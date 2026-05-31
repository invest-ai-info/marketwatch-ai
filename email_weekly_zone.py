# -*- coding: utf-8 -*-
"""weekly-zone-plan.md を読み、Markdown→HTML に整形して Gmail で送信する。
GitHub Actions（weekly-zone-email.yml、日曜21:30 JST）から実行。
※ルーチンはメール鍵を持てないため、Gmailシークレットを持つ Actions 側で送信する設計。"""
import os
import sys
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate

PLAN = "weekly-zone-plan.md"


def main():
    user = os.environ.get("GMAIL_USER")
    pw = os.environ.get("GMAIL_APP_PASSWORD")
    to = os.environ.get("ALERT_RECIPIENT") or user
    if not (user and pw):
        print("❌ GMAIL_USER / GMAIL_APP_PASSWORD が未設定")
        sys.exit(1)
    try:
        with open(PLAN, encoding="utf-8") as f:
            md = f.read()
    except Exception as e:
        print(f"❌ {PLAN} を読めません: {e}")
        sys.exit(1)

    first = md.split("\n", 1)[0].lstrip("# ").strip()
    subject = "📋 " + (first if first else "週次ゾーン＆指値プラン")

    # Markdown → HTML（テーブル対応）。markdown 未導入なら plain text にフォールバック
    try:
        import markdown
        body_html = markdown.markdown(md, extensions=["tables", "fenced_code", "nl2br", "sane_lists"])
        html = (
            "<html><body style=\"font-family:-apple-system,Segoe UI,sans-serif;"
            "font-size:14px;line-height:1.6;color:#1f2328;max-width:760px;margin:0 auto;padding:8px\">"
            "<style>table{border-collapse:collapse;width:100%;margin:8px 0}"
            "th,td{border:1px solid #d0d7de;padding:5px 8px;font-size:13px;text-align:left}"
            "th{background:#f6f8fa}h1{font-size:18px}h2{font-size:16px;border-bottom:1px solid #eaeef2;padding-bottom:4px}"
            "h3{font-size:14px}</style>"
            f"{body_html}"
            "<hr><p style=\"font-size:12px;color:#6e7781\">※本メールは個人用の分析メモであり投資助言ではありません。"
            "約定しない指値があるのは正常（規律）。SLは必ず置く。最終判断は自己責任で。</p>"
            "</body></html>"
        )
        part = MIMEText(html, "html", "utf-8")
    except Exception as e:
        print(f"（markdown未使用 → plain text 送信）: {type(e).__name__}")
        part = MIMEText(md, "plain", "utf-8")

    msg = MIMEMultipart()
    msg["From"] = user
    msg["To"] = to
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg.attach(part)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
        server.login(user, pw)
        server.sendmail(user, [to], msg.as_string())
    print(f"✅ 週次ゾーンプランを {to} に送信しました: {subject}")


if __name__ == "__main__":
    main()
