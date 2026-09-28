# -*- coding: utf-8 -*-
"""J4F 寄り付きの前向き（yori_forward.py）と検証済みリスト（verified_list.py）のテスト。2026-09-28 新設。

値動きはすべて作り物（ネットワークに出ない）。確かめること＝①事前登録と定数の一致 ②4つの当てはまり方と費用後の損益
③登録日より前・今日の分は数えない／数えた日は数え直さない／5分足の取れ方が足りない日は数えない
④1000回に届いた日に1回だけ判定・ストップはその日より後を外して数えるのをやめる・プラスは数え続ける
⑤出力と検証済みリストに銘柄コードを出さない ⑥ワークフローと SYNC禁忌。

実行:  python tests/test_yori_forward.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import verified_list as V  # noqa: E402
import yori_forward as F  # noqa: E402
import yori_lab as Y  # noqa: E402


def _rec(date, code, hot=True, cls="flat", gap=0.0, prev_ret=0.0, r15=0.0, r_close=0.0):
    op = 100.0
    p915 = op * (1 + r15)
    path = {t: p915 for t in Y.TIMES}
    path["15:30"] = p915 * (1 + r_close)
    return {"code": code, "date": date, "hot": hot, "cls": cls, "gap": gap, "prev_ret": prev_ret, "open": op,
            "p915": p915, "path": path, "r15": r15, "wick": None, "vol_share": None}


def _days(n, start="2026-09-29"):
    d0 = dt.date.fromisoformat(start)
    return [(d0 + dt.timedelta(days=i)).isoformat() for i in range(n)]


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "## J4F 寄り付きの前向き" in text
    assert F.FWD_START == "2026-09-29" and "2026-09-29 以降の取引だけ" in text
    assert F.GOAL == 1000 and "**1000回**に届いた日までの取引" in text
    assert F.MIN_COVER == 0.95 and "95％未満" in text and F.MAX_MISSING == 0.02 and "2％を超えた" in text
    assert F.PREV_BIG == 0.05 and Y.GAP_BIG == 0.03 and Y.UP == 0.02 and Y.COST == 0.001
    for cid, c in F.CANDS.items():
        assert f"**{cid}**" in text
    assert "`verified-list.md`（検証済みリスト）に載せる" in text


def test_qualifies_and_returns():
    r = _rec("2026-09-29", "A", cls="up", gap=0.04, prev_ret=0.06, r15=0.03, r_close=-0.01)
    assert all(F.qualifies(c, r) for c in F.CANDS)
    assert abs(F.trade_return("F1", r) - (0.03 - Y.COST)) < 1e-12            # 寄り→9:15
    assert abs(F.trade_return("F3", r) - (-0.01 - Y.COST)) < 1e-12           # 9:15→大引け
    assert not F.qualifies("F2", dict(r, gap=0.029)) and not F.qualifies("F4", dict(r, prev_ret=0.049))
    assert not F.qualifies("F3", dict(r, cls="flat")) and not any(F.qualifies(c, dict(r, hot=False)) for c in F.CANDS)
    assert not F.qualifies("F4", dict(r, prev_ret=None))


def test_update_counts_each_day_once_and_skips_before_start_and_today():
    st = F.empty_state()
    recs = [_rec("2026-09-28", "A"), _rec("2026-09-29", "A"), _rec("2026-09-29", "B", hot=False),
            _rec("2026-09-30", "A"), _rec("2026-10-01", "A")]
    cover = {"2026-09-28": 1.0, "2026-09-29": 1.0, "2026-09-30": 0.9, "2026-10-01": 1.0}
    added = F.update(st, recs, cover, today="2026-10-01")
    assert added == 1 and sorted(st["days"]) == ["2026-09-29"]              # 9/28＝登録前・9/30＝取れ方不足・10/1＝今日
    assert [t["d"] for t in st["trades"]] == ["2026-09-29"] and st["trades"][0]["c"] == "F1"
    cover["2026-09-30"] = 0.99
    changed = [dict(r, r15=0.05) for r in recs]                              # 後から値が変わっても、数えた日は数え直さない
    assert F.update(st, changed, cover, today="2026-10-02") == 2
    assert sum(1 for t in st["trades"] if t["d"] == "2026-09-29") == 1
    assert [t for t in st["trades"] if t["d"] == "2026-09-29"][0]["r"] == round(-Y.COST, 6)


def _fill(st, days, per_day, r15):
    recs = []
    for i, d in enumerate(days):
        for j in range(per_day):
            recs.append(_rec(d, f"S{(i * per_day + j) % 97:03d}", r15=r15 + 0.004 * ((j % 5) - 2)))
    F.update(st, recs, {d: 1.0 for d in days}, today="2099-01-01")


def test_judge_once_at_goal_and_stop_trims_and_freezes():
    st = F.empty_state()
    days = _days(60)
    _fill(st, days[:55], 20, r15=-0.002)                                     # 55日×20＝1100件（F1）
    F.judge(st)
    v = st["verdicts"]["F1"]
    assert v["status"] == "stop" and v["decided_on"] == days[49] and v["n"] == 1000   # 50日目に1000回に届いた
    assert "マイナス" in v["reason"] and max(t["d"] for t in st["trades"] if t["c"] == "F1") == days[49]
    _fill(st, days[55:], 20, r15=0.05)                                       # ストップ後は数えない・判定は変わらない
    F.judge(st)
    assert sum(1 for t in st["trades"] if t["c"] == "F1") == 1000 and st["verdicts"]["F1"] == v
    assert "F2" not in st["verdicts"]                                        # 当てはまりが無いものは観察中のまま


def test_plus_keeps_counting_and_uncertain_plus_stops():
    st = F.empty_state()
    days = _days(60)
    _fill(st, days[:52], 20, r15=0.01)
    F.judge(st)
    assert st["verdicts"]["F1"]["status"] == "plus"
    _fill(st, days[52:], 20, r15=0.01)
    assert sum(1 for t in st["trades"] if t["c"] == "F1") == 1200             # プラスは数え続ける
    st2 = F.empty_state()
    recs = []
    for i, d in enumerate(days[:50]):                                        # 平均は少しプラス・ばらつきが大きい
        for j in range(20):
            recs.append(_rec(d, f"S{j:02d}", r15=0.0012 + (0.03 if (i + j) % 2 else -0.03)))
    F.update(st2, recs, {d: 1.0 for d in days}, today="2099-01-01")
    F.judge(st2)
    v = st2["verdicts"]["F1"]
    assert v["status"] == "stop" and v["mean"] > 0 and "言い切れない" in v["reason"]


def test_outputs_have_no_codes_and_verified_list(tmp_path=None):
    import json
    import tempfile
    st = F.empty_state()
    days = _days(55)
    _fill(st, days, 20, r15=-0.002)
    F.judge(st)
    st["generated_at"], st["prereg_sha256"] = "x", "a" * 64
    md = F.render_md(st)
    assert "⏹ ストップ" in md and "S001" not in md and "投資助言ではありません" in md
    assert all(len(t["k"]) == 8 and not t["k"].startswith("S") for t in st["trades"])
    d = tmp_path or tempfile.mkdtemp()
    p = os.path.join(str(d), "yori-forward.json")
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(st, fh, ensure_ascii=False)
    stop, plus, watching = V.collect([(p, "J4F テスト", "J4F")])
    assert [r["id"] for r in stop] == ["F1"] and not plus and [r["id"] for r in watching] == ["F2", "F3", "F4"]
    out = V.render(stop, plus, watching, now="x")
    assert "J4F-F1" in out and "期待値がプラスにならなかった" in out and "S001" not in out
    assert "- まだ無い" in V.render([], [], [], now="x")


def test_load_state_never_resets_a_broken_record():
    import tempfile
    d = tempfile.mkdtemp()
    assert F.load_state(os.path.join(d, "none.json"))["trades"] == []            # 無ければ空から
    bad = os.path.join(d, "bad.json")
    open(bad, "w").write("{broken")
    for path, text in ((bad, None), (os.path.join(d, "old.json"), '{"fwd_start": "2026-01-01", "trades": [1]}')):
        if text:
            open(path, "w").write(text)
        try:
            F.load_state(path)
            raise AssertionError("止まらなかった")
        except (SystemExit, ValueError):
            pass

def test_workflow_and_sync_forbidden():
    wf = open(".github/workflows/yori-forward.yml", encoding="utf-8").read()
    line = [x for x in wf.splitlines() if "pip install" in x][0]
    assert all(p in line.split() for p in ("numpy", "pandas", "yfinance"))
    assert "python yori_forward.py" in wf and "python verified_list.py" in wf
    assert "yori-forward.json yori-forward.md verified-list.md" in wf
    import check_site_consistency as C
    for f in ("yori-forward.json", "yori-forward.md", "verified-list.md"):
        assert f in C.SYNC_FORBIDDEN, f
    import check_automation_health as H
    assert any(w[1] == "yori-forward.yml" for w in H.WORKFLOW_CHECKS)


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
