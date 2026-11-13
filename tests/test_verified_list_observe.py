# -*- coding: utf-8 -*-
"""検証済みリストの「📏 気配・注文の動き方の問い」の節（verified_list.OBSERVE_SOURCES）のテスト。2026-11-13 新設。

オーナー「両方とも進めてください」＝J10b の判定（寄り前の気配の窓は寄りまでに縮みやすい）を検証済みリストに載せる・
点検表 日本株⑤と朝のメールの説明文（jp_markers.GUIDE）にも1行足す。
①判定の出たものだけ載る（判定の前・記録なしは載らない）②数字は記録の判定の欄から写す（手で書かない）
③結果の言葉ごとの読み方 ④J46 の判定（mean_diff）も同じ節に載る ⑤research-lists.yml が記録の更新で動く
⑥点検表⑤とメールの説明文に J10b の結果がある
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import jp_markers as M  # noqa: E402
import verified_list as V  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def _src(path, key="verdict", mean="mean", sec="J10b"):
    base = next(s for s in V.OBSERVE_SOURCES if s["sec"] == sec)
    return [dict(base, src=path, key=key, mean=mean)]


def _write(d, data):
    p = os.path.join(d, "j10b-records.json")
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False)
    return p


def test_only_judged_rows_are_listed():
    with tempfile.TemporaryDirectory() as d:
        assert V.collect_observe(_src(os.path.join(d, "none.json"))) == []                 # 記録なし
        p = _write(d, {"records": [], "verdict": None})
        assert V.collect_observe(_src(p)) == []                                             # 判定の前
        p = _write(d, {"records": [], "verdict": {"decided_on": "2026-11-13", "n": 382, "days": 20, "mean": 0.011318,
                                                  "lo": 0.009229, "hi": 0.013402, "status": "縮みやすい"}})
        rows = V.collect_observe(_src(p))
        assert len(rows) == 1 and rows[0]["status"] == "縮みやすい" and rows[0]["n"] == 382
        md = "\n".join(V.render_observe(rows))
        assert "## 📏 気配・注文の動き方の問い" in md
        assert "| J10b |" in md and "2026-11-13" in md and "+1.13％" in md and "+0.92％〜+1.34％" in md
        assert "終値の側へ戻って寄りやすい" in md                                             # 結果の言葉ごとの読み方
        assert V.render_observe([])[-2] == "- まだ無い"
        row = [ln for ln in md.split("\n") if ln.startswith("| J10b |")][0]
        assert row.replace("\\|", "").count("|") == 9                                       # 8列＝縦線9本（中身の縦線は逃がす）


def test_j46_verdict_uses_mean_diff_and_prefix_words():
    with tempfile.TemporaryDirectory() as d:
        p = _write(d, {"records": [], "verdict_j46": {"decided_on": "2027-01-08", "n": 1003, "days_compared": 50,
                                                      "mean_diff": -0.0021, "lo": -0.004, "hi": -0.0003, "top_net": -0.002,
                                                      "status": "罠の目印（兆し）"}})
        rows = V.collect_observe(_src(p, key="verdict_j46", mean="mean_diff", sec="J46"))
        assert rows[0]["mean"] == -0.0021 and "下げやすく" in rows[0]["means"]
        p = _write(d, {"records": [], "verdict_j46": {"decided_on": "2027-01-08", "n": 1003, "mean_diff": 0.0, "lo": 0.0,
                                                      "hi": 0.0, "status": "見えない（比べられる日が無い）"}})
        rows = V.collect_observe(_src(p, key="verdict_j46", mean="mean_diff", sec="J46"))
        assert "決まった向きの差は見えない" in rows[0]["means"]                              # 頭の言葉で読み方を引く


def test_render_has_the_section_and_sources_are_registered():
    md = V.render([], [], [], now="2026-11-13T10:00+09:00", observe=[])
    assert "## 📏 気配・注文の動き方の問い" in md
    assert [s["sec"] for s in V.OBSERVE_SOURCES] == ["J10b", "J46"]
    assert all(s["src"] == "j10b-records.json" for s in V.OBSERVE_SOURCES)
    for s in V.OBSERVE_SOURCES:                                                              # 公開もありうる文＝記号を入れない
        assert all("J10" not in t and "J46" not in t for t in s["means"].values())
    with open(os.path.join(ROOT, ".github", "workflows", "research-lists.yml"), encoding="utf-8") as fh:
        wf = fh.read()
    assert "'j10b-records.json'" in wf and "python verified_list.py" in wf


def test_rules_and_mail_guide_carry_the_result():
    g = "\n".join(M.GUIDE)
    assert "8:59 の気配も" in g and "縮む" in g and "寄り値で決め直す" in g
    with open(os.path.join(ROOT, "MY_TRADING_RULES.md"), encoding="utf-8") as fh:
        rules = fh.read()
    assert "8:59 の気配も、寄りでは前の日の終値の側へ縮みやすい" in rules and "J10b" in rules and "1.13" in rules


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
