# -*- coding: utf-8 -*-
"""L4 ロンドン時間に入って、長めに持つ（サイトの通貨の強弱で、いちばん強い通貨を買い、いちばん弱い通貨を売る）。
2026-09-30 夕登録・オーナー「そしたらテストをしてください」。

ロンドン 08:00 に、サイトがメールで出している通貨の強弱（generate_technical_alerts.calc_currency_strength と同じ計算）で
いちばん強い通貨を買い、いちばん弱い通貨を売って、8時間（H8）／1日（H24）／5日（H120）持つ。
⚠️ 物差しと判定の基準は PILLAR_PREREG.md「L4 ロンドン時間に入って、長めに持つ」（事前登録・計算より先にコミット済み）と下の定数に固定。
   結果を見てから動かさない。費用・偽薬・幅の関数は S1（box_lab.py）と同じものを使う。出力には事前登録の中身の指紋（sha256）を書き込む。
⚠️ スワップ（金利差）は入れていない（事前登録に限界として明記）。
⚠️ 出力 london-hold-lab.json / .md は GitHub 側で生成＝手元から送らない（SYNC禁忌）。
⚠️ エンジン・発火条件・固定オラクル（signal_lab_verify.py）には触れない。メールや売買の決まりは変えない。

実行: python london_hold_lab.py   （Actions の london-hold-lab.yml から手動で。そのあと verified_list.py）
"""
import datetime as dt
import json
import sys

import numpy as np

from box_lab import JST, LON, OFFICIAL_SPREAD_PIPS, boot_ci, cost_price, local_ts, pip_size, placebo_p
from generate_technical_alerts import FX_PAIR_MAP
from pillar_lab import fetch, prereg_sha256

STRENGTH_PAIRS = dict(FX_PAIR_MAP)                              # サイトの強弱に使う9ペア
TRADE_PAIRS = dict(FX_PAIR_MAP, **{"EURGBP=X": ("EUR", "GBP")})  # 取引に使う10ペア
BACK = 23              # サイトのコード：最新（iloc[-1]）と iloc[-24] を比べる＝間は23本
MIN_PAIRS = 7          # 9ペアのうち7ペア以上で計算できない日は数えない
ENTRY_HOUR = 8         # ロンドン 08:00 に始まる足の始値で入る
MIN_N = 300
ALPHA = 0.05 / 3       # 問いが3つ
GOAL = 1000
BP = 10000.0
HOLDS = {
    "H8": {"name": "8時間（同じ日のロンドン 16:00）", "hours": 16, "days": 0, "cluster": "day"},
    "H24": {"name": "1日（次の平日のロンドン 08:00）", "hours": 8, "days": 1, "cluster": "day"},
    "H120": {"name": "5日（5つ先の平日のロンドン 08:00）", "hours": 8, "days": 5, "cluster": "month"},
}
CUR = ["USD", "EUR", "GBP", "JPY", "AUD"]
PAIR_NAME = {"USDJPY=X": "ドル円", "EURJPY=X": "ユーロ円", "GBPJPY=X": "ポンド円", "AUDJPY=X": "豪ドル円",
             "EURUSD=X": "ユーロドル", "GBPUSD=X": "ポンドドル", "AUDUSD=X": "豪ドル米ドル", "EURAUD=X": "ユーロ豪ドル",
             "GBPAUD=X": "ポンド豪ドル", "EURGBP=X": "ユーロポンド"}
OUT_JSON, OUT_MD = "london-hold-lab.json", "london-hold-lab.md"


def nth_weekday(d, n):
    """d から n 個先の平日（土日を飛ばす）。n=0 は d"""
    while n > 0:
        d += dt.timedelta(days=1)
        if d.weekday() < 5:
            n -= 1
    return d


def strength_at(series, t_last):
    """series＝{ticker: (添字の辞書, 終値の配列)}。t_last＝ロンドン 07:00 に始まる足（入る直前に確定した足）。
    サイトと同じく、各ペアの（最新の終値÷ BACK 本前の終値 −1）を通貨ごとに＋／−で平均する。計算できたペアが MIN_PAIRS 未満なら None"""
    scores = {c: [] for c in CUR}
    used = 0
    for tk, (base, quote) in STRENGTH_PAIRS.items():
        if tk not in series:
            continue
        pos, close = series[tk]
        i = pos.get(t_last)
        if i is None or i - BACK < 0 or not close[i - BACK]:
            continue
        ch = (close[i] - close[i - BACK]) / close[i - BACK] * 100
        scores[base].append(ch)
        scores[quote].append(-ch)
        used += 1
    if used < MIN_PAIRS:
        return None
    return {c: float(np.mean(v)) for c, v in scores.items() if v}


def pick_pair(strength):
    """いちばん強い S を買い、いちばん弱い W を売るペアと向き"""
    s = max(strength, key=strength.get)
    w = min(strength, key=strength.get)
    for tk, (b, q) in TRADE_PAIRS.items():
        if (b, q) == (s, w):
            return tk, +1, strength[s] - strength[w]
        if (b, q) == (w, s):
            return tk, -1, strength[s] - strength[w]
    return None, 0, None


def build_trades(bars_by):
    """bars_by＝{ticker: UTC 添字の1時間足}。戻り値＝{H8/H24/H120: 取引の行}"""
    series = {tk: ({t: i for i, t in enumerate(b.index)}, b["Close"].to_numpy(float)) for tk, b in bars_by.items()}
    opens = {tk: b["Open"] for tk, b in bars_by.items()}
    idx = {tk: set(b.index) for tk, b in bars_by.items()}
    days = sorted({t.tz_convert(LON).date() for b in bars_by.values() for t in b.index})
    rows = {k: [] for k in HOLDS}
    for d in days:
        if d.weekday() >= 5:
            continue
        st = strength_at(series, local_ts(d, ENTRY_HOUR - 1, LON))
        if not st:
            continue
        tk, direction, gap = pick_pair(st)
        if tk is None or tk not in bars_by:
            continue
        t0 = local_ts(d, ENTRY_HOUR, LON)
        if t0 not in idx[tk]:
            continue
        entry = float(opens[tk][t0])
        for k, h in HOLDS.items():
            t1 = local_ts(nth_weekday(d, h["days"]), h["hours"], LON)
            if t1 not in idx[tk] or not entry > 0:
                continue
            exit_ = float(opens[tk][t1])
            gross = direction * (exit_ - entry) / entry * BP
            cost = cost_price(tk) / entry * BP
            off = OFFICIAL_SPREAD_PIPS.get(tk)
            rows[k].append({"ticker": tk, "dir": direction, "date": d.isoformat(), "month": d.isoformat()[:7],
                            "weekday": d.weekday(), "gap": gap, "gross": gross, "cost": cost, "net": gross - cost,
                            "mirror_net": -gross - cost,
                            "net_official": None if off is None else gross - off * pip_size(tk) / entry * BP})
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


def hold_stats(rows, cluster):
    res = {"n": len(rows)}
    if not rows:
        res["verdict"] = "件数不足"
        return res
    net = [r["net"] for r in rows]
    keys = [r["date"] if cluster == "day" else r["month"] for r in rows]
    res["mean"] = float(np.mean(net))
    res["lo"], res["hi"] = boot_ci(net, keys)
    ud = sorted({r["date"] for r in rows})
    mid = ud[len(ud) // 2]
    early = [r["net"] for r in rows if r["date"] < mid]
    late = [r["net"] for r in rows if r["date"] >= mid]
    res.update({"split": mid, "early": _m(early), "late": _m(late), "first": ud[0], "last": ud[-1]})
    res["p"], res["placebo_mean"] = placebo_p(net, [r["mirror_net"] for r in rows])
    res["verdict"] = judge(res)
    # ── 読むための表（判定には使わない）──
    res["gross"] = _m(r["gross"] for r in rows)
    res["cost_median"] = float(np.median([r["cost"] for r in rows]))
    off = [r for r in rows if r["net_official"] is not None]
    res["net_official"] = {"n": len(off), "mean": _m(r["net_official"] for r in off)}
    res["by_pair"] = {tk: {"n": len(v), "mean": _m(v), "gross": _m(g)}
                      for tk in TRADE_PAIRS
                      for v, g in [([r["net"] for r in rows if r["ticker"] == tk],
                                    [r["gross"] for r in rows if r["ticker"] == tk])] if v}
    q1, q2 = np.quantile([r["gap"] for r in rows], [1 / 3, 2 / 3])
    terc = {}
    for r in rows:
        k = "小さい" if r["gap"] <= q1 else ("中くらい" if r["gap"] <= q2 else "大きい")
        terc.setdefault(k, []).append(r["net"])
    res["by_gap"] = {k: {"n": len(terc[k]), "mean": _m(terc[k])} for k in ("小さい", "中くらい", "大きい") if k in terc}
    wd = "月火水木金"
    res["by_weekday"] = {wd[i]: {"n": len(v), "mean": _m(v)} for i in range(5)
                         for v in [[r["net"] for r in rows if r["weekday"] == i]] if v}
    return res


def owner_rule(r, today):
    """1000回以上で、費用後の平均の95%の幅がまるごと0より上でなければストップ（検証済みリストへ・損益率は小数で）"""
    if r.get("n", 0) < GOAL or r.get("lo") is None or r["lo"] > 0:
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
    L = ["# L4 ロンドン時間に入って、長めに持つ（通貨の強弱）の結果", "",
         f"作成: {out['generated_jst']}（GitHub Actions で計算）。事前登録＝`PILLAR_PREREG.md`「L4 ロンドン時間に入って、長めに持つ」"
         f"（指紋 sha256 `{(out['prereg_sha256'] or '')[:16]}…`）。",
         "ロンドン 08:00 に、サイトの通貨の強弱でいちばん強い通貨を買い、いちばん弱い通貨を売る。"
         "値＝1回の損益（ベーシスポイント＝0.01％・費用後・**スワップは入れていない**）。**売買の決まりではない**。", "",
         f"判定＝費用後の平均の95%の幅がまるごと0より上・前半と後半ともプラス・偽薬（向きだけコイン）との比較 p＜{ALPHA:.4f}（問いが3つ）。"
         f"件数{MIN_N}未満は件数不足", ""]
    if out["missing"]:
        L += [f"⚠️ 取得できなかったペア：{'・'.join(PAIR_NAME[t] for t in out['missing'])}", ""]
    L += ["| 持つ時間 | 件数 | 平均 | 95%の幅 | 前半 | 後半 | 偽薬の平均 | 偽薬との比較 p | 判定 |",
          "|---|---:|---:|---|---:|---:|---:|---:|---|"]
    for k, h in HOLDS.items():
        r = out["holds"][k]
        if r["n"] == 0:
            L.append(f"| {k} {h['name']} | 0 | — | — | — | — | — | — | {r['verdict']} |")
            continue
        L.append(f"| {k} {h['name']} | {r['n']} | {_f(r['mean'])} | {_f(r['lo'])}〜{_f(r['hi'])} | {_f(r['early'])} | "
                 f"{_f(r['late'])} | {_f(r['placebo_mean'])} | {r['p']:.4f} | {r['verdict']} |")
    if out.get("verdicts"):
        L += ["", "⏹ **検証済みリストへ（1000回以上でプラスと言い切れない）**：" + "・".join(out["verdicts"])]
    L += ["", "## 読むための表（判定には使わない）", ""]
    for k, h in HOLDS.items():
        r = out["holds"][k]
        if not r.get("n"):
            continue
        L += [f"### {k} {h['name']}（{r['first']}〜{r['last']}・前半と後半の境 {r['split']}）", "",
              f"- 費用前の平均 {_f(r['gross'])}／費用の中央値 {_f(r['cost_median'], sign=False)}／"
              f"公式スプレッドで引いた平均 {_f(r['net_official']['mean'])}（{r['net_official']['n']}件・表にあるペアだけ）", "",
              "| 取引したペア | 件数 | 費用後 | 費用前 |", "|---|---:|---:|---:|"]
        L += [f"| {PAIR_NAME[t]} | {v['n']} | {_f(v['mean'])} | {_f(v['gross'])} |" for t, v in r["by_pair"].items()]
        L += ["", "| 強弱の差 | 件数 | 費用後 |", "|---|---:|---:|"]
        L += [f"| {k2} | {v['n']} | {_f(v['mean'])} |" for k2, v in r["by_gap"].items()]
        L += ["", "| 曜日 | 件数 | 費用後 |", "|---|---:|---:|"]
        L += [f"| {k2} | {v['n']} | {_f(v['mean'])} |" for k2, v in r["by_weekday"].items()]
        L.append("")
    L += ["---", "", "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。"]
    return "\n".join(L) + "\n"


def run(bars_by, today):
    rows = build_trades(bars_by)
    holds = {k: hold_stats(rows[k], HOLDS[k]["cluster"]) for k in HOLDS}
    verdicts = {k: v for k in HOLDS for v in [owner_rule(holds[k], today)] if v}
    return holds, verdicts


def main():
    bars_by, missing = {}, []
    for tk in TRADE_PAIRS:
        b = fetch(tk, "1h")
        if b is None:
            missing.append(tk)
        else:
            bars_by[tk] = b
            print(f"{tk}: 足 {len(b)}", file=sys.stderr)
    today = dt.datetime.now(JST).date().isoformat()
    if missing:
        holds, verdicts = {k: {"n": 0, "verdict": "件数不足"} for k in HOLDS}, {}
    else:
        holds, verdicts = run(bars_by, today)
    out = {"generated_jst": dt.datetime.now(JST).strftime("%Y-%m-%dT%H:%M+09:00"), "prereg_sha256": prereg_sha256(),
           "kind": "backtest", "goal": GOAL, "missing": missing,
           "titles": {k: f"ロンドン 08:00 に強い通貨を買い弱い通貨を売って{h['name']}持つ" for k, h in HOLDS.items()},
           "verdicts": verdicts, "holds": holds}
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(render_md(out))
    print(render_md(out))
    return 0 if not missing else 1


if __name__ == "__main__":
    sys.exit(main())
