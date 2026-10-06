# -*- coding: utf-8 -*-
"""J10 高値更新の翌朝の罠（highs_trap_lab.py）のテスト。2026-10-06 新設。

値動きはすべて作り物（ネットワークに出ない）。確かめること＝①高値更新の決め方が build_jp_highs.ytd_extreme と同じ
②10:00 の値（9:00 の1時間足の終値・無ければ 10:00 の足の始値）③目印（窓・前の日の高値・上ヒゲ・前の日の上げ幅）
④翌朝が 2026-10-05 より後の日は使わない ⑤幅（差がはっきりあれば0をまたがない・無ければまたぐ）⑥判定の言い分け
⑦出力に銘柄コードを出さない ⑧事前登録と定数の一致。

実行:  python tests/test_highs_trap_lab.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import json
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import build_jp_highs as H  # noqa: E402
import highs_trap_lab as T  # noqa: E402

JST = T.P.JST


def _bdays(start, n):
    d, out = dt.date.fromisoformat(start), []
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += dt.timedelta(days=1)
    return out


def _walk(n, seed, start="2023-10-02"):
    """[(日付, 始, 高, 安, 終, 出来高)] の作り物（ときどきデータの誤り＝前の日の2倍の高値を混ぜる）"""
    rnd = random.Random(seed)
    c, out = 1000.0, []
    for d in _bdays(start, n):
        o = c * (1 + rnd.gauss(0, 0.01))
        c2 = o * (1 + rnd.gauss(0.0005, 0.015))
        h = max(o, c2) * (1 + abs(rnd.gauss(0, 0.006)))
        lo = min(o, c2) * (1 - abs(rnd.gauss(0, 0.006)))
        if rnd.random() < 0.003:
            h = c * 2.0
        out.append((d, o, h, lo, c2, 1e5))
        c = c2
    return out


def _5m(day, prices):
    """prices＝[(始, 高, 安, 終)] を 9:00 から5分おきに"""
    t = dt.datetime.combine(dt.date.fromisoformat(day), dt.time(9, 0), JST)
    return [(t + dt.timedelta(minutes=5 * i), o, h, lo, c, 100.0) for i, (o, h, lo, c) in enumerate(prices)]


def _1h(day, rows):
    """rows＝[(時, 始, 終)]"""
    d = dt.date.fromisoformat(day)
    return [(dt.datetime.combine(d, dt.time(hh, 0), JST), o, max(o, c), min(o, c), c, 100.0) for hh, o, c in rows]


def test_prereg_numbers_match_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "## J10 高値更新の翌朝、寄りで買うと負ける「罠」を" in text and "## J10b 寄り前の気配は" in text
    assert T.GAP_UP == 0.01 and "Q1 窓が +1％ 以上" in text
    assert T.WICK == 0.5 and "0.5 以上＝高値を付けたのに値幅の下半分で引けた" in text
    assert T.PREV_BIG == 0.05 and "Q4 前の日に +5％ 以上上げた" in text
    assert T.COST == 0.001 and "往復 0.1％" in text and T.TRAP == -0.01 and "−1％ 以下（費用前）" in text
    assert T.N_Q == 5 and abs(T.ALPHA - 0.01) < 1e-12 and "p＜0.05÷5＝99％ の幅" in text and T.N_BOOT == 10000
    assert T.MIN_N == 30 and "30件未満" in text and T.MAX_MOVE == 0.25 and "±25％" in text
    assert T.END_DAY == "2026-10-05" and "翌朝が 2026-10-05 までの日だけ" in text


def test_ytd_flags_match_build_jp_highs():
    for seed in range(6):
        daily = _walk(760, seed)
        bars = [(d, h, lo, c, v) for d, o, h, lo, c, v in daily]
        fast = T.ytd_flags(bars)
        slow = [k > 0 and H.ytd_extreme(bars[:k + 1], H.window_start(bars[k][0])[0]) is not None for k in range(len(bars))]
        assert fast == slow, f"seed {seed}: {sum(fast)} vs {sum(slow)}"
        assert sum(fast) > 5        # 作り物でも高値更新はそれなりに起きる（突き合わせが空振りしていない）


def test_ytd_flags_window_rules():
    # 1〜3月は前の年の1月から（昨年来）。前の年の高値を超えなければ更新ではない
    days = _bdays("2025-01-06", 300)
    bars = [(d, 100.0, 99.0, 99.5, 1.0) for d in days]
    i_jun = days.index("2025-06-02")
    bars[i_jun] = (days[i_jun], 140.0, 99.0, 100.0, 1.0)              # 2025年6月の高値 140（ここは更新）
    i_feb = next(i for i, d in enumerate(days) if d >= "2026-02-02")
    bars[i_feb] = (days[i_feb], 120.0, 99.0, 100.0, 1.0)              # 2026年2月 120 は 140 を超えない
    f = T.ytd_flags(bars)
    assert f[i_jun] is True and f[i_feb] is False
    # 前の営業日が20未満は数えない・同じ値は更新に数えない
    bars2 = [(d, 100.0, 99.0, 99.5, 1.0) for d in days[:40]]
    bars2[10] = (days[10], 120.0, 99.0, 100.0, 1.0)
    assert T.ytd_flags(bars2)[10] is False
    bars2 = [(d, 100.0, 99.0, 99.5, 1.0) for d in days[:40]]
    bars2[31] = (days[31], 100.5, 99.0, 100.0, 1.0)
    f2 = T.ytd_flags(bars2)
    assert f2[30] is False and f2[31] is True


def test_price_1000_and_fallback():
    day = "2026-09-01"
    assert T.price_1000(_1h(day, [(9, 100, 103), (10, 103, 104)])) == (103, False)
    assert T.price_1000(_1h(day, [(10, 102, 104), (11, 104, 105)])) == (102, True)
    assert T.price_1000(_1h(day, [(11, 104, 105)])) == (None, None)


def test_yoriten():
    day = "2026-09-01"
    assert T.yoriten(_5m(day, [(100, 100, 98, 99)] + [(99, 99.5, 97, 98)] * 6), 100) is True
    assert T.yoriten(_5m(day, [(100, 101, 98, 99)] + [(99, 99.5, 97, 98)] * 6), 100) is False
    late = [(t + dt.timedelta(minutes=5), o, h, lo, c, v) for t, o, h, lo, c, v in _5m(day, [(100, 100, 98, 99)] * 6)]
    assert T.yoriten(late, 100) is None          # 9:00 の足が無い日は数えない


def _stock(event_day_close=110.0, event_high=115.0, event_low=100.0, next_open=112.0):
    """60営業日の横ばいのあと、ある日に高値を更新し、その翌朝を見る作り物"""
    days = _bdays("2026-06-01", 90)
    daily = [(d, 100.0, 101.0, 99.0, 100.0, 1e5) for d in days]
    k = 70
    daily[k] = (days[k], 101.0, event_high, event_low, event_day_close, 1e5)
    daily[k + 1] = (days[k + 1], next_open, next_open + 2, next_open - 3, next_open - 1, 1e5)
    return days, daily, k


def test_stock_records_features_and_outcomes():
    days, daily, k = _stock()
    t = days[k + 1]
    m5 = {t: _5m(t, [(112, 112, 110, 111)] + [(111, 111.5, 109, 110)] * 4 + [(110, 110, 108, 109.76)] * 3)}
    h1 = {t: _1h(t, [(9, 112, 109.2), (10, 109.2, 109)]), days[k + 2]: _1h(days[k + 2], [(9, 100, 101)])}
    ev, ctl = T.stock_records("9999", daily, m5, h1, akaji=False, end_day="2026-12-31")
    hit = [r for r in ev if r["date"] == t]
    assert len(hit) == 1
    r = hit[0]
    assert abs(r["gap"] - (112 / 110 - 1)) < 1e-12 and r["above_high"] is False      # 112 < 前の日の高値 115
    assert abs(r["wick"] - (115 - 110) / (115 - 100)) < 1e-12                           # 1/3＝短い
    assert abs(r["prev_ret"] - (110 / 100 - 1)) < 1e-12
    assert abs(r["r1000"] - (109.2 / 112 - 1)) < 1e-12 and r["fb"] is False
    assert abs(r["r930"] - (109.76 / 112 - 1)) < 1e-12                                  # 9:25 の足の終値
    assert r["yoriten"] is True
    assert [c["date"] for c in ctl] == [days[k + 2]] and "gap" not in ctl[0]            # 比べる相手＝前の日に更新していない日・値動きだけ


def test_end_day_excludes_later_mornings():
    days, daily, k = _stock()
    t = days[k + 1]
    h1 = {t: _1h(t, [(9, 112, 113)])}
    ev, _ = T.stock_records("9999", daily, {}, h1, end_day=days[k])           # 翌朝が end_day より後
    assert not [r for r in ev if r["date"] == t]
    ev, _ = T.stock_records("9999", daily, {}, h1, end_day=t)
    assert [r for r in ev if r["date"] == t]


def test_bad_values_are_dropped():
    drops = {"n": 0}
    o = T.outcomes(100.0, 100.0, None, _1h("2026-09-01", [(9, 100, 140)]), drops)
    assert o is None and drops["n"] == 1      # +40％ はデータの誤り


def test_boot_detects_a_clear_difference_and_not_noise():
    rnd = random.Random(1)
    rows = []
    for i in range(200):
        day = f"d{i:03d}"
        for j in range(8):
            a = j < 3
            rows.append({"date": day, "code": f"c{rnd.randrange(80)}", "a": a, "v": (-0.01 if a else 0.0) + rnd.gauss(0, 0.01)})
    d = T.safe(rows, lambda r: r["v"], lambda r: r["a"])
    assert d["hi"] < 0 and d["lo"] < d["diff"] < d["hi"]
    for r in rows:
        r["v"] = rnd.gauss(0, 0.01)
    d = T.safe(rows, lambda r: r["v"], lambda r: r["a"])
    assert d["lo"] < 0 < d["hi"]
    m = T.safe(rows, lambda r: r["v"])
    assert m["lo"] < 0 < m["hi"] and m["n"] == len(rows)


def test_judge_flag_variants():
    full = {"n_a": 100, "n_b": 300, "diff": -0.01, "lo": -0.02, "hi": -0.002}
    e, l = {"diff": -0.01}, {"diff": -0.008}
    ok60 = {"n_a": 40, "n_b": 100, "diff": -0.005}
    assert T.judge_flag(full, e, l, -0.004, ok60) == "罠の目印（入らない方がいい兆し）"
    assert "件数不足で確かめられず" in T.judge_flag(full, e, l, -0.004, dict(ok60, n_a=10))
    assert T.judge_flag(full, e, l, -0.004, dict(ok60, diff=0.003)).startswith("10:00 だけの兆し")
    assert T.judge_flag(full, e, {"diff": 0.001}, -0.004, ok60) == "見えない"       # 後半が逆
    assert T.judge_flag(full, e, l, 0.002, ok60) == "見えない"                      # 目印ありの組が費用後プラス
    assert T.judge_flag(dict(full, hi=0.001), e, l, -0.004, ok60) == "見えない"     # 幅が0をまたぐ
    assert T.judge_flag(dict(full, n_a=20), e, l, -0.004, ok60) == "件数不足"
    pos = {"n_a": 100, "n_b": 300, "diff": 0.01, "lo": 0.002, "hi": 0.02}
    assert T.judge_flag(pos, {"diff": 0.01}, {"diff": 0.01}, 0.004, {"n_a": 40, "diff": 0.005}) == "強さの目印（兆し）"


def test_judge_q0():
    neg = {"n": 900, "mean": -0.004, "lo": -0.007, "hi": -0.001}
    assert T.judge_q0(neg, {"mean": -0.004}, {"mean": -0.003}, {"n": 200, "mean": -0.002}) == "高値更新の翌朝の寄り買いは、平均で負けやすい兆し"
    assert T.judge_q0(dict(neg, hi=0.001), {"mean": -0.004}, {"mean": -0.003}, {"n": 200, "mean": -0.002}) == "見えない"
    assert T.judge_q0({"n": 3, "mean": 0.0, "lo": None, "hi": None}, {}, {}, {}) == "件数不足"


def test_analyze_and_render_have_no_codes():
    rnd = random.Random(3)
    ev, ctl = [], []
    for i in range(120):
        day = (dt.date(2025, 1, 6) + dt.timedelta(days=i)).isoformat()
        for j in range(6):
            code = f"Z{rnd.randrange(50)}Q"
            ev.append({"date": day, "code": code, "r915": rnd.gauss(0, 0.01), "r930": rnd.gauss(0, 0.01) if i > 60 else None,
                       "r1000": rnd.gauss(0, 0.01), "rclose": rnd.gauss(0, 0.02), "fb": False, "yoriten": rnd.random() < 0.3,
                       "gap": rnd.gauss(0, 0.01), "above_high": rnd.random() < 0.4, "wick": rnd.random(),
                       "prev_ret": rnd.gauss(0.02, 0.03), "akaji": rnd.random() < 0.1})
            ctl.append({"date": day, "code": f"Y{j}W", "r915": 0.0, "r930": 0.0, "r1000": 0.0, "rclose": 0.0, "yoriten": False})
    res = {"generated_at": "2026-10-06T20:00+09:00", "prereg_sha256": "0" * 64,
           "result": dict(T.analyze(ev, ctl), n_universe=400, n_missing={"daily": 0, "h1": 0, "m5": 0}, n_dropped=0)}
    out = json.dumps(res, ensure_ascii=False) + T.render_md(res)
    for code in {r["code"] for r in ev + ctl}:
        assert code not in out, code
    md = T.render_md(res)
    assert "Q0 そもそも" in md and "Q4 前の日に +5％ 以上上げた" in md and "投資助言ではありません" in md
    for key in ("q0", "q1", "q2", "q3", "q4"):
        assert res["result"][key]["verdict"]


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
