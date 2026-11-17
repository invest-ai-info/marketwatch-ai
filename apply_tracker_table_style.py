# -*- coding: utf-8 -*-
"""
apply_tracker_table_style.py — 公開済みの研究日誌の「前向きトラッカー定点観測」表に、見た目の枠を付ける。

2026-11-17 オーナー「このリストの文字がごちゃごちゃしていて見づらいのを直してほしい」。
原因＝2026-10-17 に表を道具で差し込む形（`signal_lab_tracker.py table --html --into`）にしたとき、
それまで書き手が手で付けていた枠 `<div class="tracker-wrap">` が出力に無く、#128 以降の表は
余白・区切り線・見出しの色の無い素の `<table>` で公開されていた（列の文字どうしがくっついて見えた）。
新しい記事は `signal_lab_tracker.table_html` が最初から枠つきで出す。これは**過去の記事**用。

やること（表1つにつき）:
  ・表を `signal_lab_tracker.wrap_table`（新しい表と同じ枠と CSS＝単一ソース）で包む
  ・「状態」セルに色分けの class（✅昇格＝緑・🟡蓄積中＝黄・⛔反証＝赤・⏹見込みなし＝灰）
🔑 変えるのは見た目だけ。表の文字（数字・言葉・並び）は1文字も変えない＝表ごとにタグを除いた文字を比べて確かめる。
⚠️ 素の <table> と見出し「前向き現在値(平均R)」は変えない（check_plain_japanese.py がこの2つで表を見分けている）。
⚠️ drafts/ 配下は対象外（routine の作業場）。冪等＝枠（class="mw-tracker"）がある記事は飛ばす。

使い方:
    python apply_tracker_table_style.py           # 確認だけ（何本が変わるか）
    python apply_tracker_table_style.py --apply   # 書き込む
テスト: python tests/test_tracker_table.py
"""
import argparse
import glob
import io
import os
import re

from signal_lab_tracker import state_td, wrap_table

ROOT = os.path.dirname(os.path.abspath(__file__))
TABLE_RE = re.compile(r"<table>(?:(?!</table>).)*?前向き現在値\(平均R\).*?</table>", re.S)
LAST_TD_RE = re.compile(r"<td>((?:(?!<td>|</tr>).)*?)</td>(\s*</tr>)", re.S)


def _text(h):
    return re.sub(r"\s+", "", re.sub(r"<[^>]+>", "", h))


def restyle(html):
    """戻り値＝(新しい HTML, 変えた表の数)。表の文字が変わる直しは例外で止める（黙って書かない）。"""
    if 'class="mw-tracker"' in html:
        return html, 0
    n = 0

    def one(m):
        nonlocal n
        table = m.group(0)
        new = LAST_TD_RE.sub(lambda r: f"{state_td(r.group(1))}{r.group(1)}</td>{r.group(2)}", table)
        if _text(new) != _text(table):
            raise ValueError("表の文字が変わる＝書き込まない")
        n += 1
        return wrap_table(new)

    out = TABLE_RE.sub(one, html, count=1)
    return out, n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    changed = []
    for path in sorted(glob.glob(os.path.join(ROOT, "guide-signal-lab-*.html"))):
        with io.open(path, encoding="utf-8") as fh:
            html = fh.read()
        new, n = restyle(html)
        if not n:
            continue
        changed.append(os.path.basename(path))
        if a.apply:
            with io.open(path, "w", encoding="utf-8", newline="") as fh:
                fh.write(new)
    verb = "書き込みました" if a.apply else "変わります（--apply で書き込む）"
    print(f"前向きトラッカー表に枠を付ける: {len(changed)}本 {verb}")
    for c in changed[:10]:
        print("  -", c)
    if len(changed) > 10:
        print(f"  …ほか {len(changed) - 10}本")


if __name__ == "__main__":
    main()
