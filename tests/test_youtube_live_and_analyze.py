# -*- coding: utf-8 -*-
"""YouTube の生配信の扱いと、動画1本の分析（2026-11-15 新設）のテスト。通信はしない（作り物の返事だけ）。

固定すること:
  ・配信前・配信中（live_status が upcoming / live、または長さ0）は要約しない。前に長さ0で作った要約は外して作り直す
  ・生配信の公開の時刻は、予約した時刻ではなく実際に始まった時刻
  ・Gemini への本文＝YouTube の URL・画質を下げる指定・区間の指定。画質の指定を知らないと言われたら外してもう一度
  ・長い動画（2.5時間超）は90分ごとに区切って読み、最後に1つにまとめる
  ・分析は配信前なら止まる（終わりの番号 3）・結果に「投資助言ではない」を付ける
  ・手動のワークフローは入力を env で渡し、リポジトリに書かない

実行:  python -m pytest -q tests/test_youtube_live_and_analyze.py
"""
import io
import os
import sys
import urllib.error

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import analyze_youtube_video as A  # noqa: E402
import gemini_youtube as G  # noqa: E402
import generate_youtube_summary as Y  # noqa: E402

VID = "Fm4jPi0mIAY"


def _item(live=None, duration="PT1H30M5S", status="none", published="2026-11-13T07:59:01Z"):
    it = {"id": VID, "snippet": {"title": "t", "channelTitle": "c", "publishedAt": published,
                                 "liveBroadcastContent": status, "description": "d"},
          "contentDetails": {"duration": duration}}
    if live is not None:
        it["liveStreamingDetails"] = live
    return it


# ── 部品 ──
def test_video_id_from_url():
    for u in (f"https://www.youtube.com/watch?v={VID}", f"https://youtu.be/{VID}?t=10",
              f"https://www.youtube.com/live/{VID}", f"https://www.youtube.com/watch?app=desktop&v={VID}&t=5", VID):
        assert G.video_id_from_url(u) == VID, u
    assert G.video_id_from_url("https://example.com/") is None


def test_parse_iso_duration():
    assert G.parse_iso_duration("PT1H2M3S") == 3723
    assert G.parse_iso_duration("PT45S") == 45
    assert G.parse_iso_duration("P0D") == 0
    assert G.parse_iso_duration("P1DT2H") == 93600
    assert G.parse_iso_duration("") == 0 and G.parse_iso_duration("x") == 0


def test_live_uses_actual_start_time_and_status():
    done = G.video_info_from_item(_item({"actualStartTime": "2026-11-15T03:00:00Z", "actualEndTime": "2026-11-15T05:00:00Z"}))
    assert done["published"] == "2026-11-15T03:00:00Z" and done["duration_sec"] == 5405 and G.is_ready(done)
    upcoming = G.video_info_from_item(_item({"scheduledStartTime": "2026-11-15T03:00:00Z"}, "P0D", "upcoming"))
    assert upcoming["published"] == "2026-11-13T07:59:01Z" and not G.is_ready(upcoming)
    live = G.video_info_from_item(_item({"actualStartTime": "2026-11-15T03:00:00Z"}, "P0D", "live"))
    assert not G.is_ready(live)
    normal = G.video_info_from_item(_item())
    assert normal["published"] == "2026-11-13T07:59:01Z" and G.is_ready(normal)


def test_request_body():
    b = G.build_request(f"https://www.youtube.com/watch?v={VID}", "p", start_sec=600, end_sec=1200)
    part = b["contents"][0]["parts"][0]
    assert part["fileData"] == {"fileUri": f"https://www.youtube.com/watch?v={VID}", "mimeType": "video/youtube"}
    assert part["videoMetadata"] == {"startOffset": "600s", "endOffset": "1200s"}
    assert b["generationConfig"]["mediaResolution"] == "MEDIA_RESOLUTION_LOW"
    assert b["contents"][0]["parts"][1] == {"text": "p"}
    plain = G.build_request("u", "p", low_res=False)
    assert "mediaResolution" not in plain["generationConfig"] and "videoMetadata" not in plain["contents"][0]["parts"][0]


def test_response_text_skips_thoughts():
    data = {"candidates": [{"content": {"parts": [{"text": "考え中", "thought": True}, {"text": "答え"}, {"text": "の続き"}]}}]}
    assert G.response_text(data) == "答えの続き"
    assert G.response_text({}) == ""


def test_plan_segments():
    assert G.plan_segments(0) == [(None, None)]
    assert G.plan_segments(9000) == [(None, None)]
    assert G.plan_segments(12000) == [(0, 5400), (5400, 10800), (10800, 12000)]


def _http_error(code, msg):
    return urllib.error.HTTPError("u", code, "x", {}, io.BytesIO(msg.encode()))


def test_generate_drops_media_resolution_and_moves_to_next_model(monkeypatch):
    calls = []

    def fake_post(model, body, key, timeout):
        calls.append((model, "mediaResolution" in body["generationConfig"]))
        if model == "m1":
            raise _http_error(404, "not found")
        if "mediaResolution" in body["generationConfig"]:
            raise _http_error(400, 'Invalid JSON payload received. Unknown name "mediaResolution"')
        return {"candidates": [{"content": {"parts": [{"text": "ok"}]}}], "usageMetadata": {"promptTokenCount": 7}}

    monkeypatch.setattr(G, "_post", fake_post)
    text, model, usage = G.generate(G.build_request("u", "p"), "k", models=("m1", "m2"), log=lambda m: None)
    assert (text, model, usage["promptTokenCount"]) == ("ok", "m2", 7)
    assert calls == [("m1", True), ("m2", True), ("m2", False)]


def test_generate_raises_when_all_fail(monkeypatch):
    monkeypatch.setattr(G, "_post", lambda *a: (_ for _ in ()).throw(_http_error(403, "forbidden")))
    with pytest.raises(RuntimeError) as e:
        G.generate(G.build_request("u", "p"), "k", models=("m1",), log=lambda m: None)
    assert "403" in str(e.value)


# ── YouTube 要約 ──
def test_summary_skips_not_ready_and_drops_old_guesses():
    assert Y.not_ready_for_summary({"duration_sec": 0, "live_status": "none"})
    assert Y.not_ready_for_summary({"duration_sec": 3600, "live_status": "upcoming"})
    assert Y.not_ready_for_summary({"duration_sec": 3600, "live_status": "live"})
    assert not Y.not_ready_for_summary({"duration_sec": 3600, "live_status": "none"})
    assert not Y.not_ready_for_summary({"title": "TEST_MODE の候補（長さの欄が無い）"})
    assert Y.summarized_before_ready({"duration_sec": 0, "summary_method": "video"})
    assert not Y.summarized_before_ready({"duration_sec": 1200})
    assert not Y.summarized_before_ready({"title": "長さの欄が無い古い記録"})


def test_long_videos_from_the_old_path_are_redone_once(monkeypatch):
    monkeypatch.setattr(Y, "hours_since", lambda s: 5.0)
    old = {"duration_sec": 4939, "summary_method": "video", "published": "p"}
    assert Y.needs_resummary(old)                                         # 前の道（記録なし）で作った長い動画
    assert Y.needs_resummary(dict(old, summary_method="text"))            # 題名と説明文だけの要約
    assert not Y.needs_resummary(dict(old, summary_engine=Y.SUMMARY_ENGINE))
    assert not Y.needs_resummary(dict(old, summary_engine="sdk", lowres_tried=True))   # 新しい道で試した＝毎回やり直さない
    assert not Y.needs_resummary(dict(old, duration_sec=1200))            # 短い動画はふつうの画質で読める
    monkeypatch.setattr(Y, "hours_since", lambda s: 80.0)
    assert not Y.needs_resummary(old)                                     # 窓の外は外すと作り直せない＝残す


def test_summary_reads_with_low_resolution_first(monkeypatch):
    seen = {}

    def fake(url, prompt, key, **kw):
        seen["prompt"] = prompt
        return "要約", "gm", {}

    monkeypatch.setattr(Y.gemini_youtube, "generate_from_youtube", fake)
    assert Y.summarize_with_gemini_video("u", "題名", "ch", "k") == ("要約", Y.SUMMARY_ENGINE)
    assert "題名" in seen["prompt"]
    monkeypatch.setattr(Y.gemini_youtube, "generate_from_youtube",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x")))
    monkeypatch.setitem(sys.modules, "google.generativeai", None)          # SDK が無い環境＝予備の道も無い
    assert Y.summarize_with_gemini_video("u", "題名", "ch", "k") == (None, None)


def test_fetch_channel_videos_marks_live(monkeypatch):
    def fake_get(endpoint, params, key):
        if endpoint == "channels":
            return {"items": [{"contentDetails": {"relatedPlaylists": {"uploads": "UU"}}}]}
        if endpoint == "playlistItems":
            return {"items": [{"contentDetails": {"videoId": VID}}]}
        assert "liveStreamingDetails" in params["part"]
        return {"items": [_item({"actualStartTime": "2026-11-15T03:00:00Z"}, "P0D", "live")]}

    monkeypatch.setattr(Y, "_youtube_api_get", fake_get)
    v = Y.fetch_channel_videos_api("UC", "FXism", "k")[0]
    assert v["published"] == "2026-11-15T03:00:00Z" and v["live_status"] == "live" and v["duration_sec"] == 0
    assert Y.not_ready_for_summary(v)


# ── 動画1本の分析 ──
def test_analyze_single_and_segmented(monkeypatch):
    seen = []

    def fake_video(url, prompt, key, start_sec=None, end_sec=None, log=print, **kw):
        seen.append((start_sec, end_sec, "区間" in prompt))
        return f"メモ{len(seen)}", "gm", {"promptTokenCount": 100}

    monkeypatch.setattr(G, "generate_from_youtube", fake_video)
    monkeypatch.setattr(G, "generate", lambda body, key, log=print, **kw: ("まとめ", "gm", {"promptTokenCount": 5}))
    text, model, tokens = A.analyze("u", "データの出どころは？", "k", {"duration_sec": 3600}, log=lambda m: None)
    assert (text, model, tokens) == ("メモ1", "gm", 100) and seen == [(None, None, False)]
    seen.clear()
    text, model, tokens = A.analyze("u", "", "k", {"duration_sec": 12000}, log=lambda m: None)
    assert text == "まとめ" and tokens == 305 and [s[:2] for s in seen] == [(0, 5400), (5400, 10800), (10800, 12000)]
    assert all(s[2] for s in seen)


def test_question_goes_into_prompt(monkeypatch):
    got = {}
    monkeypatch.setattr(G, "generate_from_youtube",
                        lambda url, prompt, key, log=print, **kw: (got.setdefault("p", prompt), "gm", {}))
    A.analyze("u", "買い比率のデータはどこの会社？", "k", None, log=lambda m: None)
    assert "買い比率のデータはどこの会社？" in got["p"] and "推測で埋めない" in got["p"]


def test_main_stops_before_the_stream_has_content(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.setattr(G, "fetch_video_info", lambda vid, key: G.video_info_from_item(_item({}, "P0D", "upcoming")))
    monkeypatch.setattr(G, "generate_from_youtube", lambda *a, **k: pytest.fail("配信前なのに読ませた"))
    assert A.main(["--url", f"https://youtu.be/{VID}", "--out", str(tmp_path / "a.md")]) == 3
    assert not (tmp_path / "a.md").exists()


def test_main_writes_analysis_with_disclaimer(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.setattr(G, "fetch_video_info", lambda vid, key: G.video_info_from_item(_item()))
    monkeypatch.setattr(G, "generate_from_youtube", lambda *a, **k: ("## 1. 動画の概要\n- 本文", "gm", {"promptTokenCount": 9}))
    out = tmp_path / "a.md"
    assert A.main(["--url", f"https://www.youtube.com/watch?v={VID}", "--out", str(out)]) == 0
    md = out.read_text(encoding="utf-8")
    assert "## 1. 動画の概要" in md and "投資助言ではありません" in md and "1:30:05" in md
    assert A.main(["--url", "https://example.com/"]) == 2


def test_workflow_passes_inputs_by_env_and_never_writes_the_repo():
    y = open(os.path.join(ROOT, ".github", "workflows", "youtube-analyze.yml"), encoding="utf-8").read()
    run_lines = [ln for ln in y.splitlines() if ln.strip().startswith("run:")]
    assert run_lines and not any("${{" in ln for ln in run_lines)
    assert "contents: read" in y and "git push" not in y and "git commit" not in y
    assert "workflow_dispatch" in y and "schedule" not in y
    assert "secrets.GEMINI_API_KEY" in y


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
