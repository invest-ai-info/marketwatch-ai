"""
generate_youtube_summary.py — YouTube 投資チャンネル要約ページ生成

毎日 1 回 GitHub Actions から実行され、指定チャンネルから新着動画を取得・字幕抽出・
Gemini で要約して youtube-summary.html を生成する。
"""
import os
import sys
import re
import json
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

# Windows コンソール (cp932) でも絵文字を出せるようにする
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

JST = timezone(timedelta(hours=9))

# ─────────────────────────────────────────────
# 対象チャンネル
# (handle, channel_id, 表示名)
# ─────────────────────────────────────────────
CHANNELS = [
    ("@pivot00",             "UC8yHePe_RgUBE-waRWy6olw", "PIVOT 公式チャンネル"),
    ("@rehacq",              "UCG_oqDSlIYEspNpd2H4zWhw", "ReHacQ"),
    ("@tabbata",             "UC7sEB_ylMuHJD4TjF4Ag1nw", "たぱぞうの米国株投資"),
    ("@NewsPicks",           "UCfTnJmRQP79C4y_BMF_XrlA", "NewsPicks"),
    ("@yurumazu",            "UClDM5GP-nYn5gBvDryZDW9w", "ゆるまずの投資チャンネル"),
    ("@leveraged_NASDAQ100", "UCe1VbBy2kU_lMB6t4aJmukg", "レバナス1本リーマン"),
    ("@Joe_Bitcoin",         "UChHDspjk1RSMWXe36OyV5rg", "Joe Bitcoin"),
    ("@rakumachi",           "UCPMJKbrxtpARoTd1b49iUvA", "楽待 不動産投資"),
    ("@mabuchi-mariko",      "UCXhiUvJK_0uyLY1YvaSa0AQ", "馬渕磨理子"),
    ("@saki_kaigaihudousan", "UCpv0oCYCHywaOIsqh48MEVw", "Saki 海外不動産"),
]

MAX_VIDEOS = 5        # 1日に新規要約する本数（既要約はスキップ、これに含まない）
MAX_AGE_HOURS = 168   # 候補とする動画の最大経過時間（過去7日）
TRANSCRIPT_MAX_CHARS = 12000  # Gemini に渡す字幕の最大文字数
RSS_RETRY = 3         # RSS 取得のリトライ回数
RSS_RETRY_DELAY = 5   # リトライ間隔（秒）
DATA_FILE = "youtube-summary-data.json"  # 要約データの永続化先
KEEP_DAYS = 3         # 過去何日分の要約を保持するか


# ─────────────────────────────────────────────
# RSS から動画リスト取得
# ─────────────────────────────────────────────
def fetch_channel_videos(channel_id, channel_name):
    """RSS フィードから最新動画を取得（リトライ付き）"""
    import feedparser
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    # GitHub Actions の IP は YouTube に弾かれやすいのでブラウザ風 UA で試行
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]
    content = None
    last_err = None
    for attempt in range(RSS_RETRY):
        ua = user_agents[attempt % len(user_agents)]
        # Accept ヘッダーは付けない（YouTube が 406 を返すケースあり）
        req = urllib.request.Request(url, headers={"User-Agent": ua})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                content = r.read()
                if content and len(content) > 100:
                    break
                last_err = f"empty body ({len(content) if content else 0} bytes)"
        except urllib.error.HTTPError as e:
            last_err = f"HTTP {e.code}"
            # 4xx は一般にリトライ無意味だが、403/429 はレート制限の可能性で1回だけリトライ
            if e.code not in (429, 403) and not (500 <= e.code < 600):
                break
        except Exception as e:
            last_err = f"{type(e).__name__}: {str(e)[:60]}"
        if attempt < RSS_RETRY - 1:
            time.sleep(RSS_RETRY_DELAY * (attempt + 1))
    if not content or len(content) < 100:
        print(f"⚠️ {channel_name} 取得失敗（{RSS_RETRY}回試行・最終: {last_err}）")
        return []
    feed = feedparser.parse(content)
    videos = []
    for e in feed.entries:
        vid = e.get("yt_videoid", "")
        if not vid:
            link = e.get("link", "")
            if "v=" in link:
                vid = link.split("v=")[-1].split("&")[0]
        if not vid:
            continue
        videos.append({
            "video_id": vid,
            "title": e.get("title", ""),
            "url": e.get("link", ""),
            "published": e.get("published", ""),
            "channel_name": channel_name,
            "channel_id": channel_id,
        })
    return videos


def load_existing_data():
    """既存の要約データを JSON から読み込む"""
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, encoding="utf-8") as f:
            data = json.load(f)
        videos = data.get("videos", [])
        print(f"📦 {DATA_FILE} から {len(videos)} 件の既存要約を読み込み")
        return videos
    except Exception as e:
        print(f"⚠️ {DATA_FILE} 読み込み失敗、新規開始: {e}")
        return []


def save_data(videos):
    """要約データを JSON に保存"""
    payload = {
        "videos": videos,
        "saved_at": datetime.now(JST).isoformat(timespec="seconds"),
        "keep_days": KEEP_DAYS,
    }
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"💾 {DATA_FILE} に {len(videos)} 件を保存")


def prune_old_summaries(videos, keep_days):
    """generated_at が keep_days より古いものを除外"""
    cutoff = datetime.now(timezone.utc) - timedelta(days=keep_days)
    fresh = []
    pruned = 0
    for v in videos:
        gen_at_str = v.get("generated_at", "")
        try:
            gen_at = datetime.fromisoformat(gen_at_str.replace("Z", "+00:00"))
            if gen_at.tzinfo is None:
                gen_at = gen_at.replace(tzinfo=JST)
            if gen_at.astimezone(timezone.utc) >= cutoff:
                fresh.append(v)
            else:
                pruned += 1
        except Exception:
            # 日付不明は捨てる
            pruned += 1
    if pruned:
        print(f"🗑️  {pruned} 件を期限切れで削除（{keep_days} 日経過）")
    return fresh


# ─────────────────────────────────────────────
# YouTube Shorts 判定
# ─────────────────────────────────────────────
SHORTS_TITLE_MARKERS = (
    "#shorts", "#short", "#ショート",
    "【shorts】", "【short】", "【ショート】",
    "shorts動画", "short動画",
)


def is_youtube_short(video_id, title="", description=""):
    """YouTube Shorts かを判定。
    1) タイトル/説明文に Shorts マーカーがあれば即 True（早期判定で HTTP 節約）
    2) `/shorts/{id}` に直接アクセス。200 ならショート、リダイレクトされれば通常動画
    """
    text = (title + " " + description).lower()
    if any(m in text for m in SHORTS_TITLE_MARKERS):
        return True

    # URL ベース確認（リダイレクトを追わない）
    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None

    opener = urllib.request.build_opener(_NoRedirect())
    url = f"https://www.youtube.com/shorts/{video_id}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
    )
    try:
        response = opener.open(req, timeout=8)
        # 2xx = Shorts ページが存在
        return 200 <= response.status < 300
    except urllib.error.HTTPError as e:
        # 30x リダイレクト = /watch?v=... へ転送される = 通常動画
        return False
    except Exception:
        # ネットワークエラー時は判定不能 → False（除外しない）
        return False


def hours_since(published_str):
    """発行時刻から経過時間（時間単位）。パース失敗時は -1"""
    if not published_str:
        return -1
    try:
        dt = parsedate_to_datetime(published_str)
    except Exception:
        try:
            dt = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
        except Exception:
            return -1
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - dt).total_seconds() / 3600.0


# ─────────────────────────────────────────────
# 字幕取得
# ─────────────────────────────────────────────
def get_transcript(video_id):
    """字幕を取得。日本語優先、なければ英語、それでもなければ利用可能な言語から1つ"""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        print("⚠️ youtube-transcript-api 未インストール")
        return None

    api = YouTubeTranscriptApi()

    # 試行1: 指定言語の優先順位（日本語 → 英語 → 中国語）
    for langs in (["ja", "ja-JP"], ["en", "en-US", "en-GB"], ["zh", "zh-CN", "zh-TW"]):
        try:
            t = api.fetch(video_id, languages=langs)
            return " ".join([s.text for s in t])
        except Exception:
            continue

    # 試行2: 利用可能な言語をリストアップ → 最初の1つを取得
    try:
        transcripts = api.list(video_id)
        for t_info in transcripts:
            try:
                t = t_info.fetch()
                return " ".join([s.text for s in t])
            except Exception:
                continue
    except Exception as e:
        print(f"    ⚠️ 字幕リスト取得失敗: {type(e).__name__}: {str(e)[:80]}")

    return None


# ─────────────────────────────────────────────
# Gemini で要約
# ─────────────────────────────────────────────
SUMMARY_PROMPT_VIDEO = """あなたは日本人投資家向けの動画要約ライターです。以下の YouTube 動画を視聴・分析し、日本人投資家にとって有益な情報を抽出して要約してください。

【動画情報】
チャンネル: {channel_name}
タイトル: {title}

【出力フォーマット】（このフォーマットを厳守。各セクションのタイトル文字も含めて出力）
3行サマリー:
- (1行目: 動画の核心メッセージ)
- (2行目: 注目すべき具体的データ・銘柄・金額・指標)
- (3行目: 日本人投資家にとっての示唆)

重要トピック:
- (箇条書きで3〜5個。具体的に)
- ...

マーケット示唆:
(1〜2文。この情報を踏まえて日本人投資家はどう行動・思考すべきか)

【注意】
- 動画で明示されていない情報は推測しない
- 過度な断定は避け、「〜の可能性」「〜と示唆」など慎重な表現を使う
- 日本語で出力
- 各セクションのタイトル文字（"3行サマリー:" など）は必ず行頭に置く"""


SUMMARY_PROMPT_TEXT = """あなたは日本人投資家向けの動画紹介ライターです。以下の YouTube 動画情報（タイトルと説明文のみ・動画内容は未視聴）を読み、推測できる範囲で投資家向けの紹介文を作成してください。

【動画情報】
チャンネル: {channel_name}
タイトル: {title}

【説明文】
{description}

【出力フォーマット】（このフォーマットを厳守）
3行サマリー:
- (1行目: タイトルから推測される核心テーマ)
- (2行目: 扱われそうな具体的トピック・銘柄・指標)
- (3行目: 日本人投資家にとっての示唆)

重要トピック:
- (タイトル・説明から推測される話題 3〜5個)

マーケット示唆:
(1〜2文。動画を見た上で考えるべき点として)

【注意】
- 動画本編は未視聴である前提で、「〜と思われる」「〜の可能性」「〜について解説していると見られる」など慎重な表現を使う
- タイトルや説明にない情報の捏造はしない
- 日本語で出力"""


TEXT_MODEL_CANDIDATES = ("gemini-2.0-flash", "gemini-2.5-flash", "gemini-flash-latest")
VIDEO_MODEL_CANDIDATES = ("gemini-2.0-flash", "gemini-2.5-flash")


def summarize_with_gemini_video(video_url, title, channel_name, api_key):
    """Gemini で YouTube 動画を直接要約（複数モデルで試行）"""
    try:
        import google.generativeai as genai
    except ImportError:
        return None
    genai.configure(api_key=api_key)
    prompt = SUMMARY_PROMPT_VIDEO.format(channel_name=channel_name, title=title)
    last_err = ""
    for model_name in VIDEO_MODEL_CANDIDATES:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content([
                {"file_data": {"file_uri": video_url, "mime_type": "video/youtube"}},
                prompt,
            ])
            text = (response.text or "").strip()
            if text:
                return text
        except Exception as e:
            last_err = f"{model_name}: {type(e).__name__}: {str(e)[:80]}"
            continue
    print(f"    ⚠️ video 要約失敗（全モデル）: {last_err}")
    return None


def summarize_text_only(title, channel_name, description, api_key):
    """フォールバック：タイトル + 説明文だけで要約（動画 URL 機能が使えない場合）"""
    try:
        import google.generativeai as genai
    except ImportError:
        return None
    genai.configure(api_key=api_key)
    prompt = SUMMARY_PROMPT_TEXT.format(
        channel_name=channel_name,
        title=title,
        description=description or "（説明文なし）",
    )
    last_err = ""
    for model_name in TEXT_MODEL_CANDIDATES:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            text = (response.text or "").strip()
            if text:
                return text
        except Exception as e:
            last_err = f"{model_name}: {type(e).__name__}: {str(e)[:80]}"
            continue
    print(f"    ⚠️ text 要約失敗（全モデル）: {last_err}")
    return None


# ─────────────────────────────────────────────
# Gemini 出力のパース（3セクションに分割）
# ─────────────────────────────────────────────
def parse_summary(text):
    """Gemini の出力を {three_lines, topics, implication} に分割"""
    if not text:
        return None
    three_lines = []
    topics = []
    implication = ""
    current = None
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if re.match(r"^3行?サマリー[:：]", s):
            current = "three"
            continue
        if re.match(r"^重要トピック[:：]", s):
            current = "topics"
            continue
        if re.match(r"^マーケット示唆[:：]", s):
            current = "impl"
            continue
        if current == "three":
            three_lines.append(re.sub(r"^[-・]\s*", "", s))
        elif current == "topics":
            topics.append(re.sub(r"^[-・]\s*", "", s))
        elif current == "impl":
            implication += s + " "
    return {
        "three_lines": three_lines[:3],
        "topics": topics[:6],
        "implication": implication.strip(),
        "raw": text,
    }


# ─────────────────────────────────────────────
# HTML 生成
# ─────────────────────────────────────────────
def fmt_pub_jst(pub_str):
    try:
        dt = parsedate_to_datetime(pub_str).astimezone(JST)
        return dt.strftime("%Y-%m-%d %H:%M JST")
    except Exception:
        return pub_str[:16]


def build_video_card(v):
    """1動画分のカード HTML"""
    summary = v.get("summary_parsed") or {}
    three_lines = summary.get("three_lines", [])
    topics = summary.get("topics", [])
    implication = summary.get("implication", "")

    three_html = "".join(f"<li>{l}</li>" for l in three_lines)
    topics_html = "".join(f"<li>{t}</li>" for t in topics)
    pub = fmt_pub_jst(v.get("published", ""))
    thumb = f"https://img.youtube.com/vi/{v['video_id']}/mqdefault.jpg"

    return f"""<article class="video-card">
  <div class="video-thumb-wrap">
    <a href="{v['url']}" target="_blank" rel="noopener">
      <img src="{thumb}" alt="動画サムネイル" loading="lazy">
      <div class="video-play">▶</div>
    </a>
  </div>
  <div class="video-body">
    <div class="video-channel">📺 {v['channel_name']}</div>
    <h3 class="video-title"><a href="{v['url']}" target="_blank" rel="noopener">{v['title']}</a></h3>
    <div class="video-pub">公開: {pub}</div>

    <div class="summary-section summary-3lines">
      <div class="summary-section-title">⚡ 3行サマリー</div>
      <ul>{three_html}</ul>
    </div>

    <div class="summary-section summary-topics">
      <div class="summary-section-title">📋 重要トピック</div>
      <ul>{topics_html}</ul>
    </div>

    <div class="summary-section summary-impl">
      <div class="summary-section-title">💡 マーケット示唆</div>
      <p>{implication}</p>
    </div>

    <a class="video-watch" href="{v['url']}" target="_blank" rel="noopener">▶ YouTube で視聴 →</a>
  </div>
</article>"""


PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>📺 投資系 YouTube 要約 — 日次AI要約で時短キャッチアップ | MarketWatch AI</title>
  <meta name="description" content="日本人投資家向けの厳選YouTube投資チャンネルから、毎日5本の新着動画を AI（Gemini）で要約。3行サマリー・重要トピック・マーケット示唆を一覧で時短キャッチアップ。">
  <meta name="keywords" content="YouTube,投資,要約,AI,Gemini,日本人投資家,PIVOT,NewsPicks,たぱぞう,ReHacQ">
  <link rel="canonical" href="https://marketwatch-jp.com/youtube-summary.html">
  <meta property="og:type" content="website">
  <meta property="og:title" content="📺 投資系 YouTube 要約 — 日次AI要約で時短キャッチアップ">
  <meta property="og:description" content="厳選YouTube投資チャンネルの新着動画を AI が毎日要約。3行サマリー・重要トピック・マーケット示唆。">
  <meta property="og:url" content="https://marketwatch-jp.com/youtube-summary.html">
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
    .nav-bar{{display:flex;flex-wrap:wrap;gap:10px;justify-content:center;margin-bottom:32px}}
    .nav-btn{{display:inline-flex;align-items:center;justify-content:center;gap:8px;padding:11px 20px;background:#f6f8fa;border:1px solid #d0d7de;border-radius:10px;color:#57606a;text-decoration:none;font-size:.95rem;font-weight:600;transition:all .2s;min-width:160px}}
    .nav-btn:hover{{border-color:#0969da;color:#0969da}}
    .nav-btn.current{{background:#0969da;border-color:#0969da;color:#fff}}
    .page-header{{background:linear-gradient(135deg,#ddf4ff,#f6f8fa);border:1px solid #d0d7de;border-radius:12px;padding:24px 32px;margin-bottom:28px}}
    .page-header h1{{font-size:1.6rem;color:#0969da;margin-bottom:10px;line-height:1.4}}
    .page-header .page-tagline{{font-size:.95rem;color:#1f2328;line-height:1.7;margin-bottom:10px;padding-bottom:10px;border-bottom:1px solid #d0d7de}}
    .page-header .page-tagline strong{{color:#0969da}}
    .page-header .page-meta{{font-size:.85rem;color:#57606a}}
    .channels-info{{background:#ffffff;border:1px solid #d0d7de;border-radius:10px;padding:14px 20px;margin-bottom:24px;font-size:.85rem;color:#424a53}}
    .channels-info strong{{color:#0969da}}
    .day-section{{margin-bottom:36px}}
    .day-title{{font-size:1.15rem;color:#0969da;border-bottom:2px solid #d0d7de;padding-bottom:8px;margin-bottom:16px}}
    .video-card{{display:grid;grid-template-columns:340px 1fr;gap:24px;background:#f6f8fa;border:1px solid #d0d7de;border-radius:12px;padding:24px;margin-bottom:24px;box-shadow:0 2px 6px rgba(0,0,0,.04)}}
    .video-thumb-wrap{{position:relative;border-radius:10px;overflow:hidden;height:fit-content}}
    .video-thumb-wrap img{{width:100%;height:auto;display:block;border-radius:10px}}
    .video-thumb-wrap a{{display:block;position:relative}}
    .video-play{{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);background:rgba(0,0,0,.7);color:#fff;width:60px;height:60px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:1.5rem;pointer-events:none;transition:background .15s}}
    .video-thumb-wrap a:hover .video-play{{background:#cf222e}}
    .video-body{{display:flex;flex-direction:column}}
    .video-channel{{font-size:.85rem;color:#0969da;font-weight:600;margin-bottom:6px}}
    .video-title{{font-size:1.15rem;line-height:1.4;margin-bottom:8px}}
    .video-title a{{color:#1f2328;text-decoration:none}}
    .video-title a:hover{{color:#0969da}}
    .video-pub{{font-size:.78rem;color:#57606a;margin-bottom:14px}}
    .summary-section{{background:#ffffff;border:1px solid #d0d7de;border-left:4px solid #0969da;border-radius:8px;padding:12px 16px;margin-bottom:10px}}
    .summary-section.summary-3lines{{border-left-color:#1a7f37}}
    .summary-section.summary-topics{{border-left-color:#0969da}}
    .summary-section.summary-impl{{border-left-color:#9a6700;background:#fffaf0}}
    .summary-section-title{{font-size:.85rem;font-weight:700;color:#0969da;margin-bottom:6px}}
    .summary-section.summary-3lines .summary-section-title{{color:#1a7f37}}
    .summary-section.summary-impl .summary-section-title{{color:#9a6700}}
    .summary-section ul{{padding-left:20px;font-size:.9rem;color:#424a53;line-height:1.7}}
    .summary-section ul li{{margin-bottom:4px}}
    .summary-section p{{font-size:.92rem;color:#424a53;line-height:1.7}}
    .video-watch{{display:inline-block;margin-top:auto;padding:10px 16px;background:#cf222e;color:#fff;text-decoration:none;border-radius:6px;font-size:.88rem;font-weight:600;text-align:center;transition:background .15s}}
    .video-watch:hover{{background:#a40e1f}}
    .empty-msg{{background:#fff8c5;border:1px solid #d29922;border-radius:10px;padding:18px 24px;color:#7b5a00;font-size:.95rem}}
    footer{{background:#f6f8fa;border-top:1px solid #d0d7de;padding:20px 32px;text-align:center;font-size:.78rem;color:#6e7781;margin-top:40px}}
    footer a{{color:#0969da;text-decoration:none}}
    @media(max-width:780px){{
      .video-card{{grid-template-columns:1fr}}
      .video-thumb-wrap img{{width:100%;max-width:480px;margin:0 auto}}
      main{{padding:20px 14px}}
    }}
    @media(max-width:600px){{
      .nav-bar{{display:grid;grid-template-columns:1fr 1fr;gap:8px}}
      .nav-btn{{min-width:0;width:100%;padding:10px 8px;font-size:.82rem}}
    }}
  </style>
</head>
<body>
<button id="theme-toggle" onclick="toggleTheme()" aria-label="テーマ切替" style="position:fixed;top:16px;right:16px;width:42px;height:42px;border-radius:50%;border:1px solid #d0d7de;background:#fff;cursor:pointer;z-index:9999;box-shadow:0 2px 8px rgba(0,0,0,.1);font-size:18px;display:flex;align-items:center;justify-content:center">🌙</button>
<header>
  <div class="header-inner">
    <div class="header-title">📊 MarketWatch AI</div>
    <div class="header-meta">日本人投資家のためのマーケット情報サイト</div>
  </div>
</header>
<main>
  <nav class="nav-bar">
    <a class="nav-btn" href="index.html">🏠 トップページ</a>
    <a class="nav-btn" href="calendar.html">📅 経済カレンダー</a>
    <a class="nav-btn" href="charts.html">📈 50年チャート</a>
    <a class="nav-btn" href="guides.html">📚 解説記事</a>
    <a class="nav-btn current" href="youtube-summary.html">📺 YouTube要約</a>
    <a class="nav-btn" href="market-health.html">🩺 市場健康度</a>
    <a class="nav-btn" href="hot-assets.html">🔥 出来高急増</a>
  </nav>

  <div class="page-header">
    <h1>📺 投資系 YouTube 要約 — 忙しい人のための 5 分キャッチアップ</h1>
    <div class="page-tagline">「動画を見る時間がない」を解決。<strong>厳選 {n_channels} チャンネルの新着動画を AI が毎朝自動要約</strong>。各動画の核心メッセージ・重要トピック・日本人投資家への示唆を、ひと目で把握できます。</div>
    <div class="page-meta">最終更新: {updated_at} ／ 要約 AI: Google Gemini</div>
  </div>

  <div class="channels-info">
    <strong>対象チャンネル（{n_channels} 件）:</strong> {channel_list}
  </div>

  {videos_html}

</main>

<footer>
  © 2026 MarketWatch AI ｜ <a href="index.html">トップに戻る</a> ｜ <a href="contact.html">お問い合わせ・削除要請</a><br>
  動画の著作権は各チャンネルに帰属します。本ページは AI による要約・紹介であり、内容に誤りがある場合があります。詳細・正確な情報は元動画でご確認ください。<br>
  <strong>チャンネル運営者の方へ：</strong> 当ページからのご自身のチャンネル/動画の掲載除外をご希望の場合は <a href="contact.html">お問い合わせフォーム</a> よりご連絡ください。速やかに対応いたします。
</footer>

<script>
(function(){{var hasExplicit=false;try{{var ss=document.styleSheets;for(var i=0;i<ss.length;i++){{try{{var r=ss[i].cssRules||ss[i].rules;if(!r)continue;for(var j=0;j<r.length;j++){{if(r[j].selectorText&&/body\\.dark[^-]/.test(r[j].selectorText+' ')){{hasExplicit=true;break}}}}}}catch(e){{}}if(hasExplicit)break}}}}catch(e){{}}if(!hasExplicit){{var s=document.createElement('style');s.textContent='body.dark{{background:#0d1117!important;color:#e6edf3!important}}body.dark header,body.dark footer,body.dark nav.nav-bar{{background:#161b22!important;color:#e6edf3!important;border-color:#30363d!important}}body.dark .nav-btn{{background:#161b22!important;border-color:#30363d!important;color:#8b949e!important}}body.dark .nav-btn:hover{{border-color:#58a6ff!important;color:#58a6ff!important}}body.dark .nav-btn.current{{background:#1f6feb!important;border-color:#58a6ff!important;color:#fff!important}}body.dark .header-title,body.dark .header-meta,body.dark .page-header h1{{color:#e6edf3!important}}body.dark a{{color:#79c0ff!important}}body.dark .video-card,body.dark .channels-info,body.dark .page-header{{background:#161b22!important;border-color:#30363d!important}}body.dark .video-title a{{color:#e6edf3!important}}body.dark .summary-section{{background:#0d1117!important;border-color:#30363d!important}}body.dark .summary-section.summary-impl{{background:#1c1810!important}}body.dark .summary-section ul,body.dark .summary-section p,body.dark .channels-info,body.dark .video-pub,body.dark .page-meta{{color:#c9d1d9!important}}body.dark #theme-toggle{{background:#161b22!important;border-color:#30363d!important;color:#fff!important}}';document.head.appendChild(s)}}function setTheme(t){{document.body.classList.toggle('dark',t==='dark');var b=document.getElementById('theme-toggle');if(b)b.textContent=t==='dark'?'☀️':'🌙';try{{localStorage.setItem('theme',t)}}catch(e){{}}}}window.toggleTheme=function(){{setTheme(document.body.classList.contains('dark')?'light':'dark')}};var t='light';try{{t=localStorage.getItem('theme')||'light'}}catch(e){{}}setTheme(t);}})();
</script>
</body>
</html>
"""


def build_html(summaries):
    """全要約から HTML ページを生成（generated_at 日付でグループ化）"""
    now_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    channel_list = " / ".join([c[2] for c in CHANNELS])
    today_str = datetime.now(JST).strftime("%Y-%m-%d")
    if not summaries:
        videos_html = '<div class="empty-msg">直近の対象チャンネルから新着動画がなかったか、要約に失敗しました。次回更新をお待ちください。</div>'
    else:
        # generated_at の YYYY-MM-DD でグループ化
        groups = {}
        for v in summaries:
            gen_at = v.get("generated_at", "")
            try:
                dt = datetime.fromisoformat(gen_at.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=JST)
                day = dt.astimezone(JST).strftime("%Y-%m-%d")
            except Exception:
                day = "unknown"
            groups.setdefault(day, []).append(v)
        # 日付の新しい順
        sorted_days = sorted(groups.keys(), reverse=True)
        parts = []
        for day in sorted_days:
            vids = groups[day]
            # 各日内でも公開日の新しい順
            vids.sort(key=lambda v: v.get("published", ""), reverse=True)
            if day == "unknown":
                label = "📅 日付不明"
            elif day == today_str:
                label = f"🆕 本日（{day}）追加 — {len(vids)} 本"
            else:
                label = f"📅 {day} 追加 — {len(vids)} 本"
            parts.append(f'<div class="day-section"><h2 class="day-title">{label}</h2>')
            parts.extend(build_video_card(v) for v in vids)
            parts.append("</div>")
        videos_html = "\n".join(parts)
    return PAGE_TEMPLATE.format(
        updated_at=now_jst,
        n_channels=len(CHANNELS),
        channel_list=channel_list,
        videos_html=videos_html,
    )


# ─────────────────────────────────────────────
# メイン
# ─────────────────────────────────────────────
def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY が未設定です")
        sys.exit(1)

    # 既存データロード + 期限切れ削除
    existing = load_existing_data()
    existing = prune_old_summaries(existing, KEEP_DAYS)
    existing_ids = {v.get("video_id") for v in existing if v.get("video_id")}
    print(f"📦 過去 {KEEP_DAYS} 日分の既存要約: {len(existing)} 件\n")

    # 候補収集（既存 video_id は除外）
    if os.environ.get("TEST_MODE", "").lower() in ("1", "true", "yes"):
        print("🧪 TEST_MODE: ハードコード URL で Gemini 動作確認")
        candidates = [
            {
                "video_id": "rUtIgnvEhx0",
                "url": "https://www.youtube.com/watch?v=rUtIgnvEhx0",
                "title": "リアルゲイトの増資が、\"ポジティブ材料\"なのか解説します!!",
                "channel_name": "たぱぞうの米国株投資",
                "channel_id": "UC7sEB_ylMuHJD4TjF4Ag1nw",
                "published": "2026-05-16T00:00:00Z",
            },
        ]
    else:
        print(f"📡 {len(CHANNELS)} チャンネルから動画候補を収集...")
        candidates = []
        for handle, cid, name in CHANNELS:
            vids = fetch_channel_videos(cid, name)
            recent = [v for v in vids if 0 <= hours_since(v.get("published", "")) <= MAX_AGE_HOURS]
            print(f"  {handle:25} {len(vids)}本 中 {len(recent)}本が直近 {MAX_AGE_HOURS}h 以内")
            candidates.extend(recent)
            time.sleep(1)
        candidates.sort(key=lambda v: v.get("published", ""), reverse=True)

    # 既要約は除外
    new_candidates = [v for v in candidates if v.get("video_id") not in existing_ids]
    skipped_existing = len(candidates) - len(new_candidates)
    if skipped_existing:
        print(f"⏭️  {skipped_existing} 本は既に要約済みのためスキップ")

    # Shorts を除外して上位 MAX_VIDEOS を選ぶ
    print(f"\n🔍 候補から Shorts を除外して上位 {MAX_VIDEOS} 本を選定中...")
    targets = []
    shorts_skipped = 0
    for v in new_candidates:
        if len(targets) >= MAX_VIDEOS:
            break
        if is_youtube_short(v["video_id"], v.get("title", ""), v.get("description", "")):
            shorts_skipped += 1
            print(f"  ⏭️  Shorts スキップ: {v['title'][:50]}")
            continue
        targets.append(v)
    if shorts_skipped:
        print(f"  📐 Shorts {shorts_skipped} 本を除外")
    print(f"\n🎯 通常動画 {len(targets)} 本を要約します\n")

    new_summaries = []
    video_url_works = None  # None=未判定、True/False=判定済み
    now_iso = datetime.now(JST).isoformat(timespec="seconds")
    for i, v in enumerate(targets, 1):
        print(f"[{i}/{len(targets)}] ▶ {v['channel_name']}: {v['title'][:60]}")
        summary_text = None
        method_used = None
        if video_url_works is not False:
            print(f"    🎬 動画 URL 方式 (Gemini video) で要約中...")
            summary_text = summarize_with_gemini_video(v["url"], v["title"], v["channel_name"], api_key)
            if summary_text:
                video_url_works = True
                method_used = "video"
            elif video_url_works is None:
                video_url_works = False
                print(f"    ℹ️ 動画 URL 方式は使えないため、以降はタイトル+説明文要約にフォールバック")
        if not summary_text:
            print(f"    📝 テキスト要約 (タイトル + 説明文) で生成中...")
            summary_text = summarize_text_only(v["title"], v["channel_name"], v.get("description", ""), api_key)
            if summary_text:
                method_used = "text"
        if not summary_text:
            print(f"    ⏭️ 要約失敗、スキップ")
            continue
        v["summary_raw"] = summary_text
        v["summary_parsed"] = parse_summary(summary_text)
        v["summary_method"] = method_used
        v["generated_at"] = now_iso  # ← 永続化用タイムスタンプ
        new_summaries.append(v)
        print(f"    ✅ 要約完了 [{method_used}] ({len(summary_text)} 字)")
        time.sleep(2)

    # 既存 + 新規 を統合（video_id で重複排除、新しい方を優先）
    combined_map = {}
    for v in existing:  # 古いものから入れて
        if v.get("video_id"):
            combined_map[v["video_id"]] = v
    for v in new_summaries:  # 新規で上書き
        combined_map[v["video_id"]] = v
    combined = list(combined_map.values())

    # 保存（永続化）
    save_data(combined)

    # HTML 生成（公開日順、新しい順）
    combined.sort(key=lambda v: v.get("published", ""), reverse=True)
    html = build_html(combined)
    with open("youtube-summary.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\n✅ youtube-summary.html を生成しました（合計 {len(combined)} 本、新規 {len(new_summaries)} 本）")


if __name__ == "__main__":
    main()
