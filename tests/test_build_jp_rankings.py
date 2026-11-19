# -*- coding: utf-8 -*-
"""build_jp_rankings.py の「書かずに次の回へ委ねる」判定のテスト。2026-09-25 新設。
2026-11-19 株式分割の日の前日比・相対出来高のテストを追加（キーエンス 6861 の 1→5）。

jp-rankings.yml を routine の push でも起動するようにした（cron が約5時間遅れていたため）ので、
起動時刻がこちらの管理外になった。場中に走っても途中の値を「終値」として書かないことを固定する。

実行:  python tests/test_build_jp_rankings.py     （pytest 不要。pytest でも動く）
"""
import datetime
import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_spec = importlib.util.spec_from_file_location("build_jp_rankings", os.path.join(ROOT, "build_jp_rankings.py"))
B = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(B)

JST = datetime.timezone(datetime.timedelta(hours=9))


def _at(hh, mm, day=25):
    return datetime.datetime(2026, 9, day, hh, mm, tzinfo=JST)


def test_unsettled_during_session():
    # 場中・大引け直後に取れた当日バーは書かない
    assert B.is_unsettled("2026-09-25", _at(11, 0))
    assert B.is_unsettled("2026-09-25", _at(15, 45))


def test_settled_after_close():
    # routine の push（17:48〜 / 19:09〜）と遅れた cron（21〜23時台）は書く
    assert not B.is_unsettled("2026-09-25", _at(16, 0))
    assert not B.is_unsettled("2026-09-25", _at(17, 50))
    assert not B.is_unsettled("2026-09-25", _at(21, 58))


def test_previous_day_bar_is_not_unsettled():
    # 朝の sns の回（07:10）は前営業日のバー＝確定済み。巻き戻しかどうかは is_regression が見る
    assert not B.is_unsettled("2026-09-24", _at(7, 10))
    assert not B.is_unsettled("", _at(11, 0))


def test_regression_guard_unchanged():
    assert B.is_regression("2026-09-24", "2026-09-25")
    assert not B.is_regression("2026-09-25", "2026-09-25")
    assert not B.is_regression("2026-09-25", "")


def test_modal_date_prefers_majority_then_newer():
    assert B.modal_date(["2026-09-25", "2026-09-25", "2026-09-24"]) == "2026-09-25"
    assert B.modal_date(["2026-09-24", "2026-09-25"]) == "2026-09-25"
    assert B.modal_date([]) == ""


# ── 株式分割の日（2026-11-19 新設） ────────────────────────
# キーエンス（6861）の 1→5 の分割の日（11/18）、Yahoo の日足は最後の1本だけ分割後の値で、値下がり1位に −79.7%
# （本当は 72,510→73,610 の +1.5%）・人気急上昇に出来高 3.9倍（本当は売買代金 449億円 vs 446億円）が出た。

def _ts(d):
    return int(datetime.datetime.fromisoformat(d + "T09:00:00").replace(tzinfo=JST).timestamp())


def _bdays(start, n):
    d, out = datetime.date.fromisoformat(start), []
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += datetime.timedelta(days=1)
    return out


def _chart(dates, closes, vols, splits=()):
    res = {"timestamp": [_ts(d) for d in dates],
           "indicators": {"quote": [{"close": list(closes), "volume": list(vols)}]}}
    if splits:
        res["events"] = {"splits": {str(_ts(d)): {"date": _ts(d), "numerator": r, "denominator": 1.0}
                                    for d, r in splits}}
    return res


def _keyence(extra=()):
    """11/18 の引けの形（11/17 まで分割前・11/18 だけ分割後）。extra＝そのあとの (日付, 終値, 出来高)"""
    dates = _bdays("2026-10-19", 23)
    assert dates[-1] == "2026-11-18"
    closes = [73000.0] * 21 + [72510.0, 14722.0]
    vols = [782000.0] * 21 + [614800.0, 3050000.0]
    for d, c, v in extra:
        dates.append(d)
        closes.append(c)
        vols.append(v)
    return _chart(dates, closes, vols, [("2026-11-19", 5.0)])


def test_split_day_pct_and_relvol_are_fixed():
    closes, vols, last, splits, breaks, _pend = B.parse_chart(_keyence())
    assert last == "2026-11-18" and breaks == [("2026-11-18", 5.0)]
    row = B.stock_row("6861", {"name": "キーエンス"}, closes, vols, last)
    assert row["pct"] == 0.0152                      # 14,722 ÷ (72,510÷5) − 1（補正なしだと −0.797）
    assert row["relvol"] == 0.8                      # 3,050,000 ÷ (782,000×5)（補正なしだと 3.9）
    assert row["turnover_d1"] == 449.0 and row["turnover_d2"] == 445.8   # 売買代金は補正の前後で同じ
    assert not B.split_suspect(closes, last, splits)


def test_day_after_split_relvol_uses_adjusted_base():
    # 次の日も前の足が分割前のまま（しまむらは9か月そのまま）＝基準の20日の出来高を直さないと倍率が膨らむ
    closes, vols, last, _, breaks, _pend = B.parse_chart(_keyence([("2026-11-19", 14675.0, 1500000.0)]))
    assert breaks == [("2026-11-18", 5.0)]
    row = B.stock_row("6861", {}, closes, vols, last)
    assert row["pct"] == round(14675.0 / 14722.0 - 1, 4)
    assert row["relvol"] == 0.4                      # 補正なしだと 1.7


def test_no_split_event_keeps_raw_values():
    dates = _bdays("2026-10-19", 23)
    closes, vols, last, splits, breaks, _pend = B.parse_chart(_chart(dates, [100.0] * 22 + [60.0], [1000.0] * 22 + [4000.0]))
    assert splits == [] and breaks == []
    row = B.stock_row("1111", {}, closes, vols, last)
    assert row["pct"] == -0.4 and row["relvol"] == 4.0       # 分割が無ければ極端な値動きもそのまま（本物でありうる）
    assert not B.split_suspect(closes, last, splits)


def test_extreme_move_near_split_that_cannot_be_fixed_is_suspect():
    # Yahoo の倍率（×2）と値の切れ目（1/5）が合わない＝直せない＝分割の日付の前後の極端な前日比は一覧に入れない
    dates = _bdays("2026-10-19", 23)
    res = _chart(dates, [73000.0] * 22 + [14722.0], [782000.0] * 22 + [3050000.0], [("2026-11-19", 2.0)])
    closes, vols, last, splits, breaks, _pend = B.parse_chart(res)
    assert breaks == [] and B.split_suspect(closes, last, splits)
    # 分割の日付から離れていれば対象外（分割と重ならない極端な値動きは本物でありうる）
    res = _chart(dates, [73000.0] * 22 + [14722.0], [782000.0] * 22 + [3050000.0], [("2026-08-20", 2.0)])
    closes, vols, last, splits, _, _pend = B.parse_chart(res)
    assert not B.split_suspect(closes, last, splits)


def test_parse_chart_drops_missing_closes_and_needs_two_bars():
    dates = _bdays("2026-11-16", 3)
    closes, vols, last, _, _, _pend = B.parse_chart(_chart(dates, [100.0, None, 101.0], [10, 20, None]))
    assert closes == [100.0, 101.0] and vols == [10.0, None] and last == "2026-11-18"
    assert B.parse_chart(_chart(dates[:1], [100.0], [10])) is None



def test_unit_shift_not_yet_reverted_is_left_out():
    # 🆕 2026-11-19 いちばん新しい足だけ 1/10（単位のずれ・分割の情報なし）＝値段の単位が決められない＝一覧に出さない
    dates = _bdays("2026-10-19", 23)
    closes, vols, last, splits, breaks, pending = B.parse_chart(
        _chart(dates, [3800.0] * 22 + [381.0], [1000.0] * 22 + [10000.0]))
    assert pending and splits == []
    # 2日で戻った誤り（1306.T の形）は直して出す
    closes, vols, last, splits, breaks, pending = B.parse_chart(
        _chart(dates, [3800.0] * 20 + [381.0, 379.0, 3820.0], [1000.0] * 20 + [10000.0, 10000.0, 1100.0]))
    assert not pending and [round(c) for c in closes[-4:]] == [3800, 3810, 3790, 3820] and vols[-2] == 1000.0


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
