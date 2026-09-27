# -*- coding: utf-8 -*-
"""記事一覧の「🧮 計算ツール」欄のカードが、トップページの「🧮 計算ツール」の並びにもあるかの点検のテスト。2026-09-27 新設。

投資のクセ診断を公開したとき、記事一覧にだけ入り、トップの並び（generate_market_news.py に直書き）に無かった。

実行:  python tests/test_tools_strip.py     （pytest 不要。pytest でも動く）
"""
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import check_site_consistency as C  # noqa: E402

GUIDES = ('<div class="category-section" id="cat-tools" data-category="ツール">'
          '<a class="article-card" href="guide-a.html"></a><a class="article-card" href="guide-b.html"></a></div>'
          '<div class="category-section" id="cat-x"><a class="article-card" href="guide-z.html"></a></div>')


def _run(strip_links):
    with tempfile.TemporaryDirectory() as d:
        gen = os.path.join(d, "gen.py")
        with open(gen, "w", encoding="utf-8") as fh:
            fh.write('x = """<div id="tools" style="a">' + "".join(f'<a href="{h}">b</a>' for h in strip_links) + '</div>"""')
        C.errors.clear()
        C.check_tools_strip(GUIDES, gen)
        out = list(C.errors)
        C.errors.clear()
    return out


def test_missing_button_is_an_error():
    errs = _run(["guide-a.html"])
    assert len(errs) == 1 and "guide-b.html" in errs[0]


def test_all_present_and_other_sections_ignored():
    assert _run(["guide-a.html", "guide-b.html"]) == []


def test_real_site_is_consistent():
    C.errors.clear()
    C.check_tools_strip(open("guides.html", encoding="utf-8").read())
    assert C.errors == [], C.errors


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
