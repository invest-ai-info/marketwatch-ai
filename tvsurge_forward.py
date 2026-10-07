# -*- coding: utf-8 -*-
"""J26F 目印C「前の日の売買代金の急増」の前向き（2026-10-07 夜 登録・オーナー「登録して続けてください」）。PILLAR_PREREG.md「J26F」。

発注前の点検表（MY_TRADING_RULES.md 日本株⑤）に入れた目印C を、**2026-10-08 以降の朝だけ**で数える（寄り→9:30・5分足）。
- 目印C ＝前の日の売買代金が20営業日平均の5倍以上 − 2倍未満（すべての朝）
- 目印C2＝その銘柄だけの窓 ±1％ 未満の朝だけで、5倍以上 − 2倍未満（窓の目印A と切り分ける）
売買代金の倍率は J26 と同じ landmine_lab.prev_more、朝の値の取り方は J17F（prevgap_forward.stock_mornings）をそのまま使う。
その銘柄だけの窓＝窓 − その朝に数えた全銘柄の窓の中央値（500銘柄未満の朝は数えない）。250営業日で1回だけ判定（97.5％の幅）。

⚠️ 決まりは PILLAR_PREREG.md「J26F」と下の定数に固定。途中の数字を見て動かさない。幅・日の選び方は gap_forward（J13F）をそのまま使う。
⚠️ 1行ずつの取引は持たない。朝ごと・組ごとの合計と、銘柄ごと（伏せた印）・組ごとの合計だけ。
⚠️ 出力（tvsurge-forward.json / .md）は GitHub 側で生成＝手元から送らない（SYNC禁忌）。積み上げた判定を持つ＝古い版で上書きしない。

実行: python tvsurge_forward.py          （Actions の tvsurge-forward.yml から平日に）
"""
import datetime as dt
import hashlib
import json
import sys
import time

import numpy as np

import build_jp_highs as H
import gap_forward as GF
import highs_trap_lab as T
import landmine_lab as LM
import pillar_lab as P
import prevgap_forward as PGF
import yori_lab as Y

STATE, OUT_MD = "tvsurge-forward.json", "tvsurge-forward.md"
FWD_START = "2026-10-08"
GOAL_DAYS = 250
N_Q = 2
ALPHA = 0.05 / N_Q            # 97.5％ の幅
MIN_N = 30
DAILY_RANGE = "3mo"           # 前の日の売買代金の倍率（その前の20営業日）に足りる長さ
TV_HIGH, TV_LOW = 5.0, 2.0
IDIO = 0.01                   # その銘柄だけの窓 ±1％
MIN_STOCKS = 500              # その朝に数えた銘柄がこれ未満なら、その朝は数えない
GROUPS = ("lo", "hi", "lo_mid", "hi_mid")
GROUP_NAMES = {"lo": "前の日の売買代金が20営業日平均の2倍未満", "hi": "前の日の売買代金が20営業日平均の5倍以上",
               "lo_mid": "2倍未満・その銘柄だけの窓 ±1％ 未満", "hi_mid": "5倍以上・その銘柄だけの窓 ±1％ 未満"}
MARKER_TITLES = {"C": "前の日の売買代金が20営業日平均の5倍以上の株は 9:30 までに下げやすいか（2倍未満との差）",
                 "C2": "ふつうに寄った朝（その銘柄だけの窓 ±1％ 未満）だけで、前の日の売買代金が5倍以上の株は 9:30 までに下げやすいか"}
ARMS = {"C": ("lo", "hi"), "C2": ("lo_mid", "hi_mid")}     # 差＝後ろ − 前


def empty_state():
    return {"registered": "J26F", "kind": "forward", "fwd_start": FWD_START, "goal_days": GOAL_DAYS, "unit": "pct",
            "titles": {}, "verdicts": {}, "marker_titles": MARKER_TITLES, "marker_verdicts": {},
            "days": {}, "stocks": {}, "skipped": {}, "runs": []}


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
    return hashlib.sha1(("j26f:" + str(code)).encode()).hexdigest()[:10]


def groups_of(idio, ratio):
    out = []
    if not np.isfinite(ratio):
        return out
    mid = abs(idio) < IDIO
    if ratio >= TV_HIGH:
        out += ["hi"] + (["hi_mid"] if mid else [])
    elif ratio < TV_LOW:
        out += ["lo"] + (["lo_mid"] if mid else [])
    return out


# ════════════════════ 1銘柄の朝 ════════════════════

def stock_mornings(daily, m5, days, drops=None):
    """→ {日付: (窓, 前の日の売買代金の倍率, 寄り→9:30)}。朝の値と除く朝は J17F と同じ。倍率がそろわない朝は NaN（窓の中央値には入れる）"""
    base = PGF.stock_mornings(daily, m5, days, drops)
    if not base:
        return {}
    ratio = LM.prev_more(daily)[0]
    pos = {r[0]: i for i, r in enumerate(daily)}
    return {day: (gap, float(ratio[pos[day] - 1]), r930) for day, (gap, _rprev, r930) in base.items()}


# ════════════════════ 合計を足す ════════════════════

def add_day(st, day, rows):
    """rows＝[(印, 窓, 倍率, 寄り→9:30)]。数えた銘柄が MIN_STOCKS 未満なら足さない（False）"""
    if len(rows) < MIN_STOCKS:
        st.setdefault("skipped", {})[day] = len(rows)
        return False
    med = float(np.median([gap for _, gap, _, _ in rows]))
    g = {k: [0, 0.0] for k in GROUPS}
    for sid, gap, ratio, r in rows:
        for k in groups_of(gap - med, ratio):
            g[k][0] += 1
            g[k][1] += r
            c = st["stocks"].setdefault(sid, {}).setdefault(k, [0, 0.0])
            c[0] += 1
            c[1] += r
    st["days"][day] = {"g": g, "median_gap": med, "n": len(rows)}
    st.get("skipped", {}).pop(day, None)
    return True


# ════════════════════ 幅と判定（J17F と同じ） ════════════════════

def _diff(mu):
    return mu[1] - mu[0]


def _day_sums(st, groups, days):
    return ([[st["days"][d]["g"][k][1] for d in days] for k in groups],
            [[st["days"][d]["g"][k][0] for d in days] for k in groups])


def _stock_sums(st, groups):
    ids = sorted(st["stocks"])
    return ([[st["stocks"][i].get(k, [0, 0.0])[1] for i in ids] for k in groups],
            [[st["stocks"][i].get(k, [0, 0.0])[0] for i in ids] for k in groups])


def _point(st, groups, days):
    Sm, Nm = _day_sums(st, groups, days)
    Sm, Nm = np.asarray(Sm, float), np.asarray(Nm, float)
    if Nm.size == 0 or (Nm.sum(1) == 0).any():
        return None
    return float(_diff(Sm.sum(1) / Nm.sum(1)))


def measure(st, arm):
    """その目印の いまの点・広いほうの97.5％の幅・前半後半・件数"""
    groups = ARMS[arm]
    days = sorted(st["days"])
    ns = [sum(st["days"][d]["g"][k][0] for d in days) for k in groups]
    out = {"days": len(days), "ns": ns, "mean": None, "lo": None, "hi": None, "early": None, "late": None}
    if not days or min(ns) == 0:
        return out
    pt, lo_d, hi_d = GF._boot_agg(*_day_sums(st, groups, days), _diff, alpha=ALPHA)
    _, lo_s, hi_s = GF._boot_agg(*_stock_sums(st, groups), _diff, alpha=ALPHA)
    half = len(days) // 2
    out.update(mean=pt, by_day=[lo_d, hi_d], by_stock=[lo_s, hi_s],
               early=_point(st, groups, days[:half]) if half else None, late=_point(st, groups, days[half:]))
    if None not in (lo_d, lo_s, hi_d, hi_s):
        out.update(lo=min(lo_d, lo_s), hi=max(hi_d, hi_s))
    return out


def judge(m, day):
    ok = m["hi"] is not None and m["hi"] < 0 and (m["early"] or 0) < 0 and (m["late"] or 0) < 0
    reason = ("" if ok else "97.5％の幅が0をまたぐ／前半か後半がマイナスでない" if min(m["ns"]) >= MIN_N else "件数不足")
    return {"status": "confirm" if ok else "stop", "decided_on": day, "n": m["ns"][1], "days": m["days"],
            "mean": m["mean"], "lo": m["lo"], "hi": m["hi"], "early": m["early"], "late": m["late"], "reason": reason}


def after_day(st, day):
    """1日足したあとに、250営業日に届いたら2つとも1回だけ判定する（判定は書き換えない）"""
    if len(st["days"]) == GOAL_DAYS:
        for arm in ARMS:
            if arm not in st["marker_verdicts"]:
                st["marker_verdicts"][arm] = judge(measure(st, arm), day)


def done(st):
    return all(arm in st["marker_verdicts"] for arm in ARMS)


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
    tot = {k: [sum(st["days"][d]["g"][k][i] for d in days) for i in range(2)] for k in GROUPS}
    return {"days": len(days), "first": days[0] if days else None, "last": days[-1] if days else None,
            "groups": {k: {"n": v[0], "mean": v[1] / v[0] if v[0] else None} for k, v in tot.items()}}


def render_md(st, now):
    sm = summary(st)
    L = ["# J26F 目印C「前の日の売買代金の急増」の前向き", "",
         f"更新: {now}（GitHub Actions）。事前登録＝`{P.PREREG}`「J26F」（指紋 sha256 `{(st.get('prereg_sha256') or '')[:16]}…`）。",
         f"数えるのは **{FWD_START} 以降の朝**だけ（一度数えた朝は数え直さない）。値は寄り→9:30 の株価の変化率。銘柄名は出しません。**売買の決まりではない**。", "",
         f"- 数えた朝：{sm['days']}営業日（{sm['first'] or '—'}〜{sm['last'] or '—'}）／判定は **{GOAL_DAYS}営業日**で1回だけ（97.5％の幅）",
         "- 売買代金の倍率＝前の日の売買代金 ÷ その前の20営業日の平均。その銘柄だけの窓＝窓 − その朝の全銘柄の窓の中央値（数えた銘柄が500未満の朝は数えない）",
         "", "| 組 | 回数 | 寄り→9:30 の平均（費用前） |", "|---|---:|---:|"]
    for k in GROUPS:
        g = sm["groups"][k]
        L.append(f"| {GROUP_NAMES[k]} | {g['n']:,} | {GF._p(g['mean'])} |")
    L += ["", "## 目印ごとの進み具合（途中の数字は判定に使わない）", ""]
    for arm in ARMS:
        vd = st["marker_verdicts"].get(arm)
        title = MARKER_TITLES[arm]
        if vd:
            res = {"confirm": "✅ 前向きで確認", "stop": "⏹ ストップ"}[vd["status"]]
            L.append(f"- **目印{arm} {title}**：{res}（{vd['decided_on']}・{vd['days']}営業日・{vd['n']:,}回）差 {GF._p(vd['mean'])}"
                     f"（97.5％の幅 {GF._p(vd['lo'])}〜{GF._p(vd['hi'])}・前半 {GF._p(vd['early'])}／後半 {GF._p(vd['late'])}）{('・' + vd['reason']) if vd['reason'] else ''}")
        else:
            pt = _point(st, ARMS[arm], sorted(st["days"])) if st["days"] else None
            L.append(f"- **目印{arm} {title}**：観察中・いまの点 {GF._p(pt)}（{sm['days']}/{GOAL_DAYS}営業日）")
    if st.get("skipped"):
        L.append(f"- 銘柄が{MIN_STOCKS}未満で数えなかった朝：" + "・".join(f"{d}（{n}）" for d, n in sorted(st["skipped"].items())))
    L += ["", "- ⏹ 目印C がストップになったら、点検表（`MY_TRADING_RULES.md` 日本株⑤）から外すかをオーナーに諮る。空売りは数えない。",
          "", "---", "", "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。"]
    return "\n".join(L) + "\n"


def finalize(st):
    """検証済みリスト・研究の地図が読む欄（いまの回数と判定の目安）"""
    sm = summary(st)
    st["progress"] = {"C": sm["groups"]["hi"]["n"], "C2": sm["groups"]["hi_mid"]["n"]}
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
