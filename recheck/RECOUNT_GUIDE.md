# 数え直しの手順書（検算の関門の部品②）

設計書: `docs/superpowers/specs/2026-11-26-result-audit-design.md`（5.3）／道具: `recount_compare.py`／記録: `recheck/records.json`

**いつ数え直すか**：判定が合格側（残った・合格・前向きへ・昇格）のとき／点検で「良すぎる印（G1）」が付いたとき／いま使っている結果を洗い直すとき。

**数え直しが済むまで、その合格は使わない**（2026-11-27 オーナー決定）。リストには「🔍 数え直し待ち」と出る。

## 流れ

1. 元の道具の取引の一覧を共通の形（`result_audit.py` の `TRADE_FIELDS`／`EVENT_FIELDS`）で出す → `research/recheck/<研究>/orig.csv`（値段を含む＝手元だけ）
2. 数え直しの担当（**新しいサブエージェント・Sonnet**）を、下のひな形で呼ぶ
3. 担当が書いた `research/recheck/<研究>/recount.py` を走らせて `recount-rows.csv` を作る
4. 突き合わせ：`python recount_compare.py research/recheck/<研究>/orig.csv research/recheck/<研究>/recount-rows.csv --study <研究>`
5. 食い違いを1件ずつ見て、理由を `research/recheck/<研究>/explanations.json` に**追記**する（消さない）
   - `original_error`（元の道具の誤り）→ 元の道具を直して数え直す。登録に「計算の誤りの直し」として追記
   - `recount_error`（数え直し側の誤り）→ 数え直し側を直す
   - `ambiguous_rule`（登録の文があいまい）→ **成績が良く見えない側**の読みに決め、登録に追記して、両方をその読みで数え直す
   - `data_version`（データの版の違い）→ 同じ日の同じ銘柄で、**読み込んだ値段そのものが違う**と示せたときだけ。`evidence` に両方の入力の値を書く。外せるのは元の件数の **10% まで**（`recheck_status.DATA_VERSION_MAX`）。超えたら同じ入力のデータで数え直す
6. 説明した食い違いを全部直したら、もう一度4を回す。食い違いが `data_version` だけになったら `--write` を足して記録に残す：
   ```
   python recount_compare.py ORIG RECOUNT --study <研究> --explain research/recheck/<研究>/explanations.json \
       --opened research/recheck/<研究>/opened.txt --forbid <元の道具のファイル> --write
   ```
   J-Quants を使う研究は `--local-only`（記録も手元だけ）
   - **記録の名前**は、使う所が引く名前と同じにする：シグナル研究＝tracker の仮説の id（例 `rl_tf_adx_strong`）／検証済みリストの行＝`<節>-<id>`（例 `J26F-C`）／総当たりの候補＝候補の id／DOCTRINE＝`[recheck:名前]` に書いた名前
7. 記録の `recheck/records.json` を送る（値段は入っていない）。結果をオーナーへ報告する（「研究の記録で、投資の助言ではありません」を添える）

## 担当への指示文のひな形

```
あなたは研究の数字の「数え直し」の担当です。下の登録の文だけを読んで、取引の一覧を自分で数える道具を書いてください。

■ 目的
登録どおりに数えた取引の一覧を、共通の形の CSV で出すこと。成績の良し悪しは見なくてよい（合計や平均を出さなくてよい）。

■ 登録の文（この文が唯一の決まり。数字や部品を変えない）
<PILLAR_PREREG.md のその研究の節を、「**結果（」より前まで貼る>

■ データ
<置き場と形。使ってよい読み込み部品があれば名前と戻りの形（例：research/oikawa/oj_lab.py の load_a(folder)）>

■ 出すもの
1. research/recheck/<研究>/recount.py（自分で書いた道具）
2. research/recheck/<研究>/recount-rows.csv：1行＝1つの取引。欄は次のとおり
   study, market, symbol, side(1/-1), signal_time, entry_time, exit_time（UTC の ISO・時間帯を必ず付ける）,
   entry_price, exit_price, stop_price, unit(pips/pct/bp), gross, cost, net, r, exit_reason, period
   （目印のときは study, market, symbol, date, flag, outcome, unit, period）
3. research/recheck/<研究>/opened.txt：この作業で開いたファイルを全部、1行に1つ

■ 守ること
- 次のファイルは開かない：<元の道具のファイル名>・<結果の JSON・取引の CSV>
- 登録の文で決まっていない所があれば、勝手に決めずに、どこがあいまいかを報告に書く（読みを2つとも書く）
- 1つの取引は1行（建玉を分けて持つ決まりでも、1行にまとめる）
- 終わったら、あいまいだった所と、開いたファイルの一覧を報告する
```
