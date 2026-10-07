# -*- coding: utf-8 -*-
"""J14 J13 の「窓の戻し」は昔の期間でも出ていたか（gap_history_lab.py）のテスト。2026-10-07 新設。

値動きはすべて作り物（ネットワークに出ない）。確かめること＝①事前登録と定数の一致 ②朝の値（窓・寄り→大引け・出来高0と
±25％超と穴を数えない）③判定の向き（J13 と同じ向き／逆向き／見えない）④出力に銘柄コードを出さない ⑤ワークフローと SYNC 禁忌。

実行:  python tests/test_gap_history_lab.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import gap_history_lab as G  # noqa: E402
import test_highs_trap_lab as TL  # noqa: E402


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "## J14 J13 の「窓の戻し」は、J13 が使っていない昔の期間" in text
    assert (G.FIRST_DAY, G.LAST_DAY) == ("2016-11-01", "2023-09-29") and "**2016-11-01〜2023-09-29**" in text
    assert G.N_Q == 4 and abs(G.ALPHA - 0.0125) < 1e-12 and "p＜0.05÷4＝98.75％ の幅" in text
    assert G.MAX_MOVE == 0.25 and "±25％ を超えたら数えない" in text and "出来高が0の日は数えない" in text
    assert G.DAILY_RANGE == "10y" and G.REF_FIRST == "2023-10-10"


def test_stock_rows_rules():
    days = TL._bdays("2019-03-01", 6)
    daily = [(d, 100.0, 101.0, 99.0, 100.0, 1e5) for d in days]
    daily[1] = (days[1], 102.0, 104.0, 101.0, 103.0, 1e5)       # 窓 +2％・寄り→大引け +0.98％
    daily[2] = (days[2], 103.0, 103.0, 103.0, 103.0, 0.0)       # 出来高0＝数えない
    daily[3] = (days[3], 100.0, 140.0, 99.0, 130.0, 1e5)        # 寄り→大引け +30％＝数えない
    late = (dt.date.fromisoformat(days[5]) + dt.timedelta(days=12)).isoformat()
    daily.append((late, 100.0, 101.0, 99.0, 100.0, 1e5))       # 12日の穴＝数えない
    drops = {"n": 0}
    A = G.stock_rows(3, daily, first="2019-01-01", last="2019-12-31", drops=drops)
    got = {dt.date.fromordinal(int(r[G.C["day"]])).isoformat(): r for r in A}
    assert set(got) == {days[1], days[4], days[5]} and drops["n"] == 1
    r = got[days[1]]
    assert abs(r[G.C["gap"]] - 0.02) < 1e-12 and abs(r[G.C["rclose"]] - (103 / 102 - 1)) < 1e-12 and r[G.C["code"]] == 3
    assert len(G.stock_rows(3, daily, first="2019-03-07", last="2019-03-08")) == 2 and len(G.stock_rows(3, daily, first="2019-03-05", last="2019-03-06")) == 0


def _synthetic(n_days=300, n_codes=60, up=-0.003, dn=0.003, seed=4, start="2017-01-04"):
    rng = np.random.default_rng(seed)
    d0 = dt.date.fromisoformat(start).toordinal()
    rows = []
    for d in range(n_days):
        mkt = rng.normal(0, 0.005)
        for c in range(n_codes):
            gap = rng.normal(0, 0.015)
            r = mkt + rng.normal(0, 0.012) + (up if gap >= 0.01 else 0) + (dn if gap <= -0.01 else 0)
            rows.append((d0 + d, c, gap, r, rng.choice([0.5, 5.0, 50.0])))
    return np.array(rows, float)


def test_judge_directions():
    q = G.pair_stats(_synthetic(), "up1")
    assert q["hi"] < 0 and G.judge(q, -1) == G.SAME and G.judge(q, +1) == G.OPPOSITE
    q3 = G.pair_stats(_synthetic(), "dn1")
    assert G.judge(q3, +1) == G.SAME
    qn = G.pair_stats(_synthetic(up=0.0, dn=0.0, seed=5), "up1")
    assert G.judge(qn, -1) in (G.NONE, G.SAME, G.OPPOSITE) and (qn["lo"] < 0 < qn["hi"]) == (G.judge(qn, -1) == G.NONE)


def test_analyze_render_no_codes():
    A = np.vstack([_synthetic(n_days=120), _synthetic(n_days=60, start="2023-10-10", seed=9)])
    res = {"generated_at": "x", "prereg_sha256": "0" * 64, "price_store": {"built_at": "b"},
           "result": dict(G.analyze(A), n_codes=60, list_date="2026-09-30", n_missing=0, n_dropped=0)}
    r = res["result"]
    assert all(r["pairs"][k]["verdict"] for k in ("g1", "g2", "g3", "g4")) and r["ref_j13_period"]["g1"]["diff"] is not None
    md = G.render_md(res)
    assert "G1 窓 +1％ 以上" in md and "年ごとの差" in md and "生き残りの偏り" in md and "投資助言ではありません" in md
    assert "計算できず" in G.render_md({"generated_at": "x", "prereg_sha256": "", "result": {"error": "e"}})
    dg = G.diag_summary(A, [], 60)
    assert dg["n_rows_main"] == 120 * 60 and dg["n_rows_ref"] == 60 * 60


def test_workflow_and_sync_forbidden():
    wf = open(".github/workflows/gap-history-lab.yml", encoding="utf-8").read()
    assert "python gap_history_lab.py --diag" in wf and "restore-keys: jp-bars-" in wf
    assert "gap-history-lab.json gap-history-lab.md" in wf
    lint = open("check_site_consistency.py", encoding="utf-8").read()
    assert '"gap-history-lab.json", "gap-history-lab.md"' in lint


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
