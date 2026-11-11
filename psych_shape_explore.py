# -*- coding: utf-8 -*-
"""PS2 チャートの形そのものに聞く（探す側・Yahoo の1時間足）。2026-11-11・PILLAR_PREREG.md「PS2」。

直前の値動きの形だけから4本あとの向きを勾配ブースティングに学ばせ、後半40%で1回だけ確かめる。読むだけ・何も書き出さない。
実行: python psych_shape_explore.py
"""
import sys

import numpy as np
import pandas as pd

import psych_levels_explore as PS

HOLD, ATR_N = 4, 120
TRAIN_FRAC, GAP_DAYS = 0.60, 2
TOP = 0.90
COST_PIPS = 1.5
N_MIN, Z_MIN = 300, 2.0
PARAMS = dict(max_depth=3, learning_rate=0.05, max_iter=200, min_samples_leaf=200, l2_regularization=1.0, random_state=0)


def features(d, pair):
    o, h, l, c = d["open"], d["high"], d["low"], d["close"]
    A = (h - l).rolling(ATR_N).mean().shift(1)
    F = {}
    for k in range(1, 25):
        F[f"r{k}"] = (c.shift(k - 1) - c.shift(k)) / A
    F["sum24"] = (c - c.shift(24)) / A
    F["sum120"] = (c - c.shift(120)) / A
    for n in (24, 120, 480):
        hi, lo = h.rolling(n).max(), l.rolling(n).min()
        F[f"pos{n}"] = (c - lo) / (hi - lo)
        F[f"up{n}"] = (hi - c) / A
        F[f"dn{n}"] = (c - lo) / A
    F["range"] = (h - l) / A
    F["body"] = (c - o) / A
    F["wick_up"] = (h - np.maximum(o, c)) / A
    F["wick_dn"] = (np.minimum(o, c) - l) / A
    F["vol24"] = (h - l).rolling(24).mean() / A
    F["hour"] = pd.Series(d.index.hour, index=d.index).astype(float)
    F["wday"] = pd.Series(d.index.weekday, index=d.index).astype(float)
    st = 100 * PS.pip(pair)
    F["round"] = (c % st) / st
    X = pd.DataFrame(F)
    X["y"] = (c.shift(-HOLD) - c) / A
    X["cost"] = COST_PIPS * PS.pip(pair) / A
    X["pair"] = pair
    X["date"] = np.asarray([x.isoformat() for x in d.index.date])
    return X.replace([np.inf, -np.inf], np.nan).dropna()


def zstat(v, days):
    n, m, z = PS.zstat(v, days)
    return n, m, z


def main():
    from sklearn.ensemble import HistGradientBoostingRegressor
    X = pd.concat([features(PS.fetch(p), p) for p in PS.PAIRS])
    dates = sorted(X["date"].unique())
    cut = dates[int(len(dates) * TRAIN_FRAC)]
    start_va = dates[int(len(dates) * TRAIN_FRAC) + GAP_DAYS]
    tr, va = X[X["date"] < cut], X[X["date"] >= start_va]
    cols = [c for c in X.columns if c not in ("y", "cost", "pair", "date")]
    m = HistGradientBoostingRegressor(**PARAMS).fit(tr[cols].to_numpy(), tr["y"].to_numpy())
    thr = float(np.quantile(np.abs(m.predict(tr[cols].to_numpy())), TOP))
    pv = m.predict(va[cols].to_numpy())
    va = va.assign(pred=pv)
    pick = va[np.abs(va["pred"]) > thr]
    gross = np.sign(pick["pred"]) * pick["y"]
    net = gross - pick["cost"]
    n, mean, z = zstat(net, pick["date"])
    _, gmean, gz = zstat(gross, pick["date"])
    print(f"学ぶ側 {tr['date'].min()}〜{tr['date'].max()} {len(tr)}本／確かめる側 {va['date'].min()}〜{va['date'].max()} {len(va)}本・境目 {thr:.4f}")
    print(f"入った回数 {n}（確かめる側の {len(pick) / len(va) * 100:.1f}%）")
    print(f"費用前の平均 {gmean}  z {gz}")
    print(f"費用後の平均 {mean}  z {z}  ・費用の平均 {pick['cost'].mean() if len(pick) else None}")
    verdict = "検定不能" if n < N_MIN else ("候補" if (z is not None and z >= Z_MIN) else "探す側では見えない")
    print("判定:", verdict)
    print("— 読むための表 —")
    allg = np.sign(va["pred"]) * va["y"]
    print("確かめる側ぜんぶ（予想の向きに入った場合）費用前:", zstat(allg, va["date"]))
    q = pd.qcut(va["pred"], 10, labels=False, duplicates="drop")
    print("予想の10段ごとの実際の値動き（平均）:", [round(float(va["y"][q == k].mean()), 4) for k in sorted(q.unique())])
    print("予想と実際の相関:", round(float(np.corrcoef(va["pred"], va["y"])[0, 1]), 4))
    if len(pick):
        print("ペアごと（回数・費用後）:", {p: (int((pick["pair"] == p).sum()), round(float(net[pick["pair"] == p].mean()), 4)) for p in PS.PAIRS if (pick["pair"] == p).any()})
    from sklearn.inspection import permutation_importance
    sub = va.sample(min(20000, len(va)), random_state=0)
    imp = permutation_importance(m, sub[cols].to_numpy(), sub["y"].to_numpy(), n_repeats=3, random_state=0)
    top = sorted(zip(cols, imp.importances_mean), key=lambda t: -t[1])[:8]
    print("効いた数字（確かめる側）:", [(k, round(float(v), 5)) for k, v in top])


if __name__ == "__main__":
    sys.exit(main())
