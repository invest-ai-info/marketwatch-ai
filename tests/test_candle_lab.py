# -*- coding: utf-8 -*-
"""C1 シグナルの直前の足の形（candle_lab.py）のテスト。作り物の値動きだけを使う（本物の成績は見ない）。2026-09-27 新設。

実行:  python tests/test_candle_lab.py     （pytest 不要。pytest でも動く）
"""
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import candle_lab as C  # noqa: E402


def test_constants_match_the_registration():
    assert (C.PIN_WICK, C.PIN_BODY, C.MIN_N, C.MIN_EFF, C.ENGINE_DAYS) == (0.60, 0.30, 100, 0.05, 30)
    text = open(os.path.join(ROOT, "PILLAR_PREREG.md"), encoding="utf-8").read()
    assert "## C1 シグナルの直前の足の形" in text and "60%以上" in text and "30%以下" in text


def test_pin_bar():
    assert C.pin_dirs(10.0, 10.2, 9.0, 10.1) == {"long"}        # 下ヒゲ1.0/1.2≧60%・実体0.1≦30%
    assert C.pin_dirs(10.0, 11.0, 9.8, 9.9) == {"short"}        # 上ヒゲ1.0/1.2
    assert C.pin_dirs(10.0, 10.6, 9.0, 10.5) == set()           # 実体0.5/1.6＞30%
    assert C.pin_dirs(10.0, 10.0, 10.0, 10.0) == set()          # 長さ0
    assert C.pin_dirs(10.0, 10.3, 9.6, 10.05) == set()          # 下ヒゲ0.4/0.7＜60%


def test_engulfing():
    p_red, b_green = (10.0, 10.1, 9.7, 9.8), (9.7, 10.3, 9.6, 10.2)
    assert C.engulf_dirs(p_red, b_green) == {"long"}
    p_green, b_red = (9.8, 10.1, 9.7, 10.0), (10.1, 10.2, 9.5, 9.7)
    assert C.engulf_dirs(p_green, b_red) == {"short"}
    assert C.engulf_dirs(p_red, (9.9, 10.3, 9.6, 10.2)) == set()   # B の始値がPの終値より上＝包んでいない
    assert C.engulf_dirs(p_green, b_green) == set()                # Pも陽線


def test_classify_prefers_same_direction():
    p_red, b_green_pin = (10.0, 10.1, 9.7, 9.8), (9.75, 10.3, 9.0, 10.2)
    c = C.classify(p_red, b_green_pin, "long")
    assert c["bucket"] == "same" and c["engulf"]
    assert C.classify(p_red, (10.0, 10.2, 9.0, 10.1), "short")["bucket"] == "opposite"   # 下ヒゲのピンバーに売り
    assert C.classify((10.0, 10.2, 9.9, 10.1), (10.1, 10.3, 10.0, 10.2), "long")["bucket"] == "none"


def _bars(start, n, freq, tz):
    ix = pd.date_range(start, periods=n, freq=freq, tz=tz)
    return pd.DataFrame({"Open": range(n), "High": [x + 2 for x in range(n)], "Low": [x - 1 for x in range(n)],
                         "Close": [x + 1 for x in range(n)]}, index=ix)


def test_last_closed_never_uses_the_forming_bar():
    b = _bars("2026-09-28 00:00", 6, "1h", "UTC")
    p, bb = C.last_closed(b, pd.Timestamp("2026-09-28 03:30", tz="UTC"), pd.Timedelta(hours=1))
    assert bb[0] == 2 and p[0] == 1                 # 03:00 の足は作りかけ＝使わない。02:00 の足が最後の確定足
    p, bb = C.last_closed(b, pd.Timestamp("2026-09-28 12:00", tz="Asia/Tokyo"), pd.Timedelta(hours=1))
    assert bb[0] == 2                                # 日本時間12時＝協定世界時3時ちょうど→02:00 の足は確定済み
    assert C.last_closed(b, pd.Timestamp("2026-09-28 01:30", tz="UTC"), pd.Timedelta(hours=1)) is None


def test_4h_bins_follow_the_engine_origin():
    h1 = _bars("2026-09-01 00:00", 24 * 40, "1h", "Europe/London")
    fired = pd.Timestamp("2026-09-30 10:00", tz="Asia/Tokyo")
    origin = C.engine_origin(fired, h1.index.tz)
    assert origin == pd.Timestamp("2026-08-31 00:00", tz="Europe/London")
    r4 = C.resample_4h(h1, origin)
    assert all(t.hour % 4 == 0 for t in r4.index)    # 夏時間の中では現地0時起点の4時間ごと
    got = C.last_closed(r4, fired, pd.Timedelta(hours=4))
    assert got is not None


def test_verdict_rules():
    assert C.verdict(99, 0.2, 0.1, 0.3, 0.2, 0.2) == "件数不足"
    assert C.verdict(150, 0.06, 0.01, 0.11, 0.05, 0.07).startswith("兆し")
    assert C.verdict(150, 0.04, 0.01, 0.07, 0.05, 0.03) == "差なし"      # 5ポイント未満
    assert C.verdict(150, 0.06, 0.01, 0.11, -0.01, 0.12) == "差なし"     # 前半がマイナス
    assert C.verdict(150, -0.06, -0.11, -0.01, -0.05, -0.07).startswith("逆")


def test_run_with_made_up_prices():
    def fetcher(t, interval):
        if interval == "1h":
            return _bars("2026-06-01 00:00", 24 * 60, "1h", "Europe/London")
        return _bars("2026-03-01", 200, "D", None)

    rows = []
    for i in range(12):
        day = f"2026-07-{i + 10:02d}"
        for tf in ("1h", "4h", "1d"):
            rows.append({"d": {"fired_at": f"{day}T12:05:00+09:00", "timeframe": tf}, "win": i % 2, "r": 1.0,
                         "xw": 0.1 if i % 2 else -0.1, "xr": 0.0, "ticker": "USDJPY=X", "date": day,
                         "stratum": (tf, "mr", "long", "fx"), "fam": "mr"})
    rows.append({"d": {"fired_at": "2026-07-10T12:05:00+09:00", "timeframe": "1h"}, "win": 1, "r": 1.0, "xw": 0.1,
                 "xr": 0.0, "ticker": "USDJPY=X", "date": "2026-07-10", "stratum": ("1h", "mr", "?", "fx"), "fam": "mr"})
    res = C.run(rows, C.Prices(fetcher))
    assert res["n_used"] == 36 and res["skipped"] == {"向きが無い": 1}
    assert sum(res["share"].values()) == 36
    assert C.render({**res, "generated_at": "x", "prereg_sha256": "0" * 64}).startswith("# C1")


if __name__ == "__main__":
    fails = 0
    tests = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for name, fn in tests:
        try:
            fn()
            print(f"  ✅ {name}")
        except Exception as e:  # noqa: BLE001
            fails += 1
            print(f"  ❌ {name}: {type(e).__name__}: {e}")
    print(f"--- {len(tests) - fails}/{len(tests)} 合格 ---")
    sys.exit(1 if fails else 0)
