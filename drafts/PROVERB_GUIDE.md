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
| 16 | 事件は売り、事故は買い | jiken-uri-jiko-kai | 🚨 | 人為的不祥事（信頼毀損）は影響が長引き、一過性の事故（火災・システム障害等）は過剰反応が戻りやすいという古典分類。**芯＝適用範囲の見極め**：急騰後の反動・バブル修正は「事件でも事故でもない第三類型」で、この格言では判断できない（2026年7月の半導体大手株の急落＝3ヶ月で5倍→1ヶ月で半値は好例。事例として使う場合は中立の事実整理のみ・売買推奨や「今が買い場/売り場」の示唆は厳禁） | ochiru-knife / correction系 |
| 17 | 山高ければ谷深し | yama-takakereba-tani-fukashi | 🏔 | 急騰の反動は大きい・上げ幅と下げ幅の対称性・過熱をどう測るか（乖離率・急騰倍率） | fear-greed / ochiru-knife |
| 18 | 天井三日、底百日 | tenjo-mikka-soko-hyakunichi | ⏱ | 天井は短く底は長い＝時間軸の非対称。焦って底を拾う必要がない理由 | mugiwara-fuyu / matsu-mo-soba |
| 19 | 押し目待ちに押し目なし | oshime-machi-ni-oshime-nashi | 🚏 | 強いトレンドでは調整を待つほど乗れない。機会損失の心理とFOMOの境界・「待つも相場」との緊張関係が独自の切り口 | matsu-mo-soba / soba-ni-kike |
| 20 | 行き過ぎもまた相場 | ikisugi-mo-soba | 🎢 | オーバーシュートは常態＝「適正価格に戻るはず」を当てにした逆張りの危うさ。ケインズ「市場は自分の支払能力より長く不合理でいられる」と接続 | ochiru-knife / fear-greed |
| 21 | 命金には手をつけるな | inochigane-ni-te-wo-tsukeru-na | 🛑 | 生活資金と投資資金の分離・「退場しない」が複利の前提。生活防衛資金の考え方 | position-sizing / nisa系 |
| 22 | 万人が万人ながら強気なら、たわけになりて米を売るべし | mannin-kyoki-tawake | 🌾 | 本間宗久（宗久翁秘録・諸説あり明示）。全員が強気＝買い手が尽きた天井という群集心理の極。もうはまだなり（#8）の姉妹編だが「全員一致」への着目が独自 | mou-mada / fear-greed |
| 23 | セル・イン・メイ（Sell in May and go away） | sell-in-may | 🗓 | 英国発の季節アノマリー格言。**芯＝格言をデータで検証する態度**：由来（後半節 St Leger Day）・統計的な支持/不支持の両論を紹介し「鵜呑みにせず検証する」で締める | アノマリー系 / 検証態度 |
| 24 | 国策に売りなし | kokusaku-ni-uri-nashi | 🏛 | 政策テーマの追い風の意味と**限界**（「売りなし」を文字通り信じない・政策転換リスク・テーマ株の過熱）。格言の批判的読解が芯 | political-feed導線 / news解釈 |
| 25 | 下手なナンピン、スカンピン | heta-nampin-sukampin | 🕳 | ナンピンの数理（平均取得単価が下がる**錯覚**と損失加速・資金枯渇）。**芯＝計画的な分割買い（#12 二度に買うべし）との線引き**：事前に決めた分割は戦略、含み損の後追いは破綻への道 | nido-ni-kau / loss-cut / position-sizing |
| 26 | もちあいは放れにつけ | mochiai-hanare | 📈 | レンジ相場のエネルギー蓄積とブレイク追随の古典。**芯＝ダマシ（フェイクブレイク）とどう付き合うか**：ブレイクの確認方法・損切り位置の考え方を中立に整理 | dow-theory / soba-ni-kike |
| 27 | 三割高下に向かえ | sanwari-kouge | 🎯 | 3割上げたら売り・3割下げたら買いを検討する江戸の目安。**芯＝固定の数字を鵜呑みにせず検証する態度**（#23セル・イン・メイと同じ姿勢）：目安の由来と「銘柄・時代で全く違う」限界を両論併記 | fear-greed / 検証態度 |
| 28 | 閑散に売りなし | kansan-ni-uri-nashi | 🌫 | 出来高が枯れた相場で売り込んでも続かないという出来高格言。**芯＝出来高は相場の燃料**：閑散＝売り手も尽きた状態の読み方と、逆に「人気過熱の飛びつきが不利になりやすい」対の話まで（数値は仮の例のみ） | hot-assets導線 / ochiru-knife |
| 29 | 相場の金と凧の糸は出し切るな | soba-no-kane-tako-no-ito | 🪁 | 全力買い禁止・余力の価値。**芯＝余力は「次の機会」と「心の平静」の両方を買う**：命金（#21 生活資金の分離）とは別レイヤーの、投資資金内での弾薬管理 | inochigane-ni-te-wo-tsukeru-na / position-sizing |
| 30 | 株を買うより時を買え | kabu-yori-toki | ⏰ | 銘柄選びより「いつの相場か」（地合い・環境）が結果を左右する。**芯＝同じ銘柄でも環境次第で結果が変わる**：地合いの見方（市場全体の健康度・イベント前後）を初心者向けに整理 | market-health導線 / calendar導線 |
| 31 | トレンドは友（Trend is your friend） | trend-is-your-friend | 🤝 | 順張りの規律を説く英語圏の定番。**芯＝原文の後半 "until it ends" まで含めて理解する**：友はいつか終わる＝トレンド転換のサインと、逆らわないことと飛び乗ることの違い | dow-theory / soba-ni-kike |
| 32 | FRBには逆らうな（Don't fight the Fed） | dont-fight-the-fed | 🏦 | 金融政策・流動性が地合いを決めるという米国格言。**芯＝政策金利と相場の関係の基礎教育＋盲信の限界**（政策は転換する・「逆らうな」は思考停止の免罪符ではない）。国策に売りなし（#24 財政・テーマ）との違い＝こちらは金利・流動性 | calendar（FOMC）/ political-feed導線 |
| 33 | 稲妻が輝く瞬間に市場に居よ | inazuma-kagayaku-shunkan | ⚡ | チャールズ・エリスの言葉（出典明示）。上昇の大半はごく少数の日に集中し、その日を逃すと成績が激変する＝タイミング売買の難しさ。**芯＝短期売買の否定ではなく「休むも相場（#11）」と両立する読み方**：長期積立と短期取引で結論が変わる | 積立・NISA系 / matsu-mo-soba |

※キューはここに追記して伸ばす（強い格言だけ・水増し禁止）。和洋どちらも可。重複・既存ガイドとの過度な被りは避け、必ず「格言を入口にした独自の切り口」にする。
