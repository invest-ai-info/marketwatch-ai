# -*- coding: utf-8 -*-
"""
check_automation_health.py — 裏方の自動化（GitHub Actions / 予約エージェント routine）が
「ちゃんと走っているか」を点検する番人。health-check.yml は公開6ページの死活を見るが、
こちらはその死角＝シグナル/政治フィード/ファンダ/パニックスキャン/研究日誌等の沈黙の失敗を検知する。

3方式（誤検知を避けるため）:
  ① Actions ワークフロー … Actions API で「直近の実行が成功か＋実行が新しいか」を見る
     （commit-on-change なジョブでもファイル鮮度に惑わされない）
  ② クラウド routine     … 毎回再生成する出力ファイルの最終コミット時刻で鮮度を見る
  ③ 公開記事カバレッジ   … guide-signal-lab-* / guide-news-* が guides.html にカードとして
     載っているかをリポジトリ状態で照合（local-drift 巻き戻し事故の早期検知＝B「カバレッジ番人」）

判定: critical/warn が1件でも異常なら exit 1（workflow が Issue を立てる）。info のみ/全正常なら exit 0。
実行: GitHub Actions（automation-health.yml）／ローカルでも可。
"""
import os
import sys
import json
import datetime as dt

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
try:  # Norton等のHTTPSスキャン対策（ローカル実行用。Actionsでは無くても可）
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass

import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))

# ① Actions ワークフロー: (ラベル, ワークフローyml, 直近実行の許容経過[時間], 重大度)
WORKFLOW_CHECKS = [
    ("テクニカルアラート(4H)",  "technical-alerts.yml",    6,  "critical"),
    # 2026-07-05: 3h→5h/4h に緩和。GitHub cron混雑で1H/30分ジョブが3〜4.5h滑るのは日常で、
    # 3h閾値だと毎日誤検知メール（6月末〜7月に連日発火した実績）。5h=1Hジョブが4回連続で
    # 消えたら検知＝本物の停止は引き続き当日中に捕まえる。
    ("1Hシグナル収集",          "technical-alerts-1h.yml", 5,  "warn"),
    ("政治発言フィード",        "political-alerts.yml",    4,  "critical"),
    ("市況ニュース生成",        "update-market-news.yml",  15, "warn"),
    # 🆕 2026-07-09 ⚡最新ニュース・ライブフィード（毎時）。cron滑りは日常なので5h=4〜5回連続消失で検知。
    ("最新ニュース・ティッカー", "news-ticker.yml",         5,  "warn"),
    ("パニック反発スキャン",    "panic-scan.yml",          27, "warn"),
    # 🆕 低頻度ジョブ（2026-07 追加）。7/1 に monthly-report が取りこぼされ6月レポート未生成の事故で、
    #    週次/月次が監視対象外＝盲点と判明。正常運用で誤検知しないよう余裕を持たせた閾値。
    #    max_h は「1回まるごとスキップされたら検知」水準：週次=10日 / 月次=35日。
    ("週次振り返り",            "weekly-review.yml",       24 * 10, "warn"),
    ("週次投資戦略",            "weekly-strategy.yml",     24 * 10, "warn"),
    ("月次成績レポート",        "monthly-report.yml",      24 * 35, "warn"),
    ("月次バックアップ",        "monthly-backup.yml",      24 * 35, "warn"),
    ("月次カレンダー補充",      "monthly-calendar-reminder.yml", 24 * 35, "warn"),
]

# ② クラウド routine: (ラベル, 毎回再生成される出力ファイル, 許容経過[時間], 重大度)
ROUTINE_FILE_CHECKS = [
    ("市況ファンダ・ブリーフィング", "fundamental-context.json", 15, "warn"),
    ("研究日誌・日次研究会",        "drafts/REVIEW.md",         28, "info"),
    ("記事ネタ発掘",                "article-ideas.md",         28, "info"),
    # 🆕 2026-07-04: signal-lab-daily が draft は公開するのに tracker.json のコミットだけ漏らす事故が
    #    7/3・7/4 に連続発生（REVIEW.md は更新されるため上の監視では見えない盲点）。毎朝 06:10 の
    #    routine が毎回 commit する前提＝26h で「1回漏れ」を当日の本チェック(09:30)で検知できる。
    ("シグナル前向きトラッカー",    "signal-lab-tracker.json",  26, "warn"),
    # 🆕 2026-07-07: 進化ループ①INTAKE（idea-scout-weekly・毎週日曜14:00）。週次＝閾値10日で「1回漏れ」検知。
    #    autodraft-articleのpushレース沈黙が鮮度監視をすり抜けた前例（7/4-7/5）への横展開＝専用行で監視。
    ("週次アイデアスカウト",        "drafts/idea-inbox.md",     240, "info"),
]

# ④ 固定ゲートの不変条件: ゲート/リンターを routine が書き換えて通過する「自己承認」を検知する。
#    2026-07-09 に autopublish が check_site_consistency.py のクラウドスタブ分岐を独自実装へ
#    書き換えて commit した実例（routine プロンプトの編集禁止指示だけでは防げなかった）への対策。
#    オーナー決定（2026-07-09）＝routine によるゲート編集は等価修正でも完全禁止・赤はエスカレのみ。
#    許可 author はオーナー（ローカル sync）と github-actions[bot] のみ。それ以外は warn（Issue化）。
GATE_FILES = [
    "check_site_consistency.py",
    "check_guide_draft.py",
    "signal_lab_verify.py",
    "publish_article.py",
]
GATE_WINDOW_H = 26  # 毎日09:30実行＋cron滑りをカバー（>24h。稀に同じ違反を2日連続報告するのは許容）

SEV = {"critical": "🔴", "warn": "🟡", "info": "⚪"}


def get_cfg():
    owner = os.environ.get("GH_OWNER")
    repo = os.environ.get("GH_REPO")
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not (owner and repo and token):
        try:
            with open(os.path.join(ROOT, "market-news-config.json"), encoding="utf-8-sig") as f:
                c = json.load(f)
            owner = owner or c.get("github_owner")
            repo = repo or c.get("github_repo")
            token = token or c.get("github_token")
        except Exception:
            pass
    return owner, repo, token


def api(url, token):
    req = urllib.request.Request(url, headers={
        "Authorization": f"token {token}",
        "User-Agent": "automation-healthcheck",
        "Accept": "application/vnd.github+json",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def api_raw(url, token):
    """ファイル内容を生テキストで取得（contents API + raw media type）。サイズ上限/Base64不要。"""
    req = urllib.request.Request(url, headers={
        "Authorization": f"token {token}",
        "User-Agent": "automation-healthcheck",
        "Accept": "application/vnd.github.raw",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")


def age_hours(iso, now):
    ts = dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return (now - ts).total_seconds() / 3600.0


def check_workflow(owner, repo, token, wf, max_h, now):
    """直近の実行が（completed かつ success）で、かつ max_h 以内か。"""
    data = api(f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/{wf}/runs?per_page=1", token)
    runs = data.get("workflow_runs", [])
    if not runs:
        return False, "実行履歴なし"
    r = runs[0]
    a = age_hours(r["created_at"], now)
    agetxt = f"{a:.1f}h前" if a < 48 else f"{a/24:.1f}日前"
    if r.get("status") != "completed":
        return True, f"実行中（{r.get('status')}）"  # 走行中はOK扱い
    if r.get("conclusion") != "success":
        return False, f"直近実行が失敗（{r.get('conclusion')}・{agetxt}）"
    if a > max_h:
        return False, f"{max_h}h以上動いていない（最後の成功 {agetxt}）"
    return True, f"成功 {agetxt}"


def check_file(owner, repo, token, path, max_h, now):
    data = api(f"https://api.github.com/repos/{owner}/{repo}/commits?path={path}&per_page=1", token)
    if not data:
        return False, "コミット履歴なし"
    a = age_hours(data[0]["commit"]["committer"]["date"], now)
    agetxt = f"{a:.1f}h前" if a < 48 else f"{a/24:.1f}日前"
    if a > max_h:
        return False, f"{max_h}h以上更新なし（最終 {agetxt}）"
    return True, f"更新 {agetxt}"


# ③ 公開記事カバレッジ（巻き戻し検知）の対象 prefix。新シリーズが増えたらここに足すだけ。
CARD_COVERAGE_PREFIXES = ("guide-signal-lab-", "guide-news-")


def list_repo_root_files(owner, repo, token):
    """リポジトリ直下のファイル名一覧を Git Trees API で取得（非recursive＝rootのみ・1000件制限なし）。"""
    data = api(f"https://api.github.com/repos/{owner}/{repo}/git/trees/main", token)
    return [t.get("path", "") for t in data.get("tree", []) if t.get("type") == "blob"]


def check_card_coverage(owner, repo, token):
    """公開済みの guide-signal-lab-* / guide-news-* が guides.html にカードとして載っているか
    をリポジトリ状態で照合する。載っていない＝local-drift で巻き戻された疑い（B「カバレッジ番人」）。
    ローカルの陳腐化に惑わされないよう、対象一覧も guides.html も GitHub 側の最新を読む。
    戻り値: (対象ファイル名のソート済みリスト, 未掲載ファイル名リスト)。"""
    root = list_repo_root_files(owner, repo, token)
    targets = sorted(n for n in root
                     if n.endswith(".html") and n.startswith(CARD_COVERAGE_PREFIXES))
    guides = api_raw(f"https://api.github.com/repos/{owner}/{repo}/contents/guides.html", token)
    missing = [n for n in targets if f'href="{n}"' not in guides]
    return targets, missing


def check_gate_immutability(owner, repo, token, now):
    """直近 GATE_WINDOW_H 時間に GATE_FILES を「オーナー／github-actions[bot] 以外」の author が
    変更した commit を列挙する（routine のゲート自己改変検知）。
    戻り値: [(path, sha7, author表示, 経過h), ...]（空＝違反なし）"""
    since = (now - dt.timedelta(hours=GATE_WINDOW_H)).strftime("%Y-%m-%dT%H:%M:%SZ")
    allowed = {owner.lower(), "github-actions[bot]", "web-flow"}  # web-flow=GitHub Web UI編集の committer
    hits = []
    for path in GATE_FILES:
        data = api(f"https://api.github.com/repos/{owner}/{repo}/commits?path={path}"
                   f"&since={since}&per_page=10", token)
        for cm in data:
            login = ((cm.get("author") or {}).get("login") or "").lower()
            name = cm.get("commit", {}).get("author", {}).get("name", "?")
            if login in allowed:
                continue
            a = age_hours(cm["commit"]["author"]["date"], now)
            hits.append((path, cm.get("sha", "")[:7], f"{name}(login={login or '不明'})", a))
    return hits


def main():
    owner, repo, token = get_cfg()
    if not (owner and repo and token):
        print("❌ owner/repo/token を取得できません（env か market-news-config.json）")
        sys.exit(2)

    now = dt.datetime.now(dt.timezone.utc)
    jst = now.astimezone(dt.timezone(dt.timedelta(hours=9)))
    body = [f"# 🩺 自動化ヘルスチェック（{jst:%Y-%m-%d %H:%M} JST）", ""]
    bad = []  # (label, severity)

    body.append("### ① GitHub Actions ワークフロー")
    for label, wf, max_h, sev in WORKFLOW_CHECKS:
        try:
            ok, note = check_workflow(owner, repo, token, wf, max_h, now)
        except Exception as e:
            ok, note = False, f"確認失敗 {e}"
        body.append(f"- {'✅' if ok else '🚨'} {SEV[sev]} {label}: {note}")
        if not ok:
            bad.append((label, sev))

    body.append("")
    body.append("### ② 予約エージェント routine（出力ファイルの鮮度）")
    for label, path, max_h, sev in ROUTINE_FILE_CHECKS:
        try:
            ok, note = check_file(owner, repo, token, path, max_h, now)
        except Exception as e:
            ok, note = False, f"確認失敗 {e}"
        body.append(f"- {'✅' if ok else '🚨'} {SEV[sev]} {label}: {note}")
        if not ok:
            bad.append((label, sev))

    body.append("")
    body.append("### ③ 公開記事カバレッジ（guides.html カードの巻き戻し検知）")
    try:
        targets, missing = check_card_coverage(owner, repo, token)
        if not targets:
            body.append("- ⚪ 対象記事（guide-signal-lab-* / guide-news-*）がまだ無い")
        elif missing:
            body.append(f"- 🚨 🟡 {len(missing)}/{len(targets)} 件が guides.html に未掲載"
                        f"（巻き戻しの疑い）: " + ", ".join(missing))
            bad.append(("guides.htmlカード欠落", "warn"))
        else:
            body.append(f"- ✅ 🟢 公開記事 {len(targets)} 件すべてが guides.html に掲載済み")
    except Exception as e:
        # API一時エラーで毎朝Issueを立てないよう、確認失敗自体は info 扱い（記録のみ・誤検知回避）
        body.append(f"- 🚨 ⚪ カバレッジ確認失敗: {e}")

    body.append("")
    body.append("### ④ 固定ゲートの不変条件（routineによるゲート編集＝自己承認の検知）")
    try:
        hits = check_gate_immutability(owner, repo, token, now)
        if hits:
            for path, sha, who, a in hits:
                agetxt = f"{a:.1f}h前" if a < 48 else f"{a/24:.1f}日前"
                body.append(f"- 🚨 🟡 {path} が {who} により変更されている（{sha}・{agetxt}）"
                            f"＝routineのゲート編集は完全禁止（オーナー決定 2026-07-09）。差分を確認し、"
                            f"正なら人間がローカルから採用、不正なら revert")
            bad.append(("固定ゲートのroutine改変", "warn"))
        else:
            body.append(f"- ✅ 🟢 直近{GATE_WINDOW_H}hのゲート変更はオーナー/Actionsのみ"
                        f"（対象{len(GATE_FILES)}本）")
    except Exception as e:
        # ③と同じ方針: API一時エラー自体では Issue を立てない（記録のみ）
        body.append(f"- 🚨 ⚪ ゲート不変条件の確認失敗: {e}")

    body.append("")
    serious = [l for l, s in bad if s in ("critical", "warn")]
    if bad:
        body.insert(1, f"## 🚨 {len(bad)}件に異常: " + " / ".join(l for l, _ in bad) + "\n")
    else:
        body.insert(1, "## ✅ すべての自動化が正常稼働\n")
    out = "\n".join(body)
    print(out)
    with open(os.path.join(ROOT, "automation_health_report.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(out)
    sys.exit(1 if serious else 0)


if __name__ == "__main__":
    main()
