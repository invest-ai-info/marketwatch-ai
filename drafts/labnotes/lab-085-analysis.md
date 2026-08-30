# lab-085 分析メモ（2026-08-31）

## テーマ
rsi=os × 上昇トレンド × ロング 前向きN=21追跡——IS76.5%からFWD52.4%への軟化、1H足とシグナル別の構造差

## トラッカー登録日
2026-08-11（#068にて tracker [w] 新設）

## 検証スクリプト
signals-log.json から `outcome in (tp1,tp2,sl)` の closed 件のみ集計。
win = tp1 or tp2、E(R) = tp1→+2.0R/tp2→+3.0R/sl→-1.5R。
Wilson CI z=1.96、RCI = t-interval（SD/sqrt(N) × 1.96）。

## 生出力（Python反実仮想集計）

```
All closed: 3902

=== rsi=os × 上昇 × long ===
IS (before 2026-08-11): N=51, k=39, WR=76.5%, CI=[63.2%,86.0%], E(R)=1.176, RCI=[0.765,1.588]
FWD (from 2026-08-11): N=21, k=11, WR=52.4%, CI=[32.4%,71.7%], E(R)=0.333, RCI=[-0.433,1.099]
ALL (全期間): N=72, k=50, WR=69.4%, CI=[58.0%,78.9%], E(R)=0.931, RCI=[0.556,1.306]

=== rsi=os × 上昇 (all dir) ===
IS all: N=73, k=44, WR=60.3%, CI=[48.8%,70.7%], E(R)=0.610, RCI=[0.214,1.005]
FWD all: N=34, k=19, WR=55.9%, CI=[39.5%,71.1%], E(R)=0.456, RCI=[-0.137,1.049]
ALL all: N=107, k=63, WR=58.9%, CI=[49.4%,67.7%], E(R)=0.561, RCI=[0.233,0.889]

=== FWD TF breakdown (rsi=os × 上昇 × long) ===
FWD tf=1h: N=17, k=7, WR=41.2%, CI=[21.6%,64.0%], E(R)=-0.059, RCI=[-0.903,0.785]
FWD tf=4h: N=4, k=4, WR=100.0%, CI=[51.0%,100.0%], E(R)=2.000, RCI=[2.000,2.000]

=== IS Group breakdown ===
IS group=index: N=21, k=15, WR=71.4%, CI=[50.0%,86.2%], E(R)=1.000, RCI=[0.307,1.693]
IS group=jpy_fx: N=13, k=10, WR=76.9%, CI=[49.7%,91.8%], E(R)=1.192, RCI=[0.358,2.027]
IS group=other_fx: N=8, k=6, WR=75.0%, CI=[40.9%,92.9%], E(R)=1.125, RCI=[0.002,2.248]
IS group=metal: N=3, k=3, WR=100.0%, CI=[43.8%,100.0%], E(R)=2.000, RCI=[2.000,2.000]
IS group=oil: N=5, k=4, WR=80.0%, CI=[37.6%,96.4%], E(R)=1.300

=== FWD Group breakdown ===
FWD group=index: N=11, k=4, WR=36.4%, CI=[15.2%,64.6%], E(R)=-0.227, RCI=[-1.271,0.816]
FWD group=jpy_fx: N=4, k=2, WR=50.0%, CI=[15.0%,85.0%], E(R)=0.250
FWD group=other_fx: N=3, k=2, WR=66.7%, CI=[20.8%,93.9%], E(R)=0.833
FWD group=metal: N=1, k=1, WR=100.0% (N小・無視)
FWD group=btc: N=2, k=2, WR=100.0% (N小・無視)

=== Benchmarks ===
rsi=os×long×上昇 (=main target): N=72, k=50, WR=69.4%, CI=[58.0%,78.9%], E(R)=0.931
rsi=os×long×中立: N=140, k=64, WR=45.7%, CI=[37.7%,54.0%], E(R)=0.100
rsi=os×long×下降: N=115, k=54, WR=47.0%, CI=[38.1%,56.0%], E(R)=0.143

=== rsi=os × 上昇 × short ===
rsi=os × 上昇 × short ALL: N=35, k=13, WR=37.1%, CI=[23.2%,53.7%], E(R)=-0.200

=== IS Signal breakdown ===
IS signal=rsi_oversold_bounce: N=33, k=23, WR=69.7%, CI=[52.7%,82.6%], E(R)=0.939
IS signal=bb_lower_touch: N=18, k=16, WR=88.9%, CI=[67.2%,96.9%], E(R)=1.611

=== FWD Signal breakdown ===
FWD signal=rsi_oversold_bounce: N=14, k=6, WR=42.9%, CI=[21.4%,67.4%], E(R)=0.000
FWD signal=bb_lower_touch: N=5, k=3, WR=60.0%, CI=[23.1%,88.2%], E(R)=0.600
```

## 交絡点検
- FWD N=21は宣言昇格基準N=80には大幅未達。確定判断には至らない蓄積段階。
- FWD 4H N=4（100%）は小サンプルで信頼性低い。解釈注意。
- IS BBの88.9%（N=18）は小サンプル感あり。BB N=18→FWD N=5も非常に少ない。
- FWD全体RCI[-0.433,+1.099]はゼロを大きく跨ぐ＝確定打なし（継続観察）。
