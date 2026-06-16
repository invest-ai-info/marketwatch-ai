# -*- coding: utf-8 -*-
"""
signal_lab_backtest.py — 過去日足にライブ発火ロジックを「リプレイ」して検証データを増やす。

考え方（SIGNAL_LAB_SOP.md / SESSION_HANDOFF.md の方針）:
- ライブのシグナル発火エンジン generate_technical_alerts.py の純関数（detect_signals 等）を
  **import してそのまま過去バーに当てる**＝再実装による乖離を避け、忠実に再現する。
- ライブの日足は period=450d（≒300本）の窓で評価するので、本バックテストも
  約320本のトレーリング窓を各バーに渡す＝ライブと同じ見え方を再現（かつ高速）。
- レコードは signals-log と同じフィルタ次元（ticker/group/direction/trend/tf/signal/
  reversal_long/blocked/outcome）を満たすので、signal_lab_sweep.py / signal_lab_tracker.py /
  signal_lab_verify.py がそのまま使える。**source="backtest_1d" を付け、ライブ実績と混ぜない**。

⚠️ 重要な前提（バックテストの限界。あなたが金・MT4検証で重視してきた点と同じ）:
- これは「もし当時このエンジンが動いていたら」のシミュレーション＝実約定ではない。
- 同一バー内で TP と SL の両方に触れた日は先後不明 → 保守的に SL（負け）扱い。
- スプレッド/スリッページ/約定ズレは無視（TP=2.0ATR/SL=1.5ATR に対して相対的に小）。
- first_pullback（email_silent の少数派）は安定性のため無効化。主要シグナルは忠実。
- 発見スイープには有用だが、昇格判定はあくまで「ライブの前向きトラッカー」を主役にする。

使い方:
    python signal_lab_backtest.py                       # 既定: 全18銘柄・20年・signals-log-backtest.json
    python signal_lab_backtest.py --years 3 --tickers GC=F,USDJPY=X   # 検証用の短期/少数
    python signal_lab_backtest.py --out signals-log-backtest.json
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
WINDOW = 320          # トレーリング窓（ライブの450日≒300本に合わせる）
WARMUP = 80           # MA75 が有効になるまで
EXPIRY_DAYS = 21      # 1d の期限（未決済はexpired＝勝率計算から除外）
COOLDOWN_DAYS = 3     # 1d クールダウン 72h


def fetch_daily(ticker, years):
    now = datetime.datetime.now()
    p1 = int((now - datetime.timedelta(days=int(years * 365.25))).timestamp())
    p2 = int(now.timestamp())
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
           f"?period1={p1}&period2={p2}&interval=1d")
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=40) as r:
        j = json.load(r)
    res = j["chart"]["result"][0]
    ts = res["timestamp"]
    q = res["indicators"]["quote"][0]
    df = pd.DataFrame({
        "Open": q.get("open"), "High": q.get("high"),
        "Low": q.get("low"), "Close": q.get("close"), "Volume": q.get("volume"),
    }, index=pd.to_datetime(ts, unit="s"))
    return df.dropna(subset=["High", "Low", "Close"])


def weekly_trend_fn(df):
    """日足から週足を作り、MA25/MA75 で上位足トレンドを返す関数（look-ahead無し）。"""
    wk = df["Close"].resample("W").last().dropna()
    ma25, ma75 = wk.rolling(25).mean(), wk.rolling(75).mean()

    def trend_at(d):
        idx = ma25.index.asof(d)  # d 以前で最後に確定した週末
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


def resolve_outcome(df, i, plan):
    """発火バー i の後ろを EXPIRY_DAYS 歩いて、TP1/SL のどちらが先かで勝敗を決める。
    同一バー両達は保守的に SL（負け）。"""
    e, sl = plan["entry"], plan["stop_loss"]
    tp1, tp2 = plan["take_profit_1"], plan["take_profit_2"]
    is_long = "ロング" in plan["direction"]
    fired = df.index[i]
    deadline = fired + pd.Timedelta(days=EXPIRY_DAYS)
    for j in range(i + 1, len(df)):
        d = df.index[j]
        if d > deadline:
            break
        hi, lo = float(df["High"].iloc[j]), float(df["Low"].iloc[j])
        if is_long:
            hit_sl, hit_tp1, hit_tp2 = lo <= sl, hi >= tp1, hi >= tp2
        else:
            hit_sl, hit_tp1, hit_tp2 = hi >= sl, lo <= tp1, lo <= tp2
        if hit_sl and hit_tp1:
            return "sl", d.isoformat()           # 同バー両達＝保守的に負け
        if hit_sl:
            return "sl", d.isoformat()
        if hit_tp1:
            return ("tp2" if hit_tp2 else "tp1"), d.isoformat()
    return "expired", None


def replay_ticker(ticker, years):
    try:
        df = fetch_daily(ticker, years)
    except Exception as ex:
        print(f"  ⚠️ {ticker}: 取得失敗 {str(ex)[:60]}")
        return []
    if len(df) < WARMUP + 10:
        print(f"  ⚠️ {ticker}: データ不足 ({len(df)}本)")
        return []
    trend_at = weekly_trend_fn(df)
    out = []
    last_fire = {}  # (signal_type) -> fired date（クールダウン）
    for i in range(WARMUP, len(df)):
        window = df.iloc[max(0, i - WINDOW): i + 1]
        bar_dt = df.index[i].to_pydatetime()
        try:
            signals, ind = gta.detect_signals(
                window, signals_log_recent=None, ticker=ticker,
                timeframe="1d", now_jst=bar_dt, fundamental_bias=None)
        except Exception:
            continue
        if not signals:
            continue
        direction = gta.determine_direction(signals)
        if direction not in ("long", "short"):
            continue
        primary = signals[0]["type"]
        # クールダウン（同 signal_type 72h）
        prev = last_fire.get(primary)
        if prev is not None and (df.index[i] - prev).days < COOLDOWN_DAYS:
            continue
        last_fire[primary] = df.index[i]

        plan = gta.calc_entry_sl_tp(ind["price"], ind["atr"], direction)
        if not ind.get("atr"):
            continue
        sr = gta.compute_sr_runway(plan, ind) or {"blocked": False}
        trend = trend_at(df.index[i])
        outcome, resolved_at = resolve_outcome(df, i, plan)
        rec = {
            "id": f"{ticker}_1d_{df.index[i].strftime('%Y%m%d')}",
            "fired_at": df.index[i].strftime("%Y-%m-%dT00:00:00+09:00"),
            "timeframe": "1d",
            "ticker": ticker,
            "asset_name": ticker,
            "signal_types": [s["type"] for s in signals],
            "primary_signal": primary,
            "direction": plan["direction"],
            "entry": plan["entry"], "stop_loss": plan["stop_loss"],
            "take_profit_1": plan["take_profit_1"], "take_profit_2": plan["take_profit_2"],
            "atr": plan["atr"],
            "indicators_at_signal": {
                "rsi": ind.get("rsi"), "ma25": ind.get("ma25"), "ma75": ind.get("ma75"),
                "recent_high": ind.get("recent_high"), "recent_low": ind.get("recent_low"),
                "regime": ind.get("regime"),
            },
            "trend_alignment": {"higher_tf": "週足", "higher_tf_trend": trend},
            "sr_runway": sr,
            "outcome": outcome,
            "outcome_resolved_at": resolved_at,
            "source": "backtest_1d",
        }
        out.append(rec)
    res = [r for r in out if closed(r)]
    print(f"  ✓ {ticker}: 発火 {len(out)} / 決済済 {len(res)}（{df.index[0].date()}〜{df.index[-1].date()}）")
    return out


def summarize(records):
    res = [r for r in records if closed(r)]
    print("\n=== バックテスト結果サマリ（決済済のみ・source=backtest_1d）===")
    print(f"総発火 {len(records)} / 決済済 {len(res)}")
    def line(label, rows):
        n = len(rows); k = sum(1 for r in rows if win(r))
        if n == 0:
            print(f"  {label:<16} N=0"); return
        lo, hi = wilson(k, n)
        print(f"  {label:<16} {k:>4}/{n:<5} = {100*k/n:5.1f}%  CI[{lo:.1f}~{hi:.1f}]")
    line("全体", res)
    for g, tks in GROUPS.items():
        line(g, [r for r in res if r["ticker"] in tks])
    for d in ("ロング", "ショート"):
        line(f"dir={d}", [r for r in res if d in r["direction"]])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=float, default=20, help="さかのぼる年数（既定20）")
    ap.add_argument("--tickers", help="カンマ区切り（既定=全18銘柄）")
    ap.add_argument("--out", default="signals-log-backtest.json", help="出力JSON")
    args = ap.parse_args()
    tickers = [t.strip() for t in args.tickers.split(",")] if args.tickers else ALL_TICKERS
    print(f"=== 日足リプレイ・バックテスト（{args.years}年・{len(tickers)}銘柄）===")
    all_recs = []
    for t in tickers:
        all_recs.extend(replay_ticker(t, args.years))
    with open(os.path.join(ROOT, args.out), "w", encoding="utf-8", newline="") as f:
        json.dump(all_recs, f, ensure_ascii=False, indent=2)
    summarize(all_recs)
    print(f"\n→ {args.out} に {len(all_recs)} 件を出力。`python signal_lab_sweep.py --log {args.out}` で発見スイープ可。")


if __name__ == "__main__":
    main()
