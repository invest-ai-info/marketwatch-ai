# -*- coding: utf-8 -*-
"""J33 建玉の大きさ（size_short_lab.py）のテスト。2026-10-08 新設。

値動きはすべて作り物。確かめること＝①事前登録・点検表と定数の一致 ②日ごとのまとめ ③口座の動き（複利・合計100％に縮める・
1か月 −10％ でその月は建てない・−20％ で止まる）④収まる大きさの判定 ⑤点検は損益を出さない・出力に銘柄コードを出さない
⑥ワークフローと SYNC 禁忌。

実行:  python tests/test_size_short_lab.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))
os.chdir(ROOT)
import size_short_lab as Z  # noqa: E402
import test_stop_short_lab as TS  # noqa: E402


def test_prereg_and_rules_match_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    rules = open("MY_TRADING_RULES.md", encoding="utf-8").read()
    assert "## J33 建玉の大きさ：J31・J32 の売りを口座の何％ずつ建てれば" in text and "**目隠しではない**" in text
    assert Z.SIZES == (0.01, 0.02, 0.03, 0.05, 0.10) and "**1％・2％・3％・5％・10％**" in text
    assert (Z.ONE_TRADE, Z.DAY_LIMIT, Z.MONTH_LIMIT, Z.STOP_DD) == (0.01, -0.03, -0.10, -0.20)
    assert "口座の **1%**" in rules and "**−3%**" in rules and "**−10%**" in rules and "**−20%**" in rules
    assert [f for f, *_ in Z.FORMS] == ["B0", "B10", "C0", "C10"] and [s for s, _ in Z.SCOPES] == ["all", "top3"]


def _rows(spec):
    """spec＝[(日, 1回の損益)] → 行と損益の配列"""
    A = np.full((len(spec), len(Z.C)), np.nan)
    A[:, Z.C["day"]] = [d for d, _ in spec]
    return A, np.array([v for _, v in spec])


def test_by_day_groups_trades():
    A, v = _rows([(3, 0.01), (1, 0.02), (3, -0.01), (2, np.nan)])
    days, nets = Z.by_day(A, v, np.ones(len(A), bool))
    assert days == [1, 3] and [list(x) for x in nets] == [[0.02], [0.01, -0.01]]


def test_simulate_compounding_cap_month_pause_and_stop():
    d0 = dt.date(2026, 1, 5).toordinal()
    q = Z.simulate([d0, d0 + 1], [np.array([0.02]), np.array([0.01] * 20)], 0.10)
    assert abs(q["final"] - (1 + 0.10 * 0.02) * (1 + 1.0 / 20 * 0.2)) < 1e-12           # 2日目は20銘柄＝1銘柄5％に縮める
    days = [d0 + i for i in range(6)]
    m = Z.simulate(days, [np.array([-0.6])] * 6, 0.10)                                     # 毎日 −6％ ＝2日目で月 −11.6％ → 止める
    assert m["days"] == 2 and m["paused_months"] == 1 and m["stopped_on"] is None
    days = [dt.date(2026, mo, 5).toordinal() for mo in range(1, 7)]
    s = Z.simulate(days, [np.array([-0.9])] * 6, 0.10)                                     # 月をまたいで −9％ ずつ → 3回目で −20％ を超える
    assert s["stopped_on"] == "2026-03-05" and s["days"] == 3 and s["max_dd"] <= -0.20
    assert abs(s["worst_day"] + 0.09) < 1e-12 and s["day3"] == 1.0


def test_fits():
    ok = {"stopped_on": None}
    assert Z.fits(-0.25, ok, 0.04) and not Z.fits(-0.25, ok, 0.05) and Z.fits(-0.102, ok, 0.05)
    assert not Z.fits(-0.01, {"stopped_on": "2026-01-01"}, 0.01) and not Z.fits(None, ok, 0.01)


def test_analyze_and_render():
    res = Z.analyze(TS._synthetic(0.01, 0.01, seed=6))
    assert set(res["forms"]) == {f"{f}-{s}" for f, *_ in Z.FORMS for s, _ in Z.SCOPES}
    x = res["forms"]["C0-top3"]
    assert x["eras"]["e1"]["trades"] == 20 * 3 and set(x["eras"]["e2"]["sizes"]) == {f"{s:.2f}" for s in Z.SIZES}
    assert x["fit"] in (None,) + Z.SIZES
    md = Z.render_md({"generated_at": "x", "prereg_sha256": "0" * 64, "result": dict(res, n_codes=520)})
    assert "## まとめ" in md and "収まる大きさ" in md and "投資助言ではありません" in md and "−20％で止まった日" in md
    assert "計算できず" in Z.render_md({"generated_at": "x", "result": {"error": "e"}})
    out = Z.check_summary(TS._synthetic(0.01, 0.01, seed=7), {"daily": [], "h1": [], "m5": []}, 520, None)
    assert not any(w in repr(out) for w in ("mean", "final", "cagr", "worst")) and out["eras"]["e3"]["K3"]["days"] == 20


def test_workflow_and_sync_forbidden():
    wf = open(".github/workflows/size-short-lab.yml", encoding="utf-8").read()
    assert "python -u size_short_lab.py --check" in wf and "restore-keys: jp-bars-" in wf
    assert "python tests/test_size_short_lab.py" in wf and "size-short-lab.json size-short-lab.md" in wf and "options: [check, run]" in wf
    assert '"size-short-lab.json", "size-short-lab.md"' in open("check_site_consistency.py", encoding="utf-8").read()


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
