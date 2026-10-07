# -*- coding: utf-8 -*-
"""J27 最初の5分の大きな動きのあと、足を1本空けても戻るか（open5_skip_lab.py）のテスト。2026-10-07 夜 新設。

値動きはすべて作り物。確かめること＝①事前登録と定数の一致 ②行（9:00 の足がある朝だけ・寄り＝日足の始値・各時刻の値・
費用はその朝より前の日足だけ・下限）③組と500銘柄の朝 ④判定（跳ね返りだけなら見えない・本物の戻りなら上・費用で消える）
⑤点検は損益を出さない・出力に銘柄コードを出さない ⑥ワークフローと SYNC 禁忌。

実行:  python tests/test_open5_skip_lab.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import open5_skip_lab as K  # noqa: E402
import test_highs_trap_lab as TL  # noqa: E402

JST = TL.JST


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "## J27 最初の5分で大きく動いた株は、足を1本空けても 9:30 までに戻るか" in text
    assert (K.BIG, K.FLAT, K.MIN_STOCKS) == (0.01, 0.003, 500) and "**下げた＝−1％以下**" in text
    assert K.N_Q == 3 and abs(K.ALPHA - 0.05 / 3) < 1e-12 and "98.33％の幅＝p＜0.05÷3" in text
    assert "**9:10 に買って 9:30 に売る**" in text and "**独立した確かめではない**" in text


def _bars(day, prices, start=(9, 0)):
    """5分足：prices＝[(始, 高, 安, 終)]。start の時刻から5分おき"""
    t0 = dt.datetime.combine(dt.date.fromisoformat(day), dt.time(*start), JST)
    return [(t0 + dt.timedelta(minutes=5 * i), o, h, lo, c, 1e3) for i, (o, h, lo, c) in enumerate(prices)]


def _daily(days, op=100.0):
    rng = np.random.default_rng(3)
    out, c = [], 100.0
    for d in days:
        o = c
        c2 = o * (1 + rng.normal(0, 0.01))
        out.append((d, o, max(o, c2) * 1.005, min(o, c2) * 0.995, c2, 1e5))
        c = c2
    return out


def test_rows_values_and_morning_rules():
    days = TL._bdays("2026-05-01", 90)
    daily = _daily(days)
    d, d_late, d_none = days[80], days[81], days[82]
    op = daily[80][1]
    m5 = {d: _bars(d, [(op, op, op * 0.97, op * 0.98), (op * 0.98, op * 0.99, op * 0.98, op * 0.985),
                       (op * 0.985, op * 0.99, op * 0.98, op * 0.99)] + [(op * 0.99, op, op * 0.99, op)] * 3),
          d_late: _bars(d_late, [(op, op, op, op)] * 6, start=(9, 5)),                 # 9:00 の足が無い朝は使わない
          d_none: _bars(d_none, [(op, op, op, op)] * 2)}                               # 9:10 のあと足が無い＝J22 と同じく直前の値（30分以内）
    A = K.stock_rows(7, daily, m5)
    assert len(A) == 2 and (A[:, K.C["code"]] == 7).all()
    assert A[1, K.C["r910"]] == 0.0 and A[1, K.C["day"]] == dt.date.fromisoformat(d_none).toordinal()
    r = A[0]
    assert abs(r[K.C["f5"]] - (-0.02)) < 1e-12                                          # 9:00 の足の終値 ÷ 寄り
    assert abs(r[K.C["r905_910"]] - (0.985 / 0.98 - 1)) < 1e-12 and abs(r[K.C["r910"]] - (1 / 0.985 - 1)) < 1e-12
    assert abs(r[K.C["r915"]] - (1 / 0.99 - 1)) < 1e-12 and abs(r[K.C["r905"]] - (1 / 0.98 - 1)) < 1e-12
    import cost_recount_lab as CR
    sp = CR.ar_spread_avg(daily)
    assert abs(r[K.C["cost"]] - max(sp[d], 0.001)) < 1e-15
    assert abs(r[K.C["turnover"]] - daily[79][4] * daily[79][5] / 1e8) < 1e-9


def _synthetic(kind, n_days=40, n=520, seed=1):
    """kind：bounce＝9:05 だけ下に付く見かけ／real＝9:10 からも戻る／none＝何もない"""
    rng = np.random.default_rng(seed)
    rows = []
    for d in TL._bdays("2026-08-03", n_days):
        o = dt.date.fromisoformat(d).toordinal()
        f5 = rng.choice([-0.015, 0.0, 0.015], size=n, p=[0.15, 0.7, 0.15])
        noise = rng.normal(0, 0.003, n)
        f5 = f5 + noise * (np.abs(f5) > 0)
        down = f5 <= -0.01
        bounce = np.where(down & (kind == "bounce"), 0.005, 0.0)
        drift = np.where(down & (kind == "real"), 0.012, 0.0)
        r910 = drift + rng.normal(0, 0.004, n)
        r905_910 = bounce + rng.normal(0, 0.002, n)
        r905 = (1 + r905_910) * (1 + r910) - 1
        for c in range(n):
            rows.append((o, c, f5[c], r905[c], r910[c], r910[c], r905_910[c], 5.0, 0.004))
    return np.array(rows, float)


def test_judges_split_bounce_from_real():
    real = K.analyze(_synthetic("real"))
    assert real["judges"]["Q1"]["direction"] == K.UP and real["judges"]["Q3"]["ok"], real["judges"]["Q3"]
    assert real["summary"]["W2"].startswith("兆し") and real["sample"]["days"] == 40
    bounce = K.analyze(_synthetic("bounce", seed=2))
    assert bounce["judges"]["Q1"]["direction"] is None and "見かけ" in bounce["summary"]["W2"]
    assert bounce["reading"]["by_group"]["down"]["r905_910"]["mean"] > 0.004            # 跳ね返りは読むための表に出る
    thin = _synthetic("real", seed=3)
    thin[:, K.C["cost"]] = 0.02                                                       # 費用が戻りより大きい
    t = K.analyze(thin)
    assert t["judges"]["Q1"]["direction"] == K.UP and not t["judges"]["Q3"]["ok"] and "費用で消える" in t["summary"]["W2"]


def test_mornings_need_500_stocks():
    A = _synthetic("none", n_days=3, n=520)
    A = np.vstack([A, _synthetic("none", n_days=1, n=100, seed=9) + np.array([5, 0, 0, 0, 0, 0, 0, 0, 0])])
    assert len(np.unique(K.mornings(A)[:, K.C["day"]])) == 3


def test_render_and_check_have_no_codes_or_returns():
    res = K.analyze(_synthetic("real"))
    md = K.render_md({"generated_at": "x", "prereg_sha256": "0" * 64, "result": dict(res, n_codes=520)})
    assert "## まとめ" in md and "読むための表" in md and "投資助言ではありません" in md and "独立した確かめではない" in md
    assert "計算できず" in K.render_md({"generated_at": "x", "result": {"error": "e"}})
    out = K.check_summary(_synthetic("real"), {"daily": [], "m5": []}, 520, None)
    assert not any(w in repr(out) for w in ("mean", "value", "r910", "net")) and out["days"] == 40
    assert set(out["groups"]) == {"down", "up", "flat"}


def test_workflow_and_sync_forbidden():
    wf = open(".github/workflows/open5-skip-lab.yml", encoding="utf-8").read()
    assert "python -u open5_skip_lab.py --check" in wf and "restore-keys: jp-bars-" in wf
    assert "python tests/test_open5_skip_lab.py" in wf and "open5-skip-lab.json open5-skip-lab.md" in wf and "options: [check, run]" in wf
    assert '"open5-skip-lab.json", "open5-skip-lab.md"' in open("check_site_consistency.py", encoding="utf-8").read()


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
