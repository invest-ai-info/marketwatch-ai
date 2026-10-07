# -*- coding: utf-8 -*-
"""J25 相場全体が安く寄った朝の深い下げは戻るか（market_dip_lab.py）のテスト。2026-10-07 新設。

値動きはすべて作り物。確かめること＝①事前登録と定数の一致 ②相場全体の窓（その朝の中央値・500銘柄未満の朝は使わない）
③判定（Q1 安く寄った朝の費用後・Q2 安く寄った朝 − それ以外・まとめ）④読むための表・点検は損益を出さない ⑤ワークフローと SYNC 禁忌。

実行:  python tests/test_market_dip_lab.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import dip_lab as D  # noqa: E402
import market_dip_lab as M  # noqa: E402


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "## J25 相場全体が安く寄った朝の深い下げは戻るか" in text
    assert M.MKT_DOWN == -0.005 and "中央値が −0.5％ 以下" in text
    assert M.LEVELS == (0.05, 0.08, 0.10) and "前日比 **−5％・−8％・−10％**" in text
    assert M.N_Q == 6 and abs(M.ALPHA - 0.05 / 6) < 1e-12 and "p＜0.05÷6＝99.17％ の幅" in text
    assert M.E1 == ("2006-01-04", "2016-10-31") and "2006-01-04〜2016-10-31 の日足" in text
    assert M.MIN_DOWN_DAYS == 20 and "安く寄った朝が20朝以上" in text


def _rows(n_days, start, seed, kind, effect=True, n=520, down_share=0.35):
    rng = np.random.default_rng(seed)
    d0 = dt.date.fromisoformat(start)
    days = [d for d in (d0 + dt.timedelta(i) for i in range(n_days * 2)) if d.weekday() < 5][:n_days]
    lo_col, ex_col = {"e1": ("loday_r", "close_r"), "e2": ("loday_r", "close_r"), "conf": ("lo1000_r", "p1000_r"),
                      "main": ("lo930_r", "p930_r")}[kind]
    out = []
    for d in days:
        down = rng.uniform() < down_share
        mg = -0.012 if down else 0.003
        gap = mg + rng.normal(0, 0.004, n)
        op = 1 + gap
        lo = np.minimum(op, 1 - 0.2 * rng.uniform(0, 1, n) ** 2)
        rebound = effect and down
        ex = np.where((lo <= 0.94) & rebound, 0.99, lo + 0.001) + rng.normal(0, 0.003, n)
        for c in range(n):
            row = np.full(len(D.COLS), np.nan)
            row[D.C["day"]], row[D.C["code"]], row[D.C["gap"]] = d.toordinal(), c, gap[c]
            row[D.C["turnover"]], row[D.C["spread"]], row[D.C["op_r"]] = 5.0, 0.002, op[c]
            row[D.C[lo_col]], row[D.C[ex_col]] = lo[c], ex[c]
            out.append(row)
    return np.array(out)


def _all(effect=True):
    return np.vstack([_rows(80, "2008-03-03", 1, "e1", effect), _rows(15, "2018-03-01", 2, "e2", effect),
                      _rows(15, "2024-11-01", 3, "conf", effect), _rows(12, "2026-08-10", 4, "main", effect)])


def test_market_gap():
    A = np.zeros((7, len(D.COLS)))
    A[:, D.C["day"]] = [1, 1, 1, 2, 2, 2, 2]
    A[:, D.C["gap"]] = [-0.01, 0.0, -0.02, 0.01, 0.02, 0.03, 0.04]
    keep, mg = M.market_gap(A)
    assert not keep.any() and list(mg) == [-0.01] * 3 + [0.025] * 4                     # 500銘柄未満の朝は使わない
    B = _rows(2, "2008-03-03", 9, "e1", n=520)
    keep, mg = M.market_gap(B)
    assert keep.all() and len(np.unique(mg)) == 2


def test_judges_and_reading():
    A = _all()
    old = np.full(len(A), 0.012)
    res = M.analyze(A, old)
    assert res["summary"]["0.08"] == M.OK and res["summary"]["0.10"] == M.OK, (res["summary"], res["judge"]["0.08"])
    e1 = res["eras"]["e1"]
    assert e1["days"] == 80 and 15 <= e1["down_days"] <= 45 and res["eras"]["main"]["days"] == 12
    rd = res["reading"]["e1"]["0.08"]
    assert rd["down"]["net"]["mean"] > 0 > rd["other"]["net"]["mean"] and abs(rd["down"]["net"]["mean"] - rd["down"]["net_old"]["mean"] - 0.01) < 1e-9
    assert rd["down"]["gross"]["mean"] - rd["down"]["net"]["mean"] > 0.0019
    none = M.analyze(_all(effect=False), old)
    assert all(v == M.NONE for v in none["summary"].values()), none["summary"]
    out = {"generated_at": "x", "prereg_sha256": "0" * 64, "result": dict(res, n_codes=520, list_date="2026-09-30", n_missing={}, n_dropped=0)}
    md = M.render_md(out)
    assert "## まとめ" in md and M.OK in md and "J19 の費用" in md and "投資助言ではありません" in md
    assert "計算できず" in M.render_md({"generated_at": "x", "result": {"error": "e"}})


def test_check_summary_has_no_returns():
    out = M.check_summary(_all(), {"daily": [], "h1": [], "m5": []}, 520, {"daily_range": "from:1990"})
    text = repr(out)
    assert not any(w in text for w in ("mean", "'win'", "value", "net", "gross")) and out["eras"]["e1"]["days"] == 80
    assert set(out["eras"]["main"]["fills_down_other"]) == {f"{x:.2f}" for x in M.LEVELS}


def test_workflow_and_sync_forbidden():
    wf = open(".github/workflows/market-dip-lab.yml", encoding="utf-8").read()
    assert "python -u market_dip_lab.py --check" in wf and "restore-keys: jp-bars-" in wf and "python tests/test_market_dip_lab.py" in wf
    assert "market-dip-lab.json market-dip-lab.md" in wf and "options: [check, run]" in wf
    assert '"market-dip-lab.json", "market-dip-lab.md"' in open("check_site_consistency.py", encoding="utf-8").read()


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
