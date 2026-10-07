# -*- coding: utf-8 -*-
"""J18 これまでの目印を3つ目の期間（2006〜2016年）で確かめる（third_period_lab.py）のテスト。2026-10-07 新設。

値動きはすべて作り物。確かめること＝①事前登録と定数の一致 ②使える年（始値の欠けの疑い・銘柄の少ない朝・いちばん新しい使えない年の翌年から）
③組（P1〜P7）④判定（元と同じ向き＝✅・逆向き＝⚠️・見えない）⑤出力に銘柄コードを出さない・点検は損益を出さない ⑥ワークフローと SYNC 禁忌。

実行:  python tests/test_third_period_lab.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import prevday_lab as PD  # noqa: E402
import third_period_lab as M  # noqa: E402


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "## J18 これまでの目印を、まだ使っていない3つ目の期間（2006〜2016年）で確かめる" in text
    assert M.SPAN == ("2006-01-04", "2016-10-31") and "2006-01-04 から" in text and "2016-10-31 まで" in text
    assert M.REF_YEARS == tuple(range(2017, 2026)) and "2017〜2025年" in text
    assert (M.OC_RATIO, M.THIN_SHARE, M.MIN_STOCKS, M.IDIO) == (2.0, 0.5, 500, 0.01) and "平均の2倍を超える" in text
    assert M.N_Q == 7 and abs(M.ALPHA - 0.05 / 7) < 1e-12 and "p＜0.05÷7＝99.29％ の幅" in text
    assert [j[3] for j in M.JUDGES] == [-1, +1, -1, -1, -1, -1, +1]
    import jp_bars
    assert jp_bars.SPECS[0] == ("1d", (jp_bars.FULL_DAILY, "10y")) and jp_bars.DAILY_MAX_SPACING == 5 and "間隔の中央値が5日を超えたら" in text


def _shape(oc=None):
    """年ごとの形（基準の年は始値＝終値の割合 1％）"""
    sh = {y: {"move": 1000, "oc": 10, "stocks": 3000} for y in range(2006, 2026)}
    for y, n in (oc or {}).items():
        sh[y]["oc"] = n
    return sh


def test_usable_start_rule():
    thin = {y: 0.0 for y in range(2006, 2017)}
    u = M.usable_start(_shape(), thin)
    assert u["start"] == "2006-01-04" and u["bad_years"] == [] and abs(u["ref_oc"] - 0.01) < 1e-12
    u = M.usable_start(_shape({2007: 25, 2009: 21}), thin)              # 2.5％・2.1％＞2％＝使えない
    assert u["bad_years"] == [2007, 2009] and u["start"] == "2010-01-01" and u["years"][2007]["bad"] == ["始値の欠けの疑い"]
    assert M.usable_start(_shape({2008: 20}), thin)["start"] == "2006-01-04"      # ちょうど2倍は使える
    u = M.usable_start(_shape(), {**thin, 2011: 0.6})
    assert u["start"] == "2012-01-01" and u["years"][2011]["bad"] == ["銘柄の少ない朝"]
    assert M.usable_start(_shape(), {**thin, 2016: 0.9})["start"] is None
    sh = _shape()
    del sh[2006]
    assert M.usable_start(sh, thin)["start"] == "2007-01-01"                       # データの無い年も使えない


def test_add_shape_and_thin_by_year():
    sh = {}
    M.add_shape(sh, [("2007-01-04", 100, 101, 99, 100, 10), ("2007-01-05", 100, 101, 99, 101, 10),
                     ("2007-01-09", 100, 100, 100, 100, 10), ("2008-01-04", 100, 102, 99, 101, 0)])
    assert sh == {2007: {"move": 2, "oc": 1, "stocks": 1}}
    d = dt.date(2008, 1, 7).toordinal()
    A = np.zeros((600 + 100, len(PD.COLS)))
    A[:600, PD.C["day"]] = d
    A[600:, PD.C["day"]] = d + 1
    assert M.thin_by_year(A) == {2008: 0.5}


def test_groups():
    idio = np.array([0.02, 0.0, -0.02, 0.02, -0.02, -0.02, 0.0])
    rp = np.array([0.0, 0.0, 0.0, 0.06, 0.06, -0.06, 0.06])
    A = np.zeros((len(idio), len(PD.COLS)))
    A[:, PD.C["rprev"]] = rp
    A[:, PD.C["gap"]] = [0.02, 0.0, -0.02, 0.02, -0.02, -0.02, 0.005]
    assert list(M.groups("p1", A, idio)) == [0, 1, -1, 0, -1, -1, 1]
    assert list(M.groups("p2", A, idio)) == [-1, 1, 0, -1, 0, 0, 1]
    assert list(M.groups("p3", A, idio)) == [-1, 1, -1, -1, -1, -1, 0]
    assert list(M.groups("p4", A, idio)) == [1, -1, -1, 0, -1, -1, -1]
    assert list(M.groups("p6", A, idio)) == [-1, -1, 1, -1, 0, -1, -1]
    assert list(M.groups("p7", A, idio)) == [-1, -1, 1, -1, -1, 0, -1]


def _rows(n_days=200, n_codes=600, start="2010-01-04", seed=1, sign=1.0):
    """元の向きの効き方（sign=−1 で全部逆向き）"""
    rng = np.random.default_rng(seed)
    d0 = dt.date.fromisoformat(start).toordinal()
    out = []
    for d in range(n_days):
        mkt_gap, mkt = rng.normal(0, 0.003), rng.normal(0, 0.004)
        idio = rng.choice([0.02, 0.0, -0.02, 0.005], size=n_codes)
        rp = rng.choice([0.07, 0.0, 0.01, -0.07, 0.03], size=n_codes)
        noise = rng.normal(0, 0.008, size=n_codes)
        for c in range(n_codes):
            up, dn, big, bigdn = idio[c] >= 0.01, idio[c] <= -0.01, rp[c] >= 0.05, rp[c] <= -0.05
            e = (-0.004 if up else 0) + (0.004 if dn else 0) + (-0.004 if big and not dn else 0) + (-0.006 if big and dn else 0)
            e += 0.004 if bigdn and dn else 0
            r = mkt + noise[c] + sign * e
            out.append((d0 + d, c, mkt_gap + idio[c], rp[c], r, np.nan, np.nan, 3.0))
    return np.array(out, float)


def test_replicate_same_opposite_and_render():
    res = M.analyze(_rows(), "2010-01-01")
    assert all(res["judges"][k]["replicate"] == M.SAME for k, *_ in M.JUDGES), {k: res["judges"][k]["verdict"] for k, *_ in M.JUDGES}
    assert res["n_same"] == 6
    rev = M.analyze(_rows(sign=-1.0, seed=2), "2010-01-01")
    assert rev["judges"]["p1"]["replicate"] == M.OPP and rev["judges"]["p2"]["replicate"] == M.OPP
    assert M.replicate(PD.NONE, -1) == M.NONE and M.replicate(PD.DOWN + "（…）", -1) == M.SAME
    u = M.usable_start(_shape(), {y: 0.0 for y in range(2006, 2017)})
    out = {"generated_at": "x", "prereg_sha256": "0" * 64, "price_store": {"built_at": "b", "daily_range": "from:1990", "fallback": {"1d": 3}},
           "result": dict(res, usable=u, n_codes=600, list_date="2026-09-30", n_missing=0, n_dropped=0)}
    md = M.render_md(out)
    assert "## まとめ" in md and "6／6" in md and "P7 その銘柄だけ安く寄った朝" in md and "投資助言ではありません" in md
    assert "計算できず" in M.render_md({"generated_at": "x", "prereg_sha256": "", "result": {"error": "e"}})


def test_check_summary_has_no_returns():
    A = _rows(n_days=20)
    sh = _shape()
    out = M.check_summary(A, [], sh, 600, {"daily_range": "from:1990"})
    keys = set(out) | {k for y in out["years"].values() for k in y}
    assert not any(w in " ".join(map(str, keys)) for w in ("diff", "mean", "rclose", "judge"))
    assert out["years"]["2010"]["stocks"] == 3000 and out["years"]["2010"]["thin_share"] == 0.0
    assert out["usable_start"] is None and out["years"]["2016"]["bad"] == ["銘柄の少ない朝"]     # 朝の無い年＝銘柄の少ない朝


def test_workflow_and_sync_forbidden():
    wf = open(".github/workflows/third-period-lab.yml", encoding="utf-8").read()
    assert "python -u third_period_lab.py --check" in wf and "restore-keys: jp-bars-" in wf
    assert "third-period-lab.json third-period-lab.md" in wf and "options: [check, run]" in wf
    assert '"third-period-lab.json", "third-period-lab.md"' in open("check_site_consistency.py", encoding="utf-8").read()


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
