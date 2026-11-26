"""「🔍 数え直し待ち」の表示のテスト（検算の関門・作業7）。pytest 不要・pytest でも動く。

  PYTHONUTF8=1 python tests/test_recheck_display.py
"""
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import promotion_list as P  # noqa: E402
import recheck_status as S  # noqa: E402
import research_map as RM  # noqa: E402
import verified_list as V  # noqa: E402

GL = "2026-11-27"


def _root(stores):
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, "recheck"))
    for kind, body in stores.items():
        with open(os.path.join(d, "recheck", f"{kind}.json"), "w", encoding="utf-8") as f:
            json.dump(body, f)
    return d


def _row(sec, cid, decided_on, status="plus"):
    return {"src": "x.json", "sec": sec, "id": cid, "title": f"{sec} の決まり", "goal": 1000, "unit": "pct", "n": 1000,
            "v": {"status": status, "decided_on": decided_on, "n": 1000, "mean": 0.01, "lo": 0.001, "hi": 0.02, "reason": ""}}


def test_promoted_waiting_helper():
    r = _root({})
    assert S.promoted_waiting({"id": "e", "status": "promoted", "promoted_at": "2026-12-01"}, r, GL)
    assert not S.promoted_waiting({"id": "rl_tf_adx_strong", "status": "promoted", "promoted_at": "2026-11-07"}, r, GL)
    assert not S.promoted_waiting({"id": "e", "status": "tracking", "promoted_at": "2026-12-01"}, r, GL)


def test_verified_list_moves_new_pass_to_waiting():
    plus = [_row("J9F", "F1", "2026-12-01"), _row("J4F", "F1", "2026-11-20")]
    ok, wait = V.split_waiting(plus, _root({}), go_live=GL)
    assert [r["sec"] for r in ok] == ["J4F"] and [r["sec"] for r in wait] == ["J9F"]
    md = V.render([], ok, [], "2026-12-02", waiting=wait)
    assert md.index("✅ プラスを確認") < md.index("🔍 数え直し待ち") < md.index("👀")
    assert "J9F-F1" in md[md.index("🔍 数え直し待ち"):md.index("👀")]


def test_no_waiting_section_when_empty():
    assert "🔍 数え直し待ち" not in V.render([], [_row("J4F", "F1", "2026-11-20")], [], "2026-12-02")


def test_record_releases_to_pass():
    root = _root({"records": {"J9F-F1": {"n_orig": 5, "matched": 5, "agreement": 1.0}}})
    ok, wait = V.split_waiting([_row("J9F", "F1", "2026-12-01")], root, go_live=GL)
    assert ok and not wait


def test_marker_confirm_waits():
    m = [_row("J26F", "C", "2026-12-01", status="confirm")]
    assert "🔍 数え直し待ち" in "\n".join(V.render_markers(m, root=_root({}), go_live=GL))
    old = [_row("J26F", "C", "2026-11-01", status="confirm")]
    assert "✅ 確認" in "\n".join(V.render_markers(old, root=_root({}), go_live=GL))


def test_promotion_list_keeps_waiting_out_of_gold():
    wait = [_row("J9F", "F1", "2026-12-01")]
    md = P.render([], [], "2026-12-02", waiting=wait)
    gold = md[md.index("🥇"):md.index("## 🔍")]
    assert "J9F-F1" not in gold and "🔍 数え直し待ち" in md


def test_promotion_candidate_is_marked():
    sc = [{"src": "m6-screen.json", "rounds": [], "promoted": [
        {"id": "c1", "round": "R1", "stage": "candidate", "since": "2026-12-01",
         "screen": {"n": 250, "win": 0.6, "mean": 0.1, "lo": 0.01, "hi": 0.2, "pf": 1.3, "placebo_p": 0.01}}]}]
    orig = P.J.describe
    P.J.describe = lambda s, i: "中身"
    try:
        md = P.render([], sc, "2026-12-02", root=_root({}), go_live=GL)
    finally:
        P.J.describe = orig
    assert "数え直し待ち" in md[md.index("🔬"):]


def test_map_stage_shows_waiting_but_keeps_adx():
    assert RM._stage({"id": "new", "status": "promoted", "promoted_at": "2026-12-01"}, root=_root({}), go_live=GL)[0] == "wait"
    assert RM._stage({"id": "rl_tf_adx_strong", "status": "promoted", "promoted_at": "2026-11-07"},
                     root=_root({}), go_live=GL)[0] == "done"


def test_method_lab_promotion_waits_in_diary_table():
    import research_rotation as RR
    reg = {"methods": [{"id": "m_new", "name": "新しい方法", "status": "promoted", "registered_at": "2026-12-01",
                        "promoted_at": "2026-12-01", "forward": {"n": 5}}]}
    html_ = RR.research_list({"hypotheses": []}, reg, root=_root({}), go_live=GL)
    assert "数え直し待ち" in html_ and ">昇格<" not in html_


if __name__ == "__main__":
    n = 0
    for k, fn in list(globals().items()):
        if k.startswith("test_") and callable(fn):
            fn()
            n += 1
    print(f"ok {n}")
