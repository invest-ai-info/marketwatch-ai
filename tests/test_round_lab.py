# -*- coding: utf-8 -*-
"""S3 キリの良い値（round_lab.py）のテスト。2026-09-28 新設。

値動きはすべて作り物（ネットワークに出ない）。確かめること＝①事前登録と定数の一致 ②触れた値の見つけ方
（下から・上から・両方・どちらでもない・比べる値のずらし）③00/50 と 23/73 の区別 ④1回の取引（初めての判定・
次の足の始値・抜けと跳ね返り・時間切れ・次を数えない期間・週末の飛び）⑤差の幅と p ⑥判定の分かれ方 ⑦表の書き出し。

実行:  python tests/test_round_lab.py     （pytest 不要。pytest でも動く）
"""
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import box_lab  # noqa: E402
import round_lab as S  # noqa: E402


def _section():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    a = text.index("## S3 キリの良い値")
    b = text.find("\n## ", a + 5)
    return text[a:b if b > 0 else len(text)]


def test_prereg_numbers_match_the_code():
    sec = _section()
    for s in ("50pips ごとの値", "0.50円ごと", "0.0050 ごと", "23pips 上にずらした値", "直前の24本",
              "前の足の終値にいちばん近い値だけ", "ちょうど1時間前に無いとき", "直前の14本", "直前に15本そろわなければ数えない",
              "ATR×1.5", "ATR×2.0", "入る足を1本目として4本目", "0.8pips", "1.2pips", "滑りの係数 1.5", "2,000回",
              "p＜0.05÷2", "件数300未満", "損切りが先", "協定世界時の日付"):
        assert s in sec, s
    assert S.STEP_PIPS == 50 and S.SETS == {"round": 0, "shift": 23} and S.FRESH_BARS == 24
    assert S.ATR_N == 14 and S.SL_ATR == 1.5 and S.TP_ATR == 2.0 and S.HOLD_BARS == 4
    assert S.MIN_N == 300 and abs(S.ALPHA - 0.025) < 1e-12 and S.N_BOOT == 2000
    assert box_lab.COST_PIPS == {"JPY": 0.8, "other": 1.2} and box_lab.COST_MULT == 1.5
    assert len(S.PAIRS) == 9


def test_touched_level():
    # 前の終値 14980pips（149.80円）・高値 15005 → 下から 15000 に触れた
    assert S.touched_level(14980, 15005, 14970, 0) == (15000, 1)
    # 上から：前の終値 15020・安値 14999 → 15000
    assert S.touched_level(15020, 15030, 14999, 0) == (15000, -1)
    # どちらにも届かない
    assert S.touched_level(15010, 15040, 15001, 0) is None
    # 両方に触れたら近いほう（前の終値 15040：上の 15050 まで10・下の 15000 まで40）
    assert S.touched_level(15040, 15055, 14990, 0) == (15050, 1)
    # 前の終値がちょうど値の上にあるときは、その値は数えない（上下どちらでもない）
    assert S.touched_level(15000, 15020, 14990, 0) is None
    # 比べる値（23 ずらし）：前の終値 15010 → 上の 15023 に触れる
    assert S.touched_level(15010, 15025, 15005, 23) == (15023, 1)
    assert S.touched_level(15010, 15020, 15005, 23) is None


def test_level_kind():
    assert S.level_kind(15000, 0) == "00" and S.level_kind(15050, 0) == "50"
    assert S.level_kind(15023, 23) == "23" and S.level_kind(15073, 23) == "73"
    assert S.level_kind(11000, 0) == "00" and S.level_kind(11050, 0) == "50"     # 1.1000・1.1050（pips の整数）


def _bars(rows, start="2026-07-06 00:00"):
    idx = pd.date_range(start, periods=len(rows), freq="h", tz="UTC")
    return pd.DataFrame(rows, index=idx, columns=["Open", "High", "Low", "Close"])


def _quiet(n, px=149.80):
    """値幅 0.10円（真の値幅 0.10）の静かな足。149.75〜149.85 の中＝150.00 には触れない"""
    return [(px, px + 0.05, px - 0.05, px)] * n


def test_one_touch_break_and_bounce():
    rows = _quiet(30) + [
        (149.80, 150.02, 149.78, 149.98),    # 30：下から 150.00 に触れた（初めて）
        (150.00, 150.05, 149.95, 150.02),    # 31：入る足（始値 150.00）
        (150.02, 150.06, 149.97, 150.03),
        (150.03, 150.08, 150.00, 150.04),
        (150.04, 150.09, 150.01, 150.06),    # 34：4本目＝時間切れの終値 150.06
        (150.06, 151.00, 149.00, 150.06)] + _quiet(5, 150.06)   # 35 は見ない
    got, skipped = S.trades_for(_bars(rows), "USDJPY=X", "round")
    assert len(got) == 1, got
    r = got[0]
    assert r["dir"] == 1 and r["kind"] == "00" and abs(r["level"] - 150.00) < 1e-9
    # ATR=0.10 → 1R=0.15・利確 0.20。どちらにも届かず時間切れ：抜け +0.06/0.15・跳ね返り −0.06/0.15
    assert abs(r["break_gross"] - 0.06 / 0.15) < 1e-9 and abs(r["bounce_gross"] + 0.06 / 0.15) < 1e-9
    assert r["exit_break"] == "時間切れ" and r["exit_bounce"] == "時間切れ"
    cost_r = 0.8 * 1.5 * 0.01 / 0.15
    assert abs(r["break_net"] - (0.06 / 0.15 - cost_r)) < 1e-9
    assert r["date"] == "2026-07-07"


def test_not_first_touch_and_cooldown_and_gap():
    # 直前の24本の値幅に 150.00 が入っている → 初めてではない
    rows = _quiet(20) + [(149.95, 150.01, 149.94, 149.96)] + _quiet(9) + [(149.80, 150.02, 149.78, 149.98)] + _quiet(10)
    got, _ = S.trades_for(_bars(rows), "USDJPY=X", "round")
    assert all(r["touch_utc"] != _bars(rows).index[30].isoformat() for r in got)
    # 取引の途中（時間切れの足まで）に別の値へ触れても数えない
    #   30＝150.00 に初めて触れる／31＝入る足（150.50 には届かない）／32＝150.50 に初めて触れるが、取引の途中なので数えない
    rows = _quiet(30) + [(149.80, 150.02, 149.78, 149.98), (150.00, 150.12, 149.99, 150.10),
                         (150.10, 150.55, 150.08, 150.40)] + _quiet(8, 150.40)
    b = _bars(rows)
    got, _ = S.trades_for(b, "USDJPY=X", "round")
    assert [r["touch_utc"] for r in got] == [b.index[30].isoformat()]
    # 決まりを外すと 32 も数えてしまう（＝上の結果は「次を数えない期間」が効いている証拠）
    lv = S.touched_level(S._pips(150.10, 0.01), S._pips(150.55, 0.01), S._pips(150.08, 0.01), 0)
    assert lv == (15050, 1) and not any(S._pips(b["Low"].iloc[k], .01) <= 15050 <= S._pips(b["High"].iloc[k], .01)
                                        for k in range(8, 32))
    # 前の足が1時間前に無い（週末の飛び）→ 数えない
    b = _bars(_quiet(30) + [(149.80, 150.02, 149.78, 149.98)] + _quiet(8, 149.98))
    b.index = b.index[:30].append(b.index[30:] + pd.Timedelta(hours=49))
    got, _ = S.trades_for(b, "USDJPY=X", "round")
    assert got == []
    # 次の足が無い
    got, sk = S.trades_for(_bars(_quiet(30) + [(149.80, 150.02, 149.78, 149.98)]), "USDJPY=X", "round")
    assert got == [] and sk.get("次の足が無い") == 1


def test_diff_boot():
    days = [f"2026-01-{d:02d}" for d in range(1, 29)]
    rv = [0.3 + 0.01 * (i % 5) for i in range(len(days))]
    sv = [0.0 + 0.01 * (i % 5) for i in range(len(days))]
    diff, lo, hi, p = S.diff_boot(rv, days, sv, days)
    assert abs(diff - 0.3) < 1e-9 and lo > 0.25 and hi < 0.35 and p < 0.01
    rng = np.random.default_rng(1)
    a, b = list(rng.normal(0, 1, 400)), list(rng.normal(0, 1, 400))
    d2 = [days[i % 28] for i in range(400)]
    _, lo2, hi2, p2 = S.diff_boot(a, d2, b, d2)
    assert lo2 < 0 < hi2 or p2 >= 0.025


def _side(mean, diff, p, e, l, de, dl):
    return {"mean": mean, "diff": diff, "p": p, "early": e, "late": l, "diff_early": de, "diff_late": dl}


def test_judge():
    good = _side(.1, .1, .001, .1, .1, .1, .1)
    bad = _side(-.1, -.1, .5, -.1, -.1, -.1, -.1)
    assert S.judge({"n_round": 299, "n_shift": 500, "break": good, "bounce": bad}) == "件数不足"
    assert S.judge({"n_round": 500, "n_shift": 299, "break": good, "bounce": bad}) == "件数不足"
    assert S.judge({"n_round": 300, "n_shift": 300, "break": good, "bounce": bad}).startswith("キリの良い値は抜けやすい")
    assert S.judge({"n_round": 300, "n_shift": 300, "break": bad, "bounce": good}).startswith("キリの良い値は跳ね返りやすい")
    for k, v in (("mean", -.01), ("diff", -.01), ("p", .03), ("early", -.01), ("late", None), ("diff_early", -.01),
                 ("diff_late", -.01)):
        assert S.judge({"n_round": 300, "n_shift": 300, "break": dict(good, **{k: v}), "bounce": bad}) == "差なし", k


def test_stats_and_render():
    rng = np.random.default_rng(0)
    rows = []
    for i in range(700):
        d = (pd.Timestamp("2025-01-06") + pd.Timedelta(days=i % 200)).date().isoformat()
        g = float(rng.normal(0, 1))
        sk = "round" if i % 2 == 0 else "shift"
        rows.append({"set": sk, "ticker": S.PAIRS[i % 9], "date": d, "touch_utc": d + "T10:00:00+00:00",
                     "level": 150.0, "kind": ("00", "50")[i % 4 // 2] if sk == "round" else ("23", "73")[i % 4 // 2],
                     "dir": 1 if g > 0 else -1, "break_gross": g, "break_net": g - .02, "bounce_gross": -g,
                     "bounce_net": -g - .02, "cost_r": .02, "break_official": g - .01, "bounce_official": -g - .01,
                     "exit_break": "時間切れ", "exit_bounce": "時間切れ"})
    r = S.stats(rows)
    assert r["n_round"] == 350 and r["n_shift"] == 350
    assert set(r["by_kind"]) == {"00", "50", "23", "73"} and r["break"]["diff_lo"] <= r["break"]["diff_hi"]
    out = {"generated_jst": "2026-09-28T01:00+09:00", "prereg_sha256": "ab" * 32, "missing": [],
           "skipped": {"ドル円:round:次の足が無い": 1}, "result": r}
    md = S.render_md(out)
    assert "S3 キリの良い値" in md and "抜け" in md and "跳ね返り" in md and "投資助言ではありません" in md
    assert "件数不足" in S.render_md(dict(out, result=S.stats([])))


if __name__ == "__main__":
    fns = [v for k, v in dict(globals()).items() if k.startswith("test_")]
    for fn in fns:
        fn()
        print("ok", fn.__name__)
    print(f"{len(fns)} passed")
