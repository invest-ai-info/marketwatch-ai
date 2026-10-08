# -*- coding: utf-8 -*-
"""J37 貸借銘柄だけの目印B で、建玉の大きさと落ち込みを数え直す（J33 の現実版）。
2026-10-08 登録・オーナー「両方登録して進めてください」。PILLAR_PREREG.md「J37」。

形＝B0・B10（目印B・10億円以上・貸借銘柄だけ × 損切りなし／+10％）× すべて／上位3（その朝の貸借銘柄の B のうち前の日の
売買代金の大きい順）。大きさ・守りの決まり・時代・判定（収まる大きさ）は J33 と同じ。読むための表に同じ形のすべての株（J33 と
同じ数え方）を並べる。**目隠しではない**（同じ取引を J31〜J36 で数えた）。**決まりにはしない**。

⚠️ 決まりは PILLAR_PREREG.md「J37」と下の定数に固定。口座の動きは J33（size_short_lab）、損益と組は J32（stop_short_lab）、
   貸借銘柄の一覧と行ごとの印は J36（jp_taishaku・taishaku_lab.flags）の関数をそのまま使う。
⚠️ 出力（size-tai-lab.json / .md）は集計だけ・銘柄名とコードは出さない（SYNC禁忌）。

実行: python size_tai_lab.py --check   （点検だけ＝貸借銘柄の数と形ごとの件数・日数。損益は数えない・何も書き出さない）
      python size_tai_lab.py           （本番。Actions の size-tai-lab.yml から手動で・1回だけ）
"""
import datetime as dt
import json
import sys

import numpy as np

import auction_lab as AU
import highs_trap_lab as T
import jp_bars
import jp_taishaku as JT
import pillar_lab as P
import prevgap_lab as PG
import size_short_lab as SZ
import stop_short_lab as SS
import taishaku_lab as TK

OUT_JSON, OUT_MD = "size-tai-lab.json", "size-tai-lab.md"
C = SS.C
ERAS = AU.ERAS
GROUP = "K2"                                   # 目印B（J36 で ✅）。目印C は J36 で ✕ なので入れない
FORMS = (("B0", None), ("B10", SS.STOPS[2]))
SCOPES = SZ.SCOPES
SIZES = SZ.SIZES
POPS = (("tai", "貸借銘柄だけ"), ("all", "すべての株（J33 と同じ数え方）"))


# ════════════════════ 数える ════════════════════

def bases(A, idio, tai):
    """→ {"tai": 貸借銘柄の B, "all": B 全部}（行の印）"""
    b = SS.groups(A, idio)[GROUP]
    return {"tai": b & tai, "all": b}


def form_result(A, v, m_all):
    """1つの形（行の印 m_all・損益 v）を時代ごとに口座で動かす → (時代ごとの数字, 収まる大きさ)"""
    eras, ok_sizes = {}, []
    for key, _, span in ERAS:
        m = AU.era_mask(A, span) & m_all
        days, nets = SZ.by_day(A, v, m)
        ok = m & np.isfinite(v)
        worst = float(np.min(v[ok])) if ok.any() else None
        eras[key] = {"trades": int(ok.sum()), "days": len(days), "worst_trade": worst,
                     "sizes": {f"{s:.2f}": SZ.simulate(days, nets, s) for s in SIZES}}
    for s in SIZES:
        if all(SZ.fits(eras[k]["worst_trade"], eras[k]["sizes"][f"{s:.2f}"], s) for k, _, _ in ERAS):
            ok_sizes.append(s)
    return eras, (max(ok_sizes) if ok_sizes else None)


def analyze(A, is_tai):
    A, idio = PG.idio_gap(A)
    base = bases(A, idio, is_tai(A))
    res = {"eras": {}, "forms": {}}
    for key, name, span in ERAS:
        days = np.unique(A[AU.era_mask(A, span), C["day"]])
        res["eras"][key] = {"name": name, "days": int(len(days)),
                            "first": dt.date.fromordinal(int(days[0])).isoformat() if len(days) else None,
                            "last": dt.date.fromordinal(int(days[-1])).isoformat() if len(days) else None}
    for form, stop in FORMS:
        v = SS.net(A, stop)
        for scope, sname in SCOPES:
            out = {"form": form, "scope": sname}
            for pop, _ in POPS:
                m_all = base[pop] if scope == "all" else SS.top_mask(A, base[pop])
                eras, fit = form_result(A, v, m_all)
                out[pop] = {"eras": eras, "fit": fit}
            res["forms"][f"{form}-{scope}"] = out
    return res


def check_summary(A, is_tai, n_list, missing, n_codes, store):
    """点検だけ＝形ごとの件数と日数（損益は数えない）"""
    B, idio = PG.idio_gap(A)
    base = bases(B, idio, is_tai(B))
    out = {"n_codes": n_codes, "n_list": n_list, "missing": {k: len(v) for k, v in missing.items()}, "rows": int(len(A)),
           "store": store, "eras": {}}
    for key, _, span in ERAS:
        em = AU.era_mask(B, span) & np.isfinite(B[:, C["rhigh"]])
        e = {}
        for pop, _ in POPS:
            for scope, _ in SCOPES:
                m = em & (base[pop] if scope == "all" else SS.top_mask(B, base[pop]))
                e[f"{pop}-{scope}"] = {"rows": int(m.sum()), "days": int(len(np.unique(B[m, C["day"]])))}
        out["eras"][key] = e
    return out


# ════════════════════ 書く ════════════════════

def _p(x, d=1):
    return SZ._p(x, d)


def _fit(x):
    return f"口座の {x * 100:g}％" if x else "収まる大きさなし"


def render_md(res):
    L = ["# J37 貸借銘柄だけの目印B で、建玉の大きさと落ち込みを数え直す（J33 の現実版）", "",
         f"更新: {res.get('generated_at', '')}（事前登録＝`PILLAR_PREREG.md`「J37」・指紋 `{(res.get('prereg_sha256') or '')[:12]}`）", ""]
    r = res.get("result") or {}
    if "error" in r:
        return "\n".join(L + [f"⚠️ 計算できず：{r['error']}", "", "※ 研究の記録です。投資助言ではありません。"]) + "\n"
    L += ["**目隠しではない**（同じ取引を J31〜J36 で数えた）。**決まりにはしない**。",
          "取引＝目印B（前の日 +5％以上・その銘柄だけ +1％以上高く寄った・前の日の売買代金10億円以上）のうち**貸借銘柄**"
          f"（{r.get('list_note', '')}・いまの一覧を昔に当てている）を寄り成行で売り引け成行で買い戻す（費用 0.03％）。"
          "形＝損切りなし（B0）／+10％（B10）× すべて／上位3（前の日の売買代金の大きい順）。大きさ＝1銘柄あたりの口座の割合"
          "（毎日複利・その朝の合計が100％を超える日は100％に縮める）。守りの決まり＝1か月 −10％ でその月は建てない・"
          "最高残高から −20％ でその時代は止める。", ""]
    for key, e in r["eras"].items():
        L.append(f"- {e['name']}：{e['first']}〜{e['last']}・{e['days']:,}営業日")
    L += ["", "## まとめ：収まる大きさ（3つの時代すべてで、1回の最悪 × 大きさ ≤ 口座の1％ かつ −20％ に届かない）", "",
          "| 形 | 範囲 | **貸借銘柄だけ** | 参考：すべての株（J33） | 1回の最悪・貸借銘柄だけ（E1／E2／E3） |", "|---|---|---|---|---|"]
    for k, x in r["forms"].items():
        worst = "／".join(_p(x["tai"]["eras"][e]["worst_trade"]) for e, _, _ in ERAS)
        L.append(f"| {x['form']} | {x['scope']} | **{_fit(x['tai']['fit'])}** | {_fit(x['all']['fit'])} | {worst} |")
    L += ["", "## 貸借銘柄だけ と すべての株 の比べ（口座の3％・5％）", "",
          "| 形 | 範囲 | 大きさ | 時代 | 年あたりの増え方：貸借銘柄だけ／すべて | 最大の下落：貸借銘柄だけ／すべて | 1朝あたりの件数の目安：貸借銘柄だけ／すべて |",
          "|---|---|---|---|---|---|---|"]
    for k, x in r["forms"].items():
        for s in (0.03, 0.05):
            for e, _, _ in ERAS:
                a, b = x["tai"]["eras"][e], x["all"]["eras"][e]
                qa, qb = a["sizes"][f"{s:.2f}"], b["sizes"][f"{s:.2f}"]
                per = lambda q: "—" if not q["days"] else f"{q['trades'] / q['days']:.1f}"  # noqa: E731
                L.append(f"| {x['form']} | {x['scope']} | {s * 100:g}％ | {r['eras'][e]['name']} | {_p(qa['cagr'])}／{_p(qb['cagr'])} | "
                         f"{_p(qa['max_dd'])}／{_p(qb['max_dd'])} | {per(a)}／{per(b)} |")
    for k, x in r["forms"].items():
        L += ["", f"## {x['form']}（{x['scope']}）・貸借銘柄だけ", "",
              "| 大きさ | 時代 | 年あたりの増え方 | 最後の口座 | 最大の下落 | いちばん悪い日 | −3％以下の日 | いちばん悪い月 | −10％で止めた月 | −20％で止まった日 |",
              "|---|---|---:|---:|---:|---:|---:|---:|---:|---|"]
        for s in SIZES:
            for e, _, _ in ERAS:
                q = x["tai"]["eras"][e]["sizes"][f"{s:.2f}"]
                L.append(f"| {s * 100:g}％ | {r['eras'][e]['name']} | {_p(q['cagr'])} | {q['final']:.2f} | {_p(q['max_dd'])} | {_p(q['worst_day'])} | "
                         f"{'—' if q['day3'] is None else format(q['day3'] * 100, '.1f') + '％'} | {_p(q['worst_month'])} | {q['paused_months']} | {q['stopped_on'] or '—'} |")
    L += ["", "## 注意", "",
          "- いまの貸借銘柄の一覧を昔に当てている（昔は貸借銘柄でなかった株・いまは外れた株がある）",
          "- 売り禁（申込停止）・逆日歩・注意喚起の日・信用取引の保証金・追加の保証金は入れていない。気配と始値のずれ・ストップ高で買い戻せない日・"
          "損切りの滑りは J31・J32 と同じ限界",
          "- 1日 −3％ は寄りで一度に建てる形なので途中では止められない＝届いた日の割合を数えるだけ", "", "---", "",
          "※ 研究の記録です。投資助言ではありません。空売りは損失が限られない取引です。将来の成績を約束するものではありません。"]
    return "\n".join(L) + "\n"


def main(argv):
    res = {"generated_at": dt.datetime.now(P.JST).isoformat(timespec="minutes"), "prereg_file": P.PREREG,
           "prereg_sha256": P.prereg_sha256()}
    try:
        code_list, asof, counts = JT.load()
        note = f"日本取引所グループの貸借銘柄の一覧（{asof or '日付不明'}・{len(code_list):,}銘柄）"
        print(note, flush=True)
        stocks, list_date = jp_bars.load_universe()
        codes = sorted(stocks)
        A, missing, drops = AU.load(codes, jp_bars.fetcher())
        store = jp_bars.info()
        res["price_store"] = store
        is_tai = lambda X: TK.flags(X, codes, code_list)  # noqa: E731
        if "--check" in argv:
            print(json.dumps(check_summary(A, is_tai, len(code_list), missing, len(codes), store), ensure_ascii=False, indent=1))
            return 0
        if not store or store.get("daily_range") != jp_bars.FULL_DAILY:
            raise RuntimeError("値段の置き場の日足が全期間版ではない（先に jp-bars-cache を回す）")
        if len(set(missing["daily"])) > T.MAX_MISSING * len(codes):
            raise RuntimeError("日足を取れなかった銘柄が5％超。偏った組で数えない（取り直す）")
        res["result"] = dict(analyze(A, is_tai), n_codes=len(codes), list_date=list_date, n_list=len(code_list), list_note=note,
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
