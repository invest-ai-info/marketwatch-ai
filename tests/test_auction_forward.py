# -*- coding: utf-8 -*-
"""J31F 空売りの前向き（auction_forward.py）のテスト。2026-10-08 新設。

値動きはすべて作り物。確かめること＝①事前登録・点検表と定数の一致 ②朝の値（J31 と同じ prevday_lab の行・前の日の倍率・その日の高値）
③腕（B・C・10億円以上・損切り +10％ と滑り・費用）④合計から平均を取り戻す・60営業日ごとの見張り・250営業日で1回だけ判定
⑤実行（登録の前と今日を数えない・一度数えた朝は数え直さない・取れない銘柄が5％超なら数えない）
⑥出力に銘柄コードを出さない・検証済みリストと研究の地図 ⑦ワークフロー・見張り番・SYNC 禁忌。

実行:  python tests/test_auction_forward.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import json
import os
import sys
import tempfile

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))
os.chdir(ROOT)
import auction_forward as F  # noqa: E402
import prevday_lab as PD  # noqa: E402
import test_highs_trap_lab as TL  # noqa: E402  作り物の値段の道具を借りる

JST = TL.JST


def test_prereg_and_checklist_match_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "## J31F 空売りの前向き：目印 B・C の付いた株を寄り成行で売り、引け成行で買い戻す" in text
    assert F.FWD_START == "2026-10-09" and "**2026-10-09 以降**" in text and F.GOAL_DAYS == 250 and "**250営業日に届いた日に1回だけ**" in text
    assert F.N_Q == 4 and abs(F.ALPHA - 0.0125) < 1e-12 and "p＜0.05÷4＝98.75％" in text
    assert (F.TV_MIN, F.PREV_BIG, F.IDIO, F.TV_HIGH) == (10.0, 0.05, 0.01, 5.0) and F.MIN_STOCKS == 500
    assert (F.COST, F.STOP, F.SLIP) == (0.0003, 0.10, 0.002) and "−（10％ + 0.2％）− 0.03％" in text
    assert F.CHECK_EVERY == 60 and "60・120・180・240営業日" in text and F.ARMS == ("B0", "B10", "C0", "C10")
    rules = open("MY_TRADING_RULES.md", encoding="utf-8").read()
    assert "前の日に +5% 以上上げて" in rules and "20営業日の平均の5倍以上" in rules


def _daily(days, opens, highs, closes, vols):
    return [(d, o, h, min(o, c) * 0.99, c, v) for d, o, h, c, v in zip(days, opens, highs, closes, vols)]


def test_stock_mornings_match_the_research_rows():
    days = TL._bdays("2026-09-01", 32)
    closes = [1000.0] * 32
    closes[27] = 1060.0                                         # 28日目に +6%
    opens = [c for c in closes]
    opens[28] = 1060.0 * 1.03                                   # 29日目は +3% で寄る
    vols = [1e6] * 32
    vols[27] = 6e6                                              # 28日目の売買代金が6倍
    highs = [o * 1.02 for o in opens]
    closes[28] = opens[28] * 0.98
    daily = _daily(days, opens, highs, closes, vols)
    want = {days[28], days[29]}
    got = F.stock_mornings(daily, want)
    d = days[28]
    assert set(got) == {d for d in want if d >= F.FWD_START} and d >= F.FWD_START
    gap, rprev, ratio, tv, rc, rh = got[d]
    assert abs(gap - 0.03) < 1e-9 and abs(rprev - 0.06) < 1e-9 and abs(ratio - 6 * 1060 / 1000) < 1e-9
    assert abs(tv - 1060 * 6e6 / 1e8) < 1e-9 and abs(rc - (-0.02)) < 1e-9 and abs(rh - 0.02) < 1e-9
    A = PD.stock_rows(0, daily, {}, {}, first=F.FWD_START, last=days[29], recent_from=F.FAR)
    assert len(A) == len(got) == 2 and abs(A[0, PD.C["gap"]] - gap) < 1e-12 and abs(A[0, PD.C["rclose"]] - rc) < 1e-12
    assert F.stock_mornings(daily, set()) == {}


def test_arms_and_net():
    assert F.arms_of(0.02, 0.06, 6.0, 20.0) == ["B0", "B10", "C0", "C10", "BC0"]
    assert F.arms_of(0.02, 0.06, 1.0, 20.0) == ["B0", "B10"] and F.arms_of(0.0, 0.0, 5.0, 20.0) == ["C0", "C10"]
    assert F.arms_of(0.02, 0.06, 6.0, 9.9) == [] and F.arms_of(0.009, 0.06, float("nan"), 20.0) == []
    assert abs(F.arm_net("B0", 0.04, 0.12) - (-0.04 - F.COST)) < 1e-12
    assert abs(F.arm_net("B10", 0.04, 0.12) - (-(0.10 + 0.002) - F.COST)) < 1e-12
    assert abs(F.arm_net("C10", -0.03, 0.05) - (0.03 - F.COST)) < 1e-12


def _rows(rng, drift, n=520):
    """1つの朝の行：20％は B と C の両方（前の日 +6%・+4% で寄る・倍率 7・20億円）で drift だけ下がる"""
    out = []
    for c in range(n):
        hot = c % 5 == 0
        rc = (-drift if hot else 0.0) + rng.normal(0, 0.01)
        out.append((F.tag(f"QX{c}Z"), 0.04 if hot else rng.normal(0, 0.003), 0.06 if hot else 0.0, 7.0 if hot else 1.0, 20.0,
                    rc, max(rc, 0) + (0.11 if hot and c % 25 == 0 else 0.0)))
    return out


def test_add_day_skip_and_points():
    rng = np.random.default_rng(1)
    st = F.empty_state()
    assert not F.add_day(st, "2026-10-09", _rows(rng, 0.01)[:400]) and st["skipped"]["2026-10-09"] == 400
    assert F.add_day(st, "2026-10-09", _rows(rng, 0.01)) and "2026-10-09" not in st["skipped"]
    g = st["days"]["2026-10-09"]["g"]
    assert g["B0"][0] == g["C0"][0] == g["BC0"][0] == 104 and g["B10"][2] == 21
    assert g["B0"][1] / g["B0"][0] > 0.005 and len(st["stocks"]) == 104


def test_interim_stop_and_single_verdict():
    rng = np.random.default_rng(2)
    st = F.empty_state()
    for i, d in enumerate(TL._bdays("2026-10-09", F.GOAL_DAYS)):
        F.add_day(st, d, _rows(rng, 0.01))
        F.after_day(st, d)
    v = st["verdicts"]                                       # 損切りの腕は5回に1回 −10.2%＝平均がマイナスで60営業日に止まる
    assert v["B0"]["status"] == "plus" and v["C0"]["status"] == "plus" and v["B0"]["days"] == 250 and v["B0"]["lo"] > 0
    assert v["B10"]["days"] == 60 and "途中の見張り" in v["B10"]["reason"] and F.done(st) and len(st["interim"]) == 4 + 2 * 3
    st2 = F.empty_state()
    for d in TL._bdays("2026-10-09", 60):
        F.add_day(st2, d, _rows(rng, -0.01))
        F.after_day(st2, d)
    assert all(st2["verdicts"][k]["status"] == "stop" and "途中の見張り" in st2["verdicts"][k]["reason"] for k in F.ARMS)


def test_market_adjusted_reading_column():
    """2026-10-08 の追記：相場全体（10億円以上の平均）を差し引いた欄は読むだけ・判定は変えない"""
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "**読むための欄**として「相場全体を差し引いた数字」を足す" in text and F.MIN_BIG == 30
    rng = np.random.default_rng(5)
    rows = _rows(rng, 0.01)
    st = F.empty_state()
    F.add_day(st, "2026-10-09", rows)
    mkt = float(np.mean([r[5] for r in rows if r[4] >= F.TV_MIN]))
    day = st["days"]["2026-10-09"]
    assert abs(day["market"] - mkt) < 1e-12
    g = day["g"]["C0"]
    assert g[3] == g[0] and abs(g[4] - (g[1] + g[0] * mkt)) < 1e-9
    few = [(sid, gap, rp, ra, (20.0 if i < 29 else 1.0), rc, rh) for i, (sid, gap, rp, ra, tv, rc, rh) in enumerate(rows)]
    st2 = F.empty_state()
    F.add_day(st2, "2026-10-09", few)
    assert st2["days"]["2026-10-09"]["market"] is None and st2["days"]["2026-10-09"]["g"]["C0"][3] == 0
    old = F.empty_state()                                   # 追記の前の形（3つだけ）でも読める
    old["days"]["2026-10-09"] = {"g": {k: [2, 0.02, 0] for k in F.ARMS + F.EXTRA}, "n": 600}
    sm = F.summary(old)
    assert sm["arms"]["B0"]["mean"] == 0.01 and sm["arms"]["B0"]["adj"] is None
    F.finalize(st)
    assert "相場全体を差し引いた平均" in F.render_md(st, "x") and st["summary"]["arms"]["C0"]["adj"] is not None


def test_taishaku_reading_column():
    """2026-10-08 夕方の追記（J36 を受けて）：貸借銘柄だけの割合と平均は読むだけ・判定は変えない・一覧が無い朝は空けたまま"""
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "**読むための欄**として「貸借銘柄だけ」の数字を足す" in text and "`jp_taishaku.py`" in text
    rng = np.random.default_rng(6)
    rows = _rows(rng, 0.01)
    hot = [r for r in rows if r[3] >= F.TV_HIGH]
    tags = {r[0] for r in hot[::2]}                            # 目印の付いた株の半分が貸借銘柄
    st = F.empty_state()
    F.add_day(st, "2026-10-09", rows, {"tags": tags, "asof": "2026年10月1日現在"})
    g = st["days"]["2026-10-09"]["g"]["C0"]
    want = [F.arm_net("C0", r[5], r[6]) for r in hot if r[0] in tags]
    assert g[5] == len(want) == (len(hot) + 1) // 2 and abs(g[6] - sum(want)) < 1e-9
    assert st["days"]["2026-10-09"]["tai_asof"] == "2026年10月1日現在"
    F.add_day(st, "2026-10-13", _rows(rng, 0.01))             # 一覧が取れなかった朝＝貸借の欄は空けたまま
    assert st["days"]["2026-10-13"]["tai_asof"] is None and st["days"]["2026-10-13"]["g"]["C0"][5] == 0
    sm = F.summary(st)
    a = sm["arms"]["C0"]
    assert sm["tai_days"] == 1 and abs(a["tai_share"] - g[5] / g[0]) < 1e-12 and abs(a["tai_mean"] - sum(want) / len(want)) < 1e-12
    old = F.empty_state()                                      # 追記の前の形（5つ）でも読める
    old["days"]["2026-10-09"] = {"g": {k: [2, 0.02, 0, 2, 0.04] for k in F.ARMS + F.EXTRA}, "n": 600, "market": 0.01}
    assert F.summary(old)["arms"]["B0"]["tai_share"] is None and F.summary(old)["tai_asof"] is None
    F.finalize(st)
    md = F.render_md(st, "x")
    assert "貸借銘柄だけ：割合・平均（読むだけ）" in md and "一覧があった朝 1／2営業日" in md


def test_w6_reading_column():
    """2026-10-08 夕方(2)の追記（J38 を受けて）：目印B・貸借銘柄・その銘柄だけの窓 +6％以上だけ（読むだけ・一覧が無い朝は入れない）"""
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "「**目印B・貸借銘柄・その銘柄だけの窓 +6％以上**（損切りなし）」の回数と費用後の平均を足す" in text and F.W6 == 0.06
    rng = np.random.default_rng(7)
    rows = _rows(rng, 0.01)
    rows = [(sid, 0.08 if (i % 5 == 0 and i % 10 == 0) else gap, *rest) for i, (sid, gap, *rest) in enumerate(rows)]  # 目印の半分は +8％で寄る
    tags = {r[0] for i, r in enumerate(rows) if i % 20 == 0}                 # そのうち半分が貸借銘柄
    st = F.empty_state()
    F.add_day(st, "2026-10-09", rows, {"tags": tags, "asof": "x"})
    g = st["days"]["2026-10-09"]["g"]
    med = float(np.median([r[1] for r in rows]))
    want = [F.arm_net("B0", r[5], r[6]) for r in rows if r[0] in tags and r[1] - med >= F.W6 and r[2] >= F.PREV_BIG]
    assert g["BW6"][0] == len(want) == 26 and abs(g["BW6"][1] - sum(want)) < 1e-9 and g["B0"][0] == 104
    F.add_day(st, "2026-10-13", rows)                                          # 一覧が無い朝＝入れない
    assert st["days"]["2026-10-13"]["g"]["BW6"][0] == 0
    old = F.empty_state()                                                      # 追記より前の朝（BW6 の欄が無い）でも読める
    old["days"]["2026-10-09"] = {"g": {k: [2, 0.02, 0] for k in F.ARMS + ("BC0",)}, "n": 600}
    assert F.summary(old)["arms"]["BW6"]["n"] == 0 and F.summary(old)["arms"]["BW6"]["mean"] is None
    F.finalize(st)
    assert "目印B・貸借銘柄・その銘柄だけの窓 +6％以上（損切りなし・J38 で ✅ の箱" in F.render_md(st, "x")
    assert st["summary"]["arms"]["BW6"]["n"] == 26


def test_run_loads_the_list_only_when_there_are_new_mornings():
    days_all = TL._bdays("2026-09-01", 35)
    codes = [str(1000 + i) for i in range(520)]
    calls = []

    def loader():
        calls.append(1)
        return {"codes": {c for c in codes if int(c) % 2 == 0}, "asof": "2026年10月1日現在", "n": 260}
    st = F.empty_state()
    added, _ = F.run(st, codes, _fetch_factory(days_all), "2026-10-14", tai_loader=loader)
    assert added and len(calls) == 1 and all(st["days"][d]["tai_asof"] == "2026年10月1日現在" for d in added)
    assert sum(st["days"][d]["g"]["C0"][5] for d in added) > 0
    assert F.run(st, codes, _fetch_factory(days_all), "2026-10-14", tai_loader=loader)[0] == [] and len(calls) == 1
    st2 = F.empty_state()
    F.run(st2, codes, _fetch_factory(days_all), "2026-10-14")   # 一覧なし（既定）でも数える
    assert st2["days"] and all(v["tai_asof"] is None for v in st2["days"].values())


def _fetch_factory(days_all):
    def fetch(code, interval, rng):
        out, k = [], int(code) % 7
        for i, d in enumerate(days_all):
            c = 1000.0 * (1.06 if (i + k) % 5 == 0 else 1.0)
            o = c * (1.03 if (i + k) % 5 == 1 else 1.0)
            t = dt.datetime.combine(dt.date.fromisoformat(d), dt.time(9, 0), JST)
            out.append((t, o, o * 1.02, o * 0.97, o * 0.99, 2e6 * (10 if (i + k) % 10 == 0 else 1)))
        return out
    return fetch


def test_run_counts_once_and_skips_before_start_and_today():
    days_all = TL._bdays("2026-09-01", 35)
    codes = [str(1000 + i) for i in range(520)]
    st = F.empty_state()
    today = "2026-10-14"
    added, missing = F.run(st, codes, _fetch_factory(days_all), today)
    assert missing == 0 and added == [d for d in days_all if "2026-10-09" <= d < today]
    assert F.run(st, codes, _fetch_factory(days_all), today)[0] == []
    assert sum(st["days"][d]["g"]["C0"][0] for d in st["days"]) > 0
    st3 = F.empty_state()
    fetch = _fetch_factory(days_all)
    none, miss = F.run(st3, codes, lambda c, i, r: [] if int(c) % 10 == 0 else fetch(c, i, r), today)
    assert none == [] and miss == 52 and st3["days"] == {}


def test_outputs_verified_list_and_map():
    rng = np.random.default_rng(3)
    st = F.empty_state()
    for d in TL._bdays("2026-10-09", 12):
        F.add_day(st, d, _rows(rng, 0.01))
    F.finalize(st)
    md = F.render_md(st, "x")
    out = json.dumps(st, ensure_ascii=False) + md
    assert not any(f"QX{c}Z" in out for c in range(520))
    assert "観察中" in md and "投資助言ではありません" in md and "記録だけ" in md and "B かつ C" in md
    assert st["progress"]["B0"] == st["summary"]["arms"]["B0"]["n"]
    import verified_list as V
    import research_map as R
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "auction-forward.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(st, fh, ensure_ascii=False)
        stop, plus, watching = V.collect([(path, "J31F", "J31F")])
        assert stop == [] and plus == [] and [r["id"] for r in watching] == list(F.ARMS)
        m = R.collect(tmp)
        jp = [r for r in R.collect_studies(tmp, m)["verify"] if r["cat"] == "jp"]
        assert len(jp) == 1 and "空売り" in jp[0]["name"] and "12営業日" in jp[0]["progress"]
        assert not any(w in jp[0]["name"] + jp[0]["what"] for w in ("J31", "B0", "C10"))
    assert any(s[0] == "auction-forward.json" for s in V.SOURCES) and R.AUCTION_FWD == "auction-forward.json"


def test_workflow_health_and_sync_forbidden():
    wf = open(".github/workflows/auction-forward.yml", encoding="utf-8").read()
    assert "python auction_forward.py" in wf and "python verified_list.py" in wf
    assert "auction-forward.json auction-forward.md verified-list.md" in wf and "41 23 * * 0-4" in wf and "11 4 * * 1-5" in wf
    assert '"auction-forward.json", "auction-forward.md"' in open("check_site_consistency.py", encoding="utf-8").read()
    assert '"auction-forward.yml", 24 * 4' in open("check_automation_health.py", encoding="utf-8").read()


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
