# -*- coding: utf-8 -*-
"""新しい柱・第1波（2026-09-27 着手・オーナー決定「今後は投資の成績を上げることを一番の目標に」
「大手と同じことをしてもしょうがない」「明日から第一波の3つをまとめて進めていきましょう」）。

A1 AIの見立てと、その後の値動き（逆指標か）
B1 ゴトー日の仲値（ドル円）
B2 重要な発表の前後（第1段＝FOMC・米CPI・米雇用統計）
B4 くりっく365 の資料の形を調べる（数字の検証はまだしない）

⚠️ 物差しと判定の基準は PILLAR_PREREG.md（事前登録）と下の定数に固定。結果を見てから動かさない。
   出力には事前登録の中身の指紋（sha256）を書き込む＝あとから基準をすり替えていないことを確かめられる。
⚠️ 出力 pillar-lab.json / pillar-lab.md は GitHub 側で生成＝手元から送らない（SYNC禁忌）。
⚠️ エンジン・発火条件・固定オラクル（signal_lab_verify.py）には触れない。読むだけ。

実行: python pillar_lab.py [--part all|a1|b1|b2|b4]   （Actions の pillar-lab.yml から手動で）
"""
import argparse
import datetime as dt
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from exit_rule_backtest import _mean_se_safe, t975

JST = ZoneInfo("Asia/Tokyo")
ET = ZoneInfo("America/New_York")
PREREG = "PILLAR_PREREG.md"
OUT_JSON, OUT_MD = "pillar-lab.json", "pillar-lab.md"
SEED = 20260927
N_PERM = 2000
UA = "Mozilla/5.0 (compatible; marketwatch-jp research; +https://marketwatch-jp.com/)"

# ── A1 AIの見立て ──
A1_SOURCE = "fundamental-context.json"
A1_SPLIT = "2026-08-01"            # 探索＝7月31日まで／確かめ＝8月1日から
A1_MIN_N = 100
A1_MORNING_BEFORE_HOUR = 12        # 朝の便＝日本時間12時より前に作られたもの
A1_VOL_DAYS = 20
A1_HORIZONS = {"24h": (24, 1), "1w": (168, 5)}   # 名前: (時間, ばらつきの日数)
A1_SIGN = {"BULLISH": 1, "BEARISH": -1}

# ── B1 ゴトー日 ──
B1_TICKER = "USDJPY=X"
B1_SUB = ["EURJPY=X", "GBPJPY=X", "AUDJPY=X"]
B1_PRE = (7, 10)                   # 7時の足の始値 → 10時（＝9時の足の終値）
B1_POST = (10, 15)                 # 10時の足の始値 → 15時（＝14時の足の終値）
B1_COST_YEN = 0.003                # 往復の費用 0.3銭
BANK_HOLIDAYS = {(12, 31), (1, 1), (1, 2), (1, 3)}

# ── B2 重要な発表 ──
B2_EQ = ["ES=F", "NQ=F", "NKD=F"]
B2_SUB = ["USDJPY=X", "GC=F", "EURUSD=X"]
B2_SHOCK_RATIO = 2.0
FOMC_URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
BLS_URLS = {"cpi": "https://www.bls.gov/bls/news-release/cpi.htm",
            "nfp": "https://www.bls.gov/bls/news-release/empsit.htm"}
BLS_PREFIX = {"cpi": "cpi", "nfp": "empsit"}
EVENT_TIME_ET = {"fomc": (14, 0), "cpi": (8, 30), "nfp": (8, 30)}
EVENT_NAME = {"fomc": "FOMC（米国の金融政策）", "cpi": "米CPI（消費者物価）", "nfp": "米雇用統計"}

# ── B4 くりっく365（形を調べるだけ）──
B4_URLS = ["https://www.tfx.co.jp/historical/fx/",
           "https://www.click365.jp/service/resorces/",
           "https://www.click365.jp/market.html",
           "https://www.click365.jp/newsfile/news/article/20060710-01"]
B4_WORDS = ["売建玉", "買建玉", "建玉", "売買別", "CSV", "csv", "ダウンロード", "二次利用", "転載", "禁止"]
# 2026-09-27 の1回目の調べで見つかった資料（中身の形＝列・先頭の数行・何年分あるか だけを見る。数字の検証はしない）
B4_FILES = ["https://www.tfx.co.jp/kawase/document/fx_sellbuy.xls",          # 売買別建玉の公表（2006年のお知らせからのリンク）
            "https://www.click365.jp/resorces/doc/weekly_sellbuy.xls",        # 為替売買動向（週次）
            "https://www.click365.jp/resorces/doc/fxfile.xls",                # 日別取引数量/建玉数量（当月）
            "https://www.click365.jp/resorces/doc/monthlyfx.xls",
            "https://www.tfx.co.jp/kawase/document/PRT-010-CSV-003-20260925.CSV",
            "https://www.tfx.co.jp/kawase/document/PRT-010-CSV-016-20260925.CSV"]
# ── B4 本番（2026-09-27 午後に PILLAR_PREREG.md へ追記して登録）──
B4W_URL = "https://www.click365.jp/resorces/doc/weekly_sellbuy.xls"   # 為替売買動向（週次・毎週火曜の取引終了時点）
B4W_MAIN = ["USD/JPY", "EUR/JPY", "GBP/JPY", "AUD/JPY", "EUR/USD", "GBP/USD", "AUD/USD"]   # 監視18銘柄にあるペア
B4W_WINDOW = 52          # 直前52週（その週を含む）の中での順位
B4W_MIN_HIST = 26        # 直前に26週以上の記録がある週だけ
B4W_TAIL = 0.2           # 上位2割・下位2割
B4W_LAG_DAYS = 8         # データの日付の8日後の終値で入る（公表までの日数が分からないため安全側）
B4W_HOLD = 5             # 5本後の終値で出る（20本後は読むための表）
B4W_HOLD_SUB = 20
B4W_SPLIT = "2025-01-01"  # 探索＝2024年まで／確かめ＝2025年から（入る日で分ける）
B4W_MIN_N = 100
B4W_COST = {"JPY": 0.003, "other": 0.00003}   # 往復 0.3銭／0.3ピップ
# 日々の CSV が昔の日付でも同じ名前の形で取れるか（取れる＝過去分を機械で集められる）
B4_ARCHIVE_DATES = ["20250925", "20240925", "20200925", "20150925", "20100924"]

TICKER_NAME = {"NKD=F": "日経225先物", "ES=F": "S&P500先物", "NQ=F": "ナスダック100先物", "GC=F": "金",
               "CL=F": "原油", "USDJPY=X": "ドル円", "EURUSD=X": "ユーロドル", "BTC-USD": "ビットコイン",
               "EURJPY=X": "ユーロ円", "GBPJPY=X": "ポンド円", "AUDJPY=X": "豪ドル円"}


# ════════════════════ 共通 ════════════════════

def yf_ticker(t):
    """ブリーフィングの表記（USDJPY）を Yahoo の表記（USDJPY=X）へ"""
    t = str(t or "").strip()
    if re.fullmatch(r"[A-Z]{6}", t):
        return t + "=X"
    return t


def prereg_sha256(path=PREREG):
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return None


def mean_ci(vals, groups):
    """平均と95%の幅（二方向のまとまり・安全側＝exit_rule_backtest._mean_se_safe）"""
    if len(vals) < 2:
        return {"n": len(vals), "mean": float(vals[0]) if vals else None, "lo": None, "hi": None}
    m, se, t = _mean_se_safe(vals, groups)
    if not math.isfinite(se):
        return {"n": len(vals), "mean": m, "lo": None, "hi": None}
    return {"n": len(vals), "mean": m, "lo": m - t * se, "hi": m + t * se}


def diff_ci(a, b):
    """独立した2群の平均の差（a−b）と95%の幅"""
    a, b = np.asarray(a, float), np.asarray(b, float)
    if len(a) < 2 or len(b) < 2:
        return {"n_a": len(a), "n_b": len(b), "diff": None, "lo": None, "hi": None}
    d = float(a.mean() - b.mean())
    se = math.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
    t = t975(min(len(a), len(b)) - 1)
    return {"n_a": len(a), "n_b": len(b), "mean_a": float(a.mean()), "mean_b": float(b.mean()),
            "diff": d, "lo": d - t * se, "hi": d + t * se}


def _mean(xs):
    xs = list(xs)
    return float(np.mean(xs)) if xs else None


def _ts(t):
    return pd.Timestamp(t).tz_convert("UTC")


def bar_from(bars, t, tol_h=1.0):
    """t 以後に始まる最初の足の位置（t から tol_h 時間以内に始まるものだけ）"""
    idx = bars.index
    t = _ts(t)
    i = int(idx.searchsorted(t))
    if i < len(idx) and idx[i] - t < pd.Timedelta(hours=tol_h):
        return i
    return None


def bar_before(bars, t, tol_h=1.0):
    """t より前に始まった最後の足の位置（t の tol_h 時間前以降に始まったものだけ）"""
    idx = bars.index
    t = _ts(t)
    j = int(idx.searchsorted(t)) - 1
    if j >= 0 and t - idx[j] <= pd.Timedelta(hours=tol_h):
        return j
    return None


def http_get(url, tries=3):
    import gzip
    import urllib.request
    err = None
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html",
                                                       "Accept-Encoding": "identity"})
            with urllib.request.urlopen(req, timeout=30) as r:
                raw = r.read()
            if raw[:2] == b"\x1f\x8b":
                raw = gzip.decompress(raw)
            for enc in ("utf-8", "shift_jis", "cp932"):
                try:
                    return raw.decode(enc)
                except UnicodeDecodeError:
                    continue
            return raw.decode("utf-8", "ignore")
        except Exception as e:  # noqa: BLE001
            err = e
            time.sleep(2 * (k + 1))
    raise err


def fetch(ticker, interval, tries=3, start=None):
    """Yahoo の足。1時間足＝過去730日（添字は UTC）／日足＝過去2年か start から（添字は日付・時刻なし）"""
    import yfinance as yf
    for k in range(tries):
        try:
            if interval == "1h":
                df = yf.download(ticker, period="730d", interval="1h", progress=False, auto_adjust=True)
            else:
                kw = {"start": start} if start else {"period": "2y"}
                df = yf.download(ticker, interval="1d", progress=False, auto_adjust=True, **kw)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df = df.dropna(subset=["Open", "Close"])
            if len(df) > 50:
                ix = pd.to_datetime(df.index)
                if interval == "1h":
                    df.index = ix.tz_localize("UTC") if ix.tz is None else ix.tz_convert("UTC")
                else:
                    df.index = ix.tz_localize(None) if ix.tz is not None else ix
                return df.sort_index()
        except Exception as e:  # noqa: BLE001
            print(f"  ⚠️ {ticker} {interval} 取得失敗 {k + 1}/{tries}: {type(e).__name__}: {str(e)[:80]}",
                  file=sys.stderr)
        time.sleep(2 * (k + 1))
    return None


# ════════════════════ A1 AIの見立て ════════════════════

def load_briefings(path=A1_SOURCE, run=subprocess.run):
    """GitHub の履歴にある見立てをすべて読む → [(作られた時刻 JST, {Yahooの表記: (見立て, 自信度)})]"""
    shas = run(["git", "log", "--format=%H", "--", path], capture_output=True, text=True).stdout.split()
    snaps = {}
    for sha in shas:
        r = run(["git", "show", f"{sha}:{path}"], capture_output=True)
        if r.returncode:
            continue
        try:
            d = json.loads(r.stdout.decode("utf-8") if isinstance(r.stdout, bytes) else r.stdout)
        except (ValueError, UnicodeDecodeError):
            continue
        ga = d.get("generated_at")
        if not ga or ga in snaps:
            continue
        snaps[ga] = {yf_ticker(a.get("ticker")): (str(a.get("bias", "")).upper(), str(a.get("conviction", "")).upper())
                     for a in d.get("assets") or [] if a.get("ticker")}
    out = []
    for ga, m in snaps.items():
        try:
            t = dt.datetime.fromisoformat(ga)
        except ValueError:
            continue
        if t.tzinfo is None:
            t = t.replace(tzinfo=JST)
        out.append((t.astimezone(JST), m))
    return sorted(out, key=lambda x: x[0])


def a1_samples(briefs, horizon):
    """平日の朝の便だけ。24h＝1日1つ（最初の便）／1w＝週の最初の平日の朝の便"""
    seen, out = set(), []
    for t, m in briefs:
        if t.weekday() >= 5 or t.hour >= A1_MORNING_BEFORE_HOUR:
            continue
        key = t.date() if horizon == "24h" else tuple(t.isocalendar())[:2]
        if key in seen:
            continue
        seen.add(key)
        out.append((t, m))
    return out


def window_return(bars, t0, hours):
    """入る＝t0 以後の最初の足の始値／出る＝その足の始まり＋hours より前に始まった最後の足の終値 → 対数の値動き"""
    i0 = bar_from(bars, t0, tol_h=72)
    if i0 is None:
        return None
    start = bars.index[i0]
    i1 = int(bars.index.searchsorted(start + pd.Timedelta(hours=hours))) - 1
    if i1 <= i0:
        return None
    if bars.index[i1] + pd.Timedelta(hours=1) - start < pd.Timedelta(hours=hours * 0.5):
        return None
    p0, p1 = float(bars["Open"].iloc[i0]), float(bars["Close"].iloc[i1])
    if not (p0 > 0 and p1 > 0):
        return None
    return math.log(p1 / p0)


def daily_vol(daily, day, n=A1_VOL_DAYS):
    """入る日の前々日までの n 日の、日々の値動き（対数）のばらつき"""
    if daily is None or not len(daily):
        return None
    c = daily["Close"]
    c = c[np.array([d.date() < day - dt.timedelta(days=1) for d in c.index])]
    v = np.log(np.asarray(c.values[-(n + 1):], float))
    r = np.diff(v)
    if len(r) < n // 2:
        return None
    s = float(np.std(r, ddof=1))
    return s if s > 0 else None


def a1_rows(briefs, bars_by, daily_by, horizon):
    hours, days = A1_HORIZONS[horizon]
    rows = []
    for t, m in a1_samples(briefs, horizon):
        for tk, (bias, conv) in m.items():
            s = A1_SIGN.get(bias)
            if s is None or tk not in bars_by or bars_by[tk] is None:
                continue
            lr = window_return(bars_by[tk], t, hours)
            if lr is None:
                continue
            v = daily_vol(daily_by.get(tk), t.date())
            if not v:
                continue
            raw = lr / (v * math.sqrt(days))
            rows.append({"ticker": tk, "date": t.date().isoformat(), "sign": s, "conv": conv,
                         "z": s * raw, "raw": raw})
    return rows


def perm_p(rows, n_perm=N_PERM, seed=SEED):
    """偽薬：同じ資産の中で強気・弱気の札を日付どうしでランダムに入れ替える（両側の p）"""
    if not rows:
        return None
    rng = np.random.default_rng(seed)
    obs = float(np.mean([r["z"] for r in rows]))
    by = {}
    for r in rows:
        by.setdefault(r["ticker"], ([], []))
        by[r["ticker"]][0].append(r["sign"])
        by[r["ticker"]][1].append(r["raw"])
    groups = [(np.array(s, float), np.array(x, float)) for s, x in by.values()]
    n = len(rows)
    hits = 0
    for _ in range(n_perm):
        tot = 0.0
        for s, x in groups:
            tot += float(np.dot(rng.permutation(s), x))
        if abs(tot / n) >= abs(obs) - 1e-12:
            hits += 1
    return (hits + 1) / (n_perm + 1)


def judge_a1(r):
    if r.get("n", 0) < A1_MIN_N:
        return "件数不足"
    lo, hi, e, l, p = r.get("lo"), r.get("hi"), r.get("early"), r.get("late"), r.get("p_perm")
    if None in (lo, hi, e, l, p):
        return "差なし（偶然の範囲）"
    if hi < 0 and e < 0 and l < 0 and p < 0.05:
        return "逆指標の兆し"
    if lo > 0 and e > 0 and l > 0 and p < 0.05:
        return "順指標の兆し"
    return "差なし（偶然の範囲）"


def a1_stats(rows, split=A1_SPLIT, n_perm=N_PERM, seed=SEED):
    if not rows:
        return {"n": 0, "verdict": "件数不足"}
    res = mean_ci([r["z"] for r in rows], [(r["ticker"], r["date"]) for r in rows])
    early = [r["z"] for r in rows if r["date"] < split]
    late = [r["z"] for r in rows if r["date"] >= split]
    res.update({"early": _mean(early), "late": _mean(late), "n_early": len(early), "n_late": len(late),
                "p_perm": perm_p(rows, n_perm, seed), "long_only": _mean(r["raw"] for r in rows),
                "first": min(r["date"] for r in rows), "last": max(r["date"] for r in rows)})
    res["verdict"] = judge_a1(res)
    res["by_conv"] = {c: {"n": len(v), "mean": _mean(v)} for c in ("HIGH", "MID", "LOW")
                      for v in [[r["z"] for r in rows if r["conv"] == c]] if v}
    res["by_ticker"] = {tk: {"n": len(v), "mean": _mean(v)} for tk in sorted({r["ticker"] for r in rows})
                        for v in [[r["z"] for r in rows if r["ticker"] == tk]]}
    return res


def run_a1():
    briefs = load_briefings()
    tickers = sorted({tk for _, m in briefs for tk in m})
    bars_by = {tk: fetch(tk, "1h") for tk in tickers}
    daily_by = {tk: fetch(tk, "1d") for tk in tickers}
    out = {"briefings": len(briefs), "first": briefs[0][0].isoformat() if briefs else None,
           "last": briefs[-1][0].isoformat() if briefs else None,
           "missing_prices": [tk for tk in tickers if bars_by.get(tk) is None or daily_by.get(tk) is None]}
    for h in A1_HORIZONS:
        out[h] = a1_stats(a1_rows(briefs, bars_by, daily_by, h))
    out["verdict"] = out["24h"]["verdict"]
    return out


# ════════════════════ B1 ゴトー日 ════════════════════

def jp_business_day(d, jp_holidays):
    return d.weekday() < 5 and d not in jp_holidays and (d.month, d.day) not in BANK_HOLIDAYS


def gotobi_dates(start, end, jp_holidays):
    """5日・10日・15日・20日・25日・月末（休みなら前の営業日）→ {日付: '5・10日' か '月末'}"""
    out = {}
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        nxt = dt.date(y + (m == 12), m % 12 + 1, 1)
        last = (nxt - dt.timedelta(days=1)).day
        for day, kind in ((5, "5・10日"), (10, "5・10日"), (15, "5・10日"), (20, "5・10日"), (25, "5・10日"),
                          (last, "月末")):
            d = dt.date(y, m, day)
            while not jp_business_day(d, jp_holidays):
                d -= dt.timedelta(days=1)
            if start <= d <= end:
                out.setdefault(d, kind)
        y, m = nxt.year, nxt.month
    return out


def session_return(bars, d, a, b):
    """その日の a時の足の始値 → b時（＝b−1時の足の終値）。日本時間。単位＝ベーシスポイント。足が欠ければ None"""
    t0 = dt.datetime(d.year, d.month, d.day, a, tzinfo=JST)
    t1 = dt.datetime(d.year, d.month, d.day, b, tzinfo=JST)
    i0, i1 = bar_from(bars, t0), bar_before(bars, t1)
    if i0 is None or i1 is None or i1 < i0:
        return None
    o, c = float(bars["Open"].iloc[i0]), float(bars["Close"].iloc[i1])
    if not (o > 0 and c > 0):
        return None
    return math.log(c / o) * 1e4, o


def b1_rows(bars, jp_holidays):
    days = sorted({ts.astimezone(JST).date() for ts in bars.index})
    bdays = [d for d in days if jp_business_day(d, jp_holidays)]
    if not bdays:
        return []
    gd = gotobi_dates(bdays[0], bdays[-1], jp_holidays)
    rows = []
    for d in bdays:
        pre, post = session_return(bars, d, *B1_PRE), session_return(bars, d, *B1_POST)
        if pre is None or post is None:
            continue
        rows.append({"date": d.isoformat(), "gotobi": d in gd, "kind": gd.get(d), "pre": pre[0], "post": post[0],
                     "cost": B1_COST_YEN / pre[1] * 1e4})
    return rows


def placebo_rank(rows, key, n_perm=N_PERM, seed=SEED):
    """偽薬：ゴトー日でない営業日から同じ日数をランダムに選んだ平均の中で、本物以上が出る割合"""
    g = [r[key] for r in rows if r["gotobi"]]
    o = np.array([r[key] for r in rows if not r["gotobi"]], float)
    if len(g) < 2 or len(o) < len(g):
        return None
    rng = np.random.default_rng(seed)
    obs = float(np.mean(g))
    sims = np.array([o[rng.choice(len(o), len(g), replace=False)].mean() for _ in range(n_perm)])
    return {"upper": float((np.sum(sims >= obs) + 1) / (n_perm + 1)),
            "lower": float((np.sum(sims <= obs) + 1) / (n_perm + 1))}


def judge_b1(r, kind="pre"):
    lo, hi, e, l = r.get("lo"), r.get("hi"), r.get("early"), r.get("late")
    if None in (lo, hi, e, l):
        return "見えない（偶然の範囲）"
    if kind == "pre":
        if lo > 0 and e > 0 and l > 0 and (r.get("net") or 0) > 0:
            return "今も残っている"
        if hi < 0 and e < 0 and l < 0:
            return "逆向き"
        return "見えない（偶然の範囲）"
    if hi < 0 and e < 0 and l < 0:
        return "戻りあり"
    return "見えない（偶然の範囲）"


def b1_stats(rows):
    if not rows:
        return {"n": 0, "verdict": "見えない（偶然の範囲）"}
    mid = sorted(r["date"] for r in rows)[len(rows) // 2]
    out = {"n_days": len(rows), "n_gotobi": sum(r["gotobi"] for r in rows), "split": mid,
           "first": rows[0]["date"], "last": rows[-1]["date"]}
    for key in ("pre", "post"):
        r = diff_ci([x[key] for x in rows if x["gotobi"]], [x[key] for x in rows if not x["gotobi"]])
        halves = []
        for part in ([x for x in rows if x["date"] < mid], [x for x in rows if x["date"] >= mid]):
            d = diff_ci([x[key] for x in part if x["gotobi"]], [x[key] for x in part if not x["gotobi"]])
            halves.append(d.get("diff"))
        r["early"], r["late"] = halves
        r["placebo"] = placebo_rank(rows, key)
        if key == "pre":
            g = [x for x in rows if x["gotobi"]]
            r["net"] = _mean(x["pre"] - x["cost"] for x in g)
            r["cost"] = _mean(x["cost"] for x in g)
        r["verdict"] = judge_b1(r, key)
        out[key] = r
    out["by_kind"] = {k: {"n": len(v), "pre": _mean(x["pre"] for x in v), "post": _mean(x["post"] for x in v)}
                      for k in ("5・10日", "月末") for v in [[x for x in rows if x["kind"] == k]] if v}
    out["verdict"] = out["pre"]["verdict"]
    return out


def run_b1():
    import holidays
    out = {}
    for tk in [B1_TICKER] + B1_SUB:
        bars = fetch(tk, "1h")
        if bars is None:
            out[tk] = {"error": "値動きを取得できず"}
            continue
        years = range(bars.index[0].year - 1, bars.index[-1].year + 2)
        out[tk] = b1_stats(b1_rows(bars, holidays.Japan(years=years)))
    out["verdict"] = out.get(B1_TICKER, {}).get("verdict", "見えない（偶然の範囲）")
    return out


# ════════════════════ B2 重要な発表 ════════════════════

def parse_fomc(html):
    """米連邦準備制度の日程のページから、定例会合の声明の日付だけを取る（臨時・持ち回りは除く）"""
    out = set()
    for block in re.split(r'class="[^"]*fomc-meeting__month', html)[1:]:
        m = re.search(r'fomc-meeting__date[^>]*>([^<]*)<', block)
        if not m:
            continue
        txt = m.group(1).lower()
        if "notation" in txt or "unscheduled" in txt:
            continue
        s = re.search(r'/newsevents/pressreleases/monetary(\d{8})a\.htm', block)
        if s:
            out.add(dt.datetime.strptime(s.group(1), "%Y%m%d").date())
    return sorted(out)


def parse_bls(html, prefix):
    """米労働統計局の過去の発表一覧から、発表日（リンクの名前の月日年）を取る"""
    out = set()
    for mm, dd, yyyy in re.findall(rf'/news\.release/archives/{prefix}_(\d{{2}})(\d{{2}})(\d{{4}})\.htm', html):
        try:
            out.add(dt.date(int(yyyy), int(mm), int(dd)))
        except ValueError:
            pass
    return sorted(out)


def event_time(d, kind):
    hh, mm = EVENT_TIME_ET[kind]
    return dt.datetime(d.year, d.month, d.day, hh, mm, tzinfo=ET)


def b2_window(bars, T):
    """前＝h0 の24時間前の足の始値 → h0 の直前の足の終値／直後＝h0 の足の始値 → h0＋1時間の足の終値（絶対値）。
    h0＝発表時刻を含む足の始まり。単位＝ベーシスポイント"""
    h0 = _ts(T).floor("h")
    i_a = bar_from(bars, h0 - pd.Timedelta(hours=24))
    i_b = bar_before(bars, h0)
    i_c = bar_from(bars, h0)
    i_d = bar_before(bars, h0 + pd.Timedelta(hours=2))
    out = {}
    if i_a is not None and i_b is not None and i_b > i_a:
        out["pre"] = math.log(float(bars["Close"].iloc[i_b]) / float(bars["Open"].iloc[i_a])) * 1e4
    if i_c is not None and i_d is not None and i_d >= i_c:
        out["react"] = abs(math.log(float(bars["Close"].iloc[i_d]) / float(bars["Open"].iloc[i_c])) * 1e4)
    return out


def b2_baseline(bars, kind, exclude):
    """発表が無い平日の、同じ時刻（米東部時間）の同じ窓"""
    days = sorted({ts.astimezone(ET).date() for ts in bars.index})
    pre, react = [], []
    for d in days:
        if d.weekday() >= 5 or d in exclude:
            continue
        w = b2_window(bars, event_time(d, kind))
        if "pre" in w:
            pre.append(w["pre"])
        if "react" in w:
            react.append(w["react"])
    return {"pre": _mean(pre), "react": _mean(react), "n_pre": len(pre), "n_react": len(react)}


def b2_study(bars_by, events, today):
    """events: {種類: [日付]}。① FOMC 前24時間（株価指数3つ）② 発表直後2時間の大きさの倍率"""
    exclude = {d for ds in events.values() for d in ds}
    out = {"counts": {k: len(v) for k, v in events.items()}, "ratio": {}, "pre": {}}
    fomc_rows = []
    for tk, bars in bars_by.items():
        if bars is None:
            continue
        lo_d, hi_d = bars.index[0].astimezone(ET).date(), bars.index[-1].astimezone(ET).date()
        for kind, dates in events.items():
            base = b2_baseline(bars, kind, exclude)
            vals_pre, vals_react = [], []
            for d in dates:
                if not (lo_d < d < hi_d) or d >= today:
                    continue
                w = b2_window(bars, event_time(d, kind))
                if "pre" in w and base["pre"] is not None:
                    vals_pre.append((d, w["pre"] - base["pre"]))
                if "react" in w:
                    vals_react.append(w["react"])
            if vals_react and base["react"]:
                out["ratio"].setdefault(kind, {})[tk] = {"n": len(vals_react), "event": _mean(vals_react),
                                                        "normal": base["react"],
                                                        "ratio": _mean(vals_react) / base["react"]}
            if vals_pre:
                out["pre"].setdefault(kind, {})[tk] = {"n": len(vals_pre), "mean": _mean(v for _, v in vals_pre)}
            if kind == "fomc" and tk in B2_EQ:
                fomc_rows += [{"ticker": tk, "date": d.isoformat(), "v": v} for d, v in vals_pre]
    out["fomc_eq"] = b2_fomc_stats(fomc_rows)
    out["verdict"] = out["fomc_eq"]["verdict"]
    out["shock"] = {kind: sorted(tk for tk, r in m.items() if r["ratio"] >= B2_SHOCK_RATIO)
                    for kind, m in out["ratio"].items()}
    return out


def b2_fomc_stats(rows):
    if not rows:
        return {"n": 0, "n_events": 0, "verdict": "見えない"}
    res = mean_ci([r["v"] for r in rows], [(r["date"], r["date"]) for r in rows])
    dates = sorted({r["date"] for r in rows})
    mid = dates[len(dates) // 2]
    res["n_events"] = len(dates)
    res["split"] = mid
    res["early"] = _mean(r["v"] for r in rows if r["date"] < mid)
    res["late"] = _mean(r["v"] for r in rows if r["date"] >= mid)
    ok = None not in (res.get("lo"), res["early"], res["late"])
    res["verdict"] = ("FOMC前の上昇が今も見える" if ok and res["lo"] > 0 and res["early"] > 0 and res["late"] > 0
                      else "見えない")
    return res


def run_b2(today=None):
    today = today or dt.datetime.now(JST).date()
    events, sources = {}, {}
    try:
        events["fomc"] = parse_fomc(http_get(FOMC_URL))
        sources["fomc"] = "ok" if events["fomc"] else "解析0件"
    except Exception as e:  # noqa: BLE001
        sources["fomc"] = f"取得できず: {type(e).__name__}"
    for k, url in BLS_URLS.items():
        try:
            events[k] = parse_bls(http_get(url), BLS_PREFIX[k])
            sources[k] = "ok" if events[k] else "解析0件"
        except Exception as e:  # noqa: BLE001
            sources[k] = f"取得できず: {type(e).__name__}"
    events = {k: v for k, v in events.items() if v}
    bars_by = {tk: fetch(tk, "1h") for tk in B2_EQ + B2_SUB}
    out = b2_study(bars_by, events, today)
    out["sources"] = sources
    out["recent_dates"] = {k: [d.isoformat() for d in v if d < today][-3:] for k, v in events.items()}
    return out


# ════════════════════ B4 くりっく365（形を調べるだけ）════════════════════

def b4_probe():
    """ページを取りに行き、資料のリンク・キーワードの数・二次利用の決まりの周辺だけを残す（本文は保存しない）"""
    out = []
    for url in B4_URLS:
        try:
            html = http_get(url)
        except Exception as e:  # noqa: BLE001
            out.append({"url": url, "ok": False, "error": f"{type(e).__name__}: {str(e)[:120]}"})
            continue
        text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"(?is)<(script|style).*?</\1>", " ", html)))
        links = re.findall(r'href="([^"]+)"[^>]*>([^<]{0,80})<', html)
        keep = [(h, t.strip()) for h, t in links
                if re.search(r"csv|xls|zip|pdf|建玉|日報|売買|historical|data|download", h + t, re.I)]
        terms = []
        for w in ("二次利用", "転載", "著作権", "利用規約"):
            for m in re.finditer(w, text):
                terms.append(text[max(0, m.start() - 60): m.end() + 80])
        out.append({"url": url, "ok": True, "chars": len(html), "keywords": {w: text.count(w) for w in B4_WORDS},
                    "links": keep[:60], "terms": terms[:6], "forms": re.findall(r"<form[^>]*>", html)[:5]})
    return out


def http_get_bytes(url, tries=2):
    """(HTTPの状態, 中身)。見つからない（404 など）は1回で諦める"""
    import urllib.error
    import urllib.request
    err = None
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "identity"})
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, b""
        except Exception as e:  # noqa: BLE001
            err = e
            time.sleep(2 * (k + 1))
    raise err


def file_kind(raw):
    if raw[:4] == b"\xd0\xcf\x11\xe0":
        return "xls"
    if raw[:2] == b"PK":
        return "xlsx"
    if raw[:5] == b"%PDF-":
        return "pdf"
    head = raw[:400].lower()
    if b"<html" in head or b"<!doctype" in head:
        return "html"
    return "text"


def _cell(v):
    s = str(v).strip()
    return s[:24]


def summarize_table(raw, kind):
    """表の形だけ：シート名・行数・先頭6行・末尾2行（各行は先頭12列・1セル24文字まで）"""
    out = {"kind": kind, "bytes": len(raw)}
    if kind == "text":
        text = None
        for enc in ("cp932", "utf-8"):
            try:
                text = raw.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        lines = (text or raw.decode("utf-8", "ignore")).splitlines()
        rows = [ln.split(",")[:12] for ln in lines]
        out.update({"rows": len(rows), "head": [[_cell(c) for c in r] for r in rows[:6]],
                    "tail": [[_cell(c) for c in r] for r in rows[-2:]]})
        return out
    if kind in ("xls", "xlsx"):
        import io
        sheets = pd.read_excel(io.BytesIO(raw), sheet_name=None, header=None,
                               engine="xlrd" if kind == "xls" else "openpyxl")
        out["sheets"] = {}
        for name, df in list(sheets.items())[:8]:
            df = df.dropna(how="all")
            rows = df.iloc[:, :12].astype(str).values.tolist()
            out["sheets"][str(name)[:30]] = {"rows": len(rows), "cols": int(df.shape[1]),
                                             "head": [[_cell(c) for c in r] for r in rows[:6]],
                                             "tail": [[_cell(c) for c in r] for r in rows[-2:]]}
        return out
    return out


def b4_files():
    """1回目で見つかった資料の中身の形と、日々の CSV が何年前まで同じ名前で取れるか"""
    files = []
    for url in B4_FILES:
        try:
            st, raw = http_get_bytes(url)
        except Exception as e:  # noqa: BLE001
            files.append({"url": url, "ok": False, "error": f"{type(e).__name__}: {str(e)[:120]}"})
            continue
        if st != 200 or not raw:
            files.append({"url": url, "ok": False, "error": f"HTTP {st}"})
            continue
        try:
            files.append(dict(summarize_table(raw, file_kind(raw)), url=url, ok=True))
        except Exception as e:  # noqa: BLE001
            files.append({"url": url, "ok": False, "kind": file_kind(raw), "bytes": len(raw),
                          "error": f"読めず: {type(e).__name__}: {str(e)[:120]}"})
    archive = {}
    for d in B4_ARCHIVE_DATES:
        for kind in ("003", "016"):
            url = f"https://www.tfx.co.jp/kawase/document/PRT-010-CSV-{kind}-{d}.CSV"
            try:
                st, raw = http_get_bytes(url)
                archive[f"{kind}-{d}"] = {"status": st, "bytes": len(raw)}
            except Exception as e:  # noqa: BLE001
                archive[f"{kind}-{d}"] = {"status": None, "error": type(e).__name__}
    return {"files": files, "archive": archive}


def parse_weekly_sellbuy(df):
    """為替売買動向（週次）の表 → {'USD/JPY': [(日付, 売り, 買い), ...]}。
    形（2026-09-27 に確認）：1行目にペア名（売りの列にだけ書いてある）、次の行に 日付/売り/買い、その次に date/sell/buy、
    以降が1週1行（1列目が MM/DD/YYYY）"""
    vals = df.values.tolist()
    pair_row = next(i for i, r in enumerate(vals)
                    if sum(1 for c in r if re.fullmatch(r"[A-Z]{3}/[A-Z]{3}", str(c).strip())) >= 3)
    side_row = next(i for i in range(pair_row + 1, len(vals))
                    if any(str(c).strip() in ("売り", "sell") for c in vals[i]))
    cols, cur = {}, None
    for c, name in enumerate(vals[pair_row]):
        name = str(name).strip()
        if re.fullmatch(r"[A-Z]{3}/[A-Z]{3}", name):
            cur = name
        side = str(vals[side_row][c]).strip()
        if cur and side in ("売り", "買い"):
            cols.setdefault(cur, {})["sell" if side == "売り" else "buy"] = c
    out = {}
    for r in vals[side_row + 1:]:
        raw = r[0]
        d = None
        if isinstance(raw, (dt.date, pd.Timestamp)):
            d = pd.Timestamp(raw).date()
        else:
            for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%Y/%m/%d"):
                try:
                    d = dt.datetime.strptime(str(raw).strip()[:10], fmt).date()
                    break
                except ValueError:
                    continue
        if d is None:
            continue
        for pair, cc in cols.items():
            if "sell" not in cc or "buy" not in cc:
                continue
            try:
                sell, buy = float(r[cc["sell"]]), float(r[cc["buy"]])
            except (TypeError, ValueError):
                continue
            if math.isfinite(sell) and math.isfinite(buy) and sell + buy > 0:
                out.setdefault(pair, []).append((d, sell, buy))
    return {k: sorted(v) for k, v in out.items()}


def b4w_signals(series):
    """[(日付, 売り, 買い)] → [(日付, ＋1 か −1)]。買いの割合が直前52週の中で上位2割なら −1、下位2割なら ＋1"""
    ratios = [(d, b / (s + b)) for d, s, b in series]
    out = []
    for i, (d, x) in enumerate(ratios):
        past = [y for _, y in ratios[max(0, i - B4W_WINDOW + 1):i]]
        if len(past) < B4W_MIN_HIST:
            continue
        rank = sum(1 for y in past if y < x) / len(past)
        if rank >= 1 - B4W_TAIL:
            out.append((d, -1))
        elif rank <= B4W_TAIL:
            out.append((d, 1))
    return out


def b4w_rows(parsed, daily_by):
    rows = []
    for pair, series in parsed.items():
        daily = daily_by.get(pair)
        if daily is None or not len(daily):
            continue
        days = [x.date() for x in daily.index]
        close = np.asarray(daily["Close"].values, float)
        for d, s in b4w_signals(series):
            entry = d + dt.timedelta(days=B4W_LAG_DAYS)
            i0 = int(np.searchsorted(np.array(days, dtype="datetime64[D]"), np.datetime64(entry)))
            if i0 < 21 or i0 + B4W_HOLD >= len(close):
                continue
            r = np.diff(np.log(close[i0 - 20:i0 + 1]))
            v = float(np.std(r, ddof=1))
            if not v > 0:
                continue
            lr5 = math.log(close[i0 + B4W_HOLD] / close[i0])
            cost = (B4W_COST["JPY"] if pair.endswith("/JPY") else B4W_COST["other"]) / close[i0] * 1e4
            row = {"ticker": pair, "date": days[i0].isoformat(), "sign": s, "conv": "",
                   "raw": lr5 / (v * math.sqrt(B4W_HOLD)), "net_bps": s * lr5 * 1e4 - cost, "cost_bps": cost,
                   "main": pair in B4W_MAIN}
            row["z"] = s * row["raw"]
            if i0 + B4W_HOLD_SUB < len(close):
                row["raw20"] = math.log(close[i0 + B4W_HOLD_SUB] / close[i0]) / (v * math.sqrt(B4W_HOLD_SUB))
            rows.append(row)
    return rows


def judge_b4w(r):
    if r.get("n", 0) < B4W_MIN_N:
        return "件数不足"
    lo, hi, e, l, p, net = (r.get(k) for k in ("lo", "hi", "early", "late", "p_perm", "net_bps"))
    if None in (lo, hi, e, l, p, net):
        return "差なし（偶然の範囲）"
    if lo > 0 and e > 0 and l > 0 and p < 0.05 and net > 0:
        return "個人の逆張りの兆し"
    if hi < 0 and e < 0 and l < 0 and p < 0.05:
        return "個人と同じ向きの兆し"
    return "差なし（偶然の範囲）"


def b4w_stats(rows):
    main = [r for r in rows if r["main"]]
    res = a1_stats(main, split=B4W_SPLIT) if main else {"n": 0}
    res.pop("by_conv", None)
    res["net_bps"] = _mean(r["net_bps"] for r in main)
    res["cost_bps"] = _mean(r["cost_bps"] for r in main)
    res["verdict"] = judge_b4w(res)
    sub = [dict(r, z=r["sign"] * r["raw20"]) for r in main if "raw20" in r]
    res["hold20"] = {"n": len(sub), "mean": _mean(r["z"] for r in sub)}
    others = [r for r in rows if not r["main"]]
    res["others"] = {pair: {"n": len(v), "mean": _mean(v)} for pair in sorted({r["ticker"] for r in others})
                     for v in [[r["z"] for r in others if r["ticker"] == pair]]}
    res["n_long_side"] = sum(1 for r in main if r["sign"] > 0)
    res["n_short_side"] = sum(1 for r in main if r["sign"] < 0)
    return res


def run_b4w():
    import io
    st, raw = http_get_bytes(B4W_URL)
    if st != 200 or not raw:
        return {"error": f"資料を取得できず（HTTP {st}）"}
    df = pd.read_excel(io.BytesIO(raw), sheet_name=0, header=None, engine="xlrd")
    parsed = parse_weekly_sellbuy(df)
    daily_by = {}
    for pair in parsed:
        tk = pair.replace("/", "") + "=X"
        daily_by[pair] = fetch(tk, "1d", start="2021-06-01")
    out = {"source": B4W_URL, "pairs": len(parsed),
           "weeks": {p: {"n": len(v), "first": v[0][0].isoformat(), "last": v[-1][0].isoformat()}
                     for p, v in parsed.items() if p in B4W_MAIN},
           "missing_prices": [p for p in parsed if daily_by.get(p) is None]}
    out.update(b4w_stats(b4w_rows(parsed, daily_by)))
    return out


# ════════════════════ 出力 ════════════════════

def _f(x, d=3, sign=True):
    if x is None:
        return "—"
    return f"{x:+.{d}f}" if sign else f"{x:.{d}f}"


def render_md(res):
    L = ["# 新しい柱・第1波の結果", "",
         f"作成: {res['generated_at']}（GitHub Actions で計算）。事前登録＝`{PREREG}`（指紋 sha256 `{(res.get('prereg_sha256') or '')[:16]}…`）。",
         "判定の基準は事前登録どおり。**どれも売買の決まりではない**＝兆しが出ても、登録後のデータだけで数え直してから柱にする。", ""]
    a1 = res.get("a1")
    if a1:
        L += ["## A1 AIの見立てと、その後の値動き", ""]
        if a1.get("error"):
            L += [f"- ⚠️ 計算できず: {a1['error']}", ""]
        else:
            r = a1["24h"]
            L += [f"- **判定（24時間）：{r['verdict']}**",
                  f"- 使った見立て {a1['briefings']} 便（{(a1.get('first') or '')[:10]}〜{(a1.get('last') or '')[:10]}）",
                  "- 値＝（強気なら＋1・弱気なら−1）×その後の値動き÷普段のばらつき。**マイナスなら逆指標寄り**", "",
                  "| 物差し | 件数 | 平均 | 95%の幅 | 前半（7月まで） | 後半（8月から） | 偽薬との比較 p |",
                  "|---|---:|---:|---|---:|---:|---:|"]
            for h, name in (("24h", "24時間後"), ("1w", "1週間後（読むための表）")):
                x = a1.get(h) or {}
                L.append(f"| {name} | {x.get('n', 0)} | {_f(x.get('mean'))} | {_f(x.get('lo'))}〜{_f(x.get('hi'))} | "
                         f"{_f(x.get('early'))}（{x.get('n_early', 0)}件） | {_f(x.get('late'))}（{x.get('n_late', 0)}件） | "
                         f"{_f(x.get('p_perm'), 3, False)} |")
            L += ["", f"- 参考：見立てに関係なく「いつも買い」だった場合の平均（24時間）＝{_f(r.get('long_only'))}", ""]
            if r.get("by_conv"):
                L += ["| 自信度 | 件数 | 平均 |", "|---|---:|---:|"]
                L += [f"| {c} | {v['n']} | {_f(v['mean'])} |" for c, v in r["by_conv"].items()]
                L.append("")
            if r.get("by_ticker"):
                L += ["| 資産 | 件数 | 平均 |", "|---|---:|---:|"]
                L += [f"| {TICKER_NAME.get(tk, tk)} | {v['n']} | {_f(v['mean'])} |" for tk, v in r["by_ticker"].items()]
                L.append("")
            if a1.get("missing_prices"):
                L += [f"- 値動きを取れなかった資産: {', '.join(a1['missing_prices'])}", ""]
    b1 = res.get("b1")
    if b1:
        L += ["## B1 ゴトー日の仲値（ドル円）", ""]
        u = b1.get(B1_TICKER) or {}
        if u.get("error") or "pre" not in u:
            L += [f"- ⚠️ 計算できず: {u.get('error', 'データ不足')}", ""]
        else:
            L += [f"- **判定（仲値にかけて＝7時→10時）：{u['pre']['verdict']}**／仲値のあと（10時→15時）：{u['post']['verdict']}",
                  f"- 営業日 {u['n_days']} 日（うちゴトー日 {u['n_gotobi']} 日・{u['first']}〜{u['last']}・前半／後半の境 {u['split']}）",
                  "- 単位＝ベーシスポイント（0.01%）。差＝ゴトー日の平均−ほかの日の平均", "",
                  "| 窓 | ゴトー日の平均 | ほかの日の平均 | 差 | 95%の幅 | 前半の差 | 後半の差 | 偽薬で本物以上が出る割合 |",
                  "|---|---:|---:|---:|---|---:|---:|---:|"]
            for key, name in (("pre", "7時→10時"), ("post", "10時→15時")):
                x = u[key]
                pl = x.get("placebo") or {}
                side = pl.get("upper") if key == "pre" else pl.get("lower")
                L.append(f"| {name} | {_f(x.get('mean_a'), 2)} | {_f(x.get('mean_b'), 2)} | {_f(x.get('diff'), 2)} | "
                         f"{_f(x.get('lo'), 2)}〜{_f(x.get('hi'), 2)} | {_f(x.get('early'), 2)} | {_f(x.get('late'), 2)} | "
                         f"{_f(side, 3, False)} |")
            L += ["", f"- ゴトー日だけ7時に買って10時に売った場合の平均：費用前 {_f(u['pre'].get('mean_a'), 2)}／"
                      f"費用（0.3銭）{_f(u['pre'].get('cost'), 2, False)}／**費用後 {_f(u['pre'].get('net'), 2)}**", ""]
            if u.get("by_kind"):
                L += ["| 種類 | 日数 | 7時→10時 | 10時→15時 |", "|---|---:|---:|---:|"]
                L += [f"| {k} | {v['n']} | {_f(v['pre'], 2)} | {_f(v['post'], 2)} |" for k, v in u["by_kind"].items()]
                L.append("")
        subs = [(tk, b1.get(tk)) for tk in B1_SUB if isinstance(b1.get(tk), dict) and "pre" in b1.get(tk)]
        if subs:
            L += ["読むための表（ほかの円のペア・7時→10時の差）", "", "| ペア | 差 | 95%の幅 |", "|---|---:|---|"]
            L += [f"| {TICKER_NAME.get(tk, tk)} | {_f(x['pre'].get('diff'), 2)} | {_f(x['pre'].get('lo'), 2)}〜{_f(x['pre'].get('hi'), 2)} |"
                  for tk, x in subs]
            L.append("")
    b2 = res.get("b2")
    if b2:
        L += ["## B2 重要な発表の前後（第1段＝FOMC・米CPI・米雇用統計）", ""]
        if b2.get("error"):
            L += [f"- ⚠️ 計算できず: {b2['error']}", ""]
        else:
            f = b2.get("fomc_eq") or {}
            L += [f"- **判定①（FOMC前24時間・株価指数3つ）：{f.get('verdict', '—')}**（{f.get('n_events', 0)} 回分。回数が少なく判定力は弱い）",
                  f"- 平均の差（普段の同じ窓との差・ベーシスポイント）＝{_f(f.get('mean'), 1)}（95%の幅 {_f(f.get('lo'), 1)}〜{_f(f.get('hi'), 1)}・"
                  f"前半 {_f(f.get('early'), 1)}／後半 {_f(f.get('late'), 1)}）",
                  f"- 日程の取得：{', '.join(f'{EVENT_NAME[k]}={v}' for k, v in (b2.get('sources') or {}).items())}", "",
                  "② 発表直後2時間の値動きの大きさ（普段の同じ時間帯の何倍か）。**2倍以上＝発表をまたぐ建玉は損切り幅が足りなくなりやすい**", "",
                  "| 発表 | 銘柄 | 回数 | 発表時 | 普段 | 倍率 |", "|---|---|---:|---:|---:|---:|"]
            for kind, m in (b2.get("ratio") or {}).items():
                for tk, r in m.items():
                    mark = " ⚠️" if r["ratio"] >= B2_SHOCK_RATIO else ""
                    L.append(f"| {EVENT_NAME.get(kind, kind)} | {TICKER_NAME.get(tk, tk)} | {r['n']} | {_f(r['event'], 1, False)} | "
                             f"{_f(r['normal'], 1, False)} | {r['ratio']:.1f}倍{mark} |")
            L.append("")
    b4 = res.get("b4")
    if b4:
        L += ["## B4 くりっく365（資料の形を調べただけ）", ""]
        for p in b4:
            if not p.get("ok"):
                L.append(f"- {p['url']}：取得できず（{p.get('error', '')}）")
            else:
                kw = ", ".join(f"{k}={v}" for k, v in p["keywords"].items() if v)
                L.append(f"- {p['url']}：資料らしいリンク {len(p['links'])} 件／キーワード {kw or 'なし'}／フォーム {len(p['forms'])} 個")
        L.append("")
    bf = res.get("b4_files")
    if bf:
        L += ["### B4 資料の中身の形（2回目の調べ・数字の検証はしない）", ""]
        for f in bf.get("files") or []:
            if not f.get("ok"):
                L.append(f"- {f['url']}：取得できず（{f.get('error', '')}）")
            elif f.get("sheets"):
                sh = "、".join(f"{k}（{v['rows']}行×{v['cols']}列）" for k, v in f["sheets"].items())
                L.append(f"- {f['url']}：{f['kind']}・シート {sh}")
            else:
                L.append(f"- {f['url']}：{f['kind']}・{f.get('rows', '—')}行")
        arch = bf.get("archive") or {}
        if arch:
            L.append("- 日々の CSV を昔の日付で取れるか：" + "、".join(f"{k}={v.get('status')}" for k, v in arch.items()))
        L.append("")
    w = res.get("b4w")
    if w:
        L += ["## B4 くりっく365 の個人の偏りと、その後の値動き（2026-09-27 午後に追記した登録）", ""]
        if w.get("error"):
            L += [f"- ⚠️ 計算できず: {w['error']}", ""]
        else:
            L += [f"- **判定（主なペア・5本後）：{w.get('verdict')}**",
                  f"- 値＝（買いに偏った週は−1・売りに偏った週は＋1）×その後の値動き÷普段のばらつき。**プラスなら個人の逆が当たり**",
                  f"- 件数 {w.get('n', 0)}（上を予想 {w.get('n_long_side', 0)}・下を予想 {w.get('n_short_side', 0)}）・平均 {_f(w.get('mean'))}"
                  f"（95%の幅 {_f(w.get('lo'))}〜{_f(w.get('hi'))}）・前半（2024年まで）{_f(w.get('early'))}（{w.get('n_early', 0)}件）／"
                  f"後半（2025年から）{_f(w.get('late'))}（{w.get('n_late', 0)}件）・偽薬との比較 p={_f(w.get('p_perm'), 3, False)}",
                  f"- 費用を引いた平均＝{_f(w.get('net_bps'), 1)} ベーシスポイント（費用 {_f(w.get('cost_bps'), 2, False)}）"
                  f"／20本後（読むための表）{_f((w.get('hold20') or {}).get('mean'))}（{(w.get('hold20') or {}).get('n', 0)}件）", ""]
            if w.get("by_ticker"):
                L += ["| ペア | 件数 | 平均 |", "|---|---:|---:|"]
                L += [f"| {k} | {v['n']} | {_f(v['mean'])} |" for k, v in w["by_ticker"].items()]
                L.append("")
            if w.get("others"):
                L.append("読むための表（監視外のペア）：" + "、".join(f"{k} {_f(v['mean'])}（{v['n']}件）"
                                                          for k, v in w["others"].items() if v["n"]))
                L.append("")
            L.append("- 生の建玉の数字は載せない（資料の二次利用の決まりが未確認のため）")
            L.append("")
    L += ["---", "", "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。"]
    return "\n".join(L) + "\n"


# (--part の名前, 出力の中の名前, 関数)
PARTS = [("a1", "a1", run_a1), ("b1", "b1", run_b1), ("b2", "b2", run_b2), ("b4", "b4", b4_probe),
         ("b4f", "b4_files", b4_files), ("b4w", "b4w", run_b4w)]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", default="all", choices=["all", "a1", "b1", "b2", "b4", "b4f", "b4w"])
    a = ap.parse_args(argv)
    res = {"generated_at": dt.datetime.now(JST).isoformat(timespec="minutes"),
           "prereg_file": PREREG, "prereg_sha256": prereg_sha256()}
    if os.path.exists(OUT_JSON):
        try:
            with open(OUT_JSON, encoding="utf-8") as f:
                prev = json.load(f)
            for part, k, _ in PARTS:
                if k in prev and a.part not in ("all", part):
                    res[k] = prev[k]
        except (OSError, ValueError):
            pass
    for part, key, fn in PARTS:
        if a.part not in ("all", part):
            continue
        print(f"▶ {part}", flush=True)
        try:
            res[key] = fn()
        except Exception as e:  # noqa: BLE001
            res[key] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
            print(f"  ⚠️ {part} 失敗: {res[key]['error']}", file=sys.stderr)
    if isinstance(res.get("b4_files"), dict):
        print(json.dumps(res["b4_files"], ensure_ascii=False)[:12000])
    if "b4" in res and isinstance(res["b4"], list):
        for p in res["b4"]:     # 手で読むため、ログにだけ詳しく出す（本文は保存しない）
            print(json.dumps(p, ensure_ascii=False)[:4000])
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1, default=str)
    md = render_md(res)
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
