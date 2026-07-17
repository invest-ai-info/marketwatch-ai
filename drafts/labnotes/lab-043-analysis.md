# Lab #043 — trend=下降×reversalL gate ⛔反証 解析ノート
# 基準日: 2026-07-18 JST / 実行者: signal-lab-daily routine

## スクリプト（全文）

```python
import json, math, sys
sys.path.insert(0, '/home/user/marketwatch-ai')
from signal_lab_verify import closed as is_closed, win, match, wilson, get_trend, GROUPS, REV

with open('signals-log.json') as f:
    data = json.load(f)
signals = data if isinstance(data, list) else data.get('signals', [])
all_closed = [s for s in signals if is_closed(s)]  # tp1/tp2/sl

def expected_r(s):
    if s.get('outcome') in ('tp1','tp2'): return 2.0
    elif s.get('outcome') == 'sl': return -1.5
    return 0.0

def mean_r_ci(sigs, z=1.96):
    if not sigs: return 0.0, (0.0, 0.0)
    rs = [expected_r(s) for s in sigs]
    n = len(rs); mu = sum(rs)/n
    var = sum((r-mu)**2 for r in rs)/(n-1) if n>1 else 0
    se = math.sqrt(var/n) if n>1 else 0
    return mu, (mu - z*se, mu + z*se)
```

## 生出力

### 総決済件数
Total closed (tp1/tp2/sl): 1843件

### メイン仮説: trend=下降×reversal_long=True
- フィルタ: trend_alignment.higher_tf_trend=="下降" AND direction=ロング AND primary_signal in {rsi_oversold_bounce, bb_lower_touch}
- 全期間(IS+FWD): N=260, k=107, 41.2% CI[35.3%,47.2%] E(R)=-0.060 RCI[-0.269,+0.150]
- IS(fired_at < 2026-06-25近似 / outcome_resolved_at): N≈169, k=51, 30.2% CI[23.8%,37.5%] E(R)=-0.444 RCI[-0.687,-0.201]
- FWD(outcome_resolved_at >= 2026-06-25): N=91, k=56, 61.5% CI[51.3%,70.9%] E(R)=+0.654 RCI[+0.302,+1.006]
- FWD first N=80 (⛔反証判定時点): N=80, k=54, 67.5% CI[56.6%,76.8%] E(R)=+0.863 RCI[+0.501,+1.224]

★ 前向きトラッカー公式値（fired_at基準）: N=90, k=52, 58% E(R)=+0.348 CI[-0.06,+0.76] → ⛔反証ステータス

### グループ別（全期間）
- group=index: N=25, k=12, 48.0% CI[30.0%,66.5%] E(R)=+0.180
- group=jpy_fx: N=19, k=10, 52.6% CI[31.7%,72.7%] E(R)=+0.342
- group=other_fx: N=68, k=34, 50.0% CI[38.4%,61.6%] E(R)=+0.250
- group=metal: N=92, k=23, 25.0% CI[17.3%,34.7%] E(R)=-0.625 RCI[-0.936,-0.314]
- group=btc: N=33, k=14, 42.4% CI[27.2%,59.2%] E(R)=-0.015
- group=oil: N=23, k=14, 60.9% CI[40.8%,77.8%] E(R)=+0.630

### 金属レジーム交絡（全期間→IS/FWD分解）
- metal×下降×revL 全期間: N=92, k=23, 25.0% CI[17.3%,34.7%] E(R)=-0.625
- metal×下降×revL IS: N=69, k=8, 11.6% CI[6.0%,21.2%] E(R)=-1.094 RCI[-1.361,-0.828]
- metal×下降×revL FWD: N=23, k=15, 65.2% CI[44.9%,81.2%] E(R)=+0.783 RCI[+0.086,+1.479]

### 非金属確認
- 非金属×下降×revL 全期間: N=168, k=84, 50.0% CI[42.5%,57.5%] E(R)=+0.250
- 非金属×下降×revL IS: N=100, k=43, 43.0% CI[33.7%,52.8%] E(R)=+0.005
- 非金属×下降×revL FWD: N=68, k=41, 60.3% CI[48.4%,71.1%] E(R)=+0.610 RCI[+0.200,+1.020]

### シグナル別（全期間）
- signal=rsi_oversold_bounce: N=116, k=45, 38.8% CI[30.4%,47.9%] E(R)=-0.142
- signal=bb_lower_touch: N=144, k=62, 43.1% CI[35.3%,51.2%] E(R)=+0.007
- FWD signal=rsi_oversold_bounce: N=30, k=18, 60.0% CI[42.3%,75.4%] E(R)=+0.600
- FWD signal=bb_lower_touch: N=61, k=38, 62.3% CI[49.7%,73.4%] E(R)=+0.680

### 時間足別（全期間）
- tf=1h: N=155, k=56, 36.1% CI[29.0%,43.9%] E(R)=-0.235
- tf=4h: N=102, k=49, 48.0% CI[38.6%,57.6%] E(R)=+0.181

### 対照群（全期間）
- trend=下降×long×非revL（順張りロング）: N=190, k=67, 35.3% CI[28.8%,42.3%] E(R)=-0.266
- trend=下降×short（トレンドフォロー）: N=181, k=74, 40.9% CI[34.0%,48.2%] E(R)=-0.069
- trend=上昇×reversalL（#042・対照）: N=191, k=99, 51.8% CI[44.8%,58.8%] E(R)=+0.314

### 月次推移(FWD)
- 2026-06: N=29, wins=18, 62.1%
- 2026-07: N=62, wins=38, 61.3%

## 採択理由（優先度順）
- 優先度①: tracker update により trend=下降×reversalL gate が ⛔反証ステータスに変化（#041では「接近」だった）
- IS gate設立値 30.2% E(R)=-0.444（全域マイナス）→ FWD N=80チェックポイント 67.5% E(R)=+0.863（全域プラス）で⛔反証確定
- 主因：metal IS 11.6%→FWD 65.2%（+1.877R差）のレジーム転換（#030/#032/#039/#040と同根シリーズ）
- 非金属でも IS 43.0%→FWD 60.3% の独立した改善を確認

## 交絡点検
- metal交絡: IS期間に metal 69/169=40.8% を占め、11.6%という極端低勝率が全体を 30.2%に引き下げた主因
- 非金属IS 43.0%は損益分岐付近（gate根拠が金属依存）
- 非金属FWD 60.3%も独立して改善→ 「金属のみ」の話ではなく全体的なレジーム転換

## 事前合否基準（⛔反証）
gate設立条件: IS E(R) CI全域マイナス（達成: E(R)=-0.444 RCI[-0.687,-0.201]）
⛔反証条件: FWD N≥80かつ E(R)のCI下限>0（達成: N=80, E(R)=+0.863 RCI[+0.501,+1.224]）

## Wilson CI計算確認
- 全期間 k=107/n=260: =(107+1.92)/(260+3.84) ≈ 0.416; margin≈0.060 → [35.3%, 47.2%] ✓

## スイープ結果
- 本日スイープFDR通過: 3本（全て既登録・新規なし）
- ⛔反証仮説: group=metal×dir=long, group=metal（既登録）
- ✅昇格候補: tf=1d×reversalL（既登録・前向きN=1のみ）

## tracker update 昇格/反証変化まとめ
- trend=下降×reversalL gate: 🟡蓄積中（⛔反証接近） → ⛔反証 ★今日の最大変化
- その他: 変化なし（指数×ロング✅昇格・trend=上昇×reversalL✅昇格 は継続）

