# lab-075 分析メモ — ロング回避ゲート群の前向き崩壊

基準日: 2026-08-22（JST）
仮説採択理由: 優先度①（tracker 今回ステータス変化 — trend×long 2ゲート ⛔反証確定 / metal×long 降格）

---

## スイープ結果（signal_lab_sweep.py）

```
FDR通過: 1本 tf=1d×reversalL (R+0.67)
登録: 重複スキップ1本（tf=1d×reversalLは既登録）
```

## トラッカー更新（signal_lab_tracker.py update --date 2026-08-22）

ステータス変化:
- trend=中立・もみあい×dir=long: **rejected (⛔反証)** — 前向き 平均R +0.120 / N=731
- trend=下降×dir=long: **rejected (⛔反証)** — 前向き 平均R +0.164 / N=495
- group=metal×dir=long: **demoted（降格＝基準割れ2回連続）** — 前向き 平均R +0.128 / N=242

---

## 分析スクリプト（/tmp/lab075_analysis2.py）

```python
import json, math

with open("signals-log.json") as f:
    data = json.load(f)

GROUPS = {
    "metal":    {"GC=F", "SI=F"},
    "index":    {"NKD=F", "ES=F", "NQ=F", "YM=F", "^FTSE"},
    "jpy_fx":   {"USDJPY=X", "EURJPY=X", "GBPJPY=X", "AUDJPY=X"},
    "other_fx": {"EURUSD=X", "GBPUSD=X", "AUDUSD=X", "EURAUD=X", "GBPAUD=X"},
    "btc":      {"BTC-USD"},
    "oil":      {"CL=F"},
}
REV = {"rsi_oversold_bounce", "bb_lower_touch"}

def closed(d): return d.get("outcome") in ("tp1","tp2","sl")
def win(d): return d.get("outcome") in ("tp1","tp2")
def is_long(d): return "ロング" in (d.get("direction") or "")

def get_trend(d):
    ta = d.get("trend_alignment")
    if isinstance(ta, dict) and ta.get("higher_tf_trend"):
        return ta["higher_tf_trend"]
    return "unknown"

def get_group(d):
    ticker = d.get("ticker","")
    for g, tickers in GROUPS.items():
        if ticker in tickers:
            return g
    return "other"

def get_date(d):
    return (d.get("fired_at","") or "")[:10]

def pnl_r(d):
    if d.get("outcome") == "tp2": return 3.0
    if d.get("outcome") == "tp1": return 2.0
    if d.get("outcome") == "sl": return -1.5
    return None

def wilson_ci(k, n, z=1.96):
    if n == 0: return (0.0, 100.0)
    p = k / n
    den = 1 + z*z/n
    c = (p + z*z/(2*n)) / den
    pm = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / den
    return (max(0, c-pm)*100, min(1, c+pm)*100)

def r_ci(subset, z=1.96):
    rs = [pnl_r(s) for s in subset if pnl_r(s) is not None]
    if len(rs) < 2: return (None, None, None)
    m = sum(rs)/len(rs)
    std = math.sqrt(sum((r-m)**2 for r in rs)/(len(rs)-1))
    se = std/math.sqrt(len(rs))
    return (m, m-z*se, m+z*se)

all_closed = [s for s in data if closed(s)]
NEUTRAL_TRENDS = {"中立・もみあい", "中立", "neutral", "range", "もみあい"}
DOWN_TRENDS = {"下降", "downtrend", "down"}
GATE_NEUTRAL_LONG = "2026-06-17"
GATE_DOWN_LONG    = "2026-06-25"
GATE_METAL_LONG   = "2026-06-19"
```

---

## 生出力（python /tmp/lab075_analysis2.py）

```
Total closed: 3562

============================================================
1. trend=中立・もみあい × dir=long
============================================================
  全期間: N=956 k=428 44.8% CI[41.6%~47.9%] E(R)=0.067 RCI[-0.043~0.177]
  IS(gate前 <2026-06-17): N=217 k=75 34.6% CI[28.6%~41.1%] E(R)=-0.290 RCI[-0.512~-0.068]
  FWD(gate後 >=2026-06-17): N=739 k=353 47.8% CI[44.2%~51.4%] E(R)=0.172 RCI[0.046~0.298]
  FWD×metal: N=80 k=45 56.2% CI[45.3%~66.6%] E(R)=0.469 RCI[0.086~0.852]
  FWD×index: N=180 k=70 38.9% CI[32.1%~46.2%] E(R)=-0.139 RCI[-0.389~0.111]
  FWD×jpy_fx: N=165 k=87 52.7% CI[45.1%~60.2%] E(R)=0.345 RCI[0.078~0.613]
  FWD×other_fx: N=230 k=108 47.0% CI[40.6%~53.4%] E(R)=0.143 RCI[-0.083~0.370]
  FWD×oil: N=32 k=16 50.0% CI[33.6%~66.4%] E(R)=0.250 RCI[-0.366~0.866]
  FWD×btc: N=44 k=25 56.8% CI[42.2%~70.3%] E(R)=0.489 RCI[-0.030~1.007]

============================================================
2. trend=下降 × dir=long
============================================================
  全期間: N=759 k=340 44.8% CI[41.3%~48.4%] E(R)=0.068 RCI[-0.056~0.192]
  IS(gate前 <2026-06-25): N=260 k=92 35.4% CI[29.8%~41.4%] E(R)=-0.262 RCI[-0.465~-0.058]
  FWD(gate後 >=2026-06-25): N=499 k=248 49.7% CI[45.3%~54.1%] E(R)=0.239 RCI[0.086~0.393]
  FWD×metal: N=84 k=45 53.6% CI[43.0%~63.8%] E(R)=0.375 RCI[-0.001~0.751]
  FWD×index: N=105 k=49 46.7% CI[37.4%~56.2%] E(R)=0.133 RCI[-0.202~0.469]
  FWD×jpy_fx: N=64 k=33 51.6% CI[39.6%~63.4%] E(R)=0.305 RCI[-0.127~0.737]
  FWD×other_fx: N=147 k=68 46.3% CI[38.4%~54.3%] E(R)=0.119 RCI[-0.164~0.402]
  FWD×oil: N=31 k=21 67.7% CI[50.1%~81.4%] E(R)=0.871 RCI[0.285~1.456]
  FWD×btc: N=64 k=31 48.4% CI[36.6%~60.4%] E(R)=0.195 RCI[-0.237~0.627]
  FWD×reversalL: N=185 k=103 55.7% CI[48.5%~62.6%] E(R)=0.449 RCI[0.197~0.700]

============================================================
3. group=metal × dir=long (tracker demoted)
============================================================
  全期間: N=328 k=131 39.9% CI[34.8%~45.3%] E(R)=-0.102 RCI[-0.288~0.084]
  IS(gate前 <2026-06-19): N=93 k=17 18.3% CI[11.7%~27.3%] E(R)=-0.860 RCI[-1.137~-0.584]
  FWD(gate後 >=2026-06-19): N=235 k=114 48.5% CI[42.2%~54.9%] E(R)=0.198 RCI[-0.026~0.422]
  FWD月別:
    2026-06: N=43 33% E(R)=-0.360
    2026-07: N=108 40% E(R)=-0.106
    2026-08: N=84 68% E(R)=0.875
  FWD シグナル別:
    bb_lower_touch:     N=54 44.4% E(R)=0.056
    macd_golden:        N=52 46.2% E(R)=0.115
    rsi_oversold_bounce:N=33 54.5% E(R)=0.409
    high_break:         N=24 50.0% E(R)=0.250
    bb_upper_break:     N=23 56.5% E(R)=0.478
    support_bounce:     N=20 60.0% E(R)=0.600
  FWD×GC=F: N=111 50.5% CI[41.3%~59.6%] E(R)=0.266
  FWD×SI=F: N=124 46.8% CI[38.2%~55.5%] E(R)=0.137

============================================================
4. 比較: 全体ロングFWD(>=2026-06-17)
============================================================
  全体ロングFWD: N=2075 k=952 45.9% CI[43.7%~48.0%] E(R)=0.106 RCI[0.031~0.181]

============================================================
5. トレンド分布
============================================================
  trend=上昇:     1301
  trend=中立・もみあい: 1227
  trend=下降:     1021
  trend=unknown:    13

============================================================
6. IS期間のみ金属ロング vs 指数ロング
============================================================
  IS指数×ロング: N=169 k=91 53.8% CI[46.3%~61.2%] E(R)=0.385 RCI[0.121~0.648]
  IS金属×ロング: N=93 k=17 18.3% CI[11.7%~27.3%] E(R)=-0.860 RCI[-1.137~-0.584]
```

---

## 交絡点検

- trend=中立×long FWD: metal(56%)・jpy_fx(52%)・btc(57%)が改善主因。index(38.9%)のみ依然弱い
- trend=下降×long FWD: oil(67.7% N=31)が高いが小サンプル注意。reversalL(55.7% N=185)が最大の正貢献
- metal×long降格: 2026-06-07月は-0.36R→2026-07月は-0.11R→2026-08月は+0.88R(N=84)の月次急変化
- metal×long IS: 18.3%(N=93)は同期間の指数×long 53.8%(N=169)と35.5pp乖離——IS期間に固有の金属不毛期が確認済み（#039/#013と整合）

---

## Wilson CI計算メモ（事前宣言条件の照合）

| 条件 | 値 | 判定 |
|---|---|---|
| trend=中立×long FWD RCI下限>0 | +0.046 | ✅ |
| trend=中立×long FWD N≥80 | 739 | ✅ |
| trend=下降×long FWD RCI下限>0 | +0.086 | ✅ |
| trend=下降×long FWD N≥80 | 499 | ✅ |
| metal×long FWD RCI下限>0 | -0.026 | ❌ (降格のみ・⛔反証未到達) |
