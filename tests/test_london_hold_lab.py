# -*- coding: utf-8 -*-
"""L4 ロンドン時間に入って、長めに持つ（london_hold_lab.py）のテスト。2026-09-30 新設。

値動きはすべて作り物（ネットワークに出ない）。確かめること＝①事前登録と定数の一致
②通貨の強弱がサイトの calc_currency_strength と同じ数字になる（同じ作り物の値段をサイトの関数にも通して比べる）
③いちばん強い通貨を買い、いちばん弱い通貨を売るペアと向き ④ロンドンの現地時刻で入る・出る（金曜の1日持ちは月曜）
⑤判定とオーナーの決まり ⑥検証済みリスト・ワークフロー・SYNC禁忌。

実行:  python tests/test_london_hold_lab.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import generate_technical_alerts as G  # noqa: E402
import london_hold_lab as H  # noqa: E402
import verified_list as V  # noqa: E402

UTC = dt.timezone.utc


def _walks(days, seed=1):
    """10ペアの1時間足（UTC 0〜23時・土日なし）。値は乱数の歩み"""
    rng = np.random.default_rng(seed)
    idx = [pd.Timestamp(dt.datetime(d.year, d.month, d.day, h), tz="UTC") for d in days if d.weekday() < 5 for h in range(24)]
    out = {}
    for k, tk in enumerate(H.TRADE_PAIRS):
        p0 = 150.0 if tk.endswith("JPY=X") else 1.0 + 0.1 * k
        c = p0 * np.exp(np.cumsum(rng.standard_normal(len(idx)) * 0.001))
        df = pd.DataFrame({"Close": c}, index=pd.DatetimeIndex(idx))
        df["Open"] = df["Close"].shift(1).fillna(p0)
        df["High"], df["Low"] = df[["Open", "Close"]].max(axis=1), df[["Open", "Close"]].min(axis=1)
        out[tk] = df
    return out


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "## L4 ロンドン時間に入って、長めに持つ" in text and "`iloc[-24]`" in text
    assert (H.BACK, H.MIN_PAIRS, H.ENTRY_HOUR, H.MIN_N, H.GOAL) == (23, 7, 8, 300, 1000)
    assert abs(H.ALPHA - 0.05 / 3) < 1e-12 and "p＜0.0167" in text and "7ペア以上" in text
    assert H.STRENGTH_PAIRS == G.FX_PAIR_MAP and len(H.STRENGTH_PAIRS) == 9
    assert set(H.TRADE_PAIRS) == set(G.FX_PAIR_MAP) | {"EURGBP=X"} and "EURGBP=X" in text
    assert [(h["hours"], h["days"], h["cluster"]) for h in H.HOLDS.values()] == [(16, 0, "day"), (8, 1, "day"), (8, 5, "month")]
    assert "**スワップ（金利差）は入れない**" in text


def test_strength_matches_the_sites_function():
    days = [dt.date(2026, 7, 1) + dt.timedelta(days=i) for i in range(10)]
    bars = _walks(days, seed=5)
    t_last = pd.Timestamp(dt.datetime(2026, 7, 8, 6), tz="UTC")          # 7/8（水）ロンドン 07:00＝UTC 06:00 に始まる足
    series = {tk: ({t: i for i, t in enumerate(b.index)}, b["Close"].to_numpy(float)) for tk, b in bars.items()}
    mine = H.strength_at(series, t_last)

    def fake_download(ticker, period=None, interval=None, progress=False, auto_adjust=True):
        return bars[ticker].loc[:t_last, ["Close"]]                        # サイトの関数に「その時点までの足」を渡す

    real = G.yf.download
    G.yf.download = fake_download
    try:
        site = G.calc_currency_strength()
    finally:
        G.yf.download = real
    assert set(site) == set(mine)
    for c in site:
        assert abs(site[c] - mine[c]) < 2e-3, (c, site[c], mine[c])       # サイトは小数3桁で丸める


def test_pick_pair_and_weekdays():
    assert H.pick_pair({"USD": 0, "EUR": 0.1, "GBP": 0.5, "JPY": -0.4, "AUD": 0}) [:2] == ("GBPJPY=X", +1)
    assert H.pick_pair({"USD": 0, "EUR": 0.1, "GBP": -0.5, "JPY": 0.4, "AUD": 0})[:2] == ("GBPJPY=X", -1)
    tk, d, gap = H.pick_pair({"USD": 0, "EUR": 0.3, "GBP": -0.2, "JPY": 0.0, "AUD": 0.1})
    assert (tk, d) == ("EURGBP=X", +1) and abs(gap - 0.5) < 1e-12
    fri = dt.date(2026, 7, 3)
    assert H.nth_weekday(fri, 1) == dt.date(2026, 7, 6) and H.nth_weekday(fri, 5) == dt.date(2026, 7, 10)
    assert H.nth_weekday(fri, 0) == fri


def test_trades_use_london_times():
    days = [dt.date(2026, 6, 22) + dt.timedelta(days=i) for i in range(21)]  # 夏時間（ロンドン＝UTC+1）
    bars = _walks(days, seed=2)
    rows = H.build_trades(bars)
    assert rows["H8"] and rows["H24"] and rows["H120"]
    r = rows["H24"][0]
    d = dt.date.fromisoformat(r["date"])
    tk = r["ticker"]
    t0 = pd.Timestamp(dt.datetime(d.year, d.month, d.day, 7), tz="UTC")     # ロンドン 08:00＝UTC 07:00
    d1 = H.nth_weekday(d, 1)
    t1 = pd.Timestamp(dt.datetime(d1.year, d1.month, d1.day, 7), tz="UTC")
    e, x = float(bars[tk]["Open"][t0]), float(bars[tk]["Open"][t1])
    assert abs(r["gross"] - r["dir"] * (x - e) / e * 1e4) < 1e-9 and abs(r["net"] - (r["gross"] - r["cost"])) < 1e-12
    assert abs(r["mirror_net"] - (-r["gross"] - r["cost"])) < 1e-12
    fridays = [x for x in rows["H24"] if dt.date.fromisoformat(x["date"]).weekday() == 4]
    assert fridays                                                          # 金曜の1日持ち＝月曜に出る
    assert all(x["date"] <= days[-1].isoformat() for x in rows["H120"])
    assert len(rows["H120"]) < len(rows["H24"]) <= len(rows["H8"])          # 5日先の足が無い最後の週は数えない


def _rows(n_days, mean, spread):
    rows = []
    d = dt.date(2024, 10, 1)
    k = 0
    while k < n_days:
        if d.weekday() < 5:
            g = mean + spread * (1 if k % 2 == 0 else -1) * (1 + k % 3)
            rows.append({"ticker": "GBPJPY=X", "dir": 1, "date": d.isoformat(), "month": d.isoformat()[:7], "weekday": d.weekday(),
                         "gap": 0.1 * (k % 5), "gross": g + 1.2, "cost": 1.2, "net": g, "mirror_net": -g - 2.4, "net_official": g + 0.5})
            k += 1
        d += dt.timedelta(days=1)
    return rows


def test_verdicts_and_owner_rule():
    good = H.hold_stats(_rows(500, 4.0, 5.0), "day")
    assert good["verdict"] == "過去2年では残る" and H.owner_rule(good, "x") is None
    flat = H.hold_stats(_rows(600, 0.0, 5.0), "month")
    assert flat["verdict"] == "差なし" and H.owner_rule(flat, "x") is None          # 1000回未満はストップにしない
    many = H.hold_stats(_rows(1200, 0.0, 5.0), "day")
    v = H.owner_rule(many, "2026-09-30")
    assert v["status"] == "stop" and v["n"] == 1200
    assert H.hold_stats(_rows(100, 4.0, 5.0), "day")["verdict"] == "件数不足"
    assert H.hold_stats(_rows(500, -4.0, 5.0), "day")["verdict"] == "逆に効く"


def test_run_end_to_end_and_render():
    days = [dt.date(2025, 1, 6) + dt.timedelta(days=i) for i in range(120)]
    holds, verdicts = H.run(_walks(days, seed=9), "2026-09-30")
    assert all(holds[k]["n"] > 0 for k in H.HOLDS) and not verdicts
    out = {"generated_jst": "x", "prereg_sha256": "a" * 64, "kind": "backtest", "goal": 1000, "missing": [],
           "titles": {k: k for k in H.HOLDS}, "verdicts": verdicts, "holds": holds}
    md = H.render_md(out)
    assert "スワップは入れていない" in md and "投資助言ではありません" in md


def test_workflow_sync_and_verified_list():
    wf = open(".github/workflows/london-hold-lab.yml", encoding="utf-8").read()
    line = [x for x in wf.splitlines() if "pip install" in x][0]
    assert all(p in line.split() for p in ("numpy", "pandas", "yfinance"))
    assert "python london_hold_lab.py" in wf and "python verified_list.py" in wf and "schedule:" not in wf
    assert "london-hold-lab.json london-hold-lab.md verified-list.md" in wf
    import check_site_consistency as C
    assert {"london-hold-lab.json", "london-hold-lab.md"} <= set(C.SYNC_FORBIDDEN)
    assert any(s[0] == "london-hold-lab.json" for s in V.SOURCES)


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
