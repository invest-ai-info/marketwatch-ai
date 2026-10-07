# -*- coding: utf-8 -*-
"""J15 窓の戻しは「その銘柄だけの窓」か「相場全体の窓」か（gap_split_lab.py）のテスト。2026-10-07 新設。

値動きはすべて作り物。確かめること＝①事前登録と定数の一致 ②相場全体の窓＝その朝の中央値・銘柄が少ない朝は除く
③K1〜K4 の組の作り方 ④作った効果を正しい組で拾う ⑤出力に銘柄コードを出さない ⑥ワークフローと SYNC 禁忌。

実行:  python tests/test_gap_split_lab.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import gap_lab as GL  # noqa: E402
import gap_split_lab as K  # noqa: E402


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "## J15 窓の戻しは「その銘柄だけの窓」か「相場全体の窓」か" in text
    assert K.IDIO == 0.01 and K.MKT == 0.005 and K.MIN_STOCKS == 500 and "500未満" in text
    assert K.N_Q == 4 and abs(K.ALPHA - 0.0125) < 1e-12 and "p＜0.05÷4＝98.75％ の幅" in text


def _rows(n_days=160, n_codes=520, idio_eff=-0.004, mkt_eff=0.0, seed=1, small_day=False):
    """作り物の行（gap_lab の列の並び）。その銘柄だけの窓 +1％ 以上は寄り→10:00 が idio_eff だけ低い・相場全体 +0.5％ 以上の朝は mkt_eff"""
    rng = np.random.default_rng(seed)
    d0 = dt.date(2024, 1, 4).toordinal()
    out = []
    for d in range(n_days):
        m = rng.normal(0, 0.006)
        n = 100 if (small_day and d == 0) else n_codes
        for c in range(n):
            own = rng.normal(0, 0.012)
            gap = m + own
            r = rng.normal(0, 0.01) + (idio_eff if own >= 0.01 else 0) + (mkt_eff if m >= 0.005 else 0)
            r930 = r * 0.8 if d >= n_days - 40 else np.nan
            out.append((d0 + d, c, gap, r * 0.5, r930, r, r * 1.1, 0, 3.0))
    return np.array(out, float)


def test_split_uses_daily_median_and_drops_thin_mornings():
    A = _rows(n_days=3, small_day=True)
    B, mkt, idio = K.split(A)
    assert len(B) == 2 * 520                                      # 100銘柄しかない朝は数えない
    d = B[:, GL.C["day"]] == B[0, GL.C["day"]]
    assert abs(mkt[d][0] - np.median(B[d, GL.C["gap"]])) < 1e-12 and np.allclose(idio, B[:, GL.C["gap"]] - mkt)


def test_groups_and_effects_land_where_made():
    A = _rows(idio_eff=-0.004, mkt_eff=0.0)
    res = K.analyze(A)
    assert res["judges"]["k1"]["all"]["hi"] < 0 and res["judges"]["k1"]["verdict"].startswith(GL.WORDS["up"][0])
    assert res["judges"]["k3"]["verdict"] in ("見えない", "件数不足") or res["judges"]["k3"]["all"]["lo"] < 0 < res["judges"]["k3"]["all"]["hi"]
    A2 = _rows(idio_eff=0.0, mkt_eff=-0.004, seed=2)
    r2 = K.analyze(A2)
    assert r2["judges"]["k3"]["all"]["hi"] < 0 and r2["judges"]["k1"]["all"]["lo"] < 0 < r2["judges"]["k1"]["all"]["hi"]
    g = K.groups(np.array([0.0, 0.0, 0.006, -0.006]), np.array([0.02, 0.0, 0.0, 0.0]))
    assert list(g["k1"]) == [0, 1, 1, 1] and list(g["k3"]) == [-1, 1, 0, -1] and list(g["k4"]) == [-1, 1, -1, 0]


def test_render_no_codes_and_error():
    A = _rows(n_days=60, seed=3)
    res = {"generated_at": "x", "prereg_sha256": "0" * 64, "price_store": {"built_at": "b"},
           "result": dict(K.analyze(A), n_codes=520, list_date="2026-09-30", n_missing={}, n_dropped=0)}
    md = K.render_md(res)
    assert "K1 その銘柄だけの窓" in md and "相場全体の窓 × その銘柄だけの窓" in md and "投資助言ではありません" in md
    assert "計算できず" in K.render_md({"generated_at": "x", "prereg_sha256": "", "result": {"error": "e"}})
    dg = K.diag_summary(A, {"daily": [], "h1": [], "m5": []}, 520)
    assert dg["rows_used"] == len(A) and set(dg["sizes_2y"]) == {"k1", "k2", "k3", "k4"}


def test_workflow_and_sync_forbidden():
    wf = open(".github/workflows/gap-split-lab.yml", encoding="utf-8").read()
    assert "python gap_split_lab.py --diag" in wf and "restore-keys: jp-bars-" in wf and "gap-split-lab.json gap-split-lab.md" in wf
    assert '"gap-split-lab.json", "gap-split-lab.md"' in open("check_site_consistency.py", encoding="utf-8").read()


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
