# -*- coding: utf-8 -*-
"""150年チャート用 過去データの焼き込みスクリプト（ローカルで一度だけ実行・SYNC入り）

charts.html の超長期化（2026-07-24 設計合意）のため、過去分の年次データを
静的 `historical-long.json` へ焼き込む。GitHub Actions は毎日この JSON を読み、
asof_year+1 以降だけを Yahoo で接ぎ足す（古いデータを毎日再取得しない）。

データソース（すべて年次・各年の年末値）:
  sp500  1871-1984: Robert Shiller 公開データ (Yale ie_data.xls) の12月値（月中平均）
         1985-2025: Yahoo Finance ^GSPC 年末終値（chart API 直叩き）
         ※Yahoo chart API は ^GSPC を1985年以降しか返さない（期間指定は黙って切り詰め）
  nikkei 1949-2025: FRED NIKKEI225（原データ=日本経済新聞社）年末値
  usdjpy 1949-1970: 固定相場 360円（ブレトンウッズ体制の史実定数）
         1971-2025: FRED DEXJPUS 年末値
  gold   1871-1933: 米公定価格 $20.67/oz（史実定数）
         1934-1967: 米公定価格 $35.00/oz（1934年金準備法、史実定数）
         1968-2025: LBMA PM価格 年末値（1968年3月の金プール崩壊で市場価格が誕生）

FRED はローカルPCから TLS フィンガープリントで遮断されるため、ブラウザ経由で
取得・チェックサム検証済みの `_fred_yearend_cache.json`（ローカル専用）を読む。
ライブ fetch が通る環境ならそちらを優先する。

実行: python build_historical_long.py        （historical-long.json を生成）
      python build_historical_long.py --dry-run（書き込まず内容確認のみ）
"""
import io
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_PATH = os.path.join(SCRIPT_DIR, "historical-long.json")
FRED_CACHE = os.path.join(SCRIPT_DIR, "_fred_yearend_cache.json")

ASOF_YEAR = 2025  # 完結した年までを焼き込む。以降は Actions が Yahoo で接ぎ足す

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MarketWatch-JP/1.0"}

# 米ドルの金公定価格（史実定数）
GOLD_OFFICIAL_2067 = (1871, 1933)   # $20.67/oz
GOLD_OFFICIAL_35 = (1934, 1967)     # $35.00/oz
USDJPY_FIXED_360 = (1949, 1970)     # 1ドル=360円（1949年設定〜1971年ニクソンショック）


def _fetch(url, timeout=60):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def fetch_shiller_dec(first_year, last_year):
    """Shiller ie_data.xls から各年12月の P（S&P Composite, 月中平均）を返す"""
    import pandas as pd
    raw = _fetch("http://www.econ.yale.edu/~shiller/data/ie_data.xls")
    df = pd.read_excel(io.BytesIO(raw), sheet_name="Data", skiprows=7)
    date_col, p_col = df.columns[0], df.columns[1]
    out = {}
    for _, row in df.iterrows():
        try:
            d = float(row[date_col])
            p = float(row[p_col])
        except (TypeError, ValueError):
            continue
        # Date は 1871.01〜1871.12 形式（1871.1 は10月）。12月だけ拾う
        if f"{d:.2f}".endswith(".12"):
            year = int(d)
            if first_year <= year <= last_year:
                out[year] = round(p, 2)
    return out


def fetch_yahoo_yearend(symbol, first_year, last_year):
    """Yahoo chart API 直叩きで年末終値を返す（interval=3mo・Q4バーのclose=年末終値）。
    ローカルの yfinance は不調のため直叩き。^GSPC は1985年以降しか返らない。
    ⚠️ ASOF_YEAR の Q4 が完結してから実行すること（進行中Q4バーのcloseは当日値）"""
    import time
    from datetime import timezone
    sym = urllib.parse.quote(symbol)
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
           f"?period1=0&period2={int(time.time())}&interval=3mo")
    j = json.loads(_fetch(url).decode("utf-8"))
    res = j["chart"]["result"][0]
    out = {}
    for t, c in zip(res["timestamp"], res["indicators"]["quote"][0]["close"]):
        if c is None:
            continue
        d = datetime.fromtimestamp(t, tz=timezone.utc)
        if d.month == 10 and first_year <= d.year <= last_year:
            out[d.year] = round(float(c), 2)
    return out


def load_fred_yearend(series_id, first_year, last_year):
    """FRED 年末値。ライブ fetch → 失敗時は検証済みキャッシュ（_fred_yearend_cache.json）"""
    try:
        raw = _fetch(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}", timeout=30)
        rows = raw.decode("utf-8").strip().splitlines()[1:]
        by_year = {}
        for line in rows:
            d, _, v = line.partition(",")
            if v and v != ".":
                by_year[int(d[:4])] = round(float(v), 2)
        print(f"  {series_id}: ライブ取得 {len(by_year)}年分")
    except Exception as e:
        print(f"  {series_id}: ライブ取得不可（{e}）→ キャッシュ利用")
        with open(FRED_CACHE, encoding="utf-8") as f:
            cache = json.load(f)
        by_year = {int(y): round(rec["val"], 2) for y, rec in cache[series_id]["yearEnd"].items()}
    return {y: v for y, v in by_year.items() if first_year <= y <= last_year}


def fetch_lbma_gold_yearend(last_year):
    """LBMA 金PM価格（USD）の年末値。1968年〜"""
    raw = _fetch("https://prices.lbma.org.uk/json/gold_pm.json")
    entries = json.loads(raw.decode("utf-8"))
    by_year = {}
    for e in entries:  # 日付昇順 → 上書きで年末値が残る
        usd = e["v"][0] if e.get("v") else None
        if usd:
            by_year[int(e["d"][:4])] = round(float(usd), 2)
    return {y: v for y, v in by_year.items() if 1968 <= y <= last_year}


def to_series(by_year):
    years = sorted(by_year)
    return {"dates": [str(y) for y in years], "prices": [by_year[y] for y in years]}


def check_contiguous(name, by_year, first, last):
    missing = [y for y in range(first, last + 1) if y not in by_year]
    assert not missing, f"{name}: 年の欠落 {missing[:5]}..."


def main():
    dry_run = "--dry-run" in sys.argv
    print("📊 150年チャート用 過去データを焼き込み中...")

    # ── sp500 ──
    print("  Shiller ie_data.xls 取得中...")
    sp = fetch_shiller_dec(1871, 1984)
    print(f"  Shiller 12月値: {len(sp)}年分 ({min(sp)}〜{max(sp)})")
    sp_yahoo = fetch_yahoo_yearend("^GSPC", 1985, ASOF_YEAR)
    sp.update(sp_yahoo)
    print(f"  ^GSPC 年末値: {len(sp_yahoo)}年分 ({min(sp_yahoo)}〜{max(sp_yahoo)})")

    # ── nikkei ──
    nk = load_fred_yearend("NIKKEI225", 1949, ASOF_YEAR)

    # ── usdjpy ──
    fx = {y: 360.0 for y in range(USDJPY_FIXED_360[0], USDJPY_FIXED_360[1] + 1)}
    fx.update(load_fred_yearend("DEXJPUS", 1971, ASOF_YEAR))

    # ── gold ──
    gl = {y: 20.67 for y in range(GOLD_OFFICIAL_2067[0], GOLD_OFFICIAL_2067[1] + 1)}
    gl.update({y: 35.0 for y in range(GOLD_OFFICIAL_35[0], GOLD_OFFICIAL_35[1] + 1)})
    lbma = fetch_lbma_gold_yearend(ASOF_YEAR)
    print(f"  LBMA PM 年末値: {len(lbma)}年分 ({min(lbma)}〜{max(lbma)})")
    gl.update(lbma)

    # ── サニティチェック（既知の史実値と突合）──
    check_contiguous("sp500", sp, 1871, ASOF_YEAR)
    check_contiguous("nikkei", nk, 1949, ASOF_YEAR)
    check_contiguous("usdjpy", fx, 1949, ASOF_YEAR)
    check_contiguous("gold", gl, 1871, ASOF_YEAR)
    assert 4.0 < sp[1871] < 5.5, f"sp500 1871={sp[1871]}（Shiller既知値 約4.7 と乖離）"
    assert sp[1932] < sp[1929] * 0.5, "大恐慌の下落が見えない（1932 < 1929の半分 のはず）"
    assert abs(sp[2024] - 5881.63) < 0.5, f"sp500 2024={sp[2024]}（5,881.63 のはず）"
    assert nk[1989] == 38915.87, f"nikkei 1989={nk[1989]}（38,915.87 のはず）"
    assert all(fx[y] == 360.0 for y in range(1949, 1971)), "固定相場360円の区間が壊れている"
    assert fx[2011] == 76.98, f"usdjpy 2011={fx[2011]}（史上最円高年 76.98 のはず）"
    assert gl[1933] == 20.67 and gl[1934] == 35.0, "金公定価格の段差(1934)が壊れている"
    assert 500 < gl[1980] < 700, f"gold 1980={gl[1980]}（1980年末 約590 と乖離）"
    print("  ✅ サニティチェック全通過")

    out = {
        "generated_at": datetime.now().strftime("%Y-%m-%d"),
        "asof_year": ASOF_YEAR,
        "note": "150年チャート用の静的過去データ（年次・年末値）。build_historical_long.py がローカルで一度だけ生成し、GitHub Actions は asof_year+1 以降を Yahoo で接ぎ足す。",
        "sources": {
            "sp500": "1871-1984: Robert Shiller公開データ(Yale ie_data.xls, 12月の月中平均) / 1985-2025: Yahoo Finance ^GSPC 年末終値",
            "nikkei": "1949-2025: FRED NIKKEI225(原データ=日本経済新聞社) 年末値",
            "usdjpy": "1949-1970: 固定相場360円(史実定数) / 1971-2025: FRED DEXJPUS 年末値",
            "gold": "1871-1933: 米公定価格$20.67 / 1934-1967: 米公定価格$35.00 / 1968-2025: LBMA PM価格 年末値",
        },
        "series": {
            "sp500": to_series(sp),
            "nikkei": to_series(nk),
            "usdjpy": to_series(fx),
            "gold": to_series(gl),
        },
    }

    for key, s in out["series"].items():
        print(f"  {key}: {s['dates'][0]}〜{s['dates'][-1]} {len(s['dates'])}点 "
              f"(最初={s['prices'][0]} 最後={s['prices'][-1]})")

    if dry_run:
        print("🔍 --dry-run のため書き込みなし")
        return

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    size = os.path.getsize(OUT_PATH)
    print(f"✅ {os.path.basename(OUT_PATH)} 生成完了 ({size:,} bytes)")


if __name__ == "__main__":
    main()
