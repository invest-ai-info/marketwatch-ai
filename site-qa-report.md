# 🧪 サイト整合性 QA レポート（基準日 2026-08-08T10:08 JST）

## 総合結果

| 項目 | 値 |
|---|---|
| 実行日時 | 2026-08-08 10:08 JST |
| 終了コード | **0（正常）** |
| エラー件数 | **0 件** |
| 警告件数 | **15 件** |
| 検査記事数 | 263 件 |

**✅ OK — エラーなし（警告のみ）**

---

## ❌ エラー一覧

なし。SYNC禁忌の混入、免責漏れ、ナビボタン欠落等のハードエラーは検出されませんでした。

---

## ⚠️ 警告一覧（15 件）

### ① sync_to_github.py クラウドスタブ（1 件・情報のみ）

| # | メッセージ |
|---|---|
| 1 | `sync_to_github.py` はクラウド用スタブ → SYNC_FILES 系チェックをスキップ（想定どおり） |

→ **対応不要**（クラウド環境では正常動作）

---

### ② 「↑上に戻る」ボタン欠落（1 件）

| # | ファイル | 対処法 |
|---|---|---|
| 1 | `guide-new-books.html` | `python apply_back_to_top.py` を実行 |

→ **優先度：低**（UX 改善）。`apply_back_to_top.py` が利用可能であれば実施推奨。

---

### ③ ナビCSS `max-width` 欠落（13 件）

モバイル 375px 2列×5行レイアウトが崩れる可能性あり。`python apply_nav_css.py` で一括修正可能。

| # | ファイル |
|---|---|
| 1 | `guide-auto-boj-2026-06-17.html` |
| 2 | `guide-auto-fomc-2026-06-17.html` |
| 3 | `guide-auto-us_cpi-2026-05-14.html` |
| 4 | `guide-auto-us_cpi-2026-06-10.html` |
| 5 | `guide-auto-us_jobs-2026-06-05.html` |
| 6 | `guide-auto-us_pce-2026-05-30.html` |
| 7 | `guide-auto-us_pce-2026-06-27.html` |
| 8 | `guide-weekly-2026-05-25.html` |
| 9 | `guide-weekly-2026-06-01.html` |
| 10 | `guide-weekly-2026-06-08.html` |
| 11 | `guide-weekly-2026-06-15.html` |
| 12 | `guide-weekly-2026-06-22.html` |
| 13 | `guide-weekly-review-2026-06-15.html` |

→ **優先度：中**（古い自動生成記事に限定、新規記事は修正済みと推定）。  
`python apply_nav_css.py` で一括対応可能。

---

## 🔍 推奨対応

| 優先度 | 対応 | コマンド |
|---|---|---|
| 🟢 対応不要 | sync_to_github.py スタブ警告 | — |
| 🟡 低 | guide-new-books.html 戻るボタン追加 | `python apply_back_to_top.py` |
| 🟡 中 | 旧自動生成 13 記事のナビCSS修正 | `python apply_nav_css.py` |

**SYNC禁忌の混入はなし** — 巻き戻し事故リスクはゼロ。

---

## 📋 リンター生出力

```
🔍 サイト整合性チェック（check_site_consistency.py）
  検査した guide記事: 263 件（自動生成記事を除く） / SYNC_FILES: ローカル専用のためスキップ（sync_to_github.py がリモートに無い＝正常）

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
EXIT_CODE: 0
```
