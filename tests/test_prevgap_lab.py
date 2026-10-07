# -*- coding: utf-8 -*-
"""J17 2つの目印を重ねると足し算になるか（prevgap_lab.py）のテスト。2026-10-07 新設。

値動きはすべて作り物。確かめること＝①事前登録と定数の一致 ②その銘柄だけの窓（その朝の中央値を引く・500銘柄未満の朝は除く）
③組（N1〜N3 の先の組と比べる相手）④判定とまとめ（重なると弱い・ぶつかると打ち消す／効かない目印は見えない）
⑤出力に銘柄コードを出さない・件数30未満は「—」 ⑥ワークフローと SYNC 禁忌。

実行:  python tests/test_prevgap_lab.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import prevday_lab as PD  # noqa: E402
import prevgap_lab as M  # noqa: E402


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "## J17 2つの目印を重ねると足し算になるか" in text
    assert M.OLD == PD.OLD == ("2016-11-01", "2023-09-29") and M.NEW == PD.NEW
    assert (M.IDIO, M.PREV_BIG, M.PREV_FLAT, M.MIN_STOCKS) == (0.01, 0.05, 0.02, 500)
    assert M.N_Q == 6 and abs(M.ALPHA - 0.05 / 6) < 1e-12 and "p＜0.05÷6＝99.17％ の幅" in text
    assert "500未満なら" in text and "+1％ 以上" in text and "−2％ より大きく +2％ より小さい" in text


def _A(rows):
    """(day, code, gap, rprev, rclose, r1000, r930, turnover)"""
    return np.array(rows, float).reshape(-1, len(PD.COLS))


def test_idio_gap_subtracts_the_morning_median_and_drops_thin_mornings():
    rows = [(1, c, 0.02 + (0.03 if c == 0 else 0.0), 0.0, 0, 0, 0, 1) for c in range(600)]       # 中央値 +2％
    rows += [(2, c, 0.0, 0.0, 0, 0, 0, 1) for c in range(100)]                                      # 100銘柄の朝＝除く
    B, idio = M.idio_gap(_A(rows))
    assert len(B) == 600 and set(B[:, PD.C["day"]]) == {1}
    assert abs(idio[0] - 0.03) < 1e-12 and np.allclose(idio[1:], 0)


def test_groups():
    idio = np.array([0.02, 0.02, 0.0, -0.02, -0.02, 0.02, 0.0, 0.02])
    rp = np.array([0.06, 0.0, 0.06, 0.06, 0.01, 0.03, 0.0, -0.06])
    assert list(M.groups(idio, rp, "n1")) == [0, 1, -1, -1, -1, -1, -1, -1]
    assert list(M.groups(idio, rp, "n2")) == [0, -1, 1, -1, -1, -1, -1, -1]
    assert list(M.groups(idio, rp, "n3")) == [-1, -1, -1, 0, 1, -1, -1, -1]


def _rows(n_days=260, n_codes=600, start="2017-01-04", seed=1, prev_eff=-0.004, gap_eff=-0.004, clash_eff=-0.006, with_new=True):
    """前の日 +5％以上で −0.4％・その銘柄だけ高く寄ると −0.4％（足し算）・安く寄った朝の前日上げは −0.6％（戻りを打ち消す）"""
    rng = np.random.default_rng(seed)
    d0 = dt.date.fromisoformat(start).toordinal()
    out = []
    for d in range(n_days):
        mkt_gap, mkt = rng.normal(0, 0.003), rng.normal(0, 0.004)
        idio = rng.choice([0.02, 0.0, -0.02, 0.005], size=n_codes)
        rp = rng.choice([0.07, 0.0, 0.01, -0.07, 0.03], size=n_codes)
        noise = rng.normal(0, 0.008, size=n_codes)
        for c in range(n_codes):
            big = rp[c] >= 0.05
            r = mkt + noise[c] + (gap_eff if idio[c] >= 0.01 else 0) + (+0.003 if idio[c] <= -0.01 else 0)
            r += (prev_eff if big and idio[c] > -0.01 else 0) + (clash_eff if big and idio[c] <= -0.01 else 0)
            out.append((d0 + d, c, mkt_gap + idio[c], rp[c], r, r if with_new else np.nan, r * 0.9 if with_new else np.nan, 3.0))
    return np.array(out, float)


def test_judge_and_summary():
    A = np.vstack([_rows(start="2017-01-04"), _rows(start="2024-01-04", seed=2)])
    res = M.analyze(A)
    J = res["judges"]
    for k in ("n1", "n2", "n3"):
        assert J[k]["verdict"] == PD.DOWN, (k, J[k]["verdict"], J[k]["diff"], J[k]["lo"], J[k]["hi"])
    for k in ("n4", "n5", "n6"):
        assert J[k]["verdict"].startswith(PD.DOWN), (k, J[k]["verdict"])
    assert all(res["summary"][k]["verdict"].startswith(PD.BOTH) for k in ("n1", "n2", "n3"))
    assert abs(res["extra"]["old"]) < 0.002                       # 作り物は足し算＝上乗せはほぼ0
    B = np.vstack([_rows(start="2017-01-04", prev_eff=0, clash_eff=0), _rows(start="2024-01-04", seed=2, prev_eff=0, clash_eff=0)])
    rb = M.analyze(B)
    assert rb["summary"]["n1"]["verdict"] == PD.NONE and rb["summary"]["n3"]["verdict"] == PD.NONE
    assert rb["summary"]["n2"]["verdict"].startswith(PD.BOTH)      # 窓だけ効く


def test_render_no_codes_and_thin_cells_and_error():
    A = np.vstack([_rows(n_days=60, start="2018-01-04"), _rows(n_days=40, start="2025-01-06", seed=3)])
    res = {"generated_at": "x", "prereg_sha256": "0" * 64, "price_store": {"built_at": "b"},
           "result": dict(M.analyze(A), n_codes=600, list_date="2026-09-30", n_missing={}, n_dropped=0)}
    md = M.render_md(res)
    assert "## まとめ" in md and "N1 その銘柄だけ高く寄った朝" in md and "投資助言ではありません" in md and "重なりの上乗せ" in md
    assert "計算できず" in M.render_md({"generated_at": "x", "prereg_sha256": "", "result": {"error": "e"}})
    assert M._m(np.ones(29))["mean"] is None and M._m(np.ones(30))["mean"] == 1.0
    dg = M.diag_summary(A, {"daily": [], "h1": [], "m5": []}, 600)
    assert dg["rows_kept"] == len(A) and "sizes_930" in dg["n4"]


def test_workflow_and_sync_forbidden():
    wf = open(".github/workflows/prevgap-lab.yml", encoding="utf-8").read()
    assert "python prevgap_lab.py --diag" in wf and "restore-keys: jp-bars-" in wf and "prevgap-lab.json prevgap-lab.md" in wf
    assert '"prevgap-lab.json", "prevgap-lab.md"' in open("check_site_consistency.py", encoding="utf-8").read()


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
