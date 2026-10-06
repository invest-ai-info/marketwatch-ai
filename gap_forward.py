# -*- coding: utf-8 -*-
"""J13F 窓の戻し・前向き（2026-10-06 夜 登録・オーナー「進めてください」）。PILLAR_PREREG.md「J13F」。

J13 で兆しが出た「高く寄った株は戻され、大きく安く寄った株は戻る」を、**2026-10-07 以降の朝だけ**で数える（寄り→9:30・5分足）。
- 腕A（目印）＝高く寄った（窓 +1％ 以上）− ふつう（窓 ±1％ 未満）の差。250営業日で1回だけ判定
- 腕B（買い）＝大きく安く寄った（窓 −3％ 以下）株を寄りで買い 9:30 に手じまう（費用後）。60営業日ごとにマイナスなら止める・250営業日で判定

⚠️ 決まりは PILLAR_PREREG.md「J13F」と下の定数に固定。途中の数字を見て動かさない。
⚠️ 1行ずつの取引は持たない。朝ごと・組ごとの合計と、銘柄ごと・組ごとの合計（銘柄は伏せた印）だけ＝幅はこれだけで引き直せる。
⚠️ その日より前の朝だけを数え、一度数えた朝は数え直さない。値段を取れない銘柄が5％を超えた回は1日も数えない。
⚠️ 出力（gap-forward.json / .md）は GitHub 側で生成＝手元から送らない（SYNC禁忌）。積み上げた判定を持つ＝古い版で上書きしない。

実行: python gap_forward.py          （Actions の gap-forward.yml から平日に）
"""
import datetime as dt
import hashlib
import json
import sys
import time

import numpy as np

import build_jp_highs as H
import gap_lab as GL
import highs_trap_lab as T
import highs_trap_small as S
import pillar_lab as P
import yori_lab as Y

STATE, OUT_MD = "gap-forward.json", "gap-forward.md"
FWD_START = "2026-10-07"
GOAL_DAYS = 250
CHECK_EVERY = 60              # 腕B の途中の見張り（60・120・180・240営業日）
ALPHA = 0.05
N_BOOT = 10000
MIN_N = 30
DAILY_RANGE = "1mo"
GROUPS = ("base", "up1", "up3", "dn1", "dn3")
STOCK_GROUPS = ("base", "up1", "dn3")       # 銘柄で引き直す幅に要る組だけ
TITLES = {"B": "大きく安く寄った（窓 −3％ 以下）株を寄りで買い 9:30 に手じまう（費用後）"}
MARKER_TITLES = {"A": "高く寄った（窓 +1％ 以上）株は 9:30 までに戻されるか（ふつうの朝との差）"}


def empty_state():
    return {"registered": "J13F", "kind": "forward", "fwd_start": FWD_START, "goal_days": GOAL_DAYS, "unit": "pct",
            "titles": TITLES, "verdicts": {}, "marker_titles": MARKER_TITLES, "marker_verdicts": {},
            "days": {}, "stocks": {}, "interim": [], "runs": []}


def load_state(path=STATE):
    try:
        with open(path, encoding="utf-8") as fh:
            st = json.load(fh)
    except FileNotFoundError:
        return empty_state()
    if st.get("fwd_start") != FWD_START or st.get("goal_days") != GOAL_DAYS:
        raise SystemExit(f"🚨 {path} の開始日・判定の日数が登録と違う＝上書きしない")
    return st


def tag(code):
    """銘柄コードを伏せた印（同じ銘柄は同じ印・コードには戻せない）"""
    return hashlib.sha1(("j13f:" + str(code)).encode()).hexdigest()[:10]


def group_of(gap):
    """窓 → 入る組（ふつう・高く・大きく高く・安く・大きく安く。+3％ 以上は高くにも入る）"""
    out = []
    if GL.DN1 < gap < GL.UP1:
        out.append("base")
    if gap >= GL.UP1:
        out.append("up1")
    if gap >= GL.UP3:
        out.append("up3")
    if gap <= GL.DN1:
        out.append("dn1")
    if gap <= GL.DN3:
        out.append("dn3")
    return out


# ════════════════════ 1銘柄の朝 ════════════════════

def stock_mornings(daily, m5, days, drops=None):
    """daily＝[(日付, 始, 高, 安, 終, 出来高)]（日付順）・m5＝{日付: 5分足}・days＝数える朝の集合
    → {日付: (窓, 寄り→9:30, 前の日の売買代金〔億円〕)}。J13 と同じ除外"""
    out = {}
    bars = [(d, h, lo, c, v) for d, o, h, lo, c, v in daily]
    for k in range(len(daily) - 1):
        d0, d1 = daily[k], daily[k + 1]
        day = d1[0]
        if day not in days:
            continue
        op, high, low, close, pc = d1[1], d1[2], d1[3], d1[4], d0[4]
        if not op or op <= 0 or not pc or pc <= 0:
            continue
        if (dt.date.fromisoformat(day) - dt.date.fromisoformat(d0[0])).days > GL.MAX_GAP_DAYS:
            continue
        if not H.sane_today(bars[k:k + 2]) or not (low * (1 - 1e-9) <= op <= high * (1 + 1e-9)):
            continue
        o = T.outcomes(op, close, m5.get(day), None, drops)
        if o is None or o["r930"] is None:
            continue
        out[day] = (op / pc - 1, o["r930"], pc * d0[5] / 1e8)
    return out


# ════════════════════ 合計を足す ════════════════════

def _band(turnover):
    return next(lab for lab, a, b in S.TURNOVER_BANDS if a <= turnover < b)


def add_day(st, day, rows):
    """rows＝[(印, 窓, 寄り→9:30, 売買代金)] をその朝の合計と銘柄ごとの合計に足す"""
    g = {k: [0, 0.0, 0] for k in GROUPS}
    tb = {lab: {k: [0, 0.0] for k in ("base", "up1", "dn3")} for lab, _, _ in S.TURNOVER_BANDS}
    for sid, gap, r, tv in rows:
        for k in group_of(gap):
            g[k][0] += 1
            g[k][1] += r
            g[k][2] += int(r <= T.TRAP)
            if k in tb[_band(tv)]:
                tb[_band(tv)][k][0] += 1
                tb[_band(tv)][k][1] += r
            if k in STOCK_GROUPS:
                s = st["stocks"].setdefault(sid, {})
                c = s.setdefault(k, [0, 0.0])
                c[0] += 1
                c[1] += r
    st["days"][day] = {"g": g, "tb": tb}


# ════════════════════ 幅と判定 ════════════════════

def _boot_agg(Sm, Nm, stat, alpha=ALPHA, n_boot=N_BOOT, seed=P.SEED):
    """Sm・Nm＝[組][まとまり] の合計と件数 → stat(各組の平均) の (点, 下, 上)。まとまりが5未満なら幅は出さない"""
    Sm, Nm = np.asarray(Sm, float), np.asarray(Nm, float)
    with np.errstate(invalid="ignore", divide="ignore"):
        point = float(stat(Sm.sum(1) / Nm.sum(1)))
    K = Sm.shape[1]
    if not np.isfinite(point):
        return None, None, None
    if K < 5:
        return point, None, None
    rng = np.random.default_rng(seed)
    sims = []
    for start in range(0, n_boot, 500):
        d = rng.integers(0, K, size=(min(500, n_boot - start), K))
        with np.errstate(invalid="ignore", divide="ignore"):
            sims.append(stat(Sm[:, d].sum(2) / Nm[:, d].sum(2)))
    s = np.concatenate(sims)
    s = s[np.isfinite(s)]
    lo, hi = np.percentile(s, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return point, float(lo), float(hi)


def _by_day(st, groups, days=None):
    ds = sorted(days if days is not None else st["days"])
    Sm = [[st["days"][d]["g"][k][1] for d in ds] for k in groups]
    Nm = [[st["days"][d]["g"][k][0] for d in ds] for k in groups]
    return Sm, Nm


def _by_stock(st, groups):
    ids = sorted(st["stocks"])
    Sm = [[st["stocks"][i].get(k, [0, 0.0])[1] for i in ids] for k in groups]
    Nm = [[st["stocks"][i].get(k, [0, 0.0])[0] for i in ids] for k in groups]
    return Sm, Nm


def _point(st, groups, stat, days):
    Sm, Nm = _by_day(st, groups, days)
    Sm, Nm = np.asarray(Sm, float), np.asarray(Nm, float)
    if Nm.size == 0 or (Nm.sum(1) == 0).any():
        return None
    return float(stat(Sm.sum(1) / Nm.sum(1)))


def stat_a(mu):
    return mu[1] - mu[0]          # 高く寄った − ふつう（groups＝("base", "up1")）


def stat_b(mu):
    return mu[0] - T.COST         # 大きく安く寄った（groups＝("dn3",)）の費用後


ARMS = {"A": (("base", "up1"), stat_a), "B": (("dn3",), stat_b)}


def measure(st, arm):
    """その腕の いまの点・広いほうの95％の幅・前半後半・件数"""
    groups, stat = ARMS[arm]
    days = sorted(st["days"])
    ns = [sum(st["days"][d]["g"][k][0] for d in days) for k in groups]
    out = {"days": len(days), "ns": ns, "mean": None, "lo": None, "hi": None, "early": None, "late": None}
    if not days or min(ns) == 0:
        return out
    pt, lo_d, hi_d = _boot_agg(*_by_day(st, groups), stat)
    _, lo_s, hi_s = _boot_agg(*_by_stock(st, groups), stat)
    half = len(days) // 2
    out.update(mean=pt, by_day=[lo_d, hi_d], by_stock=[lo_s, hi_s],
               early=_point(st, groups, stat, days[:half]) if half else None, late=_point(st, groups, stat, days[half:]))
    if None not in (lo_d, lo_s, hi_d, hi_s):
        out.update(lo=min(lo_d, lo_s), hi=max(hi_d, hi_s))
    return out


def judge_a(m, day):
    ok = m["hi"] is not None and m["hi"] < 0 and (m["early"] or 0) < 0 and (m["late"] or 0) < 0
    reason = ("" if ok else "95％の幅が0をまたぐ／前半か後半がマイナスでない" if min(m["ns"]) >= MIN_N else "件数不足")
    return {"status": "confirm" if ok else "stop", "decided_on": day, "n": m["ns"][1], "days": m["days"],
            "mean": m["mean"], "lo": m["lo"], "hi": m["hi"], "early": m["early"], "late": m["late"], "reason": reason}


def judge_b(m, day, interim=False):
    if interim:
        return {"status": "stop", "decided_on": day, "n": m["ns"][0], "days": m["days"], "mean": m["mean"],
                "lo": m["lo"], "hi": m["hi"], "early": m["early"], "late": m["late"],
                "reason": f"途中の見張り（{m['days']}営業日）で費用後の平均がマイナス"}
    ok = (m["ns"][0] >= MIN_N and m["lo"] is not None and m["lo"] > 0 and (m["early"] or 0) > 0 and (m["late"] or 0) > 0)
    reason = "" if ok else ("件数不足" if m["ns"][0] < MIN_N else "95％の幅が0をまたぐ／前半か後半がプラスでない")
    return {"status": "plus" if ok else "stop", "decided_on": day, "n": m["ns"][0], "days": m["days"],
            "mean": m["mean"], "lo": m["lo"], "hi": m["hi"], "early": m["early"], "late": m["late"], "reason": reason}


def after_day(st, day):
    """1日足したあとに、決まった日数なら判定する（判定は書き換えない）"""
    n = len(st["days"])
    if "B" not in st["verdicts"]:
        if n == GOAL_DAYS:
            st["verdicts"]["B"] = judge_b(measure(st, "B"), day)
        elif n % CHECK_EVERY == 0:
            m = measure(st, "B")
            st["interim"].append({"day": day, "days": n, "mean": m["mean"]})
            if m["mean"] is not None and m["mean"] < 0:
                st["verdicts"]["B"] = judge_b(m, day, interim=True)
    if "A" not in st["marker_verdicts"] and n == GOAL_DAYS:
        st["marker_verdicts"]["A"] = judge_a(measure(st, "A"), day)


def done(st):
    return "B" in st["verdicts"] and "A" in st["marker_verdicts"]


# ════════════════════ 実行 ════════════════════

def trading_days(dailies, today, start=FWD_START):
    """取った日足から、数える朝（start 以上・今日より前・半分以上の銘柄に値がある日）"""
    cnt = {}
    for daily in dailies.values():
        for d in {b[0] for b in daily}:
            cnt[d] = cnt.get(d, 0) + 1
    half = len(dailies) / 2
    return sorted(d for d, c in cnt.items() if start <= d < today and c >= half)


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
    new = [d for d in trading_days(dailies, today) if d not in st["days"]]
    drops = {"n": 0}
    per = {code: stock_mornings(dailies[code], m5s[code], set(new), drops) for code in dailies}
    added = []
    for day in new:
        if done(st):
            break
        rows = [(tag(code), *per[code][day]) for code in sorted(per) if day in per[code]]
        if not rows:
            continue
        add_day(st, day, rows)
        after_day(st, day)
        added.append(day)
    return added, missing


# ════════════════════ 出力 ════════════════════

def _p(x, d=2):
    return Y._pct(x, d)


def _share(x):
    return "—" if x is None else f"{x * 100:.1f}％"


def summary(st):
    days = sorted(st["days"])
    tot = {k: [sum(st["days"][d]["g"][k][i] for d in days) for i in range(3)] for k in GROUPS}
    return {"days": len(days), "first": days[0] if days else None, "last": days[-1] if days else None,
            "groups": {k: {"n": v[0], "mean": v[1] / v[0] if v[0] else None, "trap": v[2] / v[0] if v[0] >= MIN_N else None}
                       for k, v in tot.items()}}


def render_md(st, now):
    sm = summary(st)
    L = ["# J13F 窓の戻し・前向き", "",
         f"更新: {now}（GitHub Actions）。事前登録＝`{P.PREREG}`「J13F」（指紋 sha256 `{(st.get('prereg_sha256') or '')[:16]}…`）。",
         f"数えるのは **{FWD_START} 以降の朝**だけ（一度数えた朝は数え直さない）。値は寄り→9:30 の株価の変化率。銘柄名は出しません。**売買の決まりではない**。", "",
         f"- 数えた朝：{sm['days']}営業日（{sm['first'] or '—'}〜{sm['last'] or '—'}）／判定は **{GOAL_DAYS}営業日**で1回だけ（腕B は {CHECK_EVERY}営業日ごとに費用後の平均がマイナスなら止める）",
         "", "| 組 | 回数 | 寄り→9:30 の平均（費用前） | 費用後 | 罠の割合（−1％ 以下） |", "|---|---:|---:|---:|---:|"]
    for k in GROUPS:
        g = sm["groups"][k]
        L.append(f"| {GL.GROUP_NAMES[k]} | {g['n']:,} | {_p(g['mean'])} | {_p(None if g['mean'] is None else g['mean'] - T.COST)} | "
                 f"{_share(g['trap'])} |")
    L += ["", "## 腕ごとの進み具合（途中の数字は判定に使わない）", ""]
    for arm, title, vd in (("A", MARKER_TITLES["A"], st["marker_verdicts"].get("A")), ("B", TITLES["B"], st["verdicts"].get("B"))):
        if vd:
            res = {"confirm": "✅ 前向きで確認", "plus": "✅ プラスを確認", "stop": "⏹ ストップ"}[vd["status"]]
            L.append(f"- **腕{arm} {title}**：{res}（{vd['decided_on']}・{vd['days']}営業日・{vd['n']:,}回）平均 {_p(vd['mean'])}"
                     f"（95％の幅 {_p(vd['lo'])}〜{_p(vd['hi'])}・前半 {_p(vd['early'])}／後半 {_p(vd['late'])}）{('・' + vd['reason']) if vd['reason'] else ''}")
        else:
            groups, stat = ARMS[arm]
            pt = _point(st, groups, stat, sorted(st["days"])) if st["days"] else None
            L.append(f"- **腕{arm} {title}**：観察中・いまの点 {_p(pt)}（{sm['days']}/{GOAL_DAYS}営業日）")
    if st["interim"]:
        L.append("- 腕B の途中の見張り：" + "／".join(f"{x['days']}営業日 {_p(x['mean'])}" for x in st["interim"]))
    L += ["", "- 窓＝寄り ÷ 前の取引日の終値 − 1。ふつう＝窓 ±1％ 未満。費用は往復 0.1％（小さい株は売り買いの差が大きく、甘い）。空売りは数えない。",
          "", "---", "", "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。"]
    return "\n".join(L) + "\n"


def finalize(st):
    """検証済みリスト・研究の地図が読む欄（いまの回数と判定の目安）"""
    sm = summary(st)
    st["progress"] = {"A": sm["groups"]["up1"]["n"], "B": sm["groups"]["dn3"]["n"]}
    st["goal"] = f"{GOAL_DAYS}営業日で判定・いま {sm['days']}営業日"
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
