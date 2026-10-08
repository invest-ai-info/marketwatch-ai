# 運用の詳しい記録（OPERATIONS.md）

2026-10-08 に CLAUDE.md から「SYNC_FILES の禁忌」と「保守ツール / 運用CLI」の2節をそのまま移した（CLAUDE.md が上限 32KB を大きく超え、すべてのセッションと予約の頭に読み込まれて、10/8 朝の signal-lab-daily が文脈あふれで止まったため）。CLAUDE.md には要点だけを残している。ここを直したら、CLAUDE.md の要点と食い違わないかも見る。

## 🔄 SYNC_FILES の禁忌（重要・事故防止）

### ⚠️ 絶対に SYNC_FILES に含めないファイル

- 🆕 **`research/` 配下は丸ごとローカル専用**（2026-07-31・非公開研究）: `check_sync_forbidden` が**ディレクトリ単位**で error 停止＝**個別登録は不要**（経緯は SESSION_HANDOFF 同日節）
- **HTML 6 コアページ**: `index.html` / `calendar.html` / `charts.html` / `vix.html` / `market-health.html` / `hot-assets.html`
- **SEO 自動生成（2026-06-01 追加）**: `sitemap.xml`（`generate_market_news.py` の `build_sitemap_xml` が**全 guide-*.html を自動収集**して再生成、update-market-news が commit）。ローカルから push すると再生成版を一時的に巻き戻すため禁止。**記事追加時の手動 sitemap 編集も不要になった**（自動で全記事が載る）
- **workflow 管理ファイル**: `signals-log.json` / `technical-alerts-history*.json` / `track-record.html`
- **political 系**: `political-feed.html` / `political-feed.json`
- **YouTube 系**: `youtube-summary.html` / `youtube-summary-data.json`
- **ファンダ・ブリーフィング**: `fundamental-context.json`（予約エージェント routine `fundamental-briefing` が 1日2回 GitHub 側で生成・コミット。`generate_technical_alerts.py` と `generate_market_news.py` が読む。ローカルから push すると routine の最新版を巻き戻すため禁止）。🆕 2026-10-08 夜 朝のメール（`morning_brief.py`）は任意の欄 `currencies`（6通貨の強い/弱い傾向）・`asia_watch`（中国・豪州の気になるニュース）があれば出す＝10/8 22:05 にオーナーが予約の指示に足した。🆕 同日夜 **ロンドン前（平日 13:30〜15:00・遅れ〜16:00）／NY前（18:30〜20:00・遅れ〜21:00）の確認メール＝`session-brief.yml`（`session_brief.py`）**：「まもなく」メールと同じ5本の完了に相乗り＋cron 保険・1日1時間帯1通（actions/cache の印）・中身＝今夜の指標と発表直後の倍率・通貨の強弱（24時間／今日の東京時間・欧州時間／約5日）・AIの通貨ごとの見立て・英欧／米国の見出し（`asia_news.py --set`）・点検表の決まりと研究の注意（`NOTES`＝結果が変わったら直す）。中身の確認は `morning-mail-preview.yml` の kind=london／ny（API で作った予約はエージェントから書き換えられない＝指示を変えるときはオーナーが https://claude.ai/code/routines/trig_01M7uY1H8uR6tEwF1CJ7jXzV で）
- **週次ゾーン系**: `weekly-levels.json`（Actions `weekly-levels.yml` が**土曜 10:17 JST（＋土曜昼・日曜朝の保険）**に `compute_levels.py` で生成。2026-10-04 に日曜17時から前倒し＝実行が毎週21〜23時台にずれ込み、日曜夕方の routine 2本に間に合わず週次戦略が4週連続 verified=false だった）/ `weekly-zone-plan.md`（予約エージェント routine `weekly-zone-plan` が日曜 20:00 JST に生成、`weekly-zone-email.yml` がメール配信元として読む）。**どちらも GitHub 側で生成・コミットされるため、ローカルから push すると最新版を巻き戻す（fundamental-context.json と同じ事故）**
- **内部メモ系（2026-05-31・非公開・GitHub側生成）**: `article-ideas.md`(routine `article-idea-scout`,毎日07:30・記事ネタ)／`daily-preview.md`(`daily-market-preview`,21:00・翌日指標)／`political-digest.md`(`political-digest`,22:00・政治要約)／`compliance-scan.md`(`compliance-patrol`,日曜09:00・法務巡回)。**4件とも routine が main へコミット＝ローカルから push 禁止**
- **週次戦略コンテキスト（2026-06-01）**: `weekly-strategy-context.json`（routine `weekly-strategy-brief` `trig_01StownkcHrYyRbMMpVxVy2Z`、日曜 18:30 JST＝多エージェント起案→検証エージェントが全数値を weekly-levels.json と照合＋compliance→`verified:true/false` 付き生成）。`auto_weekly_strategy.py` が **verified=trueのみ**読んで週次戦略記事を描画（無ければプレースホルダ）。**routine が main へコミット＝push 禁止**
- **QAレポート（2026-06-01 追加）**: `site-qa-report.md`（routine `site-qa-lint` `trig_01Ph7pZ1WpjL8mZn7gXj5TEm`、土曜 10:00 JST。`check_site_consistency.py` を実行した整合性チェック結果）。**routine が main へ生成・コミットするため、ローカルから push 禁止**
- **指標結果速報（2026-06-05 追加）**: `indicator-result.json`（routine が重要指標の発表後に WebSearch で実数値・市場反応を生成・コミット。`generate_market_news.py` の `build_indicator_preview_banner` が読み、トップの注目指標バナーを「プレビュー→結果速報」に刷り替える）。**routine が GitHub 側で生成・コミットするため、ローカルから push 禁止**（SYNC_FILES に入れない）
- **パニック反発スキャン（2026-06-03 追加）**: `panic-scan.md`（GitHub Actions `panic-scan.yml`、毎日 7:27 JST。`panic_bounce_scan.py` が非FX9資産の「投げ売り＝反発候補」を出力）。**Actions が GitHub 側で生成・コミットするため、ローカルから push 禁止**（ローカル実行時に同名ファイルができるが SYNC_FILES に入れない）。前向き検証データ蓄積用の非公開メモ
- **記事下書き＋完全自動公開（2026-06-06 下書き／07-05 無人公開化）**: `drafts/draft-*.html` / `drafts/REVIEW.md`（routine `autodraft-article` `trig_01VpreEMybEJCmFiU5TS7Vet`、毎日 05:30 JST が心理＆リスク管理シリーズ下書きを生成）＋公開routine `autodraft-publish`（毎日 08:40 JST が最古の未公開下書きを仕上げ公開）。**routine が GitHub 側で生成＝SYNC_FILES に入れない**（下書きは `noindex,nofollow`＋robots.txt `/drafts/` Disallow＝**2026-08-01 にようやく実装**。それ以前は robots.txt に Disallow が無く 78本が実際にクロール可能だった＝下記「robots.txt の Disallow」節）。公開ゲート＝`check_guide_draft.py`（固定・編集禁止＝noindex/kinsho-v1/ナビ10/TODO/売買推奨NG/SVGはみ出し）exit0 → Opusコンプラ+品質(QUALITY_RUBRIC)白（🟡軽微はOpus修正→再ゲート→独立Opus確認）→ publish_article.py＋push。🔴黒/要協議/赤は REVIEW.md に🚩エスカレ。**例外＝`AUTODRAFT_GUIDE.md`／`AUTOPUBLISH_GUIDE.md`／`BOOKWATCH_GUIDE.md`は人間編集＝SYNC入り**。手順書=`drafts/AUTOPUBLISH_GUIDE.md`
- **研究アイデア受信箱（2026-07-07）**: `drafts/idea-inbox.md`（routine `idea-scout-weekly`、毎週日曜 14:00 JST＝WebSearchで検証可能な新手法・論文を最大3件・事前登録形式で**追記のみ**・重複回避は `drafts/idea-tested-slugs.txt`(SYNC入り)と照合）。**routine が GitHub側で追記＝SYNC外**（登録済・照合basename）。ローカル進化ループ（`mw evolve`／`research/DOCTRINE.md`）の①INTAKE
- **投資本 新刊ウォッチ（2026-07-05）**: `guide-new-books.html`（routine `book-watch-weekly`、毎週土曜 11:00 JST＝WebSearchで直近30日の投資系新刊を2ソース照合→中立紹介を最新40冊まで積み上げ）。**routine が GitHub側で更新＝SYNC外**（check_site_consistency の SYNC_FORBIDDEN 登録済）。手順書=`drafts/BOOKWATCH_GUIDE.md`（SYNC入り）
- **週次トレード自己レビュー（2026-06-06）**: `my-trade-review.md`（routine `weekly-trade-review` `trig_01LgSjdK2is5m6oP7ta1mh7z`、毎週土曜 12:00 JST が `my-trades.json` を分析＝敗因/遵守度/改善点の非公開メモ）。**GitHub側生成＝SYNC外**。読む対象＝`my-trades.json`／`MY_TRADING_RULES.md`(発注前チェックリスト・SYNC入り)／`economic-events.json`。本人の自己点検
- **シグナル研究日誌・日次研究会＋自動公開（2026-06-11 / 06-13 自動公開化）**: `signal-lab-ledger.md`（台帳）/ `drafts/draft-signal-lab-*.html` / `drafts/labnotes/lab-*-analysis.md` / `drafts/labnotes/lab-*-claims.json`（routine `signal-lab-daily` `trig_01V4A37Xow1vx2QAAvYwzR57`、毎朝 06:10 JST＝NY引け後。投資3視点で勝率改善仮説を**1日1本だけ**signals-logで反実仮想検証→下書き＋labnotes＋claims.json＋台帳を生成）。**routine が GitHub 側で生成＝SYNC_FILES に入れない**。自動公開ゲート＝①`signal_lab_verify.py`（**SYNC入りの固定コード＝独立オラクル・routine/agentは編集禁止・実行前に `git checkout` で確定版へ**。claims.jsonの全k/nをsignals-logから独立再計算して突合＝捏造不可＋『30秒まとめ』%完全性＋SVG＋**未対応フィルタキーは即赤**）exit0 → ②Opusコンプラ白なら自動公開（🟡軽微はOpus自己修正[表現軟化・免責のみ・数値/SVG不変]→数値再検証→別の独立Opusが白確認／🔴黒・要協議・検証赤・未対応次元は REVIEW.md に🚩エスカレ）。filterキー＝ticker/group/direction/trend/tf/signal/signals_all(コンボ=全シグナル同時発火・2026-07-19)/reversal_long/blocked/tier/env(環境警戒A-D・2026-07-19)/regime(RISK_ON等・2026-07-19)/rsi_band・ma_pos・macd_side(指標ステート・2026-07-20)/news(注目度0/1-2/3+・Q24・2026-07-23)/regime4(Q34・2026-07-27)/fired_before・fired_from(IS/FWD期間分離・2026-08-12＝IS/FWD比較記事は期間をclaimsで宣言必須。詳細はSIGNAL_LAB_SOP)/family・adx_band・vix_band・asset_class(環境の相性ラボ regime_lab.py の候補の前向き追跡用・2026-09-26・エンジンのメール照合には未対応)/fbias(ファンダの見立てとシグナルの向き＝aligned/mismatch・signal_env_profile.py の「傾向あり」の前向き追跡用・2026-09-26・メール照合には未対応)/cs_align(通貨の強弱とシグナルの向き＝aligned/against・FX本100冊の候補の前向き追跡用・2026-09-28以降の発火のみ・2026-09-27・メール照合には未対応)。groupには拡張ユニバース5キーあり(metal_x/energy_x/rates/crypto_x/index_x=1d拡張8銘柄・Q23・2026-07-23＝既存groupと非重複・トラッカーは拡張group仮説のみ凍結迂回)。⚠️`--category`＝「AIシグナル研究日誌」(絵文字なし・🧪は--emoji)。記事番号は台帳管理。**エンジン・発火条件・固定オラクルには絶対触れない。人間の役割＝エスカレ回のレビューのみ**
- **X(SNS)投稿ドラフト（2026-06-13）**: `drafts/sns/<YYYY-MM-DD>.md`（routine `sns-post-daily` `trig_01VkDY4djA8WAAZavhgu3j4M`、毎日 07:00/19:00 JST＝cron `0 10,22 * * *` UTC・JST時刻で朝/晩出し分け。@rx009898 が手動コピペするX投稿文を生成。価格=Yahoo／地合い=fundamental-context.json／イベント=economic-events.json・280字以内・免責短縮版）。**GitHub側生成＝SYNC外**。⚠️X API自動投稿はしない（無料枠2026-02廃止＝コピペ専用）。`/drafts/` は robots.txt Disallow 済（2026-08-01〜。下記「robots.txt の Disallow」節）
- **シリーズ自動公開レーン（1日1本・キュー駆動。2026-08-31 に一覧化）**: 手順書＋題材キューは **SYNC入り（人が編集）**、台帳と記事は **GitHub側生成**。
  - ~~`proverb-daily-auto`~~ ＝投資格言。**2026-09-05 に #50「全48回 総目次」で完結し、routine は削除済み**（2026-09-10 に `list_triggers` で不在を確認）。手順書 `drafts/PROVERB_GUIDE.md`／台帳 `drafts/proverb/PROVERB_LEDGER.md`／記事 `guide-proverb-*.html` は**残す**が、**`check_automation_health.py` の `QUEUE_LANES` からは外した**（2026-09-17＝畳んだレーンを見張ると毎朝必ず赤くなり番人の信用が落ちる。**レーンを足したら登録・畳んだら解除**が対の手順）（48本は公開中・前後ナビの並びにも使う）。📌 和の相場格言は44本でほぼ汲み尽くし、2度の枯渇を経て総集編で締めた＝**キュー駆動のレーンは「畳み方」を先に決めておく**という前例
  - `tse-daily-auto` `trig_01HbSi32JHhWEhoUK2erQhJr`（毎日 11:37 JST・model=claude-sonnet-5。**2026-08-31 新設＝格言の後継**）＝東証のしくみ。手順書 `drafts/TSE_GUIDE.md`（題材18件）／台帳 `drafts/tse/TSE_LEDGER.md`／記事 `guide-tse-*.html`。🚨 **このレーンだけの絶対条件＝制度の数値は一次情報（jpx.co.jp / fsa.go.jp / e-Gov）を実際に開いて確かめ、本文に確認日を書く。届かなければ書かずにエスカレ**
  - 🔁 **`company-daily-auto` `trig_01ERd5oZBggR1LaxF6c2BXw3`（毎日 10:23 JST・エージェント作成＝プロンプトと時刻をエージェントが直せる・2026-10-04 新設）**＝毎朝、**リポジトリ付きの専用セッション `session_0193RuD1wE9JzE6VKK4pMa3U`（「📊 数字で見る企業（毎日の専用セッション）」）を起こす**型（🚨 エージェントが作る「毎回新しいセッション」型のルーティンはリポジトリも add_repo も無く動けない＝2026-10-04 に試験で確認。オーナーの画面操作なしで最後まで動かすためにこの型にした）＝オーナー指示「最低でも1日1本以上…必ず1本以上は上げてください」で週1本→**毎日1本以上**。候補が消えても書かずに終わらず `COMPANY_GUIDE.md` §2-1 の7「代わりの順」で必ず1本（§0 の禁止・中3営業日・一次情報の線は下げない）。作業は origin/main の git worktree（/tmp/co-pub）で行う。候補は `edinet-yuho.json` の `cooled: true`（中3営業日を満たす）が先頭に並ぶ（`build_edinet_yuho.pick_candidates`・旧版は話題の真っ最中の15社だけで10/3に日本株が全滅した）。番人＝LEDGER_WATCH 2日。旧 `company-weekly-auto` `trig_017X6e1WvUm2FBvyegzFkAUh`（毎週土曜 14:23 JST・オーナー作成＝エージェントからは止められない）は、手順書の先頭の指示で**次の起動時に自分を止める**
  - （旧）`company-weekly-auto` `trig_017X6e1WvUm2FBvyegzFkAUh`（**毎週土曜 14:23 JST**・model=claude-sonnet-5。**2026-08-31 新設**）＝数字で見る、話題の企業。手順書 `drafts/COMPANY_GUIDE.md`／台帳 `drafts/company/COMPANY_LEDGER.md`／記事 `guide-company-*.html`。🔑 **このレーンだけキューを持たない**＝題材を機械的に選ぶので**構造的に枯渇しない**（**日本株**＝`jp-rankings.json` で直近14日に gainers/losers/hot へ2回以上／**海外株**＝`earnings-calendar.json` の `us` で決算発表から2営業日〜14日、無ければ直近15〜60日のニュース記事で主役だった海外企業）。**台帳の最新1件と違うほうを毎週の第1候補にして日米を交互に回す**（2026-08-31 オーナー指示「海外の企業も日本株に大きく影響を与えるので記事にしてほしい」）。🆕 **既刊とかぶってもよい——むしろ「続報」にする**（同オーナー指示「前回と今回じゃ状況が違う／むしろあの後どうなったのかも気になる」）＝既刊がある会社は §1⓪「前回の記事のその後」を必須にする。🚨 **⓪で既刊から引くのは事実・数字・公開日だけ**（評価語は引用しない＝いまのゲートで禁じた表現を再生産しないため。「前回の見立てが当たった/外れた」も書かない＝的中率の主張になる）。本レーン内のローテーションだけ90日あける（大きな動きがあれば例外可）。その代わり残量では止まったことを検知できないため、`check_automation_health.py` の **`LEDGER_WATCH`（台帳の最終更新が10日超で警告）**で見張る。🚨 **絶対条件＝①目標株価を書かない ②買い/売り/保有を推奨しない ③割安・割高と断定しない ④将来を予測しない ⑤証券会社名を列挙しない ⑥急騰急落の当日・翌日に書かない**。「将来性」は結論ではなく **上がる材料／下がる材料を対で並べるだけ**（オーナー指示 2026-08-31。重み付けも結論の文も書かない）。⚠️ **ニュースレーンと題材が衝突する**（デイリーニュースも個別銘柄を扱う）ので、直近14日の `guide-news-*.html` と `NEWS_LEDGER.md` を見て同じ会社ならその週は見送る手順を両方の手順書に入れてある
  - 投資詐欺は手順書 `drafts/SCAM_GUIDE.md`／台帳 `drafts/scam/SCAM_LEDGER.md`／記事 `guide-scam-*.html`（2026-08-13 新設・格言の枯渇を受けて発足）
  - 🆕 `entry-daily-auto`（毎日 12:23 JST・2026-09-25 新設）＝エントリー方法の研究。手順書 `drafts/ENTRY_GUIDE.md`（題材26件・SYNC入り）／台帳 `drafts/entry/ENTRY_LEDGER.md`／記事 `guide-entry-*.html`（GitHub側生成＝SYNC外）。**広告なし**（`DENY_PREFIX`）。🚨 論文の数字は実際に見た出典（要旨・公式PDF）からだけ書き、確かめられない数字は書かない。全25回＋総まとめで完結＝完結したら `QUEUE_LANES` から外して routine を止める
  - 🚨 **レーンを増やしたら、必ず `check_automation_health.py` の `QUEUE_LANES` に登録すること。**§⑤は「キュー枯渇による静かな停止」を捕まえる番人なのに、2026-08-31 まで **autodraft の1本しか見ておらず**、投資格言5日連続・投資詐欺7日連続の枯渇を誰も知らないまま放置していた（ルーティン自身は毎日きちんと台帳へ「🚩補充依頼」を書いていた）。🆕 **もう1つ＝guides.html に `data-category="<--category と同じ名前>"` 付きの空の欄とジャンプ欄の1行を先に作る**（無いと publish_article のカテゴリゲートで1本目が止まる。2026-09-26〜）
- **デイリーニュース記事 完全自動公開（2026-06-15→06-17 クラウド化）**: クラウドルーティン **`news-daily-auto`（`trig_01WZ9maArFYwaxyq99KJLJBi`、毎日 17:40 JST＝cron `40 8 * * *` UTC）**が手順書 `drafts/NEWS_DAILY_GUIDE.md` に従い最重要ニュースを「話題性×影響×付加価値」でスコア→**1本だけ**中立整理→**Opus自動公開ゲート（signal-lab方式＝決定論チェック[免責三層/禁止語/銘柄推奨無し/出典2系統]→🟢白は `publish_article.py --category "今日のニュース"`＋push／🟡軽微はOpus自己修正→別Opus確認／🔴黒・要協議・事実未確定はエスカレ）**で公開。公開物＝`guide-news-<YYYY-MM-DD>-<slug>.html`（通常記事）＋`guides.html`「今日のニュース」カード＋`drafts/news/NEWS_LEDGER.md`（GitHub側生成＝SYNC禁忌）。**薄い日は見送り**（合計9/15未満等）。個別銘柄は「買い/売り」と読ませないフラット整理厳守。⚠️旧ローカル `news-daily` は無効化済（二重公開防止でクラウド一本化）。手順書 `NEWS_DAILY_GUIDE.md`＝人編集＝**SYNC入り**・`drafts/news/*`はSYNC外。クラウドroutineは `RemoteTrigger`（list/get/run/create/update）で管理

- **⚡最新ニュース・ライブフィード（2026-07-09／08-06 ソース拡張）**: `news-ticker.json`（Actions `news-ticker.yml`、毎時37分＝`build_news_ticker.py` が固定媒体+公的機関+トピック横断検索（**単一の真実は `FEEDS`**）から最新24件を時刻降順で生成・`feed_health` 付き＝automation-health §⑦ がソース停止を検知。index.html がJSで閲覧時fetch）。**Actions が GitHub側で生成＝ローカルから push 禁止**（SYNC_FORBIDDEN 登録済）

- **話題の企業の有報本文（2026-09-02）**: `edinet-yuho.json`（Actions `edinet-yuho.yml`、平日 19:40 JST＝`build_edinet_yuho.py` が `EDINET_API_KEY` で jp-rankings 由来の候補企業の有報「事業等のリスク」等と主要指標を取得。routine `company-weekly-auto` はこれを読むだけ＝クラウド routine は Secrets を読めないので API を直接叩かない）。**Actions が GitHub側で生成＝ローカルから push 禁止**（SYNC_FORBIDDEN 登録済）
- **研究ラボの出力（2026-09-26）**: `*-lab.json`／`*-lab.md`／`*-forward.json`／`*-forward.md`（一覧は `RESEARCH_LABS.md`）・`signal-env-profile*`・`verified-list.md`・`promotion-list.md`（Actions が生成・**前向きの判定の履歴を持つ**＝古い版で上書きすると積み上げた判定が消える）。**正しい一覧は `check_site_consistency.py` の `SYNC_FORBIDDEN`**（ラボを足したらそこに2つ足す）
- **日本株ランキング（2026-06-20）**: `jp-rankings.json`（Actions `jp-rankings.yml`、夕 16:40/17:10 JST＝クローズ後・朝実行はcron遅延で廃止。`build_jp_rankings.py` が Yahoo価格で値上がり/値下がりトップ20生成→`generate_market_news.py` の `build_jp_rankings_section` が hot-assets 最上段に描画）。🆕 同じジョブの `jp-highs.json`（高値・安値の更新銘柄・日ごとの件数の履歴あり）も同じ扱い。**Actions が GitHub側で生成＝ローカルから push 禁止**。※`jp-stock-info.json`（赤字黒字/名前/業種の静的）と `build_jp_rankings.py` は SYNC入り＝ローカルで `make_jp_stock_info.py` で四半期更新して push

**理由**: これらは cron / 予約エージェントが GitHub 側で生成・push するファイル。ローカルから push すると古いファイルで上書きされ、**ライブページが過去日付に巻き戻る事故**（実例: 2026-04-24）。

HTML を即座に反映したい場合は GitHub Actions の "Run workflow" で手動 trigger。

### SYNC_FILES に含めるもの
- Python スクリプト（`generate_*.py` など）
- GitHub Workflow（`.github/workflows/*.yml`）
- `robots.txt`, 個別 guide-*.html（※`sitemap.xml` は **SYNC禁忌へ移動**＝下記参照。generate_market_news.py が全guideを自動収集して再生成するため、ローカルから push しない）
- `economic-events.json`, `my-trades.json`
- Claude Code 設定（`.claude/agents/*.md`）
- ドキュメント（CLAUDE.md, SESSION_HANDOFF.md, memory/*.md）

### 🤖 robots.txt の Disallow（2026-08-01 実装）

**手で編集しても消える**＝`build_robots_txt()`（`generate_market_news.py`）が毎回の update-market-news で再生成→commit するため。**変更は必ず `build_robots_txt()` に書く**（手動編集が7分で消えた実例＝SESSION_ARCHIVE【2026-08-06 退避】）。

遮断＝`/drafts/`（下書き+REVIEW.md+labnotes/news/proverb/sns）・`/memory/`（投資家プロファイル）・`/*.md$`（routine が増やすので個別列挙しない）。`Allow: /` と併存可（**より具体的な規則が勝つ**）・.md へのサイト内リンク0件・sitemap にも不掲載。

⚠️ **非公開化ではない**＝行儀の良いクローラにしか効かず `raw.githubusercontent.com` 経由の露出（2026-07-26）は塞げない。恒久策＝下書きを public に置かない、は未着手

---


## 🛠️ 保守ツール / 運用CLI（2026-06-01 新設）

**設計思想：ルールが増えても破綻しないよう「人間が手で守る」を「コードが自動で守る」に置き換える。新ルールはチェックを1個足す形で拡張する。**

| ツール | 役割 |
|---|---|
| **`mw.py`**（司令塔CLI） | `python mw.py check / publish / sync / trigger <wf> / status [wf] / routines`。スクリプト名を覚えずに運用できる単一入口 |
| **`check_site_consistency.py`**（リンター） | サイト不変条件を自動検査：**🆕公開保留のはずの記事がルートに残っていないか（カード無し＆noindex無し＝error）**／**🆕連番シリーズの回番号（重複・ファイル名とタイトルの #番号の不一致）**／**🚨SYNC禁忌の混入（巻き戻し事故防止）**／免責 kinsho-v1／10ボタンナビ／SYNC_FILES・sitemap・guidesカード登録／リンク切れ。errorで exit 1。**新ルールはここに検査を追加** |
| **`publish_article.py`** | 記事公開の②〜⑤を1コマンド・冪等（`mw publish` が内部で使用）。🆕**上書きゲート**＝git の HEAD 版と `datePublished` が違えば「公開済み記事を別記事で上書き」と判断して中止（`--allow-overwrite` で解除）。2026-09-06 に #089 が消えた事故の再発防止。🆕**置き場所ゲート**＝直下以外（drafts/ の下書きなど）は中止・上書きゲートは **origin/main とも比べる**（2026-10-04 #115 事故＝下書きのパスを通してゲートが素通り）。点検側は §10（カードの日付＝記事の公開日・drafts/ を指すカード）。🆕**カテゴリゲート**＝入れる欄が決まらなければ書き込む前に中止（旧版は記事一覧の先頭＝計算ツール欄へ黙って入れ、47枚が紛れた。2026-09-26）。点検側は `check_site_consistency` §8 が data-category の欄への紛れ込みを error |
| **`apply_logo.py`** 🆕 | サイトロゴ（案C・favicon+ヘッダーSVG）を全HTML+生成スクリプト9本へ冪等適用（2026-07-04導入済み。ロゴ変更時はSVG定数を編集して `--apply`） |
| **`apply_series_nav.py`** 🆕 | 連続シリーズ記事の末尾に「前の記事／次の記事」ボタンを冪等に敷く（2026-09-05 読者要望）。対象＝signal-lab / proverb / scam / tse / news（2026-09-09 時点 242本）。並び順は記事の `datePublished`（同日はファイル名）＝人が順番を管理しない。ただし **signal-lab だけ `"order": "number"`＝ファイル名の回番号順**（読者は #88→#89→#90 と番号で辿るため。2026-09-06 の上書き公開事故で公開日と番号が食い違った）。**update-market-news.yml が毎回 `--apply` して commit** ＝新記事が出ると「1つ前の記事の“次の記事”」も自動で貼り替わる。⚠️ 手で前後リンクを書かない（必ず腐る）。🆕 **noindex の記事は並びに入れない**（2026-09-17＝🚩エスカレ中の #097 へ #096「次」/#099「前」から到達できた） |
| **`sync_economic_events.py`**（月次同期） | `ECONOMIC_EVENTS_2026` → `economic-events.json` を毎月25日に生成。**警告が鳴るかどうかはここが全て**＝`RULES` に規則が無い指標は生成されず、環境警戒スコアの対象外になる。🚨 **2026-09-17 大改修**: 英・ユーロ・中国・日本の12種を追加（それまで ⚠️未分類が22件あり、BOE は手で足した6月・7月の2件が再生産されず8月以降消えていた＝9/17の無警告の原因）。🚨 **影響銘柄は `AUD_PAIRS`/`JPY_CROSS`/`CN_SET`/`JP_SET` に集約**（中国指標に豪ドルが、日銀に円クロスが入っていなかった実害を受けて。オーナー指示「中国の指標も豪ドル系に効く」）。⚠️ 現地時刻＋tz で書く＝夏時間は zoneinfo に任せ、JST を手計算しない。⚠️ `json_pattern` は緩くしない（`r"日銀"` が日銀短観まで拾い、誤った食い違い警告と二重登録を生んだ）|
| **`verify_uk_eu_calendar.py`** 🆕 | **英・ユーロ圏**の発表日を一次情報と突合（2026-09-17 オーナー指摘「今日の英指標が載っていない」＝**英中銀の政策金利発表が1件も入っていなかった**。監視18銘柄のGBP/EUR ペアと ^FTSE を直接動かすのに穴だった）。取得先＝英中銀 MPC日程／ECB 理事会日程／ONS 各速報の Next release。🚨 **BOE の表は年を書かない**（「Thursday 5 November」だけ）＝見出しの年を拾う。🚨 **ECB は日付行と説明行が別**＝次行を見て「(Day 2)」だけ採る（2日目が発表日）。⚠️ **ONS が確定公表するのは次回1件だけ**＝先の月を勝手に埋めない。⚠️ **検証するのは日付のみ・時刻は未検証**（JST換算式は economic-events.json の note 側）。⚠️ 未登録の指摘は `HORIZON`（460日）まで＝ECBの2028年分まで毎週鳴らさない |
| **`verify_economic_calendar.py`** 🆕 | 米指標の発表日を**一次情報（BLS 公式スケジュール）と突き合わせる**（2026-09-11 の CPI 日付誤りの恒久対策）。🚨 **曜日ルールは足さない**＝正しい金曜(9/11)を弾いて誤った木曜(9/10)を通してしまう。日付の正しさは推測では決まらない。⚠️ **解析6件未満・今日以降の比較0件も失敗扱い**（「検証できなかった」を「問題なし」と取り違えない）。`verify-calendar.yml` が週1で実行 |
| **`check_plain_japanese.py`** 🆕 | 研究日誌の「やさしい日本語」検査（2026-09-23 オーナー指示「記号をなくし、初心者にもわかる日本語で」）。記号（≤ × →）・N=・R・プログラム用の名前・英字の略語・専門用語・用語の初出説明を見る。**signal-lab-daily が 8-1 の前と 8-4 i のあとに実行**（赤は言葉だけ直して最大5回→だめならエスカレ）。規則は `RULES` が単一の真実・人が読む版は QUALITY_RUBRIC「やさしい日本語」節。⚠️ 表見出しの IS/FWD は日本語つきなら残す（verify の期間取り違え検査の目印）。テスト＝`_test_plain_japanese.py` |
| **`apply_site_frame.py`** 🆕 | サイト共通の枠を冪等に敷く（2026-09-23）。①`<style data-mw-frame>`（ナビ6+5・広告余白）②解説記事のヘッダーを標準形へ（`<h1>`入りの表紙ヘッダーは残す）③ナビを11ボタンへ（置換分は `nav-bar mwf-nav`＝ページ側CSSに依らず同じ見た目）。⚠️ 本文・記事メタ行には触らない |
| **`inject_ads.py`** | A8.net のアフィリエイト広告を記事末へ冪等注入し、**記事ごとの候補から1つをランダム表示**する（`CREATIVES`＝素材の唯一の定義／`POOLS`＝記事→候補。`mw-ads.js` は CREATIVES から自動生成＝直接編集禁止）。🚨 **2026-09-10 に設計上の欠陥を修正**＝旧方式は PC/SP 両方を HTML に置き CSS で隠していたが、ブラウザは `display:none` の `<img>` も読むため**見えていない側の1x1計測gifまで毎回飛び、表示回数が実測で約2倍**になっていた（Chromium 実測）。新方式は選ばれた1つだけを JS で描画＝表示した分だけ計測。JS無効は `<noscript>` で候補の先頭を1つ。**「広告」ラベル必須**（景表法ステマ規制・2023-10-01 施行）。⚠️ **本文に推奨文・煽り文言を足さない**（金商法の誇大広告／投資勧誘に寄せない）。既存＝DMM株・DMM CFD・JFX株式会社（22記事）。移行は `--replace` |
| **routine `site-qa-lint`** | 土曜10:00 JST にリンターを自動実行→`site-qa-report.md` に報告（人が気づく前に検知） |
| **routine `failure-mail-patrol`** 🆕 | 毎朝 08:57 JST（`trig_01BYipEtVEsakf4bSFMe5sEc`・2026-09-28 オーナー依頼「1日1回失敗メールを巡回」）＝**`failure_patrol.py`** で直近26時間の失敗した実行を集め（ワークフロー×ブランチ・そのあと成功したか・失敗した段階・見張り番の🚨行と§④のコミットが PR 経由か）、1件ずつ原因と状態を確かめて報告（通知＝スマホ・メール）。小さく確かな直しだけ PR→検査→マージ（1回2件まで・ゲート不可）。手順書＝`drafts/FAILURE_PATROL_GUIDE.md`（SYNC入り）。🚨 **予約エージェントのリポジトリとコネクタは claude.ai のルーティン編集画面で付ける**（`create_trigger` には項目が無い＝付けないと `api.github.com` でもこのリポジトリは 403。試運転2回で判明し、同日オーナーがリポジトリと Gmail を付けた）。`mcp__github__*` は無いことがある＝`api.github.com` を curl で読む（認証はプロキシが付ける）。**ログは読まない**（2026-09-28 オーナー判断「原因がわかって直せればよい」）＝原因は失敗した段階の名前＋手元で再現（鍵が要る段階は再現せず、そのあと成功したかで判断）。**repo にファイルを書かない** |
| **`auto_pull.py`** 🆕 | **手元の Claude Code の起動時に、手元を GitHub の最新へ自動でそろえる**（2026-09-26・オーナー指示「研究はとても大事なので作って」。手元専用＝クラウドでは何もしない）。GitHub の ZIP を1回取るだけ＝API 不使用。手元で書き換えていないファイルだけ更新／**手元で書き換えたファイルは触らず「手元だけ変更＝送ればよい」「両方で変更＝統合が必要」を見分ける**（判定は前回そろえた版の指紋＝`_auto_pull_state.json`・時刻では決めない）／GitHub 側で作るデータ（SYNC禁忌）は控えを残して最新に／`_cloud_ledger.txt` も更新。**触らない**＝`research/`・`_`始まり・`sync_to_github.py`・`mw.py`・`.sync-cache.json`。設定は `python auto_pull.py --install-hook`（`.claude/settings.local.json` の SessionStart）。テスト＝`tests/test_auto_pull.py` |
| **`_reconcile.py`** 🆕 | ローカルと本番の差を**向き付き**で出す（ローカル専用・既定dry-run・`--apply`で取り込み・上書き前バックアップ）。このリポジトリは routine が**本番へ直接書く**ので**ローカルは構造的に遅れる**。L(ローカル)/R(本番)/B(`.sync-cache.json` の remote_sha＝前回sync時点) の3shaで「取り込み候補」と「ローカルが新しい」を判別。🚨 **時刻の新しさは正しさではない**ので、取り込む前に本番側のコミットとパッチを見せ、**追加0・削除のみ＝巻き戻しの疑い**に目印を付ける（`--patch` で中身も表示）。⚠️ 記事ミラーの遅行は従来どおり `_pull_mirror.py`（`guide-*.html` のクラウドレーン専用）|
| **`style_diagnosis.py`** 🆕 | **投資スタイル診断**（2026-09-27 オーナー依頼「自分にどんなスタイルが合っているか」）。MT4 の口座履歴（Statement.htm）を読み、保有時間（スキャルピング／デイトレ／スイング／長め）ごとに**費用込み・ロットに左右されない物差し（1日の値動きATRの何倍か）**で数え、**値動きの大きさ・流れの向き・前半後半のどれでもプラスか**まで見て ◯△▽✕？ を出す（判定の決まりは定数に固定）。🚨 **口座履歴は個人の記録＝入力も出力も `research/` の下**（出力は既定で `research/style-diagnosis/`）。`check_site_consistency` が `Statement*.htm` の SYNC 混入を error で止める。手元で `python style_diagnosis.py research/Statement.htm`（値段は Yahoo＝手元から）。テスト＝`tests/test_style_diagnosis.py` |
| **自動売買 AT1〜AT4・LP ドル円5分足の繰り返し** 🆕 | ⏸️ 2026-10-01 夜から保留（手元の EA・タスクは止めてある）。中身・決まり・結果は **`RESEARCH_LABS.md`** の「保留中の自動売買」節（2026-10-08 に CLAUDE.md から移した）。🚨 EA（MQL4/MQL5）は手元の `research/ea/` だけ＝リポジトリに入れない |
| **`_doctrine_check.py`＋`mw evolve`** 🆕 | 投資研究の進化ループの番人（ローカル専用・**固定オラクル扱い＝安易に緩めない**）。`research/DOCTRINE.md`（検証済み知識台帳）の数値を出典と機械突合＋事前登録簿ハッシュ＋仮説キュー状態表示。読み方はDOCTRINE冒頭のプロトコル参照（毎回全文Readしない） |

- **記事公開は `python mw.py publish --file ... --category ... --emoji ... --card-title ... --desc ...`** で ②〜⑤→整合性チェック→sync→workflow起動まで一気通貫（`--dry-run` で確認）。
- **sync 前に `python mw.py check`** を習慣に（特に SYNC禁忌の混入を自動で止められる）。
- 🆕 **手元のセッションは起動時に `[auto_pull]` の行が文脈に入る**（auto_pull.py の結果）。**⚠️「まだ GitHub に送っていないファイル」が出ていたら、ほかの作業の前に片付ける**：「手元だけ変更」→ `mw check` → `mw sync`／「両方で変更」→ `_auto_pull_conflicts/<ファイル>`（GitHub 側の版）と手元の版を統合してから sync（`--force` で押し切らない）。取得に失敗した回は、送る前に `python auto_pull.py` をやり直す

---

---

## 🛡️ コードが強制しているルール一覧（2026-10-08 に SESSION_HANDOFF から移した）（"覚える"でなく"コードで強制"）

> 設計思想（CLAUDE.md／auto-memory `feedback_rules_as_code`）＝**人が手で守るルールを、コードが自動で守る形へ**。
> 新ルールは「文書に書いて記憶で守る」より「**チェックを1個足す**」。私が記憶で守るルール数をゼロに近づける。
> 文書が長くなったら、必須ルールはコードへ移して文書から消し、古い履歴はアーカイブする（このスリム化もその一環）。

| 強制しているルール | 受け皿コード（単一の真実） | 効果 |
|---|---|---|
| SYNC禁忌ファイルを誤って push しない | `check_site_consistency.py` の `SYNC_FORBIDDEN`（`mw check`） | 巻き戻し事故を push 前に **error 停止** |
| **ドキュメントの文字でライブが止まるのを防止** 🆕8/5 | `.nojekyll`（Jekyll を丸ごと迂回）＋ `check_site_consistency.py` の `check_liquid_in_markdown` | Jekyll は**同期対象の .md 24件を Liquid として解釈**する。手順書に波括弧2連を書いただけで**Pages ビルドが12時間全失敗**（`duration=0` の即失敗・本文は "Page build failed." のみ）。**ライブは古いビルドを配信し続け health-check も緑**＝人力では気づけない。検査は `.nojekyll` 有無で error/warning を切替（無ければ実際に落ちるので error）。誤検知ゼロを実測 |
| **新記事が旧テンプレ/旧色で公開されるのを防止** 🆕8/5 | `check_guide_draft.py` 検査9（判定は `apply_brand_color` の RULES/TOKENS を流用＝**色の知識を複製しない**） | ①Phase1の役割に旧色が残る ②ブランド色が1つも無い（＝既存と構造が違うテンプレ）の2条件で公開ブロック。`guide-signal-lab-060` はクラウドが**CSS変数式の別テンプレ**で出したため既存ルールが1つも当たらず、60本中1本だけ未適用だった。**誤検知率を全295本で実測＝0本**（真陽性1のみ） |
| **ロゴのラスタ画像が旧色で取り残されるのを防止** 🆕8/5 | `make_favicons.py`（`favicon.svg` を**単一の真実**として Pillow で描き直す。cairosvg 等の依存は足さない） | `apply_logo.py` はHTML内のインラインSVGしか直せず、**favicon-32/192・apple-touch-icon・ico は旧色のまま残る**（SVG対応ブラウザだけ新色という食い違い）。旧SVGで描き起こして現物と照合＝画素の96〜99.6%が一致することを実測してから配色を変えた。⚠️ロゴを変えたら `apply_logo.py --apply` と**両方**回す |
| **コミット連打で Pages のビルド上限を叩かない** 🆕8/5 | `sync_to_github.py --batch`（Git Data API で blob/tree→**1コミット**。テキストは tree に content 直埋め・バイナリのみ blob 化） | Contents API は**1ファイル＝1コミット**なので 257件の sync がビルド連打になる（実測 JST04時台48件/05時台11件/06時台25件・目安は10回/時）。一括なら**内容一致251件は tree 取得1回で通信ゼロ判定**＝往復も激減。staleness ガードと `--force` の意味は逐次版と同一 |
| 公開前に main を取り込む（reconcile） | `publish_article.py` 内蔵 reconcile | ローカル公開での巻き戻しを防止 |
| **ローカルが古い状態での sync 巻き戻し防止** 🆕 | `sync_to_github.py` の staleness ガード（remote_sha baseline 比較） | 前回 sync 後に GitHub 側が更新されたファイルの push を **🚫中止**（意図的なら `--force`） |
| **公開記事が guides.html カードから消えていないか** 🆕 | `check_automation_health.py` §③（`automation-health.yml` 毎朝09:30 JST） | 巻き戻し（local-drift）を **翌朝 Issue で即検知** |
| **同一 workflow の同時実行レース防止** 🆕 | `update-market-news.yml` の `concurrency`（cancel-in-progress: true） | push(on:push)＋手動trigger の二重起動を新しい方に一本化＝失敗run・誤アラートを根絶 |
| kinsho-v1 免責 / 10ボタンナビ / リンク切れ / SYNC_FILES登録 | `check_site_consistency.py`（`mw check`／土曜 `site-qa-lint`） | 不変条件を push 前に検査・exit 1 |
| 研究日誌の数値捏造防止 | `signal_lab_verify.py`（固定オラクル・編集禁止） | claims.json を signals-log から独立再計算して突合 |
| 更新履歴の整列・最新5件 | `generate_market_news.py` の `_history_items` | 手で削らない（日付降順・自動整列） |
| **発注前ルールの遵守を数値監視** 🆕 | `_trade_discipline_check.py`（`mw discipline`・週次 /loop） | 指標持ち越し/指数重ね張り/SL未設定/損切りずらし/JP✕を **EVダメージ順に可視化** |
| **相関ポジ合算リスク2%・実スリッページ** 🆕7/5 | 同上 R6/SLP（フォーム任意3欄=口座残高/リスク額/予定価格の入力分から自動判定） | 同テーマ×同方向の同時保有を横断検出し合算%で2%判定（金銀・FXも対象＝指数限定R3の一般化）。前向き検証の群割当は登録時5ルール固定＝R6は参考枠 |
| **公開日のUTC日付ミス防止** 🆕7/6 | `signal_lab_verify.py` の `date_check()`（再監査は `SIGNAL_LAB_SKIP_DATE_CHECK=1`） | datePublished/公開表記≠JST今日なら**赤=公開ブロック**（#031が7/5付けで公開された事故の再発防止） |
| **似スラッグの重複記事防止** 🆕7/6 | `check_guide_draft.py` 検査7 スラッグ重複検査（トークン集合の同一/包含） | ⑫⑬型の「語順違い/部分一致スラッグの同一主題」自動公開を**RED=人間エスカレ**（82記事総当たりで誤検知ゼロ） |
| **研究台帳の数値転記ミス・改竄・肥大化防止** 🆕7/7 | `_doctrine_check.py`（`mw evolve`・固定オラクル扱い） | DOCTRINEのアンカー**全件**（件数は書かない＝古びる）を出典JSON/mdと突合＋事前登録簿SHA256＋サイズ予算＋§1構造検査で**error停止**。予算は7/31に30/36KBへ改定＝上の(d)節が根拠。⚠️prose は**部分一致**なので、退避時は必ず前後で `_doctrine_check.py` を回す（偽陽性通過の実例あり） |
| **自動生成レーンの投資助言化を防止** 🆕8/1 | **`compliance_gate.py`**＝禁止語の単一の真実（SYNC対象）。**3レーン全部**が import＝`auto_weekly_review`／`generate_monthly_report`／`auto_weekly_strategy`（テスト=**`_test_weekly_review_gate.py` 18件＋`_test_compliance_gate.py` 31件**） | 禁止語に触れた生成文は不採用→次モデル→全滅なら決定論テンプレへ。**LLMの自己申告に頼らずコードで止める**（プロンプト修正だけでは再発する）。⚠️**8/1夕方の追加調査で、同じ穴が月次・週次戦略にも在ると判明**＝weekly-review を直した時点では塞がっていなかった。良性マスク（`BENIGN_PHRASES`＝「注目すべき」等）で週次戦略の誤検知を 1/10→0/10 に実測 |
| **免責(kinsho-v1)の全レーン検査** 🆕8/1 | `check_site_consistency.py` の免責検査を `AUTO_PREFIXES` の `continue` **より前**へ移動 | 除外が SYNC登録/リンク切れの誤検知回避のために置かれ、**巻き添えで免責検査まで飛んでいた**＝免責ゼロ2本を1本も検知できず。免責は生成レーンを問わない共通不変条件。誤検知は実測ゼロ（278本中、未設置は真に2本） |
| **銘柄チャートを記事に埋め込む** 🆕8/1 | `_gen_stock_panel.py`（テスト=**`_test_gen_stock_panel.py` 30件**） | 座標は全て計算（目分量のSVGは必ず破綻）。**10倍超の値動きは自動で対数軸**／軸に負の株価を出さない／x軸右端は必ず最終足／**最終足の出来高が未確定なら描かず注記**（決算日の出来高が中央値の2.9%＝Yahooの未確定値で「急騰は薄商い」と逆の示唆になる事故を防止）／トレンドライン・目標株価・売買示唆は描かない |
| **「登録したが走らない設計」の防止** 🆕7/31 | `_precheck_feasibility.py`（`control`＝同日対照が必要本数取れるか／`dim`＝使う次元が対象ログに在るか。テスト=**`_test_precheck_feasibility.py` 13件**）＋`mw evolve` の次候補に欠落欄を併記 | 必須欄チェックは**欄が埋まっているか**しか見ておらず、**埋めた設計が実行可能かは見ていない**。Q10（19銘柄に `min_ctl=30`＝理論上限18）と Q24（BTログの `news_count` 保有0.0%）を1本ずつ失って追加。⚠️**独立warningは足さず、提案するその場で欠落を出す**＝鳴りっぱなしを1本も増やさない設計 |
| **非公開研究（research/）の公開リポ流出防止** 🆕7/31 | `check_site_consistency.py` 検査1 `check_sync_forbidden`＝**ディレクトリ単位**の規則（テスト=**`_test_sync_research_guard.py` 22件**） | 列挙式は足し忘れが穴になる＝実測で research/ の非アンダースコア .md **13件中 登録済みは2件だけ**（`hypothesis_queue_archive.md`＝非公開仮説の全文147KB すら未登録）。境界は実態と一致（SYNC_FILES に research/ 配下は皆無）＝**誤検知率は全件でテストが毎回実測** |
| **非公開研究ファイルの公開リポ流出防止** 🆕7/7 | `check_site_consistency.py`＝SYNC_FORBIDDEN追加＋**`_`プレフィックス=ローカル専用規約** | DOCTRINE/queue/`_jp_*`等が SYNC_FILES に混入したら**error停止**（REDテスト7ケース済） |
| **公開記事への下書き残骸混入防止** 🆕7/7 | `signal_lab_verify.py` date_check の残骸検査 | 「下書き中」が本文に残っていたら**赤=公開ブロック**（#032実例の再発防止） |
| **休場中の発火を勝率に含めない** 🆕7/11 | エンジン=`generate_technical_alerts.py`週末閉場ガード（土07:00〜月06:00 JST・BTC除外・発火スキップ）＋集計=`is_weekend_closed_fire`（track-record/週次/月次の3本に同一定義複製） | 塩漬けデータ発火（実測214件・勝率33% vs 全体41.6%＝週明けギャップでSL直撃の測定アーティファクト）を源流と集計の両方で遮断。生ログは不変・ページに除外注記あり |
| **ローカル公開の日付事故防止** 🆕7/22 | `publish_article.py` の `check_date_gate`（免除は `--allow-backdate`・テスト=`_test_publish_date_gate.py` 5件） | 公開日≠JST今日なら **🚫 exit 1 で公開停止**（7/15事故の恒久対策・signal-lab date_check と同型） |
| **自動公開レーンの「静かな停止」検知** 🆕7/26 | `check_automation_health.py` §⑤（`automation-health.yml` 毎朝09:30 JST・テスト=`_test_topic_queue.py` 12件） | autodraft の未公開 topic が5件未満で **Issue**。①②は「走ったか」しか見ないのでキュー枯渇による仕様どおりの停止を捕まえられなかった（7/20〜24 に5日連続スキップを誰も検知できなかった実例）|
| **事前登録した仮説の「登録漏れ」検知** 🆕7/27 | `check_automation_health.py` §⑥（同 09:30 JST・`check_tracker_registration`） | コード側の宣言（`SEED`＋register定数）と実体（`signal-lab-tracker.json`）を突合し、**idもfilterも不在**なら **Issue**。7/27 に Q35の3件が「SEEDに足しただけ＝一度も登録されず」なのに台帳が「観測開始」と書いていた事故の恒久対策。**filter重複による正常スキップ（`metal_all_1d`等4件）は誤検知しない**ことを実データで確認済み |
| **エスカレした研究日誌が「直せなくなる」のを防止** 🆕8/11 | `signal_lab_verify.py` の **基準時刻凍結**（claims.json の `"asof"` ／ CLI `--asof`。打ち切りは `outcome_resolved_at`＝決済確定時刻。テスト=**`_test_asof_freeze.py` 16件**）。**使い方の正は `SIGLAB_ESCALATION_RECOVERY.md`** | 🚩が付いた回は**後日ライブログが進むと永久にREDで直せなかった**（#065 0/6・#067 は当日夕方に 11/11→2/11）。凍結で **#065 6/6・#067 11/11 に完全再現**を実測。⚠️捏造不可は不変＝数字は実ログとの完全一致が必要で asof は断面を選べるだけ。しかも **asof の日付は記事の公開日と一致必須**。⚠️`fired_at` で切ると誤り |
| **エスカレの滞留検知** 🆕8/11 | `check_automation_health.py` §⑧（`ESCALATION_STALE_DAYS=1`・テスト=**`_test_escalation_backlog.py` 13件**） | 「走ったが人間待ちで止まっている」形は①②③⑤の全部の死角だった＝オーナーが**目視**で気づくまで #065 が2日滞留。解決判定は公開実体（`guide-<target>.html` の有無）。🚩当日は鳴らさない（ゲートが働いた正常系） |
| **やりかけの仮説を増やしすぎない（WIP上限）** 🆕8/11 | `_doctrine_check.py` の `QUEUE_WARN_N/QUEUE_ERR_N`＝**12本で黄信号・16本で error**（`check_queue_wip`・テスト10件。**根拠と閾値の単一ソースは同ファイルの定数コメント**） | 旧・キューのバイト予算(36KB)を置換。要点＝36KBは「1.3KB/本」前提だったが、証拠要件を入れた **7/26以降**のブロックは平均7.8KB／以前は1.6KB＝**厚く書くほど罰せられる**逆向きの予算だった（較正が1日ずれていた）。error は**1本閉じるまで新規登録しない**WIP上限。⚠️`declutter_audit.py` の表からキューを外した（二次側が一次側と食い違う対処を出すため） |
| **事前登録の「空欄のまま登録済み」防止** 🆕7/26 | `_doctrine_check.py` の `REQUIRED_Q_FIELDS`＋`_q_field_gaps`（回帰テスト=**`_test_doctrine_registry.py` 23件**・実キュー31件でE2E確認） | 新Qは 登録日/ルール素案/検証設計/**対照**/主要評価指標/合格基準/**検出力** が埋まるまで **error＝登録簿に載せない**。SHA256は登録"後"の改竄しか見ておらず、テンプレのまま登録される穴があった。既存Qには遡及しない |
| **取り直せないスナップショットの欠測検知** 🆕7/28 | `_doctrine_check.py --agenda`（`mw evolve`）の心拍鮮度＋`_jp_earnings_cal_logger.py` の追記/冪等 | 決算カレンダーは**翌営業日1日分・履歴なし＝走らなかった日は永久欠測**。3日沈黙で ⚠️。**automation-health は GitHub 側でローカル専用ロガーを見られない**ため番人をここに置いた。BOM有無/沈黙/正常の3分岐を実測（BOMで例外→握り潰し→**番人が黙る**壊れ方を実際に踏んで修正済み） |
| **実在しない記事へのリンク公開を防止** 🆕7/30 | `publish_article.py` の `check_link_gate`（判定は `check_guide_draft.internal_link_check` に一本化＝基準の単一ソース。テスト=**`_test_guide_link_check.py` 20件＋`_test_publish_link_gate.py` 7件**） | 参照先が実ファイルとして存在しなければ **🚫 exit 1 で公開停止**（免除は `--allow-missing-links`）。Search Console の404の恒久対策。**要点は「全レーンが通る関門に置く」**＝`check_guide_draft` 側だけでは news/proverb レーンが素通りする。併せて `CLOUD_GENERATED` でSYNC禁忌ページを除外しないと**ナビ経由で全記事RED**（実測217/217→5件） |
| **ローカルミラーの遅行を解消** 🆕7/31 | `_pull_mirror.py`（ローカル専用・冪等・dry-run既定） | クラウドが公開/更新した記事を取り込む。**内容ハッシュ(git blob sha)で比較**するので「ローカルに在るが古い」も検出。取り込み内容＝リモートと同一なので **sync は「⏭️内容変更なし」でスキップ＝無駄なコミットが出ない**。`guide-new-books.html` は SYNC_FORBIDDEN のため除外。⚠️これを怠ると `mw check`・404監査・FPテストが**揃って誤検知**する（7/31 に3回） |
| sitemap 全記事網羅 | `generate_market_news.py` の `build_sitemap_xml`＋`is_noindex_slug`（除外の単一ソース） | 全 guide を自動収集・手動編集不要。未掲載＝noindex 対象の意図的除外（7/31 実測で55本中54本が該当＝**不具合ではない**）。⚠️新記事公開時は sync 後に **workflow を手動 trigger**（下記の push 順序） |
| **「Run failed」の誤判定を防ぐ** 🆕8/8 | `judge_runs`（`check_automation_health.py`・テスト16件） | 8/6の失敗11件は**10件がcancelled・失敗step0**＋1件が GitHub の `Service Unavailable`＝コード起因ゼロ。旧番人は直近1件の`!=success`判定＝**誤Issueの時限爆弾**。新＝cancelled除外・閾値内にsuccess 0なら異常。⚠️`signal-workflows`群は`signals-log.json`共有＝**分割禁止**（詳細=auto-memory `reference_actions_failure_triage`） |
| **tickerフィードの停止検知** 🆕8/6 | `build_news_ticker.py` の `feed_health`＋§⑦（閾値=`FEEDS`の`stale_days`・テスト27件） | workflow緑のまま特定フィードだけ死ぬ形（8/1 Bloomberg型）を捕捉。同日ソース10→18本（公的機関+トピック横断・バッジは実発行元）。トピック検索は監視外＝誤検知ゼロ方針 |

🆕＝2026-06-20 追加（B＝カバレッジ番人 ／ C＝sync staleness ガード）。新ルールはこの表に1行＋チェック1個で増やす。

---

---

## 📎 CLAUDE.md から移した詳しい説明（2026-10-08・CLAUDE.md を目安 32KB に収めるため。中身は変えていない）

### サイト構成の表：research-list.html の行（全文）

| **research-list.html** 🆕 | 📋 検証中リスト（2026-10-07 オーナー「検証中のものはすべて検証中リストに入れてサイトに公開・日本株・FX で分けて」）＝研究の地図と同じデータを **🇯🇵 日本株／💱 為替（FX）／📈 株価指数・先物／🪙 金・銀・原油・ビットコイン／🧭 すべての市場に共通** に仕分けて並べる（前向きの検証・研究中・4時間足の仮説を市場ごとの表に）。`research_map.build_list_page`（仮説の市場＝`market_of`・前向きの検証＝`collect_studies` の `cat`）。**新しい前向きを足したら `collect_studies` に `cat` 付きで1件足す**。トップの研究の帯・地図のタブ・sitemap からリンク。SYNC禁忌。🆕 **見込みなしで止める決まり（2026-10-07 オーナー「見込みがないと思ったら検証済みリストに移動」・PREREG 同名節）**＝仮説はトラッカーが毎日自動で ⏹見込みなし（`status=retired`＝N≥300 で良い側の端が 0.10R 未満／60日以上で最初の判定まで2年超）・前向きの腕は `verified_list.RETIRED` に1行（根拠＝結果の出たほかの検証だけ）→ 一覧から外れ、検証済みリストと各市場の最後「⏹ 検証済みリストへ移したもの」へ | technical-alerts.yml（`generate_track_record_page.py` が track-record.html と同じ回に書く） |

### 自動化の表：jp-highs.yml の行（全文）

| **jp-highs.yml** 🆕 | **jp-rankings の完了**（`workflow_run`）＝同じ営業日の一覧があれば数秒で終わる | **高値・安値の更新銘柄**（2026-10-06 オーナー依頼・同日夕に安値・同日夜に**東証の全上場 約3,700銘柄**へ＝`build_jp_highs.py`→`jp-highs.json`→hot-assets「🏔️ 高値・安値更新」。対象の一覧は JPX「東証上場銘柄一覧」を毎回取る・1回13〜15分のためランキングから分けた・**一覧が変わったときだけ** update-market-news を workflow_dispatch で頼む（相乗りだと何も変わらない回まで AI を使う）。高値と安値は同じ関数（`side`）で判定。年初来＝1〜3月は前の年の1月から／上場来は Yahoo の記録が上場の週からある銘柄（月足の最初のバーが月の途中）だけ言い切る＝「上場来」＝東証に上場してからの記録・2022年以降に始まる記録は JPX の新規上場の上場日（前後10日）で確かめたものだけ・年初来の期間の途中から記録が始まり上場も確かめられない銘柄は数えない（Yahoo の記録が途中から急に始まる銘柄がある）。見分け方の点検と本番と同じ計算の試しは `jp-highs-audit.yml`（手動・ブランチ指定でマージ前に試せる）。テスト `tests/test_build_jp_highs.py`・鮮度は automation-health §⑫c） |

### トレード分析チーム・サイト運営チーム（全文）

### 🤖 トレード分析チーム（Claude Code カスタム subagent、2026-05-27 構築）

**目的**: トレード成績向上のため、テクニカル × ファンダ × リスク管理の 3 視点で意思決定を支援。サイト運営の自動化とは別目的の組織。

| Agent | 配置 | 役割 | モデル |
|---|---|---|---|
| **technical-analyst** | `.claude/agents/technical-analyst.md` | チャート / シグナル / ATR / RSI / MACD / BB / MA / 出来高 | Sonnet |
| **fundamental-analyst** | `.claude/agents/fundamental-analyst.md` | 経済指標 / 決算 / 地政学 / 政治発言 / 金融政策 | Sonnet |
| **risk-manager** ⭐ | `.claude/agents/risk-manager.md` | 統合判断・規律遵守の門番。SL/TP/ロット算出、過信防止 | **Opus** |

#### 想定ワークフロー
technical-analyst と fundamental-analyst を**同一メッセージ内で並列**に呼ぶ → 両方の結果をテキストで risk-manager に渡して統合判断（🟢条件成立／🟡グレー／🔴見送り推奨＋SL/TP/ロット）→ ユーザーが最終判断。

⚠️ 自動委譲のトリガー語は各 agent の `description` が唯一の真実（Claude Code が自動ロード）。**ここに書き写さない**＝二重管理を避ける。明示呼び出し例＝「risk-manager に聞いて、今 GC=F に入っていい？」

#### 設計原則
1. **投資助言ではなく参考分析** — 各 agent は出力に必ず明記
2. **N=6 戦 6 勝の罠に注意** — 直近実績は小サンプル、risk-manager が過信を抑える
3. **規律の門番は妥協しない** — 金曜大引け・環境警戒 D・反転検知ありは無条件見送り
4. **サイト公開しない** — agent 出力はユーザー個人向け（無登録投資助言業リスク回避）
5. **連携はテキスト経由** — メインがテキストを橋渡し（subagent 間の直接通信なし）

---

### 🌐 サイト運営チーム（Claude Code カスタム subagent、2026-05-28 構築）

**目的**: marketwatch-jp.com のクオリティ向上。記事執筆・法務監査・SEO/UX の 3 観点で並列に動かし、サイト規模拡大と検索流入増を加速させる。

| Agent | 配置 | 役割 | モデル |
|---|---|---|---|
| **content-writer** | `.claude/agents/content-writer.md` | 解説記事の執筆・編集、個別銘柄解説、速報記事、見出し作成 | Sonnet |
| **compliance-reviewer** ⭐ | `.claude/agents/compliance-reviewer.md` | 法務監査（金商法・景表法・AdSense）、無登録投資助言業リスク判定、黒/グレー/白 3 段階評価 | **Opus** |
| **seo-ux-strategist** | `.claude/agents/seo-ux-strategist.md` | SEO（メタタグ・構造化データ・sitemap）、ナビバー・内部リンク、Core Web Vitals、モバイル最適化 | Sonnet |

#### 想定ワークフロー
content-writer と seo-ux-strategist を**同一メッセージ内で並列**に呼ぶ → 両方の結果をテキストで compliance-reviewer に渡す（断定表現／個別銘柄推奨該当性／黒・グレー・白判定＋修正案）→ 統合して**8ステップルール**で公開。

⚠️ 自動委譲のトリガー語は各 agent の `description` が唯一の真実（Claude Code が自動ロード）。**ここに書き写さない**。明示呼び出し例＝「compliance-reviewer に新記事 AMD を事前チェック頼んで」

#### 設計原則
1. **投資助言ではなく情報提供** — content-writer は断定表現を避ける、compliance-reviewer が事後監査
2. **黒/グレー/白の 3 段階評価** — compliance-reviewer は曖昧な「リスクあり」ではなく明確な判定
3. **SEO はホワイトハットのみ** — リンクファーム・隠しテキスト等は禁止
4. **8 ステップルール厳守** — 新記事追加時は必ず CLAUDE.md の 8 ステップに従う
5. **触ってはいけないファイルを認識** — 6 コア HTML + political-feed.html + track-record.html 等は cron 管理

---


### cron の遅れの実測の表（2026-09-17）

**このリポジトリの実績**（予定時刻からの遅れ）:

| ワークフロー | 予定 | 中央値 | 90%tile | 最大 |
|---|---|---|---|---|
| automation-health | 00:30 UTC | **+221分** | +294分 | +666分 |
| health-check | 00:00/11:00 UTC | +160分 | +325分 | +617分 |
| technical-alerts-1d | 21:20 UTC | +59分 | +125分 | +485分 |
| news-ticker（毎時） | :37 | +34分 | +55分 | +60分 |
| jp-rankings（9/8〜25） | 07:40 UTC | **約+5h10m** | — | +6h51m |
