# lab-015 分析ノート — 4H足ロングの系統的アンダーパフォーマンス（時間足効果の検証）

**基準日**: 2026-06-20  
**担当**: signal-lab-daily routine / main Claude orchestrator

---

## スイープ結果（2026-06-20）

`python signal_lab_sweep.py --json drafts/labnotes/sweep-2026-06-20.json` 実行結果より：

- **FDR黒字通過 2本**: group=index×dir=long (R+0.25, q=0.048), trend=中立・もみあい×dir=short (R+0.43, q=0.046)
- **FDR赤字通過 7本**: group=metal×dir=long (R-0.56), group=metal (R-0.37), group=metal×reversalL (R-0.50),  
  trend=下降×dir=short (R-0.36), trend=中立・もみあい×dir=long (R-0.20),  
  group=other_fx×dir=long (R-0.23), **tf=4h×dir=long (R-0.18, q=0.059)** ← 新規FDR通過

**今日の新規登録**: tf=4h×dir=long (gate, 2026-06-20)

---

## トラッカー更新（2026-06-20）

`python signal_lab_tracker.py update --date 2026-06-20` 実行結果：

- 昇格・反証なし（全19エントリ 🟡蓄積中）
- 注目: 指数×ロング(全足ライブ) 前向き 29/43=67%, 平均R+0.574 CI[+0.24~+0.90] — 蓄積順調
- trend=中立・もみあい×dir=short 前向き 8/14=57%, 平均R+0.333 — N不足・継続
- tf=4h×dir=long 本日新規登録 (前向き 0/0)

---

## #015 採択仮説

**「4H足ロングシグナルは1H足ロングより系統的に勝率が低いか」**

### 採択理由

優先度③（スイープFDR通過の新候補）に該当。  
tf=4h×dir=long が本日 FDR q=0.059 で初めて統計的赤字通過（R=-0.18）。  
verify.py 対応フィルタキー（tf, direction, group）で全クレームを表現可能。  
1H vs 4H という実用的な比較（どちらを優先すべきか）で投資家への価値が高い。

### 事前宣言基準

1. **主仮説（棄却確認）**: 4H×L の勝率95%CI上限 < 43.0% → 棄却確定
2. **交絡検定**: 金属比率の差 < 5%pp かつ 金属除外後も 4H×L < 1H×L
3. **副仮説**: jpy_fx グループでの時間足差 > 10pp（探索的）

---

## 検証スクリプト

```python
#!/usr/bin/env python3
# lab-015 反実仮想集計スクリプト
import json, math
from collections import Counter

with open('signals-log.json') as f:
    data = json.load(f)
signals = data if isinstance(data, list) else data.get('signals', [])

USABLE = {'tp1', 'tp2', 'sl'}
closed = [s for s in signals if s.get('outcome') in USABLE]
# → 883件

def get_r(s):
    o = s.get('outcome')
    if o == 'tp1': return 1.33
    if o == 'tp2': return 2.0
    if o == 'sl': return -1.0
    return None

def wilson_ci(k, n, z=1.96):
    if n == 0: return (0.0, 0.0)
    p = k/n
    denom = 1 + z**2/n
    center = (p + z**2/(2*n)) / denom
    margin = z * math.sqrt(p*(1-p)/n + z**2/(4*n**2)) / denom
    return (max(0, center-margin), min(1, center+margin))

def mean_ci(vals, z=1.96):
    n = len(vals)
    if n < 2: return (0, 0)
    m = sum(vals)/n
    s2 = sum((x-m)**2 for x in vals)/(n-1)
    se = math.sqrt(s2/n)
    return (m - z*se, m + z*se)

def group_of2(s):
    t = s.get('ticker','').replace('=X','')
    if t in ('GC=F','SI=F'): return 'metal'
    if t == 'CL=F': return 'oil'
    if t in ('NKD=F','ES=F','NQ=F','YM=F','^FTSE'): return 'index'
    if t == 'BTC-USD': return 'btc'
    if t in ('USDJPY','EURJPY','GBPJPY','AUDJPY'): return 'jpy_fx'
    if t in ('EURUSD','GBPUSD','AUDUSD','EURAUD','GBPAUD'): return 'other_fx'
    return 'unknown'

def analyze(subs, label):
    rs = [get_r(s) for s in subs if get_r(s) is not None]
    k = sum(1 for r in rs if r > 0)
    n = len(rs)
    if n == 0: return
    ci_lo, ci_hi = wilson_ci(k, n)
    avg_r = sum(rs)/n
    rci = mean_ci(rs)
    print(f'{label}: N={n} k={k} 勝率={k/n:.1%} CI=[{ci_lo:.1%},{ci_hi:.1%}] avgR={avg_r:+.3f}[{rci[0]:+.3f}~{rci[1]:+.3f}]')

is_long  = lambda s: 'ロング' in s.get('direction','') or 'long'  in s.get('direction','').lower()
is_short = lambda s: 'ショート' in s.get('direction','') or 'short' in s.get('direction','').lower()

long_1h  = [s for s in closed if s.get('timeframe')=='1h' and is_long(s)]
long_4h  = [s for s in closed if s.get('timeframe')=='4h' and is_long(s)]
short_1h = [s for s in closed if s.get('timeframe')=='1h' and is_short(s)]
short_4h = [s for s in closed if s.get('timeframe')=='4h' and is_short(s)]
```

---

## 生出力

```
Usable closed signals: 883

=== 時間足×方向 基本比較 ===
1H×ロング: N=367 k=148 勝率=40.3% CI=[35.4%,45.4%] avgR=-0.060[-0.177~+0.057]
4H×ロング: N=273 k=96 勝率=35.2% CI=[29.7%,41.0%] avgR=-0.181[-0.313~-0.048]
1H×ショート: N=122 k=49 勝率=40.2% CI=[31.9%,49.0%] avgR=-0.064[-0.268~+0.139]
4H×ショート: N=108 k=54 勝率=50.0% CI=[40.7%,59.3%] avgR=+0.165[-0.056~+0.386]

=== 4H×ロング グループ内訳（=X修正後）===
4H x L x metal: N=40 k=8 勝率=20.0% CI=[10.5%,34.8%] avgR=-0.534[-0.827~-0.241]
4H x L x index: N=70 k=36 勝率=51.4% CI=[40.0%,62.8%] avgR=+0.198[-0.076~+0.473]
4H x L x jpy_fx: N=47 k=14 勝率=29.8% CI=[18.7%,44.0%] avgR=-0.306[-0.614~+0.002]
4H x L x other_fx: N=80 k=27 勝率=33.8% CI=[24.3%,44.6%] avgR=-0.214[-0.457~+0.029]
4H x L x btc: N=24 k=7 勝率=29.2% CI=[14.9%,49.2%] avgR=-0.320[-0.753~+0.112]
4H x L x oil: N=12 k=4 勝率=33.3% CI=[13.8%,60.9%] avgR=-0.223[-0.872~+0.426]

=== 1H×ロング グループ内訳（=X修正後）===
1H x L x metal: N=49 k=7 勝率=14.3% CI=[7.1%,26.7%] avgR=-0.667[-0.898~-0.436]
1H x L x index: N=91 k=49 勝率=53.8% CI=[43.7%,63.7%] avgR=+0.255[+0.015~+0.495]
1H x L x jpy_fx: N=76 k=37 勝率=48.7% CI=[37.8%,59.7%] avgR=+0.134[-0.129~+0.398]
1H x L x other_fx: N=109 k=36 勝率=33.0% CI=[24.9%,42.3%] avgR=-0.230[-0.437~-0.024]
1H x L x btc: N=28 k=8 勝率=28.6% CI=[15.3%,47.1%] avgR=-0.334[-0.731~+0.063]
1H x L x oil: N=14 k=11 勝率=78.6% CI=[52.4%,92.4%] avgR=+0.831[+0.311~+1.350]

=== 金属除外後（=X修正後）===
4H x L (金属除外): N=233 k=88 勝率=37.8% CI=[31.8%,44.1%] avgR=-0.120[-0.265~+0.025]
1H x L (金属除外): N=318 k=141 勝率=44.3% CI=[39.0%,49.8%] avgR=+0.033[-0.094~+0.161]

=== グループ分布（=X修正後）===
4H x L groups:
  other_fx: 80 (29.3%)
  index: 70 (25.6%)
  jpy_fx: 47 (17.2%)
  metal: 40 (14.7%)
  btc: 24 (8.8%)
  oil: 12 (4.4%)
1H x L groups:
  other_fx: 109 (29.7%)
  index: 91 (24.8%)
  jpy_fx: 76 (20.7%)
  metal: 49 (13.4%)
  btc: 28 (7.6%)
  oil: 14 (3.8%)

金属比率差: 4H=14.7%, 1H=13.4% → 差=1.3%（5pp未満 → 交絡要因として否定）

=== 4H ショート 詳細 ===
4H x S x metal: N=22 k=11 勝率=50.0% CI=[30.7%,69.3%]
4H x S x index: N=25 k=12 勝率=48.0% CI=[30.0%,66.5%]
4H x S x jpy_fx: N=19 k=7 勝率=36.8% CI=[19.1%,59.0%]
4H x S x other_fx: N=23 k=14 勝率=60.9% CI=[40.8%,77.8%]
4H x S x btc: N=11 k=8 勝率=72.7% CI=[43.4%,90.3%]
4H x S x oil: N=8 k=2 勝率=25.0% CI=[7.1%,59.1%]
```

---

## 事前基準評価

| 基準 | 判定 |
|---|---|
| 4H×L のCI上限 < 43% | ✅ 達成: CI上限41.0% < 43% → **棄却確定** |
| 金属比率差 < 5pp | ✅ 達成: 差1.3pp（交絡否定） |
| 金属除外後も4H×L < 1H×L | ✅ 達成: 37.8% vs 44.3%（6.5pp差継続） |
| jpy_fx での時間足差 > 10pp | ✅ 達成: 4H=29.8% vs 1H=48.7%（+18.9pp） |

**総合判定**: 全4条件クリア → 通過A（棄却確認）

---

## 交絡点検チェックリスト

- [x] 金属比率の偏り → 1.3pp差 → 否定済み
- [x] 時間足によるグループ構成差 → 分布ほぼ同一（other_fx 29%台、index 25%台）
- [x] 4H足の方向別非対称性 → ロング35.2% vs ショート50.0% → 4H足は方向依存
- [x] jpy_fx での1H優位性 → 4H=29.8% vs 1H=48.7%（18.9pp）の主因候補
- [ ] (未解明) なぜ jpy_fx の 4H ロングが特に弱いのか → 次回候補（#016?）

---

## 前向きトラッカー登録

- tf=4h×dir=long が本日 gate として登録済み（sweep→register）
- 昇格基準: 前向きN≥80 かつ avgR の CI 上限 < 0
