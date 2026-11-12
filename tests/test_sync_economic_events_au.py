# -*- coding: utf-8 -*-
"""豪州の指標（豪中銀の金利・豪雇用統計・豪CPI）がカレンダーに入ることのテスト。2026-11-12 新設。

監視18銘柄のうち4つが豪ドルのペアなのに、豪州の指標が1つも無かった＝豪中銀の発表の前でも
環境警戒スコアが鳴らなかった。ここで固定すること：
  - ECONOMIC_EVENTS_2026 の "au" の行は、どれも sync_economic_events.py の決まりに当たる（未分類で落ちない）
  - 時刻は現地時刻＋タイムゾーンで決まる＝豪州の夏時間は日本時間 12:30／冬は 13:30（豪中銀）
  - 当てはめる銘柄は豪ドルの4ペア・国は AU
  - ほかの国の決まりに巻き込まれない（「豪CPI」が「米CPI」に、「豪雇用統計」が「米雇用統計」に化けない）

実行:  python tests/test_sync_economic_events_au.py     （pytest 不要。pytest でも動く）
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import sync_economic_events as S  # noqa: E402

AUD4 = ["AUDJPY=X", "AUDUSD=X", "EURAUD=X", "GBPAUD=X"]


def test_au_rows_match_rules():
    rows = [r for r in S.load_source_rows() if r[2] == "au"]
    assert len(rows) >= 5, rows                                   # 2026-11・12月の5行（豪中銀2・雇用統計2・CPI1）
    for month, day, _c, _imp, name, _desc in rows:
        rule = S.match_rule(name)
        assert rule is not None and rule["country"] == "AU", (month, day, name)
        assert rule["assets"] == AUD4, name
    names = {(m, d, S.match_rule(n)["label"]) for m, d, _c, _i, n, _x in rows}
    assert {(11, 3, "豪中銀 政策金利発表"), (12, 8, "豪中銀 政策金利発表"), (11, 19, "豪雇用統計"), (12, 17, "豪雇用統計"), (11, 25, "豪CPI")} <= names


def test_au_times_follow_local_clock():
    rba = S.match_rule("豪中銀 政策金利発表（RBA）")
    e = S.build_entry(2026, 12, 8, rba, "豪中銀 政策金利発表（RBA）")      # 豪州の夏時間（UTC+11）→ 日本時間 12:30
    assert e["datetime"] == "2026-12-08T12:30+09:00" and e["impact"] == "critical" and e["country"] == "AU", e
    assert e["affected_assets"] == AUD4 and e["category"] == "economic_indicator"
    e = S.build_entry(2026, 6, 16, rba, "豪中銀 政策金利発表（RBA）")      # 豪州の冬（UTC+10）→ 日本時間 13:30
    assert e["datetime"] == "2026-06-16T13:30+09:00", e
    jobs = S.match_rule("豪雇用統計（10月分）")
    e = S.build_entry(2026, 11, 19, jobs, "豪雇用統計（10月分）")          # 現地 11:30 → 日本時間 09:30
    assert e["datetime"] == "2026-11-19T09:30+09:00" and e["impact"] == "high" and e["name"] == "豪雇用統計（10月分）", e
    cpi = S.match_rule("豪CPI（10月分）")
    assert S.build_entry(2026, 11, 25, cpi, "豪CPI（10月分）")["datetime"] == "2026-11-25T09:30+09:00"


def test_no_cross_match_with_other_countries():
    assert S.match_rule("豪CPI（10月分）")["label"] == "豪CPI"
    assert S.match_rule("豪雇用統計（10月分）")["label"] == "豪雇用統計"
    assert S.match_rule("米CPI（10月分）")["label"] == "米 CPI"
    assert S.match_rule("米雇用統計（10月分）")["label"] == "米雇用統計 NFP"
    assert S.match_rule("英CPI（9月分）")["label"] == "英CPI"
    assert S.match_rule("英中銀 政策金利発表（MPC）")["label"] == "英中銀 政策金利発表"
    assert S.match_rule("中国CPI")["label"] == "中国 CPI"
    # 既存の台帳の名前 → 決まり（json_pattern）も取り違えない
    import re
    hit = lambda nm: [r["label"] for r in S.RULES if re.search(r["json_pattern"], nm)]  # noqa: E731
    assert hit("豪中銀 政策金利発表（RBA）") == ["豪中銀 政策金利発表"]
    assert hit("豪雇用統計（10月分）") == ["豪雇用統計"] and hit("豪CPI（10月分）") == ["豪CPI"]
    assert "豪CPI" not in hit("米 CPI 6 月") and "豪雇用統計" not in hit("英雇用統計")


def test_calendar_page_knows_australia():
    src = open(os.path.join(ROOT, "generate_market_news.py"), encoding="utf-8").read()
    assert src.count('"cn": "🇨🇳", "au": "🇦🇺"}') == 5 and '"cn": "中国", "au": "豪州"}' in src    # 国旗と国名（旗なしで出ない）
    assert src.count('"uk": "🇬🇧", "cn": "🇨🇳"}') == 0                                              # 豪州なしの旗の表が残っていない
    assert '"豪中銀":' in src and '"豪雇用統計":' in src and '"豪CPI":' in src                      # 初心者向けの説明


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok", name)
