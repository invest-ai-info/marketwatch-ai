# -*- coding: utf-8 -*-
"""J17 2つの目印を重ねると足し算になるか：前の日の大きな上げ × その銘柄だけの今朝の窓（昔の期間と最近の期間の両方で）。
2026-10-07 登録・オーナー「続けてください」（研究の加速）。PILLAR_PREREG.md「J17」。

J15（その銘柄だけの窓）と J16（前の日の大きな上げ）は別々に出た。ここでは同じ朝に重なったとき・ぶつかったときを数える。
  N1・N4＝その銘柄だけ高く寄った朝で、前日大きく上げた − 前日ふつう
  N2・N5＝前日大きく上げた株で、その銘柄だけ高く寄った − ふつうに寄った
  N3・N6＝その銘柄だけ安く寄った朝で、前日大きく上げた − 前日ふつう
N1〜N3＝昔の期間（寄り→大引け）／N4〜N6＝最近の期間（寄り→10:00・9:30 も同じ向きか）。両方の期間が同じ向きのときだけ「✅」。

⚠️ 決まりは PILLAR_PREREG.md「J17」と下の定数に固定。行の作り方・判定・まとめ方は prevday_lab（J16）をそのまま使い、
   その銘柄だけの窓は gap_split_lab（J15）と同じ定義（その朝の全銘柄の窓の中央値を引く・500銘柄未満の朝は数えない）。
⚠️ 出力（prevgap-lab.json / .md）は集計だけ・銘柄名とコードは出さない（SYNC禁忌）。

実行: python prevgap_lab.py          （本番。Actions の prevgap-lab.yml から手動で・1回だけ）
      python prevgap_lab.py --diag   （件数とデータの形だけ。値動きは出さない・何も書き出さない）
"""
import datetime as dt
import json
import sys

import numpy as np

import gap_lab as GL
import highs_trap_lab as T
import highs_trap_small as S
import jp_bars
import pillar_lab as P
import prevday_lab as PD
import yori_lab as Y

OUT_JSON, OUT_MD = "prevgap-lab.json", "prevgap-lab.md"
C = PD.C
OLD, NEW = PD.OLD, PD.NEW
IDIO = 0.01                   # その銘柄だけの窓 ±1％
PREV_BIG = 0.05               # 前の日 +5％ 以上（−5％ 以下は読むための表だけ）
PREV_FLAT = 0.02              # 前の日 ±2％ 未満
MIN_STOCKS = 500              # その朝の銘柄がこれ未満なら、その朝は数えない
N_Q = 6
ALPHA = 0.05 / N_Q            # 99.17％ の幅
JUDGES = (("n1", "N1 その銘柄だけ高く寄った朝：前日大きく上げた − 前日ふつう（昔の期間・寄り→大引け）", "n1", OLD, "rclose"),
          ("n2", "N2 前日大きく上げた株：その銘柄だけ高く寄った − ふつうに寄った（昔の期間・寄り→大引け）", "n2", OLD, "rclose"),
          ("n3", "N3 その銘柄だけ安く寄った朝：前日大きく上げた − 前日ふつう（昔の期間・寄り→大引け）", "n3", OLD, "rclose"),
          ("n4", "N4 その銘柄だけ高く寄った朝：前日大きく上げた − 前日ふつう（最近の期間・寄り→10:00）", "n1", NEW, "r1000"),
          ("n5", "N5 前日大きく上げた株：その銘柄だけ高く寄った − ふつうに寄った（最近の期間・寄り→10:00）", "n2", NEW, "r1000"),
          ("n6", "N6 その銘柄だけ安く寄った朝：前日大きく上げた − 前日ふつう（最近の期間・寄り→10:00）", "n3", NEW, "r1000"))
PAIRS = (("n1", "n4", "重なる（今朝その銘柄だけ高く寄った朝に、前の日の大きな上げがさらに効くか）"),
         ("n2", "n5", "前の日に大きく上げた株でも、今朝その銘柄だけ高く寄ると、さらに弱いか"),
         ("n3", "n6", "ぶつかる（今朝その銘柄だけ安く寄った朝に、前の日の大きな上げが戻りを打ち消すか）"))
IDIO_LABELS = ("安く（−1％以下）", "ふつう（±1％未満）", "高く（+1％以上）")
PREV_LABELS = ("前日 −5％以下", "前日 ±2％未満", "前日 +5％以上")


def idio_gap(A):
    """→ (使う行, その銘柄だけの窓)。その朝の銘柄が MIN_STOCKS 未満の朝は除く（J15 の split と同じ定義）"""
    if not len(A):
        return A, np.zeros(0)
    day, gap = A[:, C["day"]], A[:, C["gap"]]
    order = np.argsort(day, kind="stable")
    uniq, starts, counts = np.unique(day[order], return_index=True, return_counts=True)
    med = np.array([np.median(gap[order[s:s + n]]) for s, n in zip(starts, counts)])
    idx = np.searchsorted(uniq, day)
    keep = (counts >= MIN_STOCKS)[idx]
    return A[keep], (gap - med[idx])[keep]


def bands(idio, rprev):
    """その銘柄だけの窓（0 安く・1 ふつう・2 高く）と前の日（0 −5％以下・1 ±2％未満・2 +5％以上・−1 それ以外）"""
    ib = np.where(idio <= -IDIO, 0, np.where(idio >= IDIO, 2, 1))
    pb = np.where(rprev >= PREV_BIG, 2, np.where(rprev <= -PREV_BIG, 0, np.where(np.abs(rprev) < PREV_FLAT, 1, -1)))
    return ib, pb


def groups(idio, rprev, kind):
    """各行の組（先に書いた組＝0・比べる相手＝1・それ以外＝−1）"""
    ib, pb = bands(idio, rprev)
    if kind == "n1":
        return GL.pair_grp((ib == 2) & (pb == 2), (ib == 2) & (pb == 1))
    if kind == "n2":
        return GL.pair_grp((ib == 2) & (pb == 2), (ib == 1) & (pb == 2))
    if kind == "n3":
        return GL.pair_grp((ib == 0) & (pb == 2), (ib == 0) & (pb == 1))
    raise ValueError(kind)


def _diff(v, g):
    a, b = v[g == 0], v[g == 1]
    return float(a.mean() - b.mean()) if len(a) and len(b) else None


def measure(A, grp, col, alpha=ALPHA):
    """J16 の measure と同じ物差し（組だけ外から渡す）"""
    val = A[:, C[col]]
    ok = np.isfinite(val)
    g = np.where(ok, grp, -1)
    ns = [int((g == 0).sum()), int((g == 1).sum())]
    out = {"ns": ns, "diff": None, "lo": None, "hi": None}
    if min(ns) == 0:
        return out
    pt, lo_d, hi_d = GL.boot(val, g, 2, A[:, C["day"]], GL._diff2, alpha)
    _, lo_c, hi_c = GL.boot(val, g, 2, A[:, C["code"]], GL._diff2, alpha)
    days = np.unique(A[ok, C["day"]])
    cut = days[len(days) // 2]
    early, late = A[:, C["day"]] < cut, A[:, C["day"]] >= cut
    out.update(diff=pt, by_day=[lo_d, hi_d], by_stock=[lo_c, hi_c], cut=dt.date.fromordinal(int(cut)).isoformat(),
               early=_diff(val[early], g[early]), late=_diff(val[late], g[late]),
               mean_a_cost=float(val[g == 0].mean() - T.COST), mean_b_cost=float(val[g == 1].mean() - T.COST))
    if col == "r1000":
        v9 = A[:, C["r930"]]
        g9 = np.where(np.isfinite(v9), grp, -1)
        out["d60"] = {"ns": [int((g9 == 0).sum()), int((g9 == 1).sum())], "diff": _diff(v9, g9)}
    if None not in (lo_d, lo_c, hi_d, hi_c):
        out.update(lo=min(lo_d, lo_c), hi=max(hi_d, hi_c))
    return out


def _m(v):
    """平均（30件未満は None＝表では「—」）"""
    out = GL._mean(v)
    if out["n"] < T.MIN_N:
        out["mean"] = None
    return out


def _cell_table(x, idio, col):
    ib, pb = bands(idio, x[:, C["rprev"]])
    v = x[:, C[col]]
    return {IDIO_LABELS[i]: {PREV_LABELS[p]: _m(v[(ib == i) & (pb == p)]) for p in (2, 1, 0)} for i in (2, 1, 0)}


def _extra(tab):
    """重なりの上乗せ＝(高く×上げた − 高く×ふつう) − (ふつう×上げた − ふつう×ふつう)"""
    hi, mid = tab[IDIO_LABELS[2]], tab[IDIO_LABELS[1]]
    vals = [hi[PREV_LABELS[2]].get("mean"), hi[PREV_LABELS[1]].get("mean"), mid[PREV_LABELS[2]].get("mean"), mid[PREV_LABELS[1]].get("mean")]
    if None in vals:
        return None
    return float((vals[0] - vals[1]) - (vals[2] - vals[3]))


def analyze(A):
    A, idio = idio_gap(A)
    d = A[:, C["day"]]
    spans = {name: (d >= PD._ord(sp[0])) & (d <= PD._ord(sp[1])) for name, sp in (("old", OLD), ("new", NEW))}
    res = {"judges": {}}
    for key, name, kind, span, col in JUDGES:
        m = spans["old" if span == OLD else "new"]
        sub, si = A[m], idio[m]
        q = measure(sub, groups(si, sub[:, C["rprev"]], kind), col)
        q.update(name=name, verdict=PD.judge(q))
        res["judges"][key] = q
    J = res["judges"]
    res["summary"] = {a: {"label": lab, "verdict": PD.summary(J[a]["verdict"], J[b]["verdict"])} for a, b, lab in PAIRS}
    res["periods"] = {name: {"rows": int(m.sum()), "days": int(len(np.unique(d[m])))} for name, m in spans.items()}
    # ── 読むための表（判定しない）──
    res["cells"] = {name: _cell_table(A[m], idio[m], col) for (name, m), col in zip(spans.items(), ("rclose", "r1000"))}
    res["extra"] = {name: _extra(t) for name, t in res["cells"].items()}
    old, oi = A[spans["old"]], idio[spans["old"]]
    tv, rp, v = old[:, C["turnover"]], old[:, C["rprev"]], old[:, C["rclose"]]
    res["by_turnover_old"] = {}
    for lab, lo, hi in S.TURNOVER_BANDS:
        mb = (tv >= lo) & (tv < hi)
        row = {}
        for kind in ("n1", "n2", "n3"):
            g = groups(oi, rp, kind)
            g = np.where(mb, g, -1)
            ns = [int((g == 0).sum()), int((g == 1).sum())]
            row[kind] = {"diff": _diff(v, g) if min(ns) >= T.MIN_N else None, "ns": ns}
        res["by_turnover_old"][lab] = row
    return res


def diag_summary(A, missing, n_codes):
    B, idio = idio_gap(A)
    out = {"n_codes": n_codes, "missing": {k: len(v) for k, v in missing.items()}, "rows": int(len(A)), "rows_kept": int(len(B))}
    d = B[:, C["day"]]
    for key, name, kind, span, col in JUDGES:
        m = (d >= PD._ord(span[0])) & (d <= PD._ord(span[1]))
        sub = B[m]
        g = groups(idio[m], sub[:, C["rprev"]], kind)
        ok = np.isfinite(sub[:, C[col]])
        out[key] = {"days": int(len(np.unique(sub[:, C["day"]]))) if len(sub) else 0,
                    "sizes": [int(((g == 0) & ok).sum()), int(((g == 1) & ok).sum())]}
        if col == "r1000":
            ok9 = np.isfinite(sub[:, C["r930"]])
            out[key]["sizes_930"] = [int(((g == 0) & ok9).sum()), int(((g == 1) & ok9).sum())]
    return out


def _p(x, d=2):
    return Y._pct(x, d)


def render_md(res):
    L = ["# J17 2つの目印を重ねると足し算になるか：前の日の大きな上げ × その銘柄だけの今朝の窓", "",
         f"作成: {res['generated_at']}（GitHub Actions で計算）。事前登録＝`{P.PREREG}`「J17」（指紋 sha256 `{(res.get('prereg_sha256') or '')[:16]}…`）。",
         "銘柄名は出しません。値は株価の変化率（％）。**売買の決まりではない**。", ""]
    r = res.get("result") or {}
    if r.get("error"):
        return "\n".join(L + [f"- ⚠️ 計算できず: {r['error']}", ""]) + "\n"
    ps = res.get("price_store") or {}
    pe = r["periods"]
    L += [f"- 対象：置き場の一覧 {r.get('n_codes')}銘柄（一覧 {r.get('list_date')}・いま上場している銘柄だけ）。取れなかった銘柄 {r.get('n_missing')}。値段の置き場：{ps.get('built_at') or '使わず'}",
          f"- 昔の期間 {OLD[0]}〜{OLD[1]}：{pe['old']['days']}営業日・{pe['old']['rows']:,}朝／最近の期間 {NEW[0]}〜{NEW[1]}：{pe['new']['days']}営業日・{pe['new']['rows']:,}朝"
          f"（その朝の銘柄が{MIN_STOCKS}未満の朝は除いた）",
          "- その銘柄だけの窓＝今朝の窓 − その朝の全銘柄の窓の中央値。前日大きく上げた＝+5％以上・前日ふつう＝±2％未満",
          f"- 幅は99.17％（p＜0.05÷6）・日と銘柄で引き直した広いほう。±25％超で捨てた値 {r.get('n_dropped')}",
          "", "## まとめ（昔と最近の組ごと）", ""]
    for a, b, lab in PAIRS:
        L.append(f"- **{lab}**：{r['summary'][a]['verdict']}")
    L += ["", "## 判定（事前登録の6つ）", ""]
    for key, *_ in JUDGES:
        q = r["judges"][key]
        extra = f"・5分足の寄り→9:30 の差 {_p(q['d60']['diff'])}（{q['d60']['ns'][0]:,}対{q['d60']['ns'][1]:,}）" if "d60" in q else ""
        L.append(f"- **{q['name']}**：差 {_p(q.get('diff'))}（幅 {_p(q.get('lo'))}〜{_p(q.get('hi'))}・{q['ns'][0]:,}対{q['ns'][1]:,}回）・"
                 f"前半 {_p(q.get('early'))}／後半 {_p(q.get('late'))}・先の組の費用後 {_p(q.get('mean_a_cost'))}（比べる相手 {_p(q.get('mean_b_cost'))}）{extra} → **{q['verdict']}**")
    L += ["", "## 読むための表（判定しない）", ""]
    for name, title in (("old", "昔の期間・寄り→大引け"), ("new", "最近の期間・寄り→10:00")):
        t = r["cells"][name]
        L += [f"### その銘柄だけの窓 × 前の日の値動きの平均（{title}・費用なし）", "",
              "| その銘柄だけの窓 | " + " | ".join(PREV_LABELS[p] for p in (2, 1, 0)) + " |", "|---|---:|---:|---:|"]
        for il, row in t.items():
            L.append(f"| {il} | " + " | ".join(f"{_p(row[PREV_LABELS[p]].get('mean'))}（{row[PREV_LABELS[p]]['n']:,}）" for p in (2, 1, 0)) + " |")
        L += [f"- 重なりの上乗せ＝(高く×上げた − 高く×ふつう) − (ふつう×上げた − ふつう×ふつう)：{_p(r['extra'][name])}", ""]
    L += ["### 売買代金ごとの差（昔の期間・寄り→大引け）", "", "| 売買代金 | N1 高く寄った朝の前日上げ | N2 前日上げた株の高い寄り | N3 安く寄った朝の前日上げ |", "|---|---:|---:|---:|"]
    for lab, row in r["by_turnover_old"].items():
        L.append(f"| {lab} | " + " | ".join(f"{_p(row[k]['diff'])}（{row[k]['ns'][0]:,}）" for k in ("n1", "n2", "n3")) + " |")
    L += ["", "- 30件未満の区分は「—」。表の（）は件数（売買代金の表は先の組の件数）。小さい株は売り買いの差が大きく、費用 0.1％ は甘い（判定は差なので費用は消える）。空売りは数えない。",
          "", "---", "", "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。"]
    return "\n".join(L) + "\n"


def main(argv):
    res = {"generated_at": dt.datetime.now(P.JST).isoformat(timespec="minutes"), "prereg_file": P.PREREG,
           "prereg_sha256": P.prereg_sha256(), "old": OLD, "new": NEW}
    try:
        stocks, list_date = jp_bars.load_universe()
        codes = sorted(stocks)
        A, missing, drops = PD.load(codes, jp_bars.fetcher())
        res["price_store"] = jp_bars.info()
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
