# 🤖 AUTODRAFT REVIEW ノート（最新が上）

---

## 2026-06-23 | 📋 autodraft-article ルーティン実行 — 全topic下書き済み

- **基準日（JST）**: 2026-06-23（UTC 2026-06-22 20:32）
- **結果**: キュー全11トピックが「ドラフト済みまたは公開済み」のため新規下書き生成なし
- **下書き済み（drafts/draft-\<key\>.html 存在）**: position-sizing / trading-psychology-calm / risk-reward / trading-journal / leverage / dollar-cost-averaging / swap-points（7件）
- **公開済み（guides.html 掲載）**: 上記7件 + profit-taking / compounding-drawdown / cognitive-biases / diversification（計11件全て公開）
- **空コミットなし**: REVIEW.md 更新のみコミット
- **人間の残作業**: topicキューに新テーマを追加するか、既存下書きの公開作業を継続

---

## 2026-06-22 | 🧪 signal-lab #017 ゲート実行中

- **基準日（JST）**: 2026-06-22
- **採択仮説**: 「blocked=True（壁あり）シグナルはロングとショートで異なる勝率を示す（方向性分解）」（#5以降の継続研究・スイープ昇格/反証なし→シリーズ継続）
- **事前宣言**: blocked=True×Short の勝率が blocked=True×Long より 10pp 以上高い
- **検証データ**: 全決済済み883件（signals-log.json）。blocked×direction クロス集計＋signal種別探索的分析
- **結果**: blocked=True×Short=55.9%(19/34) CI[39.5%,71.1%] vs blocked=True×Long=40.9%(18/44)。差=15.0pp（宣言条件10pp超クリア）。CI下限39.5%<43%・FDR未通過（q=0.331）→ **通過A方向（確定打なし・継続観察）**。探索的: ma_dead×short×blocked=True=90.9%(10/11)はN小さすぎ
- **生成ファイル**: drafts/draft-signal-lab-017.html / drafts/labnotes/lab-017-analysis.md / drafts/labnotes/lab-017-claims.json / drafts/labnotes/sweep-2026-06-22.json / signal-lab-ledger.md

### 自動公開ゲート結果
- [x] 8-1 git commit/push ✅（chore: signal-lab draft 017 + claims）
- [x] 8-2 verify EXIT=0 ✅ — 8/8クレーム緑・要約未検証0件・SVG警告0件
- [x] 8-3 Opus compliance 🟡 グレー → 修正適用 → 最終判定=白 — H1見出しの「稼いで」→「勝率が高め」に軟化＋過去データ・将来非保証注記追記。数値・SVG・30秒まとめ不変
- [x] 8-4-i 数値再検証 EXIT=0 ✅（Opus修正後も8/8クレーム緑・数値変化なし確認）
- [x] 8-4-ii 独立確認Opus 🟢 白 ✅（kinsho-v1×2箇所・断定表現なし・将来非保証・投資助言・推奨なし 全確認）
- [x] ✅ 自動公開済み（検証緑・初期グレー→Opus修正適用→修正後白・独立確認=白）| guide-signal-lab-017.html

---

## 2026-06-21 | 🧪 signal-lab #016 ゲート実行中

- **基準日（JST）**: 2026-06-21
- **採択仮説**: 「ドル建てFXクロス（other_fx）のロングは損益分岐点43%を系統的に下回るか」（スイープFDR通過候補 q=0.046）
- **事前宣言**: CI上限<43%かつN≥100 で「棄却確認（通過A）」
- **検証データ**: 全決済済み883件（signals-log.json）。other_fx×long/short × トレンド別クロス集計
- **結果**: other_fx×L=33.0%(63/191) CI[26.7%,39.9%]・CI上限39.9%<43% → **棄却確定（通過A）**。上昇×ロング9.8%(N=41)の逆説。ショート54.1%(N=74)との方向非対称。jpy_fxとの優位性逆転。E(R)=-0.231 CI[-0.387〜-0.076]
- **生成ファイル**: drafts/draft-signal-lab-016.html / drafts/labnotes/lab-016-analysis.md / drafts/labnotes/lab-016-claims.json / drafts/labnotes/sweep-2026-06-21.json / signal-lab-ledger.md

### 自動公開ゲート結果
- [x] 8-1 git commit/push ✅（chore: signal-lab draft 016 + claims）
- [x] 8-2 verify EXIT=0 ✅ — 10/10クレーム緑・要約未検証0件・SVG警告0件
- [x] 8-3 Opus compliance 🟡 グレー → 修正適用 → 最終判定=白 — 「30秒まとめ③: 損益分岐を超える可能性」を「過去データ上はロングとショートで優位性が真逆に分かれていた（将来非保証）」に軟化。数値・SVG不変
- [x] 8-4-i 数値再検証 EXIT=0 ✅（Opus修正後も全10クレーム緑・数値変化なし確認）
- [x] 8-4-ii 独立確認Opus 🟢 白 ✅（kinsho-v1×3箇所・断定表現なし・将来非保証・投資助言・推奨なし 全確認）
- [x] ✅ 自動公開済み（検証緑・初期グレー→Opus修正適用→修正後白・独立確認=白）| guide-signal-lab-016.html

---

## 2026-06-20 | 🧪 signal-lab #015 ゲート実行中

- **基準日（JST）**: 2026-06-20
- **採択仮説**: 「4H足ロングシグナルは1H足ロングより系統的に勝率が低いか（時間足効果の検証）」（スイープFDR通過新候補 tf=4h×dir=long）
- **事前宣言**: 4H×L の CI 上限 < 43% → 棄却確定。金属比率差 < 5pp で交絡否定。金属除外後も差継続。jpy_fx 差 > 10pp（探索的）
- **検証データ**: 全決済済み883件（signals-log.json）。tf=4h/1h × direction×group クロス集計
- **結果**: 4H×L=35.2%(96/273) CI[29.7%,41.0%]・CI上限41.0%<43% → **棄却確定（通過A）**。金属比率差1.3pp（交絡否定）。jpy_fx×4H=29.8%(14/47) vs 1H=48.7%(37/76)が主因（18.9pp差）。4H×S=50.0%の方向非対称。tf=4h×dir=long gate新規登録
- **生成ファイル**: drafts/draft-signal-lab-015.html / drafts/labnotes/lab-015-analysis.md / drafts/labnotes/lab-015-claims.json / drafts/labnotes/sweep-2026-06-20.json / signal-lab-ledger.md

### 自動公開ゲート結果
- [x] 8-1 git commit/push ✅（chore: signal-lab draft 015 + claims）
- [x] 8-2 verify EXIT=0 ✅ — 10/10クレーム緑・要約未検証0件・SVG警告0件
- [x] 8-3 Opus compliance 🟢 白（修正なし）— 断定表現なし・kinsho-v1×2箇所・統計限界明示・将来非保証。修正不要
- [x] 8-4-i 数値再検証 EXIT=0 ✅（Opus修正なし・数値変化なし確認）
- [x] 8-4-ii 独立確認Opus 🟢 白 ✅（kinsho-v1×2・断定表現なし・将来非保証・投資助言・推奨なし 全確認）
- [x] ✅ 自動公開済み（検証緑・Opus=白・修正なし・独立確認=白）| guide-signal-lab-015.html

---

## 2026-06-20 | 全topic下書き済み（新規生成なし）

- **基準日（JST）**: 2026-06-20 05:32 JST
- **判定**: AUTODRAFT_GUIDE.md の全11 topicが「下書き済み or 公開済み」のため、本日の新規生成はなし
- **内訳**:
  - 下書きあり（drafts/draft-*.html 存在）: position-sizing / trading-psychology-calm / risk-reward / trading-journal / leverage / dollar-cost-averaging / swap-points（7件）
  - 公開済みで下書き不要: profit-taking / compounding-drawdown / cognitive-biases / diversification（4件、guides.html に guide-<key>.html が掲載済み）
- **次のアクション**: AUTODRAFT_GUIDE.md に新 topic を追加すれば次回から再稼働。人間が topicキューを拡張してください。

---

## 2026-06-19 | 🧪 signal-lab #014 ゲート実行中

- **基準日（JST）**: 2026-06-19
- **採択仮説**: 「bb_lower_touch × jpy_fx ロング の正式検証（#9探索記録の後継）」（バックログ最優先候補・verify.py対応済み）
- **事前宣言**: N≥60かつCI下限>43% → 通過A（エッジ確認）
- **検証データ**: 全決済済み866件（signals-log.json）。group=jpy_fx / direction=long / signal=bb_lower_touch
- **結果**: 60.0%(27/45) CI[45.5%~73.0%] E(R)=+0.398 CI[+0.061,+0.735]・CI下限45.5%>43% → **通過A方向（N=45<60のため途中経過）**。bb vs rsi逆転（14.3% N=21）・1h 73.3% vs 4h 33.3%の時間足差を発見。スイープ4本新候補登録
- **生成ファイル**: drafts/draft-signal-lab-014.html / drafts/labnotes/lab-014-analysis.md / drafts/labnotes/lab-014-claims.json / drafts/labnotes/sweep-2026-06-19.json / signal-lab-ledger.md

### 自動公開ゲート結果
- [x] 8-1 git commit/push ✅（chore: signal-lab draft 014 + claims）
- [x] 8-2 verify EXIT=0 ✅ — 8/8クレーム緑（ticker claimsをGBPJPY/USDJPY分追加後）・要約未検証0件・SVG警告0件。重複h2構造ミスを修正後 EXIT=0 確認
- [x] 8-3 Opus compliance 🟢 白（修正なし）— 禁止語・推奨なし・kinsho-v1×3箇所・統計限界明示・将来非保証。修正不要
- [x] 8-4-i 数値再検証 EXIT=0 ✅（Opus修正なし・h2重複修正で数値変化なし確認）
- [x] 8-4-ii 独立確認Opus 🟢 白 ✅（kinsho-v1×3・断定表現なし・将来非保証・売買推奨なし 全確認）
- [x] 公開完了 ✅自動公開済み（検証緑・Opus=白・独立確認白）
  - 適用修正: なし（Opusは白判定で修正不要。構造ミスはオーケストレーター修正=重複h2を統合）

---

## 2026-06-17 | 🧪 signal-lab #012 ゲート実行中

- **基準日（JST）**: 2026-06-17
- **採択仮説**: 「もみあい（中立・もみあい）相場×ショートシグナルの勝率は損益分岐43%を有意に上回るか」（FDRスイープ新候補・q=0.005最上位）
- **事前宣言**: N≥20 かつ CI下限 > 43% → 通過A（エッジ確認）
- **検証データ**: 全決済済み806件（signals-log.json）。trend=中立・もみあい×direction=short の集計
- **結果**: もみあい×short 33/49=67.3% CI[53.4%~78.8%] R=+0.57・CI下限53.4%>43%・N=49≥20 → **通過A（エッジ確認）**。macd_dead×もみあい×short=63.3%(N=30)。macd_dead×下降×short=21.2%(N=52)という環境依存交叉を発見。
- **生成ファイル**: drafts/draft-signal-lab-012.html / drafts/labnotes/lab-012-analysis.md / drafts/labnotes/lab-012-claims.json / drafts/labnotes/sweep-2026-06-17.json / signal-lab-ledger.md

### 自動公開ゲート結果
- [x] 8-1 git commit/push ✅
- [x] 8-2 verify EXIT=0 ✅ — 11/11クレーム緑・要約未検証0件・SVG警告0件
- [x] 8-3 Opus compliance 🟡グレー→軽微修正適用→白（30秒まとめ④の表現軟化・negative-box免責追加。数値不変）
- [x] 8-4-i 数値再検証 EXIT=0 ✅（Opus修正で数値変化なし確認）
- [x] 8-4-ii 独立確認Opus 🟢白 ✅（kinsho-v1×3・断定表現なし・将来非保証明記・売買推奨なし 全確認）
- [x] 公開完了 ✅自動公開済み（検証緑・Opus=グレー→修正適用後白・独立確認白）
  - 適用修正: ①30秒まとめ④「環境の見極めが鍵」→「相場環境によって集計結果が大きく変わった点が興味深い」②negative-box「大敗パターン」に「過去の集計上は」「過去データの傾向であり将来を示すものではありません」追記

---

## 2026-06-18 | ✅ 全topic下書き済み（新規生成なし）

- **基準日（JST）**: 2026-06-18（UTC 2026-06-17T20:32Z）
- **状況**: AUTODRAFT_GUIDE.md のtopicキュー全11件を確認。「draft無し・未公開」の topic が0件のため新規生成なし。
- **キュー完了状況**:
  - 公開済み（8件）: position-sizing / risk-reward / profit-taking / compounding-drawdown / cognitive-biases / diversification / leverage / dollar-cost-averaging
  - 下書き存在・未公開（3件）: trading-psychology-calm / trading-journal / swap-points
- **人間の残作業**: 上記3件の未公開ドラフトを compliance-reviewer(Opus)監査 → `mw publish` で公開

---

## 2026-06-16 | 🧪 signal-lab #009 ✅自動公開済み

- **基準日（JST）**: 2026-06-16
- **採択仮説**: 「jpy_fx（円クロスFX）ショートシグナルの勝率は損益分岐43%を安定的に下回るか」（3視点会議でリスクマネージャー採択。GC=F方向性交絡#004の拡張版）
- **事前宣言**: N≥20 かつ CI上限 < 43% → 棄却確認として通過A
- **検証データ**: 全決済済み722件（signals-log.json）。jpy_fx（USD/EUR/GBP/AUD × JPY）の方向別集計
- **結果**: jpy_fx ショート 8/34=23.5% CI[12.4%~40.0%] CI上限40.0%<43%・N=34≥20 → **通過A（棄却確認）**。macd_dead×jpy_fxが76.5%(26/34件)を占め主因。下降×ショートでも8.3%(1/12)という逆説。ロング42.3%(N=104)はトラッカー[m]新設・蓄積中。
- **生成ファイル**: drafts/draft-signal-lab-009.html / drafts/labnotes/lab-009-analysis.md / drafts/labnotes/lab-009-claims.json / signal-lab-ledger.md

### 自動公開ゲート結果
- [x] 8-1 git commit/push ✅（cherry-pick after rebase）
- [x] 8-2 verify EXIT=0 ✅ — 9/9クレーム緑・要約未検証0件・SVG警告0件
- [x] 8-3 Opus compliance 🟢白（修正なし。kinsho-v1×3確認、断定表現なし、将来非保証明示、探索的観察として記録）
- [x] 8-4-i 数値再検証 EXIT=0 ✅（Opus修正なし＝不変確認）
- [x] 8-4-ii 独立確認Opus 🟢白 ✅（6チェックポイント全通過。markup typo指摘→手動修正後verify再実行）
- [x] 8-4-iii 公開実行 ✅ — finalize（kinsho=6,svg=3,41KB）/guides.htmlカード追加/generate_market_news.py更新/check_site_consistency(EXIT=0,警告3件は既存問題)/commit+push

---

## 2026-06-15 | 🧪 signal-lab #008 ✅自動公開済み

- **基準日（JST）**: 2026-06-15
- **採択仮説**: 「ma_golden（MA25×MA75 ゴールデンクロス）の実勝率はCI上限が43%未満であることを確認する」（3視点会議でリスクマネージャー採択。元候補 d_sup_atr は verify.py 非対応次元のため回避）
- **事前宣言**: N≥20 かつ CI上限 < 43% → 棄却確認として通過A
- **検証データ**: 全決済済み654件（signals-log.json）。シグナル種別11種をprimary_signalフィールドで集計
- **結果**: ma_golden 7/30=23.3% CI[11.8%~40.9%] CI上限40.9%<43%・N=30≥20 → **通過A（棄却確認）**。全種別中最低・E(R)=-0.683R（最悪）。副次確認：macd_dead 45.6%(CI下限36.3%)、bb_lower_touch 43.3%。全CI下限43%超は現時点でゼロ。
- **生成ファイル**: drafts/draft-signal-lab-008.html / guide-signal-lab-008.html / drafts/labnotes/lab-008-analysis.md / drafts/labnotes/lab-008-claims.json / signal-lab-ledger.md

### 自動公開ゲート結果
- [x] 8-1 git commit/push ✅
- [x] 8-2 verify EXIT=0 ✅ — 全10クレーム緑、要約未検証0件、SVG警告0件
- [x] 8-3 Opus compliance 🟡グレー→修正適用→🟢白（適用修正: 「逆張り戦略は現データでは機能していない」→「過去の記録では損益分岐を満たせていなかった（将来の成績を示すものではない旨を併記）」に軟化。「有望な数字/有望な水準」→「相対的に高い」へ表現中立化。数値・統計・SVG・30秒まとめ不変）
- [x] 8-4-i 数値再検証 EXIT=0 ✅（Opus修正で数値・要約ボックス無変化を確認）
- [x] 8-4-ii 独立確認Opus 🟢白 ✅（kinsho-v1三点完備・noindex確認・断定表現なし・将来非保証明示・過信抑制記述適切）
- [x] 8-4-iii 公開実行 ✅ — finalize/publish_article（guides.html・更新履歴）/check_site_consistency(EXIT=0)/commit+push

---

## 2026-06-15 | 🔚 全topic下書き済み

- **基準日（JST）**: 2026-06-15
- **結果**: topicキュー全11件を確認。全て下書き済みまたは公開済みのため、新規下書きは生成しない。
- **内訳**:
  - 下書き済み（未公開→公開待ち）: なし（全て公開済み）
  - 下書き済み＋公開済み: position-sizing / trading-psychology-calm / risk-reward / trading-journal / leverage / dollar-cost-averaging / swap-points（7件）
  - 下書きなし＋公開済み: profit-taking / compounding-drawdown / cognitive-biases / diversification（4件）
- **次のアクション**: AUTODRAFT_GUIDE.md のtopicキューに新しいtopicを追加すること（人間による）。

---

## 2026-06-14 | 🧪 signal-lab #007

- **基準日（JST）**: 2026-06-14
- **採択仮説**: 「他FX×blocked=Trueの66.7%高勝率は下降トレンド偏りという交絡である——グループ×トレンド×blocked三次元解析」（3視点会議でリスク管理担当採択）
- **事前宣言**: ①他FX×blocked=T×下降 CI下限≥43% かつN≥5 AND ②他FX×blocked=T×中立<43% AND ③指数>メタル の3条件クリアで「通過A」
- **検証データ**: 全決済済み652件（blocked=T:41件 / blocked=F:285件。他FX×blocked=T=15件の内訳: 下降8/上昇3/中立4）
- **結果**: 他FX×blocked=T×下降 8/8=100.0% CI[67.6%~100.0%]、他FX×blocked=T×中立 0/4=0.0%、指数blocked=T=75.0%(6/8) vs メタル50.0%(4/8)。**事前宣言3条件クリア→通過A**。66.7%は下降偏り交絡と解明。
- **生成ファイル**: drafts/draft-signal-lab-007.html / drafts/labnotes/lab-007-analysis.md / drafts/labnotes/lab-007-claims.json / signal-lab-ledger.md（次番号008、トラッカー[k]追加）

### 自動公開ゲート結果
- [x] 8-2 verify EXIT=0 ✅ — 全10件緑（blocked/group/trend三次元クリア）、要約ボックス完全（0件未検証）、SVGはみ出しなし
- [x] 8-3 Opus compliance 🟡グレー→修正適用→🟢白（適用修正: ⑥positive-box内「強いシグナルだが」→「過去データ上は目立つ数字だが、将来の再現を示すものではないため過信は禁物。特定売買の推奨ではなく過去統計の傾向観察」に軟化＋非推奨明示）✅
- [x] 8-4-i 数値再検証 EXIT=0 ✅（Opus修正で数値・要約ボックス無変化を確認）
- [x] 8-4-ii 独立確認Opus 🟢白 ✅（断定表現なし・免責完備・小サンプル留保適切）
- [x] 8-4-iii **✅自動公開済み（検証緑・Opus修正適用＋独立確認白）** → guide-signal-lab-007.html push済み（2026-06-14）

---

## 2026-06-13 | 🧪 signal-lab #006

- **基準日（JST）**: 2026-06-13
- **採択仮説**: 「blocked=True の優位性はトレンド相場（上昇・下降）に限定され、中立・もみあいでは失われる」（3視点会議でrisk-manager採択）
- **事前宣言**: ①下降×blocked=True の Wilson CI下限 ≥ 43% AND ②中立×blocked=True の勝率 < 43% の両条件で「通過A」
- **検証データ**: 全決済済み652件（sr_runwayあり326件、blocked=T:41件＝上昇11/下降20/中立10、blocked=F:285件）
- **結果**: blocked=T 上昇63.6% / 下降65.0% CI[43.3〜81.9%] / 中立20.0%。**事前宣言2条件ともクリア→通過A**。他FX×blocked=T 66.7%(N=15)も有望。
- **生成ファイル**: drafts/draft-signal-lab-006.html / drafts/labnotes/lab-006-analysis.md / drafts/labnotes/lab-006-claims.json / signal-lab-ledger.md（次番号007、トラッカーi/j追加）

### 自動公開ゲート結果
- [x] 8-2 verify EXIT=0 ✅ — 全10件緑、要約ボックス完全（0件未検証）、SVGはみ出しなし
- [x] 8-3 Opus compliance 🟡グレー→修正適用→🟢白（適用修正: 期待値表「意味」欄を「過去データ集計値（将来を示さない）」に軟化、決定事項の「推奨候補」→「検証候補として記録（投資判断の推奨ではない）」）✅
- [x] 8-4-i 数値再検証 EXIT=0 ✅（Opus修正で数値・要約ボックス無変化を確認）
- [x] 8-4-ii 独立確認Opus 🟢白 ✅
- [x] 8-4-iii **✅自動公開済み（検証緑・Opus修正適用＋独立確認白）** → guide-signal-lab-006.html push済み（2026-06-13）

---

## 2026-06-13 | 🧪 signal-lab #005

- **基準日（JST）**: 2026-06-13
- **採択仮説**: 「veto_runway_blocked効果の追試——TP1前の壁ありシグナルは本当に不利か」（3視点会議でリスクマネージャー採択）
- **事前宣言**: 通過A=blocked=True 勝率≥43% かつ CI下限≥30% かつ N≥30 / 通過B=差≥10pp かつ blocked=F N≥100 / 棄却=その他
- **検証データ**: 全決済済み652件（sr_runwayあり326件、blocked=T:41件 / blocked=F:285件）
- **結果**: blocked=True 22/41=53.7% CI[38.7%〜67.9%] / blocked=False 111/285=38.9%。**通過A達成**。ALL blocked=TがavoidティアでもE(R)=+0.252R。CI下限38.7%<43%で統計確定不足→継続観察
- **生成ファイル**: draft-signal-lab-005.html / lab-005-analysis.md / lab-005-claims.json / ledger更新 / verify.py blocked拡張

### 自動公開ゲート結果
- [x] 8-2 verify EXIT=0 ✅ — 全7件緑、要約ボックス完全、SVGはみ出しなし
- [x] 8-3 Opus compliance 🟢 白（グレー指摘ゼロ）✅
- [x] 8-4 **✅自動公開済み（検証緑・Opus白）** → guide-signal-lab-005.html push済み（2026-06-13）

---

## 2026-06-12 | 🧪 signal-lab #004

- **基準日（JST）**: 2026-06-12（UTC 2026-06-12T22:59）
- **採択仮説**: 「GC=F のロング vs ショートの交絡解明（事前宣言: ショートは下降トレンド環境でCI下限43%超）」
- **検証データ**: GC=F 決済済み65件（2026-05-20〜06-12）
- **結果**: ロング12.8% CI[6.0%〜25.2%] vs ショート61.1% CI[38.6%〜79.7%]（差48pp）。根本原因は42/47件が下降中の逆張りロング（11.9%）。事前宣言仮説：ショート×下降57.1%（N=14）だがCI下限32.6%＜43%で**未達（件数不足）**。SI=Fも同方向（ロング7.7% vs ショート40.0%）
- **生成ファイル**:
  - `drafts/draft-signal-lab-004.html`（下書き記事）
  - `drafts/labnotes/lab-004-analysis.md`（検証ログ・数字照合用）
  - `signal-lab-ledger.md`（#004記録、次番号=005）

### 人間の残作業
- [ ] `drafts/labnotes/lab-004-analysis.md` と記事の数字を照合（GC=F ロング6/47・ショート11/18・ショート×下降8/14・ロング1h 1/28・ロング4h 5/19）
- [ ] SVG図2点（棒グラフ・イメージ図）の実機表示確認（ライト/ダーク両モード）
- [ ] compliance-reviewer（Opus）による法務監査
- [ ] 公開判断（人間による最終GO/NOGO）
- [ ] 公開する場合: `python mw.py publish --file guide-signal-lab-004.html --category "🧪 AIシグナル研究日誌" --emoji 🧪 --card-title "研究日誌 #4 ゴールドはロングだと9割負ける——方向性の罠を解剖" --desc "GC=Fロング12.8% vs ショート61.1%の謎を65件で解剖。根本原因は下降中の逆張りロング大量発火。"`

---

## 2026-06-12 | 🔁 全topic下書き済み／公開済み

- **基準日（JST）**: 2026-06-12
- **結果**: AUTODRAFT_GUIDE.md の全11topic（position-sizing / trading-psychology-calm / risk-reward / profit-taking / compounding-drawdown / cognitive-biases / diversification / trading-journal / leverage / dollar-cost-averaging / swap-points）が「drafts/draft-\*.html 存在」または「guides.html 公開済み」のいずれかに該当。新規下書き生成は行わない（空コミットしない）。
- **次アクション**: topicキューに新topic追加が必要。AUTODRAFT_GUIDE.md を更新すること。

---

## 2026-06-12 | 🧪 signal-lab #003

- **基準日（JST）**: 2026-06-12（UTC 2026-06-11T21:10）
- **仮説**: 「金銀（メタル）の逆張りシグナルは切り番（50ドル刻み）近傍で勝率が上がる」
- **検証データ**: 決済済み628件（2026-05-20〜06-12）
- **結果**: 主仮説❌棄却（切り番近傍16.7% vs 遠い5.9%、どちらも43%に全く届かず）。副産物: GC=Fロング12.8% vs ショート61.1%（方向の交絡）を発見。指数×逆張り52.3% CI[40.4〜64.0%]・他FX×逆張り54.2% CI[41.7〜66.3%] を継続観察トラッカーに追加
- **生成ファイル**:
  - `drafts/draft-signal-lab-003.html`（下書き記事）
  - `drafts/labnotes/lab-003-analysis.md`（検証ログ・数字照合用）
  - `signal-lab-ledger.md`（台帳初期化 + #003記録、次番号=004）

### 人間の残作業
- [ ] `drafts/labnotes/lab-003-analysis.md` と記事の数字を照合（GC=Fロング/ショート N=47/18、メタル切り番近傍N=36/遠いN=17等）
- [ ] SVG図4点の実機表示確認（ライト/ダーク両モード）
- [ ] compliance-reviewer（Opus）による法務監査
- [ ] 公開判断（人間による最終GO/NOGO）
- [ ] 公開する場合: `python mw.py publish --file guide-signal-lab-003.html --category "🧪 AIシグナル研究日誌" --emoji 🧪 --card-title "研究日誌 #3 切り番は空振り、でも方向の交絡を発見" --desc "切り番フィルタは棄却。GC=Fロング12.8%vsショート61.1%の方向差とグループ差を解明。"`

---

## 2026-06-12 | swap-points

- **基準日（JST）**: 2026-06-12（UTC 2026-06-11T20:32:45Z）
- **Topic**: スワップポイント（スワップ金利）の仕組み（FXの金利差収益）
- **Key**: `swap-points`
- **生成ファイル**: `drafts/draft-swap-points.html`
- **シリーズ**: 💰 投資の基礎知識（guides.html 既存カテゴリ）

### 参照出典 URL
| 項目 | 出典 |
|---|---|
| スワップポイントの仕組み・付与タイミング（外為どっとコム） | https://www.gaitame.com/beginner/fx/swap.html |
| スワップポイントとは（みんなのFX） | https://min-fx.jp/start/aboutswap/ |
| スワップポイントの仕組み・計算方法（松井証券） | https://www.matsui.co.jp/fx/study/article/glossary/swap/ |
| FXマイナススワップとは（インヴァストNAVI） | https://www.invast.jp/blogs/fx-negative-swap/ |
| スワップポイントの仕組み（DMM FX） | https://fx.dmm.com/fx/aboutfx/swappoint/ |
| スワップポイントの魅力と活用方法（三菱UFJ eスマート証券） | https://kabu.com/company/lp/fx/swap.html |
| スワップ金利生活のリスク（SMBC日興証券） | https://www.smbcnikko.co.jp/products/fx/knowledge/006.html |
| スワップポイント・キャリートレード（OANDA Japan） | https://www.oanda.jp/lab-education/beginners/aboutfx/swap/ |

### 自己コンプライアンスチェック結果
| チェック項目 | 結果 |
|---|---|
| 個別銘柄の売買推奨なし | ✅ 教育・一般論のみ。「今 AUD/JPY を買え」等の売買推奨表現なし。通貨ペアは例示・説明目的のみ |
| 断定・利益保証表現なし | ✅「絶対」「必ず」「100%」「保証」「儲かる」「一択」使用なし。「〜になりえます」「〜する可能性があります」「〜が大切です」等の慎重な表現を使用 |
| kinsho-v1 免責（冒頭バナー＋本文末＋footer）あり | ✅ 3箇所に `data-disclaimer="kinsho-v1"` または同等の文言を配置 |
| noindex,nofollow あり | ✅ `<meta name="robots" content="noindex,nofollow">` を head に配置済み |
| 出典の妥当性 | ✅ スワップポイントの仕組み（政策金利差・三倍デー・マイナススワップ）は複数の国内FX会社の公開コンテンツで確認。三倍デーが「水曜が一般的」と説明しつつ「FX会社によって異なる」と明記。新興国通貨のリスクの高さは複数の金融機関が説明する一般的知識として言及し、断定を避けた表現を使用。不確実な具体的数値（「〇%のリターン」等）は使用していない |
| SVG 概念図に「※ 概念を示すイメージ図です」の注記 | ✅ 全 3 点の figcaption に注記あり |

### SVG 図の構成
1. **政策金利差とスワップポイントの仕組み概念図**（高金利国バー・低金利国バー・差額→スワップ受け取り矢印）— 実装済み
2. **三倍デー（水曜）のカレンダー概念図**（月〜金の曜日セル、水曜のみ×3強調）— 実装済み
3. **スワップ収益積み上がりと為替差損の対比折れ線図**（緑=スワップ収益ゆるやか上昇、赤=為替差損急落）— 実装済み

### 人間の残作業
- [ ] **SVG の実機ライト/ダーク確認**：追加クラス `.s-bar-h`（高金利バー緑）・`.s-bar-l`（低金利バー青）・`.s-bar-diff`（差額黄）・`.s-bar-neg`（支払い赤）・`.s-swap-line`（スワップ収益緑線）・`.s-fx-line`（為替差損赤線）・`.s-cal-box`（カレンダー通常セル）・`.s-cal-3x`（三倍デーセル黄）をライト・ダークモードで目視確認。特に三倍デーの黄色ボックスがダークモードで背景に埋まらないか確認
- [ ] **Opus compliance-reviewer 監査**：公開前に `compliance-reviewer` エージェント（Opus）に下書き全文を渡してレビューを依頼。特に「為替差損がスワップを食い潰す」セクションの表現（特定通貨ペアへの言及・強制ロスカットの説明）が問題ないか確認
- [ ] **タイトル微調整**：現タイトルは適切。「スワップポイントとは」でも流入可能。公開時に head titleと h1 の文字数バランスを調整
- [ ] **関連記事リンクの確認**：`guide-yen-carry-trade.html`（公開準備中と本文に明記済み）・`guide-position-sizing.html`（公開済み ✓）・`guide-loss-cut.html`（公開済み ✓）。`guide-yen-carry-trade.html` は公開時に有効なリンクになっているか確認
- [ ] **三倍デー水曜説の最終確認**：「多くのFX会社では水曜」と記載。公開前に代表的なFX会社（外為どっとコム・DMM FX等）の最新情報で確認し、変化があれば表現を調整

---

## 2026-06-11 | dollar-cost-averaging

- **基準日（JST）**: 2026-06-11（UTC 2026-06-10T20:33:11Z）
- **Topic**: ドルコスト平均法とは（積立の時間分散・メリットと限界）
- **Key**: `dollar-cost-averaging`
- **生成ファイル**: `drafts/draft-dollar-cost-averaging.html`
- **シリーズ**: 💰 投資の基礎知識（guides.html 既存カテゴリ）

### 参照出典 URL
| 項目 | 出典 |
|---|---|
| ドルコスト平均法の仕組み・計算（ソニー生命） | https://www.sonylife.co.jp/land/shisan-keisei/article/dollar-cost-averaging/ |
| 調和平均・定額購入の数学的根拠（Wikipedia） | https://ja.wikipedia.org/wiki/%E3%83%89%E3%83%AB%E3%83%BB%E3%82%B3%E3%82%B9%E3%83%88%E5%B9%B3%E5%9D%87%E6%B3%95 |
| 平均購入単価の考え方（松井証券） | https://www.matsui.co.jp/fund/column/dollar-cost-2025/ |
| Vanguard 2012 研究（一括 vs DCA）| https://pwlcapital.com/wp-content/uploads/2024/08/Dollar-Cost-Averaging-vs-Lump-Sum-Investing.pdf |
| Northwestern Mutual 一括 vs DCA データ | https://www.northwesternmutual.com/life-and-money/is-dollar-cost-averaging-better-than-lump-sum-investing/ |
| Morgan Stanley 一括 vs DCA 分析 | https://www.morganstanley.com/articles/dollar-cost-averaging-lump-sum-investing |
| ドルコスト平均法 出口戦略・やめ時（楽天証券） | https://www.rakuten-sec.co.jp/web/rfund/followup/newsletter/20220824.html |
| 下落相場でやめてしまう罠（三菱UFJ銀行） | https://www.bk.mufg.jp/column/shisan_unyo/0022.html |

### 自己コンプライアンスチェック結果
| チェック項目 | 結果 |
|---|---|
| 個別銘柄の売買推奨なし | ✅ 教育・一般論のみ。「今 ○○ を買え」等の表現なし |
| 断定・利益保証表現なし | ✅「絶対」「必ず」「100%」「保証」「儲かる」「一択」使用なし。「約67%」「約2.3ポイント」はVanguard研究から引用し出典明記。「かもしれません」「ことがあります」「見込まれます」「整理」等の慎重表現を使用 |
| kinsho-v1 免責（冒頭バナー＋本文末＋footer）あり | ✅ 3箇所に data-disclaimer="kinsho-v1" または同等の文言を配置 |
| noindex,nofollow あり | ✅ `<meta name="robots" content="noindex,nofollow">` を head に配置済み |
| 出典の妥当性 | ✅ 調和平均の数学的定理（相加平均≧調和平均）は確立された数学の事実。Vanguard 2012研究は実在する研究で複数の金融機関が引用する信頼性の高いデータ。計算例（100口/200口/50口の例）は算術的に正確で自己計算値として明示。不確実な具体的数値（「積立すると○%必ず増える」等）は使用していない |
| SVG 概念図に「※ 概念を示すイメージ図です」の注記 | ✅ 実装した 2 点の figcaption に注記あり |

### SVG 図の構成
1. **購入口数と価格変動の関係図**（3カ月の価格バー・口数棒グラフ・DCA平均単価線 vs 単純平均線の対比）— 実装済み
2. **一括投資 vs ドルコスト平均法の資産成長イメージ**（右肩上がり相場での2本の曲線比較）— 実装済み
3. `<!-- TODO(SVG): 「下落相場でやめる vs 継続する」の資産回復パターン比較図（やめた場合の固定含み損ライン vs 継続して平均単価が改善し回復する場合の資産ライン）を要追加・要ライト/ダーク実機確認 -->`

### 人間の残作業
- [ ] **SVG の実機ライト/ダーク確認**：追加クラス `.s-curve-b`・`.s-bar-dca`・`.s-bar-lump`・`.s-avg-line`・`.s-avg-line-dca`・`.s-fill-b`・`.s-fill-g`・`.s-fill-r`・`.s-dot-b`・`.s-qty-bar` をライト・ダークモードで目視確認。特にDCA棒グラフ（青）と平均単価のオレンジ破線がダークモードで視認できるか確認
- [ ] **「下落相場でやめる vs 継続」SVGの追加**（HTML内 `TODO(SVG)` コメントを参照）：Section 6 のやめ時の罠を視覚的に示す最重要図として追加を推奨
- [ ] **Opus compliance-reviewer 監査**：公開前に `compliance-reviewer` エージェント（Opus）に下書き全文を渡してレビューを依頼。特に「Vanguard 研究の数値引用の表現」「出口戦略の書き方」が投資助言にならないか確認
- [ ] **タイトル微調整**：現タイトルは長め。「ドルコスト平均法とは｜仕組み・一括投資比較・やめ時の罠」等への短縮を検討
- [ ] **関連記事リンクの確認**：`guide-loss-cut.html`・`guide-position-sizing.html`・`guide-compounding-drawdown.html` はすべて公開済みのため、本文内リンクは有効 ✓
- [ ] **積立NISA・iDeCoへの言及確認**：本文中で「積立NISA・iDeCoの普及」と書いているが、制度の説明は最小限に留めた。公開時に読者の多くがNISA文脈で読むことを想定し、イントロの表現を調整することを検討

---

## 2026-06-09 | leverage

- **基準日（JST）**: 2026-06-09（UTC 2026-06-09）
- **Topic**: レバレッジとナンピンの正体（強制ロスカット・証拠金・なぜナンピンが資産を溶かすか）
- **Key**: `leverage`
- **生成ファイル**: `drafts/draft-leverage.html`
- **シリーズ**: 🛡️ リスク管理・資金管理（guides.html 既存カテゴリ）

### 参照出典 URL
| 項目 | 出典 |
|---|---|
| 証拠金維持率・ロスカットの仕組み（楽天カード・マネ活） | https://www.rakuten-card.co.jp/minna-money/securities/investment_other/article_2111_00001/ |
| FXロスカット解説（DMM FX） | https://fx.dmm.com/fx/aboutfx/losscut/ |
| 強制決済・マージンコール（IG証券） | https://www.ig.com/jp/our-charges/margin-calls |
| GMOクリック証券 ロスカット説明 | https://www.click-sec.com/corp/guide/fxneo/column/losscut-difference/ |
| ナンピンのリスク解説（元証券ディーラー） | https://official.gfs.tokyo/blog/stock-investment-nampin |
| ナンピン解説（松井証券） | https://www.matsui.co.jp/stock/study/article/nanpin/ |
| 「下手なナンピン、スカンピン」解説（楽天証券トウシル） | https://media.rakuten-sec.net/articles/-/52282 |
| ナンピンとドルコスト平均法の違い（東証マネ部） | https://money-bu-jpx.com/news/article026783/ |

### 自己コンプライアンスチェック結果
| チェック項目 | 結果 |
|---|---|
| 個別銘柄の売買推奨なし | ✅ 教育・一般論のみ。「今 ○○ を買え」等の表現なし |
| 断定・利益保証表現なし | ✅「絶対」「必ず」「100%」「保証」「儲かる」使用なし。計算例は数式の説明であり特定の結果を保証するものではないと読める文脈で使用。「理論上」「概念上」等の限定表現を使用 |
| kinsho-v1 免責（冒頭バナー＋本文末＋footer）あり | ✅ 3箇所に data-disclaimer="kinsho-v1" または同等の文言を配置 |
| noindex,nofollow あり | ✅ `<meta name="robots" content="noindex,nofollow">` を head に配置済み |
| 出典の妥当性 | ✅ 証拠金維持率の計算式（純資産÷必要証拠金×100）は業界標準の公式であり複数の国内金融機関が公開。国内FXレバレッジ最大25倍の規制は2011年施行の金融商品取引法施行令改正による事実（出典: 各証券会社の説明ページで確認可能）。ナンピンのリスクは複数の証券会社・金融メディアが説明。「下手なナンピン、スカンピン」は業界で広く使われる言葉として引用。不確実な数値（「○%改善する」等）は不使用 |
| SVG 概念図に「※ 概念を示すイメージ図です」の注記 | ✅ 全 2 点の figcaption に注記あり |

### SVG 図の構成
1. **レバレッジ倍率と逆行できる幅の反比例カーブ**（X軸=レバレッジ倍率1〜25倍, Y軸=逆行許容幅%、双曲線、5点のデータマーカー付き）— 実装済み
2. **ナンピンと価格下落時の損失拡大パターン**（価格下落ライン・ナンピン追加ポイント・平均コスト線の変化を表示）— 実装済み
3. `<!-- TODO(SVG): レバレッジ×ナンピンの維持率推移グラフ（時間経過×維持率、ナンピンのたびに維持率が急低下する様子を折れ線で表現）を要追加・要ライト/ダーク実機確認 -->`

### 人間の残作業
- [ ] **SVG の実機ライト/ダーク確認**：追加クラス `.s-curve-b`・`.s-dot-r`・`.s-dot-g`・`.s-dot-b`・`.s-bar-lev`・`.s-bar-lev-hi`・`.s-avg-line`・`.s-add-point` をライト・ダークモードで目視確認。特に反比例カーブの青色と、ナンピン図のオレンジ平均コスト線がダークモードで視認できるか確認
- [ ] **維持率推移SVGの追加**（HTML内 `TODO(SVG)` コメントを参照）：ナンピンのたびに証拠金維持率が急低下するパターンを折れ線グラフで示す
- [ ] **Opus compliance-reviewer 監査**：公開前に `compliance-reviewer` エージェント（Opus）に下書き全文を渡してレビューを依頼。特に「25倍で4%の逆行で全証拠金消滅」等の数値表現が誤解を招かないか確認
- [ ] **タイトル微調整**：「強制ロスカットを防ぐ仕組みと」の部分が長め。「レバレッジとナンピンの危険な真実」等への短縮を検討
- [ ] **関連記事リンクの確認**：`guide-loss-cut.html`・`guide-position-sizing.html`・`guide-risk-reward.html` はすべて公開済みのため、本文内リンクは有効 ✓
- [ ] **FXレバレッジ規制の最新確認**：「2011年8月施行」の記述が現時点でも正確かどうか、公開前に公式ソースで再確認

---

## 2026-06-09 | trading-journal

- **基準日（JST）**: 2026-06-09（UTC 2026-06-08T20:31:27Z）
- **Topic**: 売買日誌で自分のエッジを見つける（メタ認知・振り返りの型）
- **Key**: `trading-journal`
- **生成ファイル**: `drafts/draft-trading-journal.html`
- **シリーズ**: 🧠 投資の心理・メンタル（guides.html 既存カテゴリ）

### 参照出典 URL
| 項目 | 出典 |
|---|---|
| トレード日誌の書き方・活用法（FX Replay） | https://fxreplay.com/learn/how-to-use-a-trading-journal-to-improve-your-strategy |
| トレード心理・感情トラッキング（TradesViz） | https://www.tradesviz.com/blog/trading-journal-psychology-tracking/ |
| 売買記録の継続方法（トレーダーを赤字から安定へ、FX Replay） | https://fxreplay.com/ja/learn/the-trading-journal-routine-that-move-traders-from-loss-to-consistency |
| トレードノートの書き方・3項目（Fintokei） | https://www.fintokei.com/jp/blog/how-to-keep-trading-journal/ |
| トレードの記録をつけましょう（マーケットEYE） | https://tradeone.comtex.co.jp/market-eye/column/column(05.17).php |
| 統計的に証明できるエッジを探す実践例（note.com） | https://note.com/calm_clover830/n/n507cca5f2335 |
| Trading Journal Techniques 7 Steps（TradeFundrr） | https://tradefundrr.com/trading-journal-techniques/ |

### 自己コンプライアンスチェック結果
| チェック項目 | 結果 |
|---|---|
| 個別銘柄の売買推奨なし | ✅ 教育・一般論のみ。「今 ○○ を買え」等の表現なし |
| 断定・利益保証表現なし | ✅「絶対」「必ず」「100%」「保証」「儲かる」使用なし。期待値計算例は「概念の説明用」と明記。「かもしれません」「ことがあります」「多くの場合」など慎重な表現を使用 |
| kinsho-v1 免責（冒頭バナー＋本文末＋footer）あり | ✅ 3箇所に data-disclaimer="kinsho-v1" または同等の文言を配置 |
| noindex,nofollow あり | ✅ `<meta name="robots" content="noindex,nofollow">` を head に配置済み |
| 出典の妥当性 | ✅ 後知恵バイアス・確証バイアスは心理学の確立された概念。期待値計算式は数学的公式（正確）。「20〜30件」はトレード界隈で一般的に言及される目安として使用（特定の論文由来の断定ではなく実践指針）。FOMO等の用語は一般的用語。不確実な具体的数値（「○%改善する」等）は使用していない |
| SVG 概念図に「※ 概念を示すイメージ図です」の注記 | ✅ 全 2 点の figcaption に注記あり |

### SVG 図の構成
1. **PDCAサイクル図**（PLAN→DO→CHECK→ACT の2×2グリッド、中央に「売買日誌が回す」）— 実装済み
2. **心理状態別勝率の棒グラフ**（平常心・少し焦り・FOMO/狼狽の3段階比較、高さで概念的な差を表現）— 実装済み
3. `<!-- TODO(SVG): セットアップ種別×心理状態の2次元マトリクスヒートマップ（行=セットアップ種別、列=心理状態3分類）で期待値の高低をカラー表示する概念図を要追加・要ライト/ダーク実機確認 -->`

### 人間の残作業
- [ ] **SVG の実機ライト/ダーク確認**：追加クラス `.s-box-fill-b/g/y/r`・`.s-box-stroke-b/g/y/r`・`.s-box-text`・`.s-box-text-g`・`.s-box-subtext`・`.s-arr-fill-b`・`.s-bar-high/mid/low`・`.s-center-text` をライト・ダークモードで目視確認。特にPDCAボックスの塗りつぶし色と棒グラフの色がダークモードで視認できるか確認
- [ ] **2次元マトリクスヒートマップSVGの追加**（HTML内 `TODO(SVG)` コメントを参照）：セットアップ種別×心理状態の期待値マップ
- [ ] **Opus compliance-reviewer 監査**：公開前に `compliance-reviewer` エージェント（Opus）に下書き全文を渡してレビューを依頼
- [ ] **タイトル微調整**：「メタ認知・振り返りの型」は内容と合っているが、「エッジ」という用語が初心者に伝わるか検討（例：「勝ちパターンを見つける方法」等への変更を検討）
- [ ] **関連記事リンクの確認**：`guide-risk-reward.html`・`guide-position-sizing.html` が公開済みのため、本文内リンクは有効。`guide-cognitive-biases.html` も公開済み ✓

---

## 2026-06-08 | risk-reward

- **基準日（JST）**: 2026-06-08（UTC 2026-06-07T20:35:16Z）
- **Topic**: リスクリワードと期待値（勝率×損益比）
- **Key**: `risk-reward`
- **生成ファイル**: `drafts/draft-risk-reward.html`
- **シリーズ**: 🛡️ リスク管理・資金管理（guides.html 既存カテゴリ、初回は人間が新設）

### 参照出典 URL
| 項目 | 出典 |
|---|---|
| リスクリワード比・期待値計算式（松井証券） | https://www.matsui.co.jp/fx/study/article/analysis/risk-reward/ |
| リスクリワードの意味・計算式・目安（OANDA Japan） | https://www.oanda.jp/lab-education/beginners/aboutfx/moneymanagement1/ |
| リスクリワード比の解説（IG証券） | https://www.ig.com/jp/trading-strategies/risk-reward-ratio-explained-210729 |
| Risk Reward Ratio Explained（VT Markets） | https://www.vtmarkets.com/discover/risk-reward-ratio-explained-formula-trading/ |
| Win Rate vs Risk-Reward（JournalPlus） | https://journalplus.co/learn/guides/win-rate-vs-risk-reward/ |
| Win Rate and R:R: Connection Explained（LuxAlgo） | https://www.luxalgo.com/blog/win-rate-and-riskreward-connection-explained/ |

### 自己コンプライアンスチェック結果
| チェック項目 | 結果 |
|---|---|
| 個別銘柄の売買推奨なし | ✅ 教育・一般論のみ。「今 ○○ を買え」等の表現なし |
| 断定・利益保証表現なし | ✅「絶対」「必ず」「100%」「保証」「儲かる」使用なし。計算例は「概念の説明用」と明記 |
| kinsho-v1 免責（冒頭バナー＋本文末＋footer）あり | ✅ 3箇所に data-disclaimer="kinsho-v1" または同等の文言を配置 |
| noindex,nofollow あり | ✅ `<meta name="robots" content="noindex,nofollow">` を head に配置済み |
| 出典の妥当性 | ✅ 松井証券・OANDA・IG証券（国内金融機関）の公開記事、VT Markets・JournalPlus・LuxAlgoの英語教育記事を参照。損益分岐勝率の計算式（BEW = 1÷(1+R:R)×100）は業界標準的な数学公式であり、複数の信頼できる出典で確認済み。期待値例（勝率60%・R:R=0.5 → EV=−1,000円など）は自己計算値だが式に基づく純粋な算術 |
| SVG 概念図に「※ 概念を示すイメージ図です」の注記 | ✅ 全 2 点の figcaption に注記あり |

### SVG 図の構成
1. **損益分岐勝率カーブ**（X軸=R:R、Y軸=勝率、曲線で緑/赤ゾーンを区切り、例示点A・B をプロット）— 実装済み
2. **R:R=1:2 エントリー・SL・TP 設定図**（価格ライン＋リスク/リワードのブラケット注釈）— 実装済み
3. `<!-- TODO(SVG): トレーダーAとBの100トレード累積損益バーチャート（横軸=トレード回数, 縦軸=累積損益）を要追加・要ライト/ダーク実機確認 -->`

### 人間の残作業
- [ ] **SVG の実機ライト/ダーク確認**：追加クラス `.s-zone-g` `.s-zone-r` `.s-bew` `.s-entry-line` `.s-sl-line` `.s-tp-line` `.s-bracket` `.s-dot-b` `.s-dot-r` `.s-dot-g` をライト・ダークモードで目視確認。特にポリゴン塗りつぶしのゾーン色（fill-opacity）がダークモードで見づらくないか確認
- [ ] **累積損益バーチャートの追加**（HTML 内の `TODO(SVG)` コメントを参照）：トレーダーA vs B の100トレード累積損益を横フローバーチャートで示す
- [ ] **Opus compliance-reviewer 監査**：公開前に `compliance-reviewer` エージェント（Opus）に下書き全文を渡してレビューを依頼
- [ ] **タイトル・見出しの微調整**：現タイトルは適切だが「期待値計算」「損益分岐勝率」など検索需要の高いキーワードをtitle/descriptionでさらに前出しすることを検討
- [ ] **関連記事リンクの確認**：`guide-profit-taking.html`（第4弾予定）公開後に related カードに追加
- [ ] **loss-cut.html との相互リンク確認**：loss-cut.html 末尾の「リスクリワードは別記事で」予告から本記事への内部リンクを公開時に追加

---

## 2026-06-07 | trading-psychology-calm

- **基準日（JST）**: 2026-06-07（UTC 2026-06-06T20:33:37Z）
- **Topic**: 感情のコントロール・平常心の作り方（FOMO／狼狽売り／リベンジトレード）
- **Key**: `trading-psychology-calm`
- **生成ファイル**: `drafts/draft-trading-psychology-calm.html`
- **シリーズ**: 🧠 投資の心理・メンタル（guides.html 既存カテゴリ）

### 参照出典 URL
| 項目 | 出典 |
|---|---|
| FOMO の定義・投資心理 | https://fxshinri.com/mindset/fx-mindset-fomo/ |
| FOMO の定義（野村証券用語集） | https://www.nomura.co.jp/terms/english/other/A03432.html |
| Barber &amp; Odean (2000) 研究 | https://www.britannica.com/money/trading-psychology |
| 行動経済学・感情とトレード | https://www.heygotrade.com/en/blog/behavioral-finance-in-trading |
| マインドフルネスとトレード成績 | https://www.researchgate.net/publication/327138465_The_Role_of_Mindfulness_Meditation_on_Stock_Trading_Performance |
| マインドフルネスと処分効果 | https://oro.open.ac.uk/84403/1/PhD_thesis_Wong_Ernest.pdf |
| 扁桃体・感情制御（一般） | https://www.sciencedirect.com/science/article/abs/pii/S0306453025003440 |

### 自己コンプライアンスチェック結果
| チェック項目 | 結果 |
|---|---|
| 個別銘柄の売買推奨なし | ✅ 教育・一般論のみ。「今 ○○ を買え」等の表現なし |
| 断定・利益保証表現なし | ✅「絶対」「必ず」「100%」「保証」「儲かる」使用なし |
| kinsho-v1 免責（冒頭バナー＋本文末＋footer）あり | ✅ 3箇所に data-disclaimer="kinsho-v1" または同等の文言を配置 |
| noindex,nofollow あり | ✅ `<meta name="robots" content="noindex,nofollow">` を head に配置済み |
| 出典の妥当性 | ✅ Barber &amp; Odean (2000) は学術誌 Journal of Finance 掲載。マインドフルネス研究は ResearchGate / ScienceDirect の論文を参照。不確実な数値（「70%」「15%」等の出典不明統計）は使用していない |
| SVG 概念図に「※ 概念を示すイメージ図です」の注記 | ✅ 全 2 点に注記あり |

### SVG 図の構成
1. **感情の悪循環ループ**（FOMO→含み損・恐怖→狼狽売り／リベンジ→損失拡大の4ステップ循環図）— 実装済み
2. **2パターン比較図**（感情主導 vs ルール主導の3ステップ比較）— 実装済み
3. `<!-- TODO(SVG): 取引前→中→後のトレードルーティン・タイムライン図（横フロー）を要追加・要ライト/ダーク実機確認 -->`

### 人間の残作業
- [ ] **SVG の実機ライト/ダーク確認**：追加クラス `.s-box-warn` `.s-box-neg` `.s-box-pos` `.s-box-neu` `.s-box-label` `.s-box-sub` `.s-arr-r` `.s-arr-g` `.s-arr-fill-r` `.s-arr-fill-g` をライト・ダークモードで目視確認
- [ ] **ルーティン・タイムライン SVG の追加**（HTML 内の TODO(SVG) コメントを参照）：取引前・中・後の3フェーズを横フローで示す図
- [ ] **Opus compliance-reviewer 監査**：公開前に `compliance-reviewer` エージェント（Opus）に下書き全文を渡してレビューを依頼
- [ ] **タイトル・見出しの微調整**：タイトルが長いため短縮案を検討（例：「感情のコントロール完全ガイド｜FOMO・狼狽売り・リベンジトレードを克服する」）
- [ ] **関連記事リンクの確認**：`guide-risk-reward.html`（第3弾予定）が公開されたら related カードに追加

---

## 2026-06-06 | position-sizing

- **基準日（JST）**: 2026-06-06（UTC 2026-06-05T23:51:50Z）
- **Topic**: ポジションサイジング／資金管理（1トレードの許容リスク%・2%ルール）
- **Key**: `position-sizing`
- **生成ファイル**: `drafts/draft-position-sizing.html`
- **シリーズ**: 🛡️ リスク管理・資金管理（初回記事 → 公開時に guides.html に新カテゴリを人間が追加）

### 参照出典 URL
| 項目 | 出典 |
|---|---|
| 2%ルール | https://www.quantifiedstrategies.com/the-2-rule-money-management/ |
| 2%ルール（CME） | https://www.cmegroup.com/education/courses/trade-and-risk-management/the-2-percent-rule |
| ATR ポジションサイジング | https://www.vtmarkets.com/discover/average-true-range-atr-indicator-guide-master-volatility-trading/ |
| 破産確率・ドローダウン回復 | https://thearcalabs.com/en/insights/risk-of-ruin-trading/ |
| 破産確率・ドローダウン回復 | https://daytradingtoolkit.com/beginners-guide/risk-of-ruin-math-explained/ |
| ケリー基準 | https://corporatefinanceinstitute.com/resources/data-science/kelly-criterion/ |
| ケリー基準（分数ケリー） | https://www.quantifiedstrategies.com/kelly-criterion-position-sizing/ |
| Van Tharp の R 概念 | https://vantharpinstitute.com/van-tharp-teaches-position-sizing-strategies-and-risk-management/ |
| R-Multiples | https://traderlion.com/risk-management/r-and-r-multiples/ |

### 自己コンプライアンスチェック結果
| チェック項目 | 結果 |
|---|---|
| 個別銘柄の売買推奨なし | ✅ 教育・一般論のみ。「今 ○○ を買え」等の表現なし |
| 断定・利益保証表現なし | ✅「絶対」「必ず」「100%」「保証」「儲かる」使用なし |
| kinsho-v1 免責（冒頭バナー＋本文末＋footer）あり | ✅ 3箇所に data-disclaimer="kinsho-v1" または同等の文言を配置 |
| noindex,nofollow あり | ✅ `<meta name="robots" content="noindex,nofollow">` を head に配置済み |
| 出典の妥当性 | ✅ 数値はすべて上記の信頼できる出典から確認。推測値は使用していない |
| SVG 概念図に「※ 概念を示すイメージ図です」の注記 | ✅ 全 2 点に注記あり |

### SVG 図の構成
1. **2%ルールの構造図**（口座残高→許容損失額→ポジションサイズへの逆算）— 実装済み
2. **ドローダウンと回復率の非線形曲線**（10%→11%, 30%→43%, 75%→300% のデータ点入り）— 実装済み
3. `<!-- TODO(SVG): ケリー基準のベット比率（横軸）と対数資産成長率（縦軸）の放物線型カーブ — HTML 内コメントとして残置。要人間による実機ライト/ダーク確認後、追加を検討 -->`

### 人間の残作業
- [ ] **SVG の実機ライト/ダーク確認**：特に `s-bar-b` / `s-fill-b` / `s-fill-r` 等の追加クラスをライト・ダークモードで目視確認
- [ ] **ケリー基準 SVG の追加**（HTML 内の TODO(SVG) コメントを参照）：放物線型カーブ（最適ベット比率を示す）を追加するか検討
- [ ] **Opus compliance-reviewer 監査**：公開前に `compliance-reviewer` エージェント（Opus）に下書き全文を渡してレビューを依頼
- [ ] **タイトル・見出しの微調整**：タイトルが長めなので「ポジションサイジング完全ガイド」等への変更を検討
- [ ] **公開時の追加作業**：`guides.html` に新カテゴリ「🛡️ リスク管理・資金管理」を人間が作成し、記事カードを追加（`mw publish` の `--category` で指定）
- [ ] **loss-cut.html のリンク確認**：loss-cut.html に「資金管理は別記事で」という予告リンクがあるか確認し、公開後に相互リンクを更新

---
