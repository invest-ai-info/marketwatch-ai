# -*- coding: utf-8 -*-
"""J20 主戦場（前の日に大きく上げた×売買代金が大きい株）を翌朝の寄りで買うと、3つの時代でどうだったか。
2026-10-07 登録・オーナー「1と2を登録して続けてください」。PILLAR_PREREG.md「J20」。

主戦場＝前の日 +5％ 以上 かつ 前の日の売買代金 10億円以上。E1 2006〜2016・E2 2016〜2023（寄り→大引け）／E3 2023〜2026（寄り→10:00）。
  Q1 主戦場を寄りで買う（費用後）／Q2 そのうち今朝その銘柄だけの窓 ±1％ 未満（費用後）
  Q3 過熱（25日線 +15％ 超）あり − なし／Q4 連騰（4日以上）あり − なし
12の判定（p＜0.05÷12）。問いごとに3つの時代が同じ向きなら「✅」。

⚠️ 決まりは PILLAR_PREREG.md「J20」と下の定数に固定。行の作り方は prevday_lab（J16）、その銘柄だけの窓は prevgap_lab（J17）をそのまま使う。
⚠️ 出力（main-field-lab.json / .md）は集計だけ・銘柄名とコードは出さない（SYNC禁忌）。

実行: python main_field_lab.py --check   （点検だけ＝行数と組の回数。損益は数えない・何も書き出さない）
      python main_field_lab.py           （本番。Actions の main-field-lab.yml から手動で・1回だけ）
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

OUT_JSON, OUT_MD = "main-field-lab.json", "main-field-lab.md"
ERAS = (("e1", "E1 2006〜2016（寄り→大引け）", ("2006-01-04", "2016-10-31"), "rclose"),
        ("e2", "E2 2016〜2023（寄り→大引け）", PD.OLD, "rclose"),
        ("e3", "E3 2023〜2026（寄り→10:00）", PD.NEW, "r1000"))
COLS = PD.COLS + ("dev25", "streak")
C = {k: i for i, k in enumerate(COLS)}
PREV_BIG = 0.05
TURNOVER = 10.0          # 億円
IDIO = 0.01
OVERHEAT = 0.15          # 25日線から +15％ 超
STREAK = 4               # 4日以上続けて上がった
N_Q = 12
ALPHA = 0.05 / N_Q       # 99.58％ の幅
QUESTIONS = (("q1", "Q1 主戦場を寄りで買う（費用後）", "mean"),
             ("q2", "Q2 主戦場のうち、今朝その銘柄だけの窓 ±1％ 未満（費用後）", "mean"),
             ("q3", "Q3 主戦場のうち、過熱あり − なし", "diff"),
             ("q4", "Q4 主戦場のうち、連騰あり − なし", "diff"))
DOWN, UP, NONE = "下", "上", "見えない"
ALL3, TWO = "✅ 3つの時代で同じ向き", "△ 2つの時代"


# ════════════════════ 行 ════════════════════

def prev_features(daily):
    """日足の各日 k について（25日線からの離れ、それまで続けて上がった日数）。25日そろわなければ離れは NaN"""
    c = np.array([r[4] for r in daily], float)
    n = len(c)
    dev = np.full(n, np.nan)
    if n >= 25:
        cs = np.concatenate([[0.0], np.cumsum(c)])
        ma = (cs[25:] - cs[:-25]) / 25
        dev[24:] = c[24:] / ma - 1
    streak = np.zeros(n)
    for k in range(1, n):
        streak[k] = streak[k - 1] + 1 if c[k] > c[k - 1] else 0
    return dev, streak


def stock_rows(ci, daily, m5, h1, drops=None):
    """J16 の行（2006-01〜2026-10）＋前の日の 25日線からの離れ・連騰の日数"""
    A = PD.stock_rows(ci, daily, m5, h1, first=ERAS[0][2][0], last=PD.NEW[1], recent_from=PD.NEW[0], drops=drops)
    if not len(A):
        return np.zeros((0, len(COLS)))
    dev, streak = prev_features(daily)
    pos = {dt.date.fromisoformat(r[0]).toordinal(): i for i, r in enumerate(daily)}
    k = np.array([pos[int(o)] - 1 for o in A[:, PD.C["day"]]])
    return np.hstack([A, dev[k].reshape(-1, 1), streak[k].reshape(-1, 1)])


# ════════════════════ 組と判定 ════════════════════

def main_field(A):
    return (A[:, C["rprev"]] >= PREV_BIG) & (A[:, C["turnover"]] >= TURNOVER)


def groups(key, A, idio):
    """各行の組（平均の問い＝0 だけ／差の問い＝あり 0・なし 1）。それ以外は −1"""
    mf = main_field(A)
    if key == "q1":
        return np.where(mf, 0, -1)
    if key == "q2":
        return np.where(mf & (np.abs(idio) < IDIO), 0, -1)
    if key == "q3":
        dv = A[:, C["dev25"]]
        ok = mf & np.isfinite(dv)
        return GL.pair_grp(ok & (dv > OVERHEAT), ok & (dv <= OVERHEAT))
    if key == "q4":
        st = A[:, C["streak"]]
        return GL.pair_grp(mf & (st >= STREAK), mf & (st < STREAK))
    raise ValueError(key)


def _stat(kind):
    return (lambda mu: mu[0] - T.COST) if kind == "mean" else GL._diff2


def _plain(v, g, kind):
    ok = np.isfinite(v)
    a = v[ok & (g == 0)]
    if kind == "mean":
        return (float(a.mean() - T.COST) if len(a) else None), int(len(a))
    b = v[ok & (g == 1)]
    return (float(a.mean() - b.mean()) if len(a) and len(b) else None), int(min(len(a), len(b)))


def measure(A, g, col, kind, alpha=ALPHA):
    v = A[:, C[col]]
    gg = np.where(np.isfinite(v), g, -1)
    ng = 1 if kind == "mean" else 2
    ns = [int((gg == k).sum()) for k in range(ng)]
    out = {"ns": ns, "value": None, "lo": None, "hi": None, "early": None, "late": None}
    if min(ns) == 0:
        return out
    pt, lo_d, hi_d = GL.boot(v, gg, ng, A[:, C["day"]], _stat(kind), alpha)
    _, lo_c, hi_c = GL.boot(v, gg, ng, A[:, C["code"]], _stat(kind), alpha)
    days = np.unique(A[gg >= 0, C["day"]])
    cut = days[len(days) // 2]
    early, late = A[:, C["day"]] < cut, A[:, C["day"]] >= cut
    out.update(value=pt, early=_plain(v[early], gg[early], kind)[0], late=_plain(v[late], gg[late], kind)[0],
               by_day=[lo_d, hi_d], by_stock=[lo_c, hi_c])
    if None not in (lo_d, lo_c, hi_d, hi_c):
        out.update(lo=min(lo_d, lo_c), hi=max(hi_d, hi_c))
    if col == "r1000":
        x, n = _plain(A[:, C["r930"]], g, kind)
        out["d60"] = {"value": x, "n": n}
    return out


def judge(q):
    if q.get("lo") is None or min(q["ns"]) < T.MIN_N:
        return "件数不足"
    for sign, word in ((-1, DOWN), (+1, UP)):
        whole = q["hi"] < 0 if sign < 0 else q["lo"] > 0
        if whole and (q["early"] or 0) * sign > 0 and (q["late"] or 0) * sign > 0:
            if "d60" not in q:
                return word
            return T._verdict(word, T.check60(q["d60"]["n"], q["d60"]["value"], sign))
    return NONE


def _sign(verdict):
    if verdict.startswith(DOWN):
        return -1
    if verdict.startswith(UP):
        return +1
    return 0


def summarize(verdicts):
    signs = [_sign(v) for v in verdicts]
    for s, word in ((-1, DOWN), (+1, UP)):
        if signs.count(s) == 3:
            return f"{ALL3}（{word}）"
    for s, word in ((-1, DOWN), (+1, UP)):
        if signs.count(s) == 2 and -s not in signs:
            return f"{TWO}（{word}）"
    return NONE


def _era(A, span):
    d = A[:, C["day"]]
    return (d >= PD._ord(span[0])) & (d <= PD._ord(span[1]))


def _mean_n(v):
    v = v[np.isfinite(v)]
    return {"n": int(len(v)), "mean": float(v.mean()) if len(v) >= T.MIN_N else None}


def analyze(A):
    A, idio = PG.idio_gap(A)
    res = {"judges": {}, "summary": {}, "eras": {}}
    for key, name, kind in QUESTIONS:
        g = groups(key, A, idio)
        res["judges"][key] = {}
        for ek, ename, span, col in ERAS:
            m = _era(A, span)
            q = measure(A[m], g[m], col, kind)
            q.update(verdict=judge(q), era=ename)
            res["judges"][key][ek] = q
        res["summary"][key] = summarize([res["judges"][key][e]["verdict"] for e, *_ in ERAS])
    # ── 読むための表（判定しない・費用前の平均）──
    for ek, ename, span, col in ERAS:
        m = _era(A, span)
        B, ib = A[m], idio[m]
        v, rp, tv = B[:, C[col]], B[:, C["rprev"]], B[:, C["turnover"]]
        big = rp >= PREV_BIG
        res["eras"][ek] = {
            "rows": int(m.sum()), "days": int(len(np.unique(B[:, C["day"]]))),
            "by_turnover": {lab: _mean_n(v[big & (tv >= lo)]) for lab, lo in (("1億円以上", 1.0), ("10億円以上", 10.0), ("30億円以上", 30.0))},
            "by_prev": {lab: _mean_n(v[(tv >= TURNOVER) & (rp >= lo) & (rp < hi)]) for lab, lo, hi in
                        (("+5〜10％", 0.05, 0.10), ("+10〜15％", 0.10, 0.15), ("+15％以上", 0.15, 9.0))},
            "by_idio": {lab: _mean_n(v[(tv >= TURNOVER) & big & mk]) for lab, mk in
                        (("安く（−1％以下）", ib <= -IDIO), ("ふつう（±1％未満）", np.abs(ib) < IDIO), ("高く（+1％以上）", ib >= IDIO))},
        }
    mf = main_field(A)
    years = np.array([dt.date.fromordinal(int(o)).year for o in A[:, C["day"]]])
    res["by_year"] = {str(y): _mean_n(A[mf & (years == y), C["rclose"]]) for y in np.unique(years)}
    return res


# ════════════════════ 読む ════════════════════

def load(codes, fetch):
    parts, missing, drops = [], {"daily": [], "h1": [], "m5": []}, {"n": 0}
    for i, code in enumerate(codes):
        d = fetch(code, "1d", jp_bars.FULL_DAILY)
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
        parts.append(stock_rows(i, daily, T._by_day(m5), T._by_day(h1), drops=drops))
        if (i + 1) % 500 == 0:
            print(f"  ...{i + 1}/{len(codes)}", flush=True)
    A = np.vstack(parts) if parts else np.zeros((0, len(COLS)))
    return A, missing, drops


def check_summary(A, missing, n_codes, store):
    B, idio = PG.idio_gap(A)
    out = {"n_codes": n_codes, "missing": {k: len(v) for k, v in missing.items()}, "rows": int(len(A)), "rows_kept": int(len(B)),
           "store": store, "eras": {}}
    for ek, _, span, col in ERAS:
        m = _era(B, span) & np.isfinite(B[:, C[col]])
        out["eras"][ek] = {"rows": int(m.sum()), "dev25_known": int((m & np.isfinite(B[:, C["dev25"]])).sum()),
                           "sizes": {key: [int(((groups(key, B, idio) == k) & m).sum()) for k in (0, 1)] for key, *_ in QUESTIONS}}
        if col == "r1000":
            m9 = _era(B, span) & np.isfinite(B[:, C["r930"]])
            out["eras"][ek]["sizes_930"] = {key: [int(((groups(key, B, idio) == k) & m9).sum()) for k in (0, 1)] for key, *_ in QUESTIONS}
    return out


def _p(x, d=2):
    return Y._pct(x, d)


def render_md(res):
    L = ["# J20 主戦場（前の日に大きく上げた×売買代金が大きい株）を翌朝の寄りで買うと、3つの時代でどうだったか", "",
         f"作成: {res['generated_at']}（GitHub Actions で計算）。事前登録＝`{P.PREREG}`「J20」（指紋 sha256 `{(res.get('prereg_sha256') or '')[:16]}…`）。",
         "銘柄名は出しません。値は株価の変化率（％）。主戦場＝前の日 +5％ 以上 かつ 前の日の売買代金 10億円以上。費用＝往復 0.1％。**売買の決まりではない**。", ""]
    r = res.get("result") or {}
    if r.get("error"):
        return "\n".join(L + [f"- ⚠️ 計算できず: {r['error']}", ""]) + "\n"
    ps = res.get("price_store") or {}
    L += [f"- 対象：置き場の一覧 {r.get('n_codes')}銘柄（いま上場している銘柄だけ）。取れなかった銘柄 {r.get('n_missing')}。値段の置き場：{ps.get('built_at') or '使わず'}",
          "- 時代：" + "／".join(f"{name}＝{r['eras'][k]['days']}営業日" for k, name, *_ in ERAS),
          f"- 幅は99.58％（p＜0.05÷12）・日と銘柄で引き直した広いほう。±25％超で捨てた値 {r.get('n_dropped')}", "",
          "## まとめ（問いごと・3つの時代）", ""]
    for key, name, _ in QUESTIONS:
        L.append(f"- **{name}**：{r['summary'][key]}")
    L += ["", "## 判定（事前登録の12）", ""]
    for key, name, kind in QUESTIONS:
        L.append(f"### {name}")
        for ek, *_ in ERAS:
            q = r["judges"][key][ek]
            extra = f"・5分足の寄り→9:30 {_p(q['d60']['value'])}（{q['d60']['n']:,}）" if "d60" in q else ""
            ns = f"{q['ns'][0]:,}回" if kind == "mean" else f"{q['ns'][0]:,}対{q['ns'][1]:,}回"
            L.append(f"- {q['era']}：{_p(q.get('value'))}（幅 {_p(q.get('lo'))}〜{_p(q.get('hi'))}・{ns}）・前半 {_p(q.get('early'))}／後半 {_p(q.get('late'))}{extra} → **{q['verdict']}**")
        L.append("")
    L += ["## 読むための表（判定しない・費用前の平均）", "", "| 区分 | " + " | ".join(name for _, name, *_ in ERAS) + " |", "|---|---:|---:|---:|"]
    for sect, title in (("by_turnover", "前日 +5％ 以上・売買代金"), ("by_prev", "売買代金10億円以上・前の日"), ("by_idio", "主戦場・その銘柄だけの窓")):
        for lab in r["eras"]["e1"][sect]:
            L.append(f"| {title} {lab} | " + " | ".join(f"{_p(r['eras'][k][sect][lab]['mean'])}（{r['eras'][k][sect][lab]['n']:,}）" for k, *_ in ERAS) + " |")
    L += ["", "- 年ごと（主戦場・寄り→大引け・費用前）：" + "／".join(f"{y} {_p(v['mean'])}（{v['n']:,}）" for y, v in r["by_year"].items()),
          "- 30件未満の区分は「—」。⚠️ いま上場している銘柄だけ（生き残りの偏り）。点検表②の超小型・負エッジ業種と①赤字回避は数えていない。空売りは数えない。",
          "", "---", "", "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。"]
    return "\n".join(L) + "\n"


def main(argv):
    res = {"generated_at": dt.datetime.now(P.JST).isoformat(timespec="minutes"), "prereg_file": P.PREREG,
           "prereg_sha256": P.prereg_sha256()}
    try:
        stocks, list_date = jp_bars.load_universe()
        codes = sorted(stocks)
        A, missing, drops = load(codes, jp_bars.fetcher())
        store = jp_bars.info()
        res["price_store"] = store
        if "--check" in argv:
            print(json.dumps(check_summary(A, missing, len(codes), store), ensure_ascii=False, indent=1))
            return 0
        if not store or store.get("daily_range") != jp_bars.FULL_DAILY:
            raise RuntimeError("値段の置き場の日足が全期間版ではない（先に jp-bars-cache を回す）")
        bad = set(missing["daily"]) | set(missing["h1"])
        if len(bad) > T.MAX_MISSING * len(codes):
            raise RuntimeError(f"日足か1時間足を取れなかった銘柄が {len(bad)}/{len(codes)}＝5％超。偏った組で判定しない（取り直す）")
        res["result"] = dict(analyze(A), n_codes=len(codes), list_date=list_date,
                             n_missing={k: len(v) for k, v in missing.items()}, n_dropped=drops["n"])
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
