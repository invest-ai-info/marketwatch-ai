# 🧪 サイト整合性 QA レポート（2026-10-10 JST）

**基準日**: 2026-10-10 JST 10:09  
**実行**: `check_site_consistency.py`  
**結果**: ✅ **OK（エラーなし・警告 34 件）**

---

## 📋 検査概要

| 項目 | 結果 | 前回比 |
|---|---|---|
| **エラー件数** | 0 | — |
| **警告件数** | 34 | +5 |
| **SYNC禁忌混入** | ❌ なし | — |
| **免責タグ（kinsho-v1）** | ✅ 正常 | — |
| **ナビバー（10ボタン）** | ✅ 正常 | — |
| **リンク切れ** | ✅ 正常 | — |
| **検査対象 guide記事** | 499 件 | +26 |

**判定**: ✅ **サイト整合性は維持されています。警告は全て軽微な推奨修正です。**  
⚠️ **注記**: guide 記事が 473 → 499 件に増加（26 件新規）したため、相対的に警告も増えています。

---

## ⚠️ 警告リスト（グループ別）

### グループ 1: ナビゲーション CSS（max-width 欠落）— 13 件

**影響**: 8+2 レイアウト崩れ（モバイル 375px でナビが折れる）  
**修正方法**: `python apply_nav_css.py`

```
- guide-auto-boj-2026-06-17.html
- guide-auto-fomc-2026-06-17.html
- guide-auto-us_cpi-2026-05-14.html
- guide-auto-us_cpi-2026-06-10.html
- guide-auto-us_jobs-2026-06-05.html
- guide-auto-us_pce-2026-05-30.html
- guide-auto-us_pce-2026-06-27.html
- guide-weekly-2026-05-25.html
- guide-weekly-2026-06-01.html
- guide-weekly-2026-06-08.html
- guide-weekly-2026-06-15.html
- guide-weekly-2026-06-22.html
- guide-weekly-review-2026-06-15.html
```

### グループ 2: 「↑上に戻る」ボタン（mw-back-to-top）— 17 件

**影響**: スクロール用ボタン欠落（UX 低下）  
**修正方法**: `python apply_back_to_top.py`  
**増加**: +8 件（entry シリーズ新規追加）

```
- guide-entry-breakout.html
- guide-entry-carry-trade.html
- guide-entry-cot-report.html ⬅️ NEW
- guide-entry-cross-sectional-momentum.html
- guide-entry-day-of-week.html ⬅️ NEW
- guide-entry-earnings-drift.html ⬅️ NEW
- guide-entry-ma-crossover-rules.html
- guide-entry-macro-surprise.html ⬅️ NEW
- guide-entry-momentum-crash.html
- guide-entry-overnight-intraday.html ⬅️ NEW
- guide-entry-pre-fomc.html ⬅️ NEW
- guide-entry-short-term-reversal.html
- guide-entry-technical-indicators.html
- guide-entry-trend-following.html
- guide-entry-turn-of-month.html ⬅️ NEW
- guide-new-books.html
```

### グループ 3: スマホ横はみ出し防止 CSS — 1 件

**影響**: 画像やテーブルがスマホで横スクロール  
**修正方法**: `python fix_mobile_overflow.py`

```
- guide-signal-lab-079.html
```

### グループ 4: 免責が三層でない — 3 件

**影響**: 法務監査上の免責バナーの欠落  
**修正方法**: `python apply_disclaimer.py --apply`  
**減少**: -1 件（guide-signal-lab-115, 116 は前回から修正済み）

```
- guide-signal-lab-112.html（フッター欠落）
- guide-signal-lab-113.html（上部バナー・フッター欠落）
- guide-signal-lab-120.html（フッター欠落）⬅️ NEW
```

### グループ 5: クラウド用スタブ — 1 件

**内容**: `sync_to_github.py` がクラウド環境のため SYNC_FILES チェックをスキップ  
**判定**: 正常動作（エラーではない）

---

## ✅ 正常項目

- **SYNC禁忌ファイルの混入**: なし ✓
- **免責タグ（kinsho-v1）**: 全記事で検出 ✓
- **ナビバー構成**: 10 ボタン確認 ✓
- **リンク内部参照**: 切れなし ✓

---

## 🔧 推奨対応

| 優先度 | 項目 | アクション | 件数 |
|---|---|---|---|
| 🟡 中 | ナビ CSS | `python apply_nav_css.py` | 13 件 |
| 🟡 中 | 戻るボタン | `python apply_back_to_top.py` | 17 件 |
| 🟡 中 | 横はみ出し | `python fix_mobile_overflow.py` | 1 件 |
| 🟡 中 | 免責三層 | `python apply_disclaimer.py --apply` | 3 件 |

**見積実行時間**: 約 3-5 分で全修正完了  
**見積効果**: 新規追加 26 記事のうち、4 つの UX/法務ツールで統一化可能

---

## 📊 リンター生出力

```
🔍 サイト整合性チェック（check_site_consistency.py）
  検査した guide記事: 499 件（自動生成記事を除く） / SYNC_FILES: ローカル専用のためスキップ（sync_to_github.py がリモートに無い＝正常）

⚠️  警告 34 件:
   - sync_to_github.py はクラウド用スタブ（想定どおり）→ SYNC_FILES 系チェックをスキップ
   - guide-entry-breakout.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-entry-carry-trade.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-entry-cot-report.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-entry-cross-sectional-momentum.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-entry-day-of-week.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-entry-earnings-drift.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-entry-ma-crossover-rules.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-entry-macro-surprise.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-entry-momentum-crash.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-entry-overnight-intraday.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-entry-pre-fomc.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-entry-short-term-reversal.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-entry-technical-indicators.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-entry-trend-following.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-entry-turn-of-month.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-new-books.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-signal-lab-079.html: スマホ横はみ出し防止CSS(mw-mobile-fit)が無い → `python fix_mobile_overflow.py`
   - guide-signal-lab-112.html: 免責が三層でない（欠け: フッター） → `python apply_disclaimer.py --apply`
   - guide-signal-lab-113.html: 免責が三層でない（欠け: 上部バナー・フッター） → `python apply_disclaimer.py --apply`
   - guide-signal-lab-120.html: 免責が三層でない（欠け: フッター） → `python apply_disclaimer.py --apply`
   - guide-auto-boj-2026-06-17.html: ナビCSSに max-width 欠落（8+2崩れ）→ python apply_nav_css.py
   - guide-auto-fomc-2026-06-17.html: ナビCSSに max-width 欠落（8+2崩れ）→ python apply_nav_css.py
   - guide-auto-us_cpi-2026-05-14.html: ナビCSSに max-width 欠落（8+2崩れ）→ python apply_nav_css.py
   - guide-auto-us_cpi-2026-06-10.html: ナビCSSに max-width 欠落（8+2崩れ）→ python apply_nav_css.py
   - guide-auto-us_jobs-2026-06-05.html: ナビCSSに max-width 欠落（8+2崩れ）→ python apply_nav_css.py
   - guide-auto-us_pce-2026-05-30.html: ナビCSSに max-width 欠落（8+2崩れ）→ python apply_nav_css.py
   - guide-auto-us_pce-2026-06-27.html: ナビCSSに max-width 欠落（8+2崩れ）→ python apply_nav_css.py
   - guide-weekly-2026-05-25.html: ナビCSSに max-width 欠落（8+2崩れ）→ python apply_nav_css.py
   - guide-weekly-2026-06-01.html: ナビCSSに max-width 欠落（8+2崩れ）→ python apply_nav_css.py
   - guide-weekly-2026-06-08.html: ナビCSSに max-width 欠落（8+2崩れ）→ python apply_nav_css.py
   - guide-weekly-2026-06-15.html: ナビCSSに max-width 欠落（8+2崩れ）→ python apply_nav_css.py
   - guide-weekly-2026-06-22.html: ナビCSSに max-width 欠落（8+2崩れ）→ python apply_nav_css.py
   - guide-weekly-review-2026-06-15.html: ナビCSSに max-width 欠落（8+2崩れ）→ python apply_nav_css.py

結果: ✅ OK（エラーなし・警告 34 件）
```

---

**生成日時**: 2026-10-10 10:09 JST  
**前回チェック**: 2026-10-03（警告 29 件）  
**変化**: 警告 +5 件、guide 記事 +26 件  
**次回予定**: 2026-10-17（土）10:00 JST
