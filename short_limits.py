# -*- coding: utf-8 -*-
"""J40 売り禁・規制はどれくらいかかるか：J31F の売りの対象に、その朝かかっていた規制を前向きで記録する（読むだけ）。
2026-10-08 登録・オーナー「両方登録して進めてください」。PILLAR_PREREG.md「J40」。

いまは --probe だけ＝日本証券金融（売り禁・注意喚起）と日本取引所グループ（増担保規制）の公表資料の場所と形を調べる
（資料の場所・リンクの文字・表の見出しと件数だけ。損益は数えない・何も書き出さない）。読み方を PREREG「J40」の追記に
書いてから、毎朝の記録の道具をここに足す。日々公表銘柄はすでに毎日取っている jp-margin.json を使う。

⚠️ probe の表示は見出しと件数だけ（銘柄コードは伏せる・銘柄名の列は件数だけ）。
⚠️ 出力（short-limits.json / .md）は GitHub 側で生成＝手元から送らない（SYNC禁忌）。銘柄は J31F と同じ伏せた印で持つ。

実行: python short_limits.py --probe   （Actions の short-limits.yml から手動で）
"""
import io
import re
import sys

import jp_taishaku as JT

SITES = (("日本取引所グループ（信用取引の規制＝増担保など）", "https://www.jpx.co.jp/markets/equities/margin-reg/index.html"),
         ("日本取引所グループ（日々公表）", "https://www.jpx.co.jp/markets/equities/margin-daily/index.html"),
         ("日本取引所グループ（注意喚起）", "https://www.jpx.co.jp/markets/equities/alerts/index.html"),
         ("日本証券金融（貸借取引銘柄別制限措置等一覧）", "https://www.taisyaku.jp/restrictive.php"))   # 10/8 1回目の probe で見つけた（いちばん大事＝記録の最後に出す）
KEYWORDS = re.compile(r"申込停止|停止措置|制限措置|注意喚起|増担保|規制|日々公表|品貸|貸借取引|逆日歩")
A_RE = re.compile(r'<a\s[^>]*href="([^"#]+)"[^>]*>(.*?)</a>', re.I | re.S)
FILE_EXT = re.compile(r"\.(csv|xlsx?|pdf|zip|txt)(\?|$)", re.I)
MAX_PAGES = 2                 # 1つの入口から見るページの数（入口ともう1ページ）


def links(html, base):
    """ページの HTML → [(絶対 URL, リンクの文字)]（同じ URL は1回）。純関数"""
    root = re.match(r"https?://[^/]+", base).group(0)
    out, seen = [], set()
    for href, text in A_RE.findall(html):
        href = href.strip()
        if href.startswith(("mailto:", "javascript:")):
            continue
        url = href if href.startswith("http") else root + href if href.startswith("/") else base.rsplit("/", 1)[0] + "/" + href
        if url in seen:
            continue
        seen.add(url)
        out.append((url, re.sub(r"<[^>]+>|\s+", " ", text).strip()))
    return out


def keyword_links(pairs):
    """リンクの文字か URL に規制の言葉があるもの。純関数"""
    return [(u, t) for u, t in pairs if KEYWORDS.search(t) or KEYWORDS.search(u)]


def decode(raw):
    for enc in ("utf-8", "cp932"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


DATE_RE = re.compile(r"^\d{4}[/\-年.]\d{1,2}[/\-月.]\d{1,2}日?$")


def mask(v):
    s = str(v).strip().strip('"').strip()
    return "（コード）" if JT.CODE_RE.match(s) or re.fullmatch(r"\d{4}0?", s) else s[:14]


def mask_row(cells):
    """データの行：コードは伏せ、日付・数字・規制の言葉だけ残し、ほか（銘柄名など）は「…」。見出しの行（コードが無い行）はそのまま"""
    m = [mask(c) for c in cells]
    if "（コード）" not in m:
        return m
    return [c if c == "（コード）" or DATE_RE.match(c) or re.fullmatch(r"[\d.,%％\-]+", c) or KEYWORDS.search(c) or c in ("", "nan") else "…"
            for c in m]


def html_tables(html):
    """ページの表 → [(行数, 見出しの行, 2行目)]（コードは伏せる・2行目は先頭の4つだけ）。純関数"""
    out = []
    for t in re.findall(r"<table.*?</table>", html, re.S | re.I):
        rows = re.findall(r"<tr.*?</tr>", t, re.S | re.I)
        cells = [mask_row([re.sub(r"<[^>]+>|\s+", " ", c).strip() for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", r, re.S | re.I)])
                 for r in rows[:3]]
        out.append((len(rows), cells[0][:10] if cells else [], cells[1][:8] if len(cells) > 1 else []))
    return out


def show_table(url, raw):
    """表の形だけ（先頭3行の見出し・行数・列ごとの値の種類の数）"""
    import pandas as pd
    if re.search(r"\.csv", url, re.I):
        text = decode(raw)
        lines = text.splitlines()
        print(f"    CSV {len(lines)}行")
        for i, line in enumerate(lines[:3]):
            print(f"    {i}行目：{mask_row(line.split(','))[:12]}")
        return
    sheets = pd.read_excel(io.BytesIO(raw), sheet_name=None, dtype=str, header=None)
    for name, df in sheets.items():
        print(f"    表「{name}」：{df.shape[0]}行×{df.shape[1]}列")
        for i in range(min(3, len(df))):
            print(f"    {i}行目：{mask_row(df.iloc[i].tolist())[:12]}")


def probe(get=JT.http):
    for site, top in SITES:
        print(f"\n=== {site}：{top}", flush=True)
        seen_pages = 0
        queue = [(top, "（入口）")]
        visited = set()
        while queue and seen_pages < MAX_PAGES:
            url, why = queue.pop(0)
            if url in visited:
                continue
            visited.add(url)
            seen_pages += 1
            try:
                html = decode(get(url))
            except Exception as e:  # noqa: BLE001
                print(f"  ✕ 取れない {url}（{why}）：{type(e).__name__}: {str(e)[:100]}")
                continue
            title = re.search(r"<title>(.*?)</title>", html, re.S)
            hits = keyword_links(links(html, url))
            print(f"  ▼ {url}（{why}）「{(title.group(1).strip() if title else '')[:40]}」規制の言葉のリンク {len(hits)}件")
            for n, head, second in html_tables(html)[:8]:
                print(f"    表：{n}行・見出し {head}・2行目 {second}")
            files = [(u, t) for u, t in links(html, url) if FILE_EXT.search(u)]
            if files:
                print(f"    資料のリンク {len(files)}件：" + "／".join(f"{t[:20]}→{u.rsplit('/', 1)[-1]}" for u, t in files[:8]))
            for u, t in hits[:30]:
                print(f"    - {t[:50]} → {u}")
            for u, t in hits:
                if FILE_EXT.search(u):
                    continue
                if u.startswith(re.match(r"https?://[^/]+", top).group(0)) and u not in visited and len(queue) < 6 and url == top:
                    queue.append((u, t[:30]))
            for u, t in [h for h in links(html, url) if re.search(r"\.(csv|xlsx?)(\?|$)", h[0], re.I)][:2]:
                try:
                    show_table(u, get(u))
                except Exception as e:  # noqa: BLE001
                    print(f"    ✕ 読めない {u}：{type(e).__name__}: {str(e)[:100]}")
    print("\nprobe だけ（損益は数えていない・何も書き出していない）。読み方は PREREG「J40」の追記に書いてから記録の道具を足す")
    return 0


def main(argv):
    if "--probe" in argv:
        return probe()
    print("いまは --probe だけ（記録の道具は PREREG「J40」の追記のあとに足す）")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
