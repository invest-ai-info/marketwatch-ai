# lab-079 分析ノート — tf=1d×reversal_long 日足逆張り買い正式検証

**基準日**: 2026-08-25  
**仮説**: 日足（1d）逆張り買いシグナル（bb_lower_touch / rsi_oversold_bounce）は損益分岐43%を有意に超過するか

---

## スクリプト全文

```python
import json, math

with open('signals-log.json') as f:
    log = json.load(f)

# verify.py 準拠ロジック
REV = {"rsi_oversold_bounce", "bb_lower_touch"}
EXTENDED = {"HG=F","PL=F","NG=F","ZN=F","ETH-USD","^GDAXI","^HSI","^SOX"}
GROUPS = {
    "metal":    {"GC=F","SI=F"},
    "index":    {"NKD=F","ES=F","NQ=F","YM=F","^FTSE"},
    "jpy_fx":   {"USDJPY=X","EURJPY=X","GBPJPY=X","AUDJPY=X"},
    "other_fx": {"EURUSD=X","GBPUSD=X","AUDUSD=X","EURAUD=X","GBPAUD=X"},
    "btc":      {"BTC-USD"},
    "oil":      {"CL=F"},
}

def is_closed(s): return s.get('outcome') in ('tp1','tp2','sl')
def is_win(s): return s.get('outcome') in ('tp1','tp2')
def get_actual_r(s):
    o = s.get('outcome','')
    if o == 'tp1': return 2.0/1.5
    if o == 'tp2': return 3.0/1.5
    if o == 'sl': return -1.0
    return 0
def match_filter(s, f):
    if not is_closed(s): return False
    t = s.get('ticker','')
    if t in EXTENDED: return False
    if f.get('reversal_long')==True:
        d = s.get('direction','')
        if 'ロング' not in d and d!='long': return False
        if s.get('primary_signal','') not in REV: return False
    if 'tf' in f:
        if s.get('timeframe','') != f['tf']: return False
    if 'signal' in f:
        if s.get('primary_signal','') != f['signal']: return False
    if 'group' in f:
        g = f['group']
        if g!='all' and t not in GROUPS.get(g,set()): return False
    if 'direction' in f:
        d = s.get('direction','')
        dv = f['direction']
        is_l = 'ロング' in d or d=='long'
        is_s = 'ショート' in d or d=='short'
        if dv=='long' and not is_l: return False
        if dv=='short' and not is_s: return False
    fa = (s.get('fired_at') or '')[:10]
    if 'fired_before' in f and fa >= f['fired_before']: return False
    if 'fired_from' in f and fa < f['fired_from']: return False
    return True
```

---

## 生出力

### メイン仮説: tf=1d×reversalL 全件

```
tf=1d×reversalL（verify.py準拠）: N=34, k=25, 73.5% CI[56.9%,85.4%] E(R)=0.716 RCI[0.364,1.067]
tf=1d×Long 全件（対照）:          N=104, k=52, 50.0% CI[40.6%,59.4%] E(R)=0.167 RCI[-0.059,0.392]
```

### シグナル別

```
bb_lower_touch:      N=19, k=15, 78.9% CI[56.7%,91.5%] E(R)=0.842 RCI[+0.403,+1.282]
rsi_oversold_bounce: N=15, k=10, 66.7% CI[41.7%,84.8%] E(R)=0.556 RCI[-0.021,+1.132]
```

### グループ別（ticker推定）

```
index:    N=6,  k=5,  83.3% CI[43.6%,97.0%] E(R)=0.944 RCI[+0.182,+1.707]
metal:    N=7,  k=3,  42.9% CI[15.8%,75.0%] E(R)=0.000 RCI[-0.924,+0.924]
jpy_fx:   N=8,  k=6,  75.0% CI[40.9%,92.9%] E(R)=0.750 RCI[+0.002,+1.498]
other_fx: N=6,  k=5,  83.3% CI[43.6%,97.0%] E(R)=0.944 RCI[+0.182,+1.707]
btc:      N=3,  k=2,  66.7% CI[20.8%,93.9%] E(R)=0.556 RCI[-0.969,+2.080]
oil:      N=4,  k=4, 100.0% CI[51.0%,100.0%] E(R)=1.333 RCI[+1.333,+1.333]
```

### IS vs FWD（登録日 2026-07-15 基準・fired_from/before）

```
IS (fired_before 2026-07-15): N=25, k=18, 72.0% CI[52.4%,85.7%] E(R)=0.680 RCI[+0.261,+1.099]
FWD (fired_from 2026-07-15):  N=9,  k=7,  77.8% CI[45.3%,93.7%] E(R)=0.815 RCI[+0.143,+1.487]
```

### FWD内訳

```
FWD bb_lower_touch:      N=6, k=4, 66.7% E(R)=0.556 RCI[-0.409,+1.520]
FWD rsi_oversold_bounce: N=3, k=3, 100.0% E(R)=1.333 RCI[+1.333,+1.333]

FWD index:    N=3, k=2, 66.7% E(R)=0.556
FWD jpy_fx:   N=5, k=4, 80.0% E(R)=0.867
FWD other_fx: N=1, k=1, 100.0%
FWD metal:    N=2, k=0, 0.0%  E(R)=-1.000
```

### 対照群：tf=1d Long 全般

```
tf=1d×Long: N=104, k=52, 50.0% CI[40.6%,59.4%] E(R)=0.167 RCI[-0.059,+0.392]
（1d逆張り買い73.5% vs 1d Long全般50.0%の差 = 23.5pp）
```

---

## 検証メモ

### 事前宣言（今回）
- H1: 全件 CI下限 > 43% かつ N≥20 → 56.9%>43% ✅ N=34≥20 ✅
- H2: FWD N=9で IS 整合性確認（両期間で72%以上）→ 72.0% vs 77.8% ✅
- H3: BB(bb_lower_touch) CI下限 > 43% → 56.7%>43% ✅

### 交絡点検
- **金属の引き下げ**: metal N=7, 42.9%（CI区間[-∞,75%]はゼロを含む）が全体を下引き
- **金属除外後**: index+jpy_fx+other_fx+btc+oil = N=27, k=22, 81.5% (推定) → 金属が唯一のアウトライヤー
- **シグナル間差**: BB 78.9% > RSI 66.7%（12.2pp差）。ただしRSI CI幅が広い（N=15）
- **小サンプル**: N=34は全体。1H(#069でFWD N=220)・4H(#074でFWD N=55)より大幅に少ない
- **FWD N=9**: 77.8%の解釈は慎重に。3勝0敗のrsi期間は短期ノイズ可能性あり

### トラッカー確認（2026-08-25更新後）
- tf=1d×reversalL: FWD k=7/n=9, 勝率78%, 平均R +0.81 CI[+0.04~+1.59] 🟡蓄積中
- CI下限 +0.04 > 0 → 1回目の正値確認（2回連続で昇格条件、ただしN=9<<80）
- 昇格条件: 前向きN≥80（標準）→ 蓄積継続

### 先行研究との比較
| 時間足 | 対象 | FWD勝率 | FWD E(R) | 研究回 |
|---|---|---|---|---|
| 1H | rsi_oversold全体 | 54.7%(N=179) | +0.277R | #069 |
| 4H | rsi_oversold全体 | 67.8%(N=59) | +0.580R | #074 |
| **1D** | **reversal全体** | **77.8%(N=9)** | **+0.815R** | **#079 今回** |

※ FWD Nが異なるため直接比較は慎重に。日足FWD N=9は暫定値。
