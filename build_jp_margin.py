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


# 🚨 2026-09-28: JPX が 9/25 公表分から Excel を .xls（mtdailyk2026092400.xls）→ .xlsx（20260925_mtdaily.xlsx）
#    に変えた。旧版は `\.xls"` 決め打ちでリンクを見つけられず「❌ mtdaily リンクが index に無い」で止まり、
#    ワークフロー側は non-fatal なので緑のまま、サイトの信用残は 9/24 のまま残った。列の並びは同じだった。
#    → 両方の拡張子を受け、.xlsx を優先する（.xlsx を読むには openpyxl が要る＝jp-rankings.yml で入れる）。
LINK_RE = re.compile(r'href="([^"]*mtdaily[^"]*\.xlsx?)"', re.I)
# 株式コード欄は5桁（4桁＋末尾0）。2024年からの英字入りコード（例 278A0）も数える（旧版は数字だけで約12銘柄が漏れていた）
CODE_RE = re.compile(r"\d{3}[0-9A-Z]\d")


def find_excel_link(html):
    """index の HTML から日次 Excel の URL と asof（YYYY-MM-DD）を返す（純関数）。無ければ (None, "")。"""
    links = LINK_RE.findall(html)
    if not links:
        return None, ""
    links.sort(key=lambda h: not h.lower().endswith(".xlsx"))   # .xlsx を優先
    href = links[0]
    url = href if href.startswith("http") else "https://www.jpx.co.jp" + href
    dm = re.search(r"(20\d{6})", href.rsplit("/", 1)[-1])      # 日付はファイル名から（フォルダ名の数字を拾わない）
    asof = f"{dm.group(1)[:4]}-{dm.group(1)[4:6]}-{dm.group(1)[6:8]}" if dm else ""
    return url, asof


def parse_rows(df):
    """Excel（header=None で読んだ DataFrame）から銘柄の行を取り出す（純関数）。"""
    rows = []
    for i in range(df.shape[0]):
        code = str(df.iloc[i, C_CODE]).strip()
        if not CODE_RE.fullmatch(code):
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
    return rows


def main():
    idx = fetch(IDX).decode("utf-8", "replace")
    url, asof = find_excel_link(idx)
    if not url:
        print("❌ mtdaily リンクが index に無い"); sys.exit(1)
    print("📥", url, "asof", asof)
    df = pd.read_excel(io.BytesIO(fetch(url)), sheet_name=0, header=None)
    rows = parse_rows(df)
    if not rows:
        # 列の並びが変わった等。空の JSON で前回の正しいデータを上書きしない
        print("❌ 銘柄の行が0件（Excel の列の並びが変わった可能性）＝ jp-margin.json は書き換えない"); sys.exit(1)

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
