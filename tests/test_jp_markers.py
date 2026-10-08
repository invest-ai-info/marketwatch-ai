# -*- coding: utf-8 -*-
"""朝の準備用「寄りで買わない」目印の一覧（jp_markers.py）のテスト。2026-10-08 新設。

値動きはすべて作り物。確かめること＝①倍率と前の日比の計算（研究の landmine_lab.prev_more と同じ数字）②C・B候補の判定と
1億円以上だけを残すこと・件数は全部を数えること ③メールの節（平日だけ・古い一覧・無い一覧・★）④朝の指標メールと
夕方の jp-highs.json の作り方に繋がっていること ⑤〔貸借〕の印（2026-10-08 夕方・一覧が無い／古い一覧の形でも壊れない）
⑥貸借銘柄の一覧を読む部品 jp_taishaku（J36 と同じ読み方・取れなければ None）。

実行:  python tests/test_jp_markers.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import jp_markers as M  # noqa: E402


def _bars(n=30, close=1000.0, vol=1e5, last_vol=None, last_close=None):
    d0 = dt.date(2026, 8, 3)
    out = [((d0 + dt.timedelta(days=i)).isoformat(), close * 1.01, close * 0.99, close, vol) for i in range(n - 1)]
    lc = last_close or close
    out.append(((d0 + dt.timedelta(days=n - 1)).isoformat(), lc * 1.01, lc * 0.99, lc, last_vol or vol))
    return out


def test_values_match_the_research_formula():
    import numpy as np
    import landmine_lab as LM
    bars = _bars(last_vol=6e5, last_close=1060.0)
    tv, ratio, ret = M.stock_values(bars)
    assert abs(tv - 1060 * 6e5 / 1e8) < 1e-9 and abs(ret - 0.06) < 1e-12
    lm_rows = [(d, c, h, lo, c, v) for d, h, lo, c, v in bars]          # landmine_lab の日足の形（日付・始値・高値・安値・終値・出来高）
    assert abs(LM.prev_more(lm_rows)[0][-1] - ratio) < 1e-9 and abs(ratio - 6.36) < 1e-9
    assert M.stock_values(_bars(n=20))[1] is None and M.stock_values(_bars(n=1)) is None
    assert np.isclose(M.stock_values(_bars(n=21, last_vol=5e5))[1], 5.0)
    assert (M.TV_HIGH, M.UP, M.TV_DAYS) == (5.0, 0.05, 20)


def test_rules_text_matches():
    text = open("MY_TRADING_RULES.md", encoding="utf-8").read()
    assert "**C：前の日の売買代金が、その前の20営業日の平均の5倍以上 → 寄りでは買わない**" in text
    assert "**B：前の日に +5% 以上上げて、さらに今朝もその銘柄だけ +1% 以上高く寄る → 寄りでは買わない" in text


def test_compute_flags_and_filter():
    daily = {"1111": _bars(last_vol=8e5),                                  # C（8倍・8億円）
             "2222": _bars(last_close=1070.0),                             # B候補（+7%・1.07億円）
             "3333": _bars(last_vol=9e5, last_close=1100.0),               # 両方
             "4444": _bars(vol=1e4, last_vol=8e4),                         # C だが 0.8億円＝数えるが残さない
             "5555": _bars()}                                              # どちらでもない
    stocks = {c: {"name": f"会社{c}"} for c in daily}
    mk = M.compute(daily, stocks, "2026-09-01")
    assert (mk["n_c"], mk["n_b"], mk["universe"], mk["with_ratio"]) == (3, 2, 5, 5)
    codes = [r["code"] for r in mk["rows"]]
    assert codes == ["3333", "1111", "2222"] and mk["rows"][0]["c"] and mk["rows"][0]["b"] and mk["rows"][0]["name"] == "会社3333"


def test_section():
    mk = M.compute({"1111": _bars(last_vol=8e5), "3333": _bars(last_vol=9e5, last_close=1100.0)},
                   {"1111": {"name": "甲"}, "3333": {"name": "乙"}}, "2026-10-07")
    s = "\n".join(M.section(mk, dt.date(2026, 10, 8)))
    assert "2026-10-07 の引けで判定" in s and "🚫 C" in s and "B候補" in s and "★C・B候補の両方" in s and "乙" in s
    assert "空売りの合図ではない" in s and "A はどの銘柄でも" in s
    assert M.section(mk, dt.date(2026, 10, 10)) == []                                   # 土曜は出さない
    assert "今朝は使わない" in "\n".join(M.section(mk, dt.date(2026, 10, 14)))            # 7日前の一覧
    assert "今朝は使わない" in "\n".join(M.section(mk, dt.date(2026, 10, 7)))             # 同じ日（朝に夕方の一覧はありえない）
    assert "一覧を作れていない" in "\n".join(M.section(None, dt.date(2026, 10, 8)))
    assert "（なし）" in "\n".join(M.section(dict(mk, rows=[]), dt.date(2026, 10, 8)))
    many = dict(mk, rows=[dict(mk["rows"][0], code=str(1000 + i)) for i in range(30)])
    assert "…ほか 5銘柄" in "\n".join(M.section(many, dt.date(2026, 10, 8)))


def test_wired_into_digest_and_jp_highs():
    import send_indicator_digest as D
    mk = M.compute({"1111": _bars(last_vol=8e5)}, {"1111": {"name": "甲"}}, "2026-10-07")
    orig = D.load_markers
    try:
        D.load_markers = lambda: mk
        _, body = D.build(dt.datetime(2026, 10, 8, 6, 20, tzinfo=D.JST))
    finally:
        D.load_markers = orig
    assert "寄りで買わない目印" in body and "1111 甲" in body and "投資助言ではありません" in body
    src = open("build_jp_highs.py", encoding="utf-8").read()
    assert "import jp_markers" in src and '"markers": jp_markers.compute(' in src and "if sane_today(b)" in src


def test_taishaku_tag():
    daily = {"1111": _bars(last_vol=8e5), "3333": _bars(last_vol=9e5, last_close=1100.0)}
    stocks = {"1111": {"name": "甲"}, "3333": {"name": "乙"}}
    mk = M.compute(daily, stocks, "2026-10-07", {"codes": {"3333", "9999"}, "asof": "2026年10月1日現在", "n": 2})
    tai = {r["code"]: r["tai"] for r in mk["rows"]}
    assert tai == {"1111": False, "3333": True} and mk["taishaku"] == {"asof": "2026年10月1日現在", "n": 2}
    s = "\n".join(M.section(mk, dt.date(2026, 10, 8)))
    assert "乙  売買代金" in s and s.count("〔貸借〕") == 1 + 2              # 説明の1行＋C と B候補の両方に出る乙
    assert "制度信用で空売りできる銘柄（日本取引所グループの一覧 2026年10月1日現在・2銘柄）" in s and "空売りの決まりではない" in s
    no = M.compute(daily, stocks, "2026-10-07", None)                       # 一覧が取れなかった
    assert no["taishaku"] is None and all(r["tai"] is None for r in no["rows"])
    s2 = "\n".join(M.section(no, dt.date(2026, 10, 8)))
    assert "〔貸借〕の印は今回なし" in s2 and "〔貸借〕＝" not in s2
    old = {k: v for k, v in no.items() if k != "taishaku"}                   # 10/8 夕方より前の形＝何も書かない
    assert "〔貸借〕" not in "\n".join(M.section(old, dt.date(2026, 10, 8)))
    src = open("build_jp_highs.py", encoding="utf-8").read()
    assert "import jp_taishaku" in src and "jp_taishaku.load_or_none()" in src


def test_jp_taishaku_reader():
    import io
    import pandas as pd
    import jp_taishaku as JT
    import taishaku_lab as K
    assert K.parse_list is JT.parse_list and K.MIN_LIST == JT.MIN_LIST == 1000      # J36 と同じ読み方
    html = '<a href="/listing/others/margin/x.xlsx">一覧</a>'
    rows = [["2026年10月1日現在", None, None, None], ["銘柄コード", "銘柄名", "市場区分/商品区分", "信用区分"]]
    rows += [[str(1300 + i), f"会社{i}", "プライム", "貸借銘柄" if i < 1200 else "制度信用銘柄"] for i in range(1500)]
    try:
        buf = io.BytesIO()
        pd.DataFrame(rows).to_excel(buf, header=False, index=False)
    except ImportError:                                                         # openpyxl が無い手元では Excel の往復は省く
        buf = None
    got = []

    def get(url):
        got.append(url)
        return html.encode() if url == JT.PAGES[0] else buf.getvalue()
    if buf is not None:
        codes, asof, counts = JT.load(get)
        assert len(codes) == 1200 and asof == "2026年10月1日現在" and counts["制度信用銘柄"] == 300
        assert got == [JT.PAGES[0], "https://www.jpx.co.jp/listing/others/margin/x.xlsx"]
        out = JT.load_or_none(get)
        assert out["n"] == 1200 and "1300" in out["codes"] and out["asof"] == "2026年10月1日現在"
        small = io.BytesIO()
        pd.DataFrame(rows[:500]).to_excel(small, header=False, index=False)
        assert JT.load_or_none(lambda u: html.encode() if u == JT.PAGES[0] else small.getvalue()) is None   # 1,000 未満
    assert JT.load_or_none(lambda u: b"<html></html>") is None                 # Excel のリンクが無い

    def boom(u):
        raise OSError("つながらない")
    assert JT.load_or_none(boom) is None


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
