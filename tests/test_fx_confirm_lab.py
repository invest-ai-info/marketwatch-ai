# -*- coding: utf-8 -*-
"""XC（fx_confirm_lab.py）のテスト。昔の FOMC のページの3つの形・ユーロドルだけの窓・費用の2段・月曜の窓の低い費用・判定・事前登録の数字。
2026-10-08 新設。

実行:  python tests/test_fx_confirm_lab.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))
import fx_clock_lab as X  # noqa: E402
import fx_confirm_lab as C  # noqa: E402
from test_fx_clock_lab import _bars, _gap_week, _with_range  # noqa: E402


def _close(a, b, tol=1e-6):
    return abs(a - b) <= tol * max(1.0, abs(b))


def test_parse_fomc_three_page_formats():
    p2004 = ('<h5>January 27-28 Meeting - 2004</h5><a href="/boarddocs/press/monetary/2004/20040128/default.htm">S</a>'
             '<h5>March 16 Meeting - 2004</h5><a href="/boarddocs/press/monetary/2004/20040316/default.htm">S</a>')
    assert C.parse_fomc_any(p2004) == [dt.date(2004, 1, 28), dt.date(2004, 3, 16)]
    p2008 = ('<h5>January 21 Conference Call - 2008</h5><a href="/newsevents/press/monetary/20080122b.htm">S</a>'
             '<h5>January 29-30 Meeting - 2008</h5><a href="/newsevents/press/monetary/20080130a.htm">S</a>'
             '<h5>December 15-16 Meeting - 2008</h5><a href="/newsevents/press/monetary/20081216b.htm">S</a>')
    assert C.parse_fomc_any(p2008) == [dt.date(2008, 1, 30), dt.date(2008, 12, 16)]                 # 電話会議は除く・b も読む
    p2015 = ('<h5 class="panel-heading panel-heading--shaded">January 27-28 Meeting - 2015</h5>'
             '<a href="/newsevents/pressreleases/monetary20150128a.htm">S</a>')
    assert C.parse_fomc_any(p2015) == [dt.date(2015, 1, 28)]


def test_fomc_dates_unreachable_years_are_not_counted():
    def opener(req):
        raise OSError("blocked")
    dates, status = C.fomc_dates(opener)
    assert dates == [] and all(v.startswith("取得できず") for v in status.values()) and len(status) == 8


def test_xc1_eurusd_only_with_two_cost_levels():
    """ロンドン 11:00〜13:00 にユーロドルが 0.1% 下がる値段 → XC1（ユーロドル売り）の費用前は +10bp"""
    def f(t):
        lt = t.tz_convert(X.LON)
        k = min(max((lt.hour + lt.minute / 60) - 11, 0), 2) / 2
        return 1.2 * (1 - 0.001 * k)
    bars = {"EURUSD": _bars("EURUSD", "2008-01-07", "2008-01-19", f, spread_pips=0.2)}
    days = [dt.date(2008, 1, d) for d in (7, 8, 9, 10, 11, 14, 15)]
    rows, pairs = C.window_rows("X3", bars, days, {"EURUSD": -1})
    assert len(rows) == 7 and all(r["n_pairs"] == 1 for r in rows)
    r = rows[0]
    assert abs(r["gross"] - 10.0) < 0.05
    assert _close(r["gross"] - r["net"], 0.00018 / 1.2 * 1e4, tol=1e-3)                            # 個人の費用 1.8pips
    assert _close(r["gross"] - r["net_low"], 0.00008 / 1.2 * 1e4, tol=1e-3)                        # 低い費用 0.8pips


def test_xc1_actual_spread_wins_when_wider():
    bars = {"EURUSD": _bars("EURUSD", "2008-01-07", "2008-01-09", spread_pips=3.0)}
    rows, _ = C.window_rows("X3", bars, [dt.date(2008, 1, 7)], {"EURUSD": -1})
    assert _close(rows[0]["gross"] - rows[0]["net_low"], 0.0003 / 1.2 * 1e4, tol=1e-3)            # 実際の差 3pips


def test_xc2_gap_trades_get_low_cost():
    f = _gap_week(1.2000, 1.2040, lambda h: 1.2040 - 0.0010 * min(h, 4))
    d = _with_range(_bars("EURUSD", "2023-12-01", "2024-01-16", f), 0.0004)                       # 窓の週は X のテストと同じ（日付は数え方に関係しない）
    tr = C.gap_trades_low({"EURUSD": d})
    t = [x for x in tr if x["week"] == "2024-01-15"]
    assert len(t) == 1, tr
    x = t[0]
    assert _close(x["gross"] - x["net_low"], max(0.00008 / x["entry"] * 1e4, x["actual"]), tol=1e-6)
    assert x["net_low"] > x["net"]
    rows = C.week_rows(tr)
    assert all(set(r) >= {"gross", "net", "net_low"} for r in rows)


def test_judge_levels():
    def s(m, lo, a=1.0, b=1.0):
        return {"mean": m, "lo": lo, "hi": m + 1, "first": a, "second": b}
    good, bad = s(1.0, 0.2), s(-1.0, -2.0, -1.0, -1.0)
    assert C.judge({"gross": good, "net": good, "low": good}) == C.VERDICTS[0]
    assert C.judge({"gross": good, "net": bad, "low": good}) == C.VERDICTS[1]
    assert C.judge({"gross": good, "net": bad, "low": bad}) == C.VERDICTS[2]
    assert C.judge({"gross": s(1.0, 0.2, 1.0, -0.1), "net": bad, "low": bad}) == C.VERDICTS[3]     # 後半がマイナス
    assert C.judge({"gross": bad, "net": bad, "low": bad}) == C.VERDICTS[3]


def test_stats_min_n_and_halves():
    rng = np.random.default_rng(0)
    days = pd.bdate_range("2004-01-05", "2011-12-30")
    rows = [{"date": d.date().isoformat(), "gross": 3 + g, "net": 1 + g, "net_low": 2 + g} for d, g in zip(days, rng.normal(0, 4, len(days)))]
    st = C.stats(rows, "XC1")
    assert st["verdict"] == C.VERDICTS[0] and st["n_first"] > 900 and st["n_second"] > 900
    assert C.stats(rows[:40], "XC3")["verdict"] == C.VERDICTS[4]


def test_list_verdicts_only_stops():
    base = {"n": 600, "net": {"mean": -1.0, "lo": -2.0, "hi": 0.1}}
    res = {"XC1": {**base, "verdict": C.VERDICTS[2]}, "XC2": {**base, "verdict": C.VERDICTS[1]}, "XC3": {**base, "verdict": C.VERDICTS[3]}}
    v = C.list_verdicts(res, "2026-10-08")
    assert set(v) == {"XC1", "XC3"} and _close(v["XC1"]["mean"], -1e-4) and v["XC1"]["status"] == "stop"


def test_constants_match_preregistration():
    txt = open(os.path.join(ROOT, "PILLAR_PREREG.md"), encoding="utf-8").read()
    sec = txt.split("## XC X の読むための表から出た候補を", 1)[1].split("\n## ", 1)[0]
    assert "2004-01-05〜2011-12-30" in sec and (C.START, C.END) == ("2004-01-05", "2011-12-30")
    assert "2004〜2007年／2008〜2011年" in sec and C.HALF == "2008-01-01"
    assert "円のペア 0.6pips・ほか 0.8pips" in sec and C.LOW_PIPS == {"JPY": 0.6, "other": 0.8}
    assert "**0.5 以上**" in sec and C.GAP_MIN == 0.5
    assert "**98.33%の幅**" in sec and _close(C.ALPHA, 0.05 / 3) and "10,000回" in sec and C.N_BOOT == 10000
    assert "XC1 500・XC2 60・XC3 50" in sec and C.MIN_N == {"XC1": 500, "XC2": 60, "XC3": 50}
    assert "ロンドン 11:00 に始まる足の始値 → 12:00 に始まる足の終値" in sec
    assert "ロンドン 08:00 → ニューヨーク 15:00 に始まる足の終値" in sec
    assert C.PERIOD == ((2004, 1), (2011, 12)) and C.PERIOD == X.FB.EARLY


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
        except Exception as e:  # noqa: BLE001
            fails += 1
            print(f"  💥 {name}: {type(e).__name__}: {e}")
    print(f"--- {len(tests) - fails}/{len(tests)} 合格 ---")
    sys.exit(1 if fails else 0)
