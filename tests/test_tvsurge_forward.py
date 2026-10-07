# -*- coding: utf-8 -*-
"""J26F 目印C「前の日の売買代金の急増」の前向き（tvsurge_forward.py）のテスト。2026-10-07 夜 新設。

値動きはすべて作り物。確かめること＝①事前登録・点検表と定数の一致 ②朝の値（J17F と同じ窓・寄り→9:30 と、前の日の売買代金の倍率）
③組（5倍以上・2倍未満・ふつうに寄った朝・倍率がそろわない朝は組に入れないが中央値には入れる）④合計から差を取り戻す・250営業日で1回だけ判定
⑤実行（登録の前と今日を数えない・一度数えた朝は数え直さない・取れない銘柄が5％超なら数えない）
⑥出力に銘柄コードを出さない・検証済みリストと研究の地図 ⑦ワークフロー・見張り番・SYNC 禁忌。

実行:  python tests/test_tvsurge_forward.py     （pytest 不要。pytest でも動く）
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
import prevgap_forward as PGF  # noqa: E402
import tvsurge_forward as F  # noqa: E402
import test_highs_trap_lab as TL  # noqa: E402  作り物の値段の道具を借りる

JST = TL.JST


def test_prereg_and_checklist_match_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "## J26F 目印C「前の日の売買代金の急増」の前向き" in text
    assert F.FWD_START == "2026-10-08" and F.GOAL_DAYS == 250 and "**2026-10-08 以降**" in text
    assert "**数えた朝が250営業日に届いた日に1回だけ**" in text and "97.5％の幅（p＜0.05÷2" in text
    assert F.N_Q == 2 and abs(F.ALPHA - 0.025) < 1e-12
    assert (F.TV_HIGH, F.TV_LOW, F.IDIO, F.MIN_STOCKS) == (5.0, 2.0, 0.01, 500)
    assert "**5倍以上** − **2倍未満**" in text and F.ARMS == {"C": ("lo", "hi"), "C2": ("lo_mid", "hi_mid")}
    rules = open("MY_TRADING_RULES.md", encoding="utf-8").read()
    sec = rules.split("### ⑤ 寄り付きのゲート", 1)[1].split("\n---", 1)[0]
    assert "🚫 **C：前の日の売買代金が、その前の20営業日の平均の5倍以上 → 寄りでは買わない**" in sec and "J26F" in sec


def _daily(days, closes, vols):
    return [(d, c, c * 1.01, c * 0.99, c, v) for d, c, v in zip(days, closes, vols)]


def test_stock_mornings_add_the_ratio_of_the_day_before():
    days = TL._bdays("2026-08-03", 30)
    vols = [1e5] * 30
    vols[25] = 8e5                                            # 26日目に売買代金が約8倍
    daily = _daily(days, [100.0] * 30, vols)
    m5 = {d: TL._5m(d, [(100.0,) * 4] * 6 + [(0, 0, 0, 99.0)] * 2) for d in days}
    want = set(days[24:28])
    got = F.stock_mornings(daily, m5, want)
    base = PGF.stock_mornings(daily, m5, want)
    assert set(got) == set(base) and all(got[d][0] == base[d][0] and got[d][2] == base[d][2] for d in got)   # 窓と値は J17F と同じ
    assert abs(got[days[26]][1] - 8.0) < 1e-9 and abs(got[days[27]][1] - 1e5 / ((19 * 1e5 + 8e5) / 20)) < 1e-9
    early = F.stock_mornings(daily, m5, set(days[3:6]))
    assert all(np.isnan(v[1]) for v in early.values())         # 20営業日そろう前は倍率なし
    assert F.stock_mornings(daily, {}, want) == {}


def test_groups_of():
    assert F.groups_of(0.0, 6.0) == ["hi", "hi_mid"] and F.groups_of(0.02, 6.0) == ["hi"]
    assert F.groups_of(0.0, 1.0) == ["lo", "lo_mid"] and F.groups_of(-0.03, 1.5) == ["lo"]
    assert F.groups_of(0.0, 3.0) == [] and F.groups_of(0.0, float("nan")) == []


def _rows(rng, n=520, mkt=0.0, eff=-0.004, eff_mid=-0.003):
    out = []
    for c in range(n):
        ratio = rng.choice([1.0, 3.0, 6.0, np.nan], p=[0.6, 0.2, 0.15, 0.05])
        gap = mkt + rng.normal(0, 0.012)
        mid = abs(gap - mkt) < 0.01
        r = rng.normal(0, 0.006) + (eff if ratio >= 5 else 0) + (eff_mid - eff if ratio >= 5 and mid else 0)
        out.append((F.tag(f"QX{c}Z"), gap, ratio, r))
    return out


def test_add_day_median_skip_and_points():
    rng = np.random.default_rng(1)
    st = F.empty_state()
    assert F.add_day(st, "2026-10-08", _rows(rng, n=499)) is False and st["skipped"] == {"2026-10-08": 499}
    data = [(d, _rows(rng, mkt=0.008)) for d in TL._bdays("2026-10-08", 20)]
    for d, rows in data:
        assert F.add_day(st, d, rows)
    assert st["skipped"] == {} and abs(st["days"]["2026-10-09"]["median_gap"] - float(np.median([g for _, g, _, _ in data[1][1]]))) < 1e-15
    allr = [(gap - st["days"][d]["median_gap"], ra, r) for d, rows in data for _, gap, ra, r in rows]
    hi = np.mean([r for i, ra, r in allr if ra >= 5])
    lo = np.mean([r for i, ra, r in allr if ra < 2])
    hi_m = np.mean([r for i, ra, r in allr if ra >= 5 and abs(i) < 0.01])
    lo_m = np.mean([r for i, ra, r in allr if ra < 2 and abs(i) < 0.01])
    mc, m2 = F.measure(st, "C"), F.measure(st, "C2")
    assert abs(mc["mean"] - (hi - lo)) < 1e-12 and abs(m2["mean"] - (hi_m - lo_m)) < 1e-12 and mc["lo"] < mc["mean"] < mc["hi"]
    assert len(st["stocks"]) <= 520 and all(len(k) == 10 for k in st["stocks"])


def test_single_verdict_at_250():
    rng = np.random.default_rng(2)
    days = TL._bdays("2026-10-08", 260)
    st = F.empty_state()
    for d in days:
        if F.done(st):
            break
        F.add_day(st, d, _rows(rng))
        F.after_day(st, d)
        if len(st["days"]) < 250:
            assert st["marker_verdicts"] == {}
    assert len(st["days"]) == 250 and F.done(st)
    c, c2 = st["marker_verdicts"]["C"], st["marker_verdicts"]["C2"]
    assert c["status"] == c2["status"] == "confirm" and c["decided_on"] == days[249] and c["hi"] < 0
    st2 = F.empty_state()
    for d in days[:250]:
        F.add_day(st2, d, _rows(rng, eff=0.0, eff_mid=0.0))
        F.after_day(st2, d)
    assert st2["marker_verdicts"]["C"]["status"] == "stop" and st2["marker_verdicts"]["C2"]["status"] == "stop"


def _fetch_factory(days_all):
    def fetch(code, interval, rng):
        out, k = [], int(code) % 7
        for i, d in enumerate(days_all):
            o = 100.0 * (1.02 if (i + k) % 3 == 0 else 1.0)
            t = dt.datetime.combine(dt.date.fromisoformat(d), dt.time(9, 0), JST)
            if interval == "1d":
                out.append((t, o, o * 1.01, o * 0.98, 100.0, 1e5 * (10 if (i + k) % 10 == 0 else 1)))   # 10営業日ごとに10倍＝倍率は約5.3
            else:
                for j in range(8):
                    out.append((t + dt.timedelta(minutes=5 * j), o, o, o, o * (1 - 0.001 * j), 1e3))
        return out
    return fetch


def test_run_counts_once_and_skips_before_start_and_today():
    days_all = TL._bdays("2026-09-01", 35)                 # 9/1〜10/17（平日）＝倍率の20営業日がそろう
    codes = [str(1000 + i) for i in range(520)]
    st = F.empty_state()
    today = "2026-10-14"
    added, missing = F.run(st, codes, _fetch_factory(days_all), today)
    assert missing == 0 and added == [d for d in days_all if "2026-10-08" <= d < today]
    assert F.run(st, codes, _fetch_factory(days_all), today)[0] == []          # 一度数えた朝は数え直さない
    assert sum(st["days"][d]["g"]["hi"][0] for d in st["days"]) > 0
    st3 = F.empty_state()
    fetch = _fetch_factory(days_all)
    none, miss = F.run(st3, codes, lambda c, i, r: [] if int(c) % 10 == 0 else fetch(c, i, r), today)
    assert none == [] and miss == 52 and st3["days"] == {}


def test_outputs_verified_list_and_map():
    rng = np.random.default_rng(3)
    st = F.empty_state()
    for d in TL._bdays("2026-10-08", 12):
        F.add_day(st, d, _rows(rng))
    F.finalize(st)
    md = F.render_md(st, "x")
    out = json.dumps(st, ensure_ascii=False) + md
    assert not any(f"QX{c}Z" in out for c in range(520))
    assert "目印C" in md and "目印C2" in md and "観察中" in md and "投資助言ではありません" in md
    assert st["progress"]["C"] == st["summary"]["groups"]["hi"]["n"] and st["progress"]["C2"] == st["summary"]["groups"]["hi_mid"]["n"]
    import verified_list as V
    import research_map as R
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "tvsurge-forward.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(st, fh, ensure_ascii=False)
        assert V.collect([(path, "J26F", "J26F")]) == ([], [], [])
        mk = V.collect_markers([(path, "J26F", "J26F")])
        assert [r["id"] for r in mk] == ["C", "C2"] and mk[0]["n"] == st["progress"]["C"]
        m = R.collect(tmp)
        jp = [r for r in R.collect_studies(tmp, m)["verify"] if r["cat"] == "jp"]
        assert [r["name"] for r in jp] == ["「寄りで買わない」目印C：前の日に売買代金が急に増えた日本株"] and "12営業日" in jp[0]["progress"]
    assert any(s[0] == "tvsurge-forward.json" for s in V.MARKER_SOURCES) and R.TVSURGE_FWD == "tvsurge-forward.json"


def test_workflow_health_and_sync_forbidden():
    wf = open(".github/workflows/tvsurge-forward.yml", encoding="utf-8").read()
    assert "python tvsurge_forward.py" in wf and "python verified_list.py" in wf
    assert "tvsurge-forward.json tvsurge-forward.md verified-list.md" in wf and "33 23 * * 0-4" in wf and "53 3 * * 1-5" in wf
    assert '"tvsurge-forward.json", "tvsurge-forward.md"' in open("check_site_consistency.py", encoding="utf-8").read()
    assert '"tvsurge-forward.yml", 24 * 4' in open("check_automation_health.py", encoding="utf-8").read()


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
