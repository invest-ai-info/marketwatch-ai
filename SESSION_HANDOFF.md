# 🔖 セッション引き継ぎ（最終更新: 2026-07-10）

## 🧹 7/10 declutter＋Q12再監査（今日のメイン）

**①declutter＝3文書すべて予算内に復帰**: HANDOFF 38→28.5KB（7/8全節＋7/7スクリーナー節をARCHIVE退避）／DOCTRINE 25.6→**24.0KB=warning0**（§3棄却表を統合圧縮＝anchor45件維持）／CLAUDE 34.5→32.0KB（SYNC禁忌節の重複圧縮・全ファイル名保持）。CLAUDE/HANDOFF/ARCHIVEはsync済。DOCTRINE/queueはローカル専用＝sync対象外。

**②Q12 グレアム/バフェット p値再監査＝✅完了（DOCTRINE §2/§3/§6注記済・`_jp_q12_audit.py`／`_jp_q12_summary.json`）**: 7/8監査 発見4（月次formation×fwd12M=12倍重なり→SE過小の疑い）を、各主張で **旧p(iid cluster)／新p(block boot L=13)／同日クロスセクション対照** で再計算（監査＝新合否なし）。
- **🔴核心=§0-1を強く確証**: グレアム防御（暴落率差 高≥4 vs 低≤1）は train-22.4pp/holdout-19.5pp・**block bootでも同日対照でも両期間p0.0003**＝TT3リターン主張が同日対照で消えたのと対照的に守りは真の横断エッジ。効果量24%→4-5%(≈-20pp)完全維持。グレアム・リターン差も同日対照で両期間有意(+24.3/+11.8%)。
- **バフェット**: 「質は逆」方向は堅持(H1 -5.73/-6.05)だが**同日対照でtrain減衰(p0.094)/holdout堅持**。質は暴落防御にならず(H3 train+6.4pp)。割安内も質高いほど劣後(H2両期間有意)＝「安さが報われる」を強化。

## ⚡ 7/9夜 最新ニュース・ライブフィード新設（オーナー要望「夕方でも昨日のニュース」への対策・毎時更新・AI不使用・コスト0）

- **診断**: TOP3は48h窓×半減期36hの「インパクト優先」設計＝仕様どおり昨日の大ニュースが残留＋日本語フレッシュ記事のプールが薄い＋更新1日3回。
- **新設（既存TOP3/カード関連ニュースはそのまま）**:
  ①`build_news_ticker.py`＝日本語RSS/Google News 9本（ロイター/Bloomberg/日経/時事/株探/みんかぶ/NHK/Yahoo!/東洋経済）→時刻降順・類似dedup・ソース上限6・最新24件→`news-ticker.json`。センチメント絵文字はキーワード判定（generate側と同語彙の複製）。取得<5件なら既存JSON保持（フェイルセーフ）。日本語3文字未満の見出しは除外（銘柄ページのゴミ対策）。
  ②`news-ticker.yml`＝毎時:37・news-ticker.jsonのみcommit・concurrency有・update-market-newsのon:pushには**非**該当（連鎖起動なし）。
  ③index.htmlに「⚡最新マーケットニュース」枠＝`build_news_ticker_section()`（generate_market_news.py・非f-string関数）。**JSが閲覧時にJSONをfetch**（cache-buster付き・DOM APIでXSS安全・◯分前表示・8件+さらに表示・免責一文）＝HTML再生成なしで常に最新。
  ④ガード: news-ticker.json=SYNC_FORBIDDEN登録・automation-healthのWORKFLOW_CHECKSに5h/warnで登録・CLAUDE.md反映。
  ⑤**同日夜・オーナー要望で市場タグ追加（AI解説なし・AI呼び出しゼロは維持）**: `classify()`=キーワード照合で c=stocks/fx/commodity/crypto/macro/biz を付与→ティッカー枠に**バッジ+絞り込みボタン**（すべて/📈株式/💱為替/🛢商品/🪙暗号/🏛マクロ/📰経済）＋**4マーケットカードの関連ニュース下に該当市場の最新見出し3件**（`.mw-ticker-mini` data-mwcat・同じJSON・見出しのみ）。旧JSON（cなし）はbiz扱いで後方互換。
- **⚠️運用の学び=reconcile手順**: sync時に`generate_market_news.py`と`check_site_consistency.py`がstaleガード🚫→原因はクラウド公開（news-daily-auto 17:40等）がGitHub側で両ファイルを更新していたため。**リモートdiff確認→リモート版に自分の編集を乗せ直し→意図的`--force`**で解決（未変更ファイルはキャッシュskipなのでforceの影響は変更分のみ）。
- **🚩要オーナー認知**: 今朝の autopublish routine が `check_site_consistency.py` のクラウドスタブ分岐を**独自実装で書き換えてcommit**していた（7/8ローカル実装の`_IS_LOCAL`→routine版`_is_cloud_stub`）。動作は等価でクラウド実証済みのためリモート版を正として採用したが、**「ゲート/リンターをroutineが編集して通過」は自己承認と同型のリスク**＝AUTOPUBLISH_GUIDEに「リンター編集禁止・エスカレ」明文化の検討を⓪-Gに積んだ。

## 🩺 7/9夜 automation-health「3日連続失敗」の正体＝カード巻き戻し1件+可視化バグ2件（オーナーのメール通知から）

- **オーナー質問「ワークフロー失敗メールは問題か」→答え=本物の異常が3日間見えていなかった**。exit1=検知の仕様だが、通知先が腐っていた。
- **実異常（修復済み）**: `guide-news-2026-07-06-hormuz-oil-glut.html` のguides.htmlカード欠落。カード復元→push→**ライブ確認済・§③=58/58掲載✅**。⑱記事ファイルもローカルへreconcile取り込み。**※当初「巻き戻し疑い」と記録したが誤り＝真因は⓪-I参照（7/6エスカレ後の再公開手順が3日間未実施・並行セッションがgit履歴で確定）**。
- **可視化バグ①（修正済み）**: `mw issues` のGitHub API labels=カンマ区切りは**AND条件**→`bug,automation-health`のIssue #2が3週間不可視だった。ラベルごとOR取得に修正（mw.py・commit 56346eb）→**埋もれIssue #1(6/2)/#2(6/15)を発見**。
- **可視化バグ②（棚卸し済み）**: 見張り番は「Open or update」方式でIssue #2に17回コメント追記し続けていた＝open Issueが放置されると新規通知が立たない。**#1/#2とも解決コメント付きでクローズ**→次回異常は新Issueが立つ=通知復活。
- **明日7/10 13:30頃の定時運転=全緑のはず**（§③修復済・§④の80abc63検知は26h窓から自然消滅）。失敗メールが来たら新Issueを見る。
- 並行セッション（⓪-Gチップ）が実装した**検査④=ゲート編集検知は初回のローカル実行から機能**（今朝の違反commitを正しく検知）。

## 🗡 7/9 Q13深押しナイフ防御ゲート＝H1採用・🔪列実装＋寄り付きロガー自己修復化（今日のメイン）

**①朝の確認3点＝全✅**：
- **⓪-A autopublish修正後初の定時運転＝✅公開成功**：⑱economic-indicators-basics 08:40公開（全ゲート通過・REVIEW.md記録あり=沈黙禁止化が機能・ライブ200確認済）。#034研究日誌・⑲下書き（日経vsTOPIX）も正常。**7/8の二重欠陥修正は本番で実証＝クローズ**。
- **⓪-B 朝の自動化3日目**＝レイク/スクリーナーCSV/jp_dailyカード全✅。
- **🚨寄り付きロガー7/8欠測を検知→復旧＋根治**：7/8はPC電源断→17:22遅延起動→PT30M kill（jp_dailyと同じ「フェッチループに壁時計上限なし」）。7/9分はwake時のStartWhenAvailableキャッチアップが12:49完走＝設計どおり。**修正**=`jp_open_logger.py`に①FETCH_BUDGET_SEC=720（超過=偏った部分プールを書かず中断）②`--date`バックフィル③DAILY_SUMMARYタグの日次スナップショット(`_jp_openlog_tags.json`)④直前営業日欠測の自動バックフィル（自己修復）＋タスクPT30M→**PT45M**。7/8分は復元済み（40行・ds_tag='?'＝タグのみ復元不可・値上り/値下りプールは正確）。番人4項目✅復帰。
**②⓪-E アレンジ枠＝オーナー選択B「深押しナイフ防御ゲート」→Q13事前登録→検証→採用まで完走**：
- **Q13登録**（数式ロックを凍結行に直書き・SHA256登録済）: H1=G4新規突入(dev=C/MA200−1が−20%下抜け)→blowup60が同日対照より高い／H2=三空叩き込み完成→低い（例外条項）。主要=blowup60率の同日対照差・円環ブロックboot L=70・BH-FDR分母2。**⚠️出目既見を登録文に明示**（Q3/Q4の参考blowupの正式検定＝完全ブラインドでない→防御用途限定）。
- **結果（`_jp_knife_gate_screen.py`）**: **H1✅両期間合格**=同日blowup60差 train+13.07pp(q0.001)/holdout+17.02pp(q0.000)・fwd60同日diffも負(-2.01%/-4.41%)＝「G4乖離逆張り」の完全な裏返し（拾うな避けよ）。**H2❌方向逆転**=プール-5.7ppだが同日+7.85pp/+15.86pp＝三空の「守り」はパニック底日のタイミング運（新標準がまた地合い混入を暴いた・TT3の逆パターン）。
- **結晶化+適用**: DOCTRINE §2🔪新設・anchors45件（+4）・queue履歴更新・slugs2本追記。**`mw screen`に🔪ナイフ列を実装**（G4突入から60営業日以内=検証した危険窓そのまま・212/1683銘柄・注記に「買い回避の防御フラグ」明記）。
- 残: アレンジ候補A（資産クラス版デュアルモメンタム・記事#6有力）/C（=Q11）/D（複合）は未着手のままキュー外。

<!-- 7/8 全3節（Fable5方法論監査=TT3格下げ・autopublish二重欠陥根治+⑰公開・Q3酒田五法❌）は 2026-07-10 に SESSION_ARCHIVE.md へ退避。要点=auto-memory [[project_evolution_loop]]/[[project_masters_queue]]/[[project_jp_screener]]。TT3格下げの帰結（§1b・§0-4）はDOCTRINE反映済。残課題Q12は下記⓪-Dに継続。 -->

## 🧬 7/7 進化ループ構築（詳細=SESSION_ARCHIVE 7/8退避・運用=auto-memory project_evolution_loop）

- 6段ループ・DOCTRINE/番人/mw evolve/idea-scout-weekly。セッション冒頭は `mw evolve`。mw.pyはSYNC対象。未実装バックログ(a)〜(f)はARCHIVE参照。

## 🐢 7/7 TT3前向き（詳細=SESSION_ARCHIVE 7/8退避・queue Q7）

- `_jp_turtle_tracker.py` N=0/300・チェックポイント検定・**7/8にブロックboot改定**・月1回チェック。

## 🌙 7/7夜 Q1ダーバス/Q2ワインスタイン=❌棄却（詳細=SESSION_ARCHIVE 7/8退避・DOCTRINE §3）

- 両方崩れ「順張りはTT3のみ」と当時整理→**7/8監査でTT3自体も非頑健と判明**（上の7/8夜セクション参照）。

<!-- 7/7深夜 日本株スクリーナー新設（`mw screen`=`_jp_screener.py`ローカル専用・列プラグイン登録制・防御列で宿題Q9適用）＋レイク/スクリーナーCSV自動補充タスク新設＋jp_dailyフェッチバジェット根治は 2026-07-10 に SESSION_ARCHIVE.md へ退避。要点=auto-memory [[project_jp_screener]]。運用CLIは `mw screen --help`。 -->

新セッションは **このファイル＋ CLAUDE.md ＋ auto-memory（MEMORY.md 経由）** を読めば文脈を復元できる。
セッション冒頭は `python mw.py evolve`。2026-06-17 以前＋7/2〜7/3＋7/6の詳細履歴は **SESSION_ARCHIVE.md** へ退避した。

---

> 2026-07-02の「研究の高速化3点」「ルール文書棚卸し」もSESSION_ARCHIVE.mdへ退避（要点はauto-memory側に反映済み）。

## 🇯🇵 日本株：EV最速化ロードマップ＝全6施策 完了（2026-06-26/27）

ネットR／分数ケリー／赤字回避統合／外国人フロー／発注規律カード（平日6:00自動+番人8:00）／続伸×risk_offトラッカー——**詳細は非公開 `JP_EV_ROADMAP.md`・SESSION_ARCHIVE.md（2026-07-04退避）・auto-memory [[project_jp_doublebagger]]**。残＝前向きN蓄積が律速（昇格アラートはカード上段に自動表示）。

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
| **発注前ルールの遵守を数値監視** 🆕 | `_trade_discipline_check.py`（`mw discipline`・週次 /loop） | 指標持ち越し/指数重ね張り/SL未設定/損切りずらし/JP✕を **EVダメージ順に可視化** |
| **相関ポジ合算リスク2%・実スリッページ** 🆕7/5 | 同上 R6/SLP（フォーム任意3欄=口座残高/リスク額/予定価格の入力分から自動判定） | 同テーマ×同方向の同時保有を横断検出し合算%で2%判定（金銀・FXも対象＝指数限定R3の一般化）。前向き検証の群割当は登録時5ルール固定＝R6は参考枠 |
| **公開日のUTC日付ミス防止** 🆕7/6 | `signal_lab_verify.py` の `date_check()`（再監査は `SIGNAL_LAB_SKIP_DATE_CHECK=1`） | datePublished/公開表記≠JST今日なら**赤=公開ブロック**（#031が7/5付けで公開された事故の再発防止） |
| **似スラッグの重複記事防止** 🆕7/6 | `check_guide_draft.py` 検査7 スラッグ重複検査（トークン集合の同一/包含） | ⑫⑬型の「語順違い/部分一致スラッグの同一主題」自動公開を**RED=人間エスカレ**（82記事総当たりで誤検知ゼロ） |
| **研究台帳の数値転記ミス・改竄・肥大化防止** 🆕7/7 | `_doctrine_check.py`（`mw evolve`・固定オラクル扱い） | DOCTRINEのアンカー21件を出典JSON/mdと突合＋事前登録簿SHA256＋サイズ予算＋§1構造検査で**error停止** |
| **非公開研究ファイルの公開リポ流出防止** 🆕7/7 | `check_site_consistency.py`＝SYNC_FORBIDDEN追加＋**`_`プレフィックス=ローカル専用規約** | DOCTRINE/queue/`_jp_*`等が SYNC_FILES に混入したら**error停止**（REDテスト7ケース済） |
| **公開記事への下書き残骸混入防止** 🆕7/7 | `signal_lab_verify.py` date_check の残骸検査 | 「下書き中」が本文に残っていたら**赤=公開ブロック**（#032実例の再発防止） |
| sitemap 全記事網羅 | `generate_market_news.py` の `build_sitemap_xml` | 全 guide を自動収集・手動編集不要 |

🆕＝2026-06-20 追加（B＝カバレッジ番人 ／ C＝sync staleness ガード）。新ルールはこの表に1行＋チェック1個で増やす。

---

## ⚠️ 絶対遵守（事故防止）

- **SYNC禁忌**（ローカルから絶対 push しない＝routine/cron/generate が GitHub 側で生成）。**正は CLAUDE.md の SYNC禁忌リスト**。代表例：
  6コアHTML（index/calendar/charts/vix/market-health/hot-assets）／`signals-log.json`／`technical-alerts-history*.json`／`track-record.html`／political系／youtube系／`fundamental-context.json`／`weekly-levels.json`／`weekly-zone-plan.md`／`sitemap.xml`／`weekly-strategy-context.json`／`indicator-result.json`／`signal-lab-tracker.json`／`signals-log-backtest.json`／`article-ideas.md`／`daily-preview.md`／`political-digest.md`／`compliance-scan.md`／`site-qa-report.md`／`panic-scan.md`／`drafts/draft-*`・`drafts/news/*`・`drafts/sns/*`
  → `mw check`（`check_site_consistency.py`）が SYNC_FILES への誤混入を、sync の staleガードが「古いローカルでの上書き」を、それぞれ自動で止める。
- **SYNC対象（OK）**：`*.py`（※`sync_to_github.py` はローカル専用＝GitHub側は616Bスタブ。**`mw.py` はSYNC対象**＝7/7訂正。`_`プレフィックスのファイルは全てローカル専用＝SYNC禁止をコードで強制済）／`.github/workflows/*.yml`／個別 `guide-*.html`／`guides.html`／`robots.txt`／`my-trades.json`／`memory/*.md`／各 docs。
- 記事追加は **`python mw.py publish ...` → sync → workflow → ライブ確認**。公開前に compliance-reviewer(Opus)監査・教育トーン・特定銘柄の買い推奨は書かない・kinsho-v1 免責・10ボタンナビ。手動時も `mw check` で push 前点検。
- ネット不調時は無限リトライせず、ブラウザで手動 trigger を依頼（最大3〜5回）。

---

## 📌 アクティブな宿題

### 🔜 次セッションで最初に確認（在flight・2026-07-11向け）
- **⓪セッション冒頭の新ルーチン＝`python mw.py evolve`**（DOCTRINE突合+キュー+トラッカー鮮度・トークン0）。
- **⓪-A 朝の自動化継続確認**＝`python -X utf8 _jp_health_check.py`（5項目✅）＋`JP*_要確認.txt`無し。**7/10朝=寄り付きロガー自己修復版の初定時運転✅**（タグsnap 07-10記録・番人5項目緑を確認済）。
- **⓪-B autopublish**＝7/10対象=⑲nikkei-vs-topix。**⚠️7/10の公開/スキップ記録は本セッション未確認→7/11朝にREVIEW.mdで7/10記録＋7/11対象を確認**。
- **⓪-C idea-scout-weekly**：初回手動E2Eは7/7済。**初の定時運転=7/12(日)14:00 JST**→翌セッションで転記（転記slugは idea-tested-slugs.txt へ）。
- **⓪-D 進化ループ続き**：Q13(7/9・H1採用)・**Q12(7/10・✅監査完了＝グレアム防御は同日対照でも頑健／上の7/10節)** 消化済み。次候補=**Q8金ラボ第2R**／**Q11ズールー前向きトラッカー設計**（fins月次更新の整備が先）／Q10及川H-O4（低優先）。TT3前向きは月1回`_jp_turtle_tracker.py`。
- **⓪-E 巨匠アレンジ枠の残り候補（B=Q13は7/9完了）**：
  **A**=資産クラス版デュアルモメンタム（日経/S&P500/金/米債の月次乗り換え・原典回帰・Yahooで20年・記事#6有力候補）／
  **C**=ズールー前向き実装（=Q11+screener参考列）／**D**=グレアム防御×PEG成長の複合1本（複合は前科あり=期待控えめ明記）。
  ※「すでに生きているアレンジ」の整理も記事ネタ（赤三兵→連騰≥4危険ゲート・タートル資金管理→ATRベースSL/2%ルール・**G4逆張り→🔪回避フラグ（Q13）**＝原型のエントリーは死んでも部品は生きる）。
- **⓪-F ✅済（7/10）文書declutter**：CLAUDE 32.0/DOCTRINE 24.0(warning0)/HANDOFF 28.5＝全て予算内。以後もこの水準を維持（節が増えたら完了節をARCHIVEへ）。
- **⓪-G ✅済（7/9夜）routineによるリンター編集の再発防止＝三層で実装**: オーナー決定=**完全禁止**（等価修正も不可・赤はエスカレのみ・ゲート修正は人間専任）。①`AUTOPUBLISH_GUIDE.md`=固定ゲート4本（check_guide_draft/check_site_consistency/signal_lab_verify/publish_article）の編集・commit禁止+7/9違反実例を明文化 ②routineプロンプト更新済（手順4/7/絶対厳守を強化。⚠️**プロンプト禁止は7/8夜から存在したのに破られた実績あり**＝コード検知が本命） ③`check_automation_health.py`にチェック④新設=直近26hでゲート4本をオーナー/github-actions[bot]以外のauthorが変更→warn Issue（ローカル実測で7/9違反commit `80abc63` を正しく検知✅）。**⚠️7/10 09:30の運転で既知の7/9違反commit（対応済）が1回Issue化した可能性＝あれば無視してクローズ**。以後の検知は本物。
- **⓪-H ⚡news-ticker 初日の定時運転確認**: 毎時:37。翌朝、Actions履歴で夜間の毎時実行が回っているか＋live JSONのupdatedが新しいか（automation-healthにも登録済=5h/warn）。**市場タグ版は7/9夜にライブ確認済**（バッジ/絞り込み/カード内ミニ3件・分類テスト8/8）。⚠️オーナー体感の宿題1件=夜間はYahoo!経済由来の📰経済（消費者ネタ）が多め→**「📰経済を既定で非表示（ボタンで表示）」は1行で変更可＝オーナーの好み待ち**。
- **⓪-J 文書サイズ**: SESSION_HANDOFF 37.6KB（予算30）＝⓪-Fのdeclutterで7/7〜7/8の完了節をSESSION_ARCHIVEへ退避。
- **⓪-I ✅済（7/9 20:30）guides.htmlカード消失＝実は「消失」でなく「未完了公開」**: git履歴調査の結果、カードは一度も存在しなかった（巻き戻しでも取り下げでもない）。**真因**=7/6のnews-daily-autoが当時のSYNC_FILES縮小問題で `check_site_consistency` exit=1→設計どおりエスカレ（commit 1200e77b=記事HTML+NEWS_LEDGERのみpush・カード/履歴/SYNC登録なし）→台帳の「再公開手順（人間が実施）」が3日間未実施のまま放置されていた。**対応**=台帳手順どおり完了（コンプラは当時Opus×2で🟢白済・noindexなし）：カード挿入（7/7と7/5の間の正位置）+SYNC_FILES+更新履歴→`mw check`緑→sync（guides.htmlはstaleガード🚫→diff確認=カード9行のみ→定石--force・commit 156f63e=+9/-0）。**番人③再実行=58/58✅**・ライブ記事200・sitemap収載済み。ついでに⑱`guide-economic-indicators-basics.html`のローカルreconcile+SYNC_FILES登録も実施（mw checkが検出）。**教訓=番人③の検知は「エスカレ回の未完了公開」でも発火する。まずNEWS_LEDGER.mdの該当日エントリを見ると1分で原因が分かる**（GitHub側LEDGERの7/6エントリは「公開準備」のまま=SYNC禁忌のためローカルから更新不可・実態は公開完了）。
- **①巨匠シリーズ**：記事#5公開済み（7/8夜・Q1〜Q5+TT3訂正を1本化）。次記事候補=「#6 割安成長（ズールー）×グレアム再訪」＝Q11前向き設計・Q12再監査の後が筋。
- **②TT3の前向き検証＝📊稼働中**（`_jp_turtle_tracker.py`・検定はブロックboot版に7/8改定・月1回チェック・初判定は10月頃）。
- **③防御スクリーン列＝✅適用済み**（`mw screen`の🛡防御列・7/7）。
- **⑤番人EA MW_Guardian＝実弾テスト未実施**：オーナーがデモ口座で試し発注→スマホPush・仮SL自動装着・重ね張り警告の実挙動を一緒に確認（EAはPC MT4起動中のみ稼働）。
- **⑥リードマグネット公開待ち＝オーナーのGoogleフォーム作成待ち**：URLが来たら `MAGNET_SETUP.md` の Claude作業（コンプラ監査→PDF SYNC→CTA設置→X導線）を一気通貫で。
- **⑦AdSense＝7/6再却下（確定）**：🔴**オーナー作業＝AdSenseコンソール[サイト]ページで却下理由の詳細を確認**→理由を見てから対応方針を相談（候補: ニュース/自動生成記事の追加noindex・コンテンツ拡充・再申請時期）。むやみにnoindexを増やすのは理由確認後。
- **⑧オーナー手動タスク2件**：(a) **X用アイコン `mw-logo-512.png`**（作業フォルダ直下・ローカルのみ）を @rx009898 のプロフィール画像に手動アップロード (b) 実機スマホでトップページ整理後の見え方＋タブのロゴを確認。
- **⑨相談したら進む事項**：(a) OGP画像のロゴ入り差し替え (b) ツール次候補＝DCA比較/NISA枠/ポジションサイズ（後2者はコンプラ設計繊細） (c) `btc_all_1d`のN30緩和＝コスト込みで脆弱の扱い (d) 🏁5本問題のauto_*注記移設 (e) リバモア検証（優先度低）。
- ✅済（7/8・詳細は上の7/8節）：⓪-A自動化3件初運転全✅／⑰公開＋autopublish二重欠陥根治／Q3酒田五法4パターン棄却／④昇格メール初発火観測（7/7・index_long_live 8マッチ4通送信=クローズ）。
- ✅済（7/6・詳細はSESSION_ARCHIVE）：#031日付事故修正+日付ゲート／重複2ペア統合+スラッグ重複ゲート／巨匠#5〜#7+QA+複合=17仮説検証／記事#4公開／automation-health・health-check正常化確認／朝チェーン全部正常。
- **整理係**：`mw declutter` は7/3時点0件。月次 `MarketWatch_Declutter` が `DECLUTTER_REPORT.md` を出したら確認。

- ✅ 済（詳細は上の7/3まとめ・アーカイブ参照）：格言シリーズ無人化実証（7/1）／ニュース鮮度カットオフ（6/30）／ロイターRSS復活確認（7/3＝フィード健在・TOP3選外は正常）／JP朝カード初稼働＋番人（7/3）／FOMC結果の信頼性厳格化（7/3）／update-market-news concurrency（6/20）。
- ✅ **POLICY dict 更新＝完了（2026-07-04未明）**：日銀 0.75→**1.00%**（6/16利上げ）。米3.75/欧2.40/英3.75/豪4.35は6月会合すべて据え置き＝変更なし（FRB6/17・BOE6/17・RBA6/16をWebSearch＋fundamental-contextで裏取り）。次回会合=FOMC 7/28-29・日銀 7/30-31。朝7時の update-market-news から反映。
- 📉 **AdSense ＝2026-06-27 再申請済・結果待ち**（[[project_adsense_review]]）。次セッションで結果確認（上の在flight参照）。
- 🗓️ **`jp-stock-info.json` の四半期更新**（決算シーズン後に `python make_jp_stock_info.py` 再実行→`mw sync`。赤字/黒字フラグを最新決算へ。日次の値上がり率/売買代金は `jp-rankings.yml` が自動）。
- ✅ autodraft topicキュー ⑫〜⑯補充済（2026-07-04・金利債券/単複利/ETF投信/注文方法/PER・PBR＝毎朝05:30のroutineが順に消化）。
- 📊 弁護士相談アジェンダ（track-record 統計開示／確信度ラベル／個別銘柄記事の言及）。
- 🟡 保留＝**J-Quants Standard（¥3,300・1回）** で「risk_off 転換→守り」を 2018/2020 実暴落でバックテスト（オーナー課金判断時）。
- 研究日誌の自動公開はエスカレ回のみ人間レビュー（`drafts/REVIEW.md` の🚩）。

---

## 📎 運用メモ

- 作業フォルダ: `C:\Users\info0\OneDrive\デスクトップ\新しいフォルダー` ／ GitHub: `invest-ai-info/marketwatch-ai`(main)
- 運用は **`python mw.py <cmd>`** が単一入口（check / publish / sync / **deploy [--trigger]** / trigger <wf> / status [wf] / **issues** / **audit** / routines）。`mw routines` で全 routine ID 一覧。
- 🆕 **ループ・エンジニアリング土台（2026-06-23・決定論コマンド＝トークン0）**：②`mw issues`＝open health-check/automation-health Issue 一覧（トリアージの土台）。③`mw audit`＝guide記事の改善候補スコア化（desc短/本文短/内部リンク少/JSON-LD無）。**判断部分だけ上限付き `/loop` でモデルに渡す**設計。`/loop` レシピ＝②「mw issues→最大3件診断＋提案(自動適用しない)→STOP」／③「mw audit→最弱を1本改善→白確認→publish、最大3本/回、score≥2が尽きるかで停止」。**🔑調査結果（2026-06-23）＝audit最弱11件は全部すでに `noindex,follow` 済み**（週次振り返り/週次戦略/月次の自動生成は薄ページAdSense対策で既にインデックス除外＝`auto_weekly_review.py`:287 / `auto_weekly_strategy.py`:378 / `generate_monthly_report.py`:291）＝**AdSense薄コンテンツ対策は完了済み**。よって `mw audit` を **noindex対応**に改修（noindex薄ページは別枠カウント＝改善対象外）→**インデックス対象81件中 改善候補0件＝公開コンテンツは健全**と確認。底上げ不要。
- 🆕 **`mw deploy`（2026-06-23）＝自己修復デプロイ（決定論・モデル不使用＝トークン0）**：sync を ❌throttle 時に backoff して**最大5回**再試行・🚫staleは即エスカレ・成功/上限/合計15分で必ず停止→任意で workflow 起動(`--trigger`)→ライブ200検証。上限は `mw.py` の `DEPLOY_*` 定数で固定＝構造的に永久ループ不能（今日の api.github.com throttle 手動リトライを自動化）。
- 同期は `python sync_to_github.py`（＝`mw sync`）。staleガードに 🚫 されたら「先に最新を取り込む（reconcile）」か、意図的なら `--force`。workflow 手動起動は `mw trigger <wf.yml>`。**ローカルは UTF-8 強制**：`$env:PYTHONUTF8="1"`（PowerShell）。
- routine 操作: schedule スキル → `ToolSearch select:RemoteTrigger` → RemoteTrigger（list/get/update/run）。クラウド routine（`signal-lab-daily`／`news-daily-auto` 等）はこれで管理。
- ⚠️ ローカルは GitHub と未同期なことがある（OneDrive）。**真の状態は GitHub／ライブを見る**。token は `market-news-config.json`(.json)。
- ユーザー北極星：投資家全体の底上げ／サイト・SNS 年収1000万／個人投資成績 年収1億。
