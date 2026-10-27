# -*- coding: utf-8 -*-
"""警察庁の詐欺の統計の見張り（npa_stats_watch.py・npa-stats-watch.yml）のテスト。2026-10-27 新設。

通信はしない。確かめること＝①ページの見出し（全角数字・元年）を読める ②月末の途中経過は数えない
③本で使っている公表より新しいものだけを拾う ④ワークフローは読むだけ・見張り番に登録済み。

実行:  python tests/test_npa_stats_watch.py     （pytest 不要。pytest でも動く）
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import npa_stats_watch as W  # noqa: E402

# 2026-10-27 に取ったページの形（見出しの部分だけ）
PAGE = """
<p>＜令和８年の特殊詐欺の手口についてのお知らせ＞</p>
<p>※　令和７年以前の数値については、従来通りです。</p>
<p><b>　</b>特殊詐欺の認知・検挙状況等（令和８年８月末・暫定値）について</p>
<p><strong>・</strong>特殊詐欺の認知・検挙状況等（令和８年上半期・暫定値）について</p>
<p>　※　特殊詐欺の認知・検挙状況等（令和８年上半期・暫定値）の訂正について（令和８年８月５日）</p>
<p><strong>・<a id="x"></a></strong>特殊詐欺及びSNS型投資・ロマンス詐欺の認知・検挙状況等（令和７年・確定値）について</p>
<p>　※　特殊詐欺及びSNS型投資･ロマンス詐欺の認知･検挙状況等(令和７年・確定値)の訂正</p>
<p><strong>・</strong>特殊詐欺の認知・検挙状況等（令和元年・確定値）について</p>
"""


def test_parse_reads_labels_and_skips_month_end():
    found = W.parse(PAGE)
    assert (8, "上半期", "暫定値") in found
    assert (7, "年", "確定値") in found
    assert (1, "年", "確定値") in found                      # 元年
    assert not any(p[1].endswith("月末") for p in found)     # 8月末の途中経過は数えない
    assert len(found) == 3


def test_nothing_newer_than_the_book_today():
    assert W.newer_than_book(W.parse(PAGE)) == []


def test_new_year_and_half_year_publications_are_picked_up_in_order():
    page = PAGE + "（令和９年上半期・暫定値）（令和８年・確定値）（令和８年・暫定値）（令和９年１月末・暫定値）"
    assert [W.label(p) for p in W.newer_than_book(W.parse(page))] == [
        "令和8年・暫定値", "令和8年・確定値", "令和9年上半期・暫定値"]


def test_mail_names_the_new_publication_and_the_steps():
    subject, body = W.build_mail([(8, "年", "暫定値")])
    assert "令和8年・暫定値" in subject
    assert "BOOK_USES" in body and "PUBLISH_CHECKLIST.md" in body


def test_workflow_is_read_only_and_watched():
    wf = open(".github/workflows/npa-stats-watch.yml", encoding="utf-8").read()
    assert "contents: read" in wf and "git push" not in wf
    assert "workflow_dispatch" in wf
    health = open("check_automation_health.py", encoding="utf-8").read()
    assert '"npa-stats-watch.yml"' in health


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
