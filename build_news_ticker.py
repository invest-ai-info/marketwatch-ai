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


# (表示ソース名, URL, 市場キーワードフィルタを課すか)
# Google News 経由は when:1d で当日分に限定。直接RSSは MAX_AGE_HOURS でカット。
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
    ("ロイター",     gnews("site:jp.reuters.com when:1d"), False),
    ("日経",         gnews("site:nikkei.com (市場 OR 株 OR 円相場 OR 金利 OR 日銀 OR FRB) when:1d"), False),
    ("時事通信",     gnews("site:jiji.com (経済 OR 市場 OR 株 OR 円) when:1d"), False),
    ("株探",         gnews("site:kabutan.jp when:1d"), False),
    ("みんかぶ",     gnews("site:minkabu.jp when:1d"), False),
    ("NHK経済",      "https://www3.nhk.or.jp/rss/news/cat5.xml", False),
    ("Yahoo!経済",   "https://news.yahoo.co.jp/rss/topics/business.xml", False),
    ("東洋経済",     "https://toyokeizai.net/list/feed/rss", True),  # 特集系が多い→市場語フィルタ
    # 暗号資産専用（2026-08-01 追加）。上の8ソースは暗号資産の見出しを1日1件程度しか出さず、
    # 暗号資産カードのミニ見出しが枠(CAT_QUOTA=3)を満たせなかったため専門媒体を2本足した。
    # どちらも発行元が固定＝ソースバッジが嘘にならない（話題検索だと媒体名を詐称することになる）。
    ("CoinPost",     "https://coinpost.jp/?feed=rss2", False),
    ("CoinDesk JP",  "https://www.coindeskjapan.com/feed/", False),
]

# 東洋経済など総合フィード用の「市場関連」キーワード（1つも含まなければ除外）
MARKET_KWS = ("市場", "株", "円", "ドル", "金利", "日銀", "FRB", "FOMC", "為替", "投資",
              "決算", "債券", "原油", "金価格", "インフレ", "景気", "GDP", "関税", "経済")

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
    return t


def norm(t):
    return re.sub(r"[\s　、。・…「」【】\[\]()（）!！?？]", "", t).lower()


def fetch_all():
    import feedparser
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    items = []
    for source, url, kw_filter in FEEDS:
        try:
            feed = feedparser.parse(url, request_headers={"User-Agent": "Mozilla/5.0 marketwatch-jp/1.0"})
            n = 0
            for e in (feed.entries or [])[:30]:
                title = clean_title(e.get("title", ""))
                link = e.get("link", "") or ""
                tp = e.get("published_parsed") or e.get("updated_parsed")
                if not title or not link.startswith("http") or not tp:
                    continue
                # 日本語読者向けティッカー: 日本語がほぼ無い見出しは銘柄ページ等のゴミ＝除外
                if len(re.findall(r"[ぁ-んァ-ヶ一-龠]", title)) < 3:
                    continue
                dt = datetime.datetime.fromtimestamp(calendar.timegm(tp), datetime.timezone.utc)
                age_h = (now_utc - dt).total_seconds() / 3600
                if age_h < -0.5 or age_h > MAX_AGE_HOURS:
                    continue
                if kw_filter and not any(k in title for k in MARKET_KWS):
                    continue
                items.append({"t": title, "u": link, "s": source,
                              "dt": dt.astimezone(JST).isoformat(timespec="minutes"),
                              "e": sentiment_emoji(title), "c": classify(title)})
                n += 1
            print(f"  {source:<10} {n}件")
        except Exception as ex:
            print(f"  ⚠️ {source}: 取得エラー {ex}")
    return items


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
    fresh = dedup_and_cap(fetch_all())
    if len(fresh) < MIN_ITEMS:
        print(f"[keep] 取得 {len(fresh)}件 < {MIN_ITEMS}＝フィード不調とみなし既存 news-ticker.json を保持")
        return
    payload = {"updated": now_jst.isoformat(timespec="minutes"), "items": fresh}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=0)
    print(f"[ok] {len(fresh)}件 → news-ticker.json（最新: {fresh[0]['dt']} / {fresh[0]['t'][:40]}）")


if __name__ == "__main__":
    main()
