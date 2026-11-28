# 🧪 サイト整合性 QA レポート

**基準日**: 2026-11-28 (JST)  
**チェック実行時刻**: 2026-11-28 01:03:29 JST

---

## 📊 チェック結果

✅ **OK**  
**エラー**: 0 件  
**警告**: 83 件

---

## ✅ 合格項目

- ✔️ SYNC_FILES 禁忌混入: **なし**（sync_to_github.py はクラウド用スタブ・想定通り）
- ✔️ 自動生成ファイル: **整合性 OK**
- ✔️ リンク検査: **正常**
- ✔️ エラーレベル（即修正が必要な問題）: **0 件**

---

## ⚠️ 警告詳細（83 件）

### 1. 免責が三層でない（上部バナー欠落）（48 件）
🔴 **最優先**: 金商法コンプラ対応  
対象: `guide-signal-lab-{112,113,123-162}.html`  
推奨: `python apply_disclaimer.py --apply`

### 2. 「↑上に戻る」ボタン欠落（28 件）
対象: `guide-entry-*.html`（エントリーシリーズ）、`guide-new-books.html`  
推奨: `python apply_back_to_top.py`

### 3. ナビゲーション CSS max-width 欠落（8 件）
対象: 自動生成記事（`guide-auto-*`, `guide-weekly-*` シリーズ）  
推奨: `python apply_nav_css.py`

### 4. スマホ横はみ出し防止 CSS 欠落（1 件）
対象: `guide-signal-lab-079.html`  
推奨: `python fix_mobile_overflow.py`

---

## 📌 優先度別対応

| 優先度 | 分類 | 件数 | ツール |
|---|---|---|---|
| 🔴 高 | 免責バナー（金商法） | 48 | `apply_disclaimer.py --apply` |
| 🟡 中 | ナビ CSS | 8 | `apply_nav_css.py` |
| 🟡 中 | ボタン | 28 | `apply_back_to_top.py` |
| 🟢 低 | スマホ CSS | 1 | `fix_mobile_overflow.py` |

---

## 📋 推奨実行順序

1. **`python apply_disclaimer.py --apply`** ← 48 件（法的要件）
2. **`python apply_back_to_top.py`** ← 28 件（UX）
3. **`python apply_nav_css.py`** ← 8 件（見た目統一）
4. **`python fix_mobile_overflow.py`** ← 1 件（モバイル対応）

---

## ✅ まとめ

**結果**: OK（エラーなし）  
**警告件数**: 83 件（前週 76 件 → 今週 83 件 / +7件）  
**最優先対応**: 免責バナー 48 件（金商法コンプラ）  
**推奨**: 自動修正ツールで順次対応。すべて機械修正可能な形式上の問題
