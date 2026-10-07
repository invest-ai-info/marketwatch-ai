# -*- coding: utf-8 -*-
"""J29 安く寄った株の戻りを、費用に幅を持たせて数え直す。
2026-10-07 夜 登録・オーナー「一応登録して続けてください」（J28 の報告の①）。PILLAR_PREREG.md「J29」。

J28 で、日足からの費用の見積もり（J24 の形）は小さい株・中くらいの株で5分足 9:00〜9:30 の約3倍重いと出た。
安く寄った株を寄りで買う3つの組（D1 その銘柄だけ −1％以下・D2 窓 −1％以下・D3 窓 −3％以下）を、3つの時代
（E1 2006〜2016・E2 2016〜2023〔寄り→大引け〕・E3 2023〜2026〔寄り→10:00〕）で、重いほう（J24 そのもの）と
軽いほう（J24 × J28 の比）の2つの費用で数え直す。**目隠しではない＝判定ではなく数え直し**（前向き J13F 腕B で確かめる）。

⚠️ 決まりは PILLAR_PREREG.md「J29」と下の定数に固定。行と重いほうの費用は cost_recount_lab（J24）をそのまま使う。
⚠️ 出力（bounce-range-lab.json / .md）は集計だけ・銘柄名とコードは出さない（SYNC禁忌）。

実行: python bounce_range_lab.py --check   （点検だけ＝行数と組ごとの件数。損益は数えない・何も書き出さない）
      python bounce_range_lab.py           （本番。Actions の bounce-range-lab.yml から手動で・1回だけ）
"""
import datetime as dt
import json
import sys

import numpy as np

import bounce_cost_lab as BC
import cost_recount_lab as CR
import gap_lab as GL
import highs_trap_lab as T
import highs_trap_small as S
import jp_bars
import pillar_lab as P
import prevday_lab as PD
import prevgap_lab as PG
import yori_lab as Y

OUT_JSON, OUT_MD = "bounce-range-lab.json", "bounce-range-lab.md"
C = BC.C
ERAS = (("e1", "E1 2006〜2016年（寄り→大引け）", ("2006-01-04", "2016-10-31"), "rclose"),
        ("e2", "E2 2016〜2023年（寄り→大引け）", PD.OLD, "rclose"),
        ("e3", "E3 2023〜2026年（寄り→10:00）", PD.NEW, "r1000"))
READ_ERA = ("e4", "5分足の朝（寄り→9:30・読むだけ）", PD.NEW, "r930")
GROUPS = (("D1", "その銘柄だけ −1％以下で寄った", "J15 K2・J18 P2"),
          ("D2", "窓 −1％以下で寄った", "J13 G3"),
          ("D3", "窓 −3％以下で寄った", "J13 G4・J13F 腕B"))
IDIO, GAP1, GAP3 = 0.01, -0.01, -0.03
LOW_FACTOR_SMALL, LOW_FACTOR_REST = 0.29, 0.32       # J28 の「5分足 9:00〜9:30 ÷ 日足」の中央値（1億円未満／それ以上）
FLOOR = BC.COST_FLOOR                                 # 往復 0.1％
N_Q = 3
ALPHA = 0.05 / N_Q                                    # 98.33％ の幅
COSTS = (("high", "重いほう（J24 の見積もり）"), ("low", "軽いほう（J24 × J28 の比）"))
OK_BOTH, OK_LOW, NONE = "✅ 費用の見積もりに左右されずプラス", "△ 費用しだい（本当の費用が軽いほうに近ければプラス）", "✕ どちらの費用でもプラスと言えない"


# ════════════════════ 費用と組 ════════════════════

def costs(A):
    """→ (重いほう, 軽いほう)。見積もれない朝は NaN（数えない）"""
    sp = A[:, C["spread"]]
    high = np.where(np.isfinite(sp), np.maximum(sp, FLOOR), np.nan)
    factor = np.where(A[:, C["turnover"]] < 1.0, LOW_FACTOR_SMALL, LOW_FACTOR_REST)
    low = np.where(np.isfinite(sp), np.maximum(sp * factor, FLOOR), np.nan)
    return high, low


def groups(A, idio):
    gap = A[:, C["gap"]]
    return {"D1": idio <= -IDIO, "D2": gap <= GAP1, "D3": gap <= GAP3}


def era_mask(A, span):
    d = A[:, C["day"]]
    return (d >= PD._ord(span[0])) & (d <= PD._ord(span[1]))


def _first(mu):
    return mu[0]


def net_mean(A, v, m, alpha=ALPHA):
    """v（費用後の値）の m の行の平均・日と銘柄で引き直した広いほうの幅・前半後半"""
    ok = m & np.isfinite(v)
    out = {"n": int(ok.sum()), "value": None, "lo": None, "hi": None, "early": None, "late": None}
    if out["n"] < T.MIN_N:
        return out
    g = np.where(ok, 0, -1)
    pt, lo_d, hi_d = GL.boot(v, g, 1, A[:, C["day"]], _first, alpha)
    _, lo_c, hi_c = GL.boot(v, g, 1, A[:, C["code"]], _first, alpha)
    d = A[:, C["day"]]
    days = np.unique(d[ok])
    cut = days[len(days) // 2]
    out.update(value=pt, early=float(v[ok & (d < cut)].mean()), late=float(v[ok & (d >= cut)].mean()),
               by_day=[lo_d, hi_d], by_stock=[lo_c, hi_c])
    if None not in (lo_d, lo_c, hi_d, hi_c):
        out.update(lo=min(lo_d, lo_c), hi=max(hi_d, hi_c))
    return out


def plus(q):
    return q.get("lo") is not None and q["lo"] > 0


def summary_of(by_era):
    """by_era＝{e1/e2/e3: {high: q, low: q}} → 前もって決めた言葉"""
    keys = [k for k, *_ in ERAS]
    if all(plus(by_era[k]["high"]) for k in keys):
        return OK_BOTH
    if all(plus(by_era[k]["low"]) for k in keys):
        return OK_LOW
    return NONE


def _plain(v, m):
    x = v[m & np.isfinite(v)]
    if len(x) < T.MIN_N:
        return {"n": int(len(x)), "mean": None, "win": None}
    return {"n": int(len(x)), "mean": float(x.mean()), "win": float((x > 0).mean())}


def _med(x):
    x = x[np.isfinite(x)]
    return float(np.median(x)) if len(x) else None


def analyze(A):
    A, idio = PG.idio_gap(A)
    high, low = costs(A)
    grp = groups(A, idio)
    res = {"eras": {}, "groups": {}, "reading": {}}
    for key, name, span, col in ERAS + (READ_ERA,):
        em = era_mask(A, span) & np.isfinite(A[:, C[col]])
        days = np.unique(A[em, C["day"]])
        res["eras"][key] = {"name": name, "days": int(len(days)), "rows": int(em.sum()),
                            "first": dt.date.fromordinal(int(days[0])).isoformat() if len(days) else None,
                            "last": dt.date.fromordinal(int(days[-1])).isoformat() if len(days) else None}
    for g, gname, src in GROUPS:
        by_era, read = {}, {}
        for key, name, span, col in ERAS + (READ_ERA,):
            v = A[:, C[col]]
            m = era_mask(A, span) & grp[g]
            q = {c: net_mean(A, v - (high if c == "high" else low), m) for c, _ in COSTS}
            gross = _plain(v, m)
            cost_med = {"high": _med(high[m & np.isfinite(v)]), "low": _med(low[m & np.isfinite(v)])}
            if key == READ_ERA[0]:
                read[key] = dict(q, gross=gross, cost=cost_med)
            else:
                by_era[key] = dict(q, gross=gross, cost=cost_med)
        res["groups"][g] = {"name": gname, "source": src, "eras": by_era, "read": read, "summary": summary_of(by_era)}
        # 読むための表（判定しない）：軽いほうの費用後を、売買代金・株価ごとに（E2・E3）
        tv = A[:, C["turnover"]]
        rd = {}
        for key, name, span, col in ERAS[1:]:
            v = A[:, C[col]] - low
            base = era_mask(A, span) & grp[g]
            rd[key] = {"turnover": {lab: _plain(v, base & (tv >= lo) & (tv < hi)) for lab, lo, hi in S.TURNOVER_BANDS}}
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
        parts.append(CR.rows_j19(i, daily, T._by_day(m5), T._by_day(h1), CR.ar_spread_avg(daily), drops=drops))
        if (i + 1) % 500 == 0:
            print(f"  ...{i + 1}/{len(codes)}", flush=True)
    A = np.vstack(parts) if parts else np.zeros((0, len(BC.COLS)))
    return A, missing, drops


def check_summary(A, missing, n_codes, store):
    """点検だけ＝行数と組ごとの件数（損益は数えない）"""
    B, idio = PG.idio_gap(A)
    grp = groups(B, idio)
    out = {"n_codes": n_codes, "missing": {k: len(v) for k, v in missing.items()}, "rows": int(len(A)), "store": store, "eras": {}}
    for key, name, span, col in ERAS + (READ_ERA,):
        em = era_mask(B, span) & np.isfinite(B[:, C[col]])
        out["eras"][key] = {"days": int(len(np.unique(B[em, C["day"]]))), "rows": int(em.sum()),
                            "groups": {g: int((em & grp[g] & np.isfinite(B[:, C["spread"]])).sum()) for g, *_ in GROUPS}}
    return out


# ════════════════════ 書く ════════════════════

def _p(x, d=2):
    return Y._pct(x, d) if x is not None else "—"


def _band(q):
    return "—" if q.get("lo") is None else f"{_p(q['lo'])}〜{_p(q['hi'])}"


def render_md(res):
    L = ["# J29 安く寄った株の戻りを、費用に幅を持たせて数え直す", "",
         f"更新: {res.get('generated_at', '')}（事前登録＝`PILLAR_PREREG.md`「J29」・指紋 `{(res.get('prereg_sha256') or '')[:12]}`）", ""]
    r = res.get("result") or {}
    if "error" in r:
        return "\n".join(L + [f"⚠️ 計算できず：{r['error']}", "", "※ 研究の記録です。投資助言ではありません。"]) + "\n"
    L += ["**目隠しではない＝判定ではなく数え直し**（同じデータを J13・J14・J18・J19・J24 で見ている）。プラスでも売買の決まりにはせず、前向き（J13F 腕B）で確かめる。",
          "数字は寄りで買って大引け（E1・E2）／10:00（E3）に売ったときの、費用後の1回あたりの損益率の平均。幅は 98.33％（日と銘柄で引き直した広いほう）。"
          f"重いほう＝J24 の見積もり・軽いほう＝J24 × J28 の比（1億円未満 {LOW_FACTOR_SMALL}・それ以上 {LOW_FACTOR_REST}）・どちらも下限 往復0.1％。", ""]
    for key, e in r["eras"].items():
        L.append(f"- {e['name']}：{e['first']}〜{e['last']}・{e['days']:,}営業日・{e['rows']:,}朝")
    L += ["", "## まとめ", "", "| 組 | 元 | まとめ |", "|---|---|---|"]
    for g, gname, src in GROUPS:
        L.append(f"| {g} {gname} | {src} | **{r['groups'][g]['summary']}** |")
    for g, gname, src in GROUPS:
        x = r["groups"][g]
        L += ["", f"## {g} {gname}", "",
              "| 時代 | 件数 | 費用前（勝った割合） | 費用の中央値（重い／軽い） | 重いほうの費用後 | 98.33％の幅 | 軽いほうの費用後 | 98.33％の幅 |",
              "|---|---:|---|---|---:|---|---:|---|"]
        for key, q in list(x["eras"].items()) + list(x["read"].items()):
            gr = q["gross"]
            win = "—" if gr["win"] is None else f"{gr['win'] * 100:.0f}％"
            L.append(f"| {r['eras'][key]['name']} | {q['high']['n']:,} | {_p(gr['mean'])}（{win}） | {_p(q['cost']['high'])}／{_p(q['cost']['low'])} | "
                     f"{_p(q['high']['value'])} | {_band(q['high'])} | {_p(q['low']['value'])} | {_band(q['low'])} |")
    L += ["", "## 読むための表（判定しない）：軽いほうの費用後を前の日の売買代金ごとに", "",
          "| 組 | 時代 | " + " | ".join(lab for lab, *_ in S.TURNOVER_BANDS) + " |", "|---|---|" + "---:|" * len(S.TURNOVER_BANDS)]
    for g, *_ in GROUPS:
        for key, rd in r["reading"][g].items():
            L.append(f"| {g} | {r['eras'][key]['name']} | " + " | ".join(
                "—" if c["mean"] is None else f"{_p(c['mean'])}（{c['n']:,}）" for c in rd["turnover"].values()) + " |")
    L += ["", "## 注意", "",
          "- 軽いほうの比は最近の約60日の5分足から出したもの＝昔の時代の費用は違ったかもしれない（呼値が細かくなる前の E1 は軽いほうでも甘め）",
          "- 5分足の見積もりは取引の少ない足で0に寄りやすい＝軽いほうは本当の費用より軽すぎる可能性がある",
          "- いま上場している銘柄だけ（生き残りの偏り）。空売りは数えない", "", "---", "",
          "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。"]
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
