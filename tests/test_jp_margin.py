# -*- coding: utf-8 -*-
"""信用残（build_jp_margin.py）と、その鮮度の見張り（check_automation_health ⑫）のテスト。2026-09-28 新設。

きっかけ: JPX が 9/25 公表分から Excel を .xls（mtdailyk2026092400.xls）→ .xlsx（20260925_mtdaily.xlsx）に
変え、旧版は「❌ mtdaily リンクが index に無い」で止まった。ワークフローはこのステップを non-fatal に
しているので緑のまま、サイトの信用残は 9/24 のまま残った。

固定すること: 新旧どちらの形式のリンクも見つける（.xlsx を優先）／日付はファイル名から取る／
英字入りの株式コード（278A0 など）も数える／見出しの行や空の行は数えない／
行が0件なら前回のデータを空で上書きしない／ワークフローが .xlsx を読む部品（openpyxl）を入れる／
見張り番は「確定最終営業日から何営業日遅れか」を祝日カレンダーなしで数える。

実行:  python tests/test_jp_margin.py     （pytest 不要。pytest でも動く）
"""
import datetime
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import pandas as pd  # noqa: E402

import build_jp_margin as B  # noqa: E402
import check_automation_health as H  # noqa: E402

NEW_HTML = ('<a href="/markets/statistics-equities/margin/tvdivq0000001r92-att/20260925_mtdaily.xlsx">Excel</a>'
            '<a href="/markets/statistics-equities/margin/tvdivq0000001r92-att/20260925_mtdaily.pdf">PDF</a>')
OLD_HTML = '<a href="/markets/statistics-equities/margin/tvdivq0000001r92-att/mtdailyk2026092400.xls">Excel</a>'


def test_finds_new_xlsx_link():
    url, asof = B.find_excel_link(NEW_HTML)
    assert url == ("https://www.jpx.co.jp/markets/statistics-equities/margin/"
                   "tvdivq0000001r92-att/20260925_mtdaily.xlsx"), url
    assert asof == "2026-09-25"


def test_still_finds_old_xls_link():
    url, asof = B.find_excel_link(OLD_HTML)
    assert url.endswith("/mtdailyk2026092400.xls") and asof == "2026-09-24"


def test_prefers_xlsx_when_both_exist():
    url, _ = B.find_excel_link(OLD_HTML + NEW_HTML)
    assert url.endswith(".xlsx")


def test_no_link_returns_none():
    assert B.find_excel_link('<a href="/foo/bar.pdf">x</a>') == (None, "")


def test_date_comes_from_file_name_not_folder():
    html = '<a href="/margin/20250101-att/mtdaily_20260925.xlsx">x</a>'
    assert B.find_excel_link(html)[1] == "2026-09-25"


def _sheet():
    # 本物の並び（2026-09-25 分で確認）: 3=銘柄名 4=市場 5=種別 6=コード 8-10=売残/前日比/上場比 11-13=買残/前日比/上場比
    head = [None] * 23
    head[3], head[6], head[8], head[11] = "銘柄 Issue", "Code", "売残高", "買残高"

    def row(name, code, sell, sell_chg, sell_pl, buy, buy_chg, buy_pl):
        r = ["B", "日", None, name, "スタンダード", "貸", code, "JP0000000000",
             sell, sell_chg, sell_pl, buy, buy_chg, buy_pl, "1.0"] + [0] * 8
        return r
    return pd.DataFrame([
        head,
        row("ヴィッツ　普通株式", "44400", 33600, 100, "0.8", 258600, -3800, "6.2"),
        row("英字入りコード　普通株式", "278A0", 1000, -200, "0.1", 50000, 300, "2.5"),
        row("売残ゼロ　普通株式", "68620", 0, -700, "0.0", 915800, -15900, "11.6"),
        row("ETF", "13210", 500, 0, "*", 900, 0, "*"),
        row("空の行", "99990", "-", 0, "-", "-", 0, "-"),
    ])


def test_parse_rows_reads_the_real_layout():
    rows = {r["code"]: r for r in B.parse_rows(_sheet())}
    assert set(rows) == {"4440", "278A", "6862", "1321"}, set(rows)       # 見出しと空の行は数えない
    v = rows["4440"]
    assert (v["name"], v["sell"], v["buy"], v["buy_chg"], v["buy_pl"]) == ("ヴィッツ", 33600, 258600, -3800, 6.2)
    assert v["ratio"] == 7.7                                              # 信用倍率＝買残÷売残
    assert rows["6862"]["ratio"] is None                                  # 売残0は倍率を出さない
    assert rows["1321"]["buy_pl"] is None                                 # ETF の上場比「*」は None


def test_reads_xlsx_bytes_like_the_workflow_does():
    try:
        import openpyxl  # noqa: F401
    except ImportError:
        print("    （openpyxl が無いので省略）")
        return
    buf = io.BytesIO()
    _sheet().to_excel(buf, header=False, index=False)
    df = pd.read_excel(io.BytesIO(buf.getvalue()), sheet_name=0, header=None)   # main() と同じ読み方
    assert len(B.parse_rows(df)) == 4


def test_empty_sheet_does_not_overwrite_previous_data():
    src = open("build_jp_margin.py", encoding="utf-8").read()
    body = src[src.index("def main():"):]
    assert "if not rows:" in body and body.index("if not rows:") < body.index("json.dump(")


def test_workflow_installs_openpyxl():
    wf = open(".github/workflows/jp-rankings.yml", encoding="utf-8").read()
    line = [ln for ln in wf.splitlines() if "pip install" in ln and "pandas" in ln][0]
    assert "openpyxl" in line and "xlrd" in line, line


# ── 見張り番（check_automation_health ⑫の信用残）
DATES = ["2026-09-22", "2026-09-24", "2026-09-25", "2026-09-28", "2026-09-29", "2026-09-30"]   # 9/23 は祝日


def test_margin_lag_normal_is_one_business_day():
    # 9/30 09:30 JST の点検: 確定最終営業日 9/29、JPX は 9/28 申込み現在を 9/29 に公表＝遅れ1
    assert H.margin_lag_days("2026-09-28", DATES, "2026-09-29") == 1
    assert H.margin_lag_days("2026-09-29", DATES, "2026-09-29") == 0


def test_margin_lag_counts_business_days_across_weekend_and_holiday():
    assert H.margin_lag_days("2026-09-22", DATES, "2026-09-25") == 2       # 祝日 9/23 は数えない
    assert H.margin_lag_days("2026-09-25", DATES, "2026-09-28") == 1       # 土日をまたいでも1


def test_this_failure_would_be_flagged_within_two_days():
    # 9/28 の実例: asof 9/24 のまま止まった。9/29 の点検は遅れ2（1回の取りこぼしと区別できない）、9/30 で鳴る
    assert H.margin_lag_days("2026-09-24", DATES, "2026-09-28") <= H.MARGIN_LAG_MAX
    assert H.margin_lag_days("2026-09-24", DATES, "2026-09-29") > H.MARGIN_LAG_MAX


def test_margin_lag_unknown_is_none():
    assert H.margin_lag_days("", DATES, "2026-09-29") is None
    assert H.margin_lag_days("2026-09-24", [], None) is None


def test_settled_date_used_by_margin_check_skips_todays_open_bar():
    # 点検は 09:30 JST＝当日の未確定の足は落とす（⑫のランキングと同じ関数を使う）
    now = datetime.datetime(2026, 9, 30, 0, 30, tzinfo=datetime.timezone.utc)   # 09:30 JST
    assert H.latest_settled_trading_date(DATES, now) == "2026-09-29"


if __name__ == "__main__":
    fails = 0
    tests = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for name, fn in tests:
        try:
            fn()
            print(f"  ✅ {name}")
        except AssertionError as e:
            fails += 1
            print(f"  ❌ {name}: {e}")
    print(f"--- {len(tests) - fails}/{len(tests)} 合格 ---")
    sys.exit(1 if fails else 0)
