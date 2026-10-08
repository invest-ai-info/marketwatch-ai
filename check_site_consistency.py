# -*- coding: utf-8 -*-
"""
check_site_consistency.py — サイトの「不変条件」を自動検査するリンター
================================================================================
目的: ルールが増えても破綻しないよう、"人間が手で守る前提"をやめて
      "コードが自動で守る"形にする。公開(sync)前に実行し、ミスをライブ前に止める。

新しいルールができたら → この中に検査を1個足すだけ（＝拡張の入口）。

検査内容:
  🚨 SYNC禁忌ファイルが SYNC_FILES に混入していないか（過去の巻き戻し事故の自動防止）
  各 guide-*.html（週次/自動生成を除く）について:
    - kinsho-v1 免責があるか（error）
    - 10ボタンナビがあるか（warning）
    - SYNC_FILES に登録されているか（error: sync されない）
    - sitemap.xml に登録されているか（warning）
    - guides.html にカードがあるか（warning: 一覧から辿れない）
  guides.html のリンク切れ（存在しない guide を指していないか）（error）

exit code: error があれば 1、無ければ 0（CI/フックで分岐できる）

使い方:
  python check_site_consistency.py            # 検査して結果表示
  python check_site_consistency.py --quiet    # エラー時のみ詳細表示
"""
import os
import re
import subprocess
import sys
import glob

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SD = os.path.dirname(os.path.abspath(__file__))

# SYNC禁忌（CLAUDE.md準拠）: これらが SYNC_FILES に入っていたら巻き戻し事故 → error
SYNC_FORBIDDEN = {
    "index.html", "calendar.html", "charts.html", "vix.html",
    "market-health.html", "hot-assets.html", "sitemap.xml",
    "signals-log.json", "signals-log.csv", "track-record.html",
    "research-list.html",   # 🆕 2026-10-07 検証中リスト（technical-alerts が track-record.html と一緒に生成）
    "political-feed.html", "political-feed.json",
    "youtube-summary.html", "youtube-summary-data.json",
    "fundamental-context.json", "weekly-levels.json", "weekly-zone-plan.md",
    "article-ideas.md", "daily-preview.md", "political-digest.md",
    "compliance-scan.md", "weekly-strategy-context.json",
    "signal-lab-tracker.json",  # 前向きトラッカー状態（routineがGitHub側でupdate/commit。SEEDはsignal_lab_tracker.py内）
    "signals-log-backtest.json",  # 日足リプレイ出力（ローカル/週次再生成の派生データ・大容量。ローカルpush禁止）
    "jp-rankings.json",  # 値上がり/値下がりランキング（jp-rankings.yml が GitHub 側で毎朝生成・コミット。ローカルpush禁止）
    "jp-margin.json",  # 信用残ウォッチ（jp-rankings.yml が build_jp_margin.py で生成・コミット。ローカルpush禁止）
    "jp-highs.json",  # 高値・安値の更新銘柄（jp-rankings.yml が build_jp_highs.py で生成・コミット。日ごとの件数の履歴を持つ＝ローカルpush禁止）
    "news-ticker.json",  # ⚡最新ニュース・ライブフィード（news-ticker.yml が毎時GitHub側で生成・コミット。ローカルpush禁止）
    "market-health-history.json",  # 市場健康度の日次履歴（update-market-news.yml が GitHub側で生成・コミット。ローカルpush禁止）
    "economic-events.json",  # 経済指標＋市場休場（monthly-calendar-reminder.yml が GitHub側で
                             # generate_market_holidays.py と sync_economic_events.py で生成・コミット。
                             # 元データは generate_market_news.py の ECONOMIC_EVENTS_2026＝そちらを編集する）
    "earnings-calendar.json",  # 決算予定（同ワークフローが build_earnings_calendar.py で
                               # Nasdaq API + yfinance から生成・コミット。ローカルpush禁止）
    "touraku-history.json",  # 騰落レシオの日次履歴（update-market-news.yml が GitHub側で生成・コミット。ローカルpush禁止）
    "edinet-holdings.json",  # 大量保有報告書の新着（edinet-holdings.yml が平日GitHub側で生成・コミット。ローカルpush禁止）
    "edinet-yuho.json",  # 話題の企業の有報本文（edinet-yuho.yml が平日GitHub側で生成・コミット。routine company-weekly-auto が読む。ローカルpush禁止）
    "guide-new-books.html",  # 投資本新刊ウォッチ（routine book-watch-weekly が毎週土曜GitHub側で更新。ローカルpush禁止）
    "idea-inbox.md",  # 研究アイデア受信箱 drafts/idea-inbox.md（routine idea-scout-weekly が毎週日曜GitHub側で追記。照合はbasename）
    # 🆕 2026-07-07 進化ループのローカル専用ファイル（非公開研究＝公開リポへ流出させない）
    "DOCTRINE.md", "hypothesis_queue.md", "_doctrine_check.py", "_hypothesis_registry.json",
    # 🆕 2026-07-31 アーカイブ2種（basename でも止める＝research/ プレフィックス無しで
    # 書かれた場合の保険。ディレクトリ規則は上の検査1の research/ 分岐が担う）
    "DOCTRINE_ARCHIVE.md", "hypothesis_queue_archive.md",
    # 🆕 2026-09-26 研究ラボの出力（GitHub の Actions が生成・前向きの判定の履歴を持つ＝ローカルから push 禁止。
    #   古い版で上書きすると積み上げた前向きの判定が消える）。オーナー指示で Claude が追加。
    "exit-lab.json", "exit-lab.md",            # 出口の相性ラボ（exit-lab.yml・日曜）
    "exit-wall-lab.json", "exit-wall-lab.md",  # 出口の壁ラボ（exit-research.yml・日曜）
    "stop-lab.json", "stop-lab.md",            # 損切りラボ（exit-research.yml・日曜）
    "regime-lab.json", "regime-lab.md",        # 環境の相性ラボ（regime-lab.yml・手動）
    # 🆕 2026-09-26 シグナルの環境の統計（env-profile.yml・月1。月ごとの履歴を持つ＝古い版で上書きすると変化が追えなくなる）
    "signal-env-profile.md", "signal-env-profile.json", "signal-env-profile-history.json",
    # 🆕 2026-09-27 新しい柱・第1波（pillar-lab.yml・手動。事前登録 PILLAR_PREREG.md の指紋付きの結果）
    "pillar-lab.json", "pillar-lab.md",
    "pillar-lab-jp.json", "pillar-lab-jp.md",   # 第2波・日本株（pillar-lab-jp.yml・手動）
    "trend-lab.json", "trend-lab.md",           # トレンドの見方の比べ比べ（trend-lab.yml・手動）
    "combo-lab.json", "combo-lab.md",           # 組み合わせの相性ラボ（combo-lab.yml・手動）
    "exit-ind-lab.json", "exit-ind-lab.md",     # 出口の指標ラボ E1（exit-ind-lab.yml・手動）
    "exit-ind-lab-4h.json", "exit-ind-lab-4h.md",   # 🆕 2026-10-01 M7 腕A 4時間足で同じ総当たり（exit-ind-lab-4h.yml・手動）
    "combo-forward.json", "combo-forward.md",   # 🆕 2026-09-27 前向きの観察（combo-forward.yml・月1。区切りの記録を持つ）
    "yori-lab.json", "yori-lab.md",             # 🆕 2026-09-28 J4 寄り付きラボ（yori-lab.yml・手動。銘柄名は出さない）
    "yori-forward.json", "yori-forward.md",     # 🆕 2026-09-28 J4F 寄り付きの前向き（yori-forward.yml・平日。積み上げた取引と判定を持つ）
    "london-lab.json", "london-lab.md",         # 🆕 2026-09-30 L1・L2 ロンドン時間のドルの流れ（london-lab.yml・手動。検証済みリストの元にもなる）
    "london-hold-lab.json", "london-hold-lab.md",   # 🆕 2026-09-30 L4 ロンドン時間に入って長めに持つ（london-hold-lab.yml・手動）
    "hold-lab.json", "hold-lab.md",             # 🆕 2026-10-05 R1 持ち方の研究（hold-lab.yml・手動。ビットコインと株価指数）
    "buy-lab.json", "buy-lab.md",               # 🆕 2026-10-05 R2 余剰資金の入れ方（buy-lab.yml・手動。一括・分ける・下がったら買う）
    "calendar-lab.json", "calendar-lab.md",     # 🆕 2026-10-05 R3 株価指数の時間の癖（calendar-lab.yml・手動。月末月初・日中のモメンタム）
    "calendar-forward.json", "calendar-forward.md",   # 🆕 2026-10-05 R3F 月末月初の前向きの観察（calendar-forward.yml・月1。取引の記録を持つ）
    "fx-month-end-lab.json", "fx-month-end-lab.md",   # 🆕 2026-10-05 R4 月末の値決め前の為替ヘッジ（fx-month-end-lab.yml・手動）
    "holiday-lab.json", "holiday-lab.md",       # 🆕 2026-10-05 R5 日本の祝日の前の日（holiday-lab.yml・手動）
    "r4-window-lab.json", "r4-window-lab.md",   # 🆕 2026-10-05 夜 R4 腕C 正確なロンドンの窓（r4-window-lab.yml・手動）。腕B の r4-armb.* は手元の成果なので入れない
    "fx-clock-lab.json", "fx-clock-lab.md",     # 🆕 2026-10-07 X 為替の時計の癖（fx-clock-lab.yml・手動）
    "intl-tom-lab.json", "intl-tom-lab.md",     # 🆕 2026-10-05 深夜 R6 ほかの国の月末月初（intl-tom-lab.yml・手動）
    "highs-trap-lab.json", "highs-trap-lab.md", # 🆕 2026-10-06 J10 高値更新の翌朝の罠（highs-trap-lab.yml・手動。銘柄名は出さない）
    "highs-trap-forward.json", "highs-trap-forward.md",   # 🆕 2026-10-06 J10F 罠の目印の前向き（highs-trap-forward.yml・平日。積み上げた取引と判定を持つ）
    "index-open-lab.json", "index-open-lab.md",   # 🆕 2026-10-06 R7 株価指数の朝の窓・夜の上げ（index-open-lab.yml・手動）
    "night-history-lab.json", "night-history-lab.md",   # 🆕 2026-10-08 R8 日経平均の夜の上げを昔の時代で（night-history-lab.yml・手動）
    "short-side-lab.json", "short-side-lab.md",   # 🆕 2026-10-08 J30 目印の付いた株を寄りで売る（short-side-lab.yml・手動）
    "auction-lab.json", "auction-lab.md",   # 🆕 2026-10-08 J31 板寄せどうしで数え直す（auction-lab.yml・手動）
    "stop-short-lab.json", "stop-short-lab.md",   # 🆕 2026-10-08 J32 J31 の売りに損切り（stop-short-lab.yml・手動）
    "auction-forward.json", "auction-forward.md",   # 🆕 2026-10-08 J31F 空売りの前向き（auction-forward.yml・平日）
    "size-short-lab.json", "size-short-lab.md",   # 🆕 2026-10-08 J33 建玉の大きさ（size-short-lab.yml・手動）
    "market-adj-lab.json", "market-adj-lab.md",   # 🆕 2026-10-08 J34 相場全体を差し引く（market-adj-lab.yml・手動）
    "highs-trap-small.json", "highs-trap-small.md",   # 🆕 2026-10-06 J11 J10 の目印を約400銘柄の外で（highs-trap-small.yml・手動）
    "lows-trap-lab.json", "lows-trap-lab.md",         # 🆕 2026-10-06 J12 安値更新の翌朝（lows-trap-lab.yml・手動）
    "gap-lab.json", "gap-lab.md",                     # 🆕 2026-10-06 J13 窓を開けて寄った株（gap-lab.yml・手動）
    "gap-forward.json", "gap-forward.md",             # 🆕 2026-10-06 J13F 窓の戻し・前向き（gap-forward.yml・平日）
    "gap-history-lab.json", "gap-history-lab.md",     # 🆕 2026-10-07 J14 窓の戻しを昔の期間で（gap-history-lab.yml・手動）
    "gap-split-lab.json", "gap-split-lab.md",         # 🆕 2026-10-07 J15 その銘柄だけの窓か相場全体の窓か（gap-split-lab.yml・手動）
    "prevday-lab.json", "prevday-lab.md",             # 🆕 2026-10-07 J16 前の日に大きく動いた株の翌朝（prevday-lab.yml・手動）
    "prevgap-lab.json", "prevgap-lab.md",             # 🆕 2026-10-07 J17 前の日の上げ×その銘柄だけの窓（prevgap-lab.yml・手動）
    "third-period-lab.json", "third-period-lab.md",   # 🆕 2026-10-07 J18 目印を2006〜2016年で確かめる（third-period-lab.yml・手動）
    "bounce-cost-lab.json", "bounce-cost-lab.md",     # 🆕 2026-10-07 J19 安く寄った株の戻りを銘柄ごとの費用で（bounce-cost-lab.yml・手動）
    "prevgap-forward.json", "prevgap-forward.md",   # 🆕 2026-10-07 J17F 寄りで買わない目印の前向き（prevgap-forward.yml・平日）
    "tvsurge-forward.json", "tvsurge-forward.md",   # 🆕 2026-10-07 夜 J26F 目印C 前の日の売買代金の急増の前向き（tvsurge-forward.yml・平日）
    "main-field-lab.json", "main-field-lab.md",       # 🆕 2026-10-07 J20 主戦場を翌朝の寄りで買うと（main-field-lab.yml・手動）
    "landmine-lab.json", "landmine-lab.md",           # 🆕 2026-10-07 J21 主戦場から地雷を外すと（landmine-lab.yml・手動）
    "open30-lab.json", "open30-lab.md",               # 🆕 2026-10-07 J22 9:00〜9:30 に上がった株・下がった株の法則（open30-lab.yml・手動）
    "dip-lab.json", "dip-lab.md",                     # 🆕 2026-10-07 J23 寄りのあとの急落は何％で反転するか（dip-lab.yml・手動）
    "cost-recount-lab.json", "cost-recount-lab.md",   # 🆕 2026-10-07 J24 J19・J23 の費用の数え直し（cost-recount-lab.yml・手動）
    "market-dip-lab.json", "market-dip-lab.md",       # 🆕 2026-10-07 J25 相場全体が安く寄った朝の深い下げ（market-dip-lab.yml・手動）
    "market-dip-forward.json", "market-dip-forward.md",   # 🆕 2026-10-07 J25F 同・前向き（market-dip-forward.yml・平日）
    "open30-history-lab.json", "open30-history-lab.md",   # 🆕 2026-10-07 夜 J26 J22 の目印を昔の2つの時代で（open30-history-lab.yml・手動）
    "open5-skip-lab.json", "open5-skip-lab.md",   # 🆕 2026-10-07 夜 J27 最初の5分のあと足を1本空けても戻るか（open5-skip-lab.yml・手動）
    "spread-lab.json", "spread-lab.md",   # 🆕 2026-10-07 夜 J28 売り買いの差の見積もりを日足と5分足で比べる（spread-lab.yml・手動）
    "bounce-range-lab.json", "bounce-range-lab.md",   # 🆕 2026-10-07 夜 J29 安く寄った株の戻りを費用に幅を持たせて数え直す（bounce-range-lab.yml・手動）
    "verified-list.md",                         # 🆕 2026-09-28 検証済みリスト（verified_list.py が前向きの記録から組み立てる）
    "promotion-list.md",                        # 🆕 2026-09-30 昇格リスト（promotion_list.py が記録から組み立てる・research-lists.yml／yori-forward.yml）
    "signals-recent.json",                      # 🆕 2026-09-30 AT3 直近7日の4時間足の合図の写し（technical-alerts.yml が build_signals_recent.py で書く）
    "box-lab.json", "box-lab.md",               # 🆕 2026-09-27 S1 時間帯の箱の抜け（box-lab.yml・手動。スキャルピング本の整理から）
    "event-dir-lab.json", "event-dir-lab.md",   # 🆕 2026-09-27 S2 重要な発表のあとの向き（event-dir-lab.yml・手動。B2 の続き）
    "round-lab.json", "round-lab.md",           # 🆕 2026-09-28 S3 キリの良い値（round-lab.yml・手動。スキャルピング本の最後の候補）
    "candle-lab.json", "candle-lab.md",         # 🆕 2026-09-27 C1 シグナルの直前の足の形（candle-lab.yml・手動。FX本100冊の下調べから）
    "pattern-lab.json", "pattern-lab.md",       # 🆕 2026-09-28 C2 チャートパターン（pattern-lab.yml・手動。FX本100冊の最後の候補）
}

errors = []
warnings = []

# 🛡️ 2026-07-05: sync_to_github.py スタブ上書き事故の再発防止。
# GitHub側の sync_to_github.py は publish_article のクラウド用スタブ＝本物ではない。
# リモートから取り込むと本物（全SYNC_FILESリスト+staleガード）が消える（実際に起きた→OneDrive版履歴で復旧）。
# 2026-07-08 修正: クラウド環境（GITHUB_ACTIONS_RUN=true または スタブ判定）では
#   スタブは「想定どおり」のため、エラーではなく警告に留めSYNC_FILES系チェックをスキップ。
#   ローカル環境でスタブ化していた場合だけエラー（事故防止のガードを維持）。
_stg = os.path.join(SD, "sync_to_github.py")
_is_cloud_stub = False
if os.path.exists(_stg):
    _stg_src = open(_stg, encoding="utf-8", errors="replace").read()
    _is_stub = os.path.getsize(_stg) < 20000 or "staleness" not in _stg_src
    _in_cloud = (os.environ.get("GITHUB_ACTIONS_RUN") == "true"
                 or "sync stub for cloud" in _stg_src)
    if _is_stub and _in_cloud:
        _is_cloud_stub = True
        warnings.append("sync_to_github.py はクラウド用スタブ（想定どおり）→ SYNC_FILES 系チェックをスキップ")
    elif _is_stub:
        errors.append("🚨 sync_to_github.py がスタブ/破損の疑い（<20KB or staleガード無し）"
                      "→ リモートの616Bスタブで上書きした可能性。OneDriveバージョン履歴から復元すること")


def _in_git_worktree():
    """このチェックが git リポジトリの中で走っているか。

    🔑 ローカルPCの作業フォルダは git リポジトリではない（CLAUDE.md「作業フォルダ」）。
    クラウド側（GitHub Actions / routine / Claude セッション）は必ずリポジトリ内で走る。
    guides.html の鮮度が保証されるのはリポジトリ内だけなので、「カードが無い」を
    **error に格上げしてよいのはリポジトリ内のときだけ**（ローカルは記事ミラーが先に来て
    カードが後から届くため、error にすると sync が止まって人を困らせる）。
    """
    try:
        r = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"],
                           cwd=os.path.dirname(os.path.abspath(__file__)),
                           capture_output=True, text=True, timeout=20)
        return r.returncode == 0 and r.stdout.strip() == "true"
    except Exception:
        return False


def _read(p):
    with open(os.path.join(SD, p), encoding="utf-8") as f:
        return f.read()


def _exists(p):
    return os.path.exists(os.path.join(SD, p))


def get_sync_files():
    """sync_to_github.py の SYNC_FILES を正規表現で抽出（importせず安全に）。
    sync_to_github.py はローカル専用（GitHub 未追跡）なので、リモート(routine)実行時は不在。
    クラウドスタブ（_is_cloud_stub=True）の場合も None を返してスキップ（偽陽性防止）。"""
    if not _exists("sync_to_github.py"):
        return None
    if _is_cloud_stub:
        return None
    s = _read("sync_to_github.py")
    m = re.search(r"SYNC_FILES\s*=\s*\[(.*?)\n\]", s, re.S)
    if not m:
        warnings.append("sync_to_github.py の SYNC_FILES ブロックを解析できない → SYNC_FILESチェックをスキップ")
        return None
    return set(re.findall(r'"([^"]+)"', m.group(1)))


def check_economic_events():
    """経済カレンダーの決定論検査（2026-07-02 の日付誤り事故=CPI 7/10等の再発防止）。
    誤りやすいのは「パターン外挿で足した未来の日付」。機械で検査できる不変条件だけ見る:
      雇用統計=金曜 / high・mid指標が土日は疑わしい / FOMC結果=公式2026日程±1日 / ECB=木曜が通例。"""
    import datetime as dt
    if not _exists("generate_market_news.py"):
        return
    m = re.search(r"ECONOMIC_EVENTS_2026\s*=\s*\[(.*?)\n\]", _read("generate_market_news.py"), re.S)
    if not m:
        warnings.append("ECONOMIC_EVENTS_2026 が解析できない → カレンダー日付検査をスキップ")
        return
    rows = re.findall(r'\(\s*(\d+),\s*(\d+),\s*"(\w+)",\s*"(\w+)",\s*"([^"]+)"', m.group(1))
    # 2026年のFOMC決定日（federalreserve.gov 公式・ET基準）。年替わりでここを更新する
    fomc_official = {(1, 28), (3, 18), (4, 29), (6, 17), (7, 29), (9, 16), (10, 28), (12, 9)}
    today = dt.date.today()
    for mo_s, dy_s, region, imp, name in rows:
        mo, dy = int(mo_s), int(dy_s)
        try:
            d = dt.date(2026, mo, dy)
            wd = d.weekday()
        except ValueError:
            warnings.append(f"カレンダー: {mo}/{dy}「{name}」＝存在しない日付")
            continue
        if d < today:
            continue  # 過去分は表示済み＝修正不能。検査は未来の日付のみ（警告ノイズ防止）
        if "中国" in name and "PMI" in name:
            continue  # 中国国家統計局PMIは月末公表＝土日もあり得る（正当な例外）
        if "雇用統計" in name and wd != 4:
            warnings.append(f"カレンダー: {mo}/{dy}「{name}」が金曜でない（米雇用統計は原則金曜）＝要確認")
        elif wd >= 5 and "休場" not in name:
            warnings.append(f"カレンダー: {mo}/{dy}「{name}」が{'土日'[wd - 5]}曜＝日付要確認")
        if "FOMC" in name and "結果" in name:
            near = any(abs((dt.date(2026, mo, dy) - dt.date(2026, om, od)).days) <= 1 for om, od in fomc_official)
            if not near:
                warnings.append(f"カレンダー: {mo}/{dy}「{name}」が公式FOMC日程(±1日)と不一致＝要確認")
        if "ECB" in name and wd != 3:
            warnings.append(f"カレンダー: {mo}/{dy}「{name}」が木曜でない（ECB理事会は木曜が通例）＝要確認")


def check_sync_forbidden(sync_files):
    """SYNC禁忌の判定（3層: 個別禁忌リスト / `_`プレフィックス / research/ ディレクトリ）。

    2026-07-31 に main() から切り出しただけで判定内容は不変＝回帰テスト
    `_test_sync_research_guard.py` がここを直接呼べるようにするため。
    """
    for f in sorted(sync_files):
        base = os.path.basename(f)
        if base in SYNC_FORBIDDEN or f in SYNC_FORBIDDEN or re.match(r"technical-alerts-history.*\.json$", base):
            errors.append(f"🚨 SYNC禁忌ファイルが SYNC_FILES に混入: {f}（ローカルpushで巻き戻し事故の恐れ）")
        elif base.startswith("_"):
            # 🆕 2026-07-07: 「_プレフィックス＝ローカル専用（非公開研究/個人データ）」規約をコードで強制
            errors.append(f"🚨 ローカル専用（_プレフィックス）ファイルが SYNC_FILES に混入: {f}（非公開研究の流出防止）")
        elif re.match(r"(?i)(detailed)?statement.*\.html?$", base):
            # 🆕 2026-09-27: MT4 の口座履歴（Statement.htm）＝名前・口座番号・全取引が入った個人の記録。
            #   投資スタイル診断（style_diagnosis.py）の入力で、置き場所は research/ の下。名前で止める保険
            errors.append(f"🚨 MT4 の口座履歴が SYNC_FILES に混入: {f}（個人の取引記録の流出防止）")
        elif f.replace("\\", "/").startswith("drafts/") and base.startswith("draft-"):
            # 🆕 2026-10-04: 下書き（drafts/draft-*.html）はルーティンが GitHub 側で作る非公開の置き場。
            #   10/2 の研究日誌が下書きのパスのまま publish_article に通し、SYNC_FILES に入った
            errors.append(f"🚨 下書き（drafts/draft-*）が SYNC_FILES に混入: {f}（公開物ではない・GitHub 側で生成）")
        elif f.replace("\\", "/").startswith("yutai-edinet/"):
            # 🆕 2026-09-30: 株主優待の有報あつめ（yutai-edinet.yml が GitHub 側で積み上げる）。
            #   古い版で上書きすると取り終えた日・読んだ有報の記録が消える＝ローカルから push しない
            errors.append(f"🚨 GitHub 側で生成する yutai-edinet/ が SYNC_FILES に混入: {f}（巻き戻し事故の恐れ）")
        elif f.replace("\\", "/").startswith(("fx-bars/", "fx-new/")) or base.endswith(".bi5"):
            # 🆕 2026-10-07: 為替の値段の置き場（fx_bars.py・Dukascopy の1時間足）。actions/cache と artifact だけに置く
            errors.append(f"🚨 為替の値段の置き場（fx-bars/・*.bi5）が SYNC_FILES に混入: {f}（actions/cache だけに置く）")
        elif f.replace("\\", "/").startswith("jp-bars/") or base.endswith(".npz"):
            # 🆕 2026-10-06 夜: 研究ラボ共通の値段の置き場（jp_bars.py）。actions/cache と artifact だけに置く＝
            #   銘柄ごとの値段の大きなファイル。リポジトリに入れると Pages で配信されてしまう
            errors.append(f"🚨 値段の置き場（jp-bars/・*.npz）が SYNC_FILES に混入: {f}（actions/cache だけに置く）")
        elif f.replace("\\", "/").startswith("research/"):
            # 🆕 2026-07-31: 「research/ 配下は丸ごとローカル専用」をディレクトリ単位で強制。
            # 列挙式（SYNC_FORBIDDEN に1件ずつ足す）は足し忘れが穴になる＝実測で research/ の
            # 非アンダースコア .md 13件のうち登録済みは2件だけだった（非公開仮説の全文147KB＝
            # hypothesis_queue_archive.md すら未登録）。境界は実態と一致する＝SYNC_FILES 全件に
            # research/ 配下は1件も無い（誤検知率は `_test_sync_research_guard.py` が毎回実測）。
            errors.append(f"🚨 research/ 配下（非公開研究）が SYNC_FILES に混入: {f}（公開リポへの流出防止）")


def check_liquid_in_markdown(sync_files):
    """同期する .md に Liquid 構文（波括弧2連・波括弧＋％）が無いか検査する。

    🔴 2026-08-05 の実事故: GitHub Pages(Jekyll) は **.md を Liquid テンプレートとして解釈**する。
       SESSION_HANDOFF.md に「f-string の波括弧は二重」と説明するため波括弧を2つ並べて書いただけで
       閉じられない Liquid タグとみなされ、**Pages のビルドが12時間全失敗**した
       （duration=0 の即失敗・エラー本文は "Page build failed." だけで原因が出ない）。
       ライブは古いビルドを配信し続けるので**訪問者に破損は見えず**、health-check も
       「最終更新の日付が今日か」しか見ないため**緑のまま**＝人力では気づけない壊れ方をする。

    判定は `.nojekyll` の有無で段階を変える:
       無い → Jekyll が走る＝**実際にビルドが落ちる**ので error
       有る → 無害化済みだが、`.nojekyll` を失うと再発する潜在リスクなので warning
    """
    md = [f for f in sync_files if f.lower().endswith(".md")]
    has_nojekyll = _exists(".nojekyll")
    for f in sorted(md):
        if not _exists(f):
            continue
        body = _read(f)
        hits = body.count("{" + "{") + body.count("{" + "%")
        if not hits:
            continue
        msg = (f"{f}: Liquid 構文（波括弧2連 等）が {hits}箇所。"
               f"Jekyll がテンプレートとして解釈しビルドが落ちる")
        if has_nojekyll:
            warnings.append(msg + "（.nojekyll があるので現状は無害）")
        else:
            errors.append("🚨 " + msg + "（.nojekyll が無い＝ライブ更新が止まる）")


def check_series_numbering():
    """連番シリーズ（AIシグナル研究日誌）の回番号を検査する。

    🚨 2026-09-06 事故＝ `guide-signal-lab-089.html`（9/4公開・N=287）に 9/6 の実行が
       別記事を上書きし、公開済み本文が消えた。カードは9/4版のままで誰も気づかなかった。
       → 「番号の重複」と「ファイル名の番号 ≠ タイトルの #番号」を機械で見張る。
    """
    seen = {}
    for path in sorted(glob.glob(os.path.join(SD, "guide-signal-lab-*.html"))):
        name = os.path.basename(path)
        m = re.search(r"-(\d+)\.html$", name)
        if not m:
            continue
        file_no = int(m.group(1))
        text = _read(name)
        tm = re.search(r"<title>(.*?)</title>", text, re.S)
        title = re.sub(r"\s+", " ", tm.group(1)).strip() if tm else ""
        nm = re.search(r"#0*(\d+)", title)
        if not nm:
            warnings.append(f"{name}: タイトルに回番号(#NN)が無い＝番号の取り違えを検知できない")
        elif int(nm.group(1)) != file_no:
            errors.append(f"🚨 {name}: ファイル名の番号({file_no})とタイトルの #{nm.group(1)} が不一致"
                          f"（番号の取り違え/上書き公開の疑い）")
        seen.setdefault(file_no, []).append(name)
    for no, files in sorted(seen.items()):
        if len(files) > 1:
            errors.append(f"🚨 回番号 #{no} が重複: {', '.join(files)}")


def check_card_dates(guides_html, gen_py="generate_market_news.py"):
    """記事一覧のカードと記事本体の食い違いを検査する（2026-10-04 新設・#115 上書き公開事故の再発防止）。

    🚨 2026-10-02 事故＝研究日誌が publish_article を**下書きのパス**（drafts/draft-signal-lab-115.html）に
       通したため上書きゲートが下書き同士を比べて素通りし、10/1 公開の #115 が別の記事で上書きされた。
       一覧には「下書きを指すカード」と「中身と違う題名・日付のカード」が残った。
       → ①カード・更新履歴が drafts/ を指していないか ②カードの日付＝記事の datePublished か を見る。
       ②は導入時に全484枚で実測し、食い違いは #115 の1枚だけ（誤検知0）。
    """
    for href, body in re.findall(r'<a class="article-card" href="([^"]+)">(.*?)</a>', guides_html, re.S):
        h = href.replace("\\", "/")
        if h.startswith("drafts/"):
            errors.append(f"🚨 記事一覧のカードが下書きを指している: {href}"
                          f"（drafts/ は非公開の置き場＝読者に noindex の下書きが出る）")
            continue
        if "/" in h or h.startswith("#") or not h.endswith(".html") or not _exists(h):
            continue  # 外部リンク・欄内リンク・リンク切れ（別の検査）は対象外
        cm = re.search(r'<time datetime="(\d{4}-\d{2}-\d{2})"', body)
        am = re.search(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})', _read(h))
        if cm and am and cm.group(1) != am.group(1):
            errors.append(f"🚨 {h}: 一覧のカードの日付({cm.group(1)})と記事の公開日({am.group(1)})が違う"
                          f"（公開済みの記事が別の記事で上書きされた疑い）")
    if _exists(gen_py):
        for m in re.finditer(r'href="(drafts/[^"]+)"', _read(gen_py)):
            errors.append(f"🚨 {gen_py} の更新履歴が下書きを指している: {m.group(1)}（トップに下書きへのリンクが出る）")


def check_us_monthly_indicators():
    """米CPI・米雇用統計が「今日以降の各月にちょうど1件」あるかを見る（2026-09-11 新設）。

    🚨 なぜ曜日で検査しないか＝**この事故は曜日の思い込みが原因だった**。
       2026-09-11(金) が正しい発表日なのに「CPI は火〜木」と決めつけて 9/10(木) と書いていた。
       曜日ルールを足すと、正しい金曜の日付を誤りとして弾き、誤った木曜を通してしまう。
       機械で見てよいのは「欠落・重複」と「対象月の翌月の中旬という粗い窓」だけ。
       **日付そのものは BLS の公式スケジュールで人/エージェントが確認する**（一覧の先頭に明記）。
    """
    import datetime as dt
    if not _exists("generate_market_news.py"):
        return
    m = re.search(r"ECONOMIC_EVENTS_2026\s*=\s*\[(.*?)\n\]", _read("generate_market_news.py"), re.S)
    if not m:
        return                      # 解析不能は check_economic_events 側が既に警告する
    rows = re.findall(r'\(\s*(\d+),\s*(\d+),\s*"(\w+)",\s*"(\w+)",\s*"([^"]+)"', m.group(1))
    today = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date()
    year = today.year
    for label, pat in (("米CPI", r"^米CPI"), ("米雇用統計", r"^米雇用統計")):
        by_month = {}
        for mo, dy, _c, _i, name in rows:
            if re.match(pat, name):
                by_month.setdefault(int(mo), []).append((int(dy), name))
        for mo in range(today.month, 13):
            got = by_month.get(mo, [])
            if not got:
                warnings.append(f"カレンダー: {year}/{mo}月に「{label}」が無い（毎月1回の指標＝抜け落ちの疑い）")
            elif len(got) > 1:
                warnings.append(f"カレンダー: {year}/{mo}月の「{label}」が {len(got)} 件（{got}）＝重複の疑い")
        # CPI は「対象月の翌月の中旬」に出る。粗い窓から外れたら要確認（曜日は見ない）
        if label == "米CPI":
            for mo, got in by_month.items():
                for dy, name in got:
                    if mo >= today.month and not (8 <= dy <= 16):
                        warnings.append(f"カレンダー: {year}/{mo}/{dy}「{name}」が中旬(8〜16日)から外れる＝BLS公式で要確認")


def check_tools_strip(guides_html, gen_py="generate_market_news.py"):
    """記事一覧の「🧮 計算ツール」欄のカードが、トップページの「🧮 計算ツール」の並びにもあるか（2026-09-27 新設）。
    🚨 トップの並びは generate_market_news.py の生成テンプレに直に書かれていて publish_article.py は触らない。
       投資のクセ診断を公開したとき、記事一覧にだけ入りトップの並びに無かった（オーナーがスマホで気づいた）。"""
    m = re.search(r'<div class="category-section" id="cat-tools"[^>]*>(.*?)(?=<div class="category-section"|\Z)', guides_html, re.S)
    if not m or not _exists(gen_py):
        return
    cards = re.findall(r'<a class="article-card" href="([^"]+)"', m.group(1))
    with open(gen_py, encoding="utf-8") as fh:
        gen = fh.read()
    strip = re.search(r'<div id="tools"[^>]*>(.*?)</div>', gen, re.S)
    have = set(re.findall(r'href="([^"]+)"', strip.group(1))) if strip else set()
    for href in cards:
        if href not in have:
            errors.append(f"🚨 計算ツール {href} が記事一覧にはあるが、トップページの「🧮 計算ツール」の並び"
                          f"（{gen_py} の <div id=\"tools\">）に無い → ボタンを1つ足す")


def check_guides_sections(guides_html):
    """guides.html: data-category を宣言した欄と、カードのバッジが一致するか（2026-09-26 新設）。
    🚨 旧 publish_article は入れる欄が無いと記事一覧の先頭（🧮 計算ツール欄）へ黙って入れており、
       東証・詐欺・企業・エントリーの47枚が1か月溜まった。公開側はカテゴリゲートで止めるようにしたが、
       手作業の編集など publish_article を通らない紛れ込みもここで捕まえる。
       「解説」のように複数の欄で使うバッジがあるので、宣言した欄だけを見る（宣言の無い欄は混在を許す）。"""
    tags = list(re.finditer(r'<div class="category-section"[^>]*>', guides_html))
    bounds = [m.start() for m in tags] + [len(guides_html)]
    secs, home = [], {}
    for i, m in enumerate(tags):
        sid = re.search(r'\bid="([^"]+)"', m.group(0))
        sid = sid.group(1) if sid else f"欄{i + 1}"
        dc = re.search(r'\sdata-category="([^"]+)"', m.group(0))
        dc = dc.group(1) if dc else None
        cards = re.findall(r'<a class="article-card" href="([^"]+)">\s*<span class="article-badge [^"]*">([^<]*)</span>',
                           guides_html[m.start():bounds[i + 1]])
        secs.append((sid, dc, cards))
        if dc:
            if dc in home:
                errors.append(f"🚨 guides.html: data-category「{dc}」が #{home[dc]} と #{sid} の2か所で宣言されている")
            home.setdefault(dc, sid)
    for sid, dc, cards in secs:
        for href, badge in cards:
            if badge == dc:
                continue
            if dc is not None or badge in home:
                where = f"欄 #{sid}" + (f"（{dc}）" if dc else "")
                to = f"#{home[badge]} へ移す" if badge in home else "正しい欄へ移す（無ければ欄を作る）"
                errors.append(f"🚨 guides.html: 「{badge}」のカード {href} が {where} に紛れ込んでいる → {to}")


def main():
    quiet = "--quiet" in sys.argv
    sync_files = get_sync_files()
    sync_known = sync_files is not None  # sync_to_github.py を読めた = ローカル実行

    # 1. 🚨 SYNC禁忌チェック（最重要：巻き戻し事故防止。push直前のローカル実行でのみ意味がある）
    if sync_known:
        check_sync_forbidden(sync_files)
        check_liquid_in_markdown(sync_files)

    # 2. 各 guide-*.html（週次/自動生成を除く）の整合性
    guides_html = _read("guides.html") if _exists("guides.html") else ""
    guide_files = sorted(os.path.basename(p) for p in glob.glob(os.path.join(SD, "guide-*.html")))
    # 自動生成記事（テンプレは generate_*.py 側で管理。個別の登録チェック対象外）
    AUTO_PREFIXES = ("guide-weekly-", "guide-auto-", "guide-monthly-report-")
    # クラウド routine が GitHub 側で公開・管理する記事シリーズ。ローカルに無い／SYNC_FILES 非登録が
    # 正常なので、ローカル publish 向けの検査（SYNC_FILES登録・リンク切れ・ナビ）は誤検知になる→除外。
    # カードの巻き戻し検知は check_automation_health.py §③（毎朝の番人）が別途担保する。
    # 🆕 2026-09-23: tse/scam/company の3レーンを追加（いずれも routine が GitHub 側で公開。
    #    ミラー取り込み後に「SYNC_FILES 未登録」53件の誤検知が出て発覚）。
    CLOUD_PREFIXES = ("guide-news-", "guide-signal-lab-", "guide-proverb-",
                      "guide-tse-", "guide-scam-", "guide-company-")
    # 接頭辞を持たないクラウド公開記事（autodraft の投資心理＝guide-survivorship-bias 等・総目次）は
    # 名前で判別できない→**台帳で判別**する。台帳＝リモートのクラウドスタブ sync_to_github.py の
    # SYNC_FILES（publish_article.py が公開のたびに追記）を `_pull_mirror.py` が取り込み時に
    # `_cloud_ledger.txt` へ書き出したもの。ミラーと同時に更新されるので、ミラーで入ってきた記事は
    # 必ず台帳にも載る（名前の手書き列挙は足し忘れが穴になるのでしない）。
    cloud_ledger = set()
    if _exists("_cloud_ledger.txt"):
        cloud_ledger = {l.strip() for l in _read("_cloud_ledger.txt").splitlines()
                        if l.strip() and not l.startswith("#")}
    checked = 0
    for gf in guide_files:
        html = _read(gf)
        # 🆕 2026-08-01: 免責検査だけは**除外の前**に置く。
        # AUTO_PREFIXES の continue が SYNC登録/リンク切れ/ナビの誤検知を避けるために置かれていたが、
        # その巻き添えで免責検査まで飛んでおり、`guide-weekly-2026-05-25` と
        # `guide-auto-us_cpi-2026-05-14` の**免責ゼロを1本も検知できていなかった**（法務棚卸しで発覚）。
        # 免責は生成レーンを問わない全記事共通の不変条件＝除外の対象ではない。
        # 誤検知率は実測ゼロ（278本中、未設置は上記2本のみ＝いずれも真の欠落）。
        if 'data-disclaimer="kinsho-v1"' not in html:
            errors.append(f"{gf}: kinsho-v1 免責が無い")
        if gf.startswith(AUTO_PREFIXES):
            continue
        checked += 1
        if 'id="mw-mobile-fit"' not in html:
            warnings.append(f"{gf}: スマホ横はみ出し防止CSS(mw-mobile-fit)が無い → `python fix_mobile_overflow.py`")
        # ↑上に戻るボタン（2026-07-21）: 静的記事は apply_back_to_top.py で注入。
        # クラウド生成記事はテンプレが GitHub 側管理＝ローカル検査すると誤検知になるため対象外。
        if not gf.startswith(CLOUD_PREFIXES) and 'id="mw-back-to-top"' not in html:
            warnings.append(f"{gf}: 「↑上に戻る」ボタン(mw-back-to-top)が無い → `python apply_back_to_top.py`")
        # 免責の三層（2026-09-22 追加）: 上部バナー／本文末／フッターの3箇所に kinsho-v1 が要る。
        # 🚨 これが無いと気づけなかった実害: 2026-09-22 に雛形流用で作った記事4本が2層のまま
        #    check_guide_draft.py を GREEN で通過した（あちらは層数を数えていない）。
        #    さらに棚卸ししたところ、既存 247本が3層未満だった。
        # 🔑 判定はクラス名ではなく**位置**で行う（時期とレーンでマークアップが違い、
        #    クラス名で見ると「あるのに無い」と誤判定する）。修正は `python apply_disclaimer.py --apply`。
        # 🆕 2026-09-23: CLOUD_PREFIXES の除外を外した。免責は生成レーンを問わない不変条件
        #    （上の kinsho-v1 有無と同じ理屈）で、apply_disclaimer.py はクラウド記事も対象にしている。
        #    クラウド記事で欠けていたら直す先は GitHub 側のテンプレ＝ここで気づけないと直せない。
        _k = 'data-disclaimer="kinsho-v1"'
        _a = html.find("<article")
        _ae = html.find("</article>")
        if _a < 0 or _ae < 0:
            _a, _ae = html.find("<main"), html.find("</main>")
        _h1 = html.find("<h1", _a) if _a >= 0 else -1
        _f, _fe = html.find("<footer"), html.find("</footer>")
        _got = {"上部バナー": False, "本文末": False, "フッター": False}
        _i = html.find(_k)
        while _i >= 0:
            if _a >= 0 and _h1 > _a and _a < _i < _h1:
                _got["上部バナー"] = True
            elif _a >= 0 and _ae > _a and _a < _i < _ae:
                _got["本文末"] = True
            elif _f >= 0 and _fe > _f and _f < _i < _fe:
                _got["フッター"] = True
            _i = html.find(_k, _i + 1)
        _lack = [k for k, v in _got.items() if not v]
        if _lack:
            warnings.append(f"{gf}: 免責が三層でない（欠け: {'・'.join(_lack)}）"
                            f" → `python apply_disclaimer.py --apply`")
        # SYNC_FORBIDDEN（guide-new-books.html 等）は登録してはいけない側＝未登録が正しい
        if (sync_known and gf not in sync_files and not gf.startswith(CLOUD_PREFIXES)
                and gf not in cloud_ledger and gf not in SYNC_FORBIDDEN):
            errors.append(f"{gf}: SYNC_FILES に未登録（sync されずライブに出ない）")
        # sitemap.xml は generate_market_news.py が全guideを自動収集して再生成するため、
        # 個別チェック不要（漏れない設計）。ここでは検査しない。
        if f'href="{gf}"' not in guides_html:
            # noindex ページ（重複統合で一覧から外した旧版・ゲート保留中の記事）はカード不要
            if '<meta name="robots" content="noindex' not in html:
                # 🚨 2026-09-17 格上げ: これは「一覧から辿れない」だけの話ではない。
                #    ルートに置かれた記事は**その時点で公開されている**（URLで読め、
                #    build_sitemap_xml が sitemap に載せ、apply_series_nav が前後ナビで繋ぐ）。
                #    カードが無く noindex も無い＝**公開するつもりが無いのに公開状態**。
                #    実例: #097 はコンプラゲートで🚩エスカレ中だったのに finalize 済みの版が
                #    ルートに残り、sitemap に載り、#096/#099 の前後ナビから到達できた。
                #    44件ある warning に埋もれて12日気づかなかったので error にする。
                #    直し方＝公開するなら publish_article.py でカードを作る／
                #    保留するなら noindex を付ける（どちらかに倒す）。
                msg = (f"{gf}: guides.html にカードが無いのに noindex も無い"
                       f"＝**公開するつもりが無いのに公開状態**（sitemap・前後ナビからも辿れる）。"
                       f"公開するなら publish_article.py、保留なら noindex を付ける")
                (errors if _in_git_worktree() else warnings).append(msg)

    # 3. guides.html のリンク切れ（指している guide が実在するか）
    #    ※ guide-weekly-* / guide-auto-* は GitHub 側で自動生成されローカルに無いのが正常 → 除外
    for ref in sorted(set(re.findall(r'href="(guide-[^"]+\.html)"', guides_html))):
        if ref.startswith(("guide-weekly-", "guide-auto-") + CLOUD_PREFIXES):
            continue
        if ref in SYNC_FORBIDDEN:
            continue  # routine管理ページ（guide-new-books.html 等）＝ローカルに無いのが正常
        if not _exists(ref):
            errors.append(f"guides.html のリンク切れ: {ref} が存在しない（autopublish公開記事ならリモートから取り込み＝reconcile）")

    # 4. ナビ10ボタン整合性：nav を持つ生成スクリプト(.py)・静的/手動HTMLが10リンク全部を含むか。
    #    自動生成済みの過去記事(guide-weekly-*/guide-monthly-report-*/guide-auto-*)は出力なので除外。
    #    ナビの正は生成スクリプト側で担保する＝ソースを検査してドリフトを根元で捕まえる。
    # 🆕 2026-08-10: holdings.html（大量保有報告書）を追加＝11ボタン標準
    NAV_LINKS = ["index.html", "political-feed.html", "track-record.html", "calendar.html",
                 "guides.html", "guide-investment-books.html", "holdings.html",
                 "market-health.html", "hot-assets.html", "charts.html", "youtube-summary.html"]
    for src in sorted(glob.glob(os.path.join(SD, "*.py")) + glob.glob(os.path.join(SD, "*.html"))):
        name = os.path.basename(src)
        if name.startswith(("guide-weekly-", "guide-monthly-report-", "guide-auto-") + CLOUD_PREFIXES):
            continue
        # 機械生成HTML出力（index等＝SYNC禁忌・preview）はローカルが陳腐化するので除外。
        # ナビの正は生成スクリプト(.py)側で担保→そちらを検査することで根元のドリフトを捕まえる。
        if name in SYNC_FORBIDDEN or name == "preview.html":
            continue
        # 公開ページでないものを除外（2026-07-26）＝warningが恒久的に消えず、鳴りっぱなしで
        # 他の警告まで見なくなるのを防ぐ。①`_`プレフィックス＝ローカル専用（SYNC禁止と同じ境界）
        # ②`apply_*.py`＝ナビ「断片」を注入する冪等ツールで、自分が10ボタンを持つ理由が無い。
        # 実測(13件中の内訳)＝除外対象は _draft004/_draft005/_preview_health/_pub003/_pub006/
        # apply_books_nav_scripts.py の6件。除外で失う検査は `_gmn_remote.py`/`_guides_remote.html`
        # （リモートのローカル写し＝検査対象として意図されたものではない）だけ。
        if name.startswith("_") or (name.startswith("apply_") and name.endswith(".py")):
            continue
        navhrefs = set(re.findall(r'class="nav-btn[^"]*"\s+href="([^"]+)"', _read(name)))
        if not navhrefs:
            continue  # ナビを持たないファイルは対象外
        missing = [l for l in NAV_LINKS if l not in navhrefs]
        if missing:
            warnings.append(f"{name}: ナビに不足リンク {missing}（10ボタン未満）")

    # 4b. ナビCSSの標準形検査（2026-07-21 新設）：guide-*.html の .nav-bar に max-width が
    #     無いと広い画面でボタンが 8+2 に崩れる（旧クラウドテンプレの自己増殖事故）。
    #     修正は python apply_nav_css.py／公開経路は publish_article.py が自動正規化。
    for src in sorted(glob.glob(os.path.join(SD, "guide-*.html"))):
        name = os.path.basename(src)
        if name in SYNC_FORBIDDEN:
            continue
        h = _read(name)
        m = re.search(r"\.nav-bar\{display:flex[^}]*\}", h)
        if m and "max-width" not in m.group(0):
            warnings.append(f"{name}: ナビCSSに max-width 欠落（8+2崩れ）→ python apply_nav_css.py")

    # 5. 経済カレンダーの日付検査（2026-07-02 新設）
    check_economic_events()

    # 6. 連番シリーズの回番号検査（2026-09-08 新設・#089 上書き公開事故の再発防止）
    check_series_numbering()

    # 7. 米月次指標の欠落・重複検査（2026-09-11 新設・米CPI 日付誤りの再発防止）
    check_us_monthly_indicators()

    # 8. guides.html の欄とカードの対応（2026-09-26 新設・計算ツール欄への紛れ込み47枚の再発防止）
    check_guides_sections(guides_html)

    # 9. 計算ツールがトップの並びにもあるか（2026-09-27 新設・クセ診断がトップに出ていなかった）
    check_tools_strip(guides_html)

    # 10. カードと記事の食い違い・下書きへのリンク（2026-10-04 新設・#115 上書き公開事故の再発防止）
    check_card_dates(guides_html)

    # 出力
    print("🔍 サイト整合性チェック（check_site_consistency.py）")
    sf_disp = (f"{len(sync_files)} 件" if sync_known
               else "ローカル専用のためスキップ（sync_to_github.py がリモートに無い＝正常）")
    print(f"  検査した guide記事: {checked} 件（自動生成記事を除く） / SYNC_FILES: {sf_disp}")
    if warnings and not quiet:
        print(f"\n⚠️  警告 {len(warnings)} 件:")
        for w in warnings:
            print("   -", w)
    if errors:
        print(f"\n❌ エラー {len(errors)} 件（要修正）:")
        for e in errors:
            print("   -", e)
        print("\n結果: ❌ NG（エラーあり。sync 前に修正してください）")
        sys.exit(1)
    else:
        tail = f"・警告 {len(warnings)} 件" if warnings else ""
        print(f"\n結果: ✅ OK（エラーなし{tail}）")
        sys.exit(0)


if __name__ == "__main__":
    main()
