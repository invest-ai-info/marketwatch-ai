# -*- coding: utf-8 -*-
"""R4 月末のロンドン16時の値決め前の、為替ヘッジの売り買い：その月に株が上がった国の通貨は、月末に売られやすいか。
2026-10-05 登録・オーナー「おすすめ通りにお願いします」（FX はロンドン時間を MT5 で全自動）。
出どころ＝Melvin & Prins (2015, Journal of Financial Markets 22, 50–72)。

⚠️ 物差しと判定の基準は PILLAR_PREREG.md「R4 月末のロンドン16時の値決め前の、為替ヘッジの売り買い」（事前登録・計算より先にコミット）と
   下の定数に固定。結果を見てから動かさない。出力には事前登録の中身の指紋（sha256）を書き込む。
⚠️ 日足の近い形（入る＝前の日の終値・出る＝月の最後の取引日の終値）。正確なロンドン 08:00→16:00 の窓は手元の MT5 で数える（腕B）。
⚠️ R1 の追記の直し方①②（hold_lab.clean）を当てる。直したあとも為替1日10%超・株25%超が残れば何も数えない。
⚠️ 出力 fx-month-end-lab.json / .md は GitHub 側で生成＝手元から送らない（SYNC禁忌）。
⚠️ エンジン・発火条件・固定オラクル（signal_lab_verify.py）には触れない。メールや売買の決まりは変えない。

事前登録に書いていない細かい決め方（計算より先にここで固定）:
  - 株の「前の月の最後の終値」＝その月の1日より前で一番近い終値。「前の日の終値」＝為替の前の日の日付以前で一番近い終値
  - 95%の幅は月ごとのまとまりの引き直し（10,000回）の 2.5%〜97.5%。片側 p は (当てはまった回数＋1)÷(回数＋1)
  - 前半・後半＝月を古い順に並べてちょうど半分で分ける
  - 月の真ん中＝その月で日付が15日以上の最初の取引日（読むためだけ）

実行: python fx_month_end_lab.py   （Actions の fx-month-end-lab.yml から手動で）
"""
import datetime as dt
import json
import sys

import numpy as np
import pandas as pd

from box_lab import cost_price
from hold_lab import clean
from pillar_lab import fetch, prereg_sha256

JST = dt.timezone(dt.timedelta(hours=9))
FETCH_START = "2000-01-01"
START, END = "2015-01-01", "2026-09-30"
PRE_START, PRE_END = "2004-01-01", "2014-12-31"
US = "^GSPC"
# 為替 → (その国の株, 外国の通貨を売るときのその為替の向き)
PAIRS = {"EURUSD=X": ("^STOXX50E", -1), "GBPUSD=X": ("^FTSE", -1), "USDJPY=X": ("^N225", +1), "AUDUSD=X": ("^AXJO", -1)}
PAIR_NAME = {"EURUSD=X": "ユーロドル", "GBPUSD=X": "ポンドドル", "USDJPY=X": "ドル円", "AUDUSD=X": "豪ドル米ドル"}
FX_MAX, EQ_MAX = 0.10, 0.25
N_BOOT = 10000
ALPHA = 0.05
SEED = 20261008
VERDICTS = ("◎ 残っている", "◯ 傾向", "差なし")
TITLE = "月末の最後の取引日に、その月の株の上げ（外国−米国）がプラスの国の通貨を売る（日足の近い形・4ペア）"
OUT_JSON, OUT_MD = "fx-month-end-lab.json", "fx-month-end-lab.md"


def _asof(s, day):
    v = s.loc[:pd.Timestamp(day)]
    return float(v.iloc[-1]) if len(v) else np.nan


def month_trades(pair, fx, eq_f, eq_us, start, end, rule="last"):
    """月ごとの取引（rule＝last：月の最後の取引日／mid：月の真ん中の日）"""
    sell_sign = PAIRS[pair][1]
    d = pd.DatetimeIndex(fx.index)
    ym = d.year * 12 + d.month
    rows = []
    for key in sorted(set(ym)):
        idx = np.flatnonzero(ym == key)
        if rule == "last":
            t1 = idx[-1]
        else:
            later = [i for i in idx if d[i].day >= 15]
            if not later:
                continue
            t1 = later[0]
        t0 = t1 - 1
        if t0 < 0 or d[t1] < pd.Timestamp(start) or d[t1] > pd.Timestamp(end):
            continue
        month_start = pd.Timestamp(year=d[t1].year, month=d[t1].month, day=1)
        base = month_start - pd.Timedelta(days=1)
        rf = _asof(eq_f, d[t0]) / _asof(eq_f, base) - 1
        ru = _asof(eq_us, d[t0]) / _asof(eq_us, base) - 1
        sig = rf - ru
        if not np.isfinite(sig) or sig == 0:
            continue
        pos = sell_sign if sig > 0 else -sell_sign
        raw = float(fx.iloc[t1] / fx.iloc[t0] - 1)
        rows.append({"month": f"{d[t1].year}-{d[t1].month:02d}", "pair": pair, "signal": float(sig),
                     "gross": pos * raw, "net": pos * raw - cost_price(pair) / float(fx.iloc[t0]), "raw": raw})
    return rows


def cluster_stats(rows, rng, n_boot=N_BOOT):
    """月ごとのまとまりで引き直した平均の幅・前半後半・偽薬（向きをコインで）"""
    df = pd.DataFrame(rows)
    months = sorted(df["month"].unique())
    g = df.groupby("month")["net"].agg(["sum", "count"]).reindex(months)
    sums, cnts = g["sum"].to_numpy(), g["count"].to_numpy()
    idx = rng.integers(0, len(months), (n_boot, len(months)))
    boot = sums[idx].sum(axis=1) / cnts[idx].sum(axis=1)
    half = months[len(months) // 2]
    gross = df["gross"].to_numpy()
    coins = rng.choice([-1.0, 1.0], size=(n_boot, len(gross)))
    plac = (coins * gross).mean(axis=1)
    p = (int((plac >= gross.mean() - 1e-15).sum()) + 1) / (n_boot + 1)
    return {"n": len(df), "months": len(months), "mean": float(df["net"].mean()), "lo": float(np.percentile(boot, 2.5)),
            "hi": float(np.percentile(boot, 97.5)), "first": float(df[df["month"] < half]["net"].mean()),
            "second": float(df[df["month"] >= half]["net"].mean()), "p": p,
            "hit_rate": float((df["gross"] > 0).mean()), "mean_gross": float(df["gross"].mean())}


def judge(st):
    if st["mean"] > 0 and st["first"] > 0 and st["second"] > 0 and st["p"] < ALPHA:
        return VERDICTS[0] if st["lo"] > 0 else VERDICTS[1]
    return VERDICTS[2]


def simple(rows):
    if not rows:
        return {"n": 0, "mean": None}
    x = np.array([r["net"] for r in rows])
    return {"n": len(x), "mean": float(x.mean()), "hit_rate": float((np.array([r["gross"] for r in rows]) > 0).mean())}


def load(fetcher=fetch):
    """→ ({表記: 直した終値}, 失敗の説明のリスト, 直した記録)"""
    out, failed, fixes = {}, [], {}
    for tk in [US] + [v[0] for v in PAIRS.values()] + list(PAIRS):
        df = fetcher(tk, "1d", start=FETCH_START)
        if df is None:
            failed.append(f"{tk}: 取れない")
            continue
        s = df["Close"].astype(float)
        s = s[s > 0]
        s, fx = clean(s, fx=tk in PAIRS)
        if fx:
            fixes[tk] = fx
        lim = FX_MAX if tk in PAIRS else EQ_MAX
        ch = s[s.index >= pd.Timestamp(PRE_START)].pct_change().abs().dropna()
        if len(ch) and ch.max() > lim:
            failed.append(f"{tk}: 直したあとも1日 {ch.max() * 100:.1f}%（{ch.idxmax().date()}）が {lim * 100:.0f}% を超える")
        out[tk] = s
    return out, failed, fixes


def run(series, rng):
    main_rows, pre_rows, mid_rows, by_pair = [], [], [], {}
    for pair, (eq, _) in PAIRS.items():
        fx, ef, eu = series[pair], series[eq], series[US]
        r = month_trades(pair, fx, ef, eu, START, END)
        main_rows += r
        by_pair[pair] = simple(r)
        pre_rows += month_trades(pair, fx, ef, eu, PRE_START, PRE_END)
        mid_rows += month_trades(pair, fx, ef, eu, START, END, rule="mid")
    st = cluster_stats(main_rows, rng)
    st["verdict"] = judge(st)
    sig = np.abs([r["signal"] for r in main_rows])
    top = [r for r, a in zip(main_rows, sig) if a >= np.quantile(sig, 2 / 3)]
    reading = {"by_pair": by_pair, "pre_publication": simple(pre_rows), "top_third_signal": simple(top),
               "mid_month": simple(mid_rows)}
    return st, reading, main_rows


def _p(x, nd=3):
    return "—" if x is None else f"{x * 100:+.{nd}f}%"


def render_md(out):
    L = ["# R4 月末のロンドン16時の値決め前の、為替ヘッジの売り買い（日足の近い形）", "",
         f"- 生成: {out['generated_jst']}　事前登録の指紋（PILLAR_PREREG.md の sha256）: `{out['prereg_sha256']}`",
         "- 物差しと判定＝PILLAR_PREREG.md「R4」（計算より先にコミット）。出どころ＝Melvin & Prins (2015)。**論文のあと（2015-01〜2026-09）・1回だけ数えた結果**",
         "- 決まり：月の最後の取引日に、その月の株の上げ（外国−米国）がプラスなら外国の通貨を売る・マイナスなら買う。前の日の終値で入り、最後の取引日の終値で出る",
         "- 費用＝これまでのラボと同じ控えめな値（円のペア 1.2pips・ほか 1.8pips の往復）", ""]
    if out["failed"]:
        return "\n".join(L + ["## ⚠️ データの取得の失敗", ""] + [f"- {x}" for x in out["failed"]] +
                         ["", "何も数えていない。直し方を登録してから、やり直す。", ""]) + "\n"
    s, rd = out["result"], out["reading"]
    L += ["## 判定", "", f"**{s['verdict']}**", "",
          "| 回数（月） | 費用後の平均（1回） | 95%の幅 | 前半 | 後半 | 当たった割合 | 偽薬との比較 p |", "|---|---|---|---|---|---|---|",
          f"| {s['n']}（{s['months']}か月） | {_p(s['mean'])} | {_p(s['lo'])}〜{_p(s['hi'])} | {_p(s['first'])} | {_p(s['second'])} | "
          f"{s['hit_rate'] * 100:.0f}% | {s['p']:.4f} |", "",
          "## 読むための表（判定には使わない）", "", "| 区分 | 回数 | 費用後の平均 | 当たった割合 |", "|---|---|---|---|"]
    for pair, x in rd["by_pair"].items():
        L.append(f"| {PAIR_NAME[pair]} | {x['n']} | {_p(x['mean'])} | {x.get('hit_rate', 0) * 100:.0f}% |")
    for k, name in (("pre_publication", "論文の前の期間（2004〜2014）"), ("top_third_signal", "株の上げの差が大きい上位3分の1"),
                    ("mid_month", "同じ決まりを月の真ん中の日に当てたもの（比べるため）")):
        x = rd[k]
        L.append(f"| {name} | {x['n']} | {_p(x['mean'])} | {x.get('hit_rate', 0) * 100:.0f}% |")
    if out.get("data_fixes"):
        L += ["", "データの直し：" + "／".join(f"{tk} {x['kind']} {x['from']}" for tk, xs in out["data_fixes"].items() for x in xs)]
    L += ["", "## 読み方の約束と限界", "",
          "- ◎・◯ なら、次は手元の MT5 の1時間足でロンドン 08:00→16:00 の正確な窓を同じ決まりで数える（腕B）。そのあと MT5 のデモで前向き",
          "- 日足の近い形は値決めのあとの戻りの数時間まで含むので、効果を小さく見積もりやすい。差なしでも値決めの前の数時間だけには残っている可能性がある",
          "- 指数は配当なし・持ち越しの金利は入れていない・Yahoo の為替の日足の区切りは業者と違う。過去の成績は将来を約束しない。情報提供であり投資助言ではない", ""]
    return "\n".join(L) + "\n"


def main():
    rng = np.random.default_rng(SEED)
    series, failed, fixes = load()
    today = dt.datetime.now(JST).date().isoformat()
    out = {"generated_jst": dt.datetime.now(JST).strftime("%Y-%m-%dT%H:%M+09:00"), "prereg_sha256": prereg_sha256(),
           "kind": "backtest", "section": "R4", "failed": failed, "data_fixes": fixes, "titles": {"R4": TITLE}, "verdicts": {}}
    if not failed:
        st, reading, rows = run(series, rng)
        out.update({"result": st, "reading": reading})
        if st["verdict"] == VERDICTS[2]:
            out["verdicts"]["R4"] = {"status": "stop", "decided_on": today, "n": st["n"], "mean": st["mean"], "lo": st["lo"],
                                     "hi": st["hi"], "reason": "費用後の平均がプラスと言えない（日足の近い形・論文のあとの期間・1回だけ数えた）"}
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    md = render_md(out)
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(md)
    print(md)
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
