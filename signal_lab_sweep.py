# -*- coding: utf-8 -*-
"""
signal_lab_sweep.py — 仮説グリッドを「エンジンで全数検証」する発見スイープ。

設計（CLAUDE.md / SESSION_HANDOFF.md の方針）:
- LLM を使わず、signals-log.json を決定論で全数検証する（好きなだけ・ほぼ無料で回せる）。
- 検証ロジックは固定オラクル signal_lab_verify.py の部品をそのまま import（単一ソース＝捏造不能）。
- 多重検定（同じデータに多数の仮説を当てると偶然の“勝てそう”が必ず出る＝p-hacking）対策として
  Benjamini-Hochberg の FDR 補正を入れる。最小N で小サンプルの罠も除外。
- ここで「FDR を生き残った候補」を前向きトラッカー(signal_lab_tracker.py)に登録する流れ。
  ＝ 発見(in-sample)は仮説の“候補出し”、採否は前向き(out-of-sample)で判定する二段構え。

使い方:
    python signal_lab_sweep.py                 # 実データでスイープ→ランキング表示
    python signal_lab_sweep.py --json out.json # 候補を JSON 出力（トラッカー登録用）
    python signal_lab_sweep.py --min-n 15      # 最小N変更（既定20）
    python signal_lab_sweep.py --alpha 0.10    # FDR の α（既定0.10）

終了コード: 0 正常 / 2 引数エラー。
"""
import argparse
import itertools
import json
import os
import sys
from math import comb, erf, sqrt

# 固定オラクルの部品を再利用（編集しない・import のみ）
from signal_lab_verify import (
    GROUPS, REV, ALLOWED_FILTER_KEYS, wilson, closed, win, match, compute, get_trend,
)

ROOT = os.path.dirname(os.path.abspath(__file__))
BREAKEVEN = 0.43  # R:R 1:1.33（TP1=2.0ATR / SL=1.5ATR）の損益分岐勝率
TFS = ("1h", "4h", "1d")
DIRECTIONS = ("long", "short")
TRENDS = ("上昇", "下降", "中立・もみあい")


def load_log(path=None):
    if path:
        p = path if os.path.isabs(path) else os.path.join(ROOT, path)
    else:
        p = os.path.join(ROOT, "signals-log.json")
        if not os.path.exists(p):
            alt = os.path.join(ROOT, "_signals_live.json")
            if os.path.exists(alt):
                p = alt
    return json.load(open(p, encoding="utf-8-sig"))


def binom_p_ge(k, n, p):
    """P(X>=k) ／ X~Binomial(n,p)。n は最大でも数百なので厳密計算で十分。"""
    return sum(comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1))


def binom_p_le(k, n, p):
    """P(X<=k)。"""
    return sum(comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(0, k + 1))


def _norm_cdf(x):
    return 0.5 * (1 + erf(x / sqrt(2)))


def two_sided_p(k, n, p0=BREAKEVEN):
    """損益分岐 p0 と有意に異なるかの両側 p 値（方向は別途 pct で判定）。
    n≤1000 は厳密二項、それ超は正規近似（厳密だと comb が桁あふれ＋近似で十分）。"""
    if n <= 1000:
        up = binom_p_ge(k, n, p0)
        down = binom_p_le(k, n, p0)
        return min(1.0, 2.0 * min(up, down))
    se = sqrt(p0 * (1 - p0) / n)
    if se == 0:
        return 1.0
    z = (k / n - p0) / se
    return max(0.0, min(1.0, 2.0 * (1 - _norm_cdf(abs(z)))))


def signal_types(data):
    s = set()
    for d in data:
        ps = d.get("primary_signal")
        if ps:
            s.add(ps)
    return sorted(s)


def build_grid(data):
    """検証する仮説（filter dict）を列挙。組合せ爆発を避けるため厳選した1次元＋意味のある2次元。"""
    sigs = signal_types(data)
    grid = []

    def add(label, f):
        grid.append((label, f))

    # --- 1次元 ---
    for g in list(GROUPS.keys()) + ["all"]:
        add(f"group={g}", {"group": g})
    for tf in TFS:
        add(f"tf={tf}", {"tf": tf})
    for di in DIRECTIONS:
        add(f"dir={di}", {"direction": di})
    for tr in TRENDS:
        add(f"trend={tr}", {"trend": tr})
    add("reversalL（逆張り買い）", {"reversal_long": True})
    add("blocked=True（runway阻害）", {"blocked": True})
    add("blocked=False", {"blocked": False})
    for s in sigs:
        add(f"signal={s}", {"signal": s})
    # 選別タグ（エンジン既存・elite/good/neutral/avoid が期待値で分かれるか）
    for tier in ("elite", "good", "neutral", "avoid"):
        add(f"tier={tier}", {"tier": tier})
    for tier in ("elite", "good"):
        add(f"tier={tier}×dir=long", {"tier": tier, "direction": "long"})

    # --- 2次元（意味のある組合せのみ） ---
    for g in GROUPS.keys():
        add(f"group={g}×reversalL", {"group": g, "reversal_long": True})
    for di in DIRECTIONS:
        for g in GROUPS.keys():
            add(f"group={g}×dir={di}", {"group": g, "direction": di})
    for tr in TRENDS:  # 押し目買い vs 落ちるナイフ（本命）
        add(f"trend={tr}×reversalL", {"trend": tr, "reversal_long": True})
    for tf in TFS:
        add(f"tf={tf}×reversalL", {"tf": tf, "reversal_long": True})
    for tr in TRENDS:
        for di in DIRECTIONS:
            add(f"trend={tr}×dir={di}", {"trend": tr, "direction": di})
    for di in DIRECTIONS:
        add(f"blocked=True×dir={di}", {"blocked": True, "direction": di})
        add(f"blocked=False×dir={di}", {"blocked": False, "direction": di})
    for tf in TFS:
        for di in DIRECTIONS:
            add(f"tf={tf}×dir={di}", {"tf": tf, "direction": di})

    # filter の重複（同一 dict）を除去
    seen, uniq = set(), []
    for label, f in grid:
        key = tuple(sorted(f.items()))
        if key in seen:
            continue
        seen.add(key)
        uniq.append((label, f))
    return uniq


def r_of(rec):
    """outcome → 実現Rマルチプル（SL=1.5ATR=-1R / TP1=2.0ATR=+1.33R / TP2=3.0ATR=+2R）。"""
    return {"tp2": 2.0, "tp1": 4.0 / 3.0, "sl": -1.0}.get(rec.get("outcome"))


def _mean_std(xs):
    n = len(xs)
    if n == 0:
        return 0.0, 0.0
    m = sum(xs) / n
    if n < 2:
        return m, 0.0
    return m, (sum((x - m) ** 2 for x in xs) / (n - 1)) ** 0.5


def sweep(data, min_n, alpha):
    """各仮説の勝率＋【期待値(平均R)】を集計し、「期待値≠0」でBH-FDR判定（＝本当に黒字か）。"""
    rows = []
    for label, f in build_grid(data):
        matched = [d for d in data if closed(d) and match(d, f)]
        n = len(matched)
        if n < min_n:
            continue
        k = sum(1 for d in matched if win(d))
        pct = 100 * k / n
        lo, hi = wilson(k, n)
        Rs = [r_of(d) for d in matched if r_of(d) is not None]
        meanR, sdR = _mean_std(Rs)
        seR = sdR / (len(Rs) ** 0.5) if len(Rs) > 1 else 0.0
        if seR > 0:
            pR = max(0.0, min(1.0, 2 * (1 - _norm_cdf(abs(meanR / seR)))))  # 期待値≠0 の両側p
        else:
            pR = 1.0
        rows.append({
            "label": label, "filter": f, "k": k, "n": n, "pct": round(pct, 1),
            "ci_lo": round(lo, 1), "ci_hi": round(hi, 1),
            "avgR": round(meanR, 3), "rci_lo": round(meanR - 1.96 * seR, 3),
            "rci_hi": round(meanR + 1.96 * seR, 3), "p": pR, "profitable": meanR > 0,
        })

    # Benjamini-Hochberg FDR（期待値検定の p に対して）
    m = len(rows)
    ordered = sorted(range(m), key=lambda i: rows[i]["p"])
    qvals = [0.0] * m
    prev = 1.0
    for rank in range(m, 0, -1):
        i = ordered[rank - 1]
        prev = min(prev, rows[i]["p"] * m / rank)
        qvals[i] = min(1.0, prev)
    thresh_rank = 0
    for rank in range(1, m + 1):
        if rows[ordered[rank - 1]]["p"] <= (rank / m) * alpha:
            thresh_rank = rank
    reject = set(ordered[:thresh_rank])
    for i, r in enumerate(rows):
        r["q"] = round(qvals[i], 4)
        r["fdr_pass"] = i in reject
    return rows, m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-n", type=int, default=20, help="最小サンプル数（既定20）")
    ap.add_argument("--alpha", type=float, default=0.10, help="FDRのα（既定0.10）")
    ap.add_argument("--json", help="候補をJSON出力するパス（トラッカー登録用）")
    ap.add_argument("--log", help="検証する signals-log のパス（既定=signals-log.json。バックテストは signals-log-backtest.json）")
    args = ap.parse_args()

    data = load_log(args.log)
    resolved = [d for d in data if closed(d)]
    rows, m = sweep(data, args.min_n, args.alpha)

    print("=== signal-lab スイープ（期待値R）===")
    print(f"signals-log {len(data)}件（決済済 {len(resolved)}件） / 検証仮説 {m}本（N≥{args.min_n}） / "
          f"R: SL=-1.0 / TP1=+1.33 / TP2=+2.0 / FDR α={args.alpha}（期待値≠0を検定）")
    print(f"{'仮説':<34}{'k/n':>9}{'勝率':>7}{'  平均R':>9}{'  R 95%CI':>18}{'  q':>8}  判定")
    print("-" * 110)
    rows.sort(key=lambda r: (not r["fdr_pass"], r["q"], -r["avgR"]))
    for r in rows:
        flag = ("✅FDR" if r["fdr_pass"] else "  ") + ("黒字" if r["profitable"] else "赤字")
        rci = f"[{r['rci_lo']:+.2f}~{r['rci_hi']:+.2f}]"
        print(f"{r['label']:<34}{str(r['k'])+'/'+str(r['n']):>9}{r['pct']:>6.1f}%{r['avgR']:>+9.3f}{rci:>18}{r['q']:>8.3f}  {flag}")

    winners = [r for r in rows if r["fdr_pass"] and r["profitable"]]
    losers = [r for r in rows if r["fdr_pass"] and not r["profitable"]]
    print("-" * 110)
    print(f"✅黒字エッジ（期待値プラスが有意・FDR通過）: {len(winners)}本"
          + ("＝" + "、".join(f"{r['label']}(R{r['avgR']:+.2f})" for r in winners) if winners else "（なし）"))
    print(f"⛔赤字（期待値マイナスが有意・回避）: {len(losers)}本"
          + ("＝" + "、".join(f"{r['label']}(R{r['avgR']:+.2f})" for r in losers) if losers else "（なし）"))
    print("※ in-sample の候補出し。採否はライブ前向きトラッカーで out-of-sample 確認。")

    if args.json:
        out = {"min_n": args.min_n, "alpha": args.alpha,
               "candidates": [r for r in rows if r["fdr_pass"]]}  # winners/losers両方＝tracker登録用
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print(f"→ FDR通過 {len(out['candidates'])}本を {args.json} に出力（トラッカー登録用）。")

    if args.json:
        out = {"min_n": args.min_n, "alpha": args.alpha, "breakeven_pct": BREAKEVEN * 100,
               "candidates": [r for r in rows if r["fdr_pass"]]}
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print(f"→ FDR通過候補を {args.json} に出力（トラッカー登録用）")


if __name__ == "__main__":
    main()
