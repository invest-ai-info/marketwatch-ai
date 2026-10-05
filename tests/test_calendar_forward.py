# -*- coding: utf-8 -*-
"""R3F 月末月初の前向きの観察（calendar_forward.py）のテスト。2026-10-05 新設。

実行:  python tests/test_calendar_forward.py     （pytest 不要。pytest でも動く）
"""
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import calendar_forward as F  # noqa: E402
import calendar_lab as CL  # noqa: E402


def _px(start="2026-06-01", end="2027-03-31"):
    d = pd.bdate_range(start, end)
    return pd.Series(np.linspace(100, 110, len(d)), index=d)


def test_only_trades_bought_on_or_after_start_and_sold_before_until():
    px = _px()
    tr = F.new_trades(px, "Q1", "2026-12-31")
    assert tr and all(t["buy"] >= F.FWD_START for t in tr) and all(t["sell"] <= "2026-12-31" for t in tr)
    assert tr[0]["buy"] == "2026-10-29" and tr[0]["sell"] == "2026-11-04"     # 10月の最後から2日目 → 11月の3日目
    q3 = F.new_trades(px, "Q3", "2026-12-31")
    assert q3[0]["buy"] == "2026-10-23" and q3[0]["sell"] == "2026-11-03"     # 10月の最後から6日目 → 11月の2日目


def test_costs_match_calendar_lab():
    px = _px()
    t = F.new_trades(px, "Q1", "2026-12-31")[0]
    days = (pd.Timestamp(t["sell"]) - pd.Timestamp(t["buy"])).days
    assert abs(t["net"] - (t["gross"] - CL.TOM["Q1"]["cost"] - CL.FIN_RATE * days / 365)) < 1e-12


def test_recorded_trades_are_never_rewritten():
    old = [{"c": "Q1", "buy": "2026-10-29", "sell": "2026-11-04", "gross": 0.01, "net": 0.009}]
    new = [{"c": "Q1", "buy": "2026-10-29", "sell": "2026-11-04", "gross": -0.5, "net": -0.5},
           {"c": "Q1", "buy": "2026-11-26", "sell": "2026-12-03", "gross": 0.002, "net": 0.001}]
    m = F.merge(old, new)
    assert len(m) == 2 and m[0]["net"] == 0.009


def test_check_every_36_stops_only_when_negative():
    st = F.empty_state()
    st["trades"] = [{"c": "Q1", "buy": f"t{i:03d}", "net": 0.001} for i in range(36)] + \
                   [{"c": "Q3", "buy": f"t{i:03d}", "net": -0.001} for i in range(40)]
    st = F.update_checks(st, "2029-11-06")
    assert "Q1" not in st["verdicts"] and st["checks"]["Q1"][0]["n"] == 36
    assert st["verdicts"]["Q3"]["status"] == "stop" and st["verdicts"]["Q3"]["n"] == 36
    st = F.update_checks(st, "2029-12-06")                      # 2回目でも区切りは増えない
    assert len(st["checks"]["Q1"]) == 1


def test_state_is_readable_by_verified_list():
    import verified_list as V
    st = F.empty_state()
    assert set(st["titles"]) == set(F.QS) and st["goal"] == F.CHECK_EVERY and st["kind"] == "forward"
    assert any(src[0] == F.OUT_JSON for src in V.SOURCES)


def test_constants_match_preregistration():
    txt = open(os.path.join(ROOT, "PILLAR_PREREG.md"), encoding="utf-8").read()
    sec = txt.split("## R3F 月末月初の前向きの観察", 1)[1].split("\n## ", 1)[0]
    assert "2026-10-06 以降" in sec and F.FWD_START == "2026-10-06"
    assert "36回" in sec and F.CHECK_EVERY == 36


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
