# -*- coding: utf-8 -*-
"""J16 前の日に大きく動いた株が今朝ふつうに寄ったとき、寄りのあとは続くか戻るか（昔の期間と最近の期間の両方で）。
2026-10-07 朝 登録・オーナー「続けてください」（研究の加速）。PILLAR_PREREG.md「J16」。

今朝の窓が ±1％ 未満の朝だけに絞り（窓の影響を外す）、前の日の値動き（+5％以上／−5％以下／±2％未満）で組を分ける。
M1・M2＝昔の期間（2016-11〜2023-09・寄り→大引け）／M3・M4＝最近の期間（2023-10〜2026-10・寄り→10:00・9:30 も同じ向きか）。
両方の期間が同じ向きのときだけ「✅ 昔と最近の両方で同じ向き」。

⚠️ 決まりは PILLAR_PREREG.md「J16」と下の定数に固定。幅の出し方は gap_lab.boot をそのまま使う。値段は値段の置き場（jp_bars.py）から。
⚠️ 出力（prevday-lab.json / .md）は集計だけ・銘柄名とコードは出さない（SYNC禁忌）。

実行: python prevday_lab.py          （本番。Actions の prevday-lab.yml から手動で・1回だけ）
      python prevday_lab.py --diag   （件数とデータの形だけ。値動きは出さない・何も書き出さない）
"""
import datetime as dt
import json
import sys

import numpy as np

import build_jp_highs as H
import gap_lab as GL
import highs_trap_lab as T
import highs_trap_small as S
import jp_bars
import pillar_lab as P
import yori_lab as Y

OUT_JSON, OUT_MD = "prevday-lab.json", "prevday-lab.md"
OLD = ("2016-11-01", "2023-09-29")
NEW = ("2023-10-10", T.END_DAY)
GAP_FLAT = 0.01               # 今朝の窓 ±1％ 未満
PREV_BIG = 0.05               # 前の日 +5％ 以上／−5％ 以下
PREV_FLAT = 0.02              # 前の日 ±2％ 未満
MAX_MOVE = 0.25
N_Q = 4
ALPHA = 0.05 / N_Q
COLS = ("day", "code", "gap", "rprev", "rclose", "r1000", "r930", "turnover")
C = {k: i for i, k in enumerate(COLS)}
JUDGES = (("m1", "M1 前日大きく上げた − 前日ふつう（昔の期間・寄り→大引け）", "up", OLD, "rclose"),
          ("m2", "M2 前日大きく下げた − 前日ふつう（昔の期間・寄り→大引け）", "dn", OLD, "rclose"),
          ("m3", "M3 前日大きく上げた − 前日ふつう（最近の期間・寄り→10:00）", "up", NEW, "r1000"),
          ("m4", "M4 前日大きく下げた − 前日ふつう（最近の期間・寄り→10:00）", "dn", NEW, "r1000"))
DOWN, UP = "下げやすい兆し", "上げやすい兆し"
BOTH, ONE, NONE = "✅ 昔と最近の両方で同じ向き", "△ 片方の期間だけ", "見えない"


def _gap_days(a, b):
    return (dt.date.fromisoformat(b) - dt.date.fromisoformat(a)).days


def stock_rows(ci, daily, m5, h1, first=OLD[0], last=NEW[1], recent_from=NEW[0], drops=None):
    """1銘柄の朝ごとの行（COLS の順）。最近の期間の朝だけ 1時間足・5分足の値（寄り→10:00・9:30）を入れる"""
    bars = [(d, h, lo, c, v) for d, o, h, lo, c, v in daily]
    out = []
    for k in range(1, len(daily) - 1):
        dp, d0, d1 = daily[k - 1], daily[k], daily[k + 1]
        day = d1[0]
        if day < first:
            continue
        if day > last:
            break
        op, high, low, close, vol, pc, ppc = d1[1], d1[2], d1[3], d1[4], d1[5], d0[4], dp[4]
        if not op or op <= 0 or not pc or pc <= 0 or not ppc or ppc <= 0 or not vol or vol <= 0:
            continue
        if _gap_days(d0[0], day) > GL.MAX_GAP_DAYS or _gap_days(dp[0], d0[0]) > GL.MAX_GAP_DAYS:
            continue
        if not H.sane_today(bars[k:k + 2]) or not H.sane_today(bars[k - 1:k + 1]) or not (low * (1 - 1e-9) <= op <= high * (1 + 1e-9)):
            continue
        rc = close / op - 1
        if abs(rc) > MAX_MOVE:
            if drops is not None:
                drops["n"] += 1
            continue
        r1000 = r930 = np.nan
        if day >= recent_from:
            o = T.outcomes(op, close, m5.get(day), h1.get(day), drops)
            if o is not None:
                r1000 = np.nan if o["r1000"] is None else o["r1000"]
                r930 = np.nan if o["r930"] is None else o["r930"]
        out.append((dt.date.fromisoformat(day).toordinal(), ci, op / pc - 1, pc / ppc - 1, rc, r1000, r930, pc * d0[5] / 1e8))
    return np.array(out, float).reshape(-1, len(COLS))


def _ord(s):
    return dt.date.fromisoformat(s).toordinal()


def period(A, span):
    d = A[:, C["day"]]
    return A[(d >= _ord(span[0])) & (d <= _ord(span[1]))]


def groups(A, side):
    """今朝の窓 ±1％ 未満の朝だけで、前日大きく（上げた／下げた）＝0・前日ふつう＝1・それ以外＝−1"""
    flat = np.abs(A[:, C["gap"]]) < GAP_FLAT
    rp = A[:, C["rprev"]]
    big = rp >= PREV_BIG if side == "up" else rp <= -PREV_BIG
    return GL.pair_grp(flat & big, flat & (np.abs(rp) < PREV_FLAT))


def _plain(A, col, grp):
    v = A[:, C[col]]
    ok = np.isfinite(v)
    a, b = v[ok & (grp == 0)], v[ok & (grp == 1)]
    return {"ns": [int(len(a)), int(len(b))], "diff": float(a.mean() - b.mean()) if len(a) and len(b) else None}


def measure(A, side, col, alpha=ALPHA):
    grp = groups(A, side)
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
               early=_plain(A[early], col, g[early])["diff"], late=_plain(A[late], col, g[late])["diff"],
               mean_a_cost=float(val[g == 0].mean() - T.COST), mean_b_cost=float(val[g == 1].mean() - T.COST))
    if col == "r1000":
        out["d60"] = _plain(A, "r930", grp)
    if None not in (lo_d, lo_c, hi_d, hi_c):
        out.update(lo=min(lo_d, lo_c), hi=max(hi_d, hi_c))
    return out


def judge(q):
    if q.get("lo") is None or min(q["ns"]) < T.MIN_N:
        return "件数不足"
    side = (lambda x, s: x is not None and x * s > 0)
    for sign, word in ((-1, DOWN), (+1, UP)):
        whole = q["hi"] < 0 if sign < 0 else q["lo"] > 0
        if whole and side(q["early"], sign) and side(q["late"], sign) and side(q["mean_a_cost"], sign):
            if "d60" not in q:
                return word
            return T._verdict(word, T.check60(min(q["d60"]["ns"]), q["d60"]["diff"], sign))
    return NONE


def _sign(verdict):
    for sign, word in ((-1, DOWN), (+1, UP)):
        if verdict.startswith(word):
            return sign
    return 0


def summary(v_old, v_new):
    a, b = _sign(v_old), _sign(v_new)
    if a and a == b:
        return BOTH + ("（下げやすい）" if a < 0 else "（上げやすい）")
    if a or b:
        return ONE
    return NONE


def analyze(A):
    res = {"judges": {}}
    for key, name, side, span, col in JUDGES:
        sub = period(A, span)
        q = measure(sub, side, col)
        q.update(name=name, verdict=judge(q))
        res["judges"][key] = q
    J = res["judges"]
    res["summary"] = {"up": summary(J["m1"]["verdict"], J["m3"]["verdict"]), "dn": summary(J["m2"]["verdict"], J["m4"]["verdict"])}
    old, new = period(A, OLD), period(A, NEW)
    res["periods"] = {name: {"rows": int(len(x)), "days": int(len(np.unique(x[:, C["day"]]))) if len(x) else 0,
                             "flat_mornings": int((np.abs(x[:, C["gap"]]) < GAP_FLAT).sum())} for name, x in (("old", old), ("new", new))}
    # ── 読むための表（判定しない）──
    reading = {}
    for name, x, col in (("old", old, "rclose"), ("new", new, "r1000")):
        rp, gp, v = x[:, C["rprev"]], x[:, C["gap"]], x[:, C[col]]
        flat = np.abs(gp) < GAP_FLAT
        reading[name] = {lab: GL._mean(v[m]) for lab, m in (
            ("前日 +10％以上・今朝ふつう", flat & (rp >= 0.10)), ("前日 +5〜10％・今朝ふつう", flat & (rp >= 0.05) & (rp < 0.10)),
            ("前日 ±2％未満・今朝ふつう", flat & (np.abs(rp) < PREV_FLAT)),
            ("前日 −5〜−10％・今朝ふつう", flat & (rp <= -0.05) & (rp > -0.10)), ("前日 −10％以下・今朝ふつう", flat & (rp <= -0.10)),
            ("前日 +5％以上・窓は問わない", rp >= PREV_BIG), ("前日 −5％以下・窓は問わない", rp <= -PREV_BIG))}
    res["reading"] = reading
    tv = old[:, C["turnover"]]
    rp, gp, v = old[:, C["rprev"]], old[:, C["gap"]], old[:, C["rclose"]]
    flat = np.abs(gp) < GAP_FLAT
    res["by_turnover_old"] = {lab: {k: GL._mean(v[flat & m & (tv >= a) & (tv < b)]) for k, m in (
        ("up", rp >= PREV_BIG), ("base", np.abs(rp) < PREV_FLAT), ("dn", rp <= -PREV_BIG))} for lab, a, b in S.TURNOVER_BANDS}
    years = np.array([dt.date.fromordinal(int(o)).year for o in A[:, C["day"]]])
    by_year = {}
    for y in sorted(set(years.tolist())):
        x = A[years == y]
        col = "rclose"
        g_up, g_dn = groups(x, "up"), groups(x, "dn")
        v = x[:, C[col]]
        by_year[str(y)] = {"up": float(v[g_up == 0].mean() - v[g_up == 1].mean()) if (g_up == 0).any() and (g_up == 1).any() else None,
                           "dn": float(v[g_dn == 0].mean() - v[g_dn == 1].mean()) if (g_dn == 0).any() and (g_dn == 1).any() else None,
                           "n_up": int((g_up == 0).sum()), "n_dn": int((g_dn == 0).sum())}
    res["by_year_rclose"] = by_year
    return res


def load(codes, fetch):
    parts, missing, drops = [], {"daily": [], "h1": [], "m5": []}, {"n": 0}
    for i, code in enumerate(codes):
        d = fetch(code, "1d", "10y")
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


def diag_summary(A, missing, n_codes):
    out = {"n_codes": n_codes, "missing": {k: len(v) for k, v in missing.items()}, "rows": int(len(A))}
    for key, name, side, span, col in JUDGES:
        sub = period(A, span)
        g = groups(sub, side)
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
    L = ["# J16 前の日に大きく動いた株が今朝ふつうに寄ったとき、寄りのあとは続くか戻るか", "",
         f"作成: {res['generated_at']}（GitHub Actions で計算）。事前登録＝`{P.PREREG}`「J16」（指紋 sha256 `{(res.get('prereg_sha256') or '')[:16]}…`）。",
         "銘柄名は出しません。値は株価の変化率（％）。**売買の決まりではない**。", ""]
    r = res.get("result") or {}
    if r.get("error"):
        return "\n".join(L + [f"- ⚠️ 計算できず: {r['error']}", ""]) + "\n"
    ps = res.get("price_store") or {}
    pe = r["periods"]
    L += [f"- 対象：置き場の一覧 {r.get('n_codes')}銘柄（一覧 {r.get('list_date')}・いま上場している銘柄だけ）。取れなかった銘柄 {r.get('n_missing')}。値段の置き場：{ps.get('built_at') or '使わず'}",
          f"- 昔の期間 {OLD[0]}〜{OLD[1]}：{pe['old']['days']}営業日・{pe['old']['rows']:,}朝（今朝ふつうに寄った朝 {pe['old']['flat_mornings']:,}）／"
          f"最近の期間 {NEW[0]}〜{NEW[1]}：{pe['new']['days']}営業日・{pe['new']['rows']:,}朝（同 {pe['new']['flat_mornings']:,}）",
          f"- 幅は98.75％（p＜0.05÷4）・日と銘柄で引き直した広いほう。±25％超で捨てた値 {r.get('n_dropped')}",
          "", "## まとめ", "",
          f"- **前日大きく上げた株（+5％以上）**：{r['summary']['up']}",
          f"- **前日大きく下げた株（−5％以下）**：{r['summary']['dn']}",
          "", "## 判定（事前登録の4つ・どれも今朝の窓が ±1％ 未満の朝だけ）", ""]
    for key, *_ in JUDGES:
        q = r["judges"][key]
        extra = f"・5分足の寄り→9:30 の差 {_p(q['d60']['diff'])}（{q['d60']['ns'][0]:,}対{q['d60']['ns'][1]:,}）" if "d60" in q else ""
        L.append(f"- **{q['name']}**：差 {_p(q.get('diff'))}（幅 {_p(q.get('lo'))}〜{_p(q.get('hi'))}・{q['ns'][0]:,}対{q['ns'][1]:,}回）・"
                 f"前半 {_p(q.get('early'))}／後半 {_p(q.get('late'))}・その組の費用後 {_p(q.get('mean_a_cost'))}（前日ふつう {_p(q.get('mean_b_cost'))}）{extra} → **{q['verdict']}**")
    L += ["", "## 読むための表（判定しない）", "", "### 前の日の値動きごとの平均（昔＝寄り→大引け・最近＝寄り→10:00・費用なし）", "",
          "| 区分 | 昔の期間 | 最近の期間 |", "|---|---:|---:|"]
    for lab in r["reading"]["old"]:
        a, b = r["reading"]["old"][lab], r["reading"]["new"][lab]
        L.append(f"| {lab} | {_p(a.get('mean'))}（{a['n']:,}） | {_p(b.get('mean'))}（{b['n']:,}） |")
    L += ["", "### 前の日の売買代金ごと（昔の期間・今朝ふつうに寄った朝・寄り→大引け）", "", "| 売買代金 | 前日 +5％以上 | 前日ふつう | 前日 −5％以下 |", "|---|---:|---:|---:|"]
    for lab, b in r["by_turnover_old"].items():
        L.append(f"| {lab} | " + " | ".join(f"{_p(b[k].get('mean'))}（{b[k]['n']:,}）" for k in ("up", "base", "dn")) + " |")
    L += ["", "- 年ごとの差（寄り→大引け・今朝ふつうに寄った朝）：" + "／".join(
        f"{y} 上げた {_p(v['up'])}・下げた {_p(v['dn'])}" for y, v in r["by_year_rclose"].items()),
          "- 30件未満の区分は「—」。小さい株は売り買いの差が大きく、費用 0.1％ は甘い（判定は差なので費用は消える）。空売りは数えない。",
          "", "---", "", "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。"]
    return "\n".join(L) + "\n"


def main(argv):
    res = {"generated_at": dt.datetime.now(P.JST).isoformat(timespec="minutes"), "prereg_file": P.PREREG,
           "prereg_sha256": P.prereg_sha256(), "old": OLD, "new": NEW}
    try:
        stocks, list_date = jp_bars.load_universe()
        codes = sorted(stocks)
        A, missing, drops = load(codes, jp_bars.fetcher())
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
