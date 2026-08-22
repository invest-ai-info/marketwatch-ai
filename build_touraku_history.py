# -*- coding: utf-8 -*-
"""東証プライムの騰落レシオ（値上がり銘柄数／値下がり銘柄数）を日次で集めて
touraku-history.json を更新する。責務はデータ収集と JSON 更新だけ。HTMLは触らない。

⚠️ 2026-08-22 導入の経緯（SESSION_HANDOFF 既存欠陥Aの根本修正）:
  従来は nikkei225jp.com のスクレイピングに失敗すると、TOPIX ETF (1306.T) 単体の
  日次騰落"日数"を騰落"銘柄数"の代わりに使う近似にフォールバックしていた。これは
  種類の違う指標（単一銘柄の時系列自己相関 ≠ 全市場の値上がり/値下がり銘柄数の断面比）で、
  実際に投資判断の色（適正/過熱）が反転するほどズレていた。
  一次ソース側は robots.txt が Disallow している内部JSONにしか正しい値が無く直せないため、
  東証プライム全銘柄の個別終値を持つ J-Quants（既存の非公開研究パイプラインが使っている
  正規契約の有償API）で独立に計算する。

方式: 東証プライム全銘柄の日次終値（J-Quants equities/bars/daily・1コールで全市場）を
  直近の営業日ぶん取得し、前日比で値上がり/値下がり銘柄数を数える。25日ぶん溜まったら
  ratio25 = 25日間の値上がり銘柄数合計 ÷ 25日間の値下がり銘柄数合計 × 100 を算出できる
  （nikkei225jp.com 自身の定義と同じ式）。実測で同サイトの公表値と一致することを確認済み
  （2026-08-21: 自前計算 884勝622敗=116.76% ／ 同日サイト公表 883勝622敗=116.81%）。

保存するのは日次の {date, up, down} だけ（個別銘柄の値は保存しない＝非公開の生データを
公開リポジトリへは出さない。集計値のみが対象。make_jp_stock_info.py と同じ「公開安全な
集計だけを外に出す」方針）。ratio25 は読む側（generate_market_news.py）が都度計算する。

実行:
  python build_touraku_history.py             # 直近数営業日ぶんを取得して追記（毎回・冪等）
  python build_touraku_history.py --backfill  # 直近約4ヶ月を遡って埋める（初回1回だけ）

鍵: market-news-config.json の "jquants_api_key"（ローカル）／
    GitHub Actions では secrets.JQUANTS_API_KEY を環境変数 JQUANTS_API_KEY で渡す。
"""
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.request

JST = dt.timezone(dt.timedelta(hours=9))
HERE = os.path.dirname(os.path.abspath(__file__))
HISTORY_PATH = os.path.join(HERE, "touraku-history.json")
CONFIG_PATH = os.path.join(HERE, "market-news-config.json")
BASE = "https://api.jquants.com/v2/"

RATIO_WINDOW = 25          # 「25日騰落レシオ」の窓
# 通常運転で毎回さかのぼる暦日数。土日・祝日を挟んでも直近の営業日diffが最低1つは
# 取れるだけの余裕を持たせる（前回実行からの間隔が空いても自己修復する）。
STEADY_LOOKBACK_DAYS = 10
# --backfill 時にさかのぼる暦日数。25日窓の計算にすぐ使えるよう、営業日換算で
# 余裕を持って約4ヶ月ぶん集める。
BACKFILL_LOOKBACK_DAYS = 130
# 蓄積点がこれ未満なら、--backfill を付けなくても自動でバックフィル相当のレンジを取りに行く
# （build_health_history.py の SELF_HEAL_MIN_POINTS と同じ考え方）。
# touraku-history.json は SYNC禁忌＝ローカルから push できないため、GitHub Actions に
# JQUANTS_API_KEY を登録した直後の最初の1回で自動的に25日窓ぶん以上を埋めてほしい。
SELF_HEAL_MIN_POINTS = RATIO_WINDOW + 5


def _api_key():
    env = os.environ.get("JQUANTS_API_KEY")
    if env:
        return env
    return json.load(open(CONFIG_PATH, encoding="utf-8"))["jquants_api_key"]


def _get(url, key, timeout=60):
    """429は指数バックオフで再試行、400（休場/範囲外）はNoneを返す。"""
    req = urllib.request.Request(url, headers={"x-api-key": key})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(2 ** attempt)
                continue
            if e.code == 400:
                return None
            raise
    raise RuntimeError(f"rate-limited 6 retries: {url}")


def fetch_prime_codes(key):
    """東証プライム上場銘柄コードの集合を equities/master から取得。"""
    data = _get(BASE + "equities/master", key)
    rows = (data or {}).get("data", [])
    return {row["Code"] for row in rows if row.get("MktNm") == "プライム"}


def fetch_day_closes(date_str, key, codes):
    """1営業日ぶんの終値 {Code: Close}（prime銘柄のみに絞る）。休場/範囲外はNone。"""
    data = _get(BASE + "equities/bars/daily?date=" + date_str, key)
    if data is None:
        return None
    rows = data.get("data", [])
    return {r["Code"]: r["C"] for r in rows if r.get("Code") in codes and r.get("C") is not None}


def calendar_days_back(end_date, n_days):
    """end_date から n_days 暦日ぶんさかのぼった日付文字列を新しい順で返す（土日は除く）。"""
    d = end_date
    out = []
    for _ in range(n_days):
        if d.weekday() < 5:
            out.append(d.isoformat())
        d -= dt.timedelta(days=1)
    return out


def compute_up_down(prev_closes, today_closes):
    """2日分の {Code: Close} から (値上がり銘柄数, 値下がり銘柄数) を数える。"""
    up = down = 0
    for code, c in today_closes.items():
        p = prev_closes.get(code)
        if p is None:
            continue
        if c > p:
            up += 1
        elif c < p:
            down += 1
    return up, down


def merge_points(existing, new):
    """純関数。日付キーで上書きし、日付昇順で返す（何度流しても増えない＝冪等）。"""
    merged = {d: (u, dn) for d, u, dn in (existing or [])}
    for d, u, dn in (new or []):
        merged[d] = (u, dn)
    return [[d, merged[d][0], merged[d][1]] for d in sorted(merged)]


def ratio25(points):
    """直近 RATIO_WINDOW 日ぶんの up/down 合計から25日騰落レシオを計算。
    窓に満たなければ None（正直に「まだ計算できない」を返す）。"""
    if len(points) < RATIO_WINDOW:
        return None
    window = points[-RATIO_WINDOW:]
    up_sum = sum(p[1] for p in window)
    down_sum = sum(p[2] for p in window)
    if down_sum == 0:
        return None
    return round(up_sum / down_sum * 100, 1)


def empty_history():
    return {"updated_at": None, "points": [], "health": {"last_ok": None, "points": 0}}


def load_history(path=HISTORY_PATH):
    """壊れていても・無くても、必ず正しい形の器を返す。"""
    try:
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
    except Exception:
        return empty_history()
    if not isinstance(doc, dict):
        return empty_history()
    base = empty_history()
    base["updated_at"] = doc.get("updated_at")
    base["points"] = [list(p) for p in (doc.get("points") or [])]
    base["health"]["last_ok"] = (doc.get("health") or {}).get("last_ok")
    base["health"]["points"] = len(base["points"])
    return base


def save_history(doc, path=HISTORY_PATH):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))


def collect(lookback_days, key=None):
    """指定した暦日数ぶんさかのぼって {date: {Code: Close}} を取得し、
    連続する営業日ペアごとの (date, up, down) リストを返す（新しい順ではなく古い順）。"""
    key = key or _api_key()
    codes = fetch_prime_codes(key)
    if not codes:
        raise RuntimeError("equities/master からプライム銘柄が0件＝取得失敗の疑い")

    end = dt.datetime.now(JST).date()
    candidates = calendar_days_back(end, lookback_days)  # 新しい順
    closes_by_date = {}
    for d in candidates:
        c = fetch_day_closes(d, key, codes)
        if c:  # 休場(None)や空(0件)は飛ばす
            closes_by_date[d] = c

    ordered_dates = sorted(closes_by_date)  # 古い順
    out = []
    for i in range(1, len(ordered_dates)):
        prev_d, cur_d = ordered_dates[i - 1], ordered_dates[i]
        up, down = compute_up_down(closes_by_date[prev_d], closes_by_date[cur_d])
        if up + down > 0:
            out.append((cur_d, up, down))
    return out, len(codes)


def main():
    backfill = "--backfill" in sys.argv
    doc = load_history()
    if backfill or len(doc["points"]) < SELF_HEAL_MIN_POINTS:
        lookback = BACKFILL_LOOKBACK_DAYS
    else:
        lookback = STEADY_LOOKBACK_DAYS

    try:
        new_points, n_codes = collect(lookback)
    except Exception as e:
        print(f"  NG touraku: {type(e).__name__}: {str(e)[:120]}")
        # 失敗時は前回状態のまま保存し直さない（JSONを壊れた形で上書きしない）
        return

    doc["points"] = merge_points(doc["points"], new_points)
    doc["health"]["points"] = len(doc["points"])
    if doc["points"]:
        doc["health"]["last_ok"] = doc["points"][-1][0]
    doc["updated_at"] = dt.datetime.now(JST).strftime("%Y-%m-%d")

    save_history(doc)
    r25 = ratio25(doc["points"])
    print(f"saved: {HISTORY_PATH}")
    print(f"  プライム銘柄数: {n_codes}")
    print(f"  points: {len(doc['points'])}件（最新 {doc['points'][-1] if doc['points'] else '-'}）")
    print(f"  現在の25日騰落レシオ: {r25 if r25 is not None else 'N/A（データ不足）'}")


if __name__ == "__main__":
    main()
