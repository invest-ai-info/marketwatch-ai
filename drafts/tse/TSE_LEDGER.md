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

（まだなし）

## エスカレ・要人間レビュー

### 🚩 2026-09-01 キュー#1「適時開示（TDnet）」 timely-disclosure 📄 — 一次情報（jpx.co.jp）未到達のため見送り

**選定した題材**: TSE_GUIDE.md キュー#1「適時開示（TDnet）」（slug: `timely-disclosure`、絵文字: 📄）。guides.html・本台帳のどちらにも未登録の先頭項目として選定。

**理由**: このシリーズの絶対条件（TSE_GUIDE.md §0・§2-3）により、制度の数値・仕組みの説明は一次情報を実際に開いて確認し、確認日を本文に明記する必要がある。しかし本セッションのクラウド実行環境では `www.jpx.co.jp` への到達がネットワークegressポリシーにより完全にブロックされている（上記「到達性チェック」参照）。キュー#1「適時開示（TDnet）」はJPXのTDnet制度そのものが主題であり、jpx.co.jpの一次情報なしに書くことは二次情報のみでの制度説明＝このシリーズで最も避けるべき事故に直結するため、`fsa.go.jp`のみでの代替執筆はしなかった。

**取った行動**: 記事は書いていない（本文作成に着手せず、下書きファイルも作成していない）。到達性チェック結果を本台帳に記録し、エスカレのみ実施。コンプラ監査・品質ルーブリックの実行対象なし。

**必要な対応（人間へ）**: 本セッションのネットワークegress許可リストに `www.jpx.co.jp`（TDnet・上場制度関連ページを含む）の追加を検討いただきたい。許可され次第、次回実行時に再度 curl / WebFetch で到達性を確認し、キュー#1から再開する。それまでは本レーンは「一次情報未到達」の状態が続く見込み（キュー全18件中、多くがjpx.co.jpの数値を要するため）。
