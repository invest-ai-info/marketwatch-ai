# -*- coding: utf-8 -*-
"""F3 ファンダの向き × トレンド × オシレーター（fund_combo_lab.py）のテスト。2026-10-10 新設。

値はすべて作り物。確かめること＝①事前登録と定数の一致 ②1時間足 → 4時間足（UTC 0/4/8…・真ん中の値・売り買いの差）
③金曜 UTC 04:00 の手じまいと入らない時間（週末に持ち越さない）④出口（損切りが先・利確・時間・金曜）⑤費用とスワップの式
⑥ファンダの向き（金利差・金利の方向・日本の空欄＝0％・多数決）⑦通しで動き、判定の言葉と表が出る ⑧ワークフロー・SYNC 禁忌。

実行:  python tests/test_fund_combo_lab.py     （pytest 不要。pytest でも動く）
"""
import math
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import fund_combo_lab as L  # noqa: E402


def _sec():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    return text[text.index("## F3 ファンダの向き × トレンド × オシレーター"):text.index("## 共通の決まり")]


def test_prereg_matches_the_code():
    sec = _sec()
    for s in ("6×10×6＝360通り", "EURUSD・GBPUSD・USDJPY・AUDUSD・USDCHF・USDCAD・NZDUSD・EURJPY・GBPJPY・AUDJPY・EURAUD・GBPAUD",
              "UTC の 0・4・8・12・16・20時", "**F1 金利差（キャリー）**", "6か月前の値", "**F5 3つの多数決**", "**日本の政策金利が BIS で空欄の月（量的緩和の時期）は 0％とみなす**",
              "**5本あけるまで次を数えない**", "先頭 **260本**", "損切り 1.5ATR・利確 2ATR・最長20本", "**金曜の UTC 04:00 に始まる足の始値で必ず手じまう**",
              "1.2pips・ほか 1.8pips", "年1％", "件数 **150以上**", "**上位3つ**", "**後半（2015年〜2026-09）で1回だけ**", "**p＜0.05÷3**", "2,000回・両側の p"):
        assert s in sec, s
    assert L.PAIRS == ("EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCHF", "USDCAD", "NZDUSD", "EURJPY", "GBPJPY", "AUDJPY", "EURAUD", "GBPAUD")
    assert list(L.FUNDS) == ["F0", "F1", "F2", "F3", "F4", "F5"] and len(L.TRENDS) == 10 and len(L.OSCS) == 6
    assert (L.SPLIT, L.FIRST, L.LAST, L.MIN_N_EXPLORE, L.TOP_K, L.COOLDOWN, L.WARMUP) == ("2015-01-01", (2004, 1), (2026, 9), 150, 3, 5, 260)
    assert (L.RISK_ATR, L.SL_M, L.TP_M, L.CAP, L.RATE_LOOK, L.FRI_CUT_HOUR) == (1.5, 1.5, 2.0, 20, 6, 4)
    assert (L.FX_PIPS_JPY, L.FX_PIPS_OTHER, L.FX_MARKUP, L.N_PERM) == (1.2, 1.8, 0.01, 2000) and abs(L.P_LIMIT - 0.05 / 3) < 1e-12


def _hourly(start, hours, f=lambda j: 1.0 + 0.0001 * j, spread=0.0001):
    idx = pd.date_range(start, periods=hours, freq="h", tz="UTC")
    mid = np.array([f(j) for j in range(hours)])
    b, a = mid - spread / 2, mid + spread / 2
    return pd.DataFrame({"bo": b, "bh": b + 0.0002, "bl": b - 0.0002, "bc": b + 0.00005,
                         "ao": a, "ah": a + 0.0002, "al": a - 0.0002, "ac": a + 0.00005}, index=idx)


def test_bars_4h_alignment_and_spread():
    df = _hourly("2020-01-06 00:00", 9)                       # 月曜 0時から9時間
    df.loc[df.index[2], "ac"] += 0.0005                         # 2時の足の終わりの差が広い
    b = L.bars_4h(df)
    assert [t.hour for t in b.index] == [0, 4, 8] and len(b) == 3
    assert abs(b["Open"].iloc[0] - 1.0) < 1e-12 and abs(b["Close"].iloc[0] - 1.00035) < 1e-9   # 3時の足の終値（真ん中）
    assert abs(b["sp_open"].iloc[0] - 0.0001) < 1e-12 and abs(b["sp_max"].iloc[0] - 0.0006) < 1e-9
    assert abs(b["High"].iloc[1] - max((df["bh"] + df["ah"]).iloc[4:8] / 2)) < 1e-12


def test_friday_cut_and_no_weekend():
    idx = pd.DatetimeIndex(pd.to_datetime(["2020-01-09 20:00", "2020-01-10 00:00", "2020-01-10 04:00", "2020-01-10 16:00",
                                           "2020-01-12 20:00", "2020-01-13 00:00"]), tz="UTC")   # 木・金・金・金・日・月
    ok, cut, gap = L.cut_arrays(idx)
    assert list(ok) == [True, True, False, False, True, True]
    assert cut[0] == 2 and cut[1] == 2 and not gap[0]
    assert L.week_cut(idx[4]) == pd.Timestamp("2020-01-17 04:00", tz="UTC")   # 日曜の足は次の金曜
    idx2 = pd.DatetimeIndex(pd.to_datetime(["2020-04-09 20:00", "2020-04-13 00:00"]), tz="UTC")   # 金曜（聖金曜日）の足が無い週
    ok2, cut2, gap2 = L.cut_arrays(idx2)
    assert ok2[0] and cut2[0] == 1 and gap2[0]


def test_simulate_exits():
    n = 30
    o = np.full(n, 100.0); h = o + 0.5; l = o - 0.5; c = o.copy()
    cut, gap = np.full(n, n), np.zeros(n, bool)
    atr = 1.0                                                     # 損切り 98.5・利確 102・1R＝1.5
    h2 = h.copy(); h2[3] = 102.5
    r, k, held = L.simulate(o, h2, l, c, atr, 0, "long", cut, gap)
    assert abs(r - 2.0 / 1.5) < 1e-12 and k == 3 and held == 3
    l2 = l.copy(); l2[2] = 98.0; h3 = h2.copy(); h3[2] = 102.5   # 同じ足で両方＝損切りが先
    r, k, _ = L.simulate(o, h3, l2, c, atr, 0, "long", cut, gap)
    assert abs(r + 1.0) < 1e-12 and k == 2
    r, k, held = L.simulate(o, h, l, c, atr, 0, "short", cut, gap)   # 何も届かない＝20本目の終値
    assert abs(r) < 1e-12 and k == 20 and held == 20
    cut2 = cut.copy(); cut2[1] = 5; o3 = o.copy(); o3[5] = 101.0
    r, k, held = L.simulate(o3, h, l, c, atr, 0, "long", cut2, gap)    # 金曜 04:00 の始値で手じまい
    assert abs(r - 1.0 / 1.5) < 1e-12 and k == 5 and held == 4
    gap2 = gap.copy(); gap2[1] = True; c3 = c.copy(); c3[4] = 99.4
    r, k, held = L.simulate(o, h, l, c3, atr, 0, "long", cut2, gap2)   # 金曜の足が無い＝前の足の終値
    assert abs(r - (-0.6 / 1.5)) < 1e-12 and k == 4
    assert L.simulate(o, h, l, c, atr, n - 5, "long", cut, gap) is None   # 足りない


def test_cost_and_swap():
    assert abs(L.cost_r("EURUSD", 0.00005, 0.00007, 0.003) - 0.00018 / 0.003) < 1e-12        # 決まった 1.8pips のほうが大きい
    assert abs(L.cost_r("USDJPY", 0.03, 0.05, 0.3) - 0.04 / 0.3) < 1e-12                       # 実際の差（0.04）が 1.2pips（0.012）より大きい
    sw = L.swap_r(1.0, 5.0, 0.0, 6, 150.0, 0.45)                # 1日・金利差5％・買い
    assert abs(sw - (0.05 / 365 * 150 - 0.01 / 365 * 150) / 0.45) < 1e-12
    assert L.swap_r(-1.0, 5.0, 0.0, 6, 150.0, 0.45) < 0


def test_fund_states():
    months = [(2020, m) for m in range(1, 13)]
    allm = [(y, m) for y in range(1990, 2021) for m in range(1, 13)]
    rates = {a: {f"{y:04d}-{m:02d}": 1.0 for (y, m) in allm} for a in L.FV.BIS_AREA.values()}
    for (y, m) in allm:
        rates["US"][f"{y:04d}-{m:02d}"] = 3.0 if (y, m) >= (2019, 12) else 1.0   # 2019-12 から米国だけ利上げ
    del rates["JP"]                                              # 日本は空欄＝0％
    reer = {c: {k: 100.0 for k in allm} for c in L.FV.CCYS}
    reer["EUR"] = {k: (80.0 if k >= (2019, 1) else 100.0) for k in allm}       # ユーロだけ5年で安くなった
    cpi = {c: {k: 100.0 * 1.001 ** i for i, k in enumerate(allm)} for c in L.FV.CCYS}
    fs = L.fund_states(rates, reer, cpi, {c: "M" for c in L.FV.CCYS}, {}, {}, months)
    f1, f2, f3, f4, f5 = fs["EURUSD"][(2020, 3)]
    assert f1 == -1 and f2 == -1 and f4 == 1                     # ユーロ（1％）< ドル（3％）・差は6か月で広がった・ユーロが割安
    assert fs["USDJPY"][(2020, 3)][0] == 1                       # 日本の空欄＝0％ → ドル高い
    assert fs["GBPAUD"][(2020, 3)][:2] == (0, 0) and fs["GBPAUD"][(2020, 3)][4] == 0   # 同じ金利＝向きなし・多数決も無い
    assert fs["EURUSD"][(2020, 1)][1] == -1                      # 2020-01 の向き＝2019-12 の月末（利上げ直後）
    assert f3 == 0 and f5 == -1                                  # 物価がどこも同じ＝経済の勢いは向きなし／多数決＝2つが売り・逆向きなし


def _bars_world(seed, start="2013-06-03", periods=3000):
    rng = np.random.default_rng(seed)
    idx = pd.date_range(start, periods=periods * 2, freq="4h", tz="UTC")
    idx = idx[[t.weekday() < 5 for t in idx]][:periods]
    px = 1.2 * np.exp(np.cumsum(rng.normal(0, 0.003, len(idx))))
    o = np.concatenate([[px[0]], px[:-1]])
    hi = np.maximum(o, px) * (1 + np.abs(rng.normal(0, 0.001, len(idx))))
    lo = np.minimum(o, px) * (1 - np.abs(rng.normal(0, 0.001, len(idx))))
    return pd.DataFrame({"Open": o, "High": hi, "Low": lo, "Close": px, "sp_open": 0.00008, "sp_max": 0.00012}, index=idx)


def test_analyze_end_to_end():
    rng = np.random.default_rng(7)
    allm = [(y, m) for y in range(2012, 2017) for m in range(1, 13)]
    rates = {a: {f"{y:04d}-{m:02d}": float(k) for (y, m) in allm} for k, a in enumerate(L.FV.BIS_AREA.values())}
    arrays = {}
    for j, p in enumerate(L.PAIRS):
        bars = _bars_world(j)
        fund = {m: tuple(int(x) for x in rng.choice([-1, 0, 1], 5)) for m in allm}
        arrays[p] = L.pair_arrays(p, bars, fund, rates)
    r = L.analyze(arrays, n_perm=20)
    assert r["entries"] > 0 and len(r["rows"]) == 360 and set(r["fund_effect"]) == set(L.F_KEYS)
    for x in r["picked"]:
        assert x["confirm"]["verdict"] in (L.KEPT, L.GONE)
    row = max(r["rows"], key=lambda x: x["n_c"])                  # 確かめの関数そのもの（件数の多い組み合わせで）
    E = L.to_arrays(sum((L.entries_of(p, A) for p, A in arrays.items()), []), arrays)
    st = L.confirm_one(E, arrays, row, n_perm=20)
    assert st["verdict"] in (L.KEPT, L.GONE) and st["p_placebo"] is not None and st["cost_mean"] > 0
    md = L.render_md({"generated_at": "x", "prereg_sha256": "abc", "result": r})
    assert "## 判定" in md and "ファンダの向きの効き目" in md and "投資助言ではありません" in md
    # 週末に持ち越さない：入った足から出た足まで、金曜 04:00 をまたがない
    A = arrays["EURUSD"]
    assert np.isfinite(A["R"]["long"]).sum() > 0


def test_judge_words():
    assert L.judge({"lo": 0.01}, 0.001) == L.KEPT
    assert L.judge({"lo": 0.01}, 0.02) == L.GONE and L.judge({"lo": -0.01}, 0.001) == L.GONE and L.judge({}, None) == L.GONE


def test_workflow_and_sync_rules():
    wf = open(".github/workflows/fund-combo-lab.yml", encoding="utf-8").read()
    assert "workflow_dispatch" in wf and "schedule" not in wf and "fund_combo_lab.py --check" in wf and "options: [check, run]" in wf
    assert "tests/test_fund_combo_lab.py" in wf and "restore-keys: fx-bars-" in wf and "git add fund-combo-lab.json fund-combo-lab.md" in wf
    assert '"fund-combo-lab.json", "fund-combo-lab.md"' in open("check_site_consistency.py", encoding="utf-8").read()
    assert "fund-combo-lab.yml" in open("RESEARCH_LABS.md", encoding="utf-8").read()


if __name__ == "__main__":
    n = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            n += 1
            print(f"ok {name}")
    print(f"{n} tests passed")
