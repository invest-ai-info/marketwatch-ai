"""
毎朝マーケットニュース自動生成スクリプト（歴史的イベント年表付き）
yfinance で価格データ取得、Chart.js でチャート表示
"""

import yfinance as yf
import json
import os
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta

# 翻訳関数（複数バックエンド + 既に日本語ならスキップ + 失敗時ログ）
import re as _re_for_ja
_HAS_JA_RE = _re_for_ja.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')

def translate_to_ja(text):
    """英文タイトルを日本語に翻訳。失敗時は原文を返すが console にログを残す。"""
    if not text or not str(text).strip():
        return text
    # 既に日本語が含まれていれば翻訳不要
    if _HAS_JA_RE.search(text):
        return text

    src = str(text).strip()[:4500]  # 5000字制限の保険

    # ① Google 翻訳（deep_translator）
    try:
        from deep_translator import GoogleTranslator
        out = GoogleTranslator(source="auto", target="ja").translate(src)
        if out and out.strip() and out.strip().lower() != src.strip().lower():
            return out
        else:
            print(f"  ⚠️ GoogleTranslator: 空または無変換 → fallback")
    except Exception as e:
        print(f"  ⚠️ GoogleTranslator 失敗: {e} → fallback")

    # ② MyMemory フォールバック
    try:
        from deep_translator import MyMemoryTranslator
        out = MyMemoryTranslator(source="en-US", target="ja-JP").translate(src[:480])
        if out and out.strip():
            return out
    except Exception as e:
        print(f"  ⚠️ MyMemoryTranslator 失敗: {e}")

    # ③ 全部失敗 → 原文（最低限ニュース内容は伝わる）
    return text

JST = timezone(timedelta(hours=9))

# ─────────────────────────────────────────
# Google Analytics 4 タグ（全ページ共通で <head> に挿入）
# ─────────────────────────────────────────
GA4_MEASUREMENT_ID = "G-FMVFEV7Q2E"
GA4_TAG = f"""<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id={GA4_MEASUREMENT_ID}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', '{GA4_MEASUREMENT_ID}');
</script>"""

# ─────────────────────────────────────────
# SEO 共通定数 / ヘルパー
#   - 各ページの <head> に title/description/canonical/OGP/Twitter/JSON-LD を出力
#   - GitHub Pages の URL 構造に合わせる
# ─────────────────────────────────────────
SITE_NAME = "MarketWatch AI"
SITE_TAGLINE = "日本人投資家のためのマーケット情報サイト"
BASE_URL = "https://marketwatch-jp.com/"
OG_IMAGE = BASE_URL + "og-image.png"  # 後で画像設置可。当面は無くても致命傷ではない

def seo_head(slug: str, title: str, description: str, og_type: str = "website") -> str:
    """ページごとの SEO 用 <head> 要素を返す。

    slug: "" なら index、それ以外は "vix.html" 等のファイル名
    title: ページタイトル（"〜 - MarketWatch AI" の "〜" 部分）
    description: 100〜160 文字程度の要約。検索結果スニペットに出る
    og_type: "website" / "article" など
    """
    canonical = BASE_URL + slug
    full_title = f"{title} | {SITE_NAME}"
    # description はクォート崩しを避けるため簡易にエスケープ
    desc = description.replace('"', '&quot;')
    json_ld = (
        '{'
        '"@context":"https://schema.org",'
        '"@type":"WebSite",'
        f'"name":"{SITE_NAME}",'
        f'"url":"{BASE_URL}",'
        f'"description":"{SITE_TAGLINE}",'
        '"inLanguage":"ja-JP"'
        '}'
    )
    return f"""<title>{full_title}</title>
  <meta name="description" content="{desc}">
  <meta name="robots" content="index,follow">
  <meta name="author" content="{SITE_NAME}">
  <link rel="canonical" href="{canonical}">
  <meta property="og:type" content="{og_type}">
  <meta property="og:site_name" content="{SITE_NAME}">
  <meta property="og:title" content="{full_title}">
  <meta property="og:description" content="{desc}">
  <meta property="og:url" content="{canonical}">
  <meta property="og:locale" content="ja_JP">
  <meta property="og:image" content="{OG_IMAGE}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{full_title}">
  <meta name="twitter:description" content="{desc}">
  <meta name="twitter:image" content="{OG_IMAGE}">
  <script type="application/ld+json">{json_ld}</script>"""


def build_sitemap_xml(now_jst) -> str:
    """全ページの sitemap.xml を生成。lastmod は実行時刻 (JST)。"""
    lastmod = now_jst.strftime("%Y-%m-%dT%H:%M:%S+09:00")
    pages = [
        ("",                    "1.0", "hourly"),
        ("preview.html",        "0.9", "daily"),
        ("vix.html",            "0.9", "daily"),
        ("market-health.html",  "0.9", "daily"),
        ("hot-assets.html",     "0.9", "daily"),
        ("calendar.html",       "0.8", "daily"),
        ("charts.html",         "0.7", "weekly"),
        ("about.html",          "0.5", "monthly"),
        ("privacy.html",        "0.4", "monthly"),
        ("contact.html",        "0.4", "monthly"),
        ("guide-vix.html",              "0.7", "monthly"),
        ("guide-buffett-indicator.html","0.7", "monthly"),
        ("guide-fear-greed.html",       "0.7", "monthly"),
        ("guide-fomc.html",             "0.8", "monthly"),
        ("guide-us-gdp.html",           "0.8", "monthly"),
        ("guide-jpy-intervention-2026-04.html","0.95","daily"),
        ("guide-fomc-2026-04.html",     "0.9", "weekly"),
        ("guide-boj-2026-04.html",      "0.9", "weekly"),
        ("guide-nikkei-60000.html",     "0.9", "weekly"),
        ("guides.html",                 "0.8", "weekly"),
    ]
    urls = "\n".join(
        f"  <url>\n"
        f"    <loc>{BASE_URL}{slug}</loc>\n"
        f"    <lastmod>{lastmod}</lastmod>\n"
        f"    <changefreq>{cf}</changefreq>\n"
        f"    <priority>{pri}</priority>\n"
        f"  </url>"
        for slug, pri, cf in pages
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{urls}\n"
        "</urlset>\n"
    )


def build_robots_txt() -> str:
    """robots.txt — 全許可 + sitemap 位置を明示。"""
    return (
        "User-agent: *\n"
        "Allow: /\n"
        f"Sitemap: {BASE_URL}sitemap.xml\n"
    )

# ─────────────────────────────────────────
# 歴史的イベントデータ（1971〜）
# ─────────────────────────────────────────
HISTORICAL_EVENTS = [
    {"date": "1971-08", "label": "ニクソンショック",       "desc": "米ドルと金の兌換停止。変動相場制へ移行。ドル円が急落し360円台から100円台への長期円高が始まった。",           "assets": ["usdjpy", "gold"]},
    {"date": "1973-11", "label": "第一次オイルショック",   "desc": "OAPEC原油禁輸。原油価格が約4倍に急騰。世界的インフレと株安を引き起こした。",                            "assets": ["nikkei", "sp500", "gold"]},
    {"date": "1979-02", "label": "第二次オイルショック",   "desc": "イラン革命で原油供給が激減。原油価格が再び急騰し世界経済を直撃した。",                                   "assets": ["nikkei", "sp500", "gold"]},
    {"date": "1985-09", "label": "プラザ合意",             "desc": "G5がドル高是正で合意。ドル円が240円台から120円台へと急落する大規模な円高が進行した。",                    "assets": ["usdjpy", "nikkei"]},
    {"date": "1987-10", "label": "ブラックマンデー",       "desc": "ニューヨーク株式市場で1日に22.6%の暴落。世界同時株安となり日経平均も翌日約15%下落した。",               "assets": ["nikkei", "sp500"]},
    {"date": "1990-01", "label": "日本バブル崩壊",         "desc": "日経平均が38,915円のピークから急落開始。失われた30年の始まりとなった歴史的な大暴落。",                    "assets": ["nikkei"]},
    {"date": "1995-01", "label": "阪神大震災・円高",       "desc": "阪神淡路大震災後に円が急騰し1ドル=79円台の史上最高値を記録。日経平均も急落した。",                        "assets": ["nikkei", "usdjpy"]},
    {"date": "1997-07", "label": "アジア通貨危機",         "desc": "タイバーツ暴落から始まったアジア通貨危機が日本の金融機関にも波及。山一証券など相次いで破綻した。",          "assets": ["nikkei", "usdjpy"]},
    {"date": "1998-08", "label": "ロシア財政危機/LTCM",   "desc": "ロシアがデフォルト宣言。ヘッジファンドLTCM破綻。世界的な信用収縮とドル安・円高が加速した。",              "assets": ["nikkei", "sp500", "usdjpy"]},
    {"date": "2000-03", "label": "ITバブル崩壊",           "desc": "NASDAQが5,048の最高値から急落。ITバブルが崩壊し2002年まで世界的な株安が続いた。",                       "assets": ["nikkei", "sp500"]},
    {"date": "2001-09", "label": "9.11テロ",               "desc": "米同時多発テロ。ニューヨーク市場が1週間閉鎖。再開後に株価が急落し金が安全資産として買われた。",            "assets": ["nikkei", "sp500", "gold"]},
    {"date": "2003-03", "label": "イラク戦争",             "desc": "米英軍がイラク侵攻を開始。地政学リスクが高まり原油・金価格が乱高下した。",                               "assets": ["gold", "nikkei"]},
    {"date": "2008-09", "label": "リーマンショック",       "desc": "リーマン・ブラザーズ経営破綻で世界金融危機が勃発。日経平均はピークから約60%、S&P500は約57%下落した。",   "assets": ["nikkei", "sp500", "usdjpy", "gold"]},
    {"date": "2010-05", "label": "欧州債務危機",           "desc": "ギリシャ財政危機が欧州全体に波及。ユーロが急落し世界的なリスクオフの動きが強まった。",                    "assets": ["nikkei", "sp500", "gold"]},
    {"date": "2011-03", "label": "東日本大震災",           "desc": "東日本大震災・福島原発事故。日経平均が約20%急落し円が急騰。一時1ドル=76円台の超円高を記録した。",        "assets": ["nikkei", "usdjpy"]},
    {"date": "2013-04", "label": "アベノミクス/異次元緩和","desc": "日銀が異次元金融緩和を発表。円安・株高が一気に加速し日経平均は約2年で倍増した。",                        "assets": ["nikkei", "usdjpy"]},
    {"date": "2015-08", "label": "チャイナショック",       "desc": "中国株式市場の急落が世界に波及。VIX指数が急騰し日経平均は1週間で約11%下落した。",                        "assets": ["nikkei", "sp500"]},
    {"date": "2016-06", "label": "Brexit国民投票",         "desc": "英国がEU離脱を決定。ポンドが急落し世界株安・円高が進行。市場の想定外の結果に衝撃が走った。",             "assets": ["nikkei", "sp500", "gold"]},
    {"date": "2016-11", "label": "トランプ大統領当選",     "desc": "トランプ当選後に「トランプラリー」が発生。米株・ドル高・日本株が大きく上昇した。",                        "assets": ["nikkei", "sp500", "usdjpy"]},
    {"date": "2018-12", "label": "米中貿易戦争",           "desc": "米中貿易摩擦が激化。S&P500が年末にかけて約20%急落し世界の株式市場が動揺した。",                          "assets": ["nikkei", "sp500"]},
    {"date": "2020-02", "label": "コロナショック",         "desc": "新型コロナパンデミック宣言。世界の株式市場が約1ヶ月で30〜40%急落。史上最速の弱気相場入りとなった。",      "assets": ["nikkei", "sp500", "usdjpy", "gold"]},
    {"date": "2022-02", "label": "ロシア・ウクライナ侵攻", "desc": "ロシアがウクライナに軍事侵攻。原油・天然ガス・金価格が急騰し世界的なインフレ加速の引き金となった。",       "assets": ["nikkei", "sp500", "gold"]},
    {"date": "2022-03", "label": "FRB急速利上げ開始",     "desc": "FRBがゼロ金利政策を終了し急速な利上げを開始。債券・株式が同時下落し円は対ドルで30年ぶりの円安に。",      "assets": ["nikkei", "sp500", "usdjpy", "gold"]},
    {"date": "2023-03", "label": "SVB破綻",               "desc": "シリコンバレーバンク破綻。米地銀への信用不安が拡大。金が安全資産として急騰した。",                        "assets": ["nikkei", "sp500", "gold"]},
    {"date": "2024-08", "label": "日経平均歴史的暴落",     "desc": "日経平均が1日で-4,451円（-12.4%）の歴史的暴落。円キャリートレード巻き戻しで円が急騰した。",              "assets": ["nikkei", "usdjpy"]},
]

# ─────────────────────────────────────────
# データ取得関数
# ─────────────────────────────────────────
def get_price(ticker_symbol):
    """直近終値・前日比を取得。
    短期間 period では yfinance が 0〜1 行しか返さないことがある（特に ^N225 等の
    アジア指数 / 市場クローズ直後）。空なら段階的に期間を広げてリトライする。
    """
    last_err = None
    for period in ("2d", "5d", "1mo"):
        try:
            t = yf.Ticker(ticker_symbol)
            hist = t.history(period=period)
            # NaN を落としてから判定
            closes = hist["Close"].dropna() if not hist.empty else None
            if closes is not None and len(closes) >= 2:
                prev = float(closes.iloc[-2])
                last = float(closes.iloc[-1])
                if prev == 0:
                    continue
                return last, prev, (last - prev) / prev * 100
        except Exception as e:
            last_err = e
            continue
    if last_err:
        print(f"  ⚠️ get_price({ticker_symbol}) 全期間で取得失敗: {last_err}")
    return None, None, None

def get_historical_monthly(ticker, start="1975-01-01"):
    """年次の歴史的価格データを取得（軽量化のため年次に集約）"""
    try:
        t = yf.Ticker(ticker)
        hist = t.history(start=start)
        if hist.empty:
            return [], []
        # 年次データ（各年末の終値）に集約 → 約50点で軽量
        yearly = hist["Close"].resample("YE").last().dropna()
        dates  = [d.strftime("%Y") for d in yearly.index]
        prices = [round(float(v), 2) for v in yearly.values]
        return dates, prices
    except Exception:
        return [], []

def get_touraku_ratio():
    """騰落レシオ（25日）を取得する
    東証プライム全銘柄の値上がり/値下がりを25日分集計して算出。
    nikkei225jp.comからスクレイピングを試み、失敗時はyfinanceで近似計算。
    """
    # 方法1: Webから取得を試みる
    try:
        url = "https://nikkei225jp.com/data/touraku.php"
        req = urllib.request.Request(url, headers={"User-Agent": "MarketWatch/1.0"})
        with urllib.request.urlopen(req, timeout=10) as res:
            html = res.read().decode("utf-8", errors="replace")
        # テーブルから騰落レシオ（25日）を抽出
        import re
        # 25日騰落レシオの値を探す
        m = re.search(r'25日[^<]*</t[dh]>\s*<td[^>]*>\s*([\d.]+)', html)
        if m:
            val = float(m.group(1))
            print(f"  騰落レシオ(Web): {val}")
            return val
    except Exception as e:
        print(f"  騰落レシオWeb取得失敗: {e}")

    # 方法2: yfinanceでTOPIX ETF (1306.T) の25日データから近似計算
    try:
        t = yf.Ticker("1306.T")
        hist = t.history(period="40d")
        if len(hist) >= 26:
            closes = hist["Close"].values
            changes = [closes[i] - closes[i-1] for i in range(1, len(closes))]
            recent = changes[-25:]
            ups = sum(1 for c in recent if c > 0)
            downs = sum(1 for c in recent if c < 0)
            if downs > 0:
                ratio = (ups / downs) * 100
            else:
                ratio = 999.0
            print(f"  騰落レシオ(近似): {ratio:.1f}")
            return round(ratio, 1)
    except Exception as e:
        print(f"  騰落レシオ近似計算失敗: {e}")

    return None


def analyze_touraku(ratio):
    """騰落レシオの水準を分析してコメントを返す"""
    if ratio is None:
        return "N/A", "#6e7781", "😐", "データを取得できませんでした。"
    if ratio >= 140:
        return "過熱圏", "#da3633", "😢", f"騰落レシオ {ratio:.0f}%：市場は過熱状態です。短期的な調整（下落）に警戒が必要です。"
    elif ratio >= 120:
        return "買われすぎ", "#bf3989", "😐", f"騰落レシオ {ratio:.0f}%：やや買われすぎの水準。利益確定売りが出やすい局面です。"
    elif ratio >= 80:
        return "通常", "#1a7f37", "😊", f"騰落レシオ {ratio:.0f}%：通常の範囲内。市場は安定しています。"
    elif ratio >= 60:
        return "売られすぎ", "#9a6700", "😐", f"騰落レシオ {ratio:.0f}%：やや売られすぎの水準。反発のきっかけ待ちです。"
    else:
        return "底値圏", "#238636", "😊", f"騰落レシオ {ratio:.0f}%：歴史的な底値圏です。長期投資家にとっては買いのチャンスかもしれません。"


def fmt_price(val, decimals=2, prefix="", suffix=""):
    if val is None:
        return "N/A"
    return f"{prefix}{val:,.{decimals}f}{suffix}"

def fmt_change(pct):
    if pct is None:
        return ""
    sign = "▲" if pct >= 0 else "▼"
    cls  = "up" if pct >= 0 else "down"
    icon = "😊" if pct > 0 else "😢"
    return f'<span class="{cls} price-change">{icon}{sign}{abs(pct):.2f}%</span>'

def sentiment(changes):
    ups   = sum(1 for c in changes if c and c > 0)
    downs = sum(1 for c in changes if c and c < 0)
    if ups > downs:
        return "やや強気", "#238636", "😊"
    elif downs > ups:
        return "やや弱気", "#da3633", "😢"
    return "中立", "#9e6a03", "😐"

# ─────────────────────────────────────────
# NewsAPI.org ニュース取得
# ─────────────────────────────────────────
NEWS_CATEGORIES = {
    "top":       ["stock market finance economy today"],
    "stocks":    ["stock market Wall Street equities shares"],
    "fx":        ["forex dollar yen currency exchange rate"],
    "commodity": ["oil gold commodity WTI crude precious metals"],
    "crypto":    ["bitcoin ethereum crypto blockchain BTC ETH"],
}

# カテゴリ毎のyfinanceティッカー（news属性がある銘柄）
YF_NEWS_TICKERS = {
    "top":       ["^GSPC", "^N225", "^DJI"],       # 主要株価指数
    "stocks":    ["^GSPC", "^N225", "AAPL", "MSFT"],
    "fx":        ["JPY=X", "EURUSD=X", "EURJPY=X"],
    "commodity": ["GC=F", "CL=F", "SI=F"],          # 金/原油/銀
    "crypto":    ["BTC-USD", "ETH-USD"],
}


def fetch_yf_news_for_category(tickers):
    """yfinance.Ticker(X).news を複数銘柄から集約して取得"""
    articles = []
    for sym in tickers:
        try:
            news = yf.Ticker(sym).news or []
        except Exception as e:
            print(f"⚠️ yfinance news取得エラー ({sym}): {e}")
            continue
        for n in news:
            # yfinanceのnews形式に対応（新旧両方サポート）
            content = n.get("content", n)  # 新形式は content キーにネスト
            title = content.get("title", "") or n.get("title", "")
            if not title:
                continue
            # URL抽出（新旧両対応）
            url = ""
            if isinstance(content.get("canonicalUrl"), dict):
                url = content["canonicalUrl"].get("url", "")
            elif isinstance(content.get("clickThroughUrl"), dict):
                url = content["clickThroughUrl"].get("url", "")
            url = url or n.get("link", "") or "#"
            # 発行日時（UNIXタイムスタンプ or ISO形式）
            pub = ""
            if "pubDate" in content:
                pub = content["pubDate"][:10]  # ISO形式
            elif "providerPublishTime" in n:
                pub = datetime.fromtimestamp(n["providerPublishTime"], tz=timezone.utc).strftime("%Y-%m-%d")
            # ソース名
            source = ""
            if isinstance(content.get("provider"), dict):
                source = content["provider"].get("displayName", "")
            source = source or n.get("publisher", "Yahoo Finance")

            articles.append({
                "title": title,
                "description": content.get("summary", "") or n.get("summary", ""),
                "source": source,
                "url": url,
                "publishedAt": pub,
            })
    return articles


def fetch_newsapi_articles(api_key, q, lang, from_date):
    """NewsAPI.org から記事を取得（フォールバック用）"""
    params = urllib.parse.urlencode({
        "q": q, "language": lang, "sortBy": "publishedAt",
        "from": from_date, "pageSize": 10, "apiKey": api_key,
    })
    url = f"https://newsapi.org/v2/everything?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": "MarketWatch/1.0"})
    with urllib.request.urlopen(req, timeout=10) as res:
        data = json.loads(res.read())
        return [{
            "title": a.get("title", ""),
            "description": a.get("description", "") or "",
            "source": a.get("source", {}).get("name", ""),
            "url": a.get("url", "#"),
            "publishedAt": a.get("publishedAt", "")[:10],
        } for a in data.get("articles", [])]


def fetch_news(api_key):
    """ニュース取得（yfinance優先 + NewsAPIフォールバック）"""
    from_date = (datetime.now(timezone.utc) - timedelta(days=3)).strftime("%Y-%m-%d")
    results = {}

    for cat, queries in NEWS_CATEGORIES.items():
        articles = []

        # ① yfinanceから取得（最新・無遅延）
        yf_tickers = YF_NEWS_TICKERS.get(cat, [])
        try:
            articles.extend(fetch_yf_news_for_category(yf_tickers))
        except Exception as e:
            print(f"⚠️ yfinance news集約エラー ({cat}): {e}")

        # ② NewsAPIから取得（補完・api_keyがあれば）
        if api_key:
            for q in queries:
                try:
                    articles.extend(fetch_newsapi_articles(api_key, q, "en", from_date))
                except Exception as e:
                    print(f"⚠️ NewsAPI取得エラー ({cat}/{q}): {e}")

        # ③ 重複除去（URL基準）、日付で新しい順にソート
        seen = set()
        unique = []
        for a in articles:
            key = a.get("url") or a.get("title")
            if key and key not in seen and "[Removed]" not in a.get("title", ""):
                seen.add(key)
                unique.append(a)
        unique.sort(key=lambda x: x.get("publishedAt", ""), reverse=True)

        # ④ 上位3件を日本語に翻訳（rate limit回避で軽くsleep）
        import time as _time
        top3 = unique[:3]
        for a in top3:
            original = a["title"]
            a["title"] = translate_to_ja(original)
            if a["title"] != original:
                print(f"  ✅ 翻訳: {original[:40]}... → {a['title'][:40]}...")
            _time.sleep(0.4)
        results[cat] = top3

    return results


def build_annotations(asset_key, dates):
    """指定アセットに関するイベントのChart.jsアノテーションを生成"""
    anns = {}
    date_set = set(dates)
    for i, ev in enumerate(HISTORICAL_EVENTS):
        if asset_key not in ev["assets"]:
            continue
        # 年次データに含まれる年を探す（イベント日付の年以降の最初の年）
        ev_year = ev["date"][:4]
        target = next((d for d in dates if d >= ev_year), None)
        if target is None:
            continue
        key = f"ev{i}"
        anns[key] = {
            "type": "line",
            "xMin": target,
            "xMax": target,
            "borderColor": "rgba(255, 193, 7, 0.7)",
            "borderWidth": 1.5,
            "borderDash": [4, 3],
            "label": {
                "content": ev["label"],
                "display": False,
                "backgroundColor": "rgba(30,30,40,0.95)",
                "color": "#9a6700",
                "font": {"size": 11},
                "padding": 6,
                "position": "start",
            },
            "enter": {"label": {"display": True}},
            "leave": {"label": {"display": False}},
        }
    return anns

# ─────────────────────────────────────────
# ニュースセンチメント判定
# ─────────────────────────────────────────
_POS_WORDS = {
    "surge","soar","rally","gain","rise","jump","record","high","bull","boom",
    "optimis","recover","upbeat","breakout","profit","beat","strong","best",
    "上昇","急騰","高値","最高","好調","回復","強気","続伸","反発","突破","増益","黒字",
}
_NEG_WORDS = {
    "crash","plunge","drop","fall","slip","tumble","low","bear","recession",
    "fear","risk","warn","crisis","collapse","loss","miss","worst","sell-off",
    "selloff","concern","threat","hack","exploit","fraud","sanction","war","attack",
    "下落","急落","安値","最安","不調","弱気","暴落","続落","損失","赤字","破綻","懸念",
    "危機","脅威","制裁","攻撃","流出",
}

def classify_news_sentiment(title, description=""):
    """キーワードベースでポジ/ネガ/中立を判定。 (icon, css_class) を返す"""
    text = (title + " " + (description or "")).lower()
    pos = sum(1 for w in _POS_WORDS if w in text)
    neg = sum(1 for w in _NEG_WORDS if w in text)
    if pos > neg:
        return "😊", "sent-pos"
    elif neg > pos:
        return "😢", "sent-neg"
    return "😐", "sent-neu"

# ─────────────────────────────────────────
# HTML生成
# ─────────────────────────────────────────
def build_news_html(articles, limit=3):
    """ニュース記事リストをHTML文字列に変換（センチメントアイコン付き）"""
    if not articles:
        return '<div class="news-empty">ニュースを取得できませんでした</div>'
    html = ""
    for a in articles[:limit]:
        source = a.get("source", "")
        title = a.get("title", "").replace("{", "").replace("}", "")
        desc = a.get("description", "")
        url = a.get("url", "#")
        pub = a.get("publishedAt", "")[:10]
        icon, cls = classify_news_sentiment(title, desc)
        html += f'''<a class="news-item" href="{url}" target="_blank" rel="noopener">
          <span class="news-title"><span class="news-sent {cls}">{icon}</span> {title}</span>
          <span class="news-meta">{source} · {pub}</span>
        </a>'''
    return html


# ─────────────────────────────────────────
# VIX（恐怖指数）分析
# ─────────────────────────────────────────
def get_vix_history(days=90):
    """VIXの直近データを取得"""
    try:
        t = yf.Ticker("^VIX")
        hist = t.history(period=f"{days}d")
        if hist.empty:
            return [], []
        dates  = [d.strftime("%Y-%m-%d") for d in hist.index]
        prices = [round(float(v), 2) for v in hist["Close"].values]
        return dates, prices
    except Exception:
        return [], []

def analyze_vix(current, prev=None, hist_prices=None):
    """VIX値から市場の恐怖レベルを分析しコメントを生成"""
    if current is None:
        return "N/A", "#6e7781", "😐", "データを取得できませんでした。", ""

    # レベル判定
    if current < 12:
        level    = "極めて低い"
        color    = "#238636"
        icon     = "😊"
        mood     = "市場は非常に楽観的"
        warning  = "ただし、過度な楽観は相場の転換点を示唆することがあります。「みんなが安心しているときこそ注意」という格言もあります。"
    elif current < 20:
        level    = "平常"
        color    = "#1a7f37"
        icon     = "😊"
        mood     = "市場は落ち着いている"
        warning  = "通常の市場環境です。長期投資家にとっては安定した投資環境といえます。"
    elif current < 25:
        level    = "やや高い"
        color    = "#9a6700"
        icon     = "😐"
        mood     = "市場にやや緊張感あり"
        warning  = "不確実性が高まっています。ポートフォリオの分散やリスク管理を意識しましょう。"
    elif current < 30:
        level    = "高い"
        color    = "#bf3989"
        icon     = "😢"
        mood     = "市場は不安を感じている"
        warning  = "恐怖が広がっています。パニック売りは避け、冷静に判断することが大切です。逆張り投資家にとってはチャンスの兆しかもしれません。"
    elif current < 40:
        level    = "非常に高い"
        color    = "#cf222e"
        icon     = "😢"
        mood     = "市場は強い恐怖に包まれている"
        warning  = "歴史的に見て、VIXが30を超える局面は長くは続きません。パニックに乗らず、中長期の視点で判断しましょう。"
    else:
        level    = "パニック水準"
        color    = "#da3633"
        icon     = "😢"
        mood     = "市場は極度のパニック状態"
        warning  = "リーマンショックやコロナショック級の恐怖です。歴史的に、この水準からの反発は大きい傾向がありますが、下落がさらに続く可能性もあります。"

    # 前日比コメント
    trend = ""
    if prev is not None:
        diff = current - prev
        if diff > 2:
            trend = f"前日比 +{diff:.1f}pt と急上昇しており、恐怖が急速に広がっています。"
        elif diff > 0:
            trend = f"前日比 +{diff:.1f}pt とやや上昇。警戒感がじわじわ高まっています。"
        elif diff < -2:
            trend = f"前日比 {diff:.1f}pt と急低下。安心感が戻りつつあります。"
        elif diff < 0:
            trend = f"前日比 {diff:.1f}pt とやや低下。市場の緊張が和らいでいます。"
        else:
            trend = "前日とほぼ変わらず。様子見ムードです。"

    # 90日レンジ
    range_comment = ""
    if hist_prices and len(hist_prices) > 5:
        hi = max(hist_prices)
        lo = min(hist_prices)
        avg = sum(hist_prices) / len(hist_prices)
        range_comment = f"直近90日の範囲は {lo:.1f}〜{hi:.1f}（平均 {avg:.1f}）。"
        if current > avg * 1.3:
            range_comment += "平均を大きく上回っており、市場のストレスが高い状態です。"
        elif current < avg * 0.7:
            range_comment += "平均を大きく下回っており、市場は過度に楽観的な可能性があります。"
        else:
            range_comment += "平均的な水準で推移しています。"

    comment = f"VIXは現在 {current:.1f} で、恐怖レベルは「{level}」です。{mood}。{trend} {range_comment} {warning}"
    return level, color, icon, comment, mood


def build_vix_html(vix_val, vix_prev, vix_dates, vix_prices, now_jst):
    """VIX（恐怖指数）専用ページを生成"""
    time_str = now_jst.strftime("%Y年%#m月%#d日 %H:%M JST") if os.name == "nt" else now_jst.strftime("%Y年%-m月%-d日 %H:%M JST")

    level, color, icon, comment, mood = analyze_vix(vix_val, vix_prev, vix_prices)

    vix_display = f"{vix_val:.1f}" if vix_val is not None else "N/A"
    chg_html = ""
    if vix_val is not None and vix_prev is not None:
        diff = vix_val - vix_prev
        chg_pct = diff / vix_prev * 100
        sign = "+" if diff >= 0 else ""
        cls = "down" if diff >= 0 else "up"  # VIX上昇=ネガティブ
        chg_html = f'<span class="{cls}" style="font-size:1.1rem">{sign}{diff:.2f} ({sign}{chg_pct:.1f}%)</span>'

    # ゲージ位置の計算（0-80をゲージ範囲とする）
    gauge_pct = min(max((vix_val or 0) / 80 * 100, 0), 100)

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  {seo_head("vix.html", "恐怖指数（VIX）分析", "VIX指数（恐怖指数）の最新値・90日チャート・AIコメントを毎日更新。市場心理を読み解き、暴落の予兆や買い場のヒントを日本人投資家向けに分かりやすく解説します。")}
  {GA4_TAG}
  <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
  <style>
    *{{margin:0;padding:0;box-sizing:border-box}}
    body{{font-family:'Segoe UI','Hiragino Sans','Yu Gothic',sans-serif;background:#ffffff;color:#1f2328;min-height:100vh}}
    header{{background:linear-gradient(135deg,#f6f8fa,#ffffff);border-bottom:1px solid #d0d7de;padding:24px 32px}}
    .header-inner{{max-width:1200px;margin:0 auto;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px}}
    .header-title{{font-size:1.6rem;font-weight:700;background:linear-gradient(90deg,#cf222e,#bf3989);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}
    .header-meta{{font-size:.85rem;color:#57606a}}
    .header-meta span{{color:#0969da;font-weight:600}}
    .back-link{{display:inline-flex;align-items:center;gap:6px;color:#0969da;text-decoration:none;font-size:.9rem;padding:8px 16px;border:1px solid #d0d7de;border-radius:8px;transition:background .2s}}
    .back-link:hover{{background:#f6f8fa}}
    main{{max-width:1200px;margin:0 auto;padding:32px 24px}}
    .vix-hero{{background:#f6f8fa;border:1px solid #d0d7de;border-radius:16px;padding:32px;margin-bottom:28px;text-align:center}}
    .vix-value{{font-size:4rem;font-weight:800;color:{color};line-height:1.2}}
    .vix-change{{font-size:1rem;margin-top:4px}}
    .vix-level{{font-size:1.4rem;font-weight:700;color:{color};margin-top:8px}}
    .vix-mood{{font-size:.95rem;color:#57606a;margin-top:4px}}
    .gauge{{margin:24px auto 0;max-width:500px;height:18px;background:linear-gradient(90deg,#238636 0%,#1a7f37 20%,#9a6700 40%,#bf3989 60%,#cf222e 80%,#da3633 100%);border-radius:10px;position:relative}}
    .gauge-marker{{position:absolute;top:-6px;width:4px;height:30px;background:#fff;border-radius:2px;transform:translateX(-50%);box-shadow:0 0 8px rgba(255,255,255,0.5)}}
    .gauge-labels{{display:flex;justify-content:space-between;max-width:500px;margin:6px auto 0;font-size:.7rem;color:#57606a}}
    .analysis-box{{background:#f6f8fa;border:1px solid #d0d7de;border-radius:12px;padding:24px;margin-bottom:24px}}
    .analysis-title{{font-size:1.1rem;font-weight:700;color:#1f2328;margin-bottom:12px;display:flex;align-items:center;gap:8px}}
    .analysis-text{{font-size:.92rem;color:#424a53;line-height:1.8}}
    .beginner-box{{margin-top:20px;background:#ddf4ff;border:1px solid #54aeff;border-radius:8px;padding:14px 18px;font-size:.82rem;color:#1f6feb;line-height:1.8}}
    .beginner-box::before{{content:"🔰 初心者メモ　";font-weight:700;color:#0969da}}
    .chart-section{{background:#f6f8fa;border:1px solid #d0d7de;border-radius:12px;padding:24px;margin-bottom:24px}}
    .chart-title{{font-size:1rem;font-weight:700;color:#1f2328;margin-bottom:4px}}
    .chart-subtitle{{font-size:.78rem;color:#57606a;margin-bottom:16px}}
    .chart-wrap{{position:relative;height:300px}}
    .level-table{{width:100%;border-collapse:collapse;margin-top:16px;font-size:.85rem}}
    .level-table th{{text-align:left;padding:8px 12px;border-bottom:2px solid #d0d7de;color:#57606a}}
    .level-table td{{padding:8px 12px;border-bottom:1px solid #d0d7de}}
    .level-table tr:hover td{{background:#ffffff}}
    .level-dot{{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px}}
    footer{{background:#f6f8fa;border-top:1px solid #d0d7de;padding:20px 32px;text-align:center;font-size:.78rem;color:#6e7781}}
    footer a{{color:#0969da;text-decoration:none}}
    @media(max-width:600px){{.header-inner{{flex-direction:column}}.vix-value{{font-size:3rem}}}}
  .nav-bar{{display:flex;flex-wrap:wrap;gap:10px;justify-content:center;margin-bottom:28px}}
  .nav-btn{{display:inline-flex;align-items:center;gap:8px;padding:11px 20px;background:#f6f8fa;border:1px solid #d0d7de;border-radius:10px;color:#57606a;text-decoration:none;font-size:.95rem;font-weight:600;transition:all .2s}}
  .nav-btn:hover{{border-color:#0969da;color:#0969da}}
  .nav-btn.current{{background:#0969da;border-color:#0969da;color:#fff}}
  </style>
  <!-- A8.net広告タグはここに貼る予定 -->
</head>
<body>
<header>
  <div class="header-inner">
    <div>
      <div class="header-title">😱 恐怖指数（VIX）</div>
      <div class="header-meta">最終更新: <span>{time_str}</span></div>
    </div>
  </div>
</header>
<main>

<nav class="nav-bar">
  <a class="nav-btn" href="index.html">📊 マーケットニュース</a>
  <a class="nav-btn" href="calendar.html">📅 経済カレンダー</a>
  <a class="nav-btn" href="charts.html">📈 50年チャート</a>
  <a class="nav-btn current" href="vix.html">😱 恐怖指数</a>
  <a class="nav-btn" href="market-health.html">🩺 市場健康度</a>
  <a class="nav-btn" href="hot-assets.html">🔥 出来高急増</a>
</nav>

  <div class="vix-hero">
    <div class="vix-value">{vix_display}</div>
    <div class="vix-change">{chg_html}</div>
    <div class="vix-level">{icon} {level}</div>
    <div class="vix-mood">{mood}</div>
    <div class="gauge"><div class="gauge-marker" style="left:{gauge_pct}%"></div></div>
    <div class="gauge-labels"><span>安心</span><span>平常</span><span>警戒</span><span>恐怖</span><span>パニック</span></div>
  </div>

  <div style="text-align:center;margin:18px 0 24px">
    <a href="guide-vix.html" style="display:inline-block;padding:10px 22px;background:#0969da;border:1px solid #0969da;border-radius:8px;color:#fff;text-decoration:none;font-size:.92rem;font-weight:600">📚 VIX恐怖指数とは？読み方を初心者向けに解説 →</a>
  </div>

  <div class="analysis-box">
    <div class="analysis-title">📝 AIアナリスト・コメント</div>
    <div class="analysis-text">{comment}</div>
    <div class="beginner-box">
      VIX（Volatility Index）は「恐怖指数」とも呼ばれ、S&amp;P500のオプション価格から算出される「今後30日間の市場の変動予想」です。
      数値が高いほど「投資家が大きな値動きを予想＝不安」を意味します。
      一般に20以下は平常、30超は警戒、40超はパニックとされます。
      VIXが急上昇した局面は、歴史的に見ると中長期での「買い場」になることが多いですが、短期的にはさらに下落する可能性もあるため注意が必要です。
    </div>
  </div>

  <div class="chart-section">
    <div class="chart-title">VIX 直近90日チャート</div>
    <div class="chart-subtitle">日次終値</div>
    <div class="chart-wrap"><canvas id="chartVIX"></canvas></div>
  </div>

  <div class="analysis-box">
    <div class="analysis-title">📊 VIXレベル早見表</div>
    <table class="level-table">
      <thead><tr><th>レベル</th><th>VIX範囲</th><th>意味</th><th>投資家の行動指針</th></tr></thead>
      <tbody>
        <tr><td><span class="level-dot" style="background:#238636"></span>極めて低い</td><td>0〜12</td><td>過度な楽観</td><td>上昇トレンドだが過熱に注意。利確を検討</td></tr>
        <tr><td><span class="level-dot" style="background:#1a7f37"></span>平常</td><td>12〜20</td><td>安定した市場</td><td>通常の投資判断でOK。積立投資に最適</td></tr>
        <tr><td><span class="level-dot" style="background:#9a6700"></span>やや高い</td><td>20〜25</td><td>警戒感あり</td><td>リスク管理を意識。分散投資の確認を</td></tr>
        <tr><td><span class="level-dot" style="background:#bf3989"></span>高い</td><td>25〜30</td><td>不安拡大</td><td>パニック売りは禁物。冷静な判断を</td></tr>
        <tr><td><span class="level-dot" style="background:#cf222e"></span>非常に高い</td><td>30〜40</td><td>強い恐怖</td><td>逆張りのチャンスかも。ただし慎重に</td></tr>
        <tr><td><span class="level-dot" style="background:#da3633"></span>パニック</td><td>40超</td><td>極度のパニック</td><td>歴史的買い場の可能性。ただし底は誰にもわからない</td></tr>
      </tbody>
    </table>
  </div>

</main>
<footer>
  <p>データソース: Yahoo Finance (yfinance) &nbsp;|&nbsp;
  <a href="index.html">📊 マーケットニュース</a> &nbsp;|&nbsp;
  <a href="calendar.html">📅 経済カレンダー</a> &nbsp;|&nbsp;
  <a href="charts.html">📈 50年チャート</a> &nbsp;|&nbsp;
  <a href="vix.html">😱 VIX</a> &nbsp;|&nbsp;
  <a href="market-health.html">🩺 市場健康度</a> &nbsp;|&nbsp;
  <a href="hot-assets.html">🔥 出来高急増</a> &nbsp;|&nbsp;
  本データは自動取得・表示であり、投資助言ではありません。</p>
  <p style="margin-top:8px"><a href="about.html">運営者情報</a> &nbsp;|&nbsp; <a href="privacy.html">プライバシーポリシー</a> &nbsp;|&nbsp; <a href="contact.html">お問い合わせ</a></p>
</footer>

<script>
const VIX_DATES  = {json.dumps(vix_dates)};
const VIX_PRICES = {json.dumps(vix_prices)};

if (VIX_DATES.length > 0) {{
  const ctx = document.getElementById('chartVIX').getContext('2d');
  new Chart(ctx, {{
    type: 'line',
    data: {{
      labels: VIX_DATES,
      datasets: [{{
        label: 'VIX',
        data: VIX_PRICES,
        borderColor: '#cf222e',
        backgroundColor: 'rgba(248,81,73,0.1)',
        borderWidth: 2,
        fill: true,
        pointRadius: 0,
        pointHoverRadius: 4,
        tension: 0.2,
      }}]
    }},
    options: {{
      responsive: true,
      maintainAspectRatio: false,
      plugins: {{
        legend: {{ labels: {{ color: '#1f2328' }} }},
        tooltip: {{ backgroundColor: 'rgba(22,27,34,0.95)', titleColor: '#cf222e',
                    bodyColor: '#1f2328', borderColor: '#d0d7de', borderWidth: 1 }},
        annotation: {{
          annotations: {{
            line20: {{ type: 'line', yMin: 20, yMax: 20, borderColor: 'rgba(210,153,34,0.5)', borderWidth: 1, borderDash: [6,3],
              label: {{ content: '警戒ライン (20)', display: true, position: 'end', backgroundColor: 'rgba(30,30,40,0.9)', color: '#9a6700', font: {{ size: 10 }}, padding: 4 }} }},
            line30: {{ type: 'line', yMin: 30, yMax: 30, borderColor: 'rgba(248,81,73,0.5)', borderWidth: 1, borderDash: [6,3],
              label: {{ content: '恐怖ライン (30)', display: true, position: 'end', backgroundColor: 'rgba(30,30,40,0.9)', color: '#cf222e', font: {{ size: 10 }}, padding: 4 }} }},
          }}
        }},
      }},
      scales: {{
        x: {{ ticks: {{ color: '#57606a', font: {{ size: 10 }}, maxTicksLimit: 10 }}, grid: {{ color: 'rgba(48,54,61,0.8)' }} }},
        y: {{ ticks: {{ color: '#57606a', font: {{ size: 10 }} }}, grid: {{ color: 'rgba(48,54,61,0.8)' }},
             suggestedMin: 10, suggestedMax: 50 }},
      }},
    }}
  }});
}}
</script>
</body>
</html>"""


# ─────────────────────────────────────────
# マクロ経済カレンダー
# ─────────────────────────────────────────
# 2026年の主要経済イベント（month, day, country, importance, name, description）
# country: "jp","us","eu","cn"  importance: "high","mid"
ECONOMIC_EVENTS_2026 = [
    # ── 1月 ──
    (1,  6, "us","mid","ISM非製造業","サービス業の景況感"),
    (1, 10, "us","high","米雇用統計（12月分）","日本時間22:30発表"),
    (1, 15, "us","high","米CPI（12月分）","インフレの代表指標"),
    (1, 22, "jp","high","日銀金融政策決定会合（1日目）",""),
    (1, 23, "jp","high","日銀会合（結果発表）","展望レポートあり"),
    (1, 27, "us","high","FOMC（1日目）",""),
    (1, 28, "us","high","FOMC（結果発表）","日本時間4:00"),
    (1, 30, "eu","high","ECB理事会（金利決定）",""),
    # ── 2月 ──
    (2,  3, "us","mid","ISM製造業","製造業の景況感"),
    (2,  7, "us","high","米雇用統計（1月分）","日本時間22:30発表"),
    (2, 12, "us","high","米CPI（1月分）","コアCPIに注目"),
    (2, 21, "jp","mid","全国CPI（1月分）","日銀利上げ判断材料"),
    (2, 27, "us","mid","米GDP改定値（Q4）",""),
    # ── 3月 ──
    (3,  2, "us","mid","ISM製造業",""),
    (3,  6, "us","high","米雇用統計（2月分）",""),
    (3, 11, "us","high","米CPI（2月分）",""),
    (3, 12, "jp","high","日銀金融政策決定会合（1日目）",""),
    (3, 13, "jp","high","日銀会合（結果発表）",""),
    (3, 17, "us","high","FOMC（1日目）","経済見通し・ドットプロット"),
    (3, 18, "us","high","FOMC（結果発表）","記者会見あり"),
    (3, 18, "eu","high","ECB理事会（金利決定）",""),
    (3, 21, "jp","mid","全国CPI（2月分）",""),
    (3, 26, "us","mid","米GDP確定値（Q4）",""),
    # ── 4月 ──
    (4,  1, "jp","high","日銀短観（4月調査）","企業景況感"),
    (4,  1, "us","mid","ISM製造業",""),
    (4,  3, "us","high","米雇用統計（3月分）","日本時間21:30発表"),
    (4,  9, "us","mid","PPI（3月分）",""),
    (4, 10, "us","high","米CPI（3月分）",""),
    (4, 15, "cn","high","中国GDP（第1四半期）","小売売上高・鉱工業生産も同時発表"),
    (4, 15, "us","mid","小売売上高",""),
    (4, 16, "eu","high","ECB理事会（金利決定）",""),
    (4, 24, "jp","mid","全国CPI（3月分）",""),
    (4, 27, "jp","high","日銀金融政策決定会合（1日目）","展望レポートあり"),
    (4, 28, "jp","high","日銀会合（結果発表）","利上げ判断に注目"),
    (4, 28, "us","high","FOMC（1日目）",""),
    (4, 29, "us","high","FOMC（結果発表）","日本時間4/30 3:00"),
    (4, 29, "us","mid","米GDP速報値（Q1）",""),
    (4, 30, "cn","mid","中国製造業PMI（4月分）",""),
    (4, 30, "jp","mid","鉱工業生産（3月速報）",""),
    (4, 30, "eu","mid","ユーロ圏GDP速報（Q1）",""),
    # ── 5月 ──
    (5,  1, "us","mid","ISM製造業",""),
    (5,  1, "cn","mid","財新PMI",""),
    (5,  8, "us","high","米雇用統計（4月分）","GW中に発表"),
    (5, 12, "us","high","米CPI（4月分）","基準年変更に注意"),
    (5, 13, "us","mid","PPI（4月分）",""),
    (5, 15, "us","mid","小売売上高",""),
    (5, 15, "cn","mid","中国経済指標（4月分）","小売売上高・鉱工業生産"),
    (5, 20, "jp","mid","日本GDP速報値（Q1）","関税影響に注目"),
    (5, 21, "jp","mid","貿易統計（4月分）",""),
    (5, 28, "us","mid","米GDP改定値（Q1）",""),
    (5, 29, "jp","mid","全国CPI（4月分）",""),
    (5, 31, "cn","mid","中国製造業PMI（5月分）",""),
    # ── 6月 ──
    (6,  2, "us","mid","ISM製造業",""),
    (6,  5, "us","high","米雇用統計（5月分）",""),
    (6, 10, "us","high","米CPI（5月分）",""),
    (6, 10, "eu","high","ECB理事会（金利決定）",""),
    (6, 16, "us","high","FOMC（1日目）","経済見通し・ドットプロット"),
    (6, 17, "us","high","FOMC（結果発表）","記者会見あり"),
    (6, 17, "jp","high","日銀金融政策決定会合（1日目）",""),
    (6, 18, "jp","high","日銀会合（結果発表）",""),
    (6, 20, "jp","mid","全国CPI（5月分）",""),
    (6, 25, "us","mid","米GDP確定値（Q1）",""),
    # ── 7月 ──
    (7,  1, "jp","high","日銀短観（7月調査）",""),
    (7,  2, "us","high","米雇用統計（6月分）",""),
    (7, 10, "us","high","米CPI（6月分）",""),
    (7, 15, "cn","high","中国GDP（第2四半期）",""),
    (7, 22, "eu","high","ECB理事会（金利決定）",""),
    (7, 28, "us","high","FOMC（1日目）",""),
    (7, 29, "us","high","FOMC（結果発表）",""),
    (7, 29, "jp","high","日銀金融政策決定会合（1日目）","展望レポートあり"),
    (7, 30, "jp","high","日銀会合（結果発表）",""),
    (7, 30, "us","mid","米GDP速報値（Q2）",""),
    # ── 8月 ──
    (8,  1, "us","high","米雇用統計（7月分）",""),
    (8, 12, "us","high","米CPI（7月分）",""),
    # ── 9月 ──
    (9,  5, "us","high","米雇用統計（8月分）",""),
    (9, 10, "us","high","米CPI（8月分）",""),
    (9, 10, "eu","high","ECB理事会（金利決定）",""),
    (9, 15, "us","high","FOMC（1日目）","経済見通し・ドットプロット"),
    (9, 16, "us","high","FOMC（結果発表）","記者会見あり"),
    (9, 17, "jp","high","日銀金融政策決定会合（1日目）",""),
    (9, 18, "jp","high","日銀会合（結果発表）",""),
    # ── 10月 ──
    (10, 1, "jp","high","日銀短観（10月調査）",""),
    (10, 2, "us","high","米雇用統計（9月分）",""),
    (10,14, "us","high","米CPI（9月分）",""),
    (10,15, "cn","high","中国GDP（第3四半期）",""),
    (10,27, "us","high","FOMC（1日目）",""),
    (10,28, "us","high","FOMC（結果発表）",""),
    (10,28, "jp","high","日銀金融政策決定会合（1日目）","展望レポートあり"),
    (10,29, "jp","high","日銀会合（結果発表）",""),
    (10,29, "eu","high","ECB理事会（金利決定）",""),
    (10,29, "us","mid","米GDP速報値（Q3）",""),
    # ── 11月 ──
    (11, 6, "us","high","米雇用統計（10月分）",""),
    (11,12, "us","high","米CPI（10月分）",""),
    # ── 12月 ──
    (12, 4, "us","high","米雇用統計（11月分）",""),
    (12, 8, "us","high","FOMC（1日目）","経済見通し・ドットプロット"),
    (12, 9, "us","high","FOMC（結果発表）","記者会見あり"),
    (12,10, "us","high","米CPI（11月分）",""),
    (12,16, "eu","high","ECB理事会（金利決定）",""),
    (12,17, "jp","high","日銀金融政策決定会合（1日目）",""),
    (12,18, "jp","high","日銀会合（結果発表）",""),
]

# 各指標の日本語解説（初心者向け）
_EVENT_DESCRIPTIONS = {
    "米雇用統計": "非農業部門雇用者数と失業率。FRBの利下げ判断に直結。予想より強いとドル高・円安に。",
    "米CPI": "消費者物価指数。インフレの代表指標。コアCPI（食品・エネ除く）が特に重要。",
    "FOMC": "FRBの金利決定会合。利下げ・据え置き・利上げを決定。ドル円・日経に大きく影響。",
    "日銀会合": "日銀の金利決定。利上げの有無が住宅ローン金利に直結。展望レポート回は注目度大。",
    "日銀金融政策決定会合": "日銀の金利決定会合の初日。翌日に結果発表。",
    "ECB理事会": "欧州中央銀行の金利決定。ユーロ円・ユーロドルに影響。",
    "日銀短観": "企業の景況感を示す最重要指標。大企業製造業の業況判断DIに注目。",
    "中国GDP": "世界第2位の経済大国の成長率。日本の輸出企業の業績に直結。",
    "中国製造業PMI": "50以上=景気拡大、50以下=景気縮小。日本の素材・機械メーカーの受注先読みに。",
    "全国CPI": "日本のインフレ率。日銀の利上げ判断材料。コアCPIが2%超え続けるかがポイント。",
    "日本GDP": "日本経済の成長率。マイナス成長なら景気後退懸念で日銀利上げが遠のく。",
    "米GDP": "米国経済の成長率。速報→改定→確定の3段階で発表。",
}


def _get_event_detail(name):
    """イベント名から初心者向け解説を取得"""
    for key, desc in _EVENT_DESCRIPTIONS.items():
        if key in name:
            return desc
    return ""


# ─────────────────────────────────────────
# 指標解説辞書（preview.html 用）
#   各指標の「事前解説記事」のもとになる詳細情報。
#   発表前日にこの情報をもとにシナリオ別の影響を解説する。
# ─────────────────────────────────────────
INDICATOR_GUIDES = {
    "米雇用統計": {
        "emoji": "👷", "country": "us",
        "title": "米雇用統計（NFP）",
        "release": "毎月第1金曜・日本時間 21:30〜22:30",
        "what": "米労働省が発表する非農業部門雇用者数（NFP）と失業率の月次統計。米経済の最重要指標のひとつ。",
        "why": "FRBの金融政策（利上げ・利下げ）に直結。雇用が強ければ景気拡大・利下げ後退観測、弱ければ景気減速・利下げ加速観測につながる。",
        "scenarios": [
            ("強い結果（予想を大幅上回る）", "ドル高・円安／米10年債利回り上昇／株は『良いニュース＝強い経済』で上昇する場合と、『利下げが遠のく』で下落する場合あり"),
            ("ほぼ予想通り", "材料出尽くしで小動き。失業率と平均時給のサプライズに注目が移る"),
            ("弱い結果（予想を大幅下回る）", "ドル安・円高／米10年債利回り低下／株は利下げ期待で上昇する場合と、景気後退懸念で下落する場合あり"),
        ],
        "watch": ["NFP変化数（予想vs実績）", "失業率", "平均時給（前月比・前年同月比）", "前月分の改定値"],
        "tip": "結果発表の瞬間にドル円が1〜2円動くこともある最重要指標。短期トレードは避け、結果が出た後の方向感を見てから動くのが無難。",
    },
    "米CPI": {
        "emoji": "🛒", "country": "us",
        "title": "米消費者物価指数（CPI）",
        "release": "毎月中旬・日本時間 21:30（夏時間）/ 22:30（冬時間）",
        "what": "米労働省が発表する消費者物価指数。インフレ動向を示す代表指標。総合CPIとコアCPI（食品・エネルギー除く）の2種類が公表される。",
        "why": "FRBは『2%インフレ目標』を掲げており、CPIの推移が利上げ・利下げ判断の核心材料になる。FOMCの結果以上に株・為替を動かすことも多い。",
        "scenarios": [
            ("予想を上回る（インフレ加速）", "ドル高・円安／米長期金利上昇／株安（特にハイテク株が下げやすい）"),
            ("予想通り", "FRBの利下げシナリオに変化なし。小動きが多いがコアCPIの『前月比』に注目"),
            ("予想を下回る（インフレ鈍化）", "ドル安・円高／米長期金利低下／株高（利下げ期待）"),
        ],
        "watch": ["コアCPI 前年同月比（最重要）", "コアCPI 前月比（直近のトレンド）", "住居費（粘着的インフレの指標）", "サービス価格"],
        "tip": "実績が予想と0.1%違うだけでドル円が1円以上動くことも。発表前後30分はボラティリティが極端に高い。",
    },
    "FOMC": {
        "emoji": "🏛️", "country": "us",
        "title": "FOMC（連邦公開市場委員会）",
        "guide_url": "guide-fomc.html",
        "release": "年8回・日本時間 翌日 3:00（または 4:00）に政策金利発表＋議長会見",
        "what": "米FRBが政策金利（FFレート誘導目標）を決定する会合。年4回（3・6・9・12月）は経済見通し（SEP）とドットプロットも公表。",
        "why": "世界中の株・為替・債券を動かす最重要イベント。利下げ・据え置き・利上げの判断と、議長の今後の政策スタンスが市場を支配する。",
        "scenarios": [
            ("タカ派（利下げ慎重・利上げ示唆）", "ドル高・円安／米長期金利上昇／世界の株安（特に新興国・ハイテク株）"),
            ("中立（市場予想通り）", "材料出尽くしで小動きだが、議長会見でのニュアンス次第で振れる"),
            ("ハト派（利下げ前倒し示唆）", "ドル安・円高／米長期金利低下／世界の株高（リスクオン）"),
        ],
        "watch": ["政策金利の決定", "声明文の文言変更（特に『data-dependent』『patient』など）", "ドットプロット（年内利下げ回数）", "議長会見でのインフレ見通し発言"],
        "tip": "結果発表（3:00 or 4:00 JST）→ 議長会見（30分後）の二段階で動く。日本時間の早朝なので、寝ている間にドル円が2〜3円動くこともある。前日にポジションを軽くするのが鉄則。",
    },
    "日銀金融政策決定会合": {
        "emoji": "🇯🇵", "country": "jp",
        "title": "日銀金融政策決定会合",
        "release": "年8回・2日目の昼前後に結果発表＋総裁会見（15:30〜）",
        "what": "日本銀行が政策金利（短期金利・長期金利の誘導目標）を決定する会合。1月・4月・7月・10月は『展望レポート』も公表され、物価見通しが改定される。",
        "why": "ドル円・日経平均・日本国債利回りを動かす最重要イベント。利上げ・据え置き、長期金利の上限（YCC）、物価見通しの変化が焦点。",
        "scenarios": [
            ("タカ派（利上げ・YCC柔軟化）", "円高・ドル安／日本長期金利上昇／日経下落（特に銀行株は上昇、不動産株は下落）"),
            ("据え置き＆中立", "予想通りなら小動き。総裁会見の『今後の利上げ示唆』に焦点"),
            ("ハト派（利上げ後ろ倒し示唆）", "円安・ドル高／日本長期金利低下／日経上昇（特に輸出株）"),
        ],
        "watch": ["政策金利の決定", "展望レポートの物価見通し（コアCPI 2%超えを継続予想か）", "総裁会見での『次回利上げ』示唆", "国債買入れオペの変更"],
        "tip": "結果発表は不規則（11時〜13時頃）。総裁会見（15:30〜）まで様子見の投資家が多い。会見でドル円が1〜2円動くこともある。",
    },
    "ECB理事会": {
        "emoji": "🇪🇺", "country": "eu",
        "title": "ECB理事会（欧州中央銀行）",
        "release": "年8回・日本時間 21:15 に金利発表＋21:45〜 ラガルド総裁会見",
        "what": "ECBが政策金利（主要リファイナンス金利・預金ファシリティ金利）を決定する会合。ユーロ圏のインフレと景気を主眼に判断。",
        "why": "ユーロ円・ユーロドルを動かす最重要イベント。日本人投資家には『クロス円』経由でドル円にも波及するため間接的に影響。",
        "scenarios": [
            ("タカ派（利下げ慎重）", "ユーロ高・円安／欧州株は下落しやすい"),
            ("中立", "予想通りなら小動き。総裁会見のニュアンスで方向決定"),
            ("ハト派（利下げ前倒し）", "ユーロ安・円高／欧州株は上昇しやすい"),
        ],
        "watch": ["政策金利の決定", "声明文のインフレ見通し", "ラガルド総裁の『今後の利下げペース』発言", "QT（量的引き締め）の進捗"],
        "tip": "FOMCより市場へのインパクトはやや小さいが、ユーロドル経由でドル円にも波及する。",
    },
    "日銀短観": {
        "emoji": "📊", "country": "jp",
        "title": "日銀短観（全国企業短期経済観測調査）",
        "release": "年4回（4月・7月・10月・12月）・日本時間 8:50",
        "what": "日銀が約1万社の企業に景況感を聞き取る調査。『業況判断DI』（良い-悪いの差）が代表指標。大企業製造業のDIが最注目。",
        "why": "日本経済の実態を最も正確に反映する指標。日銀の利上げ判断材料となり、日経平均・ドル円に影響。",
        "scenarios": [
            ("予想を大幅に上回る", "円高・日経上昇／日銀の利上げ前倒し観測"),
            ("予想通り", "小動き"),
            ("予想を大幅に下回る", "円安・日経下落（一時的）／日銀の利上げ後ろ倒し観測"),
        ],
        "watch": ["大企業製造業 業況判断DI", "大企業非製造業 業況判断DI", "中小企業のDI", "設備投資計画（前年度比）", "想定為替レート"],
        "tip": "朝8:50発表のため、日経の寄付き（9:00）に影響大。前日にポジション調整しておくと安心。",
    },
    "中国GDP": {
        "emoji": "🇨🇳", "country": "cn",
        "title": "中国GDP（国内総生産）",
        "release": "四半期ごと（1月・4月・7月・10月）・日本時間 11:00",
        "what": "中国の四半期ごとの経済成長率。同時に小売売上高・鉱工業生産・固定資産投資も発表されることが多い。",
        "why": "世界第2位の経済大国の動向は、日本の輸出企業（自動車・機械・電子部品）の業績に直結。中国経済の減速は資源価格にも波及。",
        "scenarios": [
            ("予想を上回る（景気回復）", "資源価格上昇／豪ドル・NZドル上昇／日経は中国関連株（コマツ・ファナック等）が上昇"),
            ("予想通り", "小動き"),
            ("予想を下回る（景気減速）", "資源価格下落／豪ドル・NZドル下落／日経は中国関連株が下落／円高（リスクオフ）"),
        ],
        "watch": ["GDP前年同期比（政府目標との乖離）", "小売売上高（消費の強さ）", "鉱工業生産（生産活動）", "固定資産投資（不動産含む）"],
        "tip": "中国当局の発表する数字は『目標達成しやすいよう調整される』との見方も。あくまで参考値として扱うのが賢明。",
    },
    "中国製造業PMI": {
        "emoji": "🏭", "country": "cn",
        "title": "中国製造業PMI（購買担当者景気指数）",
        "release": "毎月月末・日本時間 10:00（公式）/ 10:45（財新）",
        "what": "中国の製造業の景況感を示す指標。50以上=景気拡大、50以下=景気縮小を意味する。『公式PMI』（国家統計局）と『財新PMI』（民間企業中心）の2種類。",
        "why": "中国の景気の先行指標。日本の素材・機械メーカーの受注動向を先読みできる。",
        "scenarios": [
            ("50以上＆改善", "豪ドル・銅価格上昇／日経の素材株（鉄鋼・化学）上昇"),
            ("50付近で小動き", "材料視されず"),
            ("50割れ＆悪化", "豪ドル・銅価格下落／日経の素材株下落／円高（リスクオフ）"),
        ],
        "watch": ["公式PMIと財新PMIの乖離", "新規受注（先行性が高い）", "雇用指数"],
        "tip": "公式PMIは国有大企業中心、財新PMIは民間中小企業中心。両方見ることで全体像が掴める。",
    },
    "全国CPI": {
        "emoji": "🇯🇵", "country": "jp",
        "title": "全国消費者物価指数（日本）",
        "release": "毎月19日前後・日本時間 8:30",
        "what": "総務省が発表する日本の消費者物価指数。総合・コア（生鮮食品除く）・コアコア（生鮮食品＋エネルギー除く）の3種類。",
        "why": "日銀の『2%物価安定目標』との比較で利上げ判断材料に。コアCPIが2%を継続して超えるかが焦点。",
        "scenarios": [
            ("予想を大幅に上回る", "円高（日銀利上げ観測）／日経下落"),
            ("予想通り", "小動き"),
            ("予想を大幅に下回る", "円安（日銀利上げ後退観測）／日経上昇"),
        ],
        "watch": ["コアCPI 前年同月比", "コアコアCPI 前年同月比（粘着的インフレ）", "サービス価格上昇率"],
        "tip": "発表は8:30、日経寄付き（9:00）の30分前なので相場に直接影響する。",
    },
    "日本GDP": {
        "emoji": "🇯🇵", "country": "jp",
        "title": "日本GDP",
        "release": "四半期ごと・日本時間 8:50（速報→改定→確定の3回発表）",
        "what": "日本の四半期ごとの経済成長率。実質GDP前期比年率が代表指標。",
        "why": "日本経済の実態を示す最重要指標。マイナス成長なら日銀の利上げが遠のく。",
        "scenarios": [
            ("予想を大幅に上回る", "円高・日経上昇"),
            ("予想通り", "小動き"),
            ("マイナス成長", "円安・日経下落（一時的）／日銀利上げ後退観測"),
        ],
        "watch": ["実質GDP前期比年率", "個人消費（GDPの過半数）", "設備投資", "輸出"],
        "tip": "速報値が最も注目される。改定値・確定値はサプライズが少ない。",
    },
    "米GDP": {
        "emoji": "📈", "country": "us",
        "title": "米GDP",
        "guide_url": "guide-us-gdp.html",
        "release": "四半期ごと・日本時間 21:30（速報→改定→確定の3回発表）",
        "what": "米国の四半期ごとの経済成長率。実質GDP前期比年率（年換算値）が代表指標。",
        "why": "米景気の実態を示す指標。市場予想との乖離でドル・株・債券が動く。",
        "scenarios": [
            ("予想を大幅に上回る", "ドル高／米長期金利上昇／株は強い経済で上昇 or 利下げ後退で下落"),
            ("予想通り", "小動き"),
            ("予想を大幅に下回る", "ドル安／米長期金利低下／株は利下げ期待で上昇 or 景気後退懸念で下落"),
        ],
        "watch": ["実質GDP前期比年率（年換算）", "個人消費", "設備投資", "GDPデフレーター（インフレ指標）"],
        "tip": "速報値（Advance）が最大のインパクト。改定値（Second/Third）はサプライズ少。",
    },
    "ISM製造業": {
        "emoji": "🏭", "country": "us",
        "title": "ISM製造業景況感指数",
        "release": "毎月月初・日本時間 23:00（夏時間）/ 24:00（冬時間）",
        "what": "ISM（全米供給管理協会）が発表する製造業の景況感指数。50以上=拡大、50以下=縮小。",
        "why": "米景気の先行指標。雇用統計・GDPに先行して景気の方向を示す。",
        "scenarios": [
            ("50超＆改善", "ドル高／株高（特にシクリカル）"),
            ("50付近で小動き", "材料視されず"),
            ("50割れ＆悪化", "ドル安／株安（景気後退懸念）"),
        ],
        "watch": ["総合指数（50との比較）", "新規受注（先行性大）", "雇用指数（NFPの先行指標）", "価格指数（インフレの先行指標）"],
        "tip": "雇用指数はNFPの先行指標として要注目。",
    },
    "ISM非製造業": {
        "emoji": "🏢", "country": "us",
        "title": "ISM非製造業景況感指数（サービス業）",
        "release": "毎月月初・日本時間 23:00（夏時間）/ 24:00（冬時間）",
        "what": "ISMが発表するサービス業の景況感指数。米GDPの約7割を占めるサービス業の動向を示す。",
        "why": "米景気の中核を示す指標。雇用統計と並ぶ重要指標。",
        "scenarios": [
            ("50超＆改善", "ドル高／株高"),
            ("50付近で小動き", "材料視されず"),
            ("50割れ", "ドル安／株安（景気後退懸念）"),
        ],
        "watch": ["総合指数", "新規受注", "雇用指数", "価格指数"],
        "tip": "製造業よりサービス業のシェアが大きく、ISM非製造業の方がGDPへの影響大。",
    },
    "PPI": {
        "emoji": "📦", "country": "us",
        "title": "米生産者物価指数（PPI）",
        "release": "毎月中旬・日本時間 21:30（夏時間）/ 22:30（冬時間）",
        "what": "米労働省が発表する生産者（卸売）段階の物価指数。CPIの先行指標。",
        "why": "PPIの上昇は1〜2か月後のCPIに波及するため、インフレの先行指標として注目される。",
        "scenarios": [
            ("予想を上回る", "ドル高・米長期金利上昇／株安"),
            ("予想通り", "小動き"),
            ("予想を下回る", "ドル安・米長期金利低下／株高"),
        ],
        "watch": ["コアPPI 前年同月比", "コアPPI 前月比"],
        "tip": "CPIの数日前に発表されることが多く、CPI予想を修正するきっかけになる。",
    },
    "小売売上高": {
        "emoji": "🛍️", "country": "us",
        "title": "米小売売上高",
        "release": "毎月中旬・日本時間 21:30（夏時間）/ 22:30（冬時間）",
        "what": "米国の小売・サービス業の売上を集計した指標。個人消費の動向を示す。",
        "why": "米GDPの約7割を占める個人消費の代表指標。FRBの政策判断にも影響。",
        "scenarios": [
            ("予想を大幅に上回る", "ドル高／株高（消費が強い）"),
            ("予想通り", "小動き"),
            ("予想を下回る", "ドル安／株安（消費低迷）"),
        ],
        "watch": ["前月比", "コア小売（自動車除く）", "コントロール・グループ（GDPに直接寄与）"],
        "tip": "コントロール・グループの方がGDPへの寄与度が高く、本質的に重要。",
    },
    "ユーロ圏GDP": {
        "emoji": "🇪🇺", "country": "eu",
        "title": "ユーロ圏GDP",
        "release": "四半期ごと・日本時間 18:00",
        "what": "ユーロ圏全体の四半期GDP。",
        "why": "ECBの利下げ判断材料。ユーロ円・ユーロドルに影響。",
        "scenarios": [
            ("予想を上回る", "ユーロ高（ECB利下げ後退観測）"),
            ("予想通り", "小動き"),
            ("予想を下回る", "ユーロ安（ECB利下げ前倒し観測）"),
        ],
        "watch": ["前期比年率", "ドイツGDP（最大経済国）"],
        "tip": "ドイツGDPと同時か近接して発表されるため、合わせて見る。",
    },
    "鉱工業生産": {
        "emoji": "🏭", "country": "jp",
        "title": "鉱工業生産（日本）",
        "release": "毎月月末・日本時間 8:50（速報）",
        "what": "経産省が発表する日本の鉱工業の生産指数。",
        "why": "日本の製造業の活動度合いを示す指標。輸出関連株や日経平均に影響。",
        "scenarios": [
            ("前月比プラス", "日経の輸出株上昇"),
            ("ほぼ横ばい", "材料視されず"),
            ("前月比マイナス", "日経の輸出株下落"),
        ],
        "watch": ["前月比", "前年同月比", "出荷・在庫指数"],
        "tip": "速報値発表後、確報値で大きく改定されることもあるので速報値の数字を過信しない。",
    },
    "貿易統計": {
        "emoji": "📦", "country": "jp",
        "title": "日本 貿易統計",
        "release": "毎月20日前後・日本時間 8:50",
        "what": "財務省が発表する日本の輸出入・貿易収支。",
        "why": "貿易黒字の推移は円需要に直結。日本企業の輸出競争力を示す。",
        "scenarios": [
            ("貿易黒字拡大", "円高圧力"),
            ("ほぼ予想通り", "材料視されず"),
            ("貿易赤字拡大", "円安圧力"),
        ],
        "watch": ["輸出 前年同月比（特に対米国・中国）", "輸入 前年同月比（資源価格の影響）", "貿易収支"],
        "tip": "日本は資源輸入国のため、原油価格上昇期には貿易赤字が膨らみ円安要因になる。",
    },
    "財新PMI": {
        "emoji": "🇨🇳", "country": "cn",
        "title": "中国 財新PMI",
        "release": "毎月月初・日本時間 10:45",
        "what": "民間企業中心の中国製造業PMI（公式PMIは国有企業中心）。",
        "why": "中国の中小企業・民間企業の景況感を反映。公式PMIとの乖離が中国経済の実態を示すヒントに。",
        "scenarios": [
            ("50超", "豪ドル上昇／日経の中国関連株上昇"),
            ("50付近", "小動き"),
            ("50割れ", "豪ドル下落／日経の中国関連株下落"),
        ],
        "watch": ["総合指数", "公式PMIとの乖離"],
        "tip": "公式PMIの翌日に発表されることが多い。両方見ることで中国経済の全体像が掴める。",
    },
}


def match_indicator_guide(event_name):
    """イベント名から該当する指標解説を検索。最も具体的にマッチするキーを返す。"""
    # 「日銀金融政策決定会合」が「日銀」より優先されるよう、キー長で降順ソート
    keys = sorted(INDICATOR_GUIDES.keys(), key=len, reverse=True)
    for key in keys:
        if key in event_name:
            return key, INDICATOR_GUIDES[key]
    return None, None


def find_upcoming_events(now_jst, days_ahead=3):
    """now_jst から days_ahead 日先までの経済イベントを返す。

    日付順・重要度順にソート。同日内では high → mid の順。
    """
    today = now_jst.date()
    target_dates = [today + timedelta(days=i) for i in range(1, days_ahead + 1)]
    target_year = now_jst.year

    upcoming = []
    for m, d, c, imp, n, desc in ECONOMIC_EVENTS_2026:
        try:
            event_date = datetime(target_year, m, d).date()
        except ValueError:
            continue
        if event_date in target_dates:
            upcoming.append({
                "date": event_date,
                "country": c,
                "importance": imp,
                "name": n,
                "desc": desc,
            })

    # 日付昇順、同日内は high 優先
    imp_rank = {"high": 0, "mid": 1}
    upcoming.sort(key=lambda x: (x["date"], imp_rank.get(x["importance"], 9)))
    return upcoming


import calendar as cal_module

# ─────────────────────────────────────────
# 出来高急増ランキング（hot-assets.html）
# ─────────────────────────────────────────
HOT_ASSETS = {
    "sectors": {
        "title": "🇺🇸 米国株セクター",
        "subtitle": "SPDR セクターETF（11業種）— どの業種に資金が流れているか",
        "symbols": [
            ("XLK", "テクノロジー"),   ("XLV", "ヘルスケア"),
            ("XLF", "金融"),            ("XLY", "一般消費財"),
            ("XLC", "通信サービス"),    ("XLI", "資本財"),
            ("XLP", "生活必需品"),      ("XLE", "エネルギー"),
            ("XLU", "公益"),            ("XLRE", "不動産"),
            ("XLB", "素材"),
        ],
    },
    "japan": {
        "title": "🇯🇵 日本株 主要銘柄",
        "subtitle": "TOPIX Core30級の代表銘柄 — 国内資金の動きを見る",
        "symbols": [
            ("7203.T", "トヨタ自動車"),    ("6758.T", "ソニーG"),
            ("8306.T", "三菱UFJ"),         ("9984.T", "ソフトバンクG"),
            ("8035.T", "東京エレクトロン"),("6861.T", "キーエンス"),
            ("9432.T", "NTT"),             ("4063.T", "信越化学"),
            ("6098.T", "リクルートHD"),    ("8058.T", "三菱商事"),
            ("8316.T", "三井住友FG"),      ("9433.T", "KDDI"),
            ("6501.T", "日立製作所"),      ("7974.T", "任天堂"),
        ],
    },
    "indices": {
        "title": "🌐 世界 主要市場",
        "subtitle": "主要インデックス — どこの市場が活況か",
        "symbols": [
            ("^N225",  "日経平均"),       ("^GSPC",  "S&P500"),
            ("^IXIC",  "ナスダック"),     ("^DJI",   "NYダウ"),
            ("^GDAXI", "独DAX"),          ("^FTSE",  "英FTSE"),
            ("^HSI",   "香港ハンセン"),   ("^STOXX50E", "欧州Stoxx50"),
        ],
    },
    "others": {
        "title": "💱 FX・コモディティ・暗号資産",
        "subtitle": "値動き率ベースのホット資産（出来高データなしの銘柄含む）",
        "symbols": [
            ("JPY=X",     "USD/JPY"),     ("EURJPY=X",  "EUR/JPY"),
            ("GBPJPY=X",  "GBP/JPY"),     ("AUDJPY=X",  "AUD/JPY"),
            ("GC=F",      "金"),          ("SI=F",      "銀"),
            ("CL=F",      "WTI原油"),     ("HG=F",      "銅"),
            ("BTC-USD",   "ビットコイン"),("ETH-USD",   "イーサリアム"),
            ("SOL-USD",   "ソラナ"),      ("XRP-USD",   "リップル"),
        ],
    },
}


def fetch_hot_asset(sym, name):
    """yfinanceから30日分の履歴を取得し、出来高急増率と価格変動を計算

    戻り値: dict または None
      - symbol, name: 銘柄識別
      - today_vol: 本日出来高
      - avg_vol: 20日平均出来高（本日除外）
      - surge_ratio: 急増率（today / avg）
      - change_pct: 前日比%
      - price: 終値
    """
    try:
        t = yf.Ticker(sym)
        hist = t.history(period="30d")
        if hist.empty or len(hist) < 2:
            return None

        today_vol = float(hist["Volume"].iloc[-1])
        avg_vol = float(hist["Volume"].iloc[:-1].mean()) if len(hist) > 1 else 0.0
        surge_ratio = (today_vol / avg_vol) if avg_vol > 0 else 0.0

        today_close = float(hist["Close"].iloc[-1])
        prev_close = float(hist["Close"].iloc[-2])
        change_pct = ((today_close - prev_close) / prev_close * 100) if prev_close > 0 else 0.0

        return {
            "symbol": sym,
            "name": name,
            "today_vol": today_vol,
            "avg_vol": avg_vol,
            "surge_ratio": surge_ratio,
            "change_pct": change_pct,
            "price": today_close,
        }
    except Exception as e:
        print(f"  ⚠️ {sym} 取得失敗: {e}")
        return None


def fetch_hot_assets_all():
    """HOT_ASSETSの全銘柄データを取得"""
    result = {}
    for cat, info in HOT_ASSETS.items():
        print(f"  {info['title']} ({len(info['symbols'])}銘柄)...")
        rows = []
        for sym, name in info["symbols"]:
            row = fetch_hot_asset(sym, name)
            if row:
                rows.append(row)
        result[cat] = rows
    return result


def _fmt_vol(v):
    """出来高を K / M / B 表記に整形"""
    if v is None or v <= 0:
        return "—"
    if v >= 1_000_000_000:
        return f"{v/1_000_000_000:.1f}B"
    if v >= 1_000_000:
        return f"{v/1_000_000:.1f}M"
    if v >= 1_000:
        return f"{v/1_000:.1f}K"
    return f"{int(v)}"


def _surge_badge(ratio):
    """急増率を色付きバッジに"""
    if ratio <= 0:
        return '<span class="badge-vol badge-na">—</span>'
    if ratio >= 3.0:
        return f'<span class="badge-vol badge-hot">🔥 {ratio:.1f}×</span>'
    if ratio >= 1.8:
        return f'<span class="badge-vol badge-warm">⚡ {ratio:.1f}×</span>'
    if ratio >= 1.2:
        return f'<span class="badge-vol badge-mild">{ratio:.1f}×</span>'
    return f'<span class="badge-vol badge-calm">{ratio:.1f}×</span>'


def _change_cell(pct):
    """前日比%を色付きセルに"""
    if pct > 0:
        return f'<span style="color:#1a7f37;font-weight:600">+{pct:.2f}%</span>'
    if pct < 0:
        return f'<span style="color:#cf222e;font-weight:600">{pct:.2f}%</span>'
    return f'<span style="color:#57606a">{pct:.2f}%</span>'


def _build_hot_rows(rows, show_volume=True):
    """カテゴリ毎のランキング行HTML生成（急増率降順）"""
    # FX系は出来高0なので、出来高なしカテゴリは値動き率|%|で並べる
    if show_volume:
        sorted_rows = sorted(rows, key=lambda r: r["surge_ratio"], reverse=True)
    else:
        sorted_rows = sorted(rows, key=lambda r: abs(r["change_pct"]), reverse=True)

    html = ""
    for i, r in enumerate(sorted_rows, 1):
        rank_color = "#bf3989" if i <= 3 else "#57606a"
        vol_cell = f'<td class="vol-cell">{_fmt_vol(r["today_vol"])}</td><td>{_surge_badge(r["surge_ratio"])}</td>' if show_volume else '<td colspan="2" style="text-align:center;color:#6e7781;font-size:.75rem">（出来高非対象）</td>'
        html += f"""
        <tr>
          <td class="rank" style="color:{rank_color}">{i}</td>
          <td class="asset-name">{r["name"]}<br><span class="asset-sym">{r["symbol"]}</span></td>
          <td class="price-cell">{r["price"]:,.2f}</td>
          <td>{_change_cell(r["change_pct"])}</td>
          {vol_cell}
        </tr>"""
    return html


def build_hot_assets_html(hot_data, now_jst):
    """hot-assets.html を生成 — 4カテゴリの出来高急増ランキング"""
    time_str = now_jst.strftime("%Y年%m月%d日 %H:%M JST")

    sections_html = ""
    category_order = [
        ("sectors", True),
        ("japan", True),
        ("indices", True),
        ("others", False),  # FX/コモディティ/暗号資産は出来高なしが多いので値動き率ソート
    ]

    for cat, show_vol in category_order:
        info = HOT_ASSETS[cat]
        rows = hot_data.get(cat, [])
        if not rows:
            body = '<tr><td colspan="6" style="text-align:center;color:#6e7781;padding:20px">データを取得できませんでした</td></tr>'
        else:
            body = _build_hot_rows(rows, show_volume=show_vol)

        vol_header = '<th>出来高</th><th>急増率</th>' if show_vol else '<th colspan="2">出来高</th>'
        sort_note = "出来高急増率が高い順" if show_vol else "値動き率（絶対値）が大きい順"

        sections_html += f"""
  <section class="hot-section">
    <h2 class="hot-title">{info["title"]}</h2>
    <p class="hot-subtitle">{info["subtitle"]} <span class="sort-note">／ {sort_note}</span></p>
    <div class="table-wrap">
      <table class="hot-table">
        <thead>
          <tr>
            <th style="width:48px">順位</th>
            <th>銘柄</th>
            <th>価格</th>
            <th>前日比</th>
            {vol_header}
          </tr>
        </thead>
        <tbody>{body}
        </tbody>
      </table>
    </div>
  </section>"""

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  {seo_head("hot-assets.html", "出来高急増ランキング", "米国セクター・日本株・世界指数・FX/コモディティ/暗号資産の出来高急増銘柄を毎日ランキング更新。資金が集まっている市場をひと目で確認できます。")}
  {GA4_TAG}
  <style>
    *{{margin:0;padding:0;box-sizing:border-box}}
    body{{font-family:'Segoe UI','Hiragino Sans','Yu Gothic',sans-serif;background:#ffffff;color:#1f2328;min-height:100vh}}
    header{{background:linear-gradient(135deg,#f6f8fa,#ffffff);border-bottom:1px solid #d0d7de;padding:24px 32px}}
    .header-inner{{max-width:1200px;margin:0 auto;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px}}
    .header-title{{font-size:1.6rem;font-weight:700;background:linear-gradient(90deg,#bf3989,#cf222e);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}
    .header-meta{{font-size:.85rem;color:#57606a}}
    .header-meta span{{color:#bf3989;font-weight:600}}
    main{{max-width:1200px;margin:0 auto;padding:32px 24px}}
    .nav-bar{{display:flex;flex-wrap:wrap;gap:10px;justify-content:center;margin-bottom:28px}}
    .nav-btn{{display:inline-flex;align-items:center;gap:8px;padding:11px 20px;background:#f6f8fa;border:1px solid #d0d7de;border-radius:10px;color:#57606a;text-decoration:none;font-size:.95rem;font-weight:600;transition:all .2s}}
    .nav-btn:hover{{border-color:#bf3989;color:#bf3989}}
    .nav-btn.current{{background:#3a1f0f;border-color:#bf3989;color:#fff}}

    .intro{{background:linear-gradient(135deg,#2a1f0f,#1c1611);border:1px solid #bf3989;border-radius:12px;padding:18px 24px;margin-bottom:32px;color:#1f2328;line-height:1.75;font-size:.9rem}}
    .intro b{{color:#bf3989}}

    .hot-section{{background:#f6f8fa;border:1px solid #d0d7de;border-radius:12px;padding:20px 24px;margin-bottom:24px}}
    .hot-title{{font-size:1.15rem;font-weight:700;color:#1f2328;margin-bottom:6px}}
    .hot-subtitle{{font-size:.8rem;color:#57606a;margin-bottom:16px;line-height:1.5}}
    .sort-note{{color:#6e7781;font-size:.72rem}}

    .table-wrap{{overflow-x:auto}}
    .hot-table{{width:100%;border-collapse:collapse;font-size:.85rem}}
    .hot-table thead th{{background:#ffffff;color:#57606a;font-size:.72rem;font-weight:600;text-transform:uppercase;letter-spacing:.06em;padding:10px 8px;text-align:left;border-bottom:2px solid #d0d7de}}
    .hot-table tbody td{{padding:10px 8px;border-bottom:1px solid #d0d7de;vertical-align:middle}}
    .hot-table tbody tr:hover{{background:#ffffff}}
    .rank{{font-weight:700;font-size:1rem;text-align:center}}
    .asset-name{{font-weight:600;color:#1f2328}}
    .asset-sym{{font-size:.7rem;color:#6e7781;font-weight:400}}
    .price-cell{{color:#57606a;font-variant-numeric:tabular-nums}}
    .vol-cell{{color:#57606a;font-variant-numeric:tabular-nums;font-size:.8rem}}

    .badge-vol{{display:inline-block;padding:3px 10px;border-radius:12px;font-size:.75rem;font-weight:700;font-variant-numeric:tabular-nums}}
    .badge-hot{{background:#5c1a1a;color:#cf222e;border:1px solid #da3633}}
    .badge-warm{{background:#4a2f0f;color:#bf3989;border:1px solid #9a6700}}
    .badge-mild{{background:#dafbe1;color:#1a7f37;border:1px solid #2ea043}}
    .badge-calm{{background:#ddf4ff;color:#57606a;border:1px solid #d0d7de}}
    .badge-na{{background:#ddf4ff;color:#6e7781;border:1px solid #d0d7de}}

    footer{{background:#f6f8fa;border-top:1px solid #d0d7de;padding:20px 32px;text-align:center;font-size:.78rem;color:#6e7781}}
    footer a{{color:#0969da;text-decoration:none}}
    @media(max-width:600px){{.header-inner{{flex-direction:column}}.hot-section{{padding:16px}}.hot-table{{font-size:.78rem}}}}
  </style>
  <!-- A8.net広告タグはここに貼る予定 -->
</head>
<body>
<header>
  <div class="header-inner">
    <div>
      <div class="header-title">🔥 出来高急増ランキング</div>
      <div class="header-meta">最終更新: <span>{time_str}</span></div>
    </div>
    <div class="header-meta">本日出来高 ÷ 20日平均</div>
  </div>
</header>
<main>

  <!-- ナビゲーション -->
  <nav class="nav-bar">
    <a class="nav-btn" href="index.html">📊 マーケットニュース</a>
    <a class="nav-btn" href="calendar.html">📅 経済カレンダー</a>
    <a class="nav-btn" href="charts.html">📈 50年チャート</a>
    <a class="nav-btn" href="vix.html">😱 恐怖指数</a>
    <a class="nav-btn" href="market-health.html">🩺 市場健康度</a>
    <a class="nav-btn current" href="hot-assets.html">🔥 出来高急増</a>
  </nav>

  <!-- 説明 -->
  <div class="intro">
    <b>🔰 急増率（Volume Surge Ratio）</b>とは、<b>本日の出来高 ÷ 直近20営業日の平均出来高</b>のことです。
    「いつもより何倍動いているか」を示し、ニュースや思惑で注目が集まると急増します。
    <b>🔥 3倍以上は異常値</b>、⚡ 1.8倍以上は要注目、1.2倍以上はやや活況の目安。
    出来高のないFX・コモディティ・暗号資産は「値動き率」でランキングしています。
  </div>
{sections_html}

</main>
<footer>
  <p>データソース: Yahoo Finance (yfinance) &nbsp;|&nbsp;
  <a href="index.html">📊 マーケットニュース</a> &nbsp;|&nbsp;
  本データは自動取得・表示であり、投資助言ではありません。</p>
  <p style="margin-top:8px"><a href="about.html">運営者情報</a> &nbsp;|&nbsp; <a href="privacy.html">プライバシーポリシー</a> &nbsp;|&nbsp; <a href="contact.html">お問い合わせ</a></p>
</footer>
</body>
</html>"""


def build_calendar_html(now_jst):
    """マクロ経済カレンダーページを生成（現在月＋翌月）"""
    time_str = now_jst.strftime("%Y年%m月%d日 %H:%M JST")
    cur_year = now_jst.year
    cur_month = now_jst.month
    next_month = cur_month + 1 if cur_month < 12 else 1
    next_year = cur_year if cur_month < 12 else cur_year + 1

    def events_for_month(year, month):
        return [(d, c, imp, n, desc) for m, d, c, imp, n, desc in ECONOMIC_EVENTS_2026 if m == month]

    def country_css(c):
        return {"jp": "jp", "us": "us", "eu": "eu", "cn": "cn"}.get(c, "us")

    def country_flag(c):
        return {"jp": "🇯🇵", "us": "🇺🇸", "eu": "🇪🇺", "cn": "🇨🇳"}.get(c, "")

    def imp_star(imp):
        return "⭐" if imp == "high" else "●"

    def tag_class(imp):
        return "tag-high" if imp == "high" else "tag-mid"

    DOW_JA = ["月", "火", "水", "木", "金", "土", "日"]

    def build_month_grid(year, month, events, is_current_month):
        month_name = f"{year}年{month}月"
        first_dow, days_in_month = cal_module.monthrange(year, month)
        # Python: Monday=0, Sunday=6 → 日始まりグリッドに変換
        start_offset = (first_dow + 1) % 7  # 日曜始まり

        grid = ""
        grid += f'<div class="month-title">📆 {month_name}</div>\n'
        grid += '<div class="cal-grid">\n'
        grid += '<div class="cal-header sun">日</div><div class="cal-header">月</div><div class="cal-header">火</div><div class="cal-header">水</div><div class="cal-header">木</div><div class="cal-header">金</div><div class="cal-header sat">土</div>\n'

        # 空セル
        for _ in range(start_offset):
            grid += '<div class="cal-cell empty"></div>\n'

        for day in range(1, days_in_month + 1):
            dow = (start_offset + day - 1) % 7  # 0=日,6=土
            day_events = [(c, imp, n) for d, c, imp, n, desc in events if d == day]
            is_today = is_current_month and day == now_jst.day
            cls_extra = ""
            if is_today:
                cls_extra = " today"
            if dow == 0:
                cls_extra += " sun"
            elif dow == 6:
                cls_extra += " sat"

            grid += f'<div class="cal-cell{cls_extra}">\n'
            day_label = f"{day} ← 今日" if is_today else str(day)
            grid += f'<div class="cal-day">{day_label}</div>\n'
            for c, imp, n in day_events:
                css = country_css(c)
                star = imp_star(imp)
                short_name = n.replace("（結果発表）", "").replace("（1日目）", "①")
                if len(short_name) > 12:
                    short_name = short_name[:11] + "…"
                grid += f'<span class="cal-event {css}"><span class="imp">{star}</span> {short_name}</span>\n'
            grid += '</div>\n'

        # 末尾の空セル
        total_cells = start_offset + days_in_month
        remaining = (7 - total_cells % 7) % 7
        for _ in range(remaining):
            grid += '<div class="cal-cell empty"></div>\n'

        grid += '</div>\n'
        return grid

    def build_event_list(events, month):
        html = f'<p style="font-size:.95rem;font-weight:600;color:#57606a;margin-bottom:12px">📋 {month}月の重要イベント詳細</p>\n'
        html += '<div class="event-list">\n'
        seen_days = set()
        for d, c, imp, n, desc in events:
            if imp != "high":
                continue
            flag = country_flag(c)
            tag_c = "tag-" + country_css(c)
            tag_i = tag_class(imp)
            imp_label = "⭐最重要" if imp == "high" else "●重要"
            detail = desc if desc else _get_event_detail(n)
            dow_idx = cal_module.weekday(cur_year, month, d)
            dow_ja = DOW_JA[dow_idx]
            html += f'''<div class="event-card">
<div class="event-date-box"><div class="event-date-day">{d}</div><div class="event-date-dow">{dow_ja}</div></div>
<div class="event-body">
<div class="event-name"><span class="event-tag {tag_c}">{flag}</span><span class="event-tag {tag_i}">{imp_label}</span> {n}</div>
<div class="event-desc">{detail}</div>
</div></div>\n'''
        html += '</div>\n'
        return html

    ev_cur = events_for_month(cur_year, cur_month)
    ev_next = events_for_month(next_year, next_month)
    grid_cur = build_month_grid(cur_year, cur_month, ev_cur, True)
    grid_next = build_month_grid(next_year, next_month, ev_next, False)
    list_cur = build_event_list(ev_cur, cur_month)
    list_next = build_event_list(ev_next, next_month)

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  {seo_head("calendar.html", f"マクロ経済カレンダー {cur_year}年{cur_month}月〜{next_month}月", "米雇用統計・FOMC・CPI・日銀金融政策決定会合・ECB理事会・中国主要指標など、相場を動かす重要イベントを月間カレンダーで一覧表示。日本人投資家向けに重要度ランク付き。")}
  {GA4_TAG}
  <style>
    *{{margin:0;padding:0;box-sizing:border-box}}
    body{{font-family:'Segoe UI','Hiragino Sans','Yu Gothic',sans-serif;background:#ffffff;color:#1f2328;min-height:100vh}}
    header{{background:linear-gradient(135deg,#f6f8fa,#ffffff);border-bottom:1px solid #d0d7de;padding:24px 32px}}
    .header-inner{{max-width:1200px;margin:0 auto;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px}}
    .header-title{{font-size:1.6rem;font-weight:700;background:linear-gradient(90deg,#0969da,#1f6feb);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}
    .header-meta{{font-size:.85rem;color:#57606a}}
    .header-meta span{{color:#0969da;font-weight:600}}
    .back-link{{color:#0969da;text-decoration:none;font-size:.85rem}}
    .back-link:hover{{text-decoration:underline}}
    main{{max-width:1200px;margin:0 auto;padding:32px 24px}}
    .legend{{display:flex;flex-wrap:wrap;gap:16px;margin-bottom:24px;padding:16px 20px;background:#f6f8fa;border:1px solid #d0d7de;border-radius:12px}}
    .legend-item{{display:flex;align-items:center;gap:6px;font-size:.82rem;color:#57606a}}
    .legend-dot{{width:10px;height:10px;border-radius:50%;display:inline-block}}
    .dot-jp{{background:#cf222e}}.dot-us{{background:#0969da}}.dot-eu{{background:#bf8700}}.dot-cn{{background:#1a7f37}}
    .month-title{{font-size:1.3rem;font-weight:700;color:#1f2328;margin-bottom:16px;padding-bottom:8px;border-bottom:2px solid #0969da;display:inline-block}}
    .cal-grid{{display:grid;grid-template-columns:repeat(7,1fr);gap:2px;margin-bottom:24px}}
    .cal-header{{background:#ffffff;padding:8px 4px;text-align:center;font-size:.75rem;font-weight:600;color:#57606a}}
    .cal-header.sun{{color:#cf222e}}.cal-header.sat{{color:#0969da}}
    .cal-cell{{background:#f6f8fa;min-height:90px;padding:6px;border:1px solid #d0d7de;transition:border-color .2s}}
    .cal-cell:hover{{border-color:#0969da}}
    .cal-cell.empty{{background:#ffffff;border-color:#f6f8fa}}
    .cal-cell.today{{border:2px solid #0969da;background:#1a2233}}
    .cal-day{{font-size:.8rem;font-weight:600;color:#57606a;margin-bottom:4px}}
    .cal-cell.sun .cal-day{{color:#cf222e}}.cal-cell.sat .cal-day{{color:#0969da}}
    .cal-event{{font-size:.65rem;line-height:1.4;padding:2px 4px;border-radius:4px;margin-bottom:2px;display:block}}
    .cal-event.jp{{background:#ffebe9;color:#cf222e;border-left:2px solid #cf222e}}
    .cal-event.us{{background:#ddf4ff;color:#218bff;border-left:2px solid #0969da}}
    .cal-event.eu{{background:#fff8c5;color:#9a6700;border-left:2px solid #bf8700}}
    .cal-event.cn{{background:#dafbe1;color:#1a7f37;border-left:2px solid #1a7f37}}
    .cal-event .imp{{font-weight:700}}
    .event-list{{margin-top:8px}}
    .event-card{{display:flex;align-items:flex-start;gap:14px;padding:14px 16px;background:#f6f8fa;border:1px solid #d0d7de;border-radius:10px;margin-bottom:8px;transition:border-color .2s}}
    .event-card:hover{{border-color:#0969da}}
    .event-date-box{{min-width:52px;text-align:center;padding:8px 6px;background:#ffffff;border-radius:8px}}
    .event-date-day{{font-size:1.3rem;font-weight:700;color:#1f2328}}
    .event-date-dow{{font-size:.65rem;color:#57606a}}
    .event-body{{flex:1}}
    .event-name{{font-size:.88rem;font-weight:600;color:#1f2328;margin-bottom:4px}}
    .event-desc{{font-size:.78rem;color:#57606a;line-height:1.6}}
    .event-tag{{display:inline-block;font-size:.6rem;font-weight:600;padding:2px 6px;border-radius:4px;margin-right:4px}}
    .tag-jp{{background:#ffebe9;color:#cf222e}}.tag-us{{background:#ddf4ff;color:#218bff}}.tag-eu{{background:#fff8c5;color:#9a6700}}.tag-cn{{background:#dafbe1;color:#1a7f37}}
    .tag-high{{background:#da3633;color:#fff}}.tag-mid{{background:#bf8700;color:#ffffff}}
    .tab-bar{{display:flex;gap:8px;margin-bottom:20px}}
    .tab-btn{{padding:8px 20px;border:1px solid #d0d7de;border-radius:8px;background:#f6f8fa;color:#57606a;font-size:.85rem;font-weight:600;cursor:pointer;transition:all .2s}}
    .tab-btn:hover{{border-color:#0969da;color:#0969da}}
    .tab-btn.active{{background:#ddf4ff;border-color:#0969da;color:#0969da}}
    .beginner-box{{margin:24px 0;background:#ddf4ff;border:1px solid #54aeff;border-radius:8px;padding:14px 18px;font-size:.82rem;color:#1f6feb;line-height:1.8}}
    .beginner-box::before{{content:"🔰 経済指標の見方　";font-weight:700;color:#0969da}}
    footer{{background:#f6f8fa;border-top:1px solid #d0d7de;padding:20px 32px;text-align:center;font-size:.78rem;color:#6e7781}}
    footer a{{color:#0969da;text-decoration:none}}
    @media(max-width:768px){{.cal-cell{{min-height:60px;padding:3px}}.cal-event{{font-size:.55rem}}.header-inner{{flex-direction:column}}}}
  .nav-bar{{display:flex;flex-wrap:wrap;gap:10px;justify-content:center;margin-bottom:28px}}
  .nav-btn{{display:inline-flex;align-items:center;gap:8px;padding:11px 20px;background:#f6f8fa;border:1px solid #d0d7de;border-radius:10px;color:#57606a;text-decoration:none;font-size:.95rem;font-weight:600;transition:all .2s}}
  .nav-btn:hover{{border-color:#0969da;color:#0969da}}
  .nav-btn.current{{background:#0969da;border-color:#0969da;color:#fff}}
  .preview-banner{{display:flex;align-items:center;gap:18px;padding:18px 24px;margin-bottom:24px;background:linear-gradient(135deg,#dafbe1 0%,#ddf4ff 100%);border:1px solid #1a7f37;border-radius:12px;text-decoration:none;transition:all .2s}}
  .preview-banner:hover{{border-color:#1a7f37;background:linear-gradient(135deg,#cef0d3 0%,#b3d4ff 100%);transform:translateY(-1px)}}
  .preview-banner-icon{{font-size:2rem;flex-shrink:0}}
  .preview-banner-body{{flex:1;min-width:0}}
  .preview-banner-title{{font-size:1.05rem;font-weight:700;color:#1a7f37;margin-bottom:4px}}
  .preview-banner-desc{{font-size:.85rem;color:#424a53;line-height:1.6}}
  .preview-banner-desc strong{{color:#1f6feb}}
  .preview-banner-arrow{{font-size:1.5rem;color:#1a7f37;font-weight:700;flex-shrink:0}}
  @media(max-width:600px){{.preview-banner{{padding:14px 16px;gap:12px}}.preview-banner-icon{{font-size:1.6rem}}.preview-banner-title{{font-size:.95rem}}.preview-banner-desc{{font-size:.78rem}}}}
  </style>
  <!-- A8.net広告タグはここに貼る予定 -->
</head>
<body>
<header>
  <div class="header-inner">
    <div>
      <div class="header-title">📅 マクロ経済カレンダー</div>
      <div class="header-meta">最終更新: <span>{time_str}</span></div>
    </div>
  </div>
</header>
<main>
<nav class="nav-bar">
  <a class="nav-btn" href="index.html">📊 マーケットニュース</a>
  <a class="nav-btn current" href="calendar.html">📅 経済カレンダー</a>
  <a class="nav-btn" href="charts.html">📈 50年チャート</a>
  <a class="nav-btn" href="vix.html">😱 恐怖指数</a>
  <a class="nav-btn" href="market-health.html">🩺 市場健康度</a>
  <a class="nav-btn" href="hot-assets.html">🔥 出来高急増</a>
</nav>

  <a href="preview.html" class="preview-banner">
    <div class="preview-banner-icon">📰</div>
    <div class="preview-banner-body">
      <div class="preview-banner-title">明日〜数日先の重要指標プレビュー</div>
      <div class="preview-banner-desc">FOMC・米CPI・雇用統計・日銀会合など、近日発表される指標の<strong>結果別シナリオ</strong>を事前に解説しています。</div>
    </div>
    <div class="preview-banner-arrow">→</div>
  </a>

  <div class="legend">
    <div class="legend-item"><span class="legend-dot dot-jp"></span> 🇯🇵 日本</div>
    <div class="legend-item"><span class="legend-dot dot-us"></span> 🇺🇸 米国</div>
    <div class="legend-item"><span class="legend-dot dot-eu"></span> 🇪🇺 欧州</div>
    <div class="legend-item"><span class="legend-dot dot-cn"></span> 🇨🇳 中国</div>
    <div class="legend-item">⭐ = 最重要 ｜ ● = 重要</div>
  </div>
  <div class="tab-bar">
    <button class="tab-btn active" onclick="showMonth('cur')">{cur_month}月</button>
    <button class="tab-btn" onclick="showMonth('next')">{next_month}月</button>
  </div>
  <div class="month-section" id="month-cur">
    {grid_cur}
    {list_cur}
  </div>
  <div class="month-section" id="month-next" style="display:none">
    {grid_next}
    {list_next}
  </div>
  <div class="beginner-box">
    経済指標は発表の瞬間に株価・為替が大きく動くことがあります。特に「⭐最重要」マークの指標発表前後は値動きが荒くなりやすいため、初心者はこの時間帯の売買を避けるのが無難です。「予想値」と「実績値」の差（サプライズ）が大きいほど相場が動きます。長期投資なら日々の指標に一喜一憂せず、トレンドを確認する程度でOKです。
  </div>
</main>
<footer>
  <p>📅 マクロ経済カレンダー ─ 日本人投資家のための経済指標ガイド</p>
  <p style="margin-top:6px">※ 日程は変更される場合があります ｜ 最新情報は各公式サイトでご確認ください</p>
  <p style="margin-top:6px"><a href="index.html">📊 マーケットニュース</a> ｜ <a href="calendar.html">📅 経済カレンダー</a> ｜ <a href="charts.html">📈 50年チャート</a> ｜ <a href="vix.html">😱 VIX恐怖指数</a> ｜ <a href="market-health.html">🩺 市場健康度</a> ｜ <a href="hot-assets.html">🔥 出来高急増</a></p>
  <p style="margin-top:8px"><a href="about.html">運営者情報</a> &nbsp;|&nbsp; <a href="privacy.html">プライバシーポリシー</a> &nbsp;|&nbsp; <a href="contact.html">お問い合わせ</a></p>
</footer>
<script>
function showMonth(m) {{
  document.getElementById('month-cur').style.display = m === 'cur' ? 'block' : 'none';
  document.getElementById('month-next').style.display = m === 'next' ? 'block' : 'none';
  document.querySelectorAll('.tab-btn').forEach(function(btn) {{ btn.classList.remove('active'); }});
  event.target.classList.add('active');
}}
</script>
</body>
</html>"""


# ─────────────────────────────────────────
# 経済指標プレビュー（preview.html）
#   翌日〜数日内の重要指標を事前解説する
# ─────────────────────────────────────────
def build_preview_html(now_jst):
    """翌日〜3日先までの重要経済指標を事前解説するページを生成"""
    time_str = now_jst.strftime("%Y年%m月%d日 %H:%M JST")
    upcoming = find_upcoming_events(now_jst, days_ahead=3)

    DOW_JA = ["月", "火", "水", "木", "金", "土", "日"]

    def country_flag(c):
        return {"jp": "🇯🇵", "us": "🇺🇸", "eu": "🇪🇺", "cn": "🇨🇳"}.get(c, "")

    def country_label(c):
        return {"jp": "日本", "us": "米国", "eu": "欧州", "cn": "中国"}.get(c, "")

    def imp_label(imp):
        return "⭐最重要" if imp == "high" else "●重要"

    def imp_class(imp):
        return "tag-high" if imp == "high" else "tag-mid"

    def days_until(event_date):
        delta = (event_date - now_jst.date()).days
        if delta == 1:
            return "明日"
        elif delta == 2:
            return "明後日"
        else:
            return f"{delta}日後"

    # ── 各イベント詳細カード ──
    if not upcoming:
        cards_html = '''
<div class="empty-state">
  <div class="empty-icon">🌙</div>
  <div class="empty-title">直近3日間に重要指標の予定はありません</div>
  <div class="empty-msg">
    <p>今は相場が静かに推移しやすい時期です。<br>
    長期投資のポートフォリオを見直すのに適した時間かもしれません。</p>
    <p style="margin-top:12px"><a href="calendar.html" style="color:#0969da">📅 経済カレンダー</a> で今月・来月のスケジュールを確認できます。</p>
  </div>
</div>
'''
    else:
        cards_html = ""
        for ev in upcoming:
            d = ev["date"]
            dow_idx = d.weekday()
            dow_ja = DOW_JA[dow_idx]
            flag = country_flag(ev["country"])
            country = country_label(ev["country"])
            imp_lbl = imp_label(ev["importance"])
            imp_cls = imp_class(ev["importance"])
            until = days_until(d)
            short_desc = ev["desc"] if ev["desc"] else _get_event_detail(ev["name"])

            key, guide = match_indicator_guide(ev["name"])

            if guide:
                # 詳細解説あり
                scenarios_html = ""
                for label, impact in guide["scenarios"]:
                    scenarios_html += f'''<div class="scenario">
  <div class="scenario-label">▸ {label}</div>
  <div class="scenario-impact">{impact}</div>
</div>
'''
                watch_html = "".join(f"<li>{w}</li>" for w in guide["watch"])

                cards_html += f'''
<article class="indicator-card">
  <div class="card-header">
    <div class="card-date-block">
      <div class="card-until">{until}</div>
      <div class="card-date">{d.month}/{d.day}（{dow_ja}）</div>
    </div>
    <div class="card-title-block">
      <div class="card-tags">
        <span class="event-tag tag-{ev["country"]}">{flag} {country}</span>
        <span class="event-tag {imp_cls}">{imp_lbl}</span>
      </div>
      <h2 class="card-title">{guide["emoji"]} {guide["title"]}</h2>
      <div class="card-event-name">該当イベント: {ev["name"]}</div>
    </div>
  </div>

  <div class="card-section">
    <div class="section-label">⏰ 発表タイミング</div>
    <div class="section-body">{guide["release"]}</div>
  </div>

  <div class="card-section">
    <div class="section-label">📖 どんな指標？</div>
    <div class="section-body">{guide["what"]}</div>
  </div>

  <div class="card-section">
    <div class="section-label">💡 なぜ相場を動かす？</div>
    <div class="section-body">{guide["why"]}</div>
  </div>

  <div class="card-section">
    <div class="section-label">📊 結果別シナリオ</div>
    <div class="scenarios">
      {scenarios_html}
    </div>
  </div>

  <div class="card-section">
    <div class="section-label">🔍 注目ポイント</div>
    <ul class="watch-list">
      {watch_html}
    </ul>
  </div>

  <div class="card-tip">
    <strong>💼 投資家の心得</strong>
    {guide["tip"]}
  </div>

  {f'<div class="card-guide-link"><a href="{guide["guide_url"]}">📖 {guide["title"]}を詳しく解説した記事を見る →</a></div>' if guide.get("guide_url") else ""}
</article>
'''
            else:
                # 解説辞書になし → 簡易表示
                cards_html += f'''
<article class="indicator-card simple">
  <div class="card-header">
    <div class="card-date-block">
      <div class="card-until">{until}</div>
      <div class="card-date">{d.month}/{d.day}（{dow_ja}）</div>
    </div>
    <div class="card-title-block">
      <div class="card-tags">
        <span class="event-tag tag-{ev["country"]}">{flag} {country}</span>
        <span class="event-tag {imp_cls}">{imp_lbl}</span>
      </div>
      <h2 class="card-title">{ev["name"]}</h2>
      {f'<div class="card-event-name">{short_desc}</div>' if short_desc else ""}
    </div>
  </div>
</article>
'''

    # ── ヘッダー要約 ──
    high_count = sum(1 for ev in upcoming if ev["importance"] == "high")
    mid_count = sum(1 for ev in upcoming if ev["importance"] == "mid")
    if upcoming:
        summary_html = f'''
<div class="summary-box">
  <div class="summary-num">{len(upcoming)}件の経済指標</div>
  <div class="summary-detail">
    今後3日間に発表予定 — <span class="high-count">⭐最重要 {high_count}件</span> ｜ <span class="mid-count">●重要 {mid_count}件</span>
  </div>
</div>
'''
    else:
        summary_html = ""

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  {seo_head("preview.html", "明日の重要経済指標プレビュー", "米CPI・FOMC・雇用統計・日銀金融政策決定会合・ECB理事会など、明日〜数日先に発表される重要経済指標の事前解説。結果別の市場影響シナリオを日本人投資家向けに簡潔に解説。")}
  {GA4_TAG}
  <style>
    *{{margin:0;padding:0;box-sizing:border-box}}
    body{{font-family:'Segoe UI','Hiragino Sans','Yu Gothic',sans-serif;background:#ffffff;color:#1f2328;min-height:100vh;line-height:1.7}}
    header{{background:linear-gradient(135deg,#f6f8fa,#ffffff);border-bottom:1px solid #d0d7de;padding:24px 32px}}
    .header-inner{{max-width:1100px;margin:0 auto;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px}}
    .header-title{{font-size:1.6rem;font-weight:700;background:linear-gradient(90deg,#1a7f37,#1f6feb);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}
    .header-meta{{font-size:.85rem;color:#57606a}}
    .header-meta span{{color:#1a7f37;font-weight:600}}
    main{{max-width:1100px;margin:0 auto;padding:32px 24px}}
    .nav-bar{{display:flex;flex-wrap:wrap;gap:10px;justify-content:center;margin-bottom:28px}}
    .nav-btn{{display:inline-flex;align-items:center;gap:8px;padding:11px 20px;background:#f6f8fa;border:1px solid #d0d7de;border-radius:10px;color:#57606a;text-decoration:none;font-size:.95rem;font-weight:600;transition:all .2s}}
    .nav-btn:hover{{border-color:#1a7f37;color:#1a7f37}}
    .nav-btn.current{{background:#dafbe1;border-color:#1a7f37;color:#1a7f37}}
    .summary-box{{background:linear-gradient(135deg,#dafbe1,#ddf4ff);border:1px solid #1a7f37;border-radius:12px;padding:20px 24px;margin-bottom:28px;text-align:center}}
    .summary-num{{font-size:1.8rem;font-weight:700;color:#1a7f37;margin-bottom:6px}}
    .summary-detail{{font-size:.95rem;color:#424a53}}
    .high-count{{color:#cf222e;font-weight:600}}
    .mid-count{{color:#bf8700;font-weight:600}}
    .indicator-card{{background:#f6f8fa;border:1px solid #d0d7de;border-radius:14px;padding:24px 26px;margin-bottom:24px;transition:border-color .2s}}
    .indicator-card:hover{{border-color:#1a7f37}}
    .indicator-card.simple{{padding:18px 22px}}
    .card-header{{display:flex;align-items:flex-start;gap:18px;padding-bottom:18px;border-bottom:1px solid #d0d7de;margin-bottom:18px}}
    .card-date-block{{flex-shrink:0;text-align:center;background:#ffffff;border-radius:10px;padding:12px 14px;min-width:80px}}
    .card-until{{font-size:.7rem;color:#57606a;margin-bottom:2px;font-weight:600}}
    .card-date{{font-size:1.1rem;font-weight:700;color:#1a7f37}}
    .card-title-block{{flex:1;min-width:0}}
    .card-tags{{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:8px}}
    .card-title{{font-size:1.4rem;font-weight:700;color:#1f2328;margin-bottom:4px;line-height:1.3}}
    .card-event-name{{font-size:.82rem;color:#57606a}}
    .event-tag{{display:inline-block;font-size:.7rem;font-weight:600;padding:3px 9px;border-radius:5px}}
    .tag-jp{{background:#ffebe9;color:#cf222e}}
    .tag-us{{background:#ddf4ff;color:#218bff}}
    .tag-eu{{background:#fff8c5;color:#9a6700}}
    .tag-cn{{background:#dafbe1;color:#1a7f37}}
    .tag-high{{background:#da3633;color:#fff}}
    .tag-mid{{background:#bf8700;color:#ffffff}}
    .card-section{{margin-bottom:18px}}
    .card-section:last-of-type{{margin-bottom:0}}
    .section-label{{font-size:.85rem;font-weight:700;color:#1a7f37;margin-bottom:6px}}
    .section-body{{font-size:.92rem;color:#424a53;line-height:1.75}}
    .scenarios{{display:flex;flex-direction:column;gap:10px;margin-top:8px}}
    .scenario{{background:#ffffff;border:1px solid #d0d7de;border-radius:8px;padding:12px 14px}}
    .scenario-label{{font-size:.88rem;font-weight:600;color:#1f6feb;margin-bottom:4px}}
    .scenario-impact{{font-size:.85rem;color:#424a53;line-height:1.7}}
    .watch-list{{list-style:none;padding:0;margin-top:6px}}
    .watch-list li{{padding:6px 0 6px 20px;font-size:.88rem;color:#424a53;position:relative;line-height:1.6}}
    .watch-list li::before{{content:"▸";color:#1a7f37;position:absolute;left:0;font-weight:700}}
    .card-tip{{background:#ddf4ff;border-left:3px solid #0969da;border-radius:6px;padding:12px 16px;margin-top:18px;font-size:.85rem;color:#218bff;line-height:1.7}}
    .card-tip strong{{color:#1f6feb;display:block;margin-bottom:4px}}
    .card-guide-link{{margin-top:16px;text-align:center}}
    .card-guide-link a{{display:inline-block;padding:10px 22px;background:#ffffff;border:1px solid #54aeff;border-radius:8px;color:#1f6feb;text-decoration:none;font-size:.88rem;font-weight:600;transition:all .2s}}
    .card-guide-link a:hover{{border-color:#1a7f37;color:#1a7f37;background:#ddf4ff}}
    .empty-state{{text-align:center;padding:60px 20px;background:#f6f8fa;border:1px dashed #d0d7de;border-radius:14px}}
    .empty-icon{{font-size:3rem;margin-bottom:12px}}
    .empty-title{{font-size:1.2rem;font-weight:700;color:#1f2328;margin-bottom:12px}}
    .empty-msg{{font-size:.92rem;color:#57606a;line-height:1.8}}
    .beginner-box{{margin:24px 0;background:#ddf4ff;border:1px solid #54aeff;border-radius:8px;padding:14px 18px;font-size:.85rem;color:#1f6feb;line-height:1.85}}
    .beginner-box::before{{content:"🔰 このページの使い方　";font-weight:700;color:#0969da}}
    .disclaimer{{margin-top:20px;font-size:.78rem;color:#6e7781;line-height:1.7;padding:12px 16px;background:#f6f8fa;border:1px solid #d0d7de;border-radius:8px}}
    footer{{background:#f6f8fa;border-top:1px solid #d0d7de;padding:20px 32px;text-align:center;font-size:.78rem;color:#6e7781;margin-top:40px}}
    footer a{{color:#0969da;text-decoration:none}}
    @media(max-width:768px){{
      .header-inner{{flex-direction:column;align-items:flex-start}}
      .card-header{{flex-direction:column;gap:12px}}
      .card-date-block{{align-self:flex-start;min-width:auto;padding:8px 14px}}
      .card-title{{font-size:1.2rem}}
      .indicator-card{{padding:18px 16px}}
    }}
  </style>
  <!-- A8.net広告タグはここに貼る予定 -->
</head>
<body>
<header>
  <div class="header-inner">
    <div>
      <div class="header-title">📰 明日の経済指標プレビュー</div>
      <div class="header-meta">最終更新: <span>{time_str}</span></div>
    </div>
  </div>
</header>
<main>
<nav class="nav-bar">
  <a class="nav-btn" href="index.html">📊 マーケットニュース</a>
  <a class="nav-btn" href="calendar.html">📅 経済カレンダー</a>
  <a class="nav-btn" href="charts.html">📈 50年チャート</a>
  <a class="nav-btn" href="vix.html">😱 恐怖指数</a>
  <a class="nav-btn" href="market-health.html">🩺 市場健康度</a>
  <a class="nav-btn" href="hot-assets.html">🔥 出来高急増</a>
</nav>

  <div class="beginner-box">
    今後3日以内に発表される重要経済指標について、<strong>「どんな結果ならマーケットがどう動くか」</strong>を事前にシナリオ別に解説しています。発表の前にポジションを軽くするか、結果が出てから動くかの判断材料にお使いください。
  </div>

  {summary_html}

  {cards_html}

  <div class="disclaimer">
    ※ 各シナリオは過去の傾向に基づく一般的な解説であり、実際の相場の動きを保証するものではありません。指標発表時のヘッドラインや要人発言など複数の要因で動きが変わるため、参考情報としてご活用ください。投資判断はご自身の責任で行ってください。
  </div>

</main>
<footer>
  <p>📰 経済指標プレビュー ─ 日本人投資家のための事前解説ページ</p>
  <p style="margin-top:6px">毎日更新 ｜ <a href="index.html">📊 マーケットニュース</a> ｜ <a href="calendar.html">📅 経済カレンダー</a> ｜ <a href="charts.html">📈 50年チャート</a> ｜ <a href="vix.html">😱 VIX</a> ｜ <a href="market-health.html">🩺 市場健康度</a> ｜ <a href="hot-assets.html">🔥 出来高急増</a></p>
  <p style="margin-top:8px"><a href="about.html">運営者情報</a> &nbsp;|&nbsp; <a href="privacy.html">プライバシーポリシー</a> &nbsp;|&nbsp; <a href="contact.html">お問い合わせ</a></p>
</footer>
</body>
</html>"""


def build_market_health_html(data, vix_val, touraku, now_jst):
    """市場健康度ダッシュボード（market-health.html）を生成。
    動的に取れるもの: 米VIX, 騰落レシオ, 日経/S&P500終値
    固定値（手動メンテ）: 日経VI・CNN F&G・バフェット指数・CAPE・RSI等は
    月次で手動更新する想定。下記 MANUAL_METRICS を編集することで更新する。
    """
    # ─── 手動メンテ値（月1回くらい更新する） ───
    # 更新日: 2026-04-20 時点の値
    MANUAL_METRICS = {
        "manual_date": "2026-04-20",
        "nikkei_vi": 32.9,          # 日経VI（大阪取引所）
        "cnn_fg": 68,               # CNN Fear & Greed（0-100）
        "crypto_fg": 50,            # Crypto Fear & Greed（0-100）
        "buffett_us": 232,          # 米国バフェット指数 %
        "buffett_jp": 142,          # 日本バフェット指数 %
        "cape": 36.5,               # S&P500 シラーPER
        "nikkei_per": 17.8,         # 日経平均 予想PER
    }

    def _tag(color, label):
        return f'<span class="tag" style="background:{color};color:#fff">{label}</span>'

    def _classify_nikkei_vi(v):
        if v < 20: return "#1a7f37", "落ち着き", min(v / 50 * 100, 100)
        if v < 30: return "#9a6700", "通常", v / 50 * 100
        if v < 40: return "#bf3989", "やや警戒", v / 50 * 100
        return "#da3633", "警戒", min(v / 50 * 100, 100)

    def _classify_fg(v):
        # CNN/Crypto Fear&Greed: 0=Extreme Fear, 100=Extreme Greed
        if v < 25: return "#1a7f37", "極度の恐怖"
        if v < 45: return "#0969da", "恐怖"
        if v < 55: return "#9a6700", "中立"
        if v < 75: return "#bf3989", "強欲"
        return "#da3633", "極度の強欲"

    def _classify_buffett(v):
        if v < 70: return "#1a7f37", "大きく割安"
        if v < 100: return "#0969da", "適正"
        if v < 135: return "#9a6700", "やや割高"
        if v < 180: return "#bf3989", "割高"
        return "#da3633", "大きく割高"

    def _classify_cape(v):
        if v < 15: return "#1a7f37", "割安"
        if v < 22: return "#0969da", "適正"
        if v < 30: return "#9a6700", "やや割高"
        if v < 40: return "#bf3989", "歴史的高水準"
        return "#da3633", "バブル級"

    def _classify_per(v):
        if v < 13: return "#1a7f37", "割安"
        if v < 16: return "#0969da", "やや割安"
        if v < 20: return "#0969da", "適正"
        if v < 25: return "#9a6700", "やや割高"
        return "#bf3989", "割高"

    # 手動値を分類
    nvi = MANUAL_METRICS["nikkei_vi"]
    nvi_color, nvi_label, nvi_pos = _classify_nikkei_vi(nvi)
    cnn = MANUAL_METRICS["cnn_fg"]
    cnn_color, cnn_label = _classify_fg(cnn)
    cry = MANUAL_METRICS["crypto_fg"]
    cry_color, cry_label = _classify_fg(cry)
    bfu = MANUAL_METRICS["buffett_us"]
    bfu_color, bfu_label = _classify_buffett(bfu)
    bfu_pos = min(bfu / 250 * 100, 100)
    bfj = MANUAL_METRICS["buffett_jp"]
    bfj_color, bfj_label = _classify_buffett(bfj)
    bfj_pos = min(bfj / 250 * 100, 100)
    cape = MANUAL_METRICS["cape"]
    cape_color, cape_label = _classify_cape(cape)
    cape_pos = min(cape / 50 * 100, 100)
    nper = MANUAL_METRICS["nikkei_per"]
    nper_color, nper_label = _classify_per(nper)
    nper_pos = min(nper / 30 * 100, 100)
    mdate = MANUAL_METRICS["manual_date"]

    # 米VIX
    if vix_val is None:
        vix_disp, vix_tag, vix_color, vix_pos = "N/A", _tag("#57606a", "取得不可"), "#57606a", 30
    elif vix_val < 15:
        vix_disp, vix_tag, vix_color, vix_pos = f"{vix_val:.1f}", _tag("#1a7f37", "落ち着き"), "#1a7f37", 15
    elif vix_val < 20:
        vix_disp, vix_tag, vix_color, vix_pos = f"{vix_val:.1f}", _tag("#1a7f37", "通常"), "#1a7f37", 25
    elif vix_val < 30:
        vix_disp, vix_tag, vix_color, vix_pos = f"{vix_val:.1f}", _tag("#9a6700", "中位"), "#9a6700", 45
    elif vix_val < 40:
        vix_disp, vix_tag, vix_color, vix_pos = f"{vix_val:.1f}", _tag("#bf3989", "警戒"), "#bf3989", 65
    else:
        vix_disp, vix_tag, vix_color, vix_pos = f"{vix_val:.1f}", _tag("#da3633", "パニック"), "#da3633", 85

    # 騰落レシオ
    if touraku is None:
        tr_disp, tr_tag, tr_color, tr_pos = "N/A", _tag("#57606a", "取得不可"), "#57606a", 50
    elif touraku < 70:
        tr_disp, tr_tag, tr_color, tr_pos = f"{touraku}%", _tag("#1a7f37", "売られすぎ"), "#1a7f37", 15
    elif touraku < 100:
        tr_disp, tr_tag, tr_color, tr_pos = f"{touraku}%", _tag("#0969da", "適正"), "#0969da", 40
    elif touraku < 120:
        tr_disp, tr_tag, tr_color, tr_pos = f"{touraku}%", _tag("#9a6700", "やや加熱"), "#9a6700", 60
    elif touraku < 140:
        tr_disp, tr_tag, tr_color, tr_pos = f"{touraku}%", _tag("#bf3989", "買われすぎ"), "#bf3989", 80
    else:
        tr_disp, tr_tag, tr_color, tr_pos = f"{touraku}%", _tag("#da3633", "過熱"), "#da3633", 95

    date_str = now_jst.strftime('%Y年%m月%d日 %H:%M JST')

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
{seo_head("market-health.html", "市場健康度ダッシュボード", "VIX・恐怖&強欲指数・バフェット指数・CAPEレシオ・騰落レシオを一画面で可視化。割高/割安/過熱/底値圏を色分け表示し、相場全体の温度感を瞬時に判断できます。")}
{GA4_TAG}
<style>
  *{{margin:0;padding:0;box-sizing:border-box}}
  body{{font-family:'Segoe UI','Hiragino Sans','Yu Gothic','Meiryo',sans-serif;background:#ffffff;color:#1f2328;min-height:100vh;font-size:16px;line-height:1.75}}
  header{{background:linear-gradient(135deg,#f6f8fa,#ffffff);border-bottom:1px solid #d0d7de;padding:26px 32px;text-align:center}}
  .header-title{{font-size:1.9rem;font-weight:700;background:linear-gradient(90deg,#0969da,#7cf2c8);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;margin-bottom:6px}}
  .header-meta{{font-size:1rem;color:#57606a}}
  main{{max-width:1200px;margin:0 auto;padding:32px 24px}}
  .nav-bar{{display:flex;flex-wrap:wrap;gap:10px;justify-content:center;margin-bottom:28px}}
  .nav-btn{{display:inline-flex;align-items:center;gap:8px;padding:11px 20px;background:#f6f8fa;border:1px solid #d0d7de;border-radius:10px;color:#57606a;text-decoration:none;font-size:.95rem;font-weight:600;transition:all .2s}}
  .nav-btn:hover{{border-color:#0969da;color:#0969da}}
  .nav-btn.current{{background:#0969da;border-color:#0969da;color:#fff}}
  .summary{{background:linear-gradient(135deg,#2a1f0e,#1c1508);border:1px solid #9a6700;border-radius:14px;padding:22px 26px;margin-bottom:28px}}
  .summary h2{{font-size:1.15rem;color:#9a6700;margin-bottom:10px}}
  .summary p{{color:#1f2328;font-size:.98rem}}
  .section{{margin-bottom:32px}}
  .section-title{{font-size:1.25rem;font-weight:700;color:#1f2328;margin-bottom:16px;padding:6px 0 6px 14px;border-left:4px solid #0969da}}
  .cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px}}
  .card{{background:#f6f8fa;border:1px solid #d0d7de;border-radius:12px;padding:22px;transition:transform .15s,border-color .2s}}
  .card:hover{{border-color:#0969da;transform:translateY(-2px)}}
  .card-header{{display:flex;align-items:baseline;gap:10px;margin-bottom:6px;flex-wrap:wrap}}
  .card-title{{font-size:1.05rem;font-weight:700;color:#1f2328}}
  .card-sub{{font-size:.78rem;color:#57606a}}
  .big-num{{font-size:2.6rem;font-weight:800;margin:6px 0}}
  .tag{{display:inline-block;font-size:.82rem;font-weight:700;padding:4px 12px;border-radius:999px;color:#001}}
  .gauge{{position:relative;height:14px;border-radius:7px;margin:14px 0 8px;overflow:visible}}
  .gauge.fear{{background:linear-gradient(90deg,#238636 0%,#1a7f37 25%,#9a6700 50%,#cf222e 75%,#da3633 100%)}}
  .gauge.val{{background:linear-gradient(90deg,#1a7f37 0%,#0969da 40%,#9a6700 65%,#cf222e 85%,#da3633 100%)}}
  .gauge.vol{{background:linear-gradient(90deg,#1a7f37 0%,#9a6700 50%,#cf222e 75%,#da3633 100%)}}
  .gauge-pin{{position:absolute;top:-4px;width:5px;height:22px;background:#fff;border-radius:3px;transform:translateX(-50%);box-shadow:0 0 8px rgba(255,255,255,.7)}}
  .gauge-labels{{display:flex;justify-content:space-between;font-size:.7rem;color:#6e7781;margin-top:4px}}
  .comment{{font-size:.93rem;color:#c8d1e6;margin-top:10px;line-height:1.7}}
  .beginner{{margin-top:12px;background:#ddf4ff;border:1px solid #54aeff;border-radius:8px;padding:12px 14px;font-size:.86rem;color:#1f6feb;line-height:1.75}}
  .beginner::before{{content:"🔰 初心者メモ　";font-weight:700;color:#0969da}}
  .formula{{font-family:'Consolas',monospace;background:#0a0d13;border:1px solid #d0d7de;border-radius:6px;padding:6px 10px;font-size:.82rem;color:#218bff;margin:8px 0;display:inline-block}}
  footer{{background:#f6f8fa;border-top:1px solid #d0d7de;padding:24px 32px;text-align:center;font-size:.9rem;color:#57606a;line-height:1.85}}
  footer a{{color:#0969da;text-decoration:none}}
  @media(max-width:600px){{.big-num{{font-size:2.1rem}}.header-title{{font-size:1.4rem}}}}
</style>
  <!-- A8.net広告タグはここに貼る予定 -->
</head>
<body>
<header>
  <div class="header-title">🩺 市場健康度ダッシュボード</div>
  <div class="header-meta">最終更新: {date_str} ／ 投資家心理・バリュエーション・ボラティリティを総合診断</div>
</header>
<main>
  <nav class="nav-bar">
    <a class="nav-btn" href="index.html">📊 マーケットニュース</a>
    <a class="nav-btn" href="calendar.html">📅 経済カレンダー</a>
    <a class="nav-btn" href="charts.html">📈 50年チャート</a>
    <a class="nav-btn" href="vix.html">😱 恐怖指数</a>
    <a class="nav-btn current" href="market-health.html">🩺 市場健康度</a>
    <a class="nav-btn" href="hot-assets.html">🔥 出来高急増</a>
  </nav>

  <div style="display:flex;flex-wrap:wrap;gap:10px;justify-content:center;margin-bottom:24px">
    <a href="guide-buffett-indicator.html" style="display:inline-block;padding:9px 18px;background:#0969da;border:1px solid #0969da;border-radius:8px;color:#fff;text-decoration:none;font-size:.88rem;font-weight:600">📖 バフェット指数とは？</a>
    <a href="guide-fear-greed.html" style="display:inline-block;padding:9px 18px;background:#0969da;border:1px solid #0969da;border-radius:8px;color:#fff;text-decoration:none;font-size:.88rem;font-weight:600">📖 恐怖と強欲指数とは？</a>
    <a href="guide-vix.html" style="display:inline-block;padding:9px 18px;background:#0969da;border:1px solid #0969da;border-radius:8px;color:#fff;text-decoration:none;font-size:.88rem;font-weight:600">📖 VIX恐怖指数とは？</a>
  </div>

  <section class="summary">
    <h2>⚠️ 総合診断: センチメントとバリュエーションを一目で確認</h2>
    <p>
      センチメント・ボラティリティ・割高割安を総合判定。
      <b>米VIX {vix_disp}</b> ／ <b>騰落レシオ {tr_disp}</b> はリアルタイム更新。
      その他の指標は <b>{mdate} 時点の参考値</b>（月次手動更新）。
      <br>● 青=適正／割安　● 橙=やや割高・過熱　● 赤=危険水準
    </p>
  </section>

  <section class="section">
    <div class="section-title">① ボラティリティ（恐怖指数）</div>
    <div class="cards">
      <article class="card">
        <div class="card-header"><div class="card-title">😱 米国 VIX</div><div class="card-sub">S&amp;P500 オプションIV</div></div>
        <div class="big-num" style="color:{vix_color}">{vix_disp} {vix_tag}</div>
        <div class="gauge vol"><div class="gauge-pin" style="left:{vix_pos}%"></div></div>
        <div class="gauge-labels"><span>10</span><span>20</span><span>30</span><span>40</span><span>50+</span></div>
        <p class="comment">20〜25は通常モード。30超は調整警戒、40超はパニック領域。リアルタイム値。</p>
        <div class="beginner">VIXは「今後30日間にS&amp;P500がどれだけ動くと投資家が予想しているか」。高いほど不安感が強い。</div>
      </article>
      <article class="card">
        <div class="card-header"><div class="card-title">🗾 日経VI</div><div class="card-sub">日経225 オプションIV ／ {mdate}時点</div></div>
        <div class="big-num" style="color:{nvi_color}">{nvi} {_tag(nvi_color, nvi_label)}</div>
        <div class="gauge vol"><div class="gauge-pin" style="left:{nvi_pos:.0f}%"></div></div>
        <div class="gauge-labels"><span>10</span><span>20</span><span>30</span><span>40</span><span>50+</span></div>
        <p class="comment">大阪取引所が算出する日本版VIX。米VIX＋5〜10が通常。40超は警戒圏。</p>
        <div class="beginner">最新値は <a href="https://www.jpx.co.jp/markets/indices/nikkei225-vi/" target="_blank" style="color:#1f6feb">JPX公式</a></div>
      </article>
      <article class="card">
        <div class="card-header"><div class="card-title">📊 騰落レシオ（25日）</div><div class="card-sub">東証プライム</div></div>
        <div class="big-num" style="color:{tr_color}">{tr_disp} {tr_tag}</div>
        <div class="gauge fear"><div class="gauge-pin" style="left:{tr_pos}%"></div></div>
        <div class="gauge-labels"><span>30</span><span>70</span><span>100</span><span>120</span><span>170</span></div>
        <p class="comment">120%以上は買われすぎ、70%以下は売られすぎの目安。リアルタイム値。</p>
        <div class="beginner">値上がり銘柄数÷値下がり銘柄数×100。日本株の短期的な過熱感を測る定番指標。</div>
      </article>
    </div>
  </section>

  <section class="section">
    <div class="section-title">② 投資家センチメント（{mdate}時点・月次更新）</div>
    <div class="cards">
      <article class="card">
        <div class="card-header"><div class="card-title">📊 CNN Fear &amp; Greed</div><div class="card-sub">米国株・7指標合成</div></div>
        <div class="big-num" style="color:{cnn_color}">{cnn} {_tag(cnn_color, cnn_label)}</div>
        <div class="gauge fear"><div class="gauge-pin" style="left:{cnn}%"></div></div>
        <div class="gauge-labels"><span>0 恐怖</span><span>25</span><span>50</span><span>75</span><span>100 強欲</span></div>
        <p class="comment">0=極度の恐怖、100=極度の強欲。75超で「他人が強欲なときは恐れよ」領域。</p>
        <div class="beginner">最新値は <a href="https://edition.cnn.com/markets/fear-and-greed" target="_blank" style="color:#1f6feb">CNN公式</a></div>
      </article>
      <article class="card">
        <div class="card-header"><div class="card-title">₿ Crypto Fear &amp; Greed</div><div class="card-sub">BTC/暗号資産</div></div>
        <div class="big-num" style="color:{cry_color}">{cry} {_tag(cry_color, cry_label)}</div>
        <div class="gauge fear"><div class="gauge-pin" style="left:{cry}%"></div></div>
        <div class="gauge-labels"><span>0 恐怖</span><span>25</span><span>50</span><span>75</span><span>100 強欲</span></div>
        <p class="comment">alternative.me が公開。ボラ・出来高・SNS・ドミナンスから算出。BTC逆張りの定番指標。</p>
        <div class="beginner">最新値は <a href="https://alternative.me/crypto/fear-and-greed-index/" target="_blank" style="color:#1f6feb">alternative.me</a></div>
      </article>
    </div>
  </section>

  <section class="section">
    <div class="section-title">③ バリュエーション（{mdate}時点・月次更新）</div>
    <div class="cards">
      <article class="card">
        <div class="card-header"><div class="card-title">💰 バフェット指数（米）</div><div class="card-sub">株式時価総額 ÷ GDP</div></div>
        <div class="big-num" style="color:{bfu_color}">{bfu}% {_tag(bfu_color, bfu_label)}</div>
        <div class="gauge val"><div class="gauge-pin" style="left:{bfu_pos:.0f}%"></div></div>
        <div class="gauge-labels"><span>70</span><span>100</span><span>135</span><span>180</span><span>250</span></div>
        <div class="formula">米国株時価総額 (Wilshire 5000) ÷ 米GDP × 100</div>
        <p class="comment">バフェット本人「200%は火遊び」発言水準を{'超過' if bfu>=200 else '未満'}。70%以下=割安、135%以上=割高。</p>
        <div class="beginner">最新値は <a href="https://www.currentmarketvaluation.com/models/buffett-indicator.php" target="_blank" style="color:#1f6feb">currentmarketvaluation.com</a></div>
      </article>
      <article class="card">
        <div class="card-header"><div class="card-title">🗾 バフェット指数（日）</div><div class="card-sub">東証時価総額 ÷ 日本GDP</div></div>
        <div class="big-num" style="color:{bfj_color}">{bfj}% {_tag(bfj_color, bfj_label)}</div>
        <div class="gauge val"><div class="gauge-pin" style="left:{bfj_pos:.0f}%"></div></div>
        <div class="gauge-labels"><span>70</span><span>100</span><span>135</span><span>180</span><span>250</span></div>
        <div class="formula">東証全銘柄時価総額 ÷ 日本名目GDP × 100</div>
        <p class="comment">1989年バブル期で約140%。100%を超えると割高圏の目安。</p>
        <div class="beginner">JPX公表の時価総額÷内閣府公表の名目GDPで計算可能。</div>
      </article>
      <article class="card">
        <div class="card-header"><div class="card-title">📈 S&amp;P500 CAPE（シラーPER）</div><div class="card-sub">10年平均利益で算出</div></div>
        <div class="big-num" style="color:{cape_color}">{cape} {_tag(cape_color, cape_label)}</div>
        <div class="gauge val"><div class="gauge-pin" style="left:{cape_pos:.0f}%"></div></div>
        <div class="gauge-labels"><span>10</span><span>15</span><span>22</span><span>30</span><span>50+</span></div>
        <div class="formula">S&amp;P500 ÷ （過去10年のインフレ調整済みEPS平均）</div>
        <p class="comment">20世紀平均15.2。30超は歴史的高水準。2000年ITバブル期44、1929年大恐慌前32。</p>
        <div class="beginner">最新値は <a href="https://www.multpl.com/shiller-pe" target="_blank" style="color:#1f6feb">multpl.com</a></div>
      </article>
      <article class="card">
        <div class="card-header"><div class="card-title">🇯🇵 日経平均 PER（予想）</div><div class="card-sub">12ヶ月先の予想利益ベース</div></div>
        <div class="big-num" style="color:{nper_color}">{nper}倍 {_tag(nper_color, nper_label)}</div>
        <div class="gauge val"><div class="gauge-pin" style="left:{nper_pos:.0f}%"></div></div>
        <div class="gauge-labels"><span>10</span><span>13</span><span>16</span><span>20</span><span>30</span></div>
        <p class="comment">歴史平均14〜16倍。米国S&amp;P500の約24倍よりは日本株が割安感あり。</p>
        <div class="beginner">最新値は <a href="https://indexes.nikkei.co.jp/nkave/statistics/dataload" target="_blank" style="color:#1f6feb">日経インデックス公式</a></div>
      </article>
    </div>
  </section>

  <section class="summary" style="background:linear-gradient(135deg,#0e1d2f,#0a1420);border-color:#0969da">
    <h2 style="color:#0969da">📋 投資判断のヒント</h2>
    <p>
      <b>短期（〜3ヶ月）</b>: VIX・騰落レシオの極端な値（VIX 30超 or 騰落120超/70未満）は転換点シグナル。<br>
      <b>中期（3〜12ヶ月）</b>: バフェット指数・CAPEが歴史的高水準なら <b>新規資金一括投入は避け、段階投資＋分散</b> が鉄則。<br>
      <b>長期（1年以上）</b>: 日本株・新興国・金・債券などへの分散で米国一極集中リスクを下げる戦略が有効。
    </p>
  </section>

</main>
<footer>
  <p>🩺 市場健康度ダッシュボード ─ 日本人投資家のための総合診断ツール</p>
  <p style="margin-top:6px">データ出典: Yahoo Finance (VIX・騰落) ／ CNN ／ alternative.me ／ currentmarketvaluation.com ／ Shiller PE (multpl.com) ／ JPX 等</p>
  <p style="margin-top:6px">※ 本ページはAIによる自動集計・要約であり、投資判断はご自身の責任でお願いいたします。</p>
  <p style="margin-top:6px">
    <a href="index.html">📊 マーケットニュース</a> ｜
    <a href="calendar.html">📅 経済カレンダー</a> ｜
    <a href="charts.html">📈 50年チャート</a> ｜
    <a href="vix.html">😱 VIX恐怖指数</a>
  </p>
  <p style="margin-top:8px"><a href="about.html">運営者情報</a> &nbsp;|&nbsp; <a href="privacy.html">プライバシーポリシー</a> &nbsp;|&nbsp; <a href="contact.html">お問い合わせ</a></p>
</footer>
</body>
</html>"""


def safe_write(path, content):
    """一時ファイルに書き込んでからリネーム（途中切れ防止）

    強化版:
      - コンテンツが空 / 異常に短い / HTMLが途中切れの場合は書き込みを拒否
      - fsync() で物理書き込みを保証
      - 書き込み後にサイズ検証
    """
    import tempfile
    dir_name = os.path.dirname(path)
    tmp_path = None

    # 0) コンテンツ健全性チェック（HTMLは </html> で終わるべき）
    if content is None:
        print(f"❌ 書き込み拒否 ({path}): content=None")
        return False
    if not isinstance(content, str):
        print(f"❌ 書き込み拒否 ({path}): content型不正 {type(content)}")
        return False
    content_len = len(content)
    if content_len < 1000:
        print(f"❌ 書き込み拒否 ({path}): コンテンツが短すぎる ({content_len}文字)")
        return False
    # HTMLの完整性チェック
    if path.endswith(".html"):
        tail = content[-200:].lower()
        if "</html>" not in tail:
            print(f"❌ 書き込み拒否 ({path}): </html>閉じタグが見つからない — 途中切れの可能性")
            print(f"   末尾200文字: ...{content[-200:]!r}")
            return False

    try:
        fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp", prefix="mktwatch_")
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
            f.flush()
            try:
                os.fsync(f.fileno())
            except OSError:
                pass  # fsyncが使えない環境では無視

        # 書き込み後にサイズ検証
        written_size = os.path.getsize(tmp_path)
        expected_min = int(len(content.encode("utf-8")) * 0.95)  # UTF-8換算で95%以上
        if written_size < expected_min:
            print(f"❌ 書き込み不完全 ({path}): 期待>={expected_min}B, 実際={written_size}B")
            os.remove(tmp_path)
            return False

        # Windows: 既存ファイルがあれば先に削除
        if os.path.exists(path):
            os.replace(tmp_path, path)
        else:
            os.rename(tmp_path, path)
        print(f"   書き込みサイズ: {written_size:,}B ({content_len:,}文字)")
        return True
    except Exception as e:
        print(f"❌ ファイル書き込みエラー ({path}): {e}")
        import traceback; traceback.print_exc()
        # 一時ファイルが残っていれば削除
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        return False


def build_event_rows():
    """イベント一覧テーブル行を生成"""
    event_rows = ""
    for ev in sorted(HISTORICAL_EVENTS, key=lambda x: x["date"], reverse=True):
        asset_badges = ""
        map_ = {"nikkei": "日経", "sp500": "S&P", "usdjpy": "ドル円", "gold": "金"}
        for a in ev["assets"]:
            asset_badges += f'<span class="badge">{map_.get(a, a)}</span>'
        event_rows += f"""
        <tr>
          <td class="ev-date">{ev["date"]}</td>
          <td class="ev-label">{ev["label"]}</td>
          <td>{asset_badges}</td>
          <td class="ev-desc">{ev["desc"]}</td>
        </tr>"""
    return event_rows


def build_charts_html(hist, now_jst):
    """50年チャート＋歴史的イベント一覧を別ページ（charts.html）として生成"""
    time_str = now_jst.strftime("%Y年%#m月%#d日 %H:%M JST") if os.name == "nt" else now_jst.strftime("%Y年%-m月%-d日 %H:%M JST")

    nk_dates,  nk_prices  = hist.get("nikkei", ([], []))
    sp_dates,  sp_prices  = hist.get("sp500",  ([], []))
    fx_dates,  fx_prices  = hist.get("usdjpy", ([], []))
    gld_dates, gld_prices = hist.get("gold",   ([], []))

    nk_ann  = json.dumps(build_annotations("nikkei", nk_dates),  ensure_ascii=False)
    sp_ann  = json.dumps(build_annotations("sp500",  sp_dates),  ensure_ascii=False)
    fx_ann  = json.dumps(build_annotations("usdjpy", fx_dates),  ensure_ascii=False)
    gld_ann = json.dumps(build_annotations("gold",   gld_dates), ensure_ascii=False)

    event_rows = build_event_rows()

    has_charts = any([nk_dates, sp_dates, fx_dates, gld_dates])
    no_data_msg = '<p style="color:#cf222e;text-align:center;padding:40px">⚠ チャートデータを取得できませんでした。次回更新時に再取得されます。</p>' if not has_charts else ''

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  {seo_head("charts.html", "50年価格チャート＆歴史的イベント", "日経平均・S&P500・ドル円・金の50年長期チャートを、ニクソンショック/プラザ合意/リーマン/コロナショックなど主要イベントと重ねて表示。歴史的視点で相場を読み解けます。")}
  {GA4_TAG}
  <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/chartjs-plugin-annotation/3.0.1/chartjs-plugin-annotation.min.js"></script>
  <style>
    *{{margin:0;padding:0;box-sizing:border-box}}
    body{{font-family:'Segoe UI','Hiragino Sans','Yu Gothic',sans-serif;background:#ffffff;color:#1f2328;min-height:100vh}}
    header{{background:linear-gradient(135deg,#f6f8fa,#ffffff);border-bottom:1px solid #d0d7de;padding:24px 32px}}
    .header-inner{{max-width:1200px;margin:0 auto;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px}}
    .header-title{{font-size:1.6rem;font-weight:700;background:linear-gradient(90deg,#0969da,#1f6feb);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}
    .header-meta{{font-size:.85rem;color:#57606a}}
    .header-meta span{{color:#0969da;font-weight:600}}
    .back-link{{display:inline-flex;align-items:center;gap:6px;color:#0969da;text-decoration:none;font-size:.9rem;padding:8px 16px;border:1px solid #d0d7de;border-radius:8px;transition:background .2s}}
    .back-link:hover{{background:#f6f8fa}}
    main{{max-width:1200px;margin:0 auto;padding:32px 24px}}
    .section-title{{font-size:1.1rem;font-weight:600;color:#57606a;text-transform:uppercase;letter-spacing:.08em;margin-bottom:16px}}
    .chart-section{{background:#f6f8fa;border:1px solid #d0d7de;border-radius:12px;padding:24px;margin-bottom:24px}}
    .chart-title{{font-size:1rem;font-weight:700;color:#1f2328;margin-bottom:4px}}
    .chart-subtitle{{font-size:.78rem;color:#57606a;margin-bottom:16px}}
    .chart-hint{{font-size:.75rem;color:#9a6700;margin-bottom:12px}}
    .chart-wrap{{position:relative;height:320px}}
    .event-section{{background:#f6f8fa;border:1px solid #d0d7de;border-radius:12px;padding:24px;margin-bottom:32px;overflow-x:auto}}
    table{{width:100%;border-collapse:collapse;font-size:.83rem}}
    th{{text-align:left;padding:10px 12px;border-bottom:2px solid #d0d7de;color:#57606a;font-weight:600;white-space:nowrap}}
    td{{padding:10px 12px;border-bottom:1px solid #d0d7de;vertical-align:top;line-height:1.5}}
    tr:hover td{{background:#ffffff}}
    .ev-date{{color:#0969da;white-space:nowrap;font-weight:600}}
    .ev-label{{font-weight:700;color:#1f2328;white-space:nowrap}}
    .ev-desc{{color:#57606a;font-size:.8rem}}
    .badge{{display:inline-block;background:#d0d7de;color:#1f6feb;border:1px solid #d0d7de;border-radius:4px;padding:2px 6px;font-size:.72rem;margin:2px 2px 2px 0;white-space:nowrap}}
    footer{{background:#f6f8fa;border-top:1px solid #d0d7de;padding:20px 32px;text-align:center;font-size:.78rem;color:#6e7781}}
    footer a{{color:#0969da;text-decoration:none}}
    @media(max-width:600px){{.header-inner{{flex-direction:column}}.chart-wrap{{height:240px}}}}
  .nav-bar{{display:flex;flex-wrap:wrap;gap:10px;justify-content:center;margin-bottom:28px}}
  .nav-btn{{display:inline-flex;align-items:center;gap:8px;padding:11px 20px;background:#f6f8fa;border:1px solid #d0d7de;border-radius:10px;color:#57606a;text-decoration:none;font-size:.95rem;font-weight:600;transition:all .2s}}
  .nav-btn:hover{{border-color:#0969da;color:#0969da}}
  .nav-btn.current{{background:#0969da;border-color:#0969da;color:#fff}}
  </style>
  <!-- A8.net広告タグはここに貼る予定 -->
</head>
<body>
<header>
  <div class="header-inner">
    <div>
      <div class="header-title">📈 50年価格チャート</div>
      <div class="header-meta">最終更新: <span>{time_str}</span></div>
    </div>
  </div>
</header>
<main>

<nav class="nav-bar">
  <a class="nav-btn" href="index.html">📊 マーケットニュース</a>
  <a class="nav-btn" href="calendar.html">📅 経済カレンダー</a>
  <a class="nav-btn current" href="charts.html">📈 50年チャート</a>
  <a class="nav-btn" href="vix.html">😱 恐怖指数</a>
  <a class="nav-btn" href="market-health.html">🩺 市場健康度</a>
  <a class="nav-btn" href="hot-assets.html">🔥 出来高急増</a>
</nav>

  {no_data_msg}

  <p class="section-title">📈 歴史的価格チャート（イベント付き）</p>

  <div class="chart-section">
    <div class="chart-title">株式市場 — 日経平均 / S&amp;P500</div>
    <div class="chart-subtitle">年次終値（左軸: 日経平均円、右軸: S&amp;P500ポイント）</div>
    <div class="chart-hint">💡 点線マーカーにカーソルを当てるとイベント名が表示されます</div>
    <div class="chart-wrap"><canvas id="chartStocks"></canvas></div>
  </div>

  <div class="chart-section">
    <div class="chart-title">為替 — USD/JPY（ドル円）</div>
    <div class="chart-subtitle">年次終値（円/ドル）</div>
    <div class="chart-hint">💡 点線マーカーにカーソルを当てるとイベント名が表示されます</div>
    <div class="chart-wrap"><canvas id="chartFX"></canvas></div>
  </div>

  <div class="chart-section">
    <div class="chart-title">ゴールド — 金価格（スポット/先物）</div>
    <div class="chart-subtitle">年次終値（USD/oz）</div>
    <div class="chart-hint">💡 点線マーカーにカーソルを当てるとイベント名が表示されます</div>
    <div class="chart-wrap"><canvas id="chartGold"></canvas></div>
  </div>

  <p class="section-title">📋 歴史的イベント一覧</p>
  <div class="event-section">
    <table>
      <thead><tr><th>年月</th><th>イベント</th><th>関連資産</th><th>概要</th></tr></thead>
      <tbody>{event_rows}</tbody>
    </table>
  </div>

</main>
<footer>
  <p>データソース: Yahoo Finance (yfinance) &nbsp;|&nbsp;
  <a href="index.html">📊 マーケットニュース</a> &nbsp;|&nbsp;
  <a href="calendar.html">📅 経済カレンダー</a> &nbsp;|&nbsp;
  <a href="charts.html">📈 50年チャート</a> &nbsp;|&nbsp;
  <a href="vix.html">😱 VIX</a> &nbsp;|&nbsp;
  <a href="market-health.html">🩺 市場健康度</a> &nbsp;|&nbsp;
  <a href="hot-assets.html">🔥 出来高急増</a> &nbsp;|&nbsp;
  本データは自動取得・表示であり、投資助言ではありません。</p>
  <p style="margin-top:8px"><a href="about.html">運営者情報</a> &nbsp;|&nbsp; <a href="privacy.html">プライバシーポリシー</a> &nbsp;|&nbsp; <a href="contact.html">お問い合わせ</a></p>
</footer>

<script>
const NK_DATES  = {json.dumps(nk_dates)};
const NK_PRICES = {json.dumps(nk_prices)};
const SP_DATES  = {json.dumps(sp_dates)};
const SP_PRICES = {json.dumps(sp_prices)};
const FX_DATES  = {json.dumps(fx_dates)};
const FX_PRICES = {json.dumps(fx_prices)};
const GLD_DATES  = {json.dumps(gld_dates)};
const GLD_PRICES = {json.dumps(gld_prices)};

const NK_ANN  = {nk_ann};
const SP_ANN  = {sp_ann};
const FX_ANN  = {fx_ann};
const GLD_ANN = {gld_ann};

const gridColor  = 'rgba(48,54,61,0.8)';
const labelColor = '#57606a';

function makeChart(id, datasets, annotations, yLabels) {{
  const canvas = document.getElementById(id);
  if (!canvas || datasets.every(ds => !ds.data || ds.data.length === 0)) return;
  const ctx = canvas.getContext('2d');
  const scales = {{}};
  datasets.forEach((ds, i) => {{
    const axId = 'y' + i;
    ds.yAxisID = axId;
    scales[axId] = {{
      position: i === 0 ? 'left' : 'right',
      grid: {{ color: i === 0 ? gridColor : 'transparent', drawBorder: false }},
      ticks: {{ color: labelColor, font: {{ size: 10 }}, maxTicksLimit: 6,
        callback: v => yLabels[i] ? yLabels[i](v) : v }},
      title: {{ display: false }},
    }};
  }});
  scales['x'] = {{
    ticks: {{ color: labelColor, font: {{ size: 10 }}, maxTicksLimit: 12,
      callback: function(val, idx) {{
        const lbl = this.getLabelForValue(val);
        return lbl && lbl.endsWith('-01') ? lbl.substring(0,4) : '';
      }}
    }},
    grid: {{ color: gridColor, drawBorder: false }},
  }};
  return new Chart(ctx, {{
    type: 'line',
    data: {{ labels: datasets[0].dates, datasets }},
    options: {{
      responsive: true, maintainAspectRatio: false,
      interaction: {{ mode: 'index', intersect: false }},
      plugins: {{
        legend: {{ labels: {{ color: '#1f2328', font: {{ size: 12 }} }} }},
        tooltip: {{ backgroundColor: 'rgba(22,27,34,0.95)', titleColor: '#0969da',
                    bodyColor: '#1f2328', borderColor: '#d0d7de', borderWidth: 1 }},
        annotation: {{ annotations }},
      }},
      scales,
      elements: {{ point: {{ radius: 0, hoverRadius: 4 }}, line: {{ tension: 0.2 }} }},
    }}
  }});
}}

makeChart('chartStocks', [
  {{ label: '日経平均（円）', dates: NK_DATES, data: NK_PRICES,
     borderColor: '#0969da', backgroundColor: 'rgba(88,166,255,0.08)',
     borderWidth: 1.5, fill: true }},
  {{ label: 'S&P500', dates: SP_DATES, data: SP_PRICES,
     borderColor: '#1a7f37', backgroundColor: 'rgba(63,185,80,0.06)',
     borderWidth: 1.5, fill: true }},
], Object.assign({{}}, NK_ANN, SP_ANN),
[v => v.toLocaleString()+'円', v => v.toLocaleString()]);

makeChart('chartFX', [
  {{ label: 'USD/JPY（円）', dates: FX_DATES, data: FX_PRICES,
     borderColor: '#bf3989', backgroundColor: 'rgba(240,136,62,0.08)',
     borderWidth: 1.5, fill: true }},
], FX_ANN, [v => v.toFixed(1)+'円']);

makeChart('chartGold', [
  {{ label: '金価格（USD/oz）', dates: GLD_DATES, data: GLD_PRICES,
     borderColor: '#9a6700', backgroundColor: 'rgba(255,215,0,0.08)',
     borderWidth: 1.5, fill: true }},
], GLD_ANN, [v => '$'+v.toLocaleString()]);
</script>
</body>
</html>"""


def _build_touraku_section(touraku):
    """騰落レシオの表示セクションHTMLを生成"""
    if touraku is None:
        return ""
    level, color, icon, comment = analyze_touraku(touraku)

    # ゲージ位置（30〜170の範囲を0〜100%にマッピング）
    pct = max(0, min(100, (touraku - 30) / 140 * 100))

    # ゲージの背景グラデーション
    gauge_bg = "linear-gradient(90deg, #238636 0%, #1a7f37 25%, #9a6700 50%, #bf3989 75%, #da3633 100%)"

    return f'''<div style="background:#f6f8fa;border:1px solid #d0d7de;border-radius:12px;padding:20px 24px;margin-bottom:32px">
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:14px;flex-wrap:wrap">
      <span style="font-size:1.1rem;font-weight:700;color:#1f2328">📊 騰落レシオ（25日）</span>
      <span style="font-size:1.5rem;font-weight:700;color:{color}">{touraku:.0f}%</span>
      <span style="background:{color};color:#fff;font-size:.75rem;font-weight:700;padding:3px 10px;border-radius:12px">{icon} {level}</span>
    </div>
    <div style="position:relative;height:18px;border-radius:9px;background:{gauge_bg};margin-bottom:10px;overflow:visible">
      <div style="position:absolute;left:{pct:.0f}%;top:-2px;width:4px;height:22px;background:#fff;border-radius:2px;transform:translateX(-50%);box-shadow:0 0 6px rgba(255,255,255,0.6)"></div>
      <div style="position:absolute;left:0;top:22px;font-size:.6rem;color:#57606a">30</div>
      <div style="position:absolute;left:36%;top:22px;font-size:.6rem;color:#57606a">80</div>
      <div style="position:absolute;left:64%;top:22px;font-size:.6rem;color:#57606a">120</div>
      <div style="position:absolute;right:0;top:22px;font-size:.6rem;color:#57606a">170</div>
    </div>
    <div style="font-size:.82rem;color:#57606a;line-height:1.65;margin-top:20px">{comment}</div>
    <div style="margin-top:10px;background:#ddf4ff;border:1px solid #54aeff;border-radius:8px;padding:10px 14px;font-size:.78rem;color:#1f6feb;line-height:1.7">
      <span style="font-weight:700;color:#0969da">🔰 初心者メモ　</span>騰落レシオは「値上がり銘柄数÷値下がり銘柄数×100」で計算されます。120%以上は「買われすぎ」、70%以下は「売られすぎ」の目安。逆張り投資の参考指標として人気があります。
    </div>
  </div>'''


def build_html(data, hist, now_jst, news=None, touraku=None):
    date_str = now_jst.strftime("%Y年%#m月%#d日") if os.name == "nt" else now_jst.strftime("%Y年%-m月%-d日")
    time_str = now_jst.strftime("%Y年%#m月%#d日 %H:%M JST") if os.name == "nt" else now_jst.strftime("%Y年%-m月%-d日 %H:%M JST")

    nk,  _, nk_chg  = data.get("nikkei", (None, None, None))
    sp,  _, sp_chg  = data.get("sp500",  (None, None, None))
    fx,  _, fx_chg  = data.get("usdjpy", (None, None, None))
    efx, _, efx_chg = data.get("eurjpy", (None, None, None))
    oil, _, oil_chg = data.get("oil",    (None, None, None))
    gld, _, gld_chg = data.get("gold",   (None, None, None))
    btc, _, btc_chg = data.get("btc",    (None, None, None))
    eth, _, eth_chg = data.get("eth",    (None, None, None))

    label, badge_color, emoji = sentiment([nk_chg, sp_chg, btc_chg, gld_chg])

    # ニュースHTML生成
    if news is None:
        news = {cat: [] for cat in ["top", "stocks", "fx", "commodity", "crypto"]}
    top_news_html     = build_news_html(news.get("top", []))
    stocks_news_html  = build_news_html(news.get("stocks", []))
    fx_news_html      = build_news_html(news.get("fx", []))
    cmd_news_html     = build_news_html(news.get("commodity", []))
    crypto_news_html  = build_news_html(news.get("crypto", []))

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  {seo_head("", f"マーケットニュース {date_str}", "日経平均・ダウ・S&P500・ドル円・原油・金・ビットコインの最新価格と日本語ニュースを毎日2回更新。AIが市場センチメントを判定し、日本人投資家にとっての注目ポイントを解説します。")}
  {GA4_TAG}
  <style>
    *{{margin:0;padding:0;box-sizing:border-box}}
    body{{font-family:'Segoe UI','Hiragino Sans','Yu Gothic',sans-serif;background:#ffffff;color:#1f2328;min-height:100vh}}
    header{{background:linear-gradient(135deg,#f6f8fa,#ffffff);border-bottom:1px solid #d0d7de;padding:24px 32px}}
    .header-inner{{max-width:1200px;margin:0 auto;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px}}
    .header-title{{font-size:1.6rem;font-weight:700;background:linear-gradient(90deg,#0969da,#1f6feb);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}
    .header-meta{{font-size:.85rem;color:#57606a}}
    .header-meta span{{color:#0969da;font-weight:600}}
    main{{max-width:1200px;margin:0 auto;padding:32px 24px}}
    .sentiment-banner{{background:linear-gradient(135deg,#1c2f1c,#162416);border:1px solid #2ea043;border-radius:12px;padding:20px 28px;margin-bottom:32px;display:flex;align-items:center;gap:16px;flex-wrap:wrap}}
    .sentiment-badge{{color:#fff;font-weight:700;font-size:1.3rem;padding:6px 16px;border-radius:20px;white-space:nowrap;background:{badge_color}}}
    .sentiment-text{{color:#1a7f37;font-size:.95rem;line-height:1.6}}
    .section-title{{font-size:1.1rem;font-weight:600;color:#57606a;text-transform:uppercase;letter-spacing:.08em;margin-bottom:16px}}
    .cards-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:20px;margin-bottom:40px}}
    .card{{background:#f6f8fa;border:1px solid #d0d7de;border-radius:12px;padding:20px;transition:border-color .2s}}
    .card:hover{{border-color:#0969da}}
    .card-header{{display:flex;align-items:center;gap:10px;margin-bottom:14px}}
    .card-icon{{width:36px;height:36px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:1.3rem}}
    .icon-stocks{{background:#1a3a5c}}.icon-fx{{background:#3a2a1a}}.icon-cmd{{background:#2a1a3a}}.icon-crypto{{background:#dafbe1}}
    .card-title{{font-weight:700;font-size:1rem;color:#1f2328}}
    .card-subtitle{{font-size:.75rem;color:#57606a}}
    .price-row{{display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid #d0d7de}}
    .price-row:last-of-type{{border-bottom:none}}
    .price-label{{font-size:.85rem;color:#57606a}}
    .price-value{{font-size:.95rem;font-weight:600;color:#1f2328}}
    .price-change{{font-size:1.3rem;margin-left:4px}}
    .up{{color:#1a7f37}}.down{{color:#cf222e}}
    .card-summary{{margin-top:14px;padding-top:14px;border-top:1px solid #d0d7de;font-size:.82rem;color:#57606a;line-height:1.65}}
    .beginner-box{{margin-top:12px;background:#ddf4ff;border:1px solid #54aeff;border-radius:8px;padding:10px 14px;font-size:.78rem;color:#1f6feb;line-height:1.7}}
    .beginner-box::before{{content:"🔰 初心者メモ　";font-weight:700;color:#0969da}}
    .chart-link-section{{text-align:center;margin-bottom:40px}}
    .chart-link-btn{{display:inline-flex;align-items:center;gap:10px;padding:16px 32px;background:linear-gradient(135deg,#ddf4ff,#f6f8fa);border:1px solid #0969da;border-radius:12px;color:#0969da;text-decoration:none;font-size:1rem;font-weight:600;transition:all .3s}}
    .chart-link-btn:hover{{background:#0969da;transform:translateY(-2px);box-shadow:0 4px 16px rgba(88,166,255,0.2)}}
    .chart-link-desc{{font-size:.8rem;color:#57606a;margin-top:8px}}
    /* トップニュース */
    .top-news{{background:linear-gradient(135deg,#1a1f2e,#f6f8fa);border:1px solid #0969da;border-radius:12px;padding:20px 24px;margin-bottom:32px}}
    .top-news-title{{font-size:1rem;font-weight:700;color:#0969da;margin-bottom:12px}}
    .news-item{{display:block;padding:10px 0;border-bottom:1px solid #d0d7de;text-decoration:none;transition:background .15s}}
    .news-item:last-child{{border-bottom:none}}
    .news-item:hover{{background:#ffffff;border-radius:6px;padding-left:8px}}
    .news-title{{display:block;font-size:.88rem;color:#1f2328;font-weight:600;line-height:1.5;margin-bottom:2px}}
    .news-meta{{display:block;font-size:.72rem;color:#57606a}}
    .news-sent{{margin-right:6px;font-size:1.3rem;vertical-align:middle}}
    .news-empty{{font-size:.82rem;color:#6e7781;padding:8px 0}}
    .card-news{{margin-top:14px;padding-top:14px;border-top:1px solid #d0d7de}}
    .card-news-title{{font-size:.78rem;color:#0969da;font-weight:600;margin-bottom:8px}}
    .card-news .news-item{{padding:6px 0}}
    .card-news .news-title{{font-size:.8rem}}
    .card-news .news-meta{{font-size:.68rem}}
    footer{{background:#f6f8fa;border-top:1px solid #d0d7de;padding:20px 32px;text-align:center;font-size:.78rem;color:#6e7781}}
    footer a{{color:#0969da;text-decoration:none}}
    .nav-bar{{display:flex;flex-wrap:wrap;gap:10px;justify-content:center;margin-bottom:28px}}
    .nav-btn{{display:inline-flex;align-items:center;gap:8px;padding:11px 20px;background:#f6f8fa;border:1px solid #d0d7de;border-radius:10px;color:#57606a;text-decoration:none;font-size:.95rem;font-weight:600;transition:all .2s}}
    .nav-btn:hover{{border-color:#0969da;color:#0969da}}
    .nav-btn.current{{background:#0969da;border-color:#0969da;color:#fff}}
    @media(max-width:600px){{.header-inner{{flex-direction:column}}.sentiment-banner{{flex-direction:column}}}}
  </style>
  <!-- A8.net広告タグはここに貼る予定 -->
</head>
<body>
<header>
  <div class="header-inner">
    <div>
      <div class="header-title">📊 マーケットニュース</div>
      <div class="header-meta">最終更新: <span>{time_str}</span></div>
    </div>
    <div class="header-meta">GitHub Actions 自動更新</div>
  </div>
</header>
<main>

  <!-- ナビゲーション -->
  <nav class="nav-bar">
    <a class="nav-btn current" href="index.html">📊 マーケットニュース</a>
    <a class="nav-btn" href="calendar.html">📅 経済カレンダー</a>
    <a class="nav-btn" href="charts.html">📈 50年チャート</a>
    <a class="nav-btn" href="vix.html">😱 恐怖指数</a>
    <a class="nav-btn" href="market-health.html">🩺 市場健康度</a>
    <a class="nav-btn" href="hot-assets.html">🔥 出来高急増</a>
  </nav>

  <!-- センチメント -->
  <div class="sentiment-banner">
    <div class="sentiment-badge">{emoji} {label}</div>
    <div class="sentiment-text">
      日経平均 {fmt_price(nk, 0, suffix='円')} / S&amp;P500 {fmt_price(sp, 2)} /
      USD/JPY {fmt_price(fx, 2, suffix='円')} / BTC {fmt_price(btc, 0, prefix='$')} /
      金 {fmt_price(gld, 2, prefix='$', suffix='/oz')}
    </div>
  </div>

  <!-- 更新履歴 -->
  <div style="background:#f6f8fa;border:1px solid #d0d7de;border-left:4px solid #0969da;border-radius:8px;padding:14px 22px;margin-bottom:32px;font-size:.88rem;line-height:1.9">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;flex-wrap:wrap;gap:10px">
      <span style="color:#0969da;font-weight:700">📰 更新履歴</span>
      <a href="guides.html" style="color:#1f6feb;font-size:.8rem;font-weight:600;text-decoration:none">📚 記事一覧 →</a>
    </div>
    <div style="color:#424a53">
      ・<b>2026-04-30</b>: 🚨 緊急速報「<a href="guide-jpy-intervention-2026-04.html" style="color:#cf222e"><b>ドル円急落：片山財務相「断固たる措置」発言で為替介入警戒最高潮</b></a>」公開<br>
      ・<b>2026-04-30</b>: 🔥 速報記事「<a href="guide-fomc-2026-04.html" style="color:#cf222e"><b>FOMC4月会合速報：据え置き＋反対4票・パウエル退任とマーケット影響</b></a>」公開<br>
      ・<b>2026-04-29</b>: 🔥 速報記事「<a href="guide-boj-2026-04.html" style="color:#cf222e"><b>日銀4月会合速報：金利据え置き＋上田総裁会見・利上げシナリオ</b></a>」公開
    </div>
  </div>

  <!-- 騰落レシオ -->
  {_build_touraku_section(touraku)}

  <!-- A8広告枠①（トップページ・ニュース上）-->
  <div style="margin:24px 0;padding:18px;background:#ffffff;border:1px solid #54aeff;border-radius:10px;text-align:center;min-height:120px;display:flex;flex-direction:column;align-items:center;justify-content:center">
    <div style="font-size:.7rem;color:#6e7781;letter-spacing:.12em;margin-bottom:10px">広告 / PR</div>
    <!-- A8.net 広告コードをここに貼り付け（推奨：728×90 バナー / 300×250 レクタングル）-->
    <div style="font-size:.82rem;color:#57606a;line-height:1.6">＊ A8.net広告コード貼付け予定（証券口座・FX口座など）</div>
  </div>

  <!-- トップニュース -->
  <div class="top-news">
    <div class="top-news-title">🔥 マーケットを動かすニュース TOP3</div>
    {top_news_html}
  </div>

  <!-- 今日のカード -->
  <p class="section-title">本日のマーケット</p>
  <div class="cards-grid">
    <div class="card">
      <div class="card-header">
        <div class="card-icon icon-stocks">🗾</div>
        <div><div class="card-title">株式市場</div><div class="card-subtitle">日本株・米国株</div></div>
      </div>
      <div class="price-row"><span class="price-label">日経平均</span><span class="price-value">{fmt_price(nk, 0, suffix='円')} {fmt_change(nk_chg)}</span></div>
      <div class="price-row"><span class="price-label">S&amp;P500</span><span class="price-value">{fmt_price(sp, 2)} {fmt_change(sp_chg)}</span></div>
      <div class="beginner-box">日経平均は日本を代表する225社の株価の平均です。上がると「日本経済が好調」のサイン。S&P500はアメリカの代表的な500社の指数で、世界経済の体温計ともいわれます。</div>
      <div class="card-news"><div class="card-news-title">📰 関連ニュース</div>{stocks_news_html}</div>
    </div>
    <div class="card">
      <div class="card-header">
        <div class="card-icon icon-fx">💱</div>
        <div><div class="card-title">為替（FX）</div><div class="card-subtitle">ドル円・ユーロ円</div></div>
      </div>
      <div class="price-row"><span class="price-label">USD/JPY</span><span class="price-value">{fmt_price(fx, 2, suffix='円')} {fmt_change(fx_chg)}</span></div>
      <div class="price-row"><span class="price-label">EUR/JPY</span><span class="price-value">{fmt_price(efx, 2, suffix='円')} {fmt_change(efx_chg)}</span></div>
      <div class="beginner-box">1ドルを買うのに何円必要かを示します。数字が大きいほど「円安（ドル高）」。円安は輸出企業に有利ですが、輸入品や旅行が割高になります。</div>
      <div class="card-news"><div class="card-news-title">📰 関連ニュース</div>{fx_news_html}</div>
    </div>
    <div class="card">
      <div class="card-header">
        <div class="card-icon icon-cmd">🛢️</div>
        <div><div class="card-title">コモディティ</div><div class="card-subtitle">原油・金</div></div>
      </div>
      <div class="price-row"><span class="price-label">WTI原油</span><span class="price-value">{fmt_price(oil, 2, prefix='$', suffix='/bbl')} {fmt_change(oil_chg)}</span></div>
      <div class="price-row"><span class="price-label">金（スポット）</span><span class="price-value">{fmt_price(gld, 2, prefix='$', suffix='/oz')} {fmt_change(gld_chg)}</span></div>
      <div class="beginner-box">原油価格が上がるとガソリンや電気代に影響します。金は「有事の金」と呼ばれ、世界が不安定なときに買われる安全資産です。金が上がるときは要注意サインのことも。</div>
      <div class="card-news"><div class="card-news-title">📰 関連ニュース</div>{cmd_news_html}</div>
    </div>
    <div class="card">
      <div class="card-header">
        <div class="card-icon icon-crypto">₿</div>
        <div><div class="card-title">暗号資産</div><div class="card-subtitle">BTC・ETH</div></div>
      </div>
      <div class="price-row"><span class="price-label">Bitcoin (BTC)</span><span class="price-value">{fmt_price(btc, 0, prefix='$')} {fmt_change(btc_chg)}</span></div>
      <div class="price-row"><span class="price-label">Ethereum (ETH)</span><span class="price-value">{fmt_price(eth, 2, prefix='$')} {fmt_change(eth_chg)}</span></div>
      <div class="beginner-box">ビットコインは世界最大の暗号資産で「デジタルゴールド」とも呼ばれます。イーサリアムはスマートコントラクト技術の基盤で、NFTやDeFiに使われます。値動きが大きいので注意が必要です。</div>
      <div class="card-news"><div class="card-news-title">📰 関連ニュース</div>{crypto_news_html}</div>
    </div>
  </div>

  <!-- サブページへのリンク -->
  <div class="chart-link-section">
    <a href="market-health.html" class="chart-link-btn" style="border-color:#9a6700;color:#9a6700;margin-bottom:12px">🩺 市場健康度ダッシュボードを見る →</a>
    <div class="chart-link-desc">VIX・恐怖&amp;強欲指数・バフェット指数・CAPE・RSIを一枚で総合診断</div>
    <div style="margin-top:16px">
      <a href="calendar.html" class="chart-link-btn" style="border-color:#7cf2c8;color:#7cf2c8">📅 マクロ経済カレンダーを見る →</a>
      <div class="chart-link-desc">日米欧中の重要経済指標（FOMC・BOJ・CPI・雇用統計など）を月間カレンダーで一覧</div>
    </div>
    <div style="margin-top:16px">
      <a href="vix.html" class="chart-link-btn" style="border-color:#cf222e;color:#cf222e">😱 恐怖指数（VIX）分析を見る →</a>
      <div class="chart-link-desc">VIXの現在値・90日チャート・AIコメントで市場の恐怖度をチェック</div>
    </div>
    <div style="margin-top:16px">
      <a href="charts.html" class="chart-link-btn">📈 50年価格チャート＆歴史的イベント一覧を見る →</a>
      <div class="chart-link-desc">日経平均・S&amp;P500・ドル円・金の50年チャートに歴史的イベントを重ねて表示</div>
    </div>
  </div>

  <!-- A8広告枠②（トップページ・フッター上）-->
  <div style="margin:32px 0;padding:18px;background:#ffffff;border:1px solid #54aeff;border-radius:10px;text-align:center;min-height:120px;display:flex;flex-direction:column;align-items:center;justify-content:center">
    <div style="font-size:.7rem;color:#6e7781;letter-spacing:.12em;margin-bottom:10px">広告 / PR</div>
    <!-- A8.net 広告コードをここに貼り付け（推奨：728×90 バナー）-->
    <div style="font-size:.82rem;color:#57606a;line-height:1.6">＊ A8.net広告コード貼付け予定（証券口座・FX口座など）</div>
  </div>

</main>
<footer>
  <p>データソース: Yahoo Finance (yfinance) &nbsp;|&nbsp;
  <a href="https://marketwatch-jp.com/">marketwatch-jp.com</a> &nbsp;|&nbsp;
  本データは自動取得・表示であり、投資助言ではありません。</p>
  <p style="margin-top:8px">
  <a href="about.html">運営者情報</a> &nbsp;|&nbsp;
  <a href="privacy.html">プライバシーポリシー</a> &nbsp;|&nbsp;
  <a href="contact.html">お問い合わせ</a></p>
</footer>
</body>
</html>"""


# ─────────────────────────────────────────
# メイン
# ─────────────────────────────────────────
# ─────────────────────────────────────────
# GitHub Pages アップロード関数
# ─────────────────────────────────────────
def upload_to_github(html_path: str, config_path: str = None) -> bool:
    """
    GitHub Contents API を使って index.html をアップロードする。
    config_path が None の場合、スクリプトと同じフォルダの
    market-news-config.json.json を自動検索する。
    戻り値: 成功 True / 失敗 False
    """
    # GitHub Actions 環境では git commit/push が workflow 側で行われるため、
    # API 経由のアップロードをスキップする（二重 push 回避）
    if os.environ.get("GITHUB_ACTIONS_RUN") == "true" or os.environ.get("GITHUB_ACTIONS") == "true":
        print(f"⏭️  GitHub Actions 環境のため、{os.path.basename(html_path)} の API アップロードはスキップ（workflow の git push に委譲）")
        return True

    import base64

    # 設定ファイルを探す
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        config_path,
        os.path.join(script_dir, "market-news-config.json.json"),
        os.path.join(script_dir, "market-news-config.json"),
    ]
    cfg_path = next((p for p in candidates if p and os.path.exists(p)), None)
    if not cfg_path:
        print("⚠️  設定ファイルが見つかりません。GitHub アップロードをスキップします。")
        return False

    with open(cfg_path, encoding="utf-8") as f:
        cfg = json.load(f)

    token  = cfg.get("github_token", "")
    owner  = cfg.get("github_owner", "")
    repo   = cfg.get("github_repo", "")
    branch = cfg.get("github_branch", "main")
    fpath  = cfg.get("file_path", "index.html")

    if not all([token, owner, repo]):
        print("⚠️  設定ファイルに必須項目が不足しています。GitHub アップロードをスキップします。")
        return False

    # html_path のファイル名でアップロード先を決定
    upload_filename = os.path.basename(html_path)
    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{upload_filename}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    # 既存ファイルの SHA 取得
    sha = None
    try:
        req = urllib.request.Request(f"{api_url}?ref={branch}", headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            sha = json.load(resp).get("sha")
        print(f"📋 既存SHA取得: {sha[:12]}...")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print("ℹ️  新規ファイルとして作成します")
        else:
            print(f"❌ SHA取得エラー ({e.code}): {e.read().decode()[:200]}")
            return False
    except Exception as e:
        print(f"❌ 接続エラー: {e}")
        return False

    # HTML を Base64 エンコード
    with open(html_path, "rb") as f:
        html_b64 = base64.b64encode(f.read()).decode("ascii")

    now_str = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    payload = {"message": f"chore: update market news [{now_str}]",
               "content": html_b64, "branch": branch}
    if sha:
        payload["sha"] = sha

    # PUT リクエスト
    try:
        body = json.dumps(payload).encode("utf-8")
        req  = urllib.request.Request(api_url, data=body, headers=headers, method="PUT")
        with urllib.request.urlopen(req, timeout=30) as resp:
            result   = json.load(resp)
            commit   = result.get("commit", {}).get("html_url", "")
            pages_url = f"https://{owner}.github.io/{repo}/"
        print(f"✅ GitHub Pages 更新成功！")
        print(f"🌐 URL: {pages_url}")
        if commit:
            print(f"📝 コミット: {commit}")
        return True
    except urllib.error.HTTPError as e:
        print(f"❌ アップロード失敗 ({e.code}): {e.read().decode()[:300]}")
        return False
    except Exception as e:
        print(f"❌ アップロードエラー: {e}")
        return False


def main():
    now_jst = datetime.now(JST)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    index_path    = os.path.join(script_dir, "index.html")
    charts_path   = os.path.join(script_dir, "charts.html")
    vix_path      = os.path.join(script_dir, "vix.html")
    calendar_path = os.path.join(script_dir, "calendar.html")
    health_path   = os.path.join(script_dir, "market-health.html")
    hot_path      = os.path.join(script_dir, "hot-assets.html")
    preview_path  = os.path.join(script_dir, "preview.html")

    # ── 価格データ取得（個別にtry-exceptで保護）──
    print("📡 現在価格を取得中...")
    tickers = {
        "nikkei": "^N225", "sp500": "^GSPC", "usdjpy": "JPY=X",
        "eurjpy": "EURJPY=X", "oil": "CL=F", "gold": "GC=F",
        "btc": "BTC-USD", "eth": "ETH-USD",
    }
    data = {}
    for key, sym in tickers.items():
        try:
            data[key] = get_price(sym)
            status = "OK" if data[key][0] is not None else "N/A"
        except Exception as e:
            data[key] = (None, None, None)
            status = f"ERROR: {e}"
        print(f"  {key}: {status}")

    # ── 歴史的価格データ取得 ──
    print("📊 歴史的価格データを取得中（50年分）...")
    hist_tickers = {
        "nikkei": "^N225", "sp500": "^GSPC",
        "usdjpy": "JPY=X", "gold": "GC=F",
    }
    hist = {}
    for key, sym in hist_tickers.items():
        try:
            hist[key] = get_historical_monthly(sym, "1975-01-01")
            count = len(hist[key][0])
        except Exception as e:
            hist[key] = ([], [])
            count = 0
        print(f"  {key}: {count}件")

    # ── 騰落レシオ取得 ──
    print("📊 騰落レシオ取得中...")
    try:
        touraku_ratio = get_touraku_ratio()
    except Exception as e:
        touraku_ratio = None
        print(f"  騰落レシオ: ERROR: {e}")

    # ── ニュース取得 ──
    print("📰 ニュース取得中...")
    news_api_key = os.environ.get("NEWSAPI_KEY", "")
    cfg_path = os.path.join(script_dir, "market-news-config.json.json")
    if not news_api_key and os.path.exists(cfg_path):
        try:
            with open(cfg_path, encoding="utf-8") as f:
                cfg = json.load(f)
            news_api_key = cfg.get("newsapi_key", "")
        except Exception as e:
            print(f"⚠️ 設定ファイル読込エラー: {e}")
    news = fetch_news(news_api_key)
    for cat, arts in news.items():
        print(f"  {cat}: {len(arts)}件")

    # ── index.html 生成（メインページ）──
    print("🖊️  index.html 生成中...")
    try:
        index_content = build_html(data, hist, now_jst, news, touraku=touraku_ratio)
        if safe_write(index_path, index_content):
            print(f"✅ index.html 生成完了 ({now_jst.strftime('%Y-%m-%d %H:%M JST')})")
        else:
            print("❌ index.html の書き込みに失敗しました")
    except Exception as e:
        print(f"❌ index.html 生成エラー: {e}")
        import traceback; traceback.print_exc()

    # ── charts.html 生成（チャート＆イベントページ）──
    print("🖊️  charts.html 生成中...")
    try:
        charts_content = build_charts_html(hist, now_jst)
        if safe_write(charts_path, charts_content):
            print(f"✅ charts.html 生成完了")
        else:
            print("❌ charts.html の書き込みに失敗しました")
    except Exception as e:
        print(f"❌ charts.html 生成エラー: {e}")
        import traceback; traceback.print_exc()

    # ── vix.html 生成（恐怖指数ページ）──
    print("😱 VIXデータ取得中...")
    try:
        vix_val, vix_prev, _ = get_price("^VIX")
        vix_dates, vix_prices = get_vix_history(90)
        print(f"  VIX: {vix_val:.1f}" if vix_val else "  VIX: N/A")
    except Exception as e:
        vix_val, vix_prev = None, None
        vix_dates, vix_prices = [], []
        print(f"  VIX: ERROR: {e}")

    print("🖊️  vix.html 生成中...")
    try:
        vix_content = build_vix_html(vix_val, vix_prev, vix_dates, vix_prices, now_jst)
        if safe_write(vix_path, vix_content):
            print(f"✅ vix.html 生成完了")
        else:
            print("❌ vix.html の書き込みに失敗しました")
    except Exception as e:
        print(f"❌ vix.html 生成エラー: {e}")
        import traceback; traceback.print_exc()

    # ── calendar.html 生成（マクロ経済カレンダー）──
    print("📅 calendar.html 生成中...")
    try:
        calendar_content = build_calendar_html(now_jst)
        if safe_write(calendar_path, calendar_content):
            print(f"✅ calendar.html 生成完了")
        else:
            print("❌ calendar.html の書き込みに失敗しました")
    except Exception as e:
        print(f"❌ calendar.html 生成エラー: {e}")
        import traceback; traceback.print_exc()

    # ── market-health.html 生成（市場健康度ダッシュボード）──
    print("🩺 market-health.html 生成中...")
    try:
        health_content = build_market_health_html(data, vix_val, touraku_ratio, now_jst)
        if safe_write(health_path, health_content):
            print(f"✅ market-health.html 生成完了")
        else:
            print("❌ market-health.html の書き込みに失敗しました")
    except Exception as e:
        print(f"❌ market-health.html 生成エラー: {e}")
        import traceback; traceback.print_exc()

    # ── hot-assets.html 生成（出来高急増ランキング）──
    print("🔥 hot-assets.html 生成中...")
    try:
        print("  出来高データ取得中...")
        hot_data = fetch_hot_assets_all()
        hot_content = build_hot_assets_html(hot_data, now_jst)
        if safe_write(hot_path, hot_content):
            print(f"✅ hot-assets.html 生成完了")
        else:
            print("❌ hot-assets.html の書き込みに失敗しました")
    except Exception as e:
        print(f"❌ hot-assets.html 生成エラー: {e}")
        import traceback; traceback.print_exc()

    # ── preview.html 生成（経済指標プレビュー）──
    print("📰 preview.html 生成中...")
    try:
        preview_content = build_preview_html(now_jst)
        if safe_write(preview_path, preview_content):
            print(f"✅ preview.html 生成完了")
        else:
            print("❌ preview.html の書き込みに失敗しました")
    except Exception as e:
        print(f"❌ preview.html 生成エラー: {e}")
        import traceback; traceback.print_exc()

    # ── sitemap.xml / robots.txt 生成 ──
    sitemap_path = os.path.join(script_dir, "sitemap.xml")
    robots_path  = os.path.join(script_dir, "robots.txt")
    print("🗺️  sitemap.xml / robots.txt 生成中...")
    try:
        with open(sitemap_path, "w", encoding="utf-8") as f:
            f.write(build_sitemap_xml(now_jst))
        with open(robots_path, "w", encoding="utf-8") as f:
            f.write(build_robots_txt())
        print(f"✅ sitemap.xml / robots.txt 生成完了")
    except Exception as e:
        print(f"❌ sitemap/robots 生成エラー: {e}")

    # ── GitHub Pages へアップロード ──
    print("\n📤 GitHub Pages にアップロード中...")
    upload_to_github(index_path)
    print("📤 charts.html をアップロード中...")
    upload_to_github(charts_path)
    print("📤 vix.html をアップロード中...")
    upload_to_github(vix_path)
    print("📤 calendar.html をアップロード中...")
    upload_to_github(calendar_path)
    print("📤 market-health.html をアップロード中...")
    upload_to_github(health_path)
    print("📤 hot-assets.html をアップロード中...")
    upload_to_github(hot_path)
    print("📤 preview.html をアップロード中...")
    upload_to_github(preview_path)
    print("📤 sitemap.xml をアップロード中...")
    upload_to_github(sitemap_path)
    print("📤 robots.txt をアップロード中...")
    upload_to_github(robots_path)

    if not os.environ.get("GITHUB_ACTIONS_RUN"):
        try:
            print("📤 generate_market_news.py 自身もアップロード中...")
            upload_to_github(os.path.abspath(__file__))
        except Exception as e:
            print(f"⚠️  スクリプト自身のアップロード失敗: {e}")

    print("\n✨ すべての処理が完了しました！")


if __name__ == "__main__":
    main()
