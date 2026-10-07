# -*- coding: utf-8 -*-
"""J26 J22 の「寄りのあと下げやすい」目印は、昔の2つの時代でも同じ向きか（前の日の売買代金の急増・高値引け・上ヒゲ）。
2026-10-07 夜 登録・オーナー「続けてください」。PILLAR_PREREG.md「J26」。

J22 の F7（前の日の売買代金が20営業日平均の5倍以上）・F9（前の日が高値引け）・F10（前の日の上ヒゲが長い）を、J22 が使っていない
E1＝2006-01〜2016-10（使える年は J18 と同じ決め方）と E2＝2016-11〜2023-09 の日足（寄り→大引け）で1回だけ数える。
Q4 は F7 を「窓の戻し」と切り分ける（その銘柄だけの窓 ±1％未満の朝だけ）。両方の時代で J22 と同じ向きなら「✅」。

⚠️ 決まりは PILLAR_PREREG.md「J26」と下の定数に固定。行は prevday_lab（J16）、特徴は landmine_lab.prev_more、
   その銘柄だけの窓は prevgap_lab.idio_gap、幅と向きは open30_lab（J22）の measure・direction をそのまま使う。
⚠️ 出力（open30-history-lab.json / .md）は集計だけ・銘柄名とコードは出さない（SYNC禁忌）。

実行: python open30_history_lab.py --check   （点検だけ＝行数・使える年・組ごとの件数。損益は数えない・何も書き出さない）
      python open30_history_lab.py           （本番。Actions の open30-history-lab.yml から手動で・1回だけ）
"""
import datetime as dt
import json
import sys

import numpy as np

import gap_lab as GL
import highs_trap_lab as T
import highs_trap_small as S
import jp_bars
import landmine_lab as LM
import open30_lab as O
import pillar_lab as P
import prevday_lab as PD
import prevgap_lab as PG
import third_period_lab as TP
import yori_lab as Y

OUT_JSON, OUT_MD = "open30-history-lab.json", "open30-history-lab.md"
E1 = TP.SPAN                               # 2006-01-04〜2016-10-31（使える年は J18 と同じ決め方）
E2 = PD.OLD                                # 2016-11-01〜2023-09-29
ERAS = (("e1", "E1 2006〜2016年"), ("e2", "E2 2016〜2023年"))
COLS = PD.COLS + ("tv_ratio", "wick", "hi_close")
C = {k: i for i, k in enumerate(COLS)}
IDIO = PG.IDIO                             # その銘柄だけの窓 ±1％
TV_HIGH, TV_LOW = 5.0, 2.0
N_Q = 8
ALPHA = 0.05 / N_Q                         # 99.375％ の幅
UP, DOWN = O.UP, O.DOWN
SAME, ONE, OPP, NONE = "✅ 昔の2つの時代とも同じ向き", "△ 片方の時代だけ", "⚠️ 逆向きの時代がある", "見えない"
# (問い, 説明, 元, 期待の向き)
QUESTIONS = (("Q1", "前の日の売買代金が20営業日平均の5倍以上 − 2倍未満", "J22 F7", -1),
             ("Q2", "前の日が高値引け − そうでない", "J22 F9", -1),
             ("Q3", "前の日の上ヒゲが長い − そうでない", "J22 F10（10:00 だけ）", +1),
             ("Q4", "ふつうに寄った朝（その銘柄だけの窓 ±1％未満）：前の日の売買代金が5倍以上 − 2倍未満", "J22 F7 を窓と切り分け", -1))


# ════════════════════ 行 ════════════════════

def stock_rows(ci, daily, drops=None):
    """J16 の行（2006-01-04〜2023-09-29・寄り→大引け）＋前の日の売買代金の倍率・上ヒゲ・高値引け"""
    A = PD.stock_rows(ci, daily, {}, {}, first=E1[0], last=E2[1], recent_from="2100-01-01", drops=drops)
    if not len(A):
        return np.zeros((0, len(COLS)))
    ratio, wick, hi_close, _ = LM.prev_more(daily)
    pos = {dt.date.fromisoformat(r[0]).toordinal(): i for i, r in enumerate(daily)}
    k = np.array([pos[int(o)] for o in A[:, C["day"]]]) - 1
    return np.hstack([A, ratio[k].reshape(-1, 1), wick[k].reshape(-1, 1), hi_close[k].reshape(-1, 1)])


# ════════════════════ 組と判定 ════════════════════

def groups(key, A, idio):
    """各行の組（特徴あり＝0・比べる相手＝1・それ以外＝−1）。NaN の特徴はどちらにも入れない"""
    tv, wk, hc = A[:, C["tv_ratio"]], A[:, C["wick"]], A[:, C["hi_close"]]
    with np.errstate(invalid="ignore"):
        if key == "Q1":
            return GL.pair_grp(tv >= TV_HIGH, tv < TV_LOW)
        if key == "Q2":
            return GL.pair_grp(hc >= 0.5, hc < 0.5)
        if key == "Q3":
            return GL.pair_grp(wk >= 0.5, wk < 0.5)
        if key == "Q4":
            mid = np.abs(idio) < IDIO
            return GL.pair_grp((tv >= TV_HIGH) & mid, (tv < TV_LOW) & mid)
    raise ValueError(key)


def era(A, span):
    d = A[:, C["day"]]
    return A[(d >= PD._ord(span[0])) & (d <= PD._ord(span[1]))]


def sign(direction):
    return -1 if direction == DOWN else +1 if direction == UP else 0


def verdict(signs, expected):
    if any(s == -expected for s in signs):
        return OPP
    hit = sum(s == expected for s in signs)
    return SAME if hit == len(signs) else ONE if hit else NONE


def _group_stats(v, g):
    """特徴ありの組の平均（費用前・往復0.1％を引いた後）と、費用後にプラスだった割合"""
    a = v[(g == 0) & np.isfinite(v)]
    if len(a) < T.MIN_N:
        return {"n": int(len(a)), "mean": None, "net": None, "win": None}
    return {"n": int(len(a)), "mean": float(a.mean()), "net": float(a.mean() - T.COST), "win": float((a - T.COST > 0).mean())}


def _plain(v, g):
    ns = [int(((g == k) & np.isfinite(v)).sum()) for k in range(2)]
    return {"ns": ns, "diff": PG._diff(v[np.isfinite(v)], g[np.isfinite(v)]) if min(ns) >= T.MIN_N else None}


def analyze(A, start):
    spans = {"e1": (start, E1[1]), "e2": E2}
    res = {"start_e1": start, "eras": {}, "judges": {}, "reading": {}}
    per = {}
    for key, _name in ERAS:
        B, idio = PG.idio_gap(era(A, spans[key]))
        v = B[:, C["rclose"]]
        days = np.unique(B[:, C["day"]])
        res["eras"][key] = {"rows": int(len(B)), "days": int(len(days)), "stocks": int(len(np.unique(B[:, C["code"]]))),
                            "first": dt.date.fromordinal(int(days[0])).isoformat() if len(days) else None,
                            "last": dt.date.fromordinal(int(days[-1])).isoformat() if len(days) else None}
        per[key] = (B, idio, v)
    for q, name, src, expected in QUESTIONS:
        out = {"name": name, "source": src, "expected": expected}
        signs = []
        for key, _n in ERAS:
            B, idio, v = per[key]
            g = groups(q, B, idio)
            m = O.measure(B, v, g, ALPHA)
            m["direction"] = O.direction(m)
            m["group"] = _group_stats(v, g)
            out[key] = m
            signs.append(sign(m["direction"]))
        out["verdict"] = verdict(signs, expected)
        res["judges"][q] = out
    # ── 読むための表（判定しない）──
    for key, _n in ERAS:
        B, idio, v = per[key]
        tv = B[:, C["turnover"]]
        years = np.array([dt.date.fromordinal(int(o)).year for o in B[:, C["day"]]])
        grps = {q: groups(q, B, idio) for q, *_ in QUESTIONS}
        ratio = B[:, C["tv_ratio"]]
        with np.errstate(invalid="ignore"):
            cuts = {f"{x:g}倍以上 − 2倍未満": GL.pair_grp(ratio >= x, ratio < TV_LOW) for x in (3.0, 10.0)}
        res["reading"][key] = {
            "by_turnover": {lab: {q: _plain(v, np.where((tv >= lo) & (tv < hi), g, -1)) for q, g in grps.items()}
                            for lab, lo, hi in S.TURNOVER_BANDS},
            "by_year": {str(y): {q: _plain(v, np.where(years == y, g, -1)) for q, g in grps.items()} for y in np.unique(years)},
            "ratio_cuts": {lab: _plain(v, g) for lab, g in cuts.items()}}
    res["n_same"] = sum(res["judges"][q]["verdict"] == SAME for q, *_ in QUESTIONS)
    return res


# ════════════════════ 読む ════════════════════

def load(codes, fetch):
    parts, missing, drops, shape = [], [], {"n": 0}, {}
    for i, code in enumerate(codes):
        d = fetch(code, "1d", jp_bars.FULL_DAILY)
        if not d:
            missing.append(code)
            continue
        daily = sorted({t.date().isoformat(): (t.date().isoformat(), o, h, lo, c, v) for t, o, h, lo, c, v in d}.values())
        TP.add_shape(shape, daily)
        parts.append(stock_rows(i, daily, drops=drops))
        if (i + 1) % 500 == 0:
            print(f"  ...{i + 1}/{len(codes)}", flush=True)
    A = np.vstack(parts) if parts else np.zeros((0, len(COLS)))
    return A, missing, drops, shape


def usable(A, shape):
    return TP.usable_start(shape, TP.thin_by_year(era(A, E1)))


def check_summary(A, missing, shape, n_codes, store):
    """点検だけ＝行数・使える年・組ごとの件数（損益は数えない）"""
    u = usable(A, shape)
    out = {"n_codes": n_codes, "missing_daily": len(missing), "rows": int(len(A)), "store": store,
           "usable_start_e1": u["start"], "bad_years": u["bad_years"], "eras": {}}
    spans = {"e1": (u["start"] or E1[0], E1[1]), "e2": E2}
    for key, _n in ERAS:
        B, idio = PG.idio_gap(era(A, spans[key]))
        out["eras"][key] = {"rows": int(len(B)), "days": int(len(np.unique(B[:, C["day"]]))),
                            "groups": {q: [int((g == k).sum()) for k in range(2)]
                                       for q, g in ((q, groups(q, B, idio)) for q, *_ in QUESTIONS)}}
    return out


# ════════════════════ 書く ════════════════════

def _p(x, d=2):
    return Y._pct(x, d)


def _band(m):
    return "—" if m.get("lo") is None else f"{_p(m['lo'])}〜{_p(m['hi'])}"


def render_md(res):
    L = ["# J26 J22 の「寄りのあと下げやすい」目印は、昔の2つの時代でも同じ向きか", "",
         f"更新: {res.get('generated_at', '')}（事前登録＝`PILLAR_PREREG.md`「J26」・指紋 `{(res.get('prereg_sha256') or '')[:12]}`）", ""]
    r = res.get("result") or {}
    if "error" in r:
        return "\n".join(L + [f"⚠️ 計算できず：{r['error']}", "", "※ 研究の記録です。投資助言ではありません。"]) + "\n"
    L += ["数字は寄り→大引けの値動きの、特徴あり − 比べる相手の平均の差（費用前）。幅は 99.375％（p＜0.05÷8・日と銘柄で引き直した広いほう）。"
          "J22 は最近の朝（9:30・10:00）だけで数えた。ここでは J22 が使っていない昔の2つの時代で同じ向きかを見る。", ""]
    for key, name in ERAS:
        e = r["eras"][key]
        L.append(f"- {name}：{e['first']}〜{e['last']}・{e['days']:,}営業日・{e['rows']:,}朝・{e['stocks']:,}銘柄")
    L += [f"- E1 の使える年の始まり：{r['start_e1']}（J18 と同じ決め方・損益は見ない）", "", "## まとめ", "",
          "| 問い | 元 | 期待 | E1 2006〜2016 | E2 2016〜2023 | まとめ |", "|---|---|---|---|---|---|"]
    for q, name, src, expected in QUESTIONS:
        j = r["judges"][q]
        cell = lambda m: f"{_p(m['value'])}（{m['direction'] or '見えない'}）"  # noqa: E731
        L.append(f"| {q} {name} | {src} | {'下' if expected < 0 else '上'} | {cell(j['e1'])} | {cell(j['e2'])} | **{j['verdict']}** |")
    L += ["", f"✅ の問い：{r['n_same']}つ（4つのうち）", ""]
    for q, name, src, expected in QUESTIONS:
        j = r["judges"][q]
        L += [f"## {q} {name}", "", "| 時代 | 件数（特徴あり／相手） | 差 | 99.375％の幅 | 前半／後半 | 特徴ありの平均（費用前／費用後） | 費用後にプラスの割合 |",
              "|---|---|---:|---|---|---|---:|"]
        for key, ename in ERAS:
            m, gs = j[key], j[key]["group"]
            win = "—" if gs["win"] is None else f"{gs['win'] * 100:.1f}％"
            L.append(f"| {ename} | {m['ns'][0]:,}／{m['ns'][1]:,} | {_p(m['value'])} | {_band(m)} | {_p(m['early'])}／{_p(m['late'])} | "
                     f"{_p(gs['mean'])}／{_p(gs['net'])} | {win} |")
        L.append("")
    L += ["## 読むための表（判定しない）", "", "### 前の日の売買代金ごとの差", ""]
    for key, ename in ERAS:
        rd = r["reading"][key]["by_turnover"]
        L += [f"#### {ename}", "", "| 売買代金 | " + " | ".join(q for q, *_ in QUESTIONS) + " |", "|---|" + "---:|" * len(QUESTIONS)]
        for lab, row in rd.items():
            L.append(f"| {lab} | " + " | ".join(f"{_p(row[q]['diff'])}（{row[q]['ns'][0]:,}）" for q, *_ in QUESTIONS) + " |")
        L.append("")
    L += ["### 売買代金の倍率の区切りを変えたとき（すべての朝）", "", "| 時代 | " + " | ".join(r["reading"]["e1"]["ratio_cuts"]) + " |",
          "|---|" + "---:|" * len(r["reading"]["e1"]["ratio_cuts"])]
    for key, ename in ERAS:
        cuts = r["reading"][key]["ratio_cuts"]
        L.append(f"| {ename} | " + " | ".join(f"{_p(c['diff'])}（{c['ns'][0]:,}）" for c in cuts.values()) + " |")
    L += ["", "### 年ごとの差", "", "| 年 | " + " | ".join(q for q, *_ in QUESTIONS) + " |", "|---|" + "---:|" * len(QUESTIONS)]
    for key, _n in ERAS:
        for y, row in r["reading"][key]["by_year"].items():
            L.append(f"| {y} | " + " | ".join(_p(row[q]["diff"]) for q, *_ in QUESTIONS) + " |")
    L += ["", "## 注意", "",
          "- いま上場している銘柄だけ（つぶれた・上場をやめた銘柄が入らない＝生き残りの偏り）。寄り→大引けは J22 の 9:30／10:00 と窓が違う",
          "- ✅ でも売買の決まりは自動では変えない。Q1 と Q4 が ✅ なら、点検表の「寄りで買わない」に足すかをオーナーに諮る（足すなら前向きを別に登録）",
          "- 空売りは数えない", "", "---", "", "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。"]
    return "\n".join(L) + "\n"


def main(argv):
    res = {"generated_at": dt.datetime.now(P.JST).isoformat(timespec="minutes"), "prereg_file": P.PREREG,
           "prereg_sha256": P.prereg_sha256(), "eras": {"e1": E1, "e2": E2}}
    try:
        stocks, list_date = jp_bars.load_universe()
        codes = sorted(stocks)
        A, missing, drops, shape = load(codes, jp_bars.fetcher())
        store = jp_bars.info()
        res["price_store"] = store
        if "--check" in argv:
            print(json.dumps(check_summary(A, missing, shape, len(codes), store), ensure_ascii=False, indent=1))
            return 0
        if not store or store.get("daily_range") != jp_bars.FULL_DAILY:
            raise RuntimeError("値段の置き場の日足が全期間版ではない（先に jp-bars-cache を回す）")
        if (store.get("fallback") or {}).get("1d", 0) > T.MAX_MISSING * len(codes):
            raise RuntimeError(f"日足を10年で取り直した銘柄が {store['fallback']['1d']}/{len(codes)}＝5％超（全期間の日足が取れていない）")
        if len(missing) > T.MAX_MISSING * len(codes):
            raise RuntimeError(f"日足を取れなかった銘柄が {len(missing)}/{len(codes)}＝5％超。偏った組で判定しない（取り直す）")
        u = usable(A, shape)
        if u["start"] is None:
            raise RuntimeError("2016年が使えない年＝E1 を数えない")
        res["result"] = dict(analyze(A, u["start"]), usable=u, n_codes=len(codes), list_date=list_date,
                             n_missing=len(missing), n_dropped=drops["n"])
    except Exception as e:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        if "--check" in argv:
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
