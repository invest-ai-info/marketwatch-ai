# -*- coding: utf-8 -*-
"""提供終了した Gemini のモデルを、候補の並びに戻さないためのテスト。2026-10-24 新設。

きっかけ:
- gemini-2.0-flash / gemini-2.0-flash-lite は 2026-06-01 に提供終了（API は 404「no longer available.
  Please update your code to use models/gemini-3.8-flash」）。それでも約14か所が候補の先頭に置いたままで、
  毎回 404 を1回はさんでから 2.5 に落ちていた。YouTube 要約などはログに最後のモデルのエラーしか出さないので、
  先頭が死んでいることも見えなかった
- 一覧と後継: https://ai.google.dev/gemini-api/docs/deprecations （提供終了が増えたら RETIRED に足す）

固定すること: リポジトリ直下の *.py と .github/workflows/*.yml に、提供終了のモデル名が出てこない
（research/ は手元専用なので見ない。このテスト自身も見ない）。

実行:  python tests/test_gemini_retired_models.py     （pytest 不要。pytest でも動く）
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

RETIRED = ("gemini-2.0-flash", "gemini-2.0-flash-lite")
# 後ろに文字が続く別の名前（例 gemini-2.0-flash-lite を gemini-2.0-flash と数え直さない）は名前ごとに見る
PAT = re.compile(r"""["'](%s)["']""" % "|".join(re.escape(m) for m in RETIRED))


def offenders():
    files = glob.glob(os.path.join(ROOT, "*.py")) + glob.glob(os.path.join(ROOT, ".github", "workflows", "*.yml"))
    hits = []
    for f in sorted(files):
        with open(f, encoding="utf-8", errors="replace") as fh:
            for i, line in enumerate(fh, 1):
                m = PAT.search(line)
                if m:
                    hits.append(f"{os.path.relpath(f, ROOT)}:{i}: {m.group(1)}")
    return hits


def test_no_retired_gemini_models_in_candidates():
    hits = offenders()
    assert not hits, "提供終了のモデルが残っている:\n  " + "\n  ".join(hits)


def test_pattern_catches_both_names():
    assert PAT.search('for m in ("gemini-2.0-flash-lite", "x")').group(1) == "gemini-2.0-flash-lite"
    assert PAT.search("MODELS = ('gemini-2.0-flash',)").group(1) == "gemini-2.0-flash"
    assert PAT.search('("gemini-2.5-flash", "gemini-2.5-flash-lite")') is None


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
