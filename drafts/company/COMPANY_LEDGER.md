# 数字で見る、話題の企業 — 台帳（COMPANY_LEDGER）

routine `company-weekly-auto` が毎週1件ずつ追記する。詳細な手順は `drafts/COMPANY_GUIDE.md`。

---

## 2026-09-01（第1回・初回実行）

### 初回の到達性実測（クラウド環境、curl）

COMPANY_GUIDE.md の指示に基づき、まず日本・米国の一次情報ソースへの到達性を実測。

| 対象 | URL | 結果 | 分類 |
|---|---|---|---|
| EDINET トップページ | disclosure2.edinet-fsa.go.jp | 200 | 到達 |
| EDINET 書類検索API (v1) | disclosure.edinet-fsa.go.jp/api/v1/documents.json | **403「The request is blocked」** | 先方のbot判定（WAF） |
| EDINET 書類検索API (v2) | api.edinet-fsa.go.jp/api/v2/documents.json | 401（要有効なSubscription-Key。未登録のため利用不可） | 先方の認証要件 |
| TDnet トップページ | release.tdnet.info | 200 | 到達 |
| TDnet 日別開示リスト | release.tdnet.info/inbs/I_list_00N_YYYYMMDD.html | 200（**ただし直近約5〜6週間のみ保持**。2026-09-01時点で2026-07-24より前は404） | 到達（範囲限定） |
| JPX トップページ | jpx.co.jp | 200 | 到達 |
| 個別企業IRサイト（例：advantest.com, tokiomarinehd.com, irbank.net） | 各社ドメイン | **`curl: (56) CONNECT tunnel failed, response 403`** | 経路（egress proxyの組織ポリシーによる拒否。`$HTTPS_PROXY/__agentproxy/status` で `connect_rejected` を確認） |
| SEC data.sec.gov (submissions API) | data.sec.gov/submissions/CIK*.json | 200 | 到達 |
| SEC www.sec.gov (EDGAR Archives) | www.sec.gov/Archives/edgar/data/... | 200 | 到達 |

**結論**：日本側は「有価証券報告書」の一次情報に**構造的に到達できない**（EDINET書類検索APIがbot判定で403、TDnetの保管期間は約5〜6週間で決算短信は拾えても6月頃の有報filingは窓の外、各社IRサイトはegress policyで遮断）。米国側（SEC EDGAR）は決算短信相当（10-Q）・年次報告書相当（10-K）とも安定して到達可能。

### 今週どちらを書くか

台帳が空＝初回のため、COMPANY_GUIDE.md の規定どおり**日本株から**検討開始。

### 日本株候補の検討→エスカレ

- **候補選定**：`jp-rankings.json` の直近14日ぶんを `git log`（`git fetch --depth=500` でシャロークローンを拡張して2026-08-24まで遡及）で確認。取得できたのは2026-08-26／08-27／08-28の3日分のみ（08-29〜09-01のjp-rankings.json更新コミットが見当たらず、cronの実行状況に懸念あり。automation-health側で別途要確認）。
  - gainers/losers/hotに2回以上登場し、かつ最終出現日から中3営業日（2026-09-01時点で3営業日クリア）が経過している銘柄のうち、時価総額最大は**アドバンテスト（6857）**（2026-08-26 gainers7位、2026-08-27 losers2位・hot19位。最終出現08-27→2026-09-01までに08-28・08-31・09-01の3営業日経過）。
  - ニュースレーンとの重複確認：直近14日の `guide-news-*.html` にアドバンテスト単独主役の記事はなし（NVIDIA・AMAT決算等の付随言及のみ）→重複なし。
  - 90日以内の本レーン既刊なし（台帳が空のため）。既刊個別記事もなし（`guide-kioxia-*` 等7社リストに含まれず）。
- **一次情報の到達確認**：
  - 決算短信：`release.tdnet.info` で2026年7月29日15:30開示の「2027年3月期 第1四半期決算短信〔IFRS〕(連結)」PDFを取得成功（`140120260728500866.pdf`、263,798バイト）。セグメント別売上高（テストシステム事業部門3,336億円・サービス他部門339億円）等の数値を確認。
  - **有価証券報告書：到達不可**。EDINET書類検索APIが403（bot判定）、TDnetの保管期間（約5〜6週間）は6月頃の有報filingをカバーせず、advantest.com（会社IR）はegress policyでCONNECT遮断。
- **判定**：COMPANY_GUIDE.md 2-2「決算短信と有報の両方に届かなければ、その週は書かずにエスカレする」に従い、**アドバンテストは今回エスカレ（非公開）**。決算短信自体は正常に取得できているため、次回以降このクラウド環境の制約が解消されれば再挑戦可能。

🚩 **要人間レビュー（アドバンテスト・6857）**：有価証券報告書に一次情報として到達できず、COMPANY_GUIDE.md 2-2 の規定によりエスカレ。本文はまだ書き起こしていないため `drafts/company/` への保存物なし。

### 海外株（米国）へ切替 → Apple(AAPL)を選定・公開

日本株側が環境要因でエスカレとなったため、同一週内で米国株側の到達性・候補充足を確認したところ両方とも良好だったため、今週の1本は**海外株**として進行（COMPANY_GUIDE.mdの「候補が無ければもう一方から選んでよい」の趣旨を、日本株側が今回到達不能だったケースに準用。判断の詳細は本行に記録し、オーナーの事後確認を仰ぐ）。

- **候補選定**：`earnings-calendar.json` の `us` で決算発表日が2営業日前〜14日前（2026-08-18〜2026-08-28）の企業はNVIDIA（8/26発表）とWalmart（8/20発表）。
  - 両社ともニュースレーンとの重複あり：NVIDIA→`guide-news-2026-08-27-nvidia-q2-fy2027-earnings-results.html`（8/27・14日以内）、Walmart→`guide-news-2026-08-20`相当の記事（NEWS_LEDGER記載、8/20・14日以内）。いずれも直近14日以内に当該企業が主役の記事あり→両方見送り。
  - ①が実質空のため②（直近15〜60日でguide-news主役だった海外企業）へ：候補はApple（8/2記事`guide-news-2026-08-02-apple-q3-earnings-drop.html`）、Amazon（8/1記事）、Alphabet（7/22-23記事）。SK Hynix・Samsung・CXMTは米国上場でなくSEC 10-K対象外のため対象外。
  - 時価総額（2026-09-01時点、WebSearchで確認）：Apple 約4.62兆ドル ＞ Alphabet・Amazonよりも大幅に大きい → **Apple(AAPL)を選定**。
  - 本レーンでのApple既刊なし（初回のため90日ルール該当なし）。個別deep-dive記事も無し（ニュース記事のみ）→⓪節は不要。
- **一次情報の到達確認**：SEC `data.sec.gov/submissions/CIK0000320193.json`（200）から直近10-K（2025-10-31提出、期末2025-09-27）・10-Q（2026-07-31提出、期末2026-06-27）を特定し、`www.sec.gov/Archives/edgar/data/320193/...` から両文書とも200で本文取得・セグメント別売上・Item 1A Risk Factors・Item 3 Legal Proceedingsを確認。SEC向けUser-Agentは `marketwatch-jp (https://marketwatch-jp.com)` を使用（個人メールアドレスは不使用）。
- **公開ファイル**：`guide-company-aapl-apple.html`
- **コンプラ監査**：後続で記録

