# 🧪 サイト整合性 QA レポート（基準日 2026-07-04 10:01 JST）

## 総合結果

| 項目 | 値 |
|---|---|
| 実行日時（JST） | 2026-07-04 10:01:22 |
| 検査対象 guide 記事数 | 130 件（自動生成記事を除く） |
| SYNC_FILES 登録数 | 8 件 |
| **総合判定** | ❌ **NG**（エラー: 78 件 / 警告: 1 件） |

---

## ❌ エラー一覧（78 件）

> ⚠️ **SYNC禁忌の混入は検出されませんでした**（最優先インシデントなし）。  
> 全エラーは「guide-*.html が SYNC_FILES に未登録」という同種の問題です。

### 原因分析

リポジトリ内に 130 件の guide 記事が存在しますが、`sync_to_github.py` の `SYNC_FILES` リストに登録されているのは **8 件のみ**です。  
これは **記事が GitHub 側（Actions や routine）で直接コミット・公開されるケースが増えた結果、SYNC_FILES リストが実態と乖離**したためと考えられます。

ただし、これらの記事はすでに GitHub リポジトリ上に存在しており、ライブサイトにも公開されています。**「SYNC_FILES に未登録」はローカルから再 sync するときにファイルが送信されないリスクを示す警告**であり、現時点でページが消えているわけではありません。

### 未登録ファイル一覧

```
guide-adx.html
guide-ai-investing-4types.html
guide-amd-2026-05.html
guide-bank-stocks-2026-05.html
guide-boj-2026-04.html
guide-bollinger-bands.html
guide-btc-crash-2026-05-19.html
guide-btc-crash-2026-06.html
guide-buffett-indicator.html
guide-clarity-act.html
guide-cognitive-biases.html
guide-compounding-drawdown.html
guide-correction-playbook.html
guide-credit-spread.html
guide-diversification.html
guide-dollar-cost-averaging.html
guide-dow-theory.html
guide-etf-vs-mutual-fund.html
guide-fear-greed.html
guide-fibonacci.html
guide-fomc-2026-04.html
guide-fomc.html
guide-graham-001.html
guide-gw-gap-2026-05.html
guide-honebuto-2026.html
guide-ichimoku.html
guide-ideco.html
guide-interest-rates-bonds.html
guide-investment-books.html
guide-investment-tax.html
guide-japan-strategy-2026-05.html
guide-jp-value-vs-zombie.html
guide-jpy-intervention-2026-04.html
guide-jpy-intervention-2026-05-06.html
guide-jpy-intervention-2026-06.html
guide-kioxia-2026-05.html
guide-learning-roadmap.html
guide-leverage.html
guide-loss-cut.html
guide-macd.html
guide-margin-balance.html
guide-moving-average.html
guide-nikkei-60000.html
guide-nikkei-60k-break-2026-05-20.html
guide-nikkei-65k-break-2026-05-25.html
guide-nisa-ranking.html
guide-nisa.html
guide-nvidia-2026-05.html
guide-order-types.html
guide-oriental-land-2026-06.html
guide-per-pbr.html
guide-position-sizing.html
guide-private-credit.html
guide-profit-taking.html
guide-risk-by-account-size.html
guide-risk-reward.html
guide-rsi.html
guide-sell-in-may.html
guide-simple-vs-compound-interest.html
guide-softbank-group-2026-05.html
guide-stochastics.html
guide-summer-doldrums.html
guide-swap-points.html
guide-toyota-2026-05.html
guide-trading-journal.html
guide-trading-psychology-calm.html
guide-tsmc-2026-05.html
guide-us-china-summit-2026-05.html
guide-us-china-summit-result-2026-05-14.html
guide-us-china-summit-result-2026-05-15.html
guide-us-cpi-2026-05.html
guide-us-cpi.html
guide-us-gdp.html
guide-us-jobs-2026-05.html
guide-vix.html
guide-volume.html
guide-yen-carry-trade.html
guide-yield-curve.html
```

---

## ⚠️ 警告一覧（1 件）

| ファイル | 内容 |
|---|---|
| `guide-news-2026-07-02-nikkei-kioxia-ai-selloff.html` | `guides.html` にカードが無い（一覧から辿れない） |

**対応**: `news-daily-auto` routine が公開した記事ですが、guides.html の「今日のニュース」カードが追加されていない可能性があります。手動で確認し、必要であれば `python mw.py publish` でカードを追加してください。

---

## 📋 推奨対応

| 優先度 | 項目 | 対応方法 |
|---|---|---|
| 🟡 中（ローカル sync 前必須） | SYNC_FILES に 78 件の guide-*.html が未登録 | `sync_to_github.py` の `SYNC_FILES` を最新の全 guide-*.html で更新する。または「ローカルから個別ファイルを送る場合のみ都度追記」する運用に切り替える（GitHub Actions / routine 経由で公開した記事はすでにライブに存在するため緊急性は低い） |
| 🟡 中 | `guide-news-2026-07-02-nikkei-kioxia-ai-selloff.html` の guides.html カードなし | `python mw.py publish` で guides.html にカードを追加する |
| ✅ なし | SYNC禁忌ファイルの混入 | 検出なし（問題なし） |
| ✅ なし | 免責漏れ | 検出なし（問題なし） |
| ✅ なし | リンク切れ | 検出なし（問題なし） |

---

## 📄 リンター生出力（原文）

```
🔍 サイト整合性チェック（check_site_consistency.py）
  検査した guide記事: 130 件（自動生成記事を除く） / SYNC_FILES: 8 件

⚠️  警告 1 件:
   - guide-news-2026-07-02-nikkei-kioxia-ai-selloff.html: guides.html にカードが無い（一覧から辿れない）

❌ エラー 78 件（要修正）:
   - guide-adx.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-ai-investing-4types.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-amd-2026-05.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-bank-stocks-2026-05.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-boj-2026-04.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-bollinger-bands.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-btc-crash-2026-05-19.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-btc-crash-2026-06.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-buffett-indicator.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-clarity-act.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-cognitive-biases.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-compounding-drawdown.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-correction-playbook.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-credit-spread.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-diversification.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-dollar-cost-averaging.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-dow-theory.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-etf-vs-mutual-fund.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-fear-greed.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-fibonacci.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-fomc-2026-04.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-fomc.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-graham-001.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-gw-gap-2026-05.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-honebuto-2026.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-ichimoku.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-ideco.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-interest-rates-bonds.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-investment-books.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-investment-tax.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-japan-strategy-2026-05.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-jp-value-vs-zombie.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-jpy-intervention-2026-04.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-jpy-intervention-2026-05-06.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-jpy-intervention-2026-06.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-kioxia-2026-05.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-learning-roadmap.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-leverage.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-loss-cut.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-macd.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-margin-balance.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-moving-average.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-nikkei-60000.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-nikkei-60k-break-2026-05-20.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-nikkei-65k-break-2026-05-25.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-nisa-ranking.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-nisa.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-nvidia-2026-05.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-order-types.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-oriental-land-2026-06.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-per-pbr.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-position-sizing.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-private-credit.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-profit-taking.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-risk-by-account-size.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-risk-reward.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-rsi.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-sell-in-may.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-simple-vs-compound-interest.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-softbank-group-2026-05.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-stochastics.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-summer-doldrums.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-swap-points.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-toyota-2026-05.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-trading-journal.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-trading-psychology-calm.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-tsmc-2026-05.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-us-china-summit-2026-05.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-us-china-summit-result-2026-05-14.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-us-china-summit-result-2026-05-15.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-us-cpi-2026-05.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-us-cpi.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-us-gdp.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-us-jobs-2026-05.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-vix.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-volume.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-yen-carry-trade.html: SYNC_FILES に未登録（sync されずライブに出ない）
   - guide-yield-curve.html: SYNC_FILES に未登録（sync されずライブに出ない）

結果: ❌ NG（エラーあり。sync 前に修正してください）
EXIT_CODE: 1
```

---

*このレポートは `check_site_consistency.py` の出力を自動集計して生成されました。*
