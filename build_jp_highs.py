# -*- coding: utf-8 -*-
"""build_jp_highs.py — 日本株の「年初来高値・安値」「上場来高値・安値」を更新した銘柄の一覧を作る（公開サイト用）。

2026-10-06 新設（オーナー依頼「日本株の大引けが終わったときに、年初来高値更新・上場来高値更新の銘柄の
一覧表を出来高急増のページに追加してほしい」）。同日夕、オーナー依頼「安値の方も追加して」で安値も。
高値と安値は同じ関数で判定する（違いは見る値と向きだけ＝ytd_extreme / all_time_extreme の side）。

対象＝build_jp_rankings.py と同じ流動性上位ユニバース（jp-stock-info.json の約400銘柄）。
東証の全銘柄ではない（大手の網羅はしない＝サイトの方針。表示側でも「約400銘柄のうち」と書く）。

判定（数字はすべて Yahoo chart API の日足・月足＝キー不要・株式分割は調整済み）:
  ・年初来高値＝その日の高値（ザラ場の高値）が、期間の始まり〜前の営業日までの高値をすべて上回った。
    年初来安値＝その日の安値（ザラ場の安値）が、同じ期間の安値をすべて下回った。同じ値は更新に数えない。
      期間の始まりは日本の新聞・証券会社の慣例どおり **4〜12月＝その年の1月1日／1〜3月＝前の年の1月1日**
      （1〜3月は「昨年来高値」と呼ぶ）。window_start() が単一の真実。
  ・上場来高値（安値）＝その日の高値（安値）が、記録のある全期間（月足 range=max）の高値（安値）をすべて上回った（下回った）。
      🚨 Yahoo の日本株の記録は古い銘柄だと途中からしかない＝1989年のバブル期の高値などとは比べられない。
      そこで**「上場来」と言い切るのは、記録が上場の週から始まっている銘柄だけ**（listing_confirmed）。
      それ以外は「記録のある期間（YYYY年〜）の最高値」として出す。
      見分け方（2026-10-06 の全399銘柄の監査＝`--audit`）: 月足の最初のバーの日付が
        ・月の1日＝Yahoo の記録がその月から始まっただけ（古い銘柄はすべてこれ。2004年以降に始まる古い銘柄もある＝
          日本郵船・川崎重工業・三菱瓦斯化学 2004-12、レーザーテック 2010-03、北洋銀行 2012-10）
        ・月の途中＝上場の週から記録がある（2017-09 以降の新規上場28銘柄すべて。古い銘柄は1つも無い）
      ⚠️ 経緯: 初版はトヨタの記録の始まりを床にして小松製作所（1949年上場）などを、2版は「2004年以降に始まる」で
      日本郵船などを「上場来」と言いうる形だった。銘柄の入れ替え（jp-stock-info.json）のときは監査をもう一度回す。

ガード（build_jp_rankings.py と同じ流儀＝関数をそのまま使う）:
  ・最終バーの日付の多数派を asof にし、少数派の銘柄は落とす（別の日を混ぜない）
  ・asof が前回より古い／大引け前（16:00 JST より前）の当日バーなら書かない
  ・取得できた銘柄が8割未満なら書かずに非ゼロ終了（偏った一覧を「最新」として出さない）
  ・その日の高値が前の日の終値の1.5倍超・安値が1/1.5未満・高値が終値より安い・安値が終値より高い＝データの誤りとして
    数えない（値幅制限があるので、ストップ高・ストップ安でもこの外には出ない）
  ・jp-rankings.json と同じ asof の一覧がもうあれば取りに行かない（jp-rankings.yml は1日に何度も走るため。--force で無視）

出力: jp-highs.json（hot-assets.html の「高値・安値の更新」欄が読む。highs／lows・日ごとの件数の履歴）。
⚠️ 事実の市場データであり、買い/売りの推奨ではない（描画側に注記と免責を付ける）。
"""
import os
import sys
import json
import time
import datetime
import urllib.request

from build_jp_rankings import INFO, JST, modal_date, is_regression, is_unsettled, SETTLE_JST

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "jp-highs.json")
RANKINGS = os.path.join(HERE, "jp-rankings.json")
MIN_PRIOR_BARS = 20       # 期間内に前の営業日がこれ未満（上場直後）は数えない＝数日分の「高値」は意味が薄い
MAX_JUMP = 1.5            # その日の高値 ÷ 前の日の終値 がこれを超えたら（安値は 1/これ 未満なら）データの誤りとして数えない
LISTING_CUTOFF = "2004-01-01"  # 念のための下限（月の途中から始まる記録でも、これより前なら上場来とは言わない）
RULE_VERSION = 4          # 判定の決まりを変えたら上げる（4＝安値を足した 2026-10-06 夕）＝同じ営業日でも作り直す（main の「取りに行かない」を素通りさせる）
HISTORY_KEEP = 250        # 毎日の件数の記録（約1年分）
MIN_COVERAGE = 0.8


def window_start(asof):
    """年初来の期間の始まりと呼び名（年初来／昨年来）を返す。純関数。

    日本の慣例＝1〜3月は前の年の1月1日から（昨年来高値・昨年来安値）、4〜12月はその年の1月1日から（年初来）。
    """
    y, m = int(asof[:4]), int(asof[5:7])
    if m <= 3:
        return f"{y - 1}-01-01", "昨年来"
    return f"{y}-01-01", "年初来"


def parse_bars(result):
    """Yahoo chart の result から [(日付JST, 高値, 安値, 終値, 出来高)] を返す（高値・安値・終値の欠けたバーは落とす）。純関数。"""
    q = result["indicators"]["quote"][0]
    ts = result.get("timestamp") or []
    highs, lows = q.get("high") or [], q.get("low") or []
    closes, vols = q.get("close") or [], q.get("volume") or []
    out = []
    for t, h, lo, c, v in zip(ts, highs, lows, closes, vols):
        if h is None or lo is None or c is None:
            continue
        d = datetime.datetime.fromtimestamp(t, JST).date().isoformat()
        out.append((d, float(h), float(lo), float(c), float(v or 0)))
    return out


def fetch_bars(code, rng, interval):
    """Yahoo から日足/月足を取る。失敗したら []。"""
    u = f"https://query1.finance.yahoo.com/v8/finance/chart/{code}.T?range={rng}&interval={interval}"
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    try:
        d = json.load(urllib.request.urlopen(req, timeout=25))["chart"]["result"][0]
        return parse_bars(d)
    except Exception:
        return []


def sane_today(bars):
    """その日のバーがデータの誤りでないか。純関数。

    高値は終値以上・安値は終値以下、どちらも前の日の終値の 1/1.5〜1.5倍に収まる（値幅制限があるので、
    ストップ高・ストップ安でもこの外には出ない）。
    """
    if len(bars) < 2:
        return False
    _, h, lo, c, _ = bars[-1]
    prev_c = bars[-2][3]
    return (prev_c > 0 and lo > 0 and h >= c * 0.999 and lo <= c * 1.001
            and h <= prev_c * MAX_JUMP and lo >= prev_c / MAX_JUMP)


# 高値／安値で変わるのは「どの値を見るか」と「どちら向きが更新か」だけ＝1つの関数で両方を判定する
_COL = {"high": 1, "low": 2}


def _beyond(today, prev, side):
    return today > prev if side == "high" else today < prev


def ytd_extreme(bars, start, side="high"):
    """その日（最後のバー）の高値（安値）が、start〜前の営業日の高値（安値）をすべて上回った（下回った）か。純関数。

    更新なら {"prev", "prev_date"}＝それまでの一番高い（安い）値とその日付。更新していない・判定できないなら None。
    同じ値は更新に数えない。
    """
    if not sane_today(bars):
        return None
    i = _COL[side]
    prior = [b for b in bars[:-1] if b[0] >= start]
    if len(prior) < MIN_PRIOR_BARS:
        return None
    pick = max if side == "high" else min
    p = pick(prior, key=lambda b: b[i])
    if _beyond(bars[-1][i], p[i], side):
        return {"prev": round(p[i], 1), "prev_date": p[0]}
    return None


def all_time_extreme(monthly, daily, side="high"):
    """上場来（記録のある全期間）の高値（安値）を更新したか。純関数。

    比べる相手＝前の月までの月足＋日足（約2年）のうち前の営業日まで。
    その月の月足はその日の値を含むので使わない（日足で前の日までを補う）。
    戻り値＝(更新したか, それまでの記録上の最高値（最安値）, 記録の始まりの日付)。月足が無ければ (None, None, None)＝判定しない。
    """
    if not monthly or not daily:
        return None, None, None
    i = _COL[side]
    asof = daily[-1][0]
    prior = [m[i] for m in monthly if m[0][:7] < asof[:7]] + [b[i] for b in daily[:-1]]
    if not prior:
        return None, None, None
    prev = max(prior) if side == "high" else min(prior)
    first = min(monthly[0][0], daily[0][0])
    return _beyond(daily[-1][i], prev, side), round(prev, 1), first


def listing_confirmed(first_date, cutoff=LISTING_CUTOFF):
    """記録が上場の週から始まっている＝上場来と言えるか。純関数。

    月足の最初のバーが月の途中の日付＝上場の週から記録がある。月の1日＝Yahoo の記録がその月から始まっただけ
    （古い銘柄。上場が月の初めの週だった新しい銘柄もここに入るが、言い切らない側なので害はない）。
    分からないときは False＝「上場来」と言い切らない側に倒す。
    """
    return bool(first_date) and first_date >= cutoff and first_date[8:10] != "01"


def make_row(code, meta, bars, hit, record, record_prev, first):
    """一覧の1行。高値・安値で同じ形（ext＝その日の高値または安値）。"""
    _, h, lo, c, v = bars[-1]
    prev_c = bars[-2][3]
    return {
        "code": code, "name": meta.get("name", ""), "sector": meta.get("sector", ""),
        "akaji": meta.get("akaji"),
        "price": round(c, 1), "pct": round(c / prev_c - 1.0, 4),
        "ext": round(h if hit["side"] == "high" else lo, 1),
        "prev": hit["prev"], "prev_date": hit["prev_date"],   # 期間内のそれまでの一番高い（安い）値と日付
        "turnover": round(c * v / 1e8, 1),          # その日の売買代金（億円・終値×出来高の概算）
        "record": bool(record),                      # 記録のある全期間の高値（安値）も更新した
        "record_prev": record_prev,                  # それまでの記録上の最高値（最安値）
        "hist_from": first,                          # 比べた記録の始まり
        "listed": listing_confirmed(first) if record else None,  # True＝上場時からの記録＝「上場来」と言える
    }


def update_history(history, asof, counts):
    """毎日の件数の記録を更新する（同じ日は置き換え・古い順・最新 HISTORY_KEEP 件）。純関数。

    counts＝{"ytd": 年初来高値, "ath": 記録上の最高値, "ytd_low": 年初来安値, "atl": 記録上の最安値}
    （安値は 2026-10-06 夕から。それより前の日は ytd_low・atl が無い）。
    """
    h = [x for x in (history or []) if x.get("date") != asof]
    h.append(dict({"date": asof}, **counts))
    h.sort(key=lambda x: x["date"])
    return h[-HISTORY_KEEP:]


def already_done(prev, rank_asof):
    """jp-rankings.json と同じ営業日・同じ決まりの一覧がもうあるか（＝取りに行かない）。純関数。"""
    return bool(rank_asof) and prev.get("asof") == rank_asof and prev.get("rule") == RULE_VERSION


def read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def main(force=False):
    prev = read_json(OUT)
    prev_asof = prev.get("asof") or ""
    rank_asof = read_json(RANKINGS).get("asof") or ""
    if not force and already_done(prev, rank_asof):
        print(f"⏭ jp-highs.json はもう {prev_asof}（jp-rankings.json と同じ営業日・同じ決まり）＝取りに行かずに終了")
        return

    stocks = json.load(open(INFO, encoding="utf-8"))["stocks"]
    codes = list(stocks.keys())
    daily, fail = {}, 0
    for i, code in enumerate(codes):
        bars = fetch_bars(code, "2y", "1d")
        if len(bars) < 2:
            fail += 1
        else:
            daily[code] = bars
        if (i + 1) % 100 == 0:
            print(f"  ...{i+1}/{len(codes)} fail={fail}", flush=True)
        time.sleep(0.07)

    asof = modal_date([b[-1][0] for b in daily.values()])
    mixed = [c for c, b in daily.items() if b[-1][0] != asof]
    if mixed:
        print(f"⚠️ 最終営業日が混在（多数派 {asof} 以外 {len(mixed)}銘柄）＝除外: {', '.join(mixed[:5])}"
              + (" ほか" if len(mixed) > 5 else ""))
        for c in mixed:
            daily.pop(c)
    if is_regression(asof, prev_asof):
        print(f"⏸ 取得できた最終営業日 {asof} が前回 {prev_asof} より古い＝更新せず終了（次の回に委ねる）")
        return
    now_jst = datetime.datetime.now(JST)
    if is_unsettled(asof, now_jst):
        print(f"⏸ {asof} はきょうで、いま {now_jst:%H:%M} JST＝大引け前後の未確定の値。"
              f"書かずに終了（{SETTLE_JST[0]}:{SETTLE_JST[1]:02d} 以降の回に委ねる）")
        return
    coverage = len(daily) / max(len(codes), 1)
    if coverage < MIN_COVERAGE:
        print(f"🚨 取得成功 {len(daily)}/{len(codes)} 銘柄（{coverage:.0%} < {MIN_COVERAGE:.0%}）＝"
              f"偏った一覧になるため jp-highs.json を更新せず終了（前回分を温存）")
        sys.exit(1)
    if rank_asof and asof != rank_asof:
        print(f"⚠️ jp-rankings.json は {rank_asof}・こちらは {asof}（取得のあいだに上流が更新された）＝各欄に日付を出すので続行")

    start, period = window_start(asof)

    out, skipped_bad = {"high": [], "low": []}, 0
    for code, bars in daily.items():
        if not sane_today(bars):
            skipped_bad += 1
            continue
        hits = {}
        for side in ("high", "low"):
            hit = ytd_extreme(bars, start, side)
            if hit:
                hits[side] = dict(hit, side=side)
        if not hits:
            continue
        monthly = fetch_bars(code, "max", "1mo")    # 年初来を更新した銘柄だけ全期間を取る（1日に数十銘柄）
        time.sleep(0.07)
        for side, hit in hits.items():
            record, record_prev, first = all_time_extreme(monthly, bars, side)
            out[side].append(make_row(code, stocks[code], bars, hit, record, record_prev, first))
    for side in out:
        out[side].sort(key=lambda r: r["turnover"], reverse=True)
    highs, lows = out["high"], out["low"]
    counts = {"ytd": len(highs), "ath": sum(1 for r in highs if r["record"]),
              "ytd_low": len(lows), "atl": sum(1 for r in lows if r["record"])}
    payload = {
        "asof": asof, "universe": len(daily), "window_start": start, "period": period,
        "rule": RULE_VERSION, "listing_cutoff": LISTING_CUTOFF, "highs": highs, "lows": lows,
        "history": update_history(prev.get("history"), asof, counts),
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    print(f"✅ {OUT}: as of {asof} / {len(daily)}銘柄（取得失敗{fail}・データの誤りで除外{skipped_bad}）・{period}＝{start}〜")
    for side, name, rec in (("high", "高値", "最高値"), ("low", "安値", "最安値")):
        rows = out[side]
        print(f"   {period}{name} {len(rows)}銘柄・記録上の{rec} {sum(1 for r in rows if r['record'])}銘柄"
              f"（うち上場来と言えるもの {sum(1 for r in rows if r['record'] and r['listed'])}）")
        for r in rows[:5]:
            print(f"     {r['code']} {r['name']} {name}{r['ext']}（それまで {r['prev']} {r['prev_date']}）"
                  f"{' ★記録' if r['record'] else ''}")


def audit():
    """全銘柄の Yahoo の記録の始まりを並べる（表示だけ・何も書かない）。LISTING_CUTOFF が安全かを確かめる用。

    見るところ＝区切り（2004年）以降に記録が始まる銘柄が、本当にその頃に上場した銘柄か。
    古くから上場している会社がここに出たら、その銘柄は Yahoo の記録が途中からしかない＝区切りを遅らせる。
    """
    stocks = json.load(open(INFO, encoding="utf-8"))["stocks"]
    firsts, fail = {}, []
    for code in stocks:
        bars = fetch_bars(code, "max", "1mo")
        if bars:
            firsts[code] = bars[0][0]
        else:
            fail.append(code)
        time.sleep(0.07)
    by_year = {}
    for d in firsts.values():
        by_year[d[:4]] = by_year.get(d[:4], 0) + 1
    print(f"記録の始まり（{len(firsts)}銘柄・取得失敗 {len(fail)}）")
    for y in sorted(by_year):
        print(f"  {y}: {by_year[y]}")
    yes = sorted((d, c) for c, d in firsts.items() if listing_confirmed(d))
    print(f"\n「上場来」と言う側 {len(yes)}銘柄（記録が月の途中＝上場の週から始まる。上場がその頃か確かめる）:")
    for d, c in yes:
        print(f"  {d}  {c}  {stocks[c].get('name', '')}")
    late_no = sorted((d, c) for c, d in firsts.items() if not listing_confirmed(d) and d >= LISTING_CUTOFF)
    print(f"\n{LISTING_CUTOFF} 以降に始まるが言い切らない側 {len(late_no)}銘柄（月の1日に始まる＝古い銘柄の記録の途中もここ）:")
    for d, c in late_no:
        print(f"  {d}  {c}  {stocks[c].get('name', '')}")
    odd = sorted((d, c) for c, d in firsts.items() if d < LISTING_CUTOFF and d[8:10] != "01")
    if odd:
        print(f"\n⚠️ {LISTING_CUTOFF} より前なのに月の途中から始まる {len(odd)}銘柄（見分け方の前提が崩れていないか見る）:")
        for d, c in odd:
            print(f"  {d}  {c}  {stocks[c].get('name', '')}")


if __name__ == "__main__":
    if "--audit" in sys.argv:
        audit()
    else:
        main(force="--force" in sys.argv)
