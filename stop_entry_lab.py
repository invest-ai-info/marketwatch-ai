# -*- coding: utf-8 -*-
"""SE 損切りの線まで待って、同じ向きに指値で入る（日足・4時間足・入口60）。

2026-10-24 登録＝PILLAR_PREREG.md「SE」（オーナー「今までのテクニカルの検証を、まず損切りラインを確認して、
そのラインに到達したときにエントリーするという形にしたらどうなるか検証してみてください」・テクニカルの区切りの例外）。

E1（exit_ind_lab.py）・M7（exit_ind_lab_4h.py）の関数を読むだけ。違うのは入り方だけ:
  合図の次の足の始値 E0・合図の足の ATR を A として、損切りの線 L＝E0−1.5A（売りは＋）に同じ向きの指値を置く。
  L を超えて動いたら L で約定（始値がすでに越えていれば始値）。約定より前に T＝E0＋2A（売りは−）に届いたら取り消し
  （同じ足で両方なら約定が先）。60本のうちに約定しなければ取り消し。
  入った後＝損切り 約定値−1.5A・利確 約定値＋2A。約定した足では利確を数えない。約定した足から60本で手じまう。
⚠️ 判定・データ・費用は登録に固定。結果を見てから動かさない。5分足の腕は手元（research/loop/se_lab.py）。
⚠️ 出力 stop-entry-lab.json / .md は GitHub 側で生成＝手元から送らない（SYNC禁忌）。

実行: python stop_entry_lab.py --check   （合図と約定の数だけ・損益は数えない・何も書かない）
      python stop_entry_lab.py           （1回だけ数える＝stop-entry-lab.yml）
"""
import argparse
import datetime as dt
import json
import sys

import numpy as np

import combo_lab as CL
import exit_ind_lab as E
import exit_ind_lab_4h as H
import pillar_lab as P
import screen_judge as J
import trend_lab as TL
from signal_lab_sweep import cost_r_of

OUT_JSON, OUT_MD = "stop-entry-lab.json", "stop-entry-lab.md"
SECTION = "## SE "
CAP = E.CAP                 # 60本（待ちも保有も）
RISK = CL.RISK_ATR          # 1R＝1.5A・損切りの線も 1.5A
TP_ATR = 2.0
ALPHA = 0.05 / 3            # 3つの足（日足・4時間足・5分足）
N_PERM = 2000
VALID, NONE, NEG = "有効（候補止まり）", "差なし", "費用後マイナス"
FRAMES = {
    "1d": {"name": "日足", "split": CL.SPLIT, "loader": E._daily, "group": lambda d: d[:4], "group_name": "銘柄と年"},
    "4h": {"name": "4時間足", "split": H.SPLIT_4H, "loader": H.load_4h, "group": lambda d: d[:7], "group_name": "銘柄と月"},
}


def se_trade(x, e, s, A, tk, tp_in_fill=False):
    """合図1つ分の結果 → (状態, R, 出口, 費用)。状態＝fill／tp_first（先に T に届いて取り消し）／timeout／tail（末尾を越える）。
    R は費用後（fill のときだけ）。tp_in_fill＝約定した足でも利確を数える（読むための上限）"""
    o, h, l, c, n = x["o"], x["h"], x["l"], x["c"], x["n"]
    if e + CAP - 1 >= n:
        return "tail", None, None, None
    E0 = o[e]
    L, T = E0 - s * RISK * A, E0 + s * TP_ATR * A
    k = fill = None
    for j in range(e, e + CAP):
        if s > 0:
            if o[j] >= T:
                return "tp_first", None, None, None
            if o[j] < L:
                k, fill = j, o[j]
            elif l[j] < L:
                k, fill = j, L
            elif h[j] >= T:
                return "tp_first", None, None, None
        else:
            if o[j] <= T:
                return "tp_first", None, None, None
            if o[j] > L:
                k, fill = j, o[j]
            elif h[j] > L:
                k, fill = j, L
            elif l[j] <= T:
                return "tp_first", None, None, None
        if k is not None:
            break
    if k is None:
        return "timeout", None, None, None
    end = k + CAP - 1
    if end >= n:
        return "tail", None, None, None
    unit = RISK * A
    sl, tp = fill - s * RISK * A, fill + s * TP_ATR * A
    px = kind = None
    for j in range(k, end + 1):
        first = j == k
        if s > 0:
            if not first and o[j] <= sl:
                px, kind = o[j], "sl"
            elif l[j] <= sl:
                px, kind = sl, "sl"
            elif not first and o[j] >= tp:
                px, kind = o[j], "tp"
            elif (not first or tp_in_fill) and h[j] >= tp:
                px, kind = tp, "tp"
        else:
            if not first and o[j] >= sl:
                px, kind = o[j], "sl"
            elif h[j] >= sl:
                px, kind = sl, "sl"
            elif not first and o[j] <= tp:
                px, kind = o[j], "tp"
            elif (not first or tp_in_fill) and l[j] <= tp:
                px, kind = tp, "tp"
        if kind:
            break
    if kind is None:
        px, kind = c[end], "time"
    cost = cost_r_of({"entry": fill, "stop_loss": fill - unit, "ticker": tk})
    return "fill", float(s * (px - fill) / unit - cost), kind, float(cost)


def market_r(x, e, s, A, tk):
    """いまの形（合図の次の足の始値で成行・S0×P0）の R（費用後）＝E1 と同じ"""
    unit = RISK * A
    return float(E.outcome(x, e, s, A, "S0", "P0") - cost_r_of({"entry": x["o"][e], "stop_loss": x["o"][e] - unit, "ticker": tk}))


def signals_for(tk, df, x):
    """E1 の entries_for と同じ合図（6オシレーター・5本あける）。同じ足・同じ向きは1つにまとめ、どの入口から来たかを持つ"""
    n = x["n"]
    states = TL.all_states(df)
    sig = CL.osc_signals(df)
    out = {}
    for (osc, side), mask in sig.items():
        s = 1.0 if side == "long" else -1.0
        last = -10 ** 9
        for i in np.flatnonzero(mask):
            if i < TL.WARMUP or i + 1 >= n or i - last < CL.COOLDOWN:
                continue
            last = i
            e = i + 1
            A = x["atr"][i]
            if e + CAP - 1 >= n or not A > 0:
                continue
            rec = out.get((e, s))
            if rec is None:
                rec = out[(e, s)] = {"ticker": tk, "e": int(e), "sign": s, "A": float(A),
                                     "date": df.index[e].date().isoformat(), "oscs": [],
                                     "st": [float(states[t][i]) for t in TL.NAMES]}
            rec["oscs"].append(osc)
    return [out[k] for k in sorted(out)]


def load_frame(frame):
    data, ctxs, missing = {}, {}, []
    for tk in TL.TICKERS:
        df = FRAMES[frame]["loader"](tk)
        if df is None or len(df) < TL.WARMUP + 80:
            missing.append(tk)
            continue
        df = df.dropna(subset=["Open", "High", "Low", "Close"])
        data[tk], ctxs[tk] = df, E.make_ctx(df)
    return data, ctxs, missing


def count_frame(data, ctxs, with_r=True):
    """合図ごとの記録（末尾を越えるものは外す）。with_r=False（check）では状態だけで R を持たない"""
    recs = []
    for tk, df in data.items():
        x = ctxs[tk]
        for r in signals_for(tk, df, x):
            status, R, kind, cost = se_trade(x, r["e"], r["sign"], r["A"], tk)
            if status == "tail":
                continue
            r = dict(r, status=status)
            if with_r:
                r.update(R=R, exit=kind, cost=cost, market=market_r(x, r["e"], r["sign"], r["A"], tk))
                if status == "fill":
                    r["R_tp_in_fill"] = se_trade(x, r["e"], r["sign"], r["A"], tk, tp_in_fill=True)[1]
            recs.append(r)
    return recs


def random_pool(data, ctxs):
    """偽薬：同じ銘柄・同じ向きの全部の足を合図とみなし、同じ指値の形で約定した取引の R"""
    pool = {}
    for tk in data:
        x = ctxs[tk]
        for s in (1.0, -1.0):
            vals = []
            for i in range(TL.WARMUP, x["n"] - 1):
                A = x["atr"][i]
                if not A > 0:
                    continue
                status, R, _, _ = se_trade(x, i + 1, s, A, tk)
                if status == "fill":
                    vals.append(R)
            pool[(tk, s)] = np.array(vals)
    return pool


def _m(xs):
    xs = [v for v in xs if v is not None]
    return float(np.mean(xs)) if xs else None


def judge(st, p, cen, front, back):
    """登録の3つ：幅がまるごと0より上・偽薬より上で p＜ALPHA・前半後半ともプラス"""
    if (st.get("lo") is not None and st["lo"] > 0 and p is not None and p < ALPHA and cen is not None
            and st["mean"] > cen and (front or 0) > 0 and (back or 0) > 0):
        return VALID
    if st.get("hi") is not None and st["hi"] < 0:
        return NEG
    return NONE


def analyze(frame, data, ctxs, recs, n_perm=N_PERM, pool=None):
    cfg = FRAMES[frame]
    split, gk = cfg["split"], cfg["group"]
    fills = [r for r in recs if r["status"] == "fill"]
    vals = [r["R"] for r in fills]
    st = P.mean_ci(vals, [(r["ticker"], gk(r["date"])) for r in fills])
    counts = {}
    for r in fills:
        counts[(r["ticker"], r["sign"])] = counts.get((r["ticker"], r["sign"]), 0) + 1
    sims = None
    if counts:
        sims = CL.placebo(pool if pool is not None else random_pool(data, ctxs), counts, n_perm=n_perm)
    cen = p = None
    if sims is not None and st.get("mean") is not None:
        cen = float(np.mean(sims))
        p = float((np.sum(np.abs(sims - cen) >= abs(st["mean"] - cen)) + 1) / (len(sims) + 1))
    front = _m(r["R"] for r in fills if r["date"] < split)
    back = _m(r["R"] for r in fills if r["date"] >= split)
    n_sig = len(recs)
    kinds = {k: sum(1 for r in fills if r["exit"] == k) for k in ("tp", "sl", "time")}
    m_tp, m_sl = _m(r["R"] for r in fills if r["exit"] == "tp"), _m(r["R"] for r in fills if r["exit"] == "sl")
    names = list(TL.NAMES)
    by_entry = []
    for t in CL.TRENDS:
        for osc in CL.OSCS:
            xs = [r["R"] for r in fills if osc in r["oscs"] and (t == "T0" or r["st"][names.index(t)] == r["sign"])]
            by_entry.append({"t": t, "osc": osc, "n": len(xs), "mean": _m(xs)})
    by_class = {}
    for cls in sorted(set(TL.TICKERS.values())):
        xs = [r["R"] for r in fills if TL.TICKERS.get(r["ticker"]) == cls]
        by_class[cls] = {"n": len(xs), "mean": _m(xs)}
    return {
        "frame": frame, "split": split, "cluster": cfg["group_name"],
        "first": min((r["date"] for r in recs), default=None), "last": max((r["date"] for r in recs), default=None),
        "signals": n_sig, "fills": len(fills),
        "cancel_tp_first": sum(1 for r in recs if r["status"] == "tp_first"),
        "cancel_timeout": sum(1 for r in recs if r["status"] == "timeout"),
        "stats": st, "placebo_mean": cen, "p_placebo": p,
        "front": front, "back": back,
        "n_front": sum(1 for r in fills if r["date"] < split), "n_back": sum(1 for r in fills if r["date"] >= split),
        "verdict": judge(st, p, cen, front, back),
        "market_all": _m(r["market"] for r in recs), "market_filled": _m(r["market"] for r in fills),
        "per100_se": (sum(vals) / n_sig * 100) if n_sig else None,
        "per100_market": (sum(r["market"] for r in recs) / n_sig * 100) if n_sig else None,
        "exits": kinds, "mean_tp": m_tp, "mean_sl": m_sl,
        "tp_share": (kinds["tp"] / len(fills)) if fills else None,
        "breakeven_tp_share": (-m_sl / (m_tp - m_sl)) if (m_tp is not None and m_sl is not None and m_tp != m_sl) else None,
        "cost_mean": _m(r["cost"] for r in fills),
        "long": {"n": sum(1 for r in fills if r["sign"] > 0), "mean": _m(r["R"] for r in fills if r["sign"] > 0)},
        "short": {"n": sum(1 for r in fills if r["sign"] < 0), "mean": _m(r["R"] for r in fills if r["sign"] < 0)},
        "by_class": by_class, "by_entry": by_entry,
        "tp_in_fill_mean": _m(r.get("R_tp_in_fill") for r in fills),
    }


def check():
    """合図と約定の数だけ（損益は数えない・何も書かない）"""
    out = {"section_sha256": J.section_sha256(head=SECTION)}
    for frame, cfg in FRAMES.items():
        data, ctxs, missing = load_frame(frame)
        recs = count_frame(data, ctxs, with_r=False)
        out[frame] = {"tickers": len(data), "missing": missing,
                      "bars": {tk: int(ctxs[tk]["n"]) for tk in data},
                      "first": min((r["date"] for r in recs), default=None), "last": max((r["date"] for r in recs), default=None),
                      "signals": len(recs), "fills": sum(1 for r in recs if r["status"] == "fill"),
                      "cancel_tp_first": sum(1 for r in recs if r["status"] == "tp_first"),
                      "cancel_timeout": sum(1 for r in recs if r["status"] == "timeout"),
                      "fills_front": sum(1 for r in recs if r["status"] == "fill" and r["date"] < cfg["split"]),
                      "fills_back": sum(1 for r in recs if r["status"] == "fill" and r["date"] >= cfg["split"])}
    return out


def verdicts_of(results, today):
    """検証済みリスト（kind: backtest）の形。有効は plus、それ以外は stop"""
    out = {}
    for frame, r in results.items():
        if r.get("error"):
            continue
        st = r["stats"]
        reason = ("過去のデータで1回だけ数えて"
                  + ("、費用後の平均の幅がまるごとマイナス" if r["verdict"] == NEG else
                     "、でたらめな足に同じ指値を当てたものと区別できないか、幅が0をまたぐ" if r["verdict"] == NONE else
                     "、3つの関門を通った（候補止まり・実スプレッドと前向きは新しく登録してから）")
                  + f"（{FRAMES[frame]['name']}・費用後・{r['first']}〜{r['last']}）")
        out[frame] = {"status": "plus" if r["verdict"] == VALID else "stop", "decided_on": today,
                              "n": st.get("n"), "mean": st.get("mean"), "lo": st.get("lo"), "hi": st.get("hi"), "reason": reason}
    return out


def run(n_perm=N_PERM):
    results = {}
    for frame in FRAMES:
        try:
            data, ctxs, missing = load_frame(frame)
            recs = count_frame(data, ctxs)
            results[frame] = dict(analyze(frame, data, ctxs, recs, n_perm=n_perm), missing=missing)
        except Exception as e:  # noqa: BLE001
            import traceback
            traceback.print_exc()
            results[frame] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
    return results


def render_md(res):
    f = P._f
    L = ["# SE 損切りの線まで待って、同じ向きに指値で入る（日足・4時間足・入口60）", "",
         f"作成: {res['generated_at']}（GitHub Actions で計算）。事前登録＝`{P.PREREG}`「SE」（節の指紋 sha256 `{(res.get('section_sha256') or '')[:16]}…`）。",
         "値＝1回の取引の損益（R・費用後。1R＝合図の足の ATR×1.5）。**売買の決まりではない**。5分足（入口32）は手元の MT5 で別に数える。", "",
         "入り方＝合図の次の足の始値から損切りの線（1.5ATR 不利な側）に同じ向きの指値を置き、そこまで来たら入る。先に利確の値（2ATR 有利な側）に届いたか、"
         "60本のうちに来なければ入らない。入った後は損切り 1.5ATR・利確 2ATR・最長60本。", "",
         f"## 判定（足ごと・p＜{ALPHA:.4f}）", "",
         "| 足 | 約定した取引 | 平均R（費用後） | 95%の幅 | 偽薬の平均 | p | 前半 | 後半 | 判定 |",
         "|---|---:|---:|---|---:|---:|---:|---:|---|"]
    rs = res.get("results") or {}
    for frame, cfg in FRAMES.items():
        r = rs.get(frame) or {}
        if r.get("error"):
            L.append(f"| {cfg['name']} | ⚠️ 計算できず: {r['error']} | | | | | | | |")
            continue
        st = r["stats"]
        L.append(f"| {cfg['name']} | {st.get('n')} | {f(st.get('mean'))} | {f(st.get('lo'))}〜{f(st.get('hi'))} | {f(r.get('placebo_mean'))} | "
                 f"{f(r.get('p_placebo'), 4, False)} | {f(r.get('front'))}（{r.get('n_front')}） | {f(r.get('back'))}（{r.get('n_back')}） | {r['verdict']} |")
    L += ["", "## 読むための表（判定しない）", ""]
    for frame, cfg in FRAMES.items():
        r = rs.get(frame) or {}
        if r.get("error"):
            continue
        ex = r["exits"]
        L += [f"### {cfg['name']}（{r.get('first')}〜{r.get('last')}・区切り {r['split']}・幅のまとまり {r['cluster']}）", "",
              f"- 合図 {r['signals']}（同じ足・同じ向きは1つ）→ 約定 {r['fills']}（{f((r['fills'] / r['signals'] * 100) if r['signals'] else None, 1, False)}%）・"
              f"取り消し：先に利確の値 {r['cancel_tp_first']}／時間切れ {r['cancel_timeout']}",
              f"- 成行（いまの形・S0×P0）の平均R：合図の全部 {f(r['market_all'])}／約定した合図だけ {f(r['market_filled'])}",
              f"- 100合図あたりの R（約定しない合図は0）：損切りの線で入る {f(r['per100_se'], 1)}／成行 {f(r['per100_market'], 1)}",
              f"- 入った後の出口：利確 {ex['tp']}・損切り {ex['sl']}・時間切れ {ex['time']}／利確の割合 {f((r['tp_share'] or 0) * 100, 1, False)}%"
              f"（損益がつり合う割合 {f((r['breakeven_tp_share'] or 0) * 100, 1, False)}%）／費用÷1R の平均 {f(r['cost_mean'], 3)}",
              f"- 買い {r['long']['n']} 件 {f(r['long']['mean'])}／売り {r['short']['n']} 件 {f(r['short']['mean'])}",
              "- 資産の種類：" + "／".join(f"{TL.CLASS_JA.get(k, k)} {v['n']} 件 {f(v['mean'])}" for k, v in r["by_class"].items()),
              f"- 約定した足でも利確を数えた場合（上限）：{f(r['tp_in_fill_mean'])}",
              "", "| 入口（トレンド × オシレーター） | 件数 | 平均R |", "|---|---:|---:|"]
        L += [f"| {CL.TREND_NAMES[x['t']]} × {CL.OSCS[x['osc']]} | {x['n']} | {f(x['mean'])} |" for x in r["by_entry"]]
        if r.get("missing"):
            L.append(f"\n- 値段を取れなかった銘柄：{', '.join(r['missing'])}")
        L.append("")
    L += ["- 日足・4時間足の費用はサイトの仮の値（実スプレッドではない）。足の中の順番は不利な側に倒した。指値は線でそのまま約定するとみなした", "",
          "---", "", "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。"]
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    if a.check:
        print(json.dumps(check(), ensure_ascii=False, indent=1, default=str))
        return 0
    res = {"generated_at": dt.datetime.now(P.JST).isoformat(timespec="minutes"), "prereg_file": P.PREREG,
           "prereg_sha256": P.prereg_sha256(), "section_sha256": J.section_sha256(head=SECTION),
           "kind": "backtest", "unit": "R",
           "titles": {"1d": "損切りの線まで待って同じ向きに指値で入る（日足・監視18銘柄・入口60・費用後・過去のデータ・1回だけ）",
                      "4h": "損切りの線まで待って同じ向きに指値で入る（4時間足・監視18銘柄・入口60・費用後・過去730日・1回だけ）"}}
    res["results"] = run()
    res["verdicts"] = verdicts_of(res["results"], dt.datetime.now(P.JST).date().isoformat())
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1, default=str)
    md = render_md(res)
    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
