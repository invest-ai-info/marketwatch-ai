# 🧪 サイト整合性 QA レポート

**基準日**: 2026-11-21 (JST)  
**チェック実行時刻**: 2026-11-21 10:03 JST

---

## 📊 チェック結果

✅ **OK**  
**エラー**: 0 件  
**警告**: 76 件

---

## ✅ 合格項目

- ✔️ SYNC_FILES 禁忌混入: **なし**
- ✔️ 自動生成ファイル: **整合性 OK**
- ✔️ リンク検査: **正常**

---

## ⚠️ 警告詳細

### 1. 「↑上に戻る」ボタン欠落（28 件）
推奨: `python apply_back_to_top.py`

### 2. 免責バナー不完全（40 件）
🔴 **最優先**: 金商法コンプラ対応  
推奨: `python apply_disclaimer.py --apply`

### 3. ナビゲーション CSS 不完全（8 件）
推奨: `python apply_nav_css.py`

### 4. スマホ CSS 欠落（1 件）
推奨: `python fix_mobile_overflow.py`

---

## 📌 優先度別対応

| 優先度 | 分類 | 件数 | ツール |
|---|---|---|---|
| 🔴 高 | 免責バナー | 40 | `apply_disclaimer.py --apply` |
| 🟡 中 | ナビ CSS | 8 | `apply_nav_css.py` |
| 🟡 中 | ボタン | 28 | `apply_back_to_top.py` |
| 🟢 低 | スマホ CSS | 1 | `fix_mobile_overflow.py` |

---

## ✅ まとめ

**結果**: OK  
**最優先**: 免責バナー 40 件（金商法）  
**推奨**: 優先度順に自動修正ツール実行
