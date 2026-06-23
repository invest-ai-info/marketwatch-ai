# lab-019 解析ノート
## 仮説: もみあい×ショートのエッジ解剖（#12・26件増データによる追跡再検証）

**基準日**: 2026-06-24 JST  
**データ**: signals-log.json (N=1260 総件、決済済 N=993)

---

## 採択経緯

tracker update 2026-06-24実行後：
- `trend=中立・もみあい×dir=short` edge（前向きトラッカー）: 10/31=32%, R=-0.247
- スイープFDR新候補: 0本（全12本重複スキップ）
- 優先度②「前向きで大きく動いた仮説」→ もみあいSの前向き32%が in-sample 67.3% から大幅乖離
- #12で33/49=67.3% CI[53.4~78.8%]を発見したが現在38/75=50.7%まで軟化
- 追加26件が5/26=19.2%と急落→エッジ構造の解剖を実施

---

## 分析スクリプト

```python
import json, math

def wilson(k, n, z=1.96):
    if n == 0: return (0.0, 100.0)
    p = k/n
    den = 1 + z*z/n
    c = (p + z*z/(2*n))/den
    pm = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))/den
    return (max(0,c-pm)*100, min(1,c+pm)*100)

def ER(k, n):
    return (k * 1.333 + (n-k) * (-1.0)) / n if n > 0 else 0

with open('signals-log.json') as f:
    data = json.load(f)

GROUPS = {
    'metal':    {'GC=F', 'SI=F'},
    'index':    {'NKD=F', 'ES=F', 'NQ=F', 'YM=F', '^FTSE'},
    'jpy_fx':   {'USDJPY=X', 'EURJPY=X', 'GBPJPY=X', 'AUDJPY=X'},
    'other_fx': {'EURUSD=X', 'GBPUSD=X', 'AUDUSD=X', 'EURAUD=X', 'GBPAUD=X'},
    'btc':      {'BTC-USD'},
    'oil':      {'CL=F'},
}

def get_trend(d):
    ta = d.get('trend_alignment')
    if isinstance(ta, dict) and ta.get('higher_tf_trend'):
        return ta['higher_tf_trend']
    return 'unknown'

closed = [s for s in data if s.get('outcome') in ('tp1','tp2','sl')]

def stats(subset):
    k = sum(1 for s in subset if s.get('outcome') in ('tp1','tp2'))
    n = len(subset)
    lo, hi = wilson(k, n)
    e = ER(k, n)
    return k, n, lo, hi, e

# Main
momai_s = [s for s in closed if get_trend(s)=='中立・もみあい' and 'ショート' in (s.get('direction') or '')]
momai_l = [s for s in closed if get_trend(s)=='中立・もみあい' and 'ロング' in (s.get('direction') or '')]

# Signal breakdown
for sig in ['macd_dead','low_break','ma_dead']:
    ss = [s for s in momai_s if s.get('primary_signal')==sig]
    k,n,lo,hi,e = stats(ss)

# Group breakdown  
for g, tickers in GROUPS.items():
    gs = [s for s in momai_s if s.get('ticker') in tickers]
    k,n,lo,hi,e = stats(gs)

# low_break×metal
lb_metal = [s for s in momai_s if s.get('primary_signal')=='low_break' 
            and s.get('ticker') in GROUPS['metal']]

# #012比較
# #012時点: 33/49=67.3%
# 追加26件: (38-33)/(75-49) = 5/26 = 19.2%
```

---

## 生出力

```
Total closed: 993

もみあい×S ALL: 38/75=50.7% CI[39.6~61.7%] E(R)=+0.182
もみあい×L ALL: 95/265=35.8% CI[30.3~41.8%] E(R)=-0.164
下降×S ALL: 31/101=30.7% CI[22.5~40.3%] E(R)=-0.284
上昇×S ALL: 46/95=48.4% CI[38.6~58.3%] E(R)=+0.130

=== もみあい×S: signal breakdown ===
  macd_dead: 20/35=57.1% CI[40.9~72.0%] E(R)=+0.333
  low_break: 10/28=35.7% CI[20.7~54.2%] E(R)=-0.167
  ma_dead: 5/9=55.6% CI[26.7~81.1%] E(R)=+0.296

=== もみあい×S: group breakdown ===
  metal: 6/17=35.3% CI[17.3~58.7%] E(R)=-0.177
  index: 2/3=66.7% CI[20.8~93.9%] E(R)=+0.555 ※N=3 tiny
  jpy_fx: 5/13=38.5% CI[17.7~64.5%] E(R)=-0.103
  other_fx: 17/31=54.8% CI[37.8~70.8%] E(R)=+0.279
  btc: 6/7=85.7% CI[48.7~97.4%] E(R)=+1.000 ※N=7 tiny
  oil: 2/4=50.0% CI[15.0~85.0%] E(R)=+0.166 ※N=4 tiny

=== もみあい×S: low_break×group ===
  low_break×metal: 0/10=0.0%   ← 主犯格
  low_break×jpy_fx: 0/3=0.0%
  low_break×other_fx: 3/7=42.9%
  low_break×btc: 5/5=100.0% ※N=5 tiny
  low_break×oil: 2/3=66.7% ※N=3 tiny

=== もみあい×S: macd_dead×group ===
  macd_dead×metal: 3/4=75.0% ※N=4 tiny
  macd_dead×jpy_fx: 5/9=55.6%
  macd_dead×other_fx: 9/16=56.2%

=== #012比較 ===
#012 claim: 33/49=67.3% CI[53.4~78.8%]
#019 today: 38/75=50.7% CI[39.6~61.7%]
追加26件: 5/26=19.2%  ← 急落

前向きトラッカー(2026-06-24, signal_lab_tracker.py出力):
  もみあい×S edge: 10/31=32% R=-0.247 CI[-0.64~+0.14]
  もみあい×L gate: 20/48=42% R=-0.028 CI[-0.36~+0.30]
```

---

## 交絡点検

1. **低勝率の主因**: low_break×metal (0/10=0.0%) が もみあい×S 全体を下引き
2. **macd_deadは健在**: 20/35=57.1%、グループを問わず50%超が多い
3. **期間交絡**: 追加26件5/26=19.2% — 最近の相場でもみあいS×low_breakが特に苦手になった可能性
4. **追加26件の組成**: 下引きした近期シグナルはlow_break偏りが疑われるが、日付フィルタは verify.py 非対応次元のため探索的記録のみ

---

## トラッカー現在値（2026-06-24 update後）

| ID | 仮説 | 前向きk/n | 勝率 | 平均R | 状態 |
|----|------|---------|------|-------|------|
| n | もみあい×S edge | 10/31 | 32% | -0.247 | 🟡蓄積中 |
| n-gate | もみあい×L gate | 20/48 | 42% | -0.028 | 🟡蓄積中 |
| 指数×L | 指数×ロング(全足ライブ) | 44/69 | 64% | +0.488 | 🟡蓄積中 |
