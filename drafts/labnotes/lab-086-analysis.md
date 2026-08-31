# Lab #086 Analysis Notes
Date: 2026-09-01 JST
Topic: rsi_oversold_bounce 全足 FWD N=257 昇格2回目挑戦——4H足CI下限52%超のエッジ確立と1H足46%の無エッジ二極化

## Tracker Context
- Hypothesis: rsi_oversold_edge（売られすぎ逆張り買い・rsi_oversold_bounce・全足）
- promote_strikes=1（2026-08-28の一時失敗から回復、CI_lo再回復）
- FWD累積: k=135/n=257 = 52.5%
- 登録日: 2026-06-16（IS/FWD境界）

## Sweep Results (2026-09-01)
- FDR candidates: 0
- No new hypothesis registrations today

## Analysis Script

```python
#!/usr/bin/env python3
"""Lab #086 rsi_oversold_bounce 全足 FWD N=257"""
import json, math

GROUPS = {
    "metal":    {"GC=F","SI=F"},
    "index":    {"NKD=F","ES=F","NQ=F","YM=F","^FTSE"},
    "jpy_fx":   {"USDJPY=X","EURJPY=X","GBPJPY=X","AUDJPY=X"},
    "other_fx": {"EURUSD=X","GBPUSD=X","AUDUSD=X","EURAUD=X","GBPAUD=X"},
    "btc":      {"BTC-USD"},
    "oil":      {"CL=F"},
}

def closed(d): return d.get("outcome") in ("tp1","tp2","sl")
def win(d):    return d.get("outcome") in ("tp1","tp2")
def get_group(ticker):
    for g,tickers in GROUPS.items():
        if ticker in tickers: return g
    return "other"
def get_trend(d):
    ta = d.get("trend_alignment") or {}
    return ta.get("higher_tf_trend","")

def wilson(k, n, z=1.96):
    if n == 0: return (0.0, 100.0)
    p = k / n
    den = 1 + z*z/n
    c = (p + z*z/(2*n)) / den
    pm = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / den
    return (max(0, c-pm)*100, min(1, c+pm)*100)

with open("signals-log.json") as f:
    data = json.load(f)

IS_CUTOFF = "2026-06-16"
fwd = [d for d in data if closed(d) and d.get("primary_signal")=="rsi_oversold_bounce"
       and (d.get("fired_at","") or "")[:10] >= IS_CUTOFF]
is_r = [d for d in data if closed(d) and d.get("primary_signal")=="rsi_oversold_bounce"
        and (d.get("fired_at","") or "")[:10] < IS_CUTOFF]
```

## Key Results

### closed()の定義（signal_lab_verify.py準拠）
- closed: outcome in ("tp1","tp2","sl")  ← expiredを含まない
- Total closed (tp1/tp2/sl): 3935

### 全期間 (all-time)
- k=187 n=390 47.9% CI[43.0%, 52.9%]

### IS期間 (<2026-06-16)
- k=52 n=133 39.1% CI[31.2%, 47.6%]

### FWD期間 (>=2026-06-16) — メイン分析
- k=135 n=257 52.5% CI[46.4%, 58.6%]  ← トラッカーと一致

### FWD 時間足別（★主発見）
- 1H: k=79 n=173 45.7% CI[38.4%, 53.1%] ← CI_lo<50% = エッジなし
- 4H: k=46 n=72  63.9% CI[52.4%, 74.0%] ← CI_lo=52.4% > 50%! エッジ確立
- 1D: k=10 n=12  83.3% CI[55.2%, 95.3%] ← 小サンプルに注意

### FWD グループ別
- metal:    k=19 n=35  54.3% CI[38.2%, 69.5%]
- index:    k=29 n=61  47.5% CI[35.5%, 59.8%]
- jpy_fx:   k=32 n=48  66.7% CI[52.5%, 78.3%] ← CI_lo>50%
- other_fx: k=37 n=78  47.4% CI[36.7%, 58.4%]
- btc:      k=7  n=13  53.8% CI[29.1%, 76.8%]
- oil:      k=11 n=22  50.0% CI[30.7%, 69.3%]

### FWD トレンド別
- trend=上昇: k=44 n=66  66.7% CI[54.7%, 76.8%] ← 高位足トレンドとの整合が効く
- trend=下降: k=41 n=100 41.0% CI[31.9%, 50.8%] ← 逆勢で不利

### FWD キーコンボ
- 4H×jpy_fx:   k=16 n=17  94.1% CI[73.0%, 99.0%] ← ★ 強い（ただしn=17・過信禁止）
- 4H×index:    k=7  n=12  58.3% CI[32.0%, 80.7%]
- 4H×metal:    k=6  n=9   66.7% CI[35.4%, 87.9%]
- 4H×other_fx: k=13 n=26  50.0% CI[32.1%, 67.9%]
- 1H×jpy_fx:   k=13 n=28  46.4% CI[29.5%, 64.2%]
- 1H×index:    k=22 n=49  44.9% CI[31.9%, 58.7%]
- 1H×metal:    k=13 n=24  54.2% CI[35.1%, 72.1%]
- 1H×other_fx: k=22 n=50  44.0% CI[31.2%, 57.7%]

### FWD 月次推移
- 2026-06: k=29 n=72  40.3% CI[29.7%, 51.8%] ← 登録直後は低調
- 2026-07: k=54 n=90  60.0% CI[49.7%, 69.5%] ← 回復
- 2026-08: k=52 n=95  54.7% CI[44.7%, 64.4%] ← 安定

### bb_lower_touch比較（参考）
- FWD: k=263 n=602 43.7% CI[39.8%, 47.7%] ← rsi_oversold_bounceを8.8pt下回る
- IS:  k=75  n=175 42.9% CI[35.8%, 50.3%]

## Key Insights

1. **足種二極化が明確**: 4H足のCI_lo=52.4%>50%でエッジ確立。1H足のCI_lo=38.4%<50%でエッジなし。
2. **4H×jpy_fx コンボ**: k=16/n=17、94.1%は極めて高いが、n=17は小サンプル。実トレードへの単純適用は要注意。
3. **トレンド方向が重要**: 上昇トレンド下では66.7%（CI_lo=54.7%）。下降トレンドでは41.0%（CI_lo<50%）。
4. **6月初動の低調**: FWD期間の最初の月（2026-06）は40.3%と低調だったが、7月以降は回復。
5. **IS→FWD変化**: IS 39.1% → FWD 52.5%。IS期間が低かったにもかかわらずFWDで改善した珍しいパターン。

## Claims Summary (for lab-086-claims.json)
| label | filter | k | n | rate | CI_lo | CI_hi |
|---|---|---|---|---|---|---|
| FWD全体 | signal=rsi_oversold_bounce, fired_from=2026-06-16 | 135 | 257 | 52.5% | 46.4% | 58.6% |
| FWD 1H足 | +tf=1h | 79 | 173 | 45.7% | 38.4% | 53.1% |
| FWD 4H足 | +tf=4h | 46 | 72 | 63.9% | 52.4% | 74.0% |
| FWD 1D足 | +tf=1d | 10 | 12 | 83.3% | 55.2% | 95.3% |
| IS全体 | signal=rsi_oversold_bounce, fired_before=2026-06-16 | 52 | 133 | 39.1% | 31.2% | 47.6% |
| FWD jpy_fx | +group=jpy_fx | 32 | 48 | 66.7% | 52.5% | 78.3% |
| FWD 4H×jpy_fx | +tf=4h, group=jpy_fx | 16 | 17 | 94.1% | 73.0% | 99.0% |
| FWD trend=上昇 | +trend=上昇 | 44 | 66 | 66.7% | 54.7% | 76.8% |
