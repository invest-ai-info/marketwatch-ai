# -*- coding: utf-8 -*-
"""build_jp_highs.py — 日本株の「年初来高値・安値」「上場来高値・安値」を更新した銘柄の一覧を作る（公開サイト用）。

2026-10-06 新設（オーナー依頼「日本株の大引けが終わったときに、年初来高値更新・上場来高値更新の銘柄の
一覧表を出来高急増のページに追加してほしい」）。同日夕、オーナー依頼「安値の方も追加して」で安値も。
高値と安値は同じ関数で判定する（違いは見る値と向きだけ＝ytd_extreme / all_time_extreme の side）。

対象＝**東証プライム・スタンダード・グロースの全上場銘柄（約3,700・内国株式と外国株式）**。一覧は JPX の
「東証上場銘柄一覧」（data_j.xlsx・月1回更新）を毎回取る（load_universe）。ETF・REIT・PRO Market は入れない。
🔁 2026-10-06 夜 オーナー依頼「全銘柄に広げて」で、流動性上位の約400銘柄（jp-stock-info.json）から広げた。
   Yahoo に約3,700回取りに行く＝1回13〜15分かかるので、日本株ランキングのジョブから分けて jp-highs.yml で動かす。
   赤字・黒字（akaji）は約400銘柄にしか無いので、表からは決算の列を外して市場区分を出す。

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
      日本郵船などを「上場来」と言いうる形だった。全銘柄に広げたので、監査（--audit）も全銘柄で回し、
      2022年以降の分は JPX の新規上場の一覧（上場日）と突き合わせる。
      ⚠️ ここでの「上場来」＝**東証に上場してからの記録**（Yahoo の .T の記録）。名証などほかの取引所から東証に
      来た銘柄（例: 中部鋼鈑 2022-12）は、それより前のほかの取引所での売買を含まない＝表示の注記にそう書く。

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
import re
import urllib.error
import urllib.request

from build_jp_rankings import INFO, JST, modal_date, is_regression, is_unsettled, SETTLE_JST

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "jp-highs.json")
RANKINGS = os.path.join(HERE, "jp-rankings.json")
MIN_PRIOR_BARS = 20       # 期間内に前の営業日がこれ未満（上場直後）は数えない＝数日分の「高値」は意味が薄い
MAX_JUMP = 1.5            # その日の高値 ÷ 前の日の終値 がこれを超えたら（安値は 1/これ 未満なら）データの誤りとして数えない
LISTING_CUTOFF = "2004-01-01"  # 念のための下限（月の途中から始まる記録でも、これより前なら上場来とは言わない）
RULE_VERSION = 5          # 判定の決まりを変えたら上げる（4＝安値を足した 2026-10-06 夕・5＝全銘柄に広げた 同日夜）＝同じ営業日でも作り直す（main の「取りに行かない」を素通りさせる）
HISTORY_KEEP = 250        # 毎日の件数の記録（約1年分）
MIN_COVERAGE = 0.8
SCOPE = "all"             # 対象の範囲（履歴の件数は同じ範囲どうしでしか比べない＝400銘柄の日と混ぜない）
JPX_LIST_PAGE = "https://www.jpx.co.jp/markets/statistics-equities/misc/01.html"   # 東証上場銘柄一覧
JPX_NEW_PAGES = ["https://www.jpx.co.jp/listing/stocks/new/index.html"] + [
    f"https://www.jpx.co.jp/listing/stocks/new/00-archives-{n:02d}.html" for n in range(1, 5)]  # 新規上場（2022年〜）
MARKETS = ("プライム", "スタンダード", "グロース")
UA = {"User-Agent": "Mozilla/5.0"}
THROTTLED = {"n": 0}      # Yahoo に「混んでいる」（429・5xx）と言われた回数（ログ用）


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


def fetch_bars(code, rng, interval, tries=3):
    """Yahoo から日足/月足を取る。失敗したら []。

    全銘柄で約3,700回取りに行くので、「混んでいる」（429・5xx）や通信の途切れは間を空けて2回までやり直す。
    404（Yahoo に無い銘柄）はやり直さない。
    """
    u = f"https://query1.finance.yahoo.com/v8/finance/chart/{code}.T?range={rng}&interval={interval}"
    for k in range(tries):
        try:
            req = urllib.request.Request(u, headers=UA)
            d = json.load(urllib.request.urlopen(req, timeout=25))["chart"]["result"][0]
            return parse_bars(d)
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500:
                THROTTLED["n"] += 1
                time.sleep(3 * (k + 1) ** 2)
                continue
            return []
        except Exception:
            time.sleep(1 + k)
    return []


def find_list_link(html):
    """JPX「東証上場銘柄一覧」のページから data_j.xls(x) の絶対 URL を返す（無ければ ""）。純関数。"""
    m = re.search(r'href="([^"]*data_j\.xlsx?)"', html, re.I)
    if not m:
        return ""
    href = m.group(1)
    return href if href.startswith("http") else "https://www.jpx.co.jp" + href


def parse_universe(records, info_stocks=None):
    """JPX の一覧の行（dict）から {コード: {name, sector, market, akaji}} と一覧の日付を返す。純関数。

    プライム・スタンダード・グロース（内国株式・外国株式）だけ。ETF・REIT・PRO Market・出資証券は入れない。
    赤字・黒字は jp-stock-info.json にある約400銘柄だけ（無ければ None）。
    """
    info_stocks = info_stocks or {}
    out, list_date = {}, ""
    for r in records:
        market = str(r.get("市場・商品区分") or "")
        code = str(r.get("コード") or "").strip()
        if not code or not market.startswith(MARKETS):
            continue
        sector = str(r.get("33業種区分") or "").strip()
        out[code] = {"name": str(r.get("銘柄名") or "").strip(),
                     "sector": "" if sector in ("-", "nan") else sector,
                     "market": market.split("（")[0],
                     "akaji": (info_stocks.get(code) or {}).get("akaji")}
        d = str(r.get("日付") or "").strip()
        if len(d) == 8 and d.isdigit():
            list_date = max(list_date, f"{d[:4]}-{d[4:6]}-{d[6:]}")
    return out, list_date


def load_universe():
    """JPX から東証上場銘柄一覧を取って parse_universe する。失敗したら例外。"""
    import io
    import pandas as pd
    html = urllib.request.urlopen(urllib.request.Request(JPX_LIST_PAGE, headers=UA), timeout=30).read().decode("utf-8", "replace")
    url = find_list_link(html)
    if not url:
        raise RuntimeError("東証上場銘柄一覧のページに data_j.xls(x) のリンクが無い（JPX のページの形が変わった？）")
    raw = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()
    df = pd.read_excel(io.BytesIO(raw), dtype=str)
    try:
        info = json.load(open(INFO, encoding="utf-8"))["stocks"]
    except Exception:
        info = {}
    stocks, list_date = parse_universe(df.to_dict("records"), info)
    if len(stocks) < 3000:
        raise RuntimeError(f"東証上場銘柄一覧から取れた銘柄が {len(stocks)} しかない（約3,700のはず）＝列名か区分の名前が変わった？")
    return stocks, list_date


def parse_jpx_new_listings(html):
    """JPX「新規上場銘柄一覧」の表から [(上場日, コード, 公開価格あり)] を返す。純関数。（点検用）

    公開価格が「-」＝新規公開（IPO）ではない上場（ほかの取引所からの上場・持株会社の設立など）。
    """
    out = []
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S):
        cells = [c.strip() for c in re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "|", row)).split("|")]
        cells = [c for c in cells if c]
        date = next((c for c in cells if re.fullmatch(r"20\d\d/\d\d/\d\d", c)), "")
        if not date:
            continue
        rest = cells[cells.index(date) + 1:]
        code = next((c for c in rest if re.fullmatch(r"\d[0-9A-Z]{2}[0-9A-Z]", c)), "")
        if not code:
            continue
        after = rest[rest.index(code) + 1:]
        ipo = any(re.search(r"\d", c) for c in after[:2])   # 仮条件・公開価格の欄に数字がある
        out.append((date.replace("/", "-"), code, ipo))
    return out


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
        "market": meta.get("market", ""), "akaji": meta.get("akaji"),
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


def main(force=False, dry_run=False):
    """dry_run＝最後まで数えて結果を表示するが jp-highs.json は書かない（点検のワークフローで本番の前に試す用）。"""
    prev = read_json(OUT)
    prev_asof = prev.get("asof") or ""
    rank_asof = read_json(RANKINGS).get("asof") or ""
    if not force and not dry_run and already_done(prev, rank_asof):
        print(f"⏭ jp-highs.json はもう {prev_asof}（jp-rankings.json と同じ営業日・同じ決まり）＝取りに行かずに終了")
        return

    t0 = time.time()
    try:
        stocks, list_date = load_universe()
    except Exception as e:
        print(f"🚨 東証上場銘柄一覧（JPX）が取れない: {e}＝jp-highs.json を更新せず終了（前回分を温存）")
        sys.exit(1)
    print(f"対象＝東証上場銘柄一覧（{list_date} 時点）のプライム・スタンダード・グロース {len(stocks)}銘柄")
    codes = list(stocks.keys())
    daily, fail = {}, 0
    for i, code in enumerate(codes):
        bars = fetch_bars(code, "2y", "1d")
        if len(bars) < 2:
            fail += 1
        else:
            daily[code] = bars
        if (i + 1) % 500 == 0:
            print(f"  ...{i+1}/{len(codes)} 取得失敗={fail} 混雑={THROTTLED['n']} 経過{(time.time()-t0)/60:.1f}分", flush=True)
        time.sleep(0.07)
    fetched = len(daily)

    asof = modal_date([b[-1][0] for b in daily.values()])
    mixed = [c for c, b in daily.items() if b[-1][0] != asof]
    if mixed:
        # 全銘柄では、その日に売買が成立しなかった銘柄（最後のバーが前の日）もここに入る＝その日は更新しようがない
        print(f"ℹ️ 最終営業日が {asof} でない {len(mixed)}銘柄（その日に売買が無かった銘柄など）＝除外: {', '.join(mixed[:5])}"
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
    coverage = fetched / max(len(codes), 1)    # 取れたかどうかで見る（売買の無かった銘柄は取れている）
    if coverage < MIN_COVERAGE:
        print(f"🚨 取得成功 {fetched}/{len(codes)} 銘柄（{coverage:.0%} < {MIN_COVERAGE:.0%}・混雑 {THROTTLED['n']}回）＝"
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
    counts = {"scope": SCOPE, "n": len(daily), "ytd": len(highs), "ath": sum(1 for r in highs if r["record"]),
              "ytd_low": len(lows), "atl": sum(1 for r in lows if r["record"])}
    payload = {
        "asof": asof, "scope": SCOPE, "listed_total": len(stocks), "list_date": list_date,
        "universe": len(daily), "window_start": start, "period": period,
        "rule": RULE_VERSION, "listing_cutoff": LISTING_CUTOFF, "highs": highs, "lows": lows,
        "history": update_history(prev.get("history"), asof, counts),
    }
    if not dry_run:
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
    print(f"{'🧪 試し（書かない）' if dry_run else '✅ ' + OUT}: as of {asof} / 一覧 {len(stocks)}銘柄 → 取れた {fetched}"
          f"（取得失敗{fail}・混雑{THROTTLED['n']}回）→ その日に値がある {len(daily)}（データの誤りで除外{skipped_bad}）"
          f"・{period}＝{start}〜・所要 {(time.time()-t0)/60:.1f}分")
    for side, name, rec in (("high", "高値", "最高値"), ("low", "安値", "最安値")):
        rows = out[side]
        print(f"   {period}{name} {len(rows)}銘柄・記録上の{rec} {sum(1 for r in rows if r['record'])}銘柄"
              f"（うち上場来と言えるもの {sum(1 for r in rows if r['record'] and r['listed'])}）")
        for r in rows[:5]:
            print(f"     {r['code']} {r['name']} {name}{r['ext']}（それまで {r['prev']} {r['prev_date']}）"
                  f"{' ★記録' if r['record'] else ''}")


def audit():
    """全銘柄の Yahoo の記録の始まりを並べる（表示だけ・何も書かない）。「上場来」の見分け方が安全かを確かめる用。

    見るところ:
      ① 月の途中から記録が始まる（＝上場来と言う側）銘柄が、2017-09 より前に無いか（あれば Yahoo の記録の途中が
         月の途中から始まる古い銘柄がある＝見分け方の前提が崩れる）
      ② 2022年以降に月の途中から始まる銘柄が、JPX の新規上場の一覧の上場日（前後10日）と合うか
      ③ JPX で新規上場したのに、記録が月の1日から始まる銘柄（言い切らない側に落ちている＝害はないが数を見る）
    """
    stocks, list_date = load_universe()
    print(f"点検の対象＝東証上場銘柄一覧（{list_date}）{len(stocks)}銘柄")
    firsts, fail = {}, []
    for code in stocks:
        bars = fetch_bars(code, "max", "1mo")
        if bars:
            firsts[code] = bars[0][0]
        else:
            fail.append(code)
        time.sleep(0.07)

    def nm(c):
        return f"{c}  {stocks[c].get('name', '')}（{stocks[c].get('market', '')}）"

    def hist(ds):
        by = {}
        for d in ds:
            by[d[:4]] = by.get(d[:4], 0) + 1
        return "  ".join(f"{y}:{by[y]}" for y in sorted(by))

    print(f"記録の始まり（{len(firsts)}銘柄・取得失敗 {len(fail)}・混雑 {THROTTLED['n']}回）年ごと:\n  {hist(firsts.values())}")
    mid = {c: d for c, d in firsts.items() if d[8:10] != "01"}
    yes = {c: d for c, d in firsts.items() if listing_confirmed(d)}
    print(f"\n月の途中から始まる {len(mid)}銘柄（うち「上場来」と言う側 {len(yes)}）年ごと:\n  {hist(mid.values())}")
    early = sorted((d, c) for c, d in mid.items() if d < "2017-09-01")
    print(f"\n① 2017-09 より前に月の途中から始まる {len(early)}銘柄（0 なら見分け方の前提どおり）:")
    for d, c in early[:60]:
        print(f"  {d}  {nm(c)}{'  ←上場来と言う側' if c in yes else ''}")

    jpx = {}
    for u in JPX_NEW_PAGES:
        try:
            html = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30).read().decode("utf-8", "replace")
            for d, c, ipo in parse_jpx_new_listings(html):
                jpx.setdefault(c, (d, ipo))
        except Exception as e:
            print(f"  ⚠️ JPX の新規上場の一覧が取れない {u}: {e}")
    print(f"\nJPX の新規上場の一覧（2022年〜）{len(jpx)}件")

    def near(a, b, days=10):
        return abs((datetime.date.fromisoformat(a) - datetime.date.fromisoformat(b)).days) <= days

    recent = sorted((d, c) for c, d in yes.items() if d >= "2022-01-01")
    ok = [(d, c) for d, c in recent if c in jpx and near(d, jpx[c][0])]
    bad = [(d, c) for d, c in recent if (d, c) not in ok]
    print(f"② 2022年以降に月の途中から始まり「上場来」と言う側 {len(recent)}銘柄 → JPX の上場日と合う {len(ok)}"
          f"（うち新規公開 {sum(1 for d, c in ok if jpx[c][1])}・ほかの取引所からの上場や持株会社など {sum(1 for d, c in ok if not jpx[c][1])}）")
    if bad:
        print(f"   ⚠️ 合わない {len(bad)}銘柄（記録の始まり／JPX の上場日）:")
        for d, c in bad[:60]:
            print(f"   {d} / {jpx.get(c, ('一覧に無い',))[0]}  {nm(c)}")
    miss = sorted((jpx[c][0], c) for c in jpx if c in firsts and c not in yes)
    print(f"③ JPX で2022年以降に新規上場したのに「上場来」と言わない側 {len(miss)}銘柄（記録が月の1日から・害はない）:")
    for d, c in miss[:30]:
        print(f"   {d}（記録 {firsts[c]}）  {nm(c)}")


if __name__ == "__main__":
    if "--audit" in sys.argv:
        audit()
    else:
        main(force="--force" in sys.argv, dry_run="--dry-run" in sys.argv)
