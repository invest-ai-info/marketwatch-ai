# -*- coding: utf-8 -*-
"""図の文字の重なり検査（svg_layout_check.py）のテスト。2026-11-17 新設。

背景＝研究日誌 #152 の図で「ここで買いのシグナル」がローソク足に、「RSIの30の線（売られすぎの目安）」が
RSI の折れ線に重なったまま公開された。固定の検査は「文字どうし」「あとから描いた箱に隠れる」しか見ておらず、
Opus のコンプラ・品質レーンは図の見た目を見ない＝誰も止められなかった。
確かめること＝①#152 の元の図を止める・直した図は通す ②正しい描き方（棒の中の文字・背景・細い目盛り線・
縁取りの文字・半透明の帯・引き出し線の先）は止めない ③公開の経路（finalize・publish_article・mw check）が呼ぶ。

実行:  python tests/test_svg_layout_check.py     （pytest 不要。pytest でも動く）
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import svg_layout_check as L  # noqa: E402

# #152「4. 図で見ると」の元の図（必要な要素だけ・座標はそのまま）
FIG152_BEFORE = '''<svg viewBox="0 0 640 340" xmlns="http://www.w3.org/2000/svg">
<rect width="640" height="340" fill="var(--c-surface,#fff)" rx="6"/>
<g stroke="var(--c-green,#16a34a)" stroke-width="1.5"><line x1="330" y1="135" x2="330" y2="180"/><line x1="380" y1="120" x2="380" y2="160"/><line x1="430" y1="105" x2="430" y2="145"/><line x1="480" y1="95" x2="480" y2="132"/></g>
<g fill="var(--c-green,#16a34a)"><rect x="322" y="145" width="16" height="26"/><rect x="372" y="128" width="16" height="24"/><rect x="422" y="112" width="16" height="24"/><rect x="472" y="102" width="16" height="22"/></g>
<rect x="310" y="125" width="40" height="64" fill="none" stroke="#d4a017" stroke-width="2" rx="6"/>
<text x="352" y="122" font-size="11" font-family="sans-serif" fill="var(--c-muted,#5a6072)">ここで買いのシグナル</text>
<line x1="60" y1="285" x2="620" y2="285" stroke="var(--c-warn,#d97706)" stroke-width="1" stroke-dasharray="4,3"/>
<text x="62" y="281" font-size="10" font-family="sans-serif" fill="var(--c-warn,#d97706)">RSIの30の線（売られすぎの目安）</text>
<polyline points="80,255 130,262 180,272 230,285 280,296 330,288 380,272 430,258 480,248" fill="none" stroke="var(--c-accent,#2563eb)" stroke-width="2.5"/>
</svg>'''
FIG152_AFTER = (FIG152_BEFORE
                .replace('<text x="352" y="122" font-size="11"', '<text x="330" y="114" font-size="11" text-anchor="middle"')
                .replace('<text x="62" y="281" font-size="10"', '<text x="618" y="280" font-size="10" text-anchor="end"'))


def _w(body, head="", vb="0 0 400 200"):
    return L.layout_check(f'<html><head>{head}</head><body><svg viewBox="{vb}">{body}</svg></body></html>')


def test_fig152_before_is_stopped_and_after_passes():
    ws = L.layout_check(FIG152_BEFORE)
    assert len(ws) == 2, ws
    assert any("ここで買いのシグナル" in w and "四角" in w for w in ws)      # ローソク足の実体に重なる
    assert any("RSIの30の線" in w and "折れ線が横切る" in w for w in ws)     # あとから描いた RSI の線が横切る
    assert all(w.startswith(L.FIXABLE) for w in ws)                          # 直し方が決まる＝routine が直して再実行できる
    assert L.layout_check(FIG152_AFTER) == []


def test_published_152_is_clean():
    with open("guide-signal-lab-152.html", encoding="utf-8") as fh:
        assert L.layout_check(fh.read()) == []


def test_label_on_its_own_box_is_fine():
    # 棒の中の白い文字・ラベルの背景の箱（文字より先に描き、文字をまるごと包む）＝正しい描き方
    assert _w('<rect x="50" y="50" width="120" height="40" fill="#2563eb"/>'
              '<text x="110" y="75" font-size="12" text-anchor="middle" fill="#fff">42.3%</text>') == []
    # 図の背景（viewBox のほぼ全体）も数えない
    assert _w('<rect x="0" y="0" width="400" height="200" fill="#fff"/><text x="10" y="20">見出し</text>') == []


def test_box_partly_under_text_is_stopped():
    ws = _w('<rect x="100" y="40" width="30" height="40" fill="#16a34a"/>'
            '<text x="80" y="60" font-size="12">はみ出す文字です</text>')
    assert len(ws) == 1 and "重なる" in ws[0]


def test_line_drawn_after_text_is_stopped():
    ws = _w('<text x="20" y="100" font-size="12">基準線の説明</text>'
            '<line x1="0" y1="96" x2="400" y2="96" stroke="#d97706" stroke-width="1"/>')
    assert len(ws) == 1 and "横切る" in ws[0]


def test_thin_grid_before_text_is_fine_but_bold_line_is_not():
    thin = '<line x1="0" y1="96" x2="400" y2="96" stroke="#e2e6ed" stroke-width="0.5"/><text x="20" y="100">47.8%</text>'
    bold = '<line x1="0" y1="96" x2="400" y2="96" stroke="#d97706" stroke-width="1.5"/><text x="20" y="100">41.1%</text>'
    assert _w(thin) == []                                     # 目盛りの補助線＝文字の下に透けても読める
    assert len(_w(bold)) == 1                                  # #152 の図3「41.1%」と 43% の線


def test_halo_text_on_line_is_fine():
    assert _w('<polyline points="0,96 400,96" fill="none" stroke="#2563eb" stroke-width="2"/>'
              '<text x="20" y="100" stroke="#fff" stroke-width="3" paint-order="stroke">縁取りの文字</text>') == []


def test_css_class_anchor_and_translucent_zone():
    css = ("<style>.lbl{text-anchor:middle;font-size:10px}.zone{fill:#ffebe9;opacity:.45}"
           "body.dark .lbl{text-anchor:start}</style>")
    # class で中央寄せの文字＝左寄せと見誤ると右の箱に重なって見える（#4519 中外製薬の図で実測）
    body = ('<rect x="160" y="40" width="80" height="40" fill="#f6f8fa"/>'
            '<text class="lbl" x="100" y="60">（中央寄せの説明）</text>')
    assert _w(body, head=css) == []
    assert len(_w(body.replace('class="lbl" ', 'font-size="10" '))) == 1
    # 半透明の帯の上の文字は読める＝数えない
    assert _w('<rect x="0" y="40" width="200" height="60" class="zone"/><text x="180" y="60">MA75</text>', head=css) == []


def test_leader_line_touching_label_end_is_fine():
    # 引き出し線の先が文字の端に触れるだけ（中を4px未満しか通らない）
    assert _w('<text x="20" y="60" font-size="12">Aさん買い</text>'
              '<line x1="200" y1="56" x2="74" y2="56" stroke="#dc2626" stroke-dasharray="3,3"/>') == []


def test_defs_and_translate():
    assert _w('<defs><rect id="r" x="0" y="40" width="300" height="40" fill="#000"/></defs>'
              '<text x="20" y="60">定義の中身は描かれない</text>') == []
    ws = _w('<g transform="translate(100,0)"><line x1="0" y1="0" x2="0" y2="200" stroke="#000" stroke-width="2"/></g>'
            '<text x="60" y="60" font-size="12">移動した線が横切る</text>')
    assert len(ws) == 1


def test_gates_call_it():
    import check_site_consistency as C
    import finalize_signal_lab as F
    import publish_article as P
    assert P.check_svg_gate(FIG152_BEFORE) and P.check_svg_gate(FIG152_BEFORE, allow=True) == []
    assert P.check_svg_gate(FIG152_AFTER) == []
    try:
        F._svg_layout_gate(FIG152_BEFORE)
        raise AssertionError("重なった図なのに finalize が止まらない")
    except SystemExit as e:
        assert e.code == 1
    F._svg_layout_gate(FIG152_AFTER)                           # 通る（何も起きない）
    assert C.SVG_LAYOUT_SINCE == "2026-11-18" and callable(C.check_svg_layout)
    sop = open("SIGNAL_LAB_SOP.md", encoding="utf-8").read()
    assert "svg_layout_check.py" in sop


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
