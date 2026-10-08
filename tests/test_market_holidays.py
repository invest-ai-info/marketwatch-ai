# -*- coding: utf-8 -*-
"""市場休場の表（generate_market_holidays.py）のテスト。2026-10-09 新設（表のコメントが「このテストが見張る」と書いていたのに
ファイルが無かった）。同日 オーナー「2028年分の東証の休日日も今のうちに足しておいてください」。

確かめること＝①東証の休場は平日だけ・重なりなし・年ごとの件数 ②2028 年の祝日を曜日の決まりから計算し直して表と一致
（第2・第3月曜・日曜の祝日が無い＝振替なし・挟まれた平日が無い＝国民の休日なし）③取り下げた日（RETRACTED）は表に無く、
実行のたびに economic-events.json から外れる ④朝のメールの東証の休みの判定（morning_brief.tse_closed）が 2028 年の祝日を休みと見る
⑤月次のワークフローの「休場の補充だけ」の入力（指標・決算・メールを飛ばす）。

実行:  python tests/test_market_holidays.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import generate_market_holidays as G  # noqa: E402
import morning_brief as B  # noqa: E402


def _jp(year):
    return [dt.date.fromisoformat(d) for d, _, _ in G.JP_HOLIDAYS if d.startswith(str(year))]


def _nth_monday(y, m, n):
    d = dt.date(y, m, 1)
    d += dt.timedelta(days=(7 - d.weekday()) % 7)
    return d + dt.timedelta(weeks=n - 1)


def test_jp_weekdays_unique_and_counts():
    days = [dt.date.fromisoformat(d) for d, _, _ in G.JP_HOLIDAYS]
    assert all(d.weekday() < 5 for d in days), [str(d) for d in days if d.weekday() >= 5]
    assert len(days) == len(set(days))
    assert (len(_jp(2026)), len(_jp(2027)), len(_jp(2028))) == (19, 17, 15)


def test_jp_2028_matches_the_holiday_rules():
    y = 2028
    fixed = [(1, 1), (2, 11), (2, 23), (4, 29), (5, 3), (5, 4), (5, 5), (8, 11), (11, 3), (11, 23)]
    hol = {dt.date(y, m, d) for m, d in fixed} | {_nth_monday(y, 1, 2), _nth_monday(y, 7, 3), _nth_monday(y, 9, 3),
                                                 _nth_monday(y, 10, 2), dt.date(y, 3, 20), dt.date(y, 9, 22)}
    assert not [d for d in hol if d.weekday() == 6]                                   # 日曜の祝日なし＝振替休日なし
    s = sorted(hol)
    assert not [a for a, b in zip(s, s[1:]) if (b - a).days == 2]                     # 祝日に挟まれた平日なし＝国民の休日なし
    tse = {d for d in hol if d.weekday() < 5} | {dt.date(y, 1, 3)}                    # 年始 1/1〜1/3（1/3 が月曜）
    assert set(_jp(y)) == tse
    assert (_nth_monday(y, 1, 2), _nth_monday(y, 7, 3), _nth_monday(y, 9, 3), _nth_monday(y, 10, 2)) == \
           (dt.date(y, 1, 10), dt.date(y, 7, 17), dt.date(y, 9, 18), dt.date(y, 10, 9))
    notes = {d: n for d, _, n in G.JP_HOLIDAYS}
    assert "官報で確定" in notes["2028-03-20"] and "官報で確定" in notes["2028-09-22"]      # 春分・秋分は 2027年2月に確かめる


def test_retracted_are_removed_and_not_listed():
    listed = {(c, d) for c, rows in (("JP", G.JP_HOLIDAYS), ("US", G.US_HOLIDAYS), ("UK", G.UK_HOLIDAYS)) for d, _, _ in rows}
    assert not [r for r in G.RETRACTED if (r["country"], r["date"]) in listed]
    ev = [{"category": "market_holiday", "country": "JP", "datetime": "2027-01-04T09:00:00+09:00"},
          {"category": "indicator", "country": "JP", "datetime": "2027-01-04T08:50:00+09:00"},
          {"category": "market_holiday", "country": "JP", "datetime": "2027-01-11T09:00:00+09:00"}]
    kept, removed = G.prune_retracted(ev)
    assert len(kept) == 2 and len(removed) == 1 and removed[0]["datetime"].startswith("2027-01-04")


def test_morning_mail_sees_2028_holidays():
    events = [G.build_event(d, n, note, "JP", ["NKD=F"]) for d, n, note in G.JP_HOLIDAYS]
    p = os.path.join(tempfile.mkdtemp(), "ev.json")
    json.dump({"events": events}, open(p, "w", encoding="utf-8"), ensure_ascii=False)
    for d in _jp(2028):
        assert B.tse_closed(d, p), d
    assert not B.tse_closed(dt.date(2028, 1, 4), p) and not B.tse_closed(dt.date(2027, 1, 4), p)   # 大発会
    assert B.prev_session(dt.date(2028, 5, 8), p) == dt.date(2028, 5, 2)                            # GW（5/3〜5/7）明け
    assert B.week_first_session(dt.date(2028, 7, 18), p)                                            # 海の日の週は火曜


def test_workflow_holidays_only_input():
    wf = open(".github/workflows/monthly-calendar-reminder.yml", encoding="utf-8").read()
    assert "holidays_only:" in wf and "type: boolean" in wf
    assert wf.count("if: ${{ !inputs.holidays_only }}") == 3                         # 指標・決算・メールを飛ばす（休場の補充と commit は回る）
    assert "run: python generate_market_holidays.py" in wf and "git add economic-events.json" in wf


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"✅ {name}")
            except AssertionError as e:
                fails += 1
                print(f"❌ {name}: {e}")
    sys.exit(1 if fails else 0)
