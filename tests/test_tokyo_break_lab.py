# -*- coding: utf-8 -*-
"""TB オーナーの裁量の決まり（tokyo_break_lab.py）のテスト。2026-11-11 新設。

値はすべて作り物（実際の値動きは見ていない）。確かめること＝①事前登録と定数の一致 ②東京時間のレンジ・「シリーズ全部がそろって抜けた」
合図・一番強いペアの選び方 ③腕A（抜けた線への指値・直近高値の利確・終値が内側に戻ったら次の足の始値・17:00 までに届かなければ入らない・
20:00 の時間切れ）④腕B（失敗の次の足の始値で逆に入る・真ん中で利確）⑤判定の順番 ⑥通しで動いて記録の形が出る ⑦リスト・ワークフロー・
RESEARCH_LABS へのつなぎ。

実行:  python tests/test_tokyo_break_lab.py     （pytest 不要。pytest でも動く）
"""
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import tokyo_break_lab as L  # noqa: E402

BASE = {p: (150.0 if p.endswith("JPY") else 1.0) for p in L.PAIRS}
SP = 0.0001                                           # スプレッド（値段に対する割合）


def _sec():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    return text[text.index(L.SECTION):text.index("## 共通の決まり")]


def _day(date, moves):
    """1日分（日本時間 09:00〜20:55）。東京時間は ±0.1% のレンジ・それ以降は moves[pair][(時,分)]＝(o,h,l,c) の倍率・無い足は直前の終値で平ら"""
    t0 = pd.Timestamp(date + " 00:00", tz="UTC")       # 日本時間 09:00
    idx = pd.date_range(t0, periods=144, freq="5min")
    bars = {}
    for p in L.PAIRS:
        b = BASE[p]
        rows, last = [], 1.0
        for k, t in enumerate(idx):
            j = t.tz_convert(L.JST)
            mv = moves.get(p, {}).get((j.hour, j.minute))
            if j.hour < 15:
                o, h, l, c = 1.0, (1.001 if k == 0 else 1.0), (0.999 if k == 1 else 1.0), 1.0
            elif mv:
                o, h, l, c = mv
            else:
                o = h = l = c = last
            last = c
            rows.append((o * b, h * b, l * b, c * b, SP * b, SP * b))
        bars[p] = pd.DataFrame(rows, index=idx, columns=["open", "high", "low", "close", "so", "sm"])
    return bars


def _cat(*days):
    return {p: pd.concat([d[p] for d in days]) for p in L.PAIRS}


BREAK = {(15, 0): (1.0, 1.004, 1.0, 1.003)}                       # 15:00 の足で東京高値（1.001）の上に引ける
BREAK_BIG = {(15, 0): (1.0, 1.0045, 1.0, 1.0035)}


def _win():      # ポンドがそろって上に抜け、ポンド円が押して（15:05）から直近高値（15:10）
    gj = {**BREAK_BIG, **{(15, 5): (1.0035, 1.0035, 1.0008, 1.002), (15, 10): (1.002, 1.005, 1.002, 1.005)}}
    return _day("2023-03-01", {"GBPJPY": gj, "GBPUSD": BREAK})


def _fail():     # 押した足の終値が内側に戻る（15:05）→ 腕A は損切り・腕B は 15:10 の始値で売って真ん中で利確
    gj = {**BREAK_BIG, **{(15, 5): (1.0035, 1.0035, 1.0004, 1.0005), (15, 10): (1.0005, 1.0005, 0.9998, 0.9999)}}
    return _day("2023-03-02", {"GBPJPY": gj, "GBPUSD": BREAK})


def test_prereg_matches_the_code():
    sec = _sec()
    for s in ("**ドル円・ユーロドル・ポンドドル・ユーロ円・ポンド円・豪ドル円・豪ドル米ドル**", "**2022-06-01〜書き出しの最後**", "**09:00〜14:55 に始まる足**",
              "**60本以上**", "**15:00〜16:55 に始まる足**", "**シリーズの全部のペアが、同じ足の終値で、その通貨が強い（弱い）向きに東京時間のレンジの外にある**",
              "**15:00 の足の始値から合図の足の終値までの値動き（%・抜けた向き）がいちばん大きいペア**", "**抜けた東京高値（売りは東京安値）に指値**",
              "**17:00 までに届かなければ入らない**", "**利確＝直近高値**", "**損切り＝5分足の終値が東京高値の内側に戻ったら**", "**時間切れ＝日本時間 20:00 に始まる足の始値**",
              "**終値が東京時間のレンジの内側に戻った**", "**利確＝東京レンジの真ん中**", "97.5%＝1−0.05÷2", "**200 未満**", "**p < 0.025（片側）**", "2,000回", "**中央値**",
              "**前半（〜2024-07-31）と後半（2024-08-01〜）の平均がどちらもプラス**", "`tokyo-break-lab.json`", "**オーナーの裁量が否定されたとは書かない**"):
        assert s in sec, s
    assert (L.START, L.SPLIT, L.TOKYO, L.WINDOW, L.TIME_EXIT, L.TOKYO_MIN_BARS, L.N_MIN, L.N_PERM) == ("2022-06-01", "2024-08-01", (540, 900), (900, 1020), 1200, 60, 200, 2000)
    assert abs(L.ALPHA - 0.025) < 1e-12
    assert set(L.SERIES["JPY"]) == {"USDJPY", "EURJPY", "GBPJPY", "AUDJPY"} and set(L.SERIES["USD"]) == {"USDJPY", "EURUSD", "GBPUSD", "AUDUSD"}
    assert L.SERIES["USD"]["USDJPY"] == 1 and L.SERIES["USD"]["EURUSD"] == -1 and all(v == -1 for v in L.SERIES["JPY"].values())
    assert L.OK.section_sha256(L.PREREG, L.SECTION)


def test_signal_needs_the_whole_series_and_picks_the_strongest_pair():
    P, idx, minute, dates, days = L.panel(_win())
    sig = L.all_signals(P, minute, days)
    assert len(sig) == 1
    g = sig[0]
    assert (g["cur"], g["strong"], g["pair"], g["s"], g["day"]) == ("GBP", 1, "GBPJPY", 1.0, "2023-03-01")
    assert abs(g["hi"] - 150.15) < 1e-9 and abs(g["lo"] - 149.85) < 1e-9 and abs(g["mid"] - 150.0) < 1e-9
    assert minute[g["t"]] == 900
    # 片方だけ抜けた日は合図なし
    P2, _, m2, _, d2 = L.panel(_day("2023-03-01", {"GBPJPY": BREAK_BIG}))
    assert L.all_signals(P2, m2, d2) == []
    # 土日は数えない
    P3, _, m3, _, d3 = L.panel(_day("2023-03-04", {"GBPJPY": BREAK_BIG, "GBPUSD": BREAK}))
    assert d3 == {} and L.all_signals(P3, m3, d3) == []


def test_yen_series_strong_and_same_pair_counted_once():
    down = {(15, 0): (1.0, 1.0, 0.996, 0.997)}
    mv = {p: down for p in ("USDJPY", "EURJPY", "GBPJPY", "AUDJPY")}
    mv["GBPJPY"] = {(15, 0): (1.0, 1.0, 0.995, 0.996)}
    mv["GBPUSD"] = down                                             # ポンドも弱い → ポンド円の売りが2つの通貨から選ばれる
    P, _, minute, _, days = L.panel(_day("2023-03-01", mv))
    sig = L.all_signals(P, minute, days)
    assert [(g["pair"], g["s"]) for g in sig] == [("GBPJPY", -1.0)]


def test_arm_a_pullback_limit_takes_profit_at_the_recent_high():
    P, _, minute, _, days = L.panel(_win())
    g = L.all_signals(P, minute, days)[0]
    t = L.trade_a(P, g, days[g["day"]], minute)
    edge, tp = 150.0 * 1.001, 150.0 * 1.0045
    assert t["exit"] == "tp" and abs(t["after"] - (tp - edge) / edge) < 1e-12
    assert abs(t["tp_d"] - (tp - edge) / edge) < 1e-12 and abs(t["sl_d"]) < 1e-12
    assert L.trade_b(P, g, days[g["day"]], minute) is None             # 内側に戻っていない＝失敗なし


def test_arm_a_not_entered_and_time_exit():
    # 押さずに上がり続ける → 入らない
    gj = {**BREAK_BIG, **{(15, 5): (1.0035, 1.006, 1.0035, 1.006)}}
    P, _, minute, _, days = L.panel(_day("2023-03-01", {"GBPJPY": gj, "GBPUSD": BREAK}))
    g = L.all_signals(P, minute, days)[0]
    assert L.trade_a(P, g, days[g["day"]], minute) is None
    # 押して入ったあと動かない → 20:00 の始値（売値）で出る
    gj = {**BREAK_BIG, **{(15, 5): (1.0035, 1.0035, 1.0008, 1.002)}}
    P, _, minute, _, days = L.panel(_day("2023-03-01", {"GBPJPY": gj, "GBPUSD": BREAK}))
    g = L.all_signals(P, minute, days)[0]
    t = L.trade_a(P, g, days[g["day"]], minute)
    edge = 150.0 * 1.001
    assert t["exit"] == "time" and abs(t["after"] - (150.0 * 1.002 - edge) / edge) < 1e-12


def test_failed_break_stops_arm_a_and_reverses_in_arm_b():
    P, _, minute, _, days = L.panel(_fail())
    g = L.all_signals(P, minute, days)[0]
    a = L.trade_a(P, g, days[g["day"]], minute)
    edge, nxt = 150.0 * 1.001, 150.0 * 1.0005
    assert a["exit"] == "sl" and abs(a["after"] - (nxt - edge) / edge) < 1e-12 and a["after"] < 0
    b = L.trade_b(P, g, days[g["day"]], minute)
    assert b["s"] == -1.0 and b["exit"] == "tp" and abs(b["after"] - (nxt - 150.0) / nxt) < 1e-12 and b["after"] > 0


def test_judge_order():
    ok = {"n": 250, "mean": 0.001, "lo": 0.0001, "hi": 0.002}
    assert L.judge(dict(ok, n=199), 0.001, 1, 1) == "検定不能"
    assert L.judge(dict(ok, lo=-0.001, hi=-0.0001), 0.001, 1, 1) == "費用後マイナス"
    assert L.judge(dict(ok, lo=-0.001), 0.001, 1, 1) == "0と区別できない"
    assert L.judge(ok, 0.03, 1, 1) == "でたらめな足と差なし"
    assert L.judge(ok, 0.001, 1, -1) == "前半と後半で割れた"
    assert L.judge(ok, 0.001, 1, 1) == L.SURVIVED


def test_end_to_end_record_shape():
    P, idx, minute, dates, days = L.panel(_cat(_win(), _fail()))
    res = L.analyze(P, minute, days, n_perm=20)
    assert res["signals"] == 2 and res["A"]["n"] == 2 and res["B"]["n"] == 1 and res["B"]["not_entered"] == 1
    assert res["A"]["exits"] == {"tp": 1, "sl": 1, "time": 0} and res["A"]["verdict"] == "検定不能"
    v = L.verdicts_of(res, "2026-11-11")
    assert set(v) == {"TB-A", "TB-B"} and v["TB-A"]["status"] == "stop" and "裁量の一部だけ" in v["TB-A"]["reason"]
    rec = L.OK._clean({"generated_jst": "x", "prereg_sha256": "abc", "data": "d", "arms": res})
    md = L.render_md(rec)
    assert "TB-A" in md and "投資助言ではありません" in md and "ペアごと" in md


def test_wiring():
    import verified_list as VL
    assert any(s[0] == "tokyo-break-lab.json" and s[2] == "" for s in VL.SOURCES)
    assert "'tokyo-break-lab.json'" in open(".github/workflows/research-lists.yml", encoding="utf-8").read()
    assert "tokyo_break_lab.py" in open("RESEARCH_LABS.md", encoding="utf-8").read()
    assert '"tokyo-break-lab.json"' not in open("check_site_consistency.py", encoding="utf-8").read()   # 手元で作って送る記録＝SYNC 禁忌ではない


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("ok  ", name)
            except Exception as e:                                    # noqa: BLE001
                fails += 1
                print("FAIL", name, repr(e))
    sys.exit(1 if fails else 0)
