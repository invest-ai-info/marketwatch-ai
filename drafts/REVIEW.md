# 🤖 AUTODRAFT REVIEW ノート（最新が上）

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
