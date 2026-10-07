# -*- coding: utf-8 -*-
"""J19 安く寄った株の戻りは、銘柄ごとの売り買いの差を引いても残るか（2006〜2016年で形を選び、2016〜2026年で確かめる）。
2026-10-07 登録・オーナー「続けてください」（研究の加速）。PILLAR_PREREG.md「J19」。

費用＝Abdi & Ranaldo (2017) の高値・安値・終値から見積もる売り買いの差（その朝より前の60営業日の平均・下限 往復0.1％）。
形＝窓の深さ3 × 売買代金3 × 前の日の動き3 ＝27通りを 2006〜2016年（寄り→大引け）だけで選び、
選んだ1つを 2016〜2023年（寄り→大引け）と 2023〜2026年（寄り→10:00）で1回だけ確かめる（97.5％の幅・日と銘柄の広いほう）。

⚠️ 決まりは PILLAR_PREREG.md「J19」と下の定数に固定。行の作り方は prevday_lab（J16）、その銘柄だけの窓は prevgap_lab（J17）をそのまま使う。
⚠️ 出力（bounce-cost-lab.json / .md）は集計だけ・銘柄名とコードは出さない（SYNC禁忌）。

実行: python bounce_cost_lab.py --check   （点検だけ＝行数・費用の見積もり・形ごとの回数。損益は数えない・何も書き出さない）
      python bounce_cost_lab.py           （本番。Actions の bounce-cost-lab.yml から手動で・1回だけ）
      python bounce_cost_lab.py --relist  （数え直さずに、書き出した結果へ検証済みリストの欄を足す）
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

OUT_JSON, OUT_MD = "bounce-cost-lab.json", "bounce-cost-lab.md"
SELECT = ("2006-01-04", "2016-10-31")     # 形を選ぶ（寄り→大引け）
CONFIRM = (("b", "確かめ1 2016-11〜2023-09（寄り→大引け）", PD.OLD, "rclose"),
           ("c", "確かめ2 2023-10〜2026-10（寄り→10:00）", PD.NEW, "r1000"))
COLS = PD.COLS + ("spread",)
C = {k: i for i, k in enumerate(COLS)}
WINDOW = 60          # 見積もりに使う、その朝より前の営業日
MIN_OBS = 20         # 出来高のある日がこれ未満なら見積もらない
COST_FLOOR = 0.001   # 往復 0.1％
MIN_TRADES = 2000
N_Q = 2
ALPHA = 0.05 / N_Q   # 97.5％ の幅
DEPTH = (("D1", "−1％以下", -0.01), ("D2", "−2％以下", -0.02), ("D3", "−3％以下", -0.03))
LIQ = (("L0", "売買代金を問わない", 0.0), ("L1", "1億円以上", 1.0), ("L2", "10億円以上", 10.0))
PREV = (("V0", "前の日を問わない"), ("V1", "前の日 −5％以下"), ("V2", "前の日 +5％以上を除く"))
BASE = "D1-L0-V0"
OK, NONE = "✅ 費用後もプラス", "見えない"
BOTH, ONE, GONE, NOSEL = "✅ 2つの期間で費用後もプラス", "△ 片方の期間だけ", "費用で消える", "選べる形なし"


# ════════════════════ 費用の見積もり ════════════════════

def ar_spread(daily, window=WINDOW, min_obs=MIN_OBS):
    """Abdi & Ranaldo (2017)。daily＝[(日付, 始, 高, 安, 終, 出来高)]（日付の順）→ {日付: その朝より前の window 営業日の見積もり}。
    2日ごとの見積もり s_t＝√max(4(c_t−η_t)(c_t−η_{t+1}), 0)（c＝終値の対数・η＝高値と安値の対数の真ん中）。
    朝 j に使うのは t+1 ≤ j−1 の s_t（その朝より前の値だけ）。出来高0の日（t か t+1）は使わない"""
    n = len(daily)
    out = {}
    if n < 3:
        return out
    c = np.log(np.array([r[4] for r in daily], float))
    eta = (np.log(np.array([r[2] for r in daily], float)) + np.log(np.array([r[3] for r in daily], float))) / 2
    vol = np.array([r[5] or 0 for r in daily], float)
    x = 4 * (c[:-1] - eta[:-1]) * (c[:-1] - eta[1:])
    s = np.sqrt(np.maximum(x, 0))
    ok = (vol[:-1] > 0) & (vol[1:] > 0) & np.isfinite(s)
    sv = np.where(ok, s, 0.0)
    cs = np.concatenate([[0.0], np.cumsum(sv)])
    cn = np.concatenate([[0], np.cumsum(ok.astype(int))])
    for j in range(2, n):
        hi = j - 1                      # s_t は t ≤ j−2（cs の添え字は hi＝j−1 まで）
        lo = max(0, hi - window)
        k = cn[hi] - cn[lo]
        if k >= min_obs:
            out[daily[j][0]] = float((cs[hi] - cs[lo]) / k)
    return out


def cost(spread):
    return np.maximum(spread, COST_FLOOR)


# ════════════════════ 形 ════════════════════

def rules():
    return [(f"{d}-{l}-{v}", dv, lv, v) for d, _, dv in DEPTH for l, _, lv in LIQ for v, _ in PREV]


def rule_label(key):
    d, l, v = key.split("-")
    return "・".join([dict((a, b) for a, b, _ in DEPTH)[d], dict((a, b) for a, b, _ in LIQ)[l], dict(PREV)[v]])


def rule_mask(A, idio, key):
    d, l, v = key.split("-")
    depth = dict((a, c) for a, _, c in DEPTH)[d]
    liq = dict((a, c) for a, _, c in LIQ)[l]
    m = (idio <= depth) & (A[:, C["turnover"]] >= liq) & np.isfinite(A[:, C["spread"]])
    rp = A[:, C["rprev"]]
    if v == "V1":
        m &= rp <= -0.05
    elif v == "V2":
        m &= rp < 0.05
    return m


def net(A, col):
    return A[:, C[col]] - cost(A[:, C["spread"]])


def _span(A, span):
    d = A[:, C["day"]]
    return (d >= PD._ord(span[0])) & (d <= PD._ord(span[1]))


def summarize(A, m, col):
    """形の回数・費用前・費用・費用後の平均と、期間の前半と後半の費用後の平均（点だけ）"""
    v = A[:, C[col]]
    m = m & np.isfinite(v)
    if not m.any():
        return {"n": 0}
    nv = net(A, col)[m]
    days = A[m, C["day"]]
    cut = np.unique(days)[len(np.unique(days)) // 2]
    return {"n": int(m.sum()), "gross": float(v[m].mean()), "cost": float(cost(A[m, C["spread"]]).mean()),
            "net": float(nv.mean()), "early": float(nv[days < cut].mean()) if (days < cut).any() else None,
            "late": float(nv[days >= cut].mean()) if (days >= cut).any() else None}


def select(grid):
    """2,000回以上・前半後半とも費用後がプラスの形のうち、費用後の平均がいちばん高いもの（無ければ None）"""
    ok = [(k, g) for k, g in grid.items() if g["n"] >= MIN_TRADES and (g.get("early") or 0) > 0 and (g.get("late") or 0) > 0]
    return max(ok, key=lambda kg: kg[1]["net"])[0] if ok else None


def confirm(A, m, col):
    """費用後の1回あたりの平均と 97.5％ の幅（日と銘柄で引き直した広いほう）"""
    q = summarize(A, m, col)
    if q["n"] < T.MIN_N:
        return dict(q, verdict="件数不足")
    v = net(A, col)
    g = np.where(m & np.isfinite(A[:, C[col]]), 0, -1)
    one = (lambda mu: mu[0])
    pt, lo_d, hi_d = GL.boot(v, g, 1, A[:, C["day"]], one, ALPHA)
    _, lo_c, hi_c = GL.boot(v, g, 1, A[:, C["code"]], one, ALPHA)
    if None in (lo_d, lo_c):
        return dict(q, verdict="件数不足")
    lo, hi = min(lo_d, lo_c), max(hi_d, hi_c)
    return dict(q, lo=lo, hi=hi, by_day=[lo_d, hi_d], by_stock=[lo_c, hi_c], verdict=OK if lo > 0 else NONE)


def overall(vb, vc):
    a, b = vb == OK, vc == OK
    if a and b:
        return BOTH
    if a or b:
        return ONE
    return GONE


def analyze(A):
    A, idio = PG.idio_gap(A)
    sel_m = _span(A, SELECT)
    res = {"grid": {}}
    for key, *_ in rules():
        res["grid"][key] = summarize(A, sel_m & rule_mask(A, idio, key), "rclose")
    chosen = select(res["grid"])
    res["chosen"] = chosen
    res["confirm"] = {}
    if chosen is None:
        res["overall"] = NOSEL
    else:
        for k, name, span, col in CONFIRM:
            q = confirm(A, _span(A, span) & rule_mask(A, idio, chosen), col)
            res["confirm"][k] = dict(q, name=name)
        res["overall"] = overall(res["confirm"]["b"]["verdict"], res["confirm"]["c"]["verdict"])
    # ── 読むための表（判定しない）──
    res["base"] = {k: summarize(A, _span(A, span) & rule_mask(A, idio, BASE), col) for k, _, span, col in CONFIRM}
    if chosen:
        ms = _span(A, PD.NEW) & rule_mask(A, idio, chosen)
        res["c_930"] = summarize(A, ms, "r930")
    res["cost_by_turnover"] = {}
    for name, span in (("select", SELECT), ("b", PD.OLD), ("c", PD.NEW)):
        m0 = _span(A, span) & np.isfinite(A[:, C["spread"]])
        tv, sp = A[:, C["turnover"]], A[:, C["spread"]]
        res["cost_by_turnover"][name] = {lab: (float(np.median(cost(sp[m0 & (tv >= lo) & (tv < hi)])))
                                               if (m0 & (tv >= lo) & (tv < hi)).any() else None) for lab, lo, hi in S.TURNOVER_BANDS}
    res["periods"] = {name: {"rows": int(_span(A, span).sum()), "with_cost": int((_span(A, span) & np.isfinite(A[:, C["spread"]])).sum())}
                      for name, span in (("select", SELECT), ("b", PD.OLD), ("c", PD.NEW))}
    return res


def listing(res, today):
    """検証済みリスト（verified_list.SOURCES）が読む欄。「費用で消える」「選べる形なし」だけストップとして載せる"""
    r = res.get("result") or {}
    out = {"kind": "backtest", "section": "J19", "titles": {"J19": "その銘柄だけ −1％以下安く寄った株を寄りで買う（銘柄ごとの売り買いの差を引く・2006〜2016年で27通りから選ぶ）"},
           "verdicts": {}}
    if r.get("overall") in (GONE, NOSEL):
        g = (r.get("grid") or {}).get(BASE) or {}
        b, c = (r.get("base") or {}).get("b") or {}, (r.get("base") or {}).get("c") or {}
        why = "27通りとも費用後プラスの形が無い（選べる形なし）" if r["overall"] == NOSEL else "選んだ形が確かめの期間で費用後プラスにならない"
        out["verdicts"]["J19"] = {"status": "stop", "decided_on": today, "n": g.get("n"), "mean": g.get("net"), "lo": None, "hi": None,
                                  "reason": f"過去のデータで1回だけ数えて{why}（いちばん広い形の費用後 2006〜2016 {_p(g.get('net'))}・"
                                            f"2016〜2023 {_p(b.get('net'))}・2023〜2026 {_p(c.get('net'))}・費用は推定で大きい株では重めの可能性）"}
    return out


def relist(path=OUT_JSON):
    """数え直さずに、書き出した結果へ検証済みリストの欄を足す（2026-10-07：1回目の本番のあとに欄を足したため）"""
    with open(path, encoding="utf-8") as fh:
        res = json.load(fh)
    res.update(listing(res, dt.datetime.now(P.JST).date().isoformat()))
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1, default=str)
    return res


# ════════════════════ 読む ════════════════════

def stock_rows(ci, daily, m5, h1, drops=None):
    """J16 の行（2006-01〜2026-10）＋その朝の費用の見積もり"""
    A = PD.stock_rows(ci, daily, m5, h1, first=SELECT[0], last=PD.NEW[1], recent_from=PD.NEW[0], drops=drops)
    sp = {dt.date.fromisoformat(d).toordinal(): v for d, v in ar_spread(daily).items()}
    col = np.array([sp.get(int(o), np.nan) for o in A[:, PD.C["day"]]], float).reshape(-1, 1)
    return np.hstack([A, col]) if len(A) else np.zeros((0, len(COLS)))


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
           "store": store, "periods": {}, "select_counts": {}}
    for name, span, col in (("select", SELECT, "rclose"), ("b", PD.OLD, "rclose"), ("c", PD.NEW, "r1000")):
        m = _span(B, span)
        sp = B[m, C["spread"]]
        out["periods"][name] = {"rows": int(m.sum()), "with_cost": int(np.isfinite(sp).sum()),
                                "with_exit": int((m & np.isfinite(B[:, C[col]])).sum()),
                                "cost_median": float(np.median(cost(sp[np.isfinite(sp)]))) if np.isfinite(sp).any() else None}
    ms = _span(B, SELECT)
    out["select_counts"] = {k: int((ms & rule_mask(B, idio, k)).sum()) for k, *_ in rules()}
    return out


def _p(x, d=2):
    return Y._pct(x, d)


def render_md(res):
    L = ["# J19 安く寄った株の戻りは、銘柄ごとの売り買いの差を引いても残るか", "",
         f"作成: {res['generated_at']}（GitHub Actions で計算）。事前登録＝`{P.PREREG}`「J19」（指紋 sha256 `{(res.get('prereg_sha256') or '')[:16]}…`）。",
         "銘柄名は出しません。値は株価の変化率（％）。費用＝銘柄ごとに見積もった売り買いの差（往復・下限 0.1％）。**売買の決まりではない**。", ""]
    r = res.get("result") or {}
    if r.get("error"):
        return "\n".join(L + [f"- ⚠️ 計算できず: {r['error']}", ""]) + "\n"
    ps, pe = res.get("price_store") or {}, r["periods"]
    L += [f"- 対象：置き場の一覧 {r.get('n_codes')}銘柄（いま上場している銘柄だけ）。取れなかった銘柄 {r.get('n_missing')}。値段の置き場：{ps.get('built_at') or '使わず'}",
          f"- 朝の数（費用を見積もれた朝）：選ぶ {pe['select']['rows']:,}（{pe['select']['with_cost']:,}）／確かめ1 {pe['b']['rows']:,}（{pe['b']['with_cost']:,}）／確かめ2 {pe['c']['rows']:,}（{pe['c']['with_cost']:,}）",
          f"- 確かめの幅は97.5％（p＜0.05÷2）・日と銘柄で引き直した広いほう。±25％超で捨てた値 {r.get('n_dropped')}", "",
          "## まとめ", ""]
    if r["chosen"] is None:
        L += [f"- **{NOSEL}**（2,000回以上・前半後半とも費用後プラスの形が無い）", ""]
    else:
        L += [f"- **選んだ形（2006〜2016年）**：{rule_label(r['chosen'])}（`{r['chosen']}`）",
              f"- **{r['overall']}**", "", "## 確かめ（事前登録の2つ）", ""]
        for k, *_ in CONFIRM:
            q = r["confirm"][k]
            L.append(f"- **{q['name']}**：費用後 {_p(q.get('net'))}（幅 {_p(q.get('lo'))}〜{_p(q.get('hi'))}・{q['n']:,}回）・費用前 {_p(q.get('gross'))}・費用 {_p(q.get('cost'))}"
                     f"・前半 {_p(q.get('early'))}／後半 {_p(q.get('late'))} → **{q['verdict']}**")
        if r.get("c_930", {}).get("n"):
            c9 = r["c_930"]
            L.append(f"- 読むだけ：確かめ2 の5分足の寄り→9:30 ＝費用後 {_p(c9['net'])}（{c9['n']:,}回・費用前 {_p(c9['gross'])}）")
    L += ["", "## 読むための表（判定しない）", "", "### 選ぶ期間（2006〜2016年・寄り→大引け）の27通り", "",
          "| 形 | 回数 | 費用前 | 費用 | 費用後 | 前半 | 後半 |", "|---|---:|---:|---:|---:|---:|---:|"]
    for k, g in r["grid"].items():
        mark = " ◀" if k == r["chosen"] else ""
        L.append(f"| {rule_label(k)}{mark} | {g['n']:,} | {_p(g.get('gross'))} | {_p(g.get('cost'))} | {_p(g.get('net'))} | {_p(g.get('early'))} | {_p(g.get('late'))} |")
    L += ["", "### いちばん広い形（その銘柄だけ −1％以下・ほかは問わない）", "", "| 期間 | 回数 | 費用前 | 費用 | 費用後 |", "|---|---:|---:|---:|---:|"]
    for k, name, *_ in CONFIRM:
        b = r["base"][k]
        L.append(f"| {name} | {b.get('n', 0):,} | {_p(b.get('gross'))} | {_p(b.get('cost'))} | {_p(b.get('net'))} |")
    L += ["", "### 見積もった往復の費用の中央値（売買代金ごと）", "", "| 売買代金 | 2006〜2016 | 2016〜2023 | 2023〜2026 |", "|---|---:|---:|---:|"]
    for lab, *_ in S.TURNOVER_BANDS:
        L.append(f"| {lab} | " + " | ".join(_p(r["cost_by_turnover"][n][lab]) for n in ("select", "b", "c")) + " |")
    L += ["", "- 費用は推定（寄りの板の厚さ＝大きく買うと値が動く分は入らない）。⚠️ いま上場している銘柄だけ（生き残りの偏り）。空売りは数えない。",
          "", "---", "", "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。"]
    return "\n".join(L) + "\n"


def main(argv):
    if "--relist" in argv:
        res = relist()
        print(json.dumps(res.get("verdicts"), ensure_ascii=False, indent=1))
        return 0
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
    res.update(listing(res, dt.datetime.now(P.JST).date().isoformat()))
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1, default=str)
    md = render_md(res)
    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
