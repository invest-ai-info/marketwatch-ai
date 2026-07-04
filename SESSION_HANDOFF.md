# 🔖 セッション引き継ぎ（最終更新: 2026-07-04 未明）

新セッションは **このファイル＋ CLAUDE.md ＋ auto-memory（MEMORY.md 経由）** を読めば文脈を復元できる。
2026-06-17 以前の詳細履歴は **SESSION_ARCHIVE.md**（保管庫・後から辿る検索用）へ退避した。

---

## ✅ 7/2夜〜7/3未明の追加作業まとめ（詳細は auto-memory 各ファイル）

- **巨匠仮説キュー始動**（[[project_masters_queue]]）：**#1グレアム6基準＝4.5万観測で検証・スコア単調・暴落確率24%→4%の防御実証**→`guide-graham-001.html` 公開済（コンプラ白・品質レーン通過・新カテゴリ「巨匠の教え検証」）。🛡グレアム列を個人ダッシュボードに搭載（`_jp_graham_now.py`→dashboard）。**#2ラリー・ウィリアムズ＝4本全滅**（ボラブレイク両期間-0.08%一貫・記事化は未・良ネタ）。次=#3オニール/ミネルヴィニ。
- **ギャップ法則研究 確定**（[[project_jp_open_edge]]）：再現則は**ストップ高引け(+3.7/+3.3%)とストップ安引け(-5.1/-3.5%)の2つだけ**。髭特徴は組合せでも不再現＝終了。
- **及川圭哉(FXism)調査・検証**（非公開・`research/oikawa_fxism_methods.md`）：手法4本柱を体系化。検証可能な外形3仮説(シリーズ揃い/欧州時間/FX押し目)は**当エンジンデータで不支持**＝エッジは裁量部分。オーナーの実取引23件分析＝**勝率47.8%×ペイオフ3.15×PF2.89の損小利大型**（メンターと逆の型で+EV。勝率追いは期待値を壊すリスク）。**MT4過去履歴は消失＝7割実績は検証不能。ロンドン時間トレードは退職後に再開予定**。YouTube要約に11ch目「FXism 及川圭哉」追加済。
- **経済カレンダー精度**（[[project_marketwatch_calendar_bug]]）：7月分の誤り修正（CPI 7/14・ECB 7/23・日銀7/30-31・雇用統計8/7）＋json7月分12件追記＋**決定論バリデータ新設**（check_site_consistency＝雇用統計金曜/土日検出/FOMC公式照合/ECB木曜・未来日付のみ）→即9/4・12/17の誤り2件検出・修正済。
- **⚡トークン効率ルール新設**：CLAUDE.md に6箇条＋文書予算（CLAUDE≤32KB/HANDOFF≤30KB/MEMORY≤4KB）＋declutter監視で強制。MEMORY.md 7→3KB・本ファイル31→22KBにスリム化済。
- **🆕 規律ギャップ・ループ新設（7/3）**：`mw discipline`（`_trade_discipline_check.py`・SYNC外）＝my-trades.json×ルール5項目（R2指標持ち越し/R3指数重ね張り/R5 SL未設定/R-L損切りずらし>1.3R/JP✕エントリー）×JPカード履歴を決定論突合→`_discipline_report.md`（EVダメージ順）。`jp_daily.py` が毎朝◎○✕を `_jp_card_history.jsonl` に追記（同日置換＝冪等）。**初回実測＝R3株指数重ね張り8件(-2.2%pt)・SL未設定2件・FOMC持ち越し2件・直近10件は勝率30%/PF0.36と型崩れ**。週次 /loop レシピ＝「mw discipline→逸脱トップ3診断→STOP」（発注・ルール変更は自動でしない）。測定不能3点（¼Kelly上限/建値ストップ/実スリッページ）はGoogleフォームに口座残高・予定価格欄を足せば解消。**→オーナー判断で前向き検証は保留＝休眠アーム済み**：①事前登録済み仮説「遵守取引＞逸脱取引」（FORWARD_REG_DATE=2026-07-03・N≥30∧両群≥8で自動判定表示・checker はGitHub側my-trades優先読み）②`_jp_health_check.py`（平日8:00番人）が取引件数の増加を検知したら `規律ループ_取引再開_検知.txt` をOneDriveに作成＝**取引再開したら自動で起こしてくれる**（基準=`_discipline_state.json`・発火テスト済み）。それまで人間もClaudeも何もしなくてよい。
- **🆕 三重監査＝検証設計/文書/バグ（7/3・Fable初仕事）**：**①signal-lab方法論の穴4つ**＝(1)相関シグナルの独立扱い（SE=sd/√n・同日複数発火25%＝実効N過大→FDR通過過多。jp_open_analysisは日付クラスタbootstrap済で自家基準不統一）(2)holdoutの遡及汚染（2021+は過去の探索で接触済・grid次元tierも結果を見て追加＝擬似OOS。真の砦は前向きN）(3)トラッカー逐次検定＋ラチェット（毎日CI判定＝α膨張・promoted/rejected固定）(4)expired完全除外（closed()=tp/slのみ＝meanRが解決条件付き期待値）。JPモメンタム側は合格（翌バーOpen・あいまいバー保守SL・打ち切り除外・netR済）。**②文書乖離5件→4件修正しsync済**（AUTODRAFT/NEWS_DAILYガイド nav9→10・CLAUDE.md月次cron 1〜3日・MY_TRADING_RULES実績を7/3再計算に更新）。**③静かに壊れるバグ10件検出**＝最重要3件が未修正：jp_daily心拍が工程失敗でも書かれ健全性が偽陽性（+古いsizing_planでカード履歴汚染）／mw.py `_run_capture` cp932デコードで🚫stale検知不能／build_jp_rankings部分失敗でも偏ったランキングをexit 0公開。他=1mo固定取得の欠損穴・run()エンコーディング・tracker生json.load・sync欠落ファイル成功扱い・祝日except誤アラート。**当日実装分2件（前向き境界・基準低下）は修正済み。残りはオーナー判断待ち**。**→同日夜に修正実施**：①jp_daily=致命工程(②⑤⑥)失敗時は心拍を書かない＋失敗バナー＋sizing_plan古date検知でカード履歴追記スキップ＋run()/tracker読みの堅牢化 ②mw.py `_run_capture` encoding明示 ③**sweep/trackerに日付クラスタ・ロバストSE導入**（CR0×G/(G-1)・決定論・各日1件なら従来一致＝単体テスト済）＋**trackerチェックポイント検定**（判定はNがmin_n倍数越えの時のみ・last_eval_n記録＝覗き見バイアス抑制）→sync済・今晩routineから有効。**クラスタ補正で再スイープ＝FDR通過26→20・holdout合格11→7**（脱落=指数×逆張り/ロング全般/runway非阻害×L等の広く薄い仮説。残存=メタル/BTCロング・other_fx回避）。**→方法論②もオーナー決定で解決（7/3夜）＝脱落4本（index_revL_1d/unblocked_long/long_all/long_1d）のN30緩和を剥奪**：`HOLDOUT_REVOKE_2026_07_03` 定数＋apply冪等適用（GitHub側tracker.jsonの旧pass=Trueも次回updateでFalse化・holdout_note付与・N80復帰）。単体テスト済（剥奪/維持/冪等/N80）・sync済（commit d608c89）。**次回 signal-lab-daily（明朝06:10）のtracker表示で 🏁 が7本になっているか確認**。**→残改修2件も同夜完了（オラクル不変・sweep側・commit 9945d5f）**＝`--itt`(expired15.1%を0R算入・exp%列常時表示)＋`--net`(スプレッド控除・FX=pip絶対/他=価格比%・SPREAD_PCT概算表は実約定で要更新)。**頑健性ラダー＝グロス7→ITT7→ITT+net6本**（メタルロング/other_fx回避は全モード頑健・**btc_all_1dはコスト込みで脆弱**＝緩和剥奪は保留・要オーナー認識）。**→7/3深夜の追加バッチ**：①build_jp_rankings に部分失敗ガード（取得<80%なら書き込まずexit 1＝偏ったトップ20を公開しない・commit bfdae43）②月初レビューは7/1実施済みと確認（02/03反映済・追加作業なし）③jp_daily増分取得をキャッシュ経過日数でレンジ自動拡大（1mo→3mo/6mo/1y/5y＝長期停止後の恒久欠損を封鎖）④autodraftキュー⑫〜⑯補充（金利債券/単複利/ETF投信/注文方法/PER・PBR・commit 15cb421）⑤**JP前向きトラッカーに横断展開**＝行permutation→日付クラスタbootstrap（副産物＝赤字回避holdout p 0.043→0.150と判明＝JP側も水増しが実在）＋チェックポイント検定（last_eval_n）。実データ走行OK。⑥[低]バグ2件も修正＝sync欠落ファイルを🚫扱い(missing一覧表示)／番人の休場リスト取得不可時は検査スキップ(誤アラート防止)。⑦**巨匠#3完了**（`_jp_masters3_screen.py`＝ON1新高値/ON2 RS/MV1トレンドテンプレ/MV2 VCP・レイク506万行）＝**4本とも事前登録基準❌（train p0.12-0.50 × holdout2025+は全勝 diff+1.6〜3.3% p≤0.003＝レジーム依存の教科書例）**。採用せず・詳細は[[project_masters_queue]]。**⑧巨匠シリーズ記事#2を公開**（`guide-masters-002-trend.html`＝LW+オニール/ミネルヴィニの8仮説・全ゲート通過＝数値照合GREEN→コンプラOpus白→品質⚠️1修正→独立白→publish→HTTP200確認済み）。⑨[低]バグ2件修正（sync欠落ファイル🚫化・番人の休場リスト取得不可スキップ）。⑩**収益初弾＝リードマグネットv1作成**（`mw-checklist-v1.pdf`＝発注前60秒チェックリスト・A4/10項目・游ゴシック埋込・免責入り・公開記事の一般化のみ＝白設計。生成=`make_lead_magnet.py`。**非公開のまま＝オーナーがGoogleフォーム作成→URL共有で、コンプラ監査→SYNC→CTA設置に進む。手順書=`MAGNET_SETUP.md`**）。
- **自動化の精度点検（7/3未明）**：①no_plan 282件＝warn系のみ発火の**設計仕様と判明（バグでない）** ②**signal-lab-daily routineを更新＝tierフィルタ解禁**（selection.tier がclaims/研究日誌で使用可に）・手本015化・nav10・🏁N30注記 ③**indicator-result routineを厳格化**＝アグリゲーター(tradingeconomics/investing/forexfactory/fxstreet)と個人ブログは裏取りに数えない・満たなければverified=false ④寄り付きロガー欠測検知を `_jp_health_check.py` に追加（前営業日照合・祝日除外・アラートファイル） ⑤generate_market_news はstaleガード作動→reconcile PUTで反映（commit 199bfa80・.sync-cache baseline整合済）。

---

## ✅ 研究の高速化3点＝時間分割ホールドアウト／J-Quants日足レイク／寄り付き分析の事前登録（2026-07-02）

「シグナル/日本株検証をもっと速く・精度高く」の実装デー。
- **①signal-lab に時間分割ホールドアウト**：`signal_lab_sweep.py --split 2021-01-01`（発見=2020以前のみ・2021以降は探索未接触の検証専用）。**初回＝FDR通過26本→合格11/脱落15（過学習検出の実証）**。❌注目＝**指数×ロングはholdout不合格**（R+0.05・CI跨ぎ＝今のレジームのエッジ）。**事前登録ルール＝ホールドアウト合格は前向きN 80→30 に緩和**（`signal_lab_tracker.py` PROMOTE_MIN_N_HOLDOUT・結果は `HOLDOUT_2026_07_02` 定数に固定→GitHub側tracker.jsonへは次回 update が冪等適用）。sweep/tracker/SOP同期済。
- **②前向きN診断**：tf=1d は18銘柄で発火約4本/日。狭い仮説は枯渇（メタル×L=16日で発火5・指数×逆張り=発火0）。**根本策＝1dスキャン銘柄拡大はオーナー判断待ち**（エンジンが4hメール版と共有のため。1d限定リスト分離が安全案）。⚠️`outcome='no_plan'` 8/60件が前向きNに入らない＝原因未調査。
- **③J-Quants 日足データレイク**：`/v2/equities/bars/daily?date=` は **Lightプランで使える＝1コール全銘柄約4,400行**（6/24の「株価はプラン外」は誤り）。範囲=直近5年ローリング（2021-07-02〜）。`_jp_jquants_daily_lake.py`（SYNC外）→`_jq_daily_lake/`に約1,225営業日を蓄積（調整後OHLCV・売買代金・ストップ高安・廃止銘柄込み＝生存バイアスフリー）。読み出しは `load_lake()`。増分更新=引数なし実行（週次推奨）。
- **④寄り付きロガー分析を事前登録**：`jp_open_analysis.py`（SYNC外）にH1〜H6固定＋日付クラスタbootstrap＋BH-FDR＋**実行ゲート（各群N≥100/20営業日）**。検出力実測＝差0.5%検出に約31営業日。
- **⑤ギャップ法則研究（進行中）**：`_jp_gap_rule_study.py`（SYNC外）＝「値上がり/値下がりトップ20から翌朝急騰を分けられるか」。**train暫定＝ストップ高引け(ul)が支配的（P(gap≥+3%)=48% vs 6%）／ストップ安引けは翌朝-5.4%**。ホールドアウト（2025以降）はレイク完走後に確定。⚠️S高張り付きは比例配分で「買えない」＝保有者の法則である点に注意。

## ✅ ルール文書の棚卸し・修復（2026-07-02）

監査エージェントで全ルール文書を点検→乖離を修正：CLAUDE.md「13銘柄→18銘柄」「filterキーにtier追加」「jp-rankingsは朝でなく夕16:40/17:10」「リンター説明9→10ボタン」／sync_to_github.pyコメント時刻／market-newsスキル（~/.claude/skills）のページ構成を6コア+全体像参照に更新／**作業フォルダ直下の旧 `SKILL.md` を削除**（claude.ai時代の遺物・無参照確認済・OneDriveごみ箱から復元可）。

---

## 🇯🇵 日本株：EV最速化ロードマップ＝全6施策 完了（2026-06-26/27）

ネットR／分数ケリー／赤字回避統合／外国人フロー／発注規律カード（平日6:00自動+番人8:00）／続伸×risk_offトラッカー——**詳細は非公開 `JP_EV_ROADMAP.md`・SESSION_ARCHIVE.md（2026-07-04退避）・auto-memory [[project_jp_doublebagger]]**。残＝前向きN蓄積が律速（昇格アラートはカード上段に自動表示）。

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
| **発注前ルールの遵守を数値監視** 🆕 | `_trade_discipline_check.py`（`mw discipline`・週次 /loop） | 指標持ち越し/指数重ね張り/SL未設定/損切りずらし/JP✕を **EVダメージ順に可視化** |
| sitemap 全記事網羅 | `generate_market_news.py` の `build_sitemap_xml` | 全 guide を自動収集・手動編集不要 |

🆕＝2026-06-20 追加（B＝カバレッジ番人 ／ C＝sync staleness ガード）。新ルールはこの表に1行＋チェック1個で増やす。

---

## ⚠️ 絶対遵守（事故防止）

- **SYNC禁忌**（ローカルから絶対 push しない＝routine/cron/generate が GitHub 側で生成）。**正は CLAUDE.md の SYNC禁忌リスト**。代表例：
  6コアHTML（index/calendar/charts/vix/market-health/hot-assets）／`signals-log.json`／`technical-alerts-history*.json`／`track-record.html`／political系／youtube系／`fundamental-context.json`／`weekly-levels.json`／`weekly-zone-plan.md`／`sitemap.xml`／`weekly-strategy-context.json`／`indicator-result.json`／`signal-lab-tracker.json`／`signals-log-backtest.json`／`article-ideas.md`／`daily-preview.md`／`political-digest.md`／`compliance-scan.md`／`site-qa-report.md`／`panic-scan.md`／`drafts/draft-*`・`drafts/news/*`・`drafts/sns/*`
  → `mw check`（`check_site_consistency.py`）が SYNC_FILES への誤混入を、sync の staleガードが「古いローカルでの上書き」を、それぞれ自動で止める。
- **SYNC対象（OK）**：`*.py`（※`sync_to_github.py`・`mw.py` 等のローカル専用ツールは GitHub 未追跡）／`.github/workflows/*.yml`／個別 `guide-*.html`／`guides.html`／`robots.txt`／`my-trades.json`／`memory/*.md`／各 docs。
- 記事追加は **`python mw.py publish ...` → sync → workflow → ライブ確認**。公開前に compliance-reviewer(Opus)監査・教育トーン・特定銘柄の買い推奨は書かない・kinsho-v1 免責・10ボタンナビ。手動時も `mw check` で push 前点検。
- ネット不調時は無限リトライせず、ブラウザで手動 trigger を依頼（最大3〜5回）。

---

## 📌 アクティブな宿題

### 🔜 次セッションで最初に確認（在flight・2026-07-04更新）
- **①´【7/4昼に確認済→要再確認7/5朝】tracker.jsonコミット漏れ事故と対策**：(a)は**不合格だった**＝routineは028/029を公開したが **signal-lab-tracker.json のコミットを7/3・7/4と2日連続で漏らし**（8-1のadd例に無い＋台帳には「トラッカー[n]更新」と虚偽記載）、GitHub側trackerは7/2朝のまま＝剥奪/クラスタSE未反映。routine本文の修正はAPIペイロード上限で不可→**コード側3ガードを実装・sync済**：`signal_lab_tracker.py`/`signal_lab_sweep.py`が出力末尾でadd必須を明示指示＋`finalize_signal_lab.py`に`_tracker_gate`（git内でupdated_at≠当日 or 未コミットならexit 1＝公開拒否・4パス単体テスト済）＋`check_automation_health.py`鮮度監視に tracker.json 26h/warn 追加。**7/5朝06:10の運転で tracker コミットが復活するか要確認**。⚠️追加発見＝**🏁は7本でなく5本が正しい挙動**：`metal_all_1d`と`other_fx_long`は既存 `auto_group-metal`/`auto_direction-long_group-other_fx` とfilter重複でregisterスキップ→holdout_passがどこにも付かない（両者は既にN≥80到達済で緩和は実質無意味だが、metalは kind=gate vs edge の向き矛盾あり）＝**オーナー判断待ち**（auto_*側にholdout注記を移すか・5本で良しとするか）。(b) indicator-result新基準は**合格**（7/1以降の全5件が一次ソース入り・アグリゲーター単独verified=trueは6/30以前の旧分のみ）。
- **②リードマグネット公開待ち＝オーナーのGoogleフォーム作成待ち**：URLが来たら `MAGNET_SETUP.md` の Claude作業（コンプラ監査→PDF SYNC→CTA設置→X導線）を一気通貫で。
- **③AdSense 再審査の結果**：6/27申請済（[[project_adsense_review]]）。承認/却下を確認。却下ならニュース記事もnoindex等の next step。
- **④jp_daily改修後の初回平日運転（月曜7/6朝）**：6:00カード＝心拍の条件化/失敗バナー/カード履歴追記が正常か（`_jp_card_history.jsonl` に月曜分が1行増える）。8:00番人＝休眠チェック「💤取引23件」表示。
- **⑤巨匠キューの補充相談**：#1〜#3消化済み。次候補＝バフェット（質×割安の点in-time財務）/リバモア（ピボット）等をオーナーと選定→事前登録。
- **整理係**：`mw declutter` は7/3時点0件。月次 `MarketWatch_Declutter` が `DECLUTTER_REPORT.md` を出したら確認。

- ✅ 済（詳細は上の7/3まとめ・アーカイブ参照）：格言シリーズ無人化実証（7/1）／ニュース鮮度カットオフ（6/30）／ロイターRSS復活確認（7/3＝フィード健在・TOP3選外は正常）／JP朝カード初稼働＋番人（7/3）／FOMC結果の信頼性厳格化（7/3）／update-market-news concurrency（6/20）。
- ✅ **POLICY dict 更新＝完了（2026-07-04未明）**：日銀 0.75→**1.00%**（6/16利上げ）。米3.75/欧2.40/英3.75/豪4.35は6月会合すべて据え置き＝変更なし（FRB6/17・BOE6/17・RBA6/16をWebSearch＋fundamental-contextで裏取り）。次回会合=FOMC 7/28-29・日銀 7/30-31。朝7時の update-market-news から反映。
- 📉 **AdSense ＝2026-06-27 再申請済・結果待ち**（[[project_adsense_review]]）。次セッションで結果確認（上の在flight参照）。
- 🗓️ **`jp-stock-info.json` の四半期更新**（決算シーズン後に `python make_jp_stock_info.py` 再実行→`mw sync`。赤字/黒字フラグを最新決算へ。日次の値上がり率/売買代金は `jp-rankings.yml` が自動）。
- ✅ autodraft topicキュー ⑫〜⑯補充済（2026-07-04・金利債券/単複利/ETF投信/注文方法/PER・PBR＝毎朝05:30のroutineが順に消化）。
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
