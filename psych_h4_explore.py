# -*- coding: utf-8 -*-
"""PS3 4時間足でチャートの形に聞く（重要な経済指標の前に手じまう）。2026-11-11・PILLAR_PREREG.md「PS3」。

〜2025年で学び、2026年で1回だけ確かめる。読むだけ・何も書き出さない。
実行: python psych_h4_explore.py
"""
import sys

import numpy as np
import pandas as pd

import psych_levels_explore as PS

HOLD, ATR_N = 6, 30
SPLIT = "2026-01-01"
TOP, COST_PIPS, N_MIN, Z_MIN = 0.90, 1.5, 300, 2.0
BAR = pd.Timedelta(hours=4)
EVENT_MARGIN = pd.Timedelta(minutes=30)
PARAMS = dict(max_depth=3, learning_rate=0.05, max_iter=200, min_samples_leaf=200, l2_regularization=1.0, random_state=0)


def to_h4(d):
    g = d.resample("4h", origin="epoch")
    out = pd.DataFrame({"open": g["open"].first(), "high": g["high"].max(), "low": g["low"].min(), "close": g["close"].last()}).dropna()
    return out


def events_2026():
    """[(UTC の時刻, 対象の一覧)]。impact が high か critical"""
    import sync_economic_events as S
    out = []
    for mo, day, _c, _imp, name, _note in S.load_source_rows():
        rule = S.match_rule(name)
        if not rule:
            continue
        e = S.build_entry(2026, mo, day, rule, name)
        if e.get("impact") in ("high", "critical"):
            out.append((pd.Timestamp(e["datetime"]).tz_convert("UTC"), tuple(e.get("affected_assets") or ())))
    return sorted(out)


def events_for(pair, ev):
    key = pair + "=X"
    return [t for t, assets in ev if "all" in assets or key in assets]


def features(d, pair):
    o, h, l, c = d["open"], d["high"], d["low"], d["close"]
    A = (h - l).rolling(ATR_N).mean().shift(1)
    F = {}
    for k in range(1, 13):
        F[f"r{k}"] = (c.shift(k - 1) - c.shift(k)) / A
    F["sum6"] = (c - c.shift(6)) / A
    F["sum30"] = (c - c.shift(30)) / A
    for n in (6, 30, 120):
        hi, lo = h.rolling(n).max(), l.rolling(n).min()
        F[f"pos{n}"] = (c - lo) / (hi - lo)
        F[f"up{n}"] = (hi - c) / A
        F[f"dn{n}"] = (c - lo) / A
    F["range"] = (h - l) / A
    F["body"] = (c - o) / A
    F["wick_up"] = (h - np.maximum(o, c)) / A
    F["wick_dn"] = (np.minimum(o, c) - l) / A
    F["vol6"] = (h - l).rolling(6).mean() / A
    dlt = c.diff()
    up, dn = dlt.clip(lower=0).rolling(14).mean(), (-dlt.clip(upper=0)).rolling(14).mean()
    F["rsi"] = 100 * up / (up + dn)
    macd = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
    F["macd_hist"] = (macd - macd.ewm(span=9, adjust=False).mean()) / A
    ma20, ma75, sd20 = c.rolling(20).mean(), c.rolling(75).mean(), c.rolling(20).std()
    F["ma20"] = (c - ma20) / A
    F["ma75"] = (c - ma75) / A
    F["ma20_slope"] = (ma20 - ma20.shift(5)) / A
    F["bb"] = (c - ma20) / (2 * sd20)
    F["hour"] = pd.Series(d.index.hour, index=d.index).astype(float)
    F["wday"] = pd.Series(d.index.weekday, index=d.index).astype(float)
    st = 100 * PS.pip(pair)
    F["round"] = (c % st) / st
    X = pd.DataFrame(F)
    X["y"] = (c.shift(-HOLD) - c) / A
    X["atr"] = A
    X["close"] = c
    X["pair"] = pair
    X["date"] = np.asarray([x.isoformat() for x in d.index.date])
    return X.replace([np.inf, -np.inf], np.nan)


def exit_steps(times, i, ev_times):
    """足 i の終値で入ったとき、何本あとの終値で出るか（0＝入らない）と、指標で早まったか"""
    end_i = times[i] + BAR
    nxt = next((e for e in ev_times if e > end_i), None)
    k, by_event = 0, False
    for j in range(i + 1, min(i + HOLD, len(times) - 1) + 1):
        if times[j] - times[j - 1] != BAR:
            break
        if nxt is not None and times[j] + BAR > nxt - EVENT_MARGIN:
            by_event = True
            break
        k = j - i
    return k, by_event


def main():
    from sklearn.ensemble import HistGradientBoostingRegressor
    ev = events_2026()
    frames = {p: features(to_h4(PS.fetch(p)), p) for p in PS.PAIRS}
    X = pd.concat(frames.values())
    cols = [c for c in X.columns if c not in ("y", "atr", "close", "pair", "date")]
    tr = X[X["date"] < SPLIT].dropna()
    m = HistGradientBoostingRegressor(**PARAMS).fit(tr[cols].to_numpy(), tr["y"].to_numpy())
    thr = float(np.quantile(np.abs(m.predict(tr[cols].to_numpy())), TOP))
    rows, skipped, early, all_pred, all_y = [], 0, 0, [], []
    for p, F in frames.items():
        F = F.dropna(subset=cols + ["atr"])
        times = list(F.index)
        pred = m.predict(F[cols].to_numpy())
        c, A, date = F["close"].to_numpy(), F["atr"].to_numpy(), F["date"].to_numpy()
        evp = events_for(p, ev)
        for i in range(len(times)):
            if date[i] < SPLIT:
                continue
            if np.isfinite(F["y"].iloc[i]):
                all_pred.append(pred[i])
                all_y.append(F["y"].iloc[i])
            if abs(pred[i]) <= thr:
                continue
            k, by_event = exit_steps(times, i, evp)
            if k == 0:
                skipped += 1
                continue
            early += int(by_event)
            g = np.sign(pred[i]) * (c[i + k] - c[i]) / A[i]
            rows.append({"pair": p, "date": date[i], "gross": g, "net": g - COST_PIPS * PS.pip(p) / A[i], "k": k, "atr_pips": A[i] / PS.pip(p)})
    T = pd.DataFrame(rows)
    print(f"指標 {len(ev)}件・学ぶ側 {tr['date'].min()}〜{tr['date'].max()} {len(tr)}本・境目 {thr:.4f}")
    if not len(T):
        print("入った回数 0・判定: 検定不能")
        return 0
    n, mean, z = PS.zstat(T["net"], T["date"])
    _, gm, gz = PS.zstat(T["gross"], T["date"])
    print(f"確かめる側 {T['date'].min()}〜{T['date'].max()}・入った回数 {n}・入らなかった {skipped}・指標で早く出た {early}・持った本数の平均 {T['k'].mean():.2f}・足の幅の平均 {T['atr_pips'].median():.1f}pips")
    print(f"費用前の平均 {gm}  z {gz}")
    print(f"費用後の平均 {mean}  z {z}")
    print("判定:", "検定不能" if n < N_MIN else ("候補" if (z is not None and z >= Z_MIN) else "探す側では見えない"))
    print("— 読むための表 —")
    ap, ay = np.asarray(all_pred), np.asarray(all_y)
    print("予想と実際の相関:", round(float(np.corrcoef(ap, ay)[0, 1]), 4), "・本数", len(ap))
    q = pd.qcut(ap, 10, labels=False, duplicates="drop")
    print("予想の10段ごとの実際の値動き:", [round(float(ay[q == k].mean()), 4) for k in sorted(set(q))])
    print("ペアごと（回数・費用後）:", {p: (int((T["pair"] == p).sum()), round(float(T["net"][T["pair"] == p].mean()), 4)) for p in PS.PAIRS if (T["pair"] == p).any()})
    from sklearn.inspection import permutation_importance
    va = X[X["date"] >= SPLIT].dropna()
    imp = permutation_importance(m, va[cols].to_numpy(), va["y"].to_numpy(), n_repeats=3, random_state=0)
    print("効いた数字:", [(k, round(float(v), 5)) for k, v in sorted(zip(cols, imp.importances_mean), key=lambda t: -t[1])[:8]])
    return 0


if __name__ == "__main__":
    sys.exit(main())
