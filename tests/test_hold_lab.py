# -*- coding: utf-8 -*-
"""R1 持ち方の研究（hold_lab.py）のテスト。作った値段で、売買・費用・税・持つ割合・偽薬・判定の決まりを確かめる。2026-10-05 新設。

実行:  python tests/test_hold_lab.py     （pytest 不要。pytest でも動く）
"""
import os
import re
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import hold_lab as H  # noqa: E402


def _days(n, start="2020-01-01"):
    return pd.date_range(start, periods=n, freq="D")


def _close(a, b, tol=1e-9):
    return abs(a - b) <= tol * max(1.0, abs(b))


# ── 売買と費用 ──

def test_hold_without_cost_or_tax_follows_price():
    p = np.array([100, 110, 90, 120, 150.0])
    s = H.simulate(p, _days(5), np.ones(5), np.zeros(5, bool), 0.0, 0.0, "btc")
    assert _close(s["final"], 1.5) and np.allclose(s["curve"], p / 100)
    assert s["trades"] == 0


def test_hold_pays_cost_once_in_and_once_out():
    c = 0.0015
    p = np.array([100, 200.0])
    s = H.simulate(p, _days(2), np.ones(2), np.zeros(2, bool), c, 0.0, "btc")
    assert _close(s["final"], 2 / (1 + c) * (1 - c)), s["final"]


def test_btc_liquidation_tax_on_gain():
    c, t = 0.0015, 0.30
    p = np.array([100, 300.0])
    s = H.simulate(p, _days(2), np.ones(2), np.zeros(2, bool), c, t, "btc")
    units = 1 / (100 * (1 + c))
    proceeds = units * 300 * (1 - c)
    assert _close(s["final"], proceeds - t * (proceeds - 1.0)), s["final"]


def test_year_end_tax_after_selling():
    # 2020/12/29 に100で買い、12/30 に200で売る（利益1.0）→ 年末 12/31 に30%＝0.3 を払う → 現金1.7
    d = pd.DatetimeIndex(["2020-12-29", "2020-12-30", "2020-12-31", "2021-01-01", "2021-01-02"])
    p = np.array([100, 200, 200, 200, 200.0])
    w = np.array([1, 0, 0, 0, 0.0])
    s = H.simulate(p, d, w, np.array([1, 1, 0, 0, 0], bool), 0.0, 0.30, "btc")
    assert _close(s["curve"][2], 1.7) and _close(s["final"], 1.7) and _close(s["taxes"], 0.3)


def test_forced_sale_to_pay_tax_is_grossed_up():
    # 利益1.0を出して全額買い直す → 年末の現金0 → 年末の値段250で売って税を払う。その売りの利益も同じ年に入る
    d = pd.DatetimeIndex(["2020-12-28", "2020-12-29", "2020-12-30", "2020-12-31", "2021-01-01"])
    p = np.array([100, 200, 200, 250, 250.0])
    w = np.array([1, 0, 1, 1, 1.0])
    s = H.simulate(p, d, w, np.array([1, 1, 1, 0, 0], bool), 0.0, 0.30, "btc")
    x = 0.3 / 235                        # x×250 = 0.3×(1 + x×(250−200))
    units_after = 0.01 - x
    assert _close(s["curve"][3], units_after * 250), (s["curve"][3], units_after * 250)
    # 税＝2020年末（1.0＋売りの利益 50x）＋2021年の最後の売り切り（残りの量×(250−200)）
    assert _close(s["taxes"], 0.3 * (1 + 50 * x) + 0.3 * units_after * 50), s["taxes"]


def test_index_loss_carries_forward_three_years_btc_does_not():
    tax, carry = H.year_tax(-1.0, [], 2020, "index", 0.2)
    assert tax == 0 and carry == [(2020, 1.0)]
    tax, carry = H.year_tax(1.5, carry, 2023, "index", 0.2)       # 3年後まで使える
    assert _close(tax, 0.1) and carry == []
    tax, _ = H.year_tax(1.5, [(2020, 1.0)], 2024, "index", 0.2)   # 4年後はもう使えない
    assert _close(tax, 0.3)
    tax, carry = H.year_tax(-1.0, [], 2020, "btc", 0.3)
    assert tax == 0 and carry == []


def test_losses_within_year_offset_gains():
    # 同じ年に +1.0 と −0.4 → 0.6 にだけ税
    d = pd.DatetimeIndex(["2020-12-26", "2020-12-27", "2020-12-28", "2020-12-29", "2020-12-31"])
    p = np.array([100, 200, 100, 60, 60.0])
    w = np.array([1, 0, 1, 0, 0.0])
    s = H.simulate(p, d, w, np.array([1, 1, 1, 1, 0], bool), 0.0, 0.30, "btc")
    assert _close(s["taxes"], 0.3 * (1.0 - 0.8)), s["taxes"]    # 2.0で買って1.2で売る＝−0.8


# ── 持つ割合 ──

def test_m200_uses_previous_close_and_trades_at_today_close():
    p = np.r_[np.full(200, 100.0), 120, 80, 80]
    w = H.m200_weights(p, 200)
    assert np.isnan(w[199]) and w[200] == 0.0       # 199日目までの平均は100、その日の終値100は平均より上ではない
    assert w[201] == 1.0                            # 200日目の終値120＞平均 → 次の日（201）に全額
    assert w[202] == 0.0                            # 201日目の終値80＜平均 → 202 に現金


def test_vt_is_set_at_month_end_and_applied_next_day_capped_at_one():
    d = pd.date_range("2020-01-01", "2020-06-30", freq="D")
    rng = np.random.default_rng(1)
    p = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, len(d))))
    w, ex = H.vt_weights(p, d, 0.40, 365)
    first = np.flatnonzero(ex)[0]
    assert d[first - 1].is_month_end and d[first].day == 1
    assert np.all(w[~np.isnan(w)] <= 1.0) and w[first] == 1.0     # 小さな値動き→割合は1で頭打ち
    w2, _ = H.vt_weights(p, d, 0.05, 365)
    nxt = np.flatnonzero(ex)[1]
    assert np.all(w2[first:nxt] == w2[first]) and w2[first] < 1.0


def test_shuffles_keep_counts():
    rng = np.random.default_rng(3)
    x = np.array([1, 1, 1, 0, 0, 1, 0, 0, 0, 0, 1, 1.0])
    y = H.shuffle_runs(x, rng)
    assert y.sum() == x.sum() and H.changes(y).sum() == H.changes(x).sum() and y[0] == x[0]
    w = np.array([0.5] * 3 + [0.8] * 4 + [1.0] * 2)
    ex = np.array([0, 0, 0, 1, 0, 0, 0, 1, 0], bool)
    z = H.shuffle_months(w, ex, rng)
    assert sorted(z[[0, 3, 7]]) == [0.5, 0.8, 1.0] and len(z) == len(w)


# ── 物差しと判定 ──

def test_metrics_basics():
    c = np.array([1.0, 1.2, 0.9, 1.3, 1.0, 1.4])
    assert _close(H.max_dd(c), 0.9 / 1.2 - 1)
    d = _days(6)
    assert H.longest_underwater(c, d) == 2


def test_verdict_rules():
    allok = dict.fromkeys("abcde", True)
    assert H.verdict(allok, 0.001) == "◎ 確認"
    assert H.verdict({**allok, "d": False, "e": False}, 0.03) == "◯ 傾向"
    assert H.verdict({**allok, "a": False, "d": False, "e": False}, 0.30) == "△ 守りだけ"
    assert H.verdict({**allok, "a": False, "d": False, "e": False}, 0.03) == "✕"
    assert H.verdict({**allok, "b": False, "d": False, "e": False}, 0.30) == "✕"


def test_bootstrap_identical_series_gives_p_one():
    rng = np.random.default_rng(5)
    d = _days(400)
    p = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, 400)))
    s = H.simulate(p, d, np.ones(400), np.zeros(400, bool), 0.0, 0.0, "btc")
    assert H.boot_p(s, s, d, np.random.default_rng(1), n_boot=200) == 1.0


def test_evaluate_end_to_end_on_made_up_prices():
    rng = np.random.default_rng(7)
    d = pd.bdate_range("2010-01-01", periods=1500)
    px = pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0003, 0.012, len(d)))), index=d)
    r = H.evaluate(px, H.ASSETS["SP500"], n_boot=50, n_placebo=20)
    assert set(r["results"]) == {"H", "M200", "VT", "M200VT"}
    for m in H.METHODS:
        x = r["results"][m]
        assert x["verdict"] in H.VERDICTS and 0 < x["p_boot"] <= 1 and 0 < x["p_placebo"] <= 1
        assert set(x["near_calmar"]) and set(x["checks"]) == set("abcde")
    assert r["info"]["eval_start"] == str(d[H.WARMUP].date())
    md = H.render_md({"generated_jst": "x", "prereg_sha256": "y", "missing": [], "sources": {"SP500": "test"},
                      "assets": {"SP500": r}})
    assert "R1 持ち方の研究" in md and "円" not in md.split("## 読み方")[0].replace("円建て", "")


def test_missing_data_counts_nothing():
    md = H.render_md({"generated_jst": "x", "prereg_sha256": "y", "missing": ["NIFTY"], "sources": {}, "assets": {}})
    assert "何も数えていない" in md


def test_constants_match_preregistration():
    txt = open(os.path.join(ROOT, "PILLAR_PREREG.md"), encoding="utf-8").read()
    sec = txt.split("## R1 持ち方の研究", 1)[1].split("\n## ", 1)[0]
    assert "0.05÷12" in sec and H.ALPHA == 0.05 / 12 and H.N_COMPARE == 12
    assert "2,000回" in sec and H.N_BOOT == 2000 and "平均60日" in sec and H.BLOCK == 60
    assert "1,000回" in sec and H.N_PLACEBO == 1000
    assert "0.75倍以下" in sec and H.DD_RATIO == 0.75
    assert "BTC 0.15%" in sec and H.ASSETS["BTC"]["cost"] == 0.0015
    assert "株価指数 0.05%" in sec and all(H.ASSETS[a]["cost"] == 0.0005 for a in ("SP500", "TOPIX", "NIFTY"))
    assert "**30%**" in sec and H.ASSETS["BTC"]["tax"] == 0.30
    assert "**20.315%**" in sec and H.ASSETS["SP500"]["tax"] == 0.20315
    assert "BTC 40%" in sec and H.ASSETS["BTC"]["vt_target"] == 0.40
    assert "株価指数 12%" in sec and H.ASSETS["TOPIX"]["vt_target"] == 0.12
    assert "最初の260日" in sec and H.WARMUP == 260
    assert "過去60日" in sec and H.VOL_WIN == 60
    assert re.search(r"150日・250日", sec) and H.SMA_NEAR == (150, 250)
    assert "0.75倍・1.25倍" in sec and H.VT_NEAR == (0.75, 1.25)
    assert "3年繰り越す" in sec and H.CARRY_YEARS == 3


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
