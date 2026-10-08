# -*- coding: utf-8 -*-
"""J37 貸借銘柄だけの目印B で建玉の大きさと落ち込み（size_tai_lab.py）のテスト。2026-10-08 新設。

値動きはすべて作り物。確かめること＝①事前登録と定数の一致（J33 と同じ大きさ・守りの決まり）②貸借銘柄だけに絞ること・
上位3は貸借銘柄の中で選ぶこと ③収まる大きさの判定（J33 と同じ式）④点検は損益を出さない・出力に銘柄コードを出さない
⑤ワークフローと SYNC 禁忌。

実行:  python tests/test_size_tai_lab.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import size_short_lab as SZ  # noqa: E402
import size_tai_lab as Z  # noqa: E402


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "## J37 貸借銘柄だけの目印B で、建玉の大きさと落ち込みを数え直す（J33 の現実版）" in text and "**目隠しではない**" in text
    assert Z.SIZES == SZ.SIZES == (0.01, 0.02, 0.03, 0.05, 0.10) and Z.GROUP == "K2"
    assert [f for f, _ in Z.FORMS] == ["B0", "B10"] and Z.FORMS[1][1] == 0.10 and [s for s, _ in Z.SCOPES] == ["all", "top3"]
    assert "目印C は J36 で ✕ だったので入れない" in text and "**こちらの「収まる大きさ」**を使う" in text


def _row(day, code, gap, rc, turnover=15.0, rprev=0.0, ratio=1.0, rh=None):
    r = np.full(len(Z.C), np.nan)
    r[[Z.C["day"], Z.C["code"], Z.C["gap"], Z.C["rprev"], Z.C["turnover"], Z.C["tv_ratio"], Z.C["rclose"], Z.C["rhigh"], Z.C["rlow"]]] = \
        [day, code, gap, rprev, turnover, ratio, rc, max(rc, 0) if rh is None else rh, min(rc, 0)]
    return r


def _synthetic(own_tai, own_other, n=520, days_per_era=20, seed=1):
    """目印B の株（20％）のうち、偶数の番号＝貸借銘柄は own_tai、奇数は own_other だけ下がる。売買代金は番号が大きいほど大きい"""
    rng = np.random.default_rng(seed)
    rows = []
    for start in ("2008-03-03", "2018-03-01", "2025-03-03"):
        d0 = dt.date.fromisoformat(start)
        days = [d for d in (d0 + dt.timedelta(i) for i in range(days_per_era * 2)) if d.weekday() < 5][:days_per_era]
        for d in days:
            up = rng.uniform(size=n) < 0.2
            for c in range(n):
                own = (own_tai if c % 2 == 0 else own_other) if up[c] else 0.0
                rows.append(_row(d.toordinal(), c, (0.04 if up[c] else 0.0) + rng.normal(0, 0.002), -own + rng.normal(0, 0.004),
                                 turnover=11.0 + c, rprev=0.06 if up[c] else 0.0))
    return np.array(rows)


def _is_tai(X):
    return X[:, Z.C["code"]].astype(int) % 2 == 0


def test_bases_and_top3_inside_the_list():
    import prevgap_lab as PG
    import stop_short_lab as SS
    A, idio = PG.idio_gap(_synthetic(0.01, 0.0))
    b = Z.bases(A, idio, _is_tai(A))
    assert b["tai"].sum() < b["all"].sum() and not (b["tai"] & ~_is_tai(A)).any() and (b["all"] & ~_is_tai(A)).any()
    top = SS.top_mask(A, b["tai"])
    per_day = np.bincount(np.unique(A[top, Z.C["day"]], return_inverse=True)[1])
    assert per_day.max() == 3 and _is_tai(A)[top].all()                     # 上位3は貸借銘柄の中から


def test_analyze_fit_and_compare():
    res = Z.analyze(_synthetic(0.01, 0.0), _is_tai)
    assert set(res["forms"]) == {"B0-all", "B0-top3", "B10-all", "B10-top3"}
    x = res["forms"]["B0-all"]
    assert x["tai"]["fit"] == 0.10 and x["all"]["fit"] is not None             # 損の小さい作り物＝10％まで収まる
    q_tai, q_all = x["tai"]["eras"]["e2"], x["all"]["eras"]["e2"]
    assert q_tai["trades"] < q_all["trades"] and q_tai["sizes"]["0.03"]["cagr"] > q_all["sizes"]["0.03"]["cagr"]
    # 1回の最悪 −25％（ストップ高）が貸借銘柄にあれば、収まるのは 1・2・3％ まで（J33 と同じ式）
    A = _synthetic(0.01, 0.0, seed=2)
    hit = np.where((A[:, Z.C["code"]] == 0) & (A[:, Z.C["rprev"]] > 0))[0][0]
    A[hit, Z.C["rclose"]] = 0.25 - Z.SS.COST                            # 売りの損益がちょうど −25％
    worst = Z.analyze(A, _is_tai)["forms"]["B0-all"]["tai"]
    assert worst["fit"] == 0.03 and min(worst["eras"][e]["worst_trade"] for e in ("e1", "e2", "e3")) < -0.24


def test_check_and_render_have_no_codes_or_returns():
    A = _synthetic(0.005, 0.0, seed=4)
    out = Z.check_summary(A, _is_tai, 260, {"daily": [], "h1": [], "m5": []}, 520, None)
    assert out["n_list"] == 260 and out["eras"]["e1"]["tai-all"]["rows"] > 0 and out["eras"]["e1"]["tai-top3"]["days"] == 20
    assert not any(w in repr(out) for w in ("mean", "cagr", "final", "worst"))
    res = Z.analyze(A, _is_tai)
    md = Z.render_md({"generated_at": "x", "prereg_sha256": "0" * 64, "result": dict(res, list_note="テスト", n_codes=520)})
    assert "## まとめ" in md and "参考：すべての株（J33）" in md and "投資助言ではありません" in md and "目隠しではない" in md
    assert "計算できず" in Z.render_md({"generated_at": "x", "result": {"error": "e"}})


def test_workflow_and_sync_forbidden():
    wf = open(".github/workflows/size-tai-lab.yml", encoding="utf-8").read()
    assert "python -u size_tai_lab.py --check" in wf and "options: [check, run]" in wf and "restore-keys: jp-bars-" in wf
    assert "python tests/test_size_tai_lab.py" in wf and "size-tai-lab.json size-tai-lab.md" in wf and "openpyxl" in wf
    assert '"size-tai-lab.json", "size-tai-lab.md"' in open("check_site_consistency.py", encoding="utf-8").read()


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
