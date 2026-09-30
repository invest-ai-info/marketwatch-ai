# -*- coding: utf-8 -*-
"""S4（手元の MT5 で1回だけ数えた）の記録が、検証済みリストに載る形になっているか"""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
import verified_list as V  # noqa: E402


def test_s4_record_in_sources_and_well_formed(monkeypatch):
    monkeypatch.chdir(ROOT)
    src = [s for s in V.SOURCES if s[0] == "s4-level-fade.json"]
    assert len(src) == 1 and src[0][2] == ""
    with open("s4-level-fade.json", encoding="utf-8") as f:
        d = json.load(f)
    assert d["kind"] == "backtest" and d["goal"] == 1000 and set(d["titles"]) == {"S4"}
    v = d["verdicts"]["S4"]
    assert v["status"] == "stop" and v["n"] >= 1000 and v["lo"] <= v["mean"] <= v["hi"] < 0
    stop, plus, watching = V.collect(src)
    assert [r["id"] for r in stop] == ["S4"] and not plus and not watching
    assert "S4" in V.render(stop, plus, watching, now="t")
