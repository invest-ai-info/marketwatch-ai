# -*- coding: utf-8 -*-
"""F3 ファンダの向き × トレンド × オシレーター（4時間足・為替12ペア・2004〜2026・6×10×6＝360通り）。
2026-10-10 登録・オーナー「蓄積系の検証はとても時間がかかるので、すぐに検証できる方法で」「ファンダメンタルズで方向性を確認して、
トレンド系の指標とオシレーター系の指標を組み合わせて、すべての組み合わせを試してみてください」。PILLAR_PREREG.md「F3」。

ファンダの向き（月ごと・前の月末に決める）× トレンド（相性ラボと同じ T0〜T9）× オシレーター（O1〜O6）。出口はいまの方式1つ
（損切り1.5ATR・利確2ATR・最長20本）＋金曜 UTC 04:00 の足の始値で手じまい（週末に持ち越さない）。費用とスワップを R で引く。
前半（2004〜2014）で上位3つを選び、後半（2015〜）で1回だけ確かめる（95%・ペアと年の二方向・偽薬 p＜0.05÷3）。

⚠️ 決まりは PILLAR_PREREG.md「F3」と下の定数に固定。出力（fund-combo-lab.json / .md）は集計だけ（SYNC禁忌）。
実行: python fund_combo_lab.py --check   （点検だけ＝4時間足とオシレーターの合図の数・ファンダの向きの割合。損益は数えない・何も書き出さない）
      python fund_combo_lab.py           （本番。Actions の fund-combo-lab.yml から手動で・1回だけ）
"""
import datetime as dt
import json
import sys

import numpy as np
import pandas as pd

import combo_lab as CL
import fx_value_lab as FV
import momentum_lab as M
import pillar_lab as P
import trend_lab as TL
import tsmom_lab as T

# ════════════════════ 事前登録の値（PILLAR_PREREG.md「F3」） ════════════════════
PAIRS = ("EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCHF", "USDCAD", "NZDUSD",
         "EURJPY", "GBPJPY", "AUDJPY", "EURAUD", "GBPAUD")
FUNDS = {"F0": "ファンダなし", "F1": "金利差（キャリー）", "F2": "金利の方向（6か月）", "F3": "経済の勢い",
         "F4": "割安", "F5": "金利差・金利の方向・経済の勢いの多数決"}
F_KEYS = ("F1", "F2", "F3", "F4", "F5")
TRENDS = CL.TRENDS                      # T0（なし）＋ T1〜T9
OSCS = tuple(CL.OSCS)                   # O1〜O6
SPLIT = "2015-01-01"                    # 前半（選ぶ）＝2014年まで／後半（確かめる）＝2015年から
FIRST, LAST = (2004, 1), (2026, 9)
MIN_N_EXPLORE, TOP_K = 150, 3
P_LIMIT = 0.05 / TOP_K
COOLDOWN, WARMUP = 5, 260
RISK_ATR, SL_M, TP_M, CAP = 1.5, 1.5, 2.0, 20
RATE_LOOK = 6                           # F2 金利の方向＝6か月前との差
FRI_CUT_HOUR = 4                        # 金曜 UTC 04:00 に始まる足の始値で手じまう
FX_PIPS_JPY, FX_PIPS_OTHER, FX_MARKUP = 1.2, 1.8, 0.01
N_PERM = 2000
OUT_JSON, OUT_MD = "fund-combo-lab.json", "fund-combo-lab.md"
KEPT, GONE = "確かめでも残った（有望）", "確かめで消えた"


# ════════════════════ 4時間足 ════════════════════

def bars_4h(df):
    """fx_bars.load の1時間足（UTC・売値 b* と買値 a*）→ 4時間足（UTC 0/4/8/12/16/20 時）。
    列＝Open High Low Close（真ん中の値）・sp_open（始まりの売り買いの差）・sp_max（足の中の一番大きい差）"""
    if df is None or df.empty:
        return None
    idx = df.index if df.index.tz is not None else df.index.tz_localize("UTC")
    mo, mh, ml, mc = ((df["bo"] + df["ao"]) / 2, (df["bh"] + df["ah"]) / 2, (df["bl"] + df["al"]) / 2, (df["bc"] + df["ac"]) / 2)
    so, sc = df["ao"] - df["bo"], df["ac"] - df["bc"]
    x = pd.DataFrame({"o": mo.values, "h": mh.values, "l": ml.values, "c": mc.values, "so": so.values,
                      "sm": np.maximum(so.values, sc.values)}, index=idx)
    g = x.groupby(idx.floor("4h"))
    out = pd.DataFrame({"Open": g["o"].first(), "High": g["h"].max(), "Low": g["l"].min(), "Close": g["c"].last(),
                        "sp_open": g["so"].first(), "sp_max": g["sm"].max()})
    return out.dropna(subset=["Open", "High", "Low", "Close"])


def week_cut(ts):
    """その足が属する取引の週の「金曜 UTC 04:00」（日曜の足は次の金曜）"""
    d = ts.normalize()
    wd = ts.weekday()
    days = 5 if wd == 6 else 4 - wd
    return d + pd.Timedelta(days=days, hours=FRI_CUT_HOUR)


def cut_arrays(index):
    """各足 e について：入ってよいか（その週の金曜 04:00 より前・土曜でない）、手じまいの足 j（金曜 04:00 以降の最初の足）、
    その足が金曜 04:00 から24時間より後か（＝金曜の足が無い週。そのときは j の1つ前の足の終値で出る）"""
    n = len(index)
    ok = np.zeros(n, bool)
    cut_k = np.full(n, n, int)
    gap = np.zeros(n, bool)
    cuts = [week_cut(t) for t in index]
    j = 0
    for e in range(n):
        ok[e] = index[e] < cuts[e] and index[e].weekday() != 5
        j = max(j, e)
        while j < n and index[j] < cuts[e]:
            j += 1
        if j < n:
            cut_k[e] = j
            gap[e] = index[j] > cuts[e] + pd.Timedelta(hours=24)
    return ok, cut_k, gap


# ════════════════════ 出口（損切り1.5・利確2・最長20本・金曜の手じまい） ════════════════════

def simulate(o, h, l, c, atr_i, i, side, cut_k, gap):
    """合図の足 i → 次の足 e＝i+1 の始値で入る。→ (R（費用前）, 出た足, 持った本数)。足りなければ None"""
    e = i + 1
    n = len(c)
    if e >= n or not atr_i > 0 or e + CAP - 1 >= n:
        return None
    s = 1.0 if side == "long" else -1.0
    entry = o[e]
    unit = RISK_ATR * atr_i
    sl, tp = entry - s * SL_M * atr_i, entry + s * TP_M * atr_i
    ck = cut_k[e]
    for k in range(e, e + CAP):
        if k == ck and k > e:                                      # 金曜 04:00 の手じまい
            if gap[e]:
                return s * (c[k - 1] - entry) / unit, k - 1, k - e   # 金曜の足が無い週＝前の足の終値
            return s * (o[k] - entry) / unit, k, k - e
        if s > 0:
            if o[k] <= sl:
                return (o[k] - entry) / unit, k, k - e
            if l[k] <= sl:
                return (sl - entry) / unit, k, k - e + 1
            if o[k] >= tp:
                return (o[k] - entry) / unit, k, k - e
            if h[k] >= tp:
                return (tp - entry) / unit, k, k - e + 1
        else:
            if o[k] >= sl:
                return -(o[k] - entry) / unit, k, k - e
            if h[k] >= sl:
                return -(sl - entry) / unit, k, k - e + 1
            if o[k] <= tp:
                return -(o[k] - entry) / unit, k, k - e
            if l[k] <= tp:
                return -(tp - entry) / unit, k, k - e + 1
    k = e + CAP - 1
    return s * (c[k] - entry) / unit, k, CAP


def pip_of(pair):
    return 0.01 if pair.endswith("JPY") else 0.0001


def cost_r(pair, sp_e, sp_x, unit):
    fixed = (FX_PIPS_JPY if pair.endswith("JPY") else FX_PIPS_OTHER) * pip_of(pair)
    act = (sp_e + sp_x) / 2 if np.isfinite(sp_e) and np.isfinite(sp_x) else 0.0
    return max(fixed, act) / unit


def swap_r(sign, rb, rq, held_bars, entry, unit):
    days = held_bars * 4 / 24
    return (sign * (rb - rq) / 100 * days / 365 * entry - FX_MARKUP * days / 365 * entry) / unit


# ════════════════════ ファンダの向き（月ごと） ════════════════════

def ym_add(t, k):
    b = FV.mi(*t) + k
    return b // 12, b % 12 + 1


def rate_of(rates, c, t):
    r = T.rate_at(rates, FV.BIS_AREA[c], FV.ymk(t))
    if r is None and c == "JPY":
        return 0.0                       # 量的緩和の時期の空欄＝0％とみなす（PREREG「F3」）
    return r


def _sgn(x, eps=1e-12):
    if x is None or not np.isfinite(x):
        return 0
    return 1 if x > eps else -1 if x < -eps else 0


def fund_states(rates, reer, cpi, cfreq, une, ufreq, months):
    """→ {pair: {(年, 月) M: (F1, F2, F3, F4, F5)}}。月 M の向き＝前の月 t＝M−1 の月末に決めたもの"""
    out = {p: {} for p in PAIRS}
    for M_ in months:
        t = ym_add(M_, -1)
        rate = {c: rate_of(rates, c, t) for c in FV.CCYS}
        rate6 = {c: rate_of(rates, c, ym_add(t, -RATE_LOOK)) for c in FV.CCYS}
        e = FV.e_signal(cpi, une, t, cfreq, ufreq)
        v = {c: FV.v_signal(reer.get(c) or {}, t) for c in FV.CCYS}
        for p in PAIRS:
            b, q = p[:3], p[3:]
            f1 = _sgn(rate[b] - rate[q]) if rate[b] is not None and rate[q] is not None else 0
            f2 = 0
            if None not in (rate[b], rate[q], rate6[b], rate6[q]):
                f2 = _sgn((rate[b] - rate[q]) - (rate6[b] - rate6[q]))
            f3 = _sgn(e[b] - e[q]) if b in e and q in e else 0
            f4 = _sgn(v[b] - v[q]) if v.get(b) is not None and v.get(q) is not None else 0
            votes = (f1, f2, f3)
            f5 = 1 if (votes.count(1) >= 2 and votes.count(-1) == 0) else -1 if (votes.count(-1) >= 2 and votes.count(1) == 0) else 0
            out[p][M_] = (f1, f2, f3, f4, f5)
    return out


# ════════════════════ 合図と1回ごとの R ════════════════════

def pair_arrays(pair, bars, fund, rates):
    """1ペアの全部の足について：買い・売りの R（費用・スワップ後・入れない足は NaN）、トレンドの向き、ファンダの向き、オシレーターの合図"""
    o, h, l, c = (np.asarray(bars[k].values, float) for k in ("Open", "High", "Low", "Close"))
    spo, spm = np.asarray(bars["sp_open"].values, float), np.asarray(bars["sp_max"].values, float)
    atr = TL.rma(TL.true_range(h, l, c), 14)
    n = len(c)
    idx = bars.index
    ok_e, cut_k, gap = cut_arrays(idx)
    months = [(t.year, t.month) for t in idx]
    F = np.array([fund.get(m, (0, 0, 0, 0, 0)) for m in months], float).reshape(n, 5)
    R, CST, SWP = {}, {}, {}
    b, q = pair[:3], pair[3:]
    for side, s in (("long", 1.0), ("short", -1.0)):
        r_all, c_all, w_all = np.full(n, np.nan), np.full(n, np.nan), np.full(n, np.nan)
        for i in range(WARMUP, n - 1):
            if not ok_e[i + 1]:
                continue
            res = simulate(o, h, l, c, atr[i], i, side, cut_k, gap)
            if res is None:
                continue
            r, k, held = res
            unit = RISK_ATR * atr[i]
            em = (idx[i + 1].year, idx[i + 1].month)
            rb, rq = rate_of(rates, b, em), rate_of(rates, q, em)
            if rb is None or rq is None:
                continue
            cr = cost_r(pair, spo[i + 1], spm[k], unit)
            sw = swap_r(s, rb, rq, held, o[i + 1], unit)
            r_all[i], c_all[i], w_all[i] = r - cr + sw, cr, sw
        R[side], CST[side], SWP[side] = r_all, c_all, w_all
    states = TL.all_states(bars)
    ST = np.array([states[k] for k in TL.NAMES], float).T          # n × 9
    sig = CL.osc_signals(bars)
    date = np.array([t.strftime("%Y-%m-%d") for t in idx])
    return {"R": R, "cost": CST, "swap": SWP, "ST": ST, "F": F, "sig": sig, "date": date, "n": n}


def entries_of(pair, A):
    """オシレーターの合図（5本あけ・準備の足を除く）→ 1回ごとの行（R が NaN の合図は数えない）"""
    rows = []
    n = A["n"]
    for (osc, side), mask in A["sig"].items():
        last = -10 ** 9
        s = 1.0 if side == "long" else -1.0
        for i in np.flatnonzero(mask):
            if i < WARMUP or i + 1 >= n or i - last < COOLDOWN:
                continue
            last = i
            r = A["R"][side][i]
            if not np.isfinite(r):
                continue
            rows.append((pair, i, OSCS.index(osc), s, A["date"][i + 1], r, A["cost"][side][i], A["swap"][side][i]))
    return rows


def build_table(E):
    """E＝entries を numpy にしたもの → 360通りの前半・後半の件数と平均"""
    rows = []
    for f in FUNDS:
        mf = np.ones(len(E["r"]), bool) if f == "F0" else (E["F"][:, F_KEYS.index(f)] == E["sign"])
        for t in TRENDS:
            mt = np.ones(len(E["r"]), bool) if t == "T0" else (E["ST"][:, list(TL.NAMES).index(t)] == E["sign"])
            for oi, o in enumerate(OSCS):
                m = mf & mt & (E["osc"] == oi)
                a, b_ = E["r"][m & E["explore"]], E["r"][m & ~E["explore"]]
                rows.append({"f": f, "t": t, "osc": o, "n_e": int(len(a)), "m_e": float(a.mean()) if len(a) else None,
                             "n_c": int(len(b_)), "m_c": float(b_.mean()) if len(b_) else None})
    return rows


def to_arrays(rows, arrays):
    if not rows:
        return None
    pair = np.array([r[0] for r in rows])
    i = np.array([r[1] for r in rows])
    E = {"pair": pair, "i": i, "osc": np.array([r[2] for r in rows]), "sign": np.array([r[3] for r in rows]),
         "date": np.array([r[4] for r in rows]), "r": np.array([r[5] for r in rows], float),
         "cost": np.array([r[6] for r in rows], float), "swap": np.array([r[7] for r in rows], float)}
    E["ST"] = np.array([arrays[p]["ST"][k] for p, k in zip(pair, i)], float).reshape(len(rows), 9)
    E["F"] = np.array([arrays[p]["F"][k] for p, k in zip(pair, i)], float).reshape(len(rows), 5)
    E["explore"] = E["date"] < SPLIT
    E["year"] = np.array([d[:4] for d in E["date"]])
    return E


def combo_mask(E, f, t, osc):
    m = E["osc"] == OSCS.index(osc)
    if f != "F0":
        m &= E["F"][:, F_KEYS.index(f)] == E["sign"]
    if t != "T0":
        m &= E["ST"][:, list(TL.NAMES).index(t)] == E["sign"]
    return m


def pick_top(rows, k=TOP_K, min_n=MIN_N_EXPLORE):
    ok = [r for r in rows if r["n_e"] >= min_n and r["m_e"] is not None]
    return sorted(ok, key=lambda r: (-r["m_e"], -r["n_e"], r["f"], r["t"], r["osc"]))[:k]


def placebo_pool(arrays, f, t):
    """後半の、同じペア・同じ向きでファンダとトレンドの条件を満たす全部の足に入った場合の R"""
    pool = {}
    for p, A in arrays.items():
        conf = A["date"] >= SPLIT
        conf = np.concatenate([conf[1:], [False]])           # 入る足（i+1）が後半
        for side, s in (("long", 1.0), ("short", -1.0)):
            m = np.isfinite(A["R"][side]) & conf
            m[:WARMUP] = False
            if f != "F0":
                m &= A["F"][:, F_KEYS.index(f)] == s
            if t != "T0":
                m &= A["ST"][:, list(TL.NAMES).index(t)] == s
            pool[(p, s)] = A["R"][side][m]
    return pool


def judge(st, p):
    lo = st.get("lo")
    if lo is None or p is None:
        return GONE
    return KEPT if (lo > 0 and p < P_LIMIT) else GONE


def confirm_one(E, arrays, r, n_perm=N_PERM):
    m = combo_mask(E, r["f"], r["t"], r["osc"]) & ~E["explore"]
    vals = E["r"][m].tolist()
    groups = list(zip(E["pair"][m].tolist(), E["year"][m].tolist()))
    st = P.mean_ci(vals, groups) if len(vals) >= 2 else {"n": len(vals), "mean": P._mean(vals), "lo": None, "hi": None}
    counts = {}
    for p, s in zip(E["pair"][m], E["sign"][m]):
        counts[(p, float(s))] = counts.get((p, float(s)), 0) + 1
    sims = CL.placebo(placebo_pool(arrays, r["f"], r["t"]), counts, n_perm=n_perm) if counts else None
    p = None
    if sims is not None and st.get("mean") is not None:
        cen = float(np.mean(sims))
        p = float((np.sum(np.abs(sims - cen) >= abs(st["mean"] - cen)) + 1) / (len(sims) + 1))
        st["placebo_mean"] = cen
    st["p_placebo"] = p
    for key, (f, t) in (("f0_mean", ("F0", r["t"])), ("t0_mean", (r["f"], "T0"))):
        mm = combo_mask(E, f, t, r["osc"]) & ~E["explore"]
        st[key] = float(E["r"][mm].mean()) if mm.any() else None
    st["cost_mean"] = float(E["cost"][m].mean()) if m.any() else None
    st["swap_mean"] = float(E["swap"][m].mean()) if m.any() else None
    st["verdict"] = judge(st, p)
    return st


def fund_effect(rows):
    """F1〜F5 ごと：同じ T×O で F − F0 の差の平均（前半・後半）と、両方で良くなったマスの数"""
    base = {(r["t"], r["osc"]): r for r in rows if r["f"] == "F0"}
    out = {}
    for f in F_KEYS:
        de, dc, both, cnt = [], [], 0, 0
        for r in rows:
            if r["f"] != f:
                continue
            b = base[(r["t"], r["osc"])]
            if None in (r["m_e"], r["m_c"], b["m_e"], b["m_c"]):
                continue
            cnt += 1
            de.append(r["m_e"] - b["m_e"])
            dc.append(r["m_c"] - b["m_c"])
            both += (r["m_e"] > b["m_e"]) and (r["m_c"] > b["m_c"])
        out[f] = {"cells": cnt, "diff_explore": float(np.mean(de)) if de else None, "diff_confirm": float(np.mean(dc)) if dc else None,
                  "improved_both": int(both)}
    return out


def analyze(arrays, n_perm=N_PERM):
    rows_all = []
    for p, A in arrays.items():
        rows_all += entries_of(p, A)
    E = to_arrays(rows_all, arrays)
    if E is None:
        return {"error": "合図が無い"}
    rows = build_table(E)
    top = pick_top(rows)
    picked = [dict(r, confirm=confirm_one(E, arrays, r, n_perm=n_perm)) for r in top]
    per_f = {}
    for f in FUNDS:
        best = pick_top([r for r in rows if r["f"] == f], k=1)
        per_f[f] = best[0] if best else None
    top10 = pick_top(rows, k=10)
    base = {k: next(r for r in rows if (r["f"], r["t"], r["osc"]) == k) for k in (("F0", "T1", "O1"), ("F0", "T1", "O4"), ("F0", "T0", "O1"))}
    fshare = {f: {"long": float((E["F"][:, i] > 0).mean()), "short": float((E["F"][:, i] < 0).mean())} for i, f in enumerate(F_KEYS)}
    return {"entries": int(len(E["r"])), "explore_n": int(E["explore"].sum()), "confirm_n": int((~E["explore"]).sum()),
            "rows": rows, "picked": picked, "per_fund_best": per_f, "top10": top10, "baseline": {"×".join(k): v for k, v in base.items()},
            "fund_effect": fund_effect(rows), "fund_share": fshare,
            "all_cost_mean": float(E["cost"].mean()), "all_swap_mean": float(E["swap"].mean())}


# ════════════════════ 読み込み ════════════════════

def load_all(fx_root=None):
    import fx_bars
    reer_text = FV._must(FV.get_text, FV.BIS_REER_URLS[0])
    p = FV.parse_sdmx_csv(reer_text, ("REF_AREA",))
    reer = {c: p.get((FV.BIS_AREA[c],), {}) for c in FV.CCYS}
    cpi, cfreq = FV.pick_cpi(FV.parse_sdmx_csv(FV._must(FV.get_text, FV.BIS_CPI_URLS[0]), ("FREQ", "REF_AREA", "UNIT_MEASURE")))
    text, _ = FV.get_text(FV.OECD_UNE_URLS[0])
    une, ufreq = FV.pick_une(FV.parse_sdmx_csv(text, FV.UNE_DIMS)) if text else ({}, {})
    if len(une) < FV.MIN_CCY:
        une, ufreq = {}, {}
    rates, bis_url = T.fetch_bis()
    months = FV.month_list(FIRST, LAST)
    fund = fund_states(rates, reer, cpi, cfreq, une, ufreq, months)
    bars = {}
    for pr in PAIRS:
        bars[pr] = bars_4h(fx_bars.load(pr, root=fx_root, start=fx_bars.EARLY[0]))
    info = {"bis_url": bis_url, "une_used": sorted(une),
            "bars": {pr: ([str(b.index.min()), str(b.index.max()), int(len(b))] if b is not None and len(b) else None) for pr, b in bars.items()}}
    return bars, fund, rates, info


def check():
    bars, fund, rates, info = load_all()
    rep = dict(info)
    rep["prereg_sha256"] = P.prereg_sha256()
    sigs = {}
    for pr, b in bars.items():
        if b is None or len(b) < WARMUP + CAP:
            continue
        s = CL.osc_signals(b)
        sigs[pr] = {f"{o}/{side}": int(m[WARMUP:].sum()) for (o, side), m in s.items()}
    rep["osc_signals"] = sigs
    allv = [v for p in fund for v in fund[p].values()]
    rep["fund_share"] = {f: {"plus": float(np.mean([x[i] > 0 for x in allv])), "minus": float(np.mean([x[i] < 0 for x in allv]))}
                         for i, f in enumerate(F_KEYS)} if allv else None
    rep["rates_missing_months"] = {c: sum(1 for t in FV.month_list(FIRST, LAST) if T.rate_at(rates, FV.BIS_AREA[c], FV.ymk(t)) is None)
                                   for c in FV.CCYS} if rates else "BIS に届かない"
    return rep


def render_md(res):
    L = ["# F3 ファンダの向き × トレンド × オシレーター（4時間足・為替12ペア）", "",
         f"更新: {res.get('generated_at', '')}（事前登録＝`PILLAR_PREREG.md`「F3」・指紋 `{(res.get('prereg_sha256') or '')[:12]}`）", ""]
    r = res.get("result") or {}
    if "error" in r:
        return "\n".join(L + [f"⚠️ 計算できず：{r['error']}", "", "※ 研究の記録です。投資助言ではありません。"]) + "\n"
    rr = lambda v: "—" if v is None else f"{v:+.3f}R"
    L += ["ファンダの向き（前の月末に決める）・トレンド・オシレーターの向きがそろったら、次の4時間足の始値で入る。損切り1.5ATR・利確2ATR・最長20本・"
          "金曜 UTC 04:00 の足の始値で手じまい。費用（max（1.2／1.8pips, 実際の差））とスワップ（政策金利の差 − 年1％）を R で引いた値。",
          f"1回ごとの合図 {r['entries']:,}件（前半 {r['explore_n']:,}・後半 {r['confirm_n']:,}）・平均の費用 {rr(r['all_cost_mean'])}・平均のスワップ {rr(r['all_swap_mean'])}", "",
          "## 判定（前半 2004〜2014 の上位3つを、後半 2015〜 で1回だけ確かめた）", "",
          "| 組み合わせ | 前半（件数・平均） | 後半の件数 | 後半の平均 | 95%の幅 | 偽薬 p | ファンダなしの後半 | トレンドなしの後半 | 判定 |",
          "|---|---:|---:|---:|---|---:|---:|---:|---|"]
    for x in r["picked"]:
        c = x["confirm"]
        L.append(f"| {x['f']} {FUNDS[x['f']]}×{x['t']} {CL.TREND_NAMES[x['t']]}×{x['osc']} {CL.OSCS[x['osc']]} | {x['n_e']}・{rr(x['m_e'])} | {c['n']} | "
                 f"{rr(c.get('mean'))} | {rr(c.get('lo'))}〜{rr(c.get('hi'))} | {'—' if c['p_placebo'] is None else format(c['p_placebo'], '.4f')} | "
                 f"{rr(c.get('f0_mean'))} | {rr(c.get('t0_mean'))} | **{c['verdict']}** |")
    L += ["", "## 読むための表（判定しない）", "", "### ファンダの向きの効き目（同じトレンド×オシレーターで F − F0）", "",
          "| ファンダ | マス | 前半の差 | 後半の差 | 前半・後半とも良くなったマス | 買い／売りの向きの割合 |", "|---|---:|---:|---:|---:|---|"]
    for f in F_KEYS:
        e = r["fund_effect"][f]
        sh = r["fund_share"][f]
        L.append(f"| {f} {FUNDS[f]} | {e['cells']} | {rr(e['diff_explore'])} | {rr(e['diff_confirm'])} | {e['improved_both']} | "
                 f"{sh['long'] * 100:.0f}％／{sh['short'] * 100:.0f}％ |")
    L += ["", "### ファンダごとの前半1位とその後半", "", "| ファンダ | 組み合わせ | 前半 | 後半 |", "|---|---|---:|---:|"]
    for f, x in r["per_fund_best"].items():
        if x:
            L.append(f"| {f} | {x['t']}×{x['osc']} | {x['n_e']}・{rr(x['m_e'])} | {x['n_c']}・{rr(x['m_c'])} |")
    L += ["", "### 前半の上位10の後半", "", "| 組み合わせ | 前半 | 後半 |", "|---|---:|---:|"]
    for x in r["top10"]:
        L.append(f"| {x['f']}×{x['t']}×{x['osc']} | {x['n_e']}・{rr(x['m_e'])} | {x['n_c']}・{rr(x['m_c'])} |")
    L += ["", "### いまのエンジンに近い組み合わせ（ファンダなし）", ""]
    for k, x in r["baseline"].items():
        L.append(f"- {k}：前半 {x['n_e']}・{rr(x['m_e'])}／後半 {x['n_c']}・{rr(x['m_c'])}")
    L += ["", "## 注意", "", "- 為替だけ・4時間足だけ・出口は1つだけ。経済の数字は今の値（改定後）で、発表の遅れを見込んだ。スワップは政策金利で近づけた目安",
          "- 360通りの全部の表は `fund-combo-lab.json` の rows。前半で良かった組み合わせほど、後半で落ちやすい（偶然の当たりを選ぶため）", "", "---", "",
          "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。"]
    return "\n".join(L) + "\n"


def main(argv):
    if "--check" in argv:
        print(json.dumps(check(), ensure_ascii=False, indent=1, default=str))
        return 0
    res = {"generated_at": dt.datetime.now(P.JST).isoformat(timespec="minutes"), "prereg_file": P.PREREG,
           "prereg_sha256": P.prereg_sha256(), "kind": "combo"}
    try:
        bars, fund, rates, info = load_all()
        if not rates:
            raise RuntimeError("BIS の政策金利に届かない（スワップとファンダの向きを数えられない）")
        arrays = {p: pair_arrays(p, b, fund[p], rates) for p, b in bars.items() if b is not None and len(b) > WARMUP + CAP}
        r = analyze(arrays)
        r.update(info)
        res["result"] = r
    except Exception as e:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        res["result"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(M.rounded(res), fh, ensure_ascii=False, indent=1, default=str)
    md = render_md(res)
    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
