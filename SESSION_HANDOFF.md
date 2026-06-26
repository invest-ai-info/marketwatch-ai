# 🔖 セッション引き継ぎ（最終更新: 2026-06-25）

新セッションは **このファイル＋ CLAUDE.md ＋ auto-memory（MEMORY.md 経由）** を読めば文脈を復元できる。
2026-06-17 以前の詳細履歴は **SESSION_ARCHIVE.md**（保管庫・後から辿る検索用）へ退避した。

---

## ✅ 経済カレンダーに「主要企業の決算予定」追加（2026-06-26）

calendar.html に 📊 決算セクションを新設（マクロ指標グリッドの下・見方セクションの上）。**米国20社＋日本20社**の決算発表日を表示。ライブ反映済み。情報提供であり投資助言ではない旨の免責付き。

- **データ＝`earnings-calendar.json`**（SYNC_FILES入り・ローカル生成→commit方式）。生成は **`build_earnings_calendar.py`**：
  - **US=Nasdaq API自動取得**（`api.nasdaq.com/api/calendar/earnings?date=` を今日から約95営業日走査し主要20銘柄を収集。要 User-Agent）。**Nasdaq未掲載の遠い銘柄(NVDA/AVGO/WMT)は `US_FALLBACK` の前年実績ベース暫定日**で補完（確定して Nasdaq に載れば自動取得が優先）。
  - **JP=`JP_CURATED` のキュレーション20社**（無料の自動ソースが無いため）。確定3社=任天堂/NTT/ファストリテ、他17社は前年同期実績ベースの推定（`tentative:True`→画面に「（予定）」表示）。
  - `generate_market_news.py` の **`build_earnings_section()`** が JSON を読んで描画するだけ（取得はしない＝重い fetch と頻繁な描画を分離）。⚠️ Nasdaq は GitHub Actions で弾かれ得るため**ローカル生成**にしている。
- **更新 cadence（重要・年4回の決算期ごと）**：① `JP_CURATED` を各社IR/株探の確定日に更新（特に**7月入り後**：今は予定が多い）② `python build_earnings_calendar.py` ③ `python mw.py sync`（earnings-calendar.json と builder を push）④ `python mw.py trigger update-market-news.yml`（calendar 再生成）。確定したら `tentative` を外す。
- 銘柄を増減したい時は build_earnings_calendar.py の `US_TICKERS` / `JP_CURATED` を編集。

---

## ✅ サイト全体・記事横断検索（site-search.js）— 全ページ完了（2026-06-26）

ナビバーではなく **右上フローティング🔍**（`/`・Ctrl+K でも開く）。検索データは **guides.html を単一ソースに初回 fetch＋解析**＝索引ファイル/ビルド改修ゼロ・新記事は自動で検索対象。guides.html 自身は既存の「ページ内フィルタ」を持つため floating は**除外**（二重回避）。なぜフローティングか＝ナビ11ボタン化でモバイル2×5グリッドが崩れる＋110ページのナビ手術回避。

- ✅ **ライブ反映・検証済み**：`site-search.js`（HTTP200・10KB）／6コアページ（index/calendar/charts/vix/market-health/hot-assets＝update-market-news 再生成済み）／静的記事 約120本＋about/contact/privacy。検証＝全ページのタグ存在＋アセット配信＋ローカル実機での完全動作（絞り込み/遷移/キー操作/ライト・ダーク・モバイル）。
- ✅ 生成元にタグ注入済み：`generate_market_news.py`(×7) `generate_youtube_summary.py` `generate_track_record_page.py` `build_political_feed_page.py`。`site-search.js`＋保守ツール `inject_site_search.py`（静的HTMLへ冪等注入・guidesと生成9ページは除外）は **SYNC_FILES 入り**。
- ✅ **生成3ページ**（youtube-summary/track-record/political-feed）＝全て🔍ライブ反映済み（生成元にタグ済み→各 workflow 再生成で反映。youtube は 2026-06-26 に手動 trigger）。
- ✅ **task #7 完了（2026-06-26）**：GitHub 上の全 guide-*.html **129本**にタグ注入済み。ローカルに無いクラウド記事36本は **`_inject_cloud_search.py`**（scratch・SYNC外＝`_fix_cloud_mobile.py` 同型の GET→`</body>`前にタグ注入→PUT・冪等）で自己修復。再発時はこれを再実行すれば未注入分だけ埋まる。
- ✅ **恒久化（将来の新記事に自動付与）**：`publish_article.py` が公開時に🔍タグを `</body>` 前へ自動注入（mobile-fit 注入の直後・冪等。news/signal-lab/手動 guide をカバー）。週次/月次は `auto_weekly_strategy.py`／`auto_weekly_review.py`／`generate_monthly_report.py` のテンプレにタグ追加済み。
- ⚠️ guides.html は floating 検索を**載せない**（独自のページ内フィルタを持つため）。`inject_site_search.py` の EXCLUDE に `guides.html` を追加済み＝再 apply でも二重化しない。
- ⚠️ デプロイ中に api.github.com が WinError 10060 を反復（既知）。`--force` は**ローカル変更ファイルのみ PUT・未変更は⚡スキップで保護**と実証済（auto-memory [[feedback-sync-force-utf8]]）。直接実行時は `PYTHONUTF8=1` 必須（cp932で絵文字クラッシュ）。

---

## ✅ スマホCSS v3 — 全 guide 112件に反映完了（2026-06-22）

スマホの表が横スクロールする件（オーナー要望）＝**v3 対応完了**：表のセルは折り返さず1行（数字も説明も縦に割れない）＋**はみ出す表だけに「→ 横にスクロールできます」誘導**（スクロールで消える小 script）。`fix_mobile_overflow.py` の BLOCK を v3 化（style＋`<script id="mw-mobile-fit-js">`）、置換 regex も style＋script 対応に拡張。

- ✅ **guide 112件すべて v3**（ローカル sync 分＋クラウド専用＋当日新着 `guide-news-2026-06-22-nikkei-72k`。`_fix_cloud_mobile.py` 最終実行＝差し替え31/変更なし81/失敗0）。
- ✅ 今後の新規記事は `publish_article.py` が公開時に v3 を自動注入（`fix_mobile_overflow.py` v3 は GitHub 反映済）。
- ⚠️ api.github.com は throttle が断続的に出た（WinError 10060。書きは api のみ／raw は throttle外）。大量PUT後に起きやすい。混雑時は per-path の `_fix_cloud_mobile.py`（GET+PUT・0.4s間隔）が sync より通りやすい。
- ⚠️ SYNC3件（`guide-jp-value-vs-zombie`／`guide-risk-by-account-size`／`guide-jpy-intervention-2026-06`）は cloud 経路で v3 化したため local(CRLF)↔GitHub で次回 sync が staleガードに 🚫 することがある＝意図確認のうえ `--force` か通常 sync で再反映すれば綺麗（中身は同一 v3）。

---

## ✅ デプロイ待ち — 全件完了（2026-06-22）

✅ **2026-06-21 夜：`python sync_to_github.py`（182件・失敗0）** — スマホ修正の残り記事3＋ツール3、ゴールド土日連投の修正（`generate_technical_alerts.py` の市場休止ガード＝**次回 technical-alerts 実行分から土日メール停止**）、本ハンドオフ自体まで反映。api.github.com の throttle（WinError 10060）は自然回復済。

✅ **2026-06-22：item #2 完了** — クラウド公開記事のスマホ修正。GitHub上の guide-*.html 111件を走査し、`id="mw-mobile-fit"` 未注入の **26件**（`guide-auto-*`／`guide-news-2026-06-19〜21`／`guide-signal-lab-006〜009・014〜016`／`guide-weekly-*`／`guide-weekly-review-*`／`guide-monthly-report-2026-05`）に注入PUT（失敗0）。contents API で代表3件 marker=True を確認・`mw check`＝エラー0。
- 今後の新規クラウド記事は `publish_article.py` が公開時に mobile-fit を自動適用するため、この backfill は一度きり。再発時用に `_fix_cloud_mobile.py`（ローカルscratch・SYNC対象外）を残置。

✅ **2026-06-22：スマホCSS v2（数字の桁割れ修正）** — 旧 `*{overflow-wrap:anywhere}` が狭い表で価格を1桁ずつ縦に折る不具合（例＝intel記事の `+10.64%（終値$133.99）`）。`fix_mobile_overflow.py` の BLOCK を v2 化（`break-word`＋表の太字数値 `white-space:nowrap`＋左右余白圧縮 `.article` 14/12px・セル6px＋360px段＋本文小型化）。同ツールを「**既存ブロックを差し替え**」方式に変更（`apply_block`）。ローカル98件→sync、クラウド専用27件→`_fix_cloud_mobile.py`。**GitHub guide 111件すべて v2**（contents API で確認・`mw check`エラー0）。
- ⚠️ **学び（次回ハマり防止）**：① Windows の text-write で BLOCK が CRLF 化し sync はバイナリ push → クラウド側は LF 比較で「常に差分」に見え無限再PUTの罠。`apply_block` の同一判定を**改行正規化**で回避。② `_fix_cloud_mobile.py` は **ディレクトリ listing の sha が約60秒キャッシュ**で古い／**raw.githubusercontent は5分キャッシュ**。内容・sha は必ず**パス指定 contents API**（`contents/{name}?ref`）で取り直すこと。

---

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
| sitemap 全記事網羅 | `generate_market_news.py` の `build_sitemap_xml` | 全 guide を自動収集・手動編集不要 |

🆕＝2026-06-20 追加（B＝カバレッジ番人 ／ C＝sync staleness ガード）。新ルールはこの表に1行＋チェック1個で増やす。

---

## ✅ 2026-06-24 セッション

- **公開記事**：`guide-per-pbr.html`「PERとPBRとは？株の割安・割高を見分ける2大指標をやさしく図解」公開（カテゴリ投資の基礎知識・📊）。**インデックス記事（noindexでない）＝AdSense直結の"実のある記事追加"**。コンプラ独立監査=🟢白（全数式＋2023年東証PBR1倍割れ改善要請を出典付きで事実確認）。PER/PBRの仕組み→違い→PBR=PER×ROE→バリュートラップ注意。割安/ゾンビ・急落・NISA・分散と内部リンク。`mw publish` 一気通貫（185/0）・ライブ200・guidesカード反映。
- **公開記事②**：`guide-order-types.html`「成行・指値・逆指値とは？株の注文方法の違いと使い分けを図解」公開（投資の基礎知識・🧾・インデックス記事）。コンプラ独立監査=🟢白（仕組みの事実確認OK・過去C1前例に倣い「ほぼ確実」等の断定を軟化）。成行/指値/逆指値の仕組み→比較→場面別使い分け→薄商い/ストップ高安の注意。損切り・急落・夏枯れ・ポジションサイズと内部リンク。`mw publish`（186/0）・ライブ200。
- **公開記事③**：`guide-interest-rates-bonds.html`「金利と債券とは？金利が上がると債券価格が下がる理由をやさしく図解」公開（投資の基礎知識・💴・インデックス記事）。独立Opus監査=🟢白（修正なし。個人向け国債の中途換金=元本割れしない設計を財務省ソースで裏取り／断定回避「〜傾向/〜と言われます」徹底／特定商品の推奨なし／免責三層）。債券の3要素→利率と利回りの違い→金利と価格の逆相関（手描きインラインSVGのシーソー概念図）→デュレーション→5リスク→株への4経路（割引率/安全資産/銀行利ざや/為替）→個人向け国債・債券投信・分散。`mw publish`（187/0・整合性✅エラー0）・ライブ200確認済（💴/SVG/免責 検出）。内部リンク=銀行株/PER・PBR/スワップ/分散。
- **公開記事④**：`guide-simple-vs-compound-interest.html`「単利と複利とは？『利息に利息がつく』複利の力をやさしく図解（72の法則も）」公開（投資の基礎知識・📈・インデックス記事）。独立Opus監査=🟢白（修正なし。100万円×年5%の単利/複利テーブル[10年162.9/20年265.3/30年432.2万]・72の法則・−50%→+100%回復まで全数値を電卓で再検算し一致／数値は「計算上の例・運用成果を保証しない」注記＋『元本保証で高利回り』を詐欺注意として明示否定／免責三層）。単利vs複利の違い→年5%の差→72の法則→効かせる3条件(利回り/期間/再投資)→損失・手数料・税金にも効く注意→再投資/つみたて/NISA。手描きSVG(単利=直線/複利=曲線)。`mw publish`（188/0・整合性✅エラー0）・ライブ200確認済。内部リンク=複利とドローダウン/ドルコスト/NISA/金利と債券。
- **公開記事⑤**：`guide-etf-vs-mutual-fund.html`「ETFと投資信託の違いとは？仕組み・コスト・使い分けをやさしく図解」公開（投資の基礎知識・🧺・インデックス記事）。独立Opus監査=🟢白（修正なし。商品比較系で最警戒の「優劣誘導」「特定商品名の推奨」をいずれも回避＝中立に使い分けで整理／ETF=上場投資信託=投信の一種・基準価額vsリアルタイム・信託報酬や分配金再投資・乖離・タコ足分配注意・NISA枠の対象差まで現行制度として正確／免責三層）。共通点(詰め合わせ分散)→比較表(取引/コスト/分配金/積立)→目的別の使い分け→注意点→NISA。手描きSVG(投信⊃ETFの包含図)。`mw publish`（189/0・整合性✅エラー0）・ライブ200確認済。内部リンク=分散/単利と複利/注文方法/NISA。
- 記事キュー残：**なし（基礎キュー＝金利と債券・単利と複利・ETF×投信 を6/24に全消化）**。次トピックは autodraft topicキュー補充 or 新規候補の選定から。
- **ヘッダー統一（6/24・デザイン統一性）**：オーナー指摘「ナビバー各ページでトップのタイトルがバラバラ」を解消。原因＝6コア/データページだけが我流の大見出し（ブランド名なし・色も赤/ピンク/青緑バラバラ）で、残り80ページ超（ブランド「📊 MarketWatch AI」先頭）と不一致だった。対応＝`generate_market_news.py` に**共通関数 `brand_header(emoji,title,updated,extra)` を新設（単一ソース＝今後ドリフトしない）**し、index/calendar/market-health/hot-assets/charts/vix＋preview の計7ページのヘッダーを2段化（①固定青グラデのブランドバー＋タグライン ②ページ名＋最終更新のサブ行）。index の📊重複は📰に。ダーク背景は各ページの `header{}` 基底＋dark スクリプトに委譲＝**インラインで色固定せずダーク非破壊**、`.header-inner` の flex 不使用で崩れ回避。`COMPILE OK`→sync(commit bb821c4)→workflow→**ライブ6ページ全て統一ヘッダー反映を実機確認**。今後ヘッダーを変えるときは `brand_header()` 1か所を直す。
  - 🆕 **静的ページの外れ値も是正**：オーナーがスクショで指摘の `guide-investment-books.html`（古い/独自テンプレ＝ヘッダーにタグライン無し＋`.nav-btn` に `display:inline-flex` 無しで `min-width:170px` が効かずボタン形が違う）を標準化（commit 27e2582）。同症状を全 guide で再スキャン→**真の該当は guide-news 3本のみ**（2026-06-15/-17/-18。当初23本ヒットは誤検知＝inline-flex がルール内別位置にあり正常）。news 3本は contents API 直PUT で標準化（`_fix_news_navbar.py`＝SYNC外scratch・巻き戻し不能・冪等）。全て実機で tagline/header-inner/nav inline-flex/hover を確認。
- **全ページ2段ヘッダー＋ナビ5×2固定（6/24・オーナー要望「移動した瞬間に現在地が分かるよう全ページにカテゴリー名を」）**：全ページのトップを「①ブランドバー＋②カテゴリー名」の2段に統一。ナビ先ページ＝各名（guides→📚解説記事／track-record→📊シグナル成績／youtube→📺YouTube要約／political-feed→🚨政治発言ライブ／投資本→📖投資本）、**個別解説記事 約105本＝📚 解説記事**、6コア＝各ページ名（既存）。ナビは `.nav-bar` に `max-width:1000px;margin:0 auto` 追加で**デスクトップ5個×2列に固定**（スマホ2列は従来通り）。ヘッダー寸法も統一＝ブランド1.6rem／タグライン0.85rem・間隔4px（market-healthの1remタグライン解消、brand_headerを1.5→1.6rem）。実装＝静的106本 `_apply_universal_header_nav.py`／生成器8本 `_apply_gen_header_nav.py`＋`brand_header()`編集。**⚠️106本一括syncで api.github.com throttle(WinError10060)に当たり**、reconcile方式（GitHub最新GET→編集当て直し→fresh shaでPUT＝巻き戻し不能）の `_push_header_nav_remaining.py`／`_push_gmn.py`／`_fix_news_navbar.py` で全件押し込み。contents-API push分17ファイルは `.sync-cache` 基準を `_reset_cache.py` でpop済（次sync再baseline）。**track-record と youtube も反映完了**（track-record は **`technical-alerts-1d.yml`＝`--no-email` でメール副作用ゼロ**に再生成／youtube は `update-youtube-summary.yml`）。実機検証＝6コア＋political-feed＋track-record＋youtube＋静的サンプル全てカテゴリ行/5×2/サイズ統一OK＝**全ページ完了**。今後の変更点＝静的は上記2スクリプト、生成器は `brand_header()` と各生成器の該当行（`_*` scratchはSYNC外で残置）。
- **AdSense 再監査＆second-tier（6/24・詳細は `ADSENSE_CHECKLIST.md`）**：6/19のnoindex対応はライブで生存＋編集記事が +20 で厚みUP＝**再申請レディ**を実機確認（sitemap混入0・6コア独自解説生存・必須ファイル全200・`mw audit`改善候補0）。**second-tier 実施**＝index残の「日付つきイベント速報フラッシュ7本(btc-crash×2/nikkei-break×2/us-china-summit×3)」を `noindex,follow`＋sitemap除外（`NOINDEX_SLUGS`に追加→`apply_noindex.py`→sync189/0→workflow）。深掘り個別銘柄/bank-stocks/jpy-intervention-2026-06はindex維持。**残ユーザー操作＝Search Consoleで薄ページが「除外(noindex)」化を確認→再申請（目安6/26）**。

---

## ✅ 2026-06-23 セッション（夏枯れ記事＋調整買いリスト）

- **公開記事**：`guide-summer-doldrums.html`「夏枯れ相場とは？7〜8月の薄商いを乗り切る個人投資家の備え方」公開。コンプラ独立監査=🟢白（特定銘柄なし・断定なし・免責二層・2024-08-05急落データは日経/Bloomberg一次ソース一致）。ライブ200・guidesカード・index更新履歴 反映確認済。季節性ジャンルで `guide-sell-in-may` の姉妹編。
- **個人用（非公開・SYNC除外）**：`_MY_CORRECTION_WATCHLIST.md`＝「大調整が来たら買う」候補リスト。土台＝`_jp_doublebagger_owner.csv`(48銘柄)＋`MY_TRADING_RULES` の「続伸＝risk_off で点火する条件付きエッジ」。中核8(中型〜大型・流動性)／サテライト7(小型高スコア)／ディフェンシブ2＋発注前5問。点火サイン＝日経/TOPIX が60日線割れ。**平常時(risk_on)は寝かせ、落ちてる最中に飛びつかない**。
- **公開記事②（続編）**：`guide-correction-playbook.html`「株の急落・調整局面での立ち回り方｜“落ちるナイフ”の見分け方」公開。コンプラ独立監査=🟢白（「教育コンテンツの理想形に近い」評価・特定銘柄なし・下げ止まり指標[RSI/サポート/VIX]は教育目的の注記付き・分割エントリーvsナンピンの違い）。ライブ200・guidesカード反映。夏枯れ記事と相互リンク。
- 続編候補（後日）：セクター別の備え／記事キュー（金利と債券・単複利・ETF×投信・注文方法・PER/PBR）。
- 🆕 **YouTube要約ページに「今日/昨日/一昨日」切替タブを実装（`generate_youtube_summary.py`）**：以前「3日分保存したい」がトラブルで止まっていた件。元々 KEEP_DAYS=3 で3日分保持＋`generated_at` 日付グループ化まではできていて、**タブUIだけ欠けていた**のが正体。`build_html` を「最新3生成日→今日/昨日/一昨日タブ＋既定は最新日のみ表示・他は hidden」に改修＋`.day-tab` CSS＋`mwDay()` 切替JS＋ダークモード対応。raw実データで検証＝3タブ/3セクション/hidden2/JS・CSS有を確認。⚠️`youtube-summary.html`/`youtube-summary-data.json` はSYNC禁忌＝直すのは生成スクリプトのみ→反映は cron(朝10/11)か `mw trigger update-youtube-summary.yml`。タブは2生成日以上あるとき表示（蓄積で1→3タブに育つ）。

---

## ✅ 2026-06-20 セッション

### 午前〜（別セッション）：JP株システム一気通貫＋研究日誌救出
詳細は auto-memory `project_jp_doublebagger`（最厚）参照。要点：
- JP株ダブルバガー・システム完成（J-Quants 点in-time財務で検証／A1〜A3 クラウド自動化／**レジーム・コックピット**＝指数 vs 60/200日線＋市場の幅の多数決で上昇・下落を判定→下落でサイズ自動で守りへ）。公開記事2本（コンプラ白）＝`guide-jp-value-vs-zombie.html`／`guide-risk-by-account-size.html`。守りエッジ群は `MY_TRADING_RULES.md`（ローカル専用・SYNC除外）。
- 🚑 研究日誌のカード消失を local-drift から全復元（ライブ研究日誌 #1〜15）。
- 🔒 再発防止A＝`publish_article.py` に公開前 reconcile を内蔵（commit 1d28085）。

### 午後（本セッション）：B → C 完了（オーナー「順番に」）
- **B＝カバレッジ番人 ✅実装・デプロイ済**：`check_automation_health.py` に §③を追加。リポの全 `guide-signal-lab-*`／`guide-news-*` が guides.html にカードとして在るかを GitHub API で**毎朝照合**し、欠落＝巻き戻しを 🟡 で Issue 化。現状 **19件すべて掲載 OK**。今朝 #015 を巻き戻した類の事故を、この番人なら翌朝検知できる（commit 790963a・automation-health.yml が実行）。
- **C＝棚卸し ✅**：
  - **rules-as-code**＝`sync_to_github.py` に **staleness ガード**を追加（上表）。「公開前 reconcile」は `publish_article.py` では強制済みだったが、**生 sync 経路に穴**が残っていた（local-drift の第2の入口）。今回その穴を塞いだ。モック単体テストで stale=ブロック／`--force`=バイパス／baseline無=fail-open を確認。※`sync_to_github.py` はローカル専用（GitHub 未追跡）＝デプロイ不要・即有効。
  - **文書スリム化**＝本ファイルを 788行 → 約80行へ圧縮。2026-06-17 以前は `SESSION_ARCHIVE.md` へ退避（SYNC_FILES 入り）。

### 午後（続き）：機能追加＋信頼性修正
- **🚨 ドル円161円・為替介入の解説記事を公開**（`guide-jpy-intervention-2026-06.html`・独立Opus監査=白・ライブHTTP200）。介入の決定=財務省/実施=日銀、当局は水準を明言しない、2026GW介入実績(4〜5兆円)を断定せず中立整理。**公開は手動trigger を打たず on:push 1本に任せレース回避**（#670 push のみ success）。
- **🚀 JP新高値ブレイク機能を追加**（オーナー要望）：`_jp_breakout_scanner.py`（新）＝流動性400から52週高値更新を抽出、**レジーム risk_on のときだけ表示**＋危険スコア(過熱/連騰/超小型/負業種)で"宝くじ"を降格。`jp_daily.py` ⑥.5 に組込・`_jp_make_dashboard.py` に🚀タブ。**private repo `jp-momentum-research` にも push 済**（cloud run #8 success・スマホ表示OK）。
- **📆 track-record に日足タブを追加**：`generate_track_record_page.py` に1d足ダッシュボード（4H/1Hと同型・記録のみ/配信なしの注記）。日足シグナルは記録のみ(--no-email)で発火済(ライブ38件)＝**メールしない方針は維持しデータだけ可視化**。`technical-alerts-1d.yml` で再生成・ライブ反映確認。
- **🔧 信頼性修正2件**：(1)`update-market-news.yml` に concurrency 追加＝同時実行レース根絶(上表・commit 14cfa77)。(2)**staleガード↔reconcile の干渉を解消**＝`publish_article.py` が reconcile 後に `.sync-cache.json` の該当 baseline を消す（朝入れた staleガードが reconcile 済ファイルを誤ブロックする副作用を除去）。
- **📊 日本株 値上がり率/値下がり率ランキングを公開サイトに実装**（オーナー要望・`hot-assets.html` 最上段・スマホ最適化2列→1列・独立Opus監査=白・ライブ反映 run #676 success 各20件）。流動性上位400で 値上がり/値下がりトップ20＋**売買代金2日分**（前日/前々日＝ストップ高/本物の大商いを判別）＋**決算🟢黒字/🔴赤字**＋業種。**自己完結（公開リポ内・キー不要）**＝静的 `jp-stock-info.json`（`make_jp_stock_info.py` がローカルのJ-Quantsから四半期更新＝赤字黒字/名前/業種）＋**`jp-rankings.yml`（東京クローズ後 16:40/17:10 JST＝朝だとcron遅延で場中更新になるため夕方に）** が `build_jp_rankings.py` で **Yahoo価格だけ**から `jp-rankings.json` を生成 → commit すると **update-market-news の on:push（`jp-rankings.json` 追加済）が hot-assets を即再描画** → `generate_market_news.build_jp_rankings_section` が最上段に描画。`jp-rankings.json`=SYNC禁忌(workflow生成)。コンプラ要点＝事実データ・売買推奨でない・「大きく動いた≠良い投資対象」注記・免責二層。

---

## ✅ 信用残ウォッチを hot-assets に実装（2026-06-24）

出来高急増ページに **信用買い残・売り残（信用残ウォッチ）** を追加・ライブ稼働。「🔴 信用買い残が多い（上場比）」「🟢 信用売り残が多い（上場比）」の2ランキング＋信用倍率＋前日比＋見方注記＋免責。
- **データ源＝JPX公式「個別銘柄信用取引残高（日々公表銘柄）」日次Excel**（mtdailyk*.xls・キー不要・無料・ToS安全）。`build_jp_margin.py`（SYNC_FILES）が index.html から最新Excelを取得→pandas/xlrd解析→`jp-margin.json`(243銘柄・SYNC禁忌)。`jp-rankings.yml` に pandas/xlrd install＋build_jp_margin.py 実行(非致命 `|| echo`)＋jp-margin.json commit を追加。`update-market-news` の on:push に `jp-margin.json` 追加＝コミットで hot-assets 即再描画。描画＝`generate_market_news.build_jp_margin_section`（jprank-* CSS流用）。
- **🔑 J-Quants調査結果＝Lightプランは `/markets/*`(信用残/株価/空売り) が全て403「プラン外」、`/fins/*`(財務)のみ**。だから株価はYahoo・信用残はJPX公式Excelで取得（信用残をJ-Quantsで取るには Standard ¥3,300/月が必要・オーナー保留）。
- **コンプラ＝独立Opus監査で🟡グレー→軽微修正→別の独立Opusが🟢白確認**。修正＝①「日々公表銘柄」定義を正確化（「信用残が基準超＝投機的」→「注意喚起のため毎日残高を公表／規制措置ではない」）②列見出しの「＝上値の重し/＝踏み上げ余地」断定を外し事実見出しに③脚注を可能性表現④極端倍率(売残僅少)は「—」＋注記。事実データ・売買推奨でない旨の免責二重。内部リンク=guide-margin-balance。
- **⚠️ ハマり＝generate_market_news.py の contents-API reconcile で `{jp_margin_html}` 差込が CRLF/LF アンカー不一致で不発**（関数・呼出は入ったが差込だけ失敗→セクション計算されるが捨てられる）。スクリプトが no-op を「成功」と誤報告したのも一因。**教訓＝contents-API の文字列置換は改行(CRLF/LF)非依存にし、PUT後に raw でなく実HEADで適用結果を必ず検証**（raw.githubusercontentは5分キャッシュで誤判定する）。`_fix_gmn_template.py` で改行非依存に差込し解決。
- 実機検証＝hot-assets にセクション/2ランキング/実データ/免責/asof 反映確認済。今後は毎夕 jp-rankings.yml が自動更新。

## ✅ 金利・クレジットのレジーム＋解説記事2本（2026-06-24）

market-health の「④ 金融環境」に **米イールドカーブ（10年−3か月）card** と **クレジットの体温（HY債）card** を追加・ライブ。＋解説記事 **クレジットスプレッド**（`guide-credit-spread.html`・💳）と **イールドカーブ・逆イールド**（`guide-yield-curve.html`・📐）を公開。
- **データ＝Yahoo chart API（無料・FRED不可のため）**：`fetch_curve_credit()`（generate_market_news.py）が ^IRX(3M)/^FVX(5Y)/^TNX(10Y)/^TYX(30Y)/HYG/IEF を取得。カーブ＝10年−3か月で順/逆イールド判定。クレジット＝**HYG÷IEF の1か月相対＝OASの代理指標**（精密なOASはFRED/有料なので代理と明記）。取得失敗時は当該カードのみ消える設計。
- **🔑 FREDはこの環境から取得不可**（fredgraph.csv が truststore有無・リトライとも全タイムアウト）。Yahoo は全系列OK。詳細は memory `reference_price_data_fetch`。
- **コンプラ＝記事2本とも独立Opus🟢白**（HY OAS水準/HY・IG区分/NY連銀10年-3か月モデル/逆イールド非断定/タイムラグ＝全検証。クレジット記事のHYG言及は「体感の手段」で推奨でない）。market-health のカードも同じ非断定表現＋代理指標明記＋免責。
- **⚠️ ハマり3点**：①`publish_article` の `--card-title` に**スマートクォート `“”` を入れると PowerShell が `"` に正規化して引数が分断**→失敗。`「」`を使う（記事HTML内の`“”`はOK）。②**相互リンクする2記事は、両方の②〜⑤を先に済ませてから `mw check`→sync**（1本目だけだとリンク先がSYNC未登録でcheck失敗）。2本目は `publish_article.py --no-reconcile` で1本目のローカル追加を保持。③FRED不可。
- 実機検証＝記事2本ライブ200＋market-health に両card・記事リンク反映を確認。market-health は毎朝夕の update-market-news で自動更新。

## ⚠️ 絶対遵守（事故防止）

- **SYNC禁忌**（ローカルから絶対 push しない＝routine/cron/generate が GitHub 側で生成）。**正は CLAUDE.md の SYNC禁忌リスト**。代表例：
  6コアHTML（index/calendar/charts/vix/market-health/hot-assets）／`signals-log.json`／`technical-alerts-history*.json`／`track-record.html`／political系／youtube系／`fundamental-context.json`／`weekly-levels.json`／`weekly-zone-plan.md`／`sitemap.xml`／`weekly-strategy-context.json`／`indicator-result.json`／`signal-lab-tracker.json`／`signals-log-backtest.json`／`article-ideas.md`／`daily-preview.md`／`political-digest.md`／`compliance-scan.md`／`site-qa-report.md`／`panic-scan.md`／`drafts/draft-*`・`drafts/news/*`・`drafts/sns/*`
  → `mw check`（`check_site_consistency.py`）が SYNC_FILES への誤混入を、sync の staleガードが「古いローカルでの上書き」を、それぞれ自動で止める。
- **SYNC対象（OK）**：`*.py`（※`sync_to_github.py`・`mw.py` 等のローカル専用ツールは GitHub 未追跡）／`.github/workflows/*.yml`／個別 `guide-*.html`／`guides.html`／`robots.txt`／`my-trades.json`／`memory/*.md`／各 docs。
- 記事追加は **`python mw.py publish ...` → sync → workflow → ライブ確認**。公開前に compliance-reviewer(Opus)監査・教育トーン・特定銘柄の買い推奨は書かない・kinsho-v1 免責・10ボタンナビ。手動時も `mw check` で push 前点検。
- ネット不調時は無限リトライせず、ブラウザで手動 trigger を依頼（最大3〜5回）。

---

## 📌 アクティブな宿題

- ✅ **update-market-news.yml の失敗は解決済**（2026-06-20 午後・concurrency追加）。原因＝push+dispatch の同時実行レース。今後 `mw publish` を素で使ってもOK。
- 🚩 **FOMC結果の信頼性検証（6/18 起票・未確認）**：`indicator-result.json` の FOMC（据え置き 3.50–3.75%）は出典が個人ブログ系の疑い。一次（Reuters/Bloomberg/Fed）で数値を確認し、違えば訂正・正しければ出典差し替え。日銀（6/16・1.0%利上げ）は verified。
- 🔴 **POLICY dict 更新**：`generate_market_news.py` の `POLICY`（日銀→1.0%／FOMC据え置き）を会合結果へ。未更新だと market-health のスワップ金利差%が陳腐化。
- 📉 **AdSense 再審査準備**（auto-memory `project_adsense_review`／2026-06-18 却下＝「有用性の低いコンテンツ」）：薄い自動ページの noindex／編集コンテンツの価値強化を監査してから再申請。
- 🗓️ **`jp-stock-info.json` の四半期更新**（決算シーズン後に `python make_jp_stock_info.py` 再実行→`mw sync`。赤字/黒字フラグを最新決算へ。日次の値上がり率/売買代金は `jp-rankings.yml` が自動）。
- ✍️ autodraft topicキュー ⑫以降の補充（候補＝金利と債券／単利と複利／ETFと投信／注文方法／PER・PBR）。
- 📊 弁護士相談アジェンダ（track-record 統計開示／確信度ラベル／個別銘柄記事の言及）。
- 🟡 保留＝**J-Quants Standard（¥3,300・1回）** で「risk_off 転換→守り」を 2018/2020 実暴落でバックテスト（オーナー課金判断時）。
- 研究日誌の自動公開はエスカレ回のみ人間レビュー（`drafts/REVIEW.md` の🚩）。

---

## 📎 運用メモ

- 作業フォルダ: `C:\Users\info0\OneDrive\デスクトップ\新しいフォルダー` ／ GitHub: `invest-ai-info/marketwatch-ai`(main)
- 運用は **`python mw.py <cmd>`** が単一入口（check / publish / sync / **deploy [--trigger]** / trigger <wf> / status [wf] / **issues** / **audit** / routines）。`mw routines` で全 routine ID 一覧。
- 🆕 **ループ・エンジニアリング土台（2026-06-23・決定論コマンド＝トークン0）**：②`mw issues`＝open health-check/automation-health Issue 一覧（トリアージの土台）。③`mw audit`＝guide記事の改善候補スコア化（desc短/本文短/内部リンク少/JSON-LD無）。**判断部分だけ上限付き `/loop` でモデルに渡す**設計。`/loop` レシピ＝②「mw issues→最大3件診断＋提案(自動適用しない)→STOP」／③「mw audit→最弱を1本改善→白確認→publish、最大3本/回、score≥2が尽きるかで停止」。**🔑調査結果（2026-06-23）＝audit最弱11件は全部すでに `noindex,follow` 済み**（週次振り返り/週次戦略/月次の自動生成は薄ページAdSense対策で既にインデックス除外＝`auto_weekly_review.py`:287 / `auto_weekly_strategy.py`:378 / `generate_monthly_report.py`:291）＝**AdSense薄コンテンツ対策は完了済み**。よって `mw audit` を **noindex対応**に改修（noindex薄ページは別枠カウント＝改善対象外）→**インデックス対象81件中 改善候補0件＝公開コンテンツは健全**と確認。底上げ不要。
- 🆕 **`mw deploy`（2026-06-23）＝自己修復デプロイ（決定論・モデル不使用＝トークン0）**：sync を ❌throttle 時に backoff して**最大5回**再試行・🚫staleは即エスカレ・成功/上限/合計15分で必ず停止→任意で workflow 起動(`--trigger`)→ライブ200検証。上限は `mw.py` の `DEPLOY_*` 定数で固定＝構造的に永久ループ不能（今日の api.github.com throttle 手動リトライを自動化）。
- 同期は `python sync_to_github.py`（＝`mw sync`）。staleガードに 🚫 されたら「先に最新を取り込む（reconcile）」か、意図的なら `--force`。workflow 手動起動は `mw trigger <wf.yml>`。**ローカルは UTF-8 強制**：`$env:PYTHONUTF8="1"`（PowerShell）。
- routine 操作: schedule スキル → `ToolSearch select:RemoteTrigger` → RemoteTrigger（list/get/update/run）。クラウド routine（`signal-lab-daily`／`news-daily-auto` 等）はこれで管理。
- ⚠️ ローカルは GitHub と未同期なことがある（OneDrive）。**真の状態は GitHub／ライブを見る**。token は `market-news-config.json`(.json)。
- ユーザー北極星：投資家全体の底上げ／サイト・SNS 年収1000万／個人投資成績 年収1億。
