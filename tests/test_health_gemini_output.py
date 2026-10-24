# -*- coding: utf-8 -*-
"""見張り番（check_automation_health）の⑯「Gemini の出力が空」のテスト。2026-10-24 新設。

きっかけ:
- Gemini（AI Studio）の前払いクレジットが 10/20 夜に尽き、API は全部「429 Your prepayment credits are
  depleted」を返した。各スクリプトは失敗を握り潰して AI の欄を空のまま出すので、ワークフローは全部
  success のまま4日続いた。YouTube 要約は 10/23 にライブで「合計 0 本」、政治発言は英語の見出しのまま
- ①（Actions の成否）では見えない＝出力の中身（generated_at・title_ja）で見る

固定すること:
- YouTube: 要約 0 件は鳴らす／最新の要約が 37h より古ければ鳴らす（実測の最大の空き 31.6h は鳴らさない）／
  saved_at が新しいか古いかで「Gemini 側」か「実行そのものが止まっている」かを書き分ける
- 政治発言: 直近2回の取り込みがどちらも1件も訳されていなければ鳴らす（10/21 朝の実際の並びで鳴る）／
  1回だけの失敗・一部だけの失敗・取り込みが1回しか無いときは鳴らさない

実行:  python tests/test_health_gemini_output.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import check_automation_health as H  # noqa: E402

JST = dt.timezone(dt.timedelta(hours=9))


def at(s):
    return dt.datetime.fromisoformat(s).astimezone(dt.timezone.utc)


def yt(saved, *gens):
    return {"videos": [{"video_id": f"v{i}", "generated_at": g} for i, g in enumerate(gens)],
            "saved_at": saved, "keep_days": 3}


# ── YouTube 要約
def test_youtube_fresh_summary_is_ok():
    ok, note = H.eval_youtube_summary(yt("2026-10-20T16:15:00+09:00", "2026-10-20T16:15:15+09:00"),
                                      at("2026-10-21T09:30:00+09:00"))
    assert ok, note


def test_youtube_zero_videos_like_2026_10_23():
    # 10/23 16:05 の実物＝videos が空・saved_at は新しい（実行は動いている）
    data = {"videos": [], "saved_at": "2026-10-23T16:05:00+09:00", "keep_days": 3}
    ok, note = H.eval_youtube_summary(data, at("2026-10-24T09:30:00+09:00"))
    assert not ok
    assert "0 件" in note and "Gemini 側" in note, note


def test_youtube_stale_summary_while_job_runs():
    # 10/22 朝: 最後の要約は 10/20 16:15（約41h前）・実行は 10/21 16:11 に動いている
    data = yt("2026-10-21T16:11:13+09:00", "2026-10-20T16:15:15+09:00", "2026-10-20T14:30:56+09:00")
    ok, note = H.eval_youtube_summary(data, at("2026-10-22T09:30:00+09:00"))
    assert not ok
    assert "Gemini 側" in note, note


def test_youtube_job_itself_stopped():
    data = yt("2026-10-20T16:15:00+09:00", "2026-10-20T16:15:15+09:00")
    ok, note = H.eval_youtube_summary(data, at("2026-10-22T12:00:00+09:00"))
    assert not ok
    assert "実行そのものが止まっている" in note, note


def test_youtube_longest_observed_gap_does_not_alarm():
    # 実測の最大の空き 31.6h（2026-08-26 12:05 → 08-27 19:44）
    data = yt("2026-08-27T16:00:00+09:00", "2026-08-26T12:05:41+09:00")
    ok, note = H.eval_youtube_summary(data, at("2026-08-27T19:40:00+09:00"))
    assert ok, note


def test_youtube_missing_file_contents():
    ok, _ = H.eval_youtube_summary(None, at("2026-10-24T09:30:00+09:00"))
    assert not ok


# ── 政治発言の日本語化
def pf(*rows):
    return [{"id": f"p{i}", "fetched_at": t, "title_en": "x", "title_ja": ja} for i, (t, ja) in enumerate(rows)]


# 10/21 09:30 JST の時点の並び（実物の fetched_at）
FEED_2026_10_21 = pf(
    ("2026-10-20T00:43:32+09:00", "訳"), ("2026-10-20T00:43:32+09:00", "訳"), ("2026-10-20T00:43:32+09:00", "訳"),
    ("2026-10-20T03:45:42+09:00", "訳"), ("2026-10-20T16:44:46+09:00", "訳"),
    ("2026-10-21T02:21:19+09:00", ""), ("2026-10-21T02:21:19+09:00", ""), ("2026-10-21T06:44:07+09:00", ""),
)


def test_political_depletion_alarms_on_the_first_morning():
    ok, note = H.eval_political_translation(FEED_2026_10_21)
    assert not ok
    assert "3 件" in note and "2026-10-21T06:44" in note, note


def test_political_all_translated_is_ok():
    ok, note = H.eval_political_translation(FEED_2026_10_21[:5])
    assert ok, note


def test_political_single_failed_batch_does_not_alarm():
    # 1回の取り込みでまとめて訳す＝一時的な失敗は1回ぶん（何件あっても）にとどまる
    feed = FEED_2026_10_21[:5] + pf(*[("2026-10-23T06:46:08+09:00", "")] * 4)
    ok, note = H.eval_political_translation(feed)
    assert ok, note


def test_political_partly_translated_does_not_alarm():
    feed = pf(("2026-10-23T05:12:06+09:00", "訳"), ("2026-10-23T05:12:06+09:00", ""),
              ("2026-10-23T06:46:08+09:00", ""))
    ok, note = H.eval_political_translation(feed)
    assert ok, note


def test_political_one_batch_is_not_enough_to_judge():
    ok, note = H.eval_political_translation(pf(("2026-10-21T02:21:19+09:00", ""), ("2026-10-21T02:21:19+09:00", "")))
    assert ok and "判定に足りない" in note, note


def test_political_order_does_not_depend_on_list_order_or_suffix():
    # 新しい順に並んでいても、Z 付きの時刻が混じっても、取り込みの新しさで見る
    feed = pf(("2026-10-21T21:44:07Z", ""), ("2026-10-20T07:44:46Z", "訳"), ("2026-10-21T02:21:19+09:00", " "))
    ok, note = H.eval_political_translation(feed)
    assert not ok, note


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
