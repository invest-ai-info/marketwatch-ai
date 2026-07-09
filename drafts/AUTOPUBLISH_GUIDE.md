# 🚀 下書き自動公開ルーティン 手順書（AUTOPUBLISH SOP・2026-07-05 新設）

routine `autodraft-publish`（毎日 08:40 JST）が読む手順書。**autodraft が生成した下書きを、
ゲート全通過のときだけ 1日1本 自動公開する**（オーナー承認済み＝2026-07-05 に完全無人化へ移行）。
方式は news-daily-auto / signal-lab-daily と同じ「決定論緑 → Opus白 → 公開／ダメならエスカレ」。

## 原則（違反したら公開しない）
- 公開は **本レーン（autodraft topicキュー）1日1本まで**。判定は「当日の `drafts/REVIEW.md` に本ルーティン（autopublish）の公開記録があるか」で行う。
  **⚠️ signal-lab／ニュース／格言／新刊など他レーンの当日公開はカウントしない**（各レーンは独立。2026-07-08 に signal-lab の朝公開を「当日公開済み」と誤判定して無言スキップした実例あり）。
- **スキップ・対象なしで終了する場合も、`drafts/REVIEW.md` 先頭に「YYYY-MM-DD autopublish: スキップ（理由）」を1行追記してコミットする（沈黙禁止）**。無言終了は失敗と区別できないため禁止。
- **編集禁止ファイル（固定ゲート4本＝固定オラクル）**: `check_guide_draft.py`／`check_site_consistency.py`／`signal_lab_verify.py`／`publish_article.py`。実行前に `git checkout origin/main -- <4本>` で確定版に戻し、**実行のみ**（signal-lab の固定オラクル方式と同じ）。ほかに 6コアHTML・political・track-record 等の SYNC禁忌（CLAUDE.md参照）。
- **🚫 ゲート/リンターが赤でも、ゲート自体を編集・commitして通すのは自己承認＝完全禁止（オーナー決定 2026-07-09。等価な書き換え・バグ修正のつもりでも禁止）**。実例: 2026-07-09 朝に本 routine が `check_site_consistency.py` のクラウドスタブ分岐を独自実装へ書き換えて公開を通過（内容は等価だったが方式として不可）。ゲートの不具合を疑う場合も公開せず `drafts/REVIEW.md` に「🚩ゲート赤／ゲート不具合疑い」でエスカレ＝ゲートの修正は人間のローカルセッション専任。違反は automation-health が commit author 照合で自動検知して Issue 化する。
- 迷ったら公開せず `drafts/REVIEW.md` に「🚩要人間レビュー」でエスカレ（理由と対象を明記）。

## 手順

### 1. 対象を1本選ぶ
`drafts/AUTODRAFT_GUIDE.md` の topicキュー順で、**`drafts/draft-<key>.html` が存在し、`guide-<key>.html` が未公開（guides.html にカードが無い）の最初の1本**。該当なしなら終了。

### 2. 仕上げ（下書き→公開版）
作業は `guide-<key>.html` として保存する版に対して行う:
- `<meta name="robots" content="noindex,nofollow">` を削除。canonical / OGP url を `guide-<key>.html` に整合。
- meta-line の日付を公開日に。**本文の数値・固有名詞を WebSearch で再確認**（不確実なら削るか出典明記）。
- `TODO(SVG)` が残っていれば図を完成させる。SVGのラベル重なり・はみ出しは**自分で座標修正してよい**（レイアウト修正はコンプラ無関係。ゲート緑まで最大3回イテレート）。
- `QUALITY_RUBRIC.md` の品質レーンで自己チェック（不合格項目は修正）。

### 3. 決定論ゲート
`python check_guide_draft.py guide-<key>.html` → **exit 0 必須**。RED はエスカレ（公開しない）。

### 4. コンプラ＋品質ゲート（Opus・signal-lab方式）
compliance-reviewer 相当の Opus 監査（黒/グレー/白・QUALITY_RUBRIC 併用）:
- 🟢白 → 公開へ。
- 🟡軽微（表現軟化・免責追記のみで直る）→ Opusが修正 → **手順3を再実行（緑必須）** → **別の独立Opusが白を確認** → 公開へ（自己承認禁止の2段構え）。
- 🔴黒・🟡要協議・独立確認が取れない → エスカレ（公開しない）。

### 5. 公開
```
python publish_article.py --file guide-<key>.html --category <下表> --emoji <下表> \
    --card-title "<短いタイトル>" --desc "<カード説明文>"
```
| シリーズ | --category（guides.html の見出しと完全一致させる） | --emoji |
|---|---|---|
| 投資心理 | 投資の心理・メンタル | 🧠 |
| リスク管理 | リスク管理・資金管理 | 🛡️ |
| 基礎知識 | 投資の基礎知識 | 💰 |

カテゴリ名の照合に失敗（カードが入らない等）したら中止してエスカレ。
`python check_site_consistency.py` を実行し error が無いこと。**error があれば公開中止→🚩エスカレ（ゲートを編集して緑にするのは禁止＝上の原則）**。

### 6. コミット＝PUSH-MAIN規約（signal-labと同じ）
`git fetch origin main && git rebase origin/main && git push origin HEAD:main` を最大5回リトライ。
5回失敗時のみ `autopublish-pending-<UTC>` ブランチに退避してエスカレ。
（push すると update-market-news の on:push が index の更新履歴を再描画する）

### 7. 事後確認と記録
- `https://marketwatch-jp.com/guide-<key>.html` が HTTP 200（数分待って最大3回）。
- `drafts/REVIEW.md` の先頭に1行追記: 日付／key／ゲート結果（決定論緑・Opus白 or 軽微修正→独立白）／URL。
- 下書き `drafts/draft-<key>.html` は**削除しない**（生成来歴として残す。手順1の判定は guides.html カード有無で行う）。
