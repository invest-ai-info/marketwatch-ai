# -*- coding: utf-8 -*-
"""build_jp_highs.py（年初来・上場来の高値と安値の一覧）の判定のテスト。2026-10-06 新設・同日夕に安値を追加。

実行:  python tests/test_build_jp_highs.py     （pytest 不要。pytest でも動く）
"""
import datetime
import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_spec = importlib.util.spec_from_file_location("build_jp_highs", os.path.join(ROOT, "build_jp_highs.py"))
H = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(H)


def _days(start, n, high=100.0, low=90.0, close=95.0):
    """start から n 営業日ぶん（土日は気にしない）の (日付, 高値, 安値, 終値, 出来高)。"""
    d0 = datetime.date.fromisoformat(start)
    return [((d0 + datetime.timedelta(days=i)).isoformat(), high, low, close, 1000.0) for i in range(n)]


def _today(high, low, close, date="2026-10-05"):
    return (date, high, low, close, 5000.0)


# ── 期間の始まり（日本の慣例） ─────────────────────────────

def test_window_april_to_december_is_this_year():
    assert H.window_start("2026-10-05") == ("2026-01-01", "年初来")
    assert H.window_start("2026-04-01") == ("2026-01-01", "年初来")
    assert H.window_start("2026-12-30") == ("2026-01-01", "年初来")


def test_window_january_to_march_is_last_year():
    # 1〜3月は前の年の1月1日から＝「昨年来高値」「昨年来安値」
    assert H.window_start("2027-01-05") == ("2026-01-01", "昨年来")
    assert H.window_start("2027-03-31") == ("2026-01-01", "昨年来")


# ── 年初来高値 ─────────────────────────────────────────

def test_ytd_high_detected_when_today_exceeds_window():
    bars = _days("2026-01-05", 60) + [_today(101.0, 96.0, 100.5)]
    assert H.ytd_extreme(bars, "2026-01-01", "high") == {"prev": 100.0, "prev_date": "2026-01-05"}
    assert H.ytd_extreme(bars, "2026-01-01", "low") is None


def test_ytd_equal_is_not_update():
    # 前の高値（安値）と同じ＝「更新」ではない
    bars = _days("2026-01-05", 60) + [_today(100.0, 90.0, 95.0)]
    assert H.ytd_extreme(bars, "2026-01-01", "high") is None
    assert H.ytd_extreme(bars, "2026-01-01", "low") is None


def test_ytd_ignores_highs_before_window():
    # 前の年の高値（120）は 4〜12月の年初来の比べる相手に入らない
    bars = (_days("2025-06-01", 30, high=120.0, low=110.0, close=115.0)
            + _days("2026-01-05", 60) + [_today(101.0, 96.0, 100.5)])
    assert H.ytd_extreme(bars, "2026-01-01", "high") is not None
    # 1〜3月の慣例（前の年の1月から）なら 120 が相手になる＝更新ではない
    assert H.ytd_extreme(bars, "2025-01-01", "high") is None


def test_ytd_needs_enough_prior_bars():
    # 上場直後（期間内の前の営業日が20日未満）は数えない
    bars = _days("2026-09-20", 10) + [_today(101.0, 96.0, 100.5)]
    assert H.ytd_extreme(bars, "2026-01-01", "high") is None
    bars = _days("2026-09-20", 10) + [_today(94.0, 85.0, 86.0)]
    assert H.ytd_extreme(bars, "2026-01-01", "low") is None


def test_ytd_rejects_bad_data():
    # 前の日の終値の1.5倍を超える高値＝データの誤り（ストップ高でも届かない）
    bars = _days("2026-01-05", 60) + [_today(160.0, 96.0, 100.5)]
    assert H.ytd_extreme(bars, "2026-01-01", "high") is None
    # 高値が終値より安い＝データの誤り
    bars = _days("2026-01-05", 60) + [_today(101.0, 96.0, 103.0)]
    assert H.ytd_extreme(bars, "2026-01-01", "high") is None


# ── 年初来安値 ─────────────────────────────────────────

def test_ytd_low_detected_when_today_goes_below_window():
    bars = _days("2026-01-05", 60) + [_today(94.0, 85.0, 86.0)]
    assert H.ytd_extreme(bars, "2026-01-01", "low") == {"prev": 90.0, "prev_date": "2026-01-05"}
    assert H.ytd_extreme(bars, "2026-01-01", "high") is None


def test_ytd_low_picks_lowest_prior_and_its_date():
    bars = _days("2026-01-05", 30) + _days("2026-03-01", 1, low=80.0) + _days("2026-03-02", 30) \
        + [_today(94.0, 79.0, 86.0)]
    assert H.ytd_extreme(bars, "2026-01-01", "low") == {"prev": 80.0, "prev_date": "2026-03-01"}
    # 80 を下回っていなければ更新ではない
    bars[-1] = _today(94.0, 81.0, 86.0)
    assert H.ytd_extreme(bars, "2026-01-01", "low") is None


def test_ytd_low_rejects_bad_data():
    # 前の日の終値の 1/1.5 を下回る安値＝データの誤り（ストップ安でも届かない）
    bars = _days("2026-01-05", 60) + [_today(94.0, 60.0, 86.0)]
    assert H.ytd_extreme(bars, "2026-01-01", "low") is None
    # 安値が終値より高い＝データの誤り
    bars = _days("2026-01-05", 60) + [_today(94.0, 87.0, 86.0)]
    assert H.ytd_extreme(bars, "2026-01-01", "low") is None
    # 安値が0以下
    bars = _days("2026-01-05", 60) + [_today(94.0, 0.0, 86.0)]
    assert H.ytd_extreme(bars, "2026-01-01", "low") is None


# ── 上場来（記録のある全期間） ───────────────────────────

def test_ath_uses_prior_months_and_prior_days_only():
    monthly = [("2001-01-01", 90.0, 50.0, 80.0, 0.0), ("2026-09-01", 100.0, 60.0, 95.0, 0.0),
               ("2026-10-01", 105.0, 60.0, 104.0, 0.0)]   # その月の月足はその日の値を含む＝使わない
    daily = _days("2024-10-07", 30, high=95.0, low=70.0, close=94.0) + [_today(101.0, 96.0, 100.0)]
    rec, prev, first = H.all_time_extreme(monthly, daily, "high")
    assert rec is True and prev == 100.0 and first == "2001-01-01"


def test_ath_not_updated_when_old_high_is_higher():
    monthly = [("2000-01-01", 300.0, 200.0, 250.0, 0.0), ("2026-09-01", 100.0, 60.0, 95.0, 0.0)]
    daily = _days("2024-10-07", 30, high=95.0, low=70.0, close=94.0) + [_today(101.0, 96.0, 100.0)]
    rec, prev, _ = H.all_time_extreme(monthly, daily, "high")
    assert rec is False and prev == 300.0


def test_ath_same_month_earlier_day_counts():
    # 同じ月の前の日の高値（日足）も比べる相手に入る
    monthly = [("2026-09-01", 100.0, 60.0, 95.0, 0.0)]
    daily = [("2026-10-01", 110.0, 100.0, 108.0, 1.0), ("2026-10-02", 105.0, 100.0, 104.0, 1.0),
             ("2026-10-05", 106.0, 101.0, 105.0, 1.0)]
    rec, prev, _ = H.all_time_extreme(monthly, daily, "high")
    assert rec is False and prev == 110.0


def test_atl_record_low_and_old_low_blocks_it():
    daily = _days("2024-10-07", 30, high=95.0, low=70.0, close=94.0) + [_today(70.0, 49.0, 52.0)]
    # 記録のある期間の安値は 50（2001年）＝きょう 49 で更新
    monthly = [("2001-01-01", 90.0, 50.0, 80.0, 0.0), ("2026-09-01", 100.0, 60.0, 95.0, 0.0),
               ("2026-10-01", 100.0, 40.0, 52.0, 0.0)]   # その月の月足（その日の安値を含む）は使わない
    rec, prev, first = H.all_time_extreme(monthly, daily, "low")
    assert rec is True and prev == 50.0 and first == "2001-01-01"
    # もっと安い昔の安値（30）があれば更新ではない
    monthly[0] = ("2001-01-01", 90.0, 30.0, 80.0, 0.0)
    rec, prev, _ = H.all_time_extreme(monthly, daily, "low")
    assert rec is False and prev == 30.0


def test_ath_without_monthly_is_unknown():
    assert H.all_time_extreme([], _days("2026-01-05", 30), "high") == (None, None, None)
    assert H.all_time_extreme([], _days("2026-01-05", 30), "low") == (None, None, None)


def test_listing_confirmed_only_when_record_starts_mid_month():
    # 2026-10-06 の全399銘柄の監査（--audit）の実データ
    # 上場の週から記録がある＝月足の最初のバーが月の途中（2017-09 以降の新規上場はすべてこれ）
    assert H.listing_confirmed("2018-06-18") is True      # メルカリ
    assert H.listing_confirmed("2024-12-18") is True      # キオクシア
    # Yahoo の記録がその月から始まっただけ＝月の1日（古い銘柄はすべてこれ）
    assert H.listing_confirmed("1999-06-01") is False     # トヨタ
    assert H.listing_confirmed("2000-02-01") is False     # 小松製作所（初版はここを「上場来」と誤った）
    assert H.listing_confirmed("2004-12-01") is False     # 日本郵船・川崎重工業（2版の「2004年以降」だと誤る）
    assert H.listing_confirmed("2010-03-01") is False     # レーザーテック（1990年上場）
    assert H.listing_confirmed("2012-10-01") is False     # 北洋銀行
    assert H.listing_confirmed("2014-11-01") is False     # リクルート（2014-10 上場だが記録は翌月から＝言い切らない側）
    # 念のための下限・分からないとき
    assert H.listing_confirmed("2001-02-15") is False
    assert H.listing_confirmed("") is False and H.listing_confirmed(None) is False


# ── 1行の形 ───────────────────────────────────────────

def test_make_row_uses_high_or_low_by_side():
    bars = _days("2026-01-05", 60) + [_today(94.0, 85.0, 86.0)]
    hit = dict(H.ytd_extreme(bars, "2026-01-01", "low"), side="low")
    r = H.make_row("7203", {"name": "テスト", "sector": "輸送用機器", "market": "プライム", "akaji": False},
                   bars, hit, True, 88.0, "2018-06-18")
    assert r["ext"] == 85.0 and r["prev"] == 90.0 and r["record"] is True and r["listed"] is True
    assert r["market"] == "プライム" and r["sector"] == "輸送用機器"
    assert r["price"] == 86.0 and round(r["pct"], 4) == round(86.0 / 95.0 - 1, 4)
    r = H.make_row("7203", {}, bars, hit, False, 80.0, "2000-02-01")
    assert r["record"] is False and r["listed"] is None


# ── 全銘柄の一覧（JPX） ────────────────────────────────────

def test_find_list_link_makes_absolute_url():
    html = '<a href="/markets/statistics-equities/misc/tvdivq0000001vg2-att/data_j.xlsx">一覧</a>'
    assert H.find_list_link(html) == \
        "https://www.jpx.co.jp/markets/statistics-equities/misc/tvdivq0000001vg2-att/data_j.xlsx"
    assert H.find_list_link('<a href="/x/data_j.xls">') == "https://www.jpx.co.jp/x/data_j.xls"
    assert H.find_list_link("<p>リンクなし</p>") == ""


def test_parse_universe_keeps_only_three_markets():
    # 2026-09-30 の実際の一覧の形（列名・区分の名前）
    recs = [
        {"日付": "20260930", "コード": "1301", "銘柄名": "極洋", "市場・商品区分": "プライム（内国株式）", "33業種区分": "水産・農林業"},
        {"日付": "20260930", "コード": "1305", "銘柄名": "ｉＦｒｅｅＥＴＦ", "市場・商品区分": "ETF・ETN", "33業種区分": "-"},
        {"日付": "20260930", "コード": "285A", "銘柄名": "キオクシアＨＤ", "市場・商品区分": "プライム（内国株式）", "33業種区分": "電気機器"},
        {"日付": "20260930", "コード": "9999", "銘柄名": "外国の会社", "市場・商品区分": "グロース（外国株式）", "33業種区分": "-"},
        {"日付": "20260930", "コード": "8951", "銘柄名": "ＲＥＩＴ", "市場・商品区分": "REIT・ベンチャーファンド・カントリーファンド・インフラファンド", "33業種区分": "-"},
        {"日付": "20260930", "コード": "1111", "銘柄名": "プロ", "市場・商品区分": "PRO Market", "33業種区分": "-"},
        {"日付": "20260930", "コード": "2222", "銘柄名": "スタ", "市場・商品区分": "スタンダード（内国株式）", "33業種区分": "化学"},
    ]
    st, d = H.parse_universe(recs, {"285A": {"akaji": False}})
    assert sorted(st) == ["1301", "2222", "285A", "9999"] and d == "2026-09-30"
    assert st["285A"] == {"name": "キオクシアＨＤ", "sector": "電気機器", "market": "プライム", "akaji": False}
    assert st["1301"]["akaji"] is None              # 約400銘柄の外＝赤字・黒字は分からない
    assert st["9999"]["market"] == "グロース" and st["9999"]["sector"] == ""


def test_parse_jpx_new_listings_reads_date_code_and_ipo():
    # JPX「新規上場銘柄一覧」の表の行の形（2022 の一覧から）
    html = ("<table><tr><th>上場日</th><th>会社名</th><th>コード</th><th>公開価格</th></tr>"
            "<tr><td>2022/12/29</td><td>（2022/11/25）</td><td>（株）スマサポ</td><td>代表者インタビュー</td>"
            "<td>9342</td><td></td><td>720～800</td><td>150</td><td>100</td></tr>"
            "<tr><td>グロース</td><td>800</td></tr>"
            "<tr><td>2022/12/28</td><td>（2022/12/21）</td><td>中部鋼鈑（株）</td><td>5461</td>"
            "<td>-</td><td>-</td><td>100</td></tr></table>")
    assert H.parse_jpx_new_listings(html) == [("2022-12-29", "9342", True), ("2022-12-28", "5461", False)]


# ── その他 ─────────────────────────────────────────────

def test_already_done_needs_same_day_and_same_rule():
    prev = {"asof": "2026-10-05", "rule": H.RULE_VERSION}
    assert H.already_done(prev, "2026-10-05") is True
    assert H.already_done(prev, "2026-10-06") is False                  # 新しい営業日＝作る
    assert H.already_done({"asof": "2026-10-05", "rule": H.RULE_VERSION - 1}, "2026-10-05") is False   # 決まりが変わった＝作り直す
    assert H.already_done({"asof": "2026-10-05"}, "2026-10-05") is False  # 初版（rule なし）も作り直す
    assert H.already_done({}, "2026-10-05") is False
    assert H.already_done(prev, "") is False


def test_update_history_replaces_same_day_and_keeps_order():
    # 安値を足す前の日（ytd・ath だけ）が混ざっていても並ぶ
    h = [{"date": "2026-10-01", "ytd": 3, "ath": 1}, {"date": "2026-10-02", "ytd": 5, "ath": 2}]
    h = H.update_history(h, "2026-10-02", {"ytd": 7, "ath": 3, "ytd_low": 1, "atl": 0})
    h = H.update_history(h, "2026-10-05", {"ytd": 9, "ath": 4, "ytd_low": 2, "atl": 1})
    assert [x["date"] for x in h] == ["2026-10-01", "2026-10-02", "2026-10-05"]
    assert h[1] == {"date": "2026-10-02", "ytd": 7, "ath": 3, "ytd_low": 1, "atl": 0}


def test_update_history_keeps_last_n():
    h = []
    for i in range(H.HISTORY_KEEP + 5):
        h = H.update_history(h, (datetime.date(2025, 1, 1) + datetime.timedelta(days=i)).isoformat(), {"ytd": i})
    assert len(h) == H.HISTORY_KEEP and h[-1]["ytd"] == H.HISTORY_KEEP + 4


def test_parse_bars_drops_missing_and_uses_jst_date():
    # 2026-10-05 00:00 UTC（＝09:00 JST）と、安値の欠けたバー
    t = int(datetime.datetime(2026, 10, 5, tzinfo=datetime.timezone.utc).timestamp())
    res = {"timestamp": [t, t + 86400],
           "indicators": {"quote": [{"high": [101.0, 102.0], "low": [97.0, None],
                                     "close": [100.0, 99.0], "volume": [5, 6]}]}}
    assert H.parse_bars(res) == [("2026-10-05", 101.0, 97.0, 100.0, 5.0)]


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"ok   {name}")
            except AssertionError as e:
                fails += 1
                print(f"FAIL {name}: {e}")
    print(f"{'全件緑' if not fails else f'{fails}件失敗'}")
    sys.exit(1 if fails else 0)
