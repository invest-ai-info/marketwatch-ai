# -*- coding: utf-8 -*-
"""J42 日本株の数か月単位のモメンタム（momentum_lab.py）のテスト。2026-10-08 新設。

値動きはすべて作り物。確かめること＝①事前登録と定数の一致 ②データの誤りの日は値動き0でつなぐ（分割の取りこぼし・長い間）
③月ごとの値（買う日の寄り・月末の値段・52週高値への近さ）④残差の当てはめ（最小二乗と同じ・業種が使えなければ全銘柄の平均だけ）
⑤仕込んだモメンタムを見つける・入れ替えた割合と費用 ⑥判定の言葉と幅 ⑦税の目安 ⑧点検は損益を出さない・出力に銘柄コードを出さない
⑨ワークフロー・SYNC 禁忌・検証済みリスト。

実行:  python tests/test_momentum_lab.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import momentum_lab as M  # noqa: E402


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    sec = text[text.index("## J42 日本株の数か月単位のモメンタム"):text.index("## 見込みなしで止める決まり")]
    for s in ("**1億円以上**", "**往復 0.1％**", "98.33％（＝1−0.05÷3）", "6か月ずつのかたまり", "**1995年1月〜2026年8月**",
              "**37か月分の月末の値段がそろう**", "**100銘柄未満の月は数えない**", "50銘柄以上に足がある日", "上位10％",
              "365暦日の高値", "m−11〜m−1 の11か月の合計 ÷ 同じ11か月の残りの標準偏差", "5銘柄以上", "最後の5取引日",
              "**昔＝決める月 1995〜2009年／最近＝2010〜2026年**", "上位10銘柄・上位20銘柄", "20.315％",
              "**数えられる月は 2003年1月〜2026年8月の284か月**", "**物差しと判定は変えない**"):
        assert s in sec, s
    assert (M.TV_MIN, M.TV_BIG, M.HIST, M.LOOK, M.RES_MONTHS, M.END_WINDOW, M.HI_DAYS) == (1.0, 10.0, 36, 12, 11, 5, 365)
    assert (M.TOP_FRAC, M.HAND, M.MIN_UNIVERSE, M.MIN_IND, M.MIN_CAL, M.MAX_GAP_DAYS) == (0.10, (10, 20), 100, 5, 50, 7)
    assert (M.COST, M.COST_HI, M.BLOCK, M.N_BOOT, M.TAX, M.FIRST, M.LAST) == (0.001, 0.003, 6, 10000, 0.20315, (1995, 1), (2026, 8))
    assert abs(M.ALPHA - 0.05 / 3) < 1e-12 and [e for e, *_ in M.ERAS] == ["all", "old", "new"]


def test_bad_days_are_bridged_with_zero_move():
    day = np.array([1, 2, 3, 4, 20, 21]) + 730000
    c = np.array([100.0, 101.0, 50.5, 51.0, 52.0, 53.0])        # 3日目＝分割の取りこぼし（半分）・5日目＝16日の間
    o = np.r_[c[0], c[:-1]]
    o[2] = 50.0
    h, lo = np.maximum(o, c) * 1.01, np.minimum(o, c) * 0.99
    Pi, Q, Hx, bad = M.clean_index(day, o, h, lo, c)
    assert bad == 2
    assert np.allclose(Pi, [1, 1.01, 1.01, 1.01 * 51 / 50.5, 1.01 * 51 / 50.5, 1.01 * 51 / 50.5 * 53 / 52])
    assert np.isclose(Q[3], Pi[2] * o[3] / c[2]) and np.isclose(Q[2], Pi[1]) and np.isclose(Hx[1], Pi[1] * 1.01)


def _bdays(y0, m0, y1, m1):
    d, e = dt.date(y0, m0, 1), dt.date(y1, m1, 28)
    out = []
    while d <= e:
        if d.weekday() < 5:
            out.append(d.toordinal())
        d += dt.timedelta(days=1)
    return np.array(out)


def _cal_tables(days):
    return M.month_table(np.asarray(days))


def test_stock_months_entry_end_and_high():
    cal = _bdays(2024, 1, 2025, 3)
    Mi, first, last, tail = _cal_tables(cal)
    day = cal.copy()
    day = day[day != first[5]]                                  # 6か月目の最初の取引日だけ足がない
    day = day[~((day > tail[7]) & (day <= last[7]))]            # 8か月目は最後の4取引日に足がない（5日目より前で終わる）
    n = len(day)
    c = 100 * np.exp(np.linspace(0, 0.3, n))
    vals = np.c_[c, c * 1.01, c * 0.99, c, np.full(n, 1e6)]
    o, bad = M.stock_months(day, vals, Mi, first, last, tail)
    assert bad == 0 and np.isnan(o["q_entry"][5]) and np.isfinite(o["q_exit"][5]) and np.isfinite(o["q_entry"][6])
    assert np.isfinite(o["p_end"][7]) and not o["has_last"][7]
    assert np.isnan(o["hi"][10]) and np.isfinite(o["hi"][13])   # 365日たってから
    assert abs(o["tv"][3] - float(np.mean(c[(M.month_id(day) == Mi[3])] * 1e6)) / 1e8) < 1e-9
    k = np.nonzero(day == last[13])[0][0]
    assert abs(o["hi"][13] - 1 / 1.01) < 1e-9 and k > 0         # 上げ続けの株＝その日の高値が一番高い


def test_month_end_needs_last_five_days():
    cal = _bdays(2024, 1, 2024, 4)
    Mi, first, last, tail = _cal_tables(cal)
    day = cal[cal < tail[1]]                                    # 2か月目は最後の5取引日の前で終わり、そのあと足がない
    vals = np.c_[np.full(len(day), 100.0), np.full(len(day), 101.0), np.full(len(day), 99.0), np.full(len(day), 100.0), np.full(len(day), 1e6)]
    o, _ = M.stock_months(day, vals, Mi, first, last, tail)
    assert np.isfinite(o["p_end"][0]) and np.isnan(o["p_end"][1]) and np.isfinite(o["p_last"][1])


def test_residual_matches_least_squares_and_falls_back():
    rng = np.random.default_rng(1)
    n, T = 6, 36
    mkt = rng.normal(0, 0.05, T)
    IND = rng.normal(0, 0.03, (n, T))
    Y = 0.01 + 0.8 * mkt + 0.5 * IND + rng.normal(0, 0.02, (n, T))
    IND[5, 3] = np.nan                                          # 1か月でも業種が使えなければ全銘柄の平均だけ
    got = M.residual_scores(Y, mkt, IND)
    for i in range(n):
        X = np.c_[np.ones(T), mkt] if i == 5 else np.c_[np.ones(T), mkt, IND[i]]
        b = np.linalg.lstsq(X, Y[i], rcond=None)[0]
        e = (Y[i] - X @ b)[24:35]
        assert abs(got[i] - e.sum() / e.std(ddof=1)) < 1e-8


def test_industry_average_leaves_self_out():
    R = np.array([[0.1, 0.0], [0.2, np.nan], [0.3, 0.0], [0.4, 0.0], [0.5, 0.0], [0.6, 0.0], [0.7, 0.0], [9.0, 9.0]])
    sector = np.array([0, 0, 0, 0, 0, 0, 0, -1])
    I = M.industry_loo(R, sector)
    assert abs(I[0, 0] - np.mean([0.2, 0.3, 0.4, 0.5, 0.6, 0.7])) < 1e-12
    assert not np.isnan(I[1, 1]) and abs(I[1, 1]) < 1e-12      # 自分が欠けた月はほかの6銘柄
    assert abs(I[0, 1]) < 1e-12                                 # ほかがちょうど5銘柄（自分と欠けた1銘柄を除く）＝使える
    R2 = R.copy()
    R2[2, 1] = np.nan
    assert np.isnan(M.industry_loo(R2, sector)[0, 1])            # ほかが4銘柄＝使えない
    assert np.isnan(I[7]).all()                                 # 業種が空


CODES = [f"7X{i:02d}" for i in range(130)]


def _panel(drift_scale=0.02, seed=7, y1=1997):
    """銘柄ごとに一定の月の流れ（勝ち組は勝ち続ける）を仕込んだ作り物の日足 → 銘柄 × 月の表"""
    series, sectors, cal = _series(drift_scale, seed, y1)
    Mi, first, last, tail = M.month_table(cal)
    return M.panel(series, sectors, Mi, first, last, tail)


def _series(drift_scale=0.02, seed=7, y1=1997):
    """→ ({コード: (日, 値)}, {コード: 業種}, 取引日)"""
    rng = np.random.default_rng(seed)
    cal = _bdays(1990, 1, y1, 12)
    series, sectors = {}, {}
    for i, code in enumerate(CODES):
        mu = rng.normal(0, drift_scale) / 21
        lr = mu + rng.normal(0, 0.01, len(cal))
        c = 1000 * np.exp(np.cumsum(lr))
        o = np.r_[c[0], c[:-1]] * (1 + rng.normal(0, 0.001, len(cal)))
        h, lo = np.maximum(o, c) * 1.003, np.minimum(o, c) * 0.997
        v = np.full(len(cal), 2e6 if i % 13 else 1e4)           # 13銘柄に1つは売買代金が足りない
        series[code] = (cal.astype(np.int32), np.c_[o, h, lo, c, v].astype(np.float32))
        sectors[code] = f"業種{i % 6}" if i % 17 else ""
    return series, sectors, cal


def test_pipeline_finds_planted_momentum_and_costs():
    T = _panel()
    recs, _ = M.records(T, first=(1993, 1), last=(1997, 10))
    assert len(recs) == 58 and all(100 <= r["n_u"] <= 120 and r["n_top"] == round(r["n_u"] / 10) for r in recs)   # 値が下がって1億円を割る株は抜ける
    d1 = [M.diff(r, "Q1") for r in recs]
    assert np.mean(d1) > 0.005                                   # 仕込んだ流れ（月 ±2％ のばらつき）を見つける
    assert recs[0]["arms"]["Q1"]["rep"] == 1.0 and all(0 <= r["arms"]["Q1"]["rep"] <= 1 for r in recs)
    r = recs[5]["arms"]["Q1"]
    assert abs(M.diff(recs[5], "Q1") - (r["top"] - recs[5]["uni"] - r["rep"] * 0.001)) < 1e-12
    assert np.mean([x["arms"]["Q1"]["rep"] for x in recs[1:]]) < 0.5   # 流れが続く株＝あまり入れ替わらない
    assert np.mean([x["arms"]["Q1"]["bot"] - x["uni"] for x in recs]) < 0
    assert all(r["big_uni"] is None for r in recs)               # 10億円以上の組は100銘柄に届かない


def test_flat_market_has_no_edge():
    T = _panel(drift_scale=0.0, seed=3, y1=2000)
    recs, _ = M.records(T, first=(1993, 1), last=(2000, 10))
    j = M.band([M.diff(r, "Q1", cost=0.0) for r in recs])
    assert j["lo"] < 0 < j["hi"]                                # 仕込みなし＝幅が0をまたぐ


def test_verdict_words_and_band():
    b = M.band([0.01] * 30)
    assert abs(b["lo"] - 0.01) < 1e-12 and abs(b["hi"] - 0.01) < 1e-12 and M.band([0.01] * 11)["lo"] is None
    x = list(np.random.default_rng(0).normal(0.001, 0.01, 200))
    assert M.band(x) == M.band(x)                                # 種が固定
    pos, zero, neg = {"mean": 0.01, "lo": 0.001, "hi": 0.02}, {"mean": 0.0, "lo": -0.01, "hi": 0.01}, {"mean": -0.01, "lo": -0.02, "hi": -0.001}
    assert M.verdict({"all": pos, "old": pos, "new": pos}) == M.OK
    assert M.verdict({"all": pos, "old": neg, "new": pos}) == M.NEW_ONLY
    assert M.verdict({"all": zero, "old": zero, "new": pos}) == M.NEW_ONLY
    assert M.verdict({"all": neg, "old": neg, "new": zero}) == M.REV
    assert M.verdict({"all": zero, "old": pos, "new": zero}) == M.NONE
    assert M.verdict({"all": pos, "old": {"mean": None, "lo": None, "hi": None}, "new": zero}) == M.NONE


def test_tax_guides():
    assert abs(M.after_tax_cagr([0.1] + [0.0] * 11, [2020] * 12) - 0.1 * (1 - 0.20315)) < 1e-12
    got = M.after_tax_cagr([-0.1] + [0.0] * 11 + [0.2] + [0.0] * 11, [2020] * 12 + [2021] * 12)
    V = 0.9 * 1.2
    V -= max(0.9 * 0.2 - 0.1, 0) * 0.20315                      # 前の年の損を繰り越す
    assert abs(got - (V ** 0.5 - 1)) < 1e-12
    assert abs(M.end_tax_cagr([0.1] * 12) - ((1.1 ** 12 - (1.1 ** 12 - 1) * 0.20315) - 1)) < 1e-12


def test_analyze_and_outputs_have_no_codes():
    T = _panel(y1=1997)
    res = M.analyze(T, first=(1993, 1), last=(1997, 10))
    assert set(res["summary"]) == {"Q1", "Q2", "Q3"} and res["judge"]["Q1"]["old"]["n"] == 34
    out = {"generated_at": "x", "prereg_sha256": "0" * 64, "result": dict(res, survivorship={})}
    md, js = M.render_md(out), json.dumps(M.rounded(out), ensure_ascii=False)
    assert "7X" not in md and "7X" not in js and "J42" in md and "投資助言ではありません" in md
    v = M.verdicts_of({"summary": {"Q1": M.OK, "Q2": M.NONE, "Q3": M.REV}, "judge": res["judge"]}, "2026-10-08")
    assert set(v) == {"Q2", "Q3"} and v["Q2"]["status"] == "stop"


def test_check_has_no_returns():
    T = _panel()
    c = M.check_summary(T, len(CODES), 0, None, first=(1993, 1), last=(1997, 10))
    s = json.dumps(c, ensure_ascii=False)
    for word in ("uni", "top", "diff", "mean", "hold", "rets", "lo", "hi", "worst", "bot"):
        assert f'"{word}"' not in s, word
    assert c["eras"]["all"]["months_counted"] == 34 and 100 <= c["eras"]["all"]["universe_median"] <= 120 and "7X" not in s


def test_workflow_sync_and_verified_list():
    wf = open(".github/workflows/momentum-lab.yml", encoding="utf-8").read()
    assert "python -u momentum_lab.py --check" in wf and "options: [check, run]" in wf and "restore-keys: jp-bars-" in wf
    assert "python tests/test_momentum_lab.py" in wf and "momentum-lab.json momentum-lab.md verified-list.md" in wf
    assert '"momentum-lab.json", "momentum-lab.md"' in open("check_site_consistency.py", encoding="utf-8").read()
    assert '"momentum-lab.json"' in open("verified_list.py", encoding="utf-8").read()
    assert "momentum-lab.yml" in open("RESEARCH_LABS.md", encoding="utf-8").read()


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
