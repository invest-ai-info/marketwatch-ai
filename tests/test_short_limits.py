# -*- coding: utf-8 -*-
"""J40 売り禁・規制の前向き記録（short_limits.py）のテスト。2026-10-08 新設。

いまは probe だけ。確かめること＝①事前登録と定数の一致 ②リンクの拾い方（相対・絶対・同じ URL は1回）と規制の言葉の絞り込み
③銘柄コードを伏せる・表の形だけを出す ④probe は何も書き出さない ⑤ワークフローと SYNC 禁忌。

実行:  python tests/test_short_limits.py     （pytest 不要。pytest でも動く）
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import short_limits as S  # noqa: E402


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "## J40 売り禁・規制はどれくらいかかるか" in text and "**損益の判定はしない**" in text and "`--probe`" in text
    assert "**3割以上**" in text and "`jp-margin.json`" in text
    names = " ".join(n for n, _ in S.SITES)
    assert "日本証券金融" in names and "増担保" in names and "日々公表" in names and "注意喚起" in names


def test_links_and_keywords():
    html = ('<a href="/brand/">貸借取引情報･銘柄別制限措置</a><a href="https://x.jp/a.csv">申込停止 一覧</a>'
            '<a href="b.html"><span>会社概要</span></a><a href="/brand/">重複</a><a href="mailto:x@y">メール</a>')
    got = S.links(html, "https://www.taisyaku.jp/top/index.html")
    assert got == [("https://www.taisyaku.jp/brand/", "貸借取引情報･銘柄別制限措置"), ("https://x.jp/a.csv", "申込停止 一覧"),
                   ("https://www.taisyaku.jp/top/b.html", "会社概要")]
    assert [u for u, _ in S.keyword_links(got)] == ["https://www.taisyaku.jp/brand/", "https://x.jp/a.csv"]   # 会社概要は外す
    assert S.FILE_EXT.search("https://x.jp/a.csv") and not S.FILE_EXT.search("https://x.jp/a.html")


def test_mask_and_tables_show_shape_only():
    assert S.mask("7203") == "（コード）" and S.mask("130A") == "（コード）" and S.mask("72030") == "（コード）"
    assert S.mask("規制の内容がとても長い文字列です") == "規制の内容がとても長い文字列"
    html = ("<table><tr><th>銘柄名</th><th>コード</th><th>実施日</th></tr><tr><td>甲（株）</td><td>7203</td><td>2026/10/08</td></tr>"
            "<tr><td>乙</td><td>6758</td><td>2026/10/07</td></tr></table>")
    (n, head, second), = S.html_tables(html)
    assert n == 3 and head == ["銘柄名", "コード", "実施日"] and second == ["…", "（コード）", "2026/10/08"]
    assert "甲" not in repr(S.html_tables(html))
    assert S.decode("申込停止".encode("cp932")) == "申込停止" and S.decode("規制".encode()) == "規制"


def test_probe_writes_nothing():
    pages = {"http://www.taisyaku.jp/brand/": '<a href="/brand/list.html">銘柄別の制限措置（申込停止）</a>'.encode(),
             "http://www.taisyaku.jp/brand/list.html": b"<table><tr><th>\xe3\x82\xb3\xe3\x83\xbc\xe3\x83\x89</th></tr></table>"}
    before = set(os.listdir("."))
    orig = S.SITES
    try:
        S.SITES = (("日本証券金融（銘柄別の制限措置）", "http://www.taisyaku.jp/brand/"),)
        assert S.probe(get=lambda u: pages[u]) == 0
    finally:
        S.SITES = orig
    assert set(os.listdir(".")) == before and S.main([]) == 1


def test_workflow_and_sync_forbidden():
    wf = open(".github/workflows/short-limits.yml", encoding="utf-8").read()
    assert "python -u short_limits.py --probe" in wf and "python tests/test_short_limits.py" in wf and "contents: read" in wf
    assert '"short-limits.json", "short-limits.md"' in open("check_site_consistency.py", encoding="utf-8").read()


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"✅ {name}")
            except AssertionError as e:
                fails += 1
                print(f"❌ {name}: {e}")
    sys.exit(1 if fails else 0)
