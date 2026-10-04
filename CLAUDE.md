# MarketWatch AI（marketwatch-jp.com）— プロジェクト全体像

**サイト目的**: 日本人投資家向けの情報収集サイト。投資家が幸福になる手助けが第一目的。

🎯 **一番の目標（2026-09-26 オーナー決定）＝シグナル研究の成績（投資の成績）を上げること**。サイトの主軸はシグナル研究＝成績が上がらなければ読者の信用を失う。作業の優先順位は「これは成績を上げるか」で決める。**大手と同じこと（速報・網羅・チャート機能）はしない**＝このサイトにしか無い記録と、日本特有の現象から新しい柱を探す（候補と手順は SESSION_HANDOFF 2026-09-26 夜（11））。検証は従来どおり「結果を見る前に事前登録→前向きで確かめる」＝成績を急いで後付けの勝ちパターンを作らない

## 作業フォルダ
- ホストパス: `C:\Users\info0\OneDrive\デスクトップ\新しいフォルダー`
- GitHub: `invest-ai-info/marketwatch-ai`（branch: main）
- 🆕 **PR のマージ（2026-09-25 オーナー決定）**: Claude がセッションで作った PR は、テスト・検査（`tests/`・`check_site_consistency.py` など）が通ったら **Claude がマージしてよい**（マージ後に何を反映したかを報告）。ただし**サイトの見た目や自動実行の動きが大きく変わるもの**は、反映の前にオーナーへ一言確認する。routine・Actions の自動生成物は従来どおり main へ直接入る（PR 不要）
- 🆕 **クラウドで頼まれたことが手元向きなら、手元のセッションへ誘導する（2026-09-26 オーナー確認）**。クラウドのセッションはオーナーの PC に触れず、手元のセッションを自動で動かす手段も無い。手元向き＝`research/`（非公開研究・DOCTRINE・`mw evolve`）／PC 内の大きなデータやキャッシュ（罠シリーズ等）／クラウドから届かないサイト（論文の出版社・bls.gov 等）／`mw discipline` など手元の取引記録の点検／手元専用の道具（`_` 始まり・本物の `sync_to_github.py`）。そのときは ①手元向きである理由を1行で伝え ②**手元のセッションにそのまま貼れる指示文**（目的・使うファイル・手順・報告してほしいこと）を渡し ③クラウドでできる部分は先に進める。連携の土台＝GitHub（クラウドの成果→手元は起動時に `auto_pull.py` で自動取り込み／手元の成果→`mw sync` で GitHub へ）＋ SESSION_HANDOFF。手元のセッションの始め方＝デスクトップアプリ Code の左の一覧「新しいフォルダー」の「＋」（または入力欄の上の実行場所を「ローカル」にしてフォルダを選ぶ）

---

## 🌐 サイト構成（9 コアページ + 解説記事群）

| ページ | 役割 | 自動生成元 |
|---|---|---|
| index.html | メイン（価格・ニュース・AI 判断） | update-market-news.yml |
| calendar.html | マクロ経済カレンダー | update-market-news.yml |
| charts.html | 150年価格チャート + 投資史年表 + 歴史イベント | update-market-news.yml |
| vix.html | VIX 恐怖指数 90日 | update-market-news.yml |
| market-health.html | 市場健康度（VIX/恐怖&強欲/バフェット/CAPE） | update-market-news.yml |
| hot-assets.html | 出来高急増ランキング | update-market-news.yml |
| guides.html | 解説記事一覧 | 手動更新 |
| **track-record.html** ⭐ | 🧪 シグナル研究（旧名「シグナル成績」＝2026-09-26 にナビ・記事内のリンク文とも改名。10 タブ。🗺️ いま検証中のこと＝`research_map.py` が毎回データから組み立てる・`#map` で直リンク） | technical-alerts.yml |
| youtube-summary.html | 投資系 YouTube 要約 | update-youtube-summary.yml |
| **political-feed.html** 🆕 | 政治発言ライブフィード | political-alerts.yml |

解説記事は `guide-*.html` として個別公開（25+ 件、最新は guides.html 最上段）。

### ナビバー（10 ボタン、利用頻度順、2026-06-15 に 📖 投資本 を追加）

```
🏠 index → 🚨 political-feed → 🧪 track-record(シグナル研究・2026-09-26 に「シグナル成績」から改名) → 📅 calendar → 📚 guides → 📖 投資本(guide-investment-books)
→ 🩺 market-health → 🔥 hot-assets → 📈 charts → 📺 youtube-summary
```

- ⚠️ **vix.html はナビバー対象外**（charts / market-health / guide-vix.html 経由で到達）。10ボタンはモバイル2列×5行・375pxで崩れ無し確認済
- 🆕 **2026-09-23〜 枠の単一の真実＝`apply_site_frame.py`**（11ボタンの並び `NAV_BUTTONS`・パソコン幅6+5の2段・解説記事ヘッダーの標準形・広告の上下40px）。**update-market-news が毎回 `--all`**＝クラウドの記事レーンが崩したヘッダー/ナビも次の実行で戻る。生成スクリプト8本は `FRAME_STYLE_TAG` を import。テスト＝`_test_site_frame.py`
- ナビバー変更時は **決定論ツールで一括更新**：
  - **guide-*.html（約75本）＝ `python unify_navbar.py --apply`**（10ボタン標準を内蔵。投資本ページのみ自身を current、他は guides.html を current）
  - **生成スクリプト8本＋guides.html＋about/contact/privacy ＝ `python apply_books_nav_scripts.py --apply`**（各 `guides.html` の nav 行直後に挿入・冪等）。対象スクリプト＝`generate_market_news.py`（nav 7ブロック）／`generate_youtube_summary.py`／`generate_track_record_page.py`／`build_political_feed_page.py`／`auto_weekly_strategy.py`／`auto_weekly_review.py`／`generate_monthly_report.py`／`auto_indicator_preview.py`
- 確認: `python mw.py check`（`check_site_consistency.py` の `NAV_LINKS` は10件＝nav保持ファイルに `guide-investment-books.html` 欠落があれば warning）

---

## 🤖 自動化システム（GitHub Actions ワークフロー）

| ワークフロー | 頻度 (JST) | 役割 |
|---|---|---|
| **update-market-news.yml** | 朝 7 / 夕 16（cron は実測で1〜3時間遅延）＋**JP Stock Rankings 完了で即起動**（`workflow_run`・2026-09-17〜） | 6 コアページ + 解説生成。⚠️ `concurrency` は `cancel-in-progress: false`＝push 途中で殺されると次の run が古い土台で rebase 衝突して exit 128 になる（2026-09-17 実際に発生）。衝突時は生成物なので `-X theirs` で今回生成した側を採り3回まで再試行する |
| **technical-alerts.yml** | 4 時間ごと（6 回/日、3 重 cron） | 18 銘柄テクニカル分析 → メール |
| **technical-alerts-1h.yml** | 1 時間ごと | 1H 足データ収集（メールなし） |
| **technical-alerts-1d.yml** 🆕 | 毎朝 06:20（NY引け後） | 日足データ収集（メールなし・記録のみ。上位足=週足・クールダウン72h・expired 21日。2026-06-11新設＝時間足勾配 1h<4h<1d? の検証用） |
| **political-alerts.yml** | 30 分ごと | 政治発言フィード + HIGH 速報メール |
| **weekly-strategy.yml** | 日曜 18:13 | 来週投資戦略の自動生成 |
| **weekly-review.yml** ⭐ | 月曜 07:13 | 先週シグナル振り返り (C1) |
| **monthly-report.yml** ⭐ | 毎月 1〜3 日 09:23（取りこぼし対策で1-3日に拡張・冪等） | 先月成績レポート (C3) |
| **monthly-calendar-reminder.yml** | 毎月 25 日 09:13 | 翌月指標リマインダー + 休場補充 |
| **monthly-backup.yml** | 毎月 1〜3 日 09:10（同上・冪等） | signals-log の GitHub Release |
| **monthly-calendar-reminder.yml** | 25日 09:13 | 市場休場の自動補充＋**経済指標の生成**（`sync_economic_events.py`）＋**決算予定の更新**（`build_earnings_calendar.py`）＋来月指標のメール |
| **health-check.yml** | 12 / 20 | サイト 6 ページ HTTP・最終更新の鮮度チェック（2026-08-30〜 **経過時間**で判定＝`STALE_HOURS=26`。旧「JSTの今日と一致するか」は実行が深夜0時JSTをまたぐと必ず誤検知した） |
| **indicator-alert.yml** 🆕 | **他のワークフローの完了に相乗り**（政治発言・ティッカー・4H/1H・市況ニュース＝1日約65回）＋毎時13分の保険 | **発表の15〜120分前に「まもなく」メールを1発表1通**（`send_indicator_digest.py --mode alert --sent-file`・送った記録は actions/cache で持ち回す）。動機＝2026-09-17 の実損（19:33 に建てて 20:00 発表）。🔁 **2026-10-04 改定**＝毎時の cron は GitHub に間引かれ実際は1日4〜5回（間隔の中央値4.7時間）で、10/2 のユーロ圏HICP・米雇用統計に届かなかった（旧45〜105分の窓・試算の取りこぼし81%→新0.6%）。⚠️ 相乗り先の `name:` は一字一句合わせる（`tests/test_indicator_alert_dedup.py` と automation-health §⑭ が見張る） |
| **indicator-digest.yml** 🆕 | **routine の push に相乗り（06:13-06:20 JST）**＋cron保険 | **今日の重要指標を朝いちでメール**（`send_indicator_digest.py`）。🚨 2026-09-17 の実損が動機＝英中銀の発表27分前に建てて当日損失の約半分を出した。環境警戒スコアは**シグナルが出たときのメールの中身でしか届かない**ので、手動の発注は誰も見張っていなかった。**判断の直前ではなくポジションを持つ前に渡す**のが趣旨。件名で状態がわかる（🚨今日ある／📅7日以内／⚪無し）。読むだけでデータは書き換えない |
| **automation-health.yml** 🆕 | 09:30 | 裏方自動化の見張り番（cron/routineの沈黙の失敗を検知。Actionsは実行成否、routineは出力鮮度で判定→異常時Issue化。`check_automation_health.py`） |
| **edinet-yuho.yml** 🆕 | 平日 19:40 | 話題の企業の有報本文→`edinet-yuho.json`（company-weekly-auto の日本株用。詳細は SYNC禁忌節） |
| **verify-calendar.yml** 🆕 | 月曜 07:10 ＋ 毎月25日 07:10 | **米・英・ユーロ圏の発表日を各国の公式日程と機械で突合**（米=`verify_economic_calendar.py`／英EU=`verify_uk_eu_calendar.py`。**2本を1ステップで回す**＝片方が落ちても両方のレポートが Issue に載る）。食い違い・解析不能・比較0件のいずれでも Issue 化。🔑 **Claude セッションからは bls.gov が egress 遮断されるが Actions のランナーからは届く**＝検証はここで回す |
| **jp-rankings.yml** 🆕 | **routine の push に相乗り**（news 台帳 17:5x・sns 19:1x JST）＋cron 保険4本（16:40〜19:10 のつもりが実測 21〜23時台） | 日本株ランキング生成（`build_jp_rankings.py`→`jp-rankings.json`。詳細は下の SYNC禁忌節の同名項目） |
| **exit-research.yml** 🆕 | 日曜 05:23（＋07:47 保険） | 出口の研究を週1で前向きに積み上げる（壁ラボ・損切りラボ。2026-09-26 オーナー指示・詳細は SESSION_HANDOFF）。🔁 同日、幅の出し方（`exit_rule_backtest._mean_se`）を安全側に切り替えた（オーナー決定）。出力は GitHub 側生成＝push 禁止 |
| **env-profile.yml** 🆕 | 毎月2日 10:17（＋3日 保険） | シグナルが「効いたとき・効かなかったとき」の環境の統計を同じ物差しで数え直す（`signal_env_profile.py`・2026-09-26 オーナー指示）。月ごとの履歴＋前回からの変化＋「ファンダの見立てと逆向き」の前向きの成績。出力は GitHub 側生成＝push 禁止 |
| **pillar-lab.yml** 🆕 | 手動のみ | 新しい柱・第1波（2026-09-27 オーナー決定）＝A1 AIの見立てと逆向き／B1 ゴトー日の仲値／B2 重要な発表の前後／B4 くりっく365 の資料の形。物差しと判定は **`PILLAR_PREREG.md`（事前登録・結果を見る前にコミット）** に固定＝出力に指紋（sha256）が入る。`pillar_lab.py`。出力は GitHub 側生成＝push 禁止 |
| **pillar-lab-jp.yml** 🆕 | 手動のみ | 新しい柱・第2波＝日本株（2026-09-27 オーナー決定）＝J1 大量保有報告書のあと／J2 権利付き最終日に向けた日経平均／J3 信用残の資料の形。事前登録＝`PILLAR_PREREG.md`「第2波・日本株」。EDINET の書類一覧は `EDINET_API_KEY` で取り、**actions/cache（edinet-hist/）に置いてリポジトリに入れない**（1回150分まで・残りは次の実行で）。`pillar_lab_jp.py`。出力に銘柄名は出さない・GitHub 側生成＝push 禁止 |
| **trend-lab.yml** 🆕 | 手動のみ | トレンドの見方の比べ比べ（2026-09-27 オーナー決定）＝機械で数えられる9つ（移動平均・200日線・ダウ理論・一目均衡表・ドンチャン55日・スーパートレンド・GMMA・平均足・ADX）を18銘柄の日足・月ごとで偽薬と比べる。一覧＝`TREND_INDICATORS.md`・事前登録＝`PILLAR_PREREG.md`。`trend_lab.py`。出力は GitHub 側生成＝push 禁止 |
| **combo-lab.yml** 🆕 | 手動のみ | 組み合わせの相性ラボ（2026-09-27 オーナー）＝トレンド10×オシレーター6×出口6＝360通り。**前半（2015年まで）で上位3つを選び、後半（2016年から）で1回だけ確かめる**（偽薬 p＜0.05÷3）。`combo_lab.py`。出力は GitHub 側生成＝push 禁止 |
| **combo-forward.yml** 🆕 | 毎月3日 10:47（＋4日 保険） | 前向きの観察（2026-09-27 オーナー「両方進めてください」）＝相性ラボで向きだけ残った 一目三役×ボリンジャー下限×追いかける損切り を**入る日 2026-09-28 以降の取引だけ**で数える。区切り 50/100/150件は一度出たら固定。事前登録＝`PILLAR_PREREG.md`「前向きの観察」。`combo_forward.py`。出力は GitHub 側生成＝push 禁止。📌 **合図の組み合わせ探しはここで区切り**（同日）＝次は J1b と⑤ |
| **box-lab.yml** 🆕 | 手動のみ | S1 時間帯の箱の抜け（2026-09-27 夜・オーナー「登録して先に数えてください」＝区切りのあとの新しい登録・J1b と⑤より先）＝東京の値幅をロンドン／NY の始まりで抜けた向きに乗る。為替9ペアの1時間足・偽薬＝向きだけコイン・p＜0.05÷2。出どころ＝スキャルピング本の整理（手元の `research/fx-scalping-books/`）。事前登録＝`PILLAR_PREREG.md`「S1」。`box_lab.py`・テスト `tests/test_box_lab.py`。出力は GitHub 側生成＝push 禁止 |
| **yori-lab.yml** 🆕 | 手動のみ | J4 前の日に出来高が急増した銘柄の、次の日の寄り付き（2026-09-28 オーナー「寄り付きから何分で手仕舞うか・どんな条件で急騰しやすいか・入らない方がいい条件」）＝サイトの日本株ユニバース約400から前の日の人気急上昇20（build_jp_rankings と同じ決め方）を選び、Yahoo の5分足（直近約60日）で次の日の 9:00〜大引けを数える。判定4つ（P1 寄り天／P2 手仕舞いの時刻を前半で選び後半で確かめる／P3 窓+3％／P4 上ヒゲ）・事前登録＝`PILLAR_PREREG.md`「J4」。`yori_lab.py`。出力は集計だけ・銘柄名なし・GitHub 側生成＝push 禁止 |
| **yori-forward.yml** 🆕 | 平日 08:17（＋19:43 保険） | J4F 寄り付きの前向き（2026-09-28 夕・オーナー「前向きに数える仕組みを作って進めてください。1000回を超えて期待値がプラスにならないようだったら検証はストップして検証済みリストに追加」）＝J4 から売買の形にした F1〜F4 を **2026-09-29 以降の取引だけ**で数える（その日より前の日だけ・1日は一度数えたら固定）。**1000回に届いた日に1回だけ判定**＝費用後の平均の幅がまるごと0より上なら「プラスを確認」、それ以外はストップして **`verified-list.md`（検証済みリスト・`verified_list.py` が記録から組み立てる。前向きの検証を足したら `SOURCES` に1行）**へ。事前登録＝`PILLAR_PREREG.md`「J4F」。`yori_forward.py`・テスト `tests/test_yori_forward.py`。5分足は約60日しか取れない＝automation-health が見張る。出力は GitHub 側生成＝push 禁止 |
| **london-lab.yml** 🆕 | 手動のみ | L1・L2 ロンドン時間のドルの流れ（2026-09-30 夕・オーナー「ロンドン時間に限定して取引をしたい」→本の下調べ→「進めてください」）＝論文で確かめられた癖を個人の費用で数える。L1＝ロンドンの朝（現地 08→12時）にユーロドル・ポンドドル売り（自国の時間の通貨安）／L2＝16時の値決めの前（現地 12→16時）にドル買い（4ペア）。Yahoo 1時間足730日・S1 と同じ費用・偽薬・日ごとの幅。**1000回以上でプラスと言い切れなければ `verified-list.md` へ**（`verified_list.py` の `SOURCES` に登録済み・過去の1回だけのものはストップだけ載せる）。事前登録＝`PILLAR_PREREG.md`「L1・L2」。`london_lab.py`・テスト `tests/test_london_lab.py`。L3（Hiro の規則）は手元の MT5 で別に登録。出力は GitHub 側生成＝push 禁止 |
| **london-hold-lab.yml** 🆕 | 手動のみ | L4 ロンドン時間に入って長めに持つ（2026-09-30 夕・オーナー「そしたらテストをしてください」）＝ロンドン 08:00 に**サイトの通貨の強弱（`calc_currency_strength` と同じ計算・テストでサイトの関数と数字を突き合わせ済み）**でいちばん強い通貨を買い、いちばん弱い通貨を売って 8時間／1日／5日持つ（10ペア）。S1 と同じ費用・偽薬・p＜0.05÷3・5日は月ごとの幅。スワップは入れない。事前登録＝`PILLAR_PREREG.md`「L4」。`london_hold_lab.py`・テスト `tests/test_london_hold_lab.py`。出力は GitHub 側生成＝push 禁止 |
| **research-lists.yml** 🆕 | 手元の記録が届いたとき（push）＋手動 | 検証済みリスト `verified-list.md` と**昇格リスト `promotion-list.md`** を記録から組み立て直す（2026-09-30 オーナー「成績の良いものは昇格リスト、悪いものは検証済みリスト…後に改善して再検証」）。M6＝ポンド円・ロンドン時間の総当たり（足3×入口32×出口64＝6,144通り）を**手元で1回ずつ**数え、判定は **`screen_judge.py`（計算より先にコミット・手元が import）**＝件数200・幅・多重検定（これまでの総数で割る）・時期・偽薬→昇格候補→MT5 の実ティック→前向き1000回。記録＝`m6-screen.json`（手元で作って送る・判定と集計だけ）。直して数え直すときは新しいラウンドを登録してから。**昇格リストはメールの昇格エッジとは別物**。事前登録＝`PILLAR_PREREG.md`「M6」・テスト `tests/test_screen_judge.py` |
| **exit-ind-lab-4h.yml** 🆕 | 手動のみ | M7 腕A＝**4時間足で E1 と同じ総当たり**（入口60×出口64＝3,840通り・監視18銘柄・時間帯の縛りなし・2026-10-01 オーナー「同じ条件で4時間足と日足で検証」）。Yahoo 1時間足730日を UTC で4時間に束ね、区切り 2025-10-01・幅は銘柄×月・費用はサイトの仮の値。`exit_ind_lab_4h.py` は `exit_ind_lab.py` の関数を読むだけ（E1 の既定は不変）。**日足は E1 で数え済み（上位3つとも確かめで消えた）＝数え直さない**。腕B＝手元の MT5 実スプレッドで M6 の入口32×出口64（`research/mt5/m7_h4.py`→`m7-screen.json`）。事前登録＝`PILLAR_PREREG.md`「M7」・テスト `tests/test_exit_ind_lab_4h.py`。出力は GitHub 側生成＝push 禁止 |
| **event-dir-lab.yml** 🆕 | 手動のみ | S2 重要な発表のあと、動いた向きに乗るか逆らうか（2026-09-27 夜・オーナー「登録してください」＝B2 の続きの1問）。FOMC・米CPI・米雇用統計の発表を含む1時間足の向きに、次の足から乗る／逆らう。為替9ペア・偽薬＝向きだけコイン・p＜0.05÷2。事前登録＝`PILLAR_PREREG.md`「S2」。`event_dir_lab.py`・テスト `tests/test_event_dir_lab.py`。出力は GitHub 側生成＝push 禁止 |
| **round-lab.yml** 🆕 | 手動のみ | S3 キリの良い値（00・50）に初めて触れたあと、抜けるか跳ね返るか（2026-09-28 未明・オーナー「キリの良い登録はもう作ってください」＝スキャルピング本の最後の候補）。1時間足・為替9ペア・23pips ずらした値（23・73）と比べる・日ごとのまとまりで差の幅と p・p＜0.05÷2。事前登録＝`PILLAR_PREREG.md`「S3」。`round_lab.py`・テスト `tests/test_round_lab.py`。出力は GitHub 側生成＝push 禁止 |
| **candle-lab.yml**・**pattern-lab.yml** 🆕 | 手動のみ | FX本100冊の下調べ（手元の `research/fx-books/`）から持ち込んだ候補。C1＝シグナルの直前の足の形（ピンバー・包み足・2026-09-27＝差なし）／C2＝三尊・逆三尊を Osler & Chang (1995) の定義どおりに監視18銘柄の日足で数える（2026-09-28）。事前登録＝`PILLAR_PREREG.md`「C1」「C2」。`candle_lab.py`・`pattern_lab.py`（テストは `tests/` の同名）。出力は GitHub 側生成＝push 禁止。**本からの持ち込みは C2 で区切り** |
| **update-youtube-summary.yml** | 朝 10 / 11 | YouTube 10 ch 要約 |
| **news-ticker.yml** | 毎時 :37 | ⚡最新ニュース・ライブフィード（`build_news_ticker.py`→`news-ticker.json`・AI不使用。詳細は SYNC禁忌節の同名項目） |

### 環境変数 / GitHub Secrets
- `NEWSAPI_KEY`、`GEMINI_API_KEY`（Tier 1 課金）、`YOUTUBE_API_KEY`
- `GMAIL_USER` / `GMAIL_APP_PASSWORD` / `ALERT_RECIPIENT`（メール送信）
- `MY_TRADES_CSV_URL`（Google フォーム連携、オプション）
- `GITHUB_ACTIONS_RUN=true`（API 経由アップロード抑制、git push に委譲）

---

## 🚨 テクニカルアラート（核機能・概要）

### 監視銘柄 18 種
```
コモディティ:  GC=F (金), SI=F (銀), CL=F (原油)
指数:         NKD=F (日経CME), ES=F (S&P500), NQ=F (Nasdaq), YM=F (ダウ), ^FTSE
暗号:         BTC-USD
FX (JPY):     USDJPY, EURJPY, GBPJPY, AUDJPY
FX (USD):     EURUSD, GBPUSD
FX (AUD):     AUDUSD, EURAUD, GBPAUD
```

### ポジションプラン（ATR ベース、固定値）
- **SL** = エントリー ± ATR × 1.5
- **TP1** = エントリー ± ATR × 2.0（R:R 1:1.33）
- **TP2** = エントリー ± ATR × 3.0（R:R 1:2.0）

### 主要機能名（詳細ルールは `memory/04_technical_rules.md` 参照）
- シグナル検出: RSI / MACD / 移動平均 MA25-75 / ボリンジャー±2σ / 高値安値ブレイク
- **環境警戒スコア A〜D**（重要指標 / VIX / ATR レジーム / 危機キーワード / 市場休場）
- **通貨強弱マトリクス**（USD/EUR/GBP/JPY/AUD 9 ペアから算出、CS-5 閾値 ±0.05）
- **AUD ペア中国フォーカス**（上海・ハンセン連動、Gemini プロンプト調整）
- **往復ビンタ防止**（12h 反転検知、risk-manager は無条件見送り）
- **マルチタイムフレーム整合性**（1H↔4H↔日足、件名タグ ✅/⚠️）
- **B2 信頼度スコア**（HIGH/MID/LOW、HIGH のみ参照）
- **AI 敗因分析 + R4 勝因分析**（SL/TP ヒット時 Gemini 5 カテゴリ）
- **銘柄別クールダウン**（原油 24h / ドル円 18h / その他 12h、1H は一律 4h）
- **昇格エッジ限定メール**（2026-07-05）: `signal-lab-tracker.json` の status=promoted 仮説にマッチしたシグナルだけメール送信（照合=固定オラクル `signal_lab_verify.match`）。他は signals-log 記録のみ＝前向き検証は全量継続。無効化は env `EMAIL_PROMOTED_ONLY=0`。🆕 **観察中の候補メール（2026-09-26）**＝tracker の `watch=True`（tracking・edge）に当てはまる4Hシグナルは件名「👀観察中」・本文に「未確定」と登録前後の成績を付けて送る（押し目買いの2本・約2通/日。停止は `EMAIL_WATCH=0`）。照合は期間の条件を外して行う（`live_filter`）。tracker は同日から「全体との差」も昇格の条件にし、却下が決まった仮説を逆向きで自動登録する

---

## 📊 データファイル

| ファイル | 内容 |
|---|---|
| `signals-log.json` / `.csv` | 全シグナル発火履歴 + 結果（環境/通貨強弱/中国/反転/トレンド/敗因/勝因） |
| `my-trades.json` / `.csv` | ユーザーの実取引ログ |
| `technical-alerts-history*.json` | クールダウン管理（4H / 1H） |
| `economic-events.json` | 重要指標カレンダー + 市場休場 77 件（2026-2027 完全カバー） |
| `political-feed.json` | 政治発言フィード（30 分更新） |
| `youtube-summary-data.json` | YouTube 要約データ |

---

## 🤖 トレード分析チーム（Claude Code カスタム subagent、2026-05-27 構築）

**目的**: トレード成績向上のため、テクニカル × ファンダ × リスク管理の 3 視点で意思決定を支援。サイト運営の自動化とは別目的の組織。

| Agent | 配置 | 役割 | モデル |
|---|---|---|---|
| **technical-analyst** | `.claude/agents/technical-analyst.md` | チャート / シグナル / ATR / RSI / MACD / BB / MA / 出来高 | Sonnet |
| **fundamental-analyst** | `.claude/agents/fundamental-analyst.md` | 経済指標 / 決算 / 地政学 / 政治発言 / 金融政策 | Sonnet |
| **risk-manager** ⭐ | `.claude/agents/risk-manager.md` | 統合判断・規律遵守の門番。SL/TP/ロット算出、過信防止 | **Opus** |

### 想定ワークフロー
technical-analyst と fundamental-analyst を**同一メッセージ内で並列**に呼ぶ → 両方の結果をテキストで risk-manager に渡して統合判断（🟢条件成立／🟡グレー／🔴見送り推奨＋SL/TP/ロット）→ ユーザーが最終判断。

⚠️ 自動委譲のトリガー語は各 agent の `description` が唯一の真実（Claude Code が自動ロード）。**ここに書き写さない**＝二重管理を避ける。明示呼び出し例＝「risk-manager に聞いて、今 GC=F に入っていい？」

### 設計原則
1. **投資助言ではなく参考分析** — 各 agent は出力に必ず明記
2. **N=6 戦 6 勝の罠に注意** — 直近実績は小サンプル、risk-manager が過信を抑える
3. **規律の門番は妥協しない** — 金曜大引け・環境警戒 D・反転検知ありは無条件見送り
4. **サイト公開しない** — agent 出力はユーザー個人向け（無登録投資助言業リスク回避）
5. **連携はテキスト経由** — メインがテキストを橋渡し（subagent 間の直接通信なし）

---

## 🌐 サイト運営チーム（Claude Code カスタム subagent、2026-05-28 構築）

**目的**: marketwatch-jp.com のクオリティ向上。記事執筆・法務監査・SEO/UX の 3 観点で並列に動かし、サイト規模拡大と検索流入増を加速させる。

| Agent | 配置 | 役割 | モデル |
|---|---|---|---|
| **content-writer** | `.claude/agents/content-writer.md` | 解説記事の執筆・編集、個別銘柄解説、速報記事、見出し作成 | Sonnet |
| **compliance-reviewer** ⭐ | `.claude/agents/compliance-reviewer.md` | 法務監査（金商法・景表法・AdSense）、無登録投資助言業リスク判定、黒/グレー/白 3 段階評価 | **Opus** |
| **seo-ux-strategist** | `.claude/agents/seo-ux-strategist.md` | SEO（メタタグ・構造化データ・sitemap）、ナビバー・内部リンク、Core Web Vitals、モバイル最適化 | Sonnet |

### 想定ワークフロー
content-writer と seo-ux-strategist を**同一メッセージ内で並列**に呼ぶ → 両方の結果をテキストで compliance-reviewer に渡す（断定表現／個別銘柄推奨該当性／黒・グレー・白判定＋修正案）→ 統合して**8ステップルール**で公開。

⚠️ 自動委譲のトリガー語は各 agent の `description` が唯一の真実（Claude Code が自動ロード）。**ここに書き写さない**。明示呼び出し例＝「compliance-reviewer に新記事 AMD を事前チェック頼んで」

### 設計原則
1. **投資助言ではなく情報提供** — content-writer は断定表現を避ける、compliance-reviewer が事後監査
2. **黒/グレー/白の 3 段階評価** — compliance-reviewer は曖昧な「リスクあり」ではなく明確な判定
3. **SEO はホワイトハットのみ** — リンクファーム・隠しテキスト等は禁止
4. **8 ステップルール厳守** — 新記事追加時は必ず CLAUDE.md の 8 ステップに従う
5. **触ってはいけないファイルを認識** — 6 コア HTML + political-feed.html + track-record.html 等は cron 管理

---

## 🔄 SYNC_FILES の禁忌（重要・事故防止）

### ⚠️ 絶対に SYNC_FILES に含めないファイル

- 🆕 **`research/` 配下は丸ごとローカル専用**（2026-07-31・非公開研究）: `check_sync_forbidden` が**ディレクトリ単位**で error 停止＝**個別登録は不要**（経緯は SESSION_HANDOFF 同日節）
- **HTML 6 コアページ**: `index.html` / `calendar.html` / `charts.html` / `vix.html` / `market-health.html` / `hot-assets.html`
- **SEO 自動生成（2026-06-01 追加）**: `sitemap.xml`（`generate_market_news.py` の `build_sitemap_xml` が**全 guide-*.html を自動収集**して再生成、update-market-news が commit）。ローカルから push すると再生成版を一時的に巻き戻すため禁止。**記事追加時の手動 sitemap 編集も不要になった**（自動で全記事が載る）
- **workflow 管理ファイル**: `signals-log.json` / `technical-alerts-history*.json` / `track-record.html`
- **political 系**: `political-feed.html` / `political-feed.json`
- **YouTube 系**: `youtube-summary.html` / `youtube-summary-data.json`
- **ファンダ・ブリーフィング**: `fundamental-context.json`（予約エージェント routine `fundamental-briefing` が 1日2回 GitHub 側で生成・コミット。`generate_technical_alerts.py` と `generate_market_news.py` が読む。ローカルから push すると routine の最新版を巻き戻すため禁止）
- **週次ゾーン系**: `weekly-levels.json`（Actions `weekly-levels.yml` が**土曜 10:17 JST（＋土曜昼・日曜朝の保険）**に `compute_levels.py` で生成。2026-10-04 に日曜17時から前倒し＝実行が毎週21〜23時台にずれ込み、日曜夕方の routine 2本に間に合わず週次戦略が4週連続 verified=false だった）/ `weekly-zone-plan.md`（予約エージェント routine `weekly-zone-plan` が日曜 20:00 JST に生成、`weekly-zone-email.yml` がメール配信元として読む）。**どちらも GitHub 側で生成・コミットされるため、ローカルから push すると最新版を巻き戻す（fundamental-context.json と同じ事故）**
- **内部メモ系（2026-05-31・非公開・GitHub側生成）**: `article-ideas.md`(routine `article-idea-scout`,毎日07:30・記事ネタ)／`daily-preview.md`(`daily-market-preview`,21:00・翌日指標)／`political-digest.md`(`political-digest`,22:00・政治要約)／`compliance-scan.md`(`compliance-patrol`,日曜09:00・法務巡回)。**4件とも routine が main へコミット＝ローカルから push 禁止**
- **週次戦略コンテキスト（2026-06-01）**: `weekly-strategy-context.json`（routine `weekly-strategy-brief` `trig_01StownkcHrYyRbMMpVxVy2Z`、日曜 18:30 JST＝多エージェント起案→検証エージェントが全数値を weekly-levels.json と照合＋compliance→`verified:true/false` 付き生成）。`auto_weekly_strategy.py` が **verified=trueのみ**読んで週次戦略記事を描画（無ければプレースホルダ）。**routine が main へコミット＝push 禁止**
- **QAレポート（2026-06-01 追加）**: `site-qa-report.md`（routine `site-qa-lint` `trig_01Ph7pZ1WpjL8mZn7gXj5TEm`、土曜 10:00 JST。`check_site_consistency.py` を実行した整合性チェック結果）。**routine が main へ生成・コミットするため、ローカルから push 禁止**
- **指標結果速報（2026-06-05 追加）**: `indicator-result.json`（routine が重要指標の発表後に WebSearch で実数値・市場反応を生成・コミット。`generate_market_news.py` の `build_indicator_preview_banner` が読み、トップの注目指標バナーを「プレビュー→結果速報」に刷り替える）。**routine が GitHub 側で生成・コミットするため、ローカルから push 禁止**（SYNC_FILES に入れない）
- **パニック反発スキャン（2026-06-03 追加）**: `panic-scan.md`（GitHub Actions `panic-scan.yml`、毎日 7:27 JST。`panic_bounce_scan.py` が非FX9資産の「投げ売り＝反発候補」を出力）。**Actions が GitHub 側で生成・コミットするため、ローカルから push 禁止**（ローカル実行時に同名ファイルができるが SYNC_FILES に入れない）。前向き検証データ蓄積用の非公開メモ
- **記事下書き＋完全自動公開（2026-06-06 下書き／07-05 無人公開化）**: `drafts/draft-*.html` / `drafts/REVIEW.md`（routine `autodraft-article` `trig_01VpreEMybEJCmFiU5TS7Vet`、毎日 05:30 JST が心理＆リスク管理シリーズ下書きを生成）＋公開routine `autodraft-publish`（毎日 08:40 JST が最古の未公開下書きを仕上げ公開）。**routine が GitHub 側で生成＝SYNC_FILES に入れない**（下書きは `noindex,nofollow`＋robots.txt `/drafts/` Disallow＝**2026-08-01 にようやく実装**。それ以前は robots.txt に Disallow が無く 78本が実際にクロール可能だった＝下記「robots.txt の Disallow」節）。公開ゲート＝`check_guide_draft.py`（固定・編集禁止＝noindex/kinsho-v1/ナビ10/TODO/売買推奨NG/SVGはみ出し）exit0 → Opusコンプラ+品質(QUALITY_RUBRIC)白（🟡軽微はOpus修正→再ゲート→独立Opus確認）→ publish_article.py＋push。🔴黒/要協議/赤は REVIEW.md に🚩エスカレ。**例外＝`AUTODRAFT_GUIDE.md`／`AUTOPUBLISH_GUIDE.md`／`BOOKWATCH_GUIDE.md`は人間編集＝SYNC入り**。手順書=`drafts/AUTOPUBLISH_GUIDE.md`
- **研究アイデア受信箱（2026-07-07）**: `drafts/idea-inbox.md`（routine `idea-scout-weekly`、毎週日曜 14:00 JST＝WebSearchで検証可能な新手法・論文を最大3件・事前登録形式で**追記のみ**・重複回避は `drafts/idea-tested-slugs.txt`(SYNC入り)と照合）。**routine が GitHub側で追記＝SYNC外**（登録済・照合basename）。ローカル進化ループ（`mw evolve`／`research/DOCTRINE.md`）の①INTAKE
- **投資本 新刊ウォッチ（2026-07-05）**: `guide-new-books.html`（routine `book-watch-weekly`、毎週土曜 11:00 JST＝WebSearchで直近30日の投資系新刊を2ソース照合→中立紹介を最新40冊まで積み上げ）。**routine が GitHub側で更新＝SYNC外**（check_site_consistency の SYNC_FORBIDDEN 登録済）。手順書=`drafts/BOOKWATCH_GUIDE.md`（SYNC入り）
- **週次トレード自己レビュー（2026-06-06）**: `my-trade-review.md`（routine `weekly-trade-review` `trig_01LgSjdK2is5m6oP7ta1mh7z`、毎週土曜 12:00 JST が `my-trades.json` を分析＝敗因/遵守度/改善点の非公開メモ）。**GitHub側生成＝SYNC外**。読む対象＝`my-trades.json`／`MY_TRADING_RULES.md`(発注前チェックリスト・SYNC入り)／`economic-events.json`。本人の自己点検
- **シグナル研究日誌・日次研究会＋自動公開（2026-06-11 / 06-13 自動公開化）**: `signal-lab-ledger.md`（台帳）/ `drafts/draft-signal-lab-*.html` / `drafts/labnotes/lab-*-analysis.md` / `drafts/labnotes/lab-*-claims.json`（routine `signal-lab-daily` `trig_01V4A37Xow1vx2QAAvYwzR57`、毎朝 06:10 JST＝NY引け後。投資3視点で勝率改善仮説を**1日1本だけ**signals-logで反実仮想検証→下書き＋labnotes＋claims.json＋台帳を生成）。**routine が GitHub 側で生成＝SYNC_FILES に入れない**。自動公開ゲート＝①`signal_lab_verify.py`（**SYNC入りの固定コード＝独立オラクル・routine/agentは編集禁止・実行前に `git checkout` で確定版へ**。claims.jsonの全k/nをsignals-logから独立再計算して突合＝捏造不可＋『30秒まとめ』%完全性＋SVG＋**未対応フィルタキーは即赤**）exit0 → ②Opusコンプラ白なら自動公開（🟡軽微はOpus自己修正[表現軟化・免責のみ・数値/SVG不変]→数値再検証→別の独立Opusが白確認／🔴黒・要協議・検証赤・未対応次元は REVIEW.md に🚩エスカレ）。filterキー＝ticker/group/direction/trend/tf/signal/signals_all(コンボ=全シグナル同時発火・2026-07-19)/reversal_long/blocked/tier/env(環境警戒A-D・2026-07-19)/regime(RISK_ON等・2026-07-19)/rsi_band・ma_pos・macd_side(指標ステート・2026-07-20)/news(注目度0/1-2/3+・Q24・2026-07-23)/regime4(Q34・2026-07-27)/fired_before・fired_from(IS/FWD期間分離・2026-08-12＝IS/FWD比較記事は期間をclaimsで宣言必須。詳細はSIGNAL_LAB_SOP)/family・adx_band・vix_band・asset_class(環境の相性ラボ regime_lab.py の候補の前向き追跡用・2026-09-26・エンジンのメール照合には未対応)/fbias(ファンダの見立てとシグナルの向き＝aligned/mismatch・signal_env_profile.py の「傾向あり」の前向き追跡用・2026-09-26・メール照合には未対応)/cs_align(通貨の強弱とシグナルの向き＝aligned/against・FX本100冊の候補の前向き追跡用・2026-09-28以降の発火のみ・2026-09-27・メール照合には未対応)。groupには拡張ユニバース5キーあり(metal_x/energy_x/rates/crypto_x/index_x=1d拡張8銘柄・Q23・2026-07-23＝既存groupと非重複・トラッカーは拡張group仮説のみ凍結迂回)。⚠️`--category`＝「AIシグナル研究日誌」(絵文字なし・🧪は--emoji)。記事番号は台帳管理。**エンジン・発火条件・固定オラクルには絶対触れない。人間の役割＝エスカレ回のレビューのみ**
- **X(SNS)投稿ドラフト（2026-06-13）**: `drafts/sns/<YYYY-MM-DD>.md`（routine `sns-post-daily` `trig_01VkDY4djA8WAAZavhgu3j4M`、毎日 07:00/19:00 JST＝cron `0 10,22 * * *` UTC・JST時刻で朝/晩出し分け。@rx009898 が手動コピペするX投稿文を生成。価格=Yahoo／地合い=fundamental-context.json／イベント=economic-events.json・280字以内・免責短縮版）。**GitHub側生成＝SYNC外**。⚠️X API自動投稿はしない（無料枠2026-02廃止＝コピペ専用）。`/drafts/` は robots.txt Disallow 済（2026-08-01〜。下記「robots.txt の Disallow」節）
- **シリーズ自動公開レーン（1日1本・キュー駆動。2026-08-31 に一覧化）**: 手順書＋題材キューは **SYNC入り（人が編集）**、台帳と記事は **GitHub側生成**。
  - ~~`proverb-daily-auto`~~ ＝投資格言。**2026-09-05 に #50「全48回 総目次」で完結し、routine は削除済み**（2026-09-10 に `list_triggers` で不在を確認）。手順書 `drafts/PROVERB_GUIDE.md`／台帳 `drafts/proverb/PROVERB_LEDGER.md`／記事 `guide-proverb-*.html` は**残す**が、**`check_automation_health.py` の `QUEUE_LANES` からは外した**（2026-09-17＝畳んだレーンを見張ると毎朝必ず赤くなり番人の信用が落ちる。**レーンを足したら登録・畳んだら解除**が対の手順）（48本は公開中・前後ナビの並びにも使う）。📌 和の相場格言は44本でほぼ汲み尽くし、2度の枯渇を経て総集編で締めた＝**キュー駆動のレーンは「畳み方」を先に決めておく**という前例
  - `tse-daily-auto` `trig_01HbSi32JHhWEhoUK2erQhJr`（毎日 11:37 JST・model=claude-sonnet-5。**2026-08-31 新設＝格言の後継**）＝東証のしくみ。手順書 `drafts/TSE_GUIDE.md`（題材18件）／台帳 `drafts/tse/TSE_LEDGER.md`／記事 `guide-tse-*.html`。🚨 **このレーンだけの絶対条件＝制度の数値は一次情報（jpx.co.jp / fsa.go.jp / e-Gov）を実際に開いて確かめ、本文に確認日を書く。届かなければ書かずにエスカレ**
  - 🔁 **`company-daily-auto` `trig_01ERd5oZBggR1LaxF6c2BXw3`（毎日 10:23 JST・エージェント作成＝プロンプトと時刻をエージェントが直せる・2026-10-04 新設）**＝毎朝、**リポジトリ付きの専用セッション `session_0193RuD1wE9JzE6VKK4pMa3U`（「📊 数字で見る企業（毎日の専用セッション）」）を起こす**型（🚨 エージェントが作る「毎回新しいセッション」型のルーティンはリポジトリも add_repo も無く動けない＝2026-10-04 に試験で確認。オーナーの画面操作なしで最後まで動かすためにこの型にした）＝オーナー指示「最低でも1日1本以上…必ず1本以上は上げてください」で週1本→**毎日1本以上**。候補が消えても書かずに終わらず `COMPANY_GUIDE.md` §2-1 の7「代わりの順」で必ず1本（§0 の禁止・中3営業日・一次情報の線は下げない）。作業は origin/main の git worktree（/tmp/co-pub）で行う。候補は `edinet-yuho.json` の `cooled: true`（中3営業日を満たす）が先頭に並ぶ（`build_edinet_yuho.pick_candidates`・旧版は話題の真っ最中の15社だけで10/3に日本株が全滅した）。番人＝LEDGER_WATCH 2日。旧 `company-weekly-auto` `trig_017X6e1WvUm2FBvyegzFkAUh`（毎週土曜 14:23 JST・オーナー作成＝エージェントからは止められない）は、手順書の先頭の指示で**次の起動時に自分を止める**
  - （旧）`company-weekly-auto` `trig_017X6e1WvUm2FBvyegzFkAUh`（**毎週土曜 14:23 JST**・model=claude-sonnet-5。**2026-08-31 新設**）＝数字で見る、話題の企業。手順書 `drafts/COMPANY_GUIDE.md`／台帳 `drafts/company/COMPANY_LEDGER.md`／記事 `guide-company-*.html`。🔑 **このレーンだけキューを持たない**＝題材を機械的に選ぶので**構造的に枯渇しない**（**日本株**＝`jp-rankings.json` で直近14日に gainers/losers/hot へ2回以上／**海外株**＝`earnings-calendar.json` の `us` で決算発表から2営業日〜14日、無ければ直近15〜60日のニュース記事で主役だった海外企業）。**台帳の最新1件と違うほうを毎週の第1候補にして日米を交互に回す**（2026-08-31 オーナー指示「海外の企業も日本株に大きく影響を与えるので記事にしてほしい」）。🆕 **既刊とかぶってもよい——むしろ「続報」にする**（同オーナー指示「前回と今回じゃ状況が違う／むしろあの後どうなったのかも気になる」）＝既刊がある会社は §1⓪「前回の記事のその後」を必須にする。🚨 **⓪で既刊から引くのは事実・数字・公開日だけ**（評価語は引用しない＝いまのゲートで禁じた表現を再生産しないため。「前回の見立てが当たった/外れた」も書かない＝的中率の主張になる）。本レーン内のローテーションだけ90日あける（大きな動きがあれば例外可）。その代わり残量では止まったことを検知できないため、`check_automation_health.py` の **`LEDGER_WATCH`（台帳の最終更新が10日超で警告）**で見張る。🚨 **絶対条件＝①目標株価を書かない ②買い/売り/保有を推奨しない ③割安・割高と断定しない ④将来を予測しない ⑤証券会社名を列挙しない ⑥急騰急落の当日・翌日に書かない**。「将来性」は結論ではなく **上がる材料／下がる材料を対で並べるだけ**（オーナー指示 2026-08-31。重み付けも結論の文も書かない）。⚠️ **ニュースレーンと題材が衝突する**（デイリーニュースも個別銘柄を扱う）ので、直近14日の `guide-news-*.html` と `NEWS_LEDGER.md` を見て同じ会社ならその週は見送る手順を両方の手順書に入れてある
  - 投資詐欺は手順書 `drafts/SCAM_GUIDE.md`／台帳 `drafts/scam/SCAM_LEDGER.md`／記事 `guide-scam-*.html`（2026-08-13 新設・格言の枯渇を受けて発足）
  - 🆕 `entry-daily-auto`（毎日 12:23 JST・2026-09-25 新設）＝エントリー方法の研究。手順書 `drafts/ENTRY_GUIDE.md`（題材26件・SYNC入り）／台帳 `drafts/entry/ENTRY_LEDGER.md`／記事 `guide-entry-*.html`（GitHub側生成＝SYNC外）。**広告なし**（`DENY_PREFIX`）。🚨 論文の数字は実際に見た出典（要旨・公式PDF）からだけ書き、確かめられない数字は書かない。全25回＋総まとめで完結＝完結したら `QUEUE_LANES` から外して routine を止める
  - 🚨 **レーンを増やしたら、必ず `check_automation_health.py` の `QUEUE_LANES` に登録すること。**§⑤は「キュー枯渇による静かな停止」を捕まえる番人なのに、2026-08-31 まで **autodraft の1本しか見ておらず**、投資格言5日連続・投資詐欺7日連続の枯渇を誰も知らないまま放置していた（ルーティン自身は毎日きちんと台帳へ「🚩補充依頼」を書いていた）。🆕 **もう1つ＝guides.html に `data-category="<--category と同じ名前>"` 付きの空の欄とジャンプ欄の1行を先に作る**（無いと publish_article のカテゴリゲートで1本目が止まる。2026-09-26〜）
- **デイリーニュース記事 完全自動公開（2026-06-15→06-17 クラウド化）**: クラウドルーティン **`news-daily-auto`（`trig_01WZ9maArFYwaxyq99KJLJBi`、毎日 17:40 JST＝cron `40 8 * * *` UTC）**が手順書 `drafts/NEWS_DAILY_GUIDE.md` に従い最重要ニュースを「話題性×影響×付加価値」でスコア→**1本だけ**中立整理→**Opus自動公開ゲート（signal-lab方式＝決定論チェック[免責三層/禁止語/銘柄推奨無し/出典2系統]→🟢白は `publish_article.py --category "今日のニュース"`＋push／🟡軽微はOpus自己修正→別Opus確認／🔴黒・要協議・事実未確定はエスカレ）**で公開。公開物＝`guide-news-<YYYY-MM-DD>-<slug>.html`（通常記事）＋`guides.html`「今日のニュース」カード＋`drafts/news/NEWS_LEDGER.md`（GitHub側生成＝SYNC禁忌）。**薄い日は見送り**（合計9/15未満等）。個別銘柄は「買い/売り」と読ませないフラット整理厳守。⚠️旧ローカル `news-daily` は無効化済（二重公開防止でクラウド一本化）。手順書 `NEWS_DAILY_GUIDE.md`＝人編集＝**SYNC入り**・`drafts/news/*`はSYNC外。クラウドroutineは `RemoteTrigger`（list/get/run/create/update）で管理

- **⚡最新ニュース・ライブフィード（2026-07-09／08-06 ソース拡張）**: `news-ticker.json`（Actions `news-ticker.yml`、毎時37分＝`build_news_ticker.py` が固定媒体+公的機関+トピック横断検索（**単一の真実は `FEEDS`**）から最新24件を時刻降順で生成・`feed_health` 付き＝automation-health §⑦ がソース停止を検知。index.html がJSで閲覧時fetch）。**Actions が GitHub側で生成＝ローカルから push 禁止**（SYNC_FORBIDDEN 登録済）

- **話題の企業の有報本文（2026-09-02）**: `edinet-yuho.json`（Actions `edinet-yuho.yml`、平日 19:40 JST＝`build_edinet_yuho.py` が `EDINET_API_KEY` で jp-rankings 由来の候補企業の有報「事業等のリスク」等と主要指標を取得。routine `company-weekly-auto` はこれを読むだけ＝クラウド routine は Secrets を読めないので API を直接叩かない）。**Actions が GitHub側で生成＝ローカルから push 禁止**（SYNC_FORBIDDEN 登録済）
- **研究ラボの出力（2026-09-26）**: `exit-lab.*`／`exit-wall-lab.*`／`stop-lab.*`／`regime-lab.*`／`signal-env-profile*`／`pillar-lab.*`／`pillar-lab-jp.*`／`trend-lab.*`／`combo-lab.*`／`combo-forward.*`／`box-lab.*`／`event-dir-lab.*`／`round-lab.*`／`candle-lab.*`／`pattern-lab.*`／`yori-lab.*`／`yori-forward.*`／`london-lab.*`／`london-hold-lab.*`／`verified-list.md`／`promotion-list.md`（Actions が生成・**前向きの判定の履歴を持つ**＝古い版で上書きすると積み上げた判定が消える）。SYNC_FORBIDDEN 登録済み
- **日本株ランキング（2026-06-20）**: `jp-rankings.json`（Actions `jp-rankings.yml`、夕 16:40/17:10 JST＝クローズ後・朝実行はcron遅延で廃止。`build_jp_rankings.py` が Yahoo価格で値上がり/値下がりトップ20生成→`generate_market_news.py` の `build_jp_rankings_section` が hot-assets 最上段に描画）。**Actions が GitHub側で生成＝ローカルから push 禁止**。※`jp-stock-info.json`（赤字黒字/名前/業種の静的）と `build_jp_rankings.py` は SYNC入り＝ローカルで `make_jp_stock_info.py` で四半期更新して push

**理由**: これらは cron / 予約エージェントが GitHub 側で生成・push するファイル。ローカルから push すると古いファイルで上書きされ、**ライブページが過去日付に巻き戻る事故**（実例: 2026-04-24）。

HTML を即座に反映したい場合は GitHub Actions の "Run workflow" で手動 trigger。

### SYNC_FILES に含めるもの
- Python スクリプト（`generate_*.py` など）
- GitHub Workflow（`.github/workflows/*.yml`）
- `robots.txt`, 個別 guide-*.html（※`sitemap.xml` は **SYNC禁忌へ移動**＝下記参照。generate_market_news.py が全guideを自動収集して再生成するため、ローカルから push しない）
- `economic-events.json`, `my-trades.json`
- Claude Code 設定（`.claude/agents/*.md`）
- ドキュメント（CLAUDE.md, SESSION_HANDOFF.md, memory/*.md）

### 🤖 robots.txt の Disallow（2026-08-01 実装）

**手で編集しても消える**＝`build_robots_txt()`（`generate_market_news.py`）が毎回の update-market-news で再生成→commit するため。**変更は必ず `build_robots_txt()` に書く**（手動編集が7分で消えた実例＝SESSION_ARCHIVE【2026-08-06 退避】）。

遮断＝`/drafts/`（下書き+REVIEW.md+labnotes/news/proverb/sns）・`/memory/`（投資家プロファイル）・`/*.md$`（routine が増やすので個別列挙しない）。`Allow: /` と併存可（**より具体的な規則が勝つ**）・.md へのサイト内リンク0件・sitemap にも不掲載。

⚠️ **非公開化ではない**＝行儀の良いクローラにしか効かず `raw.githubusercontent.com` 経由の露出（2026-07-26）は塞げない。恒久策＝下書きを public に置かない、は未着手

---

## 📋 新記事追加の 8 ステップ（毎回必須）

> 🆕 **2026-06-01：②〜⑤は `publish_article.py` で機械化（推奨）**。手作業のミス（カード位置・sitemap・SYNC_FILES漏れ・更新履歴の件数/順序崩れ）を防ぐため、記事HTMLを書いたら次の1コマンドで②〜⑤を冪等に実行できる：
> ```
> python publish_article.py --file guide-xxx.html --category 個別銘柄解説 --emoji 🏰 \
>     --card-title "カード/履歴用の短めタイトル" --desc "カード説明文"
> ```
> 日付・読了分は記事HTMLから自動抽出。`--dry-run` で変更確認。再実行しても二重化しない。実行後は ⑥sync → ⑦workflow → ⑧確認。以下は中身の参考（手動でやる場合）:

1. 新 HTML ファイル作成（既存 `guide-*.html` のデザインを踏襲）
2. `guides.html` の該当カテゴリに記事カードを追加（最新が最上段）
3. ~~`sitemap.xml` に `<url>` ブロック追加~~ → **不要**（`build_sitemap_xml` が自動再生成・SYNC禁忌）
4. `sync_to_github.py` の `SYNC_FILES` に新 HTML を追加
5. `generate_market_news.py` の「📰 更新履歴」＝`build_html()` 内の **`_history_items` リスト**（`{"date","line"}`）に **1件追加するだけ**（`date` は `YYYY-MM-DD`。日付降順ソート＋最新5件キープは描画側が自動＝手で削らない。⚠️旧記述「push out 方式」「`<br>` 調整」は誤り＝2026-07-28 訂正）
   - ⚠️ **週次戦略記事（`guide-weekly-*.html`）は手動追記しない**：`build_weekly_history_item()` が自動検出してリストに加える（index.html のバナーも自動）。手で足すと二重になる
6. `sync_to_github.py` 実行で push
7. GitHub Actions の `Update Market News` を `workflow_dispatch` で手動起動 → index.html 再生成
8. ライブ反映確認（HTTP 200、更新履歴の表示、guides.html での表示）

⚠️ 速報系記事は書く前に **「日付の事実確認」を WebSearch で実施** すること。

---

## 🛠️ 保守ツール / 運用CLI（2026-06-01 新設）

**設計思想：ルールが増えても破綻しないよう「人間が手で守る」を「コードが自動で守る」に置き換える。新ルールはチェックを1個足す形で拡張する。**

| ツール | 役割 |
|---|---|
| **`mw.py`**（司令塔CLI） | `python mw.py check / publish / sync / trigger <wf> / status [wf] / routines`。スクリプト名を覚えずに運用できる単一入口 |
| **`check_site_consistency.py`**（リンター） | サイト不変条件を自動検査：**🆕公開保留のはずの記事がルートに残っていないか（カード無し＆noindex無し＝error）**／**🆕連番シリーズの回番号（重複・ファイル名とタイトルの #番号の不一致）**／**🚨SYNC禁忌の混入（巻き戻し事故防止）**／免責 kinsho-v1／10ボタンナビ／SYNC_FILES・sitemap・guidesカード登録／リンク切れ。errorで exit 1。**新ルールはここに検査を追加** |
| **`publish_article.py`** | 記事公開の②〜⑤を1コマンド・冪等（`mw publish` が内部で使用）。🆕**上書きゲート**＝git の HEAD 版と `datePublished` が違えば「公開済み記事を別記事で上書き」と判断して中止（`--allow-overwrite` で解除）。2026-09-06 に #089 が消えた事故の再発防止。🆕**置き場所ゲート**＝直下以外（drafts/ の下書きなど）は中止・上書きゲートは **origin/main とも比べる**（2026-10-04 #115 事故＝下書きのパスを通してゲートが素通り）。点検側は §10（カードの日付＝記事の公開日・drafts/ を指すカード）。🆕**カテゴリゲート**＝入れる欄が決まらなければ書き込む前に中止（旧版は記事一覧の先頭＝計算ツール欄へ黙って入れ、47枚が紛れた。2026-09-26）。点検側は `check_site_consistency` §8 が data-category の欄への紛れ込みを error |
| **`apply_logo.py`** 🆕 | サイトロゴ（案C・favicon+ヘッダーSVG）を全HTML+生成スクリプト9本へ冪等適用（2026-07-04導入済み。ロゴ変更時はSVG定数を編集して `--apply`） |
| **`apply_series_nav.py`** 🆕 | 連続シリーズ記事の末尾に「前の記事／次の記事」ボタンを冪等に敷く（2026-09-05 読者要望）。対象＝signal-lab / proverb / scam / tse / news（2026-09-09 時点 242本）。並び順は記事の `datePublished`（同日はファイル名）＝人が順番を管理しない。ただし **signal-lab だけ `"order": "number"`＝ファイル名の回番号順**（読者は #88→#89→#90 と番号で辿るため。2026-09-06 の上書き公開事故で公開日と番号が食い違った）。**update-market-news.yml が毎回 `--apply` して commit** ＝新記事が出ると「1つ前の記事の“次の記事”」も自動で貼り替わる。⚠️ 手で前後リンクを書かない（必ず腐る）。🆕 **noindex の記事は並びに入れない**（2026-09-17＝🚩エスカレ中の #097 へ #096「次」/#099「前」から到達できた） |
| **`sync_economic_events.py`**（月次同期） | `ECONOMIC_EVENTS_2026` → `economic-events.json` を毎月25日に生成。**警告が鳴るかどうかはここが全て**＝`RULES` に規則が無い指標は生成されず、環境警戒スコアの対象外になる。🚨 **2026-09-17 大改修**: 英・ユーロ・中国・日本の12種を追加（それまで ⚠️未分類が22件あり、BOE は手で足した6月・7月の2件が再生産されず8月以降消えていた＝9/17の無警告の原因）。🚨 **影響銘柄は `AUD_PAIRS`/`JPY_CROSS`/`CN_SET`/`JP_SET` に集約**（中国指標に豪ドルが、日銀に円クロスが入っていなかった実害を受けて。オーナー指示「中国の指標も豪ドル系に効く」）。⚠️ 現地時刻＋tz で書く＝夏時間は zoneinfo に任せ、JST を手計算しない。⚠️ `json_pattern` は緩くしない（`r"日銀"` が日銀短観まで拾い、誤った食い違い警告と二重登録を生んだ）|
| **`verify_uk_eu_calendar.py`** 🆕 | **英・ユーロ圏**の発表日を一次情報と突合（2026-09-17 オーナー指摘「今日の英指標が載っていない」＝**英中銀の政策金利発表が1件も入っていなかった**。監視18銘柄のGBP/EUR ペアと ^FTSE を直接動かすのに穴だった）。取得先＝英中銀 MPC日程／ECB 理事会日程／ONS 各速報の Next release。🚨 **BOE の表は年を書かない**（「Thursday 5 November」だけ）＝見出しの年を拾う。🚨 **ECB は日付行と説明行が別**＝次行を見て「(Day 2)」だけ採る（2日目が発表日）。⚠️ **ONS が確定公表するのは次回1件だけ**＝先の月を勝手に埋めない。⚠️ **検証するのは日付のみ・時刻は未検証**（JST換算式は economic-events.json の note 側）。⚠️ 未登録の指摘は `HORIZON`（460日）まで＝ECBの2028年分まで毎週鳴らさない |
| **`verify_economic_calendar.py`** 🆕 | 米指標の発表日を**一次情報（BLS 公式スケジュール）と突き合わせる**（2026-09-11 の CPI 日付誤りの恒久対策）。🚨 **曜日ルールは足さない**＝正しい金曜(9/11)を弾いて誤った木曜(9/10)を通してしまう。日付の正しさは推測では決まらない。⚠️ **解析6件未満・今日以降の比較0件も失敗扱い**（「検証できなかった」を「問題なし」と取り違えない）。`verify-calendar.yml` が週1で実行 |
| **`check_plain_japanese.py`** 🆕 | 研究日誌の「やさしい日本語」検査（2026-09-23 オーナー指示「記号をなくし、初心者にもわかる日本語で」）。記号（≤ × →）・N=・R・プログラム用の名前・英字の略語・専門用語・用語の初出説明を見る。**signal-lab-daily が 8-1 の前と 8-4 i のあとに実行**（赤は言葉だけ直して最大5回→だめならエスカレ）。規則は `RULES` が単一の真実・人が読む版は QUALITY_RUBRIC「やさしい日本語」節。⚠️ 表見出しの IS/FWD は日本語つきなら残す（verify の期間取り違え検査の目印）。テスト＝`_test_plain_japanese.py` |
| **`apply_site_frame.py`** 🆕 | サイト共通の枠を冪等に敷く（2026-09-23）。①`<style data-mw-frame>`（ナビ6+5・広告余白）②解説記事のヘッダーを標準形へ（`<h1>`入りの表紙ヘッダーは残す）③ナビを11ボタンへ（置換分は `nav-bar mwf-nav`＝ページ側CSSに依らず同じ見た目）。⚠️ 本文・記事メタ行には触らない |
| **`inject_ads.py`** | A8.net のアフィリエイト広告を記事末へ冪等注入し、**記事ごとの候補から1つをランダム表示**する（`CREATIVES`＝素材の唯一の定義／`POOLS`＝記事→候補。`mw-ads.js` は CREATIVES から自動生成＝直接編集禁止）。🚨 **2026-09-10 に設計上の欠陥を修正**＝旧方式は PC/SP 両方を HTML に置き CSS で隠していたが、ブラウザは `display:none` の `<img>` も読むため**見えていない側の1x1計測gifまで毎回飛び、表示回数が実測で約2倍**になっていた（Chromium 実測）。新方式は選ばれた1つだけを JS で描画＝表示した分だけ計測。JS無効は `<noscript>` で候補の先頭を1つ。**「広告」ラベル必須**（景表法ステマ規制・2023-10-01 施行）。⚠️ **本文に推奨文・煽り文言を足さない**（金商法の誇大広告／投資勧誘に寄せない）。既存＝DMM株・DMM CFD・JFX株式会社（22記事）。移行は `--replace` |
| **routine `site-qa-lint`** | 土曜10:00 JST にリンターを自動実行→`site-qa-report.md` に報告（人が気づく前に検知） |
| **routine `failure-mail-patrol`** 🆕 | 毎朝 08:57 JST（`trig_01BYipEtVEsakf4bSFMe5sEc`・2026-09-28 オーナー依頼「1日1回失敗メールを巡回」）＝**`failure_patrol.py`** で直近26時間の失敗した実行を集め（ワークフロー×ブランチ・そのあと成功したか・失敗した段階・見張り番の🚨行と§④のコミットが PR 経由か）、1件ずつ原因と状態を確かめて報告（通知＝スマホ・メール）。小さく確かな直しだけ PR→検査→マージ（1回2件まで・ゲート不可）。手順書＝`drafts/FAILURE_PATROL_GUIDE.md`（SYNC入り）。🚨 **予約エージェントのリポジトリとコネクタは claude.ai のルーティン編集画面で付ける**（`create_trigger` には項目が無い＝付けないと `api.github.com` でもこのリポジトリは 403。試運転2回で判明し、同日オーナーがリポジトリと Gmail を付けた）。`mcp__github__*` は無いことがある＝`api.github.com` を curl で読む（認証はプロキシが付ける）。**ログは読まない**（2026-09-28 オーナー判断「原因がわかって直せればよい」）＝原因は失敗した段階の名前＋手元で再現（鍵が要る段階は再現せず、そのあと成功したかで判断）。**repo にファイルを書かない** |
| **`auto_pull.py`** 🆕 | **手元の Claude Code の起動時に、手元を GitHub の最新へ自動でそろえる**（2026-09-26・オーナー指示「研究はとても大事なので作って」。手元専用＝クラウドでは何もしない）。GitHub の ZIP を1回取るだけ＝API 不使用。手元で書き換えていないファイルだけ更新／**手元で書き換えたファイルは触らず「手元だけ変更＝送ればよい」「両方で変更＝統合が必要」を見分ける**（判定は前回そろえた版の指紋＝`_auto_pull_state.json`・時刻では決めない）／GitHub 側で作るデータ（SYNC禁忌）は控えを残して最新に／`_cloud_ledger.txt` も更新。**触らない**＝`research/`・`_`始まり・`sync_to_github.py`・`mw.py`・`.sync-cache.json`。設定は `python auto_pull.py --install-hook`（`.claude/settings.local.json` の SessionStart）。テスト＝`tests/test_auto_pull.py` |
| **`_reconcile.py`** 🆕 | ローカルと本番の差を**向き付き**で出す（ローカル専用・既定dry-run・`--apply`で取り込み・上書き前バックアップ）。このリポジトリは routine が**本番へ直接書く**ので**ローカルは構造的に遅れる**。L(ローカル)/R(本番)/B(`.sync-cache.json` の remote_sha＝前回sync時点) の3shaで「取り込み候補」と「ローカルが新しい」を判別。🚨 **時刻の新しさは正しさではない**ので、取り込む前に本番側のコミットとパッチを見せ、**追加0・削除のみ＝巻き戻しの疑い**に目印を付ける（`--patch` で中身も表示）。⚠️ 記事ミラーの遅行は従来どおり `_pull_mirror.py`（`guide-*.html` のクラウドレーン専用）|
| **`style_diagnosis.py`** 🆕 | **投資スタイル診断**（2026-09-27 オーナー依頼「自分にどんなスタイルが合っているか」）。MT4 の口座履歴（Statement.htm）を読み、保有時間（スキャルピング／デイトレ／スイング／長め）ごとに**費用込み・ロットに左右されない物差し（1日の値動きATRの何倍か）**で数え、**値動きの大きさ・流れの向き・前半後半のどれでもプラスか**まで見て ◯△▽✕？ を出す（判定の決まりは定数に固定）。🚨 **口座履歴は個人の記録＝入力も出力も `research/` の下**（出力は既定で `research/style-diagnosis/`）。`check_site_consistency` が `Statement*.htm` の SYNC 混入を error で止める。手元で `python style_diagnosis.py research/Statement.htm`（値段は Yahoo＝手元から）。テスト＝`tests/test_style_diagnosis.py` |
| **自動売買 AT1〜AT3**（`ea_bridge.py`・`ea_ledger.py`・`build_signals_recent.py`）🆕 | ⏸️ **2026-10-01 夜 オーナー決定で保留＝手元の EA・タスクは全部止める（AT3 の窓は判定なし）。再開は新しい期間を登録してから**。2026-09-30 オーナー「主戦場はロンドン時間の5分足とスイングの4時間足。攻めと守りの自動化を両方同時に」。**AT1 守りの見張り番**（本番・手動の建玉も全部＝損切りなし・2%超・同じ賭けの重ね・重要発表の60分前〜30分後・1日−3%〔値はオーナー確認待ち〕・金曜15:00）／**AT2 5分足の執行アシスト**（入るかはオーナー・ロット/損切り/利確/建値/18:00手じまい/記録を自動）／**AT3 4時間足のメールの合図をデモで自動に建てる**（前向き・300回でマイナスならストップ・1000回で判定・本番へは tracker の昇格＋デモ30回で下限＞0）。🚨 **EA（MQL4）は手元の `research/ea/` だけ＝リポジトリに入れない**（Pages が全ファイルを配信するため）。リポジトリ側＝`build_signals_recent.py`（technical-alerts が `signals-recent.json` を書く・SYNC禁忌・失敗しても止めない）→ 手元 `ea_bridge.py`（5分ごと・Common\Files へ UTF-16 の CSV）→ EA → `ea_ledger.py`（AT3 だけ `auto-forward.json` を送る＝R だけ・検証済みリストの SOURCES 登録済み／AT1・AT2 は手元の報告だけ）。🆕 **AT3 の振り返り**（2026-10-01）＝ずれ（遅れ・入った値・結果が変わった回・サイトの記録との差）／見送りの答え合わせ／AI の敗因／**直す候補**（文だけ・自動では入れない＝次の期間の登録で選ぶ）→ `research/ea/at3-review.md`。🆕 **AT4 約定の試験**（2026-10-01 オーナー「1日に100回ぐらいデモで取引すれば確認できる」）＝MT5 デモで日本時間15時〜翌2時に6分ごと・0.01ロットを60秒で往復・3営業日→スプレッド・滑り・約定時間・費用÷1R（5分足/4時間足）を `research/ea/at4-probe.md`（AT3 の記録・判定に混ぜない）。事前登録＝`PILLAR_PREREG.md`「AT」・テスト `tests/test_ea_tools.py` |
| **LP ドル円5分足の「取引→検証→改善」の繰り返し**（`loop_judge.py`）🆕 | ⏸️ **2026-10-01 夜 保留（台帳は止めた・方針を「予測」から「守り＋株価指数ロング＋費用と税」へ）**。2026-10-01 オーナー「10万円のデモ口座で1日平均3%以上…取引の検証をして、改善をして、また取引をする。目標を達成するまで繰り返す設計」。**1周＝登録（仕組みの理由つき）→過去で数える（手元 `research/loop/loop_lab.py`・MT5 の実ティック5分足・選ぶ 2022-06〜2024-07／確かめ 2024-08〜・数分）→関門A（段0＝確かめ期間の日次平均の下限＞0 かつ 偽薬 p＜0.05÷確かめた回数の累計〔M5-3 の6から〕）→デモの前向き（`research/ea/MW_Loop5.mq5`・窓＝100回かつ10営業日）→段1〜4→振り返り→次の登録**。物差し＝1日の損益率（日本時間 07:00 区切り・1回1%・−3%/日の上限を過去にも入れる）。**段（S1 0超／S2 +0.3%／S3 +1%／S4 +3%＝オーナーの目標）はデモの数字だけで上がる**。止める決まり＝12ラウンドで段1に届かない／段0が3回続けてデモで消える。台帳＝`research/loop/loop-ledger.json`（手元専用・金額なし）。🚨 3%/日＝費用後 +3R/日＝これまでの数字（費用13%/回・力ほぼ0）からは遠い＝段階の一番上として置く。事前登録＝`PILLAR_PREREG.md`「LP」・テスト `tests/test_loop_judge.py`。🆕 **結果（2026-10-01）＝LP の20ラウンド・続きの LQ（別の出どころ＝取引量・スプレッドの広がり・ほかの7ペア）の10ラウンドとも関門Aで落ち、台帳は止めた**（台帳の見出し・止める回数・文言は `new_ledger` の引数で変えられる）。続けるなら新しい節で別の出どころを登録（PREREG「LQ」の「かぶらない表」が書き方の型）。道具＝手元 `research/loop/`（`loop_lab.py`・`lq_lab.py`）。🆕 **同日の続き**＝ST（5分足の状態→次の動き・12軸1〜3軸・8ペアの全数検定・ラウンド1の合格296は NY17時の切り替わりをまたぐ売りの費用の誤り→ラウンド2で合格0）・LI（指値で入ると成行より良いか＝差なし）。🚨 **5分足の売りの出る側の費用は、出る時のスプレッドを使うか切り替わりをまたぐ窓を除く**（M5系の「入る足のスプレッド1回」は切り替わりで売りを水増しする） |
| **`_doctrine_check.py`＋`mw evolve`** 🆕 | 投資研究の進化ループの番人（ローカル専用・**固定オラクル扱い＝安易に緩めない**）。`research/DOCTRINE.md`（検証済み知識台帳）の数値を出典と機械突合＋事前登録簿ハッシュ＋仮説キュー状態表示。読み方はDOCTRINE冒頭のプロトコル参照（毎回全文Readしない） |

- **記事公開は `python mw.py publish --file ... --category ... --emoji ... --card-title ... --desc ...`** で ②〜⑤→整合性チェック→sync→workflow起動まで一気通貫（`--dry-run` で確認）。
- **sync 前に `python mw.py check`** を習慣に（特に SYNC禁忌の混入を自動で止められる）。
- 🆕 **手元のセッションは起動時に `[auto_pull]` の行が文脈に入る**（auto_pull.py の結果）。**⚠️「まだ GitHub に送っていないファイル」が出ていたら、ほかの作業の前に片付ける**：「手元だけ変更」→ `mw check` → `mw sync`／「両方で変更」→ `_auto_pull_conflicts/<ファイル>`（GitHub 側の版）と手元の版を統合してから sync（`--force` で押し切らない）。取得に失敗した回は、送る前に `python auto_pull.py` をやり直す

---

## ⚡ トークン効率ルール（2026-07-02 新設・Claude セッションの作業規律）

**目的＝毎セッションの固定オーバーヘッドと無駄な読み書きを最小化**（監視は `mw declutter` が自動）。

1. **文書サイズ予算（超過は declutter_audit が警告）**: CLAUDE.md ≤32KB / SESSION_HANDOFF.md ≤30KB / MEMORY.md ≤4KB。完了した ✅セクションは SESSION_ARCHIVE.md へ退避。memory 索引は1行/件、詳細は各ファイル側へ
2. **ファイルはまず Grep・部分 Read（offset/limit）**。全文 Read は編集対象ファイルのみ。読んだファイルの再 Read 禁止
3. **コマンド出力は絞る**: `| tail` / `| grep` で要点のみ。大きい JSON/CSV は Python で集計値だけ print（生ダンプ禁止）
4. **サブエージェント委任は3条件のみ**: ①5ファイル超の横断調査 ②独立監査（コンプラ/品質＝Opus 必須） ③本文が長大な執筆。単発の調査・数行の確認は自分で Grep。機械的作業のモデルは sonnet で足りる
5. **検証結果は再実行せず引用**: 済んだ検証の数値は SESSION_HANDOFF / auto-memory から引く（同じスイープ・同じ集計を回し直さない）
6. **独立ツール呼び出しは1メッセージに並列**でまとめる

---

## 🕐 GitHub Actions の cron は当てにならない（2026-09-17 実測）

**このリポジトリの実績**（予定時刻からの遅れ）:

| ワークフロー | 予定 | 中央値 | 90%tile | 最大 |
|---|---|---|---|---|
| automation-health | 00:30 UTC | **+221分** | +294分 | +666分 |
| health-check | 00:00/11:00 UTC | +160分 | +325分 | +617分 |
| technical-alerts-1d | 21:20 UTC | +59分 | +125分 | +485分 |
| news-ticker（毎時） | :37 | +34分 | +55分 | +60分 |
| jp-rankings（9/8〜25） | 07:40 UTC | **約+5h10m** | — | +6h51m |

🔑 **区切りの良い時刻（:00 / :30）ほど遅い。半端な分にすると短くなる**（このリポジトリが 07:13 / 09:23 / 11:37 のような時刻を使っているのはそのため）。
🔑 **時刻の精度が要るものは cron に頼らない**。使える手は2つ:
1. **予約エージェント(routine)の push に相乗りする**＝routine は定刻に近い（`fundamental-context.json` の朝コミットは実測16件中14件が 06:13〜06:20 JST）。🚨 **ただし相乗りできるのは routine の push だけ**＝Actions が `GITHUB_TOKEN` で押したコミットはワークフローを起動しない。実例: update-market-news の `jp-rankings.json` パス指定は**一度も発火していなかった**（push起動100件中0件）。→ **2026-09-17 に `workflow_run` へ繋ぎ替え済み**（相手の `name:` と一字一句合わせる／`conclusion == 'success'` に限定）。⚠️ **書いたつもりの繋ぎが黙って死ぬ**のが今回の教訓なので、`check_automation_health.py` §⑭ が「workflow_run 起動が直近3日にあるか」を見張る。
2. **cron を複数本に増やして最初に当たったものを使う**（update-market-news が7:27/7:57/8:27/8:57 と4本置いているのはこの考え方）。重複送信の防止が要る場合は`actions/cache` を日付キーで使う（リポジトリに書かないので他を起こさない）。

---

## 🆘 ネットワーク不調時の運用ルール

ローカル → GitHub API が timeout する場合: **無限リトライせず、ブラウザで手動 trigger** を依頼。
- Run workflow URL: `https://github.com/invest-ai-info/marketwatch-ai/actions/workflows/<workflow-yml>`
- リトライは **最大 3〜5 回まで**

---

## 📚 関連ドキュメント・必読順序

セッション開始時に必ず読む順:

1. **CLAUDE.md**（このファイル、全体像）
2. **SESSION_HANDOFF.md**（直近進捗・次回タスク候補）
3. **memory/01_profile.md**（投資家プロファイル、固定情報、年単位更新）
4. **memory/02_evolution.md**（投資スタイル進化記録、月初更新）
5. **memory/03_initiatives.md**（進行中の検証・打ち手、週次更新）
6. **memory/04_technical_rules.md** ⭐ NEW（テクニカルアラート詳細ルール、月次見直し）

その他:
- `GEMINI_BILLING_SETUP.md` — Gemini API 課金有効化手順
- `MY_TRADES_SETUP.md` — Google フォーム連携手順
- `QUALITY_RUBRIC.md` — 記事「中身」品質ルーブリック（自動公開ゲートの品質レーン・単一ソース）。公開ゲートの順序＝決定論コード緑→Opusコンプラ白→品質ルーブリック→公開。news/signal-lab の各SOPから参照。基準変更はこの1ファイルだけ直す

**月初（1-3 日）のセッション開始時は必ず**:
- マンスリーレポートを読み、`02_evolution.md` の方針更新を提案
- 完了した検証項目を `03_initiatives.md` から「検証完了」へ移動
