# -*- coding: utf-8 -*-
"""ランキングの銘柄の下のニュース（build_rank_news.py と generate_market_news._rank_news_row）のテスト。2026-11-10 新設。

一覧・RSS・値段はすべて作り物。確かめること＝①探す名前（ホールディングス等を外す・TDnet の略称・短すぎる名前は使わない）
②時間帯（2取引日前の 15:00 〜 その日の 15:30・休みの日・引け後）③TDnet の並び（大事な種類 → 新しい順・訂正と ETF を除く）
④RSS の読み取りと絞り込み（社名が見出しに入る・時間帯・除外する発行元・同じ見出しは1本）⑤3本の選び方 ⑥使い回し・
Google ニュースに断られたとき ⑦描画（日付が違えば出さない・文字を逃がす・株探の一覧）⑧ワークフロー・SYNC 禁忌。

実行:  python tests/test_build_rank_news.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import sys
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import build_rank_news as B  # noqa: E402

DAYS = ["2026-11-05", "2026-11-06", "2026-11-09", "2026-11-10"]

RSS = """<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>
<item><title>古河電工が急伸、上期の大幅増益と通期上方修正を好感 - 株探</title><link>https://news.google.com/rss/articles/a1</link>
<pubDate>Tue, 10 Nov 2026 00:30:00 GMT</pubDate><source url="https://kabutan.jp">株探</source></item>
<item><title>古河電工が急伸、上期の大幅増益と通期上方修正を好感 - Yahoo!ファイナンス</title><link>https://news.google.com/rss/articles/a2</link>
<pubDate>Tue, 10 Nov 2026 00:40:00 GMT</pubDate><source url="https://finance.yahoo.co.jp">Yahoo!ファイナンス</source></item>
<item><title>電線株がそろって高い 古河電工など - 日本経済新聞</title><link>https://news.google.com/rss/articles/a3</link>
<pubDate>Tue, 10 Nov 2026 02:00:00 GMT</pubDate><source url="https://www.nikkei.com">日本経済新聞</source></item>
<item><title>別の会社のニュース - 株探</title><link>https://news.google.com/rss/articles/a4</link>
<pubDate>Tue, 10 Nov 2026 03:00:00 GMT</pubDate><source url="https://kabutan.jp">株探</source></item>
<item><title>古河電工 新製品のお知らせ - PR TIMES</title><link>https://news.google.com/rss/articles/a5</link>
<pubDate>Tue, 10 Nov 2026 03:10:00 GMT</pubDate><source url="https://prtimes.jp">PR TIMES</source></item>
<item><title>古河電工 地域のイベントに出展 - ウォーカープラス</title><link>https://news.google.com/rss/articles/a7</link>
<pubDate>Tue, 10 Nov 2026 05:00:00 GMT</pubDate><source url="https://walkerplus.com">ウォーカープラス</source></item>
<item><title>古河電気工業(株)【5801】:株価・株式情報 - Yahoo!ファイナンス</title><link>https://news.google.com/rss/articles/a8</link>
<pubDate>Tue, 10 Nov 2026 06:00:00 GMT</pubDate><source url="https://finance.yahoo.co.jp">Yahoo!ファイナンス</source></item>
<item><title>古河電工の古い記事 - 株探</title><link>https://news.google.com/rss/articles/a6</link>
<pubDate>Wed, 04 Nov 2026 03:10:00 GMT</pubDate><source url="https://kabutan.jp">株探</source></item>
</channel></rss>"""


def test_aliases():
    assert B.aliases("東急不動産ホールディングス", "東急不HD") == ["東急不動産ホールディングス", "東急不HD", "東急不動産"]
    assert B.aliases("ＳＧホールディングス", "SGHD") == ["SGホールディングス", "SGHD"]          # 「SG」は短すぎる
    assert B.aliases("日本たばこ産業", "ＪＴ") == ["日本たばこ産業", "JT"]
    assert B.has_alias("ＪＴ、ロシア事業の続報", ["日本たばこ産業", "JT"])
    q = urllib.parse.unquote(B.gn_query(B.aliases("東急不動産ホールディングス", "東急不HD")))
    assert '"東急不HD" OR "東急不動産" OR "東急不動産ホールディングス" when:2d' in q


def test_window():
    s = B.start_day(DAYS, "2026-11-10")
    assert s == "2026-11-06"                                    # 2取引日前（11/7・11/8 は週末）
    assert B.in_window("2026-11-06", "15:00", "2026-11-10", s)
    assert not B.in_window("2026-11-06", "14:59", "2026-11-10", s)
    assert B.in_window("2026-11-07", "10:00", "2026-11-10", s)  # 休みの日の開示
    assert B.in_window("2026-11-09", "14:00", "2026-11-10", s)  # 場中の決算（次の日に大きく動く）
    assert B.in_window("2026-11-10", "15:29", "2026-11-10", s)
    assert not B.in_window("2026-11-10", "15:30", "2026-11-10", s)
    assert B.after_close("2026-11-10", "15:30", "2026-11-10")
    assert B.start_day(["2026-11-10"], "2026-11-10") is None and B.in_window("2026-11-10", "09:00", "2026-11-10", None)


def _r(tm, code, title, doc, name="古河電工"):
    return {"time": tm, "code": code, "name": name, "title": title, "doc": doc}


def test_tdnet_order():
    day_rows = {
        "2026-11-09": [_r("14:00", "58010", "2027年3月期第2四半期決算短信〔日本基準〕(連結)", "d1"),
                       _r("14:00", "58010", "通期連結業績予想の修正に関するお知らせ", "d2"),
                       _r("16:00", "58010", "（訂正）決算短信の一部訂正", "d3"),
                       _r("15:30", "13060", "ETF 日々の開示事項", "e1", "TOPIX ETF")],
        "2026-11-10": [_r("15:30", "58010", "自己株式の取得状況に関するお知らせ", "d4")],
    }
    idx = B.tdnet_index(day_rows)
    assert set(idx) == {"5801"}
    win, aft = B.tdnet_links(idx["5801"], "2026-11-10", "2026-11-06")
    assert [w["t"] for w in win] == ["通期連結業績予想の修正に関するお知らせ", "2027年3月期第2四半期決算短信〔日本基準〕(連結)"]
    assert win[0]["u"].endswith("d2.pdf") and win[0]["s"] == "TDnet" and win[0]["w"] == "11/9 14:00"
    assert len(aft) == 1 and aft[0]["s"] == "TDnet（引け後）"


def test_rss_and_filter():
    es = B.parse_rss(RSS)
    assert len(es) == 8 and es[0]["t"] == "古河電工が急伸、上期の大幅増益と通期上方修正を好感" and es[0]["s"] == "株探"
    since = dt.datetime(2026, 11, 6, 15, 0, tzinfo=B.JST)
    got = B.gn_links(es, B.aliases("古河電気工業", "古河電工"), since)
    ts = [g["t"] for g in got]
    # 金融のニュースを先に（それぞれ新しい順）・株価のページは除く・同じ見出しは1本・生活の記事はあと
    assert ts == ["電線株がそろって高い 古河電工など", "古河電工が急伸、上期の大幅増益と通期上方修正を好感",
                  "古河電工 地域のイベントに出展"], ts
    assert got[0]["w"] == "11/10 11:00"                       # JST
    assert B.parse_rss("<<壊れた>>") == []


def test_pick():
    td = [{"t": f"td{i}"} for i in range(3)]
    gn = [{"t": f"gn{i}"} for i in range(3)]
    af = [{"t": "after"}]
    assert [x["t"] for x in B.pick(td, gn, af)] == ["td0", "td1", "gn0"]
    assert [x["t"] for x in B.pick(td, [], af)] == ["td0", "td1", "td2"]
    assert [x["t"] for x in B.pick([], gn, af)] == ["gn0", "gn1", "gn2"]
    assert [x["t"] for x in B.pick(td[:1], [], af)] == ["td0", "after"]


def test_targets_and_build():
    rank = {"asof": "2026-11-10", "gainers": [{"code": "5801", "name": "古河電気工業"}], "losers": [],
            "hot": [{"code": "5801", "name": "古河電気工業"}, {"code": "2914", "name": "日本たばこ産業"}]}
    highs = {"asof": "2026-11-10", "highs": [{"code": "6532", "name": "ベイカレント", "record": True, "turnover": 240},
                                             {"code": "9999", "name": "年初来だけ", "record": False, "turnover": 999}]}
    tg = B.targets(rank, highs)
    assert set(tg) == {"5801", "2914", "6532"} and tg["5801"]["lists"] == ["値上がり率", "人気急上昇"]
    day_rows = {"2026-11-09": [_r("14:00", "58010", "通期連結業績予想の修正に関するお知らせ", "d2")]}
    calls = []

    def fetch(url):
        calls.append(url)
        return RSS
    out = B.build(tg, DAYS, {}, day_rows, fetch, pause=0, log=lambda *_: None)
    v = out["items"]["5801"]
    assert v["gn"] and v["asof"] == "2026-11-10" and len(v["links"]) == 3 and v["links"][0]["s"] == "TDnet"
    assert len(calls) == 3
    # 同じ日付で引けたものは使い回す（もう引かない）
    calls.clear()
    out2 = B.build(tg, DAYS, out, day_rows, fetch, pause=0, log=lambda *_: None)
    assert calls == [] and out2["items"]["5801"] == v
    # 選び方の版が違えば、同じ日付でも引き直す
    old = {"items": {k: dict(x, v=B.VERSION - 1) for k, x in out["items"].items()}}
    calls.clear()
    B.build(tg, DAYS, old, day_rows, fetch, pause=0, log=lambda *_: None)
    assert len(calls) == 3
    # 断られたら残りは TDnet だけ（gn=False＝次の回にもう一度）
    out3 = B.build(tg, DAYS, {}, day_rows, lambda u: "BLOCKED", pause=0, log=lambda *_: None)
    assert all(not x["gn"] for x in out3["items"].values()) and out3["items"]["5801"]["links"][0]["s"] == "TDnet"


def test_render_row():
    try:
        import generate_market_news as G
    except ImportError:                                      # ランキングの Actions には描画の部品が無い＝描画のテストは飛ばす
        print("  （generate_market_news を読めない環境＝描画のテストは飛ばす）")
        return
    news = {"5801": {"asof": "2026-11-10", "links": [
        {"t": "業績予想の<修正>", "u": "https://www.release.tdnet.info/inbs/d2.pdf", "s": "TDnet", "w": "11/9 14:00"},
        {"t": "古河電工が急伸", "u": "https://news.google.com/rss/articles/a1", "s": "株探", "w": "11/10 09:30"},
        {"t": "悪いURL", "u": "javascript:alert(1)", "s": "x", "w": ""}]}}
    row = G._rank_news_row(news, "5801", "2026-11-10", 5)
    assert 'colspan="4"' in row and "📄" in row and "📰" in row and "&lt;修正&gt;" in row
    assert "javascript:" not in row and 'rel="noopener nofollow"' in row
    assert "https://kabutan.jp/stock/news?code=5801" in row
    assert G._rank_news_row(news, "5801", "2026-11-11", 5) == ""                 # 一覧の日付と違えば出さない
    empty = G._rank_news_row({"1111": {"asof": "2026-11-10", "links": []}}, "1111", "2026-11-10", 6)
    assert "見つかりませんでした" in empty and "kabutan" in empty
    assert G._with_news("<tr><td>a</td></tr>", "<tr class=x></tr>").startswith('<tr class="jpr-hasnews">')
    assert G._with_news("<tr><td>a</td></tr>", "") == "<tr><td>a</td></tr>"


def test_wiring():
    for wf in ("jp-rankings.yml", "jp-highs.yml"):
        s = open(f".github/workflows/{wf}", encoding="utf-8").read()
        assert "python tests/test_build_rank_news.py && python build_rank_news.py" in s, wf
        assert "git add jp-rank-news.json" in s, wf
    import check_site_consistency as C
    assert "jp-rank-news.json" in C.SYNC_FORBIDDEN


if __name__ == "__main__":
    n = 0
    for k, f in list(globals().items()):
        if k.startswith("test_") and callable(f):
            f()
            n += 1
    print(f"✅ {n} 件 OK")
