# 🧪 サイト整合性 QA レポート（基準日 JST: 2026-08-01 10:08）

## 総合結果

| 項目 | 結果 |
|---|---|
| **総合判定** | ✅ OK（エラーなし） |
| **エラー件数** | 0 件 |
| **警告件数** | 15 件 |
| **検査 guide 記事数** | 238 件（自動生成除く） |
| **実行日時（JST）** | 2026-08-01 10:08:30 |

---

## ✅ エラー一覧（0件）

エラーなし。SYNC禁忌混入・免責漏れ・リンク切れは検出されませんでした。

---

## ⚠️ 警告一覧（15件）

### ① スキップ通知（正常・対応不要）

| # | ファイル | 内容 |
|---|---|---|
| 1 | `sync_to_github.py` | クラウド用スタブ（想定どおり）→ SYNC_FILES 系チェックをスキップ |

### ② 「↑上に戻る」ボタン欠落（1件）

| # | ファイル | 推奨対応 |
|---|---|---|
| 2 | `guide-new-books.html` | `python apply_back_to_top.py` を実行 |

> **備考**: `guide-new-books.html` は routine `book-watch-weekly` が毎週土曜に自動更新するファイル。
> `apply_back_to_top.py` を適用してから次回の routine 更新を確認するか、生成テンプレート側に組み込みを検討。

### ③ ナビCSS `max-width` 欠落（13件）

`python apply_nav_css.py` で一括修正可能。

| # | ファイル |
|---|---|
| 3 | `guide-auto-boj-2026-06-17.html` |
| 4 | `guide-auto-fomc-2026-06-17.html` |
| 5 | `guide-auto-us_cpi-2026-05-14.html` |
| 6 | `guide-auto-us_cpi-2026-06-10.html` |
| 7 | `guide-auto-us_jobs-2026-06-05.html` |
| 8 | `guide-auto-us_pce-2026-05-30.html` |
| 9 | `guide-auto-us_pce-2026-06-27.html` |
| 10 | `guide-weekly-2026-05-25.html` |
| 11 | `guide-weekly-2026-06-01.html` |
| 12 | `guide-weekly-2026-06-08.html` |
| 13 | `guide-weekly-2026-06-15.html` |
| 14 | `guide-weekly-2026-06-22.html` |
| 15 | `guide-weekly-review-2026-06-15.html` |

> **備考**: いずれも旧世代（ナビCSS改修以前）の自動生成記事。
> モバイル表示で「8+2列崩れ」が起きる可能性あり。`apply_nav_css.py` を実行してから push すると解消。
> ただし、週次記事（guide-weekly-*.html / guide-auto-*.html）は SYNC_FILES 登録状況を確認してから対応すること。

---

## 📋 推奨対応（優先順）

| 優先度 | 対応 | コマンド例 |
|---|---|---|
| 低 | ナビCSS max-width 欠落の一括修正 | `python apply_nav_css.py` → push |
| 低 | guide-new-books.html の「↑上に戻る」ボタン補完 | `python apply_back_to_top.py` → push または生成テンプレ修正 |

**エラーはゼロ**のため、即時対応が必要な項目はありません。次回の作業セッション時に余裕があれば上記を実施してください。

---

## 📄 リンター生出力

```
🔍 サイト整合性チェック（check_site_consistency.py）
  検査した guide記事: 238 件（自動生成記事を除く） / SYNC_FILES: ローカル専用のためスキップ（sync_to_github.py がリモートに無い＝正常）

⚠️  警告 15 件:
   - sync_to_github.py はクラウド用スタブ（想定どおり）→ SYNC_FILES 系チェックをスキップ
   - guide-new-books.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
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

結果: ✅ OK（エラーなし・警告 15 件）
EXIT_CODE:0
```
