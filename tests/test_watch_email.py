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


def test_watch_can_override_only_when_momentum_alone_blocked():
    """2026-09-28：観察中の候補（逆張りの買い）は勢いの絞り込みと相性が合わず、当てはまった94件が全部そこで止まっていた。
    勢いの絞り込み「だけ」で止まったときに限り、観察中の候補の照合をする。"""
    hyps = [{"id": "w"}]
    assert G.watch_can_override(False, True, hyps) is True        # 勢いだけで止まった → 照合する
    assert G.watch_can_override(True, False, hyps) is False       # もともと通っている → いつもの道
    assert G.watch_can_override(False, False, hyps) is False      # ほかの絞り込み（方向感なし等）で止まった → 送らない
    assert G.watch_can_override(False, True, []) is False         # 観察中の候補が無い／読めない → 送らない（fail-closed）


def test_gate_keeps_momentum_record_honest():
    """観察中の候補として送っても、記録の「勢いの絞り込みを通ったか」は通っていない扱いのまま（集計を混ぜない）"""
    src = open("generate_technical_alerts.py", encoding="utf-8").read()
    assert '"passed": filter_send_email and not watch_override' in src
    assert "watch_only = watch_can_override(filter_send_email, momentum_blocked, watch_hyps)" in src
    assert "promoted_match = None if watch_only else match_promoted_hypothesis" in src   # 昇格した仮説の配信は変えない


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


# 2026-11-18 本物の tracker（signal-lab-tracker.json）を読むテストをやめ、小さな見本の tracker に置き換えた。
#   本物は GitHub 側で毎朝書き換わる（SYNC禁忌）。11/17 からの毎日の入れ替えで rsi_oversold_4h が
#   status="retired"（watch=True のまま）になり、「観察中はこの2本」と決め打ちしたテストが壊れていた。
#   中身の変化で落ちるのはテストの欠陥なので、見るのは「更新のあとも、選ばれる条件が正しく効くか」に絞る。

def _sig(day, signal="bb_lower_touch", trend="下降", long=True, tf="4h", outcome="tp1"):
    """signals-log の決済済み1件の形（固定オラクル signal_lab_verify.match が読む項目だけ）"""
    return {"fired_at": f"{day}T10:00:00+09:00", "ticker": "GC=F", "primary_signal": signal, "signal_types": [signal],
            "direction": "ロング（買い）" if long else "ショート（売り）", "timeframe": tf, "outcome": outcome,
            "trend_alignment": {"higher_tf_trend": trend}}


def _morning_update(hyps, data, today, path):
    """一時ファイルの tracker で毎朝の更新（cmd_update）を1回まわす。既定の登録は足さない（見本の中身だけで確かめる）"""
    if hyps is not None:
        json.dump({"updated_at": None, "hypotheses": hyps}, open(path, "w", encoding="utf-8"), ensure_ascii=False)
    orig_path, orig_boot = T.TRACKER, T.apply_holdout_bootstrap
    T.TRACKER = path
    if hyps is not None:
        T.apply_holdout_bootstrap = lambda t: 0
    try:
        T.cmd_update(None, data, today)
    finally:
        T.TRACKER, T.apply_holdout_bootstrap = orig_path, orig_boot


def _edge(id_, filt, **kw):
    return dict({"id": id_, "label": id_, "kind": "edge", "status": "tracking", "registered_at": "2026-09-27",
                 "filter": filt}, **kw)


def test_morning_update_keeps_watch_only_on_tracking_edges():
    """毎朝の更新をかけたあと、観察中の候補に選ばれるのは「蓄積中（tracking）の勝ち筋（edge）で watch=True」だけ。
    止まった候補（2026-11 の本物の rsi_oversold_4h と同じ retired＋watch=True）は更新で戻らず、対象から外れる。"""
    hyps = [
        FLIP,                                                                                       # 期間の条件つき → 選ぶ
        _edge("bb_lower_4h", {"signal": "bb_lower_touch", "tf": "4h"}, watch=True),                # 期間の条件なし → 選ぶ
        _edge("rsi_oversold_4h", {"signal": "rsi_oversold_bounce", "tf": "4h"}, watch=True,
              status="retired", retired_at="2026-11-17", retire_reason="culled"),                 # 見込みなし → 外す
        _edge("rej", {"signal": "macd_golden_cross", "tf": "4h"}, watch=True,
              status="rejected", rejected_at="2026-10-01"),                                         # 反証 → 外す
        _edge("gate", {"signal": "ma_dead_cross", "tf": "4h"}, watch=True, kind="gate"),           # 回避(gate) → 外す
        _edge("plain", {"signal": "bb_lower_touch", "tf": "1d"}),                                   # watch なし → 外す
    ]
    days = [f"2026-09-{d:02d}" for d in range(20, 31)] + [f"2026-10-{d:02d}" for d in range(1, 9)]
    data = [_sig(d) for d in days]                     # 下降中の BB 下限タッチ買い（4時間足）を毎日1件
    after = sum(1 for d in days if d >= "2026-09-27")   # 登録の日（期間の始まり）以降の件数
    tmp = tempfile.mkdtemp()
    path = os.path.join(tmp, "signal-lab-tracker.json")
    try:
        _morning_update(hyps, data, "2026-10-10", path)
        by = {h["id"]: h for h in json.load(open(path, encoding="utf-8"))["hypotheses"]}
        w = G.load_watch_hypotheses(path)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    # 更新は状態の「戻し」も watch の「消し」もしない
    assert [by[i]["status"] for i in ("dip__flip", "bb_lower_4h", "rsi_oversold_4h", "rej", "gate", "plain")] == \
        ["tracking", "tracking", "retired", "rejected", "tracking", "tracking"]
    assert all(by[i]["watch"] is True for i in ("dip__flip", "bb_lower_4h", "rsi_oversold_4h", "rej", "gate"))
    # 選ばれるのは蓄積中の勝ち筋で watch=True のものだけ
    assert sorted(h["id"] for h in w) == ["bb_lower_4h", "dip__flip"], [h["id"] for h in w]
    for h in w:
        assert h["watch"] is True and h["status"] == "tracking" and h["kind"] == "edge"
        assert "fired_from" not in h["filter"] and "fired_before" not in h["filter"]   # 照合用は期間の条件を外す（live_filter）
    assert by["dip__flip"]["filter"]["fired_from"] == "2026-09-27"   # tracker の側は期間の条件を持ったまま（数え方は変えない）
    # 外したあとでも今のシグナルに当たる＝メールの本文は更新後の前向きの件数を出す
    flip = next(h for h in w if h["id"] == "dip__flip")
    assert G.match_promoted_hypothesis([flip], _probe(signal="bb_lower_touch"))["id"] == "dip__flip"
    assert flip["forward"]["n"] == after == 12
    assert f"登録後（2026-09-27〜）: {after}件" in G.watch_email_header(flip)


def test_default_registration_marks_only_the_two_dip_buy_candidates():
    """watch=True を付けて登録するのは押し目買いの2本だけ（2026-09-26 のオーナー決定＝約2.1通/日。
    環境ランク good には付けない）。本物の tracker ではなく、空の状態からコードの登録だけで確かめる。"""
    tmp = tempfile.mkdtemp()
    path = os.path.join(tmp, "signal-lab-tracker.json")   # まだ無い＝初期の仮説＋既定の登録から始まる
    try:
        _morning_update(None, [], "2026-09-26", path)
        w = G.load_watch_hypotheses(path)
    finally:
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
