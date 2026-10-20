# -*- coding: utf-8 -*-
"""evaluate_signal_outcomes.py の「利確1のその後」（after_tp1）のテスト。2026-10-20 新設。

利確1で勝ちが決まったシグナルを、その後も 1 時間足で追い、
利確2・入口・損切りのどれに先に届いたか／期限切れかを残す。今ある項目は一切変えないことも固定する。

実行:  python tests/test_after_tp1.py     （pytest 不要。pytest でも動く）
"""
import copy
import os
import sys
from datetime import datetime, timedelta, timezone

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import evaluate_signal_outcomes as E  # noqa: E402

JST = timezone(timedelta(hours=9))
FIRED = "2026-10-01T09:30:00+09:00"           # = 2026-10-01 00:30 UTC
TP1_AT = "2026-10-01T01:00:00+00:00"          # 利確1に届いた足
NOW_EARLY = datetime(2026, 10, 2, 12, 0, tzinfo=JST)    # 期限（発火+7日）の前
NOW_LATE = datetime(2026, 10, 9, 12, 0, tzinfo=JST)     # 期限の後


def _df(rows):
    """rows = [(UTC の時刻, 高値, 安値, 終値), ...] → yfinance と同じ形の 1 時間足"""
    idx = pd.DatetimeIndex([pd.Timestamp(r[0]) for r in rows])
    return pd.DataFrame({"Open": [r[3] for r in rows], "High": [r[1] for r in rows],
                         "Low": [r[2] for r in rows], "Close": [r[3] for r in rows]}, index=idx)


def _sig(short=False, tf="4h", tp1_at=TP1_AT, sid="s1", ticker="USDJPY=X"):
    if short:
        lv = {"entry": 100.0, "stop_loss": 101.5, "take_profit_1": 98.0, "take_profit_2": 97.0}
    else:
        lv = {"entry": 100.0, "stop_loss": 98.5, "take_profit_1": 102.0, "take_profit_2": 103.0}
    return {"id": sid, "ticker": ticker, "timeframe": tf, "fired_at": FIRED,
            "direction": "ショート（売り）" if short else "ロング（買い）", **lv,
            "outcome": "tp1", "outcome_resolved_at": tp1_at, "hit_tp1_at": tp1_at,
            "hit_sl_at": None, "hit_tp2_at": None,
            "max_favorable_excursion_pct": 2.1, "max_adverse_excursion_pct": -0.3}


TP1_BAR = ("2026-10-01T01:00:00+00:00", 102.1, 100.4, 101.8)   # ロングの利確1の足（入口には触れない）


def test_reaches_tp2():
    df = _df([TP1_BAR,
              ("2026-10-01T02:00:00+00:00", 102.5, 101.0, 102.2),
              ("2026-10-01T03:00:00+00:00", 103.2, 102.0, 103.0)])
    r = E.track_after_tp1(_sig(), df, NOW_EARLY)
    assert r["ended_by"] == "tp2", r
    assert r["tp2_at"] == "2026-10-01T03:00:00+00:00" and r["ended_at"] == r["tp2_at"], r
    assert r["entry_at"] is None and r["sl_at"] is None and r["order"] == ["tp2"], r
    assert r["tp1_bar"] == "ok" and r["tp1_bar_entry"] is False, r


def test_back_to_entry_keeps_tracking():
    df = _df([TP1_BAR, ("2026-10-01T02:00:00+00:00", 101.0, 99.8, 100.2)])
    r = E.track_after_tp1(_sig(), df, NOW_EARLY)
    assert r["entry_at"] == "2026-10-01T02:00:00+00:00" and r["order"] == ["entry"], r
    # 入口に戻っただけでは終わらない（利確2まで持つ出口のために、利確2か損切りまで追う）
    assert r["ended_by"] is None and r["ended_at"] is None, r


def test_back_to_sl():
    df = _df([TP1_BAR,
              ("2026-10-01T02:00:00+00:00", 101.0, 99.8, 100.2),
              ("2026-10-01T03:00:00+00:00", 100.3, 98.4, 98.6),
              ("2026-10-01T04:00:00+00:00", 103.5, 98.6, 103.2)])   # 損切りの後の利確2は数えない
    r = E.track_after_tp1(_sig(), df, NOW_EARLY)
    assert r["order"] == ["entry", "sl"], r
    assert r["ended_by"] == "sl" and r["sl_at"] == "2026-10-01T03:00:00+00:00" == r["ended_at"], r
    assert r["tp2_at"] is None, r


def test_same_bar_entry_and_tp2_puts_entry_first():
    df = _df([TP1_BAR, ("2026-10-01T02:00:00+00:00", 103.4, 99.9, 101.0)])
    r = E.track_after_tp1(_sig(), df, NOW_EARLY)
    assert r["order"] == ["entry", "tp2"], r            # 順番がわからない＝悪い側（入口）を先に
    assert r["entry_at"] == r["tp2_at"] == "2026-10-01T02:00:00+00:00", r
    assert r["ended_by"] == "tp2" and r["sl_at"] is None, r


def test_same_bar_sl_and_tp2_puts_sl_first():
    df = _df([TP1_BAR, ("2026-10-01T02:00:00+00:00", 103.4, 98.0, 101.0)])
    r = E.track_after_tp1(_sig(), df, NOW_EARLY)
    assert r["order"] == ["entry", "sl", "tp2"], r      # 入口→損切り→利確2 の順とみなす
    assert r["ended_by"] == "sl" and r["ended_at"] == "2026-10-01T02:00:00+00:00", r


def test_expired_uses_deadline_and_ignores_later_bars():
    df = _df([TP1_BAR,
              ("2026-10-01T02:00:00+00:00", 101.5, 100.5, 101.1),
              ("2026-10-07T23:00:00+00:00", 101.9, 100.6, 101.4),   # 期限（10-08 00:30 UTC）の前の最後の足
              ("2026-10-08T01:00:00+00:00", 103.5, 101.0, 103.2)])  # 期限の後＝数えない
    r = E.track_after_tp1(_sig(), df, NOW_LATE)
    assert r["ended_by"] == "expired", r
    assert datetime.fromisoformat(r["ended_at"]) == datetime(2026, 10, 8, 9, 30, tzinfo=JST), r
    assert r["last_close"] == 101.4 and r["tp2_at"] is None and r["order"] == [], r
    # 期限前なら、同じ足でもまだ追っている
    r2 = E.track_after_tp1(_sig(), df.iloc[:2], NOW_EARLY)
    assert r2["ended_by"] is None and r2["last_close"] is None, r2


def test_expired_after_entry_return():
    df = _df([TP1_BAR, ("2026-10-01T02:00:00+00:00", 101.0, 99.8, 100.2),
              ("2026-10-07T23:00:00+00:00", 100.9, 99.5, 99.7)])
    r = E.track_after_tp1(_sig(), df, NOW_LATE)
    assert r["ended_by"] == "expired" and r["entry_at"] == "2026-10-01T02:00:00+00:00", r
    assert r["last_close"] == 99.7, r


def test_tp1_bar_entry_touch_counts_as_before_tp1():
    # 利確1の足が入口にも触れていた＝足の中の順番はわからない→入口が先（利確1の前）とみなし、戻りには数えない
    df = _df([("2026-10-01T01:00:00+00:00", 102.1, 99.9, 101.8)])
    r = E.track_after_tp1(_sig(), df, NOW_EARLY)
    assert r["tp1_bar_entry"] is True and r["entry_at"] is None and r["order"] == [], r
    assert r["ended_by"] is None, r


def test_tp1_bar_reaching_tp2_counts():
    df = _df([("2026-10-01T01:00:00+00:00", 103.1, 100.4, 102.9)])
    r = E.track_after_tp1(_sig(), df, NOW_EARLY)
    assert r["ended_by"] == "tp2" and r["tp2_at"] == TP1_AT, r


def test_tp1_bar_missing_or_mismatch():
    df = _df([("2026-10-01T02:00:00+00:00", 101.5, 100.5, 101.0)])
    assert E.track_after_tp1(_sig(), df, NOW_EARLY)["tp1_bar"] == "missing"
    df = _df([("2026-10-01T01:00:00+00:00", 101.5, 100.5, 101.0)])   # 利確1に届いていない
    assert E.track_after_tp1(_sig(), df, NOW_EARLY)["tp1_bar"] == "mismatch"


def test_short_mirror():
    df = _df([("2026-10-01T01:00:00+00:00", 99.6, 97.9, 98.2),
              ("2026-10-01T02:00:00+00:00", 100.2, 98.5, 99.9),
              ("2026-10-01T03:00:00+00:00", 101.6, 99.8, 101.4)])
    r = E.track_after_tp1(_sig(short=True), df, NOW_EARLY)
    assert r["tp1_bar"] == "ok" and r["order"] == ["entry", "sl"], r
    assert r["entry_at"] == "2026-10-01T02:00:00+00:00" and r["ended_by"] == "sl", r
    df = _df([("2026-10-01T01:00:00+00:00", 99.6, 97.9, 98.2),
              ("2026-10-01T02:00:00+00:00", 98.5, 96.9, 97.0)])
    assert E.track_after_tp1(_sig(short=True), df, NOW_EARLY)["ended_by"] == "tp2"


def test_daily_signals_use_21_days():
    df = _df([TP1_BAR])
    s = _sig(tf="1d")
    assert E.track_after_tp1(s, df, datetime(2026, 10, 15, 12, 0, tzinfo=JST))["ended_by"] is None
    r = E.track_after_tp1(s, df, datetime(2026, 10, 22, 10, 0, tzinfo=JST))
    assert r["ended_by"] == "expired", r
    assert datetime.fromisoformat(r["ended_at"]) == datetime(2026, 10, 22, 9, 30, tzinfo=JST), r


def test_other_timezone_index_matches_tp1_bar():
    # yfinance は為替の足をロンドン時間で返す（hit_tp1_at も "+01:00" で残る）
    tp1 = "2026-10-01T02:00:00+01:00"
    df = _df([TP1_BAR, ("2026-10-01T02:00:00+00:00", 103.2, 101.0, 103.0)])
    df.index = df.index.tz_convert("Europe/London")
    r = E.track_after_tp1(_sig(tp1_at=tp1), df, NOW_EARLY)
    assert r["tp1_bar"] == "ok" and r["ended_by"] == "tp2", r
    assert datetime.fromisoformat(r["tp2_at"]) == datetime(2026, 10, 1, 2, 0, tzinfo=timezone.utc), r


def _log():
    a = _sig(sid="a")
    b = _sig(sid="b", tp1_at="2026-10-01T02:00:00+00:00")
    b["outcome_resolved_at"] = b["hit_tp1_at"]
    c = _sig(sid="c", ticker="GC=F")
    done = _sig(sid="done", ticker="CL=F")
    done["after_tp1"] = {"v": 1, "ended_by": "tp2", "made_at": "2026-10-02T00:00:00+09:00"}
    sl = _sig(sid="sl", ticker="NQ=F")
    sl["outcome"] = "sl"
    pend = _sig(sid="pend", ticker="ES=F")
    pend["outcome"] = None
    noplan = {"id": "np", "ticker": "BTC-USD", "outcome": "no_plan", "direction": None}
    return [a, b, c, done, sl, pend, noplan]


def _fake_fetch(calls):
    def fetch(ticker, start_dt_utc, interval="1h"):
        calls.append((ticker, start_dt_utc))
        return _df([TP1_BAR, ("2026-10-01T02:00:00+00:00", 101.0, 99.8, 100.2)])
    return fetch


def test_update_fetches_once_per_ticker_and_keeps_old_fields():
    log = _log()
    before = copy.deepcopy(log)
    calls = []
    n = E.update_after_tp1(log, NOW_EARLY, fetch=_fake_fetch(calls))
    # 追う対象は「利確1で確定・その後が未確定」だけ。値段の取得は銘柄ごとに1回、いちばん早い利確1の時刻から
    assert sorted(t for t, _ in calls) == ["GC=F", "USDJPY=X"], calls
    start = dict(calls)["USDJPY=X"]
    assert start == datetime(2026, 10, 1, 1, 0, tzinfo=timezone.utc), start
    assert n == 3, n
    for old, new in zip(before, log):
        extra = set(new) - set(old)
        if old["id"] in ("a", "b", "c"):
            assert extra == {"after_tp1"}, (old["id"], extra)
        else:
            assert extra == set(), (old["id"], extra)
        for k, v in old.items():                     # 今ある項目は1つも変えない
            assert new[k] == v, (old["id"], k)
    a = log[0]["after_tp1"]
    assert a["v"] == 1 and a["entry_at"] == "2026-10-01T02:00:00+00:00" and a["ended_by"] is None, a
    assert a["made_at"] == NOW_EARLY.isoformat(timespec="seconds"), a
    # b の利確1の足は 02:00＝その足の入口への触れは利確1より前とみなす
    assert log[1]["after_tp1"]["entry_at"] is None and log[1]["after_tp1"]["tp1_bar_entry"] is True


def test_update_keeps_made_at_and_stops_after_end():
    log = _log()
    E.update_after_tp1(log, NOW_EARLY, fetch=_fake_fetch([]))
    calls = []
    E.update_after_tp1(log, NOW_LATE, fetch=_fake_fetch(calls))
    a = log[0]["after_tp1"]
    assert a["made_at"] == NOW_EARLY.isoformat(timespec="seconds"), a     # 最初に作った時刻は残す
    assert a["ended_by"] == "expired", a
    calls = []
    assert E.update_after_tp1(log, NOW_LATE, fetch=_fake_fetch(calls)) == 0
    assert calls == [], calls                                              # 終わったものは取りに行かない


def test_update_survives_missing_prices():
    log = _log()
    assert E.update_after_tp1(log, NOW_EARLY, fetch=lambda t, s, interval="1h": None) == 0
    assert all("after_tp1" not in e for e in log if e["id"] != "done")


def test_main_tracks_even_when_nothing_is_pending():
    log = [e for e in _log() if e["id"] != "pend"]
    saved = []
    orig = (E.load_log, E.save_log, E.fetch_prices_since)
    E.load_log, E.save_log = (lambda: log), (lambda lg: saved.append(copy.deepcopy(lg)))
    E.fetch_prices_since = _fake_fetch([])
    try:
        E.main()
    finally:
        E.load_log, E.save_log, E.fetch_prices_since = orig
    assert saved and "after_tp1" in saved[0][0], saved


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"✅ {name}")
            except Exception as e:  # noqa: BLE001
                fails += 1
                print(f"❌ {name}\n{type(e).__name__}: {e}")
    print("すべて期待どおり" if not fails else f"{fails}件 失敗")
    sys.exit(1 if fails else 0)
