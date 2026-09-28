# -*- coding: utf-8 -*-
"""C2 チャートパターン（pattern_lab.py）のテスト。作り物の値動きだけを使う（本物の成績は見ない）。2026-09-28 新設。

実行:  python tests/test_pattern_lab.py     （pytest 不要。pytest でも動く）
"""
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import pattern_lab as L  # noqa: E402

CHI = [0.03]


def path(points):
    """(日, 値) を直線でつないだ終値"""
    ts = [t for t, _ in points]
    vs = [v for _, v in points]
    return np.interp(np.arange(ts[-1] + 1), ts, vs).astype(float)


# 前の山110・左肩112・頭118・右肩112.5、谷104・106・106.5（論文の5つの条件をすべて満たす）
TOP = [(0, 100), (10, 110), (15, 104), (20, 112), (25, 106), (30, 118), (35, 106.5), (40, 112.5), (50, 100)]


def test_constants_match_the_registration():
    assert L.MULTS == (1.00, 1.25, 1.50, 1.75, 2.00, 2.50, 3.00, 3.50, 4.00, 4.50)
    assert (L.ASYM, L.DEDUPE, L.RISK_ATR, L.EXIT, L.MIN_N, L.P_LIMIT) == (2.5, 2, 1.5, "X1", 300, 0.05)
    assert (L.START, L.WARMUP, L.SPLIT) == ("2006-01-01", 260, "2016-01-01")
    text = open(os.path.join(ROOT, "PILLAR_PREREG.md"), encoding="utf-8").read()
    assert "## C2 チャートパターン（三尊・逆三尊）" in text
    assert "1.00・1.25・1.50・1.75・2.00・2.50・3.00・3.50・4.00・4.50" in text and "2.5倍以下" in text


def test_zigzag_peaks_and_troughs_alternate_and_confirm_later():
    piv = L.zigzag(path(TOP), 0.03)
    kinds = [p[0] for p in piv]
    assert all(a != b for a, b in zip(kinds, kinds[1:]))
    peaks = [(p[1], p[2]) for p in piv if p[0] == 1]
    assert peaks == [(10, 110.0), (20, 112.0), (30, 118.0), (40, 112.5)]
    assert all(p[3] > p[1] for p in piv)                 # 確定は必ずあと
    assert [p for p in piv if p[1] == 40][0][3] == 43    # 112.5×0.97＝109.125 を下回った日


def test_head_and_shoulders_top_gives_a_sell_on_the_neckline_break():
    got = L.detect(path(TOP), CHI)
    assert got == [{"d": 45, "sign": 1, "step": 0}]      # ネックライン 106＋0.05×(日−25)・45日目の106.25で抜ける


def test_inverse_is_the_mirror_image():
    inv = [(t, 220 - v) for t, v in TOP]
    assert L.detect(path(inv), CHI) == [{"d": 45, "sign": -1, "step": 0}]


def test_no_look_ahead():
    c = path(TOP)
    assert L.detect(c[:46], CHI) == [{"d": 45, "sign": 1, "step": 0}]   # 45日目までで同じ合図
    assert L.detect(c[:45], CHI) == []


def test_condition2_needs_an_uptrend_before():
    pts = list(TOP)
    pts[1] = (10, 113)                                    # 前の山が左肩より高い
    assert L.detect(path(pts), CHI) == []


def test_condition4_rejects_lopsided_shapes():
    lop = [(0, 100), (10, 110), (15, 104), (20, 112), (35, 106), (50, 118), (54, 106.5), (58, 112.5), (70, 100)]
    assert L.detect(path(lop), CHI) == []                 # 左肩→頭30日・頭→右肩8日＝2.5倍を超える
    old = L.ASYM
    try:
        L.ASYM = 10.0
        assert len(L.detect(path(lop), CHI)) == 1         # 横の条件だけが落としていたことの確認
    finally:
        L.ASYM = old


def test_condition5_time_limit():
    late = TOP[:-1] + [(44, 108.5), (65, 108.5), (75, 100)]
    assert L.detect(path(late), CHI) == []                # 右肩40日・左肩20日＝60日までに抜けない


def test_overlapping_steps_are_counted_once():
    got = L.detect(path(TOP), [0.03, 0.031])
    assert got == [{"d": 45, "sign": 1, "step": 0}]


def test_sigma_is_std_of_daily_changes():
    c = np.array([100.0, 101.0, 99.99, 100.9899])
    r = np.diff(c) / c[:-1]
    assert abs(L.sigma_of(c) - np.std(r, ddof=1)) < 1e-12


def test_trade_short_hits_take_profit():
    n = 50                                                # 入る足から最長20本がそろう長さ
    o = np.full(n, 100.0)
    h, l, c = o + 0.5, o - 0.5, o.copy()
    o[21:], h[21:], l[21:], c[21:] = 100.0, 100.2, 97.0, 97.5    # 入った足で2ATR下に届く
    atr = np.full(n, 1.0)
    t = L.trade("TEST", o, h, l, c, atr, 20, -1)                 # −1＝売り
    assert t["reason"] == "利確" and abs(t["R"] - 2.0 / 1.5) < 1e-9    # 未知の銘柄は費用0
    assert abs(t["H10"] - (100.0 - 97.5) / 1.5) < 1e-9


def test_verdict_rules():
    good = {"n": 400, "mean": 0.10, "diff": 0.12}
    halves = {"前半": {"mean": 0.05, "diff": 0.08}, "後半": {"mean": 0.12, "diff": 0.15}}
    assert L.verdict(good, 0.01, halves) == "論文の三尊は残る"
    assert L.verdict(good, 0.20, halves) == "差なし"
    assert L.verdict({**good, "n": 299}, 0.01, halves) == "件数不足"
    assert L.verdict(good, 0.01, {**halves, "後半": {"mean": -0.01, "diff": 0.02}}) == "差なし"
    bad = {"n": 400, "mean": -0.20, "diff": -0.15}
    assert L.verdict(bad, 0.01, {"前半": {"mean": -0.1, "diff": -0.1}, "後半": {"mean": -0.3, "diff": -0.2}}) == "逆に効く"


def test_placebo_compares_within_ticker_side_and_half():
    rng = np.random.default_rng(1)
    pool = {("A", 1, "前半"): {"R": rng.normal(0, 1, 5000)}, ("A", -1, "前半"): {"R": rng.normal(-0.5, 1, 5000)}}
    same = [{"ticker": "A", "sign": 1, "dir": -1, "half": "前半", "R": -0.5, "date": "2010-01-05"} for _ in range(200)]
    assert abs(L.expected(same, pool) - (-0.5)) < 0.05
    assert L.placebo_p(same, pool, n_perm=500) > 0.5       # 売りが損をするだけなら差なし
    better = [dict(r, R=0.0) for r in same]
    assert L.placebo_p(better, pool, n_perm=500) < 0.01


def test_top_becomes_a_sell_and_bottom_a_buy_end_to_end():
    import pandas as pd
    lead = [(0, 80), (300, 100)]                          # 準備の260本より前に、なめらかな上昇
    body = [(300 + t, v) for t, v in TOP[1:]] + [(380, 100)]
    for pts, sign, way in ((lead + body, 1, -1), ([(t, 200 - v) for t, v in lead + body], -1, 1)):
        c = path(pts)
        idx = pd.bdate_range("2012-01-02", periods=len(c))
        df = pd.DataFrame({"Open": c, "High": c + 0.05, "Low": c - 0.05, "Close": c}, index=idx)
        rows, pool, info = L.ticker_rows("USDJPY=X", df)
        assert [(r["sign"], r["dir"]) for r in rows] == [(sign, way)]
        assert rows[0]["date"] == idx[346].date().isoformat()          # 合図の日＝345・入る＝次の足
        assert set(k[1] for k in pool) == {1, -1}                       # 偽薬は売り買いの両方の向きで持つ


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"ok   {name}")
            except Exception as e:  # noqa: BLE001
                fails += 1
                print(f"FAIL {name}: {type(e).__name__}: {e}")
    print(f"{'全部通った' if not fails else f'{fails}件 失敗'}")
    sys.exit(1 if fails else 0)
