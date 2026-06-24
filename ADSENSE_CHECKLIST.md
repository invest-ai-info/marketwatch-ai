# 📋 Google AdSense 対策チェックリスト（2026-06-06 点検）

不承認理由＝**「有用性の低いコンテンツ」**（自動データページ中心で独自価値が薄いと判断）。
本書は再審査に向けた現状採点と残タスク。pub-2552122294306014。

---

## ✅ スコアカード（2026-06-06 時点）

| 領域 | 状態 | メモ |
|---|---|---|
| ads.txt | ✅ | `google.com, pub-2552122294306014, DIRECT, f08c47fec0942fa0`・ライブ確認済 |
| プライバシーポリシー | ✅ | AdSense/Cookie/第三者配信/オプトアウト（Google広告設定・aboutads.info）を開示。2026-06-06に「利用予定→利用しています」修正＋オプトアウトリンク追加 |
| 運営者情報（about.html） | ✅ | E-E-A-T 強化済 |
| お問い合わせ（contact.html） | ✅ | あり |
| 免責（投資助言でない） | ✅ | `kinsho-v1` を全ページ footer に統一挿入 |
| オリジナル記事 | ✅ | **49本**（投資心理・リスク管理・テクニカル分析・速報・個別銘柄）。SVG図解・内部リンクでトピック権威性 |
| 薄いデータページ | ✅ | **2026-06-06：6コアページすべてにオリジナル解説を追加完了**（vix／hot-assets／calendar／market-health／charts／index に「📘 見方・活用法 / できること」セクション＝独自本文＋関連guide内部リンク＋免責）。“データダンプ”→“データ＋独自解説”化 |
| noindex 整理 | ✅ | `guide-auto-*`（自動指標プレビュー）は noindex＋**2026-06-06 sitemapからも除外**。`drafts/` は robots Disallow＋noindex |
| ナビ / モバイル | ✅ | 9ボタン・レスポンシブ |
| ポリシー（誇大/優良誤認） | ✅ | compliance-reviewer(Opus) 運用・断定表現排除・黒5件対応済 |
| 広告配置 | ⚠️（承認後） | 審査は自動広告 or 手動配置どちらでも可。承認後に配置最適化 |

---

## 🎯 残タスク（優先順）

1. **（待ち）Google の再クロール待ち（数日）**。6コアページの新解説が反映されてから再審査を出す。`site:marketwatch-jp.com` で索引状況を確認。
2. **（小・継続）** オリジナル記事を増やし続ける（下書き自動生成 routine `autodraft-article` が毎日候補を生成中）。
3. **（ユーザー操作・再審査）** 数日おいてから、AdSense コンソールで **「問題を修正しました」にチェック → 審査をリクエスト**（コンソールに該当ボタンあり）。支払い情報の登録も済ませる。
4. **（承認後）** 広告配置・自動広告の最適化（記事末尾・サイドなど。射幸性訴求は禁止）。
5. ~~（任意）youtube-summary / political-feed に独自コメント~~ ✅**完了（2026-06-06）**：両ページに独自の「📘 見方・活用法 / 使い方」セクション（政治発言が相場を動かす仕組み／YouTube要約の心構え＝ポジショントーク注意・元動画確認＋関連guide内部リンク＋免責）を追加。アグリゲーション色を独自編集色で緩和。

## 🗓️ 再審査タイミングの考え方
- 不承認理由は**「有用性の低いコンテンツ」**（コンソールのスクショで確認・2026-06-06）。
- **今すぐの再審査は非推奨**：6コアページの解説追加が**Googleに再クロールされる前**だと、bot が古い薄いページを見て再不承認になりやすい。
- **推奨フロー**：①6コア解説追加（済）→ ②数日〜1週間あけて Google が再クロール → ③`site:marketwatch-jp.com` で新内容が索引されたのを確認 → ④再審査リクエスト（1回で通しにいく）。
- 再不承認の繰り返しは印象・待機面で不利なので「明らかに基準超え」にしてから1回で。

---

## 📝 本日（2026-06-06）実施
- **privacy.html 強化**：「利用予定→利用しています」／Google広告設定（adssettings.google.com）・aboutads.info のオプトアウトリンク追加／最終更新2026-06-06。
- **sitemap.xml**：`build_sitemap_xml` で noindex の `guide-auto-*` を除外（索引矛盾を解消）。
- **データページ enrich**：vix / hot-assets / calendar に各オリジナル「📘 見方・活用法」セクション（独自解説＋関連guide内部リンク＋免責）を追加。

---

## 📝 2026-06-24 再監査＆second-tier 実施（実機検証済み）

**監査結論＝再申請レディ（6/19時点より強化）**。実機チェック結果：
- sitemap：noindexルール違反の混入 **0**。6/19の85→105へ増えたが、+20は本日の基礎5本（金利と債券/単利と複利/ETF×投信/PER・PBR/注文方法）・signal-lab・news 等の**正当な編集記事増**。
- 薄い自動/日付ページ（週次/週次振り返り/月次/preview/旧フラッシュ）＝**全て noindex 維持**。主要記事（基礎/テクニカル/研究日誌/ニュース）＝**全て index 維持**。
- 6コアデータページ（index/calendar/charts/vix/market-health/hot-assets）＝**独自解説セクション全て生存**。
- 必須：ads.txt(pub一致)・about・contact・privacy・sitemap = **全て200**／robots.txt **オープン**（/drafts/のみDisallow）。
- `mw audit`＝index対象86本中 改善候補(score≥2) **0**。

**second-tier（オーナー承認のうえ実施）**＝index のまま残っていた「消えても良い日付つきイベント速報フラッシュ **7本**」を `noindex,follow`＋sitemap除外：
`guide-btc-crash-2026-05-19` / `guide-btc-crash-2026-06` / `guide-nikkei-60k-break-2026-05-20` / `guide-nikkei-65k-break-2026-05-25` / `guide-us-china-summit-2026-05` / `guide-us-china-summit-result-2026-05-14` / `guide-us-china-summit-result-2026-05-15`。
- 手順＝`generate_market_news.py` の `NOINDEX_SLUGS` に7本追加（単一ソース）→ `apply_noindex.py`（patched 7/already 19/skipped 0）→ sync(189/0)→ `mw trigger update-market-news.yml`（sitemap再生成）。
- **深掘り個別銘柄（NVIDIA/TSMC/トヨタ/SBG/AMD/OLC/Kioxia）・`bank-stocks-2026-05`・`japan-strategy-2026-05`・`jpy-intervention-2026-06` は価値があるので index 維持**（実機で確認）。
- 実機検証＝7本すべて live で noindex／上記 index 維持を確認。sitemap は再生成後 **98** へ落ちる見込み（数分ラグ）。

**🗓 ユーザー操作（再申請の gating）**＝Google 再クロール待ち。Search Console「ページ」で薄ページ＋7本が「除外（noindexタグにより）」へ移ったか、または `site:marketwatch-jp.com` で消えたかを確認 → AdSense で「問題を修正しました」→「審査をリクエスト」。再申請目安は **2026-06-26 頃**（オーナー判断）。
