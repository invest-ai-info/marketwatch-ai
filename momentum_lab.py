# -*- coding: utf-8 -*-
"""J42 日本株の数か月単位のモメンタム：過去12か月の強さ（12−1）・市場と業種を除いた強さ（残差）・52週高値への近さで選び、
月1回入れ替える。2026-10-08 夜 登録・オーナー「1と2を登録して進めてください」。PILLAR_PREREG.md「J42」。

組＝決める月 m の最後の取引日に足があり、m の1日平均の売買代金1億円以上、37か月分の月末の値段がそろう銘柄（100銘柄未満の月は数えない）。
各腕の上位10％を翌月の最初の取引日の寄りで買い、その次の月の最初の取引日の寄りで売る。
1か月の値＝上位10％の平均 − 同じ組の全銘柄の平均 − 入れ替えた割合 × 往復0.1％。
判定＝98.33％（3つの腕）の幅・6か月のかたまりのブートストラップ。全期間で0より上かつ昔・最近ともプラス＝✅ など（PREREG のとおり）。

⚠️ 決まりは PILLAR_PREREG.md「J42」と下の定数に固定。データの誤りの物差しは J31 と同じ（build_jp_highs.sane_today・7暦日を超える間）。
⚠️ 出力（momentum-lab.json / .md）は集計だけ・銘柄名とコードは出さない（SYNC禁忌）。

実行: python momentum_lab.py --check   （点検だけ＝月の数・組の銘柄数・データの誤りの数。損益は数えない・何も書き出さない）
      python momentum_lab.py           （本番。Actions の momentum-lab.yml から手動で・1回だけ）
"""
import datetime as dt
import json
import sys

import numpy as np

import build_jp_highs as H
import hold_lab as HL
import jp_bars
import pillar_lab as P

OUT_JSON, OUT_MD = "momentum-lab.json", "momentum-lab.md"
TV_MIN = 1.0                  # 決める月の1日平均の売買代金（億円）
TV_BIG = 10.0                 # 読むための表：10億円以上の組
MIN_BARS = 10                 # 決める月に足が10本以上
HIST = 36                     # 36か月の月の損益（＝37か月分の月末の値段）
LOOK = 12                     # 12−1（m−12 の月末 → m−1 の月末）
RES_MONTHS = 11               # 残差の m−11〜m−1
END_WINDOW = 5                # 月末の値段＝その月の最後の5取引日のうちの最後の終値
HI_DAYS = 365                 # 52週高値＝365暦日の高値の最大
TOP_FRAC = 0.10
HAND = (10, 20)               # 手で回せる形（読むための表）
MIN_UNIVERSE = 100
MIN_IND = 5                   # 同じ業種（自分を除く）がその月に5銘柄以上
MIN_CAL = 50                  # 取引日＝50銘柄以上に足がある日
MAX_GAP_DAYS = 7              # 前の足との間がこれを超える日は値動き0でつなぐ（J31 と同じ）
COST = 0.001                  # 往復 0.1％（入れ替えた割合にかける）
COST_HI = 0.003               # 読むための表：往復 0.3％
N_ARMS = 3
ALPHA = 0.05 / N_ARMS         # 98.33％ の幅
BLOCK = 6                     # 6か月のかたまり
N_BOOT = 10000
TAX = 0.20315
FIRST, LAST = (1995, 1), (2026, 8)
ERAS = (("all", "全期間", (1995, 1), (2026, 8)),          # 置き場の日足は実質2000年から＝数えられるのは2003-01から（check 2026-10-08）
        ("old", "昔（〜2009年）", (1995, 1), (2009, 12)),
        ("new", "最近（2010年〜）", (2010, 1), (2026, 8)))
READ_ERAS = ERAS + (("e3", "2023年〜（読むだけ）", (2023, 1), (2026, 8)),)
ARMS = (("Q1", "mom", "腕1 ふつうのモメンタム（12−1）"),
        ("Q2", "res", "腕2 残差モメンタム（市場と業種を除いた強さ）"),
        ("Q3", "hi", "腕3 52週高値への近さ"))
OK, NEW_ONLY, REV, NONE = "✅ 効く", "△ 最近だけ", "✕ 逆向き", "✕ 見えない"
TOPIX_ETF = "1306"            # 生き残りのゆがみの目安（読むだけ）
EPOCH_ORD = dt.date(1970, 1, 1).toordinal()


# ════════════════════ 日付と月 ════════════════════

def month_id(days):
    """日（序数）→ 1970年1月からの月の番号"""
    d = np.asarray(days, dtype=np.int64) - EPOCH_ORD
    return d.astype("datetime64[D]").astype("datetime64[M]").astype(np.int64)


def ym_id(y, m):
    return (y - 1970) * 12 + m - 1


def id_ym(i):
    return 1970 + int(i) // 12, int(i) % 12 + 1


def calendar(counts, base):
    """日ごとの足のある銘柄の数（base からの添字）→ 取引日（MIN_CAL 銘柄以上）"""
    return np.nonzero(counts >= MIN_CAL)[0] + base


def month_table(cal):
    """取引日 → (月の番号, 最初の取引日, 最後の取引日, 最後の END_WINDOW 取引日の始まり)"""
    mid = month_id(cal)
    M, start = np.unique(mid, return_index=True)
    end = np.r_[start[1:], len(cal)]
    return M, cal[start], cal[end - 1], cal[np.maximum(end - END_WINDOW, start)]


# ════════════════════ 1銘柄 ════════════════════

def from_rows(rows):
    """[(JST の時刻, 始, 高, 安, 終, 出来高)] → (日, 始, 高, 安, 終, 出来高) の配列。出来高0の足は除く・同じ日は後のもの"""
    by = {}
    for t, o, h, lo, c, v in rows:
        if v and v > 0 and None not in (o, h, lo, c):
            by[t.date().toordinal()] = (o, h, lo, c, v)
    if not by:
        return None
    days = np.array(sorted(by), dtype=np.int32)
    vals = np.array([by[d] for d in days.tolist()], dtype=np.float32).reshape(-1, 5)
    return days, vals


def clean_index(day, o, h, l, c):
    """→ (終値の指数 P, 始値の指数 Q, 高値の指数 Hx, 値動き0でつないだ日の数)。
    誤りの日（sane_today と同じ物差し＋始値が高値と安値の間）・前の足との間が7暦日を超える日は値動き0でつなぐ"""
    n = len(day)
    ok_bar = (c > 0) & (l > 0) & (o > 0) & (h >= c * 0.999) & (l <= c * 1.001) & (o >= l * (1 - 1e-9)) & (o <= h * (1 + 1e-9))
    good = np.zeros(n, bool)
    if n > 1:
        prev = c[:-1]
        good[1:] = (ok_bar[1:] & (prev > 0) & (h[1:] <= prev * H.MAX_JUMP) & (l[1:] >= prev / H.MAX_JUMP)
                    & (np.diff(day) <= MAX_GAP_DAYS))
    rc = np.ones(n)
    go = np.ones(n)
    if n > 1:
        safe = np.where(c[:-1] > 0, c[:-1], 1.0)
        rc[1:] = np.where(good[1:], c[1:] / safe, 1.0)
        go[1:] = np.where(good[1:], o[1:] / safe, 1.0)
    Pi = np.cumprod(rc)
    Q = np.empty(n)
    Q[0] = o[0] / c[0] if ok_bar[0] else 1.0
    Q[1:] = Pi[:-1] * go[1:]
    Hx = Pi * np.where(ok_bar, h / np.where(c > 0, c, 1.0), 1.0)
    return Pi, Q, Hx, int(n - 1 - good[1:].sum()) if n > 1 else 0


def stock_months(day, vals, M, first, last, tail):
    """1銘柄 → 月ごとの値（長さ len(M)・無ければ NaN）と、値動き0でつないだ日の数"""
    day = np.asarray(day, np.int64)
    v = np.asarray(vals, float)
    o, h, l, c, vol = v[:, 0], v[:, 1], v[:, 2], v[:, 3], v[:, 4]
    Pi, Q, Hx, bad = clean_index(day, o, h, l, c)
    nM = len(M)
    out = {k: np.full(nM, np.nan) for k in ("p_end", "p_last", "q_entry", "q_exit", "tv", "nb", "hi")}
    out["has_last"] = np.zeros(nM, bool)
    mid = month_id(day)
    um, st = np.unique(mid, return_index=True)
    en = np.r_[st[1:], len(day)]
    pos = np.searchsorted(M, um)
    for m, a, b, j in zip(um, st, en, pos):
        if j >= nM or M[j] != m:
            continue
        k = b - 1
        out["nb"][j] = b - a
        out["tv"][j] = float(np.mean(c[a:b] * vol[a:b])) / 1e8
        out["p_last"][j] = Pi[k]
        if day[k] >= tail[j]:
            out["p_end"][j] = Pi[k]
        out["has_last"][j] = day[k] == last[j]
        out["q_exit"][j] = Q[a]
        if day[a] == first[j]:
            out["q_entry"][j] = Q[a]
        if day[0] <= day[k] - HI_DAYS:
            j0 = int(np.searchsorted(day, day[k] - HI_DAYS + 1))
            out["hi"][j] = Pi[k] / Hx[j0:k + 1].max()
    return out, bad


def panel(series, sectors, M, first, last, tail):
    """{code: (日, 値)} → 銘柄 × 月の表（銘柄の並びはコード順。コードは表に残さない）"""
    codes = sorted(series)
    nS, nM = len(codes), len(M)
    T = {k: np.full((nS, nM), np.nan) for k in ("p_end", "p_last", "q_entry", "q_exit", "tv", "nb", "hi")}
    T["has_last"] = np.zeros((nS, nM), bool)
    bad = 0
    for i, code in enumerate(codes):
        d, v = series[code]
        o, b = stock_months(d, v, M, first, last, tail)
        bad += b
        for k in T:
            T[k][i] = o[k]
    names = sorted({sectors.get(c) or "" for c in codes} - {""})
    T["sector"] = np.array([names.index(sectors[c]) if sectors.get(c) else -1 for c in codes])
    T["bad_days"] = bad
    T["M"] = M
    return T


# ════════════════════ 信号 ════════════════════

def month_returns(T):
    R = np.full(T["p_end"].shape, np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        R[:, 1:] = T["p_end"][:, 1:] / T["p_end"][:, :-1] - 1
    return R


def industry_loo(R, sector):
    """自分を除く同じ業種の平均（その月に MIN_IND 銘柄以上・業種が空なら NaN）"""
    out = np.full(R.shape, np.nan)
    fin = np.isfinite(R)
    Rz = np.where(fin, R, 0.0)
    for s in np.unique(sector[sector >= 0]):
        m = sector == s
        tot, cnt = Rz[m].sum(0), fin[m].sum(0)
        others = cnt[None, :] - fin[m]
        val = (tot[None, :] - Rz[m]) / np.where(others > 0, others, 1)
        out[m] = np.where(others >= MIN_IND, val, np.nan)
    return out


def residual_scores(Y, mkt, IND):
    """Y（n×36 の月の損益）を切片＋全銘柄の平均（＋自分を除く業種の平均）に当てはめた残りの、m−11〜m−1 の合計 ÷ 同じ11か月の標準偏差。
    業種の平均が36か月のどこかで使えない銘柄は全銘柄の平均だけ"""
    n, Tn = Y.shape
    out = np.full(n, np.nan)
    use_ind = np.isfinite(IND).all(1) if IND is not None else np.zeros(n, bool)
    for flag in (True, False):
        sel = use_ind if flag else ~use_ind
        if not sel.any():
            continue
        cols = [np.ones((sel.sum(), Tn)), np.broadcast_to(mkt, (sel.sum(), Tn))]
        if flag:
            cols.append(IND[sel])
        X = np.stack(cols, axis=2)
        y = Y[sel]
        beta = np.einsum("npt,nt->np", np.linalg.pinv(X), y)
        e = y - np.einsum("ntp,np->nt", X, beta)
        f = e[:, Tn - 1 - RES_MONTHS:Tn - 1]
        sd = f.std(1, ddof=1)
        out[np.nonzero(sel)[0]] = np.where(sd > 1e-12, f.sum(1) / np.where(sd > 1e-12, sd, 1.0), np.nan)
    return out


def rank_top(sig, idx, k, largest=True):
    """組の添字 idx の中で sig の大きい順（largest=False なら小さい順）に k 銘柄。並びが同じならコード順"""
    s = sig[idx] if largest else -sig[idx]
    order = np.lexsort((idx, -s))
    return idx[order[:k]]


# ════════════════════ 月ごとの記録 ════════════════════

def decision_months(M, first=FIRST, last=LAST):
    """決める月の添字 j（m−36 と m+2 が表にあるもの）"""
    lo, hi = ym_id(*first), ym_id(*last)
    return [j for j in range(HIST, len(M) - 2) if lo <= M[j] <= hi and M[j] - M[j - HIST] == HIST and M[j + 2] - M[j] == 2]


def universe(T, R, j):
    """決める月 j の組（添字）と持った1か月の損益（全銘柄ぶん・組の外は NaN）"""
    win = R[:, j - HIST + 1:j + 1]
    exitv = np.where(np.isfinite(T["q_exit"][:, j + 2]), T["q_exit"][:, j + 2], T["p_last"][:, j + 1])
    hold = exitv / T["q_entry"][:, j + 1] - 1
    m = (T["has_last"][:, j] & (T["nb"][:, j] >= MIN_BARS) & (T["tv"][:, j] >= TV_MIN) & np.isfinite(win).all(1)
         & np.isfinite(T["hi"][:, j]) & np.isfinite(hold))
    return m, hold


def signals(T, R, mkt, IND, j, m):
    n = len(m)
    mom = T["p_end"][:, j - 1] / T["p_end"][:, j - LOOK] - 1
    res = np.full(n, np.nan)
    idx = np.nonzero(m)[0]
    if len(idx):
        res[idx] = residual_scores(R[idx, j - HIST + 1:j + 1], mkt[j - HIST + 1:j + 1], IND[idx, j - HIST + 1:j + 1])
    return {"mom": mom, "res": res, "hi": T["hi"][:, j]}


def _replaced(prev, cur, cont):
    if not cont or prev is None or not len(cur):
        return 1.0
    return float(len(set(cur.tolist()) - set(prev.tolist())) / len(cur))


def records(T, first=FIRST, last=LAST):
    """→ 月ごとの記録（銘柄は数だけ・コードは残さない）"""
    with np.errstate(invalid="ignore", divide="ignore"):
        return _records(T, first, last)


def _records(T, first, last):
    M = T["M"]
    R = month_returns(T)
    fin = np.isfinite(R)
    mkt = np.where(fin.any(0), np.nansum(R, 0) / np.maximum(fin.sum(0), 1), np.nan)
    IND = industry_loo(R, T["sector"])
    out, prev, prev_j = [], {}, None
    for j in decision_months(M, first, last):
        m, hold = universe(T, R, j)
        sig = signals(T, R, mkt, IND, j, m)
        m = m & np.isfinite(sig["res"])
        idx = np.nonzero(m)[0]
        if len(idx) < MIN_UNIVERSE:
            prev_j = None
            continue
        cont = prev_j is not None and M[j] - M[prev_j] == 1
        k = int(round(TOP_FRAC * len(idx)))
        uni = float(hold[idx].mean())
        big = idx[T["tv"][idx, j] >= TV_BIG]
        rec = {"ym": "%04d-%02d" % id_ym(M[j]), "n_u": int(len(idx)), "n_top": k, "uni": uni,
               "n_big": int(len(big)), "big_uni": float(hold[big].mean()) if len(big) >= MIN_UNIVERSE else None, "arms": {}}
        tops = {}
        for q, key, _ in ARMS:
            top = rank_top(sig[key], idx, k)
            tops[q] = top
            a = {"top": float(hold[top].mean()), "rep": _replaced(prev.get(q), top, cont),
                 "bot": float(hold[rank_top(sig[key], idx, k, largest=False)].mean())}
            for h in HAND:
                th = rank_top(sig[key], idx, h)
                a[f"top{h}"] = float(hold[th].mean())
                a[f"rep{h}"] = _replaced(prev.get(f"{q}_{h}"), th, cont)
                prev[f"{q}_{h}"] = th
            if rec["big_uni"] is not None:
                tb = rank_top(sig[key], big, int(round(TOP_FRAC * len(big))))
                a["big"] = float(hold[tb].mean())
                a["rep_big"] = _replaced(prev.get(f"{q}_big"), tb, cont and prev.get(f"{q}_big") is not None)
                prev[f"{q}_big"] = tb
            else:
                prev[f"{q}_big"] = None
            prev[q] = top
            rec["arms"][q] = a
        r1 = R[:, j]
        rec["rev_top"] = float(hold[rank_top(r1, idx, k)].mean())
        rec["rev_bot"] = float(hold[rank_top(r1, idx, k, largest=False)].mean())
        rec["overlap"] = {f"{a}-{b}": float(len(set(tops[a].tolist()) & set(tops[b].tolist())) / k)
                          for a, b in (("Q1", "Q2"), ("Q1", "Q3"), ("Q2", "Q3"))}
        out.append(rec)
        prev_j = j
    return out, mkt


# ════════════════════ 判定 ════════════════════

def diff(rec, q, cost=COST, kind=""):
    a = rec["arms"][q]
    if kind == "big":
        return a["big"] - rec["big_uni"] - a["rep_big"] * cost if "big" in a else None
    if kind:
        return a[f"top{kind}"] - rec["uni"] - a[f"rep{kind}"] * cost
    return a["top"] - rec["uni"] - a["rep"] * cost


def band(x, alpha=ALPHA, block=BLOCK, n_boot=N_BOOT, seed=P.SEED):
    """平均と、6か月のかたまりで引き直したブートストラップの幅（両側）"""
    x = np.asarray([v for v in x if v is not None], float)
    n = len(x)
    if n < 2 * block:
        return {"n": n, "mean": float(x.mean()) if n else None, "lo": None, "hi": None}
    rng = np.random.default_rng(seed)
    nb = -(-n // block)
    sims = []
    for _ in range(n_boot // 1000):
        st = rng.integers(0, n, (1000, nb))
        ix = ((st[:, :, None] + np.arange(block)) % n).reshape(1000, -1)[:, :n]
        sims.append(x[ix].mean(1))
    lo, hi = np.percentile(np.concatenate(sims), [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return {"n": n, "mean": float(x.mean()), "lo": float(lo), "hi": float(hi)}


def plus(q):
    return q.get("lo") is not None and q["lo"] > 0


def minus(q):
    return q.get("hi") is not None and q["hi"] < 0


def verdict(j):
    a, o, n = j["all"], j["old"], j["new"]
    if plus(a) and (o["mean"] or 0) > 0 and (n["mean"] or 0) > 0:
        return OK
    if plus(n):
        return NEW_ONLY
    if minus(a):
        return REV
    return NONE


def in_era(rec, span):
    y, m = map(int, rec["ym"].split("-"))
    return ym_id(*span[0]) <= ym_id(y, m) <= ym_id(*span[1])


def max_drawdown(rets):
    if not rets:
        return None
    v = np.cumprod(1 + np.asarray(rets, float))
    return float((v / np.maximum.accumulate(v) - 1).min())


def cagr(rets):
    """月の損益 → 年率（税の前）"""
    if not rets:
        return None
    return float(np.prod(1 + np.asarray(rets, float)) ** (12 / len(rets)) - 1)


def after_tax_cagr(rets, years):
    """毎年の利益に税（損は3年繰り越し・hold_lab.year_tax）→ 年率"""
    if not rets:
        return None
    V, carry = 1.0, []
    for y in sorted(set(years)):
        start = V
        for r, yy in zip(rets, years):
            if yy == y:
                V *= 1 + r
        tax, carry = HL.year_tax(V - start, carry, y, "index", TAX)
        V -= tax
    return float(V ** (12 / len(rets)) - 1)


def end_tax_cagr(rets):
    """最後に1回だけ税 → 年率"""
    if not rets:
        return None
    V = float(np.prod(1 + np.asarray(rets, float)))
    V -= max(V - 1, 0) * TAX
    return float(V ** (12 / len(rets)) - 1)


def _mean(x):
    x = [v for v in x if v is not None]
    return float(np.mean(x)) if x else None


def analyze(T, first=FIRST, last=LAST):
    recs, mkt = records(T, first, last)
    res = {"months": len(recs), "first": recs[0]["ym"] if recs else None, "last": recs[-1]["ym"] if recs else None,
           "judge": {}, "summary": {}, "read": {}, "series": recs, "spans": {}}
    for e, _, a, b in READ_ERAS:
        ys = [r["ym"] for r in recs if in_era(r, (a, b))]
        res["spans"][e] = f"{ys[0]}〜{ys[-1]}・{len(ys)}か月" if ys else "—"
    for q, key, name in ARMS:
        res["judge"][q] = {e: band([diff(r, q) for r in recs if in_era(r, (a, b))]) for e, _, a, b in ERAS}
        res["summary"][q] = verdict(res["judge"][q])
        rd = {}
        for e, _, a, b in READ_ERAS:
            rs = [r for r in recs if in_era(r, (a, b))]
            d = [diff(r, q) for r in rs]
            net = [r["arms"][q]["top"] - r["arms"][q]["rep"] * COST for r in rs]
            rd[e] = {"months": len(rs), "top": _mean([r["arms"][q]["top"] for r in rs]), "uni": _mean([r["uni"] for r in rs]),
                     "diff": _mean(d), "diff_hi_cost": _mean([diff(r, q, COST_HI) for r in rs]),
                     "win_months": _mean([x > 0 for x in d]), "worst": min(d) if d else None,
                     "rep": _mean([r["arms"][q]["rep"] for r in rs]),
                     "mdd_top": max_drawdown(net), "mdd_uni": max_drawdown([r["uni"] for r in rs]),
                     "top10": _mean([diff(r, q, kind=10) for r in rs]), "top20": _mean([diff(r, q, kind=20) for r in rs]),
                     "big": _mean([diff(r, q, kind="big") for r in rs]), "big_months": sum(r["big_uni"] is not None for r in rs),
                     "bot": _mean([r["arms"][q]["bot"] - r["uni"] for r in rs])}
            if e == "new":
                yrs = [int(r["ym"][:4]) + (1 if r["ym"].endswith("-12") else 0) for r in rs]   # 持った月の年
                rd[e]["tax"] = {"top_pre": cagr(net), "top_after": after_tax_cagr(net, yrs),
                                "top10_after": after_tax_cagr([r["arms"][q]["top10"] - r["arms"][q]["rep10"] * COST for r in rs], yrs),
                                "uni_pre": cagr([r["uni"] for r in rs]), "uni_after": end_tax_cagr([r["uni"] for r in rs])}
        res["read"][q] = rd
    res["reversal"] = {e: {"top": _mean([r["rev_top"] - r["uni"] for r in recs if in_era(r, (a, b))]),
                           "bot": _mean([r["rev_bot"] - r["uni"] for r in recs if in_era(r, (a, b))])} for e, _, a, b in READ_ERAS}
    res["overlap"] = {k: _mean([r["overlap"][k] for r in recs]) for k in ("Q1-Q2", "Q1-Q3", "Q2-Q3")}
    res["n_u_by_year"] = {}
    for r in recs:
        res["n_u_by_year"].setdefault(r["ym"][:4], []).append(r["n_u"])
    res["n_u_by_year"] = {y: int(np.median(v)) for y, v in res["n_u_by_year"].items()}
    res["mkt_by_year"] = year_returns(T["M"], mkt)
    return res


def year_returns(M, mret):
    """月の損益（月の番号 M に並ぶ）→ {年: その年の12か月をかけ合わせた損益}（12か月そろう年だけ）"""
    by = {}
    for i, r in zip(M, mret):
        if np.isfinite(r):
            by.setdefault(id_ym(i)[0], []).append(r)
    return {str(y): float(np.prod(1 + np.asarray(v)) - 1) for y, v in by.items() if len(v) == 12}


def survivorship_gauge(res, etf_year):
    """年ごとの「置き場の全銘柄の単純平均 − TOPIX 連動 ETF」（2002年〜・読むだけ）"""
    out = {}
    for y, r in sorted(res["mkt_by_year"].items()):
        if int(y) >= 2002 and y in etf_year:
            out[y] = r - etf_year[y]
    return out


def verdicts_of(res, today):
    out = {}
    for q, _, name in ARMS:
        if res["summary"][q] in (REV, NONE):
            a = res["judge"][q]["all"]
            out[q] = {"status": "stop", "decided_on": today, "n": a["n"], "mean": a["mean"], "lo": a["lo"], "hi": a["hi"],
                      "reason": "過去のデータで1回だけ数えて" + ("強い株のほうがその後弱い（逆向き）" if res["summary"][q] == REV else "強い株を買い続ける得は見えない")
                                + f"（上位10％ − 同じ組の全銘柄の平均・費用後・{res.get('first')}〜{res.get('last')} の数字）"}
    return out


def check_summary(T, n_codes, missing, store, first=FIRST, last=LAST):
    """点検だけ＝時代ごとの月の数・組の銘柄数・データの誤りの数（損益は数えない）"""
    with np.errstate(invalid="ignore", divide="ignore"):
        return _check_summary(T, n_codes, missing, store, first, last)


def _check_summary(T, n_codes, missing, store, first, last):
    M = T["M"]
    R = month_returns(T)
    out = {"n_codes": n_codes, "missing_daily": missing, "store": store, "bad_days_zeroed": int(T["bad_days"]),
           "calendar": ["%04d-%02d" % id_ym(M[0]), "%04d-%02d" % id_ym(M[-1])] if len(M) else None, "eras": {}}
    sizes = {}
    for j in decision_months(M, first, last):
        m, _ = universe(T, R, j)
        sizes["%04d-%02d" % id_ym(M[j])] = (int(m.sum()), int((m & (T["tv"][:, j] >= TV_BIG)).sum()))
    for e, _, a, b in READ_ERAS:
        s = [v for k, v in sizes.items() if ym_id(*a) <= ym_id(*map(int, k.split("-"))) <= ym_id(*b)]
        n = [x for x, _ in s]
        out["eras"][e] = {"months": len(s), "months_counted": sum(x >= MIN_UNIVERSE for x in n),
                          "universe_min": min(n) if n else None, "universe_median": float(np.median(n)) if n else None,
                          "universe_max": max(n) if n else None,
                          "big_months": sum(y >= MIN_UNIVERSE for _, y in s)}
    return out


# ════════════════════ 読み込み ════════════════════

def load(codes, fetch):
    """→ ({code: (日, 値)}, 日足の取れなかった銘柄の数, 取引日の表)"""
    series, missing = {}, 0
    base = dt.date(1989, 1, 1).toordinal()
    counts = np.zeros(dt.date.today().toordinal() - base + 400, np.int64)
    for i, code in enumerate(codes):
        rows = fetch(code, "1d", jp_bars.FULL_DAILY)
        a = from_rows(rows) if rows else None
        if a is None:
            missing += 1
            continue
        series[code] = a
        d = a[0].astype(np.int64) - base
        d = d[(d >= 0) & (d < len(counts))]
        counts[d] += 1
        if (i + 1) % 500 == 0:
            print(f"  ...{i + 1}/{len(codes)}", flush=True)
    cal = calendar(counts, base)
    return series, missing, cal


def etf_years(fetch, M, first, last, tail):
    """TOPIX 連動 ETF（1306）の年ごとの損益（読むだけ・取れなければ {}）"""
    try:
        rows = fetch(TOPIX_ETF, "1d", jp_bars.FULL_DAILY)
        a = from_rows(rows) if rows else None
        if a is None:
            return {}
        o, _ = stock_months(a[0], a[1], M, first, last, tail)
        r = np.full(len(M), np.nan)
        r[1:] = o["p_end"][1:] / o["p_end"][:-1] - 1
        return year_returns(M, r)
    except Exception as e:  # noqa: BLE001
        print(f"  ⚠️ 1306 を読めず：{type(e).__name__}", file=sys.stderr)
        return {}


# ════════════════════ 書く ════════════════════

def _p(x, d=2):
    return "—" if x is None else f"{x * 100:+.{d}f}％"


def _band(q):
    return "—" if q.get("lo") is None else f"{_p(q['lo'])}〜{_p(q['hi'])}"


def render_md(res):
    L = ["# J42 日本株の数か月単位のモメンタム（12−1・残差・52週高値）", "",
         f"更新: {res.get('generated_at', '')}（事前登録＝`PILLAR_PREREG.md`「J42」・指紋 `{(res.get('prereg_sha256') or '')[:12]}`）", ""]
    r = res.get("result") or {}
    if "error" in r:
        return "\n".join(L + [f"⚠️ 計算できず：{r['error']}", "", "※ 研究の記録です。投資助言ではありません。"]) + "\n"
    L += [f"組＝決める月の1日平均の売買代金1億円以上・37か月分の月末の値段がそろう銘柄（{r['first']}〜{r['last']}・{r['months']}か月）。"
          "各腕の上位10％を翌月の最初の取引日の寄りで買い、その次の月の最初の取引日の寄りで売る。"
          f"1か月の値＝上位10％の平均 − 同じ組の全銘柄の平均 − 入れ替えた割合 × 往復{COST * 100:.1f}％。"
          f"幅は {100 * (1 - ALPHA):.2f}％（3つの腕・6か月のかたまりで引き直す 10,000回）。", "", "## まとめ（判定）", "",
          f"時代＝全期間 {r['spans']['all']}／昔 {r['spans']['old']}／最近 {r['spans']['new']}（置き場の日足は実質2000年から＝37か月の履歴がそろうのは2003年から）。", "",
          "| 腕 | 判定 | 全期間の差（月あたり） | 幅 | 昔 | 最近 | 最近の幅 |", "|---|---|---:|---|---:|---:|---|"]
    for q, _, name in ARMS:
        j = r["judge"][q]
        L.append(f"| {name} | **{r['summary'][q]}** | {_p(j['all']['mean'])} | {_band(j['all'])} | {_p(j['old']['mean'])} | "
                 f"{_p(j['new']['mean'])} | {_band(j['new'])} |")
    L += ["", "## 読むための表（判定しない）", ""]
    for q, _, name in ARMS:
        L += [f"### {name}", "", "| 時代 | 月 | 上位10％ | 全銘柄 | 差（0.1％） | 差（0.3％） | 差がプラスの月 | 最悪の月 | 入れ替え | 最大の下落（上位10％／全銘柄） | 上位10銘柄の差 | 上位20銘柄の差 | 10億円以上の組の差 | 下位10％ − 全銘柄 |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|"]
        for e, ename, _, _ in READ_ERAS:
            x = r["read"][q][e]
            wm = "—" if x["win_months"] is None else f"{x['win_months'] * 100:.0f}％"
            rep = "—" if x["rep"] is None else f"{x['rep'] * 100:.0f}％"
            L.append(f"| {ename}（{r['spans'][e].split('・')[0]}） | {x['months']} | {_p(x['top'])} | {_p(x['uni'])} | {_p(x['diff'])} | {_p(x['diff_hi_cost'])} | {wm} | "
                     f"{_p(x['worst'])} | {rep} | {_p(x['mdd_top'], 0)}／{_p(x['mdd_uni'], 0)} | {_p(x['top10'])} | {_p(x['top20'])} | "
                     f"{_p(x['big'])}（{x['big_months']}か月） | {_p(x['bot'])} |")
        t = r["read"][q]["new"].get("tax") or {}
        L += ["", f"税を引いたあとの目安（最近・年率）：上位10％ 税の前 {_p(t.get('top_pre'))} → 毎年の利益に税 {_p(t.get('top_after'))}／"
              f"上位10銘柄 {_p(t.get('top10_after'))}／全銘柄の平均 税の前 {_p(t.get('uni_pre'))} → 最後に1回だけ税 {_p(t.get('uni_after'))}", ""]
    L += ["### 直近1か月の損益で選んだ株（日本の1か月の戻り）", "", "| 時代 | 上位10％ − 全銘柄 | 下位10％ − 全銘柄 |", "|---|---:|---:|"]
    for e, ename, _, _ in READ_ERAS:
        x = r["reversal"][e]
        L.append(f"| {ename} | {_p(x['top'])} | {_p(x['bot'])} |")
    ov = r["overlap"]
    L += ["", "3つの腕の上位10％の重なり（月の平均）：" + "・".join(f"腕{k[1]}と腕{k[4]} {'—' if ov[k] is None else format(ov[k] * 100, '.0f') + '％'}"
                                                   for k in ("Q1-Q2", "Q1-Q3", "Q2-Q3")), "",
          "### 生き残りのゆがみの目安（年ごと・置き場の全銘柄の単純平均 − TOPIX 連動 ETF 1306・大きい株と小さい株の差も混ざる）と組の銘柄数", ""]
    g = r.get("survivorship") or {}
    L.append("、".join(f"{y} {_p(v, 1)}" for y, v in g.items()) or "（1306 を読めず）")
    L += ["", "組の銘柄数（年ごとの中央値）：" + "、".join(f"{y} {n}" for y, n in r["n_u_by_year"].items()), "",
          "## 注意", "",
          "- **いま上場している銘柄だけ**（倒産で消えた株がいない＝モメンタムを小さく見せる向き／TOB・MBO で消えた株がいない＝大きく見せる向き。差し引きは分からない）。下位10％の側は読むだけ",
          "- 配当は入っていない・業種はいまの分類・残差は Fama-French の代わりに業種・上場から3年未満の株は入らない・税は判定に入れない（目安は毎年すべての利益が確定するとした近似）",
          "- 寄り成行がその日の始値で約定する前提（ストップ高で寄らない株は実際には買えない）。月1回なので回数が少ない", "", "---", "",
          "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。"]
    return "\n".join(L) + "\n"


def rounded(x, nd=6):
    """記録を書くときに小数を丸める（JSON を軽くする）"""
    if isinstance(x, float):
        return round(x, nd)
    if isinstance(x, dict):
        return {k: rounded(v, nd) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [rounded(v, nd) for v in x]
    return x


def main(argv):
    res = {"generated_at": dt.datetime.now(P.JST).isoformat(timespec="minutes"), "prereg_file": P.PREREG,
           "prereg_sha256": P.prereg_sha256()}
    try:
        stocks, list_date = jp_bars.load_universe()
        codes = sorted(stocks)
        fetch = jp_bars.fetcher()
        series, missing, cal = load(codes, fetch)
        store = jp_bars.info()
        res["price_store"] = store
        M, first, last, tail = month_table(cal)
        T = panel(series, {c: (stocks[c] or {}).get("sector") or "" for c in series}, M, first, last, tail)
        if "--check" in argv:
            print(json.dumps(check_summary(T, len(codes), missing, store), ensure_ascii=False, indent=1))
            return 0
        if not store or store.get("daily_range") != jp_bars.FULL_DAILY:
            raise RuntimeError("値段の置き場の日足が全期間版ではない（先に jp-bars-cache を回す）")
        if missing > 0.05 * len(codes):
            raise RuntimeError("日足を取れなかった銘柄が5％超。偏った組で数えない（取り直す）")
        out = analyze(T)
        out["survivorship"] = survivorship_gauge(out, etf_years(fetch, M, first, last, tail))
        res["result"] = dict(out, n_codes=len(codes), list_date=list_date, n_missing=missing, bad_days_zeroed=int(T["bad_days"]))
        res.update(kind="backtest",
                   titles={q: f"日本株の数か月単位のモメンタム・{name}（売買代金1億円以上の上位10％を月1回入れ替え・{out['first']}〜{out['last']}・1回だけ数えた）"
                           for q, _, name in ARMS},
                   verdicts=verdicts_of(out, dt.datetime.now(P.JST).date().isoformat()))
    except Exception as e:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        if "--check" in argv:
            return 1
        res["result"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(rounded(res), fh, ensure_ascii=False, indent=1, default=str)
    md = render_md(res)
    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
