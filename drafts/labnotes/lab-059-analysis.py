#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
#059 lab analysis: もみあい相場×ショート 前向きN=141 CI上限ゼロ接触
題材: trend=中立・もみあい × dir=short
前向き登録日: 2026-06-17
前期記録: #012(IS 67.3%), #019(IS 50.7%), #029(FWD54件崩落)
今回の焦点: 前向きN=141でRCI[−0.447, +0.003]に達した事実の構造的解析
"""
import json, sys, os, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from signal_lab_sweep import load_log, r_of
from signal_lab_verify import closed, win, match, wilson

REGISTERED_AT = "2026-06-17"

def r_stats(rows):
    """avgR と日付クラスタ補正CI"""
    groups = {}
    for d in rows:
        r = r_of(d)
        if r is not None:
            day = (d.get("fired_at") or "")[:10]
            groups.setdefault(day, []).append(r)
    Rs = [x for g in groups.values() for x in g]
    nR, G = len(Rs), len(groups)
    meanR = sum(Rs) / nR if nR else 0.0
    if G >= 2:
        seR = (sum((sum(g) - len(g) * meanR) ** 2 for g in groups.values()) * G / (G - 1)) ** 0.5 / nR
    else:
        seR = 0.0
    rci_lo = round(meanR - 1.96 * seR, 3)
    rci_hi = round(meanR + 1.96 * seR, 3)
    return round(meanR, 3), rci_lo, rci_hi, nR

def analyze(rows, label):
    n = len(rows)
    k = sum(1 for d in rows if win(d))
    pct = k/n*100 if n else 0
    wci_lo, wci_hi = wilson(k, n)
    avgR, rci_lo, rci_hi, nR = r_stats(rows)
    print(f"  {label}: k={k} n={n} ({pct:.1f}%) Wilson CI[{wci_lo:.1f}%,{wci_hi:.1f}%]"
          f"  E(R)={avgR:+.3f} RCI[{rci_lo:+.3f},{rci_hi:+.3f}]")
    return {"k": k, "n": n, "pct": round(pct,1), "wci_lo": round(wci_lo,1), "wci_hi": round(wci_hi,1),
            "avgR": avgR, "rci_lo": rci_lo, "rci_hi": rci_hi}

data = load_log()
# filter: trend=中立・もみあい × direction=short × closed
base_f = {"trend": "中立・もみあい", "direction": "short"}

all_rows = [d for d in data if closed(d) and match(d, base_f)]
is_rows  = [d for d in all_rows if (d.get("fired_at") or "")[:10] < REGISTERED_AT]
fwd_rows = [d for d in all_rows if (d.get("fired_at") or "")[:10] >= REGISTERED_AT]

# half split of forward
n_fwd = len(fwd_rows)
fwd_sorted = sorted(fwd_rows, key=lambda d: (d.get("fired_at") or ""))
fwd_h1 = fwd_sorted[:n_fwd//2]
fwd_h2 = fwd_sorted[n_fwd//2:]

print("=" * 70)
print("#059 もみあい×ショート 前向きN=141 CI上限ゼロ接触 分析")
print("=" * 70)
print()
print("【1. 全期間・IS・FWD概況】")
analyze(all_rows, "全期間(IS+FWD)")
analyze(is_rows,  "IS(登録前)")
analyze(fwd_rows, "FWD(全前向き)")
analyze(fwd_h1,   f"FWD前半 N={len(fwd_h1)}")
analyze(fwd_h2,   f"FWD後半 N={len(fwd_h2)}")

# primary_signal breakdown
print()
print("【2. シグナル別 (FWD)】")
signals = {}
for d in fwd_rows:
    s = d.get("primary_signal", "unknown")
    signals.setdefault(s, []).append(d)
for s, rows in sorted(signals.items(), key=lambda x: -len(x[1])):
    analyze(rows, f"  signal={s}")

print()
print("【3. グループ別 (FWD)】")
GROUPS_MAP = {
    "index": {"NKD=F","ES=F","NQ=F","YM=F","^FTSE"},
    "jpy_fx": {"USDJPY=X","EURJPY=X","GBPJPY=X","AUDJPY=X"},
    "other_fx": {"EURUSD=X","GBPUSD=X","AUDUSD=X","EURAUD=X","GBPAUD=X"},
    "metal": {"GC=F","SI=F"},
    "btc": {"BTC-USD"},
    "oil": {"CL=F"},
}
for grp, tickers in GROUPS_MAP.items():
    grp_rows = [d for d in fwd_rows if d.get("ticker") in tickers]
    if grp_rows:
        analyze(grp_rows, f"  group={grp}")

print()
print("【4. signal=macd_dead 詳細(FWD)】")
md_fwd = [d for d in fwd_rows if d.get("primary_signal") == "macd_dead"]
lb_fwd = [d for d in fwd_rows if d.get("primary_signal") == "low_break"]
analyze(md_fwd, "  macd_dead(FWD)")
analyze(lb_fwd, "  low_break(FWD)")
# macd_dead IS
md_is = [d for d in is_rows if d.get("primary_signal") == "macd_dead"]
lb_is = [d for d in is_rows if d.get("primary_signal") == "low_break"]
analyze(md_is, "  macd_dead(IS)")
analyze(lb_is, "  low_break(IS)")

print()
print("【5. IS に比べてFWD後半はmacd_deadが何件?】")
print(f"  FWD後半 macd_dead: {sum(1 for d in fwd_h2 if d.get('primary_signal')=='macd_dead')}/{len(fwd_h2)}")
print(f"  FWD後半 low_break: {sum(1 for d in fwd_h2 if d.get('primary_signal')=='low_break')}/{len(fwd_h2)}")

print()
print("【6. もみあい×ロング対照群(FWD)】")
long_f = {"trend": "中立・もみあい", "direction": "long"}
long_fwd = [d for d in data if closed(d) and match(d, long_f) and
            (d.get("fired_at") or "")[:10] >= REGISTERED_AT]
analyze(long_fwd, "  もみあい×ロング(FWD)")

print()
print("【7. 全期間 vs #012/#019/#029 推移サマリー】")
# IS記録
is_check = [d for d in all_rows if (d.get("fired_at") or "")[:10] < "2026-06-17"]
fwd_pre_029 = [d for d in fwd_rows if (d.get("fired_at") or "")[:10] < "2026-07-04"]
fwd_post_029 = [d for d in fwd_rows if (d.get("fired_at") or "")[:10] >= "2026-07-04"]
print(f"  IS(〜06-17): k={sum(win(d) for d in is_check)} n={len(is_check)}")
print(f"  FWD前期(06-17〜07-04, #029時点): k={sum(win(d) for d in fwd_pre_029)} n={len(fwd_pre_029)}")
print(f"  FWD後期(07-04〜今日): k={sum(win(d) for d in fwd_post_029)} n={len(fwd_post_029)}")

print()
print("【8. CI上限ゼロ到達に必要な推定件数】")
# rci_hi = avgR + 1.96 * seR/sqrt(N) ≈ 0 → N = (1.96 * sd / avgR)^2
# Currently: avgR = -0.222, seR cluster-corrected ≈ se such that 0.222/1.96/se ≈ 1
# rci_hi = meanR + 1.96*seR = +0.003 currently (N=141)
# If seR shrinks proportionally to sqrt: seR_new = seR_current * sqrt(141/N)
# rci_hi_new = -0.222 + 1.96 * seR_current * sqrt(141/N)
# Set to 0: seR_current = (0.003 + 0.222) / 1.96 = 0.2250/1.96 = 0.1148
seR_est = (0.003 + 0.222) / 1.96
print(f"  現在 avgR=-0.222, seR≈{seR_est:.4f}")
for target_hi in [-0.005, 0.000, 0.005]:
    # rci_hi = -0.222 + 1.96*seR*sqrt(141/N) = target_hi
    # seR*sqrt(141/N) = (target_hi + 0.222)/1.96
    val = (target_hi + 0.222) / 1.96
    N_needed = int(141 * (seR_est / val) ** 2) + 1
    print(f"  CI上限={target_hi:+.3f}ゼロ到達に必要な追加N: {N_needed}件（追加{max(0,N_needed-141)}件）")

print()
print("【9. 全件ticker一覧(FWD参考)】")
tickers = {}
for d in fwd_rows:
    t = d.get("ticker","?")
    tickers[t] = tickers.get(t,0)+1
for t,c in sorted(tickers.items(), key=lambda x: -x[1]):
    print(f"  {t}: {c}件")
