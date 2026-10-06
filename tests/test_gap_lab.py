# -*- coding: utf-8 -*-
"""J13 窓を開けて寄った株は、寄りのあとに戻されるか（gap_lab.py）のテスト。2026-10-06 夜 新設。

値動きはすべて作り物（ネットワークに出ない）。確かめること＝①事前登録と定数の一致 ②窓・穴・データの誤り・高値更新の印
③まとまりで引き直す幅（2組の差・4組の差の差）④判定の向きと言葉 ⑤出力に銘柄コードを出さない ⑥ワークフローと SYNC 禁忌。

実行:  python tests/test_gap_lab.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import gap_lab as G  # noqa: E402
import test_highs_trap_lab as TL  # noqa: E402  作り物の値段の道具を借りる


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "## J13 窓を開けて寄った株は、寄りのあとに戻されるか" in text
    assert (G.UP1, G.UP3, G.DN1, G.DN3) == (0.01, 0.03, -0.01, -0.03)
    assert "**ふつう**＝窓が −1％ より大きく +1％ より小さい" in text and "+3％ 以上" in text and "−3％ 以下" in text
    assert G.MAX_GAP_DAYS == 7 and "**7日を超える**" in text
    assert G.N_Q == 5 and abs(G.ALPHA - 0.01) < 1e-12 and "p＜0.05÷5＝99％ の幅" in text
    assert [b[0] for b in G.GAP_BANDS] == ["−5％未満", "−5〜−3％", "−3〜−1％", "−1〜+1％", "+1〜+3％", "+3〜+5％", "+5％以上"]
    assert "−5％未満／−5〜−3％／−3〜−1％／−1〜+1％／+1〜+3％／+3〜+5％／+5％以上" in text
    assert "その日が 2026-10-05 までの朝だけ" in text


def _daily():
    """60営業日の横ばい（終値 100）→ ある日に高値を更新 → 翌朝 +2％ で寄る。最後に10日の穴"""
    days = TL._bdays("2026-06-01", 75)
    daily = [(d, 100.0, 101.0, 99.0, 100.0, 1e5) for d in days]
    k = 65
    daily[k] = (days[k], 100.0, 112.0, 99.0, 108.0, 1e5)                      # 高値更新（112 ＞ 101）。翌日の高値 111 は更新しない
    daily[k + 1] = (days[k + 1], 110.16, 111.0, 107.0, 109.0, 1e5)            # 窓 +2％
    daily[k + 2] = (days[k + 2], 109.0, 120.0, 108.0, 109.0, 1e5)             # 寄りは高値・安値の内（ふつうの窓 0％）
    daily[k + 3] = (days[k + 3], 150.0, 112.0, 108.0, 110.0, 1e5)             # 寄りが高値の外＝データの誤り
    late = (dt.date.fromisoformat(days[-1]) + dt.timedelta(days=10)).isoformat()
    daily.append((late, 100.0, 101.0, 99.0, 100.0, 1e5))                     # 10日の穴のあと＝数えない
    return days, daily, k


def test_stock_rows_gap_hole_error_and_high_flag():
    days, daily, k = _daily()
    h1 = {d: TL._1h(d, [(9, row[1], row[1] * 1.001)]) for d, row in zip([r[0] for r in daily], daily)}
    A = G.stock_rows(7, daily, {}, h1, covered=lambda d: True, end_day="2026-12-31")
    by_day = {dt.date.fromordinal(int(r[G.C["day"]])).isoformat(): r for r in A}
    r = by_day[days[k + 1]]
    assert abs(r[G.C["gap"]] - (110.16 / 108 - 1)) < 1e-12 and r[G.C["hi"]] == 1 and r[G.C["code"]] == 7
    assert abs(r[G.C["r1000"]] - 0.001) < 1e-9 and np.isnan(r[G.C["r930"]])
    assert abs(r[G.C["turnover"]] - 108 * 1e5 / 1e8) < 1e-9
    assert by_day[days[k + 2]][G.C["hi"]] == 0 and abs(by_day[days[k + 2]][G.C["gap"]]) < 1e-12
    assert days[k + 3] not in by_day                                          # 寄りが高値の外
    assert daily[-1][0] not in by_day                                         # 10日の穴
    A2 = G.stock_rows(7, daily, {}, h1, covered=lambda d: False, end_day="2026-12-31")
    by2 = {dt.date.fromordinal(int(r[G.C["day"]])).isoformat(): r for r in A2}
    assert by2[days[k + 1]][G.C["hi"]] == -1                                  # 確かめられない高値更新は G5 に入れない（G1〜G4 には残る）
    A3 = G.stock_rows(7, daily, {}, h1, covered=lambda d: True, end_day=days[k])
    assert len(A3) and max(A3[:, G.C["day"]]) <= dt.date.fromisoformat(days[k]).toordinal()


def _synthetic(n_days=200, n_codes=80, gap_effect=-0.004, did_extra=0.0, seed=3):
    """作り物の行：窓 +1％ 以上の朝は寄り→10:00 が gap_effect だけ低い。高値更新の朝はさらに did_extra"""
    rng = np.random.default_rng(seed)
    rows = []
    start = dt.date(2024, 1, 4).toordinal()
    for d in range(n_days):
        mkt = rng.normal(0, 0.004)
        for c in range(n_codes):
            gap = rng.normal(0, 0.015)
            hi = 1 if rng.random() < 0.08 else 0
            r10 = mkt + rng.normal(0, 0.01) + (gap_effect if gap >= 0.01 else 0) + (did_extra if (gap >= 0.01 and hi) else 0)
            r930 = r10 * 0.7 if d > n_days - 40 else np.nan
            rows.append((start + d, c, gap, r10 * 0.5, r930, r10, r10 * 1.2, hi, 3.0))
    return np.array(rows, float)


def test_boot_two_groups_and_did():
    A = _synthetic()
    M = G.masks(A)
    grp = G.pair_grp(M["up1"], M["base"])
    q = G.safe(A, "r1000", grp, 2, G._diff2)
    assert q["lo"] < -0.004 < q["hi"] and q["hi"] < 0 and min(q["ns"]) > 1000
    assert q["lo"] == min(q["by_day"][0], q["by_stock"][0])
    g4 = G.did_grp(A, M["up1"], M["base"])
    d = G.safe(A, "r1000", g4, 4, G._did)
    assert d["lo"] < 0 < d["hi"]                                              # 高値更新ならではの差は作っていない
    d2 = G.safe(_synthetic(did_extra=-0.01), "r1000", G.did_grp(_synthetic(did_extra=-0.01), M["up1"], M["base"]), 4, G._did)
    assert d2["hi"] < 0
    pt, lo, hi = G.boot(np.array([1.0, 2.0, 3.0]), np.array([0, 1, 0]), 2, np.array([1, 1, 2]), G._diff2)
    assert pt == 0.0 and lo is None and hi is None                            # まとまりが5未満なら幅は出さない


def test_judges_both_ways():
    full = {"ns": [500, 500], "lo": -0.004, "hi": -0.001}
    e = {"diff": -0.002}
    assert G.judge_pair(full, e, e, -0.003, {"ns": [40, 40], "diff": -0.001}, "up") == G.WORDS["up"][0]
    assert G.judge_pair(full, e, e, +0.001, {"ns": [40, 40], "diff": -0.001}, "up") == "見えない"   # 費用後がプラスなら戻されやすいとは言わない
    fullp = {"ns": [500, 500], "lo": 0.001, "hi": 0.004}
    p = {"diff": 0.002}
    assert G.judge_pair(fullp, p, p, 0.001, {"ns": [40, 40], "diff": 0.001}, "down") == G.WORDS["down"][1]
    assert G.judge_pair(fullp, p, p, 0.001, {"ns": [10, 40], "diff": 0.001}, "down").startswith(G.WORDS["down"][1] + "（10:00 では兆し")
    assert G.judge_pair(fullp, p, {"diff": -0.001}, 0.001, {"ns": [40, 40], "diff": 0.001}, "down") == "見えない"
    assert G.judge_pair({"ns": [10, 500], "lo": 0.001, "hi": 0.004}, p, p, 0.001, {"ns": [40, 40], "diff": 0.001}, "down") == "件数不足"
    fd = {"ns": [100, 100, 100, 100], "lo": -0.01, "hi": -0.002}
    assert G.judge_did(fd, e, e, {"ns": [40, 40, 40, 40], "diff": -0.001}) == G.DID_WORDS[0]
    assert G.judge_did({"ns": [100] * 4, "lo": -0.01, "hi": 0.002}, e, e, {"ns": [40] * 4, "diff": -0.001}) == G.DID_WORDS[2]


def test_analyze_render_and_error_path():
    A = _synthetic(n_days=120, n_codes=50)
    res = {"generated_at": "x", "prereg_sha256": "0" * 64,
           "result": dict(G.analyze(A), n_codes=50, list_date="2026-09-30", n_missing={}, n_dropped=0)}
    r = res["result"]
    assert r["pairs"]["g1"]["verdict"] and r["g5"]["verdict"] and set(r["by_band"]) == {b[0] for b in G.GAP_BANDS}
    assert sum(b["r1000"]["n"] for b in r["by_band"].values()) == r["n_2y"]
    md = G.render_md(res)
    assert "G1 高く寄った" in md and "G5 高値更新ならではか" in md and "窓の区分ごと" in md and "投資助言ではありません" in md
    err = G.render_md({"generated_at": "x", "prereg_sha256": "", "result": {"error": "boom"}})
    assert "計算できず" in err and "## 判定" not in err
    dg = G.diag_summary(A, {"daily": [], "h1": [], "m5": []}, 50)
    assert dg["n_rows"] == len(A) and set(dg["group_n_2y"]) == {"base", "up1", "up3", "dn1", "dn3"}


def test_workflow_and_sync_forbidden():
    wf = open(".github/workflows/gap-lab.yml", encoding="utf-8").read()
    assert "python gap_lab.py --diag" in wf and "openpyxl" in wf and "xlrd" in wf
    assert "gap-lab.json gap-lab.md" in wf
    lint = open("check_site_consistency.py", encoding="utf-8").read()
    assert '"gap-lab.json", "gap-lab.md"' in lint


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
