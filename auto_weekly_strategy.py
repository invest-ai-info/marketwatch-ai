# -*- coding: utf-8 -*-
"""
週次投資戦略記事 自動生成スクリプト
====================================
毎週日曜日18時（JST）に翌週（月〜金）の投資戦略記事を自動生成する。

使い方:
    python auto_weekly_strategy.py            # 日曜日のみ実行
    python auto_weekly_strategy.py --force    # 曜日関係なく強制実行

GitHub Actionsから毎日呼び出してOK（日曜以外はスキップ）。
INDICATOR_SCHEDULE は auto_indicator_preview.py から自動取得。
"""
import os
import re
import sys
import time
import json
import urllib.request
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

JST = timezone(timedelta(hours=9))

# auto_indicator_preview.py から指標スケジュールを取得
try:
    from auto_indicator_preview import INDICATOR_SCHEDULE
except ImportError:
    INDICATOR_SCHEDULE = {}

# ─────────────────────────────────────────────
# 週末動向収集用の高品質日本語 RSS ソース
# ─────────────────────────────────────────────
NEWS_RSS_FEEDS = [
    ("Bloomberg Markets", "https://feeds.bloomberg.com/markets/news.rss"),
    ("ロイター日本",       "https://assets.wor.jp/rss/rdf/reuters/top.rdf"),
    ("NHK経済",            "https://www3.nhk.or.jp/rss/news/cat5.xml"),
    ("東洋経済オンライン",  "https://toyokeizai.net/list/feed/rss"),
]


def fetch_recent_news(hours=72, max_per_source=15):
    """過去 N 時間以内のニュースを RSS から収集"""
    try:
        import feedparser
    except ImportError:
        print("  ⚠️ feedparser 未インストール、週末ニュース取得スキップ")
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    items = []
    for source_name, url in NEWS_RSS_FEEDS:
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            )
            with urllib.request.urlopen(req, timeout=20) as r:
                content = r.read()
            feed = feedparser.parse(content)
            for entry in feed.entries[:max_per_source]:
                pub_str = entry.get("published", "") or entry.get("updated", "")
                if not pub_str:
                    continue
                try:
                    pub_dt = parsedate_to_datetime(pub_str)
                    if pub_dt.tzinfo is None:
                        pub_dt = pub_dt.replace(tzinfo=timezone.utc)
                except Exception:
                    continue
                if pub_dt < cutoff:
                    continue
                title = re.sub(r"<[^>]+>", "", entry.get("title", "")).strip()
                if title:
                    items.append({"source": source_name, "title": title, "pub": pub_dt})
        except Exception as e:
            print(f"  ⚠️ RSS {source_name} エラー: {type(e).__name__}: {str(e)[:60]}")
        time.sleep(0.5)
    items.sort(key=lambda x: x["pub"], reverse=True)
    return items


def generate_weekend_section_with_ai(today_jst, week_start, week_end, indicators):
    """Gemini で週末動向+来週への注目ポイント HTML セクションを生成。
    API キーがない場合や失敗時は None を返す（既存テンプレートのみで生成される）。
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("  ℹ️ GEMINI_API_KEY 未設定、AI 週末セクションはスキップ")
        return None
    try:
        import google.generativeai as genai
    except ImportError:
        print("  ⚠️ google-generativeai 未インストール、AI 週末セクションはスキップ")
        return None

    news_items = fetch_recent_news(hours=72)
    print(f"  📡 直近 72h ニュース: {len(news_items)} 件取得")
    if not news_items:
        return None

    news_text = "\n".join(
        [f"- [{n['source']}] {n['title']}" for n in news_items[:25]]
    )
    if indicators:
        ind_text = "\n".join(
            [
                f"- {ev['date']} {ev['info'].get('emoji', '')} {ev['info'].get('name_short', '')}（重要度 {'★' * ev['info'].get('importance', 1)}）"
                for ev in indicators
            ]
        )
    else:
        ind_text = "（来週は注目度の高い指標発表なし）"

    week_label = f"{week_start.strftime('%Y-%m-%d')} 〜 {week_end.strftime('%Y-%m-%d')}"
    today_str = today_jst.strftime("%Y-%m-%d (%a)")
    prompt = f"""あなたは日本人個人投資家向けの投資戦略アナリストです。

【基準日】今日は {today_str}（日本時間）です。この記事は来週（{week_label}）向けに書きます。
過去 72 時間（週末を含む）に流れたニュースと、来週の重要指標スケジュールを踏まえ、
来週（{week_label}）の注目ポイントを簡潔にまとめてください。

【直近 72h の主要ニュース見出し】
{news_text}

【来週の重要指標】
{ind_text}

【出力フォーマット】（このフォーマットを厳守。プレーンテキストのみ。HTML/Markdownは使わない）
===週末動向の3行サマリー===
- (週末で最も市場に影響しそうなトピック1)
- (トピック2)
- (トピック3)

===来週ココに注目（3〜5項目）===
- (具体的に。指標・地政学・決算・要人発言などから)
- ...

===日本人投資家へのひと言===
(2〜3文。NISA/iDeCo・為替・日本株への波及視点を意識して、慎重な口調で。「〜の可能性」「〜要警戒」など)

【注意】
- 過度な断定や予想は避ける（「〜の可能性」「〜要注意」など慎重に）
- ニュースに明示されていない情報の捏造はしない
- 日付・曜日は【基準日】と【来週の重要指標】に書かれたものだけを使う。記憶や推測で具体的な日付・曜日を書かない（不確実なら「来週前半」「週半ば」など相対表現にする）
- 数字（価格目線）は具体的に書くが、根拠が薄ければ範囲表現にする
- 日本語のみ
- セクション見出し（"===..."）は必ず行頭にそのまま書く"""

    genai.configure(api_key=api_key)
    last_err = ""
    for model_name in ("gemini-2.0-flash", "gemini-2.5-flash"):
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            text = (response.text or "").strip()
            if text:
                print(f"  ✅ AI 週末セクション生成 ({model_name}, {len(text)} 字)")
                return _render_weekend_section_html(text, news_items)
        except Exception as e:
            last_err = f"{model_name}: {type(e).__name__}: {str(e)[:80]}"
            continue
    print(f"  ⚠️ AI 週末セクション生成失敗: {last_err}")
    return None


def _render_weekend_section_html(ai_text, news_items):
    """AI が出力したプレーンテキストを、既存 CSS にあわせた HTML セクションに変換"""
    sections = {"weekend": [], "watch": [], "msg": ""}
    current = None
    for line in ai_text.splitlines():
        s = line.strip()
        if not s:
            continue
        if "週末動向" in s and "===" in s:
            current = "weekend"; continue
        if "来週ココに注目" in s and "===" in s:
            current = "watch"; continue
        if "日本人投資家へのひと言" in s and "===" in s:
            current = "msg"; continue
        if current == "weekend":
            sections["weekend"].append(re.sub(r"^[-・*]\s*", "", s))
        elif current == "watch":
            sections["watch"].append(re.sub(r"^[-・*]\s*", "", s))
        elif current == "msg":
            sections["msg"] += s + " "

    weekend_html = "".join(f"<li>{l}</li>" for l in sections["weekend"][:5])
    watch_html = "".join(f"<li>{l}</li>" for l in sections["watch"][:6])
    msg_html = sections["msg"].strip()

    # 参考にしたニュースの代表 5 件
    used_news_html = ""
    for n in news_items[:5]:
        used_news_html += f'<li><span style="color:#0969da;font-weight:600">[{n["source"]}]</span> {n["title"]}</li>'

    section_html = f"""
    <h2>🌐 週末動向 × 来週の作戦（AI 分析）</h2>
    <div class="info-box" style="border-left-color:#1a7f37;background:#dafbe1;color:#1a7f37">
      <strong>📰 週末動向の3行サマリー</strong>
      <ul style="margin-top:8px;padding-left:22px">{weekend_html}</ul>
    </div>
    <div class="highlight-box">
      <strong>👀 来週ココに注目</strong>
      <ul style="margin-top:8px;padding-left:22px">{watch_html}</ul>
    </div>
    <div class="info-box" style="border-left-color:#9a6700;background:#fff8c5;color:#7b5a00">
      <strong>💡 日本人投資家へのひと言</strong>
      <p style="margin-top:6px;margin-bottom:0">{msg_html}</p>
    </div>
    <details style="background:#ffffff;border:1px solid #d0d7de;border-radius:8px;padding:10px 16px;margin:14px 0">
      <summary style="cursor:pointer;font-size:.88rem;color:#57606a">AI が参考にした直近ニュース（5 件）</summary>
      <ul style="margin-top:8px;padding-left:22px;font-size:.85rem;color:#424a53;line-height:1.7">{used_news_html}</ul>
    </details>
"""
    return section_html


def get_next_monday(today_jst):
    """次の月曜日の日付を返す"""
    days_until_monday = (0 - today_jst.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7  # 今日が月曜なら次週の月曜
    return today_jst + timedelta(days=days_until_monday)


def get_week_indicators(week_start, week_end):
    """指定週内に発表される指標を取得"""
    events = []
    for key, info in INDICATOR_SCHEDULE.items():
        for date_str in info.get("schedule", []):
            try:
                event_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                continue
            if week_start <= event_date <= week_end:
                events.append({
                    "key": key,
                    "info": info,
                    "date": event_date,
                })
    # 日付順にソート
    events.sort(key=lambda x: x["date"])
    return events


def load_weekly_strategy_context(script_dir, week_start):
    """weekly-strategy-context.json を読み、(1)存在 (2)verified=true (3)対象週が一致 を全て満たす場合のみ
    dict を返す。それ以外（不在/未検証/週ズレ/壊れ）は None → 呼び出し側はプレースホルダにフォールバック。
    これにより『検証を通った数値だけ公開』を構造的に保証する。"""
    path = os.path.join(script_dir, "weekly-strategy-context.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            ctx = json.load(f)
    except Exception as e:
        print(f"  ⚠️ weekly-strategy-context.json 読み込み失敗: {e}")
        return None
    if ctx.get("verified") is not True:
        print("  ℹ️ weekly-strategy-context.json は未検証(verified!=true) → シナリオ非表示")
        return None
    if ctx.get("week_start") != week_start.strftime("%Y-%m-%d"):
        print(f"  ℹ️ context の対象週({ctx.get('week_start')}) ≠ 今週({week_start}) → シナリオ非表示")
        return None
    return ctx


def build_scenario_section_html(ctx):
    """検証済み context から『執筆時点の水準＋3シナリオ＋資産別戦略』HTMLを描画。
    数値は weekly-strategy-brief routine が weekly-levels.json と照合済みのもののみ。"""
    snap = ctx.get("snapshot") or []
    snap_html = ""
    if snap:
        items = "".join(
            f'<li><strong>{s.get("name","")}：</strong>{s.get("price","")}'
            f'{(" — " + s["note"]) if s.get("note") else ""}</li>'
            for s in snap
        )
        snap_html = (f'    <div class="info-box">\n'
                     f'      <strong>📌 執筆時点の水準（出典 {ctx.get("levels_source","weekly-levels.json")}）</strong>\n'
                     f'      <ul>{items}</ul>\n'
                     f'    </div>\n')
    type_label = {"bull": "🟢 リスクオン", "base": "🟡 レンジ", "bear": "🔴 リスクオフ"}
    type_class = {"bull": "bull", "base": "base", "bear": "bear"}
    sc_html = ""
    for sc in ctx.get("scenarios", []):
        t = sc.get("type", "base")
        prob = (f' <span style="font-size:.8rem;color:#57606a">想定確度 {sc.get("prob")}</span>'
                if sc.get("prob") else "")
        sc_html += (f'    <div class="scenario-card {type_class.get(t,"base")}">\n'
                    f'      <div class="scenario-title">{type_label.get(t,"")}：{sc.get("title","")}{prob}</div>\n'
                    f'      <p>{sc.get("body","")}</p>\n'
                    f'    </div>\n')
    strat = ctx.get("asset_strategies") or []
    strat_html = ""
    if strat:
        lis = "".join(f'<li><strong>{a.get("name","")}：</strong>{a.get("text","")}</li>' for a in strat)
        strat_html = f'    <h2>💼 資産別トレード戦略</h2>\n    <ul>{lis}</ul>\n'
    verified_note = ('    <p style="font-size:.78rem;color:#6e7781;margin-top:6px">'
                     '✅ 本シナリオの数値は weekly-levels.json と自動照合済み（数値検証パイプライン）。'
                     '投資判断は自己責任で。</p>\n')
    return (f'    <h2>🎯 3つのメインシナリオ</h2>\n'
            f'{snap_html}{sc_html}{strat_html}{verified_note}')


# 検証済みシナリオが無いときのフォールバック（誤情報防止のプレースホルダ）
_SCENARIO_PLACEHOLDER = (
    '    <!-- 検証済みシナリオ(weekly-strategy-context.json)が未生成のため非表示。誤情報防止。 -->\n'
    '    <div class="info-box">\n'
    '      <strong>📊 シナリオ別の詳細水準はリニューアル中です。</strong><br>\n'
    '      より正確な価格水準にもとづくシナリオを提供するため、詳細表を一時的に非表示にしています。'
    '最新の価格・指標は <a href="index.html">🏠 最新マーケット</a>、<a href="calendar.html">📅 経済カレンダー</a> をご参照ください。\n'
    '    </div>\n'
)


def build_weekly_html(week_start, week_end, today_jst):
    """週次戦略記事のHTMLを生成"""
    week_start_str = week_start.strftime("%-m/%-d") if os.name != "nt" else week_start.strftime("%#m/%#d")
    week_end_str = week_end.strftime("%-m/%-d") if os.name != "nt" else week_end.strftime("%#m/%#d")
    today_str = today_jst.strftime("%Y-%m-%d")
    today_jp = today_jst.strftime("%Y年%-m月%-d日") if os.name != "nt" else today_jst.strftime("%Y年%#m月%#d日")

    events = get_week_indicators(week_start, week_end)

    # 重要度別カウント
    high_count = sum(1 for e in events if e["info"].get("importance", 1) >= 3)
    mid_count = sum(1 for e in events if e["info"].get("importance", 1) == 2)

    # イベント一覧HTML
    if events:
        events_html = ""
        weekday_jp = ["月", "火", "水", "木", "金", "土", "日"]
        for ev in events:
            d = ev["date"]
            info = ev["info"]
            day_str = d.strftime("%-m/%-d") if os.name != "nt" else d.strftime("%#m/%#d")
            wd = weekday_jp[d.weekday()]
            stars = "★" * info.get("importance", 1)
            events_html += f"""    <div class="schedule-card">
      <div class="schedule-day">{day_str}({wd})</div>
      <div class="schedule-body">
        <div class="schedule-title">{info['emoji']} {info['name_short']} <span style="color:#cf222e;font-size:.8rem">{stars}</span></div>
        <div class="schedule-desc">{info['description']} ／ 発表時刻：{info['time_jst']}</div>
      </div>
    </div>
"""
    else:
        events_html = '    <div class="info-box">今週は注目度の高い重要指標の発表はありません。地政学・企業決算・要人発言に注目。</div>\n'

    # AI による週末動向セクション（GEMINI_API_KEY が設定されていれば自動生成、なければ空文字）
    weekend_section_html = generate_weekend_section_with_ai(today_jst, week_start, week_end, events) or ""

    # 🆕 検証済みシナリオ（weekly-strategy-brief routine が生成・数値検証した context）を採用。
    #    無ければ誤情報防止のプレースホルダにフォールバック。
    _sd = os.path.dirname(os.path.abspath(__file__))
    _ws_ctx = load_weekly_strategy_context(_sd, week_start)
    scenario_section_html = build_scenario_section_html(_ws_ctx) if _ws_ctx else _SCENARIO_PLACEHOLDER

    title = f"今週の投資戦略（{week_start_str}〜{week_end_str}）：注目指標と3シナリオ別マーケット展望"

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} - MarketWatch AI</title>
  <meta name="description" content="{week_start_str}〜{week_end_str}週の投資戦略。注目指標{len(events)}本、重要度高{high_count}件。米ドル円・日経・米国株のシナリオ別展望を解説。">
  <meta name="keywords" content="今週の投資戦略,週間展望,{week_start.strftime('%Y年%-m月') if os.name != 'nt' else week_start.strftime('%Y年%#m月')},ドル円,日経平均,米国株,FOMC,日銀">
  <link rel="canonical" href="https://marketwatch-jp.com/guide-weekly-{week_start.strftime('%Y-%m-%d')}.html">
  <meta property="og:type" content="article">
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{week_start_str}〜{week_end_str}週の注目指標・シナリオ別マーケット展望を解説。">
  <meta property="og:url" content="https://marketwatch-jp.com/guide-weekly-{week_start.strftime('%Y-%m-%d')}.html">
  <meta property="og:site_name" content="MarketWatch AI">
  <meta property="og:locale" content="ja_JP">
  <script type="application/ld+json">
  {{"@context":"https://schema.org","@type":"Article","headline":"{title}","description":"{week_start_str}〜{week_end_str}週の注目指標・シナリオ別マーケット展望を解説。","author":{{"@type":"Organization","name":"MarketWatch AI"}},"publisher":{{"@type":"Organization","name":"MarketWatch AI"}},"datePublished":"{today_str}","dateModified":"{today_str}","mainEntityOfPage":"https://marketwatch-jp.com/guide-weekly-{week_start.strftime('%Y-%m-%d')}.html"}}
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
    .nav-bar{{display:flex;flex-wrap:wrap;gap:10px;justify-content:center;margin-bottom:32px}}
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
    .summary-grid{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px;margin:20px 0}}
    .summary-cell{{padding:18px;border-radius:10px;text-align:center}}
    .summary-cell.high{{background:#ffebe9;border:1px solid #cf222e}}
    .summary-cell.mid{{background:#fff8c5;border:1px solid #9a6700}}
    .summary-cell.total{{background:#ddf4ff;border:1px solid #0969da}}
    .summary-num{{font-size:2.2rem;font-weight:800;line-height:1}}
    .summary-cell.high .summary-num{{color:#cf222e}}
    .summary-cell.mid .summary-num{{color:#9a6700}}
    .summary-cell.total .summary-num{{color:#0969da}}
    .summary-label{{font-size:.82rem;color:#1f2328;margin-top:6px;font-weight:600}}
    .schedule-card{{background:#ffffff;border:1px solid #d0d7de;border-radius:10px;padding:16px 20px;margin:10px 0;display:flex;align-items:flex-start;gap:14px}}
    .schedule-day{{font-size:1rem;font-weight:700;color:#0969da;min-width:80px;background:#ddf4ff;padding:6px 10px;border-radius:6px;text-align:center}}
    .schedule-title{{font-size:.98rem;font-weight:700;color:#1f2328;margin-bottom:4px}}
    .schedule-desc{{font-size:.85rem;color:#57606a;line-height:1.6}}
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
    .highlight-box{{background:#ddf4ff;border-left:4px solid #0969da;border-radius:6px;padding:14px 18px;margin:16px 0;font-size:.92rem;color:#1f6feb}}
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
    @media(max-width:600px){{
      .article{{padding:24px 20px}}h1{{font-size:1.35rem}}
      .summary-grid{{grid-template-columns:1fr}}
      .summary-num{{font-size:1.8rem}}
      .schedule-card{{flex-direction:column;gap:8px}}
      .schedule-day{{align-self:flex-start}}
      .nav-bar{{display:grid;grid-template-columns:1fr 1fr;gap:8px}}
      .nav-btn{{min-width:0;width:100%;padding:10px 8px;font-size:.82rem}}
    }}
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
    <a class="nav-btn" href="market-health.html">🩺 市場健康度</a>
    <a class="nav-btn" href="hot-assets.html">🔥 出来高急増</a>
    <a class="nav-btn" href="charts.html">📈 50年チャート</a>
    <a class="nav-btn" href="youtube-summary.html">📺 YouTube要約</a>
  </nav>

  <div class="breadcrumb"><a href="index.html">トップ</a> ＞ <a href="guides.html">解説記事</a> ＞ {week_start_str}〜{week_end_str}週の戦略</div>

  <article class="article">
    <h1>📅 今週の投資戦略（{week_start_str}〜{week_end_str}）：注目指標と3シナリオ別マーケット展望</h1>
    <div class="meta-line">公開日：{today_jp}（日曜18時自動更新）／ 読了時間：約5分 ／ カテゴリ：週間展望（自動生成）</div>

    <h2>📊 今週の指標カウント</h2>
    <div class="summary-grid">
      <div class="summary-cell high"><div class="summary-num">{high_count}</div><div class="summary-label">重要度★★★</div></div>
      <div class="summary-cell mid"><div class="summary-num">{mid_count}</div><div class="summary-label">重要度★★</div></div>
      <div class="summary-cell total"><div class="summary-num">{len(events)}</div><div class="summary-label">注目イベント合計</div></div>
    </div>

    <h2>📆 今週の重要スケジュール</h2>
{events_html}
{weekend_section_html}
    <div class="ad-slot">
      <div style="font-size:.7rem;color:#6e7681;letter-spacing:.12em;margin-bottom:8px">広告 / PR</div>
      <a class="a8-pc" href="https://px.a8.net/svt/ejp?a8mat=4B1WM4+D44RHU+4SM6+614CX" rel="nofollow"><img border="0" width="728" height="90" alt="" src="https://www25.a8.net/svt/bgt?aid=260429404793&amp;wid=001&amp;eno=01&amp;mid=s00000022371001013000&amp;mc=1"></a>
      <a class="a8-mobile" href="https://px.a8.net/svt/ejp?a8mat=4B1WM4+D44RHU+4SM6+5ZEMP" rel="nofollow"><img border="0" width="320" height="50" alt="" src="https://www25.a8.net/svt/bgt?aid=260429404793&amp;wid=001&amp;eno=01&amp;mid=s00000022371001005000&amp;mc=1"></a>
    </div>

{scenario_section_html}
    <h2>⚠️ 注意すべきリスク</h2>
    <div class="warning-box">
      <strong>① 重要指標の上振れショック</strong>（特に米CPI・雇用統計）<br>
      <strong>② 地政学イベント</strong>（中東・台湾・北朝鮮）<br>
      <strong>③ 為替の急変動・介入リスク</strong>（円相場の急な動きに警戒）<br>
      <strong>④ 企業決算サプライズ</strong>（NVDA等大型銘柄）
    </div>

    <div class="info-box">
      <strong>今週の合言葉：</strong>「重要指標通過まで静観、押し目があれば積立加速」。無理にトレードせず、データを確認してから動くのが賢明。
    </div>

    <div class="related-section">
      <h3 style="font-size:1.05rem;color:#1f6feb;margin-bottom:8px">📚 関連記事</h3>
      <div class="related-grid">
        <a class="related-card" href="calendar.html"><div class="related-card-title">📅 経済カレンダー</div><div class="related-card-desc">月間スケジュール全体を確認</div></a>
        <a class="related-card" href="guides.html"><div class="related-card-title">📚 解説記事一覧</div><div class="related-card-desc">投資・指標解説の全記事</div></a>
        <a class="related-card" href="index.html"><div class="related-card-title">🏠 最新マーケット</div><div class="related-card-desc">価格・センチメント・TOPニュース</div></a>
        <a class="related-card" href="market-health.html"><div class="related-card-title">🩺 市場健康度</div><div class="related-card-desc">VIX・恐怖と強欲・バフェット指数</div></a>
      </div>
    </div>

    <div class="warning-box">
      本記事は日曜18時に自動生成された汎用戦略記事です。具体的な予想値・最新ニュースは個別記事を参照してください。投資判断は自己責任で行ってください。
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
    now_jst = datetime.now(JST)
    today = now_jst.date()
    force = "--force" in sys.argv or os.environ.get("FORCE_WEEKLY", "").lower() in ("1", "true", "yes")

    print(f"📅 週次戦略記事 自動生成 ({today} {now_jst.strftime('%a')})")

    # 日曜日のみ実行（曜日6=日曜）
    # ただし --force があれば曜日無視
    # GitHub Actions cronは日曜09:00 UTC = 日曜18:00 JST で発火想定
    if not force and today.weekday() != 6:
        print(f"  - 今日は{['月','火','水','木','金','土','日'][today.weekday()]}曜日、スキップ（日曜のみ実行）")
        return

    # 翌週月曜〜金曜の範囲
    next_monday = get_next_monday(today)
    next_friday = next_monday + timedelta(days=4)
    print(f"  📆 翌週: {next_monday} 〜 {next_friday}")

    filename = f"guide-weekly-{next_monday.strftime('%Y-%m-%d')}.html"
    filepath = os.path.join(script_dir, filename)

    if os.path.exists(filepath) and not force:
        print(f"  ⏭️  {filename}: 既に存在、スキップ（上書きする場合は --force）")
        return

    html = build_weekly_html(next_monday, next_friday, today)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  ✅ {filename}: 生成完了")

    # 生成と同時にGitHubへアップロード（ローカル実行時のみ。Actions 実行時は git push に委譲）
    if os.environ.get("GITHUB_ACTIONS_RUN") == "true":
        print("  ⏭️  GitHub Actions 実行中、API アップロードはスキップ（git push step で同期）")
        return
    try:
        from auto_indicator_preview import _load_gh_config, upload_to_github
        gh_cfg = _load_gh_config(script_dir)
        if gh_cfg is not None:
            upload_to_github(filepath, gh_cfg, repo_path=filename)
        else:
            print("  ⚠️  market-news-config.json が見つからず、GitHubアップロードはスキップ")
    except ImportError:
        print("  ⚠️  auto_indicator_preview.py のヘルパーをインポートできず、アップロードスキップ")

    print(f"📊 完了")


if __name__ == "__main__":
    main()
