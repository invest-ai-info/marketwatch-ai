# -*- coding: utf-8 -*-
"""
exit_wall_lab.py — 出口の壁ラボ：「壁が近ければ早めに利確、壁が無ければ伸ばす」は期待値を上げるか。

2026-09-26 オーナー指示「出口がとても重要。損切りは何％でもいいが、利確は伸ばせるときは伸ばしたいし、
思っている以上に近くにテクニカル指標の抵抗があるときは早めに利確したい。その期待値で利益が変わる。
出口戦略をさらに強化する必要がある」。

【事前登録（2026-09-26・本物のデータの結果を見る前に、この説明文ごとコミットして固定する）】
対象   : 監視18銘柄（LEGACY_UNIVERSE）。日足＝2006-01-01〜（主）／4時間足＝直近730日（副）。Yahoo・auto_adjust=True。
入口   : exit_rule_backtest.PAIRS の8つ（エンジンと同じ式）。クールダウン3本・先頭260本は使わない（regime_lab と同じ）。
         族＝順張り（高値ブレイク買い・安値割れ売り・MACD／25-75本線のクロス）／逆張り（RSI売られすぎ反発・−2σタッチの買い）。
         売りは値段を上下反転して買いと同じ計算にかける（exit_lab.mirror と同じ考え方）。
損切り : 全方式で同じ＝入った足の ATR14×1.5（これを 1R）。オーナーの「損切りは何％でもいい」に合わせて固定し、利確側だけを比べる。
         約定は exit_lab と同じ：同じ足で損切りと利確の両方に触れたら損切り／損切りは窓なら始値／値段の利確はちょうど。
         どの方式も最長120本（日足≒半年）で終値で手じまう。データの最後まで決着しない入口は、全方式から外す（対応をそろえる）。
コスト : signal_lab_sweep.cost_r_of（往復スプレッド×1.5）を1取引1回引く（半分ずつ手じまっても合計は1往復）。
壁（買いの場合。売りは上下反転）: 入った足までに分かる値だけで、入値より上にある次の水準のうち**いちばん近いもの**。
         候補＝直近20本の高値・直近60本の高値（どちらも入った足を含まない＝エンジンの recent_high と同じ作り）／
               直近120本の中の山（前後3本より高い足。入った足の3本前までに確定したもの）／
               25本線・75本線・200本線／ボリンジャー+2σ。
         入値＋0.05ATR より上のものだけ。d_wall＝(壁−入値)÷1R。候補が無ければ「壁なし」。
利確の方式:
  P0 いまの方式 : 2.0ATR（＝1.33R）。
  P1 壁で早め   : 壁が 1.33R より近ければ「壁−0.1ATR」で利確（ただし入値＋0.2R より下には置かない）。それ以外は P0。
  P2 伸ばす     : 利確を置かない。損切りを「入ってからの最高値−3ATR（入った足の ATR）」まで上げていく（下げない）。
                   上げた損切りは、その足を見てから次の足に効く。
  P3 壁で半分   : 壁が 2.67R より近ければ、壁−0.1ATR（下限 入値＋0.2R）で半分を利確し、残り半分は損切りを建値へ上げて
                   P2 と同じ追いかけ方で伸ばす。壁が無い／遠ければ全部を P2。
  P4 場合分け   : 壁が 1.33R より近い→P1／壁が 2.67R 以上先か壁なし→P2／その間→P0（オーナー案をそのまま決まりにしたもの）。
  P5 期待値で選ぶ: 探索期間（〜2015）で、族×壁までの距離（<0.67R／0.67〜1.33R／1.33〜2.67R／2.67R以上か壁なし）×
                   200本線と同じ向きか、の16マスごとに P0〜P3 のうち平均R（コスト後）がいちばん高い方式を選び
                   （そのマスの件数が100未満なら P0）、確かめ期間（2016〜）にその選び方を当てる。
主の比較（日足）: 族（2）×（P1〜P4 の P0 との差・全期間／P5 の P0 との差・2016〜だけ）＝10の比較。同じ入口どうしの差
         （銘柄×年の二方向クラスタ・t補正）。p値は exit_lab と同じ出し方。
         🔁 事前登録の修正（2026-09-26・本物のデータを見る前・較正で発覚）: 二方向クラスタの分散 V1+V2−V12 は、まとまりが
            少ないと引き算で小さく出すぎる（作り物で「期待値で選ぶ」の差の幅が ±0.004R＝素直な計算の約1/7）。
            この研究では V1+V2−V12・V1・V2・V12 の**最大**を使う（mean_ci_safe）。exit_rule_backtest の関数は、公開済みの
            出口の相性ラボが使っているので変えない。
「差がある」と言う条件: ①p値 < ボンフェローニ法（10%÷10） ②差 0.10R 以上 ③前半（〜2015）と後半（2016〜）で向きがそろう
         （P5 は後半しかないので③は無し）。
偽薬（プラセボ）: 同じ銘柄・同じ向きで、シグナルと同じ件数だけランダムな足に入った取引に、同じ方式を当てる（乱数は固定）。
         長く持つ方式（P2〜P4）は、相場全体の長い上げ（ドリフト）を拾うだけで良く見えることがある
         （出口の相性ラボの「利確を置かない」が買いで良く売りで悪いのはその疑い）。
         ⇒ 「差がある」のうち、偽薬の差を引いてもまだ同じ向きに0.05R以上残るものだけを「シグナルの場面に効く」と書き、
            残らなければ「ドリフト（相場全体の上げ下げ）で説明できる」と書く。
期待値の地図（読むための表・判定しない）: 族×壁までの距離×方式ごとの平均R（探索期間・確かめ期間・偽薬）。
前向きの確認（--live）: signals-log.json の sr_runway.d_res_atr（エンジンの直近20本の高値までの距離・買い）で、
         いまの方式の成績を距離ごとに並べる（どの出口が良いかは値動きの道筋が要るので前向きでは測れない＝参考）。
較正（本物のデータを見る前・--synthetic）: regime_lab.synthetic（上下の偏りゼロ・値動きの大きさだけが変わる作り物）で
         同じ手順を回し、主の10比較で「差がある」が出る数を数える。結果はこの下に追記する（基準は動かさない）。
  較正の結果（2026-09-26・本物のデータを見る前）:
         ①最初の作り物（1本の足の中を8歩）では「伸ばす」が +0.13R と出た＝偏りのない値動きなのに有利。原因は
           「損切りの線を1歩で飛び越えた分を無視して線ちょうどで約定」（細かい歩みで直接確かめた: 64歩でも +0.043R±0.013）。
           損切りでしか手じまわない方式ほど有利に出る。⇒ 較正は256歩（SYN_STEPS）で行う。**本物のデータでも、損切りの
           実際の滑りは入っていない**（コストの×1.5 で吸収する想定）＝追いかける損切りの方式は、滑りの分だけ有利に見積もられうる。
         ②二方向クラスタの幅が狭すぎた（上の「事前登録の修正」）。直したあとの作り物20回（乱数1〜20・日足＋4時間足）:
           主の10比較で「差がある」は**0回**。最小p値が0.01を下回ったのは20回中2回（理屈どおり約10%）。
           作り物の方式ごとの平均（コスト後）は −0.04〜+0.02R（どれも0に近い）。
前向き（🆕 2026-09-26 追加・オーナー指示「4つとも登録して前向きに検証して」の①。探索の結果を見た後の登録）:
         登録する仮説は1つ＝「日足の順張りで、2.67R 以内に壁が無い場面では、P2（伸ばす）が P0（いまの方式）より良い」
         （探索〜2015 +0.128R〔n645〕・2016〜 +0.131R〔n791〕。ただし偽薬でも +0.163R＝相場の性質の疑い・4時間足では逆向き）。
         lab_forward.FWD_FROM（2026-09-26）以降に入った取引だけで、lab_forward の決まり（件数100ごと・95%幅が0をまたがず
         同じ向き・差0.10R以上で合格・合格2回連続で確定・逆向きは1回で確定）で毎週判定する。偽薬の前向きも並べる。
         探索（主の比較・期待値の地図）は登録日より前の取引だけで出す（前向きのデータを混ぜない）。
         ⚠️ 検出力: この場面は日足の順張りの約1割＝18銘柄で年に約70件。100件たまるまで1年半ほどかかる見込み。
限界   : 壁の候補はここに挙げたものだけ（キリのいい数字・出来高の多い価格帯は入れていない）／ボリンジャーや移動平均線は
         動くが、入った足の値で固定している／先物のつなぎ目／逆張りは買いだけ。
公開   : しない（オーナー個人向けの研究。売買の推奨ではない）。

使い方（Yahoo に届く所で）: python exit_wall_lab.py --json exit-wall-lab.json --md exit-wall-lab.md
       較正（どこでも）      : python exit_wall_lab.py --synthetic 1,2,3
       前向きの確認           : python exit_wall_lab.py --live signals-log.json --live-only
"""
import argparse
import json
import math
import sys
from collections import defaultdict

import numpy as np
import pandas as pd

import exit_rule_backtest as X
import lab_forward as LF
import regime_lab as RL
from generate_technical_alerts import calc_atr, calc_bbands
from signal_lab_sweep import cost_r_of
from signal_lab_tracker import LEGACY_UNIVERSE

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WARMUP = 260
COOLDOWN = X.COOLDOWN
SL_ATR, TP_ATR = 1.5, 2.0
MAX_HOLD = 120
TRAIL_ATR = 3.0
WALL_EPS_ATR = 0.05
WALL_OFF_ATR = 0.1
MIN_TP_R = 0.2
NEAR_R = TP_ATR / SL_ATR          # 1.33R＝いまの利確までの距離
FAR_R = 2 * NEAR_R                # 2.67R
PIVOT_K, PIVOT_LOOK = 3, 120
SPLIT = pd.Timestamp("2016-01-01")
ALPHA, MIN_EFFECT, PLACEBO_KEEP = 0.10, 0.10, 0.05
P5_MIN_N = 100
SYN_STEPS = 256          # 較正の作り物の、1本の足の中の歩数（少ないと追いかける損切りが有利に出る＝下の較正の記録）
POLICIES = ("P0", "P1", "P2", "P3", "P4")
POLICY_LABEL = {"P0": "いまの方式（2ATR）", "P1": "壁で早め", "P2": "伸ばす（追いかける損切り）",
                "P3": "壁で半分＋残りを伸ばす", "P4": "場合分け（近い壁→早め／壁なし→伸ばす）",
                "P5": "期待値で選ぶ（〜2015で学習）"}
DIST_BUCKETS = ("<0.67R", "0.67-1.33R", "1.33-2.67R", "≥2.67R/なし")


def dist_bucket(d):
    if d is None or d >= FAR_R:
        return "≥2.67R/なし"
    return "<0.67R" if d < NEAR_R / 2 else ("0.67-1.33R" if d < NEAR_R else "1.33-2.67R")


# ───────────────────────── 価格の配列（買いの向きにそろえる） ─────────────────────────
def arrays(df):
    H, L, C = df["High"], df["Low"], df["Close"]
    bbu, _bbm, bbl = calc_bbands(C)
    f = lambda s: s.to_numpy(float)
    return {"o": f(df["Open"]), "h": f(H), "l": f(L), "c": f(C), "atr": f(calc_atr(H, L, C)),
            "ma25": f(C.rolling(25).mean()), "ma75": f(C.rolling(75).mean()), "ma200": f(C.rolling(200).mean()),
            "bbu": f(bbu), "bbl": f(bbl)}


def mirror(A):
    """売りを買いと同じ計算にかけるための上下反転（高値↔安値、+2σ↔−2σ、線は符号反転）。"""
    return {"o": -A["o"], "h": -A["l"], "l": -A["h"], "c": -A["c"], "atr": A["atr"],
            "ma25": -A["ma25"], "ma75": -A["ma75"], "ma200": -A["ma200"], "bbu": -A["bbl"], "bbl": -A["bbu"]}


def wall_above(A, i):
    """入値より上の、いちばん近い壁（値段）。無ければ None。入った足までの情報だけ。"""
    h, c, atr = A["h"], A["c"], A["atr"][i]
    e = c[i]
    floor = e + WALL_EPS_ATR * atr
    cands = []
    if i >= 20:
        cands.append(h[i - 20:i].max())
    if i >= 60:
        cands.append(h[i - 60:i].max())
    lo = max(PIVOT_K, i - PIVOT_LOOK)
    for j in range(lo, i - PIVOT_K + 1):
        w = h[j - PIVOT_K:j + PIVOT_K + 1]
        if h[j] >= w.max():
            cands.append(h[j])
    for k in ("ma25", "ma75", "ma200", "bbu"):
        v = A[k][i]
        if np.isfinite(v):
            cands.append(v)
    above = [x for x in cands if np.isfinite(x) and x > floor]
    return min(above) if above else None


# ───────────────────────── 手じまいの計算（買いの向き） ─────────────────────────
def _run(A, i, tp=None, trail=False, half_tp=None):
    """1取引。tp＝値段の利確（全部）／trail＝追いかける損切り／half_tp＝その値段で半分利確し、残りは建値＋追いかけ。
    戻り値＝(R コスト前, 保有本数) または (None, None)＝データの最後まで決着せず。"""
    o, h, l, c = A["o"], A["h"], A["l"], A["c"]
    n, e, atr = len(c), c[i], A["atr"][i]
    risk = SL_ATR * atr
    stop = e - risk
    hi = e
    got, left = 0.0, 1.0            # 手じまい済みの R（割合込み）・残りの割合
    for j in range(i + 1, min(n, i + MAX_HOLD + 1)):
        if l[j] <= stop:                                        # 損切り（窓なら始値）
            return got + left * (min(o[j], stop) - e) / risk, j - i
        if half_tp is not None and left == 1.0 and h[j] >= half_tp:
            got += 0.5 * (half_tp - e) / risk
            left = 0.5
            stop = max(stop, e)                                 # 残りは建値へ（次の足から効く）
            trail = True
        elif tp is not None and h[j] >= tp:
            return got + left * (tp - e) / risk, j - i
        if j == i + MAX_HOLD:
            return got + left * (c[j] - e) / risk, j - i
        hi = max(hi, h[j])
        if trail:
            stop = max(stop, hi - TRAIL_ATR * atr)
    return None, None


def policies_for(A, i, d_wall_px):
    """P0〜P4 の R（コスト前）と保有本数。"""
    e, atr = A["c"][i], A["atr"][i]
    risk = SL_ATR * atr
    tp0 = e + TP_ATR * atr
    wall_tp = None if d_wall_px is None else max(e + MIN_TP_R * risk, d_wall_px - WALL_OFF_ATR * atr)
    d = None if d_wall_px is None else (d_wall_px - e) / risk
    out = {"P0": _run(A, i, tp=tp0)}
    out["P1"] = _run(A, i, tp=wall_tp) if (d is not None and d < NEAR_R) else out["P0"]
    out["P2"] = _run(A, i, trail=True)
    out["P3"] = _run(A, i, half_tp=wall_tp) if (d is not None and d < FAR_R) else out["P2"]
    out["P4"] = out["P1"] if (d is not None and d < NEAR_R) else (out["P2"] if (d is None or d >= FAR_R) else out["P0"])
    return out, d


def lab_trades(df, ticker, tf, placebo_rng=None):
    """シグナルの取引（placebo_rng=None）／同じ件数のランダムな入口（偽薬）。"""
    sig = X.signals(df)
    A0 = arrays(df)
    Am = mirror(A0)
    times = pd.to_datetime(df.index)
    times = times.tz_convert(None) if times.tz is not None else times
    n, out = len(A0["c"]), []
    for es, side in RL.ENTRIES:
        A = A0 if side == "long" else Am
        ent = sig[es].to_numpy(bool)
        idx, last = [], -10 ** 9
        for i in range(WARMUP, n - 1):
            if ent[i] and i - last > COOLDOWN and A["atr"][i] > 0:
                idx.append(i)
                last = i
        if placebo_rng is not None:
            pool = np.arange(WARMUP, n - 1)
            idx = sorted(placebo_rng.choice(pool, size=min(len(idx), len(pool)), replace=False).tolist())
        for i in idx:
            if not (A["atr"][i] > 0):
                continue
            wall = wall_above(A, i)
            res, d = policies_for(A, i, wall)
            if any(v[0] is None for v in res.values()):
                continue
            e_abs = abs(A["c"][i])
            d_sign = 1 if side == "long" else -1
            cost = cost_r_of({"entry": e_abs, "stop_loss": e_abs - d_sign * SL_ATR * A["atr"][i], "ticker": ticker})
            ma200 = A["ma200"][i]
            out.append({"ticker": ticker, "cls": RL.CLASS_OF.get(ticker, "?"), "tf": tf, "es": es, "side": side,
                        "fam": RL.FAMILY[(es, side)], "time": times[i], "d_wall": d, "bucket": dist_bucket(d),
                        "aligned": bool(np.isfinite(ma200) and A["c"][i] > ma200),
                        "R": {k: v[0] - cost for k, v in res.items()},
                        "gross": {k: v[0] for k, v in res.items()},
                        "bars": {k: v[1] for k, v in res.items()}, "cost": cost})
    return out


# ───────────────────────── P5（期待値で選ぶ） ─────────────────────────
def cell_of(t):
    return (t["fam"], t["bucket"], t["aligned"])


def learn_p5(ts_is):
    """探索期間で、マスごとに平均R最大の方式（P0〜P3）。件数100未満は P0。"""
    by = defaultdict(list)
    for t in ts_is:
        by[cell_of(t)].append(t)
    choice = {}
    for cell, rows in by.items():
        if len(rows) < P5_MIN_N:
            choice[cell] = "P0"
            continue
        means = {p: float(np.mean([r["R"][p] for r in rows])) for p in ("P0", "P1", "P2", "P3")}
        choice[cell] = max(means, key=means.get)
    return choice


def apply_p5(ts, choice):
    for t in ts:
        p = choice.get(cell_of(t), "P0")
        t["R"]["P5"], t["p5_pick"] = t["R"][p], p


# ───────────────────────── 集計 ─────────────────────────
def mean_ci_safe(vals, groups):
    """平均と95%幅（保守版＝exit_rule_backtest._mean_se_safe。理由は同関数と上の「事前登録の修正」）。"""
    if len(vals) < 2:
        return {"n": len(vals)}
    m, se, c = X._mean_se_safe(vals, groups)
    if not math.isfinite(se):
        return {"n": len(vals), "avg": m}
    return {"n": len(vals), "avg": m, "lo": m - c * se, "hi": m + c * se}


def paired(ts, a, b="P0"):
    sel = [t for t in ts if a in t["R"] and b in t["R"]]
    dd = mean_ci_safe([t["R"][a] - t["R"][b] for t in sel], [RL.cluster(t) for t in sel])
    dd["p"] = RL.p_value(dd)
    return dd


def mean_of(ts, p):
    v = [t["R"][p] for t in ts if p in t["R"]]
    return {"n": len(v), "avg": float(np.mean(v)) if v else None}


def evaluate(ts1d, ts4h, pl1d, pl4h):
    is1d = [t for t in ts1d if t["time"] < SPLIT]
    oos1d = [t for t in ts1d if t["time"] >= SPLIT]
    choice = learn_p5(is1d)
    apply_p5(oos1d, choice)
    apply_p5([t for t in pl1d if t["time"] >= SPLIT], choice)
    fam = lambda ts, F: [t for t in ts if t["fam"] == F]
    primary = []
    for F in ("tf", "mr"):
        for p in ("P1", "P2", "P3", "P4", "P5"):
            base = fam(oos1d if p == "P5" else ts1d, F)
            row = {"fam": F, "policy": p, "diff": paired(base, p),
                   "placebo": paired(fam([t for t in pl1d if (p != "P5" or t["time"] >= SPLIT)], F), p),
                   "h4": paired(fam(ts4h, F), p) if p != "P5" and ts4h else {},
                   "h4_placebo": paired(fam(pl4h, F), p) if p != "P5" and pl4h else {},
                   "classes": {k: paired([t for t in base if t["cls"] == k], p) for k in ("index", "fx", "commodity")}}
            if p != "P5":
                row["early"] = paired([t for t in base if t["time"] < SPLIT], p)
                row["late"] = paired([t for t in base if t["time"] >= SPLIT], p)
            primary.append(row)
    m = len(primary)
    for r in primary:
        d = r["diff"]
        s0 = RL._sign(d)
        same = True if r["policy"] == "P5" else (RL._sign(r["early"]) is not None
                                                 and RL._sign(r["early"]) == RL._sign(r["late"]) == s0)
        r["flag"] = bool(d.get("p", 1.0) < ALPHA / m and abs(d.get("avg", 0)) >= MIN_EFFECT and same)
        pl = r["placebo"].get("avg")
        net = None if pl is None or "avg" not in d else d["avg"] - pl
        r["net_of_placebo"] = net
        r["situational"] = bool(r["flag"] and net is not None and s0 is not None and net * s0 >= PLACEBO_KEEP)
    # 期待値の地図（読むための表）
    maps = {}
    for label, ts in (("is", is1d), ("oos", oos1d), ("placebo", pl1d), ("4h", ts4h)):
        for F in ("tf", "mr"):
            for b in DIST_BUCKETS:
                rows = [t for t in ts if t["fam"] == F and t["bucket"] == b]
                maps[f"{label}|{F}|{b}"] = {"n": len(rows),
                                            **{p: (float(np.mean([t["R"][p] for t in rows])) if rows else None)
                                               for p in POLICIES}}
    baseline = {}
    for label, ts in (("1d", ts1d), ("4h", ts4h), ("placebo1d", pl1d)):
        for F in ("tf", "mr"):
            rows = fam(ts, F)
            if rows:
                baseline[f"{label}|{F}"] = {p: mean_of(rows, p) for p in POLICIES}
                baseline[f"{label}|{F}"]["bars_median"] = {p: float(np.median([t["bars"][p] for t in rows]))
                                                           for p in POLICIES}
    share = {}
    for F in ("tf", "mr"):
        rows = fam(ts1d, F)
        share[F] = {b: sum(t["bucket"] == b for t in rows) / max(1, len(rows)) for b in DIST_BUCKETS}
    p5 = {"|".join(map(str, k)): v for k, v in sorted(choice.items(), key=lambda kv: str(kv[0]))}
    return {"primary": primary, "maps": maps, "baseline": baseline, "bucket_share": share, "p5_choice": p5}


FWD_HYPOTHESES = [
    # (キー, 族, 足, 壁までの距離, 方式, 比べる方式, 説明)
    ("tf_open_trail_1d", "tf", "1d", "≥2.67R/なし", "P2", "P0",
     "日足の順張り・2.67R以内に壁なし: 伸ばす − いまの方式"),
]


def forward_section(hist1d, fwd1d, fwdpl1d, prev, today):
    """登録した仮説の前向き（登録日以降の取引だけ）。探索の差の向きを基準に lab_forward で判定を積み上げる。"""
    out = {}
    for key, F, _tf, b, p, q, desc in FWD_HYPOTHESES:
        cell = lambda ts: [t for t in ts if t["fam"] == F and t["bucket"] == b]
        is_d = paired(cell(hist1d), p, q)
        d = paired_fwd(cell(fwd1d), p, q)
        e = LF.step((prev or {}).get(key), d, RL._sign(is_d) or 1, today)
        e.update({"desc": desc, "insample": is_d, "placebo_now": paired_fwd(cell(fwdpl1d), p, q)})
        out[key] = e
    return out


def paired_fwd(ts, a, b="P0"):
    sel = [t for t in ts if a in t["R"] and b in t["R"]]
    dd = mean_ci_safe([t["R"][a] - t["R"][b] for t in sel], [LF.fwd_cluster(t) for t in sel])
    dd["p"] = RL.p_value(dd)
    return dd


def live_check(path):
    """いまの方式の実成績を、エンジンの d_res_atr（直近20本の高値までの距離）ごとに並べる（買い・参考）。"""
    import signal_lab_verify as V
    from signal_lab_sweep import r_used
    d = json.load(open(path, encoding="utf-8"))
    rows = defaultdict(list)
    for r in d:
        if r.get("ticker") not in LEGACY_UNIVERSE or V.family_of(r) is None or "ロング" not in (r.get("direction") or ""):
            continue
        R = r_used(r, net=True, itt=True)
        sr = r.get("sr_runway") or {}
        if R is None or not isinstance(sr, dict):
            continue
        da = sr.get("d_res_atr")
        dr = None if da is None else da / SL_ATR
        rows[(V.family_of(r), dist_bucket(dr))].append(R)
    return {f"{k[0]}|{k[1]}": {"n": len(v), "avg": float(np.mean(v))} for k, v in sorted(rows.items())}


# ───────────────────────── 実行 ─────────────────────────
def build(frames, tf, seed=12345):
    ts, pl = [], []
    rng = np.random.default_rng(seed)
    for tk, df in frames.items():
        ts += lab_trades(df, tk, tf)
        pl += lab_trades(df, tk, tf, placebo_rng=rng)
    return ts, pl


def fmt(dd):
    if not dd or dd.get("avg") is None:
        return "—"
    if "lo" not in dd:
        return f"{dd['avg']:+.3f}R"
    return f"{dd['avg']:+.3f}R [{dd['lo']:+.2f}, {dd['hi']:+.2f}]"


def report_md(res, asof, n1, n4):
    L = [f"# 出口の壁ラボ（asof {asof}）", "", f"日足 {n1:,} 取引・4時間足 {n4:,} 取引（偽薬は同数のランダムな入口）", "",
         "## 主の比較（日足・同じ入口どうしの P0＝いまの方式 との差・コスト後）", "",
         "| 族 | 方式 | 差 | p | 前半 | 後半 | 偽薬の差 | 偽薬を引いた差 | 4時間足 | 判定 |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in res["primary"]:
        v = ("✅差がある" + ("（場面に効く）" if r["situational"] else "（ドリフトで説明できる）")) if r["flag"] else "—"
        net = "—" if r["net_of_placebo"] is None else f"{r['net_of_placebo']:+.3f}R"
        L.append(f"| {RL.FAMILY_LABEL[r['fam']]} | {POLICY_LABEL[r['policy']]} | {fmt(r['diff'])} | {r['diff'].get('p', 1):.4f} | "
                 f"{fmt(r.get('early'))} | {fmt(r.get('late'))} | {fmt(r['placebo'])} | {net} | {fmt(r.get('h4'))} | {v} |")
    L += ["", "## 期待値の地図（日足・壁までの距離ごとの平均R・読むための表）", ""]
    for label in ("is", "oos", "placebo"):
        for F in ("tf", "mr"):
            L.append(f"**{label}｜{RL.FAMILY_LABEL[F]}**")
            L.append("| 壁まで | n | " + " | ".join(POLICY_LABEL[p] for p in POLICIES) + " |")
            L.append("|---|---|" + "---|" * len(POLICIES))
            for b in DIST_BUCKETS:
                m = res["maps"][f"{label}|{F}|{b}"]
                L.append(f"| {b} | {m['n']:,} | " + " | ".join("—" if m[p] is None else f"{m[p]:+.3f}" for p in POLICIES) + " |")
            L.append("")
    L += ["## P5 が探索期間で選んだ方式", "", json.dumps(res["p5_choice"], ensure_ascii=False)]
    if res.get("forward"):
        L += ["", f"## 前向き（{LF.FWD_FROM.date()} 以降に入った取引だけ）", ""]
        for k, f in res["forward"].items():
            L.append(f"- {f['desc']}: n={f['n']} {fmt(f.get('now'))}（偽薬 {fmt(f.get('placebo_now'))}）"
                     f" {f['state']}／探索 {fmt(f.get('insample'))}")
    return "\n".join(L)


def count_flags(res):
    return sum(r["flag"] for r in res["primary"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json")
    ap.add_argument("--md")
    ap.add_argument("--synthetic")
    ap.add_argument("--live")
    ap.add_argument("--live-only", action="store_true")
    ap.add_argument("--no-4h", action="store_true")
    a = ap.parse_args()

    if a.synthetic:
        for seed in [int(s) for s in a.synthetic.split(",")]:
            f1, _vix = RL.synthetic(seed, "1d", steps=SYN_STEPS)
            ts1d, pl1d = build(f1, "1d", seed)
            ts4h, pl4h = ([], []) if a.no_4h else build(RL.synthetic(seed + 10_000, "4h", steps=SYN_STEPS)[0], "4h", seed)
            res = evaluate(ts1d, ts4h, pl1d, pl4h)
            fl = [f"{RL.FAMILY_LABEL[r['fam']]}×{r['policy']}({r['diff']['avg']:+.3f})" for r in res["primary"] if r["flag"]]
            pmin = min(r["diff"].get("p", 1.0) for r in res["primary"])
            b = res["baseline"]
            base = " ".join(f"{k}:" + "/".join(f"{b[k][p]['avg']:+.2f}" for p in POLICIES) for k in b if k.startswith("1d"))
            print(f"seed={seed} 日足{len(ts1d):,} 目立つ={count_flags(res)} 最小p={pmin:.4f} {fl or 'なし'} | {base}", flush=True)
        return

    if a.live_only:
        print(json.dumps(live_check(a.live), ensure_ascii=False, indent=1))
        return

    f1, f4 = {}, {}
    for tk in sorted(LEGACY_UNIVERSE):
        df = X.fetch(tk, "1d")
        if df is not None:
            f1[tk] = df
        if not a.no_4h:
            df4 = X.fetch(tk, "4h")
            if df4 is not None:
                f4[tk] = df4
        print(f"  {tk}: 日足{len(f1.get(tk, [])):,} 4h{len(f4.get(tk, [])):,}", flush=True)
    all1d, pl1d_all = build(f1, "1d")
    all4h, pl4h_all = build(f4, "4h") if f4 else ([], [])
    ts1d, fwd1d = LF.split(all1d)          # 探索は登録日より前だけ・前向きは登録日以降
    pl1d, fwdpl1d = LF.split(pl1d_all)
    ts4h, _ = LF.split(all4h)
    pl4h, _ = LF.split(pl4h_all)
    res = evaluate(ts1d, ts4h, pl1d, pl4h)
    if a.live:
        res["live"] = live_check(a.live)
    asof = pd.Timestamp.now(tz="Asia/Tokyo").strftime("%Y-%m-%d")
    res["forward"] = forward_section(ts1d, fwd1d, fwdpl1d, LF.load_prev(a.json), asof)
    out = {"asof": asof, "fwd_from": str(LF.FWD_FROM.date()), "n_1d": len(ts1d), "n_4h": len(ts4h),
           "n_placebo_1d": len(pl1d), "n_fwd_1d": len(fwd1d), **res}
    if a.json:
        json.dump(RL._jsonable(out), open(a.json, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    md = report_md(res, asof, len(ts1d), len(ts4h))
    if a.md:
        open(a.md, "w", encoding="utf-8").write(md)
    print(md[:4000])
    print("目立つ数:", count_flags(res))


if __name__ == "__main__":
    main()
