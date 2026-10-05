# -*- coding: utf-8 -*-
"""R6 ほかの国の株価指数の月末月初（intl_tom_lab.py）のテスト。作った値段で、窓・期間の切り方・まとめ方・判定・データの点検を確かめる。
2026-10-05 新設。

実行:  python tests/test_intl_tom_lab.py     （pytest 不要。pytest でも動く）
"""
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import intl_tom_lab as I  # noqa: E402


def _close(a, b, tol=1e-9):
    return abs(a - b) <= tol * max(1.0, abs(b))


def _bump(d, daily=0.0002, bump=0.003, noise=None):
    """ふつうの日は毎日 daily、窓（月の最後の日＋最初の3日）の日は daily+bump だけ上がる値段"""
    ym = np.asarray(d.year) * 12 + np.asarray(d.month)
    first = np.r_[0, np.flatnonzero(np.diff(ym) != 0) + 1]
    inwin = np.zeros(len(d), bool)
    for k in range(1, len(first)):
        inwin[max(first[k] - 1, 0):first[k] + 3] = True
    lr = np.where(inwin, daily + bump, daily) + (noise if noise is not None else 0)
    lr[0] = 0
    return pd.Series(100 * np.exp(np.cumsum(lr)), index=d)


def test_rows_use_the_same_window_and_period():
    d = pd.bdate_range("2008-10-01", "2026-10-09")
    rows = I.market_rows(_bump(d), "^GDAXI", "2026-10-07")
    assert rows[0]["month"] == "2009-01" and rows[-1]["month"] == I.LAST_MONTH        # 窓の月 2009-01〜2026-09
    r = [x for x in rows if x["month"] == "2020-01"][0]
    assert (r["buy"], r["sell"]) == ("2020-01-30", "2020-02-05")                       # R3 の Q1 と同じ窓
    assert all(_close(x["diff"], 4 * 0.003) for x in rows)
    assert _close(r["net"], r["gross"] - I.COST - I.CL.FIN_RATE * r["days"] / 365)


def test_cut_drops_today_and_later():
    d = pd.bdate_range("2026-06-01", "2026-10-09")
    px = _bump(d)
    rows = I.market_rows(px, "^FTSE", "2026-10-05")                                   # 10/5 の途中の値は使わない
    assert "2026-09" not in {r["month"] for r in rows}                                 # 9月の窓の売り（10/5）がまだ無い
    rows2 = I.market_rows(px, "^FTSE", "2026-10-06")
    assert [r["sell"] for r in rows2 if r["month"] == "2026-09"] == ["2026-10-05"]


def test_pooled_judgement():
    rng = np.random.default_rng(0)
    d = pd.bdate_range("2008-10-01", "2026-10-09")
    rows = []
    for k, m in enumerate(I.MARKETS):
        rows += I.market_rows(_bump(d, noise=rng.normal(0, 0.004, len(d))), m, "2026-10-07")
    st = I.pooled(rows, np.random.default_rng(1))
    assert st["verdict"] == I.VERDICTS[0] and st["lo"] > 0 and st["p"] < I.ALPHA, st
    flat = []
    for m in I.MARKETS:
        flat += I.market_rows(_bump(d, bump=0.0, noise=rng.normal(0, 0.01, len(d))), m, "2026-10-07")
    assert I.pooled(flat, np.random.default_rng(2))["verdict"] != I.VERDICTS[0]
    neg = []
    for m in I.MARKETS:
        neg += I.market_rows(_bump(d, bump=-0.003), m, "2026-10-07")
    assert I.pooled(neg, np.random.default_rng(3))["verdict"] == I.VERDICTS[2]


def test_judge_rules():
    base = {"mean": 0.001, "lo": 0.0002, "first": 0.001, "second": 0.001, "p": 0.01}
    assert I.judge(base) == I.VERDICTS[0]
    assert I.judge({**base, "lo": -0.0001}) == I.VERDICTS[1]
    assert I.judge({**base, "p": 0.06}) == I.VERDICTS[2]
    assert I.judge({**base, "second": -0.001}) == I.VERDICTS[2]
    assert I.judge({**base, "mean": -0.001, "lo": -0.002}) == I.VERDICTS[2]


def test_data_check_and_unit_fix():
    d = pd.bdate_range("2007-01-01", "2026-10-02")
    good = _bump(d)
    shifted = good.copy()
    shifted.iloc[100:105] = shifted.iloc[100:105] * 10                                 # 単位のずれ（数日だけ10倍）＝直せる
    jump = good.copy()
    jump.iloc[3000:] = jump.iloc[3000:] * 1.4                                          # 1日で40%＝データの失敗

    def fetcher(tk, interval, start=None):
        s = {"^GDAXI": shifted, "^FTSE": jump}.get(tk, good)
        return pd.DataFrame({"Close": s})
    series, failed, fixes = I.load(fetcher)
    assert "^GDAXI" in fixes and not any(f.startswith("^GDAXI") for f in failed)
    assert any(f.startswith("^FTSE") for f in failed) and len(failed) == 1


def test_constants_match_preregistration():
    txt = open(os.path.join(ROOT, "PILLAR_PREREG.md"), encoding="utf-8").read()
    sec = txt.split("## R6 月末月初の窓は", 1)[1].split("\n## ", 1)[0]
    for tk in I.MARKETS:
        assert f"`{tk}`" in sec, tk
    assert len(I.MARKETS) == 7 and "7つ" in sec
    assert "2009-01〜2026-09" in sec and (I.START, I.LAST_MONTH) == ("2009-01-01", "2026-09")
    assert "往復 0.05%" in sec and I.COST == 0.0005 and "年3%" in sec and I.CL.FIN_RATE == 0.03
    assert "10,000回" in sec and I.N_BOOT == 10000
    assert "p＜0.05" in sec and I.ALPHA == 0.05
    assert "25%を超える" in sec and I.CL.MAX_DAILY == 0.25
    assert (I.PRE, I.POST) == (1, 3) and "月の最後から2日目の終値で買い、翌月の3日目の終値で売る" in sec


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
