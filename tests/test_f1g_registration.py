# -*- coding: utf-8 -*-
"""F1GF（グレアムの守りの前向き）の登録と、XC1 を区切ったことの反映のテスト。2026-10-18 新設。

きっかけ: 10/18 オーナー決定＝F1-G は前向きを登録・XC1 と Q17 A1 は区切る。F1 と F1GF の計算は手元の J-Quants の
データでしかできない。
🔁 2026-11-20 オーナー「C と D も外す」＝J-Quants の数で数えた結果は公開しない（J-Quants の案内で、分析結果の
続けての公開・第三者への表示は ×・相談メモ⑪）。記録（f1-early-lab.json・f1g-forward.json）は手元の research/jq-results/
だけに置き、検証済みリスト・研究の地図・組み立て直しのワークフローは読まない、を固定する（前は「送って載せる」を固定していた）。
XC1 は過去のデータの「◯ 低い費用ならプラス」で、どちらのリストにも載らない状態だった＝記録は書き換えずに
verified_list.CLOSED の1行で「⏹ ストップ」に載せる。

実行:  python tests/test_f1g_registration.py     （pytest 不要。pytest でも動く）
"""
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import research_map as R  # noqa: E402
import verified_list as V  # noqa: E402


JQ = ("f1-early-lab.json", "f1g-forward.json", "highs-fund-lab.json", "highs-value-lab.json",
      "j52-timing-lab.json", "j52-history.json", "j9-yutai-lab.json")


def test_jquants_results_are_not_in_the_lists_or_workflow():
    srcs = {s[0] for s in V.SOURCES} | {s[0] for s in V.MARKER_SOURCES}
    assert not srcs & set(JQ)
    wf = open(".github/workflows/research-lists.yml", encoding="utf-8").read()
    assert not [n for n in JQ if f"'{n}'" in wf]
    import sync_to_github as S                                      # GitHub 側は短い控え（一覧が無いこともある）
    assert not [n for n in JQ if n in (getattr(S, "SYNC_FILES", None) or [])]
    assert not [n for n in JQ if os.path.exists(n)]                  # リポジトリ直下に置かない（手元は research/jq-results/）
    assert "手元だけ" in V.JP_PRIVATE_NOTE and V.JP_PRIVATE_NOTE == R.JP_PRIVATE_NOTE


def test_prereg_is_written_before_any_counting():
    pre = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "## F1GF グレアムの守りの前向き" in pre
    assert "2026-11-02" in pre and "24本" in pre   # 最初の判定日と判定の本数


def test_xc1_is_listed_as_stopped_with_numbers_from_the_record():
    stop, _plus, _w = V.collect()
    row = next(r for r in stop if r["src"].startswith("XC") and r["id"] == "XC1")
    net = json.load(open("fx-confirm-lab.json", encoding="utf-8"))["results"]["XC1"]["net"]
    assert abs(row["v"]["mean"] - net["mean"] / 10000) < 1e-12   # 手で写さない＝記録の数字
    assert row["v"]["status"] == "stop" and row["v"]["decided_on"] == "2026-10-18"
    assert "XC" not in row["v"]["reason"]                          # 公開ページに出る理由に検証の番号を入れない


def test_closed_needs_no_change_to_the_generated_record():
    data = json.load(open("fx-confirm-lab.json", encoding="utf-8"))
    assert "XC1" not in (data.get("verdicts") or {})   # 記録（Actions が書く）は書き換えていない


def _verify_rows(root):
    st = R.collect_studies(root, R.collect(root))
    return st["verify"] if isinstance(st, dict) else st[0]


def test_research_map_never_shows_the_jquants_studies():
    with tempfile.TemporaryDirectory() as d:
        assert not [x for x in _verify_rows(d) if "グレアム" in x["name"] or "業績" in x["name"]]
        rec = {"kind": "forward", "goal": 24, "fwd_start": "2026-11-02", "titles": {"F1G": "x"},
               "months": {"2026-11-02": {"n_hi": 300, "n_lo": 400}}, "progress": {"F1G": 0}, "verdicts": {}}
        for n in JQ:                                                  # 記録がまぎれこんでも読まない
            with open(os.path.join(d, n), "w", encoding="utf-8") as fh:
                json.dump(rec, fh)
        os.makedirs(os.path.join(d, "yutai-edinet"))
        st = R.collect_studies(d, R.collect(d))
        names = " ".join(x["name"] for x in st["verify"] + st["research"])
        assert "グレアム" not in names and "業績の裏づけ" not in names and "割安なら" not in names and "株主優待" not in names
        page = R.build_list_page(root=d)
        assert R.JP_PRIVATE_NOTE in page and "グレアム" not in page


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
