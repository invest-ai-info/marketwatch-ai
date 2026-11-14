# -*- coding: utf-8 -*-
"""月次メールの「種類ごとの先詰まり」のテスト。2026-11-14 新設。通信しない。

なぜ要るか：月次メール（monthly_calendar_reminder.py の assess_state）は、台帳 economic-events.json の指標が
「全体であと何日ぶんあるか」しか見ていなかった。2027年は米・英・ユーロ圏が12月まで入っているので、
**中国や日本の統計が1件も無くても「✅ 対応不要」と出る**。足し忘れると、その種類だけ発表前のメール
（indicator-alert・indicator-digest）と環境警戒が黙る（このメールは 2026-09-17 に発表の直前に建てて損を出したのが
作った理由＝黙るのが一番困る）。
ここで固定すること：
  - 種類（sync_economic_events.py の RULES の label。台帳の名前との照合は json_pattern）ごとに最後の登録日を見る
  - 先の登録が1件も無い種類・もうすぐ登録が尽きる種類を、「あなたがやること」に**1件にまとめて**出す
  - 月に1回の種類は「最後の登録日まで45日以内」で知らせる。年8回の会合は29日以内。
    四半期に1回の種類（GDP・日銀短観）は間隔が長いので、登録が残っているうちは鳴らさない
  - 年末まで入っている種類（米雇用統計・FOMC など）は出さない＝やらなくていい作業を催促しない

実行:  python tests/test_calendar_kind_runway.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import json
import os
import statistics
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import monthly_calendar_reminder as R  # noqa: E402
import sync_economic_events as S  # noqa: E402

JST = S.JST
NOW = dt.datetime(2026, 11, 25, 9, 30, tzinfo=JST)          # 月次メールが出る日の朝


def _entry(date, name):
    """台帳の1行を、取り込み（sync_economic_events.build_entry）と同じ形で作る。"""
    return S.build_entry(date.year, date.month, date.day, S.match_rule(name), name)


def _after(days, name, now=NOW):
    return _entry((now + dt.timedelta(days=days)).date(), name)


def _row(rows, label):
    got = [r for r in rows if r["label"] == label]
    assert len(got) == 1, (label, got)
    return got[0]


def _state(ledger, label, now=NOW):
    return _row(R.kind_runway(ledger, now, S.RULES), label)["state"]


# ── 種類ごとに見る ───────────────────────────────────────────────

def test_every_kind_in_rules_is_looked_at():
    rows = R.kind_runway([], NOW, S.RULES)
    assert [r["label"] for r in rows] == [r["label"] for r in S.RULES]            # RULES の種類をぜんぶ・同じ順で
    assert len({r["label"] for r in rows}) == len(rows)                           # 同じ名前の種類が2つ無い
    assert all(r["state"] == "none" and r["last"] is None and r["future"] == 0 for r in rows)


def test_kind_with_no_future_is_reported_with_last_date():
    ledger = [_entry(dt.date(2026, 7, 9), "中国CPI（6月分）"), _after(300, "米CPI（9月分）")]
    rows = R.kind_runway(ledger, NOW, S.RULES)
    cn = _row(rows, "中国 CPI")
    assert cn["state"] == "none" and cn["last"] == dt.date(2026, 7, 9) and cn["future"] == 0, cn
    us = _row(rows, "米 CPI")
    assert us["state"] == "ok" and us["future"] == 1 and us["days_left"] == 300, us   # 日数は日本時間の日付どうしの差
    # 1件でも先にあれば「無い」ではない。過ぎた分だけなら「無い」
    assert _state([_after(-3, "中国CPI"), _after(200, "中国CPI")], "中国 CPI") == "ok"
    assert _state([_after(-3, "中国CPI"), _after(-40, "中国CPI")], "中国 CPI") == "none"


def test_monthly_kind_rings_when_last_date_is_within_45_days():
    for name, label in (("米雇用統計（1月分）", "米雇用統計 NFP"), ("全国CPI（3月分）", "全国CPI"),
                        ("豪雇用統計", "豪雇用統計"), ("ISM製造業", "米 ISM製造業景況感")):
        assert _state([_after(60, name)], label) == "ok", name
        assert _state([_after(47, name)], label) == "ok", name
        assert _state([_after(44, name)], label) == "soon", name
        assert _state([_after(5, name)], label) == "soon", name
        assert _state([_after(-1, name)], label) == "none", name
    # 手前に何件あっても、決め手は「最後の登録日」
    ledger = [_after(d, "米雇用統計") for d in (-30, 5, 33)]
    row = _row(R.kind_runway(ledger, NOW, S.RULES), "米雇用統計 NFP")
    assert row["state"] == "soon" and row["future"] == 2 and row["last"] == (NOW + dt.timedelta(days=33)).date(), row


def test_meeting_kind_rings_later_than_monthly():
    """年8回の会合は次まで約46日ある。月に1回の種類と同じ45日で鳴らすと、年末まで入っていても毎回鳴る。"""
    for name, label in (("FOMC（結果発表）", "FOMC 政策金利発表"), ("日銀会合（結果発表）", "日銀金融政策決定会合"),
                        ("ECB理事会", "ECB 政策金利発表"), ("英中銀 政策金利発表（MPC）", "英中銀 政策金利発表"),
                        ("豪中銀 政策金利発表（RBA）", "豪中銀 政策金利発表")):
        assert _state([_after(40, name)], label) == "ok", name
        assert _state([_after(26, name)], label) == "soon", name
        assert _state([_after(-2, name)], label) == "none", name


def test_quarterly_kind_does_not_ring_while_registered():
    """四半期に1回の種類は、次の発表が約3か月先。最後の登録日が近くても、過ぎるまでは鳴らさない。"""
    for name, label in (("日銀短観（3月調査）", "日銀短観"), ("日本GDP（10-12月期・1次速報）", "日本GDP速報"),
                        ("中国GDP（10-12月期）", "中国 GDP"), ("ユーロ圏GDP（速報）", "ユーロ圏GDP速報")):
        for days in (80, 40, 10, 1):
            assert _state([_after(days, name)], label) == "ok", (name, days)
        assert _state([_after(-1, name)], label) == "none", name      # 過ぎたら「先の登録が無い」（次まで2〜3か月ある）


def test_ledger_names_are_matched_by_json_pattern():
    ledger = [
        {"name": "米雇用統計 6 月 NFP", "datetime": "2027-06-04T21:30:00+09:00", "category": "economic_indicator"},  # 手で書いた名前
        {"name": "日銀短観（9月調査）", "datetime": "2027-10-01T08:50+09:00"},      # 日銀会合に数えない（category 無しでも読む）
        {"name": "OPEC+ 月次会合", "datetime": "2027-06-05T19:00+09:00"},           # RULES に無い種類は相手にしない
        {"name": "東証 休場", "datetime": "2027-06-10T00:00+09:00", "category": "market_holiday"},
        {"name": "英CPI（5月分）", "datetime": "こわれた日付"},                      # 読めない行で全体を止めない
        {"name": "中国 月次経済指標（10月分）", "datetime": "2027-11-15T11:00+09:00"},
        {"datetime": "2027-11-15T11:00+09:00"},                                     # 名前の無い行
    ]
    rows = R.kind_runway(ledger, NOW, S.RULES)
    assert _row(rows, "米雇用統計 NFP")["last"] == dt.date(2027, 6, 4)
    assert _row(rows, "日銀短観")["last"] == dt.date(2027, 10, 1)
    assert _row(rows, "日銀金融政策決定会合")["state"] == "none"
    assert _row(rows, "英CPI")["state"] == "none" and _row(rows, "英CPI")["last"] is None
    assert _row(rows, "中国 月次経済指標")["future"] == 1
    assert sum(r["future"] for r in rows) == 3


# ── 間隔の決まり（RULES の every_days） ─────────────────────────────

def test_intervals_are_declared_in_rules():
    every = {r["label"]: S.every_days_of(r) for r in S.RULES}
    quarterly = {k for k, v in every.items() if v >= 80}
    meetings = {k for k, v in every.items() if 40 <= v < 80}
    assert quarterly == {"日銀短観", "日本GDP速報", "中国 GDP", "ユーロ圏GDP速報"}, quarterly
    assert meetings == {"FOMC 政策金利発表", "ECB 政策金利発表", "日銀金融政策決定会合",
                        "英中銀 政策金利発表", "豪中銀 政策金利発表"}, meetings
    assert all(v == 30 for k, v in every.items() if k not in quarterly | meetings)      # 書いていない種類は月に1回
    assert S.every_days_of({"label": "あたらしい種類"}) == 30                              # 書き忘れは早めに鳴る側へ倒す


def test_declared_intervals_match_the_real_tables():
    """本物の表の発表の間隔と、RULES に書いた間隔が食い違っていない（四半期の種類を月1回と書くと毎月まちがって鳴る）。"""
    dates = {}
    for year, rows in S.load_source_tables().items():
        for month, day, _c, _imp, name, _desc in rows:
            rule = S.match_rule(name)
            if rule:
                dates.setdefault(rule["label"], set()).add(dt.date(year, month, day))
    checked = 0
    for rule in S.RULES:
        ds = sorted(dates.get(rule["label"], ()))
        if len(ds) < 4:                      # 行が少ない種類は間隔を決められない
            continue
        med = statistics.median((b - a).days for a, b in zip(ds, ds[1:]))
        every = S.every_days_of(rule)
        band = (20, 36) if every < 40 else (36, 62) if every < 80 else (80, 100)
        assert band[0] <= med <= band[1], (rule["label"], every, med)
        checked += 1
    assert checked >= 15, checked


# ── 「あなたがやること」の文 ─────────────────────────────────────────

def _full_ledger(now=NOW, days=380):
    """どの種類も先まで入っている台帳（＝何も言わなくてよい状態）。"""
    names = ["米雇用統計", "米CPI", "PPI", "小売売上高", "米GDP", "PCEデフレーター", "FOMC（結果発表）", "ECB理事会",
             "日銀会合（結果発表）", "中国CPI", "英中銀", "英CPI", "英雇用統計", "英GDP", "ユーロ圏HICP", "ユーロ圏GDP",
             "中国製造業PMI", "財新PMI", "中国経済指標", "中国GDP", "全国CPI", "日銀短観", "日本GDP", "鉱工業生産",
             "貿易統計", "豪中銀", "豪雇用統計", "豪CPI", "ISM非製造業", "ISM製造業"]
    ledger = [_after(days, n, now) for n in names]
    assert {S.match_rule(n)["label"] for n in names} == {r["label"] for r in S.RULES}     # RULES が増えたらここも足す
    return ledger


def test_nothing_to_say_when_every_kind_is_registered():
    rows = R.kind_runway(_full_ledger(), NOW, S.RULES)
    assert {r["state"] for r in rows} == {"ok"}, [r for r in rows if r["state"] != "ok"]
    assert R.kind_runway_todo(rows) is None


def test_todo_lists_kinds_in_one_item():
    ledger = [e for e in _full_ledger() if not e["name"].startswith(("中国", "財新", "米 ISM", "全国CPI", "豪雇用統計"))]
    ledger += [_entry(dt.date(2026, 7, 9), "中国CPI（6月分）"), _entry(dt.date(2026, 10, 15), "中国GDP（7-9月期）"),
               _after(22, "全国CPI（2月分）"), _after(27, "豪雇用統計")]
    rows = R.kind_runway(ledger, NOW, S.RULES)
    todo = R.kind_runway_todo(rows)
    assert isinstance(todo, str)                                                # 1件にまとめる（種類の数だけ並べない）
    for must in ("公式の日程で確かめて", "generate_market_news.py", "ECONOMIC_EVENTS_<年>", "発表前のメール", "環境警戒"):
        assert must in todo, must
    none_part, soon_part = todo.split("もうすぐ登録が尽きる")
    for label in ("中国 CPI", "中国 製造業PMI", "財新 PMI", "中国 月次経済指標", "中国 GDP",
                  "米 ISM非製造業景況感", "米 ISM製造業景況感"):
        assert label in none_part and label not in soon_part, label
    assert "中国 CPI（月1回・最後の登録 2026-07-09）" in none_part, none_part
    assert "中国 GDP（四半期に1回・最後の登録 2026-10-15）" in none_part
    assert "財新 PMI（月1回・台帳に1件も無い）" in none_part
    assert "全国CPI（月1回・最後の登録 2026-12-17＝あと22日）" in soon_part, soon_part
    assert "豪雇用統計（月1回・最後の登録 2026-12-22＝あと27日）" in soon_part
    for label in ("米雇用統計 NFP", "FOMC 政策金利発表", "米 CPI", "英CPI", "日銀短観", "ECB 政策金利発表"):
        assert label not in todo, label                                         # 先まで入っている種類は出さない
    assert "7種類" in none_part and "2種類" in soon_part and "9種類" in none_part.split("\n")[0], todo


# ── 月次メールへのつなぎ（assess_state・文面） ──────────────────────

def _folder(ledger, tmp):
    json.dump({"events": ledger}, open(os.path.join(tmp, "economic-events.json"), "w", encoding="utf-8"),
              ensure_ascii=False)
    day = (NOW + dt.timedelta(days=10)).date().isoformat()
    json.dump({"updated": "2026-11-25", "us": [{"date": day}], "jp": [{"date": day}]},
              open(os.path.join(tmp, "earnings-calendar.json"), "w", encoding="utf-8"))
    return tmp


def test_monthly_mail_stays_quiet_when_all_registered():
    with tempfile.TemporaryDirectory() as tmp:
        todos, stats = R.assess_state(NOW, here=_folder(_full_ledger(), tmp))
    assert todos == [], todos
    assert stats["kind_total"] == len(S.RULES) and stats["kind_none"] == 0 and stats["kind_soon"] == 0, stats
    subject, body = R.build_report(2026, 12, todos, stats, "")
    assert subject.startswith("✅ [対応不要]") and "✅ 対応は要りません" in body
    assert "種類ごと" in body and "先の登録なし 0" in body, body


def test_monthly_mail_asks_once_when_kinds_are_missing():
    """全体では1年先まで入っていても（米・英・ユーロ圏）、中国が無ければ「対応不要」と言わない。"""
    ledger = [e for e in _full_ledger() if not e["name"].startswith(("中国", "財新"))]
    with tempfile.TemporaryDirectory() as tmp:
        todos, stats = R.assess_state(NOW, here=_folder(ledger, tmp))
    assert len(todos) == 1 and "中国 CPI" in todos[0] and "財新 PMI" in todos[0], todos      # 5種類でも「やること」は1件
    assert stats["ind_runway"] >= 300 and stats["kind_none"] == 5 and stats["kind_soon"] == 0, stats
    subject, body = R.build_report(2026, 12, todos, stats, "(材料)")
    assert subject.startswith("⚠️ [要対応 1件]"), subject
    assert "【あなたがやること】" in body and "中国 月次経済指標" in body and "先の登録なし 5" in body
    assert "✅ 対応は要りません" not in body


def test_all_empty_ledger_is_not_said_twice():
    """指標が全部0件のときは、もとからある「未来分が0件」の1件で足りる（30種類を並べない）。"""
    with tempfile.TemporaryDirectory() as tmp:
        todos, stats = R.assess_state(NOW, here=_folder([], tmp))
    assert len(todos) == 1 and "0件" in todos[0], todos
    assert stats["kind_none"] == len(S.RULES)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok", name)
