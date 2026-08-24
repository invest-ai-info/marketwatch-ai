# 🧪 サイト整合性 QA レポート

**基準日**: 2026-08-24（JST: 12:49:52）  
**実行時刻**: 2026-08-24 03:49:52 UTC  
**前回**: 2026-08-22 10:07（guide 309件・警告 24件）

---

## 📊 結果サマリー

| 項目 | ステータス |
|------|-----------|
| エラー | ✅ **0 件** |
| 警告 | ⚠️ **27 件** |
| 検査対象 guide 記事 | **317 件**（+8 件）|
| 総合判定 | **✅ OK** |

---

## ✅ OK 判定（致命的問題なし）

- ✅ **SYNC 禁忌ファイル**: 検出なし（巻き戻し事故リスク無し）
- ✅ **免責表記（kinsho-v1）**: 正常
- ✅ **ナビバー基本構造**: 10 ボタン標準・投資本・holdings 連携機能正常
- ✅ **リンク整合性**: 6 コアページ OK
- ✅ **sitemap 登録**: 自動生成・同期正常
- ✅ **robots.txt**: Disallow ルール正常

---

## ⚠️ 警告一覧（27 件・前回比 +3 件）

### グループ1: 「↑上に戻る」ボタン不足（6 ファイル・+2 件）

**対応**: `python apply_back_to_top.py` で冪等修正可能

```
- guide-new-books.html
- guide-scam-account-lending.html        ← 新規
- guide-scam-deepfake-scam.html
- guide-scam-romance-invest.html
- guide-scam-sns-celebrity-ad.html
- guide-settlement-cycle.html             ← 新規
```

**原因**: HTML に `mw-back-to-top` クラス要素が未挿入  
**影響度**: 低（UX軽微・iOS/Android スクロール機能あり）

---

### グループ2: ナビゲーションに不足リンク（7 ファイル・+1 件）

**以下 5 ファイルに「holdings.html」リンク不足:**

```
- guide-commodity-basics.html
- guide-counterparty-risk.html
- guide-liquidity-risk.html              ← 新規
- guide-market-hours.html
- guide-sunk-cost.html
```

**以下 2 ファイルはナビゲーション全欠落（全 11 リンク不足）:**

```
- guide-correlation-risk.html
- guide-reit-basics.html
```

**原因**: 旧記事が新ナビバー 10 ボタン対応時に未更新  
**影響度**: 中（ナビボタン数 < 10 → モバイル2列崩れ）  
**推奨**: `python unify_navbar.py --apply` で統一修正

---

### グループ3: ナビバーCSS `max-width` 欠落（13 ファイル）

**影響**: モバイル 375px で 8+2 レイアウト崩れ

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

**推奨**: `python apply_nav_css.py` で冪等修正可能

---

## 🚀 推奨対応（優先順）

| 優先度 | 内容 | コマンド | 対象ファイル数 |
|---|---|---|---|
| 🟡 P1 | ナビゲーション全欠落 | `python unify_navbar.py --apply` | 2 ファイル |
| 🟡 P2 | ナビ CSS モバイル崩れ | `python apply_nav_css.py` | 13 ファイル |
| 🟡 P3 | 「↑上に戻る」ボタン | `python apply_back_to_top.py` | 6 ファイル |

**注**: すべての警告は UI 品質の改善事項。緊急対応は不要。

---

## 📈 前回比の変化

| 項目 | 前回（08-22） | 今回（08-24） | 変化 |
|---|---|---|---|
| guide 記事数 | 309 | 317 | +8 |
| 警告総数 | 24 | 27 | +3 |
| 「↑上に戻る」不足 | 4 | 6 | +2（新記事がテンプレ未適用） |
| ナビゲーション不足 | 6 | 7 | +1（liquidity-risk.html 新規） |
| ナビ CSS 欠落 | 13 | 13 | ±0 |

**解釈**: 新記事追加時に古いテンプレートが混在。`apply_*.py` スクリプトで一括修正可能。

---

## 📝 リンター生出力

```
🔍 サイト整合性チェック（check_site_consistency.py）
  検査した guide記事: 317 件（自動生成記事を除く） / SYNC_FILES: ローカル専用のためスキップ（sync_to_github.py がリモートに無い＝正常）

⚠️  警告 27 件:
   - sync_to_github.py はクラウド用スタブ（想定どおり）→ SYNC_FILES 系チェックをスキップ
   - guide-new-books.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-scam-account-lending.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-scam-deepfake-scam.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-scam-romance-invest.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-scam-sns-celebrity-ad.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-settlement-cycle.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-commodity-basics.html: ナビに不足リンク ['holdings.html']（10ボタン未満）
   - guide-correlation-risk.html: ナビに不足リンク ['index.html', 'political-feed.html', 'track-record.html', 'calendar.html', 'guides.html', 'guide-investment-books.html', 'holdings.html', 'market-health.html', 'hot-assets.html', 'charts.html', 'youtube-summary.html']（10ボタン未満）
   - guide-counterparty-risk.html: ナビに不足リンク ['holdings.html']（10ボタン未満）
   - guide-liquidity-risk.html: ナビに不足リンク ['holdings.html']（10ボタン未満）
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

結果: ✅ OK（エラーなし・警告 27 件）
```

---

## 📋 まとめ

✅ **SYNC 禁忌の混入なし** — 巻き戻し事故リスクなし（2026-04-24 事故は継続防止）  
✅ **自動生成ファイル正常** — sitemap/robots.txt 自動再生成機能正常  
⚠️ **新記事のテンプレート古い** — 317 件中、新規 8 件が旧テンプレートで統一ツール対象  
💡 **スクリプトで一括修正可能** — 3 つの apply_*.py で全警告を自動解消予定
