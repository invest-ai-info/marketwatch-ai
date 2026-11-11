# -*- coding: utf-8 -*-
"""PS チャートの上の「人の心理が動きそうな場所」を探す側（Yahoo の1時間足・約730日）。2026-11-11・PILLAR_PREREG.md「PS」。

読むだけ・判定しない。場所に来た足の終値から 1・4・8 本あとまでの動き（近づいた向きがプラス・直前120本の足の幅の平均で割る）。
実行: python psych_levels_explore.py            （Yahoo から取り、表を出す。何も書き出さない）
"""
import math
import sys
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

PAIRS = ("USDJPY", "EURJPY", "GBPJPY", "AUDJPY", "EURUSD", "GBPUSD", "AUDUSD", "EURAUD", "GBPAUD")
NY, JST = ZoneInfo("America/New_York"), ZoneInfo("Asia/Tokyo")
HORIZ = (1, 4, 8)
ATR_N = 120
BIG, STREAK = 3.0, 5
N_CELLS = 80


def pip(pair):
    return 0.01 if pair.endswith("JPY") else 0.0001


def fetch(pair):
    import yfinance as yf
    d = yf.download(pair + "=X", period="730d", interval="1h", progress=False, auto_adjust=False)
    if isinstance(d.columns, pd.MultiIndex):
        d.columns = d.columns.get_level_values(0)
    d = d.rename(columns=str.lower)[["open", "high", "low", "close"]].dropna()
    d.index = d.index.tz_convert("UTC") if d.index.tz is not None else d.index.tz_localize("UTC")
    return d[(d["high"] > d["low"]) | (d["close"] != d["open"])]


def prepare(d):
    d = d.copy()
    ny = d.index.tz_convert(NY)
    fx = (ny + pd.Timedelta(hours=7))                       # ニューヨーク 17:00 が日の区切り
    d["day"] = np.asarray([x.isoformat() for x in fx.date])
    d["week"] = np.asarray(fx.strftime("%G-%V"))
    d["atr"] = (d["high"] - d["low"]).rolling(ATR_N).mean().shift(1)
    j = d.index.tz_convert(JST)
    d["jh"] = np.asarray(j.hour)
    d["jday"] = np.asarray([x.isoformat() for x in j.date])
    return d


def level_table(d, pair):
    """日ごとの線：{day: {name: [値…]}}"""
    g = d.groupby("day", sort=True).agg(hi=("high", "max"), lo=("low", "min"), op=("open", "first"), wk=("week", "first"))
    w = d.groupby("week", sort=True).agg(hi=("high", "max"), lo=("low", "min"), op=("open", "first"))
    wprev = w.shift(1)
    out = {}
    days = list(g.index)
    for n, day in enumerate(days):
        L = {}
        if n >= 1:
            L["前の日の高値安値"] = [g["hi"].iloc[n - 1], g["lo"].iloc[n - 1]]
        if n >= 20:
            L["20日の高値安値"] = [g["hi"].iloc[n - 20:n].max(), g["lo"].iloc[n - 20:n].min()]
        wk = g["wk"].iloc[n]
        if wk in wprev.index and np.isfinite(wprev.loc[wk, "hi"]):
            L["前の週の高値安値"] = [wprev.loc[wk, "hi"], wprev.loc[wk, "lo"]]
        L["その日の始値"] = [g["op"].iloc[n]]
        L["その週の始値"] = [w.loc[wk, "op"]]
        out[day] = L
    return out


def round_levels(lo, hi, pair, step_pips, skip_pips=None):
    st = step_pips * pip(pair)
    k0, k1 = math.floor(lo / st), math.ceil(hi / st)
    v = [k * st for k in range(k0, k1 + 1)]
    if skip_pips:
        sk = skip_pips * pip(pair)
        v = [x for x in v if abs(x / sk - round(x / sk)) > 1e-6]
    return v


def touches(d, pair):
    """[(場所, 日付, 足の位置, 向き, 終わり方)]"""
    ev = []
    lv = level_table(d, pair)
    o, h, l, c = (d[k].to_numpy() for k in ("open", "high", "low", "close"))
    day, jh, jday = d["day"].to_numpy(), d["jh"].to_numpy(), d["jday"].to_numpy()
    pos_by_day = {}
    for i, dd in enumerate(day):
        pos_by_day.setdefault(dd, []).append(i)
    for dd, rows in pos_by_day.items():
        L = dict(lv.get(dd, {}))
        lo_, hi_ = l[rows].min(), h[rows].max()
        L["切りのいい値段100"] = round_levels(lo_, hi_, pair, 100)
        L["切りのいい値段50"] = round_levels(lo_, hi_, pair, 50, skip_pips=100)
        for name, vals in L.items():
            for v in vals:
                for i in rows[1:]:
                    if c[i - 1] < v <= h[i]:
                        ev.append((name, dd, i, 1, "抜けた" if c[i] > v else "戻された"))
                        break
                    if c[i - 1] > v >= l[i]:
                        ev.append((name, dd, i, -1, "抜けた" if c[i] < v else "戻された"))
                        break
    # 東京時間の高値・安値（日本時間の同じ日の15時以降）
    pos_by_j = {}
    for i, dd in enumerate(jday):
        pos_by_j.setdefault(dd, []).append(i)
    for dd, rows in pos_by_j.items():
        rows = np.asarray(rows)
        tk = rows[(jh[rows] >= 9) & (jh[rows] < 15)]
        af = rows[jh[rows] >= 15]
        if len(tk) < 5 or len(af) == 0:
            continue
        for v, s in ((h[tk].max(), 1), (l[tk].min(), -1)):
            for i in af:
                if s > 0 and c[i - 1] < v <= h[i]:
                    ev.append(("東京時間の高値安値", dd, i, 1, "抜けた" if c[i] > v else "戻された"))
                    break
                if s < 0 and c[i - 1] > v >= l[i]:
                    ev.append(("東京時間の高値安値", dd, i, -1, "抜けた" if c[i] < v else "戻された"))
                    break
    atr = d["atr"].to_numpy()
    body = np.sign(c - o)
    for i in range(ATR_N + 1, len(c)):
        if np.isfinite(atr[i]) and (h[i] - l[i]) >= BIG * atr[i] and body[i] != 0:
            ev.append(("大きな足", day[i], i, int(body[i]), "全部"))
        if body[i] != 0 and all(body[i - k] == body[i] for k in range(STREAK)) and body[i - STREAK] != body[i]:
            ev.append(("同じ向き5本", day[i], i, int(body[i]), "全部"))
    return ev


def outcomes(d, ev, pair):
    c, atr = d["close"].to_numpy(), d["atr"].to_numpy()
    rows = []
    for name, dd, i, s, how in ev:
        if not np.isfinite(atr[i]) or atr[i] <= 0:
            continue
        r = {"place": name, "day": dd, "how": how, "pair": pair, "atr_pips": atr[i] / pip(pair)}
        for hz in HORIZ:
            r[f"f{hz}"] = s * (c[i + hz] - c[i]) / atr[i] if i + hz < len(c) else np.nan
        rows.append(r)
    return rows


def zstat(vals, days):
    r = np.asarray(vals, float)
    ok = np.isfinite(r)
    r, days = r[ok], np.asarray(days)[ok]
    n = len(r)
    if n < 30:
        return n, None, None
    m = r.mean()
    _, inv = np.unique(days, return_inverse=True)
    s, cnt = np.bincount(inv, weights=r), np.bincount(inv)
    g = len(s)
    se = math.sqrt(g / (g - 1) * float(np.sum((s - m * cnt) ** 2))) / n
    return n, float(m), float(m / se) if se > 0 else None


def table(df):
    out = []
    for place in sorted(df["place"].unique()):
        sub = df[df["place"] == place]
        hows = ["全部"] if set(sub["how"]) == {"全部"} else ["全部", "抜けた", "戻された"]
        for how in hows:
            s2 = sub if how == "全部" else sub[sub["how"] == how]
            for hz in HORIZ:
                n, m, z = zstat(s2[f"f{hz}"], s2["day"])
                out.append({"place": place, "how": how, "h": hz, "n": n, "mean": m, "z": z, "atr_pips": float(s2["atr_pips"].median()) if n else None})
    return pd.DataFrame(out)


def main():
    rows = []
    for p in PAIRS:
        d = prepare(fetch(p))
        rows += outcomes(d, touches(d, p), p)
        print(p, len(d), "本", str(d.index.min())[:10], "〜", str(d.index.max())[:10], file=sys.stderr)
    df = pd.DataFrame(rows)
    t = table(df)
    pd.set_option("display.width", 200, "display.max_rows", 200)
    print(t.to_string(index=False, float_format=lambda x: f"{x:+.3f}"))
    print("升の数", len(t), "・目安 z", 3.4, "・超えた升", int((t["z"].abs() >= 3.4).sum()))
    return df, t


if __name__ == "__main__":
    main()
