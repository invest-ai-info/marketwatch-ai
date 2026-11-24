# -*- coding: utf-8 -*-
"""trade_fill.py（取引の記録を自動で埋める道具・決まりの紙 v2）のテスト。作り物の足だけ・ネットは使わない"""
import datetime as dt
import io
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import trade_fill as F  # noqa: E402
import trade_journal as T  # noqa: E402

D0 = dt.date(2026, 12, 1)            # 火曜・冬（ロンドンは17時）
BASE = {"USDJPY": 150.00, "EURJPY": 170.00, "GBPJPY": 200.00}


def ts(hm, day=D0):
    h, m = map(int, hm.split(":"))
    return int(dt.datetime(day.year, day.month, day.day, h, m, tzinfo=dt.timezone.utc).timestamp()) - 9 * 3600


def at(hm, sec=0):
    h, m = map(int, hm.split(":"))
    return dt.datetime(D0.year, D0.month, D0.day, h, m, sec)


def bars(base, moves=None, start="00:00", end="20:00", step=5, side=1, skip=()):
    """平らな足（−6 ±2pips）で、09:00 のヒゲが +2＝東京の線は +2。moves＝{"時刻": (始, 高, 安, 終)}（base からの pips・そのあとの足は直前の終値のまわりで平ら）。side=-1 で上下を逆に"""
    out, px, moves = [], -6.0, {"09:00": (-6, 2, -8, -6), **(moves or {})}
    for t in range(ts(start), ts(end), step * 60):
        hm = dt.datetime.fromtimestamp(t + 9 * 3600, dt.timezone.utc).strftime("%H:%M")
        o, h, l, c = moves.get(hm, (px, px + 2, px - 2, px))
        px = c
        if hm in skip:
            continue
        v = [base + side * x * 0.01 for x in (o, h, l, c)]
        out.append((t, v[0], max(v[1], v[2]), min(v[1], v[2]), v[3]))
    return out


# 14:40 に抜け（終値 +10）→ 14:50 に +40（線 +2 から 38pips）→ 下げて 15:05 に +21 前後（50% ＝ (2+40)/2＝+21・MA は +7 あたり）
MOVE = {"14:40": (0, 12, 0, 10), "14:45": (10, 25, 9, 24), "14:50": (24, 40, 23, 38), "14:55": (38, 39, 30, 32),
        "15:00": (29, 30, 25, 26), "15:05": (26, 27, 20, 22)}


def world(side=1, move=None, **kw):
    move = MOVE if move is None else move
    return {p: bars(BASE[p], move, side=side, **kw) for p in F.PAIRS}


def ones(pair="GBPJPY", moves=None, side=1, start="15:00", end="15:40", px=32.0):
    """1分足（15:00〜）。moves の無い分は直前の終値で平ら"""
    out, p = [], px
    for t in range(ts(start), ts(end), 60):
        hm = dt.datetime.fromtimestamp(t + 9 * 3600, dt.timezone.utc).strftime("%H:%M")
        o, h, l, c = (moves or {}).get(hm, (p, p, p, p))
        p = c
        v = [BASE[pair] + side * x * 0.01 for x in (o, h, l, c)]
        out.append((t, v[0], max(v[1], v[2]), min(v[1], v[2]), v[3]))
    return out


def price(x, side=1, pair="GBPJPY"):
    return round(BASE[pair] + side * x * 0.01, 5)


def run(side=1, hm="15:06", b5=None, b1=None, pair="GBPJPY", **kw):
    b5 = world(side) if b5 is None else b5
    if b1 is None:                                   # 入る所の1分足＝5分足と同じ動き
        b1 = {p: ones(p, {"15:00": (29, 30, 25, 26), "15:05": (26, 27, 20, 22)}, side, px=29.0) for p in F.PAIRS}
    return F.analyze(b5, b1, pair, "buy" if side > 0 else "sell", at(hm, 8), **kw)


# ── 線と抜け ────────────────────────────────────────

def test_line_is_tokyo_high_and_break_is_first_close_outside():
    r = run()
    assert r["line"] == pytest.approx(price(2)) and r["break_bar"] == "14:40"


def test_wick_is_not_a_break_but_raises_the_line_until_1455():
    mv = dict(MOVE, **{"14:00": (0, 8, 0, 1)})                   # ヒゲだけ＝抜けでない・線は +8 に上がる
    r = run(b5=world(move=mv))
    assert r["line"] == pytest.approx(price(8)) and r["break_bar"] == "14:40"


def test_close_outside_before_1400_is_not_a_break():
    mv = dict(MOVE, **{"13:50": (0, 6, 0, 5), "13:55": (5, 5, 0, 0)})
    r = run(b5=world(move=mv))
    assert r["line"] == pytest.approx(price(6)) and r["break_bar"] == "14:40"


def test_bars_before_0800_do_not_make_the_line():
    mv = dict(MOVE, **{"07:55": (0, 30, 0, 0), "08:00": (0, 3, 0, 0)})
    assert run(b5=world(move=mv))["line"] == pytest.approx(price(3))


def test_line_stops_growing_at_1500():
    mv = {"14:55": (0, 5, 0, 0), "15:00": (0, 9, 0, 1), "15:05": (1, 7, 1, 6)}      # 15:05 の終値 +6 が、14:55 までの高値 +5 の外
    r = F.analyze(world(move=mv), {}, "GBPJPY", "buy", at("15:20"))
    assert r["line"] == pytest.approx(price(5)) and r["break_bar"] == "15:05"


def test_sell_is_mirror():
    r = run(side=-1)
    assert r["line"] == pytest.approx(price(2, -1)) and r["break_bar"] == "14:40"
    assert r["extreme"] == pytest.approx(price(40, -1)) and r["far_min"] == 10 and r["entry_types"] == ["half50"]


def test_break_after_entry_is_not_seen():
    r = run(hm="14:39")
    assert r["line"] is None and r["far_min"] is None and r["leg_pips"] is None


def test_break_bar_must_be_complete_at_entry():
    assert run(hm="14:42")["line"] is None                        # 抜けた足（14:40）がまだ確定していない
    assert run(hm="14:45")["break_bar"] == "14:40"


def test_too_few_bars_is_an_error():
    skip = [f"{h:02d}:{m:02d}" for h in (8, 9, 10) for m in range(0, 60, 5)]
    with pytest.raises(F.FillError):
        run(b5=world(skip=skip[:25]))
    assert run(b5=world(skip=skip[:24]))["missing"]["GBPJPY"] == 24
    assert run()["missing"] == {p: 0 for p in F.PAIRS}


def test_monday_without_the_8_oclock_bars_asks_about_the_line(monkeypatch, tmp_path, capsys):
    """Yahoo は月曜の 8:00〜8:55（冬時間）が無い＝12本欠け。計算はするが、線が合っているかを聞いてから書く"""
    skip = [f"08:{m:02d}" for m in range(0, 60, 5)]
    b5 = world(skip=skip)
    assert cli(monkeypatch, tmp_path, b5=b5) == 2 and not os.path.exists(T.JOURNAL)
    out = capsys.readouterr().out
    assert "200.020" in out and "--break-line" in out and "--unknown line" in out and "12本" in out
    assert cli(monkeypatch, tmp_path, "--unknown", "line", b5=b5) == 0
    os.remove(T.JOURNAL)
    assert cli(monkeypatch, tmp_path, "--break-line", str(price(3)), b5=b5) == 0
    assert T.load()["trades"][0]["break_line"] == 200.03


def test_ten_missing_bars_are_fine(monkeypatch, tmp_path):
    skip = [f"08:{m:02d}" for m in range(0, 50, 5)]
    assert cli(monkeypatch, tmp_path, b5=world(skip=skip)) == 0


def test_missing_bars_of_another_pair_only_warn(monkeypatch, tmp_path, capsys):
    b5 = world()
    b5["USDJPY"] = bars(BASE["USDJPY"], MOVE, skip=[f"08:{m:02d}" for m in range(0, 60, 5)])
    assert cli(monkeypatch, tmp_path, b5=b5) == 0
    assert "ドル円" in capsys.readouterr().out.split("足が足りない")[0].split("⚠️")[-1]


def test_owner_line_wins():
    r = run(line=price(5))
    assert r["line"] == price(5) and r["line_auto"] == pytest.approx(price(2)) and r["break_bar"] == "14:40"
    assert run(line=price(11))["break_bar"] == "14:45"             # 14:40 の終値 +10 は線の内側


def test_other_day_and_pair():
    with pytest.raises(F.FillError):
        F.analyze(world(), {}, "EURUSD", "buy", at("15:31"))
    with pytest.raises(F.FillError):
        F.analyze(world(), {}, "GBPJPY", "buy", at("15:31") + dt.timedelta(days=1))   # その日の足が無い


# ── 30pips までの分 ────────────────────────────────

def far(high_bar, pips=33.0, b5=None, hm="15:31", **kw):
    """14:10 に抜けて、high_bar の足で線から pips 離れる"""
    mv = {"14:10": (0, 12, 0, 10), high_bar: (10, 2 + pips, 9, 10)}
    return F.analyze(world(move=mv), {}, "GBPJPY", "buy", at(hm), **kw)


def test_far_minutes():
    assert far("14:15")["far_min"] == 5
    assert far("14:40")["far_min"] == 30 and far("14:40")["far_state"] is True
    r = far("14:45")
    assert r["far_min"] == 35 and r["far_state"] is False
    mv = {"14:10": (0, 35, 0, 10)}
    assert F.analyze(world(move=mv), {}, "GBPJPY", "buy", at("15:31"))["far_min"] == 0      # 抜けた足そのもの


def test_far_never():
    r = far("14:20", pips=20)
    assert r["far_min"] is None and r["far_state"] is False and r["leg_pips"] == 20.0


def test_far_borderline_is_unknown():
    for p in (29.6, 30.0, 30.4):
        assert far("14:20", pips=p)["far_state"] is None
    assert far("14:20", pips=29.4)["far_state"] is False and far("14:20", pips=30.6)["far_state"] is True


def test_far_borderline_first_then_sure_within_30_is_yes():
    mv = {"14:10": (0, 12, 0, 10), "14:15": (10, 32.2, 9, 10), "14:30": (10, 40, 9, 10)}
    r = F.analyze(world(move=mv), {}, "GBPJPY", "buy", at("15:31"))
    assert r["far_state"] is True and r["far_min"] == 5


def test_far_borderline_first_then_sure_after_30_is_unknown():
    mv = {"14:10": (0, 12, 0, 10), "14:15": (10, 32.2, 9, 10), "15:00": (10, 40, 9, 10)}
    r = F.analyze(world(move=mv), {}, "GBPJPY", "buy", at("15:31"))
    assert r["far_state"] is None and r["far_min"] is None


def test_far_late_either_way_is_no():
    mv = {"14:10": (0, 12, 0, 10), "15:00": (10, 32.2, 9, 10)}
    r = F.analyze(world(move=mv), {}, "GBPJPY", "buy", at("15:31"))
    assert r["far_state"] is False and r["far_min"] == 50


def test_high_after_entry_is_not_used():
    mv = {"14:10": (0, 12, 0, 10), "14:15": (10, 60, 9, 10)}
    r = F.analyze(world(move=mv), {}, "GBPJPY", "buy", at("14:17"))          # 入ったのは 14:15 の足の中
    assert r["far_min"] is None and r["leg_pips"] == 10.0                    # 1分足が無ければ、その足は使わない（抜けた足 +12 − 線 +2）
    one = {"GBPJPY": ones(moves={"14:15": (10, 20, 9, 12), "14:16": (12, 45, 10, 12), "14:17": (12, 60, 10, 12)}, start="14:10", end="14:30", px=10)}
    r = F.analyze(world(move=mv), one, "GBPJPY", "buy", at("14:17"))
    assert r["leg_pips"] == 43.0 and r["far_min"] == 5                       # 入る1分前まで（+45）だけ


# ── いちばん遠い値・何％戻したか ──────────────────────

def test_extreme_leg_and_depth():
    r = run(entry=price(21))
    assert r["extreme"] == pytest.approx(price(40)) and r["leg_pips"] == 38.0 and r["depth_pct"] == 50.0
    r = run(entry=price(21), extreme=price(44))
    assert r["extreme"] == price(44) and r["leg_pips"] == 42.0


# ── 線に当たったか（3pips 以内）──────────────────────

def test_half50_hit_and_types():
    r = run()
    assert r["hits"]["GBPJPY"]["half50"] == 0.0                              # 15:05 の足が +20〜+27＝50%（+21）をまたぐ
    assert r["entry_types"] == ["half50"] and r["maybe_types"] == []
    assert r["pairs_hit"] == 3 and r["pairs_state"] is True


def near(low):
    """入る所の安値が low（base からの pips）。50% は +21"""
    mv = dict(MOVE, **{"15:00": (29, 30, 26, 26), "15:05": (26, 27, low, low + 1)})
    b1 = {p: ones(p, {"15:00": (29, 30, 26, 26), "15:05": (26, 27, low, low + 1)}, px=29.0) for p in F.PAIRS}
    return run(b5=world(move=mv), b1=b1)


def test_distance_edges():
    r = near(23.5)
    assert r["hits"]["GBPJPY"]["half50"] == 2.5 and r["hit_state"]["GBPJPY"] is True
    for low in (23.6, 24.0, 24.5):
        r = near(low)
        assert r["hit_state"]["GBPJPY"] is None and r["maybe_types"] == ["half50"] and r["entry_types"] == []
    r = near(24.6)
    assert r["hit_state"]["GBPJPY"] is False and r["maybe_types"] == [] and r["pairs_hit"] == 0 and r["pairs_state"] is False


def test_price_far_beyond_the_line_is_not_a_hit():
    mv = dict(MOVE, **{"14:55": (38, 39, 11, 12), "15:00": (12, 13, 11, 12), "15:05": (12, 13, 11, 12)})   # 前に 50% を割って +12 にいる
    b1 = {p: ones(p, px=12.0) for p in F.PAIRS}
    r = run(b5=world(move=mv), b1=b1)
    assert r["hits"]["GBPJPY"]["half50"] == 8.0 and "half50" not in r["entry_types"] + r["maybe_types"]


def test_break_line_hit():
    mv = {"14:10": (0, 12, 0, 10), "14:15": (10, 100, 9, 90), "15:20": (90, 90, 10, 10), "15:25": (10, 10, 10, 10), "15:30": (10, 10, 4, 5)}   # 50% ＝ +51・MA は +43 あたり
    b1 = {p: ones(p, {"15:30": (10, 10, 4, 5)}, px=10.0) for p in F.PAIRS}
    r = run(hm="15:31", b5=world(move=mv), b1=b1)
    assert r["hits"]["GBPJPY"]["line"] == 2.0 and r["entry_types"] == ["line"]


def test_ma_hit_uses_last_completed_15m_ema():
    b5 = world()
    e = F.ema15(b5["GBPJPY"])
    i = next(k for k, b in enumerate(b5["GBPJPY"]) if b[0] == ts("15:05"))
    lv = e[i]
    pips = (lv - BASE["GBPJPY"]) * 100
    b1 = {p: ones(p, px=pips + 2.0) for p in F.PAIRS}
    mv = dict(MOVE, **{"15:00": (pips + 8, pips + 9, pips + 6, pips + 6)})
    r = F.analyze({p: bars(BASE[p], mv) for p in F.PAIRS}, b1, "GBPJPY", "buy", at("15:06"))
    assert r["hits"]["GBPJPY"]["ema15"] == 2.0 and r["entry_types"] == ["ema15"]


def test_ema15_by_hand():
    b = [(ts("09:00") + 300 * k, 0, 0, 0, float(c)) for k, c in enumerate([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])]
    e = F.ema15(b)
    assert e[0] is None and e[2] is None                                     # 最初の15分足が終わるまでは無い
    assert e[3] == e[5] == 3.0                                               # 09:00 の15分足の終値
    assert e[6] == e[8] == pytest.approx(3 + 2 / 11 * (6 - 3))
    assert e[9] == pytest.approx(e[8] + 2 / 11 * (9 - e[8]))


def test_ema15_missing_bar_uses_last_close_in_bucket():
    b = [(ts("09:00"), 0, 0, 0, 1.0), (ts("09:05"), 0, 0, 0, 2.0), (ts("09:15"), 0, 0, 0, 9.0)]      # 09:10 が欠け
    assert F.ema15(b)[2] == 2.0


def test_each_pair_uses_its_own_line():
    b5 = world()
    b5["EURJPY"] = bars(BASE["EURJPY"], {"14:40": (0, 12, 0, 10), "14:45": (10, 100, 9, 90), "15:00": (90, 91, 89, 90)})        # 50% ＝ +51・いまは +90
    b1 = {p: ones(p, {"15:00": (29, 30, 25, 26), "15:05": (26, 27, 20, 22)}, px=29.0) for p in F.PAIRS}
    b1["EURJPY"] = ones("EURJPY", px=90.0)
    r = run(b5=b5, b1=b1)
    assert r["hits"]["EURJPY"]["half50"] == 38.0 and r["pairs_hit"] == 2 and r["pairs_state"] is True


def test_unbroken_pair_only_has_ma():
    b5 = world()
    b5["USDJPY"] = bars(BASE["USDJPY"])
    b1 = {p: ones(p, {"15:00": (29, 30, 25, 26), "15:05": (26, 27, 20, 22)}, px=29.0) for p in F.PAIRS}
    b1["USDJPY"] = ones("USDJPY", px=-6.0)
    r = run(b5=b5, b1=b1)
    assert set(r["hits"]["USDJPY"]) == {"ema15"} and r["signal"] is None
    assert r["pairs_hit"] == 3                                               # ドル円は MA（平ら＝−6）の上にいる


def test_window_starts_at_previous_5m_bar():
    """前の5分足の中で当たっていれば、当たり（機械の数え方＝当たった足の次の足の始値で入る、と同じ幅）"""
    mv = dict(MOVE, **{"15:00": (29, 30, 20, 27), "15:05": (27, 30, 27, 29)})
    b1 = {p: ones(p, {"15:00": (29, 30, 20, 27), "15:05": (27, 30, 27, 29)}, px=29.0) for p in F.PAIRS}
    assert run(b5=world(move=mv), b1=b1)["hit_state"]["GBPJPY"] is True
    mv = dict(MOVE, **{"14:55": (38, 39, 20, 27), "15:00": (27, 30, 27, 29), "15:05": (29, 30, 29, 29)})      # 2本前＝数えない
    b1 = {p: ones(p, {"14:59": (29, 30, 20, 29), "15:00": (27, 30, 27, 29)}, start="14:50", px=29.0) for p in F.PAIRS}
    assert run(b5=world(move=mv), b1=b1)["hits"]["GBPJPY"]["half50"] == 6.0


def test_move_after_entry_minute_is_not_used():
    mv = dict(MOVE, **{"15:00": (29, 30, 29, 29), "15:05": (29, 30, 5, 22)})
    b1 = {p: ones(p, {"15:00": (29, 30, 29, 29), "15:07": (29, 29, 5, 22)}, px=29.0) for p in F.PAIRS}        # 下げは 15:07＝入ったあと
    x = run(b5=world(move=mv), b1=b1)
    assert x["hits"]["GBPJPY"]["half50"] == 8.0 and x["entry_types"] == x["maybe_types"] == []
    b1 = {p: ones(p, {"15:00": (29, 30, 29, 29), "15:06": (29, 29, 21, 22)}, px=29.0) for p in F.PAIRS}       # 入った分は含める
    assert run(b5=world(move=mv), b1=b1)["hits"]["GBPJPY"]["half50"] == 0.0


def test_without_1m_bars_the_entry_bar_is_only_maybe():
    mv = dict(MOVE, **{"15:00": (29, 30, 29, 29), "15:05": (29, 30, 12, 22)})
    r = run(b5=world(move=mv), b1={})
    assert r["coarse"] is True and r["hit_state"]["GBPJPY"] is None and r["maybe_types"] == ["half50"] and r["pairs_hit"] is None
    mv = dict(MOVE, **{"15:00": (29, 30, 20, 27), "15:05": (27, 30, 27, 29)})                                # 前の足だけで当たり＝確か
    r = run(b5=world(move=mv), b1={})
    assert r["hit_state"]["GBPJPY"] is True and r["entry_types"] == ["half50"]
    assert run()["coarse"] is False


# ── ペアの数・合図 ────────────────────────────────

def test_pairs_state_when_some_are_maybe():
    S = F.pairs_of
    assert S({"a": True, "b": True, "c": None}) == (2, True)                 # 2以上は確か
    assert S({"a": True, "b": None, "c": False}) == (None, None)             # 1か2か分からない
    assert S({"a": None, "b": False, "c": False}) == (0, False)              # どちらでも2に届かない
    assert S({"a": True, "b": False, "c": False}) == (1, False)
    assert S({"a": True, "b": True, "c": True}) == (3, True)


def test_signal_needs_all_three_closes_at_the_same_bar():
    assert run()["signal"] == "14:40"
    b5 = world()
    b5["EURJPY"] = bars(BASE["EURJPY"], dict(MOVE, **{"14:40": (0, 1, 0, 0), "14:45": (0, 5, 0, 4), "14:50": (4, 40, 4, 38)}))
    assert run(b5=b5)["signal"] == "14:45"                                   # 最後に抜けたのがユーロ円の 14:45
    b5["GBPJPY"] = bars(BASE["GBPJPY"], dict(MOVE, **{"14:45": (10, 11, 0, 1), "14:50": (1, 40, 1, 38)}))
    assert run(b5=b5)["signal"] == "14:50"                                   # 14:45 はポンド円が線の内側


# ── Yahoo の読み取り ──────────────────────────────

def test_parse_drops_empty_bars():
    j = {"chart": {"result": [{"timestamp": [100, 400, 700], "indicators": {"quote": [{"open": [1, None, 3], "high": [1, None, 3],
         "low": [1, None, 3], "close": [1, None, 3]}]}}]}}
    assert F.parse(j) == [(100, 1.0, 1.0, 1.0, 1.0), (700, 3.0, 3.0, 3.0, 3.0)]
    assert F.parse({"chart": {"result": [{"indicators": {"quote": [{}]}}]}}) == []


def test_fetch_asks_yahoo_and_load_survives_missing_1m(monkeypatch):
    seen = []

    def fake(req, timeout=0):
        seen.append(req.full_url)
        if "interval=1m" in req.full_url:
            raise OSError("30日より前")
        j = {"chart": {"result": [{"timestamp": [100], "indicators": {"quote": [{"open": [1], "high": [1], "low": [1], "close": [1]}]}}]}}
        return io.BytesIO(json.dumps(j).encode())
    monkeypatch.setattr(F.urllib.request, "urlopen", fake)
    monkeypatch.setattr(F.time, "sleep", lambda s: None)
    b5, b1 = F.load(at("15:31"))
    assert set(b5) == set(F.PAIRS) and b1 == {}
    assert any("GBPJPY=X" in u and "interval=5m" in u for u in seen)
    a = int(next(u for u in seen if "interval=5m" in u).split("period1=")[1].split("&")[0])
    assert ts("15:31") - a >= 5 * 86400                                      # EMA のために何日か前から取る


def test_load_fails_when_5m_is_missing(monkeypatch):
    def fake(req, timeout=0):
        raise OSError("x")
    monkeypatch.setattr(F.urllib.request, "urlopen", fake)
    monkeypatch.setattr(F.time, "sleep", lambda s: None)
    with pytest.raises(F.FillError):
        F.load(at("15:31"))


# ── 記録（trade_journal）とつなぐ ─────────────────────

def cli(monkeypatch, tmp_path, *extra, b5=None, b1=None, cmd="add", entry=21, hm="15:06", pair="GBPJPY"):
    monkeypatch.chdir(tmp_path)
    b5 = world() if b5 is None else b5
    b1 = {p: ones(p, {"15:00": (29, 30, 25, 26), "15:05": (26, 27, 20, 22)}, px=29.0) for p in F.PAIRS} if b1 is None else b1
    monkeypatch.setattr(F, "load", lambda t: (b5, b1))
    a = [cmd, "--pair", pair, "--side", "buy", "--open", f"2026.12.01 {hm}:08", "--entry", str(price(entry))]
    if cmd == "add":
        a += ["--id", "900", "--sl", str(price(-2)), "--close", "2026.12.01 15:50:00", "--exit", str(price(30)), "--spread", "1.8",
              "--flags", "strongest=1,event_clear=1", "--auto"]
    return T.main(a + list(extra))


def test_add_auto_fills_everything(monkeypatch, tmp_path, capsys):
    assert cli(monkeypatch, tmp_path) == 0
    t = T.load()["trades"][0]
    assert t["entry_type"] == "half50" and t["break_line"] == 200.02 and t["extreme"] == 200.4 and t["leg_pips"] == 38.0
    assert t["far_min"] == 10 and t["pairs_hit"] == 3 and t["flags"]["tokyo_break"] is True and t["fits_v2_entry"] is True
    assert set(t["filled"]) == {"entry_type", "break_line", "extreme", "far_min", "pairs_hit", "pairs_lm", "tokyo_break"}
    out = capsys.readouterr().out
    assert "14:40" in out and "10分" in out


def test_explicit_values_win(monkeypatch, tmp_path):
    cli(monkeypatch, tmp_path, "--entry-type", "ema15", "--far-min", "25", "--pairs-hit", "1", "--pairs-lm", "1", "--break-line", str(price(5)), "--extreme", str(price(44)))
    t = T.load()["trades"][0]
    assert t["entry_type"] == "ema15" and t["far_min"] == 25 and t["pairs_hit"] == 1 and t["break_line"] == 200.05 and t["extreme"] == 200.44
    assert t["filled"] == ["tokyo_break"]


def test_manual_tokyo_flag_wins(monkeypatch, tmp_path):
    cli(monkeypatch, tmp_path, "--flags", "strongest=1,event_clear=1,tokyo_break=0")
    t = T.load()["trades"][0]
    assert t["flags"]["tokyo_break"] is False and "tokyo_break" not in t["filled"]


def test_no_signal_leaves_tokyo_unknown(monkeypatch, tmp_path):
    b5 = world()
    b5["USDJPY"] = bars(BASE["USDJPY"])
    cli(monkeypatch, tmp_path, b5=b5)
    t = T.load()["trades"][0]
    assert t["flags"]["tokyo_break"] is None                                  # 見つからない＝×とは決めない


def test_borderline_is_not_written(monkeypatch, tmp_path, capsys):
    mv = dict(MOVE, **{"14:50": (24, 32.2, 23, 30), "14:55": (30, 31, 29, 30)})       # 線から 30.2pips＝境目・50% は +17.1
    assert cli(monkeypatch, tmp_path, b5=world(move=mv)) == 2
    assert not os.path.exists(T.JOURNAL)
    out = capsys.readouterr().out
    assert "境目" in out and "--far-min" in out


def test_unknown_lets_it_through(monkeypatch, tmp_path):
    mv = dict(MOVE, **{"14:50": (24, 31.8, 23, 30), "14:55": (30, 31, 29, 30)})       # 29.8pips＝境目
    assert cli(monkeypatch, tmp_path, "--unknown", "far,type,pairs", b5=world(move=mv)) == 0
    t = T.load()["trades"][0]
    assert t["far_min"] is None and t["flags"]["far30"] is None and t["leg_pips"] == 29.8         # ×とも○とも書かない
    assert t["entry_type"] == "other" and t["fits_v2_entry"] is False and t["pairs_hit"] is None


def test_two_lines_at_once_asks_which(monkeypatch, tmp_path, capsys):
    b1 = {p: ones(p, {"15:05": (29, 30, 1, 5), "15:06": (5, 22, 5, 21)}, px=29.0) for p in F.PAIRS}       # 50% も線も MA もまたぐ
    assert cli(monkeypatch, tmp_path, b1=b1) == 2
    assert "--entry-type" in capsys.readouterr().out
    assert cli(monkeypatch, tmp_path, "--entry-type", "half50", b1=b1) == 0


def test_no_line_hit_asks_type_and_unknown_becomes_other(monkeypatch, tmp_path):
    b1 = {p: ones(p, px=36.0) for p in F.PAIRS}
    assert cli(monkeypatch, tmp_path, b1=b1) == 2
    assert cli(monkeypatch, tmp_path, "--unknown", "type", b1=b1) == 0
    assert T.load()["trades"][0]["entry_type"] == "other"


def test_unknown_word_is_rejected(monkeypatch, tmp_path):
    with pytest.raises(SystemExit):
        cli(monkeypatch, tmp_path, "--unknown", "foo")


def test_other_pairs_are_recorded_without_filling(monkeypatch, tmp_path, capsys):
    assert cli(monkeypatch, tmp_path, pair="AUDJPY") == 0
    t = T.load()["trades"][0]
    assert t["filled"] == [] and t["far_min"] is None and t["entry_type"] == "other"
    assert "ドル円・ユーロ円・ポンド円" in capsys.readouterr().out


def test_fetch_failure_is_not_written(monkeypatch, tmp_path, capsys):
    def boom(t):
        raise F.FillError("Yahoo から5分足が取れない")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(F, "load", boom)
    a = ["add", "--id", "1", "--pair", "GBPJPY", "--side", "buy", "--open", "2026.12.01 15:31", "--entry", "200.2", "--sl", "199.9",
         "--close", "2026.12.01 15:50", "--exit", "200.3", "--auto"]
    assert T.main(a) == 2 and not os.path.exists(T.JOURNAL)
    assert "取れない" in capsys.readouterr().out


def test_add_without_auto_never_fetches(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(F, "load", lambda t: pytest.fail("取りに行った"))
    T.main(["add", "--id", "1", "--pair", "GBPJPY", "--side", "buy", "--open", "2026.12.01 15:31", "--entry", "200.2", "--sl", "199.9",
            "--close", "2026.12.01 15:50", "--exit", "200.3"])
    t = T.load()["trades"][0]
    assert t["filled"] == [] and t["entry_type"] == "other"


def test_fill_only_looks(monkeypatch, tmp_path, capsys):
    assert cli(monkeypatch, tmp_path, cmd="fill", b5=flow_world(-14)) == 0        # ポンド円がいちばん強い世界
    assert not os.path.exists(T.JOURNAL)
    out = capsys.readouterr().out
    for w in ("200.020", "14:40", "10分", "200.400", "50%", "3ペア"):
        assert w in out


def test_duplicate_is_rejected_before_fetching(monkeypatch, tmp_path):
    cli(monkeypatch, tmp_path)
    monkeypatch.setattr(F, "load", lambda t: pytest.fail("取りに行った"))
    with pytest.raises(SystemExit):
        T.main(["add", "--id", "900", "--pair", "GBPJPY", "--side", "buy", "--open", "2026.12.01 15:31", "--entry", "200.2", "--sl", "199.9",
                "--close", "2026.12.01 15:50", "--exit", "200.3", "--auto"])


def test_owner_line_far_from_yahoo_is_warned(monkeypatch, tmp_path, capsys):
    cli(monkeypatch, tmp_path, "--break-line", str(price(9)), cmd="fill")
    assert "7.0pips" in capsys.readouterr().out


def test_owner_says_it_reached_on_the_borderline(monkeypatch, tmp_path):
    mv = dict(MOVE, **{"14:50": (24, 31.8, 23, 30), "14:55": (30, 31, 29, 30)})       # Yahoo では 29.8pips＝境目
    assert cli(monkeypatch, tmp_path, "--far-min", "10", "--entry-type", "half50", "--pairs-hit", "2", b5=world(move=mv)) == 0
    t = T.load()["trades"][0]
    assert t["leg_pips"] == 29.8 and t["far_min"] == 10 and t["flags"]["far30"] is True and t["fits_v2_entry"] is True


def test_clear_contradiction_is_still_rejected(monkeypatch, tmp_path):
    mv = dict(MOVE, **{"14:50": (24, 31.4, 23, 30), "14:55": (30, 31, 29, 30)})       # 29.4pips＝届いていないと分かる
    with pytest.raises(ValueError):
        cli(monkeypatch, tmp_path, "--far-min", "10", "--entry-type", "half50", "--pairs-hit", "2", b5=world(move=mv))


def test_owner_extreme_says_it_did_not_reach(monkeypatch, tmp_path):
    mv = dict(MOVE, **{"14:50": (24, 32.2, 23, 30), "14:55": (30, 31, 29, 30)})       # Yahoo では 30.2pips＝境目
    assert cli(monkeypatch, tmp_path, "--break-line", str(price(2)), "--extreme", str(price(31.5)), "--entry-type", "half50", "--pairs-hit", "2", b5=world(move=mv)) == 0
    t = T.load()["trades"][0]
    assert t["leg_pips"] == 29.5 and t["far_min"] is None and t["flags"]["far30"] is False


def test_question_shows_the_distance_within_30_minutes():
    mv = {"14:10": (0, 12, 0, 10), "14:15": (10, 32.2, 9, 10), "15:00": (10, 40, 9, 10)}
    r = F.analyze(world(move=mv), {}, "GBPJPY", "buy", at("15:31"))
    assert r["far30_pips"] == 30.2 and r["leg_pips"] == 38.0
    q = F.questions(r, {"entry_type", "pairs_lm", "strongest"}, set())
    assert len(q) == 1 and "30.2pips" in q[0]


def test_no_bars_around_entry_is_unknown_not_no():
    r = run(b5=world(skip=("15:00", "15:05")), b1={})
    assert r["hit_state"]["GBPJPY"] is None and r["hits"]["GBPJPY"]["half50"] is None and r["pairs_hit"] is None
    assert "足が無い" in F.report(r)


# ── 壊し試験で見つけた穴と、線しだいで変わるとき ─────────────

def test_1400_bar_can_break_and_equal_is_not_a_break():
    r = run(b5=world(move=dict(MOVE, **{"14:00": (0, 12, 0, 10)})))
    assert r["break_bar"] == "14:00"
    r = run(b5=world(move=dict(MOVE, **{"14:35": (0, 2, 0, 2)})))           # 終値が線ちょうど＝抜けでない
    assert r["break_bar"] == "14:40"


def test_line_matters_for_30pips_is_asked(monkeypatch, tmp_path, capsys):
    mv = dict(MOVE, **{"14:50": (24, 29, 23, 28), "14:55": (28, 29, 27, 28)})        # 28pips＝届いていない。線が 4pips 内側なら 32pips
    b5 = world(move=mv)
    more = ("--entry-type", "half50", "--pairs-hit", "2")
    assert cli(monkeypatch, tmp_path, *more, b5=b5) == 2
    out = capsys.readouterr().out
    assert out.count("❓") == 1 and "200.020" in out and "--break-line" in out and not os.path.exists(T.JOURNAL)
    assert cli(monkeypatch, tmp_path, *more, "--break-line", str(price(-2)), b5=b5) == 0
    assert T.load()["trades"][0]["flags"]["far30"] is True
    os.remove(T.JOURNAL)
    assert cli(monkeypatch, tmp_path, *more, "--unknown", "line", b5=b5) == 0
    t = T.load()["trades"][0]
    assert t["flags"]["far30"] is False and t["leg_pips"] == 28.0
    os.remove(T.JOURNAL)
    assert cli(monkeypatch, tmp_path, *more, "--extreme", str(price(29)), b5=b5) == 2      # 遠い値だけでは線のずれは分からない


def test_line_outside_side_also_matters(monkeypatch, tmp_path):
    mv = dict(MOVE, **{"14:50": (24, 35, 23, 34), "14:55": (34, 35, 30, 32)})        # 33pips＝届いた。線が 4pips 外なら 29pips
    assert run(b5=world(move=mv))["far_if"] == (True, False)
    assert cli(monkeypatch, tmp_path, "--entry-type", "half50", "--pairs-hit", "2", b5=world(move=mv)) == 2


def test_far_from_the_edge_is_not_asked():
    assert run()["far_if"] == (True, True)                                           # 38pips＝線が ±4pips ずれても届いている
    mv = dict(MOVE, **{"14:50": (24, 25, 20, 22), "14:55": (22, 23, 20, 22), "15:00": (22, 23, 20, 22)})
    r = run(b5=world(move=mv))
    assert r["far_state"] is False and r["far_if"] == (False, False)
    assert run(line=price(3))["far_if"] is None                                      # 線を渡したら確かめない


def test_minutes_given_do_not_ask_the_line(monkeypatch, tmp_path):
    mv = dict(MOVE, **{"14:50": (24, 35, 23, 34), "14:55": (34, 35, 30, 32)})
    assert cli(monkeypatch, tmp_path, "--entry-type", "half50", "--pairs-hit", "2", "--far-min", "10", b5=world(move=mv)) == 0


def test_signal_ignores_night_bars_above_the_line():
    mv = dict(MOVE, **{"01:00": (50, 51, 49, 50), "01:05": (-6, -5, -8, -6)})          # 夜中は線より上にいた＝合図ではない
    assert run(b5=world(move=mv))["signal"] == "14:40"


def test_far_if_is_inner_then_outer_for_sell_too():
    mv = dict(MOVE, **{"14:50": (24, 35, 23, 34), "14:55": (34, 35, 30, 32)})
    assert run(side=-1, b5=world(-1, move=mv))["far_if"] == (True, False)


def test_tolerance_is_the_same_in_both_tools():
    assert (T.FILL_TOL, T.FAR_PIPS, T.FAR_MIN) == (F.TOL, F.FAR_PIPS, F.FAR_MIN)


# ── 決まりの紙 v3（追記⑧）＝線か MA に当たったペアの数・一番強い通貨 ─────────────────

def level(b5, pair, hm="15:05"):
    """その足の MA（base からの pips）"""
    e = F.ema15(b5[pair])
    return round((e[next(k for k, b in enumerate(b5[pair]) if b[0] == ts(hm))] - BASE[pair]) * 100, 3)


# 14:20 に抜け・14:25 に +40（線 +2 から 38pips）→ +36 のまま＝15:05 の MA は +13 前後（線 +2・50% ＋21 のどちらからも離れている）
MV3 = {"14:20": (0, 12, 0, 10), "14:25": (10, 40, 9, 36)}


def stay(px):
    """15:00 から px（base からの pips）のまま動かない＝その値だけを見る"""
    return dict(MV3, **{"15:00": (px, px, px, px), "15:05": (px, px, px, px)})


def three(u, e, g, b1=True):
    """15:06 に、ドル円＝u・ユーロ円＝e・ポンド円＝g（pips）にいる世界"""
    pos = dict(zip(F.PAIRS, (u, e, g)))
    b5 = {p: bars(BASE[p], stay(pos[p])) for p in F.PAIRS}
    return b5, {p: ones(p, px=pos[p]) for p in F.PAIRS} if b1 else {}


MA = level(world(move=MV3), "GBPJPY")


def test_ma_level_is_away_from_the_line_and_the_half_in_these_worlds():
    assert 2 + 3.5 + 4 < MA < 21 - 3.5 and all(level(world(move=MV3), p) == pytest.approx(MA, abs=0.01) for p in F.PAIRS)


def test_half50_does_not_count_for_v3():
    r = run()                                                                        # 3ペアとも 50%（+21）だけ
    assert r["pairs_hit"] == 3 and r["pairs_lm"] == 0 and r["pairs_lm_state"] is False


def test_two_pairs_on_the_ma_count():
    b5, b1 = three(36, MA, MA)
    r = run(b5=b5, b1=b1)
    assert r["pairs_lm"] == 2 and r["pairs_lm_state"] is True and r["lm_state"] == {"USDJPY": False, "EURJPY": True, "GBPJPY": True}
    b5, b1 = three(36, 36, MA)
    r = run(b5=b5, b1=b1)
    assert r["pairs_lm"] == 1 and r["pairs_lm_state"] is False
    assert run(b5=three(MA, MA, MA)[0], b1=three(MA, MA, MA)[1])["pairs_lm"] == 3


def test_ma_within_3pips_and_the_edge():
    for d, want in ((2.4, True), (3.0, None), (3.6, False)):
        b5, b1 = three(36, MA + d, MA + d)
        r = run(b5=b5, b1=b1)
        assert r["lm_state"]["EURJPY"] is want and r["lm_state"]["GBPJPY"] is want


def test_owner_line_counts_as_it_is():
    b5, b1 = three(36, MA, 24)
    r = run(b5=b5, b1=b1, line=price(24))                                            # 渡した線（+24）の上にいる＝線を割った足は 14:50
    assert r["lm_state"]["GBPJPY"] is True and r["pairs_lm"] == 2


def test_computed_line_hit_that_depends_on_4pips_is_unknown():
    b5, b1 = three(36, 36, 36)
    b5["GBPJPY"] = bars(BASE["GBPJPY"], stay(8))                                       # MA（+13）からは離れている
    b1["GBPJPY"] = ones("GBPJPY", {"15:05": (8, 8, -6, -6)}, px=8.0)                   # 線（+2）を深くまたぐ
    r = run(b5=b5, b1=b1)
    assert r["hits"]["GBPJPY"]["ema15"] > 3.5 and r["lm_state"]["GBPJPY"] is True      # ±4pips ずれても当たっている
    assert run(b5=three(36, 36, 0.0)[0], b1=three(36, 36, 0.0)[1])["lm_state"]["GBPJPY"] is None      # 線が 4pips 内側でも当たり・4pips 外だと外れ
    assert run(b5=three(36, 36, 1.0)[0], b1=three(36, 36, 1.0)[1])["lm_state"]["GBPJPY"] is None      # 線（+2）のすぐ下・線が 4pips 外なら 5pips 離れている
    assert run(b5=three(36, 36, 1.0)[0], b1=three(36, 36, 1.0)[1], line=price(2))["lm_state"]["GBPJPY"] is True
    assert run(b5=three(36, 36, -2.0)[0], b1=three(36, 36, -2.0)[1])["lm_state"]["GBPJPY"] is None    # 線まで 4pips＝外れ。でも線が 4pips 内側なら当たり
    assert run(b5=three(36, 36, -2.0)[0], b1=three(36, 36, -2.0)[1], line=price(2))["lm_state"]["GBPJPY"] is False
    assert run(b5=three(36, 36, -5.6)[0], b1=three(36, 36, -5.6)[1])["lm_state"]["GBPJPY"] is False   # 線が 4pips 内側でも 3.6pips


def test_lm_question_only_when_two_or_not_depends(monkeypatch, tmp_path, capsys):
    b5, b1 = three(36, MA, MA + 3.0)                                                  # ユーロ円＝当たり・ポンド円＝境目
    assert cli(monkeypatch, tmp_path, "--entry-type", "ema15", b5=b5, b1=b1, entry=MA + 3) == 2
    out = capsys.readouterr().out
    assert out.count("❓") == 1 and "--pairs-lm" in out and not os.path.exists(T.JOURNAL)
    assert cli(monkeypatch, tmp_path, "--entry-type", "ema15", "--pairs-lm", "2", b5=b5, b1=b1, entry=MA + 3) == 0
    t = T.load()["trades"][0]
    assert t["pairs_lm"] == 2 and "pairs_lm" not in t["filled"]
    os.remove(T.JOURNAL)
    assert cli(monkeypatch, tmp_path, "--entry-type", "ema15", "--unknown", "pairs", b5=b5, b1=b1, entry=MA + 3) == 0
    t = T.load()["trades"][0]
    assert t["pairs_lm"] is None and t["flags"]["pairs_lm2"] is None and t["fits_v3_entry"] is None
    os.remove(T.JOURNAL)
    b5, b1 = three(MA, MA, MA + 3.0)                                                  # ほかの2つが当たり＝ポンド円がどちらでも2以上
    assert cli(monkeypatch, tmp_path, "--entry-type", "ema15", b5=b5, b1=b1, entry=MA + 3) == 0
    assert T.load()["trades"][0]["pairs_lm"] == 2


def test_v2_count_is_not_asked_any_more(monkeypatch, tmp_path):
    b1 = {p: ones(p, {"15:00": (29, 30, 25, 26), "15:05": (26, 27, 20, 22)}, px=29.0) for p in F.PAIRS}
    b5 = world()
    for p, low in (("USDJPY", 26.0), ("EURJPY", 24.0)):                               # 50% まで：ドル円＝遠い・ユーロ円＝境目
        mv = dict(MOVE, **{"15:00": (29, 30, 26, 26), "15:05": (26, 27, low, 26)})
        b5[p] = bars(BASE[p], mv)
        b1[p] = ones(p, {"15:00": (29, 30, 26, 26), "15:05": (26, 27, low, 26)}, px=29.0)
    assert cli(monkeypatch, tmp_path, b5=b5, b1=b1) == 0
    t = T.load()["trades"][0]
    assert t["pairs_hit"] is None and t["flags"]["pairs2"] is None and t["pairs_lm"] == 0


def test_series_type_when_the_strong_pair_has_not_touched(monkeypatch, tmp_path):
    b5, b1 = three(MA, MA, 36)                                                        # ポンド円はどの線からも遠い
    assert cli(monkeypatch, tmp_path, b5=b5, b1=b1, entry=36) == 0
    t = T.load()["trades"][0]
    assert t["entry_type"] == "series" and t["pairs_lm"] == 2 and t["fits_v2_entry"] is False
    assert {"entry_type", "pairs_lm"} <= set(t["filled"])


def test_type_prefers_line_and_ma_over_half50():
    S = F.type_of
    assert S({"half50": True, "line": False, "ema15": True}, True) == "ema15"          # v3 では 50% は当たりに入れない
    assert S({"half50": True, "line": False, "ema15": True}, False) == "ema15"
    assert S({"half50": True, "line": False, "ema15": False}, True) == "half50"
    assert S({"half50": True, "line": True, "ema15": True}, True) is None              # 線と MA の両方＝聞く
    assert S({"half50": True, "line": None, "ema15": False}, True) is None             # 線が境目＝聞く
    assert S({"half50": False, "line": None, "ema15": True}, True) == "ema15"
    assert S({"half50": None, "line": False, "ema15": False}, True) is None
    assert S({"half50": False, "line": False, "ema15": False}, True) == "series"
    assert S({"half50": False, "line": False, "ema15": False}, False) is None
    assert S({"half50": False, "line": False, "ema15": False}, None) is None           # 2ペア以上か分からない＝シリーズとは書かない
    assert S({"ema15": True}, True) == "ema15" and S({}, None) is None


def test_ma_and_half50_at_once_is_ma_without_asking(monkeypatch, tmp_path):
    b5 = world(move=MV3)
    b1 = {p: ones(p, {"15:05": (29, 30, MA - 1, MA), "15:06": (MA, 22, MA, 21)}, px=29.0) for p in F.PAIRS}       # 50% と MA をまたぐ・線（+2）までは 3.6pips より遠い
    assert cli(monkeypatch, tmp_path, b5=b5, b1=b1) == 0
    t = T.load()["trades"][0]
    assert t["entry_type"] == "ema15" and t["pairs_lm"] == 3


# ── 一番強い通貨（ドル円×ユーロポンドの向き） ──────────────────────

def test_pick_of_is_the_same_as_the_registered_rule():
    P = F.pick_of
    assert P(1, 1, -1) == ("GBPJPY", True) and P(1, 1, 1) == ("EURJPY", True)           # 買い：ユーロポンドが下＝ポンドが強い
    assert P(-1, -1, 1) == ("GBPJPY", True) and P(-1, -1, -1) == ("EURJPY", True)       # 売り：ユーロポンドが上＝ポンドが弱い
    assert P(1, -1, 1) == (None, True) and P(-1, 1, -1) == (None, True)                 # ドル円が逆＝決まらない
    assert P(1, None, 1) == (None, False) and P(1, 1, None) == (None, False)            # 境目
    assert P(1, -1, None) == (None, True)                                               # ドル円が逆なら、ユーロポンドが境目でも決まらない


def test_flow_is_last_complete_close_against_ema():
    b = [(ts("09:00") + 300 * k, 0, 0, 0, 100.0) for k in range(12)]
    f = F.flow_of
    assert f(b[:-1] + [(b[-1][0], 0, 0, 0, 100.02)], 0.01, 0.7) == (2.0, 1)
    assert f(b[:-1] + [(b[-1][0], 0, 0, 0, 99.98)], 0.01, 0.7) == (-2.0, -1)
    assert f(b[:-1] + [(b[-1][0], 0, 0, 0, 100.007)], 0.01, 0.7) == (0.7, 1)            # ちょうど幅＝決める
    assert f(b[:-1] + [(b[-1][0], 0, 0, 0, 100.006)], 0.01, 0.7) == (0.6, None)
    assert f(b[:-1] + [(b[-1][0], 0, 0, 0, 99.994)], 0.01, 0.7) == (-0.6, None)
    assert f(b[:2], 0.01, 0.7) == (None, None) and f([], 0.01, 0.7) == (None, None)     # MA がまだ無い


def flow_world(dg):
    """15:00 の足の終わりで、ユーロ円だけ dg pips 動かす＝ユーロポンドの向きを作る"""
    b5 = world()
    mv = dict(MOVE, **{"15:00": (29, 30, 25, 26 + dg)})
    b5["EURJPY"] = bars(BASE["EURJPY"], mv)
    return b5


def test_strong_pair_by_usdjpy_and_eurgbp():
    r = run(b5=flow_world(12))
    assert r["flow"]["USDJPY"][1] == 1 and r["flow"]["EURGBP"][1] == 1
    assert r["strong_flow"] == "EURJPY" and r["strong_state"] is False                   # 入ったのはポンド円
    r = run(b5=flow_world(-14))
    assert r["flow"]["EURGBP"][1] == -1 and r["strong_flow"] == "GBPJPY" and r["strong_state"] is True
    r = run(side=-1, b5={p: bars(BASE[p], dict(MOVE, **{"15:00": (29, 30, 25, 26 + (12 if p == "EURJPY" else 0))}), side=-1) for p in F.PAIRS})
    assert r["flow"]["USDJPY"][1] == -1 and r["flow"]["EURGBP"][1] == -1 and r["strong_flow"] == "EURJPY"      # 売り：下に強いほう


def test_flow_of_usdjpy_against_the_trade_is_undecided():
    b5 = flow_world(-14)
    b5["USDJPY"] = bars(BASE["USDJPY"], dict(MOVE, **{"14:55": (38, 39, -20, -20), "15:00": (-20, -18, -22, -20), "15:05": (-20, -18, -22, -20)}))
    r = run(b5=b5)
    assert r["flow"]["USDJPY"][1] == -1 and r["strong_flow"] is None and r["strong_state"] is False


def test_usdjpy_borderline_is_undecided():
    b5 = flow_world(-14)
    m = level(b5, "USDJPY", "15:00")
    for d, want in ((0.9, 1), (0.5, None), (-0.5, None), (-0.9, -1)):
        b5["USDJPY"] = bars(BASE["USDJPY"], dict(MOVE, **{"15:00": (m + d, m + d, m + d, m + d)}))
        r = run(b5=b5)
        assert r["flow"]["USDJPY"] == (pytest.approx(d, abs=0.01), want) and r["strong_flow"] == ("GBPJPY" if want == 1 else None)
        assert r["strong_state"] is {1: True, -1: False, None: None}[want]


def test_usdjpy_flow_ignores_the_entry_bar():
    b5 = flow_world(-14)
    b5["USDJPY"] = [b if b[0] != ts("15:05") else (b[0], b[1], b[2], b[3] - 1, b[4] - 1) for b in b5["USDJPY"]]
    assert run(b5=b5)["strong_flow"] == "GBPJPY"


def test_flow_uses_the_bar_before_the_entry_bar():
    b5 = flow_world(-14)
    b5["EURJPY"] = [b if b[0] != ts("15:05") else (b[0], b[1], b[2] + 1, b[3], b[4] + 1) for b in b5["EURJPY"]]      # 入った足（15:05）の終値は使わない
    assert run(b5=b5)["strong_flow"] == "GBPJPY"


def test_strong_far_is_the_largest_share_from_the_line():
    b5 = world()
    r = run(b5=b5)
    assert r["strong_far"] == "USDJPY"                                                   # 同じ 38pips なら、値の小さいドル円の割合が大きい
    b5["GBPJPY"] = bars(BASE["GBPJPY"], dict(MOVE, **{"14:50": (24, 47, 23, 38)}))
    assert run(b5=b5)["strong_far"] == "USDJPY"                                          # 45pips（0.225%）より 38pips（0.253%）＝割合で比べる
    b5["GBPJPY"] = bars(BASE["GBPJPY"], dict(MOVE, **{"14:50": (24, 70, 23, 38)}))
    assert run(b5=b5)["strong_far"] == "GBPJPY"
    b5["USDJPY"] = bars(BASE["USDJPY"])                                                  # 抜けていないペアは入れない
    b5["EURJPY"], b5["GBPJPY"] = bars(BASE["EURJPY"]), bars(BASE["GBPJPY"], MOVE)
    assert run(b5=b5)["strong_far"] == "GBPJPY"
    assert run(b5={p: bars(BASE[p]) for p in F.PAIRS})["strong_far"] is None


def no_strong(monkeypatch, tmp_path, *extra, **kw):
    return cli(monkeypatch, tmp_path, "--flags", "event_clear=1", *extra, **kw)


def test_strongest_is_filled_when_the_tool_agrees(monkeypatch, tmp_path):
    assert no_strong(monkeypatch, tmp_path, b5=flow_world(-14)) == 0
    t = T.load()["trades"][0]
    assert t["flags"]["strongest"] is True and "strongest" in t["filled"] and t["strong_flow"] == "GBPJPY" and t["strong_far"] == "USDJPY"


def test_strongest_is_asked_when_the_tool_disagrees(monkeypatch, tmp_path, capsys):
    assert no_strong(monkeypatch, tmp_path, b5=flow_world(12)) == 2 and not os.path.exists(T.JOURNAL)
    out = capsys.readouterr().out
    assert out.count("❓") == 1 and "ユーロ円" in out.split("❓")[1] and "strongest=1" in out
    assert no_strong(monkeypatch, tmp_path, "--unknown", "strong", b5=flow_world(12)) == 0
    t = T.load()["trades"][0]
    assert t["flags"]["strongest"] is None and t["strong_flow"] == "EURJPY"              # ×とは決めない
    os.remove(T.JOURNAL)
    assert cli(monkeypatch, tmp_path, b5=flow_world(12)) == 0                            # オーナーの見立て（strongest=1）が優先
    t = T.load()["trades"][0]
    assert t["flags"]["strongest"] is True and "strongest" not in t["filled"] and t["flags"]["pick_flow"] is False
    os.remove(T.JOURNAL)
    assert cli(monkeypatch, tmp_path, "--flags", "strongest=0,event_clear=1", b5=flow_world(-14)) == 0
    assert T.load()["trades"][0]["flags"]["strongest"] is False


def test_strongest_borderline_is_asked(monkeypatch, tmp_path, capsys):
    b5 = flow_world(0)
    i = [b[0] for b in b5["EURJPY"]].index(ts("15:00"))
    g = {b[0]: b[4] for b in b5["GBPJPY"]}
    e = F.ema15([(b[0], 0, 0, 0, b[4] / g[b[0]]) for b in b5["EURJPY"]])[i]
    b = b5["EURJPY"][i]
    c = (e + 0.2e-4) * g[b[0]]                                                            # ユーロポンドが MA の 0.2pips 上＝境目
    b5["EURJPY"][i] = (b[0], b[1], max(b[2], c), min(b[3], c), c)
    r = run(b5=b5)
    assert r["flow"]["EURGBP"][1] is None and r["strong_flow"] is None and r["strong_state"] is None
    assert no_strong(monkeypatch, tmp_path, b5=b5) == 2
    assert "境目" in capsys.readouterr().out.split("❓")[1]


def test_report_shows_the_count_and_the_strong_pair():
    b5, b1 = three(36, MA, MA)
    out = F.report(run(b5=b5, b1=b1))
    assert "線か MA に当たっていたペア：2ペア（ユーロ円＝15分足MA・ポンド円＝15分足MA）" in out and "一番強い通貨" in out and "線からいちばん遠い" in out
    assert "当たっていたペア：0ペア →" in F.report(run())
    b5, b1 = three(36, MA, MA + 3.0)
    assert "2以上かどうかが境目（ユーロ円＝15分足MA・ポンド円＝境目）" in F.report(run(b5=b5, b1=b1))
    b1 = {p: ones(p, {"15:05": (29, 30, MA - 1, MA), "15:06": (MA, 22, MA, 21)}, px=29.0) for p in F.PAIRS}
    assert "ポンド円＝15分足MA）" in F.report(run(b5=world(move=MV3), b1=b1))               # 50% もまたいだが、名前は MA だけ


def test_v3_flags_are_filled_from_the_tool(monkeypatch, tmp_path):
    b5, b1 = three(36, MA, MA)
    cli(monkeypatch, tmp_path, b5=b5, b1=b1, entry=MA)
    t = T.load()["trades"][0]
    assert t["pairs_lm"] == 2 and t["entry_type"] == "ema15" and t["flags"]["pairs_lm2"] is True and t["fits_v3_entry"] is True
    assert "pairs_lm" in t["filled"]


def test_unbroken_pair_is_not_called_the_strongest(monkeypatch, tmp_path):
    b5 = world()
    b5["EURJPY"], b5["GBPJPY"] = bars(BASE["EURJPY"]), bars(BASE["GBPJPY"], {"15:00": (-6, -6, -40, -40)})      # ユーロポンドは上・ユーロ円はまだ線の内側
    r = run(b5=b5, pair="EURJPY")
    assert r["strong_state"] is True and r["line"] is None
    assert no_strong(monkeypatch, tmp_path, b5=b5, pair="EURJPY") == 0
    t = T.load()["trades"][0]
    assert t["flags"]["strongest"] is None and t["strong_flow"] is None and t["strong_far"] is None


def test_unbroken_day_fills_neither_count_nor_strong(monkeypatch, tmp_path):
    b5 = {p: bars(BASE[p]) for p in F.PAIRS}
    assert no_strong(monkeypatch, tmp_path, b5=b5, b1={p: ones(p, px=-6.0) for p in F.PAIRS}) == 0
    t = T.load()["trades"][0]
    assert t["pairs_lm"] is None and t["strong_flow"] is None and t["flags"]["strongest"] is None and "pairs_lm" not in t["filled"]
