# -*- coding: utf-8 -*-
"""J49 上場来高値の罠の見分け・押し目の深さ・手じまい（highs_entry_lab.py）のテスト。2026-10-28 新設。

値動きはすべて作り物。確かめること＝①事前登録と定数の一致 ②全体の指数（引けと寄り）③指値の約定（触れた日・寄りが下なら寄り）
④損切り・利確・戻り売り（同じ日に両方なら損切りが先・寄りが不利なら寄り）⑤続けて上げた本数 ⑥ケースは J48 と同じで81本の足が要る
⑦目印（急騰の点数・翌日の崩れ・5本以内の下げ）と取引の全体比 ⑧幅が仕込んだ差を見つける・判定の言葉 ⑨点検は損益を出さない・
出力に銘柄コードを出さない ⑩ワークフロー・SYNC 禁忌・検証済みリスト・研究の地図。

実行:  python tests/test_highs_entry_lab.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import highs_entry_lab as E  # noqa: E402
import highs_shape_lab as S  # noqa: E402


def weekdays(start, n):
    d, out = dt.date.fromisoformat(start), []
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.toordinal())
        d += dt.timedelta(days=1)
    return np.array(out, dtype=np.int32)


def bars(close, vol=2e6, start="2010-01-04", opens=None, highs=None, lows=None):
    c = np.asarray(close, float)
    o = np.r_[c[0], c[:-1]] if opens is None else np.asarray(opens, float)
    h = np.maximum(c, o) if highs is None else np.asarray(highs, float)
    lo = np.minimum(c, o) * 0.999 if lows is None else np.asarray(lows, float)
    v = np.full(len(c), vol)
    return weekdays(start, len(c)), np.column_stack([o, h, lo, c, v]).astype(np.float32)


def flat_market(day):
    C = np.ones(len(day))
    return E.Market(day, C, C.copy())


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    sec = text[text.index("## J49 上場来高値の「罠の見分け」"):text.index("## J50 ")]
    for s in ("**テクニカルの区切りの例外**", "**記録の日のあとに81本以上の足がある**", "J48 と同じ決め方",
              "**E1 2006-01-01〜2016-10-31／E2 2016-11-01〜2023-09-30／E3 2023-10-01〜2026-07-31**",
              "往復 0.1%", "**T1 急騰の重なり**", "**3つ以上** − 2つ以下", "**T2 翌日の崩れ**", "**T3 5本以内の大きな下げ**",
              "**T4 T1 かつ T2**", "**P1 −5%**（**予想プラス**）", "**P2 −10%**（**予想プラス**）", "**P3 −20%**（**予想マイナス**",
              "**P4 25日線**", "**X1 損切り −10%**（買値 × 0.90・**予想マイナス**）", "**X2 損切り −20%**（**予想プラス**）",
              "**X3 戻り売り −15%**", "**X4 利確 +20% と損切り −10%**（**予想マイナス**）", "**99.58%の幅**", "10,000回",
              "50件未満＝「保留」", "50%以上", "同じ日に利確と損切りの両方に届いたら損切りが先"):
        assert s in sec, s
    assert (E.NEED_AFTER, E.HOLD, E.WAIT, E.COST, E.TRAP, E.HIGH_PROB) == (81, 60, 20, 0.001, -0.10, 0.50)
    assert (E.M25_HOT, E.RET_HOT, E.TVX_HOT, E.STREAK_HOT, E.HOT_MIN, E.T3_DAYS, E.T3_DROP) == (0.20, 0.10, 3.0, 4, 3, 5, 0.10)
    assert E.P_DEPTH == {"P1": 0.05, "P2": 0.10, "P3": 0.20}
    assert E.X_RULES == {"X1": {"stop": 0.10}, "X2": {"stop": 0.20}, "X3": {"trail": 0.15}, "X4": {"stop": 0.10, "tp": 0.20}}
    assert abs(E.ALPHA - 0.05 / 12) < 1e-12 and E.N_BOOT == 10000 and len(E.QUESTIONS) == 12
    signs = {q: s for q, _, s in E.QUESTIONS}
    assert signs == {"T1": 1, "T2": 1, "T3": 1, "T4": 1, "P1": 1, "P2": 1, "P3": -1, "P4": 1, "X1": -1, "X2": 1, "X3": 1, "X4": -1}
    assert E.ERAS == S.ERAS


def test_market_index_close_and_open():
    # 2銘柄：Aは毎日 +1％（寄りは前の日の引けと同じ）、Bは毎日 −1％（寄りで −0.5％）。売買代金は十分
    n = 60
    ca = 100 * 1.01 ** np.arange(n)
    cb = 100 * 0.99 ** np.arange(n)
    ob = np.r_[cb[0], cb[:-1] * 0.995]
    s = {"A": bars(ca), "B": bars(cb, opens=ob)}
    cal = s["A"][0].astype(np.int64)
    C, O = E.market_index(s, cal)
    k = 30
    assert abs(C[k] / C[k - 1] - 1 - 0.0) < 1e-6                  # (+1％ と −1％) の平均＝0（値は float32）
    assert abs(O[k] / C[k - 1] - 1 - (-0.0025)) < 1e-6            # 寄り：(0 と −0.5％) の平均
    assert C[5] == C[0]                                            # 20本の売買代金が無い日は数えない（0）


def test_fill_limit_touch_and_gap():
    Q = np.array([100, 100, 99, 96, 90, 95.0])
    Lx = np.array([99, 99, 97, 94, 89, 94.0])
    got = E.fill_limit(Q, Lx, 0, np.full(5, 95.0))      # 足3 の安値 94 が指値 95 に触れる・寄り 96 は指値より上＝指値で
    assert got == (3, 95.0)
    got = E.fill_limit(Q, Lx, 0, np.full(5, 92.0))      # 足4 は寄り 90 が指値 92 より下＝寄りの値で
    assert got == (4, 90.0)
    assert E.fill_limit(Q, Lx, 0, np.full(5, 80.0)) is None
    assert E.fill_limit(Q, Lx, 0, np.array([np.nan, np.nan, 95.0, 95.0, 95.0])) == (3, 95.0)


def test_exits_stop_tp_and_trailing():
    n = 80
    Pi = np.full(n, 100.0)
    Q, Hx, Lx = Pi.copy(), Pi * 1.01, Pi * 0.99
    px, t = E.exit_fixed(Q, Hx, Lx, Pi, 1, 100.0, stop=0.10)
    assert (px, t) == (100.0, 60)                       # 届かない＝60本目（足 1+59）の引け
    Lx2 = Lx.copy()
    Lx2[10] = 85.0
    assert E.exit_fixed(Q, Hx, Lx2, Pi, 1, 100.0, stop=0.10) == (90.0, 10)
    Q3 = Q.copy()
    Q3[10], Lx2[10] = 80.0, 79.0                        # 寄りが損切りより下＝寄りの値で
    assert E.exit_fixed(Q3, Hx, Lx2, Pi, 1, 100.0, stop=0.10) == (80.0, 10)
    Hx2 = Hx.copy()
    Hx2[10] = 125.0                                     # 同じ日に利確と損切りの両方＝損切りが先
    assert E.exit_fixed(Q, Hx2, Lx2, Pi, 1, 100.0, stop=0.10, tp=0.20) == (90.0, 10)
    Hx2[5] = 121.0
    assert E.exit_fixed(Q, Hx2, Lx2, Pi, 1, 100.0, stop=0.10, tp=0.20) == (120.0, 5)
    # 戻り売り：終値が 100→130 に上げてから下げる。いちばん高い終値 130 × 0.85＝110.5 に届いた日に売る
    P2 = np.r_[np.full(5, 100.0), np.linspace(100, 130, 10), np.linspace(129, 100, 30), np.full(n - 45, 100.0)]
    L2 = P2 * 0.995
    px, t = E.exit_trail(P2.copy(), L2, P2, 1, 100.0, 0.15)
    assert abs(px - 130 * 0.85) < 1e-9 and P2[t - 1] > 110.5 and L2[t] <= 110.5


def test_up_streak():
    assert list(E.up_streak(np.array([1, 2, 3, 2, 3, 4, 5.0]))) == [0, 1, 2, 0, 1, 2, 3]


def _case_series(after, pre=300, jump=1.15, vol_jump=1.0):
    """300本の横ばい → 記録を作る1日（jump）→ after の値動き。売買代金は 2e8 円ほど"""
    c = np.r_[np.full(pre, 100.0), 100.0 * jump, np.asarray(after, float)]
    o = np.r_[c[0], c[:-1]]
    o[pre] = c[pre] * 0.995                             # 記録の日は高く寄ってから上げる（安値は終値の近く）
    vol = np.full(len(c), 2e6)
    vol[pre] *= vol_jump
    d, v = bars(c, opens=o)
    v[:, 4] = vol
    return d, v


def test_cases_need_81_bars_and_flags_and_excess():
    after = np.r_[np.full(100, 112.0)]                 # 記録の次の日に 112（記録の日の安値 約114.3 より下＝翌日の崩れ）
    d, v = _case_series(after, jump=1.15, vol_jump=5.0)
    mkt = flat_market(d.astype(np.int64))
    cs, short = E.stock_cases(d, v, mkt)
    assert short == 0 and len(cs) == 1
    r = cs[0]
    assert r["hot_flags"][1] and r["hot_flags"][2] and not r["hot_flags"][3]   # その日 +15％・売買代金5倍・続けて上げは1本
    assert r["t2"] is True
    # 次の日の寄り（＝記録の日の引け 115）で買い、60本目の引け 112 → 全体は横ばい
    assert abs(r["b0_raw"] - (112 / 115 - 1)) < 1e-6 and abs(r["b0"] - (112 / 115 - 1 - 0.001)) < 1e-6
    # −5％ の指値（115×0.95＝109.25）は届かない／−2.5％ は読むための表に無い＝None でない深さだけ
    assert r["p"]["0.050"] is None
    # 足りない：記録のあと80本しか無い
    d2, v2 = _case_series(np.full(80, 112.0))
    cs2, short2 = E.stock_cases(d2, v2, flat_market(d2.astype(np.int64)))
    assert cs2 == [] and short2 == 1


def test_t3_window_starts_after_the_drop():
    after = np.r_[110, 108, 102, 103, np.full(100, 103.0)]   # 3本目の終値 102 ≦ 115×0.9＝103.5
    d, v = _case_series(after)
    r = E.stock_cases(d, v, flat_market(d.astype(np.int64)))[0][0]
    t = r["t3"]["0.10"]
    assert t["flag"] is True and abs(t["x"] - (103 / 102 - 1)) < 1e-9      # 4本目の寄り（＝3本目の引け 102）から60本の引け 103
    assert r["t3"]["0.15"]["flag"] is False


def test_pullback_fill_and_market_subtraction():
    after = np.r_[114, 110, 108, np.full(100, 120.0)]   # 3本目の安値で −5％（109.25）に触れる
    d, v = _case_series(after)
    D = d.astype(np.int64)
    C = np.linspace(1.0, 1.2, len(D))
    mkt = E.Market(D, C, C.copy())
    r = E.stock_cases(d, v, mkt)[0][0]
    j = 300
    f = j + 3                                            # 3本目（寄り 110 は指値 109.25 より上＝指値で）
    exp = 120 / 109.25 - 1 - 0.001 - (C[f + 59] / C[f] - 1)
    assert abs(r["p"]["0.050"] - exp) < 1e-9


def test_band_finds_a_planted_difference_and_words():
    rng = np.random.default_rng(1)
    months = np.repeat(np.arange(120), 10)
    rows = [(int(m), float(rng.random() < 0.6), "A") for m in months] + [(int(m), float(rng.random() < 0.25), "B") for m in months]
    b = S.band_diff(rows, alpha=E.ALPHA, n_boot=2000, seed=1)
    assert b["lo"] > 0 and S.era_word(b, +1) == "予想どおり" and S.era_word(b, -1) == "逆"
    assert S.overall(["予想どおり"] * 3) == E.OK and S.overall(["予想どおり", "予想どおり", "見えない"]) == E.HALF


def _toy_cases():
    rng = np.random.default_rng(3)
    out = []
    for e, a, _ in E.ERAS:
        d0 = dt.date.fromisoformat(a).toordinal()
        for i in range(300):
            x = float(rng.normal(0, 0.1))
            out.append({"day": d0 + i * 7, "hot": int(rng.integers(0, 5)), "hot_flags": [bool(rng.random() < 0.3)] * 4,
                        "t2": bool(rng.random() < 0.3), "wick": False, "tvx": 2.0, "young": False,
                        "b0_raw": x, "b0": x - 0.001, "w_t2": x, "t3": {f"{k:.2f}": {"flag": bool(rng.random() < 0.2), "x": x} for k in E.READ_T3},
                        "p": {**{f"{dd:.3f}": (x if rng.random() < 0.5 else None) for dd in sorted(set(E.READ_DEPTHS) | set(E.P_DEPTH.values()))},
                              "ma25": x, "ma75": None},
                        "x": {q: x for q in ("X0", "X1", "X2", "X3", "X4")}, "x_hit": {q: False for q in E.X_RULES},
                        "xr": {k: x for k in [f"stop{s:.2f}" for s in E.READ_STOPS] + [f"trail{s:.2f}" for s in E.READ_TRAILS] +
                               [f"tp{s:.2f}" for s in E.READ_TPS] + [f"hold{h}" for h in E.READ_HOLDS]},
                        "mfe60": abs(x), "peak60": 10, "mfe120": None})
    return out


def test_analyze_render_and_check_have_no_codes_or_returns():
    cases = _toy_cases()
    res = E.analyze(cases, n_boot=0)
    assert set(res["questions"]) == {q for q, *_ in E.QUESTIONS}
    md = E.render_md({"generated_at": "t", "prereg_sha256": "x", "result": res})
    assert "判定" in md and "どこまで上げるか" in md and "押し目の深さ" in md
    d, v = _case_series(np.full(100, 116.0))
    s = {"9999": (d, v)}
    cs, short, mkt = E.collect(s, d.astype(np.int64))
    chk = E.check_summary(cs, short, s, mkt, 1, 0, 0, None)
    txt = str(chk)
    for k in ("b0", "mean", "diff", "mfe", "win"):
        assert k not in txt, k
    assert "9999" not in E.render_md({"generated_at": "t", "prereg_sha256": "x", "result": E.analyze(cs, n_boot=0)})


def test_workflow_sync_and_lists_are_registered():
    wf = open(".github/workflows/highs-entry-lab.yml", encoding="utf-8").read()
    for s in ("workflow_dispatch", "options: [check, run]", "restore-keys: jp-bars-", "python tests/test_highs_entry_lab.py",
              "python -u highs_entry_lab.py --check", "highs-entry-lab.json highs-entry-lab.md verified-list.md"):
        assert s in wf, s
    import check_site_consistency as C
    assert {"highs-entry-lab.json", "highs-entry-lab.md"} <= set(C.SYNC_FORBIDDEN)
    assert '"highs-entry-lab.json"' in open("verified_list.py", encoding="utf-8").read()
    assert "highs-entry-lab.yml" in open("RESEARCH_LABS.md", encoding="utf-8").read()
    assert "HIGHS_ENTRY" in open("research_map.py", encoding="utf-8").read()


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
            except Exception as e:  # noqa: BLE001
                fails += 1
                print(f"💥 {name}: {type(e).__name__}: {e}")
    sys.exit(1 if fails else 0)
