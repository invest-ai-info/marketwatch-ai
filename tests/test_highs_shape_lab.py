# -*- coding: utf-8 -*-
"""J48 上場来高値の「形」（highs_shape_lab.py）のテスト。2026-10-27 新設。

値動きはすべて作り物。確かめること＝①事前登録と定数の一致 ②誤りの日の物差しが J42 と同じ ③ケースの決め方（記録上の最高値・
20本未満・売買代金・60本あけ）④その日の特徴（その日の上げ・25日線・引けの強さ・前の記録からの本数・じわじわ度・上場からの日数）
⑤次の日の寄り → 60本あとの引けと、同じ日の全銘柄の平均を引いた差 ⑥組と点数 ⑦幅（仕込んだ差を見つける）と判定の言葉
⑧点検は損益を出さない・出力に銘柄コードを出さない ⑨ワークフロー・SYNC 禁忌・検証済みリスト・研究の地図。

実行:  python tests/test_highs_shape_lab.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import highs_shape_lab as S  # noqa: E402
import momentum_lab as M  # noqa: E402


def weekdays(start, n):
    d, out = dt.date.fromisoformat(start), []
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.toordinal())
        d += dt.timedelta(days=1)
    return np.array(out, dtype=np.int32)


def bars(close, vol=1e6, start="2005-01-03", hi_pad=0.0, opens=None):
    """終値の列 → (日, [始, 高, 安, 終, 出来高])。高値＝終値×(1+hi_pad)・安値＝終値×0.99・始値＝前の日の終値（無ければ終値）"""
    c = np.asarray(close, float)
    n = len(c)
    o = np.r_[c[0], c[:-1]] if opens is None else np.asarray(opens, float)
    h = np.maximum(c, o) * (1 + hi_pad)
    lo = np.minimum(c, o) * 0.99
    v = np.full(n, vol) if np.isscalar(vol) else np.asarray(vol, float)
    return weekdays(start, n), np.column_stack([o, h, lo, c, v]).astype(np.float32)


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    sec = text[text.index("## J48 上場来高値の「形」"):text.index("## 共通の決まり")]
    for s in ("**テクニカルの区切りの例外**", "20本未満の日は入れない", "平均売買代金（終値×出来高）が1億円以上", "**60本たつまで新しいケースにしない**",
              "**E1 2006-01-01〜2016-10-31／E2 2016-11-01〜2023-09-30／E3 2023-10-01〜2026-07-31**",
              "**次の日の寄りで買い、60本あとの引けで売る**", "**同じ日に、売買代金1億円以上の全銘柄を同じように買った平均**",
              "250本", "**時代ごとにケースを3つに分ける（3分位）**", "2001-03-31", "**99.17%の幅**", "10,000回", "50件未満＝「保留」",
              "Q1** じわじわ度の下の3分の1 − 上の3分の1（**予想プラス**）", "Q2** 25日線から +20%以上 − +10%未満（**予想マイナス**）",
              "Q3** その日 +10%以上 − +3%未満（**予想マイナス**）", "Q4** 引けが前の記録以上 − 引けが前の記録より下",
              "Q5** 前の記録から250本以上（1年以上ぶりの更新）− 20本以内", "Q6** 上場から365暦日未満 − 1,096暦日（3年）以上",
              "**置き場で10年の足に戻った銘柄（fallback）は使わない**", "（目安 90%以上",
              "**同じ日に記録が始まる銘柄が10以上ある日**", "**記録の始まりから5年（1,826暦日）たつまではケースにしない**"):
        assert s in sec, s
    assert (S.TV_MIN, S.TV_N, S.MIN_BARS, S.GAP, S.HOLD, S.ID_N, S.MA_N) == (1e8, 20, 20, 60, 60, 250, 25)
    assert (S.YOUNG_DAYS, S.OLD_DAYS, S.FRESH, S.STREAK, S.MIN_GROUP, S.N_BOOT, S.OLD_RECORD) == (365, 1096, 250, 20, 50, 10000, dt.date(2001, 3, 31))
    assert (S.CLUSTER_N, S.TRUNC_DAYS) == (10, 1826)
    assert abs(S.ALPHA - 0.05 / 6) < 1e-12 and [e for e, *_ in S.ERAS] == ["E1", "E2", "E3"]
    assert [(q, s) for q, _, s in S.QUESTIONS] == [("Q1", 1), ("Q2", -1), ("Q3", -1), ("Q4", 1), ("Q5", 1), ("Q6", -1)]
    assert S.ERAS[0][1:] == ("2006-01-01", "2016-10-31") and S.ERAS[2][1:] == ("2023-10-01", "2026-07-31")


def test_bad_days_use_the_same_ruler_as_j42():
    day, v = bars(np.r_[np.full(30, 100.0), [300.0], np.full(10, 300.0)])   # 3倍の跳び（分割の取りこぼし）
    o, h, lo, c = (v[:, i].astype(float) for i in range(4))
    g = S.good_days(day, o, h, lo, c)
    _, _, _, zeroed = M.clean_index(day, o, h, lo, c)
    assert (~g[1:]).sum() == zeroed and not g[30]


def test_case_rules_record_min_bars_turnover_and_gap():
    # 300本の横ばい（100円）→ 301本目から毎日 +0.5％で上げ続ける。出来高 200万株×100円＝2億円
    c = np.r_[np.full(300, 100.0), 100.0 * 1.005 ** np.arange(1, 201)]
    day, v = bars(c, vol=2e6)
    cases, _ = S.stock_cases(day, v)
    js = [int(np.searchsorted(day, r["day"])) for r in cases]
    assert js[0] == 300 and all(b - a == S.GAP for a, b in zip(js, js[1:]))     # 最初の記録の日・60本ずつ
    first = cases[0]
    assert first["since_prev"] == 300          # 前の記録＝その高値を初めて付けた足（横ばいで並んだ足は数えない）
    assert abs(first["ret1"] - 0.005) < 1e-6 and first["close_vs_rec"] > 0
    # 売買代金が足りない（出来高 30万株×最高でも約270円＝8,000万円）＝ケースなし
    day2, v2 = bars(c, vol=3e5)
    assert S.stock_cases(day2, v2)[0] == []
    # 20本未満の記録の更新は入れない
    day3, v3 = bars(100.0 * 1.01 ** np.arange(60), vol=2e6)
    cs3, _ = S.stock_cases(day3, v3)
    assert cs3 and int(np.searchsorted(day3, cs3[0]["day"])) >= S.MIN_BARS


def test_since_prev_counts_bars_from_the_last_record():
    # 100本で 100→150 に上げ、30本下げて戻り、131本目に前の記録を抜ける
    up = np.linspace(100, 150, 100)
    c = np.r_[up, np.full(30, 140.0), [152.0], np.full(70, 152.0)]
    day, v = bars(c, vol=np.r_[np.full(100, 1e5), np.full(101, 2e6)])   # 上げの間は売買代金が足りない＝ケースにならない
    cs, _ = S.stock_cases(day, v)
    r = [x for x in cs if int(np.searchsorted(day, x["day"])) == 130]
    assert r and r[0]["since_prev"] == 31          # 前の記録＝99本目（150円）→ 130本目
    assert abs(r[0]["close_vs_rec"] - (152 / 150 - 1)) < 1e-3


def test_smooth_rise_has_lower_id_than_jumpy_rise():
    smooth = 100.0 * 1.002 ** np.arange(400)                    # 毎日少しずつ
    steps = np.ones(400)
    steps[::40] = 1.08                                           # 40本ごとに +8％・ほかは −0.1％
    steps[np.arange(400) % 40 != 0] = 0.999
    jumpy = 100.0 * np.cumprod(steps)
    ids = []
    for c in (smooth, jumpy):
        day, v = bars(c, vol=2e6)
        cs, _ = S.stock_cases(day, v)
        ids.append([r["id"] for r in cs if r["id"] is not None][-1])
    assert ids[0] < 0 < ids[1], ids


def test_forward_return_is_next_open_to_close_and_market_is_subtracted():
    n = 400
    c1 = np.r_[np.full(300, 100.0), np.linspace(101, 200, 100)]
    c2 = np.full(n, 50.0)                                        # 動かない株（全体の平均を下げる）
    s = {"A": bars(c1, vol=2e6), "B": bars(c2, vol=4e6)}
    cases = S.collect(s, s["A"][0])
    r = cases[0]
    j = int(np.searchsorted(s["A"][0], r["day"]))
    raw = c1[j + S.HOLD] / c1[j] - 1                             # 次の日の寄り＝その日の引け（作り物の始値）
    assert abs(r["r60"] - raw) < 1e-4
    assert abs(r["x60"] - (raw - (raw + 0.0) / 2)) < 1e-4       # 全体＝A と B の平均（B は0）


def test_young_record_gets_age_and_old_record_does_not():
    c = np.r_[np.full(40, 100.0), np.linspace(101, 130, 60)]
    d_new, v_new = bars(c, vol=2e6, start="2015-04-01")
    assert S.stock_cases(d_new, v_new)[0][0]["age"] is not None
    c_long = np.r_[np.full(40, 100.0), np.linspace(101, 300, 1400)]
    d_old, v_old = bars(c_long, vol=2e6, start="2001-01-04")
    cs = S.stock_cases(d_old, v_old)[0]
    assert cs and all(r["age"] is None for r in cs) and dt.date.fromordinal(cs[0]["day"]) >= dt.date(2006, 1, 4)


def test_record_starting_on_a_shared_date_is_not_a_listing():
    c = np.r_[np.full(40, 100.0), np.linspace(101, 130, 1400)]
    day, v = bars(c, vol=2e6, start="2010-02-22")
    s = {f"{i:04d}": (day, v) for i in range(S.CLUSTER_N)}            # 10銘柄が同じ日に始まる＝記録の始まり
    assert S.cluster_starts(s) == {int(day[0]): S.CLUSTER_N}
    cs, _ = S.stock_cases(day, v, clusters={int(day[0])})
    assert cs and all(r["age"] is None for r in cs)
    assert all(r["day"] - int(day[0]) >= S.TRUNC_DAYS for r in cs)     # 5年たつまではケースにしない
    cs2, _ = S.stock_cases(day, v)                                     # ひとりで始まる＝上場の日
    assert cs2[0]["age"] is not None and int(np.searchsorted(day, cs2[0]["day"])) == 40


def test_groups_and_score():
    base = {"id": -0.2, "m25": 0.05, "ret1": 0.01, "close_vs_rec": 0.01, "since_prev": 300, "age": None}
    g = S.groups(base, (-0.1, 0.0))
    assert g == {"Q1": "A", "Q2": "B", "Q3": "B", "Q4": "A", "Q5": "A", "Q6": "B"} and S.score(g) == 6
    bad = {"id": 0.3, "m25": 0.25, "ret1": 0.12, "close_vs_rec": -0.01, "since_prev": 5, "age": 100}
    g2 = S.groups(bad, (-0.1, 0.0))
    assert g2 == {"Q1": "B", "Q2": "A", "Q3": "A", "Q4": "B", "Q5": "B", "Q6": "A"} and S.score(g2) == 0
    mid = dict(base, id=-0.05, m25=0.15, ret1=0.05, since_prev=100, age=500)
    assert {q: v for q, v in S.groups(mid, (-0.1, 0.0)).items() if v} == {"Q4": "A"}


def test_band_finds_a_planted_difference_and_words_follow_the_prereg():
    rng = np.random.default_rng(1)
    rows = [(m, rng.normal(0.05, 0.1), "A") for m in range(60) for _ in range(5)]
    rows += [(m, rng.normal(0.0, 0.1), "B") for m in range(60) for _ in range(5)]
    b = S.band_diff(rows, n_boot=2000)
    assert b["lo"] > 0 and abs(b["diff"] - 0.05) < 0.02 and b["n_a"] == 300
    assert S.era_word(b, +1) == "予想どおり" and S.era_word(b, -1) == "逆"
    assert S.band_diff(rows, n_boot=0)["lo"] is None
    small = dict(b, n_a=49)
    assert S.era_word(small, +1) == S.HOLD_V
    w = "予想どおり"
    assert S.overall([w, w, w]) == S.OK and S.overall([w, w, "見えない"]) == S.HALF and S.overall([w, w, "逆"]) == S.HALF
    assert S.overall([w, "見えない", "逆"]) == S.REV and S.overall(["見えない"] * 3) == S.NONE
    assert S.overall([w, w, S.HOLD_V]) == S.HALF and S.overall([w, S.HOLD_V, "逆"]) == S.HOLD_V


def test_check_has_no_returns_and_outputs_have_no_codes():
    c = np.r_[np.full(300, 100.0), 100.0 * 1.005 ** np.arange(1, 201)]
    s = {"9999": bars(c, vol=2e6, start="2015-01-05")}
    cases = S.collect(s, s["9999"][0])
    chk = S.check_summary(cases, s, 1, 0, 0, None)
    txt = str(chk)
    for k in ("x60", "r60", "mean", "diff"):
        assert k not in txt, k
    res = {"generated_at": "t", "prereg_sha256": "x", "result": S.analyze(cases, n_boot=0)}
    md = S.render_md(res)
    assert "9999" not in md and "判定" in md


def test_workflow_sync_and_lists_are_registered():
    wf = open(".github/workflows/highs-shape-lab.yml", encoding="utf-8").read()
    for s in ("workflow_dispatch", "options: [check, run]", "restore-keys: jp-bars-", "python tests/test_highs_shape_lab.py",
              "python -u highs_shape_lab.py --check", "highs-shape-lab.json highs-shape-lab.md verified-list.md"):
        assert s in wf, s
    import check_site_consistency as C
    assert {"highs-shape-lab.json", "highs-shape-lab.md"} <= set(C.SYNC_FORBIDDEN)
    assert '"highs-shape-lab.json"' in open("verified_list.py", encoding="utf-8").read()
    assert "highs-shape-lab.yml" in open("RESEARCH_LABS.md", encoding="utf-8").read()
    assert "HIGHS_SHAPE" in open("research_map.py", encoding="utf-8").read()


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
