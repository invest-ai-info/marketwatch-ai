# -*- coding: utf-8 -*-
"""トップの価格の帯・カードの「前日比」が、いつも「前の取引日の終値」との比べになるかのテスト。2026-11-05 新設。

事故: 2026-11-05 12:47 JST の生成で 金 ▲5.20%・WTI原油 ▼9.52%・ビットコイン ▲4.15% と出た。どれも2日前の
終値との比べだった。原因は ①Yahoo の日足に行の抜け・空の終値（BTC-USD の 11/4 など）がある
②CME 先物は米東部18時からの夜間セッションが24時まで「当日の行」に入り、当日の清算値が日足から消える。

固定すること: 日足に抜けがあっても2日前と比べない／先物の夜間セッション中は当日の清算値（無ければ
米東部17時の最後の値）と比べる／取れないときは前日比を出さない（帯は「―」）／ふだんの日は今までと同じ数字で、
余分な通信をしない／祝日明けは抜けと見なさない。
下の BEFORE_AFTER は 11/5 12:47 JST の入力を再現したもの（直す前の数字は直す前の計算をそのまま写して出す）。

実行:  python tests/test_price_prev_close.py     （pytest 不要。pytest でも動く）
"""
import os
import sys
from datetime import date, datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import generate_market_news as M  # noqa: E402

ET = timezone(timedelta(hours=-5))   # 11月の米東部（標準時）
D = date


def _days(a, b):
    out, d = [], a
    while d <= b:
        out.append(d)
        d += timedelta(days=1)
    return out


class _Fetch:
    """取得関数の代わり。呼ばれた回数を数える（ふだんの日に余分な通信をしないことの確認用）。"""

    def __init__(self, value=None, error=None):
        self.value, self.error, self.calls = value, error, 0

    def __call__(self, *args):
        self.calls += 1
        if self.error:
            raise self.error
        return self.value


def _pct(picked):
    last, prev, _how = picked
    return None if prev is None else (last - prev) / prev * 100


def _old_pct(bars):
    """直す前の get_price の計算（終値の列の「最後の2つの違う値」）。比べのためだけに写す。"""
    vals = [c for _d, c in bars]
    last = vals[-1]
    for v in reversed(vals[:-1]):
        if v != last:
            return (last - v) / v * 100
    return None


# ── 11/5 12:47 JST の入力 ─────────────────────────────────────────
GOLD = [(D(2026, 11, 2), 3969.6), (D(2026, 11, 3), 3940.4), (D(2026, 11, 4), 4145.2)]   # 11/4 の行＝夜間の最新値
OIL = [(D(2026, 11, 2), 96.46), (D(2026, 11, 3), 96.09), (D(2026, 11, 4), 86.94)]
BTC = [(D(2026, 11, 1), 78248.45), (D(2026, 11, 2), 76677.3), (D(2026, 11, 3), 77345.05),
       (D(2026, 11, 5), 80553.0)]                                                        # 11/4 の終値が空
CME_DAYS = _days(D(2026, 11, 1), D(2026, 11, 4))          # Yahoo の先物の取引日の一覧（日曜も入る）
NOW_ET = datetime(2026, 11, 4, 22, 47, tzinfo=ET)          # = 11/5 12:47 JST
NOW_UTC = datetime(2026, 11, 5, 3, 47, tzinfo=timezone.utc)
HOURLY_GOLD = [(datetime(2026, 11, 4, 15, tzinfo=ET), 4069.0), (datetime(2026, 11, 4, 16, tzinfo=ET), 4072.2),
               (datetime(2026, 11, 4, 18, tzinfo=ET), 4101.0), (datetime(2026, 11, 4, 22, tzinfo=ET), 4145.2)]


def test_gold_evening_uses_that_days_close_not_two_days_ago():
    stale_yahoo = _Fetch(3940.4)   # Yahoo も暦日で区切るので前々日の清算値を返しうる＝使わない
    session = _Fetch(M._session_close_from_hourly(HOURLY_GOLD, D(2026, 11, 4)))
    got = M.choose_prev_close("GC=F", GOLD, CME_DAYS, NOW_ET, stale_yahoo, session)
    assert got[1:] == (4072.2, "session-close"), got
    assert round(_old_pct(GOLD), 2) == 5.20                 # 直す前（事故の数字）
    assert abs(_pct(got) - 1.79) < 0.01, _pct(got)          # 直した後


def test_gold_evening_prefers_settlement_when_yahoo_has_it():
    session = _Fetch(4072.2)
    got = M.choose_prev_close("GC=F", GOLD, CME_DAYS, NOW_ET, _Fetch(4073.0), session)
    assert got[1:] == (4073.0, "yahoo-prev") and session.calls == 0, got
    assert abs(_pct(got) - 1.77) < 0.01


def test_oil_evening():
    got = M.choose_prev_close("CL=F", OIL, CME_DAYS, NOW_ET, _Fetch(96.09), _Fetch(88.04))
    assert round(_old_pct(OIL), 2) == -9.52
    assert got[1:] == (88.04, "session-close") and abs(_pct(got) + 1.25) < 0.01, got


def test_futures_evening_without_any_source_shows_dash():
    got = M.choose_prev_close("GC=F", GOLD, CME_DAYS, NOW_ET, _Fetch(error=OSError("x")), _Fetch(None))
    assert got == (4145.2, None, "unknown"), got


def test_futures_evening_rejects_value_equal_to_live_price():
    got = M.choose_prev_close("GC=F", GOLD, CME_DAYS, NOW_ET, _Fetch(4145.2), _Fetch(4072.2))
    assert got[1:] == (4072.2, "session-close"), got


def test_btc_missing_day_uses_yahoo_prev():
    yahoo = _Fetch(80428.305)
    got = M.choose_prev_close("BTC-USD", BTC, _days(D(2026, 11, 1), D(2026, 11, 5)), NOW_UTC, yahoo)
    assert round(_old_pct(BTC), 2) == 4.15
    assert got[1:] == (80428.305, "yahoo-prev") and abs(_pct(got) - 0.155) < 0.01, got


def test_btc_missing_day_stale_or_failed_yahoo_shows_dash():
    for f in (_Fetch(77345.05), _Fetch(None), _Fetch(error=TimeoutError("t"))):
        got = M.choose_prev_close("BTC-USD", BTC, None, NOW_UTC, f)
        assert got == (80553.0, None, "unknown"), got


def test_normal_days_keep_daily_numbers_without_extra_fetch():
    dow = [(D(2026, 10, 30), 51770.31), (D(2026, 11, 2), 51983.98), (D(2026, 11, 3), 51786.72),
           (D(2026, 11, 4), 53356.12)]
    usdjpy = [(D(2026, 10, 30), 157.8), (D(2026, 11, 2), 157.68), (D(2026, 11, 3), 157.91),
              (D(2026, 11, 4), 158.47), (D(2026, 11, 5), 157.93)]
    gold_day = [(D(2026, 11, 3), 3940.4), (D(2026, 11, 4), 4073.0), (D(2026, 11, 5), 4132.2)]
    btc_ok = [(D(2026, 11, 3), 77345.05), (D(2026, 11, 4), 80428.3), (D(2026, 11, 5), 80553.0)]
    cases = [("^DJI", dow, datetime(2026, 11, 5, 1, 0, tzinfo=ET)),
             ("JPY=X", usdjpy, datetime(2026, 11, 5, 4, 0, tzinfo=timezone.utc)),
             ("GC=F", gold_day, datetime(2026, 11, 5, 1, 11, tzinfo=ET)),      # 先物の昼の時間帯
             ("BTC-USD", btc_ok, NOW_UTC)]
    for sym, bars, now in cases:
        y, s = _Fetch(1.0), _Fetch(1.0)
        got = M.choose_prev_close(sym, bars, None, now, y, s)
        assert got == (bars[-1][1], bars[-2][1], "daily") and y.calls == s.calls == 0, (sym, got)
        assert abs(_pct(got) - _old_pct(bars)) < 1e-12        # 正しかった銘柄は数字が変わらない


def test_holiday_is_not_a_gap_when_trading_days_known():
    # 日経平均: 11/3 は文化の日で休場。11/5 の寄り前は 11/4 と 11/2 の比べが正しい
    nk = [(D(2026, 10, 29), 64659.47), (D(2026, 10, 30), 63290.11), (D(2026, 11, 2), 63081.86),
          (D(2026, 11, 4), 62188.63)]
    tdays = [D(2026, 10, 29), D(2026, 10, 30), D(2026, 11, 2), D(2026, 11, 4), D(2026, 11, 5)]
    y = _Fetch(62188.63)   # 寄り前の Yahoo は「今日の前日終値」＝最新値そのものを返す
    got = M.choose_prev_close("^N225", nk, tdays, datetime(2026, 11, 5, 7, 17, tzinfo=timezone(timedelta(hours=9))), y)
    assert got[1:] == (63081.86, "daily") and y.calls == 0, got


def test_holiday_without_trading_days_falls_back_safely():
    nk = [(D(2026, 10, 30), 63290.11), (D(2026, 11, 2), 63081.86), (D(2026, 11, 4), 62188.63)]
    # 一覧が無い＝祝日か抜けか分からない。Yahoo の値が直前の値と同じなら祝日だったと分かる
    assert M.choose_prev_close("^N225", nk, None, None, _Fetch(63081.86))[1:] == (63081.86, "yahoo-prev")
    # 寄り前で Yahoo が最新値を返したら使わない＝出さない
    assert M.choose_prev_close("^N225", nk, None, None, _Fetch(62188.63)) == (62188.63, None, "unknown")


def test_index_missing_row_uses_yahoo_prev_and_rejects_stale():
    # 11/5 11:02 JST の実例: ^N225 の 11/4 の行が空で、11/5 の値を 11/2 と比べていた
    nk = [(D(2026, 10, 30), 63290.11), (D(2026, 11, 2), 63081.86), (D(2026, 11, 5), 61992.0)]
    tdays = [D(2026, 10, 30), D(2026, 11, 2), D(2026, 11, 4), D(2026, 11, 5)]
    got = M.choose_prev_close("^N225", nk, tdays, None, _Fetch(62188.63))
    assert got[1:] == (62188.63, "yahoo-prev") and abs(_pct(got) + 0.317) < 0.01, got
    assert M.choose_prev_close("^N225", nk, tdays, None, _Fetch(63081.86)) == (61992.0, None, "unknown")


def test_weekend_and_monday_are_not_gaps():
    fx = [(D(2026, 10, 29), 157.83), (D(2026, 10, 30), 157.8), (D(2026, 11, 2), 157.68)]
    tdays = _days(D(2026, 10, 29), D(2026, 11, 2))          # 日曜（11/1）が入っていても平日だけを見る
    assert M.choose_prev_close("JPY=X", fx, tdays, None, _Fetch(1.0))[1:] == (157.8, "daily")
    fut = [(D(2026, 10, 29), 4031.54), (D(2026, 10, 30), 3898.9)]
    sun_eve = datetime(2026, 11, 1, 20, 0, tzinfo=ET)        # 日曜夜＝前の取引日は金曜で日足どおり
    fri_eve = datetime(2026, 10, 30, 19, 0, tzinfo=ET)       # 金曜夜＝夜間セッションなし
    for now in (sun_eve, fri_eve):
        assert M.choose_prev_close("GC=F", fut, None, now, _Fetch(1.0), _Fetch(1.0))[1:] == (4031.54, "daily")


def test_futures_evening_when_yahoo_already_rolled_the_day():
    # Yahoo が夜間の値を翌日の行に入れていれば、当日の行は清算値＝日足のままで正しい
    bars = [(D(2026, 11, 3), 3940.4), (D(2026, 11, 4), 4073.0), (D(2026, 11, 5), 4145.2)]
    assert M.choose_prev_close("GC=F", bars, CME_DAYS, NOW_ET, _Fetch(1.0), _Fetch(1.0))[1:] == (4073.0, "daily")


def test_session_close_from_hourly():
    assert M._session_close_from_hourly(HOURLY_GOLD, D(2026, 11, 4)) == 4072.2
    assert M._session_close_from_hourly(HOURLY_GOLD, D(2026, 11, 3)) is None   # 16時の足が無い日は出さない


def test_duplicate_values_are_skipped_with_dates():
    bars = [(D(2026, 9, 18), 6600.0), (D(2026, 9, 19), 6650.0), (D(2026, 9, 22), 6650.0)]
    assert M._last_two_distinct_dated(bars) == ((D(2026, 9, 22), 6650.0), (D(2026, 9, 18), 6600.0))
    assert M._last_two_distinct_dated([(D(2026, 9, 22), 1.0)]) is None
    assert M.choose_prev_close("^GSPC", [], None, None) is None


def test_usable_alt_prev_rejects_bad_values():
    for v in (None, "x", 0, -1, float("nan"), float("inf")):
        assert not M._usable_alt_prev(v, GOLD, 4145.2, D(2026, 11, 4)), v


def test_get_price_wiring_with_fake_yahoo():
    """get_price が日足の空の行を落とし、取引日の一覧を読み、抜けのときだけ Yahoo の前日終値を取りに行くこと。"""
    import pandas as pd
    idx = pd.DatetimeIndex([f"2026-11-0{d} 00:00" for d in (1, 2, 3, 4, 5)]).tz_localize("UTC")
    df = pd.DataFrame({"Close": [78248.45, 76677.3, 77345.05, float("nan"), 80553.0]}, index=idx)

    class FakeTicker:
        def __init__(self, sym):
            self.history_metadata = {"tradingPeriods": pd.DataFrame(index=idx)}

        def history(self, period="5d", interval="1d"):
            return df

    calls = []
    orig_yf, orig_prev = M.yf.Ticker, M._yahoo_prev_close
    M.yf.Ticker = FakeTicker
    M._yahoo_prev_close = lambda sym: calls.append(sym) or 80428.305
    try:
        last, prev, chg = M.get_price("BTC-USD")
    finally:
        M.yf.Ticker, M._yahoo_prev_close = orig_yf, orig_prev
    assert (last, prev, calls) == (80553.0, 80428.305, ["BTC-USD"]), (last, prev, calls)
    assert abs(chg - 0.155) < 0.01


def test_band_shows_dash_when_prev_unknown():
    html = M.build_index_band({"gold": (4145.2, None, None), "oil": (86.94, 88.04, -1.25)}, {}, "中立", "😐", "#9e6a03")
    gold = html.split('<span class="ib-name">金</span>')[1].split("</a>")[0]
    assert '<span class="ib-chg">―</span>' in gold and "%" not in gold, gold
    assert "数字は前日終値比" in html


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
