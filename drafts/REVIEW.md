# 🤖 AUTODRAFT REVIEW ノート（最新が上）

---

## 2026-06-08 | risk-reward

- **基準日（JST）**: 2026-06-08（UTC 2026-06-07T20:35:16Z）
- **Topic**: リスクリワードと期待値（勝率×損益比）
- **Key**: `risk-reward`
- **生成ファイル**: `drafts/draft-risk-reward.html`
- **シリーズ**: 🛡️ リスク管理・資金管理（guides.html 既存カテゴリ、初回は人間が新設）

### 参照出典 URL
| 項目 | 出典 |
|---|---|
| リスクリワード比・期待値計算式（松井証券） | https://www.matsui.co.jp/fx/study/article/analysis/risk-reward/ |
| リスクリワードの意味・計算式・目安（OANDA Japan） | https://www.oanda.jp/lab-education/beginners/aboutfx/moneymanagement1/ |
| リスクリワード比の解説（IG証券） | https://www.ig.com/jp/trading-strategies/risk-reward-ratio-explained-210729 |
| Risk Reward Ratio Explained（VT Markets） | https://www.vtmarkets.com/discover/risk-reward-ratio-explained-formula-trading/ |
| Win Rate vs Risk-Reward（JournalPlus） | https://journalplus.co/learn/guides/win-rate-vs-risk-reward/ |
| Win Rate and R:R: Connection Explained（LuxAlgo） | https://www.luxalgo.com/blog/win-rate-and-riskreward-connection-explained/ |

### 自己コンプライアンスチェック結果
| チェック項目 | 結果 |
|---|---|
| 個別銘柄の売買推奨なし | ✅ 教育・一般論のみ。「今 ○○ を買え」等の表現なし |
| 断定・利益保証表現なし | ✅「絶対」「必ず」「100%」「保証」「儲かる」使用なし。計算例は「概念の説明用」と明記 |
| kinsho-v1 免責（冒頭バナー＋本文末＋footer）あり | ✅ 3箇所に data-disclaimer="kinsho-v1" または同等の文言を配置 |
| noindex,nofollow あり | ✅ `<meta name="robots" content="noindex,nofollow">` を head に配置済み |
| 出典の妥当性 | ✅ 松井証券・OANDA・IG証券（国内金融機関）の公開記事、VT Markets・JournalPlus・LuxAlgoの英語教育記事を参照。損益分岐勝率の計算式（BEW = 1÷(1+R:R)×100）は業界標準的な数学公式であり、複数の信頼できる出典で確認済み。期待値例（勝率60%・R:R=0.5 → EV=−1,000円など）は自己計算値だが式に基づく純粋な算術 |
| SVG 概念図に「※ 概念を示すイメージ図です」の注記 | ✅ 全 2 点の figcaption に注記あり |

### SVG 図の構成
1. **損益分岐勝率カーブ**（X軸=R:R、Y軸=勝率、曲線で緑/赤ゾーンを区切り、例示点A・B をプロット）— 実装済み
2. **R:R=1:2 エントリー・SL・TP 設定図**（価格ライン＋リスク/リワードのブラケット注釈）— 実装済み
3. `<!-- TODO(SVG): トレーダーAとBの100トレード累積損益バーチャート（横軸=トレード回数, 縦軸=累積損益）を要追加・要ライト/ダーク実機確認 -->`

### 人間の残作業
- [ ] **SVG の実機ライト/ダーク確認**：追加クラス `.s-zone-g` `.s-zone-r` `.s-bew` `.s-entry-line` `.s-sl-line` `.s-tp-line` `.s-bracket` `.s-dot-b` `.s-dot-r` `.s-dot-g` をライト・ダークモードで目視確認。特にポリゴン塗りつぶしのゾーン色（fill-opacity）がダークモードで見づらくないか確認
- [ ] **累積損益バーチャートの追加**（HTML 内の `TODO(SVG)` コメントを参照）：トレーダーA vs B の100トレード累積損益を横フローバーチャートで示す
- [ ] **Opus compliance-reviewer 監査**：公開前に `compliance-reviewer` エージェント（Opus）に下書き全文を渡してレビューを依頼
- [ ] **タイトル・見出しの微調整**：現タイトルは適切だが「期待値計算」「損益分岐勝率」など検索需要の高いキーワードをtitle/descriptionでさらに前出しすることを検討
- [ ] **関連記事リンクの確認**：`guide-profit-taking.html`（第4弾予定）公開後に related カードに追加
- [ ] **loss-cut.html との相互リンク確認**：loss-cut.html 末尾の「リスクリワードは別記事で」予告から本記事への内部リンクを公開時に追加

---

## 2026-06-07 | trading-psychology-calm

- **基準日（JST）**: 2026-06-07（UTC 2026-06-06T20:33:37Z）
- **Topic**: 感情のコントロール・平常心の作り方（FOMO／狼狽売り／リベンジトレード）
- **Key**: `trading-psychology-calm`
- **生成ファイル**: `drafts/draft-trading-psychology-calm.html`
- **シリーズ**: 🧠 投資の心理・メンタル（guides.html 既存カテゴリ）

### 参照出典 URL
| 項目 | 出典 |
|---|---|
| FOMO の定義・投資心理 | https://fxshinri.com/mindset/fx-mindset-fomo/ |
| FOMO の定義（野村証券用語集） | https://www.nomura.co.jp/terms/english/other/A03432.html |
| Barber &amp; Odean (2000) 研究 | https://www.britannica.com/money/trading-psychology |
| 行動経済学・感情とトレード | https://www.heygotrade.com/en/blog/behavioral-finance-in-trading |
| マインドフルネスとトレード成績 | https://www.researchgate.net/publication/327138465_The_Role_of_Mindfulness_Meditation_on_Stock_Trading_Performance |
| マインドフルネスと処分効果 | https://oro.open.ac.uk/84403/1/PhD_thesis_Wong_Ernest.pdf |
| 扁桃体・感情制御（一般） | https://www.sciencedirect.com/science/article/abs/pii/S0306453025003440 |

### 自己コンプライアンスチェック結果
| チェック項目 | 結果 |
|---|---|
| 個別銘柄の売買推奨なし | ✅ 教育・一般論のみ。「今 ○○ を買え」等の表現なし |
| 断定・利益保証表現なし | ✅「絶対」「必ず」「100%」「保証」「儲かる」使用なし |
| kinsho-v1 免責（冒頭バナー＋本文末＋footer）あり | ✅ 3箇所に data-disclaimer="kinsho-v1" または同等の文言を配置 |
| noindex,nofollow あり | ✅ `<meta name="robots" content="noindex,nofollow">` を head に配置済み |
| 出典の妥当性 | ✅ Barber &amp; Odean (2000) は学術誌 Journal of Finance 掲載。マインドフルネス研究は ResearchGate / ScienceDirect の論文を参照。不確実な数値（「70%」「15%」等の出典不明統計）は使用していない |
| SVG 概念図に「※ 概念を示すイメージ図です」の注記 | ✅ 全 2 点に注記あり |

### SVG 図の構成
1. **感情の悪循環ループ**（FOMO→含み損・恐怖→狼狽売り／リベンジ→損失拡大の4ステップ循環図）— 実装済み
2. **2パターン比較図**（感情主導 vs ルール主導の3ステップ比較）— 実装済み
3. `<!-- TODO(SVG): 取引前→中→後のトレードルーティン・タイムライン図（横フロー）を要追加・要ライト/ダーク実機確認 -->`

### 人間の残作業
- [ ] **SVG の実機ライト/ダーク確認**：追加クラス `.s-box-warn` `.s-box-neg` `.s-box-pos` `.s-box-neu` `.s-box-label` `.s-box-sub` `.s-arr-r` `.s-arr-g` `.s-arr-fill-r` `.s-arr-fill-g` をライト・ダークモードで目視確認
- [ ] **ルーティン・タイムライン SVG の追加**（HTML 内の TODO(SVG) コメントを参照）：取引前・中・後の3フェーズを横フローで示す図
- [ ] **Opus compliance-reviewer 監査**：公開前に `compliance-reviewer` エージェント（Opus）に下書き全文を渡してレビューを依頼
- [ ] **タイトル・見出しの微調整**：タイトルが長いため短縮案を検討（例：「感情のコントロール完全ガイド｜FOMO・狼狽売り・リベンジトレードを克服する」）
- [ ] **関連記事リンクの確認**：`guide-risk-reward.html`（第3弾予定）が公開されたら related カードに追加

---

## 2026-06-06 | position-sizing

- **基準日（JST）**: 2026-06-06（UTC 2026-06-05T23:51:50Z）
- **Topic**: ポジションサイジング／資金管理（1トレードの許容リスク%・2%ルール）
- **Key**: `position-sizing`
- **生成ファイル**: `drafts/draft-position-sizing.html`
- **シリーズ**: 🛡️ リスク管理・資金管理（初回記事 → 公開時に guides.html に新カテゴリを人間が追加）

### 参照出典 URL
| 項目 | 出典 |
|---|---|
| 2%ルール | https://www.quantifiedstrategies.com/the-2-rule-money-management/ |
| 2%ルール（CME） | https://www.cmegroup.com/education/courses/trade-and-risk-management/the-2-percent-rule |
| ATR ポジションサイジング | https://www.vtmarkets.com/discover/average-true-range-atr-indicator-guide-master-volatility-trading/ |
| 破産確率・ドローダウン回復 | https://thearcalabs.com/en/insights/risk-of-ruin-trading/ |
| 破産確率・ドローダウン回復 | https://daytradingtoolkit.com/beginners-guide/risk-of-ruin-math-explained/ |
| ケリー基準 | https://corporatefinanceinstitute.com/resources/data-science/kelly-criterion/ |
| ケリー基準（分数ケリー） | https://www.quantifiedstrategies.com/kelly-criterion-position-sizing/ |
| Van Tharp の R 概念 | https://vantharpinstitute.com/van-tharp-teaches-position-sizing-strategies-and-risk-management/ |
| R-Multiples | https://traderlion.com/risk-management/r-and-r-multiples/ |

### 自己コンプライアンスチェック結果
| チェック項目 | 結果 |
|---|---|
| 個別銘柄の売買推奨なし | ✅ 教育・一般論のみ。「今 ○○ を買え」等の表現なし |
| 断定・利益保証表現なし | ✅「絶対」「必ず」「100%」「保証」「儲かる」使用なし |
| kinsho-v1 免責（冒頭バナー＋本文末＋footer）あり | ✅ 3箇所に data-disclaimer="kinsho-v1" または同等の文言を配置 |
| noindex,nofollow あり | ✅ `<meta name="robots" content="noindex,nofollow">` を head に配置済み |
| 出典の妥当性 | ✅ 数値はすべて上記の信頼できる出典から確認。推測値は使用していない |
| SVG 概念図に「※ 概念を示すイメージ図です」の注記 | ✅ 全 2 点に注記あり |

### SVG 図の構成
1. **2%ルールの構造図**（口座残高→許容損失額→ポジションサイズへの逆算）— 実装済み
2. **ドローダウンと回復率の非線形曲線**（10%→11%, 30%→43%, 75%→300% のデータ点入り）— 実装済み
3. `<!-- TODO(SVG): ケリー基準のベット比率（横軸）と対数資産成長率（縦軸）の放物線型カーブ — HTML 内コメントとして残置。要人間による実機ライト/ダーク確認後、追加を検討 -->`

### 人間の残作業
- [ ] **SVG の実機ライト/ダーク確認**：特に `s-bar-b` / `s-fill-b` / `s-fill-r` 等の追加クラスをライト・ダークモードで目視確認
- [ ] **ケリー基準 SVG の追加**（HTML 内の TODO(SVG) コメントを参照）：放物線型カーブ（最適ベット比率を示す）を追加するか検討
- [ ] **Opus compliance-reviewer 監査**：公開前に `compliance-reviewer` エージェント（Opus）に下書き全文を渡してレビューを依頼
- [ ] **タイトル・見出しの微調整**：タイトルが長めなので「ポジションサイジング完全ガイド」等への変更を検討
- [ ] **公開時の追加作業**：`guides.html` に新カテゴリ「🛡️ リスク管理・資金管理」を人間が作成し、記事カードを追加（`mw publish` の `--category` で指定）
- [ ] **loss-cut.html のリンク確認**：loss-cut.html に「資金管理は別記事で」という予告リンクがあるか確認し、公開後に相互リンクを更新

---
