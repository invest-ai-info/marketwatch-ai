# -*- coding: utf-8 -*-
"""
check_guide_draft.py — guide記事 自動公開の決定論ゲート（2026-07-05 新設）
============================================================================
autodraft 下書きを無人公開する routine `autodraft-publish` が、公開直前の
最終HTML（noindex除去済み）に対して実行する。exit 0=GREEN（公開可）/ 1=RED（公開せず
REVIEW.md に🚩エスカレ）。

⚠️ このスクリプトは固定ゲート。routine/エージェントは編集禁止。
   実行前に `git checkout` で確定版に戻すこと（signal_lab_verify.py と同じ扱い）。

検査項目:
  1. noindex/nofollow が残っていない（下書きの検索除外タグの消し忘れ）
  2. kinsho-v1 免責（data-disclaimer="kinsho-v1"）がある
  3. ナビ10ボタンが全て揃っている
  4. 未完成マーカー（TODO(SVG) 等）が残っていない
  5. 禁止表現（売買推奨の断定）が無い — 最小限のハードNGのみ。表現ニュアンスはOpus担当
  6. SVG検査 = signal_lab_verify.py（固定オラクル）の bounds/text-overlap を流用
     過検出しても RED→人間レビューに回るだけ＝安全側
  7. スラッグ重複検査 — 既存 guide-*.html とトークン集合が同一/包含なら RED
     （2026-07-06 追加。実例: bonds-interest-rates vs interest-rates-bonds=語順違い、
      simple-vs-compound vs simple-vs-compound-interest=部分一致 の2本が重複公開された。
      キュー選定の完全一致スキップをすり抜ける「似スラッグの同一主題」を機械で止める）

usage: python check_guide_draft.py <guide-xxx.html>
"""
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

NAV_LINKS = ["index.html", "political-feed.html", "track-record.html", "calendar.html",
             "guides.html", "guide-investment-books.html", "market-health.html",
             "hot-assets.html", "charts.html", "youtube-summary.html"]

# ハードNG＝文脈に関係なく公開不可（個別の売買推奨・利益断定）。
# 「必ず儲かる」等は詐欺解説記事が引用として使うため Opus の文脈判断に委ねる（ここでは止めない）。
BANNED_HARD = ["買い推奨", "売り推奨", "購入を推奨", "エントリー推奨", "買うべきです", "売るべきです"]

TODO_MARKERS = ["TODO(SVG)", "TODO（SVG）", "<!-- TODO"]


def slug_tokens(filename):
    """guide-xxx-yyy.html → {'xxx','yyy'}（日付・番号だけのトークンは除く）"""
    base = os.path.basename(filename)
    m = re.match(r"(?:guide-|draft-)?(.+?)\.html$", base)
    if not m:
        return set()
    return {t for t in m.group(1).split("-") if t and not t.isdigit()}


def slug_duplicate_check(path):
    """既存 guide-*.html とスラッグのトークン集合が同一 or 包含関係なら重複疑いを返す。
    完全一致スラッグはキュー選定側でスキップされるため、ここは「似て非なるスラッグ」担当。"""
    fails = []
    mine = slug_tokens(path)
    if not mine:
        return fails
    my_base = os.path.basename(path)
    # 日付つき速報(news)・連番シリーズ(signal-lab等)は毎回似るので対象外
    if re.search(r"\d{4}-\d{2}", my_base) or "signal-lab" in my_base or "proverb" in my_base:
        return fails
    import glob
    for g in glob.glob(os.path.join(ROOT, "guide-*.html")):
        gb = os.path.basename(g)
        if gb == my_base or gb == my_base.replace("draft-", "guide-"):
            continue
        theirs = slug_tokens(g)
        if not theirs or re.search(r"\d{4}-\d{2}", gb):
            continue
        if mine == theirs or (len(mine & theirs) >= 2 and (mine <= theirs or theirs <= mine)):
            fails.append(f"スラッグ重複疑い: {gb} と主題が重なる可能性（トークン {sorted(mine & theirs)} 共通）")
    return fails


def main():
    if len(sys.argv) < 2:
        print("usage: python check_guide_draft.py <guide-xxx.html>")
        return 2
    path = sys.argv[1] if os.path.isabs(sys.argv[1]) else os.path.join(ROOT, sys.argv[1])
    html = open(path, encoding="utf-8-sig").read()
    fails = []

    # 1. noindex 消し忘れ
    if re.search(r'<meta[^>]*name="robots"[^>]*noindex', html, re.I):
        fails.append("noindex メタタグが残っている（下書きタグの消し忘れ）")

    # 2. 免責
    if 'data-disclaimer="kinsho-v1"' not in html:
        fails.append("kinsho-v1 免責が無い")

    # 3. ナビ10ボタン
    missing = [l for l in NAV_LINKS if l not in html]
    if missing:
        fails.append(f"ナビに不足リンク: {missing}")

    # 4. 未完成マーカー
    for mk in TODO_MARKERS:
        if mk in html:
            fails.append(f"未完成マーカーが残っている: {mk}")
            break

    # 5. 禁止表現（ハードNGのみ）
    for w in BANNED_HARD:
        if w in html:
            fails.append(f"禁止表現: 「{w}」")

    # 7. スラッグ重複（似スラッグの同一主題＝重複コンテンツ防止）
    fails.extend(slug_duplicate_check(path))

    # 6. SVG検査（固定オラクルの関数を流用＝判定基準の単一ソース化）
    try:
        import signal_lab_verify as slv
        for w in slv.svg_bounds_check(html):
            fails.append(f"SVG: {w}")
        for w in slv.text_overlap_check(html):
            fails.append(f"SVG: {w}")
    except Exception as e:
        fails.append(f"SVG検査を実行できない ({type(e).__name__}: {str(e)[:60]})")

    name = os.path.basename(path)
    if fails:
        print(f"=== check_guide_draft: {name} → RED ({len(fails)}件) ===")
        for f in fails:
            print(f"  ❌ {f}")
        print("→ 公開しない。drafts/REVIEW.md に🚩要人間レビューで記録すること。")
        return 1
    print(f"=== check_guide_draft: {name} → GREEN（決定論ゲート通過） ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
