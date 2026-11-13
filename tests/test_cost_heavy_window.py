# -*- coding: utf-8 -*-
"""費用が重い時間の印（💸費用重）のテスト。2026-11-14 新設（オーナー「印を付けて」）。

NY 17時台（日本時間 夏6時台・冬7時台）はスプレッドがふだんの3〜10倍。その直前15分から印を付ける。表示だけ。
アメリカの夏時間の切り替わり（2026年は3/8〜11/1）で、日本時間の時刻が6時と7時で入れ替わることを確かめる。

実行:  python tests/test_cost_heavy_window.py     （pytest 不要。pytest でも動く）
"""
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import generate_technical_alerts as G  # noqa: E402


def _utc(*a):
    return datetime(*a, tzinfo=timezone.utc)


def test_summer_ny17_is_jst6():
    r = G.cost_heavy_window(_utc(2026, 7, 15, 21, 0))      # NY 17:00（夏）＝日本時間 6:00
    assert r is not None
    assert r[0] == " 💸費用重"
    assert "日本時間 6時台" in r[1] and "次の 7時台" in r[1]


def test_winter_ny17_is_jst7():
    r = G.cost_heavy_window(_utc(2026, 1, 15, 22, 0))      # NY 17:00（冬）＝日本時間 7:00
    assert r is not None and "日本時間 7時台" in r[1] and "次の 8時台" in r[1]


def test_15_minutes_before_is_marked():
    assert G.cost_heavy_window(_utc(2026, 7, 15, 20, 45)) is not None   # NY 16:45
    assert G.cost_heavy_window(_utc(2026, 7, 15, 20, 44)) is None       # NY 16:44
    r = G.cost_heavy_window(_utc(2026, 1, 15, 21, 59))                  # 冬 NY 16:59＝日本時間 6:59
    assert r is not None and "日本時間 7時台" in r[1]                     # 重いのは7時台と書く


def test_after_ny18_not_marked():
    assert G.cost_heavy_window(_utc(2026, 7, 15, 21, 59)) is not None   # NY 17:59
    assert G.cost_heavy_window(_utc(2026, 7, 15, 22, 0)) is None        # NY 18:00
    assert G.cost_heavy_window(_utc(2026, 7, 15, 3, 0)) is None         # 日本時間 12:00


def test_us_dst_weeks_follow_new_york():
    # アメリカだけ夏時間の週（2026-03-08〜03-29）・アメリカだけ冬時間の週（2026-11-01〜）
    assert "日本時間 6時台" in G.cost_heavy_window(_utc(2026, 3, 10, 21, 0))[1]
    assert G.cost_heavy_window(_utc(2026, 3, 10, 22, 0)) is None
    assert "日本時間 7時台" in G.cost_heavy_window(_utc(2026, 11, 3, 22, 0))[1]
    assert G.cost_heavy_window(_utc(2026, 11, 3, 21, 0)) is None


def test_jst_input_gives_same_answer():
    jst_now = _utc(2026, 7, 15, 21, 10).astimezone(G.JST)                # 日本時間 6:10 として渡す
    assert G.cost_heavy_window(jst_now) is not None


if __name__ == "__main__":
    n = 0
    for k, f in list(globals().items()):
        if k.startswith("test_") and callable(f):
            f(); n += 1
    print(f"OK {n} tests")
