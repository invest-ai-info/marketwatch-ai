# -*- coding: utf-8 -*-
"""J19 安く寄った株の戻りは、銘柄ごとの売り買いの差を引いても残るか（bounce_cost_lab.py）のテスト。2026-10-07 新設。

値動きはすべて作り物。確かめること＝①事前登録と定数の一致 ②売り買いの差の見積もり（作り物の差を取り戻す・その朝より前の値だけ・出来高0の日を使わない）
③形27通りと選び方（2,000回・前半後半）④確かめ（✅・見えない・費用で消える）⑤出力に銘柄コードを出さない・点検は損益を出さない ⑥ワークフローと SYNC 禁忌。

実行:  python tests/test_bounce_cost_lab.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import prevday_lab as PD  # noqa: E402
import bounce_cost_lab as M  # noqa: E402


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "## J19 安く寄った株の戻りは、銘柄ごとの売り買いの差を引いても残るか" in text
    assert M.SELECT == ("2006-01-04", "2016-10-31") and "2006-01-04〜2016-10-31" in text
    assert [c[2] for c in M.CONFIRM] == [PD.OLD, PD.NEW] and [c[3] for c in M.CONFIRM] == ["rclose", "r1000"]
    assert (M.WINDOW, M.MIN_OBS, M.COST_FLOOR, M.MIN_TRADES) == (60, 20, 0.001, 2000)
    assert "60営業日" in text and "20日以上" in text and "往復 0.1％" in text and "2,000回以上" in text
    assert M.N_Q == 2 and abs(M.ALPHA - 0.025) < 1e-12 and "p＜0.05÷2＝97.5％ の幅" in text
    assert len(M.rules()) == 27 and [d[2] for d in M.DEPTH] == [-0.01, -0.02, -0.03] and [x[2] for x in M.LIQ] == [0.0, 1.0, 10.0]


def _daily(S, n=400, seed=3, zero_vol=()):
    rng = np.random.default_rng(seed)
    p, rows, d0 = 100.0, [], dt.date(2010, 1, 4)
    for t in range(n):
        p *= np.exp(rng.normal(0, 0.015))
        a = abs(rng.normal(0, 0.01)) + S / 2 + 0.001
        c = p * np.exp(rng.choice([-1, 1]) * S / 2)
        rows.append(((d0 + dt.timedelta(days=t)).isoformat(), p, p * np.exp(a), p * np.exp(-a), c, 0 if t in zero_vol else 1000))
    return rows


def test_ar_spread_recovers_and_uses_only_past():
    for S in (0.01, 0.03):
        v = np.array(list(M.ar_spread(_daily(S)).values()))
        assert 0.8 * S < np.median(v) < 1.2 * S, (S, np.median(v))
    rows = _daily(0.01)
    sp = M.ar_spread(rows)
    j = 200
    changed = rows[:j] + [(d, o * 1.5, h * 1.9, lo * 0.5, c * 1.7, v) for d, o, h, lo, c, v in rows[j:]]
    assert M.ar_spread(changed)[rows[j][0]] == sp[rows[j][0]]          # その朝と後の値を変えても、その朝の見積もりは同じ
    assert rows[M.MIN_OBS + 1][0] in sp and rows[M.MIN_OBS][0] not in sp  # 20日そろってから
    zv = M.ar_spread(_daily(0.01, zero_vol=set(range(0, 400, 2))))     # 出来高0の日を含む2日は使わない＝ずっと20日に届かない
    assert zv == {}
    assert M.cost(np.array([0.0005, 0.004])).tolist() == [0.001, 0.004]


def _rows(n_days=300, n_codes=600, start="2008-01-04", seed=1, bounce=0.006, spread=0.002, with_new=False):
    """その銘柄だけ −1％以下で寄ると bounce だけ戻る作り物（費用の見積もりは spread で一定）"""
    rng = np.random.default_rng(seed)
    d0 = dt.date.fromisoformat(start).toordinal()
    out = []
    for d in range(n_days):
        mkt_gap, mkt = rng.normal(0, 0.003), rng.normal(0, 0.004)
        idio = rng.choice([-0.035, -0.015, 0.0, 0.0, 0.015], size=n_codes)
        rp = rng.choice([0.0, 0.01, -0.06, 0.06], size=n_codes)
        tv = rng.choice([0.5, 3.0, 20.0], size=n_codes)
        noise = rng.normal(0, 0.006, size=n_codes)
        for c in range(n_codes):
            r = mkt + noise[c] + (bounce if idio[c] <= -0.01 else 0)
            out.append((d0 + d, c, mkt_gap + idio[c], rp[c], r, r if with_new else np.nan, r if with_new else np.nan, tv[c], spread))
    return np.array(out, float)


def test_rule_masks_and_select():
    A = np.zeros((6, len(M.COLS)))
    A[:, M.C["turnover"]] = [0.5, 2.0, 20.0, 20.0, 20.0, 20.0]
    A[:, M.C["rprev"]] = [0.0, 0.0, 0.0, -0.06, 0.06, 0.0]
    A[:, M.C["spread"]] = [0.002, 0.002, 0.002, 0.002, 0.002, np.nan]
    idio = np.array([-0.015, -0.025, -0.035, -0.035, -0.035, -0.035])
    assert M.rule_mask(A, idio, "D1-L0-V0").tolist() == [True, True, True, True, True, False]   # 費用を見積もれない朝は数えない
    assert M.rule_mask(A, idio, "D2-L1-V0").tolist() == [False, True, True, True, True, False]
    assert M.rule_mask(A, idio, "D3-L2-V1").tolist() == [False, False, False, True, False, False]
    assert M.rule_mask(A, idio, "D3-L2-V2").tolist() == [False, False, True, True, False, False]
    g = {"a": {"n": 3000, "net": 0.002, "early": 0.001, "late": 0.003}, "b": {"n": 1999, "net": 0.01, "early": 0.01, "late": 0.01},
         "c": {"n": 5000, "net": 0.004, "early": -0.001, "late": 0.009}, "d": {"n": 2000, "net": 0.003, "early": 0.002, "late": 0.004}}
    assert M.select(g) == "d" and M.select({"x": {"n": 10}}) is None
    assert M.rule_label("D2-L1-V1") == "−2％以下・1億円以上・前の日 −5％以下"


def test_confirm_both_and_gone_and_render():
    A = np.vstack([_rows(start="2008-01-04"), _rows(start="2018-01-04", seed=2), _rows(n_days=200, start="2024-11-01", seed=3, with_new=True)])
    res = M.analyze(A)
    assert res["chosen"] is not None and res["overall"] == M.BOTH, (res["chosen"], res["overall"], res["confirm"])
    assert res["confirm"]["b"]["verdict"] == M.OK and res["confirm"]["c"]["verdict"] == M.OK
    weak = np.vstack([_rows(start="2008-01-04", bounce=0.0025, spread=0.004), _rows(start="2018-01-04", seed=2, bounce=0.0025, spread=0.004),
                      _rows(n_days=200, start="2024-11-01", seed=3, with_new=True, bounce=0.0025, spread=0.004)])
    assert M.analyze(weak)["overall"] == M.NOSEL                       # 費用 0.4％ に戻り 0.25％＝選べる形が無い
    mixed = np.vstack([_rows(start="2008-01-04"), _rows(start="2018-01-04", seed=2, bounce=0.0, spread=0.004),
                       _rows(n_days=200, start="2024-11-01", seed=3, with_new=True, bounce=0.0, spread=0.004)])
    assert M.analyze(mixed)["overall"] == M.GONE
    out = {"generated_at": "x", "prereg_sha256": "0" * 64, "price_store": {"built_at": "b"},
           "result": dict(res, n_codes=600, list_date="2026-09-30", n_missing={}, n_dropped=0)}
    md = M.render_md(out)
    assert "## まとめ" in md and "選んだ形" in md and "27通り" in md and " ◀" in md and "投資助言ではありません" in md
    assert "計算できず" in M.render_md({"generated_at": "x", "prereg_sha256": "", "result": {"error": "e"}})


def test_stock_rows_attach_cost_and_check_has_no_returns():
    rows = [((dt.date(2015, 1, 5) + dt.timedelta(days=k)).isoformat(), *r[1:]) for k, r in enumerate(_daily(0.01, n=300))]
    A = M.stock_rows(7, rows, {}, {})
    sp = M.ar_spread(rows)
    assert A.shape[1] == len(M.COLS) and len(A)
    for r in A[:50]:
        d = dt.date.fromordinal(int(r[M.C["day"]])).isoformat()
        assert (np.isnan(r[M.C["spread"]]) and d not in sp) or abs(r[M.C["spread"]] - sp[d]) < 1e-12
    B = _rows(n_days=20)
    out = M.check_summary(B, {"daily": [], "h1": [], "m5": []}, 600, {"daily_range": "from:1990"})
    keys = " ".join(str(k) for k in out) + " ".join(str(k) for p in out["periods"].values() for k in p)
    assert not any(w in keys for w in ("net", "gross", "mean", "diff")) and len(out["select_counts"]) == 27


def test_listing_only_stops_when_costs_win_and_relist_keeps_numbers():
    import json
    import tempfile
    grid = {M.BASE: {"n": 1000, "net": -0.006}}
    base = {"b": {"net": -0.007}, "c": {"net": -0.008}}
    for overall, stop in ((M.NOSEL, True), (M.GONE, True), (M.ONE, False), (M.BOTH, False)):
        out = M.listing({"result": {"overall": overall, "grid": grid, "base": base}}, "2026-10-07")
        assert out["kind"] == "backtest" and set(out["titles"]) == {"J19"} and (("J19" in out["verdicts"]) == stop), overall
    v = M.listing({"result": {"overall": M.NOSEL, "grid": grid, "base": base}}, "2026-10-07")["verdicts"]["J19"]
    assert v["status"] == "stop" and v["n"] == 1000 and v["mean"] == -0.006 and "選べる形なし" in v["reason"] and "-0.70％" in v["reason"]
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "x.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"generated_at": "g", "result": {"overall": M.NOSEL, "grid": grid, "base": base, "chosen": None}}, fh)
        res = M.relist(path)
        assert res["result"]["grid"] == grid and res["verdicts"]["J19"]["status"] == "stop" and res["generated_at"] == "g"
    import verified_list as V
    assert any(p == "bounce-cost-lab.json" for p, *_ in V.SOURCES)


def test_workflow_and_sync_forbidden():
    wf = open(".github/workflows/bounce-cost-lab.yml", encoding="utf-8").read()
    assert "python -u bounce_cost_lab.py --check" in wf and "restore-keys: jp-bars-" in wf
    assert "bounce-cost-lab.json bounce-cost-lab.md verified-list.md" in wf and "options: [check, run, relist]" in wf
    assert "python bounce_cost_lab.py --relist" in wf
    assert '"bounce-cost-lab.json", "bounce-cost-lab.md"' in open("check_site_consistency.py", encoding="utf-8").read()


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
