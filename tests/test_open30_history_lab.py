# -*- coding: utf-8 -*-
"""J26 J22 の目印を昔の2つの時代で確かめる（open30_history_lab.py）のテスト。2026-10-07 夜 新設。

値動きはすべて作り物。確かめること＝①事前登録と定数の一致 ②行（前の日の特徴が前の日の日足から入る）
③組（Q1〜Q4・NaN はどちらにも入れない・Q4 はふつうに寄った朝だけ）④判定とまとめ（両方の時代・逆向き）
⑤点検は損益を出さない・出力に銘柄コードを出さない ⑥ワークフローと SYNC 禁忌。

実行:  python tests/test_open30_history_lab.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import open30_history_lab as H  # noqa: E402
import open30_lab as O  # noqa: E402
import test_highs_trap_lab as TL  # noqa: E402


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "## J26 J22 の「寄りのあと下げやすい」目印は、昔の2つの時代でも同じ向きか" in text
    assert H.E1 == ("2006-01-04", "2016-10-31") and H.E2 == ("2016-11-01", "2023-09-29")
    assert "**E1＝2006-01-04〜2016-10-31**" in text and "**E2＝2016-11-01〜2023-09-29**" in text
    assert H.N_Q == 8 and abs(H.ALPHA - 0.05 / 8) < 1e-12 and "99.375％の幅＝p＜0.05÷8" in text
    assert (H.TV_HIGH, H.TV_LOW, H.IDIO) == (5.0, 2.0, 0.01)
    assert [q[0] for q in H.QUESTIONS] == ["Q1", "Q2", "Q3", "Q4"] and [q[3] for q in H.QUESTIONS] == [-1, -1, +1, -1]


def _daily(n=60, start="2016-10-03", surge_at=40, hc_at=45):
    days = TL._bdays(start, n)
    out = []
    for i, d in enumerate(days):
        o, c = 100.0, 100.0 + (0.5 if i % 2 else -0.5)
        h, lo, v = max(o, c) + 1.0, min(o, c) - 1.0, 1e5
        if i == surge_at:
            v = 1e6                                  # 売買代金が約10倍
        if i == hc_at:
            c, h = 101.0, 101.0                      # 高値引け
        out.append((d, o, h, lo, c, v))
    return out


def test_rows_take_features_from_the_day_before():
    daily = _daily()
    A = H.stock_rows(3, daily)
    assert A.shape[1] == len(H.COLS) and (A[:, H.C["code"]] == 3).all()
    day_of = {int(r[H.C["day"]]): r for r in A}
    nxt = lambda i: dt.date.fromisoformat(daily[i + 1][0]).toordinal()  # noqa: E731
    assert day_of[nxt(40)][H.C["tv_ratio"]] > 5 and day_of[nxt(39)][H.C["tv_ratio"]] < 2   # 前の日の倍率
    assert day_of[nxt(45)][H.C["hi_close"]] == 1.0 and day_of[nxt(44)][H.C["hi_close"]] == 0.0
    assert np.isnan(day_of[nxt(10)][H.C["tv_ratio"]])                                   # 20日そろう前は NaN
    assert all(dt.date.fromordinal(int(o)).isoformat() >= H.E1[0] for o in A[:, H.C["day"]])


def test_groups():
    A = np.full((6, len(H.COLS)), np.nan)
    A[:, H.C["tv_ratio"]] = [6, 1, 3, np.nan, 6, 1]
    A[:, H.C["hi_close"]] = [1, 0, 0, 1, 0, 0]
    A[:, H.C["wick"]] = [0.6, 0.1, 0.5, 0.2, 0.0, 0.9]
    idio = np.array([0.0, 0.0, 0.0, 0.0, 0.02, -0.02])
    assert list(H.groups("Q1", A, idio)) == [0, 1, -1, -1, 0, 1]
    assert list(H.groups("Q2", A, idio)) == [0, 1, 1, 0, 1, 1]
    assert list(H.groups("Q3", A, idio)) == [0, 1, 0, 1, 1, 0]
    assert list(H.groups("Q4", A, idio)) == [0, 1, -1, -1, -1, -1]                   # ふつうに寄った朝だけ


def test_verdict():
    assert H.verdict([-1, -1], -1) == H.SAME and H.verdict([-1, 0], -1) == H.ONE
    assert H.verdict([0, 0], -1) == H.NONE and H.verdict([-1, +1], -1) == H.OPP and H.verdict([+1, +1], +1) == H.SAME
    assert H.sign(O.DOWN) == -1 and H.sign(O.UP) == 1 and H.sign(None) == 0


def _synthetic(effect=True, n_days=40, n=520, seed=1):
    rng = np.random.default_rng(seed)
    rows = []
    for era, start in (("e1", "2008-03-03"), ("e2", "2018-03-01")):
        for d in TL._bdays(start, n_days):
            o = dt.date.fromisoformat(d).toordinal()
            tv = rng.choice([1.0, 6.0], size=n, p=[0.8, 0.2])
            hc = (rng.uniform(size=n) < 0.2).astype(float)
            wk = rng.uniform(size=n)
            gap = rng.normal(0, 0.004, n)
            r = rng.normal(0, 0.01, n) - (0.01 * (tv >= 5) + 0.008 * hc - 0.006 * (wk >= 0.5) if effect else 0)
            for c in range(n):
                row = np.full(len(H.COLS), np.nan)
                row[[H.C["day"], H.C["code"], H.C["gap"], H.C["rprev"], H.C["rclose"], H.C["turnover"]]] = [o, c, gap[c], 0.0, r[c], 5.0]
                row[[H.C["tv_ratio"], H.C["hi_close"], H.C["wick"]]] = [tv[c], hc[c], wk[c]]
                rows.append(row)
    return np.array(rows)


def test_analyze_finds_planted_marks_and_renders_without_codes():
    res = H.analyze(_synthetic(), H.E1[0])
    assert res["judges"]["Q1"]["verdict"] == H.SAME and res["judges"]["Q2"]["verdict"] == H.SAME
    assert res["judges"]["Q3"]["verdict"] == H.SAME and res["judges"]["Q4"]["verdict"] == H.SAME and res["n_same"] == 4
    assert res["eras"]["e1"]["days"] == 40 and res["eras"]["e2"]["days"] == 40
    g = res["judges"]["Q1"]["e1"]["group"]
    assert g["net"] < g["mean"] < 0 and 0 <= g["win"] <= 1
    none = H.analyze(_synthetic(effect=False, seed=2), H.E1[0])
    assert all(j["verdict"] in (H.NONE, H.ONE) for j in none["judges"].values()), {k: j["verdict"] for k, j in none["judges"].items()}
    md = H.render_md({"generated_at": "x", "prereg_sha256": "0" * 64, "result": dict(res, n_codes=520)})
    assert "## まとめ" in md and H.SAME in md and "投資助言ではありません" in md and "読むための表" in md
    assert "計算できず" in H.render_md({"generated_at": "x", "result": {"error": "e"}})


def test_check_has_no_returns():
    A = _synthetic()
    shape = {y: {"move": 100, "oc": 1, "stocks": 600} for y in range(2006, 2026)}
    out = H.check_summary(A, [], shape, 520, {"daily_range": "from:1990"})
    text = repr(out)
    assert not any(w in text for w in ("mean", "value", "diff", "net", "'win'")) and out["eras"]["e2"]["days"] == 40
    assert set(out["eras"]["e1"]["groups"]) == {"Q1", "Q2", "Q3", "Q4"}


def test_workflow_and_sync_forbidden():
    wf = open(".github/workflows/open30-history-lab.yml", encoding="utf-8").read()
    assert "python -u open30_history_lab.py --check" in wf and "restore-keys: jp-bars-" in wf
    assert "python tests/test_open30_history_lab.py" in wf and "open30-history-lab.json open30-history-lab.md" in wf
    assert "options: [check, run]" in wf
    assert '"open30-history-lab.json", "open30-history-lab.md"' in open("check_site_consistency.py", encoding="utf-8").read()


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
