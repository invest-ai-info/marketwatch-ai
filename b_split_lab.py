# -*- coding: utf-8 -*-
"""J38 目印B の売りの取り分はどこにあるか：今朝の窓・前の日の上げ・前の日の売買代金で分ける（昔の2つの時代で選び、
最近の時代で確かめる）。2026-10-08 登録・オーナー「両方登録して進めてください」。PILLAR_PREREG.md「J38」。

組＝目印B（前の日 +5％以上・その銘柄だけ +1％以上高く寄った・前の日の売買代金10億円以上）のうち貸借銘柄。損益＝J31 と同じ
（寄り成行で売り引け成行で買い戻す・損切りなし・費用 0.03％）。区切り3つ × 箱3つ（境目は固定）。E1・E2 だけで箱を選び
（合わせた平均がいちばん高く、E1 でも E2 でもほかの箱より高い・各30件以上）、E3 で「選んだ箱 − ほかの箱」の幅を確かめる。
**目隠しではない**（目印B の全体は J31〜J36 で数えた）が、区切りごとの数字はまだ誰も見ていない。

⚠️ 決まりは PILLAR_PREREG.md「J38」と下の定数に固定。行は J31（auction_lab）、組は J32（stop_short_lab.groups）、平均の幅は
   J29（bounce_range_lab.net_mean）、差の幅は gap_lab.boot、貸借銘柄は J36（jp_taishaku・taishaku_lab.flags）をそのまま使う。
⚠️ 出力（b-split-lab.json / .md）は集計だけ・銘柄名とコードは出さない（SYNC禁忌）。

実行: python b_split_lab.py --check   （点検だけ＝箱ごとの件数と日数。損益は数えない・何も書き出さない）
      python b_split_lab.py           （本番。Actions の b-split-lab.yml から手動で・1回だけ）
"""
import datetime as dt
import json
import sys

import numpy as np

import auction_lab as AU
import bounce_range_lab as BR
import gap_lab as GL
import highs_trap_lab as T
import jp_bars
import jp_taishaku as JT
import pillar_lab as P
import prevgap_lab as PG
import stop_short_lab as SS
import taishaku_lab as TK
import yori_lab as Y

OUT_JSON, OUT_MD = "b-split-lab.json", "b-split-lab.md"
C = SS.C
ERAS = AU.ERAS
GROUP = "K2"
SPLITS = (("W", "今朝のその銘柄だけの窓", (0.01, 0.03, 0.06), ("+1〜3％", "+3〜6％", "+6％以上")),
          ("P", "前の日の上げ", (0.05, 0.10, 0.15), ("+5〜10％", "+10〜15％", "+15％以上")),
          ("T", "前の日の売買代金", (10.0, 30.0, 100.0), ("10〜30億円", "30〜100億円", "100億円以上")))
N_Q = len(SPLITS)
ALPHA = 0.05 / N_Q                 # 98.33％ の幅
MIN_N = T.MIN_N                    # 30
PICK = ("e1", "e2")                # 選ぶのは昔の2つの時代だけ
TEST = "e3"                        # 確かめるのは最近の時代
OK, PLUS_ONLY, NONE, NOT_PICKED = "✅ 最近の時代でもほかより良い", "△ 最近もプラスだが、ほかより良いとは言えない", "✕", "—（選ばれない）"


# ════════════════════ 箱 ════════════════════

def values(A, idio):
    """区切りごとの値（W＝その銘柄だけの窓・P＝前の日の上げ・T＝前の日の売買代金）"""
    return {"W": idio, "P": A[:, C["rprev"]], "T": A[:, C["turnover"]]}


def bin_of(x, edges):
    """→ 箱の番号（0・1・2）。いちばん下の境目より下や値が無ければ −1。下の端を含み上の端を含まない"""
    x = np.asarray(x, float)
    out = np.searchsorted(np.asarray(edges), x, side="right") - 1
    return np.where(np.isfinite(x), out, -1)


def _mean(v, m):
    x = v[m & np.isfinite(v)]
    return (float(x.mean()) if len(x) else None), int(len(x))


def choose(v, base, bins, era_masks):
    """E1・E2 だけで選ぶ → (選んだ箱の番号 か None, 選ぶときの数字)"""
    m12 = base & (era_masks[PICK[0]] | era_masks[PICK[1]])
    means = [_mean(v, m12 & (bins == k))[0] for k in range(3)]
    cands = [k for k in range(3) if means[k] is not None]
    info = {"means_e1e2": means, "checks": {}}
    if not cands:
        return None, info
    k = max(cands, key=lambda i: means[i])
    ok = True
    for e in PICK:
        mb, nb = _mean(v, base & era_masks[e] & (bins == k))
        mr, _ = _mean(v, base & era_masks[e] & (bins != k) & (bins >= 0))
        good = nb >= MIN_N and mb is not None and mr is not None and mb > mr
        info["checks"][e] = {"bin": mb, "rest": mr, "n": nb, "ok": bool(good)}
        ok &= good
    info["candidate"] = int(k)
    return (int(k) if ok else None), info


def diff_band(A, v, inside, rest, alpha=ALPHA):
    """「inside の平均 − rest の平均」の (点, 下, 上)。日と銘柄で引き直した広いほう"""
    grp = np.where(inside, 0, np.where(rest, 1, -1))
    stat = lambda mu: mu[0] - mu[1]  # noqa: E731
    pt, lo_d, hi_d = GL.boot(v, grp, 2, A[:, C["day"]], stat, alpha)
    _, lo_c, hi_c = GL.boot(v, grp, 2, A[:, C["code"]], stat, alpha)
    if None in (lo_d, lo_c, hi_d, hi_c):
        return {"value": pt, "lo": None, "hi": None}
    return {"value": pt, "lo": min(lo_d, lo_c), "hi": max(hi_d, hi_c), "by_day": [lo_d, hi_d], "by_stock": [lo_c, hi_c]}


def verdict(diff, own):
    if diff.get("lo") is not None and diff["lo"] > 0:
        return OK
    if own.get("lo") is not None and own["lo"] > 0:
        return PLUS_ONLY
    return NONE


def table(A, v, base, bins, era_masks):
    """読むための表：箱ごと・時代ごとの平均・件数・勝った割合・1朝あたりの件数"""
    out = {}
    for e in era_masks:
        days = len(np.unique(A[era_masks[e] & base, C["day"]])) or 1
        row = []
        for k in range(3):
            q = BR._plain(v, era_masks[e] & base & (bins == k))
            q["per_day"] = q["n"] / days
            row.append(q)
        out[e] = row
    return out


def analyze(A, is_tai):
    A, idio = PG.idio_gap(A)
    sel = SS.groups(A, idio)[GROUP]
    tai = is_tai(A)
    base, base_all = sel & tai, sel
    v = -A[:, C["rclose"]] - AU.SHORT_COST
    em = {key: AU.era_mask(A, span) for key, _, span in ERAS}
    vals = values(A, idio)
    res = {"eras": {}, "splits": {}}
    for key, name, span in ERAS:
        days = np.unique(A[em[key], C["day"]])
        res["eras"][key] = {"name": name, "days": int(len(days)),
                            "first": dt.date.fromordinal(int(days[0])).isoformat() if len(days) else None,
                            "last": dt.date.fromordinal(int(days[-1])).isoformat() if len(days) else None}
    for sk, sname, edges, labels in SPLITS:
        bins = bin_of(vals[sk], edges)
        pick, info = choose(v, base, bins, em)
        out = {"name": sname, "labels": labels, "pick": pick, "choose": info,
               "read": table(A, v, base, bins, em), "read_all": table(A, v, base_all, bins, em)}
        if pick is None:
            out["summary"] = NOT_PICKED
        else:
            inside = base & em[TEST] & (bins == pick)
            rest = base & em[TEST] & (bins != pick) & (bins >= 0)
            out["diff"] = diff_band(A, v, inside, rest)
            out["own"] = BR.net_mean(A, v, inside, alpha=ALPHA)
            out["summary"] = verdict(out["diff"], out["own"])
        res["splits"][sk] = out
    return res


def check_summary(A, is_tai, n_list, missing, n_codes, store):
    """点検だけ＝箱ごとの件数と日数（損益は数えない）"""
    B, idio = PG.idio_gap(A)
    base = SS.groups(B, idio)[GROUP] & is_tai(B)
    vals = values(B, idio)
    out = {"n_codes": n_codes, "n_list": n_list, "missing": {k: len(v) for k, v in missing.items()}, "rows": int(len(A)),
           "store": store, "eras": {}}
    for key, _, span in ERAS:
        m = AU.era_mask(B, span) & base
        e = {"B_taishaku": int(m.sum()), "days": int(len(np.unique(B[m, C["day"]])))}
        for sk, _, edges, labels in SPLITS:
            bins = bin_of(vals[sk], edges)
            e[sk] = {lab: int((m & (bins == k)).sum()) for k, lab in enumerate(labels)}
            e[sk]["outside"] = int((m & (bins < 0)).sum())
        out["eras"][key] = e
    return out


# ════════════════════ 書く ════════════════════

def _p(x, d=2):
    return Y._pct(x, d) if x is not None else "—"


def _band(q):
    return "—" if not q or q.get("lo") is None else f"{_p(q['lo'])}〜{_p(q['hi'])}"


def _cell(q):
    if q.get("mean") is None:
        return f"—（{q['n']:,}）"
    return f"{_p(q['mean'])}（{q['n']:,}・勝ち {q['win'] * 100:.0f}％・1朝 {q['per_day']:.1f}）"


def render_md(res):
    L = ["# J38 目印B の売りの取り分はどこにあるか：今朝の窓・前の日の上げ・前の日の売買代金で分ける", "",
         f"更新: {res.get('generated_at', '')}（事前登録＝`PILLAR_PREREG.md`「J38」・指紋 `{(res.get('prereg_sha256') or '')[:12]}`）", ""]
    r = res.get("result") or {}
    if "error" in r:
        return "\n".join(L + [f"⚠️ 計算できず：{r['error']}", "", "※ 研究の記録です。投資助言ではありません。"]) + "\n"
    L += ["**目隠しではない**（目印B の全体は J31〜J36 で数えた）。区切りと選び方は数える前に決めた。",
          "組＝目印B（前の日 +5％以上・その銘柄だけ +1％以上高く寄った・前の日の売買代金10億円以上）のうち**貸借銘柄**"
          f"（{r.get('list_note', '')}・いまの一覧を昔に当てている）。値＝寄り成行で売り引け成行で買い戻したときの1回あたりの損益率"
          "（プラス＝売りが勝った・費用 0.03％ 込み）。**E1・E2 だけで箱を選び、E3 で確かめる**（98.33％の幅・日と銘柄で引き直した広いほう）。", ""]
    for key, e in r["eras"].items():
        L.append(f"- {e['name']}：{e['first']}〜{e['last']}・{e['days']:,}営業日")
    L += ["", "## まとめ", "", "| 区切り | E1・E2 で選んだ箱 | E3：選んだ箱 − ほかの箱 | E3：選んだ箱だけ | まとめ |", "|---|---|---|---|---|"]
    for sk, x in r["splits"].items():
        if x["pick"] is None:
            cand = x["choose"].get("candidate")
            why = "候補 " + x["labels"][cand] + " が E1・E2 のどちらかでほかの箱を下回った／件数不足" if cand is not None else "数えられる箱が無い"
            L.append(f"| {sk} {x['name']} | 選ばれない（{why}） | — | — | **{x['summary']}** |")
        else:
            d, o = x["diff"], x["own"]
            L.append(f"| {sk} {x['name']} | {x['labels'][x['pick']]} | {_p(d.get('value'))}（{_band(d)}） | "
                     f"{_p(o.get('value'))}（{_band(o)}・{o.get('n', 0):,}件） | **{x['summary']}** |")
    for sk, x in r["splits"].items():
        L += ["", f"## {sk} {x['name']}", "", "選ぶときの数字（E1・E2）：" + "／".join(
            f"{lab} {_p(m)}" for lab, m in zip(x["labels"], x["choose"]["means_e1e2"]))]
        for e, c in x["choose"].get("checks", {}).items():
            L.append(f"- {r['eras'][e]['name']}：候補 {_p(c['bin'])}（{c['n']:,}件）／ほかの箱 {_p(c['rest'])} → {'○' if c['ok'] else '×'}")
        L += ["", "| 時代 | " + " | ".join(x["labels"]) + " |", "|---|" + "---:|" * 3]
        for e in x["read"]:
            L.append(f"| {r['eras'][e]['name']}（貸借銘柄） | " + " | ".join(_cell(q) for q in x["read"][e]) + " |")
        for e in x["read_all"]:
            L.append(f"| {r['eras'][e]['name']}（すべての株・読むだけ） | " + " | ".join(_cell(q) for q in x["read_all"][e]) + " |")
    L += ["", "## 注意", "",
          "- いまの貸借銘柄の一覧を昔に当てている（昔は貸借銘柄でなかった株・いまは外れた株がある）",
          "- 箱の境目は数える前に決めた丸い数字で、いちばん良い境目を探したものではない",
          "- 売り禁（申込停止）・逆日歩・注意喚起の日・気配と始値のずれ・ストップ高で買い戻せない日は入れていない（J31 と同じ限界）", "", "---", "",
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
