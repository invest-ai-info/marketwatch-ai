# -*- coding: utf-8 -*-
"""S3 キリの良い値（00・50）に初めて触れたあと、抜けるか跳ね返るか。2026-09-28 未明登録・オーナー「キリの良い登録はもう作ってください」。

スキャルピング本の整理で残った最後の候補。00・50 に初めて触れた足の次の足から、抜けの取引と跳ね返りの取引を数え、
00・50 から 23pips ずらした値（23・73）に触れたときと比べる。1回だけ数える。
⚠️ 物差しと判定の基準は PILLAR_PREREG.md「S3 キリの良い値」（事前登録・計算より先にコミット済み）と下の定数に固定。
   結果を見てから動かさない。出力には事前登録の中身の指紋（sha256）を書き込む。
⚠️ 出力 round-lab.json / round-lab.md は GitHub 側で生成＝手元から送らない（SYNC禁忌）。
⚠️ エンジン・発火条件・固定オラクル（signal_lab_verify.py）には触れない。メールや売買の決まりは変えない。

実行: python round_lab.py   （Actions の round-lab.yml から手動で）
"""
import datetime as dt
import json
import math
import sys

import numpy as np
import pandas as pd

from box_lab import (COST_MULT, COST_PIPS, OFFICIAL_SPREAD_PIPS, PAIR_NAME, PAIRS, _f, _m, boot_ci, cost_price,
                     pip_size, simulate)
from event_dir_lab import atr_before
from pillar_lab import JST, fetch, prereg_sha256

OUT_JSON, OUT_MD = "round-lab.json", "round-lab.md"
SEED = 20260928
N_BOOT = 2000          # 日を引き直す回数
MIN_N = 300            # 組ごと・これ未満は「件数不足」
ALPHA = 0.05 / 2       # 問いは抜け・跳ね返りの2つ
STEP_PIPS = 50         # キリの良い値の間隔（00・50）
SETS = {"round": 0, "shift": 23}   # キリの良い値／比べる値（23pips 上にずらす）
SET_NAME = {"round": "キリの良い値（00・50）", "shift": "比べる値（23・73）"}
FRESH_BARS = 24        # 直前の24本の値幅に入っていなければ「初めて」
ATR_N = 14
SL_ATR, TP_ATR = 1.5, 2.0
HOLD_BARS = 4          # 入る足を1本目として4本目の終値で時間切れ
ONE_H = pd.Timedelta(hours=1)


def _pips(x, pip):
    return round(float(x) / pip, 6)


def touched_level(pc, hh, ll, offset, step=STEP_PIPS):
    """前の足の終値 pc・この足の高値 hh・安値 ll（すべて pips）→ 触れた値 (値, 向き)。無ければ None。
    下から＝pc＜値≦hh（向き +1）／上から＝pc＞値≧ll（向き −1）。両方に触れたら pc にいちばん近い値"""
    up = offset + step * (math.floor((pc - offset) / step) + 1)      # pc より上で一番近い値
    dn = offset + step * (math.ceil((pc - offset) / step) - 1)       # pc より下で一番近い値
    cands = []
    if up <= hh:
        cands.append((up - pc, up, 1))
    if dn >= ll:
        cands.append((pc - dn, dn, -1))
    if not cands:
        return None
    _, lv, d = min(cands)
    return lv, d


def level_kind(lv, offset, step=STEP_PIPS):
    """00・50（比べる値は 23・73）のどちらか。値は pips の整数"""
    k = int(round((lv - offset) / step))
    base = "00" if k % 2 == 0 else "50"
    return base if offset == 0 else {"00": "23", "50": "73"}[base]


def trades_for(bars, ticker, set_key):
    """1つのペア・1つの組の取引。戻り値＝(行のリスト, 数えなかった理由の数)"""
    offset = SETS[set_key]
    pip = pip_size(ticker)
    o, h, lo, c = (bars[k].to_numpy(float) for k in ("Open", "High", "Low", "Close"))
    ix = bars.index
    P = {"h": [_pips(x, pip) for x in h], "l": [_pips(x, pip) for x in lo], "c": [_pips(x, pip) for x in c]}
    rows, skipped = [], {}
    next_ok = 0
    for t in range(1, len(ix)):
        if t < next_ok:
            continue
        if ix[t] - ix[t - 1] != ONE_H:
            continue
        hit = touched_level(P["c"][t - 1], P["h"][t], P["l"][t], offset)
        if hit is None:
            continue
        lv, direction = hit
        if t < FRESH_BARS or any(P["l"][k] <= lv <= P["h"][k] for k in range(t - FRESH_BARS, t)):
            continue   # 初めてではない（または直前の24本が無い）
        why = None
        if t + 1 >= len(ix) or ix[t + 1] - ix[t] != ONE_H:
            why = "次の足が無い"
        atr = atr_before(h, lo, c, t, ATR_N)
        if why is None and (atr is None or atr <= 0):
            why = "直前の足が足りない"
        if why is None:
            stop = int(ix.searchsorted(ix[t] + ONE_H * (HOLD_BARS + 1)))
            if stop <= t + 1:
                why = "次の足が無い"
        if why:
            skipped[why] = skipped.get(why, 0) + 1
            continue
        e = t + 1
        risk, width = SL_ATR * atr, TP_ATR * atr
        entry, exit_px = float(o[e]), float(c[stop - 1])
        r_b, x_b = simulate(o, h, lo, c, e, stop, entry, direction, risk, width, exit_px)
        r_r, x_r = simulate(o, h, lo, c, e, stop, entry, -direction, risk, width, exit_px)
        cost_r = cost_price(ticker) / risk
        off = OFFICIAL_SPREAD_PIPS.get(ticker)
        off_r = off * pip / risk if off is not None else None
        rows.append({"set": set_key, "ticker": ticker, "date": ix[t].date().isoformat(), "touch_utc": ix[t].isoformat(),
                     "level": lv * pip, "kind": level_kind(lv, offset), "dir": direction,
                     "break_gross": r_b, "break_net": r_b - cost_r, "bounce_gross": r_r, "bounce_net": r_r - cost_r,
                     "cost_r": cost_r,
                     "break_official": (r_b - off_r) if off_r is not None else None,
                     "bounce_official": (r_r - off_r) if off_r is not None else None,
                     "exit_break": x_b, "exit_bounce": x_r})
        next_ok = stop          # 時間切れの足が終わるまで次を数えない
    return rows, skipped


def diff_boot(r_vals, r_days, s_vals, s_days, n_boot=N_BOOT, seed=SEED):
    """キリの良い値の平均 − 比べる値の平均。日ごとのまとまりで日を引き直す（両方の組の日の和集合）。
    戻り値＝(差, 2.5%点, 97.5%点, 両側の p)"""
    days = sorted(set(r_days) | set(s_days))
    at = {d: i for i, d in enumerate(days)}
    nd = len(days)

    def agg(vals, ds):
        s = np.zeros(nd)
        n = np.zeros(nd)
        for v, d in zip(vals, ds):
            s[at[d]] += v
            n[at[d]] += 1
        return s, n

    sr, nr = agg(r_vals, r_days)
    ss, ns = agg(s_vals, s_days)
    rng = np.random.default_rng(seed)
    pick = rng.integers(0, nd, size=(n_boot, nd))
    with np.errstate(invalid="ignore", divide="ignore"):
        diffs = sr[pick].sum(1) / nr[pick].sum(1) - ss[pick].sum(1) / ns[pick].sum(1)
    diffs = diffs[np.isfinite(diffs)]
    obs = float(np.mean(r_vals) - np.mean(s_vals))
    le = (np.sum(diffs <= 0) + 1) / (len(diffs) + 1)
    ge = (np.sum(diffs >= 0) + 1) / (len(diffs) + 1)
    return obs, float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5)), float(min(1.0, 2 * min(le, ge)))


def _pos(v):
    return v is not None and v > 0


def _sub(v, w):
    return v - w if v is not None and w is not None else None


def side_stats(R, S, key, mid):
    rv, sv = [r[f"{key}_net"] for r in R], [r[f"{key}_net"] for r in S]
    rd, sd = [r["date"] for r in R], [r["date"] for r in S]
    diff, dlo, dhi, p = diff_boot(rv, rd, sv, sd)
    lo_, hi_ = boot_ci(rv, rd)
    early = _m(r[f"{key}_net"] for r in R if r["date"] < mid)
    late = _m(r[f"{key}_net"] for r in R if r["date"] >= mid)
    s_early = _m(r[f"{key}_net"] for r in S if r["date"] < mid)
    s_late = _m(r[f"{key}_net"] for r in S if r["date"] >= mid)
    return {"mean": _m(rv), "lo": lo_, "hi": hi_, "gross": _m(r[f"{key}_gross"] for r in R),
            "shift_mean": _m(sv), "shift_gross": _m(r[f"{key}_gross"] for r in S),
            "diff": diff, "diff_lo": dlo, "diff_hi": dhi, "p": p,
            "early": early, "late": late, "diff_early": _sub(early, s_early), "diff_late": _sub(late, s_late),
            "official": _m(r[f"{key}_official"] for r in R)}


def passes(s):
    return (_pos(s["mean"]) and _pos(s["diff"]) and s["p"] < ALPHA and _pos(s["early"]) and _pos(s["late"])
            and _pos(s["diff_early"]) and _pos(s["diff_late"]))


def judge(res):
    if res["n_round"] < MIN_N or res["n_shift"] < MIN_N:
        return "件数不足"
    if passes(res["break"]):
        return "キリの良い値は抜けやすい（抜けに乗る形が残る）"
    if passes(res["bounce"]):
        return "キリの良い値は跳ね返りやすい（跳ね返りを取る形が残る）"
    return "差なし"


def stats(rows):
    R = [r for r in rows if r["set"] == "round"]
    S = [r for r in rows if r["set"] == "shift"]
    res = {"n_round": len(R), "n_shift": len(S)}
    if not R or not S:
        res["verdict"] = "件数不足"
        return res
    ud = sorted({r["date"] for r in R})
    mid = ud[len(ud) // 2]
    res.update({"n_days": len(ud), "first": ud[0], "last": ud[-1], "split": mid})
    res["break"] = side_stats(R, S, "break", mid)
    res["bounce"] = side_stats(R, S, "bounce", mid)
    res["verdict"] = judge(res)
    # ── 読むための表（判定には使わない）──
    res["cost_median"] = float(np.median([r["cost_r"] for r in R]))
    res["n_official"] = sum(1 for r in R if r["break_official"] is not None)
    res["by_kind"] = {k: {"n": len(v), "break": _m(r["break_net"] for r in v), "bounce": _m(r["bounce_net"] for r in v)}
                      for k in ("00", "50", "23", "73") for v in [[r for r in rows if r["kind"] == k]] if v}
    res["by_pair"] = {tk: {"n": len(v), "break": _m(r["break_net"] for r in v), "bounce": _m(r["bounce_net"] for r in v),
                           "n_shift": len(w), "shift_break": _m(r["break_net"] for r in w)}
                      for tk in PAIRS for v, w in [([r for r in R if r["ticker"] == tk], [r for r in S if r["ticker"] == tk])] if v}
    res["by_side"] = {name: {"n": len(v), "break": _m(r["break_net"] for r in v), "bounce": _m(r["bounce_net"] for r in v)}
                      for name, d in (("下から触れた", 1), ("上から触れた", -1)) for v in [[r for r in R if r["dir"] == d]] if v}
    res["exits"] = {key: {k: sum(1 for r in R if r[f"exit_{key}"] == k) / len(R) for k in ("利確", "損切り", "時間切れ")}
                    for key in ("break", "bounce")}
    return res


def render_md(out):
    L = ["# S3 キリの良い値（00・50）に初めて触れたあと、抜けるか跳ね返るかの結果", "",
         f"作成: {out['generated_jst']}（GitHub Actions で計算）。事前登録＝`PILLAR_PREREG.md`「S3 キリの良い値」"
         f"（指紋 sha256 `{(out['prereg_sha256'] or '')[:16]}…`）。",
         "値＝1回の取引の損益（R・費用後。1R＝触れる前の平均的な値幅×1.5）。**売買の決まりではない**。", "",
         f"判定＝キリの良い値の費用後の平均がプラス・比べる値（23・73）との差がプラスで p＜{ALPHA:g}（問いが2つ）・"
         f"前半と後半とも両方プラス。組ごとに{MIN_N}件未満は件数不足", ""]
    if out["missing"]:
        L += [f"⚠️ 取得できなかったペア：{'・'.join(PAIR_NAME[t] for t in out['missing'])}", ""]
    r = out["result"]
    L += [f"判定：**{r['verdict']}**", ""]
    if "break" in r:
        L += [f"キリの良い値 {r['n_round']}件・比べる値 {r['n_shift']}件（キリの良い値に触れた日 {r['n_days']}日・"
              f"{r['first']}〜{r['last']}・前半と後半の境 {r['split']}）", "",
              "| 取引 | キリの良い値 | 95%の幅 | 比べる値 | 差 | 差の95%の幅 | p | 前半 | 後半 | 差（前半） | 差（後半） |",
              "|---|---:|---|---:|---:|---|---:|---:|---:|---:|---:|"]
        for key, name in (("break", "抜け"), ("bounce", "跳ね返り")):
            s = r[key]
            L.append(f"| {name} | {_f(s['mean'])} | {_f(s['lo'])}〜{_f(s['hi'])} | {_f(s['shift_mean'])} | {_f(s['diff'])} | "
                     f"{_f(s['diff_lo'])}〜{_f(s['diff_hi'])} | {s['p']:.4f} | {_f(s['early'])} | {_f(s['late'])} | "
                     f"{_f(s['diff_early'])} | {_f(s['diff_late'])} |")
        L += ["", "## 読むための表（判定には使わない）", "",
              f"- 費用前の平均＝抜け {_f(r['break']['gross'])}R・跳ね返り {_f(r['bounce']['gross'])}R（比べる値は "
              f"{_f(r['break']['shift_gross'])}・{_f(r['bounce']['shift_gross'])}）／費用の中央値 {_f(r['cost_median'], sign=False)}R",
              f"- 公式スプレッドで引いた平均＝抜け {_f(r['break']['official'])}R・跳ね返り {_f(r['bounce']['official'])}R"
              f"（{r['n_official']}件・ユーロ豪ドルとポンド豪ドルは除く）",
              f"- 出口（抜け）：利確 {r['exits']['break']['利確']:.0%}・損切り {r['exits']['break']['損切り']:.0%}・"
              f"時間切れ {r['exits']['break']['時間切れ']:.0%}", "",
              "| 値 | 件数 | 抜け | 跳ね返り |", "|---|---:|---:|---:|"]
        L += [f"| {k} | {v['n']} | {_f(v['break'])} | {_f(v['bounce'])} |" for k, v in r["by_kind"].items()]
        L += ["", "| ペア | 件数 | 抜け | 跳ね返り | 比べる値の件数 | 比べる値の抜け |", "|---|---:|---:|---:|---:|---:|"]
        L += [f"| {PAIR_NAME[t]} | {v['n']} | {_f(v['break'])} | {_f(v['bounce'])} | {v['n_shift']} | {_f(v['shift_break'])} |"
              for t, v in r["by_pair"].items()]
        L += ["", "| 触れた向き（キリの良い値） | 件数 | 抜け | 跳ね返り |", "|---|---:|---:|---:|"]
        L += [f"| {k} | {v['n']} | {_f(v['break'])} | {_f(v['bounce'])} |" for k, v in r["by_side"].items()]
        L.append("")
    if out["skipped"]:
        L += ["数えなかった触れ（ペア・組ごと）：" + "・".join(f"{k} {v}" for k, v in sorted(out["skipped"].items())), ""]
    L += ["---", "", "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。"]
    return "\n".join(L) + "\n"


def main():
    rows, missing, skipped = [], [], {}
    for tk in PAIRS:
        bars = fetch(tk, "1h")
        if bars is None:
            missing.append(tk)
            continue
        for sk in SETS:
            got, sp = trades_for(bars, tk, sk)
            rows += got
            for k, v in sp.items():
                skipped[f"{PAIR_NAME[tk]}:{sk}:{k}"] = v
            print(f"{tk} {sk}: 取引 {len(got)}", file=sys.stderr)
    out = {"generated_jst": dt.datetime.now(JST).strftime("%Y-%m-%dT%H:%M+09:00"),
           "prereg_sha256": prereg_sha256(), "missing": missing, "skipped": skipped,
           "cost_pips": COST_PIPS, "cost_mult": COST_MULT, "result": stats(rows)}
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(render_md(out))
    print(f"wrote {OUT_JSON} / {OUT_MD}", file=sys.stderr)
    return 0 if len(missing) < len(PAIRS) else 1


if __name__ == "__main__":
    sys.exit(main())
