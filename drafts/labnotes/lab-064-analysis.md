# AIシグナル研究日誌 #064 — 分析ノート
**日付**: 2026-08-08 (JST)
**テーマ**: 金属ロングgate 降格候補確認 — 前向きN=177でCI上限+0.16（2回目），後期56%の加速解析

## 使用スクリプト

```python
import json, math

with open('signals-log.json') as f:
    signals = json.load(f)

GROUPS = {
    'metal': {'GC=F', 'SI=F'},
    'index': {'NKD=F', 'ES=F', 'NQ=F', 'YM=F', '^FTSE'},
    'jpy_fx': {'USDJPY=X', 'EURJPY=X', 'GBPJPY=X', 'AUDJPY=X'},
    'other_fx': {'EURUSD=X', 'GBPUSD=X', 'AUDUSD=X', 'EURAUD=X', 'GBPAUD=X'},
    'btc': {'BTC-USD'},
    'oil': {'CL=F'},
}
EXT_TICKERS = {'HG=F','PL=F','NG=F','RBOB=F','ZN=F','ZB=F','ETH-USD','SOL-USD','^GDAXI','^HSI','^SOX'}

def get_group(s):
    ticker = s.get('ticker', '')
    for g, tickers in GROUPS.items():
        if ticker in tickers:
            return g
    return 'unknown'

def is_closed(s):
    return s.get('outcome') in ('tp1', 'sl', 'expired')

def is_win(s):
    return s.get('outcome') == 'tp1'

def get_r(s):
    oc = s.get('outcome')
    if oc == 'tp1': return 1.33
    elif oc == 'sl': return -1.0
    elif oc == 'expired': return -0.5
    return None

def wilson_ci(k, n, z=1.96):
    if n == 0: return (0, 0)
    p = k/n
    denom = 1 + z**2/n
    center = (p + z**2/(2*n))/denom
    margin = (z * math.sqrt(p*(1-p)/n + z**2/(4*n**2)))/denom
    return (max(0, center-margin), min(1, center+margin))

def r_ci(rs, z=1.96):
    if not rs: return (0, 0, 0)
    n = len(rs)
    mean = sum(rs)/n
    if n < 2: return (mean, mean, mean)
    var = sum((r-mean)**2 for r in rs)/(n-1)
    se = math.sqrt(var/n)
    return (mean, mean-z*se, mean+z*se)

closed = [s for s in signals if is_closed(s)]
fwd_start = '2026-06-17'  # gate registration date (#039)
```

## 生出力

### 全期間・基本統計
```
Total closed all: 2737

metal×long ALL (any TF, any date): N=263
k=89, win=33.8%, Wilson CI[28.4%,39.8%]
E(R)=-0.210 RCI[-0.343,-0.076]

metal×long (no 1d): N=248
k=85, win=34.3%, Wilson CI[28.6%,40.4%]
E(R)=-0.201 RCI[-0.339,-0.063]

GC=F long ALL: N=140, k=48, win=34.3%
SI=F long ALL: N=123, k=41, win=33.3%

By TF (all period):
  1h N=136 k=39 28.7% E(R)=-0.332 RCI[-0.51,-0.15]
  4h N=112 k=46 41.1% E(R)=-0.043 RCI[-0.26,0.17]
  1d N=15  k=4  26.7% E(R)=-0.345 RCI[-0.88,0.19]

By signal (all period, top signals):
  bb_lower_touch    N=77  k=27 35.1% E(R)=-0.183 RCI[-0.43,0.07]
  rsi_oversold      N=61  k=19 31.1% E(R)=-0.266 RCI[-0.54,0.01]
  macd_golden       N=53  k=16 30.2% E(R)=-0.297 RCI[-0.59,-0.01]
  high_break        N=18  k=5  27.8% E(R)=-0.353 RCI[-0.85,0.14]
  bb_upper_break    N=16  k=7  43.8% E(R)=+0.019 RCI[-0.57,0.60]
  ma_golden         N=12  k=4  33.3% E(R)=-0.223 RCI[-0.87,0.43]

metal×short ALL: N=100, k=45, win=45.0%, E(R)=0.049 RCI[-0.18,0.28]
```

### IS vs FWD 分解
```
FWD (fired_at >= 2026-06-17): N=177
k=75, win=42.4%, Wilson CI[35.3%,49.7%]
E(R)=-0.010 RCI[-0.180,+0.160]

Time-period breakdown (FWD):
  初期(前1/3): N=59, k=21, 36%
  中期(中1/3): N=59, k=21, 36%
  後期(後1/3): N=59, k=33, 56%  ← +20pp加速

TF=1h FWD: N=90, k=34, 38%, E(R)=-0.120 RCI[-0.35,0.11]
TF=4h FWD: N=76, k=39, 51%, E(R)=+0.196 RCI[-0.07,0.46]

rsi_oversold_bounce FWD: N=30, k=15, 50% E(R)=+0.182 RCI[-0.24,0.60]

GC=F FWD: N=86, k=38, 44%
SI=F FWD: N=91, k=37, 41%

IS (before 2026-06-17): N=86, k=14, 16.3%, E(R)=-0.621 RCI[-0.80,-0.44]
```

### tracker値（signal_lab_tracker.py より）
```
group=metal×dir=long ✅昇格
  前向き現在値: 75/176=43%, 平均R -0.01, CI[-0.29~+0.28]
  （※ trackerはcluster補正CI使用のため独自計算より幅広）
```

## 仮説・事前宣言

「group=metal×dir=long gate（2026-06-17昇格・gate条件=前向きCI上限<0）は、
降格ルール2回目チェックポイントを満たしたか。また、FWD後期(後1/3)の56%は
金属レジーム転換の継続を示すか」

### 事前宣言条件（確認前に固定）
- H1: 前向きCI上限 > 0 → gate条件未達が2回目 ← YES (+0.16 or +0.28)
- H2: FWD後期(後1/3) > FWD前期(前1/3) ← YES (56% > 36%)

### 降格ルール経緯
- Gate確認: N=86 (2026-07-14, #039) CI上限<0 ✅
- 1回目基準割れ: N=156 (#058, 2026-08-02) tracker CI upper +0.17 > 0
- 2回目基準割れ: N=177 (本日) tracker CI upper +0.28 > 0 / 独立計算 +0.16 > 0

### 結論
- H1 ✅ 達成（CI上限>0 が2回連続）
- H2 ✅ 達成（後期56% > 前期36%）
- 降格ルール2回目基準を満たした → 降格候補として記録
- ただしtrackerは🟡ではなく依然✅昇格 → 人間の最終判断が必要
