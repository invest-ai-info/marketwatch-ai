# AIシグナル研究日誌 #087 — 分析ノート

## 基準日
2026-09-02（JST）

## 仮説
**trend=上昇×reversalL（昇格済み）の前向き268件フォローアップ**
上昇トレンド中の逆張り買い（reversal_long=True）仮説は2026-06-22にトラッカー登録、
前向き検証を継続中。直近8月の成績がベースライン（42.9%）に収束しつつあるかを確認する。

## スクリプト

```python
import json, math, sys
from datetime import datetime, timezone
sys.path.insert(0, '.')
from signal_lab_verify import closed, win, get_trend, match, wilson

with open("signals-log.json") as f:
    logs = json.load(f)

all_closed = [d for d in logs if closed(d)]

# フィルター定義（signal_lab_verify.py の match 関数を使用）
filters = {
    "IS": {"trend": "上昇", "reversal_long": True, "fired_before": "2026-06-23"},
    "FWD": {"trend": "上昇", "reversal_long": True, "fired_from": "2026-06-23"},
    "ALL": {"trend": "上昇", "reversal_long": True},
    "FWD_RSI": {"trend": "上昇", "reversal_long": True, "signal": "rsi_oversold_bounce", "fired_from": "2026-06-23"},
    "FWD_BB":  {"trend": "上昇", "reversal_long": True, "signal": "bb_lower_touch",       "fired_from": "2026-06-23"},
    "FWD_JUL": {"trend": "上昇", "reversal_long": True, "fired_from": "2026-07-01", "fired_before": "2026-08-01"},
    "FWD_AUG": {"trend": "上昇", "reversal_long": True, "fired_from": "2026-08-01", "fired_before": "2026-09-01"},
}
```

## 生出力

```
全期間（IS+OOS）: k=180, n=371, 勝率=48.5%, CI=[43.5%,53.6%], E(R)=+0.198
IS期間（fired_before 2026-06-23）: k=56, n=103, 勝率=54.4%, CI=[44.8%,63.7%], E(R)=+0.403
FWD期間（fired_from 2026-06-23）: k=124, n=268, 勝率=46.3%, CI=[40.4%,52.2%], E(R)=+0.119
FWD RSI: k=40, n=62, 勝率=64.5%, CI=[52.1%,75.3%]
FWD BB:  k=84, n=206, 勝率=40.8%, CI=[34.3%,47.6%]

月別FWD:
  2026-06（発見月）: k=12, n=18, 勝率=66.7%, CI=[43.7%,83.7%]
  2026-07: k=61, n=128, 勝率=47.7%, CI=[39.2%,56.3%]
  2026-08: k=51, n=121, 勝率=42.1%, CI=[33.7%,51.1%]

全体ベースライン: k=1708, n=3985, 勝率=42.9%, CI=[41.3%,44.4%]

時間足別（全期間）:
  tf=1h: k=110, n=233, 勝率=47.2%
  tf=4h: k=51,  n=113, 勝率=45.1%
  tf=1d: k=19,  n=25,  勝率=76.0%, E(R)=+1.160 (N小)
```

## トラッカー更新ステータス
`python signal_lab_tracker.py update --date 2026-09-02` 実行済み
- trend=上昇×reversalL: ✅昇格 FWD 126/269（tracker.json 計算値）
- FDR通過新候補: 0本（sweep-2026-09-02.json に記録）

## 主要所見
1. 全期間CI下限43.5%>43%で昇格基準を維持（ただし境界域）
2. 月別OOS推移で明確な収束傾向：6月66.7% → 7月47.7% → 8月42.1%
3. 8月成績（42.1%）はベースライン（42.9%）にほぼ到達
4. RSI型がOOSで64.5%（N=62）と依然高い一方、BB型はOOS40.8%（N=206）で損益分岐割れ
5. BB型が全体の77%（206/268）を占めるため、全体が引き下げられている
6. 1d足では76.0%（N=25）と突出するが小サンプルのため参考値

## 交絡点検
- シグナル二極化（RSI vs BB）：最大の交絡要因。RSIが大幅に少ない（23%）ため、
  全体数値はBBに引っ張られる
- 指数FWD崩落（先行#062/#047で確認）：指数×BB が特に弱い可能性あり
- 9月データ：n=1と少なく今回の分析から除外
