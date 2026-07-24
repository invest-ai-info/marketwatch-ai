# 🔖 セッション引き継ぎ（最終更新: 2026-07-24 夕）

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

### 🔜 次セッションで最初に確認（在flight・2026-07-23夜更新）

- **⓪-🌅7/24朝の確認3点=✅完了（7/24夕）**: ①`JP監視サマリー.html/.txt` 7/24 06:22 初回自動生成✅（wrapper best-effort初運転成功） ②06:10=#049生成・**news次元sweep稼働確認**（news=1-2×dir=long等のセルが出現・ローカル再現一致）。ただし**期待の2本（oil×long 61.6% / rsi=os×trend=上昇 58.6%）は未登録=q0.136でFDR α0.10を惜敗**（7/23夜通過→+1日データで閾値外＝仕組みどおりの正直な挙動・エッジが本物なら数日内に自動登録される位置）。**Q23拡張group仮説も未出現=1d拡張レーン7/22開始でN<min-n20の想定内**。REVIEW.md新規🚩なし ③指数×ロングは**7/23にすでに降格済み**（demoted_at 2026-07-23・N244評価でCI下限マイナス2回連続・#048が記録）＝事前宣言ルールの自動執行。**⚠️現在の昇格=押し目反転買い×上昇トレンド(edge)＋metal×long(gate)の2本**＝「メール無音期間」は終了している（押し目edgeのR-CI下限は7/24に-0.044へ軟化=strike蓄積を監視）。DOCTRINE §1へ結晶化済み。
- **⓪-骨太方針2026スクリーニング 7/23深夜✅（オーナー依頼「投資先セクターの有力銘柄選定」）**: 7/21閣議決定=17戦略分野・官民投資370兆円枠をWebSearchで事実確認→既存 `_jp_policy_value.py` の54銘柄テーマ対応表（決定前作成・防衛/宇宙/サイバー/量子/AI半導体/核融合/蓄電池/食料/国土強靱化/レアアース/造船）を当日スクリーナーと突合＝**地雷なし20銘柄（DOWAグレアム6・住金鉱山5・サカタのタネ5防御◎・アドテスト4・NTT4等）／回避フラグ点灯30銘柄(56%)**＝テーマ株は⚡罠の巣（国策に売りなし#24の批判的読解をデータで裏付け）。個人用・非公開。**→宿題3件とも7/24✅**: (a)17分野フルカバー化=+21銘柄で計75（バイオ創薬6/コンテンツ6/クラウドDC4/港湾物流5。9613 NTTデータGは2025年NTT完全子会社化で上場廃止=4307野村総研で代替） (b)**`mw screen --policy [--refresh]`実装済み**（mw.pyヘルプ記載・_jp_policy_value.pyはローカル専用のまま） (c)IRBank財務75銘柄を--refreshで7/24再取得→**出遅れ×割安×黒字=22銘柄**（新分野からは港湾物流5本=商船三井PBR0.69等が全部入り・バイオはエーザイのみ・コンテンツ/クラウドDCは全滅=PBR>2か過熱で織り込み済みの傍証）。⚠️修正=PER/PBR欠損がNaNで採用判定をすり抜けるバグをpd.isnaで根治（東電HD・ネクセラの2本が正しく除外に）。CSV=`_jp_policy_value.csv`。当日スクリーナー旗との突合は従来どおり`mw screen`で。
- **⓪-監視サマリー 7/23夜✅（オーナー依頼「監視データを日次サマリーでOneDriveから見たい」）**: `_jp_daily_summary.py` 新設（ローカル/SYNC外・テスト`_test_jp_summary.py` 8件PASS）＝毎朝05:45の `_jp_screen_daily.py` 成功後に自動生成（wrapper末尾にbest-effort呼び出し・失敗しても本体成功扱い）。出力=**`JP監視サマリー.html`**（PC・ダークUI: 旗チップ7種+👁監視銘柄カード+旗別売買代金上位10表）+**`JP監視サマリー.txt`**（スマホOneDriveアプリ向けコンパクト版）。内容=trap/⚡/🔪/📅カウント・危険2+・TT3・防御◎・監視銘柄の旗とret5/ret20・「計測であり推奨でない」免責。**明朝05:45が初の自動運転=要確認**。
- **⓪-Q25Q26 7/23深夜✅（オーナー発案の出来高研究2本）**: **Q25=出来高バンド前向き**（非FX9ライブ・relvol3バンド=Q21同一・遡及計算型でロガー不要・初判定=前向きN≥600&両端各n≥150・登録のみ=queueに📊で待機）。**Q26=セリングクライマックス実行済み**（`_jp_q26_selling_climax.py`→`_jp_q26_summary.json`・JPレイク5年）＝**A「大商いの投げ」(5日−20%∧relvol≥5)は✅両期間有意だが方向は事前予想と逆＝劣後**（train−2.10% q0.046／holdout−4.10% q0.0005・勝ち越し64.6%なのに平均負け=左裾破滅的・クラッシュ率5〜7倍。**日本個別株のセリクラ翌日は買い場でない**=指数商品のRSI≤30反発と対照的）／**B「閑散の下げ」(∧relvol≤0.6)=❌棄却**（train ns p0.639=「閑散に売りなし(底)」の定量支持なし・クラッシュ13倍で防御面は同族）。DOCTRINE §2/§3結晶化・アンカー6件(計64)・Q26退役済み。**→✅同夜に特別記事公開済み=`guide-selling-climax.html`**（「投げ売りの翌日に買っていいのか——日本株1,285回の急落で検証」🧪AIシグナル研究日誌・数値28項目を機械突合PASS・SVG2枚はみ出し0・独立Opus監査**🟢白=修正ゼロ**・日付ゲート通過・ライブ200/guidesカード/index履歴 全確認済み。Q22急騰と合わせ「極端な出来高は両方向危険」を公開面でも一貫化）。（DOCTRINE declutterは7/24✅＝warning 0）。

- **⓪-成果戦略 7/23夜✅（オーナー発案「signal-labの成果が見えないと読者が離れる」→方針=攻めのエッジ・両輪）**:
  **A見せ方=🏆エッジ番付タブ 公開済み**（track-record.html 新タブ・`generate_track_record_page.py` の `build_banzuke_section`＝signal-lab-tracker.json を幕内(昇格2)/十両(holdout通過8)/幕下(36)/引退(5)の4段で自動描画・エッジ⚔️/ゲート🛡の型区別・「検証であり推奨でない」免責・テスト`_test_banzuke_tab.py`9件PASS・**ライブ確認済み**）。
  **B発掘=Q23/Q24事前登録＋実装**（SHA凍結済み）: Q23=拡張ユニバース正式組入れ（verify GROUPSにx-group5キー=metal_x/energy_x/rates/crypto_x/index_x・既存group不変＝汚染なし・tracker `pick_data`で拡張group仮説のみ凍結迂回・テスト9件PASS。sweepはGROUPS importで自動追随）／Q24=注目度エッジ（オラクルに`news`キー+`news_band_of`(0/1-2/3+固定)・sweepグリッドにnews×dir 9セル追加・テスト10件PASS。Q21 H-V2の攻め転用・前向きはゼロから）。CLAUDE.mdのfilterキー一覧も現行化（state系7/20+news/x-group7/23）。
  **残タスク**: (i)✅7/24=`auto_weekly_review.py`に「🏆エッジ番付の変動」節（summarize_banzuke/render_banzuke_section＝promoted_at/demoted_atを読むだけで再判定なし・tracker欠損時は節ごと省略・テスト4件PASS=7/23降格の実データ描画確認済み。**初のライブ出力=7/27月曜朝run で要確認**） (ii)✅7/24=sns-post-daily routineプロンプトへ「月曜のみ番付1行」ルール追記（RemoteTrigger update済・その回はtrack-record.html URL可・誇張断定禁止） (iii)**弁護士相談アジェンダに番付タブを追記済み→相談時に一緒に見てもらう** (iv)signal-lab-daily routineプロンプトのキー列挙が古い（7/19以前のまま。運用実績上sweep出力駆動で非ブロッキング＝env/regime仮説は流れている。次に触るとき更新） (v)Q17は10月のA1再実行までqueue_archiveで休眠（サイズ予算・判定不変）。
- **⓪-Q21Q22 7/22夜 事前登録2本を実行✅（オーナー発案仮説の答え合わせ）**: **Q21出来高/人気×成否**=H-V1薄商い失敗説❌（BT非FX9・厚−薄 train+0.025 p0.59/holdout+0.112 p0.11＝符号は説どおりだが非有意・欠損0.9%）／H-V2注目度=**予想と逆方向で有意**（人気news≥3−不人気news=0のavgR差 **−0.20** CI[−0.35,−0.05] q0.0135・週末感度同方向）＝**ニュース過熱時のシグナルは劣後**（示唆どまり・記事ネタ候補）。**Q22罠フラグ=✅両期間合格**（(F1relvol≥5∨F5回転≥8)∧F2急騰25%/5日・イベント4,602件＝fwd20同日差 train**−4.32%** p0.0003/holdout**−4.04%** p0.001・**クラッシュ率21.7% vs 対照1.8%=約12倍**・F4軽い玉層はさらに悪い）。正直な注記=F2急騰単独でも−4.75%＝コンボの付加はクラッシュ集中度。両方DOCTRINE結晶化（Q22=§2防御・Q21=§3）・queue_archiveへ退役・登録簿archived記録済み。スクリプト=`research/_q21_volume_popularity.py`／`_jp_q22_trap_flag_screen.py`（ともにローカルSYNC外）。
- **📌newsレーン30本=ダークモード全欠落**（navだけでなくページ全体にbody.dark無し。テンプレ拡充は別セッションで設計＝7/21ナビCSS節から引き継ぎ・経緯はSESSION_ARCHIVE 7/24退避分）
- **⓪-A 7/19大改修の初運転確認＝7/20朝に①②✅完了**: ①06:10 run=コンボ3本(combo_hb_rsiob/combo_bbub_rsiob/combo_db_hb)登録✅(43→46仮説・全てtracking/holdout_pass=False)・**promote_strikes未出現はCP到達仮説ゼロの仕様どおり**(コード286-293行=CP時のみ書く)・strike1保持(index_long_live N212)・#045自動公開(指数×ショートgate逆転) ②4H定時=全success・**A修正稼働の実証=n_promoted 3→2**(gateがメール通行証から除外)・**D修正稼働=avoid_matched記録出現**・support_bounce初発火2件(BTC 1h・email=False=正常)・退役2タイプ発火0・メール0通=無音期間の方向どおり ③**今週中**=指数×ロングがN=240のCPでstrike2→降格→**メール無音期間入り**（昇格edge 0本=正常状態・手動介入しない。🛡ブロック表示の実物確認は次にメールが出る時） ④✅7/22補充済=格言キュー#25〜33の9本追加（PROVERB_GUIDE.md・GitHub側#19まで公開確認済み→#24消化=7/27・次の枯渇≒**8/5**=要補充） ⑤**9/20以降**=15分足セッション追試（research/_fx_session_15m_scan.py再実行・事前登録済み） ⑥✅7/20=`/consolidate-memory`実施（MEMORY.md 9.4→4.0KB=予算内・詳細は各ファイル側に確認済みの上で索引をフック化）。
- **⓪-プラグイン 7/22**: `superpowers@claude-plugins-official` 導入済み（user scope・**スキルは7/23以降のセッションから有効**＝TDD/体系的デバッグ/検証してから完了宣言などの作業規律系14スキル）。他のプラグインは当面追加しないとオーナー合意（大半がSaaS連携で該当なし・入れるだけで毎セッションのコンテキストを消費=⚡トークン効率ルール。将来候補メモ=duckdb-skills（レイク集計が重くなったら））。
- **⓪セッション冒頭の新ルーチン＝`python mw.py evolve`**（DOCTRINE突合+キュー+トラッカー鮮度・トークン0）。⚠️**日付は作業の直前に必ずGet-Dateを取り直す**（7/15日付事故の教訓＝冒頭の値を使い回さない・auto-memory feedback_date_freshness）。
- **⓪-🔴→✅日付ゲート実装完了（7/22夜・オーナー承認「順番にお願いします」）**: `publish_article.py` に `check_date_gate` 追加（公開日≠JST今日で🚫exit 1・`--allow-backdate`免除）。TDD=`_test_publish_date_gate.py` 5件PASS＋統合確認（7/21付け記事のdry-runがブロック/免除で通過・`mw check`エラーなし）。
- **⓪-C idea-scout-weekly**：✅7/20転記完了（7/19回の3件処理）＝**Q19祝日前プレミアム事前登録**（レイク取引日暦のみで検証可・EW日次リターン差・円環ブロックbootL=5・登録簿SHA記録済み・出目未見）／自社株買い公表後=watch（TDnet公表日データ調達が先）／決算前ドリフトEAP=watch（fins開示日の四半期カバレッジ確認が先）。slugs 3件追記済み。次回の受信箱確認=7/26(日)14:00運転後。
- **⓪-D 進化ループ続き**：**✅7/20 Q17実行済み**（`_jp_q17_accounting_screen.py`→`_jp_q17_summary.json`・DOCTRINE §3/§5結晶化・アンカー4件）＝**A2アクルーアル❌確定**（train同form-3.83% q=0.0003=Sloanと有意に逆＝「質は逆」レジームの拡張）／**A1資産成長=train合格+3.44%・crash 9.7vs15.6%の防御併走**だが**holdout=6formationでブロックboot縮退（T<L=13は循環回転で平均不変=p自動有意）＝判定不能→📌2026年10月頃(formation10本)に同一コード再実行**（覗き見しない）。**✅7/20 Q19も同日実行=❌棄却**（祝日前日EW差 train−0.066%/holdout−0.137%・両期間で方向逆・p≈0.58＝カレンダー効果はLW3/LW4に続き3連敗・DOCTRINE §3済）。**✅7/20 Q20アレンジDも実行=❌不合格**（下の⓪-E参照）。**次の攻め候補=growth_levers残（②b国外OOS／④promise audit／⑤プレイブック）or Q10（エンジン実装が先・優先度低）**＝攻めキューはほぼ完走・当面は前向き観察（Q7/Q11/Q16/A1）の答え待ちが主戦場。他の候補=growth_levers残（②b国外OOS／④promise audit／⑤プレイブック）・Q10（エンジン実装が先・優先度低）。**✅7/15消化済=記事#6公開・Q18❌**。TT3=月1回・Q11=毎月1-3日タスク自動。**8/1以降の最初のセッションで7/31 formation凍結を確認**（`mw evolve`のQ11行がformation 1/12になっているはず）＋**8月にmw screen📅列の初発火を確認**（Q1決算シーズン・元データ=J-Quants earnings-calendar・キャッシュ`_jp_earnings_calendar.json`）。（DOCTRINE declutter 7/24✅）。
- **⓪-E 巨匠アレンジ枠=✅4候補完走（7/20クローズ）**：**A**=❌7/11（Q15単一資産超えず=記事#6素材）／**B**=Q13✅7/9／**C**=Q11✅7/11実装済（screener参考列だけ任意で未）／**D**=❌7/20（**Q20グレアム防御×PEG複合**=train ns→holdoutのみ有意=レジーム依存・blowupもtrainで対照並み=複合で防御一貫性が消える・複合の前科C1/C2に続き3件目・`_jp_q20_summary.json`）。
  ※「すでに生きているアレンジ」の整理も記事ネタ（赤三兵→連騰≥4危険ゲート・タートル資金管理→ATRベースSL/2%ルール・**G4逆張り→🔪回避フラグ（Q13）**＝原型のエントリーは死んでも部品は生きる）。
- **⓪-F 文書declutter**：✅7/22実施=**mw evolve warning 0**（DOCTRINE 24.0KB=§3スタブ化第2弾13行退避＋アンカー剪定22件／queue 12.3KB=Q21/Q22退役）。以後もこの水準を維持（節が増えたら完了節をARCHIVEへ・§3は15行超で古い行をスタブ化）。
- **⓪-H ⚡news-ticker**: ✅7/11朝確認=夜間毎時運転OK（updated 7/11 10:03・30件）。残1件=**「📰経済を既定で非表示（ボタンで表示）」は1行で変更可＝オーナーの好み待ち**（夜間はYahoo!経済由来の消費者ネタ多め問題）。
- **①巨匠シリーズ**：#6=7/15公開済み（Q15資産クラスDMの正直な❌）。次記事候補=「#7 割安成長（ズールー）×グレアム再訪」＝Q11前向き設計・Q12再監査が素材（両方完了済みでいつでも書ける）。
- **②TT3の前向き検証＝📊稼働中**（`_jp_turtle_tracker.py`・検定はブロックboot版に7/8改定・月1回チェック・初判定は10月頃）。
- **③防御スクリーン列＝✅適用済み**（`mw screen`の🛡防御列・7/7）。
- **⑤番人EA MW_Guardian＝✅v1.1修正完了（7/22夜）・残りはデモ実機テストのみ**：(a)監査🔴3+🟡5+#11を全修正→(b)MetaEditor CLIコンパイル **0 errors/0 warnings** 済み（`mt4/MW_Guardian.mq4`+`.ex4`生成・SETUP.md v1.1・詳細=`research/execution_audit_2026-07-11.md`対応ログ7/22行）。**✅同夜デモ実機テストまで完了**（ClaudeがMT4データフォルダ`…6C770BB1…\MQL4\Experts\mw_Guardian.mq4`へ直接配置+CLIコンパイル→オーナーがUSDJPY,H1へ再アタッチ）: ①v1.1起動ログ=ATR240分/手動玉のみON ②カレンダー取得=FOMC 7/30 03:00 JST正認識 ③仮SL自動装着 実績あり（modify ok） ④**SL削除→🚨+元位置162.881へ自動再装着=ライブ合格**。残タスク（任意）=表示リスク% vs 手計算の1回照合（2%警告が出る場面で）・番人が2チャートに重複していないか確認（USDJPY貼付時にProCon-Maxが外れた点はオーナー了知）。#14/#15/#16(discipline)/#13(文書)は未修正=次回。
- **⑥リードマグネット公開待ち＝オーナーのGoogleフォーム作成待ち**：URLが来たら `MAGNET_SETUP.md` の Claude作業（コンプラ監査→PDF SYNC→CTA設置→X導線）を一気通貫で。
- **⑦AdSense＝7/6再却下（確定）**：🔴**オーナー作業＝AdSenseコンソール[サイト]ページで却下理由の詳細を確認**→理由を見てから対応方針を相談（候補: ニュース/自動生成記事の追加noindex・コンテンツ拡充・再申請時期）。むやみにnoindexを増やすのは理由確認後。
- **⑧オーナー手動タスク2件**：(a) **X用アイコン `mw-logo-512.png`**（作業フォルダ直下・ローカルのみ）を @rx009898 のプロフィール画像に手動アップロード (b) 実機スマホでトップページ整理後の見え方＋タブのロゴを確認。
- **⑨相談したら進む事項**：(a) OGP画像のロゴ入り差し替え (b) ツール次候補＝DCA比較/NISA枠/ポジションサイズ（後2者はコンプラ設計繊細） (c) `btc_all_1d`のN30緩和＝コスト込みで脆弱の扱い (d) 🏁5本問題のauto_*注記移設 (e) リバモア検証（優先度低） (f) **triangle_squeeze（142発火・評価可能0件=warn専用ノイズ）の退役可否**＝コンボ条件次元の価値があるため7/19から保留中 (g) ⚡news-tickerの「📰経済を既定で非表示」＝1行変更でオーナー好み待ち。
- **整理係**：`mw declutter` は7/3時点0件。月次 `MarketWatch_Declutter` が `DECLUTTER_REPORT.md` を出したら確認。

- ✅ **POLICY dict 更新＝完了（2026-07-04未明）**：日銀 0.75→**1.00%**（6/16利上げ）。米3.75/欧2.40/英3.75/豪4.35は6月会合すべて据え置き＝変更なし（FRB6/17・BOE6/17・RBA6/16をWebSearch＋fundamental-contextで裏取り）。次回会合=FOMC 7/28-29・日銀 7/30-31。朝7時の update-market-news から反映。
- 🗓️ **`jp-stock-info.json` の四半期更新**（決算シーズン後に `python make_jp_stock_info.py` 再実行→`mw sync`。赤字/黒字フラグを最新決算へ。日次の値上がり率/売買代金は `jp-rankings.yml` が自動）。
- 📊 弁護士相談アジェンダ（track-record 統計開示／**🏆エッジ番付タブ（7/23新設・仮説成績の公開リーグ）**／確信度ラベル／個別銘柄記事の言及）。
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
