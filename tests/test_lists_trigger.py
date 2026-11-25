# -*- coding: utf-8 -*-
"""手元で数えて送る研究の記録が、リストを作り直すワークフロー（research-lists.yml）のきっかけに入っているかの検査
（check_site_consistency.check_lists_trigger）のテスト。2026-11-25 新設（オーナー「知らせる」）。

動機＝送る記録10本（SB・KT1・KT2・OJ〜OJ3 など）がきっかけ（on.push.paths）に無く、送っても検証済みリストが作り直されなかった。

確かめること＝①足し忘れは error（名前と直し方を言う）②入っていれば何も出さない ③'*-screen.json' のような形でも当たる
④送らない記録（GitHub 側で作るもの）は見ない ⑤コメントにした行は数えない ⑥paths のほかの欄にある名前は数えない
⑦ワークフローが無い・paths が読めないときは黙って通さない ⑧本物のリポジトリに足し忘れが無い ⑨main がこの検査を呼ぶ。

実行:  python tests/test_lists_trigger.py     （pytest 不要。pytest でも動く）
"""
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import check_site_consistency as csc  # noqa: E402

READER = '''SOURCES = [
    ("a-lab.json", "A の検証", ""),
    ("b-lab.json", "B の検証", ""),
    ("github-side.json", "GitHub 側で作る検証", ""),
]
SCREEN_SOURCES = [("m9-screen.json", "M9")]
'''
WF = """name: Research Lists
on:
  push:
    branches: [main]
    paths:
{paths}
  workflow_dispatch:
jobs:
  lists:
    strategy:
      matrix:
        file:
          - 'b-lab.json'
    steps:
      - run: cat 'b-lab.json'
"""


def _run_in(paths, sync, wf=True):
    """paths＝きっかけの行（そのまま書く）。sync＝手元から送るファイル。→ error の並び"""
    saved = csc.SD
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, ".github", "workflows"))
        with open(os.path.join(d, "verified_list.py"), "w", encoding="utf-8") as f:
            f.write(READER)
        if wf:
            with open(os.path.join(d, ".github", "workflows", "research-lists.yml"), "w", encoding="utf-8") as f:
                f.write(WF.format(paths="\n".join("      " + p for p in paths)))
        csc.SD = d
        csc.errors.clear()
        csc.warnings.clear()
        try:
            csc.check_lists_trigger(sync)
            return list(csc.errors)
        finally:
            csc.SD = saved
            csc.errors.clear()
            csc.warnings.clear()


def test_missing_record_is_an_error_naming_the_file_and_the_fix():
    errs = _run_in(["- 'a-lab.json'"], {"a-lab.json", "b-lab.json"})
    assert len(errs) == 1, errs
    assert "b-lab.json" in errs[0] and "research-lists.yml" in errs[0] and "a-lab.json" not in errs[0]


def test_listed_record_is_silent():
    assert _run_in(["- 'a-lab.json'", "- 'b-lab.json'   # 説明"], {"a-lab.json", "b-lab.json"}) == []


def test_double_quoted_and_bare_lines_count_as_listed():
    assert _run_in(['- "a-lab.json"', "- b-lab.json"], {"a-lab.json", "b-lab.json"}) == []


def test_glob_line_covers_the_record():
    assert _run_in(["- 'a-lab.json'", "- '*-screen.json'"], {"a-lab.json", "m9-screen.json"}) == []


def test_record_that_is_not_sent_from_here_is_ignored():
    assert _run_in(["- 'a-lab.json'"], {"a-lab.json"}) == []


def test_sent_file_that_the_list_does_not_read_is_ignored():
    assert _run_in(["- 'a-lab.json'"], {"a-lab.json", "my-trades.json"}) == []


def test_commented_out_line_does_not_count():
    errs = _run_in(["- 'a-lab.json'", "# - 'b-lab.json'"], {"a-lab.json", "b-lab.json"})
    assert len(errs) == 1 and "b-lab.json" in errs[0]


def test_name_outside_the_paths_block_does_not_count():
    """b-lab.json はひな形の別の一覧（matrix）と run: の中にだけある＝きっかけではない"""
    errs = _run_in(["- 'a-lab.json'"], {"b-lab.json"})
    assert len(errs) == 1 and "b-lab.json" in errs[0]


def test_comment_line_inside_the_block_does_not_end_it():
    assert _run_in(["- 'a-lab.json'", "# 2026-11-25 ここから手元の記録", "- 'b-lab.json'"], {"a-lab.json", "b-lab.json"}) == []


def test_missing_workflow_is_an_error():
    errs = _run_in([], {"a-lab.json"}, wf=False)
    assert len(errs) == 1 and "research-lists.yml" in errs[0]


def test_empty_paths_is_an_error():
    errs = _run_in([], {"a-lab.json"})
    assert len(errs) == 1 and "research-lists.yml" in errs[0]


def test_real_repository_has_no_missing_record():
    sync = csc.get_sync_files()
    if sync is None:          # クラウド（sync_to_github.py がスタブ）では手元から送る一覧が分からない
        return
    csc.errors.clear()
    try:
        csc.check_lists_trigger(sync)
        assert csc.errors == []
    finally:
        csc.errors.clear()


def test_main_runs_the_check():
    """main を実際に回して、手元から送る一覧がそのまま渡ることを見る（ほかの検査の結果は見ない）"""
    got, saved = [], (csc.check_lists_trigger, csc.get_sync_files)
    csc.check_lists_trigger = lambda s: got.append(s)
    csc.get_sync_files = lambda: {"a-lab.json"}
    out, argv = sys.stdout, sys.argv
    sys.stdout, sys.argv = open(os.devnull, "w", encoding="utf-8"), ["check_site_consistency.py", "--quiet"]
    try:
        csc.main()
    except SystemExit:
        pass
    finally:
        sys.stdout.close()
        sys.stdout, sys.argv = out, argv
        csc.check_lists_trigger, csc.get_sync_files = saved
        csc.errors.clear()
        csc.warnings.clear()
    assert got == [{"a-lab.json"}]


def test_main_skips_the_check_when_the_sync_list_is_unknown():
    """クラウドではスタブなので一覧が分からない＝自動公開を止めない"""
    got, saved = [], (csc.check_lists_trigger, csc.get_sync_files)
    csc.check_lists_trigger = lambda s: got.append(s)
    csc.get_sync_files = lambda: None
    out, argv = sys.stdout, sys.argv
    sys.stdout, sys.argv = open(os.devnull, "w", encoding="utf-8"), ["check_site_consistency.py", "--quiet"]
    try:
        csc.main()
    except SystemExit:
        pass
    finally:
        sys.stdout.close()
        sys.stdout, sys.argv = out, argv
        csc.check_lists_trigger, csc.get_sync_files = saved
        csc.errors.clear()
        csc.warnings.clear()
    assert got == []


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
