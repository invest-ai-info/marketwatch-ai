# -*- coding: utf-8 -*-
"""build_jp_rankings.py — 日本株 値上がり率/値下がり率 トップ20 ランキングを生成（公開サイト用）。

流動性上位ユニバース（jp-stock-info.json の銘柄＝約400）について、Yahoo chart API（価格のみ・キー不要）で
直近2営業日の終値・出来高を取得し:
  ・前日比% （直近営業日の終値 / その前の終値 − 1）
  ・売買代金（直近営業日・その前日の2日分＝終値×出来高、億円）
を計算 → 前日比で上位20（値上がり）と下位20（値下がり）を抽出。
銘柄名/業種/赤字黒字フラグは静的 jp-stock-info.json から join（J-Quants由来＝事前計算済み・キー不要）。

出力: jp-rankings.json（公開サイト hot-assets.html の最上段が読む）。
⚠️ これは『事実の市場データ』であり、買い/売り推奨ではない（描画側に教育注記＋免責を付す）。
"""
import os
import sys
import json
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
try:
    import truststore; truststore.inject_into_ssl()
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
INFO = os.path.join(HERE, "jp-stock-info.json")
OUT = os.path.join(HERE, "jp-rankings.json")
TOP_N = 20


def fetch_2day(code):
    """直近の (closes[], vols[], 最終営業日ISO) を Yahoo から取得。失敗時 None。"""
    u = f"https://query1.finance.yahoo.com/v8/finance/chart/{code}.T?range=7d&interval=1d"
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    d = json.load(urllib.request.urlopen(req, timeout=20))["chart"]["result"][0]
    q = d["indicators"]["quote"][0]
    ts, closes, vols = d.get("timestamp", []), q.get("close", []), q.get("volume", [])
    rows = [(t, c, v) for t, c, v in zip(ts, closes, vols) if c is not None]
    if len(rows) < 2:
        return None
    import datetime as _dt
    last_date = _dt.datetime.fromtimestamp(rows[-1][0], _dt.timezone.utc).strftime("%Y-%m-%d")
    return [r[1] for r in rows], [r[2] for r in rows], last_date


def main():
    info = json.load(open(INFO, encoding="utf-8"))
    stocks = info["stocks"]
    rows, fail, asof = [], 0, ""
    codes = list(stocks.keys())
    for i, code in enumerate(codes):
        try:
            res = fetch_2day(code)
        except Exception:
            res = None
        if not res:
            fail += 1
            continue
        closes, vols, last_date = res
        asof = last_date or asof
        c1, c0 = float(closes[-1]), float(closes[-2])      # 直近 / その前
        if c0 <= 0:
            continue
        pct = c1 / c0 - 1.0
        v1 = float(vols[-1]) if vols[-1] is not None else 0.0
        v0 = float(vols[-2]) if vols[-2] is not None else 0.0
        meta = stocks[code]
        rows.append({
            "code": code, "name": meta.get("name", ""), "sector": meta.get("sector", ""),
            "akaji": meta.get("akaji"), "price": round(c1, 1), "pct": round(pct, 4),
            "turnover_d1": round(c1 * v1 / 1e8, 1),   # 直近営業日の売買代金（億円）
            "turnover_d2": round(c0 * v0 / 1e8, 1),   # その前日の売買代金（億円）
        })
        if (i + 1) % 100 == 0:
            print(f"  ...{i+1}/{len(codes)} fail={fail}", flush=True)
        time.sleep(0.07)

    up = sorted(rows, key=lambda r: r["pct"], reverse=True)[:TOP_N]
    down = sorted(rows, key=lambda r: r["pct"])[:TOP_N]
    for i, r in enumerate(up):
        r["rank"] = i + 1
    for i, r in enumerate(down):
        r["rank"] = i + 1
    payload = {"asof": asof, "universe": len(rows), "gainers": up, "losers": down}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    print(f"✅ {OUT}: as of {asof} / 計算{len(rows)}銘柄(取得失敗{fail}) → 値上がり/値下がり 各{TOP_N}")
    print(f"   値上がり1位: {up[0]['name']} {up[0]['pct']:+.1%} / 値下がり1位: {down[0]['name']} {down[0]['pct']:+.1%}")


if __name__ == "__main__":
    main()
