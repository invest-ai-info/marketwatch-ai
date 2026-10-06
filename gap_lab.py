# -*- coding: utf-8 -*-
"""J13 窓を開けて寄った株は、寄りのあとに戻されるか（高値更新に限らず、すべての銘柄のすべての朝）（2026-10-06 夜 登録・オーナー「続けてください」）。

東証の全上場（約3,700銘柄）のすべての朝を、窓（寄り ÷ 前の取引日の終値 − 1）の大きさで分け、寄り→10:00（1時間足・判定の主）と
寄り→9:30（5分足・同じ向きか）を J10 と同じ値の取り方で数える。高く寄った株・安く寄った株を「ふつう（窓 ±1％ 未満）」と比べる。
G5 は「高値更新の翌朝ならではか」＝（高値更新の朝の差）−（それ以外の朝の差）。

⚠️ 決まりは PILLAR_PREREG.md「J13」と下の定数に固定。結果を見てから動かさない。値の取り方は highs_trap_lab.py をそのまま使う。
⚠️ 行が約250万になるので、1行ずつの辞書ではなく numpy の配列で持つ（日と銘柄は番号）。出力は集計だけ・銘柄名とコードは出さない。
⚠️ 出力（gap-lab.json / .md）は GitHub 側で生成＝手元から送らない（SYNC禁忌）。

実行: python gap_lab.py          （本番。Actions の gap-lab.yml から手動で・1回だけ）
      python gap_lab.py --diag   （件数とデータの形だけ。値動きは出さない・何も書き出さない）
"""
import datetime as dt
import json
import sys
import time

import numpy as np

import build_jp_highs as H
import highs_trap_lab as T
import highs_trap_small as S
import pillar_lab as P
import yori_lab as Y

OUT_JSON, OUT_MD = "gap-lab.json", "gap-lab.md"
UP1, UP3, DN1, DN3 = 0.01, 0.03, -0.01, -0.03
MAX_GAP_DAYS = 7              # 前の取引日との間がこれを超える日（売買停止などの穴）は数えない
N_Q = 5                       # 判定の数（G1〜G5）
ALPHA = 0.05 / N_Q            # 99％ の幅
CHUNK = 250
GAP_BANDS = (("−5％未満", -1e9, -0.05), ("−5〜−3％", -0.05, -0.03), ("−3〜−1％", -0.03, -0.01), ("−1〜+1％", -0.01, 0.01),
             ("+1〜+3％", 0.01, 0.03), ("+3〜+5％", 0.03, 0.05), ("+5％以上", 0.05, 1e9))
GROUP_NAMES = {"base": "ふつう", "up1": "高く寄った", "up3": "大きく高く寄った", "dn1": "安く寄った", "dn3": "大きく安く寄った"}
COLS = ("day", "code", "gap", "r915", "r930", "r1000", "rclose", "hi", "turnover")
C = {k: i for i, k in enumerate(COLS)}
PAIRS = (("g1", "G1 高く寄った（窓 +1％ 以上）− ふつう", "up", "up1"),
         ("g2", "G2 大きく高く寄った（窓 +3％ 以上）− ふつう", "up", "up3"),
         ("g3", "G3 安く寄った（窓 −1％ 以下）− ふつう", "down", "dn1"),
         ("g4", "G4 大きく安く寄った（窓 −3％ 以下）− ふつう", "down", "dn3"))
WORDS = {"up": ("高く寄ると戻されやすい（寄りで追わない方がいい兆し）", "高く寄ると続きやすい（兆し）"),
         "down": ("安く寄ると続けて下げやすい（兆し）", "安く寄ると戻りやすい（寄りで拾う側の兆し）")}
DID_WORDS = ("高値更新の翌朝のほうが戻され方が大きい（J10F の目印は高値更新ならでは）", "高値更新の翌朝のほうが戻され方が小さい",
             "見えない（高値更新に限った話とは言えない）")


# ════════════════════ 行を作る ════════════════════

def _nan(x):
    return np.nan if x is None else x


def stock_rows(ci, daily, m5, h1, covered, end_day=T.END_DAY, drops=None):
    """1銘柄の朝ごとの行（COLS の順の配列）。daily＝[(日付, 始, 高, 安, 終, 出来高)]（日付順）。
    hi＝1 高値更新の翌朝（期間の覆いを確かめられた）／0 高値更新でない朝／−1 G5 に入れない朝"""
    bars = [(d, h, lo, c, v) for d, o, h, lo, c, v in daily]
    flags = T.ytd_flags(bars)
    out = []
    for k in range(len(daily) - 1):
        d0, d1 = daily[k], daily[k + 1]
        day = d1[0]
        if day > end_day:
            break
        op, high, low, close, pc = d1[1], d1[2], d1[3], d1[4], d0[4]
        if not op or op <= 0 or not pc or pc <= 0:
            continue
        if (dt.date.fromisoformat(day) - dt.date.fromisoformat(d0[0])).days > MAX_GAP_DAYS:
            continue
        if not H.sane_today(bars[k:k + 2]) or not (low * (1 - 1e-9) <= op <= high * (1 + 1e-9)):
            continue
        o = T.outcomes(op, close, m5.get(day), h1.get(day), drops)
        if o is None:
            continue
        if H.window_start(d0[0])[0] < T.MIN_WINDOW_START:
            hi = -1
        elif flags[k]:
            hi = 1 if covered(d0[0]) else -1
        else:
            hi = 0
        out.append((dt.date.fromisoformat(day).toordinal(), ci, op / pc - 1, _nan(o["r915"]), _nan(o["r930"]),
                    _nan(o["r1000"]), _nan(o["rclose"]), hi, pc * d0[5] / 1e8))
    return np.array(out, float).reshape(-1, len(COLS))


# ════════════════════ 組と幅 ════════════════════

def masks(A):
    g = A[:, C["gap"]]
    return {"base": (g > DN1) & (g < UP1), "up1": g >= UP1, "up3": g >= UP3, "dn1": g <= DN1, "dn3": g <= DN3}


def boot(val, grp, n_groups, clus, stat, alpha=ALPHA, n_boot=T.N_BOOT, seed=P.SEED):
    """まとまり（clus）ごとに引き直した stat(各組の平均) の (点, 下, 上)。grp＝組の番号（−1 は入れない）。まとまりが5未満なら幅は出さない"""
    m = (grp >= 0) & np.isfinite(val)
    v, g, c = val[m], grp[m].astype(int), clus[m]
    _, ci = np.unique(c, return_inverse=True)
    K = int(ci.max()) + 1 if len(ci) else 0
    Sm = np.zeros((n_groups, K))
    Nm = np.zeros((n_groups, K))
    for k in range(n_groups):
        mk = g == k
        Sm[k] = np.bincount(ci[mk], weights=v[mk], minlength=K)
        Nm[k] = np.bincount(ci[mk], minlength=K)
    with np.errstate(invalid="ignore", divide="ignore"):
        point = float(stat(Sm.sum(1) / Nm.sum(1)))
    if not np.isfinite(point):
        return None, None, None
    if K < 5:
        return point, None, None
    rng = np.random.default_rng(seed)
    sims = []
    for start in range(0, n_boot, CHUNK):
        d = rng.integers(0, K, size=(min(CHUNK, n_boot - start), K))
        with np.errstate(invalid="ignore", divide="ignore"):
            sims.append(stat(Sm[:, d].sum(2) / Nm[:, d].sum(2)))
    s = np.concatenate(sims)
    s = s[np.isfinite(s)]
    lo, hi = np.percentile(s, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return point, float(lo), float(hi)


def _diff2(mu):
    return mu[0] - mu[1]


def _did(mu):
    return (mu[0] - mu[1]) - (mu[2] - mu[3])


def safe(A, val_col, grp, n_groups, stat, alpha=ALPHA):
    """日で引き直した幅と銘柄で引き直した幅の、広いほう（安全側）"""
    val = A[:, C[val_col]]
    ok = np.isfinite(val)
    ns = [int(((grp == k) & ok).sum()) for k in range(n_groups)]
    out = {"ns": ns, "diff": None, "lo": None, "hi": None}
    if min(ns) == 0:
        return out
    pt, lo_d, hi_d = boot(val, grp, n_groups, A[:, C["day"]], stat, alpha)
    _, lo_c, hi_c = boot(val, grp, n_groups, A[:, C["code"]], stat, alpha)
    out.update(diff=pt, by_day=[lo_d, hi_d], by_stock=[lo_c, hi_c])
    if None not in (lo_d, lo_c, hi_d, hi_c):
        out.update(lo=min(lo_d, lo_c), hi=max(hi_d, hi_c))
    return out


def plain(A, val_col, grp, n_groups, stat):
    """幅なしの点だけ（前半・後半・5分足の確かめ用）"""
    val = A[:, C[val_col]]
    ok = np.isfinite(val)
    ns = [int(((grp == k) & ok).sum()) for k in range(n_groups)]
    if min(ns) == 0:
        return {"ns": ns, "diff": None}
    mu = np.array([val[(grp == k) & ok].mean() for k in range(n_groups)])
    return {"ns": ns, "diff": float(stat(mu))}


def pair_grp(a, b):
    g = np.full(len(a), -1)
    g[b] = 1
    g[a] = 0
    return g


def did_grp(A, a, b):
    hi = A[:, C["hi"]]
    g = np.full(len(a), -1)
    g[(hi == 1) & b] = 1
    g[(hi == 1) & a] = 0
    g[(hi == 0) & b] = 3
    g[(hi == 0) & a] = 2
    return g


def mean_cost(A, mask, col="r1000"):
    v = A[mask, C[col]]
    v = v[np.isfinite(v)]
    return {"n": int(len(v)), "mean": float(v.mean() - T.COST) if len(v) else None}


# ════════════════════ 判定 ════════════════════

def judge_pair(full, early, late, mean_a_cost, d60, kind):
    if full.get("lo") is None or min(full["ns"]) < T.MIN_N:
        return "件数不足"
    for sign, base in ((-1, WORDS[kind][0]), (+1, WORDS[kind][1])):
        whole = full["hi"] < 0 if sign < 0 else full["lo"] > 0
        if whole and T._side(early.get("diff"), sign) and T._side(late.get("diff"), sign) and T._side(mean_a_cost, sign):
            return T._verdict(base, T.check60(min(d60["ns"]), d60.get("diff"), sign))
    return "見えない"


def judge_did(full, early, late, d60):
    if full.get("lo") is None or min(full["ns"]) < T.MIN_N:
        return "件数不足"
    for sign, base in ((-1, DID_WORDS[0]), (+1, DID_WORDS[1])):
        whole = full["hi"] < 0 if sign < 0 else full["lo"] > 0
        if whole and T._side(early.get("diff"), sign) and T._side(late.get("diff"), sign):
            return T._verdict(base, T.check60(min(d60["ns"]), d60.get("diff"), sign))
    return DID_WORDS[2]


# ════════════════════ まとめ ════════════════════

def band_labels(gap):
    """窓 → 区分の名前（GAP_BANDS の a ≤ 窓 ＜ b）"""
    edges = np.array([b for _, _, b in GAP_BANDS[:-1]])
    return np.array([lab for lab, _, _ in GAP_BANDS])[np.searchsorted(edges, gap, side="right")]


def _mean(v):
    v = v[np.isfinite(v)]
    return {"n": int(len(v)), "mean": float(v.mean()) if len(v) else None}


def _trap(v):
    v = v[np.isfinite(v)]
    return {"n": int(len(v)), "mean": float((v <= T.TRAP).mean()) if len(v) >= Y.MIN_CELL else None}


def analyze(A):
    A = A[np.isfinite(A[:, C["r1000"]]) | np.isfinite(A[:, C["r930"]])]
    M = masks(A)
    has10 = np.isfinite(A[:, C["r1000"]])
    days = np.unique(A[has10, C["day"]])
    cut = days[len(days) // 2] if len(days) else 0
    early, late = A[:, C["day"]] < cut, A[:, C["day"]] >= cut
    d60 = np.unique(A[np.isfinite(A[:, C["r930"]]), C["day"]])
    iso = lambda o: dt.date.fromordinal(int(o)).isoformat() if o else None  # noqa: E731
    res = {"n_rows": int(len(A)), "n_2y": int(has10.sum()), "days_2y": int(len(days)), "first": iso(days[0]) if len(days) else None,
           "last": iso(days[-1]) if len(days) else None, "cut": iso(cut), "n_60d": int(np.isfinite(A[:, C["r930"]]).sum()),
           "days_60d": int(len(d60)), "first_60d": iso(d60[0]) if len(d60) else None, "last_60d": iso(d60[-1]) if len(d60) else None,
           "group_n": {k: int((m & has10).sum()) for k, m in M.items()},
           "hi_n": {str(h): int(((A[:, C["hi"]] == h) & has10).sum()) for h in (1, 0, -1)}}
    res["pairs"] = {}
    for key, name, kind, gk in PAIRS:
        grp = pair_grp(M[gk], M["base"])
        q = {"name": name, "all": safe(A, "r1000", grp, 2, _diff2),
             "early": plain(A[early], "r1000", grp[early], 2, _diff2), "late": plain(A[late], "r1000", grp[late], 2, _diff2),
             "mean_a_cost": mean_cost(A, M[gk]), "mean_b_cost": mean_cost(A, M["base"]),
             "d60": plain(A, "r930", grp, 2, _diff2)}
        q["verdict"] = judge_pair(q["all"], q["early"], q["late"], q["mean_a_cost"]["mean"], q["d60"], kind)
        res["pairs"][key] = q
    grp = did_grp(A, M["up1"], M["base"])
    g5 = {"name": "G5 高値更新ならではか（高値更新の翌朝の G1 − それ以外の朝の G1）", "all": safe(A, "r1000", grp, 4, _did),
          "early": plain(A[early], "r1000", grp[early], 4, _did), "late": plain(A[late], "r1000", grp[late], 4, _did),
          "d60": plain(A, "r930", grp, 4, _did)}
    g5["verdict"] = judge_did(g5["all"], g5["early"], g5["late"], g5["d60"])
    res["g5"] = g5
    # ── 読むための表（判定しない）──
    bands = band_labels(A[:, C["gap"]])
    res["by_band"] = {lab: {k: _mean(A[bands == lab, C[k]]) for k in ("r915", "r930", "r1000", "rclose")}
                      | {"trap": _trap(A[bands == lab, C["r1000"]])} for lab, _, _ in GAP_BANDS}
    tv = A[:, C["turnover"]]
    res["by_turnover"] = {lab: {gk: _mean(A[M[gk] & (tv >= a) & (tv < b), C["r1000"]]) for gk in ("up1", "base", "dn1")}
                          for lab, a, b in S.TURNOVER_BANDS}
    years = np.array([dt.date.fromordinal(int(o)).year for o in A[:, C["day"]]])
    res["g1_by_year"] = {str(y): plain(A[years == y], "r1000", pair_grp(M["up1"], M["base"])[years == y], 2, _diff2)
                         for y in sorted(set(years.tolist()))}
    hi = A[:, C["hi"]]
    res["by_high"] = {name: {gk: _mean(A[M[gk] & (hi == h), C["r1000"]]) for gk in ("up1", "base", "dn1")}
                      for name, h in (("高値更新の翌朝", 1), ("それ以外の朝", 0))}
    return res


# ════════════════════ 実行 ════════════════════

def load(codes, jpx, fetch=Y.fetch_chart, end_day=T.END_DAY):
    parts = []
    missing = {"daily": [], "h1": [], "m5": []}
    drops = {"n": 0}
    for i, code in enumerate(codes):
        d = fetch(code, "1d", T.DAILY_RANGE)
        h1 = T._first(fetch, code, "60m", T.H1_RANGES)
        m5 = T._first(fetch, code, "5m", T.M5_RANGES)
        if not d:
            missing["daily"].append(code)
            continue
        if not h1:
            missing["h1"].append(code)
        if not m5:
            missing["m5"].append(code)
        daily = sorted({t.date().isoformat(): (t.date().isoformat(), o, h, lo, c, v) for t, o, h, lo, c, v in d}.values())
        first = daily[0][0]

        def covered(day, first=first, code=code):
            return H.window_covered([(first,)], H.window_start(day)[0], code, jpx)

        parts.append(stock_rows(i, daily, T._by_day(m5), T._by_day(h1), covered, end_day=end_day, drops=drops))
        if (i + 1) % 200 == 0:
            print(f"  ...{i + 1}/{len(codes)}", flush=True)
        time.sleep(0.03)
    A = np.vstack(parts) if parts else np.zeros((0, len(COLS)))
    return A, missing, drops


def diag_summary(A, missing, n_codes):
    """件数とデータの形だけ（値動きは出さない）"""
    M = masks(A)
    has10 = np.isfinite(A[:, C["r1000"]])
    has930 = np.isfinite(A[:, C["r930"]])
    days = np.unique(A[has10, C["day"]])
    years = [dt.date.fromordinal(int(o)).year for o in A[has10, C["day"]]]
    return {"n_codes": n_codes, "missing": {k: len(v) for k, v in missing.items()}, "n_rows": int(len(A)),
            "n_2y": int(has10.sum()), "n_60d": int(has930.sum()), "days_2y": int(len(days)),
            "first": dt.date.fromordinal(int(days[0])).isoformat() if len(days) else None,
            "last": dt.date.fromordinal(int(days[-1])).isoformat() if len(days) else None,
            "by_year": {str(y): years.count(y) for y in sorted(set(years))},
            "group_n_2y": {k: int((m & has10).sum()) for k, m in M.items()},
            "group_n_60d": {k: int((m & has930).sum()) for k, m in M.items()},
            "hi_n_2y": {str(h): int(((A[:, C["hi"]] == h) & has10).sum()) for h in (1, 0, -1)},
            "g5_cells_60d": {f"hi{h}_{k}": int(((A[:, C["hi"]] == h) & M[k] & has930).sum()) for h in (1, 0) for k in ("up1", "base")}}


def _p(x, d=2):
    return Y._pct(x, d)


def _ns(q):
    return "対".join(f"{n:,}" for n in q["ns"])


def render_md(res):
    L = ["# J13 窓を開けて寄った株は、寄りのあとに戻されるか", "",
         f"作成: {res['generated_at']}（GitHub Actions で計算）。事前登録＝`{P.PREREG}`「J13」（指紋 sha256 `{(res.get('prereg_sha256') or '')[:16]}…`）。",
         "銘柄名は出しません。値は株価の変化率（％）。**売買の決まりではない**。", ""]
    r = res.get("result") or {}
    if r.get("error"):
        return "\n".join(L + [f"- ⚠️ 計算できず: {r['error']}", ""]) + "\n"
    L += [f"- 対象：東証の全上場 {r.get('n_codes')}銘柄（一覧 {r.get('list_date')}）のすべての朝。取れなかった銘柄 {r.get('n_missing')}",
          f"- 1時間足（判定の主・寄り→10:00）：{r['first']}〜{r['last']}・{r['days_2y']}営業日・{r['n_2y']:,}件（前半と後半の境 {r['cut']}）",
          f"- 5分足（オーナーの取引時間・寄り→9:30）：{r['first_60d']}〜{r['last_60d']}・{r['days_60d']}営業日・{r['n_60d']:,}件",
          "- 組の件数（10:00）：" + "／".join(f"{GROUP_NAMES[k]} {v:,}" for k, v in r["group_n"].items())
          + f"。高値更新の翌朝 {r['hi_n'].get('1', 0):,}件",
          f"- その日が {T.END_DAY} までの朝だけ。幅は99％（p＜0.05÷5）・日と銘柄で引き直した広いほう。±25％超で捨てた値 {r.get('n_dropped')}",
          "", "## 判定（事前登録の5つ・寄り→10:00 の平均の差・費用前）", ""]
    for key, _, _, _ in PAIRS:
        q = r["pairs"][key]
        a = q["all"]
        L.append(f"- **{q['name']}**：差 {_p(a.get('diff'))}（幅 {_p(a.get('lo'))}〜{_p(a.get('hi'))}・{_ns(a)}件）・"
                 f"前半 {_p(q['early'].get('diff'))}／後半 {_p(q['late'].get('diff'))}・"
                 f"その組の費用後の平均 {_p(q['mean_a_cost'].get('mean'))}（ふつう {_p(q['mean_b_cost'].get('mean'))}）・"
                 f"5分足の寄り→9:30 の差 {_p(q['d60'].get('diff'))}（{_ns(q['d60'])}件） → **{q['verdict']}**")
    g = r["g5"]
    a = g["all"]
    L.append(f"- **{g['name']}**：{_p(a.get('diff'))}（幅 {_p(a.get('lo'))}〜{_p(a.get('hi'))}・{_ns(a)}件）・"
             f"前半 {_p(g['early'].get('diff'))}／後半 {_p(g['late'].get('diff'))}・5分足 {_p(g['d60'].get('diff'))}（{_ns(g['d60'])}件） → **{g['verdict']}**")
    L += ["", "## 読むための表（判定しない）", "", "### 窓の区分ごと（寄りで買った場合の平均・費用なし）", "",
          "| 窓 | 寄り→9:15 | 寄り→9:30 | 寄り→10:00 | 寄り→大引け | 罠の割合（10:00 で −1％ 以下） |", "|---|---:|---:|---:|---:|---:|"]
    for lab, b in r["by_band"].items():
        L.append(f"| {lab} | " + " | ".join(f"{_p(b[k].get('mean'))}（{b[k]['n']:,}）" for k in ("r915", "r930", "r1000", "rclose"))
                 + f" | {T._share_txt(b['trap'])} |")
    L += ["", "### 前の日の売買代金ごと（寄り→10:00 の平均・費用なし）", "", "| 売買代金 | 高く寄った | ふつう | 安く寄った |", "|---|---:|---:|---:|"]
    for lab, b in r["by_turnover"].items():
        L.append(f"| {lab} | " + " | ".join(f"{_p(b[k].get('mean'))}（{b[k]['n']:,}）" for k in ("up1", "base", "dn1")) + " |")
    L += ["", "### 高値更新の翌朝とそれ以外の朝（寄り→10:00 の平均・費用なし）", "", "| 朝 | 高く寄った | ふつう | 安く寄った |", "|---|---:|---:|---:|"]
    for lab, b in r["by_high"].items():
        L.append(f"| {lab} | " + " | ".join(f"{_p(b[k].get('mean'))}（{b[k]['n']:,}）" for k in ("up1", "base", "dn1")) + " |")
    L += ["", "- 年ごとの G1 の差（高く寄った − ふつう・寄り→10:00）：" + "／".join(
        f"{y} {_p(v.get('diff'))}（{_ns(v)}）" for y, v in r["g1_by_year"].items()),
          "- 30件未満の区分は「—」。小さい株は売り買いの差が大きく、費用 0.1％ は甘い（判定は差なので費用は消える）。空売りは数えない。",
          "", "---", "", "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。"]
    return "\n".join(L) + "\n"


def main(argv):
    res = {"generated_at": dt.datetime.now(P.JST).isoformat(timespec="minutes"), "prereg_file": P.PREREG,
           "prereg_sha256": P.prereg_sha256(), "end_day": T.END_DAY}
    try:
        stocks, list_date = H.load_universe()
        codes = sorted(stocks)
        jpx = H.load_new_listings()
        A, missing, drops = load(codes, jpx)
        if "--diag" in argv:
            print(json.dumps(diag_summary(A, missing, len(codes)), ensure_ascii=False, indent=1))
            return 0
        bad = set(missing["daily"]) | set(missing["h1"])
        if len(bad) > T.MAX_MISSING * len(codes):
            raise RuntimeError(f"日足か1時間足を取れなかった銘柄が {len(bad)}/{len(codes)}＝5％超。偏った組で判定しない（取り直す）")
        res["result"] = dict(analyze(A), n_codes=len(codes), list_date=list_date,
                             n_missing={k: len(v) for k, v in missing.items()}, n_dropped=drops["n"])
    except Exception as e:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        if "--diag" in argv:
            return 1
        res["result"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1, default=str)
    md = render_md(res)
    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
