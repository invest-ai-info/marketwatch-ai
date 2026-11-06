# -*- coding: utf-8 -*-
"""見張り番 ⑫・⑫c（日本株ランキング・高値安値の一覧の鮮度）が求める営業日のテスト。2026-11-06 新設。

動機: 番人の cron は 09:30 JST だが実際は 15:47〜16:07 JST に走っていた（11/4・11/5）。当日の足は 15:30 に確定する一方、
一覧（jp-rankings.json 17:52・jp-highs.json 18:04〜18:15 JST）はまだ前の営業日＝2日続けて「古い」と誤検知した。
一覧には JP_LISTS_READY_JST より前なら前の営業日を求める。信用残（⑫b）は今までどおり 15:30 の確定で数える。

実行:  python tests/test_health_jp_lists.py     （pytest 不要。pytest でも動く）
"""
import datetime
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import check_automation_health as H  # noqa: E402

DATES = ["2026-10-30", "2026-11-02", "2026-11-04", "2026-11-05"]       # 11/3 は文化の日


def _jst(y, m, d, hh, mm):
    return datetime.datetime(y, m, d, hh, mm, tzinfo=datetime.timezone(datetime.timedelta(hours=9)))


def test_the_two_false_alarms_are_gone():
    # 11/5 16:07 JST（実際に番人が走った時刻）: 当日の足は確定・一覧は前の営業日 11/4 で正常
    now = _jst(2026, 11, 5, 16, 7)
    assert H.latest_settled_trading_date(DATES, now) == "2026-11-05"
    assert H.expected_list_date(DATES, now) == "2026-11-04"
    # 11/4 15:47 JST も同じ
    assert H.expected_list_date(DATES[:3], _jst(2026, 11, 4, 15, 47)) == "2026-11-02"


def test_lists_are_expected_for_today_after_the_evening_build():
    assert H.expected_list_date(DATES, _jst(2026, 11, 5, 20, 29)) == "2026-11-04"
    assert H.expected_list_date(DATES, _jst(2026, 11, 5, 20, 30)) == "2026-11-05"
    assert H.expected_list_date(DATES, _jst(2026, 11, 6, 9, 30)) == "2026-11-05"   # 翌朝（当日の足がまだ無い）


def test_a_real_miss_is_still_caught():
    # 11/5 の夕方の回が当日分を作れず、翌日 16:00 にも一覧が 11/4 のまま → 求める日は 11/5 なので鳴る
    dates = DATES + ["2026-11-06"]
    assert H.expected_list_date(dates, _jst(2026, 11, 6, 16, 0)) == "2026-11-05" > "2026-11-04"


def test_morning_open_bar_is_dropped_as_before():
    dates = DATES + ["2026-11-06"]                                                    # 場中の未確定の足
    assert H.latest_settled_trading_date(dates, _jst(2026, 11, 6, 9, 30)) == "2026-11-05"
    assert H.expected_list_date(dates, _jst(2026, 11, 6, 9, 30)) == "2026-11-05"
    assert H.expected_list_date([], _jst(2026, 11, 6, 9, 30)) is None
    assert H.expected_list_date(["2026-11-06"], _jst(2026, 11, 6, 9, 30)) is None


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
