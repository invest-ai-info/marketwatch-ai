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
  6. SVG検査 = signal_lab_verify.py（固定オラクル）の bounds/text-overlap/occlusion/band-parallel を流用
     過検出しても RED→人間レビューに回るだけ＝安全側
  7. スラッグ重複検査 — 既存 guide-*.html とトークン集合が同一/包含なら RED
     （2026-07-06 追加。実例: bonds-interest-rates vs interest-rates-bonds=語順違い、
      simple-vs-compound vs simple-vs-compound-interest=部分一致 の2本が重複公開された。
      キュー選定の完全一致スキップをすり抜ける「似スラッグの同一主題」を機械で止める）
  8. 内部リンク実在検査 — サイト内リンク/画像の参照先が実ファイルとして存在するか
     （2026-07-30 追加。Search Console の「見つかりませんでした(404)」を追跡したら、
      自動公開レーンの記事6件が実在しない記事へリンクしていた＝4件はハルシネーション
      [guide-boj-policy.html 等]、2件はパス取り違え[guide-contact.html＝正しくは contact.html]。
      LLM は「あるはずの関連記事」を書けてしまうので、実在確認は機械側でしか担保できない）

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

# 内部リンク実在検査の対象拡張子（ディレクトリURL等は対象外＝拡張子で判別する）
LINK_EXT = (".html", ".htm", ".xml", ".json", ".txt", ".js", ".css",
            ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp", ".pdf")

# ⚠️ クラウド側(cron/routine)が生成する公開ページ＝SYNC禁忌ゆえローカルには存在しないことがある。
#   本番には必ず存在するので実在チェックから除外する。これを入れないと、
#   ナビ10ボタンが全記事から political-feed.html / youtube-summary.html を参照しているため
#   **全記事がゲートに引っかかって自動公開レーンが全停止する**（2026-07-30 実測: 217/217件）。
#   正は CLAUDE.md「SYNC_FILES の禁忌」節。
CLOUD_GENERATED = {
    "index.html", "calendar.html", "charts.html", "vix.html",
    "market-health.html", "hot-assets.html",
    "political-feed.html", "youtube-summary.html", "track-record.html",
    "guide-new-books.html", "sitemap.xml", "news-ticker.json",
}


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


def internal_link_check(html, path):
    """サイト内リンク・画像の参照先が実ファイルとして存在するかを検査する。

    存在しない先を指していると Google が 404 として拾い、その記事が
    インデックスされないだけでなく「リンク切れのあるサイト」になる。
    LLM は関連記事を"あるものとして"書けてしまうため、実在確認は機械側の責務。
    ⚠️ 相対パスはサイトがフラット構成である前提で basename 相当に正規化する。
    """
    fails = []
    me = os.path.basename(path)
    # 下書き draft-xxx.html は公開時に guide-xxx.html になるので自己参照は正常
    selves = {me, me.replace("draft-", "guide-"), me.replace("guide-", "draft-")}
    seen = set()
    for m in re.finditer(r'(?:href|src)="([^"]+)"', html):
        u = m.group(1).strip()
        if u.startswith(("http://", "https://", "//", "mailto:", "tel:", "#",
                         "javascript:", "data:")):
            continue
        p = u.split("#")[0].split("?")[0].lstrip("./").lstrip("/")
        if not p or not p.lower().endswith(LINK_EXT) or p in seen or p in selves:
            continue
        if p in CLOUD_GENERATED:      # クラウド生成＝ローカル不在でも本番には在る
            continue
        seen.add(p)
        if not os.path.exists(os.path.join(ROOT, p)):
            fails.append(f"リンク先が実在しない: {p}（404になる）")
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

    # 8. 内部リンク実在（存在しない記事へのリンク＝Search Console の404の正体）
    fails.extend(internal_link_check(html, path))

    # 6. SVG検査（固定オラクルの関数を流用＝判定基準の単一ソース化）
    try:
        import signal_lab_verify as slv
        for w in slv.svg_bounds_check(html):
            fails.append(f"SVG: {w}")
        for w in slv.text_overlap_check(html):
            fails.append(f"SVG: {w}")
        # 2026-07-29 追加。text_overlap は text 同士しか見ないので「不透明図形に隠れる」を、
        # bounds は座標しか見ないので「BBが平行＝σに連動しない」を、それぞれ素通りしていた。
        for w in slv.text_occlusion_check(html):
            fails.append(f"SVG: {w}")
        for w in slv.band_parallel_check(html):
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
