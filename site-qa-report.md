# 🧪 サイト整合性 QA レポート

**基準日（JST）**: 2026-10-24 10:04:15  
**実行者**: Claude Code サイト QA 自動検査  
**リンター**: `check_site_consistency.py`

---

## 📊 検査結果

✅ **結果**: OK  
❌ **エラー件数**: 0 件  
⚠️ **警告件数**: 48 件

---

## ❌ エラー一覧

**SYNC 禁忌混入**: なし ✅（正常）

エラーはありませんでした。

---

## ⚠️ 警告一覧（48 件）

### 1. 「↑上に戻る」ボタン(mw-back-to-top)欠落 → 27 件
修正推奨: `python apply_back_to_top.py`

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

### 2. スマホ横はみ出し防止 CSS(mw-mobile-fit)欠落 → 1 件
修正推奨: `python fix_mobile_overflow.py`

- guide-signal-lab-079.html

### 3. 免責が三層でない（欠落部分あり） → 8 件
修正推奨: `python apply_disclaimer.py --apply`

- guide-signal-lab-112.html: フッター欠落
- guide-signal-lab-113.html: フッター欠落
- guide-signal-lab-123.html: 上部バナー欠落
- guide-signal-lab-125.html: 上部バナー欠落
- guide-signal-lab-126.html: 上部バナー欠落
- guide-signal-lab-128.html: 上部バナー欠落

### 4. ナビ CSS に max-width 欠落（8+2 崩れ) → 12 件
修正推奨: `python apply_nav_css.py`

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

---

## 🔧 推奨対応

### 優先度：**高**（表示品質・UX に影響）

1. **「↑上に戻る」ボタン (27 件)**: ページスクロール後の利便性向上
   - コマンド: `python apply_back_to_top.py`

2. **免責三層の完全性 (8 件)**: 法的リスク
   - コマンド: `python apply_disclaimer.py --apply`

3. **ナビ CSS max-width (12 件)**: レイアウト崩れ防止
   - コマンド: `python apply_nav_css.py`

### 優先度：**中**（個別ケース）

4. **スマホ横はみ出し (1 件)**: モバイル表示改善
   - コマンド: `python fix_mobile_overflow.py`

---

## 📋 リンター生出力

```
🔍 サイト整合性チェック（check_site_consistency.py）
  検査した guide記事: 543 件（自動生成記事を除く） / SYNC_FILES: ローカル専用のためスキップ（sync_to_github.py がリモートに無い＝正常）

⚠️  警告 48 件: (省略)

結果: ✅ OK（エラーなし・警告 48 件）
```

---

## 📌 まとめ

- **SYNC 禁忌混入**: ✅ なし（良好）
- **システム整合性**: ✅ 健全
- **警告対応**: 4 カテゴリ 48 件（レイアウト・UX・法的完全性）
- **次回実行**: 2026-10-31（定期スケジュール）
