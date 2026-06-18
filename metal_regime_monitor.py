# -*- coding: utf-8 -*-
"""metal_regime_monitor.py — 金属(等)ロングの「レジーム状態」を前向きに監視する。

背景（2026-06-18 の検証 / memory: project_signal_edge_research）:
- group=metal×long は 20年バックテストで +0.296R（最良級）だが、直近ライブで −0.549R（最悪）。
- これはトレンド条件付けでは説明できない真の非定常（20年BTは下降トレンドでも +0.205R＝平均回帰が効いた）。
- 結論：一律 veto はしない（20年の最良エッジを殺す誤り）。代わりに「正常化したか」を前向きに監視し、
  確信・サイズの上げ下げ判断の材料にする。

このツールがやること:
- 直近 N 件（既定30）の実現R・勝率を集計し、損益分岐(43%/R=0) と 20年BTベースライン(+0.296R) に照らして
  🔴機能不全 / 🟡移行期 / 🟢正常化 のいずれかを返す（判定基準は下記 constants に先に宣言＝後から動かさない）。
- 直近ウィンドウを前半/後半に割り、改善中か悪化中かの“向き”も出す。
- 銘柄別(GC/SI)・トレンド別の内訳も出す（押し目買い＝下降での逆張りが鬼門なので可視化）。

設計上の約束:
- 検証ロジックは固定オラクル signal_lab_verify / signal_lab_sweep の部品をそのまま import（単一ソース＝捏造不能）。
- 監視・記録“専用”。エンジン・発火条件・メール配信・ロットには一切触れない。
- これはラグのある「現状把握」であって予測ではない。少サンプルでは判定を保留する。

使い方:
    python metal_regime_monitor.py                          # 金属×ロングを既定で監視（signals-log.json）
    python metal_regime_monitor.py --log _signals_live.json # 取得済みライブを指定
    python metal_regime_monitor.py --group btc --direction long --window 25
    python metal_regime_monitor.py --json metal-regime.json # 状態をJSON出力（routine/Actionsで利用可）

終了コード: 0 正常 / 2 引数エラー。
"""
import argparse
import json
import os

# 固定オラクルの部品（編集しない・import のみ＝単一ソース）
from signal_lab_verify import closed, win, match, wilson, get_trend
from signal_lab_sweep import r_of, load_log

ROOT = os.path.dirname(os.path.abspath(__file__))

# ── 判定基準（先に宣言。後から都合よく動かさない） ──
WINDOW = 30           # 直近この件数で「いまのレジーム」を見る
MIN_JUDGE_N = 10      # これ未満は判定保留（少サンプルの罠を避ける）
R_GREEN = 0.10        # 正常化と見なす平均Rの下限
R_RED = -0.10         # 機能不全と見なす平均Rの上限
BREAKEVEN_PCT = 43.0  # R:R 1:1.33 の損益分岐勝率


def stats(recs):
    """勝率・平均R・Wilson信頼区間(勝率)・平均Rの95%CI を返す。"""
    n = len(recs)
    k = sum(1 for d in recs if win(d))
    Rs = [r_of(d) for d in recs if r_of(d) is not None]
    if Rs:
        m = sum(Rs) / len(Rs)
        if len(Rs) > 1:
            sd = (sum((x - m) ** 2 for x in Rs) / (len(Rs) - 1)) ** 0.5
            se = sd / len(Rs) ** 0.5
        else:
            se = 0.0
    else:
        m = se = 0.0
    wlo, whi = wilson(k, n) if n else (0.0, 0.0)
    return {
        "n": n, "k": k, "pct": round(100 * k / n, 1) if n else 0.0,
        "avgR": round(m, 3), "rci_lo": round(m - 1.96 * se, 3), "rci_hi": round(m + 1.96 * se, 3),
        "win_ci_lo": round(wlo, 1), "win_ci_hi": round(whi, 1),
    }


def classify(win_pct, avg_r, n):
    """先に宣言した基準で 🔴/🟡/🟢/保留 を返す。"""
    if n < MIN_JUDGE_N:
        return "⏳判定保留", f"サンプル不足（{n}件 < {MIN_JUDGE_N}件）"
    if avg_r >= R_GREEN and win_pct >= BREAKEVEN_PCT:
        return "🟢正常化", f"平均R {avg_r:+.3f}≥{R_GREEN:+.2f} かつ 勝率 {win_pct:.1f}%≥{BREAKEVEN_PCT:.0f}%"
    if avg_r <= R_RED and win_pct < BREAKEVEN_PCT:
        return "🔴機能不全", f"平均R {avg_r:+.3f}≤{R_RED:+.2f} かつ 勝率 {win_pct:.1f}%<{BREAKEVEN_PCT:.0f}%"
    return "🟡移行期", f"平均R {avg_r:+.3f} / 勝率 {win_pct:.1f}%（損益分岐近辺・まだ確信できない）"


# 20年BTのベースライン（正常時の姿）。バックテストファイルが無い環境（Actions 等）用フォールバック
# ＝2026-06-18 の signal_lab_sweep 検証値（signals-log-backtest.json があればそちらを優先）。
BASELINE_FALLBACK = {
    ("metal", "long"): {"n": 1557, "pct": 52.9, "avgR": 0.296},
    ("btc", "long"): {"n": 589, "pct": 52.1, "avgR": 0.317},
    ("index", "long"): {"n": 3699, "pct": 44.7, "avgR": 0.053},
}


def baseline_for(flt):
    """20年バックテスト（あれば）から同フィルタのベースラインを計算。無ければフォールバック定数。"""
    p = os.path.join(ROOT, "signals-log-backtest.json")
    if os.path.exists(p):
        data = json.load(open(p, encoding="utf-8-sig"))
        recs = [d for d in data if closed(d) and match(d, flt)]
        if recs:
            return stats(recs)
    return BASELINE_FALLBACK.get((flt.get("group"), flt.get("direction")))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", help="signals-log のパス（既定 signals-log.json）")
    ap.add_argument("--group", default="metal", help="監視グループ（既定 metal）")
    ap.add_argument("--direction", default="long", help="long/short（既定 long）")
    ap.add_argument("--window", type=int, default=WINDOW, help=f"直近の判定件数（既定 {WINDOW}）")
    ap.add_argument("--json", help="状態をJSON出力するパス")
    args = ap.parse_args()

    flt = {"group": args.group, "direction": args.direction}
    data = load_log(args.log)
    matched = [d for d in data if closed(d) and match(d, flt)]
    matched.sort(key=lambda d: str(d.get("fired_at", "")))

    full = stats(matched)
    window = matched[-args.window:]
    win_s = stats(window)
    # 向き（ウィンドウ前半 vs 後半）
    h = len(window) // 2
    first, second = stats(window[:h]), stats(window[h:])
    if first["n"] >= 3 and second["n"] >= 3:
        delta = second["avgR"] - first["avgR"]
        trend = "改善中↑" if delta > 0.10 else ("悪化中↓" if delta < -0.10 else "横ばい→")
    else:
        delta, trend = 0.0, "判定不可（少データ）"

    base = baseline_for(flt)
    status, reason = classify(win_s["pct"], win_s["avgR"], win_s["n"])

    label = f"{args.group}×{args.direction}"
    print(f"=== レジーム監視: {label} ===")
    if base:
        print(f"20年BTベースライン（正常時の姿）: n={base['n']} 勝率{base['pct']}% 平均R{base['avgR']:+.3f}")
    print(f"全期間ライブ            : n={full['n']:>3} 勝率{full['pct']:>5.1f}% 平均R{full['avgR']:+.3f} "
          f"[R95%CI {full['rci_lo']:+.2f}~{full['rci_hi']:+.2f}]")
    print(f"直近{args.window}件（判定対象）  : n={win_s['n']:>3} 勝率{win_s['pct']:>5.1f}% 平均R{win_s['avgR']:+.3f} "
          f"[R95%CI {win_s['rci_lo']:+.2f}~{win_s['rci_hi']:+.2f}] 勝率CI[{win_s['win_ci_lo']}~{win_s['win_ci_hi']}]")
    print(f"  └ 向き: 前半R{first['avgR']:+.3f} → 後半R{second['avgR']:+.3f}（{trend}）")

    # 内訳（銘柄・トレンド）
    def breakdown(key_fn, title, keys):
        print(f"-- {title} --")
        from collections import defaultdict
        b = defaultdict(list)
        for d in window:
            b[key_fn(d)].append(d)
        for kk in keys:
            if b.get(kk):
                s = stats(b[kk])
                print(f"   {str(kk):14} n={s['n']:>3} 勝率{s['pct']:>5.1f}% 平均R{s['avgR']:+.3f}")
    breakdown(lambda d: d.get("ticker"), f"直近{args.window}件 銘柄別", sorted({d.get("ticker") for d in window}))
    breakdown(get_trend, f"直近{args.window}件 トレンド別（下降＝押し目買いの鬼門）", ["上昇", "中立・もみあい", "下降", "unknown"])

    print("-" * 60)
    print(f"判定: {status}  — {reason}")
    if base:
        gap = round(base["avgR"] - win_s["avgR"], 3)
        print(f"正常化の目安: 直近平均Rが {R_GREEN:+.2f} 以上＆勝率{BREAKEVEN_PCT:.0f}%以上に回復（BT正常時は{base['avgR']:+.3f}／現状との差 {gap:+.3f}）")
    print("※ ラグのある現状把握であり予測ではない。判定はサイズ/確信の上げ下げの材料（発火・配信は不変）。")

    if args.json:
        out = {
            "filter": flt, "window": args.window, "status": status, "reason": reason,
            "window_stats": win_s, "full_stats": full, "baseline_bt": base,
            "direction_first": first, "direction_second": second, "trend": trend,
            "thresholds": {"window": WINDOW, "min_judge_n": MIN_JUDGE_N,
                           "r_green": R_GREEN, "r_red": R_RED, "breakeven_pct": BREAKEVEN_PCT},
        }
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print(f"→ 状態を {args.json} に出力。")


if __name__ == "__main__":
    main()
