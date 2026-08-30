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

# 2026-08-30: index.html の鮮度判定を「JSTの今日と日付が一致するか」から
#   「最終更新からの経過時間」に変更した。
#   旧実装 (page_date < jst_today()) は、このチェック自身が深夜0時 JST をまたぐと
#   必ず誤検知した。朝の更新が来るまでの深夜帯は前日日付が正常だからで、
#   実際 cron '0 11 * * *' (20:00 JST) の回が GitHub 側の遅延で 00:07 / 00:22 JST に
#   走り、2026-08-29・08-30 の2回とも「日付が古い」で issue 化された（サイトは正常）。
#   実測: Update Market News の成功実行の最大間隔は 10.5h（直近60回・2026-08-26〜08-30）。
#   26h は「定時実行の片方が丸ごと来なかった」最悪ケース(≒24h)にも余裕を持たせた値。
#   ⚠️ この閾値を24h未満に下げないこと。上記の最悪ケースで恒常的に誤検知に戻る。
STALE_HOURS = 26

# 2026-08-26 事故: 翻訳バックエンド(Google)が HTTP 500 を返すと deep_translator が
#   エラーページ本文を「翻訳結果」として返し、全ニュース見出しがそれに置換された。
#   結果、AI 投資判断の根拠が「システムエラーのため内容が確認できません」になった。
#   原因が何であれ、この2種類の症状はライブ側から検知できる。
GARBAGE_MARKERS = [
    "Error 500 (Server Error)",
    "That’s an error",
    "That's an error",
    "!!1500",
]
# AI が「入力が壊れている」と訴えている文言（＝上流のニュース取得が死んでいるサイン）
AI_COMPLAINT_MARKERS = ["システムエラー", "内容が確認できません", "エラーを示"]


JST = zoneinfo.ZoneInfo("Asia/Tokyo")


def jst_now() -> datetime.datetime:
    return datetime.datetime.now(JST)


def jst_today() -> datetime.date:
    return jst_now().date()


def parse_updated_at(body: str) -> "datetime.datetime | None":
    """index.html の「最終更新」を JST の datetime にする。読めなければ None。

    例: 最終更新: <span>2026年8月30日 10:47 JST</span>
    2026-07-05: トップページ整理でタグ構造が変わったため、日付の前に任意個のタグ/空白を許容。
    時刻は generate_market_news.py が必ず "%H:%M JST" で出すが、書式が変わっても
    日付だけで動くように任意扱いにしてある。
    """
    m = re.search(
        r"最終更新[:：]\s*(?:<[^>]+>\s*)*(\d{4})年(\d{1,2})月(\d{1,2})日"
        r"(?:\s*(?:<[^>]+>\s*)*(\d{1,2}):(\d{2}))?",
        body,
    )
    if not m:
        return None
    # 時刻が読めないときは 23:59 とみなす＝経過時間を最も短く見積もる。
    # 誤検知を出さない側に倒す（見逃しは最大1日。巻き戻り事故は数日ずれるので拾える）。
    hh = int(m.group(4)) if m.group(4) else 23
    mm = int(m.group(5)) if m.group(5) else 59
    return datetime.datetime(
        int(m.group(1)), int(m.group(2)), int(m.group(3)), hh, mm, tzinfo=JST
    )


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
        updated_at = parse_updated_at(body)
        if updated_at is None:
            errors.append("⚠️ `index.html` 「最終更新」の日付要素が見つからない")
        else:
            age_h = (jst_now() - updated_at).total_seconds() / 3600
            if age_h > STALE_HOURS:
                errors.append(
                    f"🚨 `index.html` の更新が止まっている: 最終更新 "
                    f"`{updated_at.strftime('%Y-%m-%d %H:%M')} JST`"
                    f"（{age_h:.1f}時間前 / 閾値 {STALE_HOURS}h・"
                    f"過去日付への巻き戻り事故と同じ症状）"
                )

        # ① 取得・翻訳のエラーページ本文がそのまま本文に出ていないか
        for marker in GARBAGE_MARKERS:
            if marker in body:
                errors.append(
                    f"🚨 `index.html` に取得/翻訳エラーの文字列が混入: `{marker}` "
                    f"(翻訳バックエンド障害の疑い → Actions ログの「翻訳:」行を確認)"
                )
                break

        # ② AI 投資判断の根拠が「入力が壊れている」と訴えていないか
        for m2 in re.finditer(r'class="ai-reason"[^>]*>(.*?)</div>', body, re.S):
            reason = re.sub(r"<[^>]+>", "", m2.group(1)).strip()
            hit = next((w for w in AI_COMPLAINT_MARKERS if w in reason), None)
            if hit:
                errors.append(
                    f"🚨 `index.html` AI 投資判断の根拠が入力不良を訴えている（`{hit}`）: "
                    f"{reason[:60]}…（上流のニュース取得/翻訳が死んでいる疑い）"
                )
                break

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
