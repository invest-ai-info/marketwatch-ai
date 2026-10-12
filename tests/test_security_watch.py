# -*- coding: utf-8 -*-
"""週1回のセキュリティ点検（security_watch.py・security-watch.yml）のテスト。2026-10-12 新設。

通信はしない。確かめること＝①足された行だけから秘密の値を拾い、値は伏せる ②いま使っている鍵そのものを拾う
③知らない相手の書き込みを拾う ④巻き戻し防止の不足 ⑤知らない配信元のスクリプト・怪しい書き方
⑥公開ログに中身を書かない ⑦ワークフローは読むだけ・鍵を照合に渡す ⑧見張り番に登録済み。

実行:  python tests/test_security_watch.py     （pytest 不要。pytest でも動く）
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import security_watch as W  # noqa: E402

# 検査用のダミー。接頭辞と本体を分けて組み立てる（完全な形で書くと GitHub の push 保護に止められる）
FAKE_GH = "gh" + "p_" + "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
FAKE_GOOGLE = "AI" + "za" + "SyA1234567890abcdefghijklmnopqrstuv"
FAKE_KEY = "edinet-" + "0123456789abcdef"


def test_finds_secrets_only_in_added_lines_and_masks_them():
    log = [
        "@@@COMMIT 0123456789abcdef",
        "+++ b/notes/setup.py",
        f"+TOKEN = '{FAKE_GH}'",
        f"-OLD = '{FAKE_GOOGLE}'",           # 消した行は数えない
        "+++ b/config/x.json",
        f'+{{"k": "{FAKE_KEY}"}}',
        "@@@COMMIT fedcba9876543210",
        "+++ b/again.py",
        f"+again = '{FAKE_GH}'",              # 同じ値は1回だけ
    ]
    found = W.scan_added_lines(log, {"EDINET": FAKE_KEY})
    kinds = [(c, p, k) for c, p, k, _ in found]
    assert ("01234567", "notes/setup.py", "GitHub合鍵") in kinds, found
    assert ("01234567", "config/x.json", "いま使っている鍵（EDINET）") in kinds, found
    assert not any(k == "Google APIキー" for _, _, k in kinds), found
    assert len([k for _, _, k in kinds if k == "GitHub合鍵"]) == 1, found
    for _, _, _, v in found:
        assert FAKE_GH not in v and FAKE_KEY not in v and "文字" in v, v


def test_clean_lines_find_nothing():
    log = ["@@@COMMIT aaaaaaaa", "+++ b/a.py", "+x = os.environ['EDINET_API_KEY']", "+pat = r'gh[pousr]_[A-Za-z0-9]{36}'"]
    assert W.scan_added_lines(log, {"EDINET": FAKE_KEY}) == []


def test_unknown_writers():
    commits = [
        {"sha": "a" * 40, "author": {"login": "github-actions[bot]"}, "committer": {"login": "web-flow"}},
        {"sha": "b" * 40, "author": {"login": "claude"}, "committer": {"login": "invest-ai-info"}},
        {"sha": "c" * 40, "author": {"login": "stranger"}, "committer": {"login": "invest-ai-info"}},
        {"sha": "d" * 40, "author": None, "committer": {"login": "invest-ai-info"},
         "commit": {"author": {"name": "X", "email": "x@example.com"}}},
    ]
    got = W.unknown_writers(commits)
    assert ("cccccccc", "author", "stranger") in got, got
    assert ("dddddddd", "author", "X <x@example.com>") in got, got
    assert len(got) == 2, got


def test_missing_rules():
    assert W.missing_rules(["deletion", "non_fast_forward", "required_signatures"]) == []
    assert W.missing_rules([]) == ["deletion", "non_fast_forward"]


def test_script_problems():
    ok_html = ('<script src="https://www.googletagmanager.com/gtag/js?id=G-1"></script>'
               '<script src="site-search.js"></script><script src="//cdnjs.cloudflare.com/x.js"></script>')
    hosts = W.SITES["https://marketwatch-jp.com/"]["hosts"]
    assert W.script_problems(ok_html, hosts) == []
    bad_html = '<script src="https://evil.example/x.js"></script><script>eval(atob("YWxlcnQoMSk="))</script>'
    got = W.script_problems(bad_html, hosts)
    assert any("evil.example" in x for x in got) and any("怪しい" in x for x in got), got


def test_log_has_names_and_counts_only():
    results = [("新しく足された秘密の値（直近8日）", ["0123abcd secret/path.py: GitHub合鍵 ghp_…(40文字)"]),
               ("ドメインの向き先", [])]
    log = W.summary_for_log(results)
    assert "1件" in log and "OK" in log and "NG" in log
    assert "secret/path.py" not in log and "ghp_" not in log, log


def test_workflow_is_read_only_and_passes_keys():
    y = open(".github/workflows/security-watch.yml", encoding="utf-8").read()
    assert "permissions:\n  contents: read" in y and "write" not in y.split("jobs:")[0]
    assert "workflow_dispatch:" in y and "cron:" in y and "python security_watch.py" in y
    assert "fetch-depth: 0" in y
    for s in ("EDINET_API_KEY", "JQUANTS_API_KEY", "GEMINI_API_KEY", "GMAIL_APP_PASSWORD"):
        assert f"secrets.{s}" in y, s
    assert "git push" not in y and "git commit" not in y


def test_private_list_matches_pages_exclude():
    import check_site_consistency as csc
    ex = csc._pages_excludes(open("_config.yml", encoding="utf-8").read())
    for p in W.SITES["https://marketwatch-jp.com/"]["private"]:
        assert csc._pages_excluded(p, ex), f"{p} は _config.yml で外れていない＝点検が毎週鳴る"


def test_registered_in_automation_health():
    assert '"security-watch.yml"' in open("check_automation_health.py", encoding="utf-8").read()


if __name__ == "__main__":
    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("ok  ", name)
            except AssertionError as e:
                fails += 1
                print("FAIL", name, str(e)[:300])
    print("失敗", fails, "件")
    sys.exit(1 if fails else 0)
