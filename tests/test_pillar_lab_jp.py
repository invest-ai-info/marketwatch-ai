# -*- coding: utf-8 -*-
"""新しい柱・第2波＝日本株（pillar_lab_jp.py）のテスト。2026-09-27 新設。

値動き・届出はすべて作り物（ネットワークに出ない）。確かめること＝物差しが事前登録（PILLAR_PREREG.md の
「第2波・日本株」）どおりか、仕込んだ効果を見つけ・仕込まない効果を見つけないか。

実行:  python tests/test_pillar_lab_jp.py     （pytest 不要。pytest でも動く）
"""
import csv
import datetime as dt
import os
import shutil
import sys
import tempfile

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import pillar_lab_jp as J  # noqa: E402

D = dt.date


def test_prereg_numbers_match_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "## 第2波・日本株" in text
    assert J.J1_HOLD == 60 and "60営業日後の終値" in text and "翌営業日の終値" in text
    assert J.J1_COST_BPS == 20.0 and "往復0.2%" in text and J.J1_MIN_N == 200 and "件数200未満" in text
    assert J.J1_GAP == 60 and "60営業日以内に重なったら最初の1件だけ" in text and J.J1_BENCH == "1306.T"
    assert J.J2_T2_FROM == D(2019, 7, 16) and "2019年7月16日" in text and "2営業日前" in text and "3営業日前" in text
    assert J.J2_WINDOW == 10 and "10営業日前の終値" in text and J.J2_SPLIT == "2008-01-01" and "2008年から" in text
    assert J.J3W_WINDOW == 156 and "直前156週" in text and J.J3W_MIN_HIST == 104 and "104週以上" in text
    assert J.J3W_LAG == 4 and "4営業日後" in text and J.J3W_HOLD == 20 and "20営業日後" in text
    assert J.J3W_SPLIT == "2015-01-01" and "2015年から" in text and J.J3W_MIN_N == 100 and "件数100未満" in text


def test_new_report_and_yahoo_code():
    assert J.is_new_report("大量保有報告書") and J.is_new_report("大量保有報告書（特例対象株券等）")
    assert not J.is_new_report("変更報告書") and not J.is_new_report("訂正報告書（大量保有報告書・変更報告書）")
    assert not J.is_new_report("大量保有報告書（訂正）")
    assert J.yahoo_code("72030") == "7203.T" and J.yahoo_code("130A0") == "130A.T" and J.yahoo_code("") is None


def _market(n_stocks, effect, seed=1, n_days=900, events_per=2):
    """作り物の日足。届出の翌営業日から60営業日、その株だけ effect（対数）だけ市場を上回る"""
    rng = np.random.default_rng(seed)
    days = pd.bdate_range("2020-01-01", periods=n_days)
    bench = pd.Series(100 * np.exp(np.cumsum(rng.normal(0, 0.008, n_days))), index=days)
    prices, events = {}, []
    for s in range(n_stocks):
        tk = f"{1000 + s}.T"
        r = np.log(bench.values[1:] / bench.values[:-1])
        r = np.concatenate([[0.0], r]) + rng.normal(0, 0.015, n_days)
        for k in range(events_per):
            i = int(rng.integers(80 + k * 300, 300 + k * 300))
            d = days[i - 1].date()                      # 提出日（入るのは翌営業日）
            events.append({"ticker": tk, "date": d})
            r[i + 1:i + 1 + J.J1_HOLD] += effect / J.J1_HOLD
        prices[tk] = pd.Series(100 * np.exp(np.cumsum(r)), index=days)
    return sorted(events, key=lambda x: (x["ticker"], x["date"])), prices, bench


def test_j1_finds_planted_rise_and_not_nothing():
    ev, prices, bench = _market(150, 0.06)
    rows = J.j1_rows(ev, prices, bench)
    r = J.j1_stats(rows, J.j1_placebo(rows, prices, bench, n_perm=200))
    assert r["n"] >= J.J1_MIN_N and r["verdict"] == "届出のあと上がりやすい兆し", (r["n"], r["verdict"], r.get("mean"))
    ev, prices, bench = _market(150, 0.0, seed=2)
    rows = J.j1_rows(ev, prices, bench)
    assert J.j1_stats(rows, J.j1_placebo(rows, prices, bench, n_perm=200))["verdict"] == "差なし（偶然の範囲）"
    ev, prices, bench = _market(40, 0.06)
    rows = J.j1_rows(ev, prices, bench)
    assert J.j1_stats(rows, J.j1_placebo(rows, prices, bench, n_perm=50))["verdict"] == "件数不足"


def test_j1_enters_next_day_and_skips_repeats():
    days = pd.bdate_range("2021-01-04", periods=200)
    c = pd.Series(np.linspace(100, 120, 200), index=days)
    ev = [{"ticker": "X.T", "date": days[10].date()}, {"ticker": "X.T", "date": days[30].date()},   # 20営業日後＝重なり
          {"ticker": "X.T", "date": days[100].date()}]
    rows = J.j1_rows(ev, {"X.T": c}, c * 0 + 50.0)
    assert [r["date"] for r in rows] == [days[11].date().isoformat(), days[101].date().isoformat()]


def test_j2_uses_two_or_three_days_before_month_end():
    days = pd.bdate_range("2019-01-01", "2019-10-31")
    c = pd.Series(np.arange(len(days), dtype=float) + 1000.0, index=days)
    rows = {r["date"][:7]: r for r in J.j2_rows(c)}
    # 2019年3月の最終の取引日は29日（金）→ 3営業日前＝26日。9月は30日（月）→ 2営業日前＝26日
    i_mar = list(days.date).index(D(2019, 3, 26))
    assert abs(rows["2019-03"]["run"] - np.log(c.iloc[i_mar] / c.iloc[i_mar - 10]) * 1e4) < 1e-9
    i_sep = list(days.date).index(D(2019, 9, 26))
    assert abs(rows["2019-09"]["run"] - np.log(c.iloc[i_sep] / c.iloc[i_sep - 10]) * 1e4) < 1e-9
    assert "2019-10" in rows


def _n225(effect, seed=3):
    rng = np.random.default_rng(seed)
    days = pd.bdate_range("1990-01-01", "2026-08-31")
    r = rng.normal(0, 0.012, len(days))
    s = pd.Series(r, index=days)
    for (y, m), grp in s.groupby([s.index.year, s.index.month]):
        if m in (3, 9):
            k = s.index.get_loc(grp.index[-1])
            lag = 2 if grp.index[-1].date() >= J.J2_T2_FROM else 3
            r[k - lag - 9:k - lag + 1] += effect / 10
    return pd.Series(1000 * np.exp(np.cumsum(r)), index=days)


def test_j2_finds_planted_run_up_and_not_nothing():
    assert J.j2_stats(J.j2_rows(_n225(0.03)))["verdict"] == "権利取りの上昇が見える"
    assert J.j2_stats(J.j2_rows(_n225(0.0)))["verdict"] == "見えない（偶然の範囲）"


def test_history_is_read_back_without_duplicates():
    tmp = tempfile.mkdtemp()
    orig = J.HIST_DIR
    J.HIST_DIR = tmp
    try:
        for year, ids in (("2024", ["a", "b"]), ("2025", ["b", "c"])):
            with open(os.path.join(tmp, f"{year}.csv"), "w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=J.HIST_FIELDS)
                w.writeheader()
                for i in ids:
                    w.writerow({"date": f"{year}-01-05", "id": i, "desc": "大量保有報告書", "isec": "72030"})
        rows = J.load_history()
        assert [r["id"] for r in rows] == ["a", "b", "c"]
        assert J.j1_events(rows)[0]["ticker"] == "7203.T"
    finally:
        J.HIST_DIR = orig
        shutil.rmtree(tmp, ignore_errors=True)


def test_business_days_skip_weekends_and_holidays():
    bd = J.business_days(D(2026, 5, 1), D(2026, 5, 8))
    assert bd == [D(2026, 5, 1), D(2026, 5, 7), D(2026, 5, 8)]           # 連休（4〜6日）と土日を飛ばす


def _margin_sheet(weeks, ratio_of):
    """「信用取引現在高」と同じ形の表（月日の行＋委託/自己/合計、次の行に 売残高/買残高・各2列）"""
    rows = [["信用取引現在高"] + ["nan"] * 12, ["Outstanding"] + ["nan"] * 12, ["nan"] * 13,
            ["月日", "委託", "nan", "nan", "nan", "自己", "nan", "nan", "nan", "合計", "nan", "nan", "nan"],
            ["nan", "売残高", "nan", "買残高", "nan", "売残高", "nan", "買残高", "nan", "売残高", "nan", "買残高", "nan"]]
    rows.append([D(2001, 1, 31), "100", "1", "300", "1"] + ["1"] * 8)      # 古い月ごとの部分（使わない）
    rows.append([D(2001, 3, 31), "100", "1", "300", "1"] + ["1"] * 8)
    for k, d in enumerate(weeks):
        rows.append([d, "1000", "1", str(1000 * ratio_of(k)), "1"] + ["1"] * 8)
    rows.append(["注:", "nan"] + ["nan"] * 11)
    return pd.DataFrame(rows)


def test_parse_margin_sheet_keeps_weekly_part_only():
    weeks = [D(2002, 1, 4) + dt.timedelta(days=7 * k) for k in range(30)]
    ser = J.parse_margin_sheet(_margin_sheet(weeks, lambda k: 3.0))
    assert len(ser) == 30 and ser[0][0] == D(2002, 1, 4) and ser[0][1] == 1000 and ser[0][2] == 3000


def _j3w_data(effect, seed=7, n_weeks=1100):
    rng = np.random.default_rng(seed)
    weeks = [D(2003, 1, 3) + dt.timedelta(days=7 * k) for k in range(n_weeks)]
    ratio = np.exp(np.cumsum(rng.normal(0, 0.05, n_weeks)))
    ser = J.parse_margin_sheet(_margin_sheet(weeks, lambda k: ratio[k]))
    sig = dict(J.j3w_signals(ser))
    days = pd.bdate_range("2002-11-01", "2024-12-31")
    r = rng.normal(0, 0.012, len(days))
    dd = days.values.astype("datetime64[D]")
    for d, sgn in sig.items():                                        # 入る日から20営業日、予想の向きに動かす
        k = int(np.searchsorted(dd, np.datetime64(d), side="right")) - 1
        i0 = k + J.J3W_LAG
        r[i0 + 1:i0 + 1 + J.J3W_HOLD] += effect * sgn / J.J3W_HOLD
    close = pd.Series(10000 * np.exp(np.cumsum(r)), index=days)
    return ser, close


def test_j3w_finds_planted_contrarian_and_not_nothing():
    ser, close = _j3w_data(0.05)
    r = J.j3w_stats(J.j3w_rows(J.j3w_signals(ser), close), n_perm=300)
    assert r["n"] >= J.J3W_MIN_N and r["verdict"] == "個人の信用の偏りの逆の兆し", (r["n"], r["verdict"], r.get("mean"))
    ser, close = _j3w_data(0.0, seed=8)
    assert J.j3w_stats(J.j3w_rows(J.j3w_signals(ser), close), n_perm=300)["verdict"] == "差なし（偶然の範囲）"
    ser, close = _j3w_data(-0.05, seed=9)
    assert J.j3w_stats(J.j3w_rows(J.j3w_signals(ser), close), n_perm=300)["verdict"] == "個人と同じ向きの兆し"


def test_render_md_runs_on_partial_results():
    md = J.render_md({"generated_at": "x", "prereg_sha256": "a" * 64, "j1": {"error": "e"},
                      "j2": {"verdict": "見えない（偶然の範囲）", "by_month": {3: {"n": 1, "run": 1.0}}},
                      "j3": [{"url": "u", "ok": False, "error": "e"}], "collect": {"days_left": 3},
                      "j3f": {"files": [{"url": "f", "ok": True, "kind": "xls", "sheets": {"s": {"rows": 9, "cols": 4}}}]},
                      "j3w": {"verdict": "差なし（偶然の範囲）", "n": 120, "hold60": {"n": 1, "mean": 0.1}}})
    assert "投資助言ではありません" in md and "J3" in md and "計算できず" in md and "s（9行×4列）" in md


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
    print(f"--- {len(tests) - fails}/{len(tests)} 合格 ---")
    sys.exit(1 if fails else 0)
