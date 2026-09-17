# 一時ファイル: 日銀の年間日程／BEA公表日／ECB決定日を一次情報で確かめる。確認後に削除する。
import re, urllib.request
UA = "Mozilla/5.0 (compatible; marketwatch-jp probe; +https://marketwatch-jp.com/)"
SRC = [
    ("日銀 決定会合の日程", "https://www.boj.or.jp/mopo/mpmsche_minu/index.htm", 200),
    ("BEA 公表予定", "https://www.bea.gov/news/schedule", 220),
    ("ECB 政策決定（年別）", "https://www.ecb.europa.eu/press/govcdec/mopo/2026/html/index.en.html", 60),
]
def plain(h):
    h = re.sub(r"(?is)<(script|style).*?</\1>", " ", h)
    h = re.sub(r"(?i)<br\s*/?>|</t[dh]>|</tr>|</li>|</p>|</h[1-6]>|</div>|</a>", "\n", h)
    h = re.sub(r"<[^>]+>", " ", h).replace("&nbsp;", " ").replace("&amp;", "&")
    return [re.sub(r"[ \t]+", " ", l).strip() for l in h.splitlines() if l.strip()]
for name, url, n in SRC:
    print(f"\n{'='*70}\n■ {name}\n  {url}\n{'='*70}")
    try:
        raw = urllib.request.urlopen(
            urllib.request.Request(url, headers={"User-Agent": UA}), timeout=40).read().decode("utf-8", "replace")
    except Exception as e:
        print(f"   ❌ {type(e).__name__}: {str(e)[:120]}"); continue
    lines = plain(raw)
    # ナビを飛ばして中身から出す（本文は後半にある）
    start = 0
    for i, l in enumerate(lines):
        if re.search(r"(?i)決定会合の日程|Release Schedule|Monetary policy decisions", l) and i > 5:
            start = i; break
    print(f"   --- 全 {len(lines)} 行中 {start} 行目から {n} 行 ---")
    for l in lines[start:start + n]:
        print(f"      {l[:150]}")
