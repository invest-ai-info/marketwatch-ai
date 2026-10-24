# -*- coding: utf-8 -*-
"""yt_method_notes.py（Gemini に動画を見せてメモを作る）の約束ごとのテスト。2026-10-24 新設。

YouTube にも Gemini にも問い合わせずに、次を固定する:
  --channel - と --ids では、チャンネルの一覧を取らずに oEmbed の題名・チャンネル名を使う／
  --kind summary では内容のまとめの指示を渡す（既定は手法のメモ）／--echo のときだけメモをログに出し、字幕は出さない。

実行:  python tests/test_yt_method_notes.py     （pytest 不要。pytest でも動く）
"""
import contextlib
import importlib.util
import io
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location("yt_method_notes", os.path.join(ROOT, "yt_method_notes.py"))
Y = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(Y)


def _run(argv, calls):
    """YouTube と Gemini を差し替えて run を動かす → (ログ, 出力フォルダの中身)"""
    def fake_list(channel):
        calls.append(("list", channel))
        return [{"id": "AAA", "title": "一覧の題名", "len": "10:00"}]

    def fake_meta(vid):
        calls.append(("meta", vid))
        return "単体の題名", "単体のチャンネル"

    def fake_notes(key, vid, title, channel, caption, models=Y.MODELS, tries=4, kind="method"):
        calls.append(("notes", vid, title, channel, kind))
        return f"メモ {vid}", models[0], {}

    Y.list_videos, Y.video_meta, Y.gemini_notes = fake_list, fake_meta, fake_notes
    Y.caption_text = lambda vid, limit=30000: "[0:00] 字幕の本文"
    os.environ["GEMINI_API_KEY"] = "x"
    with tempfile.TemporaryDirectory() as tmp:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            Y.main(["run", "--out", tmp, "--pause", "0"] + argv)
        files = {n: open(os.path.join(tmp, n), encoding="utf-8").read() for n in os.listdir(tmp)}
    return buf.getvalue(), files


def test_single_video_skips_channel_listing():
    calls = []
    log, files = _run(["--channel", "-", "--ids", "BBB", "--kind", "summary"], calls)
    assert not [c for c in calls if c[0] == "list"], calls
    assert ("notes", "BBB", "単体の題名", "単体のチャンネル", "summary") in calls, calls
    assert files["BBB.md"].startswith("# 単体の題名"), files["BBB.md"][:40]
    assert "BEGIN NOTES" not in log, "echo なしでメモをログに出した"


def test_echo_prints_notes_but_not_caption():
    calls = []
    log, _ = _run(["--channel", "-", "--ids", "BBB", "--echo"], calls)
    assert "----- BEGIN NOTES BBB -----" in log and "メモ BBB" in log and "----- END NOTES BBB -----" in log, log
    assert "字幕の本文" not in log, "字幕をログに出した"


def test_channel_mode_unchanged():
    calls = []
    _run(["--channel", "@someone", "--channel-name", "名前", "--ids", "AAA"], calls)
    assert ("list", "@someone") in calls, calls
    assert ("notes", "AAA", "一覧の題名", "名前", "method") in calls, calls
    assert not [c for c in calls if c[0] == "meta"], calls


def test_summary_prompt_formats():
    s = Y.PROMPTS["summary"].format(channel="c", title="t", caption="")
    assert "チャンネル「c」" in s and "題名「t」" in s and "要点" in s
    assert Y.PROMPTS["method"] is Y.PROMPT


if __name__ == "__main__":
    fails = 0
    tests = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for name, fn in tests:
        try:
            fn()
            print(f"  ✅ {name}")
        except AssertionError as e:
            fails += 1
            print(f"  ❌ {name}: {e}")
    print(f"--- {len(tests) - fails}/{len(tests)} 合格 ---")
    sys.exit(1 if fails else 0)
