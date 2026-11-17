# -*- coding: utf-8 -*-
"""KT2（kata2_lab.py）のテスト。作った足だけで「一気（陽線2本で押し目）」の決まりどおりに動くかを見る。
KT1 の道具（kata1_lab.py）の本体が変わっていないことも見る"""
import datetime as dt
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import kata1_lab  # noqa: E402
import kata2_lab  # noqa: E402

K = kata2_lab.K
DAY = dt.date(2026, 11, 17)            # 冬（ロンドンの始まり＝日本時間 17:00・窓 16:00〜18:55）


def jst(h, m):
    return pd.Timestamp(dt.datetime(DAY.year, DAY.month, DAY.day, h, m), tz=K.JST).tz_convert("UTC")


def make(path, flat_after):
    """8:00〜19:30 の平らな5分足（線＝安値 99.90／高値 100.10）。path＝{(時, 分): (始, 高, 安, 終)}。最後の足のあとは flat_after で平ら"""
    bars = {}
    for p in K.PAIRS:
        idx = pd.date_range(jst(8, 0), jst(19, 30), freq="5min")
        df = pd.DataFrame({"open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0, "so": 0.01}, index=idx)
        df.loc[jst(8, 0), "low"] = 99.90
        df.loc[jst(8, 5), "high"] = 100.10
        last = max(path)
        for (h, m), v in path.items():
            df.loc[jst(h, m), ["open", "high", "low", "close"]] = list(v)
        for t in range(last[0] * 60 + last[1] + 5, 19 * 60 + 35, 5):
            df.loc[jst(t // 60, t % 60), ["open", "high", "low", "close"]] = [flat_after] * 4
        bars[p] = df
    D = K.panel(bars, "2026-11-16", "2026-11-17")
    abn = {p: {DAY: False} for p in K.PAIRS}
    E = {p: np.array([], dtype=np.int64) for p in K.PAIRS}
    return D, abn, E


def usd(r):
    ts = r["trades"]["B"]
    if not ts:
        return None
    qs = [q for q in ts[0]["positions"] if q["pair"] == "USDJPY"]
    return qs[0] if qs else None


SIG_SELL = (99.95, 99.95, 99.60, 99.62)          # 18:00 3つとも終値が線（99.90）の下＝合図・安値 99.60（線から 30 pips）


def test_prereg_section_and_names():
    assert K.OK.section_sha256(os.path.join(ROOT, K.PREREG), K.SECTION) is not None
    assert K.TAG == "KT2" and set(K.TITLES) == {"KT2-A", "KT2-B"}
    assert K.OUT_JSON == "kata2-lab.json"
    # KT1 の本体は変わらない
    assert kata1_lab.TAG == "KT1" and kata1_lab.SECTION.startswith("## KT1") and kata1_lab.OUT_JSON == "kata1-lab.json"
    assert kata1_lab.scan_entry is not kata2_lab.scan_entry


def test_one_way_drop_enters_like_kt1():
    """合図 → 新安値（陽線1本だけ）→ 50% に戻る＝一気＝入る"""
    path = {(18, 0): SIG_SELL, (18, 5): (99.62, 99.70, 99.55, 99.66), (18, 10): (99.66, 99.74, 99.64, 99.70)}
    D, abn, E = make(path, 99.70)
    q = usd(K.simulate(D, E, abn))
    assert q is not None and abs(q["price"] - 99.725) < 1e-9        # 線 99.90 と最安値 99.55 の真ん中


def test_push_then_new_low_is_skipped():
    """陽線2本（押し目）のあと、50% に届く前に最安値を更新＝見送り。KT1 なら入る"""
    path = {(18, 0): SIG_SELL,
            (18, 5): (99.62, 99.68, 99.61, 99.66),                   # 陽線1
            (18, 10): (99.66, 99.69, 99.65, 99.68),                  # 陽線2＝押し目（50%＝99.75 には届かない）
            (18, 15): (99.68, 99.68, 99.50, 99.52),                  # 最安値を更新 → 見送り
            (18, 20): (99.52, 99.80, 99.51, 99.78)}                  # KT1 ならここで 50%（99.70）に届いて入る
    D, abn, E = make(path, 99.78)
    assert usd(K.simulate(D, E, abn)) is None
    D1, abn1, E1 = make(path, 99.78)
    r1 = kata1_lab.simulate(D1, E1, abn1)
    q1 = [q for q in r1["trades"]["B"][0]["positions"] if q["pair"] == "USDJPY"][0]
    assert abs(q1["price"] - 99.70) < 1e-9


def test_single_up_bar_then_new_low_continues():
    """陽線1本だけのあとの安値の更新は一気のまま＝最安値と 50% をずらして入る"""
    path = {(18, 0): SIG_SELL,
            (18, 5): (99.62, 99.68, 99.61, 99.66),                   # 陽線1本
            (18, 10): (99.66, 99.67, 99.50, 99.52),                  # 陰線で最安値を更新（99.50）
            (18, 15): (99.52, 99.75, 99.51, 99.72)}                  # 50%＝99.70 に届く
    D, abn, E = make(path, 99.72)
    q = usd(K.simulate(D, E, abn))
    assert q is not None and abs(q["price"] - 99.70) < 1e-9 and abs(q["dist"] - 40) < 1e-6


def test_push_that_reaches_half_enters():
    """押し目（陽線2本）のまま 50% に届けば入る（押し目そのものが入る戻り）"""
    path = {(18, 0): SIG_SELL,
            (18, 5): (99.62, 99.70, 99.61, 99.69),                   # 陽線1（50%＝99.75 に届かない）
            (18, 10): (99.69, 99.76, 99.68, 99.75)}                  # 陽線2 の足で 50% に届く → 入る
    D, abn, E = make(path, 99.75)
    q = usd(K.simulate(D, E, abn))
    assert q is not None and abs(q["price"] - 99.75) < 1e-9


def test_push_then_half_without_new_low_enters():
    """押し目のあと、最安値を更新しないまま 30分以内に 50% に届けば入る"""
    path = {(18, 0): SIG_SELL,
            (18, 5): (99.62, 99.66, 99.61, 99.65),
            (18, 10): (99.65, 99.68, 99.64, 99.67),                  # 陽線2本＝押し目
            (18, 15): (99.67, 99.67, 99.62, 99.63),                  # 陰線・最安値（99.60）は割らない
            (18, 20): (99.63, 99.76, 99.62, 99.74)}                  # 50%＝99.75 に届く（最安値をつけた 18:00 から 20分）
    D, abn, E = make(path, 99.74)
    q = usd(K.simulate(D, E, abn))
    assert q is not None and abs(q["price"] - 99.75) < 1e-9


def test_buy_mirror_push_then_new_high_is_skipped():
    """買い（線＝高値 100.10）：陰線2本で押し目 → 最高値を更新＝見送り"""
    path = {(18, 0): (100.05, 100.40, 100.05, 100.38),              # 3つとも終値が線の上＝買いの合図・最高値 100.40
            (18, 5): (100.38, 100.39, 100.32, 100.34),               # 陰線1（50%＝100.25 に買値が届かない）
            (18, 10): (100.34, 100.35, 100.31, 100.32),              # 陰線2＝押し目
            (18, 15): (100.32, 100.50, 100.31, 100.48),              # 最高値を更新 → 見送り
            (18, 20): (100.48, 100.49, 100.20, 100.22)}              # KT1 なら 50%（100.30）で入る
    D, abn, E = make(path, 100.22)
    r = K.simulate(D, E, abn)
    assert r["signals"] and r["signals"][0]["s"] == 1
    assert usd(r) is None


def test_verdict_names_use_kt2():
    arms = {"A": {"verdict": "検定不能", "seen": {"n": 10, "mean": -1.0, "lo": -2.0, "hi": 0.1, "win": 0.4}},
            "B": {"verdict": "費用後マイナス", "seen": {"n": 20, "mean": -1.0, "lo": -2.0, "hi": -0.1, "win": 0.4}}}
    assert set(K.verdicts_of(arms, "2026-11-17")) == {"KT2-A", "KT2-B"}
