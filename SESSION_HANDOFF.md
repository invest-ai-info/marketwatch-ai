# 🔖 セッション引き継ぎ（最終更新: 2026-06-02）

新セッションはこのファイル＋ CLAUDE.md ＋ `memory/03_initiatives.md`＋`ROADMAP_10M.md` を読めば文脈を復元できます。

---

## 🆕 2026-06-02 セッションの続き（最新・まずここを読む）

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
- **B（エンジン反映）は未適用＝レビュー待ち**。`generate_technical_alerts.py` の `calc_confidence_score`（L2158）に**データ駆動の加点/減点**を足す案。現状この関数は指標生値を受け取らないので**引数追加＋呼び出し側L2599の配線が必要**。本番のシグナルメールを変える変更なので、ユーザーGO後に実機の変数名を確認して安全に適用する。提案の中身はこのセッションのチャット参照（macd_dead×0ライン位置／方向×MA位置／ma_golden降格）。前向き検証タグも併せて入れる。
- ⚠️ 多重比較62セルの懸念は残る（macd_dead×MACD>0は依然「best of many」の可能性）→ 別レジームで各候補 n≥40 の前向き再現を確認するまで本採用しない。

#### ✅ 2026-06-03：テクニカル指標シリーズ 第4弾「RSI」公開
- **`guide-rsi.html`（新規・SYNC済・ライブHTTP200確認）**（約42KB・compliance🟢白「そのまま公開OK」）。RSIの計算式（RS＝平均上昇幅÷平均下落幅、RSI＝100−100/(1+RS)）・標準14・70/30の買われすぎ売られすぎ・50ライン（センターライン）・ダイバージェンス・**強いトレンドでの張り付き＝最大の弱点**を網羅。事実はWebSearchで照合（Wilder 1978『New Concepts...』）。
- **SVG概念図3点つき**：①全体像（価格＋0〜100オシレーター＋70/50/30ライン＋買われすぎ赤帯/売られすぎ緑帯）②買われすぎ→反落/売られすぎ→反発マーカー図 ③弱気ダイバージェンス（価格高値更新×RSI高値切り下げ）。**ライト/ダーク両対応をpreviewスクショで実機確認済**。RSI用クラス（.s-rsi/.s-ob-zone/.s-os-zone/.s-ob-line/.s-os-line/.s-ob-mark/.s-os-mark）を`<style>`に追加。
- section-8は「RSIは複合シグナルの構成要素として実際に使用」と正直に明記（CLAUDE.md実装と整合）。第1弾(MA)↔第3弾(MACD)↔第4弾(RSI)を内部リンクで相互接続、関連カードはMACD/MA/track-record。guides.html「📈チャートの読み方」最上段に掲載（badge-guide「解説」）。
- 公開フロー：guidesカードのみ手動挿入（publish_article.pyは--categoryをバッジ文字＆位置マッチ兼用のため）→`publish_article.py`でsync_to_github/更新履歴を自動追加→`mw check`✅→sync→`update-market-news.yml`起動(success)→index更新履歴・guides・記事すべてライブHTTP200確認。
- **🎯 次セッション：シリーズ第6弾以降**（**第5弾「ボリンジャーバンド」は2026-06-03公開済**。次はフィボナッチ＝実装済fib_pullbackと連携／エリオット波動／出来高／ストキャスティクス …。各記事にSVG概念図必須）。

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
