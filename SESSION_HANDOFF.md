# 🔖 セッション引き継ぎ（最終更新: 2026-06-28）

新セッションは **このファイル＋ CLAUDE.md ＋ auto-memory（MEMORY.md 経由）** を読めば文脈を復元できる。
2026-06-17 以前の詳細履歴は **SESSION_ARCHIVE.md**（保管庫・後から辿る検索用）へ退避した。

---

## ✅ ④ 記事の「中身」レビュー強化＝品質レーンを公開ゲートに実装（2026-06-26）

機械的な不具合（SVG重なり・免責漏れ・数値とclaim不一致）は決定論で自動ブロック済み。残る「内容品質」をLLMレビューで底上げ。**オーナー判断＝Opusゲートに1レーン統合（独立スコアにしない）**。
- **`QUALITY_RUBRIC.md`（新設・SYNC入り＝品質基準の単一ソース）**：5観点（①リードで結論30秒 ②専門用語の初出説明 ③主張に根拠/数値 ④中立トーン ⑤見出しと中身一致）を ✅/⚠️/❌ で採点。順序＝**決定論コード緑→(a)コンプラ白→(b)品質ルーブリック→公開**。⚠️は表現・構成・補足1文だけで自己修正→再採点（**数値・SVG・claims・主張・免責は不変**）、❌（直すと中身が変わる）はエスカレ。やりすぎ防止＝止めるのは「読者を誤解/理解不能にする欠陥」だけ。
- **両自動ゲートに配線**：news＝`drafts/NEWS_DAILY_GUIDE.md` §8.5＋paste台本 `NEWS_AUTOPUBLISH_ROUTINE.md` 手順5.5／signal-lab＝`SIGNAL_LAB_SOP.md` ゲート節。**cloud routine は実行時にこれらSYNC文書を読む＝sync すれば次回実行から自動適用**（再paste不要・ただし台本も同期済）。`signal_lab_verify.py`（固定オラクル）は不触。
- **効果確認（1記事試行）**＝`guide-signal-lab-015`：①③④⑤✅・②⚠️1件（「BH-FDR多重検定補正」が平易説明なしで登場）。強い記事でも真の指摘1件＝機能・ノイズでないと確認。**数値オラクルが無い news 記事ほど価値大**。
- ⚠️ **未デプロイ**：`mw sync`（QUALITY_RUBRIC.md＋sync_to_github.py＋NEWS_DAILY_GUIDE.md＋SIGNAL_LAB_SOP.md＋本ハンドオフ）が必要。デプロイ後の次の signal-lab/news 自動公開が初の実戦。
- 🔜 **次（任意のフォロー）**：①数本の既存 news/basics 記事に手動でルーブリックを当てて"⚠️→自己修正"を実証（手動 `mw publish` 前のチェックにも使える）②運用後に誤エスカレ/見逃しが出たら `QUALITY_RUBRIC.md` の1ファイルだけ調整。
- 関連：[[feedback_rules_as_code]]（機械=コード／中身=LLMレビュー の住み分け）。

---

## ✅ ニュース精度低下の原因究明＆修正（2026-06-28）

オーナー「サイトのニュースの精度が落ちてきている」→ 調査で原因特定・修正。
- **原因＝RSSフィードのサイレント失敗**：実測したら **ロイター日本（`assets.wor.jp/rss/rdf/reuters/top.rdf`）が0件＝死亡**（他3本は20件）。yfinanceニュースも空（既知の不安定・本番でも空になりやすい）。→ ニュースプールが英語ソース（要翻訳）に偏り源の多様性が痩せ「精度が落ちた」印象に。誰も気づけなかったのはサイレント失敗だから。
- **修正**：`generate_market_news.py` の `RSS_FEEDS` のロイター日本を **Google News経由 `site:jp.reuters.com`** に差し替え（日本語のロイター記事が100件・翻訳不要で復活）。＋`fetch_news` に **0件フィード検知の警告**（`dead_feeds`→`🚨RSSフィードが0件＝要確認`）を追加＝再発時に気づける（ルールはコードで強制）。
- **デプロイ＝reconcile必須だった**：local の generate_market_news.py が GitHub より古く（6/26〜28の自動公開記事の `_history_items` がGitHubにしか無い）、staleガードがsyncをブロック（正しく機能）。→ **GitHub最新版に私のRSS修正だけを当てて現shaでcontents-API PUT**（commit 121339b1・履歴は保持・巻き戻し無し）→ update-market-news を trigger（30〜90分で反映）。`.sync-cache` の generate_market_news.py 基準も新shaへ整合済（次回sync誤ブロック防止）。
- ⚠️ **別件の未解決TODO（精度関連）**：`indicator-result.json`（注目指標バナー）のFOMC等の数値が個人ブログ系出典の疑い（6/18起票・未検証）。一次ソースで要確認＝次の精度改善候補。
- ⚠️ RSS差し替えは Google News 依存（titleに" - Reuters"付く・linkはGoogleNews redirect）。将来 Google News RSS仕様変更時は `dead_feeds` 警告で検知できる。

## ✅ 「整理係」＝ルールの重さ・腐りを定期的に洗い出す仕組み（2026-06-28）

オーナー提案「ルールが増えて重くなったら整理する係がいた方がいい」→ 記憶頼みの"係"は忘れられる罠（＝サイレント故障と同型）なので、**決定論で定期スキャンし候補を提示する仕組み**として実装（自動削除しない＝判断は人間・[[feedback_rules_as_code]]）。
- **`declutter_audit.py`（新規・SYNC入り・読取専用）**：①毎回読む文書の肥大（SESSION_HANDOFF>45KB等）②ハンドオフの✅完了古セクション数 ③SYNC_FILES死に登録 ④使い捨てscript堆積(>30) ⑤記憶件数(>30) を検出→`DECLUTTER_REPORT.md`（OneDriveで見える）に出力。`mw declutter` で実行（mw.pyに追加）。
- **月次自動化**：Windowsタスク **`MarketWatch_Declutter`（4週ごと日曜6:30・電池OK・StartWhenAvailable）**＝放置でレポートが出る。
- **初回B（手動棚卸し）の検出3件**：①SESSION_HANDOFF 54KB（✅完了13セクション）＝**古い完了セクションをSESSION_ARCHIVEへ退避してスリム化が次のアクション** ②使い捨てscript43本＝`_scratch_archive/`へ移動候補（稼働系_jp_*33本は対象外）③SYNC死に登録1件（`guide-auto-us_cpi-2026-05-14.html`）＝**本セッションで除去済**。
- ✅ **整理実施済（2026-06-28）**：(a)古い完了セクション10個をSESSION_ARCHIVEへ退避＝ハンドオフ **55.8KB→25.3KB**にスリム化。(b)使い捨てscript41本を **`_scratch_archive/`** へ移動（active参照ありの`_overshoot_depth`/`_panic_cross`は残置・READMEで可逆と明記・全てSYNC外）。検証＝`mw check`エラー0・主要オーケストレータcompile OK・**`mw declutter`＝検出0件「十分スリム」**。フォルダの.py 133→93本。再発時は月次`MarketWatch_Declutter`が`DECLUTTER_REPORT.md`で気づかせる。

## ✅ 研究日誌#21の昇格エッジ「指数×ロング」を発火エンジンに本採用（2026-06-26）

研究日誌は **昇格＝候補の旗立てのみ・発火/配信エンジンには自動反映しない**ファイアウォール設計（`generate_technical_alerts.py` は signal-lab tracker を読まない＝grep確認済）。#21 で **指数×ロング（NKD/ES/NQ/YM/^FTSE × 買い）が前向きトラッカーで正式昇格**（60.0% 54/90・+0.40R・平均RのCI下限+0.16>0・OOS生存）したのを受け、人間判断で実エンジンへ反映。
- **オーナーのデータ品質チェック（重要・解消済）**：「TP1/TP2 のどちらで利確するかで成績が変わる／後出しで選ぶと不正確では？」→ 調査の結果、`evaluate_signal_outcomes.py` は**最初に当たったレベルを採用（同バーはSL優先＝最悪ケース）**。TP1はTP2より必ず手前なので**勝ちは常にTP1で利確扱い**＝実データ分布も **tp1:341 / sl:497 / tp2:0**。つまり「TP1単一エグジット」を最初からモデル化（look-ahead無し）。#21の+0.40R＝0.6×(+1.33R)+0.4×(−1R) と一致。**TP2は現状ただの飾り**（伸ばす/分割決済を測るなら別エグジットモデルで要再検証）。
- **実装＝最小・ノーリスク（オーナー選択）**：`index_long_bonus`（指数×買いに信頼度 **+1**）は 2026-06-18 から「表示・記録のみ」で前向き検証中だった。これを **#21昇格を受けて【本採用】にステータス格上げ**（コメント＋factorラベル更新、`score += 1` は据え置き＝既に件名⭐に反映済）。**発火・メール送信可否・ロットには今回は影響させない**（配信/ロットへの昇格は追加ライブ確認のうえ別途・将来の選択肢）。可逆＝`score += 1` を消せば元通り。
- 検証＝`py_compile` OK・`mw check` エラー0。**次回 technical-alerts 実行（4hごと）から有効**（手動triggerはメール副作用があるので打たない）。
- ✅ **②配信の取りこぼし防止＝実装済（2026-06-26）**：`generate_technical_alerts.py` の email_silent ブロックに exempt 追加＝検証済み「指数×ロング」は蓄積期(email_silent)でも配信（ma_golden単独ブロック0勝N=11は維持）。commit b4271d3・次回 technical-alerts から有効・可逆。
- 🔜 残る昇格候補：**③ロット推奨に反映**（+EVを実弾サイズへ・リスクサイジングに触るので要慎重）。

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
- **🆕 投資格言シリーズ 初の自動公開を確認（2026-07-01）**：新シリーズ「投資格言から学ぼう」を構築（[[project_proverb_series]]）。#1 `guide-proverb-atama-shippo.html`（頭と尻尾はくれてやれ）は2026-06-30に手動公開済（独立Opus監査=白）。cloud routine **`proverb-daily-auto`（`trig_01P8Jjut79fHWoiALk4mfuJQ`、毎日10:12 JST）** が `drafts/PROVERB_GUIDE.md`(SOP+15キュー)を読んで自動公開。**初回=7/1 10:12 JST→#2「買いは家まで売りは命まで」が公開 or エスカレされたか**を確認（`drafts/proverb/PROVERB_LEDGER.md`／guides.html「投資格言から学ぶ」カード／`RemoteTrigger get trig_01P8Jjut79fHWoiALk4mfuJQ` の last_fired_at）。エスカレ(🚩)なら人レビュー。薄コンテンツ回避が前提（AdSense）。
- ✅ **ニュース鮮度カットオフ＝解決済（2026-06-30 ライブ確認）**：オーナー「古いニュースが表示される」→原因＝各カテゴリ「関連ニュース」と「🔍信頼性検証済みニュース」は `fundamental-context.json` ブリーフィング由来で、描画コード（`build_card_news_from_briefing`/`build_trust_news_html`）に**鮮度カットオフが無く**、新鮮な記事が少ないカテゴリ（特に暗号資産）で古いHIGH/MID記事（5/14 CLARITY法案等）が3枠埋めに生き残っていた（TOP3の48h除外とは別系統）。**修正＝`BRIEFING_NEWS_MAX_AGE_DAYS=10` カットオフ追加**（>10日除外・日付なしは残しフォールバック温存）。GitHubが`_history_items`で先行＋**CRLF**だったため**GitHub最新に差分だけPUT**（commit `a89e693854`）→ローカルも最新へ同期→update-market-news #829 success。**ライブ確認＝最古6/25・5/14と6/17は消失**。調整は定数1つ（`generate_market_news.py`）。再発時はブリーフィング生成側の日付誤りを疑う。
- **ニュースRSS修正のライブ反映確認**：6/28に死んだロイターRSSを差し替え＋update-market-news を trigger 済。**live の index.html ニュースにロイター日本（日本語）が戻っているか**を確認（WebFetch等）。
- **AdSense 再審査の結果**：6/27 申請済（[[project_adsense_review]]）。承認/却下を確認。却下ならニュース記事もnoindex等の next step。
- **JP朝カードの初稼働**：月曜6:00に `MarketWatch_JP_Daily` が初の自動実行→`DAILY_SUMMARY.md` が当日日付で更新されているか（番人 `MarketWatch_JP_Health` 8:00 も）。
- **整理係**：`mw declutter` は現在0件。月次 `MarketWatch_Declutter` が `DECLUTTER_REPORT.md` を出したら確認。

- ✅ **update-market-news.yml の失敗は解決済**（2026-06-20 午後・concurrency追加）。原因＝push+dispatch の同時実行レース。今後 `mw publish` を素で使ってもOK。
- 🚩 **FOMC結果の信頼性検証（6/18 起票・未確認）**：`indicator-result.json` の FOMC（据え置き 3.50–3.75%）は出典が個人ブログ系の疑い。一次（Reuters/Bloomberg/Fed）で数値を確認し、違えば訂正・正しければ出典差し替え。日銀（6/16・1.0%利上げ）は verified。
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
