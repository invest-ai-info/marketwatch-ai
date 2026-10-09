# -*- coding: utf-8 -*-
"""J43 SQの日の朝は特別か（sq_morning_lab.py）のテスト。2026-10-09 新設。

値動きはすべて作り物。確かめること＝①事前登録と定数の一致 ②SQ の日（第2金曜日・休みなら前の取引日）と曜日
③相場全体を引いた値（その朝の中央値を引く）④行（前の日の売買代金の倍率が前の日の日足から入る）
⑤組（Q1〜Q4・SQ の日とほかの金曜日だけ・NaN は入れない）⑥判定とまとめ（両側・3つの時代・仮説どおりか）
⑦点検は損益を出さない ⑧検証済みリストに載るのは「見えない」だけ ⑨ワークフロー・SYNC 禁忌・検証済みリストへの登録。

実行:  python tests/test_sq_morning_lab.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import open30_lab as O  # noqa: E402
import sq_morning_lab as M  # noqa: E402
import test_highs_trap_lab as TL  # noqa: E402


def _o(s):
    return dt.date.fromisoformat(s).toordinal()


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "## J43 SQの日（毎月の第2金曜日）の朝は特別か" in text
    assert M.E1 == ("2006-01-04", "2016-10-31") and M.E2 == ("2016-11-01", "2023-09-29") and M.E3 == ("2023-10-10", "2026-10-05")
    assert "**E1＝2006-01-04〜2016-10-31**" in text and "**E2＝2016-11-01〜2023-09-29**" in text and "**E3＝2023-10-10〜2026-10-05**" in text
    assert M.N_Q == 12 and abs(M.ALPHA - 0.05 / 12) < 1e-12 and "99.583％の幅＝p＜0.05÷12" in text
    assert (M.TV_HIGH, M.IDIO, M.PREV_BIG, M.SQ_NTH, M.FRIDAY) == (5.0, 0.01, 0.05, 2, 4)
    assert [q[0] for q in M.QUESTIONS] == ["Q1", "Q2", "Q3", "Q4"] and [q[2] for q in M.QUESTIONS] == [-1, +1, -1, 0]
    assert "SQ の日でない金曜日" in text and "相場全体を引いた寄り→大引け" in text and "その前の取引日" in text


def test_sq_days_second_friday_and_holiday_shift():
    days = [_o(d) for d in TL._bdays("2026-01-01", 260)]
    sq = M.sq_days(days)
    assert _o("2026-10-09") in sq and sq[_o("2026-10-09")] == 10          # 2026-10-09 はその月の第2金曜日
    assert _o("2026-01-09") in sq and _o("2026-03-13") in sq and _o("2026-10-02") not in sq
    shifted = M.sq_days([d for d in days if d != _o("2026-10-09")])         # 第2金曜日が休み → 前の取引日（木曜）
    assert _o("2026-10-08") in shifted and shifted[_o("2026-10-08")] == 10 and _o("2026-10-09") not in shifted
    assert len(M.sq_days([_o("2026-10-20"), _o("2026-10-21")])) == 0         # 第2金曜日が範囲の外の月は数えない
    assert M.sq_days([]) == {}


def test_weekday_and_kind():
    assert M.weekday(_o("2026-10-09")) == 4 and M.weekday(_o("2026-10-12")) == 0
    A = np.full((3, len(M.COLS)), np.nan)
    A[:, M.C["day"]] = [_o("2026-10-09"), _o("2026-10-02"), _o("2026-10-08")]
    assert list(M.day_kind(A, {_o("2026-10-09"): 10})) == [M.KIND_SQ, M.KIND_FRI, 0]
    assert list(M.day_kind(A, {})) == [M.KIND_FRI, M.KIND_FRI, 0]


def test_adjusted_subtracts_the_morning_median():
    A = np.full((6, len(M.COLS)), np.nan)
    A[:, M.C["day"]] = [1, 1, 1, 2, 2, 2]
    A[:, M.C["rclose"]] = [0.01, 0.02, 0.06, -0.03, -0.01, 0.0]
    assert np.allclose(M.adjusted(A), [-0.01, 0.0, 0.04, -0.02, 0.0, 0.01])


def _daily(n=60, start="2016-10-03", surge_at=40):
    out = []
    for i, d in enumerate(TL._bdays(start, n)):
        o, c = 100.0, 100.0 + (0.5 if i % 2 else -0.5)
        v = 1e6 if i == surge_at else 1e5                     # 売買代金が約10倍の日
        out.append((d, o, max(o, c) + 1.0, min(o, c) - 1.0, c, v))
    return out


def test_rows_take_the_ratio_from_the_day_before():
    daily = _daily()
    A = M.stock_rows(3, daily)
    assert A.shape[1] == len(M.COLS) and (A[:, M.C["code"]] == 3).all()
    day_of = {int(r[M.C["day"]]): r for r in A}
    nxt = lambda i: _o(daily[i + 1][0])  # noqa: E731
    assert day_of[nxt(40)][M.C["tv_ratio"]] > 5 and day_of[nxt(39)][M.C["tv_ratio"]] < 2
    assert np.isnan(day_of[nxt(10)][M.C["tv_ratio"]])                                    # 20日そろう前は NaN
    assert all(dt.date.fromordinal(int(o)).isoformat() >= M.E1[0] for o in A[:, M.C["day"]])


def test_groups_only_sq_days_and_other_fridays():
    A = np.full((8, len(M.COLS)), np.nan)
    A[:, M.C["rprev"]] = [0.06, 0.0, 0.06, 0.0, 0.0, 0.0, 0.06, 0.0]
    A[:, M.C["tv_ratio"]] = [6, 1, np.nan, 6, 6, 1, 6, 6]
    idio = np.array([0.02, 0.02, 0.02, -0.02, -0.02, 0.0, 0.02, 0.02])
    kind = np.array([1, 2, 1, 1, 2, 1, 0, 2])
    assert list(M.groups("Q1", A, idio, kind)) == [0, 1, 0, -1, -1, -1, -1, 1]
    assert list(M.groups("Q2", A, idio, kind)) == [-1, -1, -1, 0, 1, -1, -1, -1]
    assert list(M.groups("Q3", A, idio, kind)) == [0, -1, 0, -1, -1, -1, -1, -1]
    assert list(M.groups("Q4", A, idio, kind)) == [0, -1, -1, 0, 1, -1, -1, 1]       # NaN（20日そろう前）は入れない
    sel = np.array([True, True, False, True, True, True, True, True])
    assert list(M.groups("Q1", A, idio, kind, sel)) == [0, 1, -1, -1, -1, -1, -1, 1]  # SQ の日を絞る（読むための表）


def test_verdict_lean_and_hypothesis():
    assert M.verdict([-1, -1, -1]) == M.SAME and M.verdict([-1, 0, -1]) == M.TWO and M.verdict([0, 0, -1]) == M.NONE
    assert M.verdict([0, 0, 0]) == M.NONE and M.verdict([-1, +1, -1]) == M.OPP and M.verdict([+1, +1, +1]) == M.SAME
    assert M.lean([-1, -1, 0]) == -1 and M.lean([+1, +1, +1]) == 1 and M.lean([0, 0, -1]) == 0 and M.lean([-1, +1, 0]) == 0
    assert M.vs_hypothesis([-1, -1, -1], -1) == "仮説どおり" and M.vs_hypothesis([+1, +1, 0], -1) == "仮説と逆"
    assert M.vs_hypothesis([-1, -1, -1], 0) == "" and M.vs_hypothesis([0, 0, 0], -1) == ""
    assert M.sign(O.DOWN) == -1 and M.sign(O.UP) == 1 and M.sign(None) == 0


def _fridays(start, end):
    d = dt.date.fromisoformat(start)
    d += dt.timedelta((4 - d.weekday()) % 7)
    out = []
    while d.isoformat() <= end:
        out.append(d)
        d += dt.timedelta(7)
    return out


def _synthetic(effect=True, n=520, seed=1):
    """金曜日だけの作り物。effect＝SQ の日だけ、高く寄った株 −1％・安く寄った株 +1％・売買代金5倍以上の株 −1％"""
    rng = np.random.default_rng(seed)
    blocks = []
    for start, end in (("2008-01-04", "2010-12-31"), ("2018-01-05", "2020-12-25"), ("2024-01-05", "2025-12-26")):
        days = _fridays(start, end)
        sq = M.sq_days([d.toordinal() for d in days])
        for d in days:
            o = d.toordinal()
            gap = rng.normal(0, 0.01, n)
            rprev = np.where(rng.uniform(size=n) < 0.2, 0.06, 0.0)
            tv = rng.choice([1.0, 6.0], size=n, p=[0.8, 0.2])
            r = rng.normal(0, 0.01, n)
            if effect and o in sq:
                idio = gap - np.median(gap)
                r = r - 0.01 * (idio >= 0.01) + 0.01 * (idio <= -0.01) - 0.01 * (tv >= 5)
            B = np.full((n, len(M.COLS)), np.nan)
            B[:, M.C["day"]], B[:, M.C["code"]], B[:, M.C["gap"]], B[:, M.C["rprev"]] = o, np.arange(n), gap, rprev
            B[:, M.C["rclose"]], B[:, M.C["turnover"]], B[:, M.C["tv_ratio"]] = r, 5.0, tv
            blocks.append(B)
    return np.vstack(blocks)


def test_analyze_finds_planted_effect_and_renders():
    res = M.analyze(_synthetic(), M.E1[0])
    j = res["judges"]
    assert all(j[q]["verdict"] == M.SAME for q in ("Q1", "Q2", "Q3", "Q4")) and res["n_same"] == 4, {q: x["verdict"] for q, x in j.items()}
    assert j["Q1"]["lean"] == -1 and j["Q1"]["vs_hypothesis"] == "仮説どおり"
    assert j["Q2"]["lean"] == +1 and j["Q2"]["vs_hypothesis"] == "仮説どおり"
    assert j["Q4"]["lean"] == -1 and j["Q4"]["vs_hypothesis"] == ""
    e3 = res["eras"]["e3"]
    assert e3["sq_days"] == 24 and e3["sq_major"] == 8 and e3["fridays"] == e3["days"] - 24
    raw = j["Q1"]["e2"]["raw"]
    assert raw["sq"]["mean"] < raw["fri"]["mean"] and raw["sq"]["net"] < raw["sq"]["mean"]
    mk = res["reading"]["e1"]["market"]
    assert mk["sq"]["days"] == res["eras"]["e1"]["sq_days"] and mk["fri"]["days"] == res["eras"]["e1"]["fridays"]
    assert set(res["reading"]["e2"]["major"]["Q1"]) == {"major", "other"}
    none = M.analyze(_synthetic(effect=False, seed=2), M.E1[0])
    assert all(x["verdict"] == M.NONE for x in none["judges"].values()), {q: x["verdict"] for q, x in none["judges"].items()}
    md = M.render_md({"generated_at": "x", "prereg_sha256": "0" * 64, "result": dict(res, n_codes=520)})
    assert "## まとめ" in md and M.SAME in md and "仮説どおり" in md and "投資助言ではありません" in md and "読むための表" in md
    assert "計算できず" in M.render_md({"generated_at": "x", "result": {"error": "e"}})


def test_verdicts_of_lists_only_unseen_questions():
    res = M.analyze(_synthetic(effect=False, seed=2), M.E1[0])
    v = M.verdicts_of(res, "2026-10-09")
    assert set(v) == {"Q1", "Q2", "Q3", "Q4"} and all(x["status"] == "stop" and x["decided_on"] == "2026-10-09" for x in v.values())
    planted = M.analyze(_synthetic(), M.E1[0])
    assert M.verdicts_of(planted, "2026-10-09") == {}


def test_check_has_no_returns():
    A = _synthetic()
    shape = {y: {"move": 100, "oc": 1, "stocks": 600} for y in range(2006, 2027)}
    out = M.check_summary(A, [], shape, 520, {"daily_range": "from:1990"})
    text = repr(out)
    assert not any(w in text for w in ("mean", "value", "diff", "net", "'win'", "rclose"))
    assert out["eras"]["e3"]["sq_days"] == 24 and set(out["eras"]["e1"]["groups"]) == {"Q1", "Q2", "Q3", "Q4"}


def test_workflow_sync_forbidden_and_verified_list():
    wf = open(".github/workflows/sq-morning-lab.yml", encoding="utf-8").read()
    assert "python -u sq_morning_lab.py --check" in wf and "restore-keys: jp-bars-" in wf
    assert "python tests/test_sq_morning_lab.py" in wf and "sq-morning-lab.json sq-morning-lab.md" in wf
    assert "options: [check, run]" in wf and "schedule:" not in wf
    assert '"sq-morning-lab.json", "sq-morning-lab.md"' in open("check_site_consistency.py", encoding="utf-8").read()
    assert '("sq-morning-lab.json", ' in open("verified_list.py", encoding="utf-8").read()


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
