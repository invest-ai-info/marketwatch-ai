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

## 2026-07-12（JST）
### slug: accruals-anomaly
- 名前: 発生主義会計アノマリー（低アクルーアル効果）
- 主張: 純利益から営業キャッシュフローを差し引いた会計発生額（アクルーアル）が小さい銘柄は、大きい銘柄より翌年の株価リターンが高い傾向がある【出典の主張・未検証】。Sloan（1996, AR誌）が米国株で年間10%超のヘッジリターンを報告。国際的な実証研究でも多くの先進国市場で確認されており（Haugen & Baker 2010等）、日本株での再現性も示唆されている。
- 出典: https://quantpedia.com/strategies/accrual-anomaly / https://www.researchgate.net/publication/228177244_The_Accrual_Anomaly_International_Evidence
- 検証案: 東証銘柄の四半期財務データ（純利益・営業CF）でアクルーアル比率を計算し、低アクルーアル上位三分位 vs 高アクルーアル下位三分位の翌期リターンをシグナルログ内銘柄で比較。財務データjoin必要。
- タグ: ○

### slug: gross-profitability-novy-marx
- 名前: 粗利益率プレミアム（ノビー=マルクス）
- 主張: 総資産に対する粗利益（売上高−売上原価）の比率が高い企業は、低い企業より将来の株価リターンが高くなる傾向がある【出典の主張・未検証】。Novy-Marx（JFE 2013）が米国株で価値ファクターと同等の予測力を持つと報告。2025年の回顧論文（SSRN 5190788）でも収益性効果の持続を確認。バリュー投資と直交するため組み合わせ効果も大きいとされる。
- 出典: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5190788 / https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1598056
- 検証案: 東証銘柄に粗利益/総資産比率を財務データからjoinし、上位三分位vs下位三分位の1年リターン差を検証。buffett-quality（複合スクリーン）とは独立した単一指標の効果を確認する。
- タグ: ○

### slug: short-term-reversal-1w
- 名前: 短期リターン反転（週次ルーザー買い）
- 主張: 直近1週間のリターンが最も低かった銘柄群は、翌週のリターンが市場平均を上回る傾向がある【出典の主張・未検証】。Jegadeesh（1990）が米国で月次ベースで97bp/月のヘッジリターンを報告。近年は効果が弱まっているとの研究（Blitz et al. SSRN 4575689）もあるが、残差リバーサル（業種・ファクターリターンを除いた後の逆張り）に改良すると効果が復活するとされる。
- 出典: https://quantpedia.com/strategies/short-term-reversal-in-stocks / https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4575689
- 検証案: signals-log内銘柄の週次OHLCVデータで「前週リターン下位三分位」を買い候補とし、翌週の勝率・期待値を算出。純粋な価格データのみで完結。bnf-ma-deviation（25日MA逆張り）との相関も確認する。
- タグ: ◎

## 2026-07-19（JST）
### slug: pre-holiday-jp
- 名前: 日本株・祝日前プレミアム
- 主張: 市場休場日（祝日）の前日に株式リターンが統計的に有意に高くなる傾向がある【出典の主張・未検証】。Lakonishok & Smidt（1988）・Kim & Park（1994）が米国で確認。2024年の国際研究（Review of Financial Economics 2026）では1990〜2024年のアジア市場で祝日前リターンが通常日の約7倍に達すると報告。日本株個別研究は限定的だが、TSEはGWや祝日など休場頻度が高くアジア市場として同様の効果が期待される。
- 出典: https://quantpedia.com/strategies/pre-holiday-effect / https://onlinelibrary.wiley.com/doi/full/10.1002/rfe.70018
- 検証案: economic-events.jsonの「市場休場」エントリを活用してTSE休場日の前日を特定し、NKD=F日足で「祝日前日」vs「その他営業日」のリターン平均・中央値・勝率を比較。価格データのみで完結。
- タグ: ◎

### slug: japan-buyback-post
- 名前: 日本株・自社株買い公表後短期超過リターン
- 主張: 自社株買い公表の翌日、株価はTOPIXを平均約2%アウトパフォームする傾向がある【出典の主張・未検証】。NLI Research Instituteの分析による。2025年に日本市場での自社株買いアノマリーを検証した初の事前登録型学術論文が公刊され、米国で確認されているコストリー・アービトラージ仮説の成立可否を日本で検証（ScienceDirect 2025）。日本の自社株買い2025年度は22.32兆円・5年連続最高水準で制度的背景（東証の資本効率要請）も追い風。
- 出典: https://www.sciencedirect.com/article/pii/S0927538X25000034 / https://corporate.quick.co.jp/en/japanmarketsview/equity/significant-effects-of-share-buyback-japan-posts-6178-share-buyback-accounts-for-15-of-trading-volume/
- 検証案: TDnet等の自社株買い公表日データをjoinし、公表翌日〜5営業日間の超過リターンを計算。jp-rankings.jsonの銘柄と紐づけ可能かを先に調査。公表日データ調達が検証の前提条件。
- タグ: △

### slug: earnings-announcement-premium
- 名前: 決算公表プレミアム（プリアナウンスメント・ドリフト）
- 主張: 決算発表日の前の約10営業日間、株価が市場平均を上回って上昇する傾向がある（PEADとは独立した現象）【出典の主張・未検証】。Frazzini & Lamont（2007）やBarber et al.により、EAPの71%が発表前に実現すると報告。高不確実性銘柄では公表前10日間の平均異常リターンが1.52%との推計あり。情報リーケージまたは投資家の事前ポジショニングによる説明が有力。pead（事後ドリフト=watchリスト）とは発生タイミングが異なる別現象。
- 出典: https://quantpedia.com/strategies/earnings-announcement-premium / https://quantpedia.com/pre-announcement-returns/
- 検証案: 決算発表スケジュール（東証開示calendar等）をjoinし、対象銘柄の-10日〜-1日の累積リターンを計算。NKD=F指数版では四半期決算集中月（1/4/7/10月）の特定期間効果として粗く検証可能。データ調達・精度の限界に注意。
- タグ: △
