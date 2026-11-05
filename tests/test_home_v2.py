# -*- coding: utf-8 -*-
"""新しいトップ（build_home_v2・環境変数 HOME_V2=1 のときだけ使う）のテスト。2026-11-05 新設。

第1段階＝本番の index.html は今の build_html のまま。スイッチを入れたときだけ新しい版になる。
ネットワークには出ない（値段・VIX・通貨の強弱は差し替える）。

実行:  python -m pytest -q tests/test_home_v2.py
"""
import html
import inspect
import json
import os
import re
import sys
import unicodedata
import warnings
from datetime import datetime

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
with warnings.catch_warnings():
    warnings.simplefilter("ignore", SyntaxWarning)   # build_html の中の JS の正規表現（もとからある）
    import generate_market_news as M  # noqa: E402

NOW = datetime(2026, 11, 5, 12, 47, tzinfo=M.JST)
SECTIONS = ["header", "nav", "hero", "points", "schedule", "prices", "new", "picks", "ad",
            "markets", "headlines", "newsletter", "footer"]
BANNED = ["必ず", "絶対", "確実", "おすすめ", "一択"]


@pytest.fixture
def offline(monkeypatch):
    """ネットワークに出る部品を差し替える（AI の見立ては GEMINI_API_KEY が無ければ空）。"""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(M, "get_price", lambda s: (16.6, 16.0, 3.75))
    monkeypatch.setattr(M, "fetch_spark_closes", lambda sym, n=5: [1.0, 2.0, 1.5])
    monkeypatch.setattr(M, "fetch_currency_strength",
                        lambda: {"USD": -0.24, "EUR": 0.04, "GBP": 0.06, "JPY": -0.14, "AUD": 0.31})
    return M


def _data(**over):
    d = {k: (1000.0 + i, 990.0, 0.5 * (i - 3)) for i, (k, *_r) in enumerate(M.BAND_ITEMS)}
    d.update(over)
    return d


def _page(**over):
    return M.build_home_v2(_data(**over), {}, NOW, None)


def _boom(*a, **k):
    raise RuntimeError("壊れた")


# ── スイッチ ──
def test_switch_off_uses_build_html(monkeypatch):
    monkeypatch.delenv("HOME_V2", raising=False)
    assert M._index_builder() is M.build_html
    for v in ("0", "", "true", "yes", "2"):
        monkeypatch.setenv("HOME_V2", v)
        assert M._index_builder() is M.build_html, v
    monkeypatch.setenv("HOME_V2", "1")
    assert M._index_builder() is M.build_home_v2


def test_main_writes_index_through_the_switch():
    src = inspect.getsource(M.main)
    assert "index_content = _index_builder()(data, hist, now_jst, news, touraku=touraku_ratio)" in src
    assert not re.search(r"\bbuild_html\(", src)   # main が build_html を直に呼ぶ道は残っていない


# ── 各節が1回ずつ・免責は1つ ──
def test_each_section_once_and_one_disclaimer(offline):
    h = _page()
    for s in SECTIONS:
        assert h.count(f'data-v2="{s}"') == 1, s
    assert h.count('data-disclaimer="kinsho-v1"') == 1
    assert h.count("<header") == 1 and h.count("<footer") == 1 and h.count("<h1") == 1
    assert h.count('id="mlb2-42383897"') == 1        # メルマガの登録フォームは1つ
    assert h.count("data-mw-ads=") == 1               # 広告の枠は1つ
    assert h.count("pagead2.googlesyndication.com") == 1
    hd = h[h.index('data-v2="header"'):h.index("</header>")]
    assert M.SITE_NAME_V2 in hd and 'id="theme-toggle"' in hd and 'id="v2-search"' in hd


def test_removed_parts_are_gone(offline):
    body = _page().split("<body", 1)[1]
    for gone in ("MarketWatch AI でできること", "注目の解説記事", "本日のマーケット",
                 "01_hero_tokyo_market_banner.png", 'class="jump-bar"', "md-title", "rs-band",
                 'data-t="h"', "rk-tab", "📰 更新履歴", M.SITE_TAGLINE, M.SUBBRAND_HTML,
                 "本データは自動取得・表示であり", "※ 当サイトは情報提供を目的としており", 'class="nav-btn'):
        assert gone not in body, gone


def test_head_keeps_seo_ga_adsense_favicon(offline):
    head = _page().split("</head>", 1)[0]
    for s in ("<title>", '<meta name="description"', '<link rel="canonical" href="https://marketwatch-jp.com/">',
              'property="og:title"', "application/ld+json", M.GA4_MEASUREMENT_ID,
              "adsbygoogle.js?client=ca-pub-2552122294306014", 'href="favicon.svg"', "<style data-mw-frame>"):
        assert s in head, s


def test_safe_write_keeps_one_newsletter_and_adds_back_to_top(offline, tmp_path):
    p = tmp_path / "index.html"
    assert M.safe_write(str(p), _page())
    out = p.read_text(encoding="utf-8")
    assert out.count('id="mlb2-42383897"') == 1       # safe_write が2つ目を差し込まない
    assert out.count('id="mw-back-to-top"') == 1
    assert 'action="https://assets.mailerlite.com/jsonp/2419467/forms/189793597614196622/subscribe"' in out
    assert "webforms.min.js" in out and "function ml_webform_success_42383897" in out


def test_health_check_can_read_last_updated(offline):
    pytest.importorskip("requests")
    import check_site_health as H
    got = H.parse_updated_at(_page())
    assert got is not None and (got.year, got.month, got.day, got.hour, got.minute) == (2026, 11, 5, 12, 47)


# ── ナビ・リンク先 ──
def test_nav_links_point_at_real_files(offline):
    h = _page()
    nav = h[h.index('data-v2="nav"'):h.index("</header>")]
    hrefs = re.findall(r'href="([^"]+)"', nav)
    assert hrefs == [x for x, _ in M.HOME_V2_NAV + M.HOME_V2_MORE]
    for href in hrefs:
        assert os.path.exists(href.split("#")[0]), href
    assert "<details" in nav                                       # もっと見るは <details> の一覧
    assert 'id="cat-tools"' in open("guides.html", encoding="utf-8").read()  # 計算ツールの行き先
    emoji = re.compile("[\U0001F300-\U0001FAFF☀-➿]")
    assert not any(emoji.search(t) for _, t in M.HOME_V2_NAV + M.HOME_V2_MORE)


def test_other_local_links_point_at_real_files(offline):
    """新着（記事のファイルは日々増える）以外のリンク先がそろっているか。"""
    h = _page()
    i, j = h.index('data-v2="new"'), h.index('data-v2="picks"')
    rest = h[:i] + h[j:]
    for href in set(re.findall(r'href="([^"#:?]+\.html)(?:#[^"]*)?"', rest)):
        assert os.path.exists(href), href
    assert 'href="about.html#policy">編集方針・訂正の方針' in h


def test_picks_are_six_real_files():
    assert len(M.HOME_V2_PICKS) == 6
    for f, *_ in M.HOME_V2_PICKS:
        assert os.path.exists(f), f


# ── 値動き ──
def test_missing_change_shows_dash(offline):
    t = M._v2_ticker(_data(btc=(80553.0, None, None), gold=(None, None, None)))
    cells = re.findall(r'<div class="n">(.*?)</div><div class="v">(.*?)</div><div class="c ([a-z]*)">(.*?)</div>', t)
    got = {n: (v, cls, c) for n, v, cls, c in cells}
    assert len(cells) == 8 and [n for n, *_ in cells] == [nm for _k, nm, _s, _d in M.BAND_ITEMS]
    assert got["ビットコイン"] == ("80,553", "na", "—")
    assert got["金"] == ("—", "na", "—")
    assert got["日経平均"] == ("1,000", "down", "▼1.50%")
    assert '<div class="c na">—</div>' in _page(btc=(80553.0, None, None))


# ── ① 今日の要点 ──
def test_points_are_three_lines_with_note(offline):
    h = _page()
    card = h[h.index('data-v2="points"'):h.index('data-v2="schedule"')]
    assert card.count("<li>") <= 3
    assert "恐怖指数（VIX）は <b>16.6</b>＝落ち着いた水準" in card
    assert "売買の推奨ではありません" in card
    assert "資産ごとの見立て" not in card          # AI の見立てが無い日は畳みごと出さない


def test_ai_views_are_kept_in_a_closed_details(monkeypatch, offline):
    monkeypatch.setattr(M, "build_ai_analysis_section",
                        lambda **k: '<section class="ai-analysis-section" id="ai">X</section>')
    h = _page()
    assert ('<details class="fold"><summary>資産ごとの見立て（AI）を見る</summary>'
            '<section class="ai-analysis-section" id="ai">X</section></details>') in h


# ── 最初の画面の数字 ──
def test_hero_numbers_are_the_research_band_numbers(offline):
    import research_map
    m = research_map.collect()
    n_journal, _ = M._latest_signal_lab()
    h = _page()
    i = h.index('data-v2="hero"')
    hero = h[i:h.index("</section>", i)]
    band = M.build_research_band()
    for n in (m["n_active"], n_journal, len(m["ended"])):
        assert f"<b>{n}本</b>" in hero and f"<b>{n}本</b>" in band, n


# ── 新着 ──
def test_new_items_are_the_latest_five_of_the_update_history(offline):
    items = M._v2_new_items(NOW)
    assert len(items) == 5
    old = M.build_html(_data(), {}, NOW, None)
    i = old.index("📰 更新履歴")
    hist = old[i:old.index("</details>", i)]
    assert [h for _w, _c, _t, h, _ti in items] == re.findall(r'<a href="([^"]+)"', hist)[1:6]  # 先頭は記事一覧への案内


def test_new_item_labels(monkeypatch):
    rows = [
        {"date": "2026-11-06", "line": '・<b>2026-11-06</b>: 🧪 解説「<a href="guide-signal-lab-141.html" style="color:#0969da"><b>4時間足だけ63.9%で優位？【研究日誌 #141】</b></a>」公開'},
        {"date": "2026-11-05", "line": '・<b>2026-11-05</b>: 🔬 解説「<a href="guide-company-6501-hitachi.html" style="color:#0969da"><b>日立製作所</b></a>」公開'},
        {"date": "2026-11-04", "line": '・<b>2026-11-04</b>: 📰 解説「<a href="guide-news-2026-11-04.html" style="color:#0969da"><b>【11/4】S&P500 が上昇</b></a>」公開'},
        {"date": "2026-11-03", "line": '・<b>2026-11-03</b>: 📚 解説「<a href="guide-nisa.html" style="color:#0969da"><b>新NISA</b></a>」公開'},
    ]
    monkeypatch.setattr(M, "_history_items_from_build_html", lambda: [dict(r) for r in rows])
    monkeypatch.setattr(M, "build_weekly_history_item", lambda now: None)
    got = M._v2_new_items(NOW)
    assert [(w, c, t) for w, c, t, _h, _ti in got] == [
        ("11/6", "res", "研究日誌"), ("11/5", "co", "企業"), ("11/4", "nw", "ニュース"), ("11/3", "", "解説")]
    assert "%" not in got[0][4]                     # トップに成績の数字を出さない（研究の帯と同じ切り方）
    assert got[1][4] == "日立製作所（6501）"
    assert got[2][4] == "【11/4】S&P500 が上昇"     # 出すときに html.escape する


def test_new_items_are_escaped_on_the_page(monkeypatch, offline):
    monkeypatch.setattr(M, "_v2_new_items", lambda now: [("11/4", "nw", "ニュース", "guide-news-x.html", "S&P500 <b>上昇</b>")])
    h = _page()
    assert '<a href="guide-news-x.html">S&amp;P500 &lt;b&gt;上昇&lt;/b&gt;</a>' in h


def test_history_is_read_from_build_html_not_copied():
    items = M._history_items_from_build_html()
    assert len(items) > 50 and all(set(it) == {"date", "line"} for it in items)
    src = open("generate_market_news.py", encoding="utf-8").read()
    assert src.count("    _history_items = [\n") == 1     # publish_article.py が書き足す先は1か所だけ


# ── 日本株と通貨 ──
def test_jp_card_from_rankings_json(tmp_path):
    d = {"asof": "2026-11-04", "universe": 399,
         "gainers": [{"name": f"上{i}", "pct": 0.1 - i / 100, "sector": "機械"} for i in range(5)],
         "losers": [{"name": f"下{i}", "pct": -0.1 + i / 100, "sector": "化学"} for i in range(5)],
         "breadth": {"up": 144, "down": 247, "flat": 8},
         "sectors": [{"sector": "空運業", "n": 2, "avg": 0.04, "up": 2}, {"sector": "陸運業", "n": 13, "avg": 0.013, "up": 7},
                     {"sector": "不動産業", "n": 9, "avg": 0.01, "up": 6}, {"sector": "保険業", "n": 6, "avg": 0.008, "up": 4},
                     {"sector": "電気機器", "n": 50, "avg": -0.01, "up": 10}, {"sector": "ガラス・土石製品", "n": 7, "avg": -0.02, "up": 1},
                     {"sector": "非鉄金属", "n": 8, "avg": -0.03, "up": 0}]}
    p = tmp_path / "jp-rankings.json"
    p.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    card = M._v2_jp_card(str(p))
    assert card.count("<tr>") == 6 and "上0" in card and "上2" in card and "上3" not in card and "下2" in card
    assert "−10.00%" in card and "+10.00%" in card
    assert "値上がり144・値下がり247" in card
    assert "強かった業種＝陸運業・不動産業・保険業／弱かった業種＝非鉄金属・ガラス・土石製品・電気機器" in card
    assert "空運業" not in card                                   # 5銘柄未満の業種は除く（build_sector_panel と同じ）
    assert 'href="hot-assets.html"' in card and "11/4 終値・主な399銘柄" in card
    assert M._v2_jp_card(str(tmp_path / "none.json")) == ""


def test_real_rankings_names_are_shown(offline):
    d = M._load_rankings(M.JP_RANKINGS_PATH)
    if not d:
        pytest.skip("jp-rankings.json が無い")
    card = M._v2_jp_card(M.JP_RANKINGS_PATH)
    for r in d["gainers"][:3] + d["losers"][:3]:
        assert html.escape(unicodedata.normalize("NFKC", r["name"])) in card


def test_fx_card_orders_strong_to_weak():
    card = M._v2_fx_card({"USD": -0.24, "EUR": 0.04, "GBP": None, "JPY": -0.14, "AUD": 0.31})
    order = re.findall(r"<li><span>\S+ (\S+)</span>", card)
    assert order == ["豪ドル", "ユーロ", "円", "米ドル"]
    assert "left:50%;width:50.0%;background:var(--up)" in card and "right:50%;width:38.7%;background:var(--down)" in card
    assert M._v2_fx_card(None) == "" and M._v2_fx_card({"USD": None}) == ""


# ── 壊れたときもページは出る ──
def test_page_survives_missing_data(monkeypatch, offline):
    import research_map
    monkeypatch.setattr(research_map, "collect", _boom)
    monkeypatch.setattr(M, "get_price", _boom)
    monkeypatch.setattr(M, "fetch_currency_strength", lambda: None)
    monkeypatch.setattr(M, "JP_RANKINGS_PATH", os.path.join(ROOT, "no-such-rankings.json"))
    monkeypatch.setattr(M, "build_news_ticker_section", _boom)
    monkeypatch.setattr(M, "_v2_new_items", _boom)
    h = M.build_home_v2({}, {}, NOW, None)
    assert h.rstrip().endswith("</html>")
    for gone in ('data-v2="markets"', 'data-v2="headlines"', 'data-v2="new"', 'class="stats"'):
        assert gone not in h, gone
    assert h.count('data-disclaimer="kinsho-v1"') == 1 and h.count('<div class="c na">—</div>') == 8


# ── 見た目（暗い表示は今のサイトと同じ仕組み）──
def test_dark_mode_follows_site_mechanism(offline):
    h = _page()
    assert "body.dark{--bg:" in h and ":root{--bg:#ffffff" in h
    assert "localStorage.getItem('theme')" in h and "classList.toggle('dark'" in h
    assert "#ss-btn{display:none!important}" in h     # 検索は見出しの 🔍 から開く（浮いたボタンは隠す）


# ── 新しく書いた文 ──
V2_FUNCS = [M.build_home_v2, M._index_builder, M._v2_get, M._v2_signed, M._v2_part, M._v2_vix_level,
            M._v2_stats, M._v2_ticker, M._v2_points, M._v2_schedule, M._history_items_from_build_html,
            M._v2_new_items, M._v2_jp_card, M._v2_fx_card]


def test_new_text_has_no_assertive_or_recommending_words(monkeypatch, offline):
    consts = [M.SITE_NAME_V2, M.HOME_V2_NAV, M.HOME_V2_MORE, M.HOME_V2_PICKS, M._V2_COUNTDOWN, M._V2_CUR,
              M.HOME_V2_CSS, M.HOME_V2_JS]
    text = "".join(inspect.getsource(f) for f in V2_FUNCS) + str(consts)
    for w in BANNED:
        assert w not in text, w
    # 出来上がりのページからも、ほかの部品（メルマガ・広告・外部の見出し・記事の題名）を除いて確かめる
    monkeypatch.setattr(M, "_v2_new_items", lambda now: [])
    h = _page()
    for reused in (M.NEWSLETTER_FORM, M.AD2_BLOCK, M.build_news_ticker_section(), M.GA4_TAG):
        h = h.replace(reused, "")
    for w in BANNED:
        assert w not in h, w
