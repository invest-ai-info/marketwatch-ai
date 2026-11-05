#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""inject_books.py — 本のアフィリエイト（Amazon・楽天ブックス）のリンクを、投資本のページと読者の多い記事へ冪等に入れる。

2026-11-05 オーナー「本のアフィリエイトも同時に進めてください」。
GA4（10/8〜11/4）で読者がいちばん多い記事は guide-nisa.html（606回・平均 2分13秒）＝投資本のページ（上位10に入らない）
だけに置いても届かないので、NISA の記事にも「このテーマを本で深めたい人へ」の小さな枠を置く。

方針（inject_ads.py と同じ考え方）:
  - **ID が空のあいだは何もしない**（オーナーが Amazon アソシエイト／楽天アフィリエイトに登録して、下の2つに入れるまで眠っている）。
    ID はリンクの中にそのまま出る公開の値（秘密ではない）。
  - 「広告」の表示は必須（景表法のステマ規制・2023-10-01）。ページの最初に「本のリンクは広告です」を1回、
    Amazon を使うときはアソシエイトの決まりの一文も出す。
  - 推す言葉を足さない（「おすすめ」「必読」「勝てる」などを書かない）。本の説明は今ある文のまま。
  - リンクは rel="sponsored nofollow noopener"（Google の決まりどおりアフィリエイトと分かる印）。
  - ISBN はクラウドから引けない（書誌の API が届かない）ので、書名＋著者の**検索結果**へのリンクにする。
    手元のセッションで ISBN を足せば、1冊のページへのリンクに替えられる（ISBN 表に足すだけ）。
  - 冪等：入れた所は <!-- mw-book:begin --> 〜 <!-- mw-book:end --> で囲む。毎回いったん外してから入れ直す。
  - guide-new-books.html（予約 book-watch-weekly が書く・SYNC禁忌）は触らない。手順書 drafts/BOOKWATCH_GUIDE.md に
    「アフィリエイトリンクは張らない」とある（読んでいない新刊の紹介だから）＝変えるならオーナーが決める。

使い方:
  python inject_books.py --dry-run             # 何をするかだけ表示（書き込まない）
  python inject_books.py                       # ID が入っていれば入れる（空なら何もしない）
  python inject_books.py --remove              # 入れたものを全部外す
  python inject_books.py --sample --amazon-tag test-22   # リンクの形を確かめる（書き込まない）
"""
import argparse
import html
import os
import re
import sys
from urllib.parse import quote

HERE = os.path.dirname(os.path.abspath(__file__))

# ── オーナーが登録したら入れる（空のままなら何もしない） ─────────────────────────
AMAZON_TAG = ""     # Amazon アソシエイトのトラッキングID（例 "marketwatch-22"）
RAKUTEN_ID = ""     # 楽天アフィリエイトID（例 "1a2b3c4d.5e6f7a8b.1a2b3c4d.5e6f7a8b"）
# ────────────────────────────────────────────────────────────────────────────

from apply_site_frame import SITE_NAME   # サイト名の単一の真実（2026-11-05「時短投資ラボ」）
BOOKS_PAGE = "guide-investment-books.html"
# 読者の多い記事に置く枠（書名は投資本のページにある本だけ＝著者はそこから取る）
BOXES = {
    "guide-nisa.html": ("長期・インデックス投資",
                        ["インデックス投資は勝者のゲーム", "お金は寝かせて増やしなさい", "敗者のゲーム"]),
}
# ISBN-13 が分かった本だけ 1冊のページへのリンクにする（手元のセッションで足す・無ければ検索結果へのリンク）
ISBN = {}

BEGIN, END = "<!-- mw-book:begin -->", "<!-- mw-book:end -->"
BLOCK_RE = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END) + r"\n?", re.S)
BOOK_RE = re.compile(r'<div class="book-t">(.*?)<span class="book-a">／(.*?)</span>.*?</div>(<div class="book-d">.*?</div>)', re.S)
TAG_OK = re.compile(r"^[a-z0-9][a-z0-9-]{0,40}-2[0-9]$")
RAKUTEN_OK = re.compile(r"^[0-9a-f]{8}(\.[0-9a-f]{8}){3}$")
REL = 'rel="sponsored nofollow noopener" target="_blank"'

CSS = ("<style data-mw-book>"
       ".mw-bk{margin-top:6px;font-size:.82rem;color:#57606a}"
       ".mw-bk a,.mw-books li a{color:#0969da;text-decoration:underline}.mw-bk-sep{color:#8b949e;margin:0 8px}"
       ".mw-bk-label,.mw-books-label{display:inline-block;font-size:.62rem;color:#8b949e;border:1px solid #d0d7de;"
       "border-radius:4px;padding:0 4px;margin-right:6px;letter-spacing:.08em}"
       ".mw-books-note{max-width:760px;margin:12px auto 18px;padding:10px 14px;font-size:.8rem;color:#57606a;"
       "background:#f6f8fa;border:1px solid #d0d7de;border-radius:10px;line-height:1.7}"
       ".mw-books{max-width:680px;margin:32px auto 0;padding:14px 16px;border:1px solid #d0d7de;border-radius:12px;background:#fff}"
       ".mw-books-t{font-weight:600;margin:4px 0 8px}.mw-books ul{margin:0;padding-left:1.2em}.mw-books li{margin:6px 0;line-height:1.6}"
       "</style>")


def check_ids(tag, rid):
    """渡された ID の形を確かめる（空はよい＝その店は出さない）。おかしければ理由の文字列のリスト"""
    bad = []
    if tag and not TAG_OK.match(tag):
        bad.append(f"Amazon のトラッキングID「{tag}」の形が違う（例 marketwatch-22）")
    if rid and not RAKUTEN_OK.match(rid):
        bad.append(f"楽天アフィリエイトID「{rid}」の形が違う（例 1a2b3c4d.5e6f7a8b.1a2b3c4d.5e6f7a8b）")
    return bad


def keyword(title, author):
    """検索に使う言葉＝書名＋著者（「・」「、」「編」「著」は空白に）。純関数"""
    a = re.sub(r"\s*(編|著|訳)$", "", author.strip())
    a = re.sub(r"[・、,]", " ", a)
    return re.sub(r"\s+", " ", f"{title} {a}").strip()


def links(title, author, tag, rid):
    """[(店の名前, URL)]。ID が空の店は出さない。純関数"""
    kw = keyword(title, author)
    isbn = ISBN.get(title)
    out = []
    if tag:
        if isbn:
            url = f"https://www.amazon.co.jp/s?k={isbn}&i=stripbooks&tag={tag}"
        else:
            url = f"https://www.amazon.co.jp/s?k={quote(kw)}&i=stripbooks&tag={tag}"
        out.append(("Amazonで見る", url))
    if rid:
        target = f"https://books.rakuten.co.jp/search?sitem={quote(isbn or kw)}"
        enc = quote(target, safe="")
        out.append(("楽天ブックスで見る", f"https://hb.afl.rakuten.co.jp/hgc/{rid}/?pc={enc}&m={enc}"))
    return out


def anchor_html(pairs):
    return '<span class="mw-bk-sep">／</span>'.join(
        f'<a href="{html.escape(u, quote=True)}" {REL}>{name}</a>' for name, u in pairs)


def note_html(tag, rid):
    stores = "・".join(s for s, on in (("Amazon", tag), ("楽天ブックス", rid)) if on)
    s = (f"本のリンク（{stores}）はアフィリエイト広告です。リンクから本が買われると、当サイトに紹介料が入ることがあります。"
         "紹介料のあるなしで、本の選び方や説明を変えることはしません。")
    if tag:
        s += f"Amazonのアソシエイトとして、{SITE_NAME}は適格販売により収入を得ています。"
    return s


def strip(c):
    """入れたものを全部外す（CSS も）"""
    return BLOCK_RE.sub("", c)


def apply_books_page(c, tag, rid):
    """投資本のページ：最初の系統の前に「広告です」の1文、各本の説明の下に店のリンク。(新しい本文, 本の数)"""
    c = strip(c)
    n = 0

    def rep(m):
        nonlocal n
        title, author = html.unescape(m.group(1)).strip(), html.unescape(m.group(2)).strip()
        pairs = links(title, author, tag, rid)
        if not pairs:
            return m.group(0)
        n += 1
        return (m.group(0) + BEGIN + '<div class="mw-bk"><span class="mw-bk-label">広告</span>📚 '
                + anchor_html(pairs) + "</div>" + END)

    c = BOOK_RE.sub(rep, c)
    if n:
        i = c.find('<div class="bookcat"')
        if i < 0:
            raise SystemExit(f"🚨 {BOOKS_PAGE} に本の系統（bookcat）が見つからない＝入れない")
        top = (BEGIN + "\n" + CSS + '\n<div class="mw-books-note" aria-label="広告について">'
               '<span class="mw-books-label">広告</span>' + note_html(tag, rid) + "</div>\n" + END + "\n")
        c = c[:i] + top + c[i:]
    return c, n


def book_authors(books_html):
    """投資本のページの {書名: 著者}"""
    return {html.unescape(t).strip(): html.unescape(a).strip() for t, a in
            re.findall(r'<div class="book-t">(.*?)<span class="book-a">／(.*?)</span>', books_html)}


def apply_box(c, page, cat, titles, authors, tag, rid):
    """読者の多い記事：記事の最後の広告（A8）の前に小さな枠を1つ。(新しい本文, 本の数)"""
    c = strip(c)
    items = []
    for t in titles:
        if t not in authors:
            raise SystemExit(f"🚨 {page} の枠の本「{t}」が {BOOKS_PAGE} に無い＝入れない（書名を投資本のページに合わせる）")
        pairs = links(t, authors[t], tag, rid)
        if pairs:
            items.append(f"<li><b>{html.escape(t)}</b>／{html.escape(authors[t])}<br>{anchor_html(pairs)}</li>")
    if not items:
        return c, 0
    box = (BEGIN + "\n" + CSS + '\n<div class="mw-books" aria-label="広告">'
           '<span class="mw-books-label">広告</span>'
           f'<div class="mw-books-t">📚 このテーマを本で深めたい人へ（<a href="{BOOKS_PAGE}">投資本の系統別ガイド</a>の「{cat}」から）</div>'
           "<ul>" + "".join(items) + "</ul>"
           f'<div class="mw-bk">{note_html(tag, rid)}</div></div>\n' + END + "\n")
    i = c.find("<!-- ===== 広告 (A8.net")
    if i < 0:
        i = c.find('<div class="mw-ad"')
    if i < 0:
        i = c.find("<footer")
    if i < 0:
        raise SystemExit(f"🚨 {page} に入れる場所（広告の枠か footer）が見つからない")
    return c[:i] + box + c[i:], len(items)


def run(tag, rid, remove=False, dry=False, root=HERE, out=print):
    bad = check_ids(tag, rid)
    if bad:
        raise SystemExit("🚨 " + " / ".join(bad))
    if not remove and not (tag or rid):
        out("ID が未設定（AMAZON_TAG・RAKUTEN_ID が空）＝何もしない。オーナーが登録したら inject_books.py の先頭に入れて実行する")
        return {}
    pages = [BOOKS_PAGE] + list(BOXES)
    with open(os.path.join(root, BOOKS_PAGE), encoding="utf-8") as fh:
        authors = book_authors(fh.read())
    done = {}
    for page in pages:
        path = os.path.join(root, page)
        with open(path, encoding="utf-8") as fh:
            c0 = fh.read()
        if remove:
            c, n = strip(c0), 0
        elif page == BOOKS_PAGE:
            c, n = apply_books_page(c0, tag, rid)
        else:
            cat, titles = BOXES[page]
            c, n = apply_box(c0, page, cat, titles, authors, tag, rid)
        done[page] = n
        changed = c != c0
        out(f"{'（試し）' if dry else ''}{page}: 本 {n} 冊{'・変更あり' if changed else '・変更なし'}")
        if changed and not dry:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(c)
    return done


def main(argv=None):
    ap = argparse.ArgumentParser(description="本のアフィリエイトのリンクを冪等に入れる（ID が空なら何もしない）")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--remove", action="store_true")
    ap.add_argument("--sample", action="store_true", help="リンクの形を表示するだけ")
    ap.add_argument("--amazon-tag", default=None)
    ap.add_argument("--rakuten-id", default=None)
    a = ap.parse_args(argv)
    tag = AMAZON_TAG if a.amazon_tag is None else a.amazon_tag
    rid = RAKUTEN_ID if a.rakuten_id is None else a.rakuten_id
    if a.sample:
        bad = check_ids(tag, rid)
        if bad:
            raise SystemExit("🚨 " + " / ".join(bad))
        for name, u in links("敗者のゲーム", "チャールズ・エリス", tag, rid) or [("（ID が空）", "")]:
            print(name, u)
        return 0
    run(tag, rid, remove=a.remove, dry=a.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
