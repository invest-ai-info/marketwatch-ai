# -*- coding: utf-8 -*-
"""M7 腕A：4時間足で E1 と同じ総当たり（exit_ind_lab_4h.py）のテスト。2026-10-01 新設。

値動きはすべて作り物（ネットワークに出ない）。確かめること＝①事前登録と定数の一致 ②1時間足→4時間足の束ね方（UTC・0/4/8…時・始値高値安値終値）
③区切りと幅のまとまり（銘柄×月）が E1 を汚さない（呼んだあと元に戻る） ④E1 のエンジンに4時間足を渡して最後まで動く（判定・読むための表・出力に足の情報）
⑤E1 の既定の動き（loader なし・題名）が変わっていない ⑥ワークフローと SYNC禁忌。

実行:  python tests/test_exit_ind_lab_4h.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import combo_lab as CL  # noqa: E402
import exit_ind_lab as E  # noqa: E402
import exit_ind_lab_4h as H  # noqa: E402
import trend_lab as TL  # noqa: E402


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    i = text.find("\n## M7 ")
    sec = text[i:text.find("\n## ", i + 1)]
    for s in ("**選ぶ＝2025-09-30 まで／確かめ＝2025-10-01 から**", "（銘柄×月）", "`exit_ind_lab_4h.py`", "`exit-ind-lab-4h.yml`",
              "入口60×出口64", "**時間帯の縛りなし**", "日足はすでに同じ形で数えてある", "`research/mt5/m7_h4.py`", "**最長42本",
              "**3本（12時間", "**2,048**"):
        assert s in sec, s
    assert H.SPLIT_4H == "2025-10-01" and H.SECTION == "## M7 " and len(E.EXITS) == 64
    assert (E.MIN_N, E.TOP_K, round(E.P_LIMIT, 6)) == (150, 3, round(0.05 / 3, 6))


def _hourly(n_days, seed=1, p0=150.0, start=dt.datetime(2024, 10, 2, tzinfo=dt.timezone.utc)):
    rng = np.random.default_rng(seed)
    idx = pd.date_range(start, periods=n_days * 24, freq="h", tz="UTC")
    c = p0 * np.exp(np.cumsum(rng.standard_normal(len(idx)) * 0.0015))
    df = pd.DataFrame({"Close": c}, index=idx)
    df["Open"] = df["Close"].shift(1).fillna(p0)
    df["High"] = df[["Open", "Close"]].max(axis=1) * (1 + 0.0004)
    df["Low"] = df[["Open", "Close"]].min(axis=1) * (1 - 0.0004)
    df["Volume"] = 100.0
    return df


def test_to_4h_bundles_on_utc_boundaries():
    df = _hourly(3)
    h4 = H.to_4h(df)
    assert len(h4) == 18 and all(t.hour % 4 == 0 for t in h4.index)
    first = df.iloc[0:4]
    assert h4.iloc[0]["Open"] == first["Open"].iloc[0] and h4.iloc[0]["Close"] == first["Close"].iloc[-1]
    assert h4.iloc[0]["High"] == first["High"].max() and h4.iloc[0]["Low"] == first["Low"].min()
    assert h4.iloc[0]["Volume"] == 400.0
    assert H.to_4h(None) is None and H.to_4h(df.iloc[0:0]) is None
    gap = df.drop(df.index[4:8])                                   # 4時間ぶん足が無い → その4時間足は作らない
    assert len(H.to_4h(gap)) == 17


BARS = {tk: H.to_4h(_hourly(730, seed=k + 1)) for k, tk in enumerate(list(TL.TICKERS)[:2])}   # 2銘柄・約2年の作り物


def test_split_and_cluster_are_restored_after_run():
    keep_split, keep_cs = E.SPLIT, CL.confirm_stats
    seen = {}

    def fake_loader(tk):
        seen["split"], seen["cs"] = E.SPLIT, CL.confirm_stats     # 計算の間だけ差し替わっている
        return BARS.get(tk)
    res = H.run(n_perm=5, loader=fake_loader)
    assert seen["split"] == "2025-10-01" and seen["cs"] is H.confirm_stats_month
    assert E.SPLIT == keep_split and CL.confirm_stats is keep_cs    # 呼んだあとは E1 のまま
    assert res["entries"] > 0 and len(res["missing"]) == len(TL.TICKERS) - 2
    st = H.confirm_stats_month([{"ticker": "A", "date": "2025-11-03"}, {"ticker": "A", "date": "2025-11-04"},
                                {"ticker": "B", "date": "2025-12-01"}, {"ticker": "B", "date": "2026-01-05"}], [1.0, 2.0, 3.0, 4.0])
    assert st["n"] == 4 and abs(st["mean"] - 2.5) < 1e-12


def test_engine_runs_end_to_end_on_4h_bars():
    res = H.run(n_perm=20, loader=lambda tk: BARS.get(tk))
    assert res["combos"] == 3840 and res["entries"] > 0 and len(res["missing"]) == len(TL.TICKERS) - 2
    assert len(res["picked"]) <= E.TOP_K and set(res["grid"]) == {f"{s}{p}" for s, p in E.EXITS}
    for x in res["picked"]:
        assert x["confirm"]["verdict"] in ("確かめでも残った（有望）", "確かめで消えた", "件数不足")
    out = {"generated_at": "x", "prereg_file": "PILLAR_PREREG.md", "prereg_sha256": "a" * 64, "result": res}
    md = E.render_md(out, title=H.TITLE, section="M7", front="2025-10-01 より前", back="2025-10-01 から")
    assert "M7" in md and "2025-10-01 から" in md and "投資助言ではありません" in md
    default = E.render_md(out)
    assert default.startswith("# 出口にテクニカル指標を使う研究 E1") and "2015年まで" in default


def test_workflow_and_sync():
    wf = open(".github/workflows/exit-ind-lab-4h.yml", encoding="utf-8").read()
    for s in ("python tests/test_exit_ind_lab_4h.py", "python exit_ind_lab_4h.py", "exit-ind-lab-4h.json exit-ind-lab-4h.md",
              "group: exit-ind-lab-4h", "workflow_dispatch:"):
        assert s in wf, s
    assert "schedule:" not in wf
    e1 = open(".github/workflows/exit-ind-lab.yml", encoding="utf-8").read()
    assert "python exit_ind_lab.py" in e1 and "4h" not in e1                     # E1 のワークフローは触っていない
    import check_site_consistency as C
    assert {"exit-ind-lab-4h.json", "exit-ind-lab-4h.md"} <= set(C.SYNC_FORBIDDEN)


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
