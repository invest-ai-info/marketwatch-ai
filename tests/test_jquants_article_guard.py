# -*- coding: utf-8 -*-
"""記事に「J-Quants のデータで当サイトが数えた」結果を載せない番人（check_site_consistency.check_jquants_public の⑤）のテスト。
2026-11-21 新設（オーナー「E も直す」・相談メモ⑪ の E）。

確かめること＝①J-Quants と自社の集計の言葉が同じ記事にあれば error ②J-Quants の名前だけなら止めない
③自社の集計の言葉だけ（J-Quants なし）なら止めない ④本物のリポジトリの記事に⑤の error が無い。

実行:  python tests/test_jquants_article_guard.py     （pytest 不要。pytest でも動く）
"""
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import check_site_consistency as csc  # noqa: E402

OLD_LINE = "記載した傾向は、公式開示の財務情報（JPX／J-Quants）にもとづく自社集計であり…"


def _run_in(files):
    saved = csc.SD
    with tempfile.TemporaryDirectory() as d:
        for name, body in files.items():
            with open(os.path.join(d, name), "w", encoding="utf-8") as f:
                f.write(body)
        csc.SD = d
        csc.errors.clear()
        try:
            csc.check_jquants_public([])
            return [e for e in csc.errors if "自社の集計の言葉" in e]
        finally:
            csc.SD = saved
            csc.errors.clear()


def test_jquants_with_own_aggregate_is_error():
    errs = _run_in({"guide-x.html": f"<p>{OLD_LINE}</p>"})
    assert len(errs) == 1 and "guide-x.html" in errs[0]


def test_jquants_name_only_is_quiet():
    assert _run_in({"guide-x.html": "<p>日本株の財務データは J-Quants（JPX の公式サービス）でも手に入ります。</p>"}) == []


def test_own_words_without_jquants_is_quiet():
    assert _run_in({"guide-x.html": "<p>当サイトが数えた集計ではありません。論文の結果です。</p>"}) == []


def test_real_articles_have_no_error():
    csc.errors.clear()
    csc.check_jquants_public(None)
    errs = [e for e in csc.errors if "自社の集計の言葉" in e]
    csc.errors.clear()
    assert errs == [], errs


if __name__ == "__main__":
    n = 0
    for k, v in list(globals().items()):
        if k.startswith("test_") and callable(v):
            v()
            n += 1
            print("ok", k)
    print(f"✅ {n} 件")
