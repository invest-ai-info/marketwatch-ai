# -*- coding: utf-8 -*-
"""F2 為替の割安と経済の勢い（fx_value_lab.py）のテスト。2026-10-10 新設。

値はすべて作り物。確かめること＝①事前登録と定数の一致 ②BIS・OECD・FRED の CSV と一覧の読み方 ③使える値の決まり
（月ごと t−2・四半期 t−3・古すぎる値は使わない）④V（割安）・E（経済の勢い）の向き ⑤順位の重み（買い1・売り1・同じ値・6つ未満）
⑥check がネットにつながずに動き、損益を数えず、何も書き出さない ⑦ワークフロー・SYNC 禁忌。

実行:  python tests/test_fx_value_lab.py     （pytest 不要。pytest でも動く）
"""
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import fx_value_lab as L  # noqa: E402


def _sec():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    return text[text.index("## F2 為替の割安と経済の勢い"):text.index("## 共通の決まり")]


def test_prereg_matches_the_code():
    sec = _sec()
    for s in ("USD・EUR・GBP・JPY・AUD・CHF・CAD・NZD（8つ）", "EURUSD・GBPUSD・USDJPY・AUDUSD・USDCHF・USDCAD・NZDUSD",
              "**参照の月が t−2 以前**", "**その四半期の最後の月が t−3 以前**", "t−14 より古い", "54〜66か月前の13か月の平均",
              "**6つ以上**", "**買いの合計が1・売りの合計が1**", "1.2pips・ほか 1.8pips", "年1％", "**2026年8月**",
              "**2004年〜2014年**", "**2015年〜**", "98.33％＝1−0.05÷3", "6か月のかたまり", "10,000回", "2,000回", "**p＜0.0167（片側）**",
              "**失業率がどこからも取れなければ、E は物価の勢いだけで数える**", "**BIS の政策金利に届かなければ判定しない**"):
        assert s in sec, s
    assert L.CCYS == ("USD", "EUR", "GBP", "JPY", "AUD", "CHF", "CAD", "NZD")
    assert L.PAIRS == ("EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCHF", "USDCAD", "NZDUSD")
    assert (L.LAG_M, L.LAG_Q, L.STALE, L.V_FROM, L.V_TO, L.MOM, L.MIN_CCY) == (2, 3, 14, 54, 66, 12, 6)
    assert (L.LAST, L.SPLIT, L.N_ARMS, L.N_BOOT, L.N_PERM, L.BLOCK) == ((2026, 8), (2015, 1), 3, 10000, 2000, 6)
    assert abs(L.ALPHA - 0.05 / 3) < 1e-12
    assert (L.FX_PIPS_JPY, L.FX_PIPS_OTHER, L.FX_MARKUP) == (1.2, 1.8, 0.01)


def test_technical_closure_is_recorded():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    sec = text[text.index("## テクニカルの区切りと、ファンダメンタルの柱"):text.index("## F2 為替の割安と経済の勢い")]
    for s in ("**新しい登録**", "続けるもの", "F1 日本株の割安×質", "それまで登録しない"):
        assert s in sec, s


def test_period_and_parsers():
    assert L.period_key("2020-01") == ("M", 2020, 1)
    assert L.period_key("2020-Q2") == ("Q", 2020, 6)
    assert L.period_key("2020-03-31") == ("M", 2020, 3)
    assert L.period_key("2020") is None and L.period_key("2020-13") is None
    bis = ("FREQ,REF_AREA,UNIT_MEASURE,TIME_PERIOD,OBS_VALUE\n"
           "M,JP,628,2020-01,100.5\nM,JP,628,2020-02,101\nQ,AU,628,2020-Q1,99\nM,JP,628,2020-03,NaN\nM,JP,771,2020-01,\n")
    p = L.parse_sdmx_csv(bis, ("FREQ", "REF_AREA", "UNIT_MEASURE"))
    assert p[("M", "JP", "628")] == {(2020, 1): 100.5, (2020, 2): 101.0}
    assert p[("Q", "AU", "628")] == {(2020, 3): 99.0}
    assert ("M", "JP", "771") not in p
    low = "freq,ref_area,time_period,obs_value\nM,GB,2021-05,1.5\n"
    assert L.parse_sdmx_csv(low, ("REF_AREA",)) == {("GB",): {(2021, 5): 1.5}}
    assert L.parse_sdmx_csv("A,B\n1,2\n") == {}
    fred = "observation_date,LRHUTTTTJPM156S\n2020-01-01,2.4\n2020-02-01,.\n2020-03-01,2.5\n"
    assert L.parse_fred_csv(fred) == {(2020, 1): 2.4, (2020, 3): 2.5}
    xml = ('<structure:Dataflow id="DSD_LFS@DF_IALFS_UNE_M" agencyID="OECD.SDD.TPS" version="1.0"/>'
           '<structure:Dataflow agencyID="OECD.SDD.TPS" id="DSD_LFS@DF_IALFS_UNE_Q" version="1.0"/>'
           '<structure:Dataflow id="DSD_PRICES@DF_PRICES_ALL" agencyID="OECD.SDD.TPS" version="1.0"/>')
    assert L.flows_matching(xml) == ["OECD.SDD.TPS,DSD_LFS@DF_IALFS_UNE_M", "OECD.SDD.TPS,DSD_LFS@DF_IALFS_UNE_Q"]
    assert L.span({(2020, 3): 1, (2019, 12): 2}) == ["2019-12", "2020-03", 2] and L.span({}) is None
    assert L.freq_of({(2020, m): 1 for m in (3, 6, 9, 12)}) == "Q"
    assert L.freq_of({(2020, m): 1 for m in range(1, 13)}) == "M"


def _monthly(first=(1990, 1), last=(2026, 12), f=lambda i: 100.0):
    out, (y, m), i = {}, first, 0
    while (y, m) <= last:
        out[(y, m)] = f(i)
        y, m, i = y + (m == 12), m % 12 + 1, i + 1
    return out


def test_latest_usable_lag_rules():
    s = _monthly()
    k, _ = L.latest_usable(s, (2020, 5), "M")
    assert k == (2020, 3)                                    # 月ごと＝t−2
    q = {(2019, 12): 1.0, (2020, 3): 2.0, (2020, 6): 3.0}
    assert L.latest_usable(q, (2020, 5), "Q")[0] == (2019, 12)   # 2020-Q1 の最後の月 3 は t−3＝2 より後＝まだ使えない
    assert L.latest_usable(q, (2020, 6), "Q")[0] == (2020, 3)
    old = {(2018, 1): 1.0}
    assert L.latest_usable(old, (2020, 1), "M") is None      # t−14 より古い
    assert L.latest_usable({}, (2020, 1), "M") is None


def test_v_signal_direction():
    # 5年前は 100、使える最新の月だけ 80 に下がった＝実質的に安くなった＝割安＝プラス
    cheap = _monthly()
    for k in list(cheap):
        if L.mi(*k) >= L.mi(2020, 1):
            cheap[k] = 80.0
    v = L.v_signal(cheap, (2020, 3))
    assert v is not None and abs(v - (0.0 - __import__("math").log(0.8))) < 1e-9
    dear = {k: (120.0 if L.mi(*k) >= L.mi(2020, 1) else 100.0) for k in _monthly()}
    assert L.v_signal(dear, (2020, 3)) < 0
    short = {k: v for k, v in _monthly().items() if L.mi(*k) >= L.mi(2017, 1)}
    assert L.v_signal(short, (2020, 3)) is None              # 5年半前が無い


def test_rank_weights():
    w = L.rank_weights({"USD": 1, "EUR": 2, "GBP": 3, "JPY": 4, "AUD": 5, "CHF": 6, "CAD": 7, "NZD": 8})
    assert abs(sum(x for x in w.values() if x > 0) - 1) < 1e-12 and abs(sum(x for x in w.values() if x < 0) + 1) < 1e-12
    assert w["NZD"] > w["CAD"] > 0 > w["EUR"] > w["USD"] and abs(w["NZD"] + w["USD"]) < 1e-12
    t = L.rank_weights({"USD": 1, "EUR": 1, "GBP": 3, "JPY": 4, "AUD": 5, "CHF": 6})
    assert abs(t["USD"] - t["EUR"]) < 1e-12                  # 同じ値は同じ重み
    assert L.rank_weights({"USD": 1, "EUR": 2, "GBP": 3, "JPY": 4, "AUD": 5}) is None   # 6つ未満
    assert L.rank_weights({c: 1.0 for c in L.CCYS}) is None  # 全部同じ＝並べられない
    assert L.rank_weights({"USD": 1, "EUR": 2, "GBP": 3, "JPY": 4, "AUD": 5, "CHF": float("nan"), "CAD": None}) is None


def test_e_signal_direction():
    # 物価：NZD だけ前年比が上がっていく（勢いプラス）、JPY だけ下がっていく
    def cpi_for(c):
        g = {"NZD": 0.004, "JPY": -0.002}.get(c, 0.002)
        acc = {"NZD": 0.0002, "JPY": -0.0002}.get(c, 0.0)
        return _monthly(f=lambda i: 100 * (1 + g + acc * i) ** i)
    cpi = {c: cpi_for(c) for c in L.CCYS}
    freq = {c: "M" for c in L.CCYS}
    e = L.e_signal(cpi, {}, (2020, 6), freq, {})
    assert e["NZD"] > 0 > e["JPY"]
    w = L.rank_weights(e)
    assert w["NZD"] > 0 > w["JPY"]
    # 失業率：EUR だけ下がっていく＝雇用の勢いプラス（ほかは横ばい）。順位の平均＝物価（NZD 8・JPY 1・ほか 4.5）と雇用（EUR 8・ほか 4）
    une = {c: _monthly(f=(lambda i: 9 - 0.01 * i) if c == "EUR" else (lambda i: 5.0)) for c in L.CCYS}
    e2 = L.e_signal(cpi, une, (2020, 6), freq, {c: "M" for c in L.CCYS})
    assert set(e2) == set(L.CCYS)
    assert (e2["EUR"], e2["NZD"], e2["USD"], e2["JPY"]) == (6.25, 6.0, 4.25, 2.5)


def test_check_runs_offline_and_writes_nothing():
    reer = "FREQ,EER_TYPE,EER_BASKET,REF_AREA,TIME_PERIOD,OBS_VALUE\n" + "".join(
        f"M,R,B,{a},{y:04d}-{m:02d},{100 + (i % 7) + j}\n"
        for j, a in enumerate(L.BIS_AREA.values()) for i, (y, m) in enumerate(L.month_list((1995, 1), (2026, 8))))
    cpi = "FREQ,REF_AREA,UNIT_MEASURE,TIME_PERIOD,OBS_VALUE\n" + "".join(
        f"M,{a},628,{y:04d}-{m:02d},{100 * (1.001 + j / 5000) ** i}\n"
        for j, a in enumerate(L.BIS_AREA.values()) for i, (y, m) in enumerate(L.month_list((1995, 1), (2026, 8))))
    pol = "FREQ,REF_AREA,TIME_PERIOD,OBS_VALUE\n" + "".join(
        f"M,{a},2010-{m:02d},1.0\n" for a in L.BIS_AREA.values() for m in range(1, 13))

    def get(url):
        if "WS_EER" in url:
            return reer, None
        if "WS_LONG_CPI" in url:
            return cpi, None
        if "WS_CBPOL" in url:
            return pol, None
        return None, "HTTP 403"
    before = set(os.listdir(ROOT))
    rep = L.check(get=get, fx_root=os.path.join(ROOT, "no-such-fx-bars"))
    assert set(os.listdir(ROOT)) == before                   # 何も書き出さない
    assert rep["bis_reer"]["areas"]["JPY"][0] == "1995-01" and len(rep["bis_cbpol"]["areas"]) == 8
    assert set(rep["cpi_used"]) == set(L.CCYS)
    assert isinstance(rep["oecd_flows_une"], str) and "oecd_une_errors" in rep
    assert all(isinstance(v, str) for v in rep["fred_une"].values())
    mw = rep["months_with_signal"]
    assert mw["months_total"] == len(L.month_list((2004, 1))) and mw["V"] == mw["months_total"] and mw["E_cpi_only"] == mw["months_total"]
    assert not any(k in rep for k in ("returns", "mean", "result"))   # 損益は数えない


def _prices(months, f):
    """作り物の月ごとの表：ペア → DataFrame（'YYYY-MM'・close・spread）。f(pair, j) が値段"""
    import pandas as pd
    out = {}
    for pr in L.PAIRS:
        rows = {L.ymk(t): {"close": f(pr, j), "spread": 0.00005 if not pr.endswith("JPY") else 0.005} for j, t in enumerate(months)}
        out[pr] = pd.DataFrame.from_dict(rows, orient="index").sort_index()
    return out


def test_pair_direction_and_month_inputs():
    assert L.pair_of("EUR") == ("EURUSD", 1.0) and L.pair_of("JPY") == ("USDJPY", -1.0) and L.pair_of("CAD") == ("USDCAD", -1.0)
    months = L.month_list((2010, 1), (2010, 3))
    pr = _prices(months + [(2010, 4)], lambda p, j: (100.0 * 1.1 ** j) if p == "USDJPY" else 1.0)
    inp = L.month_inputs(pr, months)
    r, cost = inp[0]["JPY"]
    assert abs(r - (-math.log(1.1))) < 1e-12                 # ドル円が上がった＝円はドルに対して下がった
    assert abs(cost - 1.2 * 0.01 / 100.0) < 1e-12             # 決まった費用 1.2pips が実際の差 0.5pips より大きい
    assert abs(inp[0]["EUR"][0]) < 1e-12 and abs(inp[0]["EUR"][1] - 1.8 * 0.0001 / 1.0) < 1e-12
    short = L.month_inputs(pr, [(2010, 4)])                   # 次の月が無い＝数えない
    assert short == [{}]


def test_arm_values_return_cost_swap():
    months = L.month_list((2010, 1), (2010, 2))
    pr = _prices(months + [(2010, 3)], lambda p, j: 1.0 * 1.02 ** j if p == "EURUSD" else 1.0)
    inp = L.month_inputs(pr, months)
    w = [{"EUR": 1.0, "USD": -1.0}, {"EUR": 1.0, "USD": -1.0}]
    v, to, sw = L.arm_values(w, inp)                          # スワップなし
    c0 = 1.8 * 0.0001 / 1.0
    assert abs(v[0] - (math.log(1.02) - c0)) < 1e-12 and abs(v[1] - math.log(1.02)) < 1e-12   # 2か月目は入れ替えなし＝費用なし
    assert list(to) == [1.0, 0.0]
    rtab = [{"USD": 2.0, "EUR": 5.0}, {"USD": 2.0, "EUR": 5.0}]
    v2, _, sw2 = L.arm_values(w, inp, rtab)
    assert abs(sw2[0] - (3.0 / 100 / 12 - 0.01 / 12)) < 1e-12 and abs(v2[1] - v[1] - sw2[1]) < 1e-12
    v3, _, _ = L.arm_values(w, inp, [{"USD": 2.0}, {"USD": 2.0, "EUR": 5.0}])
    c1 = 1.8 * 0.0001 / 1.02                                  # 2か月目の値段 1.02 で割る
    assert math.isnan(v3[0]) and abs(v3[1] - (math.log(1.02) - c1 + sw2[1])) < 1e-12   # 金利が無い月は数えず、次の月は0から建てる
    v4, _, _ = L.arm_values([None, w[1]], inp)
    assert math.isnan(v4[0]) and abs(v4[1] - (math.log(1.02) - c1)) < 1e-12


def _world(n_months, aligned, seed=1):
    """合図と次の月の値動きが揃っている（aligned）か、無関係な作り物の世界"""
    import numpy as np
    rng = np.random.default_rng(seed)
    S, inp = {"V": [], "E": []}, []
    for _ in range(n_months):
        sig = {c: float(rng.normal()) for c in L.CCYS}
        noise = {c: float(rng.normal()) for c in L.CCYS}
        row = {c: (0.01 * ((sig[c] - sig["USD"]) if aligned else noise[c] - noise["USD"]), 0.0) for c in L.CCYS[1:]}
        inp.append(row)
        S["V"].append(sig)
        S["E"].append({c: float(rng.normal()) for c in L.CCYS})
    return S, inp


def test_placebo_finds_aligned_signal_only():
    import numpy as np
    S, inp = _world(60, True)
    x = L.arm_series("V", S, inp, None)
    p = L.placebo_p("V", S, inp, None, float(np.nanmean(x)), n_perm=200)
    assert np.nanmean(x) > 0 and p < 0.02
    S2, inp2 = _world(60, False)
    x2 = L.arm_series("V", S2, inp2, None)
    p2 = L.placebo_p("V", S2, inp2, None, float(np.nanmean(x2)), n_perm=200)
    assert p2 > 0.02
    ve = L.arm_series("VE", S, inp, None)
    assert np.isfinite(ve).all() and abs(np.nanmean(ve) - (np.nanmean(x) + np.nanmean(L.arm_series("E", S, inp, None))) / 2) < 1e-12


def test_verdict_words():
    plus, zero, minus = {"lo": 0.001, "hi": 0.01, "mean": 0.005}, {"lo": -0.01, "hi": 0.01, "mean": 0.001}, {"lo": -0.02, "hi": -0.001, "mean": -0.01}
    assert L.verdict(plus, 0.002, {"mean": 0.003}, 0.001) == L.OK
    assert L.verdict(plus, 0.002, {"mean": 0.003}, 0.05) != L.OK            # 偽薬を越えなければ ✅ にしない
    assert L.verdict(plus, -0.001, plus, 0.001) == L.NEW_ONLY                # 昔がマイナス＝最近だけ
    assert L.verdict(minus, -0.01, zero, 0.9) == L.REV and L.verdict(zero, 0.0, zero, 0.5) == L.NONE


def test_analyze_end_to_end_and_skip_without_rates():
    import numpy as np
    rng = np.random.default_rng(3)
    months = L.month_list((2013, 1), (2016, 6))
    allm = L.month_list((1995, 1), (2016, 7))
    reer = {c: {t: float(100 * np.exp(rng.normal(0, 0.02) * 1 + 0.001 * i * (k - 3))) for i, t in enumerate(allm)} for k, c in enumerate(L.CCYS)}
    cpi = {c: {t: float(100 * (1.002 + 0.0003 * k + 0.00001 * i) ** i) for i, t in enumerate(allm)} for k, c in enumerate(L.CCYS)}
    une = {c: {t: float(5 + rng.normal(0, 0.3)) for t in allm} for c in L.CCYS}
    freq = {c: "M" for c in L.CCYS}
    pr = _prices(L.month_list((2013, 1), (2016, 7)), lambda p, j: float(np.exp(rng.normal(0, 0.03))) * (100 if p == "USDJPY" else 1))
    rates = {a: {L.ymk(t): 1.0 + k * 0.5 for t in allm} for k, a in enumerate(L.BIS_AREA.values())}
    r = L.analyze(pr, reer, cpi, freq, une, freq, rates, months, n_perm=30)
    for arm, _ in L.ARMS:
        a = r[arm]
        assert a["months"] == len(months) and a["verdict"] in (L.OK, L.NEW_ONLY, L.REV, L.NONE)
        assert a["placebo_p"] is not None and a["read"]["swap_part"] is not None
    assert r["carry_read"]["months"] == len(months) and r["E_une_read"]["months"] == len(months)
    md = L.render_md({"generated_at": "x", "prereg_sha256": "abc", "result": r})
    assert "## まとめ（判定）" in md and "投資助言ではありません" in md
    v = L.verdicts_of(r, "2026-10-10")
    assert all(x["status"] == "stop" and x["reason"].startswith("過去のデータで1回だけ数えて") for x in v.values())
    r0 = L.analyze(pr, reer, cpi, freq, une, freq, {}, months, n_perm=5)   # 政策金利に届かない＝判定しない
    assert all(r0[arm]["verdict"] == L.SKIP and r0[arm]["placebo_p"] is None for arm, _ in L.ARMS)
    assert L.verdicts_of(r0, "2026-10-10") == {}


def test_cpi_and_unemployment_picks_follow_the_addendum():
    parsed = {("M", a, "628"): {(y, m): 100.0 + m for y in (2019, 2020) for m in range(1, 13)} for a in L.BIS_AREA.values()}
    cpi, f = L.pick_cpi(parsed)
    assert f["AUD"] == f["NZD"] == "Q" and sorted(cpi["AUD"])[-4:] == [(2020, 3), (2020, 6), (2020, 9), (2020, 12)] and len(cpi["AUD"]) == 8
    assert f["USD"] == "M" and len(cpi["USD"]) == 24
    une_parsed = {(a,) + L.UNE_KEY + (fq,): {(2020, 3): 4.0} for c, (a, fq) in L.UNE_PICK.items()}
    une_parsed[("USA",) + L.UNE_KEY[:2] + ("N",) + L.UNE_KEY[3:] + ("M",)] = {(2020, 3): 9.9}   # 季節調整なしは使わない
    une, uf = L.pick_une(une_parsed)
    assert set(une) == set(L.CCYS) and uf["CHF"] == uf["NZD"] == "Q" and une["USD"][(2020, 3)] == 4.0
    assert L.UNE_PICK["EUR"] == ("EA", "M") and L.UNE_KEY == ("UNE_LF_M", "PT_LF_SUB", "Y", "_T", "Y_GE15")
    sec = _sec()
    for s in ("`WS_EER` の `M.R.B`", "**豪ドル・NZドルは、公式の消費者物価が四半期ごとなので、3・6・9・12月の行だけを使い",
              "**MEASURE＝UNE_LF_M・UNIT_MEASURE＝PT_LF_SUB・ADJUSTMENT＝Y（季節調整済み）・SEX＝_T・AGE＝Y_GE15**",
              "**四半期ごと＝CHE・NZL**", "FRED は使わない"):
        assert s in sec, s


def test_workflow_and_sync_rules():
    wf = open(".github/workflows/fx-value-lab.yml", encoding="utf-8").read()
    assert "workflow_dispatch" in wf and "schedule" not in wf and "fx_value_lab.py --check" in wf
    assert "tests/test_fx_value_lab.py" in wf and "restore-keys: fx-bars-" in wf and "options: [check, run]" in wf
    assert "git add fx-value-lab.json fx-value-lab.md verified-list.md" in wf and "python verified_list.py" in wf
    cs = open("check_site_consistency.py", encoding="utf-8").read()
    assert '"fx-value-lab.json", "fx-value-lab.md"' in cs
    assert "fx-value-lab.yml" in open("RESEARCH_LABS.md", encoding="utf-8").read()
    import verified_list as VL
    assert any(s[0] == "fx-value-lab.json" and s[2] == "F2" for s in VL.SOURCES)


if __name__ == "__main__":
    n = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            n += 1
            print(f"ok {name}")
    print(f"{n} tests passed")
