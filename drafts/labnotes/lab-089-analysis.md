# lab-088-analysis.md — RSI売られすぎ逆張り買い FWD N=287 CI全域プラス解析

## 基準日
2026-09-04（JST）

## 仮説
`signal=rsi_oversold_bounce × direction=long`（RSI売られすぎ逆張り買い）の
前向きトラッカー N=287 でCI全域プラスに到達。IS期間39.1%→FWD 53.0%の転換を解析。

## 事前宣言（CLAIM）
- H1: FWD全体のE(R) RCI下限>0（昇格条件）
- H2: FWD 4H足のE(R) > 1H足（時間足優位の継続）
- H3: FWD jpy_fx のE(R) RCI下限>0
- H4: FWD trend=上昇のE(R) RCI下限>0

## 検証スクリプト（Python反実仮想集計）

```python
import json, math
from collections import Counter

with open('signals-log.json') as f:
    data = json.load(f)
signals = data if isinstance(data, list) else data.get('signals', [])

EXPANSION_TICKERS = {'INTC','BABA','TSM','005930.KS','ASML','ARM','SMCI','NKY','SOX','^SOX'}
closed = [s for s in signals 
          if s.get('outcome') in ('sl','tp1','tp2')
          and s.get('ticker','') not in EXPANSION_TICKERS]

GROUP_MAP = {
    'GC=F': 'metal', 'SI=F': 'metal',
    'NKD=F': 'index', 'ES=F': 'index', 'NQ=F': 'index', 'YM=F': 'index', '^FTSE': 'index',
    'BTC-USD': 'btc', 'CL=F': 'oil',
    'USDJPY=X': 'jpy_fx', 'EURJPY=X': 'jpy_fx', 'GBPJPY=X': 'jpy_fx', 'AUDJPY=X': 'jpy_fx',
    'USDJPY': 'jpy_fx', 'EURJPY': 'jpy_fx', 'GBPJPY': 'jpy_fx', 'AUDJPY': 'jpy_fx',
    'EURUSD=X': 'other_fx', 'GBPUSD=X': 'other_fx', 'AUDUSD=X': 'other_fx',
    'EURAUD=X': 'other_fx', 'GBPAUD=X': 'other_fx',
}
REG_DATE = '2026-06-16'

def group(s): return GROUP_MAP.get(s.get('ticker',''), 'other')
def tf(s): return s.get('timeframe', '?')
def is_long(s): return 'ロング' in s.get('direction','')
def trend(s):
    ht = (s.get('trend_alignment', {}) or {}).get('higher_tf_trend', '')
    if '上昇' in str(ht): return '上昇'
    if '下降' in str(ht): return '下降'
    if '中立' in str(ht) or 'もみあい' in str(ht): return '中立・もみあい'
    return 'unknown'
def is_win(s): return s.get('outcome') in ('tp1','tp2')
def r_value(s):
    o = s.get('outcome')
    if o == 'tp1': return 1.33
    if o == 'tp2': return 2.0
    return -1.0
def is_forward(s): return s.get('fired_at', '') >= REG_DATE
def is_rsi_os(s): return s.get('primary_signal') == 'rsi_oversold_bounce' and is_long(s)
```

## 生出力

Total closed (standard): 4100

=== rsi_oversold_bounce (long) ===
  全期間: k=204 n=420 (48.6%) WCI[43.8%,53.3%] E(R)=+0.132 RCI[+0.020,+0.243]
  IS (pre-2026-06-16): k=52 n=133 (39.1%) WCI[31.2%,47.6%] E(R)=-0.089 RCI[-0.283,+0.105]
  FWD (post-2026-06-16): k=152 n=287 (53.0%) WCI[47.2%,58.7%] E(R)=+0.234 RCI[+0.099,+0.369]

--- FWD by timeframe ---
  FWD tf=1h: k=86 n=190 (45.3%) WCI[38.3%,52.4%] E(R)=+0.055 RCI[-0.111,+0.220]
  FWD tf=4h: k=56 n=85 (65.9%) WCI[55.3%,75.1%] E(R)=+0.535 RCI[+0.299,+0.771]
  FWD tf=1d: k=10 n=12 (83.3%) WCI[55.2%,95.3%] E(R)=+0.942 RCI[+0.429,+1.455]

--- IS by timeframe ---
  IS tf=1h: k=33 n=81 (40.7%) WCI[30.7%,51.6%] E(R)=-0.051 RCI[-0.302,+0.200]
  IS tf=4h: k=19 n=49 (38.8%) WCI[26.4%,52.8%] E(R)=-0.097 RCI[-0.418,+0.225]

--- FWD by group ---
  FWD group=index: k=34 n=68 (50.0%) WCI[38.4%,61.6%] E(R)=+0.165 RCI[-0.114,+0.444]
  FWD group=jpy_fx: k=32 n=53 (60.4%) WCI[46.9%,72.4%] E(R)=+0.407 RCI[+0.097,+0.717]
  FWD group=other_fx: k=45 n=90 (50.0%) WCI[39.9%,60.1%] E(R)=+0.165 RCI[-0.077,+0.407]
  FWD group=metal: k=23 n=41 (56.1%) WCI[41.0%,70.1%] E(R)=+0.307 RCI[-0.051,+0.665]
  FWD group=btc: k=7 n=13 (53.8%) WCI[29.1%,76.8%] E(R)=+0.255 RCI[-0.403,+0.912]
  FWD group=oil: k=11 n=22 (50.0%) WCI[30.7%,69.3%] E(R)=+0.165 RCI[-0.333,+0.663]

--- FWD by trend ---
  FWD trend=上昇: k=49 n=74 (66.2%) WCI[54.9%,76.0%] E(R)=+0.543 RCI[+0.290,+0.796]
  FWD trend=中立・もみあい: k=55 n=101 (54.5%) WCI[44.8%,63.8%] E(R)=+0.269 RCI[+0.041,+0.496]
  FWD trend=下降: k=48 n=112 (42.9%) WCI[34.1%,52.1%] E(R)=-0.001 RCI[-0.216,+0.213]

--- FWD 4H combinations ---
  FWD 4h x jpy_fx: k=16 n=17 (94.1%) WCI[73.0%,99.0%] E(R)=+1.193 RCI[+0.924,+1.462]
  FWD 4h x other_fx: k=19 n=35 (54.3%) WCI[38.2%,69.5%] E(R)=+0.265 RCI[-0.125,+0.655]
  FWD 4h x index: k=9 n=14 (64.3%) WCI[38.8%,83.7%] E(R)=+0.498 RCI[-0.109,+1.105]
  FWD 4h x metal: k=8 n=11 (72.7%) WCI[43.4%,90.3%] E(R)=+0.695 RCI[+0.051,+1.338]

--- FWD 1H combinations ---
  FWD 1h x jpy_fx: k=13 n=33 (39.4%) WCI[24.7%,56.3%] E(R)=-0.082 RCI[-0.477,+0.312]
  FWD 1h x other_fx: k=24 n=53 (45.3%) WCI[32.7%,58.5%] E(R)=+0.055 RCI[-0.260,+0.370]
  FWD 1h x index: k=25 n=54 (46.3%) WCI[33.7%,59.4%] E(R)=+0.079 RCI[-0.234,+0.391]

--- FWD time periods ---
  P1(06-16~07-17): k=54 n=111 (48.6%) WCI[39.6%,57.8%] E(R)=+0.134 RCI[-0.084,+0.351]
  P2(07-17~08-18): k=53 n=80 (66.2%) WCI[55.4%,75.7%] E(R)=+0.544 RCI[+0.301,+0.787]
  P3(08-18~09-04): k=45 n=96 (46.9%) WCI[37.2%,56.8%] E(R)=+0.092 RCI[-0.142,+0.326]

--- IS by group ---
  IS group=index: k=20 n=35 (57.1%) WCI[40.9%,72.0%] E(R)=+0.331 RCI[-0.056,+0.719]
  IS group=jpy_fx: k=2 n=20 (10.0%) WCI[2.8%,30.1%] E(R)=-0.767 RCI[-1.081,-0.453]
  IS group=other_fx: k=14 n=23 (60.9%) WCI[40.8%,77.8%] E(R)=+0.418 RCI[-0.057,+0.893]
  IS group=metal: k=4 n=31 (12.9%) WCI[5.1%,28.9%] E(R)=-0.699 RCI[-0.979,-0.420]

=== bb_lower_touch (long, FWD) comparison ===
  FWD: k=276 n=634 (43.5%) WCI[39.7%,47.4%] E(R)=+0.014 RCI[-0.076,+0.104]
  IS: k=75 n=175 (42.9%) WCI[35.8%,50.3%] E(R)=-0.001 RCI[-0.173,+0.170]

--- RSI FWD trend=上昇 details ---
  上昇 x jpy_fx: k=14 n=19 (73.7%) WCI[51.2%,88.2%] E(R)=+0.717 RCI[+0.243,+1.191]
  上昇 x other_fx: k=12 n=20 (60.0%) WCI[38.7%,78.1%] E(R)=+0.398 RCI[-0.115,+0.911]
  上昇 x index: k=12 n=19 (63.2%) WCI[41.0%,80.9%] E(R)=+0.472 RCI[-0.048,+0.991]
  上昇 x 1h: k=18 n=35 (51.4%) WCI[35.6%,67.0%] E(R)=+0.198 RCI[-0.193,+0.590]
  上昇 x 4h: k=22 n=30 (73.3%) WCI[55.6%,85.8%] E(R)=+0.709 RCI[+0.334,+1.084]

## 判定
- H1: FWD全体 E(R)=+0.234 RCI[+0.099,+0.369] → ✅ CI全域プラス
- H2: 4H E(R)=+0.535 >> 1H E(R)=+0.055 → ✅ 4H優位（差20.6pp・差0.480R）
- H3: jpy_fx FWD E(R)=+0.407 RCI[+0.097,+0.717] → ✅ CI全域プラス
- H4: 上昇 FWD E(R)=+0.543 RCI[+0.290,+0.796] → ✅ CI全域プラス

通過A（4条件全クリア）

## 交絡点検
1. jpy_fx IS期間10.0% vs FWD 60.4%: IS期間の不振がIS全体39.1%を押し下げていた主因の一つ（金属同様）
2. 4H足優位はjpy_fx偏在（FWD 4H×jpy_fx=94.1%、N=17）で一部説明できるが、4H全体N=85でも65.9%と高水準
3. P2(07-17~08-18)の66%高勝率が全体を押し上げ、P3は47%に軟化（下降×P3が多い可能性）
4. 1D足(N=12)は83.3%だが小サンプル→参考値のみ

## 昇格ストライク状況
- #082時点: promote_strikes=1（RCI_lo=+0.005→翌日-0.007でリセット）
- 本日: FWD N=287 E(R)=+0.234 RCI[+0.099,+0.369]→CI全域プラス再到達
- 昇格には「2回連続」が必要→次のチェックポイントでCI>0が続けば✅昇格

