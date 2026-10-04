# -*- coding: utf-8 -*-
"""R1（hold_lab.py）のデータの点検。数えない・何も書き込まない（表示だけ）。2026-10-05 新設。

1回目の実行（2026-10-05 08:41）で、日本株（1306.T）の「1日の最大の変化」が 947.9%、米国株（円建て）が 22.2% と出た。
株価指数の1日の変化としてありえない大きさなので、どの日の・どの元データの値かを表示して、取得の失敗かどうかを確かめた
（ドル円の1日だけの偽の値・1306.T の10倍の単位のずれ）。追記の直し方（hold_lab.clean）で何が直り、どの資産を数え直すかも表示する。
⚠️ 物差しと判定（PILLAR_PREREG.md「R1」・hold_lab.py）には触れない。

実行: python hold_lab_datacheck.py   （Actions の hold-lab-data-check.yml から手動で）
"""
import sys

import pandas as pd

from hold_lab import ASSETS, FETCH_START, fixes_for, load_prices
from pillar_lab import fetch


def top_moves(s, k=8):
    ch = s.pct_change().dropna()
    prev = s.shift(1)
    out = []
    for d in ch.abs().sort_values(ascending=False).index[:k]:
        out.append(f"| {d.date()} | {ch[d] * 100:+.1f}% | {prev[d]:.6g} | {s[d]:.6g} |")
    return out


def main():
    L = ["# R1 データの点検（表示だけ）", ""]
    prices, missing, src, fixes = load_prices()
    L += [f"- 取れなかった資産: {missing or 'なし'}", f"- 使った表記: {src}", "",
          "## 直し（2026-10-05 追記の決まり・hold_lab.clean）", ""]
    for tk, xs in fixes.items():
        for x in xs:
            L.append(f"- {tk}: {x}")
    rerun = [a for a in ASSETS if a in src and fixes_for(a, src, fixes)]
    L += ["", f"**直しが入った資産（数え直す）: {rerun or 'なし'}**", ""]
    for a, s in prices.items():
        L += [f"## {a}（円建て・直したあと・hold_lab が数える値）: {s.index[0].date()}〜{s.index[-1].date()}・{len(s)}日", "",
              "| 日付 | 変化 | 前の日 | その日 |", "|---|---|---|---|"] + top_moves(s) + [""]
    for tk in ("USDJPY=X", "1306.T", "INRJPY=X"):
        df = fetch(tk, "1d", start=FETCH_START)
        if df is None:
            L += [f"## 元データ {tk}: 取れない", ""]
            continue
        s = df["Close"].astype(float)
        L += [f"## 元データ {tk}（auto_adjust の終値）: {s.index[0].date()}〜{s.index[-1].date()}・{len(s)}日", "",
              "| 日付 | 変化 | 前の日 | その日 |", "|---|---|---|---|"] + top_moves(s, 6) + [""]
    # 🆕 止まった値（同じ終値が続く区間）と、同じ TOPIX に連動する 1306.T と 1348.T の食い違い
    raw = {}
    for tk in ("BTC-JPY", "USDJPY=X", "^SP500TR", "1306.T", "1348.T", "^NSEI", "INRJPY=X"):
        df = fetch(tk, "1d", start=FETCH_START)
        if df is not None:
            raw[tk] = df["Close"].astype(float)
    L += ["## 同じ終値が続いた区間（長い順・3日以上）", ""]
    for tk, s in raw.items():
        same = (s.diff() == 0).to_numpy()
        runs, i = [], 0
        while i < len(same):
            if same[i]:
                j = i
                while j < len(same) and same[j]:
                    j += 1
                runs.append((j - i + 1, s.index[i - 1].date(), s.index[j - 1].date()))
                i = j
            else:
                i += 1
        top = sorted((r for r in runs if r[0] >= 3), reverse=True)[:5]
        L.append(f"- {tk}: " + ("なし" if not top else "／".join(f"{n}日 {a}〜{b}" for n, a, b in top)))
    if "1306.T" in raw and "1348.T" in raw:
        a, b = raw["1306.T"].pct_change(), raw["1348.T"].pct_change()
        j = pd.concat([a, b], axis=1, keys=["1306", "1348"]).dropna()
        gap = j[(j["1306"] - j["1348"]).abs() > 0.03]
        L += ["", f"## 1306.T と 1348.T の1日の変化が3%以上食い違った日: {len(gap)}日（両方ある {len(j)}日のうち）", "",
              "| 日付 | 1306.T | 1348.T |", "|---|---|---|"]
        L += [f"| {d.date()} | {r['1306'] * 100:+.1f}% | {r['1348'] * 100:+.1f}% |" for d, r in gap.head(25).iterrows()]
        me = pd.concat([raw["1306.T"], raw["1348.T"]], axis=1, keys=["1306", "1348"]).loc["2014-11-01":"2015-09-30"]
        me = me.groupby(me.index.to_period("M")).last()
        L += ["", "## 2014-11〜2015-09 の月末の終値（調整後）", "", "```", me.to_string(), "```", ""]
    md = "\n".join(L) + "\n"
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
