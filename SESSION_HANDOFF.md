# 🔖 セッション引き継ぎ（最終更新: 2026-07-26 15:38）

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
| **自動公開レーンの「静かな停止」検知** 🆕7/26 | `check_automation_health.py` §⑤（`automation-health.yml` 毎朝09:30 JST・テスト=`_test_topic_queue.py` 12件） | autodraft の未公開 topic が5件未満で **Issue**。①②は「走ったか」しか見ないのでキュー枯渇による仕様どおりの停止を捕まえられなかった（7/20〜24 に5日連続スキップを誰も検知できなかった実例）|
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

### 🔜 次セッションの入口（2026-07-26 14:56 更新）

> **在flight（未完了で手が止まっているもの）はゼロ。** 7/26 に #2〜#5 を着地させ、残るのはオーナー作業2件のみ。
> 以下は「次にやると良いこと」であって、途中で放置されているものではない。

| # | 次の一手 | 状態 |
|---|---|---|
| 1 | ~~Q29 の設計・実行~~ → **2026-09頃に1回だけ再実行**（有効日282日到達時・設計は変更しない） | ✅ 7/26 実行＝🚫検定不能（ブロック7/7・要8）。事前コミット済み |
| ~~2~~ | ~~`watch` 残り項目の棚卸し~~ | ✅ 10件確認済み（7/26）→ 着手可4件が判明 |
| ~~3~~ | ~~`charts.html` の `<title>`/meta が「50年」のまま~~ | ✅ 誤検知＝実測で解消済み（7/26） |
| ~~4~~ | ~~autopublish の topicキュー枯渇~~ | ✅ 15件補充＋番人追加（7/26） |
| ~~5~~ | ~~`drafts/REVIEW.md` の #049 が【ゲート実行中】のまま~~ | ✅ Contents API で補正（7/26） |
| 6 | フォーム3欄（口座残高/リスク額/予定価格）未入力で R6 が待機 | オーナー作業 |
| 7 | 規律の前向き検証が **N=0/30 の休眠アーム**（取引が6/4以降停止中） | オーナー判断 |

**セッション冒頭は `python mw.py evolve`**（DOCTRINE突合＋仮説キュー＋トラッカー鮮度＋レジーム状態）。

---


- **⓪-❌Q30 COT逆張り＝棄却（7/26 15:38・7/26の棚卸しで解禁した4本のうち1本目）**
  - **結果: 合格 0/4。しかも「検定不能」ではなく答えの出た棄却**。ブロック数36〜134（要8）＝Q28の2/1・Q29の7/7とは対照的に、検出力を事前確認してから登録した設計が意図どおり機能した。
  - **決定打は符号の期間反転**: train（〜2015）は全ホライズンで負（−0.170〜−1.615%）、holdout（2015〜）は全ホライズンで正（+0.310〜+0.860%）。p は 0.234〜0.662、BH-FDR後 q_train 0.662/q_holdout 0.602。
  - **train単独なら「順張りが正しい」、holdout単独なら「逆張りが効く」と正反対の結論を出していた**＝train/holdout分割が誤採用を実際に止めた実例。DOCTRINE §3 に記録済み。
  - **データ基盤は資産として残る**: `_cot_fetch.py`→`_cot_weekly.csv`（8資産・9,741週・2000-08〜2026-07）。CFTC公開API＝**キー不要**。派生仮説は新Q番号で使える。
  - **🔒 先読み防止の型（他のイベント系でも使える）**: COT集計日は火曜だが**公表は同週金曜15:30 ET**。「集計日+5日より後に始まる最初の週足バー」をエントリーにし、**実測ラグが4日未満なら書き出しを中止**する検査をコードに内蔵。祝日週の集計日ずれ（月119/金12/水7件）とYahoo最終週の進行中バーを一括で吸収。
  - **⚠️ 登録簿の罠2つ（今日どちらも踏んだ）**: ①**`- 補遺:`/`- 履歴:` は1行で書く**。折り返すと継続行が接頭辞を持たずハッシュ対象に入り「本文改竄」判定になる ②**新しいQブロックを挿入すると直前のQの末尾区切り（`---`）が奪われてハッシュが変わる**＝挿入時は区切りを補う。
  - **⚠️ 出典パスはBASE基準**: `[src: ...]` はプロジェクト直下から解決されるので、research配下なら `research/_q30_summary.json` と書く。
  - ⚠️ サイズ超過2件＝`hypothesis_queue.md` **32.5KB**（予算14KB）／`DOCTRINE.md` **24.5KB**（予算24KB）。**次の declutter 候補**（Q30は閉じたので退避可。手順と罠は上記）。

- **⓪-✅REVIEW.md #049 の記録補正＝完了（7/26 14:56）**
  - 実体は公開済み（`guide-signal-lab-049.html` HTTP 200・datePublished 2026-07-24・guides.html にカード有り）なのに記録が【ゲート実行中】で止まっていた。**【公開済み】＋公開ファイル名＋ゲート行**の3箇所を補正。
  - **やり方**＝`_relabel_remote_push.py` と同じ**リモート取得→完全一致置換→同じshaでPUT**（`drafts/REVIEW.md` は routine 生成の SYNC禁忌なのでローカルからは送らない）。安全弁＝各文字列が1回だけ出現・長さ増分ぴったり・**行数不変**・他エントリ健在をassertしてから適用。
  - **ゲート行は事実だけ書いた**＝当時の verify ログは残っていないので「公開は完了している（実測）／🚩エスカレが無いので通常経路を通ったと解される／**この行は事後補正であり当時のログではない**」と明記。**残っていない記録を復元したように書かない**。
  - ⚠️ **raw.githubusercontent はCDNキャッシュで数分間 古い内容を返す**（クエリ付与でも回避不可だった）。**書き込みの反映確認は Contents API で行う**（実測＝90,733字/1785行/`【ゲート実行中】`0件）。7/25の「読み取りはrawが生きている」メモと対で覚える。

- **⓪-🚫Q29 実行＝検定不能でクローズ・2026-09頃に1回だけ再実行（7/26 14:41）**
  - **結果**: 有効日278日・分割2024-02-07・train140/holdout138 → **ブロック 7/7（要8）＝検定不能**。設計時の予測は8/8だった。
  - **予測が外れた原因＝見積もり器のバグ**: `_q29_power_design.load_events()` が**末尾のホライズン未解決分を数えていた**（284日と予測→実際278日）。下限ぴったりの設計だったのでこの6日が成否を分けた。**修正済み**＝該当ホライズンの列が実在すれば実測欠損で切る（銘柄ごとの欠測も拾う）→ 実測と完全一致。回帰テスト②b で 278日/2024-02-07/140・138/7・7 をロック（計22アサーション）。
  - **効果量は記録として残す**: train **+0.643%** / holdout **+0.681%**（同符号・大きさもほぼ一致）。Q28（60日 +2.34%/+2.47%）と合わせ**独立4推定がすべて正**。ただし p は両期間とも床値0.0003＝縮退の疑いがあり**「有意」とは言えない**。
  - **⚠️ ここで `min_ctl` を下げれば成立してしまう**（3分位/min_ctl=15で9/9・10で10/10）。**しかしそれは効果量を見た後の操作＝Q28と同じ罠**であり、母集団も閑散期側へすり替わる。**やらなかった。**これが今回いちばん大事な判断。
  - **事前コミット**: 設計・合格基準を一切変えず、**有効日が282日に達した時点で1回だけ再実行**（現在278日・年約56日で増える＝目安2026-09）。**「毎月試して有意になったら採用」は optional stopping なので禁止＝再実行は1回のみ**。その1回でも8未満なら恒久クローズ。
  - **成果物**: `research/_q29_test.py`（統計本体は `samedate_diff_p`／`_pead_test` の関数を流用＝再実装せず）。イベント表は fwd10/mae10 を**加算的に**追加し、**既存11列が全行ビット一致**を機械検証（Q28の記録は不変）。fwd10 は 68,820行解決＝fwd60 より3,222行多い。
  - ⚠️ `hypothesis_queue.md` 26.2KB（予算14KB）。Q29 が閉じたので**次の declutter 候補**（手順は下の 7/26 設計節に記載）。

- **⓪-✅Q29 の設計＝事前登録まで完了（7/26 14:29・算出は `research/_q29_power_design.py`）**
  - **やり方の核心**: Q28 の失敗は「結果を見てから BLOCK_LEN を短くしたくなる」状況を作ったこと。だから **リターン列を構造的に読めなくした**上で設計した＝`load_events()` が `fwd60`/`mae60` を落として返すので、以降のコードは値を参照できない（テスト `_test_q29_power_design.py` 15件で検査。ブロック数の定義が `_pead_test` と全格子一致することも検査）。
  - **結果を見る前に判明した制約**: ①**fwd60 は分割日をどこに置いても成立しない**（最も均等な2023-12-31でも train4/holdout4 ブロック・要8）＝ホライズン短縮は不可避 ②縛るのは常に **holdout** ③決算シーズン単位のリサンプリングも不成立（四半期 train13/holdout7）。
  - **⚠️ 最大の落とし穴＝`min_ctl` を下げる案**: 日数は買えるが **母集団がすり替わる**。30→5 で増える332日は決算集中月が**13%しかない**（既存207日は77%）＝閑散期の薄い日が全体の62%を占める別物になる。**「有効日数が増えた」だけ見て緩めてはいけない**。
  - **採った設計**: 3分位・`min_ctl=20`・**fwd10**・`BLOCK_LEN=20`・**分割＝有効日の中央値（実測 2024-02-06）**。→ 有効日284日・**train143日/8ブロック・holdout141日/8ブロック＝両期間で成立**・決算集中月66%。**train/holdout 方式を捨てずに済む＝方法論の変更なし**。効いたのは「分割規則を均等に変える」ことと「fwd60解決を待たなくてよくなり末尾4,018行が使える」こと。
  - **不採用の代案も記録**: ⓐ全期間1本＋前向き検証（fwd20で10ブロック）＝holdoutを失う ⓑデータ待ち（fwd20で分割維持には有効日あと138日≒2.4年）。どちらも採用設計より弱い/遅い。
  - ⚠️ **ブロック数がちょうど8＝下限ぴったり**。再生成して8を割ったら**緩めずに `検定不能` で閉じる**（緩めた瞬間にQ28と同じ罠）。
  - **残作業は1本**: `research/_pead_events.py` に **fwd10/mae10 列を追加**して再生成 → `_pead_test.py` を凍結パラメータで実行。
  - **副次**: Q28 を `hypothesis_queue_archive.md` へ退避（キュー 29.7→24.0KB）。⚠️**退避は見出しごと消すこと**＝`### Q28` のスタブを残すと登録簿が「本文改竄」と誤検知する。さらに**ブロック間の区切り（`---`・空行）を残すと直前のQのハッシュが変わる**（Q25 で実際に起きた）。手順＝①`### Q<n>` 見出しから次の見出し直前まで丸ごと削除 ②区切りを他ブロックと同じ空行1行に揃える ③`_hypothesis_registry.json` に `"archived": 日付` を追記。KPI は 18本（生存8/棄却10）のまま不変を確認。

- **⓪-✅watch 10件の棚卸し＝完了（7/26 14:10・全証拠は `research/_watch_audit_2026-07-26.md`）**
  - **結論＝「データ調達待ち」で止まっている項目は実質ゼロ**。止めていたのは調達ではなく着手判断。事前の見立て「真に調達が要るのは粗利益率・自社株買い・COTの3件」は**2件が外れ**だった。
  - **着手可になった4件**: ①**EAP**＝カバレッジ確認は `_pead_events.csv` で完了済み＝前窓を取るだけ ②③**管理先物型TF／オールウェザー**＝Yahoo実接続で月次4資産が20〜26年揃う（^GSPC 1984-12〜/^TNX 1985-01〜/GC=F・CL=F 2000-09〜/TLT 2002-08〜/DBC 2006-03〜） ④**COT逆張り**＝CFTC公開API（**キー不要**）で 1986-01〜2026-07 の週次133列を実接続確認＝取得スクリプト1本のみ。
  - **原型不可・近似可 1件**: 自社株買い＝TDnet公表日は無いが `TrShFY`(82.7%充足)＋`DiscDate`(100%)で**実行の四半期開示**を観測できる（300銘柄で変化3,147回）。**「公表後」でなく「開示後」＝別仮説なので新Q番号で登録**。
  - **検証不能 1件**: 粗利益率（Novy-Marx）＝107列を実査し**売上原価/粗利は本当に無い**（`Sales`86.0%/`TA`86.3%/`OP`84.7%/`NP`86.3%/`Eq`86.3%/`CFO`44.1% は有り）。OP/TA 等の近縁は可能だが「粗利が優れる」という主張自体が比較対象を欠く＝**「待ち」ではなく恒久的に不可**。
  - **⚠️ 持ち帰り**: 「調達待ち」は**主張であって観測ではない**。状態として書いた時点で誰も再確認せず固定される。watch に入れるときは「**何を確認したらブロッカーが外れるか**」を確認可能な形で書く。ブロッカーは①恒久的に不可 ②1回の作業で外れる ③判断待ち の3種類があり、同じラベルで並べない。
  - **副次修正**: Q28 の状態が `⏳未着手` のままで `mw evolve` がクローズ済み仮説を「次候補」に出し続けていた。**`🚫検定不能` を凡例に新設**して修正（`❌棄却` にすると「棄却された」ことになり生存率KPIが歪む＝`_doctrine_check.py` は ✅🛡/❌/📊 しか数えないので🚫はどこにも入らないのが正しい）。修正後＝候補から消え、KPI は 18本（生存8/棄却10＝44%）のまま不変を確認。
  - ⚠️ `hypothesis_queue.md` が **25.1KB（予算14KB）**。Q28ブロックは Q29 設計の材料なので今は残す。**Q29 登録後に Q28 を `hypothesis_queue_archive.md` へ退避**するのが自然な締め（手順＝ブロック移動＋`_hypothesis_registry.json` に `"archived": 日付` を追記。怠ると `_doctrine_check.py` が warning を出す）。

- **⓪-✅autopublish の topicキュー補充＋枯渇の番人＝完了（7/26 13:54）**
  - **#3 は誤検知だった**: `charts.html` の `<title>`/description/og/twitter はライブで既に「150年価格チャート＆投資史年表」。手元の `charts.html` が **5/6 生成の古い成果物**（6コアHTMLはSYNC禁忌＝ローカルは更新されない）を見ての誤判定。**生成物のローカルコピーで判断しない＝ライブか生成スクリプトを見る**。残っていたのは CLAUDE.md のサイト構成表と market-news スキルの2箇所のみ＝修正済み。7/25 の残1だった `youtube-summary.html` も bare「50年」0件で解消を実測。
  - **#4 はバグではなく本当の枯渇**: topicキュー #1〜#24 をライブ `guides.html` と突合して **24/24 公開済み**を確認。`AUTODRAFT_GUIDE.md` が「該当が無ければ新規生成しない」と定めているので、7/20〜24 の連続スキップは**仕様どおりの停止**（＝エラーが出ないので誰も気づかない）。
  - **補充15件（#25〜#39）**: emergency-fund / earnings-season / financial-statements / overnight-gap-risk / overconfidence / market-participants / stock-split-buyback / sns-information-literacy / margin-trading / commodity-basics / correlation-risk / ipo-basics / reit-basics / market-hours / sunk-cost。**全件を `check_guide_draft.py` 検査7（トークン集合の同一/包含）と同一ロジックで既存199記事に機械突合＝RED 0件**。主題が近い4件（margin-trading／correlation-risk／sns-information-literacy／sunk-cost）は行内に「本記事はここに限定し既存記事へ誘導」の棲み分け指示を明記。
  - **⚠️ 見つけた落とし穴（記事系routineの指示を書くとき必読）**: クラウドの routine は **`research/` 配下や `_` プレフィックスのローカル専用ファイルを読めない**。当サイト独自の実測値（勝率・件数）を本文に書けと指示すると**出典を確認できないまま数値を書く**ことになる。→ キュー冒頭に「独自数値は公開済みページに載っている場合の引用に限る」を明記した。
  - **番人＝`check_automation_health.py` §⑤**（`check_topic_queue`）: キュー表から key を抽出→GitHub の `guides.html` と突合し、未公開が `QUEUE_MIN_REMAIN=5` 未満なら warn＝Issue。実データで **push前 0/24（＝停止中を正しく検知）→ push後 15/39 ✅** を両方確認。テスト `_test_topic_queue.py` 12アサーション全緑（表以外のバッククォート除外・`guide-alpha-extra` での部分一致誤判定なし・表破損時の分岐 を含む）。
  - sync 242成功/0失敗。反映確認＝raw で3ファイル（`check_automation_health.py`／`drafts/AUTODRAFT_GUIDE.md`／`CLAUDE.md`）。**翌朝 05:30 の autodraft-article が #25 `emergency-fund` から再開**する見込み。

- **⓪-✅ナビ文言「50年チャート」→「150年チャート」一括更新＝完了（7/25 21:55・全文は SESSION_ARCHIVE.md）**
  - 結果: 242箇所/223ファイル反映・sync 242成功/0失敗・Contents API でクラウドレーン110本。残1の `youtube-summary.html` も 7/26 に解消を実測。
  - **⚠️ 再利用する教訓**: ①一括置換のキーは **`📈 50年チャート` の完全一致**に限定する（`50年` の素朴なgrepは `250年`/`1950年代` に誤ヒットして `2150年`/`11950年代` に壊す） ②`generate_market_news.py` の更新履歴に残る「50年チャートを…へ拡張」は**履歴の記述なので変更禁止** ③sync の🚫staleは `--force` を直に叩かず**リモート最新に自分の編集を乗せ直す**（この日それでクラウド公開の記事カード消失を回避）。
  - **⚠️ 環境メモ**: `api.github.com` だけが TCP443 到達不能になる時間帯がある（`github.com`/`raw`/ライブは正常）。**進捗実測は raw で行い、書き込みは窓が開いた瞬間に流す**。再利用ツール＝`_relabel_remote_push.py` / `_relabel_api_targets.json` / `_relabel_live_state.py`。
- **⓪-🚫PEAD Q28＝検定不能でクローズ（7/26 08:58・全文は SESSION_ARCHIVE.md／仮説本体は `research/hypothesis_queue_archive.md`）**: 材料は全部手元にあった（＝「調達待ち」は誤り）。イベント表 `research/_pead_events.csv` は再利用資産。**⚠️実装の罠3つ**＝①合成データを「都合よく単純」にすると検査したいものが値として区別できない（entryタイミングが無検査で全緑になった） ②`samedate_diff_p` の戻り値は3-tuple `(est, p, 有効日数)`・判定に使うのは `est`（同ファイルの `block_boot_p` は float なので取り違える） ③blowup を期間跨ぎで比べない。続きは Q29 の設計/実行節へ。
- **⓪-✅レジーム転換検知オラクル＝稼働（7/25・全文は SESSION_ARCHIVE.md）**: 4状態(UP/DOWN×HIGH/LOW)の日次判定が稼働し `mw evolve` に表示（現在 UP_HIGH）。テスト21件PASS・2008年秋は61日全て DOWN_HIGH で妥当性確認済み。**凍結パラメータ（ヒステリシス21営業日/ボラ窓60日/分位窓750日/MA200/split=2024-12-31）は結果を見る前に選んだもので、変更は修正でなく新Q番号での再登録**（`_doctrine_check.py` が状態JSONの `frozen_params` を検査）。Q27第1段は**着手条件待ちで未実行**＝対象が2系統のみで収穫が薄いため（条件と設計は `research/hypothesis_queue.md` の Q27 が単一の真実）。
- **⓪-✅期限到来の確認2件＝両方クリア（7/25朝・全文は SESSION_ARCHIVE.md）**: ①#050 にチャート風図解は入った（ライブ実測でインラインSVG3本）＝**7/24夜のプロンプト改定は初適用回で機能＝調整不要** ②`drafts/REVIEW.md` の🚩は新規なし（3件はすべて7/8付の既存分）。#050は verify 6/6緑・Opusコンプラ🟢白・独立Opus🟢白で自動公開完了。
## 📎 運用メモ

- 作業フォルダ: `C:\Users\info0\OneDrive\デスクトップ\新しいフォルダー` ／ GitHub: `invest-ai-info/marketwatch-ai`(main)
- 運用は **`python mw.py <cmd>`** が単一入口（check / publish / sync / **deploy [--trigger]** / trigger <wf> / status [wf] / **issues** / **audit** / routines）。`mw routines` で全 routine ID 一覧。
- 🆕 **ループ・エンジニアリング土台（2026-06-23・決定論コマンド＝トークン0）**：②`mw issues`＝open health-check/automation-health Issue 一覧（トリアージの土台）。③`mw audit`＝guide記事の改善候補スコア化（desc短/本文短/内部リンク少/JSON-LD無）。**判断部分だけ上限付き `/loop` でモデルに渡す**設計。`/loop` レシピ＝②「mw issues→最大3件診断＋提案(自動適用しない)→STOP」／③「mw audit→最弱を1本改善→白確認→publish、最大3本/回、score≥2が尽きるかで停止」。**🔑調査結果（2026-06-23）＝audit最弱11件は全部すでに `noindex,follow` 済み**（週次振り返り/週次戦略/月次の自動生成は薄ページAdSense対策で既にインデックス除外＝`auto_weekly_review.py`:287 / `auto_weekly_strategy.py`:378 / `generate_monthly_report.py`:291）＝**AdSense薄コンテンツ対策は完了済み**。よって `mw audit` を **noindex対応**に改修（noindex薄ページは別枠カウント＝改善対象外）→**インデックス対象81件中 改善候補0件＝公開コンテンツは健全**と確認。底上げ不要。
- 🆕 **`mw deploy`（2026-06-23）＝自己修復デプロイ（決定論・モデル不使用＝トークン0）**：sync を ❌throttle 時に backoff して**最大5回**再試行・🚫staleは即エスカレ・成功/上限/合計15分で必ず停止→任意で workflow 起動(`--trigger`)→ライブ200検証。上限は `mw.py` の `DEPLOY_*` 定数で固定＝構造的に永久ループ不能（今日の api.github.com throttle 手動リトライを自動化）。
- 同期は `python sync_to_github.py`（＝`mw sync`）。staleガードに 🚫 されたら「先に最新を取り込む（reconcile）」か、意図的なら `--force`。workflow 手動起動は `mw trigger <wf.yml>`。**ローカルは UTF-8 強制**：`$env:PYTHONUTF8="1"`（PowerShell）。
- routine 操作: schedule スキル → `ToolSearch select:RemoteTrigger` → RemoteTrigger（list/get/update/run）。クラウド routine（`signal-lab-daily`／`news-daily-auto` 等）はこれで管理。
- ⚠️ ローカルは GitHub と未同期なことがある（OneDrive）。**真の状態は GitHub／ライブを見る**。token は `market-news-config.json`(.json)。
- ユーザー北極星：投資家全体の底上げ／サイト・SNS 年収1000万／個人投資成績 年収1億。
