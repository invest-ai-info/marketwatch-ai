# -*- coding: utf-8 -*-
"""check_automation_health.py §⑧「エスカレ滞留」の見出し解析テスト。

動機＝2026-09-17 の実害: §⑧ は旧書式（パイプ3本）の見出ししか拾えず、2026-08-29 に
書き手が書式を変えた時点から**何も見なくなった**。#097（9/13〜）と #098（9/14〜）が
🚩エスカレ中なのに毎朝「✅ 未対応の 🚩 は 0 件」と報告していた。
番人が静かなのと、異常が無いのは違う——それをここで機械的に固定する。

実行:  python tests/test_escalation_parsing.py     （pytest 不要。pytest でも動く）
"""
import os
import sys
import datetime as dt
import importlib.util

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location(
    "check_automation_health", os.path.join(ROOT, "check_automation_health.py"))
cah = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cah)

NOW = dt.datetime(2026, 9, 18, 0, 30, tzinfo=dt.timezone.utc)   # 09:30 JST＝番人の実行時刻


# --- ① 見出しから対象を取り出せるか（実測した5書式すべて） ---------------------------
def test_extract_target_all_formats():
    cases = [
        # 旧書式（パイプ3本）＝2026-08-29 以前
        ("2026-08-11 | 🚩 独立Opus否・FWDデータ修正要 | signal-lab-067 | signal-lab-daily",
         "signal-lab-067"),
        ("2026-08-18 | 🚩要人間レビュー（コンプラ：黒） | signal-lab-daily #072 | signal-lab-daily",
         "signal-lab-072"),
        ("2026-08-15 | 🚩 ゲート赤（旧ブランドカラー5箇所） | book-watch-weekly | 人間対応必要",
         "book-watch-weekly"),
        # 新書式（コロン区切り）＝2026-08-29 以降。旧正規表現はここから一切拾えなかった
        ("2026-09-14 signal-lab #098: draft-signal-lab-098.html", "signal-lab-098"),
        ("2026-09-13 signal-lab #097: draft-signal-lab-097.html", "signal-lab-097"),
        ("2026-09-02 autopublish: 🚩要人間レビュー: bid-ask-spread（品質③ブロッカー2件・公開せず）",
         "bid-ask-spread"),
        ("2026-07-08 | autopublish: 🚩要人間レビュー — guide-inflation-real-return.html（EXIT=1）",
         "inflation-real-return"),
        # `##` すら付かない素のログ行
        ("2026-09-14 signal-lab: draft-signal-lab-098.html 🚩エスカレ中（Opusコンプラ🔴黒）",
         "signal-lab-098"),
        ("2026-08-08 autopublish: 🚩ゲート赤／インフラ未解決（3日連続）: key=margin-trading / ...",
         "margin-trading"),
        # 日付＋🚩＋パイプ2本（旧でも新でもない混在形）
        ("2026-08-28 🚩 要人間レビュー | shareholder-benefits | autopublish",
         "shareholder-benefits"),
    ]
    for title, want in cases:
        got = cah.extract_target(title)
        assert got == want, f"{title!r} → {got!r}（期待 {want!r}）"


# --- ② `##` 節も素のログ行も同じ1件として切り出せるか --------------------------------
def test_iter_review_entries_mixes_headings_and_plain_lines():
    md = (
        "2026-09-14 signal-lab: draft-signal-lab-098.html 🚩エスカレ中\n"
        "\n"
        "## 2026-09-14 signal-lab #098: draft-signal-lab-098.html\n"
        "\n"
        "- **テーマ**: RSI売られすぎ逆張り買い\n"
        "- **基準日**: 2026-09-14（JST）\n"        # 行頭が日付でない＝新エントリにしない
        "\n"
        "2026-09-13 autopublish: guide-benchmark-comparison.html 公開\n"
    )
    entries = cah.iter_review_entries(md)
    assert len(entries) == 3, [e[1] for e in entries]
    assert entries[0][0] == "2026-09-14"
    assert not entries[1][1].startswith("#")          # `#` は落として本文だけ返す
    assert "**テーマ**" in entries[1][2]              # 続く本文がその節に付く


# --- ③ 本題: 新書式の 🚩 が未解決として検出されるか（#098 の再現） ---------------------
def test_new_format_escalation_is_detected():
    md = (
        "2026-09-14 signal-lab: draft-signal-lab-098.html 🚩エスカレ中（Opusコンプラ🔴黒①②③）\n"
        "\n"
        "## 2026-09-14 signal-lab #098: draft-signal-lab-098.html\n"
        "\n"
        "### 🚩 黒①: 昇格1/2到達の誤記\n"
    )
    stale, flags, unresolved, unparsed = cah.eval_escalations(md, published=set(), now=NOW)
    assert flags == 1 and unresolved == 1 and unparsed == []
    assert [t for t, _d, _a in stale] == ["signal-lab-098"]
    assert stale[0][1] == "2026-09-14" and stale[0][2] == 4      # 4日放置

    # 壊れていた頃の正規表現（パイプ3本必須）ではこの見出しは1件も拾えない＝回帰の目印
    assert cah.RE_OLD_PIPE.match(md.splitlines()[2].lstrip("# ")) is None


# --- ④ 旧書式も引き続き拾えるか（後方互換） -------------------------------------------
def test_old_pipe_format_still_detected():
    md = "## 2026-09-14 | 🚩 独立Opus否・FWDデータ修正要 | signal-lab-067 | signal-lab-daily\n"
    stale, flags, unresolved, unparsed = cah.eval_escalations(md, published=set(), now=NOW)
    assert flags == 1 and unresolved == 1 and unparsed == []
    assert stale[0][0] == "signal-lab-067"


# --- ⑤ 解決したものは鳴らさない（誤検知で鳴りっぱなしにしない） -----------------------
def test_resolved_escalations_are_quiet():
    md = (
        "## 2026-09-14 signal-lab #098: draft-signal-lab-098.html 🚩エスカレ中\n"
        "## 2026-09-14 autopublish: 🚩要人間レビュー: bid-ask-spread（公開せず）\n"
        "## 2026-09-14 | 🚩 ゲート赤 [解消済み] | margin-trading | autopublish\n"
        "## 2026-09-14 | 🚩 ゲート赤 | book-watch-weekly | 人間対応必要\n"
    )
    published = {
        "guide-signal-lab-098.html",   # ① 成果物が出ている＝解決
        "guide-bid-ask-spread.html",   # ① 同上（見出しの「公開せず」より実体を優先）
        "guide-new-books.html",        # ① TARGET_ARTIFACT の別名照合
    }                                  # margin-trading は ③ 明示の解消マークで解決
    stale, flags, unresolved, unparsed = cah.eval_escalations(md, published, NOW)
    assert flags == 4, flags
    assert (stale, unresolved, unparsed) == ([], 0, [])


# --- ⑥ 「公開」の語が入っていても公開していない回を解決扱いにしない ------------------
def test_not_published_marks_do_not_resolve():
    md = (
        "2026-09-10 autopublish: 🚩要人間レビュー: bid-ask-spread（品質③ブロッカー2件・公開せず）\n"
        "2026-09-14 autopublish: bid-ask-spread は公開せず（人間レビュー待ち）\n"
    )
    stale, _flags, unresolved, _unparsed = cah.eval_escalations(md, published=set(), now=NOW)
    assert unresolved == 1 and [t for t, _d, _a in stale] == ["bid-ask-spread"]

    # 本当に公開した行が後から来れば解決する
    md2 = md + "2026-09-15 autopublish: guide-bid-ask-spread.html 公開済み ✅\n"
    stale2, _f, unresolved2, _u = cah.eval_escalations(md2, published=set(), now=NOW)
    assert (stale2, unresolved2) == ([], 0)


# --- ⑦ 閾値未満は鳴らさない（当日中のエスカレで鳴りっぱなしにしない） ----------------
def test_fresh_escalation_is_unresolved_but_not_stale():
    md = "2026-09-18 signal-lab: draft-signal-lab-103.html 🚩エスカレ中\n"
    stale, flags, unresolved, _u = cah.eval_escalations(md, published=set(), now=NOW)
    assert (flags, unresolved, stale) == (1, 1, [])


# --- ⑧ 対象を取り出せない 🚩 は黙って捨てず「解析不能」で鳴らす -----------------------
#      ここが再発防止の芯。次に書式が変わっても「0件＝問題なし」には落ちない。
def test_unparsable_flag_is_reported_not_swallowed():
    md = "2026-09-14 🚩 要人間レビュー（対象名を書き忘れた回）\n"
    stale, flags, unresolved, unparsed = cah.eval_escalations(md, published=set(), now=NOW)
    assert flags == 1 and (stale, unresolved) == ([], 0)
    assert len(unparsed) == 1 and unparsed[0][0] == "2026-09-14"


# --- ⑨ 実物の見出しを凍結した資料で #098 が滞留として出るか（実データ回帰） ----------
#      合成テストだけだと「テストが通る書式」しか守れないので、実ファイルから抜いた
#      見出しを fixture として固定する。⚠️ 実データが直っても腐らないよう、
#      「今日の滞留」ではなく**凍結した資料**に対して判定する。
def test_frozen_real_headings_detect_098():
    md = open(os.path.join(ROOT, "tests", "fixtures",
                           "review-excerpt-2026-09-17.md"), encoding="utf-8").read()
    published = {"guide-signal-lab-095.html", "guide-signal-lab-079.html",
                 "guide-signal-lab-072.html", "guide-signal-lab-071.html",
                 "guide-signal-lab-067.html", "guide-bid-ask-spread.html",
                 "guide-shareholder-benefits.html", "guide-margin-trading.html",
                 "guide-new-books.html", "guide-inflation-real-return.html"}
    stale, flags, unresolved, unparsed = cah.eval_escalations(md, published, NOW)
    assert not unparsed, f"実物の見出しに解析不能が残っている: {unparsed}"
    assert flags >= 12, f"🚩 の読み取りが少なすぎる: {flags}"
    targets = [t for t, _d, _a in stale]
    # #098（9/14〜）と #097（9/13の節）は成果物が無い＝未解決。旧正規表現はどちらも見えていなかった
    assert "signal-lab-098" in targets, f"#098 が滞留として出ない: {targets}"
    assert "signal-lab-097" in targets, f"#097 が滞留として出ない: {targets}"
    # 成果物が出ているものは鳴らさない（誤検知ゼロ）
    for done in ("signal-lab-079", "bid-ask-spread", "shareholder-benefits", "book-watch-weekly"):
        assert done not in targets, f"解決済みが鳴っている: {done}"


# --- ⑩ 生きている drafts/REVIEW.md の書式ドリフト検知（内容ではなく「読めるか」を見る） ---
#      ここは滞留の中身を問わない。**解析できない🚩が1件でも出たら書式が変わった合図**で、
#      それが 2026-09-17 に §⑧ を黙らせた壊れ方そのもの。
def test_live_review_md_is_still_parsable():
    path = os.path.join(ROOT, "drafts", "REVIEW.md")
    if not os.path.exists(path):
        print("  ⏭ drafts/REVIEW.md が無いので省略")
        return
    md = open(path, encoding="utf-8").read()
    published = {f for f in os.listdir(ROOT) if f.endswith(".html")}
    _stale, flags, _unresolved, unparsed = cah.eval_escalations(md, published, NOW)
    assert flags > 0, "REVIEW.md から 🚩 を1件も読めない＝解析漏れ（過去の🚩は消えない）"
    assert not unparsed, (
        f"対象を取り出せない🚩が {len(unparsed)} 件＝見出し書式が変わった。"
        f"extract_target() に書式を足すこと: {unparsed[:3]}")


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if not name.startswith("test_") or not callable(fn):
            continue
        try:
            fn()
            print(f"✅ {name}")
        except AssertionError as e:
            fails += 1
            print(f"❌ {name}: {e}")
    print(f"\n{'✅ 全テスト通過' if not fails else f'❌ {fails} 件失敗'}")
    sys.exit(1 if fails else 0)
