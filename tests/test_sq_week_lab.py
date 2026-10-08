# -*- coding: utf-8 -*-
"""R9 SQ週（sq_week_lab.py）のテスト。2026-10-08 新設。

値動きはすべて作り物。確かめること＝①事前登録と定数の一致 ②第n金曜日と満期の週（休みの金曜も同じ週）③週の損益率（前の週の
最後の取引日の終値から）④判定の言葉（同じ向き・最近だけ・昔だけ・差なし）⑤点検は損益を出さない・検証済みリストが読む欄
⑥ワークフローと SYNC 禁忌・検証済みリストの登録。

実行:  python tests/test_sq_week_lab.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import sq_week_lab as S  # noqa: E402


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "## R9 SQ週（オプションの満期の週）は特別か" in text and "**まだ誰も数えていない**" in text
    assert [(q[2], q[3]) for q in S.QUESTIONS] == [("^N225", 2), ("^GSPC", 3)] and "**第2金曜日**" in text and "**第3金曜日**" in text
    assert [e[2] for e in S.ERAS] == [("1992-01-01", "2010-12-31"), ("2011-01-01", "2026-09-30")]
    assert abs(S.ALPHA - 0.025) < 1e-12 and S.N_BOOT == 10000 and S.COST == 0.0008 and "**0.08％**" in text


def test_fridays_and_weeks():
    assert S.nth_friday(2026, 10, 2) == dt.date(2026, 10, 9) and S.nth_friday(2026, 10, 3) == dt.date(2026, 10, 16)
    assert S.nth_friday(2026, 5, 2) == dt.date(2026, 5, 8) and S.nth_friday(2026, 1, 2) == dt.date(2026, 1, 9)
    exp = S.expiry_mondays(2026, 2026, 2)
    assert exp[dt.date(2026, 10, 5)] == 10 and len(exp) == 12
    closes = [(dt.date(2026, 10, 1), 100.0), (dt.date(2026, 10, 2), 101.0),          # 前の週（金曜 101）
              (dt.date(2026, 10, 5), 99.0), (dt.date(2026, 10, 8), 103.02),           # SQ週（金曜が休み＝木曜が最後）
              (dt.date(2026, 10, 13), 102.0), (dt.date(2026, 10, 16), 100.0)]
    w = S.weekly(closes)
    assert [x[0] for x in w] == [dt.date(2026, 10, 5), dt.date(2026, 10, 12)] and abs(w[0][2] - 0.02) < 1e-12
    is_exp, major, after = S.label(w, 2)
    assert is_exp == [True, False] and major == [False, False] and after == [False, True]


def test_verdict_words():
    up, down, flat = {"lo": 0.001, "hi": 0.01}, {"lo": -0.01, "hi": -0.001}, {"lo": -0.01, "hi": 0.01}
    assert S.verdict({"e1": up, "e2": up}) == S.OK + "（上向き）" and S.verdict({"e1": down, "e2": down}) == S.OK + "（下向き）"
    assert S.verdict({"e1": flat, "e2": up}) == S.NEW_ONLY + "（上向き）" and S.verdict({"e1": up, "e2": flat}) == S.OLD_ONLY + "（上向き）"
    assert S.verdict({"e1": flat, "e2": flat}) == S.NONE and S.verdict({"e1": {"lo": None}, "e2": flat}) == S.NONE
    q = S.diff_band(np.r_[np.full(50, 0.01), np.full(50, 0.012)], np.zeros(200))
    assert q["lo"] > 0 and abs(q["value"] - 0.011) < 1e-12 and S.diff_band([0.1] * 3, [0.0] * 10)["lo"] is None


def _frame(ticker, n_fri, bump, seed=1):
    """1991-06〜2026-09 の平日。満期の週の金曜に bump だけ上げる（それ以外は小さなでたらめ）"""
    rng = np.random.default_rng(seed)
    days = pd.bdate_range("1991-06-03", "2026-09-30")
    exp = S.expiry_mondays(1991, 2026, n_fri)
    r = rng.normal(0, 0.003, len(days))
    for i, d in enumerate(days):
        if d.weekday() == 4 and S.monday(d.date()) in exp:
            r[i] += bump
    close = 100 * np.cumprod(1 + r)
    return pd.DataFrame({"Open": close, "High": close, "Low": close, "Close": close}, index=days)


def test_analyze_and_verified_list_fields():
    data = {"^N225": _frame("^N225", 2, 0.01), "^GSPC": _frame("^GSPC", 3, 0.0, seed=2)}
    res = S.analyze(data)
    q1, q2 = res["questions"]["Q1"], res["questions"]["Q2"]
    assert q1["summary"] == S.OK + "（上向き）" and q1["eras"]["e2"]["lo"] > 0 and q1["read"]["e1"]["exp_weeks"] in range(220, 232)
    assert q2["summary"] in (S.NONE, S.NEW_ONLY + "（上向き）", S.NEW_ONLY + "（下向き）", S.OLD_ONLY + "（上向き）", S.OLD_ONLY + "（下向き）")
    assert abs(q1["read"]["e2"]["long_net"] - (q1["read"]["e2"]["exp_mean"] - S.COST)) < 1e-12
    v = S.verdicts_of({"questions": {"Q1": q1, "Q2": dict(q2, summary=S.NONE)}}, "2026-10-08")
    assert set(v) == {"Q2"} and v["Q2"]["status"] == "stop" and v["Q2"]["n"] == q2["read"]["e2"]["exp_weeks"]
    md = S.render_md({"generated_at": "x", "prereg_sha256": "0" * 64, "result": res})
    assert "## まとめ" in md and "投資助言ではありません" in md and "メジャーSQ" in md
    assert "計算できず" in S.render_md({"generated_at": "x", "result": {"error": "e"}})
    out = S.check_summary(data)
    assert out["Q1"]["eras"]["e2"]["exp_weeks"] > 180 and not any(w in repr(out) for w in ("mean", "value", "'lo'"))


def test_workflow_sync_and_verified_list():
    wf = open(".github/workflows/sq-week-lab.yml", encoding="utf-8").read()
    assert "python -u sq_week_lab.py --check" in wf and "options: [check, run]" in wf and "python tests/test_sq_week_lab.py" in wf
    assert "sq-week-lab.json sq-week-lab.md verified-list.md" in wf and "python verified_list.py" in wf
    assert '"sq-week-lab.json", "sq-week-lab.md"' in open("check_site_consistency.py", encoding="utf-8").read()
    assert '"sq-week-lab.json"' in open("verified_list.py", encoding="utf-8").read()


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
