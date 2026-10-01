# -*- coding: utf-8 -*-
"""出口にテクニカル指標を使う研究 E1（損切りの指標8×利確の指標8×入口60＝3,840通り）。

決まりは PILLAR_PREREG.md「E1」と下の定数に固定。結果を見てから動かさない。
入口は combo_lab（トレンド10×オシレーター6）を読むだけ。前半（2015年まで）で上位3つを選び、後半（2016年から）で1回だけ確かめる。
⚠️ 出力 exit-ind-lab.json / .md は GitHub 側で生成＝手元から送らない（SYNC禁忌）。
実行: python exit_ind_lab.py
"""
import datetime as dt
import json
import sys

import numpy as np
import pandas as pd

import combo_lab as CL
import pillar_lab as P
import trend_lab as TL
from generate_technical_alerts import calc_bbands, calc_rsi
from signal_lab_sweep import cost_r_of

OUT_JSON, OUT_MD = "exit-ind-lab.json", "exit-ind-lab.md"
SPLIT, MIN_N, TOP_K, P_LIMIT, N_PERM = CL.SPLIT, CL.MIN_N_EXPLORE, CL.TOP_K, CL.P_LIMIT, CL.N_PERM
CAP = 60
RISK_ATR = CL.RISK_ATR
NEAR, FAR = 0.5, 4.0     # 損切りの最初の位置＝入った値から 0.5〜4 ATR の間に収める

STOPS = {"S0": "固定（ATR×1.5・いまの方式）", "S1": "直近10本の安値（高値）", "S2": "パラボリックSAR", "S3": "シャンデリア（22本・3ATR）",
         "S4": "スーパートレンドの線", "S5": "一目均衡表の基準線", "S6": "25本移動平均", "S7": "ドンチャン20本の安値（高値）"}
TPS = {"P0": "固定（ATR×2・いまの方式）", "P1": "RSI 70以上（30以下）", "P2": "ボリンジャー +2σ（−2σ）", "P3": "ストキャスの下抜け（上抜け）",
       "P4": "MACD の下抜け（上抜け）", "P5": "CCI +100 からの下抜け（−100 から上抜け）", "P6": "ウィリアムズ%R −20以上（−80以下）", "P7": "利確の合図なし"}
SK, PK = list(STOPS), list(TPS)
EXITS = [(s, p) for s in SK for p in PK]      # 64通り


def _roll(x, n, fn):
    return getattr(pd.Series(x).rolling(n), fn)().values


def _nxt(sig):
    """nxt[k]＝k以降で最初に真になる位置（無ければ大きな数）"""
    n = len(sig)
    out = np.full(n + 1, 10 ** 9, dtype=np.int64)
    for k in range(n - 1, -1, -1):
        out[k] = k if sig[k] else out[k + 1]
    return out


def make_ctx(df):
    o, h, l, c = (np.asarray(df[k].values, float) for k in ("Open", "High", "Low", "Close"))
    atr = TL.rma(TL.true_range(h, l, c), 14)
    C = pd.Series(c)
    # 損切りの線（その足の終値までで決まる値）。long=下から追う線、short=上から追う線
    hl2 = (h + l) / 2
    a10 = TL.rma(TL.true_range(h, l, c), 10)
    bu, bl = hl2 + 3.0 * a10, hl2 - 3.0 * a10
    fu, fl = bu.copy(), bl.copy()
    for i in range(1, len(c)):
        fu[i] = bu[i] if (bu[i] < fu[i - 1] or c[i - 1] > fu[i - 1]) else fu[i - 1]
        fl[i] = bl[i] if (bl[i] > fl[i - 1] or c[i - 1] < fl[i - 1]) else fl[i - 1]
    kij = (_roll(h, 26, "max") + _roll(l, 26, "min")) / 2
    sma25 = _roll(c, 25, "mean")
    lines = {
        "S1": (_roll(l, 10, "min"), _roll(h, 10, "max")),
        "S3": (_roll(h, 22, "max") - 3.0 * atr, _roll(l, 22, "min") + 3.0 * atr),
        "S4": (fl, fu), "S5": (kij, kij), "S6": (sma25, sma25),
        "S7": (_roll(l, 20, "min"), _roll(h, 20, "max")),
    }
    # 利確の合図（その足の終値で判定）。long＝売り合図、short＝買い合図
    r14 = calc_rsi(C).values
    k, d = CL.stoch(h, l, c)
    bbu, _, bbl = (x.values for x in calc_bbands(C))
    e12, e26 = C.ewm(span=12, adjust=False).mean().values, C.ewm(span=26, adjust=False).mean().values
    macd = e12 - e26
    msig = pd.Series(macd).ewm(span=9, adjust=False).mean().values
    cc, wr = CL.cci(h, l, c), CL.williams_r(h, l, c)
    kp, dp, ccp, mp, msp = CL._prev(k), CL._prev(d), CL._prev(cc), CL._prev(macd), CL._prev(msig)
    with np.errstate(invalid="ignore"):
        sig = {
            "P1": (r14 >= 70, r14 <= 30),
            "P2": (c >= bbu, c <= bbl),
            "P3": ((kp > 80) & (kp >= dp) & (k < d), (kp < 20) & (kp <= dp) & (k > d)),
            "P4": ((mp >= msp) & (macd < msig), (mp <= msp) & (macd > msig)),
            "P5": ((ccp > 100) & (cc < 100), (ccp < -100) & (cc > -100)),
            "P6": (wr >= -20, wr <= -80),
        }
    nxt = {p: (_nxt(np.nan_to_num(a.astype(float)) > 0), _nxt(np.nan_to_num(b.astype(float)) > 0)) for p, (a, b) in sig.items()}
    return {"o": o, "h": h, "l": l, "c": c, "atr": atr, "lines": lines, "nxt": nxt, "n": len(c)}


def stop_event(x, e, s, A, S):
    """損切りに触れた (足の位置, 値)。CAP本のうちに触れなければ None"""
    o, h, l = x["o"], x["h"], x["l"]
    entry = o[e]
    lo_bound, hi_bound = (entry - FAR * A, entry - NEAR * A) if s > 0 else (entry + NEAR * A, entry + FAR * A)

    def clip(v):
        return min(max(v, lo_bound), hi_bound)

    if S == "S0":
        stop = entry - s * RISK_ATR * A
        for k in range(e, e + CAP):
            if s > 0:
                if o[k] <= stop:
                    return k, o[k]
                if l[k] <= stop:
                    return k, stop
            else:
                if o[k] >= stop:
                    return k, o[k]
                if h[k] >= stop:
                    return k, stop
        return None
    if S == "S2":
        sar = clip(float(np.min(l[e - 5:e])) if s > 0 else float(np.max(h[e - 5:e])))
        ep, af = (h[e - 1], 0.02) if s > 0 else (l[e - 1], 0.02)
        for k in range(e, e + CAP):
            if s > 0:
                if o[k] <= sar:
                    return k, o[k]
                if l[k] <= sar:
                    return k, sar
                if h[k] > ep:
                    ep, af = h[k], min(af + 0.02, 0.2)
                sar = max(sar, min(sar + af * (ep - sar), l[k], l[k - 1]))
            else:
                if o[k] >= sar:
                    return k, o[k]
                if h[k] >= sar:
                    return k, sar
                if l[k] < ep:
                    ep, af = l[k], min(af + 0.02, 0.2)
                sar = min(sar, max(sar + af * (ep - sar), h[k], h[k - 1]))
        return None
    line = x["lines"][S][0 if s > 0 else 1]
    v = line[e - 1]
    if not np.isfinite(v):
        return None
    stop = clip(v)
    for k in range(e, e + CAP):
        if s > 0:
            if o[k] <= stop:
                return k, o[k]
            if l[k] <= stop:
                return k, stop
            if np.isfinite(line[k]):
                stop = max(stop, line[k])
        else:
            if o[k] >= stop:
                return k, o[k]
            if h[k] >= stop:
                return k, stop
            if np.isfinite(line[k]):
                stop = min(stop, line[k])
    return None


def tp_event(x, e, s, A, Pn):
    """利確の (足の位置, 値)。無ければ None。P0 は足の中、P1〜P6 は終値の合図の次の足の始値"""
    if Pn == "P7":
        return None
    o, h, l = x["o"], x["h"], x["l"]
    if Pn == "P0":
        tp = o[e] + s * 2.0 * A
        for k in range(e, e + CAP):
            if s > 0:
                if o[k] >= tp:
                    return k, o[k]
                if h[k] >= tp:
                    return k, tp
            else:
                if o[k] <= tp:
                    return k, o[k]
                if l[k] <= tp:
                    return k, tp
        return None
    k = int(x["nxt"][Pn][0 if s > 0 else 1][e])
    if k > e + CAP - 2 or k + 1 >= x["n"]:
        return None
    return k, o[k + 1]


def outcome(x, e, s, A, S, Pn, se=None, te=None):
    """出口後の R（費用前）。同じ足の中で損切りと利確が両方なら損切りが先。
    P0 は足の中の指値なので te[0] < se[0] のときだけ利確。P1〜P6 は合図の足（te[0]）の次の始値で出るので te[0] < se[0] のとき利確"""
    unit = RISK_ATR * A
    entry = x["o"][e]
    if se is None:
        se = stop_event(x, e, s, A, S)
    if te is None:
        te = tp_event(x, e, s, A, Pn)
    px = x["c"][e + CAP - 1]
    if se is not None and te is not None:
        px = te[1] if te[0] < se[0] else se[1]
    elif se is not None:
        px = se[1]
    elif te is not None:
        px = te[1]
    return s * (px - entry) / unit


def entries_for(tk, df, x):
    n = x["n"]
    states = TL.all_states(df)
    sig = CL.osc_signals(df)
    out = []
    for (osc, side), mask in sig.items():
        s = 1.0 if side == "long" else -1.0
        last = -10 ** 9
        for i in np.flatnonzero(mask):
            if i < TL.WARMUP or i + 1 >= n or i - last < CL.COOLDOWN:
                continue
            last = i
            e = i + 1
            A = x["atr"][i]
            if e + CAP - 1 >= n or not A > 0:
                continue
            se = {S: stop_event(x, e, s, A, S) for S in SK}
            tes = {p: tp_event(x, e, s, A, p) for p in PK}
            unit = RISK_ATR * A
            cost = cost_r_of({"entry": x["o"][e], "stop_loss": x["o"][e] - unit, "ticker": tk})
            R = [outcome(x, e, s, A, S, p, se[S], tes[p]) - cost for S, p in EXITS]
            out.append({"ticker": tk, "date": df.index[e].date().isoformat(), "osc": osc, "sign": s,
                        "st": [float(states[k][i]) for k in TL.NAMES], "R": R})
    return out


def table(entries):
    names = list(TL.NAMES)
    R = np.array([e["R"] for e in entries])
    front = np.array([e["date"] < SPLIT for e in entries])
    oscs = np.array([e["osc"] for e in entries])
    sign = np.array([e["sign"] for e in entries])
    st = np.array([e["st"] for e in entries])
    rows = []
    for t in CL.TRENDS:
        tm = np.ones(len(entries), bool) if t == "T0" else (st[:, names.index(t)] == sign)
        for osc in CL.OSCS:
            m = tm & (oscs == osc)
            fe, ba = m & front, m & ~front
            me = R[fe].mean(axis=0) if fe.sum() else np.full(len(EXITS), np.nan)
            mc = R[ba].mean(axis=0) if ba.sum() else np.full(len(EXITS), np.nan)
            for j, (S, p) in enumerate(EXITS):
                rows.append({"t": t, "osc": osc, "s": S, "p": p, "n_e": int(fe.sum()),
                             "m_e": None if np.isnan(me[j]) else float(me[j]),
                             "n_c": int(ba.sum()), "m_c": None if np.isnan(mc[j]) else float(mc[j])})
    return rows, R, front


def random_pool(data, ctxs, t, S, Pn):
    pool = {}
    for tk, df in data.items():
        x = ctxs[tk]
        states = CL.data_states(tk, df)
        dates = np.array([d.date().isoformat() for d in df.index])
        for s in (1.0, -1.0):
            vals = []
            for i in range(TL.WARMUP, x["n"] - 1):
                e = i + 1
                if dates[e] < SPLIT or e + CAP - 1 >= x["n"]:
                    continue
                if t != "T0" and states[t][i] != s:
                    continue
                A = x["atr"][i]
                if not A > 0:
                    continue
                unit = RISK_ATR * A
                vals.append(outcome(x, e, s, A, S, Pn) - cost_r_of({"entry": x["o"][e], "stop_loss": x["o"][e] - unit, "ticker": tk}))
            pool[(tk, s)] = np.array(vals)
    return pool


def _daily(tk):
    return P.fetch(tk, "1d", start=TL.START)


def run(n_perm=N_PERM, loader=None):
    """loader＝銘柄→足（既定は日足）。🆕 2026-10-01 M7 の腕A（4時間足）が束ねた足を渡す。既定の動きは変わらない"""
    load = loader or _daily
    data, ctxs, entries, missing = {}, {}, [], []
    for tk in TL.TICKERS:
        df = load(tk)
        if df is None or len(df) < TL.WARMUP + 80:
            missing.append(tk)
            continue
        df = df.dropna(subset=["Open", "High", "Low", "Close"])
        data[tk] = df
        ctxs[tk] = make_ctx(df)
        entries += entries_for(tk, df, ctxs[tk])
    rows, R, front = table(entries)
    ok = [r for r in rows if r["n_e"] >= MIN_N and r["m_e"] is not None]
    top = sorted(ok, key=lambda r: (-r["m_e"], -r["n_e"]))[:TOP_K]
    names = list(TL.NAMES)
    picked = []
    for r in top:
        j = EXITS.index((r["s"], r["p"]))
        xs = [(e, e["R"][j]) for e in entries if e["osc"] == r["osc"] and e["date"] >= SPLIT
              and (r["t"] == "T0" or e["st"][names.index(r["t"])] == e["sign"])]
        vals = [v for _, v in xs]
        st = CL.confirm_stats([e for e, _ in xs], vals) if len(vals) >= 2 else {"n": len(vals), "mean": P._mean(vals)}
        counts = {}
        for e, _ in xs:
            counts[(e["ticker"], e["sign"])] = counts.get((e["ticker"], e["sign"]), 0) + 1
        sims = CL.placebo(random_pool(data, ctxs, r["t"], r["s"], r["p"]), counts, n_perm=n_perm) if counts else None
        p = None
        if sims is not None and st.get("mean") is not None:
            cen = float(np.mean(sims))
            p = float((np.sum(np.abs(sims - cen) >= abs(st["mean"] - cen)) + 1) / (len(sims) + 1))
            st["placebo_mean"] = cen
        st["p_placebo"] = p
        st["verdict"] = CL.judge(st, p)
        picked.append(dict(r, confirm=st))
    grid = {f"{S}{p}": [float(R[front, j].mean()), float(R[~front, j].mean())] for j, (S, p) in enumerate(EXITS)}
    by_s, by_p = {}, {}
    for S in SK:
        js = [j for j, (a, _) in enumerate(EXITS) if a == S]
        by_s[S] = [float(R[front][:, js].mean()), float(R[~front][:, js].mean())]
    for p in PK:
        js = [j for j, (_, b) in enumerate(EXITS) if b == p]
        by_p[p] = [float(R[front][:, js].mean()), float(R[~front][:, js].mean())]
    top10 = sorted(ok, key=lambda r: -r["m_e"])[:10]
    base = {o: next(r for r in rows if (r["t"], r["osc"], r["s"], r["p"]) == ("T0", o, "S0", "P0")) for o in CL.OSCS}
    return {"entries": len(entries), "missing": missing, "combos": len(rows), "picked": picked, "top10": top10,
            "grid": grid, "by_s": by_s, "by_p": by_p, "baseline": base}


def _name(r):
    return f"{CL.TREND_NAMES[r['t']]} × {CL.OSCS[r['osc']]} × 損切り:{STOPS[r['s']]} × 利確:{TPS[r['p']]}"


def render_md(res, title="出口にテクニカル指標を使う研究 E1（損切り8 × 利確8 × 入口60）", section="E1",
              front="2015年まで", back="2016年から"):
    """🆕 2026-10-01 title・section・前半後半の言葉は M7 の腕A（4時間足）が差し替える。既定は E1 のまま"""
    f = P._f
    L = [f"# {title}", "",
         f"作成: {res['generated_at']}（GitHub Actions で計算）。事前登録＝`{P.PREREG}`「{section}」（指紋 sha256 `{(res.get('prereg_sha256') or '')[:16]}…`）。",
         "値＝1回の取引の損益（R・費用後。1R＝入る時の ATR×1.5）。**売買の決まりではない**。", ""]
    r = res.get("result") or {}
    if r.get("error"):
        return "\n".join(L + [f"- ⚠️ 計算できず: {r['error']}", ""]) + "\n"
    L += [f"## 前半（{front}）で選んだ上位{TOP_K}つを、後半（{back}）で1回だけ確かめた結果（{r['combos']}通りから）", "",
          f"判定＝後半の平均Rの95%の幅がまるごと0より上・偽薬との比較 p＜{P_LIMIT:.4f}", "",
          "| 組み合わせ | 前半 件数 | 前半 平均R | 後半 件数 | 後半 平均R | 95%の幅 | 偽薬の平均 | p | 判定 |",
          "|---|---:|---:|---:|---:|---|---:|---:|---|"]
    for x in r.get("picked") or []:
        c = x["confirm"]
        L.append(f"| {_name(x)} | {x['n_e']} | {f(x['m_e'])} | {c.get('n', 0)} | {f(c.get('mean'))} | {f(c.get('lo'))}〜{f(c.get('hi'))} | "
                 f"{f(c.get('placebo_mean'))} | {f(c.get('p_placebo'), 4, False)} | {c.get('verdict')} |")
    L += ["", "## 読むための表（判定しない）", "", "### 損切り8 × 利確8：平均R（入口を全部まとめた・前半／後半）", "",
          "| 損切り＼利確 | " + " | ".join(TPS[p] for p in PK) + " |", "|---|" + "---:|" * len(PK)]
    for S in SK:
        L.append(f"| {STOPS[S]} | " + " | ".join(f"{f(r['grid'][S + p][0])}／{f(r['grid'][S + p][1])}" for p in PK) + " |")
    L += ["", "### 損切りの指標ごと（利確を全部まとめた）", "", "| 損切り | 前半 | 後半 |", "|---|---:|---:|"]
    L += [f"| {STOPS[S]} | {f(r['by_s'][S][0])} | {f(r['by_s'][S][1])} |" for S in SK]
    L += ["", "### 利確の指標ごと（損切りを全部まとめた）", "", "| 利確 | 前半 | 後半 |", "|---|---:|---:|"]
    L += [f"| {TPS[p]} | {f(r['by_p'][p][0])} | {f(r['by_p'][p][1])} |" for p in PK]
    L += ["", "### 前半の上位10は、後半でどうなったか", "",
          "| 組み合わせ | 前半 件数 | 前半 平均R | 後半 件数 | 後半 平均R |", "|---|---:|---:|---:|---:|"]
    L += [f"| {_name(x)} | {x['n_e']} | {f(x['m_e'])} | {x['n_c']} | {f(x['m_c'])} |" for x in r.get("top10") or []]
    L += ["", "### いまの方式（S0×P0）・トレンドなし：オシレーターごと（前半／後半）", ""]
    L += [f"- {CL.OSCS[o]}：{f(x['m_e'])}／{f(x['m_c'])}" for o, x in r["baseline"].items()]
    L += ["", f"- 数えた合図 {r.get('entries')} 件" + (f"・値段を取れなかった銘柄 {', '.join(r['missing'])}" if r.get("missing") else ""),
          "", "---", "", "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。"]
    return "\n".join(L) + "\n"


def main():
    res = {"generated_at": dt.datetime.now(P.JST).isoformat(timespec="minutes"), "prereg_file": P.PREREG,
           "prereg_sha256": P.prereg_sha256()}
    try:
        res["result"] = run()
    except Exception as e:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        res["result"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1, default=str)
    md = render_md(res)
    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
