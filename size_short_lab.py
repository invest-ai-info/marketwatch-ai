# -*- coding: utf-8 -*-
"""J33 建玉の大きさ：J31・J32 の売りを口座の何％ずつ建てれば、点検表の守りの決まりに収まるか。
2026-10-08 登録・オーナー「1と2を登録して続けてください」。PILLAR_PREREG.md「J33」。

形＝B0・B10・C0・C10（目印 B／C × 損切りなし／+10％・10億円以上）× すべて／上位3。大きさ＝1銘柄あたり口座の 1・2・3・5・10％
（毎日複利・その朝の合計が100％を超える日は合計100％に縮める）。守りの決まり＝1か月 −10％ でその月は建てない・最高残高から
−20％ でその時代は止める。判定＝3つの時代すべてで「1回の最悪 × 大きさ ≤ 口座の1％」かつ「−20％ に届かない」いちばん大きい大きさ。
**目隠しではない**（同じ取引を J31・J32 で数えた）。**決まりにはしない**。

⚠️ 決まりは PILLAR_PREREG.md「J33」と下の定数に固定。取引と損益は J32（stop_short_lab）の関数をそのまま使う。
⚠️ 出力（size-short-lab.json / .md）は集計だけ・銘柄名とコードは出さない（SYNC禁忌）。

実行: python size_short_lab.py --check   （点検だけ＝組ごとの件数と日数。損益は数えない・何も書き出さない）
      python size_short_lab.py           （本番。Actions の size-short-lab.yml から手動で・1回だけ）
"""
import datetime as dt
import json
import sys

import numpy as np

import auction_lab as AU
import highs_trap_lab as T
import jp_bars
import pillar_lab as P
import prevgap_lab as PG
import stop_short_lab as SS
import yori_lab as Y

OUT_JSON, OUT_MD = "size-short-lab.json", "size-short-lab.md"
C = SS.C
ERAS = AU.ERAS
SIZES = (0.01, 0.02, 0.03, 0.05, 0.10)
FORMS = (("B0", "K2", None), ("B10", "K2", SS.STOPS[2]), ("C0", "K3", None), ("C10", "K3", SS.STOPS[2]))
SCOPES = (("all", "すべて"), ("top3", "上位3"))
ONE_TRADE = 0.01          # 1回の損失＝口座の1％まで
DAY_LIMIT = -0.03         # 1日 −3％（届いた日の割合を数えるだけ）
MONTH_LIMIT = -0.10       # 1か月 −10％ でその月の残りは建てない
STOP_DD = -0.20           # 最高残高から −20％ でその時代は止める
YEAR = 365.25


# ════════════════════ 口座の動き ════════════════════

def by_day(A, v, m):
    """→ (日付の序数の並び, 日ごとの1回の損益の配列のリスト)"""
    ok = m & np.isfinite(v)
    day = A[ok, C["day"]]
    vals = v[ok]
    order = np.argsort(day, kind="stable")
    day, vals = day[order], vals[order]
    uniq, start = np.unique(day, return_index=True)
    return [int(d) for d in uniq], np.split(vals, start[1:]) if len(vals) else []


def simulate(days, nets, size):
    """1日ごとに複利で口座を動かす（守りの決まりを当てる）→ 数字"""
    acct = peak = 1.0
    month, month_start, paused = None, 1.0, False
    paused_months, stopped_on = 0, None
    rets, mrets, max_dd = [], {}, 0.0
    for d, x in zip(days, nets):
        m = dt.date.fromordinal(d).strftime("%Y-%m")
        if m != month:
            if month is not None:
                mrets[month] = acct / month_start - 1
            month, month_start, paused = m, acct, False
        if paused:
            continue
        w = min(size, 1.0 / len(x))
        r = float(w * x.sum())
        acct *= 1 + r
        rets.append(r)
        peak = max(peak, acct)
        max_dd = min(max_dd, acct / peak - 1)
        if acct / peak - 1 <= STOP_DD:
            stopped_on = dt.date.fromordinal(d).isoformat()
            break
        if acct / month_start - 1 <= MONTH_LIMIT:
            paused, paused_months = True, paused_months + 1
    if month is not None:
        mrets[month] = acct / month_start - 1
    years = max((days[-1] - days[0]) / YEAR, 1 / YEAR) if days else None
    end = dt.date.fromisoformat(stopped_on).toordinal() if stopped_on else (days[-1] if days else None)
    span = max((end - days[0]) / YEAR, 1 / YEAR) if days else None
    return {"days": len(rets), "final": acct, "cagr": (acct ** (1 / span) - 1) if span and acct > 0 else None, "years": years,
            "max_dd": max_dd, "worst_day": min(rets) if rets else None, "day3": float(np.mean(np.array(rets) <= DAY_LIMIT)) if rets else None,
            "worst_month": min(mrets.values()) if mrets else None, "paused_months": paused_months, "stopped_on": stopped_on}


def fits(worst_trade, sim, size):
    """① 1回の最悪 × 大きさ ≤ 口座の1％ ② −20％ に届かない"""
    return worst_trade is not None and abs(min(worst_trade, 0.0)) * size <= ONE_TRADE + 1e-12 and sim["stopped_on"] is None


def analyze(A):
    A, idio = PG.idio_gap(A)
    sel = SS.groups(A, idio)
    res = {"eras": {}, "forms": {}}
    for key, name, span in ERAS:
        em = AU.era_mask(A, span)
        days = np.unique(A[em, C["day"]])
        res["eras"][key] = {"name": name, "days": int(len(days)),
                            "first": dt.date.fromordinal(int(days[0])).isoformat() if len(days) else None,
                            "last": dt.date.fromordinal(int(days[-1])).isoformat() if len(days) else None}
    for form, g, stop in FORMS:
        v = SS.net(A, stop)
        for scope, sname in SCOPES:
            m_all = sel[g] if scope == "all" else SS.top_mask(A, sel[g])
            eras, ok_sizes = {}, []
            for key, _, span in ERAS:
                m = AU.era_mask(A, span) & m_all
                days, nets = by_day(A, v, m)
                worst = float(np.min(v[m & np.isfinite(v)])) if (m & np.isfinite(v)).any() else None
                sims = {f"{s:.2f}": simulate(days, nets, s) for s in SIZES}
                eras[key] = {"trades": int((m & np.isfinite(v)).sum()), "days": len(days), "worst_trade": worst, "sizes": sims}
            for s in SIZES:
                if all(fits(eras[k]["worst_trade"], eras[k]["sizes"][f"{s:.2f}"], s) for k, _, _ in ERAS):
                    ok_sizes.append(s)
            res["forms"][f"{form}-{scope}"] = {"form": form, "scope": sname, "eras": eras,
                                               "fit": max(ok_sizes) if ok_sizes else None}
    return res


# ════════════════════ 読む ════════════════════

def check_summary(A, missing, n_codes, store):
    """点検だけ＝組ごとの件数と日数（損益は数えない）"""
    B, idio = PG.idio_gap(A)
    sel = SS.groups(B, idio)
    out = {"n_codes": n_codes, "missing": {k: len(v) for k, v in missing.items()}, "rows": int(len(A)), "store": store, "eras": {}}
    for key, name, span in ERAS:
        em = AU.era_mask(B, span) & np.isfinite(B[:, C["rhigh"]])
        out["eras"][key] = {g: {"rows": int((em & sel[g]).sum()), "days": int(len(np.unique(B[em & sel[g], C["day"]])))}
                            for g, _ in SS.GROUPS}
    return out


# ════════════════════ 書く ════════════════════

def _p(x, d=1):
    return Y._pct(x, d) if x is not None else "—"


def render_md(res):
    L = ["# J33 建玉の大きさ：J31・J32 の売りを口座の何％ずつ建てれば、守りの決まりに収まるか", "",
         f"更新: {res.get('generated_at', '')}（事前登録＝`PILLAR_PREREG.md`「J33」・指紋 `{(res.get('prereg_sha256') or '')[:12]}`）", ""]
    r = res.get("result") or {}
    if "error" in r:
        return "\n".join(L + [f"⚠️ 計算できず：{r['error']}", "", "※ 研究の記録です。投資助言ではありません。"]) + "\n"
    L += ["**目隠しではない**（同じ取引を J31・J32 で数えた）。**決まりにはしない**。",
          "形＝B0・B10・C0・C10（目印 B／C × 損切りなし／+10％・前の日の売買代金10億円以上・寄り成行で売り引け成行で買い戻す）× すべて／上位3。"
          "大きさ＝1銘柄あたりの口座の割合（毎日複利・その朝の合計が100％を超える日は100％に縮める）。"
          "守りの決まり＝1か月 −10％ でその月は建てない・最高残高から −20％ でその時代は止める。", ""]
    for key, e in r["eras"].items():
        L.append(f"- {e['name']}：{e['first']}〜{e['last']}・{e['days']:,}営業日")
    L += ["", "## まとめ：収まる大きさ（3つの時代すべてで、1回の最悪 × 大きさ ≤ 口座の1％ かつ −20％ に届かない）", "",
          "| 形 | 範囲 | 収まる大きさ | 1回の最悪（E1／E2／E3） |", "|---|---|---|---|"]
    for k, x in r["forms"].items():
        worst = "／".join(_p(x["eras"][e]["worst_trade"]) for e, _, _ in ERAS)
        L.append(f"| {x['form']} | {x['scope']} | **{'口座の ' + format(x['fit'] * 100, 'g') + '％' if x['fit'] else '収まる大きさなし'}** | {worst} |")
    for k, x in r["forms"].items():
        L += ["", f"## {x['form']}（{x['scope']}）", "",
              "| 大きさ | 時代 | 年あたりの増え方 | 最後の口座 | 最大の下落 | いちばん悪い日 | −3％以下の日 | いちばん悪い月 | −10％で止めた月 | −20％で止まった日 |",
              "|---|---|---:|---:|---:|---:|---:|---:|---:|---|"]
        for s in SIZES:
            for e, ename, _ in ERAS:
                q = x["eras"][e]["sizes"][f"{s:.2f}"]
                L.append(f"| {s * 100:g}％ | {r['eras'][e]['name']} | {_p(q['cagr'])} | {q['final']:.2f} | {_p(q['max_dd'])} | {_p(q['worst_day'])} | "
                         f"{'—' if q['day3'] is None else format(q['day3'] * 100, '.1f') + '％'} | {_p(q['worst_month'])} | {q['paused_months']} | {q['stopped_on'] or '—'} |")
    L += ["", "## 注意", "",
          "- 信用取引の保証金・追加の保証金は入れていない。売り禁・在庫切れ・気配と始値のずれ・ストップ高で買い戻せない日・損切りの滑りは J31・J32 と同じ限界",
          "- 1日 −3％ は寄りで一度に建てる形なので途中では止められない＝届いた日の割合を数えるだけ", "", "---", "",
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
