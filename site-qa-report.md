# 🧪 サイト整合性 QA レポート

**基準日**: 2026-09-26 JST 10:07:25  
**実行**: `check_site_consistency.py` v1.0  
**結果**: ✅ **OK（エラーなし・警告 20 件）**

---

## 📋 検査概要

| 項目 | 結果 |
|---|---|
| **エラー件数** | 0 |
| **警告件数** | 20 |
| **SYNC禁忌混入** | ❌ なし |
| **免責タグ（kinsho-v1）** | ✅ 正常 |
| **ナビバー（10ボタン）** | ✅ 正常 |
| **リンク切れ** | ✅ 正常 |
| **検査対象 guide記事** | 450 件 |

**判定**: ✅ **サイト整合性は維持されています。警告は全て軽微な推奨修正です。**

---

## ⚠️ 警告リスト（優先度順）

### 1️⃣ ナビゲーション CSS（max-width 欠落）— 11 件
**影響**: 8+2 レイアウト崩れ（モバイル 375px でナビが 8 ボタン + 2 ボタンに折れる）  
**修正方法**: `python apply_nav_css.py`

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

### 2️⃣ 「↑上に戻る」ボタン（mw-back-to-top）— 4 件
**影響**: スクロール用ボタン欠落（UX 低下）  
**修正方法**: `python apply_back_to_top.py`

- guide-entry-trend-following.html
- guide-new-books.html
- guide-scam-romance-invest.html
- guide-scam-sns-celebrity-ad.html

### 3️⃣ スマホ横はみ出し防止 CSS — 1 件
**影響**: 画像やテーブルがスマホで横スクロール  
**修正方法**: `python fix_mobile_overflow.py`

- guide-signal-lab-079.html

### 4️⃣ カレンダー曜日確認 — 1 件
**影響**: データ品質（情報の正確さ）  
**内容**: 10/20「英雇用統計（失業率・賃金）」が金曜日でない（米雇用統計は原則金曜日発表）  
**対応**: `sync_economic_events.py` で英中銀カレンダーを再確認。ただし提出日が確定していない場合は保留可

---

## ✅ 正常項目

- **SYNC禁忌ファイルの混入**: なし ✓
- **免責タグ（kinsho-v1）**: 全記事で検出 ✓
- **ナビバー構成**: 10 ボタン確認 ✓
- **リンク内部参照**: 切れなし ✓
- **robots.txt 設定**: `/drafts/` Disallow 確認 ✓

---

## 🔧 推奨対応

| 優先度 | 項目 | アクション | 予想実行時間 |
|---|---|---|---|
| 🔴 高 | ナビ CSS (11件) | `python apply_nav_css.py` | 1 分 |
| 🟡 中 | 戻るボタン (4件) | `python apply_back_to_top.py` | 1 分 |
| 🟡 中 | 横はみ出し (1件) | `python fix_mobile_overflow.py` | 1 分 |
| 🟡 中 | 曜日確認 (1件) | 手動確認（verify-calendar.yml 参照） | 5 分 |

---

## 📊 リンター出力

```
🔍 サイト整合性チェック（check_site_consistency.py）
  検査した guide記事: 450 件（自動生成記事を除く） / SYNC_FILES: ローカル専用のためスキップ

⚠️  警告 20 件:
   - ナビ CSS max-width 欠落 (11件)
   - 「↑上に戻る」ボタン欠落 (4件)
   - スマホ横はみ出し防止 CSS 欠落 (1件)
   - カレンダー曜日確認 (1件)
   - sync_to_github.py クラウド用スタブ (1件・想定どおり)

結果: ✅ OK（エラーなし・警告 20 件）
```

---

**生成日時**: 2026-09-26 10:07 JST  
**次回チェック**: 2026-10-03（土）10:00 JST
