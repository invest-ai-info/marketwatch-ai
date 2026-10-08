# -*- coding: utf-8 -*-
"""J34 J31 の売りの取り分は、相場全体の下げの分か、目印の株ならではか。2026-10-08 登録・オーナー「続けてください」。
PILLAR_PREREG.md「J34」。

相場全体の寄り→大引け＝その朝の前の日の売買代金10億円以上の全銘柄の平均（30銘柄未満の朝は数えない）。
相場全体を差し引いた売りの損益＝−（その株の寄り→大引け − 相場全体）− 0.03％。組＝J31 の K2-P2（目印B）・K3-P2（目印C）。
**目隠しではない**（同じ取引を J31 で数えた）。

⚠️ 決まりは PILLAR_PREREG.md「J34」と下の定数に固定。行・組・幅は J31（auction_lab）・J32（stop_short_lab）・J29（bounce_range_lab）
   の関数をそのまま使う。
⚠️ 出力（market-adj-lab.json / .md）は集計だけ・銘柄名とコードは出さない（SYNC禁忌）。

実行: python market_adj_lab.py --check   （点検だけ＝行数と組ごとの件数。損益は数えない・何も書き出さない）
      python market_adj_lab.py           （本番。Actions の market-adj-lab.yml から手動で・1回だけ）
"""
import datetime as dt
import json
import sys

import numpy as np

import auction_lab as AU
import bounce_range_lab as BR
import highs_trap_lab as T
import jp_bars
import pillar_lab as P
import prevgap_lab as PG
import stop_short_lab as SS
import yori_lab as Y

OUT_JSON, OUT_MD = "market-adj-lab.json", "market-adj-lab.md"
C = AU.C
ERAS = AU.ERAS
BIG = 10.0                    # 相場全体＝前の日の売買代金10億円以上の銘柄
MIN_BIG = 30
COST = AU.SHORT_COST          # 0.03％
N_Q = 2
ALPHA = 0.05 / N_Q            # 97.5％ の幅
DAY_BANDS = (("上げた日（+0.5％以上）", 0.005, 9.0), ("ふつうの日（±0.5％未満）", -0.005, 0.005), ("下げた日（−0.5％以下）", -9.0, -0.005))
WEEKDAYS = "月火水木金"
OK_ALL, OK_OLD, NONE = "✅ 目印の株ならではの下げ", "△ 昔だけ（最近は届かない）", "✕ 相場全体の分と区別できない"


def market(A):
    """→ 各行のその朝の相場全体の寄り→大引け（大きい株が MIN_BIG 未満の朝は NaN）"""
    day = A[:, C["day"]]
    uniq, inv = np.unique(day, return_inverse=True)
    big = (A[:, C["turnover"]] >= BIG) & np.isfinite(A[:, C["rclose"]])
    n = np.bincount(inv, weights=big.astype(float), minlength=len(uniq))
    s = np.bincount(inv, weights=np.where(big, A[:, C["rclose"]], 0.0), minlength=len(uniq))
    with np.errstate(invalid="ignore", divide="ignore"):
        mk = np.where(n >= MIN_BIG, s / np.maximum(n, 1), np.nan)
    return mk[inv]


def nets(A, mkt):
    """→ (差し引く前の売り, 差し引いたあとの売り)"""
    rc = A[:, C["rclose"]]
    return -rc - COST, -(rc - mkt) - COST


def summary_of(by_era):
    plus = [q.get("lo") is not None and q["lo"] > 0 for q in (by_era["e1"], by_era["e2"], by_era["e3"])]
    if all(plus):
        return OK_ALL
    if plus[0] and plus[1]:
        return OK_OLD
    return NONE


def analyze(A):
    A, idio = PG.idio_gap(A)
    mkt = market(A)
    sel = SS.groups(A, idio)
    raw, adj = nets(A, mkt)
    day = A[:, C["day"]]
    years = np.array([dt.date.fromordinal(int(d)).year for d in day]) if len(day) else np.zeros(0, int)
    wday = np.array([dt.date.fromordinal(int(d)).weekday() for d in day]) if len(day) else np.zeros(0, int)
    res = {"eras": {}, "groups": {}}
    for key, name, span in ERAS:
        em = AU.era_mask(A, span) & np.isfinite(mkt)
        days = np.unique(day[em])
        res["eras"][key] = {"name": name, "days": int(len(days)),
                            "first": dt.date.fromordinal(int(days[0])).isoformat() if len(days) else None,
                            "last": dt.date.fromordinal(int(days[-1])).isoformat() if len(days) else None}
    for g, gname in SS.GROUPS:
        by_era, read = {}, {}
        for key, ename, span in ERAS:
            m = AU.era_mask(A, span) & sel[g] & np.isfinite(mkt)
            q = BR.net_mean(A, adj, m, alpha=ALPHA)
            q.update(raw=BR._plain(raw, m), adj=BR._plain(adj, m), mkt=BR._plain(mkt, m))
            bands = {}
            udays = np.unique(day[m])
            for lab, lo, hi in DAY_BANDS:
                mb = m & (mkt >= lo) & (mkt < hi)
                bands[lab] = {"share_days": float(len(np.unique(day[mb])) / len(udays)) if len(udays) else None,
                              "raw": BR._plain(raw, mb), "adj": BR._plain(adj, mb), "mkt": BR._plain(mkt, mb)}
            ys = sorted(set(years[m].tolist()))
            per_year = {int(y): BR._plain(adj, m & (years == y)) for y in ys}
            pos = [v["mean"] > 0 for v in per_year.values() if v["mean"] is not None]
            read[key] = {"bands": bands, "years": per_year, "plus_years": (sum(pos), len(pos)),
                         "weekdays": {WEEKDAYS[w]: BR._plain(adj, m & (wday == w)) for w in range(5)}}
            by_era[key] = q
        res["groups"][g] = {"name": gname, "eras": by_era, "read": read, "summary": summary_of(by_era)}
    return res


# ════════════════════ 読む ════════════════════

def check_summary(A, missing, n_codes, store):
    """点検だけ＝行数と組ごとの件数・相場全体が数えられた朝の数（損益は数えない）"""
    B, idio = PG.idio_gap(A)
    mkt = market(B)
    sel = SS.groups(B, idio)
    out = {"n_codes": n_codes, "missing": {k: len(v) for k, v in missing.items()}, "rows": int(len(A)), "store": store, "eras": {}}
    for key, name, span in ERAS:
        em = AU.era_mask(B, span)
        ok = em & np.isfinite(mkt)
        out["eras"][key] = {"days": int(len(np.unique(B[em, C["day"]]))), "days_with_market": int(len(np.unique(B[ok, C["day"]]))),
                            "groups": {g: int((ok & sel[g]).sum()) for g, _ in SS.GROUPS}}
    return out


# ════════════════════ 書く ════════════════════

def _p(x, d=2):
    return Y._pct(x, d) if x is not None else "—"


def _band(q):
    return "—" if q.get("lo") is None else f"{_p(q['lo'])}〜{_p(q['hi'])}"


def _cell(c):
    return "—" if c.get("mean") is None else f"{_p(c['mean'])}（{c['n']:,}）"


def render_md(res):
    L = ["# J34 J31 の売りの取り分は、相場全体の下げの分か、目印の株ならではか", "",
         f"更新: {res.get('generated_at', '')}（事前登録＝`PILLAR_PREREG.md`「J34」・指紋 `{(res.get('prereg_sha256') or '')[:12]}`）", ""]
    r = res.get("result") or {}
    if "error" in r:
        return "\n".join(L + [f"⚠️ 計算できず：{r['error']}", "", "※ 研究の記録です。投資助言ではありません。"]) + "\n"
    L += ["**目隠しではない**（同じ取引を J31 で数えた）。前の日の売買代金10億円以上の目印 B・C の株を寄り成行で売り引け成行で買い戻したときの、"
          "1回あたりの損益率（プラス＝売りが勝った・費用 0.03％ 込み）。**相場全体**＝その朝の前の日の売買代金10億円以上の全銘柄の寄り→大引けの平均。"
          "**差し引いたあと**＝その株と相場全体の差の分だけの売り。幅は 97.5％（日と銘柄で引き直した広いほう）。", ""]
    for key, e in r["eras"].items():
        L.append(f"- {e['name']}：{e['first']}〜{e['last']}・{e['days']:,}営業日（相場全体を数えられた朝）")
    L += ["", "## まとめ", "", "| 組 | まとめ |", "|---|---|"]
    for g, x in r["groups"].items():
        L.append(f"| {g} {x['name']} | **{x['summary']}** |")
    for g, x in r["groups"].items():
        L += ["", f"## {g} {x['name']}", "",
              "| 時代 | 件数 | 差し引く前 | 相場全体の寄り→大引け（同じ日の平均） | 差し引いたあと | 97.5％の幅 | 前半／後半 | プラスの年 |", "|---|---:|---:|---:|---:|---|---|---|"]
        for key, q in x["eras"].items():
            py = x["read"][key]["plus_years"]
            L.append(f"| {r['eras'][key]['name']} | {q['n']:,} | {_p(q['raw']['mean'])} | {_p(q['mkt']['mean'])} | {_p(q['value'])} | {_band(q)} | {_p(q.get('early'))}／{_p(q.get('late'))} | {py[0]}／{py[1]}年 |")
        L += ["", "読むための表：相場全体の動きで日を分ける（売りの損益・費用後）", "",
              "| 時代 | 日の分け方 | 日の割合 | 相場全体の寄り→大引け | 差し引く前 | 差し引いたあと |", "|---|---|---:|---:|---:|---:|"]
        for key in x["eras"]:
            for lab, b in x["read"][key]["bands"].items():
                share = "—" if b["share_days"] is None else f"{b['share_days'] * 100:.0f}％"
                L.append(f"| {r['eras'][key]['name']} | {lab} | {share} | {_p(b['mkt']['mean'])} | {_cell(b['raw'])} | {_cell(b['adj'])} |")
        L += ["", "読むための表：年ごと・曜日ごと（差し引いたあと）", ""]
        for key in x["eras"]:
            rd = x["read"][key]
            L.append(f"- {r['eras'][key]['name']}：" + "／".join(f"{y} {_p(v['mean'])}" for y, v in rd["years"].items()))
            L.append("  - 曜日：" + "／".join(f"{w} {_cell(v)}" for w, v in rd["weekdays"].items()))
    L += ["", "## 注意", "",
          "- 相場全体は大きい株の同じ重みの平均で、実際の株価指数（TOPIX・日経平均）とは少し違う",
          "- 売り禁・在庫切れ・気配と始値のずれ・ストップ高で買い戻せない日・いま上場している銘柄だけ（J31 と同じ限界）", "", "---", "",
          "※ 研究の記録です。投資助言ではありません。空売りは損失が限られない取引です。将来の成績を約束するものではありません。"]
    return "\n".join(L) + "\n"


def main(argv):
    res = {"generated_at": dt.datetime.now(P.JST).isoformat(timespec="minutes"), "prereg_file": P.PREREG,
           "prereg_sha256": P.prereg_sha256()}
    try:
        stocks, list_date = jp_bars.load_universe()
        codes = sorted(stocks)
        A, missing, drops = AU.load(codes, jp_bars.fetcher())
        store = jp_bars.info()
        res["price_store"] = store
        if "--check" in argv:
            print(json.dumps(check_summary(A, missing, len(codes), store), ensure_ascii=False, indent=1))
            return 0
        if not store or store.get("daily_range") != jp_bars.FULL_DAILY:
            raise RuntimeError("値段の置き場の日足が全期間版ではない（先に jp-bars-cache を回す）")
        if len(set(missing["daily"])) > T.MAX_MISSING * len(codes):
            raise RuntimeError("日足を取れなかった銘柄が5％超。偏った組で数えない（取り直す）")
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
