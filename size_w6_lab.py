# -*- coding: utf-8 -*-
"""J39 目印B・貸借銘柄・今朝のその銘柄だけの窓 +6％以上だけを売る形で、建玉の大きさと落ち込みを数える（J37 と同じ物差し）。
2026-10-08 登録・オーナー「両方登録して進めてください」。PILLAR_PREREG.md「J39」。

取引＝J38 の W の「+6％以上」の箱（目印B・前の日の売買代金10億円以上・貸借銘柄・その銘柄だけの窓 +6％以上）。形＝B0・B10
（損切りなし／+10％）× すべて／1朝1銘柄（その銘柄だけの窓がいちばん大きいもの）。大きさ・守りの決まり・時代・判定（収まる大きさ）
は J37（＝J33）と同じ。読むための表に J37 の「すべて」（目印B・貸借銘柄の全部）を並べる。
**目隠しではない**（この箱は J38 で3つの時代すべてを数えた）。**決まりにはしない**。

⚠️ 決まりは PILLAR_PREREG.md「J39」と下の定数に固定。口座の動きと収まる大きさは J37（size_tai_lab.form_result＝J33 の関数）、
   損益と組は J32（stop_short_lab）、貸借銘柄は J36（jp_taishaku・taishaku_lab.flags）の関数をそのまま使う。
⚠️ 出力（size-w6-lab.json / .md）は集計だけ・銘柄名とコードは出さない（SYNC禁忌）。

実行: python size_w6_lab.py --check   （点検だけ＝形ごとの件数と日数。損益は数えない・何も書き出さない）
      python size_w6_lab.py           （本番。Actions の size-w6-lab.yml から手動で・1回だけ）
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
import size_tai_lab as Z
import stop_short_lab as SS
import taishaku_lab as TK

OUT_JSON, OUT_MD = "size-w6-lab.json", "size-w6-lab.md"
C = SS.C
ERAS = AU.ERAS
W6 = 0.06                          # J38 の W の「+6％以上」の箱
FORMS = Z.FORMS                    # B0（損切りなし）・B10（+10％）
SCOPES = (("all", "すべて"), ("one", "1朝1銘柄（窓がいちばん大きいもの）"))
SIZES = Z.SIZES


# ════════════════════ 数える ════════════════════

def top1_by(A, sel, key):
    """その朝の sel の中で key がいちばん大きい1銘柄の印"""
    out = np.zeros(len(A), bool)
    idx = np.where(sel)[0]
    if not len(idx):
        return out
    day = A[idx, C["day"]]
    order = np.lexsort((-key[idx], day))
    idx, day = idx[order], day[order]
    first = np.r_[True, day[1:] != day[:-1]]
    out[idx[first]] = True
    return out


def masks(A, idio, tai):
    """→ (J37 の「すべて」＝目印B・貸借銘柄, この研究の取引＝そのうち窓 +6％以上)"""
    base = Z.bases(A, idio, tai)["tai"]
    return base, base & (idio >= W6)


def analyze(A, is_tai):
    A, idio = PG.idio_gap(A)
    base, w6 = masks(A, idio, is_tai(A))
    res = {"eras": {}, "forms": {}}
    for key, name, span in ERAS:
        days = np.unique(A[AU.era_mask(A, span), C["day"]])
        res["eras"][key] = {"name": name, "days": int(len(days)),
                            "first": dt.date.fromordinal(int(days[0])).isoformat() if len(days) else None,
                            "last": dt.date.fromordinal(int(days[-1])).isoformat() if len(days) else None}
    for form, stop in FORMS:
        v = SS.net(A, stop)
        hit = SS.stop_hit(A, stop)
        ref_eras, ref_fit = Z.form_result(A, v, base)
        for scope, sname in SCOPES:
            m_all = w6 if scope == "all" else top1_by(A, w6, idio)
            eras, fit = Z.form_result(A, v, m_all)
            trades = {key: SS.trade_stats(A, v, AU.era_mask(A, span) & m_all, hit) for key, _, span in ERAS}
            res["forms"][f"{form}-{scope}"] = {"form": form, "scope": sname, "eras": eras, "fit": fit, "trades": trades,
                                               "ref": {"eras": ref_eras, "fit": ref_fit}}
    return res


def check_summary(A, is_tai, n_list, missing, n_codes, store):
    """点検だけ＝形ごとの件数と日数（損益は数えない）"""
    B, idio = PG.idio_gap(A)
    base, w6 = masks(B, idio, is_tai(B))
    one = top1_by(B, w6, idio)
    out = {"n_codes": n_codes, "n_list": n_list, "missing": {k: len(v) for k, v in missing.items()}, "rows": int(len(A)),
           "store": store, "eras": {}}
    for key, _, span in ERAS:
        em = AU.era_mask(B, span) & np.isfinite(B[:, C["rhigh"]])
        out["eras"][key] = {name: {"rows": int((em & m).sum()), "days": int(len(np.unique(B[em & m, C["day"]])))}
                            for name, m in (("w6-all", w6), ("w6-one", one), ("j37-all", base))}
    return out


# ════════════════════ 書く ════════════════════

def _p(x, d=1):
    return Z._p(x, d)


def render_md(res):
    L = ["# J39 目印B・貸借銘柄・今朝のその銘柄だけの窓 +6％以上だけを売る形の、建玉の大きさと落ち込み", "",
         f"更新: {res.get('generated_at', '')}（事前登録＝`PILLAR_PREREG.md`「J39」・指紋 `{(res.get('prereg_sha256') or '')[:12]}`）", ""]
    r = res.get("result") or {}
    if "error" in r:
        return "\n".join(L + [f"⚠️ 計算できず：{r['error']}", "", "※ 研究の記録です。投資助言ではありません。"]) + "\n"
    L += ["**目隠しではない**（この箱は J38 で3つの時代すべてを数えた）。**決まりにはしない**。",
          "取引＝目印B（前の日 +5％以上・前の日の売買代金10億円以上）のうち**貸借銘柄**"
          f"（{r.get('list_note', '')}・いまの一覧を昔に当てている）で、**その銘柄だけの窓が +6％以上**の株を寄り成行で売り引け成行で買い戻す（費用 0.03％）。"
          "形＝損切りなし（B0）／+10％（B10）× すべて／1朝1銘柄（窓がいちばん大きいもの）。大きさ・守りの決まり・判定は J37（＝J33）と同じ。", ""]
    for key, e in r["eras"].items():
        L.append(f"- {e['name']}：{e['first']}〜{e['last']}・{e['days']:,}営業日")
    L += ["", "## まとめ：収まる大きさ（3つの時代すべてで、1回の最悪 × 大きさ ≤ 口座の1％ かつ −20％ に届かない）", "",
          "| 形 | 範囲 | **窓 +6％以上だけ** | 参考：J37（目印B・貸借銘柄の全部） | 1回の最悪（E1／E2／E3） | −20％で止まった時代 |", "|---|---|---|---|---|---|"]
    for k, x in r["forms"].items():
        worst = "／".join(_p(x["eras"][e]["worst_trade"]) for e, _, _ in ERAS)
        stops = [f"{s * 100:g}％：{r['eras'][e]['name'][:2]}" for s in SIZES for e, _, _ in ERAS if x["eras"][e]["sizes"][f"{s:.2f}"]["stopped_on"]]
        L.append(f"| {x['form']} | {x['scope']} | **{Z._fit(x['fit'])}** | {Z._fit(x['ref']['fit'])} | {worst} | {'・'.join(stops) or 'なし'} |")
    L += ["", "## 1回ごとの数字（読むだけ）", "",
          "| 形 | 範囲 | 時代 | 回数 | 1朝あたり | 1回の平均 | 勝った割合 | いちばん悪い1回 | −10％以下の回 | 損切りに届いた割合 |",
          "|---|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for k, x in r["forms"].items():
        for e, _, _ in ERAS:
            t, q = x["trades"][e], x["eras"][e]
            if not t.get("n"):
                L.append(f"| {x['form']} | {x['scope']} | {r['eras'][e]['name']} | 0 | — | — | — | — | — | — |")
                continue
            per = t["n"] / max(r["eras"][e]["days"], 1)
            hit = "—" if x["form"] == "B0" else f"{t['hit'] * 100:.0f}％"
            L.append(f"| {x['form']} | {x['scope']} | {r['eras'][e]['name']} | {t['n']:,} | {per:.2f} | {_p(t['mean'], 2)} | {t['win'] * 100:.0f}％ | "
                     f"{_p(t['worst'])} | {t['le10'] * 100:.1f}％ | {hit} |")
    L += ["", "## 窓 +6％以上だけ と J37（目印B・貸借銘柄の全部） の比べ", "",
          "| 形 | 範囲 | 大きさ | 時代 | 年あたりの増え方：窓 +6％以上／J37 | 最大の下落：窓 +6％以上／J37 | いちばん悪い月：窓 +6％以上／J37 |",
          "|---|---|---|---|---|---|---|"]
    for k, x in r["forms"].items():
        for s in (0.01, 0.02, 0.03, 0.05):
            for e, _, _ in ERAS:
                qa, qb = x["eras"][e]["sizes"][f"{s:.2f}"], x["ref"]["eras"][e]["sizes"][f"{s:.2f}"]
                L.append(f"| {x['form']} | {x['scope']} | {s * 100:g}％ | {r['eras'][e]['name']} | {_p(qa['cagr'])}／{_p(qb['cagr'])} | "
                         f"{_p(qa['max_dd'])}／{_p(qb['max_dd'])} | {_p(qa['worst_month'])}／{_p(qb['worst_month'])} |")
    for k, x in r["forms"].items():
        L += ["", f"## {x['form']}（{x['scope']}）", "",
              "| 大きさ | 時代 | 年あたりの増え方 | 最後の口座 | 最大の下落 | いちばん悪い日 | −3％以下の日 | いちばん悪い月 | −10％で止めた月 | −20％で止まった日 |",
              "|---|---|---:|---:|---:|---:|---:|---:|---:|---|"]
        for s in SIZES:
            for e, _, _ in ERAS:
                q = x["eras"][e]["sizes"][f"{s:.2f}"]
                L.append(f"| {s * 100:g}％ | {r['eras'][e]['name']} | {_p(q['cagr'])} | {q['final']:.2f} | {_p(q['max_dd'])} | {_p(q['worst_day'])} | "
                         f"{'—' if q['day3'] is None else format(q['day3'] * 100, '.1f') + '％'} | {_p(q['worst_month'])} | {q['paused_months']} | {q['stopped_on'] or '—'} |")
    L += ["", "## 注意", "",
          "- いまの貸借銘柄の一覧を昔に当てている（昔は貸借銘柄でなかった株・いまは外れた株がある）",
          "- 大きく高く寄った人気の株は、売り禁（申込停止）・増担保規制・注意喚起がかかりやすい（入れていない）。逆日歩・信用取引の保証金も入れていない",
          "- 気配と始値のずれ・ストップ高で買い戻せない日・損切りの滑りは J31・J32 と同じ限界", "", "---", "",
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
