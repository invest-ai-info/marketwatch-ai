# -*- coding: utf-8 -*-
"""L1・L2 ロンドン時間のドルの流れ（論文で確かめられた癖を、個人の費用で数える）。2026-09-30 夕登録・オーナー「進めてください」。

L1＝ロンドンの朝（現地 08:00→12:00）にユーロドル・ポンドドルを売る（自国の時間に自国の通貨が安い＝Ranaldo 2009・Breedon & Ranaldo 2013）
L2＝ロンドン16時の値決めの前（現地 12:00→16:00）にドルを買う（値決めの前はドル高＝Krohn, Mueller & Whelan 2024）
⚠️ 物差しと判定の基準は PILLAR_PREREG.md「L1・L2 ロンドン時間のドルの流れ」（事前登録・計算より先にコミット済み）と下の定数に固定。
   結果を見てから動かさない。費用・偽薬・幅の関数は S1（box_lab.py）と同じものを使う。出力には事前登録の中身の指紋（sha256）を書き込む。
⚠️ 出力 london-lab.json / london-lab.md は GitHub 側で生成＝手元から送らない（SYNC禁忌）。
   1000回以上でプラスと言い切れなかったものは verdicts に「ストップ」として入り、verified_list.py が検証済みリストに載せる。
⚠️ エンジン・発火条件・固定オラクル（signal_lab_verify.py）には触れない。メールや売買の決まりは変えない。

実行: python london_lab.py   （Actions の london-lab.yml から手動で。そのあと verified_list.py）
"""
import calendar
import datetime as dt
import json
import sys

import numpy as np
import pandas as pd

from box_lab import JST, LON, NY, OFFICIAL_SPREAD_PIPS, boot_ci, cost_price, local_ts, pip_size, placebo_p
from pillar_lab import fetch, prereg_sha256

MIN_N = 300            # 問いごと・これ未満は「件数不足」
ALPHA = 0.05 / 2       # 問いが2つなので厳しくする
GOAL = 1000            # オーナーの決まり：1000回以上でプラスと言い切れなければストップ（検証済みリストへ）
BP = 10000.0

# 向き：+1＝そのペアを買う／−1＝売る（どちらもドルを買う向き）
WINDOWS = {
    "L1": {"name": "ロンドンの朝にユーロ・ポンドを売る（現地 08:00→12:00）", "start": 8, "end": 12,
           "pairs": {"EURUSD=X": -1, "GBPUSD=X": -1}},
    "L2": {"name": "ロンドン16時の値決めの前にドルを買う（現地 12:00→16:00）", "start": 12, "end": 16,
           "pairs": {"EURUSD=X": -1, "GBPUSD=X": -1, "AUDUSD=X": -1, "USDJPY=X": +1}},
}
# 読むための表だけ：値決めのあと（現地 16:00→20:00）にドルを売る（論文の「後はドル安」）
AFTER_FIX = {"start": 16, "end": 20, "pairs": {"EURUSD=X": +1, "GBPUSD=X": +1, "AUDUSD=X": +1, "USDJPY=X": -1}}
PAIR_NAME = {"EURUSD=X": "ユーロドル", "GBPUSD=X": "ポンドドル", "AUDUSD=X": "豪ドル米ドル", "USDJPY=X": "ドル円"}
TICKERS = sorted({t for w in WINDOWS.values() for t in w["pairs"]})
OUT_JSON, OUT_MD = "london-lab.json", "london-lab.md"


def last_weekday(d):
    """その月の最後の平日（祝日は見ない）"""
    last = dt.date(d.year, d.month, calendar.monthrange(d.year, d.month)[1])
    while last.weekday() >= 5:
        last -= dt.timedelta(days=1)
    return last


def dst_gap(d):
    """米国と英国の夏時間がずれる日＝ロンドンとニューヨークの時差が5時間でない日"""
    noon = dt.datetime(d.year, d.month, d.day, 12)
    diff = noon.replace(tzinfo=LON).utcoffset() - noon.replace(tzinfo=NY).utcoffset()
    return diff != dt.timedelta(hours=5)


def trades_for(bars, ticker, start, end, direction):
    """bars＝UTC 添字の1時間足。ロンドンの平日ごとに、現地 start 時の足の始値で入り、end 時の足の始値で出る。
    戻り値＝取引の行のリスト（どちらかの足が無い日は数えない）"""
    opens = bars["Open"]
    idx = set(bars.index)
    days = sorted({t.tz_convert(LON).date() for t in bars.index})
    rows = []
    for d in days:
        if d.weekday() >= 5:
            continue
        t0, t1 = local_ts(d, start, LON), local_ts(d, end, LON)
        if t0 not in idx or t1 not in idx:
            continue
        entry, exit_ = float(opens[t0]), float(opens[t1])
        if not (entry > 0 and exit_ > 0):
            continue
        gross = direction * (exit_ - entry) / entry * BP
        cost = cost_price(ticker) / entry * BP
        off = OFFICIAL_SPREAD_PIPS.get(ticker)
        path = {}
        for k in range(1, end - start + 1):
            tk = local_ts(d, start + k, LON)
            if tk in idx:
                path[k] = direction * (float(opens[tk]) - entry) / entry * BP
        rows.append({"ticker": ticker, "date": d.isoformat(), "weekday": d.weekday(), "gross": gross, "cost": cost,
                     "net": gross - cost, "mirror_net": -gross - cost,
                     "net_official": None if off is None else gross - off * pip_size(ticker) / entry * BP,
                     "month_end": d == last_weekday(d), "dst_gap": dst_gap(d), "path": path})
    return rows


def _m(xs):
    xs = [x for x in xs if x is not None]
    return float(np.mean(xs)) if xs else None


def judge(r):
    if r["n"] < MIN_N:
        return "件数不足"
    lo, hi, e, l, p = r["lo"], r["hi"], r["early"], r["late"], r["p"]
    if lo > 0 and e > 0 and l > 0 and p < ALPHA:
        return "過去2年では残る"
    if hi < 0 and e < 0 and l < 0 and p < ALPHA:
        return "逆に効く"
    return "差なし"


def window_stats(rows):
    res = {"n": len(rows)}
    if not rows:
        res["verdict"] = "件数不足"
        return res
    net = [r["net"] for r in rows]
    dates = [r["date"] for r in rows]
    res["mean"] = float(np.mean(net))
    res["lo"], res["hi"] = boot_ci(net, dates)
    ud = sorted(set(dates))
    mid = ud[len(ud) // 2]
    early = [r["net"] for r in rows if r["date"] < mid]
    late = [r["net"] for r in rows if r["date"] >= mid]
    res.update({"split": mid, "early": _m(early), "late": _m(late), "n_early": len(early), "n_late": len(late),
                "first": ud[0], "last": ud[-1], "days": len(ud)})
    res["p"], res["placebo_mean"] = placebo_p(net, [r["mirror_net"] for r in rows])
    res["verdict"] = judge(res)
    # ── 読むための表（判定には使わない）──
    res["gross"] = _m(r["gross"] for r in rows)
    res["cost_median"] = float(np.median([r["cost"] for r in rows]))
    off = [r for r in rows if r["net_official"] is not None]
    res["net_official"] = {"n": len(off), "mean": _m(r["net_official"] for r in off)}
    res["by_pair"] = {tk: {"n": len(v), "mean": _m(v), "gross": _m(g), "official": _m(o)}
                      for tk in TICKERS
                      for v, g, o in [([r["net"] for r in rows if r["ticker"] == tk],
                                       [r["gross"] for r in rows if r["ticker"] == tk],
                                       [r["net_official"] for r in rows if r["ticker"] == tk])] if v}
    hours = sorted({k for r in rows for k in r["path"]})
    res["path"] = {str(k): _m(r["path"].get(k) for r in rows) for k in hours}
    wd = "月火水木金"
    res["by_weekday"] = {wd[i]: {"n": len(v), "mean": _m(v)} for i in range(5)
                         for v in [[r["net"] for r in rows if r["weekday"] == i]] if v}
    for key, name in (("month_end", "by_month_end"), ("dst_gap", "by_dst_gap")):
        yes = [r["net"] for r in rows if r[key]]
        no = [r["net"] for r in rows if not r[key]]
        res[name] = {"yes": {"n": len(yes), "mean": _m(yes)}, "no": {"n": len(no), "mean": _m(no)}}
    return res


def owner_rule(r, today):
    """オーナーの決まり：1000回以上で、費用後の平均の95%の幅がまるごと0より上でなければストップ（検証済みリストへ）。
    verified_list.py は損益率（小数）で書くので、ベーシスポイントを 10000 で割って渡す"""
    if r.get("n", 0) < GOAL or r.get("lo") is None:
        return None
    if r["lo"] > 0:
        return None
    reason = ("費用後の平均がマイナス" if r["mean"] <= 0
              else "費用後の平均はプラスだが、95％の幅が0をまたぐ（プラスと言い切れない）")
    return {"status": "stop", "decided_on": today, "n": r["n"], "mean": r["mean"] / BP, "lo": r["lo"] / BP,
            "hi": r["hi"] / BP, "reason": reason + "（過去2年・1回だけ数えた）"}


def _f(x, nd=2, sign=True):
    if x is None:
        return "—"
    return f"{x:+.{nd}f}" if sign else f"{x:.{nd}f}"


def render_md(out):
    L = ["# L1・L2 ロンドン時間のドルの流れの結果", "",
         f"作成: {out['generated_jst']}（GitHub Actions で計算）。事前登録＝`PILLAR_PREREG.md`「L1・L2 ロンドン時間のドルの流れ」"
         f"（指紋 sha256 `{(out['prereg_sha256'] or '')[:16]}…`）。",
         "値＝1回の取引の損益（ベーシスポイント＝0.01％・費用後）。費用＝S1 と同じ約束（円のペア 0.8pips・ほか 1.2pips × 1.5）。**売買の決まりではない**。", "",
         f"判定＝費用後の平均の95%の幅がまるごと0より上・前半と後半ともプラス・偽薬（向きだけコイン）との比較 p＜{ALPHA:g}（問いが2つ）。"
         f"件数{MIN_N}未満は件数不足。{GOAL}回以上でプラスと言い切れなければ検証済みリストへ", ""]
    if out["missing"]:
        L += [f"⚠️ 取得できなかったペア：{'・'.join(PAIR_NAME[t] for t in out['missing'])}", ""]
    L += ["| 問い | 件数 | 平均 | 95%の幅 | 前半 | 後半 | 偽薬の平均 | 偽薬との比較 p | 判定 |",
          "|---|---:|---:|---|---:|---:|---:|---:|---|"]
    for k, w in WINDOWS.items():
        r = out["windows"][k]
        if r["n"] == 0:
            L.append(f"| {k} {w['name']} | 0 | — | — | — | — | — | — | {r['verdict']} |")
            continue
        L.append(f"| {k} {w['name']} | {r['n']} | {_f(r['mean'])} | {_f(r['lo'])}〜{_f(r['hi'])} | {_f(r['early'])} | "
                 f"{_f(r['late'])} | {_f(r['placebo_mean'])} | {r['p']:.4f} | {r['verdict']} |")
    stops = out.get("verdicts") or {}
    if stops:
        L += ["", "⏹ **検証済みリストへ（1000回以上でプラスと言い切れない）**：" + "・".join(stops)]
    L += ["", "## 読むための表（判定には使わない）", ""]
    for k, w in WINDOWS.items():
        r = out["windows"][k]
        if not r.get("n"):
            continue
        L += [f"### {k} {w['name']}（{r['first']}〜{r['last']}・{r['days']}日・前半と後半の境 {r['split']}）", "",
              f"- 費用前の平均 {_f(r['gross'])}／費用の中央値 {_f(r['cost_median'], sign=False)}／"
              f"公式スプレッドで引いた平均 {_f(r['net_official']['mean'])}（{r['net_official']['n']}件）",
              "- 入ってからの道のり（費用前の平均）：" + "・".join(f"{h}時間後 {_f(v)}" for h, v in r["path"].items()), "",
              "| ペア | 件数 | 費用後 | 費用前 | 公式スプレッドで引いた場合 |", "|---|---:|---:|---:|---:|"]
        L += [f"| {PAIR_NAME[t]} | {v['n']} | {_f(v['mean'])} | {_f(v['gross'])} | {_f(v['official'])} |"
              for t, v in r["by_pair"].items()]
        L += ["", "| 曜日 | 件数 | 費用後 |", "|---|---:|---:|"]
        L += [f"| {k2} | {v['n']} | {_f(v['mean'])} |" for k2, v in r["by_weekday"].items()]
        me, dg = r["by_month_end"], r["by_dst_gap"]
        L += ["", f"- 月末の日 {me['yes']['n']}件 {_f(me['yes']['mean'])}／それ以外 {me['no']['n']}件 {_f(me['no']['mean'])}",
              f"- 米英の夏時間がずれる日 {dg['yes']['n']}件 {_f(dg['yes']['mean'])}／それ以外 {dg['no']['n']}件 {_f(dg['no']['mean'])}", ""]
    a = out.get("after_fix") or {}
    if a.get("n"):
        L += ["### 値決めのあと（現地 16:00→20:00 にドルを売る）＝論文の「後はドル安」の確認", "",
              f"- {a['n']}件・費用前 {_f(a['gross'])}・費用後 {_f(a['mean'])}（幅 {_f(a['lo'])}〜{_f(a['hi'])}）", ""]
    L += ["---", "", "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。"]
    return "\n".join(L) + "\n"


def run(bars_by_ticker, today):
    rows = {k: [] for k in WINDOWS}
    after = []
    for tk, bars in bars_by_ticker.items():
        for k, w in WINDOWS.items():
            if tk in w["pairs"]:
                rows[k] += trades_for(bars, tk, w["start"], w["end"], w["pairs"][tk])
        if tk in AFTER_FIX["pairs"]:
            after += trades_for(bars, tk, AFTER_FIX["start"], AFTER_FIX["end"], AFTER_FIX["pairs"][tk])
    windows = {k: window_stats(v) for k, v in rows.items()}
    af = {"n": len(after)}
    if after:
        af["gross"], af["mean"] = _m(r["gross"] for r in after), _m(r["net"] for r in after)
        af["lo"], af["hi"] = boot_ci([r["net"] for r in after], [r["date"] for r in after])
    verdicts = {k: v for k in WINDOWS for v in [owner_rule(windows[k], today)] if v}
    return windows, af, verdicts


def main():
    bars_by, missing = {}, []
    for tk in TICKERS:
        b = fetch(tk, "1h")
        if b is None:
            missing.append(tk)
        else:
            bars_by[tk] = b
            print(f"{tk}: 足 {len(b)}", file=sys.stderr)
    today = dt.datetime.now(JST).date().isoformat()
    windows, af, verdicts = run(bars_by, today) if bars_by else ({k: {"n": 0, "verdict": "件数不足"} for k in WINDOWS}, {}, {})
    out = {"generated_jst": dt.datetime.now(JST).strftime("%Y-%m-%dT%H:%M+09:00"), "prereg_sha256": prereg_sha256(),
           "kind": "backtest", "goal": GOAL, "missing": missing,
           "titles": {k: w["name"] for k, w in WINDOWS.items()}, "verdicts": verdicts,
           "windows": windows, "after_fix": af}
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(render_md(out))
    print(render_md(out))
    return 0 if not missing else 1


if __name__ == "__main__":
    sys.exit(main())
