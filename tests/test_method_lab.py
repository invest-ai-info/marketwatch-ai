# -*- coding: utf-8 -*-
"""毎日の新しい方法（method_lab.py・research_rotation.py・method_lab_verify.py）のテスト。2026-11-17 新設。
作り物の値動きと作り物の記録だけを使う（本物の成績は見ない）。

実行:  python tests/test_method_lab.py     （pytest 不要。pytest でも動く）
"""
import contextlib
import io
import json
import os
import sys
import tempfile

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import method_lab as M  # noqa: E402
import method_lab_verify as V  # noqa: E402
import research_rotation as RR  # noqa: E402


def bars_from(rows, sym="TEST"):
    d = [f"2020-01-{i + 1:02d}" for i in range(len(rows))]
    o, h, l, c = zip(*rows)
    b = M.Bars(sym, d, o, h, l, c)
    b._cache["atr", 14] = np.full(len(rows), 1.0)      # ATR=1 → 損切り 1.5・利確 2.0
    return b


# ── 決まりが事前登録と同じか ──
def test_constants_match_the_registration():
    assert (M.EXPLORE_END, M.CONFIRM_START, M.MIN_N_EXPLORE, M.MIN_N_CONFIRM, M.P_MAX, M.MIN_PER_YEAR) == \
        ("2017-12-31", "2018-01-01", 100, 50, 0.05, 40)
    assert (M.PLACEBO_DRAWS, M.SL_MULT, M.K_DEFAULT) == (2000, 1.5, 48)
    assert (RR.CULL_MIN_N, RR.POOL_FLOOR, RR.MIN_N) == (30, 20, 80)
    text = open(os.path.join(ROOT, "PILLAR_PREREG.md"), encoding="utf-8").read()
    assert "## 毎日の新しい方法と入れ替え（2026-11-17" in text


# ── 入って出るまで ──
def test_long_take_profit():
    b = bars_from([(10, 10, 10, 10), (10, 10.5, 9.9, 10.2), (10.2, 12.1, 10.1, 12.0)] + [(12, 12, 12, 12)] * 3)
    R, held = b.outcome(1, "atr_tp")
    assert abs(R[0] - 2.0 / 1.5) < 1e-9 and held[0] == 2       # 入った値10・利確12・1R=1.5


def test_same_bar_both_counts_as_stop():
    b = bars_from([(10, 10, 10, 10), (10, 12.5, 8.0, 10.0)] + [(10, 10, 10, 10)] * 3)
    R, held = b.outcome(1, "atr_tp")
    assert abs(R[0] + 1.0) < 1e-9 and held[0] == 1


def test_gap_through_stop_exits_at_open():
    b = bars_from([(10, 10, 10, 10), (10, 10.2, 9.8, 10.0), (7.0, 7.5, 6.5, 7.2)] + [(7, 7, 7, 7)] * 3)
    R, _h = b.outcome(1, "atr_tp")
    assert abs(R[0] - (7.0 - 10) / 1.5) < 1e-9                 # 損切り 8.5 ではなく始値 7.0


def test_short_and_time_exit():
    b = bars_from([(10, 10, 10, 10), (10, 10.3, 9.7, 9.8), (9.8, 10.0, 9.5, 9.6), (9.6, 9.9, 9.4, 9.5)] + [(9.5,) * 4] * 2)
    R, held = b.outcome(-1, "hold_3")
    assert abs(R[0] - (10 - 9.5) / 1.5) < 1e-9 and held[0] == 3


def test_unfinished_trade_is_nan():
    b = bars_from([(10, 10, 10, 10), (10, 10.2, 9.9, 10.1)])
    R, held = b.outcome(1, "hold_5")
    assert np.isnan(R[0]) and held[0] == 0


def test_cost_is_subtracted_for_fx():
    b = bars_from([(150, 150, 150, 150), (150, 150.2, 149.9, 150.0)] + [(150,) * 4] * 2, sym="USDJPY=X")
    R, _h = b.outcome(1, "hold_1")
    assert abs(R[0] - (-(0.008 * 1.5) / 1.5)) < 1e-9


# ── 方法の形 ──
def test_spec_id_ignores_condition_order():
    a = {"direction": "long", "universe": "index", "conds": [["rsi_lt", 2, 10], ["above_ma", 200]], "exit": "hold_5"}
    b = {"direction": "long", "universe": "index", "conds": [["above_ma", 200], ["rsi_lt", 2, 10]], "exit": "hold_5"}
    assert M.spec_id(a) == M.spec_id(b) and M.spec_valid(a)
    assert not M.spec_valid({**a, "conds": [["rsi_lt", 2, 11]]})            # 引数は決まった候補だけ
    assert not M.spec_valid({**a, "exit": "hold_2"})
    assert "「RSI（2日）が10より下」" in M.spec_name(a) and M.spec_name(a).endswith("のときに買う")


def test_ideas_are_valid_and_unique():
    ideas = M.load_ideas()
    assert len(ideas) >= 30
    assert all(M.spec_valid(i["spec"]) and i.get("why") for i in ideas)
    assert len({M.spec_id(i["spec"]) for i in ideas}) == len(ideas)


def test_batch_is_deterministic_and_skips_tested():
    a = M.make_batch("2026-11-18", [], [], 48)
    b = M.make_batch("2026-11-18", [], [], 48)
    assert [M.spec_id(s) for _x, s, _w in a] == [M.spec_id(s) for _x, s, _w in b]
    assert len(a) == 48 and len({M.spec_id(s) for _x, s, _w in a}) == 48
    assert a[0][0] == "idea" and a[1][0] == "idea"
    tested = [M.spec_id(s) for _x, s, _w in a]
    c = M.make_batch("2026-11-18", tested, [], 48)
    assert not set(tested) & {M.spec_id(s) for _x, s, _w in c}
    parent = {"id": "p", "spec": M.load_ideas()[0]["spec"]}
    d = M.make_batch("2026-11-19", [], [parent], 48)
    assert sum(1 for x in d if x[0] == "mutation") == M.K_MUT


def test_non_overlap_and_since():
    rows = [(10 + 0.01 * i, 10.3 + 0.01 * i, 9.7 + 0.01 * i, 10 + 0.01 * i) for i in range(400)]
    b = M.Bars("ES=F", [f"2020-{1 + i // 28:02d}-{1 + i % 28:02d}" if i < 336 else f"2021-{1 + (i - 336) // 28:02d}-{1 + (i - 336) % 28:02d}"
                        for i in range(400)], *zip(*rows))
    spec = {"direction": "long", "universe": "index", "conds": [["above_ma", 50]], "exit": "hold_5"}
    trs = M.trades_of(spec, {"ES=F": b})
    ts = [t for _d, _s, t, _r in trs]
    assert ts and all(y - x >= 5 for x, y in zip(ts, ts[1:]))            # 持っている間は入らない
    later = M.trades_of(spec, {"ES=F": b}, since="2021-01-01")
    assert later and all(d >= "2021-01-01" for d, *_x in later)


def test_stats_and_screen():
    trs = [(f"2020-01-{i % 28 + 1:02d}", "X", i, r) for i, r in enumerate([1.0, -1.0, 0.5] * 20)]
    st = M.stats_of(trs)
    assert st["n"] == 60 and abs(st["mean"] - 1 / 6) < 1e-3 and st["lo"] < st["mean"] < st["hi"]
    good = {"explore": {"n": 120, "mean": 0.1, "placebo": {"p": 0.01}},
            "confirm": {"n": 60, "mean": 0.05, "placebo": {"excess": 0.01}, "per_year": 45}}
    assert all(M.screen(good).values())
    assert not M.screen({**good, "confirm": {**good["confirm"], "per_year": 39}})["frequency"]
    assert not M.screen({**good, "explore": {**good["explore"], "placebo": {"p": 0.06}}})["explore"]


def test_next_routine_date():
    import datetime as dt
    assert M.next_routine_date(dt.datetime(2026, 11, 17, 21, 0, tzinfo=M.JST)) == "2026-11-18"
    assert M.next_routine_date(dt.datetime(2026, 11, 18, 3, 0, tzinfo=M.JST)) == "2026-11-18"


# ── 入れ替え ──
def hyp(i, kind="edge", n=100, lo=-0.2, hi=0.1, **kw):
    return {"id": i, "kind": kind, "status": "tracking", "registered_at": "2026-07-01", "label": i,
            "filter": {"tf": "4h"}, "forward": {"n": n, "avgR": (lo + hi) / 2, "rci_lo": lo, "rci_hi": hi}, **kw}


def test_cull_picks_lowest_best_case_with_protections():
    tr = {"hypotheses": [hyp("a", hi=0.05), hyp("b", hi=-0.01, n=20),          # b は回数が足りない
                         hyp("c", hi=-0.05, pair="d"), hyp("d", hi=0.3, pair="c"),   # 対は外さない
                         hyp("e", hi=-0.02, promote_strikes=1),                      # 昇格の途中
                         hyp("g", kind="gate", lo=-0.03, hi=0.2)]                    # gate: 見込み=+0.03
                        + [hyp(f"z{i}", hi=0.5) for i in range(20)]}
    reg = {"methods": []}
    pool, active = RR.cull_pool(tr, reg)
    assert active == 26 and [r["id"] for r in pool[:2]] == ["g", "a"]
    w, _msg, _a = RR.cull_one(tr, reg, "2026-11-18")
    g = next(h for h in tr["hypotheses"] if h["id"] == "g")
    assert w["id"] == "g" and g["status"] == "retired" and g["retire_reason"] == "culled"
    assert w.get("flip_id") == "g__flip"                                           # 避けるはずが勝っていた→逆向きで登録
    fl = next(h for h in tr["hypotheses"] if h["id"] == "g__flip")
    assert fl["kind"] == "edge" and fl["filter"]["fired_from"] == "2026-11-19" and fl["status"] == "tracking"


def test_cull_floor():
    tr = {"hypotheses": [hyp(f"x{i}") for i in range(20)]}
    w, msg, _a = RR.cull_one(tr, {"methods": []}, "2026-11-18")
    assert w is None and "20" in msg


def test_method_promotion_needs_two_checkpoints_and_placebo():
    reg = {"methods": [{"id": "m1", "name": "m", "status": "tracking", "registered_at": "2026-01-01", "kind": "edge"}]}
    lab = {"forward": {"m1": {"n": 80, "mean": 0.3, "lo": 0.1, "hi": 0.5, "excess": 0.1}}}
    RR.judge_methods(reg, lab, "2026-06-01")
    assert reg["methods"][0]["status"] == "tracking" and reg["methods"][0]["promote_strikes"] == 1
    lab["forward"]["m1"].update(n=160, excess=-0.01)
    RR.judge_methods(reg, lab, "2026-08-01")
    assert reg["methods"][0]["promote_strikes"] == 0                         # 偽薬に負けた→やり直し
    lab["forward"]["m1"].update(n=240, excess=0.05)
    RR.judge_methods(reg, lab, "2026-10-01")
    lab["forward"]["m1"].update(n=320)
    ev = RR.judge_methods(reg, lab, "2026-12-01")
    assert reg["methods"][0]["status"] == "promoted" and ev[0][0] == "promoted"


def test_method_rejected_at_checkpoint():
    reg = {"methods": [{"id": "m1", "name": "m", "status": "tracking", "registered_at": "2026-01-01", "kind": "edge"}]}
    RR.judge_methods(reg, {"forward": {"m1": {"n": 85, "mean": -0.3, "lo": -0.5, "hi": -0.1, "excess": -0.2}}}, "2026-05-01")
    assert reg["methods"][0]["status"] == "rejected"


def test_register_only_passed():
    lab = {"batches": {"2026-11-18": {"chosen": {"id": "ml-1", "name": "n", "status": "near_miss", "spec": {"direction": "long"}}}}}
    reg = {"methods": []}
    rid, _msg = RR.register_today(reg, lab, "2026-11-18")
    assert rid is None and not reg["methods"]
    lab["batches"]["2026-11-18"]["chosen"]["status"] = "passed"
    rid, msg = RR.register_today(reg, lab, "2026-11-18")
    assert rid == "ml-1" and msg == "登録した" and reg["methods"][0]["registered_at"] == "2026-11-18"


# ── 記事の数字の検査 ──
BATCH = {"counts": {"tried": 48, "pass_explore": 3, "pass_confirm": 9, "pass_frequency": 11, "pass_all": 1,
                    "by_source": {"idea": 2, "mutation": 10, "random": 36}},
         "chosen": {"status": "passed", "id": "ml-1", "by_year": {"2024": [66, 0.376]},
                    "explore": {"n": 723, "mean": 0.195, "lo": 0.0987, "hi": 0.2912, "win": 0.5533,
                                "placebo": {"mean": 0.0475, "p": 0.0005, "excess": 0.1475, "z": 4.402}},
                    "confirm": {"n": 450, "mean": 0.0787, "lo": -0.05, "hi": 0.21, "win": 0.5289, "per_year": 50.7,
                                "placebo": {"mean": 0.0567, "p": 0.3058, "excess": 0.022, "z": 0.512}}}}


def run_verify(html, claims):
    with tempfile.TemporaryDirectory() as d:
        lab, reg = os.path.join(d, "method-lab.json"), os.path.join(d, "method-lab-registry.json")
        json.dump({"batches": {"2026-11-18": BATCH}}, open(lab, "w", encoding="utf-8"))
        json.dump({"culls": [{"date": "2026-11-18", "id": "x", "n": 194, "avgR": -0.17, "lo": -0.358, "hi": 0.018,
                              "score": 0.018, "pool_size": 36}]}, open(reg, "w", encoding="utf-8"))
        hp, cp = os.path.join(d, "a.html"), os.path.join(d, "c.json")
        open(hp, "w", encoding="utf-8").write(html)
        json.dump(claims, open(cp, "w", encoding="utf-8"))
        V.LAB_PATH, V.REG_PATH = lab, reg
        old = sys.argv
        sys.argv = ["x", hp, cp]
        out = io.StringIO()
        try:
            with contextlib.redirect_stdout(out):
                V.main()
        except SystemExit as e:
            code = e.code
        finally:
            sys.argv = old
            V.LAB_PATH = os.path.join(ROOT, "method-lab.json")
            V.REG_PATH = os.path.join(ROOT, "method-lab-registry.json")
        return code, out.getvalue()


MARKS = "".join(f"<!-- MW:{m} --><div data-mw-method-snippet=\"x\"><p>{m} 999回 +9.99R</p></div><!-- /MW:{m} -->"
                for m in V.MARKERS)
CLAIMS = {"article_id": "153", "method_date": "2026-11-18", "claims": [
    {"what": "method", "period": "explore", "field": "n", "value": 723},
    {"what": "method", "period": "explore", "field": "mean", "value": 0.20},
    {"what": "method", "period": "confirm", "field": "excess", "value": 0.02},
    {"what": "batch", "field": "tried", "value": 48},
    {"what": "cull", "field": "avgR", "value": -0.17},
    {"what": "year", "year": "2024", "field": "mean", "value": 0.38}]}
GOOD = ("<html><body><p>今日は48通りを試しました。過去の探す期間では723回で1回あたり平均 損切り幅の0.20倍のもうけ、"
        "確かめる期間ではでたらめとの差 +0.02。2024年は損切り幅の0.38倍のもうけ。"
        "たくさん試すと偶然よく見えるものが混じるので、前向きで確かめるために登録しました。"
        "外した方法は1回あたり平均 損切り幅の0.17倍の損でした。</p>" + MARKS + "</body></html>")


def test_verify_green():
    code, out = run_verify(GOOD, CLAIMS)
    assert code == 0, out


def test_verify_catches_wrong_and_unbacked_numbers():
    bad = json.loads(json.dumps(CLAIMS))
    bad["claims"][1]["value"] = 0.25
    code, out = run_verify(GOOD, bad)
    assert code == 1 and "主張 0.25" in out
    code, out = run_verify(GOOD.replace("0.38倍", "0.45倍"), CLAIMS)
    assert code == 1 and "出どころの無い数字" in out
    code, out = run_verify(GOOD.replace("0.17倍の損", "0.17倍のもうけ"), CLAIMS)    # もうけと損の取り違え
    assert code == 1 and "出どころの無い数字" in out
    code, out = run_verify(GOOD.replace("+0.02。", "+0.03。"), CLAIMS)
    assert code == 1 and "出どころの無い数字" in out


def test_verify_wording_and_requirements():
    code, out = run_verify(GOOD.replace("試しました。", "試しました。この方法がおすすめです。"), CLAIMS)
    assert code == 1 and "推奨" in out
    code, out = run_verify(GOOD.replace("偶然", "たまたま"), CLAIMS)
    assert code == 1 and "偶然" in out
    no_tried = json.loads(json.dumps(CLAIMS))
    no_tried["claims"] = [c for c in no_tried["claims"] if c["what"] != "batch"]
    code, out = run_verify(GOOD.replace("48通り", "たくさん"), no_tried)
    assert code == 1 and "ためした数" in out
    code, out = run_verify(GOOD.replace("<!-- MW:CULL_BOX -->", ""), CLAIMS)
    assert code == 1 and "CULL_BOX" in out


def test_snippets_are_plain_japanese():
    """差し込む表と箱は routine が直せない＝やさしい日本語の検査（固定）をそのまま通る形で出す。"""
    import check_plain_japanese as P
    tracker = {"hypotheses": [hyp(f"z{i}", hi=0.5) for i in range(3)]}
    reg = {"methods": [{"id": "ml-1", "name": "株価指数の5つで、「RSI（2日）が10より下」のときに買う", "status": "tracking",
                        "registered_at": "2026-11-18", "forward": {"n": 0, "avgR": None}}],
           "culls": [{"date": "2026-11-18", "id": "x", "name": "逆張り買い全般（4時間足のみ）", "kind": "edge", "source": "signal",
                      "registered_at": "2026-09-27", "n": 182, "avgR": -0.179, "lo": -0.398, "hi": 0.039, "pool_size": 36}]}
    day = {"cull_id": "x"}
    html = ("<html><head><title>t</title></head><body><main><p>ATR（ふだんの1日の値動きの幅）とRSI（相対力指数：上げ下げの勢い）。</p>"
            + RR.result_table(BATCH["chosen"]) + RR.batch_box(BATCH) + RR.cull_box(day, reg, "2026-11-18")
            + RR.research_list(tracker, reg) + "</main></body></html>")
    found = P.check_html(html)
    assert not found, found[:5]
    assert all(ja and "×" not in ja for ja in M.EXIT_JA.values())


if __name__ == "__main__":
    fails = 0
    tests = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for name, fn in tests:
        try:
            fn()
            print(f"  ✅ {name}")
        except Exception as e:  # noqa: BLE001
            fails += 1
            print(f"  ❌ {name}: {type(e).__name__}: {e}")
    print(f"--- {len(tests) - fails}/{len(tests)} 合格 ---")
    sys.exit(1 if fails else 0)
