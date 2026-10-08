# -*- coding: utf-8 -*-
"""J30 「寄りで買わない」目印の付いた株を寄りで売る（short_side_lab.py）のテスト。2026-10-08 新設。

値動きはすべて作り物。確かめること＝①事前登録と定数の一致（目印の数字は点検表と同じ）②前の日の売買代金の倍率の合わせ方
（J26 と同じ・前の日の値）③目印と範囲 ④売りの損益の向きと費用（売り買いの差＋貸株料など）⑤まとめの言葉
⑥点検は損益を出さない・出力に銘柄コードを出さない ⑦ワークフローと SYNC 禁忌。

実行:  python tests/test_short_side_lab.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import cost_recount_lab as CR  # noqa: E402
import landmine_lab as LM  # noqa: E402
import short_side_lab as K  # noqa: E402


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    rules = open("MY_TRADING_RULES.md", encoding="utf-8").read()
    assert "## J30 「寄りで買わない」目印の付いた株を、寄りで売る（空売り）と費用のあとも残るか" in text and "**目隠しではない**" in text
    assert (K.IDIO, K.PREV_BIG, K.TV_HIGH) == (0.01, 0.05, 5.0)
    assert "+1% 以上高く寄る" in rules and "前の日に +5% 以上上げて" in rules and "20営業日の平均の5倍以上" in rules
    assert [p[2] for p in K.POPS] == [1.0, 10.0] and "**P1 前の日の売買代金 1億円以上**／**P2 10億円以上**" in text
    assert K.N_Q == 6 and abs(K.ALPHA - 0.05 / 6) < 1e-12 and "99.17％ の幅" in text
    assert K.BORROW == 0.0001 and "貸株料など 0.01％" in text
    assert [e[3] for e in K.ERAS] == ["rclose", "rclose", "r1000"] and K.READ_ERA[3] == "r930"


def _daily(n=90, seed=1):
    rng = np.random.default_rng(seed)
    out, c = [], 1000.0
    d = dt.date(2018, 1, 4)
    while len(out) < n:
        if d.weekday() < 5:
            o = c * (1 + rng.normal(0, 0.004))
            c2 = o * (1 + rng.normal(0, 0.01))
            v = 1e5 * (6 if len(out) % 30 == 29 else 1) * (1 + rng.uniform(0, 0.2))
            out.append((d.isoformat(), o, max(o, c2) * 1.005, min(o, c2) * 0.995, c2, v))
            c = c2
        d += dt.timedelta(days=1)
    return out


def test_ratio_is_the_previous_day():
    daily = _daily()
    A = K.stock_rows(0, daily, {}, {}, CR.ar_spread_avg(daily))
    assert len(A) > 50 and A.shape[1] == len(K.COLS)
    ratio = LM.prev_more(daily)[0]
    pos = {dt.date.fromisoformat(r[0]).toordinal(): i for i, r in enumerate(daily)}
    for row in A:
        k = pos[int(row[K.C["day"]])] - 1
        want = ratio[k]
        assert (np.isnan(want) and np.isnan(row[K.C["tv_ratio"]])) or abs(row[K.C["tv_ratio"]] - want) < 1e-12
        assert abs(row[K.C["turnover"]] - daily[k][4] * daily[k][5] / 1e8) < 1e-9          # 前の日の売買代金
    assert np.nanmax(A[:, K.C["tv_ratio"]]) > 5


def _row(day, code, gap, ret, spread=0.004, turnover=15.0, rprev=0.0, ratio=1.0, col="rclose"):
    r = np.full(len(K.COLS), np.nan)
    r[[K.C["day"], K.C["code"], K.C["gap"], K.C["rprev"], K.C["turnover"], K.C["spread"], K.C["tv_ratio"]]] = \
        [day, code, gap, rprev, turnover, spread, ratio]
    r[K.C[col]] = ret
    return r


def test_marks_pops_and_short_net():
    A = np.array([_row(1, 0, 0.02, -0.01, rprev=0.06, ratio=6), _row(1, 1, 0.02, 0, turnover=5),
                  _row(1, 2, 0.0, 0, turnover=0.5, ratio=np.nan), _row(1, 3, 0.0, 0.01, ratio=4.9)])
    idio = np.array([0.02, 0.015, 0.0, -0.005])
    m, p = K.marks(A, idio), K.pops(A)
    assert list(m["K1"]) == [True, True, False, False] and list(m["K2"]) == [True, False, False, False]
    assert list(m["K3"]) == [True, False, False, False]
    assert list(p["P1"]) == [True, True, False, True] and list(p["P2"]) == [True, False, False, True]
    net = K.short_net(A, "rclose", np.full(4, 0.002))
    assert abs(net[0] - (0.01 - 0.002 - 0.0001)) < 1e-12 and abs(net[3] - (-0.01 - 0.002 - 0.0001)) < 1e-12


def _synthetic(drift, spread=0.004, n=520, days_per_era=20, seed=1):
    """3つの時代＋5分足の朝。窓 +4％ で寄った株（20％）は drift だけ下がる（売りが勝つ）"""
    rng = np.random.default_rng(seed)
    rows = []
    for start, col in (("2008-03-03", "rclose"), ("2018-03-01", "rclose"), ("2025-03-03", "r1000"), ("2026-08-17", "r930")):
        d0 = dt.date.fromisoformat(start)
        days = [d for d in (d0 + dt.timedelta(i) for i in range(days_per_era * 2)) if d.weekday() < 5][:days_per_era]
        for d in days:
            up = rng.uniform(size=n) < 0.2
            gaps = np.where(up, 0.04, 0.0) + rng.normal(0, 0.002, n)
            for c in range(n):
                ret = (-drift if up[c] else 0.0) + rng.normal(0, 0.004)
                r = _row(d.toordinal(), c, gaps[c], ret, spread, rprev=0.06 if up[c] else 0.0, ratio=7.0 if up[c] else 1.0, col=col)
                if col == "r930":
                    r[K.C["r1000"]] = ret
                rows.append(r)
    return np.array(rows)


def test_summary_words():
    both = K.analyze(_synthetic(drift=0.012))                       # 重いほう（0.4％＋0.01％）を引いても売りがプラス
    assert all(both["groups"][f"{g}-{p}"]["summary"] == K.OK_BOTH for g, _ in K.MARKS for p, *_ in K.POPS)
    assert both["eras"]["e1"]["days"] == 20 and both["groups"]["K1-P1"]["read"]["e4"]["gross"]["n"] > 0
    low = K.analyze(_synthetic(drift=0.0032, seed=2))              # 軽いほう（0.4×0.32≒0.13％）でだけプラス
    assert low["groups"]["K2-P2"]["summary"] == K.OK_LOW, {k: v["low"].get("lo") for k, v in low["groups"]["K2-P2"]["eras"].items()}
    none = K.analyze(_synthetic(drift=0.0, seed=3))
    assert none["groups"]["K3-P1"]["summary"] == K.NONE


def test_render_and_check_have_no_codes_or_returns():
    res = K.analyze(_synthetic(drift=0.004, seed=4))
    md = K.render_md({"generated_at": "x", "prereg_sha256": "0" * 64, "result": dict(res, n_codes=520)})
    assert "## まとめ" in md and "目隠しではない" in md and "投資助言ではありません" in md and "読むための表" in md and "空売り" in md
    assert "計算できず" in K.render_md({"generated_at": "x", "result": {"error": "e"}})
    out = K.check_summary(_synthetic(drift=0.004, seed=5), {"daily": [], "h1": [], "m5": []}, 520, None)
    assert not any(w in repr(out) for w in ("mean", "value", "net", "'win'")) and out["eras"]["e1"]["days"] == 20
    assert set(out["eras"]["e2"]["groups"]) == {f"{g}-{p}" for g, _ in K.MARKS for p, *_ in K.POPS}


def test_workflow_and_sync_forbidden():
    wf = open(".github/workflows/short-side-lab.yml", encoding="utf-8").read()
    assert "python -u short_side_lab.py --check" in wf and "restore-keys: jp-bars-" in wf
    assert "python tests/test_short_side_lab.py" in wf and "short-side-lab.json short-side-lab.md" in wf and "options: [check, run]" in wf
    assert '"short-side-lab.json", "short-side-lab.md"' in open("check_site_consistency.py", encoding="utf-8").read()


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
