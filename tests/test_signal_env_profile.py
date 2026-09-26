# -*- coding: utf-8 -*-
"""signal_env_profile.py（シグナルが効いたとき・効かなかったときの環境）の計算の部品のテスト。2026-09-26 新設。

実行:  python tests/test_signal_env_profile.py     （pytest 不要。pytest でも動く）
"""
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import exit_rule_backtest as X  # noqa: E402
import signal_env_profile as P  # noqa: E402


def test_t_critical_values_match_known_table():
    for df, exp in [(10, 2.2281), (17, 2.1098), (120, 1.9799)]:
        assert abs(P.t_crit(0.05, df) - exp) < 1e-3


def test_standard_error_matches_safe_formula():
    rng = np.random.default_rng(1)
    v = rng.standard_normal(400)
    groups = [(f"t{i % 7}", i // 9) for i in range(400)]
    _m, s1, _df = P.mean_se_safe(v, groups)
    _m, s2, _c = X._mean_se_safe(v, groups)
    assert abs(s1 - s2) < 1e-12


def test_load_excludes_unresolved_and_pseudo_and_centers_each_stratum():
    rows = P.load()
    assert rows and all(x["d"].get("outcome") in ("tp1", "tp2", "sl") for x in rows)
    assert not any(x["d"].get("pseudo_record") for x in rows)
    by = {}
    for x in rows:
        by.setdefault(x["stratum"], []).append(x["xw"])
    assert all(abs(sum(v) / len(v)) < 1e-9 for v in by.values())   # 超過勝率は種類ごとに平均0


def test_buckets_use_only_values_known_at_signal_time():
    # 結果のあとに付く敗因・勝因の分析（loss_analysis / win_analysis）を区分に使っていないこと
    src = open(os.path.join(ROOT, "signal_env_profile.py"), encoding="utf-8").read()
    code = src.split('"""', 2)[2]
    assert "loss_analysis" not in code and "win_analysis" not in code


def test_monthly_change_section_reports_verdict_changes():
    # 前回の月の判定と違う区分があれば「前回からの変化」に出る／前向きの表も出る
    rows = P.load()
    K = sum(len(o) for _k, _t, _f, o in P.DIMS)
    res = P.analyze(rows, K)
    meta = {"asof": "2026-10-02 10:17", "first": "2026-05-21", "last": "2026-10-01", "excluded": 0}
    prev = P.snapshot(res, dict(meta, asof="2026-09-26 17:00"), K)
    prev["month"] = "2026-09"
    key = next(iter(prev["cells"]))
    prev["cells"][key]["verdict"] = "確かめられた・効きやすい"      # わざと違う判定にする
    md = P.render(res, [], K, meta, prev=prev, fwd=P.forward_fbias(rows))
    sec = md.split("## 前回からの変化", 1)[1].split("## 項目ごとの表", 1)[0]
    c = prev["cells"][key]
    assert f"{c['title']}＝{c['bucket']}：確かめられた・効きやすい → " in sec
    assert "前回 2026-09" in sec and "前向きの追跡：ファンダの見立てと逆向き" in md


def test_forward_counts_only_after_registration():
    rows = P.load()
    fwd = P.forward_fbias(rows)
    n_expected = sum(1 for x in rows if x["date"] >= P.FWD_FROM and P.V.fbias_of(x["d"]) == "mismatch")
    assert fwd["mismatch"]["n"] == n_expected


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
