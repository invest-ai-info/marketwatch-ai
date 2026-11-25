# -*- coding: utf-8 -*-
"""SB（series_break_lab.py）のテスト。本物の値段は使わない＝作った足だけで、決まりどおりに動くかを見る"""
import datetime as dt
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import series_break_lab as SB  # noqa: E402

DAY = dt.date(2026, 11, 17)            # 火曜・冬（ロンドンの始まり＝日本時間 17:00）
SUMMER = dt.date(2026, 6, 16)          # 火曜・夏（16:00）
FRIDAY = dt.date(2026, 11, 20)
BASE = {"USDJPY": 100.0, "EURJPY": 100.0, "GBPJPY": 100.0, "AUDJPY": 100.0, "EURUSD": 1.1, "GBPUSD": 1.1, "AUDUSD": 1.1}
NOEV = {p: np.array([], dtype=np.int64) for p in SB.PAIRS}


def jst(h, m, day=DAY):
    return pd.Timestamp(dt.datetime(day.year, day.month, day.day, h, m), tz=SB.JST).tz_convert("UTC")


def base_bars(p, day=DAY, spread_pips=1.0):
    """8:00〜19:30（日本時間）の平らな5分足。線＝基準 ±10pips（8:00 の安値・8:05 の高値）"""
    pp, px = SB.pip(p), BASE[p]
    idx = pd.date_range(jst(8, 0, day), jst(19, 30, day), freq="5min")
    df = pd.DataFrame({"open": px, "high": px, "low": px, "close": px, "so": spread_pips * pp}, index=idx)
    df.loc[jst(8, 0, day), "low"] = px - 10 * pp
    df.loc[jst(8, 5, day), "high"] = px + 10 * pp
    return df


def put(df, p, h, m, o, hi, lo, c, day=DAY):
    """足を1本書き換える（値は基準からの pips）"""
    pp, px = SB.pip(p), BASE[p]
    df.loc[jst(h, m, day), ["open", "high", "low", "close"]] = [px + o * pp, px + hi * pp, px + lo * pp, px + c * pp]


def world(day=DAY, spread=None, **moves):
    bars = {p: base_bars(p, day, (spread or {}).get(p, 1.0)) for p in SB.PAIRS}
    for p, mv in moves.items():
        for (h, m), v in mv.items():
            put(bars[p], p, h, m, *v, day=day)
    return bars


def D_of(bars, day=DAY):
    return SB.panel_of(bars, (day - dt.timedelta(days=1)).isoformat(), day.isoformat())


def sim(bars, day=DAY, E=None, **kw):
    return SB.simulate(D_of(bars, day), E or NOEV, **kw)


def flat(p, h0, m0, h1, m1, v=(25, 27, 23, 25)):
    """h0:m0〜h1:m1 の足を同じ形にする（入ったあと、損切りにも利確にも届かない）"""
    out, t = {}, dt.datetime(2000, 1, 1, h0, m0)
    while (t.hour, t.minute) <= (h1, m1):
        out[(t.hour, t.minute)] = v
        t += dt.timedelta(minutes=5)
    return out


YEN_UP = {"EURJPY": {(16, 10): (0, 20, 0, 20)}, "GBPJPY": {(16, 10): (0, 25, 0, 25), (16, 15): (25, 30, 22, 28), (16, 20): (28, 50, 27, 45)}}


# ── 登録の値 ──────────────────────────────────

def test_registered_numbers():
    assert (SB.MIN_PAIRS, SB.SL_OUT, SB.TP_PIPS, SB.SPREAD_MAX, SB.COST_MULT) == (2, 4.0, 20.0, 2.5, 7.0)
    assert (SB.BEFORE_FROM, SB.FLAT_BEFORE, SB.WAIT_AFTER, SB.END_AFTER, SB.EARLIEST) == (60, 5, 30, 120, 905)
    assert (SB.EV_BEFORE, SB.EV_AFTER, SB.EV_EXIT) == (60, 30, 5) and SB.LINE == (480, 900)
    assert (SB.N_MIN_A, SB.N_MIN_B, SB.ALPHA) == (200, 100, 0.05) and abs(SB.Z - 1.95996) < 1e-4
    assert (SB.SEEN_START, SB.OLD, SB.SPLIT_A, SB.SPLIT_B) == ("2022-06-01", ("2017-01-01", "2022-05-31"), "2024-08-01", "2019-10-01")


def test_series_pairs_share_one_currency_on_the_same_side():
    names = {"クロス円": "JPY", "ドルストレート": "USD", "ユーロ": "EUR", "ポンド": "GBP", "豪ドル": "AUD"}
    assert set(SB.SERIES) == set(names)
    for name, cur in names.items():
        pairs = SB.SERIES[name]
        assert len(pairs) >= 2 and set(pairs) <= set(SB.PAIRS)
        assert len({p.index(cur) for p in pairs}) == 1                     # みんな同じ側＝「同じ向き」は抜けた向きが同じ
    assert SB.SERIES["クロス円"] == ("USDJPY", "EURJPY", "GBPJPY", "AUDJPY") and SB.SERIES["ドルストレート"] == ("EURUSD", "GBPUSD", "AUDUSD")


def test_windows_follow_v5_and_addendum_14():
    assert SB.windows(DAY) == {"前": (960, 1015, 960, 1015), "後": (1050, 1140, 1020, 1140)}        # 冬：16:00〜16:54・17:30〜18:59
    assert SB.windows(SUMMER) == {"前": (905, 955, 905, 955), "後": (990, 1080, 960, 1080)}      # 夏：15:05〜15:54（15:00 は線）・16:30〜17:59


# ── 合図と入るペア ───────────────────────────────

def test_two_yen_pairs_break_and_the_one_that_moved_most_is_bought():
    r = sim(world(**YEN_UP))
    assert len(r["signals"]) == 1 and len(r["trades"]) == 1
    t = r["trades"][0]
    assert (t["series"], t["d"], t["seg"], t["pair"], t["n_broken"], t["minute"]) == ("クロス円", 1, "前", "GBPJPY", 2, 16 * 60 + 10)
    assert t["entry"] == pytest.approx(100.26) and t["sl_dist"] == pytest.approx(20.0) and t["spread"] == pytest.approx(1.0)
    assert t["exit"] == "tp" and t["after"] == pytest.approx(20.0) and t["r"] == pytest.approx(1.0) and t["cost"] == pytest.approx(1.0)


def test_one_pair_alone_is_not_a_signal():
    r = sim(world(GBPJPY=YEN_UP["GBPJPY"]))
    assert r["signals"] == [] and r["trades"] == []


def test_stop_comes_first_when_both_are_touched_in_one_bar():
    mv = dict(YEN_UP, GBPJPY={**YEN_UP["GBPJPY"], **{(16, 20): (28, 50, 0, 45)}})
    t = sim(world(**mv))["trades"][0]
    assert t["exit"] == "sl" and t["after"] == pytest.approx(-20.0) and t["r"] == pytest.approx(-1.0)


def test_gap_through_the_stop_fills_at_the_open():
    mv = dict(YEN_UP, GBPJPY={**YEN_UP["GBPJPY"], **{(16, 20): (2, 3, 1, 2)}})
    t = sim(world(**mv))["trades"][0]
    assert t["exit"] == "sl" and t["after"] == pytest.approx(-24.0)               # 始値 100.02＝損切り 100.06 の下


def test_time_exit_before_the_london_open():
    mv = dict(YEN_UP, GBPJPY={(16, 10): (0, 25, 0, 25), **flat("GBPJPY", 16, 15, 16, 50)})
    t = sim(world(**mv))["trades"][0]
    assert t["exit"] == "time" and t["after"] == pytest.approx(-26.0)            # 16:55 の足の始値（100.00）で出る


def test_stop_must_be_seven_spreads_away():
    mv = {"EURJPY": {(16, 10): (0, 11, 0, 11)}, "GBPJPY": {(16, 10): (0, 12, 0, 12), (16, 15): (12, 13, 11, 12)}}
    r = sim(world(spread={"GBPJPY": 2.0}, **mv))
    assert r["trades"] == [] and r["skips"]["cost7"] == 1                       # 損切りまで 8pips＜2pips×7
    r = sim(world(**mv))
    assert len(r["trades"]) == 1 and r["trades"][0]["sl_dist"] == pytest.approx(7.0)   # 1pips×7＝7 はちょうど届く


def test_wide_spread_and_entry_back_inside_are_skipped():
    r = sim(world(spread={"GBPJPY": 2.6}, **YEN_UP))
    assert r["trades"] == [] and r["skips"]["spread"] == 1
    mv = dict(YEN_UP, GBPJPY={**YEN_UP["GBPJPY"], **{(16, 15): (3, 4, 2, 3)}})
    r = sim(world(**mv))
    assert r["trades"] == [] and r["skips"]["inside"] == 1                      # 買値 100.04＝もう損切り（100.06）の下
    mv = dict(YEN_UP, GBPJPY={**YEN_UP["GBPJPY"], **{(16, 15): (5, 6, 4, 5)}})
    r = sim(world(**mv))
    assert r["trades"] == [] and r["skips"]["inside"] == 1                      # 買値 100.06＝損切りの値ちょうど（幅 0）


def test_sell_on_the_dollar_straights():
    mv = {"EURUSD": {(16, 10): (0, 0, -20, -20)},
          "GBPUSD": {(16, 10): (0, 0, -25, -25), (16, 15): (-25, -22, -28, -26), (16, 20): (-26, -24, -46, -40)}}
    t = sim(world(**mv))["trades"][0]
    assert (t["series"], t["d"], t["pair"]) == ("ドルストレート", -1, "GBPUSD")
    assert t["entry"] == pytest.approx(1.0975) and t["sl_dist"] == pytest.approx(19.0)
    assert t["exit"] == "tp" and t["after"] == pytest.approx(20.0)              # 買値の安値 1.0954＋0.0001＝1.0955


def test_sell_stop_uses_the_ask():
    mv = {"EURUSD": {(16, 10): (0, 0, -20, -20)},
          "GBPUSD": {(16, 10): (0, 0, -25, -25), (16, 15): (-25, -22, -28, -26), (16, 20): (-26, -7, -27, -20)}}
    t = sim(world(**mv))["trades"][0]
    assert t["exit"] == "sl" and t["after"] == pytest.approx(-19.0)             # 売値の高値 1.0993＋0.0001＝1.0994


# ── 時間の窓 ─────────────────────────────────

def test_no_signal_when_the_entry_bar_would_be_the_flat_time():
    late = {"EURJPY": {(16, 50): (0, 20, 0, 20)}, "GBPJPY": {(16, 50): (0, 25, 0, 25)}}
    assert sim(world(**late))["signals"] == []                                  # 入るのは 16:55＝手じまいの時刻
    ok = {"EURJPY": {(16, 45): (0, 20, 0, 20)}, "GBPJPY": {(16, 45): (0, 25, 0, 25), (16, 50): (25, 27, 23, 25)}}
    t = sim(world(**ok))["trades"][0]
    assert t["minute"] == 16 * 60 + 45 and t["exit"] == "time"


def test_after_the_open_waits_thirty_minutes_and_measures_from_the_open():
    mv = {"EURJPY": {(17, 30): (0, 20, 0, 20)}, "GBPJPY": {(17, 30): (0, 25, 0, 25), (17, 35): (25, 30, 22, 28), (17, 40): (28, 50, 27, 45)}}
    t = sim(world(**mv))["trades"][0]
    assert (t["seg"], t["minute"], t["pair"], t["exit"]) == ("後", 17 * 60 + 30, "GBPJPY", "tp")
    for h, m in ((17, 0), (17, 25)):
        early = {"EURJPY": {(h, m): (0, 20, 0, 20)}, "GBPJPY": {(h, m): (0, 25, 0, 25)}}
        assert sim(world(**early))["signals"] == []


def test_already_broken_before_the_window_is_not_a_new_signal():
    mv = {p: {(15, 55): (0, 20, 0, 20), (16, 0): (20, 22, 18, 20), (16, 5): (20, 22, 18, 20)} for p in ("EURJPY", "GBPJPY")}
    assert sim(world(**mv))["signals"] == []
    mv = {p: {(17, 25): (0, 20, 0, 20), (17, 30): (20, 22, 18, 20)} for p in ("EURJPY", "GBPJPY")}
    assert sim(world(**mv))["signals"] == []                                   # 17:25 にそろった＝17:30 からの「新しく考える」では合図にしない


def test_after_window_time_exit_is_two_hours_after_the_open():
    mv = {"EURJPY": {(17, 30): (0, 20, 0, 20)}, "GBPJPY": {(17, 30): (0, 25, 0, 25), **flat("GBPJPY", 17, 35, 18, 55)}}
    t = sim(world(**mv))["trades"][0]
    assert t["exit"] == "time" and t["hold_min"] == pytest.approx(85.0)           # 17:35 → 19:00


def test_summer_windows():
    mv = {"EURJPY": {(15, 5): (0, 20, 0, 20)}, "GBPJPY": {(15, 5): (0, 25, 0, 25), (15, 10): (25, 30, 22, 28), (15, 15): (28, 50, 27, 45)}}
    t = sim(world(day=SUMMER, **mv), day=SUMMER)["trades"][0]
    assert (t["season"], t["seg"], t["minute"]) == ("夏", "前", 15 * 60 + 5)
    mv = {"EURJPY": {(16, 25): (0, 20, 0, 20)}, "GBPJPY": {(16, 25): (0, 25, 0, 25)}}
    assert sim(world(day=SUMMER, **mv), day=SUMMER)["signals"] == []           # 夏の 16:25＝始まりの30分の中


def test_friday_is_skipped():
    r = sim(world(day=FRIDAY, **{p: {(h, m): v for (h, m), v in mv.items()} for p, mv in YEN_UP.items()}), day=FRIDAY)
    assert r["signals"] == [] and r["stats"]["weekday_days"] == 0


# ── 1つのシリーズ・向き・窓に1回・同じペアは重ねない ───────────────────

def test_first_signal_only_per_series_direction_and_window():
    mv = {"EURJPY": {(16, 10): (0, 20, 0, 20), (16, 30): (0, 20, 0, 20)},
          "GBPJPY": {**YEN_UP["GBPJPY"], **{(16, 30): (0, 25, 0, 25)}}}
    r = sim(world(**mv))
    assert len([g for g in r["signals"] if g["series"] == "クロス円"]) == 1


def test_same_pair_from_two_series_is_not_doubled():
    mv = dict(YEN_UP, GBPUSD={(16, 10): (0, 15, 0, 15)})                         # ポンドのシリーズもそろう → 選ぶのは同じポンド円
    r = sim(world(**mv))
    assert {g["series"] for g in r["signals"]} == {"クロス円", "ポンド"} and len(r["trades"]) == 1 and r["skips"]["busy"] == 1


# ── 発表 ────────────────────────────────────

def test_event_blocks_the_entry_and_forces_the_exit():
    E = dict(NOEV, GBPJPY=np.array([jst(16, 40).value], dtype=np.int64))
    r = sim(world(**YEN_UP), E=E)
    assert r["trades"] == [] and r["skips"]["event"] == 1                       # 16:15 は 16:40 の60分前の中
    mv = {"EURJPY": {(17, 30): (0, 20, 0, 20)}, "GBPJPY": {(17, 30): (0, 25, 0, 25), **flat("GBPJPY", 17, 35, 18, 55)}}
    E = dict(NOEV, GBPJPY=np.array([jst(18, 50).value], dtype=np.int64))
    t = sim(world(**mv), E=E)["trades"][0]
    assert t["exit"] == "event" and t["hold_min"] == pytest.approx(70.0)          # 17:35 → 18:45


def test_read_events_maps_to_the_seven_pairs(tmp_path):
    p = tmp_path / "ev.csv"
    p.write_text("utc,name,scope\n2026-01-05 13:30,米雇用統計,ALL\n2026-01-06 10:00,独CPI,EUR\n2026-01-07 09:30,英GDP GBPJPY,\n"
                 "2026-01-08 02:00,中国PMI,CNY\n2026-01-09 03:00,日銀,JPY\n", encoding="utf-8")
    E = SB.read_events(str(p))
    n = {k: len(v) for k, v in E.items()}
    assert n == {"USDJPY": 2, "EURUSD": 3, "GBPUSD": 3, "EURJPY": 3, "GBPJPY": 3, "AUDJPY": 3, "AUDUSD": 3}
    assert jst(22, 30, dt.date(2026, 1, 5)).value in E["EURUSD"]                   # 米国の発表はドルストレートにも当てる


# ── 偽薬・判定・記録 ─────────────────────────────

def test_placebo_is_deterministic_and_in_range():
    D = D_of(world(**YEN_UP))
    r = SB.simulate(D, NOEV, collect_pool=True)
    p1, m1 = SB.placebo(D, NOEV, r["trades"], r["pool"], n_perm=50)
    p2, m2 = SB.placebo(D, NOEV, r["trades"], r["pool"], n_perm=50)
    assert (p1, m1) == (p2, m2) and 0 < p1 <= 1
    assert all(960 + 5 <= D["minute"][k] < 1015 or 1050 + 5 <= D["minute"][k] < 1140 for k, _x, _b in r["pool"]["GBPJPY"])
    assert SB.placebo(D, NOEV, [], r["pool"]) == (None, None)


def test_check_mode_counts_without_pnl():
    r = sim(world(**YEN_UP), pnl=False)
    assert len(r["trades"]) == 1 and "after" not in r["trades"][0]


def test_judge_gates():
    good = {"n": 250, "mean": 2.0, "lo": 0.5, "hi": 3.5, "old_mean": 1.0, "new_mean": 2.5}
    goodb = {"n": 150, "mean": 1.5, "lo": 0.1, "hi": 2.9, "old_mean": 1.0, "new_mean": 2.0}
    assert SB.judge(good, 0.01, goodb) == SB.SURVIVED
    assert SB.judge(dict(good, n=199), 0.01, goodb) == "検定不能"
    assert SB.judge(dict(good, lo=-0.1), 0.01, goodb) == "0と区別できない"
    assert SB.judge(dict(good, mean=-2, lo=-3, hi=-0.5), 0.01, goodb) == "費用後マイナス"
    assert SB.judge(good, 0.05, goodb) == "でたらめな足と差なし"
    assert SB.judge(dict(good, old_mean=-0.1), 0.01, goodb) == "前半と後半で割れた"
    assert SB.judge(good, 0.01, dict(goodb, n=99)) == "昔の期間は検定不能"
    assert SB.judge(good, 0.01, dict(goodb, lo=-0.1)) == "昔の期間で消えた"
    assert SB.judge(good, 0.01, dict(goodb, new_mean=-0.1)) == "昔の期間で消えた"
    assert SB.verdicts_of(SB.SURVIVED, good, "2026-11-25") == {}
    v = SB.verdicts_of("0と区別できない", dict(good, win=0.4), "2026-11-25")["SB"]
    assert v["status"] == "stop" and v["n"] == 250 and "0と区別できない" in v["reason"]


def test_summarize_and_markdown():
    trades = sim(world(**YEN_UP))["trades"]
    s = SB.summarize(trades, SB.SPLIT_A)
    assert s["n"] == 1 and s["mean"] == pytest.approx(20.0) and s["exits"]["tp"] == 1 and s["by_series"]["クロス円"]["n"] == 1
    rec = {"generated_jst": "x", "prereg_sha256": "a" * 64, "tool_sha256": "b" * 64, "data": {"A": "a", "B": "b"}, "verdict": "検定不能",
           "A": dict(s, placebo_p=None, placebo_mean=None), "B": {"n": 0}, "signals": {"A": 1, "B": 0}, "skips": {"A": {}, "B": {}}}
    md = SB.render_md(rec)
    assert "判定：検定不能" in md and "投資助言ではありません" in md


def test_missing_pairs_in_the_old_period_do_not_stop_the_count():
    bars = world(**YEN_UP)
    bars["AUDUSD"] = pd.DataFrame(columns=["open", "high", "low", "close", "so"])
    r = sim(bars)
    assert len(r["trades"]) == 1 and r["stats"]["line_missing_pairs"] == 1
    assert SB.panel_of({p: pd.DataFrame(columns=["open", "high", "low", "close", "so"]) for p in SB.PAIRS}, "2026-11-16", "2026-11-17") is None


def test_tool_fingerprint():
    assert len(SB.tool_sha256()) == 64


def test_cost_is_the_entry_spread_for_buys_and_the_exit_spread_for_sells():
    bars = world(**YEN_UP)
    bars["GBPJPY"].loc[jst(16, 20), "so"] = 0.03                               # 出る足だけスプレッド 3pips
    t = sim(bars)["trades"][0]
    assert t["cost"] == pytest.approx(1.0) and t["after"] == pytest.approx(20.0)   # 買いは入る足のスプレッド・出るのは売値
    mv = {"EURUSD": {(16, 10): (0, 0, -20, -20)},
          "GBPUSD": {(16, 10): (0, 0, -25, -25), (16, 15): (-25, -22, -28, -26), (16, 20): (-26, -24, -47, -40)}}
    bars = world(**mv)
    bars["GBPUSD"].loc[jst(16, 20), "so"] = 0.0002
    t = sim(bars)["trades"][0]
    assert t["exit"] == "tp" and t["cost"] == pytest.approx(2.0)                # 売りは出る足のスプレッド（買値＝売値＋2pips）


def test_run_end_to_end_with_made_up_bars(monkeypatch, tmp_path):
    import json
    import oikawa_lab as OK
    old_day = dt.date(2019, 11, 19)                                          # 火曜・冬（B）
    a, b = world(**YEN_UP), world(day=old_day, **YEN_UP)
    monkeypatch.setattr(SB, "load_all", lambda folder, duka: (a, b))
    monkeypatch.setattr(SB, "read_events", lambda path: NOEV)
    rec, trades = SB.run("x", "y", "z", n_perm=20)
    assert rec["kind"] == "backtest" and rec["unit"] == "pips" and rec["verdict"] == "検定不能" and rec["verdicts"]["SB"]["status"] == "stop"
    assert rec["A"]["n"] == 1 and rec["B"]["n"] == 1 and rec["progress"] == {"SB": 1} and len(trades["A"]) == len(trades["B"]) == 1
    assert rec["pairs_with_bars"]["A"] == list(SB.PAIRS) and rec["data"]["B"].startswith("2019-11-1")
    text = json.dumps(OK._clean(rec), ensure_ascii=False)
    assert "SB" in text and "判定：検定不能" in SB.render_md(OK._clean(rec))
    monkeypatch.chdir(tmp_path)
    SB.trades_csv(trades["A"], os.path.join("out", "a.csv"))
    assert os.path.exists(os.path.join("out", "a.csv"))
