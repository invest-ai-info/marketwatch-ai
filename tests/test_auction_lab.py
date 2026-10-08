# -*- coding: utf-8 -*-
"""J31 板寄せどうしで数え直す（auction_lab.py）のテスト。2026-10-08 新設。

値動きはすべて作り物。確かめること＝①事前登録と定数の一致 ②行（J30 の行＋その日の高値・安値の始値からの幅）
③組（買い3つ・売り6つ）と損益の向き・費用 ④まとめの言葉（3つの時代とも／昔だけ／それ以外）
⑤点検は損益を出さない・出力に銘柄コードを出さない ⑥ワークフローと SYNC 禁忌。

実行:  python tests/test_auction_lab.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import auction_lab as A  # noqa: E402
import cost_recount_lab as CR  # noqa: E402
import short_side_lab as K  # noqa: E402


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "## J31 板寄せどうし（寄り成行で入り、引け成行で出る）なら費用はほぼかからない" in text and "**目隠しではない**" in text
    assert A.N_Q == 9 and abs(A.ALPHA - 0.05 / 9) < 1e-12 and "p＜0.05÷9＝99.44％ の幅" in text
    assert A.LONG_COST == 0.0002 and abs(A.SHORT_COST - 0.0003) < 1e-12 and "買い＝往復 0.02％" in text and "0.01％＝0.03％" in text
    assert [e[2] for e in A.ERAS] == [("2006-01-04", "2016-10-31"), ("2016-11-01", "2023-09-29"), ("2023-10-10", "2026-10-05")]
    assert "**E3 2023-10-10〜2026-10-05（日足の寄り→大引け）**" in text and A.STRICT_COST == 0.001 and "往復0.1％にしたとき" in text
    assert [g for g, *_ in A.LONGS] == ["L1", "L2", "L3"] and [s for *_, s in A.LONGS] == ["D1", "D2", "D3"]


def test_rows_add_high_low_of_the_day():
    import test_short_side_lab as TS
    daily = TS._daily()
    R = A.stock_rows(0, daily, {}, {}, CR.ar_spread_avg(daily))
    base = K.stock_rows(0, daily, {}, {}, CR.ar_spread_avg(daily))
    assert R.shape == (len(base), len(A.COLS)) and np.allclose(R[:, :len(K.COLS)], base, equal_nan=True)
    pos = {dt.date.fromisoformat(r[0]).toordinal(): i for i, r in enumerate(daily)}
    for row in R[:10]:
        d = daily[pos[int(row[A.C["day"]])]]
        assert abs(row[A.C["rhigh"]] - (d[2] / d[1] - 1)) < 1e-12 and abs(row[A.C["rlow"]] - (d[3] / d[1] - 1)) < 1e-12
        assert abs(row[A.C["rclose"]] - (d[4] / d[1] - 1)) < 1e-12


def _row(day, code, gap, rc, turnover=15.0, rprev=0.0, ratio=1.0):
    r = np.full(len(A.COLS), np.nan)
    r[[A.C["day"], A.C["code"], A.C["gap"], A.C["rprev"], A.C["turnover"], A.C["tv_ratio"], A.C["rclose"], A.C["rhigh"], A.C["rlow"]]] = \
        [day, code, gap, rprev, turnover, ratio, rc, max(rc, 0) + 0.01, min(rc, 0) - 0.01]
    return r


def _synthetic(drift_old, drift_new, n=520, days_per_era=20, seed=1):
    """3つの時代。窓 +4％ で寄った株（20％）は drift だけ下がり、窓 −4％ で寄った株（20％）は drift だけ上がる"""
    rng = np.random.default_rng(seed)
    rows = []
    for start, drift in (("2008-03-03", drift_old), ("2018-03-01", drift_old), ("2025-03-03", drift_new)):
        d0 = dt.date.fromisoformat(start)
        days = [d for d in (d0 + dt.timedelta(i) for i in range(days_per_era * 2)) if d.weekday() < 5][:days_per_era]
        for d in days:
            u = rng.uniform(size=n)
            up, dn = u < 0.2, u > 0.8
            gaps = np.where(up, 0.04, np.where(dn, -0.04, 0.0)) + rng.normal(0, 0.002, n)
            for c in range(n):
                rc = (-drift if up[c] else drift if dn[c] else 0.0) + rng.normal(0, 0.004)
                rows.append(_row(d.toordinal(), c, gaps[c], rc, rprev=0.06 if up[c] else 0.0, ratio=7.0 if up[c] else 1.0))
    return np.array(rows)


def test_signs_costs_and_summary_words():
    res = A.analyze(_synthetic(0.005, 0.005))
    g = res["groups"]
    assert all(x["summary"] == A.OK_ALL for x in g.values()), {k: x["summary"] for k, x in g.items()}
    assert g["K2-P1"]["side"] == "売り" and g["L3"]["side"] == "買い"
    q = g["K3-P2"]["eras"]["e1"]
    assert abs(q["value"] - (q["gross"]["mean"] - A.SHORT_COST)) < 1e-9 and q["gross"]["mean"] > 0.004
    assert abs(g["L3"]["eras"]["e2"]["value"] - (g["L3"]["eras"]["e2"]["gross"]["mean"] - A.LONG_COST)) < 1e-9
    assert q["adverse"]["mean"] > 0 and abs(q["strict"]["mean"] - (q["gross"]["mean"] - 0.001 - K.BORROW)) < 1e-9
    old = A.analyze(_synthetic(0.005, 0.0, seed=2))
    assert old["groups"]["K1-P1"]["summary"] == A.OK_OLD and old["groups"]["L2"]["summary"] == A.OK_OLD
    none = A.analyze(_synthetic(0.0, 0.0, seed=3))
    assert none["groups"]["K2-P2"]["summary"] == A.NONE and set(none["groups"]["K1-P1"]["read"]["years"]) >= {"2025年"}


def test_render_and_check_have_no_codes_or_returns():
    res = A.analyze(_synthetic(0.003, 0.003, seed=4))
    md = A.render_md({"generated_at": "x", "prereg_sha256": "0" * 64, "result": dict(res, n_codes=520)})
    assert "## まとめ" in md and "目隠しではない" in md and "投資助言ではありません" in md and "板寄せ" in md and "B かつ C" in md
    assert "計算できず" in A.render_md({"generated_at": "x", "result": {"error": "e"}})
    out = A.check_summary(_synthetic(0.003, 0.003, seed=5), {"daily": [], "h1": [], "m5": []}, 520, None)
    assert not any(w in repr(out) for w in ("mean", "value", "net", "'win'")) and out["eras"]["e3"]["days"] == 20
    assert set(out["eras"]["e2"]["groups"]) == {"L1", "L2", "L3"} | {f"{g}-{p}" for g, _ in K.MARKS for p, *_ in K.POPS}


def test_workflow_and_sync_forbidden():
    wf = open(".github/workflows/auction-lab.yml", encoding="utf-8").read()
    assert "python -u auction_lab.py --check" in wf and "restore-keys: jp-bars-" in wf
    assert "python tests/test_auction_lab.py" in wf and "auction-lab.json auction-lab.md" in wf and "options: [check, run]" in wf
    assert '"auction-lab.json", "auction-lab.md"' in open("check_site_consistency.py", encoding="utf-8").read()


if __name__ == "__main__":
    sys.path.insert(0, os.path.join(ROOT, "tests"))
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
