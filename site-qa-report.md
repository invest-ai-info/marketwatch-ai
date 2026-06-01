# 🧪 サイト整合性 QA レポート（基準日 2026-06-01 20:49 JST）

**実行日時**: 2026-06-01T20:49:25 JST（UTC+9）  
**実行環境**: GitHub Actions リモートコンテナ  
**リンタースクリプト**: `check_site_consistency.py`（存在確認: ✅）

---

## 総合結果

| 区分 | 件数 |
|---|---|
| 総合判定 | ✅ OK |
| ❌ エラー件数 | 0 件 |
| ⚠️ 警告件数 | 24 件 |
| 検査 guide 記事 | 36 件（自動生成記事除く） |
| ✅ SYNC禁忌混入 | 検出なし |
| ✅ 免責表示（kinsho-v1） | 問題なし |
| ✅ ナビボタン 9 個 | 正常 |
| SYNC_FILES チェック | スキップ（sync_to_github.py がリモートに無いため正常） |

---

## エラー一覧

**エラーなし。**  
SYNC禁忌の混入・免責文言漏れ・ナビバー9ボタン構成・リンク切れ等の致命的問題はすべてクリアです。

---

## 警告一覧（sitemap.xml 未登録 24 件）

以下の guide-*.html ファイルが `sitemap.xml` に未登録です。SEO 上は Google クローラーのクロール誘導が不十分な状態ですが、ライブ公開されているページへの即座のユーザー影響はありません。余裕があるときに対応推奨。

| ファイル名 |
|---|
| guide-amd-2026-05.html |
| guide-bank-stocks-2026-05.html |
| guide-btc-crash-2026-05-19.html |
| guide-clarity-act.html |
| guide-gw-gap-2026-05.html |
| guide-ideco.html |
| guide-japan-strategy-2026-05.html |
| guide-jpy-intervention-2026-05-06.html |
| guide-kioxia-2026-05.html |
| guide-nikkei-60k-break-2026-05-20.html |
| guide-nikkei-65k-break-2026-05-25.html |
| guide-nvidia-2026-05.html |
| guide-oriental-land-2026-06.html |
| guide-sell-in-may.html |
| guide-softbank-group-2026-05.html |
| guide-toyota-2026-05.html |
| guide-tsmc-2026-05.html |
| guide-us-china-summit-2026-05.html |
| guide-us-china-summit-result-2026-05-14.html |
| guide-us-china-summit-result-2026-05-15.html |
| guide-us-cpi-2026-05.html |
| guide-us-cpi.html |
| guide-us-jobs-2026-05.html |
| guide-yen-carry-trade.html |

---

## 推奨対応

### 即時対応不要
エラーゼロにつき、緊急対応は不要です。

### 余裕対応（sitemap 未登録 24 件）
上記 24 ファイルを `sitemap.xml` へ一括追加することで検索エンジンのクロールが改善されます。  
`python mw.py publish` コマンドを使った公開フローを踏めば sitemap 登録が自動化されます。  
一括追加は `python mw.py check` の警告ゼロを目標に、週次 QA のタイミングで対応推奨。

---

## リンター生出力（原文）

```
🔍 サイト整合性チェック（check_site_consistency.py）
  検査した guide記事: 36 件（自動生成記事を除く） / SYNC_FILES: ローカル専用のためスキップ（sync_to_github.py がリモートに無い＝正常）

⚠️  警告 24 件:
   - guide-amd-2026-05.html: sitemap.xml に未登録
   - guide-bank-stocks-2026-05.html: sitemap.xml に未登録
   - guide-btc-crash-2026-05-19.html: sitemap.xml に未登録
   - guide-clarity-act.html: sitemap.xml に未登録
   - guide-gw-gap-2026-05.html: sitemap.xml に未登録
   - guide-ideco.html: sitemap.xml に未登録
   - guide-japan-strategy-2026-05.html: sitemap.xml に未登録
   - guide-jpy-intervention-2026-05-06.html: sitemap.xml に未登録
   - guide-kioxia-2026-05.html: sitemap.xml に未登録
   - guide-nikkei-60k-break-2026-05-20.html: sitemap.xml に未登録
   - guide-nikkei-65k-break-2026-05-25.html: sitemap.xml に未登録
   - guide-nvidia-2026-05.html: sitemap.xml に未登録
   - guide-oriental-land-2026-06.html: sitemap.xml に未登録
   - guide-sell-in-may.html: sitemap.xml に未登録
   - guide-softbank-group-2026-05.html: sitemap.xml に未登録
   - guide-toyota-2026-05.html: sitemap.xml に未登録
   - guide-tsmc-2026-05.html: sitemap.xml に未登録
   - guide-us-china-summit-2026-05.html: sitemap.xml に未登録
   - guide-us-china-summit-result-2026-05-14.html: sitemap.xml に未登録
   - guide-us-china-summit-result-2026-05-15.html: sitemap.xml に未登録
   - guide-us-cpi-2026-05.html: sitemap.xml に未登録
   - guide-us-cpi.html: sitemap.xml に未登録
   - guide-us-jobs-2026-05.html: sitemap.xml に未登録
   - guide-yen-carry-trade.html: sitemap.xml に未登録

結果: ✅ OK（エラーなし・警告 24 件）
EXIT_CODE:0
```

---

*このレポートは `site-qa-lint` routine（週次自動実行）により生成されました。*
