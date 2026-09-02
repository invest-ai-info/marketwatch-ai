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

## エスカレ・要人間レビュー

### 🚩 2026-09-01 キュー#1「適時開示（TDnet）」 timely-disclosure 📄 — 一次情報（jpx.co.jp）未到達のため見送り

**選定した題材**: TSE_GUIDE.md キュー#1「適時開示（TDnet）」（slug: `timely-disclosure`、絵文字: 📄）。guides.html・本台帳のどちらにも未登録の先頭項目として選定。

**理由**: このシリーズの絶対条件（TSE_GUIDE.md §0・§2-3）により、制度の数値・仕組みの説明は一次情報を実際に開いて確認し、確認日を本文に明記する必要がある。しかし本セッションのクラウド実行環境では `www.jpx.co.jp` への到達がネットワークegressポリシーにより完全にブロックされている（上記「到達性チェック」参照）。キュー#1「適時開示（TDnet）」はJPXのTDnet制度そのものが主題であり、jpx.co.jpの一次情報なしに書くことは二次情報のみでの制度説明＝このシリーズで最も避けるべき事故に直結するため、`fsa.go.jp`のみでの代替執筆はしなかった。

**取った行動**: 記事は書いていない（本文作成に着手せず、下書きファイルも作成していない）。到達性チェック結果を本台帳に記録し、エスカレのみ実施。コンプラ監査・品質ルーブリックの実行対象なし。

**必要な対応（人間へ）**: 本セッションのネットワークegress許可リストに `www.jpx.co.jp`（TDnet・上場制度関連ページを含む）の追加を検討いただきたい。許可され次第、次回実行時に再度 curl / WebFetch で到達性を確認し、キュー#1から再開する。それまでは本レーンは「一次情報未到達」の状態が続く見込み（キュー全18件中、多くがjpx.co.jpの数値を要するため）。
