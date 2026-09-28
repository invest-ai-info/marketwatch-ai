# -*- coding: utf-8 -*-
"""failure_patrol.py（失敗の一覧）の純関数のテスト。2026-09-28 新設。

固定すること: 失敗だけをワークフロー×ブランチでまとめる（成功・取り消しは数えない）／
「そのあと成功したか」は最後の失敗より後の成功だけで決める／注記の決まり文句は落とす／
見張り番の報告から 🚨 行と §④ のコミット番号を取り出す。

実行:  python tests/test_failure_patrol.py     （pytest 不要。pytest でも動く）
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import failure_patrol as F  # noqa: E402


def _run(i, path, branch, conclusion, created, event="schedule"):
    return {"id": i, "name": path.split("/")[-1], "path": path, "head_branch": branch, "workflow_id": 1,
            "conclusion": conclusion, "created_at": created, "event": event,
            "html_url": f"https://example/{i}"}


def test_groups_only_failures_by_workflow_and_branch():
    runs = [
        _run(1, "wf/a.yml", "main", "failure", "2026-09-28T01:00:00Z"),
        _run(2, "wf/a.yml", "main", "timed_out", "2026-09-28T03:00:00Z"),
        _run(3, "wf/a.yml", "claude/x", "failure", "2026-09-28T02:00:00Z"),
        _run(4, "wf/b.yml", "main", "success", "2026-09-28T04:00:00Z"),
        _run(5, "wf/b.yml", "main", "cancelled", "2026-09-28T05:00:00Z"),
    ]
    g = F.group_failures(runs)
    assert [(x["path"], x["branch"], x["count"]) for x in g] == [("wf/a.yml", "main", 2), ("wf/a.yml", "claude/x", 1)]
    a = g[0]
    assert a["first"] == "2026-09-28T01:00:00Z" and a["last"] == "2026-09-28T03:00:00Z" and a["latest"]["id"] == 2


def test_later_success_uses_only_runs_after_the_last_failure():
    runs = [_run(1, "wf/a.yml", "main", "success", "2026-09-28T00:00:00Z"),
            _run(2, "wf/a.yml", "main", "failure", "2026-09-28T02:00:00Z"),
            _run(3, "wf/a.yml", "main", "success", "2026-09-28T04:00:00Z"),
            _run(4, "wf/a.yml", "main", "success", "2026-09-28T03:00:00Z")]
    assert F.later_success("2026-09-28T02:00:00Z", runs)["id"] == 4          # いちばん早い回復
    assert F.later_success("2026-09-28T05:00:00Z", runs) is None             # 前の成功では解決にしない


def test_boring_annotations_are_dropped():
    anns = [{"annotation_level": "failure", "message": "Process completed with exit code 1."},
            {"annotation_level": "warning", "message": "Node.js 20 is deprecated. The following ..."},
            {"annotation_level": "notice", "message": "The ubuntu-latest label will migrate ..."},
            {"annotation_level": "failure", "message": "ModuleNotFoundError: No module named 'yfinance'\nmore"}]
    assert F.useful_annotations(anns) == ["ModuleNotFoundError: No module named 'yfinance'"]


def test_alarm_lines_and_gate_shas():
    report = ("### ④ 固定ゲート\n"
              "- 🚨 🟡 check_site_consistency.py が Claude(login=claude) により変更されている（eb9d9fc・15.6h前）＝…\n"
              "- 🚨 🟡 exit_lab_verify.py が Claude(login=claude) により変更されている（aa18574・24.1h前）＝…\n"
              "- 🚨 🟡 check_site_consistency.py が Claude(login=claude) により変更されている（eb9d9fc・15.6h前）＝…\n"
              "- ✅ 🟢 公開記事 210 件すべてが掲載済み\n"
              "- 🚨 ⚪ 信用残の鮮度確認に失敗: timeout\n")
    lines = F.alarm_lines(report)
    assert len(lines) == 4 and all(ln.startswith("- 🚨") for ln in lines)
    assert F.gate_shas(lines) == ["eb9d9fc", "aa18574"]                      # 重複は1回・順番は保つ


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
