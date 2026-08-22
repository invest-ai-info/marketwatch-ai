# 🧪 サイト整合性 QA レポート（基準日 JST: 2026-08-22 10:07）

## 結果サマリー

| 項目 | 値 |
|---|---|
| 実行日時（JST） | 2026-08-22 10:07 |
| 検査 guide 記事数 | 309 件（自動生成記事を除く） |
| 終了コード | 0（正常終了） |
| エラー件数 | **0 件** |
| 警告件数 | **24 件** |
| 総合判定 | ✅ OK |

---

## エラー一覧

**エラーなし。** SYNC禁忌の混入・免責漏れ・リンク切れ等の致命的問題は検出されませんでした。

---

## 警告一覧（24 件）

### ⓪ SYNC_FILES チェックスキップ（1 件・想定動作）

| # | 内容 |
|---|---|
| 1 | `sync_to_github.py` はクラウド用スタブ（想定どおり）→ SYNC_FILES 系チェックをスキップ |

**対応**: 不要（クラウド環境での正常動作）

---

### ① 「↑上に戻る」ボタン欠落（4 件）

以下のファイルに `mw-back-to-top` ボタンが見つかりません：

| # | ファイル |
|---|---|
| 1 | `guide-new-books.html` |
| 2 | `guide-scam-deepfake-scam.html` |
| 3 | `guide-scam-romance-invest.html` |
| 4 | `guide-scam-sns-celebrity-ad.html` |

**推奨対応**: `python apply_back_to_top.py` を実行（一括適用・冪等）

---

### ② ナビバー未登録リンク（6 件）

以下のファイルで `holdings.html` 等の必須リンクがナビに含まれていません（10 ボタン未満）：

| # | ファイル | 不足リンク |
|---|---|---|
| 1 | `guide-commodity-basics.html` | `holdings.html` |
| 2 | `guide-correlation-risk.html` | `index.html`, `political-feed.html`, `track-record.html`, `calendar.html`, `guides.html`, `guide-investment-books.html`, `holdings.html`, `market-health.html`, `hot-assets.html`, `charts.html`, `youtube-summary.html` |
| 3 | `guide-counterparty-risk.html` | `holdings.html` |
| 4 | `guide-market-hours.html` | `holdings.html` |
| 5 | `guide-reit-basics.html` | `index.html`, `political-feed.html`, `track-record.html`, `calendar.html`, `guides.html`, `guide-investment-books.html`, `holdings.html`, `market-health.html`, `hot-assets.html`, `charts.html`, `youtube-summary.html` |
| 6 | `guide-sunk-cost.html` | `holdings.html` |

**推奨対応**: `python unify_navbar.py --apply` を実行（10 ボタン標準を一括適用）

---

### ③ ナビ CSS `max-width` 欠落（13 件）

以下のファイルのナビバーに `max-width` が設定されておらず、8+2 レイアウト崩れの可能性があります：

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

**推奨対応**: `python apply_nav_css.py` を実行（一括適用・冪等）

---

## 推奨対応まとめ

| 優先度 | 内容 | コマンド |
|---|---|---|
| 🟡 中 | 「↑上に戻る」ボタン欠落 4 件 | `python apply_back_to_top.py` |
| 🟡 中 | ナビバーリンク不足（holdings.html 等）6 件 | `python unify_navbar.py --apply` |
| 🟡 低 | ナビ CSS max-width 欠落 13 件（古い記事） | `python apply_nav_css.py` |

> **SYNC禁忌の混入はゼロ**。巻き戻し事故リスクなし。
> 警告はすべて UI 品質の改善事項であり、緊急対応は不要です。

---

## リンター生出力

```
🔍 サイト整合性チェック（check_site_consistency.py）
  検査した guide記事: 309 件（自動生成記事を除く） / SYNC_FILES: ローカル専用のためスキップ（sync_to_github.py がリモートに無い＝正常）

⚠️  警告 24 件:
   - sync_to_github.py はクラウド用スタブ（想定どおり）→ SYNC_FILES 系チェックをスキップ
   - guide-new-books.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-scam-deepfake-scam.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-scam-romance-invest.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-scam-sns-celebrity-ad.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-commodity-basics.html: ナビに不足リンク ['holdings.html']（10ボタン未満）
   - guide-correlation-risk.html: ナビに不足リンク ['index.html', 'political-feed.html', 'track-record.html', 'calendar.html', 'guides.html', 'guide-investment-books.html', 'holdings.html', 'market-health.html', 'hot-assets.html', 'charts.html', 'youtube-summary.html']（10ボタン未満）
   - guide-counterparty-risk.html: ナビに不足リンク ['holdings.html']（10ボタン未満）
   - guide-market-hours.html: ナビに不足リンク ['holdings.html']（10ボタン未満）
   - guide-reit-basics.html: ナビに不足リンク ['index.html', 'political-feed.html', 'track-record.html', 'calendar.html', 'guides.html', 'guide-investment-books.html', 'holdings.html', 'market-health.html', 'hot-assets.html', 'charts.html', 'youtube-summary.html']（10ボタン未満）
   - guide-sunk-cost.html: ナビに不足リンク ['holdings.html']（10ボタン未満）
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

結果: ✅ OK（エラーなし・警告 24 件）
```
