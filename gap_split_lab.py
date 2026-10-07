# -*- coding: utf-8 -*-
"""J15 窓の戻しは「その銘柄だけの窓」か「相場全体の窓」か（2026-10-07 朝 登録・オーナー「研究ペースをもっと加速させてください」）。
PILLAR_PREREG.md「J15」。

J13 と同じ朝（東証の全上場・1時間足の寄り→10:00・5分足の寄り→9:30）を、窓を2つに分けて数える。
  相場全体の窓＝その朝に数えた全銘柄の窓の中央値／その銘柄だけの窓＝窓 − 相場全体の窓
K1・K2＝同じ朝の銘柄どうし（その銘柄だけの窓 ±1％）／K3・K4＝相場全体の窓 ±0.5％ の朝どうし（全体と一緒に動いただけの銘柄）。

⚠️ 決まりは PILLAR_PREREG.md「J15」と下の定数に固定。値の取り方・幅の出し方は gap_lab.py をそのまま使う。
⚠️ 値段は研究ラボ共通の値段の置き場（jp_bars.py）から読む。出力は集計だけ・銘柄名とコードは出さない（SYNC禁忌）。

実行: python gap_split_lab.py          （本番。Actions の gap-split-lab.yml から手動で・1回だけ）
      python gap_split_lab.py --diag   （件数とデータの形だけ。値動きは出さない・何も書き出さない）
"""
import datetime as dt
import json
import sys

import numpy as np

import build_jp_highs as H
import gap_lab as GL
import highs_trap_lab as T
import jp_bars
import pillar_lab as P
import yori_lab as Y

OUT_JSON, OUT_MD = "gap-split-lab.json", "gap-split-lab.md"
IDIO = 0.01                   # その銘柄だけの窓の境（±1％）
MKT = 0.005                   # 相場全体の窓の境（±0.5％）
MIN_STOCKS = 500              # その朝の銘柄がこれ未満なら、その朝は数えない
N_Q = 4
ALPHA = 0.05 / N_Q            # 98.75％ の幅
JUDGES = (("k1", "K1 その銘柄だけの窓 +1％ 以上 − ±1％ 未満（同じ朝の銘柄どうし）", "up"),
          ("k2", "K2 その銘柄だけの窓 −1％ 以下 − ±1％ 未満（同じ朝の銘柄どうし）", "down"),
          ("k3", "K3 相場全体の窓 +0.5％ 以上の朝 − ±0.5％ 未満の朝（全体と一緒に動いただけの銘柄）", "up"),
          ("k4", "K4 相場全体の窓 −0.5％ 以下の朝 − ±0.5％ 未満の朝（全体と一緒に動いただけの銘柄）", "down"))
MKT_LABELS = ("全体 −0.5％以下", "全体 ±0.5％未満", "全体 +0.5％以上")
IDIO_LABELS = ("銘柄 −1％以下", "銘柄 ±1％未満", "銘柄 +1％以上")


def split(A):
    """→ (使う行, 相場全体の窓, その銘柄だけの窓)。その朝の銘柄が MIN_STOCKS 未満の朝は除く"""
    day = A[:, GL.C["day"]]
    gap = A[:, GL.C["gap"]]
    order = np.argsort(day, kind="stable")
    d_sorted = day[order]
    uniq, starts, counts = np.unique(d_sorted, return_index=True, return_counts=True)
    med = np.empty(len(uniq))
    for i, (s, n) in enumerate(zip(starts, counts)):
        med[i] = np.median(gap[order[s:s + n]])
    ok_day = counts >= MIN_STOCKS
    idx = np.searchsorted(uniq, day)
    keep = ok_day[idx]
    mkt = med[idx]
    return A[keep], mkt[keep], (gap - mkt)[keep]


def groups(mkt, idio):
    """各行の組（K1〜K4 で使う）"""
    i_mid = np.abs(idio) < IDIO
    m_mid = np.abs(mkt) < MKT
    return {
        "k1": GL.pair_grp(idio >= IDIO, i_mid),
        "k2": GL.pair_grp(idio <= -IDIO, i_mid),
        "k3": GL.pair_grp(i_mid & (mkt >= MKT), i_mid & m_mid),
        "k4": GL.pair_grp(i_mid & (mkt <= -MKT), i_mid & m_mid),
    }


def _band3(x, edge):
    return np.where(x <= -edge, 0, np.where(x >= edge, 2, 1))


def analyze(A):
    A, mkt, idio = split(A)
    has10 = np.isfinite(A[:, GL.C["r1000"]])
    days = np.unique(A[has10, GL.C["day"]])
    cut = days[len(days) // 2] if len(days) else 0
    early, late = A[:, GL.C["day"]] < cut, A[:, GL.C["day"]] >= cut
    iso = lambda o: dt.date.fromordinal(int(o)).isoformat() if o else None  # noqa: E731
    day_mkt = {}
    for d, m in zip(A[:, GL.C["day"]], mkt):
        day_mkt[d] = m
    dm = np.array(list(day_mkt.values()))
    res = {"n_rows": int(len(A)), "n_2y": int(has10.sum()), "days": int(len(days)), "first": iso(days[0]) if len(days) else None,
           "last": iso(days[-1]) if len(days) else None, "cut": iso(cut),
           "mkt_days": {"up": int((dm >= MKT).sum()), "mid": int((np.abs(dm) < MKT).sum()), "down": int((dm <= -MKT).sum())},
           "judges": {}}
    G = groups(mkt, idio)
    for key, name, kind in JUDGES:
        grp = G[key]
        q = {"name": name, "all": GL.safe(A, "r1000", grp, 2, GL._diff2, alpha=ALPHA),
             "early": GL.plain(A[early], "r1000", grp[early], 2, GL._diff2), "late": GL.plain(A[late], "r1000", grp[late], 2, GL._diff2),
             "mean_a_cost": GL.mean_cost(A, grp == 0), "mean_b_cost": GL.mean_cost(A, grp == 1),
             "d60": GL.plain(A, "r930", grp, 2, GL._diff2)}
        q["verdict"] = GL.judge_pair(q["all"], q["early"], q["late"], q["mean_a_cost"]["mean"], q["d60"], kind)
        res["judges"][key] = q
    # ── 読むための表（判定しない）──
    mb, ib = _band3(mkt, MKT), _band3(idio, IDIO)
    r = A[:, GL.C["r1000"]]
    res["grid"] = {MKT_LABELS[a]: {IDIO_LABELS[b]: GL._mean(r[(mb == a) & (ib == b)]) for b in range(3)} for a in range(3)}
    return res


def load(codes, jpx, fetch):
    return GL.load(codes, jpx, fetch=fetch)


def diag_summary(A, missing, n_codes):
    B, mkt, idio = split(A)
    has10 = np.isfinite(B[:, GL.C["r1000"]])
    has930 = np.isfinite(B[:, GL.C["r930"]])
    G = groups(mkt, idio)
    day_mkt = {}
    for d, m in zip(B[:, GL.C["day"]], mkt):
        day_mkt[d] = m
    dm = np.array(list(day_mkt.values()))
    return {"n_codes": n_codes, "missing": {k: len(v) for k, v in missing.items()}, "rows_all": int(len(A)), "rows_used": int(len(B)),
            "days_used": int(len(day_mkt)), "mkt_days": {"up": int((dm >= MKT).sum()), "mid": int((np.abs(dm) < MKT).sum()),
                                                        "down": int((dm <= -MKT).sum())},
            "sizes_2y": {k: [int(((g == 0) & has10).sum()), int(((g == 1) & has10).sum())] for k, g in G.items()},
            "sizes_60d": {k: [int(((g == 0) & has930).sum()), int(((g == 1) & has930).sum())] for k, g in G.items()}}


def _p(x, d=2):
    return Y._pct(x, d)


def render_md(res):
    L = ["# J15 窓の戻しは「その銘柄だけの窓」か「相場全体の窓」か", "",
         f"作成: {res['generated_at']}（GitHub Actions で計算）。事前登録＝`{P.PREREG}`「J15」（指紋 sha256 `{(res.get('prereg_sha256') or '')[:16]}…`）。",
         "銘柄名は出しません。値は株価の変化率（％）。**売買の決まりではない**。J13 と同じ朝を窓の分け方を変えて数えたもの（独立した確かめではない）。", ""]
    r = res.get("result") or {}
    if r.get("error"):
        return "\n".join(L + [f"- ⚠️ 計算できず: {r['error']}", ""]) + "\n"
    ps = res.get("price_store") or {}
    md = r["mkt_days"]
    L += [f"- 対象：東証の全上場 {r.get('n_codes')}銘柄（一覧 {r.get('list_date')}）。取れなかった銘柄 {r.get('n_missing')}。値段の置き場：{ps.get('built_at') or '使わず（Yahoo から）'}",
          f"- 1時間足（判定の主・寄り→10:00）：{r['first']}〜{r['last']}・{r['days']}営業日・{r['n_2y']:,}件（前半と後半の境 {r['cut']}）",
          f"- 相場全体の窓（その朝の全銘柄の窓の中央値）：+0.5％ 以上の朝 {md['up']}日／±0.5％ 未満 {md['mid']}日／−0.5％ 以下 {md['down']}日",
          f"- その朝が {T.END_DAY} までだけ。幅は98.75％（p＜0.05÷4）・日と銘柄で引き直した広いほう",
          "", "## 判定（事前登録の4つ・寄り→10:00 の平均の差・費用前）", ""]
    for key, _, _ in JUDGES:
        q = r["judges"][key]
        a = q["all"]
        L.append(f"- **{q['name']}**：差 {_p(a.get('diff'))}（幅 {_p(a.get('lo'))}〜{_p(a.get('hi'))}・{'対'.join(f'{n:,}' for n in a['ns'])}件）・"
                 f"前半 {_p(q['early'].get('diff'))}／後半 {_p(q['late'].get('diff'))}・その組の費用後 {_p(q['mean_a_cost'].get('mean'))}"
                 f"（比べる相手 {_p(q['mean_b_cost'].get('mean'))}）・5分足の寄り→9:30 の差 {_p(q['d60'].get('diff'))} → **{q['verdict']}**")
    L += ["", "## 読むための表（判定しない）", "", "### 相場全体の窓 × その銘柄だけの窓（寄り→10:00 の平均・費用なし・件数）", "",
          "| | " + " | ".join(IDIO_LABELS) + " |", "|---|---:|---:|---:|"]
    for a, row in r["grid"].items():
        L.append(f"| {a} | " + " | ".join(f"{_p(v.get('mean'))}（{v['n']:,}）" for v in row.values()) + " |")
    L += ["", "- 30件未満の区分は「—」。小さい株は売り買いの差が大きく、費用 0.1％ は甘い（判定は差なので費用は消える）。空売りは数えない。",
          "", "---", "", "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。"]
    return "\n".join(L) + "\n"


def main(argv):
    res = {"generated_at": dt.datetime.now(P.JST).isoformat(timespec="minutes"), "prereg_file": P.PREREG,
           "prereg_sha256": P.prereg_sha256(), "end_day": T.END_DAY}
    try:
        stocks, list_date = jp_bars.load_universe()
        codes = sorted(stocks)
        jpx = H.load_new_listings()
        A, missing, drops = load(codes, jpx, jp_bars.fetcher())
        res["price_store"] = jp_bars.info()
        if "--diag" in argv:
            print(json.dumps(diag_summary(A, missing, len(codes)), ensure_ascii=False, indent=1))
            return 0
        bad = set(missing["daily"]) | set(missing["h1"])
        if len(bad) > T.MAX_MISSING * len(codes):
            raise RuntimeError(f"日足か1時間足を取れなかった銘柄が {len(bad)}/{len(codes)}＝5％超。偏った組で判定しない（取り直す）")
        res["result"] = dict(analyze(A), n_codes=len(codes), list_date=list_date,
                             n_missing={k: len(v) for k, v in missing.items()}, n_dropped=drops["n"])
    except Exception as e:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        if "--diag" in argv:
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
