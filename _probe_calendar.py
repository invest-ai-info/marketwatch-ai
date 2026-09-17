# 一時ファイル: 過去分の日付食い違い4件を一次情報で確かめるための調査用。確認後に削除する。
import re, urllib.request
UA = "Mozilla/5.0 (compatible; marketwatch-jp probe; +https://marketwatch-jp.com/)"
SRC = [
    ("ECB 2026 報道発表一覧", "https://www.ecb.europa.eu/press/pr/date/2026/html/index.en.html"),
    ("日銀 金融政策決定会合の日程", "https://www.boj.or.jp/mopo/mpmsche_minu/index.htm"),
    ("BEA 公表予定", "https://www.bea.gov/news/schedule"),
]
def plain(h):
    h = re.sub(r"(?is)<(script|style).*?</\1>", " ", h)
    h = re.sub(r"(?i)<br\s*/?>|</t[dh]>|</tr>|</li>|</p>|</h[1-6]>|</div>", "\n", h)
    h = re.sub(r"<[^>]+>", " ", h).replace("&nbsp;", " ").replace("&amp;", "&")
    return "\n".join(re.sub(r"[ \t]+", " ", l).strip() for l in h.splitlines() if l.strip())
for name, url in SRC:
    print(f"\n{'='*70}\n■ {name}: {url}\n{'='*70}")
    try:
        raw = urllib.request.urlopen(
            urllib.request.Request(url, headers={"User-Agent": UA}), timeout=40).read().decode("utf-8", "replace")
    except Exception as e:
        print(f"   ❌ {type(e).__name__}: {str(e)[:120]}"); continue
    if "ecb.europa.eu" in url:
        print("   --- 金融政策決定の press release URL（ecb.mpYYMMDD）---")
        for m in sorted(set(re.findall(r"ecb\.mp(\d{6})", raw))):
            print(f"      20{m[:2]}-{m[2:4]}-{m[4:6]}")
    t = plain(raw)
    keys = ("2026", "GDP", "決定会合", "金融政策")
    hits = [l for l in t.splitlines() if any(k in l for k in keys)]
    print(f"   --- 手がかり行 {len(hits)} 本（先頭45本）---")
    for l in hits[:45]:
        print(f"      {l[:165]}")
