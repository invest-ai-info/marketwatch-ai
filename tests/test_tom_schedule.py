# -*- coding: utf-8 -*-
"""R3F の予定表（tom_schedule.py）のテスト。取引所の暦から、前向きの観察と同じ買う日・売る日が出るかを確かめる。
2026-10-05 新設。

実行:  python tests/test_tom_schedule.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import tom_schedule as T  # noqa: E402


def _fake(name, start, end):
    d = pd.bdate_range(start, end)
    if name == "XTKS":
        d = d[d != pd.Timestamp("2026-11-03")]                    # 文化の日
    return pd.DataFrame({"close_utc": [pd.Timestamp(x).tz_localize("UTC") + pd.Timedelta(hours=20) for x in d]}, index=d)


def test_windows_match_forward_observer_rules():
    rows = T.schedule(dt.date(2026, 10, 5), 1, sched=_fake)
    q1 = [r for r in rows if r["c"] == "Q1"][0]
    q3 = [r for r in rows if r["c"] == "Q3"][0]
    assert (q1["buy"], q1["sell"]) == ("2026-10-29", "2026-11-04"), q1       # 月の最後から2日目 → 翌月の3日目
    assert (q3["buy"], q3["sell"]) == ("2026-10-23", "2026-11-04"), q3       # 最後から6日目 → 翌月の2日目（3日は休み）


def test_real_exchange_calendars():
    try:
        import pandas_market_calendars  # noqa: F401
    except ImportError:
        print("    （pandas_market_calendars が無いので省略）")
        return
    rows = T.schedule(dt.date(2026, 10, 5), 3)
    got = {(r["c"], r["buy"], r["sell"]) for r in rows}
    assert ("Q1", "2026-10-29", "2026-11-04") in got and ("Q3", "2026-10-23", "2026-11-04") in got, got
    assert ("Q1", "2026-11-27", "2026-12-03") in got                         # 感謝祭の次の日（半日）に買う
    assert ("Q3", "2026-12-23", "2027-01-05") in got                         # 大納会 12/30・大発会 1/4
    nov = [r for r in rows if r["buy"] == "2026-11-27"][0]
    assert nov["buy_close_jst"] == "2026-11-28 03:00"                        # 半日（13:00 ニューヨーク）の大引け
    jp = [r for r in rows if r["c"] == "Q3"][0]
    assert jp["buy_close_jst"].endswith("15:30")


def test_only_future_windows():
    rows = T.schedule(dt.date(2026, 10, 24), 1, sched=_fake)
    assert all(r["buy"] >= "2026-10-24" for r in rows)
    assert [r["buy"] for r in rows if r["c"] == "Q3"] == ["2026-11-23"]       # 作った暦（勤労感謝の日を入れていない）の最後から6日目


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
