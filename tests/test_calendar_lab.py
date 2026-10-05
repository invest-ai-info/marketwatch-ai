# -*- coding: utf-8 -*-
"""R3 株価指数の時間の癖（calendar_lab.py）のテスト。作った値段で、窓の日付・損益・ふつうの日との比べ・日中の向き・判定を確かめる。
2026-10-05 新設。

実行:  python tests/test_calendar_lab.py     （pytest 不要。pytest でも動く）
"""
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import calendar_lab as C  # noqa: E402


def _close(a, b, tol=1e-9):
    return abs(a - b) <= tol * max(1.0, abs(b))


def _flat_with_window_bump(d, pre, post, daily=0.0002, bump=0.003):
    """ふつうの日は毎日 daily、窓の中の日は毎日 daily+bump だけ上がる値段（対数）"""
    ym = np.asarray(d.year) * 12 + np.asarray(d.month)
    first = np.r_[0, np.flatnonzero(np.diff(ym) != 0) + 1]
    inwin = np.zeros(len(d), bool)
    for k in range(1, len(first)):
        m1 = first[k]
        inwin[max(m1 - pre, 0):m1] = True
        inwin[m1:m1 + post] = True
    lr = np.where(inwin, daily + bump, daily)
    lr[0] = 0
    return pd.Series(100 * np.exp(np.cumsum(lr)), index=d)


def test_us_window_dates():
    d = pd.bdate_range("2019-12-01", "2020-04-30")
    t = C.tom_trades(pd.Series(np.linspace(100, 110, len(d)), index=d), 1, 3, "2020-01-01")
    row = t[t["buy"] == "2020-01-30"].iloc[0]                # 1月の最後から2日目の終値で買う
    assert row["sell"] == "2020-02-05" and row["L"] == 4      # 2月の3日目の終値で売る（4日分）


def test_early_japan_window_dates():
    d = pd.bdate_range("2019-12-01", "2020-04-30")
    t = C.tom_trades(pd.Series(np.linspace(100, 110, len(d)), index=d), 5, 2, "2020-01-01")
    row = t[t["buy"] == "2020-01-24"].iloc[0]                # 1月の最後から6日目
    assert row["sell"] == "2020-02-04" and row["L"] == 7


def test_window_vs_normal_days():
    d = pd.bdate_range("2015-01-01", "2019-12-31")
    px = _flat_with_window_bump(d, 1, 3)
    t = C.tom_trades(px, 1, 3, "2015-03-01")
    diff = t["win_log"] - t["L"] * t["rest_mean"]
    assert np.allclose(diff, 4 * 0.003), diff.describe()
    r = C.tom_eval(px, {"pre": 1, "post": 3, "start": "2015-03-01", "cost": 0.0002}, np.random.default_rng(1))
    assert r["verdict"] == C.VERDICTS[0] and r["p"] < C.ALPHA


def test_no_window_effect_is_not_confirmed():
    rng = np.random.default_rng(3)
    d = pd.bdate_range("2000-01-01", "2019-12-31")
    px = pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0002, 0.01, len(d)))), index=d)
    r = C.tom_eval(px, {"pre": 1, "post": 3, "start": "2000-03-01", "cost": 0.0002}, np.random.default_rng(2))
    assert r["verdict"] != C.VERDICTS[0]


def test_costs_and_financing_are_subtracted():
    d = pd.bdate_range("2015-01-01", "2016-12-31")
    px = _flat_with_window_bump(d, 1, 3)
    t = C.tom_trades(px, 1, 3, "2015-03-01")
    r = C.tom_eval(px, {"pre": 1, "post": 3, "start": "2015-03-01", "cost": 0.0002}, np.random.default_rng(1))
    expect = (t["gross"] - 0.0002 - C.FIN_RATE * t["days"] / 365).mean()
    assert _close(r["mean"], expect) and r["mean_no_fin"] > r["mean"]


def _bars(days, x_up=True):
    rows = []
    for i, day in enumerate(days):
        base = 100.0
        for h, m in ((9, 30), (10, 30), (11, 30), (12, 30), (13, 30), (14, 30), (15, 30)):
            t = pd.Timestamp(f"{day} {h:02d}:{m:02d}", tz="America/New_York")
            if (h, m) == (9, 30):
                c = base * (1.01 if (i % 2 == 0) == x_up else 0.99)
            elif (h, m) == (15, 30):
                c = rows[-1][1] * (1.002 if i % 2 == 0 else 0.998)
            else:
                c = rows[-1][1] if rows and rows[-1][0].date() == t.date() else base
            rows.append((t, c))
        rows.append((pd.Timestamp(f"{day} 15:59", tz="America/New_York"), 100.0))   # 次の日の「前の日の終値」を100にそろえる
    idx = pd.DatetimeIndex([r[0] for r in rows]).tz_convert("UTC")
    return pd.DataFrame({"Open": [r[1] for r in rows], "Close": [r[1] for r in rows]}, index=idx)


def test_intraday_rows_and_direction():
    days = [str(x.date()) for x in pd.bdate_range("2025-01-06", periods=6)]
    rows = C.intraday_rows(_bars(days))
    assert len(rows) == 5                                     # 最初の日は前の日の終値が無い
    assert all(np.sign(rows["x"]) == np.sign(rows["y"]))      # 朝の向きと引け前の向きが同じに作ってある
    rng = np.random.default_rng(1)
    big = pd.DataFrame({"day": [f"d{i}" for i in range(400)],
                        "x": np.where(np.arange(400) % 2 == 0, 0.01, -0.01),
                        "y": np.where(np.arange(400) % 2 == 0, 0.002, -0.002)})
    r = C.intraday_eval(big, 0.0002, rng)
    assert _close(r["mean"], 0.0018) and r["hit_rate"] == 1.0 and r["p"] < C.ALPHA and r["verdict"] == C.VERDICTS[0]


def test_judge_and_data_check():
    assert C.judge(0.001, 0.0002, 0.001, 0.001, 0.001) == C.VERDICTS[0]
    assert C.judge(0.001, 0.0002, 0.001, 0.001, 0.03) == C.VERDICTS[1]
    assert C.judge(0.001, -0.0002, 0.001, 0.001, 0.001) == C.VERDICTS[2]
    assert C.judge(0.001, 0.0002, -0.001, 0.001, 0.001) == C.VERDICTS[2]
    d = pd.bdate_range("2020-01-01", periods=5)
    ok, mx, day = C.data_ok(pd.Series([100, 101, 140, 141, 142.0], index=d))
    assert not ok and day == str(d[2].date())
    assert C.data_ok(pd.Series([100, 101, 99, 100, 102.0], index=d))[0]


def test_constants_match_preregistration():
    txt = open(os.path.join(ROOT, "PILLAR_PREREG.md"), encoding="utf-8").read()
    sec = txt.split("## R3 株価指数の時間の癖", 1)[1].split("\n## ", 1)[0]
    assert "0.05÷4" in sec and C.ALPHA == 0.05 / 4
    assert "1989-01" in sec and C.TOM["Q1"]["start"] == "1989-01-01"
    assert "1992-01" in sec and C.TOM["Q2"]["start"] == C.TOM["Q3"]["start"] == "1992-01-01"
    assert "米国株 0.02%" in sec and C.TOM["Q1"]["cost"] == 0.0002 and C.Q4["cost"] == 0.0002
    assert "日本株 0.03%" in sec and C.TOM["Q2"]["cost"] == C.TOM["Q3"]["cost"] == 0.0003
    assert "年3%" in sec and C.FIN_RATE == 0.03
    assert "10,000回" in sec and C.N_BOOT == 10000
    assert "25%を超える" in sec and C.MAX_DAILY == 0.25
    assert (C.TOM["Q1"]["pre"], C.TOM["Q1"]["post"]) == (1, 3) and (C.TOM["Q3"]["pre"], C.TOM["Q3"]["post"]) == (5, 2)
    assert "2026-09" in sec and C.END == "2026-09-30"


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
