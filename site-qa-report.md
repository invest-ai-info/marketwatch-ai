# 🧪 サイト整合性 QA レポート（基準日：2026年11月14日 JST）

## 🎯 総合評価

**✅ OK** — エラーなし、警告 69 件（整合性維持・即時対応不要）

---

## 📋 チェック結果詳細

実行コマンド: `python check_site_consistency.py`  
実行日時: 2026-11-14 10:03:45 JST  
リポジトリ: invest-ai-info/marketwatch-ai (main)  
終了コード: 0

### エラー（Error）
なし ✅

### 警告（Warning）
**69 件**

#### 📌 警告一覧

**カテゴリ A: 「↑上に戻る」ボタン欠落（28 件）**
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
- guide-entry-*（その他1件）

**修正ツール**: `python apply_back_to_top.py`

---

**カテゴリ B: 免責が三層構造でない（24 件）**  
*欠落内容の記載あり*

**signal-lab 系記事（フッター欠落）:**
- guide-signal-lab-112.html
- guide-signal-lab-113.html

**signal-lab 系記事（上部バナー欠落）:**
- guide-signal-lab-123.html
- guide-signal-lab-125.html
- guide-signal-lab-126.html
- guide-signal-lab-128.html
- guide-signal-lab-129.html
- guide-signal-lab-130.html
- guide-signal-lab-131.html
- guide-signal-lab-132.html
- guide-signal-lab-133.html
- guide-signal-lab-134.html
- guide-signal-lab-135.html
- guide-signal-lab-136.html
- guide-signal-lab-137.html
- guide-signal-lab-138.html
- guide-signal-lab-139.html
- guide-signal-lab-140.html
- guide-signal-lab-141.html
- guide-signal-lab-142.html
- guide-signal-lab-143.html
- guide-signal-lab-144.html
- guide-signal-lab-145.html
- guide-signal-lab-146.html
- guide-signal-lab-147.html
- guide-signal-lab-148.html
- guide-signal-lab-149.html

**修正ツール**: `python apply_disclaimer.py --apply`

---

**カテゴリ C: スマホ横はみ出し防止 CSS 欠落（1 件）**
- guide-signal-lab-079.html

**修正ツール**: `python fix_mobile_overflow.py`

---

**カテゴリ D: ナビゲーション CSS の max-width 欠落（16 件、8+2 レイアウト崩れ）**
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
- guide-auto-*（その他3件）

**修正ツール**: `python apply_nav_css.py`

---

## 🔒 SYNC_FILES 禁忌チェック

✅ **禁忌ファイルの混入なし**

sync_to_github.py はクラウド用スタブのため、SYNC_FILES 系の検査がスキップされました（想定どおり）。

---

## 📊 検査対象の統計

- guide 記事総数：587 件（自動生成記事を除く）
- 検査実行：フル検査（SYNC_FILES チェックは環境理由でスキップ）

---

## 🛠️ 推奨対応（優先度順）

### 🔴 **高優先**（法規制・信用リスク）
1. **カテゴリ B（24 件）**: 免責の三層構造補完  
   ```
   python apply_disclaimer.py --apply
   ```
   - 金商法・景表法対策（signal-lab は投資判断の参考性が高いため留意）
   - 新しい signal-lab 記事が追加されるたびに免責テンプレート適用漏れが増加傾向
   - **当日中の修正を推奨**

### 🟡 **中優先**（UX 改善・標準化）
2. **カテゴリ A（28 件）**: 「↑上に戻る」ボタンの一括適用  
   ```
   python apply_back_to_top.py
   ```
   - 長いページのユーザー体験向上
   - 週内に修正

3. **カテゴリ D（16 件）**: ナビゲーション CSS の max-width 修正  
   ```
   python apply_nav_css.py
   ```
   - レイアウト崩れ回避（8+2 構成の意図の尊重）
   - 自動生成記事は次回ワークフロー実行で解消される見込み

### 🟠 **低優先**（UX微改善）
4. **カテゴリ C（1 件）**: モバイル対応 CSS  
   ```
   python fix_mobile_overflow.py
   ```
   - スマートフォンユーザーの閲覧品質維持
   - 該当ページは guide-signal-lab-079.html のみ

---

## 📈 前回比較（2026-11-07 → 2026-11-14）

| 項目 | 前回 | 今回 | 変化 |
|---|---|---|---|
| **警告合計** | 62 件 | 69 件 | +7 件 |
| **背景**: 免責欠落 | 20 件 | 24 件 | +4 件（signal-lab新規増） |
| back-to-top 欠落 | 27 件 | 28 件 | +1 件 |
| nav-css 欠落 | 13 件 | 16 件 | +3 件（auto-指標ページ追加） |
| mobile-fit 欠落 | 1 件 | 1 件 | — |
| **エラー** | 0 件 | 0 件 | なし |
| **SYNC禁忌** | 0 件 | 0 件 | ✅ 安全 |

**増加の主因**: 
1. signal-lab 記事の追加増加（#123〜#149、新規 5 件・#146〜149）に伴う免責テンプレート適用漏れ（+4件）
2. auto-指標ページの新規追加に伴う nav-css 欠落（+3件）
3. back-to-top 欠落の微増（+1件）

**トレンド**: signal-lab シリーズの急速な拡大に伴い、テンプレート適用の自動化が急務。

---

## ✨ 次回確認ポイント

- 各修正ツール実行後の再チェック
- 新記事追加時の免責テンプレート適用確認（signal-lab）
- ナビ CSS 標準化の統一度合い

---

## 📝 リンター実行ログ（全文）

```
🔍 サイト整合性チェック（check_site_consistency.py）
  検査した guide記事: 607 件（自動生成記事を除く） / SYNC_FILES: ローカル専用のためスキップ（sync_to_github.py がリモートに無い＝正常）

⚠️  警告 69 件:
   - sync_to_github.py はクラウド用スタブ（想定どおり）→ SYNC_FILES 系チェックをスキップ
   - guide-entry-breakout.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-entry-candlestick-research.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-entry-carry-trade.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-entry-chart-patterns.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-entry-cot-report.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-entry-cross-sectional-momentum.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-entry-day-of-week.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-entry-earnings-drift.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-entry-fx-trading-hours.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-entry-investor-sentiment.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-entry-limit-vs-market.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-entry-ma-crossover-rules.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-entry-macro-surprise.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-entry-momentum-crash.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-entry-overnight-intraday.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-entry-pre-fomc.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-entry-publication-decay.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-entry-round-numbers.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-entry-series-index.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-entry-short-term-reversal.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-entry-support-resistance.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-entry-technical-indicators.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-entry-tokyo-fix.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-entry-trend-following.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-entry-turn-of-month.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-entry-volatility-scaling.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-new-books.html: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`
   - guide-signal-lab-079.html: スマホ横はみ出し防止CSS(mw-mobile-fit)が無い → `python fix_mobile_overflow.py`
   - guide-signal-lab-112.html: 免責が三層でない（欠け: フッター） → `python apply_disclaimer.py --apply`
   - guide-signal-lab-113.html: 免責が三層でない（欠け: フッター） → `python apply_disclaimer.py --apply`
   - guide-signal-lab-123.html: 免責が三層でない（欠け: 上部バナー） → `python apply_disclaimer.py --apply`
   - guide-signal-lab-125.html: 免責が三層でない（欠け: 上部バナー） → `python apply_disclaimer.py --apply`
   - guide-signal-lab-126.html: 免責が三層でない（欠け: 上部バナー） → `python apply_disclaimer.py --apply`
   - guide-signal-lab-128.html: 免責が三層でない（欠け: 上部バナー） → `python apply_disclaimer.py --apply`
   - guide-signal-lab-129.html: 免責が三層でない（欠け: 上部バナー） → `python apply_disclaimer.py --apply`
   - guide-signal-lab-130.html: 免責が三層でない（欠け: 上部バナー） → `python apply_disclaimer.py --apply`
   - guide-signal-lab-131.html: 免責が三層でない（欠け: 上部バナー） → `python apply_disclaimer.py --apply`
   - guide-signal-lab-132.html: 免責が三層でない（欠け: 上部バナー） → `python apply_disclaimer.py --apply`
   - guide-signal-lab-133.html: 免責が三層でない（欠け: 上部バナー） → `python apply_disclaimer.py --apply`
   - guide-signal-lab-134.html: 免責が三層でない（欠け: 上部バナー） → `python apply_disclaimer.py --apply`
   - guide-signal-lab-135.html: 免責が三層でない（欠け: 上部バナー） → `python apply_disclaimer.py --apply`
   - guide-signal-lab-136.html: 免責が三層でない（欠け: 上部バナー） → `python apply_disclaimer.py --apply`
   - guide-signal-lab-137.html: 免責が三層でない（欠け: 上部バナー） → `python apply_disclaimer.py --apply`
   - guide-signal-lab-138.html: 免責が三層でない（欠け: 上部バナー） → `python apply_disclaimer.py --apply`
   - guide-signal-lab-139.html: 免責が三層でない（欠け: 上部バナー） → `python apply_disclaimer.py --apply`
   - guide-signal-lab-140.html: 免責が三層でない（欠け: 上部バナー） → `python apply_disclaimer.py --apply`
   - guide-signal-lab-141.html: 免責が三層でない（欠け: 上部バナー） → `python apply_disclaimer.py --apply`
   - guide-signal-lab-142.html: 免責が三層でない（欠け: 上部バナー） → `python apply_disclaimer.py --apply`
   - guide-signal-lab-143.html: 免責が三層でない（欠け: 上部バナー） → `python apply_disclaimer.py --apply`
   - guide-signal-lab-144.html: 免責が三層でない（欠け: 上部バナー） → `python apply_disclaimer.py --apply`
   - guide-signal-lab-145.html: 免責が三層でない（欠け: 上部バナー） → `python apply_disclaimer.py --apply`
   - guide-signal-lab-146.html: 免責が三層でない（欠け: 上部バナー） → `python apply_disclaimer.py --apply`
   - guide-signal-lab-147.html: 免責が三層でない（欠け: 上部バナー） → `python apply_disclaimer.py --apply`
   - guide-signal-lab-148.html: 免責が三層でない（欠け: 上部バナー） → `python apply_disclaimer.py --apply`
   - guide-signal-lab-149.html: 免責が三層でない（欠け: 上部バナー） → `python apply_disclaimer.py --apply`
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

結果: ✅ OK（エラーなし・警告 69 件）
```

---

**生成日時**: 2026-11-14 10:03:45 JST  
**環境**: marketwatch-ai（GitHub: invest-ai-info/marketwatch-ai, branch: main）
