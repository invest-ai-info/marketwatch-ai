# 研究日誌 #108 — 解析メモ

## 基準日
2026-09-24 JST

## 今日のイベント
`signal_lab_tracker.py update --date 2026-09-24` の実行で、
`trend=上昇×reversalL`（上昇トレンドでの逆張り買い）が「降格」（demote）に変化。
- 降格条件: 平均Rの95%CI下限（rci_lo）が0を下回る状態が2回連続
- rci_lo の推移: 2026-09-08 = -0.033 → 2026-09-22 = -0.043 → 2026-09-24 = -0.050
- 前向きN=323（tracker更新時点）、k=152、平均R=+0.098

## 仮説
「相場が上がっている流れ（上昇トレンド）のときに、
  RSI売られすぎ反発（rsi_oversold_bounce）か
  BB下限タッチ（bb_lower_touch）のシグナルが出たところで買う（逆張り買い）と勝ちやすい？」

- フィルタ: trend="上昇" AND reversal_long=True
- 登録日: 2026-06-22（IS/FWD境界）
- IS（検証に使った期間: 2026-06-22より前）: k=54, n=101
- FWD（その後の期間: 2026-06-22以降）: k=152, n=326（今日時点）

## 検証スクリプト（Python）

```python
import json, math
from signal_lab_verify import closed, win, match

with open("signals-log.json") as f:
    data = json.load(f)
signals = data if isinstance(data, list) else data.get("signals", [])

# Wilson CI
def wilson_ci(k, n, z=1.96):
    if n == 0: return (0, 0, 0)
    p = k/n
    denom = 1 + z**2/n
    center = (p + z**2/(2*n)) / denom
    half = z * math.sqrt(p*(1-p)/n + z**2/(4*n**2)) / denom
    return (round(p*100,1), round(max(0,(center-half)*100),1), round(min(100,(center+half)*100),1))

# IS
is_sigs = [d for d in signals if closed(d) and match(d, {"reversal_long": True, "trend": "上昇", "fired_before": "2026-06-22"})]
is_k = sum(1 for s in is_sigs if win(s))
is_n = len(is_sigs)
print(f"IS: {is_k}/{is_n} = {wilson_ci(is_k,is_n)}")

# FWD
fwd_sigs = [d for d in signals if closed(d) and match(d, {"reversal_long": True, "trend": "上昇", "fired_from": "2026-06-22"})]
fwd_k = sum(1 for s in fwd_sigs if win(s))
fwd_n = len(fwd_sigs)
print(f"FWD: {fwd_k}/{fwd_n} = {wilson_ci(fwd_k,fwd_n)}")

# BB lower touch FWD
bb_sigs = [d for d in signals if closed(d) and match(d, {"signal": "bb_lower_touch", "trend": "上昇", "fired_from": "2026-06-22"})]
bb_k = sum(1 for s in bb_sigs if win(s))
print(f"BB FWD: {bb_k}/{len(bb_sigs)} = {wilson_ci(bb_k,len(bb_sigs))}")

# RSI oversold FWD
rsi_sigs = [d for d in signals if closed(d) and match(d, {"signal": "rsi_oversold_bounce", "trend": "上昇", "fired_from": "2026-06-22"})]
rsi_k = sum(1 for s in rsi_sigs if win(s))
print(f"RSI FWD: {rsi_k}/{len(rsi_sigs)} = {wilson_ci(rsi_k,len(rsi_sigs))}")

# Stock index FWD
idx_sigs = [d for d in signals if closed(d) and match(d, {"group": "index", "reversal_long": True, "trend": "上昇", "fired_from": "2026-06-22"})]
idx_k = sum(1 for s in idx_sigs if win(s))
print(f"Index FWD: {idx_k}/{len(idx_sigs)} = {wilson_ci(idx_k,len(idx_sigs))}")
```

## 生出力

```
IS: 54/101 = (53.5, 43.8, 62.9)
FWD: 152/326 = (46.6, 41.3, 52.0)
BB FWD: 104/248 = (41.9, 36.0, 48.2)
RSI FWD: 48/79 = (60.8, 49.7, 70.8)
Index FWD: 31/82 = (37.8, 28.1, 48.6)
```

## IS avgR（計算）
- alltime（tracker JSON）: n=424, avgR=0.134 → sum = 424 × 0.134 = 56.816
- FWD（tracker JSON）: n=323, avgR=0.098 → sum = 323 × 0.098 = 31.654
- IS推定: (56.816 - 31.654) / 101 ≈ +0.249

## FWD avgR（tracker JSON直接値）
- k=152, n=323（tracker更新時点）, avgR=+0.098
- R-CI: [-0.050, +0.246]（0をまたぐ = 偶然との区別ができない）

## 今日の新シグナル（tracker更新後に追加）
- 2026-09-23: ES=F (sl), AUDUSD=X (sl)
- 2026-09-24: ES=F (sl)
→ k変わらず152、nが323→326に増加

## 降格判定
- rci_loが0を下回る状態が2回連続（2026-09-22: -0.043, 2026-09-24: -0.050）
- 降格 = 「昇格できなかった」ではなく「昇格基準に届かないまま追跡終了」に近い状態
  （この仮説は一度も昇格していない = promote_min_n=80 到達後もrci_loが負のまま継続）

## ウィルソン信頼区間（偶然のぶれを考えた勝率の幅）

| 期間  | 勝ち/回数 | 勝率 | 偶然のぶれの幅 |
|---|---|---|---|
| IS（検証期間） | 54/101 | 53.5% | 43.8%〜62.9% |
| FWD（その後）全体 | 152/326 | 46.6% | 41.3%〜52.0% |
| FWD - BB下限タッチ | 104/248 | 41.9% | 36.0%〜48.2% |
| FWD - RSI売られすぎ反発 | 48/79 | 60.8% | 49.7%〜70.8% |
| FWD - 株価指数のみ | 31/82 | 37.8% | 28.1%〜48.6% |

## 交絡チェック
- ISとFWDで市場環境が異なる可能性はある（2026年前半 vs 後半）
- シグナル種別（BB vs RSI）の構成比変化は調査していないが、FWD内でBBが248件・RSIが79件と
  BBが多数を占め、BB単体が41.9%（損益分岐43%以下）であることが全体を引き下げている

## 結論
「上昇トレンドでの逆張り買い」という仮説は：
- IS期間: 53.5%（見た目は良い）
- FWD期間: 46.6%（落ちた、R-CIが0をまたぐ）
→ 「証明できなかった」として降格。
ただし内訳では、RSI売られすぎ反発単体は60.8%（FWD）と依然として有望。
「BB下限タッチ」が損益分岐以下（41.9%）で全体を引き下げているのが主因。

## sweep出力
- FDR通過: 0本（新候補なし）
