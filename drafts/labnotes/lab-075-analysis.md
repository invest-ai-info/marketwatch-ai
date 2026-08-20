# lab-075-analysis.md
# AIシグナル研究日誌 #075
# テーマ: trend=上昇×逆張り買い FWD後期解剖 ── BB全域マイナス・指数全域マイナス・RSI全域プラス
# 実行日: 2026-08-21

## 検証スクリプト (Python 3)

```python
import json, math

def wilson_lo(k, n, z=1.96):
    if n == 0: return 0.0
    p = k / n
    num = p + z**2/(2*n) - z * math.sqrt(p*(1-p)/n + z**2/(4*n**2))
    den = 1 + z**2/n
    return num / den

def wilson_hi(k, n, z=1.96):
    if n == 0: return 0.0
    p = k / n
    num = p + z**2/(2*n) + z * math.sqrt(p*(1-p)/n + z**2/(4*n**2))
    den = 1 + z**2/n
    return num / den

with open("signals-log.json") as f:
    data = json.load(f)

REV = {"rsi_oversold_bounce", "bb_lower_touch"}
GROUPS = {
    "metal": {"GC=F", "SI=F"},
    "index": {"NKD=F", "ES=F", "NQ=F", "YM=F", "^FTSE"},
    "jpy_fx": {"USDJPY=X", "EURJPY=X", "GBPJPY=X", "AUDJPY=X"},
    "other_fx": {"EURUSD=X", "GBPUSD=X", "AUDUSD=X", "EURAUD=X", "GBPAUD=X"},
    "btc": {"BTC-USD"},
    "oil": {"CL=F"},
}

def get_group(ticker):
    for g, tickers in GROUPS.items():
        if ticker in tickers:
            return g
    return None

def get_trend(d):
    ta = d.get("trend_alignment")
    if not ta: return None
    return ta.get("higher_tf_trend")

def closed(d):
    return d.get("outcome") in ("tp1", "tp2", "sl")

def is_reversal_long(d):
    if d.get("direction") != "ロング":
        return False
    ps = d.get("primary_signal", "")
    return ps in REV

def get_R(d):
    ps = d.get("primary_signal", "")
    outcome = d.get("outcome", "")
    if outcome == "tp1": return 2.0/1.5   # ATR x2 / ATR x1.5
    if outcome == "tp2": return 3.0/1.5   # ATR x3 / ATR x1.5
    if outcome == "sl":  return -1.0
    return 0.0

def compute(filter_fn):
    k = n = 0
    avgR_sum = 0.0
    for d in data:
        if not closed(d): continue
        if not filter_fn(d): continue
        n += 1
        r = get_R(d)
        avgR_sum += r
        if r > 0: k += 1
    avgR = avgR_sum / n if n > 0 else 0.0
    return k, n, avgR

# ─── 全期間 ───
k, n, avgR = compute(lambda d: get_trend(d)=="上昇" and is_reversal_long(d))
print(f"全期間 trend=上昇×revL: k={k} n={n} pct={k/n*100:.1f}% avgR={avgR:.3f}")
wlo = wilson_lo(k,n); whi = wilson_hi(k,n)
print(f"  Wilson CI: [{wlo*100:.1f}%, {whi*100:.1f}%]")

k_rsi, n_rsi, avgR_rsi = compute(lambda d: get_trend(d)=="上昇" and is_reversal_long(d) and d.get("primary_signal")=="rsi_oversold_bounce")
print(f"全期間 RSI: k={k_rsi} n={n_rsi} pct={k_rsi/n_rsi*100:.1f}% avgR={avgR_rsi:.3f}")

k_bb, n_bb, avgR_bb = compute(lambda d: get_trend(d)=="上昇" and is_reversal_long(d) and d.get("primary_signal")=="bb_lower_touch")
print(f"全期間 BB: k={k_bb} n={n_bb} pct={k_bb/n_bb*100:.1f}% avgR={avgR_bb:.3f}")

# ─── FWD全体 (fired_from 2026-06-22) ───
def after(d, dt):
    return (d.get("fired_at") or "") >= dt

k_fwd, n_fwd, avgR_fwd = compute(lambda d: get_trend(d)=="上昇" and is_reversal_long(d) and after(d, "2026-06-22"))
print(f"\nFWD全体: k={k_fwd} n={n_fwd} pct={k_fwd/n_fwd*100:.1f}% avgR={avgR_fwd:.3f}")
wlo_f = wilson_lo(k_fwd,n_fwd); whi_f = wilson_hi(k_fwd,n_fwd)
print(f"  Wilson CI: [{wlo_f*100:.1f}%, {whi_f*100:.1f}%]")

k_frsi, n_frsi, avgR_frsi = compute(lambda d: get_trend(d)=="上昇" and is_reversal_long(d) and after(d,"2026-06-22") and d.get("primary_signal")=="rsi_oversold_bounce")
print(f"FWD RSI: k={k_frsi} n={n_frsi} pct={k_frsi/n_frsi*100:.1f}% avgR={avgR_frsi:.3f} WilsonCI=[{wilson_lo(k_frsi,n_frsi)*100:.1f}%,{wilson_hi(k_frsi,n_frsi)*100:.1f}%]")

k_fbb, n_fbb, avgR_fbb = compute(lambda d: get_trend(d)=="上昇" and is_reversal_long(d) and after(d,"2026-06-22") and d.get("primary_signal")=="bb_lower_touch")
print(f"FWD BB: k={k_fbb} n={n_fbb} pct={k_fbb/n_fbb*100:.1f}% avgR={avgR_fbb:.3f} WilsonCI=[{wilson_lo(k_fbb,n_fbb)*100:.1f}%,{wilson_hi(k_fbb,n_fbb)*100:.1f}%]")

k_fi, n_fi, avgR_fi = compute(lambda d: get_trend(d)=="上昇" and is_reversal_long(d) and after(d,"2026-06-22") and get_group(d.get("ticker",""))=="index")
print(f"FWD index: k={k_fi} n={n_fi} pct={k_fi/n_fi*100:.1f}% avgR={avgR_fi:.3f} WilsonCI=[{wilson_lo(k_fi,n_fi)*100:.1f}%,{wilson_hi(k_fi,n_fi)*100:.1f}%]")

k_jpy, n_jpy, avgR_jpy = compute(lambda d: get_trend(d)=="上昇" and is_reversal_long(d) and after(d,"2026-06-22") and get_group(d.get("ticker",""))=="jpy_fx")
print(f"FWD jpy_fx: k={k_jpy} n={n_jpy} pct={k_jpy/n_jpy*100:.1f}% avgR={avgR_jpy:.3f} WilsonCI=[{wilson_lo(k_jpy,n_jpy)*100:.1f}%,{wilson_hi(k_jpy,n_jpy)*100:.1f}%]")

k_ofx, n_ofx, avgR_ofx = compute(lambda d: get_trend(d)=="上昇" and is_reversal_long(d) and after(d,"2026-06-22") and get_group(d.get("ticker",""))=="other_fx")
print(f"FWD other_fx: k={k_ofx} n={n_ofx} pct={k_ofx/n_ofx*100:.1f}% avgR={avgR_ofx:.3f} WilsonCI=[{wilson_lo(k_ofx,n_ofx)*100:.1f}%,{wilson_hi(k_ofx,n_ofx)*100:.1f}%]")

# ─── FWD後期 (fired_from 2026-08-06) ───
k_l, n_l, avgR_l = compute(lambda d: get_trend(d)=="上昇" and is_reversal_long(d) and after(d,"2026-08-06"))
print(f"\nFWD後期全体: k={k_l} n={n_l} pct={k_l/n_l*100:.1f}% avgR={avgR_l:.3f} WilsonCI=[{wilson_lo(k_l,n_l)*100:.1f}%,{wilson_hi(k_l,n_l)*100:.1f}%]")

k_lbb, n_lbb, avgR_lbb = compute(lambda d: get_trend(d)=="上昇" and is_reversal_long(d) and after(d,"2026-08-06") and d.get("primary_signal")=="bb_lower_touch")
wlo_lbb = wilson_lo(k_lbb,n_lbb); whi_lbb = wilson_hi(k_lbb,n_lbb)
print(f"FWD後期 BB: k={k_lbb} n={n_lbb} pct={k_lbb/n_lbb*100:.1f}% avgR={avgR_lbb:.3f} WilsonCI=[{wlo_lbb*100:.1f}%,{whi_lbb*100:.1f}%]")

k_li, n_li, avgR_li = compute(lambda d: get_trend(d)=="上昇" and is_reversal_long(d) and after(d,"2026-08-06") and get_group(d.get("ticker",""))=="index")
wlo_li = wilson_lo(k_li,n_li); whi_li = wilson_hi(k_li,n_li)
print(f"FWD後期 index: k={k_li} n={n_li} pct={k_li/n_li*100:.1f}% avgR={avgR_li:.3f} WilsonCI=[{wlo_li*100:.1f}%,{whi_li*100:.1f}%]")

k_lrsi, n_lrsi, avgR_lrsi = compute(lambda d: get_trend(d)=="上昇" and is_reversal_long(d) and after(d,"2026-08-06") and d.get("primary_signal")=="rsi_oversold_bounce")
wlo_lrsi = wilson_lo(k_lrsi,n_lrsi); whi_lrsi = wilson_hi(k_lrsi,n_lrsi)
print(f"FWD後期 RSI: k={k_lrsi} n={n_lrsi} pct={k_lrsi/n_lrsi*100:.1f}% avgR={avgR_lrsi:.3f} WilsonCI=[{wlo_lrsi*100:.1f}%,{whi_lrsi*100:.1f}%]")
```

## 実行結果（verify.py の compute() 関数準拠の確定値）

```
全期間 trend=上昇×revL: k=161 n=330 pct=48.8% avgR=+0.138
  Wilson CI: [43.4%, 54.2%]
全期間 RSI: k=49 n=80 pct=61.3% avgR=+0.429  WilsonCI=[50.3%, 71.2%]
全期間 BB: k=112 n=250 pct=44.8% avgR=+0.045  WilsonCI=[38.8%, 51.0%]

FWD全体: k=107 n=229 pct=46.7% avgR=+0.090
  Wilson CI: [40.4%, 53.2%]
FWD RSI: k=36 n=55 pct=65.5% avgR=+0.527  WilsonCI=[52.3%, 76.6%]
FWD BB: k=71 n=174 pct=40.8% avgR=-0.048  WilsonCI=[33.8%, 48.2%]
FWD index: k=22 n=66 pct=33.3% avgR=-0.222  WilsonCI=[23.2%, 45.3%]
FWD jpy_fx: k=37 n=73 pct=50.7% avgR=+0.182  WilsonCI=[39.5%, 61.8%]
FWD other_fx: k=29 n=54 pct=53.7% avgR=+0.253  WilsonCI=[40.6%, 66.3%]

FWD後期全体: k=25 n=74 pct=33.8% avgR=-0.212  WilsonCI=[24.0%, 45.1%]
FWD後期 BB: k=15 n=55 pct=27.3% avgR=-0.364  WilsonCI=[17.3%, 40.2%]
FWD後期 index: k=7 n=31 pct=22.6% avgR=-0.473  WilsonCI=[11.4%, 39.8%]
FWD後期 RSI: k=10 n=19 pct=52.6% avgR=+0.228  WilsonCI=[31.7%, 72.7%]
```

## RCI計算（1R換算・avgR±1.96×SE）

SE = sqrt(Var(R)/n)。各outcome の R: tp1=+1.333, tp2=+2.0, sl=-1.0

| セグメント | k/n | avgR | RCI下限 | RCI上限 |
|---|---|---|---|---|
| 全期間 | 161/330 | +0.138 | +0.012 | +0.264 |
| 全期間 RSI | 49/80 | +0.429 | +0.178 | +0.680 |
| 全期間 BB | 112/250 | +0.045 | -0.099 | +0.189 |
| FWD全体 | 107/229 | +0.090 | -0.061 | +0.241 |
| FWD RSI ✅ | 36/55 | +0.527 | **+0.231** | +0.823 |
| FWD BB | 71/174 | -0.048 | -0.219 | +0.123 |
| FWD index | 22/66 | -0.222 | -0.490 | +0.045 |
| FWD jpy_fx | 37/73 | +0.182 | -0.087 | +0.452 |
| FWD other_fx | 29/54 | +0.253 | -0.060 | +0.566 |
| FWD後期全体 | 25/74 | -0.212 | -0.465 | +0.041 |
| FWD後期 BB ✅H1 | 15/55 | -0.364 | -0.641 | **-0.087** |
| FWD後期 index ✅H2 | 7/31 | -0.473 | -0.822 | **-0.124** |
| FWD後期 RSI | 10/19 | +0.228 | -0.310 | +0.766 |

## 仮説検証結論

| 仮説 | 内容 | 結果 |
|---|---|---|
| H1 | FWD後期 BB lower_touch の RCI上限 < 0 | ✅ RCI[-0.641, -0.087] 全域マイナス確定 |
| H2 | FWD後期 index の RCI上限 < 0 | ✅ RCI[-0.822, -0.124] 全域マイナス確定 |
| H3 | FWD RSI の RCI下限 > 0 | ✅ RCI[+0.231, +0.823] 全域プラス継続 |

## トラッカー状態（2026-08-21時点）

- status: promoted (昇格維持)
- FWD: k=107, n=228, pct=46.9%, avgR=+0.095, RCI下限=-0.078
- 降格警戒継続: rci_lo が負域
  - 2026-08-18: rci_lo=+0.044（一時回復）
  - 2026-08-19: rci_lo=-0.054（翌日降落）
  - 2026-08-20: rci_lo=-0.092
  - 2026-08-21: rci_lo=-0.078

## スイープ候補（sweep-2026-08-21.json）

- 1件: tf=1d×reversalL（既登録のためスキップ）

## 選択理由

Priority ①今回昇格/反証: なし
Priority ②前向き大変動: trend=上昇×reversalL が降格警戒継続中（2日連続rci_lo<0, 一時回復→再落）→ FWD後期を解剖して BB・指数後期全域マイナス・RSI後期でも全域プラスに届かない事実を記録
本記事テーマとして採用。
