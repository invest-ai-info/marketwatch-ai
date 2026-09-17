# 一時ファイル: 過去分の日付食い違い4件を一次情報で確かめる。確認後に削除する。
import re, urllib.request
UA = "Mozilla/5.0 (compatible; marketwatch-jp probe; +https://marketwatch-jp.com/)"
SRC = [
    ("日銀 2026年の決定内容一覧", "https://www.boj.or.jp/mopo/mpmdeci/mpr_2026/index.htm", r"6月|2026"),
    ("ECB 金融政策声明 2026", "https://www.ecb.europa.eu/press/press_conference/monetary-policy-statement/2026/html/index.en.html", r"June|2026"),
    ("BEA 公表予定", "https://www.bea.gov/news/schedule", None),
]
def plain(h):
    h = re.sub(r"(?is)<(script|style).*?</\1>", " ", h)
    h = re.sub(r"(?i)<br\s*/?>|</t[dh]>|</tr>|</li>|</p>|</h[1-6]>|</div>|</a>", "\n", h)
    h = re.sub(r"<[^>]+>", " ", h).replace("&nbsp;", " ").replace("&amp;", "&")
    return "\n".join(re.sub(r"[ \t]+", " ", l).strip() for l in h.splitlines() if l.strip())
for name, url, pat in SRC:
    print(f"\n{'='*70}\n■ {name}\n  {url}\n{'='*70}")
    try:
        raw = urllib.request.urlopen(
            urllib.request.Request(url, headers={"User-Agent": UA}), timeout=40).read().decode("utf-8", "replace")
    except Exception as e:
        print(f"   ❌ {type(e).__name__}: {str(e)[:120]}"); continue
    # 日付らしき文字列を含むリンク先も拾う（YYMMDD が URL に入る運用が多い）
    for m in sorted(set(re.findall(r"(?:k|ecb\.mp|gdp)(\d{6})", raw)))[:40]:
        print(f"   [URL内の日付] 20{m[:2]}-{m[2:4]}-{m[4:6]}")
    lines = plain(raw).splitlines()
    sel = [l for l in lines if (re.search(pat, l) if pat else True)]
    print(f"   --- 本文 {len(sel)} 行（先頭50本）---")
    for l in sel[:50]:
        print(f"      {l[:160]}")
