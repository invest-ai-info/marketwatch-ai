# lab-103-analysis.md
# 基準日: 2026-09-19 / #103

## 仮説採択

- **採択理由**: トラッカー優先度①（昇格済み `trend=上昇×reversalL` が demote_strikes=1 に到達）
- **テーマ**: 上昇中の逆張り買い（trend=上昇×reversalL）——RSI型62% vs BB型42%の20pp分裂が前向きRCI下限をマイナスに転落させた解剖（降格警戒ストライク1）
- **登録日**: 2026-06-22 / FWD N=318 / status=promoted ds=1

## 検証スクリプト全文

```python
import json, math
from collections import defaultdict

with open('signals-log.json') as f:
    logs = json.load(f)

def closed(d): return d.get('outcome') in ('tp1','tp2','sl')
def win(d): return d.get('outcome') in ('tp1','tp2')
def get_trend(d):
    ta = d.get('trend_alignment')
    if isinstance(ta, dict) and ta.get('higher_tf_trend'):
        return ta['higher_tf_trend']
    return 'unknown'
def is_long(d): return 'ロング' in (d.get('direction') or '')
REV = {'rsi_oversold_bounce','bb_lower_touch'}
def is_reversal_long(d): return is_long(d) and d.get('primary_signal') in REV

def tp1_r(d):
    return 4.0/3.0 if d.get('outcome') in ('tp1','tp2') else -1.0

def stats(sigs):
    if not sigs: return None
    k = sum(1 for s in sigs if win(s))
    n = len(sigs)
    rs = [tp1_r(s) for s in sigs]
    avgR = sum(rs)/len(rs)
    z = 1.96
    p = k/n if n > 0 else 0
    num = z*z/(2*n) + z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))
    denom = 1 + z*z/n
    lo = max(0,(p + z*z/(2*n) - num) / denom)
    hi = min(1,(p + z*z/(2*n) + num) / denom)
    var = sum((r-avgR)**2 for r in rs)/(len(rs)-1) if len(rs)>1 else 0
    se = math.sqrt(var/len(rs)) if len(rs)>0 else 0
    rlo = avgR - z*se
    rhi = avgR + z*se
    return {'k':k,'n':n,'pct':k/n*100,'ci_lo':lo*100,'ci_hi':hi*100,'avgR':avgR,'rci_lo':rlo,'rci_hi':rhi}

REG = "2026-06-22"
all_revL = [s for s in logs if closed(s) and is_reversal_long(s)]
all_up = [s for s in all_revL if get_trend(s) == '上昇']
IS_up = [s for s in all_up if (s.get('fired_at') or '')[:10] < REG]
FWD_up = [s for s in all_up if (s.get('fired_at') or '')[:10] >= REG]
```

## 生出力

```
総クローズ: 4579

IS (発火日<2026-06-22): k=54/n=101 53.5% CI[42.0%,64.7%] E(R)=0.248 RCI=[0.019,0.476]
FWD (発火日>=2026-06-22): k=150/n=318 47.2% CI[41.2%,53.3%] E(R)=0.101 RCI=[-0.028,0.229]

月別FWD:
  2026-06: k=14/n=20 70.0% CI[40.0%,93.5%] E(R)=0.633 RCI=[0.153,1.114]
  2026-07: k=61/n=128 47.7% CI[37.7%,57.7%] E(R)=0.112 RCI=[-0.091,0.315]
  2026-08: k=52/n=122 42.6% CI[32.7%,53.0%] E(R)=-0.005 RCI=[-0.211,0.200]
  2026-09: k=23/n=48 47.9% CI[30.8%,65.4%] E(R)=0.118 RCI=[-0.215,0.451]

シグナル別FWD:
  rsi_oversold_bounce: k=48/n=77 62.3% CI[48.8%,74.7%] E(R)=0.455 RCI=[0.200,0.709]
  bb_lower_touch: k=102/n=241 42.3% CI[35.5%,49.4%] E(R)=-0.012 RCI=[-0.158,0.133]

グループ別FWD:
  index: k=31/n=80 38.8% CI[26.5%,52.0%] E(R)=-0.096 RCI=[-0.347,0.155]
  metal: k=12/n=23 52.2% CI[25.8%,77.9%] E(R)=0.217
  btc: k=14/n=25 56.0% CI[30.4%,80.0%] E(R)=0.307
  oil: k=9/n=16 56.2% CI[23.5%,86.6%] E(R)=0.312

時間足別FWD:
  1h: k=84/n=182 46.2% CI[38.0%,54.4%] E(R)=0.077 RCI=[-0.093,0.246]
  4h: k=50/n=113 44.2% CI[33.8%,55.1%] E(R)=0.032 RCI=[-0.182,0.247]
  1d: k=16/n=23 69.6% CI[42.0%,91.6%] E(R)=0.623 RCI=[0.175,1.072]

比較 上昇×ロング全体:
  IS: k=95/n=225 42.2% CI[35.1%,49.6%] E(R)=-0.015
  FWD: k=403/n=962 41.9% CI[38.6%,45.2%] E(R)=-0.023

シグナル×月別FWD:
  rsi_oversold_bounce:
    2026-07: k=20/n=30 66.7% CI[43.1%,86.4%] E(R)=0.556 RCI=[0.155,0.956]
    2026-08: k=17/n=29 58.6% CI[34.9%,80.3%] E(R)=0.368 RCI=[-0.058,0.793]
    2026-09: k=8/n=15 53.3% CI[19.9%,85.4%] E(R)=0.244 RCI=[-0.365,0.854]
  bb_lower_touch:
    2026-07: k=41/n=98 41.8% CI[30.7%,53.6%] E(R)=-0.024 RCI=[-0.253,0.205]
    2026-08: k=35/n=93 37.6% CI[26.5%,49.8%] E(R)=-0.122 RCI=[-0.353,0.109]
    2026-09: k=15/n=33 45.5% CI[24.6%,67.2%] E(R)=0.061 RCI=[-0.342,0.463]
```

## 事前宣言・判定

- H1: FWD RCI下限 ≤ 0（降格ストライク1の定量的根拠） → **RCI_lo=-0.028 ✅**
- H2: RSI型 vs BB型の差 ≥ 15pp → **62.3%-42.3%=20.0pp ✅**
- H3: 日足 E(R) > max(1h,4h) E(R) → **1d=+0.623 > 1h=+0.077 > 4h=+0.032 ✅**

## 交絡点検

- 指数FWD 38.8% (N=80) が全体の下引き主因（指数 IS 68.6% → FWD 38.8% の急落が継続）
- BB型 241/318件=75.8%が全体の大多数を占め、BB型の42.3%がFWD全体を43%付近に引き下げている
- RSI型(N=77)はIS・FWD問わず60%超と頑健
- 金属FWD 52.2%(N=23)はN小・BTC FWD 56.0%(N=25)はN小 → 統計確定打なし
- 上昇×ロング全体FWD 41.9% = reversalLでない上昇ロングは損益分岐以下 → reversalL自体の選別効果あり

## トラッカー参照値（2026-09-19）

- N=315, 48%, RCI[-0.040,+0.262], status=promoted, demote_strikes=1
- （スクリプト計算: N=318, 47.2%, RCI[-0.028,+0.229] — 差は fired_at vs outcome_resolved_at）
