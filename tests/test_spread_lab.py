# -*- coding: utf-8 -*-
"""J28 売り買いの差の見積もりを日足と5分足で比べる（spread_lab.py）のテスト。2026-10-07 夜 新設。

値動きはすべて作り物。確かめること＝①事前登録と定数の一致 ②5分足の組（同じ日の中・続いた足だけ・出来高0の足を使わない・
9:00〜9:25）③作り物の売り買いの差 s を見積もりが取り戻す ④まとめと前もって決めた線（半分以下）
⑤点検は見積もりを出さない・出力に銘柄コードを出さない ⑥ワークフローと SYNC 禁忌。

実行:  python tests/test_spread_lab.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import spread_lab as L  # noqa: E402

JST = dt.timezone(dt.timedelta(hours=9))


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "## J28 売り買いの差（費用）の見積もりを、日足と5分足で比べる（損益は数えない）" in text
    assert (L.MIN_PAIRS_ALL, L.MIN_PAIRS_OPEN, L.HALF, L.TV_DAYS) == (200, 60, 0.5, 20)
    assert "200組以上ある銘柄だけ" in text and "60組以上ある銘柄だけ" in text and "中央値の**半分以下**" in text


def _sim(s, days=40, per_bar=20, vol=0.002, seed=1, start=(9, 0), n_bars=60):
    """真ん中の値が動き、取引は真ん中 ± s/2 で付く作り物の5分足"""
    rng = np.random.default_rng(seed)
    by, mid = {}, 100.0
    d0 = dt.date(2026, 8, 3)
    for k in range(days):
        day = d0 + dt.timedelta(days=k)
        t = dt.datetime.combine(day, dt.time(*start), JST)
        bars = []
        for j in range(n_bars):
            px = []
            for _ in range(per_bar):
                mid *= np.exp(rng.normal(0, vol / np.sqrt(per_bar)))
                px.append(mid * (1 + s / 2 * rng.choice([-1, 1])))
            bars.append((t + dt.timedelta(minutes=5 * j), px[0], max(px), min(px), px[-1], 100))
        by[day.isoformat()] = bars
    return by


def test_pairs_rules():
    t = dt.datetime(2026, 8, 3, 9, 0, tzinfo=JST)
    b = lambda m, v=100: (t + dt.timedelta(minutes=m), 100, 101, 99, 100.5, v)  # noqa: E731
    by = {"2026-08-03": [b(0), b(5), b(10, v=0), b(15), b(25), b(30)], "2026-08-04": [(t + dt.timedelta(days=1), 100, 101, 99, 100, 100)]}
    assert len(L.m5_pairs(by)) == 2                        # 0-5 と 25-30 だけ（出来高0・5分でない間・日をまたぐ組は使わない）
    assert len(L.m5_pairs(by, open_only=True)) == 1        # 9:25-9:30 の組は 9:30 の足を含むので入れない


def test_estimate_recovers_the_made_up_spread():
    for s in (0.001, 0.003, 0.006):
        by = _sim(s)
        assert abs(L.estimate(L.m5_pairs(by), L.MIN_PAIRS_ALL) / s - 1) < 0.15
        assert abs(L.estimate(L.m5_pairs(by, open_only=True), L.MIN_PAIRS_OPEN) / s - 1) < 0.15
    assert L.estimate(L.m5_pairs(_sim(0.003, days=3)), L.MIN_PAIRS_ALL) is None      # 組が足りない（3日×59組）


def _daily(n=80, vol=0.03, seed=2, tv=1e8):
    rng = np.random.default_rng(seed)
    out, c = [], 1000.0
    d0 = dt.date(2026, 5, 1)
    for i in range(n):
        o = c * (1 + rng.normal(0, vol / 3))
        c2 = o * (1 + rng.normal(0, vol))
        out.append(((d0 + dt.timedelta(days=i)).isoformat(), o, max(o, c2) * (1 + abs(rng.normal(0, vol / 2))),
                    min(o, c2) * (1 - abs(rng.normal(0, vol / 2))), c2, tv / c2))
    return out


def test_stock_row_and_summary_verdict():
    import cost_recount_lab as CR
    daily = _daily(tv=20e8)                                  # 1日 20億円
    row = L.stock_row(daily, _sim(0.001))
    assert abs(row["daily"] - CR.ar_spread_avg(daily)[daily[-1][0]]) < 1e-15 and abs(row["turnover"] - 20.0) < 1e-6
    assert row["m5_open"] is not None and row["pairs_open"] == 200
    rows = [dict(row) for _ in range(5)]
    sm = L.summarize(rows)
    big = sm["paired"]["10億円以上"]
    assert big["n"] == 5 and abs(big["ratio"] - row["m5_open"] / row["daily"]) < 1e-12
    assert sm["verdict"] == (L.HEAVY if big["ratio"] <= 0.5 else L.OK)
    heavy = [dict(row, daily=0.004, m5_open=0.0015) for _ in range(3)]
    light = [dict(row, daily=0.004, m5_open=0.0030) for _ in range(3)]
    assert L.summarize(heavy)["verdict"] == L.HEAVY and L.summarize(light)["verdict"] == L.OK
    assert L.summarize([dict(row, turnover=0.5)])["verdict"] is None              # 大きい株がいなければ判断しない


def test_render_and_check_have_no_codes_or_estimates():
    rows = [L.stock_row(_daily(tv=20e8, seed=s), _sim(0.002, seed=s)) for s in range(3)]
    md = L.render_md({"generated_at": "x", "prereg_sha256": "0" * 64, "result": {"summary": L.summarize(rows), "stocks": 3}})
    assert "## まとめ" in md and "9:00〜9:30 ÷ 日足" in md and "投資助言ではありません" in md
    assert "計算できず" in L.render_md({"generated_at": "x", "result": {"error": "e"}})
    out = L.check_summary(rows, {"daily": 0, "m5": 0}, 3, None)
    assert out["stocks"] == 3 and out["with"]["m5_open"] == 3 and not any(k in repr(out) for k in ("'daily': 0.", "m5_open': 0."))


def test_workflow_and_sync_forbidden():
    wf = open(".github/workflows/spread-lab.yml", encoding="utf-8").read()
    assert "python -u spread_lab.py --check" in wf and "restore-keys: jp-bars-" in wf
    assert "python tests/test_spread_lab.py" in wf and "spread-lab.json spread-lab.md" in wf and "options: [check, run]" in wf
    assert '"spread-lab.json", "spread-lab.md"' in open("check_site_consistency.py", encoding="utf-8").read()


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
