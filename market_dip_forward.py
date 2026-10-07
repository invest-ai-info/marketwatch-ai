# -*- coding: utf-8 -*-
"""J25F 相場全体が安く寄った朝の深い下げ・前向き（2026-10-07 登録・オーナー「一二を登録して続けてください」）。PILLAR_PREREG.md「J25」。

**2026-10-08 以降の朝だけ**で、寄り→9:30（5分足）を数える。相場全体が安く寄った朝＝その朝の全銘柄の窓の中央値が −0.5％ 以下
（数えた銘柄が500未満の朝は数えない）。前日比 −5・−8・−10％ に買いの指値（付き方は J23 と同じ）→ 9:30 に売る・費用は J24 の新しい見積もり。
相場全体が安く寄った朝が30朝に届いた日に1回だけ判定（深さごとに Q1 費用後 ＞ 0 と Q2 安く寄った朝 − それ以外 ＞ 0・99.17％ の幅）。

⚠️ 決まりは PILLAR_PREREG.md「J25」と下の定数に固定。途中の数字を見て動かさない。幅は gap_forward（J13F）の _boot_agg をそのまま使う。
⚠️ 1行ずつの取引は持たない。朝ごと・組ごとの合計と、銘柄ごと（伏せた印）・組ごとの合計だけ。
⚠️ 出力（market-dip-forward.json / .md）は GitHub 側で生成＝手元から送らない（SYNC禁忌）。積み上げた判定を持つ＝古い版で上書きしない。

実行: python market_dip_forward.py          （Actions の market-dip-forward.yml から平日に）
"""
import datetime as dt
import hashlib
import json
import sys
import time

import numpy as np

import bounce_cost_lab as BC
import build_jp_highs as H
import cost_recount_lab as CR
import dip_lab as D
import gap_forward as GF
import gap_lab as GL
import highs_trap_lab as T
import pillar_lab as P
import yori_lab as Y

STATE, OUT_MD = "market-dip-forward.json", "market-dip-forward.md"
FWD_START = "2026-10-08"
GOAL_DOWN_DAYS = 30
LEVELS = (0.05, 0.08, 0.10)
MKT_DOWN = -0.005
MIN_STOCKS = 500
N_Q = 2 * len(LEVELS)
ALPHA = 0.05 / N_Q            # 99.17％ の幅
MIN_N = 30
DAILY_RANGE = "6mo"           # 費用の見積もりに、その朝より前の60営業日が要る
KEYS = tuple(f"X{int(round(x * 100))}" for x in LEVELS)
TITLES = {k: f"相場全体が安く寄った朝（全銘柄の窓の中央値 −0.5％以下）に、前日比 −{k[1:]}％ に指値で拾い 9:30 に売る（費用後）" for k in KEYS}


def empty_state():
    return {"registered": "J25F", "kind": "forward", "fwd_start": FWD_START, "goal_down_days": GOAL_DOWN_DAYS, "unit": "pct",
            "titles": TITLES, "verdicts": {}, "days": {}, "stocks": {}, "skipped": {}, "runs": []}


def load_state(path=STATE):
    try:
        with open(path, encoding="utf-8") as fh:
            st = json.load(fh)
    except FileNotFoundError:
        return empty_state()
    if st.get("fwd_start") != FWD_START or st.get("goal_down_days") != GOAL_DOWN_DAYS:
        raise SystemExit(f"🚨 {path} の開始日・判定の朝の数が登録と違う＝上書きしない")
    return st


def tag(code):
    """銘柄コードを伏せた印（同じ銘柄は同じ印・コードには戻せない）"""
    return hashlib.sha1(("j25f:" + str(code)).encode()).hexdigest()[:10]


# ════════════════════ 1銘柄の朝 ════════════════════

def _days_apart(a, b):
    return (dt.date.fromisoformat(b) - dt.date.fromisoformat(a)).days


def limit_net(op_r, lo_r, ex_r, spread, x):
    """前日比 −x の指値（J23 と同じ付き方）→ 費用後の値動き。付かなければ None"""
    lim = 1 - x
    if op_r <= lim:
        entry = op_r
    elif lo_r <= lim * (1 - D.THROUGH):
        entry = lim
    else:
        return None
    return ex_r / entry - 1 - float(BC.cost(spread))


def stock_mornings(daily, m5, days, drops=None):
    """→ {日付: (窓, 深さごとの費用後〔付かない・数えられないは None〕 または None)}。
    窓は日足だけで決める（相場全体の中央値に使う）。値動きは 5分足の寄り→9:30 と窓の安値・費用の見積もりがそろった朝だけ"""
    out = {}
    bars = [(d, h, lo, c, v) for d, o, h, lo, c, v in daily]
    sp = CR.ar_spread_avg(daily)
    for k in range(1, len(daily) - 1):
        dp, d0, d1 = daily[k - 1], daily[k], daily[k + 1]
        day = d1[0]
        if day not in days:
            continue
        op, high, low, close, pc, ppc = d1[1], d1[2], d1[3], d1[4], d0[4], dp[4]
        if not op or op <= 0 or not pc or pc <= 0 or not ppc or ppc <= 0:
            continue
        if _days_apart(d0[0], day) > GL.MAX_GAP_DAYS or _days_apart(dp[0], d0[0]) > GL.MAX_GAP_DAYS:
            continue
        if not H.sane_today(bars[k:k + 2]) or not H.sane_today(bars[k - 1:k + 1]) or not (low * (1 - 1e-9) <= op <= high * (1 + 1e-9)):
            continue
        nets = None
        o = T.outcomes(op, close, m5.get(day), None, drops)
        lo5, _ = D.window_5m(m5.get(day), op)
        lo5 = D._ok_low(lo5, op)
        s = sp.get(day)
        if o is not None and o["r930"] is not None and np.isfinite(lo5) and s is not None:
            ex_r = op * (1 + o["r930"]) / pc
            nets = tuple(limit_net(op / pc, lo5 / pc, ex_r, s, x) for x in LEVELS)
        out[day] = (op / pc - 1, nets)
    return out


# ════════════════════ 合計を足す ════════════════════

def add_day(st, day, rows):
    """rows＝[(印, 窓, 深さごとの費用後 または None)]。数えた銘柄が MIN_STOCKS 未満なら足さない（False）"""
    if len(rows) < MIN_STOCKS:
        st.setdefault("skipped", {})[day] = len(rows)
        return False
    med = float(np.median([gap for _, gap, _ in rows]))
    grp = "down" if med <= MKT_DOWN else "other"
    g = {f"{grp}_{k}": [0, 0.0] for k in KEYS}
    for sid, _, nets in rows:
        if nets is None:
            continue
        for k, v in zip(KEYS, nets):
            if v is None:
                continue
            key = f"{grp}_{k}"
            g[key][0] += 1
            g[key][1] += v
            c = st["stocks"].setdefault(sid, {}).setdefault(key, [0, 0.0])
            c[0] += 1
            c[1] += v
    st["days"][day] = {"g": g, "median_gap": med, "down": grp == "down", "n": len(rows)}
    st.get("skipped", {}).pop(day, None)
    return True


# ════════════════════ 幅と判定 ════════════════════

def _sums(st, groups, days):
    return ([[st["days"][d]["g"].get(k, [0, 0.0])[1] for d in days] for k in groups],
            [[st["days"][d]["g"].get(k, [0, 0.0])[0] for d in days] for k in groups])


def _stock_sums(st, groups):
    ids = sorted(st["stocks"])
    return ([[st["stocks"][i].get(k, [0, 0.0])[1] for i in ids] for k in groups],
            [[st["stocks"][i].get(k, [0, 0.0])[0] for i in ids] for k in groups])


def _point(st, groups, days, stat):
    Sm, Nm = (np.asarray(x, float) for x in _sums(st, groups, days))
    if Nm.size == 0 or (Nm.sum(1) == 0).any():
        return None
    return float(stat(Sm.sum(1) / Nm.sum(1)))


def down_days(st):
    return sorted(d for d, v in st["days"].items() if v["down"])


def measure(st, k, q):
    """q＝"q1"（安く寄った朝の費用後の平均）／"q2"（安く寄った朝 − それ以外の朝）"""
    if q == "q1":
        groups, days, stat = [f"down_{k}"], down_days(st), (lambda mu: mu[0])
    else:
        groups, days, stat = [f"down_{k}", f"other_{k}"], sorted(st["days"]), GL._diff2
    ns = [sum(st["days"][d]["g"].get(g, [0, 0.0])[0] for d in days) for g in groups]
    out = {"ns": ns, "days": len(days), "mean": None, "lo": None, "hi": None, "early": None, "late": None}
    if not days or min(ns) == 0:
        return out
    pt, lo_d, hi_d = GF._boot_agg(*_sums(st, groups, days), stat, alpha=ALPHA)
    _, lo_s, hi_s = GF._boot_agg(*_stock_sums(st, groups), stat, alpha=ALPHA)
    half = len(days) // 2
    out.update(mean=pt, by_day=[lo_d, hi_d], by_stock=[lo_s, hi_s],
               early=_point(st, groups, days[:half], stat) if half else None, late=_point(st, groups, days[half:], stat))
    if None not in (lo_d, lo_s, hi_d, hi_s):
        out.update(lo=min(lo_d, lo_s), hi=max(hi_d, hi_s))
    return out


def _up(m):
    return (m["lo"] is not None and min(m["ns"]) >= MIN_N and m["lo"] > 0 and (m["early"] or 0) > 0 and (m["late"] or 0) > 0)


def judge(st, k, day):
    q1, q2 = measure(st, k, "q1"), measure(st, k, "q2")
    ok1, ok2 = _up(q1), _up(q2)
    reason = "" if ok1 and ok2 else ("件数不足" if min(q1["ns"]) < MIN_N else
                                    "Q1（費用後 ＞ 0）が確かめられない" if not ok1 else "Q2（安く寄った朝 − それ以外 ＞ 0）が確かめられない")
    return {"status": "plus" if ok1 and ok2 else "stop", "decided_on": day, "n": q1["ns"][0], "days": q1["days"],
            "mean": q1["mean"], "lo": q1["lo"], "hi": q1["hi"], "early": q1["early"], "late": q1["late"],
            "q2": {"mean": q2["mean"], "lo": q2["lo"], "hi": q2["hi"]}, "reason": reason}


def after_day(st, day):
    """1日足したあとに、安く寄った朝が30朝に届いたら深さごとに1回だけ判定する（判定は書き換えない）"""
    if len(down_days(st)) == GOAL_DOWN_DAYS:
        for k in KEYS:
            if k not in st["verdicts"]:
                st["verdicts"][k] = judge(st, k, day)


def done(st):
    return all(k in st["verdicts"] for k in KEYS)


# ════════════════════ 実行 ════════════════════

def run(st, codes, fetch, today):
    """1回分：まだ数えていない朝を数えて足す。→ (足した朝, 取れなかった銘柄数)"""
    dailies, m5s, missing = {}, {}, 0
    for i, code in enumerate(codes):
        d = fetch(code, "1d", DAILY_RANGE)
        m5 = T._first(fetch, code, "5m", T.M5_RANGES)
        if not d or not m5:
            missing += 1
            continue
        dailies[code] = sorted({t.date().isoformat(): (t.date().isoformat(), o, h, lo, c, v) for t, o, h, lo, c, v in d}.values())
        m5s[code] = T._by_day(m5)
        if (i + 1) % 500 == 0:
            print(f"  ...{i + 1}/{len(codes)}", flush=True)
        time.sleep(0.02)
    if missing > T.MAX_MISSING * len(codes):
        print(f"⚠️ 値段を取れなかった銘柄 {missing}/{len(codes)}＝5％超。この回は1日も数えない")
        return [], missing
    new = [d for d in GF.trading_days(dailies, today, start=FWD_START) if d not in st["days"]]
    drops = {"n": 0}
    per = {code: stock_mornings(dailies[code], m5s[code], set(new), drops) for code in dailies}
    added = []
    for day in new:
        if done(st):
            break
        rows = [(tag(code), *per[code][day]) for code in sorted(per) if day in per[code]]
        if add_day(st, day, rows):
            after_day(st, day)
            added.append(day)
    return added, missing


# ════════════════════ 出力 ════════════════════

def summary(st):
    days = sorted(st["days"])
    dd = down_days(st)
    tot = {}
    for grp in ("down", "other"):
        for k in KEYS:
            key = f"{grp}_{k}"
            n = sum(st["days"][d]["g"].get(key, [0, 0.0])[0] for d in days)
            s = sum(st["days"][d]["g"].get(key, [0, 0.0])[1] for d in days)
            tot[key] = {"n": n, "mean": s / n if n else None}
    return {"days": len(days), "down_days": len(dd), "first": days[0] if days else None, "last": days[-1] if days else None,
            "groups": tot}


def render_md(st, now):
    sm = summary(st)
    L = ["# J25F 相場全体が安く寄った朝の深い下げ・前向き", "",
         f"更新: {now}（GitHub Actions）。事前登録＝`{P.PREREG}`「J25」（指紋 sha256 `{(st.get('prereg_sha256') or '')[:16]}…`）。",
         f"数えるのは **{FWD_START} 以降の朝**だけ（一度数えた朝は数え直さない）。値は寄り→9:30 の費用後の変化率（費用＝J24 の見積もり・下限 往復 0.1％）。銘柄名は出しません。**売買の決まりではない**。", "",
         f"- 数えた朝：{sm['days']}営業日（{sm['first'] or '—'}〜{sm['last'] or '—'}）・そのうち相場全体が安く寄った朝 **{sm['down_days']}朝**"
         f"（{GOAL_DOWN_DAYS}朝に届いた日に1回だけ判定・99.17％の幅）", "",
         "| 指値 | 安く寄った朝：回数 | 費用後の平均 | それ以外の朝：回数 | 費用後の平均 |", "|---|---:|---:|---:|---:|"]
    for k in KEYS:
        a, b = sm["groups"][f"down_{k}"], sm["groups"][f"other_{k}"]
        L.append(f"| 前日比 −{k[1:]}％ | {a['n']:,} | {GF._p(a['mean'])} | {b['n']:,} | {GF._p(b['mean'])} |")
    L += ["", "## 深さごとの判定（途中の数字は判定に使わない）", ""]
    for k in KEYS:
        vd = st["verdicts"].get(k)
        if vd:
            res = {"plus": "✅ プラスを確認", "stop": "⏹ ストップ"}[vd["status"]]
            L.append(f"- **{TITLES[k]}**：{res}（{vd['decided_on']}・{vd['n']:,}回）費用後 {GF._p(vd['mean'])}（幅 {GF._p(vd['lo'])}〜{GF._p(vd['hi'])}）"
                     f"・それ以外との差 {GF._p(vd['q2']['mean'])}{('・' + vd['reason']) if vd['reason'] else ''}")
        else:
            L.append(f"- **{TITLES[k]}**：観察中（安く寄った朝 {sm['down_days']}/{GOAL_DOWN_DAYS}朝）")
    if st.get("skipped"):
        L.append(f"- 銘柄が{MIN_STOCKS}未満で数えなかった朝：" + "・".join(f"{d}（{n}）" for d, n in sorted(st["skipped"].items())))
    L += ["", "- ⏹ ストップは検証済みリストへ。空売りは数えない。板の薄い株の安値の約定の数量は分からない。",
          "", "---", "", "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。"]
    return "\n".join(L) + "\n"


def finalize(st):
    """検証済みリスト・研究の地図が読む欄（いまの回数と判定の目安）"""
    sm = summary(st)
    st["progress"] = {k: sm["groups"][f"down_{k}"]["n"] for k in KEYS}
    st["goal"] = f"相場全体が安く寄った朝{GOAL_DOWN_DAYS}朝で判定・いま {sm['down_days']}朝"
    st["summary"] = sm
    return st


def main(argv):
    st = load_state()
    now = dt.datetime.now(P.JST)
    st["prereg_sha256"] = P.prereg_sha256()
    if not done(st):
        stocks, _ = H.load_universe()
        added, missing = run(st, sorted(stocks), Y.fetch_chart, now.date().isoformat())
        st["runs"] = (st.get("runs") or [])[-30:] + [{"at": now.isoformat(timespec="minutes"), "added": added,
                                                       "n_codes": len(stocks), "missing": missing}]
        print(f"足した朝：{added or 'なし'}（取れなかった銘柄 {missing}/{len(stocks)}）")
    finalize(st)
    with open(STATE, "w", encoding="utf-8") as fh:
        json.dump(st, fh, ensure_ascii=False, indent=0, default=str)
        fh.write("\n")
    md = render_md(st, now.isoformat(timespec="minutes"))
    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
