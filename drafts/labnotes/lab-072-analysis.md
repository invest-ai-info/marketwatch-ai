# signal-lab #072 分析ノート
基準日: 2026-08-18  
仮説: `trend=下降` gate（「下降トレンドシグナルは損益分岐43%を割る」）の ⛔反証確定

## スイープ・トラッカー結果
```
signal_lab_tracker.py update --date 2026-08-18
  → trend=下降: rejected（前向き 平均R +0.123 / N=567）新規ステータス変化
signal_lab_sweep.py FDR通過:
  - rsi=os×trend=上昇 (R+0.42) ✅黒字
  - tf=1d×reversalL (R+0.63) ✅黒字
  - trend=上昇×reversalL (R+0.20) ✅黒字
  - rsi=ob×trend=下降 (R-0.53) ⛔赤字（新規登録）
```

## 題材採択理由
今回の tracker update で trend=下降 が ⛔反証(rejected) に移行 → 優先度①（今回⛔反証が出た仮説）

## 検証スクリプト

```python
import json, math, random

with open('signals-log.json') as f:
    data = json.load(f)

def closed(s): return s.get('outcome') in ('tp1','tp2','sl')
def win(s): return s.get('outcome') in ('tp1','tp2')

def get_trend(s):
    ta = s.get('trend_alignment')
    if isinstance(ta, dict) and ta.get('higher_tf_trend'):
        return ta['higher_tf_trend']
    return None

def get_group(s):
    t = s.get('ticker','')
    if t in ('GC=F','SI=F'): return 'metal'
    if t in ('NKD=F','ES=F','NQ=F','YM=F','^FTSE'): return 'index'
    if t == 'BTC-USD': return 'btc'
    if t == 'CL=F': return 'oil'
    if t in ('USDJPY','EURJPY','GBPJPY','AUDJPY'): return 'jpy_fx'
    if t in ('EURUSD','GBPUSD','AUDUSD','EURAUD','GBPAUD'): return 'other_fx'
    return 'other'

def get_tf(s): return s.get('timeframe','1h')
def get_sig(s): return s.get('primary_signal','')

def wilson_ci(k, n, z=1.96):
    if n == 0: return (0,0)
    p = k/n; denom = 1+z**2/n
    center = (p+z**2/(2*n))/denom
    margin = z*math.sqrt(p*(1-p)/n+z**2/(4*n**2))/denom
    return (max(0,center-margin), min(1,center+margin))

def calc_E(sigs):
    total=0
    for s in sigs:
        o=s.get('outcome')
        if o=='tp1': total+=1
        elif o=='tp2': total+=2
        elif o=='sl': total-=1
    return total/len(sigs) if sigs else 0

FWD_CUT = '2026-06-25'
all_closed = [s for s in data if closed(s)]  # N=3145
down_all = [s for s in all_closed if get_trend(s)=='下降']  # N=947, k=408
down_is = [s for s in down_all if s.get('fired_at','') < FWD_CUT]  # N=377, k=135
down_fwd = [s for s in down_all if s.get('fired_at','') >= FWD_CUT]  # N=570, k=273
```

## 生出力

### 全体・IS/FWD分解
```
All closed (tp1/tp2/sl): 3145

trend=下降 ALL:   N=947, k=408, 43.1%, CI=[40.0%,46.3%], E(R)=-0.138
trend=下降 IS   (<2026-06-25): N=377, k=135, 35.8%, CI=[31.1%,40.8%], E(R)=-0.284
trend=下降 FWD  (>=2026-06-25): N=570, k=273, 47.9%, CI=[43.8%,52.0%], E(R)=-0.042
  ※ tracker cluster補正後: N=567, E(R)=+0.123, RCI=[+0.01,+0.23] → ⛔反証
```

### FWD分期（時系列）
```
FWD-前期(06/25-07/14): N=226, k=106, 46.9%, E(R)=-0.035
FWD-中期(07/15-07/31): N=229, k=108, 47.2%, E(R)=-0.048
FWD-後期(08/01-08/18): N=123, k=59,  48.0%, E(R)=-0.041
```

### グループ別
```
metal:  ALL N=239, k=86,  36.0%, E(R)=-0.280  | FWD N=103, k=55, 53.4%, E(R)=+0.068
index:  ALL N=121, k=63,  52.1%, E(R)=+0.041  | FWD N=96,  k=49, 51.0%, E(R)=+0.021
btc:    ALL N=118, k=51,  43.2%, E(R)=-0.136  | FWD N=76,  k=34, 44.7%, E(R)=-0.105
oil:    ALL N=68,  k=38,  55.9%, E(R)=+0.118  | FWD N=43,  k=23, 53.5%, E(R)=+0.070
```

### 方向別
```
long:  ALL N=700, k=305, 43.6%, E(R)=-0.129 | FWD N=440, k=213, 48.4%, E(R)=-0.032
short: ALL N=247, k=103, 41.7%, E(R)=-0.166 | FWD N=130, k=60,  46.2%, E(R)=-0.077
```

### 時間足別
```
1h: ALL N=550, k=227, 41.3%, E(R)=-0.175 | FWD N=337, k=154, 45.7%, E(R)=-0.086
4h: ALL N=377, k=175, 46.4%, E(R)=-0.072 | FWD N=217, k=114, 52.5%, E(R)=+0.051
```

### シグナル種別
```
bb_lower_touch:    ALL N=200, k=90, 45.0%  | FWD N=117, k=64, 54.7%, E(R)=+0.094
rsi_oversold:      ALL N=136, k=58, 42.6%  | FWD N=49,  k=29, 59.2%, E(R)=+0.184
high_break:        ALL N=61,  k=21, 34.4%  | FWD N=47,  k=16, 34.0%, E(R)=-0.319
low_break:         ALL N=71,  k=27, 38.0%  | FWD N=27,  k=11, 40.7%, E(R)=-0.185
support_bounce:    ALL N=52,  k=34, 65.4%  | FWD N=52,  k=34, 65.4%
```

## 解釈まとめ
- IS期 E(R)=-0.284（損益分岐割れ）でgateを設立（2026-06-25）
- FWD生カウント 47.9%（N=570）、tracker cluster補正後 E(R)=+0.123 RCI=[+0.01,+0.23]
- 主因: metal IS 36.0% → FWD 53.4%（+17.4pp）= #030/#032/#039/#060と同根の金属レジーム転換
- index: IS~44%→FWD 51.0%（安定的な改善）
- high_break: IS 34.4%・FWD 34.0%（依然として最悪シグナル）
- rsi_oversold: FWD 59.2%・bb_lower_touch FWD 54.7%（逆張りシグナルが優秀）
- 4h足 FWD 52.5% vs 1h足 FWD 45.7%（4h足が優勢）
