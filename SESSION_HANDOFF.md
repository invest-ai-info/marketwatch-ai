# 🔖 セッション引き継ぎ（最終更新: 2026-07-26 09:05）

<!-- 2026-07-24 declutter: 7/21完了節(⓪-7/21/⓪-人気度/⓪-EVアップ/⓪-ナビCSS/⓪-次の作業候補)をSESSION_ARCHIVE.mdへ退避。 -->

<!-- 7/20 完了節（UX利便性改善/指標ステート組合せ/失敗転換検証/シリコンサイクル記事/電池ブロック根治）は 2026-07-21 に SESSION_ARCHIVE.md へ退避。7/19以前の退避分も同ファイル。要点は auto-memory (project_signal_edge_research / project_jp_screener / project_proverb_series) と DOCTRINE に反映済み。-->

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
| sitemap 全記事網羅 | `generate_market_news.py` の `build_sitemap_xml` | 全 guide を自動収集・手動編集不要 |

🆕＝2026-06-20 追加（B＝カバレッジ番人 ／ C＝sync staleness ガード）。新ルールはこの表に1行＋チェック1個で増やす。

---

## ⚠️ 絶対遵守（事故防止）

- **SYNC禁忌**（ローカルから絶対 push しない＝routine/cron/generate が GitHub 側で生成）。**正は CLAUDE.md の SYNC禁忌リスト**。代表例：
  6コアHTML（index/calendar/charts/vix/market-health/hot-assets）／`signals-log.json`／`technical-alerts-history*.json`／`track-record.html`／political系／youtube系／`fundamental-context.json`／`weekly-levels.json`／`weekly-zone-plan.md`／`sitemap.xml`／`weekly-strategy-context.json`／`indicator-result.json`／`signal-lab-tracker.json`／`signals-log-backtest.json`／`article-ideas.md`／`daily-preview.md`／`political-digest.md`／`compliance-scan.md`／`site-qa-report.md`／`panic-scan.md`／`drafts/draft-*`・`drafts/news/*`・`drafts/sns/*`
  → `mw check`（`check_site_consistency.py`）が SYNC_FILES への誤混入を、sync の staleガードが「古いローカルでの上書き」を、それぞれ自動で止める。
- **SYNC対象（OK）**：`*.py`（※`sync_to_github.py` はローカル専用＝GitHub側は616Bスタブ。**`mw.py` はSYNC対象**＝7/7訂正。`_`プレフィックスのファイルは全てローカル専用＝SYNC禁止をコードで強制済）／`.github/workflows/*.yml`／個別 `guide-*.html`／`guides.html`／`robots.txt`／`my-trades.json`／`memory/*.md`／各 docs。
- 記事追加は **`python mw.py publish ...` → sync → workflow → ライブ確認**。公開前に compliance-reviewer(Opus)監査・教育トーン・特定銘柄の買い推奨は書かない・kinsho-v1 免責・10ボタンナビ。手動時も `mw check` で push 前点検。
- ネット不調時は無限リトライせず、ブラウザで手動 trigger を依頼（最大3〜5回）。

---

## 📌 アクティブな宿題

### 🔜 次セッションの入口（2026-07-26 09:05 更新）

> **在flight（未完了で手が止まっているもの）はゼロ。** 7/25-26 の作業は全て着地済み。
> 以下は「次にやると良いこと」であって、途中で放置されているものではない。

| # | 次の一手 | 状態 |
|---|---|---|
| 1 | **Q29 の設計**（PEADの検出力を確保する再登録）＝Q28は検定不能でクローズ済み | オーナー判断待ち |
| 2 | **`watch` 残り項目の棚卸し**（PEADは「調達待ち」が誤りだった。同じことが他でも起きている可能性） | 提案済み・未着手 |
| 3 | `charts.html` の `<title>`/meta が「50年価格チャート」のまま（中身は150年） | オーナー判断待ち |
| 4 | **autopublish の topicキュー枯渇**（7/20〜7/24 連続スキップ＝実質停止） | オーナー判断待ち |
| 5 | `drafts/REVIEW.md` の #049 が【ゲート実行中】のまま（実体は公開済み） | 記録の締めのみ |
| 6 | フォーム3欄（口座残高/リスク額/予定価格）未入力で R6 が待機 | オーナー作業 |
| 7 | 規律の前向き検証が **N=0/30 の休眠アーム**（取引が6/4以降停止中） | オーナー判断 |

**セッション冒頭は `python mw.py evolve`**（DOCTRINE突合＋仮説キュー＋トラッカー鮮度＋レジーム状態）。

---


- **⓪-✅ナビ文言「📈 50年チャート」→「📈 150年チャート」一括更新＝完了（7/25 21:55）**
  - **結果**: リモート実測 **244ファイル中243本が反映済み**。残1＝`youtube-summary.html`（生成物）は 21:55 に `update-youtube-summary.yml` を trigger 済み＝次回生成で解消。
  - **やったこと**: ①`unify_navbar.py` 25行目のラベルを150年へ→`--apply`（guide-*.html 215本） ②生成スクリプト8本＋静的HTML5本＝25箇所 ③`guide-nikkei-vs-topix`・`guide-us-china-summit-2026-05` の関連カード/本文リンク3箇所（navの2つ目以降＝unify対象外） ④sync 242成功/0失敗 ⑤Contents API でクラウドレーン **110本**（news32/signal-lab29/proverb21/auto9/weekly9/weekly-review7/他3）
  - **⚠️ 誤爆の罠（次に似た一括置換をするとき必読）**: `50年` の単純grepは **`250年`（`guide-proverb-mou-mada.html` 10箇所）と `1950年代`（`guide-masters-005`）に誤ヒット**し、機械置換すると `2150年`／`11950年代` に壊れる。`generate_market_news.py` の更新履歴「50年チャートを『150年チャート＋投資史年表』へ大幅拡張」も履歴の記述なので変更禁止。→ **置換キーを `📈 50年チャート` の完全一致に限定**すれば全部回避できる（破損0件を機械検証済み）。
  - **⚠️ reconcile が効いた実例**: sync で `generate_market_news.py`・`guides.html` が🚫staleで止まった。`--force` を直に叩かず**リモート最新を取得→その上にラベル変更を乗せ直し**てから `--force`。リモートは566B/1,445B新しく、飛ばしていたらクラウド公開の記事カードが消えていた。
  - **副次変更（申告）**: `unify_navbar.py --apply` は仕様どおりナビ全体を標準10ボタンへ正規化するため、**ラベル以外の既存崩れ24ファイルも同時に直った**（signal-lab 035-049 が `📈 チャート` と略されていた／weekly系9本に「📖 投資本」ボタン欠落）。
  - **実測スコープ訂正**: ナビラベルは 233箇所/233ファイルではなく **242箇所/223ファイル**。Contents API 対象は約50本ではなく **110本・7レーン**。ローカルに存在しないクラウド先行ファイルが30本あった。
  - **再利用ツール（ローカル専用・`_`プレフィックス）**: `_relabel_remote_push.py`（リモート最新取得→置換→PUT＝ローカルを送らないので巻き戻し事故なし）／`_relabel_api_targets.json`／`_relabel_live_state.py`（raw経由でライブ反映を実測）。
  - **⚠️ 環境メモ**: この日 `api.github.com` だけが TCP443 到達不能を繰り返した（IP 20.27.177.116・AAAA無しでIPv6迂回不可。`github.com`/`raw.githubusercontent.com`/ライブサイトは正常）。30分程度の窓が断続的に開く挙動。**raw経由の読み取りは生きているので、進捗実測は raw で行い、書き込みは窓が開いた瞬間に流す**のが有効だった。

- **⓪-🔬PEAD（決算後ドリフト）＝Q28検定不能でクローズ・Q29再登録が次（7/26 08:58）**
  - **最大の収穫は「調達不要だった」こと**: `drafts/idea-tested-slugs.txt` で PEAD は長く「データ調達待ち」とされていたが、実測すると**材料は全部手元にあった**（`_jq_fins_cache`=3,717銘柄・107列・`DiscDate`/`DiscTime` あり／日足レイク2021-07〜2026-07・両者とも5桁コードで直結合）。**`watch` の他の項目も同じ棚卸しをする価値がある**（真に調達が要るのは 粗利益率＝J-Quantsに売上原価なし／自社株買い＝TDnet／COT＝CFTC の3件のみ）。
  - **イベント表は完成・再利用可能な資産**: `research/_pead_events.py` → `_pead_events.csv` **69,616行**（2021-07-13〜2026-07-13）。受け入れ条件クリア＝**決算集中月が他月の約10倍**（2月13,176/5月13,593/8月12,666/11月12,603 vs 他月904〜3,694）。EAP（決算前ドリフト）も予想修正ドリフトも**同じ表の別の窓を見るだけ**で検証できる。
  - **Q28＝検定不能（合否なし）**: 同日diff train **+2.342%** / holdout **+2.468%**（符号・大きさとも独立2期間で一致・blowupも両期間でシグナル群が低い）だが、**bootstrapが縮退してp値が無効**。`samedate_diff_p` の `min_ctl=30` で有効日数が train101/holdout42 しかなく、`BLOCK_LEN=70` に対しブロック数が2/1。**nblk=1は系列全体の巡回シフト＝bootstrap分布が1点に潰れ、pは必ず床値0.000333**（実証: ユニーク値1/3000・標準偏差0.000000）。
  - **⚠️ 根本原因は検出力の設計不足**。決算は年4回の集中期に固まり fwd60 の窓が同一シーズン内で激しく重なる。ブロック長は重なり以上必要なのに5年で有効日数143日＝原理的に2ブロックしか取れない。**結果を見てから BLOCK_LEN を短くするのは §0-3（TT3のp 0.005→0.593）の罠。Q29 として新規登録すること。**
  - **Q29の設計課題**: 検出力を確保する方法を、**結果を見る前に**構造だけで決める（例＝ホライズンを短くする／`min_ctl`を下げる／リサンプリング単位を「日」でなく「決算シーズン」にする）。候補ごとに有効日数とブロック数は返り値を見ずに計算できるので、**事前登録時に検定成立性を検証してから走らせる**のが正しい順序。
  - **妥当性ガードを実装済み**: `_pead_test.py` の `MIN_BLOCKS=8` 未満は `検定不能`。以後この縮退で「合格」が出ることはない。
  - 設計書/計画=`docs/superpowers/specs/2026-07-26-pead-verification-design.md`／`docs/superpowers/plans/2026-07-26-pead-verification.md`。テスト=`_test_pead_events.py`(28件)/`_test_pead_test.py`(10件)。
  - **⚠️ 実装中に見つかった罠（コーディネータ起因・同種の作業で再発しうる）**: ①**entryタイミングが無検査**＝テストの始値行列を全日同値にしていたため `entry=O.shift(-1)` を `entry=O`（当日始値＝先読み）に変えても26件全緑で通った。**合成データを「都合よく単純」にすると検査したいものが値として区別できなくなる** ②`samedate_diff_p` の戻り値は3-tuple `(推定値[%], p値, 有効日数)`。同ファイルの `block_boot_p`/`cluster_boot_p` は float なので取り違えやすい。**判定に使うのは `est`**＝同日クロスセクション差で、プール平均差はタイミング運を含み誤り ③blowup比較を期間跨ぎで `max(sig)` vs `min(ctl)` にすると別母集団の突き合わせになる（登録文「blowup ≤ 対照」は期間内比較の意）。

- **⓪-✅レジーム転換検知オラクル＝稼働（7/25・オーナー承認済み設計）**
  - **背景**: DOCTRINE §3 は「棄却済みの再検証は新データ/新レジームのみ」と定めるが、**新レジーム到来を検知する仕組みが存在しなかった**（§0-6 の非定常性＝メタルが符号2回反転に対し無防備）。
  - **実装**: `research/_regime_state.py`（**固定オラクル・編集禁止**）＝N225の2軸4状態（トレンド=MA200上下／ボラ=60日実現ボラの750日分位）＋ヒステリシス21営業日。`_test_regime_state.py` **21件PASS**。
  - **実データ検証**: 2008年10-12月が**61日すべて `DOWN_HIGH`**（リーマン期＝下降×高ボラ）。4状態の分布 UP_LOW 2209/UP_HIGH 1318/DOWN_HIGH 1297/DOWN_LOW 588＝偏りなし。補完率1.623%。期間 2004-08-31〜。**現在=UP_HIGH**。
  - **配線**: 朝05:45の `_jp_screen_daily.py` に best-effort で日次更新を相乗り／`mw evolve` に現状態とアーム候補を表示／`_doctrine_check.py` に検査追加＝**鮮度10日超でwarning・凍結パラメータ外の生成はerror**（実地で発火確認済み）。
  - **事前登録**: **Q27**（`hypothesis_queue.md`・SHA256凍結済み・登録簿27件目）。凍結パラメータ＝ヒステリシス21/ボラ窓60/分位窓750/MA200/補完率上限5%/split=2024-12-31。**変更は新Q番号での再登録のみ**。
  - **🔜 第1段の再検証は保留（オーナー判断）**: 機械抽出（`research/_regime_targets.py`）の結果、**レジーム依存の棄却は表形式で3行のみ**で、うち1行は約20手法を束ねた棚卸し行（レジーム依存部分＝オニール型は他行と重複）。実質**2系統（個別5〜6本）**＝収穫が薄いため第1段は着手せず。着手条件はQ27に明記。**オラクル自体は他の仮説の条件付けにも使える資産として先に稼働させた**。
  - **設計書/計画**: `docs/superpowers/specs/2026-07-25-regime-detection-design.md`／`docs/superpowers/plans/2026-07-25-regime-detection.md`（Task 5/8＝再検証エンジンは未実装のまま保留）。
  - **⚠️ 実装中に見つかった罠4件（同種の作業で再発しうる）**: ①設計書の式表記 `mean(close[i-200:i])` が実装（当日を含む200本）とズレ＝そのまま凍結すると将来「仕様どおりに直す」名目で窓が1日ずれ全系列が非互換になる→設計書側を実装に合わせた ②**先読み禁止テストは時間方向しか見ない**＝medの窓に当日を混入させてもテストが緑のまま通った（ミューテーションテストで発覚）→時点内の自己参照は別テストで固定 ③`frozen_params` がモジュール定数を無条件に書いており、非既定生成を番人が検知できなかった＝**検知できない番人は無いより悪い**→実際に使ったparamsを渡す方式へ ④`fetch_n225` が `fromtimestamp` を tz無しで呼んでおり実行環境のTZ依存＝同プロジェクトの `build_historical_long.py`/`build_jp_rankings.py` は `tz=utc` 明示＝規約違反→修正。
  - **⚠️ `hypothesis_queue.md` が 17.4KB（予算14KB）で warning**。Q27本文が長いのは意図的（定義を設計書参照にするとハッシュ凍結が効かない）。解消は他Qの退避（`mw declutter`）で。
  - **実測スコープの訂正（下の旧メモは数値が誤り）**: ナビラベルは**233箇所/233ファイルではなく242箇所/223ファイル**。またリモートのContents API対象は**約50本ではなく110本・7レーン**（news 32／signal-lab 29／proverb 21／auto 9／weekly 9／weekly-review 7／その他3）。**ローカルに存在しないクラウド先行ファイルが30本**（`guide-auto-*` 9本など）。
  - **⚠️ 誤爆の罠（重要・単純grep厳禁）**: `50年` で引くと **`250年`（`guide-proverb-mou-mada.html` 10箇所）と `1950年代`（`guide-masters-005`）にも誤ヒット**し、機械置換すると `2150年`／`11950年代` に壊れる。また `generate_market_news.py` の更新履歴「50年チャートを『150年チャート＋投資史年表』へ大幅拡張」は**履歴の記述なので変更禁止**。→ **置換キーは `📈 50年チャート` の完全一致のみ**にすれば全て回避できる（実装済み・破損0件を機械検証済み）。
  - **副次変更（申告）**: `unify_navbar.py --apply` は仕様どおりナビ全体を標準10ボタンへ正規化するため、**ラベル以外の既存崩れ24ファイルも同時に直った**（signal-lab 035-049 が `📈 チャート` と略されていた／weekly系9本に「📖 投資本」ボタン欠落）。
  - <details><summary>着手前の調査メモ（7/25朝・数値は上で訂正済み）</summary>
  - **スコープ実測（7/25朝 grep）**: 文字列「50年チャート」＝**299箇所/249ファイル**。うち**ナビボタン（`class="nav-btn" href="charts.html">📈 50年チャート`）＝233箇所/233ファイル（1ファイル1個）**。残り約66箇所＝フッターのリンク列（`<a href="charts.html">📈 50年チャート</a>`）＋記事本文中の言及＋docs。
  - **手順（既存の決定論ツールに乗せる／新規スクリプトは書かない）**: ①**`unify_navbar.py` の25行目 `("charts.html", "📈 50年チャート")` を150年へ**（ここが10ボタン標準の単一ソース）→`python unify_navbar.py --apply`で guide-*.html 一括 ②**`apply_books_nav_scripts.py --apply`側の対象8スクリプト**＝`generate_market_news.py`(nav 7ブロック＋フッター等で計18箇所)／`generate_youtube_summary.py`／`generate_track_record_page.py`／`build_political_feed_page.py`／`auto_weekly_strategy.py`／`auto_weekly_review.py`／`generate_monthly_report.py`／`auto_indicator_preview.py` ＋ `guides.html`／`about`/`contact`/`privacy` ③`mw check`（NAV_LINKSはhref検査＝文言不問なのでエラーは出ない＝**目視かgrepで残数0を確認するのが検証手段**）→sync→`mw trigger update-market-news.yml`→ライブ確認。
  - **⚠️ 罠3つ**: (a) **6コアHTML（index/charts/vix/calendar/market-health/hot-assets）＋track-record.html＋political-feed.html＋youtube-summary.htmlはSYNC禁忌＝直接編集しない**。生成スクリプト側を直して再生成で反映（ローカルHTMLは再生成で上書きされる） (b) **`guide-signal-lab-*.html`（約50本）はSYNC_FILES外＝クラウド公開レーン**。ローカル編集してもpushされない→**Contents APIで一回限り修復push**が定石（7/21ナビ修復・7/24 anatomy導線と同型。`apply_anatomy_link.py`が手本）。しかも**ローカルミラーはGitHubに遅行**するので、一括編集前に必ずAPIでリモート列挙と突合 (c) `_`プレフィックス（`_gmn_remote.py`:7箇所・`_pub*.html`・`_draft*.html`・`_guides_remote.html`）と`drafts/*`は**ローカル専用/クラウドレーン＝触らない・pushしない**（grepの249ファイルにはこれらが混ざっている）。
  - **判断メモ**: 本文中の「50年チャート」言及（記事の文脈で"50年の長期チャート"と書いている箇所）は機械置換すると文意が壊れる可能性あり。**ナビ＋フッターのリンクラベルだけを対象**にし、本文言及は個別判断が安全。
  </details>

  - **🔜 残る判断事項（オーナー判断待ち・今回は方針どおり手を付けていない）**: `charts.html` 自身の **`<title>`／og:title／meta description が「50年価格チャート」「50年長期チャートを」のまま**（生成元＝`generate_market_news.py`）。中身は既に150年なので**表記が実態とズレている**。ナビが150年・ページ表題が50年という不整合になるため、次セッションで扱うか要判断。他に記事本文の言及が11ファイル（こちらは文意が壊れるので据え置き推奨）。

- **⓪-✅期限到来の確認2件（7/25朝＝両方クリア）**: ①**#050 に「チャート風図解」は入った**＝ライブ実測でインラインSVG3本、うち図1が `<!-- 図1：チャート風図解 -->` 付き（上昇トレンド帯＋BB上限/下限＋RSI売られすぎ反発/BB下限タッチの発火点／概念図注記あり）。図2=勝率バー、図3=IS→FWD前半→後半の時系列。**7/24夜のプロンプト改定は初適用回で機能＝調整不要** ②`drafts/REVIEW.md` の🚩＝**新規なし**（全1771行中3件はすべて7/8付の既存分）。#050は verify 6/6緑・finalize EXIT=0・Opusコンプラ🟢白・独立Opus🟢白で自動公開完了。
  - ⚠️ ついでの気づき2件: (a) **autopublish が7/20〜7/24の5日連続「topicキュー全24本公開済み・対象なし」**＝沈黙禁止ルールは効いているがキューが枯渇したまま（補充要否の判断待ち） (b) REVIEW.md の #049 が **【ゲート実行中】のまま**だが実体は公開済み＝記録の締めだけ残っている可能性。

<!-- 7/24以前の完了節は 2026-07-26 に SESSION_ARCHIVE.md へ退避（要点は auto-memory と research/DOCTRINE.md に反映済み）。 -->

## 📎 運用メモ

- 作業フォルダ: `C:\Users\info0\OneDrive\デスクトップ\新しいフォルダー` ／ GitHub: `invest-ai-info/marketwatch-ai`(main)
- 運用は **`python mw.py <cmd>`** が単一入口（check / publish / sync / **deploy [--trigger]** / trigger <wf> / status [wf] / **issues** / **audit** / routines）。`mw routines` で全 routine ID 一覧。
- 🆕 **ループ・エンジニアリング土台（2026-06-23・決定論コマンド＝トークン0）**：②`mw issues`＝open health-check/automation-health Issue 一覧（トリアージの土台）。③`mw audit`＝guide記事の改善候補スコア化（desc短/本文短/内部リンク少/JSON-LD無）。**判断部分だけ上限付き `/loop` でモデルに渡す**設計。`/loop` レシピ＝②「mw issues→最大3件診断＋提案(自動適用しない)→STOP」／③「mw audit→最弱を1本改善→白確認→publish、最大3本/回、score≥2が尽きるかで停止」。**🔑調査結果（2026-06-23）＝audit最弱11件は全部すでに `noindex,follow` 済み**（週次振り返り/週次戦略/月次の自動生成は薄ページAdSense対策で既にインデックス除外＝`auto_weekly_review.py`:287 / `auto_weekly_strategy.py`:378 / `generate_monthly_report.py`:291）＝**AdSense薄コンテンツ対策は完了済み**。よって `mw audit` を **noindex対応**に改修（noindex薄ページは別枠カウント＝改善対象外）→**インデックス対象81件中 改善候補0件＝公開コンテンツは健全**と確認。底上げ不要。
- 🆕 **`mw deploy`（2026-06-23）＝自己修復デプロイ（決定論・モデル不使用＝トークン0）**：sync を ❌throttle 時に backoff して**最大5回**再試行・🚫staleは即エスカレ・成功/上限/合計15分で必ず停止→任意で workflow 起動(`--trigger`)→ライブ200検証。上限は `mw.py` の `DEPLOY_*` 定数で固定＝構造的に永久ループ不能（今日の api.github.com throttle 手動リトライを自動化）。
- 同期は `python sync_to_github.py`（＝`mw sync`）。staleガードに 🚫 されたら「先に最新を取り込む（reconcile）」か、意図的なら `--force`。workflow 手動起動は `mw trigger <wf.yml>`。**ローカルは UTF-8 強制**：`$env:PYTHONUTF8="1"`（PowerShell）。
- routine 操作: schedule スキル → `ToolSearch select:RemoteTrigger` → RemoteTrigger（list/get/update/run）。クラウド routine（`signal-lab-daily`／`news-daily-auto` 等）はこれで管理。
- ⚠️ ローカルは GitHub と未同期なことがある（OneDrive）。**真の状態は GitHub／ライブを見る**。token は `market-news-config.json`(.json)。
- ユーザー北極星：投資家全体の底上げ／サイト・SNS 年収1000万／個人投資成績 年収1億。
