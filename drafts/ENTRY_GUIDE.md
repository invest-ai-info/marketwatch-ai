# エントリー方法の研究 — 自動公開 手順書（ENTRY_GUIDE.md）

クラウドルーティン **entry-daily-auto**（毎日 12:23 JST）が毎日読む正式手順書。1日1本、「エントリー（買う・売るタイミング）の決め方」を1つずつ取り上げ、**研究でわかっていること・わかっていないこと**を深掘りする記事を生成→コンプラ＆品質ゲート→白なら自動公開、危ういものは公開せずエスカレ。
**人が編集する＝SYNC_FILES入り。** 台帳 `drafts/entry/ENTRY_LEDGER.md` と記事 `guide-entry-*.html` は GitHub 側で生成＝SYNC外。
⚠️ 発火エンジン・signal_lab系・固定オラクル・6コアHTMLには触れない（実行のみ）。

> 発足の経緯: 2026-09-25 オーナー指示「エントリー方法も面白そうなので、一つずつ記事にして詳しく深掘りしていくシリーズを。
> 普通の記事と変わらないので、最初から自動で、毎日1本ずつ」。
> 総論の下書き `drafts/draft-entry-methods.html`（11の型の一覧・未公開）の各型を、1本ずつ掘り下げる位置づけ。
> **広告は貼らない**（同日オーナー指示）＝ `inject_ads.py` の `DENY_PREFIX` に `guide-entry-` を登録済み。

---

## 0. このシリーズの狙い（品質の芯）

**「その入り方は、どんな研究で、どの市場で、どこまで確かめられているのか」を、読者が自分で判断できる材料として渡す。**
やり方の紹介で終わらせず、**研究の結果・反論・限界**まで書く。「効く／効かない」の結論を押しつけない。

⚠️ **薄コンテンツ厳禁**。各記事は必ず次の7つを持つ:

1. **30秒まとめ**（3点・数字は出典のあるものだけ）
2. **どんな方法か**（仮の例で「こういう場面で入る」を示す。数値例には「考え方を説明するための仮の例」と注記）
3. **研究でわかっていること**（論文ごとに：誰が・いつ・どの市場・どの期間で・何がわかったか。数字は §0-A のとおり確かめたものだけ）
4. **反論・限界**（反対の結果の研究、発表後に弱まった例、取引コスト・急な下落の場面）。**反論が見つからなければ「今回調べた範囲では見当たらなかった」と書く**
5. **株・FX・コモディティでは？**（🆕 オーナー指示 2026-09-25「株・FX・コモディティはそれぞれ分けて考えて。入り方も出方も違うと思う」）。
   その研究がどの市場のデータかを明記し、**株価指数・FX・コモディティ（金・原油など）それぞれについて、研究があるか／無いか**を短い表で示す。研究が無い市場は「この研究からはわからない」と書く（推測で埋めない）
6. **よくある誤解**（1〜3個）
7. **まとめ＋関連ガイド＋出典一覧**（出典はリンク付き）

- **インラインSVG概念図を最低1枚**（ライト/ダーク両対応・`<title>` 付き・figcaption 末尾に「※概念を示すイメージ図です（実際の値動きではありません）。」）。実在の価格・日付は描かない
- 読み応え 8〜12分。題名は検索される問いの形で、回番号を入れる：
  例「トレンドフォローは本当に効くの？ 研究でわかっていること【エントリー方法の研究 #01】」

### 0-A. 🚨 このシリーズだけの絶対条件（研究の数字）

- **論文の数字は、実際に見た出典からだけ書く。**見てよい出典＝論文の出版社のページ（要旨）、著者・大学・中央銀行など公的機関の公式ページや PDF、DOI のリンク先。**思い出しで数字を書かない。**まとめブログ・AIの要約・販促資料の数字は使わない。
- **数字を確かめられなかったら、その数字は書かない**（「〜という傾向を報告しています」のように数字なしで書く）。数字が無いことを理由にエスカレしない＝シリーズを止めない。
- **題材の中心の研究そのものに一度も届かなかった（要旨も読めない）ときだけ**、その回は書かずにエスカレ（§2 手順9）。
- 本文の出典一覧に、**どこで確かめたか**（要旨／公式PDF など）が分かるリンクを付ける。`ENTRY_LEDGER.md` にも「確かめた出典のURL」を残す。
- **研究の結果を、当サイトのシグナルの裏づけとして書かない。**当サイトのシグナル（RSI・MACD・移動平均・ボリンジャー・20本の高値安値ブレイク）に触れるときは、「研究が調べた期間・市場と、当サイトのシグナルの期間・市場は違う」ことを必ず添える（2026-09-25 コンプラ監査の指摘）。
- **特定の銘柄・特定の証券会社・特定の商品を評価しない。**手法の一般論として書く。

## 1. 記事テンプレ（厳守）

**`drafts/draft-entry-methods.html` の `<head>`〜`<style>`〜header〜nav〜フッター〜末尾スクリプトを丸ごとコピーし、本文と `<head>` メタ（title/description/keywords/canonical/OG/JSON-LD/breadcrumb）だけ差し替える。**

- ⚠️ コピー元は下書きなので **`<meta name="robots" content="noindex,nofollow">` を必ず消す**（残すと `check_guide_draft.py` が赤）。本文の `TODO` コメントも持ち込まない。
- ファイル名：`guide-entry-<slug>.html`（slug はキュー参照）。canonical・og:url・JSON-LD もこのファイル名に。
- meta-line：`公開：YYYY年M月D日 ／ 読了時間：約 N 分 ／ カテゴリ：🚪 エントリー方法の研究`
- nav はテンプレのまま（`guides.html` を current）。冒頭 `disclaimer-banner`（kinsho-v1）、本文末 `p.disclaimer[data-disclaimer="kinsho-v1"]`、フッターにも `kinsho-v1`。
- 関連記事は**実在するファイルだけ**（`ls guide-xxx.html` で確かめる。`check_guide_draft.py` も検査する）。総論 `guide-entry-methods.html` は**公開されていれば**関連に入れる（まだなら入れない）。
- 断定・将来予測・売買推奨は禁止。結論は「〜と報告されています」「〜は、この研究からはわかりません」。

## 2. 毎日の手順

1. `date -u` → JST(+9) で基準日。
2. **次に書く題材を決める**：下の【キュー】を上から見て、`guides.html` に `guide-entry-<slug>.html` のカードがまだ無い最初の1件を選ぶ。
   - ★この実行で当日分の `guide-entry-*.html` をすでに作っていれば**何もしない**（1日1本）。
   - **台帳に名前があるだけで「消費済み」にしない**（東証レーン 2026-09-01 の教訓）。台帳の記載を読み、止まった理由が**経路遮断（`CONNECT tunnel failed` / `EGRESS_BLOCKED`）や一時的なエラーなら、その題材をもう一度選ぶ**。選び直さないのは `🚩要人間レビュー` かつ理由がコンプラ🔴黒・品質❌・先方のbot判定（`cf-mitigated`）のときだけ。
   - キューの最後（`series-index`＝総まとめ）まで公開済みなら、**このシリーズは完結**。何も書かずに終了する（§4）。新しい題材を勝手に作らない。
3. **出典を先に開く。**キューの「主な研究」を手がかりに、WebSearch／WebFetch で要旨・公式ページを実際に取得し、書く数字を控える（§0-A）。
   - 取得できたURLを、記事の出典一覧と `ENTRY_LEDGER.md` の両方に残す。
   - 中心の研究に一度も届かなければ、記事を書かずに手順9へ（叩いた先と応答を書く。⚠️ UA偽装での迂回はしない）。
4. テンプレに従い `guide-entry-<slug>.html` を作成（§0 の7つを必ず満たす）。回番号 `#NN` はキューの番号。
5. **やさしい日本語の検査**：`git checkout -- check_plain_japanese.py && python check_plain_japanese.py guide-entry-<slug>.html; echo EXIT=$?`。EXIT=1 なら指摘の箇所の言葉だけを直して再実行（最大5回・数字と出典は変えない）。5回で緑にならなければ手順9。
6. 【コンプラ自動公開ゲート】Agentツールで **model=opus** のサブエージェント（Read,Edit・`.claude/agents/compliance-reviewer.md` ペルソナ）に監査させる：①黒/グレー/白 ②グレーは軽微修正（表現の軟化・注記/免責の追加・研究の対象市場の明記のみ／数字・出典・SVG・構造は不変）をEditで適用 ③適用後に再読し最終判定 ④黒 or 要協議なら編集せず「エスカレ」。返り値＝【初期/適用修正/最終】。
   - 指示に必ず含める：「研究の数字を実際より強く読ませる書き方（例：『すべての市場で確かめた』『どの10年でも』のような拡大）」と「当サイトのシグナルを研究で裏づけたように読める書き方」を重点的に見ること。
7. 【品質ルーブリック】`QUALITY_RUBRIC.md` の観点で自己採点。⚠️は表現・構成・補足1文だけで自己修正（数値/SVG/主張/免責は不変）、❌は手順9。
8. **公開判定と公開**：初期=白 もしくは（グレー→opus軽微修正→最終=白）かつ ルーブリック合格 のときだけ。さらに別の fresh な **model=opus** サブエージェント（Readのみ・同ペルソナ）で「そのまま公開して白か」を独立確認。白でなければ手順9。
   - 決定論チェック（全て満たす）：① `git checkout -- check_guide_draft.py && python check_guide_draft.py guide-entry-<slug>.html` が GREEN ② `python check_plain_japanese.py guide-entry-<slug>.html` が指摘0件 ③禁止語なし（必ず/絶対/確実/100%/儲かる/一択/今すぐ買い）④特定銘柄・証券会社の推奨なし ⑤出典一覧のリンクがある。
   - a. `python publish_article.py --file guide-entry-<slug>.html --category "エントリー方法の研究" --emoji <キューの絵文字> --card-title "<短い題>" --desc "<1行説明>"`
   - b. `python check_site_consistency.py; echo EXIT=$?`（赤なら中止しエスカレ）
   - c. `git add guide-entry-<slug>.html guides.html generate_market_news.py sync_to_github.py drafts/ && git commit -m "feat: エントリー方法の研究 auto-publish <slug>"` → push（下の PUSH 手順）
   - d. `drafts/entry/ENTRY_LEDGER.md` に「✅公開済み・#NN・題材・slug・コンプラ判定（初期/適用修正/独立確認）・確かめた出典のURL」を追記しコミット＆push。
9. **エスカレ（公開しない）**：記事を `drafts/entry/draft-<slug>.html` に `noindex,nofollow` 付きで保存し、`ENTRY_LEDGER.md` に理由を記録してコミット＆push。

   | 印 | どんなとき | 次回の扱い |
   |---|---|---|
   | **`🔁再試行可`** | 出典に届かなかった（経路遮断）、一時的なエラー、API不調、やさしい日本語の検査が5回で緑にならない | **同じ題材をもう一度選ぶ** |
   | **`🚩要人間レビュー`** | コンプラ🔴黒・要協議・品質❌・事実が確定しない・先方のbot判定 | **選び直さない**（人の判断を待つ）。翌日は次の題材へ |

   ⚠️ どちらか迷ったら `🔁再試行可`。🔴黒と判定した本文はリポジトリにコミットしない（public リポジトリは raw で誰でも読める）＝台帳に日付・対象・理由の要約だけ書く。
10. 最後に日本語要約：選んだ題材・出典の到達可否・やさしい日本語の検査（初回の指摘数→最終）・コンプラ判定・公開有無・ファイル名。

**PUSH 手順**：`git fetch origin main && git rebase origin/main && git push origin HEAD:main` を成功まで最大5回（各回15秒あけ、rebase 衝突時は `git rebase --abort` してからやり直す）。5回とも失敗したら `git push origin HEAD:refs/heads/entry-pending-<UTC日時>` に退避し、台帳に「🚩 main push 失敗」を記録。

## 3. 絶対厳守

- **1日1本まで**（当日分の `guide-entry-*.html` が既にあれば何もしない）。
- **研究の数字は、実際に見た出典からだけ**（§0-A）。確かめられない数字は書かない。
- **広告を入れない**（`inject_ads.py` が除外済み。本文にも広告・アフィリエイトリンクを書かない。テンプレには Google AdSense の読み込みも無い＝**足さない**。2026-09-25 オーナー指示「広告はなしでいいです」）。
- 6コアHTML（index/calendar/charts/vix/market-health/hot-assets）・political-feed・track-record・sitemap.xml に直接触れない。
- 発火エンジン(`generate_technical_alerts.py`)・signal_lab系・固定オラクル(`signal_lab_verify.py`/`exit_lab_verify.py`/`check_site_consistency.py`/`check_guide_draft.py`/`check_plain_japanese.py`/`publish_article.py`)は**書き換えない（実行はOK）**。
- 推奨・利益示唆・断定（必ず/絶対/保証/儲かる/一択）禁止。**情報提供であり投資助言ではない。**
- 少しでもエラー・事実未確定・コンプラの迷いがあれば**公開せずエスカレ（安全側）**。

## 4. 完結のしかた（先に決めておく）

- キューは **全25回＋総まとめ1回**。総まとめ（`series-index`）を公開したらシリーズは完結。台帳に「🔚完結」と書き、以後は毎日「完結済み・何もしない」で終わる。
- 完結したら人（またはセッションの Claude）が：① `check_automation_health.py` の `QUEUE_LANES` から外す ② routine `entry-daily-auto` を停止する ③本手順書の冒頭に完結の記録を書く（東証・詐欺・格言のレーンと同じ畳み方）。
- 題材を足すときは、下の表に行を足すだけでよい（番号は続きから・総まとめは最後に移す）。

---

## 【キュー】エントリー方法の研究（上から順に消化）

| # | 題材 | slug | 絵文字 | 芯（何を深掘りするか） | 主な研究（出典の手がかり） | 接続先ガイド |
|---|---|---|---|---|---|---|
| 1 | トレンドフォロー（時系列モメンタム） | trend-following | 🧭 | **芯＝その銘柄自身の過去と比べる。**過去1〜12か月の向きに乗る考え方・何か月で見るか・もみ合いで損が続く構造 | Moskowitz, Ooi & Pedersen (2012) JFE／Hurst, Ooi & Pedersen (2017) JPM／反論 Huang, Li, Wang & Zhou (2020) JFE | masters-002-trend / proverb-trend-is-your-friend |
| 2 | 高値・安値のブレイク | breakout | ⛰ | **芯＝一定期間の高値を抜けたら入る。**考え方と「だまし」・研究で効いた時代と効かなくなった時代 | Brock, Lakonishok & LeBaron (1992) JF／Sullivan, Timmermann & White (1999) JF | signal-anatomy / indicator-combos |
| 3 | 移動平均線の交差 | ma-crossover-rules | 〰 | **芯＝遅れて出ることを受け入れる方法。**短い線と長い線・研究の結果・データを何度も試すと良く見える問題。⚠️ 既存 `guide-moving-average.html`（線の読み方）と重ねない＝**交差で売買するルールの研究の側** | Brock ほか (1992)／Sullivan ほか (1999)／Park & Irwin (2007) J. Economic Surveys | moving-average / indicator-combos |
| 4 | RSI・MACDなど指標のシグナル | technical-indicators | 📐 | **芯＝為替では研究が多い。**テクニカル分析の研究のまとめ（肯定的な結果の数と、その読み方） | Park & Irwin (2007)／Menkhoff & Taylor (2007) J. Economic Literature | indicator-combos / signal-anatomy |
| 5 | 相対的な強さ（クロスセクション・モメンタム） | cross-sectional-momentum | 🏃 | **芯＝ほかの銘柄と比べる。**①との違い・3〜12か月・株以外での研究 | Jegadeesh & Titman (1993) JF／Asness, Moskowitz & Pedersen (2013) JF（要旨で確認） | masters-006-dual-momentum |
| 6 | モメンタムの急な反転 | momentum-crash | 💥 | **芯＝強いものを買う方法が大きく負ける場面。**下げたあとの急反発で何が起きるか | Daniel & Moskowitz (2016) JFE | position-sizing |
| 7 | 短期の逆張り | short-term-reversal | ↩️ | **芯＝行き過ぎの戻り。**週・月単位の反転・取引コストで消えるかどうか | Jegadeesh (1990) JF／Lehmann (1990) QJE | proverb（逆張り系があれば）/ bid-ask-spread |
| 8 | 金利の差（キャリー） | carry-trade | 💱 | **芯＝少しずつもうかり、ときどき急に負ける形。**研究の証拠と急落の構造。⚠️ 既存 `guide-yen-carry-trade.html`（円キャリーの仕組み・規模）と重ねない＝**研究の結果と急落の起き方**に絞る | Koijen, Moskowitz, Pedersen & Vrugt (2018) JFE／Brunnermeier, Nagel & Pedersen (2008) NBER Macro Annual／Lustig, Roussanov & Verdelhan (2011) RFS | yen-carry-trade |
| 9 | FOMC前の値動き | pre-fomc | 🏦 | **芯＝見つかった傾向が、あとで消えた例。**発表前24時間の上昇と、2015年以降に弱まったこと・その理由の説明 | Lucca & Moench (2015) JF／Kurov, Wolfe & Gilbert (2021) FRL | fomc |
| 10 | 月末・月初（月替わり） | turn-of-month | 📆 | **芯＝お金が入るタイミング。**月替わりにリターンが集まるという研究と、その説明。⚠️ 既存 `guide-sell-in-may.html` と重ねない（季節ではなく月の中の日付） | Ariel (1987) JFE／Lakonishok & Smidt (1988) RFS | sell-in-may |
| 11 | 曜日の傾向 | day-of-week | 🗓 | **芯＝有名になったあとの曜日効果。**月曜の傾向の研究と、その後の検証 | French (1980) JFE（要旨で確認）ほか | market-hours / sell-in-may |
| 12 | 夜と昼（取引時間の外と中） | overnight-intraday | 🌙 | **芯＝もうけが出る時間帯は、方法によって違う。**夜のあいだと取引時間中のリターンの研究 | Lou, Polk & Skouras (2019) JFE | overnight-gap-risk / market-hours |
| 13 | 決算発表後のドリフト | earnings-drift | 📊 | **芯＝良い決算のあと、値動きがじわじわ続くという研究。**個別株の研究であること（株価指数・FX・商品には当てはまらない）を明記 | Ball & Brown (1968) JAR／Bernard & Thomas (1989) JAR | earnings-season |
| 14 | 経済指標のサプライズ | macro-surprise | 📰 | **芯＝反応するのは「予想とのずれ」。**反応の速さと大きさ・悪い結果のほうが大きく動く・発表直後のコスト | Andersen, Bollerslev, Diebold & Vega (2003) AER | economic-indicators-basics / fomc |
| 15 | 大口投機筋の持ち高（COTレポート） | cot-report | 🐂 | **芯＝「かたよったら逆」は研究で支持されていない。**大口の投機筋・ヘッジ目的の参加者・小口の違い。⚠️ 研究は米国の農産物の先物が中心であることを明記 | Wang (2001) J. Futures Markets／Wang (2003) | market-participants |
| 16 | 投資家心理の指標 | investor-sentiment | 🌡 | **芯＝心理の指標は、何を予測するのか。**株の銘柄の違いを説明する研究・個人FXの売り買い比率は研究が乏しいこと（正直に書く） | Baker & Wurgler (2006) JF | fear-greed |
| 17 | 値動きの荒さで量を変える | volatility-scaling | 🌊 | **芯＝「いつ入るか」ではなく「どれだけ入るか」。**荒れているときに量を減らす研究と反論・VIXが跳ねたあとの研究の弱さ | Moreira & Muir (2017) JF／Cederburg, O'Doherty, Wang & Yan (2020) JFE／Giot (2005) JPM | position-sizing / vix |
| 18 | ローソク足の形は効くのか | candlestick-research | 🕯 | **芯＝形の名前より、研究の結果。**米国株での検証結果と、ほかの市場での研究の有無。⚠️ 既存 `guide-candlestick-basics.html`（読み方）と重ねない＝**研究の側** | Marshall, Young & Rose (2006) JBF | candlestick-basics |
| 19 | チャートパターン | chart-patterns | 📉 | **芯＝形を機械で見つけると何がわかるか。**ヘッドアンドショルダーなどを自動で見つけた研究 | Lo, Mamaysky & Wang (2000) JF／Osler & Chang（ニューヨーク連銀・要旨で確認） | candlestick-basics / cognitive-biases |
| 20 | 支持線・抵抗線 | support-resistance | 🧱 | **芯＝何度も止められた値段に、注文は集まるのか。**銀行が公表した節目の研究 | Osler (2000) FRBNY Economic Policy Review | fibonacci |
| 21 | キリのいい値段 | round-numbers | 🔢 | **芯＝利益確定と損切りの注文は、キリ番に集まる。**注文の集まり方と、節目を抜けたあとの動き | Osler (2003) JF | fibonacci / order-types |
| 22 | 指値と成行 | limit-vs-market | 📝 | **芯＝指値は「不利なときほど約定しやすい」。**指値の逆選択の研究・過去データで指値を試すときの落とし穴 | Linnainmaa (2010) JF | order-types / bid-ask-spread |
| 23 | 通貨の時間帯 | fx-trading-hours | 🌏 | **芯＝通貨は自国の取引時間中に下がりやすい、という研究。**その説明（その国の参加者の売買のかたより） | Breedon & Ranaldo (2013) JMCB | market-hours |
| 24 | 東京の仲値（9時55分） | tokyo-fix | 🕘 | **芯＝決まった時刻に、注文がかたよって集まる。**仲値の仕組みと研究・ゴトー日は原文で確かめられた範囲だけ書く | Ito & Yamada (2017) J. International Economics | bid-ask-spread / market-hours |
| 25 | 「過去に効いた」をどう疑うか | publication-decay | 🔍 | **芯＝論文の数字は、発表後に縮む。**期間の外・発表後に弱まる研究・たくさん試すと偶然が混じる問題。シリーズ全体の読み方の回 | McLean & Pontiff (2016) JF／Sullivan ほか (1999)／Harvey, Liu & Zhu (2016) RFS（要旨で確認） | signal-anatomy |
| 26 | 総まとめ（全25回の総目次） | series-index | 📚 | **芯＝25の入り方を、研究の強さ・調べた市場・反論の有無で一覧にする。**各回へのリンク。「どれが正解か」は書かない。公開したらシリーズ完結（§4） | 各回の出典 | 各回 |
