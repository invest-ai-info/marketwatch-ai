# -*- coding: utf-8 -*-
"""J25F 相場全体が安く寄った朝の深い下げ・前向き（market_dip_forward.py）のテスト。2026-10-07 新設。

値動きはすべて作り物。確かめること＝①事前登録と定数の一致 ②指値の付き方と費用 ③1銘柄の朝（窓は日足だけで・値動きは5分足と費用がそろった朝だけ）
④朝の足し方（中央値・500銘柄未満は数えない・安く寄った朝）⑤安く寄った朝が30朝に届いた日に1回だけ判定
⑥実行（登録の前と今日を数えない・数え直さない・取れない銘柄が5％超なら数えない）⑦出力に銘柄コードを出さない・検証済みリストと研究の地図
⑧ワークフロー・見張り番・SYNC 禁忌。

実行:  python tests/test_market_dip_forward.py     （pytest 不要。pytest でも動く）
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
import market_dip_forward as F  # noqa: E402
import test_highs_trap_lab as TL  # noqa: E402

JST = TL.JST


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "**J25F（前向き）**：**2026-10-08 以降の朝だけ**" in text and F.FWD_START == "2026-10-08"
    assert F.GOAL_DOWN_DAYS == 30 and "相場全体が安く寄った朝が30朝に届いた日に1回だけ判定" in text
    assert F.LEVELS == (0.05, 0.08, 0.10) and F.MKT_DOWN == -0.005 and F.MIN_STOCKS == 500
    assert abs(F.ALPHA - 0.05 / 6) < 1e-12 and F.KEYS == ("X5", "X8", "X10")


def test_limit_net():
    assert abs(F.limit_net(0.93, 0.90, 0.97, 0.002, 0.05) - (0.97 / 0.93 - 1 - 0.002)) < 1e-12   # 寄りで買えた
    assert abs(F.limit_net(1.0, 0.95 * 0.998, 0.97, 0.0001, 0.05) - (0.97 / 0.95 - 1 - 0.001)) < 1e-12   # 費用の下限 0.1％
    assert F.limit_net(1.0, 0.95, 0.97, 0.002, 0.05) is None                                      # ぴったりは買えない


def _daily(days, opens, closes, lows=None):
    lows = lows or [min(o, c) * 0.99 for o, c in zip(opens, closes)]
    return [(d, o, max(o, c) * 1.01, lo, c, 1e5) for d, o, c, lo in zip(days, opens, closes, lows)]


def test_stock_mornings():
    days = TL._bdays("2026-06-01", 90)
    opens = [100.0] * 90
    closes = [100.0 + (i % 3) * 0.3 for i in range(90)]
    opens[85] = 93.0
    daily = _daily(days, opens, closes)
    day = days[85]
    m5 = {day: TL._5m(day, [(93, 93.5, 90, 91), (91, 92, 90.5, 91.5)] + [(91.5, 96, 91, 95)] * 4)}
    got = F.stock_mornings(daily, m5, {day, days[86]})
    gap, nets = got[day]
    pc = closes[84]
    assert abs(gap - (93 / pc - 1)) < 1e-12 and nets is not None and len(nets) == 3
    assert nets[0] is not None and nets[2] is None                                               # −5％ は寄りで、−10％ は届かない
    assert got[days[86]][1] is None and abs(got[days[86]][0] - (100 / closes[85] - 1)) < 1e-12    # 5分足の無い朝も窓は数える


def _rows(rng, n=520, down=False, eff=0.02):
    out = []
    for c in range(n):
        gap = (-0.012 if down else 0.003) + rng.normal(0, 0.004)
        nets = tuple((rng.normal(eff if down else -0.01, 0.01) if rng.uniform() < 0.3 else None) for _ in F.LEVELS)
        out.append((F.tag(f"QX{c}Z"), gap, nets if c % 7 else None))
    return out


def test_add_day_and_single_verdict_at_30_down_days():
    rng = np.random.default_rng(1)
    st = F.empty_state()
    assert F.add_day(st, "2026-10-08", _rows(rng, n=499)) is False and st["skipped"] == {"2026-10-08": 499}
    days = TL._bdays("2026-10-08", 200)
    k = 0
    for i, d in enumerate(days):
        if F.done(st):
            break
        down = i % 4 == 0
        assert F.add_day(st, d, _rows(rng, down=down))
        assert st["days"][d]["down"] is down
        F.after_day(st, d)
        k += 1
        if len(F.down_days(st)) < F.GOAL_DOWN_DAYS:
            assert st["verdicts"] == {}
    assert len(F.down_days(st)) == 30 and F.done(st) and k == 117
    v = st["verdicts"]["X8"]
    assert v["status"] == "plus" and v["decided_on"] == days[116] and v["lo"] > 0 and v["q2"]["lo"] > 0
    st2 = F.empty_state()
    for i, d in enumerate(days[:117]):
        F.add_day(st2, d, _rows(rng, down=i % 4 == 0, eff=-0.01))
        F.after_day(st2, d)
    assert all(st2["verdicts"][k]["status"] == "stop" for k in F.KEYS)
    assert all(len(sid) == 10 for sid in st["stocks"])


def _fetch_factory(days_all):
    def fetch(code, interval, rng):
        out = []
        for i, d in enumerate(days_all):
            o = 100.0 * (0.99 if (i + int(code)) % 3 == 0 else 1.0)
            t = dt.datetime.combine(dt.date.fromisoformat(d), dt.time(9, 0), JST)
            if interval == "1d":
                out.append((t, o, o * 1.01, o * 0.98, 100.0, 1e5))
            else:
                for j in range(8):
                    out.append((t + dt.timedelta(minutes=5 * j), o, o, o * 0.999, o, 1e3))
        return out
    return fetch


def test_run_counts_once_and_skips():
    days_all = TL._bdays("2026-10-01", 9)
    codes = [str(1000 + i) for i in range(520)]
    st = F.empty_state()
    today = days_all[7]
    added, missing = F.run(st, codes, _fetch_factory(days_all), today)
    assert missing == 0 and added == [d for d in days_all if "2026-10-08" <= d < today]
    assert F.run(st, codes, _fetch_factory(days_all), today)[0] == []
    st3 = F.empty_state()
    fetch = _fetch_factory(days_all)
    none, miss = F.run(st3, codes, lambda c, i, r: [] if int(c) % 10 == 0 else fetch(c, i, r), today)
    assert none == [] and miss == 52 and st3["days"] == {}


def test_outputs_verified_list_and_map():
    rng = np.random.default_rng(3)
    st = F.empty_state()
    for i, d in enumerate(TL._bdays("2026-10-08", 12)):
        F.add_day(st, d, _rows(rng, down=i % 3 == 0))
    F.finalize(st)
    md = F.render_md(st, "x")
    out = json.dumps(st, ensure_ascii=False) + md
    assert not any(f"QX{c}Z" in out for c in range(520))
    assert "観察中" in md and "投資助言ではありません" in md and st["progress"]["X8"] == st["summary"]["groups"]["down_X8"]["n"]
    import verified_list as V
    import research_map as R
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "market-dip-forward.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(st, fh, ensure_ascii=False)
        stop, plus, watching = V.collect([(path, "J25F", "J25F")])
        assert stop == [] and plus == [] and [r["id"] for r in watching] == list(F.KEYS)
        assert watching[1]["n"] == st["progress"]["X8"]
    assert any(s[0] == "market-dip-forward.json" for s in V.SOURCES) and R.MARKET_DIP_FWD == "market-dip-forward.json"


def test_workflow_health_and_sync_forbidden():
    wf = open(".github/workflows/market-dip-forward.yml", encoding="utf-8").read()
    assert "python market_dip_forward.py" in wf and "python verified_list.py" in wf
    assert "market-dip-forward.json market-dip-forward.md verified-list.md" in wf and "19 23 * * 0-4" in wf
    assert '"market-dip-forward.json", "market-dip-forward.md"' in open("check_site_consistency.py", encoding="utf-8").read()
    assert '"market-dip-forward.yml", 24 * 4' in open("check_automation_health.py", encoding="utf-8").read()


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
