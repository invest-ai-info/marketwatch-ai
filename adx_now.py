# -*- coding: utf-8 -*-
"""いまの ADX(14) を、シグナルのエンジンと同じ計算で出す（2026-11-14 オーナー「足して」）。

目的: 確かめに残った唯一の回避「順張り×ADX25以上は見送り」（signal-lab-tracker の rl_tf_adx_strong・
前向き177件 平均 −0.169R〔−0.321〜−0.018〕・2026-11-07 昇格）を、technical-analyst → risk-manager の判断で使えるようにする。
- 計算＝generate_technical_alerts.adx_choppiness（エンジンと同じ式）。足の作り方もエンジンに合わせる
  （1時間足＝直近30日・4時間足＝1時間足をその銘柄の取引所の時刻で4時間ごとに束ねる・日足＝直近450日）。
- 値段＝Yahoo の chart API を直接（yfinance は手元でブロックされるため）。最後の足は途中の足（エンジンと同じ）。
- 帯＝weak（20未満）／mid（20〜25未満）／strong（25以上）＝signal_lab_verify.adx_band_of と同じ区切り。

使い方:  python adx_now.py USDJPY=X 4h      （時間足は 1h / 4h / 1d。省略すると 4h）
"""
import json
import sys
import urllib.request

import pandas as pd

RANGE = {"1h": ("30d", "1h"), "4h": ("30d", "1h"), "1d": ("450d", "1d")}


def band_of(adx):
    """signal_lab_verify.adx_band_of と同じ区切り"""
    if adx is None or pd.isna(adx):
        return None
    return "weak" if adx < 20 else ("mid" if adx < 25 else "strong")


def frame_from_chart(result, timeframe):
    """Yahoo chart API の result → エンジンと同じ形の足（High/Low/Close）"""
    q = result["indicators"]["quote"][0]
    tz = (result.get("meta") or {}).get("exchangeTimezoneName") or "UTC"
    idx = pd.to_datetime(result["timestamp"], unit="s", utc=True).tz_convert(tz)
    df = pd.DataFrame({"Open": q["open"], "High": q["high"], "Low": q["low"], "Close": q["close"]}, index=idx)
    df = df.dropna(subset=["Close"])
    if timeframe == "4h":
        df = df.resample("4h").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last"}).dropna(subset=["Close"])
    return df


def adx_of(df):
    from generate_technical_alerts import adx_choppiness
    adx, _ = adx_choppiness(df["High"], df["Low"], df["Close"])
    v = adx.iloc[-1]
    return None if pd.isna(v) else float(v)


def fetch(ticker, timeframe):
    rng, interval = RANGE[timeframe]
    u = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range={rng}&interval={interval}"
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    return json.load(urllib.request.urlopen(req, timeout=30))["chart"]["result"][0]


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    ticker = argv[0]
    tf = argv[1] if len(argv) > 1 else "4h"
    if tf not in RANGE:
        print(f"時間足は 1h / 4h / 1d のどれか（指定: {tf}）")
        return 2
    df = frame_from_chart(fetch(ticker, tf), tf)
    a = adx_of(df)
    b = band_of(a)
    label = {"strong": "強いトレンド（25以上）＝順張りは見送り",
             "mid": "中くらい（20〜25）", "weak": "弱い（20未満）"}.get(b, "計算できない")
    print(f"{ticker} {tf} ADX(14)={a:.1f} → {label}" if a is not None else f"{ticker} {tf} ADX(14)=計算できない")
    print(f"  最後の足: {df.index[-1]}（途中の足を含む・エンジンと同じ）")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
