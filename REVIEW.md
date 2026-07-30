# REVIEW.md — AIシグナル研究日誌 レビューログ

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
