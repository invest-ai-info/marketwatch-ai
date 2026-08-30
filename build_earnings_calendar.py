# -*- coding: utf-8 -*-
"""build_earnings_calendar.py — 主要企業の決算予定を earnings-calendar.json に生成

- 米国（US）: Nasdaq 決算カレンダー API から主要銘柄の次回決算日を自動取得
    https://api.nasdaq.com/api/calendar/earnings?date=YYYY-MM-DD （要 User-Agent）
    今日から約 LOOKAHEAD_DAYS 営業日を走査し、US_TICKERS に一致する行を収集。
- 日本（JP）: JP_CURATED は**銘柄リスト**として使い、日付は yfinance で毎回更新する
    （2026-08-30 まではここが日付ごと手書きで、放置されて20件すべて過去日になっていた）
- フォールバック（US/JP 共通）: yfinance
    Nasdaq API はメガキャップを返さないことがある（2026-08-30 実測で AAPL/MSFT/GOOGL/
    AMZN/META/TSLA が丸ごと欠落＝20銘柄中9件しか取れず、うち3件は過去日だった）。
    同時刻に yfinance は同じ銘柄を8/8で返したので、取れなかったぶんだけ補う。
    ⚠️ **出力先はこの earnings-calendar.json ひとつに保つこと。**別ファイルを作ると
    「台帳が2つあって片方だけ死ぬ」形になる（economic-events.json で実際に起きた）。
    ⚠️ ローカルPCでは curl_cffi が CA証明書を見つけられず yfinance が動かない。Actions で測る。

出力: earnings-calendar.json {updated, note, us:[...], jp:[...]}
generate_market_news.py がこれを読んで calendar.html に決算セクションを描画する（取得はしない）。

使い方: python build_earnings_calendar.py        （earnings-calendar.json を生成/更新）
        python build_earnings_calendar.py --dry  （JSON を書かず内容を表示）
"""
import os
import sys
import json
import time
import datetime
import urllib.request
import urllib.error

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "earnings-calendar.json")
DRY = "--dry" in sys.argv
LOOKAHEAD_DAYS = 95  # 今日から何日先まで走査するか（NVDA/AVGO等の遅い決算期もカバー）
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")

# 米国の主要銘柄（メーカー＋メガキャップ＋金融）。日本人投資家が注目する大型株。
US_TICKERS = {
    "AAPL": "Apple", "MSFT": "Microsoft", "NVDA": "NVIDIA", "GOOGL": "Alphabet（Google）",
    "AMZN": "Amazon", "META": "Meta", "TSLA": "Tesla", "AVGO": "Broadcom",
    "TSM": "TSMC", "AMD": "AMD", "NFLX": "Netflix", "INTC": "Intel",
    "BA": "Boeing", "JPM": "JPMorgan", "V": "Visa", "WMT": "Walmart",
    "KO": "Coca-Cola", "DIS": "Disney", "JNJ": "Johnson & Johnson", "XOM": "ExxonMobil",
}

# Nasdaq がまだ遠い先（2か月超）の日付を掲載していない主要銘柄の暫定日（前年実績ベース）。
# 確定して Nasdaq に載れば自動取得が優先される（fetch_us が拾ったらフォールバックは使わない）。
US_FALLBACK = {
    "NVDA": {"date": "2026-08-26", "time": "引け後"},  # 前年Q2=2025-08-27(水)
    "AVGO": {"date": "2026-09-03", "time": "引け後"},  # 前年Q3=2025-09-04(木)
    "WMT":  {"date": "2026-08-20", "time": "寄付前"},  # 前年Q2=2025-08-21(木)
}

# 日本の主要銘柄の決算発表「予定」日（キュレーション。四半期ごとに更新）。
# code=証券コード, name=日本語社名, time=時間帯（"寄付前"/"引け後"/"—"）, tentative=予定(未確定)か
# 2026-06-26 調査（次回＝2027年3月期 第1四半期, 4-6月）。確定3社=任天堂/NTT/ファストリテ、
# 他17社は前年同期の実績発表日からの推定（tentative=True）。7月入り後に各社IRで確定値に更新する。
JP_CURATED = [
    {"code": "4063", "name": "信越化学工業", "date": "2026-07-23", "time": "引け後", "tentative": True},
    {"code": "6861", "name": "キーエンス", "date": "2026-07-29", "time": "引け後", "tentative": True},
    {"code": "6981", "name": "村田製作所", "date": "2026-07-29", "time": "引け後", "tentative": True},
    {"code": "8035", "name": "東京エレクトロン", "date": "2026-07-30", "time": "引け後", "tentative": True},
    {"code": "6501", "name": "日立製作所", "date": "2026-07-30", "time": "引け後", "tentative": True},
    {"code": "6902", "name": "デンソー", "date": "2026-07-30", "time": "場中", "tentative": True},
    {"code": "4502", "name": "武田薬品工業", "date": "2026-07-30", "time": "引け後", "tentative": True},
    {"code": "8316", "name": "三井住友フィナンシャルグループ", "date": "2026-07-31", "time": "引け後", "tentative": True},
    {"code": "9433", "name": "KDDI", "date": "2026-08-03", "time": "引け後", "tentative": True},
    {"code": "8058", "name": "三菱商事", "date": "2026-08-04", "time": "引け後", "tentative": True},
    {"code": "6098", "name": "リクルートホールディングス", "date": "2026-08-05", "time": "引け後", "tentative": True},
    {"code": "6367", "name": "ダイキン工業", "date": "2026-08-05", "time": "引け後", "tentative": True},
    {"code": "7203", "name": "トヨタ自動車", "date": "2026-08-06", "time": "場中", "tentative": True},
    {"code": "6758", "name": "ソニーグループ", "date": "2026-08-06", "time": "—", "tentative": True},
    {"code": "9984", "name": "ソフトバンクグループ", "date": "2026-08-06", "time": "—", "tentative": True},
    {"code": "7267", "name": "ホンダ（本田技研）", "date": "2026-08-06", "time": "引け後", "tentative": True},
    {"code": "7974", "name": "任天堂", "date": "2026-08-06", "time": "引け後", "tentative": False},
    {"code": "9432", "name": "NTT", "date": "2026-08-06", "time": "場中", "tentative": False},
    {"code": "8306", "name": "三菱UFJフィナンシャル・グループ", "date": "2026-08-07", "time": "引け後", "tentative": True},
    {"code": "9983", "name": "ファーストリテイリング", "date": "2026-07-09", "time": "引け後", "tentative": False},
]


def _map_time(t):
    if t == "time-pre-market":
        return "寄付前"
    if t == "time-after-hours":
        return "引け後"
    return "時間未定"


def fetch_us():
    """今日から LOOKAHEAD_DAYS の平日を走査し、US_TICKERS の次回決算日を収集。"""
    found = {}  # ticker -> {date,ticker,name,time}
    today = datetime.date.today()
    for i in range(LOOKAHEAD_DAYS):
        if len(found) >= len(US_TICKERS):
            break
        d = today + datetime.timedelta(days=i)
        if d.weekday() >= 5:  # 土日は決算なし
            continue
        ds = d.isoformat()
        url = f"https://api.nasdaq.com/api/calendar/earnings?date={ds}"
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.load(resp)
        except Exception as e:
            print(f"  ⚠️ {ds}: 取得失敗 {e}")
            continue
        rows = ((data or {}).get("data") or {}).get("rows") or []
        for row in rows:
            sym = row.get("symbol")
            if sym in US_TICKERS and sym not in found:
                found[sym] = {
                    "date": ds,
                    "ticker": sym,
                    "name": US_TICKERS[sym],
                    "time": _map_time(row.get("time")),
                }
        time.sleep(0.25)  # API に優しく
    return sorted(found.values(), key=lambda x: (x["date"], x["ticker"]))


def _yf_next_earnings(symbol, exch_tz):
    """yfinance で「次の未来の決算日時」を1件返す。取れなければ None。

    Nasdaq API が返さない銘柄の穴埋め専用。時刻は取引所の現地時間に直してから
    寄付前/場中/引け後を判定する（JSTのまま判定すると米株が全部「寄付前」になる）。
    """
    try:
        import yfinance as yf
        import datetime as _dt
        import zoneinfo
        tz = zoneinfo.ZoneInfo(exch_tz)
        now = _dt.datetime.now(tz)
        df = yf.Ticker(symbol).get_earnings_dates(limit=12)
        if df is None or not len(df):
            return None
        cand = []
        for idx in df.index:
            try:
                ts = idx.to_pydatetime()
            except Exception:
                continue
            if ts.tzinfo is None:      # 時刻の裏が取れない行は使わない（推測しない）
                continue
            local = ts.astimezone(tz)
            if local >= now:
                cand.append(local)
        if not cand:
            return None
        return min(cand)
    except Exception:
        return None


def _session_label(local_dt, open_h, open_m, close_h):
    """取引所の現地時刻から 寄付前 / 場中 / 引け後 を決める。"""
    mins = local_dt.hour * 60 + local_dt.minute
    if mins < open_h * 60 + open_m:
        return "寄付前"
    if mins >= close_h * 60:
        return "引け後"
    return "場中"


def main():
    print("📊 決算カレンダー生成")
    us = fetch_us()
    fetched = {e["ticker"] for e in us}
    # Nasdaq 未掲載の主要銘柄はフォールバック暫定日（前年実績ベース）で補完
    for tk, fb in US_FALLBACK.items():
        if tk in US_TICKERS and tk not in fetched:
            us.append({"date": fb["date"], "ticker": tk, "name": US_TICKERS[tk],
                       "time": fb["time"], "tentative": True})
    # Nasdaq も暫定日も無い銘柄を yfinance で補う（メガキャップがここで埋まる）
    yf_filled = []
    for tk in sorted(set(US_TICKERS) - {e["ticker"] for e in us}):
        d = _yf_next_earnings(tk, "America/New_York")
        if d:
            us.append({"date": d.date().isoformat(), "ticker": tk, "name": US_TICKERS[tk],
                       "time": _session_label(d, 9, 30, 16), "tentative": True})
            yf_filled.append(tk)
    us = sorted(us, key=lambda x: (x["date"], x["ticker"]))
    missing = sorted(set(US_TICKERS) - {e["ticker"] for e in us})
    print(f"  US: {len(us)}/{len(US_TICKERS)} 件"
          + (f"（自動{len(fetched)}＋暫定{len(us) - len(fetched)}）" if len(us) > len(fetched) else "（全自動）")
          + (f"＋yfinance{len(yf_filled)}" if yf_filled else "")
          + (f" ／未取得: {', '.join(missing)}" if missing else ""))
    # JP_CURATED は銘柄リストとして使い、日付は毎回 yfinance で更新する。
    # 取れなかった銘柄はキュレーション値のまま残す（消すと一覧から銘柄ごと消えるため）。
    jp, jp_updated = [], 0
    for e in JP_CURATED:
        row = dict(e)
        d = _yf_next_earnings(f"{e['code']}.T", "Asia/Tokyo")
        if d:
            row["date"] = d.date().isoformat()
            row["time"] = _session_label(d, 9, 0, 15)
            row["tentative"] = True
            jp_updated += 1
        jp.append(row)
    jp = sorted(jp, key=lambda x: (x.get("date", "9999"), x.get("code", "")))
    stale = sum(1 for x in jp if x.get("date", "") < datetime.date.today().isoformat())
    print(f"  JP: {len(jp)} 件（yfinance更新 {jp_updated} / キュレーション据置 {len(jp) - jp_updated}"
          + (f" ／過去日のまま {stale} 件" if stale else "") + "）")

    payload = {
        "updated": datetime.date.today().isoformat(),
        "note": "米国はNasdaq＋yfinance、日本はyfinanceで自動取得（取れない銘柄はキュレーション値）。発表予定日は変更の可能性あり。情報提供であり投資助言ではありません。",
        "us": us,
        "jp": jp,
    }
    if DRY:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"  ✅ 書き込み: {OUT}")


if __name__ == "__main__":
    main()
