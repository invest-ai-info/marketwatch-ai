# -*- coding: utf-8 -*-
"""
mw.py — MarketWatch AI 司令塔CLI（スクリプト名を覚えなくていい単一入口）
================================================================================
コマンド:
  python mw.py check                      サイト整合性チェック（リンター）
  python mw.py publish --file ... [...]    記事公開を一気通貫（②〜⑤→check→sync→workflow起動）
  python mw.py sync                        ローカル→GitHub 同期（sync_to_github.py）
  python mw.py deploy [--trigger]          自己修復デプロイ：syncをリトライ付き→(任意でworkflow)→ライブ検証
                                           （決定論・モデル不使用＝トークン0・上限はDEPLOY_*定数で固定）
  python mw.py trigger <workflow.yml>      GitHub Actions を手動起動（workflow_dispatch）
  python mw.py status [workflow.yml]       直近の workflow 実行状況
  python mw.py issues                      open な health-check/automation-health Issue 一覧（トリアージ②の土台）
  python mw.py audit                       guide記事の改善候補をスコア化（記事改善③の土台）
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
import time
import subprocess
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SD = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable

# ══ deploy（自己修復デプロイ）のハード上限：ここを見れば「暴走しない」と分かる ══
#    モデル不使用＝トークン消費ゼロ。下の上限のどれかで必ず停止する。
DEPLOY_MAX_ATTEMPTS  = 5         # sync の最大試行回数（運用ルール「ネット不調時は最大3〜5回」）
DEPLOY_BACKOFF_SEC   = 60        # 失敗時の待機（秒）＝throttle の自然回復待ち
DEPLOY_TOTAL_CAP_SEC = 15 * 60   # 合計の打ち切り時間（秒）＝超えたら無条件停止
LIVE_BASE            = "https://marketwatch-jp.com/"
DEPLOY_CHECK_PAGES   = ["guides.html", "index.html"]   # ライブ検証する代表ページ


def _env():
    e = dict(os.environ)
    e["PYTHONUTF8"] = "1"
    e["PYTHONIOENCODING"] = "utf-8"
    return e


def _run(args):
    """同梱スクリプトをサブプロセス実行。戻り値 = exit code。"""
    return subprocess.call([PY] + args, cwd=SD, env=_env())


def _run_capture(args):
    """同梱スクリプトを実行し (exit code, stdout) を返す（deploy の 🚫/❌ 判別用）。"""
    r = subprocess.run([PY] + args, cwd=SD, env=_env(), capture_output=True, text=True)
    return r.returncode, (r.stdout or "")


def _api_alive(timeout=12):
    try:
        urllib.request.urlopen("https://api.github.com/zen", timeout=timeout)
        return True
    except Exception:
        return False


def _http_ok(url, timeout=20):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return getattr(r, "status", 200) == 200
    except Exception:
        return False


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


def cmd_deploy(argv):
    """自己修復デプロイ：sync をリトライ付きで回す→(任意でworkflow)→ライブ検証。
    決定論・モデル不使用＝トークン0。上限は DEPLOY_* 定数で固定＝構造的に永久ループ不能。
      ❌接続失敗(throttle)＝backoffして最大 DEPLOY_MAX_ATTEMPTS 回まで再試行
      🚫staleガード(ローカルが古い)＝リトライ無効なので即エスカレ停止
      成功 / 上限回数 / 合計上限時間 のどれかで必ず停止。"""
    trigger = "--trigger" in argv
    start = time.monotonic()
    print("🔁 自己修復デプロイ（決定論・モデル不使用＝トークン0）")
    print(f"   ガード: 最大{DEPLOY_MAX_ATTEMPTS}回 / backoff{DEPLOY_BACKOFF_SEC}s / "
          f"合計上限{DEPLOY_TOTAL_CAP_SEC//60}分 → いずれかで必ず停止")
    synced = False
    for attempt in range(1, DEPLOY_MAX_ATTEMPTS + 1):
        if time.monotonic() - start > DEPLOY_TOTAL_CAP_SEC:
            print(f"\n⏹ 合計上限 {DEPLOY_TOTAL_CAP_SEC//60}分 到達 → 停止")
            break
        print(f"\n── 試行 {attempt}/{DEPLOY_MAX_ATTEMPTS} ──")
        if not _api_alive():
            print("  ⚠️ api.github.com 不通（throttle の可能性）")
        code, out = _run_capture(["sync_to_github.py"])
        for line in out.splitlines():
            if "完了:" in line or "すべて同期" in line:
                print("  " + line.strip())
        if code == 0:
            print(f"  ✅ sync 成功（{attempt} 回目）")
            synced = True
            break
        if "🚫" in out:
            print("  🚫 staleガード検知（GitHub側が新しい）＝リトライ無効 → 即エスカレ停止")
            print("     対応: 先に最新を取り込む（reconcile）か、意図的なら sync --force")
            return 2
        if attempt < DEPLOY_MAX_ATTEMPTS:
            if DEPLOY_TOTAL_CAP_SEC - (time.monotonic() - start) <= DEPLOY_BACKOFF_SEC:
                print("  ⏹ 残り時間が backoff 未満 → 停止")
                break
            print(f"  ⏳ throttle のため {DEPLOY_BACKOFF_SEC}s 待機して再試行…")
            time.sleep(DEPLOY_BACKOFF_SEC)
    if not synced:
        print("\n🚩 sync が上限内に成功せず → 手動対応へエスカレ（停止）")
        try:
            c = _cfg()
            print(f"   ブラウザ手動trigger: https://github.com/{c['github_owner']}/{c['github_repo']}/actions")
        except Exception:
            pass
        return 1
    if trigger:
        print("\n🚀 workflow 起動（update-market-news.yml）")
        cmd_trigger(["update-market-news.yml"])
    print("\n🔎 ライブ検証（GitHub Pages のビルドに数分かかる場合あり）")
    all_ok = True
    for p in DEPLOY_CHECK_PAGES:
        ok = _http_ok(LIVE_BASE + p)
        print(f"  {'✅' if ok else '❌'} {p}: HTTP {'200' if ok else 'NG'}")
        all_ok = all_ok and ok
    print("\n🎉 デプロイ完了・ライブ正常" if all_ok
          else "\n⚠️ sync は完了。ライブ未確認＝Pages ビルド待ちの可能性 → 数分後に再確認")
    return 0


def cmd_issues(argv):
    """open な health-check / automation-health Issue を一覧（決定論・トリアージの土台）。
    判断（原因診断・修正提案）は上限付き /loop でモデルに渡す。これは"データ収集"だけ＝トークン0。"""
    labels = "health-check,automation-health"
    try:
        _, data = _gh("GET", f"/issues?state=open&labels={labels}&per_page=30")
    except Exception as e:
        print(f"❌ 取得失敗: {e}")
        return 1
    issues = [it for it in data if "pull_request" not in it]
    if not issues:
        print("✅ open な health-check / automation-health Issue は無し（裏方は健全）")
        return 0
    print(f"🚨 トリアージ対象 open Issue {len(issues)} 件:")
    for it in issues:
        labs = ",".join(l.get("name", "") for l in it.get("labels", []))
        title = (it.get("title", "") or "")[:70]
        body = (it.get("body", "") or "").strip().replace("\n", " ")[:140]
        print(f"  #{it.get('number')} [{labs}] {title}")
        print(f"      {body}")
        print(f"      {it.get('html_url')}")
    return 0


def cmd_audit(argv):
    """guide-*.html の改善候補をスコア化（決定論・記事改善ループの土台）。
    弱点シグナル: meta description 無/短・本文が短い・内部guideリンクが少ない・JSON-LD無。score高=要改善。
    🆕 noindex ページは「意図的に薄く隠した自動生成」＝改善対象でないので別枠カウントし、
       本当に直すべき"インデックス対象の薄ページ"だけを候補に出す（false positive 排除）。"""
    import glob
    import re
    rows = []
    noindex_thin = 0
    for p in sorted(glob.glob(os.path.join(SD, "guide-*.html"))):
        fn = os.path.basename(p)
        try:
            html = open(p, encoding="utf-8").read()
        except Exception:
            continue
        noindex = bool(re.search(r'<meta\s+name="robots"[^>]*noindex', html))
        m = re.search(r'<meta name="description" content="([^"]*)"', html)
        desc_len = len(m.group(1)) if m else 0
        body = re.sub(r'(?is)<(script|style)[^>]*>.*?</\1>', ' ', html)
        text_len = len(re.sub(r'\s+', '', re.sub(r'(?s)<[^>]+>', ' ', body)))
        guide_links = len(set(re.findall(r'href="(guide-[a-z0-9-]+\.html)"', html)))
        has_jsonld = 'application/ld+json' in html
        score = (2 if desc_len < 60 else 0) + (2 if text_len < 2500 else 0) \
            + (1 if guide_links < 3 else 0) + (0 if has_jsonld else 1)
        if score >= 2 and noindex:
            noindex_thin += 1   # 意図的に隠した薄ページ＝AdSense対策済み＝対象外
            continue
        if not noindex:
            rows.append((score, fn, desc_len, text_len, guide_links, has_jsonld))
    rows.sort(reverse=True)
    weak = [r for r in rows if r[0] >= 2]
    total_indexed = len(rows)
    print(f"🔎 インデックス対象 guide {total_indexed} 件中 改善候補(score≥2) {len(weak)} 件（score高=要改善）")
    print(f"   ＋ noindex の薄ページ {noindex_thin} 件は意図的除外済み＝対象外（AdSense対策済み）")
    if weak:
        print(f"  {'score':>5} {'desc':>4} {'本文':>6} {'内部L':>5} {'jsonld':>6}  file")
        for score, fn, dl, tl, gl, jl in weak[:15]:
            print(f"  {score:>5} {dl:>4} {tl:>6} {gl:>5} {'有' if jl else '無':>6}  {fn}")
    else:
        print("  ✅ インデックス対象に目立つ弱点記事なし（公開コンテンツは健全）")
    return 0


CMDS = {
    "check": cmd_check, "publish": cmd_publish, "sync": cmd_sync,
    "trigger": cmd_trigger, "status": cmd_status, "routines": cmd_routines,
    "deploy": cmd_deploy, "issues": cmd_issues, "audit": cmd_audit,
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
