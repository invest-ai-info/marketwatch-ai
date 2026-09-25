# -*- coding: utf-8 -*-
"""
stop_lab.py — 損切りラボ：損切りの置き方（ATRの何倍か／固定％か）で期待値は変わるか。

2026-09-26 オーナー指示「4つとも登録して前向きに検証して」の④（損切りの研究）。オーナーの考え＝
「損切りは何％でもいい」。それが本当か（損切りの幅や決め方で、損切り幅あたりの期待値が変わらないか）を確かめる。

【事前登録（2026-09-26・本物のデータの結果を見る前に、この説明文ごとコミットして固定する）】
対象・入口・足・族・売りの扱い・約定・コスト・最長120本・未決着の扱いは exit_wall_lab.py と同じ。
利確   : 全方式で同じ＝入値 ± 2.0ATR（いまの方式）。損切りだけを変える。
損切り（1R＝その方式の損切り幅。ロットを損切り幅から逆算する運用と同じ物差し）:
  A10 ATRの1.0倍 ／ A15 ATRの1.5倍（いまの方式＝比べる基準）／ A20 ATRの2.0倍 ／ A30 ATRの3.0倍
  F   固定％（銘柄ごと）: その銘柄の 2015年までの入口の「1.5ATR÷入値」の中央値（＝平均的にはいまの方式と同じ大きさ）。
      値動きが大きい時も小さい時も同じ％で切る＝「ATRに合わせるか、％で固定するか」だけを比べる
  Fh  固定％の半分 ／ Fd 固定％の倍
  U1  全銘柄一律 1％（素朴な決め方の参考）
      ※ 4時間足の F は4時間足の ATR で決める。4時間足は2015年以前のデータが無いので、その銘柄の全期間の中央値を使う
        （副＝最近2年の再現確認なので、大きさの決め方にだけ後知恵を許す）。
主の比較（日足）: 族（2）× 各方式 − A15（7）＝14の比較。同じ入口どうしの差（exit_rule_backtest._mean_se_safe＝
         保守版の二方向クラスタ・銘柄×年・t補正）。p値は exit_lab と同じ出し方。
「差がある」と言う条件: ①p値 < ボンフェローニ法（10%÷14） ②差 0.10R 以上 ③前半（〜2015）と後半（2016〜）で向きがそろう。
偽薬   : exit_wall_lab と同じ（同じ銘柄・向き・件数のランダムな入口に同じ方式）。「差がある」のうち、偽薬の差を引いても
         同じ向きに 0.05R 以上残るものだけを「シグナルの場面に効く」と書き、残らなければ「相場の性質（どこで入っても同じ）」と書く。
前向き : lab_forward.FWD_FROM（2026-09-26）以降に入った取引だけで、主の14比較を毎週出す。探索（登録日より前）で
         「差がある」になった比較は、lab_forward の決まり（件数100ごと・95%幅と0.10R・合格2回連続で確定）で判定する。
較正（本物のデータを見る前・--synthetic）: regime_lab.synthetic（256歩）で同じ手順を回し、主の14比較の誤検出を数える。
         結果はこの下に追記する（基準は動かさない）。
  較正の結果（2026-09-26・本物のデータを見る前）: 作り物20回（乱数1〜20・日足＋4時間足・256歩）で、主の14比較に
         「差がある」は**0回**。最小p値がボンフェローニの線（0.0071）を下回ったのは20回中3回（理屈どおり約1割）。
         作り物の方式ごとの平均（コスト後）は −0.05〜+0.03R＝どれも0の近く（計算に偏りなし）。
限界   : 損切りは線ちょうどで約定（滑りは入っていない＝損切りが近い方式ほど、実際より少し有利に見積もられうる）／
         狭い損切りほどコストが R で重くなる（これは本物でも起きる実在の差）／先物のつなぎ目／逆張りは買いだけ。
公開   : しない（オーナー個人向けの研究。売買の推奨ではない）。

使い方（Yahoo に届く所で）: python stop_lab.py --json stop-lab.json --md stop-lab.md
       較正（どこでも）      : python stop_lab.py --synthetic 1,2,3
"""
import argparse
import json
import math
import sys

import numpy as np
import pandas as pd

import exit_rule_backtest as X
import exit_wall_lab as W
import lab_forward as LF
import regime_lab as RL
from signal_lab_sweep import cost_r_of
from signal_lab_tracker import LEGACY_UNIVERSE

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TP_ATR = 2.0
MAX_HOLD = W.MAX_HOLD
SPLIT = W.SPLIT
ALPHA, MIN_EFFECT, PLACEBO_KEEP = 0.10, 0.10, 0.05
BASE = "A15"
STOPS = ("A10", "A15", "A20", "A30", "F", "Fh", "Fd", "U1")
STOP_LABEL = {"A10": "ATRの1.0倍", "A15": "ATRの1.5倍（いまの方式）", "A20": "ATRの2.0倍", "A30": "ATRの3.0倍",
              "F": "固定％（いまと同じ大きさ）", "Fh": "固定％の半分", "Fd": "固定％の倍", "U1": "一律1％"}
SYN_STEPS = W.SYN_STEPS


def run_sl(A, i, sl_dist, tp):
    """損切り幅 sl_dist（値段）・利確 tp（値段）の1取引。戻り値＝(R コスト前, 保有本数) か (None, None)。"""
    o, h, l, c = A["o"], A["h"], A["l"], A["c"]
    n, e = len(c), c[i]
    stop = e - sl_dist
    for j in range(i + 1, min(n, i + MAX_HOLD + 1)):
        if l[j] <= stop:
            return (min(o[j], stop) - e) / sl_dist, j - i
        if h[j] >= tp:
            return (tp - e) / sl_dist, j - i
        if j == i + MAX_HOLD:
            return (c[j] - e) / sl_dist, j - i
    return None, None


def stop_dists(e, atr, fixed_pct):
    return {"A10": 1.0 * atr, "A15": 1.5 * atr, "A20": 2.0 * atr, "A30": 3.0 * atr,
            "F": fixed_pct * e, "Fh": 0.5 * fixed_pct * e, "Fd": 2.0 * fixed_pct * e, "U1": 0.01 * e}


def fixed_pct_of(df):
    """その銘柄の 2015年までの足の 1.5ATR÷終値 の中央値（固定％の大きさ＝事前に分かる値）。"""
    A = W.arrays(df)
    idx = pd.to_datetime(df.index)
    idx = idx.tz_convert(None) if idx.tz is not None else idx
    m = (idx < SPLIT) & np.isfinite(A["atr"]) & (A["c"] > 0)
    v = 1.5 * A["atr"][m] / A["c"][m]
    v = v[np.isfinite(v)]
    return float(np.median(v)) if len(v) else float(np.nanmedian(1.5 * A["atr"] / A["c"]))


def lab_trades(df, ticker, tf, fixed_pct, placebo_rng=None):
    sig = X.signals(df)
    A0 = W.arrays(df)
    Am = W.mirror(A0)
    times = pd.to_datetime(df.index)
    times = times.tz_convert(None) if times.tz is not None else times
    n, out = len(A0["c"]), []
    for es, side in RL.ENTRIES:
        A = A0 if side == "long" else Am
        ent = sig[es].to_numpy(bool)
        idx, last = [], -10 ** 9
        for i in range(W.WARMUP, n - 1):
            if ent[i] and i - last > X.COOLDOWN and A["atr"][i] > 0:
                idx.append(i)
                last = i
        if placebo_rng is not None:
            pool = np.arange(W.WARMUP, n - 1)
            idx = sorted(placebo_rng.choice(pool, size=min(len(idx), len(pool)), replace=False).tolist())
        for i in idx:
            atr = A["atr"][i]
            if not (atr > 0):
                continue
            e = A["c"][i]
            e_abs = abs(e)
            dists = stop_dists(e_abs, atr, fixed_pct)
            tp = e + TP_ATR * atr
            res = {k: run_sl(A, i, dv, tp) for k, dv in dists.items()}
            if any(v[0] is None for v in res.values()):
                continue
            sgn = 1 if side == "long" else -1
            cost = {k: cost_r_of({"entry": e_abs, "stop_loss": e_abs - sgn * dv, "ticker": ticker})
                    for k, dv in dists.items()}
            out.append({"ticker": ticker, "cls": RL.CLASS_OF.get(ticker, "?"), "tf": tf, "es": es, "side": side,
                        "fam": RL.FAMILY[(es, side)], "time": times[i],
                        "R": {k: v[0] - cost[k] for k, v in res.items()},
                        "gross": {k: v[0] for k, v in res.items()},
                        "bars": {k: v[1] for k, v in res.items()},
                        "sl_atr": {k: dists[k] / atr for k in dists}})
    return out


def paired(ts, a, b=BASE, cluster=RL.cluster):
    sel = [t for t in ts if a in t["R"] and b in t["R"]]
    dd = W.mean_ci_safe([t["R"][a] - t["R"][b] for t in sel], [cluster(t) for t in sel])
    dd["p"] = RL.p_value(dd)
    return dd


def key_of(F, s):
    return f"1d|{F}|{s}"


def evaluate(ts1d, ts4h, pl1d, pl4h, fwd1d=None, prev_forward=None, today=None):
    fam = lambda ts, F: [t for t in ts if t["fam"] == F]
    primary = []
    for F in ("tf", "mr"):
        base = fam(ts1d, F)
        for s in STOPS:
            if s == BASE:
                continue
            r = {"fam": F, "stop": s, "diff": paired(base, s), "gross": paired([dict(t, R=t["gross"]) for t in base], s),
                 "early": paired([t for t in base if t["time"] < SPLIT], s),
                 "late": paired([t for t in base if t["time"] >= SPLIT], s),
                 "placebo": paired(fam(pl1d, F), s),
                 "h4": paired(fam(ts4h, F), s) if ts4h else {},
                 "classes": {k: paired([t for t in base if t["cls"] == k], s) for k in ("index", "fx", "commodity")}}
            primary.append(r)
    m = len(primary)
    for r in primary:
        d = r["diff"]
        s0 = RL._sign(d)
        same = RL._sign(r["early"]) is not None and RL._sign(r["early"]) == RL._sign(r["late"]) == s0
        r["flag"] = bool(d.get("p", 1.0) < ALPHA / m and abs(d.get("avg", 0)) >= MIN_EFFECT and same)
        pl = r["placebo"].get("avg")
        r["net_of_placebo"] = None if pl is None or "avg" not in d else d["avg"] - pl
        r["situational"] = bool(r["flag"] and r["net_of_placebo"] is not None and s0
                                and r["net_of_placebo"] * s0 >= PLACEBO_KEEP)
    baseline = {}
    for label, ts in (("1d", ts1d), ("4h", ts4h), ("placebo1d", pl1d)):
        for F in ("tf", "mr"):
            rows = fam(ts, F)
            if rows:
                baseline[f"{label}|{F}"] = {s: {"avg": float(np.mean([t["R"][s] for t in rows])),
                                                "win": float(np.mean([t["R"][s] > 0 for t in rows])),
                                                "bars_median": float(np.median([t["bars"][s] for t in rows])),
                                                "sl_atr_median": float(np.median([t["sl_atr"][s] for t in rows]))}
                                            for s in STOPS}
                baseline[f"{label}|{F}"]["n"] = len(rows)
    # 前向き（登録日以降）: 主の14比較を毎週出す。探索で「差がある」になった比較だけ lab_forward で判定を積み上げる
    forward = {}
    if fwd1d is not None:
        for r in primary:
            k = key_of(r["fam"], r["stop"])
            d = paired(fam(fwd1d, r["fam"]), r["stop"], cluster=LF.fwd_cluster)
            if r["flag"]:
                forward[k] = LF.step((prev_forward or {}).get(k), d, RL._sign(r["diff"]), today)
            else:
                forward[k] = {"n": d.get("n", 0), "now": d, "state": "（探索で差なし＝参考表示）"}
    return {"primary": primary, "baseline": baseline, "forward": forward}


def build(frames, tf, seed=12345, fixed=None):
    rng = np.random.default_rng(seed)
    ts, pl = [], []
    for tk, df in frames.items():
        fp = (fixed or {}).get(tk) or fixed_pct_of(df)
        ts += lab_trades(df, tk, tf, fp)
        pl += lab_trades(df, tk, tf, fp, placebo_rng=rng)
    return ts, pl


def fmt(dd):
    if not dd or dd.get("avg") is None:
        return "—"
    if "lo" not in dd:
        return f"{dd['avg']:+.3f}R"
    return f"{dd['avg']:+.3f}R [{dd['lo']:+.2f}, {dd['hi']:+.2f}]"


def report_md(res, asof, n1, n4, fixed):
    L = [f"# 損切りラボ（asof {asof}）", "", f"日足 {n1:,} 取引・4時間足 {n4:,} 取引（登録日 {LF.FWD_FROM.date()} より前＝探索）", "",
         "固定％（銘柄ごと・2015年までの 1.5ATR÷値段 の中央値）: "
         + "、".join(f"{t} {v * 100:.2f}%" for t, v in sorted(fixed.items())), "",
         "## 主の比較（日足・同じ入口どうしの A15＝いまの方式 との差・コスト後・1R＝その方式の損切り幅）", "",
         "| 族 | 損切り | 差 | p | 前半 | 後半 | コスト前 | 偽薬の差 | 4時間足 | 判定 |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in res["primary"]:
        v = ("✅差がある" + ("（シグナルの場面に効く）" if r["situational"] else "（相場の性質）")) if r["flag"] else "—"
        L.append(f"| {RL.FAMILY_LABEL[r['fam']]} | {STOP_LABEL[r['stop']]} | {fmt(r['diff'])} | {r['diff'].get('p', 1):.4f} | "
                 f"{fmt(r['early'])} | {fmt(r['late'])} | {fmt(r['gross'])} | {fmt(r['placebo'])} | {fmt(r['h4'])} | {v} |")
    L += ["", "## 方式ごとの平均（コスト後・勝率・損切り幅の中央値[ATR]・保有本数の中央値）", ""]
    for k, b in res["baseline"].items():
        L.append(f"- {k}（n={b['n']:,}）: " + " ／ ".join(
            f"{s} {b[s]['avg']:+.3f}R・{b[s]['win']:.0%}・{b[s]['sl_atr_median']:.2f}ATR・{b[s]['bars_median']:.0f}本" for s in STOPS))
    if res.get("forward"):
        L += ["", f"## 前向き（{LF.FWD_FROM.date()} 以降に入った取引だけ）", ""]
        for k, f in res["forward"].items():
            L.append(f"- {k}: n={f['n']} {fmt(f.get('now'))} {f['state']}")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json")
    ap.add_argument("--md")
    ap.add_argument("--synthetic")
    ap.add_argument("--no-4h", action="store_true")
    a = ap.parse_args()
    if a.synthetic:
        for seed in [int(s) for s in a.synthetic.split(",")]:
            f1, _ = RL.synthetic(seed, "1d", steps=SYN_STEPS)
            ts1d, pl1d = build(f1, "1d", seed)
            ts4h, pl4h = ([], []) if a.no_4h else build(RL.synthetic(seed + 10_000, "4h", steps=SYN_STEPS)[0], "4h", seed)
            res = evaluate(ts1d, ts4h, pl1d, pl4h)
            fl = [f"{RL.FAMILY_LABEL[r['fam']]}×{r['stop']}({r['diff']['avg']:+.3f})" for r in res["primary"] if r["flag"]]
            pmin = min(r["diff"].get("p", 1.0) for r in res["primary"])
            b = res["baseline"]
            base = " ".join(f"{k}:" + "/".join(f"{b[k][s]['avg']:+.2f}" for s in STOPS) for k in b if k.startswith("1d"))
            print(f"seed={seed} 日足{len(ts1d):,} 目立つ={sum(r['flag'] for r in res['primary'])} 最小p={pmin:.4f} "
                  f"{fl or 'なし'} | {base}", flush=True)
        return
    f1, f4, fixed = {}, {}, {}
    for tk in sorted(LEGACY_UNIVERSE):
        df = X.fetch(tk, "1d")
        if df is not None:
            f1[tk] = df
            fixed[tk] = fixed_pct_of(df)
        if not a.no_4h:
            df4 = X.fetch(tk, "4h")
            if df4 is not None:
                f4[tk] = df4
        print(f"  {tk}: 日足{len(f1.get(tk, [])):,} 4h{len(f4.get(tk, [])):,}", flush=True)
    all1d, pl1d_all = build(f1, "1d", fixed=fixed)
    all4h, pl4h_all = build(f4, "4h") if f4 else ([], [])   # 4時間足は自分の足の大きさで固定％を決める（下の注）
    ts1d, fwd1d = LF.split(all1d)
    ts4h, _ = LF.split(all4h)
    pl1d, _ = LF.split(pl1d_all)
    pl4h, _ = LF.split(pl4h_all)
    today = pd.Timestamp.now(tz="Asia/Tokyo").strftime("%Y-%m-%d")
    res = evaluate(ts1d, ts4h, pl1d, pl4h, fwd1d, LF.load_prev(a.json), today)
    out = {"asof": today, "fwd_from": str(LF.FWD_FROM.date()), "n_1d": len(ts1d), "n_4h": len(ts4h),
           "n_fwd_1d": len(fwd1d), "fixed_pct": fixed, **res}
    if a.json:
        json.dump(RL._jsonable(out), open(a.json, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    md = report_md(res, today, len(ts1d), len(ts4h), fixed)
    if a.md:
        open(a.md, "w", encoding="utf-8").write(md)
    print(md[:4000])


if __name__ == "__main__":
    main()
