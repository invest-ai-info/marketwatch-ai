# 📖 投資本 新刊ウォッチ 手順書（BOOKWATCH SOP・2026-07-05 新設）

routine `book-watch-weekly`（毎週土曜 11:00 JST）が読む手順書。**直近1ヶ月に日本で発売された
投資・マネー関連の新刊を探し、`guide-new-books.html` に中立な紹介を積み上げる**（オーナー依頼）。

## 原則
- **紹介であってレビューでも推薦でもない**（未読の本を評価しない）。「読めば勝てる」系の表現・投資成果の約束は書かない・引用しない。
- **事実（書名・著者・出版社・発売日）は必ず2ソースで照合**（出版社公式サイト＋Amazon/版元ドットコム/honto 等）。照合できない本は載せない。
- アフィリエイトリンクは張らない（リンクは出版社公式 or 書誌ページのみ・nofollow不要）。
- `guide-new-books.html` は **この routine だけが編集する**（SYNC禁忌登録済み＝ローカルから push されない）。
- 編集禁止: 6コアHTML・political 等の SYNC禁忌（CLAUDE.md 参照）。guides.html は初回のカード追加のみ可。

## 毎回の手順

### 1. 新刊を探す（WebSearch）
「投資 新刊 <今月>」「株 本 新刊」「資産運用 書籍 発売」等で検索し、**発売日が直近30日以内**の
投資・トレード・資産形成・経済の一般書を候補化。教材商法・情報商材・自費出版の煽り本は除外。
**1〜3冊**選ぶ（該当なしの週は「今週は該当なし」でページの更新日だけ進めて終了＝無理に載せない）。

### 2. 事実照合
各候補について書名/著者/出版社/発売日/税込価格(分かれば)を2ソースで一致確認。紹介文は
**出版社の公式紹介文の要約**＋「どんな人向けか」1行（中立表現）。

### 3. ページ更新
`guide-new-books.html` の `<!-- BOOKWATCH:INSERT -->` マーカー直後に新エントリを挿入（最新が上）。
エントリ形式は既存エントリを踏襲（書名・著者・出版社・発売日・紹介3〜4行・「こんな人向け」）。
掲載は**最新40冊まで**＝超過分は最下部から削除。ページ冒頭の「最終更新: YYYY-MM-DD」を更新。

**初回のみ（ページが存在しない場合）**:
- `guide-investment-books.html` をデザインテンプレとして新規作成（同じ head/style/nav10ボタン/
  breadcrumb/kinsho-v1免責/footer。noindexは入れない。canonical=guide-new-books.html）。
- h1=「📖 投資本 新刊ウォッチ（毎週更新）」＋前書き（毎週土曜更新・紹介であって推薦ではない旨・
  掲載基準）＋ `<!-- BOOKWATCH:INSERT -->` マーカー＋初回の新刊エントリ。
- `guides.html` の投資本カテゴリ（無ければ「📖 投資本」見出しの近く）にカードを1枚追加。
- `guide-investment-books.html` の冒頭付近に新刊ウォッチへのリンク1行を追加（この1回のみ編集可）。

### 4. 決定論チェック → コミット → 確認
- `python check_guide_draft.py guide-new-books.html` → exit 0 必須（REDなら公開せずエスカレ）。
- PUSH-MAIN規約でコミット（fetch+rebase+push HEAD:main 最大5回。失敗時 `bookwatch-pending-<UTC>` 退避）。
- `https://marketwatch-jp.com/guide-new-books.html` HTTP 200 確認。
- 問題・判断に迷う本（コンプラ怪しい・情報商材との境界）は載せず `drafts/REVIEW.md` に1行メモ。
