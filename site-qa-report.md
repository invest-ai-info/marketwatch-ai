# 🧪 サイト整合性 QA レポート（基準日 JST）

**基準日時**: 2026-07-25T10:08:38+09:00（UTC: 2026-07-25T01:08:38Z）
**実行スクリプト**: `check_site_consistency.py`
**検査対象 guide 記事**: 212 件（自動生成記事を除く）

---

## 結果サマリー

| 項目 | 件数 |
|---|---|
| ✅ エラー | **0 件** |
| ⚠️ 警告 | **16 件** |
| 全体判定 | **✅ OK** |

---

## ❌ エラー一覧

**エラーなし。** SYNC禁忌の混入・免責漏れ・リンク切れは検出されませんでした。

---

## ⚠️ 警告一覧

### カテゴリ①：SYNC_FILES チェックスキップ（1件・正常）
- `sync_to_github.py` はクラウド用スタブ（想定どおり）→ SYNC_FILES 系チェックをスキップ

### カテゴリ②：「↑上に戻る」ボタン欠落（2件）
対象ファイル：
- `guide-new-books.html`
- `guide-signal-anatomy.html`

修正コマンド：`python apply_back_to_top.py`

### カテゴリ③：ナビCSS `max-width` 欠落（13件・8+2ボタン崩れ可能性）
対象ファイル：
- `guide-auto-boj-2026-06-17.html`
- `guide-auto-fomc-2026-06-17.html`
- `guide-auto-us_cpi-2026-05-14.html`
- `guide-auto-us_cpi-2026-06-10.html`
- `guide-auto-us_jobs-2026-06-05.html`
- `guide-auto-us_pce-2026-05-30.html`
- `guide-auto-us_pce-2026-06-27.html`
- `guide-weekly-2026-05-25.html`
- `guide-weekly-2026-06-01.html`
- `guide-weekly-2026-06-08.html`
- `guide-weekly-2026-06-15.html`
- `guide-weekly-2026-06-22.html`
- `guide-weekly-review-2026-06-15.html`

修正コマンド：`python apply_nav_css.py`

---

## 推奨対応

| 優先度 | 項目 | 対応方法 |
|---|---|---|
| 🟡 低（余裕で対応） | ナビCSS `max-width` 欠落 13件 | `python apply_nav_css.py` を実行して一括修正 |
| 🟡 低（余裕で対応） | 「↑上に戻る」ボタン欠落 2件 | `python apply_back_to_top.py` を実行して一括修正 |

⚠️ いずれも古い記事（guide-auto-* / guide-weekly-*）に限定されており、新記事・主要コアページへの影響なし。モバイル表示崩れの可能性があるため、余裕があるタイミングで一括修正を推奨。

---

## リンター生出力

```
🔍 サイト整合性チェック（check_site_consistency.py）
  検査した guide記事: 212 件（自動生成記事を除く） / SYNC_FILES: ローカル専用のためスキップ（sync_to_github.py がリモートに無い＝正常）

⚠️  警告 16 件:
   - sync_to_github.py はクラウド用スタブ（想定どおり）→ SYNC_FILES 系チェックをスキップ
   - guide-new-books.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-signal-anatomy.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
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
EXIT_CODE:0
```
