# -*- coding: utf-8 -*-
"""J34 J31 の売りから相場全体を差し引く（market_adj_lab.py）のテスト。2026-10-08 新設。

値動きはすべて作り物。確かめること＝①事前登録と定数の一致 ②相場全体（10億円以上の平均・30銘柄未満の朝は数えない）
③差し引く前と差し引いたあとの売りの損益 ④まとめの言葉（相場全体の分だけなら ✕・その株ならではなら ✅）
⑤点検は損益を出さない・出力に銘柄コードを出さない ⑥ワークフローと SYNC 禁忌。

実行:  python tests/test_market_adj_lab.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import market_adj_lab as M  # noqa: E402


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "## J34 J31 の売りの取り分は、相場全体の下げの分か、目印の株ならではか" in text and "**目隠しではない**" in text
    assert (M.BIG, M.MIN_BIG) == (10.0, 30) and "前の日の売買代金10億円以上**の全銘柄" in text and "30銘柄未満" in text
    assert M.N_Q == 2 and abs(M.ALPHA - 0.025) < 1e-12 and "p＜0.05÷2＝97.5％" in text and abs(M.COST - 0.0003) < 1e-12
    assert [b[1] for b in M.DAY_BANDS] == [0.005, -0.005, -9.0] and "+0.5％ 以上" in text and "−0.5％ 以下" in text


def _row(day, code, gap, rc, turnover=15.0, rprev=0.0, ratio=1.0):
    r = np.full(len(M.C), np.nan)
    r[[M.C["day"], M.C["code"], M.C["gap"], M.C["rprev"], M.C["turnover"], M.C["tv_ratio"], M.C["rclose"], M.C["rhigh"], M.C["rlow"]]] = \
        [day, code, gap, rprev, turnover, ratio, rc, max(rc, 0), min(rc, 0)]
    return r


def test_market_and_nets():
    rows = [_row(1, c, 0, 0.01 * (c % 3), turnover=15.0 if c < 40 else 1.0) for c in range(60)]
    rows += [_row(2, c, 0, 0.02, turnover=15.0 if c < 20 else 1.0) for c in range(60)]       # 大きい株が20＝数えない
    A = np.array(rows)
    mk = M.market(A)
    want = np.mean([0.01 * (c % 3) for c in range(40)])
    assert np.allclose(mk[:60], want) and np.isnan(mk[60:]).all()
    raw, adj = M.nets(A, mk)
    assert abs(raw[2] - (-0.02 - M.COST)) < 1e-12 and abs(adj[2] - (-(0.02 - want) - M.COST)) < 1e-12


def _synthetic(own, mkt_drift, n=520, days_per_era=20, seed=1):
    """3つの時代。毎朝の相場全体は mkt_drift ± 0.5％。目印 B・C の株（20％）は相場全体＋own だけ動く"""
    rng = np.random.default_rng(seed)
    rows = []
    for start in ("2008-03-03", "2018-03-01", "2025-03-03"):
        d0 = dt.date.fromisoformat(start)
        days = [d for d in (d0 + dt.timedelta(i) for i in range(days_per_era * 2)) if d.weekday() < 5][:days_per_era]
        for d in days:
            m = mkt_drift + rng.normal(0, 0.005)
            up = rng.uniform(size=n) < 0.2
            gaps = np.where(up, 0.04, 0.0) + rng.normal(0, 0.002, n)
            for c in range(n):
                rc = m + (own if up[c] else 0.0) + rng.normal(0, 0.004)
                rows.append(_row(d.toordinal(), c, gaps[c], rc, rprev=0.06 if up[c] else 0.0, ratio=7.0 if up[c] else 1.0))
    return np.array(rows)


def test_summary_words():
    own = M.analyze(_synthetic(-0.01, 0.0))                     # その株ならではの下げ
    assert all(x["summary"] == M.OK_ALL for x in own["groups"].values())
    mkt_only = M.analyze(_synthetic(0.0, -0.01, seed=2))        # 相場全体が下げただけ
    g = mkt_only["groups"]["K3"]
    assert g["summary"] == M.NONE and g["eras"]["e1"]["raw"]["mean"] > 0.008
    bands = own["groups"]["K2"]["read"]["e2"]["bands"]
    assert abs(sum(b["share_days"] or 0 for b in bands.values()) - 1.0) < 1e-9
    assert own["groups"]["K2"]["read"]["e3"]["plus_years"] == (1, 1)


def test_render_and_check_have_no_codes_or_returns():
    res = M.analyze(_synthetic(-0.005, 0.0, seed=4))
    md = M.render_md({"generated_at": "x", "prereg_sha256": "0" * 64, "result": dict(res, n_codes=520)})
    assert "## まとめ" in md and "目隠しではない" in md and "投資助言ではありません" in md and "上げた日" in md and "曜日" in md
    assert "計算できず" in M.render_md({"generated_at": "x", "result": {"error": "e"}})
    out = M.check_summary(_synthetic(-0.005, 0.0, seed=5), {"daily": [], "h1": [], "m5": []}, 520, None)
    assert not any(w in repr(out) for w in ("mean", "value", "'win'")) and out["eras"]["e3"]["days_with_market"] == 20


def test_workflow_and_sync_forbidden():
    wf = open(".github/workflows/market-adj-lab.yml", encoding="utf-8").read()
    assert "python -u market_adj_lab.py --check" in wf and "restore-keys: jp-bars-" in wf
    assert "python tests/test_market_adj_lab.py" in wf and "market-adj-lab.json market-adj-lab.md" in wf and "options: [check, run]" in wf
    assert '"market-adj-lab.json", "market-adj-lab.md"' in open("check_site_consistency.py", encoding="utf-8").read()


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
