# lab-035 分析ノート — tier=good 前向き急上昇の解剖
## 基準日: 2026-07-10 (JST)

## 仮説
**tier=good 前向き（FWD）E(R)+0.645 は市場全体の改善（+0.12R）を大幅に超える。**
この35.8ppの急上昇は、金属レジーム転換（#030/#032と同根）か、tier=goodに固有の現象か？
また、非金属でも同様に再現するか？

### 事前宣言基準
- H1: 非金属FWD 勝率≥60% かつ CI下限≥43%
- H2: 構成シフト寄与 < 10pp（性能シフトが主因であること）

## 検証スクリプト（全文）

```python
import json, math, datetime
from collections import Counter, defaultdict

def wilson(k, n, z=1.96):
    if n == 0: return (0.0, 100.0)
    p = k / n; den = 1 + z*z/n
    c = (p + z*z/(2*n)) / den
    pm = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / den
    return (max(0,c-pm)*100, min(1,c+pm)*100)

def closed(s): return s.get('outcome') in ('tp1','tp2','sl')
def win(s): return s.get('outcome') in ('tp1','tp2')
def is_good_tier(s): return isinstance(s.get('selection'),dict) and s['selection'].get('tier')=='good'

GROUPS = {
    "metal": {"GC=F","SI=F"},
    "index": {"NKD=F","ES=F","NQ=F","YM=F","^FTSE"},
    "jpy_fx": {"USDJPY=X","EURJPY=X","GBPJPY=X","AUDJPY=X"},
    "other_fx": {"EURUSD=X","GBPUSD=X","AUDUSD=X","EURAUD=X","GBPAUD=X"},
    "btc": {"BTC-USD"},
    "oil": {"CL=F"},
}
def get_group(ticker):
    for g, tickers in GROUPS.items():
        if ticker in tickers: return g
    return "unknown"

def get_er(signals):
    total = 0
    for s in signals:
        o = s.get('outcome')
        if o == 'tp1': total += 1.333
        elif o == 'tp2': total += 2.0
        elif o == 'sl': total -= 1.0
    return total / len(signals) if signals else 0

def get_date(s):
    fa = s.get('fired_at','')
    return datetime.date.fromisoformat(fa[:10]) if fa else None

with open('signals-log.json') as f:
    data = json.load(f)

FWD_START = datetime.date(2026, 6, 25)  # tracker登録日

# IS/FWD分割（全tier）
all_closed = [s for s in data if closed(s)]
is_all = [s for s in all_closed if (d:=get_date(s)) and d < FWD_START]
fwd_all = [s for s in all_closed if (d:=get_date(s)) and d >= FWD_START]

# tier=good IS/FWD
good = [s for s in data if closed(s) and is_good_tier(s)]
is_good = [s for s in is_all if is_good_tier(s)]
fwd_good = [s for s in fwd_all if is_good_tier(s)]
```

## 生出力（主要数値）

### IS/FWD分割
- **全体 IS**: 435/1089 = 39.9% CI[37.1~42.9] E(R)=-0.068
- **全体 FWD**: 193/430 = 44.9% CI[40.2~49.6] E(R)=+0.047
- **tier=good 全体**: 111/257 = 43.2% CI[37.3~49.3] E(R)=+0.008
- **tier=good IS**: 68/196 = 34.7% E(R)=-0.191
- **tier=good FWD**: 43/61 = 70.5% CI[58.1~80.4] E(R)=+0.645

### 全tier IS/FWD比較
- tier=elite: IS 49/104=47.1% E(R)=+0.099 | FWD 27/50=54.0% E(R)=+0.260 (+6.9pp)
- tier=good: IS 68/196=34.7% E(R)=-0.191 | FWD 43/61=70.5% E(R)=+0.645 (**+35.8pp**)
- tier=neutral: IS 89/254=35.0% E(R)=-0.183 | FWD 54/143=37.8% E(R)=-0.119 (+2.8pp)
- tier=avoid: IS 101/209=48.3% E(R)=+0.127 | FWD 69/176=39.2% E(R)=-0.085 (-9.1pp)

### グループ別 (FWD)
- FWD×metal: 7/10 = 70.0% E(R)=+0.633
- FWD×index: 13/19 = 68.4% E(R)=+0.596
- FWD×jpy_fx: 5/9 = 55.6% E(R)=+0.296
- FWD×other_fx: 10/11 = 90.9% E(R)=+1.121
- FWD×btc: 5/6 = 83.3% E(R)=+0.944
- FWD×oil: 3/6 = 50.0% E(R)=+0.166

### グループ別 (IS)
- IS×metal: 4/29 = 13.8% E(R)=-0.678
- IS×index: 27/62 = 43.5% E(R)=+0.016
- IS×jpy_fx: 13/33 = 39.4% E(R)=-0.081
- IS×other_fx: 20/58 = 34.5% E(R)=-0.196
- IS×btc: 3/6 = 50.0% E(R)=+0.166
- IS×oil: 1/8 = 12.5% E(R)=-0.708

### 構成変化（IS vs FWD）
- metal: IS 14.8% → FWD 16.4%（+1.6pp）
- index: IS 31.6% → FWD 31.1%（-0.5pp）
- other_fx: IS 29.6% → FWD 18.0%（-11.6pp）
- btc: IS 3.1% → FWD 9.8%（+6.7pp）

### 非金属での再現確認
- **非金属 IS**: 64/167 = 38.3% CI[31.3~45.9] E(R)=-0.106
- **非金属 FWD**: 36/51 = 70.6% CI[57.0~81.3] E(R)=+0.647

### 構成シフト寄与計算
- IS勝率×FWD構成で期待: 34.3%
- 実際FWD: 70.5%
- **構成シフト寄与 ≒ 0pp（36.2ppは全て性能シフト）**

### シグナル別 (FWD)
- FWD×rsi_oversold_bounce: 15/18 = 83.3% CI[60.8~94.2] E(R)=+0.944
- FWD×bb_lower_touch: 23/37 = 62.2% CI[46.1~75.9] E(R)=+0.450
- FWD×macd_dead: 4/5 = 80.0% E(R)=+0.866

### シグナル別 (IS)
- IS×rsi_oversold_bounce: 32/95 = 33.7% E(R)=-0.214
- IS×bb_lower_touch: 28/84 = 33.3% E(R)=-0.222
- IS×macd_dead: 5/7 = 71.4% E(R)=+0.666

### rsi_oversold_bounce 全体（tier問わず）
- rsi 全体 IS: 67/185 = 36.2% E(R)=-0.155
- rsi 全体 FWD: 24/32 = 75.0% CI[57.9~86.7] E(R)=+0.750

### トレンド別 (FWD)
- FWD×下降: 22/28 = 78.6% CI[60.5~89.8] E(R)=+0.833
- FWD×上昇: 11/18 = 61.1% CI[38.6~79.7] E(R)=+0.426
- FWD×中立・もみあい: 10/15 = 66.7% CI[41.7~84.8] E(R)=+0.555

### トレンド別 (IS)
- IS×下降: 19/79 = 24.1% CI[16.0~34.5] E(R)=-0.439
- IS×中立・もみあい: 24/72 = 33.3% E(R)=-0.222
- IS×上昇: 25/45 = 55.6% CI[41.2~69.1] E(R)=+0.296

### 月別推移 (FWD)
- 2026-06: 21/26 = 80.8% CI[62.1~91.5] E(R)=+0.884
- 2026-07: 22/35 = 62.9% CI[46.3~76.8] E(R)=+0.466

## 判定
- **H1 通過A**: 非金属FWD 70.6%≥60% ✅、CI下限57.0%≥43% ✅
- **H2 通過A**: 構成シフト寄与≒0pp、性能シフト36.2ppが主因 ✅
- 全4tier中、tier=goodのみ35pp超の改善（elite+6.9pp、neutral+2.8pp、avoid-9.1pp）
- rsi×IS33.7%→FWD83.3% と 下降IS24.1%→FWD78.6%の二重改善が主ドライバー
- FWD N=61<80 → tracker [q] は蓄積中（⛔反証確定打なし）
- 注意: もし N=80到達でCI上限>0が継続 → #030/#032と同じく⛔反証シナリオへ
