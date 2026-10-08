# -*- coding: utf-8 -*-
"""J40 売り禁・規制の前向き記録（short_limits.py）のテスト。2026-10-08 新設。

いまは probe だけ。確かめること＝①事前登録と定数の一致 ②リンクの拾い方（相対・絶対・同じ URL は1回）と規制の言葉の絞り込み
③銘柄コードを伏せる・表の形だけを出す ④probe は何も書き出さない ⑤ワークフローと SYNC 禁忌。

実行:  python tests/test_short_limits.py     （pytest 不要。pytest でも動く）
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import short_limits as S  # noqa: E402


def test_prereg_matches_the_code():
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "## J40 売り禁・規制はどれくらいかかるか" in text and "**損益の判定はしない**" in text and "`--probe`" in text
    assert "**3割以上**" in text and "`jp-margin.json`" in text
    names = " ".join(n for n, _ in S.SITES)
    assert "日本証券金融" in names and "増担保" in names and "日々公表" in names and "注意喚起" in names


def test_links_and_keywords():
    html = ('<a href="/brand/">貸借取引情報･銘柄別制限措置</a><a href="https://x.jp/a.csv">申込停止 一覧</a>'
            '<a href="b.html"><span>会社概要</span></a><a href="/brand/">重複</a><a href="mailto:x@y">メール</a>')
    got = S.links(html, "https://www.taisyaku.jp/top/index.html")
    assert got == [("https://www.taisyaku.jp/brand/", "貸借取引情報･銘柄別制限措置"), ("https://x.jp/a.csv", "申込停止 一覧"),
                   ("https://www.taisyaku.jp/top/b.html", "会社概要")]
    assert [u for u, _ in S.keyword_links(got)] == ["https://www.taisyaku.jp/brand/", "https://x.jp/a.csv"]   # 会社概要は外す
    assert S.FILE_EXT.search("https://x.jp/a.csv") and not S.FILE_EXT.search("https://x.jp/a.html")


def test_mask_and_tables_show_shape_only():
    assert S.mask("7203") == "（コード）" and S.mask("130A") == "（コード）" and S.mask("72030") == "（コード）"
    assert S.mask("規制の内容がとても長い文字列です") == "規制の内容がとても長い文字列"
    html = ("<table><tr><th>銘柄名</th><th>コード</th><th>実施日</th></tr><tr><td>甲（株）</td><td>7203</td><td>2026/10/08</td></tr>"
            "<tr><td>乙</td><td>6758</td><td>2026/10/07</td></tr></table>")
    (n, head, second), = S.html_tables(html)
    assert n == 3 and head == ["銘柄名", "コード", "実施日"] and second == ["…", "（コード）", "2026/10/08"]
    assert S.mask_row(['"2134"', '"北浜キャピタル"', "申込停止", "2026/10/08", "1.5"]) == ["（コード）", "…", "申込停止", "2026/10/08", "1.5"]
    assert S.mask_row(["コード", "銘柄名", "措置"]) == ["コード", "銘柄名", "措置"]                       # 見出しはそのまま
    assert S.SITES[-1][1] == "https://www.taisyaku.jp/restrictive.php"
    assert "甲" not in repr(S.html_tables(html))
    assert S.decode("申込停止".encode("cp932")) == "申込停止" and S.decode("規制".encode()) == "規制"


def test_probe_writes_nothing():
    pages = {"http://www.taisyaku.jp/brand/": '<a href="/brand/list.html">銘柄別の制限措置（申込停止）</a>'.encode(),
             "http://www.taisyaku.jp/brand/list.html": b"<table><tr><th>\xe3\x82\xb3\xe3\x83\xbc\xe3\x83\x89</th></tr></table>"}
    before = set(os.listdir("."))
    orig = S.SITES
    try:
        S.SITES = (("日本証券金融（銘柄別の制限措置）", "http://www.taisyaku.jp/brand/"),)
        assert S.probe(get=lambda u: pages[u]) == 0
    finally:
        S.SITES = orig
    assert set(os.listdir(".")) == before and S.main([]) == 1


JSF = ("<table><tr><th>直近</th><th>コード</th><th>銘柄名</th><th>実施措置</th><th>実施内容</th><th>通知日・実施日</th></tr>"
       "<tr><td></td><td>1001</td><td>甲</td><td>申込停止</td><td>新規売り</td><td>2026/10/07 2026/10/08</td></tr>"
       "<tr><td>●</td><td>1002</td><td>乙</td><td>注意喚起</td><td>-</td><td>2026/10/08</td></tr>"
       "<tr><td></td><td>1003</td><td>丙</td><td>貸借担保金率の引上げ</td><td>-</td><td>2026/10/01</td></tr>"
       "<tr><td>●</td><td>1004</td><td>丁</td><td>申込停止</td><td>新規売り</td><td>2026/10/08 2026/10/12</td></tr></table>")   # 1004 はまだ効いていない
JPX = ("<table><tr><th>銘柄名</th><th>コード</th><th>実施日</th><th>規制の内容</th><th>該当基準</th></tr>"
       "<tr><td>戊</td><td>1005</td><td>2026/09/16</td><td>…</td><td>…</td></tr><tr><td>己</td><td>1001</td><td>2026/10/20</td><td>…</td><td>…</td></tr></table>"
       "<table><tr><th>銘柄名</th><th>コード</th><th>解除日</th><th>規制の内容</th></tr><tr><td>庚</td><td>1006</td><td>2026/09/28</td><td>…</td></tr></table>")


def test_record_rules_as_registered():
    import datetime as dt
    import auction_forward as F
    text = open("PILLAR_PREREG.md", encoding="utf-8").read()
    assert "実施措置に「**申込停止**」を含む行＝**売り禁**" in text and "**いちばん遅い日がその朝より後の行は、まだ効いていないので入れない**" in text
    today = dt.date(2026, 10, 9)
    margin = {"asof": "2026-10-08", "rows": [{"code": "1002"}, {"code": "1007"}]}
    highs = {"markers": {"asof": "2026-10-08", "rows": [{"code": c} for c in ("1001", "1002", "1003", "1005")]}}
    e = S.build_entry(today, JSF, JPX, margin, highs, "x")
    assert e["jsf_ok"] and e["jpx_ok"] and e["daily_ok"] and e["candidates"] == 4
    assert e["counts"] == {"ban": 1, "jsf_alert": 1, "jsf_other": 1, "zoutanpo": 1, "daily": 2}
    assert e["tags"]["ban"] == [S.tag("1001")] and e["tags"]["daily"] == [S.tag("1002")] and e["tags"]["zoutanpo"] == [S.tag("1005")]
    assert e["labels"] == {"申込停止": 1, "注意喚起": 1, "貸借担保金率の引上げ": 1} and S.tag("1001") == F.tag("1001")
    stale = S.build_entry(today, JSF, None, None, {"markers": {"asof": "2026-09-30", "rows": []}}, "x")
    assert stale["candidates"] is None and not stale["jpx_ok"] and not stale["daily_ok"] and stale["tags"]["ban"] == [S.tag("1001")]
    assert not S.build_entry(today, "<html>表なし</html>", JPX, None, None, "x")["jsf_ok"]
    assert "1001" not in repr(e) and "甲" not in repr(e)


def test_record_once_per_day():
    import datetime as dt
    import tempfile
    calls = []

    def get(url):
        calls.append(url)
        return (JSF if "taisyaku" in url else JPX).encode()
    with tempfile.TemporaryDirectory() as d:
        orig = (S.OUT_MD, S.MARGIN, S.HIGHS)
        S.OUT_MD, S.MARGIN, S.HIGHS = os.path.join(d, "o.md"), os.path.join(d, "m.json"), os.path.join(d, "h.json")
        try:
            path = os.path.join(d, "s.json")
            st = S.record(dt.date(2026, 10, 9), get, path)
            assert st["days"]["2026-10-09"]["jsf_ok"] and len(calls) == 2 and os.path.exists(path)
            S.record(dt.date(2026, 10, 9), get, path)
            assert len(calls) == 2                                              # その日の分は取り直さない
            S.record(dt.date(2026, 10, 10), get, path)                          # 土曜は記録しない
            assert len(calls) == 2 and "| 2026-10-09 | ✅ | ✅ |" in open(S.OUT_MD, encoding="utf-8").read()
        finally:
            S.OUT_MD, S.MARGIN, S.HIGHS = orig


def test_workflow_and_sync_forbidden():
    wf = open(".github/workflows/short-limits.yml", encoding="utf-8").read()
    assert "python -u short_limits.py --probe" in wf and "python tests/test_short_limits.py" in wf and "contents: read" in wf
    assert '"short-limits.json", "short-limits.md"' in open("check_site_consistency.py", encoding="utf-8").read()
    af = open(".github/workflows/auction-forward.yml", encoding="utf-8").read()
    assert "python -u short_limits.py --record ||" in af and af.index("short_limits.py --record") < af.index("python auction_forward.py")
    assert "short-limits.json short-limits.md" in af


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
