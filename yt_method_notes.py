"""YouTube チャンネルの動画を Gemini に見せて、手法のメモ（機械で検証するための細かいメモ）を作る（研究用・手動のみ）。

2026-10-20 新設＝オーナー「この動画をすべて理解して、手法をまとめて検証を」（@fxism-rion）。
手元の回線は YouTube の字幕取得を止められていた（IpBlocked／429）ので、サイトの YouTube 要約と同じく
Gemini に動画の URL を渡して音声と画面の両方を読ませる（チャートの設定は画面にしか出ないので、字幕より向いている）。

  Actions:  python yt_method_notes.py run --channel @fxism-rion --out yt-notes --shard 0 --of 4
  手元:     python yt_method_notes.py pull <run_id> <保存先>

出力は artifact だけ（リポジトリには書かない）。動画の書き起こしは作らず、決まり・数字・短い引用のメモにする。

2026-10-24 追記（オーナー「この動画を見て内容をまとめて学習してください」・クラウドのセッションは YouTube も artifact の置き場も遮断）:
  --kind summary  手法に限らない内容のまとめ（既定は method＝手法を検証するためのメモ）
  --channel -     チャンネルの一覧を取らず --ids の動画だけ見る（題名とチャンネル名は oEmbed で取る）
  --echo          メモをログにも出す（クラウドのセッションはジョブのログで読む）。字幕は出さない
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

UA = {"User-Agent": "Mozilla/5.0", "Accept-Language": "ja"}
MODELS = ("gemini-2.5-flash", "gemini-flash-latest", "gemini-2.0-flash")

PROMPT = """あなたは FX トレード手法の研究者です。この動画（チャンネル「{channel}」、題名「{title}」）を最初から最後まで、音声と画面の両方を見て、手法をあとで機械で検証できるように細かくメモしてください。

出力（Markdown・日本語）:
## 1. 基本
- 通貨ペア／銘柄、使った時間足（全部）、取引した日時（動画内の表示どおり。日本時間かどうかも）、結果（獲得 pips・勝ち負け・建て玉の数）
## 2. 画面に映っているチャートの設定
- 表示しているインジケーター：種類・期間・色・どの時間足のものか（画面の表示や発言からわかる範囲で。例「赤の線＝4時間足の20SMA」）
- 引いている線：水平線・トレンドライン・チャネル・フィボナッチなどと、引く場所の決め方
- 自作・配布ツール（リオンチャートなど）の名前と、それが何を表示するか
## 3. 手法の決まり（発言と画面から）
- 環境認識（上位足で何を見るか、どの順で見るか）
- 待つ場所（どこまで来るのを待つか）
- エントリーの引き金（どの足のどんな形・どの線を抜けたら・何本待つか）
- 損切りの置き場所（具体的に）
- 利確（分割・刻む・どこで何割など、具体的に）
- 見送る条件・やってはいけない形・時間帯・経済指標の扱い
- 資金管理（ロット・1回の損失の割合・計算式）
## 4. 実際の取引の流れ（時刻順）
- 動画の時刻（mm:ss）ごとに、何を見て何をしたか
## 5. 数字の一覧
- 動画に出た数字（期間・pips・価格・時刻・勝率・回数・金額）をすべて、何の数字かとともに
## 6. 大事な発言の短い引用
- 決まりを言っている発言を最大5つ、各25字以内で（動画の時刻つき）
## 7. はっきりしない点
- 動画の中で決めていない・あいまいな部分（例：「重要な高値」の決め方が数字で示されていない）

注意:
- 見えない・聞こえないことは書かない。推測したときは「（推測）」と付ける
- 成績の主張は「主張」として書き、確かめられた事実として扱わない
- 宣伝（講座・LINE・口座開設・ツールの配布）の部分は1行でまとめる
- 長い書き起こしはしない（決まり・数字・短い引用のメモにする）
{caption}"""

SUMMARY_PROMPT = """あなたは日本人の個人投資家向けの調査担当です。この動画（チャンネル「{channel}」、題名「{title}」）を最初から最後まで、音声と画面の両方を見て、内容をあとで正確に学べるように細かくまとめてください。

出力（Markdown・日本語）:
## 1. 基本
- 題名・話し手（わかる範囲）・動画の長さ・収録日や話している時点（動画内でわかれば）・主題をひとことで
## 2. 要点（3〜7個）
- 動画が一番伝えたいことを、大事な順に
## 3. 流れに沿った中身（時刻つき）
- 動画の時刻（mm:ss）ごとに、何を説明・主張したか。図表やチャートが映ったら、何が描かれているか
## 4. 数字・固有名詞の一覧
- 出た数字（価格・金利・期間・割合・回数・金額・日付）と、銘柄・指標・人名・組織名を、何の数字・何の話かとともに
## 5. 主張とその根拠
- 主張ごとに、示した根拠（データ・過去の例・理屈）。根拠を示していないものは「根拠の提示なし」
## 6. 売買の決まり・手法（あれば）
- 入る条件・損切り・利確・資金管理・見送る条件などを、機械で確かめられる形で。無ければ「なし」
## 7. 大事な発言の短い引用
- 最大5つ、各25字以内（動画の時刻つき）
## 8. はっきりしない点・注意点
- あいまいな部分・数字で決めていない部分・宣伝や利害関係・事実と違うかもしれない点

注意:
- 見えない・聞こえないことは書かない。推測したときは「（推測）」と付ける
- 成績や将来の予想は「主張」として書き、確かめられた事実として扱わない
- 宣伝（講座・LINE・口座開設・ツールの配布）の部分は1行でまとめる
- 長い書き起こしはしない（要点・数字・短い引用のまとめにする）
{caption}"""
PROMPTS = {"method": PROMPT, "summary": SUMMARY_PROMPT}


def _get(url, data=None, timeout=60):
    h = dict(UA)
    if data is not None:
        h["Content-Type"] = "application/json"
    with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=h), timeout=timeout) as r:
        return r.read().decode("utf-8")


def _txt(x):
    if isinstance(x, dict):
        return x.get("content") or x.get("simpleText") or ""
    return ""


def _walk(o, out, conts):
    if isinstance(o, dict):
        lv = o.get("lockupViewModel")
        if lv and lv.get("contentType", "LOCKUP_CONTENT_TYPE_VIDEO") == "LOCKUP_CONTENT_TYPE_VIDEO":
            md = lv.get("metadata", {}).get("lockupMetadataViewModel", {})
            m = re.search(r'"text": "(\d+:\d+(?::\d+)?)"', json.dumps(lv.get("contentImage", {}), ensure_ascii=False))
            out.append({"id": lv.get("contentId"), "title": _txt(md.get("title", {})), "len": m.group(1) if m else ""})
        ci = o.get("continuationItemRenderer")
        if ci:
            m = re.search(r'"token": "([^"]+)"', json.dumps(ci))
            if m:
                conts.append(m.group(1))
        for v in o.values():
            _walk(v, out, conts)
    elif isinstance(o, list):
        for v in o:
            _walk(v, out, conts)


def list_videos(channel):
    """チャンネルの「動画」タブの全部（新しい順）→ [{id, title, len}]"""
    html = _get(f"https://www.youtube.com/{channel}/videos")
    data = json.loads(re.search(r"var ytInitialData = (\{.*?\});</script>", html).group(1))
    key = re.search(r'"INNERTUBE_API_KEY":"([^"]+)"', html).group(1)
    ver = re.search(r'"INNERTUBE_CLIENT_VERSION":"([^"]+)"', html).group(1)
    vids, conts = [], []
    _walk(data, vids, conts)
    for _ in range(100):
        if not conts:
            break
        body = json.dumps({"context": {"client": {"clientName": "WEB", "clientVersion": ver, "hl": "ja"}},
                           "continuation": conts[0]}).encode()
        d = json.loads(_get(f"https://www.youtube.com/youtubei/v1/browse?key={key}", body))
        new, conts = [], []
        _walk(d, new, conts)
        if not new:
            break
        vids += new
    seen, out = set(), []
    for v in vids:
        if v["id"] and v["id"] not in seen:
            seen.add(v["id"])
            out.append(v)
    return out


def video_meta(vid):
    """oEmbed で（題名, チャンネル名）。取れなければ空。"""
    try:
        d = json.loads(_get(f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={vid}&format=json", timeout=30))
        return d.get("title", ""), d.get("author_name", "")
    except Exception:  # noqa: BLE001
        return "", ""


def caption_text(vid, limit=30000):
    """自動字幕（取れれば Gemini への参考に渡すだけ・保存しない）。取れなければ空。"""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        t = YouTubeTranscriptApi().fetch(vid, languages=["ja", "en"])
        s = "\n".join(f"[{int(x.start) // 60}:{int(x.start) % 60:02d}] {x.text}" for x in t)
        return s[:limit]
    except Exception as e:  # noqa: BLE001
        return "" if not os.environ.get("YT_DEBUG") else f"#ERR {type(e).__name__}"


def gemini_notes(api_key, vid, title, channel, caption, models=MODELS, tries=4, kind="method"):
    cap = ""
    if caption and not caption.startswith("#ERR"):
        cap = "\n参考：自動字幕（誤認識あり・数字は画面で確かめること）\n" + caption
    prompt = PROMPTS[kind].format(channel=channel, title=title, caption=cap)
    body = {"contents": [{"parts": [{"file_data": {"file_uri": f"https://www.youtube.com/watch?v={vid}", "mime_type": "video/youtube"}},
                                    {"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 16384}}
    errs = []   # モデルごとの失敗を全部残す（最後の1つだけだと、先のモデルが落ちた理由が消える）
    for model in models:
        for k in range(tries):
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
                d = json.loads(_get(url, json.dumps(body).encode(), timeout=600))
                parts = d.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                text = "".join(p.get("text", "") for p in parts).strip()
                if text:
                    return text, model, d.get("usageMetadata", {})
                errs.append(f"{model}: empty ({d.get('candidates', [{}])[0].get('finishReason')})")
                break
            except urllib.error.HTTPError as e:
                errs.append(f"{model}: HTTP {e.code} {e.read()[:200]!r}")
                if e.code in (429, 500, 503):
                    time.sleep(20 * (k + 1))
                    continue
                break
            except Exception as e:  # noqa: BLE001
                errs.append(f"{model}: {type(e).__name__}")
                time.sleep(10 * (k + 1))
    return None, None, {"error": " | ".join(errs)}


def run(a):
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        sys.exit("GEMINI_API_KEY が無い")
    if a.ids and a.channel in ("", "-"):
        vids = [{"id": i, "title": t, "len": "", "author": au}
                for i in a.ids.split(",") for t, au in [video_meta(i)]]
    else:
        vids = list_videos(a.channel)
        if a.ids:
            want = a.ids.split(",")
            vids = [v for v in vids if v["id"] in want] + [{"id": i, "title": "", "len": ""} for i in want if i not in {v["id"] for v in vids}]
    os.makedirs(a.out, exist_ok=True)
    if a.shard == 0:
        json.dump(vids, open(os.path.join(a.out, "_videos.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    mine = [v for i, v in enumerate(vids) if i % a.of == a.shard]
    print(f"{a.channel}: {len(vids)} videos, shard {a.shard}/{a.of} → {len(mine)}")
    usage = {}
    for v in mine:
        cap = caption_text(v["id"])
        text, model, u = gemini_notes(key, v["id"], v["title"], v.get("author") or a.channel_name, cap,
                                      models=(a.model,) + tuple(m for m in MODELS if m != a.model), kind=a.kind)
        usage[v["id"]] = {"model": model, "caption": bool(cap and not cap.startswith("#ERR")), **u}
        if text:
            doc = f"# {v['title']}\n\nhttps://www.youtube.com/watch?v={v['id']}（{v['len']}・{model}）\n\n{text}\n"
            with open(os.path.join(a.out, f"{v['id']}.md"), "w", encoding="utf-8") as f:
                f.write(doc)
            if a.echo:
                print(f"----- BEGIN NOTES {v['id']} -----\n{doc}----- END NOTES {v['id']} -----")
        print(f"  {v['id']} {'ok' if text else 'FAIL'} {model} cap={usage[v['id']]['caption']} "
              f"in={u.get('promptTokenCount')} out={u.get('candidatesTokenCount')} {u.get('error', '')}")
        time.sleep(a.pause)
    json.dump(usage, open(os.path.join(a.out, f"_usage-{a.shard}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def pull(a):
    """（手元だけ）実行 run_id の artifact（yt-notes-*）を保存先に展開する。"""
    import io
    import zipfile
    import mw   # リポジトリの根の司令塔（GitHub のトークン）
    c = mw._cfg()
    _, d = mw._gh("GET", f"/actions/runs/{a.run_id}/artifacts?per_page=100")
    arts = [x for x in d.get("artifacts", []) if x["name"].startswith("yt-notes-")]

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kw):
            return None

    os.makedirs(a.dest, exist_ok=True)
    n = 0
    for art in arts:
        req = urllib.request.Request(art["archive_download_url"], headers={
            "Authorization": f"token {c['github_token']}", "Accept": "application/vnd.github+json", "User-Agent": "mw-cli"})
        try:
            urllib.request.build_opener(NoRedirect).open(req, timeout=60)
            raise RuntimeError("転送先が返らなかった")
        except urllib.error.HTTPError as e:
            if e.code not in (301, 302, 303, 307, 308):
                raise
            loc = e.headers["Location"]
        with urllib.request.urlopen(urllib.request.Request(loc, headers={"User-Agent": "mw-cli"}), timeout=300) as r:
            z = zipfile.ZipFile(io.BytesIO(r.read()))
        for name in z.namelist():
            if name.endswith("/") or "/" in name or "\\" in name or ".." in name:
                continue
            with open(os.path.join(a.dest, name), "wb") as f:
                f.write(z.read(name))
            n += 1
    print(f"{len(arts)} artifacts, {n} files → {a.dest}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--channel", required=True)
    r.add_argument("--channel-name", default="")
    r.add_argument("--ids", default="")
    r.add_argument("--out", default="yt-notes")
    r.add_argument("--shard", type=int, default=0)
    r.add_argument("--of", type=int, default=1)
    r.add_argument("--model", default=MODELS[0])
    r.add_argument("--pause", type=float, default=5)
    r.add_argument("--kind", choices=sorted(PROMPTS), default="method")
    r.add_argument("--echo", action="store_true")
    p = sub.add_parser("pull")
    p.add_argument("run_id")
    p.add_argument("dest")
    a = ap.parse_args(argv)
    if a.cmd == "run":
        a.channel_name = a.channel_name or a.channel
        run(a)
    else:
        pull(a)


if __name__ == "__main__":
    main()
