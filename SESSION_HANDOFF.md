# 🔄 セッション引継ぎ票（最終更新: 2026-05-25 深夜 — 47 タスク完了大セッション後）

新セッション開始時はまず `CLAUDE.md`（全体像）→ このファイル（直近進捗）→ `memory/` 配下の 3 ファイル を読んでください。

---

## 🌟 今、システムは何ができるか？

### 自動稼働中のワークフロー (cron スケジュール一覧)

| Workflow | 頻度 (JST) | 役割 |
|---|---|---|
| **update-market-news.yml** | 朝 7:27 / 夕 16:13 (各 +3 重 cron) | 6 コアページ HTML 自動生成 |
| **technical-alerts.yml** | 4 時間ごと (+30 分/+1 時間冗長化) | 4H シグナル検出 + メール送信 |
| **technical-alerts-1h.yml** | 1 時間ごと | 1H シグナル収集 (メールなし) |
| **political-alerts.yml** | 30 分ごと | 政治発言フィード + HIGH メール速報 |
| **weekly-strategy.yml** | 日曜 18:13 | 来週の投資戦略記事を自動生成 |
| **weekly-review.yml** | 月曜 07:13 | 先週の振り返り記事を自動生成 |
| **monthly-report.yml** | 毎月 1 日 09:23 | 月次成績レポート HTML 自動生成 |
| **monthly-calendar-reminder.yml** | 毎月 25 日 09:13 | 翌月指標リマインダーメール + 市場休場日自動補充 |
| **monthly-backup.yml** | 毎月 1 日 09:10 | GitHub Release で signals-log / my-trades zip |
| **health-check.yml** | 12 / 20 JST | サイト 6 ページの HTTP 200 確認 |
| **update-youtube-summary.yml** | 毎朝 | YouTube 10 チャンネル要約 |

### メールアラート 3 系統
1. **🚨 テクニカルアラート (4H)** — シグナル発火時、件名に信頼度⭐+休場🏖️タグ
2. **📅 経済指標リマインダー** — 毎月 25 日、翌月指標を Gemini が箇条書きで送信
3. **🚨 政治発言速報 HIGH** — 30 分ごと、Trump Truth Social 等の重要発言

### 公開サイト機能 (9 ページ + 大量の解説記事)

| ページ | 役割 |
|---|---|
| index.html | メインダッシュボード |
| calendar.html | マクロ経済カレンダー |
| charts.html | 50 年価格チャート + 歴史的イベント |
| vix.html | 恐怖指数 90 日チャート |
| market-health.html | VIX / 恐怖&強欲 / バフェット / CAPE |
| hot-assets.html | 出来高急増ランキング |
| guides.html | 解説記事一覧 |
| **🆕 political-feed.html** | 政治発言ライブフィード (30 分更新) |
| **track-record.html** | シグナル成績ダッシュボード (7 タブ) |
| youtube-summary.html | 投資系 YouTube 要約 |

### track-record.html の 7 タブ
1. 🌐 全体 / 🕓 4H / ⏱️ 1H / 📅 時間・曜日分析（+ ⏰ 時間別取引推奨）
2. 🧬 シグナル品質分析（信頼度 / 環境 / WhipSaw / マルチTF / FX 強弱）
3. **🆕 🔬 勝因・敗因分析（R4 で勝因追加、Gemini が両方を自動分析）**
4. 📥 データダウンロード

---

## 👤 ユーザー情報

### 連絡先
- メール: info0414@gmail.com（Gmail）
- GitHub: invest-ai-info/marketwatch-ai
- サイト: https://marketwatch-jp.com/

### トレードスタイル
- 🏢 サラリーマン投資家（仕事中はスマホ確認）
- 📊 4H スイング想定（1〜5 日保有）
- 💱 MT4 使用（サーバー時刻 GMT+3、日本時間 -6h ※夏時間）
- 📏 ロット 0.03 程度
- 🔒 **金曜大引け（東京 15:00 JST）で全クローズ、週末持越なし**

### Claude Code 利用
- Max プラン契約中
- 対話モード中心、2026/6/15 の料金体系変更影響なし
- 自動化スクリプトに Claude API 組込みは未実施（D2 検討中）

### Gemini API 設定
- ✅ Tier 1 (前払い) 切替済み、$10 チャージ
- 💰 月コスト想定 $1-2、予算 ¥750
- 重要レポート (週次振り返り / 月次総評 / 政治発言翻訳) は上位モデル優先

---

## 📊 取引実績 (2026-05-25 時点)

### 記録済み (my-trades.json)
| # | 銘柄 | エントリー (JST) | 決済 (JST) | P&L | 備考 |
|---|---|---|---|---|---|
| 1 | ゴールド | 5/20 07:45 @ $4,462.01 | 5/21 04:11 @ $4,560.05 | **+2.20%** | AI シグナル経由 |
| 2 | BTC-USD | 5/19 22:15 @ $76,827 | 5/22 10:49 @ $77,564 | +0.96% | MT4 #28229543、+¥11,725 |
| 3 | 日経CME | 5/21 07:22 @ ¥61,063 | 5/22 10:49 @ ¥63,015 | +3.20% | MT4 #28263396、+¥58,569 |
| 4 | 原油 | 5/21 15:57 @ $98.61 | 5/22 07:16 @ $96.76 | +1.88% | MT4 #28267616 ショート、+¥29,463 |
| 5 | 日経CME | 5/21 16:01 @ ¥61,463 | 5/22 10:49 @ ¥63,008 | +2.51% | MT4 #28267663、+¥46,359 |
| 6 | ゴールド | 5/21 16:03 @ $4,521 | 5/22 10:49 @ $4,527.60 | +0.15% | MT4 #28267698、+¥3,133 |

**通算: 6 戦 6 勝・勝率 100% / 合計 +¥149,249 (裁量分) + 第 1 号 +2.20% (AI シグナル)**

### シグナルログ累計 (2026-05-25 22:00 時点)
- signals-log.json: **78 件** (4H: 14 / 1H: 64)
- 確定 (TP/SL): **約 20 件** (TP1: 11 / SL: 8 / 期限切れ 1)
- 5/25 EURJPY 4H、GBPJPY HIGH スコア初発火など、5/25 だけで +9 件追加

---

## 📅 2026-05-25 セッション全 47 タスクサマリ

### Phase 1: 第 1 波（午前、4 タスク）
- 第 2-6 号トレード記録 (my-trades.json 5 件追加)
- WS-5 / EW-6 / CS-5 統合タブ → track-record に「🧬 シグナル品質分析」

### Phase 2: 第 2 波（午後、3 タスク）
- A1: economic-events.json に 2026/6 月分追加
- B1: Google フォーム連携の重大バグ修正 (既存上書き → マージ方式)
- A2: CS-5 強弱差閾値 ±0.1 → ±0.05

### Phase 3: 第 3 波（夕方、4 タスク）
- B2: AI 信頼度スコア機能 (⭐⭐⭐ HIGH / ⭐⭐ MID / ⭐ LOW)
- C1: 週次振り返り記事の自動下書き (`auto_weekly_review.py`)
- C2: 個別銘柄解説 第 2 弾 (トヨタ)
- C3: マンスリー成績レポート機能 (`generate_monthly_report.py`)

### Phase 4: 仕上げ（夜、2 タスク）
- R1: og:image を全テンプレに追加
- R2: メール件名タグ整理 (60 → 45 文字)

### Phase 5: 追加（夜遅く、1 タスク）
- NVIDIA 決算解説 第 3 弾 (5/20 発表 Q1 FY27、AI バブル崩壊シナリオ 5 つ)

### Phase 6: 政治発言ライブフィード（深夜、6 タスク）
- crisis_keywords 拡張、`fetch_political_news.py`、`build_political_feed_page.py`、`political-alerts.yml`、ナビバー追加、ローカルテスト

### Phase 7: 5/25 月曜（早朝〜午後）
- 3 ページのナビバー 9 ボタン統一
- 週次戦略の自動化 (`weekly-strategy.yml` 日曜 18:13 cron)
- 4H workflow cron 3 重化 (スキップ対策)
- 3 層 memory ファイル作成 (`memory/01_profile.md` / `02_evolution.md` / `03_initiatives.md`)

### Phase 8: 市場休場日機能（午後）
- H1: 主要市場休場日 年間 20 件追加 (米英日 + Global)
- H2: 休場日カテゴリ専用警告ロジック
- H3: 当日休場で env_score を 1 段階引き下げ
- H4: テスト + push

### Phase 9: 政治フィード改善 + 半自動化（午後〜夜）
- B: `generate_market_holidays.py` で 2027 年分まで先行追加（合計 77 件休場）
- A: `monthly_calendar_reminder.py` 毎月 25 日リマインダー
- P1: WhiteHouse RSS 404 対策 (4 URL 試行)
- P2: 政治発言 HIGH 件数チューニング (HIGH_COMBOS 22 個追加)

### Phase 10: 日経 65,000 突破 + 周辺機能（夜）
- 日経 65,000 円突破速報記事公開 (5/25 終値 65,158 円)
- 個別銘柄解説 第 4 弾 (SBG、NAV 40 兆円)
- C1/C3 Gemini プロンプト品質改善
- track-record に「⏰ 時間別取引推奨」セクション
- ナビバー並び順最適化 (13 ファイル、利用頻度順)

### Phase 11: 最終仕上げ（深夜）
- **R4: 成功要因分析機能** (敗因分析の対称、TP1/TP2 到達時に Gemini が勝因+再現性を分析)
- SESSION_HANDOFF 大整理 (このファイル)

### Phase 12: 個別銘柄解説にチャート挿入（深夜の追加 1 タスク）
- `generate_stock_chart.py` 新設（TradingView 埋込み + yfinance/Stooq フォールバック）
- 4 記事（NVDA / トヨタ / SBG / Kioxia）に「📈 過去 3 年のチャート」セクション追加
- 自動更新、インタラクティブ、SSL 問題回避

**累計: 48 タスク完了 / 約 105 commit / 約 21 新規ファイル**

---

## 🎯 次回作業候補 (優先度順、2026-05-25 大刷新版)

### 🥇 すぐやれる (30 分以内)
- **R4 効果の検証**: 来週、TP1/TP2 到達シグナルが出てきたら勝因分析が動作するか確認
- **政治発言フィード WhiteHouse RSS の動作確認**: 4 URL のうちどれが動いているか
- **Google Form 実セットアップ** (B1 のコード側完成済、ユーザー側 STEP 1-3)
- **CLAUDE.md にナビバー新順序を反映** (関連箇所更新)

### 🥈 中規模 (1-2 時間)
- **note 開設・第 1 記事執筆**: データ蓄積 50 件超、執筆タイミング
- **個別銘柄解説 第 5 弾**: AMD / TSMC / SBI / 半導体ファンド系
- **track-record にエクイティカーブを「実取引 vs シグナル仮想」並列表示**
- **6/1 マンスリーレポート初回品質チェック** (改善版プロンプトの効果)

### 🥉 大規模 (半日〜1 日)
- **Claude API ハイブリッド (D2)**: 勝因/敗因分析だけ Claude Haiku で品質 UP (月 +¥230 試験)
- **AI シグナル経由の準自動エントリー**: HIGH スコアシグナルを「Slack で確認 → ボタンで MT4 発注」連携
- **過去 5 年の signals 仮想バックテスト**: yfinance で過去シグナル再現 → 期待 R 検証

### 💭 検討中 (ユーザー判断待ち)
- **D3: LINE / Discord 通知** (メール以外のチャンネル)
- **D4: X API Basic ($200/月)** (政治発言を ms 単位で取得)
- **D5: アフィリエイト導線強化** (証券口座紹介)
- **D6: ナビバー 9 → 7 整理** (50 年チャート / YouTube 等をフッターへ)

### 🔬 観察中 (アクション不要)
- 政治発言フィード初日: HIGH 件数バランス、ノイズ率
- 4H 冗長 cron の効果 (5/26 朝以降)
- B2 信頼度スコアの実勝率検証 (HIGH > MID > LOW 期待)
- 6/1 weekly-review + monthly-report 初回品質
- A2 強弱差閾値の効果 (中立 → 順張り/逆張り分離)

---

## ⚠️ 注意点・既知の問題

### 重要な運用ルール
1. **HTML 6 コアファイル + political-feed.html を SYNC_FILES に絶対入れない** (workflow 管理)
2. **新記事追加は 8 ステップルール厳守** (更新履歴は常に 5 件キープ、最後の行は `<br>` なし)
3. **速報系記事を書く前に「日付の事実確認」を WebSearch で行う**
4. **ローカルの signals-log.json は触らない** (workflow が GitHub 側で管理)
5. **economic-events.json の市場休場は手動編集禁止**: `generate_market_holidays.py` が管理。重要指標のみ手動追加

### Gemini モデルチェーン
- 通常用途: `gemini-2.0-flash-lite` → `gemini-2.5-flash-lite` → `gemini-2.0-flash` (低コスト優先)
- 重要レポート (週次/月次/政治発言): `gemini-2.5-flash` → `gemini-2.0-flash` (品質優先)

### yfinance の落とし穴
- ローカル連続アクセスでレート制限される
- GitHub Actions 側は問題なく動作
- NKD=F は関連ニュースが取れないことが多い

### WhiteHouse RSS の不安定性
- presidential-actions/feed/ は 2026/5 時点で 404
- 4 URL を試行する設計、briefing-room/feed/ は確実に動く
- 政権交代でまた変わる可能性あり、定期的にチェック

---

## 🔗 重要 URL

| URL | 内容 |
|---|---|
| https://marketwatch-jp.com/ | メインサイト |
| https://marketwatch-jp.com/political-feed.html | 🆕 政治発言ライブフィード |
| https://marketwatch-jp.com/track-record.html | シグナル成績ダッシュボード |
| https://github.com/invest-ai-info/marketwatch-ai/actions | GitHub Actions ダッシュボード |
| https://github.com/invest-ai-info/marketwatch-ai/releases | 月次バックアップ Release |
| https://console.cloud.google.com/billing/budgets | Gemini API 予算管理 |

---

## 💬 新セッション開始時のテンプレ

```
作業フォルダ C:\Users\info0\OneDrive\デスクトップ\新しいフォルダー の続きです。
CLAUDE.md と SESSION_HANDOFF.md と memory/ 配下を読んで現状把握してください。
今日やりたいのは: [...]
```

---

## 🏆 達成済み機能全リスト (主要)

### 📰 サイト・コンテンツ
- [x] 6 コアページ自動更新 (朝晩 2 回)
- [x] 解説記事 30+ 件 (個別銘柄: Kioxia / トヨタ / NVIDIA / SBG)
- [x] track-record.html (7 タブ + データ DL)
- [x] political-feed.html (30 分更新)
- [x] youtube-summary.html
- [x] 週次振り返り (C1)・週次戦略 (auto_weekly_strategy)・マンスリーレポート (C3) 自動化

### 🤖 AI 機能
- [x] ニュース 15 件への AI 一言コメント
- [x] 4 アセット投資判断
- [x] AI 解説 (テクニカル + ファンダ + 通貨強弱 + 中国)
- [x] **🆕 AI 勝因分析 (R4) + AI 敗因分析 (LA、対称構成)**
- [x] ニュース見出し日本語翻訳
- [x] 政治発言の重要度判定 + 日本語コメント (Gemini)
- [x] Gemini Tier 1 課金有効化

### 🚨 テクニカルアラート
- [x] 13 銘柄監視
- [x] ATR ベース SL/TP 機械算出
- [x] 4H メール送信 (3 重 cron 化) + 1H データ収集
- [x] 銘柄別クールダウン
- [x] 環境警戒スコア A〜D + 動的ポジションサイズ
- [x] シグナル反転検知 (往復ビンタ防止)
- [x] マルチタイムフレーム整合性
- [x] 通貨強弱分析 + FX 整合性
- [x] AUD ペア中国フォーカス
- [x] 重要指標カレンダー連動 + **🆕 市場休場日連動 (env_score 引き下げ)**
- [x] **🆕 信頼度スコア (B2)**: 複数シグナル × 環境 × トレンド × 反転 × FX 強弱を統合

### 📊 データ基盤
- [x] signals-log.json (B2 confidence 含む)
- [x] my-trades.json (Form 連携バグ修正済)
- [x] CSV エクスポート (曜日・時間帯フィールド付)
- [x] 月次 GitHub Release バックアップ
- [x] 結果判定 + 勝因/敗因 AI 分析 (R4)
- [x] MFE / MAE 計算

### 📅 経済指標カレンダー (2026-2027 完全カバー)
- [x] 重要指標 17 件 (5-6 月分、以降は月末リマインダーで追加)
- [x] **🆕 市場休場日 77 件** (米 23 + 英 15 + 日 38 + Global 1)
- [x] 月次自動補充 (毎月 25 日 09:13 JST)
- [x] 月次リマインダーメール

### 🚨 政治発言ライブ
- [x] NEWS API 13 政治クエリ
- [x] WhiteHouse 公式 RSS (4 URL 試行)
- [x] 30 分間隔自動収集
- [x] 重要度判定 (HIGH/MID/LOW、コンビ判定 22 個)
- [x] HIGH 速報メール
- [x] political-feed.html リアルタイム表示

### 💡 ダッシュボード (track-record.html)
- [x] 全体 / 4H / 1H タブ
- [x] 時間・曜日・セッション・月別分析
- [x] **🆕 ⏰ 時間別取引推奨 (サラリーマン向け)**
- [x] 🧬 シグナル品質分析タブ (WS-5/EW-6/CS-5/B2 統合)
- [x] **🆕 🔬 勝因・敗因分析タブ (R4 で勝因追加)**
- [x] データダウンロードタブ

### 🧠 投資スタイル進化追跡 (memory/)
- [x] `01_profile.md`: 固定情報 (年単位更新)
- [x] `02_evolution.md`: 進化方針 (月初更新)
- [x] `03_initiatives.md`: 進行中の検証 (週次更新)

### 🛡️ 運用安定性
- [x] 4H cron 3 重化 (スキップ対策)
- [x] WhiteHouse RSS 4 URL フォールバック
- [x] import_my_trades.py マージ方式 (既存上書きバグ修正)
- [x] OG image / Twitter Card 全テンプレ対応 (R1)
- [x] メール件名コンパクト化 (R2、60→45 文字)
- [x] ナビバー利用頻度順最適化 (13 ファイル)

---

**お疲れさまでした！明日からもよろしくお願いします 🍵🌙**
