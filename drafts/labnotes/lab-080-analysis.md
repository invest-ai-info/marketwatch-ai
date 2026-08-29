# Lab-080 分析ノート — 日足逆張り買い71.4%の構造分解

**基準日**: 2026-08-26  
**仮説**: 「tf=1d×reversalL（日足逆張り買い）の71.4%勝率——非金属78.6%・上昇トレンド76.0%——は1H(43.9%)・4H(46.5%)との27pp差を形成する。グループ別に分解しても構造的優位か？」

## スクリプト全文

```python
import json, math, statistics

with open('signals-log.json') as f:
    data = json.load(f)

REV = {'rsi_oversold_bounce', 'bb_lower_touch'}
GROUPS = {
    'metal':{'GC=F','SI=F'},
    'index':{'NKD=F','ES=F','NQ=F','YM=F','^FTSE'},
    'jpy_fx':{'USDJPY=X','EURJPY=X','GBPJPY=X','AUDJPY=X'},
    'other_fx':{'EURUSD=X','GBPUSD=X','AUDUSD=X','EURAUD=X','GBPAUD=X'},
    'btc':{'BTC-USD'},
    'oil':{'CL=F'},
}
# 拡張ユニバース (index_x)
EXT_INDEX = {'^GDAXI','^HSI','^SOX'}

def closed_v(s): return s.get('outcome') in ('tp1','tp2','sl')
def win_v(s): return s.get('outcome') in ('tp1','tp2')
def get_fire_date(s): return (s.get('fired_at','') or '')[:10]
def get_trend(s):
    ta = s.get('trend_alignment',{})
    if isinstance(ta,dict) and ta.get('higher_tf_trend'):
        return ta['higher_tf_trend']
    return 'unknown'
def get_group(s):
    t = s.get('ticker','')
    for g, ts in GROUPS.items():
        if t in ts: return g
    return 'other'

def is_1d_rl(s):
    return (s.get('timeframe')=='1d' and 'ロング' in (s.get('direction') or '')
            and s.get('primary_signal') in REV and closed_v(s))
```

## 生出力（verify.py logic: closed = tp1/sl のみ）

### 全体
- **N=35**: TP1=25, SL=10
- 全期間: N=35, k=25, win=71.4% CI[54.9%,83.7%]
- 全データが 2026-06-11 以降（1Dアラート開始日）

### 期間
- 観測前(fired<2026-06-11): N=0 ← 1Dアラートは2026-06-11新設のため
- ライブ(fired>=2026-06-11): N=35, k=25, 71.4%

### 時間足比較（verify.py logic）
- 1h×reversalL: N=709, k=311, win=43.9% CI[40.3%,47.5%]
- 4h×reversalL: N=368, k=171, win=46.5% CI[41.4%,51.6%]  ← 4H N=368はtp1+slのみ
- 1d×reversalL: N=35, k=25, win=71.4% CI[54.9%,83.7%]
- 時間足差: 1D vs 1H = +27.5pp / 1D vs 4H = +24.9pp

### トレンド別（verify.py logic: get_trend = higher_tf_trend）
- 上昇: N=25, k=19, win=76.0% CI[56.6%,88.5%]
- 下降: N=4, k=3, win=75.0% CI[30.1%,95.4%] ← N=4 小サンプル
- 中立・もみあい: N=6, k=3, win=50.0% CI[18.8%,81.2%] ← N=6 小サンプル

### グループ別（verify.py GROUPS定義）
- metal (GC=F/SI=F): N=7, k=3, win=42.9% CI[15.8%,75.0%]
- index (NKD=F/ES=F/NQ=F/YM=F/^FTSE): N=6, k=5, win=83.3% CI[43.6%,97.0%]
- jpy_fx (USDJPY=X/.../GBPJPY=X): N=8, k=6, win=75.0% CI[40.9%,92.9%]
- other_fx (EURUSD=X/GBPUSD=X/AUDUSD=X/EURAUD=X): N=6, k=5, win=83.3% CI[43.6%,97.0%]
- btc (BTC-USD): N=3, k=2, win=66.7% CI[20.8%,93.9%]
- oil (CL=F): N=4, k=4, win=100.0% CI[51.0%,100.0%]
- その他(拡張含む): N=1, k=0, win=0.0% ← ^SOX (index_x)

### 金属 vs 非金属
- 金属: N=7, k=3, win=42.9%
- 非金属: N=28, k=22, win=78.6% CI[60.5%,89.8%]

### シグナル別
- bb_lower_touch: N=20, k=15, win=75.0% CI[53.1%,88.8%]
- rsi_oversold_bounce: N=15, k=10, win=66.7% CI[41.7%,84.8%]

### シグナル×トレンド
- bb_lower_touch×上昇: N=14, k=10, win=71.4% CI[45.4%,88.3%]
- rsi_oversold_bounce×上昇: N=11, k=9, win=81.8% CI[52.3%,94.9%]

### 上昇トレンド×グループ
- 上昇×metal: N=4, k=2, win=50.0%
- 上昇×index: N=6, k=5, win=83.3%
- 上昇×oil: N=4, k=4, win=100.0%
- 上昇×jpy_fx(他): N=11, k=8, win=72.7% CI[43.4%,90.3%]

### ティッカー別
| Ticker | N | k | win% |
|---|---|---|---|
| SI=F | 5 | 2 | 40.0% |
| GBPJPY=X | 5 | 4 | 80.0% |
| CL=F | 4 | 4 | 100.0% |
| BTC-USD | 3 | 2 | 66.7% |
| GC=F | 2 | 1 | 50.0% |
| NQ=F | 2 | 2 | 100.0% |
| EURJPY=X | 2 | 1 | 50.0% |
| GBPUSD=X | 2 | 2 | 100.0% |
| AUDUSD=X | 2 | 2 | 100.0% |
| ES=F | 1 | 1 | 100.0% |
| ^FTSE | 1 | 1 | 100.0% |
| EURUSD=X | 1 | 0 | 0.0% |
| NKD=F | 1 | 0 | 0.0% |
| EURAUD=X | 1 | 1 | 100.0% |
| ^SOX | 1 | 0 | 0.0% |
| YM=F | 1 | 1 | 100.0% |
| AUDJPY=X | 1 | 1 | 100.0% |

## 事前宣言（採択済み仮説）

**H1**: 非金属のCI下限 > 43%  
→ 78.6% CI[60.5%,89.8%] → CI下限60.5% >> 43% ✅

**H2**: 上昇トレンドのCI下限 > 43%  
→ 76.0% CI[56.6%,88.5%] → CI下限56.6% >> 43% ✅

**H3**: 1H vs 1D の差 ≥ 20pp  
→ 71.4% - 43.9% = 27.5pp ≥ 20pp ✅

**判定**: 通過A（全H条件クリア）

## 交絡点検

1. **金属交絡**: 金属が引き下げているか？  
   → 金属を除いても78.6% CI[60.5%,89.8%] → 金属はむしろ引き下げているが、除外後も高位維持

2. **上昇トレンド偏り**: 1D信号が上昇トレンドに偏発していないか？  
   → 上昇N=25/全N=35 = 71.4%が上昇トレンド中の発火  
   → ただし上昇中以外でも下降75%・中立50%と比較的高位

3. **2026年強気相場バイアス**: 全データが2026年（強気相場継続期）のみ  
   → これが最大の交絡。20年バックテストでは有意マイナス（バックログ記録）

4. **N=35 小サンプル**: Wilson CI幅[54.9%,83.7%]は広い  
   → 非金属N=28でも広いが下限60.5%は十分高位

## バックログ背景情報（#079より）

| 母集団 | N | 勝率 | 備考 |
|---|---|---|---|
| 20年リプレイ全期間 | 4541 | 39.7% | R=-0.055 CI[-0.099,-0.011] 有意マイナス |
| 2026-01〜06-10(観測直前) | 129 | 27.9% | R=-0.339 CI[-0.54,-0.14] 有意マイナス |
| ライブ2026-06-11〜08-06 | 35 | 71.4% | 今回集計 |

→ ライブと20年バックテストの乖離は極めて大きい（CIが完全非重複）
→ 1Dアラートが2026-06-11に開始した「観測窓の選択効果」の可能性が残る

## Wilson CI 計算式

Wilson CI (z=1.96):
  p̂ = k/n
  center = (p̂ + z²/(2n)) / (1 + z²/n)
  margin = z × √(p̂(1-p̂)/n + z²/(4n²)) / (1 + z²/n)
  CI = [center - margin, center + margin]
