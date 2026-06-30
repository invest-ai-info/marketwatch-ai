# 投資格言から学ぼう — 自動公開 手順書（PROVERB_GUIDE.md）

クラウドルーティン **proverb-daily-auto** が毎日読む正式手順書。1日1本、投資格言の解説記事を生成→コンプラ＆品質ゲート→白なら自動公開、危ういものは公開せずエスカレ。
**人が編集する＝SYNC_FILES入り。** ⚠️ 発火エンジン・signal_lab系・固定オラクル・6コアHTMLには触れない（実行のみ）。

---

## 0. このシリーズの狙い（品質の芯）
格言は「先人が損して学んだ知恵の圧縮ファイル」。**覚えやすい入口**を提供しつつ、既存の深掘りガイドへ送客する。
⚠️ **薄コンテンツ厳禁**（AdSense審査の生命線）。「格言＋一言」では絶対に出さない。各記事は必ず：
- ① 意味と由来（誰の/どの場面の言葉か） ② **具体的な数字example**（匿名の仮設定で損益を実数比較）
- ③ 裏の投資心理 ④ 現代の実践（複数の具体策） ⑤ よくある誤解 ⑥ まとめ＋関連ガイド
- **インラインSVG概念図を最低1枚**（ライト/ダーク両対応・`※概念を示すイメージ図です`明示）
- 8〜10分の読み応え。手本＝`guide-proverb-atama-shippo.html`（第1号・このテンプレを丸ごと踏襲）。

## 1. 記事テンプレ（厳守）
**`guide-proverb-atama-shippo.html` の `<head>`〜`<style>`〜nav〜フッター〜スクリプトを丸ごとコピーし、本文と<head>メタ（title/description/canonical/OG/JSON-LD）だけ差し替える。**
- ファイル名：`guide-proverb-<slug>.html`（slugはキュー参照）
- nav は10ボタン・`guides.html` を current。冒頭 `disclaimer-banner`、本文末 `p[data-disclaimer="kinsho-v1"]`、フッターにも `kinsho-v1`。
- 数値例には必ず「考え方を説明するための仮の例」注記。SVGには `<title>` と figcaption 末尾に「※概念を示すイメージ図です。」。
- 断定/将来予測/特定銘柄の売買推奨は禁止。一般論・教育として書く。結論は「〜に近づく/つながる」と非断定。

## 2. 毎日の手順
1. `date -u` → JST(+9) で基準日。
2. **次に書く格言を決める**：下の【キュー】を上から見て、`drafts/proverb/PROVERB_LEDGER.md` と `guides.html` のどちらにも未登録（＝`guide-proverb-<slug>.html` がまだ無い）最初の1件を選ぶ。
   - ★既に当日分の `guide-proverb-*.html` をこの実行で作っていれば**何もしない**（1日1本）。
   - ★キューが尽きたら**新しい格言を勝手に作らない**。`PROVERB_LEDGER.md` に「🚩キュー枯渇・補充依頼」を記録してエスカレし終了（弱い格言の水増し＝薄コンテンツ＝厳禁）。
3. テンプレに従い `guide-proverb-<slug>.html` を作成（§0・§1 の厚みを必ず満たす）。由来・人物・出典に事実確認が要る点は WebSearch で確認（不確実なら「諸説あり」と明示、断定しない）。
4. 【コンプラ自動公開ゲート（signal-lab/news方式）】Agentツールで **model=opus** のサブエージェント（Read,Edit・`.claude/agents/compliance-reviewer.md` ペルソナ）に監査させる：①黒/グレー/白 ②グレーは軽微修正（表現軟化・免責追加のみ／事実・数値・SVG・構造は不変）をEditで適用 ③適用後に再読し最終判定 ④黒 or 要協議（軽微では消せない）なら編集せず「エスカレ」。返り値＝【初期/適用修正/最終】。
5. 【品質ルーブリック】`QUALITY_RUBRIC.md` の5観点で自己採点。⚠️は表現・構成・補足1文だけで自己修正（数値/SVG/主張/免責は不変）、❌（直すと中身が変わる）はエスカレ。
6. **公開判定**：初期=白 もしくは（グレー→opus軽微修正→最終=白）かつ ルーブリック合格 のときのみ進む。さらに別の fresh な **model=opus** サブエージェント（Readのみ・同ペルソナ）で「そのまま公開して白か」を独立確認。白でなければ手順8。
   【公開前の決定論チェック（全て満たす／欠けたら手順8）】① `kinsho-v1` 免責が 冒頭＋本文末＋フッター ②禁止語なし（必ず/絶対/確実/100%/儲かる/一択/今すぐ買い 等の断定・利益保証）③特定銘柄の買い/売り推奨なし ④SVGに「概念図」明示・数値に「仮の例」明示。
7. **公開**：
   a. `python publish_article.py --file guide-proverb-<slug>.html --category "投資格言から学ぶ" --emoji <絵文字> --card-title "<格言>" --desc "<1行説明>"`
   b. `python check_site_consistency.py; echo EXIT=$?`（赤なら中止しエスカレ）
   c. `git add guide-proverb-<slug>.html guides.html generate_market_news.py sync_to_github.py drafts/ && git commit -m "feat: 投資格言 auto-publish <slug>" && git push origin main`
   d. `drafts/proverb/PROVERB_LEDGER.md` に「✅公開済み・格言・slug・コンプラ判定・出典」を追記しコミット＆push。
8. **エスカレ（公開しない）**：記事を `drafts/proverb/draft-<slug>.html` に `<meta name="robots" content="noindex,nofollow">` 付きで保存し、`drafts/proverb/PROVERB_LEDGER.md` に「🚩要人間レビュー（理由）」を記録して `git add drafts/proverb/ && git commit -m "chore: proverb escalate <slug>" && git push origin main`。
9. 最後に日本語要約：選定した格言・コンプラ判定（初期/適用修正/独立確認 or エスカレ理由）・公開有無・ファイル名。

## 3. 絶対厳守
- **1日1本まで**（当日分の `guide-proverb-*.html` が既にあれば何もしない）。
- **キュー枯渇時は水増し公開しない**＝エスカレして補充を待つ。
- 6コアHTML（index/calendar/charts/vix/market-health/hot-assets）・political-feed・track-record・sitemap.xml に直接触れない。
- 発火エンジン(`generate_technical_alerts.py`)・signal_lab系・固定オラクル(`signal_lab_verify.py`/`check_site_consistency.py`/`publish_article.py`)は**書き換えない（実行はOK）**。
- 推奨・利益示唆・断定（必ず/絶対/保証/儲かる/一択）禁止。事実は WebSearch 実値のみ。出力は日本語。**情報提供であり投資助言ではない。**
- 少しでもエラー・事実未確定・コンプラの迷いがあれば**公開せずエスカレ（安全側）**。

---

## 【キュー】投資格言（上から順に消化）
| # | 格言 | slug | 絵文字 | 学べること・芯 | 接続先ガイド |
|---|---|---|---|---|---|
| 1 | 頭と尻尾はくれてやれ | atama-shippo | 🐟 | 天井・大底を狙わず胴体を取る | profit-taking ✅**公開済** |
| 2 | 買いは家まで、売りは命まで | kai-ie-uri-inochi | ⚠️ | 買いの損失は限定・空売りは無限。リスクの非対称 | leverage / loss-cut |
| 3 | 落ちてくるナイフはつかむな | ochiru-knife | 🔪 | 急落の途中で逆張りしない・底打ち確認 | correction-playbook / loss-cut |
| 4 | 卵は一つの籠に盛るな | tamago-kago | 🧺 | 分散の本質（相関・集中リスク） | diversification |
| 5 | 噂で買って事実で売る | uwasa-jijitsu | 📰 | 期待の織り込みと材料出尽くし | （新規・ニュース解釈） |
| 6 | 人の行く裏に道あり花の山 | hito-no-iku-ura | 🌸 | 逆張り・群集心理・コントラリアン | fear-greed |
| 7 | 見切り千両、損切り万両 | mikiri-senryo | ✂️ | 損切りの価値を江戸の知恵で | loss-cut |
| 8 | もうはまだなり、まだはもうなり | mou-mada | 🔄 | 天底の心理・相場観の戒め | fear-greed |
| 9 | 相場は相場に聞け | soba-ni-kike | 👂 | 主観でなく価格・トレンドに従う | dow-theory |
| 10 | 待つも相場 | matsu-mo-soba | ⏳ | 現金もポジション・休む勇気 | position-sizing |
| 11 | 休むも相場 | yasumu-mo-soba | 🛌 | 過剰取引の戒め・メンタル管理 | trading-psychology-calm |
| 12 | 二度に買うべし二度に売るべし | nido-ni-kau | 📊 | 分割売買で平均化・タイミング分散 | order-types |
| 13 | 強気相場は悲観の中に生まれる | kyoki-hikan | 🌅 | テンプルトンの言葉・弱気の極で芽生える強気 | fear-greed |
| 14 | 麦わら帽子は冬に買え | mugiwara-fuyu | 🌾 | 人気のないとき仕込む逆張り・季節性 | fear-greed |
| 15 | 利食い千人力 | rigui-sennin | 💰 | 利益確定の安心と価値（チキン利食いとの線引き） | profit-taking |

※キューはここに追記して伸ばす（強い格言だけ・水増し禁止）。和洋どちらも可。重複・既存ガイドとの過度な被りは避け、必ず「格言を入口にした独自の切り口」にする。
