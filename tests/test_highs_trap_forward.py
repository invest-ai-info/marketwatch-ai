# -*- coding: utf-8 -*-
"""J10F 高値更新の翌朝の罠の目印・前向き（highs_trap_forward.py）と J10b の記録（j10b_records.py）のテスト。2026-10-06 新設。

値動きはすべて作り物（ネットワークに出ない）。確かめること＝①事前登録と定数の一致 ②一覧は1日1回だけ写し、10/6 より前は写さない
③A は登録の日より前・場が終わっていない日・5分足が足りない日を数えず、1日は一度だけ ④B は翌朝が終わってから数え、
足りなければ待ち、10営業日で取れた分だけ数え、古すぎれば「数えられなかった」にし、数えたらコードを消す
⑤判定は目印ありが1000回に届いた日に1回だけ・ストップはそれより後を外す ⑥出力に銘柄コードを出さない
⑦検証済みリストの「目印」の節 ⑧ワークフロー・SYNC禁忌・見張り ⑨J10b は比率だけ・20営業日まで平均を出さない。

実行:  python tests/test_highs_trap_forward.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import json
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import highs_trap_forward as F  # noqa: E402
import j10b_records as B  # noqa: E402
import verified_list as V  # noqa: E402

JST = F.P.JST


def _5m(day, close930):
    t = dt.datetime.combine(dt.date.fromisoformat(day), dt.time(9, 0), JST)
    return [(t + dt.timedelta(minutes=5 * i), 100.0, 100.0, 100.0, (close930 if i >= 5 else 100.0), 1.0) for i in range(8)]


def _daily(days, opens):
    return [(dt.datetime.combine(dt.date.fromisoformat(d), dt.time(9, 0), JST), o, o, o, o, 1.0) for d, o in zip(days, opens)]


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "## J10F 高値更新の翌朝の罠の目印・前向き" in text
    assert F.FWD_START == "2026-10-07" and "翌朝が **2026-10-07 以降**" in text
    assert F.LIST_START == "2026-10-06" and "2026-10-06 夜から東証の全上場" in text
    assert F.GOAL == 1000 and "目印ありの取引が1000回に届いた日に1回だけ" in text
    assert F.ALPHA == 0.05 and "**95％の幅**" in text and F.GAP_UP == 0.01 and "**+1％ 以上**" in text
    assert F.MIN_COVER_A == 0.95 and "ユニバースの95％未満" in text and F.MIN_COVER_B == 0.90 and "90％以上" in text
    assert F.B_WAIT_DAYS == 10 and "10営業日を過ぎたら" in text and F.B_TOO_OLD == 55 and "55日超" in text
    assert B.START == "2026-10-07" and B.GOAL_DAYS == 20 and "記録が20営業日たまった日に1回だけ" in text
    assert B.EMPTY == 0.005 and "0.5％ 以上" in text and "比率だけ" in text


def test_capture_once_and_not_before_start():
    st = F.empty_state()
    h = {"asof": "2026-10-06", "universe": 3700, "highs": [{"code": "1111", "price": 100.0}, {"code": "2222", "price": 50.0}]}
    assert F.capture(st, h, "x") == "2026-10-06"
    assert F.capture(st, h, "y") is None and st["lists"]["2026-10-06"]["captured_at"] == "x"
    assert st["lists"]["2026-10-06"]["items"] == [["1111", 100.0], ["2222", 50.0]]
    assert F.capture(st, dict(h, asof="2026-10-05"), "z") is None and "2026-10-05" not in st["lists"]
    assert F.capture(st, None, "z") is None


def _recs(day, n_flag, n_plain, r_flag, r_plain):
    out = []
    for i in range(n_flag):
        out.append({"date": day, "code": f"F{i}", "gap": 0.02, "r930": r_flag})
    for i in range(n_plain):
        out.append({"date": day, "code": f"P{i}", "gap": 0.0, "r930": r_plain})
    return out


def test_update_a_counts_each_day_once_and_skips():
    st = F.empty_state()
    recs = _recs("2026-10-06", 1, 1, -0.01, 0.0) + _recs("2026-10-07", 2, 3, -0.01, 0.0) + _recs("2026-10-08", 1, 1, 0, 0)
    cover = {"2026-10-06": 400, "2026-10-07": 400, "2026-10-08": 300, "2026-10-09": 400}
    assert F.update_a(st, recs, cover, 400, cut="2026-10-09") == 1           # 10/6＝登録前・10/8＝足りない・10/9＝場が終わっていない
    assert list(st["days"]["A"]) == ["2026-10-07"] and len(st["trades"]) == 5
    assert sum(t["f"] for t in st["trades"]) == 2 and all(len(t["k"]) == 8 for t in st["trades"])
    assert F.update_a(st, recs, cover, 400, cut="2026-10-09") == 0           # 数えた日は数え直さない


def _fetch_for(target, opens, p930s, missing=()):
    def fetch(code, interval, rng):
        if code in missing:
            return None
        if interval == "1d":
            return _daily([target], [opens[code]])
        return _5m(target, p930s[code])
    return fetch


def test_process_b_counts_after_the_morning_and_erases_codes():
    st = F.empty_state()
    F.capture(st, {"asof": "2026-10-06", "highs": [{"code": "1111", "price": 100.0}, {"code": "2222", "price": 100.0}]}, "x")
    tdays = ["2026-10-06", "2026-10-07", "2026-10-08"]
    fetch = _fetch_for("2026-10-07", {"1111": 102.0, "2222": 100.0}, {"1111": 101.0, "2222": 100.5})
    assert F.process_b(st, tdays, cut="2026-10-07", today="2026-10-07", fetch=fetch) == 0   # 翌朝の場がまだ終わっていない
    assert F.process_b(st, tdays, cut="2026-10-08", today="2026-10-08", fetch=fetch) == 1
    L = st["lists"]["2026-10-06"]
    assert L["status"] == "done" and L["items"] == [] and L["n_items"] == 2 and L["got"] == 2
    ts = sorted(st["trades"], key=lambda t: -t["f"])
    assert [t["f"] for t in ts] == [1, 0] and abs(ts[0]["r"] - (101 / 102 - 1)) < 1e-6 and ts[0]["c"] == "B"
    assert "1111" not in json.dumps(st) and "2222" not in json.dumps(st)


def test_process_b_waits_then_counts_partial_and_marks_lost():
    st = F.empty_state()
    items = [{"code": f"{1000 + i}", "price": 100.0} for i in range(10)]
    F.capture(st, {"asof": "2026-10-06", "highs": items}, "x")
    opens = {it["code"]: 100.0 for it in items}
    fetch = _fetch_for("2026-10-07", opens, {c: 100.0 for c in opens}, missing={"1000", "1001"})   # 8/10＝足りない
    tdays = ["2026-10-06", "2026-10-07", "2026-10-08"]
    assert F.process_b(st, tdays, cut="2026-10-08", today="2026-10-08", fetch=fetch) == 0
    assert st["lists"]["2026-10-06"]["status"] == "pending"
    many = tdays + [f"2026-10-{d:02d}" for d in range(9, 25)]
    assert F.process_b(st, many, cut="2026-10-24", today="2026-10-24", fetch=fetch) == 1         # 10営業日を過ぎた＝取れた分で
    assert st["lists"]["2026-10-06"]["got"] == 8
    st2 = F.empty_state()
    F.capture(st2, {"asof": "2026-10-06", "highs": items}, "x")
    assert F.process_b(st2, tdays, cut="2026-12-31", today="2026-12-31", fetch=fetch) == 0
    assert st2["lists"]["2026-10-06"]["status"] == "lost" and st2["lists"]["2026-10-06"]["items"] == []


def _fill(st, arm, n_days, per_day_flag, per_day_plain, eff, rnd):
    for k in range(n_days):
        day = (dt.date(2026, 10, 7) + dt.timedelta(days=k)).isoformat()
        st["days"][arm][day] = {"n": per_day_flag + per_day_plain}
        for i in range(per_day_flag):
            st["trades"].append({"c": arm, "d": day, "k": f"a{rnd.randrange(300)}", "g": 0.02, "r": eff + rnd.gauss(0, 0.01), "f": 1})
        for i in range(per_day_plain):
            st["trades"].append({"c": arm, "d": day, "k": f"b{rnd.randrange(300)}", "g": 0.0, "r": rnd.gauss(0, 0.01), "f": 0})


def test_judge_once_at_goal_confirm_and_stop():
    rnd = random.Random(5)
    st = F.empty_state()
    _fill(st, "A", 120, 10, 30, -0.006, rnd)          # 目印ありが 1000回に届くのは100日目
    _fill(st, "B", 120, 10, 30, 0.0, rnd)             # 差なし
    F.judge(st)
    va, vb = st["verdicts"]["A"], st["verdicts"]["B"]
    assert va["status"] == "confirm" and va["n"] == 1000 and va["hi"] < 0
    assert vb["status"] == "stop" and vb["n"] == 1000 and vb["decided_on"] == va["decided_on"]
    assert max(t["d"] for t in st["trades"] if t["c"] == "B") == vb["decided_on"]        # ストップ＝その日より後は外す
    assert max(t["d"] for t in st["trades"] if t["c"] == "A") > va["decided_on"]         # 確認＝数え続ける
    before = json.dumps(st["verdicts"], sort_keys=True)
    F.judge(st)
    assert json.dumps(st["verdicts"], sort_keys=True) == before                          # 判定は変えない


def test_not_judged_before_goal():
    rnd = random.Random(6)
    st = F.empty_state()
    _fill(st, "A", 30, 10, 30, -0.02, rnd)
    F.judge(st)
    assert st["verdicts"] == {}


def test_outputs_have_no_codes_and_verified_list():
    rnd = random.Random(7)
    st = F.empty_state()
    _fill(st, "A", 20, 5, 10, -0.005, rnd)
    F.capture(st, {"asof": "2026-10-06", "highs": [{"code": "7203", "price": 3000.0}]}, "x")
    md = F.render_md(st)
    assert "7203" not in md and "観察中（目印あり 100/1000" in md and "投資助言ではありません" in md
    path = "_tmp_highs_trap_forward.json"
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(st, fh)
        rows = V.collect_markers([(path, "J10F テスト", "J10F")])
        assert len(rows) == 2 and rows[0]["n"] == 100 and rows[1]["n"] == 0
        out = V.render([], [], [], now="x", markers=rows)
        assert "## 🔎 目印（見分け方）の前向き" in out and "J10F-A" in out and "目印あり 100/1000回" in out
        st["verdicts"]["A"] = {"status": "stop", "decided_on": "2027-01-01", "n": 1000, "mean": -0.001, "lo": -0.003, "hi": 0.001,
                               "reason": "r"}
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(st, fh)
        out = V.render([], [], [], now="x", markers=V.collect_markers([(path, "J10F テスト", "J10F")]))
        assert "⏹ ストップ" in out and "2027-01-01" in out
    finally:
        os.remove(path)


def test_load_state_never_resets_a_broken_record():
    path = "_tmp_htf_state.json"
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"fwd_start": "2026-01-01", "kind": "marker"}, fh)
        try:
            F.load_state(path)
            raise AssertionError("違う登録日なのに読み込んだ")
        except SystemExit:
            pass
    finally:
        os.remove(path)
    assert F.load_state("_no_such_file.json")["fwd_start"] == F.FWD_START


def test_workflow_sync_forbidden_and_watch():
    wf = open(".github/workflows/highs-trap-forward.yml", encoding="utf-8").read()
    assert 'workflows: ["JP Highs Lows"]' in wf and "--capture-only" in wf and "python verified_list.py" in wf
    assert "highs-trap-forward.json" in wf and "verified-list.md" in wf
    name = open(".github/workflows/jp-highs.yml", encoding="utf-8").read().split("\n", 1)[0]
    assert name.strip() == "name: JP Highs Lows"                      # 相乗り先の name と一字一句同じ
    lint = open("check_site_consistency.py", encoding="utf-8").read()
    assert '"highs-trap-forward.json", "highs-trap-forward.md"' in lint
    health = open("check_automation_health.py", encoding="utf-8").read()
    assert '"highs-trap-forward.yml", 24 * 4' in health and '"highs-trap-forward.yml", 3' in health


def test_j10b_records_are_ratios_only_and_judged_once_at_20_days():
    st = B.empty_state()
    try:
        B.add(st, B.make_record("2026-10-06", 100, 101, 100.5, 100, 101.1, 101.5, 100.9, 100.0))
        raise AssertionError("10/6 を足せてしまった")
    except SystemExit:
        pass
    r = B.make_record("2026-10-07", 7777, 7899.5, 7848, 7707, 7900, 7901, 7899, 7861)
    assert set(r) == {"date", "gap857", "gap_open", "r930", "away_up", "away_down"}
    assert 7777 not in r.values() and abs(r["gap857"] - (7899.5 / 7777 - 1)) < 1e-6
    assert B.empty_side(r) is None or B.empty_side(r) == "down"
    assert B.empty_side({"away_up": 0.01, "away_down": 0.001}) == "up" and B.empty_side({"away_up": 0.001, "away_down": 0.002}) is None
    rnd = random.Random(8)
    for k in range(19):
        day = (dt.date(2026, 10, 7) + dt.timedelta(days=k)).isoformat()
        for _ in range(5):
            B.add(st, B.make_record(day, 100, 100 + rnd.uniform(0.5, 2), 100 + rnd.uniform(-0.3, 0.3), 100))
    assert B.judge(st) is None and "途中の平均は出さない" in B.status_text(st)
    B.add(st, B.make_record("2026-11-01", 100, 101.5, 100.1, 100))
    v = B.judge(st)
    assert v and v["status"] == "縮みやすい" and v["lo"] > 0 and v["days"] == 20
    B.add(st, B.make_record("2026-11-02", 100, 100.0, 103.0, 100))
    assert B.judge(st) == v                                         # 判定は変えない


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
