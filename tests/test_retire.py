# -*- coding: utf-8 -*-
"""見込みなしで止める決まり（2026-10-07 オーナー「検証中リストは増えすぎても見づらくなるので、見込みがないと思ったら
検証済みリストに移動させてください」）のテスト。決まり＝PILLAR_PREREG.md「見込みなしで止める決まり」。

確かめること＝①事前登録と定数の一致 ②仮説の見込みなし（効きが小さすぎる／時間がかかりすぎる）と、止めないもの
③トラッカーの集計で ⏹（retired）になり戻らない・逆向きの登録はしない・反証に止めた日が残る
④前向きの腕の RETIRED（本当の判定が優先・検証済みリストの「⏹ ストップ」）⑤検証中リスト・研究の地図から外れ、
公開ページの「検証済みリストへ移したもの」に理由が載る（やさしい日本語・番号を出さない）。

実行:  python tests/test_retire.py     （pytest 不要。pytest でも動く）
"""
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))
os.chdir(ROOT)
import check_plain_japanese as C  # noqa: E402
import research_map as R  # noqa: E402
import signal_lab_tracker as T  # noqa: E402
import verified_list as V  # noqa: E402
from test_tracker_focus import _days, _run, _sig  # noqa: E402


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "## 見込みなしで止める決まり（検証中リストの整理）" in text
    assert (T.RETIRE_MIN_N, T.RETIRE_EFFECT_R, T.RETIRE_MIN_DAYS, T.RETIRE_MAX_DAYS) == (300, 0.10, 60, 730)
    assert "**300回以上**なのに" in text and "**良い側の端でも 0.10R に届かない**" in text
    assert "**60日以上**たち" in text and "**2年（730日）より長く**" in text
    assert "**根拠にその前向き自身の途中の数字は使わない**" in text
    for r in V.RETIRED:                                    # 止めた腕は、どれも登録の文に名前がある
        sec = {"F2": "J4F F2", "F4": "J4F F4", "F6": "J4G F6", "B": "J13F 腕B"}[r["id"]]
        assert f"**{sec}**" in text, sec


def _fwd(n, lo, hi, avg=0.0):
    return {"n": n, "avgR": avg, "rci_lo": lo, "rci_hi": hi}


def test_futility_rules_and_what_is_not_stopped():
    g = {"kind": "gate", "registered_at": "2026-06-25"}
    e = {"kind": "edge", "registered_at": "2026-06-25"}
    today = "2026-10-07"
    assert T.futility(g, _fwd(400, -0.08, 0.12), today) == "small"           # 良い側の端（下）でも −0.10R に届かない
    assert T.futility(g, _fwd(400, -0.12, 0.08), today) is None
    assert T.futility(g, _fwd(299, -0.05, 0.20), today) is None              # 300回未満は「小さすぎる」で止めない
    assert T.futility(e, _fwd(500, -0.10, 0.09), today) == "small"
    assert T.futility(e, _fwd(500, -0.05, 0.11), today) is None
    assert T.futility(e, _fwd(3000, 0.01, 0.09), today) is None              # 期待した向きにはっきり＝昇格の判定に任せる
    assert T.futility(g, _fwd(3000, -0.09, -0.01), today) is None
    assert T.futility(dict(g, promote_strikes=1), _fwd(400, -0.08, 0.12), today) is None
    assert T.futility(dict(g, pair="x"), _fwd(400, -0.08, 0.12), today) is None
    # 時間：104日で6回＝80回まで (80−6)×104÷6≒1283日 → 止める。60日未満はまだ速さが分からない
    assert T.futility(dict(e, registered_at="2026-06-25"), _fwd(6, -1, 1.4), today) == "slow"
    assert T.futility(dict(e, registered_at="2026-08-15"), _fwd(0, 0, 0), today) is None
    assert T.futility(dict(e, registered_at="2026-08-08"), _fwd(0, 0, 0), today) == "slow"
    assert T.futility(dict(e, registered_at="2026-07-19"), _fwd(1, 1.333, 1.333), today) == "slow"   # 1回だけの幅は当てにしない
    assert T.futility(dict(e, registered_at="2026-06-25"), _fwd(60, -0.3, 0.4), today) is None       # 80回まで約1か月
    ho = dict(e, registered_at="2026-06-25", holdout_pass=True)              # ホールドアウト合格は30回で判定
    assert T.futility(ho, _fwd(12, -0.5, 0.6), today) is None and T.futility(ho, _fwd(3, -0.5, 0.6), today) == "slow"   # (30−3)×104÷3≒936日


def test_tracker_update_retires_once_and_keeps_it():
    days = _days(400, start="2025-07-01")
    data = [_sig(d, "x_small", outcome="tp1" if (i + 1) * 177 // 400 > i * 177 // 400 else "sl")
            for i, d in enumerate(days)]                                     # 平均 +0.03R・幅 ±0.11R ほど
    data += [_sig(d, "x_rare") for d in ("2026-07-01", "2026-08-01")]         # 2回だけ
    hyps = [{"id": "g_small", "label": "小さすぎる(回避)", "kind": "gate", "filter": {"signal": "x_small"},
             "registered_at": "2025-06-30"},
            {"id": "e_rare", "label": "まれ", "kind": "edge", "filter": {"signal": "x_rare"}, "registered_at": "2026-06-01"},
            {"id": "e_new", "label": "新しい", "kind": "edge", "filter": {"signal": "x_rare"}, "registered_at": "2026-09-01"}]
    out = {h["id"]: h for h in _run(hyps, data, today="2026-09-26")}
    s = out["g_small"]
    assert s["status"] == "retired" and s["retired_at"] == "2026-09-26" and s["retire_reason"] == "small", s["forward"]
    assert -0.10 < s["forward"]["rci_lo"] < 0 < s["forward"]["rci_hi"]
    assert out["e_rare"]["status"] == "retired" and out["e_rare"]["retire_reason"] == "slow"
    assert out["e_new"]["status"] == "tracking"                                # 登録から60日未満
    assert not any(h["id"].endswith("__flip") for h in out.values())          # 逆向きの登録はしない
    more = data + [_sig(d, "x_small") for d in _days(200, start="2026-09-27")]   # そのあと勝ち続けても戻さない
    again = {h["id"]: h for h in _run(list(out.values()), more, today="2027-04-20")}
    assert again["g_small"]["status"] == "retired" and again["g_small"]["retired_at"] == "2026-09-26"


def test_rejection_keeps_the_day():
    data = [_sig(d, "bb_lower_touch", outcome="tp1" if i % 4 else "sl") for i, d in enumerate(_days(90, start="2026-06-26"))]
    out = {h["id"]: h for h in _run([{"id": "g1", "label": "BB(回避)", "kind": "gate", "filter": {"signal": "bb_lower_touch"},
                                      "registered_at": "2026-06-25"}], data)}
    assert out["g1"]["status"] == "rejected" and out["g1"]["rejected_at"] == "2026-09-26"


def test_table_and_state_words_know_retired():
    assert "⏹見込みなし" in T.STATE_WORDS
    assert T.state_cell("⏹見込みなし").count("white-space:nowrap") == 1


def _dump(d, name, obj):
    with open(os.path.join(d, name), "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False)


def _root():
    d = tempfile.mkdtemp()
    titles = {f"F{i}": f"形{i}" for i in range(1, 8)}
    _dump(d, R.YORI_FWD, {"fwd_start": "2026-09-29", "goal": 1000, "titles": titles, "verdicts": {},
                          "trades": [{"c": c} for c in ("F1", "F1", "F2", "F3", "F6")]})
    _dump(d, R.GAP_FWD, {"fwd_start": "2026-10-07", "goal_days": 250, "titles": {"B": "b"}, "verdicts": {},
                         "marker_titles": {"A": "a"}, "marker_verdicts": {}, "summary": {"days": 3}, "progress": {"A": 5, "B": 2}})
    hyps = [{"id": "zz_small", "kind": "gate", "filter": {"group": "metal"}, "status": "retired", "retire_reason": "small",
             "retired_at": "2026-10-08", "registered_at": "2026-06-17", "forward": {"n": 484, "avgR": 0.06, "rci_lo": -0.07, "rci_hi": 0.2}},
            {"id": "zz_rej", "kind": "gate", "filter": {"direction": "long"}, "status": "rejected",
             "registered_at": "2026-06-20", "forward": {"n": 900, "avgR": 0.1, "rci_lo": 0.02, "rci_hi": 0.2}},
            {"id": "zz_rej__flip", "kind": "edge", "filter": {"direction": "long", "fired_from": "2026-09-27"}, "status": "tracking",
             "flipped_from": "zz_rej", "flip_evidence": {"window": "2026-06-20〜2026-09-26"}, "registered_at": "2026-09-27",
             "forward": {"n": 10}},
            {"id": "zz_live", "kind": "edge", "filter": {"group": "metal", "direction": "long"}, "status": "tracking",
             "registered_at": "2026-09-01", "forward": {"n": 3}}]
    _dump(d, R.TRACKER_FILE, {"updated_at": "2026-10-08", "hypotheses": hyps})
    return d


def test_retired_arms_leave_the_lists():
    d = _root()
    m = R.collect(d)
    st = {r["name"]: r for r in R.collect_studies(d, m)["verify"]}
    yori = st["前の日に出来高が急に増えた日本株の、次の日の寄り付き"]["progress"]
    assert "形1 2回" in yori and "形3 1回" in yori and "形5 0回" in yori and "形7 0回" in yori
    assert "形2" not in yori and "形4" not in yori and "形6" not in yori and "見込みなしで止めた形 3つ" in yori
    gap = st["前の日の終わりの値段から離れて始まった日本株の、9時30分までの値動き"]["what"]
    assert "1パーセント以上高く始まった" in gap and "安く始まった銘柄をその値段で買う" not in gap
    ids = [r["id"] for th in m["themes"] for r in th["rows"]]
    assert "zz_small" not in ids and "zz_live" in ids                       # ⏹ は仮説の表から外れる
    ended = {r["name"]: r for r in m["ended"]}
    small = ended[T.plain_name({"group": "metal"})]
    assert small["ended"] == "2026-10-08" and "見込みなしで止めました" in small["why"]
    assert ended[T.plain_name({"direction": "long"})]["ended"] == "2026-09-26"   # 古い反証は逆向きの登録の日から


def test_list_page_shows_what_moved_in_plain_words():
    d = _root()
    page = R.build_list_page(root=d)
    jp = page.split('<h2 id="jp">', 1)[1].split("<h2 ", 1)[0]
    com = page.split('<h2 id="commodity">', 1)[1].split("<h2 ", 1)[0]
    assert "⏹ 検証済みリストへ移したもの：4件" in jp and all(r["name"] in jp for r in V.RETIRED)
    assert "⏹ 検証済みリストへ移したもの：1件" in com and "損切りの幅の1割に届かない" in com
    found = [f for f in C.check_html(page) if not (f[0] == "英字の略語" and "ADX" in f[1])]
    assert not found, found
    for code in ("J4F", "J4G", "J13F", "J19", "F2", "0.10R"):                 # 番号・記号は出さない
        assert code not in page, code
    for r in V.RETIRED:                                                     # 名前と理由はやさしい日本語
        assert not C.check_text(r["name"] + "。" + r["reason"], [], "x") if hasattr(C, "check_text") else True


def test_verified_list_shows_retired_arms_and_tracker_endings():
    d = _root()
    path = os.path.join(d, R.YORI_FWD)
    stop, plus, watching = V.collect([(path, "J4F", "J4F")])
    assert sorted(r["id"] for r in stop) == ["F2", "F4", "F6"] and len(watching) == 4
    v = {r["id"]: r["v"] for r in stop}["F2"]
    assert v["decided_on"] == "2026-10-07" and v["n"] == 4 and v["mean"] is None and "見込みなし" in v["reason"]
    data = json.load(open(path, encoding="utf-8"))                          # 本当の判定が出たら、そちらを優先
    data["verdicts"] = {"F2": {"status": "plus", "decided_on": "2031-01-05", "n": 1000, "mean": 0.002, "lo": 0.001, "hi": 0.003}}
    _dump(d, R.YORI_FWD, data)
    stop2, plus2, _ = V.collect([(path, "J4F", "J4F")])
    assert [r["id"] for r in plus2] == ["F2"] and "F2" not in [r["id"] for r in stop2]
    gstop, _, gw = V.collect([(os.path.join(d, R.GAP_FWD), "J13F", "J13F")])
    assert [r["id"] for r in gstop] == ["B"] and not gw
    marks = V.collect_markers([(os.path.join(d, R.GAP_FWD), "J13F", "J13F")])
    assert [r["id"] for r in marks] == ["A"] and marks[0]["v"] is None       # 目印の腕Aは数え続ける
    rows = V.collect_tracker(os.path.join(d, R.TRACKER_FILE))
    assert [r["id"] for r in rows] == ["zz_small", "zz_rej"]
    assert rows[1]["on"] == "2026-09-26" and "zz_rej__flip" in rows[1]["why"]
    md = V.render(stop, plus, watching, now="x", tracker=rows)
    assert "## 🧪 シグナルの条件（仮説）の採点で終わったもの" in md and "⏹ 見込みなし" in md and "⛔ 反証" in md
    assert "見込みなしで途中で止めた" in md and "J4F-F2" in md


def test_retired_registry_is_consistent():
    srcs = {s[0] for s in V.SOURCES} | {s[0] for s in V.MARKER_SOURCES}
    for r in V.RETIRED:
        assert r["src"] in srcs and r["cat"] in {k for k, *_ in R.MARKETS} and r["on"] and r["evidence"]
        assert isinstance(r["n"], int) and r["name"] and r["reason"]
        for w in ("J1", "J2", "F1", "→", "×", "R"):
            assert w not in r["name"] + r["reason"], (r["id"], w)
        if os.path.exists(r["src"]):                                         # いまの記録にその腕がある
            data = json.load(open(r["src"], encoding="utf-8"))
            assert r["id"] in {**(data.get("titles") or {}), **(data.get("marker_titles") or {})}


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
