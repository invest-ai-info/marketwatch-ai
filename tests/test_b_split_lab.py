# -*- coding: utf-8 -*-
"""J38 目印B の取り分はどこにあるか（b_split_lab.py）のテスト。2026-10-08 新設。

値動きはすべて作り物。確かめること＝①事前登録と定数の一致（区切り・境目・幅・選ぶ時代と確かめる時代）②箱の分け方（下の端を
含み上の端を含まない）③選び方（E1・E2 だけ・両方でほかの箱より高い・30件以上）④確かめ方の言葉（差の幅・その箱だけの幅）
⑤点検は損益を出さない・出力に銘柄コードを出さない ⑥ワークフローと SYNC 禁忌。

実行:  python tests/test_b_split_lab.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import b_split_lab as S  # noqa: E402


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "## J38 目印B の売りの取り分はどこにあるか" in text and "**下の区切りごとの数字はまだ誰も見ていない**" in text
    assert [s[2] for s in S.SPLITS] == [(0.01, 0.03, 0.06), (0.05, 0.10, 0.15), (10.0, 30.0, 100.0)]
    assert "+1〜3％／+3〜6％／+6％以上" in text and "+5〜10％／+10〜15％／+15％以上" in text and "10〜30億円／30〜100億円／100億円以上" in text
    assert S.N_Q == 3 and abs(S.ALPHA - 0.05 / 3) < 1e-12 and "p＜0.05÷3＝98.33％" in text and S.MIN_N == 30
    assert S.PICK == ("e1", "e2") and S.TEST == "e3" and "E1・E2 それぞれ30件以上なら**選ぶ**" in text


def test_bin_of_edges():
    got = S.bin_of(np.array([0.005, 0.01, 0.0299, 0.03, 0.06, 0.5, np.nan]), (0.01, 0.03, 0.06))
    assert got.tolist() == [-1, 0, 0, 1, 2, 2, -1]
    assert S.bin_of(np.array([10.0, 29.9, 30.0, 100.0]), (10.0, 30.0, 100.0)).tolist() == [0, 0, 1, 2]


def _row(day, code, gap, rc, turnover, rprev):
    r = np.full(len(S.C), np.nan)
    r[[S.C["day"], S.C["code"], S.C["gap"], S.C["rprev"], S.C["turnover"], S.C["tv_ratio"], S.C["rclose"], S.C["rhigh"], S.C["rlow"]]] = \
        [day, code, gap, rprev, turnover, 1.0, rc, max(rc, 0), min(rc, 0)]
    return r


def _synthetic(big_own, small_own, e3_big_own=None, n=520, days_per_era=25, seed=1):
    """目印B の株（25％）の窓は +1〜10％。窓が +6％以上なら big_own、それ未満なら small_own だけ下がる（E3 は e3_big_own）"""
    rng = np.random.default_rng(seed)
    rows = []
    for era, start in enumerate(("2008-03-03", "2018-03-01", "2025-03-03")):
        d0 = dt.date.fromisoformat(start)
        days = [d for d in (d0 + dt.timedelta(i) for i in range(days_per_era * 2)) if d.weekday() < 5][:days_per_era]
        for d in days:
            up = rng.uniform(size=n) < 0.25
            for c in range(n):
                if up[c]:
                    gap = rng.uniform(0.011, 0.10)
                    big = e3_big_own if (era == 2 and e3_big_own is not None) else big_own
                    own = big if gap >= 0.06 else small_own
                    rows.append(_row(d.toordinal(), c, gap, -own + rng.normal(0, 0.01), rng.uniform(10.5, 300), rng.uniform(0.05, 0.25)))
                else:
                    rows.append(_row(d.toordinal(), c, rng.normal(0, 0.002), rng.normal(0, 0.004), 15.0, 0.0))
    return np.array(rows)


def _all_tai(X):
    return np.ones(len(X), bool)


def test_pick_and_confirm():
    res = S.analyze(_synthetic(0.02, 0.0), _all_tai)
    w = res["splits"]["W"]
    assert w["pick"] == 2 and w["summary"] == S.OK and w["diff"]["lo"] > 0 and w["own"]["lo"] > 0
    assert all(w["choose"]["checks"][e]["ok"] for e in ("e1", "e2")) and "e3" not in w["choose"]["checks"]
    assert w["read"]["e3"][2]["mean"] > w["read"]["e3"][0]["mean"] and w["read"]["e1"][0]["per_day"] > 0
    gone = S.analyze(_synthetic(0.02, 0.005, e3_big_own=0.005, seed=2), _all_tai)["splits"]["W"]   # 最近の時代では差が消える
    assert gone["pick"] == 2 and gone["summary"] == S.PLUS_ONLY
    flat = S.analyze(_synthetic(0.0, 0.0, seed=5), _all_tai)["splits"]          # どの箱にも差が無い（偶然 ✅ になる種もある＝確率は小さい）
    assert all(x["summary"] in (S.NOT_PICKED, S.NONE) for x in flat.values())


def test_choose_needs_both_old_eras():
    v = np.array([0.02] * 40 + [0.0] * 40 + [-0.01] * 40 + [0.01] * 40)
    bins = np.array([2] * 40 + [0] * 40 + [2] * 40 + [0] * 40)
    era = {"e1": np.r_[np.ones(80, bool), np.zeros(80, bool)], "e2": np.r_[np.zeros(80, bool), np.ones(80, bool)]}
    pick, info = S.choose(v, np.ones(160, bool), bins, era)
    assert pick is None and info["candidate"] in (0, 2) and not all(c["ok"] for c in info["checks"].values())
    pick2, _ = S.choose(np.r_[v[:80], v[:80]], np.ones(160, bool), bins, era)
    assert pick2 == 2


def test_check_and_render_have_no_codes_or_returns():
    A = _synthetic(0.01, 0.0, seed=4)
    out = S.check_summary(A, _all_tai, 260, {"daily": [], "h1": [], "m5": []}, 520, None)
    e = out["eras"]["e1"]
    assert out["n_list"] == 260 and e["B_taishaku"] == sum(v for k, v in e["W"].items() if k != "outside") + e["W"]["outside"]
    assert e["W"]["outside"] == 0 and e["P"]["outside"] == 0 and e["T"]["outside"] == 0
    assert not any(w in repr(out) for w in ("mean", "value", "'win'", "lo'"))
    res = S.analyze(A, _all_tai)
    md = S.render_md({"generated_at": "x", "prereg_sha256": "0" * 64, "result": dict(res, list_note="テスト", n_codes=520)})
    assert "## まとめ" in md and "E1・E2 だけで箱を選び、E3 で確かめる" in md and "投資助言ではありません" in md and "すべての株・読むだけ" in md
    assert "計算できず" in S.render_md({"generated_at": "x", "result": {"error": "e"}})


def test_workflow_and_sync_forbidden():
    wf = open(".github/workflows/b-split-lab.yml", encoding="utf-8").read()
    assert "python -u b_split_lab.py --check" in wf and "options: [check, run]" in wf and "restore-keys: jp-bars-" in wf
    assert "python tests/test_b_split_lab.py" in wf and "b-split-lab.json b-split-lab.md" in wf and "openpyxl" in wf
    assert '"b-split-lab.json", "b-split-lab.md"' in open("check_site_consistency.py", encoding="utf-8").read()


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
