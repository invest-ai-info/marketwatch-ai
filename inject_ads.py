"""
inject_ads.py — A8.net アフィリ広告（「広告」ラベル付き）を、商品ごとに
関連 guide ページの記事末（メルマガ直前）へ冪等注入する保守ツール。

方針:
  - 商品 -> 関連ページの対応は PAGES に明示（関連性の高いページにだけ出す）。
  - 「広告」ラベル必須（景表法ステマ規制）。煽り文言は足さない（白を維持）。
  - 冪等: 既に "mw-ad" を含むページはスキップ。
  - 挿入位置: メルマガブロックの直前（無ければ <footer 直前）。

使い方:
  python inject_ads.py --dry-run   # 変更内容を確認（書き込まない）
  python inject_ads.py             # 実行

新しいアフィリ追加時 = ADS に商品ブロックを足し、PAGES に対応ページを書いて再実行。
"""
import os
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))

AD_CSS = """<style>
.mw-ad{max-width:680px;margin:32px auto;padding:14px 16px 16px;text-align:center;border:1px solid #d0d7de;border-radius:12px;background:#f6f8fa}
.mw-ad .mw-ad-label{display:block;font-size:.66rem;color:#8b949e;letter-spacing:.1em;margin-bottom:8px;text-align:left}
.mw-ad img{max-width:100%;height:auto;vertical-align:middle}
.mw-ad .mw-ad-pc{display:block}
.mw-ad .mw-ad-sp{display:none}
@media(max-width:520px){.mw-ad .mw-ad-pc{display:none}.mw-ad .mw-ad-sp{display:block}}
body.dark .mw-ad{background:#161b22;border-color:#30363d}
body.dark .mw-ad .mw-ad-label{color:#6e7681}
</style>"""

ADS = {
    "kabu": """<!-- ===== 広告 (A8.net / DMM株) ===== -->
<div class="mw-ad" aria-label="広告">
  <span class="mw-ad-label">広告</span>
  <div class="mw-ad-pc">
    <a href="https://px.a8.net/svt/ejp?a8mat=4B5R09+7CXWZ6+1WP2+15Q22P" rel="nofollow noopener" target="_blank"><img border="0" width="468" height="60" alt="DMM株" src="https://www27.a8.net/svt/bgt?aid=260608761445&wid=001&eno=01&mid=s00000008903007008000&mc=1"></a>
    <img border="0" width="1" height="1" src="https://www15.a8.net/0.gif?a8mat=4B5R09+7CXWZ6+1WP2+15Q22P" alt="">
  </div>
  <div class="mw-ad-sp">
    <a href="https://px.a8.net/svt/ejp?a8mat=4B5R09+7CXWZ6+1WP2+15PUCX" rel="nofollow noopener" target="_blank"><img border="0" width="320" height="50" alt="DMM株" src="https://www26.a8.net/svt/bgt?aid=260608761445&wid=001&eno=01&mid=s00000008903007007000&mc=1"></a>
    <img border="0" width="1" height="1" src="https://www16.a8.net/0.gif?a8mat=4B5R09+7CXWZ6+1WP2+15PUCX" alt="">
  </div>
</div>
""" + AD_CSS + """
<!-- ===== /広告 ===== -->
""",
    "cfd": """<!-- ===== 広告 (A8.net / DMM CFD) ===== -->
<div class="mw-ad" aria-label="広告">
  <span class="mw-ad-label">広告</span>
  <div class="mw-ad-pc">
    <a href="https://px.a8.net/svt/ejp?a8mat=4B5R09+79YQYA+1WP2+NY1Y9" rel="nofollow noopener" target="_blank"><img border="0" width="468" height="60" alt="DMM CFD" src="https://www25.a8.net/svt/bgt?aid=260608761440&wid=001&eno=01&mid=s00000008903004022000&mc=1"></a>
    <img border="0" width="1" height="1" src="https://www15.a8.net/0.gif?a8mat=4B5R09+79YQYA+1WP2+NY1Y9" alt="">
  </div>
  <div class="mw-ad-sp">
    <a href="https://px.a8.net/svt/ejp?a8mat=4B5R09+79YQYA+1WP2+NX735" rel="nofollow noopener" target="_blank"><img border="0" width="234" height="60" alt="DMM CFD" src="https://www27.a8.net/svt/bgt?aid=260608761440&wid=001&eno=01&mid=s00000008903004018000&mc=1"></a>
    <img border="0" width="1" height="1" src="https://www16.a8.net/0.gif?a8mat=4B5R09+79YQYA+1WP2+NX735" alt="">
  </div>
</div>
""" + AD_CSS + """
<!-- ===== /広告 ===== -->
""",
}

PAGES = {
    "cfd": [
        "guide-nikkei-60000.html",                 # 済
        "guide-nikkei-60k-break-2026-05-20.html",
        "guide-nikkei-65k-break-2026-05-25.html",
        "guide-sell-in-may.html",
    ],
    "kabu": [
        "guide-nisa.html",                         # 済
        "guide-nisa-ranking.html",
        "guide-japan-strategy-2026-05.html",
        "guide-toyota-2026-05.html",
        "guide-softbank-group-2026-05.html",
        "guide-bank-stocks-2026-05.html",
        "guide-nvidia-2026-05.html",
        "guide-tsmc-2026-05.html",
        "guide-amd-2026-05.html",
        "guide-kioxia-2026-05.html",
        "guide-oriental-land-2026-06.html",
    ],
}

NL_MARKER = "<!-- ===== MarketWatch 無料メルマガ登録"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    injected = already = missing = noanchor = 0
    for product, pages in PAGES.items():
        block = ADS[product]
        for name in pages:
            path = os.path.join(HERE, name)
            if not os.path.exists(path):
                missing += 1
                print(f"  MISS {name}: ファイル無し")
                continue
            with open(path, "r", encoding="utf-8") as f:
                c = f.read()
            if "mw-ad" in c:
                already += 1
                continue
            if NL_MARKER in c:
                new = c.replace(NL_MARKER, block + "\n" + NL_MARKER, 1)
            elif "<footer" in c:
                new = c.replace("<footer", block + "\n<footer", 1)
            else:
                noanchor += 1
                print(f"  WARN {name}: 挿入位置なし -> スキップ")
                continue
            injected += 1
            if args.dry_run:
                print(f"  [dry] {product:4} -> {name}")
            else:
                with open(path, "w", encoding="utf-8", newline="\n") as f:
                    f.write(new)
                print(f"  OK   {product:4} -> {name}")

    print("-" * 32)
    head = "DRY-RUN " if args.dry_run else ""
    print(f"{head}injected={injected} / already={already} / missing={missing} / no-anchor={noanchor}")


if __name__ == "__main__":
    main()
