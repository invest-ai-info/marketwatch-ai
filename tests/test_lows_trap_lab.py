# -*- coding: utf-8 -*-
"""J12 安値更新の翌朝、寄りで買うと戻るか、まだ下がるか（lows_trap_lab.py）のテスト。2026-10-06 新設。

値動きはすべて作り物（ネットワークに出ない）。確かめること＝①事前登録と定数の一致 ②安値更新がサイトの一覧（build_jp_highs の
side="low"）と同じ答え ③目印の値（窓・前の日の安値の下・下ヒゲ・前の日の下げ）④期間の覆いを確かめられない安値更新はどちらの組にも
入れない ⑤判定の向きと言葉 ⑥出力に銘柄コードを出さない ⑦ワークフローと SYNC 禁忌。

実行:  python tests/test_lows_trap_lab.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import json
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import build_jp_highs as H  # noqa: E402
import lows_trap_lab as L  # noqa: E402
import test_highs_trap_lab as TL  # noqa: E402  作り物の値段の道具を借りる


def _walk_down(n, seed, start="2023-10-02"):
    """下向きの作り物（ときどきデータの誤り＝前の日の半分以下の安値を混ぜる）"""
    rnd = random.Random(seed)
    c, out = 1000.0, []
    for d in TL._bdays(start, n):
        o = c * (1 + rnd.gauss(0, 0.01))
        c2 = o * (1 + rnd.gauss(-0.0005, 0.015))
        h = max(o, c2) * (1 + abs(rnd.gauss(0, 0.006)))
        lo = min(o, c2) * (1 - abs(rnd.gauss(0, 0.006)))
        if rnd.random() < 0.003:
            lo = c * 0.4
        out.append((d, o, h, lo, c2, 1e5))
        c = c2
    return out


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "## J12 安値更新の翌朝、寄りで買うと戻るか、まだ下がるか" in text
    assert L.GAP_DOWN == -0.01 and "Q1 窓が −1％ 以下" in text
    assert L.WICK == 0.5 and "（終値−安値）÷（高値−安値）が 0.5 以上" in text
    assert L.PREV_BIG == -0.05 and "Q4 前の日に −5％ 以下下げた" in text
    assert L.N_Q == 5 and abs(L.ALPHA - 0.01) < 1e-12 and "p＜0.05÷5＝99％ の幅" in text
    assert [b[0] for b in L.CROWD_BANDS] == ["1〜20銘柄", "21〜100銘柄", "101銘柄以上"] and "1〜20／21〜100／101以上" in text
    assert "安値更新の組にも比べる相手にも入れない" in text and "翌朝が 2026-10-05 までの日だけ" in text


def test_low_flags_match_build_jp_highs():
    total = 0
    for seed in range(6):
        daily = _walk_down(760, seed)
        bars = [(d, h, lo, c, v) for d, o, h, lo, c, v in daily]
        fast = L.ytd_low_flags(bars)
        slow = [k > 0 and H.ytd_extreme(bars[:k + 1], H.window_start(bars[k][0])[0], side="low") is not None for k in range(len(bars))]
        assert fast == slow, f"seed {seed}: {sum(fast)} vs {sum(slow)}"
        total += sum(fast)
    assert total > 30           # 作り物でも安値更新はそれなりに起きる（突き合わせが空振りしていない）


def _stock(event_close=90.0, event_high=99.0, event_low=86.0, next_open=88.0):
    """60営業日の横ばいのあと、ある日に安値を更新し、その翌朝を見る作り物"""
    days = TL._bdays("2026-06-01", 90)
    daily = [(d, 100.0, 101.0, 99.0, 100.0, 1e5) for d in days]
    k = 70
    daily[k] = (days[k], 99.0, event_high, event_low, event_close, 1e5)
    daily[k + 1] = (days[k + 1], next_open, next_open + 2, next_open - 1, next_open + 1, 1e5)    # 翌日は安値を更新しない（88 なら 87＞86）
    return days, daily, k


def test_stock_records_features_and_cover():
    days, daily, k = _stock()
    t = days[k + 1]
    m5 = {t: TL._5m(t, [(88, 89, 87, 88.5)] + [(88.5, 89, 88, 88.8)] * 7)}
    h1 = {t: TL._1h(t, [(9, 88, 89.76), (10, 89.76, 90)]), days[k + 2]: TL._1h(days[k + 2], [(9, 100, 101)])}
    ev, ctl = L.stock_records("9999", daily, m5, h1, covered=lambda d: True, end_day="2026-12-31")
    assert [r["date"] for r in ev] == [t] and ev[0]["low_day"] == days[k]
    r = ev[0]
    assert abs(r["gap"] - (88 / 90 - 1)) < 1e-12 and r["below_low"] is False      # 88 は前の日の安値 86 より上
    assert abs(r["wick"] - (90 - 86) / (99 - 86)) < 1e-12                         # 下ヒゲ 4/13
    assert abs(r["prev_ret"] - (90 / 100 - 1)) < 1e-12 and abs(r["turnover"] - 90 * 1e5 / 1e8) < 1e-9
    assert abs(r["r1000"] - (89.76 / 88 - 1)) < 1e-12 and r["r930"] is not None
    assert ctl["n1000"] == 1                                                      # 安値更新でない日（k+2）は比べる相手
    flags = {key: f(r) for key, _, f in L.FLAGS}
    assert flags == {"q1": True, "q2": False, "q3": False, "q4": True}
    ev, ctl = L.stock_records("9999", daily, m5, h1, covered=lambda d: False, end_day="2026-12-31")
    assert ev == [] and ctl["n1000"] == 1                                         # 確かめられない安値更新はどちらにも入らない
    days2, daily2, k2 = _stock(next_open=85.0)
    t2 = days2[k2 + 1]
    ev2, _ = L.stock_records("9999", daily2, {}, {t2: TL._1h(t2, [(9, 85, 86)])}, covered=lambda d: True, end_day="2026-12-31")
    assert ev2[0]["below_low"] is True                                            # 85 は前の日の安値 86 の下
    ev3, _ = L.stock_records("9999", daily, m5, h1, covered=lambda d: True, end_day=days[k])
    assert ev3 == []                                                              # 翌朝が end_day より後は数えない


def test_judges_both_ways():
    lo_ = {"lo": -0.004, "hi": -0.001, "n": 500}
    neg = {"mean": -0.002}
    assert L.judge_q0(lo_, neg, neg, {"n": 100, "mean": -0.001}).startswith("安値更新の翌朝の寄り買いは、平均で負けやすい兆し")
    hi_ = {"lo": 0.001, "hi": 0.004, "n": 500}
    pos = {"mean": 0.002}
    assert L.judge_q0(hi_, pos, pos, {"n": 100, "mean": 0.001}).startswith("安値更新の翌朝の寄り買いは、平均で勝ちやすい兆し")
    assert L.judge_q0(hi_, pos, neg, {"n": 100, "mean": 0.001}) == "見えない"
    full = {"n_a": 100, "n_b": 100, "lo": 0.001, "hi": 0.01}
    d = {"diff": 0.003}
    assert L.judge_flag(full, d, d, 0.002, {"n_a": 40, "n_b": 40, "diff": 0.001}) == "戻りの目印（兆し）"
    assert L.judge_flag(full, d, d, -0.002, {"n_a": 40, "n_b": 40, "diff": 0.001}) == "見えない"     # 目印ありが費用後プラスでない
    full_n = {"n_a": 100, "n_b": 100, "lo": -0.01, "hi": -0.001}
    dn = {"diff": -0.003}
    assert L.judge_flag(full_n, dn, dn, -0.002, {"n_a": 10, "n_b": 40, "diff": -0.001}).startswith("罠の目印（まだ下がる")


def test_analyze_and_render_have_no_codes():
    rnd = random.Random(9)
    ev = []
    for i in range(150):
        day = (dt.date(2024, 1, 8) + dt.timedelta(days=i)).isoformat()
        prev = (dt.date(2024, 1, 7) + dt.timedelta(days=i)).isoformat()
        for j in range(rnd.choice([3, 30, 120])):
            ev.append({"date": day, "low_day": prev, "code": f"Q{rnd.randrange(60)}Z", "r915": rnd.gauss(0, 0.01),
                       "r930": rnd.gauss(0, 0.01) if i > 90 else None, "r1000": rnd.gauss(0.001, 0.01), "rclose": rnd.gauss(0, 0.02),
                       "fb": False, "yoriten": None, "gap": rnd.gauss(-0.005, 0.015), "below_low": rnd.random() < 0.3,
                       "wick": rnd.random(), "prev_ret": rnd.gauss(-0.02, 0.03), "turnover": rnd.choice([0.3, 3.0, 30.0])})
    ctl = {"n930": 100, "s930": 0.1, "t930": 20, "n1000": 1000, "s1000": 0.5, "t1000": 150}
    big = frozenset({"Q1Z", "Q2Z"})
    res = {"generated_at": "x", "prereg_sha256": "0" * 64,
           "result": dict(L.analyze(ev, ctl, big), n_codes=3700, list_date="2026-09-30", n_missing={}, n_dropped=0)}
    md = L.render_md(res)
    out = json.dumps(res, ensure_ascii=False) + md
    assert not any(r["code"] in out for r in ev)
    assert "Q0 そもそも" in md and "Q1 窓が −1％ 以下" in md and "Q4 前の日に −5％ 以下下げた" in md and "投資助言ではありません" in md
    assert "その日に安値を更新した銘柄の数ごと" in md and "101銘柄以上" in md and "約400銘柄" in md
    rr = res["result"]
    assert rr["q0"]["verdict"] and all(rr["flags"][k]["verdict"] for k in ("q1", "q2", "q3", "q4"))
    assert sum(b["2y"]["n"] for b in rr["by_crowd"].values()) == rr["n_2y"]
    err = L.render_md({"generated_at": "x", "prereg_sha256": "", "result": {"error": "boom"}})
    assert "計算できず" in err and "## 判定" not in err


def test_workflow_and_sync_forbidden():
    wf = open(".github/workflows/lows-trap-lab.yml", encoding="utf-8").read()
    assert "python lows_trap_lab.py --diag" in wf and "openpyxl" in wf and "xlrd" in wf
    assert "lows-trap-lab.json lows-trap-lab.md" in wf
    lint = open("check_site_consistency.py", encoding="utf-8").read()
    assert '"lows-trap-lab.json", "lows-trap-lab.md"' in lint


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"✅ {name}")
            except AssertionError as e:
                fails += 1
                print(f"❌ {name}: {e}")
    sys.exit(1 if fails else 0)
