# -*- coding: utf-8 -*-
"""見張り番（check_automation_health）の②研究日誌と⑤シリーズの終わりのテスト。2026-10-18 新設。

きっかけ:
- ②研究日誌は drafts/REVIEW.md の鮮度で見ていた。日誌の予約は REVIEW.md を毎回は書かず、新刊ウォッチも
  同じファイルを書き換えるので、10/16・10/17 に日誌が2日止まったのに緑のままだった
  → いちばん新しい号の guide-signal-lab-NNN.html が足された日時で見る
- ⑤エントリー方法の研究は全25回＋総まとめで完結する設計なのに、残り2本（#25 と総まとめ）で
  「キュー補充が必要」と鳴った → 残りに総まとめが入っていれば「完結の手前」として補充を求めない

固定すること: 番号は数字で比べる（999 → 1000 で崩れない）／番号でない名前は無視／
シリーズの終わりは鳴らさない（ending）・総まとめまで出たら完結（done）・総まとめの無いキューは従来どおり。

実行:  python tests/test_health_series_watch.py     （pytest 不要。pytest でも動く）
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import check_automation_health as H  # noqa: E402

PAT = "guide-signal-lab-*.html"


# ── ② 研究日誌は、いちばん新しい号で見る
def test_latest_numbered_picks_the_biggest_number():
    names = ["guide-signal-lab-125.html", "guide-signal-lab-127.html", "guide-signal-lab-126.html",
             "guides.html", "guide-news-2026-10-17.html"]
    assert H.latest_numbered(names, PAT) == "guide-signal-lab-127.html"


def test_latest_numbered_compares_as_numbers_not_text():
    # 文字で比べると "999" > "1000" になってしまう
    assert H.latest_numbered(["guide-signal-lab-999.html", "guide-signal-lab-1000.html"], PAT) \
        == "guide-signal-lab-1000.html"


def test_latest_numbered_ignores_names_that_are_not_numbers():
    names = ["guide-signal-lab-series-index.html", "guide-signal-lab-012.html"]
    assert H.latest_numbered(names, PAT) == "guide-signal-lab-012.html"


def test_latest_numbered_none_when_nothing_matches():
    assert H.latest_numbered(["guides.html"], PAT) is None


def test_journal_row_no_longer_watches_review_md():
    rows = {label: path for label, path, _h, _s in H.ROUTINE_FILE_CHECKS}
    assert rows["研究日誌・日次研究会"] == PAT


# ── ②b ブリーフィングは1日2回（06:00・15:00 JST）を回数で見る
import datetime as _dt  # noqa: E402


def _utc(s):
    return _dt.datetime.fromisoformat(s).replace(tzinfo=_dt.timezone.utc)


def test_both_runs_present_is_ok():
    # 10/12 15:12 JST と 10/13 06:18 JST（UTC で書く）→ 10/13 09:30 JST に見る
    dates = ["2026-10-12T06:12:00Z", "2026-10-12T21:18:00Z"]
    ok, _ = H.eval_run_count(dates, _utc("2026-10-13T00:30:00"), 26, 2)
    assert ok


def test_missing_afternoon_run_is_caught():
    # 10/15 の実際の形＝前の日の 15:00 の回が無く、朝の回だけ（鮮度15hの行は緑だった）
    dates = ["2026-10-14T21:15:00Z", "2026-10-13T21:15:00Z"]
    now = _utc("2026-10-15T04:50:00")   # 実際の見張りの時刻（13:50 JST ごろ）
    ok, note = H.eval_run_count(dates, now, 26, 2)
    assert not ok and "1 回" in note
    ok15, _ = H.age_hours(dates[0], now) <= 15, None
    assert ok15   # 旧来の鮮度だけでは見逃す＝この行が要る理由


def test_count_works_late_in_the_day_too():
    # 15:00 の回のあとに見ても（見張りが遅れても）2回以上入る
    dates = ["2026-10-13T06:13:00Z", "2026-10-13T21:14:00Z", "2026-10-14T06:12:00Z"]
    ok, _ = H.eval_run_count(dates, _utc("2026-10-14T08:00:00"), 26, 2)
    assert ok


def test_briefing_count_row_is_registered():
    rows = {path: (w, n) for _l, path, w, n, _s in H.ROUTINE_COUNT_CHECKS}
    assert rows["fundamental-context.json"] == (26, 2)


# ── ⑮ 作業ブランチへの置き去り
NOW = _utc("2026-10-18T07:00:00")


def test_stranded_briefing_on_work_branch_is_caught():
    # 10/18 15:08 JST の実際の形＝作業ブランチにだけあるブリーフィングのコミット
    br = [("claude/beautiful-johnson-686hbu",
           [("2026-10-18T06:08:40Z", "chore: update fundamental-context.json (daily briefing)")])]
    hits = H.stranded_commits(br, NOW)
    assert len(hits) == 1 and hits[0][0] == "claude/beautiful-johnson-686hbu"


def test_stranded_journal_publish_is_caught():
    br = [("claude/relaxed-galileo-5dcczh",
           [("2026-10-17T21:40:00Z", "feat: publish guide-signal-lab-124 (エーディーエックス強×順張り FWD定点観測)")])]
    assert H.stranded_commits(br, NOW)


def test_human_pr_branch_is_not_flagged():
    # 人のセッションの PR 作業（main にまだ無いのが正常）は鳴らさない。題名が routine に似ていても PR があれば除く
    br = [("claude/vigilant-cray-nd5fzq",
           [("2026-10-17T06:00:00Z", "研究日誌の予約が朝に止まる件：トラッカー表を短くする")])]
    assert H.stranded_commits(br, NOW) != []
    assert H.stranded_commits(br, NOW, with_pr={"claude/vigilant-cray-nd5fzq"}) == []


def test_plain_human_commit_title_is_not_flagged():
    br = [("claude/new-session-tk0m8z", [("2026-10-18T06:00:00Z", "J10b: 朝の板を20件記録")])]
    assert H.stranded_commits(br, NOW) == []


def test_old_stranded_commit_is_outside_the_window():
    br = [("claude/beautiful-johnson-l3svna",
           [("2026-10-16T06:12:00Z", "chore: update fundamental-context.json (daily briefing)")])]
    assert H.stranded_commits(br, NOW) == []


def test_non_claude_branch_is_ignored():
    br = [("signal-lab-pending-20261018", [("2026-10-18T06:00:00Z", "feat: auto-publish signal-lab 128")])]
    assert H.stranded_commits(br, NOW) == []


# ── ⑤ シリーズの終わり
ENTRY = [f"t{i}" for i in range(1, 25)] + ["publication-decay", "series-index"]


def test_series_ending_is_not_a_refill_alarm():
    # 10/18 の実際の形＝残りは #25 と総まとめ・床3
    assert H.queue_state(ENTRY, ["publication-decay", "series-index"], [], 3) == "ending"
    assert H.queue_state(ENTRY, ["series-index"], [], 3) == "ending"


def test_series_done_after_the_finale_is_published():
    assert H.queue_state(ENTRY, [], [], 3) == "done"


def test_finale_escalated_is_not_done():
    # 総まとめが台帳に載って止まっている（エスカレ）＝完結ではない
    assert H.queue_state(ENTRY, [], ["series-index"], 3) == "low"


def test_queue_without_finale_keeps_the_old_alarm():
    keys = ["a", "b", "c", "d"]
    assert H.queue_state(keys, ["d"], [], 3) == "low"
    assert H.queue_state(keys, [], [], 3) == "low"


def test_enough_left_is_ok():
    assert H.queue_state(ENTRY, ENTRY[-5:], [], 3) == "ok"


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
