# エントリー方法の研究 — 台帳（ENTRY_LEDGER.md）

routine `entry-daily-auto` が毎日追記する台帳（GitHub 側で生成＝ローカルから push しない）。手順書は `drafts/ENTRY_GUIDE.md`。
1行＝1回。✅公開済み／🔁再試行可／🚩要人間レビュー／🔚完結。公開した回は「確かめた出典のURL」を必ず書く。

| 日付(JST) | # | slug | 結果 | コンプラ（初期/適用修正/独立確認） | 確かめた出典 | メモ |
|---|---|---|---|---|---|---|
| 2026-09-25 | — | — | 🆕レーン新設 | — | — | オーナー指示「エントリー方法を一つずつ深掘りするシリーズを、最初から自動で毎日1本」。広告なし |
| 2026-09-25 | #01 | trend-following | ✅公開済み | 初期🟡→軽微修正4件→独立確認🟢白 | https://www.sciencedirect.com/science/article/pii/S0304405X11002613（Moskowitz, Ooi & Pedersen 2012・要旨）／https://jpm.pm-research.com/content/44/1/15.abstract（Hurst, Ooi & Pedersen 2017・要旨）／https://www.sciencedirect.com/science/article/abs/pii/S0304405X19301953（Huang, Li, Wang & Zhou 2020・要旨） | 出版社ページは直接WebFetchが遮断（doi.org/sciencedirect/ssrn/jpm.pm-research.com/aqr.com/stern.nyu.edu/smu.edu.sg 等いずれもEGRESS_BLOCKED、bls.gov節と同型の制約）。WebSearchが返した検索結果内の逐語引用（引用符付き）で要旨の数字を確認し執筆。コンプラ初回🟡＝①「現在まで」→2016年までに訂正＋67市場を明記②2012年と2017年の主張を混ぜて強めていた文を分離③分散ポートフォリオ全体の成績である旨を追記④「市場も違う」の誤り（監視18銘柄は実際は重なる）を「判定のルールも同じではない」に訂正。独立Opusが最終確認して🟢白 |
| 2026-09-26 | #02 | breakout | ✅公開済み | 初期🟡→軽微修正4件→独立確認🟢白 | https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.1992.tb04681.x（Brock, Lakonishok & LeBaron 1992・要旨）／https://onlinelibrary.wiley.com/doi/10.1111/0022-1082.00163（Sullivan, Timmermann & White 1999・要旨） | 出版社ページ（onlinelibrary.wiley.com）は直接WebFetchがEGRESS_BLOCKED（#01と同型の制約）。WebSearchが返した検索結果内の逐語引用（引用符付きの要旨本文）で数字（ダウ平均1897-1986年・26ルール・7,846ルール・1987-1996年の検証期間）を確認し執筆。コンプラ初回🟡＝①「論文の考察部分で」という直接引用に読める書き方を「当サイトによる要約」と明示する形に修正②STWの最良1ルールの結果とBLLの傾向全体を混ぜて広く読ませていた2箇所を「サリバン氏らの研究では〜」に絞って訂正③当サイトシグナルとの関係の囲みに「市場も違う（研究は米国株価指数、当サイトは為替・金・原油等も対象）」の一文を追加④「必ず」を「いつも」に置換。独立Opusが最終確認して🟢白（品質ルーブリック5観点も自己採点で全て✅） |
