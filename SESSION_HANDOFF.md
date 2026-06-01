# 🔖 セッション引き継ぎ（最終更新: 2026-06-01）

新セッションはこのファイル＋ CLAUDE.md ＋ `memory/03_initiatives.md` を読めば文脈を復元できます。

---

## 🎯 直近セッション（5/29〜6/1）でやったこと

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
| **site-qa-lint** 🆕 | routine `trig_01Ph7pZ1WpjL8mZn7gXj5TEm` | 土曜 10:00 | `check_site_consistency.py`（リンター）を自動実行→不変条件の崩れを検査→`site-qa-report.md`（非公開） |

> 🆕 **新設 routine 計6本（5/31:4本＋6/1:weekly-strategy-brief・site-qa-lint）→ routine総数8本**（Max枠15/日に余裕）。出力JSON/mdは全て **SYNC禁忌**（routineがmain生成、ローカルpush禁止）。routine は Gmail鍵/yfinance不可（メール送信・価格計算はActions側）。

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

### A3. 保守の自動化ツール群（2026-06-01）— 「ルールが増えても破綻しない」基盤
**設計思想：人間が手で守るルールを、コードが自動で守る形へ。新ルールは"チェックを1個足す"で拡張。**

| ツール | 役割 |
|---|---|
| **`mw.py`**（司令塔CLI） | `python mw.py check / publish / sync / trigger <wf> / status [wf] / routines`。運用の単一入口 |
| **`check_site_consistency.py`**（リンター） | 不変条件を自動検査：🚨SYNC禁忌の混入（巻き戻し事故防止）／kinsho-v1免責／**ナビ9ボタン整合（生成スクリプト.pyを検査）**／SYNC_FILES登録／リンク切れ。errorで exit 1。ローカル=フル、リモート=SYNC_FILES系スキップ（環境判別） |
| **`publish_article.py`** | 記事公開の②④⑤を1コマンド・冪等（`mw publish` が内部利用）。③sitemapは自動化で不要に |
| **routine `site-qa-lint`** | 土曜10:00にリンター自動実行→`site-qa-report.md`（人が気づく前にドリフト検知。テストで実際に複数の問題を自動発見した） |

- **記事公開は `python mw.py publish --file ... --category ... --emoji ... --card-title ... --desc ...`** で ②→整合性チェック→sync→workflow起動まで一気通貫（`--dry-run`で確認）。**sync前に `python mw.py check` を習慣化**。
- **更新履歴の改修**：`generate_market_news.py` の `_history_items` リスト（`{date,line}`）を**日付降順ソート→最新5件**に自動整列。新記事はリストに1件足すだけ（週次は `build_weekly_history_item` が自動追加）。
- **sitemap.xml 全自動化**：`build_sitemap_xml` が**全 guide-*.html を自動収集**して再生成（手動追加不要）。二重管理解消のため **sitemap.xml は SYNC禁忌へ移動**。
- **ナビ崩れ修正**：`generate_monthly_report.py`/`auto_weekly_review.py`/`auto_indicator_preview.py` の旧5-6ボタンナビを9ボタンに統一（リンターのナビチェックが今後のドリフトを検知）。

### B. シグナルエンジン再設計（`SIGNAL_REDESIGN.md`）
- トップダウン4階建て（Layer0リスク環境→Layer1方向バイアス→Layer2テクニカル→Layer3ブレーキ）。
- **Phase 1 デプロイ済（記録のみ）**：`generate_technical_alerts.py` が各シグナルに `risk_regime`/`directional_bias`/`fundamental_context.bias_aligned` を記録。発火・メール挙動は不変。
- track-record.html の既定タブを **4H（本番成績≈54%）** に変更済。
- **Phase2/3 未着手**：データ蓄積後に「bias逆行を弾けば勝率改善するか」を signals-log で検証 → OKなら発火フィルタ本稼働。

### C. サイト（marketwatch-jp.com）の改善
- トップ「本日のマーケット」4カードの📰関連ニュースを **検証済みブリーフィング**（✔信頼度/🗓日付/💡コメント）に差し替え。重複していた専用「信頼性検証済みニュース」セクションは**削除**。古い順問題は published 日付の新しい順ソートで解消。
- **市場解説3記事を公開**（compliance🟢・8ステップ済）：
  - `guide-japan-strategy-2026-05.html`（攻め/守りセクター戦略）
  - `guide-bank-stocks-2026-05.html`（日銀利上げと銀行株・メガvs地銀）
  - `guide-oriental-land-2026-06.html`（**2026-06-01**：オリエンタルランド4661 暴落の5要因＋復活3シナリオ。出典付き・compliance🟢白）

### D. その他
- `SwingTrend_EA.mq4`（日足トレンド押し目＋3ATR追従）：バックテストで実データのエッジは薄く**実弾見送り**。手動の出口管理ツールとして保管。
- ユーザーの実トレードを `my-trades.json` に第7〜17号まで記録済（今週分ネット +4,165 円）。

---

## ⚠️ 絶対遵守（事故防止）

- **SYNC禁忌**（ローカルから絶対 push しない＝routine/cron/generate がGitHub側で生成）：
  6コアHTML / `signals-log.json` / `technical-alerts-history*.json` / `track-record.html` / political系 / youtube系
  / `fundamental-context.json` / `weekly-levels.json` / `weekly-zone-plan.md`
  **＋6/1追加：`sitemap.xml`（build_sitemap_xmlが全guide自動収集で再生成）/ `weekly-strategy-context.json` / `article-ideas.md` / `daily-preview.md` / `political-digest.md` / `compliance-scan.md` / `site-qa-report.md`**
  （※CLAUDE.mdのSYNC禁忌リストに全て追記済。`python mw.py check` がSYNC_FILESへの誤混入を自動検知）
- SYNC対象（OK）：`*.py`（compute_levels.py 等）/ `.github/workflows/*.yml` / 個別 guide-*.html / guides.html / `robots.txt` / my-trades.json / memory/*.md / docs。（sitemap.xml は禁忌へ移動）
- 記事追加は **`python mw.py publish`（推奨・8ステップの②④⑤を機械化）→ sync → workflow → ライブ確認**。③sitemapは自動。**公開前に compliance-reviewer（Opus）監査・教育トーン・特定銘柄の買い推奨は書かない・kinsho-v1免責・9ボタンナビ**。手動で行う場合も `mw check` でpush前点検。
- ネット不調時は無限リトライせず手動 trigger 依頼（最大3-5回）。

---

## 📌 次セッションの候補・宿題

1. 🔜 **6/7(日) weekly-strategy-brief 初回サイクルのライブ確認**：17:00 levels→18:30 routine(3人＋検証)→20:13 描画 で、6/8週の「今週の投資戦略」記事に **verified=true の正確な数字シナリオ**が載るか確認（`mw status weekly-strategy.yml` ＋ 記事ライブ）。
2. ✅ Max枠確認済（Max込み15/日・追加課金なし）／✅ SYNC禁忌・保守ツール群 構築済（5/31〜6/1）。
3. **記事ネタ（ユーザー興味ベース）**：他セクター深掘り→`mw publish` で公開（AI半導体／ディフェンシブ／高配当 等）。
4. **日本株ゾーンの週次組込**（保留中）：PBR1.0・配当利回りの床を weekly-zone-plan に追加する案。
5. **シグナル再設計 Phase2**：fundamental_context / bias_aligned のデータが貯まったら signals-log で検証。
6. **弁護士相談アジェンダ**：track-record統計開示／⭐確信度ラベル／「ソース信頼度」ラベル／セクター・個別銘柄記事の言及。
7. 🟢低優先（QA `site-qa-report.md` 由来）：古い自動生成ページ（5月 monthly-report 等）のナビは次の生成サイクルで9ボタンに更新される（過去ページのため放置可）／月次・週次レポートを guides.html に「📊 レポート」カテゴリで載せる案（03_initiatives R5）。

---

## 運用メモ
- 作業フォルダ: `C:\Users\info0\OneDrive\デスクトップ\新しいフォルダー` ／ GitHub: `invest-ai-info/marketwatch-ai`(main)
- **運用は `python mw.py <cmd>` が単一入口**（check / publish / sync / trigger / status / routines）。`mw routines` で全routineのID一覧。
- 同期は `python sync_to_github.py`（または `mw sync`）。workflow手動起動は `mw trigger <wf.yml>`（GitHub API、tokenは market-news-config.json.json）。**ローカルは UTF-8 強制が必要**：`$env:PYTHONUTF8="1"`（PowerShell）等。
- routine操作: schedule スキル → `ToolSearch select:RemoteTrigger` → RemoteTrigger（list/get/update/run）。
- ⚠️ **ローカルは GitHub と未同期なことがある**（OneDrive。core HTML / guide-weekly 等は手元に無い/古い＝正常）。真の状態は GitHub/ライブを見る。
- ユーザー方針: 「攻めと守りの両建て」「感情に左右されない自動化」「記事化するネタ＝本人の興味」。最終目標は投資家全体の底上げ／サイトSNS年収1000万／個人投資成績 年収1億。
