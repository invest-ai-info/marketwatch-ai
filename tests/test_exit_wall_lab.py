# -*- coding: utf-8 -*-
"""exit_wall_lab.py（出口の壁ラボ）の手じまいの計算と壁の見つけ方のテスト。2026-09-26 新設。

手で作った値動きで、いまの方式・追いかける損切り・半分利確・壁の選び方が、事前登録どおりに動くことを固定する。

実行:  python tests/test_exit_wall_lab.py     （pytest 不要。pytest でも動く）
"""
import importlib.util
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_spec = importlib.util.spec_from_file_location("exit_wall_lab", os.path.join(ROOT, "exit_wall_lab.py"))
W = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(W)


def _A(bars, atr=1.0, extra=None):
    """bars＝[(始値, 高値, 安値, 終値), ...]。0本目が入った足（終値＝入値）。"""
    o, h, l, c = (np.array([b[k] for b in bars], float) for k in range(4))
    A = {"o": o, "h": h, "l": l, "c": c, "atr": np.full(len(bars), atr)}
    for k in ("ma25", "ma75", "ma200", "bbu", "bbl"):
        A[k] = np.full(len(bars), np.nan)
    A.update(extra or {})
    return A


def test_p0_take_profit():
    # 入値100・ATR1 → 損切り98.5（1R=1.5）・利確102（+1.33R）
    A = _A([(100, 100, 100, 100), (100, 101, 99.5, 100.5), (100.5, 102.2, 100.2, 102)])
    r, bars = W._run(A, 0, tp=102.0)
    assert abs(r - 2.0 / 1.5) < 1e-9 and bars == 2


def test_stop_first_when_both_touched():
    A = _A([(100, 100, 100, 100), (100, 102.5, 98.0, 101)])
    r, _ = W._run(A, 0, tp=102.0)
    assert abs(r - (-1.0)) < 1e-9


def test_stop_gap_fills_at_open():
    A = _A([(100, 100, 100, 100), (97.0, 97.5, 96.5, 97.2)])
    r, _ = W._run(A, 0, tp=102.0)
    assert abs(r - (97.0 - 100) / 1.5) < 1e-9


def test_trailing_stop_follows_high_next_bar():
    # 最高値106 → 損切り 106−3＝103（次の足から効く）→ 102.9 まで下げたので 103 で手じまい
    A = _A([(100, 100, 100, 100), (100, 106, 99.9, 105.5), (105.5, 105.8, 102.9, 103.1)])
    r, bars = W._run(A, 0, trail=True)
    assert abs(r - 3.0 / 1.5) < 1e-9 and bars == 2


def test_half_take_then_breakeven():
    # 壁101で半分利確（+0.667R×0.5）→ 残りは建値100へ → 99.9 で建値に触れて 0
    A = _A([(100, 100, 100, 100), (100, 101.2, 100.1, 100.8), (100.8, 100.9, 99.9, 100.0)])
    r, _ = W._run(A, 0, half_tp=101.0)
    assert abs(r - 0.5 * (1.0 / 1.5)) < 1e-9


def test_max_hold_exits_at_close():
    bars = [(100, 100, 100, 100)] + [(100, 100.3, 99.8, 100.1)] * (W.MAX_HOLD + 5)
    r, n = W._run(_A(bars), 0, tp=102.0)
    assert n == W.MAX_HOLD and abs(r - 0.1 / 1.5) < 1e-9


def test_unresolved_is_none():
    r, n = W._run(_A([(100, 100, 100, 100), (100, 100.5, 99.5, 100)]), 0, tp=102.0)
    assert r is None and n is None


def test_wall_picks_nearest_above_and_ignores_below():
    n = 70
    bars = [(100, 100.5, 99.5, 100)] * n
    bars[30] = (100, 103.0, 99.5, 100)          # 60本の中の高値＝103
    A = _A(bars, extra={"ma25": np.full(n, 101.2), "ma75": np.full(n, 99.0), "bbu": np.full(n, 104.0)})
    # 候補: 20本の高値100.5・60本の高値103・山(103)・25本線101.2・+2σ104（75本線99は下）→ いちばん近い 100.5
    assert abs(W.wall_above(A, n - 1) - 100.5) < 1e-9
    # 入値＋0.05ATR 以下は壁にしない
    bars2 = [(100, 100.03, 99.5, 100)] * n
    A2 = _A(bars2, extra={"ma25": np.full(n, 101.2)})
    assert abs(W.wall_above(A2, n - 1) - 101.2) < 1e-9


def test_policy_switching():
    # 壁が 0.5R（100.75）→ P1 は壁−0.1ATR＝100.65 で利確、P4 も同じ
    A = _A([(100, 100, 100, 100), (100, 100.7, 99.9, 100.6)])
    res, d = W.policies_for(A, 0, 100.75)
    assert abs(d - 0.5) < 1e-9
    assert abs(res["P1"][0] - 0.65 / 1.5) < 1e-9 and res["P4"] == res["P1"]
    # 壁なし → P1 は P0、P3・P4 は P2
    res, d = W.policies_for(A, 0, None)
    assert d is None and res["P1"] == res["P0"] and res["P3"] == res["P2"] and res["P4"] == res["P2"]


def test_mirror_short_is_long_math():
    A = {"o": np.array([100.0]), "h": np.array([101.0]), "l": np.array([99.0]), "c": np.array([100.5]),
         "atr": np.array([1.0]), "ma25": np.array([100.0]), "ma75": np.array([100.0]), "ma200": np.array([100.0]),
         "bbu": np.array([102.0]), "bbl": np.array([98.0])}
    M = W.mirror(A)
    assert M["h"][0] == -99.0 and M["l"][0] == -101.0 and M["bbu"][0] == -98.0 and M["c"][0] == -100.5


def test_default_se_is_safe_and_not_narrower():
    # 2026-09-26 オーナー決定: 既定の幅は安全側（旧い出し方より狭くならない）
    import exit_rule_backtest as X
    assert X._mean_se is X._mean_se_safe
    rng = np.random.default_rng(0)
    vals = rng.standard_normal(600)
    groups = [(f"t{i % 6}", 2006 + (i // 6) % 11) for i in range(600)]   # 銘柄6×年11
    _m, se_new, _c = X._mean_se(vals, groups)
    _m, se_old, _c = X._mean_se_legacy(vals, groups)
    assert se_new >= se_old - 1e-12


def test_dist_buckets():
    assert W.dist_bucket(None) == "≥2.67R/なし"
    assert W.dist_bucket(0.5) == "<0.67R"
    assert W.dist_bucket(1.0) == "0.67-1.33R"
    assert W.dist_bucket(2.0) == "1.33-2.67R"
    assert W.dist_bucket(3.0) == "≥2.67R/なし"


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
