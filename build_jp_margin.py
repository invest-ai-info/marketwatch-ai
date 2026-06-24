# -*- coding: utf-8 -*-
"""build_jp_margin.py — 日本株「信用取引残高（日次）」を JPX 公式 Excel から生成（公開サイト用・キー不要）。

JPX「個別銘柄信用取引残高（日々公表銘柄）」の日次Excel（mtdailyk*.xls）を取得・解析し、
各銘柄の 売残高(信用売り残)/買残高(信用買い残)/前日比/上場比/信用倍率 を抽出 → jp-margin.json。
hot-assets.html の「信用残ウォッチ」セクションが読む。
⚠️ 公式の事実データ（売買推奨ではない）。描画側に「見方」注記＋免責を付す。
※ 日々公表銘柄＝信用残が一定基準を超え取引所が毎日残高を公表する銘柄＝投機的に注目度が高い銘柄群。
"""
import os, sys, re, io, json, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
try:
    import truststore; truststore.inject_into_ssl()
except Exception:
    pass
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "jp-margin.json")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36"
IDX = "https://www.jpx.co.jp/markets/statistics-equities/margin/index.html"

# Excel 列インデックス（mtdailyk のレイアウト・2026-06 確認）
C_NAME, C_MKT, C_TYPE, C_CODE = 3, 4, 5, 6
C_SELL, C_SELL_CHG, C_SELL_PL = 8, 9, 10
C_BUY, C_BUY_CHG, C_BUY_PL = 11, 12, 13


def fetch(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "ja"}), timeout=30).read()


def num(v):
    """Excelセルを float に（'-'/空は None）。"""
    try:
        s = str(v).replace(",", "").strip()
        if s in ("", "-", "nan", "－"):
            return None
        return float(s)
    except Exception:
        return None


def main():
    idx = fetch(IDX).decode("utf-8", "replace")
    m = re.search(r'href="([^"]*mtdaily[^"]*\.xls)"', idx, re.I)
    if not m:
        print("❌ mtdaily リンクが index に無い"); sys.exit(1)
    url = "https://www.jpx.co.jp" + m.group(1)
    dm = re.search(r"(\d{8})", url)
    asof = f"{dm.group(1)[:4]}-{dm.group(1)[4:6]}-{dm.group(1)[6:8]}" if dm else ""
    print("📥", url, "asof", asof)
    df = pd.read_excel(io.BytesIO(fetch(url)), sheet_name=0, header=None)

    rows = []
    for i in range(df.shape[0]):
        code = str(df.iloc[i, C_CODE]).strip()
        if not re.fullmatch(r"\d{5}", code):
            continue
        sell, buy = num(df.iloc[i, C_SELL]), num(df.iloc[i, C_BUY])
        if sell is None and buy is None:
            continue
        name = str(df.iloc[i, C_NAME]).replace("　普通株式", "").replace("　", " ").strip()
        ratio = round(buy / sell, 1) if (sell and sell > 0 and buy is not None) else None  # 信用倍率=買残/売残
        rows.append({
            "code": code[:4], "name": name, "mkt": str(df.iloc[i, C_MKT]).strip(),
            "sell": int(sell) if sell is not None else None,
            "buy": int(buy) if buy is not None else None,
            "sell_chg": int(num(df.iloc[i, C_SELL_CHG]) or 0),
            "buy_chg": int(num(df.iloc[i, C_BUY_CHG]) or 0),
            "sell_pl": num(df.iloc[i, C_SELL_PL]), "buy_pl": num(df.iloc[i, C_BUY_PL]),
            "ratio": ratio,
        })

    out = {"asof": asof, "source": "JPX 個別銘柄信用取引残高（日々公表銘柄）", "count": len(rows), "rows": rows}
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"✅ jp-margin.json 出力 {len(rows)} 銘柄 / asof {asof}")
    # サニティ表示
    by_ratio = sorted([r for r in rows if r["ratio"] and r["buy"]], key=lambda r: -r["ratio"])[:5]
    print("  信用倍率が高い例:", [(r["name"][:8], r["ratio"]) for r in by_ratio])
    by_buypl = sorted([r for r in rows if r["buy_pl"]], key=lambda r: -(r["buy_pl"] or 0))[:5]
    print("  買い残上場比が高い例:", [(r["name"][:8], r["buy_pl"]) for r in by_buypl])


if __name__ == "__main__":
    main()
