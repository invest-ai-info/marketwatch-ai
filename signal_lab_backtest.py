# -*- coding: utf-8 -*-
"""
signal_lab_backtest.py — 過去バーにライブ発火ロジックを「リプレイ」して検証データを増やす。

考え方（SIGNAL_LAB_SOP.md / SESSION_HANDOFF.md の方針）:
- ライブのシグナル発火エンジン generate_technical_alerts.py の純関数（detect_signals 等）を
  **import してそのまま過去バーに当てる**＝再実装による乖離を避け、忠実に再現する。
- ライブと同じ「窓」を各バーに渡す（1d=約450日≒320本、4h/1h=約30日相当）＝同じ見え方を再現。
- レコードは signals-log と同じフィルタ次元（ticker/group/direction/trend/tf/signal/
  reversal_long/blocked/outcome）を満たすので、sweep/tracker/verify がそのまま使える。
  **source="backtest_<tf>" を付け、ライブ実績と混ぜない**。

⚠️ バックテストの限界（実約定でない・同バーTP/SL両達は保守的にSL・スプレッド無視・first_pullback無効）。
   発見＋レジーム頑健性チェックに使い、昇格判定はライブ前向きトラッカーが主役。

データ源と取得可能年数（実測）:
- 1d : Yahoo で 10〜30年（period1/period2）。
- 1h : Yahoo は約2年(730日)が上限。4h は 1h をリサンプル＝同じく約2年上限。
  （2年超の intraday が要る場合は Dukascopy/HistData を別途。）

使い方:
    python signal_lab_backtest.py                                  # 1d・全18銘柄・20年
    python signal_lab_backtest.py --timeframes 1h,4h --years 2 \
        --tickers GBPJPY=X,GBPUSD=X,GBPAUD=X,EURAUD=X --out signals-log-backtest-fx.json
"""
import argparse
import datetime
import json
import os
import urllib.request

import pandas as pd

import generate_technical_alerts as gta
from signal_lab_verify import GROUPS, wilson, closed, win

ROOT = os.path.dirname(os.path.abspath(__file__))
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
ALL_TICKERS = sorted(set().union(*GROUPS.values()))

# 時間足ごとの設定（window/warmup はライブのfetch窓に合わせる。expiryはバックテストの決済打ち切り）
TF_CONFIG = {
    "1h": {"window": 720, "warmup": 90, "expiry_days": 5,  "cooldown_h": 4,  "higher_freq": "4h", "higher_label": "4H"},
    "4h": {"window": 200, "warmup": 90, "expiry_days": 14, "cooldown_h": 18, "higher_freq": "D",  "higher_label": "日足"},
    "1d": {"window": 320, "warmup": 80, "expiry_days": 21, "cooldown_h": 72, "higher_freq": "W",  "higher_label": "週足"},
}


def fetch_bars(ticker, timeframe, years):
    """日足は period1/period2 で長期、1h/4h は 1h を range=730d で取得（4h はリサンプル）。"""
    if timeframe == "1d":
        now = datetime.datetime.now()
        p1 = int((now - datetime.timedelta(days=int(years * 365.25))).timestamp())
        p2 = int(now.timestamp())
        url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
               f"?period1={p1}&period2={p2}&interval=1d")
    else:
        days = min(int(years * 365.25), 730)  # Yahoo 1h は約730日が上限
        url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
               f"?range={days}d&interval=1h")
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=40) as r:
        j = json.load(r)
    res = j["chart"]["result"][0]
    q = res["indicators"]["quote"][0]
    df = pd.DataFrame({
        "Open": q.get("open"), "High": q.get("high"),
        "Low": q.get("low"), "Close": q.get("close"), "Volume": q.get("volume"),
    }, index=pd.to_datetime(res["timestamp"], unit="s")).dropna(subset=["High", "Low", "Close"])
    if timeframe == "4h":
        agg = {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}
        df = df.resample("4h").agg(agg).dropna(subset=["Close"])
    return df


def trend_fn(df, higher_freq):
    """base df を上位足にリサンプルし MA25/MA75 で上位足トレンドを返す（look-ahead無し）。"""
    hi = df["Close"].resample(higher_freq).last().dropna()
    ma25, ma75 = hi.rolling(25).mean(), hi.rolling(75).mean()

    def trend_at(d):
        idx = ma25.index.asof(d)
        if idx is pd.NaT or pd.isna(idx):
            return "unknown"
        i = ma25.index.get_loc(idx)
        m25, m75 = ma25.iloc[i], ma75.iloc[i]
        if pd.isna(m25) or pd.isna(m75):
            return "unknown"
        m25_prev = ma25.iloc[i - 5] if i >= 5 else m25
        up = m25 > m25_prev
        if m25 > m75 and up:
            return "上昇"
        if m25 < m75 and not up:
            return "下降"
        return "中立・もみあい"

    return trend_at


def resolve_outcome(df, i, plan, expiry_days):
    e, sl = plan["entry"], plan["stop_loss"]
    tp1, tp2 = plan["take_profit_1"], plan["take_profit_2"]
    is_long = "ロング" in plan["direction"]
    deadline = df.index[i] + pd.Timedelta(days=expiry_days)
    for j in range(i + 1, len(df)):
        if df.index[j] > deadline:
            break
        hi, lo = float(df["High"].iloc[j]), float(df["Low"].iloc[j])
        if is_long:
            hit_sl, hit_tp1, hit_tp2 = lo <= sl, hi >= tp1, hi >= tp2
        else:
            hit_sl, hit_tp1, hit_tp2 = hi >= sl, lo <= tp1, lo <= tp2
        if hit_sl and hit_tp1:
            return "sl", df.index[j].isoformat()   # 同バー両達＝保守的に負け
        if hit_sl:
            return "sl", df.index[j].isoformat()
        if hit_tp1:
            return ("tp2" if hit_tp2 else "tp1"), df.index[j].isoformat()
    return "expired", None


def replay_ticker(ticker, timeframe, years):
    cfg = TF_CONFIG[timeframe]
    try:
        df = fetch_bars(ticker, timeframe, years)
    except Exception as ex:
        print(f"  ⚠️ {ticker} {timeframe}: 取得失敗 {str(ex)[:60]}")
        return []
    if len(df) < cfg["warmup"] + 10:
        print(f"  ⚠️ {ticker} {timeframe}: データ不足 ({len(df)}本)")
        return []
    trend_at = trend_fn(df, cfg["higher_freq"])
    out, last_fire = [], {}
    for i in range(cfg["warmup"], len(df)):
        window = df.iloc[max(0, i - cfg["window"]): i + 1]
        try:
            signals, ind = gta.detect_signals(
                window, signals_log_recent=None, ticker=ticker,
                timeframe=timeframe, now_jst=df.index[i].to_pydatetime(), fundamental_bias=None)
        except Exception:
            continue
        if not signals:
            continue
        direction = gta.determine_direction(signals)
        if direction not in ("long", "short") or not ind.get("atr"):
            continue
        primary = signals[0]["type"]
        prev = last_fire.get(primary)
        if prev is not None and (df.index[i] - prev).total_seconds() / 3600 < cfg["cooldown_h"]:
            continue
        last_fire[primary] = df.index[i]

        plan = gta.calc_entry_sl_tp(ind["price"], ind["atr"], direction)
        sr = gta.compute_sr_runway(plan, ind) or {"blocked": False}
        outcome, resolved_at = resolve_outcome(df, i, plan, cfg["expiry_days"])
        out.append({
            "id": f"{ticker}_{timeframe}_{df.index[i].strftime('%Y%m%d_%H%M')}",
            "fired_at": df.index[i].strftime("%Y-%m-%dT%H:%M:%S+09:00"),
            "timeframe": timeframe, "ticker": ticker, "asset_name": ticker,
            "signal_types": [s["type"] for s in signals], "primary_signal": primary,
            "direction": plan["direction"],
            "entry": plan["entry"], "stop_loss": plan["stop_loss"],
            "take_profit_1": plan["take_profit_1"], "take_profit_2": plan["take_profit_2"],
            "atr": plan["atr"],
            "indicators_at_signal": {"rsi": ind.get("rsi"), "ma25": ind.get("ma25"),
                                     "ma75": ind.get("ma75"), "recent_high": ind.get("recent_high"),
                                     "recent_low": ind.get("recent_low"), "regime": ind.get("regime")},
            "trend_alignment": {"higher_tf": cfg["higher_label"], "higher_tf_trend": trend_at(df.index[i])},
            "sr_runway": sr,
            "outcome": outcome, "outcome_resolved_at": resolved_at,
            "source": f"backtest_{timeframe}",
        })
    res = [r for r in out if closed(r)]
    print(f"  ✓ {ticker} {timeframe}: 発火 {len(out)} / 決済済 {len(res)}（{df.index[0].date()}〜{df.index[-1].date()}）")
    return out


def summarize(records):
    res = [r for r in records if closed(r)]
    print(f"\n=== バックテスト結果サマリ（決済済のみ）===\n総発火 {len(records)} / 決済済 {len(res)}")

    def line(label, rows):
        n = len(rows); k = sum(1 for r in rows if win(r))
        if n == 0:
            print(f"  {label:<22} N=0"); return
        lo, hi = wilson(k, n)
        print(f"  {label:<22} {k:>4}/{n:<5} = {100*k/n:5.1f}%  CI[{lo:.1f}~{hi:.1f}]")

    line("全体", res)
    for tf in sorted(set(r["timeframe"] for r in res)):
        line(f"tf={tf}", [r for r in res if r["timeframe"] == tf])
    for tk in sorted(set(r["ticker"] for r in res)):
        line(tk, [r for r in res if r["ticker"] == tk])
    for d in ("ロング", "ショート"):
        line(f"dir={d}", [r for r in res if d in r["direction"]])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeframes", default="1d", help="カンマ区切り 1h,4h,1d（既定1d）")
    ap.add_argument("--years", type=float, default=20, help="さかのぼる年数（intradayはYahoo上限2年）")
    ap.add_argument("--tickers", help="カンマ区切り（既定=全18銘柄）")
    ap.add_argument("--out", default="signals-log-backtest.json", help="出力JSON")
    args = ap.parse_args()
    tfs = [t.strip() for t in args.timeframes.split(",")]
    tickers = [t.strip() for t in args.tickers.split(",")] if args.tickers else ALL_TICKERS
    print(f"=== リプレイ・バックテスト（{args.years}年・{tfs}・{len(tickers)}銘柄）===")
    all_recs = []
    for tf in tfs:
        if tf not in TF_CONFIG:
            print(f"  ⚠️ 未対応timeframe: {tf}"); continue
        for t in tickers:
            all_recs.extend(replay_ticker(t, tf, args.years))
    with open(os.path.join(ROOT, args.out), "w", encoding="utf-8", newline="") as f:
        json.dump(all_recs, f, ensure_ascii=False, indent=2)
    summarize(all_recs)
    print(f"\n→ {args.out} に {len(all_recs)} 件。`python signal_lab_sweep.py --log {args.out} --min-n 50` で発見スイープ可。")


if __name__ == "__main__":
    main()
