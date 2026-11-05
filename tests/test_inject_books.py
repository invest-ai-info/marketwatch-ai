# -*- coding: utf-8 -*-
"""inject_books.py（本のアフィリエイト）のテスト。本物のページを一時フォルダに写して試す（リポジトリのページは触らない）"""
import os
import shutil
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import inject_books as IB  # noqa: E402

TAG = "test-22"
RID = "1a2b3c4d.5e6f7a8b.1a2b3c4d.5e6f7a8b"


@pytest.fixture
def site(tmp_path):
    for p in [IB.BOOKS_PAGE] + list(IB.BOXES):
        shutil.copy(os.path.join(ROOT, p), tmp_path / p)
    return tmp_path


def read(site, p):
    return (site / p).read_text(encoding="utf-8")


def test_空のIDなら何もしない(site):
    before = {p: read(site, p) for p in [IB.BOOKS_PAGE] + list(IB.BOXES)}
    assert IB.run("", "", root=str(site), out=lambda *_: None) == {}
    assert all(read(site, p) == c for p, c in before.items())


def test_リポジトリの既定は空のID():
    # オーナーが登録して入れるまで眠っている（ここが空でなくなったらこのテストを直す）
    assert IB.AMAZON_TAG == "" and IB.RAKUTEN_ID == ""


def test_入れると全部の本と枠にリンクと広告の表示が付く(site):
    done = IB.run(TAG, RID, root=str(site), out=lambda *_: None)
    books = read(site, IB.BOOKS_PAGE)
    n_books = books.count('<div class="book-t">')
    assert done[IB.BOOKS_PAGE] == n_books == 28
    assert books.count('<span class="mw-bk-label">広告</span>') == n_books
    assert f"Amazonのアソシエイトとして、{IB.SITE_NAME}は適格販売により収入を得ています。" in books
    assert books.count("tag=test-22") == n_books
    assert books.count("hb.afl.rakuten.co.jp/hgc/" + RID) == n_books
    assert 'rel="sponsored nofollow noopener"' in books
    nisa = read(site, "guide-nisa.html")
    assert done["guide-nisa.html"] == 3
    assert nisa.find('class="mw-books"') < nisa.find('<div class="mw-ad"')   # A8 の広告の前に置く
    assert 'aria-label="広告"' in nisa and "アフィリエイト広告" in nisa


def test_推す言葉を足さない(site):
    IB.run(TAG, RID, root=str(site), out=lambda *_: None)
    for p in [IB.BOOKS_PAGE] + list(IB.BOXES):
        added = "".join(IB.BLOCK_RE.findall(read(site, p)))
        for w in ("おすすめ", "オススメ", "必読", "勝てる", "儲か", "絶対"):
            assert w not in added, (p, w)


def test_冪等で外すと元に戻る(site):
    orig = {p: read(site, p) for p in [IB.BOOKS_PAGE] + list(IB.BOXES)}
    IB.run(TAG, RID, root=str(site), out=lambda *_: None)
    once = {p: read(site, p) for p in orig}
    IB.run(TAG, RID, root=str(site), out=lambda *_: None)
    assert {p: read(site, p) for p in orig} == once
    IB.run(TAG, RID, remove=True, root=str(site), out=lambda *_: None)
    assert {p: read(site, p) for p in orig} == orig


def test_片方の店だけでもよい(site):
    IB.run(TAG, "", root=str(site), out=lambda *_: None)
    books = read(site, IB.BOOKS_PAGE)
    assert "amazon.co.jp" in books and "rakuten" not in books.split(IB.BEGIN, 1)[1]
    IB.run("", RID, root=str(site), out=lambda *_: None)
    books = read(site, IB.BOOKS_PAGE)
    assert "amazon.co.jp/s?" not in books and "アソシエイト" not in books


def test_IDの形がおかしければ止める():
    assert IB.check_ids("marketwatch", "") and IB.check_ids("", "abc")
    assert IB.check_ids(TAG, RID) == []
    with pytest.raises(SystemExit):
        IB.run("bad tag", "", out=lambda *_: None)


def test_検索の言葉():
    assert IB.keyword("投資の大原則", "バートン・マルキール、チャールズ・エリス") == "投資の大原則 バートン マルキール チャールズ エリス"
    assert IB.keyword("バフェットからの手紙", "ローレンス・カニンガム 編") == "バフェットからの手紙 ローレンス カニンガム"
    u = dict(IB.links("ファスト&スロー", "ダニエル・カーネマン", TAG, ""))["Amazonで見る"]
    assert "%26" in u and u.endswith("&tag=test-22")   # 書名の & は検索の言葉の中でつぶす
