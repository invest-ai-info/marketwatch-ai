# -*- coding: utf-8 -*-
"""J32 J31 の売り（目印 B・C・前の日の売買代金10億円以上・寄り成行で売り引け成行で買い戻す）に損切りを置くと、成績と
落ち込みはどう変わるか。2026-10-08 登録・オーナー「続けてください」。PILLAR_PREREG.md「J32」。

損切り＝寄り値から +3％・+5％・+10％。その日の高値が届いたら、損切りの値からさらに 0.2％ 不利な値で買い戻す。届かなければ
大引け。利益確定は置かない。落ち込み（1日ごとの最大ドローダウン・いちばん悪い日・連続20営業日）は読むための表。
**目隠しではない**（同じ行を J31 で数えた）。

⚠️ 決まりは PILLAR_PREREG.md「J32」と下の定数に固定。行・目印・幅は J31（auction_lab）・J30（short_side_lab）・
   J29（bounce_range_lab）の関数をそのまま使う。
⚠️ 出力（stop-short-lab.json / .md）は集計だけ・銘柄名とコードは出さない（SYNC禁忌）。既存の stop_lab.py（損切りラボ・
   exit-research）とは別物。

実行: python stop_short_lab.py --check   （点検だけ＝行数と組ごとの件数。損益は数えない・何も書き出さない）
      python stop_short_lab.py           （本番。Actions の stop-short-lab.yml から手動で・1回だけ）
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
import short_side_lab as K
import yori_lab as Y

OUT_JSON, OUT_MD = "stop-short-lab.json", "stop-short-lab.md"
C = AU.C
ERAS = AU.ERAS
GROUPS = (("K2", "目印B（前の日 +5％以上かつ、その銘柄だけ +1％以上高く寄った）"),
          ("K3", "目印C（前の日の売買代金が20営業日平均の5倍以上）"))
POP = 10.0                                 # 前の日の売買代金10億円以上（J31 の P2）
STOPS = (0.03, 0.05, 0.10)
SLIP = 0.002                               # 損切りの日の滑り
COST = AU.SHORT_COST                       # 0.03％
N_Q = len(GROUPS) * len(STOPS)
ALPHA = 0.05 / N_Q                         # 99.17％ の幅
TOP = 3                                    # 上位3銘柄（前の日の売買代金の大きい順）
RUN_DAYS = 20
OK_ALL, OK_OLD, NONE = "✅ 損切りを置いてもプラス", "△ 昔だけ（最近は届かない）", "✕ プラスと言えない"


# ════════════════════ 損益 ════════════════════

def net(A, stop):
    """売りの費用後の損益。stop=None は損切りなし（J31 と同じ）"""
    v = -A[:, C["rclose"]]
    if stop is not None:
        hit = A[:, C["rhigh"]] >= stop
        v = np.where(hit, -(stop + SLIP), v)
    return v - COST


def stop_hit(A, stop):
    return np.zeros(len(A), bool) if stop is None else A[:, C["rhigh"]] >= stop


def groups(A, idio):
    mk = K.marks(A, idio)
    big = A[:, C["turnover"]] >= POP
    return {g: mk[g] & big for g, _ in GROUPS}


def top_mask(A, sel, k=TOP):
    """その朝の sel の中で、前の日の売買代金が大きい順に k 銘柄"""
    out = np.zeros(len(A), bool)
    idx = np.where(sel)[0]
    if not len(idx):
        return out
    day, tv = A[idx, C["day"]], A[idx, C["turnover"]]
    order = np.lexsort((-tv, day))
    idx, day = idx[order], day[order]
    first = np.r_[True, day[1:] != day[:-1]]
    start = np.maximum.accumulate(np.where(first, np.arange(len(idx)), 0))
    rank = np.arange(len(idx)) - start
    out[idx[rank < k]] = True
    return out


def daily_path(A, v, m):
    """1日ごと（その朝の組の銘柄に同じ金額ずつ）の平均 → 落ち込みの数字"""
    ok = m & np.isfinite(v)
    if ok.sum() == 0:
        return {"days": 0}
    day = A[ok, C["day"]]
    uniq, inv, cnt = np.unique(day, return_inverse=True, return_counts=True)
    d = np.bincount(inv, weights=v[ok]) / cnt
    cum = np.cumsum(d)
    dd = float(np.max(np.maximum.accumulate(np.r_[0.0, cum])[1:] - cum)) if len(cum) else 0.0
    runs = np.convolve(d, np.ones(RUN_DAYS), "valid") if len(d) >= RUN_DAYS else np.array([d.sum()])
    return {"days": int(len(d)), "per_day": float(cnt.mean()), "mean": float(d.mean()), "sd": float(d.std()),
            "lose_days": float((d < 0).mean()), "worst_day": float(d.min()), "max_dd": dd, "worst_run": float(runs.min())}


def trade_stats(A, v, m, hit):
    ok = m & np.isfinite(v)
    if ok.sum() == 0:
        return {"n": 0}
    x = v[ok]
    return {"n": int(ok.sum()), "hit": float(hit[ok].mean()), "worst": float(x.min()), "le10": float((x <= -0.10).mean()),
            "mean": float(x.mean()), "win": float((x > 0).mean())}


def summary_of(by_era):
    plus = [q.get("lo") is not None and q["lo"] > 0 for q in (by_era["e1"], by_era["e2"], by_era["e3"])]
    if all(plus):
        return OK_ALL
    if plus[0] and plus[1]:
        return OK_OLD
    return NONE


def analyze(A):
    A, idio = PG.idio_gap(A)
    sel = groups(A, idio)
    res = {"eras": {}, "groups": {}}
    for key, name, span in ERAS:
        em = AU.era_mask(A, span)
        days = np.unique(A[em, C["day"]])
        res["eras"][key] = {"name": name, "days": int(len(days)), "rows": int(em.sum()),
                            "first": dt.date.fromordinal(int(days[0])).isoformat() if len(days) else None,
                            "last": dt.date.fromordinal(int(days[-1])).isoformat() if len(days) else None}
    for g, gname in GROUPS:
        top = top_mask(A, sel[g])
        rows = {}
        for stop in (None,) + STOPS:
            v, hit = net(A, stop), stop_hit(A, stop)
            by_era = {}
            for key, _, span in ERAS:
                m = AU.era_mask(A, span) & sel[g]
                q = BR.net_mean(A, v, m, alpha=ALPHA) if stop is not None else {"value": BR._plain(v, m)["mean"]}
                q.update(trades=trade_stats(A, v, m, hit), daily=daily_path(A, v, m),
                         top=dict(trade_stats(A, v, m & top, hit), daily=daily_path(A, v, m & top)))
                by_era[key] = q
            label = "none" if stop is None else f"{int(round(stop * 100))}"
            rows[label] = {"stop": stop, "eras": by_era, "summary": summary_of(by_era) if stop is not None else None}
        res["groups"][g] = {"name": gname, "stops": rows}
    return res


# ════════════════════ 読む ════════════════════

def check_summary(A, missing, n_codes, store):
    """点検だけ＝行数と組ごとの件数（損益は数えない）"""
    B, idio = PG.idio_gap(A)
    sel = groups(B, idio)
    out = {"n_codes": n_codes, "missing": {k: len(v) for k, v in missing.items()}, "rows": int(len(A)), "store": store, "eras": {}}
    for key, name, span in ERAS:
        em = AU.era_mask(B, span) & np.isfinite(B[:, C["rhigh"]])
        out["eras"][key] = {"days": int(len(np.unique(B[em, C["day"]]))), "rows": int(em.sum()),
                            "groups": {g: int((em & sel[g]).sum()) for g, _ in GROUPS}}
    return out


# ════════════════════ 書く ════════════════════

def _p(x, d=2):
    return Y._pct(x, d) if x is not None else "—"


def _band(q):
    return "—" if q.get("lo") is None else f"{_p(q['lo'])}〜{_p(q['hi'])}"


def _stop_name(label):
    return "損切りなし（J31）" if label == "none" else f"損切り +{label}％"


def render_md(res):
    L = ["# J32 J31 の売り（目印 B・C・板寄せどうし）に損切りを置くと", "",
         f"更新: {res.get('generated_at', '')}（事前登録＝`PILLAR_PREREG.md`「J32」・指紋 `{(res.get('prereg_sha256') or '')[:12]}`）", ""]
    r = res.get("result") or {}
    if "error" in r:
        return "\n".join(L + [f"⚠️ 計算できず：{r['error']}", "", "※ 研究の記録です。投資助言ではありません。"]) + "\n"
    L += ["**目隠しではない**（同じ行を J31 で数えた）。前の日の売買代金10億円以上の株を寄り成行で売り、損切り（寄り値から上へ）に届いたら"
          f"その値から {SLIP * 100:.1f}％ 不利な値で、届かなければ引け成行で買い戻したときの、1回あたりの損益率（プラス＝売りが勝った）。"
          f"費用 {COST * 100:.2f}％・幅は 99.17％（日と銘柄で引き直した広いほう）。", ""]
    for key, e in r["eras"].items():
        L.append(f"- {e['name']}：{e['first']}〜{e['last']}・{e['days']:,}営業日")
    L += ["", "## まとめ", "", "| 組 | 損切り | まとめ |", "|---|---|---|"]
    for g, x in r["groups"].items():
        for label, s in x["stops"].items():
            if s["summary"]:
                L.append(f"| {g} {x['name']} | +{label}％ | **{s['summary']}** |")
    for g, x in r["groups"].items():
        L += ["", f"## {g} {x['name']}", "",
              "| 損切り | 時代 | 件数 | 費用後 | 99.17％の幅 | 勝った割合 | 損切りに届いた割合 | いちばん大きい1回の損 | −10％以下の割合 |",
              "|---|---|---:|---:|---|---:|---:|---:|---:|"]
        for label, s in x["stops"].items():
            for key, q in s["eras"].items():
                t = q["trades"]
                if not t.get("n"):
                    continue
                L.append(f"| {_stop_name(label)} | {r['eras'][key]['name']} | {t['n']:,} | {_p(q.get('value'))} | {_band(q)} | "
                         f"{t['win'] * 100:.0f}％ | {t['hit'] * 100:.0f}％ | {_p(t['worst'])} | {t['le10'] * 100:.1f}％ |")
        L += ["", "読むための表：1日ごと（その朝の組の銘柄に同じ金額ずつ売ったとき・損益は1日の平均の％）", "",
              "| 損切り | 時代 | 日数 | 1日あたりの件数 | 1日の平均 | 1日のばらつき | 負けた日 | いちばん悪い日 | 最大の落ち込み（足し上げ） | いちばん悪い連続20日 |",
              "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for label, s in x["stops"].items():
            for key, q in s["eras"].items():
                d = q["daily"]
                if not d.get("days"):
                    continue
                L.append(f"| {_stop_name(label)} | {r['eras'][key]['name']} | {d['days']:,} | {d['per_day']:.1f} | {_p(d['mean'])} | {_p(d['sd'])} | "
                         f"{d['lose_days'] * 100:.0f}％ | {_p(d['worst_day'])} | {_p(d['max_dd'])} | {_p(d['worst_run'])} |")
        L += ["", f"読むための表：上位{TOP}銘柄だけ（その朝の組の中で前の日の売買代金が大きい順）", "",
              "| 損切り | 時代 | 件数 | 1回の平均 | 勝った割合 | 1日の平均 | 負けた日 | いちばん悪い日 | 最大の落ち込み |",
              "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
        for label, s in x["stops"].items():
            for key, q in s["eras"].items():
                t, d = q["top"], q["top"]["daily"]
                if not t.get("n"):
                    continue
                L.append(f"| {_stop_name(label)} | {r['eras'][key]['name']} | {t['n']:,} | {_p(t['mean'])} | {t['win'] * 100:.0f}％ | "
                         f"{_p(d['mean'])} | {d['lose_days'] * 100:.0f}％ | {_p(d['worst_day'])} | {_p(d['max_dd'])} |")
    L += ["", "## 注意", "",
          "- 日足では、損切りに届いたのが下げの前か後かはわからない（損切りだけなので数え方は変わらないが、寄りの直後の急な上げでは滑りが大きい日がある）",
          "- ストップ高に張り付くと損切りが約定しない日がある（数えでは損切りの値で買い戻せたことになる＝甘い向き）",
          "- 「最大の落ち込み」は1日の平均を足し上げたもの（毎日同じ金額を組に割り振ったとき・複利ではない）",
          "- 売り禁・在庫切れ・気配と始値のずれ・いま上場している銘柄だけ（J31 と同じ限界）", "", "---", "",
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
