# -*- coding: utf-8 -*-
"""R1（hold_lab.py）のデータの点検。数えない・何も書き込まない（表示だけ）。2026-10-05 新設。

1回目の実行（2026-10-05 08:41）で、日本株（1306.T）の「1日の最大の変化」が 947.9%、米国株（円建て）が 22.2% と出た。
株価指数の1日の変化としてありえない大きさなので、どの日の・どの元データの値かを表示して、取得の失敗かどうかを確かめる。
⚠️ 物差しと判定（PILLAR_PREREG.md「R1」・hold_lab.py）には触れない。

実行: python hold_lab_datacheck.py   （Actions の hold-lab-data-check.yml から手動で）
"""
import sys

from hold_lab import FETCH_START, load_prices
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
    prices, missing, src = load_prices()
    L += [f"- 取れなかった資産: {missing or 'なし'}", f"- 使った表記: {src}", ""]
    for a, s in prices.items():
        L += [f"## {a}（円建て・hold_lab が数える値）: {s.index[0].date()}〜{s.index[-1].date()}・{len(s)}日", "",
              "| 日付 | 変化 | 前の日 | その日 |", "|---|---|---|---|"] + top_moves(s) + [""]
    for tk in ("USDJPY=X", "^SP500TR", "1306.T", "^NSEI", "INRJPY=X", "1348.T", "1475.T", "^TOPX"):
        df = fetch(tk, "1d", start=FETCH_START)
        if df is None:
            L += [f"## 元データ {tk}: 取れない", ""]
            continue
        s = df["Close"].astype(float)
        L += [f"## 元データ {tk}（auto_adjust の終値）: {s.index[0].date()}〜{s.index[-1].date()}・{len(s)}日", "",
              "| 日付 | 変化 | 前の日 | その日 |", "|---|---|---|---|"] + top_moves(s, 6) + [""]
    try:
        import yfinance as yf
        sp = yf.Ticker("1306.T").splits
        L += ["## 1306.T の分割の記録（yfinance）", "", "```", str(sp.tail(10)), "```", ""]
        raw = yf.download("1306.T", start="2009-01-01", interval="1d", progress=False, auto_adjust=False)
        if hasattr(raw.columns, "levels"):
            raw.columns = raw.columns.get_level_values(0)
        r = raw["Close"].pct_change().abs()
        d = r.idxmax()
        i = raw.index.get_loc(d)
        L += [f"## 1306.T 調整前の終値と調整後の終値（いちばん大きく動いた {d.date()} の前後）", "", "```",
              raw.iloc[max(0, i - 4):i + 4][["Close", "Adj Close"]].to_string(), "```", ""]
    except Exception as e:  # noqa: BLE001
        L += [f"（分割の記録を読めなかった: {type(e).__name__}: {str(e)[:120]}）", ""]
    md = "\n".join(L) + "\n"
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
