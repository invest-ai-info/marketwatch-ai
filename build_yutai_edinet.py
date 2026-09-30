# -*- coding: utf-8 -*-
"""株主優待の有無と権利の月を、有価証券報告書（EDINET）から集める（2026-09-30 オーナー「すべて進めてください」）。

目的：J9（株主優待の権利付き最終日に向けた上昇・空売りできない銘柄とできる銘柄の比較）の下ごしらえ。
      論文（Mochido-Nose 2015）は 2011〜2014年だけ＝論文の後の期間で数えるための「その時点で分かっていた優待」を作る。
      ⚠️ 値動きは一切読まない（事前登録の前）。

出どころ＝有報の「株式事務の概要」の「株主に対する特典」の欄（公的な提出書類・会社ごと年1回）。
  ・書類一覧API（type=2）で有報（docTypeCode=120）を拾い、書類取得API（type=5＝XBRL→CSV）で本文を読む。
  ・その時点の有無を作れるよう、提出日つきで**毎年の有報を全部**残す（優待の新設・廃止を追えるように）。

置き場（GitHub 側で生成＝ローカルから push しない・SYNC禁忌は check_site_consistency のディレクトリ規則）：
  yutai-edinet/state.json         取り終えた日・失敗した書類
  yutai-edinet/index-YYYY.csv     書類一覧から拾った有報（提出年ごと）
  yutai-edinet/parsed-YYYY.jsonl.gz  読んだ結果（提出年ごと。優待ありの会社だけ本文の頭400字を残す）
  yutai-edinet/probe.json         試し読みの結果（--probe のとき）

EDINET への負荷：呼び出しの間隔は既存の edinet-yuho と同じ（一覧 1.2秒・書類 1.5秒）。1回の実行は時間で区切り、残りは次の実行で。

実行: python build_yutai_edinet.py [--max-minutes 140] [--probe 2026-06-26 --probe-n 25]
"""
import argparse
import csv
import datetime as dt
import gzip
import io
import json
import os
import re
import sys
import time
import unicodedata

import build_edinet_yuho as Y

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "yutai-edinet")
LIST_START = dt.date(2020, 1, 1)      # 2021年7月以降の権利日に「直前の有報」があるように
LIST_WAIT, DOC_WAIT = Y.LIST_WAIT, Y.DOC_WAIT
KEEP_CHARS = 400                      # 優待ありの会社だけ、特典の欄の頭を残す（月の読み方を後で直せるように）
MAX_DOC_FAIL = 3                      # 同じ書類で3回失敗したら諦める
INDEX_FIELDS = ["id", "date", "submit", "sec", "period_start", "period_end", "filer"]

LABEL = "株主に対する特典"
NONE_RE = re.compile(r"^[\s　]*(該当事項(は|が)?(ありません|ございません|なし)|該当なし|なし|ありません|特になし|[―－\-‐ー—]+)[\s。．.]*($|\n|（|\()")
NEG_FIRST_RE = re.compile(r"(ありません|ございません|おりません|いません|廃止)")   # 最初の一文にあれば「なし」
DATE = r"\d{1,2}\s*月\s*(?:末日|末|\d{1,2}\s*日)"
MONTH_RE = re.compile(r"(\d{1,2})\s*月\s*(?:末日|末|\d{1,2}\s*日)")
# 「◯月◯日（及び◯月◯日）現在／を基準日／の株主名簿」＝権利の日として書かれた日付だけを拾う（発送の月などを拾わない）
GROUP_RE = re.compile(rf"((?:{DATE}\s*(?:現在)?\s*(?:及び|および|並びに|ならびに|又は|または|、|,|・|と)?\s*)+)"
                      r"(?:現在|を基準日|基準日|の株主名簿|時点|の最終の株主名簿)")
NOTE_REF_RE = re.compile(r"^\s*\(?注\s*(\d+)\)?")


# ───────────────────────── 純関数 ─────────────────────────
def norm(s):
    """全角の数字・英字を半角へ（漢字・かなは変えない）"""
    return unicodedata.normalize("NFKC", s or "")


def csv_rows(csv_texts):
    for _name, txt in sorted(csv_texts.items()):
        for f in csv.reader(io.StringIO(txt), delimiter="\t"):
            if len(f) >= 9:
                yield f


def benefit_text(csv_texts):
    """「株主に対する特典」の欄の中身（素のテキスト）と、見つけ方。見つからなければ (None, None)。
    ① 項目名に「株主に対する特典」を含む行 ② その言葉を含む TextBlock（株式事務の概要の表）の、言葉の後ろ"""
    blocks = []
    for f in csv_rows(csv_texts):
        eid, label, val = f[0], f[1], f[8]
        if LABEL in (label or ""):
            t = Y.strip_html(val)
            if t:
                return t, "label"
        if eid.endswith("TextBlock") and LABEL in (val or ""):
            blocks.append(val)
    for val in blocks:
        t = Y.strip_html(val)
        i = t.find(LABEL)
        if i >= 0:
            return t[i + len(LABEL):].strip(" \t\n:："), "block"
    return None, None


def resolve_note(text):
    """欄が「注2」のように注を指すだけのとき、その注の本文を返す（見つからなければ元のまま）"""
    n = norm(text or "")
    m = NOTE_REF_RE.match(n)
    if not m:
        return text
    k = int(m.group(1))
    i = n.find("(注)")
    if i < 0:
        return text
    notes = n[i:]
    a = re.search(rf"(?:^|[\s)。、]){k}\s*\.", notes)
    if not a:
        return text
    b = re.search(rf"[\s。、]{k + 1}\s*\.", notes[a.end():])
    return notes[a.end(): a.end() + b.start()] if b else notes[a.end():]


def record_row(csv_texts):
    """表の「基準日」の行（剰余金の配当の基準日ではない方）の中身"""
    for f in csv_rows(csv_texts):
        if f[0].endswith("TextBlock") and LABEL in (f[8] or ""):
            t = norm(Y.strip_html(f[8]))
            k = re.search(r"(?<!配当の)基準日[	 ]*(.{0,40})", t)
            return re.split(r"剰余金|1単元|単元", k.group(1))[0].strip() if k else ""
    return ""


def record_date_text(csv_texts):
    """「基準日」「剰余金の配当の基準日」の欄（表の中の行）。読むための控え"""
    for f in csv_rows(csv_texts):
        if f[0].endswith("TextBlock") and LABEL in (f[8] or ""):
            t = Y.strip_html(f[8])
            m = re.search(r"剰余金の配当の基準日[\t ]*(.{0,80})", t)
            k = re.search(r"(?<!配当の)基準日[\t ]*(.{0,60})", t)
            return " / ".join(x.group(1).replace("\n", " ").strip() for x in (k, m) if x)[:160]
    return ""


def classify(text):
    """優待の有無：True／False／None（欄が見つからない・空）"""
    if text is None:
        return None
    t = text.strip()
    if not t:
        return None
    n = norm(t)
    if NONE_RE.match(n):
        return False
    first = re.split(r"[。\n]", n, maxsplit=1)[0]
    return not NEG_FIRST_RE.search(first)


def months_in(text, head=400):
    """特典の欄の頭で、権利の日として書かれた「◯月◯日（及び◯月◯日）現在／を基準日」の月（重複なし・昇順）"""
    t = norm(text or "")[:head]
    out = set()
    for g in GROUP_RE.findall(t):
        out |= {int(m) for m in MONTH_RE.findall(g) if 1 <= int(m) <= 12}
    return sorted(out)


def yutai_months(text, rec_row):
    """(月, 読み方)。①特典の欄の権利の日 ②無ければ表の「基準日」の行（期末）"""
    m = months_in(text)
    if m:
        return m, "benefit"
    r = sorted({int(x) for x in MONTH_RE.findall(norm(rec_row or "")) if 1 <= int(x) <= 12})
    return r, ("record_row" if r else "none")


def parse_doc(csv_texts):
    raw, how = benefit_text(csv_texts)
    text = resolve_note(raw) if raw else raw
    has = classify(text)
    rec = record_row(csv_texts)
    months, mhow = yutai_months(text, rec) if has else ([], "")
    keep = KEEP_CHARS if has is not False else 120          # 読み方を後で直せるよう、なしの会社も頭だけ残す
    return {"found": how, "note_ref": raw != text, "has_yutai": has, "months": months, "months_how": mhow,
            "benefit_head": (raw or "")[:keep], "benefit_len": len(raw or ""),
            "record_row": rec, "record_dates": record_date_text(csv_texts)}


def yuho_from_list(results, date_str):
    """書類一覧の results から有報（120）だけ。取り下げ・証券コードなしは除く"""
    out = []
    for d in results or []:
        if str(d.get("docTypeCode") or "") != "120":
            continue
        if str(d.get("withdrawalStatus") or "0") != "0" or not (d.get("secCode") or "").strip():
            continue
        out.append({"id": d.get("docID"), "date": date_str, "submit": d.get("submitDateTime") or "",
                    "sec": (d.get("secCode") or "").strip(), "period_start": d.get("periodStart") or "",
                    "period_end": d.get("periodEnd") or "", "filer": (d.get("filerName") or "").strip()})
    return out


def days_between(start, end):
    """土日を除いた日（祝日は一覧が空で返るだけなので、取りこぼしを避けて除かない）"""
    d, out = start, []
    while d <= end:
        if d.weekday() < 5:
            out.append(d)
        d += dt.timedelta(days=1)
    return out


# ───────────────────────── 置き場 ─────────────────────────
def load_state(out_dir=OUT_DIR):
    try:
        with open(os.path.join(out_dir, "state.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"lists_done": [], "list_errors": {}, "doc_fail": {}, "doc_giveup": []}


def save_state(state, out_dir=OUT_DIR):
    state["lists_done"] = sorted(set(state.get("lists_done") or []))
    with open(os.path.join(out_dir, "state.json"), "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=0)


def read_index(out_dir=OUT_DIR):
    rows = {}
    for fn in sorted(os.listdir(out_dir)) if os.path.isdir(out_dir) else []:
        if re.fullmatch(r"index-\d{4}\.csv", fn):
            with open(os.path.join(out_dir, fn), encoding="utf-8", newline="") as f:
                for r in csv.DictReader(f):
                    rows[r["id"]] = r
    return rows


def append_index(rows, out_dir=OUT_DIR):
    by_year = {}
    for r in rows:
        by_year.setdefault(r["date"][:4], []).append(r)
    for y, rs in by_year.items():
        path = os.path.join(out_dir, f"index-{y}.csv")
        new = not os.path.exists(path)
        with open(path, "a", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=INDEX_FIELDS)
            if new:
                w.writeheader()
            w.writerows(rs)


def read_parsed(out_dir=OUT_DIR):
    rows = {}
    for fn in sorted(os.listdir(out_dir)) if os.path.isdir(out_dir) else []:
        if re.fullmatch(r"parsed-\d{4}\.jsonl\.gz", fn):
            with gzip.open(os.path.join(out_dir, fn), "rt", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        r = json.loads(line)
                        rows[r["id"]] = r
    return rows


def write_parsed(rows, out_dir=OUT_DIR):
    by_year = {}
    for r in rows.values():
        by_year.setdefault(r["date"][:4], []).append(r)
    for y, rs in by_year.items():
        rs.sort(key=lambda r: (r["date"], r["id"]))
        path = os.path.join(out_dir, f"parsed-{y}.jsonl.gz")
        body = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rs).encode("utf-8")
        with open(path, "wb") as f:                       # mtime=0＝中身が同じなら同じバイト列（無駄なコミットを出さない）
            with gzip.GzipFile(fileobj=f, mode="wb", mtime=0) as g:
                g.write(body)


# ───────────────────────── 実行 ─────────────────────────
def collect(api_key, max_minutes, today=None, out_dir=OUT_DIR, list_fn=Y.api_list, doc_fn=Y.api_doc_csv,
            sleep=time.sleep, clock=time.time):
    os.makedirs(out_dir, exist_ok=True)
    state = load_state(out_dir)
    t0 = clock()
    left = lambda: max_minutes - (clock() - t0) / 60   # noqa: E731
    today = today or dt.datetime.now(Y.JST).date()
    done = set(state.get("lists_done") or [])
    todo_days = [d for d in days_between(LIST_START, today - dt.timedelta(days=1)) if d.isoformat() not in done]
    n_days, found = 0, []
    for d in todo_days:                                   # ① 一覧（古い日から）
        if left() <= 0:
            break
        ds = d.isoformat()
        try:
            res = list_fn(ds, api_key)
        except Y.EdinetError as ex:
            state.setdefault("list_errors", {})[ds] = str(ex)[:120]
            done.add(ds)
            sleep(LIST_WAIT)
            continue
        except Exception as ex:  # noqa: BLE001
            state.setdefault("list_errors", {})[ds] = f"通信: {type(ex).__name__}"
            sleep(LIST_WAIT)
            continue
        found += yuho_from_list(res, ds)
        done.add(ds)
        state.get("list_errors", {}).pop(ds, None)
        n_days += 1
        sleep(LIST_WAIT)
    state["lists_done"] = sorted(done)
    known = read_index(out_dir)
    new_rows = [r for r in found if r["id"] not in known]
    append_index(new_rows, out_dir)
    save_state(state, out_dir)

    index = read_index(out_dir)                           # ② 本文（古い提出から）
    parsed = read_parsed(out_dir)
    giveup = set(state.get("doc_giveup") or [])
    pending = sorted((r for r in index.values() if r["id"] not in parsed and r["id"] not in giveup),
                     key=lambda r: (r["date"], r["id"]))
    n_docs = 0
    for r in pending:
        if left() <= 0:
            break
        try:
            texts = doc_fn(r["id"], api_key)
        except Exception as ex:  # noqa: BLE001
            fails = state.setdefault("doc_fail", {})
            fails[r["id"]] = fails.get(r["id"], 0) + 1
            if fails[r["id"]] >= MAX_DOC_FAIL:
                giveup.add(r["id"])
            sleep(DOC_WAIT)
            continue
        p = parse_doc(texts) if texts else {"found": None, "has_yutai": None, "months": [], "benefit_head": "",
                                             "benefit_len": 0, "record_dates": "", "no_csv": True}
        parsed[r["id"]] = {"id": r["id"], "date": r["date"], "submit": r["submit"], "sec": r["sec"],
                           "period_end": r["period_end"], **p}
        state.get("doc_fail", {}).pop(r["id"], None)
        n_docs += 1
        sleep(DOC_WAIT)
        if n_docs % 200 == 0:                             # 途中で落ちても積んだ分を残す
            write_parsed(parsed, out_dir)
    state["doc_giveup"] = sorted(giveup)
    state["updated"] = dt.datetime.now(Y.JST).isoformat(timespec="minutes")
    write_parsed(parsed, out_dir)
    save_state(state, out_dir)
    left_docs = len([r for r in index.values() if r["id"] not in parsed and r["id"] not in giveup])
    has = [p["has_yutai"] for p in parsed.values()]
    return {"days_fetched": n_days, "days_left": len(todo_days) - n_days, "yuho_indexed": len(index),
            "docs_parsed_now": n_docs, "docs_parsed_total": len(parsed), "docs_left": left_docs,
            "giveup": len(giveup), "has_true": has.count(True), "has_false": has.count(False),
            "has_none": has.count(None)}


def probe(api_key, date_str, n, out_dir=OUT_DIR, list_fn=Y.api_list, doc_fn=Y.api_doc_csv, sleep=time.sleep):
    """試し読み：1日分の一覧から有報を n 本だけ読み、欄の見つかり方を確かめる（状態は変えない）"""
    os.makedirs(out_dir, exist_ok=True)
    docs = yuho_from_list(list_fn(date_str, api_key), date_str)[:n]
    out = []
    for r in docs:
        sleep(DOC_WAIT)
        texts = doc_fn(r["id"], api_key)
        labels = sorted({(f[0], f[1]) for f in csv_rows(texts)
                         if re.search("株式事務|特典|基準日", (f[1] or "") + f[0])})
        p = parse_doc(texts) if texts else {}
        out.append({"id": r["id"], "sec": r["sec"], "period_end": r["period_end"], "labels": labels[:12],
                    "found": p.get("found"), "has_yutai": p.get("has_yutai"), "months": p.get("months"),
                    "head": (p.get("benefit_head") or "")[:120], "record_dates": p.get("record_dates")})
    summary = {"date": date_str, "n": len(out), "found_label": sum(o["found"] == "label" for o in out),
               "found_block": sum(o["found"] == "block" for o in out),
               "not_found": sum(o["found"] is None for o in out),
               "has_true": sum(o["has_yutai"] is True for o in out),
               "months_empty_when_true": sum(o["has_yutai"] is True and not o["months"] for o in out)}
    with open(os.path.join(out_dir, "probe.json"), "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "docs": out}, f, ensure_ascii=False, indent=1)
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-minutes", type=float, default=140)
    ap.add_argument("--probe", default="")
    ap.add_argument("--probe-n", type=int, default=25)
    a = ap.parse_args(argv)
    key = Y.get_api_key()
    if not key:
        print("❌ EDINET_API_KEY が未設定です（Actions の Secrets）")
        return 1
    res = probe(key, a.probe, a.probe_n) if a.probe else collect(key, a.max_minutes)
    print(json.dumps(res, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
