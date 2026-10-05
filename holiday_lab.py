# -*- coding: utf-8 -*-
"""R5 日本の祝日の前の日：日経平均は、東証が休む日の前の取引日に上がりやすいか（論文のあとの期間・MT4 の株価指数 CFD の費用）。
2026-10-05 登録・オーナー「続けてください」。出どころ＝Ziemba (1991)・Ariel (1990)。米国は Ko & Yang の追試で
大型株では消えているので、読むための数字だけ。

⚠️ 物差しと判定の基準は PILLAR_PREREG.md「R5 日本の祝日の前の日」（事前登録・計算より先にコミット）と下の定数に固定。
   結果を見てから動かさない。出力には事前登録の中身の指紋（sha256）を書き込む。
⚠️ 休場日＝pandas_market_calendars の東証（XTKS）・ニューヨーク証券取引所（NYSE）の取引日に入らない平日。
⚠️ 1日の変化が25%を超える日があればデータの取得の失敗として何も数えない（calendar_lab.data_ok）。
⚠️ 出力 holiday-lab.json / .md は GitHub 側で生成＝手元から送らない（SYNC禁忌）。
⚠️ エンジン・発火条件・固定オラクル（signal_lab_verify.py）には触れない。メールや売買の決まりは変えない。

事前登録に書いていない細かい決め方（計算より先にここで固定）:
  - 「休場の平日が2日以上続く」＝祝日の前の日の次の平日から数えて、休場の平日が2日以上続く
  - 前の取引日・祝日の前の日は、取引所の暦の取引日で決め、両方の終値が Yahoo にある日だけ数える
  - それ以外の日＝期間の中の取引所の取引日のうち、祝日の前の日でない日（前の取引日の終値がある日だけ）
  - 95%の幅＝祝日の前の日（費用後）を引き直す 10,000回の 2.5%〜97.5%。並べ替えの片側 p は (当てはまった回数＋1)÷(回数＋1)
  - 前半・後半＝祝日の前の日を古い順に並べてちょうど半分で分ける

実行: python holiday_lab.py   （Actions の holiday-lab.yml から手動で）
"""
import datetime as dt
import json
import sys

import numpy as np
import pandas as pd

from calendar_lab import FIN_RATE, MAX_DAILY, data_ok
from pillar_lab import fetch, prereg_sha256

JST = dt.timezone(dt.timedelta(hours=9))
START, END = "1992-01-01", "2026-09-30"
US_START = "1991-01-01"
COST_JP, COST_US = 0.0003, 0.0002
LONG_BREAK = 2                     # 休場の平日がこの日数以上続く連休
N_BOOT = 10000
N_COMPARE = 2
ALPHA = 0.05 / N_COMPARE
SEED = 20261009
VERDICTS = ("◎ 残っている", "◯ 傾向", "差なし")
TITLES = {"Q1": "日本の祝日の前の日すべて（日経平均）", "Q2": "日本の連休（休場の平日が2日以上）の前の日（日経平均）"}
OUT_JSON, OUT_MD = "holiday-lab.json", "holiday-lab.md"


def exchange_days(name, start, end):
    """取引所の取引日（日付の昇順の DatetimeIndex）"""
    import pandas_market_calendars as mcal
    s = mcal.get_calendar(name).schedule(start_date=start, end_date=end)
    return pd.DatetimeIndex(pd.to_datetime(s.index.date))


def holiday_rows(close, trade_days, start, end, cost):
    """取引日ごとの記録 → DataFrame（日付・費用前の損益・費用後・祝日の前の日か・続く休場の平日の数・持った暦日）"""
    close = close.copy()
    close.index = pd.DatetimeIndex(pd.to_datetime(close.index.date))
    tset = set(trade_days)
    rows = []
    for i in range(1, len(trade_days) - 1):
        t, prev = trade_days[i], trade_days[i - 1]
        if t < pd.Timestamp(start) or t > pd.Timestamp(end):
            continue
        if t not in close.index or prev not in close.index:
            continue
        # 次の平日から数えて、休場の平日がいくつ続くか
        closed, d = 0, t + pd.Timedelta(days=1)
        while True:
            if d.weekday() < 5:
                if d in tset:
                    break
                closed += 1
            d += pd.Timedelta(days=1)
            if (d - t).days > 20:
                break
        gross = float(close[t] / close[prev] - 1)
        days = int((t - prev).days)
        rows.append({"date": str(t.date()), "gross": gross, "net": gross - cost - FIN_RATE * days / 365.0,
                     "pre": closed >= 1, "closed": closed, "days": days})
    return pd.DataFrame(rows)


def evaluate(df, sel, rng, n=N_BOOT):
    """sel＝祝日の前の日のうち数える印。それ以外の日＝祝日の前の日でない日"""
    ev = df[sel].reset_index(drop=True)
    other = df[~df["pre"]]
    net = ev["net"].to_numpy()
    boot = net[rng.integers(0, len(net), (n, len(net)))].mean(axis=1)
    half = len(ev) // 2
    obs = ev["gross"].mean() - other["gross"].mean()
    pool = np.r_[ev["gross"].to_numpy(), other["gross"].to_numpy()]
    k = len(ev)
    hit = 0
    for _ in range(n):
        perm = rng.permutation(pool)
        hit += (perm[:k].mean() - perm[k:].mean()) >= obs - 1e-15
    p = (hit + 1) / (n + 1)
    st = {"n": int(k), "mean": float(net.mean()), "lo": float(np.percentile(boot, 2.5)), "hi": float(np.percentile(boot, 97.5)),
          "first": float(net[:half].mean()), "second": float(net[half:].mean()), "p": float(p),
          "mean_gross": float(ev["gross"].mean()), "other_mean_gross": float(other["gross"].mean()), "diff": float(obs),
          "win_rate": float((ev["gross"] > 0).mean()), "other_win_rate": float((other["gross"] > 0).mean())}
    st["verdict"] = judge(st)
    return st


def judge(st):
    if st["mean"] > 0 and st["lo"] > 0 and st["first"] > 0 and st["second"] > 0:
        return VERDICTS[0] if st["p"] < ALPHA else (VERDICTS[1] if st["p"] < 0.05 else VERDICTS[2])
    return VERDICTS[2]


def by_decade(ev):
    out = {}
    yr = ev["date"].str[:4].astype(int)
    for label, a, b in (("〜1999年", 0, 1999), ("2000年代", 2000, 2009), ("2010年代", 2010, 2019), ("2020年〜", 2020, 9999)):
        m = yr.between(a, b)
        if m.any():
            out[label] = {"n": int(m.sum()), "mean": float(ev.loc[m, "net"].mean())}
    return out


def _p(x, nd=3):
    return "—" if x is None else f"{x * 100:+.{nd}f}%"


def render_md(out):
    L = ["# R5 日本の祝日の前の日（日経平均）", "",
         f"- 生成: {out['generated_jst']}　事前登録の指紋（PILLAR_PREREG.md の sha256）: `{out['prereg_sha256']}`",
         "- 物差しと判定＝PILLAR_PREREG.md「R5」（計算より先にコミット）。**論文のあと（1992〜2026-09）・1回だけ数えた結果**",
         "- 決まり：前の取引日の終値で買い、祝日の前の日の終値で売る（1日だけ）。費用＝往復 0.03%＋持ち越しの金利 年3%",
         f"- 関門＝それ以外の日との差を並べ替えで比べた片側 p＜0.05÷{N_COMPARE}（{ALPHA:.4f}）", ""]
    if out["failed"]:
        return "\n".join(L + ["## ⚠️ データの取得の失敗", ""] + [f"- {x}" for x in out["failed"]] +
                         ["", "何も数えていない。直し方を登録してから、やり直す。", ""]) + "\n"
    L += ["## 判定", "", "| 問い | 判定 | 回数 | 費用後の平均 | 95%の幅 | 前半 | 後半 | 費用前の平均 | それ以外の日 | 差の p |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for q in ("Q1", "Q2"):
        r = out["results"][q]
        L.append(f"| {q} {TITLES[q]} | {r['verdict']} | {r['n']} | {_p(r['mean'])} | {_p(r['lo'])}〜{_p(r['hi'])} | "
                 f"{_p(r['first'])} | {_p(r['second'])} | {_p(r['mean_gross'])} | {_p(r['other_mean_gross'])} | {r['p']:.4f} |")
    rd = out["reading"]
    L += ["", "## 読むための数字（判定には使わない）", "",
          "- 日本・祝日の前の日の年代ごとの費用後の平均：" + "・".join(f"{k} {_p(v['mean'])}（{v['n']}回）" for k, v in rd["jp_decade"].items()),
          f"- 日本・上がった割合：祝日の前の日 {out['results']['Q1']['win_rate'] * 100:.0f}%／それ以外の日 {out['results']['Q1']['other_win_rate'] * 100:.0f}%",
          f"- 日本・祝日の明けの日（費用前の平均）：{_p(rd['jp_post_holiday_gross'])}（{rd['jp_post_n']}回）",
          f"- 米国（S&P500・1991〜・Ko & Yang の追試で大型株では消えたとされる）：祝日の前の日 {_p(rd['us']['mean_gross'])}"
          f"（{rd['us']['n']}回・費用後 {_p(rd['us']['mean'])}）／それ以外の日 {_p(rd['us']['other_mean_gross'])}", "",
          "## 読み方の約束と限界", "",
          "- ◎・◯ なら R3F と同じ形で前向きの観察に登録する（年に十数回＝確かめには年単位）",
          "- 指数そのものの値（配当・CFD の調整は入れない）。持ち越しの金利・売り買いの差は業者によって違う",
          "- 過去の成績は将来を約束しない。情報提供であり投資助言ではない", ""]
    return "\n".join(L) + "\n"


def main():
    rng = np.random.default_rng(SEED)
    out = {"generated_jst": dt.datetime.now(JST).strftime("%Y-%m-%dT%H:%M+09:00"), "prereg_sha256": prereg_sha256(),
           "kind": "backtest", "section": "R5", "failed": [], "titles": dict(TITLES), "results": {}}
    closes = {}
    for tk in ("^N225", "^GSPC"):
        df = fetch(tk, "1d", start="1985-01-01")
        if df is None:
            out["failed"].append(f"{tk}: 取れない")
            continue
        c = df["Close"].astype(float)
        c = c[(c > 0) & (c.index <= pd.Timestamp(END))]
        ok, mx, day = data_ok(c[c.index >= pd.Timestamp("1990-06-01")])
        if not ok:
            out["failed"].append(f"{tk}: 1日の変化 {mx * 100:.1f}%（{day}）が {MAX_DAILY * 100:.0f}% を超える")
        closes[tk] = c
    if not out["failed"]:
        jp = holiday_rows(closes["^N225"], exchange_days("XTKS", "1990-01-01", "2026-12-31"), START, END, COST_JP)
        out["results"]["Q1"] = evaluate(jp, jp["pre"], rng)
        out["results"]["Q2"] = evaluate(jp, jp["closed"] >= LONG_BREAK, rng)
        prev_closed = jp["pre"].shift(1, fill_value=False)
        post = jp[prev_closed]
        us = holiday_rows(closes["^GSPC"], exchange_days("NYSE", "1990-01-01", "2026-12-31"), US_START, END, COST_US)
        us_ev, us_other = us[us["pre"]], us[~us["pre"]]
        out["reading"] = {"jp_decade": by_decade(jp[jp["pre"]]), "jp_post_holiday_gross": float(post["gross"].mean()),
                          "jp_post_n": int(len(post)),
                          "us": {"n": int(len(us_ev)), "mean_gross": float(us_ev["gross"].mean()), "mean": float(us_ev["net"].mean()),
                                 "other_mean_gross": float(us_other["gross"].mean())}}
        out["counts"] = {"jp_days": int(len(jp)), "jp_pre": int(jp["pre"].sum()), "jp_long": int((jp["closed"] >= LONG_BREAK).sum())}
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    md = render_md(out)
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(md)
    print(md)
    return 0 if not out["failed"] else 1


if __name__ == "__main__":
    sys.exit(main())
