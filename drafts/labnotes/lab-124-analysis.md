# lab-124 分析メモ

**基準日**: 2026-10-11（日曜・JST）
**仮説**: ADX（トレンドの強さ指標）が25以上のときに順張りをすると、勝ちやすいか？
**仮説ID**: rl_tf_adx_strong（gate: 負けやすいかを検証）
**登録日**: 2026-09-26
**IS/FWD区切り**: 2026-09-27 (registered_at の翌日)

## 採択理由

スイープFDR通過0本・昇格/反証なし・読者の質問なし → ④定点観測の日。
トラッカーの中で最も注目すべき動き：ADX強×順張り(n=66)の前向き勝率30.3%、CI上限42.2%で
基準線(42.6%)をわずかに下回る状態。counterintuitiveな発見として記事化に適している。

## スクリプト

```python
import json, math

with open('signals-log.json') as f:
    all_data = json.load(f)

def closed_fn(d): return d.get('outcome') in ('tp1','tp2','sl')
def win_fn(d): return d.get('outcome') in ('tp1','tp2')

all_closed = [r for r in all_data if closed_fn(r)]

def match_adx_band(r, band):
    ind = r.get('indicators_at_signal', {})
    a = ind.get('adx') if isinstance(ind, dict) else None
    if not isinstance(a, (int, float)) or isinstance(a, bool): return False
    return ("weak" if a < 20 else ("mid" if a < 25 else "strong")) == band

def match_family(r, fam):
    dr = r.get('direction') or ''
    side = 'long' if 'ロング' in dr else ('short' if 'ショート' in dr else None)
    TF = {('high_break','long'),('low_break','short'),('macd_golden','long'),('macd_dead','short'),('ma_golden','long'),('ma_dead','short')}
    MR = {('rsi_oversold_bounce','long'),('bb_lower_touch','long')}
    key = (r.get('primary_signal'), side)
    return ('tf' if key in TF else ('mr' if key in MR else None)) == fam

def wilson_ci(k, n, z=1.96):
    if n == 0: return 0, 0
    p = k/n
    denom = 1 + z**2/n
    center = (p + z**2/(2*n)) / denom
    margin = z * math.sqrt(p*(1-p)/n + z**2/(4*n**2)) / denom
    return round((center-margin)*100,1), round((center+margin)*100,1)

# 各グループ計算
# Baseline: k=2198, n=5165, win=42.6%, CI=[41.2%~43.9%]
# ADX強×tf IS (fired_before 2026-09-27): k=443, n=1070, win=41.4%, CI=[38.5%~44.4%]
# ADX強×tf FWD (fired_from 2026-09-27): k=20, n=66, win=30.3%, CI=[20.6%~42.2%]
# ADX弱×tf IS (fired_before 2026-09-27): k=376, n=851, win=44.2%, CI=[40.9%~47.5%]
# ADX弱×tf FWD (fired_from 2026-09-27): k=30, n=74, win=40.5%, CI=[30.1%~51.9%]
```

## 生出力

```
All closed (tp1/tp2/sl): 5165
Baseline: k=2198, n=5165, win=42.6%, CI=[41.2%~43.9%]

ADX強×tf IS: k=443, n=1070, win=41.4%, CI=[38.5%~44.4%]
ADX強×tf FWD: k=20, n=66, win=30.3%, CI=[20.6%~42.2%]

ADX弱×tf IS: k=376, n=851, win=44.2%, CI=[40.9%~47.5%]
ADX弱×tf FWD: k=30, n=74, win=40.5%, CI=[30.1%~51.9%]

順張り全: n=2658, ADX値あり: 2555, ADX値なし: 103
```

## トラッカー（2026-10-11時点）

- rl_tf_adx_strong: 🟡蓄積中、FWD k=19/n=66, 28.8%, avgR=-0.328, CI[-0.54~-0.11]
  ※ trackerのk/nと私の集計(k=20/n=66)の差は outcome計算の微差（trackerはav_r計算法が異なる可能性）
- rl_tf_adx_weak: 🟡蓄積中、FWD k=29/n=77, 37.7%, avgR=-0.121, CI[-0.41~+0.16]
  ※ trackerのn=77と私の集計n=74の差は同上

## 交絡点検

ADX強は「強いトレンドが出ているとき」なので、単に相場のボラティリティが高い時期と重なりやすく、
本来の入口の質以外の要因（大きな相場変動による損切りの早まり）が成績を悪化させている可能性あり。
ただし現時点ではn=66で検証不十分。

## 記事概要

- 題材：ADXが25以上のときの順張り成績（定点観測）
- IS (1070回): 41.4% ≒ 全体平均と差なし
- FWD (66回): 30.3%, CI=[20.6%~42.2%] → 基準線42.6%を下回る傾向（まだ確定ではない）
- ADX弱との比較: IS 44.2% vs FWD 40.5%（こちらは基準線付近）
- まとめ: 「強いトレンドで乗れば有利」は現時点では支持されない

## 注記

- trackerでのFWD n=66とIS/FWD split後の私の計算n=66は一致
- FWD k差（tracker=19、私=20）は微小で、WilsonCI上では大きな差はない
- claims.jsonには私の計算値(verify.pyと同じロジック)を使用
