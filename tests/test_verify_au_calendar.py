# -*- coding: utf-8 -*-
"""豪州の発表日の見張り（verify_au_calendar.py）のテスト。2026-11-12 新設。通信しない（ページの文字は作り物）。

ここで固定すること：
  - 豪中銀の日程は「2日間の会合の2日目」を発表日として読む。1日だけの会合（決済システム）は拾わない
  - 豪統計局の「Next Release 日/月/年」をぜんぶ読む（日と月を取り違えない）
  - 公式に無い日付を載せていたら問題・近い発表（21日以内）が台帳に無ければ問題・先の未登録は知らせるだけ
  - ワークフローは3本（米・英ユーロ圏・豪）を1ステップで回し、どれか1本でも落ちたら落ちる

実行:  python tests/test_verify_au_calendar.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import verify_au_calendar as V  # noqa: E402

D = dt.date
RBA_TEXT = """Board Meeting Schedules
Meeting schedules
Board meeting schedules 2026
Month
Monetary Policy Board
Payments System Board
January
February
2&ndash;3 February
March
16&ndash;17 March
5 March
November
2–3 November
19 November
December
7-8 December
Board meeting schedules 2027
February
8&ndash;9 February
24 February
March
31 March&ndash;1 April
Related Information"""
ABS_TEXT = """Reference period September 2026
Released 15/10/2026
Future releases Next Release 19/11/2026
Labour Force, Australia, October 2026
Next Release 17/12/2026
Labour Force, Australia, November 2026
Next Release 6/01/2027
Labour Force, Australia, December 2026
View all releases
Release date and time 15/10/2026 11:30am AEDT"""


def test_parse_rba_second_day_only():
    got = V.parse_rba(RBA_TEXT)
    assert got == [D(2026, 2, 3), D(2026, 3, 17), D(2026, 11, 3), D(2026, 12, 8), D(2027, 2, 9), D(2027, 4, 1)], got
    assert D(2026, 3, 5) not in got and D(2026, 11, 19) not in got        # 1日だけの会合（決済システム）は拾わない
    assert V.parse_rba("2&ndash;3 February") == []                          # 年の見出しが無ければ読まない（年を推測しない）


def test_parse_abs_day_month_year():
    got = V.parse_abs_next(ABS_TEXT)
    assert got == [D(2026, 11, 19), D(2026, 12, 17), D(2027, 1, 6)], got    # 6/01/2027 は 1月6日（6月1日ではない）
    assert D(2026, 10, 15) not in got                                       # 「Released」「Release date and time」は拾わない
    assert V.parse_abs_next("Next Release 31/02/2027") == []                # ありえない日付は捨てる


def _run(found, js, ms, today):
    problems, notes = [], []
    V.judge("豪雇用統計", found, set(js), set(ms), today, problems, notes)
    return problems, notes


def test_judge_match_and_far_missing_is_note():
    today = D(2026, 11, 12)
    found = [D(2026, 11, 19), D(2026, 12, 17), D(2027, 1, 21)]
    problems, notes = _run(found, [D(2026, 11, 19), D(2026, 12, 17)], [D(2026, 11, 19), D(2026, 12, 17)], today)
    # 70日先の未登録は知らせるだけ。台帳と元の表（翌年の ECONOMIC_EVENTS_2027）の両方について知らせる
    # （2026-11-12 まで元の表は 2026年の日付しか見ず、翌年の抜けを知らせなかった）
    assert problems == [] and len(notes) == 2 and all("2027-01-21" in n for n in notes), notes
    assert notes[0].startswith("economic-events.json") and notes[1].startswith("ECONOMIC_EVENTS_2027")


def test_judge_wrong_date_is_problem():
    today = D(2026, 11, 12)
    found = [D(2026, 11, 19), D(2026, 12, 17), D(2027, 1, 21)]
    # 12/17 を 12/16 と載せた（曜日からの推測で1日ずらした、という事故の形）
    problems, notes = _run(found, [D(2026, 11, 19), D(2026, 12, 16)], [D(2026, 11, 19), D(2026, 12, 16)], today)
    assert any("2026-12-16" in p and "公式の日程に無い" in p and "economic-events.json" in p for p in problems)
    assert any("2026-12-16" in p and "ECONOMIC_EVENTS_2026" in p for p in problems)
    assert any("2026-12-17" in n for n in notes)                            # 正しい日は「未登録」として出る
    # 過ぎた日付と、公式がまだ出していない先の日付は食い違いにしない
    problems, _ = _run(found, [D(2026, 10, 15), D(2026, 11, 19), D(2026, 12, 17), D(2027, 2, 18)], [], today)
    assert problems == [], problems


def test_judge_near_missing_is_problem():
    today = D(2026, 11, 12)
    found = [D(2026, 11, 19), D(2026, 12, 17)]
    problems, notes = _run(found, [], [D(2026, 11, 19), D(2026, 12, 17)], today)
    assert len(problems) == 1 and "2026-11-19" in problems[0] and "未登録" in problems[0] and "あと7日" in problems[0]
    assert any("2026-12-17" in n for n in notes)                            # 35日先は知らせるだけ
    assert V.NEAR == 21
    # ちょうど 21日先は問題・22日先は知らせるだけ
    p1, _ = _run([today + dt.timedelta(days=21)], [], [], today)
    p2, n2 = _run([today + dt.timedelta(days=22)], [], [], today)
    assert len(p1) == 1 and p2 == [] and len(n2) >= 1


def test_judge_nothing_readable_is_problem():
    problems, _ = _run([D(2026, 10, 15)], [D(2026, 10, 15)], [], D(2026, 11, 12))   # 公式側に今日以降が1件も無い
    assert len(problems) == 1 and "1件も読み取れない" in problems[0]


def test_workflow_runs_all_three():
    yml = open(os.path.join(ROOT, ".github", "workflows", "verify-calendar.yml"), encoding="utf-8").read()
    step = yml[yml.index("python verify_economic_calendar.py"):yml.index("- name: Open or update issue on failure")]
    assert "python verify_uk_eu_calendar.py | tee -a calendar_verify_report.txt" in step
    assert "python verify_au_calendar.py | tee -a calendar_verify_report.txt" in step
    assert "au=$?" in step and "[ $us -eq 0 ] && [ $ukeu -eq 0 ] && [ $au -eq 0 ]" in step      # どれか1本でも落ちたら落ちる
    assert "set -o pipefail" in yml                                         # tee が失敗を隠さない
    src = open(os.path.join(ROOT, "verify_au_calendar.py"), encoding="utf-8").read()
    assert "rba.gov.au/schedules-events/board-meeting-schedules.html" in src and src.count("abs.gov.au/statistics/") == 2
    for kind in ("豪中銀", "^豪雇用統計", "^豪CPI"):                         # カレンダーの決まり（RULES）と同じ名前で突き合わせる
        assert kind in src
    import sync_economic_events as S
    for name, pat in (("豪中銀 政策金利発表（RBA）", V.RBA_PATTERN), ("豪雇用統計（10月分）", V.ABS_SOURCES[0][2]), ("豪CPI（10月分）", V.ABS_SOURCES[1][2])):
        import re
        assert re.search(pat, name) and S.match_rule(name)["country"] == "AU"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok", name)
