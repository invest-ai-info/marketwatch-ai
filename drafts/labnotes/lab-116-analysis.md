# 研究日誌 #116 分析メモ

## 基準日
2026-10-03（JST 06:11）

## 採択仮説
**仮説ID**: rsi_oversold_edge  
**内容**: primary_signal = rsi_oversold_bounce（RSI30割れ反発・逆張り買い）の前向き成績を定点観測  
**採択理由**: カテゴリ②（前向きで大きく動いた仮説）- N=401前向き蓄積、promote_strikes=1/2（昇格基準を1チェックポイント通過）

## 事前宣言
- 確かめること: 前向き追跡（2026-06-16以降）の勝率とR期待値の現在値
- 合否基準: なし（定点観測のみ）
- IS/FWD分離: registered_at=2026-06-16 が基準

## Python集計スクリプト

```python
import json, math
from datetime import datetime

def wilson_ci(k, n, z=1.96):
    if n == 0: return 0.0, 0.0, 0.0
    p = k/n
    c = (p + z*z/(2*n)) / (1 + z*z/n)
    m = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / (1 + z*z/n)
    return round(p*100,1), round(max(0,(c-m)*100),1), round(min(100,(c+m)*100),1)

with open('signals-log.json') as f:
    data = json.load(f)

reg_dt = datetime.strptime('2026-06-16', '%Y-%m-%d').date()
closed = [x for x in data if x.get('outcome') in ('tp1','sl')]

# IS
ins = [x for x in closed
       if x.get('primary_signal')=='rsi_oversold_bounce'
       and datetime.fromisoformat(x['fired_at'].replace('+09:00','')).date() < reg_dt]
ik, in_ = sum(1 for x in ins if x['outcome']=='tp1'), len(ins)
# → k=52, n=133, 39.1%, CI=[31.2%~47.6%]

# FWD
fwd = [x for x in closed
       if x.get('primary_signal')=='rsi_oversold_bounce'
       and datetime.fromisoformat(x['fired_at'].replace('+09:00','')).date() >= reg_dt]
fk, fn = sum(1 for x in fwd if x['outcome']=='tp1'), len(fwd)
# → k=200, n=403, 49.6%, CI=[44.8%~54.5%]

# Baseline (FWD period)
base_fwd = [x for x in closed
            if datetime.fromisoformat(x['fired_at'].replace('+09:00','')).date() >= reg_dt]
bk, bn = sum(1 for x in base_fwd if x['outcome']=='tp1'), len(base_fwd)
# → k=1844, n=4264, 43.2%, CI=[41.8%~44.7%]

# By TF (FWD)
# 1h: k=119, n=249, 47.8%, CI=[41.7%~54.0%]
# 4h: k=66, n=132, 50.0%, CI=[41.6%~58.4%]

# avgR (FWD)
def avg_r(sigs):
    rs = []
    for x in sigs:
        sl = abs(x.get('sl_pct', 0) or 0)
        tp1 = abs(x.get('tp1_pct', 0) or 0)
        if sl > 0 and tp1 > 0:
            r = (tp1/sl) if x['outcome']=='tp1' else -1.0
            rs.append(r)
    return round(sum(rs)/len(rs),3) if rs else None
# FWD avgR: 0.158
# IS avgR: -0.088
```

## 生出力

```
IS: k=52, n=133, rate=39.1%, CI=[31.2%~47.6%], avgR=-0.088
FWD: k=200, n=403, rate=49.6%, CI=[44.8%~54.5%], avgR=+0.158
Baseline (fwd): k=1844, n=4264, rate=43.2%, CI=[41.8%~44.7%]
1h FWD: k=119, n=249, rate=47.8%, CI=[41.7%~54.0%]
4h FWD: k=66, n=132, rate=50.0%, CI=[41.6%~58.4%]
```

## tracker.json 公式値（frozen_1d除外あり）

```
rsi_oversold_edge: forward k=200, n=401, avgR=0.164, rci=[0.001~0.326]
promote_strikes=1 (2回連続で初めて昇格・現在1/2)
```

## スイープ結果
- sweep-2026-10-03.json: FDR通過 0本（候補なし）
- tracker update: 新しい昇格/反証なし

## 採択理由補足
- promote_strikes=1 → R のCI下限が0を超えたチェックポイントを1回通過
- 前向きN=403は meaningful checkpoint（tracker最小N=80を大きく超過）
- 定点観測として公開タイミングとして適切
