# -*- coding: utf-8 -*-
"""
apply_disclaimer.py — 免責の三層（上部バナー／本文末／フッター）を冪等に揃える。

🔑 判定は**クラス名ではなく位置**で行う。
   このサイトは時期とレーンで免責のマークアップが違う（disclaimer-banner / kinsho /
   class無しの <p data-disclaimer> など）。クラス名で見ると「あるのに無い」と誤判定し、
   二重に足してしまう。位置（記事の先頭／記事の末尾／footer内）で数えるのが唯一の安全な方法。

三層の定義:
  A 上部バナー … <article> 開始 〜 最初の <h1> の間
  B 本文末     … <article> 内で、A より後ろ（h1 以降〜 </article>）
  C フッター   … <footer> 〜 </footer> の中

⚠️ 既存の文面は書き換えない。**足りない層を足すだけ**。
⚠️ drafts/ 配下は対象外（noindex の下書き）。
"""
import argparse, glob, io, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
KEY = 'data-disclaimer="kinsho-v1"'

BANNER = ('    <div class="disclaimer-banner" data-disclaimer="kinsho-v1">\n'
          '      ⚠️ 本記事は情報提供のみを目的としており、投資助言・特定金融商品の売買推奨・投資勧誘を'
          '構成するものではありません。掲載内容は公開情報にもとづく参考解説であり、将来の価格や成果を'
          '予測・保証するものではありません。<strong>投資の判断はご自身の責任でお願いいたします。</strong>\n'
          '    </div>\n\n')

BODY = ('    <div class="disclaimer" data-disclaimer="kinsho-v1">\n'
        '      <strong>【免責事項】</strong><br>\n'
        '      本記事は情報提供を目的として作成されており、金融商品取引法に基づく投資助言・投資勧誘・'
        '特定金融商品の売買推奨を行うものではありません。掲載されている情報は公開情報・一次情報をもとにした'
        '参考解説であり、その正確性・完全性を保証するものではありません。将来の株価・金利・為替・資産価格の'
        '方向性についていかなる保証も行いません。<strong>投資の判断および運用は、かならずご自身の責任と'
        '判断において行ってください。</strong>必要に応じて専門家（証券会社・ファイナンシャルプランナー等）'
        'へのご相談をお勧めします。\n'
        '    </div>\n\n')

FOOTER = ('  <div class="footer-disclaimer" data-disclaimer="kinsho-v1">'
          '本サイトの情報は投資助言・売買推奨ではありません。投資判断はご自身の責任でお願いします。</div>\n')


def spans(html):
    """記事とフッターの範囲を返す。

    ⚠️ 本文のコンテナは <article> と <main> の2通りある（時期によって違う）。
       <article> が無いページを「足せない」と切り捨てると45本が取り残されるので、
       無ければ <main> を本文のコンテナとして扱う。
    """
    a = html.find("<article")
    ae = html.find("</article>")
    if a < 0 or ae < 0:                      # <article> が無いページ
        a, ae = html.find("<main"), html.find("</main>")
    h1 = html.find("<h1", a) if a >= 0 else -1
    f = html.find("<footer")
    fe = html.find("</footer>")
    return a, h1, ae, f, fe


def layers(html):
    """位置で三層の有無を判定する。"""
    a, h1, ae, f, fe = spans(html)
    got = {"A": False, "B": False, "C": False}
    for m in re.finditer(re.escape(KEY), html):
        i = m.start()
        if a >= 0 and h1 > a and a < i < h1:
            got["A"] = True
        elif a >= 0 and ae > a and a < i < ae:
            got["B"] = True
        elif f >= 0 and fe > f and f < i < fe:
            got["C"] = True
    return got


def fix(html):
    """足りない層だけを足す。足せない場合は None を返す。"""
    got = layers(html)
    if all(got.values()):
        return None, got
    a, h1, ae, f, fe = spans(html)
    out = html
    # 後ろから入れる（前を入れると以降の位置がずれる）
    if not got["C"] and f >= 0 and fe > f:
        # 🔑 footer に既に免責の文があるなら、**新しい文を足さず既存の要素に目印だけ付ける**。
        #    足すと読者には同じ趣旨の文が2つ並んで見える（2026-09-22 実測で40本が該当）。
        foot = out[f:fe]
        cand = None
        for m in re.finditer(r"<(p|div|span)(?![^>]*data-disclaimer)([^>]*)>(.*?)</\1>", foot, re.S):
            txt = re.sub(r"<[^>]+>", "", m.group(3))
            if "投資助言" in txt or "投資判断" in txt:
                cand = m
                break
        if cand:
            ins = f + cand.start() + 1 + len(cand.group(1))
            out = out[:ins] + ' data-disclaimer="kinsho-v1"' + out[ins:]
        else:
            out = out[:fe] + FOOTER + out[fe:]
    if not got["B"] and ae >= 0:
        close = "</article>" if "</article>" in out else "</main>"
        ae2 = out.find(close)
        ls = out.rfind("\n", 0, ae2) + 1       # 閉じタグの行頭に揃えて差し込む
        out = out[:ls] + BODY + out[ls:]
    if not got["A"] and a >= 0 and h1 > a:
        # 🔑 本文コンテナ（<article> か <main>）の**開きタグ直後**に入れる。
        #    h1 の行頭に入れる方式だと、<main>\n\n<h1> のように両者が密着している形で
        #    挿入位置が判定範囲の境界に乗り、次回実行時に「A が無い」と読まれて二重に足す
        #    （2026-09-22 実測: signal-lab 2本で冪等性が崩れた）。
        tag = "<article" if "<article" in out else "<main"
        op = out.find(tag)
        gt = out.find(">", op)
        out = out[:gt + 1] + "\n" + BANNER + out[gt + 1:]
    return (out if out != html else None), got


def main():
    ap = argparse.ArgumentParser(description="免責の三層を冪等に揃える（位置で判定・既存文面は書き換えない）")
    ap.add_argument("--apply", action="store_true", help="実際に書き込む（既定は dry-run）")
    ap.add_argument("--glob", default="guide-*.html", help="対象のglob（既定: guide-*.html）")
    args = ap.parse_args()

    ok = fixed = skipped = 0
    miss = {"A": 0, "B": 0, "C": 0}
    for p in sorted(glob.glob(os.path.join(HERE, args.glob))):
        name = os.path.basename(p)
        html = io.open(p, encoding="utf-8").read()
        new, got = fix(html)
        if new is None:
            if all(got.values()):
                ok += 1
            else:
                skipped += 1
                print(f"  SKIP {name}: 足せない（article/footer が見つからない）got={got}")
            continue
        for k in miss:
            if not got[k]:
                miss[k] += 1
        fixed += 1
        if args.apply:
            io.open(p, "w", encoding="utf-8", newline="\n").write(new)
            print(f"  OK   {name}: 追加={[k for k in 'ABC' if not got[k]]}")
        else:
            print(f"  [dry] {name}: 追加={[k for k in 'ABC' if not got[k]]}")

    print("-" * 40)
    head = "DRY-RUN " if not args.apply else ""
    print(f"{head}三層OK={ok} / 補った={fixed} / スキップ={skipped}")
    print(f"  補った内訳: 上部バナー={miss['A']} 本文末={miss['B']} フッター={miss['C']}")


if __name__ == "__main__":
    main()
