"""数え直しまで合格を「使わない」関門のテスト（メールの絞り・総当たりの MT5 段・検算の関門の作業8）。
pytest 不要・pytest でも動く。

  PYTHONUTF8=1 python tests/test_recheck_gate_live.py
"""
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import generate_technical_alerts as G  # noqa: E402
import screen_judge as J  # noqa: E402

GL = "2026-11-27"


def _root(stores):
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, "recheck"))
    for kind, body in stores.items():
        with open(os.path.join(d, "recheck", f"{kind}.json"), "w", encoding="utf-8") as f:
            json.dump(body, f)
    return d


def _root_raw(rel, text):
    d = tempfile.mkdtemp()
    p = os.path.join(d, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)
    return d


def _h(hid, kind, promoted_at):
    return {"id": hid, "kind": kind, "status": "promoted", "promoted_at": promoted_at,
            "filter": {"family": "tf", "dir": 1}, "label": hid}


def _tracker(hyps):
    d = tempfile.mkdtemp()
    p = os.path.join(d, "signal-lab-tracker.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"hypotheses": hyps}, f)
    return p


def _raises(exc, fn, *a, **kw):
    try:
        fn(*a, **kw)
    except exc:
        return
    raise AssertionError(f"{exc.__name__} が出なかった")


def _screen_record(since):
    return {"promoted": [{"id": "c1", "round": "R1", "stage": "candidate", "since": since,
                          "screen": {"n": 250, "mean": 0.1}, "mt5": None, "forward": None}],
            "stopped_after_promotion": []}


def _apply_mt5(rec, cid, root, go_live):
    return J.apply_mt5(rec, cid, [0.1] * 5, ["2026-12-01"] * 5, "2026-12-02", root=root, go_live=go_live)


def test_new_promoted_edge_waits_old_one_stays():
    p = _tracker([_h("new_edge", "edge", "2026-12-01"), _h("old_edge", "edge", "2026-11-07"),
                  _h("rl_tf_adx_strong", "gate", "2026-11-07")])
    ids = [h["id"] for h in G.load_promoted_hypotheses("edge", path=p, root=_root({}), go_live=GL)]
    assert ids == ["old_edge"]
    gates = [h["id"] for h in G.load_promoted_hypotheses("gate", path=p, root=_root({}), go_live=GL)]
    assert gates == ["rl_tf_adx_strong"]


def test_recorded_edge_is_used():
    p = _tracker([_h("new_edge", "edge", "2026-12-01")])
    root = _root({"records": {"new_edge": {"n_orig": 9, "matched": 9, "agreement": 1.0}}})
    assert [h["id"] for h in G.load_promoted_hypotheses("edge", path=p, root=root, go_live=GL)] == ["new_edge"]


def test_broken_records_do_not_crash_alerts():
    p = _tracker([_h("new_edge", "edge", "2026-12-01")])
    got = G.load_promoted_hypotheses("edge", path=p, root=_root_raw("recheck/records.json", "{"), go_live=GL)
    assert got == []


def test_unreadable_tracker_still_means_gate_off():
    assert G.load_promoted_hypotheses("edge", path=os.path.join(tempfile.mkdtemp(), "none.json")) is None


def test_default_call_still_works():
    got = G.load_promoted_hypotheses("gate")
    assert got is None or isinstance(got, list)


def test_screen_candidate_cannot_enter_mt5_before_recount():
    _raises(SystemExit, _apply_mt5, _screen_record("2026-12-01"), "c1", _root({}), GL)


def test_screen_candidate_with_record_or_old_can_enter():
    root = _root({"records": {"c1": {"n_orig": 250, "matched": 250, "agreement": 1.0}}})
    for rec in (_apply_mt5(_screen_record("2026-12-01"), "c1", root, GL),
                _apply_mt5(_screen_record("2026-11-20"), "c1", _root({}), GL)):
        assert not [x for x in rec["promoted"] if x["stage"] == "candidate"]   # 止められずに MT5 の段を通った（前向きへ／ストップ）


if __name__ == "__main__":
    n = 0
    for k, fn in list(globals().items()):
        if k.startswith("test_") and callable(fn):
            fn()
            n += 1
    print(f"ok {n}")
