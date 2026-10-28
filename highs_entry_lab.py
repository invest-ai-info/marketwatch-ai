# -*- coding: utf-8 -*-
"""J49 上場来高値の「罠の見分け」「押し目の深さ」「手じまい」。2026-10-28 登録・オーナー「上場来高値を更新した銘柄がどこまで上げるか、
いつ買うべきか、いつ利確するべきか損切りするべきか分析してください」→「罠や騙しを高い確率で見つけてください。…どこまで押したときに
買った方が勝率が高くなるのか、期待値が高くなるのか…研究を進めてください」（テクニカルの区切りの例外）。PILLAR_PREREG.md「J49」。

ケース＝J48 と同じ（highs_shape_lab.stock_cases をそのまま使う）＋ 記録の日のあとに81本以上の足があるケースだけ。
全体＝毎日、その日より前の20本の平均売買代金1億円以上で誤りでない足のある全銘柄の「前の日の引け→その日の引け」と
「前の日の引け→その日の寄り」の平均（等しい重み）から作る2本の指数（引けの指数 C・寄りの指数 O）。
取引の全体比＝取引の損益 − 全体の同じ区間（寄りか指値で入った取引は入った日の O から、出た日の C まで）。
12の問い（T 罠の見分け4・P 押し目の深さ4・X 手じまい4）を3つの時代で。99.58％（0.05÷12）の幅・ケースの月で引き直す10,000回。

⚠️ 決まりは PILLAR_PREREG.md「J49」と下の定数に固定。値段は銘柄ごとの指数（momentum_lab.clean_index）で数える。
⚠️ 出力（highs-entry-lab.json / .md）は集計だけ・銘柄名とコードは出さない（GitHub 側で生成＝SYNC禁忌）。

実行: python highs_entry_lab.py --check   （点検だけ＝ケース・目印・約定の数。損益は数えない・何も書き出さない）
      python highs_entry_lab.py           （本番。Actions の highs-entry-lab.yml から手動で・1回だけ）
"""
import datetime as dt
import json
import sys

import numpy as np

import highs_shape_lab as S
import jp_bars
import momentum_lab as M
import pillar_lab as P

OUT_JSON, OUT_MD = "highs-entry-lab.json", "highs-entry-lab.md"
NEED_AFTER = 81               # 記録の日のあとに要る足（20本の待ち＋60本の持ち＋1）
HOLD = 60                     # 買った日を1本目として60本目の引けで売る
WAIT = 20                     # 押し目の指値を置く本数（記録の次の日から）
COST = 0.001                  # 往復 0.1％（1回の取引ごと）
TRAP = -0.10                  # 罠＝全体比 −10％以下（J48 と同じ・費用なし）
HIGH_PROB = 0.50              # 「高い確率」＝目印ありの罠の割合が3つの時代とも 50％以上
# T1 急騰の重なり（記録の日）
M25_HOT, RET_HOT, TVX_HOT, STREAK_HOT, HOT_MIN = 0.20, 0.10, 3.0, 4, 3
T3_DAYS, T3_DROP = 5, 0.10    # T3：記録の次の日から5本のうちに、終値が記録の日の終値の −10％以下
P_DEPTH = {"P1": 0.05, "P2": 0.10, "P3": 0.20}   # P4 は25日線
X_RULES = {"X1": {"stop": 0.10}, "X2": {"stop": 0.20}, "X3": {"trail": 0.15}, "X4": {"stop": 0.10, "tp": 0.20}}
N_Q = 12
ALPHA = 0.05 / N_Q            # 99.58％ の幅
N_BOOT = 10000
MIN_GROUP = S.MIN_GROUP       # 50件未満＝保留
ERAS = S.ERAS
YOUNG_DAYS = S.YOUNG_DAYS
OK, HALF, REV, NONE, HOLD_V = S.OK, S.HALF, S.REV, S.NONE, S.HOLD_V

QUESTIONS = (
    ("T1", "罠の見分け・急騰の重なり（25日線 +20％以上・その日 +10％以上・売買代金3倍以上・4本続けて上げ のうち3つ以上 − 2つ以下）", +1),
    ("T2", "罠の見分け・翌日の崩れ（記録の次の日の終値が記録の日の安値より下 − それ以外）", +1),
    ("T3", "罠の見分け・5本以内の大きな下げ（終値が記録の日の終値の −10％以下になった − ならなかった）", +1),
    ("T4", "罠の見分け・急騰の重なり かつ 翌日の崩れ − それ以外", +1),
    ("P1", "押し目の深さ・記録の日の終値の −5％ の指値（20本のうち）− 次の日の寄りで買う", +1),
    ("P2", "押し目の深さ・−10％ の指値 − 次の日の寄りで買う", +1),
    ("P3", "押し目の深さ・−20％ の指値 − 次の日の寄りで買う", -1),
    ("P4", "押し目の深さ・25日線の指値 − 次の日の寄りで買う", +1),
    ("X1", "手じまい・損切り −10％ − 60本持つ", -1),
    ("X2", "手じまい・損切り −20％ − 60本持つ", +1),
    ("X3", "手じまい・高値からの戻り売り −15％ − 60本持つ", +1),
    ("X4", "手じまい・利確 +20％ と損切り −10％ − 60本持つ", -1),
)

# 読むための表（判定しない）
READ_DEPTHS = (0.03, 0.05, 0.075, 0.10, 0.125, 0.15, 0.20, 0.25, 0.30)
READ_STOPS = (0.05, 0.08, 0.10, 0.15, 0.20, 0.25, 0.30)
READ_TRAILS = (0.10, 0.15, 0.20, 0.25)
READ_TPS = (0.10, 0.15, 0.20, 0.30, 0.50)     # 損切り −10％ と組み合わせ
READ_HOLDS = (20, 40, 60)
READ_T3 = (0.05, 0.10, 0.15)
RISE_LEVELS = (0.10, 0.20, 0.30, 0.50, 1.00)
WICK = 0.05                   # 上ヒゲ＝高値 ÷ 終値 − 1 が 5％以上
TVX_READ = (5.0, 10.0)


# ════════════════════ 全体の指数 ════════════════════

def _tv20(c, v):
    """その日より前の20本の平均売買代金（J48 と同じ）"""
    tv = c * v
    out = np.full(len(c), np.nan)
    rm = S._rolling_mean(tv, S.TV_N)
    out[S.TV_N:] = rm[S.TV_N - 1:-1]
    return tv, out


def _arrays(day, vals):
    o, h, l, c, v = (vals[:, i].astype(np.float64) for i in range(5))
    Pi, Q, Hx, _ = M.clean_index(day, o, h, l, c)
    Lx = Pi * np.where(c > 0, l / np.where(c > 0, c, 1.0), 1.0)
    return o, h, l, c, v, Pi, Q, Hx, Lx


def market_index(series, cal):
    """→ (C, O)：取引日ごとの引けの指数と寄りの指数。その日より前の20本の平均売買代金1億円以上で誤りでない足の等しい重みの平均"""
    cal = np.asarray(cal, np.int64)
    sc, so, cnt = np.zeros(len(cal)), np.zeros(len(cal)), np.zeros(len(cal))
    if not len(cal):
        return np.ones(0), np.ones(0)
    for day, vals in series.values():
        if len(day) < S.TV_N + 2:
            continue
        o, h, l, c, v, Pi, Q, _, _ = _arrays(day, vals)
        good = S.good_days(day, o, h, l, c)
        _, tv20 = _tv20(c, v)
        ok = good & np.isfinite(tv20) & (tv20 >= S.TV_MIN)
        ok[0] = False
        idx = np.nonzero(ok)[0]
        if not len(idx):
            continue
        d = day[idx].astype(np.int64)
        ci = np.clip(np.searchsorted(cal, d), 0, len(cal) - 1)
        on = cal[ci] == d
        np.add.at(sc, ci[on], (Pi[idx] / Pi[idx - 1] - 1)[on])
        np.add.at(so, ci[on], (Q[idx] / Pi[idx - 1] - 1)[on])
        np.add.at(cnt, ci[on], 1)
    mc = np.where(cnt > 0, sc / np.where(cnt > 0, cnt, 1), 0.0)
    mo = np.where(cnt > 0, so / np.where(cnt > 0, cnt, 1), 0.0)
    C = np.cumprod(1 + mc)
    O = np.r_[1.0, C[:-1]] * (1 + mo)
    return C, O


class Market:
    """取引日の表と2本の指数 → 区間の全体の損益"""

    def __init__(self, cal, C, O):
        self.cal, self.C, self.O = np.asarray(cal, np.int64), C, O

    def k(self, day_ord):
        return max(int(np.searchsorted(self.cal, int(day_ord), side="right")) - 1, 0)

    def ret(self, d_in, d_out, at_open=True):
        base = self.O[self.k(d_in)] if at_open else self.C[self.k(d_in)]
        return float(self.C[self.k(d_out)] / base - 1)


# ════════════════════ 1本の取引 ════════════════════

def fill_limit(Q, Lx, j, limits):
    """記録の日 j の次の日から len(limits) 本、買いの指値 limits[i] を置く → (買った足, 買値) か None。
    安値が指値以下になった最初の日に、寄りが指値以下なら寄りの値で、そうでなければ指値で買う"""
    w = len(limits)
    if j + w >= len(Q):
        return None
    lows = Lx[j + 1:j + 1 + w]
    lim = np.asarray(limits, float)
    hit = np.isfinite(lim) & (lows <= lim)
    if not hit.any():
        return None
    k = int(np.argmax(hit))
    f = j + 1 + k
    return f, float(min(Q[f], lim[k]))


def exit_fixed(Q, Hx, Lx, Pi, f, px, stop=None, tp=None, hold=HOLD):
    """f＝買った足・px＝買値 → (売値, 売った足)。損切りの逆指値・利確の指値は買った日から置く。
    届いた最初の日に、寄りがそれより不利なら寄りの値で、そうでなければその値。同じ日に両方なら損切りが先。届かなければ hold 本目の引け"""
    last = f + hold - 1
    lo, hi = Lx[f:last + 1], Hx[f:last + 1]
    sl = px * (1 - stop) if stop else None
    tg = px * (1 + tp) if tp else None
    hs = (lo <= sl) if sl is not None else np.zeros(len(lo), bool)
    ht = (hi >= tg) if tg is not None else np.zeros(len(hi), bool)
    hit = hs | ht
    if not hit.any():
        return float(Pi[last]), last
    k = int(np.argmax(hit))
    t = f + k
    if hs[k]:
        return float(min(Q[t], sl)), t
    return float(max(Q[t], tg)), t


def exit_trail(Q, Lx, Pi, f, px, trail, hold=HOLD):
    """戻り売り：買った日からのいちばん高い終値 ×（1 − trail）を、次の日から毎日引けで置き直す"""
    last = f + hold - 1
    lv = np.maximum.accumulate(Pi[f:last])[:] * (1 - trail)     # 足 f+1..last の逆指値（前の日の引けまでの高い終値から）
    lows = Lx[f + 1:last + 1]
    hit = lows <= lv
    if not hit.any():
        return float(Pi[last]), last
    k = int(np.argmax(hit))
    t = f + 1 + k
    return float(min(Q[t], lv[k])), t


def up_streak(Pi):
    """その日まで続けて終値が上げた本数"""
    n = len(Pi)
    up = np.r_[False, Pi[1:] > Pi[:-1]] if n else np.zeros(0, bool)
    idx = np.arange(n)
    return idx - np.maximum.accumulate(np.where(up, 0, idx))


# ════════════════════ 1銘柄 ════════════════════

def stock_cases(day, vals, mkt, clusters=()):
    """1銘柄 → (ケースの一覧, 81本の足が無くて落ちた数)。ケースは J48 と同じ決め方（highs_shape_lab.stock_cases）"""
    base, _ = S.stock_cases(day, vals, clusters=clusters)
    if not base:
        return [], 0
    o, h, l, c, v, Pi, Q, Hx, Lx = _arrays(day, vals)
    n = len(day)
    ma25, ma75 = S._rolling_mean(Pi, S.MA_N), S._rolling_mean(Pi, 75)
    streak = up_streak(Pi)
    D = day.astype(np.int64)
    out, short = [], 0
    calset = mkt.cal

    def xs(f, px, out_px, t, cost=True):
        """全体比（cost＝費用を引く）"""
        r = out_px / px - 1 - (COST if cost else 0.0)
        return r - mkt.ret(D[f], D[t], at_open=True)

    def window(a, cost=False):
        """足 a の寄りで買い、60本目の引けで売った全体比（罠の物差し＝費用なし）"""
        return xs(a, float(Q[a]), float(Pi[a + HOLD - 1]), a + HOLD - 1, cost)

    for rec in base:
        j = int(np.searchsorted(day, rec["day"]))
        k = int(np.searchsorted(calset, int(D[j])))
        if k >= len(calset) or int(calset[k]) != int(D[j]):
            continue                              # 取引日でない日（J48 と同じ）
        if j + NEED_AFTER >= n:
            short += 1
            continue
        m25, ret1, tvx = rec.get("m25"), rec.get("ret1"), rec.get("tvx")
        flags = [m25 is not None and np.isfinite(m25) and m25 >= M25_HOT,
                 ret1 is not None and np.isfinite(ret1) and ret1 >= RET_HOT,
                 tvx is not None and np.isfinite(tvx) and tvx >= TVX_HOT,
                 int(streak[j]) >= STREAK_HOT]
        hot = int(sum(flags))
        t2 = bool(Pi[j + 1] < Lx[j])
        r = {"day": int(D[j]), "hot": hot, "hot_flags": [bool(x) for x in flags], "t2": t2,
             "wick": bool(Hx[j] / Pi[j] - 1 >= WICK), "tvx": tvx,
             "young": rec.get("age") is not None and rec["age"] < YOUNG_DAYS}
        # 基準 B0（次の日の寄り → 60本目の引け）
        f0, px0 = j + 1, float(Q[j + 1])
        r["b0_raw"] = window(f0)
        r["b0"] = r["b0_raw"] - COST
        r["w_t2"] = window(j + 2)
        # T3 と読むための 5本以内の下げ
        r["t3"] = {}
        for drop in READ_T3:
            ks = [i for i in range(j + 1, j + T3_DAYS + 1) if Pi[i] <= Pi[j] * (1 - drop)]
            a = (ks[0] + 1) if ks else (j + T3_DAYS + 1)
            r["t3"][f"{drop:.2f}"] = {"flag": bool(ks), "x": window(a)}
        # 押し目（20本のうちの指値・60本持つ）
        r["p"] = {}
        for d in sorted(set(READ_DEPTHS) | set(P_DEPTH.values())):
            r["p"][f"{d:.3f}"] = _pull(Q, Lx, Pi, j, np.full(WAIT, Pi[j] * (1 - d)), xs)
        r["p"]["ma25"] = _pull(Q, Lx, Pi, j, ma25[j:j + WAIT], xs)
        r["p"]["ma75"] = _pull(Q, Lx, Pi, j, ma75[j:j + WAIT], xs)
        # 手じまい（B0 で買う）
        r["x"] = {"X0": r["b0"]}
        for q, rule in X_RULES.items():
            if "trail" in rule:
                px, t = exit_trail(Q, Lx, Pi, f0, px0, rule["trail"])
            else:
                px, t = exit_fixed(Q, Hx, Lx, Pi, f0, px0, stop=rule.get("stop"), tp=rule.get("tp"))
            r["x"][q] = xs(f0, px0, px, t)
            r.setdefault("x_hit", {})[q] = bool(t < f0 + HOLD - 1 or px != float(Pi[f0 + HOLD - 1]))
        r["xr"] = {}
        for s in READ_STOPS:
            px, t = exit_fixed(Q, Hx, Lx, Pi, f0, px0, stop=s)
            r["xr"][f"stop{s:.2f}"] = xs(f0, px0, px, t)
        for s in READ_TRAILS:
            px, t = exit_trail(Q, Lx, Pi, f0, px0, s)
            r["xr"][f"trail{s:.2f}"] = xs(f0, px0, px, t)
        for s in READ_TPS:
            px, t = exit_fixed(Q, Hx, Lx, Pi, f0, px0, stop=0.10, tp=s)
            r["xr"][f"tp{s:.2f}"] = xs(f0, px0, px, t)
        for hd in READ_HOLDS:
            t = f0 + hd - 1
            r["xr"][f"hold{hd}"] = xs(f0, px0, float(Pi[t]), t)
        # どこまで上げるか（買値から）
        r["mfe60"] = float(Hx[f0:f0 + HOLD].max() / px0 - 1)
        r["peak60"] = int(np.argmax(Hx[f0:f0 + HOLD])) + 1
        r["mfe120"] = float(Hx[f0:f0 + 120].max() / px0 - 1) if f0 + 120 <= n else None
        out.append(r)
    return out, short


def _pull(Q, Lx, Pi, j, limits, xs):
    got = fill_limit(Q, Lx, j, limits)
    if not got:
        return None
    f, px = got
    t = f + HOLD - 1
    return xs(f, px, float(Pi[t]), t)


def collect(series, cal):
    """{code: (日, 値)} → (ケースの一覧, 81本の足が無くて落ちた数, Market)"""
    C, O = market_index(series, cal)
    mkt = Market(cal, C, O)
    clusters = set(S.cluster_starts(series))
    cases, short = [], 0
    for day, vals in series.values():
        cs, sh = stock_cases(day, vals, mkt, clusters=clusters)
        cases += cs
        short += sh
    return cases, short, mkt


# ════════════════════ 数える ════════════════════

def split_eras(cases):
    by = {e: [] for e, *_ in ERAS}
    for r in cases:
        e = S.era_of(r["day"])
        if e:
            by[e].append(r)
    return by


def _trap(x):
    return None if x is None else (1.0 if x <= TRAP else 0.0)


def rows_of(q, rs):
    """問い → [(月, 値, "A"/"B")]"""
    out = []
    for r in rs:
        m = S.month_of(r["day"])
        if q == "T1":
            out.append((m, _trap(r["b0_raw"]), "A" if r["hot"] >= HOT_MIN else "B"))
        elif q == "T2":
            out.append((m, _trap(r["w_t2"]), "A" if r["t2"] else "B"))
        elif q == "T3":
            t = r["t3"][f"{T3_DROP:.2f}"]
            out.append((m, _trap(t["x"]), "A" if t["flag"] else "B"))
        elif q == "T4":
            out.append((m, _trap(r["w_t2"]), "A" if (r["hot"] >= HOT_MIN and r["t2"]) else "B"))
        elif q.startswith("P"):
            key = "ma25" if q == "P4" else f"{P_DEPTH[q]:.3f}"
            if r["p"].get(key) is not None:
                out.append((m, r["p"][key], "A"))
            out.append((m, r["b0"], "B"))
        else:
            out.append((m, r["x"][q], "A"))
            out.append((m, r["x"]["X0"], "B"))
    return out


def stats(xs, trap_x=None):
    """読むための数字：件数・平均（期待値）・中央値・勝率（0より上）・罠（−10％以下）"""
    x = [v for v in xs if v is not None]
    tx = [v for v in (trap_x if trap_x is not None else x) if v is not None]
    if not x:
        return {"n": 0, "mean": None, "median": None, "win": None, "trap": None}
    return {"n": len(x), "mean": float(np.mean(x)), "median": float(np.median(x)),
            "win": float(np.mean([v > 0 for v in x])), "trap": (float(np.mean([v <= TRAP for v in tx])) if tx else None)}


def group_stats(q, rs):
    """判定の中身（組ごとの数字）"""
    rows = rows_of(q, rs)
    a = [x for _, x, g in rows if g == "A"]
    b = [x for _, x, g in rows if g == "B"]
    if q.startswith("T"):
        return {"a_trap": (float(np.mean(a)) if a else None), "b_trap": (float(np.mean(b)) if b else None), "n_a": len(a), "n_b": len(b)}
    return {"a": stats(a), "b": stats(b)}


def analyze(cases, n_boot=N_BOOT):
    by = split_eras(cases)
    res = {"eras": {e: {"n": len(rs)} for e, rs in by.items()}, "questions": {}, "read": read_tables(by)}
    for q, name, sign in QUESTIONS:
        per = {}
        for e, rs in by.items():
            b = S.band_diff(rows_of(q, rs), alpha=ALPHA, n_boot=n_boot, seed=P.SEED)
            b["word"] = S.era_word(b, sign)
            b["groups"] = group_stats(q, rs)
            per[e] = b
        allrows = [x for rs in by.values() for x in rows_of(q, rs)]
        verdict = S.overall([per[e]["word"] for e, *_ in ERAS])
        x = {"name": name, "sign": sign, "eras": per, "verdict": verdict,
             "pooled": S.band_diff(allrows, alpha=ALPHA, n_boot=n_boot, seed=P.SEED)}
        if q.startswith("T"):
            rates = [per[e]["mean_a"] for e, *_ in ERAS]
            x["high_prob"] = (verdict == OK and all(v is not None and v >= HIGH_PROB for v in rates))
        res["questions"][q] = x
    return res


def read_tables(by):
    """判定しない表（時代ごと）"""
    out = {}
    for e, rs in by.items():
        t = {}
        # どこまで上げるか
        def rise(sub):
            m60 = [r["mfe60"] for r in sub]
            m120 = [r["mfe120"] for r in sub if r["mfe120"] is not None]
            return {"n": len(sub), "median60": (float(np.median(m60)) if m60 else None),
                    "reach60": {f"{lv:.2f}": (float(np.mean([x >= lv for x in m60])) if m60 else None) for lv in RISE_LEVELS},
                    "peak_bar60": (float(np.median([r["peak60"] for r in sub])) if sub else None),
                    "n120": len(m120), "median120": (float(np.median(m120)) if m120 else None),
                    "reach120": {f"{lv:.2f}": (float(np.mean([x >= lv for x in m120])) if m120 else None) for lv in RISE_LEVELS}}
        t["rise"] = {"全部": rise(rs), "急騰の点数 0〜1": rise([r for r in rs if r["hot"] <= 1]),
                     "急騰の点数 2": rise([r for r in rs if r["hot"] == 2]), "急騰の点数 3〜4": rise([r for r in rs if r["hot"] >= 3])}
        # 押し目の深さ
        pull = {"次の日の寄り（基準）": dict(stats([r["b0"] for r in rs]), fill=1.0)}
        for key in [f"{d:.3f}" for d in READ_DEPTHS] + ["ma25", "ma75"]:
            xs_ = [r["p"].get(key) for r in rs]
            got = [x for x in xs_ if x is not None]
            label = {"ma25": "25日線", "ma75": "75日線"}[key] if key.startswith("ma") else f"−{float(key) * 100:g}％"
            pull[label] = dict(stats(got), fill=(len(got) / len(rs) if rs else None))
        t["pullback"] = pull
        # 罠の目印
        traps = {}
        for k in range(5):
            traps[f"急騰の点数 {k}"] = stats([r["b0_raw"] for r in rs if r["hot"] == k])
        for i, lab in enumerate(("25日線 +20％以上", "その日 +10％以上", "売買代金3倍以上", "4本続けて上げ")):
            traps[lab] = stats([r["b0_raw"] for r in rs if r["hot_flags"][i]])
        traps["上ヒゲ 5％以上"] = stats([r["b0_raw"] for r in rs if r["wick"]])
        for x in TVX_READ:
            traps[f"売買代金 {x:g}倍以上"] = stats([r["b0_raw"] for r in rs if r["tvx"] is not None and r["tvx"] >= x])
        traps["上場1年未満"] = stats([r["b0_raw"] for r in rs if r["young"]])
        traps["翌日の崩れ（次の次の日の寄りから）"] = stats([r["w_t2"] for r in rs if r["t2"]])
        traps["翌日の崩れなし（同じ窓）"] = stats([r["w_t2"] for r in rs if not r["t2"]])
        for drop in READ_T3:
            key = f"{drop:.2f}"
            traps[f"5本以内に −{drop * 100:g}％（その次の日の寄りから）"] = stats([r["t3"][key]["x"] for r in rs if r["t3"][key]["flag"]])
        traps["急騰の点数 3以上 かつ 翌日の崩れ"] = stats([r["w_t2"] for r in rs if r["hot"] >= HOT_MIN and r["t2"]])
        traps["急騰の点数 2以上 かつ 翌日の崩れ"] = stats([r["w_t2"] for r in rs if r["hot"] >= 2 and r["t2"]])
        t["traps"] = traps
        # 手じまい
        ex = {}
        for key in [f"stop{s:.2f}" for s in READ_STOPS] + [f"trail{s:.2f}" for s in READ_TRAILS] + \
                   [f"tp{s:.2f}" for s in READ_TPS] + [f"hold{h}" for h in READ_HOLDS]:
            ex[_exit_label(key)] = stats([r["xr"][key] for r in rs])
        t["exits"] = ex
        out[e] = t
    return out


def _exit_label(key):
    if key.startswith("stop"):
        return f"損切り −{float(key[4:]) * 100:g}％"
    if key.startswith("trail"):
        return f"戻り売り −{float(key[5:]) * 100:g}％"
    if key.startswith("tp"):
        return f"利確 +{float(key[2:]) * 100:g}％（損切り −10％）"
    return f"{key[4:]}本持つ"


# ════════════════════ 点検（損益なし） ════════════════════

def check_summary(cases, short, series, mkt, n_codes, missing, fallback, store):
    by = split_eras(cases)
    eras = {}
    for e, rs in by.items():
        eras[e] = {"cases": len(rs), "months": len({S.month_of(r["day"]) for r in rs}),
                   "T1_flagged": sum(1 for r in rs if r["hot"] >= HOT_MIN), "T2_flagged": sum(1 for r in rs if r["t2"]),
                   "T3_flagged": sum(1 for r in rs if r["t3"][f"{T3_DROP:.2f}"]["flag"]),
                   "T4_flagged": sum(1 for r in rs if r["hot"] >= HOT_MIN and r["t2"]),
                   "P_filled": {q: sum(1 for r in rs if r["p"].get("ma25" if q == "P4" else f"{P_DEPTH[q]:.3f}") is not None)
                                for q in ("P1", "P2", "P3", "P4")},
                   "X_touched": {q: sum(1 for r in rs if r.get("x_hit", {}).get(q)) for q in X_RULES}}
    led = S.ledger_cases()
    found = {"found": 0, "not_record": 0, "no_bar": 0, "no_stock": 0}
    for code, d in led:
        if code not in series:
            found["no_stock"] += 1
            continue
        v = S.is_record_day(*series[code], d)
        found["found" if v else "no_bar" if v is None else "not_record"] += 1
    return {"price_store": store, "n_codes": n_codes, "missing": missing, "fallback_skipped": fallback,
            "market_days": int(len(mkt.cal)), "dropped_without_81_bars": short, "eras": eras,
            "ledger": dict(found, total=len(led), share=(found["found"] / len(led) if led else None))}


# ════════════════════ 書く ════════════════════

def _p(x, d=2):
    return "—" if x is None else f"{x * 100:+.{d}f}％"


def _s(x):
    return "—" if x is None else f"{x * 100:.0f}％"


def _band(b):
    return "—" if b.get("lo") is None else f"{_p(b['lo'])} 〜 {_p(b['hi'])}"


ST_HEAD = ("| 組 | 件数 | 期待値（全体比の平均） | 中央値 | 勝率（全体比が0より上） | 罠（−10％以下） |", "|---|---:|---:|---:|---:|---:|")


def _st(label, s, extra=""):
    return f"| {label}{extra} | {s['n']} | {_p(s['mean'])} | {_p(s['median'])} | {_s(s['win'])} | {_s(s['trap'])} |"


def render_md(res):
    L = ["# J49 上場来高値の「罠の見分け」「押し目の深さ」「手じまい」", "",
         f"更新: {res.get('generated_at', '')}（事前登録＝`PILLAR_PREREG.md`「J49」・指紋 `{(res.get('prereg_sha256') or '')[:12]}`）", "",
         "- ケース＝J48 と同じ上場来高値（記録上の最高値・売買代金1億円以上・同じ銘柄は60本あける）のうち、記録の日のあとに81本以上の足があるもの",
         "- 数字＝取引の損益 − 全体（売買代金1億円以上の全銘柄の等しい重みの指数）の同じ区間＝**全体比**。期待値と勝率は往復 0.1％ を引いたあと。"
         "罠＝全体比（費用なし）−10％以下",
         "- 判定＝問いごとに3つの時代（E1 2006-01〜2016-10／E2 2016-11〜2023-09／E3 2023-10〜2026-07）で、組の差の99.58％の幅（月で引き直す）が"
         "まるごと予想の向き＝予想どおり。3つとも＝✅・2つ＝△・それ以外＝✕",
         "- ⚠️ 置き場は今の上場だけ（上場をやめた会社が入らない）＝罠の割合は低めに、伸びは高めに出る。指値は安値が触れたら約定とみなす（押し目の買い方は有利に出る）。"
         "銘柄名・コードは出さない。過去の成績は将来を約束しない", ""]
    r = res.get("result") or {}
    if r.get("error"):
        return "\n".join(L + [f"⚠️ 数えられなかった：{r['error']}", ""])
    L += ["## 判定", "", "| 問い | 予想 | E1 | E2 | E3 | まとめ | 3つを合わせた差（読むだけ） |", "|---|---|---|---|---|---|---|"]
    for q, name, sign in QUESTIONS:
        x = r["questions"][q]
        cells = []
        for e, *_ in ERAS:
            b = x["eras"][e]
            cells.append(f"{b['word']}<br>{_p(b['diff'])}（{_band(b)}）<br>{b['n_a']}／{b['n_b']}件")
        pb = x["pooled"]
        tag = ""
        if q.startswith("T") and x["verdict"] == OK:
            tag = "<br>高い確率（50％以上）" if x.get("high_prob") else "<br>罠の割合は上がるが半分には届かない"
        L.append(f"| {q} {name} | {'プラス' if sign > 0 else 'マイナス'} | " + " | ".join(cells) +
                 f" | **{x['verdict']}**{tag} | {_p(pb['diff'])}（{_band(pb)}） |")
    L += ["", "T の差＝罠の割合の差（目印あり − なし）。P・X の差＝期待値の差（費用後）", "", "## 問いごとの組（判定の中身）", ""]
    for q, name, sign in QUESTIONS:
        L += [f"### {q} {name}", ""]
        if q.startswith("T"):
            L += ["| 時代 | 目印あり 件数 | 罠の割合 | 目印なし 件数 | 罠の割合 |", "|---|---:|---:|---:|---:|"]
            for e, *_ in ERAS:
                g = r["questions"][q]["eras"][e]["groups"]
                L.append(f"| {e} | {g['n_a']} | {_s(g['a_trap'])} | {g['n_b']} | {_s(g['b_trap'])} |")
        else:
            L += list(ST_HEAD)
            for e, *_ in ERAS:
                g = r["questions"][q]["eras"][e]["groups"]
                L.append(_st(f"{e} {'この買い方' if q.startswith('P') else 'この手じまい'}", g["a"]))
                L.append(_st(f"{e} 基準", g["b"]))
        L.append("")
    L += ["## 読むための表（判定しない）", "",
          "⚠️ ここで良く見えた深さや幅は「結果を見たあとに選んだもの」＝そのまま決まりにしない（使うなら前向きの登録から）", ""]
    for e, *_ in ERAS:
        t = r["read"][e]
        L += [f"### {e}", "", "**どこまで上げるか**（次の日の寄りの買値から、60本〔120本〕のあいだのいちばん高い高値）", "",
              "| 組 | 件数 | 中央値 | +10％ | +20％ | +30％ | +50％ | 2倍 | いちばん高い日（本目・中央値） | 120本 中央値 | 120本で +50％ | 120本で2倍 |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for k, v in t["rise"].items():
            rc = v["reach60"]
            r1 = v["reach120"]
            L.append(f"| {k} | {v['n']} | {_p(v['median60'], 1)} | " + " | ".join(_s(rc[f'{lv:.2f}']) for lv in RISE_LEVELS) +
                     f" | {v['peak_bar60'] if v['peak_bar60'] is not None else '—'} | {_p(v['median120'], 1)} | {_s(r1['0.50'])} | {_s(r1['1.00'])} |")
        L += ["", "**押し目の深さ**（記録の日の終値からの指値・20本のうち・買えた日から60本）", "",
              "| 買い方 | 買えた割合 | 件数 | 期待値 | 中央値 | 勝率 | 罠 |", "|---|---:|---:|---:|---:|---:|---:|"]
        for k, v in t["pullback"].items():
            L.append(f"| {k} | {_s(v['fill'])} | {v['n']} | {_p(v['mean'])} | {_p(v['median'])} | {_s(v['win'])} | {_s(v['trap'])} |")
        L += ["", "**罠の目印**（罠＝全体比 −10％以下・費用なし）", "", *ST_HEAD]
        L += [_st(k, v) for k, v in t["traps"].items()]
        L += ["", "**手じまい**（次の日の寄りで買う）", "", *ST_HEAD]
        L += [_st(k, v) for k, v in t["exits"].items()] + [""]
    return "\n".join(L) + "\n"


def verdicts_of(res, today):
    """✕ の問いだけ検証済みリストへ（status stop）。✅・△ は前向きで確かめるまで載せない"""
    out = {}
    for q, name, sign in QUESTIONS:
        x = res["questions"][q]
        if not x["verdict"].startswith("✕"):
            continue
        pb = x["pooled"]
        out[q] = {"status": "stop", "decided_on": today, "n": pb["n_a"] + pb["n_b"], "mean": pb["diff"], "lo": pb["lo"], "hi": pb["hi"],
                  "reason": ("過去のデータで1回だけ数えて、3つの時代（2006〜2016年・2016〜2023年・2023〜2026年）で予想の向きにそろわなかった"
                             "（数字は上場来高値のあとの" + ("罠の割合の差" if q.startswith("T") else "全体と比べた期待値の差") +
                             "・3つの時代を合わせたもの）")}
    return out


def main(argv):
    res = {"generated_at": dt.datetime.now(P.JST).isoformat(timespec="minutes"), "prereg_file": P.PREREG,
           "prereg_sha256": P.prereg_sha256()}
    try:
        stocks, list_date = jp_bars.load_universe()
        codes = sorted(stocks)
        fetch = jp_bars.fetcher()
        store = jp_bars.info()
        fb = S.store_fallback()
        series, missing, cal = S.load_series(codes, fetch, fb)
        cases, short, mkt = collect(series, cal)
        if "--check" in argv:
            print(json.dumps(S.rounded(check_summary(cases, short, series, mkt, len(codes), missing, len(fb), store)),
                             ensure_ascii=False, indent=1))
            return 0
        if not store or store.get("daily_range") != jp_bars.FULL_DAILY:
            raise RuntimeError("値段の置き場の日足が全期間版ではない（先に jp-bars-cache を回す）")
        if missing > 0.05 * len(codes):
            raise RuntimeError("日足を取れなかった銘柄が5％超。偏った組で数えない（取り直す）")
        out = analyze(cases)
        res["price_store"] = store
        res["result"] = dict(out, n_codes=len(codes), list_date=list_date, n_missing=missing, n_fallback_skipped=len(fb),
                             dropped_without_81_bars=short)
        today = dt.datetime.now(P.JST).date().isoformat()
        res.update(kind="backtest",
                   titles={q: f"上場来高値・{name}（2006〜2026-07・全体と比べた差・1回だけ数えた）" for q, name, _ in QUESTIONS},
                   verdicts=verdicts_of(out, today),
                   progress={q: out["questions"][q]["pooled"]["n_a"] + out["questions"][q]["pooled"]["n_b"] for q, *_ in QUESTIONS})
    except Exception as e:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        if "--check" in argv:
            return 1
        res["result"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(S.rounded(res), fh, ensure_ascii=False, indent=1, default=str)
    md = render_md(res)
    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
