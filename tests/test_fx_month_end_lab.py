# -*- coding: utf-8 -*-
"""R4 月末の値決め前の為替ヘッジ（fx_month_end_lab.py）のテスト。2026-10-05 新設。

実行:  python tests/test_fx_month_end_lab.py     （pytest 不要。pytest でも動く）
"""
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import fx_month_end_lab as R  # noqa: E402


def _series(d, vals):
    return pd.Series(np.asarray(vals, float), index=d)


def test_signal_direction_and_dates():
    d = pd.bdate_range("2019-12-01", "2020-03-31")
    fx = _series(d, np.full(len(d), 1.10))
    fx.loc["2020-01-31"] = 1.10 * 0.99                       # 1月の最後の取引日にユーロが1%下がる
    eq_f = _series(d, np.linspace(100, 110, len(d)))          # ユーロ圏の株が上がる
    eq_us = _series(d, np.full(len(d), 100.0))
    rows = R.month_trades("EURUSD=X", fx, eq_f, eq_us, "2020-01-01", "2020-03-31")
    jan = [r for r in rows if r["month"] == "2020-01"][0]
    assert jan["signal"] > 0                                   # 外国の株の上げが大きい＝外国の通貨を売る
    assert abs(jan["gross"] - 0.01) < 1e-9                     # ユーロ売りで +1%
    assert jan["net"] < jan["gross"]


def test_yen_is_sold_by_buying_usdjpy():
    d = pd.bdate_range("2019-12-01", "2020-02-28")
    fx = _series(d, np.full(len(d), 110.0))
    fx.loc["2020-01-31"] = 111.1                               # 円安（ドル円が上がる）
    eq_f = _series(d, np.linspace(100, 110, len(d)))
    eq_us = _series(d, np.full(len(d), 100.0))
    jan = [r for r in R.month_trades("USDJPY=X", fx, eq_f, eq_us, "2020-01-01", "2020-02-28") if r["month"] == "2020-01"][0]
    assert abs(jan["gross"] - 0.01) < 1e-9


def test_mid_month_rule_uses_first_day_on_or_after_15th():
    d = pd.bdate_range("2019-12-01", "2020-01-31")
    fx = _series(d, np.linspace(1.1, 1.2, len(d)))
    eq = _series(d, np.linspace(100, 101, len(d)))
    rows = R.month_trades("EURUSD=X", fx, eq * 1.01, eq, "2020-01-01", "2020-01-31", rule="mid")
    assert len(rows) == 1


def test_cluster_stats_and_judge():
    rng = np.random.default_rng(1)
    rows = [{"month": f"{2015 + i // 12}-{i % 12 + 1:02d}", "pair": "EURUSD=X", "signal": 0.01,
             "gross": 0.002, "net": 0.0018, "raw": -0.002} for i in range(120)]
    st = R.cluster_stats(rows, rng, n_boot=500)
    assert abs(st["mean"] - 0.0018) < 1e-12 and st["lo"] > 0 and st["p"] < 0.05 and R.judge(st) == R.VERDICTS[0]
    noisy = [dict(r, gross=g, net=g - 0.0002) for r, g in zip(rows, rng.normal(0, 0.005, 120))]
    assert R.judge(R.cluster_stats(noisy, rng, n_boot=500)) in R.VERDICTS


def test_load_flags_broken_fx():
    def fetcher(tk, interval, start=None):
        d = pd.bdate_range("2003-01-01", "2026-09-30")
        v = np.full(len(d), 1.1 if tk in R.PAIRS else 100.0)
        if tk == "GBPUSD=X":
            v[3000:] *= 1.2                                     # 戻らない20%の段差（直し方①②では直らない）
        return pd.DataFrame({"Close": v}, index=d)
    _, failed, _ = R.load(fetcher)
    assert any("GBPUSD=X" in f for f in failed)


def test_constants_match_preregistration():
    txt = open(os.path.join(ROOT, "PILLAR_PREREG.md"), encoding="utf-8").read()
    sec = txt.split("## R4 月末のロンドン16時の値決め前", 1)[1].split("\n## ", 1)[0]
    assert "2015-01〜2026-09" in sec and (R.START, R.END) == ("2015-01-01", "2026-09-30")
    assert "2004〜2014" in sec and R.PRE_START == "2004-01-01"
    for tk in ("EURUSD=X", "^STOXX50E", "GBPUSD=X", "^FTSE", "USDJPY=X", "^N225", "AUDUSD=X", "^AXJO", "^GSPC"):
        assert tk in sec
    assert "1日10%" in sec and R.FX_MAX == 0.10 and "25%" in sec and R.EQ_MAX == 0.25
    assert "p＜0.05" in sec and R.ALPHA == 0.05 and "10,000回" in sec and R.N_BOOT == 10000


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
