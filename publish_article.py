# -*- coding: utf-8 -*-
"""
publish_article.py — 解説記事公開の機械化（CLAUDE.md 8ステップの ②〜⑤ を1コマンドに集約）
================================================================================
すでに書き上げた guide-*.html を渡すと、以下を「冪等に」自動実行する:
  ② guides.html に記事カードを追加（該当カテゴリの最上段）
  ④ sync_to_github.py の SYNC_FILES に追加
  ⑤ generate_market_news.py の更新履歴(_history_items)に追加
  （③ sitemap.xml は generate_market_news.py が全guideを自動収集・再生成するため手動追加は不要になった）
     （※日付の降順ソート・最新5件キープは描画側 build_html が自動で行う）

対象外（人/別手順）:
  ① 記事HTMLの作成（執筆。content-writer + compliance-reviewer を通す）
  ⑥ python sync_to_github.py（push）
  ⑦ GitHub Actions「Update Market News」を Run workflow
  ⑧ ライブ確認

特徴:
  - 冪等: すでに追加済みの項目は「スキップ」と表示し二重化しない（再実行しても安全）
  - --dry-run: 何も書き込まず、行う変更だけ表示
  - 日付・読了分は記事HTML（datePublished / 「読了時間：約N分」）から自動抽出

使い方:
  python publish_article.py --file guide-oriental-land-2026-06.html \
      --category 個別銘柄解説 --emoji 🏰 \
      --card-title "オリエンタルランド（4661）はなぜ約6割安に？ 暴落の5つの理由と「復活」3シナリオを整理" \
      --desc "かつてPER90倍超の優良成長株が高値から約6割安に。下落の5要因と復活3シナリオを整理。"
"""
import os
import re
import sys
import argparse

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def _read(p):
    with open(os.path.join(SCRIPT_DIR, p), encoding="utf-8") as f:
        return f.read()


def _write(p, s):
    with open(os.path.join(SCRIPT_DIR, p), "w", encoding="utf-8") as f:
        f.write(s)


def _jp_date(d):
    y, mo, da = d.split("-")
    return f"{int(y)}年{int(mo)}月{int(da)}日"


def extract_from_html(html):
    """記事HTMLから date(datePublished) と readmin(読了時間 約N分) を抽出。無ければ None。"""
    date = None
    m = re.search(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})"', html)
    if m:
        date = m.group(1)
    readmin = None
    m = re.search(r'読了時間\s*[：:]\s*約\s*(\d+)\s*分', html)
    if m:
        readmin = m.group(1)
    return date, readmin


def add_to_guides(file, category, emoji, card_title, desc, date, readmin, badge, dry):
    g = _read("guides.html")
    if f'href="{file}"' in g:
        print("  ⏭️  guides.html: 既にカードあり、スキップ")
        return False
    card = (
        f'      <a class="article-card" href="{file}">\n'
        f'        <span class="article-badge {badge}">{category}</span>\n'
        f'        <div class="article-title">{emoji} {card_title}</div>\n'
        f'        <div class="article-desc">{desc}</div>\n'
        f'        <div class="article-meta">\n'
        f'          <time datetime="{date}">{_jp_date(date)}</time>\n'
        f'          <span>読了 約{readmin}分</span>\n'
        f'        </div>\n'
        f'      </a>\n'
    )
    # 該当カテゴリの最初のカードの「前」に挿入（＝そのカテゴリの最上段＝最新）
    pat = re.compile(
        r'      <a class="article-card" href="[^"]+">\s*\n\s*'
        r'<span class="article-badge [^"]*">' + re.escape(category) + r'</span>'
    )
    m = pat.search(g)
    if m:
        g2 = g[:m.start()] + card + g[m.start():]
        print(f"  ✅ guides.html: カード追加（カテゴリ「{category}」の最上段）")
    else:
        m2 = re.search(r'      <a class="article-card" href="', g)
        if not m2:
            print("  ⚠️ guides.html: 挿入位置が見つからない、スキップ")
            return False
        g2 = g[:m2.start()] + card + g[m2.start():]
        print(f"  ℹ️ guides.html: カテゴリ「{category}」が無いため記事一覧の最上段に挿入")
    if not dry:
        _write("guides.html", g2)
    return True


def add_to_sitemap(file, date, dry):
    s = _read("sitemap.xml")
    loc = f"https://marketwatch-jp.com/{file}"
    if loc in s:
        print("  ⏭️  sitemap.xml: 既にあり、スキップ")
        return False
    if "</urlset>" not in s:
        print("  ⚠️ sitemap.xml: </urlset> が無い、スキップ")
        return False
    block = (
        f"  <url>\n"
        f"    <loc>{loc}</loc>\n"
        f"    <lastmod>{date}T12:00:00+09:00</lastmod>\n"
        f"    <changefreq>monthly</changefreq>\n"
        f"    <priority>0.9</priority>\n"
        f"  </url>\n"
    )
    s2 = s.replace("</urlset>", block + "</urlset>", 1)
    print("  ✅ sitemap.xml: <url> 追加")
    if not dry:
        _write("sitemap.xml", s2)
    return True


def add_to_sync(file, dry):
    s = _read("sync_to_github.py")
    if f'"{file}"' in s:
        print("  ⏭️  sync_to_github.py: 既に SYNC_FILES にあり、スキップ")
        return False
    lines = s.split("\n")
    idx = None
    for i, ln in enumerate(lines):
        if re.match(r'\s*"guide-[^"]*\.html",', ln):
            idx = i  # 最後の guide-*.html 行を覚える
    if idx is None:
        print("  ⚠️ sync_to_github.py: SYNC_FILES の挿入位置が見つからない、スキップ")
        return False
    indent = re.match(r'(\s*)', lines[idx]).group(1)
    lines.insert(idx + 1, f'{indent}"{file}",')
    print("  ✅ sync_to_github.py: SYNC_FILES に追加")
    if not dry:
        _write("sync_to_github.py", "\n".join(lines))
    return True


def add_to_history(file, emoji, card_title, date, dry):
    g = _read("generate_market_news.py")
    anchor = "    _history_items = [\n"
    pos = g.find(anchor)
    if pos == -1:
        print("  ⚠️ generate_market_news.py: _history_items が見つからない、スキップ")
        return False
    region_end = g.find("]", pos)
    region = g[pos:region_end]
    if f'href="{file}"' in region:
        print("  ⏭️  generate_market_news.py: 既に更新履歴にあり、スキップ")
        return False
    item = (
        f'        {{"date": "{date}", "line": \'・<b>{date}</b>: {emoji} '
        f'解説「<a href="{file}" style="color:#0969da"><b>{card_title}</b></a>」公開\'}},\n'
    )
    insert_at = pos + len(anchor)
    g2 = g[:insert_at] + item + g[insert_at:]
    print("  ✅ generate_market_news.py: 更新履歴に追加（並べ替え・最新5件キープは描画側が自動）")
    if not dry:
        _write("generate_market_news.py", g2)
    return True


def main():
    ap = argparse.ArgumentParser(description="解説記事公開の機械化（8ステップ ②〜⑤）")
    ap.add_argument("--file", required=True, help="記事HTMLファイル名（例: guide-xxx.html）")
    ap.add_argument("--category", default="個別銘柄解説", help="guidesカードのバッジ（既定: 個別銘柄解説）")
    ap.add_argument("--emoji", required=True, help="先頭の絵文字（例: 🏰）")
    ap.add_argument("--card-title", required=True, dest="card_title", help="カード/更新履歴用の短めタイトル")
    ap.add_argument("--desc", required=True, help="guidesカードの説明文")
    ap.add_argument("--date", default=None, help="YYYY-MM-DD（省略時は記事HTMLのdatePublishedから）")
    ap.add_argument("--readmin", default=None, help="読了分（省略時は記事HTMLから/既定10）")
    ap.add_argument("--badge", default="badge-news", help="バッジCSSクラス（既定: badge-news）")
    ap.add_argument("--dry-run", action="store_true", dest="dry", help="書き込まず変更内容のみ表示")
    a = ap.parse_args()

    if not os.path.exists(os.path.join(SCRIPT_DIR, a.file)):
        print(f"❌ 記事HTMLが見つかりません: {a.file}（先に①記事を作成してください）")
        sys.exit(1)

    html = _read(a.file)
    auto_date, auto_readmin = extract_from_html(html)
    date = a.date or auto_date
    readmin = a.readmin or auto_readmin or "10"
    if not date or not re.match(r'^\d{4}-\d{2}-\d{2}$', date):
        print(f"❌ 日付が不正/未取得: {date}（--date YYYY-MM-DD を指定してください）")
        sys.exit(1)

    print(f"📝 記事公開の準備: {a.file}")
    print(f"   カテゴリ={a.category} / 日付={date} / 読了={readmin}分"
          + ("   [DRY-RUN: 書き込みなし]" if a.dry else ""))
    print("────────────────────────────")
    add_to_guides(a.file, a.category, a.emoji, a.card_title, a.desc, date, readmin, a.badge, a.dry)
    add_to_sync(a.file, a.dry)
    add_to_history(a.file, a.emoji, a.card_title, date, a.dry)
    print("  ℹ️  sitemap.xml は generate_market_news.py が全guideを自動収集して再生成（手動追加不要）")
    print("────────────────────────────")
    if a.dry:
        print("DRY-RUN 完了。問題なければ --dry-run を外して再実行してください。")
    else:
        print("②〜⑤ 完了。次の手順:")
        print("  ⑥ python sync_to_github.py")
        print("  ⑦ GitHub Actions → Update Market News → Run workflow（index再生成）")
        print("  ⑧ ライブ確認（記事URL / index更新履歴 / guidesカード）")


if __name__ == "__main__":
    main()
