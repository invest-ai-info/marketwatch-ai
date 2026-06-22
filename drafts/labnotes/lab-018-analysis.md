# Lab 018 — 分析ノート（2026-06-22）

## 仮説
**指数グループ（NKD=F / ES=F / NQ=F / YM=F / ^FTSE）の逆張りロング（reversal_long=True）は、
非指数グループの逆張りロングより有意に高い勝率を示す。**

- スイープ FDR q=0.023（`group=index×reversalL`）で本日新規 FDR 通過
- 前回 #013 で「指数ロング全体 54.1%」を確認済み → 逆張りサブセットに絞ると？
- 前向きトラッカー `group=index×reversalL` に本日新規登録

## 事前宣言基準
- 主仮説通過A条件：CI下限 ≥ 43%（損益分岐） かつ N ≥ 20
- 補仮説：上昇トレンドでの指数×revL CI下限 ≥ 50%

## スクリプト全文
```python
import json, math

def wilson_ci(k, n, z=1.96):
    if n == 0: return (0, 0, 0)
    p = k / n
    denom = 1 + z*z/n
    center = (p + z*z/(2*n)) / denom
    spread = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / denom
    return (p, max(0, center - spread), min(1, center + spread))

with open('signals-log.json') as f:
    logs = json.load(f)

closed = [r for r in logs if r.get('outcome') in ('tp1','tp2','sl')]

def get_trend(r):
    ta = r.get('trend_alignment')
    if isinstance(ta, dict) and ta.get('higher_tf_trend'):
        return ta['higher_tf_trend']
    return 'unknown'

GROUPS = {
    'metal': {'GC=F','SI=F'},
    'index': {'NKD=F','ES=F','NQ=F','YM=F','^FTSE'},
    'jpy_fx': {'USDJPY=X','EURJPY=X','GBPJPY=X','AUDJPY=X'},
    'other_fx': {'EURUSD=X','GBPUSD=X','AUDUSD=X','EURAUD=X','GBPAUD=X'},
    'btc': {'BTC-USD'},
    'oil': {'CL=F'},
}
REV = {'rsi_oversold_bounce','bb_lower_touch'}
def is_long(r): return 'ロング' in (r.get('direction') or '')
def is_group(r, g): return r.get('ticker','') in GROUPS.get(g, set())
def is_rev_long(r): return is_long(r) and r.get('primary_signal','') in REV
def win(r): return r.get('outcome') in ('tp1','tp2')
def r_val(r):
    o = r.get('outcome')
    if o == 'tp1': return 1.33
    if o == 'tp2': return 2.0
    if o == 'sl': return -1.0
    return None
```

## 生出力

### グループ別 reversal_long
```
index:    k=52, n=88,  59.1% CI[48.6~68.8%] E(R)=+0.377
metal:    k=13, n=62,  21.0% CI[12.7~32.6%] E(R)=-0.511
jpy_fx:   k=32, n=68,  47.1% CI[35.7~58.8%] E(R)=+0.096
other_fx: k=40, n=101, 39.6% CI[30.6~49.4%] E(R)=-0.077
btc:      k=9,  n=36,  25.0% CI[13.8~41.1%] E(R)=-0.418
oil:      k=12, n=19,  63.2% CI[41.0~80.9%] E(R)=+0.472 ※N=19 小サンプル

all×revL: k=158, n=374, 42.2% CI[37.3~47.3%] E(R)=-0.016
```

### トレンド別（指数×reversal_long）
```
上昇: k=36, n=52, 69.2% CI[55.7~80.1%] E(R)=+0.613
下降: k=5,  n=7,  71.4% CI[35.9~91.8%] E(R)=+0.664  ※N=7 小サンプル
中立: k=11, n=29, 37.9% CI[22.7~56.0%] E(R)=-0.116
```

### 銘柄別（指数×reversal_long）
```
ES=F:  k=21, n=32, 65.6% CI[48.3~79.6%] E(R)=+0.529
NQ=F:  k=14, n=19, 73.7% CI[51.2~88.2%] E(R)=+0.717
NKD=F: k=6,  n=13, 46.2% CI[23.2~70.9%] E(R)=+0.075
YM=F:  k=6,  n=15, 40.0% CI[19.8~64.3%] E(R)=-0.068
^FTSE: k=5,  n=9,  55.6% CI[26.7~81.1%] E(R)=+0.294
```

### 指数×ロング全体（比較用）
```
index×long: k=102, n=181, 56.4% CI[49.1~63.4%] E(R)=+0.313
```

## 判定
- **主仮説通過A** ✅: 指数×revL CI下限 48.6% ≥ 43%・N=88 ≥ 20
- **補仮説通過A** ✅: 上昇×指数×revL CI下限 55.7% ≥ 50%（N=52）
- FDR q=0.023 (スイープ) ✅
- 交絡点検: 全体42.2%は「グループ構成の偏り」で説明可（指数88件 vs 非指数286件）

## 交叉発見（探索的）
- NQ=F が指数グループ内最高（73.7%・N=19）。ただしN=19は参考値
- 中立・もみあい相場では37.9%と43%を割り込む（N=29）→ トレンド確認の重要性

## 前向きトラッカー登録
- `group=index×reversalL` 本日新規登録（forward N=0）
- 昇格基準: 前向きN≥80 かつ 平均R CI下限>0
