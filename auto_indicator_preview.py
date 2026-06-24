# -*- coding: utf-8 -*-
"""
経済指標プレビュー記事 自動生成スクリプト
============================================
重要指標の発表が3日以内に迫っている場合、自動で告知記事を生成する。

使い方:
    python auto_indicator_preview.py
    # または generate_market_news.py の末尾から呼び出す

仕組み:
    1. INDICATOR_SCHEDULE で指標の発表予定日をリスト化
    2. 今日から3日以内に発表される指標をチェック
    3. 該当する記事ファイル（guide-auto-{key}-{YYYY-MM-DD}.html）が
       まだ存在しなければ自動生成
    4. guides.html・sitemap.xml にも自動追記

人間がやるべきこと:
    - INDICATOR_SCHEDULE の年次予定を毎年更新
    - 公開後の予想値・結果を手動で追記（必要なら）
"""
import os
import re
import json
import base64
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone

# 日本標準時
JST = timezone(timedelta(hours=9))


# ─────────────────────────────────────────
# GitHub アップロードヘルパー（生成後の自動公開用）
# ─────────────────────────────────────────
def _load_gh_config(script_dir):
    """market-news-config.json(.json) から token/owner/repo/branch を読む。"""
    for fname in ("market-news-config.json.json", "market-news-config.json"):
        p = os.path.join(script_dir, fname)
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                return json.load(f)
    return None


def upload_to_github(local_path, cfg, repo_path=None):
    """単一ファイルを GitHub Contents API で PUT。既存ならSHAで上書き。
    成功で True、失敗で False。
    """
    fname = os.path.basename(local_path)
    rpath = (repo_path or fname).replace("\\", "/").lstrip("/")
    token = cfg["github_token"]
    owner = cfg["github_owner"]
    repo = cfg["github_repo"]
    branch = cfg.get("github_branch", "main")

    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{rpath}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    sha = None
    try:
        req = urllib.request.Request(f"{api_url}?ref={branch}", headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            sha = json.load(resp).get("sha")
    except urllib.error.HTTPError as e:
        if e.code != 404:
            print(f"  ❌ {fname}: SHA取得失敗 ({e.code})")
            return False
    except Exception as e:
        print(f"  ❌ {fname}: 接続失敗 {e}")
        return False

    try:
        with open(local_path, "rb") as f:
            content_b64 = base64.b64encode(f.read()).decode("ascii")
    except Exception as e:
        print(f"  ❌ {fname}: ファイル読込失敗 {e}")
        return False

    now = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    payload = {
        "message": f"auto: publish {fname} [{now}]",
        "content": content_b64,
        "branch": branch,
    }
    if sha:
        payload["sha"] = sha

    try:
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(api_url, data=body, headers=headers, method="PUT")
        with urllib.request.urlopen(req, timeout=60) as resp:
            j = json.load(resp)
            short = j.get("commit", {}).get("sha", "")[:7]
        action = "更新" if sha else "新規公開"
        print(f"  📤 {fname}: GitHub {action} 成功 (commit {short})")
        return True
    except urllib.error.HTTPError as e:
        print(f"  ❌ {fname}: PUT失敗 ({e.code}) {e.read().decode()[:200]}")
        return False
    except Exception as e:
        print(f"  ❌ {fname}: PUTエラー {e}")
        return False

# ─────────────────────────────────────────
# 経済指標スケジュール
# ─────────────────────────────────────────
# 各指標の発表予定日リスト（YYYY-MM-DD形式）
# 月次指標は1年分前もって登録、四半期指標は4回分
# FOMC・日銀は会合スケジュールを公式発表に基づいて登録
# ─────────────────────────────────────────
INDICATOR_SCHEDULE = {
    # ─── 米CPI（毎月10〜15日頃発表、4月分→5月、5月分→6月...）───
    "us_cpi": {
        "name": "米CPI（消費者物価指数）",
        "name_short": "米CPI",
        "category": "米国インフレ指標",
        "importance": 3,
        "emoji": "📊",
        "time_jst": "21:30",
        "country": "🇺🇸",
        "description": "米国の物価上昇率を測る最重要指標。FRBの利下げ・利上げ判断に直結。",
        "schedule": [
            # BLS公式 + カレンダーと一致させた正しい日付
            "2026-05-12",  # 4月分（実績）
            "2026-06-10",  # 5月分
            "2026-07-10",  # 6月分
            "2026-08-12",  # 7月分
            "2026-09-10",  # 8月分
            "2026-10-14",  # 9月分
            "2026-11-12",  # 10月分
            "2026-12-10",  # 11月分
        ],
        "scenarios": {
            "bull": "予想下回り → 利下げ期待強化 → ドル売り・株買い・金買い",
            "base": "予想通り → 方向感薄い、レンジ推移",
            "bear": "予想上回り → インフレ再燃懸念 → ドル買い・株売り・金売り",
        },
        "watch_points": [
            "ヘッドラインCPI（食品・エネルギー含む）の前年比",
            "コアCPI（食品・エネルギー除く）の前年比 ← FRBが重視",
            "住居費（Shelter）の動向（CPIの34%を占める）",
            "スーパーコアCPI（住居除くサービス）の動き",
        ],
    },

    # ─── 米雇用統計（毎月第1金曜日）───
    "us_jobs": {
        "name": "米雇用統計（非農業部門雇用者数・失業率）",
        "name_short": "米雇用統計",
        "category": "米国景気指標",
        "importance": 3,
        "emoji": "💼",
        "time_jst": "21:30",
        "country": "🇺🇸",
        "description": "NFP・失業率・平均時給。米景気の最重要指標。",
        "schedule": [
            "2026-06-05", "2026-07-03", "2026-08-07",
            "2026-09-04", "2026-10-02", "2026-11-06",
            "2026-12-04",
        ],
        "scenarios": {
            "bull": "NFP弱め → 利下げ期待 → ドル売り・株買い",
            "base": "予想通り → 小動き",
            "bear": "NFP強め・賃金加速 → 利下げ後退 → ドル買い・株売り",
        },
        "watch_points": [
            "NFP（非農業部門雇用者数）：20万人超で強い",
            "失業率：4.0%台維持か4.2%超で景気減速サイン",
            "平均時給：前年比+4%超は賃金インフレ持続",
            "過去2か月のNFP修正値",
        ],
    },

    # ─── 米PCE（毎月末頃）───
    "us_pce": {
        "name": "米PCE価格指数",
        "name_short": "米PCE",
        "category": "米国インフレ指標",
        "importance": 2,
        "emoji": "💵",
        "time_jst": "21:30",
        "country": "🇺🇸",
        "description": "FRBが最重視する物価指標。CPIより遅れて発表。",
        "schedule": [
            "2026-05-30", "2026-06-27", "2026-07-31",
            "2026-08-29", "2026-09-26", "2026-10-31",
            "2026-11-26", "2026-12-19",
        ],
        "scenarios": {
            "bull": "コアPCE 2%台へ鈍化 → 利下げ確度UP",
            "base": "前回並み",
            "bear": "コアPCE 3%超 → 利下げ困難",
        },
        "watch_points": [
            "コアPCE前年比（FRBの2%目標との比較）",
            "個人消費の伸び",
            "個人所得の伸び",
        ],
    },

    # ─── FOMC（年8回・2026年）───
    "fomc": {
        "name": "FOMC（米連邦公開市場委員会）",
        "name_short": "FOMC",
        "category": "米金融政策",
        "importance": 3,
        "emoji": "🏦",
        "time_jst": "翌3:00",
        "country": "🇺🇸",
        "description": "米政策金利を決定。市場最重要イベント。",
        "schedule": [
            "2026-06-17",  # June (1日目16日)
            "2026-07-29",
            "2026-09-16",
            "2026-11-04",
            "2026-12-16",
        ],
        "scenarios": {
            "bull": "利下げ＋ハト派会見 → 株高・ドル安",
            "base": "据え置き、方向感不変",
            "bear": "据え置き＋タカ派会見 → 株安・ドル高",
        },
        "watch_points": [
            "政策金利の決定（利下げか据え置きか）",
            "声明文の文言変化（前回比較）",
            "ドットチャート（3・6・9・12月のみ）",
            "パウエル議長会見のトーン",
        ],
    },

    # ─── 日銀会合（年8回）───
    "boj": {
        "name": "日銀金融政策決定会合",
        "name_short": "日銀会合",
        "category": "日本金融政策",
        "importance": 3,
        "emoji": "🏛️",
        "time_jst": "12:00頃",
        "country": "🇯🇵",
        "description": "日本の政策金利を決定。利上げ観測で円相場急変動。",
        "schedule": [
            "2026-06-17",
            "2026-07-31",
            "2026-09-19",
            "2026-10-30",
            "2026-12-19",
        ],
        "scenarios": {
            "bull": "据え置き＋ハト派 → 円安進行・日経高",
            "base": "据え置き・想定通り",
            "bear": "利上げ実施 → 円急騰・日経安",
        },
        "watch_points": [
            "政策金利の決定（現在0.75%）",
            "経済・物価見通し（年4回：1/4/7/10月）",
            "上田総裁会見のトーン",
            "国債買入オペの変更",
        ],
    },

    # ─── 米GDP速報値（四半期）───
    "us_gdp": {
        "name": "米GDP速報値",
        "name_short": "米GDP",
        "category": "米国経済",
        "importance": 2,
        "emoji": "📈",
        "time_jst": "21:30",
        "country": "🇺🇸",
        "description": "米経済成長率の速報。年4回発表。",
        "schedule": [
            "2026-07-30",  # Q2 2026
            "2026-10-30",  # Q3 2026
        ],
        "scenarios": {
            "bull": "予想上回り → 米景気強い → ドル買い",
            "base": "予想通り",
            "bear": "予想下回り → 景気減速懸念 → ドル売り",
        },
        "watch_points": [
            "前期比年率（QoQ annualized）",
            "個人消費（GDPの70%）",
            "コアPCE価格指数（同時発表）",
        ],
    },

    # ─── 日本GDP速報値（四半期）───
    "jp_gdp": {
        "name": "日本GDP速報値",
        "name_short": "日本GDP",
        "category": "日本経済",
        "importance": 2,
        "emoji": "🇯🇵",
        "time_jst": "8:50",
        "country": "🇯🇵",
        "description": "日本経済の成長率。日銀利上げ判断に影響。",
        "schedule": [
            "2026-05-16",  # Q1 2026
            "2026-08-15",  # Q2 2026
            "2026-11-14",  # Q3 2026
        ],
        "scenarios": {
            "bull": "予想上回り → 日銀利上げ観測 → 円高",
            "base": "予想通り",
            "bear": "マイナス成長 → 利上げ困難 → 円安",
        },
        "watch_points": [
            "前期比年率",
            "個人消費・設備投資",
            "輸出寄与度（円安効果）",
        ],
    },
}

# 何日前から記事を生成するか
DAYS_BEFORE = 3


def get_upcoming_events(today_jst):
    """今日から DAYS_BEFORE 以内に発表される指標を返す"""
    upcoming = []
    for key, info in INDICATOR_SCHEDULE.items():
        for date_str in info["schedule"]:
            try:
                event_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                continue
            days_until = (event_date - today_jst).days
            # 0 を含める＝発表当日も対象（前日までに生成漏れした場合のキャッチアップ・2026-06-05）
            if 0 <= days_until <= DAYS_BEFORE:
                upcoming.append({
                    "key": key,
                    "info": info,
                    "event_date": event_date,
                    "days_until": days_until,
                })
    return upcoming


def build_preview_html(event):
    """1記事分のHTMLを生成"""
    key = event["key"]
    info = event["info"]
    event_date = event["event_date"]
    days_until = event["days_until"]
    today = datetime.now(JST).strftime("%Y-%m-%d")
    today_jp = datetime.now(JST).strftime("%Y年%-m月%-d日") if os.name != "nt" else datetime.now(JST).strftime("%Y年%#m月%#d日")
    event_date_jp = event_date.strftime("%-m/%-d") if os.name != "nt" else event_date.strftime("%#m/%#d")
    event_date_full = event_date.strftime("%Y-%m-%d")

    countdown = f"あと{days_until}日" if days_until > 0 else "本日"
    countdown_emoji = "🚨" if days_until == 1 else ("⏰" if days_until == 2 else "📅")

    scenarios_html = "".join(
        f'      <div class="scenario-card {cls}"><div class="scenario-title">{emoji} {name}</div><p>{info["scenarios"][cls]}</p></div>\n'
        for cls, emoji, name in [
            ("bull", "🟢", "弱い結果（または利下げ寄り）"),
            ("base", "🟡", "想定通り"),
            ("bear", "🔴", "強い結果（または引き締め寄り）"),
        ]
    )

    watch_points_html = "".join(
        f"        <li>{p}</li>\n" for p in info["watch_points"]
    )

    title = f"【{countdown}】{info['name_short']}（{event_date_jp}発表）プレビュー：注目ポイント・3シナリオ別マーケット反応"

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="robots" content="noindex,follow"><!-- 自動生成の指標プレビュー：薄ページのためインデックス除外（AdSense低価値対策） -->
  <title>{title} - MarketWatch AI</title>
  <meta name="description" content="{event_date_jp}発表の{info['name']}を事前プレビュー。注目ポイント・3シナリオ別の市場反応・トレード戦略を解説。">
  <meta name="keywords" content="{info['name_short']},経済指標,プレビュー,{event_date.strftime('%Y年%-m月') if os.name != 'nt' else event_date.strftime('%Y年%#m月')},ドル円,株式">
  <link rel="canonical" href="https://marketwatch-jp.com/guide-auto-{key}-{event_date_full}.html">
  <meta property="og:type" content="article">
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{event_date_jp}発表の{info['name']}を事前プレビュー。3シナリオ別の市場反応を解説。">
  <meta property="og:url" content="https://marketwatch-jp.com/guide-auto-{key}-{event_date_full}.html">
  <meta property="og:site_name" content="MarketWatch AI">
  <meta property="og:locale" content="ja_JP">
  <script type="application/ld+json">
  {{"@context":"https://schema.org","@type":"NewsArticle","headline":"{title}","description":"{info['name']}の事前プレビュー。3シナリオ別の市場反応を解説。","author":{{"@type":"Organization","name":"MarketWatch AI"}},"publisher":{{"@type":"Organization","name":"MarketWatch AI"}},"datePublished":"{today}","dateModified":"{today}","mainEntityOfPage":"https://marketwatch-jp.com/guide-auto-{key}-{event_date_full}.html"}}
  </script>
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-FMVFEV7Q2E"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){{dataLayer.push(arguments);}}
    gtag('js', new Date());
    gtag('config', 'G-FMVFEV7Q2E');
  </script>
  <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-2552122294306014" crossorigin="anonymous"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    *{{margin:0;padding:0;box-sizing:border-box}}
    body{{font-family:'Noto Sans JP','Segoe UI','Hiragino Sans','Yu Gothic',sans-serif;background:#ffffff;color:#1f2328;min-height:100vh;line-height:1.85}}
    header{{background:linear-gradient(135deg,#f6f8fa,#ffffff);border-bottom:1px solid #d0d7de;padding:24px 32px}}
    .header-inner{{max-width:1200px;margin:0 auto}}
    .header-title{{font-size:1.6rem;font-weight:700;background:linear-gradient(90deg,#0969da,#1f6feb);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}
    .header-meta{{font-size:.85rem;color:#57606a;margin-top:4px}}
    main{{max-width:1200px;margin:0 auto;padding:32px 24px}}
    .nav-bar{{display:flex;flex-wrap:wrap;gap:10px;justify-content:center;max-width:1000px;margin:0 auto 32px}}
    .nav-btn{{display:inline-flex;align-items:center;justify-content:center;gap:8px;padding:11px 20px;background:#f6f8fa;border:1px solid #d0d7de;border-radius:10px;color:#57606a;text-decoration:none;font-size:.95rem;font-weight:600;transition:all .2s;min-width:170px}}
    .nav-btn:hover{{border-color:#0969da;color:#0969da}}
    .nav-btn.current{{background:#0969da;border-color:#0969da;color:#fff}}
    .breadcrumb{{font-size:.82rem;color:#57606a;margin-bottom:16px}}
    .breadcrumb a{{color:#0969da;text-decoration:none}}
    .article{{background:#f6f8fa;border:1px solid #d0d7de;border-radius:12px;padding:36px 40px}}
    h1{{font-size:1.85rem;color:#0969da;margin-bottom:8px;line-height:1.4}}
    .meta-line{{font-size:.85rem;color:#57606a;margin-bottom:28px;padding-bottom:18px;border-bottom:1px solid #d0d7de}}
    h2{{font-size:1.3rem;color:#1f6feb;margin-top:32px;margin-bottom:14px;padding-bottom:8px;border-bottom:2px solid #d0d7de}}
    p{{font-size:.97rem;color:#424a53;margin-bottom:16px}}
    ul,ol{{margin:10px 0 18px 28px;color:#424a53}}
    li{{margin-bottom:8px;font-size:.95rem}}
    strong{{color:#0969da;font-weight:700}}
    a{{color:#0969da;text-decoration:none}}
    a:hover{{text-decoration:underline}}
    .countdown-banner{{background:linear-gradient(135deg,#ffe5e5,#ddf4ff);border:2px solid #cf222e;border-radius:14px;padding:24px 28px;margin:20px 0;text-align:center}}
    .countdown-num{{font-size:2.5rem;font-weight:800;color:#cf222e;line-height:1}}
    .countdown-label{{font-size:1rem;color:#1f2328;margin-top:6px;font-weight:600}}
    .countdown-event{{font-size:1.15rem;color:#0969da;margin-top:10px;font-weight:700}}
    .countdown-time{{font-size:.9rem;color:#57606a;margin-top:6px}}
    .info-card{{background:#ffffff;border:1px solid #d0d7de;border-radius:10px;padding:18px 22px;margin:14px 0}}
    .info-card-title{{font-size:.95rem;color:#0969da;font-weight:700;margin-bottom:10px}}
    .info-card p{{font-size:.92rem;margin-bottom:0}}
    .scenario-card{{background:#ffffff;border:1px solid #d0d7de;border-radius:10px;padding:18px 22px;margin:12px 0}}
    .scenario-card.bull{{border-left:5px solid #1a7f37}}
    .scenario-card.bear{{border-left:5px solid #cf222e}}
    .scenario-card.base{{border-left:5px solid #9a6700}}
    .scenario-title{{font-size:1.02rem;font-weight:700;margin-bottom:6px}}
    .scenario-card.bull .scenario-title{{color:#1a7f37}}
    .scenario-card.bear .scenario-title{{color:#cf222e}}
    .scenario-card.base .scenario-title{{color:#9a6700}}
    .info-box{{background:#dafbe1;border-left:4px solid #1a7f37;border-radius:6px;padding:14px 18px;margin:16px 0;font-size:.92rem;color:#1a7f37}}
    .info-box::before{{content:"💡 ";font-weight:700}}
    .warning-box{{background:#fff8c5;border-left:4px solid #9a6700;border-radius:6px;padding:14px 18px;margin:16px 0;font-size:.92rem;color:#9a6700}}
    .warning-box::before{{content:"⚠️ ";font-weight:700}}
    .related-section{{margin-top:32px;padding-top:24px;border-top:1px solid #d0d7de}}
    .related-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;margin-top:14px}}
    .related-card{{background:#ffffff;border:1px solid #d0d7de;border-radius:8px;padding:14px 16px;text-decoration:none;transition:border-color .2s;display:block}}
    .related-card:hover{{border-color:#0969da;text-decoration:none}}
    .related-card-title{{font-size:.92rem;font-weight:700;color:#1f6feb;margin-bottom:4px}}
    .related-card-desc{{font-size:.78rem;color:#57606a;line-height:1.55}}
    footer{{background:#f6f8fa;border-top:1px solid #d0d7de;padding:20px 32px;text-align:center;font-size:.78rem;color:#6e7781;margin-top:40px}}
    footer a{{color:#0969da;text-decoration:none}}
    #reading-progress{{position:fixed;top:0;left:0;width:0;height:3px;background:linear-gradient(90deg,#0969da,#1f6feb);z-index:9998;transition:width .1s ease-out}}
    @media(max-width:600px){{.article{{padding:24px 20px}}h1{{font-size:1.35rem}}.countdown-num{{font-size:2rem}}.nav-bar{{display:grid;grid-template-columns:1fr 1fr;gap:8px}}.nav-btn{{min-width:0;width:100%;padding:10px 8px;font-size:.82rem}}}}
    .ad-slot{{margin:24px 0;padding:14px;background:#ffffff;border:1px solid #d0d7de;border-radius:10px;text-align:center;overflow:hidden;max-width:100%}}
    .ad-slot a,.ad-slot img{{max-width:100%;height:auto;display:inline-block}}
    .a8-pc{{display:inline-block}}.a8-mobile{{display:none}}
    @media(max-width:600px){{.a8-pc{{display:none}}.a8-mobile{{display:inline-block}}}}
  </style>
</head>
<body>
<div id="reading-progress"></div>
<header>
  <div class="header-inner">
    <div class="header-title">📊 MarketWatch AI</div>
    <div class="header-meta">日本人投資家のためのマーケット情報サイト</div>
  </div>
</header>
<main>
  <nav class="nav-bar">
    <a class="nav-btn" href="index.html">🏠 トップページ</a>
    <a class="nav-btn" href="political-feed.html">🚨 政治発言ライブ</a>
    <a class="nav-btn" href="track-record.html">📊 シグナル成績</a>
    <a class="nav-btn" href="calendar.html">📅 経済カレンダー</a>
    <a class="nav-btn current" href="guides.html">📚 解説記事</a>
    <a class="nav-btn" href="guide-investment-books.html">📖 投資本</a>
    <a class="nav-btn" href="market-health.html">🩺 市場健康度</a>
    <a class="nav-btn" href="hot-assets.html">🔥 出来高急増</a>
    <a class="nav-btn" href="charts.html">📈 50年チャート</a>
    <a class="nav-btn" href="youtube-summary.html">📺 YouTube要約</a>
  </nav>

  <div class="breadcrumb"><a href="index.html">トップ</a> ＞ <a href="guides.html">解説記事</a> ＞ {info['name_short']}カウントダウン</div>

  <article class="article">
    <h1>{countdown_emoji} 【{countdown}】{info['name_short']}発表迫る｜{event_date_jp}{info['time_jst']} 注目ポイント・3シナリオ別マーケット反応</h1>
    <div class="meta-line">公開日：{today_jp} ／ 読了時間：約4分 ／ カテゴリ：指標プレビュー（自動生成）</div>

    <div class="countdown-banner">
      <div class="countdown-num">{countdown_emoji} {countdown}</div>
      <div class="countdown-label">{info['name']}</div>
      <div class="countdown-event">{info['country']} {event_date_jp} 日本時間 {info['time_jst']}</div>
      <div class="countdown-time">重要度：{"★" * info['importance']}</div>
    </div>

    <h2>📌 この指標は何？</h2>
    <div class="info-card">
      <div class="info-card-title">{info['emoji']} {info['name']}</div>
      <p>{info['description']}</p>
    </div>

    <h2>🎯 3つの想定シナリオ</h2>
{scenarios_html}

    <h2>🔑 プロが見ている注目ポイント</h2>
    <ol>
{watch_points_html}    </ol>

    <div class="ad-slot">
      <div style="font-size:.7rem;color:#6e7681;letter-spacing:.12em;margin-bottom:8px">広告 / PR</div>
      <a class="a8-pc" href="https://px.a8.net/svt/ejp?a8mat=4B1WM4+D44RHU+4SM6+614CX" rel="nofollow"><img border="0" width="728" height="90" alt="" src="https://www25.a8.net/svt/bgt?aid=260429404793&amp;wid=001&amp;eno=01&amp;mid=s00000022371001013000&amp;mc=1"></a>
      <a class="a8-mobile" href="https://px.a8.net/svt/ejp?a8mat=4B1WM4+D44RHU+4SM6+5ZEMP" rel="nofollow"><img border="0" width="320" height="50" alt="" src="https://www25.a8.net/svt/bgt?aid=260429404793&amp;wid=001&amp;eno=01&amp;mid=s00000022371001005000&amp;mc=1"></a>
    </div>

    <h2>⏰ 日本人投資家のトレードタイミング</h2>
    <div class="info-box">
      <strong>発表前30分はポジション縮小推奨。</strong>レバレッジを使ったFX取引は特に注意。発表直後の「初動」だけで飛びつかず、5〜10分後の「セカンド・リアクション」を確認するのがプロの基本。
    </div>

    <div class="warning-box">
      本記事は自動生成された汎用プレビューです。実際の市場予想値・トレード戦略は最新情報を確認のうえ、自己責任で判断してください。
    </div>

    <div class="related-section">
      <h3 style="font-size:1.05rem;color:#1f6feb;margin-bottom:8px">📚 関連記事</h3>
      <div class="related-grid">
        <a class="related-card" href="calendar.html"><div class="related-card-title">📅 経済カレンダー</div><div class="related-card-desc">月間の重要指標を一覧で確認</div></a>
        <a class="related-card" href="guides.html"><div class="related-card-title">📚 解説記事一覧</div><div class="related-card-desc">投資・指標解説の全記事</div></a>
        <a class="related-card" href="index.html"><div class="related-card-title">🏠 トップページ</div><div class="related-card-desc">最新の価格・センチメント</div></a>
      </div>
    </div>

  </article>
</main>

<footer>
  © 2026 MarketWatch AI ｜ <a href="index.html">トップに戻る</a>
<p data-disclaimer="kinsho-v1" style="margin-top:10px;padding-top:10px;border-top:1px dashed #d0d7de;font-size:.78rem;color:#6e7781;line-height:1.6">⚠️ <b>当サイトは金融商品取引業者ではなく、投資助言・代理業の登録もしていません。</b> 本サイトの情報は投資助言ではなく、投資判断はご自身の責任で行ってください。</p>
</footer>

<script>
(function(){{function setTheme(t){{document.body.classList.toggle('dark',t==='dark');var b=document.getElementById('theme-toggle');if(b)b.textContent=t==='dark'?'☀️':'🌙';try{{localStorage.setItem('theme',t)}}catch(e){{}}}}window.toggleTheme=function(){{setTheme(document.body.classList.contains('dark')?'light':'dark')}};var t='light';try{{t=localStorage.getItem('theme')||'light'}}catch(e){{}}setTheme(t);}})();
window.addEventListener('scroll',function(){{var s=window.scrollY,d=document.documentElement.scrollHeight-window.innerHeight,p=document.getElementById('reading-progress');if(p)p.style.width=(d>0?(s/d*100):0)+'%'}});
</script>

</body>
</html>
"""
    return html


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    today_jst = datetime.now(JST).date()
    print(f"📅 経済指標プレビュー自動生成 ({today_jst})")

    upcoming = get_upcoming_events(today_jst)
    if not upcoming:
        print("  - 3日以内の重要指標なし、スキップ")
        return

    gh_cfg = _load_gh_config(script_dir)
    if gh_cfg is None:
        print("  ⚠️  market-news-config.json が見つからず、GitHubアップロードはスキップ")

    generated_count = 0
    uploaded_count = 0
    for event in upcoming:
        key = event["key"]
        event_date_str = event["event_date"].strftime("%Y-%m-%d")
        filename = f"guide-auto-{key}-{event_date_str}.html"
        filepath = os.path.join(script_dir, filename)

        if os.path.exists(filepath):
            print(f"  ⏭️  {filename}: 既に存在、スキップ")
            continue

        html = build_preview_html(event)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  ✅ {filename}: 生成完了 ({event['days_until']}日前)")
        generated_count += 1

        # 生成と同時にGitHubへアップロード
        if gh_cfg is not None:
            if upload_to_github(filepath, gh_cfg, repo_path=filename):
                uploaded_count += 1

    print(f"📊 完了: {generated_count}件の新規記事を生成 / {uploaded_count}件をGitHubへ公開")


if __name__ == "__main__":
    main()
