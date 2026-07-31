# 🔖 セッション引き継ぎ（最終更新: 2026-07-31 19:27）

> ## 🌅 次セッションの入口＝**在flightはゼロ**。
> **(a) 為替介入は着地済み（7/31 19:27）**。7/30 22:30 にドル円が30分で -3.03円（安値158.888）。
> **当サイトは報道より先に「円主導＝クロス円 -1.88% vs ドルストレート +0.42%＝4.5倍」を数値で提示**し、
> その後に日経が「政府・日銀が30日夜、3カ月ぶりの円買い為替介入に動いた」と**断定報道**。
> 日銀当座預金からの市場推計＝**約8兆4500億円**。同31日の日銀会合は**金利据え置き**。
> ドル円は31日東京で**160円台へ戻し**（高値160.833／19時 160.06）＝効果の持続性に疑問の見方。
> 記事は**公開＋追記まで完了**（`guide-news-2026-07-31-yen-surge-intervention-check.html`・commit 5b70426）。
> **残るのは確定額のみ＝財務省の月次公表（8月末）／日次内訳は四半期**。追記するならそのタイミング。
> 素材＝`_fx_intervention_data.json`／再取得 `_fx_intervention_probe.py`／図解 `_gen_fx_panels.py`。
> **(b) Search Console のインデックス登録レポートを開いて、報告されている404 URL が
> 7/30 に直した6件と一致するか確認**（別URLが載っていたらそれは未知の穴）＝**人の作業はこれだけ**。
>
> **⚠️ 夜の回線輻輳は「日による」。**2026-07-30 に原因を特定した：
> `api.github.com` と `github.com` は **AAAA を持たず IPv4 のみ**で、この回線は夜のピークに
> IPv4(PPPoE) が詰まる。IPv6 を持つ `raw.githubusercontent.com` だけが正常だった。
> ping は 7ms で通るのに TCP443 が張れないのはこのため。**遮断ではなく輻輳**なので
> リトライは効く。⚠️ ただし**同じ 7/30 の 20時台には普通に繋がり、①も404修正も完走した**。
> 「夜は不通」と決めつけず、`Test-NetConnection api.github.com -Port 443` で**実測してから**判断する。
>
> ### ✅ ① クラウドレーン記事125本に行長CSS注入 — **完了（7/30 20:33）**
> 1コミット `05142936` で125本。Contents API で実測5/5にマークあり。
> ⚠️ **教訓＝直後の冪等再確認は raw を使うと嘘をつく**（CDNキャッシュで「未適用0件」と出た）。
> 書き込み直後の検証は **Contents API**（`?ref=main`）で行うこと。
>
> ### ✅ ② `generate_market_news.py` のタップ領域CSS — **完了（7/30 21:37）**
> `#mwTickerFilters button` / `#tools a` / `#theme-toggle` / `#ss-btn` を44pxへ。commit `24944cd`。
> **reconcile を機械化した＝`_apply_tap_targets.py`（冪等・dry-run既定）**。手で乗せ直すと事故るため。
> 定石：リモート取得 → ローカルを置換 → `_apply_tap_targets.py --apply`（構文チェック内蔵）
> → 双方向 diff で照合 → `mw check` → `PYTHONUTF8=1 python sync_to_github.py --force`。
> **双方向 diff が要点**＝「合成 vs リモート＝CSS6行の追加のみ」かつ「合成 vs 旧ローカル＝履歴4行の
> 取り込みのみ」を確認すれば、クラウドの追記を消しても自分の編集を失ってもいないと機械的に言える。
> `update-market-news.yml` は `on: push` の `paths: generate_market_news.py` を監視しており、
> **generate_market_news.py だけを直す場合は push で自動起動する**（実測）。
> ⚠️ **ただし新記事を公開するときは 8ステップの⑦（手動 trigger）を省略してはいけない**（7/31 実測）。
> sync は SYNC_FILES 順に**1ファイルずつ commit**するため `generate_market_news.py` が記事より先に
> push され、**on:push が「記事がまだ存在しないツリー」で走って sitemap から記事が漏れる**。
> 起動は `python mw.py trigger update-market-news.yml`（**`.yml` を付けないと 404**）。

> ## ✅ 2026-07-30 夜に完了＝Search Console「404」の解消と恒久対策
>
> **発端**＝Search Console の「ページがインデックスに登録されない新しい要因：見つかりませんでした(404)」。
> sitemap 226URL に幽霊は0件・guides/index のリンク切れも0件で、**全284HTMLの本文内リンクを
> 実ファイル705件と突合**して初めて6件出た。**参照元は全部クラウド自動公開レーン**：
> 4件はハルシネーション（`guide-boj-policy.html`／`guide-bigtech-earnings.html`／7/15のIBM記事＝
> 日付ゲートで公開が止まった日を後続2記事が「あるもの」として参照／未公開の格言）、
> 2件はパス取り違え（`guide-contact.html`＝正しくは `contact.html`）。
> → `_fix_broken_links.py`（ローカル専用・冪等）で1コミット `ed65f396`。代替がある物は差し替え、
> 無い物は related-card ごと削除／本文中はアンカーだけ外して文章は残す。
>
> **恒久対策で踏んだ落とし穴が2つある。同じ間違いをしないこと：**
> 1. 最初 `check_guide_draft.py` にだけ検査を足したが、**このゲートを通るのは autodraft/signal-lab/
>    bookwatch だけ**で、実際に404を作った **news レーン(5件)と proverb レーン(1件)は素通り**だった。
>    → **全レーンが必ず通る関門は `publish_article.py`**。ここに `check_link_gate` を置いた（commit 338cf35）。
>    判定ロジックは `check_guide_draft.internal_link_check` に一本化（基準の二重管理を避ける）。
> 2. 素朴に実在チェックすると **217記事中217件がRED＝自動公開レーン全停止**になる。
>    ナビ10ボタンが全記事から `political-feed.html`／`youtube-summary.html` を参照しており、
>    この2つは**SYNC禁忌＝ローカルに存在しない**ため。→ `CLOUD_GENERATED` ホワイトリストで除外し
>    **217件→5件**（残5件もミラー遅行で、クラウド実行時は誤検知ゼロ）。
>    **新しいゲートを足したら必ず既存全記事で誤検知率を実測すること。**
> テスト＝`_test_guide_link_check.py`(20件)＋`_test_publish_link_gate.py`(7件・`--dry-run`で実起動)。
>
> **📌 「sitemap に54本が未掲載」は誤認だった（7/31 訂正）**：**不具合ではない**。
> `is_noindex_slug()`＝`guide-auto-*`／`guide-weekly-*`／`guide-monthly-report-*`／`NOINDEX_SLUGS`
> （AdSense再申請前に薄い日付フラッシュを noindex 統合した分）による**意図的な除外**で、
> **未掲載55本のうち54本が説明できた**（残る1本は当日公開の記事＝下記の push 順序が原因）。
> CLAUDE.md の「全 guide-*.html を自動収集」は正しい。
> ⚠️ **教訓＝生の差分だけ見て「漏れ」と判断しない**。未掲載を見つけたらまず `is_noindex_slug` に通す。
> 監査スクリプトの型は「除外ルールの単一ソースを import して、説明できない分だけ残す」。

> ## ✅ 2026-07-30 に完了してライブ反映済み
>
> **サイトデザイン改善（スマホ/PC）** — index の並べ替えと読みやすさ。すべて実測値：
> AI判断への到達 3.5→**1.9画面**／市場カード 5.0→**3.5画面**／A8広告① 3.3→**1.7画面**（動かさず前進）
> ／記事の1行 70字→**40字**（PC・116本）／タップ44px未満 51→**35個**／13px未満の文字 132→**53個**
> ／横スクロール0／ページ長は B3 の代償で 14.4→15.5画面。
> 手段＝`_apply_index_reorder.py`（並べ替え・冪等）＋ 共通CSSに `html{font-size:17px}`（rem基準を
> 上げてインライン168箇所を触らずに底上げ）＋ `_apply_readable_width.py`（記事へ `max-width:40em`）。
> ⚠️ **全部を44pxにしてはいけない**。WCAG 2.5.8 は文中リンクを除外しており、残21個中13個が該当。
>
> **図解の破綻を是正** — `guide-signal-anatomy.html` の実測で3つ発覚：BBが平行チャネル（幅の
> 最大/最小 **1.04倍**）／中心線なし／**足が x=390 で終わるのにバンドは x=480**（83px）。
> → `_gen_bb_panel.py` で**計算して座標を出す**方式へ（幅比3.01倍・−2σ貫通・RSI26点を価格と
> 0.05px精度で整列）。本文の「−2σタッチで発火」「RSI30割れ→反発」を図が満たすことを**seed採用条件**に
> 入れてある（満たさない図を出さない）。差し込みは `_apply_bb_panels.py`（冪等・dry-run既定）。
> **目分量で描くと必ず平行になる。今後チャートは計算で出す。**
>
> **公開ゲートに2検査を追加** — `signal_lab_verify.py` に `text_occlusion_check`（不透明図形に
> 文字が隠れる）と `band_parallel_check`（バンドが平行＝σ非連動）。`check_guide_draft.py` に接続済。
> 既知欠陥6ケースで陽性・陰性とも検証。既存 `text_overlap_check` は text同士しか見ておらず素通りしていた。
>
> **Codex 連携を確立** — `AGENTS.md`（プロジェクト＋`~/.codex/` グローバル）を新設。
> `§0 ENCODING` を **ASCIIのみ**で書いてあるのが要点：CP932で読むと日本語が全滅する
> （実測で CLAUDE.md が2,400文字化け）ため、化けても読める形で「UTF-8で読み直せ」を先頭に置いた。
> 呼び出しは `codex exec -s read-only --skip-git-repo-check -C <dir> -o <out> -` に**stdinでプロンプト**
> （引数渡しは PowerShell が引用符で分断する）。バイナリは `.codex/config.toml` の `CODEX_CLI_PATH`
> から引く（パスにバージョンハッシュが入るので更新で壊れる）。`.git` が無いので `codex review` は不可。
> **分業の実測**＝Codex はコードレビューで私の正規表現の退行を検出、図解2ラウンドともラベル配置は
> Codex の方が正確（私は衝突1件と2件を出した）。「私が設計/Codexが実行」ではなく
> **「私＝診断・仕様化・検証の設計／Codex＝明文化された仕様の実装」**。
> 両者とも自分の描画結果を見られないので、**測定ゲートが本質**。

## 🛡️ コードが強制しているルール一覧（"覚える"でなく"コードで強制"）

> 設計思想（CLAUDE.md／auto-memory `feedback_rules_as_code`）＝**人が手で守るルールを、コードが自動で守る形へ**。
> 新ルールは「文書に書いて記憶で守る」より「**チェックを1個足す**」。私が記憶で守るルール数をゼロに近づける。
> 文書が長くなったら、必須ルールはコードへ移して文書から消し、古い履歴はアーカイブする（このスリム化もその一環）。

| 強制しているルール | 受け皿コード（単一の真実） | 効果 |
|---|---|---|
| SYNC禁忌ファイルを誤って push しない | `check_site_consistency.py` の `SYNC_FORBIDDEN`（`mw check`） | 巻き戻し事故を push 前に **error 停止** |
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
| **研究台帳の数値転記ミス・改竄・肥大化防止** 🆕7/7 | `_doctrine_check.py`（`mw evolve`・固定オラクル扱い） | DOCTRINEのアンカー21件を出典JSON/mdと突合＋事前登録簿SHA256＋サイズ予算＋§1構造検査で**error停止** |
| **非公開研究ファイルの公開リポ流出防止** 🆕7/7 | `check_site_consistency.py`＝SYNC_FORBIDDEN追加＋**`_`プレフィックス=ローカル専用規約** | DOCTRINE/queue/`_jp_*`等が SYNC_FILES に混入したら**error停止**（REDテスト7ケース済） |
| **公開記事への下書き残骸混入防止** 🆕7/7 | `signal_lab_verify.py` date_check の残骸検査 | 「下書き中」が本文に残っていたら**赤=公開ブロック**（#032実例の再発防止） |
| **休場中の発火を勝率に含めない** 🆕7/11 | エンジン=`generate_technical_alerts.py`週末閉場ガード（土07:00〜月06:00 JST・BTC除外・発火スキップ）＋集計=`is_weekend_closed_fire`（track-record/週次/月次の3本に同一定義複製） | 塩漬けデータ発火（実測214件・勝率33% vs 全体41.6%＝週明けギャップでSL直撃の測定アーティファクト）を源流と集計の両方で遮断。生ログは不変・ページに除外注記あり |
| **ローカル公開の日付事故防止** 🆕7/22 | `publish_article.py` の `check_date_gate`（免除は `--allow-backdate`・テスト=`_test_publish_date_gate.py` 5件） | 公開日≠JST今日なら **🚫 exit 1 で公開停止**（7/15事故の恒久対策・signal-lab date_check と同型） |
| **自動公開レーンの「静かな停止」検知** 🆕7/26 | `check_automation_health.py` §⑤（`automation-health.yml` 毎朝09:30 JST・テスト=`_test_topic_queue.py` 12件） | autodraft の未公開 topic が5件未満で **Issue**。①②は「走ったか」しか見ないのでキュー枯渇による仕様どおりの停止を捕まえられなかった（7/20〜24 に5日連続スキップを誰も検知できなかった実例）|
| **事前登録した仮説の「登録漏れ」検知** 🆕7/27 | `check_automation_health.py` §⑥（同 09:30 JST・`check_tracker_registration`） | コード側の宣言（`SEED`＋register定数）と実体（`signal-lab-tracker.json`）を突合し、**idもfilterも不在**なら **Issue**。7/27 に Q35の3件が「SEEDに足しただけ＝一度も登録されず」なのに台帳が「観測開始」と書いていた事故の恒久対策。**filter重複による正常スキップ（`metal_all_1d`等4件）は誤検知しない**ことを実データで確認済み |
| **事前登録の「空欄のまま登録済み」防止** 🆕7/26 | `_doctrine_check.py` の `REQUIRED_Q_FIELDS`＋`_q_field_gaps`（回帰テスト=**`_test_doctrine_registry.py` 13件**・実キュー31件でE2E確認） | 新Qは 登録日/ルール素案/検証設計/**対照**/主要評価指標/合格基準/**検出力** が埋まるまで **error＝登録簿に載せない**。SHA256は登録"後"の改竄しか見ておらず、テンプレのまま登録される穴があった。既存Qには遡及しない |
| **取り直せないスナップショットの欠測検知** 🆕7/28 | `_doctrine_check.py --agenda`（`mw evolve`）の心拍鮮度＋`_jp_earnings_cal_logger.py` の追記/冪等 | 決算カレンダーは**翌営業日1日分・履歴なし＝走らなかった日は永久欠測**。3日沈黙で ⚠️。**automation-health は GitHub 側でローカル専用ロガーを見られない**ため番人をここに置いた。BOM有無/沈黙/正常の3分岐を実測（BOMで例外→握り潰し→**番人が黙る**壊れ方を実際に踏んで修正済み） |
| **実在しない記事へのリンク公開を防止** 🆕7/30 | `publish_article.py` の `check_link_gate`（判定は `check_guide_draft.internal_link_check` に一本化＝基準の単一ソース。テスト=**`_test_guide_link_check.py` 20件＋`_test_publish_link_gate.py` 7件**） | 参照先が実ファイルとして存在しなければ **🚫 exit 1 で公開停止**（免除は `--allow-missing-links`）。Search Console の404の恒久対策。**要点は「全レーンが通る関門に置く」**＝`check_guide_draft` 側だけでは news/proverb レーンが素通りする。併せて `CLOUD_GENERATED` でSYNC禁忌ページを除外しないと**ナビ経由で全記事RED**（実測217/217→5件） |
| sitemap 全記事網羅 | `generate_market_news.py` の `build_sitemap_xml`＋`is_noindex_slug`（除外の単一ソース） | 全 guide を自動収集・手動編集不要。未掲載＝noindex 対象の意図的除外（7/31 実測で55本中54本が該当＝**不具合ではない**）。⚠️新記事公開時は sync 後に **workflow を手動 trigger**（下記の push 順序） |

🆕＝2026-06-20 追加（B＝カバレッジ番人 ／ C＝sync staleness ガード）。新ルールはこの表に1行＋チェック1個で増やす。

---

## ⚠️ 絶対遵守（事故防止）

- **SYNC禁忌**（ローカルから絶対 push しない＝routine/cron/generate が GitHub 側で生成）。**正は CLAUDE.md の SYNC禁忌リスト**。代表例：
  6コアHTML（index/calendar/charts/vix/market-health/hot-assets）／`signals-log.json`／`technical-alerts-history*.json`／`track-record.html`／political系／youtube系／`fundamental-context.json`／`weekly-levels.json`／`weekly-zone-plan.md`／`sitemap.xml`／`weekly-strategy-context.json`／`indicator-result.json`／`signal-lab-tracker.json`／`signals-log-backtest.json`／`article-ideas.md`／`daily-preview.md`／`political-digest.md`／`compliance-scan.md`／`site-qa-report.md`／`panic-scan.md`／`drafts/draft-*`・`drafts/news/*`・`drafts/sns/*`
  → `mw check`（`check_site_consistency.py`）が SYNC_FILES への誤混入を、sync の staleガードが「古いローカルでの上書き」を、それぞれ自動で止める。
- **SYNC対象（OK）**：`*.py`（※`sync_to_github.py` はローカル専用＝GitHub側は**クラウド用スタブ**。⚠️2026-07-28訂正＝**サイズで判定しない**。クラウドが記事を公開するたび `publish_article.py` が追記するので**増え続ける**（616B→3,763B/84記事）。逆に**クラウド公開記事の台帳として使える**。**`mw.py` はSYNC対象**＝7/7訂正。`_`プレフィックスのファイルは全てローカル専用＝SYNC禁止をコードで強制済）／`.github/workflows/*.yml`／個別 `guide-*.html`／`guides.html`／`robots.txt`／`my-trades.json`／`memory/*.md`／各 docs。
- 記事追加は **`python mw.py publish ...` → sync → workflow → ライブ確認**。公開前に compliance-reviewer(Opus)監査・教育トーン・特定銘柄の買い推奨は書かない・kinsho-v1 免責・10ボタンナビ。手動時も `mw check` で push 前点検。
- ネット不調時は無限リトライせず、ブラウザで手動 trigger を依頼（最大3〜5回）。

---

## 📌 アクティブな宿題

### 🔜 次セッションの入口（2026-07-27 22:20 更新）

> **在flight（未完了で手が止まっているもの）はゼロ。** 7/27 は Q33〜Q43 の11本＋夜に Q44登録・トラッカー実バグ修正・日本株4本を着地させた。
>
> **🌅 明朝いちばんに見るのは1つだけ＝「Issue が来ていないか」。**
> 来ていなければ Q35の3件＋Q44 のトラッカー登録は成功している（`check_automation_health.py` §⑥ が 09:30 に自動判定）。
> 来ていたら routine 側の経路をもう一段疑う。**それ以外に人がやる確認作業は無い。**

| # | 次の一手 | 状態 |
|---|---|---|
| **A** | ~~日本株・寄り付き系の続き3択~~ → **7/28 オーナー判断＝③守りゲート。着手前チェックの結果、Q番号は発行せず「カバレッジ監査」に切り替え**（全文＝`hypothesis_queue.md` バックログ「決算持ち越し回避ゲート」）。**却下理由が Q44 と逆向き＝検出力が"過剰"**（必要N 14〜121件 vs 実働日中央値19件/日＝合格が最初から確定した検定）。加えて**📅列は Q14 H1 として7/11に登録・合格済み**＝重複だった。⇒ 未検証は効果量でなく **📅 の precision/recall（「空欄＝安全」と読んでよいか）**。ロガー稼働開始・**判定は 2026-09-01 目安**（8月季節を丸ごと蓄積後） | ✅判断済み・観測中。**人の手作業はゼロ**（平日2回の自動取得＋`mw evolve` の心拍番人） |
| A2 | 残る2択は未着手のまま＝①**裏返し（L1翌日の寄り天売り）**は⚠️**実行可能性の確認が先**（信用売り可否・逆日歩・空売り規制・貸株在庫） ②**「①マイナス寄り vs ③5〜10%」の差の検定** | オーナー判断待ち |
| 0 | ~~Q44＝「守り6ゲート×1h」を事前登録~~ → **7/27夜に着手前チェックで却下（537営業日必要）＝バックログへ。Q番号は発行していない**。残った実務＝**業者の実スプレッドを取得して `SPREAD_PCT` を実測に置換** | ✅判断済み。次は下の #0b |
| 0b | ~~BTC×1h にQ番号を発行するか~~ → **オーナー判断済み＝Q44として事前登録（SHA256凍結）＋トラッカー `btc_1h_gate` 登録＋`btc_all_1d` を tf=1d へスコープ補正**。判定は**前向きN≥91到達時に1回だけ**（≒2026-10上旬）。遡及 N=91 勝率31.9% グロス −0.2564 CI[−0.452,−0.060]／他17銘柄との差 −0.3477 CI[−0.584,−0.111]／総コストの24.3%を単独消費。週末アーティファクトではない（平日のみで −0.3575 と悪化） | ✅登録済み。**答えは時間が出す。覗き見しない** |
| 0c | ~~`signal_lab_tracker.py` を push~~ → **2026-07-27 19時 sync 完了（242/242成功）・リモートに `REGISTER_2026_07_27`／`TF_SCOPE_FIX_2026_07_27`／`btc_1h_gate`／`existing_ids` の反映を実測確認**。**明朝の確認は人がやらない＝番人にした**（7/27 19:47・`check_automation_health.py` §⑥）。7/28 06:10 の `signal-lab-daily` で4件が載れば 09:30 のヘルスチェックは緑、**載らなければ自動で Issue が立つ**（＝メール通知）。実装直後にライブ状態で試験し、宣言32件中**まさにこの4件だけ**を欠落として検出・正常スキップ4件は誤検知しないことを確認済み | ✅sync済＋番人化済み。**人の手作業はゼロ**。Issueが来たら routine 側の経路をもう一段疑う |
| 0c2 | **既見窓の重なりを実測・開示済み**＝Q44の前向き窓（7/27〜）と遡及分析（〜7/27）は**初日が1日重なる**が、実測の重なりは **BTC×1h で1件のみ（N=91中1.1%）・その1件は負け＝仮説に有利な方向**。`jpyfx_rsimid_gate` も1件（同じく負け）、他2件は0件。**registered_at は動かさない**（凍結した検証設計の本文と食い違わせない／手動除外は「ルールはコードで強制」に反する）。合格時はこの1件を割り引いて読む | ✅記録済み（queue Q44 の補遺） |
| 0d | **同型の tf 混在が `metal_all_1d`／`other_fx_revL`／`other_fx_long` にも残っている**（id/labelは日足や特定条件を名乗るのに filter に tf 無し＝ライブでは全足を算入）。BTCと同じ棚卸しが要るか判断する | 未着手。今回はオーナー判断がBTCのみのため対象外にした |
| 1 | ~~コスト仮定の銘柄別実測~~ → **7/27に解決済み**。プロジェクトには既に銘柄別 `signal_lab_sweep.cost_r_of`（`SPREAD_PCT`＋FX pip規約）がある。**私が使うべきはこれ**（自作フラットモデルを作らない） | ✅ |
| 2 | **フォーム3欄（口座残高/リスク額/予定価格）＝1件目の取引で入力**。無いと2%ルール/相関合算/実スリッページが測れず**チェックポイントが計算できない** | **オーナー作業**（取引再開が近い） |
| 3 | **BT3本の再生成タイミング統一**＝`signals-log-backtest-fx.json` だけ 6/16 で止まり**検出器が3種少ない**（`support_bounce`/`double_bottom`/`double_top` 欠落）。他2本は7/19再生成 | Q34/Q35の既知の不備（結論は不変） |
| 4 | Q29 → **2026-09頃に1回だけ再実行**（有効日282日到達時・設計変更なし）。自社株買いの再チェックも同時期 | 事前コミット済み・毎月試すのは禁止 |
| 5 | 規律の前向き検証が **N=0/30 の休眠アーム** | 取引再開で自動起動 |
| 6 | 信頼度スコアの整理（ティア補正の根拠 elite+0.758 が再現しない・メール本文の「HIGH＝優先」文言） | **急がない**＝スコア自体が無反応で実害なし（auto-memory `project_confidence_score_defect`） |
| 7 | **🔴黒の下書き本文を置く「非公開の受け皿」が未実装**（7/26 コンプラ監査の積み残し）。リポジトリは public＝`drafts/` は認証なしで読め、**削除してもgit履歴に残る＝取り消し不可**。⚠️**GitHub Issue も使えない**（public repoのIssueは誰でも読める） | 未着手。実害は現時点ゼロ（🚩9件は全て手続き・技術理由で法務系の黒は0件）＝**次に黒が出たときに初めて効く**穴 |
| 8 | **`weekly-trade-review` routine が `MY_TRADING_RULES.md` の6月時点の旧版を読む**（6/19 にSYNC除外＝ローカル専用にしたため）。7/26 に追加した「デイトレ開始の事前登録」がレビューから見えない | 未着手。**取引再開＝#2 と同時に効いてくる**ので、その前に受け渡し方法を決める |

**セッション冒頭は `python mw.py evolve`**（DOCTRINE突合＋仮説キュー＋トラッカー鮮度＋レジーム状態）。

---


<!-- 2026-07-27 22:20 declutter: 7/27の完了節6本（⓪-💰Q42/Q43コスト構造・⓪-🧱建玉/出口/損切り4本・⓪-🚪Q36出口・⓪-⚪B2信頼度・⓪-🎯Q34レジーム・⓪-📐Q33週足ピボット）を SESSION_ARCHIVE.md へ退避。 -->
- **⓪ 7/27 午前〜夕方の検証11本（Q33〜Q43）は全て決着済み＝本文は SESSION_ARCHIVE.md（2026-07-27 退避節）へ。**
  結晶化先＝**DOCTRINE §0-11（条件付けは構造には効き相場つきには効かない）／§0-12（出口・建玉・水準は増幅器であって発生器ではない）**、
  各Qの全文＝`research/hypothesis_queue_archive.md` の 2026-07-27 退避節。要点は冒頭★とその訂正3点に集約済み。

<!-- 2026-07-28 declutter: 7/26完了節3本（⓪-🔒コンプラ／⓪-⏱デイトレ準備／⓪-⏭自社株買い見送り）を
     SESSION_ARCHIVE.md【2026-07-28 退避】へ移動。⚠️退避前に本文へ埋もれていた**未解決2件**を
     アクティブな宿題 #7（非公開の受け皿が未実装）・#8（weekly-trade-review が旧ルールを読む）へ昇格済み。
     要点は auto-memory (project_marketwatch_compliance / project_discipline_loop) にも反映済み。 -->

<!-- 2026-07-27 declutter: 7/26完了9節（FXism数式確定/保留29件棚卸し/declutter+キュー予算/Q31/Q30/Q29/
     watch10件/autopublishキュー/完了4件）を SESSION_ARCHIVE.md【2026-07-27 退避】へ移動。
     教訓は DOCTRINE と auto-memory に反映済み。研究の全文は hypothesis_queue_archive.md。 -->
