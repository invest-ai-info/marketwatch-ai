# -*- coding: utf-8 -*-
"""新しい柱・第2波＝日本株（2026-09-27 オーナー決定「2つを並行して進めてください」）。

J1 大量保有報告書（新しく5%を超えた届出）のあとの株価
J2 権利付き最終日に向けた日経平均の上がりやすさ（指数）
J3 信用取引の買い残（まずは日本取引所グループの資料の形を調べるだけ）

⚠️ 物差しと判定の基準は PILLAR_PREREG.md の「第2波・日本株」と下の定数に固定。結果を見てから動かさない。
⚠️ 出力（pillar-lab-jp.json / .md）には**個別の銘柄名・証券コードを出さない**（統計だけ）。GitHub 側で生成＝手元から送らない。
⚠️ EDINET の書類一覧は、Actions の中で `EDINET_API_KEY`（GitHub Secrets）を使って取る。取った一覧は actions/cache に置き
   （リポジトリには入れない＝毎時のワークフローの取得を重くしないため）、次の実行で足りない日だけ取り足す。

実行: python pillar_lab_jp.py --part collect,j1,j2,j3   （Actions の pillar-lab-jp.yml から手動で）
"""
import argparse
import csv
import datetime as dt
import json
import math
import os
import re
import sys
import time

import numpy as np
import pandas as pd

import pillar_lab as P

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_JSON, OUT_MD = "pillar-lab-jp.json", "pillar-lab-jp.md"
HIST_DIR = os.environ.get("EDINET_HIST_DIR", os.path.join(HERE, "edinet-hist"))   # actions/cache の置き場所
SEED, N_PERM = P.SEED, P.N_PERM

# ── 取得 ──
HIST_START = "2016-01-04"        # EDINET の書類一覧が取れる範囲の手前から。取れない日は記録して先へ
COLLECT_MAX_MIN = 150            # 1回の実行で取りに行く時間の上限（分）。残りは次の実行で
HIST_FIELDS = ["date", "dt", "id", "desc", "filer", "filer_code", "issuer", "isec", "doc_type"]

# ── J1 大量保有 ──
J1_HOLD, J1_HOLD_SUB = 60, 20    # 60営業日（主）・20営業日（読むための表）
J1_GAP = 60                      # 同じ会社への届出が60営業日以内に重なったら最初の1件だけ
J1_COST_BPS = 20.0               # 往復0.2%
J1_MIN_N = 200
J1_BENCH = "1306.T"              # TOPIX 連動 ETF
J1_MAX_ENTRY_LAG_DAYS = 10       # 提出日から入る足まで10日を超える（値段が欠けている）ものは数えない

# ── J2 権利付き最終日 ──
J2_TICKER = "^N225"
J2_START = "1990-01-01"
J2_WINDOW = 10                   # 権利付き最終日の10営業日前の終値 → 権利付き最終日の終値
J2_T2_FROM = dt.date(2019, 7, 16)   # この日以降の権利確定日は2営業日前、それより前は3営業日前
J2_MONTHS = (3, 9)
J2_SPLIT = "2008-01-01"

# ── J3 信用残（形だけ）──
J3_URLS = ["https://www.jpx.co.jp/markets/statistics-equities/margin/index.html",
           "https://www.jpx.co.jp/markets/statistics-equities/margin/05.html",
           "https://www.jpx.co.jp/markets/statistics-equities/margin/06.html"]


# ════════════════════ EDINET の一覧を取り足す ════════════════════

def _state_path():
    return os.path.join(HIST_DIR, "state.json")


def load_state():
    try:
        with open(_state_path(), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"done": [], "errors": {}}


def business_days(start, end):
    import holidays
    jp = holidays.Japan(years=range(start.year, end.year + 1))
    d, out = start, []
    while d <= end:
        if d.weekday() < 5 and d not in jp and (d.month, d.day) not in P.BANK_HOLIDAYS:
            out.append(d)
        d += dt.timedelta(days=1)
    return out


def collect(max_minutes=COLLECT_MAX_MIN, today=None, sleep=time.sleep):
    """取っていない営業日だけ書類一覧を取り、大量保有関連（変更・訂正も含む）を年ごとの CSV に足す"""
    import build_edinet_holdings as E
    key = E.get_api_key()
    if not key:
        return {"error": "EDINET_API_KEY が無い"}
    os.makedirs(HIST_DIR, exist_ok=True)
    state = load_state()
    done = set(state.get("done") or [])
    today = today or dt.datetime.now(P.JST).date()
    todo = [d for d in business_days(dt.date.fromisoformat(HIST_START), today - dt.timedelta(days=1))
            if d.isoformat() not in done]
    code_map = E.fetch_code_map()
    t0, n_new, n_days = time.time(), 0, 0
    for d in todo:
        if (time.time() - t0) / 60 > max_minutes:
            break
        ds = d.isoformat()
        try:
            body = E.api_get(ds, key)
        except E.EdinetError as ex:
            state.setdefault("errors", {})[ds] = str(ex)[:120]
            done.add(ds)             # 範囲外などで返らない日は、何度も取りに行かない
            sleep(E.REQUEST_WAIT)
            continue
        except Exception as ex:  # noqa: BLE001
            state.setdefault("errors", {})[ds] = f"通信: {type(ex).__name__}"
            sleep(E.REQUEST_WAIT)
            continue
        rows = []
        for doc in body.get("results") or []:
            if not E.is_large_holding(doc):
                continue
            r = E.normalize(doc, ds, code_map)
            if not r:
                continue
            rows.append({"date": ds, "dt": r["dt"], "id": r["id"], "desc": r["desc"], "filer": r["filer"],
                         "filer_code": (doc.get("edinetCode") or "").strip(), "issuer": r["issuer"],
                         "isec": r["isec"], "doc_type": doc.get("docTypeCode") or ""})
        path = os.path.join(HIST_DIR, f"{d.year}.csv")
        new_file = not os.path.exists(path)
        with open(path, "a", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=HIST_FIELDS)
            if new_file:
                w.writeheader()
            w.writerows(rows)
        done.add(ds)
        state.get("errors", {}).pop(ds, None)
        n_new += len(rows)
        n_days += 1
        sleep(E.REQUEST_WAIT)
    state["done"] = sorted(done)
    state["updated"] = dt.datetime.now(P.JST).isoformat(timespec="minutes")
    with open(_state_path(), "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)
    left = len([d for d in todo if d.isoformat() not in done])
    return {"days_fetched": n_days, "rows_added": n_new, "days_left": left, "days_done": len(done),
            "errors": len(state.get("errors") or {}), "first_error_dates": sorted(state.get("errors") or {})[:5]}


def load_history():
    rows = []
    if not os.path.isdir(HIST_DIR):
        return rows
    for fn in sorted(os.listdir(HIST_DIR)):
        if re.fullmatch(r"\d{4}\.csv", fn):
            with open(os.path.join(HIST_DIR, fn), encoding="utf-8", newline="") as f:
                rows += list(csv.DictReader(f))
    seen, out = set(), []
    for r in rows:
        if r["id"] not in seen:
            seen.add(r["id"])
            out.append(r)
    return out


# ════════════════════ J1 大量保有 ════════════════════

def is_new_report(desc):
    """新しく5%を超えた届出（大量保有報告書）。変更報告書・訂正は除く"""
    d = (desc or "").strip()
    return d.startswith("大量保有報告書") and "訂正" not in d and "変更" not in d


def yahoo_code(isec):
    s = (isec or "").strip()
    if len(s) == 5 and s.endswith("0"):
        s = s[:4]
    return f"{s}.T" if re.fullmatch(r"[0-9A-Z]{4}", s) else None


def j1_events(hist):
    ev = []
    for r in hist:
        if not is_new_report(r.get("desc")):
            continue
        tk = yahoo_code(r.get("isec"))
        if not tk:
            continue
        try:
            d = dt.date.fromisoformat((r.get("dt") or r["date"])[:10])
        except ValueError:
            continue
        ev.append({"ticker": tk, "date": d})
    return sorted(ev, key=lambda x: (x["ticker"], x["date"]))


def excess_path(close, bench):
    """同じ日付に並べた（銘柄, 市場全体）の対数の終値。bench は前の値で埋める"""
    b = bench.reindex(close.index, method="ffill")
    ok = close.notna() & b.notna() & (close > 0) & (b > 0)
    return np.log(close[ok].astype(float)), np.log(b[ok].astype(float))


def j1_rows(events, prices, bench, hold=J1_HOLD):
    """events: [{ticker, date}]（ticker 順）。prices: {ticker: 終値の Series}。1件＝60営業日の超過（対数）"""
    rows, by = [], {}
    for e in events:
        by.setdefault(e["ticker"], []).append(e["date"])
    for tk, dates in by.items():
        c = prices.get(tk)
        if c is None or len(c) < hold + 5:
            continue
        lc, lb = excess_path(c, bench)
        days = np.array([x.date() for x in lc.index])
        last_i = -10 ** 9
        for d in sorted(dates):
            i0 = int(np.searchsorted(days, d, side="right"))      # 提出日の翌営業日
            if i0 >= len(days) or (days[i0] - d).days > J1_MAX_ENTRY_LAG_DAYS:
                continue
            if i0 - last_i < J1_GAP:
                continue
            last_i = i0
            if i0 + hold >= len(days):
                continue
            x = (lc.iloc[i0 + hold] - lc.iloc[i0]) - (lb.iloc[i0 + hold] - lb.iloc[i0])
            row = {"ticker": tk, "date": days[i0].isoformat(), "i0": i0, "x": float(x)}
            if i0 + J1_HOLD_SUB < len(days):
                row["x20"] = float((lc.iloc[i0 + J1_HOLD_SUB] - lc.iloc[i0]) - (lb.iloc[i0 + J1_HOLD_SUB] - lb.iloc[i0]))
            rows.append(row)
    return rows


def j1_placebo(rows, prices, bench, n_perm=N_PERM, seed=SEED, hold=J1_HOLD):
    """偽薬：同じ銘柄で、届出の前後60営業日を避けたランダムな日に入った場合の平均（件数は同じ）"""
    rng = np.random.default_rng(seed)
    pools, counts = {}, {}
    for r in rows:
        counts[r["ticker"]] = counts.get(r["ticker"], 0) + 1
    for tk, k in counts.items():
        lc, lb = excess_path(prices[tk], bench)
        ex = (lc.values[hold:] - lc.values[:-hold]) - (lb.values[hold:] - lb.values[:-hold])
        bad = np.zeros(len(ex), bool)
        for r in rows:
            if r["ticker"] == tk:
                bad[max(0, r["i0"] - J1_GAP): r["i0"] + J1_GAP + 1] = True
        pool = ex[~bad[:len(ex)]]
        if len(pool):
            pools[tk] = (pool, k)
    if not pools:
        return None
    total = sum(k for _, k in pools.values())
    sims = np.empty(n_perm)
    for j in range(n_perm):
        s = 0.0
        for pool, k in pools.values():
            s += float(pool[rng.integers(0, len(pool), k)].sum())
        sims[j] = s / total
    return sims


def judge_j1(r):
    if r.get("n", 0) < J1_MIN_N:
        return "件数不足"
    lo, hi, e, l, p, net = (r.get(k) for k in ("lo", "hi", "early", "late", "p_placebo", "net_bps"))
    if None in (lo, hi, e, l, p, net):
        return "差なし（偶然の範囲）"
    if lo > 0 and e > 0 and l > 0 and p < 0.05 and net > 0:
        return "届出のあと上がりやすい兆し"
    if hi < 0 and e < 0 and l < 0 and p < 0.05:
        return "届出のあと下がりやすい兆し"
    return "差なし（偶然の範囲）"


def j1_stats(rows, sims=None):
    if not rows:
        return {"n": 0, "verdict": "件数不足"}
    res = P.mean_ci([r["x"] for r in rows], [(r["ticker"], r["date"][:7]) for r in rows])
    mid = sorted(r["date"] for r in rows)[len(rows) // 2]
    res.update({"split": mid, "early": P._mean(r["x"] for r in rows if r["date"] < mid),
                "late": P._mean(r["x"] for r in rows if r["date"] >= mid),
                "n_early": sum(r["date"] < mid for r in rows), "n_late": sum(r["date"] >= mid for r in rows),
                "stocks": len({r["ticker"] for r in rows}),
                "first": min(r["date"] for r in rows), "last": max(r["date"] for r in rows)})
    res["net_bps"] = res["mean"] * 1e4 - J1_COST_BPS
    x20 = [r["x20"] for r in rows if "x20" in r]
    res["hold20"] = {"n": len(x20), "mean": P._mean(x20)}
    if sims is not None and len(sims):
        c = float(np.mean(sims))
        res["placebo_mean"] = c
        res["p_placebo"] = float((np.sum(np.abs(sims - c) >= abs(res["mean"] - c)) + 1) / (len(sims) + 1))
    res["by_year"] = {y: {"n": len(v), "mean": P._mean(v)} for y in sorted({r["date"][:4] for r in rows})
                      for v in [[r["x"] for r in rows if r["date"][:4] == y]]}
    res["verdict"] = judge_j1(res)
    return res


def fetch_many(tickers, start, batch=80):
    """Yahoo の日足の終値をまとめて取る → {ticker: Series}"""
    import yfinance as yf
    out = {}
    tickers = sorted(set(tickers))
    for k in range(0, len(tickers), batch):
        part = tickers[k:k + batch]
        for attempt in range(3):
            try:
                df = yf.download(part, start=start, interval="1d", progress=False, auto_adjust=True,
                                 group_by="ticker", threads=True)
                break
            except Exception as e:  # noqa: BLE001
                print(f"  ⚠️ 取得失敗 {k}: {type(e).__name__}", file=sys.stderr)
                df = None
                time.sleep(3 * (attempt + 1))
        if df is None or df.empty:
            continue
        for tk in part:
            try:
                s = (df[tk]["Close"] if isinstance(df.columns, pd.MultiIndex) else df["Close"]).dropna()
            except KeyError:
                continue
            if len(s) > 30:
                ix = pd.to_datetime(s.index)
                s.index = ix.tz_localize(None) if ix.tz is not None else ix
                out[tk] = s.sort_index()
        time.sleep(1)
    return out


def run_j1():
    hist = load_history()
    if not hist:
        return {"error": "EDINET の一覧がまだ無い（collect を先に）"}
    ev = j1_events(hist)
    if not ev:
        return {"error": "新規の大量保有報告書が0件", "history_rows": len(hist)}
    start = (min(e["date"] for e in ev) - dt.timedelta(days=400)).isoformat()
    prices = fetch_many([e["ticker"] for e in ev] + [J1_BENCH], start)
    bench = prices.pop(J1_BENCH, None)
    if bench is None:
        return {"error": "TOPIX 連動 ETF の値段を取得できず"}
    rows = j1_rows(ev, prices, bench)
    sims = j1_placebo(rows, prices, bench) if rows else None
    out = j1_stats(rows, sims)
    out.update({"history_rows": len(hist), "new_reports": len(ev), "tickers_asked": len({e["ticker"] for e in ev}),
                "tickers_priced": len(prices),
                "history_first": min(r["date"] for r in hist), "history_last": max(r["date"] for r in hist)})
    return out


# ════════════════════ J2 権利付き最終日 ════════════════════

def j2_rows(close):
    """close: 日付の添字の終値。月ごとに（権利確定日＝その月の最終の取引日, 権利付き最終日, 上がりやすさ, 落ち日の1日）"""
    days = [x.date() for x in close.index]
    c = np.asarray(close.values, float)
    last_of_month = {}
    for i, d in enumerate(days):
        last_of_month[(d.year, d.month)] = i
    rows = []
    for (y, m), k in sorted(last_of_month.items()):
        if k == len(days) - 1 and (days[k] + dt.timedelta(days=1)).month == m:
            continue                                             # 月の途中で終わっている最後の月
        lag = 2 if days[k] >= J2_T2_FROM else 3
        j = k - lag                                              # 権利付き最終日
        if j - J2_WINDOW < 0 or j + 1 >= len(c):
            continue
        rows.append({"month": m, "date": days[k].isoformat(),
                     "run": math.log(c[j] / c[j - J2_WINDOW]) * 1e4,
                     "ex": math.log(c[j + 1] / c[j]) * 1e4})
    return rows


def judge_j2(r):
    lo, hi, e, l = r.get("lo"), r.get("hi"), r.get("early"), r.get("late")
    if None in (lo, hi, e, l):
        return "見えない（偶然の範囲）"
    if lo > 0 and e > 0 and l > 0:
        return "権利取りの上昇が見える"
    if hi < 0 and e < 0 and l < 0:
        return "逆向き"
    return "見えない（偶然の範囲）"


def j2_stats(rows):
    tgt = [r for r in rows if r["month"] in J2_MONTHS]
    oth = [r for r in rows if r["month"] not in J2_MONTHS]
    res = P.diff_ci([r["run"] for r in tgt], [r["run"] for r in oth])
    halves = []
    for part in ([r for r in rows if r["date"] < J2_SPLIT], [r for r in rows if r["date"] >= J2_SPLIT]):
        d = P.diff_ci([r["run"] for r in part if r["month"] in J2_MONTHS],
                      [r["run"] for r in part if r["month"] not in J2_MONTHS])
        halves.append(d.get("diff"))
    res["early"], res["late"] = halves
    res["ex_target"] = P._mean(r["ex"] for r in tgt)
    res["ex_other"] = P._mean(r["ex"] for r in oth)
    res["by_month"] = {m: {"n": len(v), "run": P._mean(v)} for m in range(1, 13)
                       for v in [[r["run"] for r in rows if r["month"] == m]] if v}
    res["first"], res["last"] = (rows[0]["date"], rows[-1]["date"]) if rows else (None, None)
    res["verdict"] = judge_j2(res)
    return res


def run_j2():
    s = P.fetch(J2_TICKER, "1d", start=J2_START)
    if s is None:
        return {"error": "日経平均の値段を取得できず"}
    return j2_stats(j2_rows(s["Close"]))


# ════════════════════ J3 信用残（形だけ）════════════════════

def run_j3():
    out = []
    for url in J3_URLS:
        try:
            html = P.http_get(url)
        except Exception as e:  # noqa: BLE001
            out.append({"url": url, "ok": False, "error": f"{type(e).__name__}: {str(e)[:120]}"})
            continue
        links = re.findall(r'href="([^"]+)"[^>]*>([^<]{0,80})<', html)
        keep = [(h, t.strip()) for h, t in links
                if re.search(r"csv|xls|zip|pdf|銘柄別|週末|残高|margin", h + t, re.I)]
        text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))
        out.append({"url": url, "ok": True, "chars": len(html), "links": keep[:80],
                    "keywords": {w: text.count(w) for w in ("銘柄別", "週末", "信用取引残高", "買残", "売残", "CSV", "Excel")}})
    return out


# 2026-09-27 の1回目の調べ：銘柄別の週末残高は直近数週の PDF だけ（過去分を機械で集められない）。
# 市場全体の「信用取引現在高 過去推移表」は xls があるので、その中身の形（列・先頭の数行・行数）だけを見る。
J3_FILES_PAGE = "https://www.jpx.co.jp/markets/statistics-equities/margin/06.html"


def run_j3f():
    html = P.http_get(J3_FILES_PAGE)
    urls = sorted({"https://www.jpx.co.jp" + h for h in re.findall(r'href="(/markets/statistics-equities/margin/[^"]+\.xls)"', html)})
    files = []
    for url in urls[:6]:
        try:
            st, raw = P.http_get_bytes(url)
            if st != 200 or not raw:
                files.append({"url": url, "ok": False, "error": f"HTTP {st}"})
                continue
            files.append(dict(P.summarize_table(raw, P.file_kind(raw)), url=url, ok=True))
        except Exception as e:  # noqa: BLE001
            files.append({"url": url, "ok": False, "error": f"{type(e).__name__}: {str(e)[:120]}"})
    return {"files": files}


# ════════════════════ 出力 ════════════════════

def render_md(res):
    f = P._f
    L = ["# 新しい柱・第2波（日本株）の結果", "",
         f"作成: {res['generated_at']}（GitHub Actions で計算）。事前登録＝`{P.PREREG}` の「第2波・日本株」（指紋 sha256 `{(res.get('prereg_sha256') or '')[:16]}…`）。",
         "**個別の銘柄名は載せない**（統計だけ）。どれも売買の決まりではない。", ""]
    c = res.get("collect")
    if c:
        L += ["## EDINET の一覧の取り足し", "",
              f"- {json.dumps(c, ensure_ascii=False)}", ""]
    j1 = res.get("j1")
    if j1:
        L += ["## J1 大量保有報告書（新しく5%を超えた届出）のあとの株価", ""]
        if j1.get("error"):
            L += [f"- ⚠️ 計算できず: {j1['error']}", ""]
        else:
            L += [f"- **判定（60営業日）：{j1['verdict']}**",
                  f"- 値＝その株の値動き−TOPIX 連動 ETF の値動き（60営業日・対数）。プラスなら市場全体を上回った",
                  f"- 件数 {j1.get('n', 0)}（{j1.get('stocks', 0)}銘柄・{j1.get('first')}〜{j1.get('last')}）・平均 {f(j1.get('mean'), 4)}"
                  f"（95%の幅 {f(j1.get('lo'), 4)}〜{f(j1.get('hi'), 4)}）",
                  f"- 前半 {f(j1.get('early'), 4)}（{j1.get('n_early', 0)}件）／後半 {f(j1.get('late'), 4)}（{j1.get('n_late', 0)}件）・境 {j1.get('split')}",
                  f"- 偽薬（同じ銘柄のランダムな日）の平均 {f(j1.get('placebo_mean'), 4)}・偽薬との比較 p={f(j1.get('p_placebo'), 3, False)}",
                  f"- 費用（往復0.2%）を引いた平均＝{f(j1.get('net_bps'), 1)} ベーシスポイント／20営業日（読むための表）{f((j1.get('hold20') or {}).get('mean'), 4)}",
                  f"- データ：EDINET の一覧 {j1.get('history_rows')} 件（{j1.get('history_first')}〜{j1.get('history_last')}）・新規の届出 {j1.get('new_reports')} 件・"
                  f"値段が取れた銘柄 {j1.get('tickers_priced')}/{j1.get('tickers_asked')}（上場廃止は入らない）", ""]
            if j1.get("by_year"):
                L += ["| 入った年 | 件数 | 平均 |", "|---|---:|---:|"]
                L += [f"| {y} | {v['n']} | {f(v['mean'], 4)} |" for y, v in j1["by_year"].items()]
                L.append("")
    j2 = res.get("j2")
    if j2:
        L += ["## J2 権利付き最終日に向けた日経平均", ""]
        if j2.get("error"):
            L += [f"- ⚠️ 計算できず: {j2['error']}", ""]
        else:
            L += [f"- **判定：{j2['verdict']}**（{j2.get('first')}〜{j2.get('last')}）",
                  f"- 権利付き最終日の10営業日前→当日（ベーシスポイント）：3月・9月 {f(j2.get('mean_a'), 1)}（{j2.get('n_a')}回）／ほかの月 {f(j2.get('mean_b'), 1)}（{j2.get('n_b')}回）",
                  f"- 差 {f(j2.get('diff'), 1)}（95%の幅 {f(j2.get('lo'), 1)}〜{f(j2.get('hi'), 1)}）・前半（2007年まで）{f(j2.get('early'), 1)}／後半（2008年から）{f(j2.get('late'), 1)}",
                  f"- 読むための表：権利落ち日の1日 3月・9月 {f(j2.get('ex_target'), 1)}／ほかの月 {f(j2.get('ex_other'), 1)}（指数は配当の分だけ機械的に下がる）", "",
                  "| 月 | 回数 | 10営業日の平均 |", "|---|---:|---:|"]
            L += [f"| {m}月 | {v['n']} | {f(v['run'], 1)} |" for m, v in (j2.get("by_month") or {}).items()]
            L.append("")
    j3 = res.get("j3")
    if j3:
        L += ["## J3 信用残（資料の形を調べただけ）", ""]
        for p in j3:
            if not p.get("ok"):
                L.append(f"- {p['url']}：取得できず（{p.get('error', '')}）")
            else:
                kw = ", ".join(f"{k}={v}" for k, v in p["keywords"].items() if v)
                L.append(f"- {p['url']}：資料らしいリンク {len(p['links'])} 件／キーワード {kw or 'なし'}")
        L.append("")
    j3f = res.get("j3f")
    if isinstance(j3f, dict) and j3f.get("files"):
        L += ["### J3 市場全体の信用残の資料の中身の形", ""]
        for x in j3f["files"]:
            if not x.get("ok"):
                L.append(f"- {x['url']}：取得できず（{x.get('error', '')}）")
            else:
                sh = "、".join(f"{k}（{v['rows']}行×{v['cols']}列）" for k, v in (x.get("sheets") or {}).items())
                L.append(f"- {x['url']}：{x['kind']}・{sh or x.get('rows')}")
        L.append("")
    L += ["---", "", "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。"]
    return "\n".join(L) + "\n"


PARTS = {"collect": collect, "j1": run_j1, "j2": run_j2, "j3": run_j3, "j3f": run_j3f}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", default="j2,j3", help="collect,j1,j2,j3 をカンマ区切り")
    ap.add_argument("--max-minutes", type=float, default=COLLECT_MAX_MIN)
    a = ap.parse_args(argv)
    parts = [x.strip() for x in a.part.split(",") if x.strip()]
    bad = [x for x in parts if x not in PARTS]
    if bad:
        ap.error(f"知らない part: {bad}")
    res = {}
    if os.path.exists(OUT_JSON):
        try:
            with open(OUT_JSON, encoding="utf-8") as f:
                res = {k: v for k, v in json.load(f).items() if k in PARTS}
        except (OSError, ValueError):
            res = {}
    res.update({"generated_at": dt.datetime.now(P.JST).isoformat(timespec="minutes"),
                "prereg_file": P.PREREG, "prereg_sha256": P.prereg_sha256()})
    for part in parts:
        print(f"▶ {part}", flush=True)
        try:
            res[part] = PARTS[part](max_minutes=a.max_minutes) if part == "collect" else PARTS[part]()
        except Exception as e:  # noqa: BLE001
            res[part] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
            print(f"  ⚠️ {part} 失敗: {res[part]['error']}", file=sys.stderr)
    if isinstance(res.get("j3f"), dict):
        print(json.dumps(res["j3f"], ensure_ascii=False)[:12000])
    if isinstance(res.get("j3"), list):
        for p in res["j3"]:
            print(json.dumps(p, ensure_ascii=False)[:6000])
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1, default=str)
    md = render_md(res)
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
