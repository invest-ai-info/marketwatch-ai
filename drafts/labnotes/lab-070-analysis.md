# lab-070 分析ノート
## 仮説
上昇トレンド×逆張り買い（reversal_long=True）は前向きN=187で昇格維持しているか。
さらに、ISとFWDでRSI売られすぎ（rsi_oversold_bounce）とBB下限タッチ（bb_lower_touch）の二極化が深化しているか。

## 登録日
tracker registered_at: 2026-06-22（trend=上昇×reversalL）

## Python反実仮想集計スクリプト

```python
# signals-log.json から trend=上昇×reversalL を集計
# IS/FWD境界 = 2026-06-22 (tracker登録日)

GROUPS = {
    "metal":    {"GC=F","SI=F"},
    "index":    {"NKD=F","ES=F","NQ=F","YM=F","^FTSE"},
    "jpy_fx":   {"USDJPY=X","EURJPY=X","GBPJPY=X","AUDJPY=X"},
    "other_fx": {"EURUSD=X","GBPUSD=X","AUDUSD=X","EURAUD=X","GBPAUD=X"},
    "btc":      {"BTC-USD"},
    "oil":      {"CL=F"},
}
REV = {"rsi_oversold_bounce","bb_lower_touch"}
closed = outcome in (tp1,tp2,sl), win = outcome in (tp1,tp2)
trend = trend_alignment.higher_tf_trend
reversal_long = direction=ロング and primary_signal in REV
```

## 生出力

### 全期間 trend=上昇×reversalL
Total closed signals: 3035
全期間: k=149 n=288 51.7% CI[46.0%,57.4%]
IS (before 2026-06-22): k=54 n=101 53.5% CI[43.8%,62.9%]
FWD (from 2026-06-22): k=95 n=187 50.8% CI[43.7%,57.9%]

### IS signal breakdown
  rsi_oversold_bounce: k=13 n=25 52.0% CI[33.5,70.0]
  bb_lower_touch: k=41 n=76 53.9% CI[42.8,64.7]

### FWD signal breakdown
  rsi_oversold_bounce: k=29 n=39 74.4% CI[58.9,85.4]
  bb_lower_touch: k=66 n=148 44.6% CI[36.8,52.6]

### 全期間 signal breakdown
  rsi_oversold_bounce: k=42 n=64 65.6% CI[53.4,76.1]
  bb_lower_touch: k=107 n=224 47.8% CI[41.3,54.3]

### FWD group breakdown
  index: k=19 n=47 40.4% CI[27.6,54.7]
  jpy_fx: k=31 n=56 55.4% CI[42.4,67.6]
  other_fx: k=28 n=50 56.0% CI[42.3,68.8]
  metal: k=5 n=11 45.5% CI[21.3,72.0]
  btc: k=6 n=12 50.0% CI[25.4,74.6]
  oil: k=6 n=10 60.0% CI[31.3,83.2]

### IS group breakdown
  index: k=35 n=51 68.6% CI[55.0,79.7]
  jpy_fx: k=15 n=26 57.7% CI[38.9,74.5]
  other_fx: k=1 n=16 6.2% CI[1.1,28.3]
  metal: k=2 n=4 50.0%
  btc: k=0 n=2 0.0%
  oil: k=1 n=2 50.0%

### FWD時系列 3分割
  分割点: 2026-07-14 / 2026-07-28
  FWD前半 (N=61): k=35 57.4%
  FWD中半 (N=61): k=25 41.0%
  FWD後半 (N=63): k=33 52.4%

### FWD E(R) 推定（tp1=+1.33R, sl=-1.0Rで推定）
FWD E(R) approx: +0.184 CI[+0.016,+0.351]
FWD RSI E(R): +0.733 CI[+0.409,+1.056]

### トラッカー出力（cluster補正）
trend=上昇×reversalL: FWD 95/186 51% E(R)=+0.19 CI[+0.05~+0.33] ✅昇格

### 比較: reversalL × 他トレンド
  trend=下降: k=147 n=330 44.5% CI[39.3,49.9]
  trend=中立・もみあい: k=141 n=330 42.7% CI[37.5,48.1]

## 事前宣言（事後では変更しない）
H1: FWD期間 trend=上昇×reversalL の E(R) CI下限 > 0 → ✅達成（tracker CI[+0.05,+0.33]）
H2: FWD RSI (rsi_oversold_bounce) > FWD BB (bb_lower_touch) → ✅達成（74.4% vs 44.6%, 30pp差）

## 交絡点検
- 上昇×逆張りLの構成: BB 148件(79%) vs RSI 39件(21%)。BBが多数派なので全体平均はBBに引きずられやすい
- IS指数68.6%→FWD40.4%の崩落は指数×ロング降格（#048）と整合
- IS other_fx 6.2%→FWD56.0%の急上昇はレジーム転換（#030/#032と同根の金属レジーム転換に伴う全資産改善）
- FWD中半41.0%の一時落ち込みは市場のvolatility期（2026-07-14〜28）と推測されるが後半52.4%に回復
- RSIの優位はFWD期に初めて顕在化（IS期はBBと同等）→「上昇トレンドの押し目」としてRSI売られすぎが特に有効

## sweep-2026-08-15.json との整合
FDR通過: trend=上昇×reversalL (全期間k=149/n=288=51.7%, R=+0.207, q=0.0905)
→ 全期間ベースでもFDR通過しており、IS/FWD分解と整合
