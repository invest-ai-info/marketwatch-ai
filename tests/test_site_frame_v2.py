# -*- coding: utf-8 -*-
"""記事の新しい枠（apply_site_frame.py の FRAME_V2＝段階2）のテスト。2026-11-05 新設。

固定すること:
  ・スイッチ（環境変数 FRAME_V2=1）が無ければ今の枠のまま（今の関数をそのまま順にかけた結果と同じ・
    今の記事は1バイトも変わらない）
  ・オンなら新しいヘッダー・ナビ・<style> が1つずつ、ナビはヘッダーの直後。もう一度かけても変わらない
  ・オフに戻すと前の形に戻る（新しい形の跡が残らない）。もう一度オンにすると同じ結果
  ・記事の表紙（h1 入りの <header>）・免責の数と文面には触らない
  ・ナビのリンク先がある。ロゴとナビの並びはトップ（build_home_v2）と同じ物で、トップの出力は変わらない

実行:  python -m pytest -q tests/test_site_frame_v2.py
"""
import os
import re
import sys
import warnings
from datetime import datetime

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import apply_site_frame as F  # noqa: E402

with warnings.catch_warnings():
    warnings.simplefilter("ignore", SyntaxWarning)   # build_html の中の JS の正規表現（もとからある）
    import generate_market_news as M  # noqa: E402

K = 'data-disclaimer="kinsho-v1"'
V2_MARKS = ("data-v2", "mwf-v2", "data-mw-frame-v2", "mwf-hd-in", "mwf-logo")

# 時期とレーンで形が違う記事をまねた小さなページ（ヘッダーに 🌙 が入っている・ナビが <main> の中で絵文字つき10ボタン未満）
OLD_PAGE = """<!DOCTYPE html>
<html lang="ja"><head><meta charset="UTF-8"><title>題名 | MarketWatch AI</title>
<style>header{padding:24px 32px}.nav-btn{min-width:170px}</style>
</head>
<body>
<header>
  <div class="header-inner"><div class="header-title">MarketWatch AI</div>
  <button id="theme-toggle" onclick="toggleTheme()" style="position:absolute">🌙</button></div>
</header>
<main>
  <!-- ナビバー -->
  <nav class="nav-bar">
    <a class="nav-btn" href="index.html">🏠 トップ</a>
    <a class="nav-btn current" href="guides.html">📚 解説記事</a>
  </nav>
  <div class="breadcrumb"><a href="index.html">トップ</a> &gt; 記事</div>
  <article class="article">
    <div class="disclaimer-banner" data-disclaimer="kinsho-v1">⚠️ 上部の免責の文。</div>
    <h1>記事の題名</h1>
    <p>本文。</p>
    <div class="disclaimer" data-disclaimer="kinsho-v1">本文末の免責の文。</div>
  </article>
</main>
<footer><p data-disclaimer="kinsho-v1">フッターの免責の文。</p></footer>
<script src="site-search.js" defer></script>
</body></html>
"""
# 研究日誌の形（サイトのヘッダーの後ろに、h1 入りの表紙の <header> があり、免責は h1 の後ろ）
COVER = """<header class="s-hero">
  <div class="s-hero-inner"><span class="s-tag">研究日誌</span><h1>表紙の題名</h1></div>
</header>"""
LAB_PAGE = OLD_PAGE.replace('<main>\n', COVER + "\n<main>\n", 1).replace(
    '    <div class="disclaimer-banner" data-disclaimer="kinsho-v1">⚠️ 上部の免責の文。</div>\n    <h1>記事の題名</h1>\n',
    "", 1).replace('<main>\n', '<main>\n  <div class="disclaimer-banner" data-disclaimer="kinsho-v1">⚠️ 上部の免責の文。</div>\n', 1)
NAME = "guide-sample.html"
REAL = ["guide-nisa.html", "guide-nikkei-vs-topix.html"]


def _on(text, name=NAME):
    return F.process(text, name, True)[0]


def _off(text, name=NAME):
    return F.process(text, name, False)[0]


def _disclaimers(text):
    """免責の要素（開きタグから閉じタグまで）を順に。文面ごと比べる"""
    return re.findall(r"<(div|p)\b[^>]*" + re.escape(K) + r"[^>]*>.*?</\1>", text, re.S)


def _real(name):
    p = os.path.join(ROOT, name)
    if not os.path.exists(p):
        pytest.skip(f"{name} が無い")
    return open(p, encoding="utf-8").read()


# ── スイッチ ──
def test_switch_is_off_unless_frame_v2_is_1(monkeypatch):
    monkeypatch.delenv("FRAME_V2", raising=False)
    assert not F.frame_v2_enabled()
    assert F.process(OLD_PAGE, NAME) == F.process(OLD_PAGE, NAME, False)
    for v in ("0", "", "true", "yes", "2"):
        monkeypatch.setenv("FRAME_V2", v)
        assert not F.frame_v2_enabled(), v
    monkeypatch.setenv("FRAME_V2", "1")
    assert F.frame_v2_enabled()
    assert F.process(OLD_PAGE, NAME) == F.process(OLD_PAGE, NAME, True)


# ── オフ＝今と同じ ──
def test_off_is_the_v1_chain_exactly():
    """オフの結果＝今の関数（rename_site → apply_style → apply_subbrand → apply_header → apply_nav）を順にかけた結果"""
    for page in (OLD_PAGE, LAB_PAGE, OLD_PAGE.replace("</head>", "", 1)):
        t = F.apply_subbrand(F.apply_style(F.rename_site(page)))
        t = F.apply_header(t, NAME)[0]
        t = F.apply_nav(t, NAME)[0]
        out = _off(page)
        assert out == t
        assert not any(m in out for m in V2_MARKS)
        assert any(F.is_std_header(m.group(0)) for m in F._HEADER_RE.finditer(out))
        assert F.build_nav("  ") in out          # ナビはもとの場所（<main> の中）のまま


def test_off_keeps_real_articles_byte_for_byte():
    for name in REAL:
        text = _real(name)
        assert F.process(text, name, False) == (text, []), name


def test_on_leaves_non_guide_pages_as_off():
    text = _real("guides.html")
    assert F.process(text, "guides.html", True) == F.process(text, "guides.html", False)


# ── オン＝新しいヘッダーとナビが1つずつ ──
def test_on_has_one_new_header_nav_and_style():
    for page, name in [(OLD_PAGE, NAME), (LAB_PAGE, NAME)] + [(_real(n), n) for n in REAL]:
        out = _on(page, name)
        assert out.count("<header data-mw-frame data-v2>") == 1, name
        assert out.count('<nav class="nav-bar mwf-nav mwf-v2"') == 1, name
        assert out.count("<style data-mw-frame-v2>") == 1 and out.count("<style data-mw-frame>") == 1, name
        assert F.FRAME_STYLE_TAG + F.FRAME_V2_STYLE_TAG in out, name           # 今の枠の <style> の直後
        assert F.build_header_v2() + "\n" + F.build_nav_v2() in out, name     # ナビはヘッダーの直後
        assert '<nav class="nav-bar mwf-nav">' not in out and 'class="nav-bar">' not in out, name
        assert F.TAGLINE not in out.split("</header>", 1)[0], name             # 2段目・サイト説明・区分名は出さない
        assert F.SUBBRAND_HTML not in out and F.SEC_OPEN not in out, name


def test_new_header_is_logo_and_name_linking_home():
    h = F.build_header_v2()
    assert f'<a class="mwf-logo" href="index.html">{F.LOGO_V2_SVG}{F.SITE_NAME}</a>' in h
    assert h.count("<a ") == 1 and "<h1" not in h and "<nav" not in h and "<button" not in h


def test_theme_button_inside_old_header_is_kept_floating():
    out = _on(OLD_PAGE)
    btn = re.search(r'<button[^>]*id="theme-toggle"[^>]*>', out).group(0)
    assert out.count('id="theme-toggle"') == 1 and "position:fixed" in btn and 'onclick="toggleTheme()"' in btn
    assert out.index('id="theme-toggle"') < out.index("<header data-mw-frame data-v2>")
    assert 'src="site-search.js"' in out


def test_page_without_nav_gets_one_and_page_without_body_is_safe():
    no_nav = F._NAV_RE.sub("", OLD_PAGE, count=1)
    out, notes = F.process(no_nav, NAME, True)
    assert "nav:insert" in notes and out.count('<nav class="nav-bar mwf-nav mwf-v2"') == 1
    bare = '<style>x{}</style>\n<main><nav class="nav-bar"><a class="nav-btn" href="index.html">t</a></nav><h1>題</h1></main>'
    out = _on(bare)
    assert out.count('<nav class="nav-bar mwf-nav mwf-v2"') == 1 and out == _on(out)


# ── 冪等・戻せる ──
def test_on_twice_changes_nothing():
    for page, name in [(OLD_PAGE, NAME), (LAB_PAGE, NAME)] + [(_real(n), n) for n in REAL]:
        once = _on(page, name)
        assert F.process(once, name, True) == (once, []), name


def test_back_to_the_old_frame_and_on_again():
    for page, name in [(OLD_PAGE, NAME), (LAB_PAGE, NAME)] + [(_real(n), n) for n in REAL]:
        on = _on(page, name)
        back, notes = F.process(on, name, False)
        assert "style:v2-removed" in notes and "header:replace" in notes and "nav:replace" in notes
        assert not any(m in back for m in V2_MARKS), name
        assert any(F.is_std_header(m.group(0)) for m in F._HEADER_RE.finditer(back)), name
        assert F.build_nav("") in back, name                       # ヘッダーの直後に前の形のナビ（body>nav の CSS がある）
        assert F.process(back, name, False) == (back, []), name    # 戻した形も冪等
        assert _on(back, name) == on, name                         # もう一度オンにすると同じ


# ── 触らないもの ──
def test_cover_header_with_h1_is_untouched():
    out = _on(LAB_PAGE)
    assert COVER in out and out.count("<h1") == 1
    assert out.index("<header data-mw-frame data-v2>") < out.index(COVER)
    assert _off(out).count(COVER) == 1


def test_disclaimers_keep_number_and_text():
    for page, name in [(OLD_PAGE, NAME), (LAB_PAGE, NAME)] + [(_real(n), n) for n in REAL]:
        on = _on(page, name)
        assert on.count(K) == page.count(K) and on.count("kinsho-v1") == page.count("kinsho-v1"), name
        assert _disclaimers(on) == _disclaimers(page), name
        assert _off(on, name).count(K) == page.count(K), name
    # 免責を文字で数える検査が CSS の分まで数えないように、枠の部品に「kinsho」の文字を入れない
    assert "kinsho" not in F.FRAME_V2_STYLE_TAG + F.build_nav_v2() + F.build_header_v2()


def test_new_css_stays_inside_the_frame():
    """新しい枠の CSS は、枠の要素と「h1 より前の免責」だけに当たる（記事の本文の CSS を壊さない）"""
    ok = (F._HV, F._NV, "body.dark " + F._HV, "body.dark " + F._NV, F._DTV, "body.dark " + F._DTV)
    css = re.sub(r"@media\([^)]*\)\{", "", F.FRAME_V2_CSS + F.FRAME_V2_DISCLAIMER_CSS)
    sels = re.findall(r"(?:^|\})([^{}]+)\{", css)
    assert len(sels) > 20
    for group in sels:
        parts, depth, cur = [], 0, ""
        for ch in group:                  # :is(…,…)・:has(…,…) の中のカンマでは分けない
            depth += (ch == "(") - (ch == ")")
            if ch == "," and depth == 0:
                parts.append(cur)
                cur = ""
            else:
                cur += ch
        parts.append(cur)
        for s in parts:
            assert s.strip().startswith(ok), s


def test_top_disclaimer_rule_is_small_and_not_hidden():
    rule = F.FRAME_V2_DISCLAIMER_CSS
    assert "font-size:.78rem!important" in rule and "background:#f5f8fc!important" in rule
    for bad in ("display:none", "visibility:hidden", "opacity:0", "height:0"):
        assert bad not in rule


# ── ナビ ──
def test_nav_links_point_at_real_files_and_mark_current():
    nav = F.build_nav_v2()
    hrefs = re.findall(r'href="([^"]+)"', nav)
    assert hrefs == [h for h, _ in F.NAV_V2 + F.NAV_V2_MORE]
    for h in hrefs:
        assert os.path.exists(os.path.join(ROOT, h.split("#")[0])), h
    assert nav.count("nav-btn current") == 1 and '<a class="nav-btn current" href="guides.html" aria-current="page">解説記事</a>' in nav
    books = F.build_nav_v2(F.SELF_CURRENT["guide-investment-books.html"])
    assert '<li><a class="nav-btn current" href="guide-investment-books.html" aria-current="page">投資本</a></li>' in books
    assert F.process(OLD_PAGE, "guide-investment-books.html", True)[0].count('aria-current="page"') == 1
    emoji = re.compile("[\U0001F300-\U0001FAFF☀-➿]")
    assert not any(emoji.search(t) for _, t in F.NAV_V2 + F.NAV_V2_MORE)
    assert '<details class="mwf-more"><summary>もっと見る ▾</summary>' in nav


def test_nav_is_found_by_the_site_checks():
    """class に nav-bar mwf-nav（apply_nav の見つけ方）・リンクは nav-btn（check_site_consistency の NAV_LINKS の数え方）"""
    nav = F.build_nav_v2()
    opening = nav[:nav.find(">") + 1]
    assert re.search(r'class="(?:[^"]*\s)?nav-bar[\s"]', opening) and "mwf-nav" in opening
    found = set(re.findall(r'class="nav-btn[^"]*"\s+href="([^"]+)"', nav))
    nav_links = ["index.html", "political-feed.html", "track-record.html", "calendar.html",
                 "guides.html", "guide-investment-books.html", "holdings.html",
                 "market-health.html", "hot-assets.html", "charts.html", "youtube-summary.html"]
    assert [x for x in nav_links if x not in found] == []
    src = open(os.path.join(ROOT, "check_site_consistency.py"), encoding="utf-8").read()
    for x in nav_links:                      # 上の11件は検査の側の NAV_LINKS と同じ
        assert f'"{x}"' in src, x


# ── トップと同じ物・トップの出力は変わらない ──
@pytest.fixture
def offline(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(M, "get_price", lambda s: (16.6, 16.0, 3.75))
    monkeypatch.setattr(M, "fetch_spark_closes", lambda sym, n=5: [1.0, 2.0, 1.5])
    monkeypatch.setattr(M, "fetch_currency_strength",
                        lambda: {"USD": -0.24, "EUR": 0.04, "GBP": 0.06, "JPY": -0.14, "AUD": 0.31})
    return M


# リファクタ（ナビの並びとロゴを apply_site_frame へ移した）の前に build_home_v2 が出していた見出しの部分（2026-11-05）。
# トップのナビやロゴをわざと変えるときは、ここも一緒に直す
HOME_HEADER_BEFORE = (
    '<header class="hd" data-v2="header">\n'
    '  <div class="wrap">\n'
    '    <div class="hd-in">\n'
    '      <a class="logo" href="index.html"><svg viewBox="0 0 32 32" aria-hidden="true"><rect width="32" height="32" rx="8" '
    'fill="var(--brand)"/><path d="M6.5 22.5l6-6.5 4.5 3.5 8.5-9.5" fill="none" stroke="var(--bg)" stroke-width="2.6" '
    'stroke-linecap="round" stroke-linejoin="round"/><circle cx="25.5" cy="10" r="2.3" fill="var(--bg)"/></svg>時短投資ラボ</a>\n'
    '      <span class="hd-sp"></span>\n'
    '      <button class="icon-btn" type="button" id="v2-search" aria-label="記事を検索" title="記事を検索（/ または Ctrl+K）">'
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="11" cy="11" r="7"/>'
    '<path d="M20 20l-3.5-3.5"/></svg></button>\n'
    '      <button class="icon-btn" type="button" id="theme-toggle" aria-label="明るい表示と暗い表示の切り替え" aria-pressed="false">🌙</button>\n'
    '    </div>\n'
    '    <div class="nav-row" data-v2="nav">\n'
    '      <nav class="nav" aria-label="メイン"><a class="cur" aria-current="page" href="index.html">ホーム</a>'
    '<a href="guide-how-we-research.html">はじめての方へ</a><a href="guides.html">解説記事</a><a href="track-record.html">検証の結果</a>'
    '<a href="market-health.html">市場データ</a><a href="calendar.html">経済カレンダー</a></nav>\n'
    '      <details class="nav-more"><summary>もっと見る ▾</summary><ul><li><a href="political-feed.html">政治発言ライブ</a></li>'
    '<li><a href="hot-assets.html">出来高急増</a></li><li><a href="charts.html">150年チャート</a></li>'
    '<li><a href="holdings.html">大量保有報告</a></li><li><a href="guide-investment-books.html">投資本</a></li>'
    '<li><a href="youtube-summary.html">YouTube要約</a></li><li><a href="research-list.html">検証中リスト</a></li>'
    '<li><a href="guides.html#cat-tools">計算ツール</a></li></ul></details>\n'
    '    </div>\n'
    '  </div>\n'
    '</header>')


def test_home_uses_the_same_logo_and_nav_objects():
    assert M.HOME_V2_NAV is F.NAV_V2 and M.HOME_V2_MORE is F.NAV_V2_MORE and M._V2_LOGO is F.LOGO_V2_SVG


def test_home_v2_output_is_unchanged_by_the_refactor(offline):
    now = datetime(2026, 11, 5, 12, 47, tzinfo=M.JST)
    data = {k: (1000.0 + i, 990.0, 0.5 * (i - 3)) for i, (k, *_r) in enumerate(M.BAND_ITEMS)}
    h = M.build_home_v2(data, {}, now, None)
    i = h.index('<header class="hd"')
    assert h[i:h.index("</header>", i) + len("</header>")] == HOME_HEADER_BEFORE
    assert h.count(F.FRAME_STYLE_TAG) == 1 and "data-mw-frame-v2" not in h   # トップには新しい記事の枠の CSS は入らない


def test_frame_colors_are_the_home_colors():
    def toks(block):
        return dict(re.findall(r"--([\w-]+):([^;}\s]+)", block))
    root = toks(re.search(r":root\{([^}]*)\}", M.HOME_V2_CSS).group(1))
    dark = toks(re.search(r"body\.dark\{([^}]*)\}", M.HOME_V2_CSS).group(1))
    for k, v in F.V2_LIGHT:
        assert root[k] == v, k
    for k, v in F.V2_DARK:
        assert dark[k] == v, k


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
