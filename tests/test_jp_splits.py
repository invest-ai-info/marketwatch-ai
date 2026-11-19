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


def test_monthly_bars_are_not_searched_for_splits():
    # 月足では分割の切れ目を探さない（1か月の本物の動きは大きい＝メイコー 2026年10月の −30% が 1→2 に見えた）。
    # 月足は reconcile_monthly で日足と突き合わせて直す
    bars = [("2026-09-01", 83490.0, 73510.0, 80480.0, 11095700.0),
            ("2026-10-01", 82940.0, 76360.0, 78000.0, 13482900.0),
            ("2026-11-01", 77630.0, 14410.0, 14722.0, 11117000.0)]
    assert S.adjust_hlcv(bars, [("2026-11-19", 5.0)]) == (bars, [])
    meiko = [("2026-09-01", 12500.0, 11000.0, 12170.0, 1.0), ("2026-10-01", 12200.0, 8250.0, 8550.0, 1.0)]
    assert S.adjust_hlcv(meiko, [("2026-10-29", 2.0)]) == (meiko, [])


def test_big_split_needs_a_move_beyond_the_price_limit():
    # 2倍以上の分割：直していない切れ目は必ず値幅制限の外に出る。¥150 の株の −30%（¥150→¥104・制限 ¥50 の中）は本物の動き＝
    # 「1→2 の切れ目」にも見える形（比 0.69）だが直さない。制限の外（¥150→¥80）なら直していない切れ目
    dates = _dates("2026-10-19", 10)
    assert S.find_breaks(dates, [150.0] * 9 + [104.0], [("2026-11-02", 2.0)]) == []
    assert S.find_breaks(dates, [150.0] * 9 + [80.0], [("2026-11-02", 2.0)]) == [(dates[9], 2.0)]
    assert S.beyond_limit(72510.0, 14722.0) and not S.beyond_limit(400.0, 330.0) and S.beyond_limit(400.0, 300.0)


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



# ── 単位のずれ・倍率の小さい分割の日（2026-11-19 夜） ──────────────────

def test_unit_glitch_without_split_event_is_repaired():
    # 1306.T（TOPIX 連動の上場投信）：2026-03-30・31 の2日だけ 1/10（出来高は10倍）・分割の情報は無い
    dates = ["2026-03-26", "2026-03-27", "2026-03-30", "2026-03-31", "2026-04-01"]
    closes = [382.6, 382.7, 37.64, 37.14, 389.2]
    f, fixes = S.index_factors(dates, closes, [])
    assert [round(c * k, 2) for c, k in zip(closes, f)] == [382.6, 382.7, 376.4, 371.4, 389.2]
    assert fixes == [("2026-03-30", 10.0), ("2026-03-31", 0.1)] or fixes == [("2026-03-30", 10.0), ("2026-04-01", 0.1)]
    assert not S.unit_pending(dates, closes)          # 戻っている＝決められる


def test_unit_glitch_with_bogus_split_event_is_repaired():
    # 1321.T：Yahoo に偽の「100:1 の分割」・値は 10-05・06 の2日だけ 1/100（出来高は100倍）＝分割としては直さず、単位のずれとして直す
    import datetime as _dt
    days = ["2026-10-01", "2026-10-02", "2026-10-05", "2026-10-06", "2026-10-07"]
    rows = [(_dt.datetime.fromisoformat(d + "T09:00:00").replace(tzinfo=JST), c, c, c, c, v)
            for d, c, v in zip(days, [718.1, 710.4, 7.279, 7.351, 729.7], [50302200, 22979300, 3202535000, 2147485000, 13663350])]
    out, fixes = S.adjust_ohlcv(rows, [("2026-10-05", 100.0)])
    assert [round(r[4], 1) for r in out] == [718.1, 710.4, 727.9, 735.1, 729.7]
    assert round(out[2][5]) == 32025350 and out[0] == rows[0] and out[4] == rows[4]


def test_permanent_unit_shift_takes_the_latest_units():
    # 戻らないずれ（1306.T の 2015-01 のように、その日から 1/10 のまま）＝いちばん新しい足の単位にそろえる
    dates = _dates("2014-12-01", 30)
    closes = [1442.0] * 15 + [144.7] * 15
    f, fixes = S.index_factors(dates, closes, [])
    assert [round(c * k, 1) for c, k in zip(closes, f)] == [144.2] * 15 + [144.7] * 15
    assert not S.unit_pending(dates, closes)


def test_unit_shift_in_the_last_days_is_pending():
    # いちばん新しい足が 1/10（まだ戻っていない）＝どちらの単位が正しいか決められない
    dates = _dates("2026-11-02", 14)
    assert S.unit_pending(dates, [380.0] * 13 + [38.1])
    assert S.unit_pending(dates, [380.0] * 12 + [38.1, 38.3])
    assert not S.unit_pending(dates, [380.0] * 11 + [38.1, 38.3, 381.0])      # 戻った
    assert not S.unit_pending(dates, [380.0] * 14)
    # 分割の情報があり分割として直る 1→10 は「ずれ」ではない
    assert not S.unit_pending(dates, [3800.0] * 13 + [381.0], [("2026-11-20", 10.0)])


def test_small_split_only_looks_two_trading_days_before():
    # 倍率の小さい分割（1→1.05）：生の値段のまま・本当の切れ目は 3/30（分割の日付の取引日）で、その日の本物の値動きは −8%。
    # 3/31 の本物の −7% のほうが「1.05 の切れ目」に近く見えるが、見るのは日付の2取引日前〜その日だけ＝3/30 を選ぶ
    dates = ["2026-03-19", "2026-03-23", "2026-03-24", "2026-03-25", "2026-03-26", "2026-03-27",
             "2026-03-30", "2026-03-31", "2026-04-01"]
    raw = [1428.0, 1424.0, 1423.0, 1435.0, 1437.0, 1447.0, 1264.0, 1176.0, 1197.0]
    assert S.find_breaks(dates, raw, [("2026-03-30", 1.05)]) == [("2026-03-30", 1.05)]
    # 大きい分割は今までどおり（日付の 8暦日前〜3暦日後）
    assert S.find_breaks(dates, raw[:6] + [x / 5 for x in raw[6:]], [("2026-04-01", 5.0)]) == [("2026-03-30", 5.0)]



def test_unit_needs_a_move_impossible_under_price_limits():
    # ¥100 未満の制限値幅は ¥30 の定額＝¥3→¥33 のストップ高・¥33→¥3 のストップ安は本物でありうる＝単位のずれにしない
    dates = _dates("2026-10-01", 20)
    assert S.index_factors(dates, [3.0] * 19 + [33.0], [])[1] == []
    assert S.index_factors(dates, [33.0] * 19 + [3.0], [])[1] == []
    assert S.price_limit(72510.0) == 15000 and S.price_limit(37.6) == 30 and S.price_limit(2.0e7) == 6.0e6
    assert S.impossible(382.7, 37.64) and S.impossible(37.14, 389.2) and not S.impossible(33.0, 3.0)


def test_unit_prefers_yahoo_split_ratio_when_closer():
    # ブルドックソース 2005 の形：5,950 ↔ 661.11（ちょうど9倍）を何度も行き来＝分割の倍率 9 が近ければ 9 で直す（10 だと11%ずれる）
    dates = _dates("2005-09-20", 12)
    closes = [5950.0] * 6 + [661.11] * 6
    f, fixes = S.index_factors(dates, closes, [("2005-12-31", 9.0)])
    assert fixes == [(dates[6], 9.0)] and round(closes[0] * f[0], 2) == 661.11
    f, fixes = S.index_factors(dates, closes, [])
    assert fixes == [(dates[6], 10.0)]                               # 分割の情報が無ければ単位（10）



def test_unit_ignores_long_gaps_between_bars():
    # 売買の無い日が続いて足が飛んだところ（8暦日以上）の大きな動きは、単位のずれと見ない
    dates = ["2026-09-01", "2026-09-02", "2026-09-03", "2026-09-14", "2026-09-15"]
    assert S.index_factors(dates, [400.0, 401.0, 402.0, 4030.0, 4040.0], [])[1] == []
    dates = ["2026-09-01", "2026-09-02", "2026-09-03", "2026-09-04", "2026-09-07"]
    assert S.index_factors(dates, [400.0, 401.0, 402.0, 4030.0, 4040.0], [])[1] == [("2026-09-04", 0.1)]



# ── 直せるところを全部（2026-11-19 夜・2回目） ──────────────────────

def test_flip_glitch_on_split_date_is_repaired():
    # 三菱ケミカル（4188）：分割の日付 2005-09-30（倍率 0.5）の足だけ 376（前後は 752・815）＝その足だけ直す
    dates = ["2005-09-28", "2005-09-29", "2005-09-30", "2005-10-03", "2005-10-04"]
    closes = [752.0, 752.0, 376.0, 815.0, 813.0]
    f, fixes = S.index_factors(dates, closes, [("2005-09-30", 0.5)])
    assert [c * k for c, k in zip(closes, f)] == [752.0, 752.0, 752.0, 815.0, 813.0]
    # ローツェ（6323）：分割の日付 2000-08-25（倍率 2）の足だけ 230（前後は 112.75・128）
    dates = ["2000-08-23", "2000-08-24", "2000-08-25", "2000-08-28", "2000-08-29"]
    closes = [113.75, 112.75, 230.0, 128.0, 125.0]
    f, _ = S.index_factors(dates, closes, [("2000-08-25", 2.0)])
    assert [c * k for c, k in zip(closes, f)] == [113.75, 112.75, 115.0, 128.0, 125.0]


def test_real_round_trip_away_from_split_date_is_left_alone():
    # 分割の日付から離れた本物の −50%・+100%（¥100 未満の株のストップ安・ストップ高）は直さない
    dates = _dates("2026-06-01", 10)
    closes = [60.0, 60.0, 30.0, 60.0, 61.0, 62.0, 61.0, 60.0, 60.0, 61.0]
    assert S.index_factors(dates, closes, [("2026-10-01", 2.0)])[1] == []
    assert S.index_factors(dates, closes, [])[1] == []


def test_unit_uses_product_of_two_split_ratios():
    # 1793 の形：2000-01-05 に 3755 → 637.5（5.9倍）・Yahoo の分割の倍率は 0.2・3・2 ＝ 3×2＝6 がいちばん近い
    dates = ["1999-12-29", "1999-12-30", "2000-01-04", "2000-01-05", "2000-01-06"]
    closes = [3700.0, 3720.0, 3755.0, 637.5, 640.0]
    f, fixes = S.index_factors(dates, closes, [("2000-03-01", 0.2), ("2001-05-01", 3.0), ("2003-05-01", 2.0)])
    assert fixes == [("2000-01-05", 6.0)] and round(closes[2] * f[2], 2) == 625.83


def test_monthly_unit_glitch_is_not_fixed_from_monthly_alone():
    # 月足だけでは「1日ではありえない」が使えない（1か月にはストップ高・安が何度も入る）＝単位のずれとしては直さない
    bars = [("2026-02-01", 420.0, 395.0, 413.1, 1.0e8), ("2026-03-01", 413.0, 36.74, 37.14, 5.0e8),
            ("2026-04-01", 395.0, 370.0, 394.1, 1.0e8)]
    assert S.adjust_hlcv(bars, []) == (bars, [])


def test_reconcile_monthly_with_daily():
    # キーエンスの形：月足は 2025-12 以前が分割前（5倍）・2026-01 から直し済み。日足（直し済み）は 2024-11-19 から
    import datetime as _dt
    daily, d = [], _dt.date(2024, 11, 19)
    while d <= _dt.date(2026, 11, 18):
        if d.weekday() < 5:
            p = 14000.0 if d.year < 2026 else 15000.0
            daily.append((d.isoformat(), p * 1.01, p * 0.99, p, 1000.0))
        d += _dt.timedelta(days=1)
    monthly = [("2020-01-01", 80000.0, 60000.0, 70000.0, 100.0)]
    m = _dt.date(2024, 11, 1)
    while m <= _dt.date(2026, 11, 1):
        p = 70000.0 if m.year < 2026 else 15000.0
        monthly.append((m.isoformat(), p * 1.02, p * 0.98, p, 100.0))
        m = (m.replace(day=28) + _dt.timedelta(days=4)).replace(day=1)
    out, rho = S.reconcile_monthly(monthly, daily)
    assert rho == 5.0
    assert out[0] == ("2020-01-01", 16000.0, 12000.0, 14000.0, 500.0)          # 日足より前＝÷5
    dec = next(x for x in out if x[0] == "2025-12-01")
    assert dec[3] == 14000.0 and round(dec[1], 1) == 14140.0                     # 覆う月＝日足から作り直し
    assert out[-1] == monthly[-1]                                                 # いまの月（日足の最後の月）はそのまま
    # そろっていれば何もしない
    good = [(x[0], x[1] / 5, x[2] / 5, x[3] / 5, x[4]) if x[0] < "2026-01" else x for x in monthly]
    out2, rho2 = S.reconcile_monthly(good, daily)
    assert rho2 == 1.0 and out2[0] == good[0]



def test_stock_chart_tool_fixes_jp_closes():
    # 🆕 2026-11-19 generate_stock_chart（記事のチャート用・いまは使われていない）も日本株は直す・日本株以外はそのまま
    import importlib.util as _u
    sp = _u.spec_from_file_location("generate_stock_chart", os.path.join(ROOT, "generate_stock_chart.py"))
    G = _u.module_from_spec(sp)
    sp.loader.exec_module(G)
    data = [{"date": d, "close": c} for d, c in zip(["2026-03-26", "2026-03-27", "2026-03-30", "2026-03-31", "2026-04-01"],
                                                     [382.6, 382.7, 37.64, 37.14, 389.2])]
    assert [x["close"] for x in G._jp_fix("1306.T", data, [])] == [382.6, 382.7, 376.4, 371.4, 389.2]
    assert G._jp_fix("SPY", data, []) is data



def test_weekly_bars_allow_several_limit_days():
    # 霞ヶ関キャピタル（3498）：Yahoo の「月足」の古い分は週足。2019-10-07 → 10-14 の 816 → 1,592 はストップ高4日の本物の動き＝
    # 分割の倍率 2 に近くても直さない（1日の幅で見ると「ありえない」に見えた）
    dates = ["2019-09-30", "2019-10-07", "2019-10-14", "2019-10-21"]
    assert S.index_factors(dates, [820.0, 816.25, 1592.5, 1482.5], [("2019-08-29", 2.0)])[1] == []
    assert S.weekdays_between("2019-10-07", "2019-10-14") == 5 and S.weekdays_between("2026-03-27", "2026-03-30") == 1
    assert S.impossible(382.7, 37.64, 1) and not S.impossible(816.25, 1592.5, 5)



def test_small_ratio_split_does_not_flag_ordinary_days():
    # 日清製粉（2002）2013-09 の形：1→1.1 の分割の日付の前後のふつうの ±1% の動きを「行って戻る誤り」と見ない
    dates = _dates("2013-09-16", 8)
    closes = [894.21, 900.83, 912.4, 906.61, 908.26, 915.0, 910.0, 912.0]
    assert S.index_factors(dates, closes, [("2013-09-20", 1.1)])[1] == []
    # ラストワンマイル（9252）2025-08 の形：1→1.2 の分割の日付の前後の +5%・−7% も見ない
    dates = _dates("2025-07-28", 10)
    closes = [3700.0, 3720.0, 3730.0, 3744.0, 3924.0, 4000.0, 4100.0, 4200.0, 4295.0, 4000.0]
    assert S.index_factors(dates, closes, [("2025-08-01", 1.2)])[1] == []


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
