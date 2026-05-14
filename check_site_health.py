"""
marketwatch-jp.com の 6ページが正常に更新されているかをチェックする。

GitHub Actions から定期実行される想定。異常があれば health_report.md を書き出して
非ゼロ終了する（ワークフロー側で issue が立てられる）。
"""
import datetime
import re
import sys
import zoneinfo

import requests

# Windows コンソール (cp932) でも絵文字を出せるようにする
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BASE = "https://marketwatch-jp.com"
PAGES = [
    "index.html",
    "calendar.html",
    "charts.html",
    "vix.html",
    "market-health.html",
    "hot-assets.html",
]
MIN_BYTES = 5000  # 途中切れHTML検出の閾値
TIMEOUT = 20


def jst_today() -> datetime.date:
    return datetime.datetime.now(zoneinfo.ZoneInfo("Asia/Tokyo")).date()


def check_page(path: str) -> list[str]:
    url = f"{BASE}/{path}"
    errors: list[str] = []

    try:
        r = requests.get(url, timeout=TIMEOUT)
    except Exception as e:
        return [f"❌ `{path}` 取得失敗: {e}"]

    if r.status_code != 200:
        return [f"❌ `{path}` HTTP {r.status_code}"]

    body = r.text
    body_bytes = len(body.encode("utf-8"))
    if body_bytes < MIN_BYTES:
        errors.append(
            f"⚠️ `{path}` サイズ異常: {body_bytes} bytes < {MIN_BYTES}（途中切れの可能性）"
        )

    if path == "index.html":
        # 例: 最終更新: <span>2026年5月6日 22:28 JST</span>
        m = re.search(r"最終更新[:：]\s*<span[^>]*>(\d{4})年(\d{1,2})月(\d{1,2})日", body)
        if not m:
            errors.append("⚠️ `index.html` 「最終更新」の日付要素が見つからない")
        else:
            page_date = datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            today = jst_today()
            if page_date < today:
                delta = (today - page_date).days
                errors.append(
                    f"🚨 `index.html` 日付が古い: ページ表示 `{page_date}`, JST 今日 `{today}` "
                    f"(差分 {delta} 日 / 過去の巻き戻り事故と同じ症状)"
                )

    return errors


def main() -> None:
    all_errors: list[str] = []
    for path in PAGES:
        page_errors = check_page(path)
        all_errors.extend(page_errors)
        status = "✅" if not page_errors else "❌"
        print(f"{status} {path}")
        for e in page_errors:
            print(f"    {e}")

    today = jst_today().isoformat()
    if all_errors:
        report = [
            f"# 🚨 サイト異常検知 ({today} JST)",
            "",
            f"**サイト**: {BASE}",
            f"**チェック実行時刻**: "
            f"{datetime.datetime.now(zoneinfo.ZoneInfo('Asia/Tokyo')).isoformat(timespec='seconds')}",
            "",
            "## 検知された異常",
            "",
        ]
        report.extend(f"- {e}" for e in all_errors)
        report += [
            "",
            "## 復旧手順",
            "",
            "1. GitHub > Actions > **Update Market News** の最新実行ログを確認",
            "2. 失敗していた場合は `Run workflow` ボタンで手動再実行",
            "3. 復旧しない場合: ローカルで `python generate_market_news.py` を実行して原因調査",
            "4. **HTML を手動でローカルから push しないこと**（過去日付に巻き戻る既知の事故あり）",
            "",
            "---",
            "*この issue は health-check ワークフローによって自動作成されました。*",
        ]
        with open("health_report.md", "w", encoding="utf-8") as f:
            f.write("\n".join(report))
        sys.exit(1)

    print(f"\n✅ 全 {len(PAGES)} ページ正常 ({today} JST)")


if __name__ == "__main__":
    main()
