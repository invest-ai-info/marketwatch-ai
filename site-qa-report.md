# 🧪 サイト整合性 QA レポート（基準日 2026-10-31 10:03 JST）

## 📋 チェック結果

| 項目 | 状態 |
|---|---|
| **総合判定** | ✅ **OK** |
| **エラー** | 0 件 |
| **警告** | 55 件 |
| **SYNC禁忌混入** | ❌ なし（安全） |
| **リンク切れ** | ❌ なし |
| **免責漏れ** | ⚠️ あり（16件） |

---

## ✅ 良好な検査項目

- **SYNC_FILES の混入**: なし（クラウド環境・sync_to_github.py がスタブ状態のため正常）
- **リンク一貫性**: 全記事チェック済・リンク切れなし
- **サイトナビゲーション**: 10ボタン構成・連番一貫性OK
- **自動生成スクリプト**: 8本が正常に機能

---

## ⚠️ 警告一覧（55件）

### 1️⃣ 「↑上に戻る」ボタン欠落（27件）

以下の記事に `mw-back-to-top` クラスが未搭載。`python apply_back_to_top.py` で冪等修正可能：

```
- guide-entry-breakout.html
- guide-entry-candlestick-research.html
- guide-entry-carry-trade.html
- guide-entry-chart-patterns.html
- guide-entry-cot-report.html
- guide-entry-cross-sectional-momentum.html
- guide-entry-day-of-week.html
- guide-entry-earnings-drift.html
- guide-entry-fx-trading-hours.html
- guide-entry-investor-sentiment.html
- guide-entry-limit-vs-market.html
- guide-entry-ma-crossover-rules.html
- guide-entry-macro-surprise.html
- guide-entry-momentum-crash.html
- guide-entry-overnight-intraday.html
- guide-entry-pre-fomc.html
- guide-entry-publication-decay.html
- guide-entry-round-numbers.html
- guide-entry-series-index.html
- guide-entry-short-term-reversal.html
- guide-entry-support-resistance.html
- guide-entry-technical-indicators.html
- guide-entry-tokyo-fix.html
- guide-entry-trend-following.html
- guide-entry-turn-of-month.html
- guide-entry-volatility-scaling.html
- guide-new-books.html
```

**対応**: `python apply_back_to_top.py` 実行で自動修正。

---

### 2️⃣ 免責が三層でない（16件）

signal-lab系の記事で、免責テンプレートが不完全（欠け部分: 上部バナーまたはフッター）。`python apply_disclaimer.py --apply` で冪等修正：

```
- guide-signal-lab-112.html: フッター免責欠落
- guide-signal-lab-113.html: フッター免責欠落
- guide-signal-lab-123.html: 上部バナー免責欠落
- guide-signal-lab-125.html: 上部バナー免責欠落
- guide-signal-lab-126.html: 上部バナー免責欠落
- guide-signal-lab-128.html: 上部バナー免責欠落
- guide-signal-lab-129.html: 上部バナー免責欠落
- guide-signal-lab-130.html: 上部バナー免責欠落
- guide-signal-lab-131.html: 上部バナー免責欠落
- guide-signal-lab-132.html: 上部バナー免責欠落
- guide-signal-lab-133.html: 上部バナー免責欠落
- guide-signal-lab-134.html: 上部バナー免責欠落
- guide-signal-lab-135.html: 上部バナー免責欠落
```

**対応**: 優先度は**中**。既存記事の合法性に直結するため、近いうちに修正。`python apply_disclaimer.py --apply` で自動修正可能。

---

### 3️⃣ ナビCSSの max-width 欠落（11件）

自動生成記事で、ナビゲーション CSS に `max-width` 属性が欠落し、パソコン幅で 8+2 カラムレイアウトが崩れる可能性。`python apply_nav_css.py` で修正：

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

**対応**: 優先度は**低〜中**。既に読者向けに提供中の記事だが、パソコン幅での見栄えに影響。`python apply_nav_css.py` で自動修正。

---

### 4️⃣ スマホ横はみ出し防止CSS欠落（1件）

```
- guide-signal-lab-079.html: mw-mobile-fit クラス欠落
```

**対応**: `python fix_mobile_overflow.py` で修正。モバイル端末での横スクロール発生の可能性あり。

---

## 📌 推奨対応スケジュール

| 優先度 | 作業 | 推定時間 |
|---|---|---|
| 🔴 **高** | SYNC禁忌混入チェック | ✅ なし |
| 🟡 **中** | 免責三層修正（16件）+ ナビCSS修正（11件） | 15分 |
| 🟢 **低** | 「↑上に戻る」ボタン追加（27件）+ モバイル横はみ出し対応（1件） | 20分 |

---

## ✅ 次回チェック予定

- **予定日**: 2026-11-07（毎週木曜0:00 UTC / 09:00 JST）
- **自動実行**: GitHub Actions `site-qa-lint` routine

---

**生成日時**: 2026-10-31 10:03:55 JST  
**チェックツール**: `check_site_consistency.py`
