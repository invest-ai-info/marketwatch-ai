# MarketWatch AI（marketwatch-jp.com）— プロジェクト全体像

**サイト目的**: 日本人投資家向けの情報収集サイト。投資家が幸福になる手助けが第一目的。

🎯 **一番の目標（2026-09-26 オーナー決定）＝シグナル研究の成績（投資の成績）を上げること**。サイトの主軸はシグナル研究＝成績が上がらなければ読者の信用を失う。作業の優先順位は「これは成績を上げるか」で決める。**大手と同じこと（速報・網羅・チャート機能）はしない**＝このサイトにしか無い記録と、日本特有の現象から新しい柱を探す（候補と手順は SESSION_HANDOFF 2026-09-26 夜（11））。検証は従来どおり「結果を見る前に事前登録→前向きで確かめる」＝成績を急いで後付けの勝ちパターンを作らない

## 作業フォルダ
- ホストパス: `C:\Users\info0\OneDrive\デスクトップ\新しいフォルダー`
- GitHub: `invest-ai-info/marketwatch-ai`（branch: main）
- 🆕 **PR のマージ（2026-09-25 オーナー決定）**: Claude がセッションで作った PR は、テスト・検査（`tests/`・`check_site_consistency.py` など）が通ったら **Claude がマージしてよい**（マージ後に何を反映したかを報告）。ただし**サイトの見た目や自動実行の動きが大きく変わるもの**は、反映の前にオーナーへ一言確認する。routine・Actions の自動生成物は従来どおり main へ直接入る（PR 不要）
- 🆕 **クラウドで頼まれたことが手元向きなら、手元のセッションへ誘導する（2026-09-26 オーナー確認）**。クラウドのセッションはオーナーの PC に触れず、手元のセッションを自動で動かす手段も無い。手元向き＝`research/`（非公開研究・DOCTRINE・`mw evolve`）／PC 内の大きなデータやキャッシュ（罠シリーズ等）／クラウドから届かないサイト（論文の出版社・bls.gov 等）／`mw discipline` など手元の取引記録の点検／手元専用の道具（`_` 始まり・本物の `sync_to_github.py`）。そのときは ①手元向きである理由を1行で伝え ②**手元のセッションにそのまま貼れる指示文**（目的・使うファイル・手順・報告してほしいこと。⚠️ **手元は git ではない**＝`auto_pull.py` が ZIP でそろえる→git コマンドは書かず、過去の版は GitHub の API で取らせる）を渡し ③クラウドでできる部分は先に進める。連携の土台＝GitHub（クラウドの成果→手元は起動時に `auto_pull.py` で自動取り込み／手元の成果→`mw sync` で GitHub へ）＋ SESSION_HANDOFF。手元のセッションの始め方＝デスクトップアプリ Code の左の一覧「新しいフォルダー」の「＋」（または入力欄の上の実行場所を「ローカル」にしてフォルダを選ぶ）

---

## 🌐 サイト構成（9 コアページ + 解説記事群）

| ページ | 役割 | 自動生成元 |
|---|---|---|
| index.html | メイン（価格・ニュース・AI 判断） | update-market-news.yml |
| calendar.html | マクロ経済カレンダー | update-market-news.yml |
| charts.html | 150年価格チャート + 投資史年表 + 歴史イベント | update-market-news.yml |
| vix.html | VIX 恐怖指数 90日 | update-market-news.yml |
| market-health.html | 市場健康度（VIX/恐怖&強欲/バフェット/CAPE） | update-market-news.yml |
| hot-assets.html | 出来高急増ランキング | update-market-news.yml |
| guides.html | 解説記事一覧 | 手動更新 |
| **track-record.html** ⭐ | 🧪 シグナル研究（旧名「シグナル成績」＝2026-09-26 にナビ・記事内のリンク文とも改名。10 タブ。🗺️ いま検証中のこと＝`research_map.py` が毎回データから組み立てる・`#map` で直リンク） | technical-alerts.yml |
| **research-list.html** 🆕 | 📋 検証中リスト（2026-10-07 オーナー）＝研究の地図と同じデータを市場ごと（🇯🇵 日本株／💱 FX／📈 株価指数・先物／🪙 金・銀・原油・BTC／🧭 共通）に並べる。`research_map.build_list_page`。**新しい前向きを足したら `collect_studies` に `cat` 付きで1件足す**。**見込みなしで止める決まり**（PREREG 同名節）＝仮説はトラッカーが毎日自動で ⏹（`status=retired`）・前向きの腕は `verified_list.RETIRED` に1行 → 検証済みリストへ。SYNC禁忌。全文は OPERATIONS.md「CLAUDE.md から移した詳しい説明」 | technical-alerts.yml（`generate_track_record_page.py`） |
| youtube-summary.html | 投資系 YouTube 要約 | update-youtube-summary.yml |
| **political-feed.html** 🆕 | 政治発言ライブフィード | political-alerts.yml |

解説記事は `guide-*.html` として個別公開（25+ 件、最新は guides.html 最上段）。

### ナビバー（10 ボタン、利用頻度順、2026-06-15 に 📖 投資本 を追加）

```
🏠 index → 🚨 political-feed → 🧪 track-record(シグナル研究・2026-09-26 に「シグナル成績」から改名) → 📅 calendar → 📚 guides → 📖 投資本(guide-investment-books)
→ 🩺 market-health → 🔥 hot-assets → 📈 charts → 📺 youtube-summary
```

- ⚠️ **vix.html はナビバー対象外**（charts / market-health / guide-vix.html 経由で到達）。10ボタンはモバイル2列×5行・375pxで崩れ無し確認済
- 🆕 **2026-09-23〜 枠の単一の真実＝`apply_site_frame.py`**（11ボタンの並び `NAV_BUTTONS`・パソコン幅6+5の2段・解説記事ヘッダーの標準形・広告の上下40px）。**update-market-news が毎回 `--all`**＝クラウドの記事レーンが崩したヘッダー/ナビも次の実行で戻る。生成スクリプト8本は `FRAME_STYLE_TAG` を import。テスト＝`_test_site_frame.py`
- ナビバー変更時は **決定論ツールで一括更新**：
  - **guide-*.html（約75本）＝ `python unify_navbar.py --apply`**（10ボタン標準を内蔵。投資本ページのみ自身を current、他は guides.html を current）
  - **生成スクリプト8本＋guides.html＋about/contact/privacy ＝ `python apply_books_nav_scripts.py --apply`**（各 `guides.html` の nav 行直後に挿入・冪等）。対象スクリプト＝`generate_market_news.py`（nav 7ブロック）／`generate_youtube_summary.py`／`generate_track_record_page.py`／`build_political_feed_page.py`／`auto_weekly_strategy.py`／`auto_weekly_review.py`／`generate_monthly_report.py`／`auto_indicator_preview.py`
- 確認: `python mw.py check`（`check_site_consistency.py` の `NAV_LINKS` は10件＝nav保持ファイルに `guide-investment-books.html` 欠落があれば warning）

---

## 🤖 自動化システム（GitHub Actions ワークフロー）

| ワークフロー | 頻度 (JST) | 役割 |
|---|---|---|
| **update-market-news.yml** | 朝 7 / 夕 16（cron は実測で1〜3時間遅延）＋**JP Stock Rankings 完了で即起動**（`workflow_run`・2026-09-17〜） | 6 コアページ + 解説生成。⚠️ `concurrency` は `cancel-in-progress: false`＝push 途中で殺されると次の run が古い土台で rebase 衝突して exit 128 になる（2026-09-17 実際に発生）。衝突時は生成物なので `-X theirs` で今回生成した側を採り3回まで再試行する |
| **technical-alerts.yml** | 4 時間ごと（6 回/日、3 重 cron） | 18 銘柄テクニカル分析 → メール |
| **technical-alerts-1h.yml** | 1 時間ごと | 1H 足データ収集（メールなし） |
| **technical-alerts-1d.yml** 🆕 | 毎朝 06:20（NY引け後） | 日足データ収集（メールなし・記録のみ。上位足=週足・クールダウン72h・expired 21日。2026-06-11新設＝時間足勾配 1h<4h<1d? の検証用） |
| **political-alerts.yml** | 30 分ごと | 政治発言フィード + HIGH 速報メール |
| **weekly-strategy.yml** | 日曜 18:13 | 来週投資戦略の自動生成 |
| **weekly-review.yml** ⭐ | 月曜 07:13 | 先週シグナル振り返り (C1) |
| **monthly-report.yml** ⭐ | 毎月 1〜3 日 09:23（取りこぼし対策で1-3日に拡張・冪等） | 先月成績レポート (C3) |
| **monthly-backup.yml** | 毎月 1〜3 日 09:10（同上・冪等） | signals-log の GitHub Release |
| **monthly-calendar-reminder.yml** | 25日 09:13 | 市場休場の自動補充＋**経済指標の生成**（`sync_economic_events.py`）＋**決算予定の更新**（`build_earnings_calendar.py`）＋来月指標のメール |
| **health-check.yml** | 12 / 20 | サイト 6 ページ HTTP・最終更新の鮮度チェック（2026-08-30〜 **経過時間**で判定＝`STALE_HOURS=26`。旧「JSTの今日と一致するか」は実行が深夜0時JSTをまたぐと必ず誤検知した） |
| **indicator-alert.yml** 🆕 | **他のワークフローの完了に相乗り**（政治発言・ティッカー・4H/1H・市況ニュース＝1日約65回）＋毎時13分の保険 | **発表の15〜120分前に「まもなく」メールを1発表1通**（`send_indicator_digest.py --mode alert --sent-file`・送った記録は actions/cache で持ち回す）。動機＝2026-09-17 の実損（19:33 に建てて 20:00 発表）。🔁 **2026-10-04 改定**＝毎時の cron は GitHub に間引かれ実際は1日4〜5回（間隔の中央値4.7時間）で、10/2 のユーロ圏HICP・米雇用統計に届かなかった（旧45〜105分の窓・試算の取りこぼし81%→新0.6%）。⚠️ 相乗り先の `name:` は一字一句合わせる（`tests/test_indicator_alert_dedup.py` と automation-health §⑭ が見張る） |
| **indicator-digest.yml** 🆕 | **routine の push に相乗り（06:13-06:20 JST）**＋cron保険 | **今日の重要指標を朝いちでメール**（`send_indicator_digest.py`）。🚨 2026-09-17 の実損が動機＝英中銀の発表27分前に建てて当日損失の約半分を出した。環境警戒スコアは**シグナルが出たときのメールの中身でしか届かない**ので、手動の発注は誰も見張っていなかった。**判断の直前ではなくポジションを持つ前に渡す**のが趣旨。件名で状態がわかる（🚨今日ある／📅7日以内／⚪無し）。読むだけでデータは書き換えない。🆕 2026-10-08〜 日本株の「寄りで買わない」目印 C・B候補の銘柄一覧の節（`jp_markers.py`＝夕方の jp-highs が同じ日足で作る `jp-highs.json` の markers・自分用のメールだけ＝サイトには出さない）。10-08夜〜 💣地雷の印・強すぎる株（`jp_momentum.py`・J42F）・今日のファンダ／決算／研究の要約（`morning_brief.py`）・通貨の強弱（`fx_strength.py`）・中国豪州の見出し（`asia_news.py`）。**平日15時前・20時前のロンドン前／NY前のメール＝`session-brief.yml`**（相乗り・`session_brief.py`） |
| **automation-health.yml** 🆕 | 09:30 | 裏方自動化の見張り番（cron/routineの沈黙の失敗を検知。Actionsは実行成否、routineは出力鮮度で判定→異常時Issue化。`check_automation_health.py`） |
| **edinet-yuho.yml** 🆕 | 平日 19:40 | 話題の企業の有報本文→`edinet-yuho.json`（company-weekly-auto の日本株用。詳細は SYNC禁忌節） |
| **verify-calendar.yml** 🆕 | 月曜 07:10 ＋ 毎月25日 07:10 | **米・英・ユーロ圏の発表日を各国の公式日程と機械で突合**（米=`verify_economic_calendar.py`／英EU=`verify_uk_eu_calendar.py`。**2本を1ステップで回す**＝片方が落ちても両方のレポートが Issue に載る）。食い違い・解析不能・比較0件のいずれでも Issue 化。🔑 **Claude セッションからは bls.gov が egress 遮断されるが Actions のランナーからは届く**＝検証はここで回す |
| **jp-rankings.yml** 🆕 | **routine の push に相乗り**（news 台帳 17:5x・sns 19:1x JST）＋cron 保険4本（16:40〜19:10 のつもりが実測 21〜23時台） | 日本株ランキング生成（`build_jp_rankings.py`→`jp-rankings.json`。詳細は下の SYNC禁忌節の同名項目）＋ 完了で **jp-highs.yml** を起動（下の行） |
| **jp-highs.yml** 🆕 | **jp-rankings の完了**（`workflow_run`） | **高値・安値の更新銘柄**（2026-10-06 オーナー依頼・東証の全上場 約3,700）＝`build_jp_highs.py`→`jp-highs.json`→hot-assets「🏔️ 高値・安値更新」。1回13〜15分・**一覧が変わったときだけ** update-market-news を起動。年初来・上場来の決め方（Yahoo の記録の始まりと JPX の上場日の確かめ）は OPERATIONS.md「CLAUDE.md から移した詳しい説明」。点検 `jp-highs-audit.yml`・テスト `tests/test_build_jp_highs.py`・鮮度は automation-health §⑫c |
| **研究ラボ・前向きの検証（約50本）** 🆕 | 手動のみ／前向きは平日・毎月 | **一覧・登録・結果＝`RESEARCH_LABS.md`**（2026-10-08 に CLAUDE.md から移した＝肥大で予約が文脈あふれで止まったため）。🚨 **新しいラボ・前向きを足したら `RESEARCH_LABS.md` に1行（CLAUDE.md には書かない）**。共通の決まり＝事前登録 `PILLAR_PREREG.md`（結果を見る前にコミット）・check（損益なし）→ run 1回・出力は GitHub 側生成＝push 禁止（SYNC禁忌）・前向きは研究の地図（`research_map.collect_studies` に `cat` 付き）・見張り番（`check_automation_health.py`）・検証済みリスト（`verified_list.SOURCES`／`MARKER_SOURCES`）に登録・値段の置き場は `jp-bars-cache.yml`（為替は `fx-bars-cache.yml`） |
| **research-lists.yml** 🆕 | 手元の記録が届いたとき（push）＋手動 | 検証済みリスト `verified-list.md` と**昇格リスト `promotion-list.md`** を記録から組み立て直す（2026-09-30 オーナー「成績の良いものは昇格リスト、悪いものは検証済みリスト…後に改善して再検証」）。M6＝ポンド円・ロンドン時間の総当たり（足3×入口32×出口64＝6,144通り）を**手元で1回ずつ**数え、判定は **`screen_judge.py`（計算より先にコミット・手元が import）**＝件数200・幅・多重検定（これまでの総数で割る）・時期・偽薬→昇格候補→MT5 の実ティック→前向き1000回。記録＝`m6-screen.json`（手元で作って送る・判定と集計だけ）。直して数え直すときは新しいラウンドを登録してから。**昇格リストはメールの昇格エッジとは別物**。事前登録＝`PILLAR_PREREG.md`「M6」・テスト `tests/test_screen_judge.py` |
| **update-youtube-summary.yml** | 朝 10 / 11 | YouTube 10 ch 要約 |
| **news-ticker.yml** | 毎時 :37 | ⚡最新ニュース・ライブフィード（`build_news_ticker.py`→`news-ticker.json`・AI不使用。詳細は SYNC禁忌節の同名項目） |

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
- **昇格エッジ限定メール**（2026-07-05）: `signal-lab-tracker.json` の status=promoted 仮説にマッチしたシグナルだけメール送信（照合=固定オラクル `signal_lab_verify.match`）。他は signals-log 記録のみ＝前向き検証は全量継続。無効化は env `EMAIL_PROMOTED_ONLY=0`。🆕 **観察中の候補メール（2026-09-26）**＝tracker の `watch=True`（tracking・edge）に当てはまる4Hシグナルは件名「👀観察中」・本文に「未確定」と登録前後の成績を付けて送る（押し目買いの2本・約2通/日。停止は `EMAIL_WATCH=0`）。照合は期間の条件を外して行う（`live_filter`）。tracker は同日から「全体との差」も昇格の条件にし、却下が決まった仮説を逆向きで自動登録する

---

## 📊 データファイル

| ファイル | 内容 |
|---|---|
| `signals-log.json` / `.csv` | 全シグナル発火履歴 + 結果（環境/通貨強弱/中国/反転/トレンド/敗因/勝因） |
| `my-trades.json` / `.csv` | ユーザーの実取引ログ |
| `technical-alerts-history*.json` | クールダウン管理（4H / 1H） |
| `economic-events.json` | 重要指標カレンダー + 市場休場（東証2028・米英2027まで） |
| `political-feed.json` | 政治発言フィード（30 分更新） |
| `youtube-summary-data.json` | YouTube 要約データ |

---

## 🤖 Claude Code の subagent（2つのチーム・全文は OPERATIONS.md「CLAUDE.md から移した詳しい説明」）

| チーム | Agent（`.claude/agents/*.md`） | 流れ |
|---|---|---|
| **トレード分析**（2026-05-27・成績向上の意思決定支援） | technical-analyst・fundamental-analyst（Sonnet）／**risk-manager**（Opus・規律の門番＝金曜大引け・環境警戒 D・反転検知ありは無条件見送り） | テクニカルとファンダを**同じメッセージで並列**→ 結果をテキストで risk-manager へ（🟢／🟡／🔴＋SL/TP/ロット）→ ユーザーが最終判断 |
| **サイト運営**（2026-05-28・品質向上） | content-writer・seo-ux-strategist（Sonnet）／**compliance-reviewer**（Opus・黒/グレー/白） | 執筆と SEO を並列 → compliance-reviewer → **8ステップ**で公開 |

- 投資助言ではなく参考分析・情報提供（出力に明記）／agent の出力はサイトに公開しない／agent どうしは直接話さない（メインがテキストで橋渡し）
- ⚠️ 自動委譲のトリガー語は各 agent の `description` が唯一の真実＝**ここに書き写さない**

---

## 🔄 SYNC_FILES の禁忌（重要・事故防止）

**原則**：cron・Actions・予約エージェント（routine）が GitHub 側で作ってコミットするファイルは、**手元から push しない**（古い版で上書きするとライブのページが過去に巻き戻る＝2026-04-24 の事故）。**正しい一覧と検査は `check_site_consistency.py` の `SYNC_FORBIDDEN`**（`mw check` が混入を error で止める）。どの routine／Actions が何をいつ書くか・経緯の全文は **`OPERATIONS.md`「SYNC_FILES の禁忌」**（2026-10-08 に CLAUDE.md から移した＝上限 32KB を超えて予約が文脈あふれで止まったため）。HTML をすぐ反映したいときは Actions の "Run workflow"。

- **主な禁忌**：`research/` 配下まるごと（手元専用・ディレクトリ単位で止まる）／6コア HTML・`sitemap.xml`／`signals-log.json`・`technical-alerts-history*.json`・`track-record.html`・`research-list.html`／`political-feed.*`・`youtube-summary*`／`fundamental-context.json`・`weekly-levels.json`・`weekly-zone-plan.md`・`weekly-strategy-context.json`・`indicator-result.json`／routine のメモ（`article-ideas.md`・`daily-preview.md`・`political-digest.md`・`compliance-scan.md`・`site-qa-report.md`・`my-trade-review.md`・`panic-scan.md`）／`drafts/` の下書き・台帳・`drafts/sns/`・`drafts/idea-inbox.md`（例外＝人が書く手順書 `drafts/*_GUIDE.md`・`drafts/idea-tested-slugs.txt` は SYNC 入り）／`signal-lab-ledger.md`・`signal-lab-tracker.json`／`guide-new-books.html`／`news-ticker.json`・`edinet-yuho.json`・`jp-rankings.json`・`jp-highs.json`／研究ラボの出力（`*-lab.*`・`*-forward.*`・`signal-env-profile*`・`verified-list.md`・`promotion-list.md`＝前向きの判定の履歴を持つ）
- **SYNC に入れるもの**：Python・`.github/workflows/*.yml`・個別 `guide-*.html`・`economic-events.json`・`my-trades.json`・`jp-stock-info.json`・`.claude/agents/*.md`・ドキュメント（CLAUDE.md・SESSION_HANDOFF.md・RESEARCH_LABS.md・OPERATIONS.md・memory/*.md）
- **routine の中身と絶対条件**（signal-lab-daily の自動公開ゲート・news-daily-auto・autodraft・シリーズの自動公開レーン〔tse・company・entry・scam〕・sns・book-watch など）は、それぞれの手順書（`SIGNAL_LAB_SOP.md`・`drafts/*_GUIDE.md`）と `OPERATIONS.md`。🚨 **レーンを増やしたら `check_automation_health.py` の `QUEUE_LANES` に登録し、guides.html に `data-category` の欄を先に作る**（畳んだら解除）。🚨 **固定の検査（`signal_lab_verify.py`・`check_guide_draft.py`・`check_plain_japanese.py`・`exit_lab_verify.py`）は誰も編集しない**
- **robots.txt**：手で直しても消える＝`generate_market_news.py` の `build_robots_txt()` に書く。遮断＝`/drafts/`・`/memory/`・`/*.md$`。⚠️ 非公開化ではない（`raw.githubusercontent.com` からは見える）

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
3. ~~`sitemap.xml` に `<url>` ブロック追加~~ → **不要**（`build_sitemap_xml` が自動再生成・SYNC禁忌）
4. `sync_to_github.py` の `SYNC_FILES` に新 HTML を追加
5. `generate_market_news.py` の「📰 更新履歴」＝`build_html()` 内の **`_history_items` リスト**（`{"date","line"}`）に **1件追加するだけ**（`date` は `YYYY-MM-DD`。日付降順ソート＋最新5件キープは描画側が自動＝手で削らない。⚠️旧記述「push out 方式」「`<br>` 調整」は誤り＝2026-07-28 訂正）
   - ⚠️ **週次戦略記事（`guide-weekly-*.html`）は手動追記しない**：`build_weekly_history_item()` が自動検出してリストに加える（index.html のバナーも自動）。手で足すと二重になる
6. `sync_to_github.py` 実行で push
7. GitHub Actions の `Update Market News` を `workflow_dispatch` で手動起動 → index.html 再生成
8. ライブ反映確認（HTTP 200、更新履歴の表示、guides.html での表示）

⚠️ 速報系記事は書く前に **「日付の事実確認」を WebSearch で実施** すること。

---

## 🛠️ 保守ツール / 運用CLI（2026-06-01 新設）

**設計思想：「人が手で守る」を「コードが自動で守る」に置き換える。新ルールはチェックを1個足す形で拡張する。** 各ツールの詳しい中身と経緯の全文は **`OPERATIONS.md`「保守ツール」**（2026-10-08 に移した）。

| ツール | ひとことで |
|---|---|
| **`mw.py`** | 司令塔 CLI（`check / publish / sync / trigger <wf> / status [wf] / routines`） |
| **`check_site_consistency.py`** | サイトの決まりの検査（SYNC禁忌の混入・公開保留の記事・連番・免責 kinsho-v1・ナビ・登録漏れ・リンク切れ）。error で exit 1。**新ルールはここに足す** |
| **`publish_article.py`** | 記事公開の②〜⑤を1コマンド・冪等（上書き・置き場所・カテゴリのゲート付き） |
| **`apply_site_frame.py`**／**`apply_logo.py`**／**`apply_series_nav.py`** | サイト共通の枠・ロゴ・シリーズの前後リンクを冪等に敷く（前後リンクは手で書かない） |
| **`inject_ads.py`** | 広告を記事末に冪等注入（選ばれた1つだけ描画・「広告」ラベル必須・推奨文を足さない） |
| **`sync_economic_events.py`**／**`verify_economic_calendar.py`**／**`verify_uk_eu_calendar.py`** | 指標カレンダーの生成（`RULES` に無い指標は警告が鳴らない）と一次情報との突合（曜日ルールは足さない） |
| **`check_plain_japanese.py`** | 研究日誌の「やさしい日本語」検査（固定・編集禁止） |
| **`auto_pull.py`**／**`_reconcile.py`** | 手元を GitHub の最新にそろえる／手元と本番の差を向き付きで出す（手元専用） |
| **`style_diagnosis.py`** | 投資スタイル診断（口座履歴は入力も出力も `research/` の下だけ） |
| **routine `site-qa-lint`**／**`failure-mail-patrol`** | 整合性チェックの定期実行／毎朝 08:57 の失敗した実行の見回り（手順書 `drafts/FAILURE_PATROL_GUIDE.md`） |
| **自動売買 AT1〜AT4・LP ドル円5分足の繰り返し** | ⏸️ 2026-10-01 夜から保留（`RESEARCH_LABS.md`）。EA は手元の `research/ea/` だけ |
| **`_doctrine_check.py`＋`mw evolve`** | 研究の進化ループの番人（手元専用・固定オラクル） |

- **記事公開は `python mw.py publish --file ... --category ... --emoji ... --card-title ... --desc ...`**／**sync の前に `python mw.py check`**
- 手元のセッションは起動時の `[auto_pull]` の行を見て、「まだ GitHub に送っていないファイル」があればほかの作業の前に片付ける（両方で変更＝統合してから sync・`--force` で押し切らない）

---

## ⚡ トークン効率ルール（2026-07-02 新設・Claude セッションの作業規律）

**目的＝毎セッションの固定オーバーヘッドと無駄な読み書きを最小化**（監視は `mw declutter` が自動）。

1. **文書サイズ予算（超過は declutter_audit が警告）**: CLAUDE.md ≤32KB / SESSION_HANDOFF.md ≤30KB / MEMORY.md ≤4KB。完了した ✅セクションは SESSION_ARCHIVE.md へ退避。memory 索引は1行/件、詳細は各ファイル側へ
2. **ファイルはまず Grep・部分 Read（offset/limit）**。全文 Read は編集対象ファイルのみ。読んだファイルの再 Read 禁止
3. **コマンド出力は絞る**: `| tail` / `| grep` で要点のみ。大きい JSON/CSV は Python で集計値だけ print（生ダンプ禁止）
4. **サブエージェント委任は3条件のみ**: ①5ファイル超の横断調査 ②独立監査（コンプラ/品質＝Opus 必須） ③本文が長大な執筆。単発の調査・数行の確認は自分で Grep。機械的作業のモデルは sonnet で足りる
5. **検証結果は再実行せず引用**: 済んだ検証の数値は SESSION_HANDOFF / auto-memory から引く（同じスイープ・同じ集計を回し直さない）
6. **独立ツール呼び出しは1メッセージに並列**でまとめる

---

## 🕐 GitHub Actions の cron は当てにならない（2026-09-17 実測）

**実測**（2026-09-17）：automation-health は中央値 +221分・jp-rankings は約 +5時間・毎時の news-ticker でも +34分（表は OPERATIONS.md「CLAUDE.md から移した詳しい説明」）。

🔑 **区切りの良い時刻（:00 / :30）ほど遅い。半端な分にすると短くなる**（このリポジトリが 07:13 / 09:23 / 11:37 のような時刻を使っているのはそのため）。
🔑 **時刻の精度が要るものは cron に頼らない**。使える手は2つ:
1. **予約エージェント(routine)の push に相乗りする**＝routine は定刻に近い（`fundamental-context.json` の朝コミットは実測16件中14件が 06:13〜06:20 JST）。🚨 **ただし相乗りできるのは routine の push だけ**＝Actions が `GITHUB_TOKEN` で押したコミットはワークフローを起動しない。実例: update-market-news の `jp-rankings.json` パス指定は**一度も発火していなかった**（push起動100件中0件）。→ **2026-09-17 に `workflow_run` へ繋ぎ替え済み**（相手の `name:` と一字一句合わせる／`conclusion == 'success'` に限定）。⚠️ **書いたつもりの繋ぎが黙って死ぬ**のが今回の教訓なので、`check_automation_health.py` §⑭ が「workflow_run 起動が直近3日にあるか」を見張る。
2. **cron を複数本に増やして最初に当たったものを使う**（update-market-news が7:27/7:57/8:27/8:57 と4本置いているのはこの考え方）。重複送信の防止が要る場合は`actions/cache` を日付キーで使う（リポジトリに書かないので他を起こさない）。

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
- `QUALITY_RUBRIC.md` — 記事「中身」品質ルーブリック（自動公開ゲートの品質レーン・単一ソース）。公開ゲートの順序＝決定論コード緑→Opusコンプラ白→品質ルーブリック→公開。news/signal-lab の各SOPから参照。基準変更はこの1ファイルだけ直す

**月初（1-3 日）のセッション開始時は必ず**:
- マンスリーレポートを読み、`02_evolution.md` の方針更新を提案
- 完了した検証項目を `03_initiatives.md` から「検証完了」へ移動
