# -*- coding: utf-8 -*-
"""J14 J13 の「窓の戻し」は、J13 が使っていない昔の期間（2016-11〜2023-09）でも出ていたか（日足の寄り→大引け）。
2026-10-07 朝 登録・オーナー「研究ペースをもっと加速させてください」。PILLAR_PREREG.md「J14」。

J13 は1時間足が取れる約3年だけで数えた。日足は約10年前まで取れるので、J13 が見ていない昔の約7年で、
同じ窓の組み分け（ふつう／+1％以上／+3％以上／−1％以下／−3％以下）が同じ向きに効いていたかを寄り→大引けで確かめる。

⚠️ 決まりは PILLAR_PREREG.md「J14」と下の定数に固定。結果を見てから動かさない。幅の出し方は gap_lab.boot をそのまま使う。
⚠️ 値段は研究ラボ共通の値段の置き場（jp_bars.py・日足10年）から読む。無ければ Yahoo から（遅い）。
⚠️ 出力（gap-history-lab.json / .md）は集計だけ・銘柄名とコードは出さない。GitHub 側で生成＝手元から送らない（SYNC禁忌）。

実行: python gap_history_lab.py          （本番。Actions の gap-history-lab.yml から手動で・1回だけ）
      python gap_history_lab.py --diag   （件数とデータの形だけ。値動きは出さない・何も書き出さない）
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

OUT_JSON, OUT_MD = "gap-history-lab.json", "gap-history-lab.md"
FIRST_DAY, LAST_DAY = "2016-11-01", "2023-09-29"      # 判定に使う朝（J13 の1時間足の最初の日 2023-10-10 より前）
REF_FIRST, REF_LAST = "2023-10-10", T.END_DAY          # 参考＝J13 と同じ期間（読むだけ）
DAILY_RANGE = "10y"
N_Q = 4
ALPHA = 0.05 / N_Q                                    # 98.75％ の幅
MAX_MOVE = 0.25
COLS = ("day", "code", "gap", "rclose", "turnover")
C = {k: i for i, k in enumerate(COLS)}
PAIRS = (("g1", "G1 窓 +1％ 以上 − ふつう", -1, "up1"), ("g2", "G2 窓 +3％ 以上 − ふつう", -1, "up3"),
         ("g3", "G3 窓 −1％ 以下 − ふつう", +1, "dn1"), ("g4", "G4 窓 −3％ 以下 − ふつう", +1, "dn3"))
SAME, OPPOSITE, NONE = "✅ 昔の期間でも同じ向き（J13 を確かめた）", "⚠️ 昔の期間では逆向き（J13 と食い違う）", "見えない"


def stock_rows(ci, daily, first=FIRST_DAY, last=REF_LAST, drops=None):
    """1銘柄の朝ごとの行（COLS の順）。J13 と同じ除外＋出来高0の日・寄り→大引け ±25％超を除く"""
    bars = [(d, h, lo, c, v) for d, o, h, lo, c, v in daily]
    out = []
    for k in range(len(daily) - 1):
        d0, d1 = daily[k], daily[k + 1]
        day = d1[0]
        if day < first:
            continue
        if day > last:
            break
        op, high, low, close, vol, pc = d1[1], d1[2], d1[3], d1[4], d1[5], d0[4]
        if not op or op <= 0 or not pc or pc <= 0 or not vol or vol <= 0:
            continue
        if (dt.date.fromisoformat(day) - dt.date.fromisoformat(d0[0])).days > GL.MAX_GAP_DAYS:
            continue
        if not H.sane_today(bars[k:k + 2]) or not (low * (1 - 1e-9) <= op <= high * (1 + 1e-9)):
            continue
        r = close / op - 1
        if abs(r) > MAX_MOVE:
            if drops is not None:
                drops["n"] += 1
            continue
        out.append((dt.date.fromisoformat(day).toordinal(), ci, op / pc - 1, r, pc * d0[5] / 1e8))
    return np.array(out, float).reshape(-1, len(COLS))


def masks(A):
    g = A[:, C["gap"]]
    return {"base": (g > GL.DN1) & (g < GL.UP1), "up1": g >= GL.UP1, "up3": g >= GL.UP3, "dn1": g <= GL.DN1, "dn3": g <= GL.DN3}


def _ord(s):
    return dt.date.fromisoformat(s).toordinal()


def pair_stats(A, gk, alpha=ALPHA):
    """その組 − ふつう の寄り→大引けの差（費用前）・日と銘柄で引き直した広いほう・前半後半・その組の費用後の平均"""
    M = masks(A)
    grp = GL.pair_grp(M[gk], M["base"])
    val = A[:, C["rclose"]]
    ns = [int((grp == 0).sum()), int((grp == 1).sum())]
    out = {"ns": ns, "diff": None, "lo": None, "hi": None}
    if min(ns) == 0:
        return out
    pt, lo_d, hi_d = GL.boot(val, grp, 2, A[:, C["day"]], GL._diff2, alpha)
    _, lo_c, hi_c = GL.boot(val, grp, 2, A[:, C["code"]], GL._diff2, alpha)
    days = np.unique(A[:, C["day"]])
    cut = days[len(days) // 2]
    half = {}
    for name, m in (("early", A[:, C["day"]] < cut), ("late", A[:, C["day"]] >= cut)):
        a, b = val[m & (grp == 0)], val[m & (grp == 1)]
        half[name] = float(a.mean() - b.mean()) if len(a) and len(b) else None
    a_vals = val[grp == 0]
    out.update(diff=pt, by_day=[lo_d, hi_d], by_stock=[lo_c, hi_c], early=half["early"], late=half["late"],
               cut=dt.date.fromordinal(int(cut)).isoformat(), mean_a_cost=float(a_vals.mean() - T.COST),
               mean_b_cost=float(val[grp == 1].mean() - T.COST))
    if None not in (lo_d, lo_c, hi_d, hi_c):
        out.update(lo=min(lo_d, lo_c), hi=max(hi_d, hi_c))
    return out


def judge(q, sign):
    """sign＝J13 の向き（−1 高く寄った組・+1 安く寄った組）"""
    if q.get("lo") is None or min(q["ns"]) < T.MIN_N:
        return "件数不足"
    side = (lambda x: x is not None and x * sign > 0)
    whole = q["hi"] < 0 if sign < 0 else q["lo"] > 0
    if whole and side(q["early"]) and side(q["late"]) and side(q["mean_a_cost"]):
        return SAME
    if (q["lo"] > 0 if sign < 0 else q["hi"] < 0):
        return OPPOSITE
    return NONE


def analyze(A):
    day = A[:, C["day"]]
    main = A[(day >= _ord(FIRST_DAY)) & (day <= _ord(LAST_DAY))]
    ref = A[(day >= _ord(REF_FIRST)) & (day <= _ord(REF_LAST))]
    M = masks(main)
    days = np.unique(main[:, C["day"]])
    iso = lambda o: dt.date.fromordinal(int(o)).isoformat()  # noqa: E731
    res = {"n_rows": int(len(main)), "days": int(len(days)), "first": iso(days[0]) if len(days) else None,
           "last": iso(days[-1]) if len(days) else None, "n_codes_seen": int(len(np.unique(main[:, C["code"]]))),
           "group_n": {k: int(m.sum()) for k, m in M.items()}, "pairs": {}}
    for key, name, sign, gk in PAIRS:
        q = pair_stats(main, gk)
        q.update(name=name, verdict=judge(q, sign))
        res["pairs"][key] = q
    # ── 読むための表（判定しない）──
    years = np.array([dt.date.fromordinal(int(o)).year for o in main[:, C["day"]]])
    res["by_year"] = {}
    for y in sorted(set(years.tolist())):
        sub = main[years == y]
        Ms = masks(sub)
        r = sub[:, C["rclose"]]
        res["by_year"][str(y)] = {gk: (float(r[Ms[gk]].mean() - r[Ms["base"]].mean()) if Ms[gk].any() and Ms["base"].any() else None)
                                  for gk in ("up1", "dn1")} | {"n": int(len(sub))}
    tv = main[:, C["turnover"]]
    r = main[:, C["rclose"]]
    res["by_turnover"] = {lab: {gk: GL._mean(r[M[gk] & (tv >= a) & (tv < b)]) for gk in ("up1", "base", "dn1")}
                          for lab, a, b in S.TURNOVER_BANDS}
    bands = GL.band_labels(main[:, C["gap"]])
    res["by_band"] = {lab: GL._mean(r[bands == lab]) for lab, _, _ in GL.GAP_BANDS}
    res["ref_j13_period"] = {key: {"diff": (lambda q: q["diff"])(pair_stats(ref, gk, alpha=ALPHA)) if len(ref) else None,
                                   "ns": [int(masks(ref)[gk].sum()), int(masks(ref)["base"].sum())] if len(ref) else [0, 0]}
                             for key, _, _, gk in PAIRS}
    return res


def load(codes, fetch, first=FIRST_DAY, last=REF_LAST):
    parts, missing, drops = [], [], {"n": 0}
    for i, code in enumerate(codes):
        d = fetch(code, "1d", DAILY_RANGE)
        if not d:
            missing.append(code)
            continue
        daily = sorted({t.date().isoformat(): (t.date().isoformat(), o, h, lo, c, v) for t, o, h, lo, c, v in d}.values())
        parts.append(stock_rows(i, daily, first, last, drops))
        if (i + 1) % 500 == 0:
            print(f"  ...{i + 1}/{len(codes)}", flush=True)
    A = np.vstack(parts) if parts else np.zeros((0, len(COLS)))
    return A, missing, drops


def diag_summary(A, missing, n_codes):
    day = A[:, C["day"]]
    main = A[(day >= _ord(FIRST_DAY)) & (day <= _ord(LAST_DAY))]
    years = [dt.date.fromordinal(int(o)).year for o in main[:, C["day"]]]
    first_seen = {}
    for o, c in zip(A[:, C["day"]], A[:, C["code"]]):
        first_seen[c] = min(first_seen.get(c, o), o)
    return {"n_codes": n_codes, "missing": len(missing), "n_rows_main": int(len(main)),
            "days_main": int(len(np.unique(main[:, C["day"]]))),
            "first": dt.date.fromordinal(int(main[:, C["day"]].min())).isoformat() if len(main) else None,
            "last": dt.date.fromordinal(int(main[:, C["day"]].max())).isoformat() if len(main) else None,
            "by_year": {str(y): years.count(y) for y in sorted(set(years))},
            "group_n_main": {k: int(m.sum()) for k, m in masks(main).items()},
            "codes_with_rows_main": int(len(np.unique(main[:, C["code"]]))),
            "codes_starting_after_2017": sum(1 for o in first_seen.values() if o > _ord("2017-01-31")),
            "n_rows_ref": int(((day >= _ord(REF_FIRST)) & (day <= _ord(REF_LAST))).sum())}


def _p(x, d=2):
    return Y._pct(x, d)


def render_md(res):
    L = ["# J14 J13 の「窓の戻し」は昔の期間でも出ていたか（日足の寄り→大引け）", "",
         f"作成: {res['generated_at']}（GitHub Actions で計算）。事前登録＝`{P.PREREG}`「J14」（指紋 sha256 `{(res.get('prereg_sha256') or '')[:16]}…`）。",
         "銘柄名は出しません。値は株価の変化率（％）。**売買の決まりではない**。", ""]
    r = res.get("result") or {}
    if r.get("error"):
        return "\n".join(L + [f"- ⚠️ 計算できず: {r['error']}", ""]) + "\n"
    ps = res.get("price_store") or {}
    L += [f"- 対象：置き場の一覧 {r.get('n_codes')}銘柄（一覧 {r.get('list_date')}・いま上場している銘柄だけ＝生き残りの偏りあり）のうち、この期間に値のある {r['n_codes_seen']}銘柄。取れなかった銘柄 {r.get('n_missing')}",
          f"- 数えた朝：{r['first']}〜{r['last']}・{r['days']}営業日・{r['n_rows']:,}回（J13 の期間より前）。"
          + "組の件数：" + "／".join(f"{GL.GROUP_NAMES[k]} {v:,}" for k, v in r["group_n"].items()),
          f"- 幅は98.75％（p＜0.05÷4）・日と銘柄で引き直した広いほう。±25％超で捨てた値 {r.get('n_dropped')}。値段の置き場：{ps.get('built_at') or '使わず（Yahoo から）'}",
          "", "## 判定（事前登録の4つ・寄り→大引けの平均の差・費用前）", ""]
    for key, _, _, _ in PAIRS:
        q = r["pairs"][key]
        L.append(f"- **{q['name']}**：差 {_p(q.get('diff'))}（幅 {_p(q.get('lo'))}〜{_p(q.get('hi'))}・{q['ns'][0]:,}対{q['ns'][1]:,}回）・"
                 f"前半 {_p(q.get('early'))}／後半 {_p(q.get('late'))}（境 {q.get('cut')}）・その組の費用後 {_p(q.get('mean_a_cost'))}（ふつう {_p(q.get('mean_b_cost'))}） → **{q['verdict']}**")
    L += ["", "## 読むための表（判定しない）", "", "### 年ごとの差（寄り→大引け）", "", "| 年 | 高く寄った − ふつう | 安く寄った − ふつう | 回数 |", "|---|---:|---:|---:|"]
    for y, v in r["by_year"].items():
        L.append(f"| {y} | {_p(v['up1'])} | {_p(v['dn1'])} | {v['n']:,} |")
    L += ["", "### 前の日の売買代金ごと（寄り→大引けの平均・費用なし）", "", "| 売買代金 | 高く寄った | ふつう | 安く寄った |", "|---|---:|---:|---:|"]
    for lab, b in r["by_turnover"].items():
        L.append(f"| {lab} | " + " | ".join(f"{_p(b[k].get('mean'))}（{b[k]['n']:,}）" for k in ("up1", "base", "dn1")) + " |")
    L += ["", "- 窓の区分ごとの寄り→大引けの平均：" + "／".join(f"{lab} {_p(v.get('mean'))}（{v['n']:,}）" for lab, v in r["by_band"].items()),
          "- 参考＝J13 と同じ期間（" + f"{REF_FIRST}〜{REF_LAST}" + "）の寄り→大引けの差：" + "／".join(
              f"{key.upper()} {_p(v['diff'])}" for key, v in r["ref_j13_period"].items()) + "（J13 の寄り→10:00 は G1 −0.23％・G2 −0.22％・G3 +0.18％・G4 +0.32％）",
          "- 30件未満の区分は「—」。小さい株は売り買いの差が大きく、費用 0.1％ は甘い（判定は差なので費用は消える）。空売りは数えない。",
          "", "---", "", "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。"]
    return "\n".join(L) + "\n"


def main(argv):
    res = {"generated_at": dt.datetime.now(P.JST).isoformat(timespec="minutes"), "prereg_file": P.PREREG,
           "prereg_sha256": P.prereg_sha256(), "first_day": FIRST_DAY, "last_day": LAST_DAY}
    try:
        stocks, list_date = jp_bars.load_universe()
        codes = sorted(stocks)
        A, missing, drops = load(codes, jp_bars.fetcher())
        res["price_store"] = jp_bars.info()
        if "--diag" in argv:
            print(json.dumps(diag_summary(A, missing, len(codes)), ensure_ascii=False, indent=1))
            return 0
        if len(missing) > T.MAX_MISSING * len(codes):
            raise RuntimeError(f"日足を取れなかった銘柄が {len(missing)}/{len(codes)}＝5％超。偏った組で判定しない（取り直す）")
        res["result"] = dict(analyze(A), n_codes=len(codes), list_date=list_date, n_missing=len(missing), n_dropped=drops["n"])
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
