# -*- coding: utf-8 -*-
"""lab_forward.py（研究ラボの前向きの判定の積み上げ）のテスト。2026-09-26 新設。

件数100ごとにだけ判定する・合格は2回続けて確定・逆向きは1回で確定・前回の判定を引き継ぐ、を固定する。

実行:  python tests/test_lab_forward.py     （pytest 不要。pytest でも動く）
"""
import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_spec = importlib.util.spec_from_file_location("lab_forward", os.path.join(ROOT, "lab_forward.py"))
LF = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(LF)

GOOD = lambda n: {"n": n, "avg": 0.2, "lo": 0.05, "hi": 0.35}
BAD = lambda n: {"n": n, "avg": -0.2, "lo": -0.35, "hi": -0.05}
MEH = lambda n: {"n": n, "avg": 0.05, "lo": -0.1, "hi": 0.2}
SMALL = lambda n: {"n": n, "avg": 0.06, "lo": 0.01, "hi": 0.11}   # 0をまたがないが 0.10R 未満


def test_accumulating_below_min_n():
    e = LF.step(None, GOOD(40), +1, "2026-10-04")
    assert e["state"] == "🟡蓄積中" and e["history"] == []


def test_pass_twice_confirms():
    e = LF.step(None, GOOD(120), +1, "d1")
    assert e["state"].startswith("🟢") and len(e["history"]) == 1
    e = LF.step(e, GOOD(150), +1, "d2")             # 同じチェックポイント（100台）＝判定しない
    assert len(e["history"]) == 1 and e["state"].startswith("🟢")
    e = LF.step(e, GOOD(210), +1, "d3")
    assert e["state"].startswith("✅") and len(e["history"]) == 2


def test_pass_then_undecided_resets():
    e = LF.step(None, GOOD(100), +1, "d1")
    e = LF.step(e, MEH(200), +1, "d2")
    assert e["state"].startswith("⚪")
    e = LF.step(e, GOOD(300), +1, "d3")
    assert e["state"].startswith("🟢")                # 連続ではないので確定しない


def test_opposite_is_final_signal():
    e = LF.step(None, BAD(100), +1, "d1")
    assert e["state"].startswith("⛔")


def test_expected_negative_direction():
    e = LF.step(None, BAD(100), -1, "d1")
    e = LF.step(e, BAD(200), -1, "d2")
    assert e["state"].startswith("✅")


def test_small_effect_is_not_pass():
    e = LF.step(None, SMALL(100), +1, "d1")
    assert e["state"].startswith("⚪")


def test_jump_over_several_checkpoints_counts_once():
    e = LF.step(None, GOOD(350), +1, "d1")
    assert len(e["history"]) == 1 and e["history"][0]["cp"] == 3


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
    print(f"--- {len(tests) - fails}/{len(tests)} 合格 ---")
    sys.exit(1 if fails else 0)
