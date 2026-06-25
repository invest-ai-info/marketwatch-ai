# -*- coding: utf-8 -*-
"""
political-feed.html ビルダー (B案-A)
=====================================================
political-feed.json を読み込み、政治発言ライブフィードを HTML 化。
ナビバー・dark mode toggle・og:image は既存ページのデザインを踏襲。

使い方:
    python build_political_feed_page.py
"""
import os
import sys
import json
import html
from datetime import datetime, timedelta, timezone
from collections import Counter

JST = timezone(timedelta(hours=9))
FEED_FILE = "political-feed.json"
OUTPUT_FILE = "political-feed.html"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def _fmt_jst(iso_str):
    """ISO datetime を 'MM/DD HH:MM JST' に整形"""
    if not iso_str:
        return "—"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.astimezone(JST).strftime("%m/%d %H:%M")
    except Exception:
        return iso_str[:16].replace("T", " ")


def _hours_ago(iso_str):
    """何時間前かを返す（小数 1 桁）"""
    if not iso_str:
        return None
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - dt.astimezone(timezone.utc)
        return round(delta.total_seconds() / 3600, 1)
    except Exception:
        return None


def build_html(items):
    last_updated = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    total = len(items)
    high_n = sum(1 for it in items if it.get("importance") == "HIGH")
    mid_n = sum(1 for it in items if it.get("importance") == "MID")
    low_n = sum(1 for it in items if it.get("importance") == "LOW")

    # 過去 24h, 7d の集計
    now_utc = datetime.now(timezone.utc)
    last_24h = 0
    last_7d = 0
    for it in items:
        try:
            dt = datetime.fromisoformat((it.get("published_at") or "").replace("Z", "+00:00"))
            delta = now_utc - dt.astimezone(timezone.utc)
            if delta.total_seconds() <= 86400:
                last_24h += 1
            if delta.total_seconds() <= 86400 * 7:
                last_7d += 1
        except Exception:
            pass

    # 発信元分布（上位）
    src_counter = Counter((it.get("source") or "—") for it in items)
    top_sources = src_counter.most_common(5)

    # カード列を組み立て
    cards = []
    for it in items:
        importance = it.get("importance", "LOW")
        title_ja = it.get("title_ja") or it.get("title_en", "（タイトル取得失敗）")
        title_en = it.get("title_en", "")
        url = it.get("url", "#")
        source = it.get("source", "—")
        pub = _fmt_jst(it.get("published_at"))
        hours_ago = _hours_ago(it.get("published_at"))
        ai_comment = it.get("ai_comment_ja") or ""
        assets = it.get("affected_assets") or []
        query = it.get("matched_query", "")

        # 重要度バッジ
        if importance == "HIGH":
            badge_class = "badge-high"
            badge_text = "🔴 HIGH"
            card_class = "card-high"
        elif importance == "MID":
            badge_class = "badge-mid"
            badge_text = "🟠 MID"
            card_class = "card-mid"
        else:
            badge_class = "badge-low"
            badge_text = "📰 LOW"
            card_class = "card-low"

        # 影響銘柄バッジ
        asset_badges = ""
        if assets:
            asset_badges = " ".join([f'<span class="asset-tag">{html.escape(a)}</span>' for a in assets[:5]])

        hours_label = f"{hours_ago}h 前" if hours_ago is not None else ""

        # AI コメントブロック
        ai_block = ""
        if ai_comment:
            ai_block = f'<div class="ai-comment">💡 {html.escape(ai_comment)}</div>'

        # 原文タイトル（日本語と違うときだけ表示）
        en_block = ""
        if title_en and title_en != title_ja:
            en_block = f'<div class="title-en">📰 {html.escape(title_en)}</div>'

        cards.append(f"""
        <div class="feed-card {card_class}">
          <div class="card-header">
            <span class="badge {badge_class}">{badge_text}</span>
            <span class="source-label">{html.escape(source)}</span>
            <span class="time-label">{pub} JST <span style="color:#8b949e">/ {hours_label}</span></span>
          </div>
          <div class="title-ja">{html.escape(title_ja)}</div>
          {en_block}
          {ai_block}
          <div class="card-footer">
            <span class="asset-row">📊 {asset_badges or '<span class="asset-tag">all</span>'}</span>
            <a href="{html.escape(url)}" target="_blank" rel="noopener" class="orig-link">原文を読む →</a>
          </div>
        </div>""")

    cards_html = "\n".join(cards) or '<div class="empty-state">📭 まだ発言データがありません。次の workflow 実行（30 分以内）でデータが集まります。</div>'

    # 発信元分布バー
    src_bars = []
    for src_name, count in top_sources:
        if total > 0:
            pct = count / total * 100
            src_bars.append(
                f'<div class="src-row"><span class="src-name">{html.escape(src_name)}</span>'
                f'<div class="src-bar-bg"><div class="src-bar-fill" style="width:{pct:.0f}%"></div></div>'
                f'<span class="src-count">{count} 件</span></div>'
            )
    src_bars_html = "\n".join(src_bars) or '<div style="color:#6e7781">データなし</div>'

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🚨 政治発言ライブフィード｜MarketWatch AI</title>
<meta name="description" content="トランプ Truth Social・WhiteHouse 公式声明・主要中銀発言を 30 分ごとに自動収集。重要度別ランク付け、影響銘柄推定、Gemini による日本語化と一言コメント。">
<link rel="canonical" href="https://marketwatch-jp.com/political-feed.html">
<meta property="og:type" content="website">
<meta property="og:title" content="🚨 政治発言ライブフィード｜MarketWatch AI">
<meta property="og:description" content="トランプ・パウエル・植田など相場を動かす発言を 30 分ごと自動収集。重要度別ランク・影響銘柄・AI 一言コメント付き。">
<meta property="og:url" content="https://marketwatch-jp.com/political-feed.html">
<meta property="og:site_name" content="MarketWatch AI">
<meta property="og:locale" content="ja_JP">
<meta property="og:image" content="https://marketwatch-jp.com/05_top_news_frb.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="https://marketwatch-jp.com/05_top_news_frb.png">
<script async src="https://www.googletagmanager.com/gtag/js?id=G-FMVFEV7Q2E"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-FMVFEV7Q2E');</script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Noto Sans JP','Segoe UI','Hiragino Sans','Yu Gothic',sans-serif;background:#fff;color:#1f2328;line-height:1.7;min-height:100vh}}
header{{background:linear-gradient(135deg,#f6f8fa,#fff);border-bottom:1px solid #d0d7de;padding:24px 32px}}
.header-inner{{max-width:1200px;margin:0 auto}}
.header-title{{font-size:1.6rem;font-weight:700;background:linear-gradient(90deg,#0969da,#1f6feb);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}
.header-meta{{font-size:.85rem;color:#57606a;margin-top:4px}}
main{{max-width:1100px;margin:0 auto;padding:32px 24px}}
.nav-bar{{display:flex;flex-wrap:wrap;gap:10px;justify-content:center;max-width:1000px;margin:0 auto 32px}}
.nav-btn{{padding:11px 20px;background:#f6f8fa;border:1px solid #d0d7de;border-radius:10px;color:#57606a;text-decoration:none;font-size:.95rem;font-weight:600;min-width:170px;text-align:center;display:inline-flex;align-items:center;justify-content:center;gap:8px;transition:all .2s}}
.nav-btn:hover{{border-color:#0969da;color:#0969da}}
.nav-btn.current{{background:#0969da;border-color:#0969da;color:#fff}}
.page-header{{background:#f6f8fa;border:1px solid #d0d7de;border-radius:12px;padding:28px 32px;margin-bottom:24px}}
h1{{font-size:1.8rem;color:#0969da;margin-bottom:8px}}
.page-desc{{font-size:.92rem;color:#57606a}}
.kpi-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:14px;margin:18px 0 28px}}
.kpi{{background:#fff;border:1px solid #d0d7de;border-left:4px solid #0969da;border-radius:10px;padding:16px;text-align:center}}
.kpi.high{{border-left-color:#cf222e}}
.kpi.mid{{border-left-color:#9a6700}}
.kpi.low{{border-left-color:#6e7781}}
.kpi-num{{font-size:1.7rem;font-weight:800;color:#1f2328}}
.kpi.high .kpi-num{{color:#cf222e}}
.kpi.mid .kpi-num{{color:#9a6700}}
.kpi.low .kpi-num{{color:#6e7781}}
.kpi-label{{font-size:.75rem;color:#57606a;margin-top:4px}}
h2{{font-size:1.25rem;color:#1f6feb;margin:28px 0 14px;padding-bottom:8px;border-bottom:2px solid #d0d7de}}
.info-box{{background:#ddf4ff;border-left:4px solid #0969da;border-radius:6px;padding:14px 18px;margin:14px 0;font-size:.9rem;color:#1f6feb}}
.info-box::before{{content:"💡 ";font-weight:700}}
.warning-box{{background:#fff8c5;border-left:4px solid #9a6700;border-radius:6px;padding:14px 18px;margin:14px 0;font-size:.9rem;color:#9a6700}}
.warning-box::before{{content:"⚠️ ";font-weight:700}}
.feed-card{{background:#fff;border:1px solid #d0d7de;border-radius:10px;padding:18px 20px;margin:14px 0;border-left:5px solid #6e7781}}
.feed-card.card-high{{border-left-color:#cf222e;background:#fffafa}}
.feed-card.card-mid{{border-left-color:#9a6700}}
.feed-card.card-low{{border-left-color:#6e7781}}
.card-header{{display:flex;flex-wrap:wrap;align-items:center;gap:10px;margin-bottom:10px;font-size:.82rem}}
.badge{{display:inline-block;padding:3px 10px;border-radius:4px;font-weight:700;font-size:.75rem;letter-spacing:.04em}}
.badge-high{{background:#ffebe9;color:#cf222e;border:1px solid #cf222e}}
.badge-mid{{background:#fff8c5;color:#9a6700;border:1px solid #9a6700}}
.badge-low{{background:#f6f8fa;color:#6e7781;border:1px solid #d0d7de}}
.source-label{{color:#0969da;font-weight:600}}
.time-label{{color:#57606a;margin-left:auto}}
.title-ja{{font-size:1.05rem;font-weight:700;color:#1f2328;margin-bottom:6px;line-height:1.5}}
.title-en{{font-size:.82rem;color:#6e7781;margin-bottom:8px;font-style:italic}}
.ai-comment{{background:#dafbe1;border-left:3px solid #1a7f37;border-radius:4px;padding:8px 12px;margin:8px 0;font-size:.88rem;color:#1a7f37}}
.card-footer{{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-top:10px;flex-wrap:wrap;font-size:.82rem}}
.asset-tag{{display:inline-block;background:#ddf4ff;color:#0969da;border:1px solid #54aeff;padding:2px 8px;border-radius:4px;font-size:.75rem;font-weight:600;margin-right:4px}}
.orig-link{{color:#0969da;font-weight:600;text-decoration:none}}
.orig-link:hover{{text-decoration:underline}}
.empty-state{{padding:60px 0;text-align:center;color:#6e7781;font-size:1rem}}
.src-row{{display:flex;align-items:center;gap:12px;margin:6px 0;font-size:.85rem}}
.src-name{{min-width:140px;color:#1f2328;font-weight:600}}
.src-bar-bg{{flex:1;height:14px;background:#f6f8fa;border:1px solid #d0d7de;border-radius:4px;overflow:hidden}}
.src-bar-fill{{height:100%;background:linear-gradient(90deg,#0969da,#54aeff)}}
.src-count{{min-width:60px;text-align:right;color:#57606a}}
footer{{background:#f6f8fa;border-top:1px solid #d0d7de;padding:20px 32px;text-align:center;font-size:.78rem;color:#6e7781;margin-top:40px}}
footer a{{color:#0969da;text-decoration:none}}
@media(max-width:600px){{.nav-bar{{display:grid;grid-template-columns:1fr 1fr;gap:8px}}.nav-btn{{min-width:0;width:100%;padding:10px 8px;font-size:.82rem}}.page-header{{padding:20px}}h1{{font-size:1.4rem}}.kpi-num{{font-size:1.3rem}}.time-label{{margin-left:0}}}}
body.dark{{background:#0d1117;color:#e6edf3}}
body.dark header{{background:linear-gradient(135deg,#161b22,#0d1117);border-bottom-color:#30363d}}
body.dark .nav-btn{{background:#161b22;border-color:#30363d;color:#8b949e}}
body.dark .nav-btn:hover{{border-color:#58a6ff;color:#58a6ff}}
body.dark .page-header{{background:#161b22;border-color:#30363d}}
body.dark .page-desc,body.dark .header-meta{{color:#8b949e}}
body.dark h1,body.dark h2{{color:#79c0ff;border-bottom-color:#30363d}}
body.dark .kpi,body.dark .feed-card{{background:#161b22;border-color:#30363d}}
body.dark .feed-card.card-high{{background:#2d0d0e}}
body.dark .kpi-num{{color:#e6edf3}}
body.dark .title-ja{{color:#e6edf3}}
body.dark .title-en{{color:#8b949e}}
body.dark .source-label{{color:#79c0ff}}
body.dark .src-bar-bg{{background:#0d1117;border-color:#30363d}}
body.dark footer{{background:#161b22;color:#8b949e;border-top-color:#30363d}}
</style>
</head>
<body>
<button id="theme-toggle" onclick="toggleTheme()" aria-label="テーマ切替" style="position:fixed;top:16px;right:16px;width:42px;height:42px;border-radius:50%;border:1px solid #d0d7de;background:#fff;cursor:pointer;z-index:9999;box-shadow:0 2px 8px rgba(0,0,0,.1);font-size:18px;display:flex;align-items:center;justify-content:center">🌙</button>
<header><div class="header-inner"><div class="header-title">📊 MarketWatch AI</div><div class="header-meta">日本人投資家のためのマーケット情報サイト</div><div style="margin-top:11px;padding-top:11px;border-top:1px solid rgba(128,128,128,.22)"><div style="font-size:1.3rem;font-weight:700;color:#0969da">🚨 政治発言ライブ</div></div></div></header>

<main>
<nav class="nav-bar">
  <a class="nav-btn" href="index.html">🏠 トップページ</a>
  <a class="nav-btn current" href="political-feed.html">🚨 政治発言ライブ</a>
  <a class="nav-btn" href="track-record.html">📊 シグナル成績</a>
  <a class="nav-btn" href="calendar.html">📅 経済カレンダー</a>
  <a class="nav-btn" href="guides.html">📚 解説記事</a>
  <a class="nav-btn" href="guide-investment-books.html">📖 投資本</a>
  <a class="nav-btn" href="market-health.html">🩺 市場健康度</a>
  <a class="nav-btn" href="hot-assets.html">🔥 出来高急増</a>
  <a class="nav-btn" href="charts.html">📈 50年チャート</a>
  <a class="nav-btn" href="youtube-summary.html">📺 YouTube要約</a>
</nav>

<div class="page-header">
  <h1>🚨 政治発言ライブフィード</h1>
  <div class="page-desc">
    トランプ大統領 Truth Social・WhiteHouse 公式声明・パウエル FRB・植田 BOJ・ラガルド ECB など、相場を動かす発言を <strong>30 分ごとに自動収集</strong>。
    Gemini で日本語化 + 一言コメント、影響銘柄を推定して重要度別にランク付けします。
    <br><span style="color:#6e7781;font-size:.85rem">最終更新: {last_updated} ／ 自動更新: 30 分間隔 (cron best-effort、実際は 30-45 分)</span>
  </div>
</div>

<h2>📊 サマリ KPI</h2>
<div class="kpi-grid">
  <div class="kpi"><div class="kpi-num">{total}</div><div class="kpi-label">蓄積件数（最大 {100}）</div></div>
  <div class="kpi"><div class="kpi-num">{last_24h}</div><div class="kpi-label">過去 24h</div></div>
  <div class="kpi"><div class="kpi-num">{last_7d}</div><div class="kpi-label">過去 7 日</div></div>
  <div class="kpi high"><div class="kpi-num">{high_n}</div><div class="kpi-label">🔴 HIGH</div></div>
  <div class="kpi mid"><div class="kpi-num">{mid_n}</div><div class="kpi-label">🟠 MID</div></div>
  <div class="kpi low"><div class="kpi-num">{low_n}</div><div class="kpi-label">📰 LOW</div></div>
</div>

<div class="info-box">
  <strong>使い方:</strong> 🔴 HIGH 発言は新規検知時に <strong>メール通知</strong> も配信されます（GMAIL_USER / ALERT_RECIPIENT 設定済みの場合）。
  日中はサイトを開きっぱなしにせず、メールに来た HIGH 発言だけ確認するのが効率的。
</div>

<h2>📡 発信元の分布（上位 5 ソース）</h2>
{src_bars_html}

<h2>📒 直近の発言（新しい順）</h2>
{cards_html}

<div class="warning-box">
  <strong>免責:</strong> 重要度判定（HIGH/MID/LOW）はキーワードベースで自動算出されたものです。AI コメントは Gemini による一般的な示唆であり、個別の投資助言ではありません。
  発信元の信頼性・タイミング・原文の解釈はご自身でご確認ください。投資判断は自己責任で。
</div>

<div style="background:#f6f8fa;border:1px solid #d0d7de;border-radius:12px;padding:24px 28px;margin-top:24px">
  <h2 style="font-size:1.2rem;color:#1f6feb;margin:0 0 12px;border-bottom:1px solid #d0d7de;padding-bottom:8px">📘 政治発言フィードの見方・活用法</h2>
  <p style="font-size:.95rem;color:#424a53;line-height:1.85;margin-bottom:12px">なぜ政治家・中央銀行関係者の「発言」を追うのか——それは、<strong>金融政策・関税・財政・地政学</strong>といった相場の土台が、要人の一言で大きく動くことがあるからです。たとえば中銀総裁の利上げ/利下げを示唆する発言、通商をめぐる強硬発言、為替介入への言及などは、株価や為替が<strong>発言の瞬間に反応する</strong>ことがあります。このページは、そうした“相場を動かしうる発言”を時系列で拾い、重要度（HIGH/MID/LOW）の目安をつけて並べたものです。</p>
  <p style="font-size:.95rem;color:#424a53;line-height:1.85;margin-bottom:12px">使うときのコツは、<strong>ヘッドラインだけで反応しないこと</strong>。同じ言葉でも「誰が・どういう文脈で・本気度はどれくらいか」で市場へのインパクトは変わります。重要度（HIGH）に加えて、<strong>発信元の信頼性</strong>と<strong>発言の前後関係</strong>を確認し、一次情報（公式声明・会見の全文）に当たるのが基本です。</p>
  <ul style="margin:6px 0 14px 22px;color:#424a53;font-size:.94rem;line-height:1.85">
    <li><strong>速報性の裏返し</strong>：発言は速い分、噂・観測・後の撤回も混じります。最初の急な値動きに飛びつくと往復ビンタになりがち。</li>
    <li><strong>カレンダーと併用</strong>：要人発言は<a href="calendar.html" style="color:#0969da">重要指標の発表</a>前後に集中しがち。イベントとセットで見ると流れがつかめます。</li>
  </ul>
  <p style="font-size:.9rem;color:#57606a;margin-bottom:8px">▶ あわせて読む：<a href="calendar.html" style="color:#0969da">経済カレンダー</a> ／ <a href="guides.html" style="color:#0969da">解説記事一覧</a> ／ <a href="guide-loss-cut.html" style="color:#0969da">ニュースに振り回されない損切りの技術</a></p>
  <p style="font-size:.8rem;color:#6e7781;margin:0">※ 本ページは発言の整理・情報提供であり、特定銘柄の売買推奨や投資助言ではありません。発言の解釈・市場影響は不確実です。投資判断はご自身の責任で行ってください。</p>
</div>

</main>
<footer>© 2026 MarketWatch AI ｜ <a href="index.html">トップに戻る</a> ｜ <a href="guides.html">解説記事一覧</a> ｜ <a href="track-record.html">シグナル成績</a><p data-disclaimer="kinsho-v1" style="margin-top:10px;padding-top:10px;border-top:1px dashed #d0d7de;font-size:.78rem;color:#6e7781;line-height:1.6">⚠️ <b>当サイトは金融商品取引業者ではなく、投資助言・代理業の登録もしていません。</b> 本サイトの情報は投資助言ではなく、投資判断はご自身の責任で行ってください。</p>
</footer>

<script>
function toggleTheme(){{
  document.body.classList.toggle('dark');
  localStorage.setItem('theme', document.body.classList.contains('dark') ? 'dark' : 'light');
  document.getElementById('theme-toggle').textContent = document.body.classList.contains('dark') ? '☀️' : '🌙';
}}
if (localStorage.getItem('theme') === 'dark') {{
  document.body.classList.add('dark');
  document.getElementById('theme-toggle').textContent = '☀️';
}}
</script>

<script src="site-search.js" defer></script>
</body>
</html>
"""


def main():
    print(f"📄 political-feed.html ビルド開始 {datetime.now(JST).strftime('%Y-%m-%d %H:%M JST')}")
    if not os.path.exists(FEED_FILE):
        print(f"  ⚠️ {FEED_FILE} 未生成、空フィードで HTML を作成")
        items = []
    else:
        try:
            items = json.load(open(FEED_FILE, encoding="utf-8"))
        except Exception as e:
            print(f"  ⚠️ {FEED_FILE} 読込失敗: {e}")
            items = []
    print(f"  📥 {len(items)} 件読込")

    html_str = build_html(items)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html_str)
    print(f"  ✅ {OUTPUT_FILE} 生成 ({os.path.getsize(OUTPUT_FILE) / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
