# -*- coding: utf-8 -*-
"""R3F 月末月初の窓の予定表（買う日・売る日と、その日の大引けの時刻）。手元の MT4 のデモで、実際の費用（売り買いの差・持ち越しの金利）を
確かめるため。2026-10-05 夜・オーナー「続けてください」。

⚠️ 数えない・値段を使わない。取引所の暦（pandas_market_calendars のニューヨーク証券取引所・東証）だけで日を決め、窓の決め方は
   calendar_lab.tom_trades をそのまま使う＝前向きの観察（calendar_forward.py）と同じ日になる（休場の日・半日の日も暦に任せる）。
⚠️ 予定表は手元で使う（--out は research/ の下に）。サイトには載せない（売買の時期の案内と読めるため）。
⚠️ R3F の記録・判定には使わない（R3F は Yahoo の日足だけで数える）。デモで確かめるのは費用だけ。

実行:
  python tom_schedule.py                         → 次の6か月の予定を表示
  python tom_schedule.py --months 12 --out research/ea/tom_dates.csv
"""
import argparse
import datetime as dt
import sys

import numpy as np
import pandas as pd

import calendar_lab as CL

JST = dt.timezone(dt.timedelta(hours=9))
MARKETS = {"Q1": ("NYSE", "米国（S&P500）"), "Q3": ("XTKS", "日本（日経平均）")}


def exchange_schedule(name, start, end):
    """取引所の取引日と大引けの時刻（UTC）。→ DataFrame（添字＝日付・列 close_utc）"""
    import pandas_market_calendars as mcal
    s = mcal.get_calendar(name).schedule(start_date=start, end_date=end)
    return pd.DataFrame({"close_utc": pd.DatetimeIndex(s["market_close"]).tz_convert("UTC")},
                        index=pd.DatetimeIndex(pd.to_datetime(s.index.date)))


def schedule(today, months=6, sched=exchange_schedule):
    """買う日が today 以降の窓を、問いごとに months 個まで"""
    out = []
    for cid, (cal, label) in MARKETS.items():
        cfg = CL.TOM[cid]
        s = sched(cal, str(today - dt.timedelta(days=45)), str(today + dt.timedelta(days=31 * (months + 2))))
        close = pd.Series(np.arange(len(s), dtype=float) + 100.0, index=s.index)     # 値は使わない（日の並びだけ）
        t = CL.tom_trades(close, cfg["pre"], cfg["post"], str(today), end="2100-12-31")
        t = t[t["buy"] >= str(today)].head(months)
        for _, r in t.iterrows():
            bc, sc = s.loc[pd.Timestamp(r["buy"]), "close_utc"], s.loc[pd.Timestamp(r["sell"]), "close_utc"]
            out.append({"c": cid, "market": label, "buy": r["buy"], "sell": r["sell"], "days": int(r["days"]),
                        "buy_close_utc": bc.isoformat(), "sell_close_utc": sc.isoformat(),
                        "buy_close_jst": bc.tz_convert(JST).strftime("%Y-%m-%d %H:%M"),
                        "sell_close_jst": sc.tz_convert(JST).strftime("%Y-%m-%d %H:%M")})
    return out


def render(rows):
    L = ["| 問い | 市場 | 買う日（その日の大引け・日本時間） | 売る日（その日の大引け・日本時間） | 持つ暦日 |", "|---|---|---|---|---|"]
    L += [f"| {r['c']} | {r['market']} | {r['buy']}（{r['buy_close_jst']}） | {r['sell']}（{r['sell_close_jst']}） | {r['days']} |" for r in rows]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description="R3F 月末月初の窓の予定表（手元の MT4 デモ用）")
    ap.add_argument("--months", type=int, default=6)
    ap.add_argument("--out", default=None, help="CSV の書き出し先（research/ の下に）")
    ap.add_argument("--today", default=None, help="この日から（既定＝今日・日本時間）")
    a = ap.parse_args(argv)
    today = dt.date.fromisoformat(a.today) if a.today else dt.datetime.now(JST).date()
    rows = schedule(today, a.months)
    print(render(rows))
    if a.out:
        pd.DataFrame(rows).to_csv(a.out, index=False, encoding="utf-8")
        print(f"→ {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
