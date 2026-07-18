# 🔖 セッション引き継ぎ（最終更新: 2026-07-18）

## 👁 7/18 キオクシア監視＋格言キュー補充（枯渇解消）

**①監視銘柄ウォッチ新設（オーナー依頼・キオクシア285A）**: `_jp_health_check.py` に `check_watchlist()` 追加＝`_jp_watchlist.json`（ローカル専用）の銘柄をスクリーナーCSVの回避フラグ（danger≥1/🔪/⚡/赤字）と平日8:00+12:30に照合→**全解除 or 再点灯の遷移で `JP監視銘柄_状態変化_通知.txt`** を作成（両方向テスト済✅）。通知は「規律上の回避対象でなくなった」の機械的事実のみ＝買い推奨ではない。285A現況=⚡爆騰点灯中（7/16 CSV・5日-20.2%/20日-35.9%）。文脈=6月高値11.27万→半値の急落（バブル修正型＝「事件でも事故でもない第三類型」とオーナーに整理済み・個別売買判断は助言不可の線を維持）。
**③トラッカー降格ルール新設（オーナー相談→案A承認・7/18）**: オーナーが「✅昇格3本とも現在値が昇格基準割れ（CIが0跨ぎ）」の矛盾を発見→真因=`signal_lab_tracker.py`の**永久ラチェット**（一度昇格したら不変・降格ルール不在）。**降格ルールを事前登録して実装済み**＝昇格後もチェックポイント（N=min_n倍数）ごとに再判定し、**基準割れ2回連続→trackingへ降格**（昇格限定メール自動停止・再昇格可・反証⛔のみラチェット維持）。ユニットテスト5遷移✅・sync済み→**次のsignal-lab-daily(毎朝06:10)から適用**。見込み: 指数×ロング=初回runでstrike1(last_eval_n未設定→CP即到達)→N=240頃(≈1週間)で降格濃厚（N=212で平均R+0.05・holdout不合格=初期の幸運の平均回帰）／metal gate(-0.30・上限+0.018でギリ跨ぎ)とreversalL(+0.17)はCP=N160(2-3週後)から判定=境界ケースはゆっくり＝意図どおり。**DOCTRINE §0-1のライブ再現**（edge2本減衰・gateだけほぼ有意維持）。
**②格言キュー補充**: proverb-daily-autoが**7/15から4日連続キュー枯渇エスカレ**（#1〜15全公開・水増しせず正しく待機）→PROVERB_GUIDE.mdに**#16〜24の9本追記**（先頭=事件は売り事故は買い🚨・キオクシア急落を第三類型の一般論素材に使える設計・銘柄推奨禁止を行内明記／山高ければ谷深し・天井三日底百日・押し目待ちに押し目なし・行き過ぎもまた相場・命金・万人強気（宗久）・セルインメイ・国策に売りなし）。mw check緑→sync 232成功。**7/18 15:41の手動runは無出力で終了**（90分監視・公開/エスカレ/迷子ブランチ全部なし＝当日10:12回の枯渇エスカレ記録を見て1日1本を保守的に解釈した可能性）。二重公開リスクがあるため再手動runはせず、**7/19 10:12の定時運転が#16(事件は売り事故は買い)を拾うのを確認する**（キューのmain反映は確認済み）。

## 🛠️ 7/16 JP朝タスク全滅→根治（Modern Standby起因・コードのバグではない）

**事象**: 7/16朝、ローカル4タスク（JQ_Lake 5:30/JQ_Screen 5:45/JP_Daily 6:00/JP_Health 8:00）が全滅＝DAILY_SUMMARY.mdが7/15のまま。**原因**=PCがModern Standbyで定刻に走れず→7:20復帰で3本同時起動→直後に再スリープ→壁時計換算の実行上限45分を超過し次の復帰(12:01)で0x41306強制終了。**番人JP_Health自身も同型で死亡**（12:01の短い復帰で起動→再スリープ→5分上限）＝アラートtxtが出ず沈黙。GitHub Actions側（update-market-news/autopublish/signal-lab 041）は全て正常。
**復旧✅**: 4本を順に手動再実行（レイク7/15分補充→スクリーナー→カード7/16 20:44生成→ヘルス5項目✅・全exit 0）。
**恒久対策✅（Set-ScheduledTaskで設定変更のみ・bat/py無変更）**: ①4タスクの実行上限を45m/30m/5m→**PT8H**（スリープ中プロセスは休止→復帰後に完走できる。0x41306はS系コードで「失敗時再起動」の対象外＝上限延長が本命）②失敗時10分間隔×3回再起動（本物の失敗=ネット断等向けの保険）③**番人を平日8:00+12:30の2回に増発**（朝の1回が死んでも昼に検知）。次回トリガー7/17で平常運転を確認。

## 📰 7/15 記事#6公開（Q15素材消化）＋autopublish 5記事のローカルreconcile＋⚠️日付事故（修正済）

**①巨匠記事#6=✅公開済み（2026-07-15）**: `guide-masters-006-dual-momentum.html`（Q15資産クラスDM=GEM原典回帰の正直な❌＋対株式DD半減）。ゲート3本=数値36項目を`_dm_asset_class_summary.json`と機械突合（scratchpadの使い捨てスクリプト・金trainDDの丸め-30.1→-30.0%を1件修正）→SVG3枚/ナビ10/kinsho-v1×3をブラウザJS検証→**Opusコンプラ監査🟢白（修正なし）**→`mw publish`→`mw deploy --trigger`（sync232成功・workflow 204・ライブ200・カード掲載確認）。カテゴリ=巨匠の教え検証。**公開翻訳規則遵守**（金の強さは歴史的観察と明記・将来非保証・直近の選択資産は非掲載）。

**⚠️同日=公開日付事故（#031と同型の新変種・即日修正済）**: セッションが7/12(日)朝に開始→中断→7/15(水)夜に再開されたが、**冒頭で取ったGet-Date(7/12)を再開後も信じて7/12付けで公開**（記事datePublished/カード/更新履歴の3ヶ所）。GitHubのworkflowタイムスタンプとautopublish記事が「3日分余分」な違和感から発覚→サーバー時刻突合で確定→3ヶ所とも7/15へ修正・再デプロイ済み。**教訓=①日付を書く直前に必ずGet-Dateを取り直す（セッション冒頭の値を使い回さない）②harness注入のcurrentDateとローカル時計の不一致は中断・再開のサイン**。**🔴オーナー提案**: `publish_article.py` に signal-lab同様の日付ゲート（記事の公開日≠今日JSTなら停止・`--allow-backdate`で免除）を追加したい＝ゲート4本は人間専任のためオーナー承認/実施待ち。

**③Q18価格アノマリー2本=❌同日検証完了（idea-scout転記→即検証の初サイクル）**: `_jp_q18_price_anomalies_screen.py`＝P1高MAX月次(Bali MAXロッタリー)=train -0.56%ns→**holdout +0.81%方向反転**（2025+上げ相場で高MAX優位=オニール系と同型のレジーム依存・⚡H5爆騰フラグとの重複8.6-11.1%=別物）／P2週次ルーザー(Jegadeesh)=**+0.08/-0.03%≒完全ヌル**（古典逆張りは週次粒度で消滅）。実装前に補遺でL単位換算を明記（月次L=2・週次L=3）＝出目未見のまま数式確定の手順を維持。DOCTRINE §3結晶化+anchors 60件・Q18はqueue_archiveへ退避(registry archived)・slugs=tested更新。**⚠️DOCTRINE 24.2KB=warning 1（+0.2KB超過）＝次のdeclutterで§3スタブ化（Q17完了後は15行超え）**。**キュー残=Q10・Q17（会計アノマリー2本=次candidate）・アレンジD**。

**②publish時のmw checkでリンク切れ5件検出→reconcile完了**: autopublish公開済みでローカル未取込の5記事（nikkei-vs-topix⑲7/10/currency-risk⑳7/11/dividend-basics/investment-scams 7/14/stock-tax-basics=7/12〜14分）をGitHub mainから取り込み＋SYNC_FILES登録（⑱と同じ定石）。**autopublishが動くたびローカルに孤児リンクが溜まる構造**＝カード付きguides.htmlはreconcileで来るが記事本体が来ない。頻発するようならreconcile自動化を検討。

<!-- 7/11の詳細節（Q8金ラボ2R=合格2本とも防御価値で休眠／シグナルメールMT4幅併記+週末閉場ガード／Q16 NYランチ回避アーム／Q11ズールー前向きアーム+fins月次タスク／Q14防御カタログ🛡4/6=適用済／Q15資産クラスDM❌／実行系レッドチーム監査19件=EA側8件が宿題⑤／_goal_math+growth_levers台帳）は 2026-07-15 に SESSION_ARCHIVE.md へ退避。要点はauto-memory各ファイルとDOCTRINE/queue_archiveに反映済み。 -->

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

### 🔜 次セッションで最初に確認（在flight・2026-07-16向け）
- **⓪セッション冒頭の新ルーチン＝`python mw.py evolve`**（DOCTRINE突合+キュー+トラッカー鮮度・トークン0）。⚠️**日付は作業の直前に必ずGet-Dateを取り直す**（7/15日付事故の教訓＝冒頭の値を使い回さない・auto-memory feedback_date_freshness）。
- **⓪-A 朝の自動化継続確認**＝`python -X utf8 _jp_health_check.py`（5項目✅）＋`JP*_要確認.txt`無し（7/12朝=週末で対象外・7/13〜7/15朝は未確認＝次セッションでアラートtxtの有無だけ見る）。
- **⓪-B autopublish**＝7/12〜7/14分は3本公開を7/15のreconcileで確認（dividend-basics/investment-scams 7/14/stock-tax-basics）。**7/15と7/16朝の記録は未確認**（7/15はguides.htmlにカード無し=薄い日スキップ or エスカレの可能性→REVIEW.md/台帳を確認）。⚠️クラウドHTTP自己チェック失敗（Cloudflare 403）が続くようなら要観察。
- **⓪-🔴オーナー判断待ち＝publish_article.py への日付ゲート追加提案**（記事の公開日≠今日JSTなら停止・`--allow-backdate`免除・signal-lab date_check と同型）。7/15の日付事故の恒久対策＝ゲート編集は人間専任のため承認待ち。承認されたら次セッションで実装。
- **⓪-C idea-scout-weekly**：✅初定時運転7/12成功→**7/15転記完了（6件処理）**＝Q17会計アノマリー2本バッチ（資産成長・アクルーアル=TA/NP/CFOはfinsキャッシュにあり実装可）＋Q18価格アノマリー2本バッチ（MAXロッタリー・週次リバーサル=レイクのみで可）を事前登録（mw evolveで登録簿SHA記録済み・出目未見）。粗利プレミアム=watch（J-Quants財務にCOGS/粗利なし）・月末月初=tested（LW4個別株棄却の実質重複）。slugs 6件追記済み。次回の受信箱確認=7/19(日)14:00運転後。
- **⓪-D 進化ループ続き＝次の本命は Q17 会計アノマリー2本バッチ**（資産成長・アクルーアル。設計は queue に登録済み・実装は #1/#4 のPIT財務インフラ+`_jp_method_audit.py`流用＝`_jp_q18_price_anomalies_screen.py`が直近の雛形）。他の候補=growth_levers残（②b国外OOS／④promise audit／⑤プレイブック）・アレンジD（グレアム防御×PEG複合）。**✅7/15消化済=記事#6公開・Q18❌**。TT3=月1回・Q11=毎月1-3日タスク自動。**8/1以降の最初のセッションで7/31 formation凍結を確認**（`mw evolve`のQ11行がformation 1/12になっているはず）＋**8月にmw screen📅列の初発火を確認**（Q1決算シーズン・元データ=J-Quants earnings-calendar・キャッシュ`_jp_earnings_calendar.json`）。**DOCTRINE 24.2KB=warning 1＝次のdeclutterで§3スタブ化**。
- **⓪-E 巨匠アレンジ枠の残り候補（B=Q13は7/9完了）**：
  **A**=❌7/11検証済み（Q15・単一資産超えず=記事#6素材）／
  **C**=✅Q11で7/11実装済（screener参考列だけ任意で未）／**D**=グレアム防御×PEG成長の複合1本（複合は前科あり=期待控えめ明記）。
  ※「すでに生きているアレンジ」の整理も記事ネタ（赤三兵→連騰≥4危険ゲート・タートル資金管理→ATRベースSL/2%ルール・**G4逆張り→🔪回避フラグ（Q13）**＝原型のエントリーは死んでも部品は生きる）。
- **⓪-F 文書declutter**：7/15時点=HANDOFF 27.4KB（7/11節をARCHIVE退避）/queue 10.7KB（Q18退避）/CLAUDE 32.0/**DOCTRINE 24.2KB=warning1のみ残（次のdeclutterで§3スタブ化）**。以後もこの水準を維持（節が増えたら完了節をARCHIVEへ）。
- **⓪-G ✅済（7/9夜）routineによるリンター編集の再発防止＝三層で実装**: オーナー決定=**完全禁止**（等価修正も不可・赤はエスカレのみ・ゲート修正は人間専任）。①`AUTOPUBLISH_GUIDE.md`=固定ゲート4本（check_guide_draft/check_site_consistency/signal_lab_verify/publish_article）の編集・commit禁止+7/9違反実例を明文化 ②routineプロンプト更新済（手順4/7/絶対厳守を強化。⚠️**プロンプト禁止は7/8夜から存在したのに破られた実績あり**＝コード検知が本命） ③`check_automation_health.py`にチェック④新設=直近26hでゲート4本をオーナー/github-actions[bot]以外のauthorが変更→warn Issue（ローカル実測で7/9違反commit `80abc63` を正しく検知✅）。**⚠️7/10 09:30の運転で既知の7/9違反commit（対応済）が1回Issue化した可能性＝あれば無視してクローズ**。以後の検知は本物。
- **⓪-H ⚡news-ticker**: ✅7/11朝確認=夜間毎時運転OK（updated 7/11 10:03・30件）。残1件=**「📰経済を既定で非表示（ボタンで表示）」は1行で変更可＝オーナーの好み待ち**（夜間はYahoo!経済由来の消費者ネタ多め問題）。
- **⓪-I ✅済（7/9 20:30）guides.htmlカード消失＝実は「消失」でなく「未完了公開」**: git履歴調査の結果、カードは一度も存在しなかった（巻き戻しでも取り下げでもない）。**真因**=7/6のnews-daily-autoが当時のSYNC_FILES縮小問題で `check_site_consistency` exit=1→設計どおりエスカレ（commit 1200e77b=記事HTML+NEWS_LEDGERのみpush・カード/履歴/SYNC登録なし）→台帳の「再公開手順（人間が実施）」が3日間未実施のまま放置されていた。**対応**=台帳手順どおり完了（コンプラは当時Opus×2で🟢白済・noindexなし）：カード挿入（7/7と7/5の間の正位置）+SYNC_FILES+更新履歴→`mw check`緑→sync（guides.htmlはstaleガード🚫→diff確認=カード9行のみ→定石--force・commit 156f63e=+9/-0）。**番人③再実行=58/58✅**・ライブ記事200・sitemap収載済み。ついでに⑱`guide-economic-indicators-basics.html`のローカルreconcile+SYNC_FILES登録も実施（mw checkが検出）。**教訓=番人③の検知は「エスカレ回の未完了公開」でも発火する。まずNEWS_LEDGER.mdの該当日エントリを見ると1分で原因が分かる**（GitHub側LEDGERの7/6エントリは「公開準備」のまま=SYNC禁忌のためローカルから更新不可・実態は公開完了）。
- **①巨匠シリーズ**：#6=7/15公開済み（Q15資産クラスDMの正直な❌）。次記事候補=「#7 割安成長（ズールー）×グレアム再訪」＝Q11前向き設計・Q12再監査が素材（両方完了済みでいつでも書ける）。
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
