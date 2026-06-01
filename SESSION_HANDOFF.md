# 🔖 セッション引き継ぎ（最終更新: 2026-06-01）

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
| **article-idea-scout** 🆕 | routine `trig_01FmFNFSTkdx35nu1kWwKoYW` | 毎日 07:30 | 記事ネタ候補（SEOタイトル案＋根拠ソース）→ `article-ideas.md`（非公開・編集用メモ） |
| **daily-market-preview** 🆕 | routine `trig_01GFQ6tLGPhvEZ5crJgPRqCh` | 毎日 21:00 | 翌日の重要指標＋市場コンセンサス（economic-events.json突合）→ `daily-preview.md`（非公開・個人用） |
| **political-digest** 🆕 | routine `trig_01B1WV4bru6iFxr7SFB94huh` | 毎日 22:00 | political-feed.json を要約（重要発言トップ3-5＋市場影響）→ `political-digest.md`（非公開） |
| **compliance-patrol** 🆕 | routine `trig_016Pkyto4UfxhHP1sU2i5NP9` | 日曜 09:00 | 公開 guide-*.html を法務巡回（黒/グレー/白）→ `compliance-scan.md`（非公開・監査メモ） |
| **weekly-strategy-brief** 🆕 | routine `trig_01StownkcHrYyRbMMpVxVy2Z` | 日曜 18:30 | **3人エージェント(fund/tech/risk)で起案＋検証エージェントが全数値をweekly-levels.jsonと照合＋compliance** → `weekly-strategy-context.json`（`verified`付き） |
| **weekly-strategy（描画）** | Actions `weekly-strategy.yml` | 日曜 20:13(+30) | 上記contextで週次戦略記事を強制再描画（旧18:13の冗長版を転用）。verified=trueのシナリオのみ反映 |

> 🆕 **2026-05-31〜06-01 新設 routine 計5本**（Max枠に余裕＝15/日中、日次でも実質5本程度）。article-idea-scout/daily-market-preview/political-digest/compliance-patrol は社内向けmd（非公開）。weekly-strategy-brief は週次戦略記事のシナリオ源（公開記事に反映）。出力JSON/mdは全て **SYNC禁忌に追加済**（routineがmain生成、ローカルpush禁止）。routine は Gmail鍵/yfinance不可（メール送信・価格計算はActions側）。

- routine の確認/編集: claude.ai `/code/routines/<ID>`、または schedule スキル＋RemoteTrigger ツール（プロンプト変更は update）。
- routine は **クラウド(CCR)実行**。リポジトリへ commit は可能だが **yfinance は403で不可**・Gmail鍵も持てない（→データ計算とメール送信はActions側に分離している）。

### A2. 週次戦略の品質アップグレード＋日付バグ修正（2026-06-01）
- **問題**：週次戦略記事のシナリオ数字（日経60-61k等）が `auto_weekly_strategy.py` に**ハードコードされ陳腐化**（実勢66k/ドル円159/BTC73k と乖離）。精度＆コンプラ問題。
- **対応①応急**：誤数字のシナリオ表を撤去し「リニューアル中」プレースホルダへ（force再生成でライブ反映済み、誤情報除去）。リスク欄の「158円」も中立化。
- **対応②本命＝多エージェント＋数値検証パイプライン**（あなたの要望「3人で真剣に・数字は絶対正確・書いた後に照合する確認役」を実装）：
  - **producer**＝routine `weekly-strategy-brief`（日曜18:30）：fund/tech/risk の3エージェントで起案 → **検証エージェントが全数値を `weekly-levels.json` と1つずつ照合＋compliance** → `weekly-strategy-context.json`（`verified:true/false`）。テスト実走で **verified=true・全35数値一致**を確認済（実勢価格に完全一致）。
  - **consumer**＝`auto_weekly_strategy.py`：`verified=true` かつ **鮮度60h以内**のときだけ context からシナリオ描画。無ければプレースホルダ（誤情報を出さない安全設計）。
  - **render**＝`weekly-strategy.yml`（日曜20:13、force）：routine の後に記事を強制再描画して検証済みシナリオを反映。
- **稼働**：**次の日曜(6/7)サイクルから「今週の投資戦略」が3人＋検証版で自動更新**。現6/1週記事は構築前生成のためプレースホルダのまま（月曜のforce再生成は6/8週を作る＝日付ズレになるので見送り）。
- **日付バグの真因（重要・横展開可）**：GitHub Actions は**UTC実行**。素の `datetime.now()`/`date.today()` は9hズレ（JST午前0-9時は前日）。`generate_stock_chart.py` の3箇所をJST明示に修正済。Gitコミット時刻がUTC=前日表示になるのも同根。Geminiの推測日付対策として `auto_weekly_strategy.py` のプロンプトに基準日明示＋推測日付禁止を追加済。
- **記事の発見性自動化（同セッション）**：index.html に「今週の投資戦略」自動バナー＋📰更新履歴へ自動登録（`build_weekly_strategy_banner()`/`build_weekly_history_entry()`、最新guide-weeklyを自動検出）。**週次記事は更新履歴に手動追記しない**（二重表示防止）。

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
  （※CLAUDE.mdのSYNC禁忌リストに3件すべて追記済＝2026-05-31完了）
- SYNC対象（OK）：`*.py`（compute_levels.py, email_weekly_zone.py 等）/ `.github/workflows/*.yml` / 個別 guide-*.html / guides.html / sitemap.xml / my-trades.json / memory/*.md / docs。
- 記事追加は **CLAUDE.md の8ステップ厳守**（新HTML→guidesカード→sitemap→SYNC_FILES→generate_market_news.pyの更新履歴5件キープ→sync→update-market-news の workflow_dispatch→ライブ確認）。**公開前に compliance-reviewer（Opus）監査・教育トーン・特定銘柄の買い推奨は書かない・kinsho-v1免責・9ボタンナビ**。
- ネット不調時は無限リトライせず手動 trigger 依頼（最大3-5回）。

---

## 📌 次セッションの候補・宿題

1. ✅ **Max枠の確認 完了（2026-05-31）**：routine 実行は **Maxプラン込みの「1日の含まれるルーティン実行数」枠**でカウント（追加課金なし）。**上限15回/日**、確認時 2/15 使用（fundamental-briefing 朝夕2回ぶん）。日次フル稼働でも枠に余裕大。
2. ✅ **CLAUDE.md SYNC禁忌の追記 完了（2026-05-31）**：`weekly-levels.json` / `weekly-zone-plan.md`（＋後述の内部メモ4ファイル）を正式追加。
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
