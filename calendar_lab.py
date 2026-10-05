# -*- coding: utf-8 -*-
"""R3 株価指数の時間の癖（MT4 で全自動にできる短期）：論文が出たあとの期間だけで、月末月初と日中のモメンタムが
費用のあとも残っているか。2026-10-05 登録・オーナー「研究のテーマは短期売買」「先物は MT4 で暗号資産以外をシステムトレード化」。

⚠️ 物差しと判定の基準は PILLAR_PREREG.md「R3 株価指数の時間の癖」（事前登録・計算より先にコミット）と下の定数に固定。
   結果を見てから動かさない。出力には事前登録の中身の指紋（sha256）を書き込む。
⚠️ 1日の変化が25%を超える日があればデータの取得の失敗として何も数えない（R1 の教訓）。
⚠️ 出力 calendar-lab.json / .md は GitHub 側で生成＝手元から送らない（SYNC禁忌）。
⚠️ エンジン・発火条件・固定オラクル（signal_lab_verify.py）には触れない。メールや売買の決まりは変えない。

事前登録に書いていない細かい決め方（計算より先にここで固定）:
  - 月の「最後から k 日目」「k 日目」は、その月の取引日（データの行）で数える
  - 「ふつうの日」＝1つ前の窓の売った日の次の日から、この窓の買う日までの日々の対数の変化の平均（最初の窓はその月の初めから）
  - 窓の損益とふつうの日の比べは費用の前で行う（費用は (a) の平均にだけ入れる）
  - 引き直しは月（Q1〜Q3）／日（Q4）を単位にした 10,000 回。95%の幅は引き直しの 2.5%〜97.5%
  - 片側 p は (当てはまった回数＋1)÷(回数＋1)
  - Q4 の 15:30 の値段＝14:30 に始まる足の終値、16:00 の値段＝15:30 に始まる足の終値、前の日の終値＝前の日の最後の足の終値

実行: python calendar_lab.py   （Actions の calendar-lab.yml から手動で）
"""
import datetime as dt
import json
import math
import sys

import numpy as np
import pandas as pd

from pillar_lab import fetch, prereg_sha256

JST = dt.timezone(dt.timedelta(hours=9))
FETCH_START = "1985-01-01"
END = "2026-09-30"
FIN_RATE = 0.03
N_BOOT = 10000
N_COMPARE = 4
ALPHA = 0.05 / N_COMPARE
MAX_DAILY = 0.25
SEED = 20261007
TOM = {
    "Q1": {"name": "米国株の月末月初（S&P500・月の最後の日＋翌月の最初の3日）", "ticker": "^GSPC", "start": "1989-01-01",
           "pre": 1, "post": 3, "cost": 0.0002},
    "Q2": {"name": "日本株の月末月初（日経平均・米国と同じ窓）", "ticker": "^N225", "start": "1992-01-01",
           "pre": 1, "post": 3, "cost": 0.0003},
    "Q3": {"name": "日本株の早い月末月初（日経平均・月の最後の5日＋翌月の最初の2日）", "ticker": "^N225", "start": "1992-01-01",
           "pre": 5, "post": 2, "cost": 0.0003},
}
Q4 = {"name": "米国株の日中のモメンタム（SPY・前の日の終値→10:30 の向きに 15:30→16:00 だけ乗る）", "ticker": "SPY", "cost": 0.0002}
VERDICTS = ("◎ 残っている", "◯ 傾向", "差なし")
OUT_JSON, OUT_MD = "calendar-lab.json", "calendar-lab.md"


# ════════════════════ 共通 ════════════════════

def boot_mean(x, rng, n=N_BOOT):
    """平均を単位ごとに引き直した 10,000 個"""
    x = np.asarray(x, float)
    idx = rng.integers(0, len(x), (n, len(x)))
    return x[idx].mean(axis=1)


def judge(mean, lo, first, second, p):
    if mean > 0 and lo > 0 and first > 0 and second > 0:
        return VERDICTS[0] if p < ALPHA else (VERDICTS[1] if p < 0.05 else VERDICTS[2])
    return VERDICTS[2]


def data_ok(close):
    """1日の変化が MAX_DAILY を超える日が無いか → (よいか, 最大の変化, その日)"""
    ch = close.pct_change().abs().dropna()
    if ch.empty:
        return False, None, None
    d = ch.idxmax()
    return bool(ch.max() <= MAX_DAILY), float(ch.max()), str(pd.Timestamp(d).date())


# ════════════════════ 月末月初（Q1〜Q3） ════════════════════

def tom_trades(close, pre, post, start, end=END):
    """月の変わり目ごとの取引。→ DataFrame（買う日・売る日・費用前の損益・持った暦日・窓の対数・ふつうの日の1日平均・窓の日数）"""
    close = close.dropna()
    p = close.to_numpy(float)
    d = pd.DatetimeIndex(close.index)
    ym = np.asarray(d.year) * 12 + np.asarray(d.month)
    first_of = np.r_[0, np.flatnonzero(np.diff(ym) != 0) + 1]       # 各月の最初の行
    lr = np.r_[np.nan, np.diff(np.log(p))]
    rows, prev_sell = [], None
    for k in range(len(first_of) - 1):
        m0, m1 = first_of[k], first_of[k + 1]                       # この月の最初の行・次の月の最初の行
        nxt_end = first_of[k + 2] if k + 2 < len(first_of) else len(p)
        b = (m1 - 1) - pre                                          # 買う日（窓の前の日の終値）
        s = m1 + post - 1                                           # 売る日
        if s >= nxt_end or s >= len(p):
            break                                                   # 次の月の日がそろっていない（データの終わり）
        if b < max(m0, 1):
            prev_sell = s
            continue
        if d[b + 1] < pd.Timestamp(start) or d[s] > pd.Timestamp(end):
            prev_sell = s
            continue
        lo = prev_sell + 1 if prev_sell is not None else m0
        rest = lr[max(lo, 1):b + 1]                                 # ふつうの日＝前の窓のあと〜この窓の前
        rest = rest[~np.isnan(rest)]
        rows.append({"buy": str(d[b].date()), "sell": str(d[s].date()), "gross": p[s] / p[b] - 1,
                     "days": int((d[s] - d[b]).days), "win_log": float(np.log(p[s] / p[b])),
                     "rest_mean": float(rest.mean()) if len(rest) else np.nan, "L": int(s - b)})
        prev_sell = s
    return pd.DataFrame(rows)


def tom_eval(close, cfg, rng):
    t = tom_trades(close, cfg["pre"], cfg["post"], cfg["start"])
    t = t.dropna(subset=["rest_mean"]).reset_index(drop=True)
    fin = FIN_RATE * t["days"] / 365.0
    net = t["gross"] - cfg["cost"] - fin
    diff = t["win_log"] - t["L"] * t["rest_mean"]
    bm = boot_mean(net, rng)
    bd = boot_mean(diff, rng)
    half = len(t) // 2
    p = (int((bd <= 0).sum()) + 1) / (N_BOOT + 1)
    mean, lo, hi = float(net.mean()), float(np.percentile(bm, 2.5)), float(np.percentile(bm, 97.5))
    first, second = float(net[:half].mean()), float(net[half:].mean())
    dec = {}
    yr = t["sell"].str[:4].astype(int)
    for label, a, b in (("〜1999年", 0, 1999), ("2000年代", 2000, 2009), ("2010年代", 2010, 2019), ("2020年〜", 2020, 9999)):
        msk = yr.between(a, b)
        if msk.any():
            dec[label] = {"n": int(msk.sum()), "mean": float(net[msk].mean())}
    return {"n": len(t), "first_trade": t["buy"].iloc[0], "last_trade": t["sell"].iloc[-1],
            "mean": mean, "lo": lo, "hi": hi, "first": first, "second": second, "p": p,
            "win_rate": float((net > 0).mean()), "mean_gross": float(t["gross"].mean()),
            "mean_no_fin": float((t["gross"] - cfg["cost"]).mean()),
            "mean_window_log": float(t["win_log"].mean()), "mean_normal_log": float((t["L"] * t["rest_mean"]).mean()),
            "mean_diff_log": float(diff.mean()), "mean_days": float(t["days"].mean()), "by_decade": dec,
            "verdict": judge(mean, lo, first, second, p)}


# ════════════════════ 日中のモメンタム（Q4） ════════════════════

def intraday_rows(bars):
    """1時間足（ニューヨーク時間）→ 日ごとの (x＝前の日の終値→10:30, y＝15:30→16:00)"""
    b = bars.copy()
    b.index = pd.DatetimeIndex(b.index).tz_convert("America/New_York")
    out, prev_close = [], None
    for day, g in b.groupby(b.index.date):
        hm = {(t.hour, t.minute): i for i, t in enumerate(g.index)}
        last_close = float(g["Close"].iloc[-1])
        if prev_close is not None and (9, 30) in hm and (14, 30) in hm and (15, 30) in hm:
            x = float(g["Close"].iloc[hm[(9, 30)]]) / prev_close - 1
            y = float(g["Close"].iloc[hm[(15, 30)]]) / float(g["Close"].iloc[hm[(14, 30)]]) - 1
            out.append({"day": str(day), "x": x, "y": y})
        prev_close = last_close
    return pd.DataFrame(out)


def intraday_eval(rows, cost, rng):
    r = rows[rows["x"] != 0].reset_index(drop=True)
    sgn = np.sign(r["x"].to_numpy())
    y = r["y"].to_numpy()
    gross = sgn * y
    net = gross - cost
    bm = boot_mean(net, rng)
    coins = rng.choice([-1.0, 1.0], size=(N_BOOT, len(y)))
    plac = (coins * y).mean(axis=1)
    p = (int((plac >= gross.mean() - 1e-15).sum()) + 1) / (N_BOOT + 1)
    half = len(r) // 2
    mean, lo, hi = float(net.mean()), float(np.percentile(bm, 2.5)), float(np.percentile(bm, 97.5))
    first, second = float(net[:half].mean()), float(net[half:].mean())
    x = r["x"].to_numpy()
    corr = float(np.corrcoef(x, y)[0, 1]) if len(r) > 2 else None
    return {"n": len(r), "first_day": r["day"].iloc[0], "last_day": r["day"].iloc[-1], "mean": mean, "lo": lo, "hi": hi,
            "first": first, "second": second, "p": p, "hit_rate": float((gross > 0).mean()),
            "mean_gross": float(gross.mean()), "mean_abs_y": float(np.abs(y).mean()), "corr_xy": corr,
            "r2": corr ** 2 if corr is not None else None, "verdict": judge(mean, lo, first, second, p)}


# ════════════════════ 書き出し ════════════════════

def _p(x, nd=3, sign=True):
    return "—" if x is None else (f"{x * 100:+.{nd}f}%" if sign else f"{x * 100:.{nd}f}%")


def render_md(out):
    L = ["# R3 株価指数の時間の癖（月末月初・日中のモメンタム）", "",
         f"- 生成: {out['generated_jst']}　事前登録の指紋（PILLAR_PREREG.md の sha256）: `{out['prereg_sha256']}`",
         "- 物差しと判定＝PILLAR_PREREG.md「R3 株価指数の時間の癖」（計算より先にコミット）。**論文が出たあとの期間だけ・1回だけ数えた結果**",
         f"- 費用＝往復の売り買いの差（米国 0.02%・日本 0.03%）＋持ち越しの金利 年{FIN_RATE * 100:.0f}%（暦日で割り当て）",
         f"- 関門＝比べる相手との差の片側 p＜0.05÷{N_COMPARE}（{ALPHA:.4f}）", ""]
    if out["failed"]:
        L += ["## ⚠️ データの取得の失敗", ""] + [f"- {x}" for x in out["failed"]] + \
             ["", "何も数えていない。直し方を登録してから、やり直す。", ""]
        return "\n".join(L) + "\n"
    L += ["## 判定の一覧", "", "| 問い | 判定 | 回数 | 費用後の平均（1回） | 95%の幅 | 前半 | 後半 | p |", "|---|---|---|---|---|---|---|---|"]
    for q in ("Q1", "Q2", "Q3", "Q4"):
        r = out["results"][q]
        name = TOM[q]["name"] if q in TOM else Q4["name"]
        L.append(f"| {q} {name} | {r['verdict']} | {r['n']} | {_p(r['mean'])} | {_p(r['lo'])}〜{_p(r['hi'])} | "
                 f"{_p(r['first'])} | {_p(r['second'])} | {r['p']:.4f} |")
    L.append("")
    for q in ("Q1", "Q2", "Q3"):
        r = out["results"][q]
        L += [f"## {q} {TOM[q]['name']}", "",
              f"- 期間 {r['first_trade']}〜{r['last_trade']}・{r['n']}回（平均 {r['mean_days']:.1f} 暦日持つ）",
              f"- 窓の損益（費用前・対数の平均）{_p(r['mean_window_log'])} ／ 同じ長さのふつうの日 {_p(r['mean_normal_log'])} ／ "
              f"差 {_p(r['mean_diff_log'])}",
              f"- 費用前の平均 {_p(r['mean_gross'])} ／ 持ち越しの金利なし {_p(r['mean_no_fin'])} ／ 勝った割合 {_p(r['win_rate'], 0, False)}",
              "- 年代ごとの費用後の平均：" + "・".join(f"{k} {_p(v['mean'])}（{v['n']}回）" for k, v in r["by_decade"].items()), ""]
    r = out["results"]["Q4"]
    L += [f"## Q4 {Q4['name']}", "",
          f"- 期間 {r['first_day']}〜{r['last_day']}・{r['n']}日",
          f"- 当たった割合 {_p(r['hit_rate'], 0, False)} ／ 費用前の平均 {_p(r['mean_gross'])} ／ 最後の30分の平均の大きさ {_p(r['mean_abs_y'], 3, False)}"
          f" ／ 朝と引け前の相関 {r['corr_xy']:+.3f}（決定係数 {r['r2'] * 100:.2f}%）", "",
          "## 読み方の約束と限界", "",
          "- ◎ でも過去の1回の数え上げ。次は MT4 のデモで前向きに数える（デモで成果が出たら本口座で10万円から）",
          "- 月末月初は月に1回・4〜7日だけ持つ決まりで、利益は小さい。前向きの確かめには年単位がかかる",
          "- 指数そのものの値（配当・CFD の調整・先物とのずれは入れない）。Q4 は約2年分で判定の力は弱い",
          "- 持ち越しの金利・売り買いの差は業者によって違う。過去の成績は将来を約束しない。情報提供であり投資助言ではない", ""]
    return "\n".join(L) + "\n"


def main():
    rng = np.random.default_rng(SEED)
    out = {"generated_jst": dt.datetime.now(JST).strftime("%Y-%m-%dT%H:%M+09:00"), "prereg_sha256": prereg_sha256(),
           "kind": "backtest", "section": "R3", "end": END, "failed": [], "data": {}, "results": {}}
    closes = {}
    for tk in ("^GSPC", "^N225"):
        df = fetch(tk, "1d", start=FETCH_START)
        if df is None:
            out["failed"].append(f"{tk}: 取れない")
            continue
        c = df["Close"].astype(float)
        c = c[(c > 0) & (c.index <= pd.Timestamp(END))]
        ok, mx, day = data_ok(c[c.index >= pd.Timestamp("1988-06-01")])
        out["data"][tk] = {"from": str(c.index[0].date()), "to": str(c.index[-1].date()), "max_daily": mx, "max_day": day}
        if not ok:
            out["failed"].append(f"{tk}: 1日の変化 {mx * 100:.1f}%（{day}）が {MAX_DAILY * 100:.0f}% を超える")
        closes[tk] = c
    bars = fetch(Q4["ticker"], "1h")
    if bars is None:
        out["failed"].append("SPY 1時間足: 取れない")
    else:
        rows = intraday_rows(bars)
        daily = pd.Series(rows["y"].to_numpy(), index=pd.to_datetime(rows["day"])) if len(rows) else pd.Series(dtype=float)
        if len(rows) < 200:
            out["failed"].append(f"SPY 1時間足: そろった日が {len(rows)} 日しかない")
        elif (rows[["x", "y"]].abs() > MAX_DAILY).any().any():
            out["failed"].append("SPY 1時間足: 25% を超える変化がある")
        out["data"]["SPY"] = {"days": len(rows), "from": str(daily.index[0].date()) if len(daily) else None}
    if not out["failed"]:
        for q, cfg in TOM.items():
            out["results"][q] = tom_eval(closes[cfg["ticker"]], cfg, rng)
        out["results"]["Q4"] = intraday_eval(rows, Q4["cost"], rng)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    md = render_md(out)
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(md)
    print(md)
    return 0 if not out["failed"] else 1


if __name__ == "__main__":
    sys.exit(main())
