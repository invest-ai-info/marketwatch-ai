# -*- coding: utf-8 -*-
"""R7 株価指数の朝の窓は、その日のうちに埋まる向きに動くか／夜の上げは費用のあとも残るか（JP225・US500 の CFD を
MT4 で全自動にできる形）。2026-10-06 登録・オーナー「その調子でどんどん研究を進めてください」。

⚠️ 物差しと判定は PILLAR_PREREG.md「R7」（事前登録・計算より先にコミット）と下の定数に固定。結果を見てから動かさない。
   出力には事前登録の中身の指紋（sha256）を書き込む。
⚠️ 値段は上場投信（1321.T・SPY）の日足の始値と終値（pillar_lab.fetch＝yfinance の自動調整＝分割と配当を戻した値）。
⚠️ 1日の終値の変化が25%超、または始値が前日終値とちょうど同じ日が30%超ならデータの取得の失敗として何も数えない。
⚠️ 出力 index-open-lab.json / .md は GitHub 側で生成＝手元から送らない（SYNC禁忌）。
⚠️ エンジン・発火条件・固定オラクル（signal_lab_verify.py）には触れない。メールや売買の決まりは変えない。

事前登録に書いていない細かい決め方（計算より先にここで固定）:
  - 数える日の前の日（UTC）までの値だけを使う（その日の途中の値を使わない）。取引の日（窓＝その日・夜＝買う日）が 2009-01-01〜2026-09-30
  - 窓の大きさがちょうど 0.5% は入れる（以上）。窓が0の日は向きが決まらないので入らない
  - 月ごとのまとまり＝取引の日の月。95%の幅は月を引き直す 10,000回の 2.5%〜97.5%
  - 片側 p＝(偽薬・引き直しが観測以上（夜は差が0以下）だった回数＋1)÷(回数＋1)
  - 向きだけコインの偽薬は、同じ取引に無作為な向き（±1）を付けた費用前の平均を 10,000回

実行: python index_open_lab.py           （Actions の index-open-lab.yml から手動で・1回だけ）
      python index_open_lab.py --check   （データの点検だけ・損益は数えない）
"""
import datetime as dt
import json
import sys

import numpy as np
import pandas as pd

from pillar_lab import fetch, prereg_sha256

JST = dt.timezone(dt.timedelta(hours=9))
FETCH_START = "2007-01-01"
START, END = "2009-01-01", "2026-09-30"
GAP = 0.005                     # Q1・Q2 窓の大きさ 0.5% 以上
FIN_RATE = 0.03                 # 持ち越しの金利 年3%（R3 と同じ）
N_BOOT = 10000
N_Q = 4
ALPHA = 0.05 / N_Q
MAX_DAILY = 0.25
MAX_SAME_OPEN = 0.30
SEED = 20261012
VERDICTS = ("◎ 残っている", "◯ 傾向", "差なし")
QS = {
    "Q1": {"name": "日本の朝の窓を埋める向き（1321.T・窓0.5%以上の日に寄りで逆向き→大引け）", "ticker": "1321.T", "kind": "gap", "cost": 0.0003},
    "Q2": {"name": "米国の朝の窓を埋める向き（SPY・窓0.5%以上の日に寄りで逆向き→大引け）", "ticker": "SPY", "kind": "gap", "cost": 0.0002},
    "Q3": {"name": "日本の夜の上げ（1321.T・終値で買い次の取引日の始値で売る）", "ticker": "1321.T", "kind": "night", "cost": 0.0003},
    "Q4": {"name": "米国の夜の上げ（SPY・終値で買い次の取引日の始値で売る）", "ticker": "SPY", "kind": "night", "cost": 0.0002},
}
TICKERS = ("1321.T", "SPY")
OUT_JSON, OUT_MD = "index-open-lab.json", "index-open-lab.md"


# ════════════════════ データ ════════════════════

def data_ok(df):
    """→ (よいか, 説明)。終値の変化が25%超・始値＝前日終値の日が30%超はデータの失敗"""
    c, o = df["Close"].astype(float), df["Open"].astype(float)
    ch = c.pct_change().abs().dropna()
    if ch.empty:
        return False, "行が足りない"
    if ch.max() > MAX_DAILY:
        return False, f"1日の終値の変化 {ch.max() * 100:.1f}%（{pd.Timestamp(ch.idxmax()).date()}）"
    same = float((o.iloc[1:].to_numpy() == c.shift(1).iloc[1:].to_numpy()).mean())
    if same > MAX_SAME_OPEN:
        return False, f"始値が前日終値とちょうど同じ日が {same * 100:.0f}%（始値が埋まっていない）"
    return True, f"始値＝前日終値の日 {same * 100:.1f}%"


# ════════════════════ 取引 ════════════════════

def gap_trades(df, cost, start=START, end=END, cut="2100-12-31"):
    """窓が GAP 以上の日に寄りで逆向き→大引け。→ [{day, month, gap, dir, gross, net}]"""
    d = df[df.index < pd.Timestamp(cut)]
    o, c = d["Open"].astype(float).to_numpy(), d["Close"].astype(float).to_numpy()
    days = pd.DatetimeIndex(d.index)
    out = []
    for i in range(1, len(d)):
        day = days[i]
        if not (pd.Timestamp(start) <= day <= pd.Timestamp(end)):
            continue
        g = o[i] / c[i - 1] - 1
        if abs(g) < GAP or g == 0:
            continue
        sgn = -1.0 if g > 0 else 1.0
        gross = sgn * (c[i] / o[i] - 1)
        out.append({"day": str(day.date()), "month": str(day.date())[:7], "gap": float(g), "dir": sgn,
                    "gross": float(gross), "net": float(gross - cost)})
    return out


def night_trades(df, cost, start=START, end=END, cut="2100-12-31"):
    """毎取引日、終値で買い次の取引日の始値で売る。→ [{day, month, days, gross, net, intra, hold, fri}]"""
    d = df[df.index < pd.Timestamp(cut)]
    o, c = d["Open"].astype(float).to_numpy(), d["Close"].astype(float).to_numpy()
    days = pd.DatetimeIndex(d.index)
    out = []
    for i in range(len(d) - 1):
        day = days[i]
        if not (pd.Timestamp(start) <= day <= pd.Timestamp(end)):
            continue
        cal = int((days[i + 1] - day).days)
        gross = o[i + 1] / c[i] - 1
        out.append({"day": str(day.date()), "month": str(day.date())[:7], "days": cal, "gross": float(gross),
                    "net": float(gross - cost - FIN_RATE * cal / 365.0), "intra": float(c[i + 1] / o[i + 1] - 1),
                    "hold": float(c[i + 1] / c[i] - 1), "fri": day.weekday() == 4})
    return out


# ════════════════════ 数える ════════════════════

def _by_month(rows, key):
    months = sorted({r["month"] for r in rows})
    ix = {m: k for k, m in enumerate(months)}
    s, n = np.zeros(len(months)), np.zeros(len(months))
    for r in rows:
        s[ix[r["month"]]] += r[key]
        n[ix[r["month"]]] += 1
    return months, s, n


def stats(rows, kind, rng, n_boot=N_BOOT):
    if not rows:
        return {"n": 0, "verdict": VERDICTS[2]}
    months, s, n = _by_month(rows, "net")
    idx = rng.integers(0, len(months), (n_boot, len(months)))
    boot = s[idx].sum(1) / n[idx].sum(1)
    half = months[len(months) // 2]
    net = np.array([r["net"] for r in rows])
    gross = np.array([r["gross"] for r in rows])
    st = {"n": len(rows), "months": len(months), "mean": float(net.mean()), "lo": float(np.percentile(boot, 2.5)),
          "hi": float(np.percentile(boot, 97.5)), "half_from": half,
          "first": float(np.mean([r["net"] for r in rows if r["month"] < half])),
          "second": float(np.mean([r["net"] for r in rows if r["month"] >= half])),
          "mean_gross": float(gross.mean()), "win_rate": float((net > 0).mean())}
    if kind == "gap":
        signs = rng.choice((-1.0, 1.0), size=(n_boot, len(rows)))
        base = np.array([r["gross"] * r["dir"] for r in rows])          # 向きを付ける前の値動き（寄り→大引け）
        placebo = (signs * base).mean(1)
        st["p"] = (int((placebo >= gross.mean()).sum()) + 1) / (n_boot + 1)
        st["compare"] = "向きだけコイン"
    else:
        months, sd, nd = _by_month([dict(r, d=r["gross"] - r["intra"]) for r in rows], "d")
        idx2 = rng.integers(0, len(months), (n_boot, len(months)))
        bd = sd[idx2].sum(1) / nd[idx2].sum(1)
        st["diff_night_minus_day"] = float(np.mean([r["gross"] - r["intra"] for r in rows]))
        st["p"] = (int((bd <= 0).sum()) + 1) / (n_boot + 1)
        st["compare"] = "取引時間の中（夜−昼）"
    st["verdict"] = judge(st)
    return st


def judge(st):
    if st.get("n", 0) and st["mean"] > 0 and st["lo"] > 0 and st["first"] > 0 and st["second"] > 0:
        return VERDICTS[0] if st["p"] < ALPHA else (VERDICTS[1] if st["p"] < 0.05 else VERDICTS[2])
    return VERDICTS[2]


def _mean(xs):
    xs = list(xs)
    return float(np.mean(xs)) if xs else None


PERIODS = (("2009〜2014年", 2009, 2014), ("2015〜2020年", 2015, 2020), ("2021年〜", 2021, 9999))


def reading(rows, kind):
    out = {"by_period": {lab: {"n": sum(1 for r in rows if a <= int(r["day"][:4]) <= b),
                               "mean": _mean(r["net"] for r in rows if a <= int(r["day"][:4]) <= b)} for lab, a, b in PERIODS}}
    if kind == "gap":
        bands = (("0.5〜1%", 0.005, 0.01), ("1〜2%", 0.01, 0.02), ("2%以上", 0.02, 9.0))
        out["by_size"] = {lab: {"n": sum(1 for r in rows if a <= abs(r["gap"]) < b),
                                "mean": _mean(r["net"] for r in rows if a <= abs(r["gap"]) < b)} for lab, a, b in bands}
        out["by_side"] = {lab: {"n": sum(1 for r in rows if f(r)), "mean": _mean(r["net"] for r in rows if f(r))}
                          for lab, f in (("上に窓（売りで入る）", lambda r: r["gap"] > 0), ("下に窓（買いで入る）", lambda r: r["gap"] < 0))}
    else:
        out["fri"] = {"金曜の夜（週末をまたぐ）": {"n": sum(1 for r in rows if r["fri"]), "mean": _mean(r["net"] for r in rows if r["fri"])},
                      "それ以外": {"n": sum(1 for r in rows if not r["fri"]), "mean": _mean(r["net"] for r in rows if not r["fri"])}}
        out["parts_gross"] = {"夜（終値→始値）": _mean(r["gross"] for r in rows), "昼（始値→終値）": _mean(r["intra"] for r in rows),
                              "ただ持つ（終値→終値）": _mean(r["hold"] for r in rows)}
    return out


# ════════════════════ 実行 ════════════════════

def load(fetcher=fetch):
    out, failed, notes = {}, [], {}
    for tk in TICKERS:
        df = fetcher(tk, "1d", start=FETCH_START)
        if df is None:
            failed.append(f"{tk}: 取れない")
            continue
        df = df[(df["Open"] > 0) & (df["Close"] > 0)]
        ok, why = data_ok(df[df.index >= pd.Timestamp("2008-06-01")])
        notes[tk] = why
        if not ok:
            failed.append(f"{tk}: {why}")
        out[tk] = df
    return out, failed, notes


def run(data, cut, rng):
    res = {}
    for q, cfg in QS.items():
        df = data[cfg["ticker"]]
        rows = (gap_trades if cfg["kind"] == "gap" else night_trades)(df, cfg["cost"], cut=cut)
        res[q] = {"name": cfg["name"], "stats": stats(rows, cfg["kind"], rng), "reading": reading(rows, cfg["kind"]),
                  "first_day": rows[0]["day"] if rows else None, "last_day": rows[-1]["day"] if rows else None}
    return res


def _p(x, nd=3):
    return "—" if x is None else f"{x * 100:+.{nd}f}%"


def render_md(out):
    L = ["# R7 株価指数の朝の窓・夜の上げ（JP225・US500 の CFD の代わりに 1321.T・SPY の日足）", "",
         f"- 生成: {out['generated_jst']}　事前登録の指紋（PILLAR_PREREG.md の sha256）: `{out.get('prereg_sha256')}`",
         f"- 決まり＝PILLAR_PREREG.md「R7」。期間 {START}〜{END}・数える日の前の日（UTC）までの値だけ。p＜0.05÷{N_Q}",
         "- 費用＝往復の売り買いの差（日本 0.03%・米国 0.02%）。夜の上げは持ち越しの金利 年3%（暦日）も引く", ""]
    if out.get("failed"):
        return "\n".join(L + ["⚠️ データの取得の失敗＝何も数えていない：" + " / ".join(out["failed"]), ""]) + "\n"
    for q, r in (out.get("result") or {}).items():
        s, rd = r["stats"], r["reading"]
        L += [f"## {q} {r['name']}", "",
              f"- 判定：**{s['verdict']}**",
              f"- 回数 {s['n']}（{r['first_day']}〜{r['last_day']}・{s.get('months', 0)}か月）・費用後の平均 {_p(s.get('mean'))}"
              f"（95%の幅 {_p(s.get('lo'))}〜{_p(s.get('hi'))}）・費用前 {_p(s.get('mean_gross'))}・勝ち（費用後プラス）の割合 {s.get('win_rate', 0) * 100:.1f}%",
              f"- 前半 {_p(s.get('first'))}／後半 {_p(s.get('second'))}（後半は {s.get('half_from')} から）・比べる相手＝{s.get('compare')}・片側 p {s.get('p', 1):.4f}"]
        if "diff_night_minus_day" in s:
            L.append(f"- 夜−昼（費用前）の平均 {_p(s['diff_night_minus_day'])}")
        L += ["", "読むための表（判定しない）：", ""]
        L.append("- 時期ごと（費用後）：" + "／".join(f"{k} {_p(v['mean'])}（{v['n']}）" for k, v in rd["by_period"].items()))
        for key, title in (("by_size", "窓の大きさごと"), ("by_side", "窓の向きごと"), ("fri", "曜日")):
            if key in rd:
                L.append(f"- {title}（費用後）：" + "／".join(f"{k} {_p(v['mean'])}（{v['n']}）" for k, v in rd[key].items()))
        if "parts_gross" in rd:
            L.append("- 1日の分け方（費用前の平均）：" + "／".join(f"{k} {_p(v)}" for k, v in rd["parts_gross"].items()))
        L.append("")
    L += ["---", "", "※ 研究の記録です。投資助言ではありません。過去の成績は将来を約束しません。上場投信の始値・終値は CFD の値段と少しずれます。"]
    return "\n".join(L) + "\n"


def check():
    data, failed, notes = load()
    for tk, df in data.items():
        print(f"{tk}：{len(df)}行・{df.index.min().date()}〜{df.index.max().date()}・{notes.get(tk)}", flush=True)
    print("点検だけ（損益は数えていない）。" + ("⚠️ " + " / ".join(failed) if failed else "2つとも取れて、データの失敗なし"))
    return 1 if failed else 0


def main():
    if "--check" in sys.argv[1:]:
        return check()
    rng = np.random.default_rng(SEED)
    now = dt.datetime.now(dt.timezone.utc)
    cut = str(now.date())
    today = str(now.astimezone(JST).date())
    out = {"generated_jst": now.astimezone(JST).strftime("%Y-%m-%dT%H:%M+09:00"), "prereg_sha256": prereg_sha256(),
           "kind": "backtest", "section": "R7", "cut": cut, "failed": [], "titles": {q: c["name"] for q, c in QS.items()},
           "verdicts": {}}
    data, failed, notes = load()
    out["failed"], out["data_notes"] = failed, notes
    if not failed:
        res = run(data, cut, rng)
        out["result"] = res
        for q, r in res.items():
            s = r["stats"]
            if s["verdict"] == VERDICTS[2]:
                out["verdicts"][q] = {"status": "stop", "decided_on": today, "n": s["n"], "mean": s.get("mean"), "lo": s.get("lo"),
                                      "hi": s.get("hi"), "reason": f"過去のデータで1回だけ数えて差なし（{s.get('compare')}との p {s.get('p', 1):.3f}）"}
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    md = render_md(out)
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(md)
    print(md)
    return 0 if not out["failed"] else 1


if __name__ == "__main__":
    sys.exit(main())
