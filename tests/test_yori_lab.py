# -*- coding: utf-8 -*-
"""J4 寄り付きラボ（yori_lab.py）のテスト。2026-09-28 新設。

値動きはすべて作り物（ネットワークに出ない）。確かめること＝①各時刻の値の取り方（9:15＝9:10 の足の終値・昼休み）
②急騰・急落・上ヒゲの決め方 ③前の日の上位20の決め方（build_jp_rankings.py と同じ・その日を基準に入れない）
④その日の場が終わっていなければ使わない ⑤手仕舞いの時刻は前半だけで選ぶ ⑥判定 ⑦出力に銘柄コードを出さない
⑧事前登録と定数の一致。

実行:  python tests/test_yori_lab.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import yori_lab as Y  # noqa: E402

JST = Y.P.JST


def _bars(day, prices, start=(9, 0), vol=100.0):
    """prices＝[(始, 高, 安, 終)] を 5分おきに並べる（11:30〜12:30 は昼休みで飛ばす）"""
    t = dt.datetime.combine(day, dt.time(*start), JST)
    out = []
    for o, h, l, c in prices:
        if dt.time(11, 30) <= t.time() < dt.time(12, 30):
            t = dt.datetime.combine(day, dt.time(12, 30), JST)
        out.append((t, o, h, l, c, vol))
        t += dt.timedelta(minutes=5)
    return out


def test_prereg_numbers_match_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "## J4 前の日に出来高が急増した銘柄の、次の日の寄り付き" in text
    assert (Y.UP, Y.DOWN) == (0.02, -0.02) and "急騰＝+2％以上／急落＝−2％以下" in text
    assert Y.GAP_BIG == 0.03 and "窓が+3％以上" in text and Y.WICK == 0.5 and "上げ幅の半分以上を戻した" in text
    assert Y.COST == 0.001 and "往復0.1％" in text and Y.MIN_CELL == 30 and "30件未満" in text
    assert (Y.TOP_N, Y.HOT_MIN_TURNOVER, Y.HOT_BASE_DAYS) == (20, 10.0, 20) and "売買代金10億円以上" in text
    for t in ("9:15", "9:30", "9:45", "10:00", "10:30", "11:30", "13:00", "14:00"):
        assert t in text
    import build_jp_rankings as B
    assert (B.TOP_N, B.HOT_MIN_TURNOVER, B.HOT_BASE_DAYS, B.HOT_MIN_BASE) == (Y.TOP_N, Y.HOT_MIN_TURNOVER, Y.HOT_BASE_DAYS, Y.HOT_MIN_BASE)


def test_price_at_times_and_lunch():
    day = dt.date(2026, 9, 1)
    prices = [(100 + i, 101 + i, 99 + i, 100.5 + i) for i in range(60)]     # 9:00〜（昼休みを挟んで）
    bars = _bars(day, prices)
    assert Y.price_at(bars, "09:15") == bars[2][4]                          # 9:10 の足の終値
    assert Y.price_at(bars, "11:30") == [b for b in bars if b[0].time() == dt.time(11, 25)][0][4]
    assert Y.price_at(bars, "13:00") == [b for b in bars if b[0].time() == dt.time(12, 55)][0][4]
    short = [b for b in bars if b[0].time() < dt.time(10, 0)]
    assert Y.price_at(short, "14:00") is None                               # 30分以内に足が無い


def test_day_record_classes_and_wick():
    day = dt.date(2026, 9, 1)
    # 寄り100 → 最初の15分で高値106 → 9:15 に103（上げ幅6のうち3を戻した＝半分）
    bars = _bars(day, [(100, 104, 100, 104), (104, 106, 103, 105), (105, 105, 102.5, 103)] + [(103, 103, 103, 103)] * 70)
    r = Y.day_record(bars, prev_close=98, prev_prev_close=90, prev_vol=1000, close=101)
    assert r["cls"] == "up" and abs(r["r15"] - 0.03) < 1e-12 and abs(r["wick"] - 0.5) < 1e-12
    assert abs(r["gap"] - (100 / 98 - 1)) < 1e-12 and abs(r["vol_share"] - 0.3) < 1e-12
    assert r["path"]["15:30"] == 101 and abs(Y.ret(r, "09:15", "15:30") - (101 / 103 - 1)) < 1e-12
    bars2 = _bars(day, [(100, 100, 97, 97.5)] * 3 + [(97.5, 97.5, 97.5, 97.5)] * 70)
    assert Y.day_record(bars2, 100, 100, 1000, 97)["cls"] == "down"
    late = _bars(day, [(101, 102, 100, 101)] * 10, start=(9, 5))
    assert Y.day_record(late, 100, 100, 1000, 100) is None                   # 9:00 の足が無く、寄り（日足の始値）も無い
    r2 = Y.day_record(late, 98, 100, 1000, 100, day_open=100)                # Yahoo が 9:00 を空で返した日＝寄りは日足の始値
    assert r2 is not None and abs(r2["r15"] - 0.01) < 1e-12 and abs(r2["gap"] - (100 / 98 - 1)) < 1e-12
    assert r2["wick"] is None and r2["vol_share"] is None                    # 最初の5分が分からない＝上ヒゲと出来高は数えない
    delayed = _bars(day, [(100, 100, 100, 100)] * 10, start=(9, 20))
    assert Y.day_record(delayed, 100, 100, 1000, 100, day_open=100) is None   # 寄り付きが 9:15 より遅れた日は使わない


def test_hot_lists_same_rule_as_rankings():
    days = [(dt.date(2026, 6, 1) + dt.timedelta(days=i)).isoformat() for i in range(30)]
    daily = {}
    for k in range(25):
        vols = [1e6] * 30
        vols[-1] = 1e6 * (k + 1)                     # 最後の日だけ出来高を k+1 倍
        daily[f"C{k:02d}"] = [(d, 2000.0, v) for d, v in zip(days, vols)]
    daily["THIN"] = [(d, 10.0, v) for d, v in zip(days, [1e3] * 29 + [1e6])]   # 売買代金が小さい＝入らない
    hot = Y.hot_lists(daily)
    last = hot[days[-1]]
    assert len(last) == 20 and "THIN" not in last and "C24" in last and "C00" not in last
    assert days[0] not in hot                                                 # 基準の日数が足りない日は決めない


def _rec(date, code, hot, cls, r_close_915, gap=0.0, wick=0.0, path_open=None):
    p915 = 100.0
    op = p915 / (1.03 if cls == "up" else 0.97 if cls == "down" else 1.0)
    path = {t: p915 for t in Y.TIMES}
    path["15:30"] = p915 * (1 + r_close_915)
    for t, v in (path_open or {}).items():
        path[t] = op * (1 + v)
    return {"code": code, "date": date, "hot": hot, "cls": cls, "gap": gap, "wick": wick, "open": op, "p915": p915,
            "path": path, "r15": p915 / op - 1, "vol_share": 0.2, "prev_ret": 0.0, "price": 1000.0, "akaji": False, "relvol": 4.0}


def test_analyze_verdicts():
    recs = []
    days = [(dt.date(2026, 8, 3) + dt.timedelta(days=i)).isoformat() for i in range(40)]
    for d in days:
        for j in range(10):
            # 急騰は大引けまでに必ず下げる（寄り天）。上ヒゲが長いものはもっと下げる。窓が大きいものほど急騰
            recs.append(_rec(d, f"U{j}", True, "up", -0.02 - (0.01 if j < 5 else 0), gap=0.04 if j < 6 else 0.0,
                             wick=0.6 if j < 5 else 0.1))
            recs.append(_rec(d, f"F{j}", True, "flat", 0.0, gap=0.0))
            recs.append(_rec(d, f"K{j}", False, "up", 0.0))
    res = Y.analyze(recs)
    assert res["p1"]["verdict"] == "寄りの急騰は、その日のうちに失速しやすい兆し"
    assert res["p3"]["verdict"] == "窓が大きいと、寄りのあとも上がりやすい兆し"
    assert res["p4"]["verdict"] == "上ヒゲの長い寄りの急騰は、その後さらに下げやすい兆し"
    assert res["days"] == 40 and res["cut"] == days[20]
    md = Y.render_md({"generated_at": "x", "prereg_sha256": "a" * 64, "result": dict(res, missing=[])})
    assert "投資助言ではありません" in md and "U0" not in md and "K1" not in md
    no_wick = [dict(r, wick=None) for r in recs]                                      # 上ヒゲが分からない日は P4 に入れない
    res2 = Y.analyze(no_wick)
    assert res2["p4"]["verdict"] == "見えない" and res2["n_up_with_900"] == 0 and res2["p1"]["verdict"] == res["p1"]["verdict"]
    flat = [dict(r, cls="flat") for r in recs if r["code"].startswith("K")]           # 急騰が無ければ P1 は見えない
    assert Y.analyze(flat)["p1"]["verdict"] == "見えない"


def test_exit_time_is_chosen_on_the_first_half_only():
    recs = []
    days = [(dt.date(2026, 8, 3) + dt.timedelta(days=i)).isoformat() for i in range(40)]
    for i, d in enumerate(days):
        early = i < 20
        for j in range(10):
            recs.append(_rec(d, f"F{j}", True, "flat", 0.0,
                             path_open={"09:45": 0.01 if early else -0.01, "13:00": -0.005 if early else 0.02}))
    res = Y.analyze(recs)
    assert res["p2"]["t_best"] == "09:45"                      # 前半だけで選ぶ（後半なら 13:00 だった）
    assert res["p2"]["verdict"] == "見えない"                  # 後半の 9:45 はマイナス
    assert abs(res["p2"]["confirm"]["mean"] - (-0.01 - Y.COST)) < 1e-9


def test_load_all_uses_prev_day_list_and_skips_today():
    today = dt.date(2026, 9, 28)
    days = [today - dt.timedelta(days=30 - i) for i in range(31)]            # 最後が今日

    def fetch(code, interval, rng):
        if interval == "1d":
            out = []
            for i, d in enumerate(days):
                v = 5e6 if (code == "HOT" and d == days[-3]) else (1e5 if code in ("A", "B") else 1e6)   # 2日前に出来高急増／A・B は売買代金が小さい
                out.append((dt.datetime.combine(d, dt.time(9, 0), JST), 2000, 2000, 2000, 2000.0, v))
            return out
        out = []
        for d in days[-3:]:
            out += _bars(d, [(2000, 2050, 2000, 2050)] * 3 + [(2050, 2050, 2040, 2040)] * 60)
        return out

    top = Y.TOP_N
    Y.TOP_N = 1                                                               # 銘柄が少ないので上位1つだけを「上位」にする
    try:
        recs, missing = Y.load_all(["HOT", "Z", "A", "B"], {}, today.isoformat(), fetch=fetch)
        diag = {}
        recs2, _ = Y.load_all(["HOT", "Z", "A", "B"], {}, today.isoformat(), fetch=fetch, diag=diag)
    finally:
        Y.TOP_N = top
    assert missing == [] and all(r["date"] < today.isoformat() for r in recs)
    hot_days = {r["date"] for r in recs if r["hot"] and r["code"] == "HOT"}
    assert hot_days == {days[-2].isoformat()}                                 # 急増の翌日だけが「前の日の上位」
    assert not any(r["hot"] for r in recs if r["code"] in ("A", "B"))         # 売買代金10億円未満は入らない
    assert len(recs2) == len(recs)                                            # 調べる版でも記録は同じ
    assert diag["5m_range"] == {"60d": 4} and diag["first_bar_time"] == {"09:00": 12}
    why = diag["hot_next_day_by_weekday"]                                     # 上位だった日の次の日＝記録になった／5分足なし
    assert sum(v.get("記録になった（9:00 の足あり）", 0) for v in why.values()) >= 1
    assert sum(v.get("次の日の5分足なし", 0) for v in why.values()) >= 1
    assert diag["5m_days_per_stock"] == {"min": 3, "median": 3, "max": 3} and "HOT" not in str(diag)
    top = Y.TOP_N

    def fetch905(code, interval, rng):                                        # 5分足の最初が 9:05（9:00 は空で捨てられた）
        rows = fetch(code, interval, rng)
        return rows if interval == "1d" else [b for b in rows if b[0].time() != dt.time(9, 0)]

    Y.TOP_N = 1
    try:
        recs3, _ = Y.load_all(["HOT", "Z", "A", "B"], {}, today.isoformat(), fetch=fetch905)
    finally:
        Y.TOP_N = top
    assert len(recs3) == len(recs) and all(r["wick"] is None for r in recs3)   # 捨てずに数える（上ヒゲだけ無し）
    assert Y.today_cutoff(dt.datetime(2026, 9, 28, 13, 40, tzinfo=JST)) == "2026-09-28"
    assert Y.today_cutoff(dt.datetime(2026, 9, 28, 16, 0, tzinfo=JST)) == "2026-09-29"


def test_workflow_installs_the_import_chain():
    """yori_lab → pillar_lab → exit_rule_backtest → generate_technical_alerts が yfinance を読む（2026-09-28 初回の実行がこれで落ちた）"""
    wf = open(".github/workflows/yori-lab.yml", encoding="utf-8").read()
    line = [l for l in wf.splitlines() if "pip install" in l][0]
    for pkg in ("numpy", "pandas", "yfinance"):
        assert pkg in line.split(), pkg

def test_raw_shape_tells_empty_900_from_shift():
    day1, day2 = dt.date(2026, 9, 1), dt.date(2026, 9, 2)

    def fetch(code, interval, rng):
        if interval == "1d":
            return [(dt.datetime.combine(d, dt.time(9, 0), JST), 100.0, 101, 99, 100, 1000) for d in (day1, day2)]
        rows = [(dt.datetime.combine(day1, dt.time(9, 0), JST), 100.0, 101, 99, 100, 500)]      # ふつうの日
        rows += [(dt.datetime.combine(day1, dt.time(9, 5), JST), 100.0, 101, 99, 100, 500)]
        rows += [(dt.datetime.combine(day2, dt.time(9, 0), JST), None, None, None, None, 400)]   # 9:00 が空（出来高だけある）
        rows += [(dt.datetime.combine(day2, dt.time(9, 5), JST), 102.0, 103, 101, 102, 300)]
        return rows

    out = Y.raw_shape(["X"], fetch=fetch)
    assert out["09:00"]["日数"] == 1 and out["09:05"]["日数"] == 1
    assert out["09:05"]["空の行の時刻"] == {"09:00（出来高あり）": 1}
    assert out["09:05"]["出来高の比"]["中央値"] == 0.3 and out["09:00"]["出来高の比"]["中央値"] == 1.0
    assert out["09:05"]["最初の足の始値÷日足の始値"]["中央値"] == 1.02

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
