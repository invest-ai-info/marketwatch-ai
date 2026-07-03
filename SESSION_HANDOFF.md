# 🔖 セッション引き継ぎ（最終更新: 2026-07-03 未明）

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
- **🆕 三重監査＝検証設計/文書/バグ（7/3・Fable初仕事）**：**①signal-lab方法論の穴4つ**＝(1)相関シグナルの独立扱い（SE=sd/√n・同日複数発火25%＝実効N過大→FDR通過過多。jp_open_analysisは日付クラスタbootstrap済で自家基準不統一）(2)holdoutの遡及汚染（2021+は過去の探索で接触済・grid次元tierも結果を見て追加＝擬似OOS。真の砦は前向きN）(3)トラッカー逐次検定＋ラチェット（毎日CI判定＝α膨張・promoted/rejected固定）(4)expired完全除外（closed()=tp/slのみ＝meanRが解決条件付き期待値）。JPモメンタム側は合格（翌バーOpen・あいまいバー保守SL・打ち切り除外・netR済）。**②文書乖離5件→4件修正しsync済**（AUTODRAFT/NEWS_DAILYガイド nav9→10・CLAUDE.md月次cron 1〜3日・MY_TRADING_RULES実績を7/3再計算に更新）。**③静かに壊れるバグ10件検出**＝最重要3件が未修正：jp_daily心拍が工程失敗でも書かれ健全性が偽陽性（+古いsizing_planでカード履歴汚染）／mw.py `_run_capture` cp932デコードで🚫stale検知不能／build_jp_rankings部分失敗でも偏ったランキングをexit 0公開。他=1mo固定取得の欠損穴・run()エンコーディング・tracker生json.load・sync欠落ファイル成功扱い・祝日except誤アラート。**当日実装分2件（前向き境界・基準低下）は修正済み。残りはオーナー判断待ち**。
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

## 🇯🇵 日本株：EV最速化ロードマップ＋施策1（ネットR）実装（2026-06-26）

「検証を日本株に切替・期待値を最速で上げる」依頼に対し、4独立レンズ（クオンツ/リスク執行/データ優位/競争戦略）で検討→収束。**詳細は非公開ローカル `JP_EV_ROADMAP.md`**（JP個別戦略は🔴黒＝public SYNCしない）。
- **総意**：研究はもう十分深い。EV漏れは"新エッジ探し"でなく①研究→現実(コスト未計上)②研究→行動(実行規律)③未活用の無料データ(主体別フロー)。新シグナル追加は多重比較で精度低下＝逆効果。
- **✅施策1完了＝全エッジをネットRで再計算**：`_jp_momentum_edge.py` に `cost_r(size_class)`（単一ソース・往復コスト表）→ `netR5/10/20` 列生成。`_jp_momentum_validate.py --net` でネット検証（既定グロス＝daily非破壊・既存R列不変）。**結果**＝厚いエッジ（続伸合成・厳格+0.300/KEEP∩続伸+0.248）はコスト耐性あり、**超小型・規模外・連騰過熱はnetで負に転落**。diffR(対プール差)はコスト相殺で不変＝netで効くのは「絶対meanRが0超か＝実際に儲かるか」。OOSでは攻め減衰・守り持続（コストよりOOS減衰が大リスク）。⚠️JPファイルはpublic SYNC外（private repo `jp-momentum-research` 反映は別途）。
- **✅施策2完了（2026-06-27）＝危険スコア→分数ケリーのサイジング**（`_jp_sizing_engine.py`・ローカルSYNC外）：①危険スコア倍率を手置き`{0:1.0,1:0.5}`→ネットR由来の分数ケリー`{0:1.0,1:0.37}`（20k観測のnetR10からKelly実測。score≥2はnetで負→0）。②モードbase_fをフルケリー(0.122)分数で再定義＝**オーナー判断でハーフケリー**へ（growth0.12→0.06/balanced0.08→0.04/preserve0.04→0.03、CAP_F0.16→0.08）。clean×受益 15%→7.5%（レバ1.88x→0.94x）。ハーフ＝成長率フルの約75%を変動半分で・推定エッジのブレ/OOS減衰に強い。反映は"推奨"（発注はオーナー）・可逆。
- **✅施策3完了（2026-06-27）＝赤字回避ゲートを検証段に統合**（`_jp_momentum_validate.py`・ローカルSYNC外）：観測✅→検証❌→トラッカー✅ の穴（validate）を塞ぐ。fundamental akaji（点in-time財務・直近開示赤字）を技術ゲートと直交する軸として追加。net実測＝黒字netR+0.073/blowup7.6% vs 赤字netR+0.000/blowup15.9%(2倍・perm_p0.006有意)。統合ゲートKEEP_ALL=netR+0.105/blowup5.5%(プール8.2%→最小)。サイジング側は対応不要（ウォッチリストは黒字選別済）。
- **✅施策4完了（2026-06-27）＝投資部門別フローをレジーム判定に統合**（ローカルSYNC外）：`build_jp_investor_flow.py`(新規)がJPX無料週次Excel`stock_val_1_*.xls`から海外投資家・個人の当週ネット(買い−売り)を取得・マージ蓄積→`_jp_investor_flow.json`。`_jp_regime_cockpit.py`に4つ目の確認シグナル（外国人フロー4週累計・confirm/diverge）を追加＝**コア合議の閾値は不変・判定には未算入**（昇格は前向き検証後）。`jp_daily.py`④.3に組込。検証＝外国人+10,681億/4週+1,581億→買い越し基調・risk_on✅確認。build_jp_investor_flowは非公開JP（public build_jp_margin/rankingsとは別）。
- **✅施策5完了（2026-06-27）＝発注規律カード化**（`jp_daily.py`→`DAILY_SUMMARY.md`・ローカルSYNC外＝個別銘柄含むためpublic🔴黒）：サイジング×入口タイミングをcodeマージ→「◎今すぐ妙味(サイズ十分×入口OK)／○監視(入口待ち)／✕見送り(危険≥2)」に整理＋レジーム最上段に外国人フロー＋🛡️撤退規律ライン。**施策2のf≥0.10抽出が0件になるバグも是正**。検証＝◎33/○15出力OK。DAILY_SUMMARY/jp_dailyともSYNC外確認。
- **✅施策6完了（2026-06-27）＝続伸=risk_off条件付きトラッカー＋点火アラート**（ローカルSYNC外）：`_jp_momentum_tracker.py` に `tag_regime()`(market_regime.csv join)＋mask `m_cont_riskoff`(続伸×risk_off)＋SEED `continuation_riskoff`(promote_n80)。検証＝holdout 続伸×risk_off meanR+0.367/blowup0%（無条件版+0.023＝レジーム依存裏付け）・perm_p0.524＝OOS薄n~22で前向きN蓄積待ち。`jp_daily.py` カードに risk_off時の🔥点火窓アラート。
- 🎉 **JP_EV_ROADMAP 全6施策 完了（1ネットR/2分数ケリー/3赤字回避統合/4外国人フロー/5発注規律カード/6 risk_off点火）**。共通＝「新エッジ探しでなく既存エッジをコスト/サイズ/規律/需給確認で実トレードに変換」。詳細は非公開 `JP_EV_ROADMAP.md`。
- **残＝時間が律速**：前向きトラッカー各仮説のforward Nが貯まる→🟢昇格→人間が実装(#21の道)。index_long_bonus/外国人フロー/続伸×risk_off は決定算入への昇格を前向き検証後に判断。任意フォロー＝取引コストの実約定ログ更新(cost_r精緻化)/カードのスマホ最適化。
- ✅ **発注規律カードの自動生成をスケジュール化（2026-06-27）**：Windowsタスク **`MarketWatch_JP_Daily`**＝**平日7:00**に `python -X utf8 jp_daily.py` を自動実行（WorkingDir=作業フォルダ）。堅牢設定＝**電池でも起動**(DisallowStartIfOnBatteries=False/StopIfGoingOnBatteries=False)・**取りこぼし遅れ実行**(StartWhenAvailable)・30分上限・ユーザー権限(非管理者)。`-X utf8`でcp932絵文字クラッシュ回避。既存`MarketWatch_YT_Shorts`(夜)と同方式。スケジューラ起動・手動実行とも検証済。⚠️**アプリ非依存だがPCが起動(ログオン)している必要**（寝てて逃したら起動後に自動で遅れ実行）。出力=`DAILY_SUMMARY.md`(ローカル・個別銘柄含むためpublic🔴黒・SYNC外)。毎朝の運用＝カードを上から読む→絞って判断→自分で発注+損切り。時刻変更は `Set-ScheduledTask`/タスクスケジューラGUIで。
- ✅ **実行時刻 7:00→6:00 に変更（2026-06-27）**。
- ✅ **🥇健全性監視（沈黙の失敗の番人・2026-06-27）**：①カード冒頭に「🕖カード生成: 日時」バナー（今日でなければ自動更新停止＝開いた瞬間に分かる）＋ jp_daily が成功時に `_jp_heartbeat.txt`(今日の日付)を書く。②Windowsタスク **`MarketWatch_JP_Health`（平日8:00・電池OK・StartWhenAvailable）**が `_jp_health_check.py` を実行＝心拍≠今日なら `JP_カード未更新_要確認.txt` をOneDriveフォルダに作成（スマホで気づける／次回正常更新で自動消去・週末はスキップ）。サイトの automation-health と同思想をローカルJPにも。
- ✅ **🥈昇格アラート（2026-06-27）**：`jp_daily.py` カード上段に、前向きトラッカーで🟢昇格/⛔反証が出た仮説を「🎯要対応」表示（手でtracker見なくてよい）。未昇格の間は「🎯昇格まで N=x/y（あとz）」の進捗表示。
- 🥉 **取引ログ（推奨・新規コード不要）**：既存 `Googleフォーム→スプレッドシート→my-trades.json` 導線（`MY_TRADES_SETUP.md`）でJP実取引を記録すれば、(a)本物の前向き勝率/期待値、(b)実約定スリッページから施策1の `cost_r` を実測更新、が将来できる。スマホ入力が最も続く＝オーナーの習慣化待ち。
- ⚠️ 新スクリプト `_jp_health_check.py` もローカル/SYNC外（JP研究）。
- 全レンズ一致のアンチパターン：派手なBT数字/レバ100倍狙い（破産確率の崖）/HFT速度勝負＝やらない。**生き残って複利が1億への唯一解**。

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

### 🔜 次セッションで最初に確認（在flight）
- ✅ **投資格言シリーズ 自動化＝初回成功を確認済（2026-07-01）**：cloud routine **`proverb-daily-auto`（`trig_01P8Jjut79fHWoiALk4mfuJQ`、毎日10:12 JST）**（[[project_proverb_series]]）。#1 atama-shippo は6/30手動公開（白）。**初回7/1 10:12 JST発火→#2「買いは家まで売りは命まで」(kai-ie-uri-inochi/44KB) を生成→Opus二重ゲート🟢白(初期)→修正なし→🟢白(独立確認)→自動公開→ライブ確認済**（SVG図・数字仮例・免責上下・危険語ゼロ・9セクション）。台帳 `drafts/proverb/PROVERB_LEDGER.md` に記録・次候補#3=落ちるナイフ設定済。**＝完全無人パイプラインが実証された**。以後は台帳を時々見るだけ（エスカレ🚩時のみ人レビュー）。
- ✅ **ニュース鮮度カットオフ＝解決済（2026-06-30 ライブ確認）**：オーナー「古いニュースが表示される」→原因＝各カテゴリ「関連ニュース」と「🔍信頼性検証済みニュース」は `fundamental-context.json` ブリーフィング由来で、描画コード（`build_card_news_from_briefing`/`build_trust_news_html`）に**鮮度カットオフが無く**、新鮮な記事が少ないカテゴリ（特に暗号資産）で古いHIGH/MID記事（5/14 CLARITY法案等）が3枠埋めに生き残っていた（TOP3の48h除外とは別系統）。**修正＝`BRIEFING_NEWS_MAX_AGE_DAYS=10` カットオフ追加**（>10日除外・日付なしは残しフォールバック温存）。GitHubが`_history_items`で先行＋**CRLF**だったため**GitHub最新に差分だけPUT**（commit `a89e693854`）→ローカルも最新へ同期→update-market-news #829 success。**ライブ確認＝最古6/25・5/14と6/17は消失**。調整は定数1つ（`generate_market_news.py`）。再発時はブリーフィング生成側の日付誤りを疑う。
- **ニュースRSS修正のライブ反映確認**：6/28に死んだロイターRSSを差し替え＋update-market-news を trigger 済。**live の index.html ニュースにロイター日本（日本語）が戻っているか**を確認（WebFetch等）。
- **AdSense 再審査の結果**：6/27 申請済（[[project_adsense_review]]）。承認/却下を確認。却下ならニュース記事もnoindex等の next step。
- **JP朝カードの初稼働**：月曜6:00に `MarketWatch_JP_Daily` が初の自動実行→`DAILY_SUMMARY.md` が当日日付で更新されているか（番人 `MarketWatch_JP_Health` 8:00 も）。
- **整理係**：`mw declutter` は現在0件。月次 `MarketWatch_Declutter` が `DECLUTTER_REPORT.md` を出したら確認。

- ✅ **update-market-news.yml の失敗は解決済**（2026-06-20 午後・concurrency追加）。原因＝push+dispatch の同時実行レース。今後 `mw publish` を素で使ってもOK。
- ✅ **FOMC結果の信頼性検証＝対応済（2026-07-03）**：現行 results の出典は概ね公式/大手化済み（米雇用統計=BLS+CNBC/CNN等）。残っていた緩さ（investing.com単独でverified=true・substack混入）は routine プロンプト厳格化で対処（アグリゲーター裏取り禁止）。**今晩23時台の実行で新基準が守られるか確認**。
- 🔴 **POLICY dict 更新**：`generate_market_news.py` の `POLICY`（日銀→1.0%／FOMC据え置き）を会合結果へ。未更新だと market-health のスワップ金利差%が陳腐化。
- 📉 **AdSense ＝2026-06-27 再申請済・結果待ち**（[[project_adsense_review]]）。次セッションで結果確認（上の在flight参照）。
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
