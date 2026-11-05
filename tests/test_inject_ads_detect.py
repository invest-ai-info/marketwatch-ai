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
