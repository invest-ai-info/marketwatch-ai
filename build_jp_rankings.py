# -*- coding: utf-8 -*-
"""build_jp_rankings.py — 日本株 値上がり率/値下がり率 トップ20 ランキングを生成（公開サイト用）。

流動性上位ユニバース（jp-stock-info.json の銘柄＝約400）について、Yahoo chart API（価格のみ・キー不要）で
直近約3ヶ月の終値・出来高を取得し:
  ・前日比% （直近営業日の終値 / その前の終値 − 1）
  ・売買代金（直近営業日・その前日の2日分＝終値×出来高、億円）
  ・相対出来高（直近営業日の出来高 ÷ 直前20営業日の平均出来高）🆕 2026-07-21 人気急上昇ランキング用
を計算 → 前日比で上位20（値上がり）と下位20（値下がり）、相対出来高で上位20（人気急上昇）を抽出。
人気急上昇は売買代金 HOT_MIN_TURNOVER 億円以上のみ（薄商い銘柄の見かけ倍率と操作されやすい軽い銘柄を公開面から除外）。
銘柄名/業種は静的 jp-stock-info.json から join（JPX の一覧・キー不要）。
🔁 2026-11-20 赤字・黒字の印（akaji＝J-Quants の財務から決めた印）は出さない（J-Quants の案内で第三者への表示は ×・
   弁護士の相談メモ⑪ の B）。jp-stock-info.json からも外した。

🆕 2026-11-19 株式分割の補正（jp_splits.py）: キーエンス（6861）の 1→5 の分割の日（11/18）に、Yahoo の日足が最後の1本だけ
分割後の値で、値下がり1位に −79.7%（本当は +1.5%）・人気急上昇に出来高 3.9倍（本当は売買代金ほぼ同じ）が出た。
→ `&events=split` で分割を取り、Yahoo がまだ直していない切れ目より前の足を分割後の単位に直してから前日比と相対出来高を出す。
  分割の日付の前後で、直せなかった極端な前日比（1.5倍超・1/1.5未満）の銘柄は一覧に入れない（split_suspect）。

出力: jp-rankings.json（公開サイト hot-assets.html の最上段が読む）。
⚠️ これは『事実の市場データ』であり、買い/売り推奨ではない（描画側に教育注記＋免責を付す）。
⚠️ 罠フラグ（仕手的形状の判定）はここに入れない＝公開しない方針（オーナー決定 2026-07-21）。
   罠側の検証は非公開の進化ループ（research/hypothesis_queue.md の Q22）で実施する。
"""
import os
import sys
import json
import time
import datetime
import urllib.request

import jp_splits   # 🆕 2026-11-19 株式分割の補正（Yahoo が一部の足しか直していない日の前日比・相対出来高の狂い）

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
SETTLE_JST = (16, 0)      # 東証の大引け15:30＋余裕。これより前に取れた「当日」のバーは場中の値＝書かない
JST = datetime.timezone(datetime.timedelta(hours=9))


def modal_date(dates):
    """銘柄ごとの「最終バー日付」の最頻値を返す（同数なら新しい方）。

    Yahoo は同じ瞬間でも銘柄・エッジによって最終営業日が1日ずれることがある。
    その混在をそのままランキングにすると**別々の日の騰落率を1つの表に混ぜる**ので、
    多数派の日付を「その回の営業日」と決め、少数派の銘柄は落とす（下の main を参照）。
    """
    if not dates:
        return ""
    counts = {}
    for d in dates:
        counts[d] = counts.get(d, 0) + 1
    return sorted(counts.items(), key=lambda kv: (kv[1], kv[0]))[-1][0]


def is_regression(asof, prev):
    """今回取れた営業日が前回より古ければ True（＝書かずに次の回へ委ねる）。純関数。"""
    return bool(prev) and bool(asof) and asof < prev


def is_unsettled(asof, now_jst):
    """当日のバーを大引け前（SETTLE_JST より前）に取った＝場中の値なら True。純関数。

    🆕 2026-09-25: routine の push でも起動するようにした（jp-rankings.yml）ので、起動時刻が
    こちらの管理外になった。場中に走っても「2026-09-25 終値」と書いて途中の値を出さないためのガード。
    """
    return bool(asof) and asof == now_jst.date().isoformat() and (now_jst.hour, now_jst.minute) < SETTLE_JST


def previous_asof(path):
    """既存 jp-rankings.json の asof（無ければ ""）。巻き戻し防止の基準に使う。"""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f).get("asof") or ""
    except Exception:
        return ""


def sector_summary(rows):
    """全銘柄の前日比から (breadth, sectors) を返す。純関数。🆕 2026-09-23 トップの「業種の強弱」用。

    breadth = {"up": 値上がり数, "down": 値下がり数, "flat": 変わらず数}
    sectors = [{"sector", "n", "avg"(単純平均), "up"(上昇数)}] を avg の高い順。
    ⚠️ 東証の業種別指数（時価総額加重）とは別物＝表示側でそう明記する。
       少数銘柄の業種は1社の値動きで順位が決まるので、足切りは表示側（build_sector_panel）で行う。
    """
    breadth = {"up": 0, "down": 0, "flat": 0}
    by = {}
    for r in rows:
        pct = r["pct"]
        breadth["up" if pct > 0 else "down" if pct < 0 else "flat"] += 1
        by.setdefault(r.get("sector") or "その他", []).append(pct)
    sectors = [{"sector": k, "n": len(v), "avg": round(sum(v) / len(v), 4), "up": sum(1 for x in v if x > 0)}
               for k, v in by.items()]
    sectors.sort(key=lambda x: x["avg"], reverse=True)
    return breadth, sectors


def parse_chart(d):
    """Yahoo chart の result → (closes[], vols[], 最終営業日ISO, splits, 直した切れ目[], 単位のずれが未確定か)。終値が2本未満なら None。純関数。

    🆕 2026-11-19 株式分割の補正: Yahoo がまだ直していない切れ目より前の足を分割後の単位に直す
    （値段 ÷倍率・出来高 ×倍率）。直していない切れ目が無ければ（ふつうの形）値はそのまま。
    """
    q = d["indicators"]["quote"][0]
    ts, closes, vols = d.get("timestamp") or [], q.get("close") or [], q.get("volume") or []
    rows = [(t, c, v) for t, c, v in zip(ts, closes, vols) if c is not None]
    if len(rows) < 2:
        return None
    last_date = datetime.datetime.fromtimestamp(rows[-1][0], datetime.timezone.utc).strftime("%Y-%m-%d")
    dates = [datetime.datetime.fromtimestamp(t, JST).date().isoformat() for t, _, _ in rows]
    splits = jp_splits.parse_splits(d)
    raw = [float(c) for _, c, _ in rows]
    closes, vols, breaks = jp_splits.adjust_close_volume(
        dates, raw, [None if v is None else float(v) for _, _, v in rows], splits)
    return closes, vols, last_date, splits, breaks, jp_splits.unit_pending(dates, raw, splits)


def fetch_2day(code):
    """直近約3ヶ月の parse_chart の形（終値・出来高・最終営業日・分割・直したところ・単位のずれが未確定か）を Yahoo から取得。失敗時 None。
    （関数名は互換のまま。2026-07-21 に range=7d→3mo へ拡張＝相対出来高の基準20日分を確保。
      2026-11-19 に &events=split を付けて株式分割を補正＝parse_chart）"""
    u = f"https://query1.finance.yahoo.com/v8/finance/chart/{code}.T?range=3mo&interval=1d&events=split"
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    return parse_chart(json.load(urllib.request.urlopen(req, timeout=20))["chart"]["result"][0])


def split_suspect(closes, last_date, splits):
    """分割の日付の前後なのに、直したあとも前日比が極端（1.5倍超・1/1.5未満）＝Yahoo の値か倍率が合っていない。純関数。

    そういう銘柄は一覧に入れない（分割と重ならない極端な値動きは本物でありうるので入れる）。
    """
    c1, c0 = float(closes[-1]), float(closes[-2])
    if c0 <= 0 or not jp_splits.near(last_date, splits):
        return False
    return not (1 / jp_splits.MAX_MOVE <= c1 / c0 <= jp_splits.MAX_MOVE)


def stock_row(code, meta, closes, vols, last_date):
    """1銘柄の行（前日比・売買代金・相対出来高）。closes/vols は分割の補正済み（parse_chart）。前の終値が0以下なら None。純関数。"""
    c1, c0 = float(closes[-1]), float(closes[-2])      # 直近 / その前
    if c0 <= 0:
        return None
    pct = c1 / c0 - 1.0
    v1 = float(vols[-1]) if vols[-1] is not None else 0.0
    v0 = float(vols[-2]) if vols[-2] is not None else 0.0
    # 🆕 相対出来高＝当日出来高 ÷ 直前20営業日の平均出来高（当日を含まない・0/欠損日は除外）
    base = [float(v) for v in vols[-(HOT_BASE_DAYS + 1):-1] if v]
    relvol = round(v1 / (sum(base) / len(base)), 1) if (len(base) >= HOT_MIN_BASE and v1 > 0) else None
    return {
        "_last_date": last_date,
        "code": code, "name": meta.get("name", ""), "sector": meta.get("sector", ""),
        "price": round(c1, 1), "pct": round(pct, 4),
        "turnover_d1": round(c1 * v1 / 1e8, 1),   # 直近営業日の売買代金（億円）
        "turnover_d2": round(c0 * v0 / 1e8, 1),   # その前日の売買代金（億円）
        "relvol": relvol,                          # 相対出来高（倍・基準不足はNone）
    }


def main():
    info = json.load(open(INFO, encoding="utf-8"))
    stocks = info["stocks"]
    rows, fail, asof = [], 0, ""
    fixed, suspect = [], []   # 🆕 2026-11-19 株式分割を直した銘柄／直せず一覧から外した銘柄（ログ用）
    codes = list(stocks.keys())
    for i, code in enumerate(codes):
        try:
            res = fetch_2day(code)
        except Exception:
            res = None
        if not res:
            fail += 1
            continue
        closes, vols, last_date, splits, breaks, pending = res
        if breaks:
            fixed.append(f"{code}（" + "・".join(f"{d} より前 ÷{r:g}" for d, r in breaks) + "）")
        if pending or split_suspect(closes, last_date, splits):
            suspect.append(code)
        else:
            row = stock_row(code, stocks[code], closes, vols, last_date)
            if row is not None:
                rows.append(row)
        if (i + 1) % 100 == 0:
            print(f"  ...{i+1}/{len(codes)} fail={fail}", flush=True)
        time.sleep(0.07)

    if fixed:
        print(f"🔧 株式分割の補正（Yahoo がまだ直していない足を分割後の単位に）{len(fixed)}銘柄: " + ", ".join(fixed[:10])
              + (" ほか" if len(fixed) > 10 else ""))
    if suspect:
        print(f"⚠️ 分割の日付の前後で前日比が極端なまま・または単位のずれ（10倍・100倍）が戻っていない＝一覧から外した {len(suspect)}銘柄: "
              + ", ".join(suspect[:10]))

    # 🆕 2026-08-29 日付の混在ガード＋巻き戻しガード。
    #   実害: 8/29 04:34 JST の回（cron が 17時台→早朝へずれた回）は Yahoo がまだ 8/28 を
    #   返さず asof=2026-08-27 で完走し、ライブが1営業日ぶん古いまま「成功」と報告されていた。
    #   ① 最終バー日付の多数派を asof と決め、少数派の銘柄は落とす（別の日の騰落率を混ぜない）
    #   ② その asof が前回より古ければ**書かずに終了**＝次のバックアップ回に委ねる（前回分を温存）
    asof = modal_date([r["_last_date"] for r in rows])
    mixed = [r for r in rows if r["_last_date"] != asof]
    if mixed:
        print(f"⚠️ 最終営業日が混在（多数派 {asof} 以外 {len(mixed)}銘柄）＝別の日の騰落率を混ぜないため除外: "
              + ", ".join(f"{r['code']}({r['_last_date']})" for r in mixed[:5])
              + (" ほか" if len(mixed) > 5 else ""))
        rows = [r for r in rows if r["_last_date"] == asof]
    for r in rows:
        r.pop("_last_date", None)

    prev = previous_asof(OUT)
    if is_regression(asof, prev):
        print(f"⏸ 取得できた最終営業日 {asof} が前回 {prev} より古い（上流がまだ当日分を返していない）＝"
              f"jp-rankings.json を更新せず終了。次の回に委ねる（前回分を温存）")
        return
    now_jst = datetime.datetime.now(JST)
    if is_unsettled(asof, now_jst):
        print(f"⏸ 取得できた最終営業日 {asof} は今日で、いま {now_jst:%H:%M} JST＝大引け前後の未確定の値。"
              f"「終値」として書かずに終了（{SETTLE_JST[0]}:{SETTLE_JST[1]:02d} 以降の回に委ねる）")
        return

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
    breadth, sectors = sector_summary(rows)
    payload = {"asof": asof, "universe": len(rows), "gainers": up, "losers": down, "hot": hot,
               "breadth": breadth, "sectors": sectors}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    print(f"✅ {OUT}: as of {asof} / 計算{len(rows)}銘柄(取得失敗{fail}) → 値上がり/値下がり/人気急上昇 各{TOP_N}(人気={len(hot)})")
    print(f"   値上がり1位: {up[0]['name']} {up[0]['pct']:+.1%} / 値下がり1位: {down[0]['name']} {down[0]['pct']:+.1%}")
    if hot:
        print(f"   人気急上昇1位: {hot[0]['name']} 出来高{hot[0]['relvol']}倍 / 代金{hot[0]['turnover_d1']}億円")


if __name__ == "__main__":
    main()
