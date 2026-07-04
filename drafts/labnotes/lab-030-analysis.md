# Lab-030 分析ノート — ロング全般gate前向き反証

**基準日**: 2026-07-05  
**仮説**: dir=long gate（ロング全般回避ゲート）は前向きデータで反証されるか  
**採択理由**: tracker update で dir=long が ⛔反証 に変化（優先度①）

---

## スクリプト全文

```python
import json, math
from scipy import stats as scipy_stats

with open('signals-log.json') as f:
    data = json.load(f)

def is_closed(s):
    return s.get('outcome') in ('tp1', 'sl', 'expired', 'no_plan')

def win(s): return 1 if s.get('outcome') == 'tp1' else 0
def er(s):
    o = s.get('outcome')
    if o == 'tp1': return 2.0
    elif o == 'sl': return -1.5
    else: return 0.0

def is_long(s):
    d = s.get('direction') or ''
    return 'ロング' in d

def group(s):
    t = s.get('ticker') or ''
    if t in ('GC=F','SI=F'): return 'metal'
    if t in ('NKD=F','ES=F','NQ=F','YM=F','^FTSE'): return 'index'
    if t == 'BTC-USD': return 'btc'
    if t == 'CL=F': return 'oil'
    if t in ('USDJPY=X','EURJPY=X','GBPJPY=X','AUDJPY=X'): return 'jpy_fx'
    if t in ('EURUSD=X','GBPUSD=X','AUDUSD=X','EURAUD=X','GBPAUD=X'): return 'other_fx'
    return 'other'

def wilson_ci(k, n, z=1.96):
    if n == 0: return (0.0, 0.0)
    p = k/n
    denom = 1 + z**2/n
    center = (p + z**2/(2*n)) / denom
    margin = z * math.sqrt(p*(1-p)/n + z**2/(4*n**2)) / denom
    return (max(0.0, center-margin), min(1.0, center+margin))

def t_ci_er(values):
    n = len(values)
    if n == 0: return (0.0, 0.0)
    if n == 1: return (values[0], values[0])
    mean = sum(values)/n
    var = sum((x-mean)**2 for x in values)/(n-1)
    se = math.sqrt(var/n)
    t = scipy_stats.t.ppf(0.975, df=n-1)
    return (mean - t*se, mean + t*se)

closed = [s for s in data if is_closed(s)]
longs = [s for s in closed if is_long(s)]
reg_date = '2026-06-25'
fwd = [s for s in longs if (s.get('fired_at') or '')[:10] >= reg_date]
ins = [s for s in longs if (s.get('fired_at') or '')[:10] < reg_date]
```

---

## 生出力

### [1] IS vs FWD 全体
```
総クローズ=1647, ロング総数=984, IS=789, FWD=195

IS(<2026-06-25): 301/789(38.1%) E(R)=-0.161 勝率CI[34.8%~41.6%] RCI[-0.280~-0.042]
FWD(≥2026-06-25): 96/195(49.2%) E(R)=0.231 勝率CI[42.3%~56.2%] RCI[-0.016~0.478]
```

### [2] グループ別 FWD（2026-06-25以降）
```
index:    23/45(51.1%) E(R)=0.289 勝率CI[37.0%~65.0%] RCI[-0.243~0.820]
metal:    18/29(62.1%) E(R)=0.672 勝率CI[44.0%~77.3%] RCI[+0.015~+1.330]
jpy_fx:   15/39(38.5%) E(R)=-0.154 勝率CI[24.9%~54.1%] RCI[-0.713~0.405]
other_fx: 28/50(56.0%) E(R)=0.460 勝率CI[42.3%~68.8%] RCI[-0.039~0.959]
btc:       8/21(38.1%) E(R)=-0.167 勝率CI[20.8%~59.1%] RCI[-0.959~0.626]
oil:       4/11(36.4%) E(R)=-0.091 勝率CI[15.2%~64.6%] RCI[-1.243~1.061]
```

### [3] グループ別 IS（〜2026-06-24）
```
index:    106/199(53.3%) E(R)=0.379 勝率CI[46.3%~60.1%] RCI[0.136~0.623]
metal:     17/111(15.3%) E(R)=-0.964 勝率CI[9.8%~23.2%] RCI[-1.202~-0.726]
jpy_fx:    63/156(40.4%) E(R)=-0.087 勝率CI[33.0%~48.2%] RCI[-0.359~0.186]
other_fx:  82/234(35.0%) E(R)=-0.274 勝率CI[29.2%~41.4%] RCI[-0.489~-0.058]
btc:       18/60(30.0%) E(R)=-0.450 勝率CI[19.9%~42.5%] RCI[-0.868~-0.032]
oil:       15/29(51.7%) E(R)=0.310 勝率CI[34.4%~68.6%] RCI[-0.367~0.987]
```

### [4] 構成比シフト IS→FWD（ほぼ変化なし）
```
index:    IS=25.2%(N=199) FWD=23.1%(N=45)   Δ-2.1pp
metal:    IS=14.1%(N=111) FWD=14.9%(N=29)   Δ+0.8pp
jpy_fx:   IS=19.8%(N=156) FWD=20.0%(N=39)   Δ+0.2pp
other_fx: IS=29.7%(N=234) FWD=25.6%(N=50)   Δ-4.0pp
btc:       IS=7.6%(N=60) FWD=10.8%(N=21)    Δ+3.2pp
oil:       IS=3.7%(N=29) FWD=5.6%(N=11)     Δ+2.0pp
```

### [5] index FWD 銘柄別
```
NKD=F:  6/11(54.5%) E(R)=0.409
ES=F:   5/11(45.5%) E(R)=0.091
NQ=F:   4/10(40.0%) E(R)=-0.100
YM=F:   7/11(63.6%) E(R)=0.727
^FTSE:  1/2(50.0%)  E(R)=0.250
```

### [6] index IS 銘柄別
```
NKD=F:  29/44(65.9%) E(R)=0.807
ES=F:   27/54(50.0%) E(R)=0.250
NQ=F:   25/44(56.8%) E(R)=0.489
YM=F:   17/36(47.2%) E(R)=0.153
^FTSE:   8/21(38.1%) E(R)=-0.024
```

### [7] 金属銘柄別 IS vs FWD
```
GC=F IS:  13/68(19.1%) E(R)=-0.831  RCI[-1.166~-0.495]
GC=F FWD: 10/15(66.7%) E(R)=0.833   RCI[-0.112~1.779]
SI=F IS:   4/43(9.3%)  E(R)=-1.174  RCI[-1.491~-0.858]
SI=F FWD:  8/14(57.1%) E(R)=0.500   RCI[-0.538~1.538]
```

### [8] TF別 FWD
```
1h: 53/120(44.2%) E(R)=0.046  RCI[-0.270~0.361]
4h: 40/70(57.1%)  E(R)=0.521  RCI[+0.109~+0.934]
1d:  3/5(60.0%)   E(R)=0.600  (N小)
```

### [9] シグナル別 FWD
```
bb_lower_touch:   27/51(52.9%)  E(R)=0.382
macd_golden:      26/50(52.0%)  E(R)=0.320
high_break:       10/28(35.7%)  E(R)=-0.250
rsi_oversold_bounce: 14/21(66.7%) E(R)=0.833
bb_upper_break:    7/17(41.2%)  E(R)=-0.059
rsi_overbought:    4/13(30.8%)  E(R)=-0.423
```

### [10] 全期間合計（IS+FWD、claims.json用）
```
全ロング:    397/984 =40.3% E(R)=-0.083 勝率CI[37.3%~43.4%] RCI[-0.191~0.024]
金属ロング:   35/140 =25.0% E(R)=-0.625 CI[18.6%~32.8%]
指数ロング:  129/244 =52.9% E(R)=0.363  CI[46.6%~59.0%]
他FXロング:  110/284 =38.7% E(R)=-0.144 CI[33.3%~44.5%]
円クロスL:    78/195 =40.0% E(R)=-0.100 CI[33.4%~47.0%]
BTCロング:    26/81  =32.1% E(R)=-0.377 CI[22.9%~42.9%]
```

### [11] 反実仮想（構成シフト寄与）
```
反実仮想（IS構成比×FWD各グループE(R)）: E(R)=+0.257
実際のFWD E(R): +0.231
構成シフト寄与: -0.027R（ほぼゼロ＝構成ではなく性能シフトが主因）
```

### [12] 反証判定
```
N=195 ≥ 80 ✅
FWD E(R) CI = [-0.016~+0.478]
gate条件「CI上限<0」: ❌（CI上限+0.478 >> 0）
→ ⛔反証成立
```

---

## 分析サマリー

**gate設立の経緯（IS時点）**:
- IS全ロング: 38.1%(301/789), E(R)=-0.161, RCI[-0.280~-0.042] （CI全域マイナス）
- 最大の引き下げ要因: 金属ロング 15.3%(17/111), E(R)=-0.964 （111件14%が壊滅的）
- 他FXロングも不振: 35.0%(82/234), E(R)=-0.274

**反証の主因**:
1. 金属ロングの劇的レジーム転換: IS -0.964 → FWD +0.672 (+1.636R)
2. 他FXロングの改善: IS -0.274 → FWD +0.460 (+0.734R)
3. 構成シフトは寄与わずか（-0.027R＝むしろ若干マイナス方向）

**変わらなかったもの**:
- jpy_fx ロング: IS 40.4% → FWD 38.5% （依然43%割れ）
- 指数ロング: IS 53.3% → FWD 51.1% （安定だがCI幅拡大）

**重要な留意点**:
- FWD全体CI = [-0.016~+0.478]（下限がわずかにマイナス＝統計的確定打未達）
- 金属FWD N=29（小サンプル・CI幅大）
- 金属レジーム転換が#013で記録済みの現象と整合
- 「ロング全般OK」ではなく「ロング不利の法則が崩れた＝グループ選別が必要」

**4H足の逆転**:
- IS時点 4H×L=35.2%（#015棄却）→ FWD 57.1%(40/70) RCI[+0.109~+0.934]
- 1H FWD=44.2%、4H FWD=57.1%という IS時点とは逆転した関係
