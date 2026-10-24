# -*- coding: utf-8 -*-
"""SE 損切りの線まで待って、同じ向きに指値で入る（stop_entry_lab.py）のテスト。2026-10-24 新設。

値動きはすべて作り物（ネットワークに出ない）。確かめること＝①事前登録と定数の一致 ②指値の約定（線を超えたら・等しいだけでは入らない・
始値が越えていれば始値）③取り消し（先に利確の値・同じ足なら約定が先・時間切れ・末尾）④入った後の出口（約定した足は利確を数えない・損切りは数える）
⑤売りは鏡 ⑥同じ足・同じ向きの合図は1つ ⑦check は損益を持たない ⑧最後まで動いて判定・検証済みリストの形・出力 ⑨ワークフローと SYNC禁忌。

実行:  python tests/test_stop_entry_lab.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import exit_ind_lab_4h as H  # noqa: E402
import stop_entry_lab as S  # noqa: E402
import trend_lab as TL  # noqa: E402

TK = "TEST"        # 費用が0になる名前（cost_r_of の表に無い・=X でもない）


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    i = text.find("\n## SE ")
    assert i >= 0
    sec = text[i:text.find("\n## ", i + 1)]
    for s in ("**テクニカルの区切りの例外**", "L＝E0−1.5A", "T＝E0＋2A", "**L を超えて動いたら**", "等しいだけでは入らない",
              "同じ足の中で L と T の両方に届いたら約定を先", "**利確は数えない**", "日足・4時間足60本・5分足36本",
              "p＜0.05÷3＝0.0167", "2,000回", "日足 2016-01-01・4時間足 2025-10-01・5分足 2024-08-01",
              "`stop_entry_lab.py`", "`stop-entry-lab.yml`", "`tests/test_stop_entry_lab.py`", "`research/loop/se_lab.py`", "`se-m5-lab.json`"):
        assert s in sec, s
    assert (S.CAP, S.RISK, S.TP_ATR, S.N_PERM) == (60, 1.5, 2.0, 2000) and abs(S.ALPHA - 0.05 / 3) < 1e-12
    assert S.FRAMES["1d"]["split"] == "2016-01-01" and S.FRAMES["4h"]["split"] == "2025-10-01" and S.SECTION == "## SE "


def _x(bars, n=None, pad=100.0):
    """bars＝[(o,h,l,c)…]（位置1から）。位置0と残りは平らな足（L にも T にも届かない）で埋める"""
    rows = [(pad, pad, pad, pad)] + list(bars)
    n = n or (len(rows) + 2 * S.CAP + 5)
    last = rows[-1][3]
    rows += [(last, last, last, last)] * (n - len(rows))
    o, h, l, c = (np.array([r[k] for r in rows], float) for k in range(4))
    return {"o": o, "h": h, "l": l, "c": c, "n": len(rows)}


# E0＝100・A＝1 → 損切りの線 L＝98.5・もとの利確 T＝102。入った後の損切り＝約定値−1.5・利確＝約定値＋2


def test_fill_at_line_then_take_profit():
    x = _x([(100, 100.5, 99.5, 100), (99.5, 99.6, 98.0, 98.8), (99.0, 100.6, 98.9, 100.4)])
    st, R, kind, cost = S.se_trade(x, 1, 1.0, 1.0, TK)
    assert (st, kind, cost) == ("fill", "tp", 0.0) and abs(R - 2.0 / 1.5) < 1e-12


def test_equal_to_line_does_not_fill_and_tp_first_cancels():
    x = _x([(100, 100.5, 98.5, 99), (99, 102.0, 98.6, 101)])      # 安値がちょうど L（入らない）→ 次の足で T に届く
    assert S.se_trade(x, 1, 1.0, 1.0, TK)[0] == "tp_first"
    gap_up = _x([(100, 101, 99, 101), (102.5, 103, 98.0, 99)])     # 始値がすでに T の上＝始値が先 → 取り消し（安値が L より下でも）
    assert S.se_trade(gap_up, 1, 1.0, 1.0, TK)[0] == "tp_first"


def test_same_bar_fill_first_and_tp_not_counted_in_fill_bar():
    x = _x([(100, 102.5, 98.0, 100)])                              # 同じ足で L と T → 約定が先。約定した足の高値は新しい利確(100.5)を越えるが数えない
    st, R, kind, _ = S.se_trade(x, 1, 1.0, 1.0, TK)
    assert st == "fill" and kind == "time" and abs(R - (100 - 98.5) / 1.5) < 1e-12     # 残りは平ら（終値100）→ 時間切れ
    st2, R2, kind2, _ = S.se_trade(x, 1, 1.0, 1.0, TK, tp_in_fill=True)              # 読むための上限では数える
    assert kind2 == "tp" and abs(R2 - 2.0 / 1.5) < 1e-12


def test_gap_below_line_fills_at_open_and_stop_in_fill_bar_counts():
    # 位置1は入る足（始値＝E0＝100）。次の足の始値が L より下 → 始値98.0で約定。同じ足で 96.5（98−1.5）に届く → 損切り
    x = _x([(100, 100.4, 99.6, 100), (98.0, 98.2, 96.0, 96.5)])
    st, R, kind, _ = S.se_trade(x, 1, 1.0, 1.0, TK)
    assert st == "fill" and kind == "sl" and abs(R + 1.0) < 1e-12
    x2 = _x([(100, 100.2, 98.0, 98.4), (96.0, 96.5, 95.5, 96)])    # 入る足のうちに L で約定 → 次の足の始値が損切り(97.0)より下 → 始値で出る
    st2, R2, kind2, _ = S.se_trade(x2, 1, 1.0, 1.0, TK)
    assert kind2 == "sl" and abs(R2 - (96.0 - 98.5) / 1.5) < 1e-12


def test_timeout_and_tail():
    assert S.se_trade(_x([]), 1, 1.0, 1.0, TK)[0] == "timeout"     # 60本平ら → 約定しない
    assert S.se_trade(_x([], n=40), 1, 1.0, 1.0, TK)[0] == "tail"  # 待ちの終わりが末尾を越える
    late = [(100, 100, 100, 100)] * 55 + [(99, 99, 98.0, 98.4)]    # 56本目で約定 → 保有の終わりが末尾を越える
    assert S.se_trade(_x(late, n=1 + 56 + 30), 1, 1.0, 1.0, TK)[0] == "tail"


def test_short_is_the_mirror():
    # 売り：L＝101.5・T＝98。入った後の損切り＝約定値＋1.5・利確＝約定値−2
    x = _x([(100, 100.5, 99.5, 100), (100.5, 102.0, 100.4, 101.2), (101.0, 101.1, 99.4, 99.6)])
    st, R, kind, _ = S.se_trade(x, 1, -1.0, 1.0, TK)
    assert (st, kind) == ("fill", "tp") and abs(R - 2.0 / 1.5) < 1e-12
    assert S.se_trade(_x([(100, 100.4, 97.5, 98)]), 1, -1.0, 1.0, TK)[0] == "tp_first"


def _daily(n, seed, start="2012-01-02", p0=100.0, step="B"):
    rng = np.random.default_rng(seed)
    idx = pd.date_range(start, periods=n, freq=step)
    c = p0 * np.exp(np.cumsum(rng.standard_normal(n) * 0.012))
    df = pd.DataFrame({"Close": c}, index=idx)
    df["Open"] = df["Close"].shift(1).fillna(p0) * (1 + rng.standard_normal(n) * 0.002)
    df["High"] = df[["Open", "Close"]].max(axis=1) * (1 + np.abs(rng.standard_normal(n)) * 0.004)
    df["Low"] = df[["Open", "Close"]].min(axis=1) * (1 - np.abs(rng.standard_normal(n)) * 0.004)
    df["Volume"] = 100.0
    return df


def _hourly(n_days, seed):
    rng = np.random.default_rng(seed)
    idx = pd.date_range(dt.datetime(2024, 10, 2, tzinfo=dt.timezone.utc), periods=n_days * 24, freq="h", tz="UTC")
    c = 150 * np.exp(np.cumsum(rng.standard_normal(len(idx)) * 0.0015))
    df = pd.DataFrame({"Close": c}, index=idx)
    df["Open"] = df["Close"].shift(1).fillna(150.0)
    df["High"] = df[["Open", "Close"]].max(axis=1) * 1.0006
    df["Low"] = df[["Open", "Close"]].min(axis=1) * 0.9994
    df["Volume"] = 100.0
    return df


TWO = list(TL.TICKERS)[:2]
D1 = {tk: _daily(2000, k + 3) for k, tk in enumerate(TWO)}
H4 = {tk: H.to_4h(_hourly(730, k + 7)) for k, tk in enumerate(TWO)}


def _with_fake_loaders(fn):
    keep = {f: S.FRAMES[f]["loader"] for f in S.FRAMES}
    S.FRAMES["1d"]["loader"], S.FRAMES["4h"]["loader"] = D1.get, H4.get
    try:
        return fn()
    finally:
        for f, v in keep.items():
            S.FRAMES[f]["loader"] = v


def test_signals_are_deduped_and_check_has_no_returns():
    df = D1[TWO[0]]
    x = S.E.make_ctx(df)
    sigs = S.signals_for(TWO[0], df, x)
    keys = [(r["e"], r["sign"]) for r in sigs]
    assert len(sigs) > 0 and len(keys) == len(set(keys))
    assert sum(len(r["oscs"]) for r in sigs) >= len(sigs)
    out = _with_fake_loaders(S.check)
    for f in S.FRAMES:
        c = out[f]
        assert c["tickers"] == 2 and len(c["missing"]) == len(TL.TICKERS) - 2 and c["signals"] > 0
        assert c["fills"] + c["cancel_tp_first"] + c["cancel_timeout"] == c["signals"]
        assert c["fills_front"] + c["fills_back"] == c["fills"]
    recs = S.count_frame({TWO[0]: df}, {TWO[0]: x}, with_r=False)
    assert recs and all("R" not in r and "market" not in r for r in recs)


def test_runs_end_to_end_and_writes_the_verified_list_shape():
    res = _with_fake_loaders(lambda: S.run(n_perm=30))
    for f in S.FRAMES:
        r = res[f]
        assert "error" not in r, r.get("error")
        assert r["verdict"] in (S.VALID, S.NONE, S.NEG) and r["fills"] == r["stats"]["n"] > 0
        assert r["fills"] + r["cancel_tp_first"] + r["cancel_timeout"] == r["signals"]
        assert r["n_front"] + r["n_back"] == r["fills"] and len(r["by_entry"]) == 60
        assert r["exits"]["tp"] + r["exits"]["sl"] + r["exits"]["time"] == r["fills"]
        assert r["placebo_mean"] is not None and 0 < r["p_placebo"] <= 1
    v = S.verdicts_of(res, "2026-10-24")
    assert set(v) == {"1d", "4h"} and all(x["status"] in ("plus", "stop") and x["reason"] for x in v.values())
    out = {"generated_at": "x", "section_sha256": "b" * 64, "results": res}
    md = S.render_md(out)
    assert md.startswith("# SE 損切りの線まで待って") and "日足" in md and "4時間足" in md and "投資助言ではありません" in md


def test_judge_needs_all_three_gates():
    ok = {"n": 500, "mean": 0.10, "lo": 0.02, "hi": 0.18}
    assert S.judge(ok, 0.001, 0.0, 0.1, 0.1) == S.VALID
    assert S.judge(ok, 0.05, 0.0, 0.1, 0.1) == S.NONE           # 偽薬の p が足りない
    assert S.judge(ok, 0.001, 0.2, 0.1, 0.1) == S.NONE          # 偽薬の平均より下
    assert S.judge(ok, 0.001, 0.0, 0.1, -0.01) == S.NONE        # 後半がマイナス
    assert S.judge({"n": 500, "mean": -0.1, "lo": -0.18, "hi": -0.02}, 0.5, 0.0, -0.1, -0.1) == S.NEG


def test_workflow_and_sync():
    wf = open(".github/workflows/stop-entry-lab.yml", encoding="utf-8").read()
    for s in ("python tests/test_stop_entry_lab.py", "python -u stop_entry_lab.py --check", "python -u stop_entry_lab.py",
              "stop-entry-lab.json stop-entry-lab.md", "group: stop-entry-lab", "workflow_dispatch:", "options: [check, run]"):
        assert s in wf, s
    assert "schedule:" not in wf
    import check_site_consistency as C
    assert {"stop-entry-lab.json", "stop-entry-lab.md"} <= set(C.SYNC_FORBIDDEN)
    import verified_list as V
    assert any(p == "stop-entry-lab.json" and sec == "SE" for p, _, sec in V.SOURCES)


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
