# -*- coding: utf-8 -*-
"""トレンドの見方の比べ比べ（trend_lab.py）のテスト。2026-09-27 新設。

値動きはすべて作り物（ネットワークに出ない）。確かめること＝①9つの見方が素直な上昇・下降を正しく読む
②先の値動きを見ていない（後ろの足を変えても、前の日の向きが変わらない）③物差しと判定が事前登録どおり。

実行:  python tests/test_trend_lab.py     （pytest 不要。pytest でも動く）
"""
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import trend_lab as T  # noqa: E402


def _ohlc(close, seed=0, spread=0.004):
    rng = np.random.default_rng(seed)
    c = np.asarray(close, float)
    o = np.concatenate([[c[0]], c[:-1]])
    h = np.maximum(o, c) * (1 + spread * rng.random(len(c)))
    l = np.minimum(o, c) * (1 - spread * rng.random(len(c)))
    idx = pd.bdate_range("2006-01-02", periods=len(c))
    return pd.DataFrame({"Open": o, "High": h, "Low": l, "Close": c}, index=idx)


def _trend(n, drift, seed=1, vol=0.006):
    rng = np.random.default_rng(seed)
    return 100 * np.exp(np.cumsum(drift + rng.normal(0, vol, n)))


def test_prereg_numbers_match_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "## トレンドの見方の比べ比べ" in text
    assert T.SPLIT == "2016-01-01" and "2016年から" in text and T.MIN_N == 300 and "件数300未満" in text
    assert T.N_DEFS == 9 and abs(T.P_LIMIT - 0.05 / 9) < 1e-12 and "p＜0.05÷9" in text
    assert T.WARMUP == 260 and "先頭260本" in text and T.VOL_DAYS == 20
    for w in ("前後5本", "直近3本", "25より上", "直前55本", "10本・3倍", "（3・5・8・10・12・15）", "（30・35・40・45・50・60）"):
        assert w in text, w
    assert len(T.NAMES) == T.N_DEFS and len(T.TICKERS) == 18


def test_all_definitions_read_a_clean_uptrend_and_downtrend():
    up = T.all_states(_ohlc(_trend(700, 0.002)))
    dn = T.all_states(_ohlc(_trend(700, -0.002, seed=2)))
    for k in T.NAMES:
        tail_up, tail_dn = up[k][400:], dn[k][400:]
        need = 0.4 if k == "T8" else 0.6          # 平均足は「3本そろう」まで0のままの日が多い（見方の性質）
        assert (tail_up > 0).mean() > need, (k, (tail_up > 0).mean())
        assert (tail_dn < 0).mean() > need, (k, (tail_dn < 0).mean())
        assert (tail_up < 0).mean() < 0.2 and (tail_dn > 0).mean() < 0.2, k


def test_no_look_ahead():
    """後ろの足を大きく変えても、それより前の日の向きは変わらない"""
    base = _trend(600, 0.001, seed=3)
    df = _ohlc(base)
    full = T.all_states(df)
    cut = 450
    changed = base.copy()
    changed[cut:] = changed[cut:] * np.linspace(1, 0.5, len(changed) - cut)     # 先を大きく下げる
    alt = T.all_states(_ohlc(changed))
    for k in T.NAMES:
        assert np.array_equal(full[k][:cut], alt[k][:cut]), k


def test_dow_keeps_state_until_a_clear_reversal():
    # 山と谷が切り上がる → 上昇。その後、山だけ下がる（谷は上がる）＝どちらでもない → 上昇のまま
    seg = []
    for k in range(6):
        seg += list(np.linspace(100 + 4 * k, 110 + 4 * k, 8)) + list(np.linspace(110 + 4 * k, 102 + 4 * k, 8))
    peak = seg[-8]
    seg += list(np.linspace(seg[-1], peak - 1, 8)) + list(np.linspace(peak - 1, seg[-1] + 1, 8))
    c = np.array(seg, float)
    st = T.t3_dow(c * 1.001, c * 0.999)
    assert st[80] == 1.0 and st[-1] == 1.0


def test_donchian_keeps_the_last_break():
    c = np.concatenate([np.full(60, 100.0), [110.0], np.full(30, 105.0), [80.0], np.full(10, 85.0)])
    st = T.t5_donchian(c * 1.0, c * 1.0, c)
    assert st[60] == 1.0 and st[80] == 1.0 and st[91] == -1.0 and st[-1] == -1.0


def test_monthly_rows_hold_to_next_month_end():
    df = _ohlc(_trend(420, 0.001, seed=4))
    states = {"T2": np.ones(len(df))}
    rows = [r for r in T.monthly_rows("X", df, states) if r["def"] == "T2"]
    ends = T.month_ends(df.index)
    a, b = [e for e in ends if e >= T.WARMUP][:2]
    c = df["Close"].values
    v = np.std(np.diff(np.log(c))[a - 20:a], ddof=1)
    assert rows[0]["date"] == df.index[a].date().isoformat()
    assert abs(rows[0]["z"] - np.log(c[b] / c[a]) / (v * np.sqrt(b - a))) < 1e-12


def _rows(effect, n_months=240, tickers=8, seed=5):
    rng = np.random.default_rng(seed)
    rows = []
    months = pd.date_range("2006-01-31", periods=n_months, freq="ME")
    for t in range(tickers):
        for m in months:
            s = float(rng.choice([1, -1]))
            raw = effect * s + rng.normal(0, 1)
            rows.append({"ticker": f"K{t}", "date": m.date().isoformat(), "def": "T1", "sign": s, "raw": raw,
                         "z": s * raw, "conv": ""})
    return rows


def test_judgement_needs_all_conditions():
    assert T.stats_for(_rows(0.3), n_perm=300)["verdict"] == "偽薬より当てになる"
    assert T.stats_for(_rows(0.0), n_perm=300)["verdict"] == "偽薬と差なし"
    assert T.stats_for(_rows(-0.3), n_perm=300)["verdict"] == "逆に効く"
    assert T.stats_for(_rows(0.3, n_months=30, tickers=5), n_perm=100)["verdict"] == "件数不足"


def test_render_md_runs():
    res = {"generated_at": "x", "prereg_sha256": "a" * 64,
           "result": {"defs": {"T1": {"n": 400, "verdict": "偽薬と差なし", "share_long": 0.5, "by_class": {"為替": {"n": 3, "mean": 0.1}}}},
                      "agreement": {"T1-T2": 0.8}, "missing": []}}
    md = T.render_md(res)
    assert "投資助言ではありません" in md and "T1 移動平均" in md and "T1-T2 80%" in md


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
