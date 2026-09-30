# -*- coding: utf-8 -*-
"""L1・L2 ロンドン時間のドルの流れ（london_lab.py）のテスト。2026-09-30 新設。

値動きはすべて作り物（ネットワークに出ない）。確かめること＝①事前登録と定数の一致（費用は S1 と同じ）
②ロンドンの現地時刻で入る・出る（英国の夏時間と冬時間で UTC の足が1時間ずれる）③土日と足の無い日は数えない
④費用後の損益（ベーシスポイント）と偽薬の向き ⑤判定の3つ ⑥オーナーの決まり（1000回以上でプラスと言い切れなければストップ）
⑦検証済みリストへのつなぎ ⑧ワークフローと SYNC禁忌。

実行:  python tests/test_london_lab.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import json
import os
import sys
import tempfile

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import box_lab as B  # noqa: E402
import london_lab as L  # noqa: E402
import verified_list as V  # noqa: E402


def _bars(days, price_of_utc_hour, gap=None):
    """days の各日 UTC 0〜23時の1時間足。Open＝price_of_utc_hour(日, UTCの時)。gap＝抜く (日, UTCの時)"""
    idx, op = [], []
    for d in days:
        for h in range(24):
            if gap and (d, h) in gap:
                continue
            idx.append(pd.Timestamp(dt.datetime(d.year, d.month, d.day, h), tz="UTC"))
            op.append(price_of_utc_hour(d, h))
    df = pd.DataFrame({"Open": op}, index=pd.DatetimeIndex(idx))
    df["High"], df["Low"], df["Close"] = df["Open"], df["Open"], df["Open"]
    return df


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "## L1・L2 ロンドン時間のドルの流れ" in text
    assert (L.MIN_N, L.ALPHA, L.GOAL) == (300, 0.05 / 2, 1000) and "件数300未満" in text and "p＜0.025" in text
    assert "**1000回以上**" in text and "`verified-list.md`（検証済みリスト）に自動で載せる" in text
    assert (L.WINDOWS["L1"]["start"], L.WINDOWS["L1"]["end"], L.WINDOWS["L2"]["start"], L.WINDOWS["L2"]["end"]) == (8, 12, 12, 16)
    assert "現地 08:00→12:00" in text and "現地 12:00→16:00" in text and "現地 16:00→20:00" in text
    assert L.WINDOWS["L1"]["pairs"] == {"EURUSD=X": -1, "GBPUSD=X": -1}
    assert L.WINDOWS["L2"]["pairs"] == {"EURUSD=X": -1, "GBPUSD=X": -1, "AUDUSD=X": -1, "USDJPY=X": +1}
    assert B.COST_PIPS == {"JPY": 0.8, "other": 1.2} and B.COST_MULT == 1.5 and "円のペア 0.8pips・ほか 1.2pips × 滑りの係数 1.5" in text


def test_london_local_time_in_summer_and_winter():
    summer, winter = dt.date(2026, 7, 1), dt.date(2026, 1, 14)            # 英国の夏時間（UTC+1）と冬時間（UTC+0）
    bars = _bars([summer, winter], lambda d, h: 1.0 + h / 1000)
    rows = L.trades_for(bars, "EURUSD=X", 8, 12, +1)
    got = {r["date"]: r for r in rows}
    # 夏：現地8時＝UTC7時・12時＝UTC11時／冬：現地8時＝UTC8時・12時＝UTC12時
    s, w = got[summer.isoformat()], got[winter.isoformat()]
    assert abs(s["gross"] - (1.011 - 1.007) / 1.007 * 1e4) < 1e-9
    assert abs(w["gross"] - (1.012 - 1.008) / 1.008 * 1e4) < 1e-9
    assert set(s["path"]) == {1, 2, 3, 4} and abs(s["path"][4] - s["gross"]) < 1e-9


def test_weekend_and_missing_bars_are_skipped_and_costs():
    sat, mon, tue = dt.date(2026, 7, 4), dt.date(2026, 7, 6), dt.date(2026, 7, 7)
    bars = _bars([sat, mon, tue], lambda d, h: 1.2, gap={(tue, 11)})       # 火曜は出る足（UTC11時）が無い
    rows = L.trades_for(bars, "GBPUSD=X", 8, 12, -1)
    assert [r["date"] for r in rows] == [mon.isoformat()]
    r = rows[0]
    cost = 1.2 * 1.5 * 0.0001 / 1.2 * 1e4                                   # 1.8pips を入った値で割った bp
    assert abs(r["cost"] - cost) < 1e-9 and abs(r["net"] - (-cost)) < 1e-9 and abs(r["mirror_net"] - (-cost)) < 1e-9
    assert abs(r["net_official"] - (-(1.0 * 0.0001 / 1.2 * 1e4))) < 1e-9  # 公式スプレッド（ポンドドル 1.0pips）
    jpy = L.trades_for(_bars([mon], lambda d, h: 150.0 + h * 0.01), "USDJPY=X", 12, 16, +1)[0]
    assert abs(jpy["cost"] - 0.8 * 1.5 * 0.01 / 150.11 * 1e4) < 1e-9        # 夏：現地12時＝UTC11時の始値 150.11


def _rows(n_days, per_day, mean, spread, start=dt.date(2024, 10, 1)):
    """作り物の取引。ばらつきは日ごとに +と− が交互（平均はちょうど mean）"""
    rows = []
    d = start
    k = 0
    while k < n_days:
        if d.weekday() < 5:
            for j in range(per_day):
                g = mean + spread * (1 if (k + j) % 2 == 0 else -1) * (1 + k % 3)
                rows.append({"ticker": list(L.PAIR_NAME)[j % 4], "date": d.isoformat(), "weekday": d.weekday(), "gross": g + 1.5,
                             "cost": 1.5, "net": g, "mirror_net": -g - 3.0, "net_official": g + 1.0,
                             "month_end": d == L.last_weekday(d), "dst_gap": L.dst_gap(d), "path": {1: g / 2, 4: g}})
            k += 1
        d += dt.timedelta(days=1)
    return rows


def test_verdicts_and_owner_rule():
    good = L.window_stats(_rows(400, 2, 3.0, 5.0))
    assert good["verdict"] == "過去2年では残る" and L.owner_rule(good, "2026-09-30") is None
    flat = L.window_stats(_rows(600, 2, 0.0, 5.0))
    assert flat["verdict"] == "差なし" and flat["n"] == 1200
    v = L.owner_rule(flat, "2026-09-30")
    assert v["status"] == "stop" and v["n"] == 1200 and abs(v["mean"] - flat["mean"] / 1e4) < 1e-15
    assert ("マイナス" in v["reason"]) == (flat["mean"] <= 0)
    small = L.window_stats(_rows(100, 2, 0.0, 5.0))
    assert small["verdict"] == "件数不足" and L.owner_rule(small, "x") is None
    bad = L.window_stats(_rows(400, 2, -3.0, 5.0))
    assert bad["verdict"] == "逆に効く"
    assert L.dst_gap(dt.date(2026, 3, 20)) and not L.dst_gap(dt.date(2026, 7, 1))   # 米国だけ夏時間の週
    assert L.last_weekday(dt.date(2026, 5, 10)) == dt.date(2026, 5, 29)             # 5/31 は日曜


def test_run_end_to_end_and_verified_list():
    days = [dt.date(2024, 10, 1) + dt.timedelta(days=i) for i in range(730)]
    rng = np.random.default_rng(3)
    bars = {}
    for tk, p0 in (("EURUSD=X", 1.1), ("GBPUSD=X", 1.3), ("AUDUSD=X", 0.66), ("USDJPY=X", 150.0)):
        walk = p0 * np.exp(np.cumsum(rng.standard_normal(len(days) * 24) * 0.0008))
        bars[tk] = _bars(days, lambda d, h, w=walk, d0=days[0]: float(w[(d - d0).days * 24 + h]))
    windows, af, verdicts = L.run(bars, "2026-09-30")
    assert windows["L1"]["n"] > 900 and windows["L2"]["n"] > 1800 and af["n"] > 1800
    assert set(windows["L2"]["by_pair"]) == set(L.WINDOWS["L2"]["pairs"])
    out = {"generated_jst": "x", "prereg_sha256": "a" * 64, "kind": "backtest", "goal": 1000, "missing": [],
           "titles": {k: w["name"] for k, w in L.WINDOWS.items()}, "verdicts": verdicts, "windows": windows, "after_fix": af}
    md = L.render_md(out)
    assert "投資助言ではありません" in md and "値決めのあと" in md
    d = tempfile.mkdtemp()
    p = os.path.join(d, "london-lab.json")
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(dict(out, verdicts={"L2": {"status": "stop", "decided_on": "2026-09-30", "n": 1900, "mean": -1e-5,
                                             "lo": -3e-5, "hi": 1e-5, "reason": "費用後の平均がマイナス"}}), fh, ensure_ascii=False)
    stop, plus, watching = V.collect([(p, "L1・L2", "")])
    assert [r["id"] for r in stop] == ["L2"] and not plus and not watching     # 過去の1回だけのものは観察中に並べない
    txt = V.render(stop, plus, watching, now="x")
    assert "| L2 |" in txt and "過去のデータで1回だけ数えたもの" in txt
    assert ("london-lab.json", "L1・L2 ロンドン時間のドルの流れ（過去2年・1回だけ数えた）", "") in V.SOURCES


def test_workflow_and_sync_forbidden():
    wf = open(".github/workflows/london-lab.yml", encoding="utf-8").read()
    line = [x for x in wf.splitlines() if "pip install" in x][0]
    assert all(p in line.split() for p in ("numpy", "pandas", "yfinance"))
    assert "python london_lab.py" in wf and "python verified_list.py" in wf and "london-lab.json london-lab.md verified-list.md" in wf
    assert "schedule:" not in wf
    import check_site_consistency as C
    assert {"london-lab.json", "london-lab.md", "verified-list.md"} <= set(C.SYNC_FORBIDDEN)


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
