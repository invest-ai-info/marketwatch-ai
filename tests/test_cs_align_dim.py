# -*- coding: utf-8 -*-
"""通貨の強弱とシグナルの向き（cs_align）の次元と、その前向き登録のテスト。2026-09-27 新設。

FXの実用書100冊の下調べで「多くの本が勧めるのに正式な検定が無い」と分かった候補を、オーナー了承で
研究日誌のトラッカーに前向き登録した（公開ページに過去の数字が出ているので、登録の翌日以降の発火だけを数える）。
区分の決め方と登録の中身を固定する。

実行:  python tests/test_cs_align_dim.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import signal_lab_verify as V  # noqa: E402


def _d(aligned, fired_at="2026-09-28T10:00:00+09:00", direction="ロング（買い）"):
    return {"primary_signal": "rsi_oversold_bounce", "direction": direction, "ticker": "AUDJPY=X",
            "fired_at": fired_at, "fx_alignment": {"aligned": aligned, "explanation": "", "suggested_direction": None}}


def test_cs_align_of_mapping():
    assert V.cs_align_of(_d(True)) == "aligned"
    assert V.cs_align_of(_d(False)) == "against"
    assert V.cs_align_of(_d(None)) is None                      # 強弱差0.2未満（中立）
    assert V.cs_align_of({"direction": "ロング（買い）"}) is None  # FX 以外・記録なし
    assert V.cs_align_of({"fx_alignment": None}) is None        # エンジンが None を書いた回
    assert V.cs_align_of(_d("true")) is None                    # 真偽値でないものは読まない


def test_match_uses_cs_align_and_missing_never_matches():
    assert V.match(_d(True), {"cs_align": "aligned"})
    assert not V.match(_d(False), {"cs_align": "aligned"})
    assert V.match(_d(False), {"cs_align": "against"})
    assert not V.match(_d(None), {"cs_align": "aligned"}) and not V.match(_d(None), {"cs_align": "against"})


def test_forward_only():
    """登録の翌日（CS_FROM）より前の発火は数えない（公開ページで過去の数字が見えているため）。"""
    import signal_lab_tracker as T
    f = {"cs_align": "aligned", "fired_from": T.CS_FROM}
    assert V.match(_d(True, fired_at=f"{T.CS_FROM}T00:30:00+09:00"), f)
    assert not V.match(_d(True, fired_at="2026-09-27T23:59:00+09:00"), f)


def test_key_is_allowed():
    assert "cs_align" in V.ALLOWED_FILTER_KEYS


def test_tracker_declares_the_pair():
    import signal_lab_tracker as T
    regs = {h["id"]: h for h in T.REGISTER_FXBOOKS_2026_09_27["register"]}
    assert set(regs) == {"cs_aligned", "cs_against"}
    assert T.CS_FROM == "2026-09-28"
    assert regs["cs_aligned"]["filter"] == {"cs_align": "aligned", "fired_from": T.CS_FROM}
    assert regs["cs_aligned"]["kind"] == "edge" and regs["cs_against"]["kind"] == "gate"
    assert regs["cs_against"]["filter"] == {"cs_align": "against", "fired_from": T.CS_FROM}
    assert regs["cs_aligned"]["pair"] == "cs_against" and regs["cs_against"]["pair"] == "cs_aligned"
    for h in regs.values():
        assert h["registered_at"] == T.CS_FROM and set(h["filter"]) <= V.ALLOWED_FILTER_KEYS
        assert "watch" not in h   # 観察中メールは付けない（メールは変えない）
    assert T.plain_name({"cs_align": "aligned"}).startswith("通貨の強弱と同じ向き")


def test_watcher_picks_up_the_new_declarations():
    import check_automation_health as H
    import signal_lab_tracker as T
    ids = {h["id"] for h in H.declared_hypotheses(T)}
    assert {"cs_aligned", "cs_against"} <= ids
    missing, pending = H.split_missing(list(T.REGISTER_FXBOOKS_2026_09_27["register"]), dt.date(2026, 9, 28))
    assert not missing and len(pending) == 2   # 登録の翌日までは「反映待ち」


def test_research_map_themes_the_key():
    import research_map as M
    env = [t for t in M.THEMES if t[0] == "env"][0]
    assert "cs_align" in env[3]


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
