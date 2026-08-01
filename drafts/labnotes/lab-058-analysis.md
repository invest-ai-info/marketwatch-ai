# lab-058-analysis: 金属ロングgate N=156 フォローアップ
# 基準日: 2026-08-02

## 仮説
group=metal×dir=long gate（#039で確認・登録日2026-06-17）の前向きフォローアップ。
- H1: FWD後半(gate確認後 N=70)はFWD前半(N=86)よりE(R)が改善しているか？
- H2: FWD全体(N=156)でゲート条件（クラスター補正CI上限<0）は維持されているか？

## 集計スクリプト

```python
import json, math

with open("signals-log.json") as f:
    data = json.load(f)

METAL_TICKERS = {"GC=F", "SI=F"}
# ... 省略（group/dir/win/r_mult 定義）

closed = [s for s in data if s.get("outcome") in ["tp1","sl","expired"]]
# 2516件

# 全期間 metal×long:  72/242=29.8%
# IS (<2026-06-17):   14/86=16.3%
# FWD (>=2026-06-17): 58/156=37.2%
# FWD early (N=86):   24/86=27.9%
# FWD late (N=70):    34/70=48.6%
```

## 生出力

=== group=metal×dir=long ===
  全期間: k=72, n=242, 29.8% CI[24.3%,35.8%] E(R)=-0.302 RCI[-0.436,-0.167]
  IS (<2026-06-17): k=14, n=86, 16.3% CI[10.0%,25.5%] E(R)=-0.620 RCI[-0.802,-0.438]
  FWD (>=2026-06-17, N=156): k=58, n=156, 37.2% CI[30.0%,45.0%] E(R)=-0.126 RCI[-0.303,0.050]
  FWD_early (N=86 gate確認時): k=24, n=86, 27.9% CI[19.5%,38.2%] E(R)=-0.337 RCI[-0.558,-0.117]
  FWD_late (N=70 後半): k=34, n=70, 48.6% CI[37.2%,60.0%] E(R)=+0.133 RCI[-0.140,0.406]

=== 銘柄別 (FWD) ===
  GC=F FWD: 31/78=39.7% CI[29.6%,50.8%] E(R)=-0.060 RCI[-0.312,0.192]
  SI=F FWD: 27/78=34.6% CI[25.0%,45.7%] E(R)=-0.192 RCI[-0.439,0.054]

=== シグナル別 (FWD・N>=5) ===
  bb_lower_touch FWD: 19/48=39.6% CI[27.0%,53.7%] E(R)=-0.077 RCI[-0.399,0.246]
  rsi_oversold_bounce FWD: 15/30=50.0% CI[33.2%,66.8%] E(R)=+0.200 RCI[-0.211,0.610]
  macd_golden FWD: 8/28=28.6% CI[15.3%,47.1%] E(R)=-0.333 RCI[-0.724,0.057]
  ma_golden FWD: 1/9=11.1% CI[2.0%,43.5%] E(R)=-0.741 RCI[-1.220,-0.262]
  high_break FWD: 1/8=12.5% CI[2.2%,47.1%] E(R)=-0.708 RCI[-1.243,-0.174]
  support_bounce FWD: 7/11=63.6% CI[35.4%,84.8%] E(R)=+0.485 RCI[-0.179,1.148]

=== TF別 (FWD) ===
  1h FWD: 26/80=32.5% CI[23.2%,43.4%] E(R)=-0.242 RCI[-0.481,-0.002]
  4h FWD: 30/65=46.2% CI[34.6%,58.1%] E(R)=+0.077 RCI[-0.206,0.360]
  1d FWD: 2/11=18.2% CI[5.1%,47.7%] E(R)=-0.485 RCI[-1.018,0.049]

=== 対照: metal×short (FWD) ===
  FWD: 27/60=45.0% CI[33.1%,57.5%] E(R)=+0.050 RCI[-0.244,0.344]

=== 月別推移 (FWD) ===
  2026-06: 17/51=33.3% E(R)=-0.203
  2026-07: 41/105=39.0% E(R)=-0.089

=== クラスター補正CI (トラッカー出力) ===
  group=metal×dir=long gate: 58/155 勝率37% 平均R=-0.13 CI[-0.42~+0.17] ✅昇格

=== 全期間 claims 用 ===
  metal×long 全期間: k=72, n=242
  metal×long×bb_lower_touch: k=25, n=75
  metal×long×rsi_oversold_bounce: k=19, n=61
  metal×long×macd_golden: k=10, n=43
  metal×long×high_break: k=1, n=14
  metal×long×ma_golden: k=2, n=10
  GC=F×long: k=41, n=132
  SI=F×long: k=31, n=110
  tf=1h×metal×long: k=31, n=126
  tf=4h×metal×long: k=37, n=101
  metal×short 全期間: k=44, n=93

## 判定
- H1: FWD前半E(R)=-0.337 → FWD後半E(R)=+0.133（+0.470R改善）✅通過
- H2: クラスター補正CI上限=+0.17>0 → ゲート条件崩壊 ✅通過
- 次チェックポイント: N=160（降格1回目の判定タイミング）
- 通過分類: 🟡 通過A（ゲート条件崩壊確認・降格1回目接近）
