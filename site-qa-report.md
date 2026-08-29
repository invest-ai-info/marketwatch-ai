# 🧪 サイト整合性 QA レポート

**基準日**: 2026-08-29（JST: 10:07:36）  
**実行時刻**: 2026-08-29 01:07:36 UTC  
**前回**: 2026-08-24（guide 317件・警告 27件）

---

## 📊 結果サマリー

| 項目 | ステータス |
|------|-----------|
| エラー | ✅ **0 件** |
| 警告 | ⚠️ **30 件** |
| 検査対象 guide 記事 | **331 件**（+14 件）|
| 総合判定 | **✅ OK** |

---

## ✅ OK 判定（致命的問題なし）

- ✅ **SYNC 禁忌ファイル**: 検出なし（巻き戻し事故リスク無し）
- ✅ **免責表記（kinsho-v1）**: 正常
- ✅ **ナビバー基本構造**: 10 ボタン標準
- ✅ **リンク整合性**: OK
- ✅ **sitemap 登録**: 自動生成・同期正常
- ✅ **robots.txt**: Disallow ルール正常

---

## ⚠️ 警告一覧（30 件・前回比 +3 件）

### グループ1: 「↑上に戻る」ボタン不足（6 ファイル）

**対応**: `python apply_back_to_top.py` で冪等修正可能

```
- guide-new-books.html
- guide-scam-account-lending.html
- guide-scam-deepfake-scam.html
- guide-scam-romance-invest.html
- guide-scam-sns-celebrity-ad.html
- guide-settlement-cycle.html
```

**影響度**: 低

---

### グループ2: ナビゲーション不足（8 ファイル）

**6件に「holdings.html」リンク不足:**

```
- guide-commodity-basics.html
- guide-counterparty-risk.html
- guide-liquidity-risk.html
- guide-market-hours.html
- guide-sunk-cost.html
- guide-trade-journal.html
```

**3件はナビゲーション全欠落:**

```
- guide-correlation-risk.html
- guide-regret-aversion.html
- guide-reit-basics.html
```

**推奨**: `python unify_navbar.py --apply` で統一修正  
**影響度**: 中

---

### グループ3: ナビバーCSS `max-width` 欠落（13 ファイル）

自動生成記事（guide-auto-* / guide-weekly-*）でナビ CSS に max-width が欠落。モバイル 8+2 レイアウト崩れの原因。

**推奨**: `python apply_nav_css.py` で冪等修正可能  
**影響度**: 中

---

### グループ4: モバイル横はみ出し防止CSS欠落（1 ファイル）

```
- guide-signal-lab-079.html
```

**推奨**: `python fix_mobile_overflow.py` で修正可能  
**影響度**: 低

---

## 🚀 推奨対応

| 優先度 | 内容 | コマンド | 対象数 |
|---|---|---|---|
| 🟡 P1 | ナビ全欠落 | `python unify_navbar.py --apply` | 2 |
| 🟡 P2 | ナビ CSS | `python apply_nav_css.py` | 13 |
| 🟡 P3 | 上へボタン | `python apply_back_to_top.py` | 6 |
| 🟡 P4 | モバイル | `python fix_mobile_overflow.py` | 1 |

**注**: すべて UI 品質の改善事項。緊急対応不要。

---

## 📈 前回比

| 項目 | 前回（08-24） | 今回（08-29） | 変化 |
|---|---|---|---|
| guide 記事数 | 317 | 331 | +14 |
| 警告総数 | 27 | 30 | +3 |

**解釈**: 新記事追加（+14件）に伴い警告も +3件。スクリプトで一括修正可能。

---

## 📝 チェック結果

```
🔍 サイト整合性チェック（check_site_consistency.py）
検査した guide記事: 331 件

⚠️ 警告 30 件
✅ 結果: OK（エラーなし）
```

---

## 📋 まとめ

✅ **SYNC 禁忌の混入なし** — 巻き戻し事故リスクなし  
✅ **自動生成ファイル正常** — sitemap/robots.txt 正常  
⚠️ **新記事のテンプレート古い** — 331 件中、新規 14 件が旧テンプレート  
💡 **スクリプトで一括修正可能** — 4 つの apply_*.py で全警告を自動解消  
📈 **記事成長継続中** — 1 週間で +14 件の新規記事追加、品質維持レベル良好
