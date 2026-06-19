# -*- coding: utf-8 -*-
"""薄い自動テンプレ/日付つきページに noindex メタを冪等に付与する（2026-06-19・AdSense低価値対策）。

対象 = is_noindex_slug() が True の guide-*.html（週次/週次振り返り/月次/日付フラッシュ）。
  ※ preview.html と guide-auto-* は generate_market_news.py が seo_head 経由で noindex 化するので対象外。
robots.txt はオープンのまま（クロール許可しないと Google が noindex を読めず既存索引が消えないため）。
"""
import re, os
from generate_market_news import is_noindex_slug

HERE = os.path.dirname(os.path.abspath(__file__))
META = '  <meta name="robots" content="noindex,follow">'

targets = [f for f in os.listdir(HERE)
           if f.endswith(".html") and is_noindex_slug(f)
           and f != "preview.html" and not f.startswith("guide-auto-")]

patched, already, skipped = [], [], []
for fn in sorted(targets):
    p = os.path.join(HERE, fn)
    s = open(p, encoding="utf-8-sig").read()
    if re.search(r'<meta\s+name="robots"\s+content="noindex', s):
        already.append(fn); continue
    if re.search(r'<meta\s+name="robots"[^>]*>', s):
        s = re.sub(r'<meta\s+name="robots"[^>]*>', '<meta name="robots" content="noindex,follow">', s, count=1)
    elif re.search(r'<meta\s+name="viewport"[^>]*>', s):
        s = re.sub(r'(<meta\s+name="viewport"[^>]*>)', r'\1\n' + META, s, count=1)
    elif re.search(r'<meta\s+charset[^>]*>', s):
        s = re.sub(r'(<meta\s+charset[^>]*>)', r'\1\n' + META, s, count=1)
    else:
        skipped.append(fn); continue
    open(p, "w", encoding="utf-8", newline="\n").write(s)
    patched.append(fn)

print(f"対象 {len(targets)} 本 / patched {len(patched)} / already {len(already)} / skipped {len(skipped)}")
if patched: print("  patched:", ", ".join(patched))
if already: print("  already noindex:", ", ".join(already))
if skipped: print("  ⚠️ skipped(headアンカー無し):", ", ".join(skipped))
