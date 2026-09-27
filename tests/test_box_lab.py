# -*- coding: utf-8 -*-
"""S1 時間帯の箱の抜け（box_lab.py）のテスト。2026-09-27 新設。

値動きはすべて作り物（ネットワークに出ない）。確かめること＝①夏時間・冬時間の時刻 ②出口の計算（損切り・利確・
同じ足は損切りが先・始値の飛び越え・時間切れ）③1日分の取引（箱・抜け・次の足の始値で入る・費用・向きを逆にした偽薬の値）
④偽薬の p と幅と判定 ⑤事前登録と定数の一致。

実行:  python tests/test_box_lab.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import box_lab as B  # noqa: E402


def test_prereg_numbers_match_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    sec = text[text.index("## S1 時間帯の箱の抜け"):text.index("## 共通の決まり")]
    for s in ("00:00〜06:00 に始まる7本", "箱の足が6本未満の日も数えない", "07:00〜11:00 に始まる足", "08:00〜10:00 に始まる足",
              "ロンドン時間 16:00", "ニューヨーク時間 16:00", "0.8pips", "1.2pips", "1.5", "2,000回", "p＜0.05÷2", "件数300未満",
              "同じ足で損切りと利確の両方に触れたら、損切りが先"):
        assert s in sec, s
    assert list(B.BOX_HOURS) == list(range(0, 7)) and B.BOX_MIN_BARS == 6
    assert list(B.WINDOWS["L"]["hours"]) == [7, 8, 9, 10, 11] and list(B.WINDOWS["N"]["hours"]) == [8, 9, 10]
    assert B.WINDOWS["L"]["exit_hour"] == 16 and B.WINDOWS["N"]["exit_hour"] == 16
    assert B.COST_PIPS == {"JPY": 0.8, "other": 1.2} and B.COST_MULT == 1.5
    assert B.N_PERM == 2000 and B.N_BOOT == 2000 and B.MIN_N == 300 and abs(B.ALPHA - 0.025) < 1e-12
    assert len(B.PAIRS) == 9


def test_local_time_follows_summer_time():
    # 夏：ロンドン 00:00 = UTC 前日 23:00／NY 08:00 = UTC 12:00（日本時間 21:00）
    assert B.local_ts(dt.date(2026, 7, 1), 0, B.LON) == pd.Timestamp("2026-06-30 23:00", tz="UTC")
    assert B.local_ts(dt.date(2026, 7, 1), 8, B.NY) == pd.Timestamp("2026-07-01 12:00", tz="UTC")
    # 冬：ロンドン 00:00 = UTC 00:00（日本時間 9:00）／NY 08:00 = UTC 13:00（日本時間 22:00）
    assert B.local_ts(dt.date(2026, 1, 14), 0, B.LON) == pd.Timestamp("2026-01-14 00:00", tz="UTC")
    assert B.local_ts(dt.date(2026, 1, 14), 8, B.NY) == pd.Timestamp("2026-01-14 13:00", tz="UTC")


def _arr(rows):
    a = np.array(rows, float)
    return a[:, 0], a[:, 1], a[:, 2], a[:, 3]


def test_simulate_exits():
    # 買い・入る値 100・損切りまで 1・利確まで 2
    o, h, lo, c = _arr([(100, 100.5, 99.5, 100.2), (100.2, 102.1, 100.1, 101.9)])
    assert B.simulate(o, h, lo, c, 0, 2, 100.0, 1, 1.0, 2.0, 999) == (2.0, "利確")
    # 同じ足で両方に触れたら損切りが先
    o, h, lo, c = _arr([(100, 102.5, 98.5, 100)])
    assert B.simulate(o, h, lo, c, 0, 1, 100.0, 1, 1.0, 2.0, 999) == (-1.0, "損切り")
    # 次の足の始値が損切りより先に飛んでいたら、その始値で手じまう（-1 より悪い）
    o, h, lo, c = _arr([(100, 100.2, 99.8, 99.9), (98.5, 98.9, 98.0, 98.2)])
    r, kind = B.simulate(o, h, lo, c, 0, 2, 100.0, 1, 1.0, 2.0, 999)
    assert kind == "損切り" and abs(r - (-1.5)) < 1e-12
    # 決まらなければ時間切れの値で
    o, h, lo, c = _arr([(100, 100.4, 99.7, 100.1), (100.1, 100.6, 99.9, 100.3)])
    r, kind = B.simulate(o, h, lo, c, 0, 2, 100.0, 1, 1.0, 2.0, 100.5)
    assert kind == "時間切れ" and abs(r - 0.5) < 1e-12
    # 売りは向きが逆
    o, h, lo, c = _arr([(100, 100.2, 97.9, 98.0)])
    assert B.simulate(o, h, lo, c, 0, 1, 100.0, -1, 1.0, 2.0, 999) == (2.0, "利確")


def _day_bars():
    """冬の水曜（2026-01-14）の UTC の1時間足。ロンドン＝UTC。
    箱（00〜06時）＝高値 150.50・安値 150.00。07時の足の終値 150.60 で上に抜け → 08時の始値 150.60 で買い。
    損切り 150.00（1R＝0.60）・利確 150.60＋0.50＝151.10。10時の足の高値 151.20 で利確。
    そのあとは NY の箱（00〜12時・高値 151.20）の中で終わる＝窓N は取引なし"""
    idx = pd.date_range("2026-01-13 20:00", "2026-01-15 02:00", freq="1h", tz="UTC")
    rows = []
    for t in idx:
        hr = t.hour if t.date() == dt.date(2026, 1, 14) else -1
        if 0 <= hr <= 6:
            rows.append((150.25, 150.50, 150.00, 150.25))
        elif hr == 7:
            rows.append((150.40, 150.65, 150.35, 150.60))
        elif hr == 8:
            rows.append((150.60, 150.80, 150.55, 150.75))
        elif hr == 9:
            rows.append((150.75, 150.95, 150.70, 150.90))
        elif hr == 10:
            rows.append((150.90, 151.20, 150.85, 151.00))
        elif hr >= 11:
            rows.append((150.80, 150.90, 150.70, 150.80))
        else:
            rows.append((150.25, 150.30, 150.20, 150.25))
    return pd.DataFrame(rows, index=idx, columns=["Open", "High", "Low", "Close"])


def test_one_day_trade():
    bars = _day_bars()
    pos = {t: i for i, t in enumerate(bars.index)}
    got, why = B.day_trades(bars, "USDJPY=X", dt.date(2026, 1, 14), pos)
    assert why is None and len(got) == 1
    t = got[0]
    assert t["window"] == "L" and t["dir"] == 1 and t["exit"] == "利確"
    assert t["entry_utc"].startswith("2026-01-14T08:00")
    assert abs(t["gross"] - 0.50 / 0.60) < 1e-9
    cost = 0.8 * 1.5 * 0.01 / 0.60
    assert abs(t["cost_r"] - cost) < 1e-9 and abs(t["net"] - (0.50 / 0.60 - cost)) < 1e-9
    # 向きを逆にした偽薬の値：売り・損切り 151.20（1R 上）→ 10時の高値 151.20 で損切り
    assert abs(t["mirror_net"] - (-1.0 - cost)) < 1e-9
    assert abs(t["width_pips"] - 50) < 1e-6


def test_short_box_day_is_skipped():
    bars = _day_bars()
    drop = [pd.Timestamp(f"2026-01-14 0{h}:00", tz="UTC") for h in (1, 2)]
    bars = bars.drop(drop)
    pos = {t: i for i, t in enumerate(bars.index)}
    got, why = B.day_trades(bars, "USDJPY=X", dt.date(2026, 1, 14), pos)
    assert got == [] and why == "箱の足が足りない"


def test_placebo_ci_and_judge():
    real = np.full(400, 0.3)
    mirror = np.full(400, -0.3)
    p, pm = B.placebo_p(real, mirror)
    assert p < 0.01 and abs(pm) < 0.05
    p2, _ = B.placebo_p(real, real)
    assert p2 > 0.5
    lo, hi = B.boot_ci([0.2] * 10, [f"d{i % 5}" for i in range(10)])
    assert abs(lo - 0.2) < 1e-12 and abs(hi - 0.2) < 1e-12
    ok = {"n": 400, "lo": 0.01, "hi": 0.2, "early": 0.1, "late": 0.05, "p": 0.01}
    assert B.judge(ok) == "過去2年では残る"
    assert B.judge({**ok, "p": 0.03}) == "差なし"
    assert B.judge({**ok, "late": -0.01}) == "差なし"
    assert B.judge({**ok, "n": 299}) == "件数不足"
    bad = {"n": 400, "lo": -0.3, "hi": -0.01, "early": -0.1, "late": -0.2, "p": 0.001}
    assert B.judge(bad) == "逆に効く（だましが多い）"


def test_window_stats_and_render():
    rows = []
    for i in range(40):
        d = (dt.date(2026, 1, 5) + dt.timedelta(days=i)).isoformat()
        for tk in ("USDJPY=X", "EURAUD=X"):
            rows.append({"window": "L", "ticker": tk, "date": d, "weekday": i % 5, "dir": 1 if i % 2 else -1,
                         "gross": 0.1, "net": 0.05, "mirror_net": -0.05, "cost_r": 0.05,
                         "net_official": 0.09 if tk == "USDJPY=X" else None, "exit": "利確", "width_pips": 20 + i,
                         "entry_utc": d})
    res = B.window_stats(rows, {"2026-01-06"}, "2026-01-01")
    assert res["n"] == 80 and res["verdict"] == "件数不足" and res["net_official"]["n"] == 40
    assert res["by_event"]["ある日"]["n"] == 2
    out = {"generated_jst": "x", "prereg_sha256": "ab" * 32, "missing": [],
           "windows": {"L": res, "N": {"n": 0, "verdict": "件数不足"}}}
    md = B.render_md(out)
    assert "S1 時間帯の箱の抜けの結果" in md and "投資助言ではありません" in md


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"ok   {name}")
            except Exception as e:  # noqa: BLE001
                fails += 1
                print(f"FAIL {name}: {type(e).__name__}: {e}")
    print("全部通過" if not fails else f"{fails} 件失敗")
    sys.exit(1 if fails else 0)
