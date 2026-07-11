# 🔖 セッション引き継ぎ（最終更新: 2026-07-11）

## 🥇 7/11 Q8金ラボ第2R完了＋シグナルメールMT4幅併記（今日のメイン）

**①シグナルメールのMT4価格ズレ対策（オーナー要望）**: 絶対価格はYahoo基準＝MT4(BigBoss)と構造的にズレる（金/指数=先物vs現物CFD・FX=feed差＋スプレッド）→**SL/TP「幅」併記＋「MT4は現在値から同幅で設定」注記**を実装（`generate_technical_alerts.py`の`_fmt_distance`・FXはpips換算・全銘柄グループ表示テスト済）。**エンジン/signals-log記録は不変＝前向き検証の連続性維持**。commit b4f8de9・次の定時運転(technical-alerts 4hごと)から反映。実メール初確認は月曜（土曜=FX休場・BTC発火なら週末可）。

**③Q11ズールー前向きトラッカー=📊アーム完了（fins月次自動更新も整備）**: **(a)** `_jp_fins_monthly.py`＝毎月1〜3日05:50タスク`MarketWatch_JQ_Fins`(PT2H)で全3717銘柄の財務キャッシュを再取得（実測1.5s/銘柄≈93分・バジェット6600s・mtime再開・完走時のみ`_jq_fins_cache_meta.json`にrefreshed_at記録）。**(b)** `_jp_zulu_tracker.py`＝Q6シグナルをzulu_flags importで1バイト不変流用・**参照再現がsummaryと完全一致**(train+2.39% p0.0067/holdout+3.05% p0.0003)・**凍結ガード=fins refreshed_at≥formation**（PITで更新遅延は無害・凍結メンバーはstate固定）・チェックポイント=formation12の倍数・合格=formation≥12∧N≥500∧CI下限>0。**(c)** 番人=`_jp_health_check.py`にcheck_fins新設（毎月5日までに完走なければアラートtxt）・`mw evolve`アジェンダにQ11行。**初formation=7/31→8/1タスクが自動凍結**・初判定≒2027年夏。**初回フル取得=✅同日完走（3716/3717・1件timeout除外・meta refreshed_at=2026-07-11）＝fetch→バジェット中断→mtime再開→meta→トラッカー起動の全経路を3回の実行で実証済み**。

**④Q14防御カタログ第1弾=🛡4/6合格（成長レバー会議②・6仮説を1バッチ事前登録→同日検証）**: **H5短期爆騰(5日+30%新規)＝同日blowup60差+47.50/+48.56pp・blow65%＝過去最強の回避フラグ（🔪重複11%=独立）**／H4ナイフ窓延長=61-120日も+14.16/+12.63pp＝**🔪窓120日化**／H1決算またぎ+3.37/+4.71pp（準PIT注記）／H2高ボラ突破+7.78/+7.54pp。❌H3業種過熱(400ユニバース制約ns)・H6 52週安値(train ns)。`_jp_defense_catalog_screen.py`・DOCTRINE §2結晶化・**適用宿題=mw screenに⚡爆騰列+🔪窓120日化+決算前列**。

**⑤Q15資産クラスDM=❌不合格（アレンジ枠A・GEM円換算・正直な結果）**: train Sharpe0.391<IEF単独0.619／holdout1.330<金単独1.450＝**切替は単一資産を超えない**。対株式DDは半減(-35%vs-60%)＝守りの部分効果のみ・記事#6素材（「原典どおりでも円建てでは単一資産に勝てなかった」は教育価値あり）。`_dm_asset_class_screen.py`・DOCTRINE §3。

**⑥実行系レッドチーム監査=🔴3/🟡12/🔵4の19件発見（Fableサブエージェント・研究系7/8監査の実行系版）**: 🔴①EAのR2警告は建玉時のみ=持ち越し盲目 ②仮SL装着失敗が完全沈黙+無限リトライ ③保有中のSL削除が全系で無検知＝最大の抜け道。**数学(SL/TP・pips換算)は誤りなし**。Python側4件は同日修正済（#9信頼度の指数ロング+1がショートに混入するバグ=多数決方向に統一・メール幅併記の鮮度ガード/転記禁止/方向注記=commit f2cc7e3）。**EA側8件は宿題⑤と同時修正→コンパイル→デモの段取り**。全文=`research/execution_audit_2026-07-11.md`（対応ログを単一の真実に）。

**⑦軽量2本**: `_goal_math.py`=1億への算数（必要資本=1億÷CAGR・到達年数・ルーイン近似・例:500万+月20万でCAGR15%なら24.6年＝資本供給側の重要性が一目）／mw evolveに**系KPI**（前向きトラッカー2本表示+仮説生存率50%=6/12）。成長レバー台帳=`research/growth_levers_2026-07-11.md`（残: ①規律実弾化・②b国外OOS・④promise audit・⑤プレイブック）。

**②Q8金ラボ第2R=✅完了（🔓holdout解錠2026-07-11・この1回限り・再解錠禁止）**: 第1R有望2本のparamsが未記録→**valid数値の記録一致で特定**（volfilter=デフォルト0.681≒記録0.68／vol_scaled=tv0.10で0.626完全一致・照合5回・成績での選び直しなし）→合否基準を解錠前宣言(Sharpe≥0.6∧PF≥1.25)→**2本とも合格**: ①複合トレンド×低ボラ`{}`=Sharpe0.63/PF1.93(コスト2x=0.599ボーダー) ②多数決モメンタム×ボラ目標10%=Sharpe1.023/PF6.06(コスト2x頑健・valid→holdout改善)。ただし生SharpeはBH(1.114)未満＝**ラボ合格3本すべて「価値は防御」＝DOCTRINE §0-1を金でも再確認**。台帳`research/gold_backtest/RESULTS.md`新設（第1R教訓の是正）・DOCTRINE §2改稿・anchors50件・完了Q8/Q9/Q12をqueue_archiveへ退避・**DOCTRINE/queue/HANDOFF全て予算内warning 0**。金ラボは新素材が出るまで休眠。

## 🧹 7/10 declutter＋Q12再監査

**①declutter＝3文書すべて予算内に復帰**: HANDOFF 38→28.5KB（7/8全節＋7/7スクリーナー節をARCHIVE退避）／DOCTRINE 25.6→**24.0KB=warning0**（§3棄却表を統合圧縮＝anchor45件維持）／CLAUDE 34.5→32.0KB（SYNC禁忌節の重複圧縮・全ファイル名保持）。CLAUDE/HANDOFF/ARCHIVEはsync済。DOCTRINE/queueはローカル専用＝sync対象外。

**②Q12 グレアム/バフェット p値再監査＝✅完了（DOCTRINE §2/§3/§6注記済・`_jp_q12_audit.py`／`_jp_q12_summary.json`）**: 7/8監査 発見4（月次formation×fwd12M=12倍重なり→SE過小の疑い）を、各主張で **旧p(iid cluster)／新p(block boot L=13)／同日クロスセクション対照** で再計算（監査＝新合否なし）。
- **🔴核心=§0-1を強く確証**: グレアム防御（暴落率差 高≥4 vs 低≤1）は train-22.4pp/holdout-19.5pp・**block bootでも同日対照でも両期間p0.0003**＝TT3リターン主張が同日対照で消えたのと対照的に守りは真の横断エッジ。効果量24%→4-5%(≈-20pp)完全維持。グレアム・リターン差も同日対照で両期間有意(+24.3/+11.8%)。
- **バフェット**: 「質は逆」方向は堅持(H1 -5.73/-6.05)だが**同日対照でtrain減衰(p0.094)/holdout堅持**。質は暴落防御にならず(H3 train+6.4pp)。割安内も質高いほど劣後(H2両期間有意)＝「安さが報われる」を強化。

<!-- 7/9夜 news-ticker新設の詳細節は 2026-07-11 に SESSION_ARCHIVE.md へ退避（7/11朝に定時運転確認済＝運用安定）。仕様=CLAUDE.md news-ticker.yml 節・残タスク=⓪-H（📰経済の既定非表示はオーナー好み待ち）。 -->

## 🧬 7/7 進化ループ構築（詳細=SESSION_ARCHIVE 7/8退避・運用=auto-memory project_evolution_loop）

- 6段ループ・DOCTRINE/番人/mw evolve/idea-scout-weekly。セッション冒頭は `mw evolve`。mw.pyはSYNC対象。未実装バックログ(a)〜(f)はARCHIVE参照。

## 🐢 7/7 TT3前向き（詳細=SESSION_ARCHIVE 7/8退避・queue Q7）

- `_jp_turtle_tracker.py` N=0/300・チェックポイント検定・**7/8にブロックboot改定**・月1回チェック。

## 🌙 7/7夜 Q1ダーバス/Q2ワインスタイン=❌棄却（詳細=SESSION_ARCHIVE 7/8退避・DOCTRINE §3）

- 両方崩れ「順張りはTT3のみ」と当時整理→**7/8監査でTT3自体も非頑健と判明**（上の7/8夜セクション参照）。

<!-- 7/7深夜 日本株スクリーナー新設（`mw screen`=`_jp_screener.py`ローカル専用・列プラグイン登録制・防御列で宿題Q9適用）＋レイク/スクリーナーCSV自動補充タスク新設＋jp_dailyフェッチバジェット根治は 2026-07-10 に SESSION_ARCHIVE.md へ退避。要点=auto-memory [[project_jp_screener]]。運用CLIは `mw screen --help`。 -->

新セッションは **このファイル＋ CLAUDE.md ＋ auto-memory（MEMORY.md 経由）** を読めば文脈を復元できる。
セッション冒頭は `python mw.py evolve`。2026-06-17 以前＋7/2〜7/3＋7/6の詳細履歴は **SESSION_ARCHIVE.md** へ退避した。

---

> 2026-07-02の「研究の高速化3点」「ルール文書棚卸し」もSESSION_ARCHIVE.mdへ退避（要点はauto-memory側に反映済み）。

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
| **公開日のUTC日付ミス防止** 🆕7/6 | `signal_lab_verify.py` の `date_check()`（再監査は `SIGNAL_LAB_SKIP_DATE_CHECK=1`） | datePublished/公開表記≠JST今日なら**赤=公開ブロック**（#031が7/5付けで公開された事故の再発防止） |
| **似スラッグの重複記事防止** 🆕7/6 | `check_guide_draft.py` 検査7 スラッグ重複検査（トークン集合の同一/包含） | ⑫⑬型の「語順違い/部分一致スラッグの同一主題」自動公開を**RED=人間エスカレ**（82記事総当たりで誤検知ゼロ） |
| **研究台帳の数値転記ミス・改竄・肥大化防止** 🆕7/7 | `_doctrine_check.py`（`mw evolve`・固定オラクル扱い） | DOCTRINEのアンカー21件を出典JSON/mdと突合＋事前登録簿SHA256＋サイズ予算＋§1構造検査で**error停止** |
| **非公開研究ファイルの公開リポ流出防止** 🆕7/7 | `check_site_consistency.py`＝SYNC_FORBIDDEN追加＋**`_`プレフィックス=ローカル専用規約** | DOCTRINE/queue/`_jp_*`等が SYNC_FILES に混入したら**error停止**（REDテスト7ケース済） |
| **公開記事への下書き残骸混入防止** 🆕7/7 | `signal_lab_verify.py` date_check の残骸検査 | 「下書き中」が本文に残っていたら**赤=公開ブロック**（#032実例の再発防止） |
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

### 🔜 次セッションで最初に確認（在flight・2026-07-11向け）
- **⓪セッション冒頭の新ルーチン＝`python mw.py evolve`**（DOCTRINE突合+キュー+トラッカー鮮度・トークン0）。
- **⓪-A 朝の自動化継続確認**＝`python -X utf8 _jp_health_check.py`（5項目✅）＋`JP*_要確認.txt`無し。**7/10朝=寄り付きロガー自己修復版の初定時運転✅**（タグsnap 07-10記録・番人5項目緑を確認済）。
- **⓪-B autopublish**＝✅7/11朝確認済: 7/10 ⑲nikkei-vs-topix・7/11 ⑳currency-risk とも全ゲート通過で公開（⑳はライブ200+免責+datePublished裏取り済）。⚠️両日ともクラウドのHTTP自己チェックだけ失敗（Cloudflare 403/NETWORK_ERROR）＝push成功で実害なしだが続くようなら要観察。次=7/12記録の確認。
- **⓪-C idea-scout-weekly**：初回手動E2Eは7/7済。**初の定時運転=7/12(日)14:00 JST**→翌セッションで転記（転記slugは idea-tested-slugs.txt へ）。
- **⓪-D 進化ループ続き**：7/11にQ8✅・Q11アーム・Q14🛡4/6・Q15❌まで消化＝**キュー残はQ10（低優先）とアレンジD複合のみ**。**次セッションの筆頭候補=Q14適用（mw screenに🔪窓120日化+⚡爆騰列+決算前列の3本・検証済み知見の⑤APPLY・列プラグイン式で軽い）**。次点=growth_levers残（②b国外OOS／④promise audit／⑤プレイブック）・記事#6（Q15の正直な❌+DD半減が素材）。TT3=月1回・Q11=毎月1-3日タスク自動。**8/1以降の最初のセッションで7/31 formation凍結を確認**（`mw evolve`のQ11行がformation 1/12になっているはず）。
- **⓪-E 巨匠アレンジ枠の残り候補（B=Q13は7/9完了）**：
  **A**=❌7/11検証済み（Q15・単一資産超えず=記事#6素材）／
  **C**=✅Q11で7/11実装済（screener参考列だけ任意で未）／**D**=グレアム防御×PEG成長の複合1本（複合は前科あり=期待控えめ明記）。
  ※「すでに生きているアレンジ」の整理も記事ネタ（赤三兵→連騰≥4危険ゲート・タートル資金管理→ATRベースSL/2%ルール・**G4逆張り→🔪回避フラグ（Q13）**＝原型のエントリーは死んでも部品は生きる）。
- **⓪-F ✅済（7/10）文書declutter**：CLAUDE 32.0/DOCTRINE 24.0(warning0)/HANDOFF 28.5＝全て予算内。以後もこの水準を維持（節が増えたら完了節をARCHIVEへ）。
- **⓪-G ✅済（7/9夜）routineによるリンター編集の再発防止＝三層で実装**: オーナー決定=**完全禁止**（等価修正も不可・赤はエスカレのみ・ゲート修正は人間専任）。①`AUTOPUBLISH_GUIDE.md`=固定ゲート4本（check_guide_draft/check_site_consistency/signal_lab_verify/publish_article）の編集・commit禁止+7/9違反実例を明文化 ②routineプロンプト更新済（手順4/7/絶対厳守を強化。⚠️**プロンプト禁止は7/8夜から存在したのに破られた実績あり**＝コード検知が本命） ③`check_automation_health.py`にチェック④新設=直近26hでゲート4本をオーナー/github-actions[bot]以外のauthorが変更→warn Issue（ローカル実測で7/9違反commit `80abc63` を正しく検知✅）。**⚠️7/10 09:30の運転で既知の7/9違反commit（対応済）が1回Issue化した可能性＝あれば無視してクローズ**。以後の検知は本物。
- **⓪-H ⚡news-ticker**: ✅7/11朝確認=夜間毎時運転OK（updated 7/11 10:03・30件）。残1件=**「📰経済を既定で非表示（ボタンで表示）」は1行で変更可＝オーナーの好み待ち**（夜間はYahoo!経済由来の消費者ネタ多め問題）。
- **⓪-I ✅済（7/9 20:30）guides.htmlカード消失＝実は「消失」でなく「未完了公開」**: git履歴調査の結果、カードは一度も存在しなかった（巻き戻しでも取り下げでもない）。**真因**=7/6のnews-daily-autoが当時のSYNC_FILES縮小問題で `check_site_consistency` exit=1→設計どおりエスカレ（commit 1200e77b=記事HTML+NEWS_LEDGERのみpush・カード/履歴/SYNC登録なし）→台帳の「再公開手順（人間が実施）」が3日間未実施のまま放置されていた。**対応**=台帳手順どおり完了（コンプラは当時Opus×2で🟢白済・noindexなし）：カード挿入（7/7と7/5の間の正位置）+SYNC_FILES+更新履歴→`mw check`緑→sync（guides.htmlはstaleガード🚫→diff確認=カード9行のみ→定石--force・commit 156f63e=+9/-0）。**番人③再実行=58/58✅**・ライブ記事200・sitemap収載済み。ついでに⑱`guide-economic-indicators-basics.html`のローカルreconcile+SYNC_FILES登録も実施（mw checkが検出）。**教訓=番人③の検知は「エスカレ回の未完了公開」でも発火する。まずNEWS_LEDGER.mdの該当日エントリを見ると1分で原因が分かる**（GitHub側LEDGERの7/6エントリは「公開準備」のまま=SYNC禁忌のためローカルから更新不可・実態は公開完了）。
- **①巨匠シリーズ**：記事#5公開済み（7/8夜・Q1〜Q5+TT3訂正を1本化）。次記事候補=「#6 割安成長（ズールー）×グレアム再訪」＝Q11前向き設計・Q12再監査の後が筋。
- **②TT3の前向き検証＝📊稼働中**（`_jp_turtle_tracker.py`・検定はブロックboot版に7/8改定・月1回チェック・初判定は10月頃）。
- **③防御スクリーン列＝✅適用済み**（`mw screen`の🛡防御列・7/7）。
- **⑤番人EA MW_Guardian＝実弾テスト未実施＋7/11監査で要修正8件**：次のEAセッションで（a)監査🔴3件+🟡5件を修正（`research/execution_audit_2026-07-11.md`対応ログ参照・R2持ち越し盲目/仮SL沈黙/SL削除無検知/magic無差別/AutoSL_TF=240等）→(b)MetaEditorコンパイル→(c)オーナーがデモ口座で試し発注→実挙動を一緒に確認＋表示リスク%vs手計算の1回照合。
- **⑥リードマグネット公開待ち＝オーナーのGoogleフォーム作成待ち**：URLが来たら `MAGNET_SETUP.md` の Claude作業（コンプラ監査→PDF SYNC→CTA設置→X導線）を一気通貫で。
- **⑦AdSense＝7/6再却下（確定）**：🔴**オーナー作業＝AdSenseコンソール[サイト]ページで却下理由の詳細を確認**→理由を見てから対応方針を相談（候補: ニュース/自動生成記事の追加noindex・コンテンツ拡充・再申請時期）。むやみにnoindexを増やすのは理由確認後。
- **⑧オーナー手動タスク2件**：(a) **X用アイコン `mw-logo-512.png`**（作業フォルダ直下・ローカルのみ）を @rx009898 のプロフィール画像に手動アップロード (b) 実機スマホでトップページ整理後の見え方＋タブのロゴを確認。
- **⑨相談したら進む事項**：(a) OGP画像のロゴ入り差し替え (b) ツール次候補＝DCA比較/NISA枠/ポジションサイズ（後2者はコンプラ設計繊細） (c) `btc_all_1d`のN30緩和＝コスト込みで脆弱の扱い (d) 🏁5本問題のauto_*注記移設 (e) リバモア検証（優先度低）。
- ✅済（7/8・詳細は上の7/8節）：⓪-A自動化3件初運転全✅／⑰公開＋autopublish二重欠陥根治／Q3酒田五法4パターン棄却／④昇格メール初発火観測（7/7・index_long_live 8マッチ4通送信=クローズ）。
- ✅済（7/6・詳細はSESSION_ARCHIVE）：#031日付事故修正+日付ゲート／重複2ペア統合+スラッグ重複ゲート／巨匠#5〜#7+QA+複合=17仮説検証／記事#4公開／automation-health・health-check正常化確認／朝チェーン全部正常。
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
