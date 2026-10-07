# -*- coding: utf-8 -*-
"""J21 主戦場から地雷銘柄を見つけて外すと、残りの勝率と損益はどうなるか（2006〜2016年で地雷を決め、2016〜2026年で確かめる）。
2026-10-07 登録・オーナー「J20の条件で…地雷銘柄を見つけて排除した場合の勝率を確認してください」。PILLAR_PREREG.md「J21」。

主戦場＝J20 と同じ（前の日 +5％以上 × 前の日の売買代金10億円以上・翌朝の寄りで買う）。地雷の候補9つ（L1〜L9）のうち、
E1（2006〜2016・寄り→大引け）で「当てはまる − 当てはまらない」が 99.44％ の幅でまるごと下のものを地雷とし、
地雷に1つでも当てはまる朝を外した「残り」を E2（2016〜2023・寄り→大引け）・E3（2023〜2026・寄り→10:00）で1回だけ確かめる。
C1 残り − 外した ＞ 0／C2 残りの費用後 ＞ 0（98.75％ の幅）。勝率は判定に使わず必ず並べて示す。

⚠️ 決まりは PILLAR_PREREG.md「J21」と下の定数に固定。行・主戦場・幅は main_field_lab（J20）をそのまま使う。
⚠️ 出力（landmine-lab.json / .md）は集計だけ・銘柄名とコードは出さない（SYNC禁忌）。

実行: python landmine_lab.py --check   （点検だけ＝行数と候補ごとの回数。損益は数えない・何も書き出さない）
      python landmine_lab.py           （本番。Actions の landmine-lab.yml から手動で・1回だけ）
"""
import datetime as dt
import json
import sys

import numpy as np

import gap_lab as GL
import highs_trap_lab as T
import jp_bars
import main_field_lab as MF
import pillar_lab as P
import prevgap_lab as PG
import yori_lab as Y

OUT_JSON, OUT_MD = "landmine-lab.json", "landmine-lab.md"
COLS = MF.COLS + ("tv_ratio", "wick", "hi_close", "new_high")
C = {k: i for i, k in enumerate(COLS)}
ERAS = MF.ERAS
SELECT_ERA, CONFIRM_ERAS = ERAS[0], ERAS[1:]
TV_DAYS, TV_RATIO = 20, 5.0
WICK = 0.5
HI_CLOSE = 0.999
HIGH_DAYS = 250
IDIO = MF.IDIO
CANDIDATES = (("L1", "今朝その銘柄だけ +1％ 以上高く寄る"),
              ("L2", "過熱（前の日の終値が25日線より +15％ 超）"),
              ("L3", "連騰（前の日まで4日以上続けて上がった）"),
              ("L4", "前の日 +15％ 以上の急騰"),
              ("L5", "前の日の売買代金がその前20営業日の平均の5倍以上"),
              ("L6", "前の日の上ヒゲが長い（押し戻された割合 0.5 以上）"),
              ("L7", "前の日が高値引け"),
              ("L8", "前の日に52週高値を更新"),
              ("L9", "今朝その銘柄だけ −1％ 以下安く寄る"))
N_SELECT = len(CANDIDATES)
ALPHA_SELECT = 0.05 / N_SELECT     # 99.44％ の幅
N_CONFIRM = 4
ALPHA_CONFIRM = 0.05 / N_CONFIRM   # 98.75％ の幅
OK, NONE = "✅", "見えない"
BOTH, ONE = "✅ 2つの時代で確認", "△ 片方の時代だけ"


# ════════════════════ 行 ════════════════════

def prev_more(daily):
    """日足の各日 k について（売買代金の倍率・上ヒゲの割合・高値引け・52週高値の更新）。足りないときは NaN"""
    h = np.array([r[2] for r in daily], float)
    lo = np.array([r[3] for r in daily], float)
    c = np.array([r[4] for r in daily], float)
    v = np.array([r[5] or 0 for r in daily], float)
    n = len(c)
    tv = c * v / 1e8
    ratio = np.full(n, np.nan)
    cs = np.concatenate([[0.0], np.cumsum(tv)])
    for k in range(TV_DAYS, n):
        base = (cs[k] - cs[k - TV_DAYS]) / TV_DAYS
        if base > 0:
            ratio[k] = tv[k] / base
    rng = h - lo
    with np.errstate(invalid="ignore", divide="ignore"):
        wick = np.where(rng > 0, (h - c) / rng, 0.0)
    hi_close = (c >= h * HI_CLOSE).astype(float)
    new_high = np.full(n, np.nan)
    if n > HIGH_DAYS:
        past = np.lib.stride_tricks.sliding_window_view(h, HIGH_DAYS)[:-1].max(axis=1)   # k の前の250日（k−250〜k−1）
        new_high[HIGH_DAYS:] = (h[HIGH_DAYS:] > past).astype(float)
    return ratio, wick, hi_close, new_high


def stock_rows(ci, daily, m5, h1, drops=None):
    """J20 の行＋前の日の売買代金の倍率・上ヒゲ・高値引け・52週高値"""
    A = MF.stock_rows(ci, daily, m5, h1, drops=drops)
    if not len(A):
        return np.zeros((0, len(COLS)))
    extra = prev_more(daily)
    pos = {dt.date.fromisoformat(r[0]).toordinal(): i for i, r in enumerate(daily)}
    k = np.array([pos[int(o)] - 1 for o in A[:, MF.C["day"]]])
    return np.hstack([A] + [x[k].reshape(-1, 1) for x in extra])


# ════════════════════ 地雷の候補 ════════════════════

def flag(key, A, idio):
    """→ (当てはまる, 判定できる)"""
    def ok(x):
        return np.isfinite(x)
    if key == "L1":
        return idio >= IDIO, np.ones(len(A), bool)
    if key == "L2":
        x = A[:, C["dev25"]]
        return ok(x) & (x > MF.OVERHEAT), ok(x)
    if key == "L3":
        return A[:, C["streak"]] >= MF.STREAK, np.ones(len(A), bool)
    if key == "L4":
        return A[:, C["rprev"]] >= 0.15, np.ones(len(A), bool)
    if key == "L5":
        x = A[:, C["tv_ratio"]]
        return ok(x) & (x >= TV_RATIO), ok(x)
    if key == "L6":
        return A[:, C["wick"]] >= WICK, np.ones(len(A), bool)
    if key == "L7":
        return A[:, C["hi_close"]] >= 0.5, np.ones(len(A), bool)
    if key == "L8":
        x = A[:, C["new_high"]]
        return ok(x) & (x >= 0.5), ok(x)
    if key == "L9":
        return idio <= -IDIO, np.ones(len(A), bool)
    raise ValueError(key)


def _span(A, span):
    d = A[:, C["day"]]
    return (d >= MF.PD._ord(span[0])) & (d <= MF.PD._ord(span[1]))


def select(A, idio):
    """E1 で地雷を決める。→ ({候補: 測った値}, 地雷の一覧)"""
    _, _, span, col = SELECT_ERA
    m = _span(A, span) & MF.main_field(A)
    out, mines = {}, []
    for key, _ in CANDIDATES:
        f, ok = flag(key, A, idio)
        g = GL.pair_grp(m & ok & f, m & ok & ~f)
        q = MF.measure(A, g, col, "diff", alpha=ALPHA_SELECT)
        mine = (q.get("hi") is not None and min(q["ns"]) >= T.MIN_N and q["hi"] < 0
                and (q.get("early") or 0) < 0 and (q.get("late") or 0) < 0)
        q["mine"] = bool(mine)
        out[key] = q
        if mine:
            mines.append(key)
    return out, mines


def excluded(A, idio, mines):
    """主戦場のうち、地雷に1つでも当てはまる朝（判定できない候補は当てはまらない扱い）"""
    x = np.zeros(len(A), bool)
    for key in mines:
        f, ok = flag(key, A, idio)
        x |= f & ok
    return MF.main_field(A) & x


def winrate(v, m):
    """費用後の損益がプラスだった割合・平均・回数"""
    x = v[m & np.isfinite(v)] - T.COST
    if not len(x):
        return {"n": 0, "win": None, "mean": None}
    return {"n": int(len(x)), "win": float((x > 0).mean()), "mean": float(x.mean())}


def summarize(vs):
    a = [v == OK for v in vs]
    if all(a):
        return BOTH
    if any(a):
        return ONE
    return NONE


def analyze(A):
    A, idio = PG.idio_gap(A)
    cand, mines = select(A, idio)
    res = {"candidates": cand, "mines": mines, "confirm": {}, "winrates": {}, "reading": {}}
    mf = MF.main_field(A)
    excl = excluded(A, idio, mines) if mines else np.zeros(len(A), bool)
    rem = mf & ~excl
    for ek, ename, span, col in ERAS:
        m = _span(A, span)
        v = A[:, C[col]]
        res["winrates"][ek] = {"name": ename, "all": winrate(v, m & mf), "rem": winrate(v, m & rem), "excl": winrate(v, m & excl)}
        if col == "r1000":
            v9 = A[:, C["r930"]]
            res["winrates"][ek]["930"] = {"all": winrate(v9, m & mf), "rem": winrate(v9, m & rem), "excl": winrate(v9, m & excl)}
        res["reading"][ek] = {key: MF._plain(v[m], np.where(m & mf & flag(key, A, idio)[1], np.where(flag(key, A, idio)[0], 0, 1), -1)[m], "diff")[0]
                              for key, _ in CANDIDATES}
    if not mines:
        res["summary"] = {"c1": "地雷なし", "c2": "地雷なし"}
        return res
    for ek, ename, span, col in CONFIRM_ERAS:
        m = _span(A, span)
        q1 = MF.measure(A, GL.pair_grp(m & rem, m & excl), col, "diff", alpha=ALPHA_CONFIRM)
        q2 = MF.measure(A, np.where(m & rem, 0, -1), col, "mean", alpha=ALPHA_CONFIRM)
        q1["verdict"] = OK if (q1.get("lo") is not None and min(q1["ns"]) >= T.MIN_N and q1["lo"] > 0) else NONE
        q2["verdict"] = OK if (q2.get("lo") is not None and q2["ns"][0] >= T.MIN_N and q2["lo"] > 0) else NONE
        res["confirm"][ek] = {"name": ename, "c1": q1, "c2": q2}
    res["summary"] = {c: summarize([res["confirm"][ek][c]["verdict"] for ek, *_ in CONFIRM_ERAS]) for c in ("c1", "c2")}
    years = np.array([dt.date.fromordinal(int(o)).year for o in A[:, C["day"]]])
    v = A[:, C["rclose"]]
    res["by_year"] = {str(y): {"rem": winrate(v, rem & (years == y)), "all": winrate(v, mf & (years == y))} for y in np.unique(years)}
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
        parts.append(stock_rows(i, daily, T._by_day(m5), T._by_day(h1), drops=drops))
        if (i + 1) % 500 == 0:
            print(f"  ...{i + 1}/{len(codes)}", flush=True)
    A = np.vstack(parts) if parts else np.zeros((0, len(COLS)))
    return A, missing, drops


def check_summary(A, missing, n_codes, store):
    B, idio = PG.idio_gap(A)
    mf = MF.main_field(B)
    out = {"n_codes": n_codes, "missing": {k: len(v) for k, v in missing.items()}, "rows": int(len(A)), "store": store, "eras": {}}
    for ek, _, span, col in ERAS:
        m = _span(B, span) & mf & np.isfinite(B[:, C[col]])
        out["eras"][ek] = {"main_field": int(m.sum()),
                           "candidates": {key: [int((m & flag(key, B, idio)[1] & flag(key, B, idio)[0]).sum()),
                                                int((m & flag(key, B, idio)[1] & ~flag(key, B, idio)[0]).sum())] for key, _ in CANDIDATES}}
    return out


def _p(x, d=2):
    return Y._pct(x, d)


def _w(x):
    return "—" if x is None else f"{x * 100:.1f}％"


def render_md(res):
    L = ["# J21 主戦場から地雷銘柄を見つけて外すと、残りの勝率と損益はどうなるか", "",
         f"作成: {res['generated_at']}（GitHub Actions で計算）。事前登録＝`{P.PREREG}`「J21」（指紋 sha256 `{(res.get('prereg_sha256') or '')[:16]}…`）。",
         "銘柄名は出しません。主戦場＝前の日 +5％ 以上 × 前の日の売買代金10億円以上・翌朝の寄りで買う。勝率＝費用（往復 0.1％）を引いてプラスだった割合。**売買の決まりではない**。", ""]
    r = res.get("result") or {}
    if r.get("error"):
        return "\n".join(L + [f"- ⚠️ 計算できず: {r['error']}", ""]) + "\n"
    names = dict(CANDIDATES)
    mines = r["mines"]
    L += [f"- 対象：置き場の一覧 {r.get('n_codes')}銘柄（いま上場している銘柄だけ）。取れなかった銘柄 {r.get('n_missing')}",
          "", "## まとめ", "",
          f"- **2006〜2016年で地雷と決まったもの**：{'・'.join(f'{k} {names[k]}' for k in mines) if mines else 'なし'}",
          f"- **C1 地雷の見分けが効く（残り − 外した ＞ 0）**：{r['summary']['c1']}",
          f"- **C2 地雷を外せば寄りで買ってもプラス（残りの費用後 ＞ 0）**：{r['summary']['c2']}", "",
          "## 勝率と損益（費用後）", "", "| 時代 | 主戦場ぜんぶ | 地雷を外した残り | 外した地雷 | 外した割合 |", "|---|---|---|---|---:|"]
    for ek, *_ in ERAS:
        w = r["winrates"][ek]
        share = (w["excl"]["n"] / w["all"]["n"]) if w["all"]["n"] else None
        cell = lambda x: f"勝率 {_w(x['win'])}・平均 {_p(x['mean'])}（{x['n']:,}回）"  # noqa: E731
        L.append(f"| {w['name']} | {cell(w['all'])} | {cell(w['rem'])} | {cell(w['excl'])} | {_w(share)} |")
        if "930" in w:
            L.append(f"| 　└ 5分足の寄り→9:30（60日分） | {cell(w['930']['all'])} | {cell(w['930']['rem'])} | {cell(w['930']['excl'])} | — |")
    if r["confirm"]:
        L += ["", "## 確かめ（事前登録の4つ・2016〜2023 と 2023〜2026 で1回だけ）", ""]
        for ek, *_ in CONFIRM_ERAS:
            c = r["confirm"][ek]
            q1, q2 = c["c1"], c["c2"]
            L.append(f"- **{c['name']}**：C1 残り − 外した {_p(q1.get('value'))}（幅 {_p(q1.get('lo'))}〜{_p(q1.get('hi'))}）→ **{q1['verdict']}**／"
                     f"C2 残りの費用後 {_p(q2.get('value'))}（幅 {_p(q2.get('lo'))}〜{_p(q2.get('hi'))}）→ **{q2['verdict']}**")
            if q1.get("d60") or q2.get("d60"):
                d1, d2 = q1.get("d60") or {}, q2.get("d60") or {}
                L.append(f"  - 5分足の寄り→9:30（60日分・読むだけ）：C1 {_p(d1.get('value'))}（少ないほうの組 {d1.get('n', 0)}件）／"
                         f"C2 {_p(d2.get('value'))}（{d2.get('n', 0)}件）。30件未満は数字を読まない")
    L += ["", "## 地雷の候補（2006〜2016年で決めた・当てはまる − 当てはまらない の費用後の差）", "",
          "| 候補 | E1 の差（幅 99.44％） | 回数（当てはまる／当てはまらない） | 地雷 | E2 の差（読むだけ） | E3 の差（読むだけ） |", "|---|---|---|:---:|---:|---:|"]
    for key, name in CANDIDATES:
        q = r["candidates"][key]
        L.append(f"| {key} {name} | {_p(q.get('value'))}（{_p(q.get('lo'))}〜{_p(q.get('hi'))}） | {q['ns'][0]:,}／{q['ns'][1]:,} | "
                 f"{'💣' if q['mine'] else '—'} | {_p(r['reading']['e2'][key])} | {_p(r['reading']['e3'][key])} |")
    if r.get("by_year"):
        L += ["", "- 年ごと（地雷を外した残り・寄り→大引け・費用後）：" + "／".join(
            f"{y} 勝率 {_w(v['rem']['win'])}・{_p(v['rem']['mean'])}" for y, v in r["by_year"].items())]
    L += ["", "- ⚠️ L1〜L4・L9 は J20 の表で 2016〜2026 の向きをすでに見ている＝確かめ（C1）は完全な目隠しではない。本当の確かめは前向き。"
          "勝率が5割を超えても負けの1回が大きければ損益はマイナス＝判定は平均で行う。いま上場している銘柄だけ（生き残りの偏り）。空売りは数えない。",
          "", "---", "", "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。"]
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
        bad = set(missing["daily"]) | set(missing["h1"])
        if len(bad) > T.MAX_MISSING * len(codes):
            raise RuntimeError(f"日足か1時間足を取れなかった銘柄が {len(bad)}/{len(codes)}＝5％超。偏った組で判定しない（取り直す）")
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
