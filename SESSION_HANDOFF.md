# 🔖 セッション引き継ぎ（最終更新: 2026-07-06 夜）

新セッションは **このファイル＋ CLAUDE.md ＋ auto-memory（MEMORY.md 経由）** を読めば文脈を復元できる。
2026-06-17 以前＋7/2〜7/3の詳細履歴は **SESSION_ARCHIVE.md**（保管庫・後から辿る検索用）へ退避した。

---

## ✅ 7/6の作業まとめ（詳細は auto-memory 各ファイル）

- **研究日誌#031 公開日誤記事故→修正+日付ゲート新設**（[[project_signal_edge_research]]）：routine（UTC環境・06:1x JST実行時はまだUTC前日）が#031を7/5付けで公開→「今日の日誌が無い」ように見えた。日付4箇所（記事datePublished/公開表記・guides.htmlカード・generate_market_news履歴行）をAPI修正+ローカルreconcile+ライブ確認済。**恒久対策＝`signal_lab_verify.py`に`date_check()`**（公開日≠JST今日なら赤=公開ブロック・再監査は`SIGNAL_LAB_SKIP_DATE_CHECK=1`・単体テスト済）。**明朝06:10の#032が日付ゲート付きの初運転**。
- **⚠️autopublish重複記事問題＝発見・統合・再発防止**（[[project_content_psychology_strategy]]）：7/4キュー補充⑫⑬が6/24既存記事と主題重複のまま自動公開されていた（スラッグ語順違い/部分一致でキューの完全一致スキップをすり抜け）。**⑬単複利・⑫金利債券の2ペアとも統合済**＝旧6/24版（-interest / interest-rates-bonds）をnoindex+canonical→新版+誘導ボックス・guidesカード撤去・内部リンク付替え（ETF/credit-spread/yield-curve）・NOINDEX_SLUGS登録（sitemap除外）・全ライブ確認済。**⑭⑮⑯（ETF/注文方法/PER・PBR）は既存とスラッグ完全一致＝routineが自動スキップするので安全**。㉒税金はキュー行に差別化注記（口座・通算に限定+guide-investment-taxと相互リンク）。**再発防止＝`check_guide_draft.py`に検査7:スラッグ重複検査**（トークン集合の同一/包含でRED・82記事ペア総当たりで誤検知ゼロ確認済）＋リンターにnoindexページのカード必須免除。**明朝05:30 autodraftが⑭〜⑯を正しくスキップして⑰インフレを下書きするか＝スキップ実運転の初確認**。
- **🌍 世界手法カタログ+巨匠#5〜#7+QA+複合＝計17仮説を1日で検証**（[[project_masters_queue]]・全て事前登録→train/holdout→日付クラスタboot・レイク506万行）：カタログ=`research/world_methods_catalog.md`（35手法×検証可能性タグ・結果も追記済）。**①#5 BNF乖離逆張り=❌**（方向は両期間一貫+だがp≈0.09・blowup23-28%・エッジ本体は板裁量）**②#6 一目均衡表=❌**（三役好転=対照比+0.01/+0.23%＝ほぼゼロ・n4.4万）**③#7 タートルズ=TT3のみ✅シリーズ初の順張り両期間合格**（素の20/55日ブレイクはtrain有意マイナス=飛びつき負け筋再確認。**20日ブレイク×MA50>200 = train+0.67%(p.009)/holdout+1.39%(p.000)**・blowupも低下）**④QA=❌**（52週高値=惜敗・**低ボラ=暴落確率1.2-2.8% vs 対照18-19%＝防御だけ劇的に再現**・モメンタム12-1=非有意）**⑤複合C1/C2=❌**（オーナー発案「組み合わせ」→C1押し目vsナイフ=**期間で反転**・C1のblowup32-36%はBNF素より悪化=「MA200上なのに-20%乖離」は個別災害選別だった／C2低ボラ×52週高値=holdoutで負け・防御のみ再現）。**総括＝リターン複合は全て地合い依存・安定再現は「守り」だけ**。スクリプト=`_jp_bnf/_jp_ichimoku/_jp_turtle/_jp_anomaly/_jp_combo_screen.py`+各summary.json（全ローカル/SYNC外）。
- **📰 巨匠記事#4公開済**（`guide-masters-004-world.html`・12仮説を1本化）：ゲート全通過＝決定論数値照合`_verify_masters004.py`197項目一致→check_guide_draft GREEN→品質Opus公開可（軽微1件適用→再照合緑）→コンプラOpus🟢白（人物事実WebSearch裏取り済）→publish→ライブ200/カード/index履歴/sitemap確認済。
- **✅裏方2件が正常化**：automation-health=7/6から**success**（閾値緩和後初回・7/1〜7/5の連続failureが終息）／health-check=7/6 12:00 schedule**success**（6/25からの慢性失敗が終息）。openなIssueゼロ。
- **朝チェーン確認（7/6）**：autodraft 05:39コミット着地（PUSH-MAIN修正後初定時○）／jp_daily 06:17カード履歴1行追記○／signal-lab 06:29 draft031+claims○／番人の取引再開アラートなし（休眠継続=正常）。

- **🆕 複利シミュレーター公開（7/4・オーナー発案）**：`guide-compound-sim.html`＝入力4つ（初期額/月額/年利/期間）→資産推移SVGグラフ＋年次表＋単利比較＋課税概算トグル（20.315%・NISA注記）。全て端末内JS・外部送信なし。**計算式＝金融庁つみたてシミュレーター2025年9月改修後と同じ幾何月利 (1+年利)^(1/12)−1**（監査Opusが「旧式=年利÷12＋『金融庁と同じ』表記は改修で不正確＝優良誤認リスク」を発見→式ごと新式化・権威付け文言除去）。単利は年利÷12で分離。ゲート＝プレビュー実走でPython参照値と全ケース一致→コンプラ🟡→修正→独立白→publish→HTTP200。カテゴリ「💰投資の基礎知識」。今後の単複利記事（autodraftキュー⑬）から内部リンク推奨。**→常設導線2本を追加（同日）**：①index＝`generate_market_news.py` テンプレの更新履歴直下に🧮固定バナー ②guides.html最上段に「🧮 計算ツール（常設）」カテゴリ新設。**→同日夕にツール3本追加＝計4本体制（全ライブ確認済み）**：⚖️`guide-breakeven-calc.html`（損益分岐勝率＝RR⇄必要勝率⇄期待値R・当サイトの43%と直結）／🧾`guide-fee-impact.html`（信託報酬A/B比較・月3万5%20年で0.1%vs1.5%=差176万）／🎯`guide-goal-calc.html`（必要月額 or 必要年利を二分法逆算・7%超警告・達成不可判定）。全てPython参照値と突合済み・コンプラOpus一括監査=**3本とも白**（任意改善1点のみ適用＝③7%警告の文言精度）。indexバナーは4リンクのピル型ツールバーに拡張。**→同日夜に5本目＝🏖️`guide-withdrawal-sim.html`（取り崩し＝定額/定率2モード・資産寿命・4%ルールの由来と限界・シークエンスリスク強調）を公開**（参照値全一致・コンプラ🟡→ラベル軟化「元本を大きく取り崩さない月額の目安（初月基準）」＋運用継続非推奨明記→独立白→ライブ確認済み。ツールバー5本化・常設カード5枚）。残候補=DCA比較/NISA枠/ポジションサイズ（後2者はコンプラ設計繊細）。**→トップページ整理A+B実施済み（7/4夜・オーナー承認・ライブ実測確認）**：`generate_market_news.py`テンプレ改修＝①更新履歴を最新1件+`<details>`折りたたみ（モバイル実測171px⇄開469px） ②指標/週次バナーを1行薄型化（112px/66px） ③騰落レシオをindexから撤去→1行リンク38px（ゲージはmarket-healthに既存） ④ツールバー/履歴のマージン32→12px。**中段スタックが約1,070px→517pxに半減・横はみ出し0**。**→第2弾+C+Dも同夜実施（ライブ実測済み）**：ダイジェストのカウントダウンを`<details>`化（480→336px）・センチメント帯薄型化（294→257px・padding32/36→18/22）・hero/digestマージン32→16px・**ジャンプバー新設**（nav直下・#market/#ai/#tools+カレンダー・62px・ダーク対応CSSクラス`jump-bar`/`md-fold`）。1画面目（812px）にセンチメントまで収まる構成に。整理はこれで一区切り。**→同夜サイトロゴ導入（案C＝上昇ライン×日の丸・オーナー選定）**：`favicon.svg`（正）＋PIL書き出しの`favicon-32/192.png`/`favicon.ico`/`apple-touch-icon.png`（SYNC_FILES登録済）。**`apply_logo.py`**（新設・冪等sweep）で全130ファイル＝guide全部+静的3+生成スクリプト9のheadにfaviconリンク3行＋ヘッダー「📊」→インラインSVGロゴ差し替え。ライブ確認済み。**X用アイコン=`mw-logo-512.png`（ローカルのみ・手動アップロード用）**。OGP画像の差し替えは未実施（現状08_market_stock.pngのまま＝希望あれば次回）。**副収穫＝mw.py deployのstale誤検知バグ修正**（syncサマリ凡例の🚫絵文字に反応→`🚫(?!=)`の実ファイル行のみ判定に）。
- **自動化の精度点検（7/3未明）**：①no_plan 282件＝warn系のみ発火の**設計仕様と判明（バグでない）** ②**signal-lab-daily routineを更新＝tierフィルタ解禁**（selection.tier がclaims/研究日誌で使用可に）・手本015化・nav10・🏁N30注記 ③**indicator-result routineを厳格化**＝アグリゲーター(tradingeconomics/investing/forexfactory/fxstreet)と個人ブログは裏取りに数えない・満たなければverified=false ④寄り付きロガー欠測検知を `_jp_health_check.py` に追加（前営業日照合・祝日除外・アラートファイル） ⑤generate_market_news はstaleガード作動→reconcile PUTで反映（commit 199bfa80・.sync-cache baseline整合済）。

- **🆕 記事自動化2本を新設（7/5・オーナー依頼）**：①**基礎知識シリーズの完全無人公開**＝routine `autodraft-publish`（`trig_01GHZ2KG9H74H27ku2CWS8Up`・毎日08:40 JST=cron `40 23 * * *` UTC）が最古の未公開下書きを仕上げ→**決定論ゲート `check_guide_draft.py`**（新設・SYNC入り・固定ゲート＝noindex残り/kinsho-v1/ナビ10/TODO/売買推奨ハードNG/SVGはみ出し重なり=オラクル関数流用。GREEN/RED単体テスト済）→Opusコンプラ+品質白（🟡軽微=Opus修正→再ゲート→独立Opus白）→publish_article→PUSH-MAIN→HTTP200。ダメならREVIEW.mdに🚩。手順書=`drafts/AUTOPUBLISH_GUIDE.md`（SYNC入り）。②**投資本新刊ウォッチ**＝routine `book-watch-weekly`（`trig_01FN4sPxjKgGR8FFL1ezyDSS`・毎週土曜11:00 JST=cron `0 2 * * 6` UTC）＝WebSearchで直近30日の新刊1〜3冊→2ソース照合→`guide-new-books.html` に中立紹介を積み上げ（最大40冊・アフィリンクなし・評価/推薦しない・初回はページ新規作成+guides.htmlカード）。手順書=`drafts/BOOKWATCH_GUIDE.md`（SYNC入り）。**guide-new-books.html はSYNC禁忌登録済**（CLAUDE.md+check_site_consistency）。キュー⑰〜㉔も同日補充（インフレ/経済指標/日経TOPIX/為替リスク/配当/税金/投資詐欺/ローソク足）＝残13本。**→同日E2E実証完了**：新刊ウォッチ=初回公開ライブ200✅／autopublish=guide-bonds-interest-rates（キュー⑫金利債券）を決定論緑→Opus白→公開ライブ200✅。**副収穫＝autodraft-articleが7/4-7/5にpushレース負けで2日無音だったのを発見→プロンプトにPUSH-MAIN規約を移植修正（RemoteTrigger update成功・7KB制限内）**。⚠️残課題=このレース型の沈黙はautomation-healthの鮮度監視をすり抜けた（REVIEW.md/draft-*がsignal-labの書込みで新鮮に見える）＝autodraft専用の鮮度チェック（draft-signal-lab-*除外）は未実装・次回検討。明朝の定時運転確認=05:30 autodraft(⑬単複利の下書き)→08:40 autopublish(公開)。
- **🆕 番人EA「MW_Guardian」v1作成（7/5・オーナー依頼＝ローカル専用/SYNC外）**：`mt4/MW_Guardian.mq4`＋導入手順`mt4/MW_GUARDIAN_SETUP.md`。監視型（発注ブロックなし=オーナー要望で5分足の速度優先）＝約定3秒検知→R5仮SL自動装着(H1 ATR×1.5)/2%(相関合算)/重ね張り/指標接近(economic-events.json WebRequest)/損切りずらし/建値+1R通知/決済CSV記録→Alert+スマホPush。デモ/本番同一。強制クローズは意図的に未実装。**→同日夜に導入完了（デモ口座GOLD_USD H4チャート・ニコニコ☺確認・カレンダー取得OK「次=中国CPI 7/9」・スマホPushテスト着信確認済み）**。1週間デモ運転→問題なければ本番口座へ同手順で移行。旧ProCon-Max EAは置き換えで停止（検証済み「資産増えず」のため問題なし）。仕様メモ=「CPI」文字列マッチのため中国CPIも警告対象（mw disciplineと同基準・絞る場合は EventNameMatch を1行調整）。
- **🆕 規律チェック拡張＝R6相関合算リスク+スリッページ実測（7/5・アドバイス採用）**：`_trade_discipline_check.py`（SYNC外）に **R6=同テーマ×同方向の同時保有クラスタを横断検出→リスク額合算で2%判定**（テーマ=株指数(JP株込)/貴金属(金銀)/原油/BTC/円FX/クロスFX。classify_symbolに銀追加）＋**SLP=予定価格vs実約定のスリッページ実測**（--netコスト較正用）。`import_my_trades.py` はフォーム任意3欄（**口座残高（円）/リスク額（円）/予定価格**・部分一致認識・旧回答は空欄互換）を `account_balance`/`risk_jpy`/`planned_price` として取込。手順は `MY_TRADES_SETUP.md` 1-3 に追記済＝**オーナーがフォームに質問3つ足せば次の取引から自動判定開始**。⚠️前向き検証(7/3事前登録)の遵守/逸脱タグは登録時5ルールに固定＝R6は登録外・参考（プロトコル保護）。実データ試走で**旧R3に映らなかった金の重ね張り2ポジ（GOLD_USD_28375278/280）を新検出**。単体テスト全緑。**→同日夕: 取引記録フォームの接続が完了（初接続＝今まで23件は手動転記だった）**：オーナーがフォーム作成（14項目・「取引種類」表記はコード側で両対応 commit 565212a）→CSV公開→Secret `MY_TRADES_CSV_URL` をAPI登録（PyNaCl暗号化）→E2Eテスト＝TESTレコードが新3欄付きでmy-trades.jsonに着地確認→CSV行+GitHub json両方からTEST削除済（bba2130・23件に復帰＝番人誤検知なし）。**決済の記録は「送信済み回答の編集」で追記する運用**（設定「回答の編集を許可」ON推奨）。
- **🆕 メールノイズ根絶+セキュリティ点検（7/5夜・オーナー依頼）**：Gmail実査14日=約55通の内訳①pages build失敗=無害ノイズ（高頻度コミットでビルド追い越し・オーナーにGmailフィルタ案内済）②Health Check毎日失敗（6/25〜）＝**index「最終更新」regex乖離が慢性原因→check_site_health.py修正済（タグ許容形・ライブ検証済）**③automation-health毎日発火＝cron遅延誤検知→**閾値緩和（1H 3→5h/政治3→4h・41995e7）**。実害1件=7/2ニュースカード消失（7/3から検知されていた）→guides.htmlへ復旧済（dbdc80d）。セキュリティ=リポにトークン混入なし・SecretScanning+PushProtection有効・PAT はclassic repo+workflow 期限8/31（**次回更新時にfine-grained移行推奨**）・オーナーTODO=GitHub 2FA確認/Gemini予算アラート/Gmailフィルタ。**→同夜 PAT を fine-grained へ切替完了**（marketwatch-ai 限定・Contents/Workflows/Actions/Secrets/Issues=RW・Pages=RO・期限1年・全権限の実測テスト通過・旧classicトークンはオーナーが削除）。
- **⚠️ 事故と再発防止（7/5夜）＝sync_to_github.py スタブ上書き**：GitHub側のsync_to_github.pyは**publish_articleクラウド用の616Bスタブ（本物ではない・意図的設計）**。Claudeがreconcile中に誤ってローカル本物（35KB・SYNC_FILES 217件+staleガード）へ上書き→**OneDriveバージョン履歴で復元済**。再発防止=check_site_consistencyに**スタブ検知ガード**（<20KB or staleガード無しで即エラー・c248148）。教訓=**sync_to_github.py/mw.py等ローカル専用ツールは絶対にリモートから取り込まない**。autopublish公開記事はローカルへreconcile+SYNC_FILES登録が必要（bonds登録済・217件）。
- **🆕 昇格エッジ限定メール（7/5・オーナー要望）**：`generate_technical_alerts.py` に昇格ゲート新設＝**signal-lab-tracker.json の status=promoted 仮説にマッチしたシグナルだけメール送信**（現時点=index_long_live「指数×ロング」1本のみ）。他は従来どおり signals-log 記録＋クールダウン更新＝前向き検証は全量継続→**今後の研究で昇格すれば自動的に配信対象へ**（トラッカー連動・コード変更不要）。照合は固定オラクル `signal_lab_verify.match` を import（二重実装なし）。tracker読込/照合失敗は fail-open＝従来全送信（checkout欠落で沈黙しない）。キルスイッチ=環境変数 `EMAIL_PROMOTED_ONLY=0`。判定は `log_entry["promoted_gate"]` に記録。単体テスト7ケース緑。旧 #21 email_silent 例外は維持（昇格ゲートと整合）。

---

> 2026-07-02の「研究の高速化3点（holdout/J-Quantsレイク/事前登録）」「ルール文書棚卸し」はSESSION_ARCHIVE.mdへ退避（要点はauto-memory側に反映済み）。

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
| **相関ポジ合算リスク2%・実スリッページ** 🆕7/5 | 同上 R6/SLP（フォーム任意3欄=口座残高/リスク額/予定価格の入力分から自動判定） | 同テーマ×同方向の同時保有を横断検出し合算%で2%判定（金銀・FXも対象＝指数限定R3の一般化）。前向き検証の群割当は登録時5ルール固定＝R6は参考枠 |
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

### 🔜 次セッションで最初に確認（在flight・2026-07-07向け）
- **⓪7/7(火)朝の無人運転を確認**：(1)05:30 autodraft=**⑭⑮⑯を自動スキップして⑰インフレ(inflation-real-return)を下書きするか**（スキップ実運転の初確認。⑭ETF等を下書きしたら重複ゲートが08:40で止めるはず=スラッグ重複検査の初実戦） (2)06:10 signal-lab #032=**日付ゲート付き初運転**（公開日が7/7付けになるか。REDでエスカレなら日付ミス再発の証拠=REVIEW.md確認） (3)08:40 autopublish正常公開。
- **①巨匠シリーズ続行（オーナー合意済み=カタログ順に検証→記事化）**：次候補=ダーバス箱/ワインスタイン ステージ2（ブレイク系第2弾・TT3との整合が見どころ）/酒田五法/グランビル/ズールー原則(要財務join)/デュアルモメンタム。カタログ=`research/world_methods_catalog.md`（結果追記済）。スクリプトは`_jp_turtle_screen.py`が雛形。
- **②TT3の前向き検証登録（相談→実装）**：唯一の合格「20日ブレイク×MA50>200」を今日以降の新データで機械監視する仕組み（JPトラッカー流用 or 月次スクリプト）。**合格したが採用しない・前向き再現が本採用条件**の原則どおり。
- **③防御スクリーン列の追加（相談）**：低ボラ×52週高値近接（暴落確率1-3% vs 18-19%）を個人ダッシュボードの🛡グレアム列の隣に「防御列」として追加する案。リターン予測でなく保有銘柄の暴落耐性の可視化。
- **④昇格エッジ限定メール＝実発火の初観測がまだ**：7/6(月)に発火したか technical-alerts ログで確認（「🏅通過（指数ロングのみ配信）/🔇非該当（記録のみ）」・signals-log の `promoted_gate` キー）。
- **⑤番人EA MW_Guardian＝実弾テスト未実施**：オーナーがデモ口座で試し発注→スマホPush・仮SL自動装着・重ね張り警告の実挙動を一緒に確認（EAはPC MT4起動中のみ稼働）。
- **⑥リードマグネット公開待ち＝オーナーのGoogleフォーム作成待ち**：URLが来たら `MAGNET_SETUP.md` の Claude作業（コンプラ監査→PDF SYNC→CTA設置→X導線）を一気通貫で。
- **⑦AdSense 再審査の結果**：6/27申請済（[[project_adsense_review]]）。承認/却下を確認。**旧重複2記事のnoindex統合（7/6）は審査にプラス方向**。却下ならニュース記事もnoindex等の next step。
- **⑧オーナー手動タスク2件**：(a) **X用アイコン `mw-logo-512.png`**（作業フォルダ直下・ローカルのみ）を @rx009898 のプロフィール画像に手動アップロード (b) 実機スマホでトップページ整理後の見え方＋タブのロゴを確認。
- **⑨相談したら進む事項**：(a) OGP画像のロゴ入り差し替え (b) ツール次候補＝DCA比較/NISA枠/ポジションサイズ（後2者はコンプラ設計繊細） (c) `btc_all_1d`のN30緩和＝コスト込みで脆弱の扱い (d) 🏁5本問題のauto_*注記移設 (e) リバモア検証（優先度低）。
- ✅済（7/6・詳細は上の7/6節）：#031日付事故修正+日付ゲート／重複2ペア統合+スラッグ重複ゲート／巨匠#5〜#7+QA+複合=17仮説検証／記事#4公開／automation-health・health-check正常化確認／朝チェーン全部正常。
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
