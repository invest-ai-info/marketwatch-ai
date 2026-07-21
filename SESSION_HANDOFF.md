# 🔖 セッション引き継ぎ（最終更新: 2026-07-21）

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

### 🔜 次セッションで最初に確認（在flight・2026-07-22向け）
- **⓪-7/21完了✅（7/20夜計画①〜④を全消化）**: ①06:10確認=tracker51仮説・`state_*`5本出現（edge3=holdout_pass True/gate2=False・正直記録どおり）・コンボ3本tracking・index_long_live=promoted N221（CP240接近＝今週strike2→降格見込みの想定内） ②**特別記事公開=`guide-indicator-combos.html`**（🧪AIシグナル研究日誌・独立Opus監査🟢白/黒ゼロ・数値は全部コード突合＝BT18,099件13,044/5,055・SVG3枚・ライブ200/index履歴/guidesカード確認済み） ③**「↑上に戻る」一括適用完了=`apply_back_to_top.py`新設**（単一ソース=generate_market_news.pyのBACK_TO_TOP定数をregex抽出・SYNC入り静的HTML104本へ冪等注入・番人に欠落warning追加・クラウド生成記事はテンプレGitHub側のため対象外。guide-investment-booksはbook-watch更新でstale→reconcile→--force定石で解決・ライブ確認済み） ④**Q21事前登録=出来高/人気×シグナル成否**（queueにSHA凍結・出目未見。H-V1=相対出来高3バンド×非FX9銘柄BT／H-V2=news_count 0 vs ≥3ライブ。可用性確認済み=news_countフィールド有・Yahoo日足出来高は非FX9で取得可）。
- **⓪-人気度 7/21午後✅（オーナー発案「人気銘柄の見分け方」→実装決定）**: **公開=🔥人気急上昇TOP20**（`build_jp_rankings.py`=Yahoo取得7d→3moに拡張・relvol=当日出来高÷直前20営業日平均・売買代金10億円フロア＝薄商い/軽い玉を公開面から排除・`hot`キー追加）＋`generate_market_news.py`の`build_jp_rankings_section`に全幅ブロック描画（「計測であり推奨でない」注記・過熱飛びつき不利の教育文・罠フラグは掲載しない=オーナー決定）。ローカル実走✅（人気1位リコー2.3倍・60行描画・モバイルCSS流用）。**✅ライブ初回確認済み（7/21夜）**＝定時2回(19:09/19:33 JST=cron遅延)がsync(19:45)より先に走り旧コード実行→大引け後20:30に手動trigger(jp-rankings→update-market-news)で解決・ライブ69,916字/hot20件/1位リコー2.3倍=ローカル実走と一致/注記・教育文表示確認。**📝発見=jp-rankingsのcommitはon:pushを発火しない**（GITHUB_TOKEN pushはon:push非発火の仕様・従来は遅延した夕方定時runが偶然カバー＝CLAUDE.mdの「即再描画」記述と実挙動がズレ。実害=反映が定時run待ちになる程度・対処要否はオーナー相談）。**非公開=Q22事前登録**（罠フラグ=(F1出来高スパイク≥5∨F5回転異常≥8)∧F2急騰≥25%/5日・F4軽い玉層別・F6ブームバスト前科・fwd20同日クロスセクション差・SHA凍結済み出目未見。「仕手の断定」は板/ティック無しで不能＝「仕手的形状の劣後」を検証。ロガー不要と判断=全フラグがレイクから遡及計算可能・材料なき急騰のニュース条件だけ将来のライブ蓄積で別Q。合格したらmw screen非公開列→サイト公開は弁護士後）。
- **⓪-EVアップ 7/21夕✅（オーナー承認「お薦め順で」＝①1d拡大②mw size実装済み・③EA修正は次のEAセッション）**: ①**1dスキャン8銘柄拡大**（`SYMBOLS_1D_EXTRA`=HG銅/PLプラチナ/NG天然ガス/ZN米10年債/ETH/DAX/HSI/SOX・Yahoo日足可用性確認済み・^SOXは出来高無し=出来高系検出器は自然不発）。**1dレーン限定**（4h/1hメールは18銘柄のまま）＋**tracker側`LEGACY_UNIVERSE`凍結**（既存仮説の前向きNは18銘柄固定＝direction/state系フィルタへの母集団混入を遮断・🧊除外件数print付き）。ETHは週末ガード非変更=日曜06:20の1回のみスキャン外（集計5複製に触れない保守選択）。⚠️sweep探索は全量を見るため、拡張銘柄の新仮説はGROUPS正式拡張+新Q登録後に（tracker凍結中はN=0のまま＝コメント記載済）。**明朝確認=06:20 runが26銘柄で成功**（`mw status technical-alerts-1d.yml`・失敗ならautomation-healthが09:30にIssue化）。②**`mw size`新設**（`_position_size.py`=ローカル専用SYNC外+mw.pyディスパッチ）＝検証済み枠組みのCLI化: 既定1%/取引・R6相関合算2%ハードキャップ（THEMEはR6のRISK_THEME整合・ETH=BTCと同テーマ等の保守拡張）・全体5%目安（λ0.10）・戦略別参考上限（貴金属L2.0/株指数L0.4/暗号L2.0=λ0.10・楽観バイアス注記込み）。テスト5ケース✅（🟢/R6🔴/上限🟡/境界2.0%OK/入力エラーexit2）。例: `mw size --balance 3000000 --pos "GC=F,long,2650,2635" --mult "GC=F:100"`。
- **⓪-次の作業候補**: (a)✅人気急上昇のライブ確認=7/21夜完了（上の⓪-人気度参照） (b)**1d拡大の初回運転確認**（明朝06:20=26銘柄） (c)**Q21/Q22実行**（設計凍結済み） (d)**declutter**=DOCTRINE 25.5KB+hypothesis_queue 17.1KB=warning2件 (e)今週のstrike2降格→メール無音期間入りの観測（自動・介入しない） (f)**⑤EA修正8件**（次のEAセッション・オーナーと一緒に）。
- **⓪-A 7/19大改修の初運転確認＝7/20朝に①②✅完了**: ①06:10 run=コンボ3本(combo_hb_rsiob/combo_bbub_rsiob/combo_db_hb)登録✅(43→46仮説・全てtracking/holdout_pass=False)・**promote_strikes未出現はCP到達仮説ゼロの仕様どおり**(コード286-293行=CP時のみ書く)・strike1保持(index_long_live N212)・#045自動公開(指数×ショートgate逆転) ②4H定時=全success・**A修正稼働の実証=n_promoted 3→2**(gateがメール通行証から除外)・**D修正稼働=avoid_matched記録出現**・support_bounce初発火2件(BTC 1h・email=False=正常)・退役2タイプ発火0・メール0通=無音期間の方向どおり ③**今週中**=指数×ロングがN=240のCPでstrike2→降格→**メール無音期間入り**（昇格edge 0本=正常状態・手動介入しない。🛡ブロック表示の実物確認は次にメールが出る時） ④**≒7/27**=格言キュー枯渇→#25以降補充 ⑤**9/20以降**=15分足セッション追試（research/_fx_session_15m_scan.py再実行・事前登録済み） ⑥✅7/20=`/consolidate-memory`実施（MEMORY.md 9.4→4.0KB=予算内・詳細は各ファイル側に確認済みの上で索引をフック化）。
- **⓪セッション冒頭の新ルーチン＝`python mw.py evolve`**（DOCTRINE突合+キュー+トラッカー鮮度・トークン0）。⚠️**日付は作業の直前に必ずGet-Dateを取り直す**（7/15日付事故の教訓＝冒頭の値を使い回さない・auto-memory feedback_date_freshness）。
- **⓪-🔴オーナー判断待ち＝publish_article.py への日付ゲート追加提案**（記事の公開日≠今日JSTなら停止・`--allow-backdate`免除・signal-lab date_check と同型）。7/15の日付事故の恒久対策＝ゲート編集は人間専任のため承認待ち。承認されたら次セッションで実装。
- **⓪-C idea-scout-weekly**：✅7/20転記完了（7/19回の3件処理）＝**Q19祝日前プレミアム事前登録**（レイク取引日暦のみで検証可・EW日次リターン差・円環ブロックbootL=5・登録簿SHA記録済み・出目未見）／自社株買い公表後=watch（TDnet公表日データ調達が先）／決算前ドリフトEAP=watch（fins開示日の四半期カバレッジ確認が先）。slugs 3件追記済み。次回の受信箱確認=7/26(日)14:00運転後。
- **⓪-D 進化ループ続き**：**✅7/20 Q17実行済み**（`_jp_q17_accounting_screen.py`→`_jp_q17_summary.json`・DOCTRINE §3/§5結晶化・アンカー4件）＝**A2アクルーアル❌確定**（train同form-3.83% q=0.0003=Sloanと有意に逆＝「質は逆」レジームの拡張）／**A1資産成長=train合格+3.44%・crash 9.7vs15.6%の防御併走**だが**holdout=6formationでブロックboot縮退（T<L=13は循環回転で平均不変=p自動有意）＝判定不能→📌2026年10月頃(formation10本)に同一コード再実行**（覗き見しない）。**✅7/20 Q19も同日実行=❌棄却**（祝日前日EW差 train−0.066%/holdout−0.137%・両期間で方向逆・p≈0.58＝カレンダー効果はLW3/LW4に続き3連敗・DOCTRINE §3済）。**✅7/20 Q20アレンジDも実行=❌不合格**（下の⓪-E参照）。**次の攻め候補=growth_levers残（②b国外OOS／④promise audit／⑤プレイブック）or Q10（エンジン実装が先・優先度低）**＝攻めキューはほぼ完走・当面は前向き観察（Q7/Q11/Q16/A1）の答え待ちが主戦場。他の候補=growth_levers残（②b国外OOS／④promise audit／⑤プレイブック）・Q10（エンジン実装が先・優先度低）。**✅7/15消化済=記事#6公開・Q18❌**。TT3=月1回・Q11=毎月1-3日タスク自動。**8/1以降の最初のセッションで7/31 formation凍結を確認**（`mw evolve`のQ11行がformation 1/12になっているはず）＋**8月にmw screen📅列の初発火を確認**（Q1決算シーズン・元データ=J-Quants earnings-calendar・キャッシュ`_jp_earnings_calendar.json`）。**DOCTRINE 24.2KB=warning 1＝次のdeclutterで§3スタブ化**。
- **⓪-E 巨匠アレンジ枠=✅4候補完走（7/20クローズ）**：**A**=❌7/11（Q15単一資産超えず=記事#6素材）／**B**=Q13✅7/9／**C**=Q11✅7/11実装済（screener参考列だけ任意で未）／**D**=❌7/20（**Q20グレアム防御×PEG複合**=train ns→holdoutのみ有意=レジーム依存・blowupもtrainで対照並み=複合で防御一貫性が消える・複合の前科C1/C2に続き3件目・`_jp_q20_summary.json`）。
  ※「すでに生きているアレンジ」の整理も記事ネタ（赤三兵→連騰≥4危険ゲート・タートル資金管理→ATRベースSL/2%ルール・**G4逆張り→🔪回避フラグ（Q13）**＝原型のエントリーは死んでも部品は生きる）。
- **⓪-F 文書declutter**：7/15時点=HANDOFF 27.4KB（7/11節をARCHIVE退避）/queue 10.7KB（Q18退避）/CLAUDE 32.0/**DOCTRINE 24.2KB=warning1のみ残（次のdeclutterで§3スタブ化）**。以後もこの水準を維持（節が増えたら完了節をARCHIVEへ）。
- **⓪-H ⚡news-ticker**: ✅7/11朝確認=夜間毎時運転OK（updated 7/11 10:03・30件）。残1件=**「📰経済を既定で非表示（ボタンで表示）」は1行で変更可＝オーナーの好み待ち**（夜間はYahoo!経済由来の消費者ネタ多め問題）。
- **①巨匠シリーズ**：#6=7/15公開済み（Q15資産クラスDMの正直な❌）。次記事候補=「#7 割安成長（ズールー）×グレアム再訪」＝Q11前向き設計・Q12再監査が素材（両方完了済みでいつでも書ける）。
- **②TT3の前向き検証＝📊稼働中**（`_jp_turtle_tracker.py`・検定はブロックboot版に7/8改定・月1回チェック・初判定は10月頃）。
- **③防御スクリーン列＝✅適用済み**（`mw screen`の🛡防御列・7/7）。
- **⑤番人EA MW_Guardian＝実弾テスト未実施＋7/11監査で要修正8件**：次のEAセッションで（a)監査🔴3件+🟡5件を修正（`research/execution_audit_2026-07-11.md`対応ログ参照・R2持ち越し盲目/仮SL沈黙/SL削除無検知/magic無差別/AutoSL_TF=240等）→(b)MetaEditorコンパイル→(c)オーナーがデモ口座で試し発注→実挙動を一緒に確認＋表示リスク%vs手計算の1回照合。
- **⑥リードマグネット公開待ち＝オーナーのGoogleフォーム作成待ち**：URLが来たら `MAGNET_SETUP.md` の Claude作業（コンプラ監査→PDF SYNC→CTA設置→X導線）を一気通貫で。
- **⑦AdSense＝7/6再却下（確定）**：🔴**オーナー作業＝AdSenseコンソール[サイト]ページで却下理由の詳細を確認**→理由を見てから対応方針を相談（候補: ニュース/自動生成記事の追加noindex・コンテンツ拡充・再申請時期）。むやみにnoindexを増やすのは理由確認後。
- **⑧オーナー手動タスク2件**：(a) **X用アイコン `mw-logo-512.png`**（作業フォルダ直下・ローカルのみ）を @rx009898 のプロフィール画像に手動アップロード (b) 実機スマホでトップページ整理後の見え方＋タブのロゴを確認。
- **⑨相談したら進む事項**：(a) OGP画像のロゴ入り差し替え (b) ツール次候補＝DCA比較/NISA枠/ポジションサイズ（後2者はコンプラ設計繊細） (c) `btc_all_1d`のN30緩和＝コスト込みで脆弱の扱い (d) 🏁5本問題のauto_*注記移設 (e) リバモア検証（優先度低） (f) **triangle_squeeze（142発火・評価可能0件=warn専用ノイズ）の退役可否**＝コンボ条件次元の価値があるため7/19から保留中 (g) ⚡news-tickerの「📰経済を既定で非表示」＝1行変更でオーナー好み待ち。
- **整理係**：`mw declutter` は7/3時点0件。月次 `MarketWatch_Declutter` が `DECLUTTER_REPORT.md` を出したら確認。

- ✅ **POLICY dict 更新＝完了（2026-07-04未明）**：日銀 0.75→**1.00%**（6/16利上げ）。米3.75/欧2.40/英3.75/豪4.35は6月会合すべて据え置き＝変更なし（FRB6/17・BOE6/17・RBA6/16をWebSearch＋fundamental-contextで裏取り）。次回会合=FOMC 7/28-29・日銀 7/30-31。朝7時の update-market-news から反映。
- 🗓️ **`jp-stock-info.json` の四半期更新**（決算シーズン後に `python make_jp_stock_info.py` 再実行→`mw sync`。赤字/黒字フラグを最新決算へ。日次の値上がり率/売買代金は `jp-rankings.yml` が自動）。
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
