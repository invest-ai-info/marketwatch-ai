# -*- coding: utf-8 -*-
"""J22 9:00〜9:30 に上がった銘柄と下がった銘柄、それぞれの法則（open30_lab.py）のテスト。2026-10-07 新設。

値動きはすべて作り物。確かめること＝①事前登録と定数の一致 ②前の日までの特徴（株価・値幅・52週安値）と5分足の値動きの形
③主と確かめの朝の分け方（5分足の期間の始まり）④判定とまとめ（法則・片方だけ・見えない・W1/W2 の続く／戻る）
⑤出力に銘柄コードを出さない・点検は損益を出さない ⑥ワークフローと SYNC 禁忌。

実行:  python tests/test_open30_lab.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import open30_lab as O  # noqa: E402
import test_highs_trap_lab as TL  # noqa: E402


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "## J22 9:00〜9:30 に上がった銘柄と下がった銘柄、それぞれの法則" in text
    assert (O.FIRST, O.LAST) == ("2023-10-10", "2026-10-05") and "2023-10-10〜2026-10-05" in text
    assert [k for k, *_ in O.FEATURES] == [f"F{i}" for i in range(1, 15)] and [k for k, *_ in O.WINDOWS] == ["W1", "W2"]
    assert O.N_Q == 16 and abs(O.ALPHA - 0.05 / 16) < 1e-12 and "p＜0.05÷16＝99.69％ の幅" in text
    assert O.MIN_STOCKS == 500 and O.HIGH_DAYS == 250 and O.W_FLAT == 0.003 and "±0.3％未満" in text
    for frag in ("300円未満", "1,000円以上", "10億円以上", "1億円未満", "8％以上", "3％未満", "5倍以上", "2倍未満", "±5％以内", "−15％以下"):
        assert frag in text, frag


def test_shape():
    op = 100.0
    bars = TL._5m("2026-08-03", [(100, 101, 99.5, 100.5), (100.5, 102, 100, 101.8), (101.8, 101.9, 100.2, 100.4),
                                 (100.4, 100.6, 99, 99.2), (99.2, 99.5, 98.8, 99), (99, 99.4, 98.9, 99.3), (99.3, 103, 99, 102)])
    r905, hi, lo, yt, yz = O.shape(bars, op)
    assert abs(r905 - 0.005) < 1e-12 and hi == 1 and lo == 4 and yt == 0 and yz == 0      # 9:30 の足（103）は入れない
    top = TL._5m("2026-08-03", [(100, 100, 98, 98.5)] + [(98.5, 99, 97, 98)] * 5)
    assert O.shape(top, 100.0)[3] == 1 and O.shape(top, 100.0)[1] == 0                    # 寄り天
    late = [(t + dt.timedelta(minutes=5), *x) for t, *x in bars]                           # 9:05 から始まる朝は数えない
    assert all(np.isnan(x) for x in O.shape(late, op)) and all(np.isnan(x) for x in O.shape([], op))


def test_stock_rows_features():
    days = TL._bdays("2022-09-01", 300)
    daily = [(d, 100.0, 101.0, 99.0, 100.0 + (i % 2) * 0.5, 1e6) for i, d in enumerate(days)]
    k = 290
    daily[k] = (days[k], 99.0, 100.0, 90.0, 92.0, 2e6)                                      # 52週安値を更新・値幅 10/92
    daily[k + 1] = (days[k + 1], 92.0, 93.0, 91.0, 92.5, 1e6)
    day = days[k + 1]
    m5 = {day: TL._5m(day, [(92, 92.5, 91.8, 92.4)] + [(92.4, 92.6, 92.0, 92.2)] * 6)}
    A = O.stock_rows(5, daily, m5, {})
    got = {dt.date.fromordinal(int(r[O.C["day"]])).isoformat(): r for r in A}
    r = got[day]
    assert r[O.C["new_low"]] == 1 and abs(r[O.C["range"]] - 10 / 92) < 1e-12 and r[O.C["price"]] == 92.0
    assert abs(r[O.C["r905"]] - (92.4 / 92 - 1)) < 1e-12 and abs(r[O.C["r930"]] - (92.2 / 92 - 1)) < 1e-12
    assert r[O.C["hi_slot"]] == 1 and r[O.C["lo_slot"]] == 0 and r[O.C["yorizoko"]] == 0
    assert got[days[k + 2]][O.C["new_low"]] == 0 and np.isnan(got[days[k + 2]][O.C["r905"]])  # 5分足の無い朝は形を数えない
    assert min(got) >= O.FIRST


def _rows(n_days, start, seed, main):
    """主の朝（main=True）は寄り→9:30 と最初の5分、確かめの朝は寄り→10:00 だけ"""
    rng = np.random.default_rng(seed)
    d0 = dt.date.fromisoformat(start)
    days = [d for d in (d0 + dt.timedelta(i) for i in range(n_days * 2)) if d.weekday() < 5][:n_days]
    out, n = [], 600
    for d in days:
        mg, mkt = rng.normal(0, 0.003), rng.normal(0, 0.003)
        gap = mg + rng.choice([0.0, 0.0, 0.015, -0.015], size=n)
        rp = rng.choice([0.0, 0.06, 0.01, -0.06], size=n)
        price = rng.choice([200.0, 500.0, 1500.0], size=n)
        tvr = rng.choice([1.0, 6.0], size=n)
        r905 = rng.choice([0.0, 0.015, -0.015], size=n)
        noise = rng.normal(0, 0.006, size=n)
        for c in range(n):
            e = mkt + noise[c] + (-0.006 if rp[c] >= 0.05 else 0)
            if main:
                e += 0.006 if price[c] < 300 else 0
                after = e + (0.004 if r905[c] >= 0.01 else 0)
                r930, r1000, f5 = (1 + r905[c]) * (1 + after) - 1, np.nan, r905[c]
            else:
                e += -0.006 if tvr[c] >= 5 else 0
                r930, r1000, f5 = np.nan, e, np.nan
            out.append((d.toordinal(), c, gap[c], rp[c], np.nan, r1000, r930, rng.choice([0.5, 5.0, 20.0]),
                        rng.choice([0.0, 0.2, -0.2]), tvr[c], rng.choice([0.1, 0.7]), rng.choice([0.0, 1.0]),
                        rng.choice([0.0, 1.0, np.nan]), rng.choice([0.0, 1.0]), price[c], rng.choice([0.02, 0.1]),
                        f5, rng.integers(0, 6) if main else np.nan, rng.integers(0, 6) if main else np.nan,
                        rng.choice([0.0, 1.0]) if main else np.nan, rng.choice([0.0, 1.0]) if main else np.nan))
    return np.array(out, float)


def test_samples_split():
    A = np.vstack([_rows(10, "2024-01-04", 1, False), _rows(8, "2026-07-01", 2, True)])
    A[:400, O.C["r930"]] = 0.001                                                            # 先頭の朝の 400銘柄だけ 5分足 → 始まりにしない
    main, conf, start = O.samples(A)
    assert dt.date.fromordinal(start).isoformat() == "2026-07-01" and main.sum() == 8 * 600
    assert conf.sum() == 10 * 600 and not (main & conf).any()


def test_analyze_judges_and_render():
    A = np.vstack([_rows(120, "2024-01-04", 3, False), _rows(40, "2026-07-01", 4, True)])
    res = O.analyze(A)
    s = res["summary"]
    assert s["F3"] == f"{O.LAW}：{O.DOWN}", (s["F3"], res["features"]["F3"]["main"], res["features"]["F3"]["conf"])
    assert s["F13"] == f"{O.MAIN_ONLY}：{O.UP}" and s["F7"] == f"{O.CONF_ONLY}：{O.DOWN}", (s["F13"], s["F7"])
    assert s["F8"] == O.NONE and s["F11"] == O.NONE
    assert s["W1"] == f"{O.SIGN_W}：続く" and s["W2"] == O.NONE, (s["W1"], s["W2"], res["windows"])
    assert res["sample"]["main_days"] == 40 and res["sample"]["conf_days"] == 120 and res["sample"]["start_5m"] == "2026-07-01"
    rd = res["reading"]
    f3 = rd["features"]["F3"]
    assert f3["yes"]["mean"] < f3["ref"]["mean"] and f3["in_down"] > f3["in_up"]
    assert abs(rd["overall"]["930"]["up"] + rd["overall"]["930"]["down"] + rd["overall"]["930"]["flat"] - 1) < 1e-9
    assert sum(rd["shape"]["up"]["hi_slot"]) == rd["shape"]["up"]["n"] and rd["shape"]["after905"]["up1"]["mean"] > rd["shape"]["after905"]["flat"]["mean"]
    assert sum(v["days"] for v in rd["morning"]["930"]["mkt_gap"].values()) == 40 and set(rd["morning"]["1000"]["weekday"]) == set("月火水木金")
    out = {"generated_at": "x", "prereg_sha256": "0" * 64, "result": dict(res, n_codes=600, list_date="2026-09-30", n_missing={}, n_dropped=0)}
    md = O.render_md(out)
    assert "## まとめ" in md and "F3 前の日 +5％以上" in md and "寄り天" in md and "続くか戻るか" in md and "投資助言ではありません" in md
    assert "下がりやすい特徴（同）**：F3" in md
    assert "計算できず" in O.render_md({"generated_at": "x", "prereg_sha256": "", "result": {"error": "e"}})


def test_check_summary_has_no_returns():
    A = np.vstack([_rows(5, "2024-01-04", 5, False), _rows(5, "2026-07-01", 6, True)])
    out = O.check_summary(A, {"daily": [], "h1": [], "m5": []}, 600, {"daily_range": "from:1990"})
    text = repr(out)
    assert not any(w in text for w in ("mean", "value", "diff", "up_share")) and set(out["sizes"]) == {f"F{i}" for i in range(1, 15)} | {"W1", "W2"}
    assert out["main"]["days"] == 5 and out["conf"]["days"] == 5


def test_workflow_and_sync_forbidden():
    wf = open(".github/workflows/open30-lab.yml", encoding="utf-8").read()
    assert "python -u open30_lab.py --check" in wf and "restore-keys: jp-bars-" in wf and "python tests/test_open30_lab.py" in wf
    assert "open30-lab.json open30-lab.md" in wf and "options: [check, run]" in wf
    assert '"open30-lab.json", "open30-lab.md"' in open("check_site_consistency.py", encoding="utf-8").read()


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
