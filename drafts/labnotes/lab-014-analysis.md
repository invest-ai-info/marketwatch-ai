# lab-014: bb_lower_touch × jpy_fx ロング 正式検証（#9 探索的記録の後継）
# 基準日: 2026-06-19 / signals-log 1065件（決済済 866件）

## スクリプト概要
- signals-log.jsonを読み込み、closed(outcome∈{tp1,tp2,sl,expired})を抽出
- group=jpy_fx (USDJPY=X / EURJPY=X / GBPJPY=X / AUDJPY=X)
- direction=long ('ロング'を含む)
- primary_signal == 'bb_lower_touch'
- 勝利 = outcome∈{tp1,tp2}、E(R): win=+1.33、loss=-1.0

## 生出力

### 全体統計
```
Total closed: 866

=== bb_lower_touch × jpy_fx ロング ===
N=45, wins=27, rate=60.0%, Wilson CI=[45.5%,73.0%]
E(R)=0.398, 95%CI=[0.061,0.735]
43%比較: CI下限45.5% ≥ 43% → 通過A

=== jpy_fx 全体ベースライン ===
N=174, wins=67, rate=38.5% CI=[31.6%,45.9%]

=== jpy_fx ロング 全体（比較群）===
N=127, wins=52, rate=40.9% CI=[32.8%,49.6%]

=== jpy_fx ロング 他シグナル（bb_lower_touch除く）===
N=82, wins=25, rate=30.5% CI=[21.6%,41.1%]
```

### TF別内訳
```
=== bb_lower_touch × jpy_fx ロング × 1h ===
N=30, wins=22, rate=73.3% CI=[55.6%,85.8%] E(R)=0.709 CI=[0.334,1.084]
  Trend(1h): 上昇12/18=66.7% / 下降3/5=60.0% / 中立・もみあい7/7=100.0%

=== bb_lower_touch × jpy_fx ロング × 4h ===
N=15, wins=5, rate=33.3% CI=[15.2%,58.3%] E(R)=-0.223 CI=[-0.799,0.352]
  Trend(4h): 上昇0/3=0.0% / 中立・もみあい5/12=41.7%
```

### Trend別（全tf）
```
--- Trend breakdown (higher_tf_trend) ---
  上昇: 12/21 = 57.1% CI=[36.5%,75.5%]
  下降: 3/5 = 60.0% CI=[23.1%,88.2%]
  中立・もみあい: 12/19 = 63.2% CI=[41.0%,80.9%]
```

### Ticker別
```
  USDJPY=X: 7/9 = 77.8% CI=[45.3%,93.7%]
  EURJPY=X: 7/12 = 58.3% CI=[32.0%,80.7%]
  GBPJPY=X: 8/13 = 61.5% CI=[35.5%,82.3%]
  AUDJPY=X: 5/11 = 45.5% CI=[21.3%,72.0%]
```

### 対照シグナル（同じ逆張り）
```
rsi_oversold_bounce × jpy_fx ロング: k=3, n=21, rate=14.3% CI=[5.0%,34.6%]
E(R)=-0.667
```

### jpy_fx ロング シグナル別完全テーブル
```
  bb_lower_touch: 27/45=60.0% CI=[45.5%,73.0%] E(R)=0.398
  macd_golden: 9/26=34.6% CI=[19.4%,53.8%] E(R)=-0.193
  rsi_oversold_bounce: 3/21=14.3% CI=[5.0%,34.6%] E(R)=-0.667
  high_break: 6/16=37.5% CI=[18.5%,61.4%] E(R)=-0.126
  bb_upper_break: 4/8=50.0% CI=[21.5%,78.5%] E(R)=0.165
  ma_golden: 2/6=33.3% CI=[9.7%,70.0%] E(R)=-0.223
  rsi_overbought: 1/5=20.0% CI=[3.6%,62.4%] E(R)=-0.534
```

## 交絡点検
1. **TF偏り**: 1h=30件(67%)、4h=15件(33%)。1h足の好成績がサンプルを引き上げている
2. **Trend非均等**: trend=上昇21/中立19/下降5（4h×下降が0件のため下降N=5は全て1h）
3. **Ticker偏り**: 4通貨ほぼ均等(9/12/13/11)。USDJPYが最高(77.8%)だがN=9で過信禁止
4. **N=45 < 宣言目標60**: 事前宣言「N≥60で確認」にまだ未達。CI下限はすでに43%超
5. **rsi vs bb の逆転**: 同じ「逆張り買い」でも bb=60% vs rsi=14% の大差。N(rsi)=21は小サンプル注意
6. **4h×上昇が0/3**: 4h足で上昇トレンド×bb_lower_long が0勝3敗（N=3・小サンプル）という逆説

## 前向きトラッカー
- tracker registerによる2026-06-19スイープ新候補: group=other_fx×dir=long / group=btc×reversalL / trend=中立×reversalL / group=btc×dir=long の4本
- 既存tracker: 指数×ロング(全足ライブ) 29/41=71% R+0.65 CI[+0.32,+0.98]（最も前向きに動いている）
- もみあい×ショート(#12 edge): 8/14=57% R+0.33（蓄積中）
