# -*- coding: utf-8 -*-
"""R7 株価指数の朝の窓・夜の上げ（index_open_lab.py）のテスト。作った値段で、窓の選び方・向き・費用・持ち越しの金利・
期間の切り方・判定・データの点検・出力を確かめる。2026-10-06 新設。

実行:  python tests/test_index_open_lab.py     （pytest 不要。pytest でも動く）
"""
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import index_open_lab as R  # noqa: E402


def _close(a, b, tol=1e-9):
    return abs(a - b) <= tol * max(1.0, abs(b))


def _df(days, opens, closes):
    return pd.DataFrame({"Open": opens, "Close": closes}, index=pd.DatetimeIndex(days))


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "## R7 株価指数の朝の窓は、その日のうちに埋まる向きに動くか" in text
    assert R.GAP == 0.005 and "**0.5％ 以上**" in text and (R.START, R.END) == ("2009-01-01", "2026-09-30") and "2009-01-01〜2026-09-30" in text
    assert R.QS["Q1"]["cost"] == 0.0003 and "往復 0.03％" in text and R.QS["Q2"]["cost"] == 0.0002 and "往復 0.02％" in text
    assert R.FIN_RATE == 0.03 and "年3％" in text and R.N_Q == 4 and "p＜0.05÷4" in text and R.N_BOOT == 10000
    assert R.MAX_DAILY == 0.25 and R.MAX_SAME_OPEN == 0.30 and "30％を超える" in text
    assert (R.CHECK_FROM, R.CHECK_TO) == ("2008-12-01", "2026-10-02") and "2008-12-01〜2026-10-02" in text
    assert R.JP_START == "2011-01-01" and "**1321.T（Q1・Q3）は 2011-01-01 から**" in text and R.MAX_ROW_GAP == 12 and "12日を超える" in text
    assert R.QS["Q1"]["ticker"] == "1321.T" and R.QS["Q2"]["ticker"] == "SPY" and "**1321.T**" in text and "**SPY**" in text


def test_gap_trades_pick_and_fade():
    days = ["2009-01-05", "2009-01-06", "2009-01-07", "2009-01-08", "2009-01-09"]
    closes = [100.0, 101.0, 100.0, 100.4, 99.0]
    opens = [99.8, 100.4, 101.6, 100.0, 100.4]      # 窓: +0.4%（入らない）/ +0.594%（売り）/ 0%（入らない）/ 0%
    t = R.gap_trades(_df(days, opens, closes), 0.0003)
    assert [x["day"] for x in t] == ["2009-01-07"]
    x = t[0]
    assert x["dir"] == -1.0 and _close(x["gross"], -(100.0 / 101.6 - 1)) and _close(x["net"], x["gross"] - 0.0003)
    days2 = ["2009-01-05", "2009-01-06"]
    t2 = R.gap_trades(_df(days2, [100.2, 99.5], [100.0, 100.0]), 0.0)                 # ちょうど −0.5% は入る（買い）
    assert len(t2) == 1 and t2[0]["dir"] == 1.0 and _close(t2[0]["gross"], 100.0 / 99.5 - 1)


def test_period_and_cut():
    d = pd.bdate_range("2008-12-01", "2026-10-09")
    rng = np.random.default_rng(1)
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, len(d))))
    o = c * np.exp(rng.normal(0, 0.01, len(d)))
    df = _df(d, o, c)
    g = R.gap_trades(df, 0.0)
    assert g[0]["day"] >= "2009-01-01" and g[-1]["day"] <= "2026-09-30"
    n = R.night_trades(df, 0.0, cut="2026-09-15")
    assert n[-1]["day"] < "2026-09-15"


def test_night_trades_cost_and_weekend_financing():
    days = ["2009-01-08", "2009-01-09", "2009-01-12"]    # 木・金・月
    t = R.night_trades(_df(days, [100.0, 101.0, 102.0], [100.5, 101.5, 103.0]), 0.0002)
    assert [x["days"] for x in t] == [1, 3] and t[1]["fri"] is True and t[0]["fri"] is False
    assert _close(t[0]["gross"], 101.0 / 100.5 - 1) and _close(t[0]["net"], t[0]["gross"] - 0.0002 - 0.03 / 365)
    assert _close(t[1]["net"], (102.0 / 101.5 - 1) - 0.0002 - 0.03 * 3 / 365)
    assert _close(t[1]["intra"], 103.0 / 102.0 - 1) and _close(t[1]["hold"], 103.0 / 101.5 - 1)


def test_data_check():
    d = pd.bdate_range("2009-01-01", periods=300)
    c = pd.Series(np.linspace(100, 130, 300), index=d)
    ok, _ = R.data_ok(pd.DataFrame({"Open": c * 1.001, "Close": c}))
    assert ok
    c2 = c.copy()
    c2.iloc[150] = c2.iloc[149] * 1.4
    ok, why = R.data_ok(pd.DataFrame({"Open": c2 * 1.001, "Close": c2}))
    assert not ok and "終値の変化" in why
    ok, why = R.data_ok(pd.DataFrame({"Open": c.shift(1).bfill(), "Close": c}))
    assert not ok and "始値が前日終値" in why


def test_check_range_ignores_moves_outside_the_counted_period():
    d = pd.bdate_range("2008-11-03", "2026-10-09")
    c = pd.Series(np.linspace(100, 200, len(d)), index=d)
    c[pd.Timestamp("2026-10-05")] = c[pd.Timestamp("2026-10-02")] * 1.99          # 数える期間の外の異常
    df = pd.DataFrame({"Open": c * 1.001, "Close": c})
    data, failed, _ = R.load(lambda tk, iv, start=None: df)
    assert failed == [] and set(data) == {"1321.T", "SPY"}
    c2 = c.copy()
    c2[pd.Timestamp("2015-06-01")] = c2[pd.Timestamp("2015-05-29")] * 1.5           # 数える期間の中の異常
    df2 = pd.DataFrame({"Open": c2 * 1.001, "Close": c2})
    _, failed, _ = R.load(lambda tk, iv, start=None: df2)
    assert len(failed) == 2
    mv = R.biggest_moves(df)
    assert [m[0] for m in mv] == ["2026-10-02", "2026-10-05", "2026-10-06"]


def test_stale_days_and_row_gaps_are_skipped():
    days = ["2011-01-04", "2011-01-05", "2011-01-06", "2011-01-07", "2011-01-31", "2011-02-01"]
    o = [100.0, 101.0, 102.0, 103.0, 104.0, 106.0]
    c = [100.0, 101.0, 102.0, 103.5, 105.0, 105.0]
    df = pd.DataFrame({"Open": o, "High": [x + 1 for x in o], "Low": [x - 1 for x in o], "Close": c}, index=pd.DatetimeIndex(days))
    df.loc[pd.Timestamp("2011-01-05"), ["Open", "High", "Low", "Close"]] = 101.0               # 値の付いていない日
    g = R.gap_trades(df, 0.0)
    assert [x["day"] for x in g] == ["2011-01-07", "2011-02-01"]      # 1/5・1/6 は値の付かない日がからむ／1/31 は 24日の穴
    n = R.night_trades(df, 0.0)
    assert [x["day"] for x in n] == ["2011-01-06", "2011-01-31"]    # 1/4→1/5・1/5→1/6 は値の付かない日／1/7→1/31 は穴


def test_japan_starts_in_2011():
    d = pd.bdate_range("2008-12-01", "2026-10-09")
    rng = np.random.default_rng(4)
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, len(d))))
    o = c * np.exp(rng.normal(0, 0.006, len(d)))
    data = {"1321.T": _df(d, o, c), "SPY": _df(d, o, c)}
    res = R.run(data, "2026-10-07", np.random.default_rng(1))
    assert res["Q1"]["first_day"] >= "2011-01-01" and res["Q3"]["first_day"] >= "2011-01-01"
    assert res["Q2"]["first_day"] < "2009-02-01" and res["Q4"]["first_day"] < "2009-02-01"


def _rows(n, mean, sd, seed, kind):
    rng = np.random.default_rng(seed)
    days = pd.bdate_range("2009-01-01", periods=n)
    out = []
    for d, x in zip(days, rng.normal(mean, sd, n)):
        r = {"day": str(d.date()), "month": str(d.date())[:7], "gross": float(x), "net": float(x - 0.0002)}
        if kind == "gap":
            r.update(gap=0.01, dir=1.0)
        else:
            r.update(intra=0.0, hold=float(x), fri=d.weekday() == 4, days=1)
        out.append(r)
    return out


def test_judge_clear_edge_and_noise():
    rng = np.random.default_rng(5)
    st = R.stats(_rows(1500, 0.004, 0.01, 1, "gap"), "gap", rng)
    assert st["verdict"] == R.VERDICTS[0] and st["lo"] > 0 and st["p"] < R.ALPHA
    st = R.stats(_rows(1500, 0.0, 0.01, 2, "gap"), "gap", rng)
    assert st["verdict"] == R.VERDICTS[2]
    st = R.stats(_rows(3000, 0.002, 0.01, 3, "night"), "night", rng)
    assert st["verdict"] == R.VERDICTS[0] and st["diff_night_minus_day"] > 0
    st = R.stats(_rows(3000, -0.001, 0.01, 4, "night"), "night", rng)
    assert st["verdict"] == R.VERDICTS[2]


def test_run_render_and_failed_path():
    d = pd.bdate_range("2008-12-01", "2026-10-09")
    rng = np.random.default_rng(2)
    c = 100 * np.exp(np.cumsum(rng.normal(0.0002, 0.01, len(d))))
    o = c * np.exp(rng.normal(0, 0.006, len(d)))
    data = {"1321.T": _df(d, o, c), "SPY": _df(d, o * 1.0, c * 1.0)}
    res = R.run(data, "2026-10-07", np.random.default_rng(3))
    assert set(res) == {"Q1", "Q2", "Q3", "Q4"} and all(r["stats"]["n"] > 100 for r in res.values())
    out = {"generated_jst": "x", "prereg_sha256": "0" * 64, "failed": [], "result": res}
    md = R.render_md(out)
    assert "## Q1 日本の朝の窓を埋める向き" in md and "時期ごと" in md and "投資助言ではありません" in md
    md2 = R.render_md(dict(out, failed=["SPY: 取れない"]))
    assert "何も数えていない" in md2 and "## Q1" not in md2


def test_workflow_sync_forbidden_and_verified_list():
    wf = open(".github/workflows/index-open-lab.yml", encoding="utf-8").read()
    assert "python index_open_lab.py --check" in wf.replace("-u ", "") and "python verified_list.py" in wf
    assert "index-open-lab.json index-open-lab.md verified-list.md" in wf and "options: [check, run]" in wf
    lint = open("check_site_consistency.py", encoding="utf-8").read()
    assert '"index-open-lab.json", "index-open-lab.md"' in lint
    vl = open("verified_list.py", encoding="utf-8").read()
    assert '"index-open-lab.json"' in vl


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
