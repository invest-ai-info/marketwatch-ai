# -*- coding: utf-8 -*-
"""市場健康度の日次履歴を集めて market-health-history.json を更新する。

責務はデータ収集と JSON 更新だけ。HTML は一切触らない（描画は generate_market_news.py）。

⚠️ 閾値の単一の真実はこのファイルの ZONES。JSON の "zones" も、
   generate_market_news.py のカードの色分けも、ここから引く（同じ数字を2箇所に書かない）。

実行:
  python build_health_history.py             # 当日ぶんを追記
  python build_health_history.py --backfill  # 直近1年を遡って埋める（初回1回だけ）
"""
import datetime as dt
import json
import os
import sys
import urllib.request

from build_touraku_history import (
    ratio25 as _touraku_ratio25,
    RATIO_WINDOW as _TOURAKU_WINDOW,
    HISTORY_PATH as _TOURAKU_HISTORY_PATH,
)

JST = dt.timezone(dt.timedelta(hours=9))
ROOT = os.path.dirname(os.path.abspath(__file__))
HISTORY_PATH = os.path.join(ROOT, "market-health-history.json")

# (下端, 上端, ラベル, 色)。下端は「以上」、上端は「未満」。両端は None で開放。
# 色は既存の意味色（🟢#1a7f37 / 🔵#0969da / 🟡#9a6700 / 桃#bf3989 / 🔴#da3633）をそのまま使う。
ZONES = {
    "vix": [
        (None, 15, "落ち着き", "#1a7f37"),
        (15, 20, "通常", "#1a7f37"),
        (20, 30, "中位", "#9a6700"),
        (30, 40, "警戒", "#bf3989"),
        (40, None, "パニック", "#da3633"),
    ],
    "cnn_fg": [
        (None, 25, "極度の恐怖", "#1a7f37"),
        (25, 45, "恐怖", "#0969da"),
        (45, 55, "中立", "#9a6700"),
        (55, 75, "強欲", "#bf3989"),
        (75, None, "極度の強欲", "#da3633"),
    ],
    # ⚠️ crypto_fg は cnn_fg と**区分が違う**。同じ「恐怖&強欲」でも発表元が別々に定義している。
    #    2026-08-19 に両ソースの全公開値でラベル境界を実測して確認した:
    #      CNN         (251件): 極度の恐怖 <25 / 恐怖 25-45 / 中立 45-55 / 強欲 55-75 / 極度の強欲 75-
    #      alternative.me(3118件): 極度の恐怖 <26 / 恐怖 26-47 / 中立 47-55 / 強欲 55-76 / 極度の強欲 76-
    #    既存の market-health.html は両方に CNN の区分を当てていたため、例えば値 46 を
    #    「中立」と表示していた（alternative.me 自身のラベルは "Fear"）。発表元のラベルと
    #    食い違う表示になるので、ここで各ソース自身の区分に合わせる。
    "crypto_fg": [
        (None, 26, "極度の恐怖", "#1a7f37"),
        (26, 47, "恐怖", "#0969da"),
        (47, 55, "中立", "#9a6700"),
        (55, 76, "強欲", "#bf3989"),
        (76, None, "極度の強欲", "#da3633"),
    ],
    "buffett_us": [
        (None, 70, "大きく割安", "#1a7f37"),
        (70, 100, "適正", "#0969da"),
        (100, 135, "やや割高", "#9a6700"),
        (135, 180, "割高", "#bf3989"),
        (180, None, "大きく割高", "#da3633"),
    ],
    # 🆕 2026-08-22。既存 generate_market_news.py の analyze_touraku() が持っていた閾値を
    #    そのまま移設した（数値は不変＝表示挙動は変えない）。ここが単一の真実になったので
    #    analyze_touraku() 側は classify_zone("touraku_ratio", ...) を呼ぶだけに置き換える。
    "touraku_ratio": [
        (None, 60, "底値圏", "#238636"),
        (60, 80, "売られすぎ", "#9a6700"),
        (80, 120, "通常", "#1a7f37"),
        (120, 140, "買われすぎ", "#bf3989"),
        (140, None, "過熱圏", "#da3633"),
    ],
}


def classify_zone(series, value):
    """戻り値 (色, ラベル)。value が None なら灰色の「取得不可」。"""
    if value is None:
        return "#57606a", "取得不可"
    for lo, hi, label, color in ZONES[series]:
        if (lo is None or value >= lo) and (hi is None or value < hi):
            return color, label
    return "#57606a", "取得不可"


def merge_points(existing, new):
    """純関数。日付キーで上書きし、日付昇順で返す。

    - 同じ日付が来たら新しい値で上書き（何度流しても増えない＝冪等）
    - 値が None の点は**捨てる**。欠測日は点を打たない（0埋め・前日値埋めをしない）
    """
    merged = {d: v for d, v in (existing or []) if v is not None}
    for d, v in (new or []):
        if v is None:
            continue
        merged[d] = v
    return [[d, merged[d]] for d in sorted(merged)]


# CNN は素の UA だと HTTP 418 で弾く（2026-08-19 実測）。ブラウザ相当のヘッダが必須。
BROWSER_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://edition.cnn.com/",
    "Origin": "https://edition.cnn.com",
}


def _get_json(url, headers=None, timeout=25):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as res:
        return json.loads(res.read())


def _jst_date(epoch_sec):
    return dt.datetime.fromtimestamp(float(epoch_sec), JST).strftime("%Y-%m-%d")


def parse_yahoo_chart(payload):
    """Yahoo chart API の JSON -> [[日付, 終値]]。close が None の日は落とす。"""
    r = payload["chart"]["result"][0]
    ts = r["timestamp"]
    closes = r["indicators"]["quote"][0]["close"]
    out = []
    for t, c in zip(ts, closes):
        if c is None:
            continue
        out.append([_jst_date(t), round(float(c), 2)])
    return out


def parse_cnn_fg(payload):
    """CNN graphdata の JSON -> [[日付, 値]]。x はミリ秒エポック。"""
    rows = (payload.get("fear_and_greed_historical") or {}).get("data") or []
    return [[_jst_date(r["x"] / 1000.0), round(float(r["y"]), 1)] for r in rows]


def parse_crypto_fg(payload):
    """alternative.me の JSON -> [[日付, 値]]。降順で返ってくるので昇順に直す。"""
    rows = payload.get("data") or []
    out = [[_jst_date(r["timestamp"]), float(r["value"])] for r in rows]
    return sorted(out)


def compute_buffett(w5000_points, gdp_bn):
    """バフェット指数 = Wilshire5000 / 米名目GDP(10億ドル) * 100。

    ⚠️ 指数の値をそのまま「10億ドル」として扱ってよいかを 2026-08-19 に校正した:
       2026-04-20 の ^W5000 = 71,240.01、GDP = 30,769.7（世界銀行2025年）→ 231.5%。
       同日にサイトが手動で載せていた currentmarketvaluation.com 由来の値は 232%。
       差 0.5pp ＝ GDP の版の違いで説明でき、**1ポイント≒10億ドルで正しい**と確認した。

    GDP は四半期（FRED）＝日次で動くのは分子だけ。gdp_bn が None なら**何も返さない**
    （前回値で勝手に埋めない）。
    """
    if not gdp_bn:
        return []
    return [[d, round(v / float(gdp_bn) * 100, 1)] for d, v in w5000_points]


def fetch_yahoo(symbol, rng):
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/"
           + symbol + "?range=" + rng + "&interval=1d")
    return parse_yahoo_chart(_get_json(url))


def fetch_vix(rng="5d"):
    return fetch_yahoo("^VIX", rng)


def fetch_cnn_fg():
    return parse_cnn_fg(_get_json(
        "https://production.dataviz.cnn.io/index/fearandgreed/graphdata", BROWSER_HEADERS))


def fetch_crypto_fg(limit=30):
    return parse_crypto_fg(_get_json(
        "https://api.alternative.me/fng/?limit=" + str(limit) + "&format=json"))


def parse_worldbank_gdp(payload):
    """世界銀行 API の JSON -> 最新の米名目GDP（10億ドル）。値が無い年は飛ばす。"""
    rows = payload[1] if isinstance(payload, list) and len(payload) > 1 else []
    for row in rows:                       # 新しい年から並んでいる
        if row.get("value"):
            return float(row["value"]) / 1e9
    return None


def fetch_us_gdp_bn():
    """米名目GDP（10億ドル）。FRED を試し、届かなければ世界銀行にフォールバックする。

    ⚠️ FRED はローカルPCからも **GitHub Actions からも**届かない（2026-08-19 に両方で実測。
       Actions では例外が握り潰されて gdp=None のまま完走していた）。実運用の主役は世界銀行側。
    ⚠️ 世界銀行は**年次**なので、四半期より粗い。バフェット指数の日次の動きは分子（株価）だけ
       ＝この限界はページ上で自己開示する。
    """
    try:
        req = urllib.request.Request(
            "https://fred.stlouisfed.org/graph/fredgraph.csv?id=GDP",
            headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as res:
            raw = res.read().decode("utf-8", "replace")
        for line in reversed([l for l in raw.strip().splitlines() if l]):
            parts = line.split(",")
            if len(parts) >= 2:
                try:
                    return float(parts[1])
                except ValueError:
                    continue
    except Exception:
        pass
    try:
        return parse_worldbank_gdp(_get_json(
            "https://api.worldbank.org/v2/country/USA/indicator/NY.GDP.MKTP.CD"
            "?format=json&per_page=5"))
    except Exception:
        return None


def fetch_buffett_us(rng="5d", gdp_bn=None):
    return compute_buffett(fetch_yahoo("^W5000", rng), gdp_bn)


def fetch_touraku_ratio_series(path=None):
    """騰落レシオ(25日)の日次ロング系列を作る。

    🆕 2026-08-22。ネットワークは叩かない＝build_touraku_history.py が既に集めた
    touraku-history.json（{date, up, down} の生集計）をローカルで読み、日付ごとに
    「その日を最終日とする直近25日窓」の ratio25 を計算して積み上げる。
    計算式（ratio25・RATIO_WINDOW）は build_touraku_history.py を単一の真実として import する
    （generate_market_news.py の get_touraku_ratio() と同じ流用元）。

    ⚠️ ステップ順が前提: update-market-news.yml は
       build_touraku_history.py → build_health_history.py の順で回す
       （逆だと当日ぶんの touraku-history.json 更新前を読んでしまい、この系列だけ1日遅れる）。
    """
    hist = _load_touraku_history(path)
    points = hist.get("points") or []
    out = []
    for i in range(_TOURAKU_WINDOW - 1, len(points)):
        window = points[i - _TOURAKU_WINDOW + 1 : i + 1]
        r = _touraku_ratio25(window)
        if r is not None:
            out.append([points[i][0], r])
    return out


def _load_touraku_history(path=None):
    p = path or _TOURAKU_HISTORY_PATH
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"points": []}


SERIES_META = {
    # stale_days＝この日数以上あいたら「取得が止まっている」とみなす。
    # 2026-08-19 に直近1年の実データで**点と点の実際の間隔**を測って決めた（推測で置かない）。
    # 実測の最大間隔: vix 4日 / cnn_fg 4日 / crypto_fg 1日 / buffett_us 5日。
    # ⚠️ 一律3日にすると vix と cnn_fg は年45〜46回（ほぼ毎週）誤検知する＝3日の間隔は正常。
    "vix":        {"label": "米VIX", "unit": "", "stale_days": 5,
                   "source": "Yahoo Finance (^VIX)"},
    "cnn_fg":     {"label": "CNN 恐怖&強欲", "unit": "", "stale_days": 5,
                   "source": "CNN Business"},
    "crypto_fg":  {"label": "Crypto 恐怖&強欲", "unit": "", "stale_days": 3,  # 24時間365日＝毎日ある
                   "source": "alternative.me"},
    "buffett_us": {"label": "米バフェット指数", "unit": "%", "stale_days": 6,
                   "source": "Yahoo Finance (^W5000) / 米名目GDP (世界銀行・年次)",
                   "note": "分母の名目GDPは年次のため、日々動いているのは分子（株式時価総額）だけです。"},
    # 🆕 2026-08-22。stale_days は暫定値＝touraku-history.json の蓄積は2026-04-16開始で
    #    まだ4か月ぶんしか無く（実測の最大間隔は6日＝ゴールデンウィーク想定）、年末年始休場
    #    （実測データに未収録）を安全側に見込んで測定値6日より広めの10日を採用した。
    #    他の系列のように「実測の最大間隔+1日」まで詰めるのは、年末年始を跨いだ1年ぶんの
    #    データが溜まってから（目安2027年初）に見直す。
    "touraku_ratio": {"label": "騰落レシオ(25日)", "unit": "%", "stale_days": 10,
                      "source": "J-Quants (東証プライム全銘柄の終値集計) の25日騰落レシオ",
                      "note": "元データ touraku-history.json は2026-08-22開始のため、休場日数の"
                              "扱いはまだ1年分の実測に基づいていません（暫定の閾値）。"},
}


def _meta_note(key):
    return SERIES_META[key].get("note", "")


def empty_history():
    return {
        "updated_at": None,
        "series": {k: {"label": m["label"], "source": m["source"], "unit": m["unit"],
                       "note": m.get("note", ""),
                       "zones": [list(z) for z in ZONES[k]], "points": []}
                   for k, m in SERIES_META.items()},
        "health": {k: {"last_ok": None, "points": 0} for k in SERIES_META},
        "gdp_bn": None,
    }


def load_history(path=HISTORY_PATH):
    """壊れていても・無くても、必ず正しい形の器を返す。"""
    try:
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
    except Exception:
        return empty_history()
    base = empty_history()
    if not isinstance(doc, dict):
        return base
    base["updated_at"] = doc.get("updated_at")
    base["gdp_bn"] = doc.get("gdp_bn")
    for k in SERIES_META:
        old = (doc.get("series") or {}).get(k) or {}
        base["series"][k]["points"] = [list(p) for p in (old.get("points") or [])]
        oldh = (doc.get("health") or {}).get(k) or {}
        base["health"][k]["last_ok"] = oldh.get("last_ok")
        base["health"][k]["points"] = len(base["series"][k]["points"])
    return base


def collect(doc, fetchers, now_jst_date):
    """系列ごとに独立して取得し doc を更新して返す。1系列の失敗が他に波及しない。"""
    for key, fn in fetchers.items():
        try:
            pts = fn()
        except Exception as e:
            print("  NG %s: %s: %s" % (key, type(e).__name__, str(e)[:80]))
            continue
        merged = merge_points(doc["series"][key]["points"], pts)
        doc["series"][key]["points"] = merged
        doc["health"][key]["points"] = len(merged)
        if merged:
            doc["health"][key]["last_ok"] = merged[-1][0]
        print("  OK %s: %d点（最新 %s）" % (key, len(merged), merged[-1] if merged else "-"))
    doc["updated_at"] = now_jst_date
    return doc


def save_history(doc, path=HISTORY_PATH):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))


# 点がこれ未満の系列は、--backfill を付けなくても自動で1年ぶん取りに行く。
# 動機＝バフェット指数はローカルでは GDP が取れず0点のままになるので、Actions で初めて
# GDP が取れた日に自動で1年ぶん埋まってほしい（人が --backfill を打ちに行かなくて済む）。
SELF_HEAL_MIN_POINTS = 30


def series_range(doc, key, backfill):
    """その系列を取りに行くレンジ。戻り値 (yahoo range, alternative.me limit)。"""
    if backfill or len(doc["series"][key]["points"]) < SELF_HEAL_MIN_POINTS:
        return "1y", 400
    return "5d", 30


def eval_series_health(health, now, stale_days=None):
    """純関数。戻り値: (停止 [(系列, 経過日, 閾値)], 観測開始前 [系列], 監視対象数)。

    閾値は系列ごと（SERIES_META の stale_days）。市場データは土日・祝日で必ず空くので
    一律にすると毎週鳴る＝実データの間隔を測って決めてある（上の SERIES_META のコメント）。
    stale_days を渡すと全系列をその値で上書きする（テスト用）。

    一度も取れていない系列（last_ok が None）は「観測開始前」として鳴らさない
    ＝新しい系列を足した初日に赤くしない（news-ticker の feed_health と同じ方針）。
    """
    today = now.astimezone(JST).date()
    stale, pending = [], []
    for key, meta in SERIES_META.items():
        limit = stale_days if stale_days is not None else meta["stale_days"]
        rec = health.get(key) or {}
        last = rec.get("last_ok")
        if not last:
            pending.append(key)
            continue
        try:
            age = (today - dt.date.fromisoformat(last)).days
        except ValueError:
            pending.append(key)
            continue
        if age >= limit:
            stale.append((key, age, limit))
    stale.sort(key=lambda x: -x[1])
    return stale, pending, len(SERIES_META)


def main():
    backfill = "--backfill" in sys.argv
    doc = load_history()

    gdp = fetch_us_gdp_bn()
    if gdp:
        doc["gdp_bn"] = gdp
    else:
        # ローカルPCからは FRED に届かない。前回値を使う（GDPは四半期なので実害は小さい）。
        print("  -- GDP を取得できず。JSON の前回値を使う: %s" % doc.get("gdp_bn"))
    gdp = doc.get("gdp_bn")

    now_jst_date = dt.datetime.now(JST).strftime("%Y-%m-%d")
    rng_vix = series_range(doc, "vix", backfill)[0]
    rng_bf = series_range(doc, "buffett_us", backfill)[0]
    lim_crypto = series_range(doc, "crypto_fg", backfill)[1]
    fetchers = {
        "vix": lambda: fetch_vix(rng_vix),
        "cnn_fg": fetch_cnn_fg,            # CNN は常に全履歴（約251点）を返すのでレンジ指定なし
        "crypto_fg": lambda: fetch_crypto_fg(lim_crypto),
        "buffett_us": lambda: fetch_buffett_us(rng_bf, gdp),
        # touraku_ratio はネットワークを叩かず touraku-history.json をローカルで読むだけなので
        # レンジ指定は不要（毎回、蓄積済みの全期間から計算し直す＝関数自体が冪等）。
        "touraku_ratio": fetch_touraku_ratio_series,
    }
    doc = collect(doc, fetchers, now_jst_date)

    # 全系列を直近1年で揃える。CNN が約251営業日ぶんしか返さないため、そこに合わせる。
    # 毎回かけるのでファイルが無限に伸びない（1年より古い点は落ちていく）。
    cutoff = (dt.datetime.now(JST) - dt.timedelta(days=366)).strftime("%Y-%m-%d")
    for k in doc["series"]:
        doc["series"][k]["points"] = [p for p in doc["series"][k]["points"] if p[0] >= cutoff]
        doc["health"][k]["points"] = len(doc["series"][k]["points"])

    save_history(doc)
    print("saved: %s" % HISTORY_PATH)
    for k, h in doc["health"].items():
        print("  %-11s %4d点  last_ok=%s" % (k, h["points"], h["last_ok"]))


if __name__ == "__main__":
    main()
