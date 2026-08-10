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
import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "edinet-holdings.json")
JST = datetime.timezone(datetime.timedelta(hours=9))

API = "https://api.edinet-fsa.go.jp/api/v2/documents.json"
DOC_URL = "https://disclosure2.edinet-fsa.go.jp/WZEK0040.aspx"   # 書類閲覧ページ（出典リンク先）
TERMS_URL = "https://disclosure2dl.edinet-fsa.go.jp/guide/static/disclosure/WZEK0030.html"

# 書類種別コード（API仕様書 4-1 参考資料。2026-08-08 に PDF から実確認）
#   350 = 大量保有報告書 ／ 360 = 訂正大量保有報告書
# 府令コード 060 = 株券等の大量保有の状況の開示に関する内閣府令
#   → 変更報告書は独立した docTypeCode を持たないため、**府令コードで束ねる**のが確実。
ORDINANCE_LARGE_HOLDING = "060"
DOCTYPE_LABEL = {"350": "大量保有報告書", "360": "訂正大量保有報告書"}

LOOKBACK_DAYS = 5        # cron遅延・休日を跨いでも取りこぼさない（重複は docID で排除）
KEEP_ITEMS = 120         # ページに出す上限
REQUEST_WAIT = 1.2       # 連続リクエストの間隔[秒]（規約の「短時間における大量のアクセス」回避）
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


def is_large_holding(doc):
    """大量保有関連の提出書類か（府令コード優先・書類種別コードで補完）。"""
    if doc.get("ordinanceCode") == ORDINANCE_LARGE_HOLDING:
        return True
    return doc.get("docTypeCode") in DOCTYPE_LABEL


def normalize(doc, date_str):
    """1件を表示用の最小形へ。**保有割合は書類一覧APIに含まれない**ので持たせない
    （持っていない数字を推測で埋めない＝このプロジェクトの原則）。"""
    doc_id = (doc.get("docID") or "").strip()
    if not doc_id:
        return None
    # 取下げ・不開示の書類は載せない（withdrawalStatus: 1=取下書 2=取り下げられた書類）
    if str(doc.get("withdrawalStatus") or "0") in ("1", "2"):
        return None
    if str(doc.get("disclosureStatus") or "0") in ("1", "2"):
        return None
    desc = (doc.get("docDescription") or "").strip()
    return {
        "id": doc_id,
        "filer": (doc.get("filerName") or "").strip(),          # 提出者（保有者）
        "issuer": (doc.get("issuerEdinetCode") or "").strip(),   # 発行会社EDINETコード
        "sec": (doc.get("secCode") or "").strip(),               # 証券コード（5桁）
        "desc": desc,
        "type": DOCTYPE_LABEL.get(doc.get("docTypeCode"), "大量保有関連"),
        "dt": (doc.get("submitDateTime") or f"{date_str} 00:00").strip(),
        "url": f"{DOC_URL}?S100PLACEHOLDER".replace("S100PLACEHOLDER", doc_id),
    }


def collect(api_key, today=None, lookback=LOOKBACK_DAYS, sleep=time.sleep):
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
        n = 0
        for doc in (body.get("results") or []):
            if not is_large_holding(doc):
                continue
            row = normalize(doc, ds)
            if row and row["id"] not in seen:
                seen.add(row["id"])
                items.append(row)
                n += 1
        print(f"  {ds}: {n}件")
        if i < lookback - 1:
            sleep(REQUEST_WAIT)
    items.sort(key=lambda x: x["dt"], reverse=True)
    return items[:KEEP_ITEMS], errors


def main():
    api_key = os.environ.get("EDINET_API_KEY", "").strip()
    if not api_key:
        print("❌ 環境変数 EDINET_API_KEY が未設定です（GitHub Secrets に登録してください）。"
              "\n   取得手順: EDINET でアカウント作成→多要素認証→APIキー発行画面")
        return 2
    now = datetime.datetime.now(JST)
    print(f"[edinet-holdings] {now:%Y-%m-%d %H:%M JST} 直近{LOOKBACK_DAYS}日を取得…")
    try:
        items, errors = collect(api_key)
    except EdinetError as e:
        print(f"❌ {e}\n   → 既存 edinet-holdings.json は保持します（空で上書きしない）")
        return 1
    if not items:
        # 週末・連休は提出ゼロが正常。既存を保持して終了（空で上書きしない）
        print("[keep] 対象0件＝既存 edinet-holdings.json を保持（休日は提出ゼロが正常）")
        return 0
    payload = {
        "updated": now.isoformat(timespec="minutes"),
        "count": len(items),
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
