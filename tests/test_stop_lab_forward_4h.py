# -*- coding: utf-8 -*-
"""損切りラボの前向き判定に「4時間足×逆張り×損切りATR3倍」を加えたことのテスト。2026-09-26 新設
（オーナー決定「成績を上げる」の③＝押し目買いに集中）。

これまで4時間足の前向きの取引は split したまま捨てていた。日足と同じ決まり（lab_forward）で判定する。

実行:  python tests/test_stop_lab_forward_4h.py     （pytest 不要。pytest でも動く）
"""
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import stop_lab as SL  # noqa: E402


def _trade(i, fam, a30_gain, month=10):
    """ATR3倍（A30）が いまの方式（A15）より a30_gain だけ良い、手作りの1取引"""
    R = {s: 0.0 for s in SL.STOPS}
    R["A30"] = a30_gain + (0.3 if i % 2 else -0.3)          # ばらつきを持たせる
    R["A15"] = (0.3 if i % 2 else -0.3)
    return {"ticker": ["GC=F", "ES=F", "USDJPY=X"][i % 3], "time": pd.Timestamp(f"2026-{month:02d}-{1 + i % 27:02d}"),
            "fam": fam, "cls": "index", "tf": "1d", "R": R, "gross": dict(R),
            "bars": {s: 5 for s in SL.STOPS}, "sl_atr": {s: 1.5 for s in SL.STOPS}}


def _explore():
    ts = [_trade(i, f, 0.05, month=1 + i % 12) for i in range(60) for f in ("tf", "mr")]
    ts = [dict(t, time=t["time"].replace(year=2010 + (i % 12))) for i, t in enumerate(ts)]
    return ts


def test_4h_forward_is_judged_with_the_same_rules():
    ts = _explore()
    fwd4h = [_trade(i, "mr", 0.2) for i in range(120)] + [_trade(i, "tf", 0.0) for i in range(30)]
    res = SL.evaluate(ts, ts, ts, ts, fwd1d=[], prev_forward={}, today="2026-10-31", fwd4h=fwd4h)
    f = res["forward"]["4h|mr|A30"]
    assert f["n"] == 120                                   # 逆張りの取引だけを数える（順張り30件は入らない）
    assert f["registered"].startswith("2026-09-26")
    assert f["history"] and f["history"][-1]["cp"] == 1    # 100件を超えたので1回目の判定が記録される
    assert f["history"][-1]["avg"] > 0.1


def test_without_4h_data_the_result_is_unchanged():
    ts = _explore()
    res = SL.evaluate(ts, ts, ts, ts, fwd1d=[], prev_forward={}, today="2026-10-31")
    assert "4h|mr|A30" not in res["forward"]
    assert "1d|mr|A30" in res["forward"]                   # 日足の登録はこれまでどおり


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
