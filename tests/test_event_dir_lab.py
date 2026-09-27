# -*- coding: utf-8 -*-
"""S2 重要な発表のあと（event_dir_lab.py）のテスト。2026-09-27 新設。

値動きはすべて作り物（ネットワークに出ない）。確かめること＝①事前登録と定数の一致 ②発表時刻（夏時間・冬時間・
同じ時刻の重なり・範囲）③平均的な値幅 ④1つの発表の取引（向き・次の足の始値・幅・時間切れ・費用・数えない場合）
⑤判定の分かれ方 ⑥表の書き出し。

実行:  python tests/test_event_dir_lab.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import box_lab  # noqa: E402
import event_dir_lab as S  # noqa: E402


def _section():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    a = text.index("## S2 重要な発表のあと")
    b = text.find("\n## ", a + 5)
    return text[a:b if b > 0 else len(text)]


def test_prereg_numbers_match_the_code():
    sec = _section()
    for s in ("FOMC 14:00", "CPI と雇用統計 8:30", "同じ時刻の発表が重なった日は、1回の発表として数える",
              "直前の14本", "直前に15本そろわなければ数えない", "ATR×1.5", "ATR×2.0", "入る足を1本目として4本目",
              "0.8pips", "1.2pips", "滑りの係数 1.5", "2,000回", "p＜0.05÷2", "300未満", "損切りが先", "0 なら数えない"):
        assert s in sec, s
    assert S.ATR_N == 14 and S.SL_ATR == 1.5 and S.TP_ATR == 2.0 and S.HOLD_BARS == 4
    assert S.MIN_N == 300 and abs(S.ALPHA - 0.025) < 1e-12
    assert box_lab.N_PERM == 2000 and box_lab.N_BOOT == 2000
    assert box_lab.COST_PIPS == {"JPY": 0.8, "other": 1.2} and box_lab.COST_MULT == 1.5
    assert len(S.PAIRS) == 9


def test_event_times_and_dedup():
    ev = {"cpi": [dt.date(2026, 7, 15), dt.date(2026, 1, 13)], "nfp": [dt.date(2026, 7, 15)],
          "fomc": [dt.date(2026, 7, 29), dt.date(2025, 1, 2), dt.date(2026, 9, 30)]}
    got = S.event_list(ev, dt.date(2025, 1, 2), dt.date(2026, 12, 31), dt.date(2026, 9, 28))
    # 夏：8:30 ET = 12:30 UTC／冬：13:30 UTC／FOMC 14:00 ET（夏）= 18:00 UTC
    assert got == [(pd.Timestamp("2026-01-13 13:30", tz="UTC"), ("cpi",)),
                   (pd.Timestamp("2026-07-15 12:30", tz="UTC"), ("cpi", "nfp")),     # 同じ時刻は1回
                   (pd.Timestamp("2026-07-29 18:00", tz="UTC"), ("fomc",))]
    # 足の最初の日（2025-01-02）ちょうどと、今日以降（9/30）は数えない


def test_atr_before():
    h = np.array([10.0] * 16)
    lo = np.array([9.0] * 16)
    c = np.array([9.5] * 16)
    assert S.atr_before(h, lo, c, 15) == 1.0
    assert S.atr_before(h, lo, c, 14) is None          # 前の足の終値まで15本そろわない
    c2 = c.copy()
    c2[13] = 12.0                                      # 前の足の終値が高い → 次の足の真の値幅が広がる
    assert S.atr_before(h, lo, c2, 15) > 1.0


def _bars(h0, tail):
    """発表の足の前に20本（高値100.5・安値99.5・始値終値100＝真の値幅1.0）＋ tail（発表の足から）"""
    idx = pd.date_range(h0 - pd.Timedelta(hours=20), periods=20 + len(tail), freq="h", tz="UTC")
    rows = [(100.0, 100.5, 99.5, 100.0)] * 20 + tail
    return pd.DataFrame(rows, index=idx, columns=["Open", "High", "Low", "Close"])


def _run(bars, ts, ticker="USDJPY=X"):
    pos = {t: i for i, t in enumerate(bars.index)}
    arrs = tuple(bars[k].to_numpy(float) for k in ("Open", "High", "Low", "Close"))
    return S.event_trade(bars, ticker, ts, ("cpi",), pos, arrs)


def test_one_event_trade():
    ts = pd.Timestamp("2026-07-15 12:30", tz="UTC")
    h0 = ts.floor("h")
    tail = [(100.0, 101.2, 99.9, 101.0),     # 発表の足：上向き
            (101.0, 101.4, 100.8, 101.2),    # 入る足（始値 101.0）
            (101.2, 101.5, 101.0, 101.3),
            (101.3, 101.6, 101.1, 101.4),
            (101.4, 101.6, 101.2, 101.5),    # 4本目＝時間切れの終値 101.5
            (101.5, 110.0, 90.0, 101.5)]     # 5本目は見ない
    row, why = _run(_bars(h0, tail), ts)
    assert why is None and row["dir"] == 1
    # ATR=1.0 → 1R=1.5・利確 2.0。どちらにも触れず時間切れ：乗る +0.5/1.5・逆らう −0.5/1.5
    assert abs(row["follow_gross"] - 0.5 / 1.5) < 1e-12 and abs(row["fade_gross"] + 0.5 / 1.5) < 1e-12
    assert row["exit_follow"] == "時間切れ" and row["exit_fade"] == "時間切れ"
    cost_r = 0.8 * 1.5 * 0.01 / 1.5
    assert abs(row["cost_r"] - cost_r) < 1e-12 and abs(row["follow_net"] - (0.5 / 1.5 - cost_r)) < 1e-12
    assert abs(row["fade_net"] - (-0.5 / 1.5 - cost_r)) < 1e-12
    assert abs(row["follow_official"] - (0.5 / 1.5 - 0.2 * 0.01 / 1.5)) < 1e-12
    assert row["date"] == "2026-07-15" and row["move_atr"] == 1.0


def test_trade_hits_and_skips():
    ts = pd.Timestamp("2026-07-15 12:30", tz="UTC")
    h0 = ts.floor("h")
    # 下向きの発表の足 → 乗る＝売り。入る足で 97.9 まで下げる＝利確（入った 99.0 − 2.0 = 97.0 には届かない）→ 2本目で届く
    tail = [(100.0, 100.1, 98.8, 99.0), (99.0, 99.2, 97.9, 98.0), (98.0, 98.1, 96.9, 97.0),
            (97.0, 97.2, 96.8, 97.0), (97.0, 97.1, 96.9, 97.0)]
    row, _ = _run(_bars(h0, tail), ts)
    assert row["dir"] == -1 and row["exit_follow"] == "利確" and abs(row["follow_gross"] - 2.0 / 1.5) < 1e-12
    assert row["exit_fade"] == "損切り" and row["fade_gross"] == -1.0
    # 発表の足が動いていない／発表の足が無い／次の足が無い／直前の足が足りない
    flat = [(100.0, 100.5, 99.5, 100.0)] * 6
    assert _run(_bars(h0, flat), ts)[1] == "発表の足が動いていない"
    b = _bars(h0, tail)
    assert _run(b.drop(index=h0), ts)[1] == "発表の足が無い"
    assert _run(b.drop(index=h0 + pd.Timedelta(hours=1)), ts)[1] == "次の足が無い"
    assert _run(b.iloc[10:], ts)[1] == "直前の足が足りない"


def _res(n, fm, fe, fl, fg, xm, xe, xl, p):
    return {"n": n, "p": p, "follow": {"mean": fm, "early": fe, "late": fl, "gross": fg},
            "fade": {"mean": xm, "early": xe, "late": xl}}


def test_judge():
    assert S.judge(_res(299, .2, .2, .2, .3, -.3, -.3, -.3, .001)) == "件数不足"
    assert S.judge(_res(300, .2, .2, .2, .3, -.3, -.3, -.3, .001)) == "発表のあと、動いた向きに乗る形が残る"
    assert S.judge(_res(300, .2, .2, -.1, .3, -.3, -.3, -.3, .001)) == "差なし"        # 後半がマイナス
    assert S.judge(_res(300, .2, .2, .2, .3, -.3, -.3, -.3, .03)) == "差なし"          # p が 0.025 以上
    assert S.judge(_res(300, -.3, -.3, -.3, -.2, .1, .1, .1, .001)) == "発表のあと、逆らう形が残る"
    assert S.judge(_res(300, -.3, -.3, -.3, -.2, .1, .1, None, .001)) == "差なし"
    assert S.judge(_res(300, -.3, -.3, -.3, -.2, -.05, .1, .1, .001)) == "差なし"      # 逆らう側も費用後マイナス


def test_stats_and_render():
    rng = np.random.default_rng(0)
    rows = []
    for i in range(40):
        d = (dt.date(2025, 1, 6) + dt.timedelta(days=14 * i)).isoformat()
        for tk in S.PAIRS:
            g = float(rng.normal(0, 1))
            rows.append({"ticker": tk, "date": d, "event_utc": d + "T12:30:00+00:00",
                         "kinds": ["cpi", "nfp"] if i == 0 else [("fomc", "cpi", "nfp")[i % 3]],
                         "dir": 1 if g > 0 else -1, "move_atr": abs(g) + 0.1,
                         "follow_gross": g, "follow_net": g - .01, "fade_gross": -g, "fade_net": -g - .01,
                         "cost_r": .01, "follow_official": g - .005, "fade_official": -g - .005,
                         "exit_follow": "時間切れ", "exit_fade": "時間切れ"})
    r = S.stats(rows)
    assert r["n"] == 360 and r["n_days"] == 40 and r["verdict"] in ("差なし", "発表のあと、動いた向きに乗る形が残る",
                                                                  "発表のあと、逆らう形が残る")
    assert set(r["by_kind"]) == {"重なり", "fomc", "cpi", "nfp"} and r["follow"]["lo"] <= r["follow"]["hi"]
    out = {"generated_jst": "2026-09-27T23:00+09:00", "prereg_sha256": "ab" * 32, "missing": [],
           "sources": {"fomc": "ok", "cpi": "ok", "nfp": "ok"}, "skipped": {"ドル円:次の足が無い": 1}, "result": r}
    md = S.render_md(out)
    assert "S2 重要な発表のあと" in md and "乗る" in md and "逆らう" in md and "投資助言ではありません" in md
    empty = dict(out, result=S.stats([]))
    assert "件数不足" in S.render_md(empty)


if __name__ == "__main__":
    fns = [v for k, v in dict(globals()).items() if k.startswith("test_")]
    for fn in fns:
        fn()
        print("ok", fn.__name__)
    print(f"{len(fns)} passed")
