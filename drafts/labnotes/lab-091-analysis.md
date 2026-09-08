# Lab #090 — 定点観測：rsi_oversold_bounce CI下限再プラス化 ストライク1保持
## 基準日: 2026-09-07（JST）

## 実行スクリプト

```python
import json, math
from datetime import datetime

def wilson_ci(k, n):
    """Wilson区間 95%CI"""
    if n == 0: return (0, 0)
    z = 1.96
    p = k/n
    center = (p + z**2/(2*n)) / (1 + z**2/n)
    margin = (z * math.sqrt(p*(1-p)/n + z**2/(4*n**2))) / (1 + z**2/n)
    return (max(0, center-margin), min(1, center+margin))

with open('signals-log.json') as f:
    logs = json.load(f)

def is_win(l): return l.get('outcome') == 'tp1'
def is_closed(l): return l.get('outcome') in ('tp1', 'sl')

# rsi_oversold_bounce 前向き（2026-06-16以降、ロング、tp1/sl決済済）
reg_date = '2026-06-16'
fwd = [l for l in logs
       if is_closed(l)
       and l.get('primary_signal') == 'rsi_oversold_bounce'
       and l.get('direction') == 'ロング（買い）'
       and l.get('fired_at', '') >= reg_date]

wins = [l for l in fwd if is_win(l)]
n, k = len(fwd), len(wins)
ci = wilson_ci(k, n)
print(f'rsi_oversold_bounce FWD: k={k}, n={n}, pct={100*k/n:.1f}%, CI=[{100*ci[0]:.1f}%,{100*ci[1]:.1f}%]')

# 4H
fwd_4h = [l for l in fwd if l.get('timeframe') == '4h']
wins_4h = [l for l in fwd_4h if is_win(l)]
n4, k4 = len(fwd_4h), len(wins_4h)
ci4 = wilson_ci(k4, n4)
print(f'  4H: k={k4}, n={n4}, pct={100*k4/n4:.1f}%, CI=[{100*ci4[0]:.1f}%,{100*ci4[1]:.1f}%]')

# 1H
fwd_1h = [l for l in fwd if l.get('timeframe') == '1h']
wins_1h = [l for l in fwd_1h if is_win(l)]
n1, k1 = len(fwd_1h), len(wins_1h)
ci1 = wilson_ci(k1, n1)
print(f'  1H: k={k1}, n={n1}, pct={100*k1/n1:.1f}%, CI=[{100*ci1[0]:.1f}%,{100*ci1[1]:.1f}%]')
```

## 生出力

```
rsi_oversold_bounce FWD: k=158, n=296, pct=53.4%, CI=[47.7%,59.0%]
  4H: k=56, n=86, pct=65.1%, CI=[54.6%,74.3%]
  1H: k=92, n=198, pct=46.5%, CI=[39.7%,53.4%]
```

## スイープ結果（signal_lab_sweep.py）
- FDR通過候補: 0本（新規なし）

## トラッカー更新（signal_lab_tracker.py update --date 2026-09-07）
- trend=上昇×reversalL: ✅昇格 138/285=48% E(R)=+0.130 CI[-0.03~+0.29]
- 売られすぎ逆張り買い(rsi_oversold_bounce・全足): 🟡蓄積中 158/296=53% E(R)=+0.245 CI[+0.05~+0.44]
  - CI下限+0.05 > 0 → 昇格ストライク1保持中（2連続必要）

## 注目点
1. rsi_oversold_bounce CI下限がプラスに回帰（+0.05）。#082で-0.007に転落してストライクリセット後、N=296で再びプラス化。
2. 4H足: k=56, n=86, 65.1%（CI[54.6%,74.3%]・CI下限43%を大きく上回る）
3. 1H足: k=92, n=198, 46.5%（CI[39.7%,53.4%]・43%をまたぐ・エッジ弱い）
4. 今日は薄い日（FDR0本・新規昇格/反証なし）→ 定点観測のみ記事
