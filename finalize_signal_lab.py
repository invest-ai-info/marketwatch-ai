# -*- coding: utf-8 -*-
"""
finalize_signal_lab.py — drafts/draft-signal-lab-NNN.html(簡素head・noindex付き) を
公開用 guide-signal-lab-NNN.html に仕上げる（任意の号に対応）。

  python finalize_signal_lab.py 004 2026-06-13

やること:
  - 下書きの <title>/<meta description>/<meta keywords> をそのまま流用し、
    #3公開版と同じフルhead(canonical/OGP/JSON-LD/GA G-FMVFEV7Q2E/AdSense ca-pub-2552122294306014)を構築
  - noindex,nofollow を除去（検索許可）
  - meta-line「公開：YYYY年M月（下書き中）」→「公開：YYYY年M月D日」
  - <style> 以降（CSS+本文）は下書きのまま保持
出力: guide-signal-lab-NNN.html
"""
import os, re, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
GA_ID = "G-FMVFEV7Q2E"
ADSENSE = "ca-pub-2552122294306014"
OG_IMAGE = "https://marketwatch-jp.com/08_market_stock.png"


def _meta(html, name, prop=False):
    attr = "property" if prop else "name"
    m = re.search(rf'<meta {attr}="{re.escape(name)}" content="(.*?)">', html, re.S)
    return m.group(1) if m else ""


def main():
    if len(sys.argv) < 3:
        print("usage: python finalize_signal_lab.py <NNN> <YYYY-MM-DD>")
        sys.exit(2)
    nnn, date = sys.argv[1], sys.argv[2]
    m = re.match(r'^(\d{4})-(\d{2})-(\d{2})$', date)
    if not m:
        print(f"❌ 日付不正: {date}")
        sys.exit(2)
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))

    src = os.path.join(ROOT, "drafts", f"draft-signal-lab-{nnn}.html")
    dst = os.path.join(ROOT, f"guide-signal-lab-{nnn}.html")
    if not os.path.exists(src):
        print(f"❌ 下書きが見つからない: {src}")
        sys.exit(1)
    with open(src, encoding="utf-8-sig") as f:
        c = f.read()
    orig = c

    title = re.search(r'<title>(.*?)</title>', c, re.S)
    title = title.group(1).strip() if title else f"AIシグナル研究日誌 #{int(nnn)} - MarketWatch AI"
    desc = _meta(c, "description")
    keywords = _meta(c, "keywords")
    og_title = re.sub(r'\s*-\s*MarketWatch AI\s*$', '', title)
    og_desc = (desc[:110]).strip()
    slug = f"guide-signal-lab-{nnn}.html"

    new_head = f'''<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <meta name="description" content="{desc}">
  <meta name="keywords" content="{keywords}">
  <link rel="canonical" href="https://marketwatch-jp.com/{slug}">
  <meta property="og:type" content="article">
  <meta property="og:title" content="{og_title}">
  <meta property="og:description" content="{og_desc}">
  <meta property="og:url" content="https://marketwatch-jp.com/{slug}">
  <meta property="og:site_name" content="MarketWatch AI">
  <meta property="og:locale" content="ja_JP">
  <meta property="og:image" content="{OG_IMAGE}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:image" content="{OG_IMAGE}">
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "Article",
    "headline": "{og_title}",
    "description": "{og_desc}",
    "author": {{"@type": "Organization", "name": "MarketWatch AI"}},
    "publisher": {{"@type": "Organization", "name": "MarketWatch AI"}},
    "datePublished": "{date}",
    "dateModified": "{date}",
    "mainEntityOfPage": "https://marketwatch-jp.com/{slug}"
  }}
  </script>
  <script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){{dataLayer.push(arguments);}}
    gtag('js', new Date());
    gtag('config', '{GA_ID}');
  </script>
  <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ADSENSE}" crossorigin="anonymous"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;600;700&display=swap" rel="stylesheet">

'''

    if "  <style>" not in c:
        print("❌ <style> が見つからない（下書き構造異常）")
        sys.exit(1)
    idx = c.index("  <style>")
    c = new_head + c[idx:]

    # meta-line 公開形式化（「（下書き中）」を実日付に）
    n_meta = len(re.findall(r'公開：\d{4}年\d{1,2}月（下書き中）', c))
    c = re.sub(r'公開：\d{4}年\d{1,2}月（下書き中）', f'公開：{y}年{mo}月{d}日', c)

    if "noindex" in c:
        print("❌ noindex が残存（除去失敗）")
        sys.exit(1)
    for need in ('rel="canonical"', "application/ld+json", GA_ID, ADSENSE):
        if need not in c:
            print(f"❌ head要素欠落: {need}")
            sys.exit(1)
    if c.count("kinsho-v1") < 3:
        print(f"❌ 免責kinsho-v1が3未満: {c.count('kinsho-v1')}")
        sys.exit(1)

    with open(dst, "w", encoding="utf-8", newline="\n") as f:
        f.write(c)
    print(f"✅ {dst}  (meta_line_fixed={n_meta}, svg={c.count('<svg ')}, kinsho={c.count('kinsho-v1')}, size={len(c)//1024}KB)")
    sys.exit(0)


if __name__ == "__main__":
    main()
