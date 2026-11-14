# -*- coding: utf-8 -*-
"""adx_now.py（いまの ADX をエンジンと同じ計算で出す）のテスト。2026-11-14 新設。通信しない。

- 帯の区切りが signal_lab_verify.adx_band_of と同じ（20・25 の境目）
- 作り物の Yahoo の返事から作った足で、エンジンの adx_choppiness と同じ値になる
- 4時間足は取引所の時刻で4時間ごとに束ねる

実行:  python tests/test_adx_now.py     （pytest 不要。pytest でも動く）
"""
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import adx_now as A  # noqa: E402
import generate_technical_alerts as G  # noqa: E402
import signal_lab_verify as V  # noqa: E402


def _fake_result(n=400, trend=0.05, tz="Europe/London"):
    t0 = 1_760_000_400  # 1時間ちょうどの区切り
    ts, o, h, l, c = [], [], [], [], []
    p = 150.0
    for i in range(n):
        wig = 0.3 * math.sin(i / 3.0)
        p += trend + 0.1 * math.sin(i / 7.0)
        ts.append(t0 + 3600 * i)
        o.append(p - 0.05); c.append(p + 0.05 * math.cos(i))
        h.append(p + 0.4 + abs(wig)); l.append(p - 0.4 - abs(wig))
    return {"meta": {"exchangeTimezoneName": tz}, "timestamp": ts,
            "indicators": {"quote": [{"open": o, "high": h, "low": l, "close": c}]}}


def test_band_matches_signal_lab_verify():
    for v, want in ((19.99, "weak"), (20.0, "mid"), (24.99, "mid"), (25.0, "strong"), (60.0, "strong")):
        assert A.band_of(v) == want
        assert V.adx_band_of({"indicators_at_signal": {"adx": v}}) == want
    assert A.band_of(None) is None


def test_same_value_as_engine_1h():
    df = A.frame_from_chart(_fake_result(), "1h")
    adx, _ = G.adx_choppiness(df["High"], df["Low"], df["Close"])
    assert abs(A.adx_of(df) - float(adx.iloc[-1])) < 1e-9


def test_4h_bars_are_grouped_by_four_hours():
    df1 = A.frame_from_chart(_fake_result(), "1h")
    df4 = A.frame_from_chart(_fake_result(), "4h")
    assert len(df4) < len(df1) / 3
    assert all(t.hour % 4 == 0 for t in df4.index)               # 取引所の時刻で 0・4・8…時に区切る
    first = df4.index[1]
    part = df1[(df1.index >= first) & (df1.index < first + __import__("pandas").Timedelta(hours=4))]
    assert df4.loc[first, "High"] == part["High"].max() and df4.loc[first, "Close"] == part["Close"].iloc[-1]


def test_strong_trend_is_strong():
    df = A.frame_from_chart(_fake_result(trend=0.6), "4h")
    assert A.band_of(A.adx_of(df)) == "strong"


if __name__ == "__main__":
    n = 0
    for k, f in list(globals().items()):
        if k.startswith("test_") and callable(f):
            f(); n += 1
    print(f"OK {n} tests")
