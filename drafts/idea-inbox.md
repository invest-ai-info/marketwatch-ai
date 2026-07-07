# 💡 研究アイデア受信箱（idea-scout-weekly・毎週日曜）
routineが追記のみ・削除禁止。取り込みはローカルの進化ループ（hypothesis_queue.md）が行う

## 2026-07-07（JST）
### slug: jp-asset-growth
- 名前: 総資産成長アノマリー（日本株版）
- 主張: 前期比で総資産の増加率が低い銘柄（資産を増やさなかった企業）は、増加率が高い銘柄より翌年株価リターンが高い傾向がある【出典の主張・未検証】。ニッセイAMの日本株分析・吉野貴晶氏のマーケットクオンツ分析にて日本市場でも確認されたとされる逆張りファクター。計算式：（当期末総資産 − 前期末総資産）÷ 前期末総資産 で成長率を算出し、低い銘柄ほど有望とする。
- 出典: https://www.nam.co.jp/market/column/hosoku/2022/221111.html / https://media.monex.co.jp/articles/-/29126
- 検証案: jp-rankings.jsonで追跡可能な東証銘柄に財務データ（総資産）をjoinし、資産成長率の上位/下位三分位で翌年リターンを比較。NKD=F（指数先物）には不向き・個別株限定。
- タグ: ○

### slug: max-lottery-effect
- 名前: MAXアノマリー（月次最高日次リターンによる逆張り）
- 主張: 前月の日次リターンの最高値（MAX）が高い銘柄は翌月の期待リターンが有意に低くなる傾向がある【出典の主張・未検証】。Bali et al.（2011 JFE）が米国株で1%/月超のヘッジリターン差を記録。投資家の宝くじ選好（ロッタリー好み）が過大評価を生む行動ファイナンス的説明。日本株では単変量ソートでは不明確だが二変量ソート後に効果が現れるとの研究あり。
- 出典: https://pages.stern.nyu.edu/~rwhitela/papers/max%20jfe11.pdf / https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3595419
- 検証案: signals-log内の銘柄について前月MAXを日足OHLCVから計算し、高MAX（上位三分位）と低MAX（下位三分位）でシグナル的中率・リターンを比較。価格データのみで完結。
- タグ: ◎

### slug: jp-turn-of-month
- 名前: 月末・月初効果（日本株版）
- 主張: 月末4営業日〜月初3営業日の計7日間に株価が集中して上昇する傾向がある【出典の主張・未検証】。米国S&P500では1993〜2023バックテストでCAGR約2.87%・最大DD約11.97%の超過リターン（QuantifiedStrategies調べ）。日本（日経225）では2017〜2021を対象とした研究で効果が確認されなかったとの報告もあり証拠は混在。
- 出典: https://quantpedia.com/strategies/turn-of-the-month-in-equity-indexes / https://www.researchgate.net/publication/370416630_Investigating_the_Turn_of_the_Month_effect_Evidence_from_International_Financial_Markets
- 検証案: NKD=F（日経先物）日足データで月末4日〜月初3日の計7日 vs それ以外の日のリターン平均を比較。価格データのみ・曜日フィルタ不要でシンプルに機械化可能。
- タグ: ◎
