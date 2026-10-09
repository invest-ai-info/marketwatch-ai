# -*- coding: utf-8 -*-
"""J44 高値更新の台帳：年初来高値・上場来高値を更新した株の「その日の特徴」と「そのあと」（続伸・横ばい・だまし）を毎日ためる。
2026-10-09 オーナー「年初の高値を更新してさらに上げたものと、だましで下げたもの、特徴を蓄積して保存しておいてください」。
PILLAR_PREREG.md「J44」（読むだけ・判定しない）。

流れ: build_jp_highs.py（jp-highs.yml・夕方）の最後に update() を呼ぶ。
  ① そのあとがまだ埋まっていないケースに、取れた日足（build_jp_highs の daily）から次の日・5日後の値動きを書く。
     次の日の始値（窓・寄り→大引け）は daily に無いので、そのケースの銘柄だけ Yahoo の日足を取りに行く（1日に数十回）
  ② その日の高値更新の一覧（jp-highs.json の highs）を新しいケースとして足す（特徴はその日の引けでわかるものだけ）。
     台帳に前の日の一覧が無ければ、前の jp-highs.json の一覧も足す（始めた日・取りこぼした日）
  → highs-ledger.csv（全ケース・1行1ケース・Excel で開ける UTF-8 BOM つき・kind 列＝上場来／記録上の最高値／年初来）
    ／highs-ledger.md（A. 年初来の更新すべて・B. 上場来高値〔記録上の最高値〕だけ、の2部。どちらも区切りごとの表と最近のケース）
  🆕 2026-10-09 オーナー「上場来高値も同様でお願いします」で B を足した（区切りは同じ・「上場来と言えるか」で分ける）

⚠️ 続伸・だましの区切り（次の日 ±1％・5日後 ±3％）と特徴の区切りは PILLAR_PREREG.md「J44」と下の定数に固定。
⚠️ 判定はしない＝ここで目立った特徴は「候補」。決まりにするなら別に事前登録して、それより後のケースだけで確かめる。
⚠️ 出力は GitHub 側で生成＝手元から送らない（SYNC禁忌）。銘柄名あり＝サイトからはリンクしない（売買の推奨ではない記録）。
⚠️ 失敗しても jp-highs.json には触れない（build_jp_highs が try/except で呼ぶ）。
"""
import csv
import datetime as dt
import io
import json
import math
import os
import time
import urllib.error
import urllib.request

import jp_markers

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_CSV = os.path.join(HERE, "highs-ledger.csv")
OUT_MD = os.path.join(HERE, "highs-ledger.md")
START = "2026-10-08"            # この日の一覧からためる
UP1, DOWN1 = 0.01, -0.01         # 次の日：終値どうしで +1％以上＝続伸・−1％以下＝だまし
UP5, DOWN5 = 0.03, -0.03         # 5日後：+3％以上＝続伸・−3％以下＝だまし
AFTER = 5                        # 5取引日あと
OPEN_RETRY_DAYS = 20             # 次の日の始値が取れなかったケースは、この日数のあいだ取り直す
RECENT_DAYS = 10                 # md の「最近のケース」に出す営業日の数
JST = dt.timezone(dt.timedelta(hours=9))
UA = {"User-Agent": "Mozilla/5.0"}
LABEL_UP, LABEL_FLAT, LABEL_DOWN = "続伸", "横ばい", "だまし"

FEATURES = ("date", "code", "name", "market", "sector", "period", "kind", "record", "listed", "age_days", "akaji",
            "close", "pct", "high", "prev_high", "prev_date", "breakout", "close_vs_prev", "wick", "hi_close",
            "turnover", "tv_ratio", "dev25", "streak", "days_since_prev")
AFTER_COLS = ("d1", "gap1", "oc1", "cc1", "hi1", "below_prev1", "label1", "d5", "cc5", "max5", "min5", "label5")
COLS = FEATURES + AFTER_COLS
NUMERIC = {"record", "listed", "age_days", "akaji", "close", "pct", "high", "prev_high", "breakout", "close_vs_prev",
           "wick", "hi_close", "turnover", "tv_ratio", "dev25", "streak", "days_since_prev",
           "gap1", "oc1", "cc1", "hi1", "below_prev1", "cc5", "max5", "min5"}
INF = math.inf
# (見出し, 列, 区切り)。区切り＝[(名前, 下, 上)]＝「下以上・上未満」／または {値: 名前}（そのままの値で分ける）
BUCKETS = (
    ("上場から", "age_days", [("1年未満", 0, 365), ("1〜3年", 365, 1095), ("3年以上", 1095, INF)]),
    ("上場来の高値か", "record", {1: "上場来（記録上の最高値）", 0: "年初来だけ"}),
    ("その日の上げ", "pct", [("+3％未満", -INF, 0.03), ("+3〜10％", 0.03, 0.10), ("+10％以上", 0.10, INF)]),
    ("売買代金の倍率（その前の20営業日の平均の）", "tv_ratio", [("2倍未満", 0, 2), ("2〜5倍", 2, 5), ("5〜10倍", 5, 10), ("10倍以上", 10, INF)]),
    ("25日線からの離れ", "dev25", [("+10％未満", -INF, 0.10), ("+10〜20％", 0.10, 0.20), ("+20〜30％", 0.20, 0.30), ("+30％以上", 0.30, INF)]),
    ("更新幅（それまでの高値から）", "breakout", [("1％未満", -INF, 0.01), ("1〜3％", 0.01, 0.03), ("3％以上", 0.03, INF)]),
    ("引けとそれまでの高値", "close_vs_prev", [("下で引けた（その日のうちに押し戻された）", -INF, 0), ("上で引けた（保った）", 0, INF)]),
    ("上ヒゲ（高値−終値）÷（高値−安値）", "wick", [("0.3未満", -INF, 0.3), ("0.3〜0.5", 0.3, 0.5), ("0.5以上", 0.5, INF)]),
    ("連騰（続けて上がった日数）", "streak", [("2日以下", 0, 3), ("3日", 3, 4), ("4日以上", 4, INF)]),
    ("それまでの高値からの日数", "days_since_prev", [("5日未満", 0, 5), ("5〜20日", 5, 20), ("20日以上", 20, INF)]),
    ("市場", "market", None),
    ("赤字", "akaji", {1: "赤字", 0: "黒字"}),
    ("その日の売買代金", "turnover", [("1億円未満", 0, 1), ("1〜10億円", 1, 10), ("10億円以上", 10, INF)]),
    ("次の日の窓（寄りでわかる）", "gap1", [("−1％以下", -INF, -0.01), ("±1％未満", -0.01, 0.01), ("+1％以上", 0.01, INF)]),
)
# 🆕 2026-10-09 オーナー「上場来高値も同様でお願いします」＝上場来高値（記録上の最高値）のケースだけの表は、
#    「上場来の高値か」の代わりに「上場の日からの記録か」で分ける（ほかの区切りは同じ）
KIND_LISTED, KIND_RECORD, KIND_YTD = "上場来", "記録上の最高値", "年初来"
RECORD_BUCKETS = (("上場の日からの記録か", "listed", {1: "上場来と言える（上場の日からの記録）",
                                                     0: "記録の始まりが上場より後（2000年ごろからの最高値）"}),) + \
    tuple(b for b in BUCKETS if b[1] != "record")


# ════════════════════ 1件のケース ════════════════════

def _num(x):
    if x is None or x == "":
        return None
    if isinstance(x, bool):
        return int(x)
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _days(a, b):
    try:
        return (dt.date.fromisoformat(b) - dt.date.fromisoformat(a)).days
    except (TypeError, ValueError):
        return None


def label(x, up, down):
    if x is None:
        return ""
    return LABEL_UP if x >= up else LABEL_DOWN if x <= down else LABEL_FLAT


def upto(bars, day):
    """bars＝[(日付, 高値, 安値, 終値, 出来高)] のうち day までの分"""
    return [b for b in bars if b[0] <= day]


def features(row, day, bars, period=""):
    """jp-highs.json の highs の1行と、その日までの日足 → 台帳の特徴（その日の引けでわかるものだけ）"""
    b = upto(bars, day)
    if not b or b[-1][0] != day:
        return None
    _, h, lo, c, _v = b[-1]
    prev_high = _num(row.get("prev"))
    tv = jp_markers.stock_values(b)
    dev, streak = jp_markers.landmine_values(b) if b else (None, None)
    akaji = row.get("akaji")
    record = bool(row.get("record"))
    kind = KIND_LISTED if record and row.get("listed") else KIND_RECORD if record else KIND_YTD
    return {
        "date": day, "code": row.get("code", ""), "name": row.get("name", ""), "market": row.get("market", ""),
        "sector": row.get("sector", ""), "period": period, "kind": kind,
        "record": int(bool(row.get("record"))),
        "listed": "" if row.get("listed") is None else int(bool(row.get("listed"))),
        "age_days": _days(row.get("hist_from"), day),
        "akaji": "" if akaji is None else int(bool(akaji)),
        "close": c, "pct": _num(row.get("pct")), "high": _num(row.get("ext")) or h, "prev_high": prev_high,
        "prev_date": row.get("prev_date") or "",
        "breakout": (h / prev_high - 1) if prev_high else None,
        "close_vs_prev": (c / prev_high - 1) if prev_high else None,
        "wick": (h - c) / (h - lo) if h > lo else 0.0,
        "hi_close": int(c >= h * 0.999),
        "turnover": tv[0] if tv else None, "tv_ratio": tv[1] if tv else None,
        "dev25": dev, "streak": streak,
        "days_since_prev": _days(row.get("prev_date"), day),
    }


def fill_after(case, bars, opens=None):
    """そのあとを埋める。bars＝その銘柄の日足（いまの日まで）・opens＝{日付: 始値}（取れなければ None）。埋めたら True"""
    day = case["date"]
    idx = next((i for i, b in enumerate(bars) if b[0] == day), None)
    if idx is None:
        return False
    c0, h0 = bars[idx][3], bars[idx][1]
    prev_high = _num(case.get("prev_high"))
    changed = False
    if not case.get("d1") and idx + 1 < len(bars):
        d1, h1, _l1, c1, _v1 = bars[idx + 1]
        cc1 = c1 / c0 - 1
        case.update(d1=d1, cc1=cc1, hi1=h1 / h0 - 1, label1=label(cc1, UP1, DOWN1),
                    below_prev1="" if prev_high is None else int(c1 < prev_high))
        changed = True
    if case.get("d1") and _num(case.get("gap1")) is None and opens:
        o1 = opens.get(case["d1"])
        k = next((i for i, b in enumerate(bars) if b[0] == case["d1"]), None)
        if o1 and o1 > 0 and k is not None:
            case.update(gap1=o1 / c0 - 1, oc1=bars[k][3] / o1 - 1)
            changed = True
    if not case.get("d5") and idx + AFTER < len(bars):
        seg = bars[idx + 1: idx + AFTER + 1]
        cc5 = seg[-1][3] / c0 - 1
        case.update(d5=seg[-1][0], cc5=cc5, max5=max(b[1] for b in seg) / h0 - 1, min5=min(b[2] for b in seg) / c0 - 1,
                    label5=label(cc5, UP5, DOWN5))
        changed = True
    return changed


def needs_open(case, today):
    if not case.get("d1") or _num(case.get("gap1")) is not None:
        return False
    age = _days(case["d1"], today)
    return age is not None and age <= OPEN_RETRY_DAYS


# ════════════════════ 次の日の始値（Yahoo の日足） ════════════════════

def parse_opens(result):
    """Yahoo chart の result → {日付JST: 始値}（始値の無いバーは落とす）。純関数"""
    q = result["indicators"]["quote"][0]
    out = {}
    for t, o in zip(result.get("timestamp") or [], q.get("open") or []):
        if o is None:
            continue
        out[dt.datetime.fromtimestamp(t, JST).date().isoformat()] = float(o)
    return out


def fetch_opens(code, rng="3mo", tries=2):
    u = f"https://query1.finance.yahoo.com/v8/finance/chart/{code}.T?range={rng}&interval=1d"
    for k in range(tries):
        try:
            req = urllib.request.Request(u, headers=UA)
            return parse_opens(json.load(urllib.request.urlopen(req, timeout=25))["chart"]["result"][0])
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500:
                time.sleep(3 * (k + 1) ** 2)
                continue
            return {}
        except Exception:  # noqa: BLE001
            time.sleep(1 + k)
    return {}


# ════════════════════ 台帳の読み書き ════════════════════

def _fmt(k, v):
    if v is None:
        return ""
    if k in ("record", "listed", "akaji", "hi_close", "below_prev1", "streak", "age_days", "days_since_prev") and v != "":
        return str(int(v))
    if isinstance(v, float):
        return f"{v:.6g}" if k in ("close", "high", "prev_high", "turnover", "tv_ratio") else f"{v:.5f}"
    return str(v)


def read_ledger(path=OUT_CSV):
    try:
        with open(path, encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.DictReader(fh))
    except OSError:
        return []
    out = []
    for r in rows:
        case = {k: r.get(k, "") for k in COLS}
        for k in NUMERIC:
            if case[k] != "":
                case[k] = _num(case[k])
        out.append(case)
    return out


def to_csv(cases):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(COLS)
    for c in sorted(cases, key=lambda x: (x["date"], x["code"])):
        w.writerow([_fmt(k, c.get(k)) for k in COLS])
    return buf.getvalue()


# ════════════════════ まとめ（読むための表・判定しない） ════════════════════

def bucket_of(spec, x):
    if x is None or x == "":
        return None
    if spec is None:
        return str(x)
    if isinstance(spec, dict):
        return spec.get(int(x)) if isinstance(x, (int, float)) else None
    v = _num(x)
    if v is None:
        return None
    return next((name for name, lo, hi in spec if lo <= v < hi), None)


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def stats(cases):
    done = [c for c in cases if c.get("label1")]
    n = len(done)
    share = lambda lab: (sum(1 for c in done if c["label1"] == lab) / n) if n else None  # noqa: E731
    five = [c for c in cases if c.get("label5")]
    return {"n": n, "up": share(LABEL_UP), "flat": share(LABEL_FLAT), "down": share(LABEL_DOWN),
            "cc1": _mean([_num(c.get("cc1")) for c in done]), "oc1": _mean([_num(c.get("oc1")) for c in done]),
            "n5": len(five), "cc5": _mean([_num(c.get("cc5")) for c in five]),
            "down5": (sum(1 for c in five if c["label5"] == LABEL_DOWN) / len(five)) if five else None}


def tables(cases, buckets=BUCKETS):
    out = []
    for title, col, spec in buckets:
        names = ([n for n, *_ in spec] if isinstance(spec, list) else list(spec.values()) if isinstance(spec, dict)
                 else sorted({str(c.get(col)) for c in cases if c.get(col) not in (None, "")}))
        rows = [(name, stats([c for c in cases if bucket_of(spec, c.get(col)) == name])) for name in names]
        out.append((title, rows))
    return out


def _p(x, d=1):
    return "—" if x is None else f"{x * 100:+.{d}f}％"


def _s(x):
    return "—" if x is None else f"{x * 100:.0f}％"


def _x(x, unit="", d=1):
    return "—" if x is None or x == "" else f"{float(x):.{d}f}{unit}"


def section(cases, buckets, days):
    """全体・その日の特徴ごと・最近のケースの3つの表（render_md の1部ぶん）"""
    st = stats(cases)
    L = ["### 全体", "", "| 件数 | 続伸 | 横ばい | だまし | 次の日の平均（終値どうし） | 次の日の寄り→大引け | 5日後（件数） | 5日後にだまし |",
         "|---:|---:|---:|---:|---:|---:|---:|---:|",
         f"| {st['n']:,} | {_s(st['up'])} | {_s(st['flat'])} | {_s(st['down'])} | {_p(st['cc1'], 2)} | {_p(st['oc1'], 2)} | "
         f"{_p(st['cc5'], 2)}（{st['n5']:,}） | {_s(st['down5'])} |", "",
         "### その日の特徴ごと（次の日の値動き）", ""]
    for title, rows in tables(cases, buckets):
        L += [f"#### {title}", "", "| 区切り | 件数 | 続伸 | だまし | 次の日の平均 | 寄り→大引け | 5日後（件数） |", "|---|---:|---:|---:|---:|---:|---:|"]
        for name, s in rows:
            L.append(f"| {name} | {s['n']:,} | {_s(s['up'])} | {_s(s['down'])} | {_p(s['cc1'], 2)} | {_p(s['oc1'], 2)} | {_p(s['cc5'], 2)}（{s['n5']:,}） |")
        L.append("")
    recent = set(days[-RECENT_DAYS - 1:-1]) if len(days) > 1 else set()
    L += [f"### 最近のケース（次の日まで埋まった {RECENT_DAYS}営業日・だましと続伸）", "",
          "| 日 | 銘柄 | 種類 | 上場から | その日の上げ | 売買代金の倍率 | 25日線から | 更新幅 | 引けと前の高値 | 次の日の窓 | 次の日 | 5日後 |",
          "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|"]
    show = [c for c in cases if c["date"] in recent and c.get("label1") in (LABEL_UP, LABEL_DOWN)]
    for c in sorted(show, key=lambda x: (x["date"], _num(x.get("cc1")) or 0), reverse=True):
        age = _num(c.get("age_days"))
        five = f"{c['label5']} {_p(_num(c.get('cc5')))}" if c.get("label5") else "—"
        L.append(f"| {c['date']} | {c['code']} {c['name']} | {c.get('kind') or ''} | "
                 f"{'—' if age is None else f'{age / 365:.1f}年'} | {_p(_num(c.get('pct')))} | {_x(c.get('tv_ratio'), '倍')} | "
                 f"{_p(_num(c.get('dev25')))} | {_p(_num(c.get('breakout')))} | {_p(_num(c.get('close_vs_prev')))} | "
                 f"{_p(_num(c.get('gap1')))} | **{c.get('label1')}** {_p(_num(c.get('cc1')))} | "
                 f"{five} |")
    return L + [""]


def is_record(c):
    return _num(c.get("record")) == 1


def render_md(cases, now=""):
    days = sorted({c["date"] for c in cases})
    st = stats(cases)
    rec = [c for c in cases if is_record(c)]
    sr = stats(rec)
    L = ["# 高値更新の台帳（J44・読むだけ）", "",
         f"更新: {now}（事前登録＝`PILLAR_PREREG.md`「J44」）。ケース {len(cases):,}件（{days[0] if days else '—'}〜{days[-1] if days else '—'}・"
         f"{len(days)}営業日）・次の日まで埋まった {st['n']:,}件・5日後まで {st['n5']:,}件。全ケースは `highs-ledger.csv`（Excel で開ける）", "",
         f"- うち**上場来高値（記録上の最高値）** {len(rec):,}件（上場来と言える {sum(1 for c in rec if _num(c.get('listed')) == 1):,}件）・"
         f"次の日まで埋まった {sr['n']:,}件。CSV の「kind」列で 上場来／記録上の最高値／年初来 に絞れる",
         "- **ケース**＝その日の大引けで年初来高値を更新した東証の銘柄（サイトの「高値・安値更新」の一覧と同じ）。"
         "上場来高値の更新は年初来の更新の一部（同じ一覧に入る）。上場から20営業日未満の株は一覧に入らない",
         f"- **次の日**：終値どうしで +{UP1 * 100:g}％以上＝**{LABEL_UP}**・{DOWN1 * 100:g}％以下＝**{LABEL_DOWN}**・その間＝{LABEL_FLAT}"
         f"／**5日後**：+{UP5 * 100:g}％以上＝{LABEL_UP}・{DOWN5 * 100:g}％以下＝{LABEL_DOWN}",
         "- **判定はしない**。目立った特徴は「候補」で、決まりにするなら別に事前登録して、それより後のケースだけで確かめる。"
         "件数が少ないうちは割合が大きく揺れる", "",
         "## A. 年初来高値の更新（全部）", ""]
    L += section(cases, BUCKETS, days)
    L += ["## B. 上場来高値の更新（記録上の最高値）だけ", ""]
    L += section(rec, RECORD_BUCKETS, days)
    L += ["## 注意", "",
          "- Yahoo の日足だけで数えている（値の誤り・取れない日がある）。次の日の始値が取れなかったケースは窓と寄り→大引けを空けている",
          "- 「上場来と言える」＝記録の始まりが上場の日と確かめられたもの。古い株は記録の始まりが2000年ごろ＝「記録上の最高値」",
          "- 材料（ニュース・大株主の売り買い・板の様子）は入っていない。セッションで読み解いた事例は `memory/05_highs_casebook.md`",
          "- 過去の数え（J10・J11）では、高値更新の翌朝に寄りで買うと平均で負けやすく、窓 +1％以上で寄るとさらに弱い",
          "", "---", "", "※ 値動きの記録です。投資助言ではありません。将来の値動きを約束するものではありません。"]
    return "\n".join(L) + "\n"


# ════════════════════ 1日の更新 ════════════════════

def update(daily, payload, prev=None, fetch=fetch_opens, path_csv=OUT_CSV, path_md=OUT_MD, now=None, sleep=0.07):
    """build_jp_highs の最後に呼ぶ。daily＝{コード: 日足（いまの日まで）}・payload＝今日の jp-highs.json・prev＝前の jp-highs.json"""
    today = payload["asof"]
    cases = read_ledger(path_csv)
    have = {(c["date"], c["code"]) for c in cases}
    added = 0
    lists = []
    if prev and prev.get("asof") and START <= prev["asof"] < today:
        lists.append((prev["asof"], prev.get("highs") or [], prev.get("period", "")))
    if today >= START:
        lists.append((today, payload.get("highs") or [], payload.get("period", "")))
    for day, rows, period in lists:
        for row in rows:
            code = row.get("code")
            if not code or (day, code) in have or code not in daily:
                continue
            f = features(row, day, daily[code], period)
            if f:
                cases.append(dict({k: "" for k in AFTER_COLS}, **f))
                have.add((day, code))
                added += 1
    filled = opened = 0
    want_open = set()
    for c in cases:
        if c.get("d5") and not needs_open(c, today):
            continue                                  # もう埋まった（または始値を取り直す期間を過ぎた）ケースは見ない
        bars = daily.get(c["code"])
        if c["date"] < today and bars and fill_after(c, bars):
            filled += 1
        if needs_open(c, today):
            want_open.add(c["code"])
    got = {}
    for code in sorted(want_open):
        got[code] = fetch(code) or {}
        if sleep:
            time.sleep(sleep)
    for c in cases:
        if c["code"] in got and needs_open(c, today):
            bars = daily.get(c["code"])
            if bars and fill_after(c, bars, got[c["code"]]):
                opened += 1
    with open(path_csv, "w", encoding="utf-8-sig", newline="") as fh:
        fh.write(to_csv(cases))
    with open(path_md, "w", encoding="utf-8") as fh:
        fh.write(render_md(cases, now or dt.datetime.now(JST).isoformat(timespec="minutes")))
    return f"ケース {len(cases)}件（今回 +{added}）・そのあとを埋めた {filled}件・始値 {opened}件（{len(want_open)}銘柄を取りに行った）"
