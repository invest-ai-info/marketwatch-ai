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
    - 9ボタンナビがあるか（warning）
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
    "market-health.html", "hot-assets.html",
    "signals-log.json", "signals-log.csv", "track-record.html",
    "political-feed.html", "political-feed.json",
    "youtube-summary.html", "youtube-summary-data.json",
    "fundamental-context.json", "weekly-levels.json", "weekly-zone-plan.md",
    "article-ideas.md", "daily-preview.md", "political-digest.md",
    "compliance-scan.md", "weekly-strategy-context.json",
}

errors = []
warnings = []


def _read(p):
    with open(os.path.join(SD, p), encoding="utf-8") as f:
        return f.read()


def _exists(p):
    return os.path.exists(os.path.join(SD, p))


def get_sync_files():
    """sync_to_github.py の SYNC_FILES を正規表現で抽出（importせず安全に）。
    sync_to_github.py はローカル専用（GitHub 未追跡）なので、リモート(routine)実行時は不在。
    その場合は None を返し、呼び出し側で SYNC_FILES 系チェックをスキップする（偽陽性防止）。"""
    if not _exists("sync_to_github.py"):
        return None
    s = _read("sync_to_github.py")
    m = re.search(r"SYNC_FILES\s*=\s*\[(.*?)\n\]", s, re.S)
    if not m:
        warnings.append("sync_to_github.py の SYNC_FILES ブロックを解析できない → SYNC_FILESチェックをスキップ")
        return None
    return set(re.findall(r'"([^"]+)"', m.group(1)))


def main():
    quiet = "--quiet" in sys.argv
    sync_files = get_sync_files()
    sync_known = sync_files is not None  # sync_to_github.py を読めた = ローカル実行

    # 1. 🚨 SYNC禁忌チェック（最重要：巻き戻し事故防止。push直前のローカル実行でのみ意味がある）
    if sync_known:
        for f in sorted(sync_files):
            base = os.path.basename(f)
            if base in SYNC_FORBIDDEN or re.match(r"technical-alerts-history.*\.json$", base):
                errors.append(f"🚨 SYNC禁忌ファイルが SYNC_FILES に混入: {f}（ローカルpushで巻き戻し事故の恐れ）")

    # 2. 各 guide-*.html（週次/自動生成を除く）の整合性
    guides_html = _read("guides.html") if _exists("guides.html") else ""
    sitemap = _read("sitemap.xml") if _exists("sitemap.xml") else ""
    guide_files = sorted(os.path.basename(p) for p in glob.glob(os.path.join(SD, "guide-*.html")))
    # 自動生成記事（テンプレは generate_*.py 側で管理。個別の登録チェック対象外）
    AUTO_PREFIXES = ("guide-weekly-", "guide-auto-", "guide-monthly-report-")
    checked = 0
    for gf in guide_files:
        if gf.startswith(AUTO_PREFIXES):
            continue
        checked += 1
        html = _read(gf)
        if 'data-disclaimer="kinsho-v1"' not in html:
            errors.append(f"{gf}: kinsho-v1 免責が無い")
        nav = html.count('class="nav-btn')
        if nav < 9:
            warnings.append(f"{gf}: nav-btn が {nav} 個（9ボタン想定）")
        if sync_known and gf not in sync_files:
            errors.append(f"{gf}: SYNC_FILES に未登録（sync されずライブに出ない）")
        if gf not in sitemap:
            warnings.append(f"{gf}: sitemap.xml に未登録")
        if f'href="{gf}"' not in guides_html:
            warnings.append(f"{gf}: guides.html にカードが無い（一覧から辿れない）")

    # 3. guides.html のリンク切れ（指している guide が実在するか）
    #    ※ guide-weekly-* / guide-auto-* は GitHub 側で自動生成されローカルに無いのが正常 → 除外
    for ref in sorted(set(re.findall(r'href="(guide-[^"]+\.html)"', guides_html))):
        if ref.startswith("guide-weekly-") or ref.startswith("guide-auto-"):
            continue
        if not _exists(ref):
            errors.append(f"guides.html のリンク切れ: {ref} が存在しない")

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
