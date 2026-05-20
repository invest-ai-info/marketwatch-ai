"""
import_my_trades.py
───────────────────────────────────────
Google フォーム → Google スプレッドシートに記録された取引データを
公開 CSV URL 経由で取得し、my-trades.json に変換する。

セットアップ手順（MY_TRADES_SETUP.md 参照）:
1. Google フォームを作成（取引情報を入力するフォーム）
2. 回答先 Google スプレッドシートを「ウェブに公開」→ CSV 形式の URL を取得
3. その URL を MY_TRADES_CSV_URL 環境変数または下記の DEFAULT_URL に設定
4. GitHub Actions で 1 時間ごとに実行

CSV 想定列（フォーム項目順）:
  タイムスタンプ / 銘柄 / 売買 / エントリー価格 / ロット / SL / TP / 取引種別 / メモ
  + 決済時: 決済価格 / 決済日時
"""
import os
import sys
import csv
import json
import urllib.request
from datetime import datetime, timezone, timedelta
from io import StringIO

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

JST = timezone(timedelta(hours=9))
TRADES_FILE = "my-trades.json"
DEFAULT_URL = ""  # ここにスプレッドシートの公開 CSV URL を貼っても OK


def fetch_csv(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", "replace")


def parse_jp_datetime(s):
    """Google フォームのタイムスタンプは YYYY/MM/DD HH:MM:SS 形式が一般的"""
    if not s:
        return None
    for fmt in ("%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M"):
        try:
            dt = datetime.strptime(s.strip(), fmt)
            return dt.replace(tzinfo=JST).isoformat(timespec="seconds")
        except ValueError:
            continue
    return s  # フォーマット不明はそのまま返す


def to_float(s):
    try:
        return float(str(s).replace(",", "").strip())
    except Exception:
        return None


def convert_rows(rows):
    """CSV 行 → 取引レコード dict のリスト"""
    trades = []
    for r in rows:
        # 列名は柔軟に取得（フォーム作成時の項目名に合わせて調整）
        entry_at = parse_jp_datetime(r.get("タイムスタンプ") or r.get("Timestamp") or r.get("日時"))
        symbol = (r.get("銘柄") or "").strip()
        direction = (r.get("売買") or r.get("方向") or "").strip()
        # "買い" / "売り" / "ロング" / "ショート" を統一
        if direction in ("買い", "ロング", "Long", "long", "L"):
            direction = "ロング"
        elif direction in ("売り", "ショート", "Short", "short", "S"):
            direction = "ショート"

        entry_price = to_float(r.get("エントリー価格") or r.get("Entry"))
        lot = to_float(r.get("ロット") or r.get("数量"))
        sl = to_float(r.get("SL") or r.get("ストップロス"))
        tp = to_float(r.get("TP") or r.get("利確"))
        kind = (r.get("取引種別") or r.get("根拠") or "").strip()
        note = (r.get("メモ") or r.get("コメント") or "").strip()

        exit_price = to_float(r.get("決済価格") or r.get("Exit"))
        exit_at = parse_jp_datetime(r.get("決済日時") or r.get("ExitTime"))

        # P&L 計算
        pnl_pct = None
        if exit_price is not None and entry_price is not None and entry_price != 0:
            if "ショート" in direction:
                pnl_pct = (entry_price - exit_price) / entry_price * 100
            else:
                pnl_pct = (exit_price - entry_price) / entry_price * 100
            pnl_pct = round(pnl_pct, 3)

        status = "closed" if exit_price is not None else "open"

        # ID: 銘柄 + エントリー日時
        id_str = f"{symbol}_{(entry_at or '')[:16].replace(':', '').replace('-', '').replace('T', '_')}"

        trades.append({
            "id": id_str,
            "entry_at": entry_at,
            "symbol": symbol,
            "direction": direction,
            "entry_price": entry_price,
            "lot": lot,
            "stop_loss": sl,
            "take_profit": tp,
            "kind": kind,  # "AI シグナル参考" / "自己判断" / その他
            "note": note,
            "exit_price": exit_price,
            "exit_at": exit_at,
            "pnl_pct": pnl_pct,
            "status": status,
        })
    return trades


def main():
    url = os.environ.get("MY_TRADES_CSV_URL") or DEFAULT_URL
    if not url:
        print("⏭️ MY_TRADES_CSV_URL が未設定のため、import をスキップします")
        # 既存ファイルをそのまま残す
        if not os.path.exists(TRADES_FILE):
            with open(TRADES_FILE, "w", encoding="utf-8") as f:
                json.dump([], f)
        return

    print(f"📥 取引データを CSV から取得中: {url[:80]}...")
    try:
        text = fetch_csv(url)
    except Exception as e:
        print(f"❌ CSV 取得失敗: {type(e).__name__}: {str(e)[:80]}")
        sys.exit(0)  # 失敗してもワークフローは継続

    reader = csv.DictReader(StringIO(text))
    rows = list(reader)
    print(f"  {len(rows)} 行を読み込み")

    trades = convert_rows(rows)
    # 重複排除（ID ベース）
    unique = {}
    for t in trades:
        unique[t["id"]] = t  # 後優先 = 決済情報が反映される
    trades = list(unique.values())

    with open(TRADES_FILE, "w", encoding="utf-8") as f:
        json.dump(trades, f, ensure_ascii=False, indent=2)
    print(f"✅ {TRADES_FILE} に {len(trades)} 件を保存")


if __name__ == "__main__":
    main()
