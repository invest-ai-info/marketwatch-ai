# -*- coding: utf-8 -*-
"""研究日誌 #115 上書き公開事故（2026-10-02）の再発防止のテスト。2026-10-04 新設。

10/1 公開の #115 が、翌日の別の記事で同じ URL ごと上書きされた。原因は2つ:
  ① publish_article を**下書きのパス**（drafts/draft-signal-lab-115.html）に通した
     → 上書きゲートは下書き同士を比べて素通り。カードと更新履歴が下書きを指した
  ② 公開ファイルはゲートを通らずに上書きされた
対策:
  - 公開側: 直下以外は止める（check_path_gate）。比べる相手に origin/main も足す
  - 点検側: カードの日付＝記事の公開日か／カード・更新履歴が drafts/ を指していないか／
            SYNC_FILES に drafts/draft-* が無いか（check_card_dates・check_sync_forbidden）

実行:  python tests/test_overwrite_guard.py     （pytest 不要。pytest でも動く）
"""
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import check_site_consistency as C  # noqa: E402
import publish_article as P  # noqa: E402


def _article(date, title="t"):
    return (f'<html><head><title>{title}</title>'
            f'<script type="application/ld+json">{{"datePublished": "{date}"}}</script></head></html>')


def _card(href, date):
    return (f'      <a class="article-card" href="{href}">\n'
            f'        <div class="article-title">t</div>\n'
            f'        <time datetime="{date}">x</time>\n'
            f'      </a>\n')


# ── 公開側 ─────────────────────────────────────────

def test_path_gate_allows_site_root_only():
    assert P.check_path_gate("guide-signal-lab-118.html") is None
    assert P.check_path_gate("./guide-signal-lab-118.html") is None
    assert P.check_path_gate("drafts/draft-signal-lab-115.html")
    assert P.check_path_gate("drafts\\draft-signal-lab-115.html")


def test_new_article_passes():
    assert P.check_overwrite_gate("guide-x.html", _article("2026-10-02"), versions=[]) is None


def test_same_article_fix_passes():
    v = [("HEAD", _article("2026-10-02")), ("origin/main", _article("2026-10-02"))]
    assert P.check_overwrite_gate("guide-x.html", _article("2026-10-02"), versions=v) is None


def test_overwrite_stops_when_only_origin_main_has_it():
    # 作業場所の HEAD が古くて記事を持っていなくても、GitHub の最新にあれば止める
    v = [("origin/main", _article("2026-10-01", "RSI #115"))]
    err = P.check_overwrite_gate("guide-signal-lab-115.html", _article("2026-10-02", "GC #115"), versions=v)
    assert err and "origin/main" in err and "2026-10-01" in err


def test_overwrite_stops_on_head_too():
    v = [("HEAD", _article("2026-10-01"))]
    assert P.check_overwrite_gate("guide-x.html", _article("2026-10-02"), versions=v)


def test_allow_overwrite_is_explicit_escape():
    v = [("origin/main", _article("2026-10-01"))]
    assert P.check_overwrite_gate("guide-x.html", _article("2026-10-02"),
                                  allow_overwrite=True, versions=v) is None


# ── 点検側 ─────────────────────────────────────────

def _run_card_check(files, guides, gen=""):
    tmp = tempfile.mkdtemp()
    old_sd = C.SD
    try:
        for name, text in files.items():
            with open(os.path.join(tmp, name), "w", encoding="utf-8") as f:
                f.write(text)
        with open(os.path.join(tmp, "gen.py"), "w", encoding="utf-8") as f:
            f.write(gen)
        C.SD = tmp
        C.errors.clear()
        C.check_card_dates(guides, gen_py="gen.py")
        return list(C.errors)
    finally:
        C.SD = old_sd
        shutil.rmtree(tmp, ignore_errors=True)


def test_card_date_matches_article():
    errs = _run_card_check({"guide-a.html": _article("2026-10-02")}, _card("guide-a.html", "2026-10-02"))
    assert errs == [], errs


def test_card_date_mismatch_is_error():
    errs = _run_card_check({"guide-a.html": _article("2026-10-02")}, _card("guide-a.html", "2026-10-01"))
    assert len(errs) == 1 and "上書き" in errs[0], errs


def test_card_pointing_to_drafts_is_error():
    errs = _run_card_check({}, _card("drafts/draft-a.html", "2026-10-02"))
    assert len(errs) == 1 and "下書き" in errs[0], errs


def test_history_link_to_drafts_is_error():
    gen = '{"date": "2026-10-02", "line": \'<a href="drafts/draft-a.html">x</a>\'}'
    errs = _run_card_check({}, "", gen=gen)
    assert len(errs) == 1 and "更新履歴" in errs[0], errs


def test_sync_files_must_not_include_drafts():
    C.errors.clear()
    C.check_sync_forbidden(["drafts/draft-signal-lab-115.html", "drafts/AUTODRAFT_GUIDE.md", "guide-a.html"])
    errs = list(C.errors)
    assert len(errs) == 1 and "draft-signal-lab-115" in errs[0], errs


def test_real_site_has_no_card_problems():
    C.errors.clear()
    with open(os.path.join(ROOT, "guides.html"), encoding="utf-8") as f:
        C.check_card_dates(f.read())
    errs = list(C.errors)
    assert errs == [], errs


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
