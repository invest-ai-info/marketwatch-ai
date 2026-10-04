# -*- coding: utf-8 -*-
"""R1（hold_lab.py）のデータの点検。数えない・何も書き込まない（表示だけ）。2026-10-05 新設。

1回目の実行（2026-10-05 08:41）で、日本株（1306.T）の「1日の最大の変化」が 947.9%、米国株（円建て）が 22.2% と出た。
株価指数の1日の変化としてありえない大きさなので、どの日の・どの元データの値かを表示して、取得の失敗かどうかを確かめた
（ドル円の1日だけの偽の値・1306.T の10倍の単位のずれ）。追記の直し方（hold_lab.clean）で何が直り、どの資産を数え直すかも表示する。
⚠️ 物差しと判定（PILLAR_PREREG.md「R1」・hold_lab.py）には触れない。

実行: python hold_lab_datacheck.py   （Actions の hold-lab-data-check.yml から手動で）
"""
import sys

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
    md = "\n".join(L) + "\n"
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
