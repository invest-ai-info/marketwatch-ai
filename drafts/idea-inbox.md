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

## 2026-07-26（JST）
### slug: jp-dow-effect
- 名前: 日本株曜日別リターン効果（火曜プレミアム・月曜ディスカウント）
- 主張: 日本株では曜日によるリターン偏りが存在し、火曜日がプラス（オーバーナイト含む）、月曜日がマイナスになる傾向がある【出典の主張・未検証】。Jaffe & Westerfield (1985, JFQA) が学術確認。Kato et al. (2009) によれば1984年以降は火曜正効果が顕著で先物限月前月に集中。個人バックテスト (2024) では火曜オーバーナイト保有が全規模で最強・月曜デイトレードが全規模でマイナスとの結果。2019年学術研究では「UP市場でのみ有意」という条件も示唆。larry-williams テスト (tested) は曜日を含む複合システムだが、本仮説は純粋な日本市場の曜日効果を単変量で検証する別角度。
- 出典: https://pubsonline.informs.org/doi/10.1287/mnsc.36.9.1031 / https://ideas.repec.org/a/kap/apfinm/v26y2019i2d10.1007_s10690-018-9263-4.html
- 検証案: NKD=F日足で「火曜始値→水曜始値」オーバーナイトリターン vs「月曜始値→終値」デイリターンを全期間・MA(200)上昇相場限定それぞれで勝率・期待値算出。価格データのみで完結。
- タグ: ◎

### slug: jp-high-dividend-yield
- 名前: 日本株高配当利回りファクター単独効果
- 主張: 高配当利回り銘柄（MSCI Japan平均の130%超）で構成したポートフォリオは市場全体をアウトパフォームする傾向がある【出典の主張・未検証】。MSCI Japan High Dividend Yield Indexは2024年+26.28%・2025年+23.46%（MSCI Japan全体2024年+21.15%に対し超過リターン約+5pp）。TSEプライム配当利回りが2025年5月に史上最高値2.660%を記録。Fama-Frenchデータライブラリも日本を含む22カ国で配当利回りポートフォリオを構築・公開済み。buffett-quality（複合スクリーン）とは独立した単一指標効果の検証が目的。
- 出典: https://www.msci.com/resources/factsheets/index_fact_sheet/msci-japan-high-dividend-yield-index-jpy-gross.pdf / https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_port_form_dp.html
- 検証案: jp-rankings.json銘柄に予想配当利回り（実績配当÷株価）をjoinし、高利回り上位三分位vs低利回り下位三分位の翌年リターン差を算出。TSEプライム限定・財務データjoin必要。
- タグ: ○

### slug: jp-size-revival
- 名前: 日本株小型株プレミアム現代再検証（消滅→復活の検証）
- 主張: 日本株で一時消滅したとされる小型株プレミアムが特定条件下で復活している可能性がある【出典の主張・未検証】。Kubota & Takehara (2018) は消滅を報告。Zaremba et al. "Resurrecting the size effect in Japan" (ScienceDirect 2021) では低流動性銘柄除外・値嵩株除外の条件下で効果が再現すると報告。LSEG Equity Factor Insights Q4 2024でも日本スモールキャップが注目ファクターとして言及。
- 出典: https://www.sciencedirect.com/science/article/abs/pii/S0927538X21001487 / https://link.springer.com/article/10.1007/s11156-025-01421-5
- 検証案: jp-rankings.json銘柄を時価総額で三分位に分類し、大型vs小型の過去リターン差を算出。流動性フィルター（売買代金下位20%除外）の有無で2パターン比較し「除外が前提か」を確認。財務データjoin必要。
- タグ: ○

## 2026-08-02（JST）
### slug: amihud-illiquidity-premium
- 名前: Amihud非流動性プレミアム（日本株版）
- 主張: 日次の絶対リターン÷日次出来高（円建て）で計算するAmihud ILLIQ指標が高い銘柄（非流動性が高い銘柄）は将来のリターンが高くなる傾向がある【出典の主張・未検証】。Amihud（2002 JFE）が米国市場で確立し、日本TSE全セクション（東証一部・二部・マザーズ）においても非流動性とリターンに統計的に有意な正の関係が確認されたと報告されている（ScienceDirect）。サイズ・ベータを制御後も効果が持続するとの指摘あり。2023年SSRNではAmihud指標を含む複数の流動性指標を日本株に適用した論文が掲載。
- 出典: https://www.sciencedirect.com/science/article/abs/pii/S0927538X09000572 / https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4605450
- 検証案: jp-rankings.json銘柄の日足データからILLIQ（月次平均=|日次リターン|÷日次出来高の月平均）を計算し、高ILLIQ上位三分位vs低ILLIQ下位三分位の翌月リターン・勝率を比較。価格＋出来高データのみで完結。jp-size-revival（小型株）との交差集計も視野。
- タグ: ◎

### slug: greenblatt-magic-formula
- 名前: Greenblatt Magic Formula（日本株適用）
- 主張: EBIT/EV（利益利回り=EY）とEBIT/投下資本（資本利益率=ROC）の2指標を合算ランキングし上位銘柄群に投資する手法【出典の主張・未検証】。Greenblatt（"The Little Book That Beats the Market" 2005）が提唱。欧州・インド等の複数市場で市場平均を上回るリターンが報告されているが（Poznan大学国際比較論文・SSRN）、日本市場単独の査読論文は現時点で未確認。バリュー（EY）と質（ROC）の相乗効果が仮説の核心。buffett-quality（複合5基準）とは指標選択が異なる。
- 出典: https://journals.ue.poznan.pl/REF/article/view/2790 / https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3945468
- 検証案: 東証銘柄の四半期財務データ（EBIT・EV・投下資本）をjoinし、EYとROCを合算ランキング。上位20%vs下位20%の翌年リターン差を算出。buffett-qualityとの組み合わせ・相関も確認。
- タグ: ○

### slug: dekansho-bushi-seasonality
- 名前: 日本株半期季節性（節分天井・彼岸底型・Dekansho-bushi効果）
- 主張: 日本株では上半期（1〜6月）の月次リターンが有意に正、下半期（7〜12月）のリターンが有意に負になる傾向が50年以上持続しているとされる【出典の主張・未検証】。Springer収録の日本株カレンダー分析論文が確認。「Sell in May」と方向性が一致し、日本独自の企業決算サイクル・外国人投資家の動向が背景として挙げられる。小型株・低PBR銘柄で効果がより顕著との報告あり。larry-williams（月替わり・個別株）とは異なる半期スケール・指数レベルの検証。
- 出典: https://link.springer.com/chapter/10.1007/978-4-431-55501-8_23 / https://www.sciencedirect.com/science/article/abs/pii/S0922142501000676
- 検証案: NKD=F日足データで月別リターンを全期間・2010年以降で集計し、上半期月群（1〜6月）vs下半期月群（7〜12月）の平均リターン・勝率を比較。続いてjp-rankings.json銘柄で時価総額別・PBR別の効果差を確認。価格データのみで完結。
- タグ: ◎

## 2026-08-09（JST）
### slug: ivol-puzzle-jp
- 名前: 固有ボラティリティ・パズル（高IVOL→低リターン・日本株版）
- 主張: 市場モデル（CAPM）の残差として計算される固有ボラティリティ（IVOL）が高い銘柄は、翌月の株価リターンが有意に低くなる傾向がある【出典の主張・未検証】。Ang et al.（2006 JF）が米国で確認し、同グループの2009年論文で23カ国（日本含む）でも負の関係を報告。総ボラティリティ/ベータを使う「低ボラアノマリー（low-volatility 検証済み）」とは異なり、市場リターンを除去した残差リスク成分に特化した別角度の検証。2025年のWiley Financial Management掲載論文でも「IVOL逆説はアービトラージ制約で持続」と確認。
- 出典: https://onlinelibrary.wiley.com/doi/full/10.1111/fima.70058 / https://alphaarchitect.com/idiosyncratic-volatility/
- 検証案: signals-log/jp-rankings銘柄の日足データでTOPIX代理（NKD=F）への過去21日回帰を実施し残差標準偏差（IVOL）を月次計算。高IVOL上位三分位 vs 低IVOL下位三分位の翌月リターン・勝率を比較。価格データのみで完結。
- タグ: ◎

### slug: net-issuance-anomaly-jp
- 名前: 株式純発行アノマリー（希薄化企業は割高・日本株版）
- 主張: 前期比で発行済株式数が増加した銘柄（増資・新株予約権行使等）は翌年の株価リターンが低く、減少した銘柄（自社株買いによる消却）は高い傾向がある【出典の主張・未検証】。Loughran & Ritter（1995）が米国で確認。Kang, Kim & Stulz（1999）が日本株で公募増資後の長期マイナス超過リターンを報告。Lu（NBER w23809, 2017）が日本・英国・仏独加5カ国で11アノマリーを横断検証し純発行アノマリーが有意に機能すると確認。背景＝経営者が株価過大評価タイミングを見計らって増資する「マーケットタイミング仮説」。japan-buyback-post（短期イベント効果・watchリスト）とは独立したクロスセクション年次比較の別仮説。
- 出典: https://www.sciencedirect.com/science/article/abs/pii/S0304405X09001007 / https://www.nber.org/system/files/working_papers/w23809/w23809.pdf
- 検証案: jp-rankings銘柄の財務データから「発行済株式数変化率」を年次計算し、増加率上位三分位（希薄化）vs 減少三分位（自社株買い消却）の翌年リターン差を算出。jp-asset-growth（総資産成長・queued）とは変数が異なるため独立検証。
- タグ: ○

### slug: net-payout-yield-jp
- 名前: 総株主還元利回り（配当+自社株買い統合ファクター・日本株版）
- 主張: 配当利回りと自社株買い利回りを合算した「ネット・ペイアウト・イールド」（NPY＝（配当＋純自社株買い消却額）÷株価）が高い銘柄群は、配当利回り単独より翌年リターンの予測力が有意に高い傾向がある【出典の主張・未検証】。Ibbotson & Straehl（2017）が米国1871〜2014年で「NPYは実現リターンのほぼ全説明力を持つ」と報告。Meb Faberの実証でも米国株・国際株で配当+自社株買いの合算指標が優位。日本では2023年以降のTSE資本効率要請で配当+自社株買いが過去最高水準（FY2025: 22兆円超）となり環境的追い風が強い。jp-high-dividend-yield（未消化・配当のみ）との比較で「自社株買い付加価値」も同時検証可能。
- 出典: https://quantpedia.com/strategies/net-payout-yield-effect / https://mebfaber.com/wp-content/uploads/2023/05/Shareholder-Yield.pdf
- 検証案: jp-rankings銘柄の財務データから「配当総額＋自社株買い消却額」をjoinしNPYを計算。高NPY三分位 vs 低NPY三分位の翌年リターン差を算出。jp-high-dividend-yield（配当のみ版）との差分で自社株買い要素の追加効果を定量化。
- タグ: ○

## 2026-08-16（JST）
### slug: piotroski-fscore-jp
- 名前: ピオトロスキーFスコア（日本株版）
- 主張: 財務健全性の9バイナリー指標（収益性4：ROA・ΔROAt・CFO・Δ粗利益率、財務健全性3：Δ負債比率・Δ流動比率・新株発行なし、効率性2：Δ粗利益率・Δ資産回転率）の合計スコアが高い（8〜9点）銘柄群は低スコア（0〜2点）銘柄を大幅にアウトパフォームする傾向がある【出典の主張・未検証】。Piotroski（2000, JAR）が米国で年率13.4%の超過リターンを報告。Noma（2010）が日本（1986〜2001年）でハイBM×ハイFスコアのヘッジポートフォリオが年率17.6%を達成と報告。2020年の国際研究「Piotroski's F-Score: international evidence」でも米国外市場での有効性が確認されている。buffett-quality（tested・5基準複合）とは指標体系が異なる別検証。
- 出典: https://quantpedia.com/strategies/piotroski-f-score-effect-in-stocks/ / https://www.quant-investing.com/blog/piotroski-f-score-improves-global-stock-performance
- 検証案: 東証銘柄の四半期財務データ（ROA・CFO・負債比率・発行済株式数・資産回転率）から9点スコアを計算し、高スコア（8〜9点）vs 低スコア（0〜2点）の翌年リターン差を算出。jp-rankings銘柄で高PBR（割高）時の誤検知率も確認する。財務データjoin必要。
- タグ: ○

### slug: long-term-reversal-jp
- 名前: 長期リターン反転効果（3〜5年敗者逆張り・日本株版）
- 主張: 直近3〜5年間のリターンが市場全体の最下位だった「敗者」銘柄群が、最上位の「勝者」銘柄群を翌3〜5年で有意にアウトパフォームする傾向がある【出典の主張・未検証】。De Bondt & Thaler（1985 JF）が米国1926〜1982年の36ヶ月評価で「敗者は勝者を24.6%上回る」と報告。日本株では1975〜2000年データを対象とした分析（Applied Financial Economics 2003）で「敗者優位」が確認されているが、勝者の明確なアンダーパフォームは米国ほど顕著でないとの報告もあり証拠は部分的。momentum-12-1（tested・1年順張り）とは方向とラグが逆の独立した現象。short-term-reversal-1w（tested・1週間）とはスケールが大きく異なる。
- 出典: https://www.sciencedirect.com/science/article/abs/pii/S0922142503000574 / https://alphaarchitect.com/quantitative-momentum-research-long-term-return-reversal/
- 検証案: jp-rankings銘柄の日足データで過去36ヶ月・60ヶ月リターン下位三分位（敗者）vs 上位三分位（勝者）を構成し、翌12ヶ月リターン・勝率を比較。価格データのみで完結。momentum-12-1（順張り）の結果と方向を重ね合わせて「持続ゾーンvs反転ゾーン」の変わり目の時間軸を確認する。
- タグ: ◎

### slug: sector-momentum-jp
- 名前: セクター・モメンタム（業種ローテーション・日本株版）
- 主張: 過去12ヶ月リターンが上位だった業種セクターの株を買い、下位業種を売るローテーション戦略が、銘柄レベルのクロスセクション・モメンタムの多くを説明し、サイズ・BM・個別株モメンタムを制御後も有意な超過リターンを示す傾向がある【出典の主張・未検証】。Moskowitz & Grinblatt（1999 JF「Do Industries Explain Momentum?」）が米国で確認。2023年にSpringer Asia-Pacific Financial Markets掲載の「Decomposing the Momentum in the Japanese Stock Market」論文が日本株モメンタムを業種成分と個別成分に分解し、業種が一定の説明力を持つことを示唆。momentum-12-1（tested・個別株クロスセクション）とは集計レベルが異なり独立した検証。
- 出典: https://quantpedia.com/strategies/sector-momentum-rotational-system / https://link.springer.com/article/10.1007/s10690-023-09413-y
- 検証案: jp-rankings銘柄をjp-stock-info.jsonの業種フィールドでグルーピングし、業種別過去12ヶ月平均リターンを計算。上位3業種 vs 下位3業種の翌3ヶ月リターン差・勝率を算出。業種カバレッジが不足する場合はTOPIX業種別指数（価格データ）で代替検証する。
- タグ: ◎
