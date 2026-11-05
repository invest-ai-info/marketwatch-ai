# lab-141 分析メモ（rl_tf_blocked・定点観測）
スクリプト全文＝lab-141-analysis.py／生出力＝lab-141-analysis-output.txt／記事生成＝lab-141-build.py・lab-141-body.py
- 区切り日＝仮説登録日(2026-09-26)の翌日 2026-09-27。FWD＝fired_from 2026-09-27、IS＝fired_before 2026-09-27。
- 壁＝sr_runway.blocked（直近20本の高値〔売りは安値〕が入値と利確1の間にある）。family=tf＝順張り。
- 結果（前向き）壁あり 54/125=43.2% [34.8,52.0]／壁なし 83/252=32.9% [27.4,39.0]。幅は一部重なる＝差が偶然でないとは言えない。
- 向きは見立て（gate＝壁ありは悪い）と逆。トラッカーは平均R -0.023・全体差+0.11・promote_strikes=0。
