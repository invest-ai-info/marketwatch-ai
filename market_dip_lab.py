# -*- coding: utf-8 -*-
"""J25 相場全体が安く寄った朝の深い下げは戻るか（まだ使っていない 2006〜2016年の日足で確かめる）。
2026-10-07 登録・オーナー「一二を登録して続けてください」。PILLAR_PREREG.md「J25」（前向きは market_dip_forward.py＝J25F）。

相場全体が安く寄った朝＝その朝の全銘柄の窓（寄り値 ÷ 前日の終値 − 1）の中央値が −0.5％ 以下（500銘柄未満の朝は数えない）＝寄りの時点で分かる。
前日比 −5・−8・−10％ に買いの指値（付き方は J23 と同じ）→ 大引けに売る・費用は J24 の新しい見積もり。
判定（2006-01〜2016-10 の日足）＝Q1 安く寄った朝の費用後 ＞ 0／Q2 安く寄った朝 − それ以外の朝 ＞ 0（99.17％ の幅）。
2016〜2023 の日足・10:00・9:30 は読むための表（J23 で窓の安値で分けた形を見ている＝目隠しではない）。

⚠️ 決まりは PILLAR_PREREG.md「J25」と下の定数に固定。行は dip_lab（J23）、費用は cost_recount_lab（J24）と同じ。
⚠️ 出力（market-dip-lab.json / .md）は集計だけ・銘柄名とコードは出さない（SYNC禁忌）。

実行: python market_dip_lab.py --check   （点検だけ＝行数・安く寄った朝の数・指値が付いた回数。損益は数えない・何も書き出さない）
      python market_dip_lab.py           （本番。Actions の market-dip-lab.yml から手動で・1回だけ）
"""
import datetime as dt
import json
import sys

import numpy as np

import bounce_cost_lab as BC
import cost_recount_lab as CR
import dip_lab as D
import gap_lab as GL
import highs_trap_lab as T
import jp_bars
import pillar_lab as P
import prevday_lab as PD
import prevgap_lab as PG

OUT_JSON, OUT_MD = "market-dip-lab.json", "market-dip-lab.md"
FIRST = "2006-01-04"
E1 = ("2006-01-04", "2016-10-31")          # 確かめ（判定）
MKT_DOWN = -0.005                          # その朝の全銘柄の窓の中央値がこれ以下＝相場全体が安く寄った朝
LEVELS = (0.05, 0.08, 0.10)
N_Q = 2 * len(LEVELS)
ALPHA = 0.05 / N_Q                         # 99.17％ の幅
MIN_DOWN_DAYS = 20
OK, NONE = "✅ 2006〜2016年でも戻る（大引けまで・費用後）", "見えない"
DIFF_ONLY = "△ 差はあるが費用後プラスとは言えない"
ERAS = (("e1", "2006-01〜2016-10（日足・大引け）＝判定", "loday_r", "close_r"),
        ("e2", "2016-11〜2023-09（日足・大引け）", "loday_r", "close_r"),
        ("conf", "9:00〜10:00（1時間足）", "lo1000_r", "p1000_r"),
        ("main", "9:00〜9:30（5分足）", "lo930_r", "p930_r"))


# ════════════════════ 行 ════════════════════

def stock_rows(ci, daily, m5, h1, drops=None):
    """J23 の行（2006-01 から）で、費用の列を J24 の新しい見積もりに入れ替える → (行, 元の見積もり)"""
    A = D.stock_rows(ci, daily, m5, h1, drops=drops, first=FIRST)
    if not len(A):
        return A, np.zeros(0)
    old = A[:, D.C["spread"]].copy()
    A[:, D.C["spread"]] = CR._spread_for(A, D.C["day"], CR.ar_spread_avg(daily))
    return A, old


def market_gap(A):
    """→ (使う行の印, その朝の全銘柄の窓の中央値)。500銘柄未満の朝は使わない（J15〜J22 と同じ）"""
    day, gap = A[:, D.C["day"]], A[:, D.C["gap"]]
    order = np.argsort(day, kind="stable")
    uniq, starts, counts = np.unique(day[order], return_index=True, return_counts=True)
    med = np.array([np.median(gap[order[s:s + n]]) for s, n in zip(starts, counts)])
    idx = np.searchsorted(uniq, day)
    return (counts >= PG.MIN_STOCKS)[idx], med[idx]


def era_masks(A):
    S_, start = D.samples(A)
    day = A[:, D.C["day"]]
    sp = np.isfinite(A[:, D.C["spread"]])
    e1 = (np.isfinite(A[:, D.C["loday_r"]]) & np.isfinite(A[:, D.C["close_r"]]) & sp
          & (day >= PD._ord(E1[0])) & (day <= PD._ord(E1[1])))
    return {"e1": e1, "e2": S_["long"], "conf": S_["conf"], "main": S_["main"]}, start


# ════════════════════ 判定 ════════════════════

def measure2(A, v, a, b, alpha=ALPHA):
    """組 a − 組 b の平均の差（日と銘柄で引き直した広いほう）・前半と後半"""
    g = np.full(len(A), -1)
    g[b & np.isfinite(v)] = 1
    g[a & np.isfinite(v)] = 0
    ns = [int((g == 0).sum()), int((g == 1).sum())]
    out = {"ns": ns, "value": None, "lo": None, "hi": None, "early": None, "late": None}
    if min(ns) == 0:
        return out
    pt, lo_d, hi_d = GL.boot(v, g, 2, A[:, D.C["day"]], GL._diff2, alpha)
    _, lo_c, hi_c = GL.boot(v, g, 2, A[:, D.C["code"]], GL._diff2, alpha)
    days = np.unique(A[g >= 0, D.C["day"]])
    cut = days[len(days) // 2]
    d = A[:, D.C["day"]]

    def plain(m):
        x0, x1 = v[(g == 0) & m], v[(g == 1) & m]
        return float(x0.mean() - x1.mean()) if len(x0) and len(x1) else None
    out.update(value=pt, early=plain(d < cut), late=plain(d >= cut), by_day=[lo_d, hi_d], by_stock=[lo_c, hi_c])
    if None not in (lo_d, lo_c, hi_d, hi_c):
        out.update(lo=min(lo_d, lo_c), hi=max(hi_d, hi_c))
    return out


def up_ok(q, n_key="n"):
    """幅がまるごと0より上・前半と後半とも上・30件以上"""
    n = q[n_key] if n_key == "n" else min(q["ns"])
    return (q.get("lo") is not None and n >= T.MIN_N and q["lo"] > 0
            and (q.get("early") or 0) > 0 and (q.get("late") or 0) > 0)


def net_of(A, ret, spread):
    return ret - BC.cost(spread)


def _stats(v, m):
    x = v[m & np.isfinite(v)]
    return {"n": int(len(x)), "mean": float(x.mean()) if len(x) else None, "win": float((x > 0).mean()) if len(x) else None}


def analyze(A, old):
    keep, mg = market_gap(A)
    E, start = era_masks(A)
    down = keep & (mg <= MKT_DOWN)
    other = keep & (mg > MKT_DOWN)
    res = {"start_5m": dt.date.fromordinal(start).isoformat() if start else None, "eras": {}, "judge": {}, "summary": {}}
    for key, name, *_ in ERAS:
        m = E[key] & keep
        res["eras"][key] = {"name": name, "days": int(len(np.unique(A[m, D.C["day"]]))),
                            "down_days": int(len(np.unique(A[m & down, D.C["day"]]))), "rows": int(m.sum())}
    new_sp = A[:, D.C["spread"]]
    m1 = E["e1"]
    for x in LEVELS:
        k = f"{x:.2f}"
        ret, _ = D.limit_trades(A, x, "loday_r", "close_r")
        nv = net_of(A, ret, new_sp)
        q1 = D.measure(A, nv, m1 & down, alpha=ALPHA)
        q2 = measure2(A, nv, m1 & down, m1 & other)
        enough = res["eras"]["e1"]["down_days"] >= MIN_DOWN_DAYS
        ok1, ok2 = enough and up_ok(q1), enough and up_ok(q2, "ns")
        res["judge"][k] = {"q1": q1, "q2": q2, "q1_ok": bool(ok1), "q2_ok": bool(ok2)}
        res["summary"][k] = OK if ok1 and ok2 else DIFF_ONLY if ok2 else NONE
    res["reading"] = {}
    for key, _, lo_col, ex_col in ERAS:
        m = E[key]
        res["reading"][key] = {}
        for x in LEVELS:
            ret, at_open = D.limit_trades(A, x, lo_col, ex_col)
            nv, nv_old = net_of(A, ret, new_sp), net_of(A, ret, old)
            res["reading"][key][f"{x:.2f}"] = {
                "down": {"net": _stats(nv, m & down), "net_old": _stats(nv_old, m & down), "gross": _stats(ret, m & down),
                         "at_open_share": float(at_open[m & down & np.isfinite(ret)].mean()) if (m & down & np.isfinite(ret)).any() else None},
                "other": {"net": _stats(nv, m & other), "net_old": _stats(nv_old, m & other), "gross": _stats(ret, m & other)}}
    return res


# ════════════════════ 読む ════════════════════

def load(codes, fetch):
    parts, olds, missing, drops = [], [], {"daily": [], "h1": [], "m5": []}, {"n": 0}
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
        a, old = stock_rows(i, daily, T._by_day(m5), T._by_day(h1), drops=drops)
        parts.append(a)
        olds.append(old)
        if (i + 1) % 500 == 0:
            print(f"  ...{i + 1}/{len(codes)}", flush=True)
    A = np.vstack(parts) if parts else np.zeros((0, len(D.COLS)))
    return A, (np.concatenate(olds) if olds else np.zeros(0)), missing, drops


def check_summary(A, missing, n_codes, store):
    keep, mg = market_gap(A)
    E, start = era_masks(A)
    down = keep & (mg <= MKT_DOWN)
    out = {"n_codes": n_codes, "missing": {k: len(v) for k, v in missing.items()}, "rows": int(len(A)), "store": store,
           "start_5m": dt.date.fromordinal(start).isoformat() if start else None, "eras": {}}
    for key, _, lo_col, ex_col in ERAS:
        m = E[key] & keep
        fills = {}
        for x in LEVELS:
            ret, _ = D.limit_trades(A, x, lo_col, ex_col)
            f = m & np.isfinite(ret)
            fills[f"{x:.2f}"] = [int((f & down).sum()), int((f & ~down).sum())]
        out["eras"][key] = {"days": int(len(np.unique(A[m, D.C["day"]]))), "down_days": int(len(np.unique(A[m & down, D.C["day"]]))),
                            "rows": int(m.sum()), "fills_down_other": fills}
    return out


def _p(x, d=2):
    return D._p(x, d)


def _w(x):
    return D._w(x)


def _cell(s):
    return "—" if not s or not s["n"] else f"{_p(s['mean'])}・勝率 {_w(s['win'])}（{s['n']:,}回）"


def render_md(res):
    L = ["# J25 相場全体が安く寄った朝の深い下げは戻るか", "",
         f"作成: {res['generated_at']}（GitHub Actions で計算）。事前登録＝`{P.PREREG}`「J25」（指紋 sha256 `{(res.get('prereg_sha256') or '')[:16]}…`）。",
         "**相場全体が安く寄った朝＝その朝の全銘柄の窓の中央値が −0.5％ 以下**（寄りの時点で分かる）。前日比 −X％ に買いの指値・付いたら買って窓の終わりに売る。"
         "費用＝J24 の新しい見積もり（下限 往復 0.1％）。銘柄名は出しません。**売買の決まりではない**。", ""]
    r = res.get("result") or {}
    if r.get("error"):
        return "\n".join(L + [f"- ⚠️ 計算できず: {r['error']}", ""]) + "\n"
    L += [f"- 対象：置き場の一覧 {r.get('n_codes')}銘柄（いま上場している銘柄だけ）。取れなかった銘柄 {r.get('n_missing')}"]
    for key, e in r["eras"].items():
        L.append(f"- {e['name']}：{e['days']}朝のうち相場全体が安く寄った朝 {e['down_days']}朝（{e['rows']:,}行）")
    L += ["", "## まとめ（2006〜2016年の日足・大引けまで・幅 99.17％）", "",
          "| 指値 | Q1 安く寄った朝の費用後（幅） | 回数 | Q2 安く寄った朝 − それ以外（幅） | 回数（安く／それ以外） | まとめ |", "|---|---|---:|---|---|---|"]
    for x in LEVELS:
        k = f"{x:.2f}"
        j = r["judge"][k]
        q1, q2 = j["q1"], j["q2"]
        L.append(f"| 前日比 −{x * 100:.0f}％ | {_p(q1.get('value'))}（{_p(q1.get('lo'))}〜{_p(q1.get('hi'))}）{'✅' if j['q1_ok'] else ''} | {q1['n']:,} | "
                 f"{_p(q2.get('value'))}（{_p(q2.get('lo'))}〜{_p(q2.get('hi'))}）{'✅' if j['q2_ok'] else ''} | {q2['ns'][0]:,}／{q2['ns'][1]:,} | **{r['summary'][k]}** |")
    L += ["", "## 読むための表（費用後の平均・勝率・回数／J19 の見積もりの費用での平均／費用前）", ""]
    for key, name, *_ in ERAS:
        L += [f"### {name}", "", "| 指値 | 安く寄った朝 | 同（J19 の費用） | 同（費用前） | 寄りで買えた割合 | それ以外の朝 | 同（J19 の費用） | 同（費用前） |",
              "|---|---|---|---|---:|---|---|---|"]
        for x in LEVELS:
            v = r["reading"][key][f"{x:.2f}"]
            dn, ot = v["down"], v["other"]
            L.append(f"| −{x * 100:.0f}％ | {_cell(dn['net'])} | {_p(dn['net_old']['mean'])} | {_p(dn['gross']['mean'])} | {_w(dn['at_open_share'])} | "
                     f"{_cell(ot['net'])} | {_p(ot['net_old']['mean'])} | {_p(ot['gross']['mean'])} |")
        L.append("")
    L += ["- ⚠️ 日足の窓は1日で、オーナーの 9:00〜9:30 と違う（前向き J25F は 9:30 で数える）。いま上場している銘柄だけ。板の薄い株の安値の約定の数量は分からない。"
          "2016年以降の表は J23 で窓の安値で分けた形を見ている＝目隠しではない。",
          "", "---", "", "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。"]
    return "\n".join(L) + "\n"


def main(argv):
    res = {"generated_at": dt.datetime.now(P.JST).isoformat(timespec="minutes"), "prereg_file": P.PREREG,
           "prereg_sha256": P.prereg_sha256()}
    try:
        stocks, list_date = jp_bars.load_universe()
        codes = sorted(stocks)
        A, old, missing, drops = load(codes, jp_bars.fetcher())
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
        res["result"] = dict(analyze(A, old), n_codes=len(codes), list_date=list_date,
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
