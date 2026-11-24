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
