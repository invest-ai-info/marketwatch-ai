# -*- coding: utf-8 -*-
"""J13F 窓の戻し・前向き（gap_forward.py）のテスト。2026-10-06 夜 新設。

値動きはすべて作り物（ネットワークに出ない）。確かめること＝①事前登録と定数の一致 ②朝の値の取り方（窓・9:30・除外）
③合計だけで幅を引き直せる（1行ずつの計算と同じ点）④一度数えた朝は数え直さない・開始日より前と今日は数えない
⑤腕B の途中の見張り・250営業日で1回だけの判定 ⑥検証済みリスト・研究の地図・出力に銘柄コードを出さない ⑦ワークフローと SYNC 禁忌。

実行:  python tests/test_gap_forward.py     （pytest 不要。pytest でも動く）
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
import gap_forward as F  # noqa: E402
import test_highs_trap_lab as TL  # noqa: E402  作り物の値段の道具を借りる

JST = TL.JST


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "## J13F 窓の戻し・前向き" in text
    assert F.FWD_START == "2026-10-07" and "**2026-10-07 以降**" in text
    assert F.GOAL_DAYS == 250 and "250営業日に届いた日に1回だけ判定" in text
    assert F.CHECK_EVERY == 60 and "60営業日ごと（60・120・180・240）" in text
    assert F.ALPHA == 0.05 and F.N_BOOT == 10000 and "95％ の幅" in text and "各10,000回" in text
    assert F.MIN_N == 30 and "30件未満なら「件数不足」" in text


def _daily(days, opens, closes):
    return [(d, o, max(o, c) * 1.01, min(o, c) * 0.99, c, 1e5) for d, o, c in zip(days, opens, closes)]


def test_stock_mornings_gap_930_and_exclusions():
    days = TL._bdays("2026-10-05", 4)                      # 10/5 月・10/6・10/7・10/8
    daily = _daily(days, [100, 100, 102, 97], [100, 100, 101, 98])
    m5 = {d: TL._5m(d, [(daily[i][1], daily[i][1], daily[i][1], daily[i][1])] * 6 + [(0, 0, 0, daily[i][1] * 0.99)] * 2)
          for i, d in enumerate(days)}
    got = F.stock_mornings(daily, m5, set(days[2:]))
    assert set(got) == {days[2], days[3]}
    g, r, tv = got[days[2]]
    assert abs(g - 0.02) < 1e-12 and abs(tv - 100 * 1e5 / 1e8) < 1e-12 and r is not None
    assert F.group_of(g) == ["up1"] and F.group_of(-0.031) == ["dn1", "dn3"] and F.group_of(0.0) == ["base"] and F.group_of(0.05) == ["up1", "up3"]
    bad = list(daily)
    bad[3] = (days[3], 150.0, 99.0, 96.0, 98.0, 1e5)       # 寄りが高値の外＝データの誤り
    assert days[3] not in F.stock_mornings(bad, m5, set(days[2:]))
    assert F.stock_mornings(daily, {}, set(days[2:])) == {}  # 5分足が無い朝は数えない


def _state_with(days_rows):
    st = F.empty_state()
    for day, rows in days_rows:
        F.add_day(st, day, rows)
    return st


def _fake_rows(rng, n_stocks=40, up_eff=-0.003, dn3_mean=0.003):
    rows = []
    for c in range(n_stocks):
        gap = rng.choice([0.0, 0.02, -0.04, -0.015, 0.035])
        r = rng.normal(0, 0.005) + (up_eff if gap >= 0.01 else 0) + (dn3_mean if gap <= -0.03 else 0)
        rows.append((F.tag(f"QX{c}Z"), gap, r, rng.choice([0.5, 5.0, 50.0])))
    return rows


def test_aggregates_reproduce_row_level_points():
    rng = np.random.default_rng(1)
    days = TL._bdays("2026-10-07", 30)
    data = [(d, _fake_rows(rng)) for d in days]
    st = _state_with(data)
    allr = [r for _, rows in data for r in rows]
    up = np.mean([r for _, g, r, _ in allr if g >= 0.01])
    base = np.mean([r for _, g, r, _ in allr if -0.01 < g < 0.01])
    dn3 = np.mean([r for _, g, r, _ in allr if g <= -0.03])
    m = F.measure(st, "A")
    assert abs(m["mean"] - (up - base)) < 1e-12 and m["lo"] < m["mean"] < m["hi"]
    assert abs(F.measure(st, "B")["mean"] - (dn3 - 0.001)) < 1e-12
    assert len(st["stocks"]) == 40 and all(len(k) == 10 for k in st["stocks"])


def test_interim_stop_and_single_verdict_at_250():
    rng = np.random.default_rng(2)
    days = TL._bdays("2026-10-07", 260)
    st = F.empty_state()
    for d in days[:60]:
        F.add_day(st, d, _fake_rows(rng, dn3_mean=-0.004))
        F.after_day(st, d)
    v = st["verdicts"].get("B")
    assert v and v["status"] == "stop" and "途中の見張り（60営業日）" in v["reason"] and st["interim"][0]["days"] == 60
    assert "A" not in st["marker_verdicts"]
    st2 = F.empty_state()
    for d in days:
        if F.done(st2):
            break
        F.add_day(st2, d, _fake_rows(rng))
        F.after_day(st2, d)
    assert len(st2["days"]) == 250 and F.done(st2)
    a, b = st2["marker_verdicts"]["A"], st2["verdicts"]["B"]
    assert a["status"] == "confirm" and a["decided_on"] == days[249] and a["hi"] < 0
    assert b["status"] == "plus" and b["lo"] > 0 and [x["days"] for x in st2["interim"]] == [60, 120, 180, 240]


def _fetch_factory(days_all, today_bar=True):
    def fetch(code, interval, rng):
        out = []
        for i, d in enumerate(days_all):
            o = 100.0 * (1.02 if (i % 3 == 0) else 1.0)
            t = dt.datetime.combine(dt.date.fromisoformat(d), dt.time(9, 0), JST)
            if interval == "1d":
                out.append((t, o, o * 1.01, o * 0.98, 100.0, 1e5))
            else:
                for j in range(8):
                    out.append((t + dt.timedelta(minutes=5 * j), o, o, o, o * (1 - 0.001 * j), 1e3))
        return out
    return fetch


def test_run_counts_once_and_skips_before_start_and_today():
    days_all = TL._bdays("2026-10-01", 8)                  # 10/1〜10/12（平日）
    st = F.empty_state()
    today = days_all[6]
    added, missing = F.run(st, ["1001", "1002", "1003"], _fetch_factory(days_all), today)
    assert missing == 0 and added == [d for d in days_all if "2026-10-07" <= d < today]
    again, _ = F.run(st, ["1001", "1002", "1003"], _fetch_factory(days_all), today)
    assert again == []                                     # 一度数えた朝は数え直さない
    later, _ = F.run(st, ["1001", "1002", "1003"], _fetch_factory(days_all), days_all[7])
    assert later == [days_all[6]]
    st3 = F.empty_state()
    none, miss = F.run(st3, ["1001", "1002"], lambda c, i, r: [] if c == "1002" else _fetch_factory(days_all)(c, i, r), today)
    assert none == [] and miss == 1 and st3["days"] == {}  # 取れない銘柄が5％超の回は1日も数えない


def test_outputs_verified_list_and_map():
    rng = np.random.default_rng(3)
    st = _state_with([(d, _fake_rows(rng)) for d in TL._bdays("2026-10-07", 12)])
    F.finalize(st)
    md = F.render_md(st, "x")
    out = json.dumps(st, ensure_ascii=False) + md
    assert not any(f"QX{c}Z" in out for c in range(40))     # 銘柄コードは残さない
    assert "腕A" in md and "腕B" in md and "観察中" in md and "投資助言ではありません" in md
    import verified_list as V
    import research_map as R
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "gap-forward.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(st, fh, ensure_ascii=False)
        stop, plus, watching = V.collect([(path, "J13F", "J13F")])
        assert [r["id"] for r in watching] == ["B"] and watching[0]["n"] == st["progress"]["B"] and not stop   # 腕B（J28 のあと見込みなしを取り消し）
        mk = V.collect_markers([(path, "J13F", "J13F")])
        assert [r["id"] for r in mk] == ["A"] and mk[0]["n"] == st["progress"]["A"]
        assert "目印あり" in "\n".join(V.render_markers(mk)) and "250営業日で判定" in "\n".join(V.render_markers(mk))
    assert ("gap-forward.json", "J13F 窓の戻し・前向き（全上場の毎朝・寄り→9:30）", "J13F") in V.SOURCES
    assert any(s[0] == "gap-forward.json" for s in V.MARKER_SOURCES)
    assert R.GAP_FWD == "gap-forward.json"


def test_workflow_health_and_sync_forbidden():
    wf = open(".github/workflows/gap-forward.yml", encoding="utf-8").read()
    assert "python gap_forward.py" in wf and "python verified_list.py" in wf
    assert "gap-forward.json gap-forward.md verified-list.md" in wf and "53 22 * * 0-4" in wf
    lint = open("check_site_consistency.py", encoding="utf-8").read()
    assert '"gap-forward.json", "gap-forward.md"' in lint
    health = open("check_automation_health.py", encoding="utf-8").read()
    assert '"gap-forward.yml", 24 * 4' in health


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
