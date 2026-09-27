# -*- coding: utf-8 -*-
"""前向きの観察（combo_forward.py）のテスト。2026-09-27 新設。

値動きはすべて作り物（ネットワークに出ない）。確かめること＝①相性ラボ（combo_lab.entries_for）と同じ取引・同じ R になる
②登録前の取引は数えない・60本たっていない取引は数えない ③区切りの判定の順番 ④一度出た区切りは書き換えない
⑤保険の回は今月分があれば何もしない ⑥事前登録と定数の一致。

実行:  python tests/test_combo_forward.py     （pytest 不要。pytest でも動く）
"""
import json
import os
import sys
import tempfile

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import combo_forward as F  # noqa: E402
import combo_lab as C  # noqa: E402


def _df(seed, n=1500, start="2022-01-03"):
    rng = np.random.default_rng(seed)
    c = 100 * np.exp(np.cumsum(rng.normal(0.0002, 0.01, n)))
    o = np.concatenate([[c[0]], c[:-1]]) * (1 + rng.normal(0, 0.002, n))
    return pd.DataFrame({"Open": o, "High": np.maximum(o, c) * 1.004, "Low": np.minimum(o, c) * 0.996, "Close": c},
                        index=pd.bdate_range(start, periods=n))


def test_prereg_numbers_match_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "## 前向きの観察：一目均衡表 × ボリンジャー下限タッチ × 追いかける損切り" in text
    assert F.FWD_START == "2026-09-28" and "入る日が 2026-09-28 以降" in text
    assert (F.TREND, F.OSC, F.EXIT) == ("T4", "O4", "X6") and "（T4）" in text and "（O4）" in text and "（X6）" in text
    assert F.CAP == 60 and "入ってから60本がすぎた取引だけ" in text
    assert F.CHECKS == (50, 100, 150) and "50件・100件・150件" in text
    assert F.P_LIMIT == 0.05 and "p＜0.05（両側・2,000回）" in text and F.N_PERM == 2000
    assert "「銘柄」と「四半期」の二方向" in text
    assert "## 合図の組み合わせ探しの区切り" in text
    assert C.EXIT_RULE and "X6" in C.EXITS                     # 相性ラボの出口をそのまま使う


def test_same_trades_and_R_as_the_lab(monkeypatch=None):
    old = F.FWD_START
    F.FWD_START = "2023-06-01"                                   # 件数を増やして突き合わせる
    try:
        total = 0
        for seed in range(1, 5):
            df = _df(seed)
            done, open_ = F.trades_for("ES=F", df)
            lab = [e for e in C.entries_for("ES=F", df.iloc[:-1])
                   if e["osc"] == "O4" and C.trend_ok(e, "T4") and e["date"] >= F.FWD_START]
            got = sorted((x["entry"], x["sign"], round(x["R"], 12)) for x in done)
            want = sorted((e["date"], e["sign"], round(e["R"]["X6"], 12)) for e in lab)
            assert got == want, seed
            total += len(done)
            assert all(x["entry"] >= F.FWD_START for x in done + open_)
        assert total >= 10, total
    finally:
        F.FWD_START = old


def test_open_trades_are_not_counted():
    old = F.FWD_START
    F.FWD_START = "2023-06-01"
    try:
        found = 0
        for seed in range(1, 12):
            df = _df(seed)
            done, open_ = F.trades_for("ES=F", df)
            n = len(df) - 1                                        # 最後の1本は使わない
            last_ok = df.index[n - F.CAP].date().isoformat()       # 入った足＋59本＝最後の足。これより後は60本たっていない
            assert all(x["entry"] <= last_ok for x in done)
            assert all(x["entry"] > last_ok for x in open_)
            found += len(open_)
        assert found >= 1
    finally:
        F.FWD_START = old


def test_nothing_before_registration():
    done, open_ = F.trades_for("ES=F", _df(3, n=1000))             # 2025-10 で終わる
    assert done == [] and open_ == []


def test_verdict_order():
    ok = {"ok": True, "neg": False}
    no = {"ok": False, "neg": False}
    neg = {"ok": False, "neg": True}
    assert F.verdict({}) == "観察中"
    assert F.verdict({"50": ok}) == "観察中"
    assert F.verdict({"50": ok, "100": ok}) == "前向きでも残った"
    assert F.verdict({"50": no, "100": ok}) == "観察中"
    assert F.verdict({"50": no, "100": ok, "150": ok}) == "前向きでも残った"
    assert F.verdict({"50": no, "100": ok, "150": no}) == "前向きで確かめられなかった（観察終わり）"
    assert F.verdict({"50": neg}) == "前向きで消えた（はっきり負け）"
    assert F.verdict({"50": ok, "100": ok, "150": neg}) == "前向きでも残った"    # 先に起きたほうで決める


def test_checkpoints_are_never_rewritten():
    old = {"50": {"mean": 0.1, "fixed_on": "2028-10-03"}}
    new = {"50": {"mean": 0.9, "fixed_on": "2028-11-03"}, "100": {"mean": 0.2}}
    m = F.merge_checkpoints(old, new)
    assert m["50"]["mean"] == 0.1 and m["100"]["mean"] == 0.2


def test_checkpoint_uses_the_first_n_by_entry_date():
    df = _df(2)
    old = F.FWD_START
    F.FWD_START = "2023-06-01"
    try:
        done, _ = F.trades_for("ES=F", df)
        k = min(5, len(done))
        st = F.checkpoint(done, k, {"ES=F": df}, n_perm=50)
        first = F.order(done)[:k]
        assert st["n"] == k and abs(st["mean"] - np.mean([x["R"] for x in first])) < 1e-12
        assert st["last_entry"] == first[-1]["entry"]
        assert isinstance(st["ok"], bool) and isinstance(st["neg"], bool)
    finally:
        F.FWD_START = old


def test_no_checkpoint_when_a_ticker_is_missing():
    orig_fetch, orig_tickers, orig_checks = F.P.fetch, F.TL.TICKERS, F.CHECKS
    old = F.FWD_START
    try:
        F.FWD_START = "2023-01-02"
        df = _df(2)
        F.TL.TICKERS = {"ES=F": "index", "GC=F": "commodity"}
        F.P.fetch = lambda tk, *a, **k: df if tk == "ES=F" else None
        F.CHECKS = (1, 2, 3)
        r = F.run({}, "2028-10-03", n_perm=20)
        assert r["missing"] == ["GC=F"] and r["now"]["n"] >= 3 and r["checkpoints"] == {}
        F.P.fetch = lambda tk, *a, **k: df
        r = F.run({}, "2028-10-03", n_perm=20)
        assert set(r["checkpoints"]) == {"1", "2", "3"} and r["checkpoints"]["1"]["fixed_on"] == "2028-10-03"
    finally:
        F.P.fetch, F.TL.TICKERS, F.FWD_START, F.CHECKS = orig_fetch, orig_tickers, old, orig_checks


def test_quarter():
    assert F.quarter("2026-09-28") == "2026Q3" and F.quarter("2026-10-01") == "2026Q4" and F.quarter("2027-01-05") == "2027Q1"


def test_once_per_month_and_history():
    cwd = os.getcwd()
    d = tempfile.mkdtemp()
    calls = []
    orig_run, orig_sha = F.run, F.P.prereg_sha256
    try:
        os.chdir(d)
        F.P.prereg_sha256 = lambda *a, **k: "b" * 64

        def fake_run(prev, today, n_perm=F.N_PERM):
            calls.append(today)
            return {"done": [], "open": 2, "now": {"n": 0}, "checkpoints": dict(prev.get("checkpoints") or {}),
                    "verdict": "観察中", "missing": []}
        F.run = fake_run
        assert F.main([]) == 0
        assert F.main(["--once-per-month"]) == 0                     # 今月分があるので何もしない
        assert len(calls) == 1
        res = json.load(open(F.OUT_JSON, encoding="utf-8"))
        assert len(res["history"]) == 1 and res["history"][0]["open"] == 2
        assert F.main([]) == 0                                        # 手動の回は同じ月を置き換える
        res = json.load(open(F.OUT_JSON, encoding="utf-8"))
        assert len(res["history"]) == 1
        md = open(F.OUT_MD, encoding="utf-8").read()
        assert "観察中" in md and "投資助言ではありません" in md and "まだ無い" in md
    finally:
        F.run, F.P.prereg_sha256 = orig_run, orig_sha
        os.chdir(cwd)


def test_error_keeps_the_checkpoints():
    cwd = os.getcwd()
    d = tempfile.mkdtemp()
    orig_run, orig_sha = F.run, F.P.prereg_sha256
    try:
        os.chdir(d)
        F.P.prereg_sha256 = lambda *a, **k: "b" * 64
        with open(F.OUT_JSON, "w", encoding="utf-8") as fh:
            json.dump({"result": {"checkpoints": {"50": {"mean": 0.1}}}, "history": [{"month": "2028-10", "n": 50}]}, fh)

        def boom(prev, today, n_perm=F.N_PERM):
            raise RuntimeError("network")
        F.run = boom
        F.main([])
        res = json.load(open(F.OUT_JSON, encoding="utf-8"))
        assert res["result"]["checkpoints"] == {"50": {"mean": 0.1}} and res["history"] == [{"month": "2028-10", "n": 50}]
    finally:
        F.run, F.P.prereg_sha256 = orig_run, orig_sha
        os.chdir(cwd)


def test_render_with_checkpoints():
    res = {"generated_at": "x", "prereg_sha256": "a" * 64, "history": [{"month": "2028-10", "n": 50, "mean": 0.1, "lo": -0.1, "hi": 0.3, "open": 4}],
           "result": {"done": [{"entry": "2026-10-01", "ticker": "GC=F", "sign": 1.0, "R": 0.5}], "open": 4,
                      "now": {"n": 50, "mean": 0.1}, "verdict": "観察中", "missing": [],
                      "checkpoints": {"50": {"mean": 0.1, "lo": -0.1, "hi": 0.3, "placebo_mean": 0.0, "p_placebo": 0.3,
                                             "ok": False, "last_entry": "2028-06-01", "fixed_on": "2028-10-03"}}}}
    md = F.render_md(res)
    assert "| 50件 |" in md and "満たさない" in md and "GC=F" in md and "2028-10" in md


if __name__ == "__main__":
    fails = 0
    tests = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for name, fn in tests:
        try:
            fn()
            print(f"  ✅ {name}")
        except AssertionError as e:
            fails += 1
            print(f"  ❌ {name}: {e}")
    print(f"--- {len(tests) - fails}/{len(tests)} 合格 ---")
    sys.exit(1 if fails else 0)
