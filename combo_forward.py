# -*- coding: utf-8 -*-
"""前向きの観察：一目均衡表の三役 × ボリンジャー下限タッチ × 追いかける損切り（2026-09-27 夜登録）。

組み合わせの相性ラボ（combo_lab.py）で後半の確かめに届かなかったが、向きだけは残った1つを、
**登録後の新しいデータだけで**数える（オーナー「両方進めてください」）。結果を見たあとで選んだ候補なので、
過去のデータで何度確かめても意味がない＝前向きだけが確かめになる。

⚠️ 決まりは PILLAR_PREREG.md「前向きの観察：一目均衡表 × ボリンジャー下限タッチ × 追いかける損切り」と下の定数に固定。
⚠️ 合図・出口・費用の計算は combo_lab.py の関数をそのまま使う（ここで計算し直さない＝ラボとずれない）。
⚠️ 出力 combo-forward.json / combo-forward.md は GitHub 側で生成＝手元から送らない（SYNC禁忌）。
   区切りの数字は一度出たら固定＝古い版で上書きすると記録が消える。
⚠️ エンジン・発火条件・固定オラクル・メールには触れない。

実行: python combo_forward.py                    （Actions の combo-forward.yml から。毎月3日）
      python combo_forward.py --once-per-month   （保険の回：今月分が履歴にあれば何もしない）
"""
import datetime as dt
import json
import os
import sys

import numpy as np

import combo_lab as C
import pillar_lab as P
import trend_lab as TL
from signal_lab_sweep import cost_r_of

OUT_JSON, OUT_MD = "combo-forward.json", "combo-forward.md"
FWD_START = "2026-09-28"        # 入る日がこの日以降の取引だけ数える
TREND, OSC, EXIT = "T4", "O4", "X6"
CAP = 60                        # X6 の最長（この本数がすぎた取引だけ数える＝早く終わった負けに偏らない）
CHECKS = (50, 100, 150)         # 区切り。150 で「残った」にならなければ観察を終える
P_LIMIT = 0.05                  # 1つだけの問いなので割らない
N_PERM = 2000
PER_YEAR = 29                   # 後半（2016-01〜2026-09）の実績 315件÷約10.7年（見込みの説明用・判定には使わない）


def quarter(date):
    return f"{date[:4]}Q{(int(date[5:7]) - 1) // 3 + 1}"


def _cost(ticker, entry, unit):
    return cost_r_of({"entry": entry, "stop_loss": entry - unit, "ticker": ticker})


def trades_for(ticker, df):
    """登録後の取引 → ([数えた取引], [まだ60本たっていない取引])。最後の1本は作りかけかもしれないので使わない"""
    df = df.iloc[:-1]
    if len(df) < TL.WARMUP + 2:
        return [], []
    o, h, l, c, atr, ma5 = C._series(df)
    states = TL.all_states(df)
    sig = C.osc_signals(df)
    dates = [x.date().isoformat() for x in df.index]
    n = len(c)
    done, open_ = [], []
    for side, s in (("long", 1.0), ("short", -1.0)):
        last = -10 ** 9
        for i in np.flatnonzero(sig[(OSC, side)]):
            # combo_lab.entries_for と同じ「5本あける」の数え方（登録前の合図も数え方にだけ使う）
            if i < TL.WARMUP or i + 1 >= n or i - last < C.COOLDOWN:
                continue
            last = i
            if dates[i + 1] < FWD_START or states[TREND][i] != s or not atr[i] > 0:
                continue
            rec = {"ticker": ticker, "signal": dates[i], "entry": dates[i + 1], "sign": s}
            r = C.simulate(o, h, l, c, ma5, atr[i], i, side, EXIT)
            if r is None:                               # まだ60本たっていない
                open_.append(rec)
                continue
            rec["R"] = r - _cost(ticker, o[i + 1], C.RISK_ATR * atr[i])
            done.append(rec)
    return done, open_


def pool_for(ticker, df, end):
    """偽薬の元＝登録後〜end に入る日のうち、一目三役の向きが合う全部の日に入った場合の R（数えられるものだけ）"""
    df = df.iloc[:-1]
    if len(df) < TL.WARMUP + 2:
        return {}
    o, h, l, c, atr, ma5 = C._series(df)
    states = TL.all_states(df)
    dates = [x.date().isoformat() for x in df.index]
    out = {}
    for side, s in (("long", 1.0), ("short", -1.0)):
        vals = []
        for i in range(TL.WARMUP, len(c) - 1):
            if not (FWD_START <= dates[i + 1] <= end) or states[TREND][i] != s or not atr[i] > 0:
                continue
            r = C.simulate(o, h, l, c, ma5, atr[i], i, side, EXIT)
            if r is not None:
                vals.append(r - _cost(ticker, o[i + 1], C.RISK_ATR * atr[i]))
        out[(ticker, s)] = np.array(vals)
    return out


def order(trades):
    return sorted(trades, key=lambda x: (x["entry"], x["ticker"], -x["sign"]))


def stats(xs):
    return P.mean_ci([x["R"] for x in xs], [(x["ticker"], quarter(x["entry"])) for x in xs])


def checkpoint(done, k, data, n_perm=N_PERM):
    """入る日が早い順の最初の k 件で1回判定する"""
    xs = order(done)[:k]
    st = stats(xs)
    end = xs[-1]["entry"]
    counts = {}
    for x in xs:
        counts[(x["ticker"], x["sign"])] = counts.get((x["ticker"], x["sign"]), 0) + 1
    pool = {}
    for tk in {x["ticker"] for x in xs}:
        pool.update(pool_for(tk, data[tk], end))
    sims = C.placebo(pool, counts, n_perm=n_perm)
    p = None
    if sims is not None and st.get("mean") is not None:
        cen = float(np.mean(sims))
        p = float((np.sum(np.abs(sims - cen) >= abs(st["mean"] - cen)) + 1) / (len(sims) + 1))
        st["placebo_mean"] = cen
    st.update(p_placebo=p, last_entry=end, ok=bool(st.get("lo") is not None and st["lo"] > 0 and p is not None and p < P_LIMIT),
              neg=bool(st.get("hi") is not None and st["hi"] < 0))
    return st


def verdict(cps):
    """cps＝{"50": 区切りの記録, ...}。区切りを順に見て、先に起きたほうで決める"""
    seq = [cps[str(k)] for k in CHECKS if str(k) in cps]
    for j, x in enumerate(seq):
        if x.get("neg"):
            return "前向きで消えた（はっきり負け）"
        if j >= 1 and seq[j - 1].get("ok") and x.get("ok"):
            return "前向きでも残った"
    if len(seq) == len(CHECKS):
        return "前向きで確かめられなかった（観察終わり）"
    return "観察中"


def merge_checkpoints(old, new):
    """一度出た区切りの数字は書き換えない（値段のデータがあとで直っても）"""
    out = dict(old or {})
    for k, v in (new or {}).items():
        out.setdefault(k, v)
    return out


def run(prev, today, n_perm=N_PERM):
    data, missing, done, open_ = {}, [], [], []
    for tk in TL.TICKERS:
        df = P.fetch(tk, "1d", start=TL.START)
        if df is None or len(df) < TL.WARMUP + 80:
            missing.append(tk)
            continue
        df = df.dropna(subset=["Open", "High", "Low", "Close"])
        data[tk] = df
        d, op = trades_for(tk, df)
        done += d
        open_ += op
    cps = dict((prev or {}).get("checkpoints") or {})
    new = {}
    for k in CHECKS:
        # 値段を取れなかった銘柄がある月は区切りを出さない（欠けたまま固定しない）
        if not missing and str(k) not in cps and len(done) >= k:
            new[str(k)] = dict(checkpoint(done, k, data, n_perm=n_perm), fixed_on=today)
    cps = merge_checkpoints(cps, new)
    return {"done": order(done), "open": len(open_), "open_by_side": {"買い": sum(x["sign"] > 0 for x in open_),
                                                                      "売り": sum(x["sign"] < 0 for x in open_)},
            "now": stats(done) if done else {"n": 0}, "checkpoints": cps, "verdict": verdict(cps), "missing": missing}


# ════════════════════ 出力 ════════════════════

def render_md(res):
    f = P._f
    r = res.get("result") or {}
    L = ["# 前向きの観察：一目均衡表 × ボリンジャー下限タッチ × 追いかける損切り", "",
         f"作成: {res['generated_at']}（GitHub Actions で毎月計算）。事前登録＝`{P.PREREG}`「前向きの観察」"
         f"（指紋 sha256 `{(res.get('prereg_sha256') or '')[:16]}…`）。",
         f"数えるのは**入る日が {FWD_START} 以降**で、**入ってから{CAP}本がすぎた取引だけ**。"
         "値＝1回の取引の損益（R・費用後。1R＝入る時の ATR×1.5）。**売買の決まりではない**。", ""]
    if r.get("error"):
        return "\n".join(L + [f"- ⚠️ 計算できず: {r['error']}", ""]) + "\n"
    now = r.get("now") or {}
    L += [f"## いまの判定：**{r.get('verdict', '観察中')}**", "",
          f"- 数えた取引 {now.get('n', 0)} 件／まだ{CAP}本たっていない取引 {r.get('open', 0)} 件（数えない）",
          f"- 区切り＝{'・'.join(str(k) for k in CHECKS)} 件。2回続けて「幅がまるごと0より上 かつ 偽薬との比較 p＜{P_LIMIT}」なら「前向きでも残った」",
          f"- 見込み：年に約{PER_YEAR}件（過去10年の実績）。最初の区切りは早くて2028年秋ごろ。すぐに成績を上げる手段ではない", ""]
    cps = r.get("checkpoints") or {}
    L += ["## 区切りの記録（一度出たら書き換えない）", ""]
    if cps:
        L += ["| 区切り | 平均R | 95%の幅 | 偽薬の平均 | p | 条件 | 最後に入った日 | 記録した日 |", "|---:|---:|---|---:|---:|---|---|---|"]
        for k in CHECKS:
            x = cps.get(str(k))
            if x:
                L.append(f"| {k}件 | {f(x.get('mean'))} | {f(x.get('lo'))}〜{f(x.get('hi'))} | {f(x.get('placebo_mean'))} | "
                         f"{f(x.get('p_placebo'), 4, False)} | {'満たした' if x.get('ok') else '満たさない'} | "
                         f"{x.get('last_entry')} | {x.get('fixed_on')} |")
    else:
        L.append(f"- まだ無い（最初の区切りは {CHECKS[0]} 件目）")
    L += ["", "## 毎月の数字（読むための記録・判定には使わない）", "",
          "| 月 | 数えた取引 | 平均R | 95%の幅 | 未確定 |", "|---|---:|---:|---|---:|"]
    for h in res.get("history") or []:
        L.append(f"| {h['month']} | {h['n']} | {f(h.get('mean'))} | {f(h.get('lo'))}〜{f(h.get('hi'))} | {h.get('open', 0)} |")
    done = r.get("done") or []
    if done:
        L += ["", "## 数えた取引（入った日順）", "", "| 入った日 | 銘柄 | 向き | R（費用後） |", "|---|---|---|---:|"]
        for x in done:
            L.append(f"| {x['entry']} | {x['ticker']} | {'買い' if x['sign'] > 0 else '売り'} | {f(x['R'])} |")
    L += ["", "- 比べる相手（組み合わせの相性ラボの後半 2016〜）：この組み合わせ +0.259R（315件・幅 −0.035〜+0.553・p＝0.069）／"
          "同じ条件のでたらめな入口 +0.057R／トレンドなし −0.013R"]
    if r.get("missing"):
        L.append(f"- 値段を取れなかった銘柄：{', '.join(r['missing'])}")
    L += ["", "---", "", "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。"]
    return "\n".join(L) + "\n"


def load_prev(path=OUT_JSON):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    now = dt.datetime.now(P.JST)
    month, today = now.strftime("%Y-%m"), now.date().isoformat()
    prev = load_prev()
    hist = list(prev.get("history") or [])
    if "--once-per-month" in argv and any(h.get("month") == month for h in hist):
        print(f"今月分（{month}）は記録済み＝何もしない")
        return 0
    res = {"generated_at": now.isoformat(timespec="minutes"), "prereg_file": P.PREREG, "prereg_sha256": P.prereg_sha256()}
    try:
        res["result"] = run(prev.get("result") or {}, today)
    except Exception as e:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        res["result"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
        res["result"]["checkpoints"] = (prev.get("result") or {}).get("checkpoints") or {}   # 記録は消さない
    r = res["result"]
    if not r.get("error"):
        now_st = r["now"]
        hist = [h for h in hist if h.get("month") != month] + [
            {"month": month, "n": now_st.get("n", 0), "mean": now_st.get("mean"), "lo": now_st.get("lo"),
             "hi": now_st.get("hi"), "open": r.get("open", 0)}]
    res["history"] = hist
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1, default=str)
    md = render_md(res)
    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
