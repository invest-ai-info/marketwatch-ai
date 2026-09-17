# 一時ファイル: 残りの過去分（ECB 6月・米GDP 5月/6月）と日銀の年間日程を取りに行く。確認後に削除。
import gzip, io, re, urllib.request
UA = "Mozilla/5.0 (compatible; marketwatch-jp probe; +https://marketwatch-jp.com/)"
def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "identity"})
    r = urllib.request.urlopen(req, timeout=40)
    b = r.read()
    if r.headers.get("Content-Encoding") == "gzip" or b[:2] == b"\x1f\x8b":
        b = gzip.decompress(b)
    return b.decode("utf-8", "replace")
def plain(h):
    h = re.sub(r"(?is)<(script|style).*?</\1>", " ", h)
    h = re.sub(r"(?i)<br\s*/?>|</t[dh]>|</tr>|</li>|</p>|</h[1-6]>|</div>|</a>", "\n", h)
    h = re.sub(r"<[^>]+>", " ", h).replace("&nbsp;", " ").replace("&amp;", "&")
    return [re.sub(r"[ \t]+", " ", l).strip() for l in h.splitlines() if l.strip()]

print("="*70, "\n■ 日銀 決定会合の日程（本文は後半にある）")
try:
    L = plain(get("https://www.boj.or.jp/mopo/mpmsche_minu/index.htm"))
    for l in L[200:393]:
        print(f"   {l[:150]}")
except Exception as e: print("   ❌", type(e).__name__, str(e)[:120])

print("\n" + "="*70, "\n■ BEA 機械可読スケジュール（JSONリンクを探す）")
try:
    raw = get("https://www.bea.gov/news/schedule")
    for u in sorted(set(re.findall(r'href="([^"]*(?:json|ics|schedule)[^"]*)"', raw, re.I)))[:20]:
        print("   link:", u[:140])
except Exception as e: print("   ❌", type(e).__name__, str(e)[:120])

print("\n" + "="*70, "\n■ ECB 記者会見／声明の一覧（過去分の決定日を拾う）")
for u in ["https://www.ecb.europa.eu/press/press_conference/html/index.en.html",
          "https://www.ecb.europa.eu/press/press_conference/monetary-policy-statement/html/index.en.html"]:
    print("  ", u)
    try:
        raw = get(u)
        ds = sorted(set(re.findall(r"ecb\.(?:mp|is)(\d{6})", raw)))
        print("     URL内の日付:", ", ".join(f"20{d[:2]}-{d[2:4]}-{d[4:6]}" for d in ds) or "なし")
    except Exception as e: print("     ❌", type(e).__name__, str(e)[:120])
