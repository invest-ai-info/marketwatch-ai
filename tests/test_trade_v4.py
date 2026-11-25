# -*- coding: utf-8 -*-
"""trade_v4.py（取引の記録の、決まりの紙 v4 の項目）のテスト。作り物の足だけ・ネットは使わない"""
import datetime as dt
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
import trade_fill as F  # noqa: E402
import trade_journal as T  # noqa: E402
import trade_v4 as V  # noqa: E402
from test_trade_fill import BASE, D0, at, bars, ones, price, ts  # noqa: E402

# 14:40 に抜け（線 +2）→ 14:50 に +40（38pips）→ 15:00 の足で +4 まで押す（線の 2pips 手前＝当たり・94.7%）→ 15:05 は +14 前後
MV = {"14:40": (0, 12, 0, 10), "14:45": (10, 25, 9, 24), "14:50": (24, 40, 23, 38), "14:55": (38, 39, 30, 32), "15:00": (29, 30, 4, 14)}
WEAK = {"14:40": (0, 5, 0, 4), "14:45": (4, 8, 4, 7), "14:50": (7, 11, 7, 10), "14:55": (10, 10, 8, 9), "15:00": (9, 9, 8, 9)}      # 抜けただけで伸びない


def world(side=1, eur=MV, gbp=WEAK, usd=MV, **kw):
    return {"USDJPY": bars(BASE["USDJPY"], usd, side=side, **kw), "EURJPY": bars(BASE["EURJPY"], eur, side=side, **kw), "GBPJPY": bars(BASE["GBPJPY"], gbp, side=side, **kw)}


def minutes(side=1, px=None):
    px = px or {"USDJPY": 14.0, "EURJPY": 14.0, "GBPJPY": 9.0}
    return {p: ones(p, side=side, px=v, start="15:05") for p, v in px.items()}


def run(side=1, pair="EURJPY", hm="15:06", b5=None, b1=None, **kw):
    b5 = world(side) if b5 is None else b5
    b1 = minutes(side) if b1 is None else b1
    return V.analyze(b5, b1, pair, "buy" if side > 0 else "sell", at(hm, 8), **kw)


def flat(p, start="00:00", side=1):
    return bars(BASE[p], side=side)


# ── 向き（15分足 EMA10 の1時間の動き） ─────────────────────────

def test_state_has_a_border_zone():
    S = V.state_of
    assert [S(x, 2.0, 0.2) for x in (2.2, 2.19, 1.81, 1.8, 0.0, -1.8, -1.81, -2.19, -2.2, None)] == [1, None, None, 0, 0, 0, None, None, -1, None]
    assert [S(x, 0.5, 0.1) for x in (0.6, 0.59, 0.41, 0.4, -0.4, -0.5, -0.6)] == [1, None, None, 0, 0, None, -1]


def test_registered_numbers_are_the_same_as_oj3():
    assert (V.USD_MIN, V.EG_MIN, V.FAR, V.MOM, V.AGE, V.AGO, V.DEP, V.TOUCH_N, V.NEAR) == (2.0, 0.5, 20.0, 6, 24, 6, 50.0, 3, 3.0)
    assert (V.LINE_FROM, V.LINE_TO, V.S1_FROM, V.S2_FROM, V.OLD) == (480, 900, 720, 905, 6)
    assert (V.USD_TOL, V.EG_TOL) == (0.2, 0.1)


def test_slope_is_the_ema15_now_minus_12_bars_ago():
    b5 = world()
    r = run(b5=b5)
    u = [b for b in b5["USDJPY"] if b[0] < ts("15:05")]
    e = F.ema15(u)
    assert r["usd"][0] == pytest.approx((e[-1] - e[-13]) / 0.01, abs=0.01) and r["usd"][1] == 1
    g = {b[0]: b[4] for b in b5["GBPJPY"]}
    q = [(b[0], 0, 0, 0, b[4] / g[b[0]]) for b in b5["EURJPY"] if b[0] < ts("15:05")]
    x = F.ema15(q)
    assert r["eg"][0] == pytest.approx((x[-1] - x[-13]) * 1e4, abs=0.01) and r["eg"][1] == 1


def test_slope_without_enough_bars_is_unknown():
    assert V.slope([], 0.01) is None
    b = [(300 * k, 0, 0, 0, 100.0) for k in range(14)]
    assert V.slope(b, 0.01) is None                                  # 12本前の MA がまだ無い
    assert V.slope(b[:12], 0.01) is None and V.slope(b[:13], 0.01) is None
    b = [(300 * k, 0, 0, 0, 100.0) for k in range(40)]
    assert V.slope(b, 0.01) == 0.0
    b = [(300 * k, 0, 0, 0, 100.0 + 0.01 * k * k) for k in range(60)]
    for n in range(45, 60):                                          # 15分足の切れ目がどこにあっても、ちょうど12本前と比べる
        e = F.ema15(b[:n])
        assert V.slope(b[:n], 0.01) == pytest.approx((e[-1] - e[-13]) / 0.01, abs=0.006)
    assert any(F.ema15(b[:n])[-13] != F.ema15(b[:n])[-12] for n in range(45, 60))


def test_direction_ignores_the_entry_bar():
    a = run()
    b5 = world()
    for p in b5:
        b5[p] = [b if b[0] < ts("15:05") else (b[0], b[1], b[2] + 1, b[3] - 1, b[4] - 1) for b in b5[p]]
    b = run(b5=b5)
    assert a["usd"] == b["usd"] and a["eg"] == b["eg"] and a["flags"] == b["flags"]


# ── 強いほう・見るペア ───────────────────────────────

def test_strong_pair_is_by_eurgbp_only():
    r = run()                                                        # 買い・ユーロポンドが上＝ユーロ円
    assert r["strong"] == "EURJPY" and r["pick"] is True and r["watch"] == "GBPJPY"
    assert run(pair="GBPJPY")["pick"] is False
    r = run(pair="GBPJPY", b5=world(eur=WEAK, gbp=MV))               # 下＝ポンド円
    assert r["eg"][1] == -1 and r["strong"] == "GBPJPY" and r["pick"] is True and r["watch"] == "EURJPY"


def test_strong_pair_for_sells():
    r = run(side=-1)                                                 # 売り・ユーロ円のほうが下がる＝ユーロポンドは下＝ユーロ円
    assert r["eg"][1] == -1 and r["usd"][1] == -1 and r["strong"] == "EURJPY" and r["pick"] is True
    r = run(side=-1, pair="GBPJPY", b5=world(-1, eur=WEAK, gbp=MV))
    assert r["eg"][1] == 1 and r["strong"] == "GBPJPY" and r["pick"] is True


def test_flat_eurgbp_has_no_strong_pair():
    assert V.strong_of(1, 0) == (None, True) and V.strong_of(1, None) == (None, False)
    assert V.strong_of(1, 1) == ("EUR", True) and V.strong_of(1, -1) == ("GBP", True) and V.strong_of(-1, 1) == ("GBP", True) and V.strong_of(-1, -1) == ("EUR", True)
    b5 = {p: flat(p) for p in F.PAIRS}
    r = run(b5=b5)
    assert r["eg"][1] == 0 and r["strong"] is None and r["pick"] is False


def test_dollar_yen_is_never_the_strong_pair():
    r = run(pair="USDJPY")
    assert r["pick"] is False and r["watch"] is None and r["kata"] is None and r["flags"]["fresh"] is None


# ── 線と抜け ────────────────────────────────────

def one(moves, hm, s=1, **kw):
    """ポンド円の、hm の足が始まる前までの足 → いま続いている抜け"""
    d = [b for b in bars(BASE["GBPJPY"], moves, side=s, **kw) if ts("00:00") <= b[0] < ts(hm)]
    return V.leg_now(d, s)


def test_s1_line_is_30_minutes_old_or_older_and_from_noon():
    x = one(MV, "14:45")
    assert x["L"] == pytest.approx(price(2)) and x["age"] == 0
    up = {"13:00": (0, 7, 0, 5), "13:25": (5, 12, 5, 10)}            # 13:00 の抜けのあと
    assert one(up, "13:30")["L"] == pytest.approx(price(2))          # 13:00 からの抜けが続いている（線は最初の抜けのまま）
    up = {"13:00": (-6, 7, -6, -6), "13:25": (-6, 9, -6, 8)}         # 13:00 はヒゲだけ＝25分前の高値 +7 は線に入れない
    assert one(up, "13:30")["L"] == pytest.approx(price(2))
    up = {"13:00": (-6, 7, -6, -6), "13:30": (-6, 9, -6, 8)}         # ちょうど30分前の高値は線に入れる
    assert one(up, "13:35")["L"] == pytest.approx(price(7))
    assert one({"11:50": (-6, 5, -6, 4), "11:55": (4, 4, 4, 4)}, "12:00") is None    # 12時より前の抜けは見ない
    assert one({"11:50": (-6, 5, -6, 4), "11:55": (4, 4, 4, 4)}, "12:15") is None    # 12時からも、1本前の終値がもう線の外なら抜けではない
    assert one({"12:10": (-6, 6, -6, 5)}, "12:20", start="12:00") is None            # 30分前の足が無いうちは見ない


def test_break_needs_a_close_outside_not_on_the_line():
    x = one({"14:40": (0, 2, 0, 2), "14:45": (2, 10, 2, 8)}, "14:50")                 # 14:40 は線ちょうど
    assert x["age"] == 0 and one({"14:40": (0, 2, 0, 2)}, "14:45") is None


def test_first_of_two_equal_extremes():
    assert one(dict(MV, **{"14:55": (38, 40, 30, 32)}), "15:05")["ago"] == 2          # 14:50 と 14:55 が同じ高さ＝先に着いたほう


def test_s2_line_includes_the_1500_bar_and_is_used_first():
    mv = {"13:00": (0, 7, 0, 5), "15:00": (5, 9, 5, 6), "15:20": (6, 14, 6, 12)}
    assert one(mv, "15:20")["L"] == pytest.approx(price(2))          # S1（13:00 の抜け）
    x = one(mv, "15:25")
    assert x["L"] == pytest.approx(price(9)) and x["age"] == 0       # S2（15:00 の足の高値 +9 を抜けた）
    assert one({"15:00": (-6, -6, -6, -6), "15:05": (-6, 4, -6, 3)}, "15:10")["L"] == pytest.approx(price(2))


def test_break_ends_on_or_inside_the_line():
    mv = dict(MV, **{"15:00": (10, 10, 2, 2)})                       # 終値が線ちょうど＝終わり
    assert one(mv, "15:00") is not None and one(mv, "15:05") is None
    mv = dict(MV, **{"15:00": (10, 10, 2, 2), "15:05": (2, 6, 2, 5)})
    x = one(mv, "15:10")
    assert x["age"] == 0                                             # また外で確定＝新しい抜け


def test_extreme_first_20_and_ago():
    x = one(MV, "15:05")
    assert x["ext"] == pytest.approx(price(40)) and x["ex"] == pytest.approx(38) and x["t20"] == 1 and x["age"] == 4 and x["ago"] == 2
    y = one(MV, "15:05", s=-1)
    assert y["L"] == pytest.approx(price(2, -1)) and y["ext"] == pytest.approx(price(40, -1)) and (y["ex"], y["t20"], y["age"], y["ago"]) == (pytest.approx(38), 1, 4, 2)
    assert one(WEAK, "15:05")["t20"] is None


def test_move_before_0800_does_not_make_the_line():
    assert one(dict(MV, **{"07:55": (-6, 30, -6, -6)}), "15:05")["L"] == pytest.approx(price(2))


# ── 入口の項目 ───────────────────────────────────

def test_all_marks_in_a_clean_push():
    r = run()
    assert r["flags"] == {"both_broken": True, "usd_dir": True, "pick_eg": True, "far20": True, "fresh": True, "pull50": True, "touch1": True}
    assert r["kata"] == "push" and r["watch_line"] == pytest.approx(price(2, pair="GBPJPY")) and r["watch_ext"] == pytest.approx(price(11, pair="GBPJPY"))
    r = run(side=-1)
    assert all(r["flags"].values()) and r["kata"] == "push" and r["watch_ext"] == pytest.approx(price(11, -1, "GBPJPY")) and r["watch_line"] == pytest.approx(price(2, -1, "GBPJPY"))


def test_both_pairs_must_be_broken():
    r = run(b5=world(gbp={}))
    assert r["flags"]["both_broken"] is False and r["watch_line"] is None and r["kata"] == "push"      # 型は名前だけ（もう一方の抜けは別の項目）
    r = run(b5=world(eur={}), pair="EURJPY")
    assert r["flags"]["both_broken"] is False and r["kata"] is None and r["named"] is False           # 入ったペアがまだ抜けていない＝②かもしれない


def test_usd_dir():
    b5 = world(usd={})
    assert run(b5=b5)["usd"][1] == 0 and run(b5=b5)["flags"]["usd_dir"] is False
    b5 = world()
    b5["USDJPY"] = bars(BASE["USDJPY"], MV, side=-1)
    assert run(b5=b5)["usd"][1] == -1 and run(b5=b5)["flags"]["usd_dir"] is False


def test_kata_range_when_dollar_yen_is_flat():
    assert run(b5=world(usd={}))["kata"] == "range"
    assert run(b5=world(usd={}), pair="GBPJPY")["kata"] == "range"   # 入ったペアが抜けていれば、型は④（強いほうかは別の項目）
    assert run(b5=world(usd={}, gbp={}), pair="GBPJPY")["kata"] is None      # 入ったペアがまだ抜けていない
    b5 = world()
    b5["USDJPY"] = bars(BASE["USDJPY"], MV, side=-1)
    assert run(b5=b5)["kata"] is None                                # ドル円が逆向き＝どの型でもない


def test_kata_is_unknown_on_the_border():
    b5 = world(usd={})
    u = [b for b in b5["USDJPY"] if b[0] < ts("15:05")]
    for k in range(60):                                              # ドル円を、1時間の動きがちょうど 2pips になるまで動かす
        mv = {"14:40": (-6, -6 + 0.1 * k, -6, -6 + 0.1 * k)}
        b5["USDJPY"] = bars(BASE["USDJPY"], mv)
        if abs(run(b5=b5)["usd"][0] - 2.0) < 0.1:
            break
    r = run(b5=b5)
    assert abs(r["usd"][0] - 2.0) < 0.1 and r["usd"][1] is None and r["flags"]["usd_dir"] is None and r["kata"] is None and len(u)


def test_far20():
    small = dict(WEAK)
    assert run(b5=world(eur=small))["flags"]["far20"] is False
    slow = {"13:30": (0, 12, 0, 10), "14:50": (10, 40, 10, 38), "14:55": (38, 39, 30, 32), "15:00": (29, 30, 4, 14)}      # 20pips まで80分
    assert run(b5=world(eur=slow))["flags"]["far20"] is False
    edge = dict(MV, **{"14:45": (10, 12, 9, 11), "14:50": (11, 22.5, 11, 20), "14:55": (20, 20, 18, 18), "15:00": (18, 18, 4, 14)})                 # いちばん遠く 20.5pips＝線が 1pip ずれたら変わる
    assert run(b5=world(eur=edge))["flags"]["far20"] is None


def test_far20_at_30_minutes_counts():
    late = {"14:20": (0, 12, 0, 10), "14:50": (10, 40, 10, 38), "14:55": (38, 39, 30, 32), "15:00": (29, 30, 4, 14)}      # 抜けてから6本目
    assert run(b5=world(eur=late))["flags"]["far20"] is True
    late = {"14:15": (0, 12, 0, 10), "14:50": (10, 40, 10, 38), "14:55": (38, 39, 30, 32), "15:00": (29, 30, 4, 14)}
    assert run(b5=world(eur=late))["flags"]["far20"] is False


def test_fresh_is_about_the_entered_pair():
    old = {"13:00": (0, 30, 0, 28), "14:50": (28, 40, 28, 38), "14:55": (38, 39, 30, 32), "15:00": (29, 30, 4, 14)}       # 抜けてから 25本（13:00 → 15:05）
    r = run(b5=world(eur=old))
    assert r["flags"]["fresh"] is True                               # 24本（15:00 の足まで）
    old["12:55"] = old.pop("13:00")
    assert run(b5=world(eur=old))["flags"]["fresh"] is False
    stale = {"14:20": (0, 40, 0, 30), "15:00": (30, 30, 4, 14)}      # いちばん遠く（14:20）から8本
    assert run(b5=world(eur=stale))["flags"]["fresh"] is False
    assert run(b5=world(eur=dict(stale, **{"14:30": (30, 41, 30, 30)})))["flags"]["fresh"] is True                        # 6本


def test_pull50_on_either_pair_that_went_20_pips():
    shallow = dict(MV, **{"15:00": (29, 30, 23, 26)})                # (40−23)÷38＝45%
    b1 = minutes(px={"USDJPY": 14.0, "EURJPY": 26.0, "GBPJPY": 9.0})
    assert run(b5=world(eur=shallow), b1=b1)["flags"]["pull50"] is False
    assert run(b5=world(eur=shallow, gbp=MV), b1=dict(b1, GBPJPY=ones("GBPJPY", px=14.0, start="15:05")))["flags"]["pull50"] is True      # 押したのは見るペア
    border = dict(MV, **{"15:00": (29, 30, 21, 26)})                 # ちょうど50%＝境目
    assert run(b5=world(eur=border), b1=b1)["flags"]["pull50"] is None
    assert run(b5=world(eur=WEAK), b1=b1)["flags"]["pull50"] is False    # 20pips 伸びたペアが無い
    deep = {"14:40": (0, 12, 0, 10), "14:45": (10, 20, 9, 18), "14:50": (18, 18, 12, 14), "14:55": (14, 14, 10, 12), "15:00": (12, 12, 4, 9)}      # 18pips しか伸びず 89% 押した
    assert run(b5=world(eur=deep))["flags"]["pull50"] is False


def test_close_of_the_extreme_bar_counts_as_a_pull():
    mv = dict(MV, **{"14:50": (24, 30, 23, 28), "14:55": (28, 30, 27, 29), "15:00": (29, 40, 10, 12)})      # いちばん遠くの足そのものが +12 で終わった
    b1 = minutes(px={"USDJPY": 14.0, "EURJPY": 38.0, "GBPJPY": 9.0})
    assert run(b5=world(eur=mv), b1=b1)["flags"]["pull50"] is True
    b1["EURJPY"] = ones("EURJPY", {"15:05": (14, 60, 14, 20), "15:06": (58, 58, 58, 58)}, px=58.0, start="15:05")       # 1分足でも同じ
    assert run(b1=b1)["flags"]["pull50"] is True


def test_high_of_the_entry_minute_is_not_an_extreme():
    b1 = minutes()
    b1["EURJPY"] = ones("EURJPY", {"15:06": (14, 60, 14, 14)}, px=14.0, start="15:05")
    assert run(b1=b1)["legs"]["EURJPY"]["ext"] == pytest.approx(price(40, pair="EURJPY"))


def test_new_extreme_in_the_entry_bar_is_fresh_and_can_reach_20_pips():
    stale = {"14:20": (0, 40, 0, 30), "15:00": (30, 30, 4, 14)}
    b1 = minutes()
    b1["EURJPY"] = ones("EURJPY", {"15:05": (14, 60, 14, 14)}, px=14.0, start="15:05")
    assert run(b5=world(eur=stale))["flags"]["fresh"] is False and run(b5=world(eur=stale), b1=b1)["flags"]["fresh"] is True
    low = {"14:40": (0, 12, 0, 10), "14:45": (10, 16, 9, 14), "15:00": (14, 14, 9, 10)}
    assert run(b5=world(eur=low))["flags"]["far20"] is False
    b1["EURJPY"] = ones("EURJPY", {"15:05": (14, 27, 14, 14)}, px=14.0, start="15:05")                                   # 抜けてから5本目（入る足）で 25pips
    r = run(b5=world(eur=low), b1=b1)
    assert r["flags"]["far20"] is True and r["legs"]["EURJPY"]["t20"] == 5


def test_pull_counts_the_minutes_before_entry_but_not_after():
    shallow = dict(MV, **{"15:00": (29, 30, 25, 26)})
    b1 = minutes(px={"USDJPY": 14.0, "EURJPY": 26.0, "GBPJPY": 9.0})
    dip = ones("EURJPY", {"15:06": (26, 26, 10, 12)}, px=26.0, start="15:05")
    assert run(b5=world(eur=shallow), b1=dict(b1, EURJPY=dip))["flags"]["pull50"] is True       # 入った分まで
    dip = ones("EURJPY", {"15:07": (26, 26, 10, 12)}, px=26.0, start="15:05")
    assert run(b5=world(eur=shallow), b1=dict(b1, EURJPY=dip))["flags"]["pull50"] is False


def test_low_before_the_extreme_is_not_a_pull():
    mv = {"14:40": (0, 26, 0, 25), "14:45": (25, 25, 3, 20), "14:50": (20, 40, 20, 38), "14:55": (38, 39, 36, 37), "15:00": (37, 38, 35, 36)}
    b1 = minutes(px={"USDJPY": 14.0, "EURJPY": 36.0, "GBPJPY": 9.0})
    assert run(b5=world(eur=mv), b1=b1)["flags"]["pull50"] is False


def test_new_extreme_inside_the_entry_bar():
    b1 = minutes()
    b1["EURJPY"] = ones("EURJPY", {"15:05": (14, 60, 14, 58)}, px=58.0, start="15:05")
    r = run(b1=b1)
    assert r["legs"]["EURJPY"]["ext"] == pytest.approx(price(60, pair="EURJPY")) and r["flags"]["pull50"] is False


def test_touch_is_any_of_three_pairs_in_the_last_three_bars_or_the_entry_bar():
    no = dict(MV, **{"15:00": (29, 30, 14, 16)})                     # 線から 12pips・MA から遠い
    b1 = minutes(px={"USDJPY": 16.0, "EURJPY": 16.0, "GBPJPY": 9.0})
    far_usd = dict(MV, **{"15:00": (29, 30, 25, 26)})
    b5 = world(eur=no, usd=far_usd)
    e = {p: F.ema15([b for b in b5[p] if b[0] < ts("15:05")] + [(ts("15:05"), 0, 0, 0, 0)])[-1] for p in F.PAIRS}
    assert all(abs(e[p] - price(x, pair=p)) > 0.035 for p, x in (("EURJPY", 14), ("USDJPY", 25)))
    assert run(b5=b5, b1=b1)["flags"]["touch1"] is False
    tch = world(eur=no, usd=dict(far_usd, **{"14:55": (38, 39, 2.5, 32)}))      # ドル円が線の 0.5pip 手前まで来た
    assert run(b5=tch, b1=b1)["flags"]["touch1"] is True
    tch = world(eur=no, usd=dict(far_usd, **{"14:55": (38, 39, 4, 32)}))        # 線の 2pips 手前＝線が 1pip ずれると変わる
    assert run(b5=tch, b1=b1)["flags"]["touch1"] is None
    tch = world(eur=no, usd=dict(far_usd, **{"14:45": (10, 25, 2.5, 24)}))      # 4本前の当たりは見ない（直近3本は 14:50・14:55・15:00）
    assert run(b5=tch, b1=b1)["flags"]["touch1"] is False
    b2 = dict(b1, EURJPY=ones("EURJPY", {"15:06": (16, 16, 4, 6)}, px=16.0, start="15:05"))
    assert run(b5=b5, b1=b2)["flags"]["touch1"] is True              # 入る足の中（入った分まで）
    b2 = dict(b1, EURJPY=ones("EURJPY", {"15:07": (16, 16, 4, 6)}, px=16.0, start="15:05"))
    assert run(b5=b5, b1=b2)["flags"]["touch1"] is False


def tb(n, hm="15:00"):
    """最後の足が hm に始まる n 本（上向きの形・値は 200.50 のまま）"""
    return [(ts(hm) - 300 * (n - 1 - i), 200.5, 200.5, 200.5) for i in range(n)]


def touch(U, j0="15:05", logs=None, bot=None, E=None, ones_=(), near=3.0):
    n = len(U)
    return V.touches(U, logs or [[None] * n, [None] * n], bot or [None] * n, E or [None] * (n + 1), ones_, ts(j0), near)


def test_touch_by_hand():
    def U(prev, low, hm="15:00"):
        u = tb(8, hm)
        u[6], u[7] = (u[6][0], *prev), (u[7][0], prev[2], low, prev[2])
        return u
    assert touch(U((200.2, 200.1, 200.1), 200.03)) and not touch(U((200.2, 200.1, 200.1), 200.031))                     # きりのよい値 200.00
    ma = [None] * 7 + [200.35, None]
    assert touch(U((200.5, 200.4, 200.4), 200.38), E=ma) and not touch(U((200.5, 200.4, 200.4), 200.381), E=ma)
    assert not touch(U((200.5, 200.34, 200.34), 200.33), E=ma)                                                           # 1本前の終値が MA の内側
    log = [[None] * 6 + [(200.35, 2), None], [None] * 8]
    assert touch(U((200.5, 200.4, 200.4), 200.38), logs=log) and touch(U((200.5, 200.4, 200.4), 200.38), logs=log[::-1])
    assert not touch(U((200.5, 200.4, 200.4), 200.38), logs=[[None] * 7 + [(200.35, 2)], [None] * 8])                    # その足で抜けた線は、1本前には無い
    bot = [None, 200.35] + [200.0] * 6
    assert touch(U((200.5, 200.4, 200.4), 200.38), bot=bot)                                                              # 反対側の東京の線（6本前まで）
    assert not touch(U((200.5, 200.4, 200.4), 200.38, "14:55"), "15:00", bot=bot)                                        # 15:00 からの足だけ
    assert not touch(U((200.5, 200.4, 200.4), 200.38), bot=[None] + [200.0] * 6 + [200.35])
    assert not touch(U((200.2, 200.1, 200.1), 200.01, "11:55"), "11:59") and touch(U((200.2, 200.1, 200.1), 200.01, "12:00"), "12:05")


def test_touch_in_the_entry_bar_uses_its_own_ma_and_the_last_close():
    u = tb(8)
    one_ = [(ts("15:05"), 200.5, 200.38, 200.4)]
    ma = [None] * 8 + [200.35]
    assert touch(u, E=ma, ones_=one_) and not touch(u, E=ma) and not touch(u, E=[None] * 8 + [200.34], ones_=one_)


def test_opposite_line_is_the_low_of_the_tokyo_hours():
    b = bars(200.0, {"07:30": (-6, -6, -90, -6), "09:30": (-6, -6, -30, -6), "15:05": (-6, -6, -70, -6)})
    bot = V.walk(V.up(b, 1))[1]
    i = {x[0]: k for k, x in enumerate(b)}
    assert bot[i[ts("15:10")]] == pytest.approx(199.70) and bot[i[ts("09:25")]] == pytest.approx(199.92) and bot[i[ts("07:55")]] is None


def test_yesterday_does_not_make_the_line():
    b5 = world()
    for p in b5:
        b5[p] = [(b[0] - 86400, b[1] + 0.5, b[2] + 0.5, b[3] + 0.5, b[4] + 0.5) for b in b5[p]] + b5[p]
    assert run(b5=b5)["legs"]["EURJPY"]["L"] == pytest.approx(price(2, pair="EURJPY"))


def test_without_1m_bars_a_no_is_unknown():
    shallow = dict(MV, **{"15:00": (29, 30, 25, 26)})
    b5 = world(eur=shallow, usd=dict(MV, **{"15:00": (29, 30, 25, 26)}))
    b1 = minutes(px={"USDJPY": 26.0, "EURJPY": 26.0, "GBPJPY": 9.0})
    a, b = run(b5=b5, b1=b1), run(b5=b5, b1={})
    assert a["flags"]["pull50"] is False and a["flags"]["touch1"] is False and b["coarse"] is True
    assert b["flags"]["pull50"] is None and b["flags"]["touch1"] is None and b["flags"]["far20"] is True
    assert run(b1={})["flags"]["pull50"] is True                     # 確定した足だけで ○ なら ○


def test_marks_are_unknown_when_the_line_bars_are_missing():
    """月曜の 8 時台は Yahoo に足が無い＝線がずれるかもしれない項目は決めない（向きは決める）"""
    skip = [f"08:{m:02d}" for m in range(0, 60, 5)]
    r = run(b5=world(skip=skip))
    assert r["missing"]["EURJPY"] == 12 and r["usd"][1] == 1 and r["flags"]["usd_dir"] is True and r["flags"]["pick_eg"] is True
    assert all(r["flags"][k] is None for k in ("both_broken", "far20", "fresh", "pull50", "touch1")) and r["watch_line"] is None and r["kata"] == "push"
    assert run(b5=world(skip=skip[:10]))["flags"]["both_broken"] is True


def test_flags_are_unknown_when_one_pip_changes_the_answer():
    close_call = dict(MV, **{"14:40": (0, 12, 0, 2.5), "14:45": (2.5, 2.6, 0, 2.5), "14:50": (2.5, 2.6, 2.4, 2.5), "14:55": (2.5, 2.6, 2.4, 2.5), "15:00": (2.5, 2.6, 2.4, 2.5)})      # 線 +2 の 0.5pip 外で確定
    assert run(b5=world(gbp=close_call))["flags"]["both_broken"] is None


# ── ドルストレート（④の片方） ──────────────────────────

def test_dollar_straight_only_gets_the_directions():
    r = run(pair="EURUSD", b5=world(usd={}))
    assert r["pick"] is True and r["strong"] == "EURJPY" and r["kata"] == "range" and r["watch"] is None
    assert r["flags"]["pick_eg"] is True and r["flags"]["usd_dir"] is False and r["flags"]["fresh"] is None and r["flags"]["both_broken"] is None and r["legs"] == {}
    assert run(pair="GBPUSD", b5=world(usd={}))["pick"] is False
    assert run(pair="EURUSD")["kata"] is None                        # ドル円に向きがある＝④ではない


def test_other_pairs_are_rejected():
    with pytest.raises(F.FillError):
        run(pair="AUDJPY")


# ── 人に聞くこと・読む文 ─────────────────────────────

def test_questions():
    q = V.questions(run(), set(), set())
    assert q == []
    r = run(pair="GBPJPY")                                           # 入ったのは弱いほう
    q = V.questions(r, set(), set())
    assert len(q) == 1 and "strongest" in q[0] and "ユーロ円" in q[0]
    assert V.questions(r, {"strongest"}, set()) == [] and V.questions(r, set(), {"strong"}) == []
    r = run(b5=world(eur={}))
    q = V.questions(r, set(), set())
    assert len(q) == 1 and "--kata" in q[0] and "--unknown kata" in q[0]
    assert V.questions(r, {"kata"}, set()) == [] and V.questions(r, set(), {"kata"}) == []


def test_unbroken_pair_asks_only_the_kata():
    r = run(b5={p: flat(p) for p in F.PAIRS})
    q = V.questions(r, set(), set())
    assert len(q) == 1 and "--kata" in q[0]


def test_report_lines():
    out = V.report(run())
    for w in ("ドル円 上", "ユーロポンド 上", "ユーロ円", "①押し目", "見るペア ポンド円", "200.020", "200.110"):
        assert w in out, w
    out = V.report(run(b5={p: flat(p) for p in F.PAIRS}))
    assert "レンジ" in out and "型：決まらない" in out
    assert "まだ抜けていない" in V.report(run(b5=world(gbp={}))) or "見るペア" in V.report(run(b5=world(gbp={})))


# ── 入ったあと（v4 の出口まで・伸ばした分） ───────────────────

def mins(pair, seq, start="15:07", side=1):
    """seq＝[(高, 安, 終)]（base からの pips）の1分足"""
    out = []
    for k, (h, l, c) in enumerate(seq):
        t = ts(start) + 60 * k
        v = [BASE[pair] + side * x * 0.01 for x in (c, h, l, c)]
        out.append((t, v[0], max(v[1], v[2]), min(v[1], v[2]), v[3]))
    return out


def aft(p_seq, q_seq, side=1, entry=15.8, close="15:12", spread=1.8, line=2, ext=11, pnl=None, start="15:07"):
    p, q = mins("EURJPY", p_seq, start, side), mins("GBPJPY", q_seq, start, side)
    en = price(entry, side, "EURJPY")
    return V.after(p, q, "buy" if side > 0 else "sell", en, spread, price(line, side, "GBPJPY"), price(ext, side, "GBPJPY"), at("15:06", 8), at(close, 30), 0.01, pnl)


def test_after_take_profit_and_what_was_added():
    a = aft([(20, 15, 18), (26, 18, 25), (40, 24, 38)], [(10, 8, 9), (11, 9, 10), (12, 9, 10)], pnl=30.0)
    assert a["v4_exit"] == "tp" and a["v4_exit_min"] == 2 and a["v4_exit_pips"] == pytest.approx(25 - 15.8)        # 2本目の終値
    assert a["run_pips"] == pytest.approx(30.0 - 9.2) and a["mfe_pips"] == pytest.approx(40 - 15.8)


def test_after_stop_is_4_pips_inside_the_line():
    a = aft([(16, 10, 12), (14, 8, 9)], [(9, -1.9, 0), (3, -2, -1)], pnl=-8.0)
    assert a["v4_exit"] == "sl" and a["v4_exit_min"] == 2 and a["v4_exit_pips"] == pytest.approx(9 - 15.8) and a["run_pips"] is None
    assert aft([(16, 10, 12)], [(12, -2, 0)], pnl=0.0)["v4_exit"] == "sl"                                          # 同じ分に両方＝損切り


def test_after_none_when_the_owner_left_first():
    a = aft([(20, 15, 18)], [(10, 8, 9)], pnl=2.0)
    assert a["v4_exit"] == "none" and a["v4_exit_min"] is None and a["v4_exit_pips"] is None and a["run_pips"] is None and a["mfe_pips"] == pytest.approx(4.2)


def test_after_sell_pays_the_spread():
    a = aft([(20, 15, 18), (26, 18, 25)], [(10, 8, 9), (11, 9, 10)], side=-1, entry=14.0, pnl=20.0)
    assert a["v4_exit"] == "tp" and a["v4_exit_pips"] == pytest.approx(25 - 14.0 - 1.8) and a["mfe_pips"] == pytest.approx(26 - 14.0 - 1.8)


def test_after_uses_only_whole_minutes_between_entry_and_exit():
    a = aft([(20, 15, 18)] * 3, [(11, 9, 10), (9, 9, 9), (9, 9, 9)], start="15:06", pnl=0.0)                        # 入った分（15:06）は使わない
    assert a["v4_exit"] == "none"
    a = aft([(20, 15, 18)] * 8, [(9, 9, 9)] * 5 + [(11, 9, 10)] * 3, pnl=0.0)                                       # 15:12＝出た分から先は使わない
    assert a["v4_exit"] == "none"
    a = aft([(20, 15, 18)] * 8, [(9, 9, 9)] * 4 + [(11, 9, 10)] * 4, pnl=0.0)                                       # 15:11
    assert a["v4_exit"] == "tp" and a["v4_exit_min"] == 5


def test_after_without_watch_pair_only_has_mfe():
    p = mins("EURJPY", [(20, 15, 18)])
    a = V.after(p, [], "buy", price(15, 1, "EURJPY"), None, None, None, at("15:06", 8), at("15:12"), 0.01, 3.0)
    assert a == {"v4_exit": None, "v4_exit_min": None, "v4_exit_pips": None, "run_pips": None, "mfe_pips": pytest.approx(5.0)}
    a = V.after([], [], "buy", 170.0, None, None, None, at("15:06", 8), at("15:12"), 0.01, 3.0)
    assert a["mfe_pips"] is None and a["v4_exit"] is None


def test_after_sell_without_spread_is_unknown():
    p, q = mins("EURJPY", [(26, 18, 25)], side=-1), mins("GBPJPY", [(11, 9, 10)], side=-1)
    a = V.after(p, q, "sell", price(14, -1, "EURJPY"), None, price(2, -1, "GBPJPY"), price(11, -1, "GBPJPY"), at("15:06", 8), at("15:12"), 0.01, 3.0)
    assert a["v4_exit"] == "tp" and a["v4_exit_pips"] is None and a["run_pips"] is None and a["mfe_pips"] is None


def test_after_dollar_pair_pips():
    p = [(ts("15:07"), 1.1, 1.1010, 1.0990, 1.1)]
    assert V.after(p, [], "buy", 1.1000, 0.5, None, None, at("15:06", 8), at("15:12"), 0.0001, 3.0)["mfe_pips"] == pytest.approx(10.0)


def test_load_after_falls_back_to_5m_and_survives_errors(monkeypatch):
    got = []

    def fake(pair, step, a, b, tries=3):
        got.append((pair, step, a, b))
        if step == "1m":
            raise F.FillError("30日より前")
        return [(a, 1.0, 1.0, 1.0, 1.0)]
    monkeypatch.setattr(F, "fetch", fake)
    p, q, step = V.load_after("EURJPY", "GBPJPY", at("15:06", 8), at("15:30"))
    assert len(p) == 1 and len(q) == 1 and step == 300 and [g[:2] for g in got] == [("EURJPY", "1m"), ("EURJPY", "5m"), ("GBPJPY", "5m")]
    assert got[-1][2:] == (ts("15:05"), ts("15:30") + 60)
    got.clear()
    assert V.load_after("EURUSD", None, at("15:06", 8), at("15:30"))[1] == [] and {g[0] for g in got} == {"EURUSD"}

    def dead(*a, **k):
        raise F.FillError("だめ")
    monkeypatch.setattr(F, "fetch", dead)
    assert V.load_after("EURJPY", "GBPJPY", at("15:06", 8), at("15:30")) == ([], [], 60)


def test_after_5m_bars_also_skip_the_entry_bar():
    p = [(ts("15:05"), 0, price(90, 1, "EURJPY"), 0, price(20, 1, "EURJPY")), (ts("15:10"), 0, price(30, 1, "EURJPY"), price(20, 1, "EURJPY"), price(25, 1, "EURJPY"))]
    a = V.after(p, [], "buy", price(15, 1, "EURJPY"), 1.8, None, None, at("15:06", 8), at("15:17"), 0.01, 0.0, step=300)
    assert a["mfe_pips"] == pytest.approx(15.0)                      # 入った足（15:05）は使わない
    a = V.after(p, [], "buy", price(15, 1, "EURJPY"), 1.8, None, None, at("15:06", 8), at("15:12"), 0.01, 0.0, step=300)
    assert a["mfe_pips"] is None                                     # 15:10 の足は出たあと（15:12〜15:15）も含む＝使わない


# ── 記録（trade_journal） ────────────────────────────

ALL = {k: True for k in V.FLAGS}


def trade(v4=None, after=None, kata=None, **kw):
    base = dict(tid="900", pair="EURJPY", side="buy", t_open=dt.datetime(2026, 12, 1, 15, 6, 8), entry=170.158, sl=169.98, tp=None,
                t_close=dt.datetime(2026, 12, 1, 15, 40), exit_=170.4, spread=1.8, flags=T.parse_flags("event_clear=1,strongest=1"))
    base.update(kw)
    return T.make_trade(v4=v4, after=after, kata=kata, **base)


def v4(**kw):
    x = {"usd_1h": 5.0, "eg_1h": 1.2, "strong_eg": "EURJPY", "watch": "GBPJPY", "watch_line": 200.02, "watch_extreme": 200.11, "flags": dict(ALL)}
    x.update(kw)
    return x


def test_record_keeps_v4_items():
    t = trade(v4(), {"v4_exit": "tp", "v4_exit_min": 12, "v4_exit_pips": 9.2, "run_pips": 15.0, "mfe_pips": 30.0}, "push")
    assert t["kata"] == "push" and t["usd_1h"] == 5.0 and t["eg_1h"] == 1.2 and t["strong_eg"] == "EURJPY" and t["watch"] == "GBPJPY"
    assert (t["watch_line"], t["watch_extreme"], t["v4_exit"], t["run_pips"], t["mfe_pips"]) == (200.02, 200.11, "tp", 15.0, 30.0)
    assert t["fits_v4_entry"] is True and all(t["flags"][k] is True for k in V.FLAGS)


def test_record_without_v4_is_all_unknown():
    t = trade()
    assert t["kata"] is None and t["usd_1h"] is None and t["v4_exit"] is None and t["fits_v4_entry"] is None
    assert all(t["flags"][k] is None for k in V.FLAGS)


@pytest.mark.parametrize("k", V.FLAGS)
def test_fits_v4_needs_every_mark(k):
    assert trade(v4(flags=dict(ALL, **{k: False})), kata="push")["fits_v4_entry"] is False
    assert trade(v4(flags=dict(ALL, **{k: None})), kata="push")["fits_v4_entry"] is None


def test_fits_v4_needs_the_common_conditions():
    assert trade(v4(), kata="push", sl=None)["fits_v4_entry"] is False
    assert trade(v4(), kata="push", spread=2.6)["fits_v4_entry"] is False
    assert trade(v4(), kata="push", t_open=dt.datetime(2026, 12, 4, 15, 6))["fits_v4_entry"] is False      # 金曜
    assert trade(v4(), kata="push", t_open=dt.datetime(2026, 12, 1, 19, 0))["fits_v4_entry"] is False      # 終わりのあと
    assert trade(v4(), kata="push", flags=T.parse_flags("event_clear=0"))["fits_v4_entry"] is False
    assert trade(v4(), kata="push", flags=T.parse_flags(""))["fits_v4_entry"] is None                      # 発表の○×が無い
    assert trade(v4(), kata="push", flags=T.parse_flags("event_clear=1"))["fits_v4_entry"] is True         # strongest・tokyo_break は v4 の条件に入れない


def test_fits_v4_is_only_about_the_push():
    assert trade(v4(), kata=None)["fits_v4_entry"] is None
    assert trade(v4(), kata="fade")["fits_v4_entry"] is None and trade(v4(), kata="range")["fits_v4_entry"] is None
    assert trade(v4(), kata="other")["fits_v4_entry"] is False
    assert trade(v4(flags=dict(ALL, far20=False)), kata="fade")["fits_v4_entry"] is None


def test_kata_must_be_known():
    with pytest.raises(ValueError):
        trade(v4(), kata="xyz")


def test_v1_to_v3_are_unchanged_by_v4():
    a, b = trade(), trade(v4(), kata="push")
    for k in ("fits_v1_entry", "fits_v2_entry", "fits_v3_entry", "r_net", "pnl_pips"):
        assert a[k] == b[k]


def test_reading_table_has_v4_rows():
    ts_ = [trade(v4(), {"v4_exit": "tp", "v4_exit_min": 3, "v4_exit_pips": 9.0, "run_pips": 10.0, "mfe_pips": 20.0}, "push"),
           trade(v4(flags=dict(ALL, far20=False)), {"v4_exit": "sl", "v4_exit_min": 3, "v4_exit_pips": -9.0, "run_pips": None, "mfe_pips": 2.0}, "push", exit_=170.0),
           trade(v4(), None, "range")]
    r = T.reading_table(ts_)
    assert r["far20=o"]["n"] == 2 and r["far20=x"]["n"] == 1 and r["fits_v4_entry=o"]["n"] == 1 and r["fits_v4_entry=x"]["n"] == 1
    assert r["kata=push"]["n"] == 2 and r["kata=range"]["n"] == 1 and r["kata=fade"] == {"n": 0, "mean": None}
    assert r["v4_exit=tp"]["n"] == 1 and r["v4_exit=sl"]["n"] == 1 and r["run_pips"] == {"n": 1, "mean": 10.0}


def test_status_counts_v4_and_kata_without_average():
    st = T.empty_state()
    t = trade(v4(), None, "push")
    t["r_net"] = 2.345
    T.add(st, t)
    s = T.status_text(st)
    assert "決まりの紙 v4 の入口に全部当てはまった取引 1件" in s and "①押し目 1件" in s and "2.345" not in s


def test_old_records_still_work():
    st = T.empty_state()
    t = trade()
    for k in ("kata", "usd_1h", "eg_1h", "strong_eg", "watch", "watch_line", "watch_extreme", "v4_exit", "v4_exit_min", "v4_exit_pips", "run_pips", "mfe_pips", "fits_v4_entry"):
        t.pop(k)
    for k in V.FLAGS:
        t["flags"].pop(k)
    T.add(st, t)
    assert "決まりの紙 v4 の入口に全部当てはまった取引 0件" in T.status_text(st)
    r = T.reading_table([t])
    assert r["far20=o"]["n"] == 0 and r["kata=push"]["n"] == 0 and r["run_pips"] == {"n": 0, "mean": None}


def test_both_tools_have_the_same_words():
    assert T.KATA == V.KATA and T.V4_FLAGS == V.FLAGS


# ── コマンド ────────────────────────────────────

def cli(monkeypatch, tmp_path, *extra, b5=None, b1=None, pair="EURJPY", cmd="add", flags="event_clear=1", after=None, entry=15.8):
    monkeypatch.chdir(tmp_path)
    b5, b1 = world() if b5 is None else b5, minutes() if b1 is None else b1
    monkeypatch.setattr(F, "load", lambda t: (b5, b1))
    monkeypatch.setattr(V, "load_after", lambda *a: after or ([], [], 60))
    base = {"EURUSD": 1.1}.get(pair)
    en = base if base else price(entry, 1, pair)
    sl = en - (0.0020 if base else 0.20)
    a = [cmd, "--pair", pair, "--side", "buy", "--open", "2026.12.01 15:06:08", "--entry", str(en)]
    if cmd == "add":
        a += ["--id", "900", "--sl", str(sl), "--close", "2026.12.01 15:40:00", "--exit", str(en + (0.0010 if base else 0.10)), "--spread", "1.0", "--flags", flags, "--auto"]
    return T.main(a + list(extra))


def test_add_auto_fills_v4(monkeypatch, tmp_path, capsys):
    p = mins("EURJPY", [(20, 15, 18), (26, 18, 25), (40, 24, 38)])
    q = mins("GBPJPY", [(10, 8, 9), (11, 9, 10), (12, 9, 10)])
    assert cli(monkeypatch, tmp_path, after=(p, q, 60)) == 0
    t = T.load()["trades"][0]
    assert t["kata"] == "push" and t["strong_eg"] == "EURJPY" and t["watch"] == "GBPJPY" and t["watch_line"] == 200.02 and t["watch_extreme"] == 200.11
    assert t["flags"]["strongest"] is True and {"kata", "strongest"} <= set(t["filled"])
    assert t["v4_exit"] == "tp" and t["v4_exit_min"] == 2 and t["v4_exit_pips"] == pytest.approx(9.2) and t["run_pips"] == pytest.approx(10.0 - 9.2) and t["mfe_pips"] == pytest.approx(24.2)
    assert t["usd_1h"] > 2 and t["eg_1h"] > 0.5
    out = capsys.readouterr().out
    assert "①押し目" in out and "9.2" not in out.split("足した")[0]   # v4 の出口との比べは、足すときに見せない


def test_owner_kata_wins(monkeypatch, tmp_path):
    assert cli(monkeypatch, tmp_path, "--kata", "other") == 0
    t = T.load()["trades"][0]
    assert t["kata"] == "other" and "kata" not in t["filled"] and t["fits_v4_entry"] is False


def test_after_lines_are_only_for_the_push(monkeypatch, tmp_path):
    p, q = mins("EURJPY", [(20, 15, 18)] * 4), mins("GBPJPY", [(12, 9, 10)] * 4)
    assert cli(monkeypatch, tmp_path, "--kata", "range", after=(p, q, 60)) == 0
    t = T.load()["trades"][0]
    assert t["v4_exit"] is None and t["mfe_pips"] == pytest.approx(4.2) and t["watch_line"] == 200.02


def test_unbroken_pair_is_not_called_the_strongest(monkeypatch, tmp_path):
    b5 = world(eur={}, gbp={"14:30": (-6, -6, -60, -60)})            # ユーロポンドは上・ユーロ円はまだ抜けていない
    r = run(b5=b5)
    assert r["pick"] is True and r["named"] is False
    assert cli(monkeypatch, tmp_path, "--unknown", "kata", b5=b5, entry=-4) == 0
    assert T.load()["trades"][0]["flags"]["strongest"] is None


def test_unknown_kata_stops_and_can_be_let_through(monkeypatch, tmp_path, capsys):
    b5 = world(eur={})
    assert cli(monkeypatch, tmp_path, b5=b5, entry=-4) == 2 and not os.path.exists(T.JOURNAL)
    assert "--kata" in capsys.readouterr().out
    assert cli(monkeypatch, tmp_path, "--unknown", "kata", b5=b5, entry=-4) == 0
    assert T.load()["trades"][0]["kata"] is None


def test_strongest_is_asked_by_the_v4_answer(monkeypatch, tmp_path, capsys):
    b5 = world(eur=WEAK, gbp=MV)
    assert cli(monkeypatch, tmp_path, b5=b5) == 2
    out = capsys.readouterr().out
    assert out.count("❓") == 1 and "ポンド円" in out.split("❓")[1] and "strongest=1" in out
    assert cli(monkeypatch, tmp_path, "--unknown", "strong", b5=b5) == 0
    t = T.load()["trades"][0]
    assert t["flags"]["strongest"] is None and t["flags"]["pick_eg"] is False


def test_eurgbp_border_is_asked(monkeypatch, tmp_path, capsys):
    for k in range(80):                                              # ユーロ円の伸びを変えて、ユーロポンドの1時間の動きがちょうど 0.5pips になる所
        eur = dict(WEAK, **{"14:50": (7, 11, 7, 6 + 0.1 * k), "14:55": (10, 11, 6, 6 + 0.1 * k), "15:00": (9, 11, 6, 6 + 0.1 * k)})
        b5 = world(eur=eur, gbp=WEAK)
        if abs(run(b5=b5)["eg"][0] - 0.5) < 0.05:
            break
    r = run(b5=b5)
    assert r["eg"][1] is None and r["pick"] is None and r["strong"] is None and r["flags"]["pick_eg"] is None
    assert cli(monkeypatch, tmp_path, b5=b5, entry=8) == 2
    assert "境目" in capsys.readouterr().out.split("❓")[1]


def test_dollar_straight_is_filled_with_directions(monkeypatch, tmp_path, capsys):
    assert cli(monkeypatch, tmp_path, b5=world(usd={}), pair="EURUSD") == 0
    t = T.load()["trades"][0]
    assert t["kata"] == "range" and t["flags"]["pick_eg"] is True and t["flags"]["strongest"] is True and t["strong_eg"] == "EURJPY" and t["watch"] is None
    assert t["break_line"] is None and t["far_min"] is None
    assert cli(monkeypatch, tmp_path, b5=world(usd={}), pair="EURUSD", cmd="fill") == 0


def test_fill_shows_v4(monkeypatch, tmp_path, capsys):
    assert cli(monkeypatch, tmp_path, cmd="fill") in (0, 2) and not os.path.exists(T.JOURNAL)
    out = capsys.readouterr().out
    assert "v4" in out and "見るペア ポンド円" in out


def test_kata_can_be_given_without_auto(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(F, "load", lambda t: pytest.fail("取りに行った"))
    T.main(["add", "--id", "1", "--pair", "EURUSD", "--side", "buy", "--open", "2026.12.01 15:31", "--entry", "1.1", "--sl", "1.098", "--close", "2026.12.01 15:50", "--exit", "1.101", "--kata", "range"])
    t = T.load()["trades"][0]
    assert t["kata"] == "range" and t["strong_eg"] is None and D0


# ── 決まりの紙 v5（「OJ」追記⑫・始まりの30分後からは、始まりからの動きで測り直す） ──────────

# 17:00 にドル円が上へ（始値 +14 → 17:25 の終値 +25＝11pips）・17:25 にポンド円だけ 29pips 下げる（ユーロポンドは上）
USD5 = dict(MV, **{"17:00": (14, 20, 13, 18), "17:25": (18, 26, 18, 25)})
EUR5 = dict(MV, **{"17:00": (14, 15, 13, 14)})
GBP5 = dict(WEAK, **{"17:00": (9, 12, 5, 6), "17:25": (6, 6, -20, -20)})      # 始まりの足は始値 +9・終値 +6（始値から測る）


def world5(**kw):
    return world(usd=kw.get("usd", USD5), eur=kw.get("eur", EUR5), gbp=kw.get("gbp", GBP5))


def test_since_london_is_from_the_open_of_the_1700_bar_to_the_last_closed_bar():
    b5 = world5()
    u, e = V.since_london(b5, at("17:31", 8))
    assert u == pytest.approx(11.0)
    E, G = {b[0]: b for b in b5["EURJPY"]}, {b[0]: b for b in b5["GBPJPY"]}
    l0, k = ts("17:00"), ts("17:25")
    assert e == pytest.approx((E[k][4] / G[k][4] - E[l0][1] / G[l0][1]) / 0.0001, abs=0.01) and e > 10
    assert V.since_london(b5, at("17:29", 59))[0] == pytest.approx(4.0)       # 入った足（17:25〜）は使わない＝17:20 の終値 +18
    assert V.since_london(b5, at("17:03", 0)) == (None, None)                 # 始まりの足がまだ確定していない
    b5["USDJPY"] = [b for b in b5["USDJPY"] if b[0] != ts("17:00")]
    assert V.since_london(b5, at("17:31", 8))[0] is None                      # 始まりの足が無い


def test_v5_after_the_wait_uses_the_move_since_the_open():
    r = run(b5=world5(), hm="17:31")
    assert r["phase"] == "after" and r["usd5"] == (11.0, 1) and r["eg5"][1] == 1
    assert r["strong5"] == "EURJPY" and r["pick5"] is True and r["kata5"] == "push"
    assert r["flags5"] == {"usd_dir5": True, "pick_eg5": True}
    assert r["eg"][1] == 0 and r["pick"] is False                             # v4（1時間の動き）ではユーロポンドはレンジ＝強いほうが決まらない
    assert V.questions(r, set(), set()) == []                                 # 30分後からは v5 の答えで聞く＝聞かない
    assert "v5（ロンドンの始まりから）" in V.report(r) and "+11.0pips" in V.report(r)
    rec = V.record(r)
    assert (rec["usd_ldn"], rec["strong_ldn"], rec["kata5"], rec["flags5"]) == (11.0, "EURJPY", "push", {"usd_dir5": True, "pick_eg5": True})


def test_v5_asks_when_the_move_since_the_open_disagrees():
    r = run(b5=world5(gbp=dict(WEAK, **{"17:25": (9, 40, 9, 40)})), hm="17:31")   # ポンド円のほうが上げた＝ユーロポンドは下
    assert r["eg5"][1] == -1 and r["strong5"] == "GBPJPY" and r["pick5"] is False and r["flags5"]["pick_eg5"] is False
    q = V.questions(r, set(), set())
    assert len(q) == 1 and "始まりから" in q[0]
    r = run(b5=world5(usd=dict(MV, **{"17:00": (14, 15, 13, 14)})), hm="17:31")   # ドル円が始まりから動いていない＝④の見当
    assert r["usd5"][1] == 0 and r["flags5"]["usd_dir5"] is False and r["kata5"] == "range"


def test_v5_before_the_open_is_the_v4_answer_and_the_wait_is_not_measured():
    r = run()                                                                 # 15:06
    assert r["phase"] == "before" and r["flags5"] == {"usd_dir5": r["flags"]["usd_dir"], "pick_eg5": r["pick"]}
    assert (r["kata5"], r["strong5"], r["usd5"][0]) == (r["kata"], r["strong"], None)
    for hm in ("16:55", "17:02", "17:29"):
        r = run(b5=world5(), hm=hm)
        assert r["phase"] == "flat" and r["flags5"] == {"usd_dir5": None, "pick_eg5": None} and r["kata5"] is None
        assert "入らない時間" in V.report(r)
    assert V.pick_now(run(b5=world5(), hm="17:02")) is run(b5=world5(), hm="17:02")["pick"]


def v5(**kw):
    x = v4(usd_ldn=11.0, eg_ldn=12.3, strong_ldn="EURJPY", kata5="push", flags5={"usd_dir5": True, "pick_eg5": True})
    x.update(kw)
    return x


def test_fits_v5_after_the_wait():
    t = trade(v5(), kata="push", t_open=dt.datetime(2026, 12, 1, 17, 31, 8), t_close=dt.datetime(2026, 12, 1, 18, 0))
    assert t["fits_v5_entry"] is True and (t["usd_ldn"], t["strong_ldn"], t["kata5"]) == (11.0, "EURJPY", "push")
    assert trade(v5(), kata="push", t_open=dt.datetime(2026, 12, 1, 17, 2), t_close=dt.datetime(2026, 12, 1, 17, 21))["fits_v5_entry"] is False
    assert trade(v5(), kata="push", t_open=dt.datetime(2026, 12, 1, 19, 0), t_close=dt.datetime(2026, 12, 1, 19, 30))["fits_v5_entry"] is False


@pytest.mark.parametrize("k", ["usd_dir5", "pick_eg5"])
def test_fits_v5_needs_the_new_direction(k):
    at_ = dict(t_open=dt.datetime(2026, 12, 1, 17, 31, 8), t_close=dt.datetime(2026, 12, 1, 18, 0))
    assert trade(v5(flags5={"usd_dir5": True, "pick_eg5": True, k: False}), kata="push", **at_)["fits_v5_entry"] is False
    assert trade(v5(flags5={"usd_dir5": True, "pick_eg5": True, k: None}), kata="push", **at_)["fits_v5_entry"] is None
    assert trade(v5(flags=dict(ALL, usd_dir=False, pick_eg=False)), kata="push", **at_)["fits_v5_entry"] is True   # v4 の向きは v5 では使わない


def test_fits_v5_uses_the_v5_kata_and_keeps_v4_kata():
    at_ = dict(t_open=dt.datetime(2026, 12, 1, 17, 31, 8), t_close=dt.datetime(2026, 12, 1, 18, 0))
    t = trade(v5(kata5="range"), kata="push", **at_)
    assert t["kata"] == "push" and t["kata5"] == "range" and t["fits_v5_entry"] is None
    assert trade(v4(), kata="push")["kata5"] == "push"                       # v5 の型が無い記録は v4 の型
    assert trade(kata="push")["fits_v5_entry"] is None                       # --auto なし＝向きが分からない


def test_owner_kata_is_also_the_v5_kata(monkeypatch, tmp_path):
    assert cli(monkeypatch, tmp_path, "--kata", "other") == 0
    t = T.load()["trades"][0]
    assert t["kata5"] == "other" and t["fits_v5_entry"] is False and t["flags"]["in_window5"] is True and t["flags"]["ldn_flat"] is True


def test_v5_eurgbp_uses_its_own_threshold():
    r = run(b5=world5(gbp=dict(WEAK, **{"17:00": (9, 9, 9, 9), "17:25": (9, 9, 6.5, 6.5)})), hm="17:31")   # ポンド円だけ 2.5pips 下げる
    assert 0.6 < r["eg5"][0] < 1.8 and r["eg5"][1] == 1 and r["pick5"] is True                          # ユーロポンドの物差し（0.5pips）で上


def test_v5_asks_the_kata_from_the_move_since_the_open():
    usd = dict(MV, **{"16:30": (14, 30, 14, 30), "17:00": (30, 31, 29, 30), "17:25": (30, 32, 30, 32)})   # 16:30 に上げ（1時間の動きは上）・始まりからは +2.0＝境目
    r = run(b5=world5(usd=usd), hm="17:31")
    assert r["usd5"] == (2.0, None) and r["kata5"] is None and r["kata"] == "push"
    q = V.questions(r, set(), set())
    assert any("--kata" in x for x in q)
    assert not any("--kata" in x for x in V.questions(run(), set(), set()))


@pytest.mark.parametrize("kata, want", [("fade", False), ("push", True), (None, True)])
def test_add_marks_the_time_by_kata(monkeypatch, tmp_path, kata, want):
    """冬の 15:06＝②逆張りの時間（16:00 から）の外・①押し目の時間の中（オーナーが言わなければ道具の答え＝①）"""
    assert cli(monkeypatch, tmp_path, *(("--kata", kata) if kata else ())) == 0
    t = T.load()["trades"][0]
    assert t["kata"] == (kata or "push") and t["flags"]["in_window5"] is want


def test_add_leaves_the_time_empty_when_the_kata_is_unknown(monkeypatch, tmp_path):
    b5 = world(eur={})                                                       # 入ったペアがまだ抜けていない＝道具は型を決めない
    assert cli(monkeypatch, tmp_path, "--unknown", "kata", b5=b5, entry=-4) == 0
    assert T.load()["trades"][0]["flags"]["in_window5"] is None
