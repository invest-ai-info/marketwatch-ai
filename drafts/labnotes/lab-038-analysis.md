# lab-038-analysis.md
# 仮説: tier=good gate の IS/FWD 乖離解析
# 生成日: 2026-07-13 JST

## 使用スクリプト

```python
import json, math

with open('signals-log.json') as f:
    data = json.load(f)

closed = [s for s in data if s.get('outcome') in ['tp1','tp2','sl']]
with_sel = [s for s in closed if 'selection' in s]

GROUP_MAP = {
    'GC=F': 'metal', 'SI=F': 'metal',
    'NKD=F': 'index', 'ES=F': 'index', 'NQ=F': 'index', 'YM=F': 'index', '^FTSE': 'index',
    'BTC-USD': 'btc', 'CL=F': 'oil',
    'USDJPY': 'jpy_fx', 'EURJPY': 'jpy_fx', 'GBPJPY': 'jpy_fx', 'AUDJPY': 'jpy_fx',
    'EURUSD': 'other_fx', 'GBPUSD': 'other_fx', 'AUDUSD': 'other_fx',
    'EURAUD': 'other_fx', 'GBPAUD': 'other_fx',
}

def wilson_ci(k, n, z=1.96):
    if n == 0: return (0.0, 0.0)
    p = k/n
    denom = 1 + z**2/n
    center = (p + z**2/(2*n))/denom
    margin = (z*math.sqrt(p*(1-p)/n + z**2/(4*n**2)))/denom
    return (max(0, center-margin), min(1, center+margin))

def mean_r_ci(rs):
    if not rs: return (0.0, 0.0, 0.0)
    n = len(rs)
    mean = sum(rs)/n
    if n < 2: return (mean, mean, mean)
    variance = sum((r-mean)**2 for r in rs) / (n-1)
    se = math.sqrt(variance/n)
    t = 2.0 if n < 30 else 1.96
    return (mean, mean - t*se, mean + t*se)

# E(R) with TP1/SL ratio = 2.0/1.5 = 1.333
def er(k, n):
    if n == 0: return 0.0
    p = k/n
    return p * 1.333 + (1-p) * (-1.0)

# Registration dates from signal-lab-tracker.json:
# tier=good gate: 2026-06-25
# tier=neutral gate: 2026-06-22
# tier=avoid gate: 2026-06-25 (同スイープ登録日)
# tier=elite: 未登録（比較参照のみ）

reg_good = '2026-06-25'
reg_neutral = '2026-06-22'
reg_avoid = '2026-06-25'
```

## 生出力

### 1. データ規模
- 全決済済みシグナル: 1,567件
- selection 付き: 1,241件（2026-06-04〜2026-07-12）

### 2. tier=good IS vs FWD 分解

**IS期間（〜2026-06-25, N=196）**
- 全体: 68/196 = 34.7% E(R)≈-0.190
- metal IS: 4/29 = 13.8% E(R)=-0.678
- index IS: 27/62 = 43.5% E(R)=-0.129
- oil IS: 1/8 = 12.5% E(R)=-0.708
- btc IS: 3/6 = 50.0% E(R)=0.000

**FWD期間（2026-06-25以降, N=67）**
- 全体: 46/67 = 68.7% E(R)=+0.603 (tracker CI[+0.38~+0.82])
- metal FWD: 7/11 = 63.6% E(R)=+0.273 (+49.8pp from IS!)
- index FWD: 13/19 = 68.4% E(R)=+0.368 (+24.9pp)
- btc FWD: 6/7 = 85.7% E(R)=+0.714 (N小・注意)
- oil FWD: 3/6 = 50.0% E(R)=0.000 (+37.5pp)
- jpy_fx: N=0 (both IS and FWD) — tier=goodに円FXシグナルは出ない

**N=67→80の残り: 13件**

### 3. tier=neutral FWD（N=187 >> 80）

登録日: 2026-06-22
- IS: 74/218 = 33.9% E(R)=-0.321
- FWD: 72/187 = 38.5% CI[31.8%,45.6%] E(R)=-0.102 (tracker: R=-0.102 CI[-0.25~+0.04])
- N=187 ≥ 80だがCI上限+0.04>0→trackerでは⛔反証未確定（蓄積中）
- IS負→FWD負継続（gate方向を確認）

### 4. tier=avoid FWD（N=206 >> 80）

登録日: 2026-06-25 (仮定)
- IS: 101/209 = 48.3% E(R)=-0.033
- FWD: 76/206 = 36.9% CI[30.6%,43.7%] E(R)=-0.139
- IS期間は相対的に高め（名前と一致しない逆説）、FWDでは36.9%に悪化

### 5. tier=elite FWD（N=54）

登録日: 2026-06-25
- IS: 49/104 = 47.1% E(R)=-0.058
- FWD: 28/54 = 51.9% CI[38.9%,64.6%] E(R)=+0.037 (軽微プラス・有意差なし)

### 6. tier=good 全期間内訳（claims.json 用）

| tier | k | n | 勝率 | Wilson CI |
|---|---|---|---|---|
| elite | 77 | 158 | 48.7% | [41.1%,56.5%] |
| good | 114 | 263 | 43.3% | [37.5%,49.4%] |
| neutral | 146 | 405 | 36.0% | [31.5%,40.8%] |
| avoid | 177 | 415 | 42.7% | [38.0%,47.5%] |

tier=good グループ別（全期間）:
| group | k | n | 勝率 |
|---|---|---|---|
| metal | 11 | 40 | 27.5% |
| index | 40 | 81 | 49.4% |
| btc | 9 | 13 | 69.2% |
| oil | 4 | 14 | 28.6% |
| jpy_fx | 0 | 0 | N/A |
| other_fx | 0 | 0 | N/A |

tier=good シグナル別（全期間）:
| signal | k | n | 勝率 |
|---|---|---|---|
| bb_lower_touch | 54 | 127 | 42.5% |
| rsi_oversold_bounce | 47 | 113 | 41.6% |
| macd_dead | 9 | 12 | 75.0% |
| macd_golden | 4 | 10 | 40.0% |

tier=good 方向別（全期間）:
| direction | k | n | 勝率 |
|---|---|---|---|
| long | 105 | 251 | 41.8% |
| short | 9 | 12 | 75.0% |

### 7. 交絡点検

- **金属レジーム交絡**: IS 13.8%→FWD 63.6% の急騰は#030/#032で確認された金属レジーム転換と完全一致。tier=good×metalの不毛期（IS）が全体IS34.7%を作った主因
- **構成シフト**: FWD期間にjpy_fx/other_fxが0件。これはFX系シグナルがtier=goodに分類されにくいことを示す（#016 other_fx ロング weaknessと一致）
- **サンプルサイズ**: FWD N=67 < 80（昇格基準未達）。BTC 6/7は小サンプル過信禁止
- **多重比較**: スイープ通過は全既登録候補（FDR新規なし）

### 8. 前向きトラッカー確認（2026-07-13 update結果）

| 仮説 | 登録日 | FWD k/n | 勝率 | E(R) CI | 状態 |
|---|---|---|---|---|---|
| tier=good (gate) | 2026-06-25 | 46/67 | 69% | [+0.38~+0.82] | 🟡蓄積中 (N=67<80) |
| tier=neutral (gate) | 2026-06-22 | 72/187 | 38% | [-0.25~+0.04] | 🟡蓄積中 |
| 指数×ロング(全足ライブ) | 2026-06-12 | 88/163 | 54% | [+0.00~+0.52] | ✅昇格 |
| dir=long (gate) | 2026-06-25 | 157/352 | 45% | [-0.13~+0.21] | ⛔反証 |
| reversalL (gate) | 2026-06-25 | 72/126 | 57% | [+0.11~+0.56] | ⛔反証 |
