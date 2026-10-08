# -*- coding: utf-8 -*-
"""J31 板寄せどうし（寄り成行で入り、引け成行で出る）なら費用はほぼかからない＝目印の付いた株の売りと、安く寄った株の
買いを、3つの時代とも寄り→大引けで数え直す。2026-10-08 登録・オーナー「続けてください」。PILLAR_PREREG.md「J31」。

J19・J29・J30 は、寄り→大引け（板寄せどうし）にも売り値と買い値の差の往復分を引いていた＝板寄せの注文には重すぎた。
最近の時代（E3）も日足の寄り→大引けで数える。**目隠しではない＝判定ではなく数え直し**。

⚠️ 決まりは PILLAR_PREREG.md「J31」と下の定数に固定。行は J30（short_side_lab.stock_rows）に、その日の高値・安値の
   始値からの幅（読むための表だけ）を足したもの。組・幅は J29（bounce_range_lab）と J30 の関数をそのまま使う。
⚠️ 出力（auction-lab.json / .md）は集計だけ・銘柄名とコードは出さない（SYNC禁忌）。

実行: python auction_lab.py --check   （点検だけ＝行数と組ごとの件数。損益は数えない・何も書き出さない）
      python auction_lab.py           （本番。Actions の auction-lab.yml から手動で・1回だけ）
"""
import datetime as dt
import json
import sys

import numpy as np

import bounce_range_lab as BR
import cost_recount_lab as CR
import highs_trap_lab as T
import highs_trap_small as S
import jp_bars
import pillar_lab as P
import prevday_lab as PD
import prevgap_lab as PG
import short_side_lab as K
import yori_lab as Y

OUT_JSON, OUT_MD = "auction-lab.json", "auction-lab.md"
COLS = K.COLS + ("rhigh", "rlow")
C = {k: i for i, k in enumerate(COLS)}
ERAS = (("e1", "E1 2006〜2016年", ("2006-01-04", "2016-10-31")),
        ("e2", "E2 2016〜2023年", PD.OLD),
        ("e3", "E3 2023〜2026年", PD.NEW))
LONG_COST = 0.0002                     # 往復 0.02％（板寄せどうしの余裕）
SHORT_COST = 0.0002 + K.BORROW         # ＋貸株料など 0.01％
STRICT_COST = 0.001                    # 読むための表：厳しめの往復 0.1％
LONGS = (("L1", "その銘柄だけ −1％以下で寄った株を買う", "D1"),
         ("L2", "窓 −1％以下で寄った株を買う", "D2"),
         ("L3", "窓 −3％以下で寄った株を買う", "D3"))
SHORTS = K.MARKS
N_Q = len(LONGS) + len(SHORTS) * len(K.POPS)
ALPHA = 0.05 / N_Q                     # 99.44％ の幅
OK_ALL, OK_OLD, NONE = "✅ 板寄せどうしならプラス", "△ 昔だけ（最近は届かない）", "✕ プラスと言えない"


# ════════════════════ 行 ════════════════════

def stock_rows(ci, daily, m5, h1, sp, drops=None):
    """J30 の行＋その日の（高値÷始値−1・安値÷始値−1）＝読むための表だけ"""
    A = K.stock_rows(ci, daily, m5, h1, sp, drops=drops)
    if not len(A):
        return np.zeros((0, len(COLS)))
    pos = {dt.date.fromisoformat(r[0]).toordinal(): i for i, r in enumerate(daily)}
    k = np.array([pos[int(o)] for o in A[:, C["day"]]])
    o = np.array([daily[j][1] for j in k], float)
    hi = np.array([daily[j][2] for j in k], float) / o - 1
    lo = np.array([daily[j][3] for j in k], float) / o - 1
    return np.hstack([A, hi.reshape(-1, 1), lo.reshape(-1, 1)])


def era_mask(A, span):
    return BR.era_mask(A, span) & np.isfinite(A[:, C["rclose"]])


def summary_of(by_era):
    plus = [q.get("lo") is not None and q["lo"] > 0 for q in (by_era["e1"], by_era["e2"], by_era["e3"])]
    if all(plus):
        return OK_ALL
    if plus[0] and plus[1]:
        return OK_OLD
    return NONE


# ════════════════════ 数える ════════════════════

def _sides(A, idio):
    """→ [(組の名前, 向き(+1 買い／−1 売り), 当てはまる行, 費用)]"""
    d = BR.groups(A, idio)
    mk, pp = K.marks(A, idio), K.pops(A)
    out = [(g, name, +1, d[src] & pp["P1"], LONG_COST) for g, name, src in LONGS]
    for g, name in SHORTS:
        for p, pname, _ in K.POPS:
            out.append((f"{g}-{p}", f"{name}（{pname}）を売る", -1, mk[g] & pp[p], SHORT_COST))
    return out


def analyze(A):
    A, idio = PG.idio_gap(A)
    res = {"eras": {}, "groups": {}}
    for key, name, span in ERAS:
        em = era_mask(A, span)
        days = np.unique(A[em, C["day"]])
        res["eras"][key] = {"name": name, "days": int(len(days)), "rows": int(em.sum()),
                            "first": dt.date.fromordinal(int(days[0])).isoformat() if len(days) else None,
                            "last": dt.date.fromordinal(int(days[-1])).isoformat() if len(days) else None}
    tv, ratio, rc = A[:, C["turnover"]], A[:, C["tv_ratio"]], A[:, C["rclose"]]
    dayc = A[:, C["day"]]
    years = (("2023年10月〜", "2023-10-10", "2023-12-31"), ("2024年", "2024-01-01", "2024-12-31"),
             ("2025年", "2025-01-01", "2025-12-31"), ("2026年", "2026-01-01", "2026-10-05"))
    with np.errstate(invalid="ignore"):
        cuts = {"K1": (("+1〜+3％", (idio >= 0.01) & (idio < 0.03)), ("+3〜+5％", (idio >= 0.03) & (idio < 0.05)), ("+5％以上", idio >= 0.05)),
                "K2": (("B かつ C", (ratio >= K.TV_HIGH)), ("B で C でない", ~(ratio >= K.TV_HIGH))),
                "K3": (("5〜10倍", (ratio >= K.TV_HIGH) & (ratio < 10)), ("10倍以上", ratio >= 10))}
    for g, name, sgn, sel, cost in _sides(A, idio):
        v = sgn * rc - cost
        adverse = A[:, C["rhigh"]] if sgn < 0 else -A[:, C["rlow"]]       # 1日のうちに逆に動いた幅（正の数）
        by_era = {}
        for key, ename, span in ERAS:
            m = era_mask(A, span) & sel
            q = BR.net_mean(A, v, m, alpha=ALPHA)
            q.update(gross=BR._plain(sgn * rc, m), strict=BR._plain(sgn * rc - STRICT_COST - (K.BORROW if sgn < 0 else 0), m),
                     adverse=BR._plain(adverse, m),
                     turnover={lab: BR._plain(v, m & (tv >= lo) & (tv < hi)) for lab, lo, hi in S.TURNOVER_BANDS[1:]})
            by_era[key] = q
        e3 = era_mask(A, PD.NEW) & sel
        read = {"years": {lab: BR._plain(v, e3 & (dayc >= PD._ord(a)) & (dayc <= PD._ord(b))) for lab, a, b in years}}
        base = g.split("-")[0]
        if base in cuts:
            extra = K.marks(A, idio)["K2"] if base == "K2" else np.ones(len(A), bool)
            read["cut"] = {lab: {key: BR._plain(v, era_mask(A, span) & sel & c & extra) for key, _, span in ERAS}
                           for lab, c in cuts[base]}
        res["groups"][g] = {"name": name, "side": "買い" if sgn > 0 else "売り", "cost": cost, "eras": by_era, "read": read,
                            "summary": summary_of(by_era)}
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
    out = {"n_codes": n_codes, "missing": {k: len(v) for k, v in missing.items()}, "rows": int(len(A)), "store": store, "eras": {}}
    for key, name, span in ERAS:
        em = era_mask(B, span)
        out["eras"][key] = {"days": int(len(np.unique(B[em, C["day"]]))), "rows": int(em.sum()),
                            "groups": {g: int((em & sel).sum()) for g, _, _, sel, _ in _sides(B, idio)}}
    return out


# ════════════════════ 書く ════════════════════

def _p(x, d=2):
    return Y._pct(x, d) if x is not None else "—"


def _band(q):
    return "—" if q.get("lo") is None else f"{_p(q['lo'])}〜{_p(q['hi'])}"


def _cell(c):
    return "—" if c.get("mean") is None else f"{_p(c['mean'])}（{c['n']:,}）"


def render_md(res):
    L = ["# J31 板寄せどうし（寄り成行で入り、引け成行で出る）で数え直す：目印の付いた株の売り・安く寄った株の買い", "",
         f"更新: {res.get('generated_at', '')}（事前登録＝`PILLAR_PREREG.md`「J31」・指紋 `{(res.get('prereg_sha256') or '')[:12]}`）", ""]
    r = res.get("result") or {}
    if "error" in r:
        return "\n".join(L + [f"⚠️ 計算できず：{r['error']}", "", "※ 研究の記録です。投資助言ではありません。"]) + "\n"
    L += ["**目隠しではない＝判定ではなく数え直し**（E1・E2 は J19・J29・J30 で、E3 の窓の組は J13 で見ている）。プラスでも売買の決まりにはせず、前向きを別に登録して確かめる。",
          f"数字は寄り（始値）で入って大引け（終値）で出たときの、1回あたりの損益率の平均（売りはプラス＝売りが勝った）。費用＝板寄せどうし（買い 往復{LONG_COST * 100:.2f}％・"
          f"売り {SHORT_COST * 100:.2f}％）。幅は 99.44％（日と銘柄で引き直した広いほう）。", ""]
    for key, e in r["eras"].items():
        L.append(f"- {e['name']}：{e['first']}〜{e['last']}・{e['days']:,}営業日・{e['rows']:,}朝")
    L += ["", "## まとめ", "", "| 組 | 向き | まとめ |", "|---|---|---|"]
    for g, x in r["groups"].items():
        L.append(f"| {g} {x['name']} | {x['side']} | **{x['summary']}** |")
    for g, x in r["groups"].items():
        L += ["", f"## {g} {x['name']}", "",
              "| 時代 | 件数 | 費用前（勝った割合） | 費用後 | 99.44％の幅 | 前半／後半 | 費用0.1％なら | 1日のうちに逆に動いた幅 | 1〜10億円 | 10億円以上 |",
              "|---|---:|---|---:|---|---|---:|---:|---:|---:|"]
        for key, q in x["eras"].items():
            gr = q["gross"]
            win = "—" if gr["win"] is None else f"{gr['win'] * 100:.0f}％"
            tvs = [_cell(c) for c in q["turnover"].values()]
            L.append(f"| {r['eras'][key]['name']} | {q['n']:,} | {_p(gr['mean'])}（{win}） | {_p(q['value'])} | {_band(q)} | "
                     f"{_p(q.get('early'))}／{_p(q.get('late'))} | {_p(q['strict']['mean'])} | {_p(q['adverse']['mean'])} | {tvs[0]} | {tvs[1]} |")
        rd = x["read"]
        L.append("")
        L.append("読むだけ・E3 の年ごと（費用後）：" + "／".join(f"{lab} {_cell(c)}" for lab, c in rd["years"].items()))
        if "cut" in rd:
            for lab, by in rd["cut"].items():
                L.append(f"- {lab}（費用後）：" + "／".join(f"{r['eras'][k]['name']} {_cell(c)}" for k, c in by.items()))
    L += ["", "## 注意", "",
          "- 板寄せでも自分の注文で値段が少し動く（小さい株ほど）。始値が特別気配で遅れて決まる日は、その値で約定する前提",
          "- B は寄りの気配で判断して寄りの前に注文する＝実際の始値と気配がずれる。C は前の日の引けでわかる",
          "- 熱い株は一般信用の売りの在庫が無いことが多く、制度信用でも売り禁になることがある。大引けでストップ高に張り付くと買い戻しが付かない日がある",
          "- いま上場している銘柄だけ（生き残りの偏り＝売りには不利な向き）", "", "---", "",
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
