# -*- coding: utf-8 -*-
"""Gemini に YouTube の動画を読ませる共通の部品（2026-11-15 新設・標準ライブラリだけ）。

なぜ要るか:
  ・YouTube はクラウドの通信元からの機械的な取得を確認画面へ回す。Gemini の「YouTube の URL を渡す」機能は、
    動画を Google の中から取りに行く正式な道なので、GitHub Actions からでも読める
  ・生配信の録画のように長い動画（1時間超）は、ふつうの画質だと読み込む量が上限を超えて失敗し、
    YouTube 要約は「題名と説明文だけの要約（text）」に落ちていた（2026-11-12〜13 に2件）。
    ここでは画質を下げて（MEDIA_RESOLUTION_LOW）読み込む量を約3分の1にする
  ・YouTube Data API で動画の長さと「配信前・配信中」かを先に確かめる（配信前の動画を要約すると、
    中身を見ずに題名から推測した要約になる＝2026-11-15 に4件見つかった）

使う所: generate_youtube_summary.py（長い動画の読み直し）・analyze_youtube_video.py（動画1本の分析）
キー: GEMINI_API_KEY（GitHub の Secrets）。YouTube Data API は YOUTUBE_API_KEY、無ければ GEMINI_API_KEY
"""
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
# 新しい順。提供終了のモデルは tests/test_gemini_retired_models.py が止める
VIDEO_MODELS = ("gemini-flash-latest", "gemini-2.5-flash")
LOW_RES = "MEDIA_RESOLUTION_LOW"
# 画質を下げたときの読み込む量の目安（1秒あたり・映像1枚＋音声）。長い動画を区切るかどうかの判断にだけ使う
TOKENS_PER_SEC_LOW = 100
TOKENS_PER_SEC_DEFAULT = 300

_ID_RE = re.compile(r"(?:v=|youtu\.be/|/live/|/shorts/|/embed/)([A-Za-z0-9_-]{11})")


def video_id_from_url(url):
    """watch?v= / youtu.be / live / shorts / embed のどれでも動画の ID（11文字）を返す。無ければ None"""
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", url or ""):
        return url
    m = _ID_RE.search(url or "")
    return m.group(1) if m else None


def parse_iso_duration(s):
    """ISO 8601 の長さ（PT1H2M3S・P0D）→ 秒。読めなければ 0"""
    m = re.fullmatch(r"P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?", s or "")
    if not m:
        return 0
    d, h, mi, se = (int(x or 0) for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + se


def video_info_from_item(item):
    """YouTube Data API の videos の1件（snippet・contentDetails・liveStreamingDetails）→ 使う形。
    published は生配信なら実際に始まった時刻（予約した時刻ではない）。live_status は none / upcoming / live"""
    sn = item.get("snippet", {}) or {}
    live = item.get("liveStreamingDetails", {}) or {}
    return {
        "video_id": item.get("id", ""),
        "title": sn.get("title", ""),
        "channel": sn.get("channelTitle", ""),
        "description": sn.get("description", "") or "",
        "published": live.get("actualStartTime") or sn.get("publishedAt", ""),
        "duration_sec": parse_iso_duration((item.get("contentDetails", {}) or {}).get("duration", "")),
        "live_status": sn.get("liveBroadcastContent", "none") or "none",
    }


def is_ready(info):
    """要約・分析してよい動画か（配信前・配信中・長さ0は、まだ中身が無い）"""
    return info.get("live_status", "none") not in ("upcoming", "live") and (info.get("duration_sec") or 0) > 0


def fetch_video_info(video_id, api_key, timeout=20):
    """YouTube Data API で1本の情報を取る（1 unit）。取れなければ None"""
    q = urllib.parse.urlencode({"part": "snippet,contentDetails,liveStreamingDetails", "id": video_id, "key": api_key})
    req = urllib.request.Request(f"{YOUTUBE_API_BASE}/videos?{q}", headers={"User-Agent": "marketwatch-jp/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        items = json.loads(r.read().decode("utf-8")).get("items", [])
    return video_info_from_item(items[0]) if items else None


def build_request(url, prompt, low_res=True, start_sec=None, end_sec=None, max_output_tokens=16384, temperature=0.2):
    """generateContent に送る本文（REST の形）。start_sec / end_sec を付けるとその区間だけ読む"""
    video = {"fileData": {"fileUri": url, "mimeType": "video/youtube"}}
    meta = {}
    if start_sec is not None:
        meta["startOffset"] = f"{int(start_sec)}s"
    if end_sec is not None:
        meta["endOffset"] = f"{int(end_sec)}s"
    if meta:
        video["videoMetadata"] = meta
    cfg = {"maxOutputTokens": max_output_tokens, "temperature": temperature}
    if low_res:
        cfg["mediaResolution"] = LOW_RES
    return {"contents": [{"role": "user", "parts": [video, {"text": prompt}]}], "generationConfig": cfg}


def build_text_request(prompt, max_output_tokens=16384, temperature=0.2):
    return {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": max_output_tokens, "temperature": temperature}}


def response_text(data):
    """generateContent の返事から文章を取り出す。無ければ空文字"""
    out = []
    for c in data.get("candidates", []) or []:
        for p in (c.get("content", {}) or {}).get("parts", []) or []:
            if p.get("text") and not p.get("thought"):
                out.append(p["text"])
        if out:
            break
    return "".join(out).strip()


def _post(model, body, api_key, timeout):
    req = urllib.request.Request(
        f"{GEMINI_BASE}/{model}:generateContent", data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def generate(body, api_key, models=VIDEO_MODELS, timeout=900, retries=2, log=print):
    """本文を候補のモデルへ順に送る。返り値＝(文章, モデル名, 返事の usageMetadata)。全部だめなら RuntimeError。
    ・404（そのモデルが無い）→ 次のモデル
    ・400 で mediaResolution を知らないと言われたら、それを外して同じモデルでもう1回
    ・429 / 5xx → 少し待って同じモデルで最大 retries 回"""
    errors = []
    for model in models:
        b = json.loads(json.dumps(body))
        attempt = 0
        while True:
            try:
                data = _post(model, b, api_key, timeout)
                text = response_text(data)
                if text:
                    return text, model, data.get("usageMetadata", {}) or {}
                reason = ((data.get("candidates") or [{}])[0] or {}).get("finishReason", "") or \
                    json.dumps(data.get("promptFeedback", {}), ensure_ascii=False)[:120]
                errors.append(f"{model}: 空の返事（{reason}）")
                break
            except urllib.error.HTTPError as e:
                msg = e.read().decode("utf-8", errors="replace")[:300] if hasattr(e, "read") else ""
                if e.code == 400 and "mediaResolution" in json.dumps(b) and re.search(r"media_?[Rr]esolution", msg):
                    b["generationConfig"].pop("mediaResolution", None)
                    log(f"    ℹ️ {model}: 画質の指定を外してもう一度")
                    continue
                if e.code in (429, 500, 502, 503, 504) and attempt < retries:
                    attempt += 1
                    time.sleep(15 * attempt)
                    continue
                errors.append(f"{model}: HTTP {e.code} {msg}")
                break
            except Exception as e:  # noqa: BLE001 — 通信の切れ・時間切れは次のモデルへ
                errors.append(f"{model}: {type(e).__name__}: {str(e)[:120]}")
                break
    raise RuntimeError(" / ".join(errors) or "モデルの候補が空")


def generate_from_youtube(url, prompt, api_key, low_res=True, start_sec=None, end_sec=None,
                          max_output_tokens=16384, models=VIDEO_MODELS, log=print):
    """動画（またはその区間）を読ませて文章を返す。返り値＝(文章, モデル名, usageMetadata)"""
    body = build_request(url, prompt, low_res, start_sec, end_sec, max_output_tokens)
    return generate(body, api_key, models=models, log=log)


def plan_segments(duration_sec, max_single_sec=9000, chunk_sec=5400):
    """長さに応じて区間に分ける。max_single_sec（2.5時間）までは1回で読む（画質を下げて約90万トークン）。
    それより長いときは chunk_sec（90分）ごと。長さが分からない（0）ときは1回"""
    if not duration_sec or duration_sec <= max_single_sec:
        return [(None, None)]
    return [(s, min(s + chunk_sec, duration_sec)) for s in range(0, duration_sec, chunk_sec)]
