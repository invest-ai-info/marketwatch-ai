# -*- coding: utf-8 -*-
"""J24 J19・J23 の費用の数え直し（cost_recount_lab.py）のテスト。2026-10-07 新設。

値動きはすべて作り物。確かめること＝①事前登録と定数の一致 ②新しい見積もり（窓で平均してから平方根・その朝より前の値だけ・
出来高0の日・20組未満）と、元の見積もり（0で切ってから平均）より上に偏らないこと ③費用の列だけを入れ替えること
④元の判定を並べるだけ・出力に銘柄コードを出さない ⑤ワークフローと SYNC 禁忌。

実行:  python tests/test_cost_recount_lab.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import bounce_cost_lab as BC  # noqa: E402
import cost_recount_lab as CR  # noqa: E402
import dip_lab as D  # noqa: E402
import test_highs_trap_lab as TL  # noqa: E402


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "## J24 J19・J23 の費用の数え直し（偏りの小さい見積もり）" in text
    assert "**まず平均し**、0より小さければ0にしてから平方根" in text and "目隠しではない" in text
    assert (CR.WINDOW, CR.MIN_OBS) == (60, 20) and BC.COST_FLOOR == 0.001
    assert "元の判定（J19＝選べる形なし／J23＝−2〜−8％ は ✕）は書き換えない" in text


def _daily(n=120, seed=1, vol=0.03, zero_at=()):
    rng = np.random.default_rng(seed)
    days = TL._bdays("2025-01-06", n)
    out, c = [], 100.0
    for i, d in enumerate(days):
        o = c * (1 + rng.normal(0, vol / 3))
        c2 = o * (1 + rng.normal(0, vol))
        h, lo = max(o, c2) * (1 + abs(rng.normal(0, vol / 2))), min(o, c2) * (1 - abs(rng.normal(0, vol / 2)))
        out.append((d, o, h, lo, c2, 0.0 if i in zero_at else 1e5))
        c = c2
    return out


def test_ar_spread_avg_values_and_bias():
    daily = _daily()
    new, old = CR.ar_spread_avg(daily), BC.ar_spread(daily)
    assert set(new) == set(old) and daily[2][0] not in new
    j = 100
    c = np.log([r[4] for r in daily])
    eta = (np.log([r[2] for r in daily]) + np.log([r[3] for r in daily])) / 2
    x = 4 * (c[:-1] - eta[:-1]) * (c[:-1] - eta[1:])
    want = np.sqrt(max(x[j - 1 - 60:j - 1].mean(), 0))                       # その朝より前の60組だけ
    assert abs(new[daily[j][0]] - want) < 1e-12
    assert all(new[d] <= old[d] + 1e-12 for d in new)                          # 平方根は凹＝平均してから取る方が小さい
    z = CR.ar_spread_avg(_daily(zero_at=set(range(30, 120))))                  # 出来高0の日は使わない → 20組未満の朝は見積もらない
    assert daily[80][0] not in z and daily[25][0] in z


def test_rows_replace_only_the_cost_column():
    daily = _daily(n=140, seed=2)
    sp = CR.ar_spread_avg(daily)
    A19 = CR.rows_j19(1, daily, {}, {}, sp)
    assert A19.shape[1] == len(BC.COLS)
    got = {dt.date.fromordinal(int(r[BC.C["day"]])).isoformat(): r[BC.C["spread"]] for r in A19}
    assert all((np.isnan(v) and d not in sp) or abs(v - sp[d]) < 1e-15 for d, v in got.items())
    A23, old = CR.rows_j23(1, daily, {}, {}, sp)
    ref = D.stock_rows(1, daily, {}, {})
    assert A23.shape == ref.shape and np.allclose(old, ref[:, D.C["spread"]], equal_nan=True)
    others = [i for i in range(len(D.COLS)) if i != D.C["spread"]]
    assert np.allclose(A23[:, others], ref[:, others], equal_nan=True)


def test_render_keeps_originals_and_has_no_codes():
    res = {"generated_at": "x", "prereg_sha256": "0" * 64, "result": {
        "n_codes": 3, "n_missing": {}, "originals": {"j19": {"chosen": None, "overall": "選べる形なし"}, "j23": {"summary": {"0.02": "✕ 元"}}},
        "j19": {"chosen": None, "overall": "選べる形なし", "confirm": {}},
        "j23": {"summary": {f"{x:.2f}": "見えない" for x in D.LEVELS},
                "judge": {f"{x:.2f}": {"main": {"value": 0.001}, "conf": {"value": None}} for x in D.LEVELS}},
        "costs": {k: {"all": {"old": 0.012, "new": 0.004, "n": 10}, "dip": {"old": 0.013, "new": 0.005, "n": 3},
                      "turnover": {"10億円以上": {"old": 0.01, "new": 0.002}}} for k in ("main", "conf", "long")},
        "j19_res": {"generated_at": "x", "result": {"error": "e"}}, "j23_res": {"generated_at": "x", "result": {"error": "e"}}}}
    md = CR.render_md(res)
    assert "元＝選べる形なし" in md and "✕ 元" in md and "数え直し" in md and "目隠しではない" in md and "投資助言ではありません" in md
    assert md.count("※ 研究の記録です") == 1 and "付録1" in md
    assert "計算できず" in CR.render_md({"generated_at": "x", "result": {"error": "e"}})


def test_workflow_and_sync_forbidden():
    wf = open(".github/workflows/cost-recount-lab.yml", encoding="utf-8").read()
    assert "python -u cost_recount_lab.py --check" in wf and "restore-keys: jp-bars-" in wf and "python tests/test_cost_recount_lab.py" in wf
    assert "cost-recount-lab.json cost-recount-lab.md" in wf and "options: [check, run]" in wf
    assert '"cost-recount-lab.json", "cost-recount-lab.md"' in open("check_site_consistency.py", encoding="utf-8").read()


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
