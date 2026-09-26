# -*- coding: utf-8 -*-
"""ファンダの見立てとシグナルの向き（fbias）の次元と、その前向き登録のテスト。2026-09-26 新設。

signal_env_profile.py で唯一「傾向あり」になった区分（ファンダの見立てと逆向き）を、オーナー指示で
研究日誌のトラッカーに前向き登録した。区分の決め方と登録の中身を固定する。

実行:  python tests/test_fbias_dim.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import signal_lab_verify as V  # noqa: E402


def _d(aligned, direction="ロング（買い）"):
    return {"primary_signal": "rsi_oversold_bounce", "direction": direction,
            "fundamental_context": {"bias_aligned": aligned}}


def test_fbias_of_mapping():
    assert V.fbias_of(_d(True)) == "aligned"
    assert V.fbias_of(_d(False)) == "mismatch"
    assert V.fbias_of(_d(None)) is None                     # 見立てが中立・向きなし
    assert V.fbias_of({"direction": "ロング（買い）"}) is None  # 記録なし
    assert V.fbias_of(_d("false")) is None                  # 真偽値でないものは読まない


def test_match_uses_fbias_and_missing_never_matches():
    assert V.match(_d(False), {"fbias": "mismatch"})
    assert not V.match(_d(True), {"fbias": "mismatch"})
    assert V.match(_d(True), {"fbias": "aligned"})
    assert not V.match(_d(None), {"fbias": "aligned"}) and not V.match(_d(None), {"fbias": "mismatch"})


def test_key_is_allowed():
    assert "fbias" in V.ALLOWED_FILTER_KEYS


def test_tracker_declares_the_pair():
    import signal_lab_tracker as T
    regs = {h["id"]: h for h in T.REGISTER_ENVPROFILE_2026_09_26["register"]}
    assert set(regs) == {"ep_fbias_mismatch", "ep_fbias_aligned"}
    assert regs["ep_fbias_mismatch"]["filter"] == {"fbias": "mismatch"} and regs["ep_fbias_mismatch"]["kind"] == "edge"
    assert regs["ep_fbias_aligned"]["filter"] == {"fbias": "aligned"}
    assert regs["ep_fbias_mismatch"]["pair"] == "ep_fbias_aligned" and regs["ep_fbias_aligned"]["pair"] == "ep_fbias_mismatch"
    for h in regs.values():
        assert h["registered_at"] == "2026-09-26" and set(h["filter"]) <= V.ALLOWED_FILTER_KEYS
    assert T.plain_name({"fbias": "mismatch"}).startswith("ファンダの見立てと逆向き")


def test_watcher_picks_up_the_new_declarations():
    import check_automation_health as H
    import signal_lab_tracker as T
    ids = {h["id"] for h in H.declared_hypotheses(T)}
    assert {"ep_fbias_mismatch", "ep_fbias_aligned"} <= ids
    absent = [h for h in T.REGISTER_ENVPROFILE_2026_09_26["register"]]
    missing, pending = H.split_missing(absent, dt.date(2026, 9, 27))
    assert not missing and len(pending) == 2   # 登録の翌日までは「反映待ち」


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
