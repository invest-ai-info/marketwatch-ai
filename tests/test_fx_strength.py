# -*- coding: utf-8 -*-
"""朝のメールの通貨の強弱（fx_strength.py）と、通貨・中国と豪州のニュースの節（morning_brief.fx_section／asia_section）のテスト。
2026-10-08 夜 新設（オーナー「FXの強弱…オージー…中国やオーストラリアのニュース…前日のファンダでどの通貨が弱い／強い傾向」）。

値動きはすべて作り物。確かめること＝①サイトの通貨強弱（generate_technical_alerts.calc_currency_strength）と同じ式・同じペア
②24本前・120本前の変動率 ③取れないときは None・一時ファイルの古さ ④メールの節（平日だけ・豪ドルの行・AIの見立て・今日の豪州と中国の指標・
欄がまだ無いとき）⑤中国・豪州のニュースは重要度→新しい順 ⑥朝のメールのワークフローと本体に繋がっていること（失敗してもメールは送る）。

実行:  python tests/test_fx_strength.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import asia_news as AN  # noqa: E402
import fx_strength as FX  # noqa: E402
import morning_brief as B  # noqa: E402

JST = dt.timezone(dt.timedelta(hours=9))


def test_same_formula_and_pairs_as_the_site():
    import generate_technical_alerts as G
    assert FX.PAIRS == G.FX_PAIR_MAP and FX.EDGE == 0.05
    fake = {"USDJPY=X": 0.5, "EURJPY=X": 0.2, "GBPJPY=X": -0.1, "AUDJPY=X": 0.9, "EURUSD=X": -0.3,
            "GBPUSD=X": -0.6, "AUDUSD=X": 0.4, "EURAUD=X": -0.7, "GBPAUD=X": -1.0}
    orig = G.calc_pair_change_24h
    try:
        G.calc_pair_change_24h = lambda t, period="3d": fake[t]
        assert G.calc_currency_strength() == FX.strength(fake)
    finally:
        G.calc_pair_change_24h = orig


def test_change_back_and_compute():
    closes = [100.0 + i for i in range(130)]
    assert FX.change(closes, 24) == round((229 - 206) / 206 * 100, 3)          # 最新と24本前（サイトの iloc[-24]）
    assert FX.change(closes, 120) == round((229 - 110) / 110 * 100, 3) and FX.change(closes[:20], 24) is None
    d = FX.compute(lambda t: [100.0] * 119 + [101.0] if t == "AUDJPY=X" else [100.0] * 130)
    assert d["pairs"]["AUDJPY=X"]["h24"] == 1.0 and d["pairs"]["AUDJPY=X"]["d5"] == 1.0 and d["h24"]["AUD"] > 0 > d["h24"]["JPY"]
    assert FX.compute(lambda t: []) is None
    assert FX.label(0.05) == "強い" and FX.label(-0.05) == "弱い" and FX.label(0.04) == "中立"
    assert FX.ranking({"USD": 0.4, "JPY": -0.3, "AUD": None}) == "米ドル +0.40%（強い） ＞ 円 -0.30%（弱い）"


def test_temp_file_age():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "fx.json")
        json.dump({"generated_at": "2026-10-09T06:10+09:00", "h24": {}}, open(p, "w"))
        assert FX.load(p, dt.datetime(2026, 10, 9, 6, 20, tzinfo=JST)) is not None
        assert FX.load(p, dt.datetime(2026, 10, 9, 10, 20, tzinfo=JST)) is None          # 3時間より古い
        assert FX.load(os.path.join(d, "none.json")) is None
    assert ".fx-strength.json" in open(".gitignore", encoding="utf-8").read()


FX_D = {"h24": {"USD": 0.42, "EUR": -0.1, "GBP": 0.0, "JPY": -0.3, "AUD": 0.2},
        "d5": {"USD": 1.1, "EUR": -0.5, "GBP": -0.2, "JPY": -0.8, "AUD": 0.3},
        "pairs": {"AUDJPY=X": {"h24": 0.31, "d5": 1.2}, "AUDUSD=X": {"h24": -0.12, "d5": None}}}
FC = {"generated_at": "2026-10-09T06:15:00+09:00",
      "currencies": [{"code": "USD", "lean": "STRONG", "conviction": "MID", "reason": "FOMC がタカ派"},
                     {"code": "AUD", "lean": "WEAK", "conviction": "LOW", "reason": "中国の景気の弱さ"},
                     {"code": "CNY", "lean": "WEAK", "conviction": "MID", "reason": "人民元安の容認"}],
      "asia_watch": [{"headline": "古い高", "published": "2026-10-07", "region": "CN", "materiality": "high", "source": "Reuters", "why": "鉄鉱石"},
                     {"headline": "新しい高", "published": "2026-10-08", "region": "AU", "materiality": "high", "source": "RBA"},
                     {"headline": "中くらい", "published": "2026-10-08", "region": "CN", "materiality": "mid", "source": "Bloomberg"}]}


def test_fx_section():
    ev = [(dt.datetime(2026, 10, 9, 10, 30, tzinfo=JST), {"name": "豪 雇用統計", "country": "AU"}),
          (dt.datetime(2026, 10, 9, 21, 30, tzinfo=JST), {"name": "米 CPI", "country": "US"})]
    s = "\n".join(B.fx_section(FX_D, FC, ev, dt.date(2026, 10, 9)))
    assert "米ドル +0.42%（強い） ＞ 豪ドル +0.20%（強い） ＞ ポンド +0.00%（中立）" in s and "約5日（傾向）：米ドル +1.10%" in s
    assert "豪ドル：豪ドル円 +0.31%（24時間）・+1.20%（約5日）／豪ドル米ドル -0.12%（24時間）・—（約5日）" in s
    assert "・米ドル 強い（中）：FOMC がタカ派" in s and "・人民元 弱い（中）" in s and "今日の豪州・中国の指標：10:30 豪 雇用統計" in s
    assert "米 CPI" not in s and "当たり外れをまだ記録していない" in s
    t = "\n".join(B.fx_section(None, {}, [], dt.date(2026, 10, 9)))
    assert "値動きの強弱を取れなかった" in t and "予約 fundamental-briefing の指示に通貨の欄を足すと" in t and "今日の豪州・中国の指標：なし" in t
    res = {"results": [{"event_date": "2026-10-08", "name": "米9月CPI", "country": "us", "headline": "予想を上回る",
                        "market_reaction": "ドル買い"},
                       {"event_date": "2026-10-01", "name": "古い", "country": "us", "headline": "x"}]}
    u = "\n".join(B.fx_section(FX_D, FC, [], dt.date(2026, 10, 9), res))
    assert "🇺🇸 米9月CPI（10-08）：予想を上回る" in u and "→ ドル買い" in u and "古い" not in u
    assert [r["name"] for r in B.recent_results(res, dt.date(2026, 10, 12))] == []          # 月曜の前の平日は金曜 10/9
    assert B.fx_section(FX_D, FC, ev, dt.date(2026, 10, 10)) == []


def test_asia_section_order_and_missing():
    s = B.asia_section(FC, dt.date(2026, 10, 9))
    heads = [x for x in s if "[重要度" in x]
    assert "新しい高" in heads[0] and "古い高" in heads[1] and "中くらい" in heads[2] and "🇦🇺" in heads[0] and "→ 鉄鉱石" in "\n".join(s)
    assert "AI が選んだもの：今朝は特になし" in "\n".join(B.asia_section(dict(FC, asia_watch=[]), dt.date(2026, 10, 9)))
    t = "\n".join(B.asia_section({"generated_at": "x"}, dt.date(2026, 10, 9)))
    assert "AI が選んだもの：まだ無い" in t and "機械で拾った見出し：取れなかった" in t
    news = {"items": [{"t": "豪ドル上昇", "s": "ロイター", "dt": "2026-10-09T05:10+09:00", "r": "AU"}]}
    t = "\n".join(B.asia_section(FC, dt.date(2026, 10, 9), news))
    assert "🇦🇺 10-09 05:10 豪ドル上昇（ロイター）" in t and "重要度の判断はしていない" in t
    assert "直近30時間になし" in "\n".join(B.asia_section(FC, dt.date(2026, 10, 9), {"items": []}))
    assert B.asia_section(FC, dt.date(2026, 10, 11)) == []


def test_wired_into_digest_and_workflow():
    import send_indicator_digest as D
    wf = open(".github/workflows/indicator-digest.yml", encoding="utf-8").read()
    assert "run: python fx_strength.py" in wf and "run: python asia_news.py" in wf and wf.count("continue-on-error: true") >= 2
    assert wf.index("python fx_strength.py") < wf.index("python asia_news.py") < wf.index("python send_indicator_digest.py")
    orig, orig_load = D.load_fx, FX.load
    try:
        D.load_fx = lambda: FX_D
        _, body = D.build(dt.datetime(2026, 10, 9, 6, 20, tzinfo=D.JST))
        D.load_fx = orig
        FX.load = lambda *a, **k: 1 / 0                                   # 一時ファイルの読み込みが壊れても
        assert D.load_fx() is None
        _, body2 = D.build(dt.datetime(2026, 10, 9, 6, 20, tzinfo=D.JST))  # 朝のメールは届く
    finally:
        D.load_fx, FX.load = orig, orig_load
    assert "通貨の強弱" in body and "米ドル +0.42%" in body and "中国・オーストラリアのニュース" in body
    assert body.index("今日のファンダ") < body.index("通貨の強弱") < body.index("中国・オーストラリア") < body.index("決算発表")
    assert "値動きの強弱を取れなかった" in body2 and "投資助言ではありません" in body2
    pv = open(".github/workflows/morning-mail-preview.yml", encoding="utf-8").read()
    assert "--dry-run" in pv and "GMAIL" not in pv and "python fx_strength.py" in pv and "python asia_news.py" in pv


RSS = """<?xml version="1.0"?><rss><channel>
<item><title>豪ドルが上昇、RBA の発言で - ロイター</title><link>https://x/1</link><pubDate>Thu, 08 Oct 2026 20:00:00 GMT</pubDate><source>ロイター</source></item>
<item><title>豪ドルが上昇、RBA の発言で - 日経</title><link>https://x/2</link><pubDate>Thu, 08 Oct 2026 19:00:00 GMT</pubDate><source>日経</source></item>
<item><title>中国の9月の輸出が予想を下回る</title><link>https://x/3</link><pubDate>Thu, 08 Oct 2026 10:00:00 GMT</pubDate><source>Bloomberg</source></item>
<item><title>古い人民元のニュース記事です</title><link>https://x/4</link><pubDate>Mon, 05 Oct 2026 10:00:00 GMT</pubDate><source>共同</source></item>
<item><title>English only headline</title><link>https://x/5</link><pubDate>Thu, 08 Oct 2026 20:00:00 GMT</pubDate><source>X</source></item>
<item><title>欧州為替：ドル・円はじり高、米金利高で</title><link>https://x/6</link><pubDate>Thu, 08 Oct 2026 20:00:00 GMT</pubDate><source>47NEWS</source></item>
<item><title>上海総合の指数情報・推移</title><link>https://x/7</link><pubDate>Thu, 08 Oct 2026 20:00:00 GMT</pubDate><source>Yahoo!ファイナンス</source></item>
<item><title>豪ドルが上昇、RBA の発言で 執筆： Fisco - Investing.com - FX</title><link>https://x/8</link><pubDate>Thu, 08 Oct 2026 18:00:00 GMT</pubDate><source>Investing.com</source></item>
</channel></rss>"""


def test_asia_news_parse_and_pick():
    now = dt.datetime(2026, 10, 8, 21, 0, tzinfo=dt.timezone.utc)
    xs = AN.parse(RSS, "CN", now)
    assert [x["t"] for x in xs][:3] == ["豪ドルが上昇、RBA の発言で", "豪ドルが上昇、RBA の発言で", "中国の9月の輸出が予想を下回る"]
    assert len(xs) == 4 and not any("ドル・円" in x["t"] or "指数情報" in x["t"] for x in xs)   # 豪州・中国の言葉が無い見出し・相場のページは拾わない
    assert xs[0]["r"] == "AU" and xs[2]["r"] == "CN" and xs[0]["dt"] == "2026-10-09T05:00+09:00" and xs[0]["s"] == "ロイター"
    assert [x["s"] for x in AN.pick(xs)] == ["ロイター", "Bloomberg"]                  # 似た見出しは1つ（末尾が違う同じ記事も）・新しい順
    assert AN.parse("<rss>壊れた", "CN", now) == []
    d = AN.collect(lambda q: RSS, now)
    assert len(d["items"]) == 2 and d["errors"] == 0 and AN.collect(lambda q: 1 / 0, now) == {"items": [], "errors": 3}
    assert ".asia-news.json" in open(".gitignore", encoding="utf-8").read()


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"✅ {name}")
            except AssertionError as e:
                fails += 1
                print(f"❌ {name}: {e}")
    sys.exit(1 if fails else 0)
