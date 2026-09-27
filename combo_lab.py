# -*- coding: utf-8 -*-
"""組み合わせの相性ラボ（トレンド×オシレーター×出口・2026-09-27 オーナー「どれが一番相性いいか調べて」）。

トレンド10（なし＋T1〜T9）×オシレーター6×出口6＝360通り。前半（2015年まで）で上位3つを選び、後半（2016年から）で1回だけ確かめる。
⚠️ 決まりは PILLAR_PREREG.md「組み合わせの相性ラボ」と下の定数に固定。結果を見てから動かさない。
⚠️ 出力 combo-lab.json / combo-lab.md は GitHub 側で生成＝手元から送らない（SYNC禁忌）。
⚠️ エンジン・発火条件・固定オラクルには触れない（計算の関数を読むだけ）。

実行: python combo_lab.py   （Actions の combo-lab.yml から手動で）
"""
import datetime as dt
import json
import math
import sys

import numpy as np
import pandas as pd

import pillar_lab as P
import trend_lab as TL
from generate_technical_alerts import calc_bbands, calc_rsi
from signal_lab_sweep import cost_r_of

OUT_JSON, OUT_MD = "combo-lab.json", "combo-lab.md"
SPLIT = "2016-01-01"            # 前半（選ぶ）＝2015年まで／後半（確かめる）＝2016年から
MIN_N_EXPLORE = 150
TOP_K = 3
P_LIMIT = 0.05 / TOP_K
COOLDOWN = 5
RISK_ATR = 1.5                  # 1R＝ATR14×1.5
N_PERM = 2000

TRENDS = ["T0"] + list(TL.NAMES)
TREND_NAMES = dict(T0="トレンドなし", **TL.NAMES)
OSCS = {"O1": "RSI（14）の戻り", "O2": "2日RSIの深い押し目", "O3": "ストキャスティクス", "O4": "ボリンジャー下限タッチ",
        "O5": "CCI（20）", "O6": "ウィリアムズ%R"}
EXITS = {"X1": "いまの方式（損切り1.5・利確2・20本）", "X2": "利確を伸ばす（1.5・3・30本）",
         "X3": "損切りを広げる（3・2・20本）", "X4": "5本目の終値", "X5": "5本線を越えたら（保険3・10本）",
         "X6": "追いかける損切り（3ATR・60本）"}
EXIT_RULE = {"X1": (1.5, 2.0, 20), "X2": (1.5, 3.0, 30), "X3": (3.0, 2.0, 20)}


# ════════════════════ オシレーター ════════════════════

def stoch(h, l, c, n=14, k=3, d=3):
    H, L_, C = pd.Series(h), pd.Series(l), pd.Series(c)
    lo, hi = L_.rolling(n).min(), H.rolling(n).max()
    fast = 100 * (C - lo) / (hi - lo).replace(0, np.nan)
    kk = fast.rolling(k).mean()
    return kk.values, kk.rolling(d).mean().values


def cci(h, l, c, n=20):
    tp = pd.Series((h + l + c) / 3)
    sma = tp.rolling(n).mean()
    mad = tp.rolling(n).apply(lambda x: np.mean(np.abs(x - x.mean())), raw=True)
    return ((tp - sma) / (0.015 * mad.replace(0, np.nan))).values


def williams_r(h, l, c, n=14):
    H, L_, C = pd.Series(h), pd.Series(l), pd.Series(c)
    hi, lo = H.rolling(n).max(), L_.rolling(n).min()
    return (-100 * (hi - C) / (hi - lo).replace(0, np.nan)).values


def _prev(x):
    return np.concatenate([[np.nan], x[:-1]])


def osc_signals(df):
    """{(O, 'long'|'short'): 合図の足の真偽}（その足の終値までで判定）"""
    o, h, l, c = (np.asarray(df[k].values, float) for k in ("Open", "High", "Low", "Close"))
    C = pd.Series(c)
    r14 = calc_rsi(C).values
    r2 = calc_rsi(C, period=2).values
    k, d = stoch(h, l, c)
    bbu, _, bbl = (x.values for x in calc_bbands(C))
    width = bbu - bbl
    with np.errstate(invalid="ignore", divide="ignore"):
        pos = np.where(width > 0, (c - bbl) / width, 0.5)
    cc = cci(h, l, c)
    wr = williams_r(h, l, c)
    rp, kp, dp, ccp, wrp = _prev(r14), _prev(k), _prev(d), _prev(cc), _prev(wr)
    with np.errstate(invalid="ignore"):
        sig = {
            ("O1", "long"): (rp < 30) & (r14 > rp) & (r14 < 50),
            ("O1", "short"): (rp > 70) & (r14 < rp) & (r14 > 50),
            ("O2", "long"): r2 < 10,
            ("O2", "short"): r2 > 90,
            ("O3", "long"): (kp < 20) & (kp <= dp) & (k > d),
            ("O3", "short"): (kp > 80) & (kp >= dp) & (k < d),
            ("O4", "long"): (l <= bbl) & (c > l) & (pos < 0.3),
            ("O4", "short"): (h >= bbu) & (c < h) & (pos > 0.7),
            ("O5", "long"): (ccp < -100) & (cc > -100),
            ("O5", "short"): (ccp > 100) & (cc < 100),
            ("O6", "long"): (wrp < -80) & (wr > -80),
            ("O6", "short"): (wrp > -20) & (wr < -20),
        }
    return {key: np.nan_to_num(v.astype(float)) > 0 for key, v in sig.items()}


# ════════════════════ 出口 ════════════════════

def simulate(o, h, l, c, ma5, atr_i, i, side, ex):
    """合図の足 i → 次の足 i+1 の始値で入る。戻り値＝R（費用前）と入った足の位置。足りなければ None"""
    e = i + 1
    n = len(c)
    if e >= n or not atr_i > 0:
        return None
    s = 1.0 if side == "long" else -1.0
    entry = o[e]
    unit = RISK_ATR * atr_i

    def r_of(px):
        return s * (px - entry) / unit

    if ex in EXIT_RULE:
        sl_m, tp_m, cap = EXIT_RULE[ex]
        sl, tp = entry - s * sl_m * atr_i, entry + s * tp_m * atr_i
        if e + cap - 1 >= n:
            return None
        for k in range(e, e + cap):
            if s > 0:
                if o[k] <= sl:
                    return r_of(o[k])
                if l[k] <= sl:
                    return r_of(sl)
                if o[k] >= tp:
                    return r_of(o[k])
                if h[k] >= tp:
                    return r_of(tp)
            else:
                if o[k] >= sl:
                    return r_of(o[k])
                if h[k] >= sl:
                    return r_of(sl)
                if o[k] <= tp:
                    return r_of(o[k])
                if l[k] <= tp:
                    return r_of(tp)
        return r_of(c[e + cap - 1])
    if ex == "X4":
        return None if e + 4 >= n else r_of(c[e + 4])
    if ex == "X5":
        cap = 10
        if e + cap - 1 >= n:
            return None
        sl = entry - s * 3.0 * atr_i
        for k in range(e, e + cap):
            if s > 0 and (o[k] <= sl or l[k] <= sl):
                return r_of(min(o[k], sl))
            if s < 0 and (o[k] >= sl or h[k] >= sl):
                return r_of(max(o[k], sl))
            if (s > 0 and c[k] > ma5[k]) or (s < 0 and c[k] < ma5[k]):
                return r_of(c[k])
        return r_of(c[e + cap - 1])
    if ex == "X6":
        cap = 60
        if e + cap - 1 >= n:
            return None
        stop = entry - s * 3.0 * atr_i
        ext = entry
        for k in range(e, e + cap):
            if s > 0:
                if o[k] <= stop:
                    return r_of(o[k])
                if l[k] <= stop:
                    return r_of(stop)
                ext = max(ext, h[k])
                stop = max(stop, ext - 3.0 * atr_i)
            else:
                if o[k] >= stop:
                    return r_of(o[k])
                if h[k] >= stop:
                    return r_of(stop)
                ext = min(ext, l[k])
                stop = min(stop, ext + 3.0 * atr_i)
        return r_of(c[e + cap - 1])
    raise ValueError(ex)


def _series(df):
    o, h, l, c = (np.asarray(df[k].values, float) for k in ("Open", "High", "Low", "Close"))
    atr = TL.rma(TL.true_range(h, l, c), 14)
    ma5 = pd.Series(c).rolling(5).mean().values
    return o, h, l, c, atr, ma5


def entries_for(ticker, df):
    """オシレーターの合図ごとに6つの出口の R（費用後）と、合図の足での T1〜T9 の向きを持つ1件"""
    o, h, l, c, atr, ma5 = _series(df)
    states = TL.all_states(df)
    sig = osc_signals(df)
    out = []
    for (osc, side), mask in sig.items():
        last = -10 ** 9
        for i in np.flatnonzero(mask):
            if i < TL.WARMUP or i + 1 >= len(c) or i - last < COOLDOWN:
                continue
            last = i
            rs = {}
            for ex in EXITS:
                r = simulate(o, h, l, c, ma5, atr[i], i, side, ex)
                if r is None:
                    rs = None
                    break
                unit = RISK_ATR * atr[i]
                rs[ex] = r - cost_r_of({"entry": o[i + 1], "stop_loss": o[i + 1] - unit, "ticker": ticker})
            if rs is None:
                continue
            out.append({"ticker": ticker, "date": df.index[i + 1].date().isoformat(), "osc": osc,
                        "sign": 1.0 if side == "long" else -1.0,
                        "st": [float(states[k][i]) for k in TL.NAMES], "R": rs})
    return out


# ════════════════════ 並べる・選ぶ・確かめる ════════════════════

def trend_ok(entry, t):
    return t == "T0" or entry["st"][list(TL.NAMES).index(t)] == entry["sign"]


def combo_values(entries, t, osc, ex, period=None):
    xs = [e for e in entries if e["osc"] == osc and trend_ok(e, t)]
    if period == "explore":
        xs = [e for e in xs if e["date"] < SPLIT]
    elif period == "confirm":
        xs = [e for e in xs if e["date"] >= SPLIT]
    return xs, [e["R"][ex] for e in xs]


def table(entries):
    """360通りの 前半・後半 の件数と平均（オシレーターごと・トレンドごとに1回だけ絞る）"""
    by_osc = {o: [e for e in entries if e["osc"] == o] for o in OSCS}
    rows = []
    for t in TRENDS:
        for osc in OSCS:
            xs = [e for e in by_osc[osc] if trend_ok(e, t)]
            ea = [e for e in xs if e["date"] < SPLIT]
            ca = [e for e in xs if e["date"] >= SPLIT]
            for ex in EXITS:
                a = [e["R"][ex] for e in ea]
                b = [e["R"][ex] for e in ca]
                rows.append({"t": t, "osc": osc, "ex": ex, "n_e": len(a), "m_e": P._mean(a), "n_c": len(b), "m_c": P._mean(b)})
    return rows


def pick_top(rows, k=TOP_K, min_n=MIN_N_EXPLORE):
    ok = [r for r in rows if r["n_e"] >= min_n and r["m_e"] is not None]
    return sorted(ok, key=lambda r: (-r["m_e"], -r["n_e"]))[:k]


def confirm_stats(xs, vals):
    groups = [(e["ticker"], e["date"][:4]) for e in xs]
    return P.mean_ci(vals, groups)


def placebo(pool_by, counts, n_perm=N_PERM, seed=P.SEED):
    """pool_by[(ticker, sign)] = でたらめな入口の R の配列。counts[(ticker, sign)] = 本物の件数"""
    rng = np.random.default_rng(seed)
    keys = [k for k in counts if len(pool_by.get(k, [])) > 0]
    total = sum(counts[k] for k in keys)
    if not total:
        return None
    sims = np.empty(n_perm)
    for j in range(n_perm):
        s = 0.0
        for k in keys:
            pool = pool_by[k]
            s += float(pool[rng.integers(0, len(pool), counts[k])].sum())
        sims[j] = s / total
    return sims


def random_pool(data, t, ex):
    """後半の、同じトレンドの条件を満たす全部の日に入った場合の R（費用後）"""
    pool = {}
    for tk, df in data.items():
        o, h, l, c, atr, ma5 = _series(df)
        states = data_states(tk, df)
        dates = np.array([x.date().isoformat() for x in df.index])
        for side, s in (("long", 1.0), ("short", -1.0)):
            vals = []
            for i in range(TL.WARMUP, len(c) - 1):
                if dates[i + 1] < SPLIT:
                    continue
                if t != "T0" and states[t][i] != s:
                    continue
                r = simulate(o, h, l, c, ma5, atr[i], i, side, ex)
                if r is None:
                    continue
                unit = RISK_ATR * atr[i]
                vals.append(r - cost_r_of({"entry": o[i + 1], "stop_loss": o[i + 1] - unit, "ticker": tk}))
            pool[(tk, s)] = np.array(vals)
    return pool


_STATES = {}


def data_states(tk, df):
    if tk not in _STATES:
        _STATES[tk] = TL.all_states(df)
    return _STATES[tk]


def judge(st, p):
    lo = st.get("lo")
    if lo is None or p is None:
        return "確かめで消えた"
    return "確かめでも残った（有望）" if (lo > 0 and p < P_LIMIT) else "確かめで消えた"


def run(n_perm=N_PERM):
    data, entries, missing = {}, [], []
    for tk in TL.TICKERS:
        df = P.fetch(tk, "1d", start=TL.START)
        if df is None or len(df) < TL.WARMUP + 80:
            missing.append(tk)
            continue
        df = df.dropna(subset=["Open", "High", "Low", "Close"])
        data[tk] = df
        entries += entries_for(tk, df)
    rows = table(entries)
    top = pick_top(rows)
    picked = []
    for r in top:
        xs, vals = combo_values(entries, r["t"], r["osc"], r["ex"], "confirm")
        st = confirm_stats(xs, vals) if len(vals) >= 2 else {"n": len(vals), "mean": P._mean(vals)}
        counts = {}
        for e in xs:
            counts[(e["ticker"], e["sign"])] = counts.get((e["ticker"], e["sign"]), 0) + 1
        sims = placebo(random_pool(data, r["t"], r["ex"]), counts, n_perm=n_perm) if counts else None
        p = None
        if sims is not None and st.get("mean") is not None:
            cen = float(np.mean(sims))
            p = float((np.sum(np.abs(sims - cen) >= abs(st["mean"] - cen)) + 1) / (len(sims) + 1))
            st["placebo_mean"] = cen
        st["p_placebo"] = p
        _, t0 = combo_values(entries, "T0", r["osc"], r["ex"], "confirm")
        st["t0_mean"] = P._mean(t0)
        st["verdict"] = judge(st, p)
        picked.append(dict(r, confirm=st))
    base = {f"{t}×{o}×{x}": next(r for r in rows if (r["t"], r["osc"], r["ex"]) == (t, o, x))
            for t, o, x in (("T1", "O1", "X1"), ("T1", "O4", "X1"))}
    top10 = sorted([r for r in rows if r["n_e"] >= MIN_N_EXPLORE and r["m_e"] is not None],
                   key=lambda r: -r["m_e"])[:10]
    return {"entries": len(entries), "missing": missing, "rows": rows, "picked": picked, "top10": top10, "baseline": base}


# ════════════════════ 出力 ════════════════════

def _name(r):
    return f"{TREND_NAMES[r['t']]} × {OSCS[r['osc']]} × {EXITS[r['ex']]}"


def render_md(res):
    f = P._f
    L = ["# 組み合わせの相性ラボ（トレンド×オシレーター×出口）", "",
         f"作成: {res['generated_at']}（GitHub Actions で計算）。事前登録＝`{P.PREREG}`「組み合わせの相性ラボ」（指紋 sha256 `{(res.get('prereg_sha256') or '')[:16]}…`）。",
         "値＝1回の取引の損益（R・費用後。1R＝入る時の ATR×1.5）。**売買の決まりではない**。", ""]
    r = res.get("result") or {}
    if r.get("error"):
        return "\n".join(L + [f"- ⚠️ 計算できず: {r['error']}", ""]) + "\n"
    L += [f"## 前半（2015年まで）で選んだ上位{TOP_K}つを、後半（2016年から）で1回だけ確かめた結果", "",
          f"判定＝後半の平均Rの95%の幅がまるごと0より上・偽薬との比較 p＜{P_LIMIT:.4f}", "",
          "| 組み合わせ | 前半 件数 | 前半 平均R | 後半 件数 | 後半 平均R | 95%の幅 | 偽薬の平均 | p | トレンドなしの後半 | 判定 |",
          "|---|---:|---:|---:|---:|---|---:|---:|---:|---|"]
    for x in r.get("picked") or []:
        c = x["confirm"]
        L.append(f"| {_name(x)} | {x['n_e']} | {f(x['m_e'])} | {c.get('n', 0)} | {f(c.get('mean'))} | "
                 f"{f(c.get('lo'))}〜{f(c.get('hi'))} | {f(c.get('placebo_mean'))} | {f(c.get('p_placebo'), 4, False)} | "
                 f"{f(c.get('t0_mean'))} | {c.get('verdict')} |")
    rows = r.get("rows") or []
    get = {(x["t"], x["osc"], x["ex"]): x for x in rows}
    L += ["", "## 読むための表（判定しない）", "", "### 前半の上位10は、後半でどうなったか", "",
          "| 組み合わせ | 前半 件数 | 前半 平均R | 後半 件数 | 後半 平均R |", "|---|---:|---:|---:|---:|"]
    for x in r.get("top10") or []:
        L.append(f"| {_name(x)} | {x['n_e']} | {f(x['m_e'])} | {x['n_c']} | {f(x['m_c'])} |")
    L += ["", "### トレンド×オシレーター（出口はいまの方式 X1）：前半の平均R／後半の平均R", "",
          "| トレンド | " + " | ".join(OSCS[o] for o in OSCS) + " |", "|---|" + "---:|" * len(OSCS)]
    for t in TRENDS:
        L.append(f"| {TREND_NAMES[t]} | " + " | ".join(
            f"{f(get[(t, o, 'X1')]['m_e'])}／{f(get[(t, o, 'X1')]['m_c'])}" for o in OSCS) + " |")
    L += ["", "### オシレーター×出口（トレンドなし）：前半の平均R／後半の平均R", "",
          "| オシレーター | " + " | ".join(EXITS[x] for x in EXITS) + " |", "|---|" + "---:|" * len(EXITS)]
    for o in OSCS:
        L.append(f"| {OSCS[o]} | " + " | ".join(
            f"{f(get[('T0', o, x)]['m_e'])}／{f(get[('T0', o, x)]['m_c'])}" for x in EXITS) + " |")
    L += ["", "### いまのエンジンに近い組み合わせ", ""]
    for k, x in (r.get("baseline") or {}).items():
        L.append(f"- {_name(x)}：前半 {x['n_e']}件 {f(x['m_e'])}／後半 {x['n_c']}件 {f(x['m_c'])}")
    L += ["", f"- 数えた合図 {r.get('entries')} 件" + (f"・値段を取れなかった銘柄 {', '.join(r['missing'])}" if r.get("missing") else ""),
          "", "---", "", "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。"]
    return "\n".join(L) + "\n"


def main():
    res = {"generated_at": dt.datetime.now(P.JST).isoformat(timespec="minutes"),
           "prereg_file": P.PREREG, "prereg_sha256": P.prereg_sha256()}
    try:
        res["result"] = run()
    except Exception as e:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        res["result"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1, default=str)
    md = render_md(res)
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
