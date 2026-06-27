# Lab-023 解析ノート
# 仮説: RSI売られすぎ逆張り（rsi_oversold_bounce）vs BB下限タッチ（bb_lower_touch）の系統的性能差
# 基準日: 2026-06-28 JST
# 総クローズ数: 1160件（tp1/sl のみ）

## 事前宣言基準
- H1: rsi_oversold_bounce 全体のCI上限 < 43%（棄却確認→通過A）
- H2: bb_lower_touch の勝率 - rsi_oversold_bounce の勝率 ≥ 10pp

## 動機
- 前向きトラッカーで「売られすぎ逆張り買い(rsi_oversold_bounce)」がN=59・30%・R-0.288 CI[-0.56~-0.01]（CI上限 barely < 0）
- #009（jpy_fx方向性）・#014（bb_lower×jpy_fx 60%）で RSI vs BB の断片的証拠
- 今回は全データ1160件で正式な種別比較を実施

---

## 生出力（Pythonスクリプト実行結果）

```
=== RSI vs BB 逆張りシグナル型比較 (#023) / 総クローズ数: 1160 ===

--- 全体 ---
rsi_oversold_bounce (全体)    k= 70/n=192   36.5%  CI[ 30.0%~ 43.5%]
bb_lower_touch (全体)         k=115/n=275   41.8%  CI[ 36.1%~ 47.7%]

--- 方向確認（全件がロングのはず） ---
rsi_oversold_bounce: Long=192, Short=0
bb_lower_touch:      Long=275, Short=0
（両シグナルとも純粋なロング逆張りシグナル）

--- グループ別 rsi_oversold_bounce ---
rsi x index     k= 24/n= 40   60.0%  CI[ 44.6%~ 73.7%]
rsi x jpy_fx    k=  6/n= 31   19.4%  CI[  9.2%~ 36.3%]
rsi x other_fx  k= 19/n= 50   38.0%  CI[ 25.9%~ 51.8%]
rsi x metal     k=  6/n= 38   15.8%  CI[  7.4%~ 30.4%]
rsi x btc       k=  5/n= 17   29.4%  CI[ 13.3%~ 53.1%]
rsi x oil       k= 10/n= 16   62.5%  CI[ 38.6%~ 81.5%]

--- グループ別 bb_lower_touch ---
bb x index      k= 32/n= 60   53.3%  CI[ 40.9%~ 65.4%]
bb x jpy_fx     k= 32/n= 55   58.2%  CI[ 45.0%~ 70.3%]
bb x other_fx   k= 31/n= 79   39.2%  CI[ 29.2%~ 50.3%]
bb x metal      k= 11/n= 46   23.9%  CI[ 13.9%~ 37.9%]
bb x btc        k=  5/n= 25   20.0%  CI[  8.9%~ 39.1%]
bb x oil        k=  4/n= 10   40.0%  CI[ 16.8%~ 68.7%]

--- トレンド別 rsi_oversold_bounce ---
rsi x 上昇        k= 13/n= 25   52.0%  CI[ 33.5%~ 70.0%]
rsi x 下降        k= 32/n= 94   34.0%  CI[ 25.3%~ 44.1%]
rsi x 中立        k= 24/n= 71   33.8%  CI[ 23.9%~ 45.4%]

--- トレンド別 bb_lower_touch ---
bb x 上昇         k= 47/n= 86   54.7%  CI[ 44.2%~ 64.8%]
bb x 下降         k= 30/n= 90   33.3%  CI[ 24.4%~ 43.6%]
bb x 中立         k= 38/n= 97   39.2%  CI[ 30.0%~ 49.1%]

--- 時間足別 ---
rsi x 1h          k= 44/n=121   36.4%  CI[ 28.3%~ 45.2%]
bb x 1h           k= 70/n=157   44.6%  CI[ 37.0%~ 52.4%]
rsi x 4h          k= 26/n= 68   38.2%  CI[ 27.6%~ 50.1%]
bb x 4h           k= 40/n=111   36.0%  CI[ 27.7%~ 45.3%]
```

## 事前宣言基準の検証
- H1: rsi CI上限 = 43.5% > 43% → **FAIL（0.5ppで未達）**
- H2: bb-rsi 差 = 5.4pp < 10pp → **FAIL（4.6pp不足）**

## 探索的発見（事前宣言外・次回検証候補）
- jpy_fx × rsi: 19.4% (6/31) CI[9.2%~36.3%] E(R)=-0.55R
- jpy_fx × bb:  58.2% (32/55) CI[45.0%~70.3%] E(R)=+0.36R
- **差: 38.8pp、E(R)差: +0.91R** → 同一資産クラスで最大級の信号品質差
- index × rsi: 60.0% (24/40) E(R)=+0.40R
- index × bb:  53.3% (32/60) E(R)=+0.24R
- → 指数では逆にRSIがBBを上回る（逆転！）

## 期待値計算式
E(R) = (勝率 × TP1R:1.33) - ((1-勝率) × SL:1.0) = 2.33 × 勝率 - 1
（TP1=2×ATR, SL=1.5×ATR → TP1/SL比=1.333の系より）

## 交絡点検
- jpy_fx×rsiはN=31（小サンプル懸念あり）
- btcはrsi/bb共にN<25で除外
- oilはN<20で除外
- 全件がロング（Short=0）のため方向交絡なし

## 判定
- 事前宣言H1・H2いずれも未達
- 記事は「仮説失敗・探索的発見あり」で正直に公開
- 次回候補: signal=rsi_oversold_bounce × group=jpy_fx 正式検証（N=31 → 目標N≥60）
