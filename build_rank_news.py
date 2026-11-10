# -*- coding: utf-8 -*-
"""ランキングの各銘柄の下に出す「値動きの原因になりそうなニュース」を集める（hot-assets.html・AI 不使用）。

2026-11-10 オーナー「毎日値上がり率、値下がり率、出来高急増、上場来高値のランキングを表示してもらってると思いますけど、
各それぞれの、なぜこのランキングに表示されるほど値動きをしたのか調べるのを時間を短縮するために、それぞれのランキングの下に
値動きの原因であろうニュースをそれぞれ3つくらいリンクを貼り付けるのでいいので、それと文字も小さくしてもらって表示してください」。

- 対象：`jp-rankings.json` の値上がり率・値下がり率・人気急上昇（出来高急増）の各20銘柄と、`jp-highs.json` の上場来高値
  （記録上の最高値）・上場来安値（記録上の最安値・11/10 夜 オーナー「上場来安値でもお願いします」）のうち売買代金の大きい順に
  それぞれ HIGHS_MAX 銘柄
- 集める（1銘柄 最大3本）：
  ① TDnet の開示（会社の公式発表）のうち、**値動きの時間帯＝2取引日前の 15:00 から、その日の 15:30 まで**に出たもの
     （場中の決算は次の日に大きく動くことがある＝11/9 14:00 の古河電工・KOKUSAI は 11/10 に S高近く・11/6 の TOWA は2日続けて）。
     大事な種類を先に（TOB・不祥事・業績修正・差異・M&A・提携・決算…）、同じなら新しい順・最大2本
  ② Google ニュース（日本語）の検索で、**会社名（短くした名前・TDnet の略称）が見出しに入った記事**（同じ時間帯・
     新しい順・PR TIMES などニュースティッカーと同じ除外）
  ③ まだ足りなければ、その日の引け後（15:30 以降）の TDnet の開示（「引け後」と書く＝次の日の材料）
  株探のその銘柄のニュース一覧へのリンクは描画側（generate_market_news.py）が毎回付ける（ここでは取らない）
- 出す：`jp-rank-news.json`＝{"items": {コード: {"asof": その一覧の日付, "links": [{"t": 見出し, "u": URL, "s": 出どころ, "w": 時刻}],
  "gn": Google ニュースを引けたか}}}。同じ日付で引けたものは次の回で使い回す（jp-rankings と jp-highs の2回走る）

⚠️ 自動で集めた「候補」。値動きの原因とは限らない（ページにもそう書く）。売買の推奨ではない。
⚠️ GitHub 側で生成＝ローカルから push しない（SYNC禁忌）。Google ニュースはクラウドのセッションからは届かない（Actions からは届く）。

実行: python build_rank_news.py            （jp-rankings.yml と jp-highs.yml から）
      python build_rank_news.py --no-gnews  （TDnet だけで試す）
"""
import argparse
import datetime as dt
import email.utils
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

import build_news_ticker as NT
import tdnet_events as T
import tdnet_reaction as TR

JST = dt.timezone(dt.timedelta(hours=9))
OUT = "jp-rank-news.json"
RANKINGS, HIGHS = "jp-rankings.json", "jp-highs.json"
LISTS = (("gainers", "値上がり率"), ("losers", "値下がり率"), ("hot", "人気急上昇"))
HIGHS_MAX = 30
VERSION = 2                  # 選び方を変えたら上げる（同じ日付でも版が違えば引き直す）
MAX_LINKS, MAX_TDNET = 3, 2
OPEN_FROM = "15:00"          # 2取引日前のこの時刻から（15:00 の決算も入る）
BACK = 2                     # 何取引日さかのぼるか
CLOSE = "15:30"
PAUSE_GN = 1.2
TITLE_MAX = 60
UA = {"User-Agent": "Mozilla/5.0 marketwatch-jp/1.0"}
SUFFIX = r"(ホールディングス|ホールディング|グループ|株式会社|\(株\)|コーポレーション|ＨＤ|HD)$"
# 🆕 11/10 夜 Actions の最初の実行で「(株)ジャパンディスプレイ【JPDYY】:株価・株式情報」のような株価のページが混ざった＝外す
QUOTE_PAGE = r"株価・株式情報|株価情報|株価チャート|[:：]\s*株価|掲示板|株価予想|銘柄情報$"
# 金融のニュースを先に（同じ組の中は新しい順）。ほかの発行元（生活・地域の記事など）は空いた枠にだけ入る
FIN_SOURCES = ("株探", "かぶたん", "Yahoo!ファイナンス", "日本経済新聞", "日経", "ロイター", "Reuters", "ブルームバーグ", "Bloomberg",
               "みんかぶ", "MINKABU", "東洋経済", "ダイヤモンド", "時事", "QUICK", "四季報", "フィスコ", "FISCO",
               "トレーダーズ", "モーニングスター", "Moomoo", "moomoo", "日刊工業", "日経クロステック", "ITmedia", "NHK")


# ════════════════════ 名前・時間帯（純関数） ════════════════════

def nfkc(s):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", s or "")).strip()


def aliases(name, short=""):
    """見出しに探す名前（長い順）。正式名・後ろの「ホールディングス」等を外した名前・TDnet の略称（2文字以上）"""
    full = nfkc(name)
    out = [full]
    cut = re.sub(SUFFIX, "", full).strip()
    if len(cut) >= 3 and cut != full:
        out.append(cut)
    s = nfkc(short)
    if len(s) >= 2 and s not in out:
        out.append(s)
    return sorted({a for a in out if a}, key=lambda a: (-len(a), a))     # 長い順（同じ長さは文字の順＝毎回同じ）


def has_alias(title, names):
    t = nfkc(title).lower()
    return any(a.lower() in t for a in names)


def start_day(days, d, back=BACK):
    """d より back 取引日前（取引日の一覧に無ければ None）"""
    p = [x for x in days if x < d]
    return p[-back] if len(p) >= back else (p[0] if p else None)


def in_window(date, hhmm, d, start):
    """値動きの時間帯（start の 15:00 〜 その日 d の 15:30 の前）か。休みの日の開示も入る"""
    lo = (start or d, OPEN_FROM if start else "00:00")
    return lo <= (date, hhmm) < (d, CLOSE)


def after_close(date, hhmm, d):
    return date == d and hhmm >= CLOSE


# ════════════════════ TDnet ════════════════════

def tdnet_rank(title):
    tags = T.tags_of(title)
    r = [TR.TITLE_FIRST.index(t) for t in tags if t in TR.TITLE_FIRST]
    return min(r) if r else len(TR.TITLE_FIRST) + (0 if tags else 1)


def tdnet_index(day_rows):
    """{日付: [一覧の行]} → {コード4桁: [(日付, 時刻, 表題, PDF, 略称)]}"""
    idx = {}
    for d, rows in day_rows.items():
        for r in rows:
            if TR.skip_row(r) or not r.get("code") or re.search(TR.FIX, nfkc(r.get("title"))):
                continue
            idx.setdefault(r["code"][:4], []).append((d, r["time"], r.get("title") or "", r.get("doc") or "", (r.get("name") or "").strip()))
    return idx


def tdnet_links(items, d, start):
    """→ (時間帯の中のリンク（大事な順）, 引け後のリンク)"""
    def link(x, tag=""):
        date, hhmm, title, doc, _ = x
        return {"t": nfkc(title)[:TITLE_MAX], "u": f"{T.BASE}{doc}.pdf" if doc else "", "s": "TDnet" + tag,
                "w": f"{int(date[5:7])}/{int(date[8:10])} {hhmm}"}
    win = [x for x in items if in_window(x[0], x[1], d, start)]
    win.sort(key=lambda x: (x[0], x[1]), reverse=True)                     # 新しい順 → 大事な種類を先に（安定な並べ替え）
    win.sort(key=lambda x: tdnet_rank(x[2]))
    aft = sorted([x for x in items if after_close(x[0], x[1], d)], key=lambda x: (tdnet_rank(x[2]), x[1]))
    return [link(x) for x in win if x[3]], [link(x, "（引け後）") for x in aft if x[3]]


# ════════════════════ Google ニュース ════════════════════

def gn_query(names):
    """短い名前から（記事は「東急不動産HD」「清水建」のように短く書く）最大3つを OR で。直近2日"""
    q = " OR ".join(f'"{a}"' for a in sorted(names, key=len)[:3])
    return NT.gnews(f"{q} when:2d")


def parse_rss(text):
    """Google ニュースの RSS → [{"t", "u", "s", "dt"(JST の datetime)}]。純関数"""
    out = []
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return out
    for it in root.iter("item"):
        title = NT.clean_title(it.findtext("title") or "")
        link = (it.findtext("link") or "").strip()
        src = (it.findtext("source") or "").strip().split(" | ")[0].split(" - ")[0].strip()
        try:
            when = email.utils.parsedate_to_datetime(it.findtext("pubDate") or "").astimezone(JST)
        except (TypeError, ValueError):
            continue
        if title and link.startswith("http"):
            out.append({"t": title, "u": link, "s": src[:20] or "ニュース", "dt": when})
    return out


def gn_links(entries, names, since):
    """見出しに名前が入り、since 以降の記事（金融のニュースを先に・それぞれ新しい順・株価のページは除く・同じ見出しは1本）"""
    seen, out = set(), []
    newest = sorted(entries, key=lambda e: e["dt"], reverse=True)
    for e in sorted(newest, key=lambda e: 0 if any(f in e["s"] for f in FIN_SOURCES) else 1):   # 金融のニュースを先に（安定）
        if (e["dt"] < since or not has_alias(e["t"], names) or NT.is_ng_publisher(e["s"])
                or re.search(QUOTE_PAGE, nfkc(e["t"]))):
            continue
        k = NT.norm(e["t"])
        if k in seen:
            continue
        seen.add(k)
        out.append({"t": nfkc(e["t"])[:TITLE_MAX], "u": e["u"], "s": e["s"], "w": f"{e['dt'].month}/{e['dt'].day} {e['dt']:%H:%M}"})
    return out


def fetch_gn(url, tries=2):
    """→ RSS の文字。断られた（429/503）ときは "BLOCKED"、取れなければ None"""
    for k in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20).read().decode("utf-8", "ignore")
        except urllib.error.HTTPError as e:
            if e.code in (429, 503):
                return "BLOCKED"
        except Exception:  # noqa: BLE001
            pass
        time.sleep(2 * (k + 1))
    return None


# ════════════════════ まとめる ════════════════════

def pick(td_win, gn, td_after):
    """TDnet（時間帯）を最大2本 → ニュース → 足りなければ引け後の TDnet。合わせて最大3本"""
    out = td_win[:MAX_TDNET]
    out += gn[:MAX_LINKS - len(out)]
    out += td_win[MAX_TDNET:MAX_LINKS]                   # ニュースが無ければ TDnet の3本目
    out = out[:MAX_LINKS]
    out += td_after[:MAX_LINKS - len(out)]
    return out[:MAX_LINKS]


def targets(rank, highs):
    """→ {コード: {"name", "asof", "lists"}}（同じ銘柄が2つの一覧にあっても1回だけ引く）"""
    out = {}
    for key, label in LISTS:
        for r in (rank or {}).get(key) or []:
            t = out.setdefault(r["code"], {"name": r.get("name", ""), "asof": rank.get("asof", ""), "lists": []})
            t["lists"].append(label)
    for key, label in (("highs", "上場来高値"), ("lows", "上場来安値")):   # 🆕 11/10 夜 安値も（オーナー「上場来安値でもお願いします」）
        rec = sorted([r for r in (highs or {}).get(key) or [] if r.get("record")], key=lambda r: -(r.get("turnover") or 0))
        for r in rec[:HIGHS_MAX]:
            t = out.setdefault(r["code"], {"name": r.get("name", ""), "asof": highs.get("asof", ""), "lists": []})
            t["lists"].append(label)
            if highs.get("asof", "") > t["asof"]:
                t["asof"] = highs["asof"]
    return out


def load(path, empty=None):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return empty


def build(tg, days, old, day_rows, gn_fetch=None, pause=PAUSE_GN, log=print):
    """→ 出力の dict。gn_fetch(url)→ RSS の文字（None＝Google ニュースを引かない）"""
    idx = tdnet_index(day_rows)
    items, blocked, n_gn = {}, False, 0
    for code, t in tg.items():
        d = t["asof"]
        p = start_day(days, d)
        prev = (old or {}).get("items", {}).get(code)
        if prev and prev.get("asof") == d and prev.get("gn") and prev.get("v") == VERSION:
            items[code] = prev                             # 同じ日付で引けたもの＝使い回す
            continue
        rows = idx.get(code[:4], [])
        short = next((x[4] for x in rows if x[4]), "")
        names = aliases(t["name"], short)
        td_win, td_after = tdnet_links(rows, d, p)
        gn, got = [], False
        if gn_fetch and not blocked:
            time.sleep(pause)
            text = gn_fetch(gn_query(names))
            if text == "BLOCKED":
                blocked = True
                log("  ⚠️ Google ニュースに断られた＝残りは TDnet だけ")
            elif text is not None:
                since = dt.datetime.fromisoformat(f"{p or d}T{OPEN_FROM}").replace(tzinfo=JST)
                gn, got = gn_links(parse_rss(text), names, since), True
                n_gn += 1
        items[code] = {"asof": d, "name": nfkc(t["name"]), "lists": t["lists"], "links": pick(td_win, gn, td_after), "gn": got,
                       "v": VERSION}
    log(f"  ニュース：{len(items)}銘柄（Google ニュースを引いた {n_gn}・リンクあり {sum(1 for v in items.values() if v['links'])}）")
    return {"built": dt.datetime.now(JST).isoformat(timespec="minutes"), "items": items}


def main(argv=None):
    ap = argparse.ArgumentParser(description="ランキングの銘柄の下に出すニュース（TDnet＋Google ニュース・AI 不使用）")
    ap.add_argument("--no-gnews", action="store_true", help="Google ニュースを引かない（TDnet だけ）")
    a = ap.parse_args(argv)
    tg = targets(load(RANKINGS, {}), load(HIGHS, {}))
    if not tg:
        print("  ランキングが無い＝作らない")
        return 0
    days = sorted(TR.daily_map(TR.fetch_chart(TR.TOPIX, "1d", "1mo") or []))
    if not days:
        print("  ⚠️ 1306 の日足が取れない＝取引日が分からないので作らない")
        return 0
    need = set()
    for t in tg.values():
        d, p = t["asof"], start_day(days, t["asof"])
        x = dt.date.fromisoformat(p or d)
        while x.isoformat() <= d:
            if x.weekday() < 5:
                need.add(x.isoformat())
            x += dt.timedelta(days=1)
    day_rows = {}
    for d in sorted(need):
        got = T.fetch_day(dt.date.fromisoformat(d))
        day_rows[d] = got[1] if got else []
        print(f"  TDnet {d}: {len(day_rows[d])}件")
    out = build(tg, days, load(OUT, {}), day_rows, None if a.no_gnews else fetch_gn)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
