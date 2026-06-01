# MarketWatch AI（marketwatch-jp.com）— プロジェクト全体像

**サイト目的**: 日本人投資家向けの情報収集サイト。投資家が幸福になる手助けが第一目的。

## 作業フォルダ
- ホストパス: `C:\Users\info0\OneDrive\デスクトップ\新しいフォルダー`
- GitHub: `invest-ai-info/marketwatch-ai`（branch: main）

---

## 🌐 サイト構成（9 コアページ + 解説記事群）

| ページ | 役割 | 自動生成元 |
|---|---|---|
| index.html | メイン（価格・ニュース・AI 判断） | update-market-news.yml |
| calendar.html | マクロ経済カレンダー | update-market-news.yml |
| charts.html | 50年価格チャート + 歴史イベント | update-market-news.yml |
| vix.html | VIX 恐怖指数 90日 | update-market-news.yml |
| market-health.html | 市場健康度（VIX/恐怖&強欲/バフェット/CAPE） | update-market-news.yml |
| hot-assets.html | 出来高急増ランキング | update-market-news.yml |
| guides.html | 解説記事一覧 | 手動更新 |
| **track-record.html** ⭐ | シグナル成績ダッシュボード（7 タブ） | technical-alerts.yml |
| youtube-summary.html | 投資系 YouTube 要約 | update-youtube-summary.yml |
| **political-feed.html** 🆕 | 政治発言ライブフィード | political-alerts.yml |

解説記事は `guide-*.html` として個別公開（25+ 件、最新は guides.html 最上段）。

### ナビバー（9 ボタン、利用頻度順、2026-05-25 最適化）

```
🏠 index → 🚨 political-feed → 📊 track-record → 📅 calendar → 📚 guides
→ 🩺 market-health → 🔥 hot-assets → 📈 charts → 📺 youtube-summary
```

- ⚠️ **vix.html はナビバー対象外**（charts / market-health / guide-vix.html 経由で到達。10 ボタンになるとモバイル 2×N グリッドが崩れる設計判断）
- ナビバー変更時は **ソース 13 ファイルを一括更新**（`generate_market_news.py`、`generate_youtube_summary.py`、`generate_track_record_page.py`、`build_political_feed_page.py`、`auto_weekly_*.py`、`generate_monthly_report.py`、`guides.html` + 後発 guide-*.html）
- 確認: `grep -l "political-feed.html.*政治発言ライブ" *.py *.html` で 13 件出れば OK

---

## 🤖 自動化システム（GitHub Actions ワークフロー）

| ワークフロー | 頻度 (JST) | 役割 |
|---|---|---|
| **update-market-news.yml** | 朝 7 / 夕 16（30-90 分遅延） | 6 コアページ + 解説生成 |
| **technical-alerts.yml** | 4 時間ごと（6 回/日、3 重 cron） | 13 銘柄テクニカル分析 → メール |
| **technical-alerts-1h.yml** | 1 時間ごと | 1H 足データ収集（メールなし） |
| **political-alerts.yml** | 30 分ごと | 政治発言フィード + HIGH 速報メール |
| **weekly-strategy.yml** | 日曜 18:13 | 来週投資戦略の自動生成 |
| **weekly-review.yml** ⭐ | 月曜 07:13 | 先週シグナル振り返り (C1) |
| **monthly-report.yml** ⭐ | 毎月 1 日 09:23 | 先月成績レポート (C3) |
| **monthly-calendar-reminder.yml** | 毎月 25 日 09:13 | 翌月指標リマインダー + 休場補充 |
| **monthly-backup.yml** | 毎月 1 日 09:10 | signals-log の GitHub Release |
| **health-check.yml** | 12 / 20 | サイト 6 ページ HTTP・最終更新日付チェック |
| **update-youtube-summary.yml** | 朝 10 / 11 | YouTube 10 ch 要約 |

### 環境変数 / GitHub Secrets
- `NEWSAPI_KEY`、`GEMINI_API_KEY`（Tier 1 課金）、`YOUTUBE_API_KEY`
- `GMAIL_USER` / `GMAIL_APP_PASSWORD` / `ALERT_RECIPIENT`（メール送信）
- `MY_TRADES_CSV_URL`（Google フォーム連携、オプション）
- `GITHUB_ACTIONS_RUN=true`（API 経由アップロード抑制、git push に委譲）

---

## 🚨 テクニカルアラート（核機能・概要）

### 監視銘柄 18 種
```
コモディティ:  GC=F (金), SI=F (銀), CL=F (原油)
指数:         NKD=F (日経CME), ES=F (S&P500), NQ=F (Nasdaq), YM=F (ダウ), ^FTSE
暗号:         BTC-USD
FX (JPY):     USDJPY, EURJPY, GBPJPY, AUDJPY
FX (USD):     EURUSD, GBPUSD
FX (AUD):     AUDUSD, EURAUD, GBPAUD
```

### ポジションプラン（ATR ベース、固定値）
- **SL** = エントリー ± ATR × 1.5
- **TP1** = エントリー ± ATR × 2.0（R:R 1:1.33）
- **TP2** = エントリー ± ATR × 3.0（R:R 1:2.0）

### 主要機能名（詳細ルールは `memory/04_technical_rules.md` 参照）
- シグナル検出: RSI / MACD / 移動平均 MA25-75 / ボリンジャー±2σ / 高値安値ブレイク
- **環境警戒スコア A〜D**（重要指標 / VIX / ATR レジーム / 危機キーワード / 市場休場）
- **通貨強弱マトリクス**（USD/EUR/GBP/JPY/AUD 9 ペアから算出、CS-5 閾値 ±0.05）
- **AUD ペア中国フォーカス**（上海・ハンセン連動、Gemini プロンプト調整）
- **往復ビンタ防止**（12h 反転検知、risk-manager は無条件見送り）
- **マルチタイムフレーム整合性**（1H↔4H↔日足、件名タグ ✅/⚠️）
- **B2 信頼度スコア**（HIGH/MID/LOW、HIGH のみ参照）
- **AI 敗因分析 + R4 勝因分析**（SL/TP ヒット時 Gemini 5 カテゴリ）
- **銘柄別クールダウン**（原油 24h / ドル円 18h / その他 12h、1H は一律 4h）

---

## 📊 データファイル

| ファイル | 内容 |
|---|---|
| `signals-log.json` / `.csv` | 全シグナル発火履歴 + 結果（環境/通貨強弱/中国/反転/トレンド/敗因/勝因） |
| `my-trades.json` / `.csv` | ユーザーの実取引ログ |
| `technical-alerts-history*.json` | クールダウン管理（4H / 1H） |
| `economic-events.json` | 重要指標カレンダー + 市場休場 77 件（2026-2027 完全カバー） |
| `political-feed.json` | 政治発言フィード（30 分更新） |
| `youtube-summary-data.json` | YouTube 要約データ |

---

## 🤖 トレード分析チーム（Claude Code カスタム subagent、2026-05-27 構築）

**目的**: トレード成績向上のため、テクニカル × ファンダ × リスク管理の 3 視点で意思決定を支援。サイト運営の自動化とは別目的の組織。

| Agent | 配置 | 役割 | モデル |
|---|---|---|---|
| **technical-analyst** | `.claude/agents/technical-analyst.md` | チャート / シグナル / ATR / RSI / MACD / BB / MA / 出来高 | Sonnet |
| **fundamental-analyst** | `.claude/agents/fundamental-analyst.md` | 経済指標 / 決算 / 地政学 / 政治発言 / 金融政策 | Sonnet |
| **risk-manager** ⭐ | `.claude/agents/risk-manager.md` | 統合判断・規律遵守の門番。SL/TP/ロット算出、過信防止 | **Opus** |

### 想定ワークフロー

```
ユーザー「明日 NKD=F でロングを検討してる」
   ↓
メイン Claude が並列で 2 人に依頼（同一メッセージ内で Agent ツール 2 つ）
   ├─ technical-analyst: チャート、シグナル、ATR、マルチ TF
   └─ fundamental-analyst: 来週の指標、地政学、関連政治発言
   ↓
両方の結果を risk-manager の prompt に埋め込んで統合判断
   ↓
「🟢 ✅ 条件成立 / 🟡 ⚠️ グレー / 🔴 ❌ 見送り推奨」+ SL/TP/ロット
   ↓
ユーザーが最終判断
```

### 自動委譲のトリガー（description ベース）
- 「チャート」「テクニカル」「シグナル」「ATR」 → technical-analyst
- 「FOMC」「決算」「ファンダ」「地政学」「マクロ」 → fundamental-analyst
- 「エントリーしていい？」「SL どこ」「リスク的にどう」 → risk-manager
- 明示呼び出し例: 「risk-manager に聞いて、今 GC=F に入っていい？」

### 設計原則
1. **投資助言ではなく参考分析** — 各 agent は出力に必ず明記
2. **N=6 戦 6 勝の罠に注意** — 直近実績は小サンプル、risk-manager が過信を抑える
3. **規律の門番は妥協しない** — 金曜大引け・環境警戒 D・反転検知ありは無条件見送り
4. **サイト公開しない** — agent 出力はユーザー個人向け（無登録投資助言業リスク回避）
5. **連携はテキスト経由** — メインがテキストを橋渡し（subagent 間の直接通信なし）

---

## 🌐 サイト運営チーム（Claude Code カスタム subagent、2026-05-28 構築）

**目的**: marketwatch-jp.com のクオリティ向上。記事執筆・法務監査・SEO/UX の 3 観点で並列に動かし、サイト規模拡大と検索流入増を加速させる。

| Agent | 配置 | 役割 | モデル |
|---|---|---|---|
| **content-writer** | `.claude/agents/content-writer.md` | 解説記事の執筆・編集、個別銘柄解説、速報記事、見出し作成 | Sonnet |
| **compliance-reviewer** ⭐ | `.claude/agents/compliance-reviewer.md` | 法務監査（金商法・景表法・AdSense）、無登録投資助言業リスク判定、黒/グレー/白 3 段階評価 | **Opus** |
| **seo-ux-strategist** | `.claude/agents/seo-ux-strategist.md` | SEO（メタタグ・構造化データ・sitemap）、ナビバー・内部リンク、Core Web Vitals、モバイル最適化 | Sonnet |

### 想定ワークフロー

```
ユーザー「AMD 個別銘柄解説 第 5 弾を書きたい」
   ↓
メイン Claude が並列で 2 人に依頼（同一メッセージ内で Agent ツール 2 つ）
   ├─ content-writer: 記事構成・本文ドラフト（NVIDIA/SBG 等のトーンを踏襲）
   └─ seo-ux-strategist: タイトル/メタ/見出し最適化、構造化データ、内部リンク提案
   ↓
両方の結果を compliance-reviewer に渡す（テキスト橋渡し）
   ├─ 断定表現チェック（「ほぼ確実」「一択」等）
   ├─ 個別銘柄推奨に該当しないか
   └─ 黒/グレー/白 判定 + 修正案
   ↓
メイン Claude が統合 → 8 ステップルール（記事追加）で公開
```

### 自動委譲のトリガー（description ベース）
- 「記事」「解説」「ドラフト」「書いて」「執筆」「速報」「リライト」 → content-writer
- 「法的に」「コンプラ」「金商法」「景表法」「ディスクレイマー」「免責」「投資助言」 → compliance-reviewer
- 「SEO」「メタタグ」「サイトマップ」「内部リンク」「ナビバー」「モバイル」「構造化データ」 → seo-ux-strategist
- 明示呼び出し例: 「compliance-reviewer に新記事 AMD を事前チェック頼んで」

### 設計原則
1. **投資助言ではなく情報提供** — content-writer は断定表現を避ける、compliance-reviewer が事後監査
2. **黒/グレー/白の 3 段階評価** — compliance-reviewer は曖昧な「リスクあり」ではなく明確な判定
3. **SEO はホワイトハットのみ** — リンクファーム・隠しテキスト等は禁止
4. **8 ステップルール厳守** — 新記事追加時は必ず CLAUDE.md の 8 ステップに従う
5. **触ってはいけないファイルを認識** — 6 コア HTML + political-feed.html + track-record.html 等は cron 管理

---

## 🔄 SYNC_FILES の禁忌（重要・事故防止）

### ⚠️ 絶対に SYNC_FILES に含めないファイル

- **HTML 6 コアページ**: `index.html` / `calendar.html` / `charts.html` / `vix.html` / `market-health.html` / `hot-assets.html`
- **SEO 自動生成（2026-06-01 追加）**: `sitemap.xml`（`generate_market_news.py` の `build_sitemap_xml` が**全 guide-*.html を自動収集**して再生成、update-market-news が commit）。ローカルから push すると再生成版を一時的に巻き戻すため禁止。**記事追加時の手動 sitemap 編集も不要になった**（自動で全記事が載る）
- **workflow 管理ファイル**: `signals-log.json` / `technical-alerts-history*.json` / `track-record.html`
- **political 系**: `political-feed.html` / `political-feed.json`
- **YouTube 系**: `youtube-summary.html` / `youtube-summary-data.json`
- **ファンダ・ブリーフィング**: `fundamental-context.json`（予約エージェント routine `fundamental-briefing` が 1日2回 GitHub 側で生成・コミット。`generate_technical_alerts.py` と `generate_market_news.py` が読む。ローカルから push すると routine の最新版を巻き戻すため禁止）
- **週次ゾーン系**: `weekly-levels.json`（Actions `weekly-levels.yml` が日曜 17:00 JST に `compute_levels.py` で生成）/ `weekly-zone-plan.md`（予約エージェント routine `weekly-zone-plan` が日曜 20:00 JST に生成、`weekly-zone-email.yml` がメール配信元として読む）。**どちらも GitHub 側で生成・コミットされるため、ローカルから push すると最新版を巻き戻す（fundamental-context.json と同じ事故）**
- **内部メモ系（2026-05-31 追加の routine 出力、いずれも非公開・GitHub 側で生成）**: `article-ideas.md`（routine `article-idea-scout`、毎日 07:30 JST、記事ネタ候補）/ `daily-preview.md`（routine `daily-market-preview`、毎日 21:00 JST、翌日の指標プレビュー）/ `political-digest.md`（routine `political-digest`、毎日 22:00 JST、政治発言要約）/ `compliance-scan.md`（routine `compliance-patrol`、日曜 09:00 JST、公開記事の法務巡回）。**4 件とも routine が main へコミットするため、ローカルから push 禁止**
- **週次戦略コンテキスト（2026-06-01 追加）**: `weekly-strategy-context.json`（予約エージェント routine `weekly-strategy-brief` `trig_01StownkcHrYyRbMMpVxVy2Z`、日曜 18:30 JST。fundamental/technical/risk の多エージェントで起案→検証エージェントが全数値を weekly-levels.json と照合＋compliance→`verified:true/false` 付きで生成）。`auto_weekly_strategy.py` が **verified=true のときだけ**これを読んで週次戦略記事のシナリオを描画（無ければプレースホルダ）。**routine が main へコミットするため、ローカルから push 禁止**
- **QAレポート（2026-06-01 追加）**: `site-qa-report.md`（routine `site-qa-lint` `trig_01Ph7pZ1WpjL8mZn7gXj5TEm`、土曜 10:00 JST。`check_site_consistency.py` を実行した整合性チェック結果）。**routine が main へ生成・コミットするため、ローカルから push 禁止**

**理由**: これらは cron / 予約エージェントが GitHub 側で生成・push するファイル。ローカルから push すると古いファイルで上書きされ、**ライブページが過去日付に巻き戻る事故**（実例: 2026-04-24）。

HTML を即座に反映したい場合は GitHub Actions の "Run workflow" で手動 trigger。

### SYNC_FILES に含めるもの
- Python スクリプト（`generate_*.py` など）
- GitHub Workflow（`.github/workflows/*.yml`）
- `robots.txt`, 個別 guide-*.html（※`sitemap.xml` は **SYNC禁忌へ移動**＝下記参照。generate_market_news.py が全guideを自動収集して再生成するため、ローカルから push しない）
- `economic-events.json`, `my-trades.json`
- Claude Code 設定（`.claude/agents/*.md`）
- ドキュメント（CLAUDE.md, SESSION_HANDOFF.md, memory/*.md）

---

## 📋 新記事追加の 8 ステップ（毎回必須）

> 🆕 **2026-06-01：②〜⑤は `publish_article.py` で機械化（推奨）**。手作業のミス（カード位置・sitemap・SYNC_FILES漏れ・更新履歴の件数/順序崩れ）を防ぐため、記事HTMLを書いたら次の1コマンドで②〜⑤を冪等に実行できる：
> ```
> python publish_article.py --file guide-xxx.html --category 個別銘柄解説 --emoji 🏰 \
>     --card-title "カード/履歴用の短めタイトル" --desc "カード説明文"
> ```
> 日付・読了分は記事HTMLから自動抽出。`--dry-run` で変更確認。再実行しても二重化しない。実行後は ⑥sync → ⑦workflow → ⑧確認。以下は中身の参考（手動でやる場合）:

1. 新 HTML ファイル作成（既存 `guide-*.html` のデザインを踏襲）
2. `guides.html` の該当カテゴリに記事カードを追加（最新が最上段）
3. ~~`sitemap.xml` に `<url>` ブロック追加~~ → **不要（2026-06-01〜自動）**：`build_sitemap_xml` が全 guide-*.html を自動収集して再生成（sitemap.xml は SYNC禁忌）
4. `sync_to_github.py` の `SYNC_FILES` に新 HTML を追加
5. `generate_market_news.py` の「📰 更新履歴」に新エントリ追加
   - **常に最新 5 件キープ**（最古 1 件を削除、push out 方式）
   - 最後の行は `公開` で終わり、`<br>` を付けない
   - **2026-06-01 改修**：更新履歴は `build_html()` 内の **`_history_items` リスト**（`{"date","line"}`）で管理。新記事は **このリストに1件追加するだけ**（`date` は `YYYY-MM-DD`）。**日付降順ソート＋最新5件キープは自動**（手で削る必要なし、`<br>`の付け外しも不要）。
   - ⚠️ **週次戦略記事（`guide-weekly-*.html`）は手動追記しない**：`build_weekly_history_item()` が最新の guide-weekly を自動検出してリストに加える（同時に `build_weekly_strategy_banner()` が index.html 上部にバナーも自動生成）。手で足すと二重になる
6. `sync_to_github.py` 実行で push
7. GitHub Actions の `Update Market News` を `workflow_dispatch` で手動起動 → index.html 再生成
8. ライブ反映確認（HTTP 200、更新履歴の表示、guides.html での表示）

⚠️ 速報系記事は書く前に **「日付の事実確認」を WebSearch で実施** すること。

---

## 🛠️ 保守ツール / 運用CLI（2026-06-01 新設）

**設計思想：ルールが増えても破綻しないよう「人間が手で守る」を「コードが自動で守る」に置き換える。新ルールはチェックを1個足す形で拡張する。**

| ツール | 役割 |
|---|---|
| **`mw.py`**（司令塔CLI） | `python mw.py check / publish / sync / trigger <wf> / status [wf] / routines`。スクリプト名を覚えずに運用できる単一入口 |
| **`check_site_consistency.py`**（リンター） | サイト不変条件を自動検査：**🚨SYNC禁忌の混入（巻き戻し事故防止）**／免責 kinsho-v1／9ボタンナビ／SYNC_FILES・sitemap・guidesカード登録／リンク切れ。errorで exit 1。**新ルールはここに検査を追加** |
| **`publish_article.py`** | 記事公開の②〜⑤を1コマンド・冪等（`mw publish` が内部で使用） |
| **routine `site-qa-lint`** | 土曜10:00 JST にリンターを自動実行→`site-qa-report.md` に報告（人が気づく前に検知） |

- **記事公開は `python mw.py publish --file ... --category ... --emoji ... --card-title ... --desc ...`** で ②〜⑤→整合性チェック→sync→workflow起動まで一気通貫（`--dry-run` で確認）。
- **sync 前に `python mw.py check`** を習慣に（特に SYNC禁忌の混入を自動で止められる）。

---

## 🆘 ネットワーク不調時の運用ルール

ローカル → GitHub API が timeout する場合: **無限リトライせず、ブラウザで手動 trigger** を依頼。
- Run workflow URL: `https://github.com/invest-ai-info/marketwatch-ai/actions/workflows/<workflow-yml>`
- リトライは **最大 3〜5 回まで**

---

## 📚 関連ドキュメント・必読順序

セッション開始時に必ず読む順:

1. **CLAUDE.md**（このファイル、全体像）
2. **SESSION_HANDOFF.md**（直近進捗・次回タスク候補）
3. **memory/01_profile.md**（投資家プロファイル、固定情報、年単位更新）
4. **memory/02_evolution.md**（投資スタイル進化記録、月初更新）
5. **memory/03_initiatives.md**（進行中の検証・打ち手、週次更新）
6. **memory/04_technical_rules.md** ⭐ NEW（テクニカルアラート詳細ルール、月次見直し）

その他:
- `GEMINI_BILLING_SETUP.md` — Gemini API 課金有効化手順
- `MY_TRADES_SETUP.md` — Google フォーム連携手順

**月初（1-3 日）のセッション開始時は必ず**:
- マンスリーレポートを読み、`02_evolution.md` の方針更新を提案
- 完了した検証項目を `03_initiatives.md` から「検証完了」へ移動
