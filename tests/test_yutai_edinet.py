# -*- coding: utf-8 -*-
"""build_yutai_edinet の試験（作り物の CSV だけ。EDINET には行かない）"""
import datetime as dt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import build_yutai_edinet as B  # noqa: E402


def _csv(rows):
    """XBRL→CSV の形（タブ区切り・9列・引用符付き）"""
    out = ['"要素ID"\t"項目名"\t"コンテキストID"\t"相対年度"\t"連結・個別"\t"期間・時点"\t"ユニットID"\t"単位"\t"値"']
    for eid, label, val in rows:
        v = val.replace('"', '""')
        out.append(f'"{eid}"\t"{label}"\t"FilingDateInstant"\t"提出日時点"\t"その他"\t"時点"\t""\t""\t"{v}"')
    return {"jpcrp030000-asr-001.csv": "\n".join(out)}


BLOCK = ("<table><tr><td>事業年度</td><td>４月１日から３月31日まで</td></tr>"
         "<tr><td>基準日</td><td>３月31日</td></tr>"
         "<tr><td>剰余金の配当の基準日</td><td>９月30日<br/>３月31日</td></tr>"
         "<tr><td>株主に対する特典</td><td>毎年３月31日及び９月30日現在の株主名簿に記載された"
         "１単元（100株）以上保有の株主に対し、自社製品詰め合わせを贈呈します。</td></tr></table>")


def test_block_found_months_and_record_dates():
    texts = _csv([("jpcrp_cor:NetSales", "売上高", "100"),
                  ("jpcrp_cor:SomethingStockAdministrationTextBlock", "株式事務の概要 [テキストブロック]", BLOCK)])
    p = B.parse_doc(texts)
    assert p["found"] == "block" and p["has_yutai"] is True
    assert p["months"] == [3, 9]
    assert p["benefit_head"].startswith("毎年")
    assert "3月31日" in B.norm(p["record_dates"]) and "9月30日" in B.norm(p["record_dates"])


def test_label_row_preferred():
    texts = _csv([("jpcrp_cor:X", "株主に対する特典", "12月末日現在の株主にクオカード1,000円分")])
    p = B.parse_doc(texts)
    assert p["found"] == "label" and p["has_yutai"] is True and p["months"] == [12]


def test_no_benefit_variants():
    for s in ["該当事項はありません。", "該当事項はありません", "なし", "ありません", "該当なし", "―", "－",
              "該当事項はございません（注）単元未満株式の権利制限…"]:
        assert B.classify(s) is False, s
    assert B.classify("") is None and B.classify(None) is None
    assert B.classify("自社の食事券を贈呈") is True
    assert B.classify("当社は株主優待制度を導入しておりません。") is False
    assert B.classify("株主優待制度は2025年3月末日をもって廃止いたしました。") is False
    assert B.classify("3月末日現在の株主に対し、自社製品を贈呈いたします。なお、詳細はありません") is True


def test_not_found():
    p = B.parse_doc(_csv([("jpcrp_cor:NetSales", "売上高", "100")]))
    assert p["found"] is None and p["has_yutai"] is None and p["months"] == [] and p["benefit_head"] == ""


def test_months_only_head_and_valid():
    assert B.months_in("毎年6月末日及び12月末日現在") == [6, 12]
    assert B.months_in("13月1日 と 0月5日") == []
    assert B.months_in("x" * 500 + "3月31日") == []          # 頭の400字の外は見ない


def test_yuho_from_list_filters():
    res = [{"docID": "S1", "docTypeCode": "120", "secCode": "72030", "withdrawalStatus": "0",
            "submitDateTime": "2026-06-18 15:00", "periodStart": "2025-04-01", "periodEnd": "2026-03-31",
            "filerName": "テスト"},
           {"docID": "S2", "docTypeCode": "130", "secCode": "72030"},                       # 訂正は入れない
           {"docID": "S3", "docTypeCode": "120", "secCode": "", "withdrawalStatus": "0"},   # 証券コードなし
           {"docID": "S4", "docTypeCode": "120", "secCode": "99990", "withdrawalStatus": "1"}]  # 取り下げ
    out = B.yuho_from_list(res, "2026-06-18")
    assert [r["id"] for r in out] == ["S1"] and out[0]["period_end"] == "2026-03-31"


def test_collect_end_to_end(tmp_path):
    day = dt.date(2026, 6, 18)
    lists = {day.isoformat(): [{"docID": "S1", "docTypeCode": "120", "secCode": "72030", "withdrawalStatus": "0",
                                "submitDateTime": "2026-06-18 15:00", "periodEnd": "2026-03-31"},
                               {"docID": "S2", "docTypeCode": "120", "secCode": "13010", "withdrawalStatus": "0",
                                "submitDateTime": "2026-06-18 15:00", "periodEnd": "2026-03-31"}]}
    docs = {"S1": _csv([("jpcrp_cor:A", "株主に対する特典", "3月31日現在の株主に米5kg")]),
            "S2": _csv([("jpcrp_cor:A", "株主に対する特典", "該当事項はありません。")])}
    old_start = B.LIST_START
    B.LIST_START = day
    try:
        r = B.collect("k", 10, today=day + dt.timedelta(days=1), out_dir=str(tmp_path),
                      list_fn=lambda ds, k: lists.get(ds, []), doc_fn=lambda i, k: docs[i], sleep=lambda s: None)
        assert r["docs_parsed_total"] == 2 and r["has_true"] == 1 and r["has_false"] == 1 and r["docs_left"] == 0
        parsed = B.read_parsed(str(tmp_path))
        assert parsed["S1"]["months"] == [3] and parsed["S2"]["benefit_head"] == ""
        r2 = B.collect("k", 10, today=day + dt.timedelta(days=1), out_dir=str(tmp_path),
                       list_fn=lambda ds, k: lists.get(ds, []), doc_fn=lambda i, k: docs[i], sleep=lambda s: None)
        assert r2["days_fetched"] == 0 and r2["docs_parsed_now"] == 0          # 2回目は何もしない（冪等）
        assert len(B.read_index(str(tmp_path))) == 2
    finally:
        B.LIST_START = old_start


def test_doc_failure_gives_up(tmp_path):
    day = dt.date(2026, 6, 18)
    lists = {day.isoformat(): [{"docID": "S9", "docTypeCode": "120", "secCode": "72030", "withdrawalStatus": "0"}]}

    def boom(i, k):
        raise OSError("x")
    old_start = B.LIST_START
    B.LIST_START = day
    try:
        for _ in range(B.MAX_DOC_FAIL):
            r = B.collect("k", 10, today=day + dt.timedelta(days=1), out_dir=str(tmp_path),
                          list_fn=lambda ds, k: lists.get(ds, []), doc_fn=boom, sleep=lambda s: None)
        assert r["giveup"] == 1 and r["docs_left"] == 0
    finally:
        B.LIST_START = old_start


def test_parsed_file_is_deterministic(tmp_path):
    rows = {"A": {"id": "A", "date": "2026-06-18", "x": 1}}
    B.write_parsed(rows, str(tmp_path))
    a = (tmp_path / "parsed-2026.jsonl.gz").read_bytes()
    B.write_parsed(rows, str(tmp_path))
    assert (tmp_path / "parsed-2026.jsonl.gz").read_bytes() == a
