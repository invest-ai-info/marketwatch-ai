# -*- coding: utf-8 -*-
"""R8 日経平均の夜の上げを昔の時代で確かめる（night_history_lab.py）のテスト。2026-10-08 新設。

値動きはすべて作り物。確かめること＝①事前登録と定数の一致 ②年ごとの点検と数える最初の年 ③配当落ちの夜（3月・9月の最後の5取引日に
売る夜）を除く ④指数の始値の確かめ（相関・ばらつきの比）⑤判定（夜に上がる作り物＝◎・上がらない作り物＝差なし）
⑥点検は損益を出さない・出力の形 ⑦ワークフローと SYNC 禁忌。

実行:  python tests/test_night_history_lab.py     （pytest 不要。pytest でも動く）
"""
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import index_open_lab as I  # noqa: E402
import night_history_lab as N  # noqa: E402


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "## R8 日経平均の夜の上げは、R7 が使っていない昔の時代（1992〜2010年）でも出ていたか" in text
    assert (N.START, N.END) == ("1992-01-01", "2010-12-31") and "1992-01-01〜2010-12-31" in text
    assert N.COST == 0.0003 and I.FIN_RATE == 0.03 and "往復 0.03％＋持ち越しの金利 年3％" in text
    assert (N.MIN_ROWS, N.MAX_SAME_OPEN, N.MAX_OPEN_EQ_CLOSE, N.MAX_DAILY, N.MIN_YEARS) == (200, 0.30, 0.05, 0.25, 5)
    assert "①行が200未満 ②始値が前の日の終値とちょうど同じ日が30％超" in text and "③始値と終値がちょうど同じ日が5％超" in text
    assert "④終値の変化が25％を超える日がある" in text and "使える年が5年に満たなければ数えない" in text
    assert N.DIV_LAST == 5 and "3月と9月の最後の5取引日" in text
    assert (N.MIN_CORR, N.SD_RATIO, N.MIN_OVERLAP) == (0.90, (0.8, 1.25), 1000) and "**相関が0.90以上**" in text and "0.8〜1.25" in text
    assert (N.OV_START, N.OV_END) == ("2011-01-01", "2026-09-30") and "2011-01-01〜2026-09-30" in text and "1,000に満たなければ" in text
    assert N.ALPHA == 0.05 and "**判定（1つ・p＜0.05）**" in text and N.N_BOOT == 10000


def _series(start, end, night_mu=0.0, night_sd=0.008, day_mu=0.0, day_sd=0.01, seed=1, stale_open=None):
    """作り物の日足。stale_open=k なら指数の始値が夜の値動きの k 倍しか動かない"""
    rng = np.random.default_rng(seed)
    days = pd.bdate_range(start, end)
    o, c = np.empty(len(days)), np.empty(len(days))
    prev = 20000.0
    for i in range(len(days)):
        night = rng.normal(night_mu, night_sd)
        o[i] = prev * (1 + night * (stale_open if stale_open is not None else 1.0))
        c[i] = prev * (1 + night) * (1 + rng.normal(day_mu, day_sd))
        prev = c[i]
    return pd.DataFrame({"Open": o, "High": np.maximum(o, c) * 1.002, "Low": np.minimum(o, c) * 0.998, "Close": c}, index=days)


def test_year_shape_and_first_year():
    df = _series("1990-01-01", "2010-12-31")
    shape = N.year_shape(df)
    assert all(v["ok"] for v in shape.values()) and N.usable_from(shape) == 1992
    bad = df.copy()
    m = bad.index.year == 1995
    bad.loc[m, "Open"] = bad["Close"].shift(1)[m]                    # 1995年は始値が埋まっていない
    s2 = N.year_shape(bad)
    assert not s2[1995]["ok"] and "始値＝前の日の終値" in s2[1995]["why"] and N.usable_from(s2) == 1996
    gone = df[df.index.year != 2007]                                 # 2007年が無い → 2008〜2010年＝3年だけ
    assert N.usable_from(N.year_shape(gone)) is None
    oc = df.copy()
    m = oc.index.year == 2001
    oc.loc[m, "Open"] = oc.loc[m, "Close"]
    assert not N.year_shape(oc)[2001]["ok"] and N.usable_from(N.year_shape(oc)) == 2002


def test_dividend_nights_are_dropped():
    df = _series("2004-01-01", "2006-12-31")
    divs = N.div_days(df.index)
    mar = [d for d in df.index if d.year == 2005 and d.month == 3]
    assert {str(d.date()) for d in mar[-5:]} <= divs and str(mar[-6].date()) not in divs and len(divs) == 3 * 2 * 5
    rows, dropped = N.nights(df, "2004-01-01", "2006-12-31", "2007-01-05")
    assert dropped == 30 and not any(r["sell"] in divs for r in rows)
    full = I.night_trades(df, N.COST, start="2004-01-01", end="2006-12-31", cut="2007-01-05")
    assert len(rows) + dropped == len(full)


def test_overlap_gate():
    idx = _series("2010-06-01", "2026-10-02", seed=3)
    assert N.overlap(idx, idx * 0.001)["ok"]                         # 同じ値動き（単位だけ違う）＝通る
    stale = _series("2010-06-01", "2026-10-02", seed=3, stale_open=0.5)
    ov = N.overlap(stale, idx)
    assert not ov["ok"] and ov["sd_ratio"] < 0.8 and "ばらつきの比" in ov["why"]
    other = _series("2010-06-01", "2026-10-02", seed=4)
    assert not N.overlap(other, idx)["ok"]                           # 別の値動き＝相関が低い
    assert not N.overlap(idx[idx.index.year < 2013], idx)["ok"]      # 同じ夜が足りない


def _data(night_mu, seed):
    s = _series("1990-01-01", "2026-10-02", night_mu=night_mu, seed=seed)
    return {N.INDEX: s, N.ETF: s[s.index >= "2007-01-01"] * 0.01}


def test_judgment():
    res = N.analyze(_data(0.0015, 5), np.random.default_rng(1))
    s = res["stats"]
    assert res["from_year"] == 1992 and s["verdict"] == N.VERDICTS[0] and s["lo"] > 0 and s["p"] < 0.05, s
    assert res["dropped_div"] > 0 and res["first_day"].startswith("1992") and res["last_day"].startswith("2010")
    assert set(res["reading"]["by_period"]) == {p[0] for p in N.PERIODS} and res["r7_period_index"]["n"] > 3000
    flat = N.analyze(_data(0.0, 6), np.random.default_rng(2))
    assert flat["stats"]["verdict"] == N.VERDICTS[1]
    d = _data(0.0015, 7)
    d[N.INDEX] = d[N.INDEX][d[N.INDEX].index.year != 2008]           # 2008年が無い → 2009〜2010年だけ＝数えない
    bad = N.analyze(d, np.random.default_rng(3))
    assert "error" in bad and "stats" not in bad and bad["bad_years"][2008] == "行が0"


def test_check_has_no_returns_and_render():
    d = _data(0.0015, 8)
    out = N.check_summary(d)
    assert out["from_year"] == 1992 and out["overlap"]["ok"] and not out["stop"]
    assert not any(w in repr(out) for w in ("mean", "gross", "net", "_means"))
    res = N.analyze(d, np.random.default_rng(4))
    md = N.render_md({"generated_jst": "x", "prereg_sha256": "0" * 64, "result": res})
    assert "## データの点検" in md and "## Q1" in md and "投資助言ではありません" in md and "R7 の期間" in md
    err = N.render_md({"generated_jst": "x", "result": {"from_year": None, "overlap": {"n": 5, "ok": False}, "bad_years": {}, "error": "e"}})
    assert "計算できず" in err
    assert "取得の失敗" in N.render_md({"generated_jst": "x", "failed": ["^N225: 取れない"]})


def test_workflow_and_sync_forbidden():
    wf = open(".github/workflows/night-history-lab.yml", encoding="utf-8").read()
    assert "python -u night_history_lab.py --check" in wf and "python tests/test_night_history_lab.py" in wf
    assert "night-history-lab.json night-history-lab.md" in wf and "options: [check, run]" in wf
    assert '"night-history-lab.json", "night-history-lab.md"' in open("check_site_consistency.py", encoding="utf-8").read()
    assert '"night-history-lab.json"' in open("verified_list.py", encoding="utf-8").read()


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
