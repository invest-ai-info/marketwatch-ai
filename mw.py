# -*- coding: utf-8 -*-
"""
mw.py — MarketWatch AI 司令塔CLI（スクリプト名を覚えなくていい単一入口）
================================================================================
コマンド:
  python mw.py check                      サイト整合性チェック（リンター）
  python mw.py publish --file ... [...]    記事公開を一気通貫（②〜⑤→check→sync→workflow起動）
  python mw.py sync                        ローカル→GitHub 同期（sync_to_github.py）
  python mw.py trigger <workflow.yml>      GitHub Actions を手動起動（workflow_dispatch）
  python mw.py status [workflow.yml]       直近の workflow 実行状況
  python mw.py routines                    予約エージェント routine 一覧（参照）

publish の流れ（--dry-run で②〜⑤の確認のみ）:
  python mw.py publish --file guide-xxx.html --category 個別銘柄解説 --emoji 🏰 \
      --card-title "短めタイトル" --desc "カード説明文"
  → ②〜⑤(publish_article) → 整合性チェック → ⑥sync → ⑦workflow起動
  → ⑧確認は `python mw.py status update-market-news.yml`
"""
import os
import sys
import json
import subprocess
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SD = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable


def _env():
    e = dict(os.environ)
    e["PYTHONUTF8"] = "1"
    e["PYTHONIOENCODING"] = "utf-8"
    return e


def _run(args):
    """同梱スクリプトをサブプロセス実行。戻り値 = exit code。"""
    return subprocess.call([PY] + args, cwd=SD, env=_env())


def _cfg():
    for name in ("market-news-config.json.json", "market-news-config.json"):
        p = os.path.join(SD, name)
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                return json.load(f)
    raise FileNotFoundError("market-news-config が見つかりません")


def _gh(method, path, body=None):
    c = _cfg()
    url = f"https://api.github.com/repos/{c['github_owner']}/{c['github_repo']}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"token {c['github_token']}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "mw-cli",
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        t = r.read().decode()
        return r.status, (json.loads(t) if t.strip() else {})


def cmd_check(argv):
    return _run(["check_site_consistency.py"] + argv)


def cmd_sync(argv):
    print("📦 sync_to_github.py 実行...")
    return _run(["sync_to_github.py"])


def cmd_trigger(argv):
    if not argv:
        print("usage: python mw.py trigger <workflow.yml>")
        return 1
    wf = argv[0]
    try:
        st, _ = _gh("POST", f"/actions/workflows/{wf}/dispatches", {"ref": "main"})
        print(f"🚀 {wf} を起動 (HTTP {st})")
        return 0 if st in (200, 201, 204) else 1
    except Exception as e:
        print(f"❌ 起動失敗: {e}")
        return 1


def cmd_status(argv):
    wf = argv[0] if argv else None
    path = (f"/actions/workflows/{wf}/runs?per_page=5" if wf
            else "/actions/runs?per_page=8")
    try:
        _, data = _gh("GET", path)
    except Exception as e:
        print(f"❌ 取得失敗: {e}")
        return 1
    print(f"📊 直近の workflow 実行{(' : ' + wf) if wf else ''}")
    for r in data.get("workflow_runs", []):
        print(f"  {(r.get('name','?'))[:26]:26} {r.get('event',''):16} "
              f"{r.get('status',''):12} {str(r.get('conclusion','')):10} {r.get('created_at','')}")
    return 0


def cmd_routines(argv):
    ROUTINES = [
        ("fundamental-briefing", "毎日06/15", "fundamental-context.json", "trig_01M7uY1H8uR6tEwF1CJ7jXzV"),
        ("weekly-zone-plan", "日曜20:00", "weekly-zone-plan.md", "trig_01LP5pbD28BK55bE3GZWaHJf"),
        ("article-idea-scout", "毎日07:30", "article-ideas.md", "trig_01FmFNFSTkdx35nu1kWwKoYW"),
        ("daily-market-preview", "毎日21:00", "daily-preview.md", "trig_01GFQ6tLGPhvEZ5crJgPRqCh"),
        ("political-digest", "毎日22:00", "political-digest.md", "trig_01B1WV4bru6iFxr7SFB94huh"),
        ("compliance-patrol", "日曜09:00", "compliance-scan.md", "trig_016Pkyto4UfxhHP1sU2i5NP9"),
        ("weekly-strategy-brief", "日曜18:30", "weekly-strategy-context.json", "trig_01StownkcHrYyRbMMpVxVy2Z"),
    ]
    print("📋 予約エージェント routine（編集/実行は claude.ai/code/routines/<ID>）")
    for n, sch, out, tid in ROUTINES:
        print(f"  {n:24} {sch:10} → {out:32} {tid}")
    return 0


def cmd_publish(argv):
    dry = "--dry-run" in argv
    print("=== ②〜⑤ ファイル更新（publish_article.py）===")
    if _run(["publish_article.py"] + argv) != 0:
        print("❌ publish_article.py で失敗。中断。")
        return 1
    if dry:
        print("\nDRY-RUN のため終了（sync/workflowは実行しません）。")
        return 0
    print("\n=== 整合性チェック（check_site_consistency.py）===")
    if _run(["check_site_consistency.py", "--quiet"]) != 0:
        print("❌ 整合性エラーを検出。sync を中止しました。修正してから再実行してください。")
        return 1
    print("\n=== ⑥ sync（GitHubへ push）===")
    if _run(["sync_to_github.py"]) != 0:
        print("❌ sync 失敗。中断。")
        return 1
    print("\n=== ⑦ Update Market News 起動（index再生成）===")
    cmd_trigger(["update-market-news.yml"])
    print("\n✅ 公開フロー完了。⑧確認: `python mw.py status update-market-news.yml`")
    print("   （index再生成に数分。記事HTML自体は sync 済みなので即ライブ）")
    return 0


CMDS = {
    "check": cmd_check, "publish": cmd_publish, "sync": cmd_sync,
    "trigger": cmd_trigger, "status": cmd_status, "routines": cmd_routines,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    cmd = sys.argv[1]
    if cmd not in CMDS:
        print(f"unknown command: {cmd}\n{__doc__}")
        return 1
    return CMDS[cmd](sys.argv[2:]) or 0


if __name__ == "__main__":
    sys.exit(main())
