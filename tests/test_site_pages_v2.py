# -*- coding: utf-8 -*-
"""トップ以外のページをトップの見た目にする（apply_site_frame.py の段階3＝V2_PAGES・SKIN_V2）のテスト。2026-11-15 新設。

固定すること:
  ・スイッチ（PAGES_V2_ON・環境変数 PAGES_V2=0/1）。オフなら生成スクリプトが作ったばかりの前の形のページは1バイトも変わらない
  ・オンなら新しいヘッダー・ナビ（今いるページが光る）・<style> が1つずつ。ナビはヘッダーの直後。もう一度かけても変わらない
  ・前のヘッダーのページ名と最終更新は、h1 の無いページだけナビの下の帯（h1）へ移る。h1 のあるページに2つ目の h1 を作らない
  ・オフに戻すと、新しい形になった静的ページは前の形（前のヘッダー・11ボタンのナビ）に戻る
  ・免責の数と文面・本文には触らない。トップ（index.html）は変えない
  ・共通の見た目の CSS は要素か決まったクラスだけを選ぶ（ページの部品の色を上書きしない）。色はトップと同じ値
  ・暗い表示を持たないページでは、ヘッダーとナビも明るいまま（前と同じ見え方）
  ・生成スクリプトはどれも書き出す前に finish_page を通す

実行:  python -m pytest -q tests/test_site_pages_v2.py
"""
import os
import re
import sys
import warnings

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import apply_site_frame as F  # noqa: E402

with warnings.catch_warnings():
    warnings.simplefilter("ignore", SyntaxWarning)
    import generate_market_news as M  # noqa: E402

K = 'data-disclaimer="kinsho-v1"'


def _cal_page():
    """生成スクリプト（brand_header）が作る形の、h1 の無いページ（カレンダーの形）"""
    head = M.brand_header("📅", "マクロ経済カレンダー", "2026年11月15日 12:13 JST")
    return ("<!DOCTYPE html>\n<html lang=\"ja\"><head><meta charset=\"UTF-8\"><title>t</title>\n"
            "<style>*{margin:0;padding:0;box-sizing:border-box}body{color:#1f2328}h2{color:#2C4F8F}</style>\n"
            f"{F.FRAME_STYLE_TAG}\n</head>\n<body>\n{head}\n"
            '<button id="theme-toggle" onclick="toggleTheme()" style="position:fixed">🌙</button>\n'
            f"{F.build_nav('  ', 'calendar.html')}\n"
            "<main>\n  <h2>📆 2026年11月</h2>\n  <p>本文。</p>\n</main>\n"
            f"<footer><p {K}>フッターの免責の文。</p></footer>\n</body></html>\n")


def _h1_page():
    """h1 が本文にあるページ（解説記事の一覧の形）"""
    return _cal_page().replace("<h2>📆 2026年11月</h2>", '<div class="page-header"><h1>📚 一覧</h1></div>', 1)


def _on(text, name="calendar.html"):
    return F.process(text, name, True, True)[0]


def _off(text, name="calendar.html"):
    return F.process(text, name, True, False)[0]


def _markup(text):
    """<style> の中（枠の CSS が持つクラス名）を除いた、ページの要素だけ"""
    return re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.S)


def _real(name):
    p = os.path.join(ROOT, name)
    if not os.path.exists(p):
        pytest.skip(f"{name} が無い")
    return open(p, encoding="utf-8").read()


# ── スイッチ ──
def test_switch(monkeypatch):
    monkeypatch.delenv("PAGES_V2", raising=False)
    assert F.pages_v2_enabled() is F.PAGES_V2_ON
    monkeypatch.setenv("PAGES_V2", "0")
    assert not F.pages_v2_enabled()
    monkeypatch.setenv("PAGES_V2", "1")
    assert F.pages_v2_enabled()
    for v in ("", "yes", "2"):
        monkeypatch.setenv("PAGES_V2", v)
        assert F.pages_v2_enabled() is F.PAGES_V2_ON


def test_off_leaves_a_freshly_generated_page_byte_for_byte():
    for page in (_cal_page(), _h1_page()):
        assert F.process(page, "calendar.html", True, False) == (page, [])


def test_frame_v2_switch_does_not_decide_pages():
    for v2 in (True, False):
        assert F.process(_cal_page(), "calendar.html", v2, True)[0] == _on(_cal_page())


# ── オン＝新しい形 ──
def test_on_has_one_new_header_nav_style_and_band():
    out = _on(_cal_page())
    head, nav = F.build_header_v2(), F.build_nav_v2("calendar.html")
    assert out.count(head) == 1 and out.count(nav) == 1
    assert out.index(nav) == out.index(head) + len(head) + 1          # ナビはヘッダーの直後
    assert out.count("<style data-mw-frame-v2>") == 1 and out.count("<style data-mw-skin-v2>") == 1
    assert "header-title" not in _markup(out) and "mw-subbrand" not in _markup(out)   # 前のヘッダーは残らない
    band = F.build_page_title_v2("📅 マクロ経済カレンダー", "🕒 最終更新: 2026年11月15日 12:13 JST")
    assert out.count(band) == 1 and out.index(band) == out.index(nav) + len(nav) + 1
    assert out.count("<h1") == 1
    assert 'id="theme-toggle"' in out                                  # 🌙 は残る
    assert '<a class="nav-btn current" href="calendar.html" aria-current="page">経済カレンダー</a>' in out


def test_on_twice_changes_nothing():
    for page in (_cal_page(), _h1_page()):
        once = _on(page)
        assert F.process(once, "calendar.html", True, True) == (once, [])


def test_page_with_its_own_h1_gets_no_band():
    out = _on(_h1_page(), "guides.html")
    assert "mwf-ptitle" not in _markup(out) and out.count("<h1") == 1
    assert out.count('aria-current="page"') == 1 and 'href="guides.html" aria-current="page"' in out


def test_current_item_by_page():
    assert set(F.V2_PAGES) >= {"calendar.html", "charts.html", "vix.html", "market-health.html", "hot-assets.html",
                               "preview.html", "track-record.html", "research-list.html", "youtube-summary.html",
                               "political-feed.html"} | set(F.STATIC_PAGES)
    hrefs = {h for h, _ in F.NAV_V2 + F.NAV_V2_MORE}
    for name, cur in F.V2_PAGES.items():
        assert cur is None or cur in hrefs, name
        out = _on(_h1_page(), name)
        assert out.count('aria-current="page"') == (0 if cur is None else 1), name


def test_top_page_is_not_touched():
    assert "index.html" not in F.V2_PAGES
    page = _cal_page()
    assert F.finish_page(page, "index.html") is page
    assert F.finish_page(page, "guide-x.html") is page


def test_disclaimers_and_body_are_kept():
    for page in (_cal_page(), _h1_page()):
        out = _on(page)
        assert out.count(K) == page.count(K)
        assert "<p>本文。</p>" in out


# ── オフに戻す ──
def test_back_to_the_old_frame_and_on_again():
    for name in ("guides.html", "about.html", "holdings.html"):
        on = _on(_h1_page(), name)
        off = _off(on, name)
        assert not any(m in off for m in ("data-v2", "mwf-v2", "data-mw-frame-v2", "data-mw-skin-v2", "data-mw-font"))
        assert "header-title" in off and 'class="nav-bar mwf-nav"' in off
        assert F.process(off, name, True, False) == (off, [])
        assert _on(off, name) == on
    assert "📚 解説記事" in _off(_on(_h1_page(), "guides.html"), "guides.html")


def test_band_is_removed_when_off():
    # 生成ページは生成スクリプトが毎回前の形で作り直すので、ここでは帯と新しい形の跡が残らないことだけ見る
    off = _off(_on(_cal_page()))
    assert not any(m in _markup(off) for m in ("mwf-ptitle", "data-v2", "mwf-v2"))


# ── 共通の見た目 ──
_ALLOWED = {"body", "main", "h1", "h2", "a", "footer", ".breadcrumb", ".article", ".doc-card", ".page-header",
            ".page-desc", "html", ".mw-newsletter", ".ml-form-embedWrapper", ".mw-nl-badge", ".ml-form-embedContent",
            "h4", "p", ".ml-form-fieldRow", "input", ".ml-form-embedSubmit", "button", "body.dark"}


def _selectors(css):
    css = re.sub(r"@media\([^)]*\)\{", "", css)
    out = []
    for group in re.findall(r"(?:^|\})([^{}]+)\{", css):
        out += [s.strip() for s in group.split(",")]
    return out


def test_skin_selects_elements_and_known_boxes_only():
    """クラスで色を決めているページの部品（カード・表・ボタン）を上書きしない＝選ぶのは要素か決まった箱だけ"""
    for sel in _selectors(F.SKIN_V2_CSS + F.SKIN_V2_DARK_CSS):
        for part in re.split(r"\s+", sel.replace(":hover", "")):
            assert part in _ALLOWED, (sel, part)
    frame = (F._HV, F._NV, F._PT, "body.dark " + F._HV, "body.dark " + F._NV, "body.dark " + F._PT)
    for sel in _selectors(F.PAGE_TITLE_V2_CSS + F.PAGE_TITLE_V2_DARK_CSS + F.LIGHT_LOCK_CSS):
        assert sel.startswith(frame), sel
    assert "!important" not in F.SKIN_V2_CSS + F.SKIN_V2_DARK_CSS     # ページ側の強い指定（!important）には勝たない
    assert "kinsho" not in F.SKIN_V2_STYLE_TAG + F.SKIN_V2_LIGHT_STYLE_TAG


def test_skin_colors_are_the_home_colors():
    def toks(block):
        return dict(re.findall(r"--([\w-]+):([^;}\s]+)", block))
    root = toks(re.search(r":root\{([^}]*)\}", M.HOME_V2_CSS).group(1))
    dark = toks(re.search(r"body\.dark\{([^}]*)\}", M.HOME_V2_CSS).group(1))
    for k, v in F._SK.items():
        assert root[k] == v, k
    for k, v in F._SKD.items():
        assert dark[k] == v, k
    assert root["t-teal"] == F._SK_T_TEAL


def test_dark_follows_the_page():
    """暗い表示を持つページは暗い色つき、持たないページは page_palette が暗い表示を足す（2026-11-21〜）。
    page_palette のスイッチがオフなら前のとおりヘッダーとナビも明るいまま"""
    import page_palette
    plain = _on(_cal_page())
    assert not F.has_own_dark(plain) and F.SKIN_V2_STYLE_TAG in plain and "<style data-mw-palette>" in plain
    old = page_palette.ON
    try:
        page_palette.ON = False
        plain = _on(_cal_page())
        assert F.SKIN_V2_LIGHT_STYLE_TAG in plain and F.LIGHT_LOCK_CSS in plain and "data-mw-palette" not in plain
    finally:
        page_palette.ON = old
    rules = "".join(f"body.dark .c{i}{{color:#fff}}" for i in range(F._OWN_DARK_MIN))
    dark = _on(_cal_page().replace("h2{color:#2C4F8F}", "h2{color:#2C4F8F}" + rules, 1))
    assert F.has_own_dark(dark) and F.SKIN_V2_STYLE_TAG in dark and F.LIGHT_LOCK_CSS not in dark
    # 広告・メルマガ・🌙 の部品の暗い指定は数えない
    widget = "".join(f"body.dark .mw-ad .x{i}{{color:#fff}}" for i in range(20))
    assert not F.has_own_dark("<style>" + widget + "</style>")


def test_articles_get_the_skin_only_on_the_standard_template():
    std = "<html><head><style>h1{font-size:1.95rem;color:#1E3A6E;margin-bottom:8px}</style>" + F.FRAME_STYLE_TAG + \
          "</head><body><main><article class=\"article\"><h1>t</h1></article></main></body></html>"
    own = std.replace("h1{font-size:1.95rem;color:#1E3A6E;margin-bottom:8px}", "h1{color:var(--c-ink)}")
    assert "data-mw-skin-v2" in F.process(std, "guide-x.html", True, True)[0]
    assert "data-mw-skin-v2" not in F.process(own, "guide-x.html", True, True)[0]
    assert "data-mw-skin-v2" not in F.process(std, "guide-x.html", False, True)[0]


# ── 本物のページ ──
@pytest.mark.parametrize("name", F.STATIC_PAGES)
def test_live_static_pages_are_stable(name):
    """公開中の静的ページは本番の設定でもう一度かけても1バイトも変わらない（毎回の --all で揺れない）"""
    text = _real(name)
    assert F.process(text, name, True) == (text, []), name


def test_generators_pass_pages_through_finish_page():
    for src, needle in [("generate_market_news.py", "content = finish_page(content, os.path.basename(path))"),
                        ("generate_track_record_page.py", "finish_page(build_html(signals, tracker), OUTPUT_FILE)"),
                        ("generate_youtube_summary.py", "finish_page(add_page_ad(build_html(combined)"),
                        ("build_political_feed_page.py", "finish_page(add_page_ad(build_html(items)"),
                        ("research_map.py", "F.finish_page(build_list_page(root=root)")]:
        assert needle in open(os.path.join(ROOT, src), encoding="utf-8").read(), src


def test_market_page_generator_output_is_new(tmp_path):
    from datetime import datetime
    now = datetime(2026, 11, 15, 12, 0, tzinfo=M.JST)
    p = tmp_path / "calendar.html"
    assert M.safe_write(str(p), M.build_calendar_html(now))
    out = p.read_text(encoding="utf-8")
    assert out.count(F.build_header_v2()) == 1 and out.count(F.build_nav_v2("calendar.html")) == 1
    assert out.count('<div class="mwf-ptitle" data-v2>') == 1 and "マクロ経済カレンダー</h1>" in out
    assert F.finish_page(out, "calendar.html") == out


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
