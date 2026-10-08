# -*- coding: utf-8 -*-
"""J42F 「過去12か月で一番上げた10銘柄」の前向きの記録（momentum_forward.py）のテスト。2026-10-08 新設。

値動きはすべて作り物。確かめること＝①事前登録と定数の一致 ②1か月の値は J42 の「上位10銘柄の差」と同じ式 ③一度記録した月は
書き換えない ④買う日の一覧は符号だけ・消えた銘柄を数える ⑤24か月そろったときだけ判定・途中の数字を md に出さない
⑥出力に銘柄コードを出さない ⑦ワークフロー・SYNC 禁忌・検証済みリスト・研究の地図・見張り番。

実行:  python tests/test_momentum_forward.py     （pytest 不要。pytest でも動く）
"""
import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))
os.chdir(ROOT)
import momentum_forward as F  # noqa: E402
import momentum_lab as M  # noqa: E402
import test_momentum_lab as TL  # noqa: E402


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    sec = text[text.index("## J42F "):text.index("## 見込みなしで止める決まり")]
    for s in ("**決める月 2026年10月〜2028年9月の24か月**", "**一度記録した月は書き換えない**", "**95％の幅**", "6か月のかたまり",
              "**5年の日足（始値つき）を取り直して**", "`momentum_lab.diff(kind=10)`", "約1割", "数えた月の数だけ", "毎月3日 10:37 JST"):
        assert s in sec, s
    assert (F.FWD_FIRST, F.FWD_LAST, F.PREV, F.GOAL, F.TOP, F.RANGE, F.ALPHA) == ((2026, 10), (2028, 9), (2026, 9), 24, 10, "5y", 0.05)


def _with_window(first, last, prev):
    F.FWD_FIRST, F.FWD_LAST, F.PREV = first, last, prev


def test_values_pending_and_gone():
    keep = (F.FWD_FIRST, F.FWD_LAST, F.PREV)
    try:
        _with_window((1995, 1), (1996, 12), (1994, 12))
        T = TL._panel(y1=1997)
        codes = sorted(TL.CODES)
        recs, _ = M.records(T, first=F.PREV, last=F.FWD_LAST)
        vals = F.month_values(recs)
        assert sorted(vals)[0] == "1995-01" and sorted(vals)[-1] == "1996-12" and len(vals) == 24
        r = next(x for x in recs if x["ym"] == "1995-03")
        assert abs(vals["1995-03"]["d10"] - M.diff(r, "Q1", kind=10)) < 1e-12
        assert vals["1995-01"]["rep10"] < 1.0                     # 前の月（1994-12）から数える
        pend = F.pending_tops(T, codes)
        assert set(vals) <= set(pend) and all(len(v) == 10 and all(len(t) == 12 for t in v) for v in pend.values())
        assert F.gone_counts(T, codes, pend, ["1995-03"]) == {"1995-03": 0}
        # 1995-03 に買った10銘柄のうち1つの記録が Yahoo から消えた（上場廃止）→ 消えた1
        victim = next(c for c in codes if F.tag(c) == pend["1995-03"][0])
        full, sectors, cal = TL._series()
        series = {c: v for c, v in full.items() if c != victim}
        T2 = M.panel(series, sectors, *M.month_table(cal))
        assert F.gone_counts(T2, sorted(series), pend, ["1995-03"]) == {"1995-03": 1}
    finally:
        _with_window(*keep)


def test_merge_never_rewrites():
    old = {"2026-10": {"d10": -0.01}}
    out, added = F.merge(old, {"2026-10": {"d10": 0.5}, "2026-11": {"d10": 0.02}})
    assert out["2026-10"]["d10"] == -0.01 and added == ["2026-11"] and out["2026-11"]["d10"] == 0.02


def test_judge_only_at_goal_and_md_hides_numbers():
    months = {f"20{26 + (9 + i) // 12}-{(9 + i) % 12 + 1:02d}": {"d10": -0.05, "d20": -0.02, "top10": 0.0, "uni": 0.05}
              for i in range(23)}
    assert F.judge(months) is None
    md = F.render_md({"generated_at": "x", "prereg_sha256": "0" * 64, "months": months, "pending": {}})
    assert "23/24" in md and "-5.00" not in md and "−5" not in md and "## 判定" not in md
    months["2028-09"] = {"d10": -0.05, "d20": -0.02, "top10": 0.0, "uni": 0.05}
    j = F.judge(months)
    assert j["verdict"] == F.OK and abs(j["mean"] + 0.05) < 1e-12
    v = F.verdicts_of(j, "2028-11-04")
    assert v["F1"]["status"] == "confirm" and "前向きでも弱い" in v["F1"]["reason"]
    rng = np.random.default_rng(0)
    noisy = {k: dict(v2, d10=float(rng.normal(0, 0.1))) for k, v2 in months.items()}
    assert F.judge(noisy)["verdict"] == F.NONE and F.verdicts_of(F.judge(noisy), "x")["F1"]["status"] == "stop"
    md = F.render_md({"generated_at": "x", "prereg_sha256": "0" * 64, "months": months, "pending": {}, "judge": j, "gone": {}})
    js = json.dumps(M.rounded({"months": months}), ensure_ascii=False)
    assert "前向きでも弱い" in md and "7X" not in md + js


def test_tags_hide_codes():
    t = F.tag("7203")
    assert len(t) == 12 and "7203" not in t and t == F.tag("7203") and t != F.tag("7204")


def test_registrations():
    wf = open(".github/workflows/momentum-forward.yml", encoding="utf-8").read()
    assert "python -u momentum_forward.py --check" in wf and "'37 1 3 * *'" in wf and "python tests/test_momentum_forward.py" in wf
    assert "momentum-forward.json momentum-forward.md verified-list.md" in wf
    assert '"momentum-forward.json", "momentum-forward.md"' in open("check_site_consistency.py", encoding="utf-8").read()
    assert '"momentum-forward.json"' in open("verified_list.py", encoding="utf-8").read()
    assert "momentum-forward.yml" in open("check_automation_health.py", encoding="utf-8").read()
    assert "MOMENTUM_FWD" in open("research_map.py", encoding="utf-8").read()
    assert "momentum-forward.yml" in open("RESEARCH_LABS.md", encoding="utf-8").read()


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
