# -*- coding: utf-8 -*-
"""週1回のセキュリティ点検（GitHub 側・読むだけ）。2026-10-12 新設（オーナー依頼「サイバー攻撃を確認・防ぐ」）。

見るもの（どれも書き換えない）:
  ① main の巻き戻し防止（ruleset の non_fast_forward・deletion）が marketwatch-ai と ai-tsukaikata で効いているか
  ② 直近8日の書き込みが、知っている相手（本人・github-actions・Claude・GitHub の画面）だけか
  ③ 直近8日に共同編集者が足されていないか（MemberEvent）
  ④ 直近8日に足された行に、秘密の値（鍵の形・いま Secrets に入っている鍵そのもの）が無いか
  ⑤ サイトで個人の記録・手順書・コードが開けないままか（_config.yml の exclude が効いているか）
  ⑥ サイトが読み込むスクリプトが、知っている配信元だけか・怪しい書き方が無いか
  ⑦ ドメインが GitHub Pages を指しているか

知らせ方: 要確認があるときだけ Gmail（GMAIL_USER／GMAIL_APP_PASSWORD／ALERT_RECIPIENT）。何も無ければ送らない。
⚠️ このリポジトリは公開＝Actions のログは誰でも読める。**ログには項目名と件数だけ**を出し、
   場所・値・メールアドレスなどの中身はメールにだけ書く。鍵の値はメールにも先頭4文字しか書かない。
PC 側の点検は手元の `_security_watch_pc.py`（タスク MarketWatch_Security_PC）。

実行: GitHub Actions（security-watch.yml・月曜朝）／手元でも `python security_watch.py --dry-run`（メールを送らず中身を表示）
"""
import datetime as dt
import json
import os
import re
import socket
import subprocess
import sys
import urllib.error
import urllib.request

OWNER = "invest-ai-info"
REPOS = ("marketwatch-ai", "ai-tsukaikata")
DAYS = 8
NEED_RULES = {"non_fast_forward", "deletion"}
KNOWN_LOGINS = {"github-actions[bot]", "invest-ai-info", "claude", "web-flow"}
PAGES_IPS = {"185.199.108.153", "185.199.109.153", "185.199.110.153", "185.199.111.153"}

SITES = {
    "https://marketwatch-jp.com/": {
        "pages": ["", "calendar.html", "charts.html", "vix.html", "guides.html", "track-record.html"],
        "hosts": {"www.googletagmanager.com", "pagead2.googlesyndication.com", "groot.mailerlite.com",
                  "cdnjs.cloudflare.com", "cdn.jsdelivr.net"},   # jsdelivr＝track-record の Chart.js
        # サイトで開けてはいけないもの（_config.yml の exclude・2026-10-12）
        "private": ["my-trades.json", "my-trades.csv", "MY_TRADING_RULES.md", "memory/01_profile.md",
                    "drafts/REVIEW.md", "compliance-scan.md", "CLAUDE.md", "generate_market_news.py"],
    },
    "https://ai-tsukaikata.com/": {
        "pages": [""],
        "hosts": {"pagead2.googlesyndication.com"},
        "private": [],
    },
}

# 鍵の形（部分一致で拾う）。検査用のダミーは接頭辞と本体を分けて書くこと（そのまま書くと push 保護に止められる）
SECRET_PATTERNS = {
    "GitHub合鍵": r"gh[pousr]_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{60,}",
    "Google APIキー": r"AIza[0-9A-Za-z_\-]{35}",
    "Google OAuth秘密": r"GOCSPX-[A-Za-z0-9_\-]{20,}",
    "秘密鍵": r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP |ENCRYPTED )?PRIVATE KEY",
    "AWSキー": r"(?:AKIA|ASIA)[0-9A-Z]{16}",
    "Slack": r"xox[baprs]-[0-9A-Za-z-]{10,}",
    "Anthropicキー": r"sk-ant-[A-Za-z0-9_\-]{20,}",
    "OpenAIキー": r"sk-proj-[A-Za-z0-9_\-]{40,}",
    "Googleシートの公開URL": r"docs\.google\.com/spreadsheets/d/e/2PACX-[\w\-]+",
}
_SECRET_RX = {k: re.compile(v) for k, v in SECRET_PATTERNS.items()}
# 毎日書き換わる大きなデータ（鍵が入る経路が無い）は差分を読まない＝実行時間を抑える
SKIP_DIFF = ("signals-log.json", "signals-log.csv", "*.gz")
SUSPICIOUS_JS = re.compile(r"eval\s*\(\s*atob|document\.write\s*\(\s*unescape|coinhive|cryptonight|"
                           r"String\.fromCharCode\((?:\s*\d+\s*,){20,}", re.I)


def mask(v):
    return v[:4] + f"…({len(v)}文字)"


# ---------------------------------------------------------------- 判定（通信しない＝テストで直接呼ぶ）

def scan_added_lines(lines, known):
    """`git log -p` の行を読み、足された行の秘密の値を返す。known={名前: 値}（いま使っている鍵）。

    返り値: [(commit, path, 種類, 伏せた値)]。同じ値は1回だけ。
    """
    found, seen, commit, path = [], set(), "?", "?"
    for line in lines:
        if line.startswith("@@@COMMIT "):
            commit = line.split()[1][:8]
            continue
        if line.startswith("+++ "):
            path = line[6:].strip() if line.startswith("+++ b/") else line[4:].strip()
            continue
        if not line.startswith("+"):
            continue
        body = line[1:]
        for name, val in known.items():
            if val and val in body and ("known", name) not in seen:
                seen.add(("known", name))
                found.append((commit, path, f"いま使っている鍵（{name}）", mask(val)))
        for kind, rx in _SECRET_RX.items():
            for m in rx.finditer(body):
                v = m.group(0)
                if (kind, v) in seen:
                    continue
                seen.add((kind, v))
                found.append((commit, path, kind, mask(v)))
    return found


def unknown_writers(commits):
    """書き込みのうち、知っている相手でないもの。[(sha, 役, login or 名前<メール>)]"""
    out = []
    for c in commits:
        for role in ("author", "committer"):
            acct = c.get(role) or {}
            login = acct.get("login")
            if login in KNOWN_LOGINS:
                continue
            raw = (c.get("commit") or {}).get(role) or {}
            who = login or f"{raw.get('name', '?')} <{raw.get('email', '?')}>"
            out.append((c.get("sha", "?")[:8], role, who))
    return out


def missing_rules(rule_types):
    return sorted(NEED_RULES - set(rule_types))


def script_problems(html, allowed_hosts):
    """読み込むスクリプトの配信元が知らないもの・怪しい書き方。[文字列]"""
    out = []
    for src in re.findall(r"<script[^>]+src\s*=\s*[\"']([^\"']+)", html, re.I):
        if src.startswith("//"):
            src = "https:" + src
        m = re.match(r"https?://([^/]+)", src)
        if m and m.group(1).lower() not in allowed_hosts:
            out.append(f"知らない配信元のスクリプト: {m.group(1)}")
    for m in SUSPICIOUS_JS.finditer(html):
        out.append(f"怪しい書き方: {m.group(0)[:40]}")
    for m in re.finditer(r"<iframe[^>]+src\s*=\s*[\"']([^\"']+)", html, re.I):
        out.append(f"iframe: {m.group(1)[:80]}")
    return out


def summary_for_log(results):
    """公開ログ用：項目名と件数だけ（中身は書かない）。"""
    lines = []
    for name, items in results:
        lines.append(f"  {'OK ' if not items else 'NG '} {name}" + (f"（{len(items)}件）" if items else ""))
    return "\n".join(lines)


# ---------------------------------------------------------------- 通信

def _get(url, token=None, accept="application/vnd.github+json"):
    req = urllib.request.Request(url, headers={"User-Agent": "mw-security-watch", "Accept": accept})
    if token and url.startswith("https://api.github.com"):
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.status, r.read()


def _status(url):
    try:
        st, _ = _get(url + ("&" if "?" in url else "?") + "v=" + str(int(dt.datetime.now().timestamp())), accept="*/*")
        return st
    except urllib.error.HTTPError as e:
        return e.code


def run_checks(token, known, since):
    results = []

    # ① 巻き戻し防止
    items = []
    for repo in REPOS:
        try:
            _, b = _get(f"https://api.github.com/repos/{OWNER}/{repo}/rules/branches/main", token)
            miss = missing_rules(r.get("type") for r in json.loads(b))
            if miss:
                items.append(f"{repo}: main に {miss} が無い＝force-push で履歴を消せる。"
                             f"Settings → Rules → Rulesets で Block force pushes と Restrict deletions を入れる")
        except Exception as e:
            items.append(f"{repo}: 確かめられず（{type(e).__name__}）")
    results.append(("main の巻き戻し防止", items))

    # ② 書き込んだ相手 ③ 共同編集者
    items, members = [], []
    for repo in REPOS:
        commits = []
        try:
            for page in range(1, 11):
                _, b = _get(f"https://api.github.com/repos/{OWNER}/{repo}/commits?since={since}&per_page=100&page={page}", token)
                got = json.loads(b)
                commits += got
                if len(got) < 100:
                    break
            items += [f"{repo} {sha} {role}: {who}" for sha, role, who in unknown_writers(commits)]
        except Exception as e:
            items.append(f"{repo}: 確かめられず（{type(e).__name__}）")
        try:
            _, b = _get(f"https://api.github.com/repos/{OWNER}/{repo}/events?per_page=100", token)
            for ev in json.loads(b):
                if ev.get("type") == "MemberEvent" and ev.get("created_at", "") >= since:
                    who = ((ev.get("payload") or {}).get("member") or {}).get("login", "?")
                    members.append(f"{repo}: {ev['created_at']} に共同編集者 {who} が {ev['payload'].get('action')}")
        except Exception as e:
            members.append(f"{repo}: 確かめられず（{type(e).__name__}）")
    results.append(("書き込んだ相手（直近8日）", items))
    results.append(("共同編集者の追加（直近8日）", members))

    # ④ 足された行の秘密の値（このリポジトリだけ＝チェックアウト済み）
    items = []
    try:
        cmd = ["git", "log", f"--since={DAYS} days ago", "-p", "--no-color", "--no-ext-diff", "--unified=0",
               "--format=@@@COMMIT %H", "--", "."] + [f":(exclude){p}" for p in SKIP_DIFF]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
        found = scan_added_lines((l.rstrip("\n") for l in proc.stdout), known)
        proc.wait()
        if proc.returncode != 0:
            items.append(f"git log が失敗（{proc.returncode}）")
        items += [f"{c} {p}: {k} {v}" for c, p, k, v in found]
    except Exception as e:
        items.append(f"確かめられず（{type(e).__name__}）")
    results.append(("新しく足された秘密の値（直近8日）", items))

    # ⑤ サイトで開けてはいけないもの ⑥ スクリプト ⑦ ドメイン
    priv, scripts, dns = [], [], []
    for base, conf in SITES.items():
        for p in conf["private"]:
            st = _status(base + p)
            if st not in (403, 404):
                priv.append(f"{base}{p} が開ける（HTTP {st}）")
        for p in conf["pages"]:
            try:
                _, b = _get(base + p, accept="text/html")
                scripts += [f"{base}{p}: {x}" for x in script_problems(b.decode("utf-8", "replace"), conf["hosts"])]
            except Exception as e:
                scripts.append(f"{base}{p}: 開けず（{type(e).__name__}）")
        host = re.match(r"https://([^/]+)", base).group(1)
        try:
            ips = set(socket.gethostbyname_ex(host)[2])
            if not ips or not ips <= PAGES_IPS:
                dns.append(f"{host} が GitHub Pages 以外を指している: {sorted(ips - PAGES_IPS)}")
        except Exception as e:
            dns.append(f"{host}: 引けず（{type(e).__name__}）")
    results.append(("サイトで個人の記録が開けないか", priv))
    results.append(("サイトが読み込むスクリプト", scripts))
    results.append(("ドメインの向き先", dns))
    return results


def send_mail(subject, body):
    user, pw = os.environ.get("GMAIL_USER"), os.environ.get("GMAIL_APP_PASSWORD")
    to = os.environ.get("ALERT_RECIPIENT") or user
    if not (user and pw):
        return False
    import smtplib
    from email.mime.text import MIMEText
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"], msg["From"], msg["To"] = subject, user, to
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as s:
        s.login(user, pw)
        s.send_message(msg)
    return True


def main():
    dry = "--dry-run" in sys.argv
    token = os.environ.get("GITHUB_TOKEN")
    known = {k[len("WATCH_KEY_"):]: v for k, v in os.environ.items() if k.startswith("WATCH_KEY_") and len(v or "") >= 8}
    since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")
    results = run_checks(token, known, since)
    bad = [(n, i) for n, i in results if i]
    print(f"週1セキュリティ点検：{len(results)}項目・要確認 {sum(len(i) for _, i in bad)}件"
          f"（いま使っている鍵 {len(known)}本と照合）")
    print(summary_for_log(results))
    if not bad:
        print("要確認なし＝メールは送らない")
        return 0
    today = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).strftime("%Y-%m-%d")
    body = [f"週1セキュリティ点検（{today}・GitHub 側・読むだけ）で要確認がありました。", ""]
    for name, items in bad:
        body.append(f"■ {name}（{len(items)}件）")
        body += [f"  - {x}" for x in items[:30]]
        body.append("")
    body += ["何も書き換えていません。直し方が分からないときは、このメールを Claude に貼ってください。",
             "（PC 側の点検は手元のタスク MarketWatch_Security_PC が別に知らせます）"]
    subject = f"🛡️ 週1セキュリティ点検：要確認 {sum(len(i) for _, i in bad)}件"
    if dry:
        print("\n--dry-run（送らない）\n" + subject + "\n" + "\n".join(body))
        return 0
    try:
        sent = send_mail(subject, "\n".join(body))
    except Exception as e:
        print(f"メール送信に失敗（{type(e).__name__}）")
        return 1
    if not sent:
        print("GMAIL_USER/GMAIL_APP_PASSWORD が無い＝知らせられない")
        return 1
    print("メールで知らせた（中身はメールだけ）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
