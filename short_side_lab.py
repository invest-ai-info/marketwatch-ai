# -*- coding: utf-8 -*-
"""J30 「寄りで買わない」目印の付いた株を、寄りで売る（空売り）と費用のあとも残るか。
2026-10-08 登録・オーナー「一、二。に進めてください」。PILLAR_PREREG.md「J30」。

目印（点検表 日本株⑤）＝K1 A その銘柄だけ +1％以上高く寄った／K2 B 前の日 +5％以上かつ A／K3 C 前の日の売買代金が
その前の20営業日の平均の5倍以上。範囲＝P1 前の日の売買代金1億円以上・P2 10億円以上。3つの時代（E1 2006〜2016・
E2 2016〜2023〔寄り→大引け〕・E3 2023〜2026〔寄り→10:00〕）で、寄りで売って買い戻した損益から、売り買いの差
（J29 と同じ重いほう・軽いほう）と貸株料など 0.01％を引く。**目隠しではない＝判定ではなく数え直し**。

⚠️ 決まりは PILLAR_PREREG.md「J30」と下の定数に固定。行・費用・幅は J29（bounce_range_lab）と J24（cost_recount_lab）を
   そのまま使い、倍率は J26 と同じ landmine_lab.prev_more。目印の数字は点検表と同じ（ここで変えない）。
⚠️ 出力（short-side-lab.json / .md）は集計だけ・銘柄名とコードは出さない（SYNC禁忌）。

実行: python short_side_lab.py --check   （点検だけ＝行数と組ごとの件数。損益は数えない・何も書き出さない）
      python short_side_lab.py           （本番。Actions の short-side-lab.yml から手動で・1回だけ）
"""
import datetime as dt
import json
import sys

import numpy as np

import bounce_cost_lab as BC
import bounce_range_lab as BR
import cost_recount_lab as CR
import highs_trap_lab as T
import highs_trap_small as S
import jp_bars
import landmine_lab as LM
import pillar_lab as P
import prevgap_lab as PG
import yori_lab as Y

OUT_JSON, OUT_MD = "short-side-lab.json", "short-side-lab.md"
COLS = BC.COLS + ("tv_ratio",)
C = {k: i for i, k in enumerate(COLS)}
ERAS, READ_ERA = BR.ERAS, BR.READ_ERA
IDIO, PREV_BIG, TV_HIGH = 0.01, 0.05, 5.0            # 点検表 日本株⑤ と同じ
MARKS = (("K1", "目印A その銘柄だけ +1％以上高く寄った"),
         ("K2", "目印B 前の日 +5％以上かつ、その銘柄だけ +1％以上高く寄った"),
         ("K3", "目印C 前の日の売買代金が20営業日平均の5倍以上"))
POPS = (("P1", "前の日の売買代金1億円以上", 1.0), ("P2", "10億円以上", 10.0))
BORROW = 0.0001                                       # 貸株料など（年3.65％の1日分）
N_Q = len(MARKS) * len(POPS)
ALPHA = 0.05 / N_Q                                    # 99.17％ の幅
COSTS = BR.COSTS
OK_BOTH, OK_LOW, NONE = BR.OK_BOTH, BR.OK_LOW, BR.NONE


# ════════════════════ 行・目印 ════════════════════

def stock_rows(ci, daily, m5, h1, sp, drops=None):
    """J24・J29 の行（cost_recount_lab.rows_j19）＋前の日の売買代金の倍率（landmine_lab.prev_more・J26 と同じ合わせ方）"""
    A = CR.rows_j19(ci, daily, m5, h1, sp, drops=drops)
    if not len(A):
        return np.zeros((0, len(COLS)))
    ratio = LM.prev_more(daily)[0]
    pos = {dt.date.fromisoformat(r[0]).toordinal(): i for i, r in enumerate(daily)}
    k = np.array([pos[int(o)] - 1 for o in A[:, C["day"]]])
    return np.hstack([A, ratio[k].reshape(-1, 1)])


def marks(A, idio):
    rp, ratio = A[:, C["rprev"]], A[:, C["tv_ratio"]]
    with np.errstate(invalid="ignore"):
        k3 = np.isfinite(ratio) & (ratio >= TV_HIGH)
    return {"K1": idio >= IDIO, "K2": (rp >= PREV_BIG) & (idio >= IDIO), "K3": k3}


def pops(A):
    tv = A[:, C["turnover"]]
    return {p: tv >= lo for p, _, lo in POPS}


# ════════════════════ 数える ════════════════════

def short_net(A, col, cost):
    """売りの費用後の損益＝−（買い戻し÷寄り−1）− 売り買いの差 − 貸株料など"""
    return -A[:, C[col]] - cost - BORROW


def _short_plain(A, col, m):
    return BR._plain(-A[:, C[col]], m)


def analyze(A):
    A, idio = PG.idio_gap(A)
    high, low = BR.costs(A)
    mk, pp = marks(A, idio), pops(A)
    res = {"eras": {}, "groups": {}, "reading": {}}
    for key, name, span, col in ERAS + (READ_ERA,):
        em = BR.era_mask(A, span) & np.isfinite(A[:, C[col]])
        days = np.unique(A[em, C["day"]])
        res["eras"][key] = {"name": name, "days": int(len(days)), "rows": int(em.sum()),
                            "first": dt.date.fromordinal(int(days[0])).isoformat() if len(days) else None,
                            "last": dt.date.fromordinal(int(days[-1])).isoformat() if len(days) else None}
    for g, gname in MARKS:
        for p, pname, _ in POPS:
            sel = mk[g] & pp[p]
            by_era, read = {}, {}
            for key, name, span, col in ERAS + (READ_ERA,):
                m = BR.era_mask(A, span) & sel
                ok = m & np.isfinite(A[:, C[col]])
                q = {c: BR.net_mean(A, short_net(A, col, high if c == "high" else low), m, alpha=ALPHA) for c, _ in COSTS}
                q.update(gross=_short_plain(A, col, m), cost={"high": BR._med(high[ok]), "low": BR._med(low[ok])})
                (read if key == READ_ERA[0] else by_era)[key] = q
            res["groups"][f"{g}-{p}"] = {"mark": g, "name": gname, "pop": p, "pop_name": pname, "eras": by_era, "read": read,
                                         "summary": BR.summary_of(by_era)}
    # 読むための表（判定しない）：軽いほうの費用後（E2・E3）を、売買代金・窓の大きさ・倍率・B と C の重なりで
    tv, gap_i, ratio = A[:, C["turnover"]], idio, A[:, C["tv_ratio"]]
    with np.errstate(invalid="ignore"):
        cuts = {"K1": (("+1〜+3％", (gap_i >= IDIO) & (gap_i < 0.03)), ("+3％以上", gap_i >= 0.03)),
                "K3": (("5〜10倍", (ratio >= TV_HIGH) & (ratio < 10)), ("10倍以上", ratio >= 10)),
                "K2": (("B かつ C", mk["K2"] & mk["K3"]), ("B で C でない", mk["K2"] & ~mk["K3"]))}
    for g, _ in MARKS:
        rd = {}
        for key, name, span, col in ERAS[1:] + (READ_ERA,):
            v = short_net(A, col, low)
            base = BR.era_mask(A, span) & mk[g] & pp["P1"]
            rd[key] = {"turnover": {lab: BR._plain(v, base & (tv >= lo) & (tv < hi)) for lab, lo, hi in S.TURNOVER_BANDS[1:]},
                       "cut": {lab: BR._plain(v, base & c) for lab, c in cuts[g]}}
        res["reading"][g] = rd
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
        parts.append(stock_rows(i, daily, T._by_day(m5), T._by_day(h1), CR.ar_spread_avg(daily), drops=drops))
        if (i + 1) % 500 == 0:
            print(f"  ...{i + 1}/{len(codes)}", flush=True)
    A = np.vstack(parts) if parts else np.zeros((0, len(COLS)))
    return A, missing, drops


def check_summary(A, missing, n_codes, store):
    """点検だけ＝行数と組ごとの件数（損益は数えない）"""
    B, idio = PG.idio_gap(A)
    mk, pp = marks(B, idio), pops(B)
    out = {"n_codes": n_codes, "missing": {k: len(v) for k, v in missing.items()}, "rows": int(len(A)), "store": store, "eras": {}}
    for key, name, span, col in ERAS + (READ_ERA,):
        em = BR.era_mask(B, span) & np.isfinite(B[:, C[col]]) & np.isfinite(B[:, C["spread"]])
        out["eras"][key] = {"days": int(len(np.unique(B[em, C["day"]]))), "rows": int(em.sum()),
                            "groups": {f"{g}-{p}": int((em & mk[g] & pp[p]).sum()) for g, _ in MARKS for p, *_ in POPS}}
    return out


# ════════════════════ 書く ════════════════════

def _p(x, d=2):
    return Y._pct(x, d) if x is not None else "—"


def _band(q):
    return "—" if q.get("lo") is None else f"{_p(q['lo'])}〜{_p(q['hi'])}"


def render_md(res):
    L = ["# J30 「寄りで買わない」目印の付いた株を、寄りで売る（空売り）と費用のあとも残るか", "",
         f"更新: {res.get('generated_at', '')}（事前登録＝`PILLAR_PREREG.md`「J30」・指紋 `{(res.get('prereg_sha256') or '')[:12]}`）", ""]
    r = res.get("result") or {}
    if "error" in r:
        return "\n".join(L + [f"⚠️ 計算できず：{r['error']}", "", "※ 研究の記録です。投資助言ではありません。"]) + "\n"
    L += ["**目隠しではない＝判定ではなく数え直し**（同じデータを J14〜J29 で見ている）。プラスでも売買の決まりにはせず、空売りの前向きを別に登録して確かめる。",
          "数字は寄りで売って大引け（E1・E2）／10:00（E3）に買い戻したときの、費用後の1回あたりの損益率の平均（プラス＝売りが勝った）。"
          f"幅は 99.17％（日と銘柄で引き直した広いほう）。売り買いの差＝重いほう（J24）・軽いほう（J24 × J28 の比）・どちらも下限 往復0.1％。"
          f"ほかに貸株料など {BORROW * 100:.2f}％。", ""]
    for key, e in r["eras"].items():
        L.append(f"- {e['name']}：{e['first']}〜{e['last']}・{e['days']:,}営業日・{e['rows']:,}朝")
    L += ["", "## まとめ", "", "| 目印 | 範囲 | まとめ |", "|---|---|---|"]
    for key, x in r["groups"].items():
        L.append(f"| {x['mark']} {x['name']} | {x['pop']} {x['pop_name']} | **{x['summary']}** |")
    for key, x in r["groups"].items():
        L += ["", f"## {x['mark']} {x['name']}（{x['pop_name']}）", "",
              "| 時代 | 件数 | 費用前の売り（勝った割合） | 費用の中央値（重い／軽い） | 重いほうの費用後 | 99.17％の幅 | 軽いほうの費用後 | 99.17％の幅 | 前半／後半（重いほう） |",
              "|---|---:|---|---|---:|---|---:|---|---|"]
        for ek, q in list(x["eras"].items()) + list(x["read"].items()):
            gr = q["gross"]
            win = "—" if gr["win"] is None else f"{gr['win'] * 100:.0f}％"
            L.append(f"| {r['eras'][ek]['name']} | {q['high']['n']:,} | {_p(gr['mean'])}（{win}） | {_p(q['cost']['high'])}／{_p(q['cost']['low'])} | "
                     f"{_p(q['high']['value'])} | {_band(q['high'])} | {_p(q['low']['value'])} | {_band(q['low'])} | "
                     f"{_p(q['high'].get('early'))}／{_p(q['high'].get('late'))} |")
    L += ["", "## 読むための表（判定しない）：軽いほうの費用後（前の日の売買代金1億円以上）", "",
          "| 目印 | 時代 | 1〜10億円 | 10億円以上 | 分け方 | 分けた2つ |", "|---|---|---:|---:|---|---|"]
    for g, _ in MARKS:
        for ek, rd in r["reading"][g].items():
            tvs = [("—" if c["mean"] is None else f"{_p(c['mean'])}（{c['n']:,}）") for c in rd["turnover"].values()]
            cut = "／".join(f"{lab} {'—' if c['mean'] is None else _p(c['mean'])}（{c['n']:,}）" for lab, c in rd["cut"].items())
            L.append(f"| {g} | {r['eras'][ek]['name']} | {tvs[0]} | {tvs[1]} | {'窓の大きさ' if g == 'K1' else '倍率' if g == 'K3' else 'C との重なり'} | {cut} |")
    L += ["", "## 注意", "",
          "- 昔の時代に、その銘柄が売れた（貸借銘柄だった・在庫があった）かはわからない。いま上場している銘柄だけ（生き残りの偏り）",
          "- 寄りの売りは寄り値で付く前提（実際は気配を見て寄りの前に注文する＝A・B は気配と寄り値がずれることがある）",
          "- 軽いほうの比は最近の約60日の5分足から出したもの。5分足の見積もりは取引の少ない足で0に寄りやすい＝軽いほうは軽すぎる可能性がある",
          "- 逆日歩・売り禁は入れていない（日計りなら逆日歩はかからない）", "", "---", "",
          "※ 研究の記録です。投資助言ではありません。空売りは損失が限られない取引です。将来の成績を約束するものではありません。"]
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
        if len(set(missing["daily"]) | set(missing["h1"])) > T.MAX_MISSING * len(codes):
            raise RuntimeError("日足か1時間足を取れなかった銘柄が5％超。偏った組で数えない（取り直す）")
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
