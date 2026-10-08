# -*- coding: utf-8 -*-
"""J35 J31 の売りを、同じ金額の株価指数（1321.T）の買いで打ち消すと、成績・落ち込み・建玉の大きさはどう変わるか。
2026-10-08 登録・オーナー「両方登録して続けてください」。PILLAR_PREREG.md「J35」。

1組＝目印の株を寄り成行で売り引け成行で買い戻す（−その株の寄り→大引け − 0.03％）＋ 1321.T を同じ寄りに買い同じ大引けに売る
（1321.T の寄り→大引け − 0.03％）。組＝B0・C0（10億円以上・損切りなし）× すべて／上位3。時代＝E1′ 2011〜2016・E2・E3。
判定①＝B0・C0（すべて）の1組の損益の幅が3つの時代ともプラス／判定②＝J33 と同じ物差しの「収まる大きさ」。
**目隠しではない**（同じ取引を J31〜J34 で数えた）。

⚠️ 決まりは PILLAR_PREREG.md「J35」と下の定数に固定。行・組は J31（auction_lab）・J32（stop_short_lab）、口座の動きは J33
   （size_short_lab）、幅は J29（bounce_range_lab）の関数をそのまま使う。1321.T の扱いは R7（index_open_lab）と同じ。
⚠️ 出力（hedge-short-lab.json / .md）は集計だけ・銘柄名とコードは出さない（SYNC禁忌）。

実行: python hedge_short_lab.py --check   （点検だけ＝行数・組ごとの件数・1321.T の行の数。損益は数えない・何も書き出さない）
      python hedge_short_lab.py           （本番。Actions の hedge-short-lab.yml から手動で・1回だけ）
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
import prevday_lab as PD
import prevgap_lab as PG
import size_short_lab as Z
import stop_short_lab as SS
import yori_lab as Y

OUT_JSON, OUT_MD = "hedge-short-lab.json", "hedge-short-lab.md"
C = AU.C
HEDGE, HEDGE_START = "1321.T", "2011-01-01"
HEDGE_COST = 0.0003
SHORT_COST = AU.SHORT_COST
MAX_MOVE = 0.25
ERAS = (("e1", "E1′ 2011〜2016年", ("2011-01-04", "2016-10-31")),
        ("e2", "E2 2016〜2023年", PD.OLD),
        ("e3", "E3 2023〜2026年", PD.NEW))
FORMS = (("B0", "K2"), ("C0", "K3"))
SCOPES = Z.SCOPES
SIZES = Z.SIZES
N_Q = 2
ALPHA = 0.05 / N_Q            # 97.5％ の幅
DAY_BANDS = (("1321.T が上げた日（+0.5％以上）", 0.005, 9.0), ("ふつうの日（±0.5％未満）", -0.005, 0.005), ("下げた日（−0.5％以下）", -9.0, -0.005))
OK_ALL, OK_OLD, NONE = "✅ 打ち消してもプラス", "△ 昔だけ（最近は届かない）", "✕ プラスと言えない"


# ════════════════════ 打ち消しの値段 ════════════════════

def hedge_returns(df):
    """1321.T の日足（Open・High・Low・Close）→ {日付の序数: 寄り→大引け}。2011年より前・値の付いていない日・±25％超は入れない"""
    out = {}
    if df is None or not len(df):
        return out
    o, c = df["Open"].to_numpy(float), df["Close"].to_numpy(float)
    h = df["High"].to_numpy(float) if "High" in df else None
    lo = df["Low"].to_numpy(float) if "Low" in df else None
    start = dt.date.fromisoformat(HEDGE_START)
    for i, ts in enumerate(df.index):
        d = ts.date() if hasattr(ts, "date") else ts
        if d < start or not (o[i] > 0 and c[i] > 0):
            continue
        stale = o[i] == c[i] and (h is None or (h[i] == lo[i] == o[i]))
        r = c[i] / o[i] - 1
        if stale or abs(r) > MAX_MOVE:
            continue
        out[d.toordinal()] = float(r)
    return out


def pair_nets(A, hedge):
    """→ (売りだけ, 1組, 1321.T の寄り→大引け)。1321.T の無い日は NaN"""
    h = np.array([hedge.get(int(d), np.nan) for d in A[:, C["day"]]], float)
    short = -A[:, C["rclose"]] - SHORT_COST
    return short, short + h - HEDGE_COST, h


def summary_of(by_era):
    plus = [q.get("lo") is not None and q["lo"] > 0 for q in (by_era["e1"], by_era["e2"], by_era["e3"])]
    if all(plus):
        return OK_ALL
    if plus[0] and plus[1]:
        return OK_OLD
    return NONE


def _corr(A, short, h, m):
    ok = m & np.isfinite(short) & np.isfinite(h)
    if ok.sum() < 30:
        return None
    day = A[ok, C["day"]]
    uniq, inv, cnt = np.unique(day, return_inverse=True, return_counts=True)
    s = np.bincount(inv, weights=short[ok]) / cnt
    hh = np.bincount(inv, weights=h[ok]) / cnt
    if len(uniq) < 30 or s.std() == 0 or hh.std() == 0:
        return None
    return float(np.corrcoef(s, hh)[0, 1])


def analyze(A, hedge):
    A, idio = PG.idio_gap(A)
    sel = SS.groups(A, idio)
    short, pair, h = pair_nets(A, hedge)
    res = {"eras": {}, "judge": {}, "forms": {}}
    for key, name, span in ERAS:
        em = AU.era_mask(A, span) & np.isfinite(h)
        days = np.unique(A[em, C["day"]])
        res["eras"][key] = {"name": name, "days": int(len(days)),
                            "first": dt.date.fromordinal(int(days[0])).isoformat() if len(days) else None,
                            "last": dt.date.fromordinal(int(days[-1])).isoformat() if len(days) else None}
    for form, g in FORMS:
        by_era = {}
        for key, _, span in ERAS:
            m = AU.era_mask(A, span) & sel[g] & np.isfinite(h)
            q = BR.net_mean(A, pair, m, alpha=ALPHA)
            q.update(short=BR._plain(short, m), hedge=BR._plain(h, m), corr=_corr(A, short, h, m),
                     bands={lab: {"pair": BR._plain(pair, m & (h >= lo) & (h < hi)), "short": BR._plain(short, m & (h >= lo) & (h < hi))}
                            for lab, lo, hi in DAY_BANDS})
            by_era[key] = q
        res["judge"][form] = {"eras": by_era, "summary": summary_of(by_era)}
        for scope, sname in SCOPES:
            m_all = sel[g] if scope == "all" else SS.top_mask(A, sel[g])
            eras, ok_sizes = {}, []
            for key, _, span in ERAS:
                m = AU.era_mask(A, span) & m_all & np.isfinite(h)
                dp, np_ = Z.by_day(A, pair, m)
                ds, ns = Z.by_day(A, short, m)
                worst = float(np.min(pair[m])) if m.any() else None
                eras[key] = {"trades": int(m.sum()), "days": len(dp), "worst_pair": worst,
                             "worst_short": float(np.min(short[m])) if m.any() else None,
                             "daily_pair": SS.daily_path(A, pair, m), "daily_short": SS.daily_path(A, short, m),
                             "sizes": {f"{s:.2f}": {"pair": Z.simulate(dp, np_, s), "short": Z.simulate(ds, ns, s)} for s in SIZES}}
            for s in SIZES:
                if all(Z.fits(eras[k]["worst_pair"], eras[k]["sizes"][f"{s:.2f}"]["pair"], s) for k, _, _ in ERAS):
                    ok_sizes.append(s)
            res["forms"][f"{form}-{scope}"] = {"form": form, "scope": sname, "eras": eras, "fit": max(ok_sizes) if ok_sizes else None}
    return res


# ════════════════════ 読む ════════════════════

def check_summary(A, hedge, missing, n_codes, store):
    """点検だけ＝行数・組ごとの件数・1321.T の日数（損益は数えない）"""
    B, idio = PG.idio_gap(A)
    sel = SS.groups(B, idio)
    _, _, h = pair_nets(B, hedge)
    out = {"n_codes": n_codes, "missing": {k: len(v) for k, v in missing.items()}, "rows": int(len(A)), "store": store,
           "hedge_days": len(hedge), "hedge_first": dt.date.fromordinal(min(hedge)).isoformat() if hedge else None, "eras": {}}
    for key, name, span in ERAS:
        em = AU.era_mask(B, span)
        ok = em & np.isfinite(h)
        out["eras"][key] = {"days": int(len(np.unique(B[em, C["day"]]))), "days_with_hedge": int(len(np.unique(B[ok, C["day"]]))),
                            "groups": {g: int((ok & sel[g]).sum()) for _, g in FORMS}}
    return out


# ════════════════════ 書く ════════════════════

def _p(x, d=2):
    return Y._pct(x, d) if x is not None else "—"


def _band(q):
    return "—" if q.get("lo") is None else f"{_p(q['lo'])}〜{_p(q['hi'])}"


def _cell(c):
    return "—" if c.get("mean") is None else f"{_p(c['mean'])}（{c['n']:,}）"


def render_md(res):
    L = ["# J35 J31 の売りを、同じ金額の株価指数（1321.T）の買いで打ち消すと", "",
         f"更新: {res.get('generated_at', '')}（事前登録＝`PILLAR_PREREG.md`「J35」・指紋 `{(res.get('prereg_sha256') or '')[:12]}`）", ""]
    r = res.get("result") or {}
    if "error" in r:
        return "\n".join(L + [f"⚠️ 計算できず：{r['error']}", "", "※ 研究の記録です。投資助言ではありません。"]) + "\n"
    L += ["**目隠しではない**（同じ取引を J31〜J34 で数えた）。1組＝目印の株を寄り成行で売り引け成行で買い戻す（費用 0.03％）＋ "
          "同じ金額の 1321.T（日経225連動型上場投信）を同じ寄りに買い同じ大引けに売る（費用 0.03％）。幅は 97.5％（日と銘柄で引き直した広いほう）。", ""]
    for key, e in r["eras"].items():
        L.append(f"- {e['name']}：{e['first']}〜{e['last']}・{e['days']:,}営業日（1321.T のある日）")
    L += ["", "## 判定①：打ち消してもプラスか（すべて）", "", "| 組 | まとめ |", "|---|---|"]
    for form, j in r["judge"].items():
        L.append(f"| {form} | **{j['summary']}** |")
    L += ["", "| 組 | 時代 | 件数 | 売りだけ | 1321.T の寄り→大引け（同じ日） | 1組 | 97.5％の幅 | 前半／後半 | 1日の売りと 1321.T の相関 |",
          "|---|---|---:|---:|---:|---:|---|---|---:|"]
    for form, j in r["judge"].items():
        for key, q in j["eras"].items():
            corr = "—" if q["corr"] is None else f"{q['corr']:.2f}"
            L.append(f"| {form} | {r['eras'][key]['name']} | {q['n']:,} | {_p(q['short']['mean'])} | {_p(q['hedge']['mean'])} | {_p(q['value'])} | "
                     f"{_band(q)} | {_p(q.get('early'))}／{_p(q.get('late'))} | {corr} |")
    L += ["", "読むための表：1321.T の動きで日を分ける（1組／売りだけ）", ""]
    for form, j in r["judge"].items():
        for key, q in j["eras"].items():
            L.append(f"- {form} {r['eras'][key]['name']}：" + "／".join(f"{lab} 1組 {_cell(b['pair'])}・売りだけ {_cell(b['short'])}" for lab, b in q["bands"].items()))
    L += ["", "## 判定②：収まる大きさ（3つの時代すべてで、1組の最悪 × 大きさ ≤ 口座の1％ かつ −20％ に届かない）", "",
          "| 形 | 範囲 | 収まる大きさ | 1組の最悪（E1′／E2／E3） | 売りだけの最悪 |", "|---|---|---|---|---|"]
    for k, x in r["forms"].items():
        wp = "／".join(_p(x["eras"][e]["worst_pair"], 1) for e, _, _ in ERAS)
        ws = "／".join(_p(x["eras"][e]["worst_short"], 1) for e, _, _ in ERAS)
        L.append(f"| {x['form']} | {x['scope']} | **{'口座の ' + format(x['fit'] * 100, 'g') + '％' if x['fit'] else '収まる大きさなし'}** | {wp} | {ws} |")
    L += ["", "読むための表：1日ごと（同じ金額ずつ）の荒さ＝打ち消した形／売りだけ", "",
          "| 形 | 範囲 | 時代 | 1日の平均 | 1日のばらつき | 負けた日 | いちばん悪い日 |", "|---|---|---|---|---|---|---|"]
    for k, x in r["forms"].items():
        for e, ename, _ in ERAS:
            dp, ds = x["eras"][e]["daily_pair"], x["eras"][e]["daily_short"]
            if not dp.get("days"):
                continue
            L.append(f"| {x['form']} | {x['scope']} | {r['eras'][e]['name']} | {_p(dp['mean'])}／{_p(ds['mean'])} | {_p(dp['sd'])}／{_p(ds['sd'])} | "
                     f"{dp['lose_days'] * 100:.0f}％／{ds['lose_days'] * 100:.0f}％ | {_p(dp['worst_day'])}／{_p(ds['worst_day'])} |")
    L += ["", "読むための表：口座の動き（大きさごと・打ち消した形／売りだけ・毎日複利・守りの決まりを当てる）", "",
          "| 形 | 範囲 | 大きさ | 時代 | 年あたりの増え方 | 最大の下落 | いちばん悪い日 | いちばん悪い月 | −20％で止まった日 |", "|---|---|---|---|---|---|---|---|---|"]
    for k, x in r["forms"].items():
        for s in SIZES:
            for e, ename, _ in ERAS:
                q = x["eras"][e]["sizes"][f"{s:.2f}"]
                a, b = q["pair"], q["short"]
                L.append(f"| {x['form']} | {x['scope']} | {s * 100:g}％ | {r['eras'][e]['name']} | {_p(a['cagr'], 1)}／{_p(b['cagr'], 1)} | "
                         f"{_p(a['max_dd'], 1)}／{_p(b['max_dd'], 1)} | {_p(a['worst_day'], 1)}／{_p(b['worst_day'], 1)} | "
                         f"{_p(a['worst_month'], 1)}／{_p(b['worst_month'], 1)} | {a['stopped_on'] or '—'}／{b['stopped_on'] or '—'} |")
    L += ["", "## 注意", "",
          "- 1321.T の寄り・引けは CFD や先物の値段と少しずれる。信用取引の保証金・手数料の違いは入れていない",
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
        hedge = hedge_returns(P.fetch(HEDGE, "1d", start="2007-01-01"))
        store = jp_bars.info()
        res["price_store"] = store
        if "--check" in argv:
            print(json.dumps(check_summary(A, hedge, missing, len(codes), store), ensure_ascii=False, indent=1))
            return 0
        if not store or store.get("daily_range") != jp_bars.FULL_DAILY:
            raise RuntimeError("値段の置き場の日足が全期間版ではない（先に jp-bars-cache を回す）")
        if len(set(missing["daily"])) > T.MAX_MISSING * len(codes):
            raise RuntimeError("日足を取れなかった銘柄が5％超。偏った組で数えない（取り直す）")
        if len(hedge) < 1000:
            raise RuntimeError(f"1321.T の日足が {len(hedge)} 日しかない（取り直す）")
        res["result"] = dict(analyze(A, hedge), n_codes=len(codes), list_date=list_date, hedge_days=len(hedge),
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
