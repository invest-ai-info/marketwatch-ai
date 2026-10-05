# -*- coding: utf-8 -*-
"""R3F 月末月初の前向きの観察（R3 の Q1 米国・Q3 日本の早い窓を、登録後の新しい月だけで数える）。
2026-10-05 登録・オーナー「おすすめ通りにお願いします」。

R3（calendar_lab.py）で「◯ 傾向」（関門の手前）だった2つを、**買う日が 2026-10-06 以降の取引だけ**で数える。
結果を見たあとで選んだ2つなので、過去のデータで数え直しても確かめにならない＝前向きだけが確かめ。

⚠️ 決まりは PILLAR_PREREG.md「R3F 月末月初の前向きの観察」と下の定数に固定。窓・費用の計算は calendar_lab.py の関数をそのまま使う。
⚠️ 月に1回なので、前向きだけで「プラスを確認」とは言わない（数十年かかる）。役目は**崩れていないかを見張る**こと：
   36回ごとに前向きの費用後の平均がマイナスなら止める（検証済みリストへ）。
⚠️ 一度記録した取引は書き換えない（あとで Yahoo の値が直っても固定）。売る日が過ぎた取引だけを記録する。
⚠️ 出力 calendar-forward.json / .md は GitHub 側で生成＝手元から送らない（SYNC禁忌・取引の記録を持つ）。
⚠️ エンジン・発火条件・固定オラクル・メールには触れない。

実行: python calendar_forward.py   （Actions の calendar-forward.yml から。毎月6日・8日に保険）
"""
import datetime as dt
import json
import math
import sys

import numpy as np
import pandas as pd

import calendar_lab as CL
from pillar_lab import fetch, prereg_sha256

JST = dt.timezone(dt.timedelta(hours=9))
FWD_START = "2026-10-06"
CHECK_EVERY = 36
QS = ("Q1", "Q3")
TITLES = {"Q1": "米国の月末月初（S&P500・月の最後の日＋翌月の最初の3日・CFD の費用）",
          "Q3": "日本の早い月末月初（日経平均・月の最後の5日＋翌月の最初の2日・CFD の費用）"}
OUT_JSON, OUT_MD = "calendar-forward.json", "calendar-forward.md"


def new_trades(close, cid, until):
    """買う日が FWD_START 以降で、売る日が until 以前の取引（費用後の損益つき）"""
    cfg = CL.TOM[cid]
    t = CL.tom_trades(close, cfg["pre"], cfg["post"], FWD_START, end=until)
    if t.empty:
        return []
    t = t[t["buy"] >= FWD_START]
    return [{"c": cid, "buy": r["buy"], "sell": r["sell"], "gross": float(r["gross"]),
             "net": float(r["gross"] - cfg["cost"] - CL.FIN_RATE * r["days"] / 365.0)} for _, r in t.iterrows()]


def merge(old, new):
    """古い記録はそのまま、まだ無い取引（同じ問い・同じ買う日）だけを足す"""
    have = {(t["c"], t["buy"]) for t in old}
    return sorted(old + [t for t in new if (t["c"], t["buy"]) not in have], key=lambda t: (t["c"], t["buy"]))


def stats(xs):
    xs = np.asarray(xs, float)
    if len(xs) == 0:
        return {"n": 0, "mean": None, "lo": None, "hi": None}
    m = float(xs.mean())
    if len(xs) < 2:
        return {"n": 1, "mean": m, "lo": None, "hi": None}
    se = float(xs.std(ddof=1)) / math.sqrt(len(xs))
    return {"n": len(xs), "mean": m, "lo": m - 1.96 * se, "hi": m + 1.96 * se}


def update_checks(state, today):
    """36回ごとの見張り。区切りの数字は一度出たら固定。マイナスなら止める"""
    for cid in QS:
        ts = [t["net"] for t in state["trades"] if t["c"] == cid]
        done = {c["n"] for c in state["checks"].setdefault(cid, [])}
        k = CHECK_EVERY
        while k <= len(ts):
            if k not in done and cid not in state["verdicts"]:
                st = stats(ts[:k])
                state["checks"][cid].append({"n": k, "on": today, "mean": st["mean"], "lo": st["lo"], "hi": st["hi"]})
                if st["mean"] < 0:
                    state["verdicts"][cid] = {"status": "stop", "decided_on": today, "n": k, "mean": st["mean"],
                                              "lo": st["lo"], "hi": st["hi"],
                                              "reason": f"前向き{CHECK_EVERY}回ごとの見張りで費用後の平均がマイナス"}
            k += CHECK_EVERY
    return state


def empty_state():
    return {"kind": "forward", "section": "R3F", "goal": CHECK_EVERY, "unit": "pct", "fwd_start": FWD_START,
            "titles": dict(TITLES), "verdicts": {}, "checks": {}, "trades": []}


def load_prev(path=OUT_JSON):
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        return d if d.get("section") == "R3F" else empty_state()
    except (OSError, ValueError):
        return empty_state()


def _p(x):
    return "—" if x is None else f"{x * 100:+.2f}%"


def render_md(state):
    L = ["# R3F 月末月初の前向きの観察", "",
         f"- 生成: {state['generated_jst']}　事前登録の指紋（PILLAR_PREREG.md の sha256）: `{state['prereg_sha256']}`",
         f"- 決まり＝PILLAR_PREREG.md「R3F」（R3 と同じ窓・費用）。**買う日が {FWD_START} 以降の取引だけ**を数え、一度記録した取引は書き換えない",
         f"- 役目＝崩れていないかを見張る（{CHECK_EVERY}回ごとに費用後の平均がマイナスなら止める）。月に1回なので、前向きだけで「プラスを確認」とは言わない",
         ""]
    for cid in QS:
        ts = [t for t in state["trades"] if t["c"] == cid]
        st = stats([t["net"] for t in ts])
        v = state["verdicts"].get(cid)
        nxt = (st["n"] // CHECK_EVERY + 1) * CHECK_EVERY
        status = (f"⏹ 止めた（{v['decided_on']}・{v['n']}回の見張りで平均 {_p(v['mean'])}）" if v
                  else f"👀 観察中（次の見張りは {nxt}回目）")
        L += [f"## {cid} {TITLES[cid]}", "", f"- 状態：{status}",
              f"- これまで {st['n']}回・費用後の平均 {_p(st['mean'])}" + (f"（95%の幅 {_p(st['lo'])}〜{_p(st['hi'])}）" if st["lo"] is not None else ""),
              ""]
        if ts:
            L += ["| 買った日 | 売った日 | 費用前 | 費用後 |", "|---|---|---|---|"]
            L += [f"| {t['buy']} | {t['sell']} | {_p(t['gross'])} | {_p(t['net'])} |" for t in ts[-24:]]
            L.append("")
        for c in state["checks"].get(cid, []):
            L.append(f"- 見張り {c['n']}回（{c['on']}）：平均 {_p(c['mean'])}")
        L.append("")
    L += ["---", "", "※ 研究の記録です。投資助言ではありません。過去・前向きの成績は将来を約束しません。"]
    return "\n".join(L) + "\n"


def main():
    today = dt.datetime.now(JST).date()
    until = str(today - dt.timedelta(days=1))           # 売る日が昨日までの取引だけ（今日の途中の値を使わない）
    state = load_prev()
    new = []
    for cid, tk in (("Q1", "^GSPC"), ("Q3", "^N225")):
        df = fetch(tk, "1d", start="2026-01-01")
        if df is None:
            print(f"{tk} が取れない＝何も書き換えない", file=sys.stderr)
            return 1
        c = df["Close"].astype(float)
        ok, mx, day = CL.data_ok(c[c > 0])
        if not ok:
            print(f"{tk} の1日の変化 {mx * 100:.1f}%（{day}）が {CL.MAX_DAILY * 100:.0f}% を超える＝何も書き換えない", file=sys.stderr)
            return 1
        new += new_trades(c[c > 0], cid, until)
    state["trades"] = merge(state.get("trades", []), new)
    state = update_checks(state, str(today))
    state.update({"generated_jst": dt.datetime.now(JST).strftime("%Y-%m-%dT%H:%M+09:00"), "prereg_sha256": prereg_sha256()})
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)
    md = render_md(state)
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
