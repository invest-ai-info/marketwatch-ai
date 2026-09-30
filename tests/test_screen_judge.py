# -*- coding: utf-8 -*-
"""総当たりのふるい分けの判定（screen_judge.py）と、昇格リスト・検証済みリストのテスト。2026-09-30 新設（M6）。

取引はすべて作り物（ネットワークに出ない）。確かめること＝①事前登録と定数の一致 ②幅の式（週ごとのまとまり）
③多重検定（これまでの総数で割る）④落ちた理由の順番と、ラウンド1は6,144通りすべてを渡すこと ⑤偽薬
⑥記録（ラウンドの判定は変えない・やり直しは理由つき・2回目のラウンドは総数が増える）
⑦MT5 の確かめと前向き（300回でマイナスはストップ・1000回で判定）⑧2つのリストの組み立て ⑨ワークフローと SYNC禁忌。

実行:  python tests/test_screen_judge.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import json
import math
import os
import sys
import tempfile

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import promotion_list as P  # noqa: E402
import screen_judge as J  # noqa: E402
import verified_list as V  # noqa: E402

WEEKDAYS = [dt.date(2022, 6, 1) + dt.timedelta(days=i) for i in range((dt.date(2026, 9, 24) - dt.date(2022, 6, 1)).days + 1)]
WEEKDAYS = [d for d in WEEKDAYS if d.weekday() < 5]


def _trades(n, mean, a=1.0, mean2=None):
    """期間いっぱいに並べた n 回の取引。ぶれは週ごとに＋と−が入れ替わる（同じ週は同じ向き）。mean2＝後半だけの平均"""
    idx = np.linspace(0, len(WEEKDAYS) - 1, n).astype(int)
    dates = [WEEKDAYS[i].isoformat() for i in idx]
    r = []
    for d in dates:
        wk = dt.date.fromisoformat(d).isocalendar()[1]
        m = mean2 if (mean2 is not None and d >= J.HALF) else mean
        r.append(m + a * (1 if wk % 2 == 0 else -1))
    return {"r": r, "date": dates, "pips": [x * 10 for x in r]}


def _round1(special):
    combos = {}
    for tf in J.TFS:
        for e in range(1, 33):
            for s in range(8):
                for p in range(8):
                    combos[f"M6-{tf}-E{e:02d}-S{s}P{p}"] = {"r": [], "date": []}
    combos.update(special)
    assert len(combos) == 6144
    return combos


SPECIAL = {
    "M6-M5-E01-S0P0": _trades(1000, 0.5),                    # 強くて、どの時期もプラス → 偽薬へ
    "M6-M15-E02-S0P0": _trades(1000, -0.3),                  # 費用後マイナス
    "M6-H1-E03-S0P0": _trades(150, 0.5),                     # 件数不足
    "M6-M5-E04-S1P1": _trades(1000, 0.0),                    # 0と区別できない
    "M6-M15-E05-S2P2": _trades(1100, 0.2),                   # 幅は0より上だが、6,144通りの多重検定を越えない
    "M6-H1-E06-S3P3": _trades(1000, -0.1, mean2=1.1),        # 強いが前半がマイナス → 時期で割れた
}


def _judged():
    rows = J.judge_round(_round1(SPECIAL), "r1")
    return rows, {x["id"]: x for x in rows}


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    i = text.find("\n## M6 ")
    sec = text[i:text.find("\n## ", i + 1)]
    for s in ("**6,144通り**", "件数 **200以上**", "**3つ以上**", "**1,000回**", "p＜0.05", "ベンヤミニ・ホッホベルク",
              "現地 08:00〜15:59", "現地 17:00 に始まる足の始値で必ず出る", "300回以上", "**1000回**", "`screen_judge.py`",
              "`promotion-list.md`", "`research-lists.yml`", "`m6-screen.json`", "**これまでに数えた総数**",
              "メールの「昇格エッジ」", "上位20", "2022-06-01〜2026-09-24"):
        assert s in sec, s
    for a, b in J.PERIODS:
        assert f"{a}〜{b}" in sec or (b == J.END and f"{a}〜{b}" in sec), (a, b)
    assert "前半（2022-06-01〜2024-07-31）／後半（2024-08-01〜）" in sec and J.HALF == "2024-08-01"
    assert (J.MIN_N, J.Q, J.N_PLACEBO, J.PLACEBO_ALPHA, J.MIN_PERIODS_PLUS) == (200, 0.05, 1000, 0.05, 3)
    assert (J.FWD_STOP_MIN, J.GOAL, J.NEAR_TOP, J.ROUND_SIZES["r1"]) == (300, 1000, 20, 6144)
    assert (J.START, J.END) == ("2022-06-01", "2026-09-24") and J.TFS == ("M5", "M15", "H1")
    assert len(J.section_sha256()) == 64


def test_cluster_stats_formula():
    st = J.cluster_stats([1, -1, 2, 0], ["2024-01-01", "2024-01-02", "2024-01-08", "2024-01-09"])
    # 週ごとの合計 0・2、回数 2・2、平均0.5 → 残り −1・+1 → 2/(2−1)×2÷4² → 標準誤差0.5
    assert st["n"] == 4 and abs(st["mean"] - 0.5) < 1e-12 and abs(st["se"] - 0.5) < 1e-12
    assert abs(st["t"] - 1.0) < 1e-12 and abs(st["p"] - 0.158655) < 1e-5
    assert abs(st["lo"] - (0.5 - J.Z95 * 0.5)) < 1e-12 and st["win"] == 0.5 and st["pf"] == 3.0 and st["mdd"] == 1.0
    one = J.cluster_stats([1.0, 2.0], ["2024-01-01", "2024-01-02"])          # 1週だけ＝幅は出せない
    assert one["se"] == math.inf and one["lo"] == -math.inf
    assert J.cluster_stats([], [])["p"] == 1.0
    assert J.week_of("2024-12-30") == "2025-W01"                               # ISO 週


def test_bh_uses_the_total_so_far():
    p = [0.001, 0.02, 0.03, 0.5]
    assert J.bh_pass(p, 4).tolist() == [True, True, True, False]
    assert not J.bh_pass(p, 100).any()                                         # 総数が増えるほど厳しい
    try:
        J.bh_pass(p, 3)
        raise AssertionError("総数がラウンドの数より小さいのに通った")
    except ValueError:
        pass


def test_reasons_in_order():
    rows, by = _judged()
    assert all(x["m_total"] == 6144 for x in rows)
    want = {"M6-M15-E02-S0P0": "minus", "M6-H1-E03-S0P0": "few", "M6-M5-E04-S1P1": "zero",
            "M6-M15-E05-S2P2": "luck", "M6-H1-E06-S3P3": "split"}
    for cid, reason in want.items():
        assert by[cid]["reason"] == reason and by[cid]["status"] == "out", (cid, by[cid]["reason"])
    luck = by["M6-M15-E05-S2P2"]
    assert luck["lo"] > 0 and luck["p"] < 0.05 and not luck["bh"]              # ふつうの p＜0.05 だが、6,144通りでは偶然の範囲
    assert by["M6-H1-E06-S3P3"]["bh"] and by["M6-H1-E06-S3P3"]["half"][0] < 0
    assert [x["id"] for x in J.needs_placebo(rows)] == ["M6-M5-E01-S0P0"]
    assert by["M6-M5-E01-S1P0"]["reason"] == "few" and by["M6-M5-E01-S1P0"]["n"] == 0
    try:
        combos = _round1(SPECIAL)
        combos.pop("M6-M5-E32-S7P7")
        J.judge_round(combos, "r1")
        raise AssertionError("ラウンド1が6,143通りで通った")
    except ValueError:
        pass


def test_placebo():
    rows, by = _judged()
    strong = by["M6-M5-E01-S0P0"]
    rng = np.random.default_rng(J.placebo_seed(strong["id"]))
    J.apply_placebo(strong, rng.normal(0.0, 0.05, J.N_PLACEBO))
    assert strong["status"] == "candidate" and strong["placebo_p"] < 0.01
    same = dict(strong, status="needs_placebo", reason=None)
    J.apply_placebo(same, rng.normal(strong["mean"], 0.05, J.N_PLACEBO))       # 偽薬も同じくらい良い＝入口に意味が無い
    assert same["status"] == "out" and same["reason"] == "placebo"
    try:
        J.apply_placebo(dict(strong), [0.0] * 10)
        raise AssertionError("偽薬10回で通った")
    except ValueError:
        pass
    assert J.placebo_seed("M6-M5-E01-S0P0") == J.placebo_seed("M6-M5-E01-S0P0")


def _record():
    rows, by = _judged()
    J.apply_placebo(by["M6-M5-E01-S0P0"], np.zeros(J.N_PLACEBO))
    rec = J.build_record(rows, "r1", ran_on="2026-10-01", data={"symbol": "GBPJPY"},
                         labels={"E01": "指数平滑9本と21本の交差", "S0": "固定ATR×1.5", "P0": "固定ATR×2"}, now="x")
    return rows, rec


def test_record_rounds_and_redo():
    rows, rec = _record()
    c = rec["counts"]["r1"]
    assert c["total"] == 6144 and c["candidate"] == 1 and c["few"] == 6144 - 5 and c["luck"] == 1 and c["split"] == 1
    assert sum(c[k] for k in J.SCREEN_REASONS) + c["candidate"] == 6144
    assert [x["id"] for x in rec["promoted"]] == ["M6-M5-E01-S0P0"] and rec["promoted"][0]["stage"] == "candidate"
    assert {x["id"] for x in rec["near_misses"]} == {"M6-M15-E05-S2P2", "M6-H1-E06-S3P3"}
    assert rec["near_misses"][0]["id"] == "M6-H1-E06-S3P3"                      # t の大きい順
    assert rec["rounds"][0]["prereg_sha256"] == J.section_sha256() and rec["rounds"][0]["m_total"] == 6144
    assert J.describe(rec, "M6-M5-E01-S0P0") == "5分足・入口 指数平滑9本と21本の交差・損切り 固定ATR×1.5・利確 固定ATR×2"
    txt = json.dumps(rec, ensure_ascii=False)
    assert "Infinity" not in txt and "NaN" not in txt and '"r":' not in txt and '"date":' not in txt   # 取引の行は書かない
    try:
        J.build_record(rows, "r1", ran_on="2026-10-02", prev=rec)
        raise AssertionError("判定済みのラウンドを上書きできた")
    except ValueError:
        pass
    redo = J.build_record(rows, "r1", ran_on="2026-10-02", prev=rec, redo_reason="足の読み込みの誤りを直した")
    assert len(redo["rounds"]) == 1 and redo["redo"][0]["reason"] == "足の読み込みの誤りを直した" and len(redo["promoted"]) == 1
    r2 = J.judge_round({"M6r2-M15-E05-S2P2": _trades(1100, 0.2), "M6r2-M15-E05-S2P3": _trades(900, -0.1)}, "r2", prev=rec)
    assert all(x["m_total"] == 6146 for x in r2)                              # 総数＝6,144＋2
    rec2 = J.build_record(r2, "r2", ran_on="2026-11-01", prev=rec)
    assert [x["round"] for x in rec2["rounds"]] == ["r1", "r2"] and rec2["counts"]["r1"] == rec["counts"]["r1"]
    try:
        J.build_record(J.judge_round({"M6-M5-E01-S0P0": _trades(1000, 0.5)}, "r3", prev=rec2), "r3", ran_on="x", prev=rec2)
        raise AssertionError("偽薬がまだなのに記録できた")
    except ValueError:
        pass


def test_mt5_and_forward():
    _, rec = _record()
    cid = "M6-M5-E01-S0P0"
    bad = json.loads(json.dumps(rec))
    J.apply_mt5(bad, cid, _trades(900, -0.05)["r"], _trades(900, -0.05)["date"], "2026-10-05")
    assert not bad["promoted"] and bad["stopped_after_promotion"][0]["reason"] == "mt5"
    good = json.loads(json.dumps(rec))
    t = _trades(1000, 0.45)
    J.apply_mt5(good, cid, t["r"], t["date"], "2026-10-05")
    item = good["promoted"][0]
    assert item["stage"] == "mt5_ok" and abs(item["mt5"]["diff_from_screen"] - (item["mt5"]["mean"] - item["screen"]["mean"])) < 1e-3
    try:
        J.apply_mt5(good, cid, t["r"], t["date"], "2026-10-06")
        raise AssertionError("MT5 の確かめを2回できた")
    except ValueError:
        pass
    days = [dt.date(2026, 10, 2) + dt.timedelta(days=i) for i in range(1600)]
    days = [d.isoformat() for d in days if d.weekday() < 5]

    def fwd(n, mean):
        return [mean + (1 if (i // 5) % 2 == 0 else -1) for i in range(n)], days[:n]
    try:
        J.apply_forward(good, cid, [0.1], ["2026-10-01"], "2026-11-01")
        raise AssertionError("実行日の取引を前向きに数えた")
    except ValueError:
        pass
    J.apply_forward(good, cid, *fwd(100, 0.3), "2026-11-01")
    assert good["promoted"][0]["forward"]["n"] == 100 and good["promoted"][0]["stage"] == "mt5_ok"
    try:
        J.apply_forward(good, cid, *fwd(90, 0.3), "2026-12-01")
        raise AssertionError("前向きの取引が減ったのに通った")
    except ValueError:
        pass
    stop = json.loads(json.dumps(good))
    J.apply_forward(stop, cid, *fwd(320, -0.6), "2027-01-01")
    assert not stop["promoted"] and stop["stopped_after_promotion"][0]["reason"] == "fwd"
    plus = json.loads(json.dumps(good))
    J.apply_forward(plus, cid, *fwd(1100, 0.4), "2030-01-01")
    it = plus["promoted"][0]
    assert it["stage"] == "plus" and it["forward"]["n"] == 1000 and it["forward"]["decided_on"] == "2030-01-01"
    J.apply_forward(plus, cid, *fwd(1100, -2.0), "2030-02-01")                 # 判定が出たら固定
    assert plus["promoted"][0]["stage"] == "plus"
    return bad, good, plus


def test_lists_are_built_from_the_record():
    bad, good, plus = test_mt5_and_forward()
    _, rec = _record()
    d = tempfile.mkdtemp()
    out = {}
    for name, r in (("cand", rec), ("bad", bad), ("good", good), ("plus", plus)):
        p = os.path.join(d, f"{name}.json")
        J.write_record(r, p)
        out[name] = V.collect_screens([(p, "M6 試し")])
    vtxt = V.render([], [], [], now="x", screens=out["bad"])
    assert "## 🧮 総当たりのふるい分け" in vtxt and "MT5 の確かめで消えた" in vtxt and "偶然の範囲" in vtxt
    assert "直す出発点の候補" in vtxt and "M6-M15-E05-S2P2" in vtxt and "費用後マイナス 1" in vtxt
    assert "まだ無い（手元で数えた記録が届くと載る）" in V.render([], [], [], now="x")
    ptxt = P.render([], out["cand"], now="x")
    assert "## 🔬 昇格候補" in ptxt and "M6-M5-E01-S0P0（r1）" in ptxt and "メールの「昇格エッジ」" in ptxt
    assert "0/1000回" in P.render([], out["good"], now="x")
    top = P.render([], out["plus"], now="x")
    assert top.split("## 👀")[0].count("M6-M5-E01-S0P0") == 1                  # 🥇 の段に載る
    fr = {"src": "J4F", "sec": "J4F", "id": "F1", "title": "寄り付き", "goal": 1000, "n": 1000,
          "v": {"status": "plus", "decided_on": "2027-01-01", "n": 1000, "mean": 0.001, "lo": 0.0002, "hi": 0.002}}
    assert "| J4F-F1 |" in P.render([fr], [], now="x")                          # ほかの前向きの「プラスを確認」も並べる
    assert "投資助言ではありません" in ptxt


def test_full_csv():
    rows, _ = _judged()
    p = os.path.join(tempfile.mkdtemp(), "full.csv")
    J.write_full_csv(rows, p)
    lines = open(p, encoding="utf-8").read().splitlines()
    assert len(lines) == 6145 and lines[0].startswith("id,round,tf,n,win,mean")


def test_workflow_sync_and_sources():
    wf = open(".github/workflows/research-lists.yml", encoding="utf-8").read()
    for s in ("'*-screen.json'", "'s4-level-fade.json'", "python tests/test_screen_judge.py", "python verified_list.py",
              "python promotion_list.py", "git add verified-list.md promotion-list.md", "workflow_dispatch:"):
        assert s in wf, s
    assert "schedule:" not in wf and "pip install numpy" in wf
    yf = open(".github/workflows/yori-forward.yml", encoding="utf-8").read()
    assert "python promotion_list.py" in yf and "verified-list.md promotion-list.md" in yf
    import check_site_consistency as C
    assert {"promotion-list.md", "verified-list.md"} <= set(C.SYNC_FORBIDDEN)
    assert "m6-screen.json" not in C.SYNC_FORBIDDEN                            # 手元で作って送るもの
    assert ("m6-screen.json", "M6 ポンド円・ロンドン時間の総当たり（手元の MT5 の5分足・過去に1回ずつ）") in V.SCREEN_SOURCES


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
