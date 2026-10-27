"""警察庁の詐欺の統計に新しい公表が出たら、Kindle の本の数字を入れ替える時期をメールで知らせる。2026-10-27 新設。

なぜ：Kindle『投資詐欺から自分と家族を守れる人になる』の内容紹介で「新しい統計が公表されたら、数字を見直して
更新していきます」と約束した（オーナー 2026-10-27「作ってください」）。本で使っている警察庁の公表より新しい
「年の暫定値・確定値」「上半期の暫定値」が出たら、npa-stats-watch.yml（月2回）がメールを送る。

- 月ごとの途中経過（「令和8年8月末・暫定値」など）は数えない。本は年と上半期の数字だけを使う
- 本を直したら、下の BOOK_USES を新しい公表に書き換える。書き換えるまで、メールは月2回届き続ける（忘れ防止）
- ページの形が変わって公表を1件も読めなかったとき、新しい公表があるのにメールを送れなかったときは exit 1
  （ワークフローが赤になり、見張り番が気づく）

実行:  python npa_stats_watch.py      テスト:  python tests/test_npa_stats_watch.py
"""
import os
import re
import sys
import time
import urllib.request

URL = "https://www.npa.go.jp/publications/statistics/sousa/sagi.html"

# 本でいま使っている、いちばん新しい公表（2026-10-27 時点＝令和8年上半期・暫定値。年の数字は令和7年・確定値）
BOOK_USES = (8, "上半期", "暫定値")

PERIOD_ORDER = {"上半期": 0, "年": 1}
KIND_ORDER = {"暫定値": 0, "確定値": 1}
_Z2H = str.maketrans("０１２３４５６７８９", "0123456789")
_LABEL = re.compile(r"令和(元|\d+)年(上半期|\d+月末)?・(暫定値|確定値)")


def parse(html):
    """ページから公表の見出し（年・期間・暫定/確定）を集める。月末の途中経過は除く。"""
    text = re.sub(r"<[^>]+>|\s+", "", html).translate(_Z2H)
    found = set()
    for m in _LABEL.finditer(text):
        period = m.group(2) or "年"
        if period.endswith("月末"):
            continue
        year = 1 if m.group(1) == "元" else int(m.group(1))
        found.add((year, period, m.group(3)))
    return found


def order(pub):
    return (pub[0], PERIOD_ORDER[pub[1]], KIND_ORDER[pub[2]])


def label(pub):
    return f"令和{pub[0]}年{'' if pub[1] == '年' else pub[1]}・{pub[2]}"


def newer_than_book(found):
    return sorted((p for p in found if order(p) > order(BOOK_USES)), key=order)


def fetch(url, tries=3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (npa-stats-watch)"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode("utf-8", errors="replace")
        except Exception as e:  # noqa: BLE001 — 通信の失敗は種類を問わず数回やり直す
            last = e
            time.sleep(5 * (i + 1))
    raise RuntimeError(f"取得に失敗: {last}")


def build_mail(newer):
    names = "／".join(label(p) for p in newer)
    subject = f"📚 警察庁の詐欺の統計に新しい公表（{names}）＝Kindle の本の数字を入れ替える時期です"
    body = f"""警察庁の「特殊詐欺の認知・検挙状況等について」に、本で使っているものより新しい公表が出ました。

新しい公表：{names}
本で使っている公表：{label(BOOK_USES)}（年の数字は令和7年・確定値）
ページ：{URL}

やること（手元のセッションで）
1. research/kindle/psych-scam/PUBLISH_CHECKLIST.md の「数字の更新の予定」を開く
2. 新しい資料の数字で、はじめに・第1章・内容紹介などを入れ替える（calc_examples.py と check_numbers.py の CITED も）
3. check_numbers.py と ../check_listing.py が exit 0 → build_epub.py → KDP で原稿を差し替える
4. 終わったら npa_stats_watch.py の BOOK_USES を新しい公表に書き換える（書き換えるまで、このメールは月2回届きます）

※ 警察庁は令和8年から、SNS型投資・ロマンス詐欺を「特殊詐欺」の手口の1つとして数えています。
  令和7年以前と数え方が変わったところがないか、資料の注意書きを確かめてから入れ替えてください。
"""
    return subject, body


def send_mail(subject, body):
    user, pw = os.environ.get("GMAIL_USER"), os.environ.get("GMAIL_APP_PASSWORD")
    to = os.environ.get("ALERT_RECIPIENT") or user
    if not (user and pw):
        return False
    import smtplib
    from email.mime.text import MIMEText
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"], msg["From"], msg["To"] = subject, user, to
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as s:
        s.login(user, pw)
        s.send_message(msg)
    return True


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    found = parse(fetch(URL))
    if not found:
        print("❌ 公表の見出しを1件も読めなかった＝ページの形が変わった。npa_stats_watch.py の _LABEL を直す")
        return 1
    newest = max(found, key=order)
    print(f"読めた公表 {len(found)} 件・いちばん新しい＝{label(newest)}・本で使っている＝{label(BOOK_USES)}")
    newer = newer_than_book(found)
    if not newer:
        print("新しい公表なし")
        return 0
    print("新しい公表あり：" + "／".join(label(p) for p in newer))
    if not send_mail(*build_mail(newer)):
        print("❌ メールを送れなかった（GMAIL_USER / GMAIL_APP_PASSWORD が無い）")
        return 1
    print("メールを送った")
    return 0


if __name__ == "__main__":
    sys.exit(main())
