# MarketWatch AI（marketwatch-jp.com）— プロジェクト全体像

ここで作成される WEB サイトは **日本人投資家に向けた情報収集サイト**である。
日本人が理解し易く投資に有利になる情報を収集するものとする。
日本国民が投資によって幸福になる手助けをするサイトでなければならない。

## 作業フォルダ
- ホストパス: `C:\Users\info0\OneDrive\デスクトップ\新しいフォルダー`
- マウント後パス: `/sessions/<session>/mnt/新しいフォルダー/`
- GitHub: `invest-ai-info/marketwatch-ai`（branch: main）

---

## 🌐 サイト構成

### コアページ（自動生成 6 ページ + 解説 1 ページ + ダッシュボード 2 ページ）
- **index.html** — メイン（価格・ニュース・センチメント・AI 投資判断・更新履歴）
- **calendar.html** — マクロ経済カレンダー（日米欧中の重要指標）
- **charts.html** — 50年価格チャート + 歴史的イベント表
- **vix.html** — 恐怖指数（VIX）90 日チャート・AI コメント
- **market-health.html** — 市場健康度（VIX・恐怖&強欲・バフェット・CAPE・RSI）
- **hot-assets.html** — 出来高急増ランキング
- **guides.html** — 解説記事 & 速報の一覧
- **track-record.html** ⭐ — シグナル成績ダッシュボード（5 タブ構成）
- **youtube-summary.html** — 投資系 YouTube チャンネル要約

### 解説記事・速報（guide-*.html）
速報・解説 25+ 件を guide-*.html として個別公開。最新は guides.html の最上段に。

---

## 🤖 自動化システム（GitHub Actions ワークフロー）

| ワークフロー | 頻度 | 役割 |
|---|---|---|
| **update-market-news.yml** | 毎日 2 回（朝 7 / 夕 16 JST、実際は 30〜90 分遅延） | 6 コアページ + 解説生成 + 更新履歴 |
| **technical-alerts.yml** | 4 時間ごと（6 回/日） | 13 銘柄テクニカル分析 → メール送信 |
| **technical-alerts-1h.yml** | 1 時間ごと | 1H 足データ収集（メール送信なし） |
| **monthly-backup.yml** | 毎月 1 日 09:10 JST | signals-log / my-trades の Release 化 |
| **health-check.yml** | 12 / 20 JST | サイト 6 ページの HTTP 200・最終更新日付チェック |
| **update-youtube-summary.yml** | 毎朝 | YouTube 10 チャンネル要約更新 |
| **weekly-review.yml** ⭐ | 月曜 07:13 JST | 先週シグナル集計＋AI 教訓 → `guide-weekly-review-*.html`（C1） |
| **monthly-report.yml** ⭐ | 毎月 1 日 09:23 JST | 先月成績集計＋AI 総評 → `guide-monthly-report-*.html`（C3） |
| **political-alerts.yml** 🆕 | 30 分間隔 | トランプ・パウエル・WhiteHouse 等の発言を NEWS API + RSS 収集 → `political-feed.html` 更新 + HIGH 速報メール送信 |

### 環境変数 / GitHub Secrets
- `NEWSAPI_KEY` — ニュース取得
- `GEMINI_API_KEY` — AI 解説・敗因分析・翻訳（Tier 1 課金有効）
- `YOUTUBE_API_KEY` — YouTube Data API v3
- `GMAIL_USER` / `GMAIL_APP_PASSWORD` — アラートメール送信
- `ALERT_RECIPIENT` — 通知先メールアドレス
- `MY_TRADES_CSV_URL` — Google フォーム連携（オプション、未設定時はスキップ）
- `GITHUB_ACTIONS_RUN=true` — API 経由のアップロード抑制（git push に委譲）

---

## 🚨 テクニカルアラートシステム（核機能）

### 監視銘柄 13 種
```
コモディティ: GC=F (金), CL=F (原油)
指数:        NKD=F (日経 CME)
暗号:        BTC-USD
JPY ペア:    USDJPY, EURJPY, GBPJPY, AUDJPY
ドルストレート: EURUSD, GBPUSD
AUD クロス:  AUDUSD, EURAUD, GBPAUD
```

### シグナル検出（calc_atr / detect_signals）
- RSI 過売り反発 / 過買い警戒
- MACD ゴールデン / デッドクロス
- 移動平均ゴールデン / デッドクロス（MA25 vs MA75）
- ボリンジャー ±2σ タッチ・突破
- 直近 20 本 高値・安値ブレイク

### ポジションプラン算出（ATR ベース）
```
SL  = エントリー ± ATR × 1.5
TP1 = エントリー ± ATR × 2.0（R:R 1:1.3）
TP2 = エントリー ± ATR × 3.0（R:R 1:2.0）
```
※ AI に数値判断させず固定値、AI は「なぜこの水準が妥当か」のみ解説

### 銘柄別クールダウン（4H）
- 原油 24h（ニュース感応度高）
- ドル円 18h（介入リスク）
- その他 12h
- 1H ワークフローは一律 4h

### 環境警戒システム（取引推奨度 A〜D）
シグナル発火時に以下を統合判定：
- 📅 **重要指標近接**（FOMC / 雇用統計 / CPI / 日銀等、`economic-events.json`）
- 📊 **VIX レベル**（25 超で警告、30 超で禁止、24h +20% で警告）
- ⚡ **ATR レジーム**（過去 30 日平均との倍率、3x 超で取引禁止）
- 🚨 **危機キーワード**（戦争・介入・暴落等のニュース検知）

→ スコア A: 100% / B: 70% / C: 40% / D: 0%（取引非推奨）

### 通貨強弱分析（24h）
USD/EUR/GBP/JPY/AUD の総合強弱を 9 つの FX ペアから算出 → ランキング表示。
シグナル方向と整合性チェック（複合順張り / 逆張り判定）。

### AUD ペア専用 中国フォーカス
AUDJPY/AUDUSD/EURAUD/GBPAUD のシグナル発火時：
- 上海総合指数・香港ハンセン指数を自動取得
- 中国関連ニュースを優先取得
- Gemini プロンプトに「AUD は中国景気依存通貨」と明示

### 往復ビンタ防止（シグナル反転検知）
直近 12h 以内に反対方向シグナルが発火 → 🔄 反転警告。
ニュース・地政学要因による短期混乱を検知し、見送り推奨。

### マルチタイムフレーム整合性
- 1H シグナル → 4H トレンド（MA25/75）と整合確認
- 4H シグナル → 日足トレンドと整合確認
- 結果を [✅順張り] / [⚠️逆張り] タグで件名に付与

### AI 敗因分析（SL ヒット時のみ）
- VIX 変動・保有期間中ニュース・指標スナップショットを Gemini に渡す
- 5 カテゴリ分類: テクニカル悪化 / ファンダメンタル / 地政学・突発 / ボラ拡大 / シグナル品質
- 詳細解説 + 教訓を自動生成 → `loss_analysis` フィールドに保存

---

## 📊 データ蓄積・分析基盤

### データファイル（GitHub 上で永続化）
| ファイル | 内容 |
|---|---|
| `signals-log.json` | 全シグナル発火履歴（環境/通貨強弱/中国/反転/トレンド/敗因 全部含む） |
| `signals-log.csv` | 上記の CSV 版（曜日・時間帯派生フィールド付き） |
| `my-trades.json` | ユーザーの実取引ログ |
| `my-trades.csv` | 上記の CSV 版 |
| `technical-alerts-history.json` | 4H クールダウン管理 |
| `technical-alerts-history-1h.json` | 1H クールダウン管理 |
| `economic-events.json` | 重要指標カレンダー（手動メンテ、月初に当月分を追加） |

### track-record.html（5 タブ構成）
- 🌐 **全体** — 全シグナル集計
- 🕓 **4H 足** — 4H 専用統計
- ⏱️ **1H 足** — 1H 専用統計
- 📅 **時間・曜日分析** — 曜日別 / セッション別 / 月別 / 時間ヒートマップ
- 🔬 **敗因分析** — SL ヒット案件のカテゴリ別分析
- 📥 **データダウンロード** — CSV/JSON ダウンロード + pandas サンプル

### バックアップ
- 月次 GitHub Release（毎月 1 日 09:10 JST）
- Git 履歴に全コミット永続化

---

## 💼 ユーザー（運用者）情報

### 取引スタイル
- サラリーマン投資家（仕事中はスマホでチラ見運用）
- 4H スイング想定（保有 1〜5 日）
- ロット 0.03 程度
- MT4 使用（サーバー時刻 GMT+3 ≒ 日本時間 -6h ※夏時間）
- **金曜大引け（東京 15:00 JST）で全クローズ、週末持越なし**
- 中東情勢・米中対立で週末ギャップリスク回避

### 取引実績（記録済 + 未記録）
- 第 1 号: ゴールド +2.20%（5/20-5/21、AI シグナル経由、リアル記録済）
- 第 2-5 号: 5/22 大引け全クローズ済（詳細記録待ち）
- **記録時点で 5 戦 5 勝・勝率 100%**

### 将来の展望
- note 開設して「サラリーマン投資家 × AI 運用日記」発信
- 1〜2 ヶ月データ蓄積後に振り返り記事
- 法的に安全な範囲で（金商法・投資助言業の登録不要な事後報告型）
- アフィリエイト（証券口座紹介）でマネタイズ

---

## 🎨 HTML デザイン方針

- ライトテーマ基本（背景 `#ffffff`）+ ダークモードトグル（ローカルストレージ永続化）
- ダーク背景色 `#0d1117`、サブカラー `#161b22`
- アクセント: `#0969da`（青、リンク）/ `#cf222e`（赤、警告）/ `#1a7f37`（緑、確定）/ `#9a6700`（橙、注意）
- 日付・時刻は日本時間（JST）表示
- 4 カテゴリ: 株式 / 為替 / コモディティ / 暗号資産
- 全アイコンサイズ統一（1.3rem）
- 初心者メモ（🔰）を各カードに配置
- ダークモードは「明示ルール優先＋無いページは JS injection」

---

## 🔄 ローカル同期スクリプト（sync_to_github.py）のルール

### ⚠️ HTML 6 コアファイルは絶対に SYNC_FILES に含めない
理由: cron が生成する HTML をローカルから push すると、古いローカル HTML で上書きされ
ライブページが過去日付に巻き戻る（実例: 2026-04-24 早朝に発生）。

### SYNC_FILES に含めるもの
- Python スクリプト（generate_*.py, evaluate_*.py, export_*.py, import_*.py 等）
- GitHub Workflow ファイル（.github/workflows/*.yml）
- `sitemap.xml`, `robots.txt`
- 個別の解説記事・速報 HTML（guide-*.html）
- 経済イベントデータ（`economic-events.json`）
- `my-trades.json`（実取引ログ、初期空）

### SYNC_FILES に含めないもの
- `index.html` / `calendar.html` / `charts.html` / `vix.html` / `market-health.html` / `hot-assets.html`（cron 管理）
- `signals-log.json` / `technical-alerts-history*.json` / `track-record.html`（workflow 管理）
- `political-feed.html` / `political-feed.json`（political-alerts.yml が GitHub 側で更新）

HTML を即座に反映したい場合は GitHub Actions の "Run workflow" を使う。

---

## 📋 新記事を追加するときの定型手順（毎回必須・8 ステップ）

1. 新 HTML ファイル作成（既存 `guide-*.html` のデザインを踏襲）
2. `guides.html` の該当カテゴリセクションに記事カードを追加（最新が最上段）
3. `sitemap.xml` に `<url>` ブロックを追加
4. `sync_to_github.py` の `SYNC_FILES` リストに新 HTML を追加
5. `generate_market_news.py` の「📰 更新履歴」セクションに新エントリを追加
   - **常に最新 5 件キープ** — 新エントリを最上段に挿入し、最古 1 件を削除（push out 方式）
   - 一覧の最後の行は `公開` で終わり、`<br>` を付けない
6. `sync_to_github.py` 実行で GitHub に push
7. GitHub Actions の `Update Market News` を `workflow_dispatch` で手動起動 → index.html 再生成
8. ライブサイトで反映確認（URL HTTP 200、更新履歴の表示、guides.html での表示）

速報系記事を書く前に **「日付の事実確認」を WebSearch で行う** こと。

---

## 🛠️ 主要スクリプト一覧

| スクリプト | 役割 |
|---|---|
| `generate_market_news.py` | 6 コアページ生成、ニュース取得、AI 投資判断 |
| `generate_technical_alerts.py` | 13 銘柄テクニカル分析 + メール送信 |
| `evaluate_signal_outcomes.py` | シグナル結果判定 + AI 敗因分析 |
| `generate_track_record_page.py` | track-record.html 自動生成 |
| `export_to_csv.py` | signals-log/my-trades の CSV 出力 |
| `import_my_trades.py` | Google フォーム → my-trades.json 取り込み |
| `generate_youtube_summary.py` | YouTube 10 チャンネル要約 |
| `auto_weekly_strategy.py` | 週次戦略記事の自動生成（日曜18時） |
| `auto_weekly_review.py` | 週次振り返り記事の自動生成（月曜朝、C1） |
| `auto_indicator_preview.py` | 経済指標プレビュー記事の自動生成 |
| `generate_monthly_report.py` | マンスリー成績レポートの自動生成（月初、C3） |
| `fetch_political_news.py` | 政治発言フィード収集（NEWS API + WhiteHouse RSS、30 分ごと） |
| `build_political_feed_page.py` | `political-feed.html` ビルダー（30 分ごと） |
| `sync_to_github.py` | ローカル → GitHub 同期（キャッシュ付き） |
| `check_site_health.py` | health-check 異常検知 |

---

## 🆘 ネットワーク不調時の運用ルール

ローカル PC → GitHub API への接続が timeout を繰り返すケースがある。

**対応**: 無限リトライせず、ユーザーに **ブラウザでの手動 trigger** を促す。
- Run workflow URL: `https://github.com/invest-ai-info/marketwatch-ai/actions/workflows/<workflow-yml>`
- リトライは **最大 3〜5 回まで**

---

## 📚 関連ドキュメント

- `SESSION_HANDOFF.md` — 直近セッションの詳細進捗・次回タスク候補
- `GEMINI_BILLING_SETUP.md` — Gemini API 課金有効化手順
- `MY_TRADES_SETUP.md` — Google フォーム連携セットアップ手順
