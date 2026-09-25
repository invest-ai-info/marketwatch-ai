# -*- coding: utf-8 -*-
"""
apply_tracker_plain_names.py — 公開済みの研究日誌の「前向きトラッカー定点観測」表を、やさしい日本語に揃える。

2026-09-24 オーナー指示「この組み合わせを日本語にしてわかりやすく。慣れていない人が見ると何の機構か全くわからない」。
新しい記事は `signal_lab_tracker.py table --html` が最初から日本語で出す。これは**過去の記事**用。

やること（表1つにつき）:
  ・「仮説」セル  … 「group=metal×dir=long」→「金・銀の買い」＋小さな文字で元の管理名
  ・「種別」セル  … 「gate」→「負けやすいか」＋小さな文字で gate
  ・表の直前      … 「表の見方」の段落を1つ足す
名前と説明は signal_lab_tracker.plain_name / plain_legend をそのまま使う（単一ソース）。

🔑 変えるのは言葉だけ。数字・宣言基準・状態の列、表の並び、表の外の本文には触らない。
🔑 どの仮説かは signal-lab-tracker.json の label で引く。記事側で routine が足した印（<strong>・「★本回」・「🆕」など）は残す。
   台帳に無い名前の行は**そのまま残して報告する**（推測で訳さない）。
⚠️ 見出しの「前向き現在値(平均R)」と素の <table> は変えない＝check_plain_japanese.py がこの2つで表を見分けている。
⚠️ drafts/ 配下は対象外（routine の作業場）。
冪等＝2回目以降は data-mw-tracker-legend がある記事を飛ばす。
🆕 2026-09-25: 「宣言基準」「前向き現在値」「状態」の改行も整える（relayout）。型に合う古い書き方だけを並べ替え、
   数字の並びが1つも変わっていないことを表ごとに確かめる。新しい書き方には合わない＝2回目以降は何もしない。

使い方:
    python apply_tracker_plain_names.py           # 確認だけ（何本・何行が変わるか）
    python apply_tracker_plain_names.py --apply   # 書き込む
"""
import argparse, glob, html, io, os, re

from signal_lab_tracker import (crit_cell, load_tracker, plain_cell, plain_kind_cell, plain_legend, plain_name,
                                state_cell, value_cell)

HERE = os.path.dirname(os.path.abspath(__file__))
TABLE = re.compile(r"<table>(?:(?!</table>).)*?前向き現在値\(平均R\).*?</table>", re.S)  # check_plain_japanese と同じ
ROW = re.compile(r"(<tr[^>]*>\s*<td[^>]*>)(.*?)(</td>\s*<td[^>]*>)(.*?)(</td>)", re.S)  # 色付きの主題行（<tr class/style>）も対象
WRAP = re.compile(r"((?:<[^/>][^>]*>)*)(.*?)((?:</[^>]+>)*)", re.S)  # 先頭の開きタグ／中身／末尾の閉じタグ
MARK = "data-mw-tracker-legend"

# 途中で名前を付け直した仮説（古い記事には旧名で載っている）
ALIASES = {
    "売られすぎ逆張り買い(rsi_oversold_bounce)": "売られすぎ逆張り買い(rsi_oversold_bounce・全足)",
}


def convert(src, by_label):
    """記事HTML → (新HTML, 変換した行数, 台帳に無かった名前のリスト)。表が無い／変換済みなら行数0。"""
    if MARK in src:
        return src, 0, []
    m = TABLE.search(src)
    if not m:
        return src, 0, []
    labels = sorted(by_label, key=len, reverse=True)  # 長い名前から当てる（「group=metal」より「group=metal×dir=long」を先に）
    names, missing = [], []

    def row(r):
        lead, text, trail = WRAP.fullmatch(r.group(2).strip()).groups()
        inner = html.unescape(text)
        key = next((l for l in labels if inner.startswith(l)), None)
        if key is None or inner[len(key):].lstrip()[:1] in ("×", "="):  # 続きがあれば台帳に無い別の仮説

            missing.append(inner)
            return r.group(0)
        h = by_label[key]
        names.append(plain_name(h["filter"]))
        extra = html.escape(inner[len(key):])
        klead, ktext, ktrail = WRAP.fullmatch(r.group(4).strip()).groups()
        kind = ktext.strip() if ktext.strip() in ("edge", "gate") else None
        kcell = f"{klead}{plain_kind_cell(kind)}{ktrail}" if kind else r.group(4)
        return (f"{r.group(1)}{lead}{plain_cell(h['filter'], h['label'], extra)}{trail}"
                f"{r.group(3)}{kcell}{r.group(5)}")

    table = ROW.sub(row, m.group(0))
    if not names:
        return src, 0, missing
    return src[:m.start()] + plain_legend(names) + "\n    " + table + src[m.end():], len(names), missing


# ── 2026-09-25 追加: 「宣言基準」「前向き現在値」「状態」の改行（オーナー指示「改行をうまく使って見やすく」）
#    数字の文字は1つも変えない（符号の「−」「-」、区切りの「~」「〜」も記事のまま）。型に合わないセルは触らない。
TR = re.compile(r"(<tr[^>]*>)(.*?)(</tr>)", re.S)
TD = re.compile(r"(<td[^>]*>)(.*?)(</td>)", re.S)
NUM = r"[+\-−]?\d+\.\d+"
RE_CRIT = re.compile(r"前向きN≥(\d+)かつ平均RのCI(上限|下限)(?:<|>|&lt;|&gt;)0(🏁?)")
RE_VAL = re.compile(rf"平均R\s*({NUM})\s*CI\[({NUM})([~〜])({NUM})\]（(\d+)/(\d+)・([^）<]+)）")
NUMS = re.compile(r"\d+(?:\.\d+)?")


def _relayout_cell(i, inner):
    lead, text, trail = WRAP.fullmatch(inner.strip()).groups()
    if i == 2:
        m = RE_CRIT.fullmatch(text.strip())
        if m:
            return f"{lead}{crit_cell('edge' if m.group(2) == '下限' else 'gate', m.group(1), bool(m.group(3)))}{trail}"
    elif i == 3:
        m = RE_VAL.match(text.strip())
        if m:
            tail = text.strip()[m.end():]
            return (f"{lead}{value_cell(m.group(1), m.group(2), m.group(4), m.group(5), m.group(6), m.group(7), m.group(3))}"
                    f"{tail}{trail}")
    elif i == 4:
        return state_cell(inner)
    return inner


def relayout(src):
    """記事HTML → (新HTML, 変えたセル数)。表の中の数字の並びが変わっていないことを確かめてから返す。"""
    m = TABLE.search(src)
    if not m:
        return src, 0
    changed = [0]

    def tr(r):
        cells = TD.findall(r.group(2))
        if len(cells) != 5:
            return r.group(0)
        idx = iter(range(5))

        def td(c):
            new = _relayout_cell(next(idx), c.group(2))
            changed[0] += new != c.group(2)
            return c.group(1) + new + c.group(3)

        return r.group(1) + TD.sub(td, r.group(2)) + r.group(3)

    table = TR.sub(tr, m.group(0))
    # タグだけを消す（古い記事の生の「<0」はタグではない＝「<」の次が英字か「/」のものだけをタグとみなす）
    text = lambda h: html.unescape(re.sub(r"</?[A-Za-z][^>]*>", "", h))
    assert NUMS.findall(text(table)) == NUMS.findall(text(m.group(0))), "数字の並びが変わった"
    return src[:m.start()] + table + src[m.end():], changed[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="書き込む（無ければ確認だけ）")
    args = ap.parse_args()

    by_label = {h["label"]: h for h in load_tracker()["hypotheses"]}
    for old, new in ALIASES.items():
        if new in by_label:
            by_label[old] = dict(by_label[new], label=old)
    changed = rows = cells = 0
    missing_all = {}
    for p in sorted(glob.glob(os.path.join(HERE, "guide-signal-lab-*.html"))):
        src = io.open(p, encoding="utf-8").read()
        out, n, missing = convert(src, by_label)
        for x in missing:
            missing_all.setdefault(x, []).append(os.path.basename(p))
        out, c = relayout(out)
        if n == 0 and c == 0:
            continue
        changed += 1
        rows += n
        cells += c
        if args.apply:
            io.open(p, "w", encoding="utf-8", newline="").write(out)
    verb = "書き換えた" if args.apply else "書き換える予定"
    print(f"{verb}記事 {changed}本 / 仮説名の行 {rows} / 改行を整えたセル {cells}")
    if missing_all:
        print(f"⚠️ 台帳に無い名前（そのまま残した）{len(missing_all)}種:")
        for x, fs in sorted(missing_all.items(), key=lambda kv: -len(kv[1])):
            print(f"   {x!r}: {len(fs)}本（例 {fs[0]}）")
    if not args.apply and changed:
        print("→ 書き込むには --apply")


if __name__ == "__main__":
    main()
