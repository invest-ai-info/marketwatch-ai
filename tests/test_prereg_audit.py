"""登録の関門（mw check＝check_site_consistency.check_prereg_audit・検算の関門の作業9）のテスト。
使い始めの日より後の登録で、結果を書いた節には「点検の指紋」が要る。pytest 不要・pytest でも動く。

  PYTHONUTF8=1 python tests/test_prereg_audit.py
"""
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import check_site_consistency as csc  # noqa: E402

GL = "2026-11-27"


def _root(stores):
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, "recheck"))
    for kind, body in stores.items():
        with open(os.path.join(d, "recheck", f"{kind}.json"), "w", encoding="utf-8") as f:
            json.dump(body, f)
    return d


def _run(text, root, go_live):
    csc.errors.clear()
    csc.warnings.clear()
    csc.check_prereg_audit(text=text, root=root, go_live=go_live)


def test_new_registration_with_result_needs_audit():
    t = "# 登録\n## X1 試し（2026-12-01 登録）\n本文\n**結果（2026-12-02・登録どおり1回）**：ストップ\n"
    _run(t, _root({}), GL)
    assert any("点検の指紋" in e for e in csc.errors)


def test_audit_fingerprint_passes_and_errors_fail():
    fp = "ab12cd34ef56"
    t = f"## X1 試し（2026-12-01 登録）\n**結果（2026-12-02・点検の指紋 `{fp}`）**：ストップ\n"
    _run(t, _root({"audits": {"X1": {"fingerprint": fp + "0" * 52, "errors": 0}}}), GL)
    assert not csc.errors
    _run(t, _root({"audits": {"X1": {"fingerprint": fp + "0" * 52, "errors": 2}}}), GL)
    assert csc.errors
    _run(t, _root({}), GL)
    assert any("見つからない" in e for e in csc.errors)


def test_old_undated_and_duplicate_ids_are_fine():
    t = ("## OJ5 v5（2026-11-26 登録）\n**結果（2026-11-28）**：x\n"
         "## B4 追記（2026-09-27 午後）\n**結果（2026-09-28）**：x\n"
         "## 共通の決まり\n**結果（…）**\n")
    _run(t, _root({}), GL)
    assert not csc.errors


def test_registration_without_result_is_fine():
    _run("## X2 まだ（2026-12-01 登録）\n本文\n", _root({}), GL)
    assert not csc.errors


def test_fingerprint_must_be_inside_the_result_part():
    fp = "ab12cd34ef56"
    t = (f"## X3 試し（2026-12-01 登録）\n点検の指紋 `{fp}`\n**結果（2026-12-02）**：x\n"
         "## X4 次（2026-12-03 登録）\n本文\n")
    _run(t, _root({"audits": {"X3": {"fingerprint": fp + "0" * 52, "errors": 0}}}), GL)
    assert any("X3" in e for e in csc.errors)


def test_real_prereg_has_no_errors_today():
    _run(None, ROOT, None)
    assert not csc.errors, csc.errors[:3]


def test_bullet_and_heading_result_markers():
    _run("## X6 試し（2026-12-01 登録）\n本文\n- **結果（2026-12-02）**：ストップ\n", _root({}), GL)
    assert any("X6" in e for e in csc.errors)
    _run("## X7 試し（2026-12-01 登録）\n本文\n### 結果\nストップ\n", _root({}), GL)
    assert any("X7" in e for e in csc.errors)


def test_substage_date_governs():                  # 古い ## の下の新しい ### の登録
    t = "## OJ 押し目（2026-11-24 登録）\n本文\n### 段4（2026-12-01 登録）\n**結果（2026-12-02）**：x\n"
    _run(t, _root({}), GL)
    assert any("段4" in e for e in csc.errors)
    old = "## OJ 押し目（2026-11-24 登録）\n**結果（2026-11-25）**：x\n### 追記①（2026-12-01）\n本文\n"
    _run(old, _root({}), GL)
    assert not csc.errors, csc.errors


def test_refused_gate_record_does_not_pass():
    fp = "ab12cd34ef56"
    t = f"## X8 試し（2026-12-01 登録）\n**結果（2026-12-02・点検の指紋 `{fp}`）**：x\n"
    _run(t, _root({"audits": {"X8": {"fingerprint": fp + "0" * 52, "errors": 0, "passed": False}}}), GL)
    assert csc.errors


def test_heading_with_dot_before_registered():
    _run("## X9 試し（2026-12-01・夜 登録）\n**結果（2026-12-02）**：x\n", _root({}), GL)
    assert any("X9" in e for e in csc.errors)


if __name__ == "__main__":
    n = 0
    for k, fn in list(globals().items()):
        if k.startswith("test_") and callable(fn):
            fn()
            n += 1
    print(f"ok {n}")
