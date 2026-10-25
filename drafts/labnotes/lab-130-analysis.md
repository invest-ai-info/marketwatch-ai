# lab-130 分析メモ — rsi_oversold_edge 定点観測（前向き430回）

日付: 2026-10-26 (JST) / 仮説ID: rsi_oversold_edge（edge）/ 登録 2026-06-16 / 前向き 2026-06-17〜
- 題材の理由: 昇格/反証の変化なし・スイープFDR通過0本・読者質問なし・出口の回は日曜のみ(今日は月曜) → ②前向きで動いた仮説（N=401で1回目合格→426へ。平均Rの下限が+0.001→-0.014へ）
- トラッカー: 426回 平均R +0.139 [-0.014,+0.292]、promote_strikes=1、last_eval_n=401、次の判定は480回（min_n=80）
- 記事側の数字は signals-log から signal=rsi_oversold_bounce で数え直し（claims.json）。トラッカー(登録日当日から・18銘柄固定)と記事(翌日から・全銘柄)で数件ずれる
- スクリプト全文: lab-130-analysis.py／生出力: lab-130-analysis-output.txt
