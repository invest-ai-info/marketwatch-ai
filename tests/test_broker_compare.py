# -*- coding: utf-8 -*-
"""証券会社の比較ページが本文の約束を守っているかを確かめる。"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import inject_ads  # noqa: E402

PAGE = "guide-broker-compare.html"
HTML = (ROOT / PAGE).read_text(encoding="utf-8")
# 五十音順＝本文の「社名の並びは五十音順」の約束
ORDER = ["SMBC日興証券", "SBI証券", "DMM株", "松井証券", "マネックス証券", "三菱UFJ eスマート証券", "楽天証券"]


def table_body(table_id):
    return re.search(rf'id="{table_id}".*?<tbody>(.*?)</tbody>', HTML, re.S).group(1)


def test_page_is_excluded_from_auto_ads():
    # 毎回の update-market-news の inject_ads --all で広告が差し込まれると本文の約束が崩れる
    assert PAGE in inject_ads.DENY_EXACT


def test_page_has_no_affiliate_links():
    # サイト共通の枠に .mw-ad の CSS があるので、広告枠そのもの（class 属性）だけを見る
    for word in ("a8.net", 'class="mw-ad', 'rel="sponsored', "mw-ads.js", "adsbygoogle"):
        assert word not in HTML


def test_advertisers_are_disclosed():
    # 別のページの広告主を増やしたら、本文の開示も直す
    for creative in inject_ads.CREATIVES.values():
        assert creative["alt"].replace("株式会社", "") in HTML


def test_no_ranking_words():
    for word in ("おすすめ1位", "ランキング", "一択", "最強"):
        assert word not in HTML


def test_compare_table_keeps_alphabetical_order():
    rows = re.findall(r'data-label="証券会社"><a [^>]*>([^<]+)</a>', table_body("bc-table"))
    assert rows == ORDER


def test_every_filter_has_a_matching_row():
    tags = set()
    for tag_list in re.findall(r'data-tags="([^"]+)"', HTML):
        tags |= set(tag_list.split())
    values = set(re.findall(r'<input type="checkbox" value="(\w+)"', HTML))
    assert values == tags


def test_checked_date_matches_script():
    script = re.search(r"var CHECKED = '(\d{4})-(\d{2})-(\d{2})'", HTML)
    year, month, day = (int(x) for x in script.groups())
    assert f'id="bc-checked">{year}年{month}月{day}日<' in HTML


def test_disclaimer_marker_present():
    assert HTML.count('data-disclaimer="kinsho-v1"') >= 3


def test_browser_translation_is_off():
    # 自動翻訳で金融の言葉が別の意味に化けると誤解を招く（2026-11-06「食べる前に考えること」）
    assert '<html lang="ja" translate="no">' in HTML
    assert '<meta name="google" content="notranslate">' in HTML
