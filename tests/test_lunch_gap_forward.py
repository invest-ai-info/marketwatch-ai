# -*- coding: utf-8 -*-
"""R10F 昼休みの窓と同じ向きに後場を持つ・前向き（lunch_gap_forward.py）のテスト。2026-10-08 新設。

値動きはすべて作り物。確かめること＝①事前登録と定数の一致 ②登録日より前・今日の日は数えない・一度数えた日は数え直さない
③腕の損益（F1 は 0.20％以上の日だけ・g＝0 は持たない）④判定の時点（F1 は100回・F2 は250日）と途中の見張り
⑤読むための欄 ⑥ワークフロー・見張り番・SYNC 禁忌・検証済みリスト・研究の地図。

実行:  python tests/test_lunch_gap_forward.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import lunch_gap_forward as F  # noqa: E402


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "## R10F 昼休みの窓と同じ向きに後場を持つ・前向きの記録" in text and "**2026-10-09 以降**" in text
    assert (F.FWD_START, F.LINE, F.COST, F.GOAL) == ("2026-10-09", 0.002, 0.0001, {"F1": ("n", 100), "F2": ("days", 250)})
    assert F.CHECKS == (60, 120, 180, 240) and abs(F.ALPHA - 0.025) < 1e-12 and "**0.20％以上**" in text and "**F2 は 250日（数えた日）・F1 は 100回に届いたとき**" in text


def _sess(start, n, drift, seed=1, big_every=4):
    """平日 n 日分。4日に1日は大きな窓（±0.3％）・後場は窓と同じ向きに drift だけ動く"""
    rng = np.random.default_rng(seed)
    out, d = [], dt.date.fromisoformat(start)
    while len(out) < n:
        if d.weekday() < 5:
            i = len(out)
            g = (0.003 if i % 2 else -0.003) if i % big_every == 0 else rng.normal(0, 0.0008)
            a = np.sign(g) * drift + rng.normal(0, 0.001)
            out.append((d, 100.0, 100.0 * (1 + g), 100.0 * (1 + g) * (1 + a)))
        d += dt.timedelta(1)
    return out


def test_counts_once_and_only_after_registration():
    st = F.empty_state()
    sess = _sess("2026-10-05", 10, 0.002)
    added = F.add_days(st, sess, "2026-10-14")
    assert added == ["2026-10-09", "2026-10-12", "2026-10-13"]                 # 10/9 より前・10/14 以降は入れない
    assert F.add_days(st, sess, "2026-10-20") == ["2026-10-14", "2026-10-15", "2026-10-16"] and len(st["days"]) == 6
    assert F.add_days(st, sess, "2026-10-20") == []                             # 数え直さない


def test_arm_values():
    assert F.arm_value("F1", 0.001, 0.01) is None and F.arm_value("F2", 0.0, 0.01) is None
    assert abs(F.arm_value("F1", -0.003, -0.004) - (0.004 - F.COST)) < 1e-12
    assert abs(F.arm_value("F2", 0.0005, -0.002) - (-0.002 - F.COST)) < 1e-12


def test_judgement_points_and_interim():
    st = F.empty_state()
    F.add_days(st, _sess("2026-10-09", 260, 0.002), "2099-01-01")
    v = st["verdicts"]
    assert v["F2"]["days"] == 250 and v["F2"]["status"] == "plus"              # F2 は 250日で判定
    assert "F1" not in v and 65 <= F.measure(st, "F1")["n"] < 100              # F1 は 100回まで観察中
    F.add_days(st, _sess("2026-10-09", 420, 0.002), "2099-01-01")
    assert st["verdicts"]["F1"]["n"] == 100 and st["verdicts"]["F1"]["status"] == "plus" and F.done(st)
    bad = F.empty_state()
    F.add_days(bad, _sess("2026-10-09", 130, -0.002, seed=2), "2099-01-01")
    assert bad["verdicts"]["F1"]["days"] == 60 and "途中の見張り" in bad["verdicts"]["F1"]["reason"]
    assert bad["verdicts"]["F2"]["days"] == 60 and len(bad["interim"]) == 2


def test_reading_and_outputs():
    st = F.empty_state()
    F.add_days(st, _sess("2026-10-09", 80, 0.001, seed=3), "2099-01-01")
    rd = F.reading(st)
    assert rd["down"]["n"] + rd["up"]["n"] == F.measure(st, "F1")["n"] and rd["slope"] is not None and rd["monday"]["n"] >= 1
    F.finalize(st)
    assert st["progress"]["F1"] == F.measure(st, "F1")["n"] and "250日" in st["goal"]
    md = F.render_md(st, "x")
    assert "R10F" in md and "読むための欄" in md and "投資助言ではありません" in md and "R10 は +0.436" in md


def test_registrations():
    wf = open(".github/workflows/lunch-gap-forward.yml", encoding="utf-8").read()
    assert "python lunch_gap_forward.py" in wf and "python verified_list.py" in wf and "17 7 * * 1-5" in wf and "47 23 * * 0-4" in wf
    assert "lunch-gap-forward.json lunch-gap-forward.md verified-list.md" in wf
    assert '"lunch-gap-forward.json", "lunch-gap-forward.md"' in open("check_site_consistency.py", encoding="utf-8").read()
    assert '"lunch-gap-forward.yml", 24 * 4' in open("check_automation_health.py", encoding="utf-8").read()
    assert '"lunch-gap-forward.json"' in open("verified_list.py", encoding="utf-8").read()
    assert "LUNCH_FWD" in open("research_map.py", encoding="utf-8").read()


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
