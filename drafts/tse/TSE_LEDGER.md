# 東証のしくみシリーズ TSE_LEDGER

## 一次情報 到達性チェック（クラウド実行環境・実測）

- **2026-09-01 02:38 UTC（11:38 JST）**：初回実行につき §TSE_GUIDE.md の指示どおり、着手前に一次情報サイトへの到達性を実測。
  - `www.jpx.co.jp`：**到達不可**。
    - curl: `curl: (56) CONNECT tunnel failed, response 403`（HTTP status 000）
    - WebFetch: `{"error_type":"EGRESS_BLOCKED","domain":"www.jpx.co.jp","message":"Access to www.jpx.co.jp is blocked by the network egress proxy."}`
    - プロキシの `__agentproxy/status` でも同時刻に `connect_rejected` / "gateway answered 403 to CONNECT (policy denial or upstream failure)" を記録（host: `www.jpx.co.jp:443`）。
    - **遮断の種類＝経路（許可リスト）**。先方サーバーのbot判定（`cf-mitigated`等）ではなく、本セッションのネットワークegressポリシーが `jpx.co.jp` を許可リストに含めていないことによる拒否。UA偽装での迂回は行っていない。
  - `www.fsa.go.jp`：**到達可能**（curl実測 `HTTP:200`）。
  - 手元PC（オーナー環境）では両サイトとも2026-08-31時点で200到達済み（TSE_GUIDE.md記載）。**クラウド実行環境だけ jpx.co.jp が塞がれている**ことが今回判明。

## 公開済み記事

### ✅ 2026-09-02 キュー#1「適時開示（TDnet）」 timely-disclosure 📄

**題材**: TSE_GUIDE.md キュー#1「適時開示（TDnet）」（slug: `timely-disclosure`、絵文字: 📄、カテゴリ「東証のしくみ」）。前日2026-09-01は`www.jpx.co.jp`が経路遮断（`CONNECT tunnel failed`）でエスカレしたが、TSE_GUIDE §2の再試行ルール（経路遮断＝再試行可）に従い同じ題材を再度選定。

**一次情報の到達性（本日実測）**: `www.jpx.co.jp`への到達は**復旧済み**。curl（素のUA、偽装なし）で以下4URLすべてHTTP 200を実測（WebFetchのみ403＝先方のbot判定、curlは到達）：
- https://www.jpx.co.jp/equities/listing/disclosure/overview/index.html（適時開示制度の概要・更新日2025/08/26）
- https://www.jpx.co.jp/equities/listing/disclosure/tdnet/index.html（TDnetの概要・更新日2022/02/28）
- https://www.jpx.co.jp/equities/listing/disclosure/info/index.html（適時開示が求められる会社情報・更新日2026/07/03）
- https://www.jpx.co.jp/listing/disclosure/01.html（適時開示情報閲覧サービス ご利用案内・更新日2025/10/14）

確認日：2026-09-02（JST）。※`faq.jpx.co.jp`・`clientportal.jpx.co.jp`は引き続き経路遮断（`CONNECT tunnel failed`）だったが、本記事の執筆には`www.jpx.co.jp`本体の4ページで十分な一次情報が得られたため、これらへの依存なしで執筆完了。

**コンプラ監査**（.claude/agents/compliance-reviewer.md ペルソナ・model=opus）：
- 【初期判定】🟡グレー（黒0）— ①冒頭disclaimer-bannerに`data-disclaimer="kinsho-v1"`属性欠落（形式不備）②「減らします」の効果断定 ③インサイダー取引規制の説明が規制対象者を捨象し過度に単純化 ④（コンプラ外だが要修正）「法定開示は年1回・四半期ごと」が2024年施行の改正金商法（四半期報告書→半期報告書に一本化）と整合せず、記事自身の引用元（JPX overview）とも矛盾
- 4点すべて適用修正（事実・数値・SVG・構造は不変、表現軟化と属性追加のみ）
- 【独立最終確認】（別セッション・model=opus・Readのみ）→ 🟢白（修正反映確認・新規リスクなし）
- 品質ルーブリック：自己採点で5観点すべて✅（XBRL用語に初出説明を追加）

**公開**: `guide-tse-timely-disclosure.html`（読了約9分）。`publish_article.py`→`check_site_consistency.py`（EXIT=0、本記事に警告なし）→ `apply_back_to_top.py --apply`（本記事へ新規注入・既存33ページの正規化も同時実施）→ git push origin main（commit f60b48c, 3161db1）。

### ✅ 2026-09-03 キュー#2「値幅制限（ストップ高・ストップ安）」 price-limits 🛑

**題材**: TSE_GUIDE.md キュー#2「値幅制限（ストップ高・ストップ安）」（slug: `price-limits`、絵文字: 🛑、カテゴリ「東証のしくみ」）。guides.html・本台帳のどちらにも未登録の先頭項目として選定。当日分の `guide-tse-*.html` は未作成だったため着手（1日1本ルール準拠）。

**一次情報の到達性（本日実測）**: `www.jpx.co.jp`は素のcurl（UA偽装なし）でHTTP 200・到達可能（トップページ実測含む）。`www.fsa.go.jp`も200。以下3URLを実際にcurlで取得し内容を確認：
- https://www.jpx.co.jp/equities/trading/domestic/06.html（制限値幅｜内国株の売買制度・**ページ更新日 2026/09/02**）— 基準値段ごとの制限値幅の全表、臨時拡大の条件（2営業日連続の該当条件／ETF・ETN・レバレッジ商品の別条件）を確認。
- https://www.jpx.co.jp/glossary/sa/238.html（用語集「ストップ高・ストップ安」）
- https://www.jpx.co.jp/glossary/sa/239.html（用語集「ストップ配分」）— ストップ配分の具体例（A社5万株/B社7万株/C社6万株→B社→C社→A社の順に100株ずつ、結果A社600株/B社700株/C社700株）を一次情報からそのまま引用。

※WebFetchはjpx.co.jp系に対して403（先方のbot判定）を返したため、curlで取得したHTMLをローカルでテキスト抽出して内容確認した。UA偽装は行っていない（既定のcurl UAで200取得）。

確認日：2026-09-03（JST）。

**コンプラ監査**（.claude/agents/compliance-reviewer.md ペルソナ・model=opus）：
- 【初期判定】🟡グレー（黒0）— ①「調べれば必ず分かる」等の断定語の再生産 ②「投資家を守る」等、制度の効果を言い切る表現 ③見出し「達しやすい」の言い切り ④「安心です」等の不安解消訴求と読まれうる語 ⑤まとめの「実践的な対処になる」という行動を推す語感 ⑥ストップ配分引用への出典リンク明示の余地
- 6点すべて適用修正（事実・数値・SVG・構造・免責文言は不変、表現の軟化と出所明示の強化のみ。8箇所編集）
- 【独立最終確認】（別セッション・model=opus・Readのみ）→ 🟢白（修正反映確認・新規リスクなし）。冒頭disclaimer-bannerに`data-disclaimer="kinsho-v1"`属性が欠落している点を指摘されたため、公開前に属性を追加（事実・文言は不変の形式修正）。
- 品質ルーブリック：自己採点で5観点すべて✅

**公開**: `guide-tse-price-limits.html`（読了約9分）。`check_guide_draft.py`（GREEN）→`publish_article.py`→`check_site_consistency.py`（EXIT=0、警告32件はいずれも既存の他記事の警告＝本記事に起因する新規errorなし）→ `apply_back_to_top.py --apply`（本記事へ新規注入。同時に既存の`guide-bid-ask-spread.html`も正規化）→ 同時刻に別クラウドroutine（scam系）がpushしていたため`generate_market_news.py`の更新履歴リストと`sync_to_github.py`のSYNC_FILESで軽微なマージコンフリクトが発生、両エントリを残す形で解消 → git push origin main（commit 7c5e029, 440715a）。

## エスカレ・要人間レビュー

### 🚩 2026-09-01 キュー#1「適時開示（TDnet）」 timely-disclosure 📄 — 一次情報（jpx.co.jp）未到達のため見送り

**選定した題材**: TSE_GUIDE.md キュー#1「適時開示（TDnet）」（slug: `timely-disclosure`、絵文字: 📄）。guides.html・本台帳のどちらにも未登録の先頭項目として選定。

**理由**: このシリーズの絶対条件（TSE_GUIDE.md §0・§2-3）により、制度の数値・仕組みの説明は一次情報を実際に開いて確認し、確認日を本文に明記する必要がある。しかし本セッションのクラウド実行環境では `www.jpx.co.jp` への到達がネットワークegressポリシーにより完全にブロックされている（上記「到達性チェック」参照）。キュー#1「適時開示（TDnet）」はJPXのTDnet制度そのものが主題であり、jpx.co.jpの一次情報なしに書くことは二次情報のみでの制度説明＝このシリーズで最も避けるべき事故に直結するため、`fsa.go.jp`のみでの代替執筆はしなかった。

**取った行動**: 記事は書いていない（本文作成に着手せず、下書きファイルも作成していない）。到達性チェック結果を本台帳に記録し、エスカレのみ実施。コンプラ監査・品質ルーブリックの実行対象なし。

**必要な対応（人間へ）**: 本セッションのネットワークegress許可リストに `www.jpx.co.jp`（TDnet・上場制度関連ページを含む）の追加を検討いただきたい。許可され次第、次回実行時に再度 curl / WebFetch で到達性を確認し、キュー#1から再開する。それまでは本レーンは「一次情報未到達」の状態が続く見込み（キュー全18件中、多くがjpx.co.jpの数値を要するため）。

### ✅ 2026-09-04 キュー#3「呼値の単位（ティックサイズ）」 tick-size 📏

**題材**: TSE_GUIDE.md キュー#3「呼値の単位（ティックサイズ）」（slug: `tick-size`、絵文字: 📏、カテゴリ「東証のしくみ」）。guides.html・本台帳のどちらにも未登録の先頭項目として選定。当日分の `guide-tse-*.html` は未作成だったため着手（1日1本ルール準拠）。

**一次情報の到達性（本日実測）**: `www.jpx.co.jp`・`www.fsa.go.jp`ともcurlで素のUA・HTTP 200・到達可能（トップページ実測含む）。以下のURLを実際にcurlで取得し、HTMLをテキスト抽出して内容を確認：
- https://www.jpx.co.jp/equities/trading/domestic/07.html（呼値の単位｜内国株の売買制度・**ページ更新日 2026/08/06**）— 値段の水準×銘柄区分（TOPIX500構成銘柄／売買単位1口のETF等／その他の銘柄）の呼値表（全16段階）、2027年3月1日からSTR（Spread to Tick Ratio）に基づく制度へ変更予定である旨を確認。
- https://www.jpx.co.jp/equities/trading/strengthening/index.html（現物市場の機能強化に向けた取組み）— 呼値の単位の見直しがJPX「売買制度ワーキング・グループ」の議論に基づくものであることの背景確認（本文には未使用、事実確認のみ）。

※WebFetchはjpx.co.jp系に対して403（先方のbot判定）を返したため、curlで取得したHTMLをローカルでテキスト抽出して内容確認した（UA偽装なし）。JPX用語集（glossary/yo/配下）での「呼値」単独の定義ページは404が続き発見できなかったため、本文の定義は上記07.htmlの記述に基づく。

確認日：2026-09-04（JST）。

**コンプラ監査**（.claude/agents/compliance-reviewer.md ペルソナ・model=opus）：
- 【初期判定】🟡グレー（黒0）— ①「実質的な売買コストに直接関わってくる」の断定寄り表現 ②「TOPIX500構成銘柄のほうが5倍細かい」が銘柄区分の優劣の示唆に読まれうる（中立化の一文が無い） ③関連カードの「値段が飛びやすい傾向がある」が本文の緩和表現と不整合
- 3点すべて適用修正（事実・数値・SVG・構造・免責文言は不変、表現の軟化と中立化の一文追加のみ）
- コンプラ範囲外の実装バグ2件をエージェントが検出→自分で修正：a) `<div class="warning-box">`が`</p>`で誤って閉じられHTML構造が壊れていた（`</div>`に修正）b) 指値の刻み例（1,003円・10円刻み）が本文の呼値表と矛盾（1,003円は実際は0.5〜1円区分）→整合する価格帯（6,000円台・10円刻み）に差し替え
- 【独立最終確認】（別セッション・model=opus・Readのみ・JPX一次情報を再取得し表27セル全突合）→ 🟢白（修正反映確認・数値完全一致・HTML構造破綻なし・新規リスクなし）
- 品質ルーブリック：自己採点で5観点すべて✅

**公開**: `guide-tse-tick-size.html`（読了約9分）。`check_guide_draft.py`（GREEN）→コンプラ・品質ゲート通過→`publish_article.py`→`check_site_consistency.py`（EXIT=0、警告36件はいずれも既存の他記事の警告＝本記事に起因する新規errorなし）→ git push origin main（commit 551ce8e。pushコマンド実行時に一時的にHEAD detachedとなったため `git checkout -B main <commit>` で復帰してからpush）。
