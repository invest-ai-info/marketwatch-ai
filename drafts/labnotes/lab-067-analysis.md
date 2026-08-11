# lab-067-analysis.md
# 記事 #067: RSI売られすぎ逆張り買い(rsi_oversold_bounce) 前向きN=178
# 基準日: 2026-08-12 (JST)

## 分析スクリプト

```python
import json, math

with open('signals-log.json') as f:
    data = json.load(f)
signals = data if isinstance(data, list) else data.get('signals', [])

GROUPS = {
    'metal': {'GC=F','SI=F'},
    'index': {'NKD=F','ES=F','NQ=F','YM=F','^FTSE'},
    'jpy_fx': {'USDJPY=X','EURJPY=X','GBPJPY=X','AUDJPY=X'},
    'other_fx': {'EURUSD=X','GBPUSD=X','AUDUSD=X','EURAUD=X','GBPAUD=X'},
    'btc': {'BTC-USD'},
    'oil': {'CL=F'},
}
def get_group(ticker):
    for g, tickers in GROUPS.items():
        if ticker in tickers:
            return g
    return 'other'

def wilson(k, n, z=1.96):
    if n == 0: return (0,0)
    p = k/n
    lo = (p + z*z/(2*n) - z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))) / (1 + z*z/n)
    hi = (p + z*z/(2*n) + z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))) / (1 + z*z/n)
    return (max(0,lo), min(1,hi))

REG_DATE = "2026-06-17"  # rsi_oversold_bounce 登録日 (前向き基準)

def is_win(s): return s.get('outcome') in ('tp1','tp2')
def is_closed(s): return s.get('outcome') in ('tp1','tp2','sl')
def is_fwd(s): return s.get('fired_at','') >= REG_DATE

osb = [s for s in signals if s.get('primary_signal') == 'rsi_oversold_bounce']
osb_closed = [s for s in osb if is_closed(s)]
osb_fwd = [s for s in osb if is_fwd(s)]
osb_fwd_closed = [s for s in osb_fwd if is_closed(s)]

print(f"全体 closed: k={sum(1 for s in osb_closed if is_win(s))}, n={len(osb_closed)}")

# FWD期間のみ
print(f"FWD closed: k={sum(1 for s in osb_fwd_closed if is_win(s))}, n={len(osb_fwd_closed)}")

# group別 全期間
for g in ['index','jpy_fx','other_fx','metal']:
    sub = [s for s in osb_closed if get_group(s.get('ticker','')) == g]
    k = sum(1 for s in sub if is_win(s))
    n = len(sub)
    lo,hi = wilson(k,n)
    print(f"group={g}: k={k}, n={n}, wr={k/n:.1%}, WCI=[{lo:.1%},{hi:.1%}]")

# trend別 全期間
for t in ['上昇','下降','中立・もみあい']:
    sub = [s for s in osb_closed if s.get('trend_alignment',{}).get('higher_tf_trend') == t]
    k = sum(1 for s in sub if is_win(s))
    n = len(sub)
    lo,hi = wilson(k,n)
    print(f"trend={t}: k={k}, n={n}, wr={k/n:.1%}, WCI=[{lo:.1%},{hi:.1%}]")

# tf別 全期間
for tf in ['1h','4h']:
    sub = [s for s in osb_closed if s.get('timeframe') == tf]
    k = sum(1 for s in sub if is_win(s))
    n = len(sub)
    lo,hi = wilson(k,n)
    print(f"tf={tf}: k={k}, n={n}, wr={k/n:.1%}, WCI=[{lo:.1%},{hi:.1%}]")

# bb_lower_touch 比較対照
bbt = [s for s in signals if s.get('primary_signal') == 'bb_lower_touch' and is_closed(s)]
k = sum(1 for s in bbt if is_win(s)); n = len(bbt)
lo,hi = wilson(k,n)
print(f"bb_lower_touch: k={k}, n={n}, wr={k/n:.1%}, WCI=[{lo:.1%},{hi:.1%}]")
```

## 実行結果

```
全体 closed: k=149, n=311
FWD closed: k=97, n=178

group=index:    k=40,  n=64,  wr=62.5%, WCI=[50.0%,73.6%]
group=jpy_fx:   k=25,  n=55,  wr=45.5%, WCI=[32.7%,58.6%]
group=other_fx: k=38,  n=79,  wr=48.1%, WCI=[37.2%,59.2%]
group=metal:    k=19,  n=60,  wr=31.7%, WCI=[20.6%,44.9%]

trend=上昇:           k=41, n=63,  wr=65.1%, WCI=[52.5%,75.8%]
trend=下降:           k=57, n=134, wr=42.5%, WCI=[34.3%,51.2%]
trend=中立・もみあい: k=50, n=112, wr=44.6%, WCI=[35.6%,54.0%]

tf=1h: k=86, n=195, wr=44.1%, WCI=[37.3%,51.1%]
tf=4h: k=56, n=104, wr=53.8%, WCI=[44.1%,63.3%]

bb_lower_touch: k=268, n=596, wr=45.0%, WCI=[41.0%,49.0%]
```

## 前向きトラッカー値（signal_lab_tracker.py より、2026-08-12）

- FWD 全体: 97/178=54.5%, E(R)=+0.272, RCI[+0.00, +0.54]（cluster-corrected）
- trend=上昇 FWD: 32/43=74.4%
- trend=中立 FWD:  32/53=60.4%
- trend=下降 FWD:  33/82=40.2%
- tf=4h FWD:  37/55=67.3%
- tf=1h FWD:  53/114=46.5%
- group=index FWD:   20/29=69.0%
- group=jpy_fx FWD:  23/35=65.7%
- group=other_fx FWD: 24/56=42.9%

### 前向き時系列 3分割（FWD期間）
- FWD-1 (2026-06-17〜06-25): 20/59=33.9%, E(R)=-0.314
- FWD-2 (2026-06-25〜07-17): 38/59=64.4%, E(R)=+0.754
- FWD-3 (2026-07-21〜08-11): 39/60=65.0%, E(R)=+0.775

## 主要発見

1. FWD RCI下限が遂にゼロ到達（N=178, 以前はN=168で[-0.058,+0.474]）
2. 上昇トレンドで74%（FWD）——「逆張り」でも上昇トレンドに乗るほうが有利
3. 4H足: FWD 67.3% > 1H足: FWD 46.5%（#015の全体的4H劣勢と逆転）
4. jpy_fx: IS(全期間)45.5% → FWD 65.7%（政策・介入期待で構造変化?）
5. 前向き時系列: 初期(6/17〜6/25)は33.9%と軟調→後半2区間は65%で安定
