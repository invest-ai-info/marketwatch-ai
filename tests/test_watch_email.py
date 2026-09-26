# -*- coding: utf-8 -*-
"""観察中の候補のメール（👀観察中・未確定）のテスト。2026-09-26 新設（オーナー決定「成績を上げる」の④）。

昇格した仮説が0本のため 7/22 を最後にシグナルのメールが0通だった。tracker で watch=True の候補に当てはまる
4時間足のシグナルだけ、「未確定」と明記して送る。

実行:  python tests/test_watch_email.py     （pytest 不要。pytest でも動く）
"""
import json
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import generate_technical_alerts as G  # noqa: E402
import signal_lab_tracker as T  # noqa: E402

FLIP = {"id": "dip__flip", "label": "下降トレンド中の逆張り買い（逆向きで再登録）", "kind": "edge", "status": "tracking",
        "watch": True, "registered_at": "2026-09-27",
        "filter": {"trend": "下降", "reversal_long": True, "fired_from": "2026-09-27"},
        "flip_evidence": {"n": 349, "avgR": 0.19, "rci_lo": 0.038, "rci_hi": 0.342, "window": "2026-06-25〜2026-09-26"},
        "forward": {"n": 3, "avgR": 0.5}}


def _probe(signal="rsi_oversold_bounce", trend="下降", long=True, tf="4h"):
    """エンジンが送信前に作る照合用の属性（発火時刻は持たない）"""
    return {"ticker": "GC=F", "direction": "ロング（買い）" if long else "ショート（売り）", "primary_signal": signal,
            "signal_types": [signal], "timeframe": tf, "trend_alignment": {"higher_tf_trend": trend}}


def _tracker_file(hyps):
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    json.dump({"hypotheses": hyps}, open(path, "w", encoding="utf-8"), ensure_ascii=False)
    return path


def test_live_filter_drops_only_window_keys():
    assert G.live_filter({"tier": "good", "fired_from": "2026-09-27", "fired_before": "2026-10-01"}) == {"tier": "good"}
    assert G.live_filter(None) == {}


def test_load_watch_selects_tracking_edges_with_watch():
    hyps = [FLIP,
            dict(FLIP, id="promoted", status="promoted"), dict(FLIP, id="rejected", status="rejected"),
            dict(FLIP, id="gate", kind="gate"), dict(FLIP, id="nowatch", watch=None)]
    path = _tracker_file(hyps)
    try:
        w = G.load_watch_hypotheses(path)
    finally:
        os.remove(path)
    assert [h["id"] for h in w] == ["dip__flip"]
    assert "fired_from" not in w[0]["filter"]               # 照合用のコピーは期間の条件を外す
    assert FLIP["filter"]["fired_from"] == "2026-09-27"     # 元の仮説は書き換えない


def test_unreadable_tracker_sends_no_watch_email():
    assert G.load_watch_hypotheses("/nonexistent/tracker.json") == []


def test_dip_buy_signal_matches_only_after_dropping_the_window():
    w = [dict(FLIP, filter=G.live_filter(FLIP["filter"]))]
    assert G.match_promoted_hypothesis(w, _probe())["id"] == "dip__flip"
    assert G.match_promoted_hypothesis([FLIP], _probe()) is None          # 期間の条件付きのままだと永久に不一致
    assert G.match_promoted_hypothesis(w, _probe(trend="上昇")) is None    # 下降トレンド以外は対象外
    assert G.match_promoted_hypothesis(w, _probe(long=False)) is None       # 売りは対象外


def test_header_says_unconfirmed_with_evidence():
    head = G.watch_email_header(FLIP)
    assert "観察中の候補（未確定）" in head and "確定していません" in head
    assert "+0.19R・349件" in head and "2026-06-25〜2026-09-26" in head and "登録後（2026-09-27〜）: 3件" in head


def test_real_tracker_after_morning_update_has_exactly_two_watch_candidates():
    """本物の tracker に毎朝の更新（登録＋集計）をかけると、観察中の候補は押し目買いの2本だけ"""
    tmp = tempfile.mkdtemp()
    path = os.path.join(tmp, "signal-lab-tracker.json")
    shutil.copy(os.path.join(ROOT, "signal-lab-tracker.json"), path)
    orig = T.TRACKER
    T.TRACKER = path
    try:
        data = T.freeze_universe(T.load_log(os.path.join(ROOT, "signals-log.json")))
        T.cmd_update(None, data, "2026-09-26")
        w = G.load_watch_hypotheses(path)
    finally:
        T.TRACKER = orig
        shutil.rmtree(tmp, ignore_errors=True)
    assert sorted(h["id"] for h in w) == ["auto_reversal_long-True_trend-下降__flip", "rsi_oversold_4h"], [h["id"] for h in w]
    assert all("fired_from" not in h["filter"] for h in w)


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
