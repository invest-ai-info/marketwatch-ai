# -*- coding: utf-8 -*-
"""経済指標カレンダーが年をまたいでも動くことのテスト。2026-11-12 新設。通信しない。

なぜ要るか：発表日の元の表は generate_market_news.py の ECONOMIC_EVENTS_2026 だけで、使う側は
どこも「2026」を直に書いていた（sync_economic_events.py の年の既定・見張り3本・check_site_consistency.py）。
そのまま年が変わると、
  - 12月のカレンダーの「翌月」＝2027年1月の枠に、2026年1月の発表が並ぶ
  - 1月からは economic-events.json に何も足されず、発表前のメール（indicator-alert・indicator-digest）が黙る
    （このメールは 2026-09-17 に発表の直前に建てて損を出したのが作った理由）
  - 見張りは翌年の表を読まないので、翌年の日付の誤りも抜けも知らせない
ここで固定すること：
  - 表は年ごと（ECONOMIC_EVENTS_<年>）で、**表の名前の年がそのまま日付の年**。ある表はぜんぶ読む
  - 12月のうちから翌年1月の発表が台帳に入る・1月になっても前の年の表を今年として読まない
  - カレンダーのページ・トップの予定・見張り3本・点検（mw check）のどこにも年が直に書かれていない

実行:  python tests/test_economic_calendar_year_rollover.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import re
import sys
import warnings

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import sync_economic_events as S  # noqa: E402
import verify_au_calendar as VA  # noqa: E402
import verify_economic_calendar as VUS  # noqa: E402
import verify_uk_eu_calendar as VUK  # noqa: E402

D = dt.date
JST = S.JST
# 作り物の表（年またぎの形だけを持つ小さな見本）。書式は本物と同じ
FAKE = '''
ECONOMIC_EVENTS_2026 = [
    # ── 1月 ──
    (1,  6, "us","mid","ISM非製造業","前の年の1月の行"),
    (1, 15, "us","high","米CPI（12月分）",""),
    # ── 12月 ──
    (12, 4, "us","high","米雇用統計（11月分）",""),
    (12,10, "us","high","米CPI（11月分）",""),
    (12,17, "uk","high","英中銀 政策金利発表（MPC）",""),
    (12,31, "us","high","FOMC（結果発表）","年末の作り物"),
]

ECONOMIC_EVENTS_2027 = [
    (1,  6, "au","mid","豪CPI（11月分）",""),
    (1,  8, "us","high","米雇用統計（12月分）",""),
    (1, 13, "us","high","米CPI（12月分）",""),
    (1, 27, "au","mid","豪CPI（12月分）",""),
    (2,  4, "uk","high","英中銀 政策金利発表（MPC）",""),
    (2,  9, "au","high","豪中銀 政策金利発表（RBA）",""),
    (2, 11, "us","high","米CPI（1月分）",""),
    (2, 30, "us","high","米雇用統計（1月分）","ありえない日付"),
]
'''


def _json_entry(year, month, day, name):
    return S.build_entry(year, month, day, S.match_rule(name), name)


# ── 元の表の読み取り ─────────────────────────────────────────────

def test_tables_are_read_per_year():
    t = S.parse_source_tables(FAKE)
    assert sorted(t) == [2026, 2027] and len(t[2026]) == 6 and len(t[2027]) == 8
    assert t[2027][1] == (1, 8, "us", "high", "米雇用統計（12月分）", "")
    # 表が1つ増えても読む（次の年に同じ直しをしなくてよい）
    t = S.parse_source_tables(FAKE + '\nECONOMIC_EVENTS_2028 = [\n    (1, 7, "us","high","米雇用統計（12月分）",""),\n]\n')
    assert sorted(t) == [2026, 2027, 2028]


def test_real_file_has_both_years_and_nothing_unclassified():
    t = S.load_source_tables()
    assert 2026 in t and 2027 in t, sorted(t)
    for month, day, _c, _imp, name, _desc in t[2027]:
        D(2027, month, day)                                             # ありえない日付が無い
        assert S.match_rule(name) or S.is_known_skip(name), (month, day, name)   # 「未分類」で落ちる行が無い
    count = lambda pat: sum(1 for r in t[2027] if re.search(pat, r[4]))  # noqa: E731
    # 年8回の会合と、毎月1回の米2指標がそろっている（抜けたまま年を越さない）
    for pat in (r"^FOMC（結果発表）", r"^日銀会合（結果発表）", r"^ECB理事会", r"^英中銀", r"^豪中銀"):
        assert count(pat) == 8, (pat, count(pat))
    for pat in (r"^米雇用統計", r"^米CPI"):
        assert sorted(r[0] for r in t[2027] if re.search(pat, r[4])) == list(range(1, 13)), pat


# ── 台帳（economic-events.json）への取り込み ───────────────────────

def test_december_run_adds_next_january():
    """12月のうちから1月の発表が見える（25日の月次の取り込みを 2026-12-25 に回した形）。"""
    tables = S.parse_source_tables(FAKE)
    have = [_json_entry(2026, 12, 4, "米雇用統計（11月分）"), _json_entry(2026, 12, 10, "米CPI（11月分）"),
            _json_entry(2026, 12, 17, "英中銀 政策金利発表（MPC）")]
    plan = S.plan_additions(tables, have, dt.datetime(2026, 12, 25, 9, 30, tzinfo=JST))
    got = {(e["datetime"][:10], e["name"]) for e in plan["added"]}
    assert ("2027-01-08", "米雇用統計 NFP（12月分）") in got and ("2027-01-13", "米 CPI（12月分）") in got, got
    assert ("2027-02-04", "英中銀 政策金利発表（MPC）") in got and ("2027-02-09", "豪中銀 政策金利発表（RBA）") in got
    assert not [e for e in plan["added"] if e["datetime"].startswith("2026-01")]      # 前の年の1月を足さない
    assert plan["conflicts"] == [] and plan["already"] == 3
    # 年末の発表は時差で年をまたぐ：米東部 2026-12-31 14:00 → 日本時間 2027-01-01 04:00
    fomc = [e for e in plan["added"] if e["name"].startswith("FOMC")]
    assert [e["datetime"] for e in fomc] == ["2027-01-01T04:00+09:00"], fomc
    assert "ECONOMIC_EVENTS_2026 から生成" in fomc[0]["note"]                          # どの表から来たかが残る
    assert all("ECONOMIC_EVENTS_2027 から生成" in e["note"] for e in plan["added"] if e["datetime"] >= "2027-01-02")


def test_january_run_does_not_reuse_last_year():
    """1月になっても動く：前の年の表を「今年」として読まない（2026年1月の行が 2027年1月に化けない）。"""
    tables = S.parse_source_tables(FAKE)
    plan = S.plan_additions(tables, [], dt.datetime(2027, 1, 10, 9, 0, tzinfo=JST))
    dates = sorted(e["datetime"][:10] for e in plan["added"])
    assert "2027-01-15" not in dates and "2027-01-06" in dates, dates              # 01-15 は2026年の表の米CPI（12月分）
    assert dates[0] >= "2027-01-03", dates                                          # 7日より前は足さない
    assert {e["datetime"][:10] for e in plan["added"] if "米 CPI" in e["name"]} == {"2027-01-13", "2027-02-11"}
    assert plan["past"] == 6                                                        # 2026年の表の6行はぜんぶ「過ぎた」（今年の日付に化けない）


def test_two_releases_in_one_month_are_not_a_conflict():
    """豪CPI は 2027年1月に2回出る（1/6 と 1/27）。片方だけ先に台帳にあっても、もう片方を足せる。"""
    tables = S.parse_source_tables(FAKE)
    now = dt.datetime(2026, 12, 25, 9, 30, tzinfo=JST)
    both = [e["datetime"][:10] for e in S.plan_additions(tables, [], now)["added"] if e["name"].startswith("豪CPI")]
    assert both == ["2027-01-06", "2027-01-27"], both
    plan = S.plan_additions(tables, [_json_entry(2027, 1, 6, "豪CPI（11月分）")], now)
    assert [e["datetime"][:10] for e in plan["added"] if e["name"].startswith("豪CPI")] == ["2027-01-27"]
    assert plan["conflicts"] == []
    # 台帳に「表に無い日付」があるときは食い違い（黙って足さない。人が判断する）
    plan = S.plan_additions(tables, [_json_entry(2027, 1, 7, "豪CPI（11月分）")], now)
    assert not [e for e in plan["added"] if e["name"].startswith("豪CPI")]
    assert {c[0] for c in plan["conflicts"]} == {"豪CPI"} and plan["conflicts"][0][1].startswith("2027-01-07")
    # 2回動かしても二重に足さない
    again = S.plan_additions(tables, S.plan_additions(tables, [], now)["added"], now)
    assert again["added"] == []


# ── 見張り3本 ───────────────────────────────────────────────────

def test_watchers_read_every_year():
    assert VUK.master_from_source(FAKE, r"英中銀") == {D(2026, 12, 17), D(2027, 2, 4)}
    assert VUK.master_from_source(FAKE, r"^豪CPI") == {D(2027, 1, 6), D(2027, 1, 27)}
    us = VUS.master_from_source(FAKE)
    # 鍵は (対象月の年, 対象月, 種類)。1月に出る12月分は前の年の12月分
    assert us[(2026, 12, "CPI")] == D(2027, 1, 13) and us[(2027, 1, "CPI")] == D(2027, 2, 11), us
    assert us[(2026, 11, "雇用統計")] == D(2026, 12, 4) and us[(2026, 12, "雇用統計")] == D(2027, 1, 8)
    assert (2027, 1, "雇用統計") not in us                                          # ありえない日付（2/30）の行は捨てる
    assert VUK.master_label(D(2027, 1, 6)) == "ECONOMIC_EVENTS_2027"
    # 台帳の名前（取り込みが付けるラベル＋括弧）を米の見張りが読める。「 NFP」付きの米雇用統計も当たる
    for name, kind in (("米雇用統計（12月分）", "雇用統計"), ("米CPI（12月分）", "CPI")):
        got = VUS.JSON_NAME_RE.match(_json_entry(2027, 1, 8, name)["name"])
        assert got and got.groups() == (kind, "12"), (name, got)
    assert not VUS.JSON_NAME_RE.match("英雇用統計（失業率・賃金）") and not VUS.JSON_NAME_RE.match("豪CPI（12月分）")


def test_watcher_reports_next_year_table():
    today = D(2026, 12, 20)
    found = [D(2027, 1, 6), D(2027, 1, 27), D(2027, 2, 24)]
    # 翌年の日付が元の表に無ければ知らせる（前は 2026年の日付しか見なかった）
    problems, notes = [], []
    VA.judge("豪CPI", found, {D(2027, 1, 6), D(2027, 1, 27), D(2027, 2, 24)}, {D(2027, 1, 6), D(2027, 1, 27)}, today, problems, notes)
    assert problems == [] and notes == ["ECONOMIC_EVENTS_2027: 2027-02-24（水）の豪CPIが未登録"], (problems, notes)
    # 翌年の表の誤った日付（1/27 を 1/26 と載せた）は、翌年の表の名前で問題にする
    problems, notes = [], []
    VA.judge("豪CPI", found, set(found), {D(2027, 1, 6), D(2027, 1, 26), D(2027, 2, 24)}, today, problems, notes)
    assert len(problems) == 1 and "ECONOMIC_EVENTS_2027" in problems[0] and "2027-01-26" in problems[0], problems
    # 17日先の公式の発表が台帳に無ければ問題（＝発表の前にカレンダーが黙る）。年をまたいでも同じ
    problems, notes = [], []
    VA.judge("豪CPI", found, set(), set(found), today, problems, notes)
    assert any("2027-01-06" in p and "あと17日" in p for p in problems), problems


def test_no_year_written_in_code():
    """年を直に書いた場所が残っていない（残ると次の年にまた同じ直しが要る）。"""
    for name in ("sync_economic_events.py", "verify_economic_calendar.py", "verify_uk_eu_calendar.py",
                 "verify_au_calendar.py", "check_site_consistency.py"):
        src = open(os.path.join(ROOT, name), encoding="utf-8").read()
        assert not re.search(r"dt\.date\(20\d\d,\s*(int\(|mo\b|om\b)", src), name      # dt.date(2026, mo, dy) の形
        assert '"EVENTS_YEAR"' not in src and not re.search(r"ECONOMIC_EVENTS_20\d\d\\s", src), name   # 表の名前を1年だけ探す正規表現
        assert not re.search(r"\.year == 20\d\d", src), name
    gen = open(os.path.join(ROOT, "generate_market_news.py"), encoding="utf-8").read()
    assert not re.search(r"\bin ECONOMIC_EVENTS_20\d\d\b", gen)                       # 使う側は dated_economic_events / economic_events_of
    assert gen.count("dated_economic_events()") >= 4 and "economic_events_of(year)" in gen


# ── 点検（mw check） ─────────────────────────────────────────────

def test_site_check_covers_next_year():
    import check_site_consistency as C
    real_read = C._read
    try:
        # 本物の表：2027年の行に、曜日・FOMC・毎月の米2指標の警告が1件も出ない
        del C.warnings[:]
        C.check_economic_events(today=D(2026, 11, 12))
        C.check_us_monthly_indicators(today=D(2026, 11, 12))
        assert [w for w in C.warnings if "2027" in w] == [], C.warnings
        assert sorted(C._economic_event_tables())[:2] == [2026, 2027] and 2027 in C.FOMC_OFFICIAL
        # 1月になっても：今年（2027年）の表を1月から12月まで見る
        del C.warnings[:]
        C.check_us_monthly_indicators(today=D(2027, 1, 2))
        assert C.warnings == [], C.warnings
        # 作り物：翌年の表が無いまま10月を過ぎたら催促・年が変わったら強い警告
        C._read = lambda p: FAKE.split("ECONOMIC_EVENTS_2027")[0] if p == "generate_market_news.py" else real_read(p)
        del C.warnings[:]
        C.check_economic_events(today=D(2026, 9, 30))
        assert not [w for w in C.warnings if "ECONOMIC_EVENTS_2027" in w]
        C.check_economic_events(today=D(2026, 10, 1))
        assert any("ECONOMIC_EVENTS_2027 の表がまだ無い" in w for w in C.warnings), C.warnings
        del C.warnings[:]
        C.check_economic_events(today=D(2027, 1, 1))
        assert any("ECONOMIC_EVENTS_2027 の表が無い" in w for w in C.warnings), C.warnings
        # 作り物：翌年の表の抜け（2月の米雇用統計が無い＝2/30 と書いた行は別に「存在しない日付」）と日付の誤りを拾う
        C._read = lambda p: FAKE if p == "generate_market_news.py" else real_read(p)
        del C.warnings[:]
        C.check_economic_events(today=D(2026, 12, 20))
        C.check_us_monthly_indicators(today=D(2026, 12, 20))
        assert any("2027/2/30" in w and "存在しない日付" in w for w in C.warnings), C.warnings
        assert any("2027/3月に「米CPI」が無い" in w for w in C.warnings)
        assert any("2026/12/31" in w and "FOMC" in w and "不一致" in w for w in C.warnings)      # 公式の日程に無い FOMC
        assert not any("2026/1/" in w for w in C.warnings)                                       # 過ぎた行は言わない
    finally:
        C._read = real_read
        del C.warnings[:]


# ── ページ（カレンダー・トップの予定） ─────────────────────────────

def _gen():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SyntaxWarning)       # build_html の中の JS の正規表現（もとからある）
        import generate_market_news as M
    return M


def test_page_tables_follow_table_names():
    M = _gen()
    assert sorted(M.ECONOMIC_EVENTS_BY_YEAR) == sorted(S.load_source_tables()), sorted(M.ECONOMIC_EVENTS_BY_YEAR)   # 読み落とした表が無い
    assert M.economic_events_of(2027) is M.ECONOMIC_EVENTS_2027 and M.economic_events_of(2031) == []
    dated = M.dated_economic_events()
    assert len(dated) == len(M.ECONOMIC_EVENTS_2026) + len(M.ECONOMIC_EVENTS_2027)
    assert min(d for d, *_ in dated).year == 2026 and max(d for d, *_ in dated).year == 2027


def test_upcoming_events_cross_new_year():
    M = _gen()
    ev = M.find_upcoming_events(dt.datetime(2026, 12, 30, 7, 0, tzinfo=M.JST), days_ahead=10)
    by_day = {}
    for e in ev:
        by_day.setdefault(e["date"], []).append(e["name"])
    assert any(n.startswith("米雇用統計") for n in by_day.get(D(2027, 1, 8), [])), by_day      # 年末から年明けの発表が見える
    assert any(n.startswith("豪CPI") for n in by_day.get(D(2027, 1, 6), []))
    assert "ISM非製造業" not in by_day.get(D(2027, 1, 6), [])                                   # 2026年1月6日の行が化けて出ない
    # 1月になっても：2027年の表で数える（2026年の表の 1/10 米雇用統計が 2027-01-10 に出ない）
    ev = M.find_upcoming_events(dt.datetime(2027, 1, 7, 7, 0, tzinfo=M.JST), days_ahead=3)
    assert D(2027, 1, 8) in {e["date"] for e in ev} and D(2027, 1, 10) not in {e["date"] for e in ev}, ev


def test_calendar_page_december_shows_next_january():
    M = _gen()
    page = M.build_calendar_html(dt.datetime(2026, 12, 15, 7, 0, tzinfo=M.JST))
    assert "📆 2026年12月" in page and "📆 2027年1月" in page
    jan = page[page.index("📆 2027年1月"):]
    jan = jan[:jan.index("</main>")] if "</main>" in jan else jan
    assert "米雇用統計（12月分）" in jan and "豪CPI" in jan                 # 2027年の表の1月
    assert "ISM非製造業" not in jan                                           # 2026年の表の1月（1/6）を出さない
    # 1月の一覧の曜日は2027年のもの：1/8（米雇用統計）は金曜。前は今年（2026年）の曜日＝木曜で出た
    card = re.search(r'event-date-day">8</div><div class="event-date-dow">(.)</div></div>\s*<div class="event-body">\s*'
                     r'<div class="event-name">.*?米雇用統計（12月分）', jan, re.S)
    assert card and card.group(1) == "金", card and card.group(1)
    # 1月になっても：2027年1月と2月
    page = M.build_calendar_html(dt.datetime(2027, 1, 10, 7, 0, tzinfo=M.JST))
    assert "📆 2027年1月" in page and "📆 2027年2月" in page and "📆 2026年" not in page
    feb = page[page.index("📆 2027年2月"):]
    assert "英中銀" in feb and "豪中銀" in feb and "米CPI（1月分）" in feb


def test_top_schedule_counts_into_next_year():
    M = _gen()
    box = "".join(M._v2_schedule(dt.datetime(2026, 12, 21, 7, 0, tzinfo=M.JST)))   # 2026年の主な発表がぜんぶ済んだあと（戻りは 行・リンク の組）
    assert "1/13" in box and "米CPI（12月分）" in box, box                    # 次の米CPI＝2027-01-13
    assert "1/8" in box and "1/22" in box and "1/27" in box                  # 雇用統計・日銀・FOMC も翌年の日付


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok", name)
