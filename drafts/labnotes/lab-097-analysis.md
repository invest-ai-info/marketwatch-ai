# lab-097 解析ノート

## 基準日
2026-09-13（JST）

## 本日の優先度
Priority ①: `trend=上昇 × reversal_long`（✅昇格済み・demote_strikes=1でCIギリギリ境界）

## 採択仮説
**上昇トレンド中の逆張り買い（rsi_oversold_bounce / bb_lower_touch × Long）の前向き成績**
- トラッカー: id=`auto_reversal_long-True_trend-上昇`, status=promoted, demote_strikes=1
- 登録日: 2026-06-22
- 前回記事: なし（今回が初記事）

## 使用スクリプト
```python
import json, math
from collections import defaultdict

with open('signals-log.json') as f:
    data = json.load(f)

valid_outcomes = {'tp1','tp2','sl','expired'}
REVERSAL_LONG_SIGNALS = {'rsi_oversold_bounce', 'bb_lower_touch'}  # signal_lab_verify.py 定義

GROUPS = {
    'metal': {'GC=F','SI=F'},
    'index': {'NKD=F','ES=F','NQ=F','YM=F','^FTSE'},
    'jpy_fx': {'USDJPY=X','EURJPY=X','GBPJPY=X','AUDJPY=X','USDJPY','EURJPY','GBPJPY','AUDJPY'},
    'other_fx': {'EURUSD','GBPUSD','AUDUSD','EURAUD','GBPAUD','EURUSD=X','GBPUSD=X','AUDUSD=X','EURAUD=X','GBPAUD=X'},
    'btc': {'BTC-USD'},
    'oil': {'CL=F'},
}

def is_closed(e): return e.get('outcome') in valid_outcomes
def win(e): return 1 if e.get('outcome') in ('tp1','tp2') else 0
def is_reversal_long(e):
    ps = e.get('primary_signal','') or ''
    direction = e.get('direction','') or ''
    return 'ロング' in direction and ps in REVERSAL_LONG_SIGNALS

def get_trend(e):
    ta = e.get('trend_alignment')
    if ta and isinstance(ta, dict):
        t = ta.get('higher_tf_trend') or ''
        if '上昇' in t: return '上昇'
        elif '下降' in t: return '下降'
        elif '中立' in t or 'もみあい' in t: return '中立・もみあい'
    return 'unknown'
```

## 生出力

```
Total closed: 4432  IS(~2026-06-22): 964  FWD: 3468

IS (in-sample): n=101, k=54, win=53.5%, CI[43.8~62.9%], E(R)=0.248 RCI[0.019~0.476]
FWD (前向き): n=307, k=144, win=46.9%, CI[41.4~52.5%], E(R)=0.114 RCI[-0.015~0.243]

=== Signal breakdown (FWD) ===
  bb_lower_touch: n=232, k=99, win=42.7%, CI[36.5~49.1%]
  rsi_oversold_bounce: n=75, k=45, win=60.0%, CI[48.7~70.3%]

=== Group breakdown (FWD) ===
  jpy_fx: n=91, k=42, win=46.2%, CI[36.3~56.3%], E(R)=0.132
  index: n=81, k=31, win=38.3%, CI[28.4~49.2%], E(R)=-0.095
  other_fx: n=75, k=39, win=52.0%, CI[40.9~62.9%], E(R)=0.213
  btc: n=23, k=13, win=56.5%, CI[36.8~74.4%], E(R)=0.319
  metal: n=21, k=11, win=52.4%, CI[32.4~71.7%], E(R)=0.222
  oil: n=14, k=8, win=57.1%, CI[32.6~78.6%], E(R)=0.333

=== Timeframe breakdown (FWD) ===
  1h: n=177, k=82, win=46.3%, CI[39.1~53.7%]
  4h: n=108, k=47, win=43.5%, CI[34.5~52.9%]
  1d: n=22, k=15, win=68.2%, CI[47.3~83.6%]

=== Context comparisons (FWD) ===
  上昇×逆張り買い: n=307, k=144, win=46.9%, CI[41.4~52.5%], E(R)=0.114
  上昇×順張り買い(非逆張り): n=633, k=246, win=38.9%, CI[35.1~42.7%], E(R)=-0.076
  上昇×ショート: n=370, k=145, win=39.2%, CI[34.4~44.3%], E(R)=-0.053
  全体×ロング: n=2612, k=1138, win=43.6%, CI[41.7~45.5%], E(R)=0.030

=== All-time combined (IS+FWD) ===
  全体: n=408, k=198, win=48.5%, CI[43.7~53.4%], E(R)=0.147 RCI[0.035~0.260]
```

## 交絡検討
- FWD全体46.9%は損益分岐43%超え
- 内部分裂: rsi_oversold_bounce(60%) vs bb_lower_touch(42.7%) → 17.3pp の差
- 指数グループの弱さ(38.3%)が全体を引き下げ
- 上昇×逆張りは上昇×順張り(38.9%)より7.8pp優位 → 「上昇中でも押し目逆張りが有効」

## トラッカー状態
- status: promoted
- demote_strikes: 1
- FWD n=299（tracker），k=144, avgR=0.124, rci_lo=-0.033（CIギリギリ負値）
- 全期間合算 n=408, k=198, win=48.5%, CI[43.7~53.4%], E(R)=0.147 RCI[0.035~0.260]（正値確認）
