# -*- coding: utf-8 -*-
"""朝のメール用「強すぎる株＝買わない側」（jp_momentum.py）・地雷の印（jp_markers）・今日のファンダと決算（morning_brief.py）のテスト。
2026-10-08 夜 新設。

値動きはすべて作り物。確かめること＝①12−1 の値が研究の momentum_lab と同じ ②上場からの長さ（37か月）で外す・上位10・確かめる数の上限
③今朝使う一覧の選び方（月の最初の取引日の朝＝asof の一覧・月の途中＝month_end の一覧・古ければ警告）④メールの節（平日だけ・目印の印）
⑤地雷の印（J21 と同じ数字・主戦場だけ）⑥今日のファンダ・決算・研究の要約の節 ⑦朝の指標メールと夕方の jp-highs に繋がっていること。

実行:  python tests/test_jp_momentum.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))
os.chdir(ROOT)
import jp_markers as JM  # noqa: E402
import jp_momentum as J  # noqa: E402
import momentum_lab as M  # noqa: E402
import morning_brief as B  # noqa: E402
import test_momentum_lab as TL  # noqa: E402


def _jp_bars(series):
    """momentum_lab の形（日, [始, 高, 安, 終, 出来高]）→ build_jp_highs の形［(日付, 高値, 安値, 終値, 出来高)］"""
    out = {}
    for code, (days, vals) in series.items():
        out[code] = [(dt.date.fromordinal(int(d)).isoformat(), float(v[1]), float(v[2]), float(v[3]), float(v[4]))
                     for d, v in zip(days, vals)]
    return out


def test_constants_match_the_research():
    assert (J.TV_MIN, J.MIN_BARS, J.LOOK, J.AGE_MONTHS, J.END_WINDOW, J.MIN_CAL, J.MAX_GAP_DAYS, J.TOP) == \
           (M.TV_MIN, M.MIN_BARS, M.LOOK, M.HIST, M.END_WINDOW, M.MIN_CAL, M.MAX_GAP_DAYS, 10)
    import build_jp_highs as H
    assert J.MAX_JUMP == H.MAX_JUMP
    text = open("momentum-lab.md", encoding="utf-8").read()
    assert "| 最近（2010年〜）（2010-01〜2026-08） | 200 |" in text and "| -1.45％ |" in text   # メールに写した根拠の数字
    assert "−2.79〜−0.11" in J.EVIDENCE and "J42F" in J.EVIDENCE


def test_signal_equals_momentum_lab():
    series, sectors, cal = TL._series(y1=1997)
    T = M.panel(series, sectors, *M.month_table(cal))
    jb = _jp_bars(series)
    table = J.month_table(jb)
    sms = {c: J.stock_months(b, table) for c, b in jb.items()}
    j = [i for i, m in enumerate(T["M"]) if "%04d-%02d" % M.id_ym(m) == "1996-06"][0]
    codes = sorted(series)
    mom = T["p_end"][:, j - 1] / T["p_end"][:, j - 12] - 1
    n = 0
    for i, c in enumerate(codes):
        s = J.signal(sms[c], "1996-06")
        ok = T["has_last"][i, j] and T["nb"][i, j] >= 10 and T["tv"][i, j] >= 1.0
        if s is None:
            assert not ok or not np.isfinite(mom[i])
            continue
        n += 1
        assert ok and abs(s - mom[i]) < 1e-6
    assert n >= 100


def test_bad_day_is_bridged_like_the_lab():
    bars = [("2026-01-05", 101, 99, 100, 1e6), ("2026-01-06", 102, 100, 101, 1e6), ("2026-01-07", 51, 50, 50.5, 1e6),
            ("2026-01-08", 52, 50, 51, 1e6), ("2026-01-09", 52, 50, 51, 0)]
    table = {"2026-01": ("2026-01-05", "2026-01-08", "2026-01-05")}
    sm = J.stock_months(bars, table)
    p, has_last, tv, nb = sm["2026-01"]
    assert abs(p - 1.01 * 51 / 50.5) < 1e-12 and has_last and nb == 4          # 分割の取りこぼしは値動き0・出来高0の日は無いもの


def test_build_list_age_top_and_cap():
    series, sectors, cal = TL._series(y1=1997)
    jb = _jp_bars(series)
    table = J.month_table(jb)
    sms = {c: J.stock_months(b, table) for c, b in jb.items()}
    stocks = {c: {"name": f"会社{c}"} for c in jb}
    young = set(sorted(jb)[:60])
    asked = []

    def age(c):
        asked.append(c)
        return "1995-01" if c in young else "1990-01"
    x = J.build_list(sms, stocks, "1996-06", table, age)
    sig = {c: J.signal(sms[c], "1996-06") for c in jb}
    want = [c for c in sorted((c for c in sig if sig[c] is not None), key=lambda c: (-sig[c], c)) if c not in young][:10]
    assert [r["code"] for r in x["rows"]] == want and x["date"] == table["1996-06"][1] and x["rows"][0]["name"].startswith("会社")
    assert all(r["code"] not in young for r in x["rows"]) and len(asked) <= J.MAX_CHECK
    none = J.build_list(sms, stocks, "1996-06", table, lambda c: None)
    assert none["rows"] == [] and none["age_unknown"] == J.MAX_CHECK
    mom = J.compute({c: b for c, b in jb.items() if b[-1][0] >= "1996-06-28" and b}, stocks, "1996-06-28",
                    lambda c: [("1990-01-01",)])
    assert mom["lists"]["asof"]["ym"] == "1996-06" and mom["lists"]["month_end"]["ym"] == "1996-05"


def _mom():
    rows = [{"code": "7777", "name": "強", "ret12": 3.5, "tv": 12.3}, {"code": "8888", "name": "次", "ret12": 2.0, "tv": 5.0}]
    return {"asof": "2026-10-30", "lists": {"asof": {"ym": "2026-10", "date": "2026-10-30", "universe": 1100, "rows": rows},
                                            "month_end": {"ym": "2026-09", "date": "2026-09-30", "universe": 1090, "rows": rows[:1]}}}


def test_pick_and_section():
    mom = _mom()
    assert J.pick(mom, dt.date(2026, 11, 2))["ym"] == "2026-10"          # 月の最初の取引日の朝＝前の夕方の一覧
    assert J.pick(mom, dt.date(2026, 10, 30))["ym"] == "2026-09"         # 月の途中＝前の月末の一覧
    assert J.pick(mom, dt.date(2026, 12, 1)) is None and J.pick(None, dt.date(2026, 10, 9)) is None
    markers = {"rows": [{"code": "7777", "c": True, "b": False}]}
    s = "\n".join(J.section(mom, markers, dt.date(2026, 11, 2)))
    assert "2026-10-30 の大引けで決めた一覧（11月のあいだ使う）" in s and "7777 強  12か月 +350%" in s and "〔C 売買代金の急増〕" in s
    assert "新しく買わない側" in s and "空売りの合図でもない" in s and "J42F" in s and "J42 ✕" in s
    assert J.section(mom, markers, dt.date(2026, 10, 31)) == []          # 土曜
    assert "10月に使う一覧がまだ無い（夕方の jp-highs が次に回ったときから作る）" in "\n".join(J.section(None, None, dt.date(2026, 10, 9)))
    assert "最新は 2026-10-30 の分" in "\n".join(J.section(mom, None, dt.date(2026, 12, 1)))


def test_landmine_flags_match_the_research():
    import main_field_lab as MF
    c = [100 + i * 0.1 for i in range(40)]
    c[-6:] = [103.0, 110, 111, 112, 120, 140]                           # 6日前に下げて、そのあと5日続けて上げた
    rows = [(f"d{i}", 0, 0, 0, x, 0) for i, x in enumerate(c)]          # main_field_lab の日足の形（4列目が終値）
    dev, streak = MF.prev_features(rows)
    bars = [(f"d{i}", x * 1.01, x * 0.99, x, 1e6) for i, x in enumerate(c)]
    d2, s2 = JM.landmine_values(bars)
    assert abs(d2 - dev[-1]) < 1e-12 and s2 == streak[-1] == 5
    assert (JM.OVERHEAT, JM.STREAK, JM.MAIN_TV, JM.SURGE) == (MF.OVERHEAT, MF.STREAK, MF.TURNOVER, 0.15) and JM.UP == MF.PREV_BIG
    r = {"b": True, "c": True, "tv": 12.0, "ret": 0.167, "dev25": d2, "streak": 5}
    assert JM.mines(r) == [f"過熱（25日線 +{d2 * 100:.0f}%）", "連騰（5日）", "急騰（+15%以上）", "売買代金の急増"]
    assert JM.mines(dict(r, tv=9.0)) == [] and JM.mines(dict(r, b=False)) == []      # 主戦場（+5%・10億円以上）だけ
    assert "💣地雷：" in JM._fmt(dict(r, code="1111", name="甲", ratio=6.0))


FC = {"generated_at": "2026-10-09T06:15:00+09:00",
      "risk_regime": {"regime": "RISK_OFF", "confidence": "MID", "rationale": "米金利の上昇" * 30,
                      "key_drivers": ["FOMC", "原油", "ドル高", "四つ目"]},
      "assets": [{"name": "日経225", "ticker": "NKD=F", "bias": "NEUTRAL", "conviction": "MID", "rationale": "円安が支え"},
                 {"name": "ドル円", "ticker": "USDJPY", "bias": "BULLISH", "conviction": "LOW"}]}
EC = {"updated": "2026-09-25", "jp": [{"code": "9983", "name": "ファストリ", "date": "2026-10-09", "time": "引け後", "tentative": True},
                                      {"code": "4063", "name": "信越", "date": "2026-10-12", "time": "引け後"}],
      "us": [{"ticker": "JPM", "name": "JPMorgan", "date": "2026-10-13", "time": "寄付前"}]}


def test_fundamentals_section():
    s = "\n".join(B.fundamentals_section(FC, dt.date(2026, 10, 9)))
    assert "リスクオフ（売られやすい）・確度 中（06:15 作成）" in s and "…" in s and "四つ目" not in s
    assert "日経225 中立（中）・ドル円 上向き（低）" in s and "日経：円安が支え" in s and "A1" in s and "今朝の見立てではない" not in s
    assert "今朝の見立てではない（2026-10-09T06:15" in "\n".join(B.fundamentals_section(FC, dt.date(2026, 10, 12)))
    assert B.fundamentals_section(FC, dt.date(2026, 10, 10)) == [] and "読めない" in "\n".join(B.fundamentals_section(None, dt.date(2026, 10, 9)))


def test_earnings_section():
    s = "\n".join(B.earnings_section(EC, dt.date(2026, 10, 12)))
    assert "🇯🇵 10/09(金)＝今日の寄りに効く 引け後 9983" in s                # 前の平日の引け後
    s = "\n".join(B.earnings_section(EC, dt.date(2026, 10, 9)))       # 金曜＝次の平日は月曜 10/12
    assert "🇯🇵 今日 引け後 9983 ファストリ（予定）" in s and "10/12(月) 引け後 4063 信越" in s and "JPM" not in s
    assert "主な銘柄の決算の予定なし" in "\n".join(B.earnings_section(EC, dt.date(2026, 10, 20)))
    assert "🇺🇸 10/13(火)（米国の日付） 寄付前 JPM" in "\n".join(B.earnings_section(EC, dt.date(2026, 10, 12)))
    assert "JPM" not in "\n".join(B.earnings_section(EC, dt.date(2026, 10, 14)))   # 前の平日の「寄付前」は出さない
    assert B.earnings_section(EC, dt.date(2026, 10, 11)) == []
    assert B.research_section(dt.date(2026, 10, 10)) == [] and "J42 ✕" in "\n".join(B.research_section(dt.date(2026, 10, 5)))
    # 2026-10-09〜 研究は週の最初の取引日だけ（月曜・10/12 はスポーツの日＝その週は火曜 10/13）
    assert B.research_section(dt.date(2026, 10, 9)) == [] and B.research_section(dt.date(2026, 10, 12)) == []
    assert B.research_section(dt.date(2026, 10, 13)) and B.research_section(dt.date(2026, 10, 14)) == []
    s = "\n".join(B.earnings_section(EC, dt.date(2026, 10, 12), jp_open=False))      # 東証の休み＝前の平日の引け後は次の取引日に効く
    assert "🇯🇵 10/09(金)＝次の取引日の寄りに効く 引け後 9983" in s and "今日の寄りに効く" not in s


def test_tse_calendar():
    """東証の休み（2026-10-09 オーナー「東証の休日日はもちろん意味がないので日本株の欄を止めてください」）"""
    d = dt.date
    assert B.tse_closed(d(2026, 10, 12)) and B.tse_closed(d(2026, 10, 10)) and not B.tse_closed(d(2026, 10, 13))
    assert B.tse_closed(d(2026, 12, 31)) and B.tse_closed(d(2028, 1, 3)) and not B.tse_closed(d(2028, 1, 4))   # 年末年始は一覧の外でも休み
    assert B.tse_closed(d(2026, 10, 12), "/nonexistent.json") is False                                    # 一覧が無ければ土日と年末年始だけ
    assert B.prev_session(d(2026, 10, 13)) == d(2026, 10, 9) and B.prev_session(d(2026, 5, 7)) == d(2026, 5, 1)
    assert B.week_first_session(d(2026, 10, 5)) and B.week_first_session(d(2026, 10, 13)) and not B.week_first_session(d(2026, 10, 6))
    assert B.week_first_session(d(2026, 9, 24)) and not B.week_first_session(d(2026, 9, 21))              # 9/21〜23 の連休の週は木曜


def test_summary_section():
    """一番上の「今日の要点」（2026-10-09 オーナー「1と2を進めて」）＝下の各欄から数字を拾うだけ"""
    J9 = lambda h, m=0, d=9: dt.datetime(2026, 10, d, h, m, tzinfo=dt.timezone(dt.timedelta(hours=9)))
    now = J9(6, 20)
    ev = lambda w, n: (w, {"name": n})
    fc = dict(FC, currencies=[{"code": "USD", "lean": "STRONG", "conviction": "HIGH"}, {"code": "JPY", "lean": "WEAK", "conviction": "MID"},
                              {"code": "AUD", "lean": "NEUTRAL", "conviction": "LOW"}])
    fx = {"h24": {"USD": 0.40, "EUR": -0.02, "GBP": 0.06, "JPY": -0.30, "AUD": -0.12}}
    mk = {"asof": "2026-10-08", "rows": [{"code": "7777", "c": True, "b": True, "tv": 12.0, "ret": 0.2, "dev25": 0.3, "streak": 5},
                                         {"code": "8888", "c": True, "b": False, "tv": 3.0, "ret": 0.01}]}
    s = "\n".join(B.summary_section(now, [ev(J9(9, 30), "豪 雇用統計"), ev(J9(21, 30), "米 CPI"), ev(J9(23), "米 何か"),
                                         ev(J9(23, 30), "米 四つ目")], fc, fx, mk, _mom(), EC))
    assert s.startswith("【⭐ 今日の要点（くわしくは下の各欄）】")
    assert "🚫 発表：09:30 豪 雇用統計・21:30 米 CPI・23:00 米 何か ほか1件（数時間前〜は新規を建てない）" in s
    assert "・地合い（AI）：リスクオフ（売られやすい）・確度 中／日経225 中立・ドル円 上向き" in s and "今朝の見立てではない" not in s
    assert "・通貨（24時間の値動き）：強い 米ドル +0.40%・ポンド +0.06% ／ 弱い 円 -0.30%・豪ドル -0.12%" in s
    assert "・通貨（AIの見立て）：強い 米ドル（高） ／ 弱い 円（中）" in s
    assert "・日本株：寄りで買わない目印 2銘柄（★C・B候補の両方 1・💣地雷 1）／強すぎる株 1銘柄（新しく買わない側）" in s
    assert "・決算（日本の主な銘柄）：9983 ファストリ（今日 引け後）" in s
    s = "\n".join(B.summary_section(now, [ev(J9(21, 30, 13), "米 CPI")], None, None, None, None, None))
    assert "・発表：今日はなし（次は 10/13(火) 21:30 米 CPI）" in s and "地合い" not in s and "日本株" not in s and "通貨" not in s
    assert "🟡 発表：21:30 米 CPI" in "\n".join(B.summary_section(now, [ev(J9(21, 30), "米 CPI")]))          # 6時間より先
    s = "\n".join(B.summary_section(J9(6, 20, 12), [], FC, None, mk, {"lists": "壊れた"}, EC))       # 月曜・一覧は金曜→4日以内
    assert "今朝の見立てではない" in s and "強すぎる株" not in s and "寄りで買わない目印 2銘柄" in s
    assert "9983 ファストリ（10/09 引け後＝今日の寄りに効く）" in s and "4063 信越（今日 引け後）" in s
    assert "日本株" not in "\n".join(B.summary_section(J9(6, 20, 14), [], FC, None, mk))                 # 一覧が古い
    hol = "\n".join(B.summary_section(J9(6, 20, 12), [], FC, fx, mk, _mom(), EC, jp_open=False))        # 東証の休み
    assert "・日本株：今日は東証の休み（日本株の欄はなし）" in hol and "寄りで買わない目印" not in hol and "決算" not in hol and "通貨" in hol
    sat = B.summary_section(J9(6, 20, 10), [], FC, fx, mk, _mom(), EC)
    assert sat == ["【⭐ 今日の要点（くわしくは下の各欄）】", "  ・発表：今日はなし", ""]                     # 土曜は発表だけ


def test_wired_into_digest_and_jp_highs():
    import send_indicator_digest as D
    o1, o2, o3, o4 = D.load_markers, D.load_momentum, B.FUND, B.EARN
    try:
        D.load_markers = lambda: {"asof": "2026-10-08", "rows": [{"code": "7777", "name": "強", "tv": 12.3, "ratio": 6.0, "ret": 0.2,
                                                                   "c": True, "b": True, "dev25": 0.3, "streak": 5}],
                                  "universe": 3700, "n_c": 1, "n_b": 1, "keep_min_tv": 1.0}
        D.load_momentum = lambda: _mom()
        _, body = D.build(dt.datetime(2026, 10, 9, 6, 20, tzinfo=D.JST))
    finally:
        D.load_markers, D.load_momentum = o1, o2
    for s in ("今日のファンダ", "決算発表", "寄りで買わない目印", "💣地雷：", "強すぎる株＝新しく買わない側", "2026-09-30 の大引けで決めた一覧",
              "投資助言ではありません"):
        assert s in body, s
    assert body.index("今日の要点") < body.index("【今日】") < body.index("今日のファンダ") < body.index("【🇯🇵 日本株：寄りで買わない目印") \
        < body.index("【🇯🇵 日本株：強すぎる株") and "研究から分かっていること" not in body                      # 金曜＝研究の欄なし
    try:
        D.load_markers = lambda: {"asof": "2026-10-09", "rows": [], "universe": 3700, "n_c": 0, "n_b": 0, "keep_min_tv": 1.0}
        D.load_momentum = lambda: _mom()
        _, hol = D.build(dt.datetime(2026, 10, 12, 6, 20, tzinfo=D.JST))                 # スポーツの日（東証の休み）
        _, tue = D.build(dt.datetime(2026, 10, 13, 6, 20, tzinfo=D.JST))                 # その週の最初の取引日
    finally:
        D.load_markers, D.load_momentum = o1, o2
    assert "今日は東証の休み" in hol and "【🇯🇵" not in hol and "研究から分かっていること" not in hol and "今日のファンダ" in hol
    assert "【🇯🇵 日本株：寄りで買わない目印" in tue and "【🇯🇵 日本株：強すぎる株" in tue and "研究から分かっていること" in tue
    assert "寄りで買わない目印 1銘柄（★C・B候補の両方 1・💣地雷 1）／強すぎる株 1銘柄" in body
    try:
        D.load_momentum = lambda: {"lists": "壊れた"}                      # 壊れた欄でもメールは届く
        _, broken = D.build(dt.datetime(2026, 10, 9, 6, 20, tzinfo=D.JST))
    finally:
        D.load_momentum = o2
    assert "【強すぎる株】" in broken and "作れなかった" in broken and "投資助言ではありません" in broken
    _, sat = D.build(dt.datetime(2026, 10, 10, 6, 20, tzinfo=D.JST))
    assert "強すぎる株" not in sat and "今日のファンダ" not in sat
    src = open("build_jp_highs.py", encoding="utf-8").read()
    assert "import jp_momentum" in src and '"momentum": momentum_or_error(daily, stocks, asof)' in src and '"momentum" in prev' in src
    assert (B.FUND, B.EARN) == (o3, o4)


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
