# -*- coding: utf-8 -*-
"""build_edinet_holdings.py — 大量保有報告書の新着一覧を生成（AI不使用・決定論・追加コスト0円）
================================================================================
目的: 日本株の「5%ルール」提出（大量保有報告書・変更報告書）の**新着を事実として並べる**軽量レーン。
      GitHub Actions `edinet-holdings.yml` が1日1回実行し `edinet-holdings.json` だけを commit する。
      holdings.html 側は JavaScript が閲覧時に JSON を fetch＝HTML再生成なしで常に最新
      （⚡最新ニュース・ティッカーと同じ設計。オーナー承認 2026-08-08）。

出典・ライセンス（2026-08-08 に一次情報で確認済み）:
  - データ元 = 金融庁 EDINET API v2（https://api.edinet-fsa.go.jp/api/v2/）
  - EDINET 利用規約は **公共データ利用規約（PDL1.0）準拠＝二次利用・再配布可**。
    ただし **出典表示が必須**（本スクリプトは JSON に `source` を必ず埋め、ページが常時表示する）
  - ⚠️ 規約は **スクレイピング禁止・短時間の大量アクセス禁止**。よって
    ①APIのみ使用（HTMLは取りに行かない）②1日1回・数リクエストに抑える③連続取得の間に待機を入れる

⚠️ 実装上の最大の罠（2026-08-08 実測）:
  **認証失敗でも HTTP は 200 が返り、JSON 本文の "StatusCode" が 401 になる。**
      $ curl .../documents.json?date=...&type=2   → HTTP 200
        {"StatusCode": 401,"message": "Access denied due to invalid subscription key. ..."}
  HTTP ステータスだけを見る実装は「成功した」と誤認し、**空の一覧で既存JSONを上書きする**。
  → `api_get()` は必ず本文の StatusCode を検査し、200 以外は例外にする。

⚠️ edinet-holdings.json は Actions が生成・commit する＝**SYNC_FILES に入れない（SYNC禁忌）**。
   このスクリプトと holdings.html は SYNC 対象。
"""
import collections
import csv
import datetime
import io
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import zipfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "edinet-holdings.json")
JST = datetime.timezone(datetime.timedelta(hours=9))

API = "https://api.edinet-fsa.go.jp/api/v2/documents.json"
DOC_URL = "https://disclosure2.edinet-fsa.go.jp/WZEK0040.aspx"   # 書類閲覧ページ（出典リンク先）
TERMS_URL = "https://disclosure2dl.edinet-fsa.go.jp/guide/static/disclosure/WZEK0030.html"

# EDINETコードリスト（EDINETコード → 提出者名・証券コード）。APIキー不要の公開ZIP。
# ⚠️ 2026-08-10 実測で判明した設計の誤りの修正に必要:
#   書類一覧APIの `secCode` は **提出者（＝保有者）の証券コード**であって、対象銘柄のものではない。
#   大量保有報告書の提出者はファンド・個人・財団が大半なので **120件中115件（96%）が空**だった。
#   「どの銘柄への届出か」は `issuerEdinetCode`（発行会社のEDINETコード）にあり、
#   このリストで 会社名＋証券コード に解決する。
CODELIST_URL = "https://disclosure2dl.edinet-fsa.go.jp/searchdocument/codelist/Edinetcode.zip"

# 書類種別コード（API仕様書 4-1 参考資料。2026-08-08 に PDF から実確認）
#   350 = 大量保有報告書 ／ 360 = 訂正大量保有報告書
# 府令コード 060 = 株券等の大量保有の状況の開示に関する内閣府令
#   → 変更報告書は独立した docTypeCode を持たないため、**府令コードで束ねる**のが確実。
ORDINANCE_LARGE_HOLDING = "060"
DOCTYPE_LABEL = {"350": "大量保有報告書", "360": "訂正大量保有報告書"}

# 🆕 2026-08-11: 自己株券買付状況報告書（オーナー依頼で同じ一覧に載せる）。
#   ⚠️ 大量保有（府令060）とは**別の開示制度**＝府令010・金商法24条の6・**月次の状況報告**。
#   「保有割合」の意味も違う（大量保有＝外部株主の保有割合／自己株＝会社が持つ自己株式の比率）。
#   同じ列に出すので、ページ側で必ずラベルを分けて誤読を防ぐこと。
DOCTYPE_BUYBACK = {"220": "自己株券買付状況報告書", "230": "訂正自己株券買付状況報告書"}
KIND_HOLDING, KIND_BUYBACK = "holding", "buyback"

# ===== 保有割合の強調ルール（オーナー決定 2026-08-10）=====
# 「大きく買い進んだ／新しい大口が出た／大きく売った」を一目で分かるようにする。
# ⚠️ これは事実の分類であって売買推奨ではない（ページ側でも明記する）。
UP_THRESHOLD = 5.0       # 前回比 +5ポイント以上 → 強調（買い増し）
DOWN_THRESHOLD = -5.0    # 前回比 −5ポイント以上 → 強調（売却）
NEW_THRESHOLD = 5.0      # 新規提出（前回報告なし）で保有割合がこの値超 → 強調（新規の大口）

LOOKBACK_DAYS = 5        # cron遅延・休日を跨いでも取りこぼさない（重複は docID で排除）
# ⚠️ 種別ごとに枠を確保する。自己株買付は提出が非常に多く（2026-08-11 実測: 5日で248件・
#    8/7だけで137件）、単純な時刻降順で混ぜると**大量保有報告書が押し出されて消える**。
#    ⚡ニュースティッカーで同じ失敗（低頻度カテゴリの全滅）を踏んでいるので最初から枠で確保する。
KEEP_ITEMS = {KIND_HOLDING: 120, KIND_BUYBACK: 80}
REQUEST_WAIT = 1.2       # 連続リクエストの間隔[秒]（規約の「短時間における大量のアクセス」回避）
RATIO_FETCH_WAIT = 1.5   # 書類取得APIの間隔[秒]。同上
RATIO_FETCH_BUDGET = 90  # 1回の実行で新規に取りに行く書類数の上限（暴走防止）
TIMEOUT = 30


class EdinetError(RuntimeError):
    pass


def api_get(date_str, api_key):
    """書類一覧API（type=2＝提出書類一覧＋メタデータ）。

    ⚠️ HTTP 200 でも本文の StatusCode がエラーのことがある（401など）。必ず本文で判定する。
    """
    q = urllib.parse.urlencode({"date": date_str, "type": 2, "Subscription-Key": api_key})
    req = urllib.request.Request(f"{API}?{q}", headers={"User-Agent": "marketwatch-jp/1.0"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        body = json.load(r)
    status = str((body.get("metadata") or {}).get("status") or body.get("StatusCode") or "200")
    if status != "200":
        msg = body.get("message") or (body.get("metadata") or {}).get("message") or "不明なエラー"
        raise EdinetError(f"EDINET API がエラーを返しました（status={status}）: {msg}")
    return body


def parse_code_list(raw_zip):
    """EdinetcodeDlInfo.csv を {EDINETコード: {"name":..., "sec":...}} へ。

    ⚠️ 文字コードは cp932（UTF-8で読むと例外）。1行目はダウンロード日・件数のヘッダ、
       2行目が列名、3行目以降がデータ（2026-08-10 実測: 11,380件）。
    """
    z = zipfile.ZipFile(io.BytesIO(raw_zip))
    raw = z.read(z.namelist()[0])
    txt = raw.decode("cp932", errors="replace")
    rows = list(csv.reader(io.StringIO(txt)))
    if len(rows) < 3:
        return {}
    header = rows[1]
    try:
        i_code = header.index("ＥＤＩＮＥＴコード")
        i_name = header.index("提出者名")
        i_sec = header.index("証券コード")
    except ValueError:
        return {}                      # 列名が変わったら黙って諦める（誤った列を読むより安全）
    out = {}
    for r in rows[2:]:
        if len(r) <= max(i_code, i_name, i_sec):
            continue
        code = (r[i_code] or "").strip()
        if code:
            out[code] = {"name": (r[i_name] or "").strip(), "sec": (r[i_sec] or "").strip()}
    return out


def fetch_code_map():
    """EDINETコードリストを取得。失敗しても**レーン自体は止めない**（会社名が出ないだけ）。"""
    try:
        req = urllib.request.Request(CODELIST_URL, headers={"User-Agent": "marketwatch-jp/1.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            m = parse_code_list(r.read())
        print(f"  EDINETコードリスト: {len(m)}件")
        return m
    except Exception as ex:
        print(f"  ⚠️ EDINETコードリスト取得失敗（会社名なしで継続）: {ex}")
        return {}


def classify_change(ratio, prev_ratio, is_amend=False):
    """保有割合の変化を分類する純関数（ネットワーク・書式に依存しない＝テスト対象）。

    戻り値: (flag, delta)
      flag  … "up" | "down" | "new" | ""（強調なし）
      delta … 前回比のポイント差（前回が無ければ None）

    ⚠️ 数値が取れていない（None）ときは**推測しない**＝flag="" / delta=None。
       「取れなかった」と「変化なし」を混同させないため、呼び出し側も None を空欄で描く。
    """
    if ratio is None:
        return "", None
    if prev_ratio is None:
        # 前回報告が無い＝新規の大量保有（訂正報告書は「新規」と呼べないので除く）
        if not is_amend and ratio > NEW_THRESHOLD:
            return "new", None
        return "", None
    delta = round(ratio - prev_ratio, 2)
    if delta >= UP_THRESHOLD:
        return "up", delta
    if delta <= DOWN_THRESHOLD:
        return "down", delta
    return "", delta


def parse_ratio(value, unit=""):
    """XBRL/CSV の値を割合[%]の float へ。取れない値は **None**（0.0 と混同させない）。

    ⚠️⚠️ **単位 `pure` は小数**（2026-08-10・15書類54行で実測。全行 pure・1超えゼロ）。
       `0.5121` は 0.51% ではなく **51.21%**。そのまま読むと **100倍ずれる**。
       裏付け＝①共同保有者の内訳 0.5121+0.3494+0.0008 が集約 0.8623 に一致
       ②別書類で 前回0.0893→今回0.0000・提出事由「１％以上減少」＝8.93%→0%と整合
       （0.0893% なら5%基準を満たさず提出自体があり得ない）。

    ⚠️ **全角の正規化を最初に行う**（2026-08-10 テストで捕捉）。
       Python の `\\d` は全角数字にマッチするが全角ピリオド「．」にはマッチしないため、
       正規化しないと「１２．３４」が **12.0** になる＝小数部が静かに消える。
       二次情報で数字が壊れる典型（[[project_marketwatch_compliance]] の教訓）なので、
       NFKC 正規化してから解釈する。
    ⚠️ 0% は正当な値（全部売却して 0% になった変更報告書がある）＝捨てないこと。
       0〜100 の範囲外は書式違いとみなして None（推測で直さない）。
    """
    if value is None:
        return None
    s = unicodedata.normalize("NFKC", str(value)).strip()
    s = s.replace(",", "").replace("%", "").replace(" ", "")
    if not s:
        return None
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    if not m:
        return None
    try:
        v = float(m.group(0))
    except ValueError:
        return None
    if unit == "pure":
        v *= 100
    if v < 0 or v > 100:
        return None      # 範囲外＝書式違い。推測で直さず空欄にして原本を見てもらう
    return round(v, 2)


# XBRL要素ID（2026-08-10 実データで確認）
EL_RATIO = "jplvh_cor:HoldingRatioOfShareCertificatesEtc"
EL_PREV = "jplvh_cor:HoldingRatioOfShareCertificatesEtcPerLastReport"
EL_REASON = "jplvh_cor:ReasonForFilingChangeReportCoverPage"
CTX_AGG = "FilingDateInstant"     # 共同保有者がいる場合のグループ合計


def extract_ratio_rows(csv_text):
    """XBRL_TO_CSV（タブ区切り）から (現在割合, 前回割合, 提出事由) を取り出す純関数。

    選び方（2026-08-10 実測の構造に従う）:
      ① 集約行 `FilingDateInstant` があればそれ（＝グループ合計。内訳の和と一致することを確認済み）
      ② 無ければ内訳が**1行だけ**のときに限りその行（単独保有＝集約行が出ない書類が 9/15 件）
      ③ 内訳が複数あるのに集約が無い場合は **None**（合算を自作しない＝数字を作らない）
    """
    agg_cur = agg_prev = None
    members_cur, members_prev = [], []
    reason = ""
    for line in csv_text.splitlines()[1:]:
        f = [c.strip('"') for c in line.split("\t")]
        if len(f) < 9:
            continue
        eid, ctx, unit, val = f[0], f[2], f[6], f[8]
        if eid == EL_RATIO:
            r = parse_ratio(val, unit)
            if ctx == CTX_AGG:
                agg_cur = r
            else:
                members_cur.append(r)
        elif eid == EL_PREV:
            r = parse_ratio(val, unit)
            if ctx == CTX_AGG:
                agg_prev = r
            else:
                members_prev.append(r)
        elif eid == EL_REASON and val not in ("－", "-", ""):
            reason = val
    if agg_cur is not None:
        return agg_cur, agg_prev, reason
    if len(members_cur) == 1:
        return members_cur[0], (members_prev[0] if len(members_prev) == 1 else None), reason
    return None, None, reason


def fetch_doc_ratio(doc_id, api_key):
    """書類取得API(type=5＝XBRLのCSV)から割合を取る。失敗は (None, None, "") で返す（止めない）。"""
    url = (f"https://api.edinet-fsa.go.jp/api/v2/documents/{urllib.parse.quote(doc_id)}"
           f"?type=5&Subscription-Key={urllib.parse.quote(api_key)}")
    req = urllib.request.Request(url, headers={"User-Agent": "marketwatch-jp/1.0"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        raw = r.read()
    if raw[:2] != b"PK":               # ZIPでなければ失敗（本文にJSONエラーが入る形）
        return None, None, ""
    z = zipfile.ZipFile(io.BytesIO(raw))
    names = [n for n in z.namelist() if n.lower().endswith(".csv")]
    if not names:
        return None, None, ""
    return extract_ratio_rows(z.read(names[0]).decode("utf-16", errors="replace"))


def is_large_holding(doc):
    """大量保有関連の提出書類か（府令コード優先・書類種別コードで補完）。"""
    if doc.get("ordinanceCode") == ORDINANCE_LARGE_HOLDING:
        return True
    return doc.get("docTypeCode") in DOCTYPE_LABEL


def doc_kind(doc):
    """対象書類なら種別を返す（対象外は None）。"""
    if is_large_holding(doc):
        return KIND_HOLDING
    if doc.get("docTypeCode") in DOCTYPE_BUYBACK:
        return KIND_BUYBACK
    return None


# 自己株券買付状況報告書の「保有状況」テキストブロック（数値が独立要素になっておらず
# 表を平坦化した文字列に埋まっている＝2026-08-11 実測）。20書類で 20/20 抽出成功・
# 値も 0.09〜17.41% と妥当（自己株式数 ≤ 発行済株式総数 も全件成立）を確認済み。
EL_HOLD_BLOCK = "HoldingOfTreasurySharesTextBlock"
RE_SHARES_TOTAL = re.compile(r"発行済株式総数[^\d]{0,12}([\d,]+)")
RE_SHARES_OWN = re.compile(r"保有自己株式数[^\d]{0,12}([\d,]+)")


def extract_treasury_ratio(csv_text):
    """自己株券買付状況報告書から「自己株式の保有比率[%]」を計算する純関数。

    戻り値: (比率[%] or None, 発行済株式総数 or None, 保有自己株式数 or None)
    ⚠️ 妥当性を満たさない値は **None**（0 と混同させない・推測で直さない）:
       発行済>0 / 0≤自己≤発行済 / 比率0〜100。
    """
    block = ""
    for line in csv_text.splitlines():
        if EL_HOLD_BLOCK in line:
            f = [c.strip('"') for c in line.split("\t")]
            if len(f) >= 9:
                block = f[8]
            break
    if not block:
        return None, None, None
    mt, mo = RE_SHARES_TOTAL.search(block), RE_SHARES_OWN.search(block)
    if not (mt and mo):
        return None, None, None
    try:
        total = int(mt.group(1).replace(",", ""))
        own = int(mo.group(1).replace(",", ""))
    except ValueError:
        return None, None, None
    if total <= 0 or own < 0 or own > total:
        return None, None, None
    return round(own / total * 100, 2), total, own


def fetch_treasury_ratio(doc_id, api_key):
    """自己株券買付状況報告書の自己株比率を取得（失敗は None）。"""
    url = (f"https://api.edinet-fsa.go.jp/api/v2/documents/{urllib.parse.quote(doc_id)}"
           f"?type=5&Subscription-Key={urllib.parse.quote(api_key)}")
    with urllib.request.urlopen(
            urllib.request.Request(url, headers={"User-Agent": "marketwatch-jp/1.0"}),
            timeout=TIMEOUT) as r:
        raw = r.read()
    if raw[:2] != b"PK":
        return None, None, None
    z = zipfile.ZipFile(io.BytesIO(raw))
    names = [n for n in z.namelist() if n.lower().endswith(".csv")]
    if not names:
        return None, None, None
    return extract_treasury_ratio(z.read(names[0]).decode("utf-16", errors="replace"))


def normalize(doc, date_str, code_map=None):
    """1件を表示用の最小形へ。**保有割合は書類一覧APIに含まれない**ので持たせない
    （持っていない数字を推測で埋めない＝このプロジェクトの原則）。

    対象銘柄は issuerEdinetCode を code_map で会社名＋証券コードに解決する
    （secCode は提出者自身のコードなので対象銘柄ではない＝2026-08-10 の修正）。
    """
    doc_id = (doc.get("docID") or "").strip()
    if not doc_id:
        return None
    # 取下げ・不開示の書類は載せない（withdrawalStatus: 1=取下書 2=取り下げられた書類）
    if str(doc.get("withdrawalStatus") or "0") in ("1", "2"):
        return None
    if str(doc.get("disclosureStatus") or "0") in ("1", "2"):
        return None
    desc = (doc.get("docDescription") or "").strip()
    kind = doc_kind(doc) or KIND_HOLDING
    if kind == KIND_BUYBACK:
        # 自己株買付は「提出者＝対象会社」＝issuerEdinetCode は空。提出者側のコードで解決する。
        issuer_code = (doc.get("edinetCode") or "").strip()
    else:
        issuer_code = (doc.get("issuerEdinetCode") or "").strip()
    info = (code_map or {}).get(issuer_code) or {}
    # ⚠️ 書類名は docDescription を正とする（2026-08-10 実測: docTypeCode 350 には
    #    「大量保有報告書」だけでなく「変更報告書」も含まれ、コード表だけでは区別できない）。
    if kind == KIND_BUYBACK:
        label = DOCTYPE_BUYBACK.get(doc.get("docTypeCode"), "自己株券買付状況報告書")
    else:
        label = desc or DOCTYPE_LABEL.get(doc.get("docTypeCode"), "大量保有関連")
    return {
        "id": doc_id,
        "kind": kind,
        "filer": (doc.get("filerName") or "").strip(),          # 提出者（保有者／自己株は会社自身）
        "issuer": issuer_code,                                   # 対象会社のEDINETコード
        # ⚠️ 未解決時のフォールバックは **自己株買付のみ**。大量保有で提出者名を代用すると
        #    「保有者を対象銘柄として表示する」誤りになる（2026-08-11 テストで捕捉）。
        "iname": info.get("name", "") or (
            (doc.get("filerName") or "").strip() if kind == KIND_BUYBACK else ""),
        "isec": info.get("sec", "") or (
            (doc.get("secCode") or "").strip() if kind == KIND_BUYBACK else ""),
        "desc": desc,
        "type": label[:24],
        "csv": str(doc.get("csvFlag") or "0") == "1",            # 割合を取りに行けるか
        "dt": (doc.get("submitDateTime") or f"{date_str} 00:00").strip(),
        "url": f"{DOC_URL}?S100PLACEHOLDER".replace("S100PLACEHOLDER", doc_id),
    }


def enrich_ratios(items, api_key, cache, sleep=time.sleep, budget=RATIO_FETCH_BUDGET):
    """各件に保有割合を付ける。**キャッシュ済みの書類は再取得しない**
    （EDINET規約の「短時間における大量のアクセス」を避ける＝新着ぶんだけ取りに行く）。

    cache: {docID: {"ratio":…, "prev":…, "reason":…}}（前回の edinet-holdings.json から復元）
    戻り値: (取得した件数, 失敗件数)
    """
    fetched = failed = 0
    # ⚠️ 大量保有を先に埋める。予算超過で削られるのは自己株買付（件数が多く、月次で毎回出る）側にする。
    for it in sorted(items, key=lambda x: 0 if x.get("kind") == KIND_HOLDING else 1):
        hit = cache.get(it["id"])
        if hit is not None:
            it["ratio"], it["prev"], it["reason"] = hit.get("ratio"), hit.get("prev"), hit.get("reason", "")
        elif it.get("csv") and fetched < budget:
            try:
                if it.get("kind") == KIND_BUYBACK:
                    cur, _total, _own = fetch_treasury_ratio(it["id"], api_key)
                    prev, reason = None, ""
                else:
                    cur, prev, reason = fetch_doc_ratio(it["id"], api_key)
                it["ratio"], it["prev"], it["reason"] = cur, prev, reason
                fetched += 1
            except Exception as ex:
                it["ratio"] = it["prev"] = None
                it["reason"] = ""
                failed += 1
                print(f"  ⚠️ {it['id']} 割合取得失敗: {ex}")
            sleep(RATIO_FETCH_WAIT)
        else:
            it["ratio"] = it["prev"] = None
            it["reason"] = ""
        # 強調フラグは**大量保有だけ**。自己株の比率は意味が違うので同じ判定にかけない
        if it.get("kind") == KIND_BUYBACK:
            it["flag"], it["delta"] = "", None
        else:
            it["flag"], it["delta"] = classify_change(
                it["ratio"], it["prev"], is_amend="訂正" in (it.get("type") or ""))
    return fetched, failed


def collect(api_key, today=None, lookback=LOOKBACK_DAYS, sleep=time.sleep, code_map=None):
    """直近 lookback 日ぶんを取得して新しい順に返す。docID で重複排除。"""
    today = today or datetime.datetime.now(JST).date()
    items, seen, errors = [], set(), []
    for i in range(lookback):
        d = today - datetime.timedelta(days=i)
        ds = d.isoformat()
        try:
            body = api_get(ds, api_key)
        except EdinetError:
            raise                      # 認証エラー等は即座に上へ（空JSONで上書きしないため）
        except Exception as ex:        # 通信の一時失敗はその日だけ諦めて続行
            errors.append(f"{ds}: {ex}")
            print(f"  ⚠️ {ds} 取得失敗: {ex}")
            continue
        n = collections.Counter()
        for doc in (body.get("results") or []):
            if doc_kind(doc) is None:
                continue
            row = normalize(doc, ds, code_map)
            if row and row["id"] not in seen:
                seen.add(row["id"])
                items.append(row)
                n[row["kind"]] += 1
        print(f"  {ds}: 大量保有 {n[KIND_HOLDING]}件 / 自己株買付 {n[KIND_BUYBACK]}件")
        if i < lookback - 1:
            sleep(REQUEST_WAIT)
    items.sort(key=lambda x: x["dt"], reverse=True)
    return cap_by_kind(items), errors


def cap_by_kind(items):
    """種別ごとの枠で切ってから、全体を時刻降順に戻す。

    ⚠️ 単純な時刻降順の打ち切りだと、件数の多い自己株買付（実測 5日で248件）が枠を食い尽くし、
       **大量保有報告書が1件も残らない**ことがある（⚡ニュースティッカーで実際に踏んだ形）。
    """
    kept, used = [], collections.Counter()
    for it in items:                      # items は時刻降順で渡ってくる前提
        k = it.get("kind") or KIND_HOLDING
        if used[k] < KEEP_ITEMS.get(k, 0):
            kept.append(it)
            used[k] += 1
    kept.sort(key=lambda x: x["dt"], reverse=True)
    return kept


def get_api_key():
    """APIキーの取得元は ①環境変数（Actions＝GitHub Secrets） ②market-news-config.json の
    `edinet_api_key`（ローカル開発用・**.gitignore 済みでSYNC対象外**）の順。
    check_automation_health.get_cfg と同じ方式に揃えている。"""
    key = os.environ.get("EDINET_API_KEY", "").strip()
    if key:
        return key
    try:
        with open(os.path.join(HERE, "market-news-config.json"), encoding="utf-8-sig") as f:
            return (json.load(f).get("edinet_api_key") or "").strip()
    except Exception:
        return ""


def main():
    api_key = get_api_key()
    if not api_key:
        print("❌ APIキーが未設定です。Actions では GitHub Secrets の EDINET_API_KEY、"
              "ローカルでは market-news-config.json の \"edinet_api_key\" を参照します。")
        return 2
    now = datetime.datetime.now(JST)
    print(f"[edinet-holdings] {now:%Y-%m-%d %H:%M JST} 直近{LOOKBACK_DAYS}日を取得…")
    try:                                   # 前回JSON＝割合キャッシュの供給元
        with open(OUT, encoding="utf-8") as f:
            prev = json.load(f)
    except Exception:
        prev = {}
    code_map = fetch_code_map()
    try:
        items, errors = collect(api_key, code_map=code_map)
    except EdinetError as e:
        print(f"❌ {e}\n   → 既存 edinet-holdings.json は保持します（空で上書きしない）")
        return 1

    # 前回JSONから割合キャッシュを復元（取得済み書類は再取得しない）
    cache = {i["id"]: i for i in (prev.get("items") or []) if i.get("id") and "ratio" in i}
    fetched, failed = enrich_ratios(items, api_key, cache)
    got = sum(1 for i in items if i.get("ratio") is not None)
    cached = sum(1 for i in items if i["id"] in cache)
    pending = len(items) - fetched - failed - cached   # 予算上限で今回は見送った件数
    print(f"  保有割合: 解決 {got}/{len(items)}（新規取得 {fetched} / キャッシュ {cached} / "
          f"失敗 {failed} / 予算超過で次回 {pending}）")
    if not items:
        # 週末・連休は提出ゼロが正常。既存を保持して終了（空で上書きしない）
        print("[keep] 対象0件＝既存 edinet-holdings.json を保持（休日は提出ゼロが正常）")
        return 0
    payload = {
        "updated": now.isoformat(timespec="minutes"),
        "count": len(items),
        "thresholds": {"up": UP_THRESHOLD, "down": DOWN_THRESHOLD, "new": NEW_THRESHOLD},
        "source": {
            "name": "金融庁 EDINET",
            "url": "https://disclosure2.edinet-fsa.go.jp/",
            "terms": TERMS_URL,
            "note": "出典：EDINET閲覧サイト（https://disclosure2.edinet-fsa.go.jp/）"
                    "をもとに MarketWatch AI 作成。公共データ利用規約（PDL1.0）に基づき利用。",
        },
        "items": items,
    }
    if errors:
        payload["fetch_errors"] = errors
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=0)
    print(f"[ok] {len(items)}件 → edinet-holdings.json（最新: {items[0]['dt']} / {items[0]['filer'][:24]}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
