# 🔄 セッション引継ぎ票（最終更新: 2026-05-27 夜 — トレード分析チーム 3 人構築完了）

新セッション開始時はまず `CLAUDE.md`（全体像）→ このファイル（直近進捗）→ `memory/` 配下の 4 ファイル（01-04）を読んでください。

---

## 🛡️ セキュリティ確認結果（2026-05-27 実施）

API キー漏洩の 5 分チェックを実施し、**現状漏洩リスクは非常に低い**ことを確認:

- ✅ GitHub Secret Scanning Alert: 0 件
- ✅ リポジトリ public + Secret Scanning 自動有効
- ✅ `market-news-config.json[.json]` は GitHub に存在しない（push されていない）
- ✅ ローカルは git リポジトリではない → `git add` 誤操作リスクなし
- ✅ `sync_to_github.py` の SYNC_FILES に config を含めていない
- ✅ `.gitignore` を新規作成（将来 git init するときの保険）

### 中期的な備え（未実施、Step 2 と並行で）
- [ ] Gemini / NewsAPI / YouTube API ダッシュボードでの月次使用量チェック習慣化
- [ ] GitHub アカウント 2FA / Gmail 2FA 状態確認
- [ ] GitHub PAT が Classic か Fine-grained か確認 + 必要なら移行
- [ ] 半年に 1 回のキーローテーション（11 月にカレンダー登録）
- [ ] 万一の漏洩時の対応手順書を作成（再発行 → Secrets 更新 → ローカル更新 → API プロバイダー通知）

詳細は `memory/` か別ドキュメント化を検討。

---

## 🚀 新セッション開始用テンプレート（コピペで使用）

**運用方針**: 用途別に新セッションを始めるのが推奨（subagent はセッション起動時にのみスキャンされる）。同じ作業の 10-30 分以内の続きだけ既存セッションで OK。

### A. トレード分析・エントリー判断（3 人 subagent を使う）
```
作業フォルダ C:\Users\info0\OneDrive\デスクトップ\新しいフォルダー の続きです。
CLAUDE.md と SESSION_HANDOFF.md と memory/ を読んで現状把握してください。
今日やりたいのは: [銘柄名] のテクニカル × ファンダ分析、エントリー判断
```
→ メイン Claude が `technical-analyst` と `fundamental-analyst` を**並列起動** → 結果を `risk-manager` に統合 → 🟢/🟡/🔴 判定 + SL/TP/ロット

### B. シグナルメール改善（過去シグナル分析、アプローチ B）
```
作業フォルダ〜の続きです。CLAUDE.md と SESSION_HANDOFF.md と memory/ を読んで。
SESSION_HANDOFF の「アプローチ B」を実行してください。
3 人並列で signals-log.json (78 件、確定 20 件) を分析 → 改善案統合表で提示。
```
→ 3 人並列分析 → generate_technical_alerts.py のチューニング候補抽出 → 採用判断 → 実装

### C. サイト運営・記事執筆（subagent は使わない、メイン Claude が直接）
```
作業フォルダ〜の続きです。CLAUDE.md と SESSION_HANDOFF.md と memory/ を読んで。
今日やりたいのは: [作業内容]
（例: AMD 個別銘柄解説 第 5 弾を執筆 / 既存 guide-*.html のフッター B2 ディスクレイマー一括追加 / about.html のナビバー統一）
```
→ 8 ステップルール（CLAUDE.md 参照）に従い記事追加・修正

### 🗓 1 日の典型的なセッション運用例

```
[朝 8:00 以降] B: シグナル分析セッション
  - 朝の cron (7:27 update-market-news) 反映後に分析
  - 30-60 分で終了 → Ctrl+D

[エントリー検討時] A: トレード分析セッション
  - 「USDJPY ロング検討中、3 人で見て」
  - 5-10 分で終了 → Ctrl+D

[夜] C: サイト運営セッション（必要時）
  - 記事追加・コンプライアンス改善・ナビバー統一など
  - 1-2 時間で終了 → Ctrl+D
```

---

## 🚨 セッション開始時の最重要タスク（2026-05-27 構築直後 → 2026-05-28 以降）

**`.claude/agents/` に 3 人のトレード分析 subagent を作成済み**。仕様詳細は CLAUDE.md の「🤖 トレード分析チーム」セクション参照。

### 🥇 最優先: アプローチ B — 過去シグナル分析（シグナルメール精度 UP 用）

ユーザーは「シグナルメールの精度を上げたい」を最重要目的に指定。直近のアラート品質改善に直結。

**目的**: `signals-log.json`（78 件、確定 20 件: TP1 11/SL 8/期限切れ 1）を 3 人の subagent に分析させ、`generate_technical_alerts.py` のパラメータチューニング候補を抽出する。

**実施手順** (subagent 認識のため Claude Code 再起動後)：

1. **データ準備**: `signals-log.json` をそのまま subagent に読ませる（Read ツール）。CSV 版 `signals-log.csv` でも可
2. **3 人並列に依頼**（同一メッセージ内で Agent ツール 3 つ並列起動）:

   - **technical-analyst へ**:
     > 「signals-log.json の確定 20 件を読んで、テクニカル観点で『勝ちパターン』『負けパターン』を抽出してください。
     > 具体的に: ①TP 到達 11 件に共通するテクニカル要素（MA トレンド整合性、ATR レジーム、シグナル種別、マルチTF整合性） ②SL ヒット 8 件に共通する負け要因 ③`generate_technical_alerts.py` の `detect_signals()` / `calc_atr()` で改善できそうな閾値・フィルタ。具体的なパラメータ案 3 つ以上で。」

   - **fundamental-analyst へ**:
     > 「signals-log.json の確定 20 件を読んで、ファンダ観点で勝敗の傾向を分析してください。
     > 具体的に: ①重要指標前後 ±24h の発火は TP/SL どちらに偏ったか ②政治発言 HIGH 直近 6h の発火の傾向 ③市場休場日近接の発火の傾向 ④曜日・時間帯別の傾向。`economic-events.json` と `political-feed.json` を併読。改善案 3 つ以上で。」

   - **risk-manager へ**:
     > 「signals-log.json の確定 20 件を読んで、リスク管理観点で『取るべきだった見送り』『見送るべきだった反転検知』を抽出してください。
     > 具体的に: ①SL ヒット 8 件のうち事前の規律で防げたものはいくつか ②B2 信頼度 HIGH/MID/LOW の実勝率は仮説通りか ③現在の銘柄別クールダウン（4H=12h, 原油=24h, ドル円=18h）は妥当か ④メール件名タグや信頼度しきい値の改善案。具体的に 3 つ以上で。」

3. **3 人の結果を統合**: メイン Claude が「テクニカル / ファンダ / リスク」の改善案を表で整理 → ユーザーに採用判断を仰ぐ
4. **採用された案を `generate_technical_alerts.py` に実装** → push → 次回 cron で改善版動作
5. **2-4 週間後**: track-record で実勝率の改善を測定 → 効果があれば固定、無ければロールバック

**期待効果**: 現状の TP1+TP2 勝率 55%（11/20）を 5-10pt 改善する候補が抽出できる見込み。

### 🥈 動作テスト（軽め、上記の前後どこかで）

「動作テスト」だけしたい場合: 「USDJPY どう？テクニカル・ファンダ両方で見て、エントリーしていい？」を投げて、3 人並列 → risk-manager 統合 の挙動を確認。

期待される挙動:
- メイン Claude が `technical-analyst` と `fundamental-analyst` を**並列起動**（同一メッセージ内で Agent ツール 2 つ）
- 両者の結果テキストを `risk-manager` の prompt に埋め込んで再呼び出し
- 最終判定（🟢/🟡/🔴 + 理由 + SL/TP/ロット）を提示

うまく動かない場合: ファイル `.claude/agents/*.md` の frontmatter（特に `name:` と `description:`）を確認。Claude Code 再起動が不十分だった可能性も。

### 2026-05-27 セッション構築サマリ

- `.claude/agents/technical-analyst.md` (Sonnet, ~5KB) — チャート / シグナル / ATR / 移動平均 / RSI / MACD / BB の評価
- `.claude/agents/fundamental-analyst.md` (Sonnet, ~5KB) — 経済指標 / 決算 / 地政学 / 政治発言 / 金融政策の評価
- `.claude/agents/risk-manager.md` (**Opus**, ~6KB) — 統合判断・規律遵守の門番。SL/TP/ロット算出、金曜大引け / 環境警戒 / 反転検知のチェック、過信防止
- `sync_to_github.py` の SYNC_FILES に 3 ファイル追加
- CLAUDE.md に「🤖 トレード分析チーム」セクション追加（ワークフロー図 + 自動委譲トリガー + 設計原則 5 点）
- `claude-code-guide` で確認した重要仕様:
  - subagent はセッション起動時にスキャン、手動ファイル追加は再起動必要
  - `/agents` コマンド経由で作成すれば再起動不要
  - Bash 経由の yfinance / urllib 等は問題なく動作
  - 並列起動は 1 メッセージ内で複数 Agent ツール呼び出しで OK
  - subagent 間の連携はメインがテキストを橋渡しするパターンが推奨

---

## 🆕 2026-05-26 セッションサマリ

### 🌅 午後の作業 (3 件)
1. **YouTube 要約パーサ修正** (commit `e75a294`): Gemini が `**3行サマリー:**` のような Markdown 太字を返してパース失敗していた `503YENFXFIs` ライブ動画を修復。`parse_summary()` を Markdown 装飾耐性化 + プロンプトに「Markdown 不可」追記 + 既存壊れデータの自動修復ロジック追加（冪等）。明朝 cron で自動反映予定。
2. **CLAUDE.md にナビバー新順序反映** (commit `49577d2`): 「コアページ」セクションに political-feed.html 追加（ダッシュボード 3 ページに）、track-record を 7 タブ構成に修正、新規「ナビバー（9 ボタン、利用頻度順）」セクション追加。vix.html がナビ対象外の設計理由も明記。
3. **ライブ動画の限界について議論**: ライブ配信は Gemini video URL 方式が使えず text 方式にフォールバックするため要約品質が落ちる、という構造を共有。今回は様子見。

### 🛡️ 夜の作業：サイト法務リスク棚卸し（最重要）
全領域 A/B/C/D を実態調査して **「黒 5 件」「グレー 6 件」「白 9 件」** に整理（リスクレポート完成、当該セッション内で配信済み）。**黒 5 件全部を今晩中に修正・push 完了**：

| # | 内容 | 該当 | commit |
|---|---|---|---|
| C1 | 「ほぼ確実」→「モメンタム継続シナリオで数日内に到達余地（外部環境次第）」 | guide-nikkei-65k-break-2026-05-25 | `1ae4ec7` |
| C2 | 「オルカン一択」「これ買っとけば間違いない」→ 中立表現に | guide-nisa-ranking | `755e85c` |
| C3 | 勝率 100% 表示直下に注釈追加 + auto_weekly_review.py テンプレ修正 | guide-weekly-review-* + auto_weekly_review.py | `708c430`/`d42bbcb` |
| B1 | track-record ページ冒頭に大型免責バナー（赤枠、N<10 注意、推奨表現の意図説明） | generate_track_record_page.py | `83255f9` |
| B2 | **11 ファイル × 17 箇所**のフッターに金商法ディスクレイマー一括挿入（`data-disclaimer="kinsho-v1"` マーカーで冪等） | テンプレ 8 + 静的 3 ページ | 11 commits |

**B2 のディスクレイマー文言**: 「⚠️ 当サイトは金融商品取引業者ではなく、投資助言・代理業の登録もしていません。本サイトの情報は投資助言ではなく、投資判断はご自身の責任で行ってください。」

### ⏸ ライブ反映タイミング
- 🟢 即〜10 分: 静的 HTML（guide-* / about / privacy / contact）— GitHub Pages デプロイ
- 🟠 1 時間以内: track-record.html（technical-alerts-1h cron）、political-feed.html（political-alerts cron）
- 🟠 明朝: index / calendar / charts / vix / market-health / hot-assets（update-market-news cron）、youtube-summary.html（update-youtube-summary cron）

---

## 🎯 2026-05-27 明日の計画

### 🥇🥇 最優先（明日夜、仕事帰り後にじっくり）— トレード分析チーム 3 人の構築

**方針転換**: サイト運営の自動化から、**トレード成績向上**に軸足を明示。「ヘッジファンド最小構成」で 3 人の subagent を設計：

| Agent | 役割 | 自動委譲トリガー（description） | 許可ツール | モデル |
|---|---|---|---|---|
| **technical-analyst** | 価格・チャート・シグナル中心の分析。「今この銘柄、テクニカル的にどうか」を客観評価 | 「テクニカル分析、チャートパターン、サポート/レジスタンス、RSI/MACD/BB/MA、ATR、出来高、シグナル発火状況の評価が必要なとき」 | Read / Grep / Bash / WebFetch | Sonnet |
| **fundamental-analyst** | マクロ・経済指標・地政学・政治発言・決算中心の分析 | 「ファンダメンタル分析、経済指標、決算、地政学リスク、金融政策、政治発言、ニュース、金利・為替の方向性評価が必要なとき」 | Read / Grep / Bash / WebFetch / WebSearch | Sonnet |
| **risk-manager** | テクニカル × ファンダ意見を統合し、エントリー可否・SL/TP・ロット・規律遵守を判断。**ユーザーの規律の門番** | 「エントリー可否判定、SL/TP 設計、ポジションサイズ、ルール遵守チェック（金曜大引け、ロット 0.03、環境警戒、反転検知）、テクニカルとファンダの整合性判断が必要なとき」 | Read / Grep / Bash | Opus（精度重視） |

**配置**: `.claude/agents/*.md`（プロジェクト単位、git 共有）。`sync_to_github.py` の SYNC_FILES に `.claude/agents/technical-analyst.md` 等を追加。

**プロンプト本文の必須要素**:
- ユーザーは「サラリーマン × 4H スイング × MT4 × ロット 0.03 × 金曜大引けクローズ厳守」
- 監視銘柄 18 種（CLAUDE.md 参照）
- 「これは投資助言ではなく、参考分析」を必ず明示
- 「N=6 戦 6 勝の罠」過信防止を risk-manager に組み込む

**作業手順**:
1. claude-code-guide に subagent 仕様（agentId: a3cf434803982fb26）の続きを確認、特に「Bash 許可で yfinance を呼ぶ方法」「subagent 間の連携パターン」
2. 各 agent の .md を作成（プロンプト本文をしっかり）
3. SYNC_FILES に追加
4. CLAUDE.md に「🤖 トレード分析チーム」セクション追加
5. 動作テスト：「明日 NKD=F のロング検討中、どう思う？」を投げて 3 人並列実行 → 統合提示

**想定ワークフロー**:
```
ユーザー「明日 NKD=F でロングを検討してる」
   ↓
メイン Claude が並列で 2 人に依頼
   ├─ technical-analyst: 直近 4H/1H チャート、シグナル、ATR、相関
   └─ fundamental-analyst: 来週の経済指標、地政学、円相場、関連政治発言
   ↓
両方の結果を risk-manager に渡す
   ├─ テクニカル × ファンダの整合性
   ├─ SL/TP/ロット算出（ATR ベース）
   └─ ユーザーのルール照合（金曜大引け、環境警戒等）
   ↓
メイン Claude が「✅ 条件付き推奨」「⚠️ グレー」「❌ 見送り推奨」+ 理由を提示
   ↓
ユーザーが最終判断
```

**サイト運営系 agent は当面作らない**（記事追加・法務チェック・自動化保守はメイン Claude が直接対応）。半年運用してトレード成績が伸びたら、運営系を検討。

---

### 📅 5/30 ごろ（6/1 マンスリー初回直前）: Step 2 実装

**目的**: 敗因/勝因分析 → シグナルメール改善の半自動ループを完成させる。現状「分析しただけで終わっている」状態を、月次で改善案が自動提示される状態に。

**作業**: `generate_monthly_report.py` に「来月のパラメータ調整候補」セクションを追加

**詳細仕様**:
- データ源: `signals-log.json` の過去 30 日分、特に `loss_analysis` (SL ヒット時) と `win_analysis` (R4、TP1/TP2 到達時) フィールド
- Gemini プロンプト（上位モデル優先、品質重視）:
  ```
  以下は過去 30 日のシグナル全件と敗因/勝因分析データです。
  生で読みやすい形に集計してから、generate_technical_alerts.py の
  パラメータについて 3-5 個の具体的な調整候補を提案してください。
  対象パラメータ例:
  - ATR 倍率（SL=1.5 / TP1=2.0 / TP2=3.0）
  - B2 信頼度しきい値
  - 銘柄別クールダウン（原油 24h / ドル円 18h / その他 12h）
  - 環境警戒スコアの判定閾値（VIX 25/30、ATR 倍率 3x 等）
  - シグナル種別の重み付け（RSI/MACD/MA/BB/ブレイク）
  各提案は「現状の値 → 提案する変更 → 根拠（具体データの引用）→ 期待効果」で。
  ```
- 出力フォーマット: HTML レポート末尾に「🔧 来月のパラメータ調整候補」セクション
  - 表形式: パラメータ名 / 現状 / 提案 / 根拠 / 期待効果
  - 末尾に「※ 採用判断はユーザーが行ってください」と明示
- ユーザー採用判断 → `generate_technical_alerts.py` を直接編集 → push → 次月の cron で改善版動作
- 採用したらメモリ `memory/03_initiatives.md` か `memory/04_technical_rules.md` の「実勝率」セクションに変更履歴を残す

**実装工数**: 30-45 分（既存スクリプトに数十行追加）

**6/1 初回マンスリーレポートに間に合わせる**ため、5/30 までに push 完了。

---

### 🥇 朝（cron 反映後 30 分）
1. **ライブ反映の全 9 ページ確認**: 朝のうちに track-record の大型バナー、各ページのフッターディスクレイマー、guide-nikkei-65k-break / guide-nisa-ranking / guide-weekly-review の文言修正、youtube-summary の Markdown パース修復（`503YENFXFIs`）が反映されているかチェック
2. **D3: about / privacy / contact のナビバー旧 6 ボタン → 新 9 ボタン統一**（5/25 ナビバー最適化の漏れ）
3. **D2: about.html のデータソース更新**（Gemini AI / YouTube Data API / 政治発言 NEWS API / WhiteHouse RSS の追記、透明性向上）
4. **既存 guide-*.html 33 ファイルにフッター B2 ディスクレイマーを一括追加**（今晩の対応からスコープ外だった分。`add_disclaimer.py` を拡張して guide-*.html もターゲットに）

### 🥈 中規模（1-2 時間ずつ）
5. **B1 続き: track-record の N<10 自動マーキング**（kpi 値に N=●件を自動付与、灰色化）
6. **A1: ニュース見出しの原文併記**（generate_market_news.py のニュース表示で `（原文: ●●）` を追加）
7. **A2: 政治発言フィードの NEWS API クレジット復活**（build_political_feed_page.py で元 source 名を表示）
8. **D1: AdSense × 投資コンテンツのポリシー精査**（Google ポリシーセンターで「金融商品 / 投資勧誘」関連の制限事項を確認）

### 🥉 中長期（来週以降）
9. **弁護士相談アジェンダ確定 + IT 系弁護士 1 時間相談**（聞くべき 3 点: ①track-record の過去シグナル統計開示が無登録投資助言業か ②⭐⭐⭐ HIGH / 🟢推奨ラベルが投資勧誘表現か ③将来の note + アフィリエイト時の必要表記）
10. **関東財務局事前相談（無料）の申込**

### 🥉 既存の積み残し（5/25 セッションから継続）
11. R4 効果検証（TP1/TP2 到達シグナル発生時の AI 勝因分析動作確認）
12. 政治発言フィード WhiteHouse RSS の 4 URL のうちどれが生きているかの動作確認
13. 個別銘柄解説 第 5 弾（AMD / TSMC / SBI）
14. 6/1 マンスリーレポート初回品質チェック
15. note 開設・第 1 記事執筆

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
