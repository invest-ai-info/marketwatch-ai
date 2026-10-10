# -*- coding: utf-8 -*-
"""OK 及川式の通貨の強弱（oikawa_lab.py）のテスト。2026-10-10 新設。

値はすべて作り物（実際の値動きは見ていない）。確かめること＝①事前登録と定数の一致 ②手元の5分足ファイルの読み方（サーバー時刻 →
UTC → ロンドン・スプレッドのポイント → 値段）③腕A（ユーロポンド＝ユーロドル÷ポンドドル・ドル円で強い方を選ぶ）と腕B（豪ドルの
シリーズ）の合図 ④次の足で入って出る・費用（出る側は出る時のスプレッド）・足が続いていなければ入らない ⑤ロンドンの時間帯（夏冬）
⑥幅・偽薬・判定の順番 ⑦通しで動き、検証済みリストの形の記録が出る ⑧検証済みリスト・ワークフローへのつなぎ。

実行:  python tests/test_oikawa_lab.py     （pytest 不要。pytest でも動く）
"""
import json
import os
import sys
import tempfile

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import oikawa_lab as L  # noqa: E402


def _sec():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    return text[text.index(L.SECTION):text.index("## 共通の決まり")]


def test_prereg_matches_the_code():
    sec = _sec()
    for s in ("**ドル円・ユーロドル・ポンドドル・ユーロ円・ポンド円・豪ドル円・豪ドル米ドル**", "**ユーロポンドは書き出しに無いので、同じ時刻のユーロドル÷ポンドドルで作る**",
              "**2022-06-01〜書き出しの最後**", "**08:00〜15:50**", "**そのペアが同じ足で上げていたら**", "**そのペアが同じ足で下げていたら**",
              "**豪ドル円と豪ドル米ドルが同じ足で同じ向きに動いた**", "**次の足の始値**で入り、**その足の終値**で必ず手じまう",
              "**次の足の始まりのスプレッド**", "97.5%＝1−0.05÷2", "**300 未満**", "**p < 0.025（片側）**", "**前半（〜2024-07-31）と後半（2024-08-01〜）の平均がどちらもプラス**",
              "2,000回", "持つ足を3本", "`oikawa-lab.json`"):
        assert s in sec, s
    assert L.PAIRS == ("USDJPY", "EURUSD", "GBPUSD", "EURJPY", "GBPJPY", "AUDJPY", "AUDUSD") and "USDJPY" not in L.TRADED
    assert (L.START, L.SPLIT, L.SIG_FROM, L.SIG_TO, L.N_MIN, L.N_PERM, L.HOLD, L.HOLD_READ) == ("2022-06-01", "2024-08-01", (8, 0), (15, 50), 300, 2000, 1, 3)
    assert abs(L.ALPHA - 0.025) < 1e-12 and abs(L.Z - 2.2414) < 1e-3


def _write_csv(folder, pair, rows):
    path = os.path.join(folder, f"m5tick_{pair}.csv")
    with open(path, "w", encoding="utf-8") as f:
        f.write("time\topen\thigh\tlow\tclose\ttickvol\tspread_open\tspread_max\n" + "\n".join("\t".join(map(str, r)) for r in rows) + "\n")
    return path


def test_read_bars_time_and_units():
    with tempfile.TemporaryDirectory() as d:
        p = _write_csv(d, "EURUSD", [("2022.06.01 10:00", 1.07, 1.071, 1.069, 1.0705, 50, 8, 15),
                                     ("2022.06.01 10:05", 1.0705, 1.071, 1.07, 1.0702, 40, 9, 12)])
        b = L.read_bars(p, "EURUSD")
        assert str(b.index[0]) == "2022-06-01 07:00:00+00:00"            # サーバー 10:00（NY＋7・夏）＝NY 03:00＝UTC 07:00
        assert b.index[0].tz_convert(L.LON).hour == 8                    # ロンドン 08:00（夏時間）
        assert abs(b["so"].iloc[0] - 0.00008) < 1e-12 and abs(b["sm"].iloc[0] - 0.00015) < 1e-12
        assert abs(b["close"].iloc[1] - 1.0702) < 1e-12
        pj = _write_csv(d, "USDJPY", [("2022.12.01 10:00", 135.0, 135.1, 134.9, 135.05, 50, 7, 10)])
        bj = L.read_bars(pj, "USDJPY")
        assert bj.index[0].tz_convert(L.LON).hour == 8 and abs(bj["so"].iloc[0] - 0.007) < 1e-12   # 冬：サーバー 10:00＝UTC 08:00＝ロンドン 08:00


def _panel(times, quotes):
    """times＝UTC の時刻の並び・quotes[pair]＝[(o, c, so)] → panel と同じ形"""
    idx = pd.DatetimeIndex(pd.to_datetime(times), tz="UTC")
    P = {}
    for p in L.PAIRS:
        q = quotes.get(p) or [(1.0, 1.0, 0.0)] * len(times)
        P[p] = {"o": np.array([x[0] for x in q], float), "c": np.array([x[1] for x in q], float),
                "so": np.array([x[2] for x in q], float), "sm": np.array([x[2] * 2 for x in q], float)}
    return P, idx, idx.tz_convert(L.LON)


T3 = ["2022-07-01 07:00", "2022-07-01 07:05", "2022-07-01 07:10"]       # ロンドン 08:00・08:05・08:10（夏）


def test_arm_a_picks_the_strong_side():
    up, dn, flat = (1.0, 1.001, 0.0), (1.0, 0.999, 0.0), (1.0, 1.0, 0.0)
    # ドル円が上げ（円が弱い）・ユーロドルがポンドドルより上げ（ユーロポンドが上げ＝ユーロが強い）
    q = {"USDJPY": [(100, 100.1, 0.01)] * 3, "EURUSD": [(1.10, 1.102, 0.0001)] * 3, "GBPUSD": [(1.25, 1.2505, 0.0001)] * 3,
         "EURJPY": [(150, 150.2, 0.02)] * 3, "GBPJPY": [up] * 3, "AUDJPY": [flat] * 3, "AUDUSD": [flat] * 3}
    P, idx, lon = _panel(T3, q)
    sig = L.signals(P, lon)
    longs = [(i, p, s) for i, p, s in sig["A"] if s > 0]
    assert longs[0][1:] == ("EURJPY", 1.0)                      # 強いユーロ × 弱い円を買う
    assert not [x for x in sig["A"] if x[2] < 0]                # 売りの候補（ポンドドル）は上げている＝売らない
    q["GBPUSD"] = [(1.25, 1.2495, 0.0001)] * 3                  # ポンドドルが下げ
    P, idx, lon = _panel(T3, q)
    sig = L.signals(P, lon)
    assert ("GBPUSD", -1.0) in [(p, s) for _, p, s in sig["A"]]   # 弱いポンド × 強いドルを売る
    q["USDJPY"] = [(100, 100, 0.01)] * 3                        # ドル円が動かない＝入らない
    P, idx, lon = _panel(T3, q)
    assert L.signals(P, lon)["A"] == [] and L.signals(P, lon)["B"] == []


def test_arm_b_aud_series():
    up, dn = (1.0, 1.001, 0.0), (1.0, 0.999, 0.0)
    q = {"USDJPY": [(100, 100.1, 0.01)] * 3, "AUDJPY": [(90, 90.1, 0.02)] * 3, "AUDUSD": [(0.70, 0.701, 0.0001)] * 3}
    P, idx, lon = _panel(T3, q)
    sig = L.signals(P, lon)
    assert sig["B"][0][1:] == ("AUDJPY", 1.0) and len(sig["B_both"]) == 2 * len(sig["B"])   # 豪ドルが強い・円が弱い → 豪ドル円を買う
    q["USDJPY"] = [(100, 99.9, 0.01)] * 3                       # 円が強い → 豪ドル米ドルを買う
    P, idx, lon = _panel(T3, q)
    assert L.signals(P, lon)["B"][0][1:] == ("AUDUSD", 1.0)
    q["AUDJPY"], q["AUDUSD"] = [(90, 89.9, 0.02)] * 3, [(0.70, 0.699, 0.0001)] * 3       # 両方下げ・円が強い → 豪ドル円を売る
    P, idx, lon = _panel(T3, q)
    assert L.signals(P, lon)["B"][0][1:] == ("AUDJPY", -1.0)
    q["AUDUSD"] = [(0.70, 0.701, 0.0001)] * 3                   # そろわない＝入らない
    P, idx, lon = _panel(T3, q)
    assert L.signals(P, lon)["B"] == []


def test_trade_cost_and_contiguity():
    q = {"EURUSD": [(1.1000, 1.1010, 0.0001), (1.1010, 1.1020, 0.0002), (1.1020, 1.1000, 0.0003)]}
    P, idx, lon = _panel(T3, q)
    after, before, e = L.trade(P, idx, 0, "EURUSD", 1.0)
    assert e == 1 and abs(before - (1.1020 - 1.1010) / 1.1010) < 1e-12
    assert abs(after - (1.1020 - (1.1010 + 0.0002)) / (1.1010 + 0.0002)) < 1e-12          # 買い＝買値で入り売値で出る
    after_s, before_s, _ = L.trade(P, idx, 0, "EURUSD", -1.0)
    assert abs(after_s - -((1.1020 + 0.0003) - 1.1010) / 1.1010) < 1e-12                   # 売り＝出る側は次の足の始まりのスプレッド
    P2, idx2, _ = _panel(["2022-07-01 07:00", "2022-07-01 07:10", "2022-07-01 07:15"], q)
    assert L.trade(P2, idx2, 0, "EURUSD", 1.0) is None            # 5分ずつ続いていない＝入らない


def test_trade_short_last_bar_uses_max_spread():
    q = {"EURUSD": [(1.1, 1.1, 0.0001), (1.1, 1.0990, 0.0002), (1.0990, 1.0980, 0.0003), (1.0980, 1.0970, 0.0004)]}
    P, idx, lon = _panel(["2022-07-01 07:00", "2022-07-01 07:05", "2022-07-01 07:10", "2022-07-01 07:30"], q)
    after, before, e = L.trade(P, idx, 1, "EURUSD", -1.0)        # 入る足 2・次の足（3）は20分後＝続いていない → 足 2 の最大スプレッド
    assert e == 2 and abs(after - (1.0990 - (1.0980 + 0.0006)) / 1.0990) < 1e-12


def test_london_window_and_dst():
    idx = pd.DatetimeIndex(pd.to_datetime(["2022-07-01 06:55", "2022-07-01 07:00", "2022-07-01 14:50", "2022-07-01 14:55",
                                           "2022-12-01 08:00", "2022-12-03 08:00"]), tz="UTC")
    w = L.in_window(idx.tz_convert(L.LON))
    assert list(w) == [False, True, True, False, True, False]   # 夏 07:55 外・08:00 内・15:50 内・15:55 外／冬 UTC 08:00＝ロンドン 08:00／土曜は外


def test_cluster_judge_and_placebo():
    st = L.cluster([0.001] * 200 + [0.0011] * 200, [f"2023-01-{1 + k % 28:02d}" for k in range(400)])
    assert st["lo"] > 0 and st["n"] == 400
    assert L.judge({"n": 299, "lo": 1, "hi": 2}, 0.0, 1, 1) == "検定不能"
    assert L.judge({"n": 400, "lo": -0.2, "hi": -0.1}, 0.0, 1, 1) == "費用後マイナス"
    assert L.judge({"n": 400, "lo": -0.1, "hi": 0.1}, 0.0, 1, 1) == "0と区別できない"
    assert L.judge({"n": 400, "lo": 0.1, "hi": 0.2}, 0.05, 1, 1) == "でたらめな足と差なし"
    assert L.judge({"n": 400, "lo": 0.1, "hi": 0.2}, 0.001, -1, 1) == "前半と後半で割れた"
    assert L.judge({"n": 400, "lo": 0.1, "hi": 0.2}, 0.001, 1, 1) == L.SURVIVED
    rows = [{"pair": "EURUSD", "s": 1.0}] * 50
    pool = {("EURUSD", 1.0): np.random.default_rng(1).normal(0, 0.001, 5000)}
    p_hi, _ = L.placebo_p(rows, pool, 0.002, n_perm=300)
    p_lo, _ = L.placebo_p(rows, pool, -0.002, n_perm=300)
    assert p_hi < 0.01 and p_lo > 0.9


def test_run_end_to_end_with_made_up_files():
    rng = np.random.default_rng(5)
    srv = pd.date_range("2022-06-06 09:00", "2022-06-10 18:00", freq="5min")      # サーバー時刻（夏）＝ロンドン 07:00〜16:00 前後
    srv = srv[[t.weekday() < 5 and 9 <= t.hour < 19 for t in srv]]
    base = {"USDJPY": 130.0, "EURUSD": 1.07, "GBPUSD": 1.25, "EURJPY": 139.0, "GBPJPY": 162.0, "AUDJPY": 93.0, "AUDUSD": 0.72}
    with tempfile.TemporaryDirectory() as d:
        for p, b0 in base.items():
            px = b0 * np.exp(np.cumsum(rng.normal(0, 0.0004, len(srv))))
            o = np.concatenate([[b0], px[:-1]])
            rows = [(t.strftime("%Y.%m.%d %H:%M"), f"{a:.5f}", f"{max(a, c) * 1.0001:.5f}", f"{min(a, c) * 0.9999:.5f}", f"{c:.5f}", 10, 9, 15)
                    for t, a, c in zip(srv, o, px)]
            _write_csv(d, p, rows)
        rep = L.check(d)
        assert rep["bars"]["EURUSD"]["rows"] > 0 and rep["london_bars"] > 0 and set(rep["signals"]) == {"A", "B", "B_both"}
        assert "returns" not in json.dumps(rep) and "after" not in json.dumps(rep)     # check は損益を数えない
        rec = L._clean(L.run(d, n_perm=20))
        assert set(rec["titles"]) == {"OK-A", "OK-B"} and rec["kind"] == "backtest" and rec["unit"] == "pct"
        for arm in ("A", "B"):
            assert rec["arms"][arm]["verdict"] in ("検定不能", "費用後マイナス", "0と区別できない", "でたらめな足と差なし", "前半と後半で割れた", L.SURVIVED)
        assert all(v["status"] == "stop" for v in rec["verdicts"].values())
        md = L.render_md(rec)
        assert "OK-A" in md and "投資助言ではありません" in md


def test_lists_and_workflow():
    import verified_list as VL
    assert any(s[0] == "oikawa-lab.json" and s[2] == "OK" for s in VL.SOURCES)
    assert "'oikawa-lab.json'" in open(".github/workflows/research-lists.yml", encoding="utf-8").read()
    assert "oikawa_lab.py" in open("RESEARCH_LABS.md", encoding="utf-8").read()
    assert '"oikawa-lab.json"' not in open("check_site_consistency.py", encoding="utf-8").read()   # 手元で作って送る記録＝SYNC 禁忌ではない


if __name__ == "__main__":
    n = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            n += 1
            print(f"ok {name}")
    print(f"{n} tests passed")
