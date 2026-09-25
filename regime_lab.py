# -*- coding: utf-8 -*-
"""
regime_lab.py — テクニカル指標が「効く環境・効かない環境」の検証（環境の相性ラボ）。

2026-09-25 オーナー指示「テクニカル指標は常に効くわけではないのはもうわかっている。効きやすい環境と
効きにくい環境があるはず。どういう時に効くのか・効かないのかを徹底的にリサーチして検証して」。

【事前登録（2026-09-25・本物のデータの結果を見る前に、この説明文ごとコミットして固定する）】
対象   : 監視18銘柄（signal_lab_tracker.LEGACY_UNIVERSE）。Yahoo・auto_adjust=True（exit_rule_backtest.fetch）。
足     : 日足＝2006-01-01〜実行日（主）／4時間足＝直近730日の1時間足を resample（副＝最近2年でも同じ向きかの確認）。
入口   : exit_rule_backtest.PAIRS の8つ（X.signals＝エンジン detect_signals と同じ式）。クールダウン3本。
         環境の物差しに過去252本・200本線が要るので、先頭 WARMUP=260 本は使わない。
族     : 順張り＝高値ブレイク買い・安値割れ売り・MACDゴールデン買い・MACDデッド売り・25/75本線ゴールデン買い・デッド売り
         逆張り＝RSI売られすぎ反発の買い・−2σタッチの買い
         ⚠️ エンジンは逆張りの「売り」を使わない＝逆張りは買いだけ。株価指数などの長期の上昇が混ざる点に注意。
成績   : 主＝いまの方式（損切り1.5ATR／利確2.0ATR／期限 日足21本・4時間足42本／同じ足で両方なら損切り／
         損切りは窓なら始値）の1取引あたりR（コスト後。コストは signal_lab_sweep.cost_r_of＝往復スプレッド×1.5）。
         1R＝入った足の ATR14×1.5。データの最後まで決着しない取引は数えない。
         副＝10本後の終値までの動き（向きをそろえ、入った足の ATR 単位・コスト前）＝出口の置き方に左右されない
         「向きが当たったか」の物差し。
環境（すべて入る足の終値までに分かる値だけ＝後知恵なし）:
  E1 vol   値動きの大きさ: ATR14÷終値 の、その銘柄の直近252本（その足を含む）の中での順位（0〜1）。
           低＜1/3・中・高≥2/3。
  E2 adx   トレンドの強さ: ADX14（generate_technical_alerts.adx_choppiness＝エンジンと同じ式）。弱＜20・中20〜25・強≥25。
  E3 er    値動きの素直さ: 効率比 ER20＝|終値の20本の変化| ÷ 20本の1本ごとの変化の絶対値の合計。
           その銘柄の直近252本の中での順位で 低＜1/3・中・高≥2/3。
  E4 ma200 長期トレンドと同じ向きか: 終値が200本線より上で買う／下で売る＝順行、それ以外＝逆行。
  E5 vix   市場の怖さ: VIX の終値（後知恵を避けるため、その足の日付より前の最後の終値＝前日の値）。
           低＜15・中15〜25・高≥25。
  E6 volchg 値動きが広がり中か縮み中か: ATR14 ÷ 直前60本（その足を含まない）の ATR14 の平均。
           縮み＜0.9・普通・広がり＞1.1。
  E7 recent そのシグナルが最近効いていたか: 同じ入口×同じ資産クラス×同じ足で、この足より前に決着した直近30件の
           いまの方式の平均R（コスト後）が ＞0＝効いていた／≤0＝効いていなかった。30件に満たない間は対象外。
比べ方（主）: 日足。族（2）×環境（7）＝14の比較。E1・E2・E3・E5・E6 は「高（強・広がり）−低（弱・縮み）」、
           E4 は「順行−逆行」、E7 は「効いていた−効いていなかった」の、平均R（コスト後）の差。
           別々の集まりの差（exit_rule_backtest.diff2）＝銘柄×年の二方向クラスタ・t補正。p値は exit_lab と同じ
           （95%幅から正規近似で出す＝幅に t 補正が入っているぶん保守側）。
「差がある」と言う条件（主・日足）: ①p値 < ボンフェローニ法（10%÷14） ②差の大きさ 0.10R 以上
           ③前半（〜2015）と後半（2016〜）で差の向きがそろう。の3つ全部。
           参考として並べる（判定には使わない）: 4時間足（直近2年）で同じ向きか／資産クラス（株価指数・FX・
           コモディティ）ごとの向き／10本後の動き（副）でも同じ向きか／コスト前でも同じ向きか。
           「差がある」のうち、4時間足・10本後・コスト前の3つとも同じ向きのものを「頑健」と書く。
コストだけの差の見分け: コスト後だけ差があり、コスト前では差の向きが逆か 0.03R 未満なら「指標の効き目ではなくコストの差」。
探索（副）: 入口8つ×環境7 を日足・4時間足それぞれ（56マスずつ。ボンフェローニ法の分母もそれぞれ56）。
           条件は主と同じ（4時間足は③の代わりに条件なし）。探索で出たものは**候補**であって結論ではない。
           2つの環境の組み合わせ（ADX×値動きの大きさ など）は表を出すだけで判定しない。
前向きの確認（--live）: signals-log.json（エンジンが実際に出したシグナル・2026-05-20〜・1h/4h/1d）で、
           同じ8つの入口と同じ向きのシグナルだけを使い、記録済みの環境で同じ差を見る。
           E2＝indicators_at_signal.adx、E5＝environment.vix.current、E6＝environment.atr_regime.ratio（30日平均との比）、
           E7＝ログ自身から（同じ入口×同じ資産クラスで、そのシグナルより前に決着した直近30件）。
           R＝signal_lab_sweep.r_used(net=True, itt=True)。幅＝銘柄×週の二方向クラスタ。件数が少ないので参考。
較正（本物のデータを見る前・--synthetic）: 上下の偏りがゼロで、値動きの大きさだけがゆっくり変わる作り物の値動き
           （18銘柄×日足20年・資産クラス内で連動・作り物の VIX）で同じ手順を回し、主の14比較・探索の各マスで
           「差がある」が出る数を数える。結果はこの下に追記する（基準は動かさない）。
  較正の結果（2026-09-25・本物のデータ・前向きのデータを1件も見る前）:
           作り物42回（乱数 1〜12・100〜129）で、主の14比較に誤って「差がある」が出たのは計4回＝1回あたり0.095
           （設計の「全体で10%」どおり）。出たのは 逆張り×効率比 が2回（乱数10・12）、ほか2回。
           p値の分布: 名目5%を下回る割合は6.4%（420比較）とほぼ名目どおりだが、裾は少し重い
           （ボンフェローニの線 0.0071 を下回る割合は1.7%＝名目の約2.3倍）。それを差0.10R以上・前後半の向きの条件が抑えている。
           探索（日足56マス）の誤検出は1回あたり0.27マス（30回）、4時間足（56マス）は12回で0マス。
           ⇒ 基準は事前登録どおり。**探索の日足で目立つマスが1つ以下なら、偶然でも出る範囲**と読む。
           作り物の族ごとの平均（コスト後）: 順張り −0.00〜+0.01R／逆張り −0.03R 前後（逆張りは損切りまでが近い入り方ではないが、
           コストの分だけ少し負ける）＝計算そのものに偏りは無い。
限界（先に書く）: 先物のつなぎ目で値段が飛ぶ／逆張りは買いだけ／VIX は米国株の怖さの物差し（FX・コモディティには
           間接的）／同じ銘柄の取引は重なる（クラスタで扱う）／E1〜E3・E6 は互いに似た物を測る（同じ現象を別の
           物差しで数回数えることになる）／重要指標の発表日やセンチメントは過去20年分のデータが無いので扱えない
           （前向きの確認でだけ環境警戒スコアを参考に見る）。
公開   : しない（オーナー個人向けの研究。結果の読み方は「検証結果」であって売買の推奨ではない）。

使い方（Yahoo に届く所で）: python regime_lab.py --json regime-lab.json --md regime-lab.md
       較正（どこでも）      : python regime_lab.py --synthetic 1,2,3,4,5,6
       前向きの確認（どこでも）: python regime_lab.py --live signals-log.json --live-only --json regime-lab-live.json
"""
import argparse
import bisect
import json
import math
import sys
from collections import defaultdict

import numpy as np
import pandas as pd

import exit_rule_backtest as X
from generate_technical_alerts import adx_choppiness, calc_atr
from signal_lab_sweep import cost_r_of, r_used
from signal_lab_tracker import LEGACY_UNIVERSE
from signal_lab_verify import GROUPS

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WARMUP = 260
COOLDOWN = X.COOLDOWN
EXPIRY = X.EXPIRY
SL_ATR, TP_ATR = 1.5, 2.0
H_BARS = 10
SPLIT = pd.Timestamp("2016-01-01")
ALPHA = 0.10
MIN_EFFECT = 0.10
RECENT_N = 30
COST_ONLY_EPS = 0.03

ENTRIES = [(es, side) for _g, es, side, _x in X.PAIRS]
FAMILY = {("rsi_oversold_bounce", "long"): "mr", ("bb_lower_touch", "long"): "mr"}
for _e in ENTRIES:
    FAMILY.setdefault(_e, "tf")
FAMILY_LABEL = {"tf": "順張り", "mr": "逆張り"}
ENTRY_LABEL = {"rsi_oversold_bounce": "RSI売られすぎ反発", "bb_lower_touch": "−2σタッチ", "high_break": "高値ブレイク",
               "low_break": "安値割れ", "macd_golden": "MACDゴールデン", "macd_dead": "MACDデッド",
               "ma_golden": "25/75本線ゴールデン", "ma_dead": "25/75本線デッド"}
SIDE_LABEL = {"long": "買い", "short": "売り"}

# 環境: (キー, 名前, 分け方の名前, 比べる2つ(高い側, 低い側), 表示順)
REGIMES = {
    "vol": ("値動きの大きさ", ("低", "中", "高"), ("高", "低")),
    "adx": ("トレンドの強さ(ADX)", ("弱", "中", "強"), ("強", "弱")),
    "er": ("値動きの素直さ(効率比)", ("低", "中", "高"), ("高", "低")),
    "ma200": ("200本線と同じ向きか", ("逆行", "順行"), ("順行", "逆行")),
    "vix": ("市場の怖さ(VIX)", ("低", "中", "高"), ("高", "低")),
    "volchg": ("値動きの広がり", ("縮み", "普通", "広がり"), ("広がり", "縮み")),
    "recent": ("最近効いていたか", ("効いていない", "効いていた"), ("効いていた", "効いていない")),
}

ASSET_CLASSES = {"index": ("株価指数", ("index",)), "fx": ("FX", ("jpy_fx", "other_fx")),
                 "commodity": ("コモディティ", ("metal", "oil")), "crypto": ("暗号資産", ("btc",))}
CLASS_OF = {t: k for k, (_l, gs) in ASSET_CLASSES.items() for g in gs for t in GROUPS[g]}


# ───────────────────────── 環境の物差し ─────────────────────────
def _tercile(x):
    if x is None or not np.isfinite(x):
        return None
    return "低" if x < 1 / 3 else ("高" if x >= 2 / 3 else "中")


def features(df, vix_prev):
    """足ごとの環境の値（すべてその足の終値までに分かる値）。vix_prev は足の index に合わせた前日の VIX。"""
    h, l, c = df["High"], df["Low"], df["Close"]
    atr = calc_atr(h, l, c)
    adx, _chop = adx_choppiness(h, l, c)
    volp = (atr / c).rolling(252).rank(pct=True)
    er = (c - c.shift(20)).abs() / c.diff().abs().rolling(20).sum()
    erp = er.rolling(252).rank(pct=True)
    ma200 = c.rolling(200).mean()
    volchg = atr / atr.shift(1).rolling(60).mean()
    return pd.DataFrame({"atr": atr, "adx": adx, "volp": volp, "erp": erp, "ma200": ma200,
                         "volchg": volchg, "vix": vix_prev}, index=df.index)


def buckets(f, i, close, side):
    """その足の環境の区分。値が無ければ None。"""
    def g(k):
        v = f[k][i]
        return v if np.isfinite(v) else None
    adx, vix, vc, ma = g("adx"), g("vix"), g("volchg"), g("ma200")
    return {
        "vol": _tercile(g("volp")),
        "adx": None if adx is None else ("弱" if adx < 20 else ("強" if adx >= 25 else "中")),
        "er": _tercile(g("erp")),
        "ma200": None if ma is None else ("順行" if (close > ma) == (side == "long") else "逆行"),
        "vix": None if vix is None else ("低" if vix < 15 else ("高" if vix >= 25 else "中")),
        "volchg": None if vc is None else ("縮み" if vc < 0.9 else ("広がり" if vc > 1.1 else "普通")),
    }


def align_vix(vix, index):
    """その足の日付より前の、最後の VIX 終値（前日の値）。"""
    if vix is None or len(vix) == 0:
        return pd.Series(np.nan, index=index)
    v = vix.copy()
    v.index = pd.to_datetime(v.index).tz_localize(None).normalize()
    v = v[~v.index.duplicated()].sort_index()
    idx = pd.to_datetime(index)
    idx = idx.tz_convert(None) if idx.tz is not None else idx
    days = idx.normalize() - pd.Timedelta(days=1)
    return pd.Series(v.reindex(days, method="ffill").to_numpy(float), index=index)


# ───────────────────────── 取引 ─────────────────────────
def outcome_A(o, h, l, c, i, side, atr_i, tf):
    """いまの方式。戻り値＝(R コスト前, 決着した足)。決着しなければ (None, None)。exit_rule_backtest の A と同じ。"""
    d = 1 if side == "long" else -1
    e, risk = c[i], SL_ATR * atr_i
    sl, tp = e - d * risk, e + d * TP_ATR * atr_i
    n = len(c)
    for j in range(i + 1, min(n, i + EXPIRY[tf] + 1)):
        f = X._sl_fill(side, sl, o[j], h[j], l[j])
        if f is not None:
            return d * (f - e) / risk, j
        if (side == "long" and h[j] >= tp) or (side == "short" and l[j] <= tp):
            return TP_ATR / SL_ATR, j
        if j == i + EXPIRY[tf]:
            return d * (c[j] - e) / risk, j
    return None, None


def lab_trades(df, ticker, tf, vix_prev):
    sig = X.signals(df)
    f = features(df, vix_prev)
    F = {k: f[k].to_numpy(float) for k in f.columns}
    o, h, l, c = (df[k].to_numpy(float) for k in ("Open", "High", "Low", "Close"))
    times = pd.to_datetime(df.index)
    times = times.tz_convert(None) if times.tz is not None else times
    n, out = len(c), []
    for es, side in ENTRIES:
        ent = sig[es].to_numpy(bool)
        d = 1 if side == "long" else -1
        last = -10 ** 9
        for i in range(WARMUP, n - 1):
            if not ent[i] or i - last <= COOLDOWN or not (F["atr"][i] > 0):
                continue
            last = i
            A, j = outcome_A(o, h, l, c, i, side, F["atr"][i], tf)
            if A is None:
                continue
            cost = cost_r_of({"entry": c[i], "stop_loss": c[i] - d * SL_ATR * F["atr"][i], "ticker": ticker})
            h10 = d * (c[i + H_BARS] - c[i]) / F["atr"][i] if i + H_BARS < n else None
            out.append({"ticker": ticker, "cls": CLASS_OF.get(ticker, "?"), "tf": tf, "es": es, "side": side,
                        "fam": FAMILY[(es, side)], "time": times[i], "exit_time": times[j],
                        "gross": A, "cost": cost, "net": A - cost, "h10": h10, "b": buckets(F, i, c[i], side)})
    return out


def add_recent(ts):
    """E7: 同じ入口×同じ資産クラス×同じ足で、この足より前に決着した直近30件の平均R（コスト後）。"""
    by = defaultdict(list)
    for t in ts:
        by[(t["tf"], t["es"], t["side"], t["cls"])].append(t)
    for grp in by.values():
        ex = sorted(grp, key=lambda t: t["exit_time"])
        et = [t["exit_time"] for t in ex]
        cs = np.concatenate([[0.0], np.cumsum([t["net"] for t in ex])])
        for t in grp:
            k = bisect.bisect_left(et, t["time"])
            t["b"]["recent"] = None if k < RECENT_N else (
                "効いていた" if (cs[k] - cs[k - RECENT_N]) / RECENT_N > 0 else "効いていない")


# ───────────────────────── 集計 ─────────────────────────
def cluster(t):
    ts = t["time"]
    if t["tf"] == "1d":
        return (t["ticker"], ts.year)
    if t["tf"] == "live":
        iso = ts.isocalendar()
        return (t["ticker"], (iso[0], iso[1]))
    return (t["ticker"], (ts.year, (ts.month - 1) // 3))


def p_value(dd):
    """95%幅から正規近似の両側 p値（exit_lab._p_value と同じ）。"""
    if not dd or dd.get("n", 0) < 2 or "lo" not in dd or not math.isfinite(dd["lo"]) or dd["hi"] == dd["lo"]:
        return 1.0
    se = (dd["hi"] - dd["lo"]) / (2 * 1.96)
    return math.erfc(abs(dd["avg"]) / se / math.sqrt(2)) if se > 0 else 1.0


def contrast(ts, key, field="net"):
    hi, lo = REGIMES[key][2]
    a = [t for t in ts if t["b"].get(key) == hi and t.get(field) is not None]
    b = [t for t in ts if t["b"].get(key) == lo and t.get(field) is not None]
    dd = X.diff2([t[field] for t in a], [cluster(t) for t in a], [t[field] for t in b], [cluster(t) for t in b])
    dd["n_hi"], dd["n_lo"] = len(a), len(b)
    dd["p"] = p_value(dd)
    return dd


def bucket_table(ts, key):
    rows = []
    for name in REGIMES[key][1]:
        sel = [t for t in ts if t["b"].get(key) == name]
        s = X.summarize([t["net"] for t in sel], [cluster(t) for t in sel]) if sel else {"n": 0}
        if sel:
            s["gross"] = float(np.mean([t["gross"] for t in sel]))
            hv = [t["h10"] for t in sel if t["h10"] is not None]
            s["h10"] = float(np.mean(hv)) if hv else None
        rows.append({"bucket": name, **{k: v for k, v in s.items() if k in ("n", "win", "avg", "lo", "hi", "gross", "h10")}})
    return rows


def _sign(dd):
    return None if not dd or "avg" not in dd else (1 if dd["avg"] > 0 else -1)


def evaluate(ts1d, ts4h, live=None):
    """主（族×環境・日足）と探索（入口×環境・日足/4h）。"""
    fam = lambda ts, F: [t for t in ts if t["fam"] == F]
    primary = []
    for F in ("tf", "mr"):
        for key in REGIMES:
            base = fam(ts1d, F)
            dd = contrast(base, key)
            row = {"fam": F, "key": key, "diff": dd,
                   "early": contrast([t for t in base if t["time"] < SPLIT], key),
                   "late": contrast([t for t in base if t["time"] >= SPLIT], key),
                   "gross": contrast(base, key, "gross"), "h10": contrast(base, key, "h10"),
                   "h4": contrast(fam(ts4h, F), key) if ts4h else {},
                   "classes": {k: contrast([t for t in base if t["cls"] == k], key) for k in ("index", "fx", "commodity")},
                   "table": bucket_table(base, key),
                   "table4h": bucket_table(fam(ts4h, F), key) if ts4h else []}
            if live is not None:
                row["live"] = contrast(fam(live, F), key) if any(t["b"].get(key) for t in live) else {}
                row["live_table"] = bucket_table(fam(live, F), key)
            primary.append(row)
    m = len(primary)
    for r in primary:
        d = r["diff"]
        r["bonf"] = d.get("p", 1.0) < ALPHA / m
        same = _sign(r["early"]) is not None and _sign(r["early"]) == _sign(r["late"]) == _sign(d)
        r["flag"] = bool(r["bonf"] and abs(d.get("avg", 0)) >= MIN_EFFECT and same)
        s0 = _sign(d)
        r["robust"] = bool(r["flag"] and _sign(r["h4"]) == s0 and _sign(r["h10"]) == s0 and _sign(r["gross"]) == s0)
        g = r["gross"]
        r["cost_only"] = bool(r["flag"] and (_sign(g) != s0 or abs(g.get("avg", 0)) < COST_ONLY_EPS))
    explore = []
    for tf, ts in (("1d", ts1d), ("4h", ts4h)):
        if not ts:
            continue
        cells = []
        for es, side in ENTRIES:
            sub = [t for t in ts if t["es"] == es and t["side"] == side]
            for key in REGIMES:
                c = {"tf": tf, "es": es, "side": side, "key": key, "diff": contrast(sub, key)}
                if tf == "1d":
                    c["early"] = contrast([t for t in sub if t["time"] < SPLIT], key)
                    c["late"] = contrast([t for t in sub if t["time"] >= SPLIT], key)
                cells.append(c)
        mm = len(cells)
        for c in cells:
            d = c["diff"]
            same = True if tf != "1d" else (_sign(c["early"]) is not None and _sign(c["early"]) == _sign(c["late"]) == _sign(d))
            c["flag"] = bool(d.get("p", 1.0) < ALPHA / mm and abs(d.get("avg", 0)) >= MIN_EFFECT and same)
        explore += cells
    # 組み合わせ（判定しない）: 族ごとに ADX × 値動きの大きさ、ADX × 200本線
    combos = {}
    for F in ("tf", "mr"):
        base = fam(ts1d, F)
        for k1, k2 in (("adx", "vol"), ("adx", "ma200"), ("vix", "ma200")):
            tab = {}
            for b1 in REGIMES[k1][1]:
                for b2 in REGIMES[k2][1]:
                    sel = [t["net"] for t in base if t["b"].get(k1) == b1 and t["b"].get(k2) == b2]
                    tab[f"{b1}|{b2}"] = {"n": len(sel), "avg": float(np.mean(sel)) if sel else None}
            combos[f"{F}|{k1}×{k2}"] = tab
    baseline = {}
    for tf, ts in (("1d", ts1d), ("4h", ts4h)):
        for F in ("tf", "mr"):
            sel = fam(ts, F)
            if sel:
                baseline[f"{tf}|{F}"] = X.summarize([t["net"] for t in sel], [cluster(t) for t in sel])
    return {"primary": primary, "explore": explore, "combos": combos, "baseline": baseline}


# ───────────────────────── 前向き（signals-log） ─────────────────────────
DIR_OF = {"ロング（買い）": "long", "ショート（売り）": "short"}


def live_trades(path):
    d = json.load(open(path, encoding="utf-8"))
    ents = set(ENTRIES)
    out = []
    for r in d:
        side = DIR_OF.get(r.get("direction"))
        es = r.get("primary_signal")
        if (es, side) not in ents or r.get("ticker") not in LEGACY_UNIVERSE:
            continue
        R = r_used(r, net=True, itt=True)
        if R is None:
            continue
        ind = r.get("indicators_at_signal") or {}
        env = r.get("environment") or {}
        adx = ind.get("adx")
        vix = (env.get("vix") or {}).get("current")
        ratio = (env.get("atr_regime") or {}).get("ratio")
        t = pd.Timestamp(r["fired_at"]).tz_convert(None)
        res = r.get("outcome_resolved_at")
        b = {"adx": None if adx is None else ("弱" if adx < 20 else ("強" if adx >= 25 else "中")),
             "vix": None if vix is None else ("低" if vix < 15 else ("高" if vix >= 25 else "中")),
             "volchg": None if ratio is None else ("縮み" if ratio < 0.9 else ("広がり" if ratio > 1.1 else "普通"))}
        out.append({"ticker": r["ticker"], "cls": CLASS_OF.get(r["ticker"], "?"), "tf": "live", "es": es, "side": side,
                    "fam": FAMILY[(es, side)], "time": t,
                    "exit_time": pd.Timestamp(res).tz_convert(None) if res else t,
                    "gross": R + cost_r_of(r), "cost": cost_r_of(r), "net": R, "h10": None, "b": b,
                    "src_tf": r.get("timeframe")})
    add_recent(out)
    return out


# ───────────────────────── 作り物の値動き（較正） ─────────────────────────
SYN = {  # 価格の水準・1日の値動き（標準偏差）
    "GC=F": (1800, .010), "SI=F": (25, .018), "CL=F": (70, .022), "NKD=F": (30000, .013), "ES=F": (4000, .011),
    "NQ=F": (14000, .014), "YM=F": (35000, .010), "^FTSE": (7000, .010), "BTC-USD": (30000, .035),
    "USDJPY=X": (130, .006), "EURJPY=X": (140, .0065), "GBPJPY=X": (170, .007), "AUDJPY=X": (90, .008),
    "EURUSD=X": (1.15, .0055), "GBPUSD=X": (1.3, .006), "AUDUSD=X": (0.75, .007), "EURAUD=X": (1.55, .006),
    "GBPAUD=X": (1.8, .0065),
}


def synthetic(seed, tf="1d"):
    """上下の偏りゼロ・値動きの大きさが資産クラスごとにゆっくり変わる（対数ボラの AR(1)）・クラス内で連動する作り物。"""
    rng = np.random.default_rng(seed)
    if tf == "1d":
        idx = pd.bdate_range("2006-01-02", "2026-09-24")
        scale = 1.0
    else:
        idx = pd.date_range("2024-09-25", "2026-09-24", freq="4h")
        scale = 1 / math.sqrt(6)
    n = len(idx)
    cls_h, cls_f = {}, {}
    for k in ASSET_CLASSES:
        hv = np.zeros(n)
        e = rng.standard_normal(n)
        for i in range(1, n):
            hv[i] = 0.985 * hv[i - 1] + 0.12 * e[i]
        cls_h[k] = hv
        cls_f[k] = rng.standard_t(5, n) / math.sqrt(5 / 3)
    frames = {}
    for tk, (p0, s) in SYN.items():
        k = CLASS_OF[tk]
        hid = np.zeros(n)
        e = rng.standard_normal(n)
        for i in range(1, n):
            hid[i] = 0.97 * hid[i - 1] + 0.06 * e[i]
        sig = s * scale * np.exp(cls_h[k] + hid - 0.5 * (0.12 ** 2 / (1 - 0.985 ** 2) + 0.06 ** 2 / (1 - 0.97 ** 2)))
        rho = 0.6 if k == "index" else 0.3
        z = math.sqrt(rho) * cls_f[k] + math.sqrt(1 - rho) * rng.standard_t(5, n) / math.sqrt(5 / 3)
        steps = 8
        sub = rng.standard_normal((n, steps)) / math.sqrt(steps)
        sub = sub - sub.mean(axis=1, keepdims=True) + (z / steps)[:, None]   # 足全体の動き＝z
        gap = 0.15 * rng.standard_normal(n)
        C = np.empty(n)
        O, H, L = np.empty(n), np.empty(n), np.empty(n)
        prev = p0
        for i in range(n):
            o = prev * (1 + gap[i] * sig[i])
            path = o * (1 + np.cumsum(sub[i]) * sig[i] * math.sqrt(max(1e-9, 1 - 0.15 ** 2)))
            O[i], C[i] = o, path[-1]
            H[i], L[i] = max(o, path.max()), min(o, path.min())
            prev = C[i]
        frames[tk] = pd.DataFrame({"Open": O, "High": H, "Low": L, "Close": C, "Volume": 0.0}, index=idx)
    vix = pd.Series(100 * math.sqrt(252) * np.mean([SYN[t][1] for t in GROUPS["index"]]) * np.exp(cls_h["index"])
                    * np.exp(0.1 * rng.standard_normal(n)), index=idx)
    if tf != "1d":
        vix = vix.resample("1D").last().dropna()
    return frames, vix


# ───────────────────────── 実行 ─────────────────────────
def build(frames_1d, frames_4h, vix):
    ts1d, ts4h = [], []
    for tk, df in frames_1d.items():
        ts1d += lab_trades(df, tk, "1d", align_vix(vix, df.index))
    for tk, df in frames_4h.items():
        ts4h += lab_trades(df, tk, "4h", align_vix(vix, df.index))
    add_recent(ts1d)
    add_recent(ts4h)
    return ts1d, ts4h


def fmt(dd, nd=2):
    if not dd or "avg" not in dd:
        return "—"
    return f"{dd['avg']:+.{nd}f}R [{dd['lo']:+.{nd}f}, {dd['hi']:+.{nd}f}]"


def report_md(res, asof, n1, n4, nlive=None):
    L = [f"# 環境の相性ラボ（asof {asof}）", "",
         f"日足の取引 {n1:,} 件・4時間足 {n4:,} 件" + (f"・前向き（signals-log）{nlive:,} 件" if nlive else ""), "",
         "## 基準（族ごとの平均・コスト後）", ""]
    for k, s in res["baseline"].items():
        L.append(f"- {k}: n={s['n']:,} 平均 {s['avg']:+.3f}R [{s['lo']:+.3f}, {s['hi']:+.3f}] 勝率 {s['win']:.1%}")
    L += ["", "## 主の比較（日足・族×環境・差＝高い側−低い側）", "",
          "| 族 | 環境 | 比べる2つ | 差（日足） | p | 前半 | 後半 | 4時間足 | 10本後 | コスト前 | 判定 |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in res["primary"]:
        name, _b, (hi, lo) = REGIMES[r["key"]]
        v = "✅差がある" + ("（頑健）" if r["robust"] else "") + ("※コストの差" if r["cost_only"] else "") if r["flag"] else "—"
        L.append(f"| {FAMILY_LABEL[r['fam']]} | {name} | {hi}−{lo} | {fmt(r['diff'])} | {r['diff'].get('p', 1):.4f} | "
                 f"{fmt(r['early'])} | {fmt(r['late'])} | {fmt(r['h4'])} | {fmt(r['h10'])} | {fmt(r['gross'])} | {v} |")
    L += ["", "## 区分ごとの平均（日足・コスト後）", ""]
    for r in res["primary"]:
        name = REGIMES[r["key"]][0]
        cells = " / ".join(f"{b['bucket']} {b['avg']:+.3f}R(n={b['n']:,})" if b.get("n") else f"{b['bucket']} —"
                           for b in r["table"])
        L.append(f"- {FAMILY_LABEL[r['fam']]}×{name}: {cells}")
    L += ["", "## 探索で目立ったマス（候補・結論ではない）", ""]
    fl = [c for c in res["explore"] if c["flag"]]
    for c in fl:
        L.append(f"- {c['tf']} {ENTRY_LABEL[c['es']]}({SIDE_LABEL[c['side']]})×{REGIMES[c['key']][0]}: {fmt(c['diff'])}")
    if not fl:
        L.append("- なし")
    return "\n".join(L)


def count_flags(res):
    return {"primary": sum(r["flag"] for r in res["primary"]),
            "explore_1d": sum(c["flag"] for c in res["explore"] if c["tf"] == "1d"),
            "explore_4h": sum(c["flag"] for c in res["explore"] if c["tf"] == "4h")}


def _jsonable(o):
    if isinstance(o, dict):
        return {k: _jsonable(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_jsonable(v) for v in o]
    if isinstance(o, (np.floating, float)):
        return None if not math.isfinite(float(o)) else round(float(o), 4)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return o


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json")
    ap.add_argument("--md")
    ap.add_argument("--synthetic", help="較正: 乱数の種をカンマ区切りで")
    ap.add_argument("--live", help="前向きの確認: signals-log.json のパス")
    ap.add_argument("--no-4h", action="store_true")
    ap.add_argument("--live-only", action="store_true", help="Yahoo を使わず前向き（signals-log）だけ")
    a = ap.parse_args()

    if a.synthetic:
        for seed in [int(s) for s in a.synthetic.split(",")]:
            f1, vix = synthetic(seed, "1d")
            f4, vix4 = ({}, None) if a.no_4h else synthetic(seed + 10_000, "4h")
            ts1d, _ = build(f1, {}, vix)
            ts4h = build({}, f4, vix4)[1] if f4 else []
            res = evaluate(ts1d, ts4h)
            flagged = [FAMILY_LABEL[r["fam"]] + "×" + r["key"] + "(%+.3f)" % r["diff"]["avg"]
                       for r in res["primary"] if r["flag"]]
            base = ", ".join("%s:%+.3f" % (k, v["avg"]) for k, v in res["baseline"].items())
            pmin = min(r["diff"].get("p", 1.0) for r in res["primary"])
            print(f"seed={seed} 取引 日足{len(ts1d):,}/4h{len(ts4h):,} 目立つ={count_flags(res)} "
                  f"主の最小p={pmin:.4f} 基準 {base} 主の目立つ: {flagged or 'なし'}", flush=True)
        return

    live = live_trades(a.live) if a.live else None
    frames_1d, frames_4h, vix = {}, {}, None
    if not a.live_only:
        vix_df = X.fetch("^VIX", "1d")
        vix = vix_df["Close"] if vix_df is not None else None
        for tk in sorted(LEGACY_UNIVERSE):
            df = X.fetch(tk, "1d")
            if df is not None:
                frames_1d[tk] = df
            if not a.no_4h:
                df4 = X.fetch(tk, "4h")
                if df4 is not None:
                    frames_4h[tk] = df4
            print(f"  {tk}: 日足{len(frames_1d.get(tk, [])):,} 4h{len(frames_4h.get(tk, [])):,}", flush=True)
    ts1d, ts4h = build(frames_1d, frames_4h, vix)
    res = evaluate(ts1d, ts4h, live)
    asof = pd.Timestamp.now(tz="Asia/Tokyo").strftime("%Y-%m-%d")
    out = {"asof": asof, "n_1d": len(ts1d), "n_4h": len(ts4h), "n_live": len(live) if live else 0,
           "vix_ok": vix is not None, **res}
    if a.json:
        json.dump(_jsonable(out), open(a.json, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    md = report_md(res, asof, len(ts1d), len(ts4h), len(live) if live else None)
    if a.md:
        open(a.md, "w", encoding="utf-8").write(md)
    print(md[:3000])
    print("目立つ数:", count_flags(res))


if __name__ == "__main__":
    main()
