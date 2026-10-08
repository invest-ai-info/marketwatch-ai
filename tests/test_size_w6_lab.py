# -*- coding: utf-8 -*-
"""J39 目印B・貸借銘柄・窓 +6％以上だけの建玉の大きさ（size_w6_lab.py）のテスト。2026-10-08 新設。

値動きはすべて作り物。確かめること＝①事前登録と定数の一致（J38 の箱・J37 と同じ物差し）②窓 +6％以上と貸借銘柄に絞ること・
1朝1銘柄は窓がいちばん大きいもの ③収まる大きさと J37 の参考の並び ④点検は損益を出さない・出力に銘柄コードを出さない
⑤ワークフローと SYNC 禁忌。

実行:  python tests/test_size_w6_lab.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import size_tai_lab as Z37  # noqa: E402
import size_w6_lab as W  # noqa: E402


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "## J39 目印B・貸借銘柄・今朝のその銘柄だけの窓 +6％以上だけを売る形で" in text and "**目隠しではない**" in text
    assert W.W6 == 0.06 and W.FORMS == Z37.FORMS and W.SIZES == Z37.SIZES == (0.01, 0.02, 0.03, 0.05, 0.10)
    assert [s for s, _ in W.SCOPES] == ["all", "one"] and "**1朝1銘柄**（その朝の該当銘柄のうち、その銘柄だけの窓がいちばん大きいもの）" in text


def _row(day, code, gap, rc, turnover=15.0, rprev=0.0):
    r = np.full(len(W.C), np.nan)
    r[[W.C["day"], W.C["code"], W.C["gap"], W.C["rprev"], W.C["turnover"], W.C["tv_ratio"], W.C["rclose"], W.C["rhigh"], W.C["rlow"]]] = \
        [day, code, gap, rprev, turnover, 1.0, rc, max(rc, 0), min(rc, 0)]
    return r


def _synthetic(n=520, days_per_era=20, seed=1):
    """目印B の株（20％）の窓は +2〜10％。窓 +6％以上は 1.5％、それ未満は 0.3％ だけ下がる"""
    rng = np.random.default_rng(seed)
    rows = []
    for start in ("2008-03-03", "2018-03-01", "2025-03-03"):
        d0 = dt.date.fromisoformat(start)
        days = [d for d in (d0 + dt.timedelta(i) for i in range(days_per_era * 2)) if d.weekday() < 5][:days_per_era]
        for d in days:
            up = rng.uniform(size=n) < 0.2
            for c in range(n):
                if up[c]:
                    gap = rng.uniform(0.02, 0.10)
                    rows.append(_row(d.toordinal(), c, gap, -(0.015 if gap >= 0.06 else 0.003) + rng.normal(0, 0.004), rprev=0.06))
                else:
                    rows.append(_row(d.toordinal(), c, rng.normal(0, 0.002), rng.normal(0, 0.004)))
    return np.array(rows)


def _is_tai(X):
    return X[:, W.C["code"]].astype(int) % 2 == 0


def test_masks_and_one_per_morning():
    import prevgap_lab as PG
    A, idio = PG.idio_gap(_synthetic())
    base, w6 = W.masks(A, idio, _is_tai(A))
    assert w6.sum() < base.sum() and (idio[w6] >= W.W6).all() and _is_tai(A)[w6].all() and not (w6 & ~base).any()
    one = W.top1_by(A, w6, idio)
    days = A[one, W.C["day"]]
    assert len(days) == len(np.unique(days)) == len(np.unique(A[w6, W.C["day"]]))      # 1朝に1銘柄
    for d in np.unique(days)[:5]:                                                      # その朝の窓がいちばん大きいもの
        m = w6 & (A[:, W.C["day"]] == d)
        assert idio[one & (A[:, W.C["day"]] == d)][0] == idio[m].max()
    assert not W.top1_by(A, np.zeros(len(A), bool), idio).any()


def test_analyze_fit_trades_and_reference():
    res = W.analyze(_synthetic(), _is_tai)
    assert set(res["forms"]) == {"B0-all", "B0-one", "B10-all", "B10-one"}
    x = res["forms"]["B0-all"]
    assert x["fit"] == 0.10 and x["ref"]["fit"] == 0.10                                  # 損の小さい作り物＝10％まで収まる
    t = x["trades"]["e2"]
    assert t["n"] > 0 and t["mean"] > 0.01 and x["trades"]["e2"]["n"] < x["ref"]["eras"]["e2"]["trades"]
    assert x["eras"]["e2"]["sizes"]["0.03"]["cagr"] > 0 and res["forms"]["B0-one"]["trades"]["e1"]["n"] <= 20


def test_check_and_render_have_no_codes_or_returns():
    A = _synthetic(seed=4)
    out = W.check_summary(A, _is_tai, 260, {"daily": [], "h1": [], "m5": []}, 520, None)
    e = out["eras"]["e1"]
    assert out["n_list"] == 260 and 0 < e["w6-all"]["rows"] < e["j37-all"]["rows"] and e["w6-one"]["rows"] == e["w6-one"]["days"]
    assert not any(w in repr(out) for w in ("mean", "cagr", "final", "worst"))
    md = W.render_md({"generated_at": "x", "prereg_sha256": "0" * 64, "result": dict(W.analyze(A, _is_tai), list_note="テスト", n_codes=520)})
    assert "## まとめ" in md and "参考：J37" in md and "1回ごとの数字" in md and "投資助言ではありません" in md and "目隠しではない" in md
    assert "計算できず" in W.render_md({"generated_at": "x", "result": {"error": "e"}})


def test_workflow_and_sync_forbidden():
    wf = open(".github/workflows/size-w6-lab.yml", encoding="utf-8").read()
    assert "python -u size_w6_lab.py --check" in wf and "options: [check, run]" in wf and "restore-keys: jp-bars-" in wf
    assert "python tests/test_size_w6_lab.py" in wf and "size-w6-lab.json size-w6-lab.md" in wf and "openpyxl" in wf
    assert '"size-w6-lab.json", "size-w6-lab.md"' in open("check_site_consistency.py", encoding="utf-8").read()


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
