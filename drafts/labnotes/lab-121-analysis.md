# 研究日誌 #121 分析メモ（2026-10-09）

## 基準日・本日の概要
- JST基準日: 2026-10-09（金曜）
- 題材: 前向きトラッカー大規模刈り込み — 12本同時引退の記録
- 採択理由: トラッカー優先度② (前向きで大きく動いた)

## 今日のトラッカー変化
python signal_lab_tracker.py update --date 2026-10-09 実行結果：

### 引退（⏹見込みなし）12本：
| ID | 理由 |
|---|---|
| auto_group-all (group=all) | 効きが小さすぎる（FWD N=3975 R+0.016 CI[-0.03,+0.07]） |
| auto_blocked-False (blocked=False) | 効きが小さすぎる（FWD N=3177 R+0.016 CI[-0.04,+0.07]） |
| auto_blocked-False_direction-long (blocked=False×long) | 効きが小さすぎる（FWD N=2513 R+0.022 CI[-0.05,+0.10]） |
| auto_direction-long_tf-4h (tf=4h×long) | 効きが小さすぎる（FWD N=1150 R+0.014 CI[-0.09,+0.11]） |
| auto_tier-neutral (tier=neutral) | 効きが小さすぎる（FWD N=1044 R+0.028 CI[-0.05,+0.10]） |
| auto_group-index (group=index) | 効きが小さすぎる（FWD N=1044 R+0.001 CI[-0.09,+0.09]） |
| auto_group-metal (group=metal) | 効きが小さすぎる（FWD N=493 R+0.051 CI[-0.09,+0.19]） |
| auto_注目度ゼロ (news=0) | 効きが小さすぎる（FWD N=579 R-0.057 CI[-0.18,+0.07]） |
| auto_trend-neutral-reversal (trend=中立×reversal) | 効きが小さすぎる（FWD N=382 R+0.063 CI[-0.07,+0.19]） |
| auto_trend-down-short (trend=下降×short) | 効きが小さすぎる（FWD N=316 R+0.085 CI[-0.07,+0.25]） |
| 指数×逆張り買い(日足) | 時間がかかりすぎる（N=6 で2年超える） |
| コンボ ダブルボトム×高値ブレイク | 時間がかかりすぎる（N=1） |

### 昇格・反証: なし（本日）
### FDRスイープ候補: 0本

## 検証数値（signals-log.json から直接集計）

### A. 全シグナルベースライン（FWD: 2026-06-26以降）
- filter: {"group": "all"}
- hypothesis_id: auto_group-all (registered_at: 2026-06-25)
- N=3984（sl+tp1+tp2）, k=1723, wr=43.2%
- Wilson95CI=[41.7%,44.8%]
- avgR=+0.009, R-CI=[-0.03,+0.05]

### B. 4時間足の買い（FWD: 2026-06-21以降）
- filter: {"tf": "4h", "direction": "long"}
- hypothesis_id: auto_direction-long_tf-4h (registered_at: 2026-06-20)
- N=1143, k=497, wr=43.5%
- Wilson95CI=[40.6%,46.4%]
- avgR=+0.015, R-CI=[-0.05,+0.08]

### C. RSI売られすぎ逆張り買い（FWD: 2026-06-17以降）
- filter: {"signal": "rsi_oversold_bounce"}
- hypothesis_id: rsi_oversold_edge (registered_at: 2026-06-16)
- N=412, k=203, wr=49.3%
- Wilson95CI=[44.5%,54.1%]
- avgR=+0.150, R-CI=[+0.04,+0.26]

## 引退の判定基準（トラッカーのルール）
- N≥100（件数が十分）
- かつ R（期待値）の良い方の端（CI上限）が +0.10R 未満
→ エッジがないと確認できる規模まで積み上がった

## 生成ファイル
- drafts/labnotes/lab-121-analysis.md（本ファイル）
- drafts/labnotes/lab-121-claims.json
- drafts/labnotes/sweep-2026-10-09.json（スイープ: FDR通過0本）
- drafts/draft-signal-lab-121.html
