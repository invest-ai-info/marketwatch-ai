# -*- coding: utf-8 -*-
"""evaluate_signal_outcomes.py の「失敗した敗因・勝因分析のやり直し」（--retry-failed-ai）のテスト。2026-10-24 新設。

きっかけ:
- Gemini（AI Studio）の前払いクレジットが 10/20 夜に尽き、その間に決着したシグナルの分析が
  {"error": "AI 分析失敗"} のまま残った（10/24 時点で敗因50件・勝因24件）。分析は決着した瞬間に1回だけで、
  後から直す道が無かった

固定すること:
- 対象（ai_retry_targets）＝ai_result に "error" がある欄だけ・outcome に合う欄だけ（sl→敗因・tp1/tp2→勝因）・
  決着の古い順（時差の違う時刻が混じっても）。成功した分・JSON が読めなかった raw_response は触らない
- 差し替え（apply_ai_retry）＝primary_category のある結果だけ。失敗なら entry は1文字も変えない
- 回し方（retry_failed_ai）＝上限件数を守る・続けて5件失敗したら打ち切る・1件の例外で止めない・
  VIX は残っていれば使い回す（無いものだけ取り直す）・ニュースは残っている見出しだけ訳し直す
- track-record.html の勝因・敗因の集計が、やり直したあとの値で出る（「未分類」から正しいカテゴリへ）

実行:  python tests/test_retry_failed_ai.py     （pytest 不要。pytest でも動く）
"""
import copy
import os
import sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import evaluate_signal_outcomes as E  # noqa: E402
import generate_track_record_page as G  # noqa: E402

JST = timezone(timedelta(hours=9))
NOW = datetime(2026, 10, 25, 9, 0, tzinfo=JST)
FAIL = {"error": "AI 分析失敗"}
VIX = {"start": 16.72, "end": 18.03, "change_pct": 7.83}
GOOD_LOSS = {"primary_category": "ボラ拡大", "primary_cause": "指標で急変", "ai_diagnosis": "発表で値が飛んだ",
             "lesson": "教訓L：次は指標前に入らない", "category_tag": "ボラ爆発"}
GOOD_WIN = {"primary_category": "トレンド継続", "primary_cause": "上位足と同じ向き", "ai_diagnosis": "流れに乗れた",
            "lesson": "教訓W：同じ条件ならサイズを上げる", "category_tag": "順張り", "repeatable": "medium"}


def _sig(sid, outcome="sl", resolved="2026-10-21T10:00:00+09:00", ai=None, key=None, vix=VIX, news=None,
         direction="ロング（買い）"):
    """決着したシグナル1件。ai を渡すと outcome に合う欄（または key の欄）に分析を入れる"""
    e = {"id": sid, "ticker": "USDJPY=X", "asset_name": "ドル円", "timeframe": "4h",
         "fired_at": "2026-10-20T09:30:00+09:00", "direction": direction,
         "entry": 150.0, "stop_loss": 149.5, "take_profit_1": 150.7, "take_profit_2": 151.0, "atr": 0.33,
         "outcome": outcome, "outcome_resolved_at": resolved}
    if ai is not None:
        e[key or E._ANALYSIS_KEY[outcome]] = {"vix_data": vix, "news_during_holding": list(news or []), "ai_result": ai}
    return e


class _patch:
    """E の関数を一時的に差し替える（Gemini と yfinance を呼ばない）"""

    def __init__(self, **fns):
        self.fns, self.old = fns, {}

    def __enter__(self):
        for k, v in self.fns.items():
            self.old[k] = getattr(E, k)
            setattr(E, k, v)
        return self

    def __exit__(self, *a):
        for k, v in self.old.items():
            setattr(E, k, v)


def _fakes(loss=lambda e: GOOD_LOSS, win=lambda e: GOOD_WIN, calls=None):
    calls = calls if calls is not None else {}

    def _count(name):
        calls[name] = calls.get(name, 0) + 1

    def vix(start_utc, end_iso):
        _count("vix")
        return {"start": 20.0, "end": 21.0, "change_pct": 5.0}

    def translate(titles, key):
        _count("translate")
        return [f"訳:{t}" for t in titles]

    def analyze_loss(entry, ts, news, vix_data, key):
        _count("loss")
        r = loss(entry)
        if isinstance(r, Exception):
            raise r
        return copy.deepcopy(r)

    def analyze_win(entry, ts, label, news, vix_data, key):
        _count("win")
        assert label == entry["outcome"]
        return copy.deepcopy(win(entry))

    return dict(get_vix_change=vix, translate_titles_to_jp_quick=translate,
                analyze_loss_with_ai=analyze_loss, analyze_win_with_ai=analyze_win), calls


# ── 対象の選び方（純関数）
def test_targets_are_only_error_fields_matching_outcome():
    log = [
        _sig("ok_loss", ai=GOOD_LOSS),
        _sig("raw", ai={"raw_response": "{壊れた JSON"}),
        _sig("fail_sl", ai=FAIL),
        _sig("fail_tp1", outcome="tp1", ai=FAIL),
        _sig("fail_tp2", outcome="tp2", ai=FAIL),
        _sig("mismatch", outcome="sl", ai=FAIL, key="win_analysis"),   # 欄が outcome と合わない
        _sig("no_plan", ai=FAIL, direction=None),
        _sig("no_resolved", ai=FAIL, resolved=None),
        _sig("expired", outcome="expired"),
        _sig("never_analyzed"),                                        # GEMINI_API_KEY 無しで分析しなかった分
    ]
    got = [(e["id"], k) for e, k in E.ai_retry_targets(log)]
    assert sorted(got) == sorted([("fail_sl", "loss_analysis"), ("fail_tp1", "win_analysis"),
                                  ("fail_tp2", "win_analysis")]), got


def test_targets_are_oldest_first_across_time_zones():
    # +01:00 の 15:00（UTC 14:00）より +09:00 の 22:00（UTC 13:00）が先
    log = [_sig("b", resolved="2026-10-20T15:00:00+01:00", ai=FAIL),
           _sig("c", resolved="2026-10-22T08:00:00+09:00", ai=FAIL),
           _sig("a", resolved="2026-10-20T22:00:00+09:00", ai=FAIL)]
    assert [e["id"] for e, _ in E.ai_retry_targets(log)] == ["a", "b", "c"]


# ── 差し替え（純関数）
def test_apply_keeps_entry_untouched_on_failure():
    for bad in (None, {"error": "AI 分析失敗"}, {"raw_response": "x"}, {}, "文字列", {"primary_category": ""}):
        e = _sig("s", ai=FAIL, news=["Fed holds"])
        before = copy.deepcopy(e)
        assert E.apply_ai_retry(e, "loss_analysis", bad, ["訳"], VIX, NOW) is False, bad
        assert e == before, bad


def test_apply_replaces_only_the_analysis_field():
    e = _sig("s", ai=FAIL, news=["Fed holds"])
    before = copy.deepcopy(e)
    assert E.apply_ai_retry(e, "loss_analysis", dict(GOOD_LOSS), ["FRB 据え置き"], VIX, NOW) is True
    assert e["loss_analysis"] == {"vix_data": VIX, "news_during_holding": ["FRB 据え置き"],
                                  "ai_result": GOOD_LOSS, "retried_at": "2026-10-25T09:00:00+09:00"}, e
    rest = {k: v for k, v in e.items() if k != "loss_analysis"}
    assert rest == {k: v for k, v in before.items() if k != "loss_analysis"}


# ── 回し方（Gemini・yfinance は差し替え）
def test_retry_replaces_successes_and_keeps_failures():
    log = [_sig("l1", ai=FAIL, resolved="2026-10-21T01:00:00+09:00"),
           _sig("w1", outcome="tp1", ai=FAIL, resolved="2026-10-21T02:00:00+09:00"),
           _sig("l2", ai=FAIL, resolved="2026-10-21T03:00:00+09:00")]
    fakes, calls = _fakes(loss=lambda e: None if e["id"] == "l2" else GOOD_LOSS)
    with _patch(**fakes):
        n, tried, done = E.retry_failed_ai(log, "key", NOW)
    assert (n, tried, done) == (3, 3, 2)
    assert log[0]["loss_analysis"]["ai_result"] == GOOD_LOSS and "retried_at" in log[0]["loss_analysis"]
    assert log[1]["win_analysis"]["ai_result"] == GOOD_WIN
    assert log[2]["loss_analysis"] == {"vix_data": VIX, "news_during_holding": [], "ai_result": FAIL}
    assert calls == {"loss": 2, "win": 1}, calls          # VIX が残っている・ニュース無し＝取り直しも翻訳もしない
    assert [k for _, k in E.ai_retry_targets(log)] == ["loss_analysis"]   # 次に押せば l2 だけ


def test_retry_respects_limit_oldest_first():
    log = [_sig(f"s{i}", ai=FAIL, resolved=f"2026-10-2{i}T10:00:00+09:00") for i in (3, 1, 2)]
    fakes, _ = _fakes()
    with _patch(**fakes):
        n, tried, done = E.retry_failed_ai(log, "key", NOW, limit=2)
    assert (n, tried, done) == (3, 2, 2)
    assert [e["id"] for e in log if "retried_at" in e["loss_analysis"]] == ["s1", "s2"]


def test_retry_stops_after_consecutive_failures_like_depleted_credits():
    log = [_sig(f"s{i}", ai=FAIL, resolved=f"2026-10-21T0{i}:00:00+09:00") for i in range(8)]
    before = copy.deepcopy(log)
    fakes, calls = _fakes(loss=lambda e: None)          # 429 のまま＝analyze_loss_with_ai は None を返す
    with _patch(**fakes):
        n, tried, done = E.retry_failed_ai(log, "key", NOW)
    assert (n, tried, done) == (8, E.RETRY_AI_MAX_CONSECUTIVE_FAIL, 0)
    assert calls["loss"] == E.RETRY_AI_MAX_CONSECUTIVE_FAIL
    assert log == before


def test_retry_success_resets_the_failure_streak():
    # 失敗4・成功1・失敗4 は打ち切らない（続けて5件ではない）
    ids_ok = {"s4"}
    log = [_sig(f"s{i}", ai=FAIL, resolved=f"2026-10-21T0{i}:00:00+09:00") for i in range(9)]
    fakes, _ = _fakes(loss=lambda e: GOOD_LOSS if e["id"] in ids_ok else None)
    with _patch(**fakes):
        n, tried, done = E.retry_failed_ai(log, "key", NOW)
    assert (n, tried, done) == (9, 9, 1)


def test_retry_exception_on_one_entry_does_not_stop_or_corrupt():
    log = [_sig("boom", ai=FAIL, resolved="2026-10-21T01:00:00+09:00"),
           _sig("fine", ai=FAIL, resolved="2026-10-21T02:00:00+09:00")]
    before0 = copy.deepcopy(log[0])
    fakes, _ = _fakes(loss=lambda e: TypeError("atr=None") if e["id"] == "boom" else GOOD_LOSS)
    with _patch(**fakes):
        n, tried, done = E.retry_failed_ai(log, "key", NOW)
    assert (n, tried, done) == (2, 2, 1)
    assert log[0] == before0
    assert log[1]["loss_analysis"]["ai_result"] == GOOD_LOSS


def test_retry_refetches_missing_vix_and_translates_stored_news():
    log = [_sig("novix", ai=FAIL, vix=None, news=["Oil jumps on supply fears"])]
    fakes, calls = _fakes()
    with _patch(**fakes):
        E.retry_failed_ai(log, "key", NOW)
    la = log[0]["loss_analysis"]
    assert la["vix_data"] == {"start": 20.0, "end": 21.0, "change_pct": 5.0}, la
    assert la["news_during_holding"] == ["訳:Oil jumps on supply fears"], la
    assert calls == {"vix": 1, "translate": 1, "loss": 1}, calls


def test_main_retry_exit_codes():
    saved = []
    fakes, _ = _fakes(loss=lambda e: None)
    old_key = os.environ.pop("GEMINI_API_KEY", None)
    try:
        with _patch(load_log=lambda: [_sig("s", ai=FAIL)], save_log=lambda log: saved.append(log), **fakes):
            assert E.main_retry_failed_ai(dry_run=True) == 0          # dry-run は鍵なしでも数えるだけ
            assert E.main_retry_failed_ai() == 1                      # 鍵なし
            os.environ["GEMINI_API_KEY"] = "dummy"
            assert E.main_retry_failed_ai() == 1                      # 試して1件も直らない＝赤
        with _patch(load_log=lambda: [_sig("s", ai=FAIL)], save_log=lambda log: saved.append(log), **_fakes()[0]):
            assert E.main_retry_failed_ai() == 0
        with _patch(load_log=lambda: [_sig("s", ai=GOOD_LOSS)], save_log=lambda log: saved.append(log), **fakes):
            assert E.main_retry_failed_ai() == 0                      # 対象なし
    finally:
        os.environ.pop("GEMINI_API_KEY", None)
        if old_key is not None:
            os.environ["GEMINI_API_KEY"] = old_key
    assert len(saved) == 1, saved                                     # 保存は差し替えたときだけ
    assert saved[0][0]["loss_analysis"]["ai_result"] == GOOD_LOSS


# ── track-record.html の集計（generate_track_record_page.build_outcome_analysis_section）
def test_track_record_counts_follow_the_retried_values():
    log = [_sig("l_ok", ai=dict(GOOD_LOSS, primary_category="テクニカル悪化"), resolved="2026-10-19T10:00:00+09:00"),
           _sig("l_fail", ai=FAIL, resolved="2026-10-21T10:00:00+09:00"),
           _sig("w_fail", outcome="tp1", ai=FAIL, resolved="2026-10-22T10:00:00+09:00")]
    html_before = G.build_outcome_analysis_section(log)
    assert "未分類" in html_before                                     # 失敗した分は「未分類」として数えられていた
    fakes, _ = _fakes()
    with _patch(**fakes):
        E.retry_failed_ai(log, "key", NOW)
    html = G.build_outcome_analysis_section(log)
    assert "未分類" not in html, "やり直したのに未分類が残っている"
    assert "勝因分析（TP1/TP2 到達: 1 件）" in html and "SL ヒット案件: 2 件" in html
    for cat in ("テクニカル悪化", "ボラ拡大", "トレンド継続", "指標で急変", "上位足と同じ向き"):
        assert cat in html, cat
    # AI の「教訓」と「再現性」は公開ページに出さない（2026-09-26 法務チェック）＝やり直した分も同じ
    assert GOOD_LOSS["lesson"] not in html and GOOD_WIN["lesson"] not in html


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
