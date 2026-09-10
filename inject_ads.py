"""inject_ads.py — A8.net アフィリ広告（「広告」ラベル付き）を、記事末（メルマガ直前）へ
冪等注入する保守ツール。**記事ごとに決めた候補の中から1つをランダム表示**する。

方針:
  - 候補は記事ごとに `POOLS` で明示（関連性の高い広告だけを候補にする）。
  - 「広告」ラベル必須（景表法ステマ規制・2023-10-01 施行）。煽り文言は足さない（白を維持）。
  - 冪等: 既に "mw-ad" を含むページはスキップ。`--replace` で既存ブロックを貼り替え。
  - 挿入位置: メルマガブロックの直前（無ければ <footer 直前）。

🚨 2026-09-10 に直した設計上の欠陥（実測で発見）:
  旧方式は PC 用と SP 用のバナーを**両方 HTML に書いて CSS で片方を隠す**形だった。
  ブラウザは display:none の中の <img> も読み込むため、**見えていない側の画像と
  1x1 計測gif も毎回リクエストされていた**（Chromium 実測＝PC表示でもSP用が、SP表示でも
  PC用が読み込まれる＝表示回数が実際の約2倍で記録され、クリック率が実態の半分に見える）。
  → 新方式は「選ばれた1つだけを JS で描画する」。表示した分だけが計測される。
  JS 無効の閲覧者には <noscript> で候補の先頭を出す（こちらも1つだけ）。

構成:
  - CREATIVES … 広告素材の唯一の定義。ここから `mw-ads.js` を自動生成する。
  - POOLS     … 記事 -> 候補キーの配列。ランダムはこの中から選ぶ。

使い方:
  python inject_ads.py --dry-run    # 変更内容を確認（書き込まない）
  python inject_ads.py              # 未注入ページへ注入 ＋ mw-ads.js 再生成
  python inject_ads.py --replace    # 既存の広告ブロックも新形式へ貼り替え

新しいアフィリ追加時 = CREATIVES に素材を足し、POOLS の該当記事に候補キーを足して再実行。
"""
import argparse
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
JS_NAME = "mw-ads.js"

AD_CSS = """<style>
.mw-ad{max-width:680px;margin:32px auto;padding:14px 16px 16px;text-align:center;border:1px solid #d0d7de;border-radius:12px;background:#f6f8fa}
.mw-ad .mw-ad-label{display:block;font-size:.66rem;color:#8b949e;letter-spacing:.1em;margin-bottom:8px;text-align:left}
.mw-ad img{max-width:100%;height:auto;vertical-align:middle}
.mw-ad .mw-ad-slot{min-height:60px}
body.dark .mw-ad{background:#161b22;border-color:#30363d}
body.dark .mw-ad .mw-ad-label{color:#6e7681}
</style>"""

# ── 広告素材の唯一の定義（ここを直すと mw-ads.js と <noscript> の両方に反映される）
#    sp は 520px 以下で使う。alt は広告主名＝読み上げソフトで何の広告か分かるように。
CREATIVES = {
    "kabu": {
        "alt": "DMM株",
        "pc": {"href": "https://px.a8.net/svt/ejp?a8mat=4B5R09+7CXWZ6+1WP2+15Q22P",
               "img": "https://www27.a8.net/svt/bgt?aid=260608761445&wid=001&eno=01&mid=s00000008903007008000&mc=1",
               "gif": "https://www15.a8.net/0.gif?a8mat=4B5R09+7CXWZ6+1WP2+15Q22P", "w": 468, "h": 60},
        "sp": {"href": "https://px.a8.net/svt/ejp?a8mat=4B5R09+7CXWZ6+1WP2+15PUCX",
               "img": "https://www26.a8.net/svt/bgt?aid=260608761445&wid=001&eno=01&mid=s00000008903007007000&mc=1",
               "gif": "https://www16.a8.net/0.gif?a8mat=4B5R09+7CXWZ6+1WP2+15PUCX", "w": 320, "h": 50},
    },
    "cfd": {
        "alt": "DMM CFD",
        "pc": {"href": "https://px.a8.net/svt/ejp?a8mat=4B5R09+79YQYA+1WP2+NY1Y9",
               "img": "https://www25.a8.net/svt/bgt?aid=260608761440&wid=001&eno=01&mid=s00000008903004022000&mc=1",
               "gif": "https://www15.a8.net/0.gif?a8mat=4B5R09+79YQYA+1WP2+NY1Y9", "w": 468, "h": 60},
        "sp": {"href": "https://px.a8.net/svt/ejp?a8mat=4B5R09+79YQYA+1WP2+NX735",
               "img": "https://www27.a8.net/svt/bgt?aid=260608761440&wid=001&eno=01&mid=s00000008903004018000&mc=1",
               "gif": "https://www16.a8.net/0.gif?a8mat=4B5R09+79YQYA+1WP2+NX735", "w": 234, "h": 60},
    },
    "fx": {
        "alt": "JFX株式会社",
        "pc": {"href": "https://px.a8.net/svt/ejp?a8mat=4BC736+9U8XPU+25B2+61JSH",
               "img": "https://www23.a8.net/svt/bgt?aid=260909538595&wid=001&eno=01&mid=s00000010019001015000&mc=1",
               "gif": "https://www16.a8.net/0.gif?a8mat=4BC736+9U8XPU+25B2+61JSH", "w": 468, "h": 60},
        "sp": {"href": "https://px.a8.net/svt/ejp?a8mat=4BC736+9U8XPU+25B2+61C2P",
               "img": "https://www21.a8.net/svt/bgt?aid=260909538595&wid=001&eno=01&mid=s00000010019001014000&mc=1",
               "gif": "https://www10.a8.net/0.gif?a8mat=4BC736+9U8XPU+25B2+61C2P", "w": 234, "h": 60},
    },
}

# ── 記事 -> 候補（この中からランダムに1つ）。先頭は JS 無効時に出る既定。
#    2026-09-10 オーナー選択＝「記事に合う複数社からランダム」＝関連性を保ったまま重複を防ぐ。
FX_POOL = ["fx", "cfd"]        # FXが主題 … JFX を軸に、レバレッジ取引つながりで CFD
KABU_POOL = ["kabu", "cfd"]    # 個別株・NISA … DMM株を軸に CFD
IDX_POOL = ["cfd", "kabu"]     # 日経平均など指数 … 指数CFDを軸に株

POOLS = {
    # FXが主題の常設解説記事（2026-09-10 追加）
    "guide-swap-points.html": FX_POOL,
    "guide-leverage.html": FX_POOL,
    "guide-currency-risk.html": FX_POOL,
    "guide-currency-hedge-cost.html": FX_POOL,
    "guide-yen-carry-trade.html": FX_POOL,
    "guide-bid-ask-spread.html": FX_POOL,
    "guide-investment-tax.html": ["fx", "kabu"],   # 株もFXも扱う回
    # 指数・相場観
    "guide-nikkei-60000.html": IDX_POOL,
    "guide-nikkei-60k-break-2026-05-20.html": IDX_POOL,
    "guide-nikkei-65k-break-2026-05-25.html": IDX_POOL,
    "guide-sell-in-may.html": IDX_POOL,
    # 個別株・NISA
    "guide-nisa.html": KABU_POOL,
    "guide-nisa-ranking.html": KABU_POOL,
    "guide-japan-strategy-2026-05.html": KABU_POOL,
    "guide-toyota-2026-05.html": KABU_POOL,
    "guide-softbank-group-2026-05.html": KABU_POOL,
    "guide-bank-stocks-2026-05.html": KABU_POOL,
    "guide-nvidia-2026-05.html": KABU_POOL,
    "guide-tsmc-2026-05.html": KABU_POOL,
    "guide-amd-2026-05.html": KABU_POOL,
    "guide-kioxia-2026-05.html": KABU_POOL,
    "guide-oriental-land-2026-06.html": KABU_POOL,
}

NL_MARKER = "<!-- ===== MarketWatch 無料メルマガ登録"
BEGIN = "<!-- ===== 広告 (A8.net) ===== -->"
END = "<!-- ===== /広告 ===== -->"
# 旧形式（商品名入りのコメント）も拾えるようにしておく＝--replace での移行用
BLOCK_RE = re.compile(r"<!-- ===== 広告 \(A8\.net[^)]*\) ===== -->.*?" + re.escape(END) + r"\n?", re.S)

JS_TEMPLATE = """/* mw-ads.js — 記事末の広告枠に、候補からランダムに1つだけ描画する。
 *
 * 🚨 「1つだけ描く」ことが要点。旧方式は PC/SP 両方を HTML に書いて CSS で隠していたが、
 *    ブラウザは display:none の <img> も読み込むため、見えていない側の 1x1 計測gif まで
 *    毎回飛び、表示回数が実際の約2倍で記録されていた（2026-09-10 Chromium 実測）。
 *
 * ⚠️ このファイルは inject_ads.py が CREATIVES から自動生成する。直接編集しないこと。
 */
(function () {
  var C = %s;
  var SP = "(max-width:520px)";

  function el(tag, attrs) {
    var e = document.createElement(tag);
    for (var k in attrs) { if (attrs[k] !== null) e.setAttribute(k, attrs[k]); }
    return e;
  }

  function render(box) {
    var slot = box.querySelector(".mw-ad-slot");
    if (!slot || slot.getAttribute("data-mw-done")) { return; }
    var keys = (box.getAttribute("data-mw-ads") || "").split(",").filter(function (k) { return C[k]; });
    if (!keys.length) { return; }
    var c = C[keys[Math.floor(Math.random() * keys.length)]];
    var v = (window.matchMedia && window.matchMedia(SP).matches) ? c.sp : c.pc;

    var a = el("a", {href: v.href, rel: "nofollow noopener", target: "_blank"});
    a.appendChild(el("img", {src: v.img, width: v.w, height: v.h, alt: c.alt, border: "0"}));
    slot.appendChild(a);
    slot.appendChild(el("img", {src: v.gif, width: 1, height: 1, alt: "", border: "0"}));
    slot.setAttribute("data-mw-done", "1");
  }

  function run() {
    var boxes = document.querySelectorAll(".mw-ad[data-mw-ads]");
    for (var i = 0; i < boxes.length; i++) { render(boxes[i]); }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", run);
  } else {
    run();
  }
})();
"""


def build_js():
    """CREATIVES から mw-ads.js の中身を作る（唯一の定義から生成＝二重管理しない）。"""
    return JS_TEMPLATE % json.dumps(CREATIVES, ensure_ascii=False, indent=2)


def build_block(keys):
    """記事に差し込む広告枠。JS 無効なら <noscript> で候補の先頭を1つだけ出す。"""
    d = CREATIVES[keys[0]]["pc"]
    alt = CREATIVES[keys[0]]["alt"]
    return (
        BEGIN + "\n"
        '<div class="mw-ad" aria-label="広告" data-mw-ads="' + ",".join(keys) + '">\n'
        '  <span class="mw-ad-label">広告</span>\n'
        '  <div class="mw-ad-slot"></div>\n'
        "  <noscript>\n"
        '    <a href="' + d["href"] + '" rel="nofollow noopener" target="_blank">'
        '<img border="0" width="' + str(d["w"]) + '" height="' + str(d["h"]) + '" alt="' + alt + '" '
        'src="' + d["img"] + '"></a>\n'
        '    <img border="0" width="1" height="1" src="' + d["gif"] + '" alt="">\n'
        "  </noscript>\n"
        "</div>\n"
        + AD_CSS + "\n"
        '<script src="' + JS_NAME + '" defer></script>\n'
        + END + "\n"
    )


def main():
    ap = argparse.ArgumentParser(description="A8広告をランダム表示で記事末に注入（既定＝未注入ページのみ）")
    ap.add_argument("--dry-run", action="store_true", help="書き込まず変更内容だけ表示")
    ap.add_argument("--replace", action="store_true", help="既存の広告ブロックも新形式へ貼り替える")
    args = ap.parse_args()

    # ① mw-ads.js を CREATIVES から再生成
    js_path = os.path.join(HERE, JS_NAME)
    js = build_js()
    old_js = open(js_path, encoding="utf-8").read() if os.path.exists(js_path) else None
    if old_js != js:
        if args.dry_run:
            print(f"  [dry] {JS_NAME} を{'更新' if old_js else '新規作成'}")
        else:
            with open(js_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(js)
            print(f"  OK   {JS_NAME} を{'更新' if old_js else '新規作成'}")

    # ② 各記事へ注入 / 貼り替え
    injected = replaced = already = missing = noanchor = 0
    for name, keys in POOLS.items():
        path = os.path.join(HERE, name)
        if not os.path.exists(path):
            missing += 1
            print(f"  MISS {name}: ファイル無し")
            continue
        unknown = [k for k in keys if k not in CREATIVES]
        if unknown:
            print(f"  WARN {name}: 未知の広告キー {unknown} -> スキップ")
            continue
        with open(path, "r", encoding="utf-8") as f:
            c = f.read()
        block = build_block(keys)
        has_block = BLOCK_RE.search(c) is not None

        if has_block and not args.replace:
            already += 1
            continue
        if has_block:
            new = BLOCK_RE.sub(lambda _m: block, c, count=1)
            if new == c:
                already += 1
                continue
            replaced += 1
            tag = "REPL"
        elif "mw-ad" in c:
            already += 1        # 手置きの広告がある＝触らない
            continue
        elif NL_MARKER in c:
            new = c.replace(NL_MARKER, block + "\n" + NL_MARKER, 1)
            injected += 1
            tag = "OK  "
        elif "<footer" in c:
            new = c.replace("<footer", block + "\n<footer", 1)
            injected += 1
            tag = "OK  "
        else:
            noanchor += 1
            print(f"  WARN {name}: 挿入位置なし -> スキップ")
            continue

        if args.dry_run:
            print(f"  [dry] {','.join(keys):9} -> {name}")
        else:
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(new)
            print(f"  {tag} {','.join(keys):9} -> {name}")

    print("-" * 32)
    head = "DRY-RUN " if args.dry_run else ""
    print(f"{head}injected={injected} / replaced={replaced} / already={already} / "
          f"missing={missing} / no-anchor={noanchor}")


if __name__ == "__main__":
    main()
