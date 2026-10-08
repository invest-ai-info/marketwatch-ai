# -*- coding: utf-8 -*-
"""R10 日本の昼休みの窓（lunch_gap_lab.py）のテスト。2026-10-08 新設。

値動きはすべて作り物。確かめること＝①事前登録と定数の一致 ②前場・後場の足の分け方（12:00 より前／以後）と g・a
③Q1（上位20％の日に逆向き）・Q2（傾き）と判定の言葉（戻る・続く・向きなし・前半と後半で違う）④点検は損益を出さない
⑤ワークフロー・SYNC 禁忌・検証済みリスト。

実行:  python tests/test_lunch_gap_lab.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import lunch_gap_lab as L  # noqa: E402


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "## R10 日本の昼休みの窓" in text and "**まだ誰も数えていない**" in text
    assert (L.TICKER, L.NOON, L.TOP_SHARE, L.N_BOOT, L.COST) == ("1321.T", 12, 0.20, 10000, 0.0001)
    assert abs(L.ALPHA - 0.025) < 1e-12 and "上位20％" in text and "**0.01％**" in text and "前場の足＝12:00 より前に始まる足" in text


def test_sessions_and_gaps():
    j = lambda h, m: dt.datetime(2026, 10, 1, h, m)  # noqa: E731
    bars = [(j(9, 0), 100, 101, 99, 100.5), (j(10, 0), 100.5, 101, 100, 100.8), (j(11, 0), 100.8, 101, 100, 101.0),
            (j(12, 30), 101.5, 102, 101, 101.2), (j(13, 30), 101.2, 102, 101, 101.0), (j(14, 30), 101.0, 101.5, 100, 100.9),
            (dt.datetime(2026, 10, 2, 9, 0), 100, 101, 99, 100)]                       # 前場だけの日は数えない
    sess = L.sessions(bars)
    assert sess == [(dt.date(2026, 10, 1), 101.0, 101.5, 100.9)]
    d, g, a = L.gaps(sess)
    assert abs(g[0] - (101.5 / 101.0 - 1)) < 1e-12 and abs(a[0] - (100.9 / 101.5 - 1)) < 1e-12


def _days(n, rho, seed=1, flip_half=False):
    """a ＝ rho × g ＋ でたらめ（rho＜0 なら戻る向き）"""
    rng = np.random.default_rng(seed)
    d = [dt.date(2024, 10, 1) + dt.timedelta(i) for i in range(n)]
    g = rng.normal(0, 0.003, n)
    r = np.full(n, rho)
    if flip_half:
        r[n // 2:] = -rho
    a = r * g + rng.normal(0, 0.003, n)
    return d, g, a


def test_judge_words():
    rev = L.analyze_days(*_days(490, -0.8))
    assert rev["Q1"]["summary"] == L.REVERT and rev["Q2"]["summary"] == L.REVERT and rev["Q1"]["value"] > 0 and rev["Q2"]["value"] < 0
    fol = L.analyze_days(*_days(490, 0.8, seed=2))
    assert fol["Q1"]["summary"] == L.FOLLOW and fol["Q2"]["summary"] == L.FOLLOW
    flat = L.analyze_days(*_days(490, 0.0, seed=3))
    assert flat["Q1"]["summary"] in (L.NONE, L.SPLIT) and set(L.verdicts_of(flat, "x")) >= {"Q1"} or flat["Q1"]["summary"] == L.NONE
    split = L.analyze_days(*_days(490, -1.5, seed=4, flip_half=True))
    assert split["Q2"]["summary"] in (L.NONE, L.SPLIT)
    assert rev["Q1"]["n"] == 98 and abs(rev["read"]["net_in_q1_direction"] - (rev["Q1"]["value"] - L.COST)) < 1e-12
    assert len(rev["read"]["quintiles"]) == 5 and set(rev["read"]["month_edge"]) == {"first", "mid", "last"}
    assert L.verdicts_of(rev, "x") == {}


def test_render_and_check():
    res = L.analyze_days(*_days(300, -0.5, seed=5))
    md = L.render_md({"generated_at": "x", "prereg_sha256": "0" * 64, "result": res})
    assert "## まとめ" in md and "Q1 大きな昼休みの窓" in md and "投資助言ではありません" in md
    assert "計算できず" in L.render_md({"generated_at": "x", "result": {"error": "e"}})
    ix = pd.DatetimeIndex([pd.Timestamp("2026-10-01 00:00", tz="UTC"), pd.Timestamp("2026-10-01 03:30", tz="UTC")])
    df = pd.DataFrame({"Open": [100.0, 101.0], "High": [101.0, 102.0], "Low": [99.0, 100.0], "Close": [100.5, 101.5]}, index=ix)
    out = L.check_summary(df)
    assert out["bar_start_times"] == {"09:00": 1, "12:30": 1} and out["days_with_both_sessions"] == 1
    assert not any(w in repr(out) for w in ("value", "mean", "'lo'"))
    assert out["lunch_gap_zero_share"] == 0.0 and abs(out["lunch_gap_sd"]) < 1e-12 and "a_sd" not in out   # 1日だけ＝ばらつき0


def test_workflow_sync_and_verified_list():
    wf = open(".github/workflows/lunch-gap-lab.yml", encoding="utf-8").read()
    assert "python -u lunch_gap_lab.py --check" in wf and "options: [check, run]" in wf and "python tests/test_lunch_gap_lab.py" in wf
    assert "lunch-gap-lab.json lunch-gap-lab.md verified-list.md" in wf and "python verified_list.py" in wf
    assert '"lunch-gap-lab.json", "lunch-gap-lab.md"' in open("check_site_consistency.py", encoding="utf-8").read()
    assert '"lunch-gap-lab.json"' in open("verified_list.py", encoding="utf-8").read()


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
