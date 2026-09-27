# -*- coding: utf-8 -*-
"""MT4 の口座履歴（Statement.htm）が SYNC_FILES に入ったら止まることのテスト。2026-09-27 新設。

口座履歴には名前・口座番号・全取引が入る（投資スタイル診断 style_diagnosis.py の入力）。置き場所は research/ の下だが、
手元のフォルダの一番上に置かれることもあるので、名前でも止める。

実行:  python tests/test_sync_statement_guard.py     （pytest 不要。pytest でも動く）
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import check_site_consistency as C  # noqa: E402


def _errors(files):
    C.errors.clear()
    C.check_sync_forbidden(files)
    out = list(C.errors)
    C.errors.clear()
    return out


def test_statement_files_are_blocked():
    for f in ("Statement.htm", "statement.html", "DetailedStatement.htm", "Statement (2).htm", "research/Statement.htm"):
        assert _errors([f]), f


def test_ordinary_files_pass():
    assert _errors(["guide-statement-reading.html", "style_diagnosis.py", "guides.html"]) == []


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
