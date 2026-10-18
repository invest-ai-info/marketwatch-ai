# -*- coding: utf-8 -*-
"""F1GF（グレアムの守りの前向き）の登録と、XC1 を区切ったことの反映のテスト。2026-10-18 新設。

きっかけ: 10/18 オーナー決定＝F1-G は前向きを登録・XC1 と Q17 A1 は区切る。F1 と F1GF の計算は手元の J-Quants の
データでしかできないので、記録（f1-early-lab.json・f1g-forward.json）は手元で作って送る。届く前から地図に出し、
届いたらリストが組み直され、届かなければ見張り番が知らせる、の3つがつながっていることを固定する。
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


def test_records_are_registered_in_the_lists_and_workflow():
    srcs = {s[0]: s[2] for s in V.SOURCES}
    assert srcs.get("f1-early-lab.json") == "F1" and srcs.get("f1g-forward.json") == "F1GF"
    wf = open(".github/workflows/research-lists.yml", encoding="utf-8").read()
    assert "'f1-early-lab.json'" in wf and "'f1g-forward.json'" in wf   # 届いたらリストを組み立て直す


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


def test_research_map_shows_f1gf_before_the_first_record_arrives():
    with tempfile.TemporaryDirectory() as d:
        rows = [x for x in _verify_rows(d) if "グレアム" in x["name"]]
    assert rows and rows[0]["cat"] == "jp" and "2026-11-02" in rows[0]["progress"] and rows[0]["placeholder"]


def test_research_map_reads_progress_and_drops_after_verdict():
    with tempfile.TemporaryDirectory() as d:
        rec = {"kind": "forward", "goal": 24, "fwd_start": "2026-11-02", "titles": {"F1G": "x"},
               "months": {"2026-11-02": {"n_hi": 300, "n_lo": 400}}, "progress": {"F1G": 0}, "verdicts": {}}
        with open(os.path.join(d, "f1g-forward.json"), "w", encoding="utf-8") as fh:
            json.dump(rec, fh)
        rows = [x for x in _verify_rows(d) if "グレアム" in x["name"]]
        assert rows and "判定日 1本" in rows[0]["progress"] and "0/24" in rows[0]["progress"]
        rec["verdicts"] = {"F1G": {"status": "plus", "decided_on": "2029-10-30", "n": 24,
                                   "mean": -0.2, "lo": None, "hi": None, "reason": "x"}}
        with open(os.path.join(d, "f1g-forward.json"), "w", encoding="utf-8") as fh:
            json.dump(rec, fh)
        assert not [x for x in _verify_rows(d) if "グレアム" in x["name"]]   # 判定が出たら地図から外れる


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
