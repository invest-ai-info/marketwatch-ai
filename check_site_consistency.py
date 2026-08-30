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
    "political-feed.html", "political-feed.json",
    "youtube-summary.html", "youtube-summary-data.json",
    "fundamental-context.json", "weekly-levels.json", "weekly-zone-plan.md",
    "article-ideas.md", "daily-preview.md", "political-digest.md",
    "compliance-scan.md", "weekly-strategy-context.json",
    "signal-lab-tracker.json",  # 前向きトラッカー状態（routineがGitHub側でupdate/commit。SEEDはsignal_lab_tracker.py内）
    "signals-log-backtest.json",  # 日足リプレイ出力（ローカル/週次再生成の派生データ・大容量。ローカルpush禁止）
    "jp-rankings.json",  # 値上がり/値下がりランキング（jp-rankings.yml が GitHub 側で毎朝生成・コミット。ローカルpush禁止）
    "jp-margin.json",  # 信用残ウォッチ（jp-rankings.yml が build_jp_margin.py で生成・コミット。ローカルpush禁止）
    "news-ticker.json",  # ⚡最新ニュース・ライブフィード（news-ticker.yml が毎時GitHub側で生成・コミット。ローカルpush禁止）
    "market-health-history.json",  # 市場健康度の日次履歴（update-market-news.yml が GitHub側で生成・コミット。ローカルpush禁止）
    "touraku-history.json",  # 騰落レシオの日次履歴（update-market-news.yml が GitHub側で生成・コミット。ローカルpush禁止）
    "edinet-holdings.json",  # 大量保有報告書の新着（edinet-holdings.yml が平日GitHub側で生成・コミット。ローカルpush禁止）
    "guide-new-books.html",  # 投資本新刊ウォッチ（routine book-watch-weekly が毎週土曜GitHub側で更新。ローカルpush禁止）
    "idea-inbox.md",  # 研究アイデア受信箱 drafts/idea-inbox.md（routine idea-scout-weekly が毎週日曜GitHub側で追記。照合はbasename）
    # 🆕 2026-07-07 進化ループのローカル専用ファイル（非公開研究＝公開リポへ流出させない）
    "DOCTRINE.md", "hypothesis_queue.md", "_doctrine_check.py", "_hypothesis_registry.json",
    # 🆕 2026-07-31 アーカイブ2種（basename でも止める＝research/ プレフィックス無しで
    # 書かれた場合の保険。ディレクトリ規則は上の検査1の research/ 分岐が担う）
    "DOCTRINE_ARCHIVE.md", "hypothesis_queue_archive.md",
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
    CLOUD_PREFIXES = ("guide-news-", "guide-signal-lab-", "guide-proverb-")
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
        if sync_known and gf not in sync_files and not gf.startswith(CLOUD_PREFIXES):
            errors.append(f"{gf}: SYNC_FILES に未登録（sync されずライブに出ない）")
        # sitemap.xml は generate_market_news.py が全guideを自動収集して再生成するため、
        # 個別チェック不要（漏れない設計）。ここでは検査しない。
        if f'href="{gf}"' not in guides_html:
            # noindex ページ（重複統合などで意図的に一覧から外した旧版）はカード不要
            if '<meta name="robots" content="noindex' not in html:
                warnings.append(f"{gf}: guides.html にカードが無い（一覧から辿れない）")

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
