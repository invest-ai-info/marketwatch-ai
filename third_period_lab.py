# -*- coding: utf-8 -*-
"""J18 これまでの目印を、まだ使っていない3つ目の期間（2006〜2016年）で確かめる。
2026-10-07 登録・オーナー「続けてください」（研究の加速）。PILLAR_PREREG.md「J18」。

J13〜J17 の目印は 2016-11〜2026-10 だけで数えた。値段の置き場の日足を取れる全期間に広げ、2006-01〜2016-10 を寄り→大引けで1回だけ数える。
  P1・P2＝J15 K1・K2（その銘柄だけの窓）／P3＝J16 M1（前日 +5％以上・今朝ふつう）／P4〜P6＝J17 N1〜N3（重なる・ぶつかる）
  P7＝新しい問い（その銘柄だけ安く寄った朝で、前日 −5％以下 − 前日ふつう）
元と同じ向きの兆しなら「✅ 3つ目の期間でも同じ向き」。使える年はデータの形だけで機械的に決める（損益は見ない）。

⚠️ 決まりは PILLAR_PREREG.md「J18」と下の定数に固定。行の作り方・判定は prevday_lab（J16）、その銘柄だけの窓・組・幅は prevgap_lab（J17）をそのまま使う。
⚠️ 出力（third-period-lab.json / .md）は集計だけ・銘柄名とコードは出さない（SYNC禁忌）。

実行: python third_period_lab.py --check   （点検だけ＝データの形と使える年。損益は数えない・何も書き出さない）
      python third_period_lab.py           （本番。Actions の third-period-lab.yml から手動で・1回だけ）
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
import prevgap_lab as PG
import yori_lab as Y

OUT_JSON, OUT_MD = "third-period-lab.json", "third-period-lab.md"
C = PD.C
SPAN = ("2006-01-04", "2016-10-31")
REF_YEARS = tuple(range(2017, 2026))     # 始値の欠けの疑いの割合を比べる年（2017〜2025）
OC_RATIO = 2.0                           # 割合がこの倍を超える年は使えない
THIN_SHARE = 0.5                         # 500銘柄未満の朝がこの割合を超える年は使えない
MIN_STOCKS = PG.MIN_STOCKS
IDIO = PG.IDIO
N_Q = 7
ALPHA = 0.05 / N_Q                       # 99.29％ の幅
JUDGES = (("p1", "P1 その銘柄だけ +1％以上高く寄った − ふつう", "J15 K1", -1),
          ("p2", "P2 その銘柄だけ −1％以下安く寄った − ふつう", "J15 K2", +1),
          ("p3", "P3 今朝の窓 ±1％未満の朝：前日 +5％以上 − 前日ふつう", "J16 M1", -1),
          ("p4", "P4 その銘柄だけ高く寄った朝：前日 +5％以上 − 前日ふつう", "J17 N1", -1),
          ("p5", "P5 前日 +5％以上の株：その銘柄だけ高く寄った − ふつうに寄った", "J17 N2", -1),
          ("p6", "P6 その銘柄だけ安く寄った朝：前日 +5％以上 − 前日ふつう", "J17 N3", -1),
          ("p7", "P7 その銘柄だけ安く寄った朝：前日 −5％以下 − 前日ふつう（新しい問い）", "J17 の読むための表", +1))
YEAR_KEYS = ("p1", "p2", "p3", "p4", "p7")
SAME, OPP, NONE = "✅ 3つ目の期間でも同じ向き", "⚠️ 逆向き", "見えない"


# ════════════════════ 使える年（損益は見ない） ════════════════════

def add_shape(shape, daily):
    """1銘柄の日足から、年ごとの『動いた日』『始値＝終値で動いた日』『データのある銘柄』を数える（出来高0の日は数えない）"""
    seen = set()
    for d, o, h, lo, c, v in daily:
        y = int(d[:4])
        if not v or v <= 0:
            continue
        s = shape.setdefault(y, {"move": 0, "oc": 0, "stocks": 0})
        if y not in seen:
            seen.add(y)
            s["stocks"] += 1
        if h > lo:
            s["move"] += 1
            if o == c:
                s["oc"] += 1


def thin_by_year(A):
    """年ごとの『数えられる銘柄が MIN_STOCKS 未満の朝』の割合（A＝stock_rows の行）"""
    if not len(A):
        return {}
    days, counts = np.unique(A[:, C["day"]], return_counts=True)
    years = np.array([dt.date.fromordinal(int(o)).year for o in days])
    return {int(y): float((counts[years == y] < MIN_STOCKS).mean()) for y in np.unique(years)}


def usable_start(shape, thin):
    """→ {"start", "bad_years", "years", "ref_oc"}。start が None なら数えない（2016年が使えない年）"""
    share = {y: (s["oc"] / s["move"] if s["move"] else None) for y, s in shape.items()}
    ref = [share[y] for y in REF_YEARS if share.get(y) is not None]
    ref_oc = float(np.mean(ref)) if ref else None
    first, last = int(SPAN[0][:4]), int(SPAN[1][:4])
    years, bad = {}, []
    for y in range(first, last + 1):
        sh, th = share.get(y), thin.get(y, 1.0)
        why = []
        if sh is None or (ref_oc is not None and sh > OC_RATIO * ref_oc):
            why.append("始値の欠けの疑い")
        if th > THIN_SHARE:
            why.append("銘柄の少ない朝")
        years[y] = {"oc_share": sh, "thin_share": th, "stocks": shape.get(y, {}).get("stocks", 0), "bad": why}
        if why:
            bad.append(y)
    if last in bad:
        start = None
    elif bad:
        start = f"{max(bad) + 1}-01-01"
    else:
        start = SPAN[0]
    return {"start": start, "bad_years": bad, "years": years, "ref_oc": ref_oc}


# ════════════════════ 組と判定 ════════════════════

def groups(key, A, idio):
    """各行の組（先に書いた組＝0・比べる相手＝1・それ以外＝−1）"""
    mid = np.abs(idio) < IDIO
    if key == "p1":
        return GL.pair_grp(idio >= IDIO, mid)
    if key == "p2":
        return GL.pair_grp(idio <= -IDIO, mid)
    if key == "p3":
        return PD.groups(A, "up")
    if key in ("p4", "p5", "p6"):
        return PG.groups(idio, A[:, C["rprev"]], {"p4": "n1", "p5": "n2", "p6": "n3"}[key])
    if key == "p7":
        ib, pb = PG.bands(idio, A[:, C["rprev"]])
        return GL.pair_grp((ib == 0) & (pb == 0), (ib == 0) & (pb == 1))
    raise ValueError(key)


def replicate(verdict, expected):
    s = PD._sign(verdict)
    if s == expected:
        return SAME
    if s == -expected:
        return OPP
    return NONE


def _plain_diff(v, g):
    ns = [int((g == 0).sum()), int((g == 1).sum())]
    return {"diff": PG._diff(v, g) if min(ns) >= T.MIN_N else None, "ns": ns}


def analyze(A, start):
    d = A[:, C["day"]]
    A = A[(d >= PD._ord(start)) & (d <= PD._ord(SPAN[1]))]
    A, idio = PG.idio_gap(A)
    v = A[:, C["rclose"]]
    res = {"judges": {}, "start": start}
    grps = {}
    for key, name, src, expected in JUDGES:
        g = groups(key, A, idio)
        grps[key] = g
        q = PG.measure(A, g, "rclose", ALPHA)
        q.update(name=name, source=src, expected=expected, verdict=PD.judge(q))
        q["replicate"] = replicate(q["verdict"], expected)
        res["judges"][key] = q
    res["n_same"] = sum(res["judges"][k]["replicate"] == SAME for k in ("p1", "p2", "p3", "p4", "p5", "p6"))
    days = np.unique(A[:, C["day"]])
    res["period"] = {"rows": int(len(A)), "days": int(len(days)),
                     "first": dt.date.fromordinal(int(days[0])).isoformat() if len(days) else None,
                     "last": dt.date.fromordinal(int(days[-1])).isoformat() if len(days) else None,
                     "stocks": int(len(np.unique(A[:, C["code"]])))}
    # ── 読むための表（判定しない）──
    years = np.array([dt.date.fromordinal(int(o)).year for o in A[:, C["day"]]])
    res["by_year"] = {str(y): {k: _plain_diff(v, np.where(years == y, grps[k], -1)) for k in YEAR_KEYS} for y in np.unique(years)}
    tv = A[:, C["turnover"]]
    res["by_turnover"] = {lab: {k: _plain_diff(v, np.where((tv >= lo) & (tv < hi), grps[k], -1)) for k, *_ in JUDGES}
                          for lab, lo, hi in S.TURNOVER_BANDS}
    res["cells"] = PG._cell_table(A, idio, "rclose")
    return res


# ════════════════════ 読む ════════════════════

def load(codes, fetch):
    parts, missing, drops, shape = [], [], {"n": 0}, {}
    for i, code in enumerate(codes):
        d = fetch(code, "1d", "max")
        if not d:
            missing.append(code)
            continue
        daily = sorted({t.date().isoformat(): (t.date().isoformat(), o, h, lo, c, v) for t, o, h, lo, c, v in d}.values())
        add_shape(shape, daily)
        parts.append(PD.stock_rows(i, daily, {}, {}, first=SPAN[0], last=SPAN[1], recent_from="2100-01-01", drops=drops))
        if (i + 1) % 500 == 0:
            print(f"  ...{i + 1}/{len(codes)}", flush=True)
    A = np.vstack(parts) if parts else np.zeros((0, len(PD.COLS)))
    return A, missing, drops, shape


def check_summary(A, missing, shape, n_codes, store):
    u = usable_start(shape, thin_by_year(A))
    return {"n_codes": n_codes, "missing_daily": len(missing), "rows_2006_2016": int(len(A)), "store": store,
            "ref_oc_share_2017_2025": u["ref_oc"], "bad_years": u["bad_years"], "usable_start": u["start"],
            "years": {str(y): {"stocks": x["stocks"], "oc_share": None if x["oc_share"] is None else round(x["oc_share"], 5),
                               "thin_share": round(x["thin_share"], 3), "bad": x["bad"]} for y, x in u["years"].items()}}


def _p(x, d=2):
    return Y._pct(x, d)


def render_md(res):
    L = ["# J18 これまでの目印を、まだ使っていない3つ目の期間（2006〜2016年）で確かめる", "",
         f"作成: {res['generated_at']}（GitHub Actions で計算）。事前登録＝`{P.PREREG}`「J18」（指紋 sha256 `{(res.get('prereg_sha256') or '')[:16]}…`）。",
         "銘柄名は出しません。値は株価の変化率（％）。**売買の決まりではない**。", ""]
    r = res.get("result") or {}
    if r.get("error"):
        return "\n".join(L + [f"- ⚠️ 計算できず: {r['error']}", ""]) + "\n"
    ps, pe, u = res.get("price_store") or {}, r["period"], r["usable"]
    L += [f"- 対象：置き場の一覧 {r.get('n_codes')}銘柄（いま上場している銘柄だけ）。日足を取れなかった銘柄 {r.get('n_missing')}。"
          f"値段の置き場：{ps.get('built_at') or '使わず'}（日足 {ps.get('daily_range')}・10年で取り直した銘柄 {(ps.get('fallback') or {}).get('1d')}）",
          f"- 使える年（データの形だけで決めた）：使えない年 {u['bad_years'] or 'なし'} → **{r['start']}〜{SPAN[1]}**"
          f"（始値＝終値の割合の基準 2017〜2025年 {_p(u['ref_oc'], 3)}）",
          f"- 数えた朝：{pe['first']}〜{pe['last']}・{pe['days']}営業日・{pe['rows']:,}朝・{pe['stocks']}銘柄（その朝の銘柄が{MIN_STOCKS}未満の朝は除いた）",
          f"- 寄り→大引け（この期間は1時間足・5分足が無い）。幅は99.29％（p＜0.05÷7）・日と銘柄で引き直した広いほう。±25％超で捨てた値 {r.get('n_dropped')}",
          "", "## まとめ", "",
          f"- **これまでの目印6つ（P1〜P6）のうち、3つ目の期間でも同じ向き：{r['n_same']}／6**",
          f"- **新しい問い P7**：{r['judges']['p7']['replicate']}", "",
          "## 判定（事前登録の7つ）", ""]
    for key, *_ in JUDGES:
        q = r["judges"][key]
        L.append(f"- **{q['name']}**（元＝{q['source']}・{'下げやすい' if q['expected'] < 0 else '上げやすい'}）：差 {_p(q.get('diff'))}"
                 f"（幅 {_p(q.get('lo'))}〜{_p(q.get('hi'))}・{q['ns'][0]:,}対{q['ns'][1]:,}回）・前半 {_p(q.get('early'))}／後半 {_p(q.get('late'))}・"
                 f"先の組の費用後 {_p(q.get('mean_a_cost'))}（比べる相手 {_p(q.get('mean_b_cost'))}）→ {q['verdict']} → **{q['replicate']}**")
    L += ["", "## 読むための表（判定しない）", "", "### 年ごとの差（寄り→大引け）", "",
          "| 年 | " + " | ".join(k.upper() for k in YEAR_KEYS) + " |", "|---|" + "---:|" * len(YEAR_KEYS)]
    for y, row in r["by_year"].items():
        L.append(f"| {y} | " + " | ".join(_p(row[k]["diff"]) for k in YEAR_KEYS) + " |")
    L += ["", "### 売買代金ごとの差", "", "| 売買代金 | " + " | ".join(k.upper() for k, *_ in JUDGES) + " |", "|---|" + "---:|" * len(JUDGES)]
    for lab, row in r["by_turnover"].items():
        L.append(f"| {lab} | " + " | ".join(f"{_p(row[k]['diff'])}" for k, *_ in JUDGES) + " |")
    L += ["", "### その銘柄だけの窓 × 前の日の値動きの平均（寄り→大引け・費用なし）", "",
          "| その銘柄だけの窓 | " + " | ".join(PG.PREV_LABELS[p] for p in (2, 1, 0)) + " |", "|---|---:|---:|---:|"]
    for il, row in r["cells"].items():
        L.append(f"| {il} | " + " | ".join(f"{_p(row[PG.PREV_LABELS[p]].get('mean'))}（{row[PG.PREV_LABELS[p]]['n']:,}）" for p in (2, 1, 0)) + " |")
    L += ["", "- 30件未満の区分は「—」。⚠️ いま上場している銘柄だけ（この期間に上場をやめた株は入らない＝生き残りの偏り）。"
          "小さい株は売り買いの差が大きく、費用 0.1％ は甘い（判定は差なので費用は消える）。空売りは数えない。",
          "", "---", "", "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。"]
    return "\n".join(L) + "\n"


def main(argv):
    res = {"generated_at": dt.datetime.now(P.JST).isoformat(timespec="minutes"), "prereg_file": P.PREREG,
           "prereg_sha256": P.prereg_sha256(), "span": SPAN}
    try:
        stocks, list_date = jp_bars.load_universe()
        codes = sorted(stocks)
        A, missing, drops, shape = load(codes, jp_bars.fetcher())
        store = jp_bars.info()
        res["price_store"] = store
        if "--check" in argv:
            print(json.dumps(check_summary(A, missing, shape, len(codes), store), ensure_ascii=False, indent=1))
            return 0
        if not store or store.get("daily_range") != "max":
            raise RuntimeError("値段の置き場の日足が全期間版ではない（先に jp-bars-cache を回す）")
        if len(missing) > T.MAX_MISSING * len(codes):
            raise RuntimeError(f"日足を取れなかった銘柄が {len(missing)}/{len(codes)}＝5％超。偏った組で判定しない（取り直す）")
        u = usable_start(shape, thin_by_year(A))
        if u["start"] is None:
            raise RuntimeError(f"2016年が使えない年（{u['years'][int(SPAN[1][:4])]['bad']}）＝数えない")
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
