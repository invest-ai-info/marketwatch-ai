# -*- coding: utf-8 -*-
"""部品の色をトップの色に・暗い表示を足す（page_palette.py）のテスト。2026-11-21 新設。

固定すること:
  ・トップの色（TOP_LIGHT／TOP_DARK）は generate_market_news.HOME_V2_CSS の :root と body.dark と同じ値
  ・灰色→地・枠・文字、青→ブランド、緑→上げ、赤→下げ、淡い地→トップの淡い4色。紫・桃などはそのまま。白に近い灰色は淡い青にしない
  ・明るい表示ではページ自身の CSS だけを置き換え、HTML に直接書かれた色（データで決まる濃さ）は触らない
  ・暗い表示はトップの暗い色へ。HTML に直接書かれた色も上書きする（!important）。ボタンの濃い地と白い文字はそのまま
  ・</body> の直前に1つだけ・冪等・スイッチ（ON／PALETTE）で消える
  ・暗い表示を持つページ・解説記事には何もしない（apply_site_frame.process）

実行:  python tests/test_page_palette.py     （pytest 不要。pytest でも動く）
"""
import os
import re
import sys
import warnings

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import apply_site_frame as F  # noqa: E402
import page_palette as P  # noqa: E402

PAGE = """<!DOCTYPE html><html><head><meta charset="UTF-8"><title>t</title>
<style>
body{background:#ffffff;color:#1f2937}
.card{background:#f8fafc;border:1px solid #e2e8f0;color:#334155}
.btn{background:#2563eb;color:#fff}
.up{color:#16a34a}.down{color:#dc2626}
.note{background:linear-gradient(135deg,#ecfdf5,#dbeafe);border-left:4px solid #7c3aed}
@media (max-width:640px){.card{background:#f1f5f9}}
@keyframes fade{from{color:#000}to{color:#fff}}
</style></head>
<body><main><div class="card" style="background:#fee2e2;color:#991b1b">x</div><p style="color:#24292f">y</p></main></body></html>"""


def _pal(text):
    m = re.search(r"<style data-mw-palette>(.*?)</style>", text, re.S)
    return m.group(1) if m else None


def test_top_colors_match_the_home_page():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SyntaxWarning)
        import generate_market_news as M
    root = re.search(r":root\{(.*?)\}", M.HOME_V2_CSS, re.S).group(1)
    dark = re.search(r"body\.dark\{(.*?)\}", M.HOME_V2_CSS, re.S).group(1)
    for k, v in P.TOP_LIGHT.items():
        assert f"--{k}:{v};" in root.replace("\n", "").replace(" ", "") + ";", k
    for k, v in P.TOP_DARK.items():
        assert f"--{k}:{v};" in dark.replace("\n", "").replace(" ", "") + ";", k


def test_color_roles():
    L = P.to_light
    assert L("#f8fafc", "bg") == "#f5f8fc" and L("#f1f5f9", "bg") == "#f5f8fc"          # 白に近い灰色＝地（淡い青にしない）
    assert L("#e2e8f0", "border") == "#dbe3ee" and L("#94a3b8", "text") == "#7b879a"
    assert L("#64748b", "text") == "#526075" and L("#1e293b", "text") == "#1b2433"
    assert L("#dbeafe", "bg") == "#eaf3ff" and L("#dcfce7", "bg") == "#e4f6f2" and L("#fef3c7", "bg") == "#fff3dc"
    assert L("#2563eb", "bg") == "#1766d6" and L("#2563eb", "text") == "#1263cc"
    assert L("#16a34a", "text") == "#16884a" and L("#dc2626", "text") == "#d9363e"
    assert L("#7c3aed", "text") == "#7c3aed" and L("#be185d", "text") == "#be185d"   # 役目の無い色はそのまま
    assert L("#fff", "text") == "#fff"                                                 # ボタンの白い文字
    assert L("rgba(37,99,235,.2)", "bg") == "rgba(23,102,214,0.2)"                     # 透明度は残す
    for v in P.TOP_LIGHT.values():                                                     # トップの色は動かない
        assert L(v, "bg") == v and L(v, "border") == v


def test_dark_roles():
    D = P.to_dark
    assert D("#f5f8fc", "bg") == "#151d28" and D("#ffffff", "bg") == "#151d28"
    assert D("#eaf3ff", "bg") == "#13233a" and D("#dbe3ee", "border") == "#283444"
    assert D("#1b2433", "text") == "#e7edf5" and D("#526075", "text") == "#a1adbd"
    assert D("#1263cc", "text") == "#7fb2ff" and D("#d9363e", "text") == "#ff7a72"
    assert D("#1766d6", "bg") == "#1766d6" and D("#ffffff", "text") == "#ffffff"       # ボタンはそのまま
    a, b = P.parse(D("#fee2e2", "bg")), P.parse(D("#fecaca", "bg"))                   # 濃さの順は残る（淡いほど暗く）
    assert sum(a[:3]) < sum(b[:3])
    assert sum(P.parse(D("#991b1b", "text"))[:3]) > sum(P.parse("#991b1b")[:3])        # 暗い文字は明るく


def test_layers_light_only_own_css_and_dark_covers_inline():
    tag = _pal(P.apply(PAGE))
    light, dark = tag.split(P.BASE_DARK)
    assert ".card{background:#f5f8fc;border:1px solid #dbe3ee;color:#1b2433}" in light
    assert ".btn{background:#1766d6}" in light and ".up{color:#16884a}" in light
    assert "@media (max-width:640px){.card{background:#f5f8fc}}" in light
    assert "#7c3aed" not in light and "fade" not in tag                                # 紫の枠はそのまま・@keyframes は読まない
    assert "#fee2e2" not in light and "#991b1b" not in light                           # 明るい表示では HTML の色に触らない
    assert "body.dark .card{" in dark and "body.dark{" in dark
    assert '[style^="background:#fee2e2"]' in dark and '[style*=";color:#991b1b"]' in dark and "!important" in dark
    assert '[style^="color:#24292f"]' in dark


def test_place_once_idempotent_and_switch():
    once = P.apply(PAGE)
    assert once.count("<style data-mw-palette>") == 1 and once.index("<style data-mw-palette>") > once.index("</main>")
    assert P.apply(once) == once
    assert P.apply(once, on=False) == PAGE


def test_frame_applies_only_to_pages_without_their_own_dark(monkeypatch=None):
    out, notes = F.process(PAGE, "calendar.html", pages_v2=True)
    assert "palette" in notes and _pal(out) and F.SKIN_V2_STYLE_TAG in out          # 暗い表示を足すページはヘッダーも暗くなる
    assert F.process(out, "calendar.html", pages_v2=True)[0] == out
    dark_page = PAGE.replace("</style>", "".join(f"body.dark .c{i}{{color:#fff}}" for i in range(12)) + "</style>", 1)
    out2, notes2 = F.process(dark_page, "calendar.html", pages_v2=True)
    assert "palette" not in notes2 and _pal(out2) is None                              # 自分の暗い表示を持つページは今のまま
    assert _pal(F.process(PAGE, "guide-sample.html", v2=True)[0]) is None             # 解説記事は対象外
    assert _pal(F.process(PAGE, "index.html")[0]) is None                              # トップ（V2_PAGES に無い）も対象外
    off, n_off = F.process(out, "calendar.html", pages_v2=False)
    assert _pal(off) is None and "palette-removed" in n_off                            # 前の形に戻すと消える
    old = P.ON
    try:
        P.ON = False
        assert _pal(F.process(out, "calendar.html", pages_v2=True)[0]) is None         # スイッチで消える
    finally:
        P.ON = old


def test_generator_has_no_inline_important_colors_in_the_rate_table():
    """HTML に直接書いた !important はどの CSS より強い＝暗い表示の上書きが効かない（2026-11-21 市場健康度の金利の表）"""
    src = open(os.path.join(ROOT, "generate_market_news.py"), encoding="utf-8").read()
    i = src.index("_swtd = ")
    block = src[i:src.index("</table>", src.index("通貨ペア", i))]
    assert not re.search(r"color:[^;\"']*!important", block)


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
            except Exception as e:  # noqa: BLE001
                fails += 1
                print(f"💥 {name}: {type(e).__name__}: {e}")
    sys.exit(1 if fails else 0)
