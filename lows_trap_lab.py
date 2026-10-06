# -*- coding: utf-8 -*-
"""J12 安値更新の翌朝、寄りで買うと戻るか、まだ下がるか（落ちるナイフの見分け）（2026-10-06 登録・オーナー「その調子でどんどん研究を進めてください」）。

サイトの「高値・安値更新」の安値の側（東証の全上場・約3,700銘柄）と同じ決め方で、過去の年初来安値（1〜3月は昨年来安値）の更新を
日ごとに決め直し、翌朝に寄りで買ったときの値動きを数える。J10・J11（高値の側）と同じ物差し・同じ値の取り方。

⚠️ 決まりは PILLAR_PREREG.md「J12」と下の定数に固定。結果を見てから動かさない。値の取り方・幅の出し方は highs_trap_lab.py をそのまま使う。
⚠️ 安値更新は build_jp_highs.ytd_extreme(side="low") と同じ答え（テストで突き合わせる）＋サイトの一覧と同じ「期間の覆いの確かめ」。
   確かめられない日の安値更新は、安値更新の組にも比べる相手にも入れない。安値更新でない日は比べる相手に残す。
⚠️ 比べる相手は件数が多い（数百万）ので、件数・合計・罠の数だけを持つ（判定には使わない）。
⚠️ 出力（lows-trap-lab.json / .md）は集計だけ・銘柄名とコードは出さない。GitHub 側で生成＝手元から送らない（SYNC禁忌）。

実行: python lows_trap_lab.py          （本番。Actions の lows-trap-lab.yml から手動で・1回だけ）
      python lows_trap_lab.py --diag   （件数とデータの形だけ。値動きは出さない・何も書き出さない）
"""
import bisect
import datetime as dt
import json
import sys
import time

import build_jp_highs as H
import highs_trap_lab as T
import highs_trap_small as S
import pillar_lab as P
import yori_lab as Y

OUT_JSON, OUT_MD = "lows-trap-lab.json", "lows-trap-lab.md"
GAP_DOWN = -0.01              # Q1 窓が −1％ 以下
WICK = 0.5                    # Q3 前の日の（終値−安値）÷（高値−安値）が 0.5 以上＝下ヒゲが長い
PREV_BIG = -0.05              # Q4 前の日に −5％ 以下下げた
N_Q = 5                       # 判定の数（Q0〜Q4）
ALPHA = 0.05 / N_Q            # 99％ の幅
CROWD_BANDS = (("1〜20銘柄", 1, 20), ("21〜100銘柄", 21, 100), ("101銘柄以上", 101, 10 ** 9))
GAP_BANDS = (("−3％未満", -1e9, -0.03), ("−3〜−1％", -0.03, -0.01), ("−1〜+1％", -0.01, 0.01), ("+1％以上", 0.01, 1e9))

FLAGS = [
    ("q1", "Q1 窓が −1％ 以下", lambda r: r["gap"] <= GAP_DOWN),
    ("q2", "Q2 寄りが前の日の安値より下", lambda r: r["below_low"]),
    ("q3", "Q3 前の日の下ヒゲが長い", lambda r: r["wick"] >= WICK),
    ("q4", "Q4 前の日に −5％ 以下下げた", lambda r: r["prev_ret"] is not None and r["prev_ret"] <= PREV_BIG),
]


# ════════════════════ 安値更新 ════════════════════

def ytd_low_flags(bars):
    """bars＝[(日付, 高値, 安値, 終値, 出来高)]（日付順）→ 各日に年初来安値（1〜3月は昨年来安値）を更新したか。

    build_jp_highs.ytd_extreme(bars[:k+1], window_start(その日), side="low") が None でないのと同じ答え（テストで突き合わせる）。"""
    n = len(bars)
    dates = [b[0] for b in bars]
    lows = [b[2] for b in bars]
    out = [False] * n
    runmin = {}
    for k in range(1, n):
        s = bisect.bisect_left(dates, H.window_start(dates[k])[0])
        if k - s < H.MIN_PRIOR_BARS or not H.sane_today(bars[k - 1:k + 1]):
            continue
        if s not in runmin:
            acc, m = [], float("inf")
            for x in lows[s:]:
                m = min(m, x)
                acc.append(m)
            runmin[s] = acc
        out[k] = lows[k] < runmin[s][k - 1 - s]
    return out


def stock_records(code, daily, m5, h1, covered, end_day=T.END_DAY, drops=None):
    """J10 と同じ値の取り方。安値更新は covered(その日の日付) が真の日だけ。
    → (安値更新の翌朝の記録, 比べる相手の集計)"""
    flags = ytd_low_flags([(d, h, lo, c, v) for d, o, h, lo, c, v in daily])
    ev, ctl = [], S.empty_ctl()
    for k in range(1, len(daily) - 1):
        day, op, close = daily[k + 1][0], daily[k + 1][1], daily[k + 1][4]
        if day > end_day:
            break
        if not op or op <= 0 or H.window_start(daily[k][0])[0] < T.MIN_WINDOW_START:
            continue
        if flags[k] and not covered(daily[k][0]):
            continue                                  # 確かめられない安値更新＝どちらにも入れない
        out = T.outcomes(op, close, m5.get(day), h1.get(day), drops)
        if out is None:
            continue
        if flags[k]:
            _, _, h0, l0, c0, v0 = daily[k]
            pc = daily[k - 1][4]
            ev.append(dict(out, date=day, code=code, low_day=daily[k][0], gap=op / c0 - 1, below_low=op < l0,
                           wick=(c0 - l0) / (h0 - l0) if h0 > l0 else 0.0, prev_ret=c0 / pc - 1 if pc else None,
                           turnover=c0 * v0 / 1e8))
        else:
            for key, n, s, t in (("r930", "n930", "s930", "t930"), ("r1000", "n1000", "s1000", "t1000")):
                if out[key] is not None:
                    ctl[n] += 1
                    ctl[s] += out[key]
                    ctl[t] += int(out[key] <= T.TRAP)
    return ev, ctl


# ════════════════════ 判定 ════════════════════

def judge_q0(full, early, late, m60):
    if full.get("lo") is None:
        return "件数不足"
    for sign, base in ((-1, "安値更新の翌朝の寄り買いは、平均で負けやすい兆し（まだ下がる）"),
                       (+1, "安値更新の翌朝の寄り買いは、平均で勝ちやすい兆し（戻る）")):
        whole = full["hi"] < 0 if sign < 0 else full["lo"] > 0
        if whole and T._side(early.get("mean"), sign) and T._side(late.get("mean"), sign):
            return T._verdict(base, T.check60(m60.get("n", 0), m60.get("mean"), sign))
    return "見えない"


def judge_flag(full, early, late, mean_a_cost, d60):
    if full.get("n_a", 0) < T.MIN_N or full.get("n_b", 0) < T.MIN_N or full.get("lo") is None:
        return "件数不足"
    for sign, base in ((-1, "罠の目印（まだ下がる＝入らない方がいい兆し）"), (+1, "戻りの目印（兆し）")):
        whole = full["hi"] < 0 if sign < 0 else full["lo"] > 0
        if whole and T._side(early.get("diff"), sign) and T._side(late.get("diff"), sign) and T._side(mean_a_cost, sign):
            return T._verdict(base, T.check60(d60.get("n_a", 0), d60.get("diff"), sign))
    return "見えない"


def _band(x, bands):
    return next((lab for lab, a, b in bands if a <= x < b), None)


def _crowd(x):
    return next(lab for lab, a, b in CROWD_BANDS if a <= x <= b)


def analyze(ev, ctl, big=frozenset()):
    """big＝J10 の約400銘柄のコード（読むための表の分け方だけに使う）"""
    crowd = {}
    for r in ev:
        crowd[r["low_day"]] = crowd.get(r["low_day"], 0) + 1     # その日に安値を更新した銘柄の数（数えた銘柄のうち）
    e2 = [r for r in ev if r["r1000"] is not None]
    e60 = [r for r in ev if r["r930"] is not None]
    days = sorted({r["date"] for r in e2})
    cut = days[len(days) // 2] if days else ""
    early, late = [r for r in e2 if r["date"] < cut], [r for r in e2 if r["date"] >= cut]
    days60 = sorted({r["date"] for r in e60})
    f10, f930 = (lambda r: r["r1000"]), (lambda r: r["r930"])
    f10c, f930c = T._cost("r1000"), T._cost("r930")
    res = {"n_2y": len(e2), "days_2y": len(days), "first": days[0] if days else None, "last": days[-1] if days else None,
           "cut": cut, "n_60d": len(e60), "days_60d": len(days60), "first_60d": days60[0] if days60 else None,
           "last_60d": days60[-1] if days60 else None, "n_fallback_1000": sum(1 for r in e2 if r["fb"]),
           "by_year": {y: sum(1 for r in e2 if r["date"][:4] == y) for y in sorted({r["date"][:4] for r in e2})}}
    q0 = {"all": T.safe(e2, f10c, alpha=ALPHA), "early": T.mean_of(early, f10c), "late": T.mean_of(late, f10c),
          "m60": T.mean_of(e60, f930c)}
    q0["verdict"] = judge_q0(q0["all"], q0["early"], q0["late"], q0["m60"])
    res["q0"] = q0
    res["flags"] = {}
    for key, name, flag in FLAGS:
        q = {"name": name, "all": T.safe(e2, f10, flag, alpha=ALPHA), "early": T.diff_of(early, f10, flag),
             "late": T.diff_of(late, f10, flag), "mean_a_cost": T.mean_of([r for r in e2 if flag(r)], f10c),
             "mean_b_cost": T.mean_of([r for r in e2 if not flag(r)], f10c), "d60": T.diff_of(e60, f930, flag)}
        q["verdict"] = judge_flag(q["all"], q["early"], q["late"], q["mean_a_cost"]["mean"], q["d60"])
        res["flags"][key] = q
    # ── 読むための表（判定しない）──
    res["paths"] = {k: T.mean_of(ev, lambda r, k=k: r[k]) for k in ("r915", "r930", "r1000", "rclose")}
    res["ctl"] = {k: {"n": ctl["n" + s], "mean": ctl["s" + s] / ctl["n" + s] if ctl["n" + s] else None,
                      "trap": ctl["t" + s] / ctl["n" + s] if ctl["n" + s] else None}
                  for k, s in (("r930", "930"), ("r1000", "1000"))}
    res["trap"] = {"r1000": T._share(e2, "r1000"), "r930": T._share(e60, "r930")}

    def table(pick, labels):
        return {lab: {"2y": T.mean_of([r for r in e2 if pick(r) == lab], f10),
                      "2y_trap": T._share([r for r in e2 if pick(r) == lab], "r1000"),
                      "60d": T.mean_of([r for r in e60 if pick(r) == lab], f930)} for lab in labels}

    res["by_turnover"] = table(lambda r: S._band(r["turnover"]), [b[0] for b in S.TURNOVER_BANDS])
    res["by_crowd"] = table(lambda r: _crowd(crowd[r["low_day"]]), [b[0] for b in CROWD_BANDS])
    res["by_gap"] = table(lambda r: _band(r["gap"], GAP_BANDS), [b[0] for b in GAP_BANDS])
    res["by_size"] = table(lambda r: "約400銘柄" if r["code"] in big else "それ以外", ["約400銘柄", "それ以外"])
    return res


# ════════════════════ 実行 ════════════════════

def load(codes, jpx, fetch=Y.fetch_chart, end_day=T.END_DAY):
    ev, ctl = [], S.empty_ctl()
    missing = {"daily": [], "h1": [], "m5": []}
    drops = {"n": 0}
    shape = {"first_day_after_2022": 0}
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
        shape["first_day_after_2022"] += int(first > "2022-01-11")

        def covered(day, first=first, code=code):
            return H.window_covered([(first,)], H.window_start(day)[0], code, jpx)

        e, c = stock_records(code, daily, T._by_day(m5), T._by_day(h1), covered, end_day=end_day, drops=drops)
        ev += e
        S.add_ctl(ctl, c)
        if (i + 1) % 200 == 0:
            print(f"  ...{i + 1}/{len(codes)}", flush=True)
        time.sleep(0.03)
    return ev, ctl, missing, drops, shape


def diag_summary(ev, ctl, missing, shape, n_codes):
    """件数とデータの形だけ（値動きは出さない）"""
    e2 = [r for r in ev if r["r1000"] is not None]
    e60 = [r for r in ev if r["r930"] is not None]
    return {"n_codes": n_codes, "missing": {k: len(v) for k, v in missing.items()}, "shape": shape,
            "events": {"n_2y": len(e2), "n_60d": len(e60), "days_2y": len({r["date"] for r in e2}),
                       "first": min((r["date"] for r in e2), default=None), "last": max((r["date"] for r in e2), default=None),
                       "by_year": {y: sum(1 for r in e2 if r["date"][:4] == y) for y in sorted({r["date"][:4] for r in e2})},
                       "n_fallback_1000": sum(1 for r in e2 if r["fb"])},
            "flag_sizes_2y": {k: sum(1 for r in e2 if f(r)) for k, _, f in FLAGS},
            "flag_sizes_60d": {k: sum(1 for r in e60 if f(r)) for k, _, f in FLAGS},
            "n_ctl": {"2y": ctl["n1000"], "60d": ctl["n930"]}}


def _p(x, d=2):
    return Y._pct(x, d)


def _row(lab, b):
    return (f"| {lab} | {_p(b['2y'].get('mean'))}（{b['2y'].get('n', 0)}） | {T._share_txt(b['2y_trap'])} | "
            f"{_p(b['60d'].get('mean'))}（{b['60d'].get('n', 0)}） |")


def render_md(res):
    L = ["# J12 安値更新の翌朝、寄りで買うと戻るか、まだ下がるか", "",
         f"作成: {res['generated_at']}（GitHub Actions で計算）。事前登録＝`{P.PREREG}`「J12」（指紋 sha256 `{(res.get('prereg_sha256') or '')[:16]}…`）。",
         "銘柄名は出しません。値は株価の変化率（％）。**売買の決まりではない**。", ""]
    r = res.get("result") or {}
    if r.get("error"):
        return "\n".join(L + [f"- ⚠️ 計算できず: {r['error']}", ""]) + "\n"
    L += [f"- 対象：東証の全上場 {r.get('n_codes')}銘柄（一覧 {r.get('list_date')}）。取れなかった銘柄 {r.get('n_missing')}",
          f"- 1時間足（判定の主・寄り→10:00）：{r['first']}〜{r['last']}・{r['days_2y']}営業日・{r['n_2y']}件（前半と後半の境 {r['cut']}）。年ごと {r['by_year']}",
          f"- 5分足（オーナーの取引時間・寄り→9:30）：{r['first_60d']}〜{r['last_60d']}・{r['days_60d']}営業日・{r['n_60d']}件",
          f"- 翌朝が {T.END_DAY} までの日だけ。幅は99％（p＜0.05÷5）・日と銘柄で引き直した広いほう。±25％超で捨てた値 {r.get('n_dropped')}",
          "", "## 判定（事前登録の5つ）", ""]
    q0 = r["q0"]
    a = q0["all"]
    L.append(f"- **Q0 そもそも（寄りで買い 10:00 に手仕舞う・費用後）**：平均 {_p(a.get('mean'))}（幅 {_p(a.get('lo'))}〜{_p(a.get('hi'))}・{a.get('n', 0)}件）"
             f"・前半 {_p(q0['early'].get('mean'))}／後半 {_p(q0['late'].get('mean'))}・5分足の寄り→9:30（費用後）{_p(q0['m60'].get('mean'))}（{q0['m60'].get('n', 0)}件）"
             f" → **{q0['verdict']}**")
    for key, _, _ in FLAGS:
        q = r["flags"][key]
        d = q["all"]
        L.append(f"- **{q['name']}**：目印あり−なし（寄り→10:00）の差 {_p(d.get('diff'))}（幅 {_p(d.get('lo'))}〜{_p(d.get('hi'))}・"
                 f"{d.get('n_a', 0)}件 対 {d.get('n_b', 0)}件）・前半 {_p(q['early'].get('diff'))}／後半 {_p(q['late'].get('diff'))}・"
                 f"目印ありの平均（費用後）{_p(q['mean_a_cost'].get('mean'))}／なし {_p(q['mean_b_cost'].get('mean'))}・"
                 f"5分足の寄り→9:30 の差 {_p(q['d60'].get('diff'))}（{q['d60'].get('n_a', 0)}件 対 {q['d60'].get('n_b', 0)}件） → **{q['verdict']}**")
    pa, c, tr = r["paths"], r["ctl"], r["trap"]
    L += ["", "## 読むための表（判定しない）", "", "### 寄りで買った場合の平均（費用なし）", "",
          "| | 寄り→9:15 | 寄り→9:30 | 寄り→10:00 | 寄り→大引け |", "|---|---:|---:|---:|---:|",
          "| 安値更新の翌朝 | " + " | ".join(f"{_p(pa[k].get('mean'))}（{pa[k].get('n', 0)}）" for k in ("r915", "r930", "r1000", "rclose")) + " |",
          f"| 比べる相手 | — | {_p(c['r930']['mean'])}（{c['r930']['n']}） | {_p(c['r1000']['mean'])}（{c['r1000']['n']}） | — |",
          "", f"- 罠の割合（寄りから −1％ 以下）：安値更新の翌朝 10:00 {T._share_txt(tr['r1000'])}・9:30 {T._share_txt(tr['r930'])}／"
          f"比べる相手 10:00 {T._share_txt({'mean': c['r1000']['trap'], 'n': c['r1000']['n']})}・9:30 {T._share_txt({'mean': c['r930']['trap'], 'n': c['r930']['n']})}"]
    for title, key in (("前の日の売買代金ごと", "by_turnover"), ("その日に安値を更新した銘柄の数ごと（多い日＝全体が崩れた日）", "by_crowd"),
                       ("窓の区分ごと", "by_gap"), ("J10 の約400銘柄か、それ以外か", "by_size")):
        L += ["", f"### {title}", "", "| 区分 | 寄り→10:00 の平均（件数） | 罠の割合 | 寄り→9:30 の平均（件数） |", "|---|---:|---:|---:|"]
        L += [_row(lab, b) for lab, b in r[key].items()]
    L += ["", "- 30件未満の区分は「—」。小さい株は売り買いの差が大きく、費用 0.1％ は甘い（目印は差なので費用は消える）。空売りは数えない（貸株の費用と在庫が銘柄ごとに違うため）。",
          "", "---", "", "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。"]
    return "\n".join(L) + "\n"


def main(argv):
    res = {"generated_at": dt.datetime.now(P.JST).isoformat(timespec="minutes"), "prereg_file": P.PREREG,
           "prereg_sha256": P.prereg_sha256(), "end_day": T.END_DAY}
    try:
        stocks, list_date = H.load_universe()
        codes = sorted(stocks)
        with open(Y.UNIVERSE, encoding="utf-8") as fh:
            big = frozenset(json.load(fh)["stocks"])
        jpx = H.load_new_listings()
        ev, ctl, missing, drops, shape = load(codes, jpx)
        if "--diag" in argv:
            print(json.dumps(diag_summary(ev, ctl, missing, shape, len(codes)), ensure_ascii=False, indent=1))
            return 0
        bad = set(missing["daily"]) | set(missing["h1"])
        if len(bad) > T.MAX_MISSING * len(codes):
            raise RuntimeError(f"日足か1時間足を取れなかった銘柄が {len(bad)}/{len(codes)}＝5％超。偏った組で判定しない（取り直す）")
        res["result"] = dict(analyze(ev, ctl, big), n_codes=len(codes), list_date=list_date,
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
