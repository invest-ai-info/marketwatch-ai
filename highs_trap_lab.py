# -*- coding: utf-8 -*-
"""J10 高値更新の翌朝、寄りで買うと負ける「罠」を、寄りの時点までにわかることで見分けられるか
（2026-10-06 オーナー「進めてください。これで罠銘柄が見分けられるかどうかを分析してください」）。

⚠️ 決まりは PILLAR_PREREG.md「J10」と下の定数に固定。結果を見てから動かさない。
⚠️ 出力（highs-trap-lab.json / highs-trap-lab.md）は集計だけ。銘柄名・コードは出さない。GitHub 側で生成＝手元から送らない（SYNC禁忌）。
⚠️ 高値更新の決め方は build_jp_highs.py と同じ（window_start・sane_today・MIN_PRIOR_BARS・同じ値は更新に数えない）。
   約3年分を日ごとに決め直すので、前もって計算する形（ytd_flags）にした。build_jp_highs.ytd_extreme と同じ答えになることは
   tests/test_highs_trap_lab.py が作り物の値動きで突き合わせて確かめる。
⚠️ 値の取り方は yori_lab.py と同じ（寄り＝日足の始値・9:30＝9:25 の5分足の終値＝price_at）。

実行: python highs_trap_lab.py          （本番。Actions の highs-trap-lab.yml から手動で・1回だけ）
      python highs_trap_lab.py --diag   （データの形と件数だけ。値動きは出さない・何も書き出さない）
"""
import bisect
import datetime as dt
import json
import sys
import time

import numpy as np

import build_jp_highs as H
import pillar_lab as P
import yori_lab as Y

UNIVERSE = "jp-stock-info.json"
OUT_JSON, OUT_MD = "highs-trap-lab.json", "highs-trap-lab.md"
END_DAY = "2026-10-05"        # 翌朝がこの日までの分だけ（10/6 は仮説を作るのに使った）
GAP_UP = 0.01                 # Q1 窓が +1％ 以上
WICK = 0.5                    # Q3 前の日の（高値−終値）÷（高値−安値）が 0.5 以上
PREV_BIG = 0.05               # Q4 前の日に +5％ 以上上げた
COST = 0.001                  # 往復 0.1％
TRAP = -0.01                  # 読むための「罠の割合」＝寄りからの値動きが −1％ 以下（費用前）
MAX_MOVE = 0.25               # 寄りからの値動きが ±25％ を超えたらデータの誤り
N_Q = 5                       # 判定の数（Q0〜Q4）
ALPHA = 0.05 / N_Q            # 99％ の幅
N_BOOT = 10000
MIN_N = 30
MAX_MISSING = 0.05            # 日足か1時間足を取れなかった銘柄がユニバースのこれを超えたら判定しない
DAILY_RANGE = "3y"
H1_RANGES = ("729d", "1y")    # 1時間足は Yahoo が約2年（730日）まで
M5_RANGES = ("60d", "1mo")    # 5分足は約60日まで

FLAGS = [
    ("q1", "Q1 窓が +1％ 以上", lambda r: r["gap"] >= GAP_UP),
    ("q2", "Q2 寄りが前の日の高値より上", lambda r: r["above_high"]),
    ("q3", "Q3 前の日の上ヒゲが長い", lambda r: r["wick"] >= WICK),
    ("q4", "Q4 前の日に +5％ 以上上げた", lambda r: r["prev_ret"] is not None and r["prev_ret"] >= PREV_BIG),
]


# ════════════════════ 高値更新・値の取り方 ════════════════════

def ytd_flags(bars):
    """bars＝[(日付, 高値, 安値, 終値, 出来高)]（日付順）→ 各日に年初来高値（1〜3月は昨年来高値）を更新したか。

    build_jp_highs.ytd_extreme(bars[:k+1], window_start(その日)) が None でないのと同じ答え（テストで突き合わせる）。
    期間の始まりは年に1〜2回しか変わらないので、始まりごとに累積の最高値を1回だけ作る。"""
    n = len(bars)
    dates = [b[0] for b in bars]
    highs = [b[1] for b in bars]
    out = [False] * n
    runmax = {}
    for k in range(1, n):
        s = bisect.bisect_left(dates, H.window_start(dates[k])[0])
        if k - s < H.MIN_PRIOR_BARS or not H.sane_today(bars[k - 1:k + 1]):
            continue
        if s not in runmax:
            acc, m = [], -float("inf")
            for h in highs[s:]:
                m = max(m, h)
                acc.append(m)
            runmax[s] = acc
        out[k] = highs[k] > runmax[s][k - 1 - s]
    return out


def price_1000(bars):
    """その日の1時間足 → (10:00 の値, 代えたか)。9:00 から始まる足の終値。無ければ 10:00 から始まる足の始値。"""
    by = {(t.hour, t.minute): (o, c) for t, o, h, l, c, v in bars}
    if (9, 0) in by:
        return by[(9, 0)][1], False
    if (10, 0) in by:
        return by[(10, 0)][0], True
    return None, None


def yoriten(bars5, op):
    """寄り値が 9:00〜9:30 の高値だったか（5分足の 9:00 の足がある日だけ。無ければ None）"""
    if not bars5 or (bars5[0][0].hour, bars5[0][0].minute) != (9, 0):
        return None
    hi = max(b[2] for b in bars5 if (b[0].hour, b[0].minute) < (9, 30))
    return op >= hi * (1 - 1e-9)


def outcomes(op, close, bars5, bars1h, drops=None):
    """寄りからの値動き（費用前）。9:30 も 10:00 も無ければ None。±25％ 超はデータの誤りとして捨てる。"""
    def r(x):
        if not x:
            return None
        v = x / op - 1
        if abs(v) > MAX_MOVE:
            if drops is not None:
                drops["n"] += 1
            return None
        return v

    o = {"r915": None, "r930": None, "r1000": None, "rclose": r(close), "fb": None, "yoriten": None}
    if bars5:
        b = sorted(bars5)
        o["r915"], o["r930"] = r(Y.price_at(b, "09:15")), r(Y.price_at(b, "09:30"))
        o["yoriten"] = yoriten(b, op)
    if bars1h:
        p, fb = price_1000(sorted(bars1h))
        o["r1000"] = r(p)
        o["fb"] = fb if o["r1000"] is not None else None
    if o["r930"] is None and o["r1000"] is None:
        return None
    return o


def stock_records(code, daily, m5, h1, akaji=None, end_day=END_DAY, drops=None):
    """1銘柄 → (高値更新の翌朝の記録, 比べる相手の記録)。
    daily＝[(日付, 始, 高, 安, 終, 出来高)]（日付順）、m5／h1＝{日付: [(時刻, 始, 高, 安, 終, 出来高)…]}"""
    flags = ytd_flags([(d, h, lo, c, v) for d, o, h, lo, c, v in daily])
    ev, ctl = [], []
    for k in range(1, len(daily) - 1):
        day, op, close = daily[k + 1][0], daily[k + 1][1], daily[k + 1][4]
        if day > end_day:
            break
        if not op or op <= 0:
            continue
        out = outcomes(op, close, m5.get(day), h1.get(day), drops)
        if out is None:
            continue
        rec = dict(out, date=day, code=code)
        if flags[k]:
            _, _, h0, l0, c0, _ = daily[k]
            pc = daily[k - 1][4]
            rec.update(gap=op / c0 - 1, above_high=op > h0, wick=(h0 - c0) / (h0 - l0) if h0 > l0 else 0.0,
                       prev_ret=c0 / pc - 1 if pc else None, akaji=akaji)
            ev.append(rec)
        else:
            ctl.append({x: rec[x] for x in ("date", "code", "r915", "r930", "r1000", "rclose", "yoriten")})
    return ev, ctl


# ════════════════════ 数える ════════════════════

def boot(vals, keys, flags=None, alpha=ALPHA, n_boot=N_BOOT, seed=P.SEED):
    """まとまり（keys）ごとに引き直した、平均（flags があれば 目印あり − なし の差）の点と幅 (点, 下, 上)。
    まとまりが5未満なら幅は出さない。"""
    v = np.asarray(vals, float)
    uk = {k: i for i, k in enumerate(sorted(set(keys)))}
    C = len(uk)
    ci = np.fromiter((uk[k] for k in keys), int, len(keys))

    def parts(mask):
        return (np.bincount(ci, weights=np.where(mask, v, 0.0), minlength=C),
                np.bincount(ci, weights=mask.astype(float), minlength=C))

    if flags is None:
        sa, na = parts(np.ones(len(v), bool))
        sb = nb = None
    else:
        f = np.asarray(flags, bool)
        sa, na = parts(f)
        sb, nb = parts(~f)

    def stat(SA, NA, SB, NB):
        with np.errstate(invalid="ignore", divide="ignore"):
            m = SA / NA
            return m if SB is None else m - SB / NB

    point = float(stat(sa.sum(), na.sum(), None if sb is None else sb.sum(), None if nb is None else nb.sum()))
    if not np.isfinite(point):
        return None, None, None
    if C < 5:
        return point, None, None
    rng = np.random.default_rng(seed)
    sims = []
    for start in range(0, n_boot, 500):
        m = min(500, n_boot - start)
        d = rng.integers(0, C, size=(m, C))
        sims.append(stat(sa[d].sum(1), na[d].sum(1), None if sb is None else sb[d].sum(1), None if nb is None else nb[d].sum(1)))
    s = np.concatenate(sims)
    s = s[np.isfinite(s)]
    lo, hi = np.percentile(s, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return point, float(lo), float(hi)


def safe(rows, f, flag=None):
    """日で引き直した幅と銘柄で引き直した幅の、広いほう（安全側）"""
    xs = [(f(r), r) for r in rows]
    xs = [(v, r) for v, r in xs if v is not None]
    key = "mean" if flag is None else "diff"
    out = {"n": len(xs), key: None, "lo": None, "hi": None}
    if not xs:
        return out
    vals = [v for v, _ in xs]
    fl = None
    if flag is not None:
        fl = [bool(flag(r)) for _, r in xs]
        out.update(n_a=sum(fl), n_b=len(fl) - sum(fl))
        if out["n_a"] == 0 or out["n_b"] == 0:
            return out
    pt, lo_d, hi_d = boot(vals, [r["date"] for _, r in xs], fl)
    _, lo_c, hi_c = boot(vals, [r["code"] for _, r in xs], fl)
    out.update({key: pt, "by_day": [lo_d, hi_d], "by_stock": [lo_c, hi_c]})
    if None not in (lo_d, lo_c, hi_d, hi_c):
        out.update(lo=min(lo_d, lo_c), hi=max(hi_d, hi_c))
    return out


def mean_of(rows, f):
    xs = [x for x in (f(r) for r in rows) if x is not None]
    return {"n": len(xs), "mean": float(np.mean(xs)) if xs else None}


def diff_of(rows, f, flag):
    a = [x for x in (f(r) for r in rows if flag(r)) if x is not None]
    b = [x for x in (f(r) for r in rows if not flag(r)) if x is not None]
    return {"n_a": len(a), "n_b": len(b), "diff": float(np.mean(a) - np.mean(b)) if a and b else None,
            "mean_a": float(np.mean(a)) if a else None, "mean_b": float(np.mean(b)) if b else None}


def _side(x, sign):
    return x is not None and x * sign > 0


def check60(n, x, sign):
    """5分足（約60日・寄り→9:30）が同じ向きか"""
    if n < MIN_N or x is None:
        return "件数不足"
    return "同じ向き" if x * sign > 0 else "逆向き"


def _verdict(base, c60):
    if c60 == "同じ向き":
        return base
    if c60 == "件数不足":
        return base + "（10:00 では兆し・9:30 は件数不足で確かめられず）"
    return "10:00 だけの兆し（9:30 では逆向き＝オーナーの取引時間では使えない）：" + base


def judge_q0(full, early, late, m60):
    if full.get("lo") is None:
        return "件数不足"
    for sign, base in ((-1, "高値更新の翌朝の寄り買いは、平均で負けやすい兆し"), (+1, "高値更新の翌朝の寄り買いは、平均で勝ちやすい兆し")):
        whole = full["hi"] < 0 if sign < 0 else full["lo"] > 0
        if whole and _side(early.get("mean"), sign) and _side(late.get("mean"), sign):
            return _verdict(base, check60(m60.get("n", 0), m60.get("mean"), sign))
    return "見えない"


def judge_flag(full, early, late, mean_a_cost, d60):
    if full.get("n_a", 0) < MIN_N or full.get("n_b", 0) < MIN_N or full.get("lo") is None:
        return "件数不足"
    for sign, base in ((-1, "罠の目印（入らない方がいい兆し）"), (+1, "強さの目印（兆し）")):
        whole = full["hi"] < 0 if sign < 0 else full["lo"] > 0
        if whole and _side(early.get("diff"), sign) and _side(late.get("diff"), sign) and _side(mean_a_cost, sign):
            return _verdict(base, check60(d60.get("n_a", 0), d60.get("diff"), sign))
    return "見えない"


def _cost(key):
    return lambda r: None if r.get(key) is None else r[key] - COST


def _share(rows, key):
    """罠の割合（寄りからの値動きが −1％ 以下）"""
    xs = [r[key] for r in rows if r.get(key) is not None]
    return {"n": len(xs), "mean": (sum(1 for x in xs if x <= TRAP) / len(xs)) if len(xs) >= Y.MIN_CELL else None}


def analyze(ev, ctl):
    e2 = [r for r in ev if r["r1000"] is not None]
    e60 = [r for r in ev if r["r930"] is not None]
    days = sorted({r["date"] for r in e2})
    cut = days[len(days) // 2] if days else ""
    early, late = [r for r in e2 if r["date"] < cut], [r for r in e2 if r["date"] >= cut]
    days60 = sorted({r["date"] for r in e60})
    res = {"n_2y": len(e2), "days_2y": len(days), "first": days[0] if days else None, "last": days[-1] if days else None,
           "cut": cut, "n_60d": len(e60), "days_60d": len(days60), "first_60d": days60[0] if days60 else None,
           "last_60d": days60[-1] if days60 else None, "n_fallback_1000": sum(1 for r in e2 if r["fb"]),
           "n_ctl_2y": sum(1 for r in ctl if r["r1000"] is not None), "n_ctl_60d": sum(1 for r in ctl if r["r930"] is not None),
           "by_year": {y: sum(1 for r in e2 if r["date"][:4] == y) for y in sorted({r["date"][:4] for r in e2})}}
    f10, f930 = (lambda r: r["r1000"]), (lambda r: r["r930"])
    f10c, f930c = _cost("r1000"), _cost("r930")
    q0 = {"all": safe(e2, f10c), "early": mean_of(early, f10c), "late": mean_of(late, f10c), "m60": mean_of(e60, f930c)}
    q0["verdict"] = judge_q0(q0["all"], q0["early"], q0["late"], q0["m60"])
    res["q0"] = q0
    for key, name, flag in FLAGS:
        full = safe(e2, f10, flag)
        q = {"name": name, "all": full, "early": diff_of(early, f10, flag), "late": diff_of(late, f10, flag),
             "mean_a_cost": mean_of([r for r in e2 if flag(r)], f10c), "mean_b_cost": mean_of([r for r in e2 if not flag(r)], f10c),
             "d60": diff_of(e60, f930, flag)}
        q["verdict"] = judge_flag(full, q["early"], q["late"], q["mean_a_cost"]["mean"], q["d60"])
        res[key] = q
    # ── 読むための表（判定しない）──
    res["paths"] = {name: {k: mean_of(rows, lambda r, k=k: r[k]) for k in ("r915", "r930", "r1000", "rclose")}
                    for name, rows in (("高値更新の翌朝", ev), ("比べる相手", ctl))}
    groups = [("すべて", lambda r: True)]
    for _, name, flag in FLAGS:
        groups += [(name + "：あり", flag), (name + "：なし", lambda r, flag=flag: not flag(r))]
    groups += [("窓 " + b, lambda r, b=b: Y.gap_band(r["gap"]) == b) for b in ("−1％未満", "−1〜+1％", "+1〜+3％", "+3％以上")]
    groups += [("前の日 " + b, lambda r, b=b: Y.prev_band(r["prev_ret"]) == b) for b in ("−5％以下", "−5〜+5％", "+5％以上")]
    groups += [("赤字", lambda r: bool(r.get("akaji"))), ("黒字", lambda r: not r.get("akaji"))]
    res["trap_share"] = [{"label": lab, "2y_1000": _share([r for r in e2 if g(r)], "r1000"),
                          "60d_930": _share([r for r in e60 if g(r)], "r930")} for lab, g in groups]
    res["trap_share_ctl"] = {"2y_1000": _share(ctl, "r1000"), "60d_930": _share(ctl, "r930")}
    yt = [r["yoriten"] for r in ev if r["yoriten"] is not None]
    yc = [r["yoriten"] for r in ctl if r["yoriten"] is not None]
    res["yoriten"] = {"n": len(yt), "share": (sum(yt) / len(yt)) if len(yt) >= Y.MIN_CELL else None,
                      "n_ctl": len(yc), "share_ctl": (sum(yc) / len(yc)) if len(yc) >= Y.MIN_CELL else None}
    return res


# ════════════════════ 実行 ════════════════════

def _first(fetch, code, interval, ranges):
    for rg in ranges:
        x = fetch(code, interval, rg)
        if x:
            return x
    return None


def _by_day(bars):
    by = {}
    for b in bars or []:
        by.setdefault(b[0].date().isoformat(), []).append(b)
    return by


def load(codes, meta, fetch=Y.fetch_chart, end_day=END_DAY):
    ev, ctl = [], []
    missing = {"daily": [], "h1": [], "m5": []}
    shape = {"h1_first_day": [], "h1_times": {}, "m5_first_time": {}}
    drops = {"n": 0}
    for i, code in enumerate(codes):
        d = fetch(code, "1d", DAILY_RANGE)
        h1 = _first(fetch, code, "60m", H1_RANGES)
        m5 = _first(fetch, code, "5m", M5_RANGES)
        if not d:
            missing["daily"].append(code)
            continue
        if not h1:
            missing["h1"].append(code)
        if not m5:
            missing["m5"].append(code)
        daily = sorted({t.date().isoformat(): (t.date().isoformat(), o, h, lo, c, v) for t, o, h, lo, c, v in d}.values())
        by5, by1 = _by_day(m5), _by_day(h1)
        if by1:
            shape["h1_first_day"].append(min(by1))
        for bars in by1.values():
            for t, *_ in bars:
                k = t.strftime("%H:%M")
                shape["h1_times"][k] = shape["h1_times"].get(k, 0) + 1
        for bars in by5.values():
            k = min(bars)[0].strftime("%H:%M")
            shape["m5_first_time"][k] = shape["m5_first_time"].get(k, 0) + 1
        e, c = stock_records(code, daily, by5, by1, akaji=meta.get(code, {}).get("akaji"), end_day=end_day, drops=drops)
        ev += e
        ctl += c
        if (i + 1) % 50 == 0:
            print(f"  ...{i + 1}/{len(codes)}", flush=True)
        time.sleep(0.05)
    return ev, ctl, missing, shape, drops


def diag_summary(ev, ctl, missing, shape, n_universe):
    """件数とデータの形だけ（値動きは出さない）"""
    e2 = [r for r in ev if r["r1000"] is not None]
    e60 = [r for r in ev if r["r930"] is not None]
    fd = sorted(shape["h1_first_day"])
    out = {"n_universe": n_universe, "missing": {k: len(v) for k, v in missing.items()},
           "h1_first_day": {"min": fd[0], "median": fd[len(fd) // 2], "max": fd[-1]} if fd else {},
           "h1_bar_start_times_top": dict(sorted(shape["h1_times"].items(), key=lambda kv: -kv[1])[:10]),
           "m5_first_bar_time_top": dict(sorted(shape["m5_first_time"].items(), key=lambda kv: -kv[1])[:6]),
           "events": {"n_2y": len(e2), "n_60d": len(e60), "days_2y": len({r["date"] for r in e2}),
                      "days_60d": len({r["date"] for r in e60}), "first": min((r["date"] for r in e2), default=None),
                      "last": max((r["date"] for r in e2), default=None),
                      "n_fallback_1000": sum(1 for r in e2 if r["fb"]),
                      "n_60d_with_900_bar": sum(1 for r in e60 if r["yoriten"] is not None),
                      "by_year": {y: sum(1 for r in e2 if r["date"][:4] == y) for y in sorted({r["date"][:4] for r in e2})}},
           "flag_sizes": {name: {"2y": sum(1 for r in e2 if f(r)), "60d": sum(1 for r in e60 if f(r))} for _, name, f in FLAGS},
           "n_ctl": {"2y": sum(1 for r in ctl if r["r1000"] is not None), "60d": sum(1 for r in ctl if r["r930"] is not None)}}
    return out


def _pct(x, d=2):
    return Y._pct(x, d)


def _share_txt(s):
    return f"{s['mean'] * 100:.1f}％（{s['n']}）" if s.get("mean") is not None else f"—（{s.get('n', 0)}）"


def render_md(res):
    L = ["# J10 高値更新の翌朝、寄りで買うと負ける「罠」を見分けられるか", "",
         f"作成: {res['generated_at']}（GitHub Actions で計算）。事前登録＝`{P.PREREG}`「J10」（指紋 sha256 `{(res.get('prereg_sha256') or '')[:16]}…`）。",
         "銘柄名は出しません。値は株価の変化率（％）。**売買の決まりではない**。", ""]
    r = res.get("result") or {}
    if r.get("error"):
        return "\n".join(L + [f"- ⚠️ 計算できず: {r['error']}", ""]) + "\n"
    L += [f"- 1時間足（判定の主・寄り→10:00）：{r['first']}〜{r['last']}・{r['days_2y']}営業日・{r['n_2y']}件（前半と後半の境 {r['cut']}）。"
          f"年ごと {r['by_year']}。10:00 の値を「10:00 から始まる足の始値」で代えた件数 {r['n_fallback_1000']}",
          f"- 5分足（オーナーの取引時間・寄り→9:30）：{r['first_60d']}〜{r['last_60d']}・{r['days_60d']}営業日・{r['n_60d']}件",
          f"- 比べる相手（前の日に高値を更新していない銘柄）：1時間足 {r['n_ctl_2y']}件・5分足 {r['n_ctl_60d']}件",
          f"- ユニバース {r.get('n_universe')}銘柄・取れなかった銘柄 {r.get('n_missing')}・±25％超で捨てた値 {r.get('n_dropped')}",
          f"- 翌朝が {END_DAY} までの日だけ（10/6 は仮説を作るのに使ったので外した）。幅は99％（p＜0.05÷5）・日と銘柄で引き直した広いほう",
          "", "## 判定（事前登録の5つ）", ""]
    q0 = r["q0"]
    a = q0["all"]
    L += [f"- **Q0 そもそも（寄りで買い 10:00 に手仕舞う・費用後）**：平均 {_pct(a.get('mean'))}（幅 {_pct(a.get('lo'))}〜{_pct(a.get('hi'))}・{a.get('n', 0)}件）"
          f"・前半 {_pct(q0['early'].get('mean'))}／後半 {_pct(q0['late'].get('mean'))}・5分足の寄り→9:30（費用後）{_pct(q0['m60'].get('mean'))}（{q0['m60'].get('n', 0)}件）"
          f" → **{q0['verdict']}**"]
    for key, _, _ in FLAGS:
        q = r[key]
        d = q["all"]
        L += [f"- **{q['name']}**：目印あり−なし（寄り→10:00）の差 {_pct(d.get('diff'))}（幅 {_pct(d.get('lo'))}〜{_pct(d.get('hi'))}・"
              f"{d.get('n_a', 0)}件 対 {d.get('n_b', 0)}件）・前半 {_pct(q['early'].get('diff'))}／後半 {_pct(q['late'].get('diff'))}・"
              f"目印ありの平均（費用後）{_pct(q['mean_a_cost'].get('mean'))}／なし {_pct(q['mean_b_cost'].get('mean'))}・"
              f"5分足の寄り→9:30 の差 {_pct(q['d60'].get('diff'))}（{q['d60'].get('n_a', 0)}件 対 {q['d60'].get('n_b', 0)}件） → **{q['verdict']}**"]
    L += ["", "## 読むための表（判定しない）", "", "### 寄りで買った場合の平均（費用なし）", "",
          "| | 寄り→9:15 | 寄り→9:30 | 寄り→10:00 | 寄り→大引け |", "|---|---:|---:|---:|---:|"]
    for name, p in r["paths"].items():
        L.append(f"| {name} | " + " | ".join(f"{_pct(p[k].get('mean'))}（{p[k].get('n', 0)}）" for k in ("r915", "r930", "r1000", "rclose")) + " |")
    L += ["", "### 罠の割合（寄りからの値動きが −1％ 以下・費用前）", "",
          "| | 寄り→10:00（1時間足） | 寄り→9:30（5分足） |", "|---|---:|---:|"]
    for row in r["trap_share"]:
        L.append(f"| {row['label']} | {_share_txt(row['2y_1000'])} | {_share_txt(row['60d_930'])} |")
    c = r["trap_share_ctl"]
    L.append(f"| 比べる相手 | {_share_txt(c['2y_1000'])} | {_share_txt(c['60d_930'])} |")
    y = r["yoriten"]
    yt = _share_txt({"mean": y["share"], "n": y["n"]})
    yc = _share_txt({"mean": y["share_ctl"], "n": y["n_ctl"]})
    L += ["", f"- 寄り天の割合（寄り値が 9:00〜9:30 の高値・5分足の 9:00 の足がある日だけ）：高値更新の翌朝 {yt}／比べる相手 {yc}",
          f"- 30件未満の区分は「—」。費用＝往復{COST * 100:.1f}％（判定の Q0 と「目印ありの平均」だけ差し引く）。空売りは数えない。",
          "- ユニバースは今の流動性上位400銘柄＝2年前には入っていなかった銘柄も含む。実際の約定（寄りの成行・10:00／9:30 の値）とはずれる。",
          "", "---", "", "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。"]
    return "\n".join(L) + "\n"


def main_diag():
    info = json.load(open(UNIVERSE, encoding="utf-8"))["stocks"]
    ev, ctl, missing, shape, _ = load(list(info), info)
    print(json.dumps(diag_summary(ev, ctl, missing, shape, len(info)), ensure_ascii=False, indent=1))
    return 0


def main():
    res = {"generated_at": dt.datetime.now(P.JST).isoformat(timespec="minutes"), "prereg_file": P.PREREG,
           "prereg_sha256": P.prereg_sha256(), "end_day": END_DAY}
    try:
        info = json.load(open(UNIVERSE, encoding="utf-8"))["stocks"]
        codes = list(info)
        ev, ctl, missing, shape, drops = load(codes, info)
        bad = set(missing["daily"]) | set(missing["h1"])
        if len(bad) > MAX_MISSING * len(codes):
            raise RuntimeError(f"日足か1時間足を取れなかった銘柄が {len(bad)}/{len(codes)}＝5％超。偏った組で判定しない（取り直す）")
        res["result"] = dict(analyze(ev, ctl), n_universe=len(codes), n_missing={k: len(v) for k, v in missing.items()},
                             n_dropped=drops["n"])
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
    sys.exit(main_diag() if "--diag" in sys.argv else main())
