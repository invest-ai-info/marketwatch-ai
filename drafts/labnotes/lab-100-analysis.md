# Lab #100 Analysis — trend=上昇×reversalL 昇格後157日の内部構造

基準日: 2026-09-16 (JST)
登録日: 2026-06-22
仮説: 上昇トレンド中の逆張り買い（rsi_oversold_bounce / bb_lower_touch × trend=上昇）

## 採択理由

priority①: tracker ✅昇格仮説（trend=上昇×reversalL）が #097（2026-09-13 エスカレ未公開）以来
公開された記事がなく、昇格ストーリーが未告知のまま。今日のトラッカー更新（N=304→307）で
最新状態を解析する好機。FDRスイープ通過0本のため ②③ 対象なし。

## 検証スクリプト

```python
import json, math, random

with open('/home/user/marketwatch-ai/signals-log.json') as f:
    logs = json.load(f)

REGISTERED = "2026-06-22"
REV = {"rsi_oversold_bounce", "bb_lower_touch"}

def is_closed(s): return s.get('outcome') in ('tp1','tp2','sl')
def win(s): return s.get('outcome') in ('tp1','tp2')
def get_r(s):
    o = s.get('outcome','')
    if o == 'tp1': return 1.33
    if o == 'tp2': return 2.0
    if o == 'sl':  return -1.0
    return None

def get_trend(s):
    ta = s.get('trend_alignment')
    if isinstance(ta, dict): return ta.get('higher_tf_trend')
    return None

def is_reversal_long(s):
    return ('ロング' in (s.get('direction') or '')) and s.get('primary_signal') in REV

def get_group(s):
    tk = s.get('ticker','')
    m = {'GC=F':'metal','SI=F':'metal','CL=F':'oil',
         'NKD=F':'index','ES=F':'index','NQ=F':'index','YM=F':'index','^FTSE':'index',
         'BTC-USD':'btc',
         'USDJPY':'jpy_fx','EURJPY':'jpy_fx','GBPJPY':'jpy_fx','AUDJPY':'jpy_fx',
         'EURUSD':'other_fx','GBPUSD':'other_fx','AUDUSD':'other_fx',
         'EURAUD':'other_fx','GBPAUD':'other_fx'}
    return m.get(tk,'other')

def get_tf(s):
    tf_raw = s.get('timeframe','')
    if '1H' in tf_raw or '1h' in tf_raw: return '1h'
    if '4H' in tf_raw or '4h' in tf_raw: return '4h'
    if '1D' in tf_raw or '1d' in tf_raw or '日足' in tf_raw: return '1d'
    return tf_raw
```

## 生出力

```
=== trend=上昇×reversalL ===
全件: 408 (IS:101 FWD:307)

全期間: k=200 n=408 pct=49.0% CI[44.2%, 53.9%] avgR=+0.142 RCI[+0.028, +0.251]
IS:     k=54  n=101 pct=53.5% CI[43.8%, 62.9%] avgR=+0.246 RCI[+0.015, +0.476]
FWD:    k=146 n=307 pct=47.6% CI[42.0%, 53.1%] avgR=+0.108 RCI[-0.021, +0.230]

--- FWD グループ別 ---
  metal:    k=11 n=21  pct=52.4% CI[32.4%, 71.7%] avgR=+0.220 RCI[-0.223, +0.664]
  index:    k=31 n=80  pct=38.8% CI[28.8%, 49.7%] avgR=-0.097 RCI[-0.330, +0.165]
  oil:      k=9  n=15  pct=60.0% CI[35.7%, 80.2%] avgR=+0.398 RCI[-0.223, +0.864]
  btc:      k=14 n=25  pct=56.0% CI[37.1%, 73.3%] avgR=+0.305 RCI[-0.161, +0.771]

--- FWD 時間足別 ---
  1h: k=83  n=178 pct=46.6% CI[39.4%, 54.0%] avgR=+0.086 RCI[-0.084, +0.257]
  4h: k=48  n=107 pct=44.9% CI[35.8%, 54.3%] avgR=+0.045 RCI[-0.173, +0.263]
  1d: k=15  n=22  pct=68.2% CI[47.3%, 83.6%] avgR=+0.589 RCI[+0.059, +1.012]

--- FWD シグナル種別 ---
  rsi_oversold_bounce: k=45 n=73  pct=61.6% CI[50.2%, 71.9%] avgR=+0.436 RCI[+0.181, +0.692]
  bb_lower_touch:      k=101 n=234 pct=43.2% CI[37.0%, 49.6%] avgR=+0.006 RCI[-0.134, +0.155]

--- IS グループ別 ---
  IS index: k=35 n=51 pct=68.6% CI[55.0%, 79.7%] avgR=+0.599 RCI[+0.279, +0.873]

--- FWD 上昇×ロング全体(N=936) vs 逆張り(N=307) vs 順張り(N=629) ---
  上昇×ロング全体:  k=393 n=936 pct=42.0% CI[38.9%, 45.2%] avgR=-0.022 RCI[-0.096, +0.053]
  上昇×逆張り(reversal): k=146 n=307 pct=47.6% RCI[-0.021, +0.230]
  上昇×順張り(non-reversal): k=247 n=629 pct=39.3% CI[35.5%, 43.1%] avgR=-0.085 RCI[-0.170, +0.004]
```

## 交絡点検

1. IS偏り: IS期間(N=101)は指数が51件と過半を占め、IS指数68.6%が全体を押し上げている。
   FWD期間は指数が増えてN=80になるが勝率38.8%に急落 → IS/FWD乖離の主因は指数グループ
2. シグナル種別偏り: RSI型(n=73)とBB型(n=234)で3.2:1の非対称。BB型が母数を支配
3. 1d足 N=22小サンプル: RCI下限+0.059はプラスだが信頼区間が広い
4. 順張り比較の方法: reversal_long=falseは filter不可なので参考値扱い（全体からreversalを引いた補集合）

## 採択仮説

「上昇トレンド中の逆張り買いは、RSI売られすぎ型では期待値プラスが統計的に有意だが、
BB下限タッチ型では損益分岐付近にとどまる（FWD N=307・IS/FWD解剖）」

## 前向き宣言（この記事時点）

- RSI型 RCI下限 > +0.10 かつ N ≥ 100 → 単独昇格候補（現在 N=73・継続観察）
- BB型 RCI下限 > 0 → 将来の昇格条件（現在マイナス）
- 全体の昇格状態は今後もデメリット2回連続降格が出なければ維持
