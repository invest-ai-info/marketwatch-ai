# 🔖 セッション引き継ぎ（最終更新: 2026-07-07 昼）

## 🧬 7/7 進化ループ構築（オーナー依頼「投資スペシャリストとして日々自律進化するシステム」）

- **進化ループ6段**＝①INTAKE(idea-scout-weekly) ②QUEUE(事前登録) ③VALIDATE(既存エンジン) ④CONSOLIDATE(DOCTRINE)
  ⑤APPLY(昇格メール/朝カード/discipline/相談) ⑥REFLECT(mw evolve/月次監査)。**単一ソース＝`research/DOCTRINE.md` 冒頭**。
- **新設（ローカル専用・SYNC外）**: `research/DOCTRINE.md`（検証済み知識台帳・エビデンス2軸格付け・全数値出典付き）／
  `research/hypothesis_queue.md`（事前登録キュー Q1〜Q10・登録簿SHA256で改竄検出）／`_doctrine_check.py`
  （番人=アンカー21件突合+登録簿+サイズ予算+§1構造検査。**固定オラクル扱い**）／`mw evolve`（決定論ダイジェスト・トークン0）。
- **新設（クラウド）**: routine `idea-scout-weekly`（`trig_01DtET4sXeLYkRbyX7jKzpYb`・毎週日曜14:00 JST=cron `0 5 * * 0`）＝
  WebSearchで検証可能な新手法を最大3件→`drafts/idea-inbox.md`へ**追記のみ**（SYNC禁忌登録済・automation-health監視行追加済）。
  重複回避=`drafts/idea-tested-slugs.txt`（SYNC入り・手法名のみ）。在庫ゲート=未消化10件でスキップ。
- **品質保証**: 棚卸し5エージェント→DOCTRINE起草→敵対的検証5+設計クリティーク3（自動化事故/トークン/科学的厳密性）→
  指摘20件を全て反映（数値転記ミス0件・出典タグずれと文脈落ちを修正）。SYNC_FORBIDDENに「_プレフィックス=ローカル専用」規約を追加（REDテスト済）。
- **運用**: セッション冒頭は `mw evolve` だけ（DOCTRINE全文Readしない＝読み方プロトコルがDOCTRINE冒頭に）。
  検証完了→DOCTRINE更新→`_doctrine_check.py`緑が儀式。公開翻訳規則（✅/合格を記事に書かない）はDOCTRINE冒頭。
- **⚠️訂正**: mw.py は **SYNC対象**（GitHubに存在。従来メモの「未追跡」は誤り）。cmd_evolve にクラウド実行ガード実装済み。
- **未実装バックログ（次回以降・優先度順）**: (a) publish_article.py に check_guide_draft のハードNG検査を共通化（手動公開レーンの
  コンプラ穴＝rigor監査のcritical） (b) アンカーの name-key参照（rows.4→rows[hyp=TT3]） (c) 鮮度検査のcontent-hash化
  (d) §1b新規エントリの3点アンカー必須規則 (e) idea-inbox削除行のdiff検査 (f) CLAUDE.md 32KB超のトリム。

## 🐢 7/7 TT3前向き検証を事前登録・稼働（オーナー承認「推奨通り」）

- **新設 `_jp_turtle_tracker.py`（ローカル/SYNC外・`_`で自動ブロック）**＝TT3専用の前向きトラッカー。
  発火ルール（liquid×20日高値ブレイク×MA50>MA200）とfwd60・日付クラスタboot(B3000/seed42)を
  **`_jp_turtle_screen.py`から1バイト変えず流用**（参考train diff+0.67%p0.003・holdout+1.39%p0.000が
  screen値と点推定完全一致＝忠実さ確認）。状態=`_jp_turtle_tracker.json`。
- **事前登録（2026-07-07ロック・以後不変）**: 登録日以降に発火しfwd60解決した観測のみ計上。
  昇格=前向きN≥300 かつ diff60の95%CI下限>0 かつ blowup≤対照（**チェックポイント検定**=Nが300倍数越え時のみ判定＝逐次覗きのα膨張抑制）。反証=CI上限<0。**昇格しても旗立てのみ＝発注/配信に触れない**。
- **現況 N=0/300**＝レイク末(7/1)＜登録日(7/7)＋fwd60は60営業日後に解決＝正常。**初判定は約3か月後**
  （TT3は1日約90銘柄発火＝解決さえ進めばN300は数営業日ぶんで到達）。R枠でなくfwd60専用枠＝検証時の指標に忠実。
- キューQ7を💬→📊前向き観察に更新。DOCTRINE §1b/§5＋アンカー2件追加（計23件突合）。**番人修正**＝
  登録簿ハッシュから「状態/履歴/補遺/備考」を除外（状態遷移は許し、合格基準/ルール/検証設計を凍結）。
- **次回チェック**=セッションでたまに `python _jp_turtle_tracker.py`（レイク要・約1分）。クラウドroutine不可
  （レイクはローカルのみ）＝月1回ペースで十分（fwd60は月次でしか意味的に動かない）。

## ✅ 7/7朝の無人運転確認（旧宿題⓪）

- **autodraft**: ⑭⑮⑯を正しくスキップし**⑰インフレ（draft-inflation-real-return.html）を下書き✅**＝スラッグ重複ゲート実戦初勝利。
  ただし着地が09:11 JST（定時05:30から大幅遅延=cron混雑か）→このため**08:40のautopublishは「対象なし」の正常空振り**
  （last_fired_at 23:40:45Z=定時実行は確認済）。**⑰の公開は明朝08:40**＝明日確認。
- **signal-lab #032**: **日付ゲート初運転を通過し7/7付けで自動公開✅**（datePublished/表記とも正しい）。
  ⚠️ただし公開表記に「（下書き中）」残骸→**ライブ修正済（commit afb35376）＋`signal_lab_verify.py` date_check に残骸検査を追加**（sync済）。

## 🌙 7/7夜 進化ループ初の自動検証サイクル（Q1 ダーバス・ボックス）

- **③VALIDATE→④CONSOLIDATE を初めて実走**（キューの次候補Q1を検証・`_jp_darvas_screen.py`ローカル/SYNC外）。
  結果=**リターン棄却・防御は再現・TT3の部分集合**の三点。4変種（N20/X10%・N30/X15% × 出来高1.5x有無）とも
  **train diff60+（q<0.10）→holdout diff60負**（N20/X10%: -1.22%）で方向反転＝BH-FDR不合格。だがblowup
  4.5-5.8% vs対照17-18%で両期間防御を再現。**TT3と96.5%重複＝ほぼ部分集合**＝箱＋高値近接フィルタがTT3の
  リターン(holdout+1.39%)を防御に変換（§0-1「守りだけ再現」の再確認）。DOCTRINE §3へ結晶化・採用せず。
- キューQ1を❌棄却に更新（状態行のみ＝登録簿は本文凍結を維持）・idea-tested-slugs更新・カタログに結果追記。
- **番人の衛生改善**＝アンカーJSONを `research/_doctrine_anchors.json` に外出し（DOCTRINE 24.4→21.4KB・
  機械データと人間台帳を分離）。SESSION_HANDOFF 33.6→21KBに減量（7/6分をARCHIVEへ退避）。25アンカー突合・warning0。
- **Q2 ワインスタイン ステージ2も検証＝❌棄却**（`_jp_weinstein_screen.py`）：150日MA上抜け×勾配>0の2変種とも
  train +2.05%(q<0.10)→**holdout -0.05%**で崩壊・防御も弱い。**TT3とわずか5.7%重複＝独立した順張りなのに崩れる**
  ＝TT3の特異性を逆に補強（トレンド確認付き順張り一般は効かず、TT3の特定組合せだけ生存）。DOCTRINE §3結晶化。
  → ダーバス(TT3の部分集合)とワインスタイン(TT3と独立)の両方が崩れ、**順張りで生き残るのはTT3の1点のみ**が固まった。
- **次候補=Q3 酒田五法**（客観化可能な三空/赤三兵等）＝パターン系第1弾。以降 Q4グランビル/Q5デュアルモメンタム/Q6ズールー。

## 🔍 7/7深夜 日本株スクリーナー新設（オーナー依頼「個人用・後から項目追加可能」）

- **`_jp_screener.py`（ローカル専用/SYNC外）＝`mw screen`**：全上場銘柄（レイク直近1.3年＋J-Quants `equities/master`
  全4,437銘柄マスタ=業種/規模/名前・7日キャッシュ`_jp_listed_master.json`）を**検証済み知見だけ**で採点。
  流動性床1億通過=約1,700銘柄。列=⚠️危険スコア0-4（危険ゲート同一定義）/🔴赤字（jp-stock-info・400銘柄のみ他は?）/
  🛡グレアム0-6（_jp_doublebagger_graham.csv流用）/🛡防御列（QA2低ボラ×QA1の52週高値近接＝**宿題Q9をこれで適用済み**・
  ◎16銘柄）/🐢TT3本日発火（⛔未採用・観察用と明記・7/1は40銘柄）/流動性/直近リターン。
- **拡張＝列プラグイン登録制**：関数1個＋COLUMNSに1行で新列（ヘッダに手順明記・検証済みでない列は「参考」表記必須）。
- 使い方例：`mw screen --max-danger 0 --min-graham 4`／`--defense`／`--tt3`／`--code 7203`（1銘柄内訳）／
  `--sector 銀行`／`--refresh-master`。出力=コンソール+`_jp_screen_latest.csv`（Excel可）。
- コンプラ：個人用・非公開（`_`プレフィックスで流出コードブロック済）。公開版はデータライセンス（J-Quants個人利用）＋
  無登録助言リスクで弁護士相談後の別設計（銘柄名を出さない基準チェッカー等）。
- 残タスク（任意）：ETF/ETNの除外フラグ（masterのProdCat活用）・ウォッチリストダッシュボードへの防御列追加・
  赤字判定の全銘柄化（要J-Quants財務join）。
- **レイク自動補充を新設（オーナー依頼）**：タスクスケジューラ `MarketWatch_JQ_Lake`（毎朝05:30・
  `python -X utf8 _jp_jquants_daily_lake.py`＝差分のみ数十秒・既存JP_Dailyと同一流儀・StartWhenAvailable）。
  **番人 `_jp_health_check.py` に check_lake() 追加**（毎朝8:00・レイク最終日<前営業日なら
  `JPレイク未更新_要確認.txt`・GREEN動作確認済）。
- **⚠️副産物で本物の異常を発見・根本修正済＝7/7朝のjp_daily未完走**：6:40起動→30分制限(PT30M)で強制終了
  （Last Result 267014＝SCHED_S_TASK_TERMINATED）。**真因特定**＝手動実行は299秒(5分)で完走＝肥大ではない。
  ノートPCだがバッテリー/アイドル停止は既にOFF＝**時間制限に本当に達した**。根本＝`incremental_fetch()`が
  約400銘柄をループ・各Yahoo呼出は`timeout=20`だが**ループ全体の上限が無く、朝の起動直後(WiFi未接続)に連続
  タイムアウトすると最悪133分**→30分killで心拍も残らず。**修正**=①`jp_daily.py`のフェッチループに壁時計
  バジェット`FETCH_BUDGET_SEC=720`（超過で残り銘柄スキップ→下流はキャッシュ続行＝総killより安全・syntax/wiring
  テスト緑）②両タスクのExecutionTimeLimit PT30M→**PT45M**（フェッチ上限12分+下流3分に余裕）。当日カードは手動
  再生成で心拍7/7・番人全✅復帰済。**明朝6:00が修正後の初運転**（万一またコケても番人が8:00にアラートtxt）。

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

### 🔜 次セッションで最初に確認（在flight・2026-07-08向け）
- **⓪セッション冒頭の新ルーチン＝`python mw.py evolve`**（DOCTRINE突合+キュー+トラッカー鮮度・トークン0）。
- **⓪'7/8(水)朝**：(1)08:40 autopublish が**⑰インフレ(inflation-real-return)を公開するか**（7/7は下書き遅延09:11着地のため空振り=正常） (2)autodraft 05:30の遅延が再発するか（7/7は3.5h遅延） (3)⑱以降のキュー消化継続。
- **⓪''idea-scout-weekly**：初回手動E2Eは7/7実施済み（結果はこのセッション末尾参照）。**初の定時運転=7/12(日)14:00 JST**→翌セッションで drafts/idea-inbox.md を確認しキュー転記（転記したslugは drafts/idea-tested-slugs.txt へ追記+sync）。
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
