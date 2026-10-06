# -*- coding: utf-8 -*-
"""J11 J10 の罠の目印は約400銘柄の外の株でも成り立つか（highs_trap_small.py）のテスト。2026-10-06 新設。

値動きはすべて作り物（ネットワークに出ない）。確かめること＝①事前登録と定数の一致 ②約400を除く ③期間の覆いを確かめられない
高値更新はどちらの組にも入れず、高値更新でない日は比べる相手に入れる ④判定と出力（銘柄コードを出さない） ⑤ワークフローと SYNC 禁忌。

実行:  python tests/test_highs_trap_small.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import json
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import highs_trap_small as S  # noqa: E402
import test_highs_trap_lab as TL  # noqa: E402  作り物の値段の道具を借りる


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "## J11 J10 の罠の目印は、約400銘柄の外の株でも成り立つか" in text
    assert S.N_Q == 2 and abs(S.ALPHA - 0.025) < 1e-12 and "p＜0.05÷2＝97.5％ の幅" in text
    assert [b[0] for b in S.TURNOVER_BANDS] == ["1億円未満", "1〜10億円", "10億円以上"] and "1億円未満／1〜10億円／10億円以上" in text
    assert "高値更新の組にも比べる相手にも入れない" in text and "`build_jp_highs.window_covered`" in text


def test_universe_drops_the_400():
    info = json.load(open("jp-stock-info.json", encoding="utf-8"))["stocks"]
    one_big = next(iter(info))
    fake = lambda: ({one_big: {"name": "x"}, "9999": {"name": "y"}, "1001": {"name": "z"}}, "2026-09-30")  # noqa: E731
    u, d, n = S.universe(load=fake)
    assert set(u) == {"9999", "1001"} and d == "2026-09-30" and n == 3


def test_uncovered_highs_go_nowhere_and_plain_days_go_to_control():
    days, daily, k = TL._stock()
    t = days[k + 1]
    h1 = {t: TL._1h(t, [(9, 112, 109.2)]), days[k + 2]: TL._1h(days[k + 2], [(9, 100, 101)])}
    ev, ctl = S.stock_records("9999", daily, {}, h1, covered=lambda d: True, end_day="2026-12-31")
    assert [r["date"] for r in ev] == [t] and ctl["n1000"] == 1 and abs(ev[0]["turnover"] - 110 * 1e5 / 1e8) < 1e-9
    ev, ctl = S.stock_records("9999", daily, {}, h1, covered=lambda d: False, end_day="2026-12-31")
    assert ev == [] and ctl["n1000"] == 1                                   # 確かめられない高値更新はどちらにも入らない


def test_analyze_and_render_have_no_codes():
    rnd = random.Random(9)
    ev = []
    for i in range(150):
        day = (dt.date(2024, 1, 8) + dt.timedelta(days=i)).isoformat()
        for j in range(8):
            ev.append({"date": day, "code": f"Q{rnd.randrange(60)}Z", "r915": rnd.gauss(0, 0.01), "r930": rnd.gauss(0, 0.01) if i > 90 else None,
                       "r1000": rnd.gauss(-0.001, 0.01), "rclose": rnd.gauss(0, 0.02), "fb": False, "yoriten": None,
                       "gap": rnd.gauss(0.005, 0.01), "above_high": rnd.random() < 0.4, "wick": rnd.random(),
                       "prev_ret": rnd.gauss(0.02, 0.03), "turnover": rnd.choice([0.3, 3.0, 30.0])})
    ctl = {"n930": 100, "s930": 0.1, "t930": 20, "n1000": 1000, "s1000": 0.5, "t1000": 150}
    res = {"generated_at": "x", "prereg_sha256": "0" * 64,
           "result": dict(S.analyze(ev, ctl), n_codes=3300, n_listed=3700, list_date="2026-09-30", n_missing={}, n_dropped=0)}
    md = S.render_md(res)
    out = json.dumps(res, ensure_ascii=False) + md
    assert not any(r["code"] in out for r in ev)
    assert "Q0 そもそも" in md and "Q1 窓が +1％ 以上" in md and "前の日の売買代金ごと" in md and "投資助言ではありません" in md
    assert res["result"]["q0"]["verdict"] and res["result"]["q1"]["verdict"]


def test_workflow_and_sync_forbidden():
    wf = open(".github/workflows/highs-trap-small.yml", encoding="utf-8").read()
    assert "python highs_trap_small.py --diag" in wf and "openpyxl" in wf and "xlrd" in wf
    assert "highs-trap-small.json highs-trap-small.md" in wf
    lint = open("check_site_consistency.py", encoding="utf-8").read()
    assert '"highs-trap-small.json", "highs-trap-small.md"' in lint


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
