# -*- coding: utf-8 -*-
"""
政治発言・公式声明 ライブフィード収集スクリプト (Phase 1+2)
=====================================================
NEWS API + WhiteHouse 公式 RSS から相場影響のある政治発言を取得し、
political-feed.json (過去 100 件キープ) に蓄積する。
新規 HIGH 発言があれば既存メールシステム経由で速報送信。

データソース:
- NEWS API: 政治発言クエリ多数 (Trump tariff, Powell criticism, BOJ intervention 等)
- WhiteHouse 公式 RSS: 大統領令・公式声明

使い方:
    python fetch_political_news.py            # 通常実行
    python fetch_political_news.py --no-email # メール送信なし（テスト用）

GitHub Actions schedule: 30 分間隔 (cron */30 * * * *)
"""
import os
import sys
import json
import hashlib
import smtplib
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate, parsedate_to_datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

JST = timezone(timedelta(hours=9))
FEED_FILE = "political-feed.json"
MAX_KEEP = 100  # フィードに残す最大件数

# 政治発言クエリ + 影響銘柄推定（NEWS API）
POLITICAL_QUERIES = [
    ("Trump tariff",              ["NKD=F", "USDJPY=X", "CL=F"]),
    ("Trump China tariff",        ["NKD=F", "USDJPY=X", "AUDJPY=X", "CL=F"]),
    ("Trump Fed Powell",          ["USDJPY=X", "all"]),
    ("Truth Social Trump market", ["all"]),
    ("White House statement",     ["all"]),
    ("executive order Trump",     ["all"]),
    ("BOJ intervention yen",      ["USDJPY=X", "NKD=F"]),
    ("Bank of Japan policy",      ["USDJPY=X", "NKD=F"]),
    ("Federal Reserve emergency", ["all"]),
    ("Powell speech market",      ["USDJPY=X", "all"]),
    ("ECB Lagarde",               ["EURUSD=X", "EURJPY=X"]),
    ("Iran oil Strait Hormuz",    ["CL=F"]),
    ("China retaliation tariff",  ["NKD=F", "CL=F", "AUDJPY=X"]),
]

# WhiteHouse 公式 RSS
WHITEHOUSE_FEEDS = [
    "https://www.whitehouse.gov/briefing-room/feed/",
    "https://www.whitehouse.gov/presidential-actions/feed/",
]

# 重要度判定キーワード（小文字比較）
HIGH_TRIGGERS = [
    "tariff announce", "tariff impose", "additional tariff", "retaliatory tariff",
    "intervention", "emergency rate", "executive order",
    "trump signs", "trump announces", "fed emergency",
    "boj intervene", "yen intervention",
    "iran strike", "china retaliat",
]
MID_TRIGGERS = [
    "trump", "powell", "fed", "boj", "white house", "ecb", "lagarde",
    "statement", "speech", "warning", "criticism", "tariff", "sanction",
    "truth social",
]


def _now_iso():
    return datetime.now(JST).isoformat(timespec="seconds")


def make_id(source, url, pub):
    base = f"{source}|{url}|{pub}"
    return hashlib.sha1(base.encode("utf-8")).hexdigest()[:16]


def calc_importance(title_en, source):
    """タイトルと source から HIGH/MID/LOW を判定"""
    t = (title_en or "").lower()
    # HIGH トリガー: 強い相場インパクトのキーワード
    for kw in HIGH_TRIGGERS:
        if kw in t:
            return "HIGH"
    # MID トリガー: 政治家・中銀関連の発言
    hits = sum(1 for kw in MID_TRIGGERS if kw in t)
    if hits >= 2:
        return "HIGH"  # MID キーワード 2 個以上 = 重要
    if hits >= 1:
        return "MID"
    return "LOW"


def fetch_newsapi_political(api_key, query, from_iso):
    """NEWS API で政治クエリの記事を取得"""
    params = urllib.parse.urlencode({
        "q": query,
        "language": "en",
        "sortBy": "publishedAt",
        "from": from_iso,
        "pageSize": 10,
        "apiKey": api_key,
    })
    url = f"https://newsapi.org/v2/everything?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": "MarketWatch/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            data = json.loads(res.read())
            return data.get("articles", [])
    except Exception as e:
        print(f"  ⚠️ NEWS API ({query[:30]}) 失敗: {type(e).__name__}: {str(e)[:60]}")
        return []


def fetch_whitehouse_rss(feed_url):
    """WhiteHouse 公式 RSS を取得"""
    try:
        import feedparser
    except ImportError:
        print("  ⚠️ feedparser 未インストール、WhiteHouse RSS スキップ")
        return []
    try:
        req = urllib.request.Request(feed_url, headers={"User-Agent": "Mozilla/5.0 (compatible; MarketWatch/1.0)"})
        with urllib.request.urlopen(req, timeout=15) as r:
            content = r.read()
        feed = feedparser.parse(content)
        items = []
        for entry in feed.entries[:30]:
            pub_str = entry.get("published") or entry.get("updated") or ""
            try:
                pub_dt = parsedate_to_datetime(pub_str)
                if pub_dt.tzinfo is None:
                    pub_dt = pub_dt.replace(tzinfo=timezone.utc)
            except Exception:
                continue
            summary = entry.get("summary", "") or entry.get("description", "")
            items.append({
                "title": entry.get("title", ""),
                "url": entry.get("link", ""),
                "publishedAt": pub_dt.isoformat(),
                "description": (summary or "")[:300],
            })
        return items
    except Exception as e:
        print(f"  ⚠️ WhiteHouse RSS 失敗: {type(e).__name__}: {str(e)[:60]}")
        return []


def translate_and_comment_jp(items, api_key):
    """Gemini で英語タイトルを一括日本語化 + 一言コメント"""
    if not api_key or not items:
        return items
    try:
        import google.generativeai as genai
    except ImportError:
        return items
    genai.configure(api_key=api_key)

    # バッチで一気に翻訳（API call を 1 回に集約）
    numbered = "\n".join([f"{i+1}. {it['title_en']}" for i, it in enumerate(items)])
    prompt = f"""次の英語の政治・マーケットニュース見出しを、それぞれ日本語に翻訳し、各見出しごとに日本人投資家への一言コメント（40 字以内）を「／」で区切って付けてください。

【入力】
{numbered}

【出力フォーマット】（番号付き、前置きや解説は一切不要）
1. 日本語見出し ／ 一言コメント
2. 日本語見出し ／ 一言コメント
...

【注意】
- 日本語見出しは固有名詞を保持して自然な翻訳に
- 一言コメントは「短期で〜に下押し」「為替に〜の可能性」など慎重表現で
- 影響なさそうなニュースは「直接的な相場影響は限定的」など
"""
    text = ""
    for model_name in ("gemini-2.0-flash-lite", "gemini-2.5-flash-lite", "gemini-2.0-flash"):
        try:
            model = genai.GenerativeModel(model_name)
            resp = model.generate_content(prompt)
            text = (resp.text or "").strip()
            if text:
                break
        except Exception:
            continue
    if not text:
        return items

    # パース
    import re as _re
    for line in text.splitlines():
        m = _re.match(r"^\s*(\d+)[.\)]\s*(.+)$", line.strip())
        if m:
            n = int(m.group(1)) - 1
            if 0 <= n < len(items):
                parts = m.group(2).split("／")
                if len(parts) >= 2:
                    items[n]["title_ja"] = parts[0].strip()
                    items[n]["ai_comment_ja"] = parts[1].strip()[:80]
                else:
                    items[n]["title_ja"] = m.group(2).strip()
                    items[n]["ai_comment_ja"] = ""
    return items


def send_alert_email(new_high_items):
    """新規 HIGH 発言があればメール送信"""
    sender = os.environ.get("GMAIL_USER", "")
    password = os.environ.get("GMAIL_APP_PASSWORD", "")
    recipient = os.environ.get("ALERT_RECIPIENT", "")
    if not (sender and password and recipient):
        print("  ⚠️ メール認証情報未設定、送信スキップ")
        return
    if not new_high_items:
        return

    top = new_high_items[0]
    top_title = top.get("title_ja") or top.get("title_en", "")
    subject = f"🚨 政治速報 [{len(new_high_items)}件]: {top_title[:40]}"

    body_lines = [
        "━━━━━━━━━━━━━━━━━━━━━",
        "🚨 政治発言ライブフィード - HIGH 速報",
        f"検知時刻: {datetime.now(JST).strftime('%Y-%m-%d %H:%M JST')}",
        "━━━━━━━━━━━━━━━━━━━━━",
        "",
    ]
    for it in new_high_items[:10]:
        body_lines.append(f"【{it['importance']}】 {it.get('title_ja') or it['title_en']}")
        if it.get("title_ja") and it.get("title_en"):
            body_lines.append(f"  📰 原文: {it['title_en'][:120]}")
        if it.get("ai_comment_ja"):
            body_lines.append(f"  💡 {it['ai_comment_ja']}")
        if it.get("affected_assets"):
            body_lines.append(f"  📊 影響: {', '.join(it['affected_assets'])}")
        body_lines.append(f"  🔗 {it.get('url', '')}")
        body_lines.append(f"  発信: {it.get('source', '')} / 発表 {(it.get('published_at') or '')[:16]}")
        body_lines.append("")
    body_lines.append("━━━━━━━━━━━━━━━━━━━━━")
    body_lines.append("📊 ライブフィード: https://marketwatch-jp.com/political-feed.html")
    body_lines.append("━━━━━━━━━━━━━━━━━━━━━")
    body_lines.append("MarketWatch AI Political Alerts")

    body = "\n".join(body_lines)

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg.attach(MIMEText(body, "plain", "utf-8"))
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as server:
            server.login(sender, password)
            server.sendmail(sender, [recipient], msg.as_string())
        print(f"  📧 メール送信完了: {recipient} ({len(new_high_items)} 件)")
    except Exception as e:
        print(f"  ❌ メール送信失敗: {type(e).__name__}: {str(e)[:80]}")


def main():
    print(f"📡 政治発言フィード収集 {datetime.now(JST).strftime('%Y-%m-%d %H:%M JST')}")

    api_key_news = os.environ.get("NEWSAPI_KEY", "")
    api_key_gemini = os.environ.get("GEMINI_API_KEY", "")
    no_email = "--no-email" in sys.argv or os.environ.get("NO_EMAIL", "").lower() in ("1", "true")

    # 既存 feed を読み込み（重複排除用）
    existing = []
    existing_ids = set()
    if os.path.exists(FEED_FILE):
        try:
            existing = json.load(open(FEED_FILE, encoding="utf-8"))
            existing_ids = {it.get("id") for it in existing if it.get("id")}
        except Exception:
            existing = []
    print(f"  📂 既存フィード: {len(existing)} 件")

    # 過去 6 時間以内の記事を対象（workflow 30 分間隔の余裕）
    since_dt = datetime.now(timezone.utc) - timedelta(hours=6)
    since_iso = since_dt.strftime("%Y-%m-%dT%H:%M:%S")

    new_items = []

    # === NEWS API ===
    if api_key_news:
        print(f"  📰 NEWS API: {len(POLITICAL_QUERIES)} クエリ実行中...")
        for query, assets in POLITICAL_QUERIES:
            articles = fetch_newsapi_political(api_key_news, query, since_iso)
            for a in articles:
                url = a.get("url", "")
                title_en = a.get("title", "")
                pub = a.get("publishedAt", "")
                src = (a.get("source") or {}).get("name", "NewsAPI")
                if not (title_en and url):
                    continue
                item_id = make_id(src, url, pub)
                if item_id in existing_ids:
                    continue
                importance = calc_importance(title_en, src)
                new_items.append({
                    "id": item_id,
                    "source": src,
                    "source_type": "newsapi",
                    "matched_query": query,
                    "fetched_at": _now_iso(),
                    "published_at": pub,
                    "title_en": title_en,
                    "title_ja": "",
                    "url": url,
                    "importance": importance,
                    "affected_assets": assets,
                    "ai_comment_ja": "",
                })
                existing_ids.add(item_id)
    else:
        print("  ⚠️ NEWSAPI_KEY 未設定、NEWS API クエリをスキップ")

    # === WhiteHouse 公式 RSS ===
    print(f"  🏛️  WhiteHouse RSS: {len(WHITEHOUSE_FEEDS)} フィード取得中...")
    for feed_url in WHITEHOUSE_FEEDS:
        wh_items = fetch_whitehouse_rss(feed_url)
        for a in wh_items:
            url = a.get("url", "")
            title_en = a.get("title", "")
            pub = a.get("publishedAt", "")
            if not (title_en and url):
                continue
            item_id = make_id("WhiteHouse", url, pub)
            if item_id in existing_ids:
                continue
            importance = calc_importance(title_en, "WhiteHouse")
            # WhiteHouse は政府公式なので最低 MID 扱い
            if importance == "LOW":
                importance = "MID"
            new_items.append({
                "id": item_id,
                "source": "WhiteHouse 公式",
                "source_type": "whitehouse_rss",
                "matched_query": feed_url.rstrip("/").split("/")[-2] if "/" in feed_url else "whitehouse",
                "fetched_at": _now_iso(),
                "published_at": pub,
                "title_en": title_en,
                "title_ja": "",
                "url": url,
                "importance": importance,
                "affected_assets": ["all"],
                "ai_comment_ja": "",
            })
            existing_ids.add(item_id)

    print(f"  📥 新規発言: {len(new_items)} 件")

    # Gemini で一括日本語化 + 一言コメント
    if new_items and api_key_gemini:
        print(f"  🌐 Gemini で {len(new_items)} 件を翻訳・コメント生成中...")
        new_items = translate_and_comment_jp(new_items, api_key_gemini)

    # マージ → 最新 N 件キープ（published_at 降順）
    all_items = new_items + existing
    all_items.sort(key=lambda x: x.get("published_at") or "", reverse=True)
    all_items = all_items[:MAX_KEEP]

    with open(FEED_FILE, "w", encoding="utf-8") as f:
        json.dump(all_items, f, ensure_ascii=False, indent=2)
    print(f"  ✅ {FEED_FILE} 保存: {len(all_items)} 件（最大 {MAX_KEEP} キープ）")

    # 重要度カウント
    high_n = sum(1 for it in new_items if it["importance"] == "HIGH")
    mid_n = sum(1 for it in new_items if it["importance"] == "MID")
    low_n = sum(1 for it in new_items if it["importance"] == "LOW")
    print(f"  🚨 新規 HIGH: {high_n} / MID: {mid_n} / LOW: {low_n}")

    # HIGH 発言だけメール送信
    new_high = [it for it in new_items if it["importance"] == "HIGH"]
    if no_email:
        print(f"  🔇 メール送信スキップ (--no-email)。送信予定だった HIGH: {len(new_high)} 件")
    elif new_high:
        send_alert_email(new_high)
    else:
        print(f"  ℹ️  HIGH 発言なし、メール送信なし")


if __name__ == "__main__":
    main()
