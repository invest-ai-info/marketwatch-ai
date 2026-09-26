# -*- coding: utf-8 -*-
"""前向きトラッカーの「拾い損ね防止」「全体との差」のテスト。2026-09-26 新設（オーナー決定「成績を上げる」の①②）。

① 却下が決まった仮説は、逆向き（gate→edge／edge→gate）で翌日以降の発火だけを数える形に自動で登録し直す
② 同じ時期・同じ向き（・同じ時間足）の全体との差を記録し、新しい昇格はその差の向きも条件にする

実行:  python tests/test_tracker_focus.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import signal_lab_tracker as T  # noqa: E402


def _sig(day, signal, long=True, outcome="tp1", tf="4h"):
    return {"fired_at": f"{day}T10:00:00+09:00", "primary_signal": signal, "outcome": outcome, "timeframe": tf,
            "direction": "ロング（買い）" if long else "ショート（売り）", "ticker": "GC=F"}


def _days(n, start="2026-07-01"):
    d0 = dt.date.fromisoformat(start)
    return [(d0 + dt.timedelta(days=i)).isoformat() for i in range(n)]


def _run(hyps, data, today="2026-09-26"):
    """一時ファイルのトラッカーで cmd_update を1回まわし、結果の仮説一覧を返す（既定の登録は足さない）"""
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    json.dump({"updated_at": None, "hypotheses": hyps}, open(path, "w", encoding="utf-8"), ensure_ascii=False)
    orig_path, orig_boot = T.TRACKER, T.apply_holdout_bootstrap
    T.TRACKER, T.apply_holdout_bootstrap = path, (lambda t: 0)
    try:
        T.cmd_update(None, data, today)
        return json.load(open(path, encoding="utf-8"))["hypotheses"]
    finally:
        T.TRACKER, T.apply_holdout_bootstrap = orig_path, orig_boot
        os.remove(path)


def test_baseline_filter_direction_and_window():
    f = T.baseline_filter({"signal": "x", "tf": "4h", "fired_from": "2026-09-27", "group": "metal"})
    assert f == {"tf": "4h", "fired_from": "2026-09-27"}          # 銘柄の群・合図は相手に入れない
    assert T.baseline_filter({"direction": "short"})["direction"] == "short"
    assert T.baseline_filter({"reversal_long": True})["direction"] == "long"
    longs = [{"direction": "ロング"}] * 19 + [{"direction": "ショート"}]
    assert T.baseline_filter({"signal": "x"}, longs)["direction"] == "long"   # 95%以上が買い
    mixed = [{"direction": "ロング"}] * 10 + [{"direction": "ショート"}] * 10
    assert "direction" not in T.baseline_filter({"signal": "x"}, mixed)


def test_beats_baseline():
    assert T.beats_baseline("edge", {"excess": 0.05}) and not T.beats_baseline("edge", {"excess": 0.0})
    assert T.beats_baseline("gate", {"excess": -0.05}) and not T.beats_baseline("gate", {"excess": 0.01})
    assert not T.beats_baseline("edge", {"excess": None}) and not T.beats_baseline("edge", None)


def test_make_flip_gate_to_edge_and_back():
    fwd = {"n": 100, "avgR": 0.2, "rci_lo": 0.05, "rci_hi": 0.35}
    g = {"id": "g1", "label": "BB下限タッチ(回避)", "kind": "gate", "filter": {"signal": "bb", "fired_before": "2026-09-01"},
         "registered_at": "2026-06-25"}
    fl = T.make_flip(g, fwd, "2026-09-26")
    assert fl["id"] == "g1__flip" and fl["kind"] == "edge" and fl["registered_at"] == "2026-09-27"
    assert fl["filter"] == {"signal": "bb", "fired_from": "2026-09-27"}      # 古い期間の条件は外し、翌日以降だけ
    assert "(回避)" not in fl["label"] and "逆向きで再登録" in fl["label"]
    assert fl["flipped_from"] == "g1" and fl["flip_evidence"]["avgR"] == 0.2
    e = dict(g, id="e1", kind="edge", label="何かの買い")
    assert T.make_flip(e, fwd, "2026-09-26")["kind"] == "gate"
    assert "(回避)" in T.make_flip(e, fwd, "2026-09-26")["label"]


def test_rejected_gate_is_flipped_once():
    # 「避けるはず」の合図が、前向きで逆にはっきり勝っている（80件で判定点に届く）
    data = [_sig(d, "bb_lower_touch", outcome="tp1" if i % 4 else "sl")
            for i, d in enumerate(_days(90, start="2026-06-26"))]          # 6/26〜9/23（翌日以降のデータは無い）
    hyps = [{"id": "g1", "label": "BB下限タッチ(回避)", "kind": "gate", "filter": {"signal": "bb_lower_touch"},
             "registered_at": "2026-06-25"}]
    out = _run(hyps, data)
    by = {h["id"]: h for h in out}
    assert by["g1"]["status"] == "rejected"
    fl = by["g1__flip"]
    assert fl["kind"] == "edge" and fl["status"] == "tracking" and fl["filter"]["fired_from"] == "2026-09-27"
    assert fl["forward"]["n"] == 0                       # 却下に使ったデータは数えない
    again = _run(out, data)                              # 2回目：却下はそのまま・二重登録しない
    assert sum(1 for h in again if h["id"] == "g1__flip") == 1


def test_promotion_needs_to_beat_the_same_side_baseline():
    # 買い全体が勝っている時期＝「買いならどれでも勝つ」。買い全体そのものは昇格しない
    data = [_sig(d, "macd_golden") for d in _days(90)]
    out = _run([{"id": "e1", "label": "買い全体", "kind": "edge", "filter": {"direction": "long"},
                 "registered_at": "2026-06-25"}], data)
    h = out[0]
    assert h["status"] == "tracking" and h.get("promote_block") == "below_baseline"
    assert h["baseline"]["excess"] == 0.0 and not h.get("promote_strikes")


def test_promotion_counts_when_it_beats_the_baseline():
    # 同じ時期の買い全体は負け越し、その中の1つの合図だけが勝っている＝差がプラス→昇格の1回目に数える
    days = _days(90)
    data = [_sig(d, "rsi_oversold_bounce") for d in days] + [_sig(d, "macd_golden", outcome="sl") for d in days] * 2
    out = _run([{"id": "e2", "label": "売られすぎ買い", "kind": "edge", "filter": {"signal": "rsi_oversold_bounce"},
                 "registered_at": "2026-06-25"}], data)
    h = out[0]
    assert h["baseline"]["filter"] == {"direction": "long"} and h["baseline"]["excess"] > 0
    assert h.get("promote_strikes") == 1 and h["status"] == "tracking"      # 昇格は2回連続で確定（従来どおり）


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
