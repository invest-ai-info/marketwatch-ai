# -*- coding: utf-8 -*-
"""J41 日本の早い月末月初を個別株の籠で（tom_basket_lab.py）のテスト。2026-10-08 新設。

値動きはすべて作り物。確かめること＝①事前登録と定数の一致（R3 Q3 と同じ窓・費用 0.02％・10億円以上）②終値どうしの損益率と籠
③窓とふつうの日の決め方（月の最後から6日目の引けで買う・翌月の2日目の引けで売る）④判定の言葉 ⑤上位10銘柄（買った日の銘柄を持つ）
⑥点検は損益を出さない・出力に銘柄コードを出さない ⑦ワークフロー・SYNC 禁忌・検証済みリスト。

実行:  python tests/test_tom_basket_lab.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import tom_basket_lab as M  # noqa: E402


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "## J41 日本の早い月末月初（R3 Q3 の窓）を" in text and "**目隠しではない**" in text
    assert (M.TV_MIN, M.BACK, M.AHEAD, M.WIN, M.COST, M.TOP) == (10.0, 5, 2, 7, 0.0002, 10) and "費用 **0.02％**" in text
    assert "R3 Q3 と同じ＝月の最後から6日目の引けで買い、翌月の2日目の引けで売る" in text and M.ALPHA == 0.05


def test_windows_follow_r3():
    days = [dt.date(2026, 1, d).toordinal() for d in range(5, 31) if dt.date(2026, 1, d).weekday() < 5]
    days += [dt.date(2026, 2, d).toordinal() for d in (2, 3, 4)]
    (buy, w, normal), = M.windows(days)
    jan = [d for d in days if dt.date.fromordinal(d).month == 1]
    assert buy == jan[-6] and w == jan[-5:] + days[-3:-1] and normal == jan[2:-5] and len(w) == 7


def _row(day, code, gap, rc, tv):
    r = np.full(len(M.C), np.nan)
    r[[M.C["day"], M.C["code"], M.C["gap"], M.C["rclose"], M.C["turnover"]]] = [day, code, gap, rc, tv]
    return r


def _synthetic(win_bump, n=60, seed=1, start="2006-01-02", end="2026-09-30"):
    """全部の銘柄が毎日小さく動き、月末月初の窓の日だけ win_bump だけ上げる（売買代金は番号が大きいほど大きい）。
    作り物は 60 銘柄なので、500銘柄未満の日を除く線はテストの中だけ 50 に下げる"""
    rng = np.random.default_rng(seed)
    days = np.array([d for d in range(dt.date.fromisoformat(start).toordinal(), dt.date.fromisoformat(end).toordinal() + 1)
                     if dt.date.fromordinal(d).weekday() < 5])
    hot = {d for _, w, _ in M.windows(list(days)) for d in w}
    bump = np.array([win_bump if d in hot else 0.0 for d in days])
    A = np.full((len(days) * n, len(M.C)), np.nan)
    A[:, M.C["day"]] = np.repeat(days, n)
    A[:, M.C["code"]] = np.tile(np.arange(n), len(days))
    A[:, M.C["gap"]] = 0.0
    A[:, M.C["rclose"]] = np.repeat(bump, n) + rng.normal(0, 0.004, len(days) * n)
    A[:, M.C["turnover"]] = 1.0 + A[:, M.C["code"]] * 0.5
    return A


class _FewStocks:
    def __enter__(self):
        self.old = M.PG.MIN_STOCKS
        M.PG.MIN_STOCKS = 50

    def __exit__(self, *a):
        M.PG.MIN_STOCKS = self.old


def test_returns_basket_and_judge():
    A = np.array([_row(1, 0, 0.01, 0.02, 15.0), _row(1, 1, 0.0, -0.01, 5.0), _row(1, 2, 0.0, 0.03, 20.0)])
    r = M.daily_returns(A)
    assert abs(r[0] - (1.01 * 1.02 - 1)) < 1e-12 and abs(M.basket(A, r)[1] - ((1.01 * 1.02 - 1) + 0.03) / 2) < 1e-12
    assert M.basket(A, r, 10.0, 18.0) == {1: r[0]}
    up = {"lo": 0.001}
    flat = {"lo": -0.01}
    assert M.verdict({"e1": up, "e2": up, "e3": up}) == M.OK and M.verdict({"e1": flat, "e2": flat, "e3": up}) == M.NEW_ONLY
    assert M.verdict({"e1": up, "e2": up, "e3": flat}) == M.OLD_ONLY and M.verdict({"e1": up, "e2": flat, "e3": flat}) == M.NONE


def test_analyze_end_to_end():
    with _FewStocks():
        _end_to_end()


def _end_to_end():
    A = _synthetic(0.003)
    res = M.analyze(A)
    assert res["summary"] == M.OK and res["judge"]["e3"]["lo"] > 0
    e3 = res["read"]["e3"]
    assert abs(e3["win_mean"] - ((1.003 ** 7) - 1 - M.COST)) < 0.002 and res["eras"]["e3"]["months"] in range(34, 38)
    assert e3["top10_months"] > 30 and abs(e3["top10_win_mean"] - e3["win_mean"]) < 0.004
    assert set(e3["tiers"]) == {"10〜30億円", "30〜100億円", "100億円以上"}
    flat = M.analyze(_synthetic(0.0, seed=2))
    assert flat["summary"] in (M.NONE, M.OLD_ONLY, M.NEW_ONLY) and M.verdicts_of(dict(flat, summary=M.NONE), "x")["Q1"]["status"] == "stop"
    md = M.render_md({"generated_at": "x", "prereg_sha256": "0" * 64, "result": res})
    assert "## まとめ" in md and "上位10銘柄" in md and "投資助言ではありません" in md
    assert "計算できず" in M.render_md({"generated_at": "x", "result": {"error": "e"}})
    out = M.check_summary(A, {"daily": [], "h1": [], "m5": []}, 60, None)
    assert out["eras"]["e2"]["months"] > 70 and out["eras"]["e1"]["basket_per_day_min"] == 42
    assert not any(w in repr(out) for w in ("mean", "'win", "diff"))


def test_workflow_sync_and_verified_list():
    wf = open(".github/workflows/tom-basket-lab.yml", encoding="utf-8").read()
    assert "python -u tom_basket_lab.py --check" in wf and "options: [check, run]" in wf and "restore-keys: jp-bars-" in wf
    assert "python tests/test_tom_basket_lab.py" in wf and "tom-basket-lab.json tom-basket-lab.md verified-list.md" in wf
    assert '"tom-basket-lab.json", "tom-basket-lab.md"' in open("check_site_consistency.py", encoding="utf-8").read()
    assert '"tom-basket-lab.json"' in open("verified_list.py", encoding="utf-8").read()


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
