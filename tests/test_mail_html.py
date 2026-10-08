# -*- coding: utf-8 -*-
"""メールの色付き HTML（mail_html.py）のテスト。2026-10-09 オーナー「ちょっと見づらいので色を使って見やすく…銘柄コードを青、銘柄名を水色…」。

確かめること＝①銘柄の札（コード＝青・名前＝水色・印の札・💣・騰落率の色）②騰落率は決まった行だけ塗る（決まりの文の「+5% 以上」は塗らない）
③通貨の並びの札（強い＝緑・弱い＝赤・中立＝灰）④見出しの帯の色 ⑤決算の欄だけコードと名前を塗る（ニュースの英字は塗らない）
⑥文字を落とさない（本文の言葉は全部 HTML に残る）・HTML の特殊文字を逃がす ⑦送るメール＝文字＋HTML の2本立て・作れなければ文字だけ
⑧Gmail の約102KB の切れ目より十分小さい ⑨朝・まもなく・ロンドン前／NY前の3通がこの部品で送る。

実行:  python tests/test_mail_html.py     （pytest 不要。pytest でも動く）
"""
import datetime as dt
import html
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import mail_html as M  # noqa: E402

ROW = "     1. 3692 ＦＦＲＩセキュリティ  売買代金 232.4億円（6.3倍）・前の日 +17.7% ★C・B候補の両方 〔貸借〕 💣地雷：過熱（25日線 +40%）・急騰（+15%以上）"
ROW2 = "     7. 476A 辻・本郷ＩＴコンサルティング  売買代金 34.3億円（9.3倍）・前の日 -16.8%"
MOM = "     1. 3103 ユニチカ  12か月 +692%・売買代金 108.5億円/日 〔C 売買代金の急増〕"


def text_of(page):
    """HTML → 見える文字（タグを外す）"""
    return html.unescape(re.sub(r"<[^>]+>", "", page))


def test_stock_row_card():
    h = M.stock_row(M.ROW.match(ROW), True)
    assert '<b style="color:#0b57d0">3692</b> <b style="color:#0288d1">ＦＦＲＩセキュリティ</b>' in h
    assert "#fff1e5" in h and "★C・B候補の両方" in h and "〔貸借〕" in h and "background:#f6f8fa" in h
    assert '<b style="color:#1a7f37">+17.7%</b>' in h and "💣地雷：過熱（25日線 +40%）" in h and "color:#cf222e" in h
    h2 = M.stock_row(M.ROW.match(ROW2), False)
    assert '<b style="color:#0b57d0">476A</b>' in h2 and '<b style="color:#cf222e">-16.8%</b>' in h2 and "#f6f8fa" not in h2
    h3 = M.stock_row(M.ROW.match(MOM), False)
    assert '<b style="color:#0288d1">ユニチカ</b>' in h3 and '<b style="color:#1a7f37">+692%</b>' in h3
    assert "background:#ffebe9" in h3 and "〔C 売買代金の急増〕" in h3              # 〔C …〕〔B候補 …〕＝赤の札


def test_percent_only_on_number_lines():
    rule = M.line_html("  🚫🚫 B候補 前の日に +5% 以上：43銘柄（うち1億円以上 36）")
    assert "+5%" in rule and 'color:#1a7f37">+5%' not in rule and "#fff1f0" in rule        # 🚫＝赤い枠・％は塗らない
    fx = M.line_html("  主なペア：ドル円 +0.70%（24時間）・+0.00%（欧州時間）／ユーロドル -0.50%（24時間）")
    assert '<b style="color:#1a7f37">+0.70%</b>' in fx and '<b style="color:#6e7781">+0.00%</b>' in fx and \
           '<b style="color:#cf222e">-0.50%</b>' in fx


def test_ranking_pills():
    h = M.line_html("  24時間：米ドル +0.40%（強い） ＞ 豪ドル +0.00%（中立） ＞ 円 -0.30%（弱い）")
    assert h.count("border-radius:10px") == 3 and "#dafbe1" in h and "#ffebe9" in h and "#eaeef2" in h
    assert "24時間" in h and "米ドル +0.40%" in h
    assert M.ranking("24時間：米ドル +0.40%（強い） ＞ —") is None and M.ranking("材料：FOMC") is None


def test_words_and_boxes():
    h = M.line_html("  地合い：リスクオフ（売られやすい）・確度 高（06:08 作成）")
    assert '<b style="color:#cf222e">リスクオフ</b>' in h and "<b>06:08</b>" in h
    h = M.line_html("  向き：日経225 下向き（中）・金 中立（中）・原油 上向き（高）")
    assert '<b style="color:#cf222e">下向き</b>' in h and '<b style="color:#6e7781">中立</b>' in h and \
           '<b style="color:#1a7f37">上向き</b>' in h
    h = M.line_html("   ・米ドル 強い（高）：米金利の上昇")
    assert "<b>米ドル</b>" in h and '<b style="color:#1a7f37">強い</b>' in h
    assert "強い</b>" not in M.line_html("     → 今朝…（いちばん強い目印・大きい株でも強い）")       # 文の中の「強い」は塗らない
    assert "#f3efff" in M.line_html("  🏦 20:00（あと1.0h）  英中銀 政策金利")
    assert "#fff8e1" in M.line_html("  ⚠️ 発表の数時間前〜は新規を建てない")
    assert "font-size:12px" in M.line_html("  ※ 投資助言ではありません") and "font-size:12px" in M.line_html("       影響: 全銘柄")
    assert "[重要度 高]" in M.line_html("  🇦🇺 [重要度 高] RBA が利上げ") and "#ffebe9" in M.line_html("  🇦🇺 [重要度 高] RBA")
    assert "font-size:17px" in M.line_html("  21:30 JST  米 CPI（9月分）")


def test_section_colors():
    assert M.section_color("【🇯🇵 日本株：寄りで買わない目印（点検表 日本株⑤・前の日の引けでわかるもの）】") == "#b42318"
    assert M.section_color("【📚 研究から分かっていること（日本株・朝の売買）】") == "#57606a"
    assert M.section_color("【⚠️ この時間の注意（点検表の決まりと研究から）】") == "#b42318"
    assert M.section_color("【💱 通貨の強弱（前の日の値動き＋ファンダの見立て）】") == "#00796b"
    assert M.section_color("【🧭 今日のファンダ（AIの朝の見立て・ニュースの要約から）】") == "#6f42c1"
    assert M.section_color("【📊 決算発表（前の平日の引け後・今日・次の平日／主な銘柄だけ）】") == "#8a5a00"
    assert M.section_color("【今日】") == "#0b57d0" and M.section_color("【なにか】") == M.SECTION_DEFAULT


def test_earnings_only_in_its_section():
    jp = "  🇯🇵 10/08(木)＝今日の寄りに効く 引け後 9983 ファーストリテイリング（予定）"
    us = "  🇺🇸 10/08(木)（米国の日付） 寄付前 WMT Walmart"
    sec = "【📊 決算発表（前の平日の引け後・今日・次の平日）】"
    assert '<b style="color:#0b57d0">9983</b> <b style="color:#0288d1">ファーストリテイリング</b>（予定）' in M.line_html(jp, sec)
    assert '<b style="color:#0b57d0">WMT</b> <b style="color:#0288d1">Walmart</b>' in M.line_html(us, sec)
    assert "#0b57d0" not in M.line_html("  🇺🇸 10-13 10:05 FRB 議長が講演（ロイター）", "【📰 米国のニュースの見出し】")


BODY = "\n".join([
    "━━━━━━━━━━━━━━━━━━━━━", "📅 2026-10-09 (Fri) の重要指標", "━━━━━━━━━━━━━━━━━━━━━", "",
    "【今日】", "  🚫 21:30（あと15.0h）  米 CPI <速報> & 改定", "       影響: 全銘柄", "",
    "【🇯🇵 日本株：寄りで買わない目印】", ROW, ROW2, "     …ほか 14銘柄", "",
    "【💱 通貨の強弱】", "  値動き 24時間（±0.05%で強い／弱い）：米ドル +0.40%（強い） ＞ 円 -0.30%（弱い）", "",
    "━━━━━━━━━━━━━━━━━━━━━", "※ これは自分用の確認メールであり投資助言ではありません。"])


def test_page_keeps_every_word_and_escapes():
    page = M.to_html(BODY, "件名 <テスト>")
    assert "<速報>" not in page and "&lt;速報&gt; &amp; 改定" in page and "<title>件名 &lt;テスト&gt;</title>" in page
    seen = text_of(page)
    for line in BODY.split("\n"):
        if line.strip() and not M.SEP.match(line.strip()):
            for w in re.findall(r"[^\s（）＞：]+", line):
                assert w in seen, (w, line)
    assert "background:#1f2a44" in page and "font-size:17px" in page and "<hr" in page   # 題＝紺の帯・最後の区切り＝線
    assert page.count("━") == 0


def test_message_is_text_plus_html():
    msg = M.message("件名", BODY, "a@example.com", "b@example.com")
    assert msg.get_content_type() == "multipart/alternative" and msg["Subject"] == "件名" and msg["To"] == "b@example.com"
    parts = msg.get_payload()
    assert [p.get_content_type() for p in parts] == ["text/plain", "text/html"]
    assert parts[0].get_payload(decode=True).decode("utf-8") == BODY                      # 文字の本文はそのまま
    assert "color:#0b57d0" in parts[1].get_payload(decode=True).decode("utf-8")
    orig = M.to_html
    try:
        M.to_html = lambda *a: 1 / 0                                                   # HTML を作れない＝文字だけで送る
        msg = M.message("件名", BODY, "a@example.com", "b@example.com")
        assert msg.get_content_type() == "text/plain" and msg["From"] == "a@example.com"
    finally:
        M.to_html = orig


def test_size_far_below_gmail_clip():
    rows = [ROW.replace("1.", f"{i}.", 1) for i in range(1, 26)]
    body = "\n".join(["━━━━", "題", "━━━━", "【🇯🇵 日本株】"] + rows + ["", "【🇯🇵 日本株 2】"] + rows + [""] + [BODY] * 3)
    assert len(M.to_html(body).encode("utf-8")) < 80_000                                 # Gmail は約102KB を超えると切る


def test_three_mails_send_through_it():
    for p in ("send_indicator_digest.py", "session_brief.py"):
        src = open(p, encoding="utf-8").read()
        assert "mail_html.message(subject, body, sender, recipient)" in src and 'MIMEText(body, "plain"' not in src, p
        assert "--html-out" in src, p
    import send_indicator_digest as D
    subject, body = D.build(dt.datetime(2026, 10, 9, 6, 30, tzinfo=D.JST))
    page = M.to_html(body, subject)
    assert page.startswith("<!DOCTYPE html>") and len(page.encode("utf-8")) < 90_000
    wf = open(".github/workflows/morning-mail-preview.yml", encoding="utf-8").read()
    assert "--html-out mail.html" in wf and "upload-artifact" in wf


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
