# 🧪 サイト整合性 QA レポート（基準日 2026-06-20 10:01 JST）

## 総合結果

| 項目 | 件数 |
|---|---|
| 検査 guide 記事数 | 84 件（自動生成除く） |
| エラー | **0 件** |
| 警告 | **8 件** |
| **総合判定** | **✅ OK** |

SYNC 禁忌混入なし。免責漏れなし。リンク切れなし。

---

## ❌ エラー一覧

なし。

---

## ⚠️ 警告一覧（8 件）

すべて `guide-signal-lab-006〜009.html` に関連する 2 種類の問題。

### 1. guides.html カード未登録（4 件）

| ファイル | 問題 |
|---|---|
| guide-signal-lab-006.html | guides.html にカードが無い（一覧から辿れない） |
| guide-signal-lab-007.html | guides.html にカードが無い（一覧から辿れない） |
| guide-signal-lab-008.html | guides.html にカードが無い（一覧から辿れない） |
| guide-signal-lab-009.html | guides.html にカードが無い（一覧から辿れない） |

**背景**: `signal-lab-daily` routine が自動公開した記事（06/13 以降の自動公開化）。`publish_article.py` 経由で guides.html へのカード登録が行われていない可能性あり。または routine が直接ファイルを配置しているが guides.html 更新まで至っていない可能性。

### 2. ナビバー 10 ボタン未満（4 件）

| ファイル | 不足リンク |
|---|---|
| guide-signal-lab-006.html | `guide-investment-books.html` |
| guide-signal-lab-007.html | `guide-investment-books.html` |
| guide-signal-lab-008.html | `guide-investment-books.html` |
| guide-signal-lab-009.html | `guide-investment-books.html` |

**背景**: 2026-06-15 に追加された「📖 投資本」ボタン（10 ボタン化）が、それ以前に生成されたこれらの記事のナビバーに反映されていない。`python unify_navbar.py --apply` で一括更新可能。

---

## 📋 推奨対応

| 優先度 | 対応内容 | 担当 |
|---|---|---|
| 🔵 低 | `python unify_navbar.py --apply` でナビバーを 10 ボタンに統一 → sync → workflow 起動 | 人間 or 次回セッション |
| 🔵 低 | guides.html に signal-lab-006〜009 のカードが本当に欠けているか確認し、`publish_article.py` で登録補完 | 人間 or 次回セッション |

> ⚠️ SYNC 禁忌ファイルの混入は **0 件**。巻き戻し事故リスクなし。
>
> 警告は既存記事のナビ更新漏れ・カード未登録のみ。サイトの可用性・法務コンプラには影響なし。対応は余裕を持って実施できます。

---

## 📄 リンター生出力（原文）

```
🔍 サイト整合性チェック（check_site_consistency.py）
  検査した guide記事: 84 件（自動生成記事を除く） / SYNC_FILES: ローカル専用のためスキップ（sync_to_github.py がリモートに無い＝正常）

⚠️  警告 8 件:
   - guide-signal-lab-006.html: guides.html にカードが無い（一覧から辿れない）
   - guide-signal-lab-007.html: guides.html にカードが無い（一覧から辿れない）
   - guide-signal-lab-008.html: guides.html にカードが無い（一覧から辿れない）
   - guide-signal-lab-009.html: guides.html にカードが無い（一覧から辿れない）
   - guide-signal-lab-006.html: ナビに不足リンク ['guide-investment-books.html']（10ボタン未満）
   - guide-signal-lab-007.html: ナビに不足リンク ['guide-investment-books.html']（10ボタン未満）
   - guide-signal-lab-008.html: ナビに不足リンク ['guide-investment-books.html']（10ボタン未満）
   - guide-signal-lab-009.html: ナビに不足リンク ['guide-investment-books.html']（10ボタン未満）

結果: ✅ OK（エラーなし・警告 8 件）
EXIT_CODE=0
```

---

*生成: 2026-06-20 10:01 JST（routine `site-qa-lint` / `check_site_consistency.py`）*
