# -*- coding: utf-8 -*-
"""
exit_rule_backtest.py — 「入ったシグナルと同じ指標のシグナルでしか手じまわない」ルールの検証。

2026-09-24 オーナーの質問「あるシグナルでエントリーしたとして、利確と損切りは必ず同じシグナルで行う
というルールにしたらどうなるか」。いまのシステムは ATR 固定（損切り 1.5ATR / 利確 2.0ATR）で出る。

【事前登録（2026-09-24・結果を見る前にこの説明文ごとコミットして固定する）】
対象   : 監視18銘柄（signal_lab_tracker.LEGACY_UNIVERSE）。Yahoo・auto_adjust=True。
足     : 日足＝2006-01-01〜実行日（主）／4時間足＝直近730日の1時間足を resample("4h")（エンジンと同じ作り方・副）。
入口   : エンジン detect_signals と同じ式（calc_rsi / calc_macd / calc_bbands / calc_atr をそのまま import）。
         その足の終値で入る。同じ銘柄×同じ入口は、出たあと3本は数えない（日足エンジンのクールダウン72hに相当）。
         各シグナルを独立の1取引として数える（重なりを許す＝3つの出口に**同じ入口**を当てて比べるため）。
         指標が出揃う前（先頭80本）は使わない。
組（入口 → 同じ指標の出口）:
         RSI           : RSI売られすぎからの反発で買い → RSI70超えで手じまい
         ボリンジャー   : −2σタッチで買い → +2σ突破で手じまい
         直近20本       : 高値ブレイクで買い → 安値割れで手じまい ／ 安値割れで売り → 高値ブレイクで手じまい
         MACD          : ゴールデンクロスで買い → デッドクロスで手じまい ／ デッドで売り → ゴールデンで手じまい
         移動平均線     : 25本線が75本線を上抜けで買い → 下抜けで手じまい ／ その逆の売り
         （RSI70超え・+2σ突破での「売り」はエンジンが売りに使っていないので入口にしない）
出口（3通り）:
  S  同じ指標だけ : 反対のシグナルが出た足の終値で手じまう。値段の損切りは置かない。
                    データの最後まで出なければ「未決済」として別に数える（勝ち負けに入れない）。
  A  いまの方式   : 損切り 1.5ATR / 利確 2.0ATR。先に触れた方。同じ足で両方なら損切り（エンジンと同じ保守側）。
                    損切りは窓を開けて飛び越えたら始値で約定（実際に起きる損）。利確は 2.0ATR ちょうど。
                    日足21本・4時間足42本（=7日）で届かなければ、その足の終値で手じまう（エンジンの期限と同じ長さ）。
  S+ 同じ指標＋値段の損切り : S に A と同じ損切り（1.5ATR・窓は始値）だけを足す。利確は同じ指標のシグナル。
R の単位 : 入った足の ATR(14)×1.5 を 1R（3通り共通）。
コスト   : signal_lab_sweep.cost_r_of と同じ往復スプレッド×1.5 を1取引ごとに引く（3通り共通）。主指標はコスト後。
判定     : 主指標＝組ごとのコスト後の平均R。「S が A より良い／悪い」と言うのは、同じ入口ごとの差（S−A）の
           平均の95%幅が0をまたがないときだけ。95%幅は「銘柄」と「時期（日足＝年・4時間足＝四半期）」の
           二方向でまとめて数え、まとまりの少なさを t 分布で補正する（重なった取引も、同じ時期の銘柄どうしも独立でない）。
           日足はさらに、前半・後半で差の向きがそろうことを条件にする（そろわなければ「時期しだい」）。
           加えて差の大きさが 0.10R 以上（1回あたり損切り幅の1割）のときだけ「差がある」と書く。
         事前の較正（2026-09-24・作り物の値動き＝上下の癖なしの足し算ランダムウォーク×18銘柄×12回）:
           ・幅の見積もりは実際のばらつきとほぼ一致（倍率の中央値 0.95）。ただし**移動平均線の買い（日足）は
             約0.6倍に狭く出た**（取引が少なく保有が長い）＝この組の「差がある」は割り引いて読む。
           ・癖のない値動きでも、注文の仕方の違いだけで ±0.03〜0.08R の差が毎回同じ向きに出る
             （A の利確は指値＝ヒゲで約定、S は終値で手じまい、損切りはどちらもヒゲで刈られる）。
             これは本物の相場でも起きる実在の差なので、0.10R 未満の差は「意味のある差」として扱わない。またぐなら「差があるとは言えない」と書く。
           日足は 2006–2015 と 2016–実行日 に分けても同じ向きかを見る（片方だけなら「時期しだい」と書く）。
限界（先に書いておく）: 先物のつなぎ目（限月の乗り換え）で値段が飛ぶ。TP2 は使わない（エンジンでも先に TP1 に触れる）。
           エンジンは同じ足に複数のシグナルが出ると多数決で向きを決めるが、ここでは組ごとに向きを固定する。

使い方（Yahoo に届く所で）: python exit_rule_backtest.py [--out exit_rule_backtest.json]
"""
import argparse
import json
import math
import sys
import time

import numpy as np
import pandas as pd

from generate_technical_alerts import calc_atr, calc_bbands, calc_macd, calc_rsi
from signal_lab_sweep import cost_r_of
from signal_lab_tracker import LEGACY_UNIVERSE

PAIRS = [  # (組, 入口シグナル, 向き, 出口シグナル)
    ("RSI", "rsi_oversold_bounce", "long", "rsi_overbought"),
    ("ボリンジャー", "bb_lower_touch", "long", "bb_upper_break"),
    ("直近20本", "high_break", "long", "low_break"),
    ("直近20本", "low_break", "short", "high_break"),
    ("MACD", "macd_golden", "long", "macd_dead"),
    ("MACD", "macd_dead", "short", "macd_golden"),
    ("移動平均線", "ma_golden", "long", "ma_dead"),
    ("移動平均線", "ma_dead", "short", "ma_golden"),
]
COOLDOWN = 3
WARMUP = 80
SL_ATR, TP_ATR = 1.5, 2.0
EXPIRY = {"1d": 21, "4h": 42}
SPLIT = pd.Timestamp("2016-01-01")


def signals(df):
    """エンジン detect_signals の10種を、全ての足について一度に計算する（t と t−1 の値で判定＝同じ式）。"""
    c, h, l = df["Close"], df["High"], df["Low"]
    rsi = calc_rsi(c)
    macd, sig, _ = calc_macd(c)
    bbu, _, bbl = calc_bbands(c)
    ma25, ma75 = c.rolling(25).mean(), c.rolling(75).mean()
    width = bbu - bbl
    bb_pos = ((c - bbl) / width).where(width > 0, 0.5)
    rp, mp, sp, m25p, m75p = rsi.shift(1), macd.shift(1), sig.shift(1), ma25.shift(1), ma75.shift(1)
    return pd.DataFrame({
        "rsi_oversold_bounce": (rp < 30) & (rsi > rp) & (rsi < 50),
        "rsi_overbought": (rp <= 70) & (rsi > 70),
        "macd_golden": (mp <= sp) & (macd > sig),
        "macd_dead": (mp >= sp) & (macd < sig),
        "ma_golden": (m25p <= m75p) & (ma25 > ma75),
        "ma_dead": (m25p >= m75p) & (ma25 < ma75),
        "bb_lower_touch": (l <= bbl) & (c > l) & (bb_pos < 0.3),
        "bb_upper_break": (c > bbu) & (c.shift(1) <= bbu) & (bb_pos > 0.7),
        "high_break": c > h.shift(1).rolling(20).max(),
        "low_break": c < l.shift(1).rolling(20).min(),
    }, index=df.index).fillna(False)


def _sl_fill(side, sl, o, h, l):
    """その足で損切りに触れたら約定値、触れなければ None。窓で飛び越えたら始値（実際の損）。"""
    if side == "long" and l <= sl:
        return min(o, sl)
    if side == "short" and h >= sl:
        return max(o, sl)
    return None


def trades(df, sig, ticker, tf, entry_sig, side, exit_sig):
    """1銘柄×1組の全取引。戻り値＝[{time, S, A, Splus, bars_S, cost}]（R は未決済なら None）。"""
    o, h, l, c = (df[k].to_numpy(float) for k in ("Open", "High", "Low", "Close"))
    atr = calc_atr(df["High"], df["Low"], df["Close"]).to_numpy(float)
    ent, ext = sig[entry_sig].to_numpy(bool), sig[exit_sig].to_numpy(bool)
    d = 1 if side == "long" else -1
    n, out, last = len(c), [], -10 ** 9
    for i in range(WARMUP, n - 1):
        if not ent[i] or i - last <= COOLDOWN or not (atr[i] > 0):
            continue
        last = i
        e, risk = c[i], SL_ATR * atr[i]
        sl, tp = e - d * risk, e + d * TP_ATR * atr[i]
        r = lambda px: d * (px - e) / risk
        # S: 同じ指標の反対シグナルだけ
        js = next((j for j in range(i + 1, n) if ext[j]), None)
        S, bars = (r(c[js]), js - i) if js is not None else (None, None)
        # S+: S に値段の損切りを足す（同じ足なら損切りが先＝ザラ場で先に触れる）
        Sp = None
        for j in range(i + 1, n):
            f = _sl_fill(side, sl, o[j], h[j], l[j])
            if f is not None:
                Sp = r(f)
                break
            if ext[j]:
                Sp = r(c[j])
                break
        # A: いまの方式（先に触れた方・同じ足なら損切り・期限で終値）
        A = None
        for j in range(i + 1, min(n, i + EXPIRY[tf] + 1)):
            f = _sl_fill(side, sl, o[j], h[j], l[j])
            if f is not None:
                A = r(f)
                break
            if (side == "long" and h[j] >= tp) or (side == "short" and l[j] <= tp):
                A = TP_ATR / SL_ATR
                break
            if j == i + EXPIRY[tf]:
                A = r(c[j])
        cost = cost_r_of({"entry": e, "stop_loss": sl, "ticker": ticker})
        out.append({"ticker": ticker, "tf": tf, "time": df.index[i], "S": S, "A": A, "Splus": Sp,
                    "bars_S": bars, "cost": cost,
                    "open_S_mtm": r(c[-1]) if S is None else None})
    return out


T975 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228,
        11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145, 15: 2.131, 16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093,
        20: 2.086, 25: 2.060, 30: 2.042}


def t975(df):
    """t分布の97.5%点（まとまりが少ないときの補正）。表に無い自由度は小さい側の値＝保守側。"""
    return T975[max(k for k in T975 if k <= max(1, df))] if df <= 30 else 2.0


def clusters_of(t):
    """まとまり2つ＝(銘柄, 時期)。時期＝日足は年・4時間足は四半期。
    同じ銘柄の取引は出口を共有して重なり（独立でない）、同じ時期は銘柄どうしがそろって動く
    （株価指数どうし・通貨どうし）。両方を許す二方向クラスタで幅を出す。
    実測（作り物のランダムな値動き）: 銘柄×年だけでは「差がある」と誤って出る割合が 12.5%＝設計の 5% を大きく超えた。"""
    ts = t["time"]
    return t["ticker"], (ts.year if t["tf"] == "1d" else (ts.year, (ts.month - 1) // 3))


def _mean_ci(vals, groups):
    """平均と95%幅。groups＝[(銘柄, 時期)]。二方向クラスタ（CR1）＋ t(G−1)、G＝少ない方のまとまり数。"""
    a = np.array(vals, float)
    n, m = len(a), float(a.mean())
    if n < 2:
        return m, m, m
    e = a - m

    def ss(keyf):
        sums = {}
        for x, g in zip(e, groups):
            k = keyf(g)
            sums[k] = sums.get(k, 0.0) + x
        return sum(v * v for v in sums.values()), len(sums)

    s1, g1 = ss(lambda g: g[0])
    s2, g2 = ss(lambda g: g[1])
    s12, _ = ss(lambda g: g)
    v = s1 + s2 - s12
    if v <= 0:
        v = max(s1, s2)
    G = min(g1, g2)
    if G < 2:
        return m, float("-inf"), float("inf")
    se = math.sqrt(v * G / (G - 1)) / n
    c = t975(G - 1)
    return m, m - c * se, m + c * se


def summarize(rs, groups, gross=None, bars=None):
    keep = [i for i, x in enumerate(rs) if x is not None]
    if not keep:
        return {"n": 0}
    a = np.array([rs[i] for i in keep])
    m, lo, hi = _mean_ci(a, [groups[i] for i in keep])
    g = np.array([gross[i] for i in keep]) if gross is not None else a
    out = {"n": len(a), "win": float((a > 0).mean()), "avg": m, "lo": lo, "hi": hi,
           "beyond_1R": float((g < -1.0 - 1e-9).mean()),  # コスト前で −1R より悪い負け（窓・損切りなし）
           "p5": float(np.percentile(a, 5)), "worst": float(a.min())}
    if bars:
        out["bars_median"] = float(np.median(bars))
    return out


def diff(xs, ys, groups):
    """同じ入口ごとの差（x−y）の平均と95%幅（まとまりごとの相関を許す）。"""
    keep = [i for i in range(len(xs)) if xs[i] is not None and ys[i] is not None]
    if len(keep) < 2:
        return {"n": len(keep)}
    m, lo, hi = _mean_ci([xs[i] - ys[i] for i in keep], [groups[i] for i in keep])
    return {"n": len(keep), "avg": m, "lo": lo, "hi": hi}


def evaluate(ts):
    """取引の束 → S/A/S+ の要約（コスト後）と差。"""
    if not ts:
        return {}
    net = lambda k: [t[k] - t["cost"] if t[k] is not None else None for t in ts]
    gross = lambda k: [t[k] for t in ts]
    g = [clusters_of(t) for t in ts]
    S, A, Sp = net("S"), net("A"), net("Splus")
    gS = [x for x in gross("S") if x is not None]
    return {
        "S": summarize(S, g, gross("S"), [t["bars_S"] for t in ts if t["bars_S"] is not None]),
        "A": summarize(A, g, gross("A")), "Splus": summarize(Sp, g, gross("Splus")),
        "S_minus_A": diff(S, A, g), "Splus_minus_A": diff(Sp, A, g),
        "open_S": sum(1 for t in ts if t["S"] is None),
        "gross_S_avg": float(np.mean(gS)) if gS else None,
    }


def fetch(ticker, tf, tries=3):
    import yfinance as yf
    for k in range(tries):
        try:
            if tf == "1d":
                df = yf.download(ticker, start="2006-01-01", interval="1d", progress=False, auto_adjust=True)
            else:
                df = yf.download(ticker, period="730d", interval="1h", progress=False, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            if tf == "4h":
                agg = {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}
                df = df.resample("4h").agg(agg)
            df = df.dropna(subset=["Open", "High", "Low", "Close"])
            if len(df) > WARMUP + 50:
                return df
        except Exception as e:  # noqa: BLE001
            print(f"  ⚠️ {ticker} {tf} 取得失敗 {k + 1}/{tries}: {type(e).__name__}: {str(e)[:80]}", file=sys.stderr)
        time.sleep(2 * (k + 1))
    return None


def run(frames):
    """frames＝{(ticker, tf): df} → 結果 dict（組×足、全体、日足の時期別）。"""
    res = {}
    for (ticker, tf), df in frames.items():
        sig = signals(df)
        for grp, es, side, xs in PAIRS:
            key = f"{tf}|{grp}|{es}|{side}|{xs}"
            res.setdefault(key, []).extend(trades(df, sig, ticker, tf, es, side, xs))
    out = {}
    for key, ts in res.items():
        tf = key.split("|")[0]
        out[key] = evaluate(ts)
        if tf == "1d":
            out[key]["early"] = evaluate([t for t in ts if t["time"].tz_localize(None) < SPLIT])
            out[key]["late"] = evaluate([t for t in ts if t["time"].tz_localize(None) >= SPLIT])
    for tf in ("1d", "4h"):
        allts = [t for k, ts in res.items() if k.startswith(tf + "|") for t in ts]
        if allts:
            out[f"{tf}|全体"] = evaluate(allts)
    return out


LABEL = {"rsi_oversold_bounce": "RSI売られすぎ反発", "rsi_overbought": "RSI70超え", "bb_lower_touch": "−2σタッチ",
         "bb_upper_break": "+2σ突破", "high_break": "20本高値ブレイク", "low_break": "20本安値割れ",
         "macd_golden": "MACDゴールデン", "macd_dead": "MACDデッド", "ma_golden": "MAゴールデン", "ma_dead": "MAデッド"}


MIN_EFFECT = 0.10


def verdict(d, early=None, late=None):
    """事前登録した判定: 幅が0をまたがない・差が0.10R以上・（日足は）前半と後半で向きがそろう。"""
    if not d or d.get("n", 0) < 2 or not math.isfinite(d.get("lo", float("nan"))):
        return "判定できない"
    if not ((d["lo"] > 0 or d["hi"] < 0) and abs(d["avg"]) >= MIN_EFFECT):
        return "差があるとは言えない"
    if early is not None and late is not None:
        if not (early.get("n", 0) >= 2 and late.get("n", 0) >= 2) or (early["avg"] > 0) != (late["avg"] > 0):
            return "時期しだい"
    return "左の方が良い" if d["avg"] > 0 else "左の方が悪い"


def fmt(s):
    if not s or not s.get("n"):
        return "—"
    return f"{s['avg']:+.3f} [{s['lo']:+.3f}〜{s['hi']:+.3f}]"


def report(out):
    lines = []
    for tf, title in (("1d", "日足（2006年〜）"), ("4h", "4時間足（直近2年）")):
        keys = [k for k in out if k.startswith(tf + "|") and k != f"{tf}|全体"]
        if not keys:
            continue
        lines.append(f"\n## {title}\n")
        lines.append("| 入口 → 出口 | 向き | 出口 | 件数 | 勝率 | 平均R・コスト後 [95%] | −1R超の負け | 下位5% | 最悪 | 保有(中央) |")
        lines.append("|---|---|---|---|---|---|---|---|---|---|")
        for k in keys + [f"{tf}|全体"]:
            if k not in out:
                continue
            p = k.split("|")
            name = "全体" if len(p) == 2 else f"{LABEL[p[2]]} → {LABEL[p[4]]}"
            side = "" if len(p) == 2 else ("買い" if p[3] == "long" else "売り")
            for code, lab in (("S", "S 同じ指標だけ"), ("Splus", "S+ 同じ指標＋損切り"), ("A", "A いまの方式")):
                s = out[k][code]
                if not s.get("n"):
                    continue
                bm = f"{s['bars_median']:.0f}本" if "bars_median" in s else ""
                lines.append(f"| {name} | {side} | {lab} | {s['n']} | {100 * s['win']:.1f}% | {fmt(s)} | "
                             f"{100 * s['beyond_1R']:.1f}% | {s['p5']:+.2f} | {s['worst']:+.2f} | {bm} |")
            d1, d2 = out[k]["S_minus_A"], out[k]["Splus_minus_A"]
            e, la = out[k].get("early", {}), out[k].get("late", {})
            v1 = verdict(d1, e.get("S_minus_A"), la.get("S_minus_A"))
            v2 = verdict(d2, e.get("Splus_minus_A"), la.get("Splus_minus_A"))
            lines.append(f"| ↳ 差 |  | S−A {fmt(d1)}＝**{v1}** ／ S+−A {fmt(d2)}＝**{v2}** | 未決済S {out[k]['open_S']} "
                         f"|  |  |  |  |  |  |")
        if tf == "1d":
            lines.append("\n### 日足・時期別（コスト後の平均R：前半 2006–2015 ／ 後半 2016–）\n")
            lines.append("| 入口 → 出口 | 向き | S 前半 | S 後半 | A 前半 | A 後半 | S−A 前半 | S−A 後半 |")
            lines.append("|---|---|---|---|---|---|---|---|")
            for k in keys:
                p = k.split("|")
                e, la = out[k]["early"], out[k]["late"]
                lines.append(f"| {LABEL[p[2]]} → {LABEL[p[4]]} | {'買い' if p[3] == 'long' else '売り'} | "
                             f"{fmt(e['S'])} | {fmt(la['S'])} | {fmt(e['A'])} | {fmt(la['A'])} | "
                             f"{fmt(e['S_minus_A'])} | {fmt(la['S_minus_A'])} |")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="exit_rule_backtest.json")
    ap.add_argument("--tf", default="1d,4h")
    args = ap.parse_args()
    frames, missing = {}, []
    for tf in args.tf.split(","):
        for t in sorted(LEGACY_UNIVERSE):
            df = fetch(t, tf)
            if df is None:
                missing.append(f"{t}({tf})")
            else:
                frames[(t, tf)] = df
                print(f"  {t} {tf}: {len(df)}本 {df.index[0].date()}〜{df.index[-1].date()}", file=sys.stderr)
    out = run(frames)
    print("# 同じ指標で手じまうルールの検証（exit_rule_backtest.py）")
    print(f"取得できなかった銘柄: {', '.join(missing) or 'なし'}")
    print(report(out))
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, default=str)


if __name__ == "__main__":
    main()
