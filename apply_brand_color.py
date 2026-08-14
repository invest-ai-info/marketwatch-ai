# -*- coding: utf-8 -*-
"""apply_brand_color.py — ブランドカラー「藍 × 山吹」を冪等適用する（2026-08-04）。

設計書: docs/superpowers/specs/2026-08-04-brand-color-design.md

⚠️ 最大の落とし穴＝`#0969da` はサイト内に366箇所あるが、その全てがブランド色ではない。
   リンク・見出し・境界・背景で役割が違う。**色→色の一括置換は絶対にしない。**
   このツールは「役割 → 色」の明示ルール表だけを当てる（下の RULES）。

使い方:
  python apply_brand_color.py --phase 1              # dry-run（既定・書き込まない）
  python apply_brand_color.py --phase 1 --apply      # 適用
  python apply_brand_color.py --phase 1 --revert     # 元に戻す
"""
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SD = os.path.dirname(os.path.abspath(__file__))

# ── 色トークン（単一の真実）─────────────────────────────
# 実測コントラスト（WCAG 2.1）はテスト `_test_apply_brand_color.py` が毎回検証する。
TOKENS = {
    "brand":      "#1E3A6E",   # 藍。面で使う。白文字 11.14:1 (AAA)
    "brand_lite": "#2C4F8F",   # 藍(明)。h2・インラインリンク。白地 8.01:1 (AAA)
    "accent":     "#E8A317",   # 山吹。⚠️塗り専用（白地の文字は 2.17:1 で不可）
    "accent_bg":  "#F5EDD8",   # 山吹(淡)。chip 背景など
}

# ── ダークモード用（TOKENS は Task 1 で確定済みなので触らず、別に持つ）─────
# ⚠️ 藍はダーク地では 1.70:1 でほぼ不可視。ダークの見出しに藍は使えない。
#    ブランド表現はダークでは「ナビ・ヘッダー」が担い、本文見出しは可読性を優先する。
DARK_BG = "#0d1117"    # 既存のダーク地（body.dark{background:#0d1117}）
DARK_INK = "#e6edf3"   # ダーク時の見出し色。ダーク稼働174本中118本が既に採用。16.02:1 (AAA)

# 注入した宣言の目印。これが付いている宣言だけを --revert で取り除くので、
# 「元から書いてあった宣言」を誤って消すことが原理的に起きない。
MARK = "/*mw-brand*/"


def _lum(hexs):
    h = hexs.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    f = [(x / 12.92) if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * f[0] + 0.7152 * f[1] + 0.0722 * f[2]


def contrast(a, b):
    """WCAG 2.1 のコントラスト比を返す。"""
    la, lb = _lum(a), _lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


# ── 置換ルール（役割 → 色）───────────────────────────────
# 各要素 = (phase, ラベル, 旧文字列, 新文字列)  ※すべて素の文字列（正規表現ではない）
#
# ⚠️ ここに「#0969da を全部置換」のような広いルールを足さないこと。
#    対象は必ずセレクタ名・プロパティ名ごと書き下して名指しする。
#    （`#0969da` はサイト内に散在するが、その全てがブランド色ではない）
#
# ⚠️ 正規表現にしないのは --revert を正確にするため。(旧,新) の素の組なら
#    revert は入れ替えるだけで必ず正しい。後方参照からの復元は原理的に不正確。
#
# 旧文字列は**末尾を開いたプレフィックス**にしてある（`;` で切る）。
# 理由＝同じ役割でも後続プロパティが揺れるため。実測（2026-08-04, guide-*.html
# 279本 + guides.html = 280本）:
#   h2 1.3rem 系は margin-top が 32px(52本)/30px(46本) の2系統 → プレフィックスなら1本で両取り
#   guides.html の h1 は margin-bottom で終わり line-height 無し → ブロック全体だと外す
RULES = [
    # --- Phase 1: 顔 ---
    # 実測 476回 / 280本。用途は .header-title（文字グラデ）と #reading-progress（進捗バー）。
    # ⚠️ 135deg 版は別物（guide-learning-roadmap.html の .rm-step-num＝本文中の丸数字）。対象外。
    (1, "ヘッダーのグラデーション",
     "linear-gradient(90deg,#0969da,#1f6feb)",
     f"linear-gradient(90deg,{TOKENS['brand']},{TOKENS['brand_lite']})"),

    # 実測 280回 / 280本（ライト時のみ）。
    # ⚠️ ダーク時の .nav-btn.current は #1f6feb の別ルール（151本+117本）＝Phase 1 では触らない。
    (1, "ナビ current の背景",
     ".nav-btn.current{background:#0969da;border-color:#0969da;",
     f".nav-btn.current{{background:{TOKENS['brand']};"
     f"border-color:{TOKENS['brand']};"),

    # ダーク時のナビ current。実測 151本（素）と 118本（!important 版）の2形。
    # ⚠️ **background だけ**を差し替え、border-color:#58a6ff は残す。
    #    塗り #2C4F8F はダーク地との差が 2.36:1 しかなく、枠線がボタンの境界(3:1)を担うため。
    #    枠線 #58a6ff vs ダーク地 = 7.49:1。なお白文字は 4.63:1 → 8.01:1 に改善する。
    (1, "ダークのナビ current の背景（素・151本）",
     "body.dark .nav-btn.current{background:#1f6feb;",
     f"body.dark .nav-btn.current{{background:{TOKENS['brand_lite']};"),

    (1, "ダークのナビ current の背景（!important・118本）",
     "body.dark .nav-btn.current{background:#1f6feb!important;",
     f"body.dark .nav-btn.current{{background:{TOKENS['brand_lite']}!important;"),

    # h1 の文字色。実測で font-size が3種に割れていたので3行に分けた（1行1バリエーション）。
    # 180 + 51 + 47 = 278本 / 280本。
    # ⚠️ 残り2本は h1{...;color:#cf222e}（速報記事の意図的な赤）＝意味色なので対象外。
    (1, "h1 の文字色（1.95rem・180本）",
     "h1{font-size:1.95rem;color:#0969da;",
     f"h1{{font-size:1.95rem;color:{TOKENS['brand']};"),

    (1, "h1 の文字色（1.85rem・51本）",
     "h1{font-size:1.85rem;color:#0969da;",
     f"h1{{font-size:1.85rem;color:{TOKENS['brand']};"),

    (1, "h1 の文字色（1.8rem・47本）",
     "h1{font-size:1.8rem;color:#0969da;",
     f"h1{{font-size:1.8rem;color:{TOKENS['brand']};"),

    # h2 の文字色。実測で font-size が2種。181 + 98 = 279本 / 280本。
    # ⚠️ 残り1本は guides.html（青い h2 を持たず .category-title を使う）＝対象なしで正しい。
    (1, "h2 の文字色（1.35rem・181本）",
     "h2{font-size:1.35rem;color:#1f6feb;",
     f"h2{{font-size:1.35rem;color:{TOKENS['brand_lite']};"),

    (1, "h2 の文字色（1.3rem・98本）",
     "h2{font-size:1.3rem;color:#1f6feb;",
     f"h2{{font-size:1.3rem;color:{TOKENS['brand_lite']};"),

    # ── 生成HTMLの **インライン style 属性** の見出し（2026-08-05 追加）──
    # ⚠️ CSSブロックのルールだけを名指ししていたため、生成ページの見出しが旧色のまま残っていた。
    #    実例＝index.html の h2 は <h2 style="font-size:1.25rem;color:#1f6feb;...">＝**要素の属性**で色を指定しており、
    #    `h2{font-size:...;color:...}` の名指しにはどうやっても当たらない（8/5 のライブ実測で発覚）。
    # ⚠️ 対応関係は既存ルールと同一＝#0969da→藍 / #1f6feb→藍(明)。新しい設計判断はしていない。
    # ⚠️ 見出しだけを名指しする。同じ属性に居る **本文の青文字278・リンク12・ボタン背景10・罫線4 は対象外**
    #    （役割が違う＝「色→色の一括置換は禁止」の原則）。font-size を含めることで本文と混ざらない。
    (1, "インライン見出し h1級（ヘッダーのページタイトル・7箇所）",
     "font-size:1.3rem;font-weight:700;color:#0969da",
     f"font-size:1.3rem;font-weight:700;color:{TOKENS['brand']}"),

    (1, "インライン見出し h2級（下線付きセクション見出し 1.2rem・8箇所）",
     "font-size:1.2rem;color:#1f6feb;",
     f"font-size:1.2rem;color:{TOKENS['brand_lite']};"),

    (1, "インライン見出し h2級（同 1.25rem・1箇所）",
     "font-size:1.25rem;color:#1f6feb;",
     f"font-size:1.25rem;color:{TOKENS['brand_lite']};"),

    (1, "インライン見出し h2級（track-record の小見出し・1箇所）",
     "font-size:1.2rem;color:#0969da;margin-bottom:12px",
     f"font-size:1.2rem;color:{TOKENS['brand']};margin-bottom:12px"),

    # ⚠️ `text-align:right;font-weight:800;color:#0969da!important;font-size:1.5rem` は**見出しではなく
    #    右寄せの数値表示**なので対象外（font-size だけで見出し判定すると巻き込む実例）。

    # ── クラウドの新テンプレ（CSS変数式）──
    # `guide-signal-lab-060.html`（2026-08-04 公開）だけが従来と別テンプレで、
    # 色を `var(--accent)` 経由で持つため既存ルールが1つも当たらなかった（295本中この1本）。
    # 今後このテンプレが標準化するなら後続記事にも自動で当たる＝ここに置く価値がある。
    # ⚠️ ダーク側の `--accent: #60a5fa` は**触らない**（藍(明)はダーク地で沈む）。
    #    実測でこの2箇所はどちらも :root と :root[data-theme="light"] ＝ライト専用。
    (1, "CSS変数テンプレの accent（ライトのみ）",
     "--accent: #2563eb",
     f"--accent: {TOKENS['brand_lite']}"),

    (1, "CSS変数テンプレの h1 に色を与える",
     "h1 { font-size: 1.45rem; line-height: 1.4;",
     f"h1 {{ font-size: 1.45rem; color: {TOKENS['brand']}; line-height: 1.4;"),

    # ⚠️ Phase 1 に山吹（accent）のルールは無い。意図的な不在であって書き忘れではない。
    #    設計書は「記事カードの左罫」を初出と想定していたが、実測の結果それは存在しなかった:
    #      - guides.html の .article-card は border-left を持たない（border 1px + hover 色のみ）
    #      - guide-*.html の border-left 付きカードは .scenario-card(bull/bear/base) /
    #        .threshold-card / .granville-card ＝すべて #1a7f37 / #cf222e / #9a6700 の意味色
    #      - 青い border-left は .info-box(215本) / .highlight-box(49本) / .kpi(18本)
    #        ＝いずれも本文の面。.info-box は設計書どおり Phase 2 送り
    #    無い適用先を作るより「面で使わない」原則を優先し、Phase 1 の山吹はロゴのみとする。

    # --- Phase 2: 本文 ---
    # 実測 824回 / 280本。
    (2, "インラインリンク（＋下線）",
     "a{color:#0969da;text-decoration:none}",
     f"a{{color:{TOKENS['brand_lite']};text-decoration:underline;"
     f"text-underline-offset:2px}}"),
]


# ── 注入ルール（無ければ足す）───────────────────────────
# 各要素 = (phase, ラベル, アンカー, 注入する文字列, 既存判定の正規表現)
#
# 置換型では直せない問題が1つだけある＝**宣言そのものが存在しない**ケース。
# ライトの h1 を藍にすると、ダーク時に h1 の色を上書きしていないファイルでは
# 藍がそのままダーク地に乗り 1.70:1（ほぼ不可視）になる。元々 3.64:1 で AA 割れ
# だった既存欠陥を、こちらの変更が大幅に悪化させる形。よって宣言を足して直す。
#
# ⚠️ アンカーは実測で決めた（2026-08-04）:
#    対象53本の **53本すべて** が `body.dark{background:#0d1117;color:#e6edf3}` を
#    **ちょうど1回**・`<style>` 内の**トップレベル**（@media の外）に持つ。
#    ＝書き方は完全に揃っており、部分集合に絞る必要はなかった。
#
# ⚠️ 注入する宣言には MARK を付ける。revert は MARK 付きだけを消すので、
#    元から書いてあった宣言を誤って消すことが起きない。
#
# ⚠️ h2 は注入しない。ダーク稼働174本の**全部**が既に
#    `body.dark h2{color:#79c0ff;...}` を持っており（9.73:1）、不足がない。
ENSURES = [
    (1, "ダーク時の h1 の文字色（注入）",
     "body.dark{background:#0d1117;color:#e6edf3}",
     f"{MARK}body.dark h1{{color:{DARK_INK}}}",
     # 既に何らかの形で h1 を上書きしていれば触らない。
     # 実測の内訳: `body.dark h1,body.dark h2,h3,h4{color:#e6edf3!important}` 118本 /
     #             `body.dark h1{color:#58a6ff}` 2本 / `#79c0ff` 系 2本
     re.compile(r"body\.dark[^{]{0,80}\bh1\b[^{]{0,80}\{[^}]*color", re.I)),
]


def fstring_form(s):
    """f-string に埋め込まれた CSS の形（波括弧が二重化された形）へ変換する。

    ⚠️ 2026-08-05 に実測で判明した穴の対策。生成スクリプト8本は CSS を **f-string の中**に
       持つので `{` が `{{`・`}` が `}}` になっている。RULES を素の形だけで名指ししていた間、
       **生成ページ（6コア/track-record/political-feed/youtube-summary/週次/月次）だけが
       塗り残されていた＝計31箇所**（ナビ12・ダークナビ9・h1が6・h2が4）。
       波括弧を含まないルール（ヘッダーのグラデ）だけは当たっていたため、
       「一部は変わっている」ように見えて気づきにくかった。

    正規表現ではなく単純な二重化なので、revert は (新,旧) を入れ替えるだけで正確に戻る
    ＝「素の文字列ペアで名指しする」という RULES の設計方針を崩さない。
    """
    return s.replace("{", "{{").replace("}", "}}")


def apply_rules(text, phase, revert=False):
    """(new_text, 変更件数) を返す。revert=True で逆方向に当てる。

    2種類のルールを順に当てる:
      RULES   … 素の文字列の置換。revert は (旧,新) を入れ替えるだけで正確に戻る。
                **素の形と f-string 形（`{{`）の両方**を当てる（静的HTMLと生成スクリプトの両対応）。
      ENSURES … 宣言が無ければアンカーの直後に注入。revert は MARK 付きを消すだけ。
    どちらも冪等（2回当てても結果が変わらない）。
    """
    total = 0
    for ph, _label, old, new in RULES:
        if ph != phase:
            continue
        # 素の形 → f-string 形 の順。互いに部分一致しないので順序で結果は変わらない
        # （`current{background` は `current{{background` の部分文字列にならない）。
        forms = [(old, new)]
        f_old, f_new = fstring_form(old), fstring_form(new)
        if f_old != old:                 # 波括弧を含まないルールは二重に数えない
            forms.append((f_old, f_new))
        for o, n_ in forms:
            src, dst = (n_, o) if revert else (o, n_)
            n = text.count(src)
            if n:
                text = text.replace(src, dst)
            total += n

    for ph, _label, anchor, inject, has_re in ENSURES:
        if ph != phase:
            continue
        if revert:
            # MARK 付きの注入分だけを消す。元からある宣言は MARK を持たないので無傷。
            n = text.count(inject)
            if n:
                text = text.replace(inject, "")
            total += n
            continue
        if inject in text or has_re.search(text):
            continue        # 既に注入済み or 元から上書きがある → 何もしない（冪等）
        if anchor not in text:
            continue        # ダークを持たないファイル → 対象外
        text = text.replace(anchor, anchor + inject, 1)
        total += 1
    return text, total


# 生成スクリプト（CSSを内蔵している8本）
SCRIPTS = [
    "generate_market_news.py", "generate_youtube_summary.py",
    "generate_track_record_page.py", "build_political_feed_page.py",
    "auto_weekly_strategy.py", "auto_weekly_review.py",
    "generate_monthly_report.py", "auto_indicator_preview.py",
]
# 6コア等は SYNC_FILES に無いので自動的に除外されるが、事故防止で明示的にも弾く
FORBIDDEN = {"index.html", "calendar.html", "charts.html", "vix.html",
             "market-health.html", "hot-assets.html",
             "track-record.html", "political-feed.html", "youtube-summary.html"}


def load_sync_files():
    """sync_to_github.py の SYNC_FILES を抽出（apply_back_to_top.py と同方式）。"""
    with open(os.path.join(SD, "sync_to_github.py"), encoding="utf-8") as f:
        s = f.read()
    m = re.search(r"SYNC_FILES\s*=\s*\[(.*?)\n\]", s, re.S)
    if not m:
        print("❌ sync_to_github.py の SYNC_FILES を解析できない")
        sys.exit(1)
    return set(re.findall(r'"([^"]+)"', m.group(1)))


def collect_targets(include_cloud=False, only_scripts=False):
    """SYNC入りの静的HTML＋生成スクリプトの絶対パス一覧を返す。

    include_cloud=True にすると、SYNC_FILES に登録されていない
    クラウド自動公開記事（guide-news-/signal-lab-/proverb-/auto-/weekly-/monthly-report-）
    も対象に含める。

    ⚠️ 既定を False にしてあるのは意図的。クラウド記事はローカルのコピーが
       古い場合があり、そのまま push するとクラウド側の更新を巻き戻すため
       （実測: 2026-08-04 に 135本が古い/欠落だった）。
       include_cloud=True で使う前に **必ず `_pull_mirror.py --apply` で
       ローカルを最新化すること。** これらは SYNC_FILES に載らないので、
       sync_to_github.py では push されない＝別途 Contents API で送る必要がある。
    """
    if only_scripts:
        # 生成スクリプト8本だけを対象にする。
        # ⚠️ 2026-08-05 のオーナー判断＝インライン見出しルールは**生成ページにだけ**当てる。
        #    同じ規則は静的記事187本のヘッダーラベルにも当たる（＝サイト全体で旧青のまま残っている）が、
        #    今回は送らないと決めた。将来フル `--apply` を回すとその187本も拾う＝想定どおりの挙動。
        return [os.path.join(SD, n) for n in SCRIPTS if os.path.exists(os.path.join(SD, n))]
    sync = load_sync_files()
    out = []
    for name in sorted(sync):
        if name in FORBIDDEN or not name.endswith(".html"):
            continue
        p = os.path.join(SD, name)
        if os.path.exists(p):
            out.append(p)
    if include_cloud:
        import glob
        seen = {os.path.basename(p) for p in out}
        for p in sorted(glob.glob(os.path.join(SD, "guide-*.html"))):
            name = os.path.basename(p)
            if name in seen or name in FORBIDDEN:
                continue
            out.append(p)
    for name in SCRIPTS:
        p = os.path.join(SD, name)
        if os.path.exists(p):
            out.append(p)
    return out


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", type=int, choices=(1, 2), required=True)
    ap.add_argument("--apply", action="store_true", help="実際に書き込む（既定は dry-run）")
    ap.add_argument("--revert", action="store_true", help="元に戻す")
    ap.add_argument("--include-cloud", action="store_true",
                    help="クラウド自動公開記事も対象に含める"
                         "（⚠️事前に差分の正体を revert 照合で測ること）")
    ap.add_argument("--only-scripts", action="store_true",
                    help="生成スクリプト8本だけに当てる（HTMLは触らない）")
    a = ap.parse_args()

    mode = "REVERT" if a.revert else "APPLY"
    if not a.apply:
        mode += "（DRY-RUN: 書き込みなし）"
    print(f"🎨 ブランドカラー Phase {a.phase} / {mode}")
    print(f"   藍={TOKENS['brand']} 藍(明)={TOKENS['brand_lite']} "
          f"山吹={TOKENS['accent']}")
    print("─" * 60)

    changed = total = 0
    targets = collect_targets(include_cloud=a.include_cloud,
                              only_scripts=a.only_scripts)
    for path in targets:
        with open(path, encoding="utf-8") as f:
            src = f.read()
        new, n = apply_rules(src, phase=a.phase, revert=a.revert)
        if n == 0 or new == src:
            continue
        changed += 1
        total += n
        print(f"  {'✅' if a.apply else '·'} {os.path.basename(path):52s} {n:>3}箇所")
        if a.apply:
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(new)

    print("─" * 60)
    print(f"対象 {len(targets)} / 変更 {changed} ファイル / 置換 {total} 箇所")
    if not a.apply:
        print("DRY-RUN 完了。問題なければ --apply を付けて再実行。")
    else:
        print("完了。次: python mw.py check → python sync_to_github.py")


if __name__ == "__main__":
    main()
