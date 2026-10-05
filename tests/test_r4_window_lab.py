# -*- coding: utf-8 -*-
"""R4 腕B・腕C（r4_window_lab.py）のテスト。作った足で、時刻の直し方・窓の値・日の選び方・向き・費用・判定・CSV の読み方を確かめる。
2026-10-05 新設。

実行:  python tests/test_r4_window_lab.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import io
import lzma
import os
import struct
import sys
import tempfile

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import r4_window_lab as W  # noqa: E402


def _close(a, b, tol=1e-9):
    return abs(a - b) <= tol * max(1.0, abs(b))


def _bars(rows):
    """[(UTC の時刻の文字列, 始値, 取引量, スプレッド)] → 足"""
    idx = pd.DatetimeIndex([pd.Timestamp(t, tz="UTC") for t, *_ in rows])
    return pd.DataFrame({"open": [r[1] for r in rows], "vol": [r[2] for r in rows], "spread": [r[3] for r in rows]}, index=idx)


def test_server_time_to_london():
    t = pd.to_datetime(["2024-07-01 10:00", "2024-01-15 10:00", "2024-03-12 11:00"])
    lon = W.server_to_utc(t).tz_convert(W.LON)
    assert [x.hour for x in lon] == [8, 8, 8], lon       # 夏・冬・米国だけ夏時間の週（サーバー11時＝ロンドン8時）


def test_windows_pick_first_bar_with_volume_in_london_hours():
    # 2024-07-01（英国は夏時間）：ロンドン 08:00＝UTC 07:00、16:00＝UTC 15:00
    b = _bars([("2024-07-01 06:55", 1.0, 5, 0.1), ("2024-07-01 07:00", 1.10, 0, 0.1), ("2024-07-01 07:05", 1.11, 3, 0.2),
               ("2024-07-01 15:00", 1.20, 4, 0.3), ("2024-07-01 15:05", 1.21, 4, 0.3),
               ("2024-07-02 07:00", 1.30, 4, 0.1)])                                  # 2日は16時台が無い
    w = W.windows_from_bars(b)
    assert w == {dt.date(2024, 7, 1): (1.11, 0.2, 1.20, 0.3)}, w
    # 冬：ロンドン 08:00＝UTC 08:00
    w2 = W.windows_from_bars(_bars([("2024-01-15 08:00", 2.0, 1, 0), ("2024-01-15 16:00", 2.1, 1, 0)]))
    assert w2 == {dt.date(2024, 1, 15): (2.0, 0.0, 2.1, 0.0)}


def test_pick_day_skips_days_without_data():
    have = {dt.date(2024, 5, 30), dt.date(2024, 5, 15), dt.date(2024, 5, 16)}
    fn = lambda pair, d: (1, 0, 1, 0) if d in have else None                         # noqa: E731
    assert W.pick_day(fn, "EURUSD=X", 2024, 5, "last", dt.date(2024, 12, 31)) == dt.date(2024, 5, 30)   # 31日（金）は無い
    assert W.pick_day(fn, "EURUSD=X", 2024, 5, "mid", dt.date(2024, 12, 31)) == dt.date(2024, 5, 15)
    assert W.pick_day(fn, "EURUSD=X", 2024, 6, "last", dt.date(2024, 12, 31)) is None


def _equities(f_up, us_up):
    d = pd.bdate_range("2024-04-25", "2024-06-10")
    out = {W.US: pd.Series(np.where(d >= pd.Timestamp("2024-05-01"), 100 * (1 + us_up), 100.0), index=d)}
    for p, (eq, _) in W.PAIRS.items():
        out[eq] = pd.Series(np.where(d >= pd.Timestamp("2024-05-01"), 100 * (1 + f_up), 100.0), index=d)
    return out


def test_direction_sells_currency_of_rising_stock_market():
    eq = _equities(0.05, 0.01)                                  # 外国の株が米国より上がった＝外国の通貨を売る
    win = (1.1000, 0.0, 1.0989, 0.0)                            # 値が下がる
    t = W.trade("EURUSD=X", dt.date(2024, 5, 31), win, eq, "dukascopy")
    assert t["gross"] > 0 and _close(t["gross"], -(1.0989 / 1.1 - 1))               # ユーロドルは売り
    t2 = W.trade("USDJPY=X", dt.date(2024, 5, 31), (150.0, 0.0, 150.3, 0.0), eq, "dukascopy")
    assert t2["gross"] > 0                                                           # 円を売る＝ドル円の買い
    assert _close(t2["net"], t2["gross"] - W.cost_price("USDJPY=X") / 150.0)
    eq_down = _equities(-0.02, 0.01)
    t3 = W.trade("EURUSD=X", dt.date(2024, 5, 31), win, eq_down, "dukascopy")
    assert t3["gross"] < 0                                                           # 逆向き（ユーロ買い）
    assert W.trade("EURUSD=X", dt.date(2024, 5, 31), win, _equities(0.01, 0.01), "dukascopy") is None   # 差0は入らない


def test_mt5_cost_is_half_spread_at_entry_and_exit():
    eq = _equities(0.05, 0.01)
    t = W.trade("EURUSD=X", dt.date(2024, 5, 31), (1.1000, 0.0002, 1.0990, 0.0004), eq, "mt5")
    me, mx = 1.1001, 1.0992
    assert _close(t["gross"], -(mx / me - 1)) and _close(t["cost"], 0.0003 / me)
    assert _close(t["net"], t["gross"] - t["cost"]) and _close(t["spread_pips"], 3.0)


def _rows(month_vals, rule_val):
    rows = []
    for k, (y, m) in enumerate(month_vals):
        for p in W.PAIRS:
            v = rule_val(k, p)
            rows.append({"month": f"{y}-{m:02d}", "day": f"{y}-{m:02d}-28", "pair": p, "raw": v, "gross": v, "net": v})
    return rows


def test_stats_and_judge():
    months = [(2015 + i // 12, i % 12 + 1) for i in range(120)]
    rng = np.random.default_rng(0)
    noise = rng.normal(0, 0.0005, (120, 4))
    end = _rows(months, lambda k, p: 0.002 + noise[k, list(W.PAIRS).index(p)])
    mid = _rows(months, lambda k, p: 0.0 + noise[(k + 7) % 120, list(W.PAIRS).index(p)])
    st = W.stats(end, mid, np.random.default_rng(1))
    assert st["verdict"] == W.VERDICTS[0] and st["p_diff"] < W.ALPHA and st["lo"] > 0, st
    st2 = W.stats(end, end, np.random.default_rng(1))                               # 真ん中も同じだけプラス
    assert st2["verdict"] == W.VERDICTS[1]
    neg = _rows(months, lambda k, p: -0.001 + noise[k, list(W.PAIRS).index(p)])
    assert W.stats(neg, mid, np.random.default_rng(1))["verdict"] == W.VERDICTS[2]


def test_collect_skips_month_cut_by_export_end():
    have = lambda pair, d: (1.0, 0.0, 1.0, 0.0)                                      # noqa: E731
    eq = {W.US: pd.Series(100.0, index=pd.bdate_range("2026-06-01", "2026-10-01"))}
    for p, (e, _) in W.PAIRS.items():
        eq[e] = pd.Series(np.linspace(100, 110, len(eq[W.US])), index=eq[W.US].index)
    end_rows, mid_rows, cover = W.collect(have, eq, "2026-08-01", "2026-09-24", "mt5")
    assert {r["month"] for r in end_rows} == {"2026-08"} and all(c["months"] == 1 for c in cover.values())
    assert {r["day"] for r in end_rows} == {"2026-08-31"} and {r["day"] for r in mid_rows} == {"2026-08-17"}


def _duka_bytes(rows, scale):
    raw = b"".join(struct.pack(">IIIIIf", t, round(o / scale), round(o / scale), round(o / scale), round(o / scale), v)
                   for t, o, v in rows)
    return lzma.compress(raw, format=lzma.FORMAT_ALONE)


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_dukascopy_parse_and_fetch():
    # 2024-01-15（冬）：ロンドン 08:00＝UTC 08:00（28800秒）、16:00＝57600秒
    body = _duka_bytes([(28740, 150.0, 1.0), (28800, 150.123, 0.0), (28860, 150.125, 2.0), (57600, 150.5, 1.0)], 0.001)
    seen = []

    def opener(req):
        seen.append(req.full_url)
        return _Resp(body)
    d = W.Duka(opener=opener, pause=0, wait=lambda s: None)
    w = d.window("USDJPY=X", dt.date(2024, 1, 15))
    assert seen[0].endswith("/USDJPY/2024/00/15/BID_candles_min_1.bi5")                 # 月は0から数える
    assert _close(w[0], 150.125) and _close(w[2], 150.5) and w[1] == 0.0               # 取引量0の足はとばす
    d.window("USDJPY=X", dt.date(2024, 1, 15))
    assert len(seen) == 1                                                             # 覚えておく
    e = W.parse_duka(lzma.decompress(_duka_bytes([(28800, 1.08765, 1.0)], 0.00001)), dt.date(2024, 1, 15), "EURUSD=X")
    assert _close(float(e["open"].iloc[0]), 1.08765)


def test_dukascopy_retries_when_busy():
    import urllib.error
    body = _duka_bytes([(28800, 1.1, 1.0), (57600, 1.2, 1.0)], 0.00001)
    calls, waits = [], []

    def opener(req):
        calls.append(1)
        if len(calls) < 3:
            raise urllib.error.HTTPError(req.full_url, 503, "busy", {}, None)
        return _Resp(body)
    d = W.Duka(opener=opener, wait=waits.append)
    w = d.window("EURUSD=X", dt.date(2024, 1, 15))
    assert _close(w[0], 1.1) and _close(w[2], 1.2), w
    assert waits[:2] == [5, 15] and not d.errors                                       # 混雑は長めに待って取り直す
    gone = W.Duka(opener=lambda req: (_ for _ in ()).throw(urllib.error.HTTPError(req.full_url, 404, "x", {}, None)), wait=waits.append)
    assert gone.window("EURUSD=X", dt.date(2024, 1, 13)) is None and not gone.errors   # 404＝データの無い日（失敗ではない）
    bad = W.Duka(opener=lambda req: (_ for _ in ()).throw(urllib.error.HTTPError(req.full_url, 503, "x", {}, None)), tries=2, wait=lambda s: None)
    assert bad.window("EURUSD=X", dt.date(2024, 1, 15)) is None and len(bad.errors) == 1


def test_first_candidates_and_disk_cache():
    keys = W.first_candidates("2026-08-01", "2026-09-24")
    assert ("EURUSD=X", dt.date(2026, 8, 31)) in keys and ("EURUSD=X", dt.date(2026, 8, 17)) in keys
    assert all(k[1].month == 8 for k in keys) and len(keys) == 8                         # 9月は書き出しの途中で終わる＝数えない
    body = _duka_bytes([(28800, 1.1, 1.0), (57600, 1.2, 1.0)], 0.00001)
    seen = []
    with tempfile.TemporaryDirectory() as tmp:
        d = W.Duka(opener=lambda req: (seen.append(req.full_url), _Resp(body))[1], wait=lambda s: None, cache_dir=tmp)
        n_err, n = W.fetch_only("EURUSD=X", "2024-01-01", "2024-01-31", tmp, end="2024-12-31", duka=d)
        assert (n_err, n) == (0, 2) and len(os.listdir(tmp)) == 2                         # 冬の月末（1/31）と真ん中（1/15）
        d2 = W.Duka(opener=lambda req: 1 / 0, wait=lambda s: None, cache_dir=tmp)       # 2回目は置き場から読むだけ
        w = d2.window("EURUSD=X", dt.date(2024, 1, 31))
        assert d2.from_disk == 1 and d2.fetched == 0 and _close(w[0], 1.1)
        import urllib.error
        d3 = W.Duka(opener=lambda req: (_ for _ in ()).throw(urllib.error.HTTPError(req.full_url, 404, "x", {}, None)),
                    wait=lambda s: None, cache_dir=tmp)
        assert d3.window("EURUSD=X", dt.date(2024, 1, 25)) is None
        assert os.path.getsize(os.path.join(tmp, "EURUSD_2024-01-25.bi5")) == 0            # データの無い日も覚える


def test_read_mt5_csv_variants():
    rows = ["2024.01.15 10:00,150.100,150.2,150.0,150.15,12,5,9", "2024.01.15 10:05,150.15,150.3,150.1,150.2,0,6,8"]
    with tempfile.TemporaryDirectory() as tmp:
        p1 = os.path.join(tmp, "a.csv")
        with open(p1, "w", encoding="utf-8") as f:
            f.write("\n".join(rows) + "\n")
        p2 = os.path.join(tmp, "b.csv")
        with open(p2, "w", encoding="utf-16") as f:
            f.write("time\topen\thigh\tlow\tclose\ttickvol\tspread_open\tspread_max\n" + "\n".join(r.replace(",", "\t") for r in rows) + "\n")
        for p in (p1, p2):
            df = W.read_mt5_csv(p)
            assert len(df) == 2 and df["time"].iloc[0] == pd.Timestamp("2024-01-15 10:00")
            assert _close(df["open"].iloc[0], 150.1) and df["vol"].tolist() == [12, 0] and df["spread_pt"].tolist() == [5, 6]
        b = W.mt5_bars(W.read_mt5_csv(p1), "USDJPY=X")
        w = W.windows_from_bars(pd.concat([b, _bars([("2024-01-15 16:00", 150.4, 3, 0.004)])]))
        assert w == {dt.date(2024, 1, 15): (150.1, 0.005, 150.4, 0.004)}                 # サーバー10時＝ロンドン8時・5ポイント＝0.005円


def test_build_roles_and_stop():
    months = [(2023, m) for m in range(1, 13)]
    end = _rows(months, lambda k, p: -0.001)
    mid = _rows(months, lambda k, p: 0.0)
    cover = {p: {"months": 12, "both": 12, "share": 1.0} for p in W.PAIRS}
    out = W.build("dukascopy", end, mid, cover, [], "判定", np.random.default_rng(0), "2026-10-05")
    assert out["data_ok"] and out["verdicts"]["R4C"]["status"] == "stop" and out["kind"] == "backtest"
    rd = W.build("mt5", end, mid, cover, [], "読むための数字（腕C が判定）", np.random.default_rng(0), "2026-10-05")
    assert rd["titles"] == {} and rd["kind"] == "reading" and rd["verdicts"] == {}
    low = {p: {"months": 12, "both": 10, "share": 10 / 12} for p in W.PAIRS}
    bad = W.build("dukascopy", end, mid, low, [], "判定", np.random.default_rng(0), "2026-10-05")
    assert not bad["data_ok"] and bad["failed"] and "result" not in bad
    big = _rows(months, lambda k, p: 0.09)
    assert any("8%" in x for x in W.build("dukascopy", big, mid, cover, [], "判定", np.random.default_rng(0), "2026-10-05")["failed"])


def test_constants_match_preregistration():
    txt = open(os.path.join(ROOT, "PILLAR_PREREG.md"), encoding="utf-8").read()
    sec = txt.split("**R4 腕B の補足と腕C", 1)[1].split("\n## ", 1)[0]
    assert "2022-06-01〜2026-09-24" in sec and W.PERIOD["mt5"] == ("2022-06-01", "2026-09-24")
    assert "2015-01〜2026-09" in sec and W.PERIOD["dukascopy"] == ("2015-01-01", "2026-09-30")
    assert "95%以上" in sec and W.COVER == 0.95
    assert "8%を超えて" in sec and W.MAX_MOVE == 0.08
    assert "0.1〜5pips" in sec and W.SPREAD_PIPS_OK == (0.1, 5.0)
    assert "10,000回" in sec and W.N_BOOT == 10000
    assert "ニューヨーク時間＋7時間" in sec and W.SERVER_SHIFT_H == 7
    assert "円のペア 0.001・ほか 0.00001" in sec and W.point("USDJPY=X") == 0.001 and W.point("EURUSD=X") == 0.00001
    assert "`box_lab.cost_price`" in sec
    for v in W.VERDICTS:
        assert v.replace("◎ ", "") in sec
    armb = txt.split("**R4 腕B（2026-10-05 登録", 1)[1].split("**R4 腕B の補足", 1)[0]
    assert "片側 p＜0.05" in armb and W.ALPHA == 0.05 and "08:00" in armb and "16:00" in armb
    assert (W.ENTRY_H, W.EXIT_H) == (8, 16)


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
