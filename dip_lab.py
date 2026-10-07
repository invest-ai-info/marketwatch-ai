# -*- coding: utf-8 -*-
"""J23 寄りのあとに急落した株は、何％下がったところで反転するか（反転した株の底の深さ・深さごとの戻り方・その深さに指値で拾ったときの損益）。
2026-10-07 登録・オーナー「そしたら逆に寄りで急落した銘柄が反転して急騰したときに、何パーセント下がったときに反転するのか調べてください」。
PILLAR_PREREG.md「J23」。

深さ＝前日の終値から見た安値（前日比）。窓＝主 9:00〜9:30（5分足・J22 と同じ朝）／確かめ 9:00〜10:00（1時間足・それより前の朝）／
長い期間 1日（日足 2016-11〜2023-09・読むだけ）。判定＝前日比 −X％ に買いの指値・付いたら買い・窓の終わりに売る（費用は J19 の見積もり）。
反転した株の底の深さと、深さごとの戻り方は読むための表（結果から選ぶので、その深さで買えば戻るという意味ではない）。

⚠️ 決まりは PILLAR_PREREG.md「J23」と下の定数に固定。朝の行は prevday_lab（J16）、費用は bounce_cost_lab（J19）と同じ。
⚠️ 出力（dip-lab.json / .md）は集計だけ・銘柄名とコードは出さない（SYNC禁忌）。

実行: python dip_lab.py --check   （点検だけ＝行数と指値が付いた回数。損益は数えない・何も書き出さない）
      python dip_lab.py           （本番。Actions の dip-lab.yml から手動で・1回だけ）
"""
import datetime as dt
import json
import sys

import numpy as np

import bounce_cost_lab as BC
import gap_lab as GL
import highs_trap_lab as T
import jp_bars
import pillar_lab as P
import prevday_lab as PD
import yori_lab as Y

OUT_JSON, OUT_MD = "dip-lab.json", "dip-lab.md"
FIRST, LAST = PD.OLD[0], PD.NEW[1]          # 2016-11-01〜2026-10-05
LONG = PD.OLD                              # 長い期間（日足・読むだけ）
NEW_FROM = PD.NEW[0]                       # 2023-10-10
COLS = PD.COLS + ("spread", "op_r", "lo930_r", "p930_r", "lo_slot", "lo1000_r", "p1000_r", "loday_r", "close_r")
C = {k: i for i, k in enumerate(COLS)}
MIN_STOCKS = 500
LEVELS = (0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.10, 0.15)
THROUGH = 0.002                            # 指値より 0.2％以上下まで付いたら買えた
N_Q = len(LEVELS)
ALPHA = 0.05 / N_Q                         # 99.375％ の幅
REV_DEPTH, REV_BOUNCE = -0.03, 0.03        # 反転した株＝前日比 −3％以下まで下げ、安値から +3％以上戻した
NEAR_LOW = 0.005
MKT_DOWN = -0.015                          # その朝の全銘柄の安値の深さの中央値がこれ以下＝相場全体が下げた朝
BANDS = (("−3〜−4％", -0.04, -0.03), ("−4〜−5％", -0.05, -0.04), ("−5〜−7％", -0.07, -0.05),
         ("−7〜−10％", -0.10, -0.07), ("−10〜−15％", -0.15, -0.10), ("−15％以下", -np.inf, -0.15))
WINDOWS = (("main", "主 9:00〜9:30（5分足）", "lo930_r", "p930_r"), ("conf", "確かめ 9:00〜10:00（1時間足）", "lo1000_r", "p1000_r"),
           ("long", "長い期間 1日（日足 2016-11〜2023-09・読むだけ）", "loday_r", "close_r"))
UP, DOWN = "上", "下"
BOTH_UP, BOTH_DOWN, NONE = "✅ その深さで拾うと費用後プラス（9:30 と 10:00 の両方）", "✕ その深さで拾うと費用後マイナス（両方）", "見えない"
QS = (10, 25, 50, 75, 90)


# ════════════════════ 行 ════════════════════

def window_5m(bars5, op):
    """9:30 より前に始まる5分足 → (安値〔寄り値より上にしない〕, 安値の足の番号 0＝9:00〜5＝9:25)"""
    win = [b for b in sorted(bars5 or []) if b[0].hour == 9 and b[0].minute < 30]
    if not win:
        return np.nan, np.nan
    lows = [b[3] for b in win]
    k = int(np.argmin(lows))
    if op <= lows[k]:
        return op, 0.0
    return lows[k], float(win[k][0].minute // 5)


def window_1h(bars1h):
    """9:00 から始まる1時間足 → (安値, 終値)。無ければ (NaN, NaN)"""
    for t, o, h, lo, c, v in bars1h or []:
        if (t.hour, t.minute) == (9, 0):
            return lo, c
    return np.nan, np.nan


def _f(x):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return np.nan
    return x if np.isfinite(x) else np.nan


def _ok_low(lo, op):
    lo = _f(lo)
    return lo if np.isfinite(lo) and lo > 0 and lo / op - 1 >= -T.MAX_MOVE else np.nan


def stock_rows(ci, daily, m5, h1, drops=None):
    """J16 の行（2016-11〜2026-10）＋費用の見積もり＋3つの窓の安値と出口（どれも前日の終値で割った値）"""
    A = PD.stock_rows(ci, daily, m5, h1, first=FIRST, last=LAST, recent_from=NEW_FROM, drops=drops)
    if not len(A):
        return np.zeros((0, len(COLS)))
    sp = {dt.date.fromisoformat(d).toordinal(): v for d, v in BC.ar_spread(daily).items()}
    pos = {dt.date.fromisoformat(r[0]).toordinal(): i for i, r in enumerate(daily)}
    out = []
    for row in A:
        j = pos[int(row[C["day"]])]
        day, op, lo_d, close = daily[j][0], daily[j][1], daily[j][3], daily[j][4]
        pc = daily[j - 1][4]
        lo5, slot, p930 = np.nan, np.nan, np.nan
        if np.isfinite(row[C["r930"]]):
            lo5, slot = window_5m(m5.get(day), op)
            lo5 = _ok_low(lo5, op)
            p930 = op * (1 + row[C["r930"]]) if np.isfinite(lo5) else np.nan
        lo1, c1 = np.nan, np.nan
        if day >= NEW_FROM:
            lo1, c1 = (_f(x) for x in window_1h(h1.get(day)))
            lo1 = _ok_low(min(lo1, op), op) if np.isfinite(lo1) else np.nan
            if not (np.isfinite(lo1) and np.isfinite(c1) and abs(c1 / op - 1) <= T.MAX_MOVE):
                lo1, c1 = np.nan, np.nan
        lod = _f(lo_d)
        lod = _ok_low(min(lod, op), op) if np.isfinite(lod) else np.nan
        out.append((sp.get(int(row[C["day"]]), np.nan), op / pc, lo5 / pc, p930 / pc, slot, lo1 / pc, c1 / pc,
                    lod / pc, close / pc if np.isfinite(lod) else np.nan))
    return np.hstack([A, np.array(out, float).reshape(-1, 9)])


# ════════════════════ 窓と指値 ════════════════════

def samples(A):
    """→ {main, conf, long} の行の印と、5分足の期間の始まり（序数）"""
    day = A[:, C["day"]]
    sp = np.isfinite(A[:, C["spread"]])
    has5 = np.isfinite(A[:, C["lo930_r"]]) & np.isfinite(A[:, C["p930_r"]])
    u, n = np.unique(day[has5], return_counts=True)
    ok = u[n >= MIN_STOCKS]
    start = int(ok.min()) if len(ok) else None
    new_from, long0, long1 = PD._ord(NEW_FROM), PD._ord(LONG[0]), PD._ord(LONG[1])
    main = has5 & sp & (day >= start) if start else np.zeros(len(A), bool)
    conf = np.isfinite(A[:, C["lo1000_r"]]) & np.isfinite(A[:, C["p1000_r"]]) & sp & (day >= new_from)
    if start:
        conf &= day < start
    long = np.isfinite(A[:, C["loday_r"]]) & np.isfinite(A[:, C["close_r"]]) & sp & (day >= long0) & (day <= long1)
    return {"main": main, "conf": conf, "long": long}, start


def limit_trades(A, x, lo_col, exit_col):
    """前日比 −x に買いの指値 → (費用前の値動き〔付かなかった行は NaN〕, 寄りで買えたか)"""
    lim = 1 - x
    op, lo, ex = A[:, C["op_r"]], A[:, C[lo_col]], A[:, C[exit_col]]
    ok = np.isfinite(lo) & np.isfinite(ex)
    with np.errstate(invalid="ignore"):
        at_open = ok & (op <= lim)
        intra = ok & ~at_open & (lo <= lim * (1 - THROUGH))
        entry = np.where(at_open, op, lim)
        ret = np.where(at_open | intra, ex / entry - 1, np.nan)
    return ret, at_open


def net_of(A, ret):
    return ret - BC.cost(A[:, C["spread"]])


def measure(A, v, m, alpha=ALPHA):
    """印 m の行の v の平均（日と銘柄で引き直した広いほう）・前半と後半"""
    g = np.where(m & np.isfinite(v), 0, -1)
    n = int((g == 0).sum())
    out = {"n": n, "value": None, "lo": None, "hi": None, "early": None, "late": None}
    if n == 0:
        return out
    stat = lambda mu: mu[0]  # noqa: E731
    pt, lo_d, hi_d = GL.boot(v, g, 1, A[:, C["day"]], stat, alpha)
    _, lo_c, hi_c = GL.boot(v, g, 1, A[:, C["code"]], stat, alpha)
    days = np.unique(A[g == 0, C["day"]])
    cut = days[len(days) // 2]
    d = A[:, C["day"]]
    out.update(value=pt, early=float(v[(g == 0) & (d < cut)].mean()) if ((g == 0) & (d < cut)).any() else None,
               late=float(v[(g == 0) & (d >= cut)].mean()), by_day=[lo_d, hi_d], by_stock=[lo_c, hi_c])
    if None not in (lo_d, lo_c, hi_d, hi_c):
        out.update(lo=min(lo_d, lo_c), hi=max(hi_d, hi_c))
    return out


def direction(q, halves=True):
    if q.get("lo") is None or q["n"] < T.MIN_N:
        return None
    d = UP if q["lo"] > 0 else DOWN if q["hi"] < 0 else None
    if d and halves:
        s = 1 if d == UP else -1
        if q.get("early") is None or q.get("late") is None or q["early"] * s <= 0 or q["late"] * s <= 0:
            return None
    return d


def summarize(dm, dc):
    if dm and dc:
        return (BOTH_UP if dm == UP else BOTH_DOWN) if dm == dc else NONE
    if dm:
        return f"△ 9:30 だけ：{dm}"
    if dc:
        return f"△ 10:00 だけ：{dc}"
    return NONE


# ════════════════════ 読むための表 ════════════════════

def _stats(v, m):
    x = v[m & np.isfinite(v)]
    if not len(x):
        return {"n": 0, "mean": None, "win": None}
    return {"n": int(len(x)), "mean": float(x.mean()), "win": float((x > 0).mean())}


def reversal_tables(A, m, lo_col, exit_col, with_slot):
    lo, ex, op = A[:, C[lo_col]], A[:, C[exit_col]], A[:, C["op_r"]]
    with np.errstate(invalid="ignore", divide="ignore"):
        depth, bounce = lo - 1, ex / lo - 1
        rec = (ex - lo) / (1 - lo)
    plunged = m & (depth <= REV_DEPTH)
    rev = plunged & (bounce >= REV_BOUNCE)
    out = {"n_plunged": int(plunged.sum()), "n_rev": int(rev.sum()), "bands": {}}
    if rev.any():
        out["depth_q"] = [float(np.percentile(depth[rev], q)) for q in QS]
        out["from_open_q"] = [float(np.percentile((lo / op - 1)[rev], q)) for q in QS]
        out["rev_by_band"] = {name: int((rev & (depth > a) & (depth <= b)).sum()) for name, a, b in BANDS}
        if with_slot:
            s = A[rev, C["lo_slot"]]
            out["slot"] = [int((s == k).sum()) for k in range(6)]
    for name, a, b in BANDS:
        mb = plunged & (depth > a) & (depth <= b)
        n = int(mb.sum())
        out["bands"][name] = {"n": n} if not n else {
            "n": n, "bounce3": float((bounce[mb] >= REV_BOUNCE).mean()), "half": float((rec[mb] >= 0.5).mean()),
            "back": float((ex[mb] >= 1).mean()), "near_low": float((bounce[mb] < NEAR_LOW).mean()), "median_bounce": float(np.median(bounce[mb]))}
    return out


def day_median(day, v):
    """→ (日, その日の v の中央値)"""
    if not len(day):
        return np.zeros(0), np.zeros(0)
    order = np.lexsort((v, day))
    d, x = day[order], v[order]
    u, starts, counts = np.unique(d, return_index=True, return_counts=True)
    return u, (x[starts + (counts - 1) // 2] + x[starts + counts // 2]) / 2


def limit_tables(A, m, lo_col, exit_col):
    day = A[:, C["day"]]
    u, med = day_median(day[m], A[m, C[lo_col]] - 1)
    mkt = np.zeros(len(A), bool)
    if len(u):
        mkt[np.where(m)[0]] = (med <= MKT_DOWN)[np.searchsorted(u, day[m])]
    big = A[:, C["turnover"]] >= 10
    out = {"mkt_down_days": int((med <= MKT_DOWN).sum()), "days": int(len(u)), "levels": {}}
    for x in LEVELS:
        ret, at_open = limit_trades(A, x, lo_col, exit_col)
        nt = net_of(A, ret)
        f = m & np.isfinite(nt)
        out["levels"][f"{x:.2f}"] = {"all": _stats(nt, f), "gross": _stats(ret, f), "open_share": float(at_open[f].mean()) if f.any() else None,
                                     "at_open": _stats(nt, f & at_open), "intra": _stats(nt, f & ~at_open),
                                     "big": _stats(nt, f & big), "small": _stats(nt, f & ~big),
                                     "mkt_down": _stats(nt, f & mkt), "mkt_other": _stats(nt, f & ~mkt)}
    return out


def analyze(A):
    S, start = samples(A)
    res = {"sample": {"start_5m": dt.date.fromordinal(start).isoformat() if start else None},
           "judge": {}, "summary": {}, "reading": {}}
    for key, *_ in WINDOWS:
        m = S[key]
        res["sample"][key] = {"days": int(len(np.unique(A[m, C["day"]]))), "rows": int(m.sum())}
    for x in LEVELS:
        k = f"{x:.2f}"
        qs = {}
        for key, _, lo_col, ex_col in WINDOWS[:2]:
            ret, _ = limit_trades(A, x, lo_col, ex_col)
            qs[key] = measure(A, net_of(A, ret), S[key])
        dm, dc = direction(qs["main"]), direction(qs["conf"], halves=False)
        res["judge"][k] = {"main": qs["main"], "conf": qs["conf"], "dir_main": dm, "dir_conf": dc}
        res["summary"][k] = summarize(dm, dc)
    for key, _, lo_col, ex_col in WINDOWS:
        res["reading"][key] = {"reversal": reversal_tables(A, S[key], lo_col, ex_col, key == "main"),
                               "limits": limit_tables(A, S[key], lo_col, ex_col)}
    return res


# ════════════════════ 読む ════════════════════

def load(codes, fetch):
    parts, missing, drops = [], {"daily": [], "h1": [], "m5": []}, {"n": 0}
    for i, code in enumerate(codes):
        d = fetch(code, "1d", "10y")
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
    S, start = samples(A)
    out = {"n_codes": n_codes, "missing": {k: len(v) for k, v in missing.items()}, "rows": int(len(A)), "store": store,
           "start_5m": dt.date.fromordinal(start).isoformat() if start else None, "windows": {}}
    for key, _, lo_col, ex_col in WINDOWS:
        m = S[key]
        fills = {}
        for x in LEVELS:
            ret, at_open = limit_trades(A, x, lo_col, ex_col)
            f = m & np.isfinite(ret)
            fills[f"{x:.2f}"] = [int(f.sum()), int((f & at_open).sum())]
        lo = A[:, C[lo_col]]
        out["windows"][key] = {"days": int(len(np.unique(A[m, C["day"]]))), "rows": int(m.sum()),
                               "plunged_3pct": int((m & (lo - 1 <= REV_DEPTH)).sum()), "fills_and_at_open": fills}
    return out


def _p(x, d=2):
    return Y._pct(x, d)


def _w(x):
    return "—" if x is None else f"{x * 100:.1f}％"


def _cell(s):
    return "—" if not s or not s["n"] else f"{_p(s['mean'])}・勝率 {_w(s['win'])}（{s['n']:,}回）"


def render_md(res):
    L = ["# J23 寄りのあとに急落した株は、何％下がったところで反転するか", "",
         f"作成: {res['generated_at']}（GitHub Actions で計算）。事前登録＝`{P.PREREG}`「J23」（指紋 sha256 `{(res.get('prereg_sha256') or '')[:16]}…`）。",
         "銘柄名は出しません。**深さ＝前日の終値から見た安値（前日比）**。指値＝前日比 −X％ に買い・付いたら買って窓の終わりに売る・費用は銘柄ごとの見積もり（下限 往復 0.1％）。**売買の決まりではない**。", ""]
    r = res.get("result") or {}
    if r.get("error"):
        return "\n".join(L + [f"- ⚠️ 計算できず: {r['error']}", ""]) + "\n"
    s = r["sample"]
    L += [f"- 対象：置き場の一覧 {r.get('n_codes')}銘柄（いま上場している銘柄だけ）。取れなかった銘柄 {r.get('n_missing')}",
          f"- 主 9:00〜9:30＝{s['start_5m']}〜 の {s['main']['days']}朝・{s['main']['rows']:,}行／確かめ 9:00〜10:00＝それより前の {s['conf']['days']}朝・{s['conf']['rows']:,}行／"
          f"長い期間（大引け）＝{s['long']['days']}日・{s['long']['rows']:,}行", "",
          "## まとめ（前日比 −X％ に指値で拾い、窓の終わりに売る・費用後）", "",
          "| 指値の深さ | 9:30（主）の平均（幅 99.375％） | 回数 | 10:00（確かめ）の平均（幅） | 回数 | まとめ |", "|---|---|---:|---|---:|---|"]
    for x in LEVELS:
        k = f"{x:.2f}"
        j = r["judge"][k]
        qm, qc = j["main"], j["conf"]
        L.append(f"| 前日比 −{x * 100:.0f}％ | {_p(qm.get('value'))}（{_p(qm.get('lo'))}〜{_p(qm.get('hi'))}） | {qm['n']:,} | "
                 f"{_p(qc.get('value'))}（{_p(qc.get('lo'))}〜{_p(qc.get('hi'))}） | {qc['n']:,} | {r['summary'][k]} |")
    rd = r["reading"]
    for key, name, *_ in WINDOWS:
        rv = rd[key]["reversal"]
        L += ["", f"## {name}", "",
              f"### 反転した株の底（前日比 −3％以下まで下げ、安値から +3％以上戻した株・{rv['n_rev']:,}回／−3％以下まで下げた {rv['n_plunged']:,}回のうち）", ""]
        if rv.get("depth_q"):
            L += ["- 安値の深さ（前日比）：" + "・".join(f"{q}％点 {_p(v, 1)}" for q, v in zip(QS, rv["depth_q"])),
                  "- 安値の深さ（寄り値から）：" + "・".join(f"{q}％点 {_p(v, 1)}" for q, v in zip(QS, rv["from_open_q"])),
                  "- 深さの区分ごとの数：" + "・".join(f"{k} {v:,}" for k, v in rv["rev_by_band"].items())]
            if rv.get("slot"):
                n = max(sum(rv["slot"]), 1)
                L.append("- 安値をつけた5分足：" + "・".join(f"{t} {c / n * 100:.0f}％" for t, c in zip(("9:00", "9:05", "9:10", "9:15", "9:20", "9:25"), rv["slot"])))
        L += ["", "### 深さごとの戻り方（安値の深さで分けた・結果から見た数字＝その深さで買えば戻るという意味ではない）", "",
              "| 安値の深さ（前日比） | 回数 | +3％以上戻した | 下げの半分以上を戻した | 前日の終値まで戻した | ほぼ安値で終わった | 安値からの戻りの中央値 |", "|---|---:|---:|---:|---:|---:|---:|"]
        for band, b in rv["bands"].items():
            if not b["n"]:
                L.append(f"| {band} | 0 | — | — | — | — | — |")
                continue
            L.append(f"| {band} | {b['n']:,} | {_w(b['bounce3'])} | {_w(b['half'])} | {_w(b['back'])} | {_w(b['near_low'])} | {_p(b['median_bounce'])} |")
        lt = rd[key]["limits"]
        L += ["", f"### 指値の深さごと（費用後の平均・勝率・回数／相場全体が下げた朝＝{lt['mkt_down_days']}朝／{lt['days']}朝）", "",
              "| 指値 | ぜんぶ | 費用前 | 寄りで買えた割合 | 寄りで買えた朝 | 寄りのあとに付いた朝 | 売買代金10億円以上 | 10億円未満 | 相場全体が下げた朝 | それ以外の朝 |",
              "|---|---|---|---:|---|---|---|---|---|---|"]
        for x in LEVELS:
            v = lt["levels"][f"{x:.2f}"]
            L.append(f"| −{x * 100:.0f}％ | {_cell(v['all'])} | {_p(v['gross']['mean'])} | {_w(v['open_share'])} | {_cell(v['at_open'])} | {_cell(v['intra'])} | "
                     f"{_cell(v['big'])} | {_cell(v['small'])} | {_cell(v['mkt_down'])} | {_cell(v['mkt_other'])} |")
    L += ["", "- ⚠️ 主（9:30）は約2か月分だけ。安値に付いた約定は板の薄い株ほど少ない数量のことが多い（0.2％下まで付いたことを条件にしても、実際に買えた数量は分からない）。"
          "いま上場している銘柄だけ＝急落のあと上場をやめた株が入らない（拾う形には甘く出る）。**使うなら前向きの登録で確かめてから**。",
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
        bad = set(missing["daily"]) | set(missing["h1"]) | set(missing["m5"])
        if len(bad) > T.MAX_MISSING * len(codes):
            raise RuntimeError(f"日足・1時間足・5分足のどれかを取れなかった銘柄が {len(bad)}/{len(codes)}＝5％超。偏った組で判定しない（取り直す）")
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
