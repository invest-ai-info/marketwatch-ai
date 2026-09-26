# -*- coding: utf-8 -*-
"""publish_article のカテゴリゲートと、check_site_consistency の欄とカードの対応検査のテスト。2026-09-26 新設。

旧 add_to_guides は入れる欄が無いと記事一覧の先頭（🧮 計算ツール欄）へ黙って入れており、
東証19・詐欺21・企業5・エントリー2 の計47枚が1か月溜まった（オーナー判断「案A＋点検」）。
  - 公開側: 入れる欄が決まらなければ、記事と一覧を書き換える前に止める
  - 点検側: data-category を宣言した欄にほかのカードが紛れていたら error

実行:  python tests/test_publish_category_gate.py     （pytest 不要。pytest でも動く）
"""
import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import check_site_consistency as C  # noqa: E402
import publish_article as P  # noqa: E402


def _card(href, badge):
    return (f'      <a class="article-card" href="{href}">\n'
            f'        <span class="article-badge badge-news">{badge}</span>\n'
            f'        <div class="article-title">t</div>\n'
            f'      </a>\n')


def _section(sid, cards="", decl=None):
    d = f' data-category="{decl}"' if decl else ""
    return (f'  <div class="category-section" id="{sid}"{d}>\n'
            f'    <div class="category-title">見出し</div>\n'
            f'    <div class="article-list">\n{cards}    </div>\n  </div>\n')


# 本物と同じ並び＝先頭が計算ツール欄
GUIDES = ("<html><body>\n"
          + _section("cat-tools", _card("guide-compound-sim.html", "ツール"), "ツール")
          + _section("cat-flash", _card("guide-news-a.html", "今日のニュース") + _card("guide-proverb-a.html", "投資格言から学ぶ"))
          + _section("cat-new", "", "新しいシリーズ")           # 1本目を待つ空の欄
          + _section("cat-proverb", "", "投資格言から学ぶ")      # 後から作った専用の欄
          + "</body></html>\n")


def _section_of(g, href):
    pos = g.index(f'href="{href}"')
    ids = [(m.start(), m.group(1)) for m in re.finditer(r'<div class="category-section" id="([^"]+)"', g)]
    return [sid for p, sid in ids if p < pos][-1]


def _add(g, category, href="guide-zz-new.html"):
    """add_to_guides を本物のまま呼び、書き込むはずだった一覧を返す（書かなければ None）"""
    out = {}
    orig_r, orig_w = P._read, P._write
    P._read = lambda p: g
    P._write = lambda p, s: out.__setitem__(p, s)
    try:
        P.add_to_guides(href, category, "🧪", "題", "説明", "2026-09-26", "5", "badge-news", False)
    finally:
        P._read, P._write = orig_r, orig_w
    return out.get("guides.html")


def test_first_article_of_new_series_goes_into_declared_empty_section():
    g = _add(GUIDES, "新しいシリーズ")
    assert g is not None and _section_of(g, "guide-zz-new.html") == "cat-new"


def test_existing_badge_card_top_of_its_section():
    g = _add(GUIDES, "今日のニュース")
    assert _section_of(g, "guide-zz-new.html") == "cat-flash"
    assert g.index("guide-zz-new.html") < g.index("guide-news-a.html")   # そのカテゴリの最上段


def test_declared_section_wins_over_same_badge_elsewhere():
    # 速報欄に同じバッジのカードが先にあっても、宣言した専用の欄へ入れる
    g = _add(GUIDES, "投資格言から学ぶ")
    assert _section_of(g, "guide-zz-new.html") == "cat-proverb"


def test_unknown_category_is_never_put_at_the_top():
    assert _add(GUIDES, "未知のカテゴリ") is None      # 旧版はここで計算ツール欄の先頭に入れていた
    assert P.check_category_gate("guide-zz-new.html", "未知のカテゴリ", GUIDES)


def test_gate_suggests_near_names_for_typos():
    msg = P.check_category_gate("guide-zz-new.html", "🧪 今日のニュース", GUIDES)
    assert msg and "今日のニュース" in msg.split("近いカテゴリ名")[1]


def test_gate_passes_known_and_already_registered():
    assert P.check_category_gate("guide-zz-new.html", "ツール", GUIDES) is None
    assert P.check_category_gate("guide-zz-new.html", "新しいシリーズ", GUIDES) is None
    # 登録済みの記事の再実行は、カテゴリ名が何でも止めない（冪等）
    assert P.check_category_gate("guide-news-a.html", "未知のカテゴリ", GUIDES) is None


def test_publish_stops_before_touching_any_file():
    """公開コマンド全体を別フォルダで動かし、止まるとき記事と一覧が1バイトも変わらないこと"""
    tmp = tempfile.mkdtemp()
    try:
        for f in ("publish_article.py", "check_guide_draft.py", "fix_mobile_overflow.py", "apply_nav_css.py"):
            if os.path.exists(os.path.join(ROOT, f)):
                shutil.copy(os.path.join(ROOT, f), tmp)
        art = ('<html><head><script type="application/ld+json">{"datePublished": "2026-09-26"}</script>'
               "</head><body><p>読了時間：約5分</p></body></html>\n")
        for name, text in (("guide-zz-new.html", art), ("guides.html", GUIDES)):
            with open(os.path.join(tmp, name), "w", encoding="utf-8") as f:
                f.write(text)
        r = subprocess.run([sys.executable, "publish_article.py", "--file", "guide-zz-new.html",
                            "--category", "未知のカテゴリ", "--emoji", "🧪", "--card-title", "題", "--desc", "説明",
                            "--allow-backdate", "--no-reconcile"],
                           cwd=tmp, capture_output=True, text=True, encoding="utf-8", timeout=60)
        assert r.returncode == 1 and "カテゴリゲート" in r.stdout, r.stdout[-400:] + r.stderr[-400:]
        with open(os.path.join(tmp, "guides.html"), encoding="utf-8") as f:
            assert f.read() == GUIDES
        with open(os.path.join(tmp, "guide-zz-new.html"), encoding="utf-8") as f:
            assert f.read() == art                       # モバイルCSS等の注入より前に止まっている
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _check(g):
    C.errors.clear()
    C.check_guides_sections(g)
    return list(C.errors)


def test_checker_catches_card_in_wrong_declared_section():
    # 今回の事故の形＝計算ツール欄の先頭に別シリーズのカード
    bad = ("<html>" + _section("cat-tools", _card("guide-tse-a.html", "東証のしくみ")
                               + _card("guide-compound-sim.html", "ツール"), "ツール") + "</html>")
    errs = _check(bad)
    assert len(errs) == 1 and "guide-tse-a.html" in errs[0] and "cat-tools" in errs[0], errs


def test_checker_catches_card_outside_its_declared_home():
    # 速報欄の格言カードは、専用の欄（cat-proverb）が宣言されているので紛れ込み扱い
    errs = _check(GUIDES)
    assert len(errs) == 1 and "guide-proverb-a.html" in errs[0] and "#cat-proverb" in errs[0]


def test_checker_allows_shared_badge_in_undeclared_sections():
    g = ("<html>" + _section("cat-econ", _card("guide-a.html", "解説"))
         + _section("cat-tech", _card("guide-b.html", "解説")) + "</html>")
    assert _check(g) == []


def test_real_guides_html_is_consistent():
    with open(os.path.join(ROOT, "guides.html"), encoding="utf-8") as f:
        assert _check(f.read()) == []


def test_every_routine_category_has_a_home_in_real_guides():
    """自動公開の手順書が渡す --category が、どれも今の guides.html で入れ先が決まること"""
    with open(os.path.join(ROOT, "guides.html"), encoding="utf-8") as f:
        g = f.read()
    # 研究日誌だけは手順書ではなく routine の指示文にある（CLAUDE.md「--category＝AIシグナル研究日誌」）
    cats = {"AIシグナル研究日誌"}
    for p in glob.glob(os.path.join(ROOT, "drafts", "*.md")):
        if os.path.basename(p) == "REVIEW.md":           # 過去の記録（6月の古い書き方を含む）
            continue
        with open(p, encoding="utf-8") as f:
            lines = f.read().splitlines()
        cats |= set(re.findall(r'--category\s+"([^"]+)"', "\n".join(lines)))
        # 表で書く手順書（AUTOPUBLISH_GUIDE の「| シリーズ | --category | --emoji |」）
        for i, ln in enumerate(lines):
            if ln.startswith("|") and "--category" in ln:
                col = [c.strip() for c in ln.strip("|").split("|")].index(
                    next(c.strip() for c in ln.strip("|").split("|") if "--category" in c))
                for row in lines[i + 2:]:
                    if not row.startswith("|"):
                        break
                    cats.add([c.strip() for c in row.strip("|").split("|")][col])
    assert len(cats) >= 10, cats
    missing = [c for c in sorted(cats) if P.check_category_gate("guide-zz-new.html", c, g)]
    assert not missing, missing


if __name__ == "__main__":
    fails = 0
    tests = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for name, fn in tests:
        try:
            fn()
            print(f"  ✅ {name}")
        except AssertionError as e:
            fails += 1
            print(f"  ❌ {name}: {e}")
    print(f"--- {len(tests) - fails}/{len(tests)} 合格 ---")
    sys.exit(1 if fails else 0)
