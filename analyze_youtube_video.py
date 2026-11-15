# -*- coding: utf-8 -*-
"""YouTube の動画1本を Gemini に読ませて分析する（2026-11-15 新設・オーナー依頼「内容の分析もお願いします」）。

動かす所: GitHub Actions の手動実行（.github/workflows/youtube-analyze.yml）。GEMINI_API_KEY は GitHub の
Secrets にしか無く、クラウドのセッションからは YouTube が確認画面へ回すため。結果は実行の記録（ジョブの
まとめ）と成果物の .md にだけ出す＝サイトには載せない・リポジトリにも書かない。

使い方:
  python analyze_youtube_video.py --url https://www.youtube.com/watch?v=XXXXXXXXXXX [--question "知りたいこと"]
  終わりの番号: 0＝できた／2＝キーが無い・URL が読めない／3＝まだ配信前か配信中（録画ができてから）／4＝Gemini が失敗
"""
import argparse
import os
import sys
from datetime import datetime, timedelta, timezone

import gemini_youtube as G

JST = timezone(timedelta(hours=9))

BASE_RULES = """あなたは投資の動画を確かめる調査係です。日本語で、見出しと箇条書きで書いてください。
決まり:
- 動画の中で実際に話された言葉と、画面に映った文字・数字・グラフだけを根拠にする。見ていない・聞いていないことは書かず「動画では確認できない」と書く。推測で埋めない
- 根拠には必ずおおよその時刻（例 0:12:30）を付ける
- 数字（値段・パーセント・回数・期間・損益）は、話された・映ったとおりに書く
- 話し手の意見と、データで示された事実を分けて書く
- 宣伝（無料プレゼント・LINE 登録・有料の講座や商品の案内）があれば、その中身と時刻を書く
"""

FULL_PROMPT = BASE_RULES + """
次の見出しで書いてください。
## 1. 動画の概要（5行以内）
## 2. 時刻つきの流れ（10〜25項目）
## 3. 主張とその根拠（主張ごとに「根拠として示されたもの」と「示されなかったもの」）
## 4. 売買の決まり（話された範囲で: 通貨ペア・時間足・入る条件・利確・損切り・持つ時間・資金の管理。決まっていない所は「動画では決まっていない」）
## 5. 画面に出たデータとその出どころ（グラフの題名・データの名前・提供している会社やサイト名・更新の頻度・期間。読めた文字はそのまま）
## 6. 過去の成績として示されたもの（期間・回数・勝率・損益。示されていなければ「示されていない」）
## 7. 宣伝・勧誘
## 8. 動画では確認できなかったこと・気をつける点
"""

SEGMENT_PROMPT = BASE_RULES + """
これは長い動画の一部（{start}〜{end}）です。この区間について、時刻つきの細かいメモを書いてください。
主張・根拠・売買の決まり・画面に出たデータとその出どころ・数字・宣伝を漏らさずに。
"""

SYNTH_PROMPT = """次は1本の長い動画を区間ごとに読んだメモです（区間の順）。メモに書かれていることだけを使い、
新しいことを足さずに、下の見出しで1つにまとめてください。日本語・見出しと箇条書き。時刻はメモのものを使う。
{sections}

{question}
---
{notes}
"""


def _hms(sec):
    sec = int(sec or 0)
    return f"{sec // 3600}:{sec % 3600 // 60:02d}:{sec % 60:02d}"


def _sections_of(prompt):
    return "\n".join(line for line in prompt.splitlines() if line.startswith("## "))


def question_block(question):
    q = (question or "").strip()
    return f"\n## 9. 依頼者の質問への答え\n質問: {q}\n（動画の中の根拠と時刻を付けて答える。根拠が無ければそう書く）\n" if q else ""


def analyze(url, question, api_key, info=None, log=print):
    """返り値＝(本文, 使ったモデル, 読み込んだ量の合計)。失敗は RuntimeError"""
    duration = (info or {}).get("duration_sec") or 0
    segments = G.plan_segments(duration)
    prompt = FULL_PROMPT + question_block(question)
    if segments == [(None, None)]:
        log(f"  🎬 1回で読みます（画質を下げる・長さ {_hms(duration)}）")
        text, model, usage = G.generate_from_youtube(url, prompt, api_key, log=log)
        return text, model, usage.get("promptTokenCount", 0)
    notes, total, model = [], 0, ""
    for i, (s, e) in enumerate(segments, 1):
        log(f"  🎬 区間 {i}/{len(segments)}: {_hms(s)}〜{_hms(e)}")
        p = SEGMENT_PROMPT.format(start=_hms(s), end=_hms(e))
        t, model, usage = G.generate_from_youtube(url, p, api_key, start_sec=s, end_sec=e, log=log)
        notes.append(f"### 区間 {_hms(s)}〜{_hms(e)}\n{t}")
        total += usage.get("promptTokenCount", 0)
    log("  🧩 区間のメモを1つにまとめます")
    body = G.build_text_request(SYNTH_PROMPT.format(sections=_sections_of(FULL_PROMPT), question=question_block(question),
                                                    notes="\n\n".join(notes)))
    text, model2, usage = G.generate(body, api_key, log=log)
    return text, model2 or model, total + usage.get("promptTokenCount", 0)


def render(url, info, body, model, tokens, now=None):
    now = now or datetime.now(JST)
    info = info or {}
    head = [f"# 動画の分析：{info.get('title') or url}", "",
            f"- URL: {url}",
            f"- チャンネル: {info.get('channel') or '（取れなかった）'}",
            f"- 公開（生配信は始まった時刻）: {info.get('published') or '（取れなかった）'}",
            f"- 長さ: {_hms(info.get('duration_sec')) if info.get('duration_sec') else '（取れなかった）'}",
            f"- 分析: Gemini（{model}・画質を下げて読み込み・読み込んだ量 約{tokens:,}トークン）・{now:%Y-%m-%d %H:%M} JST",
            "", "---", ""]
    foot = ["", "---", "※ Gemini が動画を読んで作ったメモです。時刻を付けた所は動画で確かめてください。"
            "研究のための記録で、投資助言ではありません。"]
    return "\n".join(head) + body.strip() + "\n" + "\n".join(foot) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--url", required=True)
    ap.add_argument("--question", default="")
    ap.add_argument("--out", default="youtube-analysis.md")
    a = ap.parse_args(argv)

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    yt_key = os.environ.get("YOUTUBE_API_KEY", "").strip() or api_key
    vid = G.video_id_from_url(a.url)
    if not api_key or not vid:
        print("❌ GEMINI_API_KEY が無いか、URL から動画の ID を読めません")
        return 2
    url = f"https://www.youtube.com/watch?v={vid}"

    info = None
    try:
        info = G.fetch_video_info(vid, yt_key)
    except Exception as e:  # noqa: BLE001 — 長さが分からなくても1回で読む
        print(f"  ⚠️ 動画の情報を取れませんでした（長さが分からないので1回で読みます）: {type(e).__name__}: {str(e)[:120]}")
    if info:
        print(f"▶ {info['channel']}: {info['title']}（長さ {_hms(info['duration_sec'])}・{info['live_status']}）")
        if not G.is_ready(info):
            msg = (f"⏸️ まだ配信前か配信中です（{info['live_status']}・長さ {info['duration_sec']}秒）。"
                   "中身が無いまま読ませると推測の答えになるので、録画ができてからもう一度実行してください")
            print(msg)
            _summary(f"# 動画の分析：{info['title']}\n\n{msg}\n")
            return 3
    try:
        body, model, tokens = analyze(url, a.question, api_key, info)
    except RuntimeError as e:
        print(f"❌ Gemini で読めませんでした: {e}")
        return 4
    md = render(url, info, body, model, tokens)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(md)
    _summary(md)
    print("\n" + md)
    return 0


def _summary(md):
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(md + "\n")


if __name__ == "__main__":
    sys.exit(main())
