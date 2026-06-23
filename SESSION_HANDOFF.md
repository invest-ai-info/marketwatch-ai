# 🔖 セッション引き継ぎ（最終更新: 2026-06-21）

新セッションは **このファイル＋ CLAUDE.md ＋ auto-memory（MEMORY.md 経由）** を読めば文脈を復元できる。
2026-06-17 以前の詳細履歴は **SESSION_ARCHIVE.md**（保管庫・後から辿る検索用）へ退避した。

---

## ✅ スマホCSS v3 — 全 guide 112件に反映完了（2026-06-22）

スマホの表が横スクロールする件（オーナー要望）＝**v3 対応完了**：表のセルは折り返さず1行（数字も説明も縦に割れない）＋**はみ出す表だけに「→ 横にスクロールできます」誘導**（スクロールで消える小 script）。`fix_mobile_overflow.py` の BLOCK を v3 化（style＋`<script id="mw-mobile-fit-js">`）、置換 regex も style＋script 対応に拡張。

- ✅ **guide 112件すべて v3**（ローカル sync 分＋クラウド専用＋当日新着 `guide-news-2026-06-22-nikkei-72k`。`_fix_cloud_mobile.py` 最終実行＝差し替え31/変更なし81/失敗0）。
- ✅ 今後の新規記事は `publish_article.py` が公開時に v3 を自動注入（`fix_mobile_overflow.py` v3 は GitHub 反映済）。
- ⚠️ api.github.com は throttle が断続的に出た（WinError 10060。書きは api のみ／raw は throttle外）。大量PUT後に起きやすい。混雑時は per-path の `_fix_cloud_mobile.py`（GET+PUT・0.4s間隔）が sync より通りやすい。
- ⚠️ SYNC3件（`guide-jp-value-vs-zombie`／`guide-risk-by-account-size`／`guide-jpy-intervention-2026-06`）は cloud 経路で v3 化したため local(CRLF)↔GitHub で次回 sync が staleガードに 🚫 することがある＝意図確認のうえ `--force` か通常 sync で再反映すれば綺麗（中身は同一 v3）。

---

## ✅ デプロイ待ち — 全件完了（2026-06-22）

✅ **2026-06-21 夜：`python sync_to_github.py`（182件・失敗0）** — スマホ修正の残り記事3＋ツール3、ゴールド土日連投の修正（`generate_technical_alerts.py` の市場休止ガード＝**次回 technical-alerts 実行分から土日メール停止**）、本ハンドオフ自体まで反映。api.github.com の throttle（WinError 10060）は自然回復済。

✅ **2026-06-22：item #2 完了** — クラウド公開記事のスマホ修正。GitHub上の guide-*.html 111件を走査し、`id="mw-mobile-fit"` 未注入の **26件**（`guide-auto-*`／`guide-news-2026-06-19〜21`／`guide-signal-lab-006〜009・014〜016`／`guide-weekly-*`／`guide-weekly-review-*`／`guide-monthly-report-2026-05`）に注入PUT（失敗0）。contents API で代表3件 marker=True を確認・`mw check`＝エラー0。
- 今後の新規クラウド記事は `publish_article.py` が公開時に mobile-fit を自動適用するため、この backfill は一度きり。再発時用に `_fix_cloud_mobile.py`（ローカルscratch・SYNC対象外）を残置。

✅ **2026-06-22：スマホCSS v2（数字の桁割れ修正）** — 旧 `*{overflow-wrap:anywhere}` が狭い表で価格を1桁ずつ縦に折る不具合（例＝intel記事の `+10.64%（終値$133.99）`）。`fix_mobile_overflow.py` の BLOCK を v2 化（`break-word`＋表の太字数値 `white-space:nowrap`＋左右余白圧縮 `.article` 14/12px・セル6px＋360px段＋本文小型化）。同ツールを「**既存ブロックを差し替え**」方式に変更（`apply_block`）。ローカル98件→sync、クラウド専用27件→`_fix_cloud_mobile.py`。**GitHub guide 111件すべて v2**（contents API で確認・`mw check`エラー0）。
- ⚠️ **学び（次回ハマり防止）**：① Windows の text-write で BLOCK が CRLF 化し sync はバイナリ push → クラウド側は LF 比較で「常に差分」に見え無限再PUTの罠。`apply_block` の同一判定を**改行正規化**で回避。② `_fix_cloud_mobile.py` は **ディレクトリ listing の sha が約60秒キャッシュ**で古い／**raw.githubusercontent は5分キャッシュ**。内容・sha は必ず**パス指定 contents API**（`contents/{name}?ref`）で取り直すこと。

---

## 🛡️ コードが強制しているルール一覧（"覚える"でなく"コードで強制"）

> 設計思想（CLAUDE.md／auto-memory `feedback_rules_as_code`）＝**人が手で守るルールを、コードが自動で守る形へ**。
> 新ルールは「文書に書いて記憶で守る」より「**チェックを1個足す**」。私が記憶で守るルール数をゼロに近づける。
> 文書が長くなったら、必須ルールはコードへ移して文書から消し、古い履歴はアーカイブする（このスリム化もその一環）。

| 強制しているルール | 受け皿コード（単一の真実） | 効果 |
|---|---|---|
| SYNC禁忌ファイルを誤って push しない | `check_site_consistency.py` の `SYNC_FORBIDDEN`（`mw check`） | 巻き戻し事故を push 前に **error 停止** |
| 公開前に main を取り込む（reconcile） | `publish_article.py` 内蔵 reconcile | ローカル公開での巻き戻しを防止 |
| **ローカルが古い状態での sync 巻き戻し防止** 🆕 | `sync_to_github.py` の staleness ガード（remote_sha baseline 比較） | 前回 sync 後に GitHub 側が更新されたファイルの push を **🚫中止**（意図的なら `--force`） |
| **公開記事が guides.html カードから消えていないか** 🆕 | `check_automation_health.py` §③（`automation-health.yml` 毎朝09:30 JST） | 巻き戻し（local-drift）を **翌朝 Issue で即検知** |
| **同一 workflow の同時実行レース防止** 🆕 | `update-market-news.yml` の `concurrency`（cancel-in-progress: true） | push(on:push)＋手動trigger の二重起動を新しい方に一本化＝失敗run・誤アラートを根絶 |
| kinsho-v1 免責 / 10ボタンナビ / リンク切れ / SYNC_FILES登録 | `check_site_consistency.py`（`mw check`／土曜 `site-qa-lint`） | 不変条件を push 前に検査・exit 1 |
| 研究日誌の数値捏造防止 | `signal_lab_verify.py`（固定オラクル・編集禁止） | claims.json を signals-log から独立再計算して突合 |
| 更新履歴の整列・最新5件 | `generate_market_news.py` の `_history_items` | 手で削らない（日付降順・自動整列） |
| sitemap 全記事網羅 | `generate_market_news.py` の `build_sitemap_xml` | 全 guide を自動収集・手動編集不要 |

🆕＝2026-06-20 追加（B＝カバレッジ番人 ／ C＝sync staleness ガード）。新ルールはこの表に1行＋チェック1個で増やす。

---

## ✅ 2026-06-23 セッション（夏枯れ記事＋調整買いリスト）

- **公開記事**：`guide-summer-doldrums.html`「夏枯れ相場とは？7〜8月の薄商いを乗り切る個人投資家の備え方」公開。コンプラ独立監査=🟢白（特定銘柄なし・断定なし・免責二層・2024-08-05急落データは日経/Bloomberg一次ソース一致）。ライブ200・guidesカード・index更新履歴 反映確認済。季節性ジャンルで `guide-sell-in-may` の姉妹編。
- **個人用（非公開・SYNC除外）**：`_MY_CORRECTION_WATCHLIST.md`＝「大調整が来たら買う」候補リスト。土台＝`_jp_doublebagger_owner.csv`(48銘柄)＋`MY_TRADING_RULES` の「続伸＝risk_off で点火する条件付きエッジ」。中核8(中型〜大型・流動性)／サテライト7(小型高スコア)／ディフェンシブ2＋発注前5問。点火サイン＝日経/TOPIX が60日線割れ。**平常時(risk_on)は寝かせ、落ちてる最中に飛びつかない**。
- **公開記事②（続編）**：`guide-correction-playbook.html`「株の急落・調整局面での立ち回り方｜“落ちるナイフ”の見分け方」公開。コンプラ独立監査=🟢白（「教育コンテンツの理想形に近い」評価・特定銘柄なし・下げ止まり指標[RSI/サポート/VIX]は教育目的の注記付き・分割エントリーvsナンピンの違い）。ライブ200・guidesカード反映。夏枯れ記事と相互リンク。
- 続編候補（後日）：セクター別の備え／記事キュー（金利と債券・単複利・ETF×投信・注文方法・PER/PBR）。

---

## ✅ 2026-06-20 セッション

### 午前〜（別セッション）：JP株システム一気通貫＋研究日誌救出
詳細は auto-memory `project_jp_doublebagger`（最厚）参照。要点：
- JP株ダブルバガー・システム完成（J-Quants 点in-time財務で検証／A1〜A3 クラウド自動化／**レジーム・コックピット**＝指数 vs 60/200日線＋市場の幅の多数決で上昇・下落を判定→下落でサイズ自動で守りへ）。公開記事2本（コンプラ白）＝`guide-jp-value-vs-zombie.html`／`guide-risk-by-account-size.html`。守りエッジ群は `MY_TRADING_RULES.md`（ローカル専用・SYNC除外）。
- 🚑 研究日誌のカード消失を local-drift から全復元（ライブ研究日誌 #1〜15）。
- 🔒 再発防止A＝`publish_article.py` に公開前 reconcile を内蔵（commit 1d28085）。

### 午後（本セッション）：B → C 完了（オーナー「順番に」）
- **B＝カバレッジ番人 ✅実装・デプロイ済**：`check_automation_health.py` に §③を追加。リポの全 `guide-signal-lab-*`／`guide-news-*` が guides.html にカードとして在るかを GitHub API で**毎朝照合**し、欠落＝巻き戻しを 🟡 で Issue 化。現状 **19件すべて掲載 OK**。今朝 #015 を巻き戻した類の事故を、この番人なら翌朝検知できる（commit 790963a・automation-health.yml が実行）。
- **C＝棚卸し ✅**：
  - **rules-as-code**＝`sync_to_github.py` に **staleness ガード**を追加（上表）。「公開前 reconcile」は `publish_article.py` では強制済みだったが、**生 sync 経路に穴**が残っていた（local-drift の第2の入口）。今回その穴を塞いだ。モック単体テストで stale=ブロック／`--force`=バイパス／baseline無=fail-open を確認。※`sync_to_github.py` はローカル専用（GitHub 未追跡）＝デプロイ不要・即有効。
  - **文書スリム化**＝本ファイルを 788行 → 約80行へ圧縮。2026-06-17 以前は `SESSION_ARCHIVE.md` へ退避（SYNC_FILES 入り）。

### 午後（続き）：機能追加＋信頼性修正
- **🚨 ドル円161円・為替介入の解説記事を公開**（`guide-jpy-intervention-2026-06.html`・独立Opus監査=白・ライブHTTP200）。介入の決定=財務省/実施=日銀、当局は水準を明言しない、2026GW介入実績(4〜5兆円)を断定せず中立整理。**公開は手動trigger を打たず on:push 1本に任せレース回避**（#670 push のみ success）。
- **🚀 JP新高値ブレイク機能を追加**（オーナー要望）：`_jp_breakout_scanner.py`（新）＝流動性400から52週高値更新を抽出、**レジーム risk_on のときだけ表示**＋危険スコア(過熱/連騰/超小型/負業種)で"宝くじ"を降格。`jp_daily.py` ⑥.5 に組込・`_jp_make_dashboard.py` に🚀タブ。**private repo `jp-momentum-research` にも push 済**（cloud run #8 success・スマホ表示OK）。
- **📆 track-record に日足タブを追加**：`generate_track_record_page.py` に1d足ダッシュボード（4H/1Hと同型・記録のみ/配信なしの注記）。日足シグナルは記録のみ(--no-email)で発火済(ライブ38件)＝**メールしない方針は維持しデータだけ可視化**。`technical-alerts-1d.yml` で再生成・ライブ反映確認。
- **🔧 信頼性修正2件**：(1)`update-market-news.yml` に concurrency 追加＝同時実行レース根絶(上表・commit 14cfa77)。(2)**staleガード↔reconcile の干渉を解消**＝`publish_article.py` が reconcile 後に `.sync-cache.json` の該当 baseline を消す（朝入れた staleガードが reconcile 済ファイルを誤ブロックする副作用を除去）。
- **📊 日本株 値上がり率/値下がり率ランキングを公開サイトに実装**（オーナー要望・`hot-assets.html` 最上段・スマホ最適化2列→1列・独立Opus監査=白・ライブ反映 run #676 success 各20件）。流動性上位400で 値上がり/値下がりトップ20＋**売買代金2日分**（前日/前々日＝ストップ高/本物の大商いを判別）＋**決算🟢黒字/🔴赤字**＋業種。**自己完結（公開リポ内・キー不要）**＝静的 `jp-stock-info.json`（`make_jp_stock_info.py` がローカルのJ-Quantsから四半期更新＝赤字黒字/名前/業種）＋**`jp-rankings.yml`（東京クローズ後 16:40/17:10 JST＝朝だとcron遅延で場中更新になるため夕方に）** が `build_jp_rankings.py` で **Yahoo価格だけ**から `jp-rankings.json` を生成 → commit すると **update-market-news の on:push（`jp-rankings.json` 追加済）が hot-assets を即再描画** → `generate_market_news.build_jp_rankings_section` が最上段に描画。`jp-rankings.json`=SYNC禁忌(workflow生成)。コンプラ要点＝事実データ・売買推奨でない・「大きく動いた≠良い投資対象」注記・免責二層。

---

## ⚠️ 絶対遵守（事故防止）

- **SYNC禁忌**（ローカルから絶対 push しない＝routine/cron/generate が GitHub 側で生成）。**正は CLAUDE.md の SYNC禁忌リスト**。代表例：
  6コアHTML（index/calendar/charts/vix/market-health/hot-assets）／`signals-log.json`／`technical-alerts-history*.json`／`track-record.html`／political系／youtube系／`fundamental-context.json`／`weekly-levels.json`／`weekly-zone-plan.md`／`sitemap.xml`／`weekly-strategy-context.json`／`indicator-result.json`／`signal-lab-tracker.json`／`signals-log-backtest.json`／`article-ideas.md`／`daily-preview.md`／`political-digest.md`／`compliance-scan.md`／`site-qa-report.md`／`panic-scan.md`／`drafts/draft-*`・`drafts/news/*`・`drafts/sns/*`
  → `mw check`（`check_site_consistency.py`）が SYNC_FILES への誤混入を、sync の staleガードが「古いローカルでの上書き」を、それぞれ自動で止める。
- **SYNC対象（OK）**：`*.py`（※`sync_to_github.py`・`mw.py` 等のローカル専用ツールは GitHub 未追跡）／`.github/workflows/*.yml`／個別 `guide-*.html`／`guides.html`／`robots.txt`／`my-trades.json`／`memory/*.md`／各 docs。
- 記事追加は **`python mw.py publish ...` → sync → workflow → ライブ確認**。公開前に compliance-reviewer(Opus)監査・教育トーン・特定銘柄の買い推奨は書かない・kinsho-v1 免責・10ボタンナビ。手動時も `mw check` で push 前点検。
- ネット不調時は無限リトライせず、ブラウザで手動 trigger を依頼（最大3〜5回）。

---

## 📌 アクティブな宿題

- ✅ **update-market-news.yml の失敗は解決済**（2026-06-20 午後・concurrency追加）。原因＝push+dispatch の同時実行レース。今後 `mw publish` を素で使ってもOK。
- 🚩 **FOMC結果の信頼性検証（6/18 起票・未確認）**：`indicator-result.json` の FOMC（据え置き 3.50–3.75%）は出典が個人ブログ系の疑い。一次（Reuters/Bloomberg/Fed）で数値を確認し、違えば訂正・正しければ出典差し替え。日銀（6/16・1.0%利上げ）は verified。
- 🔴 **POLICY dict 更新**：`generate_market_news.py` の `POLICY`（日銀→1.0%／FOMC据え置き）を会合結果へ。未更新だと market-health のスワップ金利差%が陳腐化。
- 📉 **AdSense 再審査準備**（auto-memory `project_adsense_review`／2026-06-18 却下＝「有用性の低いコンテンツ」）：薄い自動ページの noindex／編集コンテンツの価値強化を監査してから再申請。
- 🗓️ **`jp-stock-info.json` の四半期更新**（決算シーズン後に `python make_jp_stock_info.py` 再実行→`mw sync`。赤字/黒字フラグを最新決算へ。日次の値上がり率/売買代金は `jp-rankings.yml` が自動）。
- ✍️ autodraft topicキュー ⑫以降の補充（候補＝金利と債券／単利と複利／ETFと投信／注文方法／PER・PBR）。
- 📊 弁護士相談アジェンダ（track-record 統計開示／確信度ラベル／個別銘柄記事の言及）。
- 🟡 保留＝**J-Quants Standard（¥3,300・1回）** で「risk_off 転換→守り」を 2018/2020 実暴落でバックテスト（オーナー課金判断時）。
- 研究日誌の自動公開はエスカレ回のみ人間レビュー（`drafts/REVIEW.md` の🚩）。

---

## 📎 運用メモ

- 作業フォルダ: `C:\Users\info0\OneDrive\デスクトップ\新しいフォルダー` ／ GitHub: `invest-ai-info/marketwatch-ai`(main)
- 運用は **`python mw.py <cmd>`** が単一入口（check / publish / sync / **deploy [--trigger]** / trigger <wf> / status [wf] / **issues** / **audit** / routines）。`mw routines` で全 routine ID 一覧。
- 🆕 **ループ・エンジニアリング土台（2026-06-23・決定論コマンド＝トークン0）**：②`mw issues`＝open health-check/automation-health Issue 一覧（トリアージの土台）。③`mw audit`＝guide記事の改善候補スコア化（desc短/本文短/内部リンク少/JSON-LD無）。**判断部分だけ上限付き `/loop` でモデルに渡す**設計。⚠️**audit最弱は全部クラウド自動生成（weekly-review/weekly/monthly）＝SYNC禁忌＝手でHTML直すと巻き戻る→直すのは生成スクリプトのテンプレ（`auto_weekly_review.py`/`auto_weekly_strategy.py`/`generate_monthly_report.py`）**。これは AdSense「薄いコンテンツ」対策と直結。`/loop` レシピ＝②「mw issues→最大3件診断＋提案(自動適用しない)→STOP」／③「mw audit→手書きguideの最弱を1本改善→白確認→publish、最大3本/回、score≥2が尽きるかで停止。自動生成ページは生成スクリプト側を直す」。
- 🆕 **`mw deploy`（2026-06-23）＝自己修復デプロイ（決定論・モデル不使用＝トークン0）**：sync を ❌throttle 時に backoff して**最大5回**再試行・🚫staleは即エスカレ・成功/上限/合計15分で必ず停止→任意で workflow 起動(`--trigger`)→ライブ200検証。上限は `mw.py` の `DEPLOY_*` 定数で固定＝構造的に永久ループ不能（今日の api.github.com throttle 手動リトライを自動化）。
- 同期は `python sync_to_github.py`（＝`mw sync`）。staleガードに 🚫 されたら「先に最新を取り込む（reconcile）」か、意図的なら `--force`。workflow 手動起動は `mw trigger <wf.yml>`。**ローカルは UTF-8 強制**：`$env:PYTHONUTF8="1"`（PowerShell）。
- routine 操作: schedule スキル → `ToolSearch select:RemoteTrigger` → RemoteTrigger（list/get/update/run）。クラウド routine（`signal-lab-daily`／`news-daily-auto` 等）はこれで管理。
- ⚠️ ローカルは GitHub と未同期なことがある（OneDrive）。**真の状態は GitHub／ライブを見る**。token は `market-news-config.json`(.json)。
- ユーザー北極星：投資家全体の底上げ／サイト・SNS 年収1000万／個人投資成績 年収1億。
