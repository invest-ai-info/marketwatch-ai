# -*- coding: utf-8 -*-
"""組み合わせの相性ラボ（combo_lab.py）のテスト。2026-09-27 新設。

値動きはすべて作り物（ネットワークに出ない）。確かめること＝①出口の計算（損切り・利確・同じ足は損切りが先・
窓を開けた寄り付き・時間・5本線・追いかける損切り）②**選ぶのは前半だけ**（後半の成績で選ばない）③判定 ④事前登録と定数の一致。

実行:  python tests/test_combo_lab.py     （pytest 不要。pytest でも動く）
"""
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import combo_lab as C  # noqa: E402


def _bars(rows):
    """[(o, h, l, c), ...] → 配列4本"""
    a = np.array(rows, float)
    return a[:, 0], a[:, 1], a[:, 2], a[:, 3]


def test_prereg_numbers_match_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "## 組み合わせの相性ラボ" in text and "10×6×6＝360" in text
    assert C.SPLIT == "2016-01-01" and C.MIN_N_EXPLORE == 150 and "件数150以上" in text
    assert C.TOP_K == 3 and "上位3つ" in text and abs(C.P_LIMIT - 0.05 / 3) < 1e-12 and "p＜0.05÷3" in text
    assert C.COOLDOWN == 5 and "5本あけるまで" in text and C.RISK_ATR == 1.5
    assert C.EXIT_RULE == {"X1": (1.5, 2.0, 20), "X2": (1.5, 3.0, 30), "X3": (3.0, 2.0, 20)}
    assert "損切り 1.5ATR・利確 2ATR・最長20本" in text and "損切り 3ATR・利確 2ATR・最長20本" in text
    assert len(C.TRENDS) * len(C.OSCS) * len(C.EXITS) == 360


def test_tp_sl_and_same_bar_rule():
    # 合図の足0 → 足1の始値100で入る。ATR=1 → X1 損切り98.5・利確102
    base = [(100, 100, 100, 100)]
    o, h, l, c = _bars(base + [(100, 101, 99.5, 100.5), (100.5, 102.5, 100, 102)] + [(102, 102, 102, 102)] * 25)
    ma5 = pd.Series(c).rolling(5).mean().values
    assert abs(C.simulate(o, h, l, c, ma5, 1.0, 0, "long", "X1") - 2 / 1.5) < 1e-12        # 利確
    o, h, l, c = _bars(base + [(100, 102.5, 98.0, 101)] + [(101, 101, 101, 101)] * 25)     # 同じ足で両方
    assert abs(C.simulate(o, h, l, c, ma5, 1.0, 0, "long", "X1") - (-1.5 / 1.5)) < 1e-12   # 損切りが先
    o, h, l, c = _bars(base + [(100, 100.5, 99.5, 100), (97.0, 97.5, 96.5, 97)] + [(97, 97, 97, 97)] * 25)
    assert abs(C.simulate(o, h, l, c, ma5, 1.0, 0, "long", "X1") - (-3 / 1.5)) < 1e-12     # 窓を開けたら始値
    # 売り：損切り101.5・利確98
    o, h, l, c = _bars(base + [(100, 100.2, 97.5, 98)] + [(98, 98, 98, 98)] * 25)
    assert abs(C.simulate(o, h, l, c, ma5, 1.0, 0, "short", "X1") - 2 / 1.5) < 1e-12


def test_time_exit_ma5_exit_and_trailing_stop():
    rows = [(100, 100, 100, 100)] * 6 + [(100, 100.5, 99.8, 100.2), (100.2, 101, 100, 100.9), (100.9, 101.2, 100.5, 101),
                                          (101, 101.5, 100.8, 101.4), (101.4, 101.6, 101, 101.5)] + [(101.5, 101.5, 101.5, 101.5)] * 70
    o, h, l, c = _bars(rows)
    ma5 = pd.Series(c).rolling(5).mean().values
    i = 5
    assert abs(C.simulate(o, h, l, c, ma5, 1.0, i, "long", "X4") - (c[i + 5] - o[i + 1]) / 1.5) < 1e-12   # 5本目の終値
    r5 = C.simulate(o, h, l, c, ma5, 1.0, i, "long", "X5")
    k = next(k for k in range(i + 1, i + 11) if c[k] > ma5[k])
    assert abs(r5 - (c[k] - o[i + 1]) / 1.5) < 1e-12                                                    # 5本線を越えた足の終値
    # 追いかける損切り：高値110まで上がったあと 106.9 まで下がる → 110−3＝107 で切られる
    up = [(100 + j, 101 + j, 99.5 + j, 100.8 + j) for j in range(10)]
    rows = [(100, 100, 100, 100)] + up + [(109.5, 110, 108, 108.5), (108, 108.2, 106.9, 107.2)] + [(107, 107, 107, 107)] * 60
    o, h, l, c = _bars(rows)
    ma5 = pd.Series(c).rolling(5).mean().values
    assert abs(C.simulate(o, h, l, c, ma5, 1.0, 0, "long", "X6") - (107 - o[1]) / 1.5) < 1e-12


def test_not_enough_bars_returns_none():
    o, h, l, c = _bars([(100, 100, 100, 100)] * 10)
    ma5 = pd.Series(c).rolling(5).mean().values
    assert C.simulate(o, h, l, c, ma5, 1.0, 0, "long", "X1") is None
    assert C.simulate(o, h, l, c, ma5, 0.0, 0, "long", "X4") is None


def _entry(date, osc, sign, st, R):
    return {"ticker": "K", "date": date, "osc": osc, "sign": sign, "st": st, "R": {x: R for x in C.EXITS}}


def test_pick_uses_the_first_half_only():
    up = [1.0] * 9
    es = []
    for k in range(200):
        es.append(_entry("2010-01-05", "O1", 1.0, up, 0.5))      # 前半だけ良い
        es.append(_entry("2020-01-05", "O1", 1.0, up, -0.5))
        es.append(_entry("2010-01-05", "O2", 1.0, up, -0.2))     # 後半だけ良い
        es.append(_entry("2020-01-05", "O2", 1.0, up, 2.0))
    rows = C.table(es)
    top = C.pick_top(rows)
    assert all(r["osc"] == "O1" for r in top)
    assert all(r["m_e"] == 0.5 for r in top)


def test_trend_filter_matches_direction():
    st = [1.0, -1.0] + [0.0] * 7                                     # T1 上昇・T2 下降
    assert C.trend_ok(_entry("2010-01-05", "O1", 1.0, st, 0), "T1")
    assert not C.trend_ok(_entry("2010-01-05", "O1", 1.0, st, 0), "T2")
    assert C.trend_ok(_entry("2010-01-05", "O1", -1.0, st, 0), "T2")
    assert not C.trend_ok(_entry("2010-01-05", "O1", 1.0, st, 0), "T3")
    assert C.trend_ok(_entry("2010-01-05", "O1", -1.0, st, 0), "T0")


def test_judge():
    assert C.judge({"lo": 0.05}, 0.001) == "確かめでも残った（有望）"
    assert C.judge({"lo": 0.05}, 0.02) == "確かめで消えた"             # 0.05÷3 に届かない
    assert C.judge({"lo": -0.01}, 0.001) == "確かめで消えた"
    assert C.judge({"lo": None}, None) == "確かめで消えた"


def test_signals_on_a_real_shaped_series():
    rng = np.random.default_rng(3)
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, 800)))
    o = np.concatenate([[c[0]], c[:-1]])
    df = pd.DataFrame({"Open": o, "High": np.maximum(o, c) * 1.003, "Low": np.minimum(o, c) * 0.997, "Close": c},
                      index=pd.bdate_range("2006-01-02", periods=800))
    sig = C.osc_signals(df)
    assert set(sig) == {(o_, s) for o_ in C.OSCS for s in ("long", "short")}
    for k, v in sig.items():
        assert 0 < v.sum() < 800 * 0.4, (k, v.sum())
    es = C.entries_for("ES=F", df)
    assert es and all(set(e["R"]) == set(C.EXITS) for e in es) and all(len(e["st"]) == 9 for e in es)


def test_render_md_runs():
    rows = [{"t": t, "osc": o, "ex": x, "n_e": 200, "m_e": 0.01, "n_c": 100, "m_c": 0.0}
            for t in C.TRENDS for o in C.OSCS for x in C.EXITS]
    res = {"generated_at": "x", "prereg_sha256": "a" * 64,
           "result": {"rows": rows, "picked": [dict(rows[0], confirm={"n": 100, "mean": 0.0, "verdict": "確かめで消えた"})],
                      "top10": rows[:10], "baseline": {"a": rows[0]}, "entries": 10, "missing": []}}
    md = C.render_md(res)
    assert "投資助言ではありません" in md and "確かめで消えた" in md and "トレンドなし" in md


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
