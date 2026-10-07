# -*- coding: utf-8 -*-
"""J29 安く寄った株の戻りを、費用に幅を持たせて数え直す（bounce_range_lab.py）のテスト。2026-10-07 夜 新設。

値動きはすべて作り物。確かめること＝①事前登録と定数の一致 ②2つの費用（重いほう＝J24・軽いほう＝J24×J28 の比・下限0.1％・
見積もれない朝は数えない）③組（その銘柄だけの窓・生の窓）④まとめの言葉（重いほうでも3つの時代とも上／軽いほうだけ／それ以外）
⑤点検は損益を出さない・出力に銘柄コードを出さない ⑥ワークフローと SYNC 禁忌。

実行:  python tests/test_bounce_range_lab.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import bounce_cost_lab as BC  # noqa: E402
import bounce_range_lab as B  # noqa: E402


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "## J29 安く寄った株の戻りを、費用に幅を持たせて数え直す" in text and "**目隠しではない**" in text
    assert (B.LOW_FACTOR_SMALL, B.LOW_FACTOR_REST, B.FLOOR) == (0.29, 0.32, 0.001) and "1億円未満＝0.29・1億円以上＝0.32" in text
    assert B.N_Q == 3 and abs(B.ALPHA - 0.05 / 3) < 1e-12 and "98.33％の幅（p＜0.05÷3" in text
    assert [e[2] for e in B.ERAS] == [("2006-01-04", "2016-10-31"), ("2016-11-01", "2023-09-29"), ("2023-10-10", "2026-10-05")]
    assert [e[3] for e in B.ERAS] == ["rclose", "rclose", "r1000"] and [g[0] for g in B.GROUPS] == ["D1", "D2", "D3"]


def _row(day, code, gap, ret, spread, turnover=5.0, col="rclose"):
    r = np.full(len(BC.COLS), np.nan)
    r[[B.C["day"], B.C["code"], B.C["gap"], B.C["rprev"], B.C["turnover"], B.C["spread"]]] = [day, code, gap, 0.0, turnover, spread]
    r[B.C[col]] = ret
    return r


def test_costs():
    A = np.array([_row(1, 0, 0, 0, 0.006, turnover=0.5), _row(1, 1, 0, 0, 0.006, turnover=5.0),
                  _row(1, 2, 0, 0, 0.0002), _row(1, 3, 0, 0, np.nan)])
    high, low = B.costs(A)
    assert np.allclose(high[:3], [0.006, 0.006, 0.001]) and np.isnan(high[3])
    assert np.allclose(low[:3], [0.006 * 0.29, 0.006 * 0.32, 0.001]) and np.isnan(low[3])


def test_groups():
    A = np.array([_row(1, i, g, 0, 0.004) for i, g in enumerate([-0.04, -0.02, -0.005, 0.0])])
    idio = np.array([-0.035, -0.015, 0.005, 0.01])
    g = B.groups(A, idio)
    assert list(g["D1"]) == [True, True, False, False] and list(g["D2"]) == [True, True, False, False]
    assert list(g["D3"]) == [True, False, False, False]


def _synthetic(drift, spread=0.006, n=520, days_per_era=20, seed=1):
    """3つの時代＋5分足の朝。安く寄った株（窓 −4％）は drift だけ戻る"""
    rng = np.random.default_rng(seed)
    rows = []
    for start, col in (("2008-03-03", "rclose"), ("2018-03-01", "rclose"), ("2025-03-03", "r1000"), ("2026-08-17", "r930")):
        d0 = dt.date.fromisoformat(start)
        days = [d for d in (d0 + dt.timedelta(i) for i in range(days_per_era * 2)) if d.weekday() < 5][:days_per_era]
        for d in days:
            gaps = np.where(rng.uniform(size=n) < 0.2, -0.04, 0.0) + rng.normal(0, 0.002, n)
            for c in range(n):
                ret = (drift if gaps[c] <= -0.03 else 0.0) + rng.normal(0, 0.004)
                r = _row(d.toordinal(), c, gaps[c], ret, spread, col=col)
                if col == "r930":
                    r[B.C["r1000"]] = ret
                rows.append(r)
    return np.array(rows)


def test_summary_words():
    both = B.analyze(_synthetic(drift=0.012))                     # 重いほう（0.6％）を引いてもプラス
    assert both["groups"]["D3"]["summary"] == B.OK_BOTH and both["eras"]["e1"]["days"] == 20
    low = B.analyze(_synthetic(drift=0.004, seed=2))              # 軽いほう（0.6×0.32≒0.19％）でだけプラス
    assert low["groups"]["D3"]["summary"] == B.OK_LOW, {k: v["low"].get("lo") for k, v in low["groups"]["D3"]["eras"].items()}
    none = B.analyze(_synthetic(drift=0.0, seed=3))
    assert none["groups"]["D3"]["summary"] == B.NONE and none["groups"]["D3"]["read"]["e4"]["gross"]["n"] > 0


def test_render_and_check_have_no_codes_or_returns():
    res = B.analyze(_synthetic(drift=0.004, seed=4))
    md = B.render_md({"generated_at": "x", "prereg_sha256": "0" * 64, "result": dict(res, n_codes=520)})
    assert "## まとめ" in md and "目隠しではない" in md and "投資助言ではありません" in md and "読むための表" in md
    assert "計算できず" in B.render_md({"generated_at": "x", "result": {"error": "e"}})
    out = B.check_summary(_synthetic(drift=0.004, seed=5), {"daily": [], "h1": [], "m5": []}, 520, None)
    assert not any(w in repr(out) for w in ("mean", "value", "net", "'win'")) and out["eras"]["e1"]["days"] == 20
    assert set(out["eras"]["e2"]["groups"]) == {"D1", "D2", "D3"}


def test_workflow_and_sync_forbidden():
    wf = open(".github/workflows/bounce-range-lab.yml", encoding="utf-8").read()
    assert "python -u bounce_range_lab.py --check" in wf and "restore-keys: jp-bars-" in wf
    assert "python tests/test_bounce_range_lab.py" in wf and "bounce-range-lab.json bounce-range-lab.md" in wf and "options: [check, run]" in wf
    assert '"bounce-range-lab.json", "bounce-range-lab.md"' in open("check_site_consistency.py", encoding="utf-8").read()


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
