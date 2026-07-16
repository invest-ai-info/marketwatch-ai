# lab-042-analysis.md — 上昇トレンド×reversal_long 昇格確認解析

**実施日**: 2026-07-17 JST
**仮説**: trend=上昇×reversalL（上昇トレンド中の逆張り買い）は損益分岐43%を超えるエッジを持ち、前向きN≥80でE(R)のCI下限>0を達成する
**優先度**: ① 今回✅昇格変化（tracker: trend=上昇×reversalL promoted N=81 R+0.239）

---

## スクリプト全文

```python
import json, math

with open('signals-log.json') as f:
    data = json.load(f)
signals = data if isinstance(data, list) else data.get('signals', [])

# verify.py準拠: closed=tp1+tp2+sl, win=tp1+tp2
closed = [s for s in signals if s.get('outcome') in ('tp1','tp2','sl')]

GROUPS = {
    'metal': {'GC=F','SI=F'},
    'index': {'NKD=F','ES=F','NQ=F','YM=F','^FTSE'},
    'jpy_fx': {'USDJPY=X','EURJPY=X','GBPJPY=X','AUDJPY=X'},
    'other_fx': {'EURUSD=X','GBPUSD=X','AUDUSD=X','EURAUD=X','GBPAUD=X'},
    'btc': {'BTC-USD'},
    'oil': {'CL=F'},
}

def get_group(s):
    t = s.get('ticker','')
    for g, tks in GROUPS.items():
        if t in tks: return g
    return 'other'

def get_trend(s):
    ta = s.get('trend_alignment')
    if isinstance(ta, dict) and ta.get('higher_tf_trend'):
        return ta['higher_tf_trend']
    return None

def is_reversal_long(s):
    return (s.get('direction','').startswith('ロング') and 
            s.get('primary_signal') in ('rsi_oversold_bounce', 'bb_lower_touch'))

def is_win(s):
    return s.get('outcome') in ('tp1','tp2')

def wilson_ci(k, n, z=1.96):
    if n == 0: return 0.0, 0.0, 0.0
    p = k/n
    denom = 1 + z**2/n
    center = (p + z**2/(2*n)) / denom
    margin = z * math.sqrt(p*(1-p)/n + z**2/(4*n**2)) / denom
    return round(p*100,1), round((center-margin)*100,1), round((center+margin)*100,1)

def er_r(k, n):
    if n == 0: return 0.0
    p = k/n
    return round(p*1.33 - (1-p)*1.0, 3)

def rci(k, n, z=1.96):
    if n == 0: return 0.0, 0.0
    p = k/n
    se = math.sqrt(p*(1-p)/n) if n > 1 else 0
    lo = max(0.0, p-z*se)*1.33 - (1-max(0.0, p-z*se))
    hi = min(1.0, p+z*se)*1.33 - (1-min(1.0, p+z*se))
    return round(lo,3), round(hi,3)
```

---

## 生出力

```
Total closed (tp1+tp2+sl): 1792
tp2 signals: 0

全closed: 1792, reversalL: 653, trend記録あり: 649

### trended reversalL by trend:
  trend=上昇×revL: 97/182 = 53.3% CI[46.1%,60.4%] E(R)=0.242 RCI[0.073,0.411]
  trend=下降×revL: 105/253 = 41.5% CI[35.6%,47.7%] E(R)=-0.033 RCI[-0.174,0.108]
  trend=中立・もみあい×revL: 84/214 = 39.3% CI[33.0%,45.9%] E(R)=-0.085 RCI[-0.238,0.067]
  reversalL全体: 287/653 = 44.0% CI[40.2%,47.8%] E(R)=0.024 RCI[-0.065,0.113]

### trend=上昇×revL — グループ別:
  上昇×revL合計: 97/182 = 53.3% CI[46.1%,60.4%] E(R)=0.242 RCI[0.073,0.411]
    index: 42/72 = 58.3% CI[46.8%,69.0%] E(R)=0.359 RCI[0.094,0.625]
    jpy_fx: 26/43 = 60.5% CI[45.6%,73.6%] E(R)=0.409 RCI[0.068,0.749]
    other_fx: 18/47 = 38.3% CI[25.8%,52.6%] E(R)=-0.108 RCI[-0.431,0.216]
    metal: 3/7 = 42.9% N小 (参考のみ)
    btc: 2/6 = 33.3% N小 (参考のみ)
    oil: 6/7 = 85.7% N小 (参考のみ)

### trend=上昇×revL — シグナル別:
    rsi_oversold_bounce: 27/44 = 61.4% CI[46.6%,74.3%] E(R)=0.430 RCI[0.095,0.765]
    bb_lower_touch: 70/138 = 50.7% CI[42.5%,58.9%] E(R)=0.182 RCI[-0.012,0.376]

### trend=上昇×revL — 時間足別:
    tf=1h: 55/111 = 49.5% CI[40.4%,58.7%] E(R)=0.155 RCI[-0.062,0.371]
    tf=4h: 29/55 = 52.7% CI[39.8%,65.3%] E(R)=0.229 RCI[-0.079,0.536]
    tf=1d: 13/16 = 81.2% CI[57.0%,93.4%] E(R)=0.893 N小

### bb×index×上昇×revL:
  bb_lower_touch×index×上昇×revL: 30/52 = 57.7% CI[44.2%,70.1%] E(R)=0.344 RCI[0.031,0.657]

### 対照群:
  trend=上昇全体: 259/619 = 41.8% CI[38.0%,45.8%] E(R)=-0.025 RCI[-0.116,0.065]
  trend=上昇×非revL: 162/437 = 37.1% CI[32.7%,41.7%] E(R)=-0.136 RCI[-0.242,-0.031]
  trend=下降×revL: 105/253 = 41.5% CI[35.6%,47.7%] E(R)=-0.033
  trend=中立×revL: 84/214 = 39.3% CI[33.0%,45.9%] E(R)=-0.085

### jpy_fx詳細:
  jpy_fx×revL全体: 56/113 = 49.6% CI[40.5%,58.6%] E(R)=0.155
    jpy_fx×上昇×revL: 26/43 = 60.5% CI[45.6%,73.6%] E(R)=0.409 RCI[0.068,0.749]
    jpy_fx×下降×revL: 10/19 = 52.6% CI[31.7%,72.7%] E(R)=0.226 N小
    jpy_fx×中立×revL: 20/51 = 39.2% CI[27.0%,52.9%] E(R)=-0.086

### index詳細:
  index×revL全体: 75/143 = 52.4% CI[44.3%,60.5%] E(R)=0.222 RCI[0.031,0.413]
    index×上昇×revL: 42/72 = 58.3% CI[46.8%,69.0%] E(R)=0.359 RCI[0.094,0.625]
    index×下降×revL: 12/22 = 54.5% CI[34.7%,73.1%] E(R)=0.271 N小
    index×中立×revL: 21/49 = 42.9% CI[30.0%,56.7%] E(R)=-0.001
```

---

## 前向きトラッカー更新結果 (2026-07-17)

- trend=上昇×reversalL: 前向き N=81 avg R +0.239 CI[+0.03~+0.44] → **✅昇格**（N≥80・CI下限>0）
- trend=下降×reversalL gate: N=83 avg R +0.406 CI[+0.01~+0.81] → ⛔反証（#041で既報）

---

## 考察・交絡点検

1. **グループ偏り**: 上昇×revL 182件の構成は index 72件(39.6%) + jpy_fx 43件(23.6%) + other_fx 47件(25.8%)
2. **構成シフト交絡**: other_fx(38.3%)がN=47(25.8%)存在することで全体が引き下げられている
3. **index・jpy_fxの優位性**: RCI下限がいずれもプラスで有意なエッジを示す
4. **other_fxの逆効果**: 上昇トレンド中のother_fx逆張り買いは38.3%で損益分岐割れ。#016(ロング全体33%)の延長
5. **シグナル別**: RSI=61.4%(N=44)はBB=50.7%(N=138)より高いが、N=44では95%CIが広い

---

## Wilson CI検定（主要比較）

- trend=上昇×revL CI[46.1%, 60.4%]: 下限46.1% > 43% → H1達成
- 前向き: RCI[+0.03, +0.44]: 下限+0.03 > 0 → 昇格条件クリア
- 対照群 trend=上昇×非revL RCI[-0.242, -0.031]: CI全域マイナス → 逆張りの比較優位を傍証
