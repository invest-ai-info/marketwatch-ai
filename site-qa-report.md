# 🧪 サイト整合性 QA レポート（基準日 JST）

**実行日時**: 2026-08-15 10:11 JST  
**チェッカー**: `check_site_consistency.py`  
**対象 guide 記事**: 278 件（自動生成記事を除く）

---

## ✅ 総合結果：OK

| 区分 | 件数 |
|---|---|
| ❌ エラー（exit 1） | **0 件** |
| ⚠️ 警告 | **16 件** |

SYNC 禁忌の混入なし。免責漏れなし。リンク切れなし。

---

## ⚠️ 警告一覧（16 件）

### 1. 「↑上に戻る」ボタン欠落（2 件）

以下のファイルに `mw-back-to-top` ボタンが存在しない。

| ファイル | 対応コマンド |
|---|---|
| `guide-new-books.html` | `python apply_back_to_top.py` |
| `guide-scam-sns-celebrity-ad.html` | `python apply_back_to_top.py` |

### 2. ナビ CSS max-width 欠落（14 件）

以下のファイルのナビゲーション CSS に `max-width` が不足しており、8+2 レイアウトが崩れる可能性がある。

| ファイル | 対応コマンド |
|---|---|
| `guide-auto-boj-2026-06-17.html` | `python apply_nav_css.py` |
| `guide-auto-fomc-2026-06-17.html` | `python apply_nav_css.py` |
| `guide-auto-us_cpi-2026-05-14.html` | `python apply_nav_css.py` |
| `guide-auto-us_cpi-2026-06-10.html` | `python apply_nav_css.py` |
| `guide-auto-us_jobs-2026-06-05.html` | `python apply_nav_css.py` |
| `guide-auto-us_pce-2026-05-30.html` | `python apply_nav_css.py` |
| `guide-auto-us_pce-2026-06-27.html` | `python apply_nav_css.py` |
| `guide-weekly-2026-05-25.html` | `python apply_nav_css.py` |
| `guide-weekly-2026-06-01.html` | `python apply_nav_css.py` |
| `guide-weekly-2026-06-08.html` | `python apply_nav_css.py` |
| `guide-weekly-2026-06-15.html` | `python apply_nav_css.py` |
| `guide-weekly-2026-06-22.html` | `python apply_nav_css.py` |
| `guide-weekly-review-2026-06-15.html` | `python apply_nav_css.py` |

---

## 推奨対応

| 優先度 | 項目 | 対応 |
|---|---|---|
| 🟡 中 | ナビ CSS max-width 欠落（13 件） | `python apply_nav_css.py --apply` で一括修正 |
| 🟡 低 | 「↑上に戻る」ボタン欠落（2 件） | `python apply_back_to_top.py --apply` で一括修正 |

> **SYNC 禁忌の混入・免責漏れ・リンク切れはいずれも検出されませんでした。** 今週のシステムドリフトは軽微な UI 問題のみです。先週（2026-08-08）の警告 15 件から 1 件増（`guide-scam-sns-celebrity-ad.html` の戻るボタン欠落が新たに検出）。

---

## 📋 リンター生出力

```
🔍 サイト整合性チェック（check_site_consistency.py）
  検査した guide記事: 278 件（自動生成記事を除く） / SYNC_FILES: ローカル専用のためスキップ（sync_to_github.py がリモートに無い＝正常）

⚠️  警告 16 件:
   - sync_to_github.py はクラウド用スタブ（想定どおり）→ SYNC_FILES 系チェックをスキップ
   - guide-new-books.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-scam-sns-celebrity-ad.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
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

結果: ✅ OK（エラーなし・警告 16 件）
EXIT_CODE: 0
```
