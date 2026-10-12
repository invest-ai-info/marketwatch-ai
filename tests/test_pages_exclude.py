# -*- coding: utf-8 -*-
"""サイト（GitHub Pages）に載せないファイルの検査（check_site_consistency.check_pages_exclude）のテスト。2026-10-12 新設。

背景：.nojekyll で Jekyll を止めていた間（2026-08-05〜10-12）は、リポジトリの全ファイルが
marketwatch-jp.com でそのまま配信され、my-trades.json・memory/*.md・CLAUDE.md・全コードが誰でも開けた。
_config.yml の exclude で「サイトではないもの」を載せないようにし、その一覧の抜けを機械で止める。

確かめること＝①_config.yml の exclude を読める ②.nojekyll が戻ったら error ③必須の除外が抜けたら error
④公開ページが載せないファイルを指したら error（リンク切れになる）⑤.md の Liquid は exclude で無害
⑥_config.yml だけは SYNC してよい（ほかの _ 始まりは今までどおり止める）⑦本物の _config.yml と公開ページで error が出ない。

実行:  python tests/test_pages_exclude.py     （pytest 不要。pytest でも動く）
"""
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import check_site_consistency as csc  # noqa: E402

GOOD_CONFIG = (
    "# コメント\n"
    "exclude:\n"
    '  - "*.md"\n'
    '  - "*.py"\n'
    "  - drafts/\n"
    "  - tests/\n"
    "  - my-trades.json   # 取引記録\n"
    "  - my-trades.csv\n"
)


def _run_in(files):
    """作り物のフォルダで check_pages_exclude を走らせ、(errors, warnings) を返す。"""
    saved = csc.SD
    with tempfile.TemporaryDirectory() as d:
        for name, body in files.items():
            p = os.path.join(d, name)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                f.write(body)
        csc.SD = d
        csc.errors.clear()
        csc.warnings.clear()
        try:
            csc.check_pages_exclude()
            return list(csc.errors), list(csc.warnings)
        finally:
            csc.SD = saved
            csc.errors.clear()
            csc.warnings.clear()


def test_reads_exclude_list():
    assert csc._pages_excludes(GOOD_CONFIG) == ["*.md", "*.py", "drafts/", "tests/", "my-trades.json", "my-trades.csv"]
    assert csc._pages_excludes("title: x\nexclude:\n  - a/\ninclude:\n  - b\n") == ["a/"]


def test_matcher_works_like_jekyll():
    ex = csc._pages_excludes(GOOD_CONFIG)
    assert csc._pages_excluded("memory/01_profile.md", ex)      # *.md は下のフォルダにも効く
    assert csc._pages_excluded("CLAUDE.md", ex)
    assert csc._pages_excluded("drafts/draft-signal-lab-028.html", ex)
    assert csc._pages_excluded("my-trades.json", ex)
    assert not csc._pages_excluded("index.html", ex)
    assert not csc._pages_excluded("signals-log.json", ex)
    assert not csc._pages_excluded("research-list.html", ex)


def test_nojekyll_is_error():
    errs, _ = _run_in({"_config.yml": GOOD_CONFIG, ".nojekyll": ""})
    assert any(".nojekyll" in e for e in errs), errs


def test_missing_config_is_error():
    errs, _ = _run_in({"index.html": "<a href='guides.html'>x</a>"})
    assert any("_config.yml" in e for e in errs), errs


def test_missing_required_exclude_is_error():
    errs, _ = _run_in({"_config.yml": GOOD_CONFIG.replace("  - my-trades.json   # 取引記録\n", "")})
    assert any("my-trades.json" in e for e in errs), errs


def test_public_page_linking_to_excluded_file_is_error():
    page = '<a class="related-card" href="drafts/draft-signal-lab-028.html">前の回</a><a href="guides.html">一覧</a>'
    errs, _ = _run_in({"_config.yml": GOOD_CONFIG, "guide-signal-lab-033.html": page,
                       "drafts/draft-signal-lab-028.html": "x", "guides.html": "x"})
    assert any("guide-signal-lab-033.html" in e and "drafts/draft-signal-lab-028.html" in e for e in errs), errs


def test_good_setup_has_no_error():
    page = '<a href="guides.html">一覧</a><script src="site-search.js"></script><a href="https://example.com/x.md">外</a>'
    errs, _ = _run_in({"_config.yml": GOOD_CONFIG, "index.html": page, "guides.html": "x", "site-search.js": "x"})
    assert errs == [], errs


def test_liquid_in_markdown_is_harmless_when_md_excluded():
    saved = csc.SD
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "_config.yml"), "w", encoding="utf-8").write(GOOD_CONFIG)
        open(os.path.join(d, "NOTE.md"), "w", encoding="utf-8").write("f-string は {" + "{ と書く")
        csc.SD = d
        csc.errors.clear()
        csc.warnings.clear()
        try:
            csc.check_liquid_in_markdown(["NOTE.md"])
            assert csc.errors == [], csc.errors
            # exclude から *.md を外すと Jekyll が読む＝ビルドが落ちるので error に戻る
            open(os.path.join(d, "_config.yml"), "w", encoding="utf-8").write(GOOD_CONFIG.replace('  - "*.md"\n', ""))
            csc.check_liquid_in_markdown(["NOTE.md"])
            assert any("NOTE.md" in e for e in csc.errors), csc.errors
        finally:
            csc.SD = saved
            csc.errors.clear()
            csc.warnings.clear()


def test_sync_allows_only_config_among_underscore_files():
    csc.errors.clear()
    csc.check_sync_forbidden(["_config.yml"])
    assert csc.errors == [], csc.errors
    csc.check_sync_forbidden(["_private_notes.py"])
    assert any("_private_notes.py" in e for e in csc.errors), csc.errors
    csc.errors.clear()


def test_real_repo_has_no_error():
    csc.errors.clear()
    csc.warnings.clear()
    csc.check_pages_exclude()
    errs = list(csc.errors)
    csc.errors.clear()
    csc.warnings.clear()
    assert errs == [], errs


if __name__ == "__main__":
    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("ok  ", name)
            except AssertionError as e:
                fails += 1
                print("FAIL", name, str(e)[:300])
    print("失敗", fails, "件")
    sys.exit(1 if fails else 0)
