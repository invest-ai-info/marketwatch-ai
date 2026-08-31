# -*- coding: utf-8 -*-
"""
check_automation_health.py — 裏方の自動化（GitHub Actions / 予約エージェント routine）が
「ちゃんと走っているか」を点検する番人。health-check.yml は公開6ページの死活を見るが、
こちらはその死角＝シグナル/政治フィード/ファンダ/パニックスキャン/研究日誌等の沈黙の失敗を検知する。

5方式（誤検知を避けるため）:
  ① Actions ワークフロー … Actions API で「直近の実行が成功か＋実行が新しいか」を見る
     （commit-on-change なジョブでもファイル鮮度に惑わされない）
  ② クラウド routine     … 毎回再生成する出力ファイルの最終コミット時刻で鮮度を見る
  ③ 公開記事カバレッジ   … guide-signal-lab-* / guide-news-* が guides.html にカードとして
     載っているかをリポジトリ状態で照合（local-drift 巻き戻し事故の早期検知＝B「カバレッジ番人」）
  ④ 固定ゲートの不変条件 … ゲート/リンターを routine が書き換えて通過する自己承認を検知
  ⑤ topicキューの残量    … autodraft の未公開 topic 本数を数える。①②は「走ったか」しか見ないので、
     キューが尽きて仕様どおり静かに停止する枯渇（2026-07-20〜24 の実例）を捕まえられない

判定: critical/warn が1件でも異常なら exit 1（workflow が Issue を立てる）。info のみ/全正常なら exit 0。
実行: GitHub Actions（automation-health.yml）／ローカルでも可。
"""
import os
import re
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
    # ⚠️ ここの max_h は「cron が来なかった」を見る②専用の閾値であって、故障検知の閾値ではない。
    #    judge_runs の①（cancelled を除いた直近の実質結果が failure なら即異常）が本物の故障を
    #    経過時間と無関係に拾うので、**max_h を上げても故障検知は一切弱まらない**。
    #    ⇒ max_h は「正常運用で観測されうる最大の空き」より必ず大きく取ること。
    #
    # 2026-08-30 再較正: 毎時系4本が実測と乖離し、automation-health が連日 exit 1 して
    #   issue #4 を鳴らし続けていた（8/27・8/28・8/29×4・8/30。中身はすべて②の誤検知で、
    #   当該ワークフローは直近100 run すべて success）。鳴りっぱなしは本物の異常
    #   （⑩ JQUANTS_API_KEY 未登録・⑪ force-push）を埋もれさせるので実測で置き直した。
    #   直近100回の成功実行の間隔（2026-08-22〜08-30 実測）:
    #     technical-alerts     median 0.5h / p90 4.3h / MAX 12.6h  （旧閾値 6h）
    #     technical-alerts-1h  median 1.0h /            MAX 13.3h  （旧閾値 5h）
    #     political-alerts     median 0.9h /            MAX 16.9h  （旧閾値 4h）
    #     news-ticker          median 1.0h / p90 2.8h / MAX 10.9h  （旧閾値 5h）
    #   閾値は jp-rankings と同じ流儀＝**実測MAX + 5h**（＝観測済みの最悪ケースに余裕を足す）。
    #   ⚠️ 元に戻さないこと。旧値は「1時間ごとの cron が来る」前提だが、GitHub は日常的に
    #      10〜17時間まとめて実行を作らない（skipped でも cancelled でもなく run 自体が無い）。
    ("テクニカルアラート(4H)",  "technical-alerts.yml",    18, "critical"),
    ("1Hシグナル収集",          "technical-alerts-1h.yml", 18, "warn"),
    ("政治発言フィード",        "political-alerts.yml",    22, "critical"),
    ("市況ニュース生成",        "update-market-news.yml",  15, "warn"),
    ("最新ニュース・ティッカー", "news-ticker.yml",         16, "warn"),
    ("パニック反発スキャン",    "panic-scan.yml",          27, "warn"),
    # 🆕 2026-08-29 追加。hot-assets 最上段の日本株ランキング（と信用残）を作る唯一のジョブなのに
    #    監視対象外だった＝止まってもライブが古いまま誰も気づけない口。閾値は実測で置いた:
    #    直近30runの日跨ぎ間隔は 24〜25h（1日2回・cronの滑りは30〜45分）。8/27 は1日まるごと
    #    スキップされて 33.5h あいた＝**その形を捕まえる**ために 30h（正常の最大25hに5hの余裕）。
    ("日本株ランキング",        "jp-rankings.yml",         30, "warn"),
    # 🆕 低頻度ジョブ（2026-07 追加）。7/1 に monthly-report が取りこぼされ6月レポート未生成の事故で、
    #    週次/月次が監視対象外＝盲点と判明。正常運用で誤検知しないよう余裕を持たせた閾値。
    #    max_h は「1回まるごとスキップされたら検知」水準：週次=10日 / 月次=35日。
    # 🆕 2026-08-30 追加。**監視の穴だった**＝週次振り返り/週次投資戦略/週次ゾーンメールの3本すべての
    #    土台になる水準計算なのに、ここだけリストに無かった。しかも下流の weekly-strategy.yml は
    #    中身が空でも success で終わる（verified=false・scenarios=[] を書いて正常終了する）ので、
    #    **どこからも異常に見えない**。issue #3（2026-06-21）が2か月開いたままだったのはこれが理由で、
    #    2026-08-30 に同じ形で再発しているのを実測した（cron 17:00/18:00 JST の2本立てなのに
    #    GitHub が両方とも実行を作らず、18:30 の routine が levels stale 168h で verified=false）。
    #    実測（直近28回・2026-05-30〜08-30）: 週次の間隔は中央値 168.0h / 最大 170.3h
    #    ＝cron遅延の寄与は最大 +2.3h しかない。192h(8日) なら余裕 21.7h で、日曜が丸ごと飛んだ場合に
    #    **火曜朝の定期チェック(09:30)で検知**できる（24*10=240h だと木曜まで気づけない）。
    #    ⚠️ 日曜当日に気づきたいなら、この閾値ではなく automation-health 自体を日曜夜にも回す必要がある。
    ("週次レベル計算",          "weekly-levels.yml",       24 * 8,  "warn"),
    ("週次振り返り",            "weekly-review.yml",       24 * 10, "warn"),
    ("週次投資戦略",            "weekly-strategy.yml",     24 * 10, "warn"),
    # 🆕 2026-08-16 追加。8/2・8/9・8/16 と3週連続で失敗していたのに、監視対象外だったので
    #    誰も気づけなかった（原因＝Gmailアプリパスワードの失効。⑨で毎朝直接確かめる）。
    ("週次ゾーンメール",        "weekly-zone-email.yml",   24 * 10, "warn"),
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


def judge_runs(runs, max_h, now):
    """純関数（テスト対象）＝実行履歴から健全性を判定する。

    ⚠️ 2026-08-08 改定: **cancelled を failure と同一視しない**。
       旧実装は直近1件だけを見て `conclusion != "success"` なら異常としていたが、
       `cancelled` の大半は **concurrency による意図的な取り下げ**（`signal-workflows` 群の
       3重cron冗長化や `cancel-in-progress: true` の後勝ち）であって、故障ではない。
       実測（2026-08-06）: 失敗扱いの非Pages run 11件のうち **10件が job=cancelled・失敗stepゼロ**、
       残り1件も GitHub 側の "Service Unavailable"（アクション取得の一時障害）だった。
       この設計のまま cancelled が直近に来た朝があれば、番人は**故障していないのに Issue を立てる**。

       新方式: ①cancelled は判定から除外して「直近の実質的な結果」を見る
               ②ただし **max_h 以内に success が1件も無ければ異常**（＝全部 cancelled で
                 詰まっている状態や、本当に走っていない状態は取り逃さない）
       戻り値: (ok, note)
    """
    if not runs:
        return False, "実行履歴なし"

    # 走行中（未完了）が最新なら OK 扱い（旧実装と同じ）
    newest = runs[0]
    if newest.get("status") != "completed":
        return True, f"実行中（{newest.get('status')}）"

    completed = [r for r in runs if r.get("status") == "completed"]
    succ = [r for r in completed if r.get("conclusion") == "success"]
    cancelled_recent = sum(1 for r in completed
                           if r.get("conclusion") == "cancelled" and age_hours(r["created_at"], now) <= max_h)

    def agetxt(r):
        a = age_hours(r["created_at"], now)
        return f"{a:.1f}h前" if a < 48 else f"{a/24:.1f}日前"

    # ① cancelled を除いた「実質的な直近の結果」が失敗なら異常
    substantive = [r for r in completed if r.get("conclusion") != "cancelled"]
    if substantive and substantive[0].get("conclusion") != "success":
        return False, f"直近実行が失敗（{substantive[0].get('conclusion')}・{agetxt(substantive[0])}）"

    # ② max_h 以内に success が1件も無ければ異常（全部 cancelled で詰まる形もここで捕まる）
    if not succ:
        return False, f"取得範囲内に成功実行なし（cancelled {cancelled_recent}件）"
    a = age_hours(succ[0]["created_at"], now)
    if a > max_h:
        extra = f"・直近{max_h}hに cancelled {cancelled_recent}件" if cancelled_recent else ""
        return False, f"{max_h}h以上成功していない（最後の成功 {agetxt(succ[0])}{extra}）"

    note = f"成功 {agetxt(succ[0])}"
    if cancelled_recent:
        # 故障ではないが、多発は輻輳/設計の兆候なので可視化はする（Issueにはしない）
        note += f"（別途 cancelled {cancelled_recent}件＝concurrencyによる取り下げ・故障ではない）"
    return True, note


def check_workflow(owner, repo, token, wf, max_h, now):
    """直近の実行群から健全性を判定（判定則は judge_runs＝単一の真実）。"""
    data = api(f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/{wf}/runs?per_page=20", token)
    return judge_runs(data.get("workflow_runs", []), max_h, now)


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


# ⑤ autodraft topicキューの残量。①②は「routine が走ったか」しか見ないので、キューが尽きて
#    手順書どおり「該当なし＝生成しない」で静かに止まる枯渇を検知できない（2026-07-20〜24 の実例＝
#    autopublish が5日連続スキップしても誰も気づかなかった）。未公開 topic の本数＝残り日数なので、
#    尽きる前に補充の締切を通知する。
QUEUE_GUIDE_PATH = "drafts/AUTODRAFT_GUIDE.md"
QUEUE_MIN_REMAIN = 5  # 未公開 topic がこれ未満なら warn（1日1本なので約5日前に通知）

# 🚨 2026-08-31 追加: 見ていたのは autodraft レーンだけだった。
#
# 同日に測ったら **投資格言は5日連続・投資詐欺は7日連続**、ルーティン自身が台帳に
# 「🚩キュー枯渇・補充依頼」を書き続けていたのに、誰も気づいていなかった。
# ⑤は「静かな停止を捕まえる」ために作った番人なのに、**見ている口が1つしかなかった**
# ＝新しい自動公開レーン（proverb 2026-08-06〜 / scam 2026-08-13〜）が増えたときに
# ここへ登録する手順が無かった。**レーンを増やしたら必ずこの表に足すこと。**
#
# ⚠️ 台帳（LEDGER）に載っている key は残量に数えない。ルーティン自身が
# 「LEDGER と guides.html のどちらにも未登録の最初の1件」を選ぶので、
# **台帳に載った時点でその回は選ばれない**（人間判断でクローズした格言、
# エスカレ中で公開できない手口が該当）。数に入れると、動かせない在庫が床を支えてしまう。
QUEUE_LANES = [
    # (レーン名, 手順書, guide- の後ろに付く接頭辞, 台帳, 床)
    ("autodraft（心理＆リスク管理）", QUEUE_GUIDE_PATH, "", None, QUEUE_MIN_REMAIN),
    ("proverb（投資格言）", "drafts/PROVERB_GUIDE.md", "proverb-",
     "drafts/proverb/PROVERB_LEDGER.md", QUEUE_MIN_REMAIN),
    ("scam（投資詐欺）", "drafts/SCAM_GUIDE.md", "scam-",
     "drafts/scam/SCAM_LEDGER.md", QUEUE_MIN_REMAIN),
    # 2026-08-31 新設。格言シリーズ（44本で汲み尽くし）の後継として日次枠を引き継ぐ
    ("tse（東証のしくみ）", "drafts/TSE_GUIDE.md", "tse-",
     "drafts/tse/TSE_LEDGER.md", QUEUE_MIN_REMAIN),
]


# 🆕 2026-08-31: キューを持たないレーンは、上の QUEUE_LANES では見張れない。
#
# 「数字で見る、話題の企業」（週次）は題材を jp-rankings.json から機械的に選ぶ設計で、
# **キューが無い＝枯渇しない**のが売り。その代わり「止まったこと」を残量では検知できないので、
# **台帳の最終更新の鮮度**で見る。
# 🚨 レーンを足したら必ず何かで見張ること——2026-08-31 に格言5日・詐欺7日の枯渇を
# 誰も知らないまま放置した原因は「番人に登録する手順が無かった」ことだった。
#
# ⚠️ `since` より前は鳴らさない。ルーティンが初回に走る前から赤いと、番人の信用が落ちる。
LEDGER_WATCH = [
    # (レーン名, 台帳, 何日で鳴らすか, いつから見張るか)
    ("company（数字で見る企業・週次）", "drafts/company/COMPANY_LEDGER.md", 10, dt.date(2026, 9, 7)),
]


def check_ledger_freshness(owner, repo, token, path, max_days, since, today):
    """台帳の最終コミットからの経過日数を返す。戻り値: (状態, 説明)。

    状態は "ok" / "stale" / "missing" / "waiting"（since 前で判定しない）。
    """
    if today < since:
        return "waiting", f"{since.isoformat()} から見張ります"
    url = (f"https://api.github.com/repos/{owner}/{repo}/commits"
           f"?path={path}&per_page=1")
    commits = json.loads(api_raw(url, token))
    if not commits:
        return "missing", f"{path} がまだありません（初回の実行が済んでいない可能性）"
    stamp = commits[0]["commit"]["committer"]["date"][:10]
    last = dt.date(int(stamp[:4]), int(stamp[5:7]), int(stamp[8:10]))
    age = (today - last).days
    if age > max_days:
        return "stale", f"{path} の最終更新が {stamp}（{age}日前・閾値{max_days}日）"
    return "ok", f"{path} の最終更新は {stamp}（{age}日前）"


def check_topic_queue(owner, repo, token, path=QUEUE_GUIDE_PATH, prefix="", ledger=None):
    """手順書のキュー表から key を抽出し、guides.html に guide-<prefix><key>.html の
    カードが無いもの＝未公開の残りを数える。
    ローカルの陳腐化に惑わされないよう、どれも GitHub 側の最新を読む（③と同方針）。
    戻り値: (キュー総数, いま着手できるkeyのリスト, 台帳に載っていて数えないkeyのリスト)。"""
    md = api_raw(f"https://api.github.com/repos/{owner}/{repo}/contents/{path}", token)
    # 表の行「| 12 | 基礎知識 | `bonds-interest-rates` | …」から key だけを取る。
    # ⚠️ proverb / scam の表は key をバッククォートで囲っていないので任意にする
    keys = re.findall(r"^\|\s*\d+\s*\|[^|]*\|\s*`?([a-z0-9-]+)`?\s*\|", md, re.M)
    guides = api_raw(f"https://api.github.com/repos/{owner}/{repo}/contents/guides.html", token)
    unpublished = [k for k in keys if f'href="guide-{prefix}{k}.html"' not in guides]

    held = []
    if ledger and unpublished:
        try:
            text = api_raw(f"https://api.github.com/repos/{owner}/{repo}/contents/{ledger}", token)
            held = [k for k in unpublished if k in text]
        except Exception:
            held = []          # 台帳が読めないだけで番人を止めない（数は多めに出る）
    remaining = [k for k in unpublished if k not in held]
    return len(keys), remaining, held


# ⑥ 「宣言した仮説」がライブトラッカーに実在するか（＝事前登録の静かな失敗の検知）。
#    2026-07-27 の実バグが動機: Q35 の新規3件を `signal_lab_tracker.SEED` に足したが、SEED は
#    **トラッカー未作成時にしか使われない**（load_tracker は既存 JSON を返す）ため一度も登録されず、
#    同日のリモート tracker 51件に3件とも不在だった。SESSION_HANDOFF と DOCTRINE には
#    「7/27から観測開始」と書かれていたのに**実体が無かった**＝台帳が嘘をつく最悪の壊れ方。
#    ①②⑤は「routine が走ったか」しか見ず、③は公開記事、④はゲート改変しか見ないので誰も捕まえられない。
#    ここでは**宣言（コード側の SEED / register 定数）と実体（signal-lab-tracker.json）を突き合わせる**。
#    ⚠️ 重複スキップは正常系: apply_holdout_bootstrap は id か filter が既存と重なる宣言を意図的に
#    飛ばす（例 metal_all_1d は auto_group-metal と filter 同一）。よって**id と filter の両方が
#    不在のときだけ**「登録漏れ」と判定する＝恒久的な誤検知を出さない。
TRACKER_JSON_PATH = "signal-lab-tracker.json"


def declared_hypotheses(T):
    """`signal_lab_tracker` が宣言している仮説を全部集める（純関数・テスト対象）。

    ⚠️ 2026-08-11 修正: 旧実装は定数名を**ハードコードしたタプル**で列挙しており、
       同日追加した `REGISTER_2026_08_11`（Q24 news_zero_edge）が**検査から漏れていた**
       ＝「登録漏れを検知する番人」自身が新しい登録漏れを見逃す構造だった。
       日付つき register 定数は今後も増えるので、**名前の形で動的に拾う**。
       （§⑥の趣旨は「宣言と実体の突合」＝宣言の集め方が手作業だと趣旨が崩れる）
    """
    out = list(T.SEED)
    for name in sorted(dir(T)):
        if not re.fullmatch(r"[A-Z][A-Z_]*_\d{4}_\d{2}_\d{2}", name):
            continue
        v = getattr(T, name, None)
        if isinstance(v, dict):
            out += v.get("register", [])
    return out


def check_tracker_registration(owner, repo, token):
    """コードで宣言した仮説が GitHub 側 tracker に実在するか。戻り値: (宣言総数, 欠落リスト)。"""
    import signal_lab_tracker as T

    declared = declared_hypotheses(T)

    live = json.loads(api_raw(
        f"https://api.github.com/repos/{owner}/{repo}/contents/{TRACKER_JSON_PATH}", token))
    live_ids = {h.get("id") for h in live.get("hypotheses", [])}
    live_filters = {T._filter_key(h["filter"]) for h in live.get("hypotheses", []) if h.get("filter")}

    missing = [s["id"] for s in declared
               if s["id"] not in live_ids and T._filter_key(s["filter"]) not in live_filters]
    return len(declared), sorted(set(missing))


# ⑦ ティッカー用フィードのソース単位の停止検知（2026-08-06 追加）。
#    ①は news-ticker.yml の実行成否しか見ないため、workflow が緑のまま特定フィードだけが
#    死ぬ形（URL変更・RSS廃止＝8/1 Bloomberg の壊れ方）を捕まえられない。
#    build_news_ticker.py が JSON に書く feed_health（フィード別の最終観測時刻）と、
#    FEEDS 側の閾値 stale_days を突き合わせる。閾値の単一の真実は FEEDS（ここに複製しない）。
#    トピック検索フィードは stale_days=None＝監視対象外（「静か」が正常＝誤検知ゼロ方針）。
TICKER_JSON_PATH = "news-ticker.json"


# ⑧ エスカレの滞留検知（2026-08-11 追加）。
#    動機＝実際に起きた見落とし: オーナーが「今日シグナル研究日誌が更新されていない」と**目視で**気づいた。
#    実体は routine 正常（06:29 下書き生成）で、公開ゲートの最終段（独立Opus）が 🔴否 →
#    07:02 に `drafts/REVIEW.md` へ 🚩 エスカレしていた。さらに #065 が 8/09 から**2日間放置**
#    （公開番号は #001〜#066 で **#065 だけ欠番**）。
#    ①②は「走ったか」、③は公開記事の掲載、④はゲート改変、⑤はキュー枯渇しか見ないので、
#    **「走ったが人間待ちで止まっている」形を誰も捕まえられなかった**。ここで塞ぐ。
#    ⚠️ 🚩 が出ること自体は正常（ゲートが働いた証拠）。異常なのは**放置され続けること**なので
#       閾値は日数で持つ＝当日中のエスカレでは鳴らさない（鳴りっぱなしにしない）。
REVIEW_PATH = "drafts/REVIEW.md"
# 🆕 2026-08-11 夜: 2日 → **1日**（オーナー決定）。理由＝signal-lab は放置すると救済コストが上がる。
#    基準時刻凍結（`signal_lab_verify.py --asof` / claims.json の "asof"）を入れたので
#    「日が変わると直せない」問題自体は解消したが、**asof を持たない旧claimsは依然として救済不能**で、
#    かつ 09:30 の本チェックは 06:10 生成の**翌朝**に鳴る＝1日にしないと最短でも2日放置になる。
ESCALATION_STALE_DAYS = 1
# 見出しの形: `## 2026-08-11 | 🚩 独立Opus否・FWDデータ修正要 | signal-lab-067 | signal-lab-daily`
RE_REVIEW_HEAD = re.compile(r"^##\s*(\d{4}-\d{2}-\d{2})\s*\|([^|\n]*)\|\s*([^|\n]+?)\s*\|", re.M)


# 見出し3列目（対象）の表記ゆれを実体スラッグへ寄せる。
# 2026-08-18 実測: signal-lab レーンは回によって `signal-lab-067`（スラッグ）と
# `signal-lab-daily #071`（ルーティン名＋番号）の2通りを書く。後者は
# `guide-signal-lab-daily #071.html` を探しに行って必ず不在＝**永久に滞留と誤検知**していた
# （#071 はライブ200＝実際には解決済みだったのに3日間鳴り続けた）。
RE_LAB_TARGET = re.compile(r"signal-lab\D*(\d{2,4})")
# 明示の解決マーク（書き手が見出しに残す）。実体判定が効かない回の保険。
RESOLVED_MARKS = ("[解消済み]", "[解決済み]", "解消済み", "解決済み")
# ルーティン名と成果物ファイル名が食い違う対象。**表示名（ルーティン名）は変えず、実体照合だけ別名で行う**。
# 2026-08-19 実測: `book-watch-weekly` の成果物は `guide-new-books.html`（単一ソース＝drafts/BOOKWATCH_GUIDE.md）。
# 素のままだと `guide-book-watch-weekly.html` を探しに行って必ず不在＝**公開済みでも永久に滞留と誤検知**する
# （8/18 に新刊2冊を公開してライブ200なのに、8/19 も「4日放置」と鳴り続けていた）。
# ⚠️ ここは表記ゆれ（normalize_target）ではなく**別物の対応表**。ルーティン名は識別子として保つ。
TARGET_ARTIFACT = {"book-watch-weekly": "new-books"}


def normalize_target(tgt):
    """`signal-lab-daily #071` → `signal-lab-071`。それ以外は素通し。"""
    m = RE_LAB_TARGET.search(tgt or "")
    return f"signal-lab-{m.group(1)}" if m else (tgt or "").strip()


def eval_escalations(review_md, published, now, stale_days=ESCALATION_STALE_DAYS):
    """純関数（テスト対象）。戻り値: (滞留 [(target, 日付, 経過日)], 🚩総数, 未解決総数)。

    解決の判定は**実体で**行う（宣言でなく成果物を見る＝③と同じ方針）:
      ① `guide-<target>.html`（TARGET_ARTIFACT に別名があればそれ）が公開済みなら解決
      ② 同じ target について、より新しい見出しが 🚩 なしで「公開」と言っていれば解決
    どちらも無ければ未解決。未解決のうち stale_days 以上経過したものだけを滞留として返す。
    """
    heads = [(d, kind, normalize_target(tgt)) for d, kind, tgt in RE_REVIEW_HEAD.findall(review_md)]
    # target ごとの最新の「公開」見出し日
    published_head = {}
    for d, kind, tgt in heads:
        if "🚩" not in kind and "公開" in kind:
            published_head[tgt] = max(published_head.get(tgt, ""), d)
    flags = [(d, tgt, kind) for d, kind, tgt in heads if "🚩" in kind]
    stale, unresolved = [], 0
    seen = set()
    for d, tgt, kind in flags:
        if tgt in seen:          # 同じ対象の複数エスカレは最新1件で代表させる
            continue
        seen.add(tgt)
        artifact = TARGET_ARTIFACT.get(tgt, tgt)
        if f"guide-{artifact}.html" in published or published_head.get(tgt, "") >= d:
            continue
        if any(m in kind for m in RESOLVED_MARKS):   # 見出しに明示の解決マーク
            continue
        unresolved += 1
        try:
            age = (now.date() - dt.date.fromisoformat(d)).days
        except ValueError:
            continue
        if age >= stale_days:
            stale.append((tgt, d, age))
    stale.sort(key=lambda x: -x[2])
    return stale, len(flags), unresolved


def check_escalation_backlog(owner, repo, token, now):
    """戻り値: (滞留リスト, 🚩総数, 未解決総数)。実体＝リポジトリ直下の公開HTML一覧で判定。"""
    md = api_raw(f"https://api.github.com/repos/{owner}/{repo}/contents/{REVIEW_PATH}", token)
    published = set(list_repo_root_files(owner, repo, token))
    return eval_escalations(md, published, now)


def eval_ticker_feed_health(feeds, feed_health, now):
    """純関数（テスト対象）。戻り値: (停止 [(name, 経過日, 閾値日)], 観測開始前 [name], 監視対象数)。"""
    stale, pending, watched = [], [], 0
    for feed in feeds:
        days = feed.get("stale_days")
        if not days:
            continue
        watched += 1
        rec = feed_health.get(feed["name"]) or {}
        last = rec.get("last") or rec.get("first")
        if not last:
            pending.append(feed["name"])
            continue
        a = age_hours(last, now) / 24.0
        if a > days:
            stale.append((feed["name"], a, days))
    return stale, pending, watched


def check_smtp_auth():
    """Gmail アプリパスワードが生きているかを login だけで確かめる（メールは送らない）。

    戻り値 (ok, note): ok=True 正常 / False 認証失効 / None 判定不能（未設定・一時障害）。

    なぜ要るか＝2026-08-16 に実際に踏んだ穴。アプリパスワードが失効すると
    **メール送信の全レーンが同時に死ぬ**が、`generate_technical_alerts.py` /
    `fetch_political_news.py` / `panic_bounce_scan.py` / `monthly_calendar_reminder.py` は
    送信失敗を `except Exception` で握り潰して exit 0 のまま緑になる
    （シグナル記録を送信成否から切り離すための正しい設計なので、そちらは変えない）。
    唯一 `weekly-zone-email.yml` だけが赤くなるが**週1回＝最大7日気づけない**。
    実際 8/2 から3週間、誰も気づかなかった。ここで毎朝 login を試して24h以内に捕まえる。
    ⚠️ 送信はしない（毎朝メールが増えると読まれなくなる＝警報の価値が下がる）。
    """
    user = os.environ.get("GMAIL_USER")
    pw = os.environ.get("GMAIL_APP_PASSWORD")
    if not (user and pw):
        # ローカル実行では鍵を持たないのが正常。無いデータで判定しない。
        return None, "GMAIL_USER/GMAIL_APP_PASSWORD が未設定＝判定しない（ローカル実行では正常）"
    import smtplib
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as server:
            server.login(user, pw)
        return True, "アプリパスワードは有効（login のみ・送信なし）"
    except smtplib.SMTPAuthenticationError as e:
        detail = e.smtp_error.decode("utf-8", "replace") if isinstance(e.smtp_error, bytes) else str(e.smtp_error)
        return False, (f"Gmail が認証を拒否（{e.smtp_code} {detail[:120]}）"
                       f"＝アプリパスワードの失効/取り消しが濃厚。"
                       f"Google アカウント → セキュリティ → 2段階認証 → アプリパスワード を再発行し、"
                       f"リポジトリ Secrets の GMAIL_APP_PASSWORD を更新する（16桁・空白なし）。"
                       f"⚠️ この間、テクニカル/政治/パニックの各メールも同時に届いていない"
                       f"（それらは送信失敗を握り潰すため workflow は緑のまま）")
    except Exception as e:
        # 一時的なネットワーク/SMTP障害で毎朝 Issue を立てない（③〜⑧と同じ方針）
        return None, f"SMTP 到達を確認できず（一時障害の可能性・判定しない）: {type(e).__name__}: {str(e)[:80]}"


# ⑬ 経済指標カレンダーの先詰まり。①②は「ワークフローが走ったか」しか見ないので、
#    「走ったが中身が増えていない」を取り逃す。2026-08-30 に実際そうなっていた:
#    economic-events.json の指標が 2026-07-31 を最後に**2か月ゼロ**だったのに、
#    monthly-calendar-reminder.yml は「メールを送る」だけで success を返し続けていた。
#    実害はシグナル側で、8月は指標発表24時間前に出た113本のシグナルに
#    「🚫 重要指標まで X h」が付かなかった（うち12本は発表0.6時間前）。
#    いまは sync_economic_events.py が ECONOMIC_EVENTS_2026 から自動生成するので
#    人手の転記は無いが、**その元表が尽きれば同じ形で静かに空になる**
#    （2027年ぶんは未整備＝年が変われば実際に起きる）。だからデータ側で見る。
FORWARD_DAYS = 21      # 先を見る窓。月次補充(25日)＋cron滑りを跨いでも余裕がある長さ
# 判定は「枯れたか」＝0件かどうかで見る。2件等の下限は根拠が無く、
# 9月下旬のように元表が薄い時期を誤検知した（2026-08-30 の全日スイープで実測）。
# 健全なカレンダーなら21日窓に必ず雇用統計かCPIが入るので、0件は本当に異常。
FORWARD_MIN = 1


def judge_calendar_runway(events, now, forward_days=FORWARD_DAYS, min_count=FORWARD_MIN):
    """純関数（テスト対象）＝今後 forward_days 日に指標イベントが何件あるか。

    市場休場（category=market_holiday）は数えない。あれは
    generate_market_holidays.py が2027年まで自動補充しており、
    **これがあるせいで「イベントはある」ように見えてしまう**のが今回の見落としの正体。
    戻り値: (ok, 件数, 直近イベント名 or None)
    """
    horizon = now + dt.timedelta(days=forward_days)
    upcoming = []
    for e in events:
        if e.get("category") == "market_holiday":
            continue
        try:
            t = dt.datetime.fromisoformat(e["datetime"])
        except Exception:
            continue
        if now <= t <= horizon:
            upcoming.append((t, e.get("name", "")))
    upcoming.sort()
    nearest = upcoming[0][1] if upcoming else None
    return (len(upcoming) >= min_count, len(upcoming), nearest)


# ⑫ 日本株ランキングの鮮度。①は「jp-rankings.yml が走ったか」しか見ないが、走っても
# 上流(Yahoo)がまだ当日の日足を返していない時刻に走ると、成功したまま前営業日の順位が残る
# （2026-08-29 実測: cron が 17時台→04:34 JST へずれた回が asof=2026-08-27 で完走）。
# 祝日カレンダーを持たずに判定するため、**上流自身の最終営業日**と突き合わせる。
JP_PROBE_TICKER = "7203.T"          # 流動性の高い代表銘柄（上流の営業日を知るためだけに使う）
JP_SETTLE_HOUR_JST = 15, 30         # 東京クローズ15:00＋余裕。これ以前の当日バーは未確定扱い


def latest_settled_trading_date(dates, now):
    """上流の日付列から「確定済みの最終営業日」を返す（純関数）。

    場中は当日の未確定バーが最後に来るので1本落とす。番人は 09:30 JST に走るため、
    この処理が無いと毎朝「当日 vs 前営業日」で必ず誤検知する。
    """
    if not dates:
        return None
    jst = now.astimezone(dt.timezone(dt.timedelta(hours=9)))
    h, m = JP_SETTLE_HOUR_JST
    if dates[-1] == jst.date().isoformat() and (jst.hour, jst.minute) < (h, m):
        return dates[-2] if len(dates) >= 2 else None
    return dates[-1]


def fetch_jp_trading_dates(ticker=JP_PROBE_TICKER):
    """Yahoo chart から直近1か月の日足の日付列（JST・昇順）を取る。キー不要。"""
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
           f"?range=1mo&interval=1d")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.load(r)["chart"]["result"][0]
    q = d["indicators"]["quote"][0]
    jstz = dt.timezone(dt.timedelta(hours=9))
    return [dt.datetime.fromtimestamp(t, jstz).date().isoformat()
            for t, c in zip(d.get("timestamp", []), q.get("close", [])) if c is not None]


FORCE_PUSH_WINDOW_H = 30   # 09:30 JST の日次点検が1回飛んでも取りこぼさない幅


def eval_force_push(events, now, window_h=FORCE_PUSH_WINDOW_H):
    """純関数（テスト対象）＝ref アクティビティから main の巻き戻しを拾う。

    なぜ要るか＝2026-08-29 に実際に踏んだ穴。8/25 時点の古い作業コピーを持った
    クラウドのルーティンが main へ force-push し、**299コミット（3.5日分）が消えた**
    （6コアHTMLの再生成・news-ticker・公開記事・signals-log 追記がまとめて巻き戻り）。
    厄介なのは、消えたあとも全ワークフローが緑のままだったこと：
      - 各ジョブは checkout → 生成 → push で完結するので、巻き戻った土台の上でも成功する
      - health-check.yml の「最終更新が今日か」も、巻き戻り直後の再生成で**今日の日付に戻る**
        ＝日付だけ見ていると正常に見える（実際 8/29 12:47 の再生成で緑に戻った）
    つまり既存の番人はどれも履歴の巻き戻りを見ていない。ここで ref の force_push を直接見る。
    """
    hits = []
    for e in events:
        if e.get("activity_type") != "force_push":
            continue
        age = age_hours(e["timestamp"], now)
        if age <= window_h:
            hits.append({
                "at": e["timestamp"],
                "age_h": round(age, 1),
                "actor": (e.get("actor") or {}).get("login", "?"),
                "before": (e.get("before") or "")[:8],
                "after": (e.get("after") or "")[:8],
            })
    return hits


def check_force_push(owner, repo, token, now):
    ev = api(f"https://api.github.com/repos/{owner}/{repo}/activity"
             f"?ref=refs/heads/main&activity_type=force_push&per_page=20", token)
    return eval_force_push(ev, now)


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
    body.append("### ⑤ 自動公開レーンのキュー残量（枯渇＝静かな停止）")
    for lane, path, prefix, ledger, floor in QUEUE_LANES:
        try:
            total, remaining, held = check_topic_queue(owner, repo, token, path, prefix, ledger)
            hold = f"／台帳に載っていて数えない {len(held)}件（{', '.join(held)}）" if held else ""
            if not total:
                body.append(f"- 🚨 ⚪ {lane}: キューを解析できない（{path} の表形式を確認）")
            elif len(remaining) < floor:
                nokori = ", ".join(remaining) if remaining else "なし＝レーン停止中"
                body.append(f"- 🚨 🟡 {lane}: いま着手できる残りが {len(remaining)}/{total} 件"
                            f"（閾値 {floor}）{hold}＝キュー補充が必要。"
                            f"{path} の表に行を追加する。残り: {nokori}")
                bad.append((f"{lane} キュー枯渇", "warn"))
            else:
                body.append(f"- ✅ 🟢 {lane}: いま着手できる残り {len(remaining)}/{total} 件"
                            f"（閾値 {floor} 以上）{hold}")
        except Exception as e:
            # ③④と同じ方針: API一時エラー自体では Issue を立てない（記録のみ）
            body.append(f"- 🚨 ⚪ {lane}: キュー残量の確認失敗: {e}")
    for lane, path, max_days, since in LEDGER_WATCH:
        try:
            state, detail = check_ledger_freshness(
                owner, repo, token, path, max_days, since, dt.date.today())
            if state == "ok":
                body.append(f"- ✅ 🟢 {lane}: {detail}")
            elif state == "waiting":
                body.append(f"- ✅ ⚪ {lane}: {detail}")
            else:
                body.append(f"- 🚨 🟡 {lane}: {detail}＝レーンが止まっている可能性")
                bad.append((f"{lane} 停止の疑い", "warn"))
        except Exception as e:
            body.append(f"- 🚨 ⚪ {lane}: 台帳の鮮度確認に失敗: {e}")

    body.append("")
    body.append("### ⑥ 事前登録した仮説がトラッカーに実在するか（登録漏れ＝台帳が嘘をつく壊れ方）")
    try:
        total, missing = check_tracker_registration(owner, repo, token)
        if missing:
            body.append(f"- 🚨 🟡 宣言 {total} 件のうち **{len(missing)} 件が tracker に不在**"
                        f"（id も filter も無い＝重複スキップではない登録漏れ）: " + ", ".join(missing)
                        + "。`signal_lab_tracker.py` の SEED に足しただけになっていないか確認する"
                          "（SEEDはトラッカー未作成時にしか使われない＝2026-07-27 の実バグ）")
            bad.append(("トラッカー登録漏れ", "warn"))
        else:
            body.append(f"- ✅ 🟢 宣言 {total} 件すべてが tracker に実在（または filter 重複で正常スキップ）")
    except Exception as e:
        # ③④⑤と同じ方針: API/import の一時エラー自体では Issue を立てない（記録のみ）
        body.append(f"- 🚨 ⚪ トラッカー登録の突合失敗: {e}")

    body.append("")
    body.append("### ⑦ ティッカー用フィードの停止検知（①はworkflow成否しか見ない死角＝ソース単位で見る）")
    try:
        import build_news_ticker as B
        data = json.loads(api_raw(
            f"https://api.github.com/repos/{owner}/{repo}/contents/{TICKER_JSON_PATH}", token))
        fh = data.get("feed_health")
        if fh is None:
            body.append("- ⚪ feed_health が未生成（旧版JSON＝次回の毎時実行から記録開始）")
        else:
            stale, pending, watched = eval_ticker_feed_health(B.FEEDS, fh, now)
            if stale:
                det = ", ".join(f"{n}（{a:.0f}日無音/閾値{d}日）" for n, a, d in stale)
                body.append(f"- 🚨 🟡 記事が途絶えたフィード {len(stale)}/{watched} 本: {det}。"
                            f"URL変更/RSS廃止を疑い、実測プローブ→FEEDS を削除/差し替え"
                            f"（8/1 Bloomberg・8/6 プローブと同じ手順）")
                bad.append(("tickerフィード停止", "warn"))
            else:
                note = f"（観測開始前 {len(pending)} 本）" if pending else ""
                body.append(f"- ✅ 🟢 監視対象 {watched} 本すべて閾値内{note}")
    except Exception as e:
        # ③〜⑥と同じ方針: API/import の一時エラー自体では Issue を立てない（記録のみ）
        body.append(f"- 🚨 ⚪ フィード鮮度の確認失敗: {e}")

    body.append("")
    body.append("### ⑧ エスカレの滞留（走ったが人間待ちで止まっている＝①②③⑤の死角）")
    try:
        stale, flags, unresolved = check_escalation_backlog(owner, repo, token, now)
        if stale:
            det = ", ".join(f"{t}（{d}・{a}日放置）" for t, d, a in stale)
            body.append(f"- 🚨 🟡 未対応の 🚩 が {len(stale)} 件（{ESCALATION_STALE_DAYS}日以上）: {det}。"
                        f"{REVIEW_PATH} の該当節に修正指示が具体値まで書かれている。"
                        f"⚠️ signal-lab を後日直すときは **必ず基準時刻を凍結する**："
                        f"`python signal_lab_verify.py <draft> <claims> --asof <生成時刻ISO8601>`"
                        f"（claims.json に \"asof\" があればそちらが優先）。"
                        f"凍結しないとライブログが進んだぶん k/n がずれ、正しい下書きでも RED になる"
                        f"（2026-08-11 に #065 が 0/6 → 凍結して 6/6 緑を実測）。"
                        f"asof は記事の公開日と同じJST日付でなければ RED＝都合のよい断面は選べない")
            bad.append(("エスカレ滞留", "warn"))
        else:
            body.append(f"- ✅ 🟢 未対応の 🚩 は {unresolved} 件"
                        f"（いずれも{ESCALATION_STALE_DAYS}日未満・🚩通算{flags}件）")
    except Exception as e:
        body.append(f"- 🚨 ⚪ エスカレ滞留の確認失敗: {e}")

    body.append("")
    body.append("### ⑨ Gmailアプリパスワードの死活（メール全レーンの共通の急所）")
    ok, note = check_smtp_auth()
    if ok is None:
        body.append(f"- ⚪ {note}")
    elif ok:
        body.append(f"- ✅ 🟢 {note}")
    else:
        body.append(f"- 🚨 🔴 {note}")
        bad.append(("Gmail認証失効", "critical"))

    body.append("")
    body.append("### ⑩ 市場健康度の履歴（系列別の取得停止）")
    try:
        import build_health_history as BHH
        data = json.loads(api_raw(
            f"https://api.github.com/repos/{owner}/{repo}/contents/market-health-history.json", token))
        stale, pending, watched, overdue = BHH.eval_series_health(
            data.get("health") or {}, now)
        if stale:
            det = ", ".join(f"{n}（{a}日取得なし/閾値{d}日）" for n, a, d in stale)
            body.append(f"- 🚨 🟡 取得が止まっている系列 {len(stale)}/{watched}: {det}。"
                        f"build_health_history.py の該当 fetch を実測プローブし、"
                        f"URL変更なら差し替え・恒久停止なら系列を落とす。"
                        f"⚠️ **代替の別指標を同じ名前で入れない**"
                        f"（発表元ごとに区分が違う＝2026-08-19 に CNN と alternative.me で実測）")
            bad.append(("健康度履歴の停止", "warn"))
        # 「観測開始前」は新設初日を赤くしないための猶予。猶予を過ぎても一度も取れて
        # いない系列は、放っておくと永久に🟢のまま隠れる（2026-08-29 に touraku_ratio で
        # 7日間そうなっていた＝実害）。ここで別枠にして必ず自己申告させる。
        if overdue:
            parts = []
            for n, a, g in overdue:
                meta = BHH.SERIES_META.get(n) or {}
                hint = meta.get("pending_hint")
                parts.append(f"{meta.get('label', n)}（新設から{a}日・猶予{g}日・一度も取得できていない）"
                             + (f"＝{hint}" if hint else ""))
            body.append(f"- 🚨 🟡 一度も取れていない系列 {len(overdue)}/{watched}: "
                        + " / ".join(parts)
                        + "。**ライブは該当指標を「取得不可」表示のまま**＝新設時の設定漏れ"
                          "（APIキー未登録・URL誤り）を先に疑う。恒久停止なら系列ごと落とす")
            bad.append(("健康度履歴の未開始", "warn"))
        if not stale and not overdue:
            note = f"（観測開始前 {len(pending)} 本）" if pending else ""
            body.append(f"- ✅ 🟢 監視 {watched} 系列すべて閾値内{note}")
    except Exception as e:
        # ③〜⑧と同じ方針: API/import の一時エラー自体では Issue を立てない（記録のみ）
        body.append(f"- 🚨 ⚪ 健康度履歴の確認失敗: {e}")

    body.append("")
    body.append("### ⑪ main の巻き戻し（force-push）")
    try:
        hits = check_force_push(owner, repo, token, now)
        if hits:
            det = ", ".join(f"{h['at']}（{h['actor']}・{h['before']}→{h['after']}・{h['age_h']}h前）"
                            for h in hits)
            body.append(f"- 🚨 🔴 直近{FORCE_PUSH_WINDOW_H}時間に main の force-push が {len(hits)}件: {det}。"
                        f"**消えたコミットは GitHub 側にしばらく残る**＝まず退避する: "
                        f"before の完全SHA に branch を立てる"
                        f"（POST /repos/{owner}/{repo}/git/refs に "
                        f'{{"ref":"refs/heads/rescue-YYYYMMDD","sha":"<before の完全SHA>"}}）。'
                        f"退避後は before を土台に巻き戻り後のコミットを cherry-pick し、"
                        f"`git merge --no-commit -s ours` + `git read-tree -u --reset` で"
                        f"**fast-forward の1コミット**にして push する"
                        f"（force を force で上書きしない＝二重に履歴を壊さない）。"
                        f"⚠️ データ系（signals-log 等）は行数の多い側＝巻き戻り前を採用する。"
                        f"恒久対策は main の ruleset に non_fast_forward を入れること"
                        f"（Settings → Rules → Rulesets → Block force pushes）")
            bad.append(("mainの巻き戻し", "critical"))
        else:
            body.append(f"- ✅ 🟢 直近{FORCE_PUSH_WINDOW_H}時間に main の force-push なし")
    except Exception as e:
        # ③〜⑧と同じ方針: API の一時エラー自体では Issue を立てない（記録のみ）
        body.append(f"- 🚨 ⚪ force-push の確認失敗: {e}")

    body.append("")
    body.append("### ⑫ 日本株ランキングの鮮度（①はworkflow成否しか見ない死角＝データ側で見る）")
    try:
        rank = json.loads(api_raw(
            f"https://api.github.com/repos/{owner}/{repo}/contents/jp-rankings.json", token))
        settled = latest_settled_trading_date(fetch_jp_trading_dates(), now)
        asof = rank.get("asof") or ""
        if settled and asof and asof < settled:
            body.append(f"- 🚨 🟡 日本株ランキングが古い: jp-rankings.json の asof={asof} / "
                        f"上流(Yahoo)の確定最終営業日={settled}。**ライブ hot-assets は前の営業日の"
                        f"順位を出したまま**。build_jp_rankings.py は多数派の営業日しか書かない"
                        f"（2026-08-29 のガード）ので、上流が追いつけば次の回で自動的に直る。"
                        f"2日以上続くなら cron の実行時刻が上流の公開前にずれていないかを見る")
            bad.append(("日本株ランキングの鮮度", "warn"))
        elif settled and asof:
            body.append(f"- ✅ 🟢 asof={asof}（上流の確定最終営業日と一致）")
        else:
            body.append(f"- ⚪ 判定不能（asof={asof or 'なし'} / 上流={settled or 'なし'}）")
    except Exception as e:
        # ③〜⑧と同じ方針: API/ネットワークの一時エラー自体では Issue を立てない（記録のみ）
        body.append(f"- 🚨 ⚪ 日本株ランキングの鮮度確認に失敗: {e}")

    body.append("")
    body.append("### ⑬ カレンダーの先詰まり（①②はworkflow成否しか見ない死角＝中身で見る）")
    try:
        cal = json.loads(api_raw(
            f"https://api.github.com/repos/{owner}/{repo}/contents/economic-events.json", token))
        ok_cal, n_cal, nearest = judge_calendar_runway(cal.get("events", []), now)
        if ok_cal:
            body.append(f"- ✅ 🟢 今後{FORWARD_DAYS}日に指標 {n_cal} 件（直近: {nearest}）")
        else:
            body.append(
                f"- 🚨 🟡 今後{FORWARD_DAYS}日の経済指標が {n_cal} 件（閾値 {FORWARD_MIN} 以上）"
                f"＝カレンダーが尽きかけている。**シグナルの「🚫 重要指標まで X h」が出なくなる**"
                f"（2026-08 に2か月ゼロで113本のシグナルが無警告だった事故と同じ形）。"
                f"直し方＝generate_market_news.py の ECONOMIC_EVENTS_2026 に翌月以降を追記し、"
                f"monthly-calendar-reminder.yml を手動実行する（sync_economic_events.py が"
                f"そこから economic-events.json を生成する）。⚠️ economic-events.json を直接"
                f"編集しても次回の生成対象にはならない。市場休場は別枠で自動補充されるので"
                f"**「イベントはある」ように見えても指標はゼロになりうる**")
            bad.append(("経済指標カレンダーの先詰まり", "warn"))
    except Exception as e:
        body.append(f"- 🚨 ⚪ 経済指標カレンダーの確認に失敗: {e}")

    # 決算予定も同じ形で腐る。2026-08-30 実測: build_earnings_calendar.py が
    # **どのワークフローからも呼ばれておらず**、earnings-calendar.json が
    # updated=2026-06-26 のまま（US 9/20件・JP は20件すべて過去日）で
    # calendar.html に描画され続けていた。いまは monthly-calendar-reminder.yml が
    # 毎月呼ぶが、上流（Nasdaq API / yfinance）が黙って空を返せば同じ形になる。
    try:
        ec = json.loads(api_raw(
            f"https://api.github.com/repos/{owner}/{repo}/contents/earnings-calendar.json", token))
        today = now.astimezone(dt.timezone(dt.timedelta(hours=9))).date().isoformat()
        fut_us = [x for x in ec.get("us", []) if x.get("date", "") >= today]
        fut_jp = [x for x in ec.get("jp", []) if x.get("date", "") >= today]
        if not fut_us or not fut_jp:
            body.append(
                f"- 🚨 🟡 決算予定に未来分が無い（米 {len(fut_us)} 件 / 日 {len(fut_jp)} 件・"
                f"updated={ec.get('updated')}）＝calendar.html が過去の決算を出し続ける。"
                f"直し方＝monthly-calendar-reminder.yml を手動実行"
                f"（build_earnings_calendar.py が Nasdaq API と yfinance の2系統で取る）。"
                f"両方0なら上流の障害、片方だけなら該当国のソースを疑う")
            bad.append(("決算予定の先詰まり", "warn"))
        else:
            body.append(f"- ✅ 🟢 決算予定の未来分: 米 {len(fut_us)} 件 / 日 {len(fut_jp)} 件"
                        f"（updated={ec.get('updated')}）")
    except Exception as e:
        body.append(f"- 🚨 ⚪ 決算予定の確認に失敗: {e}")

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
