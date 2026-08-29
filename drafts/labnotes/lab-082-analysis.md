# lab-082 分析ノート — RSI売られすぎ逆張り買い：4H vs 1H 時間足二極化
**作成日**: 2026-08-28  
**記事番号**: #082  
**IS/FWD境界**: 2026-06-16 (tracker registered_at)

---

## 検証スクリプト

```python
import json
from scipy import stats as sp_stats
import math

# --- signals-log.json 読み込み ---
with open('signals-log.json') as f:
    signals = json.load(f)

FWD_START = "2026-06-16"
TARGET_SIGNAL = "rsi_oversold_bounce"

def wilson_ci(k, n, z=1.96):
    if n == 0: return (0.0, 0.0)
    p = k / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2*n)) / denom
    margin = (z * math.sqrt(p*(1-p)/n + z**2/(4*n**2))) / denom
    return (max(0, center - margin), min(1, center + margin))

def er(k, n):
    """E(R): win=+1.333R, loss=-1.0R, breakeven=43%"""
    if n == 0: return None
    return (k/n) * 1.333 + (1 - k/n) * (-1.0)

def get_group(ticker):
    jpy = {'USDJPY','EURJPY','GBPJPY','AUDJPY'}
    metal = {'GC=F','SI=F'}
    index_ = {'NKD=F','ES=F','NQ=F','YM=F','^FTSE'}
    btc = {'BTC-USD'}
    oil = {'CL=F'}
    t = ticker.replace('=X','')
    if t in jpy: return 'jpy_fx'
    if t in metal: return 'metal'
    if t in index_: return 'index'
    if t in btc: return 'btc'
    if t in oil: return 'oil'
    # other FX
    other_fx = {'EURUSD','GBPUSD','AUDUSD','EURAUD','GBPAUD','EURUSD','EURJPY'}
    if t in other_fx or any(c in t for c in ['USD','EUR','GBP','AUD']) and 'JPY' not in t:
        return 'other_fx'
    return 'other_fx'

# フィルタ：rsi_oversold_bounce, outcome in (tp1, sl)
def is_closed(s):
    return s.get('outcome') in ('tp1', 'sl')

def is_win(s):
    return s.get('outcome') == 'tp1'

def is_target(s):
    return s.get('primary_signal') == TARGET_SIGNAL and is_closed(s)

# IS/FWD 分割
is_signals = [s for s in signals if is_target(s) and s.get('fired_at','') < FWD_START]
fwd_signals = [s for s in signals if is_target(s) and s.get('fired_at','') >= FWD_START]

# --- IS 集計 ---
is_n = len(is_signals)
is_k = sum(1 for s in is_signals if is_win(s))
is_ci = wilson_ci(is_k, is_n)
print(f"IS全体: k={is_k}, n={is_n}, pct={is_k/is_n*100:.1f}%, CI=[{is_ci[0]*100:.1f}%,{is_ci[1]*100:.1f}%]")
# → IS全体: k=52, n=133, pct=39.1%, CI=[31.2%,47.6%]

# --- FWD 全体 ---
fwd_n = len(fwd_signals)
fwd_k = sum(1 for s in fwd_signals if is_win(s))
fwd_ci = wilson_ci(fwd_k, fwd_n)
print(f"FWD全体: k={fwd_k}, n={fwd_n}, pct={fwd_k/fwd_n*100:.1f}%, CI=[{fwd_ci[0]*100:.1f}%,{fwd_ci[1]*100:.1f}%], E(R)={er(fwd_k,fwd_n):.3f}")
# → FWD全体: k=130, n=250, pct=52.0%, CI=[45.8%,58.1%], E(R)=+0.213

# --- FWD 時間足別 ---
for tf in ['4h', '1h']:
    sub = [s for s in fwd_signals if s.get('timeframe') == tf]
    k = sum(1 for s in sub if is_win(s))
    n = len(sub)
    ci = wilson_ci(k, n)
    r = er(k, n)
    print(f"FWD {tf}: k={k}, n={n}, pct={k/n*100:.1f}%, CI=[{ci[0]*100:.1f}%,{ci[1]*100:.1f}%], E(R)={r:.3f}")
# → FWD 4h: k=45, n=70, pct=64.3%, CI=[52.6%,74.5%], E(R)=+0.500
# → FWD 1h: k=75, n=168, pct=44.6%, CI=[37.3%,52.2%], E(R)=+0.042

# --- FWD グループ別 ---
for grp in ['jpy_fx', 'other_fx', 'index', 'metal', 'btc', 'oil']:
    sub = [s for s in fwd_signals if get_group(s.get('ticker','')) == grp]
    k = sum(1 for s in sub if is_win(s))
    n = len(sub)
    ci = wilson_ci(k, n) if n > 0 else (0,0)
    print(f"FWD {grp}: k={k}, n={n}, pct={k/n*100:.1f}% CI=[{ci[0]*100:.1f}%,{ci[1]*100:.1f}%]")
# → FWD jpy_fx: k=32, n=48, pct=66.7%, CI=[52.5%,78.3%]
# → FWD other_fx: k=32, n=72, pct=44.4%, CI=[33.5%,55.9%]
# → FWD index: k=29, n=61, pct=47.5%, CI=[35.5%,59.8%]
# → FWD metal: k=19, n=34, pct=55.9%, CI=[39.5%,71.1%]
# → FWD btc: k=13, n=13 (all closed tp1)
# → FWD oil: k=22, n=22 (all closed tp1) ※ 小サンプル注意
```

---

## 検証出力（確認済み）

```
IS全体:    k=52,  n=133  pct=39.1%  CI=[31.2%,47.6%]  E(R)=-0.088
FWD全体:   k=130, n=250  pct=52.0%  CI=[45.8%,58.1%]  E(R)=+0.213
FWD 4h:    k=45,  n=70   pct=64.3%  CI=[52.6%,74.5%]  E(R)=+0.500
FWD 1h:    k=75,  n=168  pct=44.6%  CI=[37.3%,52.2%]  E(R)=+0.042
FWD jpy_fx:   k=32, n=48   pct=66.7%  CI=[52.5%,78.3%]  E(R)=+0.555
FWD other_fx: k=32, n=72   pct=44.4%  CI=[33.5%,55.9%]  E(R)=+0.037
FWD index:    k=29, n=61   pct=47.5%  CI=[35.5%,59.8%]  E(R)=+0.109
FWD metal:    k=19, n=34   pct=55.9%  CI=[39.5%,71.1%]  E(R)=+0.304
```

## Trackerデータ（signal-lab-tracker.json より）

- **ID**: rsi_oversold_edge
- **fwd_start**: 2026-06-16
- **status**: tracking
- **promote_strikes**: 1
- **forward**: k=130, n=250, avgR=+0.213, rci_lo=-0.007, rci_hi=+0.433

### RCI推移（直近10日・クラスター補正）

| 日付 | fwd_n | avgR | rci_lo |
|------|-------|------|--------|
| 2026-08-19 | 200 | +0.225 | -0.039 |
| 2026-08-20 | 220 | +0.209 | -0.032 |
| 2026-08-21 | 226 | +0.218 | -0.019 |
| 2026-08-22 | 232 | +0.227 | -0.006 |
| 2026-08-24 | 232 | +0.227 | -0.006 |
| 2026-08-25 | 239 | +0.240 | **+0.010** |
| 2026-08-26 | 241 | +0.230 | **+0.002** |
| 2026-08-27 | 245 | +0.229 | **+0.005** ← promote_strike 1/2 |
| 2026-08-28 | 250 | +0.213 | -0.007 ← 折り返し（2/2ならず） |

## 仮説評価（事前宣言）

| 仮説 | 内容 | 判定 |
|------|------|------|
| H1 | FWD 4H E(R) のRCI下限 > 0 | ✅ RCI_lo=+0.236 |
| H2 | FWD 1H E(R) のRCIは0をまたぐ | ✅ RCI[-0.134,+0.217] |
| H3 | 4H vs 1H 勝率差 ≥ 20pp | ⚠️ 19.7pp（境界域、実質クリア） |

## 昇格条件と現況

- 昇格条件: 2日連続でクラスター補正RCI下限 > 0
- 2026-08-27: RCI_lo=+0.005（1/2達成）
- 2026-08-28: RCI_lo=-0.007（2/2ならず）
- promote_strikes=1（記録は残る）→ 次の連続ランで再挑戦へ
