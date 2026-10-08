# -*- coding: utf-8 -*-
"""X 為替の時計の癖（第3波）。2026-10-07 登録・オーナー「FX短期トレードの期待値向上の研究を加速させてください」。

物差しと判定は PILLAR_PREREG.md「X 為替の時計の癖（第3波）」に固定（計算より先にコミット）。結果を見てから動かさない。
値段は為替の値段の置き場（fx_bars.py・Dukascopy の1時間足・売値と買値・12ペア×2012年から）。

- X1 月曜の窓を埋める向き（12ペア）       Dao, McGroarty & Urquhart (2016)・日本の「月曜の窓埋め」
- X2 ロンドンの値決めのあと、ドルを売る      Krohn, Mueller & Whelan (2024)
- X3 ECB の値決めの前、ドルを買う
- X4 東京の値決め（仲値）の前、ドルを買う
- X5 FOMC の発表の日、ドルを売る           Mueller, Tahbaz-Salehi & Vedolin (2017)

使い方:  python fx_clock_lab.py --check   （点検だけ・損益は出さない）
         python fx_clock_lab.py           （1回だけ数えて fx-clock-lab.json / .md を書く）
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

import fx_bars as FB

UTC = dt.timezone.utc
LON = ZoneInfo("Europe/London")
NY = ZoneInfo("America/New_York")
JST = dt.timezone(dt.timedelta(hours=9))
START, END = "2012-01-02", "2026-09-30"
HALF, RECENT = "2019-01-01", "2021-01-01"
USD_BUY = {"EURUSD": -1, "GBPUSD": -1, "AUDUSD": -1, "NZDUSD": -1, "USDJPY": 1, "USDCHF": 1, "USDCAD": 1}   # ドル買いの向き
FIXED_PIPS = {"JPY": 0.8 * 1.5, "other": 1.2 * 1.5}       # S1 と同じ約束（往復）
MAX_SPREAD_PIPS = 100                                     # これを超える差・売値＞買値の足は使わない
MIN_PAIRS = 5
GAP_MIN, GAP_READ = 0.25, 0.10
WEEK_GAP_H = 36
ATR_DAYS, ATR_MIN_BARS = 20, 20
EXIT_X1_UTC_H = 19                                        # 月曜 19:00 UTC に始まる足の終値で出る
MIN_N = {"X1": 300, "X2": 300, "X3": 300, "X4": 300, "X5": 80}
N_BOOT, ALPHA, SEED = 10000, 0.01, 20261012
MISSING_MAX = 0.05
VERDICTS = ("◎ 費用のあとも残っている", "◯ 傾向", "差なし", "件数不足")
SEEN_NOTE = "癖は見えるが費用で消える"
TITLE = {"X1": "月曜の窓を埋める向き（窓が直近20日の1日の値幅の0.25以上・月曜 0時 UTC に入り、金曜の終値か 20時 UTC で出る・12ペア）",
         "X2": "ロンドンの値決めのあと、ドルを売る（ロンドン 16:00→20:00・ドルのペア7つ）",
         "X3": "ECB の値決めの前、ドルを買う（ロンドン 11:00→13:00・ドルのペア7つ）",
         "X4": "東京の値決め（仲値）の前、ドルを買う（日本時間 8:00→10:00・ドルのペア7つ）",
         "X5": "FOMC の発表の日、ドルを売る（ロンドン 08:00→ニューヨーク 16:00・ドルのペア7つ）"}
FOMC_CUR = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
FOMC_HIST = "https://www.federalreserve.gov/monetarypolicy/fomchistorical{y}.htm"
OUT_JSON, OUT_MD = "fx-clock-lab.json", "fx-clock-lab.md"


def pip(pair):
    return FB.pip(pair)


def fixed_cost(pair):
    return FIXED_PIPS["JPY" if pair.endswith("JPY") else "other"] * pip(pair)


def prereg_sha(path="PILLAR_PREREG.md"):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# ════════════════════ 足の下ごしらえ ════════════════════

def prep(df, pair):
    """中値の始高安終・売り買いの差（始値・終値）を足す。差がおかしい足は落とす → (DataFrame, 落とした数)"""
    if df.empty:
        return df.assign(mo=[], mh=[], ml=[], mc=[], so=[], sc=[]), 0
    d = pd.DataFrame(index=df.index)
    d["mo"] = (df["bo"] + df["ao"]) / 2
    d["mh"] = (df["bh"] + df["ah"]) / 2
    d["ml"] = (df["bl"] + df["al"]) / 2
    d["mc"] = (df["bc"] + df["ac"]) / 2
    d["so"] = df["ao"] - df["bo"]
    d["sc"] = df["ac"] - df["bc"]
    lim = MAX_SPREAD_PIPS * pip(pair)
    bad = (d["so"] < 0) | (d["sc"] < 0) | (d["so"] > lim) | (d["sc"] > lim)
    d = d[~bad]
    d = d[(d.index >= pd.Timestamp(START, tz="UTC")) & (d.index < pd.Timestamp(END, tz="UTC") + pd.Timedelta(days=1))]
    return d, int(bad.sum())


def trade_arrays(d, pair, t_in, t_out, sign):
    """入る足の始まり t_in・出る足の始まり t_out（UTC の DatetimeIndex）→ 費用前・費用後（bp）の配列（無い足は NaN）"""
    e = d.reindex(t_in)
    x = d.reindex(t_out)
    mo, mc = e["mo"].to_numpy(), x["mc"].to_numpy()
    gross = sign * (mc / mo - 1) * 1e4
    cost_px = np.maximum(fixed_cost(pair), (e["so"].to_numpy() + x["sc"].to_numpy()) / 2)
    cost = cost_px / mo * 1e4
    return gross, gross - cost, cost


# ════════════════════ 日の一覧 ════════════════════

def weekdays(start=START, end=END):
    d = pd.date_range(start, end, freq="D")
    return [x.date() for x in d if x.weekday() < 5]


def easter(y):
    from dateutil.easter import easter as _e
    return _e(y)


def target_holidays(years):
    out = set()
    for y in years:
        e = easter(y)
        out |= {dt.date(y, 1, 1), e - dt.timedelta(days=2), e + dt.timedelta(days=1), dt.date(y, 5, 1), dt.date(y, 12, 25), dt.date(y, 12, 26)}
    return out


def tokyo_bank_holidays(years):
    import holidays
    out = set(holidays.Japan(years=list(years)).keys())
    for y in years:
        out |= {dt.date(y, 12, 31), dt.date(y, 1, 1), dt.date(y, 1, 2), dt.date(y, 1, 3)}
    return out


def local_bar(days, hour, tz):
    """その地域の日付 days の hour 時に始まる足（UTC）"""
    return pd.DatetimeIndex([pd.Timestamp(dt.datetime.combine(d, dt.time(hour)), tz=tz).tz_convert("UTC") for d in days])


def fix_windows(kind, days):
    """問いごとの（入る足, 出る足）。kind: X2 X3 X4 X5"""
    if kind == "X2":
        return local_bar(days, 16, LON), local_bar(days, 19, LON)
    if kind == "X3":
        return local_bar(days, 11, LON), local_bar(days, 12, LON)
    if kind == "X4":
        return local_bar(days, 8, JST), local_bar(days, 9, JST)
    if kind == "X5":
        return local_bar(days, 8, LON), local_bar(days, 15, NY)
    raise ValueError(kind)


def days_for(kind, fomc=None):
    wd = weekdays()
    years = range(int(START[:4]), int(END[:4]) + 1)
    if kind == "X2":
        return wd
    if kind == "X3":
        h = target_holidays(years)
        return [d for d in wd if d not in h]
    if kind == "X4":
        h = tokyo_bank_holidays(years)
        return [d for d in wd if d not in h]
    if kind == "X5":
        return sorted(d for d in (fomc or []) if pd.Timestamp(START).date() <= d <= pd.Timestamp(END).date())
    raise ValueError(kind)


# ════════════════════ FOMC の日（一次情報） ════════════════════

def http_get(url, opener=None):
    op = opener or (lambda req: urllib.request.urlopen(req, timeout=30))
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research)", "Accept": "text/html"})
    with op(req) as r:
        return r.read().decode("utf-8", "replace")


def parse_fomc_current(html):
    """日程のページ（直近5年ほど）：定例会合の声明の日（臨時・持ち回りは除く）"""
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


def parse_fomc_hist(html):
    """年ごとの過去のページ：見出し「… Meeting - 年」の欄の声明の日（unscheduled・cancelled・notation・conference call は除く）"""
    out = set()
    for block in re.split(r'<h5 class="panel-heading', html)[1:]:
        head = re.search(r'>([^<]*)</h5>', block)
        if not head:
            continue
        h = head.group(1).lower()
        if "meeting" not in h or any(w in h for w in ("unscheduled", "cancel", "notation", "conference call")):
            continue
        s = re.search(r'monetary(\d{8})a\.htm', block)
        if s:
            out.add(dt.datetime.strptime(s.group(1), "%Y%m%d").date())
    return sorted(out)


def fomc_dates(opener=None):
    """→ (日付の一覧, 年ごとの状態)。取れない年は「取得できず」として数えない"""
    dates, status = set(), {}
    try:
        cur = parse_fomc_current(http_get(FOMC_CUR, opener))
    except Exception as e:  # noqa: BLE001
        cur, status["current"] = [], f"取得できず: {type(e).__name__}"
    else:
        status["current"] = f"{len(cur)}件"
    cur_years = {d.year for d in cur}
    for y in range(int(START[:4]), int(END[:4]) + 1):
        got = [d for d in cur if d.year == y]
        if y not in cur_years or len(got) < 8:
            try:
                got = sorted(set(got) | set(parse_fomc_hist(http_get(FOMC_HIST.format(y=y), opener))))
            except Exception as e:  # noqa: BLE001
                if not got:                       # 日程のページにも無い年だけ「取得できず」（今年は過去のページがまだ無い）
                    status[str(y)] = f"取得できず: {type(e).__name__}"
                    continue
                status[str(y)] = f"{len(got)}件（日程のページ・過去のページは {type(e).__name__}）"
                dates |= set(got)
                continue
        status[str(y)] = f"{len(got)}件"
        dates |= set(got)
    return sorted(dates), status


# ════════════════════ 問いごとの取引 ════════════════════

def fix_rows(kind, bars, days):
    """X2〜X5：日ごとのドルのペアの平均（MIN_PAIRS 以上そろった日）→ 行の一覧。1行＝1日"""
    t_in, t_out = fix_windows(kind, days)
    sign_kind = {"X2": -1, "X3": 1, "X4": 1, "X5": -1}[kind]
    G, N, C, per_pair = [], [], [], {}
    for p, s in USD_BUY.items():
        if p not in bars:
            continue
        g, n, c = trade_arrays(bars[p], p, t_in, t_out, s * sign_kind)
        G.append(g), N.append(n), C.append(c)
        per_pair[p] = (g, n)
    G, N, C = np.array(G), np.array(N), np.array(C)
    ok = (~np.isnan(N)).sum(0)
    rows = []
    for i, d in enumerate(days):
        if ok[i] < MIN_PAIRS:
            continue
        rows.append({"date": d.isoformat(), "gross": float(np.nanmean(G[:, i])), "net": float(np.nanmean(N[:, i])),
                     "cost": float(np.nanmean(C[:, i])), "n_pairs": int(ok[i])})
    pairs = {p: {"n": int((~np.isnan(n)).sum()), "gross": _nm(g), "net": _nm(n)} for p, (g, n) in per_pair.items()}
    return rows, pairs


def _nm(a):
    a = np.asarray(a, float)
    a = a[~np.isnan(a)]
    return float(a.mean()) if len(a) else None


def daily_ranges(d):
    """UTC の日ごとの値幅（中値の高値−安値）。足が ATR_MIN_BARS 本以上ある日だけ"""
    g = d.groupby(d.index.floor("D"))
    r = g["mh"].max() - g["ml"].min()
    return r[g.size() >= ATR_MIN_BARS]


def gap_trades(d, pair, gap_min=GAP_READ):
    """X1：1ペアの月曜の窓の取引（窓の大きさ gap_min 以上・まだ埋まっていない週）"""
    if len(d) < 2:
        return []
    idx = d.index
    mo, mh, ml, mc = (d[c].to_numpy() for c in ("mo", "mh", "ml", "mc"))
    so, sc = d["so"].to_numpy(), d["sc"].to_numpy()
    rng = daily_ranges(d)
    rdates = rng.index
    gaps = (idx[1:] - idx[:-1]) >= pd.Timedelta(hours=WEEK_GAP_H)
    out = []
    for p in np.flatnonzero(gaps) + 1:
        fri = p - 1
        target = mc[fri]
        prior = rng[rdates <= idx[fri].floor("D")].iloc[-ATR_DAYS:]
        if len(prior) < ATR_DAYS:
            continue
        atr = float(prior.mean())
        gap = mo[p] - target
        if atr <= 0 or abs(gap) / atr < gap_min:
            continue
        mon0 = idx[p].ceil("D")
        t_end = mon0 + pd.Timedelta(hours=EXIT_X1_UTC_H)
        q = int(np.searchsorted(idx, mon0))
        if q >= len(idx) or idx[q] > t_end:
            continue
        up = gap > 0
        pre = slice(p, q)                 # 週の初めの足から、入る足の前まで（週の初めが月曜 0時ちょうどなら 0本）
        filled_before = q > p and ((ml[pre].min() <= target) if up else (mh[pre].max() >= target))
        if filled_before:
            out.append({"week": mon0.date().isoformat(), "pair": pair, "g": abs(gap) / atr, "up": bool(up), "traded": False})
            continue
        entry = mo[q]
        if (up and entry <= target) or (not up and entry >= target):
            out.append({"week": mon0.date().isoformat(), "pair": pair, "g": abs(gap) / atr, "up": bool(up), "traded": False})
            continue
        r = q
        exit_px, hit = None, False
        while r < len(idx) and idx[r] <= t_end:
            if (up and ml[r] <= target) or (not up and mh[r] >= target):
                exit_px, hit = target, True
                break
            r += 1
        if exit_px is None:
            r -= 1
            exit_px = mc[r]
        sign = -1 if up else 1
        gross = sign * (exit_px / entry - 1) * 1e4
        cost = max(fixed_cost(pair), (so[q] + sc[r]) / 2) / entry * 1e4
        out.append({"week": mon0.date().isoformat(), "pair": pair, "g": abs(gap) / atr, "up": bool(up), "traded": True,
                    "filled": hit, "gross": gross, "net": gross - cost, "cost": cost,
                    "spread_over": bool((so[q] + sc[r]) / 2 > fixed_cost(pair))})
    return out


def week_rows(trades, gap_min=GAP_MIN):
    """X1：週ごとの、入ったペアの平均 → 行の一覧（1行＝1週）"""
    t = [x for x in trades if x["traded"] and x["g"] >= gap_min]
    by = {}
    for x in t:
        by.setdefault(x["week"], []).append(x)
    return [{"date": w, "gross": float(np.mean([x["gross"] for x in v])), "net": float(np.mean([x["net"] for x in v])),
             "cost": float(np.mean([x["cost"] for x in v])), "n_pairs": len(v)} for w, v in sorted(by.items())]


# ════════════════════ 物差しと判定 ════════════════════

def boot_ci(vals, n_boot=N_BOOT, alpha=ALPHA, seed=SEED):
    v = np.asarray(vals, float)
    rng = np.random.default_rng(seed)
    means = np.empty(n_boot)
    step = max(1, 2_000_000 // max(len(v), 1))
    for k in range(0, n_boot, step):
        m = min(step, n_boot - k)
        means[k:k + m] = v[rng.integers(0, len(v), size=(m, len(v)))].mean(1)
    return float(np.percentile(means, 100 * alpha / 2)), float(np.percentile(means, 100 * (1 - alpha / 2)))


def stats(rows, kind):
    n = len(rows)
    if n < MIN_N[kind]:
        return {"n": n, "verdict": VERDICTS[3]}
    net = np.array([r["net"] for r in rows])
    gross = np.array([r["gross"] for r in rows])
    dates = np.array([r["date"] for r in rows])
    lo, hi = boot_ci(net)
    glo, ghi = boot_ci(gross, seed=SEED + 1)
    first, second = net[dates < HALF], net[dates >= HALF]
    recent = net[dates >= RECENT]
    st = {"n": n, "mean": float(net.mean()), "lo": lo, "hi": hi, "gross": float(gross.mean()), "glo": glo, "ghi": ghi,
          "first": float(first.mean()) if len(first) else None, "second": float(second.mean()) if len(second) else None,
          "recent": float(recent.mean()) if len(recent) else None, "n_recent": int(len(recent)),
          "cost": float(np.median([r["cost"] for r in rows])), "win": float((net > 0).mean())}
    st["verdict"] = judge(st)
    st["seen_before_cost"] = bool(glo > 0)
    return st


def judge(st):
    if st.get("mean") is None:
        return VERDICTS[3]
    a = st["lo"] > 0
    b = (st["first"] or 0) > 0 and (st["second"] or 0) > 0
    c = (st["recent"] or 0) > 0
    if a and b and c:
        return VERDICTS[0]
    if st["mean"] > 0 and c:
        return VERDICTS[1]
    return VERDICTS[2]


def by_year(rows):
    out = {}
    for r in rows:
        out.setdefault(r["date"][:4], []).append(r["net"])
    return {y: {"n": len(v), "net": float(np.mean(v))} for y, v in sorted(out.items())}


# ════════════════════ 読むための地図 ════════════════════

def clock_map(bars):
    """ドルのペア7つの「ドル買い」の1時間ごとの平均（ロンドンの時刻・費用前・平日）"""
    acc = {}
    for p, s in USD_BUY.items():
        d = bars.get(p)
        if d is None or d.empty:
            continue
        r = s * (d["mc"] / d["mo"] - 1) * 1e4
        loc = d.index.tz_convert(LON)
        keep = loc.weekday < 5
        g = pd.Series(r.to_numpy()[keep]).groupby(loc.hour[keep]).mean()
        for h, v in g.items():
            acc.setdefault(int(h), []).append(float(v))
    return {h: float(np.mean(v)) for h, v in sorted(acc.items())}


def cost_map(bars):
    """ペア×ロンドンの時刻：売り買いの差の中央値（pips）・1時間の値幅の中央値（pips）"""
    out = {}
    for p, d in bars.items():
        if d.empty:
            continue
        loc = d.index.tz_convert(LON)
        keep = loc.weekday < 5
        sp = pd.Series((d["so"] / pip(p)).to_numpy()[keep]).groupby(loc.hour[keep]).median()
        rg = pd.Series(((d["mh"] - d["ml"]) / pip(p)).to_numpy()[keep]).groupby(loc.hour[keep]).median()
        out[p] = {int(h): {"spread": float(sp[h]), "range": float(rg[h])} for h in sp.index}
    return out


# ════════════════════ 点検・本番 ════════════════════

def load_all(root=None):
    bars, dropped = {}, {}
    for p in FB.PAIRS:
        d, n_bad = prep(FB.load(p, root=root), p)
        bars[p], dropped[p] = d, n_bad
    return bars, dropped


def missing_share(root=None):
    cov = FB.coverage(root, end=(int(END[:4]), int(END[5:7])))
    want = sum(v["want"] for v in cov.values())
    have = sum(v["have"] for v in cov.values())
    return (1 - have / want) if want else 1.0, cov


def check(root=None):
    """点検だけ（損益は出さない）"""
    miss, cov = missing_share(root)
    print(f"置き場：{FB.info(root)}", flush=True)
    print(f"欠けている月の割合 {miss:.1%}（上限 {MISSING_MAX:.0%}）", flush=True)
    bars, dropped = load_all(root)
    print("| ペア | 足の数 | 最初 | 最後 | 差がおかしく落とした足 | 終値の中値の範囲 | 差の中央値（pips） |\n|---|---|---|---|---|---|---|")
    for p, d in bars.items():
        if d.empty:
            print(f"| {p} | 0 | — | — | {dropped[p]} | — | — |")
            continue
        print(f"| {p} | {len(d)} | {d.index[0]:%Y-%m-%d} | {d.index[-1]:%Y-%m-%d} | {dropped[p]} | "
              f"{d['mc'].min():.5g}〜{d['mc'].max():.5g} | {(d['so'] / pip(p)).median():.2f} |")
    fomc, status = fomc_dates()
    print(f"FOMC の定例会合の声明の日：{len(fomc)}件（{START}〜{END} は {len(days_for('X5', fomc))}件）・{status}", flush=True)
    ok = miss <= MISSING_MAX and all(not d.empty for d in bars.values())
    print("数えられる" if ok else "数えない（置き場を取り直す）", flush=True)
    return 0 if ok else 1


def run(root=None, today=None):
    miss, _ = missing_share(root)
    if miss > MISSING_MAX:
        print(f"欠けている月の割合 {miss:.1%} が上限を超えた＝数えない", flush=True)
        return None
    bars, dropped = load_all(root)
    fomc, fomc_status = fomc_dates()
    res, rows_all = {}, {}
    gt = []
    for p in FB.PAIRS:
        gt += gap_trades(bars[p], p)
    rows_all["X1"] = week_rows(gt)
    for k in ("X2", "X3", "X4", "X5"):
        rows_all[k], pairs = fix_rows(k, bars, days_for(k, fomc))
        res[k] = {"pairs": pairs}
    res.setdefault("X1", {})
    for k in ("X1", "X2", "X3", "X4", "X5"):
        res[k].update(stats(rows_all[k], k))
        res[k]["by_year"] = by_year(rows_all[k])
        res[k]["title"] = TITLE[k]
    # X1 の読むための表
    traded = [x for x in gt if x["traded"]]
    bins = {"0.10〜0.25": (0.10, 0.25), "0.25〜0.5": (0.25, 0.5), "0.5以上": (0.5, 1e9)}
    res["X1"]["by_size"] = {k: _x1_sub([x for x in traded if lo <= x["g"] < hi]) for k, (lo, hi) in bins.items()}
    big = [x for x in traded if x["g"] >= GAP_MIN]
    res["X1"]["by_dir"] = {"上に窓（売り）": _x1_sub([x for x in big if x["up"]]), "下に窓（買い）": _x1_sub([x for x in big if not x["up"]])}
    res["X1"]["filled_share"] = float(np.mean([x["filled"] for x in big])) if big else None
    res["X1"]["skipped_filled_before"] = int(sum(1 for x in gt if not x["traded"] and x["g"] >= GAP_MIN))
    res["X1"]["spread_over_share"] = float(np.mean([x["spread_over"] for x in big])) if big else None
    res["X1"]["pairs"] = {p: _x1_sub([x for x in big if x["pair"] == p]) for p in FB.PAIRS}
    # X5 の比べる相手：同じ窓を FOMC の無い平日に
    fset = set(days_for("X5", fomc))
    others = [d for d in weekdays() if d not in fset]
    orow, _ = fix_rows("X5", bars, others)
    res["X5"]["non_fomc"] = {"n": len(orow), "gross": _nm([r["gross"] for r in orow]), "net": _nm([r["net"] for r in orow])}
    now = today or dt.datetime.now(JST)
    out = {"generated": now.isoformat(timespec="minutes"), "prereg_sha256": prereg_sha(), "kind": "backtest", "section": "X",
           "store": FB.info(root), "period": [START, END], "dropped_bars": dropped, "fomc_status": fomc_status,
           "titles": {k: TITLE[k] for k in TITLE}, "verdicts": list_verdicts(res, now.date().isoformat()),
           "results": res, "clock_map": clock_map(bars), "cost_map": cost_map(bars)}
    return out


def list_verdicts(res, day):
    """検証済みリスト（verified_list.py）に載せる形。差なしだけ（ストップ）。値は損益率（bp÷10000）"""
    out = {}
    for k, r in res.items():
        if r.get("verdict") != VERDICTS[2]:
            continue
        note = f"・{SEEN_NOTE}" if r.get("seen_before_cost") else ""
        out[k] = {"status": "stop", "decided_on": day, "n": r["n"], "mean": r["mean"] / 1e4, "lo": r["lo"] / 1e4, "hi": r["hi"] / 1e4,
                  "reason": f"過去のデータ（Dukascopy の1時間足・2012〜2026-09）で1回だけ数えて差なし（99%の幅・前半後半・最近{note}）"}
    return out


def _x1_sub(trs):
    if not trs:
        return {"n": 0}
    return {"n": len(trs), "gross": float(np.mean([x["gross"] for x in trs])), "net": float(np.mean([x["net"] for x in trs])),
            "filled": float(np.mean([x["filled"] for x in trs]))}


def _f(x, nd=2, sign=True):
    if x is None:
        return "—"
    return f"{x:+.{nd}f}" if sign else f"{x:.{nd}f}"


def render_md(out):
    R = out["results"]
    L = ["# X 為替の時計の癖（第3波）", "",
         f"- 生成: {out['generated']}　事前登録の指紋（PILLAR_PREREG.md の sha256）: `{out['prereg_sha256']}`",
         f"- 物差しと判定＝PILLAR_PREREG.md「X 為替の時計の癖（第3波）」（計算より先にコミット）。期間 {out['period'][0]}〜{out['period'][1]}・**1回だけ数えた結果**",
         f"- 値段＝為替の値段の置き場（Dukascopy の1時間足・売値と買値）：{out['store']}",
         "- 単位＝ベーシスポイント（0.01%）。費用＝max（円のペア 1.2pips・ほか 1.8pips の往復, 実際の売り買いの差）。**売買の決まりではない**",
         f"- 判定＝費用後の平均の99%の幅がまるごと0より上・前半（〜2018）と後半（2019〜）とも費用後プラス・最近（2021〜）も費用後プラス（問いが5つ＝0.05÷5）", "",
         "## 判定の一覧", "",
         "| 問い | 判定 | 回数 | 費用後の平均 | 99%の幅 | 前半 | 後半 | 最近 | 費用前の平均 | 費用前の99%の幅 | 費用の中央値 |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for k in ("X1", "X2", "X3", "X4", "X5"):
        r = R[k]
        if r["verdict"] == VERDICTS[3]:
            L.append(f"| {k} {r['title']} | {r['verdict']} | {r['n']} | — | — | — | — | — | — | — | — |")
            continue
        v = r["verdict"] + (f"（{SEEN_NOTE}）" if r["seen_before_cost"] and r["verdict"] != VERDICTS[0] else "")
        L.append(f"| {k} {r['title']} | {v} | {r['n']} | {_f(r['mean'])} | {_f(r['lo'])}〜{_f(r['hi'])} | {_f(r['first'])} | {_f(r['second'])} | "
                 f"{_f(r['recent'])} | {_f(r['gross'])} | {_f(r['glo'])}〜{_f(r['ghi'])} | {_f(r['cost'], sign=False)} |")
    L += ["", "## 読むための表（判定には使わない）", ""]
    for k in ("X1", "X2", "X3", "X4", "X5"):
        r = R[k]
        L += [f"### {k} {r['title']}", ""]
        if r.get("by_year"):
            L.append("- 年ごとの費用後の平均：" + "・".join(f"{y} {_f(v['net'])}（{v['n']}）" for y, v in r["by_year"].items()))
        if k == "X1":
            L.append(f"- 金曜の終値まで戻った割合 {_f(r.get('filled_share'), sign=False)}・入る前に埋まって入らなかった {r.get('skipped_filled_before')}・"
                     f"実際の差が決まった費用を上回った割合 {_f(r.get('spread_over_share'), sign=False)}")
            L.append("- 窓の大きさごと：" + "・".join(f"{b} {_f(v.get('net'))}（{v['n']}・戻った {_f(v.get('filled'), sign=False)}）" for b, v in r["by_size"].items()))
            L.append("- 窓の向きごと：" + "・".join(f"{b} {_f(v.get('net'))}（{v['n']}）" for b, v in r["by_dir"].items()))
        if k == "X5" and r.get("non_fomc"):
            o = r["non_fomc"]
            L.append(f"- 同じ窓を FOMC の無い平日に当てたもの：費用前 {_f(o['gross'])}・費用後 {_f(o['net'])}（{o['n']}日）")
        if r.get("pairs"):
            L.append("- ペアごと（費用前／費用後・回数）：" + "・".join(f"{p} {_f(v.get('gross'))}／{_f(v.get('net'))}（{v['n']}）" for p, v in r["pairs"].items() if v.get("n")))
        L.append("")
    L += ["## 時計の地図（ドルのペア7つの「ドル買い」の1時間ごとの平均・費用前・全期間・平日）", "",
          "⚠️ ここから選んだ窓は、別の登録にして、この期間の外（前向き・手元の MT5 の実際の約定）で確かめる", "",
          "| ロンドンの時刻 | 平均（bp） |", "|---|---|"]
    L += [f"| {h:02d}:00 | {_f(v, 3)} |" for h, v in out["clock_map"].items()]
    pairs = list(out["cost_map"].keys())
    L += ["", "## 費用の地図（売り買いの差の中央値 pips ／ 1時間の値幅の中央値 pips・平日・ロンドンの時刻）", "",
          "| 時刻 | " + " | ".join(pairs) + " |", "|---|" + "---|" * len(pairs)]
    for h in range(24):
        cells = []
        for p in pairs:
            c = out["cost_map"][p].get(h) or out["cost_map"][p].get(str(h))
            cells.append(f"{c['spread']:.1f}／{c['range']:.0f}" if c else "—")
        L.append(f"| {h:02d} | " + " | ".join(cells) + " |")
    L += ["", "## 読み方の約束と限界", "",
          "- ◎ なら MT5 のデモで前向きの観察を別に登録してから始める。◯ は読むための数字まで。差なしは検証済みリストへ",
          "- Dukascopy は個人向けの業者より売り買いの差が狭い（決まった費用を下限にした）・1時間足なので値決めの時刻ちょうどでは区切れない・スワップは入れない",
          "- 過去の成績は将来を約束しない。情報提供であり投資助言ではない"]
    return "\n".join(L) + "\n"


def write(out):
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, default=str)
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(render_md(out))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--root", default=None)
    a = ap.parse_args(argv)
    if a.check:
        return check(a.root)
    if os.path.exists(OUT_JSON):
        print(f"{OUT_JSON} がすでにある＝1回だけ数える決まりなので数えない", flush=True)
        return 1
    out = run(a.root)
    if out is None:
        return 1
    write(out)
    print(render_md(out), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
