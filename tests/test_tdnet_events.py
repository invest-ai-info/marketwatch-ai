# -*- coding: utf-8 -*-
"""TDnet の開示の蓄積と台帳への付与（tdnet_events.py）のテスト。2026-10-27 新設。

一覧の HTML と PDF の文字はすべて作り物（TDnet の形だけまねる）。確かめること＝①一覧の読み取り（全件数・ページ・5桁コード）
②表題の種類（除く言葉・ETF を飛ばす）③PDF の表から向き（全角・数字の間の空白・△・「－」・通期の表を先に・差異）
④取る日（取り終えた日は取り直さない・直近は取り直す・0件の休日・取れない日）⑤付ける窓（30暦日・引けの前と後・覆い）
⑥md と出力に表題を置かない ⑦ワークフロー・SYNC 禁忌・見張り番・事前登録の追記。

実行:  python tests/test_tdnet_events.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import tdnet_events as T  # noqa: E402


def _row(tm, code5, name, title, doc):
    return (f'<tr><td class="oddnew-L kjTime" noWrap>{tm}</td><td class="oddnew-M kjCode" noWrap>{code5}</td>'
            f'<td class="oddnew-M kjName" noWrap>{name} </td><td class="oddnew-M kjTitle" align="left">'
            f'<a href="{doc}.pdf" target="_blank">{title}</a></td><td class="oddnew-M kjXbrl"> </td>'
            f'<td class="oddnew-M kjPlace" noWrap>東 </td><td class="oddnew-R kjHistroy"> </td></tr>')


def page(total, rows):
    return (f'<div>1～{len(rows)}件&nbsp;/&nbsp;全{total}件</div><table><tr><td class="header-L">時刻</td></tr>'
            + "".join(_row(*r) for r in rows) + "</table>")


REV_TEXT = """
1. 通期業績予想数値の修正
                    売上高    営業利益   経常利益   当期純利益   1株当たり
 前回発表予想（Ａ）   百万円     百万円     百万円      百万円        円 銭
 (2026 年４月 21 日公表)  100,000   9,000    9,500      6,000        100.00
 今回修正予想（Ｂ）   102,000   9,800    10,100     6,600        110.00
 増減額（Ｂ－Ａ）       2,000     800      600        600
"""
WIDE_TEXT = """
前 回 発 表 予 想（ Ａ ） １ ２ ５ ,０ ０ ０               ３ ,２ ０ ０     ３ ,６ ５ ０       ２ ,１ ０ ０        ８１円４７銭
今 回 修 正 予 想（ Ｂ ） １ ２ ３ ,０ ０ ０               １ ,６ ０ ０     ２ ,２ ０ ０           ８５０         ３２円９８銭
増     減       額（ Ｂ － Ａ ）      △ ２ ,０ ０ ０    △ １ ,６ ０ ０   △ １ ,４ ５ ０     △ １ ,２ ５ ０         ―
"""
NET_ONLY = """
 前回発表予想（Ａ）       3,944,000    53,500     67,500      43,000      210.06
 今回修正予想（Ｂ）       3,944,000    53,500     67,500      53,000      258.92
 増減額（ＢーＡ）               －           －          －     10,000       48.86
"""
TWO_TABLES = """
（１）第２四半期（累計）
 前回発表予想（Ａ）   50,000   4,000   4,100   2,800
 今回修正予想（Ｂ）   48,000   3,500   3,600   2,500
 増減額（Ｂ－Ａ）
（２）通期
 前回発表予想（Ａ）   100,000   8,000   8,200   5,600
 今回修正予想（Ｂ）   101,000   8,300   8,400   5,800
 増減額（Ｂ－Ａ）
"""
GAP_TEXT = """
予想値（Ａ）                 11,351         1,012               682             622           13.34
実績値（Ｂ）                 11,167         1,289             1,023             901           19.32
増減額（Ｂ－Ａ）                △183             276              341             279                ―
"""


def test_parse_list_reads_rows_and_total():
    total, rows = T.parse_list(page(205, [("17:00", "28010", "キッコマン", "剰余金の配当（中間配当）に関するお知らせ", "1401202610275566"),
                                          ("15:30", "436A0", "サンプル", "業績予想の修正に関するお知らせ", "1401202610270001")]))
    assert total == 205 and [r["code"] for r in rows] == ["2801", "436A"] and rows[1]["doc"] == "1401202610270001"
    assert rows[0]["time"] == "17:00" and rows[0]["title"].startswith("剰余金")


def test_tags_follow_the_words():
    t = T.tags_of
    assert t("2027年３月期通期業績予想の修正（上方修正）及び期末配当予想の修正（増配）に関するお知らせ") == ["業績修正", "増配"]
    assert t("業績予想及び配当予想の修正に関するお知らせ") == ["業績修正"]
    assert t("配当予想の修正（増配）に関するお知らせ") == ["増配"]
    assert "業績修正" not in t("2027年4月期の運用状況および分配予想の上方修正のお知らせ")
    assert t("ETFの収益分配のお知らせ") == [] and t("上場ETF（管理会社：X）に関する日々の開示事項") == []
    assert t("自己株式取得に係る事項の決定に関するお知らせ") == ["自社株買い"]
    assert t("自己株式の取得状況に関するお知らせ") == ["自社株買いの進み"]
    assert t("自己株式取得および自己株式消却に係る事項の決定に関するお知らせ") == ["自社株買い", "自己株式の消却"]
    assert t("譲渡制限付株式報酬の株主総会決議超過及び自己株式の無償取得に関するお知らせ") == []
    assert t("譲渡制限付株式報酬としての自己株式の処分に関するお知らせ") == []
    assert t("譲渡制限付株式報酬としての新株式発行に関するお知らせ") == []
    assert t("三菱ケミカル物流株式会社株式の取得に関するお知らせ") == ["M&A"]
    assert t("2027年３月期第２四半期（中間期）連結業績予想と実績との差異に関するお知らせ") == ["差異"]
    assert t("株主による臨時株主総会の招集許可申立てに関するお知らせ") == ["株主総会・提案"]
    assert "TOB・上場廃止" in t("X合同会社による当社株券等に対する公開買付けに関する賛同の意見表明及び応募推奨のお知らせ")


def test_pdf_direction_reads_tables():
    assert T.pdf_direction(REV_TEXT, "修正") == "上方"
    assert T.pdf_direction(WIDE_TEXT, "修正") == "下方"            # 全角・数字の間の空白・円銭
    assert T.pdf_direction(NET_ONLY, "修正") == "上方"             # 営業・経常は「－」＝同じ→純利益で
    assert T.pdf_direction(TWO_TABLES, "修正") == "上方"           # 通期の表を先に（第2四半期は下方）
    assert T.pdf_direction(GAP_TEXT, "差異") == "上方" and T.pdf_direction(GAP_TEXT, "修正") is None
    assert T.pdf_direction("文字化け%&$#", "修正") is None
    assert T.nums("(2026 年４月 21 日公表) 148,700 △98 －") == [148700.0, -98.0, None] or \
        T.nums(T._norm("(2026 年４月 21 日公表) 148,700 △98 －")) == [148700.0, -98.0, None]


def test_classify_prefers_title_direction_and_marks_unknown():
    row = {"time": "15:30", "code": "4684", "title": "通期業績予想の修正（上方修正）に関するお知らせ", "doc": "d1"}
    assert T.classify(row, reader=lambda d: "")["dir"] == "上方"
    row2 = dict(row, title="業績予想の修正に関するお知らせ")
    assert T.classify(row2, reader=lambda d: WIDE_TEXT)["dir"] == "下方"
    assert T.classify(row2, reader=lambda d: "")["dir"] == "不明"
    assert T.classify(dict(row, title="人事異動に関するお知らせ")) is None


def _fake_site(pages_by_day, pdf=""):
    calls = []

    def getter(url, binary=False):
        calls.append(url)
        if binary:
            return pdf.encode() if pdf else None
        for (day, n), html in pages_by_day.items():
            if url.endswith(f"I_list_{n:03d}_{day}.html"):
                return html
        return None
    return getter, calls


def test_collect_fetches_missing_days_and_refreshes_recent():
    today = dt.date(2026, 10, 27)
    rows = [("15:30", "46840", "A社", "業績予想の修正に関するお知らせ", "d1"), ("16:00", "75040", "B社", "役員人事に関するお知らせ", "d2")]
    pages = {("20261027", 1): page(2, rows), ("20261026", 1): page(1, rows[1:]), ("20261023", 1): page(0, []),
             ("20261020", 1): page(150, rows), ("20261020", 2): page(150, rows)}
    getter, calls = _fake_site(pages)
    events, days = T.collect(today, [], {"days": {}}, getter=getter, reader=lambda d: REV_TEXT, back=8, log=lambda *a: None)
    assert set(days["days"]) == {"2026-10-27", "2026-10-26", "2026-10-23", "2026-10-20"}   # 10/23 は0件（3日前＝休日として取り終え）
    assert days["days"]["2026-10-20"]["total"] == 150 and days["days"]["2026-10-27"]["tagged"] == 1
    assert [(e["date"], e["code"], e["dir"]) for e in events] == [("2026-10-20", "4684", "上方"), ("2026-10-20", "4684", "上方"),
                                                                  ("2026-10-27", "4684", "上方")]
    getter2, calls2 = _fake_site(pages)
    T.collect(today, events, days, getter=getter2, reader=lambda d: 1 / 0, back=8, log=lambda *a: None)
    assert not any("20261020" in u for u in calls2)                # 取り終えた古い日は取り直さない
    assert any("20261027" in u for u in calls2)                    # 直近は取り直す（PDF は読み直さない＝reader を呼ばない）


def test_attach_window_close_and_cover():
    days = {"days": {(dt.date(2026, 10, 27) - dt.timedelta(days=k)).isoformat(): {"total": 1}
                     for k in range(0, 31) if (dt.date(2026, 10, 27) - dt.timedelta(days=k)).weekday() < 5}}
    ev = [{"date": "2026-10-27", "time": "15:30", "code": "4684", "tags": "業績修正|増配", "dir": "上方", "doc": "a"},
          {"date": "2026-10-27", "time": "11:00", "code": "4684", "tags": "自社株買い", "dir": "", "doc": "b"},
          {"date": "2026-10-20", "time": "15:00", "code": "4684", "tags": "決算", "dir": "", "doc": "c"},
          {"date": "2026-09-27", "time": "15:00", "code": "4684", "tags": "M&A", "dir": "", "doc": "d"},    # 30暦日ちょうど前＝窓の外
          {"date": "2026-10-10", "time": "15:00", "code": "9999", "tags": "M&A", "dir": "", "doc": "e"}]
    rows = T.attach([{"date": "2026-10-27", "code": "4684", "kind": "記録上の最高値"},
                     {"date": "2026-10-27", "code": "4684", "kind": "記録上の最高値"},       # 同じ日の同じ銘柄は1行
                     {"date": "2026-10-01", "code": "4684", "kind": "年初来"}], ev, days)
    r = rows[0]
    assert len(rows) == 1 and r["td_cover"] == 1 and r["td_n30"] == 2 and r["td_自社株買い"] == 1 and r["td_決算"] == 1
    assert r["td_earn_days"] == 7 and r["td_M&A"] == 0 and r["td_上方修正"] == 0
    assert r["td_after"] == "増配|業績修正・上方"
    days2 = {"days": {k: v for k, v in days["days"].items() if k != "2026-10-05"}}
    assert T.attach([{"date": "2026-10-27", "code": "4684", "kind": "上場来"}], ev, days2)[0]["td_cover"] == 0


def test_outputs_have_no_titles():
    ev = [{"date": "2026-10-27", "time": "15:30", "code": "4684", "tags": "業績修正", "dir": "上方", "doc": "a"}]
    assert T.EVENT_COLS == ("date", "time", "code", "tags", "dir", "doc") and "title" not in T.OUT_COLS
    days = {"days": {"2026-10-27": {"total": 3, "tagged": 1}}}
    att = T.attach([{"date": "2026-10-27", "code": "4684", "kind": "上場来"}], ev, days)
    md = T.render_md(att, [{"date": "2026-10-27", "code": "4684", "name": "オービック"}], ev, days, now="t")
    assert "業績予想の修正に関するお知らせ" not in md and "取れた範囲" in md


def test_registered_in_workflow_sync_health_and_prereg():
    wf = open(".github/workflows/tdnet-events.yml", encoding="utf-8").read()
    for s in ('workflows: ["JP Highs Lows"]', "poppler-utils poppler-data", "python tests/test_tdnet_events.py", "python tdnet_events.py",
              "git add tdnet-events.csv tdnet-days.json highs-tdnet.csv highs-tdnet.md"):
        assert s in wf, s
    cs = open("check_site_consistency.py", encoding="utf-8").read()
    for f in ("tdnet-events.csv", "tdnet-days.json", "highs-tdnet.csv", "highs-tdnet.md"):
        assert f'"{f}"' in cs, f
    h = open("check_automation_health.py", encoding="utf-8").read()
    assert h.count('"tdnet-events.yml"') >= 2                          # 鮮度と workflow_run の起動の両方
    pre = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "追記（2026-10-27・TDnet の開示を付ける" in pre and "tdnet-events.yml" in open("RESEARCH_LABS.md", encoding="utf-8").read()


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
            except Exception as e:  # noqa: BLE001
                fails += 1
                print(f"💥 {name}: {type(e).__name__}: {e}")
    sys.exit(1 if fails else 0)
