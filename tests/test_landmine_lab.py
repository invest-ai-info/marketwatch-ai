# -*- coding: utf-8 -*-
"""J21 主戦場から地雷銘柄を見つけて外すと、残りの勝率と損益はどうなるか（landmine_lab.py）のテスト。2026-10-07 新設。

値動きはすべて作り物。確かめること＝①事前登録と定数の一致 ②前の日の売買代金の倍率・上ヒゲ・高値引け・52週高値（前の日までの値だけ）
③候補の当てはまり・判定できるか ④地雷を E1 だけで決める・外す・残りの勝率・確かめ（C1・C2）・まとめ
⑤出力に銘柄コードを出さない・点検は損益を出さない ⑥ワークフローと SYNC 禁忌。

実行:  python tests/test_landmine_lab.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import highs_trap_lab as T  # noqa: E402
import landmine_lab as L  # noqa: E402
import main_field_lab as MF  # noqa: E402
import test_highs_trap_lab as TL  # noqa: E402


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "## J21 主戦場から地雷銘柄を見つけて外すと、残りの勝率と損益はどうなるか" in text
    assert L.ERAS == MF.ERAS and L.SELECT_ERA[0] == "e1" and [e[0] for e in L.CONFIRM_ERAS] == ["e2", "e3"]
    assert [k for k, _ in L.CANDIDATES] == [f"L{i}" for i in range(1, 10)]
    assert (L.TV_DAYS, L.TV_RATIO, L.WICK, L.HI_CLOSE, L.HIGH_DAYS) == (20, 5.0, 0.5, 0.999, 250)
    assert "20営業日の平均の5倍以上" in text and "0.5 以上" in text and "99.9％ 以上" in text and "250営業日" in text
    assert abs(L.ALPHA_SELECT - 0.05 / 9) < 1e-12 and "p＜0.05÷9" in text and "99.44％" in text
    assert abs(L.ALPHA_CONFIRM - 0.05 / 4) < 1e-12 and "p＜0.05÷4＝98.75％ の幅" in text
    assert L.COLS[:len(MF.COLS)] == MF.COLS and all(L.C[k] == MF.C[k] for k in MF.COLS)   # J20 の列はそのままの位置


def _daily(n=262, start="2015-01-05"):
    days = TL._bdays(start, n)
    rows = []
    for i, d in enumerate(days):
        c = 100.0 + (i % 3) * 0.1
        rows.append([d, c, c * 1.01, c * 0.99, c, 1e6 * (1 + (i % 2))])
    return days, rows


def test_prev_more_uses_only_past_values():
    days, rows = _daily()
    rows[255] = [days[255], 100.0, 108.0, 99.0, 102.0, 1e7]      # 売買代金が急増・上ヒゲ・高値を更新
    rows[256] = [days[256], 102.0, 103.0, 101.0, 103.0, 1e6]      # 高値引け
    ratio, wick, hi_close, new_high = L.prev_more([tuple(r) for r in rows])
    tv = np.array([r[4] * r[5] / 1e8 for r in rows])
    assert np.isnan(ratio[19]) and abs(ratio[255] - tv[255] / tv[235:255].mean()) < 1e-12 and ratio[255] > 5
    assert abs(wick[255] - 6 / 9) < 1e-12 and hi_close[256] == 1.0 and hi_close[255] == 0.0
    assert np.isnan(new_high[249]) and new_high[255] == 1.0 and new_high[254] == 0.0
    A = L.stock_rows(7, [tuple(r) for r in rows], {}, {})
    got = {dt.date.fromordinal(int(r[L.C["day"]])).isoformat(): r for r in A}
    r = got[days[256]]                                              # 前の日＝ days[255]
    assert abs(r[L.C["tv_ratio"]] - ratio[255]) < 1e-12 and abs(r[L.C["wick"]] - 6 / 9) < 1e-12
    assert r[L.C["new_high"]] == 1.0 and r[L.C["hi_close"]] == 0.0
    assert got[days[257]][L.C["hi_close"]] == 1.0 and got[days[257]][L.C["new_high"]] == 0.0
    assert np.isnan(got[days[100]][L.C["new_high"]])               # 250日そろわなければ判定しない


def test_flags():
    A = np.zeros((4, len(L.COLS)))
    A[:, L.C["dev25"]] = [0.2, 0.1, np.nan, 0.2]
    A[:, L.C["streak"]] = [4, 3, 5, 0]
    A[:, L.C["rprev"]] = [0.16, 0.06, 0.15, 0.05]
    A[:, L.C["tv_ratio"]] = [6, 2, np.nan, 5]
    A[:, L.C["wick"]] = [0.6, 0.2, 0.5, 0.0]
    A[:, L.C["hi_close"]] = [1, 0, 0, 1]
    A[:, L.C["new_high"]] = [1, 0, np.nan, 1]
    idio = np.array([0.01, 0.0, -0.01, -0.02])
    want = {"L1": [1, 0, 0, 0], "L2": [1, 0, 0, 1], "L3": [1, 0, 1, 0], "L4": [1, 0, 1, 0], "L5": [1, 0, 0, 1],
            "L6": [1, 0, 1, 0], "L7": [1, 0, 0, 1], "L8": [1, 0, 0, 1], "L9": [0, 0, 1, 1]}
    for key, w in want.items():
        f, ok = L.flag(key, A, idio)
        assert list((f & ok).astype(int)) == w, key
    assert list(L.flag("L2", A, idio)[1]) == [True, True, False, True] and list(L.flag("L8", A, idio)[1]) == [True, True, False, True]


def _rows(n_days=110, n_codes=600, start="2008-01-04", seed=1, mine=-0.012, good=0.004, with_new=False):
    """主戦場のうち L5（売買代金の急増）に当てはまる朝だけ mine、それ以外の主戦場は good"""
    rng = np.random.default_rng(seed)
    d0 = dt.date.fromisoformat(start).toordinal()
    out = []
    for d in range(n_days):
        mkt_gap, mkt = rng.normal(0, 0.003), rng.normal(0, 0.003)
        idio = rng.choice([0.0, 0.0, 0.015, -0.015], size=n_codes)
        rp = rng.choice([0.0, 0.06, 0.06, 0.01, 0.2], size=n_codes)
        tv = rng.choice([3.0, 20.0, 20.0], size=n_codes)
        dv = rng.choice([0.05, 0.2], size=n_codes)
        st = rng.choice([1, 5], size=n_codes)
        ratio = rng.choice([1.0, 1.0, 6.0], size=n_codes)
        wick = rng.choice([0.1, 0.7], size=n_codes)
        hc = rng.choice([0.0, 1.0], size=n_codes)
        nh = rng.choice([0.0, 1.0, np.nan], size=n_codes)
        noise = rng.normal(0, 0.006, size=n_codes)
        for c in range(n_codes):
            mf = rp[c] >= 0.05 and tv[c] >= 10
            r = mkt + noise[c] + ((mine if ratio[c] >= 5 else good) if mf else 0.0)
            out.append((d0 + d, c, mkt_gap + idio[c], rp[c], r, r if with_new else np.nan, r if with_new else np.nan,
                        tv[c], dv[c], st[c], ratio[c], wick[c], hc[c], nh[c]))
    return np.array(out, float)


def _three(**kw):
    return np.vstack([_rows(start="2008-01-04", **kw), _rows(start="2018-01-04", seed=2, **kw),
                      _rows(n_days=90, start="2024-11-01", seed=3, with_new=True, **kw)])


def test_select_exclude_and_confirm():
    A = _three()
    res = L.analyze(A)
    assert res["mines"] == ["L5"], {k: (q["value"], q["hi"]) for k, q in res["candidates"].items()}
    assert res["candidates"]["L5"]["mine"] and res["candidates"]["L5"]["hi"] < 0
    w = res["winrates"]
    for ek in ("e1", "e2", "e3"):
        assert w[ek]["rem"]["mean"] > 0 > w[ek]["excl"]["mean"] and w[ek]["rem"]["win"] > w[ek]["all"]["win"] > w[ek]["excl"]["win"]
        assert w[ek]["all"]["n"] == w[ek]["rem"]["n"] + w[ek]["excl"]["n"]
    assert "930" in w["e3"] and "930" not in w["e1"]
    assert res["summary"] == {"c1": L.BOTH, "c2": L.BOTH} and res["confirm"]["e3"]["c1"]["d60"]["n"] >= 30
    assert res["reading"]["e2"]["L5"] < -0.01 and abs(res["reading"]["e2"]["L7"]) < 0.002
    assert set(res["by_year"]) == {"2008", "2018", "2024", "2025"}


def test_no_mine_and_no_profit():
    res = L.analyze(_three(mine=0.0, good=0.0))
    assert res["mines"] == [] and res["summary"] == {"c1": "地雷なし", "c2": "地雷なし"} and res["confirm"] == {}
    assert res["winrates"]["e2"]["excl"]["n"] == 0
    rb = L.analyze(_three(good=0.0))                       # 地雷は見分けられるが、残りは費用を払うとプラスにならない
    assert rb["mines"] == ["L5"] and rb["summary"]["c1"] == L.BOTH and rb["summary"]["c2"] == L.NONE
    assert L.summarize([L.OK, L.NONE]) == L.ONE and L.summarize([L.NONE, L.NONE]) == L.NONE


def test_winrate():
    v = np.array([0.003, -0.002, 0.0005, np.nan, 0.01])
    w = L.winrate(v, np.array([True, True, True, True, False]))
    assert w["n"] == 3 and abs(w["win"] - 1 / 3) < 1e-12 and abs(w["mean"] - (np.mean([0.003, -0.002, 0.0005]) - T.COST)) < 1e-12
    assert L.winrate(v, np.zeros(5, bool)) == {"n": 0, "win": None, "mean": None}


def test_render_and_check_have_no_codes_or_returns():
    res = L.analyze(_three())
    out = {"generated_at": "x", "prereg_sha256": "0" * 64, "price_store": {"built_at": "b"},
           "result": dict(res, n_codes=600, list_date="2026-09-30", n_missing={}, n_dropped=0)}
    md = L.render_md(out)
    assert "## まとめ" in md and "L5 前の日の売買代金" in md and "💣" in md and "勝率" in md and "投資助言ではありません" in md
    assert "5分足の寄り→9:30" in md and L.BOTH in md
    assert "計算できず" in L.render_md({"generated_at": "x", "prereg_sha256": "", "result": {"error": "e"}})
    ck = L.check_summary(_rows(n_days=10), {"daily": [], "h1": [], "m5": []}, 600, {"daily_range": "from:1990"})
    keys = " ".join(str(k) for k in ck) + " ".join(str(k) for e in ck["eras"].values() for k in e)
    assert not any(w in keys for w in ("mean", "win", "value", "diff")) and set(ck["eras"]["e1"]["candidates"]) == {k for k, _ in L.CANDIDATES}


def test_workflow_and_sync_forbidden():
    wf = open(".github/workflows/landmine-lab.yml", encoding="utf-8").read()
    assert "python -u landmine_lab.py --check" in wf and "restore-keys: jp-bars-" in wf and "python tests/test_landmine_lab.py" in wf
    assert "landmine-lab.json landmine-lab.md" in wf and "options: [check, run]" in wf
    assert '"landmine-lab.json", "landmine-lab.md"' in open("check_site_consistency.py", encoding="utf-8").read()


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
