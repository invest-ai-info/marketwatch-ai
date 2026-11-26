"""見張り番の「数え直し待ち」の節（check_automation_health.eval_recheck_waiting・検算の関門の作業10）のテスト。
新しく待ちが出た日から2日だけ Issue に出し、そのあとは一覧の行だけ（知らせ疲れを避ける）。pytest 不要・pytest でも動く。

  PYTHONUTF8=1 python tests/test_health_recheck.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import check_automation_health as H  # noqa: E402

GL = "2026-11-27"


def test_new_waiting_warns_then_quiet():
    tr = {"hypotheses": [{"id": "e1", "status": "promoted", "promoted_at": "2026-12-01"}]}
    assert H.eval_recheck_waiting(tr, {}, [], "2026-12-02", GL)[0] == "new"
    assert H.eval_recheck_waiting(tr, {}, [], "2026-12-03", GL)[0] == "new"
    assert H.eval_recheck_waiting(tr, {}, [], "2026-12-06", GL)[0] == "waiting"


def test_old_promotion_and_recorded_are_not_waiting():
    tr = {"hypotheses": [{"id": "rl_tf_adx_strong", "status": "promoted", "promoted_at": "2026-11-07"},
                         {"id": "e2", "status": "promoted", "promoted_at": "2026-12-01"}]}
    rec = {"e2": {"n_orig": 3, "matched": 3, "agreement": 1.0}}
    level, note, ids = H.eval_recheck_waiting(tr, rec, [], "2026-12-02", GL)
    assert level == "none" and ids == []


def test_screen_candidate_counts():
    sc = [{"promoted": [{"id": "c1", "stage": "candidate", "since": "2026-12-01"},
                        {"id": "c2", "stage": "mt5_ok", "since": "2026-12-01"}]}]
    level, note, ids = H.eval_recheck_waiting({"hypotheses": []}, {}, sc, "2026-12-01", GL)
    assert ids == ["c1"] and level == "new" and "c1" in note


def test_empty_inputs():
    assert H.eval_recheck_waiting(None, None, None, "2026-12-01", GL)[0] == "none"


if __name__ == "__main__":
    n = 0
    for k, fn in list(globals().items()):
        if k.startswith("test_") and callable(fn):
            fn()
            n += 1
    print(f"ok {n}")
