# -*- coding: utf-8 -*-
"""J16 前の日に大きく動いた株が今朝ふつうに寄ったとき（prevday_lab.py）のテスト。2026-10-07 新設。

値動きはすべて作り物。確かめること＝①事前登録と定数の一致 ②朝の値（前の日の値動き・今朝の窓・穴と出来高0と±25％超）
③組（今朝の窓 ±1％ 未満だけ）④判定とまとめ（両方の期間で同じ向き／片方だけ／見えない）⑤出力に銘柄コードを出さない ⑥ワークフロー。

実行:  python tests/test_prevday_lab.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import prevday_lab as M  # noqa: E402
import test_highs_trap_lab as TL  # noqa: E402


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "## J16 前の日に大きく動いた株が今朝ふつうに寄ったとき" in text
    assert M.OLD == ("2016-11-01", "2023-09-29") and M.NEW[0] == "2023-10-10" and "2023-10-10〜2026-10-05" in text
    assert (M.GAP_FLAT, M.PREV_BIG, M.PREV_FLAT) == (0.01, 0.05, 0.02) and "+5％ 以上" in text and "−2％ より大きく +2％ より小さい" in text
    assert M.N_Q == 4 and abs(M.ALPHA - 0.0125) < 1e-12 and "p＜0.05÷4＝98.75％ の幅" in text


def test_stock_rows_prev_move_and_rules():
    days = TL._bdays("2019-03-01", 7)
    daily = [(d, 100.0, 101.0, 99.0, 100.0, 1e5) for d in days]
    daily[1] = (days[1], 100.0, 107.0, 99.0, 106.0, 1e5)      # 前の日 +6％
    daily[2] = (days[2], 106.3, 108.0, 105.0, 107.0, 1e5)     # 今朝の窓 +0.28％・寄り→大引け +0.66％
    daily[4] = (days[4], 100.0, 100.0, 100.0, 100.0, 0.0)     # 出来高0
    A = M.stock_rows(5, daily, {}, {}, first="2019-01-01", last="2019-12-31", recent_from="2030-01-01")
    got = {dt.date.fromordinal(int(r[M.C["day"]])).isoformat(): r for r in A}
    r = got[days[2]]
    assert abs(r[M.C["rprev"]] - 0.06) < 1e-12 and abs(r[M.C["gap"]] - (106.3 / 106 - 1)) < 1e-12
    assert abs(r[M.C["rclose"]] - (107 / 106.3 - 1)) < 1e-12 and np.isnan(r[M.C["r1000"]]) and r[M.C["code"]] == 5
    assert days[4] not in got and days[0] not in got                 # 出来高0・その前の日が無い朝は数えない


def _rows(n_days=300, n_codes=80, up_eff=-0.004, dn_eff=0.0, start="2017-01-04", seed=1, with_new=True):
    rng = np.random.default_rng(seed)
    d0 = dt.date.fromisoformat(start).toordinal()
    out = []
    for d in range(n_days):
        mkt = rng.normal(0, 0.004)
        for c in range(n_codes):
            gap = rng.normal(0, 0.01)
            rp = rng.choice([0.07, -0.07, 0.0, 0.01, -0.01, 0.03])
            r = mkt + rng.normal(0, 0.01) + (up_eff if rp >= 0.05 else 0) + (dn_eff if rp <= -0.05 else 0)
            out.append((d0 + d, c, gap, rp, r, r if with_new else np.nan, r * 0.8 if with_new else np.nan, 3.0))
    return np.array(out, float)


def test_groups_only_flat_mornings():
    A = np.array([[0, 0, 0.002, 0.06, 0, 0, 0, 1], [0, 1, 0.02, 0.06, 0, 0, 0, 1], [0, 2, 0.0, 0.0, 0, 0, 0, 1], [0, 3, 0.0, 0.03, 0, 0, 0, 1]], float)
    assert list(M.groups(A, "up")) == [0, -1, 1, -1] and list(M.groups(A, "dn")) == [-1, -1, 1, -1]


def test_judge_and_summary():
    old = _rows(start="2017-01-04")
    new = _rows(start="2024-01-04", seed=2)
    res = M.analyze(np.vstack([old, new]))
    assert res["judges"]["m1"]["verdict"] == M.DOWN and res["judges"]["m3"]["verdict"].startswith(M.DOWN)
    assert res["summary"]["up"].startswith(M.BOTH) and res["summary"]["dn"] == M.NONE
    assert M.summary(M.DOWN, M.NONE) == M.ONE and M.summary(M.UP, M.UP + "（10:00 では兆し・9:30 は件数不足で確かめられず）").startswith(M.BOTH)


def test_render_no_codes_and_error():
    A = np.vstack([_rows(n_days=80, start="2018-01-04"), _rows(n_days=60, start="2025-01-06", seed=3)])
    res = {"generated_at": "x", "prereg_sha256": "0" * 64, "price_store": {"built_at": "b"},
           "result": dict(M.analyze(A), n_codes=80, list_date="2026-09-30", n_missing={}, n_dropped=0)}
    md = M.render_md(res)
    assert "## まとめ" in md and "M1 前日大きく上げた" in md and "投資助言ではありません" in md
    assert "計算できず" in M.render_md({"generated_at": "x", "prereg_sha256": "", "result": {"error": "e"}})
    dg = M.diag_summary(A, {"daily": [], "h1": [], "m5": []}, 80)
    assert dg["rows"] == len(A) and "sizes_930" in dg["m3"]


def test_workflow_and_sync_forbidden():
    wf = open(".github/workflows/prevday-lab.yml", encoding="utf-8").read()
    assert "python prevday_lab.py --diag" in wf and "restore-keys: jp-bars-" in wf and "prevday-lab.json prevday-lab.md" in wf
    assert '"prevday-lab.json", "prevday-lab.md"' in open("check_site_consistency.py", encoding="utf-8").read()


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
