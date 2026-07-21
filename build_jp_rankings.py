# -*- coding: utf-8 -*-
"""build_jp_rankings.py — 日本株 値上がり率/値下がり率 トップ20 ランキングを生成（公開サイト用）。

流動性上位ユニバース（jp-stock-info.json の銘柄＝約400）について、Yahoo chart API（価格のみ・キー不要）で
直近約3ヶ月の終値・出来高を取得し:
  ・前日比% （直近営業日の終値 / その前の終値 − 1）
  ・売買代金（直近営業日・その前日の2日分＝終値×出来高、億円）
  ・相対出来高（直近営業日の出来高 ÷ 直前20営業日の平均出来高）🆕 2026-07-21 人気急上昇ランキング用
を計算 → 前日比で上位20（値上がり）と下位20（値下がり）、相対出来高で上位20（人気急上昇）を抽出。
人気急上昇は売買代金 HOT_MIN_TURNOVER 億円以上のみ（薄商い銘柄の見かけ倍率と操作されやすい軽い銘柄を公開面から除外）。
銘柄名/業種/赤字黒字フラグは静的 jp-stock-info.json から join（J-Quants由来＝事前計算済み・キー不要）。

出力: jp-rankings.json（公開サイト hot-assets.html の最上段が読む）。
⚠️ これは『事実の市場データ』であり、買い/売り推奨ではない（描画側に教育注記＋免責を付す）。
⚠️ 罠フラグ（仕手的形状の判定）はここに入れない＝公開しない方針（オーナー決定 2026-07-21）。
   罠側の検証は非公開の進化ループ（research/hypothesis_queue.md の Q22）で実施する。
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
HOT_MIN_TURNOVER = 10.0   # 人気急上昇の流動性フロア（億円）。薄商いの見かけ倍率を公開面に出さない
HOT_BASE_DAYS = 20        # 相対出来高の基準＝直前20営業日平均（当日は含まない）
HOT_MIN_BASE = 15         # 基準日数がこれ未満（新規上場等）なら相対出来高は算出しない


def fetch_2day(code):
    """直近約3ヶ月の (closes[], vols[], 最終営業日ISO) を Yahoo から取得。失敗時 None。
    （関数名は互換のまま。2026-07-21 に range=7d→3mo へ拡張＝相対出来高の基準20日分を確保）"""
    u = f"https://query1.finance.yahoo.com/v8/finance/chart/{code}.T?range=3mo&interval=1d"
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
        # 🆕 相対出来高＝当日出来高 ÷ 直前20営業日の平均出来高（当日を含まない・0/欠損日は除外）
        base = [float(v) for v in vols[-(HOT_BASE_DAYS + 1):-1] if v]
        relvol = round(v1 / (sum(base) / len(base)), 1) if (len(base) >= HOT_MIN_BASE and v1 > 0) else None
        meta = stocks[code]
        rows.append({
            "code": code, "name": meta.get("name", ""), "sector": meta.get("sector", ""),
            "akaji": meta.get("akaji"), "price": round(c1, 1), "pct": round(pct, 4),
            "turnover_d1": round(c1 * v1 / 1e8, 1),   # 直近営業日の売買代金（億円）
            "turnover_d2": round(c0 * v0 / 1e8, 1),   # その前日の売買代金（億円）
            "relvol": relvol,                          # 相対出来高（倍・基準不足はNone）
        })
        if (i + 1) % 100 == 0:
            print(f"  ...{i+1}/{len(codes)} fail={fail}", flush=True)
        time.sleep(0.07)

    # 🆕 2026-07-03 部分失敗ガード: Yahoo throttle 等で大量失敗した回は、偏った部分集合の
    #   ランキングを「最新」として公開しない（書き込み前に検査・未達は非ゼロexitでcommitさせない）。
    MIN_COVERAGE = 0.8
    coverage = len(rows) / max(len(codes), 1)
    if coverage < MIN_COVERAGE:
        print(f"🚨 取得成功 {len(rows)}/{len(codes)} 銘柄（{coverage:.0%} < {MIN_COVERAGE:.0%}）＝"
              f"ユニバース不足。偏ったランキングになるため jp-rankings.json を更新せず終了（前回分を温存）")
        sys.exit(1)

    up = sorted(rows, key=lambda r: r["pct"], reverse=True)[:TOP_N]
    down = sorted(rows, key=lambda r: r["pct"])[:TOP_N]
    # 🆕 人気急上昇＝相対出来高の上位（流動性フロア付き。罠フラグは公開しない＝Q22で非公開検証）
    hot_pool = [r for r in rows if r.get("relvol") and (r.get("turnover_d1") or 0) >= HOT_MIN_TURNOVER]
    hot = sorted(hot_pool, key=lambda r: r["relvol"], reverse=True)[:TOP_N]
    # rank付与はコピーで行う（同一銘柄がup/down/hotに重複したときrankを共有しないため）
    up = [dict(r, rank=i + 1) for i, r in enumerate(up)]
    down = [dict(r, rank=i + 1) for i, r in enumerate(down)]
    hot = [dict(r, rank=i + 1) for i, r in enumerate(hot)]
    payload = {"asof": asof, "universe": len(rows), "gainers": up, "losers": down, "hot": hot}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    print(f"✅ {OUT}: as of {asof} / 計算{len(rows)}銘柄(取得失敗{fail}) → 値上がり/値下がり/人気急上昇 各{TOP_N}(人気={len(hot)})")
    print(f"   値上がり1位: {up[0]['name']} {up[0]['pct']:+.1%} / 値下がり1位: {down[0]['name']} {down[0]['pct']:+.1%}")
    if hot:
        print(f"   人気急上昇1位: {hot[0]['name']} 出来高{hot[0]['relvol']}倍 / 代金{hot[0]['turnover_d1']}億円")


if __name__ == "__main__":
    main()
