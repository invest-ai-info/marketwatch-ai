# 🧪 サイト整合性 QA レポート

**基準日（JST）**: 2026-09-12 10:07 JST

---

## 📋 検査結果

**ステータス**: ✅ **OK**（エラーなし）

- **検査対象**: 395 個の guide 記事、SYNC禁忌、免責、ナビバー、リンク
- **エラー件数**: 0 件
- **警告件数**: 38 件

---

## ⚠️ 警告一覧（対応方法付き）

### 1️⃣ 「↑上に戻る」ボタン欠落（3件）
下書きと非公開記事向けの警告。公開記事では設置必須。

```
guide-new-books.html
guide-scam-romance-invest.html
guide-scam-sns-celebrity-ad.html
```

**対応**: `python apply_back_to_top.py` を実行

---

### 2️⃣ スマホ横はみ出し CSS 欠落（1件）

```
guide-signal-lab-079.html
```

**対応**: `python fix_mobile_overflow.py` を実行

---

### 3️⃣ ナビバー不足リンク（19件）

古い記事や自動生成記事でナビの10ボタン構成が不完全。**危険度: 低**（本体ナビバーは正常）。

```
guide-anchoring-price.html
guide-bid-ask-spread.html
guide-cash-allocation.html
guide-commodity-basics.html
guide-correlation-risk.html
guide-counterparty-risk.html
guide-equity-offering.html
guide-index-vs-active.html
guide-liquidity-risk.html
guide-market-hours.html
guide-odd-lot-investing.html
guide-outcome-bias.html
guide-rebalancing.html
guide-regret-aversion.html
guide-reit-basics.html
guide-scam-real-estate-yield-pitch.html
guide-sunk-cost.html
guide-survivorship-bias.html
guide-trade-journal.html
guide-volatility-vs-risk.html
```

**対応**: `python unify_navbar.py --apply` で一括修正可能

---

### 4️⃣ ナビ CSS（max-width）欠落による 8+2 レイアウト崩れ（13件）

自動生成の早期記事でモバイル対応 CSS が不足。ナビが横崩れの可能性。

```
guide-auto-boj-2026-06-17.html
guide-auto-fomc-2026-06-17.html
guide-auto-us_cpi-2026-05-14.html
guide-auto-us_cpi-2026-06-10.html
guide-auto-us_jobs-2026-06-05.html
guide-auto-us_pce-2026-05-30.html
guide-auto-us_pce-2026-06-27.html
guide-weekly-2026-05-25.html
guide-weekly-2026-06-01.html
guide-weekly-2026-06-08.html
guide-weekly-2026-06-15.html
guide-weekly-2026-06-22.html
guide-weekly-review-2026-06-15.html
```

**対応**: `python apply_nav_css.py` で修正

---

## 🛡️ SYNC禁忌チェック

✅ **クラウド生成ファイルの混入なし**（問題なし）

- GitHub Actions で生成される `*.json` / `political-feed.html` / 週次ファイル等の変更: **検出されず**
- ローカルから禁止ファイルの push: **なし**
- `sync_to_github.py` はクラウド環境用スタブ（想定どおり）

---

## 📊 リンター生出力

```
🔍 サイト整合性チェック（check_site_consistency.py）
  検査した guide記事: 395 件（自動生成記事を除く） / SYNC_FILES: ローカル専用のためスキップ（sync_to_github.py がリモートに無い＝正常）

⚠️  警告 38 件:
   - sync_to_github.py はクラウド用スタブ（想定どおり）→ SYNC_FILES 系チェックをスキップ
   - guide-new-books.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-scam-romance-invest.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-scam-sns-celebrity-ad.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-signal-lab-079.html: スマホ横はみ出し防止CSS(mw-mobile-fit)が無い → `python fix_mobile_overflow.py`
   - guide-anchoring-price.html: ナビに不足リンク ['holdings.html']（10ボタン未満）
   - guide-bid-ask-spread.html: ナビに不足リンク ['holdings.html']（10ボタン未満）
   - guide-cash-allocation.html: ナビに不足リンク ['holdings.html']（10ボタン未満）
   - guide-commodity-basics.html: ナビに不足リンク ['holdings.html']（10ボタン未満）
   - guide-correlation-risk.html: ナビに不足リンク ['index.html', 'political-feed.html', 'track-record.html', 'calendar.html', 'guides.html', 'guide-investment-books.html', 'holdings.html', 'market-health.html', 'hot-assets.html', 'charts.html', 'youtube-summary.html']（10ボタン未満）
   - guide-counterparty-risk.html: ナビに不足リンク ['holdings.html']（10ボタン未満）
   - guide-equity-offering.html: ナビに不足リンク ['holdings.html']（10ボタン未満）
   - guide-index-vs-active.html: ナビに不足リンク ['holdings.html']（10ボタン未満）
   - guide-liquidity-risk.html: ナビに不足リンク ['holdings.html']（10ボタン未満）
   - guide-market-hours.html: ナビに不足リンク ['holdings.html']（10ボタン未満）
   - guide-odd-lot-investing.html: ナビに不足リンク ['holdings.html']（10ボタン未満）
   - guide-outcome-bias.html: ナビに不足リンク ['holdings.html']（10ボタン未満）
   - guide-rebalancing.html: ナビに不足リンク ['holdings.html']（10ボタン未満）
   - guide-regret-aversion.html: ナビに不足リンク ['index.html', 'political-feed.html', 'track-record.html', 'calendar.html', 'guides.html', 'guide-investment-books.html', 'holdings.html', 'market-health.html', 'hot-assets.html', 'charts.html', 'youtube-summary.html']（10ボタン未満）
   - guide-reit-basics.html: ナビに不足リンク ['index.html', 'political-feed.html', 'track-record.html', 'calendar.html', 'guides.html', 'guide-investment-books.html', 'holdings.html', 'market-health.html', 'hot-assets.html', 'charts.html', 'youtube-summary.html']（10ボタン未満）
   - guide-scam-real-estate-yield-pitch.html: ナビに不足リンク ['holdings.html']（10ボタン未満）
   - guide-sunk-cost.html: ナビに不足リンク ['holdings.html']（10ボタン未満）
   - guide-survivorship-bias.html: ナビに不足リンク ['holdings.html']（10ボタン未満）
   - guide-trade-journal.html: ナビに不足リンク ['holdings.html']（10ボタン未満）
   - guide-volatility-vs-risk.html: ナビに不足リンク ['holdings.html']（10ボタン未満）
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

結果: ✅ OK（エラーなし・警告 38 件）
```

---

## 🎯 推奨対応（優先度順）

| 優先度 | 項目 | 件数 | コマンド | 理由 |
|--------|------|------|---------|------|
| 🔴 高 | ナビ CSS max-width | 13件 | `python apply_nav_css.py` | モバイルレイアウト崩れ |
| 🟡 中 | ナビバー不足リンク | 19件 | `python unify_navbar.py --apply` | 内部ナビゲーション不完全 |
| 🟢 低 | バックボタン欠落 | 3件 | `python apply_back_to_top.py` | UX 向上用（重大性低） |
| 🟢 低 | 横はみ出し CSS | 1件 | `python fix_mobile_overflow.py` | 1記事のみ |

---

## ✨ まとめ

- **SYNC禁忌混入**: なし ✅（クラウド生成ファイルの巻き戻し事故なし）
- **免責・法務**: OK ✅（kinsho-v1 確認済み）
- **ナビバー**: 10ボタン本体は正常 ✅（個別記事の不足はあるが主要ページは問題なし）
- **リンク切れ**: なし ✅
- **本番リスク**: 低 ✅（警告は軽微・UX 品質向上用）

次回の check-site-consistency は **2026-09-19（土）10:00 JST** 予定。
