# -*- coding: utf-8 -*-
"""LP ドル円5分足の「取引→検証→改善」の繰り返し（loop_judge.py）のテスト。2026-10-01 新設。

取引はすべて作り物（ネットワークに出ない）。確かめること＝①事前登録と定数の一致 ②日本時間 07:00 区切り
③1日の損失の上限 −3% を過去の計算に入れる ④デモの記録から％だけ ⑤日ごとの幅・落ち込み ⑥段は幅の下限で上がる
⑦関門A（確かめた回数の累計で厳しくなる）と登録の決まり ⑧デモの窓（途中で消える・窓の終わり・段は下がらない）
⑨止める決まり（12ラウンド・3回続けて消えた）⑩振り返りの表 ⑪台帳に金額を書かない。

実行:  python tests/test_loop_judge.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import loop_judge as LJ  # noqa: E402

UTC = dt.timezone.utc


def _utc(y, m, d, h, mi=0):
    return int(dt.datetime(y, m, d, h, mi, tzinfo=UTC).timestamp())


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    i = text.find("\n## LP ")
    sec = text[i:text.find("\n## ", i + 1)]
    for s in ("日本時間 07:00 区切り", "**1日の損失の上限 −3%**", "段4", "+3%（オーナーの目標）", "+0.3%", "+1%",
              "**12ラウンド**", "**3回続けてデモで消えた**", "**窓＝100回以上かつ10営業日以上**", "5営業日かつ30回以上",
              "**累計は M5-3 の確かめ6回から始める**", "最大3つまで", "`loop_judge.py`", "`research/loop/loop-ledger.json`",
              "2022-06-01〜2024-07-31／確かめ＝2024-08-01〜2026-09-24"):
        assert s in sec, s
    assert (LJ.RISK_PCT, LJ.DAILY_STOP, LJ.DAY_CUT_HOUR) == (0.01, -0.03, 7)
    assert [s[2] for s in LJ.STAGES] == [None, 0.0, 0.003, 0.01, 0.03]
    assert (LJ.CONFIRM_BASE, LJ.MAX_VARIANTS, LJ.MAX_ROUNDS, LJ.MAX_FWD_FAILS) == (6, 3, 12, 3)
    assert (LJ.FWD_MIN_TRADES, LJ.FWD_MIN_DAYS, LJ.EARLY_TRADES, LJ.EARLY_DAYS) == (100, 10, 30, 5)
    assert LJ.SELECT == ("2022-06-01", "2024-07-31") and LJ.CONFIRM == ("2024-08-01", "2026-09-24")
    assert len(LJ.new_ledger()["prereg_sha256"]) == 64


def test_trading_day_cut_at_0700_jst():
    assert LJ.trading_day(_utc(2026, 10, 1, 21, 59)) == "2026-10-01"      # 日本時間 10/2 06:59 → 10/1 の日
    assert LJ.trading_day(_utc(2026, 10, 1, 22, 0)) == "2026-10-02"       # 日本時間 10/2 07:00 → 10/2 の日
    assert LJ.trading_day(_utc(2026, 10, 2, 8, 0)) == "2026-10-02"


def test_daily_stop_is_applied_to_backtest():
    t0 = _utc(2026, 10, 2, 6)
    trades = [{"t": t0 + 300 * k, "r": r, "cost_r": 0.13} for k, r in enumerate([-1, -1, -1, 2, 2])]
    days = LJ.daily_from_r(trades)
    assert len(days) == 1
    d = days[0]
    assert abs(d["pct"] + 0.03) < 1e-12 and d["stopped"] and d["n"] == 3 and d["skipped"] == 2   # 3回目で −3%＝残りは入らない
    assert abs(d["cost_pct"] - 0.0039) < 1e-12
    ok = LJ.daily_from_r([{"d": "2026-10-05", "r": 1.5}, {"d": "2026-10-05", "r": -1}, {"d": "2026-10-06", "r": 0.5}])
    assert [(x["d"], round(x["pct"], 4), x["n"]) for x in ok] == [("2026-10-05", 0.005, 2), ("2026-10-06", 0.005, 1)]


def test_daily_from_demo_money_is_pct_only():
    t = _utc(2026, 10, 2, 6)
    rows = [{"open_utc": t, "close_utc": t + 600, "balance": 100000, "profit": 400, "commission": -10, "swap": 0},
            {"open_utc": t + 900, "close_utc": t + 1500, "balance": 100390, "profit": -200, "commission": -10, "swap": -5},
            {"open_utc": t + 1800, "close_utc": "", "balance": 100175, "profit": 0, "commission": 0, "swap": 0}]   # 開いている
    days = LJ.daily_from_money(rows)
    assert len(days) == 1 and days[0]["n"] == 2 and abs(days[0]["pct"] - (390 - 215) / 100000) < 1e-12
    assert "balance" not in json.dumps(days) and days[0]["cost_pct"] is None


def _days(vals, start=dt.date(2026, 10, 5), n=None):
    out, d, k = [], start, 0
    for v in vals:
        while d.weekday() >= 5:
            d += dt.timedelta(days=1)
        out.append({"d": d.isoformat(), "pct": v, "n": n or 10, "cost_pct": 0.004, "stopped": v <= -0.03, "skipped": 0})
        d += dt.timedelta(days=1)
    return out


def test_day_stats_and_stages():
    st = LJ.day_stats(_days([0.01, -0.01, 0.02, 0.0]))
    assert st["days"] == 4 and st["trades"] == 40 and abs(st["mean"] - 0.005) < 1e-12 and st["win_days"] == 0.5
    assert abs(st["max_dd"] - 0.01) < 1e-12 and abs(st["cost_per_day"] - 0.004) < 1e-12 and st["trades_per_day"] == 10
    assert st["lo"] < 0 < st["hi"] and LJ.stage_from_forward(st) == 0
    assert LJ.day_stats([])["mean"] is None and LJ.stage_from_forward(LJ.day_stats([])) == 0
    good = LJ.day_stats(_days([0.012, 0.008, 0.011, 0.009] * 10))        # 下限 ≈ +0.95%
    assert LJ.stage_from_forward(good) == 2
    best = LJ.day_stats(_days([0.035, 0.031, 0.034, 0.032] * 10))        # 下限 > +3%
    assert LJ.stage_from_forward(best) == 4
    one = LJ.day_stats(_days([0.02]))
    assert one["lo"] == -LJ.math.inf and LJ.stage_from_forward(one) == 0


def test_gate_a_and_registration_rules():
    led = LJ.new_ledger()
    assert led["confirm_tests"] == 6
    LJ.register_round(led, "LP-01", "時間帯で入らない", "15〜16時だけ", "費用が重い時間を外す", variants=2, on="2026-10-02")
    assert led["confirm_tests"] == 8 and led["rounds"][0]["confirm_count_at_gate"] == 8
    for bad in (dict(variants=4), dict(mechanism=""), dict(reason="")):
        kw = dict(mechanism="x", change="y", reason="z"); kw.update(bad)
        try:
            LJ.register_round(led, "LP-02", kw["mechanism"], kw["change"], kw["reason"], variants=kw.get("variants", 1))
            raise AssertionError(f"通ってはいけない登録 {bad}")
        except ValueError:
            pass
    con_good = _days([0.004, 0.006, 0.005, 0.004] * 8)
    assert LJ.gate_a(LJ.day_stats(con_good), 0.001, 8) == (True, None)
    assert LJ.gate_a(LJ.day_stats(con_good), 0.01, 8) == (False, "placebo")          # 0.05÷8＝0.00625 より大きい
    assert LJ.gate_a(LJ.day_stats(_days([0.01, -0.01] * 8)), 0.001, 8) == (False, "confirm")
    LJ.record_backtest(led, "LP-01", _days([0.003] * 20), con_good, placebo_p=0.001)
    r = led["rounds"][0]
    assert r["status"] == "s0" and r["backtest"]["gate_a"] and r["backtest"]["p_needed"] == 0.00625
    try:
        LJ.record_backtest(led, "LP-01", [], [], 0.5)
        raise AssertionError("過去の計算を2回記録できた")
    except ValueError:
        pass


def _s0_round(led, rid):
    LJ.register_round(led, rid, "仕組み", "直し", "理由", on="2026-10-02")
    LJ.record_backtest(led, rid, _days([0.003] * 20), _days([0.004, 0.006, 0.005, 0.004] * 8), placebo_p=1e-4)
    assert led["rounds"][-1]["status"] == "s0"


def test_forward_window_and_stages():
    led = LJ.new_ledger()
    _s0_round(led, "LP-01")
    LJ.record_forward(led, "LP-01", _days([0.01, 0.012, 0.009], n=12), today="2026-10-10")
    r = led["rounds"][0]
    assert r["status"] == "forward" and r["forward"]["window"] == "continue" and r["stage"] == 0      # まだ3日
    LJ.record_forward(led, "LP-01", _days([0.012, 0.008, 0.011, 0.009, 0.012, 0.01], n=12), today="2026-10-14")
    assert r["status"] == "forward" and r["stage"] == 0                       # 6日72回＝窓の途中では段を上げない（幅が小さすぎる）
    LJ.record_forward(led, "LP-01", _days([0.012, 0.008, 0.011, 0.009] * 3, n=12), today="2026-10-20")
    assert r["status"] == "judged" and r["forward"]["window"] == "window_done" and r["stage"] == 2
    LJ.record_forward(led, "LP-01", _days([0.0, 0.0] * 6, n=12), today="2026-10-21")
    assert r["stage"] == 2                                                                            # 段は下がらない
    try:
        LJ.record_forward(led, "LP-99", [], today="x")
        raise AssertionError("無いラウンドに記録できた")
    except KeyError:
        pass
    fade = LJ.new_ledger()
    _s0_round(fade, "LP-01")
    LJ.record_forward(fade, "LP-01", _days([-0.01, -0.012, -0.009, -0.011, -0.01], n=8), today="2026-10-10")
    assert fade["rounds"][0]["status"] == "out" and fade["rounds"][0]["out_reason"] == "前向きで消えた" and fade["fwd_fails"] == 1
    flat = LJ.new_ledger()
    _s0_round(flat, "LP-01")
    LJ.record_forward(flat, "LP-01", _days([0.005, -0.005] * 5, n=12), today="2026-10-20")
    assert flat["rounds"][0]["out_reason"] == "前向きで段1に届かなかった" and flat["fwd_fails"] == 1


def test_stop_rules():
    led = LJ.new_ledger()
    for k in range(3):
        _s0_round(led, f"LP-0{k + 1}")
        LJ.record_forward(led, f"LP-0{k + 1}", _days([-0.01, -0.012, -0.009, -0.011, -0.01], n=8), today="x")
    assert led["status"] == "closed" and "3回続けて" in led["closed_reason"]
    try:
        LJ.register_round(led, "LP-04", "x", "y", "z")
        raise AssertionError("止めたループに登録できた")
    except ValueError:
        pass
    led2 = LJ.new_ledger()
    for k in range(12):
        LJ.register_round(led2, f"LP-{k + 1:02d}", "x", "y", "z", on="2026-10-02")
        LJ.record_backtest(led2, f"LP-{k + 1:02d}", _days([0.0] * 10), _days([0.01, -0.01] * 8), placebo_p=0.5)
        assert led2["rounds"][-1]["out_reason"] == "確かめ期間で費用後プラスでない"
    assert led2["status"] == "closed" and "12ラウンド" in led2["closed_reason"] and led2["confirm_tests"] == 18


def test_review_tables_and_render_without_money():
    t0 = _utc(2026, 10, 2, 6)                                              # 日本時間 15:00・金曜
    trades = [{"t": t0 + 600 * k, "r": r, "cost_r": c} for k, (r, c) in
              enumerate([(-1, 0.05), (-1, 0.15), (2, 0.25), (0.5, 0.15), (-1, 0.05), (-1, 0.05), (1, 0.05)])]
    tb = LJ.review_tables(trades)
    assert tb["by_hour_jst"]["15"]["n"] == 6 and tb["by_hour_jst"]["16"]["n"] == 1 and tb["by_weekday"]["4"]["n"] == 7
    assert tb["by_cost"]["費用 <0.10R"]["n"] == 4 and tb["after_losses"]["2連敗のあと"] == {"n": 2, "mean_r": 1.5}
    led = LJ.new_ledger()
    _s0_round(led, "LP-01")
    LJ.record_forward(led, "LP-01", _days([0.01, 0.012, 0.009], n=12), today="2026-10-10")
    md = LJ.render_md(led)
    assert "| LP-01 |" in md and "S0" in md and "投資助言ではありません" in md and "p＜0.0071" in md
    p = os.path.join(tempfile.mkdtemp(), "loop-ledger.json")
    LJ.save(led, p)
    assert LJ.load(p)["rounds"][0]["round"] == "LP-01" and LJ.load(p + ".none") is None
    led["rounds"][0]["balance"] = 1
    try:
        LJ.save(led, p)
        raise AssertionError("金額の項目を台帳に書けた")
    except ValueError:
        pass


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
