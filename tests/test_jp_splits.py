# -*- coding: utf-8 -*-
"""jp_splits.py（日本株の株式分割の補正）のテスト。2026-11-19 新設。

きっかけ: キーエンス（6861）の 1→5 の分割の日（2026-11-18）、Yahoo の日足は最後の1本だけ分割後の値で、
jp-rankings.json の値下がり1位に −79.7%（本当は +1.5%）が出た。しまむら（8227）は 2026-02 の 1→3 の分割の前の足が
9か月たっても直っていなかった。どちらの形でも「直していない切れ目より前の足を分割後の単位に直す」ことと、
Yahoo がもう直している（ふつうの）形には何もしないことを固定する。

実行:  python tests/test_jp_splits.py     （pytest 不要。pytest でも動く）
"""
import datetime
import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_spec = importlib.util.spec_from_file_location("jp_splits", os.path.join(ROOT, "jp_splits.py"))
S = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(S)

JST = datetime.timezone(datetime.timedelta(hours=9))


def _ts(d):
    return int(datetime.datetime.fromisoformat(d + "T09:00:00").replace(tzinfo=JST).timestamp())


def _ev(*splits):
    """(日付, numerator, denominator) → Yahoo の events の形"""
    return {"splits": {str(_ts(d)): {"date": _ts(d), "numerator": n, "denominator": m, "splitRatio": f"{n}:{m}"}
                       for d, n, m in splits}}


def _dates(start, n):
    """start から n 営業日（土日を飛ばす）"""
    d, out = datetime.date.fromisoformat(start), []
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += datetime.timedelta(days=1)
    return out


# ── 分割の読み取り ───────────────────────────────────────

def test_parse_splits_reads_ratio_and_jst_date():
    res = {"events": _ev(("2026-11-19", 5.0, 1.0), ("2026-02-19", 3, 1))}
    assert S.parse_splits(res) == [("2026-02-19", 3.0), ("2026-11-19", 5.0)]


def test_parse_splits_keeps_reverse_split_and_drops_broken():
    res = {"events": {"splits": {
        "1": {"date": _ts("2026-06-01"), "numerator": 1, "denominator": 10},     # 併合（10株→1株）
        "2": {"date": _ts("2026-06-02"), "numerator": 1, "denominator": 1},      # 1倍＝何もしない
        "3": {"date": _ts("2026-06-03"), "numerator": 2, "denominator": 0},      # 壊れた値
        "4": {"date": _ts("2026-06-04")},                                        # 倍率が無い
    }}}
    assert S.parse_splits(res) == [("2026-06-01", 0.1)]
    assert S.parse_splits({}) == [] and S.parse_splits(None) == []


# ── 切れ目の見つけ方 ─────────────────────────────────────

def test_keyence_shape_only_last_bar_adjusted():
    # 2026-11-18 の引け：11/17 まで分割前（72,510）・11/18 だけ分割後（14,722）。分割の日付は 11/19
    dates = _dates("2026-10-20", 22)
    assert dates[-2:] == ["2026-11-17", "2026-11-18"]
    closes = [73000.0] * 20 + [72510.0, 14722.0]
    br = S.find_breaks(dates, closes, [("2026-11-19", 5.0)])
    assert br == [("2026-11-18", 5.0)]
    assert S.factor("2026-11-17", br) == 0.2 and S.factor("2026-11-18", br) == 1.0


def test_already_adjusted_series_is_left_alone():
    # Yahoo がもう全部直している（ふつうの形）＝分割の日付があっても切れ目は無い
    dates = _dates("2026-10-20", 22)
    closes = [14600.0] * 20 + [14502.0, 14722.0]
    assert S.find_breaks(dates, closes, [("2026-11-19", 5.0)]) == []


def test_ordinary_drop_is_not_mistaken_for_split():
    # 直してある足のふつうの下げ（−10%）は 1→2 の分割の切れ目にしない（直すと +80% になる＝分割ではないほうが近い）
    dates = _dates("2026-10-20", 22)
    closes = [1000.0] * 21 + [900.0]
    assert S.find_breaks(dates, closes, [("2026-11-19", 2.0)]) == []


def test_small_split_already_adjusted_by_yahoo_is_left_alone():
    # コタ（4923）の形：1→1.05 の分割（2026-03）を Yahoo は直し済み（前の足は 1425÷1.05＝1357.14… と呼値に乗らない）。
    # 03-31 の本物の −7%（1264→1176）は 1.05 の切れ目にも見えるが、直し済みなので何もしない
    dates = ["2026-03-19", "2026-03-23", "2026-03-24", "2026-03-25", "2026-03-26", "2026-03-27",
             "2026-03-30", "2026-03-31", "2026-04-01"]
    closes = [1360.0, 1356.1904296875, 1355.238037109375, 1366.6666259765625, 1368.5714111328125,
              1378.09521484375, 1264.0, 1176.0, 1197.0]
    assert S.find_breaks(dates, closes, [("2026-03-30", 1.05)]) == []
    # 前の足が呼値に乗る（生の値段）なら止めない＝直していない切れ目として扱う（3/30 に 1447→1380 ＝ちょうど 1.05 で割った値）
    raw = [1428.0, 1424.0, 1423.0, 1435.0, 1437.0, 1447.0, 1380.0, 1380.0, 1380.0]
    assert S.find_breaks(dates, raw, [("2026-03-30", 1.05)]) == [("2026-03-30", 1.05)]


def test_on_tick():
    assert S.on_tick(11040.0) and S.on_tick(512.29998779296875) and S.on_tick(2345.5) and S.on_tick(72510.0)
    assert not S.on_tick(1357.142822265625) and not S.on_tick(3713.333251953125)
    assert not S.already_adjusted([11040.0, 11050.0]) and S.already_adjusted([1357.1428, 1356.19, 1360.0])
    assert not S.already_adjusted([])


def test_unadjusted_break_found_long_after_the_split():
    # しまむらの形：2026-02-19 の 1→3 の分割の前の足が、何か月たっても分割前の単位のまま（切れ目は 02-18）
    dates = _dates("2026-01-05", 120)
    i = dates.index("2026-02-18")
    closes = [11040.0] * i + [3713.3] + [3600.0] * (len(dates) - i - 1)
    br = S.find_breaks(dates, closes, [("2026-02-19", 3.0)])
    assert br == [("2026-02-18", 3.0)]


def test_break_far_from_split_date_is_ignored():
    # 分割の日付から離れたところの大きな切れ目は分割のせいにしない（日付の前後 SPLIT_BEFORE〜SPLIT_AFTER 暦日だけ見る）
    dates = _dates("2026-01-05", 60)
    closes = [1000.0] * 30 + [200.0] * 30
    assert S.find_breaks(dates, closes, [("2026-11-19", 5.0)]) == []


def test_reverse_split_break():
    # 併合（10株→1株＝倍率 0.1）：分割前の単位のままの足は値段が1/10
    dates = _dates("2026-10-20", 22)
    closes = [50.0] * 21 + [505.0]
    br = S.find_breaks(dates, closes, [("2026-11-19", 0.1)])
    assert br == [("2026-11-18", 0.1)]
    assert abs(S.factor("2026-11-17", br) - 10.0) < 1e-9


def test_two_splits_each_get_their_own_break():
    dates = _dates("2026-01-05", 200)
    a, b = dates.index("2026-03-27"), dates.index("2026-09-28")
    closes = [6000.0] * a + [3000.0] * (b - a) + [1000.0] * (len(dates) - b)
    br = S.find_breaks(dates, closes, [("2026-03-30", 2.0), ("2026-09-29", 3.0)])
    assert br == [("2026-03-27", 2.0), ("2026-09-28", 3.0)]
    assert abs(S.factor("2026-01-05", br) - 1 / 6) < 1e-12


def test_near_uses_same_window():
    sp = [("2026-11-19", 5.0)]
    assert S.near("2026-11-18", sp) and S.near("2026-11-11", sp) and S.near("2026-11-22", sp)
    assert not S.near("2026-11-10", sp) and not S.near("2026-11-23", sp) and not S.near("2026-11-18", [])


# ── 足の直し方 ───────────────────────────────────────────

def test_adjust_hlcv_keeps_turnover():
    bars = [("2026-11-16", 73700.0, 73200.0, 73450.0, 566400.0),
            ("2026-11-17", 73350.0, 71930.0, 72510.0, 614800.0),
            ("2026-11-18", 14736.0, 14410.0, 14722.0, 3050000.0)]
    out, br = S.adjust_hlcv(bars, [("2026-11-19", 5.0)])
    assert br == [("2026-11-18", 5.0)]
    d, h, lo, c, v = out[1]
    assert (d, round(h, 1), round(lo, 1), round(c, 1), v) == ("2026-11-17", 14670.0, 14386.0, 14502.0, 3074000.0)
    assert abs(c * v - 72510.0 * 614800.0) < 1e-3      # 売買代金（終値×出来高）は変わらない
    assert out[2] == bars[2]


def test_adjust_hlcv_monthly_mixed_bar():
    # 月足：分割のあった月の足は高値が分割前の単位のまま（キーエンス 2026年11月＝高値 77,630・安値 14,410・終値 14,722）
    bars = [("2026-09-01", 83490.0, 73510.0, 80480.0, 11095700.0),
            ("2026-10-01", 82940.0, 76360.0, 78000.0, 13482900.0),
            ("2026-11-01", 77630.0, 14410.0, 14722.0, 11117000.0)]
    out, br = S.adjust_hlcv(bars, [("2026-11-19", 5.0)])
    assert br == [("2026-11-01", 5.0)]
    assert round(out[1][1], 1) == 16588.0 and round(out[1][3], 1) == 15600.0
    assert round(out[2][1], 1) == 15526.0 and out[2][2] == 14410.0 and out[2][3] == 14722.0


def test_adjust_hlcv_without_splits_returns_same_list():
    bars = [("2026-11-17", 101.0, 99.0, 100.0, 10.0), ("2026-11-18", 102.0, 98.0, 50.0, 10.0)]
    out, br = S.adjust_hlcv(bars, [])
    assert out is bars and br == []


def test_breaks_of_reads_result():
    dates = ["2026-11-16", "2026-11-17", "2026-11-18"]
    res = {"timestamp": [_ts(d) for d in dates], "events": _ev(("2026-11-19", 5, 1)),
           "indicators": {"quote": [{"close": [73450.0, 72510.0, 14722.0]}]}}
    assert S.breaks_of(res) == [("2026-11-18", 5.0)]
    res.pop("events")
    assert S.breaks_of(res) == []



# ── 数日だけの値の誤り・日中足・ほかの形（2026-11-19 同日夕） ─────────────

def test_glitch_that_reverts_is_not_a_split():
    # 1321.T の形：Yahoo に「100:1 の分割」があるが、値は 10-05・06 の2日だけ 1/100 で 10-07 に戻る＝分割ではない。
    # 直すと 10-05 より前が全部 1/100 になる＝何もしない
    dates = ["2026-09-30", "2026-10-01", "2026-10-02", "2026-10-05", "2026-10-06", "2026-10-07", "2026-10-08"]
    closes = [705.0, 708.0, 710.4, 7.279, 7.351, 729.7, 731.0]
    assert S.find_breaks(dates, closes, [("2026-10-05", 100.0)]) == []
    # 戻らなければ（本物の直しもれ）直す
    closes = [705.0, 708.0, 710.4, 7.2, 7.35, 7.3, 7.31]
    assert S.find_breaks(dates, closes, [("2026-10-05", 100.0)]) == [("2026-10-05", 100.0)]


def test_one_day_glitch_before_the_candidate_is_not_a_split():
    # 1990年からの日足の点検で見つかった形：誤りの足（1日だけ半分／2倍）の次の足が「分割で落ちた／上がった」切れ目に見える
    # 三菱ケミカル（4188）：2005-09-30 だけ 1/2・分割の情報は 0.5（2005-10-03）
    dates = ["2005-09-28", "2005-09-29", "2005-09-30", "2005-10-03", "2005-10-04"]
    assert S.find_breaks(dates, [750.0, 752.0, 376.0, 815.0, 813.0], [("2005-10-03", 0.5)]) == []
    # ローツェ（6323）：2000-08-25 だけ 2倍・分割の情報は 2.0（2000-08-28）
    dates = ["2000-08-23", "2000-08-24", "2000-08-25", "2000-08-28", "2000-08-29"]
    assert S.find_breaks(dates, [113.0, 112.75, 230.0, 128.0, 125.0], [("2000-08-28", 2.0)]) == []


def test_index_factors_work_on_intraday_bars():
    # 5分足：同じ日付の足が続く。切れ目は 11/18 の最初の足（そこから分割後の単位）
    dates = ["2026-11-17"] * 3 + ["2026-11-18"] * 3
    closes = [72600.0, 72550.0, 72510.0, 14650.0, 14700.0, 14722.0]
    f, br = S.index_factors(dates, closes, [("2026-11-19", 5.0)])
    assert br == [("2026-11-18", 5.0)] and f == [0.2, 0.2, 0.2, 1.0, 1.0, 1.0]


def test_adjust_ohlcv_keeps_none_open_and_scales_volume():
    import datetime as _dt
    t = [_dt.datetime(2026, 11, d, 9, 0, tzinfo=JST) for d in (16, 17, 18)]
    rows = [(t[0], 73500.0, 73700.0, 73200.0, 73450.0, 566400.0),
            (t[1], 73000.0, 73350.0, 71930.0, 72510.0, 614800.0),
            (t[2], None, 14736.0, 14410.0, 14722.0, 3050000.0)]
    out, br = S.adjust_ohlcv(rows, [("2026-11-19", 5.0)])
    assert br == [("2026-11-18", 5.0)]
    assert out[1] == (t[1], 14600.0, 14670.0, 14386.0, 14502.0, 3074000.0) and out[2] == rows[2]
    assert S.adjust_ohlcv(rows, []) == (rows, [])


def test_adjust_close_volume():
    c, v, br = S.adjust_close_volume(["2026-11-17", "2026-11-18"], [72510.0, 14722.0], [614800.0, None], [("2026-11-19", 5.0)])
    assert br == [("2026-11-18", 5.0)] and c == [14502.0, 14722.0] and v == [3074000.0, None]
    c, v, br = S.adjust_close_volume(["2026-11-17", "2026-11-18"], [14502.0, 14722.0], [1.0, 2.0], [("2026-11-19", 5.0)])
    assert br == [] and c == [14502.0, 14722.0] and v == [1.0, 2.0]


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
