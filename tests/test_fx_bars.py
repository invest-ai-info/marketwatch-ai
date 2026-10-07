# -*- coding: utf-8 -*-
"""為替の値段の置き場（fx_bars.py）のテスト。作ったファイルで、読み取り・点検・取得の手順・重ね方を確かめる（ネットにはつながない）。
2026-10-07 新設。

実行:  python tests/test_fx_bars.py     （pytest 不要。pytest でも動く）
"""
import io
import lzma
import os
import sys
import tempfile
import urllib.error

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import fx_bars as F  # noqa: E402


def _month_bytes(pair, y, m, price, spread_pts=0, hours=None, vol=1.0):
    """1か月の1時間足（月の初めからの秒・始・終・安・高・取引量）を Dukascopy と同じ並びで作る"""
    k = F.point(pair)
    n = hours if hours is not None else 24 * 3
    a = np.zeros(n, dtype=F.REC)
    a["t"] = np.arange(n) * 3600
    base = int(round(price / k)) + spread_pts
    a["o"] = base
    a["c"] = base + 5
    a["l"] = base - 10
    a["h"] = base + 10
    a["v"] = vol
    return a.tobytes()


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_parse_times_and_units():
    df = F.parse(_month_bytes("USDJPY", 2020, 3, 108.5), 2020, 3, "USDJPY")
    assert df.index[0] == pd.Timestamp("2020-03-01 00:00", tz="UTC") and df.index[1] == pd.Timestamp("2020-03-01 01:00", tz="UTC")
    assert abs(df["o"].iloc[0] - 108.5) < 1e-9 and abs(df["c"].iloc[0] - 108.505) < 1e-9          # 円のペア＝1/1000
    e = F.parse(_month_bytes("EURUSD", 2020, 3, 1.1), 2020, 3, "EURUSD")
    assert abs(e["c"].iloc[0] - 1.10005) < 1e-12                                                       # ほか＝1/100000
    assert F.parse(b"", 2020, 3, "EURUSD").empty
    try:
        F.parse(b"x" * 25, 2020, 3, "EURUSD")
        assert False, "24バイトの倍数でなければ止まる"
    except ValueError:
        pass


def test_check_month_catches_unit_and_time_errors():
    ok = F.parse(_month_bytes("USDJPY", 2020, 3, 108.5), 2020, 3, "USDJPY")
    assert F.check_month(ok, 2020, 3, "USDJPY") is None
    wrong_unit = F.parse(_month_bytes("EURUSD", 2020, 3, 108.5), 2020, 3, "USDJPY")                    # 1/100000 で作った値を 1/1000 で読む＝100倍
    assert "単位" in F.check_month(wrong_unit, 2020, 3, "USDJPY")
    shifted = ok.copy()
    shifted.index = shifted.index - pd.Timedelta(days=2)                                                 # 前の月にはみ出す
    assert "月の外" in F.check_month(shifted, 2020, 3, "USDJPY")


def test_months_tasks_and_shards():
    ms = F.months((2025, 11), (2026, 2))
    assert ms == [(2025, 11), (2025, 12), (2026, 1), (2026, 2)]
    assert F.last_full_month(pd.Timestamp("2026-10-07").date()) == (2026, 9)
    assert F.last_full_month(pd.Timestamp("2026-01-01").date()) == (2025, 12)
    t = F.tasks(("EURUSD", "USDJPY"), (2026, 1), (2026, 3))
    assert len(t) == 2 * 2 * 3
    parts = [F.shard(t, k, 5) for k in range(5)]
    assert sorted(x for p in parts for x in p) == sorted(t) and max(map(len, parts)) - min(map(len, parts)) <= 1


def test_fetch_skips_present_saves_new_marks_404_and_drops_bad():
    with tempfile.TemporaryDirectory() as d:
        have, new = os.path.join(d, "have"), os.path.join(d, "new")
        F.save(have, "USDJPY", "BID", 2020, 1, lzma.compress(_month_bytes("USDJPY", 2020, 1, 108)))      # すでにある月
        calls = []

        def opener(req):
            calls.append(req.full_url)
            if "/2020/01/" in req.full_url:                                                              # 2月（月-1＝01）＝無い月
                raise urllib.error.HTTPError(req.full_url, 404, "nf", None, None)
            if "/2020/02/" in req.full_url and "ASK" in req.full_url:                                    # 3月の買値＝単位がおかしい
                return _Resp(lzma.compress(_month_bytes("EURUSD", 2020, 3, 108)))                        # 100倍の値
            return _Resp(lzma.compress(_month_bytes("USDJPY", 2020, 3, 108)))
        f = F.Fetcher(opener=opener, wait=lambda s: None)
        items = F.tasks(("USDJPY",), (2020, 1), (2020, 3))
        st = F.fetch(items, have_root=have, new_root=new, fetcher=f, log=lambda s: None)
        assert not any("/2020/00/BID" in u for u in calls)                                               # ある月は取りに行かない
        assert st["todo"] == 5 and st["empty"] == 2 and st["bad"] == 1 and st["fetched"] == 2
        assert os.path.getsize(F.raw_path(new, "USDJPY", "BID", 2020, 2)) == 0                           # 無い月は空のファイル
        assert not os.path.exists(F.raw_path(new, "USDJPY", "ASK", 2020, 3))                             # 点検で落とした月は置かない


def test_fetch_retries_busy_and_gives_up_without_saving():
    n = {"k": 0}

    def opener(req):
        n["k"] += 1
        raise urllib.error.HTTPError(req.full_url, 503, "busy", None, None)
    with tempfile.TemporaryDirectory() as d:
        f = F.Fetcher(opener=opener, wait=lambda s: None, tries=3)
        st = F.fetch([("EURUSD", "BID", 2020, 1)], have_root=os.path.join(d, "h"), new_root=os.path.join(d, "n"), fetcher=f, log=lambda s: None)
        assert n["k"] == 3 and st["failed"] == 1
        assert not os.path.exists(F.raw_path(os.path.join(d, "n"), "EURUSD", "BID", 2020, 1))          # 次の実行で取り直す


def test_budget_stops_before_new_months():
    t = {"now": 0.0}

    def clock():
        t["now"] += 40.0                                                                                 # 1件ごとに40秒進む
        return t["now"]
    with tempfile.TemporaryDirectory() as d:
        f = F.Fetcher(opener=lambda req: _Resp(lzma.compress(_month_bytes("EURUSD", 2020, 1, 1.1))), wait=lambda s: None)
        st = F.fetch(F.tasks(("EURUSD",), (2020, 1), (2020, 6)), have_root=os.path.join(d, "h"), new_root=os.path.join(d, "n"),
                     fetcher=f, budget_min=1, clock=clock, log=lambda s: None)
        assert st["left"] > 0 and st["fetched"] + st["left"] == 12


def test_merge_and_load_join_bid_ask():
    with tempfile.TemporaryDirectory() as d:
        root, new = os.path.join(d, "fx-bars"), os.path.join(d, "fx-new")
        for (y, m) in ((2026, 8), (2026, 9)):
            F.save(new, "USDJPY", "BID", y, m, lzma.compress(_month_bytes("USDJPY", y, m, 147.0)))
            F.save(new, "USDJPY", "ASK", y, m, lzma.compress(_month_bytes("USDJPY", y, m, 147.0, spread_pts=8)))
        F.save(new, "EURUSD", "BID", 2026, 9, lzma.compress(_month_bytes("EURUSD", 2026, 9, 1.17)))     # 買値が無い
        n, cov = F.merge(new, root, today=pd.Timestamp("2026-10-07").date())
        assert n == 5 and cov["USDJPY/BID"]["have"] == 2 and "2026-07" in cov["USDJPY/BID"]["missing"]
        df = F.load("USDJPY", root=root, start=(2026, 8), end=(2026, 9))
        assert len(df) == 2 * 72 and list(df.columns[:5]) == ["bo", "bh", "bl", "bc", "v"]
        assert np.allclose((df["ac"] - df["bc"]) / F.pip("USDJPY"), 0.8)                                 # 8 ポイント＝0.8 pips
        assert F.load("EURUSD", root=root, start=(2026, 9), end=(2026, 9)).empty                       # 片側だけの月は使わない
        inf = F.info(root)
        assert inf["months"][1] == "2026-09" and inf["series"] == len(F.PAIRS) * 2


def test_load_drops_no_volume_hours():
    with tempfile.TemporaryDirectory() as d:
        for s in F.SIDES:
            F.save(d, "EURUSD", s, 2026, 9, lzma.compress(_month_bytes("EURUSD", 2026, 9, 1.17, vol=0.0)))
        assert F.load("EURUSD", root=d, start=(2026, 9), end=(2026, 9)).empty


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
        except Exception as e:  # noqa: BLE001
            fails += 1
            print(f"  💥 {name}: {type(e).__name__}: {e}")
    print(f"--- {len(tests) - fails}/{len(tests)} 合格 ---")
    sys.exit(1 if fails else 0)
