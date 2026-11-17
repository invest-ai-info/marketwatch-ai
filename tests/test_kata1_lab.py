# -*- coding: utf-8 -*-
"""KT1（kata1_lab.py）のテスト。本物の値段は使わない＝作った足だけで、決まりどおりに動くかを見る"""
import datetime as dt
import lzma
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import kata1_lab as K  # noqa: E402

DAY = dt.date(2026, 11, 17)            # 冬（ロンドンの始まり＝日本時間 17:00）


def jst(h, m):
    return pd.Timestamp(dt.datetime(DAY.year, DAY.month, DAY.day, h, m), tz=K.JST).tz_convert("UTC")


def base_bars(spread=0.01):
    """8:00〜19:30（日本時間）の平らな5分足・線＝安値 99.90／高値 100.10"""
    idx = pd.date_range(jst(8, 0), jst(19, 30), freq="5min")
    df = pd.DataFrame({"open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0, "so": spread}, index=idx)
    df.loc[jst(8, 0), "low"] = 99.90
    df.loc[jst(8, 5), "high"] = 100.10
    return df


def put(df, h, m, o, hi, lo, c):
    df.loc[jst(h, m), ["open", "high", "low", "close"]] = [o, hi, lo, c]


def scenario(after_fill):
    """18:00 に3つそろって線（99.90）を割る → 18:05 に新安値 99.55 → 18:10 に 50%（99.725）で1発目。after_fill(df) でそのあとを決める"""
    bars = {}
    for p in K.PAIRS:
        df = base_bars()
        put(df, 18, 0, 99.95, 99.95, 99.60, 99.62)
        put(df, 18, 5, 99.62, 99.70, 99.55, 99.66)
        put(df, 18, 10, 99.66, 99.74, 99.64, 99.70)
        for (h, m) in [(t // 60, t % 60) for t in range(18 * 60 + 15, 19 * 60 + 35, 5)]:
            put(df, h, m, 99.70, 99.70, 99.70, 99.70)
        after_fill(df, p)
        bars[p] = df
    D = K.panel(bars, "2026-11-16", "2026-11-17")
    abn = {p: {DAY: False} for p in K.PAIRS}
    E = {p: np.array([], dtype=np.int64) for p in K.PAIRS}
    return D, abn, E


def run_day(after_fill, events=None):
    D, abn, E = scenario(after_fill)
    if events:
        E = events
    return D, K.simulate(D, E, abn)


def test_window_and_london_open():
    assert K.london_open_minute(dt.date(2026, 11, 17)) == 17 * 60
    assert K.london_open_minute(dt.date(2026, 7, 1)) == 16 * 60
    assert K.window_of(dt.date(2026, 11, 17))[1:] == (16 * 60, 18 * 60 + 55, 19 * 60)
    assert K.window_of(dt.date(2026, 7, 1))[1:] == (15 * 60 + 5, 17 * 60 + 55, 18 * 60)


def test_prereg_section_exists():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assert K.OK.section_sha256(os.path.join(here, K.PREREG), K.SECTION) is not None


def test_signal_entry_and_early_take_profit():
    def after(df, p):
        put(df, 18, 15, 99.70, 99.71, 99.60, 99.61)                 # 3つとも陰線＝そろった
        if p == "USDJPY":
            put(df, 18, 20, 99.61, 99.66, 99.60, 99.65)             # ドル円だけ陽線 → 次の足で早めに利確
        else:
            put(df, 18, 20, 99.61, 99.62, 99.58, 99.59)
        put(df, 18, 25, 99.64, 99.64, 99.64, 99.64)
    D, r = run_day(after)
    assert len(r["signals"]) == 1 and r["signals"][0]["minute"] == 18 * 60 and r["signals"][0]["s"] == -1
    tb = r["trades"]["B"][0]
    assert len(tb["positions"]) == 3
    q = [x for x in tb["positions"] if x["pair"] == "USDJPY"][0]
    assert abs(q["price"] - 99.725) < 1e-9                         # 50%＝線 99.90 と新安値 99.55 の真ん中
    assert q["exit"] == "early" and not q["second"]
    assert abs(q["after"] - (99.725 - 99.65) / 0.01 / 3) < 1e-6     # 18:25 の始値＋スプレッドで買い戻す・3分の1
    assert abs(q["before"] - q["after"] - 1 / 3) < 1e-6              # 費用＝スプレッド 1 pip × 3分の1
    v = K.signal_value(tb)
    assert abs(v["after"] - sum(x["after"] for x in tb["positions"]) / 3) < 1e-9


def test_take_profit_at_recent_low():
    def after(df, p):
        put(df, 18, 15, 99.70, 99.71, 99.53, 99.60)                 # 買値の安値 99.54 ≤ 直近安値 99.55
    D, r = run_day(after)
    q = r["trades"]["B"][0]["positions"][0]
    assert q["exit"] == "tp" and abs(q["after"] - (99.725 - 99.55) / 0.01 / 3) < 1e-6


def test_stop_loss_on_close_beyond_line_and_second_entry():
    def after(df, p):
        put(df, 18, 15, 99.70, 99.92, 99.69, 99.91)                 # 線に届いて2発目 → 終値も線の上＝損切り
        put(df, 18, 20, 99.93, 99.93, 99.93, 99.93)
    D, r = run_day(after)
    q = r["trades"]["B"][0]["positions"][0]
    assert q["second"] and q["exit"] == "sl"
    exp = ((99.725 - 99.94) / 3 + (99.90 - 99.94) * 2 / 3) / 0.01
    assert abs(q["after"] - exp) < 1e-6


def test_time_stop_at_london_plus_two_hours():
    D, r = run_day(lambda df, p: None)
    q = r["trades"]["B"][0]["positions"][0]
    assert q["exit"] == "time"
    assert abs(q["hold_min"] - 50) < 1e-9                          # 18:10 に入って 19:00 の始値で出る


def test_minimum_distance_and_timeout():
    def shallow(df, p):
        pass
    bars = {}
    for p in K.PAIRS:
        df = base_bars()
        put(df, 18, 0, 99.95, 99.95, 99.80, 99.85)                  # 線から 10 pips しか離れない
        put(df, 18, 5, 99.85, 99.89, 99.84, 99.88)                  # 50%（99.85）に届くが 20 pips 未満＝入らない
        bars[p] = df
    D = K.panel(bars, "2026-11-16", "2026-11-17")
    r = K.simulate(D, {p: np.array([], dtype=np.int64) for p in K.PAIRS}, {p: {DAY: False} for p in K.PAIRS})
    assert len(r["signals"]) == 1 and not r["trades"]["B"]


def test_wait_more_than_30_minutes_skips():
    bars = {}
    for p in K.PAIRS:
        df = base_bars()
        put(df, 18, 0, 99.95, 99.95, 99.60, 99.62)
        for (h, m) in [(18, 5), (18, 10), (18, 15), (18, 20), (18, 25), (18, 30), (18, 35)]:
            put(df, h, m, 99.62, 99.65, 99.61, 99.63)              # 50%（99.75）に届かない
        put(df, 18, 40, 99.63, 99.80, 99.62, 99.70)                 # 30分を過ぎてから届く＝入らない
        bars[p] = df
    D = K.panel(bars, "2026-11-16", "2026-11-17")
    r = K.simulate(D, {p: np.array([], dtype=np.int64) for p in K.PAIRS}, {p: {DAY: False} for p in K.PAIRS})
    assert not r["trades"]["B"]


def test_event_blocks_signal():
    ev = {p: np.array([jst(18, 10).value], dtype=np.int64) for p in K.PAIRS}
    D, r = run_day(lambda df, p: None, events=ev)
    assert not r["signals"]


def test_no_signal_when_already_below_before_window():
    bars = {}
    for p in K.PAIRS:
        df = base_bars()
        for t in range(15 * 60 + 30, 19 * 60 + 35, 5):
            put(df, t // 60, t % 60, 99.80, 99.85, 99.70, 99.80)    # 15:30 から3つとも線の下のまま（窓の前に割れた）
        bars[p] = df
    D = K.panel(bars, "2026-11-16", "2026-11-17")
    r = K.simulate(D, {p: np.array([], dtype=np.int64) for p in K.PAIRS}, {p: {DAY: False} for p in K.PAIRS})
    assert not r["signals"]


def test_abnormal_day_is_skipped():
    D, abn, E = scenario(lambda df, p: None)
    abn["GBPJPY"][DAY] = True
    r = K.simulate(D, E, abn)
    assert r["stats"]["abnormal"] == 1 and not r["signals"]


def test_gate_pair_by_eurgbp():
    assert K.gate_pair("GBPJPY", -1, 1) and not K.gate_pair("EURJPY", -1, 1)     # 売り・ユーロが強い → ポンド円
    assert K.gate_pair("EURJPY", -1, -1)                                           # 売り・ポンドが強い → ユーロ円
    assert K.gate_pair("EURJPY", 1, 1) and K.gate_pair("GBPJPY", 1, -1)            # 買いは逆
    assert not K.gate_pair("EURJPY", -1, 0)                                        # レンジの中は入らない


def test_arm_a_after_16_uses_one_pair_by_eurgbp():
    def after(df, p):
        if p == "GBPJPY":                                                          # ポンド円の終値を上げてユーロポンドをレンジの下へ
            put(df, 18, 5, 99.62, 99.70, 99.55, 99.80)
    D, r = run_day(after)
    ta = r["trades"]["A"]
    assert len(ta) == 1 and [q["pair"] for q in ta[0]["positions"]] == ["EURJPY"]
    assert ta[0]["positions"][0]["weight"] == 1.0


def test_abnormal_days_uses_only_past():
    idx = [dt.date(2020, 1, 1) + dt.timedelta(days=i) for i in range(300)]
    r = pd.Series([1.0] * 290 + [5.0] * 10, index=idx)
    out = K.abnormal_days(r)
    assert out[idx[269]] is None and out[idx[270]] is False
    assert out[idx[290]] is False                    # その日の値幅はまだ平均に入らない（前の日まで）
    assert out[idx[291]] is True


def test_duka_files_to_5m(tmp_path):
    day = dt.date(2021, 3, 2)
    rec = np.dtype([("t", ">u4"), ("o", ">u4"), ("c", ">u4"), ("l", ">u4"), ("h", ">u4"), ("v", ">f4")])

    def write(side, rows):
        a = np.array(rows, dtype=rec)
        p = tmp_path / "USDJPY" / side
        p.mkdir(parents=True, exist_ok=True)
        (p / f"{day.isoformat()}.bi5").write_bytes(lzma.compress(a.tobytes()))
    write("BID", [(0, 100000, 100010, 99990, 100020, 1.0), (60, 100010, 100030, 100000, 100040, 1.0), (300, 100030, 100030, 100030, 100030, 0.0)])
    write("ASK", [(0, 100005, 100015, 99995, 100025, 1.0), (60, 100015, 100035, 100005, 100045, 1.0), (300, 100035, 100035, 100035, 100035, 0.0)])
    df = K.read_duka(str(tmp_path), "USDJPY", day.isoformat(), day.isoformat())
    assert len(df) == 1                              # 300秒の分は取引量が0＝使わない
    row = df.iloc[0]
    assert abs(row["open"] - 100.0) < 1e-9 and abs(row["close"] - 100.03) < 1e-9
    assert abs(row["high"] - 100.04) < 1e-9 and abs(row["low"] - 99.99) < 1e-9
    assert abs(row["so"] - 0.005) < 1e-9


def test_read_events_pairs_and_all(tmp_path):
    p = tmp_path / "ev.csv"
    p.write_text("utc,name,pairs\n2024-01-05 13:30:00,米雇用統計,4ペアとも\n2024-01-10 07:00:00,英GDP,GBPJPY\n"
                 "2024-01-11 10:00:00,ユーロ圏CPI,EURJPY\n", encoding="utf-8")
    E = K.read_events(str(p))
    assert len(E["USDJPY"]) == 1 and len(E["GBPJPY"]) == 2 and len(E["EURJPY"]) == 2


def test_judge_order():
    good = {"n": 300, "lo": 0.1, "hi": 2.0, "old_mean": 1.0, "new_mean": 1.0, "commission_mean": 0.5}
    assert K.judge(dict(good, n=100), 0.01, {"mean": 1, "commission_mean": 1}) == "検定不能"
    assert K.judge(dict(good, lo=-0.5, hi=-0.1), 0.01, {"mean": 1, "commission_mean": 1}) == "費用後マイナス"
    assert K.judge(good, 0.2, {"mean": 1, "commission_mean": 1}) == "でたらめな足と差なし"
    assert K.judge(dict(good, new_mean=-0.1), 0.01, {"mean": 1, "commission_mean": 1}) == "前半と後半で割れた"
    assert K.judge(good, 0.01, {"mean": -1, "commission_mean": -1}) == "昔の期間で消えた"
    assert K.judge(good, 0.01, {"mean": 0.5, "commission_mean": -0.1}) == "手数料で消える"
    assert K.judge(good, 0.01, {"mean": 0.5, "commission_mean": 0.1}) == K.SURVIVED


def test_summary_placebo_and_render_smoke(tmp_path):
    D, abn, E = scenario(lambda df, p: put(df, 18, 15, 99.70, 99.71, 99.53, 99.60))
    r = K.simulate(D, E, abn, collect_pool=True)
    s = K.summarize(r["trades"]["B"])
    assert s["n"] == 1 and s["exits"]["tp"] == 3
    p, pm = K.placebo(D, E, r["trades"]["B"], r["pool"], n_perm=5)
    assert p is not None and 0 < p <= 1
    s["placebo_p"], s["placebo_mean"] = p, pm
    arms = {"A": {"seen": s, "old": {"n": 0}, "verdict": K.judge(s, p, {"n": 0}), "not_entered_seen": 0},
            "B": {"seen": s, "old": {"n": 0}, "verdict": K.judge(s, p, {"n": 0}), "not_entered_seen": 0}}
    rec = K.OK._clean({"generated_jst": "x", "prereg_sha256": "abc", "data": {"seen": "a", "old": "b"}, "arms": arms,
                       "verdicts": K.verdicts_of(arms, "2026-11-17")})
    md = K.render_md(rec)
    assert "KT1-A" in md and "検定不能" in md
    assert rec["verdicts"]["KT1-B"]["status"] == "stop"
    K.trades_csv(r["trades"], str(tmp_path / "t.csv"))
    assert (tmp_path / "t.csv").exists()
