# drafts/REVIEW.md から抜いた見出しの実物（2026-09-17 時点）。
# §⑧ が読めなければならない書式をここで凍結する。**実データが直っても腐らない**ように、
# 本文は落として見出し行だけを残してある。

2026-09-17 signal-lab: 🚨 #097 は🚩エスカレ中なのに finalize 済みの `guide-signal-lab-097.html` がルートに残っており、**sitemap に載り #096「次」/#099「前」から読めてしまう状態だった**（9/13〜9/17）。応急処置として ①ルート版に noindex を付与 ②sitemap から削除 ③前後ナビを #096↔#099 に貼り替え ④#100 本文のリンクを解除 を実施。**ファイル自体の削除はオーナー承認待ち**。再発防止＝`check_site_consistency.py` が「カード無し＆noi
2026-09-14 signal-lab: draft-signal-lab-098.html 🚩エスカレ中（Opusコンプラ🔴黒①②③・数値訂正3件要人間レビュー）
## 2026-09-14 signal-lab #098: draft-signal-lab-098.html
## 2026-09-13 signal-lab #097: draft-signal-lab-097.html
2026-09-15 autopublish: guide-base-rate-neglect.html 公開済み ✅ 決定論緑・Opus🟡グレー修正→独立白確認 https://marketwatch-jp.com/guide-base-rate-neglect.html
2026-09-18 signal-lab: #102 ✅自動公開済み（テーマ：もみあい×ショート⛔反証解剖。OOS 112/295=38.0%・E(R)=-0.11。verify緑→Opus3回独立監査白→finalize→publish完了）
## 2026-09-11 signal-lab: guide-signal-lab-095.html ✅公開済み
## 2026-09-02 autopublish: 🚩要人間レビュー: bid-ask-spread（品質③ブロッカー2件・コンプラ白・公開せず）
## 2026-08-28 🚩 要人間レビュー | shareholder-benefits | autopublish
## 2026-08-25 signal-lab: 🚩 要人間レビュー | #079 tf=1d×reversalL 日足逆張り買い正式検証 | drafts/draft-signal-lab-079.html
## 2026-08-23 🚩要人間レビュー（コンプラ🔴：事実誤認＋kinsho-v1不足） | signal-lab-daily #077
## 2026-08-18 | 🚩要人間レビュー（コンプラ：黒・期間ラベル誤記） | signal-lab-daily #072 | signal-lab-daily
## 2026-08-16 | 🚩 コンプラ🔴黒（数値整合不備）[解消済み] | signal-lab-daily #071 | ~~人間対応必要~~
## 2026-08-15 | 🚩 ゲート赤（旧ブランドカラー5箇所） | book-watch-weekly | 人間対応必要
## 2026-08-11 | 🚩 独立Opus否・FWDデータ修正要 | signal-lab-067 | signal-lab-daily
2026-08-08 autopublish: 🚩ゲート赤／インフラ未解決（3日連続）: key=margin-trading / `check_guide_draft.py` の検査#9が `apply_brand_color` モジュール（origin/mainに不在）を import しようとして ModuleNotFoundError → EXIT=1。固定オラクル＝ゲートの編集・迂回は禁止のため公開せずエスカレ。**人間必須の対処**: ローカルで `apply_brand_color.py` を作成し SYNC_FILES に追加→push → ゲート EXIT=0 確認 → 次回
## 2026-07-08 | autopublish: 🚩要人間レビュー — guide-inflation-real-return.html（check_site_consistency EXIT=1）
