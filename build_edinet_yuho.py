#!/usr/bin/env python3
"""EDINET から「話題の企業」の有価証券報告書（有報）本文を取り、edinet-yuho.json に書く。

目的（2026-09-02 新設）
  「数字で見る、話題の企業」レーン（drafts/COMPANY_GUIDE.md）は日本株の §1④＝**会社自身が挙げるリスク**を
  有報の「事業等のリスク」から書く設計だが、クラウド routine は GitHub Secrets（EDINET_API_KEY）を
  読めないため EDINET API v2 が 401 で止まり、日本株が毎週エスカレしていた。
  → fundamental-context.json と同じ型で、**Actions 側がキーを使って取得し JSON にコミット**、
    routine はこのファイルを読むだけにする。

やること
  ① 候補企業 = jp-rankings.json の gainers/losers/hot に **直近14日で2回以上**載った証券コード
     （COMPANY_GUIDE §2-1 と同じ定義。登場履歴は本スクリプト自身が JSON に積む＝git log 不要）。
     0件なら最新スナップショットの hot 上位を fallback として載せる（`fallback: true` で明示）。
  ② EDINET 書類一覧API（日付単位）で有報（docTypeCode 120）の索引を **毎日少しずつ** 積み上げる。
     有報は年1回なので、直近 INDEX_TARGET_DAYS（420日）ぶんを、1回の実行で BACKFILL_PER_RUN 日ずつ遡る。
     （EDINET 利用規約＝「短時間における大量のアクセス」禁止。1回の実行の呼び出し数は LIST_BUDGET で上限）
  ③ 候補企業ごとに最新の有報を書類取得API（type=5＝XBRL→CSV）から取り、
     「事業等のリスク」「沿革」「事業の内容」「経営方針」「MD&A」の TextBlock と
     「主要な経営指標等の推移」の数値を JSON に入れる。
     🚨 本文は**加工しない**（HTMLタグ除去と空白正規化のみ）。数値も EDINET の値をそのまま持つ。

出力 edinet-yuho.json は GitHub 側で生成・コミット＝**SYNC禁忌**（ローカルから push しない）。
APIキー未設定は exit 2 で止まり、既存 JSON を空で上書きしない。

ローカルでの動作確認は `python build_edinet_yuho.py --dry-run`（ファイルを書かない）。
"""
from __future__ import annotations

import csv
import datetime
import html
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "edinet-yuho.json")
RANKINGS = os.path.join(HERE, "jp-rankings.json")
JST = datetime.timezone(datetime.timedelta(hours=9))

API_LIST = "https://api.edinet-fsa.go.jp/api/v2/documents.json"
API_DOC = "https://api.edinet-fsa.go.jp/api/v2/documents/{doc_id}"
DOC_URL = "https://disclosure2.edinet-fsa.go.jp/WZEK0040.aspx"   # 書類閲覧ページ（出典リンク先）
USER_AGENT = "marketwatch-jp/1.0"
TIMEOUT = 60

DOCTYPE_YUHO = "120"          # 有価証券報告書（訂正 130 は部分訂正が多いので索引に入れない）

# ── 候補選定（COMPANY_GUIDE §2-1 と同じ） ────────────────────────────────
APPEAR_WINDOW_DAYS = 14       # 直近14日
APPEAR_MIN = 2                # 2回以上登場
FALLBACK_HOT_TOP = 5          # 該当0件のときの受け皿＝最新 hot 上位
MAX_CANDIDATES = 15

# ── EDINET への負荷上限（規約対策。上げないこと） ──────────────────────────
INDEX_TARGET_DAYS = 420       # 有報は年1回＝1年+余裕を索引すれば必ず1本ある
BACKFILL_PER_RUN = int(os.environ.get("BACKFILL_PER_RUN", "60") or 60)   # 1回の実行で遡る日数
LIST_BUDGET = 90              # 書類一覧APIの呼び出し上限/回（前進+遡り合計）
DOC_BUDGET = 8                # 書類取得APIの呼び出し上限/回
LIST_WAIT = 1.2               # 呼び出し間隔[秒]
DOC_WAIT = 1.5

# ── 本文の上限（JSON 肥大防止。超えたら truncated=true を立てて切る） ────────
TEXT_LIMITS = {
    "risks": 60000, "history": 20000, "business": 20000, "policy": 30000, "mdna": 40000,
}
TEXT_BLOCKS = {
    "jpcrp_cor:BusinessRisksTextBlock": "risks",                        # 事業等のリスク
    "jpcrp_cor:CompanyHistoryTextBlock": "history",                     # 沿革
    "jpcrp_cor:DescriptionOfBusinessTextBlock": "business",             # 事業の内容
    "jpcrp_cor:BusinessPolicyBusinessEnvironmentIssuesToAddressEtcTextBlock": "policy",   # 経営方針・課題
    "jpcrp_cor:ManagementAnalysisOfFinancialPositionOperatingResultsAndCashFlowsTextBlock": "mdna",
}
RE_SUMMARY_CTX = re.compile(r"^(CurrentYear|Prior[1-4]Year)(Duration|Instant)(_NonConsolidatedMember)?$")
KEEP_STALE_DAYS = 45          # 候補から外れた会社の本文を保持する日数


class EdinetError(RuntimeError):
    pass


# ───────────────────────── API ─────────────────────────
def get_api_key():
    """①環境変数（Actions＝GitHub Secrets） ②market-news-config.json の edinet_api_key（ローカル・.gitignore 済）。"""
    key = os.environ.get("EDINET_API_KEY", "").strip()
    if key:
        return key
    try:
        with open(os.path.join(HERE, "market-news-config.json"), encoding="utf-8-sig") as f:
            return (json.load(f).get("edinet_api_key") or "").strip()
    except Exception:
        return ""


def api_list(date_str, api_key):
    """書類一覧API（type=2）。HTTP 200 でも本文の status がエラーのことがある＝本文で判定。"""
    q = urllib.parse.urlencode({"date": date_str, "type": 2, "Subscription-Key": api_key})
    req = urllib.request.Request(f"{API_LIST}?{q}", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        body = json.load(r)
    status = str((body.get("metadata") or {}).get("status") or body.get("StatusCode") or "200")
    if status != "200":
        msg = body.get("message") or (body.get("metadata") or {}).get("message") or "不明なエラー"
        raise EdinetError(f"EDINET 書類一覧API がエラー（status={status}）: {msg}")
    return body.get("results") or []


def api_doc_csv(doc_id, api_key):
    """書類取得API（type=5＝XBRL_TO_CSV の zip）→ {csv名: 本文(str)}。zip でなければ空。"""
    url = API_DOC.format(doc_id=urllib.parse.quote(doc_id)) + \
        f"?type=5&Subscription-Key={urllib.parse.quote(api_key)}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        raw = r.read()
    if raw[:2] != b"PK":
        return {}
    z = zipfile.ZipFile(io.BytesIO(raw))
    out = {}
    for n in z.namelist():
        if n.lower().endswith(".csv") and "jpcrp" in n.lower():
            out[n] = z.read(n).decode("utf-16", errors="replace")
    return out


# ───────────────────────── 純関数 ─────────────────────────
def sec4(sec_code):
    """EDINET の secCode（5桁・末尾0）→ 4桁。例 '72030'→'7203', '130A0'→'130A'。"""
    s = (sec_code or "").strip()
    if len(s) == 5 and s.endswith("0"):
        return s[:-1]
    return s


def strip_html(s):
    """TextBlock の HTML を素のテキストへ（段落と改行だけ残す。内容は変えない）。"""
    if not s:
        return ""
    s = re.sub(r"(?is)<\s*(br|/p|/tr|/li|/h\d|/div)\s*/?\s*>", "\n", s)
    s = re.sub(r"(?is)<\s*/t[dh]\s*>", "\t", s)
    s = re.sub(r"(?s)<[^>]+>", "", s)
    s = html.unescape(s).replace("　", " ").replace("\xa0", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"[ \t]*\n[ \t]*", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def parse_yuho_csv(csv_texts):
    """XBRL_TO_CSV（タブ区切り・引用符付き・値に改行を含む）から本文と主要指標を取り出す純関数。

    列（2026-08-10 実測の構造）: 0=要素ID 1=項目名 2=コンテキストID 3=相対年度 4=連結個別
                                  5=期間時点 6=ユニットID 7=単位 8=値
    ⚠️ 値に改行を含む行があるので splitlines ではなく csv モジュールで読む。
    戻り値: {"texts": {key: str}, "truncated": [key], "summary": {element: {...}}}
    """
    texts, truncated, summary = {}, [], {}
    for _name, txt in sorted(csv_texts.items()):
        rows = csv.reader(io.StringIO(txt), delimiter="\t")
        for f in rows:
            if len(f) < 9 or not f[0].startswith("jpcrp_cor:"):
                continue
            eid, label, ctx, unit, val = f[0], f[1], f[2], f[7], f[8]
            key = TEXT_BLOCKS.get(eid)
            if key:
                if texts.get(key):
                    continue                        # 最初に出た非空を採用
                plain = strip_html(val)
                if not plain:
                    continue
                lim = TEXT_LIMITS[key]
                if len(plain) > lim:
                    plain = plain[:lim] + "\n…（以下略・原文は出典URLで確認）"
                    truncated.append(key)
                texts[key] = plain
                continue
            short = eid.split(":", 1)[1]
            if (short.endswith("SummaryOfBusinessResults") or short == "NumberOfEmployees") \
                    and RE_SUMMARY_CTX.match(ctx):
                if val in ("", "－", "-"):
                    continue
                ent = summary.setdefault(short, {"label": label, "unit": unit, "values": {}})
                ent["values"].setdefault(ctx, val)
    return {"texts": texts, "truncated": truncated, "summary": summary}


def index_from_docs(docs, date_str):
    """書類一覧の results から 有報 だけ {sec4: エントリ} へ（取下げ・不開示は除外）。"""
    out = {}
    for d in docs:
        if str(d.get("docTypeCode") or "") != DOCTYPE_YUHO:
            continue
        if str(d.get("withdrawalStatus") or "0") in ("1", "2"):
            continue
        if str(d.get("disclosureStatus") or "0") in ("1", "2"):
            continue
        code = sec4(d.get("secCode"))
        doc_id = (d.get("docID") or "").strip()
        if not code or not doc_id:
            continue
        ent = {
            "docID": doc_id,
            "submitDateTime": d.get("submitDateTime") or date_str,
            "filerName": (d.get("filerName") or "").strip(),
            "periodEnd": d.get("periodEnd") or "",
            "docDescription": (d.get("docDescription") or "").strip(),
            "url": f"{DOC_URL}?{doc_id}",
        }
        prev = out.get(code)
        if not prev or ent["submitDateTime"] > prev["submitDateTime"]:
            out[code] = ent
    return out


def merge_index(index, new_entries):
    """新しい提出日のものだけ上書き（遡り中に古い有報で新しいものを潰さない）。"""
    for code, ent in new_entries.items():
        prev = index.get(code)
        if not prev or ent["submitDateTime"] > prev["submitDateTime"]:
            index[code] = ent


def update_appearances(appearances, rankings, today):
    """jp-rankings.json の asof 日を登場履歴に足し、14日より古い日を落とす。"""
    asof = (rankings or {}).get("asof") or ""
    if asof:
        for sec in ("gainers", "losers", "hot"):
            for row in rankings.get(sec) or []:
                code = str(row.get("code") or "").strip()
                if not code:
                    continue
                ent = appearances.setdefault(code, {"name": row.get("name") or "", "dates": {}})
                if row.get("name"):
                    ent["name"] = row["name"]
                ent["dates"].setdefault(asof, [])
                if sec not in ent["dates"][asof]:
                    ent["dates"][asof].append(sec)
    cutoff = (today - datetime.timedelta(days=APPEAR_WINDOW_DAYS)).isoformat()
    for code in list(appearances):
        ds = {d: v for d, v in appearances[code]["dates"].items() if d >= cutoff}
        if ds:
            appearances[code]["dates"] = ds
        else:
            del appearances[code]
    return appearances


def pick_candidates(appearances, rankings):
    """直近14日に2回以上登場 → 候補（回数降順・最新日降順）。0件なら最新 hot 上位を fallback。"""
    scored = []
    for code, ent in appearances.items():
        n = len(ent["dates"])
        if n >= APPEAR_MIN:
            scored.append((n, max(ent["dates"]), code))
    scored.sort(reverse=True)
    cands = [{"code": c, "name": appearances[c]["name"], "appearances": n,
              "dates": sorted(appearances[c]["dates"]), "fallback": False}
             for n, _, c in scored[:MAX_CANDIDATES]]
    if cands:
        return cands
    for row in (rankings or {}).get("hot") or []:
        if len(cands) >= FALLBACK_HOT_TOP:
            break
        code = str(row.get("code") or "").strip()
        if code:
            cands.append({"code": code, "name": row.get("name") or "", "appearances": 1,
                          "dates": [rankings.get("asof") or ""], "fallback": True})
    return cands


def plan_index_dates(coverage, today, backfill_per_run, budget):
    """今回の実行で書類一覧を引く日付列。前進（coverage.to+1〜today）を優先し、残りで遡る。"""
    dates = []
    if coverage.get("from") and coverage.get("to"):
        c_from = datetime.date.fromisoformat(coverage["from"])
        c_to = datetime.date.fromisoformat(coverage["to"])
        d = c_to + datetime.timedelta(days=1)
        while d <= today and len(dates) < budget:
            dates.append(d)
            d += datetime.timedelta(days=1)
        floor = today - datetime.timedelta(days=INDEX_TARGET_DAYS)
        d = c_from - datetime.timedelta(days=1)
        n = 0
        while d >= floor and n < backfill_per_run and len(dates) < budget:
            dates.append(d)
            d -= datetime.timedelta(days=1)
            n += 1
    else:
        d = today
        n = 0
        while n < backfill_per_run and len(dates) < budget:
            dates.append(d)
            d -= datetime.timedelta(days=1)
            n += 1
    return dates


# ───────────────────────── 本体 ─────────────────────────
def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def run(api_key, today=None, list_fn=api_list, doc_fn=api_doc_csv, sleep=time.sleep,
        prev=None, rankings=None, log=print):
    today = today or datetime.datetime.now(JST).date()
    prev = prev if prev is not None else load_json(OUT, {})
    rankings = rankings if rankings is not None else load_json(RANKINGS, {})

    index = dict(prev.get("index") or {})
    coverage = dict(prev.get("index_coverage") or {})
    appearances = update_appearances(dict(prev.get("appearances") or {}), rankings, today)
    candidates = pick_candidates(appearances, rankings)
    companies = dict(prev.get("companies") or {})
    errors = []

    # ② 索引を積む（前進→遡り）
    dates = plan_index_dates(coverage, today, BACKFILL_PER_RUN, LIST_BUDGET)
    done_dates = []
    for i, d in enumerate(dates):
        ds = d.isoformat()
        try:
            merge_index(index, index_from_docs(list_fn(ds, api_key), ds))
            done_dates.append(d)
        except EdinetError as e:
            errors.append(f"list {ds}: {e}")
            raise
        except Exception as e:                    # 通信断などは記録して続行（索引は取れた分だけ進む）
            errors.append(f"list {ds}: {e}")
            break
        if i < len(dates) - 1:
            sleep(LIST_WAIT)
    if done_dates:
        lo, hi = min(done_dates), max(done_dates)
        if coverage.get("from") and coverage.get("to"):
            c_from, c_to = coverage["from"], coverage["to"]
            # 前進分と遡り分は coverage と連続しているので min/max で結合できる
            coverage = {"from": min(c_from, lo.isoformat()), "to": max(c_to, hi.isoformat())}
        else:
            coverage = {"from": lo.isoformat(), "to": hi.isoformat()}
    cov_days = 0
    if coverage:
        cov_days = (datetime.date.fromisoformat(coverage["to"])
                    - datetime.date.fromisoformat(coverage["from"])).days + 1
    log(f"📚 索引: {len(index)}社 / 範囲 {coverage.get('from')}〜{coverage.get('to')}（{cov_days}日・目標{INDEX_TARGET_DAYS}日）"
        f" / 今回 {len(done_dates)}日ぶん取得")

    # ③ 候補の有報本文
    fetched = 0
    missing = []
    for c in candidates:
        code = c["code"]
        ent = index.get(code)
        if not ent:
            missing.append({"code": code, "name": c["name"],
                            "reason": "索引に有報なし（索引の範囲が足りないか、有報を提出しない会社）"})
            continue
        cur = companies.get(code)
        if cur and cur.get("docID") == ent["docID"] and cur.get("texts"):
            continue                                  # 取得済み・同じ書類
        if fetched >= DOC_BUDGET:
            missing.append({"code": code, "name": c["name"], "reason": "今回の取得予算超過（次回に取る）"})
            continue
        try:
            if fetched:
                sleep(DOC_WAIT)
            csvs = doc_fn(ent["docID"], api_key)
            fetched += 1
            parsed = parse_yuho_csv(csvs) if csvs else {"texts": {}, "truncated": [], "summary": {}}
            if not parsed["texts"]:
                errors.append(f"doc {code} {ent['docID']}: CSV に本文が無い")
                missing.append({"code": code, "name": c["name"], "reason": "書類取得はできたが本文を抽出できず"})
                continue
            companies[code] = {
                "name": ent["filerName"] or c["name"],
                "docID": ent["docID"],
                "url": ent["url"],
                "docDescription": ent["docDescription"],
                "submitDateTime": ent["submitDateTime"],
                "periodEnd": ent["periodEnd"],
                "fetched_at": datetime.datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"),
                "texts": parsed["texts"],
                "truncated": parsed["truncated"],
                "summary": parsed["summary"],
            }
            log(f"📄 {code} {companies[code]['name']}: {ent['docDescription']} "
                f"texts={list(parsed['texts'])} summary={len(parsed['summary'])}項目")
        except Exception as e:
            errors.append(f"doc {code} {ent['docID']}: {e}")
            missing.append({"code": code, "name": c["name"], "reason": f"書類取得に失敗: {e}"})

    # 候補から外れて久しい会社は落とす（肥大防止）
    cand_codes = {c["code"] for c in candidates}
    keep_after = (today - datetime.timedelta(days=KEEP_STALE_DAYS)).strftime("%Y-%m-%d")
    for code in list(companies):
        if code not in cand_codes and (companies[code].get("fetched_at") or "") < keep_after:
            del companies[code]

    return {
        "generated_at": datetime.datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"),
        "source": {
            "name": "EDINET（金融庁）書類一覧API / 書類取得API v2",
            "url": "https://disclosure2.edinet-fsa.go.jp/",
            "note": "本文は有価証券報告書の記載をそのまま（HTMLタグ除去のみ）。出典は各社 url（EDINET 閲覧ページ）。",
        },
        "rankings_asof": (rankings or {}).get("asof") or "",
        "candidate_rule": f"jp-rankings.json の gainers/losers/hot に直近{APPEAR_WINDOW_DAYS}日で{APPEAR_MIN}回以上",
        "candidates": candidates,
        "missing": missing,
        "companies": companies,
        "appearances": appearances,
        "index_coverage": coverage,
        "index_days": cov_days,
        "index_complete": cov_days >= INDEX_TARGET_DAYS,
        "index": index,
        "errors": errors,
    }


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    dry = "--dry-run" in argv
    api_key = get_api_key()
    if not api_key:
        print("❌ APIキーが未設定です。Actions では GitHub Secrets の EDINET_API_KEY、"
              "ローカルでは market-news-config.json の edinet_api_key に入れてください。", file=sys.stderr)
        return 2
    try:
        data = run(api_key)
    except EdinetError as e:
        print(f"❌ {e}", file=sys.stderr)
        return 3
    print(f"🎯 候補 {len(data['candidates'])}社 / 本文あり {len(data['companies'])}社 / 未取得 {len(data['missing'])}社"
          f" / エラー {len(data['errors'])}件")
    for m in data["missing"]:
        print(f"   ⏳ {m['code']} {m['name']}: {m['reason']}")
    for e in data["errors"]:
        print(f"   ⚠️ {e}")
    if dry:
        print("（--dry-run: 書き込みなし）")
        return 0
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"✅ wrote {os.path.basename(OUT)} ({os.path.getsize(OUT):,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
