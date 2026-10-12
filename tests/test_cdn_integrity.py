# -*- coding: utf-8 -*-
"""CDN から読むスクリプトの改ざん防止の印（integrity＝SRI）の検査（check_site_consistency.check_cdn_integrity）のテスト。2026-10-12 新設。

確かめること＝①生成スクリプト（.py）に印の無い CDN スクリプトがあれば error ②ページ（.html）なら warning
③印があれば何も出さない ④本物のリポジトリの生成スクリプトに error が無い ⑤入れた印が配信元の公表値と同じ文字列。

実行:  python tests/test_cdn_integrity.py     （pytest 不要。pytest でも動く）
"""
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import check_site_consistency as csc  # noqa: E402

BARE = '<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>'
WITH = ('<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js" '
        'integrity="sha512-x" crossorigin="anonymous"></script>')
# cdnjs が公表している値（https://api.cdnjs.com/libraries/<名前>/<版>?fields=sri・2026-10-12 に取得して照合済み）
PUBLISHED = {
    "Chart.js/4.4.1/chart.umd.min.js":
        "sha512-CQBWl4fJHWbryGE+Pc7UAxWMUMNMWzWxF4SQo9CgkJIN1kx6djDQZjh3Y8SZ1d+6I+1zze6Z7kHXO7q3UyZAWw==",
    "chartjs-plugin-annotation/3.0.1/chartjs-plugin-annotation.min.js":
        "sha512-Hn1w6YiiFw6p6S2lXv6yKeqTk0PLVzeCwWY9n32beuPjQ5HLcvz5l2QsP+KilEr1ws37rCTw3bZpvfvVIeTh0Q==",
}


def _run_in(files):
    saved = csc.SD
    with tempfile.TemporaryDirectory() as d:
        for name, body in files.items():
            with open(os.path.join(d, name), "w", encoding="utf-8") as f:
                f.write(body)
        csc.SD = d
        csc.errors.clear()
        csc.warnings.clear()
        try:
            csc.check_cdn_integrity()
            return list(csc.errors), list(csc.warnings)
        finally:
            csc.SD = saved
            csc.errors.clear()
            csc.warnings.clear()


def test_generator_without_integrity_is_error():
    errs, warns = _run_in({"generate_x.py": f"html = '''{BARE}'''"})
    assert any("generate_x.py" in e for e in errs), (errs, warns)


def test_page_without_integrity_is_warning():
    errs, warns = _run_in({"charts.html": BARE})
    assert errs == [] and any("charts.html" in w for w in warns), (errs, warns)


def test_with_integrity_is_quiet():
    errs, warns = _run_in({"generate_x.py": f"html = '''{WITH}'''", "charts.html": WITH})
    assert errs == [] and warns == [], (errs, warns)


def test_local_only_files_are_skipped():
    errs, warns = _run_in({"_scratch.py": f"x = '''{BARE}'''"})
    assert errs == [] and warns == [], (errs, warns)


def test_real_generators_have_no_error():
    csc.errors.clear()
    csc.warnings.clear()
    csc.check_cdn_integrity()
    errs = list(csc.errors)
    csc.errors.clear()
    csc.warnings.clear()
    assert errs == [], errs


def test_generators_use_published_values():
    for name in ("generate_market_news.py", "generate_track_record_page.py", "generate_stock_chart.py"):
        src = open(name, encoding="utf-8").read()
        assert "cdn.jsdelivr.net/npm/chart.js" not in src, f"{name}: jsdelivr の自動縮小版は中身が変わりうる＝使わない"
        for path, sri in PUBLISHED.items():
            if path in src:
                assert src.count(path) == src.count(f'{path}" integrity="{sri}"'), f"{name}: {path} の印が公表値と違う"


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
