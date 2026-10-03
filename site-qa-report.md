# 🧪 サイト整合性 QA レポート

**基準日**: 2026-10-03 JST 10:09  
**実行**: `check_site_consistency.py`  
**結果**: ✅ **OK（エラーなし・警告 29 件）**

---

## 📋 検査概要

| 項目 | 結果 |
|---|---|
| **エラー件数** | 0 |
| **警告件数** | 29 |
| **SYNC禁忌混入** | ❌ なし |
| **免責タグ（kinsho-v1）** | ✅ 正常 |
| **ナビバー（10ボタン）** | ✅ 正常 |
| **リンク切れ** | ✅ 正常 |
| **検査対象 guide記事** | 473 件 |

**判定**: ✅ **サイト整合性は維持されています。警告は全て軽微な推奨修正です。**

---

## ⚠️ 警告リスト（優先度順）

### 1️⃣ ナビゲーション CSS（max-width 欠落）— 13 件
**影響**: 8+2 レイアウト崩れ（モバイル 375px でナビが 8 ボタン + 2 ボタンに折れる）  
**修正方法**: `python apply_nav_css.py`

自動生成・過去記事:
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

### 2️⃣ 「↑上に戻る」ボタン（mw-back-to-top）— 9 件
**影響**: スクロール用ボタン欠落（UX 低下）  
**修正方法**: `python apply_back_to_top.py`

entry シリーズ新規追加記事:
- guide-entry-breakout.html
- guide-entry-carry-trade.html
- guide-entry-cross-sectional-momentum.html
- guide-entry-ma-crossover-rules.html
- guide-entry-momentum-crash.html
- guide-entry-short-term-reversal.html
- guide-entry-technical-indicators.html
- guide-entry-trend-following.html
- guide-new-books.html

### 3️⃣ スマホ横はみ出し防止 CSS — 1 件
**影響**: 画像やテーブルがスマホで横スクロール  
**修正方法**: `python fix_mobile_overflow.py`

- guide-signal-lab-079.html

### 4️⃣ 免責が三層でない — 4 件
**影響**: 法務監査上の免責バナーの欠落  
**修正方法**: `python apply_disclaimer.py --apply`

signal-lab 記事:
- guide-signal-lab-112.html（フッター欠落）
- guide-signal-lab-113.html（上部バナー・フッター欠落）
- guide-signal-lab-115.html（本文末・フッター欠落）
- guide-signal-lab-116.html（本文末・フッター欠落）

### 5️⃣ カレンダー曜日確認 — 1 件
**影響**: データ品質（情報の正確さ）  
**内容**: 10/20「英雇用統計（失業率・賃金）」が金曜日でない（米雇用統計は原則金曜日発表）  
**対応**: `verify_uk_eu_calendar.py` で英中銀・ONS カレンダーを再確認推奨

### 6️⃣ クラウド用スタブ（想定どおり） — 1 件
**内容**: `sync_to_github.py` がクラウド環境のため SYNC_FILES チェックをスキップ  
**判定**: 正常動作（エラーではない）

---

## ✅ 正常項目

- **SYNC禁忌ファイルの混入**: なし ✓
- **免責タグ（kinsho-v1）**: 全記事で検出 ✓
- **ナビバー構成**: 10 ボタン確認 ✓
- **リンク内部参照**: 切れなし ✓
- **robots.txt 設定**: `/drafts/` Disallow 確認 ✓

---

## 🔧 推奨対応

| 優先度 | 項目 | アクション | 件数 |
|---|---|---|---|
| 🟡 中 | ナビ CSS | `python apply_nav_css.py` | 13 件 |
| 🟡 中 | 戻るボタン | `python apply_back_to_top.py` | 9 件 |
| 🟡 中 | 横はみ出し | `python fix_mobile_overflow.py` | 1 件 |
| 🟡 中 | 免責三層 | `python apply_disclaimer.py --apply` | 4 件 |
| 🔵 低 | 曜日確認 | 手動確認（verify-calendar.yml 参照） | 1 件 |

**見積実行時間**: 約 3-5 分で全修正完了

---

## 📊 リンター出力

```
🔍 サイト整合性チェック（check_site_consistency.py）
  検査した guide記事: 473 件（自動生成記事を除く） / SYNC_FILES: ローカル専用のためスキップ（sync_to_github.py がリモートに無い＝正常）

⚠️  警告 29 件:
   - sync_to_github.py はクラウド用スタブ（想定どおり）→ SYNC_FILES 系チェックをスキップ
   - guide-entry-* 9件: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-signal-lab-079.html: スマホ横はみ出し防止CSS(mw-mobile-fit)が無い → `python fix_mobile_overflow.py`
   - guide-signal-lab-{112,113,115,116}.html: 免責が三層でない → `python apply_disclaimer.py --apply`
   - guide-auto-* / guide-weekly-* 13件: ナビCSSに max-width 欠落（8+2崩れ）→ python apply_nav_css.py
   - カレンダー: 10/20「英雇用統計（失業率・賃金）」が金曜でない（米雇用統計は原則金曜）＝要確認

結果: ✅ OK（エラーなし・警告 29 件）
```

---

**生成日時**: 2026-10-03 10:09 JST  
**前回チェック**: 2026-09-26（警告 20 件）  
**次回チェック**: 2026-10-10（土）10:00 JST
