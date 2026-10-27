# -*- coding: utf-8 -*-
"""J48F 上場来高値の急騰型の前向き（highs_shape_forward.py）のテスト。2026-10-27 新設。

台帳の行はすべて作り物。確かめること＝①事前登録と定数の一致 ②ケースの決め方（記録上の最高値だけ・10/8 以降・
売買代金1億円・60取引日あけ・組の境目）③判定の前は件数だけ（割合・差を出さない）④件数がそろったら1回だけ判定し、
書いたら変えない ⑤幅が仕込んだ差を見つける・言葉 ⑥保留 ⑦出力に銘柄コードを出さない ⑧ワークフロー・SYNC 禁忌・
研究の地図・見張り番。

実行:  python tests/test_highs_shape_forward.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import highs_shape_forward as F  # noqa: E402


def row(date, code, dev, pct, ex60=None, min60=None, record=1, tv=5.0, ratio=1.0):
    return {"date": date, "code": code, "record": str(record), "turnover": str(tv), "tv_ratio": str(ratio),
            "dev25": str(dev), "pct": str(pct), "ex60": "" if ex60 is None else str(ex60),
            "min60": "" if min60 is None else str(min60), "ex20": "", "ex120": ""}


def days(n, start="2026-10-08"):
    d, out = dt.date.fromisoformat(start), []
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += dt.timedelta(days=1)
    return out


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    sec = text[text.index("## J48F 上場来高値の「急騰型」"):text.index("## 共通の決まり")]
    for s in ("**2026-10-08 以降**", "**1億円以上**", "**60取引日（台帳の日付の数で数える）たつまで新しいケースにしない**",
              "**A 急騰型＝25日線から +20%以上（`dev25` ≧ 0.20）または その日 +10%以上（`pct` ≧ 0.10）**",
              "**B ふつう＝`dev25` ＜ 0.10 かつ `pct` ＜ 0.03**", "**F1** 罠の割合（`ex60` ≦ −10%）の差（**予想プラス**",
              "**F2** いちばん深い下げ（`min60`）の中央値の差（**予想マイナス**", "**A の埋まったケースが100件に届いた最初の週の実行**",
              "2027-12-31", "A が50件以上", "B が50件未満", "**97.5%の幅**", "10,000回", "**判定の前は件数だけを出す**",
              "判定は書いたら変えない"):
        assert s in sec, s
    assert (F.START, F.TV_MIN, F.GAP, F.A_DEV, F.A_PCT, F.B_DEV, F.B_PCT, F.TRAP) == ("2026-10-08", 1.0, 60, 0.20, 0.10, 0.10, 0.03, -0.10)
    assert (F.GOAL, F.LATE, F.LATE_MIN, F.MIN_B, F.N_BOOT) == (100, "2027-12-31", 50, 50, 10000) and abs(F.ALPHA - 0.025) < 1e-12
    assert [(q, s) for q, _, s in F.QUESTIONS] == [("F1", 1), ("F2", -1)]
    assert F.SEED == 20260927 and "SEED = 20260927" in open("pillar_lab.py", encoding="utf-8").read()   # 乱数の種は pillar_lab と同じ


def test_case_rules():
    d = days(70)
    rows = [row(d[0], "1111", 0.25, 0.01),            # A（25日線）
            row(d[0], "2222", 0.05, 0.12),            # A（その日）
            row(d[0], "3333", 0.05, 0.01),            # B
            row(d[0], "4444", 0.15, 0.01),            # 真ん中＝数えない
            row(d[0], "5555", 0.05, 0.01, record=0),  # 年初来＝数えない
            row(d[0], "6666", 0.05, 0.01, tv=0.5),    # 20日平均 0.5億円＝数えない
            row("2026-10-07", "7777", 0.05, 0.01),    # 10/8 より前＝数えない
            row(d[30], "1111", 0.30, 0.01),           # 60取引日たっていない＝数えない
            row(d[60], "1111", 0.30, 0.01),           # 60取引日あと＝新しいケース
            row(d[0], "8888", 0.15, 0.01),            # 真ん中の組の日もケース＝60取引日あけに数える
            row(d[10], "8888", 0.30, 0.01),           # → 10取引日あとの急騰型は数えない
            ] + [row(x, "9999", 0.0, 0.0, record=0) for x in d]   # 台帳の日付（取引日）を埋める
    cs = F.cases(rows)
    got = [(c["date"], c["g"]) for c in cs]
    assert got == [(d[0], "A"), (d[0], "A"), (d[0], "B"), (d[60], "A")], got
    assert F.group_of(0.20, 0.0) == "A" and F.group_of(0.0, 0.10) == "A" and F.group_of(0.0999, 0.0299) == "B"
    assert F.group_of(0.10, 0.0) is None and F.group_of(None, 0.0) is None


def _planted(n_a, n_b, ndays=40, seed=3):
    rng = np.random.default_rng(seed)
    d = days(ndays)
    rows = []
    for i in range(n_a):
        rows.append(row(d[i % ndays], f"A{i:03d}", 0.25, 0.02, ex60=rng.normal(-0.06, 0.15), min60=rng.normal(-0.20, 0.06)))
    for i in range(n_b):
        rows.append(row(d[i % ndays], f"B{i:03d}", 0.05, 0.01, ex60=rng.normal(0.01, 0.08), min60=rng.normal(-0.08, 0.04)))
    return rows


def test_counts_only_before_the_goal():
    res = F.build(_planted(60, 150), today="2026-12-01", n_boot=200)
    assert "decision" not in res and res["verdicts"] == {}
    assert res["counts"]["A_filled"] == 60 and res["counts"]["B_filled"] == 150
    md = F.render_md(res)
    assert "判定はまだ" in md and "罠の割合" not in md.split("## 件数")[1]
    assert "A000" not in md and "B000" not in md


def test_judges_once_when_goal_is_reached_and_freezes():
    res = F.build(_planted(120, 300), today="2027-03-01", n_boot=500)
    d = res["decision"]
    assert d["words"] == {"F1": "確認", "F2": "確認"} and d["status"] == F.OK_WORD, d["words"]
    assert res["verdicts"]["F1"]["status"] == "confirm" and res["verdicts"]["F1"]["n"] == 120
    assert d["bands"]["F1"]["lo"] > 0 and d["bands"]["F2"]["hi"] < 0
    again = F.build(_planted(150, 300, seed=9), prev=res, today="2027-04-01", n_boot=200)
    assert again["decision"] == d and again["verdicts"] == res["verdicts"]
    md = F.render_md(res)
    assert "読むための表" in md and "A000" not in md


def test_no_difference_is_not_confirmed():
    rng = np.random.default_rng(5)
    d = days(40)
    rows = [row(d[i % 40], f"A{i:03d}", 0.25, 0.02, ex60=rng.normal(0, 0.1), min60=rng.normal(-0.1, 0.05)) for i in range(120)]
    rows += [row(d[i % 40], f"B{i:03d}", 0.05, 0.01, ex60=rng.normal(0, 0.1), min60=rng.normal(-0.1, 0.05)) for i in range(300)]
    res = F.build(rows, today="2027-03-01", n_boot=500)
    assert res["decision"]["status"] == "✕" and res["verdicts"]["F2"]["status"] == "stop"
    assert F.word({"lo": -0.2, "hi": -0.1}, +1) == "逆" and F.word({"lo": None, "hi": None}, +1) == "保留"


def test_hold_when_b_is_short_or_late_and_small():
    res = F.build(_planted(110, 30), today="2027-03-01", n_boot=100)
    assert res["decision"]["status"] == "保留" and res["verdicts"] == {}
    late = F.build(_planted(40, 200), today="2028-01-07", n_boot=100)
    assert late["decision"]["status"] == "保留"
    late_ok = F.build(_planted(60, 200), today="2028-01-07", n_boot=200)
    assert late_ok["decision"]["status"] in (F.OK_WORD, "✕")


def test_registered_in_workflow_sync_map_and_health():
    wf = open(".github/workflows/highs-shape-forward.yml", encoding="utf-8").read()
    for s in ("workflow_dispatch", "cron: '23 23 * * 5'", "python tests/test_highs_shape_forward.py", "python highs_shape_forward.py",
              "git add highs-shape-forward.json highs-shape-forward.md"):
        assert s in wf, s
    assert '"highs-shape-forward.json", "highs-shape-forward.md"' in open("check_site_consistency.py", encoding="utf-8").read()
    assert "HIGHS_SHAPE_FWD" in open("research_map.py", encoding="utf-8").read()
    assert '"highs-shape-forward.yml"' in open("check_automation_health.py", encoding="utf-8").read()
    assert "highs-shape-forward.yml" in open("RESEARCH_LABS.md", encoding="utf-8").read()


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
            except Exception as e:  # noqa: BLE001
                fails += 1
                print(f"💥 {name}: {type(e).__name__}: {e}")
    sys.exit(1 if fails else 0)
