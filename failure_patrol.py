# -*- coding: utf-8 -*-
"""failure_patrol.py — 直近の「失敗した実行」を GitHub から集めて、巡回役が読む一覧を作る（2026-09-28 新設）。

routine `failure-mail-patrol`（毎朝 08:57 JST）が最初に実行する。手順書＝drafts/FAILURE_PATROL_GUIDE.md。

なぜ要るか: 定時の予約エージェントのセッションには Gmail の道具も GitHub の道具（mcp__github__*）も
入っていなかった（2026-09-28 の試運転で判明）。一方、同じ環境の通信は api.github.com へ認証つきで
届く（プロキシが付ける）ので、道具に頼らずここで集める。読むだけ・何も書き換えない。

出すもの（ワークフローごとに1件）:
- 失敗の回数・最初と最後の時刻（JST）・ブランチ・起動のされ方
- いまの状態＝そのあと同じワークフロー・同じブランチで成功した回があるか（あれば「解決済み」の候補）
- 最新の失敗の「失敗した段階」の名前と、エラーの注記（決まり文句は除く）
- ログは既定では取りにいかない（2026-09-28 オーナー判断「原因がわかって直せればログは読まなくてよい」。
  保管先 productionresultssa*.blob.core.windows.net はこの環境の通信設定で止められている）。原因は段階の名前＋再現でつかむ
- 見張り番（automation-health）なら、Issue の最新コメントの 🚨 行と、§④ のコミットが PR 経由かどうか

使い方:
  python failure_patrol.py                 # 直近26時間
  python failure_patrol.py --hours 50      # 期間を変える
  python failure_patrol.py --logs          # ログも取りにいく（通信が許可された環境だけで意味がある）
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = "invest-ai-info/marketwatch-ai"
API = "https://api.github.com/repos/"
JST = dt.timezone(dt.timedelta(hours=9))
FAIL_STATUSES = ("failure", "timed_out", "startup_failure")
HEALTH_WF = ".github/workflows/automation-health.yml"
# 注記のうち原因の手がかりにならない決まり文句
BORING = (
    re.compile(r"^Process completed with exit code \d+\.?$"),
    re.compile(r"Node\.js \d+ is deprecated"),
    re.compile(r"ubuntu-latest label will migrate"),
)
LOG_TAIL = 60


def api(path, repo=REPO, raw=False):
    """GitHub API を読む。GITHUB_TOKEN があれば使う（手元用）。クラウドではプロキシが認証を付ける。"""
    url = path if path.startswith("http") else API + repo + path
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json",
                                               "User-Agent": "failure-patrol"})
    tok = os.environ.get("GITHUB_TOKEN")
    if tok:
        req.add_header("Authorization", f"Bearer {tok}")
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read()
    return body.decode("utf-8", "replace") if raw else json.loads(body)


def parse_ts(s):
    return dt.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)


def jst(s):
    return parse_ts(s).astimezone(JST).strftime("%m/%d %H:%M")


# ── 純関数（テスト対象）────────────────────────────────────────────
def group_failures(runs):
    """失敗した回をワークフロー×ブランチでまとめる。新しい順の配列を返す。"""
    groups = {}
    for r in runs:
        if r.get("conclusion") not in FAIL_STATUSES:
            continue
        key = (r.get("path") or r.get("name"), r.get("head_branch"))
        groups.setdefault(key, []).append(r)
    out = []
    for (path, branch), rs in groups.items():
        rs.sort(key=lambda r: r["created_at"])
        out.append({"name": rs[-1].get("name"), "path": path, "branch": branch,
                    "workflow_id": rs[-1].get("workflow_id"), "count": len(rs),
                    "first": rs[0]["created_at"], "last": rs[-1]["created_at"],
                    "events": sorted({r.get("event") for r in rs}), "latest": rs[-1]})
    out.sort(key=lambda g: g["last"], reverse=True)
    return out


def later_success(last_failed_at, runs):
    """最後の失敗より後に始まって成功した回を返す（無ければ None）。runs は同じワークフロー・同じブランチ。"""
    ok = [r for r in runs if r.get("conclusion") == "success" and r["created_at"] > last_failed_at]
    return min(ok, key=lambda r: r["created_at"]) if ok else None


def useful_annotations(anns):
    """注記から、原因の手がかりになるもの（failure/warning で決まり文句でないもの）だけ残す。"""
    out = []
    for a in anns:
        msg = (a.get("message") or "").strip()
        if a.get("annotation_level") not in ("failure", "warning") or not msg:
            continue
        if any(p.search(msg) for p in BORING):
            continue
        out.append(msg.splitlines()[0][:300])
    return out


def alarm_lines(report):
    """見張り番の報告から 🚨 の行だけ取り出す（「確認失敗」の⚪も含む）。"""
    return [ln.strip() for ln in report.splitlines() if ln.strip().startswith("- 🚨")]


GATE_SHA = re.compile(r"により変更されている（([0-9a-f]{7,40})・")


def gate_shas(lines):
    """§④ の行からコミットの短い番号を取り出す（重複は除く・順番は保つ）。"""
    seen, out = set(), []
    for ln in lines:
        m = GATE_SHA.search(ln)
        if m and m.group(1) not in seen:
            seen.add(m.group(1))
            out.append(m.group(1))
    return out


# ── 集める（ネットワーク）──────────────────────────────────────────
def fetch_failed_runs(since):
    runs = []
    for st in FAIL_STATUSES:
        page = 1
        while page <= 5:
            d = api(f"/actions/runs?status={st}&created=>={since:%Y-%m-%dT%H:%M:%SZ}&per_page=100&page={page}")
            batch = d.get("workflow_runs", [])
            runs += batch
            if len(batch) < 100:
                break
            page += 1
    return runs


def failure_detail(run, want_logs):
    """最新の失敗の回について、失敗した段階・注記・ログの末尾を集める。"""
    detail = {"steps": [], "annotations": [], "log_tail": None, "log_error": None}
    jobs = api(f"/actions/runs/{run['id']}/jobs?per_page=50").get("jobs", [])
    for j in jobs:
        if j.get("conclusion") not in FAIL_STATUSES:
            continue
        for s in j.get("steps", []):
            if s.get("conclusion") in FAIL_STATUSES:
                detail["steps"].append(f"{j['name']} / {s['number']}. {s['name']}")
        try:
            detail["annotations"] += useful_annotations(api(f"/check-runs/{j['id']}/annotations"))
        except Exception as e:  # 注記が取れなくても続ける
            detail["annotations"].append(f"（注記の取得に失敗: {e}）")
        if want_logs and detail["log_tail"] is None:
            try:
                txt = api(f"/actions/jobs/{j['id']}/logs", raw=True)
                lines = [re.sub(r"^\S+Z ", "", ln) for ln in txt.splitlines()]
                cut = [i for i, ln in enumerate(lines) if "##[error]" in ln]
                end = (cut[0] + 3) if cut else len(lines)
                detail["log_tail"] = lines[max(0, end - LOG_TAIL):end]
            except Exception as e:
                detail["log_error"] = f"ログを取れない（{e}）＝段階の名前と再現で原因を確かめる"
    return detail


def health_detail(since):
    """見張り番の Issue（automation-health ラベル）の最新コメントから 🚨 行と §④ の PR を集める。"""
    issues = api("/issues?labels=automation-health&state=open&per_page=1")
    if not issues:
        return None
    iss = issues[0]
    comments = api(f"/issues/{iss['number']}/comments?since={since:%Y-%m-%dT%H:%M:%SZ}&per_page=100")
    body = comments[-1]["body"] if comments else iss.get("body", "")
    lines = alarm_lines(body)
    prs = {}
    for sha in gate_shas(lines):
        try:
            pulls = api(f"/commits/{sha}/pulls")
            merged = [p for p in pulls if p.get("merged_at") and p["base"]["ref"] == "main"]
            prs[sha] = f"PR #{merged[0]['number']} 経由（マージ済み）" if merged else "PR なし＝main へ直接（要確認）"
        except Exception as e:
            prs[sha] = f"確認失敗: {e}"
    return {"issue": iss["number"], "url": iss["html_url"], "lines": lines, "gate_prs": prs}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=float, default=26)
    ap.add_argument("--logs", action="store_true", help="ログも取りにいく（既定は取らない）")
    a = ap.parse_args()
    now = dt.datetime.now(dt.timezone.utc)
    since = now - dt.timedelta(hours=a.hours)

    print(f"# 失敗の一覧（{REPO}・直近{a.hours:g}時間・{now.astimezone(JST):%Y-%m-%d %H:%M} JST 時点）\n")
    try:
        groups = group_failures(fetch_failed_runs(since))
    except urllib.error.HTTPError as e:
        print(f"❌ GitHub の窓口を読めない（{e.code}）＝巡回できない。報告に書くこと"); sys.exit(2)
    if not groups:
        print("🟢 失敗した実行なし"); return

    for i, g in enumerate(groups, 1):
        last = g["latest"]
        try:
            after = api(f"/actions/workflows/{g['workflow_id']}/runs?branch={g['branch']}&per_page=20")
            fixed = later_success(g["last"], after.get("workflow_runs", []))
        except Exception:
            fixed = None
        state = (f"✅ そのあと成功（{jst(fixed['created_at'])}・{fixed['html_url']}）" if fixed
                 else "❗ そのあと成功した回はまだ無い")
        print(f"## {i}. {g['name']}（{g['path']}・ブランチ {g['branch']}）")
        print(f"- 失敗 {g['count']} 回（{jst(g['first'])}〜{jst(g['last'])} JST・起動: {'/'.join(g['events'])}）")
        print(f"- 最新の失敗: {last['html_url']}")
        print(f"- いまの状態: {state}")
        try:
            d = failure_detail(last, want_logs=a.logs)
        except Exception as e:
            print(f"- 詳細の取得に失敗: {e}\n"); continue
        for s in d["steps"]:
            print(f"- 失敗した段階: {s}")
        for m in d["annotations"]:
            print(f"- 注記: {m}")
        if g["path"] == HEALTH_WF:
            try:
                h = health_detail(since)
            except Exception as e:
                h = None
                print(f"- 見張り番の Issue を読めない: {e}")
            if h:
                print(f"- 見張り番の報告（Issue #{h['issue']} {h['url']}）の 🚨 行:")
                for ln in h["lines"]:
                    print(f"    {ln[:240]}")
                for sha, where in h["gate_prs"].items():
                    print(f"    §④ {sha}: {where}")
        if d["log_tail"]:
            print("- ログの末尾:")
            print("```")
            print("\n".join(d["log_tail"]))
            print("```")
        elif d["log_error"]:
            print(f"- {d['log_error']}")
        print()


if __name__ == "__main__":
    main()
