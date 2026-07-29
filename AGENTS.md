<!-- ===== READ THIS FIRST - ASCII only, survives any codepage ===== -->

## 0. ENCODING (read this before anything else)

Every file in this folder is **UTF-8**. This is a Japanese Windows machine, so the
shell default codepage is CP932. Reading UTF-8 with the default codepage produces
garbage, and you will silently miss every rule in this file.

    Get-Content -Raw -Encoding UTF8 <file>      # correct
    Get-Content -Raw <file>                     # WRONG - gives mojibake
    $env:PYTHONUTF8 = "1"                       # set before running any python script

If Japanese text ever looks like `繝帙せ繝医ヱ繧ｹ` or `縺ゅ↑縺`, you used the wrong
encoding. Stop, re-read the file with `-Encoding UTF8`, and start over. Do not
act on mojibake - you are reading a corrupted copy of the rules.

Verified 2026-07-29: a `codex exec` run read `CLAUDE.md` this way and received
2,400+ corrupted characters. ASCII identifiers survived, all Japanese did not.

<!-- ===== end ASCII section ===== -->

# AGENTS.md — このフォルダで作業する AI エージェントへ

MarketWatch AI（marketwatch-jp.com）の作業フォルダ。
**Claude Code と Codex が同じガードで動くための共有ファイル**（2026-07-29 新設）。

## 大原則

ルールの本文をここに複製しない。**単一ソースは `CLAUDE.md`**——複製は必ず古くなって嘘をつく。
守るべきは文書でなく**コード**：下の決定論ゲートを通すことが唯一の合格条件。

---

## 1. push 前に必ず通すゲート

```
python mw.py check
```

`check_site_consistency.py` が SYNC禁忌の混入・免責表記・ナビ10ボタン・リンク切れを検査し、
error があれば **exit 1** で止まる。**これを通さずに `sync_to_github.py` を実行しない。**

## 2. 触ってはいけないファイル

- **自動生成の6コアHTML**（`index` / `calendar` / `charts` / `vix` / `market-health` / `hot-assets`）
  = `generate_market_news.py` が生成元。**HTML を直接編集しない**（次の生成で消える）
- **`_` プレフィックスのファイル** = ローカル専用・SYNC禁止（コードで強制済み）
- **固定オラクル＝編集して基準を緩めない**：
  `signal_lab_verify.py` / `check_guide_draft.py` / `_doctrine_check.py`
  これらは「検証結果が捏造でないこと」を独立に保証するコード。
  **自分が通したい検査を自分で書き換えるのは禁止**。基準変更はオーナー承認が要る

## 3. SYNC_FILES の禁忌（事故の実例あり）

cron / クラウド routine が **GitHub 側で生成する**ファイルを `SYNC_FILES` に足さない。
ローカルから push すると古い版で上書きされ、**ライブサイトが過去日付に巻き戻る**
（実例: 2026-04-24）。対象一覧の単一ソースは `CLAUDE.md`「SYNC_FILES の禁忌」節。
混入は `mw check` が push 前に止める。

## 4. 記事公開は手作業でやらない

```
python mw.py publish --file guide-xxx.html --category <既存カテゴリ名> --emoji 🏰 \
    --card-title "カード用の短めタイトル" --desc "カード説明文"
```

冪等（再実行しても二重化しない）。`guides.html` のカード・`sitemap.xml`・更新履歴を
**手で編集しない**（sitemap は全 guide を自動収集して再生成される）。

## 5. Windows 実行時

- **ファイル読み書きは必ず UTF-8 指定**（§0 参照）。既定のまま読むと日本語が全滅する
- Python 実行には `PYTHONUTF8=1` を付ける（付けないと日本語で文字化け・失敗する）
- **日付は書き込み直前に取り直す**。セッションを跨ぐと平気で古い日付を書く

## 6. このフォルダは git リポジトリではない

GitHub への反映は `sync_to_github.py`（GitHub API 経由）。`git` コマンドを前提にしない。
`codex review` のような**リポジトリ前提のツールはここでは動かない**。

---

## 7. 図解（インラインSVG）の標準

サイトの図解は**すべて手描きのインラインSVG概念図**。PNG等の画像は使わない。
理由＝ダークモードに自動追従する／固定オラクルで機械検査できる／再生成できる／
実在価格を使わない概念図なのでコンプラ安全／サイズが SVG 5KB に対し PNG は 1〜2MB。

### 守ること

1. **色をSVGに直接書かない**（`fill=` / `stroke=` / `style=`）。
   ライト/ダーク両対応はCSS側にあるので、直書きするとダークモードで見えなくなる
2. **既存のCSSクラスだけを使う。新クラスを発明しない。**
   ⚠️ **クラス一覧をこのファイルに複製しない**——複製は必ず古くなって嘘をつく。
   **対象記事の `<style>` ブロックを読み、そこに定義されているクラスだけを使うこと。**
   - 解説記事レーンの手本＝`guide-algo-volatility.html`（`.s-lane` / `.s-node` / `.s-arrow` 系）
   - チャートレーンの手本＝`guide-signal-anatomy.html`（`.s-candle-up|dn` / `.s-bb` / `.s-ma25` / `.s-fire` 系）
3. `<figcaption class="chart-caption">` に **「※ 実在の価格ではなくイメージです。」** を必ず入れる
4. `viewBox="0 0 720 …"` を基準にし、`role="img"` と `aria-label` を付ける。フォント指定はしない
5. **ラベルを重ねない。不透明な図形の下に文字を置かない**
   （`.s-node` は不透明。文字より後に描くと文字を隠す）

### チャートは目分量で描かない

2026-07-29 に `guide-signal-anatomy.html` を実測したら、手描きの結果こうなっていた：

- ボリンジャーバンドが平行チャネル（幅の最大/最小が **1.04倍**）＝σに連動しておらず、
  スクイーズもエクスパンションも起きない＝「ボリンジャーバンドっぽくない」
- 中心線（20SMA）が無い
- ローソク足は x=390 で終わるのに、バンドは x=480 まで伸びていた（**83px**、足の無い場所にバンド）

→ ローソク足・BB・RSI は **`_gen_bb_panel.py` で計算**して座標を出す（差し込みは `_apply_bb_panels.py`）。
20期間のBBは手前に20本の助走が要る。描画する本数だけで計算しないこと。
**図が本文の主張（「−2σタッチで発火」等）を実際に満たしていることも、生成側の採用条件で保証する**
（本文と矛盾する図を出さない）。

### 出したら必ず測る

描いた本人は**自分の描画結果を見られない**。実測でも、Claude・Codex とも初回提出で毎回
ラベル欠陥を出した（テキスト衝突・不透明図形による遮蔽・パネル枠のはみ出し）。
目視で済ませず機械で測ること：

- `signal_lab_verify.svg_bounds_check` / `text_overlap_check`（固定オラクル）
- ブラウザで `getBBox()` を使い、テキスト衝突・遮蔽・枠外を検査
- **ライトとダークの両方**を必ず見る

## 迷ったら

`CLAUDE.md`（全体像・禁忌の正）→ `SESSION_HANDOFF.md`（直近の経緯）の順に読む。
整理・肥大の監査は `python mw.py declutter`。研究文書の予算は `python mw.py evolve`。
