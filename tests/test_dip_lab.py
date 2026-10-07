# -*- coding: utf-8 -*-
"""J23 寄りのあとに急落した株は、何％下がったところで反転するか（dip_lab.py）のテスト。2026-10-07 新設。

値動きはすべて作り物。確かめること＝①事前登録と定数の一致 ②窓の安値（寄り値より上にしない）と出口・指値の付き方（寄りで買えた／0.2％下まで付いた／ぴったりは買えない）
③1銘柄の行（前日の終値で割った値・費用の見積もり）④判定とまとめ（両方で上・両方で下）・反転した株の底・深さごとの戻り方
⑤出力に銘柄コードを出さない・点検は損益を出さない ⑥ワークフローと SYNC 禁忌。

実行:  python tests/test_dip_lab.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import dip_lab as D  # noqa: E402
import test_highs_trap_lab as TL  # noqa: E402


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "## J23 寄りのあとに急落した株は、何％下がったところで反転するか" in text
    assert D.LEVELS == (0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.10, 0.15)
    assert "**−2％・−3％・−4％・−5％・−6％・−8％・−10％・−15％**" in text
    assert D.THROUGH == 0.002 and "0.2％以上下まで付いたら指値で買えた" in text
    assert D.N_Q == 8 and abs(D.ALPHA - 0.05 / 8) < 1e-12 and "p＜0.05÷8＝99.375％ の幅" in text
    assert (D.REV_DEPTH, D.REV_BOUNCE, D.NEAR_LOW, D.MKT_DOWN) == (-0.03, 0.03, 0.005, -0.015)
    assert "−3〜−4・−4〜−5・−5〜−7・−7〜−10・−10〜−15・−15％以下" in text and len(D.BANDS) == 6
    assert (D.FIRST, D.LAST, D.NEW_FROM) == ("2016-11-01", "2026-10-05", "2023-10-10")


def test_windows_and_limit_fills():
    bars = TL._5m("2026-08-03", [(100, 100.5, 97, 98), (98, 99, 96.5, 97), (97, 102, 96.8, 101), (101, 101, 99, 100),
                                 (100, 100, 99, 99.5), (99.5, 100, 99, 99.8), (99.8, 100, 90, 91)])
    assert D.window_5m(bars, 100.0) == (96.5, 1.0)                                         # 9:30 の足（90）は入れない
    assert D.window_5m(TL._5m("2026-08-03", [(101, 102, 100.5, 101)]), 100.0) == (100.0, 0.0)  # 寄り値が窓の安値
    assert np.isnan(D.window_5m([], 100.0)[0])
    h1 = TL._1h("2026-08-03", [(9, 100, 97), (10, 97, 99)])
    assert D.window_1h(h1) == (97, 97) and np.isnan(D.window_1h(TL._1h("2026-08-03", [(10, 97, 99)]))[0])
    A = np.full((5, len(D.COLS)), np.nan)
    A[:, D.C["op_r"]] = [0.94, 1.00, 1.00, 1.00, 0.99]
    A[:, D.C["lo930_r"]] = [0.93, 0.95 * 0.998, 0.95, 0.96, 0.949]
    A[:, D.C["p930_r"]] = [0.97, 0.97, 0.97, 0.97, np.nan]
    ret, at_open = D.limit_trades(A, 0.05, "lo930_r", "p930_r")
    assert abs(ret[0] - (0.97 / 0.94 - 1)) < 1e-12 and at_open[0]                        # 寄りで買えた（寄り値で）
    assert abs(ret[1] - (0.97 / 0.95 - 1)) < 1e-12 and not at_open[1]                    # 0.2％下まで付いた
    assert np.isnan(ret[2]) and np.isnan(ret[3]) and np.isnan(ret[4])                      # ぴったり・届かない・出口なし


def test_stock_rows():
    days = TL._bdays("2026-04-01", 100)
    daily = [(d, 100.0, 101.0, 99.0, 100.0 + (i % 3) * 0.2, 1e5) for i, d in enumerate(days)]
    k = 95
    day, pc = days[k], daily[k - 1][4]
    daily[k] = (day, 98.0, 99.5, 93.0, 99.0, 2e5)
    m5 = {day: TL._5m(day, [(98, 98.5, 95, 95.5), (95.5, 96, 94, 94.5), (94.5, 97, 94.2, 96.8)] + [(96.8, 97.5, 96.5, 97.2)] * 4)}
    h1 = {day: TL._1h(day, [(9, 98, 98.6), (10, 98.6, 99)])}
    h1[day][0] = (h1[day][0][0], 98.0, 99.0, 93.5, 98.6, 100.0)
    A = D.stock_rows(3, daily, m5, h1)
    got = {dt.date.fromordinal(int(r[D.C["day"]])).isoformat(): r for r in A}
    r = got[day]
    assert abs(r[D.C["op_r"]] - 98 / pc) < 1e-12 and abs(r[D.C["lo930_r"]] - 94 / pc) < 1e-12 and r[D.C["lo_slot"]] == 1
    assert abs(r[D.C["p930_r"]] - 97.2 / pc) < 1e-12 and abs(r[D.C["lo1000_r"]] - 93.5 / pc) < 1e-12 and abs(r[D.C["p1000_r"]] - 98.6 / pc) < 1e-12
    assert abs(r[D.C["loday_r"]] - 93 / pc) < 1e-12 and abs(r[D.C["close_r"]] - 99 / pc) < 1e-12 and np.isfinite(r[D.C["spread"]])
    other = got[days[k + 1]]
    assert np.isnan(other[D.C["lo930_r"]]) and np.isnan(other[D.C["lo1000_r"]]) and np.isfinite(other[D.C["loday_r"]])


def _rows(n_days, start, seed, kind):
    rng = np.random.default_rng(seed)
    d0 = dt.date.fromisoformat(start)
    days = [d for d in (d0 + dt.timedelta(i) for i in range(n_days * 2)) if d.weekday() < 5][:n_days]
    lo_col, ex_col = {"main": ("lo930_r", "p930_r"), "conf": ("lo1000_r", "p1000_r"), "long": ("loday_r", "close_r")}[kind]
    out = []
    for d in days:
        n = 600
        lo = 1 - 0.2 * rng.uniform(0, 1, n) ** 2
        op = np.maximum(1 + rng.normal(0, 0.005, n), lo)
        ex = np.where(lo <= 0.94, 0.98, lo + 0.001) + rng.normal(0, 0.005, n) + rng.normal(0, 0.002)
        for c in range(n):
            row = np.full(len(D.COLS), np.nan)
            row[D.C["day"]], row[D.C["code"]], row[D.C["turnover"]] = d.toordinal(), c, rng.choice([0.5, 20.0])
            row[D.C["spread"]], row[D.C["op_r"]] = 0.002, op[c]
            row[D.C[lo_col]], row[D.C[ex_col]] = lo[c], ex[c]
            if kind == "main":
                row[D.C["lo_slot"]] = rng.integers(0, 6)
            out.append(row)
    return np.array(out)


def test_analyze_judges_and_reading():
    A = np.vstack([_rows(40, "2026-08-10", 1, "main"), _rows(120, "2024-11-01", 2, "conf"), _rows(30, "2018-03-01", 3, "long")])
    res = D.analyze(A)
    s = res["summary"]
    assert s["0.08"] == D.BOTH_UP and s["0.10"] == D.BOTH_UP, (s, res["judge"]["0.08"])
    assert s["0.02"] == D.BOTH_DOWN, s["0.02"]                                          # 浅い指値は戻らない株を多く拾う
    assert res["sample"]["start_5m"] == "2026-08-10" and res["sample"]["main"]["days"] == 40 and res["sample"]["conf"]["days"] == 120
    assert res["sample"]["long"]["days"] == 30
    rv = res["reading"]["main"]["reversal"]
    assert rv["depth_q"][4] <= -0.06 + 1e-9 and sum(rv["slot"]) == rv["n_rev"] and sum(rv["rev_by_band"].values()) == rv["n_rev"]
    assert rv["bands"]["−3〜−4％"]["bounce3"] < 0.05 and rv["bands"]["−7〜−10％"]["bounce3"] > 0.95
    lt = res["reading"]["conf"]["limits"]["levels"]["0.05"]
    assert lt["mkt_down"]["n"] + lt["mkt_other"]["n"] == lt["all"]["n"] == lt["big"]["n"] + lt["small"]["n"] == lt["at_open"]["n"] + lt["intra"]["n"]
    assert "slot" not in res["reading"]["long"]["reversal"]
    out = {"generated_at": "x", "prereg_sha256": "0" * 64, "result": dict(res, n_codes=600, list_date="2026-09-30", n_missing={}, n_dropped=0)}
    md = D.render_md(out)
    assert "## まとめ" in md and "前日比 −8％" in md and "反転した株の底" in md and "深さごとの戻り方" in md and "投資助言ではありません" in md
    assert D.BOTH_UP in md and D.BOTH_DOWN in md
    assert "計算できず" in D.render_md({"generated_at": "x", "prereg_sha256": "", "result": {"error": "e"}})


def test_day_median():
    u, med = D.day_median(np.array([2.0, 1.0, 2.0, 1.0, 2.0]), np.array([5.0, 1.0, 3.0, 3.0, 4.0]))
    assert list(u) == [1.0, 2.0] and list(med) == [2.0, 4.0]


def test_check_summary_has_no_returns():
    A = np.vstack([_rows(5, "2026-08-10", 4, "main"), _rows(5, "2024-11-01", 5, "conf")])
    out = D.check_summary(A, {"daily": [], "h1": [], "m5": []}, 600, {"daily_range": "from:1990"})
    text = repr(out)
    assert not any(w in text for w in ("mean", "'win'", "value", "bounce", "gross")) and out["windows"]["main"]["days"] == 5
    assert set(out["windows"]["conf"]["fills_and_at_open"]) == {f"{x:.2f}" for x in D.LEVELS}


def test_workflow_and_sync_forbidden():
    wf = open(".github/workflows/dip-lab.yml", encoding="utf-8").read()
    assert "python -u dip_lab.py --check" in wf and "restore-keys: jp-bars-" in wf and "python tests/test_dip_lab.py" in wf
    assert "dip-lab.json dip-lab.md" in wf and "options: [check, run]" in wf
    assert '"dip-lab.json", "dip-lab.md"' in open("check_site_consistency.py", encoding="utf-8").read()


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
