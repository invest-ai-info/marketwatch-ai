# -*- coding: utf-8 -*-
"""「まもなく発表」メールの1行（発表直後2時間は普段の何倍動いたか）のテスト。
2026-09-27 オーナー決定「メールに1行足してください」（新しい柱 B2② の実測を使う）。

実行:  python tests/test_indicator_shock_line.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import send_indicator_digest as S  # noqa: E402

RATIO = {"b2": {"ratio": {
    "fomc": {"USDJPY=X": {"n": 23, "ratio": 5.8}, "GC=F": {"n": 19, "ratio": 4.7},
             "EURUSD=X": {"n": 23, "ratio": 5.3}, "ES=F": {"n": 19, "ratio": 2.6}},
    "nfp": {"USDJPY=X": {"n": 32, "ratio": 2.8}}}}}


def _file(obj):
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    json.dump(obj, open(path, "w", encoding="utf-8"))
    return path


def test_fomc_line_shows_top_three_measured():
    path = _file(RATIO)
    try:
        line = S.shock_line({"name": "FOMC 政策金利発表（結果発表）", "affected_assets": ["all"]}, path)
    finally:
        os.remove(path)
    assert "ドル円 5.8倍・ユーロドル 5.3倍・金 4.7倍" in line and "（19〜23回）" in line
    assert "S&P500" not in line                                    # 上位3つだけ


def test_only_affected_assets_and_only_measured_events():
    path = _file(RATIO)
    try:
        line = S.shock_line({"name": "FOMC 政策金利発表（10月）", "affected_assets": ["ES=F"]}, path)
        assert line.endswith("S&P500 2.6倍（19回）")
        assert S.shock_line({"name": "英雇用統計（失業率・賃金）", "affected_assets": ["all"]}, path) is None
        assert S.shock_line({"name": "中国 CPI（5月）", "affected_assets": ["all"]}, path) is None
        assert S.shock_line({"name": "米 CPI（10月分）", "affected_assets": ["all"]}, path) is None   # 測っていない
        assert S.shock_line({"name": "米雇用統計 NFP（10月分）", "affected_assets": ["GC=F"]}, path) is None
    finally:
        os.remove(path)


def test_missing_file_adds_nothing_and_alert_still_builds():
    assert S.shock_line({"name": "FOMC 政策金利発表（結果発表）"}, "/nonexistent/pillar-lab.json") is None
    subj, body = S.build_alert(dt.datetime(2026, 10, 2, 20, 30, tzinfo=S.JST))
    if subj:                                                        # 本物のカレンダーに雇用統計がある場合
        assert "まもなく発表" in body and "いまやること" in body


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
