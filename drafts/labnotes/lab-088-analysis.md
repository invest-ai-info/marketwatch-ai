# Lab-088 Analysis Notes — rsi_oversold_bounce 時間足二極化 継続追跡

**Date**: 2026-09-03  
**Routine**: signal-lab-daily  
**REG_DATE**: 2026-06-16 (IS/FWD境界)  
**Hypothesis priority**: ②大きく動いた仮説（FWD N=276, tracker CI[+0.04, +0.46]）  
**Previous episodes**: #069, #074, #082

---

## Python Analysis Script

```python
import json, math

with open("signals-log.json") as f:
    data = json.load(f)
all_sigs = data if isinstance(data, list) else list(data.values())

GROUPS = {
    "metal":    {"GC=F","SI=F"},
    "oil":      {"CL=F"},
    "index":    {"NKD=F","ES=F","NQ=F","YM=F","^FTSE"},
    "btc":      {"BTC-USD"},
    "jpy_fx":   {"USDJPY=X","EURJPY=X","GBPJPY=X","AUDJPY=X"},
    "other_fx": {"EURUSD=X","GBPUSD=X","AUDUSD=X","EURAUD=X","GBPAUD=X"},
}

def get_group(ticker):
    for g, ts in GROUPS.items():
        if ticker in ts: return g
    return None

def get_trend(d):
    ta = d.get("trend_alignment")
    if isinstance(ta, dict) and ta.get("higher_tf_trend"):
        return ta["higher_tf_trend"]
    return None

def get_fire_date(d):
    fa = d.get("fired_at","")
    return fa[:10] if fa else ""

def closed_f(d): return d.get("outcome") in ("tp1","tp2","sl")
def win_f(d): return d.get("outcome") in ("tp1","tp2")
def get_r(d):
    o = d.get("outcome")
    if o == "tp2": return 2.0
    if o == "tp1": return 1.333
    if o == "sl":  return -1.0
    return 0.0

def wilson_ci(k, n, z=1.96):
    if n == 0: return (0.0, 0.0)
    p = k / n
    denom = 1 + z*z/n
    center = (p + z*z/(2*n)) / denom
    margin = (z * math.sqrt(p*(1-p)/n + z*z/(4*n*n))) / denom
    return (max(0, center - margin), min(1, center + margin))

def r_ci(rs, z=1.96):
    n = len(rs)
    if n < 2: return (None, None)
    mu = sum(rs) / n
    var = sum((r - mu)**2 for r in rs) / (n - 1)
    se = math.sqrt(var / n)
    return (mu - z*se, mu + z*se)

def analyze(sigs, label):
    closed = [d for d in sigs if closed_f(d)]
    wins = [d for d in closed if win_f(d)]
    n, k = len(closed), len(wins)
    wr = k/n if n > 0 else 0
    lo, hi = wilson_ci(k, n)
    rs = [get_r(d) for d in closed]
    er = sum(rs)/len(rs) if rs else 0
    rlo, rhi = r_ci(rs)
    print(f"{label}: N={n}, k={k}, WR={wr*100:.1f}% CI=[{lo*100:.1f}%,{hi*100:.1f}%], E(R)={er:+.3f} RCI=[{rlo:+.3f},{rhi:+.3f}]" if rlo else f"{label}: N={n}, k={k}, WR={wr*100:.1f}% CI=[{lo*100:.1f}%,{hi*100:.1f}%], E(R)={er:+.3f}")
    return n, k, wr, lo, hi, er, rlo, rhi

REG_DATE = "2026-06-16"
bounce = [d for d in all_sigs if d.get("primary_signal") == "rsi_oversold_bounce"]
print(f"Total rsi_oversold_bounce signals: {len(bounce)}")

is_sigs  = [d for d in bounce if get_fire_date(d) < REG_DATE]
fwd_sigs = [d for d in bounce if get_fire_date(d) >= REG_DATE]

print("=== IS ===")
analyze(is_sigs, "IS全体")

print("\n=== FWD ===")
analyze(fwd_sigs, "FWD全体")

for tf in ["4h", "1h"]:
    sub = [d for d in fwd_sigs if d.get("timeframe") == tf]
    analyze(sub, f"FWD {tf}")

print()
for g in ["jpy_fx", "metal", "index", "other_fx"]:
    sub = [d for d in fwd_sigs if get_group(d.get("ticker","")) == g]
    if sub: analyze(sub, f"FWD group={g}")

print()
for tr in ["上昇", "下降", "中立・もみあい"]:
    sub = [d for d in fwd_sigs if get_trend(d) == tr]
    analyze(sub, f"FWD trend={tr}")

print("\n=== 4H breakdown ===")
fwd_4h = [d for d in fwd_sigs if d.get("timeframe") == "4h"]
for g in ["jpy_fx", "metal", "index", "other_fx"]:
    sub = [d for d in fwd_4h if get_group(d.get("ticker","")) == g]
    if sub: analyze(sub, f"4H group={g}")
for tr in ["上昇", "下降", "中立・もみあい"]:
    sub = [d for d in fwd_4h if get_trend(d) == tr]
    if sub: analyze(sub, f"4H trend={tr}")

print("\n=== FWD 期間別 ===")
p1 = [d for d in fwd_sigs if "2026-06-17" <= get_fire_date(d) <= "2026-07-08"]
p2 = [d for d in fwd_sigs if "2026-07-08" <  get_fire_date(d) <= "2026-08-14"]
p3 = [d for d in fwd_sigs if "2026-08-14" <  get_fire_date(d) <= "2026-09-02"]
analyze(p1, "FWD前期(06-17~07-08)")
analyze(p2, "FWD中期(07-08~08-14)")
analyze(p3, "FWD後期(08-14~09-02)")

print("\n=== 全期間(IS+FWD) ===")
analyze(bounce, "全期間全足")
analyze([d for d in bounce if d.get("timeframe") == "4h"], "全期間 4H")
analyze([d for d in bounce if d.get("timeframe") == "1h"], "全期間 1H")
```

---

## Raw Output

```
Total rsi_oversold_bounce signals: 409

=== IS ===
IS全体: N=133, k=52, WR=39.1% CI=[31.2%,47.6%], E(R)=-0.088

=== FWD ===
FWD全体: N=276, k=148, WR=53.6% CI=[47.7%,59.4%], E(R)=+0.251 RCI=[+0.114,+0.389]
FWD 4h: N=81, k=53, WR=65.4% CI=[54.6%,74.9%], E(R)=+0.527 RCI=[+0.283,+0.770]
FWD 1h: N=183, k=85, WR=46.4% CI=[39.4%,53.7%], E(R)=+0.084 RCI=[-0.085,+0.253]
FWD group=jpy_fx: N=48, k=32, WR=66.7% CI=[52.5%,78.3%], E(R)=+0.555 RCI=[+0.241,+0.870]
FWD group=metal: N=40, k=24, WR=60.0% CI=[44.7%,73.6%], E(R)=+0.356 RCI=[+0.047,+0.665]
FWD group=index: N=63, k=36, WR=57.1% CI=[44.7%,68.7%], E(R)=+0.245 RCI=[+0.001,+0.489]
FWD group=other_fx: N=52, k=26, WR=50.0% CI=[36.8%,63.2%], E(R)=+0.126 RCI=[-0.149,+0.401]
FWD trend=上昇: N=70, k=46, WR=65.7% CI=[54.0%,75.8%], E(R)=+0.533 RCI=[+0.272,+0.794]
FWD trend=下降: N=108, k=47, WR=43.5% CI=[34.5%,52.9%], E(R)=+0.015
FWD trend=中立・もみあい: N=98, k=55, WR=56.1% CI=[46.3%,65.5%], E(R)=+0.309 RCI=[+0.079,+0.540]

=== 4H breakdown ===
4H group=jpy_fx: N=17, k=16, WR=94.1% CI=[73.0%,99.0%], E(R)=+1.196 RCI=[+0.927,+1.465]
4H group=index: N=20, k=13, WR=65.0% CI=[43.3%,81.9%], E(R)=+0.435 RCI=[+0.030,+0.840]
4H trend=上昇: N=27, k=19, WR=70.4% CI=[51.3%,84.2%], E(R)=+0.642 RCI=[+0.232,+1.051]
4H trend=中立・もみあい: N=22, k=17, WR=77.3% CI=[56.6%,89.9%], E(R)=+0.803 RCI=[+0.385,+1.221]

=== FWD 期間別 ===
FWD前期(06-17~07-08): N=92, k=45, WR=48.9% CI=[38.8%,59.2%], E(R)=+0.141 RCI=[-0.098,+0.381]
FWD中期(07-08~08-14): N=92, k=57, WR=62.0% CI=[51.6%,71.4%], E(R)=+0.445 RCI=[+0.213,+0.678]
FWD後期(08-14~09-02): N=92, k=46, WR=50.0% CI=[39.8%,60.2%], E(R)=+0.167 RCI=[-0.073,+0.406]

=== 全期間(IS+FWD) ===
全期間全足: N=409, k=200, WR=48.9% CI=[44.1%,53.7%], E(R)=+0.141 RCI=[+0.028,+0.254]
全期間 4H: N=130, k=72, WR=55.4% CI=[46.8%,63.7%], E(R)=+0.292 RCI=[+0.092,+0.492]
全期間 1H: N=264, k=118, WR=44.7% CI=[38.8%,50.7%], E(R)=+0.043 RCI=[-0.097,+0.183]
```

---

## Key Findings

1. **IS → FWD 逆転**: IS 39.1% (k=52/N=133, E(R)=-0.088) → FWD 53.6% (k=148/N=276, E(R)=+0.251)。信号が登録後に改善している。
2. **時間足二極化**: FWD 4H=65.4% vs FWD 1H=46.4%。19ポイント差がCI非重複（4H CI下限54.6% > 1H CI上限53.7%）。
3. **グループ最強**: FWD jpy_fx=66.7%、特に4H jpy_fx=94.1%（N=17, CI=[73%,99%]）はN小に注意が必要だが極端に高い。
4. **トレンドフィルタ**: FWD 上昇トレンド=65.7% vs 下降トレンド=43.5%。逆張り買いなのに上昇トレンドで強い（モメンタムの一時調整を捉えている）。
5. **期間別変動**: 中期(07-08~08-14)が62.0%と突出し、前期・後期は約50%。熱いフェーズと冷えたフェーズが混在。
6. **時間足差は全期間でも持続**: 全期間4H=55.4% CI=[46.8%,63.7%] vs 全期間1H=44.7% CI=[38.8%,50.7%]。

## Claims Verification Cross-check

| Label | k | n | WR |
|---|---|---|---|
| IS全体 | 52 | 133 | 39.1% |
| FWD全体 | 148 | 276 | 53.6% |
| FWD 4H | 53 | 81 | 65.4% |
| FWD 1H | 85 | 183 | 46.4% |
| FWD jpy_fx | 32 | 48 | 66.7% |
| FWD trend=上昇 | 46 | 70 | 65.7% |
| FWD trend=下降 | 47 | 108 | 43.5% |
| 全期間 4H | 72 | 130 | 55.4% |
| 全期間 1H | 118 | 264 | 44.7% |
