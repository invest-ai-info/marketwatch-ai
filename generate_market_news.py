"""
毎朝マーケットニュース自動生成スクリプト（歴史的イベント年表付き）
yfinance で価格データ取得、Chart.js でチャート表示
"""

import yfinance as yf
import json
import re
import os
import html
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
# 無料メルマガ登録フォーム（MailerLite account 2419467 / form 189793597614196622）
#   safe_write() が全 .html の <footer> 直前に一括注入する。
#   MailerLite の送信機能（webforms.min.js + フォーム構造）は維持し、
#   見た目だけサイトのライト/ダーク両テーマに合わせて作り直した版。
#   ※ これはプレーン文字列（f-string ではない）。波括弧は CSS/JS の literal。
# ─────────────────────────────────────────
NEWSLETTER_FORM = '''
<!-- ===== MarketWatch 無料メルマガ登録 (MailerLite 2419467/189793597614196622) ===== -->
<div class="mw-newsletter">
<div id="mlb2-42383897" class="ml-form-embedContainer ml-subscribe-form ml-subscribe-form-42383897">
  <div class="ml-form-align-center">
    <div class="ml-form-embedWrapper embedForm">
      <div class="ml-form-embedBody ml-form-embedBodyDefault row-form">
        <div class="ml-form-embedContent">
          <span class="mw-nl-badge">🎁 無料PDFプレゼント</span>
          <h4>登録特典『投資をはじめる前の基礎チェックリスト』(PDF)を無料プレゼント</h4>
          <p>初心者が確認したい12項目のチェックリスト(PDF)を無料ダウンロード。さらに毎週の相場振り返りと注目ポイントをメールでお届けします。登録無料・1クリックで解除OK・投資助言ではありません。</p>
        </div>
        <form class="ml-block-form" action="https://assets.mailerlite.com/jsonp/2419467/forms/189793597614196622/subscribe" data-code="" method="post" target="_blank">
          <div class="ml-form-formContent">
            <div class="ml-form-fieldRow ml-last-item">
              <div class="ml-field-group ml-field-email ml-validate-email ml-validate-required">
                <input aria-label="email" aria-required="true" type="email" class="form-control" name="fields[email]" placeholder="メールアドレスを入力" autocomplete="email">
              </div>
            </div>
          </div>
          <input type="hidden" name="ml-submit" value="1">
          <div class="ml-form-embedSubmit">
            <button type="submit" class="primary">登録する</button>
            <button disabled="disabled" style="display:none" type="button" class="loading"><div class="ml-form-embedSubmitLoad"></div><span class="sr-only">送信中...</span></button>
          </div>
          <input type="hidden" name="anticsrf" value="true">
        </form>
      </div>
      <div class="ml-form-successBody row-success" style="display:none">
        <div class="ml-form-successContent">
          <h4>✅ 登録ありがとうございます！</h4>
          <p>下のボタンから特典PDFをダウンロードできます。次回のメルマガ配信もお楽しみに。</p>
          <a href="/investing-checklist.pdf" target="_blank" rel="noopener" style="display:inline-block;margin-top:10px;padding:11px 22px;background:#0969da;color:#fff;border-radius:8px;text-decoration:none;font-weight:700">📥 チェックリスト(PDF)をダウンロード</a>
        </div>
      </div>
    </div>
  </div>
</div>
</div>
<style>
.mw-newsletter{max-width:680px;margin:40px auto;padding:0 16px}
.mw-newsletter *{box-sizing:border-box}
.mw-newsletter .ml-form-embedContainer{width:100%;margin:0}
.mw-newsletter .ml-form-align-center{text-align:left}
.mw-newsletter .ml-form-embedWrapper{display:block;width:100%;max-width:100%;background:#f6f8fa;border:1px solid #d0d7de;border-radius:14px}
.mw-newsletter .ml-form-embedBody{padding:26px 24px}
.mw-newsletter .ml-form-embedContent{margin:0 0 18px}
.mw-newsletter .mw-nl-badge{display:inline-block;font-size:.78rem;font-weight:700;color:#0969da;background:rgba(9,105,218,.1);border:1px solid rgba(9,105,218,.3);padding:3px 12px;border-radius:999px;margin-bottom:12px}
.mw-newsletter .ml-form-embedContent h4{color:#24292f;font-size:1.18rem;font-weight:700;line-height:1.5;margin:0 0 8px}
.mw-newsletter .ml-form-embedContent p{color:#57606a;font-size:.86rem;line-height:1.7;margin:0}
.mw-newsletter .ml-form-formContent{margin:0}
.mw-newsletter .ml-form-fieldRow{margin:0 0 10px}
.mw-newsletter .ml-form-fieldRow input{width:100%;background:#fff;color:#24292f;border:1px solid #d0d7de;border-radius:8px;padding:12px 14px;font-size:.95rem}
.mw-newsletter .ml-form-fieldRow input:focus{border-color:#0969da;box-shadow:0 0 0 3px rgba(9,105,218,.2);outline:none}
.mw-newsletter .ml-form-fieldRow input::placeholder{color:#8b949e}
.mw-newsletter .ml-form-embedSubmit{margin:0}
.mw-newsletter .ml-form-embedSubmit button{width:100%;background:#1f6feb;color:#fff;border:none;border-radius:8px;padding:12px;font-size:.95rem;font-weight:700;cursor:pointer;transition:background .15s}
.mw-newsletter .ml-form-embedSubmit button.primary:hover{background:#388bfd}
.mw-newsletter .ml-form-successContent h4{color:#1a7f37;font-size:1.1rem;font-weight:700;margin:0 0 8px;text-align:center}
.mw-newsletter .ml-form-successContent p{color:#57606a;font-size:.86rem;line-height:1.7;text-align:center;margin:0}
.mw-newsletter .ml-error input{border-color:#cf222e !important}
.mw-newsletter .ml-form-embedSubmitLoad{display:inline-block;width:20px;height:20px}
.mw-newsletter .ml-form-embedSubmitLoad:after{content:" ";display:block;width:11px;height:11px;margin:0 auto;border-radius:50%;border:3px solid #fff;border-color:#fff #fff #fff transparent;animation:mw-nl-spin 1.2s linear infinite}
@keyframes mw-nl-spin{0%{transform:rotate(0)}100%{transform:rotate(360deg)}}
.mw-newsletter .sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);border:0}
body.dark .mw-newsletter .ml-form-embedWrapper{background:linear-gradient(180deg,#161b22,#0d1117);border-color:#30363d}
body.dark .mw-newsletter .mw-nl-badge{color:#79c0ff;background:rgba(56,139,253,.12);border-color:rgba(56,139,253,.35)}
body.dark .mw-newsletter .ml-form-embedContent h4{color:#e6edf3}
body.dark .mw-newsletter .ml-form-embedContent p{color:#8b949e}
body.dark .mw-newsletter .ml-form-fieldRow input{background:#0d1117;color:#e6edf3;border-color:#30363d}
body.dark .mw-newsletter .ml-form-fieldRow input::placeholder{color:#6e7681}
body.dark .mw-newsletter .ml-form-successContent h4{color:#3fb950}
body.dark .mw-newsletter .ml-form-successContent p{color:#8b949e}
</style>
<script>
function ml_webform_success_42383897(){var $=ml_jQuery||jQuery;$('.ml-subscribe-form-42383897 .row-success').show();$('.ml-subscribe-form-42383897 .row-form').hide();}
</script>
<script src="https://groot.mailerlite.com/js/w/webforms.min.js?v83147fa8ce2d95cb73ece7f28b469519" type="text/javascript"></script>
<script>fetch("https://assets.mailerlite.com/jsonp/2419467/forms/189793597614196622/takel")</script>
<!-- ===== /無料メルマガ登録 ===== -->
'''

# ─────────────────────────────────────────
# SEO 共通定数 / ヘルパー
#   - 各ページの <head> に title/description/canonical/OGP/Twitter/JSON-LD を出力
#   - GitHub Pages の URL 構造に合わせる
# ─────────────────────────────────────────
SITE_NAME = "MarketWatch AI"
SITE_TAGLINE = "日本人投資家のためのマーケット情報サイト"
BASE_URL = "https://marketwatch-jp.com/"
OG_IMAGE = BASE_URL + "og-image.png"  # 後で画像設置可。当面は無くても致命傷ではない

# 🆕 2026-06-19: 薄い自動テンプレ/日付つきページの noindex 判定（AdSense「低価値コンテンツ」対策・単一ソース）。
#   週次戦略/週次振り返り(guide-weekly-)/月次レポート(guide-monthly-report-)/指標プレビュー(preview,guide-auto-)/
#   期限切れの日付フラッシュ を非索引にし sitemap からも除外。Google には良質な“常設”記事だけを評価させる。
NOINDEX_SLUGS = {
    "preview.html",
    "guide-jpy-intervention-2026-04.html", "guide-fomc-2026-04.html", "guide-boj-2026-04.html",
    "guide-gw-gap-2026-05.html", "guide-jpy-intervention-2026-05-06.html",
    "guide-us-cpi-2026-05.html", "guide-us-jobs-2026-05.html",
    # 🆕 2026-06-24 second-tier（AdSense再申請前）: 消えても良い日付つきイベント速報フラッシュを noindex+sitemap除外。
    #   深掘り個別銘柄(NVIDIA/TSMC等)・bank-stocks・jpy-intervention-2026-06 は価値があるので index 維持。
    "guide-btc-crash-2026-05-19.html", "guide-btc-crash-2026-06.html",
    "guide-nikkei-60k-break-2026-05-20.html", "guide-nikkei-65k-break-2026-05-25.html",
    "guide-us-china-summit-2026-05.html",
    "guide-us-china-summit-result-2026-05-14.html", "guide-us-china-summit-result-2026-05-15.html",
}
def is_noindex_slug(slug: str) -> bool:
    s = slug or ""
    return (s in NOINDEX_SLUGS or s.startswith("guide-weekly-")
            or s.startswith("guide-monthly-report-") or s.startswith("guide-auto-"))


# 🆕 2026-06-24: 全コア/データページ共通の2段ヘッダー（①ブランドバー ②ページ名＋最終更新）。
#   狙い＝トップのタイトルを全ページで統一（旧来は各ページが我流の大見出しでブランド名が無かった）。
#   ブランド名の色は固定の青グラデで統一。背景・ダーク対応は base の header{} と各ページの dark スクリプトに委譲
#   （インラインで色を固定しない＝ダークモードを壊さない）。.header-inner の flex は使わず自前 block で2段組み。
def brand_header(page_emoji, page_title, updated="", extra=""):
    meta = ""
    if updated:
        meta += f'<div class="header-meta" style="margin-top:2px">最終更新: {updated}</div>'
    if extra:
        meta += f'<div class="header-meta" style="margin-top:1px;font-size:.78rem">{extra}</div>'
    return (
        '<header><div style="max-width:1200px;margin:0 auto;text-align:left">'
        '<div style="font-size:1.6rem;font-weight:700;line-height:1.3;'
        'background:linear-gradient(90deg,#0969da,#1f6feb);-webkit-background-clip:text;'
        '-webkit-text-fill-color:transparent;background-clip:text">📊 MarketWatch AI</div>'
        '<div class="header-meta" style="font-size:.85rem;margin-top:4px">日本人投資家のためのマーケット情報サイト</div>'
        '<div style="margin-top:11px;padding-top:11px;border-top:1px solid rgba(128,128,128,.22)">'
        f'<div style="font-size:1.3rem;font-weight:700;color:#0969da;line-height:1.35">{page_emoji} {page_title}</div>'
        f'{meta}'
        '</div></div></header>'
    )


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
  <meta name="robots" content="{'noindex,follow' if is_noindex_slug(slug) else 'index,follow'}">
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
        ("guide-investment-tax.html",   "0.85","monthly"),
        ("guide-nisa.html",             "0.85","monthly"),
        ("guide-nisa-ranking.html",     "0.85","weekly"),
        ("guide-weekly-2026-05-04.html","0.95","daily"),
        ("guide-jpy-intervention-2026-04.html","0.95","daily"),
        ("guide-fomc-2026-04.html",     "0.9", "weekly"),
        ("guide-boj-2026-04.html",      "0.9", "weekly"),
        ("guide-nikkei-60000.html",     "0.9", "weekly"),
        ("guides.html",                 "0.8", "weekly"),
    ]
    # 🆕 ハードコード漏れ防止：リポジト内の全 guide-*.html を自動追加（重複は除外）。
    # これで sitemap は常に「完全」になり、手作業での追加が不要（＝sitemapの二重管理を解消）。
    # 🆕 2026-06-19: noindex 対象（週次/月次/preview/guide-auto-/日付フラッシュ）は sitemap からも除外。
    #   判定は is_noindex_slug() に単一ソース化（seo_head の noindex メタと同じ規則）。
    _listed = {slug for slug, _, _ in pages}
    _sd = os.path.dirname(os.path.abspath(__file__))
    try:
        for _name in sorted(os.listdir(_sd)):
            if is_noindex_slug(_name):  # noindex ページは sitemap に載せない（「index して/するな」の矛盾回避）
                continue
            if _name.startswith("guide-") and _name.endswith(".html") and _name not in _listed:
                pages.append((_name, "0.8", "monthly"))
                _listed.add(_name)
    except Exception as _e:
        print(f"  ⚠️ sitemap: guide自動収集スキップ: {_e}")
    # ハードコード一覧の中の noindex 対象も最終除外（preview/週次/旧フラッシュ）
    pages = [(s, p, c) for (s, p, c) in pages if not is_noindex_slug(s)]
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

# ─────────────────────────────────────────
# 影響度スコアリング（マーケットを動かすTOP3用）
# 全カテゴリのニュースから「市場へのインパクトが大きい」記事を選別
# ─────────────────────────────────────────
IMPACT_KEYWORDS = {
    # 中央銀行・金融政策（最高重要度）
    "fomc": 10, "frb": 10, "federal reserve": 10, "powell": 9, "パウエル": 9,
    "rate hike": 10, "rate cut": 10, "interest rate": 7, "monetary policy": 7,
    "利上げ": 10, "利下げ": 10, "政策金利": 9, "金融政策": 7,
    "boj": 10, "bank of japan": 10, "日銀": 10, "ueda": 8, "上田": 8,
    "ecb": 8, "lagarde": 7, "ラガルド": 7,
    "yield curve": 6, "イールドカーブ": 6,

    # 主要経済指標
    "jobs report": 9, "nonfarm": 9, "nfp": 9, "雇用統計": 9,
    "unemployment": 7, "失業率": 8, "employment": 6,
    "cpi": 9, "inflation": 7, "消費者物価": 9, "インフレ": 6,
    "gdp": 8, "pce": 8, "ppi": 6, "ism": 6, "pmi": 6,
    "retail sales": 5, "小売売上": 5,

    # 為替介入・通貨
    "intervention": 10, "為替介入": 10, "介入": 7,
    "財務省": 6, "神田": 7, "三村": 7, "片山": 7, "kanda": 7, "mimura": 7, "katayama": 7,

    # 地政学・大事件
    "war": 8, "戦争": 8, "ukraine": 6, "ウクライナ": 6,
    "middle east": 7, "中東": 7, "iran": 7, "イラン": 7,
    "russia": 6, "ロシア": 6, "israel": 6, "イスラエル": 6,
    "north korea": 7, "北朝鮮": 7, "taiwan": 6, "台湾": 6, "china": 5, "中国": 5,

    # 政治・関税
    "trump": 6, "トランプ": 6, "tariff": 8, "関税": 8,
    "election": 5, "選挙": 5, "sanction": 7, "制裁": 7,

    # 大手企業・決算（個別株名は重みを抑え、決算サプライズ系を相対的に浮上させる）
    "earnings": 4, "決算": 4, "guidance": 5,
    "nvidia": 3, "apple": 3, "microsoft": 3, "meta": 3,
    "tesla": 3, "テスラ": 3, "amazon": 3, "google": 3, "alphabet": 3,

    # 急騰・急落
    "crash": 9, "plunge": 8, "tumble": 7, "sell-off": 7, "selloff": 7,
    "暴落": 9, "急落": 8,
    "surge": 6, "rally": 5, "soar": 6, "急騰": 7, "急上昇": 6,
    "record high": 6, "最高値": 7, "all-time high": 7,

    # 信用・債券・リセッション
    "downgrade": 8, "格下げ": 8, "default": 9, "デフォルト": 9,
    "recession": 8, "景気後退": 8, "リセッション": 8,
    "treasury yield": 5, "国債": 4, "債券": 4,
    "bubble": 6, "バブル": 6,

    # OPEC・原油
    "opec": 6, "supply cut": 6, "減産": 6,
}

# ─────────────────────────────────────────
# ニュース品質向上：追加スコアボーナス
# 「具体性のある記事」「サプライズ・速報」「確定事項」を浮上させる
# ─────────────────────────────────────────
import re as _re_for_impact
IMPACT_BONUS_PATTERNS = [
    # サプライズ・想定外（市場が動く要素）
    (_re_for_impact.compile(r"予想外|想定外|サプライズ|surprise|unexpected|shock|ショック", _re_for_impact.IGNORECASE), 5),
    # 速報・確定事項（観測より結果を優先）
    (_re_for_impact.compile(r"速報|breaking|flash|決定|発表|引下げ|引上げ|cut|hike|raise|signed", _re_for_impact.IGNORECASE), 3),
    # 数字含み（具体性 — %, 円, ドル, bp, 億, 兆 など）
    (_re_for_impact.compile(r"\d+\.?\d*\s*(%|％|円|ドル|\$|¥|bp|bps|億|兆|万|million|billion)", _re_for_impact.IGNORECASE), 3),
    # 銘柄羅列・「動き手」系の薄い記事を抑制
    (_re_for_impact.compile(r"stocks?\s*(movers?|to\s+watch|moving|on\s+the\s+move)|today.?s\s*(gainers|losers|movers)|premarket\s+movers|動き手|値動きの大きい|動く銘柄|gainers\s+and\s+losers", _re_for_impact.IGNORECASE), -5),
]

# 5個以上のカンマ・読点区切り＝銘柄羅列とみなして減点
_LIST_TITLE_RE = _re_for_impact.compile(r"[,、，]")

# ─────────────────────────────────────────
# 日本語高品質 RSS ソース（TOP3候補プールに追加）
# ─────────────────────────────────────────
RSS_FEEDS = [
    ("Bloomberg Markets", "https://feeds.bloomberg.com/markets/news.rss"),
    # 2026-06-28 旧 assets.wor.jp のロイターRSFが死亡(0件・サイレント)→ Google News経由で jp.reuters.com を
    #   直接狙い、日本語のロイター記事を復活（翻訳不要・質の高い日本語ソース）。
    ("ロイター日本",       "https://news.google.com/rss/search?q=site:jp.reuters.com+when:3d&hl=ja&gl=JP&ceid=JP:ja"),
    ("NHK経済",            "https://www3.nhk.or.jp/rss/news/cat5.xml"),
    ("東洋経済オンライン",  "https://toyokeizai.net/list/feed/rss"),
]


_HTML_TAG_RE = _re_for_impact.compile(r"<[^>]+>")

def _strip_html(text):
    if not text:
        return ""
    return _HTML_TAG_RE.sub("", str(text)).strip()


def fetch_rss_articles(source_name, url):
    """RSS フィードから記事を NewsAPI 互換形式で取得"""
    try:
        import feedparser
    except ImportError:
        print(f"⚠️ feedparser 未インストール、RSS スキップ ({source_name})")
        return []
    articles = []
    try:
        feed = feedparser.parse(url, request_headers={"User-Agent": "Mozilla/5.0 marketwatch-jp/1.0"})
        for entry in (feed.entries or [])[:20]:
            title = _strip_html(entry.get("title", ""))
            if not title:
                continue
            articles.append({
                "title": title,
                "description": _strip_html(entry.get("summary", ""))[:300],
                "url": entry.get("link", "") or "",
                "publishedAt": entry.get("published", "") or entry.get("updated", "") or "",
                "source": {"name": source_name},
                "_is_rss": True,  # curated 高品質ソースのマーカー（スコアボーナス用）
            })
    except Exception as e:
        print(f"⚠️ RSS 取得エラー ({source_name}): {e}")
    return articles


def score_article_with_bonuses(article):
    """既存 score_article にボーナスを加算した強化版スコア。
    - キーワード由来のサプライズ・速報・数字ボーナス
    - 銘柄羅列リスト型見出しは減点
    - curated 高品質ソース（RSS_FEEDS）にはベース +5 を付与
    """
    base = score_article(article)
    title = article.get("title", "") or ""
    text = title + " " + (article.get("description", "") or "")
    for pattern, bonus in IMPACT_BONUS_PATTERNS:
        if pattern.search(text):
            base += bonus
    # タイトルに 5 個以上のカンマ・読点 → 銘柄羅列とみなして減点
    if len(_LIST_TITLE_RE.findall(title)) >= 5:
        base -= 5
    # curated RSS ソース優遇（マーケット影響度の高い厳選ソース）
    if article.get("_is_rss"):
        base += 5
    return base


def score_article(article):
    """記事の影響度スコアを計算（タイトル+概要のキーワードマッチ）"""
    text = ((article.get("title", "") or "") + " " +
            (article.get("description", "") or "")).lower()
    if not text.strip():
        return 0
    score = 0
    for kw, weight in IMPACT_KEYWORDS.items():
        if kw in text:
            score += weight
    return score


def hours_since_published(iso_str):
    """ISO 8601文字列から経過時間（hour）を返す。パース失敗時はNone。"""
    if not iso_str:
        return None
    s = iso_str.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except Exception:
        # 日付のみの形式（YYYY-MM-DD）にフォールバック
        try:
            dt = datetime.fromisoformat(s[:10]).replace(tzinfo=timezone.utc)
        except Exception:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    age = (datetime.now(timezone.utc) - dt).total_seconds() / 3600.0
    return max(0.0, age)


def score_article_with_recency(article):
    """影響度スコア（ボーナス込み）× 時間減衰。
    24h以内はほぼ満点、36hで半減、72hで1/4。古い記事がTOP固定されるのを防ぐ。
    ボーナス：サプライズ語 / 速報・確定語 / 数字含みの記事を加点。
    """
    base = score_article_with_bonuses(article)
    if base <= 0:
        return 0.0
    hrs = hours_since_published(article.get("publishedAt", ""))
    if hrs is None:
        # 時刻不明は控えめに扱う（新鮮さ不明 → 24h相当として減衰）
        hrs = 24.0
    # 半減期36h の指数減衰
    decay = 0.5 ** (hrs / 36.0)
    return base * decay


def _get_source_name(article):
    """記事の source 名を安全に取得する。
    yfinance は str、NewsAPI/RSS は dict 形式で source を持つので両方に対応。
    """
    src = article.get("source")
    if isinstance(src, dict):
        return src.get("name") or "unknown"
    if isinstance(src, str) and src:
        return src
    return "unknown"


def select_top_diverse(pool, n=3, source_cap=2, sim_threshold=0.7):
    """スコア順に並んだ pool から、ソース多様性と類似タイトル除外を考慮して n 件選ぶ。
    - source_cap: 同一ソースから採用する最大件数
    - sim_threshold: タイトル類似度（SequenceMatcher ratio）。これ以上は同一とみなして除外
    """
    from difflib import SequenceMatcher
    selected = []
    source_count = {}
    for a in pool:
        if len(selected) >= n:
            break
        title = a.get("title", "")
        if not title:
            continue
        src = _get_source_name(a)
        if source_count.get(src, 0) >= source_cap:
            continue
        # 既選択との類似度チェック
        too_similar = False
        for s in selected:
            ratio = SequenceMatcher(None, title, s.get("title", "")).ratio()
            if ratio >= sim_threshold:
                too_similar = True
                break
        if too_similar:
            continue
        selected.append(a)
        source_count[src] = source_count.get(src, 0) + 1
    return selected


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
            # 発行日時（UNIXタイムスタンプ or ISO形式）— 時刻まで保持して鮮度判定に使う
            pub = ""
            if "pubDate" in content:
                pub = content["pubDate"]  # ISO形式（時刻付き）
            elif "providerPublishTime" in n:
                pub = datetime.fromtimestamp(n["providerPublishTime"], tz=timezone.utc).isoformat()
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
            "publishedAt": a.get("publishedAt", ""),  # ISO形式（時刻まで）
        } for a in data.get("articles", [])]


# ─────────────────────────────────────────
# AI（Gemini）でニュースに「日本人投資家視点」コメントを 1〜2 文生成
# ─────────────────────────────────────────
_GEMINI_NEWS_PROMPT = """以下のマーケットニュースの見出しと説明を読み、日本人個人投資家にとっての意味を1〜2文（合計 80 字以内）で簡潔に解説してください。

カテゴリ: {category}
見出し: {title}
説明: {description}

【ルール】
- 1〜2 文、合計 80 字以内
- 「〜の可能性」「〜要注意」など慎重表現
- 日本人投資家視点（NISA・為替・日本株への波及）を意識
- 出力はコメント文のみ。前置きや見出しは不要"""

_CAT_LABEL = {"top": "マーケット全体", "stocks": "株式", "fx": "為替",
              "commodity": "コモディティ", "crypto": "暗号資産"}


def generate_news_comments_batch(articles, api_key):
    """複数記事を 1 回の Gemini コールでまとめてコメント生成（rate limit 回避）。
    返り値: {index: comment文字列} の dict（インデックスは articles の順序）"""
    if not api_key or not articles:
        return {}
    try:
        import google.generativeai as genai
    except ImportError:
        return {}
    genai.configure(api_key=api_key)

    items = []
    for i, a in enumerate(articles, 1):
        title = (a.get("title") or "")[:180]
        desc = (a.get("description") or "")[:250]
        cat = a.get("_source_cat", "")
        cat_label = _CAT_LABEL.get(cat, cat) if cat else ""
        items.append(f"{i}. [{cat_label}] {title}\n   説明: {desc}")

    prompt = f"""あなたは日本人個人投資家向けのマーケットアナリストです。以下の {len(articles)} 件のニュース見出しと説明を読み、それぞれに対して日本人個人投資家視点のコメントを 1〜2 文（80 字以内）で生成してください。

【ニュース一覧】
{chr(10).join(items)}

【出力フォーマット】（このフォーマットを厳守。JSON 配列のみ。前置き・```マーク・コードフェンス・余計な文字は禁止）
[
  {{"id": 1, "comment": "コメント本文"}},
  {{"id": 2, "comment": "コメント本文"}},
  ...
]

【ルール】
- 必ず {len(articles)} 件分のオブジェクトを返す
- 各 comment は 80 字以内
- 「〜の可能性」「〜要注意」など慎重表現
- 日本人投資家視点（NISA・為替・日本株への波及）
- JSON として valid であること"""

    # クォータが緩いモデルから順に試す（無料枠の RPD/RPM 違いを考慮）
    model_candidates = ("gemini-2.0-flash-lite", "gemini-2.5-flash-lite", "gemini-2.0-flash", "gemini-2.5-flash")
    last_err = ""
    for model_name in model_candidates:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            text = (response.text or "").strip()
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```\s*$", "", text)
            data = json.loads(text)
            result = {}
            for item in data:
                i = item.get("id")
                c = (item.get("comment") or "").strip()
                if isinstance(i, int) and 1 <= i <= len(articles) and c:
                    result[i - 1] = c.replace("\n", " ")[:200]
            if result:
                print(f"  ✅ batch コメント生成成功 ({model_name})")
                return result
        except Exception as e:
            last_err = f"{model_name}: {type(e).__name__}: {str(e)[:80]}"
            continue
    print(f"  ⚠️ batch コメント生成失敗（全モデル）: {last_err}")
    return {}


def generate_news_comment(title, description, category, api_key):
    """Gemini で 1〜2 文の投資家視点コメントを生成。失敗時は空文字"""
    if not api_key or not title:
        return ""
    try:
        import google.generativeai as genai
    except ImportError:
        return ""
    genai.configure(api_key=api_key)
    prompt = _GEMINI_NEWS_PROMPT.format(
        category=_CAT_LABEL.get(category, category),
        title=title[:200],
        description=(description or "")[:400],
    )
    last_err = ""
    for model_name in ("gemini-2.0-flash", "gemini-2.5-flash"):
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            text = (response.text or "").strip()
            if text:
                text = text.replace("\n", " ").replace("\r", "").strip()
                return text[:200]
        except Exception as e:
            last_err = f"{model_name}: {type(e).__name__}: {str(e)[:60]}"
            continue
    if last_err:
        print(f"    ⚠️ news comment 失敗: {last_err}")
    return ""


# ─────────────────────────────────────────
# AI（Gemini）でアセット別投資判断（強気度 / スコア / アクション / 根拠）
# ─────────────────────────────────────────
_GEMINI_ASSET_PROMPT = """あなたは日本人個人投資家向けのマーケット・アナリストです。
以下の {asset_name} の現在価格と直近ニュースから、現時点の投資スタンスを判定してください。

【現在価格】{price}

【直近のニュース見出し】
{news}

【出力フォーマット】（厳守。プレーンテキストのみ。HTML/Markdown は使わない）
===強気度===
(以下から1つ：強気 / やや強気 / ニュートラル / やや弱気 / 弱気)
===スコア===
(-100 から +100 の整数。+100=超強気、0=中立、-100=超弱気)
===アクション===
(以下から1つ：積極買い / 押し目買い準備 / 様子見 / 部分利確 / 一部ヘッジ)
===根拠===
(2 文程度。具体的な価格目線も含める)

【注意】
- ニュース内容に基づく（推測の上塗り禁止）
- 「〜の可能性」など慎重表現
- 日本語のみ"""


def generate_asset_analysis(asset_name, price_str, news_titles, api_key):
    """Gemini でアセット別の投資判断を取得。dict を返す（失敗時は None）"""
    if not api_key:
        return None
    try:
        import google.generativeai as genai
    except ImportError:
        return None
    genai.configure(api_key=api_key)
    news_text = "\n".join([f"- {t[:120]}" for t in news_titles[:10]]) or "（直近の関連ニュースなし）"
    prompt = _GEMINI_ASSET_PROMPT.format(asset_name=asset_name, price=price_str, news=news_text)
    # クォータが緩いモデルから順に試す
    for model_name in ("gemini-2.0-flash-lite", "gemini-2.5-flash-lite", "gemini-2.0-flash", "gemini-2.5-flash"):
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            text = (response.text or "").strip()
            if text:
                return _parse_asset_analysis(text)
        except Exception:
            continue
    return None


def _parse_asset_analysis(text):
    """Gemini プレーンテキスト出力を {sentiment, score, action, reason} に分解"""
    result = {"sentiment": "ニュートラル", "score": 0, "action": "様子見", "reason": ""}
    current = None
    import re as _re
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if "===強気度===" in s:
            current = "sentiment"; continue
        if "===スコア===" in s:
            current = "score"; continue
        if "===アクション===" in s:
            current = "action"; continue
        if "===根拠===" in s:
            current = "reason"; continue
        if current == "sentiment":
            result["sentiment"] = s
        elif current == "score":
            try:
                m = _re.search(r"-?\d+", s)
                if m:
                    result["score"] = max(-100, min(100, int(m.group(0))))
            except Exception:
                pass
        elif current == "action":
            result["action"] = s
        elif current == "reason":
            result["reason"] += s + " "
    result["reason"] = result["reason"].strip()
    return result


def fetch_news(api_key):
    """ニュース取得（yfinance優先 + NewsAPIフォールバック）

    - 各カテゴリ（stocks/fx/commodity/crypto）：最新3件
    - topカテゴリ：全カテゴリ統合 + 影響度×時間減衰スコア順 TOP3
      （36h半減期で古い記事がTOPに居座らないようにする）
    """
    # NewsAPI問い合わせ用の検索開始日（過去2日）— TOP選定では時間減衰でさらに鮮度を要求
    from_date = (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%d")

    # ─── ① 各カテゴリで記事を収集（topは後で全統合から生成） ───
    raw_by_cat = {}
    for cat, queries in NEWS_CATEGORIES.items():
        if cat == "top":
            continue  # topは後で生成
        articles = []
        # yfinance
        yf_tickers = YF_NEWS_TICKERS.get(cat, [])
        try:
            articles.extend(fetch_yf_news_for_category(yf_tickers))
        except Exception as e:
            print(f"⚠️ yfinance news集約エラー ({cat}): {e}")
        # NewsAPI
        if api_key:
            for q in queries:
                try:
                    articles.extend(fetch_newsapi_articles(api_key, q, "en", from_date))
                except Exception as e:
                    print(f"⚠️ NewsAPI取得エラー ({cat}/{q}): {e}")
        # カテゴリ内で重複除去 + 日付降順
        seen = set()
        unique = []
        for a in articles:
            key = a.get("url") or a.get("title")
            if key and key not in seen and "[Removed]" not in a.get("title", ""):
                seen.add(key)
                unique.append(a)
        unique.sort(key=lambda x: x.get("publishedAt", ""), reverse=True)
        raw_by_cat[cat] = unique

    # ─── ② TOP候補プール：全カテゴリ + 高品質 RSS フィード ───
    # 古い高インパクト記事がTOPに張り付くのを防ぐため、半減期36hの指数減衰を適用。
    # さらに、48h以上前の記事はTOP候補から除外（生のインパクトが高くても）。
    MAX_AGE_HOURS = 48.0
    all_seen = set()
    pool = []

    # 既存カテゴリ記事から
    for cat, arts in raw_by_cat.items():
        for a in arts:
            key = a.get("url") or a.get("title")
            if not key or key in all_seen:
                continue
            all_seen.add(key)
            hrs = hours_since_published(a.get("publishedAt", ""))
            if hrs is not None and hrs > MAX_AGE_HOURS:
                continue
            a["_score"] = score_article_with_recency(a)
            a["_raw_score"] = score_article_with_bonuses(a)
            a["_age_h"] = hrs if hrs is not None else -1
            a["_source_cat"] = cat
            pool.append(a)

    # RSS フィードから（環境変数 USE_RSS_FEEDS=false で OFF にできる）
    if os.environ.get("USE_RSS_FEEDS", "true").lower() in ("1", "true", "yes"):
        rss_count = 0
        dead_feeds = []   # 2026-06-28 サイレント失敗の検知: 0件のフィードを記録（精度低下の主因だった）
        for name, url in RSS_FEEDS:
            raw_f = fetch_rss_articles(name, url)
            if not raw_f:
                dead_feeds.append(name)
            for a in raw_f:
                key = a.get("url") or a.get("title")
                if not key or key in all_seen:
                    continue
                all_seen.add(key)
                hrs = hours_since_published(a.get("publishedAt", ""))
                if hrs is not None and hrs > MAX_AGE_HOURS:
                    continue
                a["_score"] = score_article_with_recency(a)
                a["_raw_score"] = score_article_with_bonuses(a)
                a["_age_h"] = hrs if hrs is not None else -1
                a["_source_cat"] = "rss"
                pool.append(a)
                rss_count += 1
        print(f"  📡 RSS: {rss_count}件追加（候補プール合計 {len(pool)}件）")
        if dead_feeds:
            print(f"  🚨 RSSフィードが0件＝要確認(切れ/URL変更の可能性): {', '.join(dead_feeds)}")

    # 減衰後スコア降順 → 同点は新しい順
    pool.sort(key=lambda x: (x.get("_score", 0.0), x.get("publishedAt", "")), reverse=True)
    # 該当が3件未満なら、48h制限を解除して全件から再選定（フォールバック）
    if len(pool) < 3:
        pool = []
        all_seen.clear()
        for cat, arts in raw_by_cat.items():
            for a in arts:
                key = a.get("url") or a.get("title")
                if not key or key in all_seen:
                    continue
                all_seen.add(key)
                a["_score"] = score_article_with_recency(a)
                a["_raw_score"] = score_article_with_bonuses(a)
                a["_source_cat"] = cat
                pool.append(a)
        pool.sort(key=lambda x: (x.get("_score", 0.0), x.get("publishedAt", "")), reverse=True)

    # 多様性確保（ソース完全分散 + 類似タイトル除外）で TOP3 を選ぶ
    # source_cap=1: 同じソースの記事は1件まで → 3ソース完全分散を強制
    top_pool = select_top_diverse(pool, n=3, source_cap=1, sim_threshold=0.7)

    # ─── ③ 結果集計（各カテゴリTOP3 + topのTOP3） ───
    results = {}
    selected = []
    for cat in raw_by_cat:
        results[cat] = raw_by_cat[cat][:3]
        selected.extend(results[cat])
    results["top"] = top_pool
    selected.extend(top_pool)

    # ─── ④ 翻訳（同じdict参照は1回だけ翻訳されるよう id() で重複排除） ───
    import time as _time
    translated_ids = set()
    for a in selected:
        if id(a) in translated_ids:
            continue
        original = a.get("title", "")
        if not original:
            continue
        a["title"] = translate_to_ja(original)
        if a["title"] != original:
            print(f"  ✅ 翻訳: {original[:40]}... → {a['title'][:40]}...")
        translated_ids.add(id(a))
        _time.sleep(0.4)

    # デバッグログ
    print(f"  📊 TOP3スコア: {[a.get('_score', 0) for a in top_pool]}")

    # ─── ⑤ AI（Gemini）で各ニュースに投資家視点コメント生成（バッチ処理）───
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key:
        # 表示対象記事を id() で重複排除して収集
        unique_articles = []
        seen = set()
        for cat, arts in results.items():
            for a in arts:
                if id(a) in seen:
                    continue
                seen.add(id(a))
                # _source_cat にカテゴリ情報を保持（プロンプト生成用）
                if "_source_cat" not in a:
                    a["_source_cat"] = cat
                unique_articles.append(a)
        print(f"  💡 Gemini で {len(unique_articles)} 件のニュースに投資家視点コメント生成中（1回のバッチ呼び出し）...")
        comments = generate_news_comments_batch(unique_articles, gemini_key)
        for idx, art in enumerate(unique_articles):
            if idx in comments and comments[idx]:
                art["ai_comment"] = comments[idx]
        print(f"  ✅ {len(comments)} / {len(unique_articles)} 件にコメント付与")
    else:
        print("  ℹ️ GEMINI_API_KEY 未設定、AI コメントはスキップ")

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
def _format_pub_date(pub_str):
    """ISO 形式または RFC822 形式から YYYY-MM-DD を抽出"""
    if not pub_str:
        return ""
    # ISO 形式（"2026-05-15T...") はそのまま 10 文字
    if len(pub_str) >= 10 and pub_str[4] == "-" and pub_str[7] == "-":
        return pub_str[:10]
    # RFC822 形式 ("Sat, 16 May 2026 ...") は dateutil で解析
    try:
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(pub_str).strftime("%Y-%m-%d")
    except Exception:
        return pub_str[:10]


def build_ai_analysis_section(nikkei_val=None, sp500_val=None, gold_val=None, btc_val=None,
                                stocks_news=None, commodity_news=None, crypto_news=None):
    """AI（Gemini）でアセット別投資判断を生成し HTML セクションを返す。
    GEMINI_API_KEY 未設定なら空文字。"""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return ""

    stocks_news = stocks_news or []
    commodity_news = commodity_news or []
    crypto_news = crypto_news or []
    stock_titles = [a.get("title", "") for a in stocks_news[:10]]
    commodity_titles = [a.get("title", "") for a in commodity_news[:10]]
    crypto_titles = [a.get("title", "") for a in crypto_news[:10]]

    # 4 アセット
    assets = []
    if nikkei_val is not None:
        assets.append(("japan_stocks", "🇯🇵", "日本株（日経平均）", f"{nikkei_val:,.0f}円", stock_titles))
    if sp500_val is not None:
        assets.append(("us_stocks",    "🇺🇸", "米国株（S&P500）",   f"{sp500_val:,.2f}", stock_titles))
    if gold_val is not None:
        assets.append(("gold",         "🥇", "ゴールド",            f"${gold_val:,.0f}/oz", commodity_titles))
    if btc_val is not None:
        assets.append(("btc",          "🪙", "ビットコイン",        f"${btc_val:,.0f}", crypto_titles))

    print(f"  🤖 アセット別 AI 投資判断を生成中（{len(assets)} 件）...")
    import time as _time
    analyses = []
    for key, icon, name, price_str, titles in assets:
        result = generate_asset_analysis(name, price_str, titles, api_key)
        if result:
            analyses.append((key, icon, name, price_str, result))
            print(f"    ✅ {name}: {result.get('sentiment', '?')} / {result.get('action', '?')}")
        else:
            print(f"    ⚠️ {name}: 生成失敗（rate limit の可能性）")
        # Gemini 無料枠 15 RPM 対策で 4.5 秒間隔
        _time.sleep(4.5)
    if not analyses:
        return ""

    # HTML 生成
    cards = []
    for key, icon, name, price_str, a in analyses:
        score = a.get("score", 0)
        pct = max(0, min(100, (score + 100) / 2))
        sentiment = a.get("sentiment", "ニュートラル")
        # 色（弱気=赤、強気=緑、中立=橙）
        if "強気" in sentiment and "弱" not in sentiment:
            color = "#1a7f37"
        elif "弱気" in sentiment:
            color = "#cf222e"
        else:
            color = "#9a6700"
        cards.append(f'''
        <div class="ai-asset-card">
          <div class="ai-asset-header">
            <span class="ai-asset-icon">{icon}</span>
            <div class="ai-asset-name-wrap">
              <div class="ai-asset-name">{name}</div>
              <div class="ai-asset-price">{price_str}</div>
            </div>
            <span class="ai-asset-sentiment" style="background:{color};color:#fff">{sentiment}</span>
          </div>
          <div class="ai-meter">
            <div class="ai-meter-track">
              <div class="ai-meter-dot" style="left:{pct:.0f}%;background:{color}"></div>
            </div>
            <div class="ai-meter-labels"><span>弱気</span><span>中立</span><span>強気</span></div>
          </div>
          <div class="ai-action"><strong>✏️ アクション:</strong> {a.get("action", "様子見")}</div>
          <div class="ai-reason"><strong>💡 根拠:</strong> {a.get("reason", "")}</div>
        </div>''')

    return f'''
  <!-- AI 投資判断（Gemini） -->
  <section class="ai-analysis-section">
    <p class="section-title">🤖 AI 投資判断 <span style="font-size:.7rem;color:#57606a;font-weight:500">（直近ニュースと価格から AI が分析。投資判断は自己責任で）</span></p>
    <div class="ai-analysis-grid">
      {''.join(cards)}
    </div>
  </section>
'''


def build_news_html(articles, limit=3):
    """ニュース記事リストをHTML文字列に変換（センチメントアイコン + AI コメント付き）"""
    if not articles:
        return '<div class="news-empty">ニュースを取得できませんでした</div>'
    html = ""
    for a in articles[:limit]:
        source = _get_source_name(a)
        title = a.get("title", "").replace("{", "").replace("}", "")
        desc = a.get("description", "")
        url = a.get("url", "#")
        pub = _format_pub_date(a.get("publishedAt", ""))
        ai_comment = (a.get("ai_comment") or "").replace("{", "").replace("}", "")
        ai_html = f'<span class="news-ai">💡 {ai_comment}</span>' if ai_comment else ''
        icon, cls = classify_news_sentiment(title, desc)
        html += f'''<a class="news-item" href="{url}" target="_blank" rel="noopener">
          <span class="news-title"><span class="news-sent {cls}">{icon}</span> {title}</span>
          {ai_html}
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
    body{{font-family:'Noto Sans JP','Segoe UI','Hiragino Sans','Yu Gothic',sans-serif;background:#ffffff;color:#1f2328;min-height:100vh}}
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
  .nav-bar{{display:flex;flex-wrap:wrap;gap:10px;justify-content:center;max-width:1000px;margin:0 auto 28px}}
  .nav-btn{{display:inline-flex;align-items:center;justify-content:center;gap:8px;padding:11px 20px;background:#f6f8fa;border:1px solid #d0d7de;border-radius:10px;color:#57606a;text-decoration:none;font-size:.95rem;font-weight:600;transition:all .2s;min-width:170px}}
  .nav-btn:hover{{border-color:#0969da;color:#0969da}}
  .nav-btn.current{{background:#0969da;border-color:#0969da;color:#fff}}
    @media(max-width:600px){{.header-inner{{flex-direction:column}}.vix-value{{font-size:3rem}}.nav-bar{{display:grid;grid-template-columns:1fr 1fr;gap:8px}}.nav-btn{{min-width:0;width:100%;padding:10px 8px;font-size:.82rem}}}}
  </style>
  <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-2552122294306014" crossorigin="anonymous"></script>
  <!-- A8.net広告タグはここに貼る予定 -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;600;700&display=swap" rel="stylesheet">
</head>
<body>
<div id="reading-progress"></div>
<button id="theme-toggle" onclick="toggleTheme()" aria-label="テーマ切替" style="position:fixed;top:16px;right:16px;width:42px;height:42px;border-radius:50%;border:1px solid #d0d7de;background:#fff;cursor:pointer;z-index:9999;box-shadow:0 2px 8px rgba(0,0,0,.1);font-size:18px;display:flex;align-items:center;justify-content:center">🌙</button>
{brand_header("😱", "恐怖指数（VIX）", time_str)}
<main>

<nav class="nav-bar">
  <a class="nav-btn" href="index.html">🏠 トップページ</a>
  <a class="nav-btn" href="political-feed.html">🚨 政治発言ライブ</a>
  <a class="nav-btn" href="track-record.html">📊 シグナル成績</a>
  <a class="nav-btn" href="calendar.html">📅 経済カレンダー</a>
  <a class="nav-btn" href="guides.html">📚 解説記事</a>
  <a class="nav-btn" href="guide-investment-books.html">📖 投資本</a>
  <a class="nav-btn" href="market-health.html">🩺 市場健康度</a>
  <a class="nav-btn" href="hot-assets.html">🔥 出来高急増</a>
  <a class="nav-btn" href="charts.html">📈 50年チャート</a>
  <a class="nav-btn" href="youtube-summary.html">📺 YouTube要約</a>
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

  <div style="background:#f6f8fa;border:1px solid #d0d7de;border-radius:12px;padding:24px 28px;margin-top:24px">
    <h2 style="font-size:1.2rem;color:#1f6feb;margin:0 0 12px;border-bottom:1px solid #d0d7de;padding-bottom:8px">📘 VIX恐怖指数の見方・活用法</h2>
    <p style="font-size:.95rem;color:#424a53;line-height:1.85;margin-bottom:12px">VIX（恐怖指数）は、S&amp;P500のオプション価格から算出される「今後30日間の予想変動率」です。数字が大きいほど投資家が将来の値動きを大きく（＝不安に）見ている、という<strong>市場の“体温計”</strong>のような指標です。株価が急落する局面ではVIXが跳ね上がり、相場が落ち着くと低下します（株価とVIXは逆相関の傾向）。</p>
    <p style="font-size:.95rem;color:#424a53;line-height:1.85;margin-bottom:12px">このページの<strong>90日チャートと早見表</strong>は、次のように読むと実用的です。まず<strong>今のVIXがどの帯（平常/警戒/恐怖）にいるか</strong>を確認します。20以下なら平常運転、20〜30は警戒、30超は強い恐怖です。重要なのは“絶対水準”だけでなく<strong>「直近からの変化の速さ」</strong>。短期間でVIXが急騰したときほど、市場がパニックに傾いている合図になります。</p>
    <ul style="margin:6px 0 14px 22px;color:#424a53;font-size:.94rem;line-height:1.85">
      <li><strong>VIXが低い（〜15）</strong>：相場は静か。積立など淡々とした投資がしやすい一方、過度な楽観は反落の前触れになることも。</li>
      <li><strong>VIXが高い（30〜）</strong>：恐怖が支配。歴史的には“行き過ぎた恐怖”が買い場になったことも多いものの、<strong>どこが底かは誰にも分かりません</strong>。一度に動かず分割で、損切りラインを決めてから臨むのが鉄則です。</li>
      <li><strong>使い方の注意</strong>：VIXは“タイミングを当てる魔法の杖”ではありません。あくまで市場心理の温度を測る補助で、価格そのもののテクニカルや資金管理と<strong>組み合わせて</strong>使うものです。</li>
    </ul>
    <p style="font-size:.9rem;color:#57606a;margin-bottom:8px">▶ あわせて読む：<a href="guide-vix.html" style="color:#0969da">VIX恐怖指数とは？</a> ／ <a href="guide-fear-greed.html" style="color:#0969da">恐怖と強欲指数</a> ／ <a href="market-health.html" style="color:#0969da">市場健康度ダッシュボード</a> ／ <a href="guide-loss-cut.html" style="color:#0969da">恐怖に飲まれない損切りの技術</a></p>
    <p style="font-size:.8rem;color:#6e7781;margin:0">※ 本ページは市場データの提供と一般的な解説であり、特定銘柄の売買推奨や投資助言ではありません。投資判断はご自身の責任で行ってください。</p>
  </div>

</main>
<footer>
  <p>データソース: Yahoo Finance (yfinance) &nbsp;|&nbsp;
  <a href="index.html">🏠 トップページ</a> &nbsp;|&nbsp;
  <a href="calendar.html">📅 経済カレンダー</a> &nbsp;|&nbsp;
  <a href="charts.html">📈 50年チャート</a> &nbsp;|&nbsp;
  <a href="vix.html">😱 VIX</a> &nbsp;|&nbsp;
  <a href="market-health.html">🩺 市場健康度</a> &nbsp;|&nbsp;
  <a href="hot-assets.html">🔥 出来高急増</a> &nbsp;|&nbsp;
  本データは自動取得・表示であり、投資助言ではありません。</p>
  <p style="margin-top:8px"><a href="about.html">運営者情報</a> &nbsp;|&nbsp; <a href="privacy.html">プライバシーポリシー</a> &nbsp;|&nbsp; <a href="contact.html">お問い合わせ</a></p>
<p data-disclaimer="kinsho-v1" style="margin-top:10px;padding-top:10px;border-top:1px dashed #d0d7de;font-size:.78rem;color:#6e7781;line-height:1.6">⚠️ <b>当サイトは金融商品取引業者ではなく、投資助言・代理業の登録もしていません。</b> 本サイトの情報は投資助言ではなく、投資判断はご自身の責任で行ってください。</p>
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
<script>(function(){{var hasExplicit=false;try{{var ss=document.styleSheets;for(var i=0;i<ss.length;i++){{try{{var r=ss[i].cssRules||ss[i].rules;if(!r)continue;for(var j=0;j<r.length;j++){{if(r[j].selectorText&&/body\.dark[^-]/.test(r[j].selectorText+' ')){{hasExplicit=true;break}}}}}}catch(e){{}}if(hasExplicit)break}}}}catch(e){{}}if(!hasExplicit){{var s=document.createElement('style');s.textContent='body.dark{{background:#0d1117!important;color:#e6edf3!important}}body.dark header,body.dark footer,body.dark nav.nav-bar{{background:#161b22!important;color:#e6edf3!important;border-color:#30363d!important}}body.dark .nav-btn{{background:#161b22!important;border-color:#30363d!important;color:#8b949e!important}}body.dark .nav-btn:hover{{border-color:#58a6ff!important;color:#58a6ff!important}}body.dark .nav-btn.current{{background:#1f6feb!important;border-color:#58a6ff!important;color:#fff!important}}body.dark .header-title,body.dark .header-meta,body.dark .header-meta span{{color:#e6edf3!important}}body.dark a{{color:#79c0ff!important}}body.dark h1,body.dark h2,body.dark h3,body.dark h4{{color:#e6edf3!important}}body.dark p,body.dark li,body.dark td{{color:#c9d1d9!important}}body.dark hr{{border-color:#30363d!important}}body.dark th{{background:#0d1117!important;color:#79c0ff!important}}body.dark #theme-toggle{{background:#161b22!important;border-color:#30363d!important;color:#fff!important}}body.dark *[style*="background:#fff"]:not(img),body.dark *[style*="background:#ffffff"]:not(img),body.dark *[style*="background-color:#fff"]:not(img),body.dark *[style*="background-color:#ffffff"]:not(img),body.dark *[style*="background:#f6f8fa"]:not(img),body.dark *[style*="background-color:#f6f8fa"]:not(img){{background:#161b22!important}}body.dark *[style*="border:1px solid #d0d7de"],body.dark *[style*="border-color:#d0d7de"]{{border-color:#30363d!important}}body.dark *[style*="color:#1f2328"],body.dark *[style*="color:#57606a"],body.dark *[style*="color:#6e7781"],body.dark *[style*="color:#424a53"]{{color:#e6edf3!important}}';document.head.appendChild(s)}}function setTheme(t){{document.body.classList.toggle('dark',t==='dark');var b=document.getElementById('theme-toggle');if(b)b.textContent=t==='dark'?'☀️':'🌙';try{{localStorage.setItem('theme',t)}}catch(e){{}}}}window.toggleTheme=function(){{setTheme(document.body.classList.contains('dark')?'light':'dark')}};var t='light';try{{t=localStorage.getItem('theme')||'light'}}catch(e){{}}setTheme(t);}})();</script>
<script src="site-search.js" defer></script>
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
    # range を 0 始まりにして「発表当日」も含める（当日にプレビューが消える不具合の修正・2026-06-05）
    target_dates = [today + timedelta(days=i) for i in range(0, days_ahead + 1)]
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


def build_jp_rankings_section(now_jst):
    """日本株 値上がり率/値下がり率 トップ20（jp-rankings.json）を hot-assets 最上段に描画。
    事実の市場データの中立提示＋教育注記（飛びつき注意）。買い/売り推奨ではない。データ無ければ空文字。"""
    import json as _json
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jp-rankings.json")
    if not os.path.exists(p):
        return ""
    try:
        d = _json.load(open(p, encoding="utf-8"))
    except Exception:
        return ""

    def _fin(a):
        if a is True:
            return '<span title="直近開示の決算が赤字" aria-label="赤字">🔴</span>'
        if a is False:
            return '<span title="直近開示の決算が黒字" aria-label="黒字">🟢</span>'
        return '<span title="決算情報なし" style="color:#8b949e">—</span>'

    def _rows(items, ud):
        out = ""
        for r in items:
            pct = (r.get("pct") or 0) * 100
            sign = "+" if pct >= 0 else ""
            nm = str(r.get("name", ""))[:14]
            sec = str(r.get("sector", ""))[:6]
            t1 = r.get("turnover_d1") or 0
            t2 = r.get("turnover_d2") or 0
            out += (f'<tr><td class="jpr-rk">{r.get("rank","")}</td>'
                    f'<td><div class="jpr-nm">{nm}</div><div class="jpr-meta">{r.get("code","")}・{sec}</div></td>'
                    f'<td class="jpr-pct {ud}">{sign}{pct:.1f}%</td>'
                    f'<td class="jpr-to">{t1:,.0f}<br><span class="jpr-to2">{t2:,.0f}</span></td>'
                    f'<td class="jpr-fin">{_fin(r.get("akaji"))}</td></tr>')
        return out or '<tr><td colspan="5" style="text-align:center;color:#6e7781;padding:16px">データ取得中…</td></tr>'

    head = ('<tr><th>#</th><th>銘柄</th><th style="text-align:right">騰落率</th>'
            '<th style="text-align:right">代金億<br><span style="font-weight:400;font-size:.62rem">前/前々</span></th>'
            '<th style="text-align:center">決算</th></tr>')
    asof = d.get("asof", "")
    up = _rows(d.get("gainers", []), "up")
    down = _rows(d.get("losers", []), "down")
    return f"""
  <section class="jprank">
    <div class="jprank-h">💹 日本株 値上がり率・値下がり率 ランキング</div>
    <div class="jprank-sub">流動性上位 約400銘柄 ／ 前日比（{asof} 終値・自動集計／無保証）。<b>売買代金＝終値×出来高の概算（億円・上＝前日／下＝前々日）</b>。決算アイコン＝直近開示が🟢黒字／🔴赤字。
    <b>⚠️ 大きく動いた銘柄＝良い投資対象ではありません</b>（素の値上がり率上位は飛びつき高値づかみ・落ちるナイフになりやすい）。これは事実の市場データで、特定銘柄の売買推奨や投資助言ではありません。</div>
    <div class="jprank-grid">
      <div class="jprank-col up"><h3>📈 値上がり率 TOP20</h3>
        <div class="table-wrap"><table class="jprank-table"><thead>{head}</thead><tbody>{up}</tbody></table></div></div>
      <div class="jprank-col down"><h3>📉 値下がり率 TOP20</h3>
        <div class="table-wrap"><table class="jprank-table"><thead>{head}</thead><tbody>{down}</tbody></table></div></div>
    </div>
    <div class="jprank-foot">💡 売買代金の「前/前々」2日分で、出来高を伴う本物の動きか・ストップ高で薄商いかが分かります。値上がり率＋大きな売買代金は市場の注目が集まりやすい局面（＝買い推奨ではない）。
    ▶ <a href="guide-volume.html">出来高の見方</a> ／ <a href="guide-loss-cut.html">飛びつきを防ぐ損切り</a></div>
  </section>"""


def build_jp_margin_section(now_jst):
    """信用残ウォッチ（jp-margin.json＝JPX「個別銘柄信用取引残高・日々公表銘柄」日次）を hot-assets に描画。
    事実データの中立提示＋見方注記。買い/売り推奨ではない。データ無ければ空文字。jprank-* のCSSを流用。"""
    import json as _json
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jp-margin.json")
    if not os.path.exists(p):
        return ""
    try:
        d = _json.load(open(p, encoding="utf-8"))
    except Exception:
        return ""
    rows = d.get("rows", [])
    if not rows:
        return ""

    def _ratio(r):
        rt = r.get("ratio")
        if rt is None or rt >= 100:   # 売残が僅少だと倍率が極端に大きく算出されるため注記付きで省略表示
            return '<span style="color:#8b949e" title="売り残が僅少なため倍率は省略（ほぼ買いのみ）">—</span>'
        return f'{rt:g}倍'

    def _mrows(items, side):
        clr = "#cf222e" if side == "buy" else "#1a7f37"
        plk = "buy_pl" if side == "buy" else "sell_pl"
        chgk = "buy_chg" if side == "buy" else "sell_chg"
        out = ""
        for i, r in enumerate(items, 1):
            nm = str(r.get("name", ""))[:13]
            pl = r.get(plk) or 0
            chg = r.get(chgk) or 0
            csign = "+" if chg >= 0 else ""
            out += (f'<tr><td class="jpr-rk">{i}</td>'
                    f'<td><div class="jpr-nm">{nm}</div><div class="jpr-meta">{r.get("code","")}・{str(r.get("mkt",""))[:4]}</div></td>'
                    f'<td class="jpr-pct" style="color:{clr};text-align:right">{pl:.1f}%</td>'
                    f'<td style="text-align:right;white-space:nowrap">{_ratio(r)}</td>'
                    f'<td class="jpr-to" style="text-align:right">{csign}{chg:,}</td></tr>')
        return out or '<tr><td colspan="5" style="text-align:center;color:#6e7781;padding:16px">データ取得中…</td></tr>'

    buy = sorted([r for r in rows if r.get("buy_pl")], key=lambda r: -(r.get("buy_pl") or 0))[:10]
    sell = sorted([r for r in rows if r.get("sell_pl")], key=lambda r: -(r.get("sell_pl") or 0))[:10]
    head_b = ('<tr><th>#</th><th>銘柄</th><th style="text-align:right">買い残/上場</th>'
              '<th style="text-align:right">倍率</th><th style="text-align:right">前日比(株)</th></tr>')
    head_s = head_b.replace("買い残/上場", "売り残/上場")
    asof = d.get("asof", "")
    return f"""
  <section class="jprank">
    <div class="jprank-h">💳 信用残ウォッチ（信用買い残・売り残）</div>
    <div class="jprank-sub">JPX「個別銘柄信用取引残高（日々公表銘柄）」より（{asof} 申込み現在・日次／無保証）。<b>日々公表銘柄＝信用取引が過度に利用される可能性があるとして、取引所が投資家への注意喚起のため信用残高を毎日公表する銘柄</b>（規制措置の対象という意味ではありません）。「買い残/上場」「売り残/上場」＝信用残が上場株数に占める割合。<b>信用倍率＝買い残÷売り残（高い＝買い長／1未満＝売り長）</b>。これは事実の市場データで、特定銘柄の売買推奨や投資助言ではありません。</div>
    <div class="jprank-grid">
      <div class="jprank-col"><h3 style="color:#cf222e">🔴 信用買い残が多い（上場比）</h3>
        <div class="table-wrap"><table class="jprank-table"><thead>{head_b}</thead><tbody>{_mrows(buy, "buy")}</tbody></table></div></div>
      <div class="jprank-col"><h3 style="color:#1a7f37">🟢 信用売り残が多い（上場比）</h3>
        <div class="table-wrap"><table class="jprank-table"><thead>{head_s}</thead><tbody>{_mrows(sell, "sell")}</tbody></table></div></div>
    </div>
    <div class="jprank-foot">💡 信用買い残（上場比）が大きいほど、いずれ反対売買（売り）の対象となりうるため、戻り売り圧力として意識されやすい（上値の重しの目安）。逆に売り残が大きいと、買い戻し（踏み上げ）が起きやすいとされる。いずれも需給の一般的な目安であり、将来の値動きを示すものでも、買い/売り推奨でもありません。
    ▶ <a href="guide-margin-balance.html">信用残・取組の見方</a> ／ <a href="guide-loss-cut.html">飛びつきを防ぐ損切り</a></div>
  </section>"""


def build_hot_assets_html(hot_data, now_jst):
    """hot-assets.html を生成 — 最上段に日本株 値上がり/値下がりランキング、続いて4カテゴリの出来高急増ランキング"""
    time_str = now_jst.strftime("%Y年%m月%d日 %H:%M JST")
    jp_rank_html = build_jp_rankings_section(now_jst)
    jp_margin_html = build_jp_margin_section(now_jst)

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
    body{{font-family:'Noto Sans JP','Segoe UI','Hiragino Sans','Yu Gothic',sans-serif;background:#ffffff;color:#1f2328;min-height:100vh}}
    header{{background:linear-gradient(135deg,#f6f8fa,#ffffff);border-bottom:1px solid #d0d7de;padding:24px 32px}}
    .header-inner{{max-width:1200px;margin:0 auto;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px}}
    .header-title{{font-size:1.6rem;font-weight:700;background:linear-gradient(90deg,#bf3989,#cf222e);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}
    .header-meta{{font-size:.85rem;color:#57606a}}
    .header-meta span{{color:#bf3989;font-weight:600}}
    main{{max-width:1200px;margin:0 auto;padding:32px 24px}}
    .nav-bar{{display:flex;flex-wrap:wrap;gap:10px;justify-content:center;max-width:1000px;margin:0 auto 28px}}
    .nav-btn{{display:inline-flex;align-items:center;justify-content:center;gap:8px;padding:11px 20px;background:#f6f8fa;border:1px solid #d0d7de;border-radius:10px;color:#57606a;text-decoration:none;font-size:.95rem;font-weight:600;transition:all .2s;min-width:170px}}
    .nav-btn:hover{{border-color:#bf3989;color:#bf3989}}
    .nav-btn.current{{background:#3a1f0f;border-color:#bf3989;color:#fff}}

    .intro{{background:linear-gradient(135deg,#fff8c5,#ffffff);border:1px solid #bf3989;border-radius:12px;padding:18px 24px;margin-bottom:32px;color:#1f2328;line-height:1.75;font-size:.9rem}}
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

    .jprank{{background:#f6f8fa;border:1px solid #d0d7de;border-radius:12px;padding:20px 24px;margin-bottom:24px}}
    .jprank-h{{font-size:1.2rem;font-weight:700;color:#1f2328;margin-bottom:4px}}
    .jprank-sub{{font-size:.76rem;color:#57606a;margin-bottom:14px;line-height:1.65}}
    .jprank-sub b{{color:#bf3989}}
    .jprank-grid{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}
    .jprank-col h3{{font-size:1rem;margin-bottom:8px;padding-bottom:6px;border-bottom:2px solid #d0d7de}}
    .jprank-col.up h3{{color:#1a7f37}}
    .jprank-col.down h3{{color:#cf222e}}
    .jprank-table{{width:100%;border-collapse:collapse;font-size:.82rem}}
    .jprank-table th{{font-size:.66rem;color:#57606a;text-align:left;padding:6px 5px;border-bottom:2px solid #d0d7de;font-weight:600;white-space:nowrap}}
    .jprank-table td{{padding:7px 5px;border-bottom:1px solid #e1e6eb;vertical-align:top}}
    .jpr-rk{{font-weight:700;color:#6e7781;text-align:center;width:22px}}
    .jpr-nm{{font-weight:600;color:#1f2328;line-height:1.25}}
    .jpr-meta{{font-size:.66rem;color:#6e7781}}
    .jpr-pct{{font-weight:700;font-variant-numeric:tabular-nums;text-align:right;white-space:nowrap}}
    .jpr-pct.up{{color:#1a7f37}}
    .jpr-pct.down{{color:#cf222e}}
    .jpr-to{{font-variant-numeric:tabular-nums;text-align:right;font-size:.74rem;color:#1f2328;white-space:nowrap;line-height:1.2}}
    .jpr-to2{{color:#8b949e;font-size:.68rem}}
    .jpr-fin{{text-align:center}}
    .jprank-foot{{margin-top:14px;font-size:.76rem;color:#57606a;line-height:1.6;border-top:1px dashed #d0d7de;padding-top:10px}}
    @media(max-width:760px){{.jprank-grid{{grid-template-columns:1fr;gap:18px}}}}

    footer{{background:#f6f8fa;border-top:1px solid #d0d7de;padding:20px 32px;text-align:center;font-size:.78rem;color:#6e7781}}
    footer a{{color:#0969da;text-decoration:none}}
    @media(max-width:600px){{.header-inner{{flex-direction:column}}.hot-section{{padding:16px}}.hot-table{{font-size:.78rem}}.nav-bar{{display:grid;grid-template-columns:1fr 1fr;gap:8px}}.nav-btn{{min-width:0;width:100%;padding:10px 8px;font-size:.82rem}}}}
  </style>
  <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-2552122294306014" crossorigin="anonymous"></script>
  <!-- A8.net広告タグはここに貼る予定 -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;600;700&display=swap" rel="stylesheet">
</head>
<body>
<div id="reading-progress"></div>
<button id="theme-toggle" onclick="toggleTheme()" aria-label="テーマ切替" style="position:fixed;top:16px;right:16px;width:42px;height:42px;border-radius:50%;border:1px solid #d0d7de;background:#fff;cursor:pointer;z-index:9999;box-shadow:0 2px 8px rgba(0,0,0,.1);font-size:18px;display:flex;align-items:center;justify-content:center">🌙</button>
{brand_header("🔥", "出来高急増ランキング", time_str, "本日出来高 ÷ 20日平均")}
<main>

  <!-- ナビゲーション -->
  <nav class="nav-bar">
    <a class="nav-btn" href="index.html">🏠 トップページ</a>
    <a class="nav-btn" href="political-feed.html">🚨 政治発言ライブ</a>
    <a class="nav-btn" href="track-record.html">📊 シグナル成績</a>
    <a class="nav-btn" href="calendar.html">📅 経済カレンダー</a>
    <a class="nav-btn" href="guides.html">📚 解説記事</a>
    <a class="nav-btn" href="guide-investment-books.html">📖 投資本</a>
    <a class="nav-btn" href="market-health.html">🩺 市場健康度</a>
    <a class="nav-btn current" href="hot-assets.html">🔥 出来高急増</a>
    <a class="nav-btn" href="charts.html">📈 50年チャート</a>
    <a class="nav-btn" href="youtube-summary.html">📺 YouTube要約</a>
  </nav>
{jp_rank_html}
{jp_margin_html}
  <!-- 説明 -->
  <div class="intro">
    <b>🔰 急増率（Volume Surge Ratio）</b>とは、<b>本日の出来高 ÷ 直近20営業日の平均出来高</b>のことです。
    「いつもより何倍動いているか」を示し、ニュースや思惑で注目が集まると急増します。
    <b>🔥 3倍以上は異常値</b>、⚡ 1.8倍以上は要注目、1.2倍以上はやや活況の目安。
    出来高のないFX・コモディティ・暗号資産は「値動き率」でランキングしています。
  </div>
{sections_html}

  <div style="background:#f6f8fa;border:1px solid #d0d7de;border-radius:12px;padding:24px 28px;margin-top:24px;max-width:1100px;margin-left:auto;margin-right:auto">
    <h2 style="font-size:1.2rem;color:#1f6feb;margin:0 0 12px;border-bottom:1px solid #d0d7de;padding-bottom:8px">📘 出来高急増ランキングの見方・活用法</h2>
    <p style="font-size:.95rem;color:#424a53;line-height:1.85;margin-bottom:12px">出来高は「その銘柄にどれだけ資金と関心が集まっているか」を示す、価格と並んで重要な情報です。このランキングは<strong>本日の出来高が直近20営業日の平均の何倍か（急増率）</strong>で並べており、ニュース・決算・思惑などで<strong>市場の注目が一気に集まった銘柄</strong>がひと目で分かります。「相場のどこに今、資金が向かっているか」を把握する地図として使えます。</p>
    <p style="font-size:.95rem;color:#424a53;line-height:1.85;margin-bottom:12px">ただし大切な注意点があります。<strong>出来高が急増している＝上がる、ではありません</strong>。急増は「注目された」という事実にすぎず、買いで急増することも、投げ売り（パニック）で急増することもあります。急騰して話題になっている銘柄に勢いで<strong>飛びつくと高値づかみ</strong>になりやすいのは、出来高急増の典型的な落とし穴です。</p>
    <ul style="margin:6px 0 14px 22px;color:#424a53;font-size:.94rem;line-height:1.85">
      <li><strong>“監視リスト”として使う</strong>：ランキングは「今日の主役」を教えてくれる入口。そこから値動き（陽線/陰線・サポートやレジスタンス）を確認してから判断するのが安全です。</li>
      <li><strong>出来高は価格を「確認」する</strong>：上昇に出来高が伴えば本物の買い、出来高を伴わない上昇は息切れしやすい、という見方が基本です。</li>
      <li><strong>急落＋出来高急増＝セリングクライマックス</strong>の可能性も。投げ売りで出来高が爆発した後に反発することもありますが、底は読めないため分割・損切り前提で。</li>
      <li>FX・コモディティ・暗号資産は本当の出来高が取れないため、ここでは<strong>値動き率</strong>でランキングしています。</li>
    </ul>
    <p style="font-size:.9rem;color:#57606a;margin-bottom:8px">▶ あわせて読む：<a href="guide-volume.html" style="color:#0969da">出来高の見方</a> ／ <a href="guide-dow-theory.html" style="color:#0969da">ダウ理論（出来高はトレンドを確認する）</a> ／ <a href="guide-loss-cut.html" style="color:#0969da">飛びつき買いを防ぐ損切りの技術</a></p>
    <p style="font-size:.8rem;color:#6e7781;margin:0">※ 本ページは市場データの提供と一般的な解説であり、特定銘柄の売買推奨や投資助言ではありません。投資判断はご自身の責任で行ってください。</p>
  </div>

</main>
<footer>
  <p>データソース: Yahoo Finance (yfinance) &nbsp;|&nbsp;
  <a href="index.html">🏠 トップページ</a> &nbsp;|&nbsp;
  本データは自動取得・表示であり、投資助言ではありません。</p>
  <p style="margin-top:8px"><a href="about.html">運営者情報</a> &nbsp;|&nbsp; <a href="privacy.html">プライバシーポリシー</a> &nbsp;|&nbsp; <a href="contact.html">お問い合わせ</a></p>
<p data-disclaimer="kinsho-v1" style="margin-top:10px;padding-top:10px;border-top:1px dashed #d0d7de;font-size:.78rem;color:#6e7781;line-height:1.6">⚠️ <b>当サイトは金融商品取引業者ではなく、投資助言・代理業の登録もしていません。</b> 本サイトの情報は投資助言ではなく、投資判断はご自身の責任で行ってください。</p>
</footer>
<script>(function(){{var hasExplicit=false;try{{var ss=document.styleSheets;for(var i=0;i<ss.length;i++){{try{{var r=ss[i].cssRules||ss[i].rules;if(!r)continue;for(var j=0;j<r.length;j++){{if(r[j].selectorText&&/body\.dark[^-]/.test(r[j].selectorText+' ')){{hasExplicit=true;break}}}}}}catch(e){{}}if(hasExplicit)break}}}}catch(e){{}}if(!hasExplicit){{var s=document.createElement('style');s.textContent='body.dark{{background:#0d1117!important;color:#e6edf3!important}}body.dark header,body.dark footer,body.dark nav.nav-bar{{background:#161b22!important;color:#e6edf3!important;border-color:#30363d!important}}body.dark .nav-btn{{background:#161b22!important;border-color:#30363d!important;color:#8b949e!important}}body.dark .nav-btn:hover{{border-color:#58a6ff!important;color:#58a6ff!important}}body.dark .nav-btn.current{{background:#1f6feb!important;border-color:#58a6ff!important;color:#fff!important}}body.dark .header-title,body.dark .header-meta,body.dark .header-meta span{{color:#e6edf3!important}}body.dark a{{color:#79c0ff!important}}body.dark h1,body.dark h2,body.dark h3,body.dark h4{{color:#e6edf3!important}}body.dark p,body.dark li,body.dark td{{color:#c9d1d9!important}}body.dark hr{{border-color:#30363d!important}}body.dark th{{background:#0d1117!important;color:#79c0ff!important}}body.dark #theme-toggle{{background:#161b22!important;border-color:#30363d!important;color:#fff!important}}body.dark *[style*="background:#fff"]:not(img),body.dark *[style*="background:#ffffff"]:not(img),body.dark *[style*="background-color:#fff"]:not(img),body.dark *[style*="background-color:#ffffff"]:not(img),body.dark *[style*="background:#f6f8fa"]:not(img),body.dark *[style*="background-color:#f6f8fa"]:not(img){{background:#161b22!important}}body.dark *[style*="border:1px solid #d0d7de"],body.dark *[style*="border-color:#d0d7de"]{{border-color:#30363d!important}}body.dark *[style*="color:#1f2328"],body.dark *[style*="color:#57606a"],body.dark *[style*="color:#6e7781"],body.dark *[style*="color:#424a53"]{{color:#e6edf3!important}}';document.head.appendChild(s)}}function setTheme(t){{document.body.classList.toggle('dark',t==='dark');var b=document.getElementById('theme-toggle');if(b)b.textContent=t==='dark'?'☀️':'🌙';try{{localStorage.setItem('theme',t)}}catch(e){{}}}}window.toggleTheme=function(){{setTheme(document.body.classList.contains('dark')?'light':'dark')}};var t='light';try{{t=localStorage.getItem('theme')||'light'}}catch(e){{}}setTheme(t);}})();</script>
<script src="site-search.js" defer></script>
</body>
</html>"""


def build_earnings_section():
    """earnings-calendar.json を読んで「主要企業の決算予定」セクションHTMLを返す（無ければ空文字）。
    米国=Nasdaq自動取得 / 日本=キュレーション。生成は build_earnings_calendar.py 側。ここは描画のみ。"""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "earnings-calendar.json")
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return ""
    us = data.get("us") or []
    jp = data.get("jp") or []
    if not us and not jp:
        return ""
    _dow = ["月", "火", "水", "木", "金", "土", "日"]

    def _fmt(ds):
        try:
            d = datetime.strptime(ds, "%Y-%m-%d")
            return f"{d.month}/{d.day}（{_dow[d.weekday()]}）"
        except Exception:
            return "未定"

    def _rows(items, is_jp):
        parts = []
        for e in items:
            ds = e.get("date")
            dtxt = _fmt(ds) if ds else "未定"
            name = e.get("name", "")
            code = (e.get("code") if is_jp else e.get("ticker")) or ""
            tm = e.get("time", "") or ""
            tent = ('<span style="color:#9a6700;font-size:.74rem">（予定）</span>'
                    if e.get("tentative") else "")
            parts.append(
                '<div style="display:flex;gap:8px;align-items:baseline;padding:7px 2px;border-bottom:1px solid #eaeef2">'
                f'<span style="flex:none;width:80px;font-weight:700;color:#1f6feb;font-size:.88rem">{dtxt}</span>'
                f'<span style="flex:1;color:#1f2328;font-size:.9rem;line-height:1.4">{name} '
                f'<span style="color:#6e7781;font-size:.78rem">{code}</span> {tent}</span>'
                f'<span style="flex:none;color:#57606a;font-size:.76rem;white-space:nowrap">{tm}</span>'
                "</div>")
        return "".join(parts) or '<p style="color:#6e7781;font-size:.85rem;padding:8px 2px">準備中</p>'

    updated = data.get("updated", "")
    return (
        '<div style="background:#f6f8fa;border:1px solid #d0d7de;border-radius:12px;padding:22px 26px;margin-top:24px">'
        '<h2 style="font-size:1.2rem;color:#1f6feb;margin:0 0 6px;border-bottom:1px solid #d0d7de;padding-bottom:8px">📊 主要企業の決算予定</h2>'
        f'<p style="font-size:.82rem;color:#6e7781;margin:0 0 14px;line-height:1.6">米国はNasdaqより自動取得／日本は発表予定日（各社IRで確定・日程は変更の場合あり）｜更新: {updated}</p>'
        '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:14px 26px">'
        '<div><div style="font-weight:700;color:#1f2328;margin-bottom:4px;font-size:.98rem">🇺🇸 米国</div>'
        + _rows(us, False) + "</div>"
        '<div><div style="font-weight:700;color:#1f2328;margin-bottom:4px;font-size:.98rem">🇯🇵 日本</div>'
        + _rows(jp, True) + "</div>"
        "</div>"
        '<p style="font-size:.78rem;color:#6e7781;margin:14px 0 0;line-height:1.6">※ 決算日は予告なく変更される場合があります。最新は各社公式IRでご確認ください。本欄は情報提供であり、特定銘柄の売買推奨や投資助言ではありません。</p>'
        "</div>"
    )


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
    earnings_section = build_earnings_section()

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  {seo_head("calendar.html", f"マクロ経済カレンダー {cur_year}年{cur_month}月〜{next_month}月", "米雇用統計・FOMC・CPI・日銀金融政策決定会合・ECB理事会・中国主要指標など、相場を動かす重要イベントを月間カレンダーで一覧表示。日本人投資家向けに重要度ランク付き。")}
  {GA4_TAG}
  <style>
    *{{margin:0;padding:0;box-sizing:border-box}}
    body{{font-family:'Noto Sans JP','Segoe UI','Hiragino Sans','Yu Gothic',sans-serif;background:#ffffff;color:#1f2328;min-height:100vh}}
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
  .nav-bar{{display:flex;flex-wrap:wrap;gap:10px;justify-content:center;max-width:1000px;margin:0 auto 28px}}
  .nav-btn{{display:inline-flex;align-items:center;justify-content:center;gap:8px;padding:11px 20px;background:#f6f8fa;border:1px solid #d0d7de;border-radius:10px;color:#57606a;text-decoration:none;font-size:.95rem;font-weight:600;transition:all .2s;min-width:170px}}
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
  @media(max-width:600px){{.preview-banner{{padding:14px 16px;gap:12px}}.preview-banner-icon{{font-size:1.6rem}}.preview-banner-title{{font-size:.95rem}}.preview-banner-desc{{font-size:.78rem}}.nav-bar{{display:grid;grid-template-columns:1fr 1fr;gap:8px}}.nav-btn{{min-width:0;width:100%;padding:10px 8px;font-size:.82rem}}}}
  </style>
  <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-2552122294306014" crossorigin="anonymous"></script>
  <!-- A8.net広告タグはここに貼る予定 -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;600;700&display=swap" rel="stylesheet">
</head>
<body>
<div id="reading-progress"></div>
<button id="theme-toggle" onclick="toggleTheme()" aria-label="テーマ切替" style="position:fixed;top:16px;right:16px;width:42px;height:42px;border-radius:50%;border:1px solid #d0d7de;background:#fff;cursor:pointer;z-index:9999;box-shadow:0 2px 8px rgba(0,0,0,.1);font-size:18px;display:flex;align-items:center;justify-content:center">🌙</button>
{brand_header("📅", "マクロ経済カレンダー", time_str)}
<main>
<nav class="nav-bar">
  <a class="nav-btn" href="index.html">🏠 トップページ</a>
  <a class="nav-btn" href="political-feed.html">🚨 政治発言ライブ</a>
  <a class="nav-btn" href="track-record.html">📊 シグナル成績</a>
  <a class="nav-btn current" href="calendar.html">📅 経済カレンダー</a>
  <a class="nav-btn" href="guides.html">📚 解説記事</a>
  <a class="nav-btn" href="guide-investment-books.html">📖 投資本</a>
  <a class="nav-btn" href="market-health.html">🩺 市場健康度</a>
  <a class="nav-btn" href="hot-assets.html">🔥 出来高急増</a>
  <a class="nav-btn" href="charts.html">📈 50年チャート</a>
  <a class="nav-btn" href="youtube-summary.html">📺 YouTube要約</a>
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

  {earnings_section}

  <div style="background:#f6f8fa;border:1px solid #d0d7de;border-radius:12px;padding:24px 28px;margin-top:24px">
    <h2 style="font-size:1.2rem;color:#1f6feb;margin:0 0 12px;border-bottom:1px solid #d0d7de;padding-bottom:8px">📘 経済カレンダーの見方・活用法</h2>
    <p style="font-size:.95rem;color:#424a53;line-height:1.85;margin-bottom:12px">経済指標とは、雇用・物価・景気などの「国の経済の通信簿」です。相場が動くのは指標の良し悪しそのものより、<strong>事前の「予想値」と発表された「実績値」のズレ（サプライズ）</strong>。予想を大きく上回る/下回るほど、株価や為替が瞬間的に大きく動きます。このカレンダーは、そうした<strong>“相場が動きやすい日”を前もって把握する</strong>ためのものです。</p>
    <p style="font-size:.95rem;color:#424a53;line-height:1.85;margin-bottom:12px">使い方はシンプルです。まず<strong>今週・来週の「⭐最重要」指標がいつあるか</strong>を確認します。そして——これは実体験からの教訓でもありますが——<strong>重要指標の直前に、新しいポジションを大きく持ち越さない</strong>こと。たとえば米雇用統計やFOMCの前夜にうっかり建てたポジションが、発表直後の急変で損切りになる、というのはよくある失敗です。発表を「跨ぐ」のか「避ける」のかを、事前に決めておくだけでリスクが大きく変わります。</p>
    <ul style="margin:6px 0 14px 22px;color:#424a53;font-size:.94rem;line-height:1.85">
      <li><strong>米雇用統計（NFP）</strong>：毎月第1金曜。米国の景気と利下げ/利上げ観測を左右し、ドル円・米国株が大きく反応。</li>
      <li><strong>米CPI（消費者物価指数）</strong>：インフレの体温計。FRBの政策見通しを通じて全市場に波及。</li>
      <li><strong>FOMC（米金融政策決定会合）</strong>：政策金利の決定。声明・会見のニュアンスまで材料に。</li>
      <li><strong>日銀金融政策決定会合</strong>：日本の金利・円相場・日本株に直結。</li>
    </ul>
    <p style="font-size:.9rem;color:#57606a;margin-bottom:8px">▶ あわせて読む：<a href="preview.html" style="color:#0969da">近日の指標プレビュー（結果別シナリオ）</a> ／ <a href="guide-fomc.html" style="color:#0969da">FOMCとは</a> ／ <a href="guide-us-cpi.html" style="color:#0969da">米CPIとは</a> ／ <a href="guide-position-sizing.html" style="color:#0969da">指標を跨がない資金管理</a></p>
    <p style="font-size:.8rem;color:#6e7781;margin:0">※ 日程は変更される場合があります。本ページは情報提供・一般的な解説であり、特定銘柄の売買推奨や投資助言ではありません。投資判断はご自身の責任で行ってください。</p>
  </div>
</main>
<footer>
  <p>📅 マクロ経済カレンダー ─ 日本人投資家のための経済指標ガイド</p>
  <p style="margin-top:6px">※ 日程は変更される場合があります ｜ 最新情報は各公式サイトでご確認ください</p>
  <p style="margin-top:6px"><a href="index.html">🏠 トップページ</a> ｜ <a href="calendar.html">📅 経済カレンダー</a> ｜ <a href="charts.html">📈 50年チャート</a> ｜ <a href="vix.html">😱 VIX恐怖指数</a> ｜ <a href="market-health.html">🩺 市場健康度</a> ｜ <a href="hot-assets.html">🔥 出来高急増</a></p>
  <p style="margin-top:8px"><a href="about.html">運営者情報</a> &nbsp;|&nbsp; <a href="privacy.html">プライバシーポリシー</a> &nbsp;|&nbsp; <a href="contact.html">お問い合わせ</a></p>
<p data-disclaimer="kinsho-v1" style="margin-top:10px;padding-top:10px;border-top:1px dashed #d0d7de;font-size:.78rem;color:#6e7781;line-height:1.6">⚠️ <b>当サイトは金融商品取引業者ではなく、投資助言・代理業の登録もしていません。</b> 本サイトの情報は投資助言ではなく、投資判断はご自身の責任で行ってください。</p>
</footer>
<script>
function showMonth(m) {{
  document.getElementById('month-cur').style.display = m === 'cur' ? 'block' : 'none';
  document.getElementById('month-next').style.display = m === 'next' ? 'block' : 'none';
  document.querySelectorAll('.tab-btn').forEach(function(btn) {{ btn.classList.remove('active'); }});
  event.target.classList.add('active');
}}
</script>
<script>(function(){{var hasExplicit=false;try{{var ss=document.styleSheets;for(var i=0;i<ss.length;i++){{try{{var r=ss[i].cssRules||ss[i].rules;if(!r)continue;for(var j=0;j<r.length;j++){{if(r[j].selectorText&&/body\.dark[^-]/.test(r[j].selectorText+' ')){{hasExplicit=true;break}}}}}}catch(e){{}}if(hasExplicit)break}}}}catch(e){{}}if(!hasExplicit){{var s=document.createElement('style');s.textContent='body.dark{{background:#0d1117!important;color:#e6edf3!important}}body.dark header,body.dark footer,body.dark nav.nav-bar{{background:#161b22!important;color:#e6edf3!important;border-color:#30363d!important}}body.dark .nav-btn{{background:#161b22!important;border-color:#30363d!important;color:#8b949e!important}}body.dark .nav-btn:hover{{border-color:#58a6ff!important;color:#58a6ff!important}}body.dark .nav-btn.current{{background:#1f6feb!important;border-color:#58a6ff!important;color:#fff!important}}body.dark .header-title,body.dark .header-meta,body.dark .header-meta span{{color:#e6edf3!important}}body.dark a{{color:#79c0ff!important}}body.dark h1,body.dark h2,body.dark h3,body.dark h4{{color:#e6edf3!important}}body.dark p,body.dark li,body.dark td{{color:#c9d1d9!important}}body.dark hr{{border-color:#30363d!important}}body.dark th{{background:#0d1117!important;color:#79c0ff!important}}body.dark #theme-toggle{{background:#161b22!important;border-color:#30363d!important;color:#fff!important}}body.dark *[style*="background:#fff"]:not(img),body.dark *[style*="background:#ffffff"]:not(img),body.dark *[style*="background-color:#fff"]:not(img),body.dark *[style*="background-color:#ffffff"]:not(img),body.dark *[style*="background:#f6f8fa"]:not(img),body.dark *[style*="background-color:#f6f8fa"]:not(img){{background:#161b22!important}}body.dark *[style*="border:1px solid #d0d7de"],body.dark *[style*="border-color:#d0d7de"]{{border-color:#30363d!important}}body.dark *[style*="color:#1f2328"],body.dark *[style*="color:#57606a"],body.dark *[style*="color:#6e7781"],body.dark *[style*="color:#424a53"]{{color:#e6edf3!important}}';document.head.appendChild(s)}}function setTheme(t){{document.body.classList.toggle('dark',t==='dark');var b=document.getElementById('theme-toggle');if(b)b.textContent=t==='dark'?'☀️':'🌙';try{{localStorage.setItem('theme',t)}}catch(e){{}}}}window.toggleTheme=function(){{setTheme(document.body.classList.contains('dark')?'light':'dark')}};var t='light';try{{t=localStorage.getItem('theme')||'light'}}catch(e){{}}setTheme(t);}})();</script>
<script src="site-search.js" defer></script>
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
        if delta == 0:
            return "本日"
        elif delta == 1:
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

    # ── 🆕 2026-06-06 発表後の「結果速報」セクション（indicator-result.json 由来） ──
    # index トップのバナーが結果速報へ刷り替わるのと同一条件（verified・発表当日〜翌日）で、
    # preview.html 本体の先頭にも結果（実数値・市場反応・要約・出典）を表示する。
    # ※ これまで preview 本体は upcoming（発表前）しか描画せず、バナーから飛んでも中身が空だった不具合の修正。
    result_html = ""
    for res in _load_indicator_results(now_jst):
        r_name = res.get("name", "経済指標")
        r_flag = country_flag(res.get("country", "us"))
        r_head = res.get("headline", "")
        r_result = res.get("result", "")
        r_react = res.get("market_reaction", "")
        r_summary = res.get("summary", "")
        try:
            _ed = datetime.strptime(res.get("event_date", ""), "%Y-%m-%d")
            r_date = f"{_ed.month}/{_ed.day} 発表"
        except Exception:
            r_date = "発表済み"
        result_line = (f'<p style="font-size:.96rem;color:#1f2328;margin-bottom:12px">'
                       f'<strong style="color:#1a7f37">📌 ポイント：</strong>{r_result}</p>') if r_result else ""
        react_line = (f'<div style="background:#ddf4ff;border-left:4px solid #0969da;border-radius:6px;'
                      f'padding:14px 18px;margin-bottom:14px;font-size:.93rem;color:#1f2328;line-height:1.7">'
                      f'<strong style="color:#0969da">📈 市場の反応：</strong>{r_react}</div>') if r_react else ""
        summary_line = (f'<p style="font-size:.95rem;color:#424a53;line-height:1.85">{r_summary}</p>') if r_summary else ""
        src_list = [s for s in (res.get("sources") or []) if isinstance(s, str) and s.startswith("http")][:4]
        if src_list:
            links = "".join(
                f'<a href="{u}" target="_blank" rel="nofollow noopener" '
                f'style="color:#0969da;font-size:.82rem;margin-right:14px;word-break:break-all">🔗 '
                f'{u.split("/")[2] if "//" in u else u}</a>'
                for u in src_list
            )
            sources_html = (f'<div style="margin-top:14px"><span style="font-size:.78rem;color:#6e7781">出典：</span> '
                            f'{links}</div>')
        else:
            sources_html = ""
        result_html += f'''
<section style="background:linear-gradient(135deg,#e6ffed,#ffffff);border:1px solid #1a7f37;border-radius:14px;padding:22px 26px;margin-bottom:28px">
  <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:10px">
    <span style="background:#1a7f37;color:#fff;font-weight:700;font-size:.82rem;padding:4px 12px;border-radius:999px">📊 結果速報</span>
    <span style="font-size:.82rem;color:#57606a">{r_date}</span>
  </div>
  <h2 style="font-size:1.25rem;color:#1a7f37;margin-bottom:12px;line-height:1.5">{r_flag} {r_name}</h2>
  <div style="background:#ffffff;border:1px solid #1a7f37;border-radius:10px;padding:14px 18px;margin-bottom:14px;font-size:1.02rem;font-weight:700;color:#1f2328;line-height:1.6">{r_head}</div>
  {result_line}
  {react_line}
  {summary_line}
  {sources_html}
  <p style="font-size:.78rem;color:#6e7781;margin-top:14px;line-height:1.7">※ 数値は発表直後に公開情報をもとに記録したもので、確報値・改定で変わる場合があります。本内容は情報提供であり投資助言ではありません。投資判断はご自身の責任で行ってください。</p>
</section>
'''

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  {seo_head("preview.html", "明日の重要経済指標プレビュー", "米CPI・FOMC・雇用統計・日銀金融政策決定会合・ECB理事会など、明日〜数日先に発表される重要経済指標の事前解説。結果別の市場影響シナリオを日本人投資家向けに簡潔に解説。")}
  {GA4_TAG}
  <style>
    *{{margin:0;padding:0;box-sizing:border-box}}
    body{{font-family:'Noto Sans JP','Segoe UI','Hiragino Sans','Yu Gothic',sans-serif;background:#ffffff;color:#1f2328;min-height:100vh;line-height:1.7}}
    header{{background:linear-gradient(135deg,#f6f8fa,#ffffff);border-bottom:1px solid #d0d7de;padding:24px 32px}}
    .header-inner{{max-width:1100px;margin:0 auto;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px}}
    .header-title{{font-size:1.6rem;font-weight:700;background:linear-gradient(90deg,#1a7f37,#1f6feb);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}
    .header-meta{{font-size:.85rem;color:#57606a}}
    .header-meta span{{color:#1a7f37;font-weight:600}}
    main{{max-width:1100px;margin:0 auto;padding:32px 24px}}
    .nav-bar{{display:flex;flex-wrap:wrap;gap:10px;justify-content:center;max-width:1000px;margin:0 auto 28px}}
    .nav-btn{{display:inline-flex;align-items:center;justify-content:center;gap:8px;padding:11px 20px;background:#f6f8fa;border:1px solid #d0d7de;border-radius:10px;color:#57606a;text-decoration:none;font-size:.95rem;font-weight:600;transition:all .2s;min-width:170px}}
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
    @media(max-width:600px){{
      .nav-bar{{display:grid;grid-template-columns:1fr 1fr;gap:8px}}
      .nav-btn{{min-width:0;width:100%;padding:10px 8px;font-size:.82rem}}
    }}
  </style>
  <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-2552122294306014" crossorigin="anonymous"></script>
  <!-- A8.net広告タグはここに貼る予定 -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;600;700&display=swap" rel="stylesheet">
</head>
<body>
<div id="reading-progress"></div>
<button id="theme-toggle" onclick="toggleTheme()" aria-label="テーマ切替" style="position:fixed;top:16px;right:16px;width:42px;height:42px;border-radius:50%;border:1px solid #d0d7de;background:#fff;cursor:pointer;z-index:9999;box-shadow:0 2px 8px rgba(0,0,0,.1);font-size:18px;display:flex;align-items:center;justify-content:center">🌙</button>
{brand_header("📰", "明日の経済指標プレビュー", time_str)}
<main>
<nav class="nav-bar">
  <a class="nav-btn" href="index.html">🏠 トップページ</a>
  <a class="nav-btn" href="political-feed.html">🚨 政治発言ライブ</a>
  <a class="nav-btn" href="track-record.html">📊 シグナル成績</a>
  <a class="nav-btn" href="calendar.html">📅 経済カレンダー</a>
  <a class="nav-btn" href="guides.html">📚 解説記事</a>
  <a class="nav-btn" href="guide-investment-books.html">📖 投資本</a>
  <a class="nav-btn" href="market-health.html">🩺 市場健康度</a>
  <a class="nav-btn" href="hot-assets.html">🔥 出来高急増</a>
  <a class="nav-btn" href="charts.html">📈 50年チャート</a>
  <a class="nav-btn" href="youtube-summary.html">📺 YouTube要約</a>
</nav>

  <div class="beginner-box">
    今後3日以内に発表される重要経済指標について、<strong>「どんな結果ならマーケットがどう動くか」</strong>を事前にシナリオ別に解説しています。発表の前にポジションを軽くするか、結果が出てから動くかの判断材料にお使いください。
  </div>

  {result_html}

  {summary_html}

  {cards_html}

  <div class="disclaimer">
    ※ 各シナリオは過去の傾向に基づく一般的な解説であり、実際の相場の動きを保証するものではありません。指標発表時のヘッドラインや要人発言など複数の要因で動きが変わるため、参考情報としてご活用ください。投資判断はご自身の責任で行ってください。
  </div>

</main>
<footer>
  <p>📰 経済指標プレビュー ─ 日本人投資家のための事前解説ページ</p>
  <p style="margin-top:6px">毎日更新 ｜ <a href="index.html">🏠 トップページ</a> ｜ <a href="calendar.html">📅 経済カレンダー</a> ｜ <a href="charts.html">📈 50年チャート</a> ｜ <a href="vix.html">😱 VIX</a> ｜ <a href="market-health.html">🩺 市場健康度</a> ｜ <a href="hot-assets.html">🔥 出来高急増</a></p>
  <p style="margin-top:8px"><a href="about.html">運営者情報</a> &nbsp;|&nbsp; <a href="privacy.html">プライバシーポリシー</a> &nbsp;|&nbsp; <a href="contact.html">お問い合わせ</a></p>
<p data-disclaimer="kinsho-v1" style="margin-top:10px;padding-top:10px;border-top:1px dashed #d0d7de;font-size:.78rem;color:#6e7781;line-height:1.6">⚠️ <b>当サイトは金融商品取引業者ではなく、投資助言・代理業の登録もしていません。</b> 本サイトの情報は投資助言ではなく、投資判断はご自身の責任で行ってください。</p>
</footer>
<script>(function(){{var hasExplicit=false;try{{var ss=document.styleSheets;for(var i=0;i<ss.length;i++){{try{{var r=ss[i].cssRules||ss[i].rules;if(!r)continue;for(var j=0;j<r.length;j++){{if(r[j].selectorText&&/body\.dark[^-]/.test(r[j].selectorText+' ')){{hasExplicit=true;break}}}}}}catch(e){{}}if(hasExplicit)break}}}}catch(e){{}}if(!hasExplicit){{var s=document.createElement('style');s.textContent='body.dark{{background:#0d1117!important;color:#e6edf3!important}}body.dark header,body.dark footer,body.dark nav.nav-bar{{background:#161b22!important;color:#e6edf3!important;border-color:#30363d!important}}body.dark .nav-btn{{background:#161b22!important;border-color:#30363d!important;color:#8b949e!important}}body.dark .nav-btn:hover{{border-color:#58a6ff!important;color:#58a6ff!important}}body.dark .nav-btn.current{{background:#1f6feb!important;border-color:#58a6ff!important;color:#fff!important}}body.dark .header-title,body.dark .header-meta,body.dark .header-meta span{{color:#e6edf3!important}}body.dark a{{color:#79c0ff!important}}body.dark h1,body.dark h2,body.dark h3,body.dark h4{{color:#e6edf3!important}}body.dark p,body.dark li,body.dark td{{color:#c9d1d9!important}}body.dark hr{{border-color:#30363d!important}}body.dark th{{background:#0d1117!important;color:#79c0ff!important}}body.dark #theme-toggle{{background:#161b22!important;border-color:#30363d!important;color:#fff!important}}body.dark *[style*="background:#fff"]:not(img),body.dark *[style*="background:#ffffff"]:not(img),body.dark *[style*="background-color:#fff"]:not(img),body.dark *[style*="background-color:#ffffff"]:not(img),body.dark *[style*="background:#f6f8fa"]:not(img),body.dark *[style*="background-color:#f6f8fa"]:not(img){{background:#161b22!important}}body.dark *[style*="border:1px solid #d0d7de"],body.dark *[style*="border-color:#d0d7de"]{{border-color:#30363d!important}}body.dark *[style*="color:#1f2328"],body.dark *[style*="color:#57606a"],body.dark *[style*="color:#6e7781"],body.dark *[style*="color:#424a53"]{{color:#e6edf3!important}}';document.head.appendChild(s)}}function setTheme(t){{document.body.classList.toggle('dark',t==='dark');var b=document.getElementById('theme-toggle');if(b)b.textContent=t==='dark'?'☀️':'🌙';try{{localStorage.setItem('theme',t)}}catch(e){{}}}}window.toggleTheme=function(){{setTheme(document.body.classList.contains('dark')?'light':'dark')}};var t='light';try{{t=localStorage.getItem('theme')||'light'}}catch(e){{}}setTheme(t);}})();</script>
<script src="site-search.js" defer></script>
</body>
</html>"""


def fetch_jp_10y(timeout=15):
    """財務省「国債金利情報」CSV から日本10年国債利回り(%)と基準日(YYYY-MM-DD)を返す。失敗時 (None, None)。"""
    import urllib.request
    url = "https://www.mof.go.jp/jgbs/reference/interest_rate/jgbcm.csv"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        txt = urllib.request.urlopen(req, timeout=timeout).read().decode("shift_jis", errors="replace")
    except Exception:
        return None, None
    rows = []
    for line in txt.splitlines():
        cells = line.split(",")
        # 基準日が和暦（R8.6.11 等）で、10年カラム(index10)まである行のみ
        if cells and cells[0][:1] in ("R", "H", "S") and "." in cells[0] and len(cells) > 10:
            rows.append(cells)
    if not rows:
        return None, None
    last = rows[-1]
    try:
        y10 = round(float(last[10]), 3)   # ヘッダ: 基準日,1年,2年,…,10年(=index10)
    except Exception:
        return None, None
    gdate = None
    try:
        era = last[0][0]
        y, m, d = (int(x) for x in last[0][1:].split("."))
        base = {"R": 2018, "H": 1988, "S": 1925}.get(era, 2018)  # 和暦→西暦
        gdate = f"{base + y:04d}-{m:02d}-{d:02d}"
    except Exception:
        pass
    return y10, gdate


def fetch_rate_panel(timeout=15):
    """日米10年国債利回りと金利差を返す。{us10, jp10, jp_date, diff} or None（安全フォールバック）。"""
    import urllib.request
    import json as _json
    us10 = None
    try:
        u = "https://query1.finance.yahoo.com/v8/finance/chart/%5ETNX?interval=1d&range=5d"
        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
        d = _json.loads(urllib.request.urlopen(req, timeout=timeout).read())
        cl = [x for x in d["chart"]["result"][0]["indicators"]["quote"][0]["close"] if x is not None]
        us10 = round(cl[-1], 3) if cl else None
    except Exception:
        us10 = None
    jp10, jp_date = fetch_jp_10y(timeout)
    if us10 is None or jp10 is None:
        return None
    # 差は表示と同じ「小数2桁」同士で計算（4.49−2.68=1.81 と読者の暗算が一致するように）
    diff = round(round(us10, 2) - round(jp10, 2), 2)
    return {"us10": us10, "jp10": jp10, "jp_date": jp_date, "diff": diff}


def fetch_curve_credit(timeout=15):
    """米イールドカーブ(3M/5Y/10Y/30Y)とクレジットの体温(HY債ETF)を Yahoo から取得（無料）。失敗時 None。"""
    import urllib.request
    import json as _json

    def _y(t):
        try:
            u = f"https://query1.finance.yahoo.com/v8/finance/chart/{t}?interval=1d&range=3mo"
            req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
            d = _json.loads(urllib.request.urlopen(req, timeout=timeout).read())["chart"]["result"][0]
            cl = [x for x in d["indicators"]["quote"][0]["close"] if x is not None]
            mp = d["meta"].get("regularMarketPrice")
            last = mp if mp is not None else (cl[-1] if cl else None)
            ago = cl[-22] if len(cl) >= 22 else (cl[0] if cl else None)
            return last, ago
        except Exception:
            return None, None

    t3m, _ = _y("%5EIRX"); t5, _ = _y("%5EFVX"); t10, t10a = _y("%5ETNX"); t30, _ = _y("%5ETYX")
    hyg, hyga = _y("HYG"); ief, iefa = _y("IEF")
    if t10 is None or t3m is None or hyg is None or ief is None:
        return None
    out = {"t3m": round(t3m, 2), "t5": round(t5, 2) if t5 else None,
           "t10": round(t10, 2), "t30": round(t30, 2) if t30 else None,
           "curve": round(t10 - t3m, 2),
           "t10_chg": round(t10 - t10a, 2) if t10a else None}
    ratio_ago = (hyga / iefa) if (hyga and iefa) else None
    out["credit_chg"] = round(((hyg / ief) / ratio_ago - 1) * 100, 2) if ratio_ago else None
    out["hyg_chg"] = round((hyg / hyga - 1) * 100, 2) if hyga else None
    return out


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

    # ④ 金融環境（金利）— 10年債は取得失敗時に当該カードのみ消える。スワップ用の政策金利は手動メンテ。
    _rp = fetch_rate_panel()

    # 政策金利（手動メンテ：中央銀行の会合時のみ更新。出典: investing.com 等）
    POLICY = {"updated": "2026-06-13", "USD": 3.75, "EUR": 2.40, "GBP": 3.75, "AUD": 4.35, "JPY": 0.75}
    _swtd = "padding:10px 12px;border-bottom:1px solid #d0d7de;color:#24292f!important"
    swap_rows = ""
    for _name, _cur in [("米ドル/円", "USD"), ("ユーロ/円", "EUR"), ("ポンド/円", "GBP"), ("豪ドル/円", "AUD")]:
        _d = round(POLICY[_cur] - POLICY["JPY"], 2)
        if _d > 0:
            _dir, _sg = "ロングで受取 / ショートで支払", "+"
        elif _d < 0:
            _dir, _sg = "ロングで支払 / ショートで受取", ""
        else:
            _dir, _sg = "ほぼ中立", ""
        _dc = "#57606a"   # 損益を連想させない中立色（コンプラ: 利益示唆の回避）
        swap_rows += (f'<tr><td style="{_swtd};font-size:1rem">{_name}</td>'
                      f'<td style="{_swtd};text-align:right;font-weight:700;font-size:1.05rem">{_sg}{_d:.2f}%</td>'
                      f'<td style="{_swtd};font-weight:600;color:{_dc}!important;font-size:.92rem">{_dir}</td></tr>')

    bond_card = ""
    if _rp:
        bond_card = f'''      <article class="card" style="grid-column:1 / -1">
        <div class="card-header"><div class="card-title">🏦 日米10年国債 利回り比較</div><div class="card-sub">為替（ドル円）を動かす最大の要因</div></div>
        <table style="width:100%;border-collapse:collapse;margin:8px 0 4px">
          <tr><td style="padding:11px 12px;border-bottom:1px solid #d0d7de;font-size:1rem;color:#24292f!important">🇺🇸 米10年国債</td><td style="padding:11px 12px;border-bottom:1px solid #d0d7de;text-align:right;font-weight:700;font-size:1.1rem;color:#24292f!important">{_rp['us10']:.2f}%</td></tr>
          <tr><td style="padding:11px 12px;border-bottom:1px solid #d0d7de;font-size:1rem;color:#24292f!important">🇯🇵 日本10年国債</td><td style="padding:11px 12px;border-bottom:1px solid #d0d7de;text-align:right;font-weight:700;font-size:1.1rem;color:#24292f!important">{_rp['jp10']:.2f}%</td></tr>
          <tr><td style="padding:13px 12px;font-weight:700;color:#0969da!important;font-size:1.05rem">📊 日米金利差</td><td style="padding:13px 12px;text-align:right;font-weight:800;color:#0969da!important;font-size:1.5rem">{_rp['diff']:.2f}%</td></tr>
        </table>
        <p class="comment">一般に <b>金利差が開く＝円安</b>、<b>縮む＝円高</b> に傾きやすい（金利の高いドルを持つほど利息を多く得られるため）。ただし日銀・FRBの政策や市場心理でも為替は動きます。</p>
        <div class="beginner">出典: 米＝Yahoo Finance（米10年債利回り ^TNX・当日）／ 日＝財務省「国債金利情報」（{_rp['jp_date']} 基準）。差 ＝ 米 − 日。これは情報提供であり投資助言ではありません。</div>
      </article>
'''
    swap_card = f'''      <article class="card" style="grid-column:1 / -1">
        <div class="card-header"><div class="card-title">💱 主要通貨ペアの金利差（スワップの向き）</div><div class="card-sub">各国の政策金利の差 ＝ FXのスワップに効く短期金利</div></div>
        <table style="width:100%;border-collapse:collapse;margin:8px 0 4px">
          <tr><td style="padding:8px 12px;border-bottom:2px solid #d0d7de;color:#57606a!important;font-size:.84rem;font-weight:600">通貨ペア</td><td style="padding:8px 12px;border-bottom:2px solid #d0d7de;text-align:right;color:#57606a!important;font-size:.84rem;font-weight:600">政策金利差</td><td style="padding:8px 12px;border-bottom:2px solid #d0d7de;color:#57606a!important;font-size:.84rem;font-weight:600">スワップの向き</td></tr>
          {swap_rows}
        </table>
        <div style="font-size:.8rem;color:#57606a;margin:8px 2px 0">参考・各国政策金利（{POLICY['updated']}時点）：米 {POLICY['USD']:.2f}％／欧 {POLICY['EUR']:.2f}％／英 {POLICY['GBP']:.2f}％／豪 {POLICY['AUD']:.2f}％／日 {POLICY['JPY']:.2f}％</div>
        <p class="comment">金利の<b>高い通貨を買って（ロング）</b>低い円を売ると、その金利差ぶんのスワップを受け取れる一方、<b>反対向きでは支払い</b>になります。目安として差が大きいほどスワップも大きくなる傾向がありますが、<b>為替が逆に動けばスワップ以上の評価損が出ることもあり、スワップだけで利益が出るわけではありません</b>。</p>
        <div class="beginner">⚠️ これは各国<b>政策金利の差</b>であり、実際に付与されるスワップポイントの<b>金額はFX会社ごとに異なります</b>（手数料ぶん目減りし、ロングとショートで非対称）。政策金利は中央銀行の会合時のみ更新。これは情報提供であり投資助言ではありません。</div>
      </article>
'''
    # イールドカーブ＋クレジットの体温（Yahoo・無料。取得失敗時は当該カードのみ消える）
    _cc = fetch_curve_credit()
    curve_card = credit_card = ""
    if _cc:
        _cv = _cc["curve"]
        if _cv <= -0.05:
            cv_color, cv_label = "#da3633", "逆イールド"
        elif _cv <= 0.5:
            cv_color, cv_label = "#9a6700", "フラット気味"
        else:
            cv_color, cv_label = "#1a7f37", "順イールド（正常）"
        _t10c = _cc.get("t10_chg")
        _t10s = (f"（1か月 {'+' if _t10c >= 0 else ''}{_t10c:.2f}pt）" if _t10c is not None else "")
        _t5s = f"{_cc['t5']:.2f}％" if _cc['t5'] else "—"
        _t30s = f"{_cc['t30']:.2f}％" if _cc['t30'] else "—"
        curve_card = f'''      <article class="card">
        <div class="card-header"><div class="card-title">📐 米イールドカーブ（10年−3か月）</div><div class="card-sub">長短逆転＝景気後退の前兆とされる</div></div>
        <div class="big-num" style="color:{cv_color}">{_cc['curve']:+.2f}% {_tag(cv_color, cv_label)}</div>
        <div style="font-size:.86rem;color:#57606a;margin:6px 0 2px">3か月 {_cc['t3m']:.2f}％ ／ 5年 {_t5s} ／ 10年 {_cc['t10']:.2f}％{_t10s} ／ 30年 {_t30s}</div>
        <p class="comment">長期(10年)が短期(3か月)より高い＝<b>順イールド（正常）</b>。長短が逆転（逆イールド）すると、過去は景気後退の前に現れることが多かった指標です（必ず当たるわけではありません）。米NY連銀の景気後退モデルも10年−3か月を使用。</p>
        <div class="beginner">出典: Yahoo Finance（^IRX/^FVX/^TNX/^TYX・当日）。くわしくは <a href="guide-yield-curve.html" style="color:#1f6feb">イールドカーブ・逆イールドとは</a>。情報提供であり投資助言ではありません。</div>
      </article>
'''
        _crc = _cc.get("credit_chg")
        if _crc is None:
            cr_color, cr_label = "#57606a", "データ取得中"
        elif _crc <= -1.5:
            cr_color, cr_label = "#da3633", "警戒（クレジット悪化）"
        elif _crc < 0.5:
            cr_color, cr_label = "#9a6700", "中立"
        else:
            cr_color, cr_label = "#1a7f37", "良好（リスクオン）"
        _hc = _cc.get("hyg_chg")
        _hcs = f"{'+' if _hc >= 0 else ''}{_hc:.1f}％" if _hc is not None else "—"
        _crcs = f"{'+' if _crc >= 0 else ''}{_crc:.1f}％" if _crc is not None else "—"
        credit_card = f'''      <article class="card">
        <div class="card-header"><div class="card-title">💳 クレジットの体温（ハイイールド債）</div><div class="card-sub">スプレッド拡大＝リスクオフの早期サイン</div></div>
        <div class="big-num" style="color:{cr_color}">{_tag(cr_color, cr_label)}</div>
        <div style="font-size:.86rem;color:#57606a;margin:6px 0 2px">HY債ETF(HYG) 1か月 {_hcs} ／ 対米国債(HYG÷IEF) {_crcs}</div>
        <p class="comment">クレジットスプレッド（低格付け債と国債の利回り差）が広がると、ハイイールド債(HYG)が安全な国債(IEF)に対して値下がりします。その相対の動きで“信用の体温”を見ます。株価より先に悪化することがある早期警報です。</p>
        <div class="beginner">出典: Yahoo Finance（HYG・IEF）。精密なスプレッド(OAS)ではなくETF相対による代理指標。くわしくは <a href="guide-credit-spread.html" style="color:#1f6feb">クレジットスプレッドとは</a>。情報提供であり投資助言ではありません。</div>
      </article>
'''
    rate_section = f'''  <section class="section">
    <div class="section-title">④ 金融環境 ― 金利・イールドカーブ・クレジット</div>
    <div class="cards">
{bond_card}{curve_card}{credit_card}{swap_card}    </div>
  </section>

'''

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
{seo_head("market-health.html", "市場健康度ダッシュボード", "VIX・恐怖&強欲指数・バフェット指数・CAPEレシオ・騰落レシオを一画面で可視化。割高/割安/過熱/底値圏を色分け表示し、相場全体の温度感を瞬時に判断できます。")}
{GA4_TAG}
<style>
  *{{margin:0;padding:0;box-sizing:border-box}}
  body{{font-family:'Noto Sans JP','Segoe UI','Hiragino Sans','Yu Gothic','Meiryo',sans-serif;background:#ffffff;color:#1f2328;min-height:100vh;font-size:16px;line-height:1.75}}
  header{{background:linear-gradient(135deg,#f6f8fa,#ffffff);border-bottom:1px solid #d0d7de;padding:26px 32px;text-align:center}}
  .header-title{{font-size:1.9rem;font-weight:700;background:linear-gradient(90deg,#0969da,#7cf2c8);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;margin-bottom:6px}}
  .header-meta{{font-size:1rem;color:#57606a}}
  main{{max-width:1200px;margin:0 auto;padding:32px 24px}}
  .nav-bar{{display:flex;flex-wrap:wrap;gap:10px;justify-content:center;max-width:1000px;margin:0 auto 28px}}
  .nav-btn{{display:inline-flex;align-items:center;justify-content:center;gap:8px;padding:11px 20px;background:#f6f8fa;border:1px solid #d0d7de;border-radius:10px;color:#57606a;text-decoration:none;font-size:.95rem;font-weight:600;transition:all .2s;min-width:170px}}
  .nav-btn:hover{{border-color:#0969da;color:#0969da}}
  .nav-btn.current{{background:#0969da;border-color:#0969da;color:#fff}}
  .summary{{background:linear-gradient(135deg,#fff8c5,#ffffff);border:1px solid #9a6700;border-radius:14px;padding:22px 26px;margin-bottom:28px}}
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
  .comment{{font-size:.93rem;color:#424a53;margin-top:10px;line-height:1.7}}
  .beginner{{margin-top:12px;background:#ddf4ff;border:1px solid #54aeff;border-radius:8px;padding:12px 14px;font-size:.86rem;color:#1f6feb;line-height:1.75}}
  .beginner::before{{content:"🔰 初心者メモ　";font-weight:700;color:#0969da}}
  .formula{{font-family:'Consolas',monospace;background:#f6f8fa;border:1px solid #d0d7de;border-radius:6px;padding:6px 10px;font-size:.82rem;color:#218bff;margin:8px 0;display:inline-block}}
  footer{{background:#f6f8fa;border-top:1px solid #d0d7de;padding:24px 32px;text-align:center;font-size:.9rem;color:#57606a;line-height:1.85}}
  footer a{{color:#0969da;text-decoration:none}}
  @media(max-width:600px){{.big-num{{font-size:2.1rem}}.header-title{{font-size:1.4rem}}.nav-bar{{display:grid;grid-template-columns:1fr 1fr;gap:8px}}.nav-btn{{min-width:0;width:100%;padding:10px 8px;font-size:.82rem}}}}
</style>
  <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-2552122294306014" crossorigin="anonymous"></script>
  <!-- A8.net広告タグはここに貼る予定 -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;600;700&display=swap" rel="stylesheet">
</head>
<body>
<div id="reading-progress"></div>
<button id="theme-toggle" onclick="toggleTheme()" aria-label="テーマ切替" style="position:fixed;top:16px;right:16px;width:42px;height:42px;border-radius:50%;border:1px solid #d0d7de;background:#fff;cursor:pointer;z-index:9999;box-shadow:0 2px 8px rgba(0,0,0,.1);font-size:18px;display:flex;align-items:center;justify-content:center">🌙</button>
{brand_header("🩺", "市場健康度ダッシュボード", date_str, "投資家心理・バリュエーション・ボラティリティを総合診断")}
<main>
  <nav class="nav-bar">
    <a class="nav-btn" href="index.html">🏠 トップページ</a>
    <a class="nav-btn" href="political-feed.html">🚨 政治発言ライブ</a>
    <a class="nav-btn" href="track-record.html">📊 シグナル成績</a>
    <a class="nav-btn" href="calendar.html">📅 経済カレンダー</a>
    <a class="nav-btn" href="guides.html">📚 解説記事</a>
    <a class="nav-btn" href="guide-investment-books.html">📖 投資本</a>
    <a class="nav-btn current" href="market-health.html">🩺 市場健康度</a>
    <a class="nav-btn" href="hot-assets.html">🔥 出来高急増</a>
    <a class="nav-btn" href="charts.html">📈 50年チャート</a>
    <a class="nav-btn" href="youtube-summary.html">📺 YouTube要約</a>
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

{rate_section}  <section class="summary" style="background:linear-gradient(135deg,#0e1d2f,#0a1420);border-color:#0969da">
    <h2 style="color:#58a6ff">📋 投資判断のヒント</h2>
    <p style="color:#cdd9e5">
      <b style="color:#79c0ff">短期（〜3ヶ月）</b>: VIX・騰落レシオの極端な値（VIX 30超 or 騰落120超/70未満）は転換点シグナル。<br>
      <b style="color:#79c0ff">中期（3〜12ヶ月）</b>: バフェット指数・CAPEが歴史的高水準なら <b style="color:#e6edf3">新規資金一括投入は避け、段階投資＋分散</b> が鉄則。<br>
      <b style="color:#79c0ff">長期（1年以上）</b>: 日本株・新興国・金・債券などへの分散で米国一極集中リスクを下げる戦略が有効。
    </p>
  </section>

  <div style="background:#f6f8fa;border:1px solid #d0d7de;border-radius:12px;padding:24px 28px;margin-top:24px">
    <h2 style="font-size:1.2rem;color:#1f6feb;margin:0 0 12px;border-bottom:1px solid #d0d7de;padding-bottom:8px">📘 市場健康度の読み方</h2>
    <p style="font-size:.95rem;color:#424a53;line-height:1.85;margin-bottom:12px">このダッシュボードは、性質の異なる複数の“体温計”を1画面に集めたものです。大きく分けて、<strong>市場心理</strong>を測る指標（VIX恐怖指数・恐怖と強欲指数）、<strong>過熱/売られすぎ</strong>を測る指標（騰落レシオ）、そして<strong>割高/割安（バリュエーション）</strong>を測る指標（バフェット指数・CAPEレシオ・PER）です。性格が違うものを並べることで、相場全体の“温度感”を多面的に把握できます。</p>
    <p style="font-size:.95rem;color:#424a53;line-height:1.85;margin-bottom:12px">読み方のコツは、<strong>1つの指標だけで判断しないこと</strong>。複数の指標が<strong>同じ方向（過熱、または悲観）を同時に指したときほど、シグナルの信頼度が高い</strong>とされます。たとえば「VIXが急騰（恐怖）＋騰落レシオが70未満（売られすぎ）」が重なれば、行き過ぎた悲観＝逆張りを検討する材料に。逆に「バフェット指数もCAPEも歴史的高水準（割高）＋恐怖と強欲が極度の強欲」なら、新規の一括投資は控えめに、という具合です。</p>
    <ul style="margin:6px 0 14px 22px;color:#424a53;font-size:.94rem;line-height:1.85">
      <li><strong>短期の温度</strong>はVIX・騰落レシオで（数日〜数週間の振れ）。</li>
      <li><strong>中長期の割高/割安</strong>はバフェット指数・CAPE・PERで（数ヶ月〜数年の目安）。</li>
      <li>あくまで“環境認識”の道具であり、個別の売買タイミングは価格そのもののテクニカルと資金管理で。</li>
    </ul>
    <p style="font-size:.9rem;color:#57606a;margin-bottom:8px">▶ あわせて読む：<a href="guide-vix.html" style="color:#0969da">VIX恐怖指数</a> ／ <a href="guide-buffett-indicator.html" style="color:#0969da">バフェット指数</a> ／ <a href="guide-fear-greed.html" style="color:#0969da">恐怖と強欲指数</a></p>
    <p style="font-size:.8rem;color:#6e7781;margin:0">※ 一部の指標は月次の手動更新値を含みます。本ページは情報提供・一般的な解説であり、特定銘柄の売買推奨や投資助言ではありません。投資判断はご自身の責任で行ってください。</p>
  </div>

</main>
<footer>
  <p>🩺 市場健康度ダッシュボード ─ 日本人投資家のための総合診断ツール</p>
  <p style="margin-top:6px">データ出典: Yahoo Finance (VIX・騰落) ／ CNN ／ alternative.me ／ currentmarketvaluation.com ／ Shiller PE (multpl.com) ／ JPX 等</p>
  <p style="margin-top:6px">※ 本ページはAIによる自動集計・要約であり、投資判断はご自身の責任でお願いいたします。</p>
  <p style="margin-top:6px">
    <a href="index.html">🏠 トップページ</a> ｜
    <a href="calendar.html">📅 経済カレンダー</a> ｜
    <a href="charts.html">📈 50年チャート</a> ｜
    <a href="vix.html">😱 VIX恐怖指数</a>
  </p>
  <p style="margin-top:8px"><a href="about.html">運営者情報</a> &nbsp;|&nbsp; <a href="privacy.html">プライバシーポリシー</a> &nbsp;|&nbsp; <a href="contact.html">お問い合わせ</a></p>
<p data-disclaimer="kinsho-v1" style="margin-top:10px;padding-top:10px;border-top:1px dashed #d0d7de;font-size:.78rem;color:#6e7781;line-height:1.6">⚠️ <b>当サイトは金融商品取引業者ではなく、投資助言・代理業の登録もしていません。</b> 本サイトの情報は投資助言ではなく、投資判断はご自身の責任で行ってください。</p>
</footer>
<script>(function(){{var hasExplicit=false;try{{var ss=document.styleSheets;for(var i=0;i<ss.length;i++){{try{{var r=ss[i].cssRules||ss[i].rules;if(!r)continue;for(var j=0;j<r.length;j++){{if(r[j].selectorText&&/body\.dark[^-]/.test(r[j].selectorText+' ')){{hasExplicit=true;break}}}}}}catch(e){{}}if(hasExplicit)break}}}}catch(e){{}}if(!hasExplicit){{var s=document.createElement('style');s.textContent='body.dark{{background:#0d1117!important;color:#e6edf3!important}}body.dark header,body.dark footer,body.dark nav.nav-bar{{background:#161b22!important;color:#e6edf3!important;border-color:#30363d!important}}body.dark .nav-btn{{background:#161b22!important;border-color:#30363d!important;color:#8b949e!important}}body.dark .nav-btn:hover{{border-color:#58a6ff!important;color:#58a6ff!important}}body.dark .nav-btn.current{{background:#1f6feb!important;border-color:#58a6ff!important;color:#fff!important}}body.dark .header-title,body.dark .header-meta,body.dark .header-meta span{{color:#e6edf3!important}}body.dark a{{color:#79c0ff!important}}body.dark h1,body.dark h2,body.dark h3,body.dark h4{{color:#e6edf3!important}}body.dark p,body.dark li,body.dark td{{color:#c9d1d9!important}}body.dark hr{{border-color:#30363d!important}}body.dark th{{background:#0d1117!important;color:#79c0ff!important}}body.dark #theme-toggle{{background:#161b22!important;border-color:#30363d!important;color:#fff!important}}body.dark *[style*="background:#fff"]:not(img),body.dark *[style*="background:#ffffff"]:not(img),body.dark *[style*="background-color:#fff"]:not(img),body.dark *[style*="background-color:#ffffff"]:not(img),body.dark *[style*="background:#f6f8fa"]:not(img),body.dark *[style*="background-color:#f6f8fa"]:not(img){{background:#161b22!important}}body.dark *[style*="border:1px solid #d0d7de"],body.dark *[style*="border-color:#d0d7de"]{{border-color:#30363d!important}}body.dark *[style*="color:#1f2328"],body.dark *[style*="color:#57606a"],body.dark *[style*="color:#6e7781"],body.dark *[style*="color:#424a53"]{{color:#e6edf3!important}}';document.head.appendChild(s)}}function setTheme(t){{document.body.classList.toggle('dark',t==='dark');var b=document.getElementById('theme-toggle');if(b)b.textContent=t==='dark'?'☀️':'🌙';try{{localStorage.setItem('theme',t)}}catch(e){{}}}}window.toggleTheme=function(){{setTheme(document.body.classList.contains('dark')?'light':'dark')}};var t='light';try{{t=localStorage.getItem('theme')||'light'}}catch(e){{}}setTheme(t);}})();</script>
<script src="site-search.js" defer></script>
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
    # 0.4) 無料メルマガ登録フォームを全 .html の <footer> 直前に一括注入（冪等）
    if path.endswith(".html") and "mw-newsletter" not in content and "<footer" in content:
        content = content.replace("<footer", NEWSLETTER_FORM + "<footer", 1)
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
    body{{font-family:'Noto Sans JP','Segoe UI','Hiragino Sans','Yu Gothic',sans-serif;background:#ffffff;color:#1f2328;min-height:100vh}}
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
  .nav-bar{{display:flex;flex-wrap:wrap;gap:10px;justify-content:center;max-width:1000px;margin:0 auto 28px}}
  .nav-btn{{display:inline-flex;align-items:center;justify-content:center;gap:8px;padding:11px 20px;background:#f6f8fa;border:1px solid #d0d7de;border-radius:10px;color:#57606a;text-decoration:none;font-size:.95rem;font-weight:600;transition:all .2s;min-width:170px}}
  .nav-btn:hover{{border-color:#0969da;color:#0969da}}
  .nav-btn.current{{background:#0969da;border-color:#0969da;color:#fff}}
    @media(max-width:600px){{.header-inner{{flex-direction:column}}.chart-wrap{{height:240px}}.nav-bar{{display:grid;grid-template-columns:1fr 1fr;gap:8px}}.nav-btn{{min-width:0;width:100%;padding:10px 8px;font-size:.82rem}}}}
  </style>
  <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-2552122294306014" crossorigin="anonymous"></script>
  <!-- A8.net広告タグはここに貼る予定 -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;600;700&display=swap" rel="stylesheet">
</head>
<body>
<div id="reading-progress"></div>
<button id="theme-toggle" onclick="toggleTheme()" aria-label="テーマ切替" style="position:fixed;top:16px;right:16px;width:42px;height:42px;border-radius:50%;border:1px solid #d0d7de;background:#fff;cursor:pointer;z-index:9999;box-shadow:0 2px 8px rgba(0,0,0,.1);font-size:18px;display:flex;align-items:center;justify-content:center">🌙</button>
{brand_header("📈", "50年価格チャート", time_str)}
<main>

<nav class="nav-bar">
  <a class="nav-btn" href="index.html">🏠 トップページ</a>
  <a class="nav-btn" href="political-feed.html">🚨 政治発言ライブ</a>
  <a class="nav-btn" href="track-record.html">📊 シグナル成績</a>
  <a class="nav-btn" href="calendar.html">📅 経済カレンダー</a>
  <a class="nav-btn" href="guides.html">📚 解説記事</a>
  <a class="nav-btn" href="guide-investment-books.html">📖 投資本</a>
  <a class="nav-btn" href="market-health.html">🩺 市場健康度</a>
  <a class="nav-btn" href="hot-assets.html">🔥 出来高急増</a>
  <a class="nav-btn current" href="charts.html">📈 50年チャート</a>
  <a class="nav-btn" href="youtube-summary.html">📺 YouTube要約</a>
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

  <div style="background:#f6f8fa;border:1px solid #d0d7de;border-radius:12px;padding:24px 28px;margin-top:24px">
    <h2 style="font-size:1.2rem;color:#1f6feb;margin:0 0 12px;border-bottom:1px solid #d0d7de;padding-bottom:8px">📘 50年チャートの活かし方</h2>
    <p style="font-size:.95rem;color:#424a53;line-height:1.85;margin-bottom:12px">日々のニュースを追っていると、目先の上げ下げに心が振り回されがちです。このページの<strong>数十年スケールの長期チャート</strong>は、いま起きている値動きを<strong>“歴史の文脈”の中で見る</strong>ための地図です。長い目で見れば、株価はオイルショック・ブラックマンデー・ITバブル崩壊・リーマンショック・コロナショックといった<strong>暴落を何度もはさみながら、それでも長期では上昇</strong>してきました。下の年表は、その節目となった出来事をまとめたものです。</p>
    <p style="font-size:.95rem;color:#424a53;line-height:1.85;margin-bottom:12px">このページの一番の使いどころは、<strong>暴落の渦中で冷静さを保つ</strong>ことです。渦中では「もう終わりだ」と感じても、後から長期チャートで振り返ると、多くの危機は<strong>一時的な急落</strong>として刻まれています。ただし——<strong>「いつか戻る」と“どこが底か”は別問題</strong>。回復まで何年もかかった局面もあり、底は誰にも当てられません。だからこそ、長期では強気でも、<strong>一度に動かず分割で・損切りラインを決めて</strong>臨むのが現実的です。</p>
    <ul style="margin:6px 0 14px 22px;color:#424a53;font-size:.94rem;line-height:1.85">
      <li><strong>長期投資の視点</strong>：短期の急落を“割安に買えるバーゲン”と捉えられるかは、長期チャートで歴史を知っているかどうかで変わります。</li>
      <li><strong>過信は禁物</strong>：「過去がこうだったから未来もこうなる」とは限りません。歴史はパターンの参考であって、保証ではありません。</li>
    </ul>
    <p style="font-size:.9rem;color:#57606a;margin-bottom:8px">▶ あわせて読む：<a href="market-health.html" style="color:#0969da">市場健康度（割高/割安の温度）</a> ／ <a href="guide-loss-cut.html" style="color:#0969da">暴落で動揺しない損切りの技術</a> ／ <a href="guide-position-sizing.html" style="color:#0969da">分割で買う資金管理</a></p>
    <p style="font-size:.8rem;color:#6e7781;margin:0">※ 本ページは過去データの表示と一般的な解説であり、将来の値動きや特定銘柄の売買を示唆するものではありません。投資判断はご自身の責任で行ってください。</p>
  </div>

</main>
<footer>
  <p>データソース: Yahoo Finance (yfinance) &nbsp;|&nbsp;
  <a href="index.html">🏠 トップページ</a> &nbsp;|&nbsp;
  <a href="calendar.html">📅 経済カレンダー</a> &nbsp;|&nbsp;
  <a href="charts.html">📈 50年チャート</a> &nbsp;|&nbsp;
  <a href="vix.html">😱 VIX</a> &nbsp;|&nbsp;
  <a href="market-health.html">🩺 市場健康度</a> &nbsp;|&nbsp;
  <a href="hot-assets.html">🔥 出来高急増</a> &nbsp;|&nbsp;
  本データは自動取得・表示であり、投資助言ではありません。</p>
  <p style="margin-top:8px"><a href="about.html">運営者情報</a> &nbsp;|&nbsp; <a href="privacy.html">プライバシーポリシー</a> &nbsp;|&nbsp; <a href="contact.html">お問い合わせ</a></p>
<p data-disclaimer="kinsho-v1" style="margin-top:10px;padding-top:10px;border-top:1px dashed #d0d7de;font-size:.78rem;color:#6e7781;line-height:1.6">⚠️ <b>当サイトは金融商品取引業者ではなく、投資助言・代理業の登録もしていません。</b> 本サイトの情報は投資助言ではなく、投資判断はご自身の責任で行ってください。</p>
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
<script>(function(){{var hasExplicit=false;try{{var ss=document.styleSheets;for(var i=0;i<ss.length;i++){{try{{var r=ss[i].cssRules||ss[i].rules;if(!r)continue;for(var j=0;j<r.length;j++){{if(r[j].selectorText&&/body\.dark[^-]/.test(r[j].selectorText+' ')){{hasExplicit=true;break}}}}}}catch(e){{}}if(hasExplicit)break}}}}catch(e){{}}if(!hasExplicit){{var s=document.createElement('style');s.textContent='body.dark{{background:#0d1117!important;color:#e6edf3!important}}body.dark header,body.dark footer,body.dark nav.nav-bar{{background:#161b22!important;color:#e6edf3!important;border-color:#30363d!important}}body.dark .nav-btn{{background:#161b22!important;border-color:#30363d!important;color:#8b949e!important}}body.dark .nav-btn:hover{{border-color:#58a6ff!important;color:#58a6ff!important}}body.dark .nav-btn.current{{background:#1f6feb!important;border-color:#58a6ff!important;color:#fff!important}}body.dark .header-title,body.dark .header-meta,body.dark .header-meta span{{color:#e6edf3!important}}body.dark a{{color:#79c0ff!important}}body.dark h1,body.dark h2,body.dark h3,body.dark h4{{color:#e6edf3!important}}body.dark p,body.dark li,body.dark td{{color:#c9d1d9!important}}body.dark hr{{border-color:#30363d!important}}body.dark th{{background:#0d1117!important;color:#79c0ff!important}}body.dark #theme-toggle{{background:#161b22!important;border-color:#30363d!important;color:#fff!important}}body.dark *[style*="background:#fff"]:not(img),body.dark *[style*="background:#ffffff"]:not(img),body.dark *[style*="background-color:#fff"]:not(img),body.dark *[style*="background-color:#ffffff"]:not(img),body.dark *[style*="background:#f6f8fa"]:not(img),body.dark *[style*="background-color:#f6f8fa"]:not(img){{background:#161b22!important}}body.dark *[style*="border:1px solid #d0d7de"],body.dark *[style*="border-color:#d0d7de"]{{border-color:#30363d!important}}body.dark *[style*="color:#1f2328"],body.dark *[style*="color:#57606a"],body.dark *[style*="color:#6e7781"],body.dark *[style*="color:#424a53"]{{color:#e6edf3!important}}';document.head.appendChild(s)}}function setTheme(t){{document.body.classList.toggle('dark',t==='dark');var b=document.getElementById('theme-toggle');if(b)b.textContent=t==='dark'?'☀️':'🌙';try{{localStorage.setItem('theme',t)}}catch(e){{}}}}window.toggleTheme=function(){{setTheme(document.body.classList.contains('dark')?'light':'dark')}};var t='light';try{{t=localStorage.getItem('theme')||'light'}}catch(e){{}}setTheme(t);}})();</script>
<script src="site-search.js" defer></script>
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


# ─────────────────────────────────────────
# 🆕 2026-05-29 信頼性検証済みニュース（fundamental-context.json 由来）
# 多サブエージェント・ブリーフィングが生成した、ソース格付け・クロス照合済みニュースを表示。
# ⚠️ 方向観(bias/conviction/direction)・risk_regime は公開しない（無登録投資助言リスク回避）。
#    公開するのは「事実・出典・ソース信頼性」のみ。
# ─────────────────────────────────────────
_TIER_LABELS = {1: "🏛️ 一次情報", 2: "📰 通信社・専門", 3: "📺 一般大手", 4: "💬 その他"}


def load_fundamental_context_for_site():
    """表示用に fundamental-context.json を読み込む。不在/壊れは None。"""
    try:
        sd = os.path.dirname(os.path.abspath(__file__))
    except Exception:
        sd = "."
    try:
        with open(os.path.join(sd, "fundamental-context.json"), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


# 🆕 関連ニュース／検証済みニュースの鮮度カットオフ（古い記事の混入防止・2026-06-30）。
# TOP3 は別途 48h 減衰で制御。ブリーフィング(fundamental-context.json)由来はここで一括カット＝唯一の調整点。
BRIEFING_NEWS_MAX_AGE_DAYS = 10


def _briefing_news_too_old(n):
    """published(YYYY-MM-DD)が MAX_AGE 日より古ければ True。日付不明(空/解析不可)は除外しない（False）。"""
    pub = (n.get("published") or "").strip()
    if not pub:
        return False
    try:
        d = datetime.fromisoformat(pub[:10]).date()
    except Exception:
        return False
    return (datetime.now(JST).date() - d).days > BRIEFING_NEWS_MAX_AGE_DAYS


def build_trust_news_html(ctx, max_items=10):
    """信頼性検証済みニュースのセクションHTML。
    ⚠️ bias / conviction / direction / risk_regime は一切読まない・出さない（投資助言回避）。
    不在・該当なしなら空文字（セクション自体を出さない＝安全フォールバック）。"""
    if not ctx:
        return ""
    seen_url, seen_head, items = set(), set(), []
    for a in ctx.get("assets", []):
        for n in (a.get("top_news") or []):
            cred = (n.get("credibility") or "").upper()
            if cred not in ("HIGH", "MID"):  # LOW・未検証は公開しない
                continue
            if _briefing_news_too_old(n):  # 🆕 鮮度カットオフ（古い記事の混入防止）
                continue
            # 資産間の重複除去: まず URL（同一記事）、無ければ見出し先頭で判定
            url = (n.get("url") or "").strip()
            hkey = (n.get("headline") or "").strip()[:24]
            if url and url in seen_url:
                continue
            if hkey and hkey in seen_head:
                continue
            if not url and not hkey:
                continue
            if url:
                seen_url.add(url)
            if hkey:
                seen_head.add(hkey)
            items.append(n)
    if not items:
        return ""
    cred_rank = {"HIGH": 0, "MID": 1}
    mat_rank = {"high": 0, "mid": 1, "low": 2}
    # 二段ソート（安定ソート利用）: まず信頼度×重要度、次に published 日付の新しい順。
    # 日付(published, "YYYY-MM-DD")が無い項目は "0000-00-00" 扱いで末尾へ（除外はしない）。
    items.sort(key=lambda n: (cred_rank.get((n.get("credibility") or "").upper(), 9),
                              mat_rank.get((n.get("materiality") or "").lower(), 9)))
    items.sort(key=lambda n: (n.get("published") or "0000-00-00"), reverse=True)
    items = items[:max_items]

    rows = []
    for n in items:
        cred = (n.get("credibility") or "").upper()
        cred_color = "#1a7f37" if cred == "HIGH" else "#9a6700"
        cred_label = "ソース信頼度 高" if cred == "HIGH" else "ソース信頼度 中"
        tier = _TIER_LABELS.get(n.get("tier"), "")
        corro = n.get("corroborated_by") or []
        corro_html = (f'<span style="color:#57606a">🔗 裏取り: {html.escape(" / ".join(str(c) for c in corro[:3]))}</span>'
                      if corro else "")
        mat = (n.get("materiality") or "").lower()
        mat_html = ('<span style="display:inline-block;padding:1px 8px;border-radius:10px;background:#fff1f0;color:#cf222e;font-size:.68rem;font-weight:600">重要度 高</span>'
                    if mat == "high" else "")
        pub = (n.get("published") or "").strip()
        pub_html = (f'<span style="display:inline-block;padding:1px 8px;border-radius:10px;background:#eaf2ff;color:#0969da;font-weight:600">🗓 {html.escape(pub)}</span>'
                    if pub else "")
        headline = html.escape(n.get("headline") or "")
        src = html.escape(n.get("source") or "")
        url = n.get("url") or ""
        link = (f'<a href="{html.escape(url)}" target="_blank" rel="noopener nofollow" style="color:#0969da;font-size:.72rem;white-space:nowrap">出典 →</a>'
                if isinstance(url, str) and url.startswith("http") else "")
        rows.append(f"""    <div style="padding:12px 0;border-bottom:1px solid #eaeef2">
      <div style="font-size:.93rem;font-weight:600;color:#1f2328;line-height:1.5;margin-bottom:6px">{headline}</div>
      <div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;font-size:.72rem">
        {pub_html}
        <span style="display:inline-block;padding:1px 8px;border-radius:10px;background:#eff3f6;color:#424a53;font-weight:600">{tier}</span>
        <span style="display:inline-block;padding:1px 8px;border-radius:10px;background:#eaf6ee;color:{cred_color};font-weight:700">✔ {cred_label}</span>
        {mat_html}
        <span style="color:#57606a">{src}</span>
        {link}
      </div>
      <div style="font-size:.72rem;margin-top:4px">{corro_html}</div>
    </div>""")

    gen = str(ctx.get("generated_at", ""))[:16].replace("T", " ")
    body = "\n".join(rows)
    return f"""
  <!-- 信頼性検証済みニュース（fundamental-context.json 由来、方向観は非公開）-->
  <div style="margin:32px 0;padding:22px;background:#ffffff;border:1px solid #d0d7de;border-radius:12px">
    <div style="font-size:1.15rem;font-weight:700;color:#1f2328;margin-bottom:4px">🔍 信頼性検証済みニュース <span style="font-size:.68rem;color:#57606a;font-weight:500">（複数の信頼できる情報源でクロス照合・ソース格付け済み）</span></div>
    <div style="font-size:.78rem;color:#6e7781;margin-bottom:8px">一次情報（中央銀行・政府統計など）や大手通信社を中心に、信頼性を検証したニュースを新しい順に掲載。{gen} 更新。</div>
{body}
    <p data-disclaimer="kinsho-v1" style="margin-top:14px;padding-top:10px;border-top:1px dashed #d0d7de;font-size:.75rem;color:#6e7781;line-height:1.6">⚠️ 掲載ニュースは事実の整理と出典提示を目的としており、投資助言ではありません。ソース格付け・信頼度は当サイトの編集上の評価です。投資判断はご自身の責任で行ってください。</p>
  </div>
"""


# 🆕 各マーケットカードに、信頼性検証済みブリーフィングのニュースを割り当てるマップ
_CARD_TICKERS = {
    "stocks":    {"NKD=F", "ES=F", "NQ=F"},
    "fx":        {"USDJPY", "EURUSD", "USDJPY=X", "EURUSD=X"},
    "commodity": {"GC=F", "CL=F"},
    "crypto":    {"BTC-USD"},
}


def build_card_news_from_briefing(ctx, cat, limit=3):
    """指定カテゴリ（stocks/fx/commodity/crypto）の信頼性検証済みニュースをカード用HTMLで返す。
    ⚠️ bias / direction 等は出さない（事実・出典・日付・信頼度のみ）。
    ctx不在 or 該当ニュース無しなら None（呼び出し側で旧パイプラインにフォールバック）。"""
    if not ctx:
        return None
    want = _CARD_TICKERS.get(cat, set())
    seen, items = set(), []
    for a in ctx.get("assets", []):
        if (a.get("ticker") or "") not in want:
            continue
        for n in (a.get("top_news") or []):
            cred = (n.get("credibility") or "").upper()
            if cred not in ("HIGH", "MID"):
                continue
            if _briefing_news_too_old(n):  # 🆕 鮮度カットオフ（古い記事の混入防止）
                continue
            key = (n.get("headline") or "").strip()[:24]
            if not key or key in seen:
                continue
            seen.add(key)
            items.append(n)
    if not items:
        return None
    cred_rank = {"HIGH": 0, "MID": 1}
    mat_rank = {"high": 0, "mid": 1, "low": 2}
    items.sort(key=lambda n: (cred_rank.get((n.get("credibility") or "").upper(), 9),
                              mat_rank.get((n.get("materiality") or "").lower(), 9)))
    items.sort(key=lambda n: (n.get("published") or "0000-00-00"), reverse=True)
    out = ""
    for n in items[:limit]:
        cred = (n.get("credibility") or "").upper()
        cred_label = "ソース信頼度 高" if cred == "HIGH" else "ソース信頼度 中"
        cred_color = "#1a7f37" if cred == "HIGH" else "#9a6700"
        headline = html.escape(n.get("headline") or "")
        src = html.escape(n.get("source") or "")
        pub = html.escape((n.get("published") or "").strip())
        url = n.get("url") or "#"
        url = url if (isinstance(url, str) and url.startswith("http")) else "#"
        comment = html.escape((n.get("comment") or "").strip())
        ai_html = f'<span class="news-ai">💡 {comment}</span>' if comment else ""
        meta = " · ".join([x for x in [src, pub] if x])
        out += f'''<a class="news-item" href="{html.escape(url)}" target="_blank" rel="noopener nofollow">
          <span class="news-title">✔ {headline}</span>
          {ai_html}
          <span class="news-meta">{meta} · <span style="color:{cred_color};font-weight:600">{cred_label}</span></span>
        </a>'''
    return out


def _find_latest_weekly_article():
    """リポジトリ直下から最新の guide-weekly-YYYY-MM-DD.html を探し (filename, date) を返す。
    見つからなければ (None, None)。週次「振り返り」(guide-weekly-review-*) は別物なので除外。"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    latest_date = None
    latest_file = None
    for name in os.listdir(script_dir):
        if not (name.startswith("guide-weekly-") and name.endswith(".html")):
            continue
        if name.startswith("guide-weekly-review-"):
            continue
        ds = name[len("guide-weekly-"):-len(".html")]
        try:
            d = datetime.strptime(ds, "%Y-%m-%d").date()
        except ValueError:
            continue
        if latest_date is None or d > latest_date:
            latest_date, latest_file = d, name
    return latest_file, latest_date


def _weekly_range_label(week_start):
    """週開始(月)の date から「6/1〜6/5」形式の範囲ラベルを返す。"""
    wk_end = week_start + timedelta(days=4)
    if os.name == "nt":
        return f"{week_start.strftime('%#m/%#d')}〜{wk_end.strftime('%#m/%#d')}"
    return f"{week_start.strftime('%-m/%-d')}〜{wk_end.strftime('%-m/%-d')}"


def build_weekly_strategy_banner(now_jst):
    """最新の週次戦略記事への導線バナー HTML を返す。記事が無ければ空文字。
    index.html は完全自動生成（SYNC 禁忌＝ローカルから push しない）なので、手動 sync と競合せず
    毎週自動でリンクが張り替わる（guides.html をサーバ側で自動編集すると巻き戻し事故になるため、
    導線はこちらの自動生成ページに置く）。"""
    try:
        latest_file, latest_date = _find_latest_weekly_article()
        if not latest_file:
            return ""
        rng = _weekly_range_label(latest_date)
        return f'''  <!-- 今週の投資戦略（最新の guide-weekly へ自動リンク。手動編集不要）-->
  <a href="{latest_file}" style="display:block;text-decoration:none;background:linear-gradient(135deg,#0969da,#1f6feb);color:#fff;border-radius:10px;padding:16px 22px;margin-bottom:32px">
    <div style="font-size:.72rem;letter-spacing:.1em;opacity:.92;margin-bottom:4px">📅 今週の投資戦略（{rng}）</div>
    <div style="font-size:1.02rem;font-weight:700;line-height:1.5">注目指標と3シナリオ別マーケット展望を読む →</div>
  </a>'''
    except Exception as e:
        print(f"  ⚠️ weekly strategy banner 生成スキップ: {e}")
        return ""


def _load_indicator_result(now_jst):
    """routine が WebSearch で生成・コミットする indicator-result.json（当日発表分の結果速報）を読む。
    当日イベントの verified 済み結果のみ採用。無ければ None（＝発表前 or 未生成）。"""
    try:
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "indicator-result.json")
        if not os.path.exists(p):
            return None
        with open(p, encoding="utf-8") as f:
            r = json.load(f)
        ed = r.get("event_date")
        if not (r.get("verified") and ed):
            return None
        # 結果速報は「発表当日＋翌日まで」表示（翌朝の再生成でも昨日の結果を拾えるように）。
        # それ以降は古い結果として無視し、自動でプレビュー（次の指標）へ戻る。
        edate = datetime.strptime(ed, "%Y-%m-%d").date()
        delta = (now_jst.date() - edate).days
        return r if 0 <= delta <= 1 else None
    except Exception:
        return None


def _load_indicator_results(now_jst):
    """複数の結果速報に対応。verified かつ発表当日〜3日後のものを新しい順で返す（リスト）。
    中銀ウィーク（FOMC＋日銀が数日に渡る）でも両方を並べて残せるよう表示窓は4日。
    indicator-result.json は {"results":[...]} / 旧来の単一オブジェクト / リスト のいずれでも可。"""
    try:
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "indicator-result.json")
        if not os.path.exists(p):
            return []
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get("results"), list):
            items = data["results"]
        elif isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = [data]
        else:
            items = []
        out = []
        for r in items:
            if not isinstance(r, dict):
                continue
            ed = r.get("event_date")
            if not (r.get("verified") and ed):
                continue
            try:
                edate = datetime.strptime(ed, "%Y-%m-%d").date()
            except Exception:
                continue
            if 0 <= (now_jst.date() - edate).days <= 3:
                out.append((edate, r))
        out.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in out]
    except Exception:
        return []


def build_indicator_preview_banner(now_jst):
    """発表前＝プレビュー、発表後（routineが結果JSONを書いたら）＝結果速報、に自動で刷り替わる
    トップの注目指標バナー HTML を返す。📰更新履歴とは別枠。対象が無ければ空文字（自動で消える）。
    index は完全自動生成（SYNC禁忌）なので毎回張り替わる。"""
    try:
        flag = {"jp": "🇯🇵", "us": "🇺🇸", "eu": "🇪🇺", "cn": "🇨🇳"}
        # ── ① 発表後：当日の結果速報があれば「結果」バナーへ刷り替え ──
        _results = _load_indicator_results(now_jst)
        if _results:
            if len(_results) == 1:
                _r0 = _results[0]
                _fl = flag.get(_r0.get("country", "us"), "")
                _nm = _r0.get("name", "経済指標")
                _hd = _r0.get("headline", "結果が出ました")
                _inner = f"✅ {_fl} {_nm}：{_hd} — 結果と市場反応を見る →"
            else:
                _labels = " ＋ ".join(flag.get(_r.get("country", "us"), "") + " " + _r.get("name", "指標") for _r in _results[:3])
                _inner = f"✅ {_labels} の結果速報（{len(_results)}件）— 各結果と市場反応を見る →"
            return f'''  <!-- 結果速報バナー（発表後・routine が WebSearch で生成した indicator-result.json 由来。複数指標対応。preview.html へ）-->
  <a href="preview.html" style="display:block;text-decoration:none;background:linear-gradient(135deg,#1a7f37,#0969da);color:#fff;border-radius:10px;padding:16px 22px;margin-bottom:32px">
    <div style="font-size:.72rem;letter-spacing:.1em;opacity:.92;margin-bottom:4px">📊 経済指標の結果速報</div>
    <div style="font-size:1.02rem;font-weight:700;line-height:1.5">{_inner}</div>
  </a>'''
        # ── ② 発表前：3日以内（当日含む）の high 重要度指標プレビュー ──
        ups = find_upcoming_events(now_jst, days_ahead=3)
        highs = [e for e in ups if e.get("importance") == "high"]
        if not highs:
            return ""

        def _lbl(d):
            delta = (d - now_jst.date()).days
            return "本日" if delta == 0 else ("明日" if delta == 1 else ("明後日" if delta == 2 else f"{delta}日後"))

        e0 = highs[0]
        delta0 = (e0["date"] - now_jst.date()).days
        emoji = "🚨" if delta0 <= 1 else ("⏰" if delta0 == 2 else "📅")
        when0 = _lbl(e0["date"])
        date0 = f"{e0['date'].month}/{e0['date'].day}"
        more = f"　ほか{len(highs) - 1}件" if len(highs) > 1 else ""
        return f'''  <!-- 注目の経済指標バナー（発表3日前〜当日まで常時表示・📰更新履歴とは別枠。preview.html へ自動リンク）-->
  <a href="preview.html" style="display:block;text-decoration:none;background:linear-gradient(135deg,#cf222e,#bc4c00);color:#fff;border-radius:10px;padding:16px 22px;margin-bottom:32px">
    <div style="font-size:.72rem;letter-spacing:.1em;opacity:.92;margin-bottom:4px">📅 注目の経済指標プレビュー</div>
    <div style="font-size:1.02rem;font-weight:700;line-height:1.5">{emoji} <span style="background:rgba(255,255,255,.22);border-radius:6px;padding:1px 8px">{when0}</span> {flag.get(e0["country"], "")} {e0["name"]}（{date0}）{more} — 結果別シナリオを見る →</div>
  </a>'''
    except Exception as e:
        print(f"  ⚠️ indicator preview banner 生成スキップ: {e}")
        return ""


def build_morning_digest_banner(now_jst, data, sentiment_label):
    """🌅 今朝の3行ダイジェスト＋重要イベントカウントダウン（2026-06-11 新設）。
    ①直近の主な値動き（前日比の大きい順）②今日の経済イベント ③市場の温度（VIX）を
    既に取得済みのデータから毎回自動生成する。事実とデータの表示のみ（方向観・売買示唆は出さない）。
    カウントダウンは CPI/FOMC/日銀会合/雇用統計 の「次回」までの日数。失敗時は空文字（自動で消える）。"""
    try:
        flag = {"jp": "🇯🇵", "us": "🇺🇸", "eu": "🇪🇺", "cn": "🇨🇳"}
        today = now_jst.date()

        # ── ① 直近の主な値動き（前日比の絶対値が大きい順に3つ）──
        names = {"nikkei": "日経平均", "sp500": "S&P500", "usdjpy": "ドル円",
                 "eurjpy": "ユーロ円", "oil": "原油", "gold": "金",
                 "btc": "BTC", "eth": "ETH"}
        movers = []
        for k, nm in names.items():
            _, _, chg = data.get(k, (None, None, None))
            if chg is not None:
                movers.append((nm, chg))
        movers.sort(key=lambda x: abs(x[1]), reverse=True)
        if movers:
            parts = []
            for nm, chg in movers[:3]:
                cls = "md-up" if chg >= 0 else "md-down"
                arrow = "▲" if chg >= 0 else "▼"
                parts.append(f'{nm} <span class="{cls}">{arrow}{abs(chg):.1f}%</span>')
            line1 = "値動きが大きい順：" + "・".join(parts) + "（前日比）"
        else:
            line1 = "価格データを取得中です"

        # ── ② 今日の経済イベント（無ければ次の high を案内）──
        ups = find_upcoming_events(now_jst, days_ahead=7)
        todays = [e for e in ups if e["date"] == today]
        if todays:
            ev = "・".join(f'{"🚨" if e["importance"] == "high" else "📌"}{flag.get(e["country"], "")} {e["name"]}'
                           for e in todays[:3])
            more = f"　ほか{len(todays) - 3}件" if len(todays) > 3 else ""
            line2 = f"本日：{ev}{more}"
        else:
            nxt = next((e for e in ups if e["importance"] == "high"), None)
            if nxt:
                d = (nxt["date"] - today).days
                line2 = (f'本日の重要指標はなし。次は {flag.get(nxt["country"], "")} {nxt["name"]}'
                         f'（{nxt["date"].month}/{nxt["date"].day}・あと{d}日）')
            else:
                line2 = "直近1週間に主要な経済指標の予定はありません"

        # ── ③ 市場の温度（VIX＋センチメント）──
        vix_txt = ""
        try:
            vix_val, _, _ = get_price("^VIX")
            if vix_val is not None:
                if vix_val < 13:
                    lv = "きわめて落ち着いた水準"
                elif vix_val < 17:
                    lv = "落ち着いた水準"
                elif vix_val < 22:
                    lv = "やや神経質な水準"
                elif vix_val < 30:
                    lv = "警戒水準"
                else:
                    lv = "強い警戒水準"
                vix_txt = f'恐怖指数VIX <b>{vix_val:.1f}</b>（{lv}）・'
        except Exception:
            pass
        line3 = f'市場の温度：{vix_txt}センチメント判定は「<b>{sentiment_label}</b>」'

        # ── 重要イベントカウントダウン（次回の CPI / FOMC / 日銀 / 雇用統計）──
        keys = [("米CPI", "🇺🇸 米CPI"), ("FOMC（結果発表）", "🇺🇸 FOMC"),
                ("日銀会合（結果発表）", "🇯🇵 日銀会合"), ("米雇用統計", "🇺🇸 雇用統計")]
        chips = []
        for sub, lbl in keys:
            nxt_date = None
            for m, d, c, imp, n, desc in ECONOMIC_EVENTS_2026:
                if sub not in n:
                    continue
                try:
                    ed = datetime(now_jst.year, m, d).date()
                except ValueError:
                    continue
                if ed >= today and (nxt_date is None or ed < nxt_date):
                    nxt_date = ed
            if nxt_date:
                dd = (nxt_date - today).days
                when = "<b>本日</b>" if dd == 0 else (f"<b>あと{dd}日</b>" if dd <= 3 else f"あと{dd}日")
                chips.append((dd, f'<span class="md-chip">{lbl} {when}（{nxt_date.month}/{nxt_date.day}）</span>'))
        chips.sort(key=lambda x: x[0])
        chips_html = ""
        if chips:
            chips_html = ('\n    <div class="md-chips">' + "".join(c for _, c in chips)
                          + '<a href="calendar.html" class="md-chip" style="text-decoration:none">📅 カレンダー →</a></div>')

        title = "🌅 今朝の3行" if now_jst.hour < 12 else "🌇 今日の3行"
        upd = now_jst.strftime("%H:%M")
        return f'''  <!-- 今朝の3行ダイジェスト＋重要イベントカウントダウン（毎回自動生成・事実とデータのみ）-->
  <div class="morning-digest">
    <div class="md-title">{title} <span class="md-sub">忙しい人のための30秒まとめ（{upd} JST 更新）</span></div>
    <div class="md-line">📈 {line1}</div>
    <div class="md-line">📅 {line2}</div>
    <div class="md-line">🌡️ {line3}</div>{chips_html}
  </div>'''
    except Exception as e:
        print(f"  ⚠️ morning digest 生成スキップ: {e}")
        return ""


def build_weekly_history_item(now_jst):
    """📰 更新履歴 に載せる「今週の投資戦略」エントリを {date, line} で返す（日付降順ソート用）。
    最新の guide-weekly を自動検出。記事が無ければ None。line は先頭スペース・末尾<br>なし。"""
    try:
        latest_file, latest_date = _find_latest_weekly_article()
        if not latest_file:
            return None
        rng = _weekly_range_label(latest_date)
        pub = (latest_date - timedelta(days=1)).strftime("%Y-%m-%d")  # 生成された日曜＝週開始(月)の前日
        line = (f'・<b>{pub}</b>: 📅 解説「<a href="{latest_file}" style="color:#0969da">'
                f'<b>今週の投資戦略（{rng}）：注目指標と3シナリオ別マーケット展望</b></a>」公開')
        return {"date": pub, "line": line}
    except Exception as e:
        print(f"  ⚠️ weekly history item 生成スキップ: {e}")
        return None


def build_featured_guides():
    """🆕 2026-06-01 トップに『注目の解説記事』を前面表示。
    独自の厚い解説記事を目立たせ、"データ寄せ集め"感を薄める（AdSense低価値対策＋内部リンク＋UX）。"""
    items = [
        ("guide-oriental-land-2026-06.html", "🏰", "オリエンタルランド（4661）はなぜ約6割安に？", "暴落の5つの理由と「復活」3シナリオをフラットに整理"),
        ("guide-bank-stocks-2026-05.html", "🏦", "日銀利上げで銀行株はどうなる？", "メガバンク vs 地方銀行の違い・利ざや・株主還元を整理"),
        ("guide-japan-strategy-2026-05.html", "🗾", "2026年 日本株の歩き方", "攻め（AI半導体・銀行）と守り（ディフェンシブ）のセクター戦略"),
        ("guide-softbank-group-2026-05.html", "📱", "ソフトバンクグループ（9984）徹底解説", "OpenAI・Arm・Vision Fund と NAV、5つのリスクまで網羅"),
        ("guide-nvidia-2026-05.html", "🎮", "NVIDIA 決算解説", "AI相場の中心銘柄を決算からフラットに読み解く"),
        ("guide-nisa.html", "💰", "新NISA 完全ガイド", "制度の基本と、長期保有・高配当・積立の考え方"),
    ]
    cards = "\n".join(
        f'''      <a href="{f}" style="display:block;background:#ffffff;border:1px solid #d0d7de;border-radius:12px;padding:18px 22px;text-decoration:none">
        <div style="font-size:1.0rem;font-weight:700;color:#0969da;margin-bottom:6px">{e} {t}</div>
        <div style="font-size:.8rem;color:#57606a;line-height:1.6">{d}</div>
      </a>'''
        for f, e, t, d in items
    )
    return f'''  <!-- 注目の解説記事（独自コンテンツを前面に）-->
  <div style="margin-top:48px;padding-top:24px;border-top:1px solid #d0d7de">
    <div style="font-size:1.2rem;font-weight:700;color:#1f2328;margin-bottom:6px">📚 注目の解説記事</div>
    <div style="font-size:.88rem;color:#57606a;margin-bottom:20px">投資の「なぜ？」を、出典付きでわかりやすく解説（<a href="guides.html" style="color:#1f6feb;text-decoration:none">解説記事の一覧 →</a>）</div>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px">
{cards}
    </div>
  </div>
'''


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
    fc_ctx = load_fundamental_context_for_site()
    top_news_html     = build_news_html(news.get("top", []))
    # 🆕 各カードの関連ニュースを信頼性検証済みブリーフィングで置換（無ければ旧パイプラインにフォールバック）
    stocks_news_html  = build_card_news_from_briefing(fc_ctx, "stocks")    or build_news_html(news.get("stocks", []))
    fx_news_html      = build_card_news_from_briefing(fc_ctx, "fx")        or build_news_html(news.get("fx", []))
    cmd_news_html     = build_card_news_from_briefing(fc_ctx, "commodity") or build_news_html(news.get("commodity", []))
    crypto_news_html  = build_card_news_from_briefing(fc_ctx, "crypto")    or build_news_html(news.get("crypto", []))

    # 🆕 ブリーフィングのニュースは各マーケットカードに集約済み。専用セクション(trust_news)とTOP3は
    #    重複のため出さない。ブリーフィング不在時のみ従来の TOP3 をフォールバック表示。
    if fc_ctx:
        top3_block = ""
    else:
        top3_block = f'''  <!-- トップニュース（フォールバック）-->
  <div class="top-news">
    <div class="top-news-title">🔥 マーケットを動かすニュース TOP3 <span style="font-size:.7rem;color:#57606a;font-weight:500">（中央銀行・経済指標・地政学など影響度の高いキーワードでスコアリング）</span></div>
    {top_news_html}
  </div>'''

    # AI 投資判断セクション（Gemini）
    ai_analysis_html = build_ai_analysis_section(
        nikkei_val=nk,    sp500_val=sp,
        gold_val=gld,     btc_val=btc,
        stocks_news=news.get("stocks", []),
        commodity_news=news.get("commodity", []),
        crypto_news=news.get("crypto", []),
    )

    # 🆕 今週の投資戦略への自動導線バナー（最新 guide-weekly を自動検出）
    weekly_strategy_banner = build_weekly_strategy_banner(now_jst)
    # 🆕 注目の経済指標バナー（発表3日前〜当日まで常時表示・更新履歴とは別枠）
    indicator_preview_banner = build_indicator_preview_banner(now_jst)
    # 🆕 今朝の3行ダイジェスト＋重要イベントカウントダウン（2026-06-11）
    morning_digest = build_morning_digest_banner(now_jst, data, label)
    # 🆕 📰 更新履歴：手動エントリ＋週次自動エントリを「日付降順」に並べ、最新5件のみ表示。
    #    新記事を足すときは下のリストに {"date","line"} を1件追加するだけ（並べ替え・5件キープは自動）。
    #    週次戦略(guide-weekly)は build_weekly_history_item が自動検出するので手動追記しない。
    _history_items = [
        {"date": "2026-06-30", "line": '・<b>2026-06-30</b>: 📰 解説「<a href="guide-news-2026-06-30-gold-q2-crash.html" style="color:#0969da"><b>【6/30】金（ゴールド）Q2急落・$3,986</b></a>」公開'},
        {"date": "2026-06-30", "line": '・<b>2026-06-30</b>: 🐟 解説「<a href="guide-proverb-atama-shippo.html" style="color:#0969da"><b>頭と尻尾はくれてやれ</b></a>」公開'},
        {"date": "2026-06-30", "line": '・<b>2026-06-30</b>: 🧪 解説「<a href="guide-signal-lab-025.html" style="color:#0969da"><b>研究日誌 #25 指数の売りの27%という現実——ショート勝率と方向非対称の解剖</b></a>」公開'},
        {"date": "2026-06-29", "line": '・<b>2026-06-29</b>: 📰 解説「<a href="guide-news-2026-06-29-tokyo-cpi-boj.html" style="color:#0969da"><b>【6/29】東京6月CPI 8ヶ月ぶり加速・コア+1.6% — 日銀の次の利上げはいつか？</b></a>」公開'},
        {"date": "2026-06-29", "line": '・<b>2026-06-29</b>: 🧪 解説「<a href="guide-signal-lab-024.html" style="color:#0969da"><b>円クロスFXでRSI逆張りが機能しない理由</b></a>」公開'},
        {"date": "2026-06-28", "line": '・<b>2026-06-28</b>: 📰 解説「<a href="guide-news-2026-06-28-iran-us-escalation.html" style="color:#0969da"><b>【6/28】米イラン停戦が瀬戸際、それでも原油急落した理由</b></a>」公開'},
        {"date": "2026-06-28", "line": '・<b>2026-06-28</b>: 🧪 解説「<a href="guide-signal-lab-023.html" style="color:#0969da"><b>研究日誌 #23 RSI売られすぎとBB下限タッチはなぜ正反対になるか——467件の資産クラス別比較</b></a>」公開'},
        {"date": "2026-06-27", "line": '・<b>2026-06-27</b>: 📰 解説「<a href="guide-news-2026-06-27-alphabet-dow.html" style="color:#0969da"><b>【6/27】AlphabetがダウJones産業平均に週明け6/29採用・Verizon除外</b></a>」公開'},
        {"date": "2026-06-27", "line": '・<b>2026-06-27</b>: 🧪 解説「<a href="guide-signal-lab-022.html" style="color:#0969da"><b>研究日誌 #22 逆張り買いはトレンド次第で真逆——上昇中54%・下降中34%の非対称とグループ交絡</b></a>」公開'},
        {"date": "2026-06-26", "line": '・<b>2026-06-26</b>: 📰 解説「<a href="guide-news-2026-06-26-openai-ipo-delay-softbank.html" style="color:#0969da"><b>【6/26】OpenAI IPO延期報道でSoftBank一時14%急落・日経歴代3位▲3,005円</b></a>」公開'},
        {"date": "2026-06-26", "line": '・<b>2026-06-26</b>: 🧪 解説「<a href="guide-signal-lab-021.html" style="color:#0969da"><b>研究日誌 #21 指数×ロング 前向きトラッカー初昇格——E(R)+0.40が示した「買い方有利」の傾向</b></a>」公開'},
        {"date": "2026-06-25", "line": '・<b>2026-06-25</b>: 📰 解説「<a href="guide-news-2026-06-25-micron-q3-record.html" style="color:#0969da"><b>【6/25】Micron Q3過去最高決算・売上$41.5B 前年比+340% — AIメモリ需要が構造的と確認</b></a>」公開'},
        {"date": "2026-06-25", "line": '・<b>2026-06-25</b>: 🧪 解説「<a href="guide-signal-lab-020.html" style="color:#0969da"><b>研究日誌 #20 MA デッドクロス×ショート 62.5%——ゴールデンクロス(ロング)との33pp非対称</b></a>」公開'},
        {"date": "2026-06-24", "line": '・<b>2026-06-24</b>: 📐 解説「<a href="guide-yield-curve.html" style="color:#0969da"><b>イールドカーブ・逆イールドとは？景気後退の前兆とされる金利の「形」を図解</b></a>」公開'},
        {"date": "2026-06-24", "line": '・<b>2026-06-24</b>: 💳 解説「<a href="guide-credit-spread.html" style="color:#0969da"><b>クレジットスプレッドとは？「市場の不安」を先に映す金利差を図解</b></a>」公開'},
        {"date": "2026-06-24", "line": '・<b>2026-06-24</b>: 🧺 解説「<a href="guide-etf-vs-mutual-fund.html" style="color:#0969da"><b>ETFと投資信託の違いとは？仕組み・コスト・使い分けを図解</b></a>」公開'},
        {"date": "2026-06-24", "line": '・<b>2026-06-24</b>: 📈 解説「<a href="guide-simple-vs-compound-interest.html" style="color:#0969da"><b>単利と複利とは？「利息に利息がつく」複利の力を図解（72の法則も）</b></a>」公開'},
        {"date": "2026-06-24", "line": '・<b>2026-06-24</b>: 💴 解説「<a href="guide-interest-rates-bonds.html" style="color:#0969da"><b>金利と債券とは？金利が上がると債券価格が下がる理由を図解</b></a>」公開'},
        {"date": "2026-06-24", "line": '・<b>2026-06-24</b>: 🧾 解説「<a href="guide-order-types.html" style="color:#0969da"><b>成行・指値・逆指値とは？注文方法の違いと使い分け</b></a>」公開'},
        {"date": "2026-06-24", "line": '・<b>2026-06-24</b>: 📊 解説「<a href="guide-per-pbr.html" style="color:#0969da"><b>PERとPBRとは？割安・割高を見分ける2大指標</b></a>」公開'},
        {"date": "2026-06-24", "line": '・<b>2026-06-24</b>: 🧪 解説「<a href="guide-signal-lab-019.html" style="color:#0969da"><b>研究日誌 #19 もみあい×Sのエッジ解剖——low_break×金属 0/10 が主犯</b></a>」公開'},
        {"date": "2026-06-23", "line": '・<b>2026-06-23</b>: 🛟 解説「<a href="guide-correction-playbook.html" style="color:#0969da"><b>株の急落・調整局面での立ち回り方</b></a>」公開'},
        {"date": "2026-06-24", "line": '・<b>2026-06-24</b>: 📰 解説「<a href="guide-news-2026-06-24-soxx-global-semis-rout.html" style="color:#0969da"><b>【6/24】世界的AI半導体株急落・SOXX-7.88%・韓国KOSPIサーキットブレーカー2度発動</b></a>」公開'},
        {"date": "2026-06-23", "line": '・<b>2026-06-23</b>: 📰 解説「<a href="guide-news-2026-06-23-alphabet-ai-talent.html" style="color:#0969da"><b>【6/23】Alphabet AI人材2人離脱・株価-5〜7%・時価総額約37兆円消失</b></a>」公開'},
        {"date": "2026-06-23", "line": '・<b>2026-06-23</b>: 🌻 解説「<a href="guide-summer-doldrums.html" style="color:#0969da"><b>夏枯れ相場とは？薄商いの夏の備え方</b></a>」公開'},
        {"date": "2026-06-22", "line": '・<b>2026-06-22</b>: 🧪 解説「<a href="guide-signal-lab-018.html" style="color:#0969da"><b>研究日誌 #18 逆張りロングは"舞台"を選ぶ——指数専有59%エッジと全体42%の罠</b></a>」公開'},
        {"date": "2026-06-22", "line": '・<b>2026-06-22</b>: 📰 解説「<a href="guide-news-2026-06-22-nikkei-72k.html" style="color:#0969da"><b>【6/22】日経平均が史上初の7万2000円台突破・8日続伸</b></a>」公開'},
        {"date": "2026-06-22", "line": '・<b>2026-06-22</b>: 🧪 解説「<a href="guide-signal-lab-017.html" style="color:#0969da"><b>研究日誌 #17 blocked=True方向性分解——壁ありショートは勝率が高め・ロングは中立</b></a>」公開'},
        {"date": "2026-06-21", "line": '・<b>2026-06-21</b>: 📰 解説「<a href="guide-news-2026-06-21-intel-apple-chip.html" style="color:#0969da"><b>【6/21】トランプ発表でIntel+10.6%急騰—Apple×Intel半導体協業の背景と日本株への影響</b></a>」公開'},
        {"date": "2026-06-21", "line": '・<b>2026-06-21</b>: 🧪 解説「<a href="guide-signal-lab-016.html" style="color:#0969da"><b>研究日誌 #16 ドル建てFXクロスのロングは逆効果だった——other_fx 全191件の方向性検証</b></a>」公開'},
        {"date": "2026-06-20", "line": '・<b>2026-06-20</b>: 🚨 解説「<a href="guide-jpy-intervention-2026-06.html" style="color:#0969da"><b>ドル円161円突破、為替介入はあるのか？「いくらで介入」を中立整理</b></a>」公開'},
        {"date": "2026-06-20", "line": '・<b>2026-06-20</b>: ⚖️ 解説「<a href="guide-risk-by-account-size.html" style="color:#0969da"><b>資産額でリスクの取り方は変えるべき？ 変える「攻めの量」と変えてはいけない「守りの床」</b></a>」公開'},
        {"date": "2026-06-20", "line": '・<b>2026-06-20</b>: 📊 解説「<a href="guide-jp-value-vs-zombie.html" style="color:#0969da"><b>「2倍株を当てる」より「ゼロ化を避ける」— 上昇率と下落率で見る日本株</b></a>」公開'},
        {"date": "2026-06-20", "line": '・<b>2026-06-20</b>: 🧪 解説「<a href="guide-signal-lab-015.html" style="color:#0969da"><b>研究日誌 #15 4H足ロングは系統的に弱い——時間足で勝率はどう変わるか</b></a>」公開'},
        {"date": "2026-06-19", "line": '・<b>2026-06-19</b>: 📰 解説「<a href="guide-news-2026-06-19-fujikura-ai-rally.html" style="color:#0969da"><b>【6/19】フジクラが営業利益予想47%上方修正でストップ高・AIラリー再加速</b></a>」公開'},
        {"date": "2026-06-18", "line": '・<b>2026-06-18</b>: 🧪 解説「<a href="guide-signal-lab-013.html" style="color:#0969da"><b>レジーム反転の罠——金属ロングが20年最良から最悪へ</b></a>」公開'},
        {"date": "2026-06-18", "line": '・<b>2026-06-18</b>: 📰 解説「<a href="guide-news-2026-06-18-fomc-nikkei-71k.html" style="color:#0969da"><b>【6/18】FOMCタカ派転換でも日経が71,053円へ最高値更新 — 日米逆行の背景</b></a>」公開'},
        {"date": "2026-06-17", "line": '・<b>2026-06-17</b>: 🧪 解説「<a href="guide-signal-lab-012.html" style="color:#0969da"><b>研究日誌 #12 もみあい×ショートが67%——FDR通過の新エッジ発見、環境依存も解明</b></a>」公開'},
        {"date": "2026-06-17", "line": '・<b>2026-06-17</b>: 📰 解説「<a href="guide-news-2026-06-17-nikkei-70k.html" style="color:#0969da"><b>【6/16】日経平均が史上初の7万円台タッチ・連日最高値更新</b></a>」公開'},
        {"date": "2026-06-17", "line": '・<b>2026-06-17</b>: 🧪 解説「<a href="guide-signal-lab-011.html" style="color:#0969da"><b>「当てる」より「避ける・飛ばさない」——守りが効く2つの理由（例題編）</b></a>」公開'},
        {"date": "2026-06-17", "line": '・<b>2026-06-17</b>: 🧪 解説「<a href="guide-signal-lab-010.html" style="color:#0969da"><b>「当てる」より「飛ばさない」——ケリー基準と破産確率（リスク管理編）</b></a>」公開'},
        {"date": "2026-06-15", "line": '・<b>2026-06-15</b>: 📚 解説「<a href="guide-investment-books.html" style="color:#0969da"><b>投資本の系統別ガイド｜デイトレ・ファンダ・テクニカル・偉人…「どれを読む？」を系統で選ぶ</b></a>」公開'},
        {"date": "2026-06-15", "line": '・<b>2026-06-15</b>: 📰 解説「<a href="guide-news-2026-06-15-nikkei-69k.html" style="color:#0969da"><b>【6/15】日経平均が+5%急騰・史上初の6万9000円台はなぜ？ 米イラン緊張緩和を中立整理</b></a>」公開'},
        {"date": "2026-06-15", "line": '・<b>2026-06-15</b>: 📚 解説「<a href="guide-learning-roadmap.html" style="color:#0969da"><b>投資の学習ロードマップ — 何から学ぶ？「順番」で迷わない地図</b></a>」公開'},
        {"date": "2026-06-13", "line": '・<b>2026-06-13</b>: 🏦 解説「<a href="guide-private-credit.html" style="color:#0969da"><b>プライベートクレジットとは？ リーマンショック級なのか — 仕組みと5つの危険性をフラットに整理</b></a>」公開'},
        {"date": "2026-06-13", "line": '・<b>2026-06-13</b>: 🧪 解説「<a href="guide-signal-lab-005.html" style="color:#0969da"><b>研究日誌 #5 壁ありシグナルが勝つ逆転現象——「避けろ」判定の中身を解剖</b></a>」公開'},
        {"date": "2026-06-13", "line": '・<b>2026-06-13</b>: 🧪 解説「<a href="guide-signal-lab-004.html" style="color:#0969da"><b>研究日誌 #4 ゴールドはロングだと9割負ける——方向性の罠を解剖</b></a>」公開'},
        {"date": "2026-06-12", "line": '・<b>2026-06-12</b>: 💱 解説「<a href="guide-swap-points.html" style="color:#0969da"><b>スワップポイントの仕組みとリスク｜FXの金利差収益を図解で解説</b></a>」公開'},
        {"date": "2026-06-12", "line": '・<b>2026-06-12</b>: 🧪 解説「<a href="guide-signal-lab-003.html" style="color:#0969da"><b>AIシグナル研究日誌 #3：切り番フィルタは空振り——でも「方向の交絡」という別鉱脈が見えた</b></a>」公開'},
        {"date": "2026-06-12", "line": '・<b>2026-06-12</b>: 💰 解説「<a href="guide-dollar-cost-averaging.html" style="color:#0969da"><b>ドルコスト平均法とは？仕組み・一括投資との比較・やめ時の罠</b></a>」公開'},
        {"date": "2026-06-11", "line": '・<b>2026-06-11</b>: 💣 解説「<a href="guide-leverage.html" style="color:#0969da"><b>レバレッジとナンピンの正体——なぜ資産が溶けるのか</b></a>」公開'},
        {"date": "2026-06-11", "line": '・<b>2026-06-11</b>: 🤖 解説「<a href="guide-ai-investing-4types.html" style="color:#0969da"><b>AIに「上がる銘柄」を聞いてはいけない理由｜AI×投資の4つの型</b></a>」公開'},
        {"date": "2026-06-11", "line": '・<b>2026-06-11</b>: 📓 解説「<a href="guide-trading-journal.html" style="color:#0969da"><b>売買日誌で「自分だけのエッジ」を見つける技術</b></a>」公開'},
        {"date": "2026-06-10", "line": '・<b>2026-06-10</b>: 🧪 研究日誌「<a href="guide-signal-lab-002.html" style="color:#0969da"><b>#2：「上げトレンド中の下げは押し目では？」を検証したら希望が見えた</b></a>」公開'},
        {"date": "2026-06-10", "line": '・<b>2026-06-10</b>: 🧪 連載開始「<a href="guide-signal-lab-001.html" style="color:#0969da"><b>AIシグナル研究日誌 #1：新フィルタ、534件検証の結果は「不採用」</b></a>」公開'},
        {"date": "2026-06-08", "line": '・<b>2026-06-08</b>: 💹 解説「<a href="guide-margin-balance.html" style="color:#0969da"><b>信用残の見方</b></a>」公開'},
        {"date": "2026-06-08", "line": '・<b>2026-06-08</b>: 🛡️ 解説「<a href="guide-diversification.html" style="color:#0969da"><b>分散投資の本質</b></a>」公開'},
        {"date": "2026-06-08", "line": '・<b>2026-06-08</b>: 🧠 解説「<a href="guide-cognitive-biases.html" style="color:#0969da"><b>投資家が陥る認知バイアス6選</b></a>」公開'},
        {"date": "2026-06-08", "line": '・<b>2026-06-08</b>: 🛡️ 解説「<a href="guide-compounding-drawdown.html" style="color:#0969da"><b>複利とドローダウンの関係</b></a>」公開'},
        {"date": "2026-06-08", "line": '・<b>2026-06-08</b>: 🧠 解説「<a href="guide-profit-taking.html" style="color:#0969da"><b>利益確定の心理と技術</b></a>」公開'},
        {"date": "2026-06-08", "line": '・<b>2026-06-08</b>: 🛡️ 解説「<a href="guide-risk-reward.html" style="color:#0969da"><b>リスクリワードと期待値</b></a>」公開'},
        {"date": "2026-06-07", "line": '・<b>2026-06-07</b>: 🧘 解説「<a href="guide-trading-psychology-calm.html" style="color:#0969da"><b>感情のコントロール・平常心の作り方</b></a>」公開'},
        {"date": "2026-06-07", "line": '・<b>2026-06-07</b>: 🏛️ 解説「<a href="guide-honebuto-2026.html" style="color:#0969da"><b>骨太の方針2026とは？ いつ発表？ 高市政権初・「責任ある積極財政」の論点と市場への影響</b></a>」公開'},
        {"date": "2026-06-06", "line": '・<b>2026-06-06</b>: 🛡️ 解説「<a href="guide-position-sizing.html" style="color:#0969da"><b>ポジションサイジングの基本｜2%ルールと損切り幅から逆算するロット計算</b></a>」公開'},
        {"date": "2026-06-05", "line": '・<b>2026-06-05</b>: 🧠 解説「<a href="guide-loss-cut.html" style="color:#0969da"><b>損切りができない本当の理由と、淡々と切る技術</b></a>」公開'},
        {"date": "2026-06-05", "line": '・<b>2026-06-05</b>: 📈 解説「<a href="guide-dow-theory.html" style="color:#0969da"><b>ダウ理論とは？6つの基本原則とトレンドの3段階を初心者向けに徹底解説</b></a>」公開'},
        {"date": "2026-06-05", "line": '・<b>2026-06-05</b>: 📊 解説「<a href="guide-adx.html" style="color:#0969da"><b>ADX・DMIとは？トレンドの強さの測り方と+DI/-DIの見方を初心者向けに徹底解説</b></a>」公開'},
        {"date": "2026-06-04", "line": '・<b>2026-06-04</b>: 📊 解説「<a href="guide-stochastics.html" style="color:#0969da"><b>ストキャスティクスとは？%K・%D・80/20の見方とRSIとの違いを初心者向けに徹底解説</b></a>」公開'},
        {"date": "2026-06-04", "line": '・<b>2026-06-04</b>: 📉 解説「<a href="guide-btc-crash-2026-06.html" style="color:#0969da"><b>ビットコイン暴落（2026年6月）はなぜ？6つの要因と今後の3シナリオを整理</b></a>」公開'},
        {"date": "2026-06-04", "line": '・<b>2026-06-04</b>: 📐 解説「<a href="guide-fibonacci.html" style="color:#0969da"><b>フィボナッチリトレースメントとは？黄金比・38.2/50/61.8%・押し目の見方を初心者向けに徹底解説</b></a>」公開'},
        {"date": "2026-06-04", "line": '・<b>2026-06-04</b>: 📊 解説「<a href="guide-volume.html" style="color:#0969da"><b>出来高とは？見方・価格との関係・セリングクライマックスを初心者向けに徹底解説</b></a>」公開'},
        {"date": "2026-06-03", "line": '・<b>2026-06-03</b>: 📊 解説「<a href="guide-bollinger-bands.html" style="color:#0969da"><b>ボリンジャーバンドとは？±2σ・スクイーズ・バンドウォークの見方を初心者向けに徹底解説</b></a>」公開'},
        {"date": "2026-06-03", "line": '・<b>2026-06-03</b>: 📊 解説「<a href="guide-rsi.html" style="color:#0969da"><b>RSIとは？見方・買われすぎ売られすぎ・ダイバージェンスを初心者向けに徹底解説</b></a>」公開'},
        {"date": "2026-06-02", "line": '・<b>2026-06-02</b>: 📊 解説「<a href="guide-macd.html" style="color:#0969da"><b>MACD やさしい解説（GC・ダイバージェンス）</b></a>」公開'},
        {"date": "2026-06-02", "line": '・<b>2026-06-02</b>: ☁️ 解説「<a href="guide-ichimoku.html" style="color:#0969da"><b>一目均衡表 やさしい解説（雲・三役好転）</b></a>」公開'},
        {"date": "2026-06-02", "line": '・<b>2026-06-02</b>: 📈 解説「<a href="guide-moving-average.html" style="color:#0969da"><b>移動平均線とは？SMA・EMA・ゴールデンクロスの使い方を初心者向けに徹底解説【テクニカル分析シリーズ第1弾】</b></a>」公開'},
        {"date": "2026-06-01", "line": '・<b>2026-06-01</b>: 🏰 解説「<a href="guide-oriental-land-2026-06.html" style="color:#0969da"><b>オリエンタルランド（4661）はなぜ約6割安に？ 暴落の5つの理由と「復活」3シナリオを整理</b></a>」公開'},
        {"date": "2026-05-31", "line": '・<b>2026-05-31</b>: 🏦 解説「<a href="guide-bank-stocks-2026-05.html" style="color:#0969da"><b>日銀が利上げしたら銀行株はどうなる？ メガバンク vs 地方銀行の違いを整理（2026年版）</b></a>」公開'},
        {"date": "2026-05-31", "line": '・<b>2026-05-31</b>: 🗾 解説「<a href="guide-japan-strategy-2026-05.html" style="color:#0969da"><b>2026年 日本株の歩き方：日経を動かす「攻め」と暴落に強い「守り」のセクター戦略</b></a>」公開'},
        {"date": "2026-05-29", "line": '・<b>2026-05-29</b>: 🏭 解説「<a href="guide-tsmc-2026-05.html" style="color:#0969da"><b>TSMC（NYSE: TSM）2026 Q1 決算解説：売上 359 億ドルで過去最高、純利益 +58% — 世界最大ファウンドリの強さと「地政学リスク」をフラットに整理する</b></a>」公開'},
    ]
    _wk_item = build_weekly_history_item(now_jst)
    if _wk_item:
        _history_items.append(_wk_item)
    _history_items.sort(key=lambda x: x["date"], reverse=True)  # 日付降順（安定ソート＝同日は手動を先に）
    update_history_html = "<br>\n".join("      " + it["line"] for it in _history_items[:5])
    # 🆕 注目の解説記事（独自コンテンツを前面に）
    featured_guides = build_featured_guides()

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  {seo_head("", f"マーケットニュース {date_str}", "日経平均・ダウ・S&P500・ドル円・原油・金・ビットコインの最新価格と日本語ニュースを毎日2回更新。AIが市場センチメントを判定し、日本人投資家にとっての注目ポイントを解説します。")}
  {GA4_TAG}
  <style>
    *{{margin:0;padding:0;box-sizing:border-box}}
    body{{font-family:'Noto Sans JP','Segoe UI','Hiragino Sans','Yu Gothic',sans-serif;background:#ffffff;color:#1f2328;min-height:100vh}}
    header{{background:linear-gradient(135deg,#f6f8fa,#ffffff);border-bottom:1px solid #d0d7de;padding:24px 32px}}
    .header-inner{{max-width:1200px;margin:0 auto;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px}}
    .header-title{{font-size:1.6rem;font-weight:700;background:linear-gradient(90deg,#0969da,#1f6feb);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}
    .header-meta{{font-size:.85rem;color:#57606a}}
    .header-meta span{{color:#0969da;font-weight:600}}
    main{{max-width:1200px;margin:0 auto;padding:32px 24px}}
    .sentiment-banner{{background:linear-gradient(135deg,#dafbe1,#ddf4ff);border:1px solid {badge_color};border-radius:16px;padding:32px 36px;margin-bottom:32px;display:flex;align-items:center;gap:24px;flex-wrap:wrap;box-shadow:0 4px 12px rgba(0,0,0,.05)}}
    .sentiment-icon{{font-size:4rem;line-height:1;flex-shrink:0}}
    .sentiment-body{{flex:1;min-width:200px}}
    .sentiment-label-small{{font-size:.78rem;color:#57606a;font-weight:600;letter-spacing:.08em;margin-bottom:4px}}
    .sentiment-badge{{color:{badge_color};font-weight:800;font-size:2.4rem;line-height:1.1;margin-bottom:6px;display:block}}
    .sentiment-text{{color:#424a53;font-size:.92rem;line-height:1.6}}
    .morning-digest{{background:#ffffff;border:1px solid #d0d7de;border-left:4px solid #bc4c00;border-radius:10px;padding:16px 22px;margin-bottom:32px}}
    .md-title{{font-size:.98rem;font-weight:700;color:#bc4c00;margin-bottom:8px}}
    .md-sub{{font-size:.72rem;color:#6e7781;font-weight:500;margin-left:6px}}
    .md-line{{font-size:.9rem;color:#424a53;line-height:2.0}}
    .md-line b{{color:#1f2328}}
    .md-up{{color:#1a7f37;font-weight:700}}
    .md-down{{color:#cf222e;font-weight:700}}
    .md-chips{{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px;padding-top:12px;border-top:1px dashed #d0d7de}}
    .md-chip{{display:inline-block;padding:4px 12px;border-radius:999px;background:#f6f8fa;border:1px solid #d0d7de;font-size:.78rem;color:#424a53;font-weight:600}}
    .md-chip b{{color:#cf222e}}
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
    .top-news{{background:linear-gradient(135deg,#ddf4ff,#f6f8fa);border:1px solid #0969da;border-radius:12px;padding:20px 24px;margin-bottom:32px}}
    .top-news-title{{font-size:1rem;font-weight:700;color:#0969da;margin-bottom:12px}}
    .news-item{{display:block;padding:10px 0;border-bottom:1px solid #d0d7de;text-decoration:none;transition:background .15s}}
    .news-item:last-child{{border-bottom:none}}
    .news-item:hover{{background:#ffffff;border-radius:6px;padding-left:8px}}
    .news-title{{display:block;font-size:.88rem;color:#1f2328;font-weight:600;line-height:1.5;margin-bottom:2px}}
    .news-meta{{display:block;font-size:.72rem;color:#57606a}}
    .news-sent{{margin-right:6px;font-size:1.3rem;vertical-align:middle}}
    .news-ai{{display:block;font-size:.78rem;color:#1f6feb;line-height:1.65;margin:6px 0 4px;padding:6px 10px;background:#f6f8fa;border-left:3px solid #1f6feb;border-radius:4px}}
    /* AI 投資判断セクション */
    .ai-analysis-section{{margin:24px 0 36px}}
    .ai-analysis-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px;margin-top:14px}}
    .ai-asset-card{{background:#ffffff;border:1px solid #d0d7de;border-radius:12px;padding:16px 18px;box-shadow:0 1px 3px rgba(0,0,0,.04)}}
    .ai-asset-header{{display:flex;align-items:center;gap:10px;margin-bottom:12px}}
    .ai-asset-icon{{font-size:1.6rem}}
    .ai-asset-name-wrap{{flex:1;min-width:0}}
    .ai-asset-name{{font-size:.95rem;font-weight:700;color:#1f2328}}
    .ai-asset-price{{font-size:.78rem;color:#57606a;margin-top:2px}}
    .ai-asset-sentiment{{font-size:.78rem;font-weight:700;padding:4px 10px;border-radius:12px;white-space:nowrap}}
    .ai-meter{{margin:10px 0 12px}}
    .ai-meter-track{{position:relative;height:8px;background:linear-gradient(90deg,#fee2e2 0%,#fef3c7 50%,#dcfce7 100%);border-radius:4px}}
    .ai-meter-dot{{position:absolute;top:50%;width:14px;height:14px;border-radius:50%;border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.25);transform:translate(-50%,-50%)}}
    .ai-meter-labels{{display:flex;justify-content:space-between;font-size:.7rem;color:#57606a;margin-top:4px}}
    .ai-action{{font-size:.85rem;color:#1f2328;margin-bottom:6px;line-height:1.5}}
    .ai-action strong{{color:#0969da}}
    .ai-reason{{font-size:.82rem;color:#424a53;line-height:1.6}}
    .ai-reason strong{{color:#9a6700}}
    .news-empty{{font-size:.82rem;color:#6e7781;padding:8px 0}}
    .card-news{{margin-top:14px;padding-top:14px;border-top:1px solid #d0d7de}}
    .card-news-title{{font-size:.78rem;color:#0969da;font-weight:600;margin-bottom:8px}}
    .card-news .news-item{{padding:6px 0}}
    .card-news .news-title{{font-size:.8rem}}
    .card-news .news-meta{{font-size:.68rem}}
    footer{{background:#f6f8fa;border-top:1px solid #d0d7de;padding:20px 32px;text-align:center;font-size:.78rem;color:#6e7781}}
    footer a{{color:#0969da;text-decoration:none}}
    .nav-bar{{display:flex;flex-wrap:wrap;gap:10px;justify-content:center;max-width:1000px;margin:0 auto 28px}}
    .nav-btn{{display:inline-flex;align-items:center;justify-content:center;gap:8px;padding:11px 20px;background:#f6f8fa;border:1px solid #d0d7de;border-radius:10px;color:#57606a;text-decoration:none;font-size:.95rem;font-weight:600;transition:all .2s;min-width:170px}}
    .nav-btn:hover{{border-color:#0969da;color:#0969da}}
    .nav-btn.current{{background:#0969da;border-color:#0969da;color:#fff}}
    .market-card-img{{width:100%;height:120px;object-fit:cover;object-position:top;display:block}}
    .a8-pc{{display:inline-block}}.a8-mobile{{display:none}}
    .hero-banner{{position:relative;border-radius:16px;overflow:hidden;margin-bottom:32px;box-shadow:0 4px 16px rgba(0,0,0,.08)}}
    .hero-img{{width:100%;height:auto;display:block;max-height:280px;object-fit:cover}}
    .hero-overlay{{position:absolute;inset:0;background:linear-gradient(90deg,rgba(255,255,255,.85) 0%,rgba(255,255,255,.4) 60%,rgba(255,255,255,0) 100%);display:flex;align-items:center;padding:0 36px}}
    .hero-title{{font-size:2rem;font-weight:800;color:#0969da;margin-bottom:6px;text-shadow:0 1px 3px rgba(255,255,255,.8)}}
    .hero-sub{{font-size:1rem;color:#1f2328;font-weight:500;text-shadow:0 1px 2px rgba(255,255,255,.8)}}
    @media(max-width:600px){{
      .header-inner{{flex-direction:column}}
      .sentiment-banner{{flex-direction:column}}
      .nav-bar{{display:grid;grid-template-columns:1fr 1fr;gap:8px}}
      .nav-btn{{min-width:0;width:100%;padding:10px 8px;font-size:.82rem}}
      .hero-img{{max-height:140px;object-position:center}}
      .hero-overlay{{padding:0 18px;background:linear-gradient(180deg,rgba(255,255,255,.92) 0%,rgba(255,255,255,.7) 70%,rgba(255,255,255,.5) 100%)}}
      .hero-title{{font-size:1.3rem;margin-bottom:2px;text-shadow:0 1px 2px #fff,0 0 4px #fff}}
      .hero-sub{{font-size:.78rem;text-shadow:0 1px 2px #fff,0 0 3px #fff}}
      .market-card-img{{height:160px;object-position:top center}}
      .a8-pc{{display:none}}.a8-mobile{{display:inline-block}}
    }}
    /* ダークモード（明示ルール） */
    body.dark{{background:#0d1117!important;color:#e6edf3}}
    body.dark header{{background:linear-gradient(135deg,#161b22,#0d1117)!important;border-bottom-color:#30363d}}
    body.dark .header-meta,body.dark .header-meta span{{color:#8b949e}}
    body.dark .nav-btn{{background:#161b22!important;border-color:#30363d;color:#8b949e}}
    body.dark .nav-btn:hover{{border-color:#58a6ff;color:#58a6ff}}
    body.dark .nav-btn.current{{background:#1f6feb!important;border-color:#58a6ff;color:#fff}}
    body.dark .hero-overlay{{background:linear-gradient(90deg,rgba(13,17,23,.85) 0%,rgba(13,17,23,.5) 60%,rgba(13,17,23,0) 100%)}}
    body.dark .hero-title{{color:#79c0ff;text-shadow:0 1px 3px rgba(13,17,23,.9)}}
    body.dark .hero-sub{{color:#e6edf3;text-shadow:0 1px 2px rgba(13,17,23,.9)}}
    body.dark .sentiment-banner{{background:linear-gradient(135deg,#0d2616,#0d1f2a)!important;border-color:#2ea043}}
    body.dark .sentiment-label-small{{color:#8b949e}}
    body.dark .sentiment-text{{color:#c9d1d9}}
    body.dark .morning-digest{{background:#161b22;border-color:#30363d;border-left-color:#d4a017}}
    body.dark .md-title{{color:#d4a017}}
    body.dark .md-sub{{color:#8b949e}}
    body.dark .md-line{{color:#c9d1d9}}
    body.dark .md-line b{{color:#e6edf3}}
    body.dark .md-up{{color:#3fb950}}
    body.dark .md-down{{color:#ff8080}}
    body.dark .md-chips{{border-top-color:#30363d}}
    body.dark .md-chip{{background:#0d1117;border-color:#30363d;color:#c9d1d9}}
    body.dark .md-chip b{{color:#ff8080}}
    body.dark .section-title{{color:#8b949e}}
    body.dark .card{{background:#161b22!important;border-color:#30363d}}
    body.dark .card:hover{{border-color:#58a6ff}}
    body.dark .card-title{{color:#e6edf3}}
    body.dark .card-subtitle{{color:#8b949e}}
    body.dark .price-row{{border-bottom-color:#30363d}}
    body.dark .price-label{{color:#8b949e}}
    body.dark .price-value{{color:#e6edf3}}
    body.dark .card-summary,body.dark .card-news{{border-top-color:#30363d;color:#8b949e}}
    body.dark .card-news-title{{color:#79c0ff}}
    body.dark .beginner-box{{background:#0d1f2a!important;border-color:#1f6feb;color:#79c0ff}}
    body.dark .beginner-box::before{{color:#79c0ff}}
    body.dark .news-item:hover{{background:#1c2128}}
    body.dark .news-title{{color:#e6edf3}}
    body.dark .news-meta{{color:#8b949e}}
    body.dark .top-news{{background:linear-gradient(135deg,#0d2030,#0d1117)!important;border-color:#1f6feb}}
    body.dark .top-news-title{{color:#79c0ff}}
    body.dark footer{{background:#161b22!important;border-top-color:#30363d;color:#8b949e}}
    body.dark footer a{{color:#79c0ff}}
    body.dark #theme-toggle{{background:#161b22!important;border-color:#30363d;color:#fff}}
    body.dark .market-card-img,body.dark .hero-img{{filter:brightness(.85)}}
    /* インラインstyleで白背景になっている要素も上書き */
    body.dark a[style*="background:#ffffff"],body.dark a[style*="background:#fff"],body.dark div[style*="background:#ffffff"],body.dark div[style*="background:#fff"]{{background:#161b22!important;border-color:#30363d!important}}
    body.dark div[style*="background:#f6f8fa"]{{background:#0d1117!important}}
    body.dark div[style*="background:#ddf4ff"]{{background:#1a2030!important;border-color:#1f6feb!important}}
    body.dark div[style*="color:#1f2328"]{{color:#e6edf3!important}}
    body.dark div[style*="color:#57606a"]{{color:#8b949e!important}}
    body.dark .ad-slot{{background:#0d1117!important;border-color:#30363d!important}}
  </style>
  <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-2552122294306014" crossorigin="anonymous"></script>
  <!-- A8.net広告タグはここに貼る予定 -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;600;700&display=swap" rel="stylesheet">
</head>
<body>
<div id="reading-progress"></div>
<button id="theme-toggle" onclick="toggleTheme()" aria-label="テーマ切替" style="position:fixed;top:16px;right:16px;width:42px;height:42px;border-radius:50%;border:1px solid #d0d7de;background:#fff;cursor:pointer;z-index:9999;box-shadow:0 2px 8px rgba(0,0,0,.1);font-size:18px;display:flex;align-items:center;justify-content:center">🌙</button>
{brand_header("📰", "マーケットニュース", time_str, "GitHub Actions 自動更新")}
<main>

  <!-- ナビゲーション -->
  <nav class="nav-bar">
    <a class="nav-btn current" href="index.html">🏠 トップページ</a>
    <a class="nav-btn" href="political-feed.html">🚨 政治発言ライブ</a>
    <a class="nav-btn" href="track-record.html">📊 シグナル成績</a>
    <a class="nav-btn" href="calendar.html">📅 経済カレンダー</a>
    <a class="nav-btn" href="guides.html">📚 解説記事</a>
    <a class="nav-btn" href="guide-investment-books.html">📖 投資本</a>
    <a class="nav-btn" href="market-health.html">🩺 市場健康度</a>
    <a class="nav-btn" href="hot-assets.html">🔥 出来高急増</a>
    <a class="nav-btn" href="charts.html">📈 50年チャート</a>
    <a class="nav-btn" href="youtube-summary.html">📺 YouTube要約</a>
  </nav>

  <!-- ヒーロー画像 -->
  <div class="hero-banner">
    <img src="01_hero_tokyo_market_banner.png" alt="マーケットニュース" class="hero-img">
    <div class="hero-overlay">
      <div>
        <div class="hero-title"><span style="display:inline-block">お金の不安が消える、</span><span style="display:inline-block">毎朝の 5 分。</span></div>
        <div class="hero-sub"><span style="display:inline-block">暮らしを楽しむための、</span><span style="display:inline-block">日本人投資家サイト</span></div>
      </div>
    </div>
  </div>

  <!-- センチメント -->
  <div class="sentiment-banner">
    <div class="sentiment-icon">{emoji}</div>
    <div class="sentiment-body">
      <div class="sentiment-label-small">本日のマーケットセンチメント</div>
      <span class="sentiment-badge">{label}</span>
      <div class="sentiment-text">
        日経 {fmt_price(nk, 0, suffix='円')} ／ S&amp;P500 {fmt_price(sp, 2)} ／
        USD/JPY {fmt_price(fx, 2, suffix='円')} ／ BTC {fmt_price(btc, 0, prefix='$')} ／
        金 {fmt_price(gld, 2, prefix='$', suffix='/oz')}
      </div>
    </div>
  </div>

{morning_digest}

  <!-- 更新履歴 -->
  <div style="background:#f6f8fa;border:1px solid #d0d7de;border-left:4px solid #0969da;border-radius:8px;padding:14px 22px;margin-bottom:32px;font-size:.88rem;line-height:1.9">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;flex-wrap:wrap;gap:10px">
      <span style="color:#0969da;font-weight:700">📰 更新履歴</span>
      <a href="guides.html" style="color:#1f6feb;font-size:.8rem;font-weight:600;text-decoration:none">📚 記事一覧 →</a>
    </div>
    <div style="color:#424a53">
{update_history_html}
    </div>
  </div>

  {indicator_preview_banner}
  {weekly_strategy_banner}

  <!-- 騰落レシオ -->
  {_build_touraku_section(touraku)}

  <!-- A8広告枠①（トップページ・ニュース上）-->
  <div style="margin:24px 0;padding:14px;background:#ffffff;border:1px solid #d0d7de;border-radius:10px;text-align:center">
    <div style="font-size:.7rem;color:#6e7781;letter-spacing:.12em;margin-bottom:8px">広告 / PR</div>
    <a class="a8-pc" href="https://px.a8.net/svt/ejp?a8mat=4B1WM4+D44RHU+4SM6+614CX" rel="nofollow"><img border="0" width="728" height="90" alt="" src="https://www25.a8.net/svt/bgt?aid=260429404793&amp;wid=001&amp;eno=01&amp;mid=s00000022371001013000&amp;mc=1"></a><img class="a8-pc" border="0" width="1" height="1" src="https://www12.a8.net/0.gif?a8mat=4B1WM4+D44RHU+4SM6+614CX" alt="">
    <a class="a8-mobile" href="https://px.a8.net/svt/ejp?a8mat=4B1WM4+D44RHU+4SM6+5ZEMP" rel="nofollow"><img border="0" width="320" height="50" alt="" src="https://www25.a8.net/svt/bgt?aid=260429404793&amp;wid=001&amp;eno=01&amp;mid=s00000022371001005000&amp;mc=1"></a><img class="a8-mobile" border="0" width="1" height="1" src="https://www13.a8.net/0.gif?a8mat=4B1WM4+D44RHU+4SM6+5ZEMP" alt="">
  </div>

  {top3_block}

  {ai_analysis_html}

  <!-- 今日のカード -->
  <p class="section-title">本日のマーケット</p>
  <div class="cards-grid">
    <div class="card" style="overflow:hidden;padding:0">
      <img src="08_market_stock.png" alt="株式市場" class="market-card-img">
      <div style="padding:20px">
        <div class="card-header">
          <div class="card-icon icon-stocks">🗾</div>
          <div><div class="card-title">株式市場</div><div class="card-subtitle">日本株・米国株</div></div>
        </div>
        <div class="price-row"><span class="price-label">日経平均</span><span class="price-value">{fmt_price(nk, 0, suffix='円')} {fmt_change(nk_chg)}</span></div>
        <div class="price-row"><span class="price-label">S&amp;P500</span><span class="price-value">{fmt_price(sp, 2)} {fmt_change(sp_chg)}</span></div>
        <div class="beginner-box">日経平均は日本を代表する225社の株価の平均です。上がると「日本経済が好調」のサイン。S&P500はアメリカの代表的な500社の指数で、世界経済の体温計ともいわれます。</div>
        <div class="card-news"><div class="card-news-title">📰 関連ニュース</div>{stocks_news_html}</div>
      </div>
    </div>
    <div class="card" style="overflow:hidden;padding:0">
      <img src="09_market_fx.png" alt="為替FX" class="market-card-img">
      <div style="padding:20px">
        <div class="card-header">
          <div class="card-icon icon-fx">💱</div>
          <div><div class="card-title">為替（FX）</div><div class="card-subtitle">ドル円・ユーロ円</div></div>
        </div>
        <div class="price-row"><span class="price-label">USD/JPY</span><span class="price-value">{fmt_price(fx, 2, suffix='円')} {fmt_change(fx_chg)}</span></div>
        <div class="price-row"><span class="price-label">EUR/JPY</span><span class="price-value">{fmt_price(efx, 2, suffix='円')} {fmt_change(efx_chg)}</span></div>
        <div class="beginner-box">1ドルを買うのに何円必要かを示します。数字が大きいほど「円安（ドル高）」。円安は輸出企業に有利ですが、輸入品や旅行が割高になります。</div>
        <div class="card-news"><div class="card-news-title">📰 関連ニュース</div>{fx_news_html}</div>
      </div>
    </div>
    <div class="card" style="overflow:hidden;padding:0">
      <img src="10_market_commodity.png" alt="コモディティ" class="market-card-img">
      <div style="padding:20px">
        <div class="card-header">
          <div class="card-icon icon-cmd">🛢️</div>
          <div><div class="card-title">コモディティ</div><div class="card-subtitle">原油・金</div></div>
        </div>
        <div class="price-row"><span class="price-label">WTI原油</span><span class="price-value">{fmt_price(oil, 2, prefix='$', suffix='/bbl')} {fmt_change(oil_chg)}</span></div>
        <div class="price-row"><span class="price-label">金（スポット）</span><span class="price-value">{fmt_price(gld, 2, prefix='$', suffix='/oz')} {fmt_change(gld_chg)}</span></div>
        <div class="beginner-box">原油価格が上がるとガソリンや電気代に影響します。金は「有事の金」と呼ばれ、世界が不安定なときに買われる安全資産です。金が上がるときは要注意サインのことも。</div>
        <div class="card-news"><div class="card-news-title">📰 関連ニュース</div>{cmd_news_html}</div>
      </div>
    </div>
    <div class="card" style="overflow:hidden;padding:0">
      <img src="11_market_crypto.png" alt="暗号資産" class="market-card-img">
      <div style="padding:20px">
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
  </div>

  <!-- A8広告枠②（トップページ・フッター上）-->
  <div style="margin:32px 0;padding:14px;background:#ffffff;border:1px solid #d0d7de;border-radius:10px;text-align:center">
    <div style="font-size:.7rem;color:#6e7781;letter-spacing:.12em;margin-bottom:8px">広告 / PR</div>
    <a class="a8-pc" href="https://px.a8.net/svt/ejp?a8mat=4B1WM4+D44RHU+4SM6+614CX" rel="nofollow"><img border="0" width="728" height="90" alt="" src="https://www25.a8.net/svt/bgt?aid=260429404793&amp;wid=001&amp;eno=01&amp;mid=s00000022371001013000&amp;mc=1"></a><img class="a8-pc" border="0" width="1" height="1" src="https://www12.a8.net/0.gif?a8mat=4B1WM4+D44RHU+4SM6+614CX" alt="">
    <a class="a8-mobile" href="https://px.a8.net/svt/ejp?a8mat=4B1WM4+D44RHU+4SM6+5ZEMP" rel="nofollow"><img border="0" width="320" height="50" alt="" src="https://www25.a8.net/svt/bgt?aid=260429404793&amp;wid=001&amp;eno=01&amp;mid=s00000022371001005000&amp;mc=1"></a><img class="a8-mobile" border="0" width="1" height="1" src="https://www13.a8.net/0.gif?a8mat=4B1WM4+D44RHU+4SM6+5ZEMP" alt="">
  </div>

{featured_guides}
  <!-- 4機能カード（より深い市場分析へ）-->
  <div style="margin-top:48px;padding-top:24px;border-top:1px solid #d0d7de">
    <div style="font-size:1.2rem;font-weight:700;color:#1f2328;margin-bottom:6px">🔍 AIが導く、より深い市場分析へ</div>
    <div style="font-size:.88rem;color:#57606a;margin-bottom:20px">主要機能ページへのショートカット</div>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px">
      <a href="market-health.html" style="display:block;background:#ffffff;border:1px solid #d0d7de;border-radius:12px;text-decoration:none;transition:all .25s;overflow:hidden">
        <img src="12_feature_market_health.png" alt="市場健康度" style="width:100%;height:140px;object-fit:cover;display:block">
        <div style="padding:18px 22px">
          <div style="font-size:1.02rem;font-weight:700;color:#1a7f37;margin-bottom:6px">🩺 市場健康度ダッシュボード</div>
          <div style="font-size:.78rem;color:#57606a;line-height:1.6">VIX・恐怖と強欲・バフェット指数で市場の過熱感を多角的に可視化</div>
        </div>
      </a>
      <a href="calendar.html" style="display:block;background:#ffffff;border:1px solid #d0d7de;border-radius:12px;text-decoration:none;transition:all .25s;overflow:hidden">
        <img src="13_feature_macro_calendar.png" alt="マクロ経済カレンダー" style="width:100%;height:140px;object-fit:cover;display:block">
        <div style="padding:18px 22px">
          <div style="font-size:1.02rem;font-weight:700;color:#0969da;margin-bottom:6px">📅 マクロ経済カレンダー</div>
          <div style="font-size:.78rem;color:#57606a;line-height:1.6">日米欧中の主要指標・FOMC・日銀イベントを月間一覧でチェック</div>
        </div>
      </a>
      <a href="charts.html" style="display:block;background:#ffffff;border:1px solid #d0d7de;border-radius:12px;text-decoration:none;transition:all .25s;overflow:hidden">
        <img src="15_feature_50year_chart.png" alt="50年チャート" style="width:100%;height:140px;object-fit:cover;display:block">
        <div style="padding:18px 22px">
          <div style="font-size:1.02rem;font-weight:700;color:#9a6700;margin-bottom:6px">📈 50年価格チャート</div>
          <div style="font-size:.78rem;color:#57606a;line-height:1.6">日経・S&amp;P500・ドル円・金の超長期トレンドと歴史的イベント一覧</div>
        </div>
      </a>
      <a href="market-health.html#vix" style="display:block;background:#ffffff;border:1px solid #d0d7de;border-radius:12px;text-decoration:none;transition:all .25s;overflow:hidden">
        <img src="14_feature_vix.png" alt="VIX恐怖指数" style="width:100%;height:140px;object-fit:cover;display:block">
        <div style="padding:18px 22px">
          <div style="font-size:1.02rem;font-weight:700;color:#cf222e;margin-bottom:6px">😱 恐怖指数（VIX）分析</div>
          <div style="font-size:.78rem;color:#57606a;line-height:1.6">投資家心理を数値化したVIXでリスクオン・オフを判定</div>
        </div>
      </a>
    </div>
  </div>

  <div style="background:#f6f8fa;border:1px solid #d0d7de;border-radius:12px;padding:26px 30px;margin-top:28px">
    <h2 style="font-size:1.25rem;color:#1f6feb;margin:0 0 12px;border-bottom:1px solid #d0d7de;padding-bottom:8px">📘 MarketWatch AI でできること</h2>
    <p style="font-size:.96rem;color:#424a53;line-height:1.85;margin-bottom:14px">MarketWatch AI は、日本人投資家のための情報サイトです。単なる市場データの寄せ集めではなく、<strong>「市場データ」＋「独自の解説」＋「AIシグナルの透明な成績公開」</strong>を一つにまとめ、投資家が<strong>感情に振り回されず、規律と平常心で判断できるようになる</strong>ことを目指しています。主に次のことができます。</p>
    <ul style="margin:6px 0 16px 0;padding:0;list-style:none;color:#424a53;font-size:.95rem;line-height:1.8">
      <li style="margin-bottom:10px">📚 <strong><a href="guides.html" style="color:#0969da">解説記事（49本以上）</a></strong>でじっくり学ぶ — <strong>投資心理（損切り・メンタル）／リスク管理（ポジションサイジング）／テクニカル分析（移動平均・RSI・MACD・ボリンジャー等）／経済指標</strong>を、手描きの図解つきで初心者〜中上級まで二層構造で解説。</li>
      <li style="margin-bottom:10px">🩺 <strong>市場の“温度”を読む</strong> — <a href="market-health.html" style="color:#0969da">市場健康度</a>・<a href="vix.html" style="color:#0969da">VIX恐怖指数</a>・<a href="calendar.html" style="color:#0969da">経済カレンダー</a>・<a href="hot-assets.html" style="color:#0969da">出来高急増</a>を、データだけでなく<strong>「読み方・活用法」つき</strong>で。</li>
      <li style="margin-bottom:10px">📊 <strong><a href="track-record.html" style="color:#0969da">シグナル成績を隠さず公開</a></strong> — 自動テクニカルシグナルの発火履歴と結果を、<strong>勝ちも負けも</strong>そのまま公開。実データで検証し、機能しない手法は正直に見直す姿勢を大切にしています。</li>
      <li>🚨 <a href="political-feed.html" style="color:#0969da">政治発言ライブ</a>・<a href="youtube-summary.html" style="color:#0969da">YouTube要約</a>など、忙しい個人投資家の<strong>情報収集の時間を短縮</strong>する機能も。</li>
    </ul>
    <p style="font-size:.86rem;color:#57606a;margin-bottom:8px">▶ はじめての方は <a href="guides.html" style="color:#0969da">解説記事一覧</a> ／ <a href="about.html" style="color:#0969da">運営者情報</a> もどうぞ。</p>
    <p style="font-size:.8rem;color:#6e7781;margin:0">※ 当サイトは情報提供を目的としており、特定銘柄の売買推奨や投資助言ではありません。投資判断はご自身の責任で行ってください。</p>
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
<p data-disclaimer="kinsho-v1" style="margin-top:10px;padding-top:10px;border-top:1px dashed #d0d7de;font-size:.78rem;color:#6e7781;line-height:1.6">⚠️ <b>当サイトは金融商品取引業者ではなく、投資助言・代理業の登録もしていません。</b> 本サイトの情報は投資助言ではなく、投資判断はご自身の責任で行ってください。</p>
</footer>
<script>(function(){{var hasExplicit=false;try{{var ss=document.styleSheets;for(var i=0;i<ss.length;i++){{try{{var r=ss[i].cssRules||ss[i].rules;if(!r)continue;for(var j=0;j<r.length;j++){{if(r[j].selectorText&&/body\.dark[^-]/.test(r[j].selectorText+' ')){{hasExplicit=true;break}}}}}}catch(e){{}}if(hasExplicit)break}}}}catch(e){{}}if(!hasExplicit){{var s=document.createElement('style');s.textContent='body.dark{{background:#0d1117!important;color:#e6edf3!important}}body.dark header,body.dark footer,body.dark nav.nav-bar{{background:#161b22!important;color:#e6edf3!important;border-color:#30363d!important}}body.dark .nav-btn{{background:#161b22!important;border-color:#30363d!important;color:#8b949e!important}}body.dark .nav-btn:hover{{border-color:#58a6ff!important;color:#58a6ff!important}}body.dark .nav-btn.current{{background:#1f6feb!important;border-color:#58a6ff!important;color:#fff!important}}body.dark .header-title,body.dark .header-meta,body.dark .header-meta span{{color:#e6edf3!important}}body.dark a{{color:#79c0ff!important}}body.dark h1,body.dark h2,body.dark h3,body.dark h4{{color:#e6edf3!important}}body.dark p,body.dark li,body.dark td{{color:#c9d1d9!important}}body.dark hr{{border-color:#30363d!important}}body.dark th{{background:#0d1117!important;color:#79c0ff!important}}body.dark #theme-toggle{{background:#161b22!important;border-color:#30363d!important;color:#fff!important}}body.dark *[style*="background:#fff"]:not(img),body.dark *[style*="background:#ffffff"]:not(img),body.dark *[style*="background-color:#fff"]:not(img),body.dark *[style*="background-color:#ffffff"]:not(img),body.dark *[style*="background:#f6f8fa"]:not(img),body.dark *[style*="background-color:#f6f8fa"]:not(img){{background:#161b22!important}}body.dark *[style*="border:1px solid #d0d7de"],body.dark *[style*="border-color:#d0d7de"]{{border-color:#30363d!important}}body.dark *[style*="color:#1f2328"],body.dark *[style*="color:#57606a"],body.dark *[style*="color:#6e7781"],body.dark *[style*="color:#424a53"]{{color:#e6edf3!important}}';document.head.appendChild(s)}}function setTheme(t){{document.body.classList.toggle('dark',t==='dark');var b=document.getElementById('theme-toggle');if(b)b.textContent=t==='dark'?'☀️':'🌙';try{{localStorage.setItem('theme',t)}}catch(e){{}}}}window.toggleTheme=function(){{setTheme(document.body.classList.contains('dark')?'light':'dark')}};var t='light';try{{t=localStorage.getItem('theme')||'light'}}catch(e){{}}setTheme(t);}})();</script>
<script src="site-search.js" defer></script>
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
            print("✅ market-health.html 生成完了")
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
            print("✅ hot-assets.html 生成完了")
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
            print("✅ preview.html 生成完了")
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
        print("✅ sitemap.xml / robots.txt 生成完了")
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

    # ── 自動記事生成（指標プレビュー＆週次戦略）──
    # 朝7時/夕方16時の自動更新と同時に、指標が3日以内なら告知記事を、
    # 日曜なら翌週戦略記事を生成＋GitHubへ直接アップロード。
    print("\n📰 自動記事生成チェック中...")
    try:
        import auto_indicator_preview
        auto_indicator_preview.main()
    except Exception as e:
        print(f"  ⚠️  auto_indicator_preview 実行エラー: {e}")
        import traceback; traceback.print_exc()

    try:
        import auto_weekly_strategy
        auto_weekly_strategy.main()
    except Exception as e:
        print(f"  ⚠️  auto_weekly_strategy 実行エラー: {e}")
        import traceback; traceback.print_exc()

    print("\n🎉 全処理完了！")


if __name__ == "__main__":
    main()
