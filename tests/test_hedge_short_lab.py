# -*- coding: utf-8 -*-
"""J35 J31 の売りを 1321.T の買いで打ち消す（hedge_short_lab.py）のテスト。2026-10-08 新設。

値動きはすべて作り物。確かめること＝①事前登録と定数の一致 ②1321.T の扱い（2011年から・値の付いていない日・±25％超を除く）
③1組の損益（売り＋買い・費用それぞれ 0.03％）④判定①の言葉（相場全体の分だけなら ✕・その株ならではなら ✅）
⑤収まる大きさと打ち消さない形の並び ⑥点検は損益を出さない・出力に銘柄コードを出さない ⑦ワークフローと SYNC 禁忌。

実行:  python tests/test_hedge_short_lab.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import hedge_short_lab as H  # noqa: E402


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "## J35 J31 の売りを、同じ金額の株価指数の買いで打ち消すと" in text and "**目隠しではない**" in text
    assert (H.HEDGE, H.HEDGE_START, H.HEDGE_COST, H.MAX_MOVE) == ("1321.T", "2011-01-01", 0.0003, 0.25)
    assert "**2011-01-01 から**" in text and "1321.T の寄り→大引け − 0.03％" in text
    assert [e[2][0] for e in H.ERAS] == ["2011-01-04", "2016-11-01", "2023-10-10"] and "**E1′ 2011-01-04〜2016-10-31**" in text
    assert H.N_Q == 2 and abs(H.ALPHA - 0.025) < 1e-12 and "p＜0.05÷2＝97.5％" in text and H.SIZES == (0.01, 0.02, 0.03, 0.05, 0.10)


def test_hedge_returns_rules():
    idx = pd.to_datetime(["2010-12-30", "2011-01-04", "2011-01-05", "2011-01-06", "2011-01-07"])
    df = pd.DataFrame({"Open": [100, 100, 100, 100, 100], "High": [101, 102, 100, 140, 101],
                       "Low": [99, 99, 100, 99, 99], "Close": [100, 101, 100, 130, 99]}, index=idx)
    r = H.hedge_returns(df)
    assert set(r) == {dt.date(2011, 1, 4).toordinal(), dt.date(2011, 1, 7).toordinal()}       # 2010年・値の付いていない日・+30％ は入れない
    assert abs(r[dt.date(2011, 1, 4).toordinal()] - 0.01) < 1e-12 and H.hedge_returns(None) == {}


def _row(day, code, gap, rc, turnover=15.0, rprev=0.0, ratio=1.0):
    r = np.full(len(H.C), np.nan)
    r[[H.C["day"], H.C["code"], H.C["gap"], H.C["rprev"], H.C["turnover"], H.C["tv_ratio"], H.C["rclose"], H.C["rhigh"], H.C["rlow"]]] = \
        [day, code, gap, rprev, turnover, ratio, rc, max(rc, 0), min(rc, 0)]
    return r


def _synthetic(own, mkt_drift, n=520, days_per_era=25, seed=1):
    """3つの時代。毎朝の相場全体（＝1321.T）は mkt_drift ± 0.5％。目印 B・C の株（20％）は相場全体＋own だけ動く"""
    rng = np.random.default_rng(seed)
    rows, hedge = [], {}
    for start in ("2012-03-01", "2018-03-01", "2025-03-03"):
        d0 = dt.date.fromisoformat(start)
        days = [d for d in (d0 + dt.timedelta(i) for i in range(days_per_era * 2)) if d.weekday() < 5][:days_per_era]
        for d in days:
            m = mkt_drift + rng.normal(0, 0.005)
            hedge[d.toordinal()] = m
            up = rng.uniform(size=n) < 0.2
            gaps = np.where(up, 0.04, 0.0) + rng.normal(0, 0.002, n)
            for c in range(n):
                rc = m + (own if up[c] else 0.0) + rng.normal(0, 0.004)
                rows.append(_row(d.toordinal(), c, gaps[c], rc, rprev=0.06 if up[c] else 0.0, ratio=7.0 if up[c] else 1.0))
    return np.array(rows), hedge


def test_pair_nets():
    A = np.array([_row(dt.date(2012, 3, 1).toordinal(), 0, 0.04, 0.02), _row(dt.date(2012, 3, 2).toordinal(), 1, 0.04, -0.01)])
    short, pair, h = H.pair_nets(A, {dt.date(2012, 3, 1).toordinal(): 0.015})
    assert abs(short[0] - (-0.02 - H.SHORT_COST)) < 1e-12 and abs(pair[0] - (-0.02 - H.SHORT_COST + 0.015 - H.HEDGE_COST)) < 1e-12
    assert np.isnan(pair[1]) and np.isnan(h[1]) and not np.isnan(short[1])


def test_judge_words_and_sizes():
    own = H.analyze(*_synthetic(-0.01, 0.0))
    assert all(j["summary"] == H.OK_ALL for j in own["judge"].values())
    mkt = H.analyze(*_synthetic(0.0, -0.01, seed=2))                  # 相場全体が下げただけ＝打ち消すと残らない
    assert mkt["judge"]["C0"]["summary"] == H.NONE and mkt["judge"]["C0"]["eras"]["e2"]["short"]["mean"] > 0.008
    x = own["forms"]["B0-top3"]
    assert set(x["eras"]["e3"]["sizes"]["0.03"]) == {"pair", "short"} and x["fit"] in (None,) + H.SIZES
    assert own["forms"]["C0-all"]["eras"]["e1"]["daily_pair"]["days"] == 25
    assert own["judge"]["B0"]["eras"]["e1"]["corr"] is None or -1 <= own["judge"]["B0"]["eras"]["e1"]["corr"] <= 1


def test_render_and_check_have_no_codes_or_returns():
    A, hedge = _synthetic(-0.005, 0.0, seed=4)
    res = H.analyze(A, hedge)
    md = H.render_md({"generated_at": "x", "prereg_sha256": "0" * 64, "result": dict(res, n_codes=520)})
    assert "判定①" in md and "判定②" in md and "目隠しではない" in md and "投資助言ではありません" in md and "売りだけ" in md
    assert "計算できず" in H.render_md({"generated_at": "x", "result": {"error": "e"}})
    out = H.check_summary(A, hedge, {"daily": [], "h1": [], "m5": []}, 520, None)
    assert not any(w in repr(out) for w in ("mean", "value", "'win'", "cagr")) and out["eras"]["e3"]["days_with_hedge"] == 25
    assert out["hedge_days"] == 75 and out["hedge_first"] == "2012-03-01"


def test_workflow_and_sync_forbidden():
    wf = open(".github/workflows/hedge-short-lab.yml", encoding="utf-8").read()
    assert "python -u hedge_short_lab.py --check" in wf and "restore-keys: jp-bars-" in wf and "yfinance" in wf
    assert "python tests/test_hedge_short_lab.py" in wf and "hedge-short-lab.json hedge-short-lab.md" in wf and "options: [check, run]" in wf
    assert '"hedge-short-lab.json", "hedge-short-lab.md"' in open("check_site_consistency.py", encoding="utf-8").read()


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"✅ {name}")
            except AssertionError as e:
                fails += 1
                print(f"❌ {name}: {e}")
    sys.exit(1 if fails else 0)
