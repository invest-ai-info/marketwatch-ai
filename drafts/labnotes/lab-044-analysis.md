# lab-044-analysis.md — 指数×ロング 前向き後半崩落と降格ルール初日の棚卸し

**基準日**: 2026-07-19  
**前向き決済済総数**: 1843件  
**検証目的**: 降格ルール（2026-07-18新設）初日の全✅昇格仮説チェックポイント。
特に指数×ロング FWD後半N=57（2026-07-09〜07-17）の急落を詳細解析。

---

## ▼ 実行スクリプト（Python反実仮想集計）

```python
import json, math
from datetime import datetime

with open('signals-log.json') as f:
    data = json.load(f)

GROUPS = {
    "metal":    {"GC=F","SI=F"},
    "index":    {"NKD=F","ES=F","NQ=F","YM=F","^FTSE"},
    "jpy_fx":   {"USDJPY=X","EURJPY=X","GBPJPY=X","AUDJPY=X"},
    "other_fx": {"EURUSD=X","GBPUSD=X","AUDUSD=X","EURAUD=X","GBPAUD=X"},
    "btc":      {"BTC-USD"},
    "oil":      {"CL=F"},
}
REV = {"rsi_oversold_bounce","bb_lower_touch"}

def closed(d): return d.get("outcome") in ("tp1","tp2","sl")
def win(d): return d.get("outcome") in ("tp1","tp2")
def is_long(d): return "ロング" in (d.get("direction") or "")
def is_short(d): return "ショート" in (d.get("direction") or "")
def get_group(d):
    t=d.get("ticker","")
    for g,ts in GROUPS.items():
        if t in ts: return g
    return "other"
def get_tf(d): return d.get("timeframe","")
def get_trend(d):
    ta=d.get("trend_alignment")
    if isinstance(ta,dict) and ta.get("higher_tf_trend"):
        return ta["higher_tf_trend"]
    return "unknown"
def get_date(s): return (s.get("fired_at") or "")[:10]
def get_r(s):
    o=s.get("outcome","")
    if o=="sl": return -1.5
    if o=="tp2": return 3.0
    if o=="tp1": return 2.0
    return 0

def wilson(k,n,z=1.96):
    if n==0: return 0,0
    p=k/n; den=1+z*z/n; c=(p+z*z/(2*n))/den
    pm=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return max(0,c-pm),min(1,c+pm)

def er_ci(rs,z=1.96):
    n=len(rs)
    if n==0: return 0,0,0
    m=sum(rs)/n
    if n<2: return m,m,m
    std=math.sqrt(sum((r-m)**2 for r in rs)/(n-1))
    se=std/math.sqrt(n)
    return m,m-z*se,m+z*se
```

---

## ▼ 生出力

### 総件数
Total closed: 1843

### 指数×ロング 全期間（IS+FWD）
```
index×long ALL: k=154 n=333 46.2% WCI[41.0%,51.6%] E(R)=+0.119 RCI[-0.069,+0.306]
NKD=F×long ALL: k=41 n=75 54.7% WCI[43.4%,65.4%] E(R)=+0.413 RCI[+0.016,+0.810]
ES=F×long ALL:  k=40 n=89 44.9% WCI[35.0%,55.3%] E(R)=+0.073 RCI[-0.291,+0.437]
NQ=F×long ALL:  k=34 n=77 44.2% WCI[33.6%,55.3%] E(R)=+0.045 RCI[-0.345,+0.436]
YM=F×long ALL:  k=27 n=65 41.5% WCI[30.4%,53.7%] E(R)=-0.046 RCI[-0.469,+0.376]
^FTSE×long ALL: k=12 n=27 44.4% WCI[27.6%,62.7%] E(R)=+0.056 RCI[-0.613,+0.724]
index×long×1h:  k=92 n=189 48.7% WCI[41.6%,55.8%] E(R)=+0.204 RCI[-0.046,+0.454]
index×long×4h:  k=57 n=132 43.2% WCI[35.0%,51.7%] E(R)=+0.011 RCI[-0.286,+0.308]
index×short ALL: k=46 n=117 39.3% WCI[30.9%,48.4%] E(R)=-0.124 RCI[-0.435,+0.187]
```

### 指数×ロング 前向き時系列分割（登録日2026-06-12以降）
```
FWD全体（N=212):  k=95  n=212 44.8% WCI[38.3%,51.5%] E(R)=+0.068 RCI[-0.166,+0.303]
FWD前半N=155:     k=84  n=155 54.2% WCI[46.3%,61.8%] E(R)=+0.397 RCI[+0.121,+0.672]
FWD後半N=57:      k=11  n=57  19.3% WCI[11.1%,31.3%] E(R)=-0.825 RCI[-1.186,-0.463]
  後半日付範囲: 2026-07-09 〜 2026-07-17
  ×NKD=F: k=3  n=12 25.0% WCI[ 8.9%,53.2%] E(R)=-0.625 RCI[-1.521,+0.271]
  ×ES=F:  k=3  n=16 18.8% WCI[ 6.6%,43.0%] E(R)=-0.844 RCI[-1.535,-0.152]
  ×NQ=F:  k=2  n=16 12.5% WCI[ 3.5%,36.0%] E(R)=-1.062 RCI[-1.648,-0.477]
  ×YM=F:  k=1  n=10 10.0% WCI[ 1.8%,40.4%] E(R)=-1.150 RCI[-1.836,-0.464]
  ×^FTSE: k=2  n=3  66.7% WCI[20.8%,93.9%] E(R)=+0.833 N小・参考値
  ×1h:    k=8  n=38 21.1% WCI[11.1%,36.3%] E(R)=-0.763 RCI[-1.223,-0.303]
  ×4h:    k=3  n=17 17.6% WCI[ 6.2%,41.0%] E(R)=-0.882 RCI[-1.536,-0.229]
  ×rsi_oversold: k=0 n=6 0.0% E(R)=-1.500
  ×bb_lower:     k=4 n=21 19.0% WCI[ 7.7%,40.0%] E(R)=-0.833 RCI[-1.436,-0.231]
  ×high_break:   k=1 n=7 14.3% E(R)=-1.000
  ×macd_golden:  k=5 n=16 31.2% WCI[14.2%,55.6%] E(R)=-0.406
  ×trend=上昇:   k=3 n=24 12.5% WCI[ 4.3%,31.0%] E(R)=-1.062 RCI[-1.536,-0.589]
  ×trend=下降:   k=1 n=13  7.7% WCI[ 1.4%,33.3%] E(R)=-1.231
  ×trend=中立:   k=7 n=20 35.0% WCI[18.1%,56.7%] E(R)=-0.275
```

### trend=上昇×revL 全期間（IS+FWD）
```
上昇×revL ALL: k=99 n=191 51.8% WCI[44.8%,58.8%] E(R)=+0.314 RCI[+0.065,+0.563]
  ×index:    k=42 n=75 56.0% WCI[44.7%,66.7%] E(R)=+0.460 RCI[+0.064,+0.856]
  ×jpy_fx:   k=27 n=47 57.4% WCI[43.3%,70.5%] E(R)=+0.511 RCI[+0.011,+1.011]
  ×other_fx: k=19 n=48 39.6% WCI[27.0%,53.7%] E(R)=-0.115 RCI[-0.604,+0.375]
```

### trend=上昇×revL 前向き時系列分割（登録日2026-06-22以降）
```
FWD前半N=81 (#042確認時): k=44 n=81  54.3% WCI[43.5%,64.7%] E(R)=+0.401 RCI[+0.019,+0.783]
FWD後半N=9 (2026-07-16〜07-17): k=1 n=9  11.1% WCI[2.0%,43.5%] E(R)=-1.111 RCI[-1.873,-0.349]
  ×group=index:  k=0 n=4 0.0% E(R)=-1.500 （ES=F 0/2, NQ=F 0/1, YM=F 0/1）
  ×group=jpy_fx: k=1 n=4 25.0%
```

### 金属×ロング(gate) 全期間（IS+FWD）
```
metal×long ALL: k=45 n=190 23.7% WCI[18.2%,30.2%] E(R)=-0.671 RCI[-0.883,-0.459]
  IS (前N=86):    k=14 n=86  16.3% E(R)=-0.930 RCI[-1.205,-0.656]
  FWD全体N=104:   k=31 n=104 29.8% E(R)=-0.457 RCI[-0.766,-0.148]
  FWD前半N=86:    k=24 n=86  27.9% E(R)=-0.523 RCI[-0.857,-0.190]（#039確認時）
  FWD後半N=18:    k=7  n=18  38.9% E(R)=-0.139 RCI[-0.950,+0.672]（CIゼロ含む）
```

---

## ▼ 交絡点検・解釈メモ

### 指数×ロング 後半N=57 崩落の解釈
- **日付範囲**: 2026-07-09〜07-17（約9日間）
- **全銘柄崩落**: ES=F 18.8%・NQ=F 12.5%・YM=F 10%・NKD=F 25%
- **特筆**: 上昇トレンド中の指数ロングでも12.5%（#021/026での最強パターンが崩壊）
- **シグナル別**: rsi_oversold 0/6=0%（前半66%の真逆）・bb 19%・high_break 14%
- **TF別**: 1H 21.1%・4H 17.6%（TF差は小さく、全般的な地合い悪化が主因）
- **構造的交絡否定**: 全銘柄横断・全シグナル横断・全TF横断で崩落 → 銘柄構成/シグナル偏りは説明困難
- **仮説**: 7/9〜7/17 の市場環境（指数全般の高値圏/不安定期）が主因の可能性

### trend=上昇×revL 後半N=9 崩落
- **日付集中**: 2026-07-16〜07-17（わずか2日間・9件）
- **指数部分 0/4=0%** が主犯（ES=F 0/2・NQ=F 0/1・YM=F 0/1）
- 指数×ロング後半崩落と**同根の現象**（指数グループの7月中旬一斉不振）
- 小サンプル（N=9）のため強い結論は不可、ただし指数部分の崩落は構造的

### 降格ルール（2026-07-18新設）への示唆
- 指数×ロング: FWD E(R) CI[-0.22,+0.31]（ゼロまたぎ）→ **1回目の基準割れ候補**
- trend=上昇×revL: FWD E(R) CI[-0.07,+0.40]（ゼロまたぎ）→ **1回目の基準割れ候補**
- 2回連続で降格 → 次チェックポイントで継続監視が重要
- 金属×long gate: FWD CI[-0.63,+0.02]（barely crosses zero）→ gate条件割れ候補

---

## ▼ トラッカー現在値（2026-07-19 update結果）

- 指数×ロング: FWD 95/212=45% E(R)=+0.046 CI[-0.22~+0.31] ✅昇格（降格基準割れ1回目候補）
- trend=上昇×revL: FWD 45/90=50% E(R)=+0.167 CI[-0.07~+0.40] ✅昇格（降格基準割れ1回目候補）
- metal×long gate: FWD 31/104=30% E(R)=-0.304 CI[-0.63~+0.02] ✅昇格（gate条件CIが+0.02でゼロ超え）
