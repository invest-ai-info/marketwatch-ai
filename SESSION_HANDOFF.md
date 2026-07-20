# 🔖 セッション引き継ぎ（最終更新: 2026-07-19）

## 📧 7/19 シグナルメール改善A〜E（オーナー依頼「順番に」・完了）

**剖検**: 7/5昇格限定メール化以降の配信=指数×ロングのみ9通・7SL勝ち0（エッジ減衰6/22 R+0.67→+0.05の直撃）。**降格strike1は今朝06:10のrunで正常付与✅（7/18見張り事項②完了）**。格言#16も定時公開✅（見張り①完了）。
**A✅ kind=="edge"バグ修正**: `load_promoted_hypotheses()`がstatusだけ見てkind不問→**gate昇格（回避確定=metal×ロング7/14昇格・R-0.30）も「検証済みエッジ🏅」メールの通行証になる地雷**。実害ゼロは金銀逆張り系がemail_silentで上流ブロックされた偶然。1行修正+テスト3本。
**C✅ 昇格入口の対称化**（`signal_lab_tracker.py`・新規昇格のみ・不遡及）: ①基準合格**2CP連続**(`promote_strikes`)で昇格＝降格と対称（指数×ロングがN43-60の1回合格で昇格→平均回帰した実例への対処）②`holdout_pass=False`確定仮説はライブCIのみで昇格禁止（**None=許容**＝ライブ専用仮説を永久不能にしない設計判断・オーナー提案の「true必須」から意図的に緩和）③反証は従来1CP（保守側）。テスト11本（7/18降格ルール回帰込み）。
**D✅ メールへ回避情報併載**（表示のみ・送信可否不変・可逆）: 本文に🛡規律フィルタブロック（disciplineの算出をbody前へ前倒し=ログ記録と同一値を再利用）＋エッジ×回避gate同時該当時の⚠️警告最上部表示＋`promoted_gate.avoid_matched`記録。
**E❌ TP幾何=正直なヌル**（`research/_tp_geometry_counterfactual.py`・事前登録→1回だけ実行）: MFE近似はSL後反発混入（evaluate側は確定後再評価しない=MFE凍結が検知run窓）で不採用→**Yahoo 1hバー再取得のパス歩行シミュレーション**（同一バー両該当SL優先=評価器と同規約）。妥当性=シミュvs実ログ一致率**99.9%**(700/701)。4h train最良α=1.0×ATRでもペアΔ+0.030 CI[-0.053,+0.112]=0跨ぎ→**事前ルールで不合格＝TP短縮は改善しない**（holdout参考値は符号反転Δ-0.017でヌル補強・1hは全α悪化）。出力=`research/_tp_cf_summary.json`。
**sync済**: `generate_technical_alerts.py`/`signal_lab_tracker.py`＝local==main照合✅。research/*はローカル専用。
**👁次回確認**: ①次の4H定時=🛡ブロック表示+Technical Alerts失敗メールが来ないこと ②明朝06:10=新昇格ルールでtracker更新正常（promote_strikes/promote_blockフィールド出現＋**コンボ3本のブートストラップ登録が現れる**）③≈1週間後N=240で指数×ロングstrike2→降格→メール自動停止 ④降格後は昇格edge 0本=メール無音期間に入る（メール資格の次の候補はトラッカー任せ＝手動介入しない）。

**同日⑥ BT再生成インフラ＋出来高検出器（攻めキュー完走・sync済）**: `signal_lab_backtest.py`=バックテスト時は退役無効化（研究ログ全タイプ収録）・**再生成9分/回**・旧版は`signals-log-backtest-2026-06-16.bak.json`退避。再生成後スイープ=生存7本+過熱コンボholdout落ちが完全再現✅。**support_bounce: 1d=R-0.038ヌルだが4h×2年非FXリプレイ(signals-log-backtest-4h-nonfx.json)=R+0.065 CI[-0.02,+0.15]・40本/月→ライブN80まで≈2ヶ月＝labとトラッカーに委任**。**volume_climax_bounce新設**（RSI≤30×出来高2倍×陽線・非FX・record-only・テスト4本✅）=20年で14回だけの歴史的セリクラ検出器（リーマン/COVID等を全部拾う）＝**シグナルより環境フラグ向きの可能性・寿命管理の休眠ルールで誤退役させないこと**。次の4H定時からライブ発火開始。

**同日⑤ 切り番エッジ検証＝ダブル❌（#3バックログ正式実施・事前登録→1回・research/_round_number_edge.py=ローカル）**: 20年BT16,221決済に切り番近接を遡及計算（2有効桁00/50レベル・≤0.3ATR）。P1メタルL×切り番サポート=train差-0.089逆向き❌／P2 TP経路の切り番阻害=+0.036効かず❌・副次全q≥0.46・ライブ整合。**結晶化=市場が覚えているのは実反発価格(sr_runway実証済み)でありキリ番ではない**（1d粒度でザラ場反発は不可視の注記付き）。#3クローズ。**攻めの残キュー=①20年BT再生成(新検出器込み=support_bounceの20年成績が出る)②出来高スパイク検出器(非FX限定)**。オーナーは及川式5分足を実弾で実践検証中（サイト側の15分足実測=閑散帯回避+コスト1割超が前提知識）。

**同日④ FXセッション15分足スキャン（オーナー依頼・事前登録→1回・research/_fx_session_15m_scan.py=ローカル）**: FX9ペア×60日15分足×本番11検出器（数式import）=12,143トレード。**主要仮説✅=ロンドン>閑散が有意（差+0.144 CI[+0.07,+0.22]）だが、核心は「15分足は全セッションでスプレッド控除後マイナス」**（コスト中央値0.118R・ロンドン初動16-18もnet-0.128）＝標準テクニカルの15分足移植では勝てない。**最強の回避知見=閑散帯(2-7時JST)の順張り/過熱 net-0.635/-0.751**。及川ノート（research/oikawa_fxism_methods.md）に実測補遺を追記。**📌追試を事前登録=2026-09-20以降に非重複の新60日窓で同一コードを再実行**（合格=両窓で同方向CI下限>0・それまで採用判断しない）。

**同日③ シグナル寿命管理＋新指標（オーナー依頼・sync済）**: ①寿命ポリシーのコード化=`signal_type_lifecycle.py`（ローカル・事前宣言5分類。**live赤×bt黒の🛡罠6本=macd_golden/bb_upper_break/high_break/ma_golden/rsi_overbought/double_bottomは退役禁止**）②退役2本=`RETIRED_SIGNAL_TYPES`{double_top, first_pullback_long}（フラグ可逆・検出後一括除去・過去データ不変）③新検出器`support_bounce`（6/3検証サポ近接ロング59.6%/+0.485Rの実装化・record-only）④ファンダ次元`env`/`regime`をoracle/sweep/probeに解禁（初回=有意ゼロ・env=C+0.05/RISK_ON×L-0.17の示唆のみ・以後は毎朝のlabが自動探索）⑤**📋要オーナー判断=triangle_squeeze**（142発火・評価可能0件=warn専用ノイズ。コンボ条件次元の価値はあるため保留）。CLAUDE.mdのfilterキー一覧更新済み。**👁追加確認: 次の4H/1H定時でsupport_bounceの初発火がログに乗るか（メールは出ない=正常）**。

**同日② コンフルエンス検証パイプライン新設（オーナー依頼「最低2指標の組み合わせ」・4ファイルsync済）**: 固定オラクルに新filterキー**`signals_all`**（全シグナル同時発火・人間による正式拡張）＋sweepペア次元（train共起support≥40）＋trackerの`_filter_key`JSON化（リスト値filterのunhashableクラッシュを先回り根治）＋`COMBO_2026_07_19`冪等登録＋メールprobeに`signal_types`。**初回スイープ（20年1d・train/holdout・クラスタSE）＝ペア14本→train-FDR3本→全てholdoutで有意性消失**（高値ブレイク×RSI買われすぎ等の過熱モメンタム系・方向は維持だがCI 0跨ぎ・ITT/netはtrain頑健）→**holdout_pass=Falseで前向き登録**（Cルールでライブ運昇格は不可＝定点観測のみ）。「2つ以上なら良い」はライブで否定（count別avgRほぼ同一）・ダブル売られすぎはtrain赤字（R-0.15）。単体テストT1-T5✅。

## 👁 7/18 キオクシア監視＋格言キュー補充（枯渇解消）

**①監視銘柄ウォッチ新設（オーナー依頼・キオクシア285A）**: `_jp_health_check.py` に `check_watchlist()` 追加＝`_jp_watchlist.json`（ローカル専用）の銘柄をスクリーナーCSVの回避フラグ（danger≥1/🔪/⚡/赤字）と平日8:00+12:30に照合→**全解除 or 再点灯の遷移で `JP監視銘柄_状態変化_通知.txt`** を作成（両方向テスト済✅）。通知は「規律上の回避対象でなくなった」の機械的事実のみ＝買い推奨ではない。285A現況=⚡爆騰点灯中（7/16 CSV・5日-20.2%/20日-35.9%）。文脈=6月高値11.27万→半値の急落（バブル修正型＝「事件でも事故でもない第三類型」とオーナーに整理済み・個別売買判断は助言不可の線を維持）。
**③トラッカー降格ルール新設（オーナー相談→案A承認・7/18）**: オーナーが「✅昇格3本とも現在値が昇格基準割れ（CIが0跨ぎ）」の矛盾を発見→真因=`signal_lab_tracker.py`の**永久ラチェット**（一度昇格したら不変・降格ルール不在）。**降格ルールを事前登録して実装済み**＝昇格後もチェックポイント（N=min_n倍数）ごとに再判定し、**基準割れ2回連続→trackingへ降格**（昇格限定メール自動停止・再昇格可・反証⛔のみラチェット維持）。ユニットテスト5遷移✅・sync済み→**次のsignal-lab-daily(毎朝06:10)から適用**。見込み: 指数×ロング=初回runでstrike1(last_eval_n未設定→CP即到達)→N=240頃(≈1週間)で降格濃厚（N=212で平均R+0.05・holdout不合格=初期の幸運の平均回帰）／metal gate(-0.30・上限+0.018でギリ跨ぎ)とreversalL(+0.17)はCP=N160(2-3週後)から判定=境界ケースはゆっくり＝意図どおり。**DOCTRINE §0-1のライブ再現**（edge2本減衰・gateだけほぼ有意維持）。
**④4Hクラッシュ根治（7/17 23:28の全落ちメール・オーナー承認済み修正）**: 真因=**7/11監査#9修正が持ち込んだ代入前参照**＝email_silent免除判定(指数×ロング#21)が`position_plan`を参照するが算出が31行後→「その回の最初の新規シグナル銘柄が全email_silent」で未代入クラッシュ（実例=NQ first_pullback_short・その回の記録/評価/track-record全スキップ）。落ちない場合も**前銘柄の古いプランを誤参照**する副作用バグが同居。**修正=プラン算出ブロックをemail_silent判定の前へ移動**（意味は監査#9のまま・コンパイル✅・代入<参照を機械確認✅・mw check緑・sync済・local==main照合✅）。次の4H定時から反映＝**次回以降のTechnical Alerts失敗メールが来ないことを確認**。
**②格言キュー補充**: proverb-daily-autoが**7/15から4日連続キュー枯渇エスカレ**（#1〜15全公開・水増しせず正しく待機）→PROVERB_GUIDE.mdに**#16〜24の9本追記**（先頭=事件は売り事故は買い🚨・キオクシア急落を第三類型の一般論素材に使える設計・銘柄推奨禁止を行内明記／山高ければ谷深し・天井三日底百日・押し目待ちに押し目なし・行き過ぎもまた相場・命金・万人強気（宗久）・セルインメイ・国策に売りなし）。mw check緑→sync 232成功。**7/18 15:41の手動runは無出力で終了**（90分監視・公開/エスカレ/迷子ブランチ全部なし＝当日10:12回の枯渇エスカレ記録を見て1日1本を保守的に解釈した可能性）。二重公開リスクがあるため再手動runはせず、**7/19 10:12の定時運転が#16(事件は売り事故は買い)を拾うのを確認する**（キューのmain反映は確認済み）。

<!-- 7/16 Modern Standby根治／7/15 記事#6+日付事故+Q18❌+reconcile／7/10 declutter+Q12／7/7 進化ループ・TT3・Q1Q2／6/26-27 JP EVロードマップ の各節は 2026-07-19 に SESSION_ARCHIVE.md へ退避。要点は auto-memory と DOCTRINE に反映済み。🔴日付ゲート提案は下の宿題⓪-🔴が現役。 -->

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

### 🔜 次セッションで最初に確認（在flight・2026-07-20向け）
- **⓪-A 7/19大改修の初運転確認＝7/20朝に①②✅完了**: ①06:10 run=コンボ3本(combo_hb_rsiob/combo_bbub_rsiob/combo_db_hb)登録✅(43→46仮説・全てtracking/holdout_pass=False)・**promote_strikes未出現はCP到達仮説ゼロの仕様どおり**(コード286-293行=CP時のみ書く)・strike1保持(index_long_live N212)・#045自動公開(指数×ショートgate逆転) ②4H定時=全success・**A修正稼働の実証=n_promoted 3→2**(gateがメール通行証から除外)・**D修正稼働=avoid_matched記録出現**・support_bounce初発火2件(BTC 1h・email=False=正常)・退役2タイプ発火0・メール0通=無音期間の方向どおり ③**今週中**=指数×ロングがN=240のCPでstrike2→降格→**メール無音期間入り**（昇格edge 0本=正常状態・手動介入しない。🛡ブロック表示の実物確認は次にメールが出る時） ④**≒7/27**=格言キュー枯渇→#25以降補充 ⑤**9/20以降**=15分足セッション追試（research/_fx_session_15m_scan.py再実行・事前登録済み） ⑥✅7/20=`/consolidate-memory`実施（MEMORY.md 9.4→4.0KB=予算内・詳細は各ファイル側に確認済みの上で索引をフック化）。
- **⓪-B 7/20昼 ローカルタスク電池ブロック根治✅**: スリープ復帰後、JQ_Lake/JQ_Screenだけ`DisallowStartIfOnBatteries=True`（7/16対策の漏れ＝バッテリー駆動時はwake発火もブロック）と判明→**両タスク電池OK化**（他設定不変・他3タスクと整合）。7/20は海の日=休場で実害なし・真の欠測=金曜7/17の寄り付きロガー分は`jp_open_logger.py`自動バックフィルで回復（45行・DS◎○タグ付き）＋心拍7/17へ前進。screen/card/openlogの番人アラート3件は日次スクリプト手動実行で全解消・番人オールグリーン確認済み。
- **⓪セッション冒頭の新ルーチン＝`python mw.py evolve`**（DOCTRINE突合+キュー+トラッカー鮮度・トークン0）。⚠️**日付は作業の直前に必ずGet-Dateを取り直す**（7/15日付事故の教訓＝冒頭の値を使い回さない・auto-memory feedback_date_freshness）。
- **⓪-🔴オーナー判断待ち＝publish_article.py への日付ゲート追加提案**（記事の公開日≠今日JSTなら停止・`--allow-backdate`免除・signal-lab date_check と同型）。7/15の日付事故の恒久対策＝ゲート編集は人間専任のため承認待ち。承認されたら次セッションで実装。
- **⓪-C idea-scout-weekly**：✅初定時運転7/12成功→**7/15転記完了（6件処理）**＝Q17会計アノマリー2本バッチ（資産成長・アクルーアル=TA/NP/CFOはfinsキャッシュにあり実装可）＋Q18価格アノマリー2本バッチ（MAXロッタリー・週次リバーサル=レイクのみで可）を事前登録（mw evolveで登録簿SHA記録済み・出目未見）。粗利プレミアム=watch（J-Quants財務にCOGS/粗利なし）・月末月初=tested（LW4個別株棄却の実質重複）。slugs 6件追記済み。次回の受信箱確認=7/19(日)14:00運転後。
- **⓪-D 進化ループ続き＝次の本命は Q17 会計アノマリー2本バッチ**（資産成長・アクルーアル。設計は queue に登録済み・実装は #1/#4 のPIT財務インフラ+`_jp_method_audit.py`流用＝`_jp_q18_price_anomalies_screen.py`が直近の雛形）。他の候補=growth_levers残（②b国外OOS／④promise audit／⑤プレイブック）・アレンジD（グレアム防御×PEG複合）。**✅7/15消化済=記事#6公開・Q18❌**。TT3=月1回・Q11=毎月1-3日タスク自動。**8/1以降の最初のセッションで7/31 formation凍結を確認**（`mw evolve`のQ11行がformation 1/12になっているはず）＋**8月にmw screen📅列の初発火を確認**（Q1決算シーズン・元データ=J-Quants earnings-calendar・キャッシュ`_jp_earnings_calendar.json`）。**DOCTRINE 24.2KB=warning 1＝次のdeclutterで§3スタブ化**。
- **⓪-E 巨匠アレンジ枠の残り候補（B=Q13は7/9完了）**：
  **A**=❌7/11検証済み（Q15・単一資産超えず=記事#6素材）／
  **C**=✅Q11で7/11実装済（screener参考列だけ任意で未）／**D**=グレアム防御×PEG成長の複合1本（複合は前科あり=期待控えめ明記）。
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
- **⑨相談したら進む事項**：(a) OGP画像のロゴ入り差し替え (b) ツール次候補＝DCA比較/NISA枠/ポジションサイズ（後2者はコンプラ設計繊細） (c) `btc_all_1d`のN30緩和＝コスト込みで脆弱の扱い (d) 🏁5本問題のauto_*注記移設 (e) リバモア検証（優先度低）。
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
