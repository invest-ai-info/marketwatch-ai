# -*- coding: utf-8 -*-
"""R11 株価指数・商品と為替の時系列モメンタム（tsmom_lab.py）のテスト。2026-10-08 夜 新設。

値動きはすべて作り物。確かめること＝①事前登録と定数の一致 ②月ごとの表（月末の終値・60日のばらつき・データの誤りの日）
③向き・量・費用・持ち越し・スワップの式 ④仕込んだトレンドを見つける／でたらめでは幅が0をまたぐ・偽薬の p ⑤為替の1時間足→日ごと・
BIS の CSV の読み方 ⑥昔／最近（Q2 の前半後半の代わり）と判定の言葉 ⑦ワークフロー・SYNC 禁忌・検証済みリスト。

実行:  python tests/test_tsmom_lab.py     （pytest 不要。pytest でも動く）
"""
import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import tsmom_lab as L  # noqa: E402


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    sec = text[text.index("## R11 "):text.index("## 見込みなしで止める決まり")]
    for s in ("0.10 ÷ σ", "上限3倍", "60日", "× 0.05％", "年3％", "1.2pips・ほか 1.8pips", "年1％", "BIS", "**BIS に届かなければ Q2 は判定しない**",
              "25％", "**1990年1月〜2026年8月**", "36か月未満", "97.5％＝1−0.05÷2", "6か月のかたまり", "2,000回", "p＜0.025（片側）", "3つ未満の月は数えない"):
        assert s in sec, s
    assert (L.LOOK, L.VOL_DAYS, L.ANN, L.TARGET, L.CAP, L.Q1_COST, L.Q1_FIN) == (12, 60, 252, 0.10, 3.0, 0.0005, 0.03)
    assert (L.FX_PIPS_JPY, L.FX_PIPS_OTHER, L.FX_MARKUP, L.MAX_DAY, L.MIN_ASSETS, L.FIRST_Q1, L.LAST, L.SPLIT, L.MIN_OLD) == \
           (1.2, 1.8, 0.01, 0.25, 3, (1990, 1), (2026, 8), (2010, 1), 36)
    assert abs(L.ALPHA - 0.025) < 1e-12 and L.N_PERM == 2000 and len(L.Q1_ASSETS) == 9 and len(L.FX_PAIRS) == 12


def _daily(drifts, seed=0, start="2000-01-03", vol=0.01):
    """月ごとの流れ（drifts＝月ごとの日あたりの流れ）を仕込んだ平日の終値"""
    rng = np.random.default_rng(seed)
    days = pd.bdate_range(start, periods=21 * len(drifts))
    mu = np.repeat(drifts, 21)[:len(days)]
    return pd.Series(100 * np.exp(np.cumsum(mu + rng.normal(0, vol, len(days)))), index=days)


def test_monthly_table_and_bad_days():
    s = _daily([0.0] * 12)
    tb = L.monthly_table(s)
    k = L.month_key(s.index[-1])
    assert abs(tb.loc[k, "close"] - s.iloc[-1]) < 1e-9 and 0.10 < tb.loc[k, "sigma"] < 0.22          # 日 1％ ≒ 年 16％
    s2 = s.copy()
    s2.iloc[100] *= 1.3                                                                                # +30％ の誤り
    tb2 = L.monthly_table(s2)
    km = L.month_key(s2.index[100])
    assert tb2.loc[km, "bad_month"] and tb2.loc[km, "bad_win"] and not tb.loc[km, "bad_month"]
    s3 = s.copy()
    s3.iloc[100:] *= 0.79                                                                              # −21％ の本当の下げは誤りではない（1987年など）
    assert not L.monthly_table(s3).loc[km, "bad_month"]


def _tables(n=4, months=120, trend=True, seed=1):
    rng = np.random.default_rng(seed)
    out = {}
    for i in range(n):
        if trend:   # 12か月ごとに向きが変わる強いトレンド
            dr = np.repeat([0.002 if (j // 24) % 2 == 0 else -0.002 for j in range(months)], 1)
        else:
            dr = np.zeros(months)
        out[f"A{i}"] = L.monthly_table(_daily(dr, seed=seed + i, vol=0.006))
    return out


def test_formula_of_one_cell():
    tb = _tables(n=3)
    months = L.month_list((2002, 1), (2008, 12))
    mx = L.matrices(tb, months, "q1")
    i, j = 0, 30
    assert mx["V"][i, j]
    k = months[j]
    y, m = L.ym_tuple(k)
    prev = f"{(y * 12 + m - 13) // 12:04d}-{(y * 12 + m - 13) % 12 + 1:02d}"
    nxt = f"{(y * 12 + m) // 12:04d}-{(y * 12 + m) % 12 + 1:02d}"
    a, b, c = (tb["A0"].loc[x] for x in (prev, k, nxt))
    s = 1.0 if b["close"] > a["close"] else -1.0
    w = min(0.10 / b["sigma"], 3.0)
    assert mx["S"][i, j] == s and abs(mx["W"][i, j] - w) < 1e-12 and abs(mx["R"][i, j] - (c["close"] / b["close"] - 1)) < 1e-12
    v = L.net(mx)
    pos, prevpos = s * w, mx["S"][i, j - 1] * mx["W"][i, j - 1]
    want = pos * mx["R"][i, j] - abs(pos - prevpos) * 0.0005 - abs(pos) * 0.03 / 12
    assert abs(v[i, j] - want) < 1e-12


def test_finds_planted_trend_and_not_noise():
    months = L.month_list((2002, 1), (2009, 6))
    tr = L.analyze_arm(L.matrices(_tables(trend=True), months, "q1"), "q1")
    assert tr["full"]["mean"] > 0 and tr["placebo_p"] < 0.05
    nz = L.analyze_arm(L.matrices(_tables(trend=False, seed=5), months, "q1"), "q1")
    assert nz["full"]["lo"] < 0 < nz["full"]["hi"] or nz["full"]["hi"] < 0                    # でたらめ＋費用＝プラスにはならない
    assert nz["verdict"] in (L.NONE, L.REV) and nz["placebo_p"] > 0.025


def test_fx_daily_bis_and_swap():
    ix = pd.date_range("2020-01-01", periods=72, freq="h", tz="UTC")
    df = pd.DataFrame({"bc": np.linspace(1.10, 1.11, 72), "ac": np.linspace(1.1001, 1.1101, 72)}, index=ix)
    c, sp = L.fx_daily(df)
    assert len(c) == 3 and abs(c.iloc[0] - (df["bc"].iloc[23] + df["ac"].iloc[23]) / 2) < 1e-12 and abs(sp.iloc[0] - 0.0001) < 1e-9
    csv_text = "FREQ,REF_AREA,TIME_PERIOD,OBS_VALUE\nM,US,2020-01,1.75\nM,JP,2020-01,-0.10\nM,US,2020-02,1.75\nM,XM,2020-03,0\n"
    r = L.parse_bis_csv(csv_text)
    assert r["US"]["2020-01"] == 1.75 and r["JP"]["2020-01"] == -0.1 and L.rate_at(r, "US", "2020-04") == 1.75 and L.rate_at(r, "JP", "2020-06") is None
    assert L.parse_bis_csv("a,b\n1,2\n") == {}
    rates, url = L.fetch_bis(get=lambda u: "FREQ,REF_AREA,TIME_PERIOD,OBS_VALUE\n" + "".join(f"M,{a},2020-01,1\n" for a in "US JP XM GB AU CA CH NZ".split()))
    assert len(rates) == 8 and url == L.BIS_URLS[0].format(areas="+".join(sorted(set(L.CCY_AREA.values()))))
    assert L.fetch_bis(get=lambda u: 1 / 0) == ({}, None)


def test_fx_matrices_costs_and_swap():
    tb = {p: L.monthly_table(_daily([0.001] * 60, seed=i, vol=0.004) * (150 if p.endswith("JPY") else 1.1)) for i, p in enumerate(("USDJPY", "EURUSD", "AUDUSD"))}
    for p in tb:
        tb[p]["spread"] = 0.00001
    months = L.month_list((2001, 3), (2004, 6))
    rates = {a: {k: (5.0 if a == "US" else 0.0) for k in months} for a in ("US", "JP", "XM", "AU")}
    mx = L.matrices(tb, months, "q2", rates)
    j = 10
    i = mx["names"].index("USDJPY")
    assert abs(mx["K"][i, j] - 5.0 / 100 / 12) < 1e-12 and abs(mx["F"][i, j] - 0.01 / 12) < 1e-12
    assert abs(mx["C"][i, j] - 1.2 * 0.01 / tb["USDJPY"].loc[months[j], "close"]) < 1e-12                      # 実際の差より個人の費用が大きい
    e = mx["names"].index("EURUSD")
    assert abs(mx["K"][e, j] - (0.0 - 5.0) / 100 / 12) < 1e-12 and abs(mx["C"][e, j] - 1.8 * 0.0001 / tb["EURUSD"].loc[months[j], "close"]) < 1e-12
    noswap = L.matrices(tb, months, "q2", None)
    assert not noswap["K"].any() and not noswap["F"].any() and noswap["V"].sum() == mx["V"].sum()


def test_halves_and_verdict():
    months = L.month_list((2012, 1), (2016, 12))
    ser = np.ones(len(months))
    old, new, lab = L.halves(months, ser, "q2")
    assert lab == ("前半", "後半") and len(old) == len(new) == 30
    m2 = L.month_list((2005, 1), (2015, 12))
    o2, n2, l2 = L.halves(m2, np.ones(len(m2)), "q2")
    assert l2 == ("〜2009年", "2010年〜") and m2[o2[-1]] == "2009-12" and m2[n2[0]] == "2010-01"
    pos, zero, neg = {"mean": 0.01, "lo": 0.001, "hi": 0.02}, {"mean": 0.0, "lo": -0.01, "hi": 0.01}, {"mean": -0.01, "lo": -0.02, "hi": -0.001}
    assert L.verdict(pos, 0.01, pos, 0.01) == L.OK and L.verdict(pos, 0.01, pos, 0.03) == L.NEW_ONLY
    assert L.verdict(pos, -0.01, zero, 0.01) == L.NONE and L.verdict(neg, -0.01, zero, 0.9) == L.REV
    assert L.verdict(zero, 0.0, pos, 0.5) == L.NEW_ONLY


def test_outputs_and_registrations():
    months = L.month_list((2002, 1), (2009, 6))
    a = L.analyze_arm(L.matrices(_tables(), months, "q1"), "q1")
    res = {"generated_at": "x", "prereg_sha256": "0" * 64, "result": {"q1": a, "bis_url": None}}
    md = L.render_md(res)
    assert "R11" in md and "Q1 株価指数・商品（MT4）" in md and "投資助言ではありません" in md and "届かず" in md
    json.dumps(L.M.rounded(res), ensure_ascii=False)
    v = L.verdicts_of({"q1": dict(a, verdict=L.NONE), "q2": dict(a, verdict=L.SKIP)}, "2026-10-08")
    assert set(v) == {"Q1"} and v["Q1"]["status"] == "stop"
    assert "でたらめな向きには勝つ" in L.verdicts_of({"q1": dict(a, verdict=L.NONE, placebo_p=0.001)}, "x")["Q1"]["reason"]
    assert "でたらめな向きと区別できない" in L.verdicts_of({"q1": dict(a, verdict=L.NONE, placebo_p=0.5)}, "x")["Q1"]["reason"]
    import verified_list as V
    assert ("tsmom-lab.json", "Q1") in V.REASON_FIX and "でたらめな向きには勝つ" in V.REASON_FIX[("tsmom-lab.json", "Q1")]
    wf = open(".github/workflows/tsmom-lab.yml", encoding="utf-8").read()
    assert "python -u tsmom_lab.py --check" in wf and "restore-keys: fx-bars-" in wf and "python tests/test_tsmom_lab.py" in wf
    assert "tsmom-lab.json tsmom-lab.md verified-list.md" in wf
    assert '"tsmom-lab.json", "tsmom-lab.md"' in open("check_site_consistency.py", encoding="utf-8").read()
    assert '"tsmom-lab.json"' in open("verified_list.py", encoding="utf-8").read()
    assert "tsmom-lab.yml" in open("RESEARCH_LABS.md", encoding="utf-8").read()


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
