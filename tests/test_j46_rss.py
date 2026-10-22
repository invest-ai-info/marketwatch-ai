# -*- coding: utf-8 -*-
"""J46R 寄り前の売買代金の多さ（RSS 版・j46_rss.py）のテスト。2026-10-22 新設。

値はすべて作り物（ネットワークに出ない）。確かめること＝①事前登録と定数の一致 ②比率だけの記録（コード・値段を残さない）
③数えない行（片側の気配・特別気配・寄っていない・9:30 が古い・±25％超）④start より前と同じ日は足さない
⑤1000件以上かつ20営業日以上で1回だけ判定・判定は変えない ⑥diag は寄り→9:30 を出さない。

実行:  python tests/test_j46_rss.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import j10b_records as B  # noqa: E402
import j46_rss as R  # noqa: E402


def _r859(code, prev, ask, bid, aq, bq, ms=0, mb=0, flag="", date="2026-10-27"):
    return {"date": date, "time": "08:59:30", "code": code, "prev_close": str(prev), "ask": str(ask), "ask_qty": str(aq),
            "bid": str(bid), "bid_qty": str(bq), "mkt_sell_qty": str(ms), "mkt_buy_qty": str(mb), "ask_flag": flag,
            "bid_flag": ""}


def _r930(code, op, last, t="09:30:01", date="2026-10-27"):
    return {"date": date, "time": "09:30:05", "code": code, "open": str(op), "last": str(last), "last_time": t}


def test_prereg_matches_constants():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    sec = text[text.index("## J46 "):text.index("## 共通の決まり")]
    assert "J46R" in sec and "1000件以上 かつ 20営業日以上" in sec and "jp-stock-info.json" in sec
    assert R.GOAL_N == 1000 and R.GOAL_DAYS == 20 and R.MIN_930 == "09:20" and R.MAX_MOVE == 0.25
    assert "9:20 より前" in sec and "±25%" in sec and "j46_rss.py" in sec


def test_records_are_ratios_only_and_skip_rules():
    rows859 = [_r859("7203.T", 3000, 3010, 3008, 1000, 1200, 300, 500),          # 数える
               _r859("1111", 500, 0, 499, 0, 10),                              # 片側の気配が無い
               _r859("2222", 500, 520, 520, 10, 10, flag="特"),                 # 特別気配
               _r859("3333", 500, 501, 500, 10, 10),                           # 寄っていない
               _r859("4444", 500, 501, 500, 10, 10),                           # 9:30 の値が古い
               _r859("5555", 500, 501, 500, 10, 10),                           # ±25％超
               _r859("6666", 500, 501, 500, 10, 10),                           # ふだんの売買代金が無い
               _r859("7777", 500, 501, 500, 10, 10, date="2026-10-26")]        # 日付が違う
    rows930 = [_r930("7203", 3000, 3030), _r930("3333", "", ""), _r930("4444", 500, 505, t="09:15:00"),
               _r930("5555", 100, 200), _r930("6666", 500, 501)]
    base = {c: 1e9 for c in ("7203", "1111", "2222", "3333", "4444", "5555")}
    recs, skipped = R.make_records("2026-10-27", rows859, rows930, base, qty_unit=1, special=("特",))
    assert len(recs) == 1
    r = recs[0]
    assert set(r) == {"date", "gap859", "gap_open", "r930", "pre_tv"}
    assert 3000 not in r.values() and "7203" not in str(r)
    assert abs(r["pre_tv"] - round((300 + 1000 + 500 + 1200) / 2 * 3009 / 1e9, 6)) < 1e-9
    assert abs(r["r930"] - 0.01) < 1e-6 and r["gap_open"] == 0.0
    assert skipped == {"片側の気配が無い": 1, "特別気配": 1, "寄っていない・9:30 の値が無い": 1, "9:30 の値が古い": 1,
                       "データの誤り（±25％超）": 1, "ふだんの売買代金が無い": 1, "日付が違う": 1}
    recs100, _ = R.make_records("2026-10-27", rows859[:1], rows930[:1], base, qty_unit=100)
    assert abs(recs100[0]["pre_tv"] / r["pre_tv"] / 100 - 1) < 1e-3            # 百株なら100倍（記録は6桁で丸める）
    assert R.num("1,234.5") == 1234.5 and R.num("-") is None and R.hhmm("2026-10-27 09:30:01") == "09:30" and R.hhmm("9:15:00") == "09:15" and R.hhmm("x") == ""


def test_start_once_day_once_and_judged_once():
    st = R.empty_state()
    assert "start" in R.add_day(st, "2026-10-26", [], {})                      # 試運転の日は数えない
    st["start"] = "2026-10-27"
    assert "より前" in R.add_day(st, "2026-10-26", [], {})
    rnd = random.Random(46)
    day0 = dt.date(2026, 10, 27)
    for k in range(19):                                                         # 19日×100件＝1900件でもまだ（20営業日に届かない）
        day = (day0 + dt.timedelta(days=k)).isoformat()
        recs = []
        for _ in range(100):
            pre = rnd.uniform(0.01, 0.6)
            recs.append({"date": day, "gap859": 0.0, "gap_open": 0.0, "r930": -0.02 * pre + rnd.uniform(-0.002, 0.002),
                         "pre_tv": pre})
        assert R.add_day(st, day, recs, {}) is None
    assert R.add_day(st, (day0).isoformat(), [], {}) is not None               # 同じ日は二度足さない
    assert R.judge(st) is None and "途中の平均は出さない" in R.status_text(st)
    last = (day0 + dt.timedelta(days=19)).isoformat()
    R.add_day(st, last, [{"date": last, "gap859": 0.0, "gap_open": 0.0, "r930": -0.02 * p / 100, "pre_tv": p / 100}
                         for p in range(1, 61)], {})
    v = R.judge(st)
    assert v and v["decided_on"] == last and v["days"] == 20 and v["n"] == 1960 and v["status"] == "罠の目印（兆し）"
    assert v == R.judge(st)                                                    # 判定は変えない
    assert B.compare_within_day([], 10, 1)["days_compared"] == 0


def test_diag_shows_no_open_to_930_moves():
    rows859 = [_r859(str(1000 + i), 1000, 1001, 1000, 50, 60, 5, 5) for i in range(10)] + [_r859("9999", 1000, 0, 0, 0, 0)]
    rows930 = [_r930(str(1000 + i), 1000, 1100) for i in range(10)]
    base = {str(1000 + i): 1e8 for i in range(10)}
    txt = R.diag_text("2026-10-27", rows859, rows930, base)
    assert "片側の気配が無い" in txt and "pre_tv" in txt and "始値あり 10/10" in txt
    assert "+10" not in txt and "10.00%" not in txt and "寄り→9:30 は出さない" in txt


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
