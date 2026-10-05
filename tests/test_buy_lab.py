# -*- coding: utf-8 -*-
"""R2 余剰資金の入れ方（buy_lab.py）のテスト。作った値段で、買う日・買う量・資産・判定の決まりを確かめる。2026-10-05 新設。

実行:  python tests/test_buy_lab.py     （pytest 不要。pytest でも動く）
"""
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import buy_lab as B  # noqa: E402


def _close(a, b, tol=1e-9):
    return abs(a - b) <= tol * max(1.0, abs(b))


def test_next_hits_finds_first_day_at_or_after():
    dd = np.array([0, -0.05, -0.12, -0.03, -0.25, 0.0])
    h = B.next_hits(dd, 0.10)
    assert list(h) == [2, 2, 2, 4, 4, 6]
    assert list(B.next_hits(dd, 0.50)) == [6] * 6


def test_drawdown_uses_one_year_high():
    p = np.r_[np.full(10, 100.0), 80.0]
    assert _close(B.drawdown(p, win=5)[-1], -0.2)
    p2 = np.r_[200.0, np.full(10, 100.0)]          # 古い高値は5本の窓の外
    assert _close(B.drawdown(p2, win=5)[-1], 0.0)


def test_lump_and_monthly_wealth():
    p = np.array([100, 110, 120, 130, 140.0])
    ms = np.array([0, 1, 2, 3, 4])
    assert _close(B.wealth(p, B.schedule("L", ms, 0, 0), 4), 1.4)
    w = B.wealth(p, B.schedule("D", ms, 0, 0, k=2), 4)
    assert _close(w, 0.5 * 140 / 100 + 0.5 * 140 / 110)


def test_dip_buys_at_tiers_and_rest_at_deadline():
    n = 40
    ms = np.arange(n)                                 # 毎日を月初とみなす（期限＝24本後）
    hits = [np.full(n, n), np.full(n, n)]
    hits[0][:] = 5                                    # 1つめの段は5日目に届く
    sch = B.schedule("DIP", ms, 0, 0, hits=hits)
    assert sch == [(5, 0.5), (24, 0.5)]


def test_hybrid_stops_when_cash_runs_out():
    n = 40
    ms = np.arange(n)
    hits = [np.full(n, 3), np.full(n, 3), np.full(n, 4)]   # 3つの段がすぐ届く
    sch = B.schedule("HYB", ms, 0, 0, hits=hits)
    assert _close(sum(a for _, a in sch), 1.0)
    assert sch[-1][0] < 24                                   # 24か月より前に現金が尽きる
    no_hit = [np.full(n, n)] * 3
    sch2 = B.schedule("HYB", ms, 0, 0, hits=no_hit)
    assert len(sch2) == 24 and _close(sum(a for _, a in sch2), 1.0)


def test_fund_path_counts_cash_and_units():
    p = np.array([100, 50, 100.0])
    v, cash = B.fund_path(p, [(0, 0.5), (1, 0.5)], 0, 2)
    assert np.allclose(cash, [0.5, 0, 0]) and np.allclose(v, [1.0, 0.75, 1.5])


def test_start_grid_needs_one_year_and_ten_years_after():
    d = pd.bdate_range("2000-01-03", "2013-12-31")
    ms, grid = B.start_grid(d, 10)
    pos, s, e = grid[0]
    assert s >= B.HIGH_WIN and s == ms[pos]
    assert d[e] >= d[s] + pd.DateOffset(years=10) and d[e - 1] < d[s] + pd.DateOffset(years=10)
    assert all(d[e2] <= d[-1] for _, _, e2 in grid)


def test_judge_rules():
    base = {"mean_log": 0.02, "mean_log_first": 0.01, "mean_log_second": 0.03, "win": 0.6,
            "near_mean_log": {"a": 0.01, "b": 0.02}}
    assert B.judge(base, 0.001, 0.9) == B.VERDICTS[0]
    assert B.judge(base, 0.03, 0.9) == B.VERDICTS[1]
    assert B.judge(base, 0.20, 0.9) == B.VERDICTS[4]
    neg = {"mean_log": -0.02, "mean_log_first": -0.01, "mean_log_second": -0.03, "win": 0.3,
           "near_mean_log": {"a": -0.01, "b": -0.02}}
    assert B.judge(neg, 0.9, 0.001) == B.VERDICTS[2]
    assert B.judge(neg, 0.9, 0.03) == B.VERDICTS[3]
    assert B.judge({**base, "mean_log_second": -0.01}, 0.001, 0.9) == B.VERDICTS[4]


def test_evaluate_end_to_end_and_lump_vs_itself():
    rng = np.random.default_rng(4)
    d = pd.bdate_range("2004-01-01", "2020-12-31")
    px = pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0003, 0.011, len(d)))), index=d)
    r = B.evaluate(px, n_boot=20)
    assert set(r["results"]) == {"L", *B.METHODS}
    for m in B.METHODS:
        x = r["results"][m]
        assert x["verdict"] in B.VERDICTS and 0 < x["p_better"] <= 1 and 0 < x["p_worse"] <= 1
        assert 0 <= x["win"] <= 1 and 0 <= x["cash_share"] < 1
    # 毎日上がり続ける値段なら、一括がいちばん多く残る（分ける・待つは損）
    up = pd.Series(100 * np.exp(np.arange(len(d)) * 0.0004), index=d)
    r2 = B.evaluate(up, n_boot=5)
    for m in B.METHODS:
        assert r2["results"][m]["mean_log"] < 0 and r2["results"][m]["win"] == 0
    md = B.render_md({"generated_jst": "x", "prereg_sha256": "y", "missing": [], "assets": {"SP500": r}})
    assert "R2 余剰資金の入れ方" in md


def test_constants_match_preregistration():
    txt = open(os.path.join(ROOT, "PILLAR_PREREG.md"), encoding="utf-8").read()
    sec = txt.split("## R2 余剰資金の入れ方", 1)[1].split("\n## ", 1)[0]
    assert "0.05÷12" in sec and B.ALPHA == 0.05 / 12
    assert "1,000本" in sec and B.N_BOOT == 1000 and "平均250日" in sec and B.BLOCK == 250
    assert "10年後" in sec and B.HORIZON_Y == 10 and "5年後" in sec and B.READ_Y == 5
    assert "最初の252日" in sec and B.HIGH_WIN == 252
    assert "−10%・−20%・−30%・−40%" in sec and B.DIP_TIERS == (0.10, 0.20, 0.30, 0.40)
    assert "−10%・−20%・−30% に初めて" in sec and B.HYB_TIERS == (0.10, 0.20, 0.30)
    assert "9か月・15か月" in sec and "18か月・30か月" in sec and B.NEAR == (0.75, 1.25)
    assert "24か月たって" in sec and B.WINDOW_M == 24
    assert B.UNTIL == "2026-10-02" and "2026-10-02 まで" in sec


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
