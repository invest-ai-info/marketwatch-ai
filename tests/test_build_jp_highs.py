# -*- coding: utf-8 -*-
"""build_jp_highs.py（年初来高値・上場来高値の一覧）の判定のテスト。2026-10-06 新設。

実行:  python tests/test_build_jp_highs.py     （pytest 不要。pytest でも動く）
"""
import datetime
import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_spec = importlib.util.spec_from_file_location("build_jp_highs", os.path.join(ROOT, "build_jp_highs.py"))
H = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(H)


def _days(start, n, high=100.0, close=99.0):
    """start から n 営業日ぶん（土日は気にしない）の (日付, 高値, 終値, 出来高)。"""
    d0 = datetime.date.fromisoformat(start)
    return [((d0 + datetime.timedelta(days=i)).isoformat(), high, close, 1000.0) for i in range(n)]


# ── 期間の始まり（日本の慣例） ─────────────────────────────

def test_window_april_to_december_is_this_year():
    assert H.window_start("2026-10-05") == ("2026-01-01", "年初来高値")
    assert H.window_start("2026-04-01") == ("2026-01-01", "年初来高値")
    assert H.window_start("2026-12-30") == ("2026-01-01", "年初来高値")


def test_window_january_to_march_is_last_year():
    # 1〜3月は前の年の1月1日から＝「昨年来高値」
    assert H.window_start("2027-01-05") == ("2026-01-01", "昨年来高値")
    assert H.window_start("2027-03-31") == ("2026-01-01", "昨年来高値")


# ── 年初来高値 ─────────────────────────────────────────

def test_ytd_high_detected_when_today_exceeds_window():
    bars = _days("2026-01-05", 60, high=100.0) + [("2026-10-05", 101.0, 100.5, 5000.0)]
    hit = H.ytd_high(bars, "2026-01-01")
    assert hit == {"prev_high": 100.0, "prev_high_date": "2026-01-05"}


def test_ytd_equal_is_not_update():
    # 前の高値と同じ＝「更新」ではない
    bars = _days("2026-01-05", 60, high=100.0) + [("2026-10-05", 100.0, 99.5, 5000.0)]
    assert H.ytd_high(bars, "2026-01-01") is None


def test_ytd_ignores_highs_before_window():
    # 前の年の高値（120）は 4〜12月の年初来の比べる相手に入らない
    bars = (_days("2025-06-01", 30, high=120.0, close=119.0)
            + _days("2026-01-05", 60, high=100.0) + [("2026-10-05", 101.0, 100.5, 5000.0)])
    assert H.ytd_high(bars, "2026-01-01") is not None
    # 1〜3月の慣例（前の年の1月から）なら 120 が相手になる＝更新ではない
    assert H.ytd_high(bars, "2025-01-01") is None


def test_ytd_needs_enough_prior_bars():
    # 上場直後（期間内の前の営業日が20日未満）は数えない
    bars = _days("2026-09-20", 10, high=100.0) + [("2026-10-05", 101.0, 100.5, 5000.0)]
    assert H.ytd_high(bars, "2026-01-01") is None


def test_ytd_rejects_bad_data():
    # 前の日の終値の1.5倍を超える高値＝データの誤り（ストップ高でも届かない）
    bars = _days("2026-01-05", 60, high=100.0) + [("2026-10-05", 160.0, 100.5, 5000.0)]
    assert H.ytd_high(bars, "2026-01-01") is None
    # 高値が終値より安い＝データの誤り
    bars = _days("2026-01-05", 60, high=100.0) + [("2026-10-05", 101.0, 103.0, 5000.0)]
    assert H.ytd_high(bars, "2026-01-01") is None


# ── 上場来高値（記録のある全期間） ───────────────────────────

def test_ath_uses_prior_months_and_prior_days_only():
    monthly = [("2001-01-01", 90.0, 80.0, 0.0), ("2026-09-01", 100.0, 95.0, 0.0),
               ("2026-10-01", 105.0, 104.0, 0.0)]   # その月の月足はその日の高値を含む＝使わない
    daily = _days("2024-10-07", 30, high=95.0, close=94.0) + [("2026-10-05", 101.0, 100.0, 1.0)]
    ath, prev_max, first = H.all_time_high(monthly, daily)
    assert ath is True and prev_max == 100.0 and first == "2001-01-01"


def test_ath_not_updated_when_old_high_is_higher():
    monthly = [("2000-01-01", 300.0, 250.0, 0.0), ("2026-09-01", 100.0, 95.0, 0.0)]
    daily = _days("2024-10-07", 30, high=95.0, close=94.0) + [("2026-10-05", 101.0, 100.0, 1.0)]
    ath, prev_max, _ = H.all_time_high(monthly, daily)
    assert ath is False and prev_max == 300.0


def test_ath_same_month_earlier_day_counts():
    # 同じ月の前の日の高値（日足）も比べる相手に入る
    monthly = [("2026-09-01", 100.0, 95.0, 0.0)]
    daily = [("2026-10-01", 110.0, 108.0, 1.0), ("2026-10-02", 105.0, 104.0, 1.0),
             ("2026-10-05", 106.0, 105.0, 1.0)]
    ath, prev_max, _ = H.all_time_high(monthly, daily)
    assert ath is False and prev_max == 110.0


def test_ath_without_monthly_is_unknown():
    assert H.all_time_high([], _days("2026-01-05", 30)) == (None, None, None)


def test_listing_confirmed_only_when_record_starts_after_cutoff():
    assert H.listing_confirmed("2014-03-19") is True      # 2014年上場＝記録は上場時から
    assert H.listing_confirmed("2024-12-18") is True
    # 2026-10-06 の実データ＝Yahoo の記録の始まりは銘柄ごとにばらばら（トヨタ 1999-06・小松 2000-02・カプコン 2001-02）。
    # 初版はトヨタを床にして、小松（1949年上場）などを「上場来」と誤って出した＝どれも言い切らない側
    assert H.listing_confirmed("1999-06-01") is False
    assert H.listing_confirmed("2000-02-01") is False
    assert H.listing_confirmed("2001-02-01") is False
    assert H.listing_confirmed("2003-12-01") is False
    assert H.listing_confirmed("") is False and H.listing_confirmed(None) is False   # 分からないときは言い切らない


# ── その他 ─────────────────────────────────────────────

def test_already_done_needs_same_day_and_same_rule():
    prev = {"asof": "2026-10-05", "rule": H.RULE_VERSION}
    assert H.already_done(prev, "2026-10-05") is True
    assert H.already_done(prev, "2026-10-06") is False                  # 新しい営業日＝作る
    assert H.already_done({"asof": "2026-10-05", "rule": 1}, "2026-10-05") is False   # 決まりが変わった＝作り直す
    assert H.already_done({"asof": "2026-10-05"}, "2026-10-05") is False  # 初版（rule なし）も作り直す
    assert H.already_done({}, "2026-10-05") is False
    assert H.already_done(prev, "") is False


def test_update_history_replaces_same_day_and_keeps_order():
    h = [{"date": "2026-10-01", "ytd": 3, "ath": 1}, {"date": "2026-10-02", "ytd": 5, "ath": 2}]
    h = H.update_history(h, "2026-10-02", 7, 3)
    h = H.update_history(h, "2026-10-05", 9, 4)
    assert [x["date"] for x in h] == ["2026-10-01", "2026-10-02", "2026-10-05"]
    assert h[1] == {"date": "2026-10-02", "ytd": 7, "ath": 3}


def test_update_history_keeps_last_n():
    h = []
    for i in range(H.HISTORY_KEEP + 5):
        h = H.update_history(h, (datetime.date(2025, 1, 1) + datetime.timedelta(days=i)).isoformat(), i, 0)
    assert len(h) == H.HISTORY_KEEP and h[-1]["ytd"] == H.HISTORY_KEEP + 4


def test_parse_bars_drops_missing_and_uses_jst_date():
    # 2026-10-05 00:00 UTC（＝09:00 JST）と、高値の欠けたバー
    t = int(datetime.datetime(2026, 10, 5, tzinfo=datetime.timezone.utc).timestamp())
    res = {"timestamp": [t, t + 86400],
           "indicators": {"quote": [{"high": [101.0, None], "close": [100.0, 99.0], "volume": [5, 6]}]}}
    assert H.parse_bars(res) == [("2026-10-05", 101.0, 100.0, 5.0)]


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"ok   {name}")
            except AssertionError as e:
                fails += 1
                print(f"FAIL {name}: {e}")
    print(f"{'全件緑' if not fails else f'{fails}件失敗'}")
    sys.exit(1 if fails else 0)
