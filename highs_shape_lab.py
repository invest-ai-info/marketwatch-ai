# -*- coding: utf-8 -*-
"""J48 上場来高値の「形」：どんな値動きで付けた上場来高値が、そのあとも伸びるか。
2026-10-27 登録・オーナー「上場来高値更新の銘柄をチャート分析して、どんな形状が高値を更新し続けるのか…銘柄を選別できるように
研究してください」（テクニカルの区切りの例外）。PILLAR_PREREG.md「J48」。

ケース＝その日の高値が、その銘柄の記録（値段の置き場の最初の足から前の日まで）の高値をすべて上回った日（サイトの「記録上の最高値」）。
記録の最初から20本未満は入れない・その日より前の20本の平均売買代金1億円以上・誤りの日でない・同じ銘柄は前のケースから60本あける。
そのあと＝次の日の寄りで買い60本あとの引けで売る損益 − 同じ日に売買代金1億円以上の全銘柄を同じように買った平均（全体と比べた差）。
6つの問い（前の組 − 後の組）を3つの時代で。99.17％（0.05÷6）の幅・ケースの月で引き直す10,000回。
3つの時代すべて予想どおり＝✅／2つ＝△／それ以外＝✕。

⚠️ 決まりは PILLAR_PREREG.md「J48」と下の定数に固定。誤りの日の扱いは J42 と同じ（momentum_lab.clean_index）。
⚠️ 出力（highs-shape-lab.json / .md）は集計だけ・銘柄名とコードは出さない（GitHub 側で生成＝SYNC禁忌）。

実行: python highs_shape_lab.py --check   （点検だけ＝ケースと組の数・台帳の再現。損益は数えない・何も書き出さない）
      python highs_shape_lab.py           （本番。Actions の highs-shape-lab.yml から手動で・1回だけ）
"""
import csv
import datetime as dt
import json
import os
import sys

import numpy as np

import build_jp_highs as H
import jp_bars
import momentum_lab as M
import pillar_lab as P

OUT_JSON, OUT_MD = "highs-shape-lab.json", "highs-shape-lab.md"
LEDGER = "highs-ledger.csv"
LEDGER_FROM = "2026-10-08"
LEDGER_KINDS = ("記録上の最高値", "上場来")
TV_MIN = 1e8                  # その日より前の20本の平均売買代金（円）
TV_N = 20
MIN_BARS = 20                 # 記録の最初から20本未満の日は入れない
GAP = 60                      # 同じ銘柄は前のケースから60本あける
HOLD = 60                     # 次の日の寄り → 60本あとの引け
READ_HOLDS = (20, 120)        # 読むだけ
ID_N = 250                    # じわじわ度の本数
MA_N = 25
OLD_RECORD = dt.date(2001, 3, 31)   # 記録の始まりがこれより後なら、最初の足の日を上場の日とみなす
CLUSTER_N = 10                # 🆕 補足：同じ日に記録が始まる銘柄がこれ以上＝Yahoo の記録の始まり（上場の日ではない）
TRUNC_DAYS = 1826             # 🆕 補足：上場の日ではない記録の始まりから5年（暦日）たつまではケースにしない
YOUNG_DAYS, OLD_DAYS = 365, 1096
FRESH, STREAK = 250, 20       # Q5：前の記録から250本以上／20本以内
TV_BIG_X, TV_SMALL_X = 3.0, 1.5      # 読むだけ：その日の売買代金の倍率
UP_GOOD, DOWN_BAD = 0.10, -0.10      # 読むだけ：「伸びた」「罠」（全体比）
MIN_CAL = M.MIN_CAL           # 取引日＝50銘柄以上に足がある日
MIN_GROUP = 50
N_Q = 6
ALPHA = 0.05 / N_Q            # 99.17％ の幅
N_BOOT = 10000
ERAS = (("E1", "2006-01-01", "2016-10-31"),
        ("E2", "2016-11-01", "2023-09-30"),
        ("E3", "2023-10-01", "2026-07-31"))
# (問い, 名前, 予想の向き)。組の決め方は groups()
QUESTIONS = (("Q1", "じわじわ上げた株（じわじわ度の下の3分の1）− 少ない日に大きく上げた株（上の3分の1）", +1),
             ("Q2", "25日線から +20％以上離れた株 − +10％未満の株", -1),
             ("Q3", "その日 +10％以上上げた株 − +3％未満の株", -1),
             ("Q4", "引けでも前の記録の上に残った株 − 場中だけ抜けて引けは前の記録より下の株", +1),
             ("Q5", "1年以上ぶりの更新（前の記録から250本以上）− 更新が続いている株（20本以内）", +1),
             ("Q6", "上場から1年未満の株 − 3年以上の株", -1))
OK, HALF, REV, NONE, HOLD_V = "✅ 3つの時代で同じ向き", "△ 2つの時代", "✕ 逆向き", "✕ 見えない", "保留"
EPOCH_ORD = M.EPOCH_ORD


# ════════════════════ 1銘柄 ════════════════════

def good_days(day, o, h, l, c):
    """誤りでない足（momentum_lab.clean_index と同じ物差し）。最初の足は前が無いので False"""
    n = len(day)
    ok_bar = (c > 0) & (l > 0) & (o > 0) & (h >= c * 0.999) & (l <= c * 1.001) & (o >= l * (1 - 1e-9)) & (o <= h * (1 + 1e-9))
    good = np.zeros(n, bool)
    if n > 1:
        prev = c[:-1]
        good[1:] = (ok_bar[1:] & (prev > 0) & (h[1:] <= prev * H.MAX_JUMP) & (l[1:] >= prev / H.MAX_JUMP)
                    & (np.diff(day) <= M.MAX_GAP_DAYS))
    return good


def _rolling_mean(x, n):
    """x[j−n+1..j] の平均（j<n−1 は nan）"""
    out = np.full(len(x), np.nan)
    if len(x) >= n:
        cs = np.cumsum(np.r_[0.0, x])
        out[n - 1:] = (cs[n:] - cs[:-n]) / n
    return out


def _r2(y):
    """対数の値段の一直線さ（最小二乗の当てはまり）"""
    x = np.arange(len(y), dtype=float)
    xm, ym = x.mean(), y.mean()
    sxx, syy = ((x - xm) ** 2).sum(), ((y - ym) ** 2).sum()
    if sxx <= 0 or syy <= 0:
        return None
    return float(((x - xm) * (y - ym)).sum() ** 2 / (sxx * syy))


def _fwd_arr(Pi, Q, js, k):
    """次の日の寄り → k本あとの引け（足りなければ nan）"""
    out = np.full(len(js), np.nan)
    ok = js + k < len(Pi)
    out[ok] = Pi[js[ok] + k] / Q[js[ok] + 1] - 1
    return out


def listing_start(day0, clusters=()):
    """記録の最初の足の日を上場の日とみなせるか（2001-03-31 より後で、多くの銘柄が同じ日に始まる日でない）"""
    return dt.date.fromordinal(int(day0)) > OLD_RECORD and int(day0) not in clusters


def cluster_starts(series, n=CLUSTER_N):
    """同じ日に記録が始まる銘柄が n 以上の日（Yahoo の記録の始まり・取引所の統合など）→ {日: 銘柄の数}"""
    cnt = {}
    for day, _ in series.values():
        if len(day):
            cnt[int(day[0])] = cnt.get(int(day[0]), 0) + 1
    return {d: k for d, k in cnt.items() if k >= n}


def stock_cases(day, vals, hold=HOLD, clusters=()):
    """1銘柄 → (ケースの一覧, 全体の平均に足す (日, [損益60, 引けからの損益60, 損益20, 損益120]))。
    ケースはその日の引けまでに分かる特徴と、そのあとの値（本数が足りなければ None）を持つ。
    記録の始まりが上場の日でない株は、始まりから5年たつまでケースにしない（記録の短さで見かけの最高値が続くのを防ぐ）"""
    o, h, l, c, v = (vals[:, i].astype(np.float64) for i in range(5))
    n = len(day)
    if n <= MIN_BARS:
        return [], (np.zeros(0, np.int64), np.zeros((4, 0)))
    Pi, Q, Hx, _ = M.clean_index(day, o, h, l, c)
    Lx = Pi * np.where(c > 0, l / np.where(c > 0, c, 1.0), 1.0)
    good = good_days(day, o, h, l, c)
    tv = c * v
    tv20 = np.full(n, np.nan)                 # その日より前の20本
    rm = _rolling_mean(tv, TV_N)
    tv20[TV_N:] = rm[TV_N - 1:-1]
    cm = np.maximum.accumulate(Hx)
    prev_max = np.r_[np.nan, cm[:-1]]
    newmax = np.r_[True, Hx[1:] > cm[:-1]]    # 前の記録の足＝その高値を初めて付けた足（同じ値に並んだ足は数えない）
    setidx = np.maximum.accumulate(np.where(newmax, np.arange(n), -1))
    ma25 = _rolling_mean(Pi, MA_N)
    ma75, ma200 = _rolling_mean(Pi, 75), _rolling_mean(Pi, 200)
    rng_pct = np.where(c > 0, (h - l) / np.where(c > 0, c, 1.0), np.nan)
    rng20, rng120 = _rolling_mean(rng_pct, 20), _rolling_mean(rng_pct, 120)
    dr = np.r_[0.0, Pi[1:] / Pi[:-1] - 1]
    cpos, cneg = np.cumsum(dr > 0), np.cumsum(dr < 0)
    young_record = listing_start(day[0], clusters)

    def fwd(j, k):
        return float(Pi[j + k] / Q[j + 1] - 1) if j + k < n else None

    # 全体の平均に足す分（売買代金1億円以上・60本あとがある足）＝配列で返す（足ごとの Python のループは重い）
    js = np.nonzero(np.isfinite(tv20) & (tv20 >= TV_MIN) & (np.arange(n) + hold < n))[0]
    market = (day[js].astype(np.int64), np.vstack([_fwd_arr(Pi, Q, js, hold), Pi[js + hold] / Pi[js] - 1,
                                                    _fwd_arr(Pi, Q, js, READ_HOLDS[0]), _fwd_arr(Pi, Q, js, READ_HOLDS[1])]))

    cases, last = [], -10 ** 9
    cand = (np.arange(n) >= MIN_BARS) & good & np.isfinite(tv20) & (tv20 >= TV_MIN) & (Hx > prev_max)
    if not young_record:
        cand &= (day.astype(np.int64) - int(day[0])) >= TRUNC_DAYS
    for j in np.nonzero(cand)[0]:
        if j - last < GAP:
            continue
        last = j
        pm = prev_max[j]
        ps = int(setidx[j - 1])
        idv = None
        if j >= ID_N:
            pret = Pi[j] / Pi[j - ID_N] - 1
            pos = (cpos[j] - cpos[j - ID_N]) / ID_N
            neg = (cneg[j] - cneg[j - ID_N]) / ID_N
            idv = float(np.sign(pret) * (neg - pos))
        age = (int(day[j]) - int(day[0])) if young_record else None
        rec = {"day": int(day[j]),
               "ret1": float(Pi[j] / Pi[j - 1] - 1),
               "m25": float(Pi[j] / ma25[j] - 1),
               "close_vs_rec": float(Pi[j] / pm - 1),
               "since_prev": int(j - ps),
               "id": idv,
               "age": age,
               "tv20": float(tv20[j]),
               "tvx": float(tv[j] / tv20[j]) if tv20[j] > 0 else None,
               "vcr": float(rng20[j] / rng120[j]) if j >= 120 and rng120[j] > 0 else None,
               "align": (bool(ma25[j] > ma75[j] > ma200[j] and ma200[j] > ma200[j - 20]) if j >= 220 else None),
               "r2": _r2(np.log(Pi[j - 119:j + 1])) if j >= 119 else None,
               "base_depth": (float(Lx[ps + 1:j].min() / pm - 1) if j - ps >= 2 else None),
               "r60": fwd(j, hold), "c60": (float(Pi[j + hold] / Pi[j] - 1) if j + hold < n else None),
               "r20": fwd(j, READ_HOLDS[0]), "r120": fwd(j, READ_HOLDS[1])}
        if j + hold < n:
            rec["again20"] = bool(Hx[j + 1:j + 21].max() > cm[j]) if j + 20 < n else None
            rec["again60"] = bool(Hx[j + 1:j + hold + 1].max() > cm[j])
            rec["dd60"] = float(Lx[j + 1:j + hold + 1].min() / Q[j + 1] - 1)
        cases.append(rec)
    return cases, market


# ════════════════════ 全銘柄 ════════════════════

OUTCOMES = (("r60", "x60"), ("c60", "xc60"), ("r20", "x20"), ("r120", "x120"))   # (そのあとの値, 全体と比べた差)


def collect(series, cal):
    """{code: (日, 値)} → ケースの一覧（全体と比べた差 x60・xc60・x20・x120 を付ける）。
    全体＝同じ日（取引日）に売買代金1億円以上の全銘柄を同じように買った平均（その銘柄自身を含む・等しい重み）"""
    cal = np.asarray(cal, np.int64)
    sums, cnts = np.zeros((4, len(cal))), np.zeros((4, len(cal)))
    cases = []
    clusters = set(cluster_starts(series))
    for code, (day, vals) in series.items():
        cs, (mdays, mvals) = stock_cases(day, vals, clusters=clusters)
        if len(mdays):
            ci = np.clip(np.searchsorted(cal, mdays), 0, len(cal) - 1)
            on = cal[ci] == mdays
            for i in range(4):
                ok = on & np.isfinite(mvals[i])
                np.add.at(sums[i], ci[ok], mvals[i][ok])
                np.add.at(cnts[i], ci[ok], 1)
        cases += cs
    with np.errstate(invalid="ignore", divide="ignore"):
        mkt = np.where(cnts > 0, sums / np.where(cnts > 0, cnts, 1), np.nan)
    kept = []
    for r in cases:
        k = int(np.searchsorted(cal, r["day"]))
        if k >= len(cal) or int(cal[k]) != r["day"]:
            continue                          # 取引日でない日（50銘柄未満）のケースは数えない
        for i, (key, xkey) in enumerate(OUTCOMES):
            base = mkt[i, k]
            r[xkey] = (r[key] - float(base)) if (r[key] is not None and np.isfinite(base)) else None
        kept.append(r)
    return kept


def era_of(day_ord):
    d = dt.date.fromordinal(int(day_ord)).isoformat()
    for e, a, b in ERAS:
        if a <= d <= b:
            return e
    return None


def tercile_cuts(x):
    x = np.asarray([v for v in x if v is not None], float)
    return (float(np.quantile(x, 1 / 3)), float(np.quantile(x, 2 / 3))) if len(x) >= 3 else (None, None)


def tercile(v, cuts):
    """下（≦1/3 の点）／上（＞2/3 の点）／真ん中"""
    if v is None or cuts[0] is None:
        return None
    return "low" if v <= cuts[0] else "high" if v > cuts[1] else "mid"


def groups(r, idcuts):
    """ケース → {問い: "A"（前の組）/"B"（後の組）/None}"""
    old = r["age"] is None or r["age"] >= OLD_DAYS
    t = tercile(r["id"], idcuts)
    return {"Q1": "A" if t == "low" else "B" if t == "high" else None,
            "Q2": "A" if r["m25"] >= 0.20 else "B" if r["m25"] < 0.10 else None,
            "Q3": "A" if r["ret1"] >= 0.10 else "B" if r["ret1"] < 0.03 else None,
            "Q4": "A" if r["close_vs_rec"] >= 0 else "B",
            "Q5": "A" if r["since_prev"] >= FRESH else "B" if r["since_prev"] <= STREAK else None,
            "Q6": "A" if (r["age"] is not None and r["age"] < YOUNG_DAYS) else "B" if old else None}


def score(g):
    """目安の点数（読むだけ）＝6つのうち「良いと見込む側」に当たる数"""
    good_side = {"Q1": "A", "Q2": "B", "Q3": "B", "Q4": "A", "Q5": "A", "Q6": "B"}
    return sum(1 for q, s in good_side.items() if g.get(q) == s)


def month_of(day_ord):
    return int(M.month_id([day_ord])[0])


def band_diff(rows, alpha=ALPHA, n_boot=N_BOOT, seed=P.SEED):
    """rows＝[(月, 値, "A"/"B")] → 平均の差（A − B）と、月を単位に引き直した両側の幅"""
    a = [(m, x) for m, x, g in rows if g == "A" and x is not None]
    b = [(m, x) for m, x, g in rows if g == "B" and x is not None]
    out = {"n_a": len(a), "n_b": len(b), "mean_a": _mean([x for _, x in a]), "mean_b": _mean([x for _, x in b]),
           "diff": None, "lo": None, "hi": None}
    if not a or not b:
        return out
    out["diff"] = out["mean_a"] - out["mean_b"]
    months = sorted({m for m, _ in a} | {m for m, _ in b})
    pos = {m: i for i, m in enumerate(months)}
    K = len(months)
    sa, na, sb, nb = (np.zeros(K) for _ in range(4))
    for m, x in a:
        sa[pos[m]] += x
        na[pos[m]] += 1
    for m, x in b:
        sb[pos[m]] += x
        nb[pos[m]] += 1
    if not n_boot:
        return out
    rng = np.random.default_rng(seed)
    sims = []
    for _ in range(n_boot // 1000):
        W = rng.multinomial(K, np.full(K, 1.0 / K), size=1000).astype(float)
        with np.errstate(invalid="ignore", divide="ignore"):
            sims.append((W @ sa) / (W @ na) - (W @ sb) / (W @ nb))
    s = np.concatenate(sims)
    out["nan_draws"] = int(np.isnan(s).sum())
    lo, hi = np.nanpercentile(s, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    out.update(lo=float(lo), hi=float(hi))
    return out


def era_word(b, sign):
    if min(b["n_a"], b["n_b"]) < MIN_GROUP or b["lo"] is None:
        return HOLD_V
    if (sign > 0 and b["lo"] > 0) or (sign < 0 and b["hi"] < 0):
        return "予想どおり"
    if (sign > 0 and b["hi"] < 0) or (sign < 0 and b["lo"] > 0):
        return "逆"
    return "見えない"


def overall(words):
    ok = sum(1 for w in words if w == "予想どおり")
    if HOLD_V in words:
        return HALF if ok >= 2 else HOLD_V
    if ok == 3:
        return OK
    if ok == 2:
        return HALF
    return REV if "逆" in words else NONE


def _mean(x):
    x = [v for v in x if v is not None]
    return float(np.mean(x)) if x else None


def _median(x):
    x = [v for v in x if v is not None]
    return float(np.median(x)) if x else None


def _share(x, f):
    x = [v for v in x if v is not None]
    return (sum(1 for v in x if f(v)) / len(x)) if x else None


def summary(rs, key="x60"):
    """読むための組の数字"""
    xs = [r.get(key) for r in rs]
    return {"n": len([x for x in xs if x is not None]), "mean": _mean(xs), "median": _median(xs),
            "up": _share(xs, lambda v: v >= UP_GOOD), "trap": _share(xs, lambda v: v <= DOWN_BAD),
            "again20": _share([r.get("again20") for r in rs], bool), "again60": _share([r.get("again60") for r in rs], bool),
            "dd60": _median([r.get("dd60") for r in rs])}


def split_eras(cases):
    by = {e: [] for e, *_ in ERAS}
    for r in cases:
        e = era_of(r["day"])
        if e and r.get("x60") is not None:
            by[e].append(r)
    return by


def analyze(cases, n_boot=N_BOOT):
    by = split_eras(cases)
    res = {"eras": {}, "questions": {}, "read": {}}
    gs = {}
    for e, rs in by.items():
        cuts = tercile_cuts([r["id"] for r in rs])
        res["eras"][e] = {"n": len(rs), "id_cuts": cuts, "all": summary(rs)}
        for r in rs:
            gs[id(r)] = groups(r, cuts)
    for q, name, sign in QUESTIONS:
        per = {}
        for e, rs in by.items():
            rows = [(month_of(r["day"]), r["x60"], gs[id(r)][q]) for r in rs]
            b = band_diff(rows, n_boot=n_boot)
            b["word"] = era_word(b, sign)
            b["a"] = summary([r for r in rs if gs[id(r)][q] == "A"])
            b["b"] = summary([r for r in rs if gs[id(r)][q] == "B"])
            b["close"] = band_diff([(month_of(r["day"]), r.get("xc60"), gs[id(r)][q]) for r in rs], n_boot=0)   # 読むだけ
            b["h20"] = band_diff([(month_of(r["day"]), r.get("x20"), gs[id(r)][q]) for r in rs], n_boot=0)
            b["h120"] = band_diff([(month_of(r["day"]), r.get("x120"), gs[id(r)][q]) for r in rs], n_boot=0)
            per[e] = b
        allrows = [(month_of(r["day"]), r["x60"], gs[id(r)][q]) for rs in by.values() for r in rs]
        res["questions"][q] = {"name": name, "sign": sign, "eras": per,
                               "verdict": overall([per[e]["word"] for e, *_ in ERAS]),
                               "pooled": band_diff(allrows, n_boot=n_boot)}   # 3つの時代を合わせた幅（読むだけ）
    res["read"] = read_tables(by, gs)
    return res


def read_tables(by, gs):
    """判定しない表（時代ごと）"""
    out = {}
    for e, rs in by.items():
        t = {}
        sc = {}
        for r in rs:
            sc.setdefault(score(gs[id(r)]), []).append(r)
        t["score"] = {str(k): summary(v) for k, v in sorted(sc.items())}
        t["tvx"] = {"3倍以上": summary([r for r in rs if r["tvx"] is not None and r["tvx"] >= TV_BIG_X]),
                    "1.5倍未満": summary([r for r in rs if r["tvx"] is not None and r["tvx"] < TV_SMALL_X])}
        for key, label in (("vcr", "値幅の縮み（20本÷120本）"), ("r2", "120本の一直線さ R²"), ("tv20", "売買代金の大きさ")):
            cuts = tercile_cuts([r[key] for r in rs])
            t[key] = {"cuts": cuts, "label": label,
                      **{g: summary([r for r in rs if tercile(r[key], cuts) == g]) for g in ("low", "mid", "high")}}
        t["align"] = {"そろう": summary([r for r in rs if r["align"] is True]),
                      "そろわない": summary([r for r in rs if r["align"] is False])}
        fresh = [r for r in rs if r["since_prev"] >= FRESH and r["base_depth"] is not None]
        t["base_depth"] = {"浅い（−20％より浅い）": summary([r for r in fresh if r["base_depth"] > -0.20]),
                           "中くらい（−20〜−40％）": summary([r for r in fresh if -0.40 < r["base_depth"] <= -0.20]),
                           "深い（−40％以下）": summary([r for r in fresh if r["base_depth"] <= -0.40])}
        yr = {}
        for r in rs:
            yr.setdefault(dt.date.fromordinal(r["day"]).year, []).append(r)
        t["years"] = {str(y): summary(v) for y, v in sorted(yr.items())}
        out[e] = t
    return out


# ════════════════════ 点検 ════════════════════

def ledger_cases(path=LEDGER, since=LEDGER_FROM):
    try:
        with open(path, encoding="utf-8-sig") as fh:
            return [(r["code"], r["date"]) for r in csv.DictReader(fh) if r.get("kind") in LEDGER_KINDS and r.get("date", "") >= since]
    except OSError:
        return []


def is_record_day(day, vals, date_iso):
    """その日が記録上の最高値の日か（売買代金と60本あけは見ない）→ True/False/None（足が無い）"""
    d = dt.date.fromisoformat(date_iso).toordinal()
    j = int(np.searchsorted(day, d))
    if j >= len(day) or int(day[j]) != d or j < MIN_BARS:
        return None
    o, h, l, c = (vals[:, i].astype(np.float64) for i in range(4))
    _, _, Hx, _ = M.clean_index(day, o, h, l, c)
    return bool(Hx[j] > Hx[:j].max())


def check_summary(cases, series, n_codes, missing, fallback, store):
    """損益を出さない点検（数だけ）"""
    by = {e: [] for e, *_ in ERAS}
    dropped = {e: 0 for e, *_ in ERAS}
    for r in cases:
        e = era_of(r["day"])
        if not e:
            continue
        if r.get("x60") is None:
            dropped[e] += 1
        else:
            by[e].append(r)
    eras = {}
    for e, rs in by.items():
        cuts = tercile_cuts([r["id"] for r in rs])
        cnt = {q: {"A": 0, "B": 0} for q, *_ in QUESTIONS}
        for r in rs:
            for q, g in groups(r, cuts).items():
                if g:
                    cnt[q][g] += 1
        eras[e] = {"cases": len(rs), "no_outcome_dropped": dropped[e], "with_id": sum(1 for r in rs if r["id"] is not None),
                   "months": len({month_of(r["day"]) for r in rs}), "groups": cnt}
    led = ledger_cases()
    found = {"found": 0, "not_record": 0, "no_bar": 0, "no_stock": 0}
    for code, d in led:
        if code not in series:
            found["no_stock"] += 1
            continue
        v = is_record_day(*series[code], d)
        found["found" if v else "no_bar" if v is None else "not_record"] += 1
    cl = cluster_starts(series)
    return {"price_store": store, "n_codes": n_codes, "missing": missing, "fallback_skipped": fallback,
            "record_start_clusters": {dt.date.fromordinal(d).isoformat(): k for d, k in sorted(cl.items())},
            "listing_start_stocks": sum(1 for day, _ in series.values() if len(day) and listing_start(day[0], set(cl))),
            "eras": eras, "ledger": dict(found, total=len(led), share=(found["found"] / len(led) if led else None))}


# ════════════════════ 読み込み ════════════════════

def load_series(codes, fetch, fallback=()):
    series, missing, cal = M.load([c for c in codes if c not in set(fallback)], fetch)
    return series, missing, cal


def store_fallback():
    b = jp_bars.bars()
    return sorted((b.fallback or {}).get("1d", [])) if b else []


# ════════════════════ 書く ════════════════════

def _p(x, d=2):
    return "—" if x is None else f"{x * 100:+.{d}f}％"


def _s(x):
    return "—" if x is None else f"{x * 100:.0f}％"


def _band(b):
    return "—" if b.get("lo") is None else f"{_p(b['lo'])} 〜 {_p(b['hi'])}"


def _row(label, s):
    return (f"| {label} | {s['n']} | {_p(s['mean'])} | {_p(s['median'])} | {_s(s['up'])} | {_s(s['trap'])} | "
            f"{_s(s['again60'])} | {_p(s['dd60'], 1)} |")


HEAD = ("| 組 | 件数 | 平均（全体比） | 中央値 | 伸びた（+10％以上） | 罠（−10％以下） | 60本の間に再び更新 | いちばん深い下げ（中央値） |",
        "|---|---:|---:|---:|---:|---:|---:|---:|")


def render_md(res):
    L = ["# J48 上場来高値の「形」：どんな値動きで付けた上場来高値が、そのあとも伸びるか", "",
         f"更新: {res.get('generated_at', '')}（事前登録＝`PILLAR_PREREG.md`「J48」・指紋 `{(res.get('prereg_sha256') or '')[:12]}`）", "",
         "- ケース＝記録上の最高値（置き場の記録で一番高い値）を付けた日・売買代金1億円以上・同じ銘柄は60本あける",
         "- 数字＝**次の日の寄りで買い、60本あとの引けで売った損益 − 同じ日に売買代金1億円以上の全銘柄を同じように買った平均**（費用・配当なし）",
         "- 判定＝問いごとに3つの時代（E1 2006-01〜2016-10／E2 2016-11〜2023-09／E3 2023-10〜2026-07）で、組の差の99.17％の幅（月で引き直す）が"
         "まるごと予想の向き＝予想どおり。3つとも＝✅・2つ＝△・それ以外＝✕",
         "- ⚠️ 置き場は今の上場だけ（上場をやめた会社が入らない）＝全体の水準は高めに出る。銘柄名・コードは出さない。過去の成績は将来を約束しない", ""]
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
        L.append(f"| {q} {name} | {'プラス' if sign > 0 else 'マイナス'} | " + " | ".join(cells) +
                 f" | **{x['verdict']}** | {_p(pb['diff'])}（{_band(pb)}） |")
    L += ["", "## 時代ごとのケース（全部）", "", *HEAD]
    for e, *_ in ERAS:
        L.append(_row(f"{e}（じわじわ度の区切り {r['eras'][e]['id_cuts']}）", r["eras"][e]["all"]))
    L += ["", "## 問いごとの組（判定の中身・時代ごと）", ""]
    for q, name, sign in QUESTIONS:
        L += [f"### {q} {name}", "", *HEAD]
        for e, *_ in ERAS:
            b = r["questions"][q]["eras"][e]
            L.append(_row(f"{e} 前の組", b["a"]))
            L.append(_row(f"{e} 後の組", b["b"]))
        L += ["", "差（読むだけ）：" + "／".join(
            f"{e} 引けで買う {_p(r['questions'][q]['eras'][e]['close']['diff'])}・20本 {_p(r['questions'][q]['eras'][e]['h20']['diff'])}"
            f"・120本 {_p(r['questions'][q]['eras'][e]['h120']['diff'])}" for e, *_ in ERAS), ""]
    L += ["## 読むための表（判定しない）", ""]
    for e, *_ in ERAS:
        t = r["read"][e]
        L += [f"### {e}", "", "**目安の点数**（6つのうち良いと見込む側に当たる数）", "", *HEAD]
        L += [_row(f"{k}点", v) for k, v in t["score"].items()]
        L += ["", "**その日の売買代金の倍率・移動平均の並び・保ち合いの深さ**", "", *HEAD]
        L += [_row(f"倍率 {k}", v) for k, v in t["tvx"].items()]
        L += [_row(f"25＞75＞200 {k}", v) for k, v in t["align"].items()]
        L += [_row(f"1年以上ぶり・{k}", v) for k, v in t["base_depth"].items()]
        for key in ("vcr", "r2", "tv20"):
            x = t[key]
            L += ["", f"**{x['label']}の3分位**（区切り {x['cuts']}）", "", *HEAD]
            L += [_row(g, x[g]) for g in ("low", "mid", "high")]
        L += ["", "**年ごと**", "", *HEAD] + [_row(y, v) for y, v in t["years"].items()] + [""]
    return "\n".join(L) + "\n"


def rounded(x, nd=6):
    if isinstance(x, float):
        return round(x, nd)
    if isinstance(x, dict):
        return {k: rounded(v, nd) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [rounded(v, nd) for v in x]
    return x


def verdicts_of(res, today):
    """✕ の問いだけ検証済みリストへ（status stop）。✅・△ は前向き（J48F）で確かめるまで載せない"""
    out = {}
    for q, name, sign in QUESTIONS:
        x = res["questions"][q]
        if not x["verdict"].startswith("✕"):
            continue
        pb = x["pooled"]
        out[q] = {"status": "stop", "decided_on": today, "n": pb["n_a"] + pb["n_b"], "mean": pb["diff"], "lo": pb["lo"], "hi": pb["hi"],
                  "reason": ("過去のデータで1回だけ数えて、3つの時代（2006〜2016年・2016〜2023年・2023〜2026年）で予想の向きにそろわなかった"
                             "（数字は上場来高値の次の日の寄りで買い60営業日持った、全体と比べた差の組の差・3つの時代を合わせたもの）")}
    return out


def main(argv):
    res = {"generated_at": dt.datetime.now(P.JST).isoformat(timespec="minutes"), "prereg_file": P.PREREG,
           "prereg_sha256": P.prereg_sha256()}
    try:
        stocks, list_date = jp_bars.load_universe()
        codes = sorted(stocks)
        fetch = jp_bars.fetcher()
        store = jp_bars.info()
        fb = store_fallback()
        series, missing, cal = load_series(codes, fetch, fb)
        cases = collect(series, cal)
        if "--check" in argv:
            print(json.dumps(rounded(check_summary(cases, series, len(codes), missing, len(fb), store)), ensure_ascii=False, indent=1))
            return 0
        if not store or store.get("daily_range") != jp_bars.FULL_DAILY:
            raise RuntimeError("値段の置き場の日足が全期間版ではない（先に jp-bars-cache を回す）")
        if missing > 0.05 * len(codes):
            raise RuntimeError("日足を取れなかった銘柄が5％超。偏った組で数えない（取り直す）")
        out = analyze(cases)
        res["price_store"] = store
        res["result"] = dict(out, n_codes=len(codes), list_date=list_date, n_missing=missing, n_fallback_skipped=len(fb))
        today = dt.datetime.now(P.JST).date().isoformat()
        res.update(kind="backtest",
                   titles={q: f"上場来高値の形・{name}（次の日の寄りで買い60営業日・全体と比べた差・2006〜2026-07・1回だけ数えた）"
                           for q, name, _ in QUESTIONS},
                   verdicts=verdicts_of(out, today),
                   progress={q: out["questions"][q]["pooled"]["n_a"] + out["questions"][q]["pooled"]["n_b"] for q, *_ in QUESTIONS})
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
