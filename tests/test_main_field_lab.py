# -*- coding: utf-8 -*-
"""J20 主戦場を翌朝の寄りで買うと、3つの時代でどうだったか（main_field_lab.py）のテスト。2026-10-07 新設。

値動きはすべて作り物。確かめること＝①事前登録と定数の一致 ②前の日の 25日線からの離れ・連騰の日数（前の日までの値だけ）
③組（主戦場・窓・過熱・連騰）④判定とまとめ（3つの時代で同じ向き・2つ・見えない）⑤出力に銘柄コードを出さない・点検は損益を出さない
⑥ワークフローと SYNC 禁忌。

実行:  python tests/test_main_field_lab.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import prevday_lab as PD  # noqa: E402
import main_field_lab as M  # noqa: E402
import test_highs_trap_lab as TL  # noqa: E402


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "## J20 主戦場（前の日に大きく上げた×売買代金が大きい株）を翌朝の寄りで買うと" in text
    assert [e[2] for e in M.ERAS] == [("2006-01-04", "2016-10-31"), PD.OLD, PD.NEW] and [e[3] for e in M.ERAS] == ["rclose", "rclose", "r1000"]
    assert (M.PREV_BIG, M.TURNOVER, M.IDIO, M.OVERHEAT, M.STREAK) == (0.05, 10.0, 0.01, 0.15, 4)
    assert "前の日の売買代金 10億円以上" in text and "+15％ 超" in text and "4日以上続けて" in text
    assert M.N_Q == 12 and abs(M.ALPHA - 0.05 / 12) < 1e-12 and "p＜0.05÷12＝99.58％ の幅" in text


def test_prev_features_and_rows():
    days = TL._bdays("2019-01-04", 40)
    closes = [100.0] * 30 + [101, 102, 103, 104, 110, 111, 111, 111, 111, 111]
    daily = [(d, c, c * 1.01, c * 0.99, c, 1e7) for d, c in zip(days, closes)]
    dev, streak = M.prev_features(daily)
    assert np.isnan(dev[23]) and abs(dev[24]) < 1e-12 and streak[29] == 0 and streak[34] == 5 and streak[36] == 0
    assert abs(dev[34] - (110 / np.mean(closes[10:35]) - 1)) < 1e-12
    A = M.stock_rows(3, daily, {}, {})
    got = {dt.date.fromordinal(int(r[M.C["day"]])).isoformat(): r for r in A}
    r = got[days[35]]                                                   # 前の日＝ days[34]（5日続けて上がった・+5.8％）
    assert r[M.C["streak"]] == 5 and abs(r[M.C["dev25"]] - dev[34]) < 1e-12 and abs(r[M.C["rprev"]] - (110 / 104 - 1)) < 1e-12


def test_groups():
    A = np.zeros((6, len(M.COLS)))
    A[:, M.C["rprev"]] = [0.06, 0.06, 0.06, 0.03, 0.06, 0.06]
    A[:, M.C["turnover"]] = [20, 20, 5, 20, 20, 20]
    A[:, M.C["dev25"]] = [0.2, 0.1, 0.2, 0.2, np.nan, 0.1]
    A[:, M.C["streak"]] = [4, 1, 4, 4, 5, 3]
    idio = np.array([0.0, 0.02, 0.0, 0.0, 0.0, -0.02])
    assert list(M.groups("q1", A, idio)) == [0, 0, -1, -1, 0, 0]
    assert list(M.groups("q2", A, idio)) == [0, -1, -1, -1, 0, -1]
    assert list(M.groups("q3", A, idio)) == [0, 1, -1, -1, -1, 1]
    assert list(M.groups("q4", A, idio)) == [0, 1, -1, -1, 0, 1]


def _rows(n_days=150, n_codes=600, start="2008-01-04", seed=1, base_eff=-0.006, heat=-0.004, run=-0.004, with_new=False):
    rng = np.random.default_rng(seed)
    d0 = dt.date.fromisoformat(start).toordinal()
    out = []
    for d in range(n_days):
        mkt_gap, mkt = rng.normal(0, 0.003), rng.normal(0, 0.004)
        idio = rng.choice([0.0, 0.0, 0.015, -0.015], size=n_codes)
        rp = rng.choice([0.0, 0.06, 0.06, 0.01], size=n_codes)
        tv = rng.choice([3.0, 20.0, 20.0], size=n_codes)
        dv = rng.choice([0.05, 0.2], size=n_codes)
        st = rng.choice([1, 5], size=n_codes)
        noise = rng.normal(0, 0.006, size=n_codes)
        for c in range(n_codes):
            mf = rp[c] >= 0.05 and tv[c] >= 10
            r = mkt + noise[c] + ((base_eff + (heat if dv[c] > 0.15 else 0) + (run if st[c] >= 4 else 0)) if mf else 0)
            out.append((d0 + d, c, mkt_gap + idio[c], rp[c], r, r if with_new else np.nan, r if with_new else np.nan, tv[c], dv[c], st[c]))
    return np.array(out, float)


def test_analyze_judges_and_summary():
    A = np.vstack([_rows(start="2008-01-04"), _rows(start="2018-01-04", seed=2), _rows(n_days=120, start="2024-11-01", seed=3, with_new=True)])
    res = M.analyze(A)
    for key in ("q1", "q2", "q3", "q4"):
        assert res["summary"][key].startswith(M.ALL3) and "（下）" in res["summary"][key], (key, res["summary"][key],
                                                                                         [res["judges"][key][e]["verdict"] for e in ("e1", "e2", "e3")])
    B = np.vstack([_rows(start="2008-01-04", heat=0.0, run=0.0), _rows(start="2018-01-04", seed=2, heat=0.0, run=0.0),
                   _rows(n_days=120, start="2024-11-01", seed=3, with_new=True, heat=0.0, run=0.0)])
    rb = M.analyze(B)
    assert rb["summary"]["q3"] == M.NONE and rb["summary"]["q4"] == M.NONE and rb["summary"]["q1"].startswith(M.ALL3)
    assert M.summarize(["下", "下", "見えない"]) == f"{M.TWO}（下）" and M.summarize(["下", "上", "下"]) == M.NONE
    assert M.summarize(["10:00 だけの兆し（9:30 では逆向き＝オーナーの取引時間では使えない）：下", "下", "下"]) == f"{M.TWO}（下）"
    out = {"generated_at": "x", "prereg_sha256": "0" * 64, "price_store": {"built_at": "b"},
           "result": dict(res, n_codes=600, list_date="2026-09-30", n_missing={}, n_dropped=0)}
    md = M.render_md(out)
    assert "## まとめ" in md and "Q3 主戦場のうち、過熱あり" in md and "投資助言ではありません" in md
    assert "計算できず" in M.render_md({"generated_at": "x", "prereg_sha256": "", "result": {"error": "e"}})


def test_check_summary_has_no_returns():
    A = _rows(n_days=20)
    out = M.check_summary(A, {"daily": [], "h1": [], "m5": []}, 600, {"daily_range": "from:1990"})
    keys = " ".join(str(k) for k in out) + " ".join(str(k) for e in out["eras"].values() for k in e)
    assert not any(w in keys for w in ("mean", "value", "diff")) and set(out["eras"]["e1"]["sizes"]) == {"q1", "q2", "q3", "q4"}


def test_workflow_and_sync_forbidden():
    wf = open(".github/workflows/main-field-lab.yml", encoding="utf-8").read()
    assert "python -u main_field_lab.py --check" in wf and "restore-keys: jp-bars-" in wf
    assert "main-field-lab.json main-field-lab.md" in wf and "options: [check, run]" in wf
    assert '"main-field-lab.json", "main-field-lab.md"' in open("check_site_consistency.py", encoding="utf-8").read()


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
