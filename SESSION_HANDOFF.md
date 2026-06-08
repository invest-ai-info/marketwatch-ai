# 🔖 セッション引き継ぎ（最終更新: 2026-06-08）

新セッションはこのファイル＋ CLAUDE.md ＋ `memory/03_initiatives.md`＋`ROADMAP_10M.md` を読めば文脈を復元できます。

---

## 🆕 2026-06-08 セッションの続き（最新・まずここを読む）

#### ✅ 2026-06-08：guides.html モバイルUX改善（アコーディオン実装）
- **`guides.html`（SYNC済・commit 3020a87）**
- 54記事が縦並びで重すぎ問題を解決。カテゴリごとに「最新3件＋もっと見る（N件）」で折りたたむ
- **動作**：モバイル（≤700px）=ボタン表示・4件目以降非表示 / デスクトップ=全件表示・ボタン非表示
- ボタン数4個：速報29件 / 投資の基礎知識2件 / 投資指標2件 / テクニカル分析7件
- 展開後は「折りたたむ ↑」に切り替え＋クリックでカテゴリ先頭へスクロール
- **あわせてフッター修復**：以前のセッションで末尾が切れていた（kinsho-v1免責・スクリプト欠落）→ 完全版に修復

#### ✅ 2026-06-08：心理＆リスク管理シリーズ⑤「複利とドローダウン」公開
- **`guide-compounding-drawdown.html`（新規・SYNC済・HTTP200確認・compliance🟢白）**
- SVG3点（複利成長曲線/ドローダウン回復棒グラフ/ボラティリティドラッグ）
- コミット：07e1a1b(記事) / c122b44(guides) / efe94d6(更新履歴)

#### ✅ 2026-06-08：心理＆リスク管理シリーズ④「利益確定の心理」公開
- **`guide-profit-taking.html`（新規・SYNC済・ライブHTTP200確認・約47KB・compliance🟢白）**
- **タイトル**：「利益確定の心理と技術｜チキン利食いを止め、利を伸ばす仕組み」カテゴリ：🧠 投資の心理・メンタル
- **構成**：処分効果/プロスペクト理論（前半）＋期待値への影響・トレーリングストップ・部分利確（TP1/TP2）・事前ルール化（後半）。SVG3点（処分効果対比・トレーリング・2段階出口）
- **compliance修正5件（🟡→🟢）**：①「再現性のある成績」→「成績の安定を目指す考え方」②期待値数値例に「仮の例」注記③「理論上損なし」→スプレッド注記④「実践的です」→「考え方もあります」⑤「タダでもらった利益」→「損益分岐点以上にSLを移した状態」
- **コミット**：57a2222(記事) / d861e3b(guides) / 52a7032(更新履歴)
- **シリーズ計**: 心理3本（loss-cut/calm/profit-taking）＋リスク管理2本（position-sizing/risk-reward）= 計5本公開済

#### 🔜 次のトピックキュー
| # | キー | テーマ |
|---|------|--------|
| ⑥ | cognitive-biases | 認知バイアス一覧（確証・後知恵・代表性など） |
| ⑦ | diversification | 分散投資の本質 |
| ⑧ | trading-journal | トレード日誌の活用 |
| ⑨ | leverage | レバレッジの仕組みとリスク |

---

## 🆕 2026-06-07 セッションの続き（最新・まずここを読む）

#### 🌙 2026-06-07（夜の続き）：戦略の実証 → 日本株2倍株＆政策テーマ → 日経見送り → 心理記事#2公開
> 詳細は memory `project_mt4_ea_validation` / `project_jp_doublebagger` / `project_content_psychology_strategy` に反映済。

- **① MT4/戦略バックテストの大結論**：MT4(BigBoss/ProCon-Max)のテスターが**勝ちトレードを損失として記録する不具合**を発見（モデリング品質n/a・チャートエラー約2000件）→ **MetaQuotes-Demo(login `174318935`)＋「始値のみ」で正しく検証可能に**。逆張りEA(`MeanReversionBounce_EA.mq4`)＝**実在するが薄い(PF1.0-1.3)・レンジ専用・直近減衰**。3人チーム提案の順張りトレンドフォロー(`_trendfollow_backtest.py`)も**実体はBTC大相場頼みで再現性なし**。**結論＝この18銘柄を単純ルールで回す万能の自動売買は無い。エッジは裁量の「フィルタ/規律」として使うのが正解**。
- **② 日本株ダブルバガー＆政策テーマ（非公開・個人用）**：全東証内国株3,734→ベースレート分析(2倍株=叩き売られ+インフレ業種)→241→黒字×割安×高ROE 81→＋成長48→**3人チーム精査で精鋭9に確定（T1本命5：松田産業/地主/ロードスター/DOWA/サンフロ ・T2要確認4：フィル/円谷=落ちるナイフ待ち/内田洋行/日清）**。オーナー分類(IRBank)で👑18/機関30。高市政権×骨太2026の17戦略分野→政策テーマ→**出遅れ×割安19件**（過熱半導体/防衛大型は除外）。🔗**DOWA(5714)＝2倍株T1∩政策テーマの三冠**。成果物＝**`_jp_doublebagger_watchlist.html`(3タブ・👑/🎯フィルタ)＋`日本株ダブルバガー_精鋭9_非公開.pdf`(スマホ可)**。ツール群`_jp_*.py`＋キャッシュ`_jp_cache/`等。**全ローカル・未SYNC・公開NG（特定銘柄=無登録投資助言業/景表法=黒）**。次＝個社カタリスト/循環性精査・自己資本比率regex修正。
- **③ 日経(N225_JPY)スイング判断**：高値68k→63.9kの急落で「ゾーン下限」買い検討→**🟡見送りが正解**（落ちるナイフ＋中旬イベント集中(CPI/FOMC/日銀/骨太)＋ドル円160=円安追い風だが介入リスク）。**買いトリガー＝63,540死守して反発 or 64,441奪回。MT4に63,540/64,441アラート推奨**（システムのシグナルメールはNKD=F監視＝参考程度・BigBoss CFDとは別物）。
- **④ 投資心理シリーズ第2弾を公開**：**`guide-trading-psychology-calm.html`「感情のコントロール・平常心」公開済（ライブHTTP200・compliance🟢白・SVG3点・内部リンク2本）**。フロー＝content-writer(opus)→compliance-reviewer(opus)→preview(localhost:8765・`.claude/launch.json` marketwatch-static)でSVG実機確認→`mw publish`。**シリーズ計 心理2+リスク管理1。次のautodraft topicキュー＝③risk-reward（リスクリワード）**。

#### ✅ 2026-06-07：シグナル前向き検証（タグ実装後の本物データ48件）＋勝率アップ施策を【表示/記録のみ】実装
- **きっかけ**：ユーザーが「勝率アップ＝資産を増やす戦略・戦術の提案とバックテスト」を希望（日曜・時間あり）。SIGNAL_REDESIGN/選別ティアの続き。
- **データ＝ライブ signals-log.json（raw取得・`_signals_live.json`）。総476件・決済済み374件（4H=167/1H=207）・期間5/20〜6/7（約18日・単一レジーム）**。⚠️ **TP2バグ健在**（outcomeに'tp2'=0、hit_tp2_atで別途検出＝39件）。新規ローカル解析ツール `_strategy_backtest.py`/`_strategy_refine.py`/`_xtab.py`/`_recon.py`（未SYNC・既存_*.py同様）。
- **🎯 最大の収穫＝前向き検証データが使えるようになった**：selection/sr_runway は **6/4から記録開始**→決済済み**48件**が in-sample（〜6/3でルール化）より後の**本物の前向きサンプル**。
- **前向きの結論（n一桁・方向性確認であって確定でない）**：
  - ✅ **核のエッジ「売られすぎ逆張り」は再現**：逆張り系 +0.181R(45.8%,n24) vs 飛びつき/順張り系 −0.089R(33.3%,n15)。**bb_lower_touch +0.333R(53%,n15)** が主役。**macd_golden ロングは 0勝7敗(−1.0R)** ＝飛びつき＝負け筋（機構的にも妥当）。
  - ⚠️ **選別ティアの単調順序は崩れた**：**elite だけ強く再現(+1.39R全/+0.78R 4H・勝率83/67%・n6/3)**、しかし **good は in-sample(+0.364R)に反して −0.30R**（neutralと分離できず）。avoidティアは“汚い”（macd_goldenを5/7しか拾えず勝ち型混入で−0.04Rに薄まる）＝**型(飛びつき)の方がcomposite ティアより負け筋を綺麗に切れる**。
  - sr_runway：clear +0.102R(n36) > blocked −0.056R(n12)＝方向は再現も効果小。discipline_filter は決済0件＝まだ判定不可。
  - 建値ストップ(+1R)：4H167で −0.028R→+0.044R（SL負け102中12件を救済）だが**MFE/MAEだけでは「勝ちを建値で殺す副作用」を検出できず過大評価＝上限**。
- **資産シミュ（初期100万・固定比率1%・複利・4H）**：フィルタのリターン差は小さいが**ドローダウンと連敗を劇的圧縮**（全部取る DD10.2%/連敗10 → good+elite DD2.0%/連敗2）。＝このシステムの資産増の本質は「大きく勝つ」でなく**「滑らかな曲線で生き残り安全にサイズを上げる」**（MFE分析＝右裾薄い平均回帰スキャ、と整合）。
- **実装＝ユーザー選択で【表示/記録のみ・送信ゲート不変・可逆】の3点（commit a5224ac / 2ba73d5）**：
  1. **飛びつき順張りのソフト格下げ**（`calc_confidence_score`）：primary型が macd_golden/ma_golden/high_break かつ severity=buy で **信頼度 −2 ＋ factor「飛びつき順張り(前向き負け筋)」＋ 件名に🐢タグ**。`confidence.chasing_downgrade` を記録。型ベースがティアより綺麗（avoidが2件取りこぼした分も捕捉）。
  2. **good補正 +1→0**（elite +2は維持）＝前向きで崩れた補正を外す。
  3. **建値ストップ+1R を `MY_TRADING_RULES.md` に追記**（手動の出口戦術・過大評価の注意つき・前向き記録で確認）。
  - ⚠️ **発火・メール送信可否・ロットには一切不変**（confidenceは件名⭐・本文・log のみ／送信は filter_send_email が独立制御）。UTF-8 compile✅・ユニットテスト✅（飛びつきbuyは⭐⭐→⭐に格下げ・逆張り/ショートは無傷）・mw check✅・sync済。**次回 technical-alerts 実行から自動反映**（trigger不要）。
- **次（前向き検証の継続）**：①2〜4週ためて **elite と 逆張りエッジが別レジームでも再現するか** ②discipline_filter の決済データが貯まったら green vs red 確認 ③chasing_downgrade の実勝率で「ソフト格下げ→送信ゲート/件名昇格」を判断 ④建値ストップの実挙動記録。**まだ本採用しない**（18日・単一レジーム・多重比較・n一桁の限界）。memory `project_signal_edge_research` に要点反映済。

#### ✅ 2026-06-07：「骨太の方針2026」予告解説記事を公開＋発表ウォッチを設置（速報追記が宿題）
- **きっかけ**：ユーザーが「骨太の方針は6月のいつ発表か」と質問→WebSearchで確認（**例年6月中〜下旬に閣議決定／高市政権で初・「責任ある積極財政」が柱／本日6/7時点で未決定**。検索で出る「原案・実質賃金1%」は2025年版＝石破政権・6/6なので混同注意）。ユーザー希望で**続報を記事化**する方針に。
- **方針＝予告解説を今書く＋発表で速報追記（ユーザー選択）**。中身（原案）が未公表なので「速報」は今書けない→**発表前の予習版**を先に公開し、原案公表後に冒頭へ「速報：原案の中身」を追記する二段構え。
- **公開＝`guide-honebuto-2026.html`（新規・SYNC済・ライブHTTP200・約26.4KB・compliance🟢白「そのまま公開OK」・事実4点を一次情報と照合済）**。カテゴリ＝guides.html「🔥 速報・タイムリー記事」最上段（badge-news「**政策速報**」＝新バッジ文字なので**guidesカードのみ手動挿入**→publish_articleはsync＋更新履歴のみ）。内容＝骨太とは/いつ発表(スケジュールSVGタイムライン図つき・「今ここ6/7」マーカー)/2026論点(責任ある積極財政・新投資枠・財政目標を単年度PB黒字化→**債務残高対GDP比の安定的引き下げ**へ・賃上げ・重点投資)/市場への影響を🟢🟡🔴の3つの見方で**中立整理(断定回避)**/チェックポイント。冒頭breaking-boxで「原案公表後に速報追記」を明記。SVG実機確認(preview)・mw check✅・sync→朝のscheduleで update-market-news 再生成→index更新履歴/sitemap反映確認。
- **🔭 発表ウォッチ＝ローカル スケジュールタスク `honebuto-watch-2026`（毎日19:30 JST＝cron `30 19 * * *` ローカル時刻・notifyOnCompletion=true・sonnet）**。`schedule`スキル→`mcp__scheduled-tasks__create_scheduled_task`で作成（※これは**cloud CCR routineではなくローカルタスク**＝アプリ起動中に実行・閉じてたら次回起動時にcatch up）。WebSearchで原案/閣議決定の公表を検知→出たら**このアプリに通知**＋ローカル`honebuto-watch.md`に記録（**SYNC禁忌＝push禁止**・ただしローカルタスク生成なのでSYNC_FILESに無く事故らない）。**公開記事は触らない**（速報の実追記はライブで人＋compliance-reviewer(Opus)再監査を通すため）。閣議決定を確認したらタスク停止。
- **🎯 宿題（次にやる）**：①ウォッチ初回は**サイドバー「Scheduled」→"Run now"でツール承認を保存**推奨（WebSearch/Write）。②**原案公表の通知が来たら** `guide-honebuto-2026.html` 冒頭に「🆕 速報：原案の中身」（実数値・要点・市場反応・出典）を追記→**Opus再監査**（compliance担当が「追記分は断定的予測/銘柄混入しやすいので再監査推奨」と指摘済）→sync→update-market-news trigger→ライブ確認。③閣議決定まで載せたらウォッチ停止。
- **横展開メモ**：①`compliance-reviewer`等の**カスタムsubagentはAgentツールのsubagent_typeで直接呼べない**（"not found"）→`.claude/agents/*.md`をReadしてgeneral-purpose(model opus)にinlineするのが現状の解。②publish_articleの`--category`は**バッジ文字＆挿入位置マッチ兼用**＝新バッジ文字の記事はguidesカードを手動挿入してからpublish_article（カードは"既にあり"でスキップされsync/履歴だけ走る）。

---

## 🆕 2026-06-06 セッションの続き（まずここを読む）

#### ✅ 2026-06-06：AdSense対策（データページ解説追加＋技術穴埋め＋総点検レポート）
- **不承認理由＝「有用性の低いコンテンツ」**への対策3点（ユーザーが3つとも選択）。総点検は **`ADSENSE_CHECKLIST.md`（新規・SYNC_FILES入り）** に採点＋残タスクをまとめた。
- **① データページにオリジナル解説を追加（6コア全て完了）**（“データダンプ”→“データ＋解説”化）：`generate_market_news.py` の各ビルダーの `</main>` 直前に独自セクションを注入。**vix/hot-assets/calendar（前半）＋market-health/charts/index（後半）の計6ページ完了**（market-health=「読み方」/charts=「50年チャートの活かし方」/index=「MarketWatch AIでできること」＝オリジナル本文＋関連guide内部リンク＋免責）。ライブHTTP確認済。
- **🆕 コンソール状況（ユーザー提供スクショ・2026-06-06）**：所有権✅／**「ポリシー違反：有用性の低いコンテンツ」**＋「審査をリクエスト」ボタンあり。→ **今すぐ再審査は非推奨**。6コア解説の追加を **Googleが再クロールするまで数日〜1週間待ってから**1回で出す（`site:marketwatch-jp.com`で索引確認）。再不承認の繰り返しは不利。
- **② 技術的な穴埋め（quick）**：privacy.html を強化（「利用予定→利用しています」／**Google広告設定 adssettings.google.com・aboutads.info のオプトアウトリンク追加**／更新日2026-06-06）。`build_sitemap_xml` で **noindex の `guide-auto-*` を sitemap から除外**（索引矛盾を解消・ライブで guide-auto 消滅を確認）。
- **③ 既に出来ていた点**：ads.txt（pub-2552122294306014・DIRECT）✅／about E-E-A-T✅／contact✅／kinsho-v1免責✅／オリジナル記事49本✅／drafts noindex+Disallow✅。
- **🆕 youtube-summary / political-feed も独自解説を追加（2026-06-06）**：`generate_youtube_summary.py`（YouTube要約の使い方＝ポジショントーク注意・元動画確認）と `build_political_feed_page.py`（政治発言フィードの見方＝相場を動かす仕組み・一次情報確認）の `</main>` 直前に独自セクション注入→各workflow trigger で再生成。アグリゲーション色を独自編集色で緩和。**＝公開ページ群はほぼ全て“独自解説つき”に。**
- **残タスク**：①記事を増やし続ける（autodraft稼働中）②**数日〜1週間 Google再クロール待ち→`site:`で確認→再審査リクエスト（ユーザー操作）** ③承認後に広告配置最適化。詳細は `ADSENSE_CHECKLIST.md`。


#### ✅ 2026-06-06：自動シグナルに「ルールベース規律フィルタ」を実装（記録のみ・commit e9bfa01）
- **背景**：fib停止後、ユーザーが「自動シグナルを3人(担当)の判断でフィルタしたい」。設計協議の結果、**曖昧なLLM判定はfibと同じ轍**になりかねないため、**データが示した敗因を決定論ルール化**する方式を採用（ユーザー選択）。
- **実装（`generate_technical_alerts.py`・記録のみ＝発火/メール/信頼度は不変）**：`compute_discipline_filter(primary_type, sigdir, indicators, env_score, is_index, prior_index_same_dir)` を追加。各シグナルに `log_entry["discipline_filter"]={verdict:green/yellow/red, score, reasons}` を付与。ルール＝**減点：弱いタイプ(ma_golden/high_break/macd_golden −2)・落ちるナイフ(下降中ロング＝price<ma25<ma75 −2)・上昇中ショート(−1)・環境D(−2)/C(−1)・相関集中(同run指数の同方向重ね −2)／加点：売られすぎ逆張り系(bb_lower_touch/low_break/rsi_oversold_bounce +1)・RSI極値(売られすぎ<=30ロング/買われすぎ>=70ショート +1)**。閾値 green≥1 / yellow=0 / red<0。相関集中は run 内で `_index_fired_dirs` を追跡（INDEX_TICKERS={NKD=F,ES=F,NQ=F,YM=F,^FTSE}）。
- **過去167件で in-sample 検証（強力に分離）**：**🟢green 65.5%(n=29) / 🟡yellow 34.0%(n=50) / 🔴red 33.0%(n=88)**＝**green−red 差 +32.6pt**。redを見送れば全体38.9%→45.6%、greenのみなら65.5%（初期の好調水準に相当）。⚠️ in-sample（同データでルール化）なので楽観値・前向き検証が必要。ただしルールは型別/条件別の既知効果の符号化なので筋は通る。
- **次（前向き検証→昇格）**：次回 technical-alerts から discipline_filter が記録され始める。数週間ためて **green が red より実際に勝つか**を確認 → 効けば「redはメール送信スキップ or 件名タグ」へ昇格（記録のみ→発火/メールゲート）。weekly-trade-review/SIGNAL_REDESIGN と統合可。

#### ✅ 2026-06-06：fib_pullback を完全停止＝シグナルを100%テクニカルに戻す（反実仮想分析の帰結・commit 087a019）
- **きっかけ**：ユーザーが「4Hシグナルは最初好調→“ファンダ先行”にしてから成績が下がった気がする。元ルールなら勝率は？」と問題提起。
- **反実仮想分析（signals-log.json・4H決済済み167件）**：週次勝率 **W21 69.2%(n=13)→W22 38.5%→W23 34.2%** と低下を確認。切り分けの結果：
  - **「ファンダ先行」で実際に増えた発火は `fib_pullback` のみ**（他は全て「記録のみ」＝発火不変）。その fib_pullback が **0勝8敗(0%)**。
  - 元ルール（fib除外）の直近 W23＝**38.2%**（実際34.2%）。**fibを除けば+4pt回復**するが、元シグナル自体も 69→38% と低下＝**低下の主因は相場(regime)＋W21がn=13の小サンプル**で、ファンダ撤廃で69%復活ではない。
  - bias_aligned別：整合True 17.4%・逆行 14.3%・記録なし 45.4%（時間交絡だが「ファンダ順方向だから勝てる」は不支持）。
  - タイプ別：勝ち＝low_break 64%/bb_lower_touch(売られすぎ)52%、負け＝ma_golden 8%/fib_pullback 0%/high_break 35%＝**売られすぎ逆張りが勝ち・飛びつき順張りが負け**（過去研究と一致）。
- **ユーザー判断＝fib_pullback 完全停止＋「ファンダ先行」をやめる**。理由（ユーザーの言葉）：「ファンダでは説明できない動きを何度も見てきた。人間のパニックはファンダでは分析できない」。＝サイトの実エッジ（売られすぎ＝パニックの逆張り＝テクニカル）と一致する見立て。
- **実装**：`generate_technical_alerts.py` に `FIB_PULLBACK_ENABLED = False`（detect_fib_pullback の直前）を追加し、detect_signals の発火ゲートを `if FIB_PULLBACK_ENABLED and fundamental_bias in (...)` に変更。検出・発火・メール・ログを**全停止**。True に戻せば即復活（他シグナルに無関係）。py_compile✅・sync済。**これで fundamental_bias が signal を発火させる唯一の経路が消え、シグナルは100%テクニカルに戻った**（他のファンダ項目は record-only のまま）。
- **⚠️ 横展開メモ**：①`guide-fibonacci.html` の section-8 が「当サイトのシグナルは fib_pullback を実際に使用」と書いており**事実と乖離**＝要修正（一般教育記事なので「使用していた／複数根拠の一例」等に和らげる）。②ファンダ・ブリーフィング routine は引き続き稼働し**公開サイトのニュース＋週次戦略**に使われる（トレードシグナルには不使用に）。完全停止するか公開サイト用に残すかはユーザー要確認。③「全シグナルを担当3人(technical/fundamental/risk-manager)に任せる」案はユーザーが思案中＝運用方法を要確認。


#### ✅ 2026-06-06：実トレード分析→改善案→仕組み化（発注前チェックリスト＋週次自動レビュー routine）
- **今週の実トレード（第18〜23号）を分析**：全23件で純+112,441円・勝率45%・損益比2.73（負け小・勝ち大の良い形・ただし利益は日経大勝ち2本に依存）。今週6件は−41,364円・1勝5敗。**敗因＝①下げ局面での逆張りロング(6件中5件・落ちるナイフ)②NFP(6/5)持ち越し(最大2敗の22日経・23ナス)③相関集中(日経＋ナスの同時ロング＝同じリスクオフの賭け)**。Yahoo chart API直叩きで各エントリーの直近24h値動きを実測して確定（6/4→6/5に日経−3.6%・ナス−2.9%の急落）。**守れている点＝損切りは全部≈−1Rで止まった（出口の規律は合格）・勝ちは伸ばせている**。
- **改善案を2つの仕組みに（ユーザー承認）**：
  - **① 発注前チェックリスト `MY_TRADING_RULES.md`（新規・SYNC_FILES入り・非公開）**：エントリー前に見る5つの質問（1.落ちてる最中に買わない＝RSI≤30/サポート/panic-scan候補から 2.重要指標を持ち越さない 3.相関する指数を重ねない 4.損失上限2% 5.SL先決め）＋守るべき良い点。
  - **② 週次自動レビュー routine `weekly-trade-review`（trig_01LgSjdK2is5m6oP7ta1mh7z・毎週土曜12:00 JST＝cron `0 3 * * 6`・sonnet）**：`my-trades.json`＋`MY_TRADING_RULES.md`＋`economic-events.json`を読み、純損益/勝率/期待値/R・銘柄/方向別・**5ルールの遵守スコアカード（指標持ち越し=economic-events突合／相関集中=保有期間重複／損切り規律=R判定）**・敗因トップ・来週の重点 を `my-trade-review.md` に毎週コミット。**`my-trade-review.md` は routine生成＝SYNC禁忌**（CLAUDE.md登録済）。本日テスト実行1回 trigger 済（要・生成確認）。**routine総数12本**。
- 補足：MT4サーバー時刻=GMT+3（夏時間）→**JST=表示+6時間**で記録するのが今週確定した変換規則（my-trades.json の note にも明記）。


#### 🚨→✅ 2026-06-06：technical-alerts（4H/1H）が約18h全失敗していた→修正（既存バグ・VIX急騰で顕在化）
- **症状**：GitHubから「Technical Alerts (1H/4H) All jobs have failed」通知が毎回。調査の結果、**6/5 12:23 UTC まで success → 6/5 15:33 UTC 以降は4H・1H とも全 run failure**（リトライではなく毎回1回失敗。最終的にも成功していなかった＝シグナルメールが約18h停止）。
- **根本原因**：`generate_technical_alerts.py` の `_dir = log_entry.get("direction", "")`（2026-05-29 Phase1の既存コード）。**warn のみで方向が定まらないシグナルは `direction=None`**。`.get(key, "")` は「キーが存在し値がNone」だと**Noneを返す**ため、次行 `"ロング" in _dir` が `TypeError: argument of type 'NoneType' is not iterable` でクラッシュ→main全体が exit 1。引き金は **6/5 の VIX 24h +39.7% 急騰**で NKD=F 等に方向感なし warn シグナルが多発したこと（市場条件依存の潜在バグ）。
- **⚠️ B案（信頼度スコア）変更が原因ではない**：B案コミット8e72c82（12:16 UTC）を含む12:23 UTCの run は success。B案は当該行を行番号でずらしただけ（2818→2848）。
- **修正（commit 87d4961）**：`_dir = log_entry.get("direction") or ""` で None を空文字に正規化。py_compile✅＋ローカル再現テスト（None→"neutral"でクラッシュせず）。**4H・1H とも手動trigger→success を確認**＝復旧。失敗通知メールも停止する。
- **横展開の教訓**：`direction` は warn のみ等で **None になり得る**。`"○" in x` 系は **`str(x)` か `x or ""`** で None 安全にする（同種の既存箇所 L213/1325/2297/2332 は str()/not direction ガード済みで安全。危険は2847の1箇所のみだった）。値が None を取りうるキーに `dict.get(k, default)` の default は効かない（キー存在時）ことに注意。


#### ✅ 2026-06-06：記事シリーズの「毎日自動更新」＝ストック＆ドリップ方式に着手（下書き自動routine 稼働）
- **ユーザー要望**：心理＆リスク管理シリーズを「毎日1本ずつ自動更新」したい（ルーティン化）。
- **方針（ユーザー承認）＝ストック＆ドリップ**：コンプラ（無登録投資助言業・景表法）と品質が生命線なので**「無人で自動公開」はしない**。創作は自動化、**公開前は必ず人間＋compliance-reviewer(Opus)監査**。①下書きを毎日自動生成→②人間がレビュー&仕上げ&コンプラ監査→③承認済みを毎日1本ドリップ公開。
- **✅ 実装①＝下書き自動生成 routine（本日稼働）**：
  - routine **`autodraft-article`（trig_01VpreEMybEJCmFiU5TS7Vet・毎日 05:30 JST＝cron `30 20 * * *` UTC・sonnet）**。`drafts/AUTODRAFT_GUIDE.md`（手順書＋topicキュー）と `guide-loss-cut.html`（テンプレ手本）を読み、topicキューの未着手1件をWebSearch事実確認のうえ **`drafts/draft-<key>.html` に下書き生成＋`drafts/REVIEW.md` 追記→drafts/配下のみコミット**。**本番ファイル（guides.html/generate_market_news.py/index等）には触れない・公開しない・1日1本**。下書きは `noindex,nofollow`＋robots.txt で `/drafts/` Disallow 済。
  - topicキュー（公開順）：①position-sizing ②trading-psychology-calm ③risk-reward ④profit-taking ⑤compounding-drawdown ⑥cognitive-biases ⑦diversification ⑧trading-journal ⑨leverage（リスク管理は新カテゴリ「🛡️ リスク管理・資金管理」を初回公開時に人間が新設）。
  - 本日テスト実行を1回 trigger 済（初回は①position-sizing の下書きが `drafts/` に出るはず・要確認）。通常運転の初回は 6/7 05:30 JST。
  - **routine 総数 10本**（Max枠15/日に余裕）。`drafts/AUTODRAFT_GUIDE.md` のみ SYNC_FILES 入り（人間が編集）、`drafts/draft-*.html`・`drafts/REVIEW.md` は routine がGitHub側生成＝**SYNC_FILESに入れない**（ローカルから push しない＝巻き戻し防止）。
- **🔜 実装②＝ドリップ公開（未着手・次タスク）**：承認済み記事を毎日1本だけ自動公開する仕組み。**設計上の注意＝公開処理は guides.html / generate_market_news.py（更新履歴）を編集するため、ローカル手動編集と競合(clobber)し得る**。GitHub Action 化するなら「ローカルとの同期ドリフト」を必ず設計で潰すこと（履歴をデータ駆動化 or pull-before-edit ルール）。在庫（承認済み記事）が貯まってから着手で良い（今は在庫ゼロ）。
- **運用フロー**：朝 `drafts/REVIEW.md` を見る → メインClaudeが下書きを仕上げ（SVG実機ライト/ダーク確認・微修正）→ **compliance-reviewer(Opus)監査** → 🟢で `guide-<key>.html` 確定 → `mw publish`（将来はドリップキュー投入）→ ライブ確認。

#### ✅ 2026-06-06：リスク管理シリーズ第1弾「ポジションサイジング」公開＝自動下書きパイプライン初実戦
- **自動下書き（autodraft-article のテスト実行が生成した `drafts/draft-position-sizing.html`）を人間＋Opusで仕上げて公開**＝ストック＆ドリップの「創作自動→人間承認→公開」フローが実際に回ることを実証。
- **`guide-position-sizing.html`（新規・SYNC済・ライブHTTP200・約49KB・compliance🟢白「そのまま公開可」黒ゼロ）**：「ポジションサイジングの基本｜口座を守る2%ルールと損切り幅から逆算するロット計算」。前半=2%ルール/損切り幅から逆算するロット計算/FX・先物のpips計算。後半=ATR連動サイジング/R倍数（バン・サープ）/ドローダウン回復の非線形性（30%→43%・75%→300%）/ケリー基準（f*=(bp−q)/b・分数ケリー25〜50%）。事実はWebSearch照合（routineが実施・Opus監査で数式の正確性も確認）。
- **新カテゴリ「🛡️ リスク管理・資金管理」をguides.htmlに新設**（🧠投資の心理・メンタルの直後）。**SVG概念図3点**（①2%ルール構造②ドローダウン回復の非線形カーブ③ケリー基準の成長率カーブ＝人間が追加）。**ライト/ダーク両対応をpreviewで実機確認**。新クラス `.s-bar-*`/`.s-fill-*`/`.s-stroke-*` を`<style>`に追加（routine生成）。
- **人間の仕上げ作業**＝①noindex除去 ②TODO(SVG)だったケリー図を実装（SVG3点目）③「50連敗で約36%残る」の表現を複利計算で明確化 ④誤字「負め→負け」⑤新カテゴリ手動挿入。**下書きの本文・構造・出典は概ねそのまま使えた＝sonnet下書きの品質は十分**（人間は仕上げ＋コンプラ＋SVG実機確認に集中できる）。
- 公開フロー＝従来同一（guidesカード手動挿入→publish_article→mw check✅→sync→update-market-news(success)→記事/guides/index/sitemap 全ライブ確認）。**シリーズ計：投資心理1本＋リスク管理1本**。次の自動下書きは topic②「感情のコントロール・平常心（trading-psychology-calm）」を選ぶはず（position-sizingは公開済みなのでスキップ）。

---

## 🆕 2026-06-05 セッションの続き（まずここを読む）

#### ✅ 2026-06-06：preview.html に「結果速報」セクションを実装（雇用統計が空だった不具合の修正）
- **症状**：トップの「📊 結果速報」バナー（NFP +17.2万…）から「結果と市場反応を見る →」で飛ぶと、リンク先 **preview.html に雇用統計の内容が何も無い**（ユーザー報告）。
- **原因**：indicator-result.json も index バナーも正常だが、**preview.html を生成する `generate_market_news.py` の `build_preview_html` が upcoming（発表前）イベントしか描画せず、indicator-result.json を一切参照していなかった**。さらに発表が終わった指標は翌日に upcoming 一覧から外れる→翌朝は完全に空。＝6/5に「残課題（任意）②preview.html 本体にも結果セクションを出す」としていた未実装部分が表面化（バグというより未配線）。※preview.html は auto_indicator_preview.py ではなく generate_market_news.py が生成（auto_indicator_preview.py は guide-auto-*.html の個別記事のみ）。
- **修正（commit be80173）**：`build_preview_html` に index バナーと**同一条件**（`_load_indicator_result`＝verified・発表当日〜翌日 0〜1日窓）で「📊 結果速報」セクション（ヘッドライン実数値／📌ポイント／📈市場の反応／要約／🔗出典／免責）を本文先頭（beginner-box の直後・upcoming プレビューの上）に描画。結果が無ければ空文字で従来通り。ローカルで実JSONをDLしてレンダリング検証（結果速報/NFP/市場の反応/出典すべて描画）→mw check✅→sync→update-market-news(success)→**ライブ preview.html に反映確認（15.8KB）**。＝バナーとページ本体が同期した。


#### ✅ 2026-06-05：シグB案＝選別ティアを信頼度スコアに昇格（本番メール反映・commit 8e72c82）
- **何を**：6/3に【記録のみ】で実装した `selection` ティア（avoid/neutral/good/elite）を `generate_technical_alerts.py` の **B2 信頼度スコア `calc_confidence_score` に配線**。これでメールの ⭐ ランクがデータ駆動の選別エッジを反映する。
- **補正値（ユーザーが「単調対称」を選択）**：**avoid −2 / neutral 0 / good +1 / elite +2**。根拠＝過去304件で tier別実Rが −0.248 / −0.093 / +0.364 / +0.758 と**完全単調・前後半とも安定**。avoid＝飛びつき買い/ma_goldenロング/runway阻害 を内包（6/2案の負けエッジを全て含む）。**当初案の macd_dead×0ライン加点は「best of many＝偽陽性最有力」のため不採用**。
- **実装**：`calc_confidence_score(... , position_plan=None, indicators=None)` に引数追加→内部で監査済み `compute_sr_runway`/`compute_selection_tier` を再利用しティア算出→score補正＋factors追記＋`edge_tier` を戻り値に追加。呼び出し側L2695で `position_plan`/`indicators` を渡す。後方互換（引数なし→補正なし）も確認。
- **⚠️ 安全性（影響範囲を全追跡で確定）**：`confidence` は **件名⭐・本文信頼度ブロック・signals-log記録 の3箇所のみ**で使用、**メール送信可否には不使用**（送信は `filter_send_email` が独立制御）。＝**メールの増減はゼロ・⭐ランクの再ランク付けと記録だけ**の安全な変更。`log_entry["confidence"]` に edge_tier も記録されるので**前向き検証フックは自動**。
- **検証**：UTF-8 compile✅／合成データで5ティア全て期待通り（ELITE+2/GOOD+1/NEUTRAL 0/AVOID-chasing・blocked・ma_golden −2）／`mw check`✅／sync成功。**次回 technical-alerts.yml（4h）実行から本番メールに反映**（手動trigger不要＝triggerは実メールを早める副作用のみ）。
- **次（前向き検証）**：数週間後、6/5以降に発火したシグナルで `confidence.edge_tier` 別の実勝率/実Rが単調を保つか確認 → 保てば**発火フィルタへの昇格**（avoid抑制 or elite優遇）を検討。崩れれば補正値を縮小/撤回。multiple-comparison・13日単一レジームの限界は残るため、これは依然「前向き検証段階」。

#### ✅ 2026-06-05：新シリーズ「投資の心理・メンタル」始動＝第1弾「損切り」公開（戦略転換）
- **背景＝戦略議論**：ユーザーと「投資家の成長に何が必要か」を議論し、**サイトの真の目的＝情報と感情の負荷を肩代わりし人間を“規律と平常心”に集中させる装置**と言語化。核心スキル＝**①損切りの規律（淡々と切る）＞下手な勝ち方 ②再現性 ③冷静な判断**。→ **次の主軸はテクニカル第11弾より「②考え方・③行動」の層**（投資心理＋リスク管理シリーズ）。詳細は memory `project_content_psychology_strategy`。
- **読者ターゲットの二刀流**：初心者＝集客/PV/AdSense（北極星サイト1000万）、中級〜上級＝自分の成績（北極星 個人1億）。→ **1記事を二層構造**（前半=初心者の入口／後半=実データ裏打ちの中上級深掘り）で両立。心理/リスクは全レベル共通テーマで橋になる。
- **第1弾 `guide-loss-cut.html`（新規・SYNC済・ライブHTTP200・約49KB・compliance🟢白「そのまま公開推奨」黒ゼロ）**：「損切りができない本当の理由と、淡々と切る技術」。前半=損失回避/プロスペクト理論（Kahneman&Tversky 1979・損失≈2.25倍）/処分効果（Shefrin&Statman 1985）/サンクコスト/アンカリング。後半=「下手な勝ちより上手な負け（期待値・コツコツドカン回避）」/エントリー前ルール化/逆指値での機械執行/再現性/section-9で当サイトの思想（ルール発火・SL併記・成績公開＝感情を判断から追い出す）。事実はWebSearch照合。
- **SVG概念図3点（ライト/ダーク両対応をpreviewスクショで実機確認済）**：①プロスペクト理論の価値関数（損失側が急＝非対称）②期待値の資産曲線対比（上手な負け方↗ vs コツコツドカン）③ルールで淡々と切る vs 塩漬けの対比。投資心理用クラス（.s-axis/.s-curve-g/.s-curve-l/.s-guide）を`<style>`に追加。
- **新カテゴリ**：guides.html に **「🧠 投資の心理・メンタル」**を新設（💰投資の基礎知識の直前）。新カテゴリのためguidesカードは手動挿入→publish_article（SYNC_FILES＋更新履歴）→mw check✅→sync→update-market-news(success)→記事/guides/index/sitemap 全ライブ確認。
- **🎯 次セッション：シリーズ継続（B＝章立てマップに沿って量産）**。**最有力の第2弾＝リスク管理シリーズ第1弾「ポジションサイジング／資金管理」**（損切り記事の本文で「資金管理は別記事で取り上げる予定」と予告済＝内部リンクの受け皿）。投資心理側の次点＝「感情のコントロール・平常心の作り方（FOMO/狼狽売り/リベンジトレード）」。各記事SVG概念図3点必須・二層構造・compliance🟢必須。

---

## 🆕 2026-06-02 セッションの続き（過去分）

### ⚠️ 最重要：設定ファイルの状態（事故対応済み）
- セッション中に `market-news-config.json.json`（GitHubトークン入り）が**フォルダから消失**（原因不明・OneDrive疑い）。`.json.json` パスは**書込みもアクセス拒否**（ロック/ゴースト化）。
- → **`market-news-config.json`（拡張子1つ）で復元**。sync_to_github / mw.py は両名を見るので動作OK（sync成功確認済み）。**今後の設定ファイルは `market-news-config.json`**。
- 🔐 ✅ **済（2026-06-02）**：原因不明で消えたため **GitHub PAT を失効＋新規発行**。旧トークン `cowork-marketwatch`（...0JYwwj）を delete（→401確認）し、新 `cowork-marketwatch-2`（repo＋workflow scope・期限2026-08-31）を発行→ `market-news-config.json` の `github_token` を差し替え。`GET /user` 200＋`mw status` 疎通確認済。設定ファイルは SYNC_FILES・.gitignore 双方で除外済（GitHubへ漏れない）。

### 🔬 シグナル勝てる組み合わせ調査（ultracode、2026-06-02）← 明日の続き候補
- signals-log.json（**ライブ=GitHub側に346件・決済済み278件**。ローカルは空なので raw.githubusercontent から取得）を分析。再利用ツール `analyze_signal_edges.py`（ローカル・未SYNC）＋出力 `signal_edges_stats.json`。
- **結論：13日分・単一レジームの薄いデータでは「robustな勝ちエッジ」はゼロ**。全体は勝率38.8%/−0.094R（弱い）。
- **有望（採用でなく前向き検証行き）**：`macd_dead × MACD>0(0ライン上)のショート` n=38/60.5%/+0.412R（唯一stable）。`押し目買い(価格<MA25&MA75のロング)` n=79/48.1%/+0.122R。
- **避けるべき負けエッジ（確度高い）**：`ma_goldenロング` n=25/12%/−0.72R、`飛びつき買い(価格>両MA)` n=89/30.3%/−0.292R、`macd_dead×MACD<0` 20%/−0.533R、`GC=F金` 22.6%/−0.473R。
- **⚠️ 要修正の重大バグ（方法論監査が発見）**：①**TP2スコアリング**＝outcome に 'tp2' が0件で、本当はTP2(2.0R)到達の勝ち26/108件が+1.33Rで過小計上→期待値が系統的に過小。`analyze_signal_edges.py` と `generate_technical_alerts.py` のTP2判定を直すのが先決。②多重比較62セル（stable=trueは62回中1回＝偽陽性の可能性）。③打ち切りバイアス＋13日のみ＝過去≠未来が強い。
- **明日の選択肢**：A=TP2バグ修正→再分析 / B=B2信頼度の微調整実装（macd_dead上0ライン+1・下−2／押し目+1・飛びつき−2／ma_goldenロングLOW降格）をA/B検証で仕込む / C=記録継続でデータ蓄積（1〜2か月） / D=テクニカル第4弾(RSI)記事。推奨はA→B、ただしデータ薄いのでCも妥当。SIGNAL_REDESIGN Phase2 と直結。

#### ✅ 2026-06-03 昼：A（TP2バグ修正）完了
- `analyze_signal_edges.py` の `rec_R` を **TP2対応**に修正（勝ちでhit_tp2_at有り→tp2_pct/sl_pct≈2.0R、TP1止まり→1.33R）。ベースライン両建て表示（TP2対応 / 保守=全TP1利確）も追加。
- 再分析（最新294件、TP2対応）：**ベースライン 39.8%・−0.012R（保守−0.071R）＝ほぼ均衡**。勝ち117中TP2到達26件。
- **昨日の結論はTP2修正＋1日分データ増でも崩れず**。最有力 `macd_dead×MACD>0(0ライン上ショート)` は **n=44・56.8%・+0.462R・✅安定**（昨日n38/+0.412Rから改善＝軽い前向き確認）。負けエッジ（ma_goldenロング 12%/−0.69R、飛びつき買い−0.195R、GC=F −0.47R）も不変。
- **✅ B（エンジン反映）2026-06-05 適用済（commit 8e72c82・下記専用節参照）**。当初案の macd_dead×0ライン加点は「best of many＝偽陽性の可能性が最も高い」ため**不採用**とし、代わりに監査済みの **selection ティア（avoid/neutral/good/elite）を信頼度に配線**（より頑健・負けエッジを内包）。`calc_confidence_score` に `position_plan`/`indicators` 引数追加＋呼び出し側L2695配線済。**信頼度の表示と記録のみ補正・発火/送信/ロットは不変**。
- ⚠️ 多重比較62セルの懸念は残る（macd_dead×MACD>0は依然「best of many」の可能性）→ 別レジームで各候補 n≥40 の前向き再現を確認するまで本採用しない。

#### ✅ 2026-06-03：テクニカル指標シリーズ 第4弾「RSI」公開
- **`guide-rsi.html`（新規・SYNC済・ライブHTTP200確認）**（約42KB・compliance🟢白「そのまま公開OK」）。RSIの計算式（RS＝平均上昇幅÷平均下落幅、RSI＝100−100/(1+RS)）・標準14・70/30の買われすぎ売られすぎ・50ライン（センターライン）・ダイバージェンス・**強いトレンドでの張り付き＝最大の弱点**を網羅。事実はWebSearchで照合（Wilder 1978『New Concepts...』）。
- **SVG概念図3点つき**：①全体像（価格＋0〜100オシレーター＋70/50/30ライン＋買われすぎ赤帯/売られすぎ緑帯）②買われすぎ→反落/売られすぎ→反発マーカー図 ③弱気ダイバージェンス（価格高値更新×RSI高値切り下げ）。**ライト/ダーク両対応をpreviewスクショで実機確認済**。RSI用クラス（.s-rsi/.s-ob-zone/.s-os-zone/.s-ob-line/.s-os-line/.s-ob-mark/.s-os-mark）を`<style>`に追加。
- section-8は「RSIは複合シグナルの構成要素として実際に使用」と正直に明記（CLAUDE.md実装と整合）。第1弾(MA)↔第3弾(MACD)↔第4弾(RSI)を内部リンクで相互接続、関連カードはMACD/MA/track-record。guides.html「📈チャートの読み方」最上段に掲載（badge-guide「解説」）。
- 公開フロー：guidesカードのみ手動挿入（publish_article.pyは--categoryをバッジ文字＆位置マッチ兼用のため）→`publish_article.py`でsync_to_github/更新履歴を自動追加→`mw check`✅→sync→`update-market-news.yml`起動(success)→index更新履歴・guides・記事すべてライブHTTP200確認。
- **🎯 次セッション：シリーズ第10弾以降**（**第5「ボリンジャーバンド」・第6「出来高」・第7「フィボナッチ」・第8「ストキャスティクス」・第9「ADX・DMI」公開済（6/3-6/5）**。次はダウ理論／サポレジ＆トレンドライン／エリオット波動／一目の補完 …。各記事にSVG概念図必須）。

#### ✅ 2026-06-05：第10弾「ダウ理論」公開（シリーズ計10本）
- `guide-dow-theory.html`（compliance🟢白・SVG3図・ライブHTTP200確認）。6つの基本原則／3つのトレンド／高値安値の切り上げと転換／3段階（先行・追随・利食い）。**シリーズ計10本**（MA/一目/MACD/RSI/BB/出来高/フィボ/ストキャス/ADX/ダウ理論）。**次は第11弾＝サポレジ&トレンドライン／エリオット波動 等**。
- **⚠️横展開**：複数sync直後にupdate-market-newsをtriggerすると `git pull --rebase` 競合で失敗(exit128)あり（コード健全）。対処＝sync後ワンテンポ置く／失敗時は少し待って再トリガー。Windowsの`py_compile`はcp932で誤検知→真の構文確認は`compile(open(f,encoding='utf-8').read(),f,'exec')`。

#### ✅ 2026-06-05：テクニカル指標シリーズ 第9弾「ADX・DMI」公開
- **`guide-adx.html`（新規・SYNC済・ライブHTTP200確認）**（約38.5KB・compliance🟢白「そのまま公開OK」）。+DI/-DI/ADXの3本・14期間・**ADX25以上で強トレンド/20以下でレンジ・ADXは強さで方向でない**・**+DIと-DIのクロス（方向、ADX25超で信頼度↑）**・トレンド/レンジの見極めフィルター・遅行性を網羅。事実WebSearch照合（Wilder・RSI/ATRと同じ考案者）。
- **SVG概念図3点つき**：①構成図（価格＋+DI緑/-DI赤/ADX青＋25ライン）②+DI×-DIクロス（緑GC＝買い＋ADX25超で信頼度高）③トレンド/レンジ見極め（ADXが25超で強トレンド→ピーク→レンジ復帰、25/20ライン）。**ライト/ダーク両対応をpreviewスクショ確認**。ADX用クラス（.s-pdi/.s-mdi/.s-adx/.s-th/.s-th2）を`<style>`に追加。
- **section-8で正直に明記**：当サイトのシグナルは**発火時にADX/Choppinessを記録し市況(トレンド/レンジ)判定の材料に使用**、ただし現状はStep C＝記録・regime判定中心でハードな発火フィルタには未組込（CLAUDE.md/コードの「Step C: 記録のみ」と整合）。今後「ADX高い局面のシグナルは勝率高いか」の検証に活用可。関連カードはMA/MACD/track-record。**シリーズ計9本**（MA/一目/MACD/RSI/BB/出来高/フィボ/ストキャス/ADX）。

#### ✅ 2026-06-04：テクニカル指標シリーズ 第8弾「ストキャスティクス」公開
- **`guide-stochastics.html`（新規・SYNC済・ライブHTTP200確認）**（約41.5KB・compliance🟢白「そのまま公開OK」）。%K=(終値−最安値)/(最高値−最安値)×100・%D=%Kの3期間SMA・標準14・80/20の買われすぎ売られすぎ・**%Kと%Dのクロス（過熱圏GC/DC）**・ダイバージェンス・**ファスト/スロー/フル**・**RSIとの違い（勢いの比率 vs 値幅内の終値位置）**を網羅。事実WebSearch照合（George Lane）。
- **SVG概念図3点つき**：①構成図（価格＋%K青/%D橙点線＋80/50/20＋赤緑ゾーン）②%K×%Dクロス（売られすぎ圏で緑GC＝買い/買われすぎ圏で赤DC＝売り）③弱気ダイバージェンス。**ライト/ダーク両対応をpreviewスクショで実機確認済**。RSIの`.s-ob-zone`系＋新規`.s-k`/`.s-d`を`<style>`に定義。
- **section-8で正直に明記**：当サイトの自動シグナルはRSI/MACD/MA/BB/ブレイクを使用し**ストキャスティクスは未組込（過熱感の役割はRSIが担当）**＝「指標は数より役割で絞る」という設計思想。関連カードはRSI/MACD/track-record。第4(RSI)と内部リンク強化（RSIとの違いセクション）。**シリーズ計8本**（MA/一目/MACD/RSI/BB/出来高/フィボ/ストキャス）。
- 公開フロー従来同一（guidesカード手動挿入→publish_article→mw check✅→sync→update-market-news(success)→記事/guides/index全ライブHTTP200確認）。

#### ✅ 2026-06-05：トップに「注目の経済指標」バナー新設（A）＋ 結果刷り替えは設計中（B）
- **A 実装済（ライブ確認）**：`generate_market_news.py` に `build_indicator_preview_banner(now_jst)` を追加し index.html へ注入（`weekly_strategy_banner` と同方式・自己完結インライン・条件付きで対象無しなら空）。**発表3日前〜当日まで常時表示・📰更新履歴とは別枠**、最も近い high 重要度指標を「本日/明日/…」カウントダウン＋国旗で表示し preview.html へリンク。現在「本日 🇺🇸 米雇用統計（5月分）」表示。high指標が3日以内に無ければ自動で消える。注入箇所＝index の weekly banner 直前。
- **B 結果刷り替え 実装済（2026-06-05）**：発表後にトップのバナーを「プレビュー→結果速報」へ自動で刷り替える仕組みを完成。
  - **描画側**：`generate_market_news.py` に `_load_indicator_result(now_jst)` ＋ build_indicator_preview_banner の結果分岐を追加。`indicator-result.json` があり verified かつ **event_date が当日 or 翌日(0〜1日)**なら緑の「📊 結果速報」バナー（headlineの実数値表示）、無ければ従来のプレビュー。単体テストで当日/翌日=結果・2日後=プレビュー復帰を確認。`indicator-result.json` は **SYNC禁忌（CLAUDE.md登録済）**。
  - **routine**：`indicator-result`（**trig_0183wxDTjBRPNzWBtEM1MfsM**・毎日**23:13 JST**=14:13 UTC・sonnet）。その日に発表された重要指標(NFP/CPI/PCE/GDP/ISM/FOMC/日銀/日本GDP・CPI)があればWebSearchで実数値・市場反応を確認し indicator-result.json をコミット。**数値はWebSearch実値のみ・不確実なら verified=false・断定/助言なし**。発表が無い日は何もコミットしない。
  - **タイミング**：jobs(21:30 JST)→routine(23:13 JST)で結果JSON生成→**同夜23:43 JSTにindex再生成して結果バナーを当夜表示**（翌朝7:27もフォールバック。当日＋翌日ウィンドウで確実に拾う）。**routine総数9本**（Max枠15/日に余裕）。
  - **✅ 同夜表示の理由（2026-06-05 ユーザーと確認）**：雇用統計は金21:30 JST発表＝動きの本番は“金曜の夜”（FXは土曜朝6時頃クローズ）。翌朝表示だとアクティブ層に遅い。そこで `update-market-news.yml` に **23:43 JST(14:43 UTC)＋0:13 JST(15:13 UTC)** の夜枠を追加。結果routineの直後に再生成→金曜夜のうちに結果バナーへ刷り替わる。発表が無い夜は「変更なし」でほぼ無害（夕方以降の最新値も反映されるおまけ付き）。
  - **残（任意）**：~~②preview.html 本体にも結果セクションを出す~~ ✅**完了（2026-06-06・commit be80173）**。③FOMC(翌3:00)/BOJ(12:00)は23:13起動では拾えないので別cron追加。④auto-preview内A8広告のrel sponsored統一。

#### ✅ 2026-06-05：指標プレビューの「発表“当日”に消える」日付バグを修正
- **症状**：重要指標(例 6/5雇用統計)の前日まで preview.html に「明日 ◯◯」と出るのに、**発表当日になると消えて空状態**になる（ユーザー報告）。
- **根本原因**：`generate_market_news.py` の `find_upcoming_events(now_jst, days_ahead=3)` が `range(1, days_ahead+1)`＝**翌日〜3日先のみ**で**当日(0日)を除外**。データ（1566行 `(6,5,"us","high","米雇用統計（5月分）")`）は登録済み。`auto_indicator_preview.get_upcoming_events` も `0<days_until` で同じ当日除外。
- **修正（3か所）**：①find_upcoming_events を `range(0, days_ahead+1)`＝当日含む ②build_preview_html の days_until に `delta==0→"本日"` 追加 ③auto_indicator_preview を `0<=days_until` に。py_compile✅・sync・update-market-news再生成→**preview.htmlに「本日 米雇用統計（5月分）」表示・空メッセージ消滅をライブ確認**。
- **横展開メモ**：これは以前のUTC日付バグと同系統の「境界(当日/0)取りこぼし」。日付範囲は当日を含めるか毎回確認。
- **残課題（任意）**：個別記事 `guide-auto-*`（auto_indicator_preview生成）は preview.html と別系統で**どこからもリンクされない孤立ページ**（preview.html自体はリッチなインライン内容を持つので機能的には重複）。①guide-autoをpreview.htmlから貼る or ②生成を止める、のどちらかで整理可。プレビューバナーは calendar.html のみで index.html に無い→index追加で露出増。auto-preview内のA8広告(514-515行)は`rel="nofollow"`のみ→`sponsored`統一推奨。

#### ✅ 2026-06-04：金融アフィリ（A8証券/FX口座）を教育記事末尾に掲載開始
- 承認済みA8広告を **guide-nisa.html / guide-yen-carry-trade.html の末尾**に設置（300x250・compliance🟢白・ライブHTTP200確認）。形式＝「広告・PR（スポンサーリンク）」ラベル＋`rel="sponsored nofollow noopener"`＋免責4要素、**シグナルと分離した中立記事末尾**。
- **方針確定**：「1枚の口座開設バナーを正しく置くだけなら弁護士相談は必須でない」（アフィリ広告自体は合法・助言業でない）。効くのは表記/誇大なし/配置分離/免責。**金融アフィリは教育記事限定・末尾のみ、track-record/シグナル/推奨銘柄の隣には貼らない**（詳細 memory `project_marketwatch_compliance`）。
- **残TODO**：①about/privacyにアフィリ参加開示追加 ②既存yen-carry中段広告(253-258)のrelをsponsored統一 ③compliance-patrolにアフィリ画像も対象化。確実性が要れば関東財務局の無料事前相談。

#### ✅ 2026-06-04：速報「ビットコイン暴落（2026年6月）」公開
- **`guide-btc-crash-2026-06.html`（新規・SYNC済・ライブHTTP200確認）**（約33.5KB・compliance🟢白「そのまま公開OK」・6高リスク次元すべて合格）。速報系＝**WebSearch事実確認を先に実施**（CoinDesk/Investing/Yahoo Finance/CryptoTimes 等で照合）。
- **内容**：BTCが週内高値約$75.8K→6/3-4に$66K台（一時$62K割れ）へ約2割急落／24h清算15-18億ドル。**6要因**（①スポットETF記録的流出 約$3.4B/1週・11日連続 ②レバレッジ清算連鎖 ③MicroStrategy約4年ぶり売却＝never sell神話 ④Mt.Gox配布 約10,400BTC ⑤FRB利下げ後退観測「2%目標」文言削除・Q3→2027説 ⑥米イラン緊張＋AIローテ）＋**今後の弱気/中立/強気3シナリオ（断定回避・条件付き）**。
- **SVGはシナリオ分岐の概念図**（現在→緑/灰/赤の3分岐、価格でなく概念＝コンプラ安全）。oriental-land型の「N要因＋Mシナリオ」構成。出典欄・元本割れリスク明記。「売られすぎ→即反発」を明示的に中和（compliance最重要チェック合格）。
- カテゴリ＝guides.html「🔥 速報・タイムリー記事」最上段（badge-news「暗号資産速報」）。関連カードはRSI/ボリンジャー/market-health、CTAは市場健康度。**この暴落はパニックスキャナがBTCをRSI22で🔴反発候補として検出していた事象と整合**（記事は公開情報のみで構成、私的シグナル研究は未使用）。
- 公開フロー従来同一（guidesカード手動挿入→publish_article→mw check✅→sync→update-market-news(success)→記事/guides/index全ライブHTTP200確認）。

#### ✅ 2026-06-04：テクニカル指標シリーズ 第7弾「フィボナッチ」公開
- **`guide-fibonacci.html`（新規・SYNC済・ライブHTTP200確認）**（約39KB・compliance🟢白「そのまま公開OK」）。フィボナッチ数列と黄金比(1.618/0.618)・主要比率(23.6/38.2/50/61.8/78.6%)・**50%は心理的半値で正式比率でないと正確に明記**・**ゴールデンポケット(50〜61.8%)押し目**・フィボナッチエクステンション(127.2/161.8%＝利確目安)を網羅。事実WebSearch照合。
- **SVG概念図3点つき**：①リトレースメント基本（上昇に対しフィボ水準＋金色ゴールデンポケット帯、61.8%押しで反発）②ゴールデンポケット拡大（50-61.8%帯で反発）③エクステンション（押し目→127.2→161.8%利確目標）。**ライト/ダーク両対応をpreviewスクショで実機確認済**。フィボ用クラス（.s-fib/.s-fib-key/.s-fib-gp/.s-fib-lbl/.s-note-o）を`<style>`に追加。
- **section-8は実装と整合して正直に**：当サイトのシグナルは**フィボナッチを「ファンダ整合×ゴールデンポケット押し目(fib_pullback)」として実際に発火条件に使用**（CLAUDE.md/04_technical_rules の fib_pullback_long/short・両方向・ゴールデンポケット50-61.8と一致）。単独はダマシ多→ファンダ一致前提＋複数根拠と明記。関連カードはMA/RSI/track-record。第6(出来高)↔第7(フィボ)接続、本文でMA/RSI/MACDへ内部リンク。**シリーズ計7本**（MA/一目/MACD/RSI/BB/出来高/フィボ）。
- 公開フロー＝従来同一（guidesカード手動挿入→publish_article→mw check✅→sync→update-market-news(success)→記事/guides/index全ライブHTTP200確認）。

#### ✅ 2026-06-04：テクニカル指標シリーズ 第6弾「出来高」公開
- **`guide-volume.html`（新規・SYNC済・ライブHTTP200確認）**（約41KB・compliance🟢白「そのまま公開OK」）。出来高の意味・チャートでの見方・「出来高は価格に先行する/確認する」基本原則・出来高ダイバージェンス（息切れ）・**セリングクライマックス（投げ売りの転換）**・OBV(グランビル)・**FXはティックボリュームで近似（本当の出来高が無い）**を網羅。事実はWebSearch照合。
- **SVG概念図3点つき**：①構成図（価格＋緑/赤の出来高棒＋橙の急増スパイク）②出来高ダイバージェンス（価格高値更新×出来高は山切り下げ）③セリングクライマックス（急落の底で出来高爆発→反発）。**ライト/ダーク両対応をpreviewスクショで実機確認済**。出来高用クラス（.s-vbar-up/.s-vbar-down/.s-vbar-big/.s-base/.s-note-r）を`<style>`に追加。
- **section-8は正直に明記**：当サイトは出来高を `hot-assets`（出来高急増ランキング）で活用する一方、**自動シグナルは監視対象にFXが多く出来高が取れないため発火条件に未組込**（価格・ボラ系中心）。＝今回のシグナル研究（出来高は補助・FXは取れない）と整合。関連カードはボリンジャー/RSI/hot-assets、CTAはhot-assetsへ誘導。第4(RSI)↔第5(BB)↔第6(出来高)を内部リンク接続。**シリーズ計6本**（MA/一目/MACD/RSI/BB/出来高）。
- 公開フロー＝従来同一（guidesカード手動挿入→publish_article→mw check✅→sync→update-market-news起動(success)→記事/guides/index全てライブHTTP200確認）。

#### ✅ 2026-06-03：テクニカル指標シリーズ 第5弾「ボリンジャーバンド」公開
- **`guide-bollinger-bands.html`（新規・SYNC済・ライブHTTP200確認）**（約41KB・compliance🟢白「そのまま公開OK」）。中央20SMA＋上下±2σ（標準偏差）の3本・計算・**バンド内に収まる目安（正規分布の仮定で約95%／実際は約9割前後と明確に区別）**・スクイーズ↔エクスパンション（ボラ）・**バンドウォーク（＋2σタッチ＝即売りではない）**・順張り/逆張りの使い分けを網羅。事実はWebSearch照合（John Bollinger・期間20/±2σ・%b）。
- **SVG概念図3点つき**：①構成図（価格＋±2σバンド塗り＋20SMA点線）②スクイーズ→エクスパンション（収縮帯→緑ブレイク線→拡大・上放れ）③バンドウォーク（右肩上がりバンドに価格が＋2σ張り付き）。**ライト/ダーク両対応をpreviewスクショで実機確認済**。BB用クラス（.s-bbfill/.s-bbband/.s-bbmid/.s-brk/.s-note/.s-note-g）を`<style>`に追加。
- section-8は「BB（±2σ）は複合シグナルの構成要素として実際に使用」と正直に明記（CLAUDE.md「ボリンジャー±2σ」・signals-logの bb_lower_touch/bb_upper_break と整合）。第1弾(MA)↔第3弾(MACD)↔第4弾(RSI)↔第5弾(BB)を内部リンクで相互接続、関連カードはMA/RSI/track-record。guides.html「📈チャートの読み方」最上段に掲載（badge-guide「解説」）。
- 公開フロー＝RSIと同一（guidesカードのみ手動挿入→publish_article→mw check✅→sync→update-market-news起動(success)→記事/guides/index更新履歴すべてライブHTTP200確認）。**シリーズ計5本**（MA/一目/MACD/RSI/BB）。

#### ✅ 2026-06-03 昼：サポレジ自動検出を technical-analyst に統合
- **`detect_sr_levels.py`（新規・SYNC済）**：スイングピボットのクラスタリングで主要S/Rを自動検出（★=タッチ回数=強さ、現値からの距離%、簡易トレンドライン）。ティッカー直接指定で自己完結（例 `python detect_sr_levels.py "GBPJPY=X"`）。`sys.stdout.reconfigure(utf-8)` でBashのcp932でも落ちない。
- **データ取得の回避策（重要）**：yfinanceライブラリ＝Yahooにブロックされ空／Stooq＝APIキー必須化、で両方不可。**Yahoo chart API を直接叩く**のが現状の解（`https://query1.finance.yahoo.com/v8/finance/chart/<ticker>?range=9mo&interval=1d`＋UA、PowerShellでもpython urllibでも通る）。
- **`technical-analyst.md` 更新（SYNC済）**：壊れたyfinance記述を上記に差し替え、「主要レベル」で `detect_sr_levels.py` を必ず使うよう指示。「レベルがある≠勝てる（high_break=-0.12R）」の戒めも追記。
- **end-to-end実証済**：GBPJPYでエージェントがツール実行→S/R（212.29★25タッチが強固）を一次情報に完全レポート生成。水平S/Rは実用レベル、トレンドラインは近似（向きの参考）。
- 残候補：B（S/R接近時の勝率をsignals-logで検証）／C（トレンドライン精度=チャネル検出）。S/Rを**実トレード採用**するなら別途バックテスト要。

#### ✅ 2026-06-03：残候補B＝「S/R主軸＋テクニカル」の勝率をsignals-logで検証（重要・要点）
- ツール `backtest_sr_edges.py`（日足S/R版）＋ `_sr_recent.py`（recent版）＋ `_sr_robust.py`（頑健性）。データ＝ライブ `_signals_live.json`（決済済み304件）。出力 `sr_edge_stats.json`/`sr_recent_stats.json`。**いずれもローカル・未SYNC**（analyze_signal_edges.pyと同方針）。
- **日足S/R版（look-ahead有り）は要注意**：表面は「S/R整合≤1ATR=56%/+0.547R」だが頑健性チェックで**方向交絡が露呈**＝整合の手柄はショート側だけ（n=13/84.6%、primary=macd_dead大半＝既知の「macd_dead×レジ反落ショート」と同一の疑い）、**サポ買いは−0.417Rで負け**。距離の単調性も無し。＝**S/Rの手柄と断定できない**。
- **C案＝recent_high/recent_low（発火時点・自分の時間足）でlook-ahead完全排除し再検証 → 結果が一変して良化**：
  - **S/R整合（サポ買い/レジ売り）≤1ATR：n=62・56.5%・+0.403R・✅安定**。うち**整合×ロング n=57・59.6%・+0.485R・✅安定**（前半後半とも黒字、ロングは227件と十分サンプル）。日足版の「サポ買い負け」は look-ahead 由来の誤りで、正しくは**サポ近接ロングに実エッジ**。
  - **runwayフィルタ（entry→TP1間にS/Rが挟まるか・方向非依存）：阻害 n=83・27.7%・−0.337R vs クリア n=221・44.3%・+0.110R**。long/short両方で一貫、**深さ感度も単調**（S/Rが進路の0–34%地点で塞ぐ＝−0.41R、TP直前67–100%＝−0.00R）。機構的に筋が通る。
  - generic テクニカル上乗せは相変わらず無効（クリア+上位足トレンド一致は逆に−0.196R）。
- **A＝runwayタグを本番エンジンに【記録のみ】実装・SYNC済（commit 81e1f9e）**：`generate_technical_alerts.py` に `compute_sr_runway(position_plan, indicators)` を追加し、`build_signal_log_entry` のレコードに `"sr_runway"`（blocked / block_frac / aligned / d_sup_atr / d_res_atr）を記録。**発火・メール・信頼度は完全に不変**（build_signal_log_entryはレコード整形専用＝前段に影響なし）。py_compile✅、実304件で blocked=83/aligned=62 と再現一致を検証済。**次回 technical-alerts 実行から新規シグナルに記録され始める**。
- **次の選択肢**：①数週間 sr_runway を蓄積 → blocked vs clear の**前向き実勝率**を確認（別レジームでの再現＝本採用の前提）。②再現すれば runway阻害を発火フィルタ/信頼度減点へ昇格（B案と統合）。③サポ近接ロング（+0.485R安定）も同様に前向きタグ化を検討。**まだ本採用しない**（13日・単一レジーム・多重比較の限界）。

#### ✅ 2026-06-03：シグナル成績の底上げ＝MFE/MAE分析＋選別tagの記録実装（重要）
- **問い**：「勝率は低くてOK、大きく取って資産を増やす案は？」→ MFE/MAE分析（`_mfe_analysis.py`、max_favorable/adverse_excursion を R換算）。
- **判明（やや意外）**：このシグナルは**大相場を取るタイプではない**。MFE中央値0.90R・90%点でも2.37R、**3R以上に伸びたのは4.3%だけ・4R以上0.7%・5R以上ゼロ**。右裾が薄く、「利を伸ばす」改造をしても期待値はほぼ不変（理論上限+0.008R）。正体は**短期の逆張り/平均回帰**で、**レンジregimeで+0.518R・トレンドで+0.17R**（レンジで効きトレンドで削られる）。SL負け183件の大半は一度も伸びず直行（+1R以上含み益だったのは14.8%）。勝ちのMAE中央値0.40R（SL=1.0R）でSLには詰める余地。
- **結論＝「大きく取る」より「選別＋建値で底上げ」**。`_selection_backtest.py`（look-ahead無しrunway直輸入）で厳密検証：
  - **veto（飛びつき買い/ma_goldenロング/runway阻害 を除外）**：−0.012R→**+0.224R**・勝率40→49%・**取引は半分(152件)維持**（⚠不安定）。
  - **keep tier**：`整合∪レンジ`(35%残/+0.425R/✅安定)、**`クリア∩レンジ`=精鋭(13%/勝率70%/+0.833R/✅安定)**。keep系は全て前後半黒字＝信頼度高い。
  - **建値ストップ(+1R)**：全フィルタに+0.05〜0.08R上乗せの普遍レバー（あげ戻し約15%を救済、上限）。
- **A＝選別tag `selection` を本番に【記録のみ】実装・SYNC済（commit 36171c3）**：`compute_selection_tier()` 追加、レコードに `selection`（tier=avoid/neutral/good/elite ＋ veto_chasing/veto_ma_golden_long/veto_runway_blocked/aligned/regime）。`sr_runway` と同じく **発火・メール・信頼度は不変**。py_compile✅、実304件で **tier別実Rが avoid −0.248R < neutral −0.093R < good +0.364R < elite +0.758R と完全単調**を確認。次回 technical-alerts から記録開始。
- **次（前向き検証後に判断）**：tierの順序がライブで再現したら、avoid抑制／good・elite優遇を信頼度スコア or 発火に昇格、建値ストップ実装。**B案＝「大きく取る」本命は別系統**（週足トレンドフォロー/スイング、広SL・トレールrunner、weekly-zone/weekly-strategyインフラに乗せる）として中期テーマ。**まだ本採用しない**（13日・単一レジーム・多重比較）。

#### ✅ 2026-06-03：エッジの正体＝「行き過ぎ（売られすぎ）の逆張り」を4データで確定＋パニック反発スキャナ
- ユーザーの気づき（人気/出来高に資金集中、行き過ぎを取る）を順に検証。**結論：このシステムの実エッジは一貫して平均回帰＝“安いパニックを拾う/熱狂を売る”**。
  - signals-log: 行き過ぎfade +0.31R（深い±2σ/RSI極値は+0.32R✅安定）、chase（順張り）は−0.03R。サポ買い+0.485R・レンジ+0.52R も同族。
  - **非FX9資産 日足2年 OHLCV（出来高検証）**：下落+出来高急増(パニック)→前向き5日+0.24σ/62%。**出来高を伴わない上昇は10日で失速**（出来高は“続伸の確認”）。
  - **交差検証（本丸特定）**：**RSI≤30 単独で +0.92σ/78%、RSI≤25 で +1.66σ/81%**。出来高急増は上乗せ（RSI≤30+パニックで+1.02σ）、バンド割れ%bはRSIと冗長。＝**主役はRSI売られすぎ、出来高は補助**。
  - マネーフロー snapshot：資金は今 日本株>米テック>…>コモディティ/クリプト。
- **ツール（すべてローカル・未SYNC、Yahoo直叩き）**：`panic_bounce_scan.py`（日次「投げ売り＝反発候補」スキャン）／`_panic_cross.py`（交差検証）／`_volume_divergence_backtest.py`／`_money_flow_snapshot.py`／`_overshoot_analysis.py`／`_mfe_analysis.py`。
- **現況スキャン例**：BTC（RSI23+出来高+2.1σ+下落）が唯一の🔴反発候補、米株/日経はRSI70台＝過熱側。
- **マーチンゲール検討は却下**：時系列で最大13連敗（good+eliteでも6連敗）、倍張りは38件目で破産。健全策＝固定比率/逆マーチン×+EV選別。
- **✅ デプロイ済（2026-06-03）＝D完了**：`panic-scan.yml`（GitHub Actions・毎日**7:27 JST**＋バックアップ7:47・workflow_dispatch併設・`weekly-levels.yml`型でYahoo直叩き、CCR403回避）。`panic_bounce_scan.py` が非FX9資産をスキャンし **`panic-scan.md`** を生成・コミット。手動triggerで completed success＋GitHubコミット＋HTTP200を実証。SYNC_FILESに py と yml を追加、`panic-scan.md` はSYNC禁忌（CLAUDE.md登録済・Actionが生成）。**panic-scan.md は前向き検証データ蓄積用の非公開メモ**。
- **🆕 候補日のみメール通知を追加（2026-06-04・実機送信確認済）**：`panic_bounce_scan.py` に `_maybe_email()` を追加。**RSI≤30の候補がある日かつGmail creds存在時（=Actions上）のみ** info0414@gmail.com へ送信（ローカル実行・候補なしの日は送らない）。`panic-scan.yml` に job-level env で GMAIL_USER/GMAIL_APP_PASSWORD/ALERT_RECIPIENT＋`pip install markdown` 追加。`email_weekly_zone.py` と同じSMTP_SSL方式、md→HTML。手動triggerで **「✅ パニック反発候補メールを *** に送信」をActionsログで確認**（BTC候補・宛先はsecretマスク）。⚠以前は「panic-scan.md コミットのみ＝メール無し」だった（ユーザーが当初その方式を選択していたため）。
- **🆕 拾いゾーン出力を追加（2026-06-03）**：候補ごとに「どこまで落ちうるか」をゾーンで提示。根拠＝`_overshoot_depth.py` 実測（RSI≤30後の追加下落 中央0.9ATR/75%1.7ATR/90%3.7ATR、反発中央1.2ATR）。出力＝拾いゾーン浅(−0.9ATR)/深(−1.7ATR)・最大想定(−3.7ATR)・`detect_sr_levels`式の近いサポート(★)・SL目安(最大想定/強サポ割れの下)・反発TP(+1.2ATR)。weekly-zone-planのラダー発想をパニック反発に適用。検出/参考のみ（分割・損切り前提、売買推奨でない）。
- **実トレード採用は前向き再現＋スリッページ確認後**（歴史内2年・上昇ドリフト期・深条件n小・bandwalk罠）。次の任意ステップ：数週間 panic-scan.md を蓄積→候補の実反発率を追跡／効けば hot-assets に「売られすぎ反発候補」枠 or 候補日のみメール通知。
- **⚠️ 時間足の整合（2026-06-03 ユーザー指摘で追加検証）**：出来高/パニック検証を当初**日足**で実施したが、システムは4h/1h。`_panic_4h.py`（1h取得→UTC4h合成、n=25,682）で4h再検証した結果：**エッジの向きは不変（RSI売られすぎが主役・深いほど強い・%b/出来高は弱い）だが効果量は日足の約1/4〜1/5**（RSI≤30: 日足+0.92σ/78% → 4h+0.20σ/61%、RSI≤25: +1.66σ→+0.31σ）。**4hでは出来高の上乗せが消える**（RSI≤30単独 ＞ パニック+RSI≤30）。＝**この行き過ぎ反発エッジは本質的に日足スイングで強い**。よって日次スキャナ(panic-scan.yml)は「4hメールとは別の日足スイング層」として妥当だが、**両者は別土俵**と意識すること。4hメール勝率改善には行き過ぎ反発(+0.20σ)より**選別tier(avoid除外で+0.224R)の方が効く**。教訓＝**検証は必ずシステムの実時間足に揃えてから（日足デフォルトに流れない）**。

### 📈 テクニカル指標 解説シリーズ 始動 ← 次セッションの主タスク（P1＝記事量産）
- guides.html に新カテゴリ **「📈 チャートの読み方（テクニカル分析）」** を追加。
- **第1弾「移動平均線」公開済**（`guide-moving-average.html`・45KB・compliance🟢白）。**3人チーム（content-writer＋seo-ux-strategist＋compliance-reviewer）＋ `mw publish` で量産する流れを実証済み**。
- **第2弾「一目均衡表」公開済（2026-06-02）**（`guide-ichimoku.html`・50.4KB・compliance🟢白「そのまま公開OK」・事実10項目照合済）。雲／三役好転・逆転／5本の線／時間論・波動論・値幅観測論を網羅。guides.htmlの「📈チャートの読み方（テクニカル分析）」セクションに第1弾と並べて掲載（badge-guide「解説」）。section-8は「一目均衡表は発火トリガーに未使用」と正直に明記。第1弾↔第2弾を内部リンクで相互接続済。
- **🖼️ シリーズ標準＝インラインSVG概念図（2026-06-02 確立）**：チャート系記事は文字だけだと伝わらないので、**手描きSVGの概念図**を入れる方針に決定。**第1弾・第2弾とも各3図実装済**：一目均衡表（①全体像 ②雲位置3パネル ③三役好転）／移動平均線（①SMA vs EMA ②パーフェクトオーダー ③GC・DC、2026-06-02後付け）。`<style>`に `.chart-figure/.svg-panels/.s-*` クラス（**ライト/ダーク両対応**・実価格不使用＝コンプラ安全）を定義。**実在価格でなく概念図とキャプション明記**。次弾以降も同手法で図解する（MACD=2線+ヒストグラム、RSI=0-100オシレーター等）。概念・マクロ記事にも後付け開始：**VIX**（水準ゲージ5色帯＋逆相関図）・**NISA**（年間枠内訳バー＋生涯枠1800万/成長枠1200万上限の箱型図）に図追加済（2026-06-02）。残り候補＝バフェット指数（ゲージ）／恐怖と強欲（メーター）／FOMC／iDeCo／投資の税金。ローカル確認は `.claude/launch.json` の `marketwatch-static`（python http.server 8765）→ preview スクショ。
- **第3弾「MACD」公開済（2026-06-02）**（`guide-macd.html`・42.1KB・compliance🟢白「そのまま公開OK」・事実7項目照合済）。MACD線/シグナル線/ヒストグラムの3要素・計算式・GC/DC・0ライン・ダイバージェンスを網羅。**SVG概念図3点つき（①構成図＝price+MACD/signal/histogram/0ライン ②GC・DC拡大 ③弱気ダイバージェンス）**。section-8は「MACDは当サイトのシグナルで実際に複合条件の一つとして使用」と正直に明記（CLAUDE.md実装と整合）。第1弾(MA)↔第3弾(MACD)↔第2弾(一目)を内部リンクで相互接続。
- **🎯 次セッション：シリーズを継続して量産**（**第4弾「RSI」は2026-06-03公開済**。次は第5弾以降：ボリンジャーバンド／フィボナッチ（実装済み fib_pullback と連携）／エリオット波動／出来高 …。**各記事にSVG概念図を必ず添える**。RSI=0-100オシレーター+30/70ライン図、ボリンジャー=±2σバンド図 が作りやすい）。狙い＝**エバーグリーン×高検索需要×低コンプラ＝SEO・AdSense両方に効く**。**内部リンクで束ねてトピック権威性**を作る。「薄い量産はNG・質が命」。
- 量産手順：WebSearchで事実確認 → content-writer（本文HTML）＋seo-ux（title/meta/JSON-LD）を並列起動（`.claude/agents/*.md` を Read→general-purpose に inline、model sonnet）→ compliance-reviewer（opus）監査 → `python mw.py publish --file … --category テクニカル分析 --emoji … --card-title … --desc …` または content-writer が②④⑤実行→sync→workflow。

### 💰 AdSense 審査突破（基盤収益・進行中）
- **不承認理由＝「有用性の低いコンテンツ」**（自動データページ中心で独自価値が薄いと判断）。ads.txt は「不明」だった。
- **実施済（6/1〜6/2）**：①`ads.txt` 設置（pub-2552122294306014・ライブ）②about.html **E-E-A-T強化** ③薄い自動ページ noindex ④トップに「📚 注目の解説記事」前面化 ⑤質の高い独自記事の量産開始（MA記事）。
- **次（ユーザー操作）**：コンソールで**お支払い情報追加＋サイトをリンク → 数日後に再審査リクエスト**。質の高いシリーズ記事が増えるほど有利。

### 🗺️ 年商1000万ロードマップ（`ROADMAP_10M.md`＝戦略の単一ソース・月初見直し）
- ゴール月商83万＝3本柱（AdSense×アフィリ×note）。**最大レバー＝証券/FX口座アフィリ（弁護士相談クリアが前提）**。
- **現状＝プレ収益・低トラフィック**（A8: 月1,200インプレ・成約0／AdSense未承認＝実質¥0）。当面の二大レバー＝**P1（記事量産でPV成長）＋P0（弁護士で金融アフィリ解禁）**。

### 🎣 シグナル新機能：ファンダ整合フィボ押し目（メールON・6/2実装）
- `fib_pullback_long/short`：fundamental-context が BULLISH/BEARISH（確信度HIGH/MID）× **ゴールデンポケット50-61.8%押し**で発火。両方向・モメンタムフィルタbypass・対象8資産。詳細 `memory/04_technical_rules.md`。発火件数と実勝率を signals-log で監視。

### 🔧 その他（6/2）
- ナビ崩れ修正：`generate_monthly_report.py`/`auto_weekly_review.py`/`auto_indicator_preview.py` を9ボタンに統一＋リンターにナビ整合チェック追加。
- **routine 計8本**（fundamental-briefing / weekly-zone-plan / article-idea-scout / daily-market-preview / political-digest / compliance-patrol / weekly-strategy-brief / site-qa-lint）。

### ⏰ 時間依存
- **6/7(日)**：weekly-strategy-brief 初回サイクル（17:00 levels→18:30 routine 3人＋検証→20:13 描画）で、6/8週の「今週の投資戦略」記事に **verified シナリオ**が載るかライブ確認（`mw status weekly-strategy.yml`）。

---

## 🎯 直近セッション（5/29〜6/1）でやったこと

「シグナル成績が悪い」を起点に、**個人トレード支援の自動化**と**サイトの情報品質向上**を一気に構築。詳細は `SIGNAL_REDESIGN.md` と `memory/03_initiatives.md`。

### A. 自動で回り続けている仕組み（予約エージェント routine ＋ GitHub Actions）

| 仕組み | 種別 / ID | スケジュール(JST) | 役割・出力 |
|---|---|---|---|
| **fundamental-briefing** | routine `trig_01M7uY1H8uR6tEwF1CJ7jXzV` | 毎日 06:00 / 15:00 | 信頼性検証ニュース＋regime/bias → `fundamental-context.json`。日本語・`published`日付・`comment`(💡一言)付き |
| **weekly-levels** | Actions `weekly-levels.yml` | 日曜 17:00 | `compute_levels.py`で18銘柄の正確な水準 → `weekly-levels.json`（※CCRはyfinance403不可なのでActions側で計算） |
| **weekly-zone-plan** | routine `trig_01LP5pbD28BK55bE3GZWaHJf` | 日曜 20:00 | 18銘柄の上下ゾーン＋ラダー指値＋SL/TP/R:R → `weekly-zone-plan.md`（weekly-levels.jsonを読む） |
| **weekly-zone-email** | Actions `weekly-zone-email.yml` | 日曜 21:30 | `email_weekly_zone.py`で weekly-zone-plan.md をHTMLメール送信（→ info0414@gmail.com） |
| **article-idea-scout** 🆕 | routine `trig_01FmFNFSTkdx35nu1kWwKoYW` | 毎日 07:30 | 記事ネタ候補（SEOタイトル案＋根拠ソース）→ `article-ideas.md`（非公開・編集用メモ） |
| **daily-market-preview** 🆕 | routine `trig_01GFQ6tLGPhvEZ5crJgPRqCh` | 毎日 21:00 | 翌日の重要指標＋市場コンセンサス（economic-events.json突合）→ `daily-preview.md`（非公開・個人用） |
| **political-digest** 🆕 | routine `trig_01B1WV4bru6iFxr7SFB94huh` | 毎日 22:00 | political-feed.json を要約（重要発言トップ3-5＋市場影響）→ `political-digest.md`（非公開） |
| **compliance-patrol** 🆕 | routine `trig_016Pkyto4UfxhHP1sU2i5NP9` | 日曜 09:00 | 公開 guide-*.html を法務巡回（黒/グレー/白）→ `compliance-scan.md`（非公開・監査メモ） |
| **weekly-strategy-brief** 🆕 | routine `trig_01StownkcHrYyRbMMpVxVy2Z` | 日曜 18:30 | **3人エージェント(fund/tech/risk)で起案＋検証エージェントが全数値をweekly-levels.jsonと照合＋compliance** → `weekly-strategy-context.json`（`verified`付き） |
| **weekly-strategy（描画）** | Actions `weekly-strategy.yml` | 日曜 20:13(+30) | 上記contextで週次戦略記事を強制再描画（旧18:13の冗長版を転用）。verified=trueのシナリオのみ反映 |
| **site-qa-lint** 🆕 | routine `trig_01Ph7pZ1WpjL8mZn7gXj5TEm` | 土曜 10:00 | `check_site_consistency.py`（リンター）を自動実行→不変条件の崩れを検査→`site-qa-report.md`（非公開） |

> 🆕 **新設 routine 計6本（5/31:4本＋6/1:weekly-strategy-brief・site-qa-lint）→ routine総数8本**（Max枠15/日に余裕）。出力JSON/mdは全て **SYNC禁忌**（routineがmain生成、ローカルpush禁止）。routine は Gmail鍵/yfinance不可（メール送信・価格計算はActions側）。

- routine の確認/編集: claude.ai `/code/routines/<ID>`、または schedule スキル＋RemoteTrigger ツール（プロンプト変更は update）。
- routine は **クラウド(CCR)実行**。リポジトリへ commit は可能だが **yfinance は403で不可**・Gmail鍵も持てない（→データ計算とメール送信はActions側に分離している）。

### A2. 週次戦略の品質アップグレード＋日付バグ修正（2026-06-01）
- **問題**：週次戦略記事のシナリオ数字（日経60-61k等）が `auto_weekly_strategy.py` に**ハードコードされ陳腐化**（実勢66k/ドル円159/BTC73k と乖離）。精度＆コンプラ問題。
- **対応①応急**：誤数字のシナリオ表を撤去し「リニューアル中」プレースホルダへ（force再生成でライブ反映済み、誤情報除去）。リスク欄の「158円」も中立化。
- **対応②本命＝多エージェント＋数値検証パイプライン**（あなたの要望「3人で真剣に・数字は絶対正確・書いた後に照合する確認役」を実装）：
  - **producer**＝routine `weekly-strategy-brief`（日曜18:30）：fund/tech/risk の3エージェントで起案 → **検証エージェントが全数値を `weekly-levels.json` と1つずつ照合＋compliance** → `weekly-strategy-context.json`（`verified:true/false`）。テスト実走で **verified=true・全35数値一致**を確認済（実勢価格に完全一致）。
  - **consumer**＝`auto_weekly_strategy.py`：`verified=true` かつ **鮮度60h以内**のときだけ context からシナリオ描画。無ければプレースホルダ（誤情報を出さない安全設計）。
  - **render**＝`weekly-strategy.yml`（日曜20:13、force）：routine の後に記事を強制再描画して検証済みシナリオを反映。
- **稼働**：**次の日曜(6/7)サイクルから「今週の投資戦略」が3人＋検証版で自動更新**。現6/1週記事は構築前生成のためプレースホルダのまま（月曜のforce再生成は6/8週を作る＝日付ズレになるので見送り）。
- **日付バグの真因（重要・横展開可）**：GitHub Actions は**UTC実行**。素の `datetime.now()`/`date.today()` は9hズレ（JST午前0-9時は前日）。`generate_stock_chart.py` の3箇所をJST明示に修正済。Gitコミット時刻がUTC=前日表示になるのも同根。Geminiの推測日付対策として `auto_weekly_strategy.py` のプロンプトに基準日明示＋推測日付禁止を追加済。
- **記事の発見性自動化（同セッション）**：index.html に「今週の投資戦略」自動バナー＋📰更新履歴へ自動登録（`build_weekly_strategy_banner()`/`build_weekly_history_entry()`、最新guide-weeklyを自動検出）。**週次記事は更新履歴に手動追記しない**（二重表示防止）。

### A3. 保守の自動化ツール群（2026-06-01）— 「ルールが増えても破綻しない」基盤
**設計思想：人間が手で守るルールを、コードが自動で守る形へ。新ルールは"チェックを1個足す"で拡張。**

| ツール | 役割 |
|---|---|
| **`mw.py`**（司令塔CLI） | `python mw.py check / publish / sync / trigger <wf> / status [wf] / routines`。運用の単一入口 |
| **`check_site_consistency.py`**（リンター） | 不変条件を自動検査：🚨SYNC禁忌の混入（巻き戻し事故防止）／kinsho-v1免責／**ナビ9ボタン整合（生成スクリプト.pyを検査）**／SYNC_FILES登録／リンク切れ。errorで exit 1。ローカル=フル、リモート=SYNC_FILES系スキップ（環境判別） |
| **`publish_article.py`** | 記事公開の②④⑤を1コマンド・冪等（`mw publish` が内部利用）。③sitemapは自動化で不要に |
| **routine `site-qa-lint`** | 土曜10:00にリンター自動実行→`site-qa-report.md`（人が気づく前にドリフト検知。テストで実際に複数の問題を自動発見した） |

- **記事公開は `python mw.py publish --file ... --category ... --emoji ... --card-title ... --desc ...`** で ②→整合性チェック→sync→workflow起動まで一気通貫（`--dry-run`で確認）。**sync前に `python mw.py check` を習慣化**。
- **更新履歴の改修**：`generate_market_news.py` の `_history_items` リスト（`{date,line}`）を**日付降順ソート→最新5件**に自動整列。新記事はリストに1件足すだけ（週次は `build_weekly_history_item` が自動追加）。
- **sitemap.xml 全自動化**：`build_sitemap_xml` が**全 guide-*.html を自動収集**して再生成（手動追加不要）。二重管理解消のため **sitemap.xml は SYNC禁忌へ移動**。
- **ナビ崩れ修正**：`generate_monthly_report.py`/`auto_weekly_review.py`/`auto_indicator_preview.py` の旧5-6ボタンナビを9ボタンに統一（リンターのナビチェックが今後のドリフトを検知）。

### B. シグナルエンジン再設計（`SIGNAL_REDESIGN.md`）
- トップダウン4階建て（Layer0リスク環境→Layer1方向バイアス→Layer2テクニカル→Layer3ブレーキ）。
- **Phase 1 デプロイ済（記録のみ）**：`generate_technical_alerts.py` が各シグナルに `risk_regime`/`directional_bias`/`fundamental_context.bias_aligned` を記録。発火・メール挙動は不変。
- track-record.html の既定タブを **4H（本番成績≈54%）** に変更済。
- **Phase2/3 未着手**：データ蓄積後に「bias逆行を弾けば勝率改善するか」を signals-log で検証 → OKなら発火フィルタ本稼働。

### C. サイト（marketwatch-jp.com）の改善
- トップ「本日のマーケット」4カードの📰関連ニュースを **検証済みブリーフィング**（✔信頼度/🗓日付/💡コメント）に差し替え。重複していた専用「信頼性検証済みニュース」セクションは**削除**。古い順問題は published 日付の新しい順ソートで解消。
- **市場解説3記事を公開**（compliance🟢・8ステップ済）：
  - `guide-japan-strategy-2026-05.html`（攻め/守りセクター戦略）
  - `guide-bank-stocks-2026-05.html`（日銀利上げと銀行株・メガvs地銀）
  - `guide-oriental-land-2026-06.html`（**2026-06-01**：オリエンタルランド4661 暴落の5要因＋復活3シナリオ。出典付き・compliance🟢白）

### D. その他
- `SwingTrend_EA.mq4`（日足トレンド押し目＋3ATR追従）：バックテストで実データのエッジは薄く**実弾見送り**。手動の出口管理ツールとして保管。
- ユーザーの実トレードを `my-trades.json` に第7〜17号まで記録済（今週分ネット +4,165 円）。

---

## ⚠️ 絶対遵守（事故防止）

- **SYNC禁忌**（ローカルから絶対 push しない＝routine/cron/generate がGitHub側で生成）：
  6コアHTML / `signals-log.json` / `technical-alerts-history*.json` / `track-record.html` / political系 / youtube系
  / `fundamental-context.json` / `weekly-levels.json` / `weekly-zone-plan.md`
  **＋6/1追加：`sitemap.xml`（build_sitemap_xmlが全guide自動収集で再生成）/ `weekly-strategy-context.json` / `article-ideas.md` / `daily-preview.md` / `political-digest.md` / `compliance-scan.md` / `site-qa-report.md`**
  （※CLAUDE.mdのSYNC禁忌リストに全て追記済。`python mw.py check` がSYNC_FILESへの誤混入を自動検知）
- SYNC対象（OK）：`*.py`（compute_levels.py 等）/ `.github/workflows/*.yml` / 個別 guide-*.html / guides.html / `robots.txt` / my-trades.json / memory/*.md / docs。（sitemap.xml は禁忌へ移動）
- 記事追加は **`python mw.py publish`（推奨・8ステップの②④⑤を機械化）→ sync → workflow → ライブ確認**。③sitemapは自動。**公開前に compliance-reviewer（Opus）監査・教育トーン・特定銘柄の買い推奨は書かない・kinsho-v1免責・9ボタンナビ**。手動で行う場合も `mw check` でpush前点検。
- ネット不調時は無限リトライせず手動 trigger 依頼（最大3-5回）。

---

## 📌 次セッションの候補・宿題

0. 🎯 **【最優先・戦略】年商1000万ロードマップの作成（2026-06-01 ユーザー提起）**：北極星「サイト・SNS 年収1000万」へゴール逆算の計画を1枚作り、毎回の作業をそこに紐付ける。次セッション冒頭で作成推奨。
   - **収益レバー（仮説・要精査）**：①アフィリエイト（証券口座紹介＝1件1〜3万円の最大レバー、ただし**弁護士相談クリア前提**・無登録投資助言業/景表法/ステマ規制）②AdSense（PV依存。月数十万PV規模が必要）③note有料記事/メンバーシップ ④将来：スポンサー/自社商材。
   - **エンジン＝SEO×記事量産×SNS流入**：今ある40+記事・sitemap全自動・mw publish の量産体制を活かす。KPI候補：月間PV／AdSense RPM／アフィリ成約／記事数／SNSフォロワー。
   - **フェーズ案**：P1 基盤（PV成長＋弁護士相談で収益化の法務クリア）→ P2 収益化ON（AdSense最適化＋アフィリ設置）→ P3 拡大（記事速度＋SNS＋note）。
   - **制約**：サラリーマン（時間有限）／compliance（金融×アフィリは弁護士相談アジェンダ③と直結）。
   - → 次回：現状の月間PV・AdSense収益・記事数の実数を確認 → 1000万の内訳（収益ミックス）を置き → 月次マイルストーン＋KPIダッシュボード化を提案。
1. 🔜 **6/7(日) weekly-strategy-brief 初回サイクルのライブ確認**：17:00 levels→18:30 routine(3人＋検証)→20:13 描画 で、6/8週の「今週の投資戦略」記事に **verified=true の正確な数字シナリオ**が載るか確認（`mw status weekly-strategy.yml` ＋ 記事ライブ）。
   - 🆕 6/1実装：**ファンダ整合フィボ押し目シグナル**（fib_pullback、メールON・両方向・ゴールデンポケット50-61.8%）が4Hメールに乗る。発火件数と実勝率を signals-log で監視（詳細 memory/04_technical_rules.md）。
2. ✅ Max枠確認済（Max込み15/日・追加課金なし）／✅ SYNC禁忌・保守ツール群 構築済（5/31〜6/1）。
3. **記事ネタ（ユーザー興味ベース）**：他セクター深掘り→`mw publish` で公開（AI半導体／ディフェンシブ／高配当 等）。
4. **日本株ゾーンの週次組込**（保留中）：PBR1.0・配当利回りの床を weekly-zone-plan に追加する案。
5. **シグナル再設計 Phase2**：fundamental_context / bias_aligned のデータが貯まったら signals-log で検証。
6. **弁護士相談アジェンダ**：track-record統計開示／⭐確信度ラベル／「ソース信頼度」ラベル／セクター・個別銘柄記事の言及。
7. 🟢低優先（QA `site-qa-report.md` 由来）：古い自動生成ページ（5月 monthly-report 等）のナビは次の生成サイクルで9ボタンに更新される（過去ページのため放置可）／月次・週次レポートを guides.html に「📊 レポート」カテゴリで載せる案（03_initiatives R5）。

---

## 運用メモ
- 作業フォルダ: `C:\Users\info0\OneDrive\デスクトップ\新しいフォルダー` ／ GitHub: `invest-ai-info/marketwatch-ai`(main)
- **運用は `python mw.py <cmd>` が単一入口**（check / publish / sync / trigger / status / routines）。`mw routines` で全routineのID一覧。
- 同期は `python sync_to_github.py`（または `mw sync`）。workflow手動起動は `mw trigger <wf.yml>`（GitHub API、tokenは market-news-config.json.json）。**ローカルは UTF-8 強制が必要**：`$env:PYTHONUTF8="1"`（PowerShell）等。
- routine操作: schedule スキル → `ToolSearch select:RemoteTrigger` → RemoteTrigger（list/get/update/run）。
- ⚠️ **ローカルは GitHub と未同期なことがある**（OneDrive。core HTML / guide-weekly 等は手元に無い/古い＝正常）。真の状態は GitHub/ライブを見る。
- ユーザー方針: 「攻めと守りの両建て」「感情に左右されない自動化」「記事化するネタ＝本人の興味」。最終目標は投資家全体の底上げ／サイトSNS年収1000万／個人投資成績 年収1億。
