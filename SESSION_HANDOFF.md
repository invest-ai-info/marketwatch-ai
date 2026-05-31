# 🔖 セッション引き継ぎ（最終更新: 2026-05-31）

新セッションはこのファイル＋ CLAUDE.md ＋ `memory/03_initiatives.md` を読めば文脈を復元できます。

---

## 🎯 直近2セッション（5/29〜5/31）でやったこと

「シグナル成績が悪い」を起点に、**個人トレード支援の自動化**と**サイトの情報品質向上**を一気に構築。詳細は `SIGNAL_REDESIGN.md` と `memory/03_initiatives.md`。

### A. 自動で回り続けている仕組み（予約エージェント routine ＋ GitHub Actions）

| 仕組み | 種別 / ID | スケジュール(JST) | 役割・出力 |
|---|---|---|---|
| **fundamental-briefing** | routine `trig_01M7uY1H8uR6tEwF1CJ7jXzV` | 毎日 06:00 / 15:00 | 信頼性検証ニュース＋regime/bias → `fundamental-context.json`。日本語・`published`日付・`comment`(💡一言)付き |
| **weekly-levels** | Actions `weekly-levels.yml` | 日曜 17:00 | `compute_levels.py`で18銘柄の正確な水準 → `weekly-levels.json`（※CCRはyfinance403不可なのでActions側で計算） |
| **weekly-zone-plan** | routine `trig_01LP5pbD28BK55bE3GZWaHJf` | 日曜 20:00 | 18銘柄の上下ゾーン＋ラダー指値＋SL/TP/R:R → `weekly-zone-plan.md`（weekly-levels.jsonを読む） |
| **weekly-zone-email** | Actions `weekly-zone-email.yml` | 日曜 21:30 | `email_weekly_zone.py`で weekly-zone-plan.md をHTMLメール送信（→ info0414@gmail.com） |

- routine の確認/編集: claude.ai `/code/routines/<ID>`、または schedule スキル＋RemoteTrigger ツール（プロンプト変更は update）。
- routine は **クラウド(CCR)実行**。リポジトリへ commit は可能だが **yfinance は403で不可**・Gmail鍵も持てない（→データ計算とメール送信はActions側に分離している）。

### B. シグナルエンジン再設計（`SIGNAL_REDESIGN.md`）
- トップダウン4階建て（Layer0リスク環境→Layer1方向バイアス→Layer2テクニカル→Layer3ブレーキ）。
- **Phase 1 デプロイ済（記録のみ）**：`generate_technical_alerts.py` が各シグナルに `risk_regime`/`directional_bias`/`fundamental_context.bias_aligned` を記録。発火・メール挙動は不変。
- track-record.html の既定タブを **4H（本番成績≈54%）** に変更済。
- **Phase2/3 未着手**：データ蓄積後に「bias逆行を弾けば勝率改善するか」を signals-log で検証 → OKなら発火フィルタ本稼働。

### C. サイト（marketwatch-jp.com）の改善
- トップ「本日のマーケット」4カードの📰関連ニュースを **検証済みブリーフィング**（✔信頼度/🗓日付/💡コメント）に差し替え。重複していた専用「信頼性検証済みニュース」セクションは**削除**。古い順問題は published 日付の新しい順ソートで解消。
- **市場解説2記事を公開**（compliance🟢・8ステップ済）：
  - `guide-japan-strategy-2026-05.html`（攻め/守りセクター戦略）
  - `guide-bank-stocks-2026-05.html`（日銀利上げと銀行株・メガvs地銀）

### D. その他
- `SwingTrend_EA.mq4`（日足トレンド押し目＋3ATR追従）：バックテストで実データのエッジは薄く**実弾見送り**。手動の出口管理ツールとして保管。
- ユーザーの実トレードを `my-trades.json` に第7〜17号まで記録済（今週分ネット +4,165 円）。

---

## ⚠️ 絶対遵守（事故防止）

- **SYNC禁忌**（ローカルから絶対 push しない＝routine/cronがGitHub側で生成）：
  6コアHTML / `signals-log.json` / `technical-alerts-history*.json` / `track-record.html` / political系 / youtube系
  **＋今セッション追加：`fundamental-context.json` / `weekly-levels.json` / `weekly-zone-plan.md`**
  （※CLAUDE.mdのSYNC禁忌リストに fundamental-context.json は追記済。weekly-levels.json / weekly-zone-plan.md も追記推奨＝**新セッションの軽タスク**）
- SYNC対象（OK）：`*.py`（compute_levels.py, email_weekly_zone.py 等）/ `.github/workflows/*.yml` / 個別 guide-*.html / guides.html / sitemap.xml / my-trades.json / memory/*.md / docs。
- 記事追加は **CLAUDE.md の8ステップ厳守**（新HTML→guidesカード→sitemap→SYNC_FILES→generate_market_news.pyの更新履歴5件キープ→sync→update-market-news の workflow_dispatch→ライブ確認）。**公開前に compliance-reviewer（Opus）監査・教育トーン・特定銘柄の買い推奨は書かない・kinsho-v1免責・9ボタンナビ**。
- ネット不調時は無限リトライせず手動 trigger 依頼（最大3-5回）。

---

## 📌 次セッションの候補・宿題

1. **Max枠の確認**：routine実行が Claude Max の利用枠から引かれているか別課金か、claude.ai「利用状況」で確認（未確認）。
2. **CLAUDE.md SYNC禁忌の追記**：`weekly-levels.json` / `weekly-zone-plan.md` を正式追加（軽タスク）。
3. **記事ネタ（ユーザー興味ベース）**：他セクター深掘り→記事化（AI半導体／ディフェンシブ／高配当 等。銀行は公開済）。
4. **日本株ゾーンの週次組込**（保留中）：PBR1.0・配当利回りの床を weekly-zone-plan に「日本株セクション」として追加する案。
5. **シグナル再設計 Phase2**：fundamental_context / bias_aligned のデータが貯まったら signals-log で検証。
6. **弁護士相談アジェンダ**（来週予定）：track-record統計開示／⭐確信度ラベル／「ソース信頼度」ラベル／セクター記事の銘柄言及。

---

## 運用メモ
- 作業フォルダ: `C:\Users\info0\OneDrive\デスクトップ\新しいフォルダー` ／ GitHub: `invest-ai-info/marketwatch-ai`(main)
- 同期: `python sync_to_github.py`。workflow手動起動はGitHub APIの workflow_dispatch（tokenは market-news-config.json.json）。
- routine操作: schedule スキル → `ToolSearch select:RemoteTrigger` → RemoteTrigger（list/get/update/run）。
- ユーザー方針: 「攻めと守りの両建て」「感情に左右されない自動化」「記事化するネタ＝本人の興味」。最終目標は投資家全体の底上げ／サイトSNS年収1000万／個人投資成績 年収1億。
