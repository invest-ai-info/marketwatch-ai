# 研究日誌 #095 解析ノート — 2026-09-11

## 仮説採択理由

優先度②（前向きトラッカー大変動）：
- `売られすぎ逆張り買い(rsi_oversold_bounce・全足)` edge
- 直前 #091(2026-09-07) での FWD N=296 CI[+0.05 cluster補正] → 本日 N=332 CI[-0.01 cluster補正] に転落
- 昇格ストライク1 (promote_strikes=1) がリセット → promote_strikes=0 に戻った
- スイープFDR通過0本、新規✅昇格/⛔反証なし

## Python集計スクリプト

```python
import json, math
from collections import defaultdict

with open('signals-log.json') as f:
    signals = json.load(f)

GROUPS = {
    "metal": {"GC=F","SI=F"},
    "index": {"NKD=F","ES=F","NQ=F","YM=F","^FTSE"},
    "jpy_fx": {"USDJPY=X","EURJPY=X","GBPJPY=X","AUDJPY=X"},
    "other_fx": {"EURUSD=X","GBPUSD=X","AUDUSD=X","EURAUD=X","GBPAUD=X"},
    "btc": {"BTC-USD"},
    "oil": {"CL=F"},
}

def get_group(ticker):
    for g, ts in GROUPS.items():
        if ticker in ts: return g
    return 'other'

def win(s): return s.get('outcome') in ('tp1','tp2')
def r_mult(s):
    o = s.get('outcome','')
    if o == 'tp2': return 2.0
    if o == 'tp1': return 1.33
    if o == 'sl': return -1.0
    if o == 'expired': return -0.5
    return 0.0

def wilson_ci(k, n, z=1.96):
    if n == 0: return 0.0, 1.0
    p = k/n
    a = p + z*z/(2*n)
    b = z * math.sqrt((p*(1-p)+z*z/(4*n))/n)
    c = 1 + z*z/n
    return (a-b)/c, (a+b)/c

def matches(s, f):
    outcome = s.get('outcome','')
    if outcome not in ('tp1','tp2','sl','expired'): return None
    if 'signal' in f:
        if s.get('primary_signal') != f['signal']: return False
    if 'direction' in f:
        d = f['direction']
        sd = s.get('direction','') or ''
        if d=='long' and not sd.startswith('ロング'): return False
    if 'group' in f:
        g = f['group']
        if g != 'all' and get_group(s.get('ticker','')) != g: return False
    if 'tf' in f:
        if s.get('timeframe') != f['tf']: return False
    if 'fired_from' in f:
        fa = s.get('fired_at','')
        if not fa or not (fa >= f['fired_from']): return False
    if 'fired_before' in f:
        fa = s.get('fired_at','')
        if not fa or not (fa < f['fired_before']): return False
    return True

def compute(f):
    matched = [s for s in signals if matches(s,f) is True]
    n = len(matched)
    k = sum(win(s) for s in matched)
    r = sum(r_mult(s) for s in matched)/n if n > 0 else 0
    lo, hi = wilson_ci(k, n)
    return k, n, r, lo, hi
```

## 生出力（検証済み）

### シグナル検索
```
Total signals: 5452
rsi_oversold_bounce long closed: 465
  2026-05: 15  (IS)
  2026-06: 192 (IS=118, FWD=74)
  2026-07: 91  (FWD)
  2026-08: 105 (FWD)
  2026-09: 62  (FWD)

IS boundary: fired_at <= 2026-06-15 → N=133
FWD boundary: fired_at >= 2026-06-17 → N=332
```

### 全Claims計算結果

```
IS（N=133）:              k=52  n=133  39.1%  E(R)=-0.089  CI[31.2%,47.6%]
FWD全体（N=332）:         k=163 n=332  49.1%  E(R)=+0.153  CI[43.8%,54.5%]
FWD pre-Sep（N=270）:     k=140 n=270  51.9%  E(R)=+0.219  CI[45.9%,57.7%]
FWD 9月（N=62）:          k=23  n=62   37.1%  E(R)=-0.136  CI[26.2%,49.5%]
FWD 9月4日以降（N=38）:   k=10  n=38   26.3%  E(R)=-0.387  CI[15.0%,42.0%]
FWD 4H足（N=102）:        k=57  n=102  55.9%  E(R)=+0.317  CI[46.2%,65.1%]
FWD 1H足（N=214）:        k=96  n=214  44.9%  E(R)=+0.045  CI[38.3%,51.6%]
FWD jpy_fx（N=90）:       k=42  n=90   46.7%  E(R)=+0.104  CI[36.7%,56.9%]
FWD metal（N=42）:        k=23  n=42   54.8%  E(R)=+0.288  CI[39.9%,68.8%]
FWD other_fx（N=93）:     k=46  n=93   49.5%  E(R)=+0.163  CI[39.5%,59.4%]
FWD index（N=72）:        k=34  n=72   47.2%  E(R)=+0.100  CI[36.1%,58.6%]
FWD 9月 jpy_fx（N=39）:   k=10  n=39   25.6%  E(R)=-0.403  CI[14.6%,41.1%]
FWD 9月4日以降 jpy_fx:    k=10  n=34   29.4%  E(R)=-0.315  CI[16.8%,46.2%]
FWD 4H×jpy_fx（N=31）:   k=16  n=31   51.6%  E(R)=+0.235  CI[34.8%,68.0%]
```

### 直近38件の詳細（fired_from=2026-09-04）
```
2026-09-04 AUDJPY=X 1h tp1 +1.33R
2026-09-04 USDJPY=X 4h sl  -1.00R
2026-09-04 EURJPY=X 4h sl  -1.00R
2026-09-04 GBPJPY=X 4h sl  -1.00R
2026-09-04 AUDJPY=X 4h sl  -1.00R
2026-09-04 USDJPY=X 1h tp1 +1.33R
2026-09-04 EURJPY=X 1h sl  -1.00R
2026-09-04 GBPJPY=X 1h sl  -1.00R
2026-09-04 USDJPY=X 1h tp1 +1.33R
2026-09-04 AUDJPY=X 1h tp1 +1.33R
... (9/5以降も大半がjpy_fx SL)
summary: 10/38=26.3%, jpy_fx 10/34=29.4%, index 0/4=0.0%
```

## 仮説検証判定

| 仮説 | 内容 | 結果 | 判定 |
|---|---|---|---|
| H1 | 9月FWD勝率が損益分岐43%以下 | 37.1%<43% | ✅ |
| H2 | FWD CI下限が昇格未達（tracker cluster補正でマイナス） | CI[-0.01~+0.35] | ✅ |
| H3 | 9月主犯はjpy_fx（25%以下） | 25.6% | ✅ |

## 交絡考察

1. **TF非対称**: 4H=55.9% vs 1H=44.9% の11pp差は全期間で継続
2. **9月の主犯**: jpy_fx 9月25.6%（対比pre-Sep 46.7%から-21pp急落）
3. **4H×jpy_fx は51.6%**: 4H足はjpy_fxでも一定の優位を維持（N=31小）
4. **金属/BTC/oil は健全**: metal54.8%, btc53.8%, oil50%
5. **9月失速の原因推定**: 円高方向の動き（リスクオフ）がRSI売られすぎからの反発を封じた可能性

## FDR / トラッカー変化

- スイープFDR: 0本（新規なし）
- トラッカー変化: rsi_oversold_bounce promote_strikes: 1→0（CI下限マイナス転落）
- trend=上昇×reversalL: demote_strikes継続中（CI[-0.03~+0.29]）
