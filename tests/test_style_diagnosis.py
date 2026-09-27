# -*- coding: utf-8 -*-
"""投資スタイル診断（style_diagnosis.py）のテスト。2026-09-27 新設。

取引履歴も値段もすべて作り物（個人のデータは使わない・ネットワークに出ない）。確かめること＝①MT4 の口座履歴の読み込みと
口座の数字との照合 ②サーバー時刻→日本時間（夏時間）③スタイル・銘柄の分け方 ④費用込みの物差し ⑤環境は入る前の日足だけで
決める（後から見た情報を使わない）⑥判定の決まり ⑦出力先は research/ の下（GitHub へ送られない）。

実行:  python tests/test_style_diagnosis.py     （pytest 不要。pytest でも動く）
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
import style_diagnosis as S  # noqa: E402

HEAD = ["Ticket", "Open Time", "Type", "Size", "Item", "Price", "S / L", "T / P", "Close Time", "Price", "Commission", "Taxes", "Swap", "Profit"]


def _row(cells):
    return "<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>"


def _stmt(trades, closed_pl=None):
    """trades＝[(open, type, lot, item, price, close, cprice, comm, swap, profit)]"""
    rows = [_row(["Closed Transactions:"]), _row(HEAD)]
    for k, (o, ty, lot, item, p, c, cp, comm, swap, prof) in enumerate(trades):
        rows.append(_row([str(1000 + k), o, ty, f"{lot:.2f}", item, p, "0.000", "0.000", c, cp, f"{comm:,.0f}".replace(",", " "),
                          "0", f"{swap:,.0f}".replace(",", " "), f"{prof:,.0f}".replace(",", " ")]))
    rows.append(_row(["1", "2026.01.05 00:00:00", "balance", "D deposit", "100 000"]))
    rows.append(_row(["2", "2026.01.05 00:00:00", "buy limit", "0.10", "usdjpy", "150.0", "0", "0", "2026.01.06 00:00:00", "151", "cancelled"]))
    if closed_pl is not None:
        rows.append(_row(["Closed P/L:", f"{closed_pl:,.0f}".replace(",", " ")]))
    return "<html><table>" + "".join(rows) + "</table></html>"


def test_server_time_to_jst_with_summer_time():
    assert S.server_to_jst("2026.07.01 12:00:00").strftime("%H:%M") == "18:00"          # 夏＝+6時間
    assert S.server_to_jst("2026.01.15 12:00:00").strftime("%H:%M") == "19:00"          # 冬＝+7時間
    assert S.server_to_jst("2026.01.15 12:00:00", "utc+3").strftime("%H:%M") == "18:00"
    assert S.server_to_jst("2026.01.15 12:00", "jst").strftime("%H:%M") == "12:00"


def test_parse_and_check_against_account():
    tr = [("2026.03.02 10:00:00", "buy", 0.10, "usdjpy", "150.000", "2026.03.02 10:20:00", "150.100", -73, 0, 1000),
          ("2026.03.03 10:00:00", "sell", 0.01, "gold_usd", "3000.00", "2026.03.05 10:00:00", "2990.00", 0, -120, 1500)]
    trades, pl = S.parse_statement(_stmt(tr, closed_pl=1000 - 73 + 1500 - 120))
    assert len(trades) == 2 and pl == 2307
    assert abs(sum(x["net"] for x in trades) - pl) < 1e-9
    assert trades[0]["side"] == 1 and trades[1]["side"] == -1 and trades[0]["cost"] == -73
    assert abs(trades[0]["hold_min"] - 20) < 1e-9


def test_reads_utf16_and_shift_jis():
    tr = [("2026.03.02 10:00:00", "buy", 0.10, "usdjpy", "150.000", "2026.03.02 10:20:00", "150.100", -73, 0, 1000)]
    text = _stmt(tr, closed_pl=927).replace("<html>", "<html><p>名前</p>")
    with tempfile.TemporaryDirectory() as d:
        for enc in ("utf-16", "cp932", "utf-8"):
            p = os.path.join(d, f"s-{enc}.htm")
            open(p, "wb").write(text.encode(enc))
            trades, pl = S.parse_statement(S.read_text(p))
            assert len(trades) == 1 and pl == 927, enc


def test_styles_and_symbols():
    mk = lambda m: {"hold_min": m}
    assert [S.style_of(mk(m)) for m in (0, 59.9, 60, 479, 480, 7199, 7200, 99999)] == \
        ["スキャルピング", "スキャルピング", "デイトレ", "デイトレ", "スイング", "スイング", "長め", "長め"]
    assert S.class_of("usdjpy") == "円のペア" and S.class_of("EURUSD.m") == "その他の為替" and S.class_of("gold_usd") == "金・銀"
    assert S.class_of("n225_jpy") == "株価指数" and S.class_of("oilwti_usd") == "原油" and S.class_of("btcusdt") == "暗号資産"
    assert S.yahoo_of("gbpjpy") == "GBPJPY=X" and S.yahoo_of("XAUUSD") == "GC=F" and S.yahoo_of("n225_jpy") == "NKD=F"
    assert S.yahoo_of("btcusdt") == "BTC-USD" and S.yahoo_of("dow30_usd") == "YM=F" and S.yahoo_of("abc") is None


def test_units_include_costs():
    x = {"side": 1, "po": 100.0, "pc": 101.0, "profit": 1000.0, "net": 800.0, "atr": 2.0}
    assert abs(S.net_units(x, "atr") - 0.4) < 1e-12          # 値幅1 × 800/1000 ÷ ATR2
    assert abs(S.net_units(x, "bp") - 80.0) < 1e-9
    x2 = dict(x, side=-1, pc=99.0)
    assert abs(S.net_units(x2, "atr") - 0.4) < 1e-12
    assert S.net_units(dict(x, atr=None), "atr") is None


def test_judge_rules():
    good = {"n_unit": 50, "mean": 0.2, "lo": 0.05, "hi": 0.4, "mean_wo_top": 0.1}
    halves = [("前半", 25, 0.2), ("後半", 25, 0.1)]
    cells = [("値動き小さい", 12, 0.1), ("流れに逆らう", 5, -0.3)]            # 10回未満の区分は見ない
    assert S.judge(good, halves, cells, True) == ("◯ 合っている", [])
    assert S.judge(dict(good, n_unit=29), halves, cells, True)[0] == "？ 記録が足りない"
    assert S.judge(dict(good, mean=-0.3, lo=-0.5, hi=-0.1), halves, cells, True)[0] == "✕ 合っていない"
    assert S.judge(dict(good, mean=-0.1, lo=-0.5, hi=0.2), halves, cells, True)[0] == "▽ マイナス寄り（確かではない）"
    v, why = S.judge(dict(good, lo=-0.01, mean_wo_top=-0.02), [("前半", 25, -0.1), ("後半", 25, 0.3)],
                     [("値動き大きい", 11, -0.2)], False)
    assert v == "△ プラスだが確かではない"
    assert why == ["95%の幅が0をまたぐ", "大きい勝ち5回を除くとマイナス", "時期によってマイナス（前半）",
                   "環境の確認ができていない", "環境によってマイナス（値動き大きい）"]


def _daily(n=700, start="2023-06-01", spike_on=None):
    idx = pd.bdate_range(start, periods=n)
    c = 100 + np.cumsum(np.full(n, 0.05))                                       # ゆっくり上がる
    h, l = c + 0.5, c - 0.5
    df = pd.DataFrame({"Open": c, "High": h, "Low": l, "Close": c}, index=idx)
    if spike_on is not None:
        df.loc[pd.Timestamp(spike_on), "High"] += 50                            # 入った日の足に大きな値幅
    return df


def test_environment_uses_only_bars_before_entry():
    x = {"sym": "usdjpy", "side": 1, "open": dt.datetime(2025, 9, 10, 20, 0, tzinfo=S.JST)}
    S.attach_market([x], fetch=lambda tk, start: _daily(spike_on="2025-09-10"))
    assert abs(x["atr"] - 1.0) < 0.2                          # 入った日の大きな値幅は入っていない
    assert x["trend"] == "流れに沿う"                          # 上がる相場で買い
    y = {"sym": "usdjpy", "side": -1, "open": dt.datetime(2025, 9, 10, 20, 0, tzinfo=S.JST)}
    S.attach_market([y], fetch=lambda tk, start: _daily())
    assert y["trend"] == "流れに逆らう" and y["vol"] in ("小さい", "ふつう", "大きい")
    z = {"sym": "unknown_sym", "side": 1, "open": dt.datetime(2025, 9, 10, 20, 0, tzinfo=S.JST)}
    assert S.attach_market([z], fetch=lambda tk, start: _daily()) == [] and z["atr"] is None


def _many(seed=1):
    """スイングだけ勝つ作り物の履歴（120回）"""
    rng = np.random.default_rng(seed)
    base = dt.datetime(2025, 9, 1, 12, 0)
    tr = []
    for k in range(120):
        o = base + dt.timedelta(hours=13 * k)
        swing = k % 2 == 0
        hold = dt.timedelta(hours=30) if swing else dt.timedelta(minutes=20)
        move = (0.8 if swing else -0.1) + rng.normal(0, 0.1)
        prof = move * 1000
        tr.append((o.strftime("%Y.%m.%d %H:%M:%S"), "buy", 0.10, "usdjpy", "150.000", (o + hold).strftime("%Y.%m.%d %H:%M:%S"),
                   f"{150 + move:.3f}", -70, 0, round(prof)))
    return tr


def test_run_end_to_end_writes_under_research():
    tr = _many()
    net = sum(t[9] + t[7] for t in tr)
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "Statement.htm")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(_stmt(tr, closed_pl=net))
        out = os.path.join(d, "research", "style-diagnosis")
        md, res, meta = S.run(p, market=True, out_dir=out, fetch=lambda tk, start: _daily(n=900, start="2023-01-02"),
                              now=dt.datetime(2026, 9, 27, 20, 0, tzinfo=S.JST))
        assert meta["check"] == "一致" and meta["kind"] == "atr" and meta["n"] == 120
        assert res["スキャルピング"]["verdict"].startswith(("✕", "▽"))
        assert res["スイング"]["mean"] > 0 and res["スイング"]["verdict"] in ("◯ 合っている", "△ プラスだが確かではない")
        assert sorted(os.listdir(out)) == ["report-20260927.md", "result-20260927.json"]
        assert "投資助言ではありません" in md and "環境が変わっても同じか" in md
        md2, _, meta2 = S.run(p, market=False, out_dir=out)
        assert meta2["kind"] == "bp" and "環境の確認ができていない" in md2


def test_profile_init_and_compare():
    with tempfile.TemporaryDirectory() as d:
        pf = os.path.join(d, "profile.json")
        assert S.main(["--init-profile", "--profile", pf]) == 0
        data = json.load(open(pf, encoding="utf-8"))
        assert set(data["answers"]) == {"weekday_daytime", "weekday_evening", "preferred_style", "revenge_urge"}
        data["answers"]["preferred_style"] = "スイング"
        json.dump(data, open(pf, "w", encoding="utf-8"), ensure_ascii=False)
        assert S.main(["--init-profile", "--profile", pf]) == 0                     # 上書きしない
        assert json.load(open(pf, encoding="utf-8"))["answers"]["preferred_style"] == "スイング"
    res = {"スイング": {"verdict": "△ プラスだが確かではない"}}
    x = {"open": dt.datetime(2026, 9, 1, 11, 0, tzinfo=S.JST), "net": -500}          # 平日の日中
    lines = S.compare_profile({"preferred_style": "スイング", "weekday_daytime": "見られない", "revenge_urge": "ならない"},
                              res, [x], {"after_loss": (3, -900), "busy_days": (0, 0)})
    assert len(lines) == 3 and "△" in lines[0] and "1回" in lines[1] and "3回" in lines[2]


def test_default_output_is_private():
    assert S.OUT_DIR.replace("\\", "/").startswith("research/")


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
