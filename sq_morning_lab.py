# -*- coding: utf-8 -*-
"""J43 SQの日（毎月の第2金曜日）の朝は特別か：寄りの窓の戻しと「寄りで買わない」目印を、ほかの金曜日と比べる。
2026-10-09 登録・オーナー「1と2を進めてください」。PILLAR_PREREG.md「J43」。

きっかけ＝2026-10-09（10月のオプションSQの日）の朝、8:55〜8:58 の気配が寄り値と大きくずれた。SQ の日は、SQ の値に合わせる
注文が寄りに集まり、寄りの値が需給でゆがむと言われる。ゆがんだ寄りなら寄りのあとに戻しやすいはず＝点検表の目印（A・B・C）と
「安く寄った株」の寄り→大引けが、SQ の日だけ違うかを、3つの時代の日足で1回だけ数える。

値＝相場全体を引いた寄り→大引け（その銘柄の寄り→大引け − その朝に数えた全銘柄の寄り→大引けの中央値）。
差＝目印の株の値の平均の、SQ の日 − SQ の日でない金曜日（曜日の癖を消す）。向きは両側で見る。

⚠️ 決まりは PILLAR_PREREG.md「J43」と下の定数に固定。行は prevday_lab（J16）、売買代金の倍率は landmine_lab.prev_more、
   その銘柄だけの窓は prevgap_lab.idio_gap、幅と向きは open30_lab（J22）の measure・direction、SQ の日は sq_week_lab.nth_friday。
⚠️ 出力（sq-morning-lab.json / .md）は集計だけ・銘柄名とコードは出さない（SYNC禁忌）。

実行: python sq_morning_lab.py --check   （点検だけ＝行数・SQ の日の数・組ごとの件数。損益は数えない・何も書き出さない）
      python sq_morning_lab.py           （本番。Actions の sq-morning-lab.yml から手動で・1回だけ）
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
import sq_week_lab as SW
import third_period_lab as TP
import yori_lab as Y

OUT_JSON, OUT_MD = "sq-morning-lab.json", "sq-morning-lab.md"
E1, E2, E3 = TP.SPAN, PD.OLD, PD.NEW       # 2006-01-04〜2016-10-31／2016-11-01〜2023-09-29／2023-10-10〜2026-10-05
ERAS = (("e1", "E1 2006〜2016年"), ("e2", "E2 2016〜2023年"), ("e3", "E3 2023〜2026年"))
COLS = PD.COLS + ("tv_ratio",)
C = {k: i for i, k in enumerate(COLS)}
IDIO = PG.IDIO                             # その銘柄だけの窓 ±1％
PREV_BIG = PD.PREV_BIG                     # 前の日 +5％以上
TV_HIGH = 5.0                              # 目印C：前の日の売買代金が20営業日平均の5倍以上
SQ_NTH = 2                                 # 第2金曜日
FRIDAY = 4                                 # date.weekday() の金曜日
MAJOR = SW.MAJOR                           # 3・6・9・12月＝メジャーSQ（読むための表だけ）
N_Q = 12                                   # 4つの問い × 3つの時代
ALPHA = 0.05 / N_Q                         # 99.583％ の幅
UP, DOWN = O.UP, O.DOWN
SAME, TWO, OPP, NONE = "✅ 3つの時代とも同じ向き", "△ 2つの時代で同じ向き（もう1つは見えない）", "⚠️ 逆向きの時代がある", "見えない"
KIND_SQ, KIND_FRI = 1, 2                   # 行の日：1＝SQ の日・2＝SQ の日でない金曜日・0＝それ以外
# (問い, 目印, 仮説の向き：+1 上・−1 下・0 なし)
QUESTIONS = (("Q1", "目印A その銘柄だけ +1％以上高く寄った株", -1),
             ("Q2", "その銘柄だけ −1％以下安く寄った株", +1),
             ("Q3", "目印B 前の日 +5％以上かつ、その銘柄だけ +1％以上高く寄った株", -1),
             ("Q4", "目印C 前の日の売買代金が20営業日平均の5倍以上の株", 0))


# ════════════════════ 行 ════════════════════

def stock_rows(ci, daily, drops=None):
    """J16 の行（2006-01-04〜2026-10-05・寄り→大引け）＋前の日の売買代金の倍率"""
    A = PD.stock_rows(ci, daily, {}, {}, first=E1[0], last=E3[1], recent_from="2100-01-01", drops=drops)
    if not len(A):
        return np.zeros((0, len(COLS)))
    ratio = LM.prev_more(daily)[0]
    pos = {dt.date.fromisoformat(r[0]).toordinal(): i for i, r in enumerate(daily)}
    k = np.array([pos[int(o)] for o in A[:, C["day"]]]) - 1
    return np.hstack([A, ratio[k].reshape(-1, 1)])


# ════════════════════ SQ の日 ════════════════════

def sq_days(trading):
    """→ {SQ の日の通し番号: 月}。第2金曜日。その日が取引日でなければ、その前の取引日（繰り上げ・同じ月の中だけ）"""
    days = np.unique(np.asarray(trading, dtype=np.int64))
    if not len(days):
        return {}
    first, last = dt.date.fromordinal(int(days[0])), dt.date.fromordinal(int(days[-1]))
    out = {}
    for y in range(first.year, last.year + 1):
        for m in range(1, 13):
            f = SW.nth_friday(y, m, SQ_NTH).toordinal()
            if f < days[0] or f > days[-1]:
                continue
            i = int(np.searchsorted(days, f, side="right")) - 1     # f 以下でいちばん近い取引日
            if i >= 0 and dt.date.fromordinal(int(days[i])).month == m:
                out[int(days[i])] = m
    return out


def weekday(day):
    """通し番号（date.toordinal）の曜日。0001-01-01 は月曜日"""
    return (np.asarray(day, dtype=np.int64) - 1) % 7


def day_kind(A, sq):
    d = A[:, C["day"]].astype(np.int64)
    is_sq = np.isin(d, np.fromiter(sq, dtype=np.int64, count=len(sq))) if sq else np.zeros(len(d), bool)
    return np.where(is_sq, KIND_SQ, np.where(weekday(d) == FRIDAY, KIND_FRI, 0))


def day_median(day, x):
    """→ (日の並び, その日の中央値, 各行のその日の中央値)"""
    order = np.argsort(day, kind="stable")
    uniq, starts, counts = np.unique(day[order], return_index=True, return_counts=True)
    med = np.array([np.median(x[order[s:s + n]]) for s, n in zip(starts, counts)])
    return uniq, med, med[np.searchsorted(uniq, day)]


def adjusted(A):
    """相場全体を引いた寄り→大引け＝その銘柄の寄り→大引け − その朝に数えた全銘柄の寄り→大引けの中央値"""
    r = A[:, C["rclose"]]
    _, _, row_med = day_median(A[:, C["day"]], r)
    return r - row_med


# ════════════════════ 組と判定 ════════════════════

def feature(key, A, idio):
    rprev, tv = A[:, C["rprev"]], A[:, C["tv_ratio"]]
    with np.errstate(invalid="ignore"):
        if key == "Q1":
            return idio >= IDIO
        if key == "Q2":
            return idio <= -IDIO
        if key == "Q3":
            return (rprev >= PREV_BIG) & (idio >= IDIO)
        if key == "Q4":
            return tv >= TV_HIGH                 # NaN（20日そろう前）は入れない
    raise ValueError(key)


def groups(key, A, idio, kind, sq_sel=None):
    """各行の組（SQ の日の目印の株＝0・SQ の日でない金曜日の目印の株＝1・それ以外＝−1）。sq_sel で SQ の日を絞る（読むための表）"""
    f = feature(key, A, idio)
    sq = kind == KIND_SQ if sq_sel is None else (kind == KIND_SQ) & sq_sel
    return GL.pair_grp(f & sq, f & (kind == KIND_FRI))


def era(A, span):
    d = A[:, C["day"]]
    return A[(d >= PD._ord(span[0])) & (d <= PD._ord(span[1]))]


def sign(direction):
    return -1 if direction == DOWN else +1 if direction == UP else 0


def verdict(signs):
    if +1 in signs and -1 in signs:
        return OPP
    hit = sum(1 for s in signs if s)
    return SAME if hit == len(signs) else TWO if hit == 2 else NONE


def lean(signs):
    """✅・△ のときの向き（+1 上・−1 下）。それ以外は 0"""
    nz = {s for s in signs if s}
    return nz.pop() if len(nz) == 1 and verdict(signs) in (SAME, TWO) else 0


def vs_hypothesis(signs, expected):
    w = lean(signs)
    if not w or not expected:
        return ""
    return "仮説どおり" if w == expected else "仮説と逆"


def _raw(r, g):
    """目印の株の素の寄り→大引け（費用前・往復0.1％を引いた後）：SQ の日／ほかの金曜日"""
    out = {}
    for k, lab in ((0, "sq"), (1, "fri")):
        a = r[(g == k) & np.isfinite(r)]
        out[lab] = {"n": int(len(a)), "mean": None, "net": None} if len(a) < T.MIN_N else \
            {"n": int(len(a)), "mean": float(a.mean()), "net": float(a.mean() - T.COST)}
    return out


def _plain(v, g):
    fin = np.isfinite(v)
    ns = [int(((g == k) & fin).sum()) for k in range(2)]
    return {"ns": ns, "diff": PG._diff(v[fin], g[fin]) if min(ns) >= T.MIN_N else None}


def _market(uniq, med_r, med_g, kinds):
    """相場全体（その朝の中央値）：SQ の日とほかの金曜日の、寄り→大引けの平均・上げた日の割合・窓の大きさ（絶対値）の平均"""
    out = {}
    for k, lab in ((KIND_SQ, "sq"), (KIND_FRI, "fri")):
        m = kinds == k
        out[lab] = {"days": int(m.sum()),
                    "rclose": float(med_r[m].mean()) if m.any() else None,
                    "up_share": float((med_r[m] > 0).mean()) if m.any() else None,
                    "abs_gap": float(np.abs(med_g[m]).mean()) if m.any() else None}
    return out


def _prepare(A, span, sq):
    B, idio = PG.idio_gap(era(A, span))
    kind = day_kind(B, sq)
    return B, idio, adjusted(B), kind


def analyze(A, start):
    spans = {"e1": (start, E1[1]), "e2": E2, "e3": E3}
    sq = sq_days(A[:, C["day"]])
    res = {"start_e1": start, "eras": {}, "judges": {}, "reading": {}}
    per = {}
    for key, _name in ERAS:
        B, idio, v, kind = _prepare(A, spans[key], sq)
        days = np.unique(B[:, C["day"]])
        sq_in = sorted({int(d) for d in B[kind == KIND_SQ, C["day"]]})
        res["eras"][key] = {"rows": int(len(B)), "days": int(len(days)), "stocks": int(len(np.unique(B[:, C["code"]]))),
                            "first": dt.date.fromordinal(int(days[0])).isoformat() if len(days) else None,
                            "last": dt.date.fromordinal(int(days[-1])).isoformat() if len(days) else None,
                            "sq_days": len(sq_in), "sq_major": sum(1 for d in sq_in if sq[d] in MAJOR),
                            "fridays": int(len(np.unique(B[kind == KIND_FRI, C["day"]])))}
        per[key] = (B, idio, v, kind)
    for q, name, expected in QUESTIONS:
        out = {"name": name, "expected": expected}
        signs = []
        for key, _n in ERAS:
            B, idio, v, kind = per[key]
            g = groups(q, B, idio, kind)
            m = O.measure(B, v, g, ALPHA)
            m["direction"] = O.direction(m)
            m["raw"] = _raw(B[:, C["rclose"]], g)
            out[key] = m
            signs.append(sign(m["direction"]))
        out["verdict"] = verdict(signs)
        out["lean"] = lean(signs)
        out["vs_hypothesis"] = vs_hypothesis(signs, expected)
        res["judges"][q] = out
    # ── 読むための表（判定しない）──
    for key, _n in ERAS:
        B, idio, v, kind = per[key]
        d = B[:, C["day"]].astype(np.int64)
        major = np.isin(d, np.array([x for x, mo in sq.items() if mo in MAJOR], dtype=np.int64))
        tv = B[:, C["turnover"]]
        ud, inv = np.unique(d, return_inverse=True)
        years = np.array([dt.date.fromordinal(int(o)).year for o in ud], dtype=np.int64)[inv]
        grps = {q: groups(q, B, idio, kind) for q, *_ in QUESTIONS}
        uniq, med_r, _ = day_median(B[:, C["day"]], B[:, C["rclose"]])
        _, med_g, _ = day_median(B[:, C["day"]], B[:, C["gap"]])
        kinds = np.array([KIND_SQ if int(u) in sq else KIND_FRI if weekday(int(u)) == FRIDAY else 0 for u in uniq])
        res["reading"][key] = {
            "major": {q: {"major": _plain(v, groups(q, B, idio, kind, major)), "other": _plain(v, groups(q, B, idio, kind, ~major))}
                      for q, *_ in QUESTIONS},
            "by_turnover": {lab: {q: _plain(v, np.where((tv >= lo) & (tv < hi), g, -1)) for q, g in grps.items()}
                            for lab, lo, hi in S.TURNOVER_BANDS},
            "market": _market(uniq, med_r, med_g, kinds),
            "by_year": {str(y): {q: _plain(v, np.where(years == y, g, -1)) for q, g in grps.items()} for y in np.unique(years)}}
    res["n_same"] = sum(res["judges"][q]["verdict"] == SAME for q, *_ in QUESTIONS)
    return res


def verdicts_of(result, today):
    """検証済みリストが読む欄：見えない問いだけ stop として載せる（PREREG「J43」の読み方の約束）。数字は E2 2016〜2023年"""
    out = {}
    for q, *_ in QUESTIONS:
        j = result["judges"][q]
        if j["verdict"] != NONE:
            continue
        m = j["e2"]
        out[q] = {"status": "stop", "decided_on": today, "n": m["ns"][0], "mean": m["value"], "lo": m["lo"], "hi": m["hi"],
                  "reason": "過去のデータで1回だけ数えて差なし（SQ の日 − ほかの金曜日・相場全体を引いた寄り→大引け・2016〜2023年の数字）"}
    return out


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
    """点検だけ＝行数・使える年・SQ の日の数・組ごとの件数（損益は数えない）"""
    u = usable(A, shape)
    sq = sq_days(A[:, C["day"]]) if len(A) else {}
    out = {"n_codes": n_codes, "missing_daily": len(missing), "rows": int(len(A)), "store": store,
           "usable_start_e1": u["start"], "bad_years": u["bad_years"], "eras": {}}
    spans = {"e1": (u["start"] or E1[0], E1[1]), "e2": E2, "e3": E3}
    for key, _n in ERAS:
        B, idio = PG.idio_gap(era(A, spans[key]))
        kind = day_kind(B, sq)
        out["eras"][key] = {"rows": int(len(B)), "days": int(len(np.unique(B[:, C["day"]]))),
                            "sq_days": int(len(np.unique(B[kind == KIND_SQ, C["day"]]))),
                            "fridays": int(len(np.unique(B[kind == KIND_FRI, C["day"]]))),
                            "groups": {q: [int((g == k).sum()) for k in range(2)]
                                       for q, g in ((q, groups(q, B, idio, kind)) for q, *_ in QUESTIONS)}}
    return out


# ════════════════════ 書く ════════════════════

def _p(x, d=2):
    return Y._pct(x, d)


def _band(m):
    return "—" if m.get("lo") is None else f"{_p(m['lo'])}〜{_p(m['hi'])}"


def _dir(m):
    return "上がりやすい" if m.get("direction") == UP else "下がりやすい" if m.get("direction") == DOWN else "見えない"


def _hyp(expected):
    return "下" if expected < 0 else "上" if expected > 0 else "なし"


def _summary(j):
    if j["verdict"] in (SAME, TWO):
        w = "上向き" if j["lean"] > 0 else "下向き"
        return f"{j['verdict']}（{w}{'・' + j['vs_hypothesis'] if j['vs_hypothesis'] else ''}）"
    return j["verdict"]


def render_md(res):
    L = ["# J43 SQの日（毎月の第2金曜日）の朝は特別か：寄りの窓の戻しと「寄りで買わない」目印", "",
         f"更新: {res.get('generated_at', '')}（事前登録＝`PILLAR_PREREG.md`「J43」・指紋 `{(res.get('prereg_sha256') or '')[:12]}`）", ""]
    r = res.get("result") or {}
    if "error" in r:
        return "\n".join(L + [f"⚠️ 計算できず：{r['error']}", "", "※ 研究の記録です。投資助言ではありません。"]) + "\n"
    L += ["数字は**相場全体を引いた寄り→大引け**（その銘柄の寄り→大引け − その朝の全銘柄の中央値）の、目印の株の平均の "
          "**SQ の日 − SQ の日でない金曜日**（費用前）。SQ の日＝第2金曜日（休みなら前の取引日）。"
          "幅は 99.583％（p＜0.05÷12・日と銘柄で引き直した広いほう）。向きは両側で見る。", ""]
    for key, name in ERAS:
        e = r["eras"][key]
        L.append(f"- {name}：{e['first']}〜{e['last']}・{e['days']:,}営業日（SQ の日 {e['sq_days']}日〔うちメジャーSQ {e['sq_major']}日〕・"
                 f"ほかの金曜日 {e['fridays']}日）・{e['rows']:,}朝・{e['stocks']:,}銘柄")
    L += [f"- E1 の使える年の始まり：{r['start_e1']}（J18 と同じ決め方・損益は見ない）", "", "## まとめ", "",
          "| 問い | 仮説 | E1 2006〜2016 | E2 2016〜2023 | E3 2023〜2026 | まとめ |", "|---|---|---|---|---|---|"]
    for q, name, expected in QUESTIONS:
        j = r["judges"][q]
        cell = lambda m: f"{_p(m['value'])}（{_dir(m)}）"  # noqa: E731
        L.append(f"| {q} {name} | {_hyp(expected)} | {cell(j['e1'])} | {cell(j['e2'])} | {cell(j['e3'])} | **{_summary(j)}** |")
    L += ["", f"✅ の問い：{r['n_same']}つ（4つのうち）", ""]
    for q, name, expected in QUESTIONS:
        j = r["judges"][q]
        L += [f"## {q} {name}", "",
              "| 時代 | 件数（SQ の日／ほかの金曜日） | 差 | 99.583％の幅 | 前半／後半 | 素の寄り→大引け SQ の日（費用前／費用後） | ほかの金曜日（費用前／費用後） |",
              "|---|---|---:|---|---|---|---|"]
        for key, ename in ERAS:
            m, raw = j[key], j[key]["raw"]
            L.append(f"| {ename} | {m['ns'][0]:,}／{m['ns'][1]:,} | {_p(m['value'])} | {_band(m)} | {_p(m['early'])}／{_p(m['late'])} | "
                     f"{_p(raw['sq']['mean'])}／{_p(raw['sq']['net'])} | {_p(raw['fri']['mean'])}／{_p(raw['fri']['net'])} |")
        L.append("")
    L += ["## 読むための表（判定しない）", "", "### メジャーSQ（3・6・9・12月）とそれ以外の月の SQ", "",
          "| 時代 | " + " | ".join(f"{q} メジャー／それ以外" for q, *_ in QUESTIONS) + " |", "|---|" + "---|" * len(QUESTIONS)]
    for key, ename in ERAS:
        rd = r["reading"][key]["major"]
        L.append(f"| {ename} | " + " | ".join(f"{_p(rd[q]['major']['diff'])}／{_p(rd[q]['other']['diff'])}" for q, *_ in QUESTIONS) + " |")
    L += ["", "### 前の日の売買代金ごとの差", ""]
    for key, ename in ERAS:
        rd = r["reading"][key]["by_turnover"]
        L += [f"#### {ename}", "", "| 売買代金 | " + " | ".join(q for q, *_ in QUESTIONS) + " |", "|---|" + "---:|" * len(QUESTIONS)]
        for lab, row in rd.items():
            L.append(f"| {lab} | " + " | ".join(f"{_p(row[q]['diff'])}（{row[q]['ns'][0]:,}）" for q, *_ in QUESTIONS) + " |")
        L.append("")
    L += ["### 相場全体（その朝の全銘柄の中央値）", "",
          "| 時代 | 日の数（SQ の日／ほかの金曜日） | 寄り→大引けの平均 | 上げた日の割合 | 窓の大きさ（絶対値）の平均 |", "|---|---|---|---|---|"]
    for key, ename in ERAS:
        mk = r["reading"][key]["market"]
        sq, fr = mk["sq"], mk["fri"]
        share = lambda x: "—" if x is None else f"{x * 100:.0f}％"  # noqa: E731
        L.append(f"| {ename} | {sq['days']}／{fr['days']} | {_p(sq['rclose'])}／{_p(fr['rclose'])} | {share(sq['up_share'])}／{share(fr['up_share'])} | "
                 f"{_p(sq['abs_gap'])}／{_p(fr['abs_gap'])} |")
    L += ["", "### 年ごとの差", "", "| 年 | " + " | ".join(q for q, *_ in QUESTIONS) + " |", "|---|" + "---:|" * len(QUESTIONS)]
    for key, _n in ERAS:
        for y, row in r["reading"][key]["by_year"].items():
            L.append(f"| {y} | " + " | ".join(_p(row[q]["diff"]) for q, *_ in QUESTIONS) + " |")
    L += ["", "## 注意", "",
          "- いま上場している銘柄だけ（つぶれた・上場をやめた銘柄が入らない＝生き残りの偏り）。SQ の日は1つの時代に約36〜130日しかない＝幅が広い",
          "- 寄り前の気配そのもの（寄り値とのずれ）は日足に無いので数えていない。数えたのは寄ったあとの動きだけ",
          "- 日経平均の採用銘柄の移り変わりを持っていないので全銘柄で数えた（読むための表の売買代金10億円以上が、採用銘柄に近い）",
          "- ✅ でも売買の決まりは自動では変えない。Q1 か Q3 が ✅ で仮説どおり（下）なら、点検表⑤への書き足しをオーナーに諮る",
          "- 空売りは数えない", "", "---", "", "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。"]
    return "\n".join(L) + "\n"


def main(argv):
    res = {"generated_at": dt.datetime.now(P.JST).isoformat(timespec="minutes"), "prereg_file": P.PREREG,
           "prereg_sha256": P.prereg_sha256(), "eras": {"e1": E1, "e2": E2, "e3": E3}}
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
        today = dt.datetime.now(P.JST).date().isoformat()
        res.update(kind="backtest", section="J43",
                   titles={q: f"SQの日の朝：{name}（相場全体を引いた寄り→大引け・SQ の日 − ほかの金曜日・2006〜2026-10・1回だけ数えた）"
                           for q, name, _ in QUESTIONS},
                   verdicts=verdicts_of(res["result"], today))
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
