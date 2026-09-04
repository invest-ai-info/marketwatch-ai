# REVIEW.md — AIシグナル研究日誌 レビューログ

---

## 2026-09-05｜#090 RSI売られすぎ逆張り買い N=296追跡

**テーマ**: rsi_oversold_bounce FWD N=296——昇格ストライク1回目再獲得・4H足65%・円クロスFX×4H 89%の二極化継続

**結果**: IS 52/133=39.1% CI[31.2%,47.6%] / **FWD 158/296=53.4% CI[47.7%,59.0%] E(R)=+0.244** / 4H 56/86=65.1% CI[54.6%,74.3%] / 1H 92/198=46.5% CI[39.7%,53.4%] / jpy_fx 38/62=61.3% / 4H×jpy_fx 16/18=88.9% CI[67.2%,96.9%] / 昇格ストライク1回目再獲得（CI下限+0.05>0）

**ゲート状況**: ✅自動公開済み（2026-09-05）
- signal_lab_verify.py: 14/14 GREEN → EXIT=0（修正前後2回）
- Opusコンプラ1: 🔴要協議（B-1追加分数値不一致/B-2 N=255→250誤記/A kinsho-v1属性欠落/C表現）→全修正実施（追加分行削除・N=250修正・属性付与・表現軟化）
- Opusコンプラ2（独立）: 🟢白（修正1件・L432表現軟化のみ・数値不変）
- verify再確認: EXIT=0（14/14 GREEN・SVG 0警告）
- finalize_signal_lab.py: EXIT=0 (kinsho=3, svg=4, size=39KB)
- publish_article.py: EXIT=0
- check_site_consistency.py: EXIT=0（エラー0・警告36件は既存問題）
- PUSH-MAIN: ✅ d650e04

**注記**: セッション引き継ぎ時に #089 が既公開（2026-09-04, N=287）であることを確認し、本日分を #090 として正しく採番。draft-signal-lab-089.htmlの誤作成ファイルはコミットせず。

---

## 2026-07-31｜#056 日足ロングのシグナル二極化

**仮説**: 日足ロング(1d×Long)のシグナル二極化——BB下限タッチ(+1.125R)とBB上限ブレイク(-1.250R)の2.375R差

**結果**:
- H1（棄却確認）: bb_upper_break×1d×Long → WR=7.1% CI[1.3%,31.5%] N=14 → ✅通過A
- H2（エッジ確認）: bb_lower_touch×1d×Long → E(R)=+1.125 RCI[+0.36,+1.89] N=16 → ✅通過A

**ゲート状況**: ✅自動公開済み（2026-07-31）
- signal_lab_verify.py: 7/7 GREEN → EXIT=0
- Opusコンプラ: 🟢白（2回確認）
- finalize_signal_lab.py: EXIT=0 (kinsho=4, svg=3)
- publish_article.py: EXIT=0
- check_site_consistency.py: EXIT=0（警告15件はすべて既存の別記事）
- PUSH-MAIN: b5c765a..b49ba1b ✅

---

## 2026-06-25｜#020 MA デッドクロス×ショートの非対称性

**仮説**: ma_dead × ショートは損益分岐43%を CI 下限で超えるか（#8 ma_golden×L 棄却確認の裏面）

**結果**: 62.5%（20/32）CI[45.3%〜77.1%] R=+0.456 → **通過A（CI下限45.3%≥43%・N=32）**

**主要発見**:
- ma_golden×L（29.5%）との差: **33.0pp の方向性非対称**
- blocked=True（N=17）: 82.4% R=+0.919 vs blocked=False（N=15）: 40.0% R=-0.068 → **差42.4pp**
- ma_dead 発火時のblocked=True比率=53%（全シグナル平均の約4倍）—— 主ドライバー疑い
- FX 集中（jpy_fx 10件・other_fx 14件）

**ゲート状況**: 実行中（8-1コミット→8-2検証→8-3コンプラ の順）

---
