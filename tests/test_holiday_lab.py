# -*- coding: utf-8 -*-
"""R5 日本の祝日の前の日（holiday_lab.py）のテスト。2026-10-05 新設。

実行:  python tests/test_holiday_lab.py     （pytest 不要。pytest でも動く）
"""
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import holiday_lab as H  # noqa: E402


def _calendar(start="2000-01-03", end="2012-12-28", holidays_every=20, long_every=200):
    """平日のうち、holidays_every 日ごとに1日、long_every 日ごとに3日続けて休む作り物の暦"""
    wd = pd.bdate_range(start, end)
    closed = set()
    for i in range(10, len(wd), holidays_every):
        closed.add(wd[i])
    for i in range(50, len(wd), long_every):
        closed.update(wd[i:i + 3])
    return pd.DatetimeIndex([d for d in wd if d not in closed])


def _prices(tdays, pre_bump=0.0, seed=1, sd=0.0):
    rng = np.random.default_rng(seed)
    tset = set(tdays)
    lr = []
    for i, t in enumerate(tdays):
        nxt = t + pd.Timedelta(days=1)
        while nxt.weekday() >= 5:
            nxt += pd.Timedelta(days=1)
        pre = nxt not in tset
        lr.append(0.0003 + (pre_bump if pre else 0.0) + (rng.normal(0, sd) if sd else 0.0))
    lr[0] = 0.0
    return pd.Series(100 * np.exp(np.cumsum(lr)), index=tdays)


def test_pre_holiday_and_long_break_flags():
    td = _calendar()
    df = H.holiday_rows(_prices(td), td, "2000-02-01", "2012-12-01", H.COST_JP)
    assert df["pre"].sum() > 100 and (df["closed"] >= H.LONG_BREAK).sum() >= 10
    assert set(df.loc[df["closed"] >= 3, "closed"]) <= {3, 4}          # 3日続く休み（週末をまたげば数え方は平日だけ）


def test_friday_before_monday_holiday_counts_and_holds_three_nights():
    td = pd.DatetimeIndex([d for d in pd.bdate_range("2021-01-04", "2021-02-26") if d != pd.Timestamp("2021-01-18")])
    df = H.holiday_rows(_prices(td), td, "2021-01-05", "2021-02-25", H.COST_JP)
    fri = df[df["date"] == "2021-01-15"].iloc[0]
    assert bool(fri["pre"]) and fri["closed"] == 1
    tue = df[df["date"] == "2021-01-19"].iloc[0]
    assert tue["days"] == 4                                            # 1/15(金)→1/19(火)は休みをまたぐ（数えるのは前の取引日から）
    mon = df[df["date"] == "2021-01-11"].iloc[0]
    assert mon["days"] == 3 and abs(mon["net"] - (mon["gross"] - H.COST_JP - H.FIN_RATE * 3 / 365)) < 1e-12


def test_bump_on_pre_holiday_is_found_and_noise_is_not():
    td = _calendar()
    rng = np.random.default_rng(3)
    df = H.holiday_rows(_prices(td, pre_bump=0.004, sd=0.002), td, "2000-02-01", "2012-12-01", H.COST_JP)
    r = H.evaluate(df, df["pre"], rng, n=500)
    assert r["verdict"] == H.VERDICTS[0] and r["p"] < H.ALPHA and r["diff"] > 0.003
    df2 = H.holiday_rows(_prices(td, pre_bump=0.0, sd=0.01, seed=9), td, "2000-02-01", "2012-12-01", H.COST_JP)
    r2 = H.evaluate(df2, df2["pre"], rng, n=500)
    assert r2["verdict"] != H.VERDICTS[0]


def test_judge_rules():
    base = {"mean": 0.002, "lo": 0.0005, "first": 0.002, "second": 0.001, "p": 0.001}
    assert H.judge(base) == H.VERDICTS[0]
    assert H.judge(dict(base, p=0.04)) == H.VERDICTS[1]
    assert H.judge(dict(base, p=0.2)) == H.VERDICTS[2]
    assert H.judge(dict(base, second=-0.001)) == H.VERDICTS[2]
    assert H.judge(dict(base, lo=-0.0001)) == H.VERDICTS[2]


def test_exchange_calendar_known_dates():
    td = set(H.exchange_days("XTKS", "2019-04-01", "2025-01-31"))
    for d in ("2019-04-29", "2019-04-30", "2019-05-01", "2019-05-02", "2019-05-06", "2024-05-03", "2024-12-31", "2025-01-03"):
        assert pd.Timestamp(d) not in td, d
    for d in ("2019-05-07", "2024-12-30", "2025-01-06"):
        assert pd.Timestamp(d) in td, d


def test_constants_match_preregistration():
    txt = open(os.path.join(ROOT, "PILLAR_PREREG.md"), encoding="utf-8").read()
    sec = txt.split("## R5 日本の祝日の前の日", 1)[1].split("\n## ", 1)[0]
    assert "1992-01〜2026-09" in sec and (H.START, H.END) == ("1992-01-01", "2026-09-30")
    assert "往復 0.03%" in sec and H.COST_JP == 0.0003 and "年3%" in sec and H.FIN_RATE == 0.03
    assert "0.05÷2" in sec and H.ALPHA == 0.05 / 2 and "10,000回" in sec and H.N_BOOT == 10000
    assert "2日以上" in sec and H.LONG_BREAK == 2 and "25%を超える" in sec


if __name__ == "__main__":
    fails = 0
    tests = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for name, fn in tests:
        try:
            fn()
            print(f"  ✅ {name}")
        except AssertionError as e:
            fails += 1
            print(f"  ❌ {name}: {e}")
    print(f"--- {len(tests) - fails}/{len(tests)} 合格 ---")
    sys.exit(1 if fails else 0)
