# -*- coding: utf-8 -*-
"""trade_journal.py（OJ 段3・オーナーの裁量の取引の記録）のテスト。作り物の値だけ"""
import datetime as dt
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import trade_journal as T  # noqa: E402

J = dt.datetime


def gbpjpy(**kw):
    base = dict(tid="30211960", pair="GBPJPY", side="buy", t_open=J(2026, 11, 24, 16, 4, 8), entry=207.605,
                sl=207.469, tp=207.778, t_close=J(2026, 11, 24, 16, 27, 3), exit_=207.734, spread=1.8,
                entry_type="ema15",
                flags=T.parse_flags("tokyo_break=1,strongest=1,htf_aligned=0,tp_before_high=0,event_clear=1"))
    base.update(kw)
    return T.make_trade(**base)


def test_real_gbpjpy_numbers():
    t = gbpjpy()
    assert t["pnl_pips"] == 12.9 and t["risk_pips"] == 13.6
    assert t["r_net"] == pytest.approx(0.949, abs=0.001)
    assert t["cost_r"] == pytest.approx(0.132, abs=0.001)
    assert t["r_gross"] == pytest.approx(1.081, abs=0.001)
    assert t["exit_kind"] == "manual" and t["hold_min"] == pytest.approx(22.9, abs=0.1)
    f = t["flags"]
    assert f["in_window"] is True and f["sl_order"] is True and f["spread_ok"] is True
    assert t["fits_v1_entry"] is True          # 出口の tp_before_high と htf_aligned は入口の判定に入れない


def test_no_lot_or_yen_kept():
    t = gbpjpy()
    assert not {"lot", "pnl_yen", "account"} & set(t)


def test_sell_non_jpy_and_no_stop():
    t = T.make_trade("30187134", "EURUSD", "sell", J(2026, 11, 19, 16, 30, 54), 1.09765, 0.0, 1.09693,
                     J(2026, 11, 19, 16, 50, 7), 1.09733)
    assert t["pnl_pips"] == 3.2 and t["sl"] is None
    assert t["r_net"] is None and t["flags"]["sl_order"] is False and t["fits_v1_entry"] is False


def test_sl_and_tp_hits_and_sell_r():
    t = T.make_trade("1", "USDJPY", "sell", J(2026, 12, 1, 15, 30), 150.00, 150.20, 149.70,
                     J(2026, 12, 1, 15, 50), 150.20, spread=1.0)
    assert t["exit_kind"] == "sl" and t["r_net"] == -1.0
    t = T.make_trade("2", "USDJPY", "sell", J(2026, 12, 1, 15, 30), 150.00, 150.20, 149.70,
                     J(2026, 12, 1, 15, 50), 149.70, spread=1.0)
    assert t["exit_kind"] == "tp" and t["r_net"] == 1.5


def test_stop_on_wrong_side_is_rejected():
    with pytest.raises(ValueError):
        T.make_trade("3", "GBPJPY", "buy", J(2026, 12, 1, 16), 207.0, 207.2, None, J(2026, 12, 1, 16, 10), 207.1)


def test_spread_rules():
    assert gbpjpy(spread=2.6)["flags"]["spread_ok"] is False            # 広すぎる
    assert gbpjpy(sl=207.505)["flags"]["spread_ok"] is False            # 損切り 10pips < 1.8×7
    assert gbpjpy(spread=None)["flags"]["spread_ok"] is None


def test_window_and_v1_entry():
    t = gbpjpy(t_open=J(2026, 11, 24, 17, 5), t_close=J(2026, 11, 24, 17, 30))
    assert t["flags"]["in_window"] is False and t["fits_v1_entry"] is False
    assert gbpjpy(entry_type="line")["fits_v1_entry"] is False
    t = gbpjpy(flags=T.parse_flags("strongest=1,event_clear=1"))     # tokyo_break が分からない
    assert t["fits_v1_entry"] is None


def test_server_time_dst():
    assert T.server_to_jst(J(2026, 11, 24, 9, 4, 8)) == J(2026, 11, 24, 16, 4, 8)     # 冬＝+7
    assert T.server_to_jst(J(2026, 6, 2, 5, 8, 40)) == J(2026, 6, 2, 11, 8, 40)        # 夏＝+6
    assert T.us_dst(dt.date(2026, 11, 1)) is False and T.us_dst(dt.date(2026, 10, 31)) is True
    assert T.us_dst(dt.date(2026, 3, 8)) is True and T.us_dst(dt.date(2026, 3, 7)) is False


def test_flags_parse_rejects_unknown():
    with pytest.raises(SystemExit):
        T.parse_flags("foo=1")
    assert T.parse_flags("tokyo_break=?")["tokyo_break"] is None


def test_add_rejects_duplicates_and_old_dates():
    st = T.empty_state()
    T.add(st, gbpjpy())
    with pytest.raises(SystemExit):
        T.add(st, gbpjpy())
    with pytest.raises(SystemExit):
        T.add(st, gbpjpy(tid="9", t_open=J(2026, 11, 19, 16), t_close=J(2026, 11, 19, 16, 20)))


def fake(i, r, day):
    t = gbpjpy(tid=str(i), t_open=J(2026, 12, 1, 15, 0) + dt.timedelta(days=day, minutes=i),
               t_close=J(2026, 12, 1, 15, 30) + dt.timedelta(days=day, minutes=i))
    t["r_net"] = r
    return t


def test_checkpoint_only_at_multiples_and_fixed():
    st = T.empty_state()
    for i in range(29):
        T.add(st, fake(i, 0.5, i // 3))
    T.run_checkpoints(st, n_boot=500)
    assert st["checkpoints"] == []
    assert "平均" not in T.status_text(st).split("\n")[0].replace("途中の平均は出さない", "")
    T.add(st, fake(29, 0.5, 10))
    T.run_checkpoints(st, n_boot=500)
    assert [c["n"] for c in st["checkpoints"]] == [30]
    c = st["checkpoints"][0]
    assert c["lo"] > 0 and c["verdict"].startswith("機能している")
    T.add(st, fake(30, -5.0, 11))                 # 判定は固定＝あとの取引で書き換わらない
    T.run_checkpoints(st, n_boot=500)
    assert st["checkpoints"][0] == c and len(st["checkpoints"]) == 1


def test_verdicts():
    assert T.verdict_of(0.01, 0.5).startswith("機能")
    assert T.verdict_of(-0.5, -0.01).startswith("反証")
    assert T.verdict_of(-0.1, 0.2).startswith("まだ")


def test_reading_table_skips_rule_source_trade():
    trades = [gbpjpy(used_for_rule=True), fake(1, -1.0, 0)]
    rows = T.reading_table(trades)
    assert rows["tokyo_break=o"]["n"] == 1 and rows["tokyo_break=o"]["mean"] == -1.0


def test_push_and_stop_line_buffer():
    t = gbpjpy(push="2", sl_line=207.51)
    assert t["push"] == "2" and t["sl_buffer_pips"] == 4.1
    s = T.make_trade("5", "EURUSD", "sell", J(2026, 12, 1, 15, 30), 1.1000, 1.1020, None,
                     J(2026, 12, 1, 15, 40), 1.0990, push="1", sl_line=1.1015)
    assert s["sl_buffer_pips"] == 5.0           # 売りは線の上に余白
    with pytest.raises(ValueError):
        gbpjpy(push="4")
    assert gbpjpy()["sl_buffer_pips"] is None


def test_friday_is_outside_v1():
    t = gbpjpy(t_open=J(2026, 11, 27, 16, 4), t_close=J(2026, 11, 27, 16, 30))   # 金曜
    assert t["flags"]["weekday_ok"] is False and t["fits_v1_entry"] is False
    assert gbpjpy()["flags"]["weekday_ok"] is True                               # 火曜


# ── 50%押し目（型1）の目印（2026-11-24 夜・オーナー「はい、足す」）──────────────

def half50(**kw):
    """型1 の売りの形（作り物の日付・値段は 11/17 の実例の線と新安値と同じ並び）"""
    base = dict(tid="h1", pair="GBPJPY", side="sell", t_open=J(2026, 12, 1, 18, 45), entry=209.889, sl=210.019,
                tp=None, t_close=J(2026, 12, 1, 19, 2, 47), exit_=209.760, spread=1.8, entry_type="half50",
                break_line=209.963, extreme=209.570)
    base.update(kw)
    return T.make_trade(**base)


def test_half50_keeps_leg_and_depth():
    t = half50()
    assert t["entry_type"] == "half50"
    assert t["leg_pips"] == 39.3                     # 線から新安値まで
    assert t["depth_pct"] == 81.2                    # 線までの何％戻したところで入ったか（11/17 は約81%）
    assert t["break_line"] == 209.963 and t["extreme"] == 209.570
    assert t["fits_v1_entry"] is False               # OJ（15分足 EMA の押し）の決まりの紙には当てはまらない
    assert gbpjpy()["fits_v1_entry"] is True and gbpjpy(entry_type="half50")["fits_v1_entry"] is False   # ○× が全部そろっていても混ぜない


def test_half50_buy_is_mirror():
    t = half50(side="buy", entry=207.56, sl=207.30, exit_=207.70, break_line=207.36, extreme=207.76)
    assert t["leg_pips"] == 40.0 and t["depth_pct"] == 50.0


def test_half50_second_entry_at_line_is_100():
    assert half50(entry=209.963)["depth_pct"] == 100.0


def test_leg_is_none_without_line_and_extreme():
    t = gbpjpy()
    assert t["leg_pips"] is None and t["depth_pct"] is None and t["break_line"] is None and t["extreme"] is None
    for kw in (dict(break_line=None), dict(extreme=None)):     # 片方だけ＝入れ忘れ
        with pytest.raises(ValueError):
            half50(**kw)


def test_extreme_on_wrong_side_is_rejected():
    with pytest.raises(ValueError):
        half50(extreme=210.30)                       # 売りなのに、新安値が線より上
    with pytest.raises(ValueError):
        half50(side="buy", sl=207.30, entry=207.56, exit_=207.7, break_line=207.36, extreme=207.10)
    with pytest.raises(ValueError):
        half50(extreme=209.963)                      # 線と同じ値＝0で割る


def test_unknown_entry_type_is_rejected():
    with pytest.raises(ValueError):
        half50(entry_type="half")


def fake_half(i, r, day):
    t = half50(tid=f"h{i}", t_open=J(2026, 12, 1, 17, 0) + dt.timedelta(days=day, minutes=i),
               t_close=J(2026, 12, 1, 17, 30) + dt.timedelta(days=day, minutes=i))
    t["r_net"] = r
    return t


def test_checkpoint_counts_all_types_and_reading_splits_them():
    st = T.empty_state()
    for i in range(15):
        T.add(st, fake(i, 1.0, i % 3))               # 火〜木（金曜は決まりの紙の外になる）
        T.add(st, fake_half(i, -0.5, i % 3))
    T.run_checkpoints(st, n_boot=300)
    c = st["checkpoints"][0]
    assert c["n"] == 30 and c["mean_r"] == 0.25      # 判定は全部の取引をまとめて1つ（種類で分けない）
    r = c["reading"]
    assert r["entry_type=ema15"] == {"n": 15, "mean": 1.0}
    assert r["entry_type=half50"] == {"n": 15, "mean": -0.5}
    assert r["entry_type=line"] == {"n": 0, "mean": None}
    assert r["fits_v1_entry=o"]["n"] == 15           # 50%押し目は OJ の決まりの紙に混ざらない


def test_reading_by_type_skips_rule_source_trade():
    r = T.reading_table([gbpjpy(used_for_rule=True), fake(1, -1.0, 0), fake_half(1, 2.0, 0)])
    assert r["entry_type=ema15"] == {"n": 1, "mean": -1.0} and r["entry_type=half50"] == {"n": 1, "mean": 2.0}


def test_status_shows_counts_by_type_but_no_average():
    st = T.empty_state()
    T.add(st, gbpjpy())
    T.add(st, fake_half(1, 2.345, 0))
    T.add(st, half50(tid="nosl", sl=None, t_open=J(2026, 12, 2, 18), t_close=J(2026, 12, 2, 18, 20)))
    s = T.status_text(st)
    assert "15分足EMAの押し 1件" in s and "50%押し目 1件" in s       # R を出せる取引だけ数える
    assert "2.345" not in s and "+2.3" not in s and "R（95%" not in s


def test_old_records_without_new_keys_still_work():
    st = T.empty_state()
    t = gbpjpy()
    for k in ("break_line", "extreme", "leg_pips", "depth_pct"):
        t.pop(k)
    T.add(st, t)
    assert "15分足EMAの押し 1件" in T.status_text(st)
    assert T.reading_table([t])["entry_type=ema15"]["n"] == 1


def test_cli_adds_half50(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    T.main(["add", "--id", "77", "--pair", "GBPJPY", "--side", "sell", "--open", "2026.12.01 11:45:00", "--entry", "209.889",
            "--sl", "210.019", "--close", "2026.12.01 12:02:47", "--exit", "209.760", "--spread", "1.8", "--server-time",
            "--entry-type", "half50", "--break-line", "209.963", "--extreme", "209.570"])
    t = T.load()["trades"][0]
    assert t["entry_type"] == "half50" and t["depth_pct"] == 81.2 and t["entry_time"] == "18:45:00"
    assert "50%押し目 1件" in capsys.readouterr().out


# ── 決まりの紙 v2（追記⑥）＝30分以内に30pips → 50%・水平線・MA の押し（2026-11-24 夜・オーナー「これからの取引を記録する」）──

V2_FLAGS = "tokyo_break=1,strongest=1,event_clear=1"


def v2(**kw):
    """割った線 209.963 → 20分で30pips → 新安値 209.570 → 50% で売り・損切りは線の 4pips 外"""
    base = dict(sl=210.003, sl_line=209.963, entry=209.767, exit_=209.640, far_min=20, pairs_hit=2,
                flags=T.parse_flags(V2_FLAGS), t_open=J(2026, 12, 1, 17, 30), t_close=J(2026, 12, 1, 17, 50))
    base.update(kw)
    return half50(**base)


def test_v2_keeps_minutes_and_pairs():
    t = v2()
    assert t["far_min"] == 20 and t["pairs_hit"] == 2
    assert t["flags"]["far30"] is True and t["flags"]["pairs2"] is True
    assert t["fits_v2_entry"] is True
    assert t["sl_buffer_pips"] == 4.0 and t["depth_pct"] == 50.1


def test_far30_edges():
    assert v2(far_min=30)["flags"]["far30"] is True
    assert v2(far_min=35)["flags"]["far30"] is False          # 30分を過ぎて離れた＝狙わない
    assert v2(far_min=35)["fits_v2_entry"] is False
    assert v2(far_min=0)["flags"]["far30"] is True            # 抜けた足そのもので30pips
    t = v2(far_min=None)                                      # 分を入れ忘れ＝分からない
    assert t["flags"]["far30"] is None and t["fits_v2_entry"] is None


def test_never_reached_30pips_is_false_without_minutes():
    t = v2(far_min=None, extreme=209.664, entry=209.814)      # 29.9pips しか離れていない
    assert t["leg_pips"] == 29.9 and t["flags"]["far30"] is False and t["fits_v2_entry"] is False
    t = v2(far_min=10, extreme=209.663, entry=209.813)        # ちょうど30.0pips
    assert t["leg_pips"] == 30.0 and t["flags"]["far30"] is True


def test_minutes_contradict_leg_is_rejected():
    with pytest.raises(ValueError):
        v2(far_min=10, extreme=209.664, entry=209.814)        # 30pips 離れていないのに「10分で届いた」
    with pytest.raises(ValueError):
        v2(far_min=-5)


def test_pairs_hit_edges():
    assert v2(pairs_hit=1)["flags"]["pairs2"] is False
    assert v2(pairs_hit=3)["flags"]["pairs2"] is True
    assert v2(pairs_hit=None)["flags"]["pairs2"] is None
    assert v2(pairs_hit=1)["fits_v2_entry"] is True           # 「できれば」＝入口の条件には入れない（読むための表で分ける）
    for bad in (-1, 4):
        with pytest.raises(ValueError):
            v2(pairs_hit=bad)


def test_v2_takes_all_three_lines_but_not_other():
    for k in ("ema15", "line", "half50"):
        assert v2(entry_type=k)["fits_v2_entry"] is True
    assert v2(entry_type="other")["fits_v2_entry"] is False


def test_v2_window_is_until_two_hours_after_london():
    def at(*a):
        return v2(t_open=J(*a), t_close=J(*a) + dt.timedelta(minutes=10))
    assert at(2026, 12, 1, 18, 59)["flags"]["in_window2"] is True        # 冬＝英国の朝8時は17時
    assert at(2026, 12, 1, 19, 0)["flags"]["in_window2"] is False
    assert at(2026, 12, 1, 15, 0)["flags"]["in_window2"] is True
    assert at(2026, 12, 1, 14, 59)["flags"]["in_window2"] is False
    assert at(2027, 6, 1, 17, 59)["flags"]["in_window2"] is True         # 夏＝16時
    assert at(2027, 6, 1, 18, 0)["flags"]["in_window2"] is False
    assert at(2026, 12, 1, 18, 59)["fits_v2_entry"] is True
    assert at(2026, 12, 1, 19, 0)["fits_v2_entry"] is False
    assert at(2026, 12, 1, 18, 59)["flags"]["in_window"] is False        # v1 の時間は変えない


def test_london_open_follows_uk_not_us_dst():
    assert T.london_open(dt.date(2027, 3, 26)) == 17 and T.london_open(dt.date(2027, 3, 28)) == 16   # 3月の最後の日曜
    assert T.london_open(dt.date(2027, 3, 16)) == 17                     # 米国はもう夏時間・英国はまだ冬
    assert T.london_open(dt.date(2027, 10, 30)) == 16 and T.london_open(dt.date(2027, 10, 31)) == 17
    assert T.london_open(dt.date(2026, 10, 27)) == 17                    # 米国はまだ夏時間・英国はもう冬


def test_v2_needs_the_common_conditions():
    for kw in (dict(sl=None, sl_line=None), dict(spread=2.6), dict(t_open=J(2026, 12, 4, 17, 30), t_close=J(2026, 12, 4, 17, 50)),
               dict(flags=T.parse_flags("tokyo_break=0,strongest=1,event_clear=1")),
               dict(flags=T.parse_flags("tokyo_break=1,strongest=0,event_clear=1")),
               dict(flags=T.parse_flags("tokyo_break=1,strongest=1,event_clear=0"))):
        assert v2(**kw)["fits_v2_entry"] is False
    assert v2(flags=T.parse_flags("tokyo_break=1,strongest=1"))["fits_v2_entry"] is None


def test_v1_is_unchanged_by_v2():
    t = gbpjpy()
    assert t["fits_v1_entry"] is True and t["fits_v2_entry"] is None     # 30pips の記録が無い＝分からない
    assert t["far_min"] is None and t["pairs_hit"] is None
    t = gbpjpy(far_min=45, pairs_hit=1)
    assert t["fits_v1_entry"] is True and t["fits_v2_entry"] is False


def fake_v2(i, r, day, **kw):
    t = v2(tid=f"v{i}", t_open=J(2026, 12, 1, 17, 0) + dt.timedelta(days=day, minutes=i),
           t_close=J(2026, 12, 1, 17, 30) + dt.timedelta(days=day, minutes=i), **kw)
    t["r_net"] = r
    return t


def test_reading_table_splits_v2_items():
    r = T.reading_table([fake_v2(1, 1.0, 0), fake_v2(2, 3.0, 0), fake_v2(3, -1.0, 0, far_min=40, pairs_hit=1),
                         fake_v2(4, 9.0, 0, far_min=None, pairs_hit=None)])
    assert r["far30=o"] == {"n": 2, "mean": 2.0} and r["far30=x"] == {"n": 1, "mean": -1.0}
    assert r["pairs2=o"] == {"n": 2, "mean": 2.0} and r["pairs2=x"] == {"n": 1, "mean": -1.0}
    assert r["fits_v2_entry=o"] == {"n": 2, "mean": 2.0} and r["fits_v2_entry=x"] == {"n": 1, "mean": -1.0}
    assert r["in_window2=o"]["n"] == 4


def test_checkpoint_is_not_split_by_v2():
    st = T.empty_state()
    for i in range(15):
        T.add(st, fake(i, 1.0, i % 3))
        T.add(st, fake_v2(i, -0.5, i % 3))
    T.run_checkpoints(st, n_boot=300)
    assert [c["n"] for c in st["checkpoints"]] == [30] and st["checkpoints"][0]["mean_r"] == 0.25


def test_status_counts_v2_without_average():
    st = T.empty_state()
    T.add(st, gbpjpy())
    T.add(st, fake_v2(1, 2.345, 0))
    s = T.status_text(st)
    assert "決まりの紙 v2 の入口に全部当てはまった取引 1件" in s and "決まりの紙 v1 の入口に全部当てはまった取引 1件" in s
    assert "2.345" not in s and "+2.3" not in s


def test_old_record_without_v2_keys_still_works():
    st = T.empty_state()
    t = gbpjpy()
    for k in ("far_min", "pairs_hit", "fits_v2_entry"):
        t.pop(k)
    for k in ("far30", "pairs2", "in_window2"):
        t["flags"].pop(k)
    T.add(st, t)
    assert "決まりの紙 v2 の入口に全部当てはまった取引 0件" in T.status_text(st)
    r = T.reading_table([t])
    assert r["far30=o"]["n"] == 0 and r["fits_v2_entry=o"]["n"] == 0


def test_cli_adds_v2(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    T.main(["add", "--id", "78", "--pair", "GBPJPY", "--side", "sell", "--open", "2026.12.01 10:30:00", "--entry", "209.767",
            "--sl", "210.003", "--close", "2026.12.01 10:50:00", "--exit", "209.640", "--spread", "1.8", "--server-time",
            "--entry-type", "half50", "--break-line", "209.963", "--extreme", "209.570", "--sl-line", "209.963",
            "--far-min", "20", "--pairs-hit", "2", "--flags", V2_FLAGS])
    t = T.load()["trades"][0]
    assert t["far_min"] == 20 and t["pairs_hit"] == 2 and t["fits_v2_entry"] is True and t["entry_time"] == "17:30:00"
    assert "決まりの紙 v2 の入口に全部当てはまった取引 1件" in capsys.readouterr().out


# ── 決まりの紙 v3（追記⑧）＝2ペア以上が水平線か MA に当たったら、一番強い通貨に入る（2026-11-25）──

def v3(**kw):
    """割った線 209.963 → 20分で30pips → ほかの2ペアが線か MA に当たり、まだ線の手前にいる強いほう（ポンド円）を売る"""
    base = dict(pairs_lm=2, pairs_hit=None, entry_type="series", strong_flow="GBPJPY", strong_far="GBPJPY")
    base.update(kw)
    return v2(**base)


def test_v3_keeps_the_count_and_both_answers():
    t = v3(strong_far="EURJPY")
    assert t["pairs_lm"] == 2 and t["strong_flow"] == "GBPJPY" and t["strong_far"] == "EURJPY"
    assert t["flags"]["pairs_lm2"] is True and t["flags"]["pick_flow"] is True and t["flags"]["pick_far"] is False
    assert t["fits_v3_entry"] is True


def test_v3_needs_two_pairs():
    assert v3(pairs_lm=3)["fits_v3_entry"] is True
    t = v3(pairs_lm=1)
    assert t["flags"]["pairs_lm2"] is False and t["fits_v3_entry"] is False        # v2 の「できれば」と違い、条件
    t = v3(pairs_lm=None)
    assert t["flags"]["pairs_lm2"] is None and t["fits_v3_entry"] is None
    assert v3(pairs_lm=0)["fits_v3_entry"] is False
    for bad in (-1, 4):
        with pytest.raises(ValueError):
            v3(pairs_lm=bad)


def test_v3_does_not_need_the_entered_pair_on_a_line():
    for k in T.ENTRY_TYPES:
        assert v3(entry_type=k)["fits_v3_entry"] is True                           # 入ったペアがどの線に当たっていたかは問わない
    assert v3()["fits_v2_entry"] is False                                          # v2 は入るペア自身の当たりが要る


def test_v3_needs_the_strongest_pair():
    def f(x):
        return v3(flags=T.parse_flags("tokyo_break=1,event_clear=1" + x))["fits_v3_entry"]
    assert f(",strongest=1") is True and f(",strongest=0") is False and f("") is None
    assert v3(strong_flow="EURJPY")["fits_v3_entry"] is True                        # 道具の答えと違っても、オーナーの見立てが優先


def test_v3_needs_30pips_and_the_common_conditions():
    assert v3(far_min=35)["fits_v3_entry"] is False and v3(far_min=None)["fits_v3_entry"] is None
    for kw in (dict(sl=None, sl_line=None), dict(spread=2.6), dict(t_open=J(2026, 12, 4, 17, 30), t_close=J(2026, 12, 4, 17, 50)),
               dict(t_open=J(2026, 12, 1, 19, 0), t_close=J(2026, 12, 1, 19, 10)), dict(flags=T.parse_flags("tokyo_break=0,strongest=1,event_clear=1")),
               dict(flags=T.parse_flags("tokyo_break=1,strongest=1,event_clear=0"))):
        assert v3(**kw)["fits_v3_entry"] is False


def test_v1_and_v2_are_unchanged_by_v3():
    assert v2()["fits_v2_entry"] is True and v2()["fits_v3_entry"] is None         # 線か MA のペア数の記録が無い＝分からない
    assert v2(pairs_lm=0)["fits_v2_entry"] is True
    t = gbpjpy()
    assert t["fits_v1_entry"] is True and t["pairs_lm"] is None and t["strong_flow"] is None and t["strong_far"] is None
    assert t["flags"]["pick_flow"] is None and t["flags"]["pick_far"] is None


def test_reading_table_splits_v3_items():
    def one(i, r, **kw):
        t = v3(tid=f"w{i}", **kw)
        t["r_net"] = r
        return t
    r = T.reading_table([one(1, 1.0), one(2, 3.0, strong_far="EURJPY"), one(3, -1.0, pairs_lm=1, strong_flow="EURJPY"), one(4, 9.0, pairs_lm=None, strong_flow=None)])
    assert r["pairs_lm2=o"] == {"n": 2, "mean": 2.0} and r["pairs_lm2=x"] == {"n": 1, "mean": -1.0}
    assert r["fits_v3_entry=o"] == {"n": 2, "mean": 2.0} and r["fits_v3_entry=x"] == {"n": 1, "mean": -1.0}
    assert r["pick_flow=o"] == {"n": 2, "mean": 2.0} and r["pick_flow=x"] == {"n": 1, "mean": -1.0}
    assert r["pick_far=x"] == {"n": 1, "mean": 3.0} and r["entry_type=series"]["n"] == 4


def test_status_counts_v3_without_average():
    st = T.empty_state()
    t = v3(tid="z1")
    t["r_net"] = 2.345
    T.add(st, t)
    s = T.status_text(st)
    assert "決まりの紙 v3 の入口に全部当てはまった取引 1件" in s and "シリーズ" in s and "2.345" not in s


def test_old_record_without_v3_keys_still_works():
    st = T.empty_state()
    t = v2()
    for k in ("pairs_lm", "strong_flow", "strong_far", "fits_v3_entry"):
        t.pop(k)
    for k in ("pairs_lm2", "pick_flow", "pick_far"):
        t["flags"].pop(k)
    T.add(st, t)
    assert "決まりの紙 v3 の入口に全部当てはまった取引 0件" in T.status_text(st)
    assert T.reading_table([t])["pairs_lm2=o"]["n"] == 0


def test_cli_adds_v3(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    T.main(["add", "--id", "79", "--pair", "GBPJPY", "--side", "sell", "--open", "2026.12.01 10:30:00", "--entry", "209.767",
            "--sl", "210.003", "--close", "2026.12.01 10:50:00", "--exit", "209.640", "--spread", "1.8", "--server-time",
            "--entry-type", "series", "--break-line", "209.963", "--extreme", "209.570", "--sl-line", "209.963",
            "--far-min", "20", "--pairs-lm", "2", "--flags", V2_FLAGS])
    t = T.load()["trades"][0]
    assert t["pairs_lm"] == 2 and t["fits_v3_entry"] is True and t["fits_v2_entry"] is False and t["entry_type"] == "series"
    assert "決まりの紙 v3 の入口に全部当てはまった取引 1件" in capsys.readouterr().out
