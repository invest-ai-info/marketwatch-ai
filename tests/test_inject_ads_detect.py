# -*- coding: utf-8 -*-
"""inject_ads.py の「広告がもうあるか」の見分け（2026-11-05）。
共通 CSS（apply_site_frame の AD_GAP_CSS＝div.mw-ad{...}）の文字だけでは「広告あり」にしない。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import apply_site_frame as F  # noqa: E402
import inject_ads as IA  # noqa: E402


def test_共通CSSの文字だけでは広告ありにしない():
    page = "<html><head>" + F.FRAME_STYLE_TAG + "</head><body><p>本文</p><footer></footer></body></html>"
    assert "mw-ad" in page                      # 文字はある（9/23 からの全ページ）
    assert not IA.HAND_AD_RE.search(page)       # でも広告の要素は無い


def test_広告の要素があれば広告あり():
    assert IA.HAND_AD_RE.search('<div class="mw-ad" aria-label="広告">')
    assert IA.HAND_AD_RE.search('<div class="mw-ad mw-x">')
    assert not IA.HAND_AD_RE.search('<div class="mw-ads-note">')


def test_研究のまとめは外す():
    assert IA.is_denied("guide-time-anomalies-after-papers.html")
    assert IA.is_denied("guide-signal-lab-140.html")
    assert not IA.is_denied("guide-news-2026-11-04-us-midterms.html")


def test_生成ページに広告を1つだけ():
    page = ('<html><body><main>表</main>' + IA.NL_MARKER + ' --><div class="mw-newsletter"></div>'
            '<footer>f</footer></body></html>')
    once = IA.add_page_ad(page, "calendar.html")
    assert once.count('class="mw-ad"') == 1
    assert once.find('class="mw-ad"') < once.find(IA.NL_MARKER)      # メルマガの前
    assert IA.add_page_ad(once, "calendar.html") == once              # 冪等
    no_nl = IA.add_page_ad("<html><body><footer>f</footer></body></html>", "charts.html")
    assert no_nl.find('class="mw-ad"') < no_nl.find("<footer")


def test_研究と決まりのページには入れない():
    page = "<html><body><footer>f</footer></body></html>"
    for name in ("track-record.html", "research-list.html", "about.html", "contact.html", "privacy.html", "index.html"):
        assert IA.add_page_ad(page, name) == page, name
