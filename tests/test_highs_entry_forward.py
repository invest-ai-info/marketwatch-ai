# -*- coding: utf-8 -*-
"""J49F 上場来高値の罠の目印の前向き（highs_entry_forward.py）のテスト。2026-10-28 新設。

台帳の行と値段はすべて作り物。確かめること＝①事前登録と定数の一致 ②ケースの決め方（J48F と同じ・形の組で分けない）
③急騰の点数 ④T1F・T3F の窓（次の日の寄り／下げた日の次の日の寄り／6本目の寄り → 60本目の引け − 1306）
⑤判定の前は件数だけ ⑥件数がそろったら問いごとに1回だけ判定し、書いたら変えない ⑦保留
⑧出力に銘柄コードを出さない ⑨ワークフロー・SYNC 禁忌・研究の地図・見張り番。

実行:  python tests/test_highs_entry_forward.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import highs_entry_forward as E  # noqa: E402


def row(date, code, dev=0.05, pct=0.01, ratio=1.0, streak=0, record=1, tv=5.0):
    return {"date": date, "code": code, "record": str(record), "turnover": str(tv), "tv_ratio": str(ratio),
            "dev25": str(dev), "pct": str(pct), "streak": str(streak)}


def days(n, start="2026-10-08"):
    d, out = dt.date.fromisoformat(start), []
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += dt.timedelta(days=1)
    return out


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    sec = text[text.index("## J49F 上場来高値の罠の目印"):text.index("## 共通の決まり")]
    for s in ("**2026-10-08 以降**", "1億円以上", "60取引日（台帳の日付の数）あける", "**3つ以上** − 2つ以下",
              "(a) 25日線から +20%以上（`dev25`）", "(b) その日 +10%以上（`pct`）", "(c) 売買代金がその前20営業日の平均の3倍以上（`tv_ratio`）",
              "(d) その日まで4日以上続けて終値が上げた（`streak`）", "次の日の寄りで買い、60本目の引けで売った損益 − 1306 の同じ区間",
              "その最初の日の次の日の寄りから60本", "6本目の寄りから60本", "**罠**＝その損益 − 1306 が −10%以下",
              "**100件に届いた最初の週**", "2027-12-31", "50件以上", "50件未満なら「保留」", "**97.5%の幅**", "10,000回",
              "50%以上なら「高い確率（50%以上）」", "件数だけを出す", "判定は書いたら変えない"):
        assert s in sec, s
    assert (E.START, E.TV_MIN, E.GAP, E.HOLD, E.TRAP) == ("2026-10-08", 1.0, 60, 60, -0.10)
    assert (E.M25_HOT, E.RET_HOT, E.TVX_HOT, E.STREAK_HOT, E.HOT_MIN, E.T3_DAYS, E.T3_DROP) == (0.20, 0.10, 3.0, 4, 3, 5, 0.10)
    assert (E.GOAL, E.LATE, E.LATE_MIN, E.MIN_B, E.N_BOOT, E.HIGH_PROB) == (100, "2027-12-31", 50, 50, 10000, 0.50)
    assert abs(E.ALPHA - 0.025) < 1e-12 and E.TOPIX == "1306" and [q for q, *_ in E.QUESTIONS] == ["T1F", "T3F"]


def test_case_rules_and_hot_score():
    d = days(70)
    rows = [row(d[0], "1111", dev=0.25, pct=0.12, ratio=3.5),            # 3つ
            row(d[0], "2222", dev=0.25, pct=0.12, ratio=3.5, streak=4),  # 4つ
            row(d[0], "3333"),                                         # 0
            row(d[0], "4444", record=0),                               # 年初来＝数えない
            row(d[0], "5555", tv=0.5),                                 # 0.5億円＝数えない
            row(d[10], "1111"),                                        # 60取引日たっていない＝数えない
            row(d[61], "1111"),                                        # 61取引日目＝ケース
            row("2026-10-07", "6666")]                                 # 10/8 より前＝数えない
    rows += [row(x, "9999", record=0) for x in d]                       # 台帳の日付をそろえる
    got = sorted((c["date"], c["code"], c["hot"]) for c in E.cases(rows))
    assert got == sorted([(d[0], "1111", 3), (d[0], "2222", 4), (d[0], "3333", 0), (d[61], "1111", 0)])
    assert E.hot_score(None, 0.12, 3.0, 4) == 3 and E.hot_score(0.19, 0.099, 2.9, 3) == 0


def test_windows_t1_and_t3():
    dates = days(90, "2026-10-01")
    idx = {x: (100.0, 100.0) for x in dates}                     # 全体は動かない
    # 記録の日の終値 100 → 次の日（寄り 99・引け 95）→ 2本目の引け 88（−12％）＝T3 の目印 → そのあと寄り 88・引け 85
    px = [(dates[0], 100.0, 100.0), (dates[1], 99.0, 95.0), (dates[2], 95.0, 88.0)] + [(x, 88.0, 85.0) for x in dates[3:]]
    o = E.outcomes({"date": dates[0]}, px, idx)
    assert o["t1"] is True                                       # 寄り 99 → 60本目の引け 85＝−14.1％＝罠
    assert o["t3_flag"] is True and o["t3"] is False             # 3本目の寄り 88 → 85＝−3.4％
    assert abs(E.window(px, 1, idx) - (85 / 99 - 1)) < 1e-12
    # 目印なし：5本とも −10％ より上 → 6本目の寄りから
    px2 = [(dates[0], 100.0, 100.0)] + [(x, 95.0, 95.0) for x in dates[1:6]] + [(x, 80.0, 84.0) for x in dates[6:]]
    o2 = E.outcomes({"date": dates[0]}, px2, idx)
    assert o2["t3_flag"] is False and o2["t3"] is False          # 6本目の寄り 80 → 84
    # 全体を引く：1306 が同じ区間で +5％
    idx2 = dict(idx)
    idx2[dates[1]] = (100.0, 100.0)
    idx2[dates[60]] = (100.0, 105.0)
    assert abs(E.window(px, 1, idx2) - (85 / 99 - 1 - 0.05)) < 1e-12
    # 足りない
    assert E.outcomes({"date": dates[50]}, px, idx)["t1"] is None
    assert E.outcomes({"date": "2025-01-01"}, px, idx) == {"t1": None, "t3_flag": None, "t3": None}


def _world(n_flag, n_plain, trap_flag=True):
    """急騰の点数3のケース n_flag 件（罠）と0点のケース n_plain 件（罠でない）。どれも記録の日は台帳の最初の日"""
    d = days(100)
    rows = [row(d[0], f"F{i:03d}", dev=0.3, pct=0.15, ratio=4.0) for i in range(n_flag)] + \
           [row(d[0], f"P{i:03d}") for i in range(n_plain)] + [row(x, "Z999", record=0) for x in d]
    bad = [(d[0], 100.0, 100.0)] + [(x, 100.0, 80.0 if trap_flag else 100.0) for x in d[1:]]
    good = [(d[0], 100.0, 100.0)] + [(x, 100.0, 100.0) for x in d[1:]]
    top = [(x, 100.0, 100.0) for x in d]

    def fetch(code):
        return top if code == E.TOPIX else bad if code.startswith("F") else good
    return rows, fetch


def test_counts_only_before_the_goal_and_no_codes():
    rows, fetch = _world(40, 200)
    res = E.build(rows, fetch, today="2026-12-01", n_boot=200)
    assert res["decisions"] == {} and res["counts"]["T1F"]["A_filled"] == 40 and res["progress"]["T1F"] == 40
    txt = json.dumps(res, ensure_ascii=False) + E.render_md(res)
    assert "F000" not in txt and "P000" not in txt and "判定はまだ" in txt
    for k in ('"a":', '"diff"', "trap"):
        assert k not in json.dumps(res["counts"]), k


def test_judges_once_and_keeps_the_decision():
    rows, fetch = _world(120, 200)
    res = E.build(rows, fetch, today="2027-03-01", n_boot=500)
    d = res["decisions"]["T1F"]
    assert d["word"] == "確認" and d["status"] == E.OK_WORD and d["high_prob"] is True
    assert res["verdicts"]["T1F"]["status"] == "confirm"
    assert res["decisions"]["T3F"]["word"] == "確認"            # 目印の株は次の日に −20％（5本以内の下げ）→ そのあとも罠
    rows2, fetch2 = _world(120, 200, trap_flag=False)           # 値段が変わっても、前の判定は書き換えない
    res2 = E.build(rows2, fetch2, prev=res, today="2027-03-08", n_boot=500)
    assert res2["decisions"]["T1F"] == d                          # 書いたら変えない
    # 期限を過ぎて件数が足りなければ保留
    rows3, fetch3 = _world(10, 200)
    res3 = E.build(rows3, fetch3, today="2028-01-05", n_boot=100)
    assert res3["decisions"]["T1F"]["status"] == "保留"


def test_workflow_sync_and_lists_are_registered():
    wf = open(".github/workflows/highs-entry-forward.yml", encoding="utf-8").read()
    for s in ("workflow_dispatch", "cron:", "python tests/test_highs_entry_forward.py", "python highs_entry_forward.py",
              "git add highs-entry-forward.json highs-entry-forward.md"):
        assert s in wf, s
    import check_site_consistency as C
    assert {"highs-entry-forward.json", "highs-entry-forward.md"} <= set(C.SYNC_FORBIDDEN)
    assert '"highs-entry-forward.yml"' in open("check_automation_health.py", encoding="utf-8").read()
    assert "highs-entry-forward.yml" in open("RESEARCH_LABS.md", encoding="utf-8").read()
    assert "HIGHS_ENTRY_FWD" in open("research_map.py", encoding="utf-8").read()


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
