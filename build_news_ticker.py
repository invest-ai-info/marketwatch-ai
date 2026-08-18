# -*- coding: utf-8 -*-
"""
build_news_ticker.py — ⚡最新ニュース・ライブフィード生成（AI不使用・決定論・追加コスト0円）
================================================================================
目的: トップページに「常に最新のニュース見出し」を出す軽量レーン。
      既存の update-market-news（1日3回・AI解説つき）とは独立し、
      GitHub Actions `news-ticker.yml` が毎時実行して `news-ticker.json` だけを commit する。
      index.html 側は JavaScript が閲覧時に JSON を fetch して描画＝HTML再生成なしで常に最新。

設計:
  - ソースは日本語優先の RSS / Google News RSS（翻訳不要・無料・キー不要）
  - 選定はスコアリングせず「時刻降順」＝鮮度がすべて（解説つきの選定は既存レーンの役割）
  - センチメント絵文字はキーワード判定（generate_market_news.py の判定と同一語彙・AI不使用）
  - フェイルセーフ: 取得が薄い時（<MIN_ITEMS）は既存 JSON を保持して終了（良品を空で上書きしない）
  - 2026-08-06 拡張: 固定ソースに公的機関（日銀/財務省）とトピック横断検索5本を追加（計18本）。
    トピック検索のバッジはエントリの <source>（実際の発行元）＝媒体名を詐称しない。
    フィード別の最終観測時刻を `feed_health` として JSON に持ち、automation-health §⑦ が
    ソース単位の「静かな停止」を検知する（index.html の JS は d.items / d.updated しか読まない
    ことを実測済み＝キー追加は表示に無影響）。

⚠️ news-ticker.json は GitHub Actions が生成・commit する＝SYNC_FILES に入れない（SYNC禁忌）。
   このスクリプト自体は SYNC 対象。
"""
import json
import os
import re
import sys
import calendar
import datetime
from difflib import SequenceMatcher
from urllib.parse import quote

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "news-ticker.json")
JST = datetime.timezone(datetime.timedelta(hours=9))

MAX_AGE_HOURS = 26      # 「今日＋昨晩」まで。古い記事はティッカーに出さない
PER_SOURCE_CAP = 6      # 1ソース占拠の防止
TOTAL_ITEMS = 24
MIN_ITEMS = 5           # これ未満しか取れない＝ネット/フィード不調とみなし既存JSONを保持
SIM_THRESHOLD = 0.62    # タイトル類似の重複除去

# カテゴリ別の下限枠（2026-08-01 追加）。数字は index.html 側の使われ方から決めている。
#   stocks/fx/commodity/crypto … 4マーケットカード内のミニ見出しが c で絞って .slice(0,3)＝
#       最大3件出し、0件なら枠ごと描画しない。カードに見出しを出すため 3。
#   macro … カードは無いが絞り込みボタンがある（ボタンは常に6個描画される）。空振りを避ける最低限で 2。
#   biz  … 常に潤沢（実測 raw 70件）なので枠不要。残り枠を鮮度順で自然に埋める。
CAT_QUOTA = {"stocks": 3, "fx": 3, "commodity": 3, "crypto": 3, "macro": 2}


def gnews(query):
    """Google News RSS 検索 URL（日本語版）。site: 指定で各社の日本語記事を横断取得できる。"""
    return f"https://news.google.com/rss/search?q={quote(query)}&hl=ja&gl=JP&ceid=JP:ja"


# 各フィードは dict:
#   name        … 表示ソース名（badge_entry=True では取得失敗時のフォールバック表示名）
#   url         … RSS URL（Google News 経由は when:1d で当日限定。直接RSSは MAX_AGE_HOURS でカット）
#   kw          … True なら MARKET_KWS の市場語フィルタを課す（生活記事が混ざる総合メディア用）
#   stale_days  … automation-health §⑦ のソース停止検知の閾値[日]。None=監視しない
#                 （トピック検索は「静か」が正常になり得るため必ず None＝誤検知ゼロ方針）
#   badge_entry … True ならエントリの <source>（実際の発行元）をバッジに使う（トピック検索用）。
#                 8/1 に「話題検索だと媒体名を詐称する」で却下したが、Google News RSS は
#                 エントリ単位で発行元タグを持つ（8/6 実測 30/30 件）＝そこから取れば嘘にならない
#
# ⚠️ 2026-08-01: Bloomberg（gnews("site:bloomberg.co.jp when:1d")）を削除した。
#    Google News が bloomberg.co.jp の**記事を索引していない**＝返るのは株価クオートと固定ページだけ。
#    実測: entries=100 の中身が「80388: 香港取引所 Stock Price Quote」「CNY to USD Exchange Rate」
#    「ブルームバーグ プロフェッショナル サービス」等で、日付の中央値は約90,000時間前（≒10年）。
#    公式RSS も /feeds/rss・/rss・markets.rss の3本とも 0件＝日本語版に公開RSSが無い。
#    毎時1リクエストを捨てていただけでなく、稀に日付だけ新しいクオートページ
#    （実測「PHPMD Quote - Wisdom Tree 貴金属ﾊﾞｽｹｯﾄ上場 Fund」）が見出しとして混入する事故源でもあった。
#    代替も探したが QUICK Money World / ロイター直RSS / JOGMEC は 0件、ダイヤモンドは漫画・育児記事が
#    主体で市場ニュースにならないため、**補充せず削除のみ**とした（残る8ソースで件数は足りている）。
FEEDS = [
    {"name": "ロイター",    "url": gnews("site:jp.reuters.com when:1d"), "kw": False, "stale_days": 7},
    {"name": "日経",        "url": gnews("site:nikkei.com (市場 OR 株 OR 円相場 OR 金利 OR 日銀 OR FRB) when:1d"), "kw": False, "stale_days": 7},
    {"name": "時事通信",    "url": gnews("site:jiji.com (経済 OR 市場 OR 株 OR 円) when:1d"), "kw": False, "stale_days": 7},
    {"name": "株探",        "url": gnews("site:kabutan.jp when:1d"), "kw": False, "stale_days": 7},
    {"name": "みんかぶ",    "url": gnews("site:minkabu.jp when:1d"), "kw": False, "stale_days": 7},
    # ⛔ NHK経済（2026-08-18 削除）＝**NHK側のRSSが停止**。うちの設定ミスではない。
    #    実測: cat5.xml は HTTP 200 を返すが Last-Modified=2026-08-08 / lastBuildDate=2026-08-09 01:15 JST で凍結。
    #    Cache-Control=max-age=60（短命）でキャッシュ由来ではなく、クエリでキャッシュ回避しても同じ内容。
    #    **cat0/cat4/cat5/cat6 の全カテゴリが 8/8 で同時停止**＝経済カテゴリ固有の問題でもない。
    #    移設先も無し（www.nhk.or.jp=301 / news/business/rss.xml=301 / rss/news/business.xml=404）。
    #    → 8/1 Bloomberg と同じ判断で削除。同じ範囲はロイター/日経/時事/Yahoo!経済/東洋経済が既にカバーする。
    {"name": "Yahoo!経済",  "url": "https://news.yahoo.co.jp/rss/topics/business.xml", "kw": False, "stale_days": 7},
    {"name": "東洋経済",    "url": "https://toyokeizai.net/list/feed/rss", "kw": True, "stale_days": 7},  # 特集系が多い→市場語フィルタ
    # 暗号資産専用（2026-08-01 追加）。総合ソースは暗号資産の見出しを1日1件程度しか出さず、
    # 暗号資産カードのミニ見出しが枠(CAT_QUOTA=3)を満たせなかったため専門媒体を2本置いている。
    {"name": "CoinPost",    "url": "https://coinpost.jp/?feed=rss2", "kw": False, "stale_days": 7},
    {"name": "CoinDesk JP", "url": "https://www.coindeskjapan.com/feed/", "kw": False, "stale_days": 7},
    # --- 公的機関（2026-08-06 追加）。発行元固定の一次情報＝報道より先に原文が出る。
    #     8/6 実測プローブ: 日銀 whatsnew=60件/最新9.2h・財務省 news.rss=100件/最新3.2h（国債入札・大臣会見）。
    #     低頻度（週末は沈黙）なので停止閾値は30日。
    # ⚠️ 同日に測って死んでいた候補（再プローブ不要）: 金融庁 fsaRSS.xml=0件／JPX rss/news.xml=0件／
    #     財務省 rss/index.xml=0件／トウシル・マネクリ=RSS実体なし／経産省 atom=最新でも1158h(48日前)＝不適。
    {"name": "日銀",        "url": "https://www.boj.or.jp/rss/whatsnew.xml", "kw": False, "stale_days": 30},
    {"name": "財務省",      "url": "https://www.mof.go.jp/news.rss", "kw": False, "stale_days": 30},
    # 市場系メディア（2026-08-06 追加）。ZUU は車・時計等の生活記事も流れる（8/6 実測「BMW X5…」）→市場語フィルタ必須
    {"name": "ZUU",         "url": "https://zuuonline.com/feed", "kw": True, "stale_days": 7},
    # --- トピック狙い撃ち（2026-08-06 追加・Google News 横断検索）。固定ソース網に無い媒体
    #     （朝日/WSJ/Reuters日本語/外為どっとコム/トレーダーズ・ウェブ等）まで実効カバレッジが広がる。
    #     8/6 実測: 5本とも 26h以内30/30件・発行元タグ30/30件・中央値4.7〜17.8h。
    {"name": "介入",        "url": gnews("為替介入 OR 円買い介入 OR 政府日銀 when:1d"), "kw": False, "stale_days": None, "badge_entry": True},
    {"name": "中銀",        "url": gnews("FOMC OR FRB OR パウエル when:1d"), "kw": False, "stale_days": None, "badge_entry": True},
    {"name": "経済指標",    "url": gnews("雇用統計 OR 消費者物価指数 OR GDP when:1d"), "kw": False, "stale_days": None, "badge_entry": True},
    {"name": "決算修正",    "url": gnews("決算 (上方修正 OR 下方修正) when:1d"), "kw": False, "stale_days": None, "badge_entry": True},
    {"name": "地政学",      "url": gnews("地政学 (原油 OR 市場 OR 円) when:1d"), "kw": False, "stale_days": None, "badge_entry": True},
]

# トピック検索が拾う発行元の除外。①名指しリスト（部分一致）＋②文字体系ルールの二段構え。
# 8/6 実測: Vietnam.vn・BigGo（日本語化された海外アグリゲータ）／PR TIMES（プレスリリース
# ＝企業広報であってニュースでない）／Межа（ウクライナ語圏メディアの日本語化記事）。
# ②は「日本語媒体名に出ない文字体系（キリル/アラビア/タイ文字）」を機械判定＝名指しのモグラ叩きを減らす。
NG_PUBLISHERS = ("Vietnam.vn", "BigGo", "PR TIMES")
_NG_SCRIPT_RE = re.compile(r"[Ѐ-ӿ؀-ۿ฀-๿]")


def is_ng_publisher(badge):
    return bool(_NG_SCRIPT_RE.search(badge)) or any(ng in badge for ng in NG_PUBLISHERS)


def entry_badge(e, feed):
    """表示するソースバッジ。badge_entry のフィードはエントリの <source>（実際の発行元）を使う。
    取れなければフィード名にフォールバック（表示崩れ防止で24字まで）。"""
    if feed.get("badge_entry"):
        src = ((e.get("source") or {}).get("title") or "").strip()
        # セクション付き媒体名（8/6 実測「Investing.com - FX | 株式市場」）は先頭セグメントだけ使う
        src = src.split(" | ")[0].split(" - ")[0].strip()
        if src:
            return src[:24]
    return feed["name"]

# 東洋経済など総合フィード用の「市場関連」キーワード（1つも含まなければ除外）
MARKET_KWS = ("市場", "株", "円", "ドル", "金利", "日銀", "FRB", "FOMC", "為替", "投資",
              "決算", "債券", "原油", "金価格", "インフレ", "景気", "GDP", "関税", "経済",
              "相場")  # 2026-08-06 追加: ZUU の「日々是相場」等が円/株を含まず落ちていた

# センチメント判定（generate_market_news.py の _POS_WORDS/_NEG_WORDS と同一語彙・依存を軽くするため複製）
_POS_WORDS = {
    "surge", "soar", "rally", "gain", "rise", "jump", "record", "high", "bull", "boom",
    "optimis", "recover", "upbeat", "breakout", "profit", "beat", "strong", "best",
    "上昇", "急騰", "高値", "最高", "好調", "回復", "強気", "続伸", "反発", "突破", "増益", "黒字",
}
_NEG_WORDS = {
    "crash", "plunge", "drop", "fall", "slip", "tumble", "low", "bear", "recession",
    "fear", "risk", "warn", "crisis", "collapse", "loss", "miss", "worst", "sell-off",
    "selloff", "concern", "threat", "hack", "exploit", "fraud", "sanction", "war", "attack",
    "下落", "急落", "安値", "最安", "不調", "弱気", "暴落", "続落", "損失", "赤字", "破綻", "懸念",
    "危機", "脅威", "制裁", "攻撃", "流出",
}


def sentiment_emoji(title):
    text = title.lower()
    pos = sum(1 for w in _POS_WORDS if w in text)
    neg = sum(1 for w in _NEG_WORDS if w in text)
    return "😊" if pos > neg else ("😢" if neg > pos else "😐")


# 市場タグ判定（キーワード照合のみ・AI不使用＝コスト0）。上から順に最初に一致したタグ1個。
# 意図: 「どの市場に効くニュースか」をひと目で分かるようにする（index.htmlのバッジ/絞り込み/カード内ミニ一覧が使う）
_CAT_RULES = [
    ("crypto",    ("ビットコイン", "BTC", "イーサリアム", "イーサ", "暗号資産", "仮想通貨", "ステーブルコイン", "アルトコイン", "コインベース")),
    ("commodity", ("原油", "WTI", "ブレント", "OPEC", "金価格", "金相場", "金先物", "ゴールド", "銀価格", "プラチナ", "銅価格", "天然ガス", "LNG", "商品市況", "穀物", "小麦", "レアアース")),
    ("fx",        ("円相場", "ドル円", "円安", "円高", "為替", "介入", "ユーロ円", "ユーロドル", "ポンド", "人民元", "通貨")),
    ("stocks",    ("日経", "TOPIX", "株価", "株式", "ダウ", "ナスダック", "NASDAQ", "S&P", "半導体", "決算", "上場", "KOSPI", "株")),
    ("macro",     ("日銀", "FRB", "FOMC", "ECB", "利上げ", "利下げ", "金利", "雇用統計", "CPI", "GDP", "インフレ", "関税", "景気", "財政", "国債", "経済対策")),
]


# 部分一致ゆえの誤爆を止める除外語（当たったらそのカテゴリとしては数えず、次の規則へ進む）。
# 2026-08-01 実測: commodity の「ゴールド」だけで ゴールドマン・サックス／ゴールドカード／
# ゴールドウイン／ゴールドパートナー まで拾っていた。commodity の枠は3件しかないので、
# 1件の誤爆が本物の金・原油の見出しを1件押し出す＝実害がある。
# 「ゴールド」自体は残す（「ＳＰＤＲゴールドの現物保有高」等、本物の金相場ニュースが使うため）。
_CAT_EXCLUDE = {
    "commodity": ("ゴールドマン", "ゴールドカード", "ゴールドウイン",
                  "ゴールドパートナー", "ゴールデン"),
}


def classify(title):
    for key, kws in _CAT_RULES:
        if any(k in title for k in kws) and not any(x in title for x in _CAT_EXCLUDE.get(key, ())):
            return key
    return "biz"  # その他の経済ニュース


_TAG_RE = re.compile(r"<[^>]+>")


def clean_title(title):
    """末尾の媒体名サフィックスを除去（Google News=『 - 媒体名』・東洋経済=『 | ビジネス | 媒体名』等。
    表示は別途ソースバッジで出す）。末尾セグメントが短い（≤22字）ときだけ媒体名とみなす。"""
    t = _TAG_RE.sub("", title or "").strip()
    for sep in (" - ", " | ", "｜"):
        while sep in t:
            head, tail = t.rsplit(sep, 1)
            if 0 < len(tail) <= 22 and len(head) >= 10:
                t = head.strip()
            else:
                break
    # TBS NEWS DIG 等の見出し末尾に残る飾り（8/6 実測「…フォトギャラリー | TBS…」）
    return re.sub(r"\s*フォトギャラリー$", "", t).strip()


def norm(t):
    return re.sub(r"[\s　、。・…「」【】\[\]()（）!！?？]", "", t).lower()


def fetch_all():
    """全フィードを取得。戻り値: (採用候補items, フィード別の最新エントリ時刻 {name: JST iso})。
    feed_seen は「フィードが記事を出しているか」の生存記録＝鮮度/日本語/市場語フィルタの採否とは
    無関係に、有効な日付を持つ生エントリの最新時刻を記録する（停止検知 §⑦ の材料）。"""
    import feedparser
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    items, feed_seen = [], {}
    for feed in FEEDS:
        source, url = feed["name"], feed["url"]
        try:
            fp = feedparser.parse(url, request_headers={"User-Agent": "Mozilla/5.0 marketwatch-jp/1.0"})
            n = 0
            for e in (fp.entries or [])[:30]:
                title = clean_title(e.get("title", ""))
                link = e.get("link", "") or ""
                tp = e.get("published_parsed") or e.get("updated_parsed")
                if not title or not link.startswith("http") or not tp:
                    continue
                dt = datetime.datetime.fromtimestamp(calendar.timegm(tp), datetime.timezone.utc)
                iso = dt.astimezone(JST).isoformat(timespec="minutes")
                if iso > feed_seen.get(source, ""):
                    feed_seen[source] = iso
                # 日本語読者向けティッカー: 日本語がほぼ無い見出しは銘柄ページ等のゴミ＝除外
                if len(re.findall(r"[ぁ-んァ-ヶ一-龠]", title)) < 3:
                    continue
                age_h = (now_utc - dt).total_seconds() / 3600
                if age_h < -0.5 or age_h > MAX_AGE_HOURS:
                    continue
                if feed["kw"] and not any(k in title for k in MARKET_KWS):
                    continue
                badge = entry_badge(e, feed)
                if is_ng_publisher(badge):
                    continue
                items.append({"t": title, "u": link, "s": badge,
                              "dt": iso, "e": sentiment_emoji(title), "c": classify(title)})
                n += 1
            print(f"  {source:<10} {n}件")
        except Exception as ex:
            print(f"  ⚠️ {source}: 取得エラー {ex}")
    return items, feed_seen


def merge_feed_health(prev, seen, now_iso):
    """フィードごとの観測記録 {name: {"first": 監視開始時刻, "last": 最後に記事を観測した時刻|None}}。
    今回0件/取得エラーのフィードは前回値を保持（消さない）。FEEDS から外れたフィードは落とす。"""
    out = {}
    for feed in FEEDS:
        name = feed["name"]
        rec = dict(prev.get(name) or {"first": now_iso, "last": None})
        newest = seen.get(name)
        if newest and (not rec.get("last") or newest > rec["last"]):
            rec["last"] = newest
        out[name] = rec
    return out


def dedup_and_cap(items):
    """重複・1ソース占拠・カテゴリ偏りを抑えつつ TOTAL_ITEMS 件を選ぶ（全体は時刻降順）。

    ⚠️ 2026-08-01: カテゴリ別の下限枠を追加。
       それ以前は時刻降順に TOTAL_ITEMS まで取って break するだけだったため、
       件数の多い biz が枠を食い尽くし、commodity と crypto が **常に0件** になっていた。
       実測（2026-08-01 19時台）: 取得 raw=166 → commodity 5件・crypto 1件が取れているのに採用0件。
       index.html の4カード内ミニ見出しは c で絞って最大3件出し 0件なら枠ごと描画しないため、
       コモディティと暗号資産のカードだけ見出しが出ないまま放置されていた。
       対策＝QUOTA_CATS を先に確保してから残りを鮮度順で埋める。
    """
    items.sort(key=lambda x: x["dt"], reverse=True)
    out, seen_norms, per_source, used = [], [], {}, set()

    def take(idx):
        """重複・1ソース上限を検査して採用。可否によらず「処理済み」として記録する
        （どちらの棄却理由も後から緩むことはないので再検査は不要）。"""
        it = items[idx]
        used.add(idx)
        nt = norm(it["t"])
        if not nt:
            return False
        if any(SequenceMatcher(None, nt, s).ratio() >= SIM_THRESHOLD for s in seen_norms):
            return False
        if per_source.get(it["s"], 0) >= PER_SOURCE_CAP:
            return False
        out.append(it)
        seen_norms.append(nt)
        per_source[it["s"]] = per_source.get(it["s"], 0) + 1
        return True

    # ① 枠取り。取れる件数が少ないカテゴリから先に確保する
    #    （後回しにすると 1ソース上限を他カテゴリに先に食われて取り逃す）
    avail = {c: sum(1 for it in items if it["c"] == c) for c in CAT_QUOTA}
    for cat in sorted(CAT_QUOTA, key=lambda c: avail[c]):
        got = 0
        for idx, it in enumerate(items):
            if got >= CAT_QUOTA[cat] or len(out) >= TOTAL_ITEMS:
                break
            if idx not in used and it["c"] == cat and take(idx):
                got += 1

    # ② 残り枠は純粋に鮮度順で埋める
    for idx in range(len(items)):
        if len(out) >= TOTAL_ITEMS:
            break
        if idx not in used:
            take(idx)

    out.sort(key=lambda x: x["dt"], reverse=True)  # 枠取りで崩れた並びを鮮度順へ戻す
    return out


def main():
    now_jst = datetime.datetime.now(JST)
    print(f"[news-ticker] {now_jst:%Y-%m-%d %H:%M JST} フィード{len(FEEDS)}本を取得…")
    try:
        with open(OUT, encoding="utf-8") as f:
            prev = json.load(f)
    except Exception:
        prev = {}
    raw, feed_seen = fetch_all()
    fresh = dedup_and_cap(raw)
    if len(fresh) < MIN_ITEMS:
        print(f"[keep] 取得 {len(fresh)}件 < {MIN_ITEMS}＝フィード不調とみなし既存 news-ticker.json を保持")
        return
    payload = {"updated": now_jst.isoformat(timespec="minutes"), "items": fresh,
               "feed_health": merge_feed_health(prev.get("feed_health") or {}, feed_seen,
                                                now_jst.isoformat(timespec="minutes"))}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=0)
    print(f"[ok] {len(fresh)}件 → news-ticker.json（最新: {fresh[0]['dt']} / {fresh[0]['t'][:40]}）")


if __name__ == "__main__":
    main()
