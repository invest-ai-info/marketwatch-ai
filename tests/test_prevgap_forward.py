# -*- coding: utf-8 -*-
"""J17F 「寄りで買わない」目印の前向き（prevgap_forward.py）のテスト。2026-10-07 新設。

値動きはすべて作り物。確かめること＝①事前登録と定数の一致 ②朝の値（窓・前の日の値動き・寄り→9:30・除外）
③その銘柄だけの窓（その朝の中央値を引く・500銘柄未満の朝は数えない）と組 ④合計から行ごとの差を取り戻す・250営業日で1回だけ判定
⑤実行（登録の前と今日を数えない・一度数えた朝は数え直さない・取れない銘柄が5％超なら数えない）
⑥出力に銘柄コードを出さない・検証済みリストと研究の地図 ⑦ワークフロー・見張り番・SYNC 禁忌。

実行:  python tests/test_prevgap_forward.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import json
import os
import sys
import tempfile

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import prevgap_forward as F  # noqa: E402
import test_highs_trap_lab as TL  # noqa: E402  作り物の値段の道具を借りる

JST = TL.JST


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "## J17F 「寄りで買わない」目印の前向き" in text
    assert F.FWD_START == "2026-10-08" and "**2026-10-08 以降**" in text
    assert F.GOAL_DAYS == 250 and "250営業日〔約1年〕に届いた日に1回だけ" in text
    assert F.N_Q == 2 and abs(F.ALPHA - 0.025) < 1e-12 and "p＜0.05÷2＝97.5％ の幅" in text
    assert (F.IDIO, F.PREV_BIG, F.PREV_FLAT, F.MIN_STOCKS) == (0.01, 0.05, 0.02, 500) and "500未満の朝は数えない" in text
    assert F.ARMS == {"A": ("mid", "hi"), "B": ("base", "ovl")}
    rules = open("MY_TRADING_RULES.md", encoding="utf-8").read()
    assert "### ⑤ 寄り付きのゲート" in rules and "J17F" in rules


def _daily(days, opens, closes):
    return [(d, o, max(o, c) * 1.01, min(o, c) * 0.99, c, 1e5) for d, o, c in zip(days, opens, closes)]


def test_stock_mornings_values_and_exclusions():
    days = TL._bdays("2026-10-05", 5)                      # 10/5 月〜10/9 金
    daily = _daily(days, [100, 100, 106, 109, 100], [100, 106, 107, 100, 100])
    m5 = {d: TL._5m(d, [(daily[i][1],) * 4] * 6 + [(0, 0, 0, daily[i][1] * 0.99)] * 2) for i, d in enumerate(days)}
    got = F.stock_mornings(daily, m5, set(days[2:]))
    gap, rprev, r = got[days[2]]
    assert abs(gap - 0.0) < 1e-12 and abs(rprev - 0.06) < 1e-12 and r is not None      # 寄り 106 ÷ 前の日の終値 106
    assert abs(got[days[3]][0] - (109 / 107 - 1)) < 1e-12 and abs(got[days[3]][1] - (107 / 106 - 1)) < 1e-12
    far = [daily[0]] + [(d, *x[1:]) for d, x in zip(TL._bdays("2026-10-20", 4), daily[1:])]   # 前の日とその前の日が15日あく
    m5f = {x[0]: TL._5m(x[0], [(x[1],) * 4] * 8) for x in far}
    assert far[2][0] not in F.stock_mornings(far, m5f, {x[0] for x in far})
    assert F.stock_mornings(daily, {}, set(days)) == {}       # 5分足が無い朝は数えない


def test_groups_of():
    assert F.groups_of(0.0, 0.0) == ["mid", "base"] and F.groups_of(0.0, 0.03) == ["mid"]
    assert F.groups_of(0.015, 0.06) == ["hi", "ovl"] and F.groups_of(0.015, 0.0) == ["hi"] and F.groups_of(-0.02, 0.06) == []


def _rows(rng, n=520, a_eff=-0.003, b_extra=-0.004, mkt=None):
    mkt = rng.normal(0, 0.004) if mkt is None else mkt
    out = []
    for c in range(n):
        idio = rng.choice([0.0, 0.0, 0.015, -0.015, 0.003])
        rp = rng.choice([0.0, 0.01, 0.06, -0.03])
        r = rng.normal(0, 0.004) + (a_eff if idio >= 0.01 else 0) + (b_extra if idio >= 0.01 and rp >= 0.05 else 0)
        out.append((F.tag(f"QX{c}Z"), mkt + idio, rp, r))
    return out


def test_add_day_median_skip_and_points():
    rng = np.random.default_rng(1)
    st = F.empty_state()
    assert F.add_day(st, "2026-10-08", _rows(rng, n=499)) is False and st["days"] == {} and st["skipped"] == {"2026-10-08": 499}
    data = [(d, _rows(rng, mkt=0.012)) for d in TL._bdays("2026-10-08", 20)]   # 相場全体が +1.2％ 高く寄った朝
    for d, rows in data:
        assert F.add_day(st, d, rows)
    assert "2026-10-08" in st["days"] and st["skipped"] == {}                  # のちに数えられた朝は外す
    allr = [(gap - st["days"][d]["median_gap"], rp, r) for d, rows in data for _, gap, rp, r in rows]
    hi = np.mean([r for i, rp, r in allr if i >= 0.01])
    mid = np.mean([r for i, rp, r in allr if abs(i) < 0.01])
    ovl = np.mean([r for i, rp, r in allr if i >= 0.01 and rp >= 0.05])
    base = np.mean([r for i, rp, r in allr if abs(i) < 0.01 and abs(rp) < 0.02])
    ma, mb = F.measure(st, "A"), F.measure(st, "B")
    assert abs(ma["mean"] - (hi - mid)) < 1e-12 and abs(mb["mean"] - (ovl - base)) < 1e-12 and ma["lo"] < ma["mean"] < ma["hi"]
    assert abs(st["days"]["2026-10-09"]["median_gap"] - 0.012) < 1e-12             # 中央値＝相場全体の窓
    assert len(st["stocks"]) == 520 and all(len(k) == 10 for k in st["stocks"])


def test_single_verdict_at_250():
    rng = np.random.default_rng(2)
    days = TL._bdays("2026-10-08", 260)
    st = F.empty_state()
    for d in days:
        if F.done(st):
            break
        F.add_day(st, d, _rows(rng, n=520))
        F.after_day(st, d)
        if len(st["days"]) < 250:
            assert st["marker_verdicts"] == {}
    assert len(st["days"]) == 250 and F.done(st)
    a, b = st["marker_verdicts"]["A"], st["marker_verdicts"]["B"]
    assert a["status"] == b["status"] == "confirm" and a["decided_on"] == days[249] and a["hi"] < 0 and b["hi"] < 0
    st2 = F.empty_state()
    for d in days[:250]:
        F.add_day(st2, d, _rows(rng, n=520, a_eff=0.0, b_extra=0.0))
        F.after_day(st2, d)
    assert st2["marker_verdicts"]["A"]["status"] == "stop" and st2["marker_verdicts"]["B"]["status"] == "stop"


def _fetch_factory(days_all):
    def fetch(code, interval, rng):
        out, k = [], int(code) % 7
        for i, d in enumerate(days_all):
            o = 100.0 * (1.02 if (i + k) % 3 == 0 else 1.0)
            t = dt.datetime.combine(dt.date.fromisoformat(d), dt.time(9, 0), JST)
            if interval == "1d":
                out.append((t, o, o * 1.01, o * 0.98, 100.0, 1e5))
            else:
                for j in range(8):
                    out.append((t + dt.timedelta(minutes=5 * j), o, o, o, o * (1 - 0.001 * j), 1e3))
        return out
    return fetch


def test_run_counts_once_and_skips_before_start_and_today():
    days_all = TL._bdays("2026-10-01", 9)                  # 10/1〜10/13（平日）
    codes = [str(1000 + i) for i in range(520)]
    st = F.empty_state()
    today = days_all[7]
    added, missing = F.run(st, codes, _fetch_factory(days_all), today)
    assert missing == 0 and added == [d for d in days_all if "2026-10-08" <= d < today]
    again, _ = F.run(st, codes, _fetch_factory(days_all), today)
    assert again == []                                     # 一度数えた朝は数え直さない
    st3 = F.empty_state()
    fetch = _fetch_factory(days_all)
    none, miss = F.run(st3, codes, lambda c, i, r: [] if int(c) % 10 == 0 else fetch(c, i, r), today)
    assert none == [] and miss == 52 and st3["days"] == {}  # 取れない銘柄が5％超の回は1日も数えない


def test_outputs_verified_list_and_map():
    rng = np.random.default_rng(3)
    st = F.empty_state()
    for d in TL._bdays("2026-10-08", 12):
        F.add_day(st, d, _rows(rng))
    F.finalize(st)
    md = F.render_md(st, "x")
    out = json.dumps(st, ensure_ascii=False) + md
    assert not any(f"QX{c}Z" in out for c in range(520))  # 銘柄コードは残さない
    assert "目印A" in md and "目印B" in md and "観察中" in md and "投資助言ではありません" in md
    assert st["progress"]["A"] == st["summary"]["groups"]["hi"]["n"] and st["progress"]["B"] == st["summary"]["groups"]["ovl"]["n"]
    import verified_list as V
    import research_map as R
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "prevgap-forward.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(st, fh, ensure_ascii=False)
        assert V.collect([(path, "J17F", "J17F")]) == ([], [], [])          # 期待値の節には載せない
        mk = V.collect_markers([(path, "J17F", "J17F")])
        assert [r["id"] for r in mk] == ["A", "B"] and mk[1]["n"] == st["progress"]["B"]
    assert any(s[0] == "prevgap-forward.json" for s in V.MARKER_SOURCES) and R.PREVGAP_FWD == "prevgap-forward.json"


def test_workflow_health_and_sync_forbidden():
    wf = open(".github/workflows/prevgap-forward.yml", encoding="utf-8").read()
    assert "python prevgap_forward.py" in wf and "python verified_list.py" in wf
    assert "prevgap-forward.json prevgap-forward.md verified-list.md" in wf and "7 23 * * 0-4" in wf
    lint = open("check_site_consistency.py", encoding="utf-8").read()
    assert '"prevgap-forward.json", "prevgap-forward.md"' in lint
    health = open("check_automation_health.py", encoding="utf-8").read()
    assert '"prevgap-forward.yml", 24 * 4' in health


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
