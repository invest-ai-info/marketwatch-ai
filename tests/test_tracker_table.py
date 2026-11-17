# -*- coding: utf-8 -*-
"""研究日誌の前向きトラッカー表（signal_lab_tracker.table_html / insert_table）のテスト。2026-10-17 新設。

背景＝表が73本で約4万字になり、予約 signal-lab-daily が下書きを1回で書くと出力の上限（32,000トークン）を超えて
10/16・10/17 の朝に止まった。オーナー「順番に進めてください」で、①表を短くする ②道具で下書きに差し込む、を入れた。
確かめること＝①表に載るのは昇格・蓄積中と、終わって7日以内の仮説だけ・省いた件数とエッジ番付へのリンク
②固定の検査（exit_lab_verify・check_plain_japanese）が新しい表を前と同じく「表」として扱う
③--into の目印の置き換え・前の表の置き換え（何度でも）・どちらも無いときは止まる ④手順書に書いてある。
🆕 2026-11-17 ⑤表は枠と CSS ごと出る（素の表で公開されて「ごちゃごちゃして見づらい」とオーナー）・過去の記事も揃っている。

実行:  python tests/test_tracker_table.py     （pytest 不要。pytest でも動く）
"""
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import check_plain_japanese as C  # noqa: E402
import exit_lab_verify as E  # noqa: E402
import signal_lab_tracker as T  # noqa: E402


def _h(i, status, n=10, **kw):
    h = {"id": f"h{i}", "label": f"group=metal×dir=long#{i}", "kind": "edge", "filter": {"group": "metal", "direction": "long"},
         "status": status, "registered_at": "2026-07-01",
         "forward": {"k": n // 2, "n": n, "pct": 50.0, "avgR": 0.05, "rci_lo": -0.1, "rci_hi": 0.2}}
    h.update(kw)
    return h


def _tracker():
    return {"updated_at": "2026-10-17", "hypotheses": [
        _h(1, "tracking", n=30), _h(2, "promoted", n=90), _h(3, "tracking", n=5),
        _h(4, "rejected", n=400),                                   # 古い反証（日付なし）＝省く
        _h(5, "retired", n=500, retired_at="2026-10-09"),           # 8日前＝省く
        _h(6, "rejected", n=300, rejected_at="2026-10-16"),         # 昨日の反証＝その日の主役になりうる＝残す
        _h(7, "retired", n=300, retired_at="2026-10-10")]}          # ちょうど7日前＝残す


def test_rows_shown_and_hidden():
    shown, hidden = T.table_rows(_tracker()["hypotheses"], "2026-10-17")
    assert [h["id"] for h in shown] == ["h2", "h1", "h3", "h6", "h7"]          # 昇格→蓄積中（件数の多い順）→終わって7日以内
    assert hidden == {"rejected": 1, "retired": 1}
    shown, hidden = T.table_rows(_tracker()["hypotheses"], "2026-11-30")
    assert hidden == {"rejected": 2, "retired": 2} and len(shown) == 3


def test_html_keeps_the_shape_the_checks_rely_on():
    block = T.table_html(_tracker(), "2026-10-17")
    assert block.count("<tr>") == 1 + 5 and "<table><tr><th>仮説</th>" in block and "前向き現在値(平均R)" in block
    legend = block[block.index("data-mw-tracker-legend"):block.index("<table>")]
    assert "確かめ終えた2本（⛔反証1本・⏹見込みなし1本）を含む全部の一覧" in legend
    assert "本を載せています" not in legend                                    # 載せた本数は書かない（書き手が表を削っても嘘にならない）
    assert 'href="track-record.html#banzuke"' in legend
    none_hidden = {"updated_at": "x", "hypotheses": [_h(1, "tracking")]}
    assert "全部の一覧" not in T.table_html(none_hidden, "2026-10-17")           # 省いたものが無ければ一文も無い


def test_fixed_checks_treat_it_as_the_table():
    doc = "<html><body><main><p>本文です。</p>" + T.table_html(_tracker(), "2026-10-17") + "<p>おわりです。</p></main></body></html>"
    text, _svg, tracker = E.body_text(doc)
    assert "確かめ終えた2本" in tracker and "確かめ終えた" not in text        # 件数は表の側＝本文の数字の出どころに数えない
    stripped = C._strip_machine_parts(doc)
    assert "前向き現在値" not in stripped                                      # やさしい日本語の検査は表を飛ばす


def test_insert_into_draft():
    d = tempfile.mkdtemp()
    path = os.path.join(d, "draft.html")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("<p>前</p>\n" + T.TABLE_MARK + "\n<p>後</p>\n")
    block = T.table_html(_tracker(), "2026-10-17")
    assert T.insert_table(path, block) == "mark"
    assert T.insert_table(path, block) == "replaced"                           # 2回目＝前の表を置き換える
    doc = open(path, encoding="utf-8").read()
    assert doc.count('<h2 id="tracker">') == 1 and doc.startswith("<p>前</p>") and doc.rstrip().endswith("<p>後</p>")
    assert T.TABLE_MARK not in doc
    bad = os.path.join(d, "bad.html")
    with open(bad, "w", encoding="utf-8") as fh:
        fh.write("<p>x</p>")
    try:
        T.insert_table(bad, block)
        raise AssertionError("目印も表も無いのに差し込めてしまった")
    except ValueError:
        pass
    assert open(bad, encoding="utf-8").read() == "<p>x</p>"                    # 黙って足さない


def test_table_carries_its_own_frame():
    """2026-11-17 オーナー「このリストの文字がごちゃごちゃしていて見づらい」＝素の表（余白・区切り線なし）に戻さない。"""
    block = T.table_html(_tracker(), "2026-10-17")
    i, j = block.index('<div class="mw-tracker">'), block.index("<table>")
    assert i < j and "data-mw-tracker-style" in block[i:j]                    # 枠と CSS が表の直前にある
    assert block.rstrip().endswith("</table>\n</div>\n" + T.TABLE_END)
    assert '<td class="mw-st mw-st-promoted">' in block and '<td class="mw-st mw-st-rejected">' in block
    assert block.count('class="mw-st ') == 5                                  # 状態の列だけ＝行の数と同じ


def test_insert_replaces_framed_table_without_leftovers():
    d = tempfile.mkdtemp()
    path = os.path.join(d, "draft.html")
    block = T.table_html(_tracker(), "2026-10-17")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("<p>前</p>\n" + block + "\n<h2>次の節</h2>\n<p>後</p>\n")
    assert T.insert_table(path, block) == "replaced"
    doc = open(path, encoding="utf-8").read()
    assert doc.count('<div class="mw-tracker">') == 1 and doc.count(T.TABLE_END) == 1
    assert doc.count("<div") == doc.count("</div>")                          # 枠の </div> が残らない
    assert "<h2>次の節</h2>" in doc


def test_restyle_past_articles_keeps_the_words():
    import apply_tracker_table_style as A
    old_block = T.table_html(_tracker(), "2026-10-17")
    bare = old_block[old_block.index("<table>"):old_block.index("</table>") + len("</table>")]
    bare = bare.replace('<td class="mw-st mw-st-promoted">', "<td>").replace('<td class="mw-st mw-st-tracking">', "<td>")
    bare = bare.replace('<td class="mw-st mw-st-rejected">', "<td>").replace('<td class="mw-st mw-st-retired">', "<td>")
    doc = "<p>本文</p>\n" + bare + "\n<p>後</p>"
    new, n = A.restyle(doc)
    assert n == 1 and 'class="mw-tracker"' in new and A._text(new) != "" 
    strip = lambda h: A._text(h[h.index("<table>"):h.index("</table>")])
    assert strip(new) == strip(doc)                                          # 表の文字は1文字も変わらない
    assert '<td class="mw-st mw-st-tracking">' in new
    assert A.restyle(new) == (new, 0)                                        # 2回目は何もしない
    doc2 = "<html>" + new + "</html>"
    assert "前向き現在値" not in C._strip_machine_parts(doc2)                 # やさしい日本語の検査は今までどおり表を飛ばす


def test_published_signal_lab_tables_are_framed():
    import glob
    import re
    bare = [p for p in glob.glob("guide-signal-lab-*.html")
            if re.search(r"<table>(?:(?!</table>).)*?前向き現在値\(平均R\)", open(p, encoding="utf-8").read(), re.S)
            and 'class="mw-tracker"' not in open(p, encoding="utf-8").read()]
    assert bare == [], bare


def test_sop_says_so():
    sop = open("SIGNAL_LAB_SOP.md", encoding="utf-8").read()
    assert "--into drafts/draft-signal-lab-NNN.html" in sop and "<!-- MW:TRACKER_TABLE -->" in sop
    assert "下書きは1回の Write で丸ごと書かない" in sop and T.RECENT_END_DAYS == 7


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"✅ {name}")
            except AssertionError as e:
                fails += 1
                print(f"❌ {name}: {e}")
    sys.exit(1 if fails else 0)
