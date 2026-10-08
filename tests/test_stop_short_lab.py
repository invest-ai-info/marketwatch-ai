# -*- coding: utf-8 -*-
"""J32 J31 の売りに損切りを置く（stop_short_lab.py）のテスト。2026-10-08 新設。

値動きはすべて作り物。確かめること＝①事前登録と定数の一致 ②損切りの損益（届いたら損切りの値＋滑り・届かなければ大引け・費用）
③上位3銘柄の選び方 ④1日ごとの落ち込みの数字 ⑤まとめの言葉 ⑥点検は損益を出さない・出力に銘柄コードを出さない
⑦ワークフローと SYNC 禁忌。

実行:  python tests/test_stop_short_lab.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import stop_short_lab as S  # noqa: E402


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "## J32 J31 の売り（目印 B・C・板寄せどうし）に損切りを置くと、成績と落ち込みはどう変わるか" in text
    assert S.STOPS == (0.03, 0.05, 0.10) and "**+3％・+5％・+10％**" in text
    assert S.SLIP == 0.002 and "**さらに 0.2％ 不利**" in text and abs(S.COST - 0.0003) < 1e-12
    assert S.N_Q == 6 and abs(S.ALPHA - 0.05 / 6) < 1e-12 and "99.17％ の幅" in text and S.POP == 10.0
    assert S.TOP == 3 and "**上位3銘柄だけ**" in text and S.RUN_DAYS == 20 and "連続20営業日" in text
    assert "`stop_short_lab.py`" in text and os.path.exists("stop_lab.py")          # 既存の損切りラボとは別のファイル


def _row(day, code, gap, rc, rhigh, turnover=15.0, rprev=0.0, ratio=1.0):
    r = np.full(len(S.C), np.nan)
    r[[S.C["day"], S.C["code"], S.C["gap"], S.C["rprev"], S.C["turnover"], S.C["tv_ratio"], S.C["rclose"], S.C["rhigh"], S.C["rlow"]]] = \
        [day, code, gap, rprev, turnover, ratio, rc, rhigh, min(rc, 0) - 0.01]
    return r


def test_net_with_and_without_stop():
    A = np.array([_row(1, 0, 0.02, -0.02, 0.01), _row(1, 1, 0.02, 0.04, 0.06), _row(1, 2, 0.02, 0.01, 0.12)])
    assert np.allclose(S.net(A, None), [0.02 - S.COST, -0.04 - S.COST, -0.01 - S.COST])
    assert np.allclose(S.net(A, 0.05), [0.02 - S.COST, -(0.05 + S.SLIP) - S.COST, -(0.05 + S.SLIP) - S.COST])
    assert np.allclose(S.net(A, 0.10), [0.02 - S.COST, -0.04 - S.COST, -(0.10 + S.SLIP) - S.COST])
    assert list(S.stop_hit(A, 0.05)) == [False, True, True] and not S.stop_hit(A, None).any()


def test_top_mask_picks_largest_turnover_each_day():
    A = np.array([_row(d, c, 0.02, 0, 0, turnover=tv) for d in (1, 2) for c, tv in enumerate((11, 50, 30, 12, 40))])
    m = S.top_mask(A, np.ones(len(A), bool))
    assert m.sum() == 6 and sorted(A[m & (A[:, S.C["day"]] == 1), S.C["turnover"]]) == [30, 40, 50]
    sel = np.array([True, False] * 5)
    assert S.top_mask(A, sel).sum() == 5 and not (S.top_mask(A, sel) & ~sel).any()


def test_daily_path_numbers():
    vals = [0.01, -0.02, -0.03, 0.01, 0.02]
    A = np.array([_row(d + 1, 0, 0, 0, 0) for d in range(5)] + [_row(d + 1, 1, 0, 0, 0) for d in range(5)])
    v = np.array(vals + vals)
    p = S.daily_path(A, v, np.ones(len(A), bool))
    assert p["days"] == 5 and p["per_day"] == 2 and abs(p["worst_day"] + 0.03) < 1e-12
    assert abs(p["max_dd"] - 0.05) < 1e-12 and abs(p["lose_days"] - 0.4) < 1e-12 and abs(p["worst_run"] - (-0.01)) < 1e-12


def _synthetic(drift_old, drift_new, n=520, days_per_era=20, seed=1):
    """3つの時代。目印B・C の付いた株（20％）は drift だけ下がり、高値は寄りから 0〜8％"""
    rng = np.random.default_rng(seed)
    rows = []
    for start, drift in (("2008-03-03", drift_old), ("2018-03-01", drift_old), ("2025-03-03", drift_new)):
        d0 = dt.date.fromisoformat(start)
        days = [d for d in (d0 + dt.timedelta(i) for i in range(days_per_era * 2)) if d.weekday() < 5][:days_per_era]
        for d in days:
            up = rng.uniform(size=n) < 0.2
            gaps = np.where(up, 0.04, 0.0) + rng.normal(0, 0.002, n)
            for c in range(n):
                rc = (-drift if up[c] else 0.0) + rng.normal(0, 0.004)
                rows.append(_row(d.toordinal(), c, gaps[c], rc, max(rc, 0) + rng.uniform(0, 0.08) * (rng.uniform() < 0.3),
                                 rprev=0.06 if up[c] else 0.0, ratio=7.0 if up[c] else 1.0))
    return np.array(rows)


def test_summary_words():
    good = S.analyze(_synthetic(0.03, 0.03))
    for g, _ in S.GROUPS:
        st = good["groups"][g]["stops"]
        assert st["10"]["summary"] == S.OK_ALL and st["none"]["summary"] is None
        assert st["3"]["eras"]["e1"]["trades"]["hit"] > st["10"]["eras"]["e1"]["trades"]["hit"]
        assert st["none"]["eras"]["e3"]["top"]["n"] == 20 * 3
    old = S.analyze(_synthetic(0.03, 0.0, seed=2))
    assert old["groups"]["K3"]["stops"]["10"]["summary"] == S.OK_OLD
    none = S.analyze(_synthetic(0.0, 0.0, seed=3))
    assert none["groups"]["K2"]["stops"]["5"]["summary"] == S.NONE


def test_render_and_check_have_no_codes_or_returns():
    res = S.analyze(_synthetic(0.01, 0.01, seed=4))
    md = S.render_md({"generated_at": "x", "prereg_sha256": "0" * 64, "result": dict(res, n_codes=520)})
    assert "## まとめ" in md and "目隠しではない" in md and "投資助言ではありません" in md and "最大の落ち込み" in md and "上位3銘柄" in md
    assert "計算できず" in S.render_md({"generated_at": "x", "result": {"error": "e"}})
    out = S.check_summary(_synthetic(0.01, 0.01, seed=5), {"daily": [], "h1": [], "m5": []}, 520, None)
    assert not any(w in repr(out) for w in ("mean", "value", "net", "'win'", "worst")) and out["eras"]["e3"]["days"] == 20
    assert set(out["eras"]["e1"]["groups"]) == {"K2", "K3"}


def test_workflow_and_sync_forbidden():
    wf = open(".github/workflows/stop-short-lab.yml", encoding="utf-8").read()
    assert "python -u stop_short_lab.py --check" in wf and "restore-keys: jp-bars-" in wf
    assert "python tests/test_stop_short_lab.py" in wf and "stop-short-lab.json stop-short-lab.md" in wf and "options: [check, run]" in wf
    assert '"stop-short-lab.json", "stop-short-lab.md"' in open("check_site_consistency.py", encoding="utf-8").read()


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
