# -*- coding: utf-8 -*-
"""J11 J10 の罠の目印は、約400銘柄の外の株でも成り立つか（2026-10-06 登録・オーナー「その調子でどんどん研究を進めてください」）。

J10（highs_trap_lab.py）が数えていない銘柄＝東証の全上場（JPX の一覧）から jp-stock-info.json の約400を除いた約3,300で、
J10 の Q0（そもそも負けやすいか）と Q1（窓 +1％ 以上＝罠の目印か）だけを、同じ物差しで数える。

⚠️ 決まりは PILLAR_PREREG.md「J11」と下の定数に固定。結果を見てから動かさない。値の取り方・判定の関数は highs_trap_lab.py をそのまま使う。
⚠️ 高値更新は J10 と同じ決め方に、サイトの一覧と同じ「期間の覆いの確かめ」（build_jp_highs.window_covered＋JPX の新規上場の一覧）を足す。
   確かめられない日の高値更新は、高値更新の組にも比べる相手にも入れない。高値更新でない日は比べる相手に残す。
⚠️ 比べる相手は件数が多い（数十万）ので、件数・合計・罠の数だけを持つ（判定には使わない）。
⚠️ 出力（highs-trap-small.json / .md）は集計だけ・銘柄名とコードは出さない。GitHub 側で生成＝手元から送らない（SYNC禁忌）。

実行: python highs_trap_small.py          （本番。Actions の highs-trap-small.yml から手動で・1回だけ）
      python highs_trap_small.py --diag   （件数とデータの形だけ。値動きは出さない・何も書き出さない）
"""
import datetime as dt
import json
import sys
import time

import build_jp_highs as H
import highs_trap_lab as T
import jp_bars
import pillar_lab as P
import yori_lab as Y

OUT_JSON, OUT_MD = "highs-trap-small.json", "highs-trap-small.md"
N_Q = 2
ALPHA = 0.05 / N_Q            # 97.5％ の幅
TURNOVER_BANDS = (("1億円未満", 0.0, 1.0), ("1〜10億円", 1.0, 10.0), ("10億円以上", 10.0, 1e18))
FLAG = lambda r: r["gap"] >= T.GAP_UP  # noqa: E731  Q1 窓 +1％ 以上（J10 と同じ）


def universe(load=None, info_path=Y.UNIVERSE):
    """→ ({コード: 情報}（約400を除いた）, 一覧の日付, 全体の件数)"""
    stocks, list_date = (load or H.load_universe)()
    with open(info_path, encoding="utf-8") as fh:
        big = set(json.load(fh)["stocks"])
    return {c: m for c, m in stocks.items() if c not in big}, list_date, len(stocks)


def empty_ctl():
    return {"n930": 0, "s930": 0.0, "t930": 0, "n1000": 0, "s1000": 0.0, "t1000": 0}


def add_ctl(acc, x):
    for k in acc:
        acc[k] += x[k]
    return acc


def stock_records(code, daily, m5, h1, covered, end_day=T.END_DAY, drops=None):
    """J10 の stock_records と同じ値の取り方。高値更新は covered(その日の日付) が真の日だけ。
    → (高値更新の翌朝の記録, 比べる相手の集計)"""
    flags = T.ytd_flags([(d, h, lo, c, v) for d, o, h, lo, c, v in daily])
    ev, ctl = [], empty_ctl()
    for k in range(1, len(daily) - 1):
        day, op, close = daily[k + 1][0], daily[k + 1][1], daily[k + 1][4]
        if day > end_day:
            break
        if not op or op <= 0 or H.window_start(daily[k][0])[0] < T.MIN_WINDOW_START:
            continue
        if flags[k] and not covered(daily[k][0]):
            continue                                  # 確かめられない高値更新＝どちらにも入れない
        out = T.outcomes(op, close, m5.get(day), h1.get(day), drops)
        if out is None:
            continue
        if flags[k]:
            _, _, h0, l0, c0, v0 = daily[k]
            pc = daily[k - 1][4]
            ev.append(dict(out, date=day, code=code, gap=op / c0 - 1, above_high=op > h0,
                           wick=(h0 - c0) / (h0 - l0) if h0 > l0 else 0.0, prev_ret=c0 / pc - 1 if pc else None,
                           turnover=c0 * v0 / 1e8))
        else:
            for key, n, s, t in (("r930", "n930", "s930", "t930"), ("r1000", "n1000", "s1000", "t1000")):
                if out[key] is not None:
                    ctl[n] += 1
                    ctl[s] += out[key]
                    ctl[t] += int(out[key] <= T.TRAP)
    return ev, ctl


def _band(x):
    return next(lab for lab, a, b in TURNOVER_BANDS if a <= x < b)


def analyze(ev, ctl):
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
    q0["verdict"] = T.judge_q0(q0["all"], q0["early"], q0["late"], q0["m60"])
    q1 = {"all": T.safe(e2, f10, FLAG, alpha=ALPHA), "early": T.diff_of(early, f10, FLAG), "late": T.diff_of(late, f10, FLAG),
          "mean_a_cost": T.mean_of([r for r in e2 if FLAG(r)], f10c), "mean_b_cost": T.mean_of([r for r in e2 if not FLAG(r)], f10c),
          "d60": T.diff_of(e60, f930, FLAG)}
    q1["verdict"] = T.judge_flag(q1["all"], q1["early"], q1["late"], q1["mean_a_cost"]["mean"], q1["d60"])
    res["q0"], res["q1"] = q0, q1
    # ── 読むための表（判定しない）──
    res["paths"] = {k: T.mean_of(ev, lambda r, k=k: r[k]) for k in ("r915", "r930", "r1000", "rclose")}
    res["ctl"] = {"r930": {"n": ctl["n930"], "mean": ctl["s930"] / ctl["n930"] if ctl["n930"] else None,
                           "trap": ctl["t930"] / ctl["n930"] if ctl["n930"] else None},
                  "r1000": {"n": ctl["n1000"], "mean": ctl["s1000"] / ctl["n1000"] if ctl["n1000"] else None,
                            "trap": ctl["t1000"] / ctl["n1000"] if ctl["n1000"] else None}}
    bands = {}
    for lab, _, _ in TURNOVER_BANDS:
        rows2 = [r for r in e2 if _band(r["turnover"]) == lab]
        rows60 = [r for r in e60 if _band(r["turnover"]) == lab]
        bands[lab] = {"2y": T.mean_of(rows2, f10), "2y_trap": T._share(rows2, "r1000"), "q1_diff_2y": T.diff_of(rows2, f10, FLAG),
                      "60d": T.mean_of(rows60, f930), "60d_trap": T._share(rows60, "r930")}
    res["by_turnover"] = bands
    res["other_flags_2y"] = {name: T.diff_of(e2, f10, flag) for key, name, flag in T.FLAGS if key != "q1"}
    res["by_gap"] = {b: {"2y": T._share([r for r in e2 if Y.gap_band(r["gap"]) == b], "r1000"),
                         "mean_2y": T.mean_of([r for r in e2 if Y.gap_band(r["gap"]) == b], f10)}
                     for b in ("−1％未満", "−1〜+1％", "+1〜+3％", "+3％以上")}
    return res


# ════════════════════ 実行 ════════════════════

def load(codes, jpx, fetch=Y.fetch_chart, end_day=T.END_DAY):
    ev, ctl = [], empty_ctl()
    missing = {"daily": [], "h1": [], "m5": []}
    drops = {"n": 0}
    shape = {"first_day_after_2022": 0, "uncovered_highs": 0}
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
        add_ctl(ctl, c)
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
            "q1_sizes": {"2y": sum(1 for r in e2 if FLAG(r)), "60d": sum(1 for r in e60 if FLAG(r))},
            "by_turnover_n": {lab: sum(1 for r in e2 if _band(r["turnover"]) == lab) for lab, _, _ in TURNOVER_BANDS},
            "n_ctl": {"2y": ctl["n1000"], "60d": ctl["n930"]}}


def _p(x, d=2):
    return Y._pct(x, d)


def render_md(res):
    L = ["# J11 J10 の罠の目印は、約400銘柄の外の株でも成り立つか", "",
         f"作成: {res['generated_at']}（GitHub Actions で計算）。事前登録＝`{P.PREREG}`「J11」（指紋 sha256 `{(res.get('prereg_sha256') or '')[:16]}…`）。",
         "銘柄名は出しません。値は株価の変化率（％）。**売買の決まりではない**。", ""]
    r = res.get("result") or {}
    if r.get("error"):
        return "\n".join(L + [f"- ⚠️ 計算できず: {r['error']}", ""]) + "\n"
    L += [f"- 対象：東証の全上場 {r.get('n_listed')}銘柄（一覧 {r.get('list_date')}）のうち、J10 の約400を除いた {r.get('n_codes')}銘柄。取れなかった銘柄 {r.get('n_missing')}",
          f"- 1時間足（判定の主・寄り→10:00）：{r['first']}〜{r['last']}・{r['days_2y']}営業日・{r['n_2y']}件（前半と後半の境 {r['cut']}）。年ごと {r['by_year']}",
          f"- 5分足（オーナーの取引時間・寄り→9:30）：{r['first_60d']}〜{r['last_60d']}・{r['days_60d']}営業日・{r['n_60d']}件",
          f"- 翌朝が {T.END_DAY} までの日だけ。幅は97.5％（p＜0.05÷2）・日と銘柄で引き直した広いほう。±25％超で捨てた値 {r.get('n_dropped')}",
          "", "## 判定（事前登録の2つ）", ""]
    q0, q1 = r["q0"], r["q1"]
    a = q0["all"]
    L.append(f"- **Q0 そもそも（寄りで買い 10:00 に手仕舞う・費用後）**：平均 {_p(a.get('mean'))}（幅 {_p(a.get('lo'))}〜{_p(a.get('hi'))}・{a.get('n', 0)}件）"
             f"・前半 {_p(q0['early'].get('mean'))}／後半 {_p(q0['late'].get('mean'))}・5分足の寄り→9:30（費用後）{_p(q0['m60'].get('mean'))}（{q0['m60'].get('n', 0)}件）"
             f" → **{q0['verdict']}**")
    d = q1["all"]
    L.append(f"- **Q1 窓が +1％ 以上**：目印あり−なし（寄り→10:00）の差 {_p(d.get('diff'))}（幅 {_p(d.get('lo'))}〜{_p(d.get('hi'))}・"
             f"{d.get('n_a', 0)}件 対 {d.get('n_b', 0)}件）・前半 {_p(q1['early'].get('diff'))}／後半 {_p(q1['late'].get('diff'))}・"
             f"目印ありの平均（費用後）{_p(q1['mean_a_cost'].get('mean'))}／なし {_p(q1['mean_b_cost'].get('mean'))}・"
             f"5分足の寄り→9:30 の差 {_p(q1['d60'].get('diff'))}（{q1['d60'].get('n_a', 0)}件 対 {q1['d60'].get('n_b', 0)}件） → **{q1['verdict']}**")
    pa, c = r["paths"], r["ctl"]
    L += ["", "## 読むための表（判定しない）", "", "### 寄りで買った場合の平均（費用なし）", "",
          "| | 寄り→9:15 | 寄り→9:30 | 寄り→10:00 | 寄り→大引け |", "|---|---:|---:|---:|---:|",
          f"| 高値更新の翌朝 | " + " | ".join(f"{_p(pa[k].get('mean'))}（{pa[k].get('n', 0)}）" for k in ("r915", "r930", "r1000", "rclose")) + " |",
          f"| 比べる相手 | — | {_p(c['r930']['mean'])}（{c['r930']['n']}） | {_p(c['r1000']['mean'])}（{c['r1000']['n']}） | — |",
          "", "### 前の日の売買代金ごと", "",
          "| 売買代金 | 寄り→10:00 の平均（件数） | 罠の割合 | 目印あり−なしの差（10:00） | 寄り→9:30 の平均（件数） | 罠の割合（9:30） |",
          "|---|---:|---:|---:|---:|---:|"]
    for lab, b in r["by_turnover"].items():
        L.append(f"| {lab} | {_p(b['2y'].get('mean'))}（{b['2y'].get('n', 0)}） | {T._share_txt(b['2y_trap'])} | "
                 f"{_p(b['q1_diff_2y'].get('diff'))}（{b['q1_diff_2y'].get('n_a', 0)}対{b['q1_diff_2y'].get('n_b', 0)}） | "
                 f"{_p(b['60d'].get('mean'))}（{b['60d'].get('n', 0)}） | {T._share_txt(b['60d_trap'])} |")
    L += ["", f"- 比べる相手の罠の割合：寄り→10:00 {T._share_txt({'mean': c['r1000']['trap'], 'n': c['r1000']['n']})}・"
          f"寄り→9:30 {T._share_txt({'mean': c['r930']['trap'], 'n': c['r930']['n']})}",
          "- J10 のほかの目印（寄り→10:00 の差・判定しない）：" + "／".join(
              f"{name} {_p(v.get('diff'))}（{v.get('n_a', 0)}対{v.get('n_b', 0)}）" for name, v in r["other_flags_2y"].items()),
          "- 窓の区分ごと（寄り→10:00 の平均・罠の割合）：" + "／".join(
              f"{b} {_p(v['mean_2y'].get('mean'))}・{T._share_txt(v['2y'])}" for b, v in r["by_gap"].items()),
          "- 30件未満の区分は「—」。小さい株は売り買いの差が大きく、費用 0.1％ は甘い（Q1 は差なので費用は消える）。空売りは数えない。",
          "", "---", "", "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。"]
    return "\n".join(L) + "\n"


def main(argv):
    res = {"generated_at": dt.datetime.now(P.JST).isoformat(timespec="minutes"), "prereg_file": P.PREREG,
           "prereg_sha256": P.prereg_sha256(), "end_day": T.END_DAY}
    try:
        stocks, list_date, n_listed = universe(load=jp_bars.load_universe)   # 値段の置き場があればその一覧
        codes = sorted(stocks)
        jpx = H.load_new_listings()
        ev, ctl, missing, drops, shape = load(codes, jpx, fetch=jp_bars.fetcher())
        res["price_store"] = jp_bars.info()
        if "--diag" in argv:
            print(json.dumps(diag_summary(ev, ctl, missing, shape, len(codes)), ensure_ascii=False, indent=1))
            return 0
        bad = set(missing["daily"]) | set(missing["h1"])
        if len(bad) > T.MAX_MISSING * len(codes):
            raise RuntimeError(f"日足か1時間足を取れなかった銘柄が {len(bad)}/{len(codes)}＝5％超。偏った組で判定しない（取り直す）")
        res["result"] = dict(analyze(ev, ctl), n_codes=len(codes), n_listed=n_listed, list_date=list_date,
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
