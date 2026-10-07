# -*- coding: utf-8 -*-
"""X 為替の時計の癖（fx_clock_lab.py）のテスト。作った値段で、時刻（夏時間）・向き・費用・月曜の窓・FOMC の日の読み取り・判定を確かめる。
2026-10-07 新設。

実行:  python tests/test_fx_clock_lab.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import fx_clock_lab as X  # noqa: E402


def _close(a, b, tol=1e-6):
    return abs(a - b) <= tol * max(1.0, abs(b))


def _bars(pair, start, end, price_fn=None, spread_pips=0.2):
    """平日（日曜 22:00 UTC〜金曜 21:00 UTC）の1時間足。price_fn(足の始まり)＝その足の始値、終値＝次の足の始値"""
    idx = pd.date_range(start, end, freq="h", tz="UTC")
    wd, h = idx.weekday, idx.hour
    keep = ((wd < 4) | ((wd == 4) & (h < 21)) | ((wd == 6) & (h >= 22)))
    idx = idx[keep]
    base = 150.0 if pair.endswith("JPY") else 1.2
    f = price_fn or (lambda t: base)
    o = np.array([f(t) for t in idx], float)
    c = np.array([f(t + pd.Timedelta(hours=1)) for t in idx], float)
    s = spread_pips * X.pip(pair)
    return pd.DataFrame({"mo": o, "mh": np.maximum(o, c), "ml": np.minimum(o, c), "mc": c, "so": s, "sc": s}, index=idx)


def test_windows_follow_summer_time():
    s, w = dt.date(2024, 7, 10), dt.date(2024, 1, 10)
    i2, o2 = X.fix_windows("X2", [s, w])
    assert [t.hour for t in i2] == [15, 16] and [t.hour for t in o2] == [18, 19]          # ロンドン 16:00→19:00 の足（夏は UTC-1）
    i3, o3 = X.fix_windows("X3", [s])
    assert (i3[0].hour, o3[0].hour) == (10, 11)                                            # ロンドン 11:00・12:00（夏）
    i4, o4 = X.fix_windows("X4", [w])
    assert i4[0] == pd.Timestamp("2024-01-09 23:00", tz="UTC") and o4[0] == pd.Timestamp("2024-01-10 00:00", tz="UTC")
    i5, o5 = X.fix_windows("X5", [s, w])
    assert [t.hour for t in i5] == [7, 8] and [t.hour for t in o5] == [19, 20]             # NY 15:00 の足（夏 19 UTC・冬 20 UTC）


def test_days_skip_holidays():
    x3 = set(X.days_for("X3"))
    assert dt.date(2024, 3, 29) not in x3 and dt.date(2024, 4, 1) not in x3 and dt.date(2024, 3, 28) in x3   # 聖金曜日・復活祭の月曜
    assert dt.date(2024, 12, 26) not in x3 and dt.date(2024, 5, 1) not in x3
    x4 = set(X.days_for("X4"))
    assert dt.date(2024, 1, 8) not in x4 and dt.date(2024, 1, 3) not in x4 and dt.date(2024, 1, 4) in x4      # 成人の日・正月
    assert dt.date(2024, 7, 13) not in set(X.days_for("X2"))                                                  # 土曜


def test_prep_drops_bad_spreads_and_builds_mid():
    idx = pd.date_range("2024-01-08", periods=3, freq="h", tz="UTC")
    raw = pd.DataFrame({"bo": [1.1, 1.1, 1.1], "bh": [1.1] * 3, "bl": [1.1] * 3, "bc": [1.1] * 3, "v": [1.0] * 3,
                        "ao": [1.1002, 1.0999, 1.13], "ah": [1.1] * 3, "al": [1.1] * 3, "ac": [1.1002, 1.1002, 1.1002]}, index=idx)
    d, bad = X.prep(raw, "EURUSD")
    assert bad == 2 and len(d) == 1                                                        # 売値＞買値・差 200pips の足を落とす
    assert _close(d["mo"].iloc[0], 1.1001) and _close(d["so"].iloc[0] / X.pip("EURUSD"), 2.0)


def test_cost_is_the_larger_of_fixed_and_actual():
    d = _bars("USDJPY", "2024-01-08", "2024-01-09")
    t = pd.DatetimeIndex([pd.Timestamp("2024-01-08 10:00", tz="UTC")])
    g, n, c = X.trade_arrays(d, "USDJPY", t, t, 1)
    assert _close(c[0], 0.012 / 150 * 1e4) and _close(g[0], 0.0)                           # 決まった費用 1.2pips
    wide = d.copy()
    wide["so"] = wide["sc"] = 5 * X.pip("USDJPY")
    _, _, c2 = X.trade_arrays(wide, "USDJPY", t, t, 1)
    assert _close(c2[0], 0.05 / 150 * 1e4)                                                 # 実際の差 5pips のほうが大きい


def test_fix_rows_sign_and_pairs():
    """ロンドン 11:00〜13:00 にドルが 0.1% 上がる値段 → X3（ドル買い）の費用前は +10bp、X2（その時間外）は 0"""
    def mk(pair, s):
        def f(t):
            lt = t.tz_convert(X.LON)
            base = 150.0 if pair.endswith("JPY") else 1.2
            k = min(max((lt.hour + lt.minute / 60) - 11, 0), 2) / 2                        # 11時から13時にかけて 0→1
            return base * (1 + 0.001 * k) ** s
        return f
    bars = {p: _bars(p, "2024-01-08", "2024-01-20", mk(p, s)) for p, s in X.USD_BUY.items()}
    days = [dt.date(2024, 1, d) for d in (8, 9, 10, 11, 12, 15, 16)]
    rows, pairs = X.fix_rows("X3", bars, days)
    assert len(rows) == 7 and all(r["n_pairs"] == 7 for r in rows)
    assert all(abs(r["gross"] - 10) < 0.2 for r in rows), rows[0]
    rows2, _ = X.fix_rows("X2", bars, days)
    assert all(abs(r["gross"]) < 1e-6 for r in rows2) and all(r["net"] < 0 for r in rows2)
    few = {p: bars[p] for p in list(X.USD_BUY)[:4]}
    assert X.fix_rows("X3", few, days)[0] == []                                           # 5ペアそろわない日は数えない


def _gap_week(fri_px, open_px, path):
    """金曜まで fri_px、日曜 22:00 に open_px で始まり、月曜は path(時) の値段"""
    def f(t):
        if t < pd.Timestamp("2024-01-14 22:00", tz="UTC"):
            return fri_px
        if t < pd.Timestamp("2024-01-15 00:00", tz="UTC"):
            return open_px
        return path((t - pd.Timestamp("2024-01-15 00:00", tz="UTC")).total_seconds() / 3600)
    return f


def _with_range(d, width):
    d = d.copy()
    d["mh"] = d[["mo", "mc"]].max(axis=1) + width / 2
    d["ml"] = d[["mo", "mc"]].min(axis=1) - width / 2
    return d


def test_gap_trade_fills_at_friday_close():
    # 金曜 1.2000・月曜の窓 +0.0040（1日の値幅＝24本×0.0004…を作る）→ 月曜 03:00 に 1.2000 まで戻る
    f = _gap_week(1.2000, 1.2040, lambda h: 1.2040 - 0.0010 * min(h, 4))
    d = _with_range(_bars("EURUSD", "2023-12-01", "2024-01-16", f), 0.0004)
    tr = [x for x in X.gap_trades(d, "EURUSD") if x["week"] == "2024-01-15"]
    assert len(tr) == 1 and tr[0]["traded"] and tr[0]["filled"] and tr[0]["up"]
    assert _close(tr[0]["gross"], -(1.2000 / 1.2040 - 1) * 1e4, tol=1e-6)                  # 売り：1.2040 で入り 1.2000 で出る
    assert tr[0]["g"] > 0.25


def test_gap_trade_skips_when_filled_before_entry_and_times_out():
    filled = _gap_week(1.2000, 1.2040, lambda h: 1.2040)
    d = _with_range(_bars("EURUSD", "2023-12-01", "2024-01-16", filled), 0.0004)
    d.loc[pd.Timestamp("2024-01-14 23:00", tz="UTC"), "ml"] = 1.1995                      # 日曜 23:00 の足で埋まった
    tr = [x for x in X.gap_trades(d, "EURUSD") if x["week"] == "2024-01-15"]
    assert len(tr) == 1 and not tr[0]["traded"]
    stay = _with_range(_bars("EURUSD", "2023-12-01", "2024-01-16", _gap_week(1.2000, 1.2040, lambda h: 1.2040 + 0.0001 * h)), 0.0004)
    tr2 = [x for x in X.gap_trades(stay, "EURUSD") if x["week"] == "2024-01-15"][0]
    assert tr2["traded"] and not tr2["filled"]
    assert _close(tr2["gross"], -(1.2040 + 0.0001 * 20) / 1.2040 * 1e4 + 1e4, tol=1e-3)   # 19:00 の足の終値（＝20時の値）で出る


def test_week_rows_threshold():
    trades = [{"week": "2024-01-15", "traded": True, "g": 0.3, "gross": 5.0, "net": 3.0, "cost": 2.0},
              {"week": "2024-01-15", "traded": True, "g": 0.2, "gross": 50.0, "net": 48.0, "cost": 2.0},
              {"week": "2024-01-22", "traded": True, "g": 0.6, "gross": -1.0, "net": -3.0, "cost": 2.0}]
    rows = X.week_rows(trades)
    assert [r["date"] for r in rows] == ["2024-01-15", "2024-01-22"] and rows[0]["net"] == 3.0   # 0.25 未満は入れない


def test_parse_fomc_pages():
    hist = ('<h5 class="panel-heading">January 28-29 Meeting - 2020</h5><a href="/newsevents/pressreleases/monetary20200129a.htm">s</a>'
            '<h5 class="panel-heading">March 2 (unscheduled) Meeting - 2020</h5><a href="monetary20200303a.htm">s</a>'
            '<h5 class="panel-heading">March 19 (notation vote) - 2020</h5><a href="monetary20200323a.htm">s</a>'
            '<h5 class="panel-heading">April 28-29 Meeting - 2020</h5><a href="monetary20200429a.htm">s</a>')
    assert X.parse_fomc_hist(hist) == [dt.date(2020, 1, 29), dt.date(2020, 4, 29)]
    cur = ('<div class="fomc-meeting__month">Jan</div><div class="fomc-meeting__date">27-28</div>'
           '<a href="/newsevents/pressreleases/monetary20210127a.htm">Statement</a>'
           '<div class="fomc-meeting__month">Mar</div><div class="fomc-meeting__date">15 (unscheduled)</div>'
           '<a href="/newsevents/pressreleases/monetary20210315a.htm">Statement</a>')
    assert X.parse_fomc_current(cur) == [dt.date(2021, 1, 27)]


def test_fomc_dates_mark_unreachable_years():
    def opener(req):
        raise OSError("blocked")
    dates, status = X.fomc_dates(opener)
    assert dates == [] and status["2015"].startswith("取得できず")


def test_judge_rules():
    base = {"mean": 1.0, "lo": 0.2, "first": 1.0, "second": 1.0, "recent": 0.5}
    assert X.judge(base) == X.VERDICTS[0]
    assert X.judge({**base, "lo": -0.1}) == X.VERDICTS[1]
    assert X.judge({**base, "first": -0.2}) == X.VERDICTS[1]
    assert X.judge({**base, "recent": -0.1}) == X.VERDICTS[2]
    assert X.judge({**base, "mean": -0.1, "lo": -0.5}) == X.VERDICTS[2]


def test_stats_uses_99_and_min_n():
    rng = np.random.default_rng(0)
    days = pd.bdate_range("2012-01-02", "2026-09-30")
    rows = [{"date": d.date().isoformat(), "gross": 3 + g, "net": 1 + g, "cost": 2.0} for d, g in zip(days, rng.normal(0, 5, len(days)))]
    st = X.stats(rows, "X2")
    assert st["verdict"] == X.VERDICTS[0] and st["seen_before_cost"] and st["n_recent"] > 1000
    assert X.stats(rows[:50], "X5")["verdict"] == X.VERDICTS[3]


def test_constants_match_preregistration():
    txt = open(os.path.join(ROOT, "PILLAR_PREREG.md"), encoding="utf-8").read()
    sec = txt.split("## X 為替の時計の癖（第3波）", 1)[1].split("\n## ", 1)[0]
    assert "2012-01-02〜2026-09-30" in sec and (X.START, X.END) == ("2012-01-02", "2026-09-30")
    assert "円のペア 1.2pips・ほか 1.8pips" in sec and _close(X.FIXED_PIPS["JPY"], 1.2) and _close(X.FIXED_PIPS["other"], 1.8)
    assert "**0.25 以上**" in sec and X.GAP_MIN == 0.25 and "36時間以上" in sec and X.WEEK_GAP_H == 36
    assert "直近20日" in sec and X.ATR_DAYS == 20 and "足が20本以上" in sec and X.ATR_MIN_BARS == 20
    assert "月曜 19:00 UTC に始まる足の終値" in sec and X.EXIT_X1_UTC_H == 19
    assert "**99%の幅**" in sec and X.ALPHA == 0.01 and "10,000回" in sec and X.N_BOOT == 10000
    assert "2012〜2018年／2019〜2026-09" in sec and X.HALF == "2019-01-01" and "2021-01 から" in sec and X.RECENT == "2021-01-01"
    assert "X1〜X4 は300・X5 は80" in sec and X.MIN_N == {"X1": 300, "X2": 300, "X3": 300, "X4": 300, "X5": 80}
    assert "5つ以上そろった日" in sec and X.MIN_PAIRS == 5 and "100pips" in sec and X.MAX_SPREAD_PIPS == 100
    assert "欠けが5%を超えたら" in sec and X.MISSING_MAX == 0.05
    for w in ("ロンドン 16:00 に始まる足の始値", "19:00 に始まる足の終値（＝20:00）", "ロンドン 11:00 に始まる足の始値", "12:00 に始まる足の終値（＝13:00",
              "日本時間 8:00 に始まる足の始値", "9:00 に始まる足の終値（＝10:00", "ロンドン 08:00 に始まる足の始値", "ニューヨーク 15:00 に始まる足の終値"):
        assert w in sec, w
    assert len(X.USD_BUY) == 7 and sum(1 for s in X.USD_BUY.values() if s == 1) == 3


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
