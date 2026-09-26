# -*- coding: utf-8 -*-
"""
exit_lab.py — 出口の相性ラボ：入口シグナル × 損切りの型 × 利確の型 を、同じ入口に全部当てて比べる。

2026-09-24 オーナー指示「どのシグナルで入ったときにどの損切りが合うのか、どの利確が相性がいいのかをリサーチしたい。
研究日誌で日々検証して公開する（『この入口にはこの出口が合う』という記事は書かない）」。
GitHub Actions（exit-lab.yml・週1）が価格を取って計算し、exit-lab.json / exit-lab.md を書く。
研究日誌の routine は Yahoo に届かないので、この JSON を読むだけ。

【事前登録（2026-09-24・結果を見る前にコミットして固定する）】
入口     : exit_rule_backtest.PAIRS の8つ（エンジン detect_signals と同じ式・クールダウン3本・先頭80本は使わない）。
足       : 日足 2006-01-01〜／4時間足 直近730日（1時間足を resample）。18銘柄（LEGACY_UNIVERSE）。
損切りの型（SL_TYPES）と利確の型（TP_TYPES）は下の表。全部の組み合わせ（8×9）を同じ入口に当てる。
  売りは値段を上下反転して買いと同じ計算にかける（高値↔安値、+2σ↔−2σ、RSI70↔30、25本線の上↔下）。
R の単位 : その組の**最初の損切り幅**を 1R（ロットを損切り幅から逆算する運用）。損切り幅が 0.3ATR 未満になる入口は
           その組では「対象外」（幅が狭すぎてロットが極端になる）。利確が入値の向こうに無い入口も「対象外」
           （例: 節目の利確で高値更新中／真ん中の線・+2σ・RSI70 をすでに超えている）。
約定     : 同じ足で損切りと利確の両方に触れたら損切り（保守側）。損切りは窓なら始値。値段の利確はちょうど。
           終値で決める手じまい（25本線割れ・真ん中の線・+2σ・RSI70・時間）はその足の終値。
           追いかける損切り（シャンデリア・パラボリック・タートル・建値）は、その足を見てから次の足に効く（上げる方向だけ）。
           半分利確は +1R に触れた足で半分を 1R で決済し、残りの損切りを次の足から建値へ。
           どの組も最長 120本（日足≒半年・4時間足≒20日）で終値で手じまう。データの最後まで決着しない入口は数えない。
コスト   : signal_lab_sweep.cost_r_of と同じ往復スプレッド×1.5 を、その組の 1R で割って引く（1取引1回）。
期間     : 探索（IS）＝2026-09-25 より前に出たシグナル／前向き（FWD）＝2026-09-25 以降。
主な数字 : 組ごとの 1取引あたり平均R（コスト後）と、**いまの方式（ATRの1.5倍／ATRの2倍）との差**（両方が対象の入口だけで対応をとる）。
           ※「いまの方式」は損切り・利確の幅がエンジンと同じ。期限はエンジンの21本／42本ではなく全組共通の最長120本
             （追いかける損切りのように長く持つ組と同じ条件で比べるため。1.5ATR／2ATR はほとんど10本前後で決着する）。
           95%幅は exit_rule_backtest と同じ二方向クラスタ（銘柄×時期）＋t補正。前向きは時期を年月で区切る。
「目立つ」と言う条件（IS）: いまの方式との差について、①p値がボンフェローニ法（誤りの確率10%÷比べるマスの数）を下回る
           ②差が 0.15R 以上 ③日足は前半（〜2015）と後半（2016〜）で向きがそろう。の3つ全部。
           較正（2026-09-24・本物のデータを見る前）: 癖のない値動き（足し算のランダムウォーク×18銘柄・コスト0）で同じ手順を
           3回まわすと、最初に置いた「BH法10%＋差0.10R」は毎回約10マスを誤って「目立つ」とした（ぶれの大きい組で幅が狭く出る）。
           上の3条件にすると 0・1・0マス（平均0.3）。⇒ この基準を採用。コストを入れると損切りの近い組ほど悪く出るが、
           それは本物の相場でも起きる実在の差（作り物の値動きは値段に対する値幅が小さく、コストが5〜10倍重く出る点に注意）。
           ⚠️ 組み合わせが 8入口×72組×2足＝1,152 と多い＝「目立つ」は**候補**であって結論ではない。
           候補は exit-lab-hypotheses.json に登録し、前向き（FWD）で確かめて初めて「確かめられた」と書く。
前向きの確かめ方（2026-09-24・前向きのデータが1件も無いうちに固定）:
           探索期間で「目立つ」になったマスごとに、前向き期間の「いまの方式との差」を見る。件数100以上で、
           95%幅が0をまたがず探索期間と同じ向き、かつ差が0.10R以上なら「前向きでも同じ向き」。100件ごとに見直し、
           2回続けて同じ向きなら「確かめられた」（exit-lab-hypotheses.json・研究日誌のトラッカーと同じ考え方）。
           前向き期間は全マス共通で 2026-09-25 以降＝探索期間の判定に前向きのデータは入らない（後から目立ったマスでも同じ）。
4時間足の注意: Yahoo の1時間足は直近730日しか取れないので、4時間足の探索期間は毎週古い側が少しずつ削れる。
           そのため p値が境目のマスは週ごとに「目立つ」を出入りする（1回目と2回目の試走でも1マス入れ替わった）。
           日足の探索期間は 2006〜2026-09-24 で固定＝入れ替わらない。
🔁 較正の訂正（2026-09-25）: 上の「0・1・0マス（平均0.3）」は乱数3つ（1000・3000・7000）だけの結果だった。別の乱数3つ
           （0・100・200）では6・3・3マス＝6回で平均約2.2。誤検出の多くは4時間足のシャンデリア型（1R が小さい組）。
           「目立つ」の基準そのものは事前登録どおり変えない（実データを見た後なので）。ただし**目立つ組が数マスなら、
           偶然でも出る数の範囲**と読む（2026-09-24 の実データは4マス）。
🔁 幅の出し方の切り替え（2026-09-26 オーナー決定「安全側の計算に切り替えて」）: 95%幅の二方向クラスタの分散 V1+V2−V12 は、
           まとまり（銘柄18・年）が少ないと引き算で小さく出すぎることがある（出口の壁ラボの較正で発覚）。exit_rule_backtest._mean_se を
           V1+V2−V12・V1・V2・V12 の最大（_mean_se_safe）に切り替えた。「目立つ」の3条件そのもの（ボンフェローニ10%・差0.15R・前後半）は変えない。
           較正（細かい作り物＝regime_lab.synthetic 256歩・5回）: 全18銘柄の表の誤検出 旧 2・2・2・0・0（平均1.2）→ 新 0・1・0・0・0（平均0.2）。
           資産クラス別 旧 平均0.6 → 新 0。粗い作り物（8歩）では追いかける損切りが有利に出る別の偏りがあり、上の「0・1・0・6・3・3」は
           その影響も受けていた。実データ（2026-09-26）では、旧で目立った12マスのうち7マスが新でも残った（全部 −2σタッチ買い×シャンデリア）。
           旧い幅で出し直すときは --legacy-se。
資産クラス別（2026-09-25 オーナー指示「株・FX・コモディティは分けて考えて」。実データのクラス別の数字を見る前に固定）:
           株価指数（5銘柄）・FX（9銘柄）・コモディティ（金・銀・原油）・暗号資産（ビットコイン）に分けて、同じ72組を当てる。
           割り振りは signal_lab_verify.GROUPS（研究日誌の group と同じ）。json の各マスの "group"（"all" が全18銘柄）。
           「目立つ」は全18銘柄とは別の家族として数え（ボンフェローニ法の分母も別）、条件は全18銘柄と同じ3つに加えて
           **差0.25R以上・いまの方式と比べられた取引が200件以上**。較正: 作り物の値動き6回で
           0・1・1・0・0・0マス（平均0.3）。差0.15R・件数制限なしのままだと6〜11マス（平均8）出たため厳しくした。
           暗号資産は1銘柄＝銘柄のまとまりで幅を出せないので、数字は出すが「目立つ」の判定はしない。
公開     : 研究日誌で「検証結果」として公開してよい（オーナー判断 2026-09-24）。ただし「この入口にはこの出口が合う／
           おすすめ」とは書かない。良い組も悪い組も並べ、組み合わせが多いぶん偶然で良く見える可能性を必ず書く。

使い方（Yahoo に届く所で）: python exit_lab.py --json exit-lab.json --md exit-lab.md [--tf 1d,4h]
"""
import argparse
import json
import math
import sys

import numpy as np
import pandas as pd

import exit_rule_backtest as X
from generate_technical_alerts import calc_atr, calc_bbands, calc_rsi
from signal_lab_sweep import cost_r_of
from signal_lab_tracker import LEGACY_UNIVERSE
from signal_lab_verify import GROUPS

SL_TYPES = {
    "atr": "ATRの1.5倍（いまの方式）",
    "swing": "直近20本の安値の少し下（節目）",
    "ma": "25本線を終値で割ったら",
    "chandelier": "シャンデリア（22本の最高値−3ATRを追いかける）",
    "psar": "パラボリックSAR",
    "turtle": "タートル型（2N＋10本安値割れ）",
    "atr_time": "ATRの1.5倍＋10本で時間切れ",
    "be": "ATRの1.5倍＋1Rで建値へ",
}
TP_TYPES = {
    "atr2": "ATRの2倍（いまの方式）",
    "swing": "直近20本の高値（節目）",
    "rr2": "損切り幅の2倍",
    "rr3": "損切り幅の3倍",
    "bb_mid": "ボリンジャーの真ん中の線",
    "bb_up": "ボリンジャー+2σ（売りは−2σ）",
    "rsi70": "RSI70超え（売りは30割れ）",
    "none": "利確を置かない",
    "half": "半分を1Rで利確・残りは建値で",
}
BASE = ("atr", "atr2")
MAX_HOLD = 120
MIN_RISK_ATR = 0.3
IS_UNTIL = pd.Timestamp("2026-09-25")
ALPHA = 0.10            # ボンフェローニ法の誤りの確率（全マス合わせて）
MIN_EFFECT_LAB = 0.15   # 目立つと言う差の大きさ（較正で決めた）
CLASS_MIN_EFFECT = 0.25  # 資産クラス別の家族だけ: 差の大きさ（2026-09-25 較正で決めた・実データのクラス別を見る前）
CLASS_MIN_N = 200        # 資産クラス別の家族だけ: いまの方式と比べられた取引の件数
COMBOS = [(s, t) for s in SL_TYPES for t in TP_TYPES]

# 資産クラス別（2026-09-25 オーナー指示「株・FX・コモディティはそれぞれ分けて考えて。入り方も出方も違うと思う」）。
# 銘柄の割り振りは signal_lab_verify.GROUPS（固定オラクル）から作る＝研究日誌の group と同じ区切り。
ASSET_CLASSES = {
    "index": ("株価指数", ("index",)),
    "fx": ("FX", ("jpy_fx", "other_fx")),
    "commodity": ("コモディティ", ("metal", "oil")),
    "crypto": ("暗号資産", ("btc",)),
}
FLAG_CLASSES = ("index", "fx", "commodity")   # 暗号資産は1銘柄＝銘柄のまとまりで幅を出せないので参考表示だけ
CLASS_OF = {t: key for key, (_lab, gs) in ASSET_CLASSES.items() for g in gs for t in GROUPS[g]}


def arrays(df):
    """計算に使う列を numpy にまとめる（エンジンと同じ式）。"""
    H, L, C = df["High"], df["Low"], df["Close"]
    bbu, bbm, bbl = calc_bbands(C)
    f = lambda s: s.to_numpy(float)
    return {"o": f(df["Open"]), "h": f(H), "l": f(L), "c": f(C),
            "atr": f(calc_atr(H, L, C)), "atr20": f(calc_atr(H, L, C, 20)), "atr22": f(calc_atr(H, L, C, 22)),
            "ma25": f(C.rolling(25).mean()), "bbu": f(bbu), "bbm": f(bbm), "bbl": f(bbl), "rsi": f(calc_rsi(C))}


def mirror(A):
    """売りを買いと同じ計算にかけるための上下反転。"""
    return {"o": -A["o"], "h": -A["l"], "l": -A["h"], "c": -A["c"],
            "atr": A["atr"], "atr20": A["atr20"], "atr22": A["atr22"],
            "ma25": -A["ma25"], "bbu": -A["bbl"], "bbm": -A["bbm"], "bbl": -A["bbu"], "rsi": 100.0 - A["rsi"]}


def sim_long(A, i, sl, tp):
    """買い1回分。戻り値＝(R コスト前, 保有本数, 決着の仕方, 1R の値幅) または None（対象外・未決着）。"""
    o, h, l, c = A["o"], A["h"], A["l"], A["c"]
    n, e, atr = len(c), c[i], A["atr"][i]
    if sl in ("atr", "atr_time", "be"):
        stop = e - 1.5 * atr
    elif sl == "swing":
        stop = l[i - 19:i + 1].min() - 0.3 * atr
    elif sl == "ma":
        stop = A["ma25"][i]                     # 終値で判定する。1R＝入値−25本線
    elif sl == "chandelier":
        stop = h[i - 21:i + 1].max() - 3 * A["atr22"][i]
    elif sl == "psar":
        stop = l[i - 4:i + 1].min()             # パラボリックの出発点＝直近5本の安値
    elif sl == "turtle":
        stop = max(e - 2 * A["atr20"][i], l[i - 9:i + 1].min())
    else:
        raise ValueError(sl)
    risk = e - stop
    if not (risk >= MIN_RISK_ATR * atr):
        return None
    target = None
    if tp == "atr2":
        target = e + 2 * atr
    elif tp == "swing":
        target = h[i - 19:i + 1].max()
        if target <= e:
            return None
    elif tp == "rr2":
        target = e + 2 * risk
    elif tp == "rr3":
        target = e + 3 * risk
    elif (tp == "bb_mid" and e >= A["bbm"][i]) or (tp == "bb_up" and e >= A["bbu"][i]) or \
            (tp == "rsi70" and A["rsi"][i] >= 70):
        return None
    pos, got, half_done = 1.0, 0.0, False
    af, ep = 0.02, h[i]
    for j in range(i + 1, min(n, i + MAX_HOLD + 1)):
        if sl != "ma" and l[j] <= stop:                         # 値段の損切り（ザラ場・窓なら始値）
            return (got + pos * (min(o[j], stop) - e)) / risk, j - i, "sl", risk
        if target is not None and h[j] >= target:               # 値段の利確（ちょうど）
            return (got + pos * (target - e)) / risk, j - i, "tp", risk
        if tp == "half" and not half_done and h[j] >= e + risk:  # 半分を 1R で
            got, pos, half_done = got + 0.5 * risk, 0.5, True
        closed = None
        if sl == "ma" and c[j] < A["ma25"][j]:
            closed = "sl"
        elif (tp == "bb_mid" and c[j] >= A["bbm"][j]) or (tp == "bb_up" and c[j] >= A["bbu"][j]) or \
                (tp == "rsi70" and A["rsi"][j] > 70):
            closed = "tp"
        elif sl == "atr_time" and j - i >= 10:
            closed = "time"
        elif j == i + MAX_HOLD:
            closed = "maxhold"
        if closed:
            return (got + pos * (c[j] - e)) / risk, j - i, closed, risk
        # 次の足のための損切りの更新（上げる方向だけ）
        if half_done or (sl == "be" and h[j] >= e + risk):
            stop = max(stop, e)
        if sl == "chandelier":
            stop = max(stop, h[j - 21:j + 1].max() - 3 * A["atr22"][j])
        elif sl == "psar":
            if h[j] > ep:
                ep, af = h[j], min(0.2, af + 0.02)
            stop = max(stop, min(stop + af * (ep - stop), l[j], l[j - 1]))
        elif sl == "turtle":
            stop = max(stop, l[j - 9:j + 1].min())
    return None


def entries(df, sig, entry_sig):
    """エンジンと同じ入口（クールダウン3本・先頭80本は使わない）。exit_rule_backtest.trades と同じ選び方。"""
    ent = sig[entry_sig].to_numpy(bool)
    atr = calc_atr(df["High"], df["Low"], df["Close"]).to_numpy(float)
    out, last = [], -10 ** 9
    for i in range(X.WARMUP, len(df) - 1):
        if ent[i] and i - last > X.COOLDOWN and atr[i] > 0:
            out.append(i)
            last = i
    return out


def run_lab(frames):
    """frames＝{(ticker, tf): df} → 入口ごとの取引表 {(tf, entry, side): {"meta": [...], "R": {combo: [...]}}}。"""
    book = {}
    for (ticker, tf), df in frames.items():
        sig = X.signals(df)
        A0 = arrays(df)
        A1 = mirror(A0)
        for _grp, es, side, _xs in X.PAIRS:
            key = (tf, es, side)
            b = book.setdefault(key, {"meta": [], "R": {k: [] for k in COMBOS}})
            A = A0 if side == "long" else A1
            for i in entries(df, sig, es):
                price = float(df["Close"].iloc[i])
                spread = cost_r_of({"entry": price, "stop_loss": price - 1.0, "ticker": ticker})  # 往復×1.5（値段の単位）
                b["meta"].append({"ticker": ticker, "tf": tf, "time": df.index[i]})
                for k in COMBOS:
                    r = sim_long(A, i, *k)
                    b["R"][k].append(None if r is None else (r[0] - spread / r[3], r[0], r[1], r[3] / A["atr"][i]))
    return book


def _groups(meta, fwd):
    return [(m["ticker"], (m["time"].year, m["time"].month) if fwd else
             (m["time"].year if m["tf"] == "1d" else (m["time"].year, (m["time"].month - 1) // 3))) for m in meta]


def _p_value(d):
    """95%幅（t補正込み）から、正規近似の両側 p値に直す（幅を1.96で割った値を標準誤差とみなす）。"""
    if not d or d.get("n", 0) < 2 or not math.isfinite(d.get("lo", float("nan"))) or d["hi"] == d["lo"]:
        return 1.0
    se = (d["hi"] - d["lo"]) / (2 * 1.96)
    return math.erfc(abs(d["avg"]) / se / math.sqrt(2)) if se > 0 else 1.0


def evaluate_lab(book):
    """組ごとの要約・いまの方式との差・ボンフェローニ法・前後半。
    group＝"all"（全18銘柄）と資産クラス（ASSET_CLASSES）ごと。目立つの判定は "all" と資産クラスで別の家族として数える。"""
    cells = []
    for (tf, es, side), b in book.items():
        meta = b["meta"]
        for group in ("all",) + tuple(ASSET_CLASSES):
            in_group = [group == "all" or CLASS_OF.get(m["ticker"]) == group for m in meta]
            for period in ("is", "fwd"):
                idx = [i for i, m in enumerate(meta)
                       if in_group[i] and (m["time"].tz_localize(None) < IS_UNTIL) == (period == "is")]
                if idx:
                    cells += _cells_for(tf, es, side, group, period, idx, b)
    _flag([c for c in cells if c["period"] == "is" and "p" in c and c["group"] == "all"], MIN_EFFECT_LAB, 0)
    _flag([c for c in cells if c["period"] == "is" and "p" in c and c["group"] in FLAG_CLASSES],
          CLASS_MIN_EFFECT, CLASS_MIN_N)
    for c in cells:
        if c["group"] not in ("all",) + FLAG_CLASSES:
            c["flag"] = False   # 暗号資産（1銘柄）は判定しない
    return cells


def _cells_for(tf, es, side, group, period, idx, b):
    """1つの入口×足×group×期間の72組ぶんのマス。idx＝その group・期間に入る入口の番号。"""
    meta = b["meta"]
    out = []
    g_all = _groups(meta, period == "fwd")
    base = b["R"][BASE]
    for k in COMBOS:
        R = b["R"][k]
        ii = [i for i in idx if R[i] is not None]
        cell = {"tf": tf, "entry": es, "side": side, "group": group, "sl": k[0], "tp": k[1], "period": period,
                "n_entries": len(idx), "n": len(ii)}
        if ii:
            s = X.summarize([R[i][0] for i in ii], [g_all[i] for i in ii], [R[i][1] for i in ii],
                            [R[i][2] for i in ii])
            cell.update({kk: s[kk] for kk in ("avg", "lo", "hi", "win", "p5", "worst", "beyond_1R", "bars_median")
                         if kk in s})
            # 1R の大きさ（ATR何本ぶんか）。1R が小さい組ほど R の値が大きく振れる（表示用・判定には使わない）
            cell["risk_atr_median"] = float(np.median([R[i][3] for i in ii]))
        if k != BASE:
            jj = [i for i in ii if base[i] is not None]
            d = X.diff([R[i][0] for i in jj], [base[i][0] for i in jj], [g_all[i] for i in jj])
            cell["vs_base"] = d
            cell["p"] = _p_value(d)
            if period == "is" and tf == "1d":
                for half, cond in (("early", lambda t: t < X.SPLIT), ("late", lambda t: t >= X.SPLIT)):
                    hh = [i for i in jj if cond(meta[i]["time"].tz_localize(None))]
                    cell[f"vs_base_{half}"] = X.diff([R[i][0] for i in hh], [base[i][0] for i in hh],
                                                     [g_all[i] for i in hh])
        out.append(cell)
    return out


def _flag(tests, min_effect, min_n):
    """ボンフェローニ法（その家族の IS の全マス・いまの方式との差）＋差 min_effect 以上＋件数 min_n 以上
    ＋日足は前後半で同じ向き。"""
    m = max(1, len(tests))
    for c in tests:
        c["bonf"] = c["p"] < ALPHA / m
        d = c["vs_base"]
        same_dir = True
        if c["tf"] == "1d":
            e_, l_ = c.get("vs_base_early", {}), c.get("vs_base_late", {})
            same_dir = ("avg" in e_ and "avg" in l_ and "avg" in d
                        and (e_["avg"] > 0) == (l_["avg"] > 0) == (d["avg"] > 0))
        c["flag"] = bool(c["bonf"] and abs(d.get("avg", 0)) >= min_effect and d.get("n", 0) >= min_n and same_dir)


SHOW_N_BELOW = 100   # 件数がこれ未満のマスは件数を添える（表示だけ・判定には使わない）


def _cellstr(c):
    if not c or "avg" not in c:
        return "—"
    mark = ""
    if c.get("flag"):
        mark = " ▲" if c["vs_base"]["avg"] > 0 else " ▼"
    small = f" (n={c['n']})" if c.get("n", 0) < SHOW_N_BELOW else ""
    return f"{c['avg']:+.2f}{mark}{small}"


def report_md(cells, fwd_results, asof):
    L = [f"# 出口の相性ラボ（基準日 {asof}）", "",
         "各マスは **1取引あたりの平均R（コスト後）**。R はその組の最初の損切り幅を 1 とした値。",
         "▲▼＝いまの方式（ATRの1.5倍／ATRの2倍）より良い／悪いと「目立つ」組（ボンフェローニ法10%・差0.15R以上・日足は前後半で同じ向き）。",
         "📏 物差し（2026-09-26 に幅の出し方を安全側へ切り替えた・オーナー決定）：癖のない値動き（作り物・足の中を細かく刻んだもの）で"
         "同じ手順を5回まわすと、全18銘柄の表で偶然「目立つ」が出たのは 0・1・0・0・0マス（平均0.2）。旧い幅の出し方では同じ作り物で平均1.2マス出ていた。"
         "⇒ 目立つ組が1マス程度なら、まだ偶然の可能性がある。",
         "📏 資産クラス別は、より厳しく「差0.25R以上・件数200以上」も足した（同じ作り物5回で 0マス）。",
         f"⚠️ 組み合わせが多い（8入口×{len(COMBOS)}組×2足）ので、目立つ組も**候補**にすぎない。前向き（2026-09-25以降）で確かめるまで結論にしない。",
         "⚠️ 売りの行は値段を上下反転して計算（+2σ↔−2σ、RSI70↔30、安値↔高値）。",
         "「—」＝その組は対象外（例: 25本線より下で出る買いは「25本線割れで損切り」が置けない／高値ブレイクの買いはもう真ん中の線より上）。",
         f"「(n=…)」＝その組で数えられた取引が{SHOW_N_BELOW}件未満＝ぶれが大きいので、平均Rの大きさを真に受けない。",
         "⚠️ マスどうしは対象の入口がそろっていない（組ごとに対象外が違う）。比べるときは json の vs_base（同じ入口どうしの差）を使う。"
         "1R が小さい組（損切りが近い組・json の risk_atr_median）ほど R の値は大きく振れる。", ""]
    idx = cell_index(cells)
    keys = sorted({(c["tf"], c["entry"], c["side"]) for c in cells}, key=lambda k: (k[0] != "1d", k[1], k[2]))
    for tf, es, side in keys:
        base = idx.get((tf, es, side, "all", *BASE, "is"), {})
        title = f"{'日足' if tf == '1d' else '4時間足'}｜{X.LABEL[es]}の{'買い' if side == 'long' else '売り'}"
        L += [f"## {title}（探索期間・入口 {base.get('n_entries', 0)}件・いまの方式 {_cellstr(base)}）", "",
              "| 損切り ＼ 利確 | " + " | ".join(TP_TYPES[t] for t in TP_TYPES) + " |",
              "|" + "---|" * (1 + len(TP_TYPES))]
        for s in SL_TYPES:
            L.append(f"| {SL_TYPES[s]} | " + " | ".join(_cellstr(idx.get((tf, es, side, "all", s, t, "is"))) for t in TP_TYPES) + " |")
        L.append("")
    L += ["## 資産クラス別（探索期間）", "",
          "各マス＝入口の件数／いまの方式の平均R。組ごとの数字は json の group（index / fx / commodity / crypto）にある。"
          "暗号資産は1銘柄なので「目立つ」の判定はしない（参考）。", "",
          "| 足・入口 | " + " | ".join(lab for lab, _g in ASSET_CLASSES.values()) + " |",
          "|" + "---|" * (1 + len(ASSET_CLASSES))]
    for tf, es, side in keys:
        row = []
        for g in ASSET_CLASSES:
            b = idx.get((tf, es, side, g, *BASE, "is"), {})
            row.append(f"{b.get('n_entries', 0)}件／{_cellstr(b)}" if b else "—")
        L.append(f"| {'日足' if tf == '1d' else '4時間足'}・{X.LABEL[es]}の{'買い' if side == 'long' else '売り'} | "
                 + " | ".join(row) + " |")
    L.append("")
    flagged = [c for c in cells if c.get("flag")]
    L += ["## 目立つ組（探索期間・候補）", "",
          "「全体」＝全18銘柄の家族、各資産クラス＝資産クラス別の家族（それぞれ別にボンフェローニ法で数える）。", ""]
    if flagged:
        L += ["| 足 | 入口 | 対象 | 損切り | 利確 | 件数 | 平均R | いまの方式との差 [95%] |", "|---|---|---|---|---|---|---|---|"]
        for c in sorted(flagged, key=lambda c: (c["group"] != "all", -c["vs_base"]["avg"])):
            d = c["vs_base"]
            L.append(f"| {c['tf']} | {X.LABEL[c['entry']]}（{'買い' if c['side'] == 'long' else '売り'}） | {group_label(c['group'])} | "
                     f"{SL_TYPES[c['sl']]} | {TP_TYPES[c['tp']]} | {c['n']} | {c['avg']:+.3f} | "
                     f"{d['avg']:+.3f} [{d['lo']:+.3f}〜{d['hi']:+.3f}] |")
    else:
        L.append("なし")
    L += ["", "## 目立つ組の前向き（2026-09-25以降に出たシグナルだけ）", ""]
    if flagged:
        L += ["| 足 | 入口 | 対象 | 損切り | 利確 | 探索での差 | 前向きの件数（必要100） | 前向きの差 [95%] | 状態 |",
              "|---|---|---|---|---|---|---|---|---|"]
        for c in sorted(flagged, key=lambda c: (c["group"] != "all", c["tf"], c["entry"], c["sl"], c["tp"])):
            f = fwd_check(c, idx)
            d = f.get("vs_base") or {}
            rng = f"{d['avg']:+.3f} [{d['lo']:+.3f}〜{d['hi']:+.3f}]" if "avg" in d else "—"
            L.append(f"| {c['tf']} | {X.LABEL[c['entry']]}（{'買い' if c['side'] == 'long' else '売り'}） | {group_label(c['group'])} | "
                     f"{SL_TYPES[c['sl']]} | {TP_TYPES[c['tp']]} | {c['vs_base']['avg']:+.3f} | {d.get('n', 0)} | "
                     f"{rng} | {f['state']} |")
    else:
        L.append("なし")
    L += ["", X.report_forward(fwd_results, asof) if fwd_results else "", ""]
    return "\n".join(L)


def cell_index(cells):
    return {(c["tf"], c["entry"], c["side"], c["group"], c["sl"], c["tp"], c["period"]): c for c in cells}


def group_label(g):
    return "全体" if g == "all" else ASSET_CLASSES[g][0]


FWD_MIN_N = 100
FWD_MIN_EFFECT = 0.10


def fwd_check(c, idx):
    """探索で目立ったマスの前向き（事前登録どおり: 件数100以上・95%幅が0をまたがず同じ向き・差0.10R以上）。"""
    f = idx.get((c["tf"], c["entry"], c["side"], c["group"], c["sl"], c["tp"], "fwd"), {})
    d = f.get("vs_base") or {}
    n = d.get("n", 0)
    if n < FWD_MIN_N or "avg" not in d:
        state = "🟡蓄積中"
    else:
        up = c["vs_base"]["avg"] > 0
        same = (d["lo"] > 0) if up else (d["hi"] < 0)
        opposite = (d["hi"] < 0) if up else (d["lo"] > 0)
        if same and abs(d["avg"]) >= FWD_MIN_EFFECT:
            state = "🟢前向きでも同じ向き"
        elif opposite:
            state = "⛔前向きでは逆向き"
        else:
            state = "⚪まだ判断できない"
    return {"vs_base": d, "state": state}


def _rounded(x):
    """JSON を小さくする（毎週コミットするので）。小数は4桁。"""
    if isinstance(x, float):
        return round(x, 4) if math.isfinite(x) else None
    if isinstance(x, dict):
        return {k: _rounded(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_rounded(v) for v in x]
    return x


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="exit-lab.json")
    ap.add_argument("--md", default="exit-lab.md")
    ap.add_argument("--tf", default="1d,4h")
    ap.add_argument("--legacy-se", action="store_true",
                    help="旧い幅（2026-09-26 まで）で出す＝比べるとき専用。公開用の exit-lab.json/.md は上書きしない")
    args = ap.parse_args()
    if args.legacy_se:
        if args.json == "exit-lab.json" or args.md == "exit-lab.md":
            print("--legacy-se は公開用の exit-lab.json/.md を上書きしない＝別の --json/--md を指定する", file=sys.stderr)
            sys.exit(2)
        X._mean_se = X._mean_se_legacy   # X.diff / X._mean_ci / X.diff2 が中で呼ぶ関数を差し替える
    frames, missing = {}, []
    for tf in args.tf.split(","):
        for t in sorted(LEGACY_UNIVERSE):
            df = X.fetch(t, tf)
            if df is None:
                missing.append(f"{t}({tf})")
            else:
                frames[(t, tf)] = df
    if not frames:
        print("価格が1つも取れなかった＝何も書かない", file=sys.stderr)
        sys.exit(1)
    cells = evaluate_lab(run_lab(frames))
    fwd = X.evaluate_forward(frames)
    asof = pd.Timestamp.now(tz="Asia/Tokyo").strftime("%Y-%m-%d")
    idx = cell_index(cells)
    flagged_fwd = [{"tf": c["tf"], "entry": c["entry"], "side": c["side"], "group": c["group"], "sl": c["sl"],
                    "tp": c["tp"], "is_vs_base": c["vs_base"], **fwd_check(c, idx)} for c in cells if c.get("flag")]
    classes = {k: {"label": lab, "tickers": sorted(t for t, g in CLASS_OF.items() if g == k), "flag": k in FLAG_CLASSES}
               for k, (lab, _g) in ASSET_CLASSES.items()}
    out = {"asof": asof, "is_until": str(IS_UNTIL.date()), "missing": missing,
           "sl_types": SL_TYPES, "tp_types": TP_TYPES, "base": list(BASE), "max_hold": MAX_HOLD,
           "asset_classes": classes,
           "cells": cells, "flagged_forward": flagged_fwd, "forward_hypotheses": fwd}
    with open(args.json, "w", encoding="utf-8") as f:
        json.dump(_rounded(out), f, ensure_ascii=False, indent=0, default=str)
    with open(args.md, "w", encoding="utf-8") as f:
        f.write(report_md(cells, fwd, asof))
    print(f"書いた: {args.json}（{len(cells)}マス）／{args.md}／取得できなかった: {', '.join(missing) or 'なし'}")


if __name__ == "__main__":
    main()
