# -*- coding: utf-8 -*-
"""R6 月末月初の窓は、ほかの国の株価指数でも論文のあとに残っているか（R3F を育てる確かめ）。
2026-10-05 深夜 登録・オーナー「おすすめ通りにお願いします」→「続けてください」（R3F・J4G を育てる方針）。
出どころ＝McConnell & Xu (2008, Financial Analysts Journal)：2005年まで35か国のうち31か国で月末月初の上げ。

⚠️ 物差しと判定は PILLAR_PREREG.md「R6」（事前登録・計算より先にコミット）と下の定数に固定。結果を見てから動かさない。
   出力には事前登録の中身の指紋（sha256）を書き込む。
⚠️ 窓の決め方は calendar_lab.tom_trades をそのまま使う（R3 の Q1 と同じ＝月の最後から2日目の終値で買い、翌月の3日目の終値で売る）。
⚠️ R1 の直し方①（単位のずれ・hold_lab.clean）を当て、直したあとも1日25%を超える変化が残る指数があれば何も数えない。
⚠️ 出力 intl-tom-lab.json / .md は GitHub 側で生成＝手元から送らない（SYNC禁忌）。
⚠️ エンジン・発火条件・固定オラクル（signal_lab_verify.py）には触れない。メールや売買の決まりは変えない。

事前登録に書いていない細かい決め方（計算より先にここで固定）:
  - 数える日の前の日（UTC）までの終値だけを使う（その日の途中の値を使わない）。窓の月（買う日の月）が 2009-01〜2026-09 の取引だけ
  - ふつうの日の平均が出せない窓（前の窓との間に日が無い）は数えない（R3 と同じ）
  - 月ごとのまとまり＝窓の月。95%の幅は月を引き直す 10,000回の 2.5%〜97.5%。片側 p＝(差の引き直しが0以下だった回数＋1)÷(回数＋1)
  - 前半・後半＝窓の月を古い順に並べてちょうど半分で分ける

実行: python intl_tom_lab.py   （Actions の intl-tom-lab.yml から手動で）
"""
import datetime as dt
import json
import sys

import numpy as np
import pandas as pd

import calendar_lab as CL
from hold_lab import clean
from pillar_lab import fetch, prereg_sha256

JST = dt.timezone(dt.timedelta(hours=9))
MARKETS = {"^GDAXI": "ドイツ", "^FTSE": "英国", "^FCHI": "フランス", "^STOXX50E": "ユーロ圏50",
           "^IBEX": "スペイン", "^AXJO": "豪州", "^HSI": "香港"}
FETCH_START = "2007-01-01"
START, LAST_MONTH = "2009-01-01", "2026-09"
PRE, POST = 1, 3
COST = 0.0005
N_BOOT = 10000
ALPHA = 0.05
SEED = 20261011
VERDICTS = ("◎ 残っている", "◯ 傾向", "差なし")
TITLE = "ほかの国の株価指数（ドイツ・英国・フランス・ユーロ圏50・スペイン・豪州・香港）の月末月初（月の最後の日＋翌月の最初の3日）"
OUT_JSON, OUT_MD = "intl-tom-lab.json", "intl-tom-lab.md"


def market_rows(close, market, cut):
    """ひとつの指数の取引（窓の月・費用後の損益・ふつうの日との差）"""
    c = close[close.index < pd.Timestamp(cut)].dropna()
    t = CL.tom_trades(c, PRE, POST, START, end="2100-12-31")
    if t.empty:
        return []
    t = t.dropna(subset=["rest_mean"])
    t = t[t["buy"].str[:7] <= LAST_MONTH]
    fin = CL.FIN_RATE * t["days"] / 365.0
    return [{"market": market, "month": r["buy"][:7], "buy": r["buy"], "sell": r["sell"], "gross": float(r["gross"]),
             "net": float(r["gross"] - COST - f), "no_fin": float(r["gross"] - COST),
             "diff": float(r["win_log"] - r["L"] * r["rest_mean"]), "days": int(r["days"])}
            for (_, r), f in zip(t.iterrows(), fin)]


def pooled(rows, rng, n_boot=N_BOOT):
    """7つをまとめて数える（95%の幅と差の p は月ごとのまとまりで引き直す）"""
    df = pd.DataFrame(rows)
    months = sorted(df["month"].unique())
    g = df.groupby("month").agg(net=("net", "sum"), diff=("diff", "sum"), n=("net", "count")).reindex(months)
    idx = rng.integers(0, len(months), (n_boot, len(months)))
    cnt = g["n"].to_numpy()[idx].sum(axis=1)
    boot_net = g["net"].to_numpy()[idx].sum(axis=1) / cnt
    boot_diff = g["diff"].to_numpy()[idx].sum(axis=1) / cnt
    half = months[len(months) // 2]
    st = {"n": int(len(df)), "months": len(months), "mean": float(df["net"].mean()),
          "lo": float(np.percentile(boot_net, 2.5)), "hi": float(np.percentile(boot_net, 97.5)),
          "first": float(df[df["month"] < half]["net"].mean()), "second": float(df[df["month"] >= half]["net"].mean()),
          "half_from": half, "diff": float(df["diff"].mean()), "p": (int((boot_diff <= 0).sum()) + 1) / (n_boot + 1),
          "mean_gross": float(df["gross"].mean()), "mean_no_fin": float(df["no_fin"].mean()),
          "win_rate": float((df["net"] > 0).mean())}
    st["verdict"] = judge(st)
    return st


def judge(st):
    if st["mean"] > 0 and st["first"] > 0 and st["second"] > 0 and st["p"] < ALPHA:
        return VERDICTS[0] if st["lo"] > 0 else VERDICTS[1]
    return VERDICTS[2]


def by_market(rows):
    out = {}
    for m in MARKETS:
        x = [r for r in rows if r["market"] == m]
        if x:
            out[m] = {"n": len(x), "mean": float(np.mean([r["net"] for r in x])),
                      "mean_gross": float(np.mean([r["gross"] for r in x])), "diff": float(np.mean([r["diff"] for r in x]))}
    return out


def by_period(rows):
    out = {}
    for label, a, b in (("2009〜2014年", 2009, 2014), ("2015〜2020年", 2015, 2020), ("2021年〜", 2021, 9999)):
        x = [r["net"] for r in rows if a <= int(r["month"][:4]) <= b]
        if x:
            out[label] = {"n": len(x), "mean": float(np.mean(x))}
    return out


def load(fetcher=fetch):
    """→ ({表記: 直した終値}, 失敗の説明, 直した記録)"""
    out, failed, fixes = {}, [], {}
    for tk in MARKETS:
        df = fetcher(tk, "1d", start=FETCH_START)
        if df is None:
            failed.append(f"{tk}: 取れない")
            continue
        s = df["Close"].astype(float)
        s, fx = clean(s[s > 0], fx=False)
        if fx:
            fixes[tk] = fx
        ok, mx, day = CL.data_ok(s[s.index >= pd.Timestamp("2008-06-01")])
        if not ok:
            failed.append(f"{tk}: 直したあとも1日の変化 {mx * 100:.1f}%（{day}）が {CL.MAX_DAILY * 100:.0f}% を超える")
        out[tk] = s
    return out, failed, fixes


def _p(x, nd=3):
    return "—" if x is None else f"{x * 100:+.{nd}f}%"


def render_md(out):
    L = ["# R6 ほかの国の株価指数の月末月初（R3F を育てる確かめ）", "",
         f"- 生成: {out['generated_jst']}　事前登録の指紋（PILLAR_PREREG.md の sha256）: `{out['prereg_sha256']}`",
         f"- 物差しと判定＝PILLAR_PREREG.md「R6」（計算より先にコミット）。窓の月 2009-01〜{LAST_MONTH}・{out['cut']} の前の日までの終値・1回だけ数えた結果",
         f"- 決まり：{TITLE}。月の最後から2日目の終値で買い、翌月の3日目の終値で売る（R3 の米国と同じ窓）",
         f"- 費用：往復 {COST * 100:.2f}%＋持ち越しの金利 年{CL.FIN_RATE * 100:.0f}%（持った暦日）", ""]
    if out["failed"]:
        return "\n".join(L + ["## ⚠️ データの取得の失敗", ""] + [f"- {x}" for x in out["failed"]] +
                         ["", "何も数えていない（判定なし）。直し方を登録してから、やり直す。", ""]) + "\n"
    r = out["result"]
    L += ["## 判定", "", "| 判定 | 回数 | 費用後の平均 | 95%の幅 | 前半 | 後半 | ふつうの日との差（対数） | 差の片側 p |",
          "|---|---|---|---|---|---|---|---|",
          f"| {r['verdict']} | {r['n']}（{r['months']}か月×最大7つ） | {_p(r['mean'])} | {_p(r['lo'])}〜{_p(r['hi'])} | "
          f"{_p(r['first'])} | {_p(r['second'])} | {_p(r['diff'])} | {r['p']:.4f} |", "",
          "## 読むための数字（判定には使わない）", "",
          f"- 費用前の平均 {_p(r['mean_gross'])}・持ち越しの金利なし {_p(r['mean_no_fin'])}・プラスだった割合 {r['win_rate'] * 100:.0f}%",
          "- 時期ごとの費用後の平均：" + "・".join(f"{k} {_p(v['mean'])}（{v['n']}回）" for k, v in out["reading"]["by_period"].items()),
          "", "| 指数 | 回数 | 費用後の平均 | 費用前 | ふつうの日との差 |", "|---|---|---|---|---|"]
    for tk, v in out["reading"]["by_market"].items():
        L.append(f"| {MARKETS[tk]} | {v['n']} | {_p(v['mean'])} | {_p(v['mean_gross'])} | {_p(v['diff'])} |")
    L += ["", "## 読み方の約束と限界", "",
          "- ◎ なら R3F に7つを足す前向きの観察を別に登録してから始める。◯ なら R3F はそのまま（7つは足さない）。差なしなら検証済みリストへ",
          "- 指数そのものの値（配当なし）。CFD の配当の調整や費用は業者で違う。欧州の4つは強く一緒に動く（月ごとのまとまりで引き直した）",
          "- 過去の成績は将来を約束しない。研究の記録であり投資助言ではない", ""]
    return "\n".join(L) + "\n"


def run(series, cut, rng):
    rows = []
    for tk in MARKETS:
        if tk in series:
            rows += market_rows(series[tk], tk, cut)
    return rows, pooled(rows, rng)


def main():
    rng = np.random.default_rng(SEED)
    now = dt.datetime.now(dt.timezone.utc)
    cut = str(now.date())                                    # この日より前の終値だけ（途中の値を使わない）
    today = str(now.astimezone(JST).date())
    out = {"generated_jst": now.astimezone(JST).strftime("%Y-%m-%dT%H:%M+09:00"), "prereg_sha256": prereg_sha256(),
           "kind": "backtest", "section": "R6", "cut": cut, "failed": [], "data_fixes": {}, "titles": {"R6": TITLE},
           "verdicts": {}}
    series, failed, fixes = load()
    out["failed"], out["data_fixes"] = failed, fixes
    if not failed:
        rows, st = run(series, cut, rng)
        out["result"] = st
        out["reading"] = {"by_market": by_market(rows), "by_period": by_period(rows),
                          "last_month_by_market": {m: max((r["month"] for r in rows if r["market"] == m), default=None)
                                                   for m in MARKETS}}
        if st["verdict"] == VERDICTS[2]:
            out["verdicts"]["R6"] = {"status": "stop", "decided_on": today, "n": st["n"], "mean": st["mean"], "lo": st["lo"],
                                     "hi": st["hi"], "reason": f"過去のデータで1回だけ数えて差なし（ふつうの日との差 p {st['p']:.3f}）"}
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    md = render_md(out)
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(md)
    print(md)
    return 0 if not out["failed"] else 1


if __name__ == "__main__":
    sys.exit(main())
