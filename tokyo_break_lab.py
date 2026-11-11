# -*- coding: utf-8 -*-
"""TB オーナーの裁量の決まり（及川式）：東京時間の高値・安値を、通貨のシリーズが全部そろって抜けたら押し目で入る／
抜けに失敗したら逆に入る（5分足・日本時間 15:00〜17:00）。2026-11-11 登録・PILLAR_PREREG.md「TB」。

腕A：そろって抜けた（合図）あと、抜けた東京高値（安値）への指値で入る。利確＝直近高値（安値）・損切り＝5分足の終値がレンジの内側に
     戻ったら次の足の始値・時間切れ＝日本時間 20:00。
腕B：合図のあと 16:55 までに終値がレンジの内側に戻ったら、次の足の始値で逆に入る。利確＝東京レンジの真ん中・損切り＝終値がもう一度
     レンジの外に出たら次の足の始値・時間切れ＝20:00。
費用＝実際のスプレッド（買いは買値で入り売値で出る・売りは売値で入り買値で出る）。

⚠️ 決まりは PILLAR_PREREG.md「TB」と下の定数に固定。データは手元の MT5 の5分足だけ＝**手元で1回だけ**回す。
実行（手元）: python tokyo_break_lab.py check --dir C:\\mt5run   （足の数・時刻・スプレッドの単位・合図の数だけ。損益は数えない・何も書き出さない）
             python tokyo_break_lab.py run   --dir C:\\mt5run   （本番・1回だけ → tokyo-break-lab.json（送る）・research/oikawa/tokyo-break-result.md（手元））
"""
import argparse
import datetime as dt
import json
import os
import sys
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

import oikawa_lab as OK

# ════════════════════ 事前登録の値（PILLAR_PREREG.md「TB」） ════════════════════
PAIRS = OK.PAIRS                     # ドル円・ユーロドル・ポンドドル・ユーロ円・ポンド円・豪ドル円・豪ドル米ドル
START = "2022-06-01"
SPLIT = "2024-08-01"                 # 前半＝〜2024-07-31／後半＝2024-08-01〜
JST = ZoneInfo("Asia/Tokyo")
TOKYO = (9 * 60, 15 * 60)            # 東京時間のレンジ＝09:00〜14:55 に始まる足（分）
WINDOW = (15 * 60, 17 * 60)          # 合図・入る足＝15:00〜16:55 に始まる足
TIME_EXIT = 20 * 60                  # 20:00 に始まる足の始値で手じまう
TOKYO_MIN_BARS = 60                  # 72本のうち60本以上
N_MIN = 200
ALPHA = 0.05 / 2                     # 2つの腕
N_PERM = 2000
SEED = 20261111
# 通貨のシリーズ：その通貨が強いときに各ペアが抜ける向き（+1＝東京高値の上・−1＝東京安値の下）
SERIES = {
    "JPY": {"USDJPY": -1, "EURJPY": -1, "GBPJPY": -1, "AUDJPY": -1},
    "USD": {"USDJPY": +1, "EURUSD": -1, "GBPUSD": -1, "AUDUSD": -1},
    "EUR": {"EURJPY": +1, "EURUSD": +1},
    "GBP": {"GBPJPY": +1, "GBPUSD": +1},
    "AUD": {"AUDJPY": +1, "AUDUSD": +1},
}
PREREG = "PILLAR_PREREG.md"
SECTION = "## TB オーナーの裁量の決まり（及川式）"
OUT_JSON = "tokyo-break-lab.json"
OUT_MD = os.path.join("research", "oikawa", "tokyo-break-result.md")
TITLES = {"TB-A": "オーナーの裁量の決まり（及川式）：通貨のシリーズが全部そろって東京時間の高値・安値を抜けたら、抜けた線への押し目で入る・利確は直近高値・"
                  "損切りは終値がレンジの内側に戻ったら（5分足・日本時間 15:00〜17:00・20:00 で手じまう・過去のデータ・1回だけ・手元の MT5）",
          "TB-B": "オーナーの裁量の決まり（及川式）：そろって抜けたあと終値がレンジの内側に戻ったら逆に入る・利確は東京レンジの真ん中"
                  "（5分足・日本時間 15:00〜17:00・20:00 で手じまう・過去のデータ・1回だけ・手元の MT5）"}
SURVIVED = OK.SURVIVED


# ════════════════════ 足をそろえる ════════════════════

def panel(bars):
    """ペアごとの足 → 共通の時刻にそろえた配列 {pair: {o,h,l,c,so}}・時刻（UTC）・日本時間の分・日本時間の日付の番号・日ごとの足の位置"""
    idx = None
    for b in bars.values():
        idx = b.index if idx is None else idx.union(b.index)
    idx = idx[idx >= pd.Timestamp(START, tz="UTC")]
    P = {}
    for p, b in bars.items():
        r = b.reindex(idx)
        P[p] = {k: r[col].to_numpy(float) for k, col in (("o", "open"), ("h", "high"), ("l", "low"), ("c", "close"), ("so", "so"))}
    j = idx.tz_convert(JST)
    minute = np.asarray(j.hour * 60 + j.minute)
    dates = np.asarray([d.isoformat() for d in j.date])
    wd = np.asarray(j.weekday)
    days = {}
    for i, (d, w) in enumerate(zip(dates, wd)):
        if w < 5:
            days.setdefault(d, []).append(i)
    return P, idx, minute, dates, {d: np.asarray(v) for d, v in days.items()}


def tokyo_range(P, pair, rows, minute):
    """その日の東京高値・東京安値・真ん中。足が足りなければ None"""
    m = minute[rows]
    tk = rows[(m >= TOKYO[0]) & (m < TOKYO[1])]
    h, l = P[pair]["h"][tk], P[pair]["l"][tk]
    ok = np.isfinite(h) & np.isfinite(l)
    if ok.sum() < TOKYO_MIN_BARS:
        return None
    hi, lo = float(h[ok].max()), float(l[ok].min())
    return hi, lo, (hi + lo) / 2.0


# ════════════════════ 合図 ════════════════════

def day_signals(P, rows, minute):
    """1日分の合図。[{cur, strong, t, pair, s, hi, lo, mid, w0}]（t＝合図の足・w0＝15:00 以降の最初の足）"""
    m = minute[rows]
    win = rows[(m >= WINDOW[0]) & (m < WINDOW[1])]
    if len(win) == 0:
        return []
    rng = {p: tokyo_range(P, p, rows, minute) for p in PAIRS}
    found = []
    for cur, members in SERIES.items():
        if any(rng[p] is None for p in members):
            continue
        for strong in (+1, -1):
            for t in win:
                ok = True
                for p, sgn in members.items():
                    c = P[p]["c"][t]
                    d = sgn * strong
                    hi, lo, _ = rng[p]
                    if not np.isfinite(c) or not (c > hi if d > 0 else c < lo):
                        ok = False
                        break
                if not ok:
                    continue
                best, best_mv = None, -np.inf
                for p, sgn in members.items():
                    d = sgn * strong
                    o0 = next((P[p]["o"][w] for w in win if np.isfinite(P[p]["o"][w])), np.nan)
                    mv = d * (P[p]["c"][t] - o0) / o0 if np.isfinite(o0) and o0 > 0 else -np.inf
                    if mv > best_mv:
                        best, best_mv = (p, d), mv
                if best is not None:
                    hi, lo, mid = rng[best[0]]
                    found.append({"cur": cur, "strong": strong, "t": int(t), "pair": best[0], "s": float(best[1]),
                                  "hi": hi, "lo": lo, "mid": mid, "w0": int(win[0])})
                break
    found.sort(key=lambda g: g["t"])
    seen, out = set(), []
    for g in found:                                   # 同じ日・同じペア・同じ向きは早いほうだけ
        k = (g["pair"], g["s"])
        if k not in seen:
            seen.add(k)
            out.append(g)
    return out


def all_signals(P, minute, days):
    out = []
    for d in sorted(days):
        for g in day_signals(P, days[d], minute):
            g["day"] = d
            out.append(g)
    return out


# ════════════════════ 入る・出る ════════════════════

def manage(P, pair, rows, minute, k0, s, entry, tp, sl, tp_from_first=True):
    """入ったあとの手じまい。rows＝その日の足の位置・k0＝入った足。sl＝この線の内側（買いは下・売りは上）に終値が来たら次の足の始値で出る。
    戻り値（費用後の損益率・出口の種類）。出る値が取れなければ None"""
    A = P[pair]
    pos = int(np.searchsorted(rows, k0))
    n = len(rows)

    def out_at_open(q):                                # q 番目以降で最初に値のある足の始値で出る
        for r in range(q, n):
            i = rows[r]
            if np.isfinite(A["o"][i]):
                return A["o"][i] if s > 0 else A["o"][i] + (A["so"][i] if np.isfinite(A["so"][i]) else 0.0)
        return None

    for r in range(pos, n):
        i = rows[r]
        if minute[i] >= TIME_EXIT:
            x = out_at_open(r)
            return None if x is None else (s * (x - entry) / entry, "time")
        if not np.isfinite(A["c"][i]):
            continue
        sp = A["so"][i] if np.isfinite(A["so"][i]) else 0.0
        if r > pos or tp_from_first:
            if s > 0 and A["h"][i] >= tp:
                x = max(tp, A["o"][i]) if r > pos else tp
                return (x - entry) / entry, "tp"
            if s < 0 and A["l"][i] + sp <= tp:
                x = min(tp, A["o"][i] + sp) if r > pos else tp
                return -(x - entry) / entry, "tp"
        if (s > 0 and A["c"][i] < sl) or (s < 0 and A["c"][i] > sl):
            x = out_at_open(r + 1)
            return None if x is None else (s * (x - entry) / entry, "sl")
    return None


def trade_a(P, g, rows, minute):
    """腕A：抜けた線への指値。戻り値 dict か None（入れなかった）"""
    A, s = P[g["pair"]], g["s"]
    edge = g["hi"] if s > 0 else g["lo"]
    for i in rows[rows > g["t"]]:
        if minute[i] >= WINDOW[1]:
            break
        if not np.isfinite(A["c"][i]):
            continue
        sp = A["so"][i] if np.isfinite(A["so"][i]) else 0.0
        if s > 0 and A["l"][i] + sp <= edge:
            entry = min(edge, A["o"][i] + sp)
        elif s < 0 and A["h"][i] >= edge:
            entry = max(edge, A["o"][i])
        else:
            continue
        before = rows[(rows >= g["w0"]) & (rows < i)]
        tp = float(np.nanmax(A["h"][before])) if s > 0 else float(np.nanmin(A["l"][before]))
        res = manage(P, g["pair"], rows, minute, int(i), s, entry, tp, edge, tp_from_first=False)
        if res is None:
            return None
        return {"pair": g["pair"], "s": s, "cur": g["cur"], "day": g["day"], "after": res[0], "exit": res[1], "cost": sp / entry,
                "tp_d": abs(tp - entry) / entry, "sl_d": s * (entry - edge) / entry}
    return None


def trade_b(P, g, rows, minute):
    """腕B：終値がレンジの内側に戻ったら次の足の始値で逆に入る"""
    A, s0 = P[g["pair"]], g["s"]
    edge = g["hi"] if s0 > 0 else g["lo"]
    s = -s0
    after_t = rows[rows > g["t"]]
    for n_, i in enumerate(after_t):
        if minute[i] >= WINDOW[1]:
            break
        c = A["c"][i]
        if not np.isfinite(c) or not (c < edge if s0 > 0 else c > edge):
            continue
        if n_ + 1 >= len(after_t):
            return None
        k = after_t[n_ + 1]
        if not np.isfinite(A["o"][k]) or minute[k] >= TIME_EXIT:
            return None
        sp = A["so"][k] if np.isfinite(A["so"][k]) else 0.0
        entry = A["o"][k] + sp if s > 0 else A["o"][k]
        res = manage(P, g["pair"], rows, minute, int(k), s, entry, g["mid"], edge, tp_from_first=True)
        if res is None:
            return None
        return {"pair": g["pair"], "s": s, "cur": g["cur"], "day": g["day"], "after": res[0], "exit": res[1], "cost": sp / entry,
                "tp_d": abs(g["mid"] - entry) / entry, "sl_d": s * (entry - edge) / entry}
    return None


# ════════════════════ 偽薬 ════════════════════

def pool_for(P, pair, s, tp_d, sl_d, minute, days):
    """そのペア・向きで、15:00〜16:55 のすべての足の始値で入った場合の費用後の損益率（利確・損切りの幅は本物の中央値）"""
    A, v = P[pair], []
    for d in sorted(days):
        rows = days[d]
        m = minute[rows]
        for i in rows[(m >= WINDOW[0]) & (m < WINDOW[1])]:
            if not np.isfinite(A["o"][i]):
                continue
            sp = A["so"][i] if np.isfinite(A["so"][i]) else 0.0
            entry = A["o"][i] + sp if s > 0 else A["o"][i]
            res = manage(P, pair, rows, minute, int(i), s, entry, entry * (1 + s * tp_d), entry * (1 - s * sl_d), tp_from_first=True)
            if res is not None:
                v.append(res[0])
    return np.asarray(v, float)


def pools(P, trades, minute, days):
    out = {}
    for k in sorted({(t["pair"], t["s"]) for t in trades}):
        sub = [t for t in trades if (t["pair"], t["s"]) == k]
        out[k] = pool_for(P, k[0], k[1], float(np.median([t["tp_d"] for t in sub])), float(np.median([t["sl_d"] for t in sub])), minute, days)
    return out


# ════════════════════ 集計・判定 ════════════════════

def judge(st, p, old, new):
    if st["n"] < N_MIN:
        return "検定不能"
    if st["lo"] is None or st["lo"] <= 0:
        return "費用後マイナス" if (st["hi"] is not None and st["hi"] < 0) else "0と区別できない"
    if p is None or p >= ALPHA:
        return "でたらめな足と差なし"
    if not ((old or 0) > 0 and (new or 0) > 0):
        return "前半と後半で割れた"
    return SURVIVED


def _group(trades, key):
    out = {}
    for k in sorted({key(t) for t in trades}):
        v = [t["after"] for t in trades if key(t) == k]
        out[k] = {"n": len(v), "after": float(np.mean(v))}
    return out


def summarize(trades, pool=None, n_perm=N_PERM):
    if not trades:
        return {"n": 0, "verdict": "検定不能"}
    after = [t["after"] for t in trades]
    days_ = [t["day"] for t in trades]
    st = OK.cluster(after, days_)
    old = [a for a, d in zip(after, days_) if d < SPLIT]
    new = [a for a, d in zip(after, days_) if d >= SPLIT]
    p, pm = OK.placebo_p(trades, pool, st["mean"], n_perm, SEED) if pool is not None else (None, None)
    out = dict(st, placebo_p=p, placebo_mean=pm, old_mean=float(np.mean(old)) if old else None, new_mean=float(np.mean(new)) if new else None,
               old_n=len(old), new_n=len(new), win=float(np.mean(np.asarray(after) > 0)), cost_mean=float(np.mean([t["cost"] for t in trades])),
               exits={k: sum(1 for t in trades if t["exit"] == k) for k in ("tp", "sl", "time")},
               by_cur=_group(trades, lambda t: t["cur"]), by_pair=_group(trades, lambda t: t["pair"]),
               by_side=_group(trades, lambda t: "買い" if t["s"] > 0 else "売り"))
    out["verdict"] = judge(st, p, out["old_mean"], out["new_mean"])
    return out


def analyze(P, minute, days, n_perm=N_PERM):
    sig = all_signals(P, minute, days)
    res = {"signals": len(sig)}
    for arm, fn in (("A", trade_a), ("B", trade_b)):
        tr = [t for t in (fn(P, g, days[g["day"]], minute) for g in sig) if t is not None]
        res[arm] = summarize(tr, pools(P, tr, minute, days) if tr else None, n_perm)
        res[arm]["not_entered"] = len(sig) - len(tr)
    return res


def verdicts_of(res, today):
    out = {}
    for arm, key in (("A", "TB-A"), ("B", "TB-B")):
        a = res.get(arm) or {}
        v = a.get("verdict")
        if v and v != SURVIVED:
            out[key] = {"status": "stop", "decided_on": today, "n": a.get("n"), "mean": a.get("mean"), "lo": a.get("lo"), "hi": a.get("hi"),
                        "reason": f"{v}（過去のデータ・1回だけ数えた・手元の MT5 の5分足・勝率 {(a.get('win') or 0) * 100:.1f}%・機械の決まりは裁量の一部だけ）"}
    return out


def render_md(rec):
    bp = lambda v: "—" if v is None else f"{v * 1e4:+.2f}bp"
    L = ["# TB オーナーの裁量の決まり（及川式）：東京時間の高値・安値のそろった抜け", "",
         f"更新: {rec.get('generated_jst')}（事前登録＝`PILLAR_PREREG.md`「TB」・節の指紋 `{(rec.get('prereg_sha256') or '')[:12]}`）・データ {rec.get('data')}・合図 {rec['arms'].get('signals')}回", "",
         "| 腕 | 判定 | 回数 | 費用後の平均 | 97.5%の幅 | 偽薬 p | 前半／後半 | 勝率 | 利確／損切り／時間切れ | 入れなかった |", "|---|---|---:|---:|---|---:|---|---:|---|---:|"]
    for arm, key in (("A", "TB-A"), ("B", "TB-B")):
        a = rec["arms"].get(arm) or {}
        if not a.get("n"):
            L.append(f"| {key} | {a.get('verdict')} | 0 | | | | | | | {a.get('not_entered')} |")
            continue
        e = a["exits"]
        L.append(f"| {key} | **{a['verdict']}** | {a['n']} | {bp(a['mean'])} | {bp(a['lo'])}〜{bp(a['hi'])} | "
                 f"{'—' if a['placebo_p'] is None else format(a['placebo_p'], '.4f')} | {bp(a['old_mean'])}／{bp(a['new_mean'])} | "
                 f"{a['win'] * 100:.1f}% | {e['tp']}／{e['sl']}／{e['time']} | {a.get('not_entered')} |")
    L += ["", "## 読むための表（判定しない）", ""]
    for arm, key in (("A", "TB-A"), ("B", "TB-B")):
        a = rec["arms"].get(arm) or {}
        if not a.get("n"):
            continue
        L += [f"### {key}", ""] + [f"- {name}（回数・費用後）：" + "／".join(f"{k} {v['n']}・{bp(v['after'])}" for k, v in a[f].items())
                                   for name, f in (("通貨ごと", "by_cur"), ("ペアごと", "by_pair"), ("買い売りごと", "by_side"))]
        L += [f"- 1回の費用の目安（入る足のスプレッド）：{bp(a['cost_mean'])}", ""]
    L += ["---", "", "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。機械の決まりは裁量の一部だけを数えています。"]
    return "\n".join(L) + "\n"


def load(folder):
    return {p: OK.read_bars(os.path.join(folder, f"m5tick_{p}.csv"), p) for p in PAIRS}


def check(folder):
    bars = load(folder)
    P, idx, minute, dates, days = panel(bars)
    win = (minute >= WINDOW[0]) & (minute < WINDOW[1])
    rep = {"prereg_sha256": OK.section_sha256(PREREG, SECTION), "days": len(days), "bars": {}}
    for p in PAIRS:
        ok = np.isfinite(P[p]["c"])
        so = P[p]["so"][ok & win]
        med = float(np.median(so)) / OK.pip(p) if len(so) else None
        rep["bars"][p] = {"rows": int(ok.sum()), "first_utc": str(idx[ok].min()), "last_utc": str(idx[ok].max()), "window_bars": int((ok & win).sum()),
                          "spread_median_pips": med, "spread_ok": bool(med is not None and OK.SPREAD_PIPS_OK[0] <= med <= OK.SPREAD_PIPS_OK[1])}
    sig = all_signals(P, minute, days)
    rep["signals"] = {"total": len(sig), "by_cur": {c: sum(1 for g in sig if g["cur"] == c) for c in SERIES}}   # 合図の数だけ（損益は数えない）
    return rep


def run(folder, n_perm=N_PERM):
    bars = load(folder)
    P, idx, minute, dates, days = panel(bars)
    res = analyze(P, minute, days, n_perm)
    now = dt.datetime.now(JST)
    return {"kind": "backtest", "unit": "pct", "source": "手元の MT5（BigBoss）の実ティックの5分足",
            "generated_jst": now.isoformat(timespec="minutes"), "prereg_sha256": OK.section_sha256(PREREG, SECTION),
            "data": f"{str(idx.min())[:10]}〜{str(idx.max())[:10]}", "titles": TITLES, "verdicts": verdicts_of(res, now.date().isoformat()), "arms": res}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["check", "run"])
    ap.add_argument("--dir", default=r"C:\mt5run", help="m5tick_*.csv のあるフォルダ")
    a = ap.parse_args(argv)
    if a.mode == "check":
        print(json.dumps(OK._clean(check(a.dir)), ensure_ascii=False, indent=1))
        return 0
    rec = OK._clean(run(a.dir))
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=1)
    os.makedirs(os.path.dirname(OUT_MD), exist_ok=True)
    md = render_md(rec)
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
