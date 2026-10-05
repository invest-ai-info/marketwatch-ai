# -*- coding: utf-8 -*-
"""R4 腕B・腕C 正確なロンドン 08:00→16:00 の窓：その月に株が上がった国の通貨は、月末の値決めの前に売られやすいか。
2026-10-05 夜 登録・オーナー「続けてください」。腕A（fx_month_end_lab.py・日足の近い形）は ◯ 傾向だったが、
同じ決まりを月の真ん中の日に当てても同じくらいプラスだった＝「月末だけの癖」かどうかを、値決め前の数時間で確かめる。

  腕C（クラウド）＝Dukascopy の公開の1分足（売値）・2015-01〜2026-09・費用は腕A と同じ控えめな値（box_lab.cost_price）
  腕B（手元）  ＝MT5（BigBoss）の5分足の書き出し（C:\\mt5run\\m5tick_*.csv）・2022-06-01〜2026-09-24・費用は足の実際のスプレッド
  ⚠️ 判定は元の登録どおり腕B（手元で 2026-10-05 10:36 に数え済み＝差なし）。腕C は同じ問いを別のデータで確かめた数字
     （PREREG「R4 の記録の訂正」。下の「腕C が取れれば腕C が判定」の作りは取り消した補足のなごり）

⚠️ 物差しと判定は PILLAR_PREREG.md「R4」の腕B と「R4 腕B の補足と腕C」（事前登録・計算より先にコミット）と下の定数に固定。
   結果を見てから動かさない。出力には事前登録の中身の指紋（sha256）を書き込む。
⚠️ 出力 r4-window-lab.json / .md（腕C）は GitHub 側で生成＝手元から送らない（SYNC禁忌）。r4-armb.json / .md（腕B）は手元の成果として送る。
⚠️ エンジン・発火条件・固定オラクル（signal_lab_verify.py）には触れない。メールや売買の決まりは変えない。

事前登録の補足に書いた細かい決め方（ここでも固定）:
  - 「その1時間に足がある」＝ティック数／取引量が0より大きい足が1本以上。入る値・出る値はその1時間の最初のそういう足の始値
  - 月の最後の取引日＝ロンドンの平日のうち 08時台と16時台の両方に足がある最後の日。真ん中＝15日以上で両方に足がある最初の平日
  - 月の本当の最後の平日が期間の終わりより後の月は数えない（書き出しが月の途中で終わる月を、月末と取り違えない）
  - 株の上げ＝前の月の最後の終値 → 取引する日の1つ前の平日以前で一番近い終値。差がちょうど0の月は入らない
  - 95%の幅＝月末の取引を月ごとに引き直す（10,000回）。差＝月末と真ん中の和集合の月を一緒に引き直す。片側 p＝(0以下の回数＋1)÷(回数＋1)
  - 探す日の数の上限＝月末は最後の平日から5日、真ん中は15日以上の最初の平日から5日（休場の日をとばすため）

実行:
  腕C（クラウド）     python r4_window_lab.py --source dukascopy        （Actions の r4-window-lab.yml から手動で）
  届くかだけ（数えない） python r4_window_lab.py --probe
  取得だけ（数えない）   python r4_window_lab.py --fetch-only --pair EURUSD --span 2015-01-01,2020-12-31 --cache-dir duka-cache
  腕C を置き場から数える python r4_window_lab.py --source dukascopy --cache-dir duka-cache
  腕B（手元）         python r4_window_lab.py --source mt5 --dir C:\\mt5run
  手元の点検だけ       python r4_window_lab.py --source mt5 --dir C:\\mt5run --check   （損益は数えない）
"""
import argparse
import datetime as dt
import json
import lzma
import os
import sys
import time
import urllib.error
import urllib.request
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from box_lab import cost_price
from fx_month_end_lab import EQ_MAX, PAIR_NAME, PAIRS, US
from hold_lab import clean
from pillar_lab import fetch, prereg_sha256

JST = dt.timezone(dt.timedelta(hours=9))
LON = ZoneInfo("Europe/London")
NY = ZoneInfo("America/New_York")
SYM = {"EURUSD=X": "EURUSD", "GBPUSD=X": "GBPUSD", "USDJPY=X": "USDJPY", "AUDUSD=X": "AUDUSD"}
PERIOD = {"dukascopy": ("2015-01-01", "2026-09-30"), "mt5": ("2022-06-01", "2026-09-24")}
ENTRY_H, EXIT_H = 8, 16
SERVER_SHIFT_H = 7                 # MT5（BigBoss）のサーバー時刻＝ニューヨーク時間＋7時間
SEARCH_DAYS = 5
N_BOOT = 10000
ALPHA = 0.05
SEED = 20261010
MAX_MOVE = 0.08                    # 8時間の窓でこれを超えて動いたらデータの失敗
SPREAD_PIPS_OK = (0.1, 5.0)        # 腕B：08時台のスプレッドの中央値（pips）がこの外なら単位の取り違え
COVER = 0.95                       # 腕C：月末と真ん中の両方が見つかった月の割合
VERDICTS = ("◎ 月末の値決め前に残っている", "月末だけの癖ではない", "差なし")
ARM = {"dukascopy": ("R4C", "腕C", "r4-window-lab.json", "r4-window-lab.md"),
       "mt5": ("R4B", "腕B", "r4-armb.json", "r4-armb.md")}
TITLE = {"R4C": "月末の最後の取引日のロンドン 08:00→16:00 に、その月の株の上げ（外国−米国）がプラスの国の通貨を売る（Dukascopy の1分足・4ペア）",
         "R4B": "同じ決まりを MT5（BigBoss）の5分足と実際のスプレッドで（2022-06〜・4ペア）"}
DUKA_URL = "https://datafeed.dukascopy.com/datafeed/{sym}/{y}/{m:02d}/{d:02d}/BID_candles_min_1.bi5"


def point(pair):
    """値の最小単位（Dukascopy の整数の割り算・MT5 のスプレッドのポイント）"""
    return 0.001 if pair.endswith("JPY=X") else 0.00001


def pip(pair):
    return 0.01 if pair.endswith("JPY=X") else 0.0001


# ---------------------------------------------------------------- 足 → 1日の窓
def windows_from_bars(bars):
    """bars＝UTC の時刻の添字・列 open / vol / spread（値の単位）。
    → {ロンドンの日付: (入る値, 入る足のスプレッド, 出る値, 出る足のスプレッド)}（08時台と16時台の両方に足がある日だけ）"""
    if bars is None or bars.empty:
        return {}
    b = bars[bars["vol"] > 0]
    if b.empty:
        return {}
    loc = b.index.tz_convert(LON)
    df = pd.DataFrame({"date": loc.date, "hour": loc.hour, "open": b["open"].to_numpy(float),
                       "spread": b["spread"].to_numpy(float)}, index=b.index)
    df = df[df["hour"].isin([ENTRY_H, EXIT_H])].sort_index()
    first = df.groupby(["date", "hour"], sort=True).first()
    out = {}
    for day in sorted({d for d, _ in first.index}):
        if (day, ENTRY_H) in first.index and (day, EXIT_H) in first.index:
            e, x = first.loc[(day, ENTRY_H)], first.loc[(day, EXIT_H)]
            out[day] = (float(e["open"]), float(e["spread"]), float(x["open"]), float(x["spread"]))
    return out


def weekdays(y, m):
    d = pd.date_range(f"{y}-{m:02d}-01", periods=pd.Period(f"{y}-{m:02d}").days_in_month, freq="D")
    return [x.date() for x in d if x.weekday() < 5]


FAILED = object()                  # 取得に失敗した日（「足が無い日」とは別）


def pick_day(window_fn, pair, y, m, rule, end):
    """rule＝last：両方に足がある最後の平日／mid：15日以上で両方に足がある最初の平日。見つからなければ None。
    取得に失敗した日（FAILED）に当たったら、次の日へ進まずに None（決まりと違う日を使わない＝その月は見つからなかった扱い）"""
    wd = [d for d in weekdays(y, m) if d <= end]
    cands = wd[::-1][:SEARCH_DAYS] if rule == "last" else [d for d in wd if d.day >= 15][:SEARCH_DAYS]
    for d in cands:
        w = window_fn(pair, d)
        if w is FAILED:
            return None
        if w is not None:
            return d
    return None


def prev_weekday(d):
    d = d - dt.timedelta(days=1)
    while d.weekday() >= 5:
        d -= dt.timedelta(days=1)
    return d


def _asof(s, day):
    v = s.loc[:pd.Timestamp(day)]
    return float(v.iloc[-1]) if len(v) else np.nan


def trade(pair, day, win, equities, src):
    """1回の取引（費用後の損益は率）。向きが決まらなければ None"""
    eq_f, sell_sign = PAIRS[pair]
    base = pd.Timestamp(year=day.year, month=day.month, day=1) - pd.Timedelta(days=1)
    t0 = prev_weekday(day)
    rf = _asof(equities[eq_f], t0) / _asof(equities[eq_f], base) - 1
    ru = _asof(equities[US], t0) / _asof(equities[US], base) - 1
    sig = rf - ru
    if not np.isfinite(sig) or sig == 0:
        return None
    pos = sell_sign if sig > 0 else -sell_sign
    be, se, bx, sx = win
    if src == "mt5":                          # 値は売値。中値で損益を出し、費用＝入る足と出る足のスプレッドの半分ずつ
        me, mx = be + se / 2, bx + sx / 2
        cost = (se / 2 + sx / 2) / me
    else:                                     # Dukascopy：売値のまま・費用は腕A と同じ控えめな値
        me, mx = be, bx
        cost = cost_price(pair) / me
    raw = mx / me - 1
    return {"month": f"{day.year}-{day.month:02d}", "day": str(day), "pair": pair, "signal": float(sig),
            "raw": float(raw), "gross": float(pos * raw), "net": float(pos * raw - cost), "cost": float(cost),
            "spread_pips": float((se + sx) / 2 / pip(pair)) if src == "mt5" else None}


def months_between(start, end):
    s, e = pd.Timestamp(start), pd.Timestamp(end)
    return [(p.year, p.month) for p in pd.period_range(s, e, freq="M")]


def collect(window_fn, equities, start, end, src, pairs=tuple(PAIRS)):
    """→ (月末の取引, 真ん中の取引, ペアごとの見つかった割合)"""
    end_d = pd.Timestamp(end).date()
    rows = {"last": [], "mid": []}
    cover = {p: {"months": 0, "both": 0} for p in pairs}
    for y, m in months_between(start, end):
        if weekdays(y, m)[-1] > end_d or pd.Timestamp(year=y, month=m, day=1) < pd.Timestamp(start).replace(day=1):
            continue
        for pair in pairs:
            cover[pair]["months"] += 1
            days = {r: pick_day(window_fn, pair, y, m, r, end_d) for r in ("last", "mid")}
            if days["last"] and days["mid"]:
                cover[pair]["both"] += 1
            for r, d in days.items():
                if d is None or d < pd.Timestamp(start).date():
                    continue
                t = trade(pair, d, window_fn(pair, d), equities, src)
                if t:
                    rows[r].append(t)
    for p in cover:
        c = cover[p]
        c["share"] = c["both"] / c["months"] if c["months"] else 0.0
    return rows["last"], rows["mid"], cover


# ---------------------------------------------------------------- 物差しと判定
def stats(end_rows, mid_rows, rng, n_boot=N_BOOT):
    e, m = pd.DataFrame(end_rows), pd.DataFrame(mid_rows)
    em = sorted(e["month"].unique())
    g = e.groupby("month")["net"].agg(["sum", "count"]).reindex(em)
    idx = rng.integers(0, len(em), (n_boot, len(em)))
    boot = g["sum"].to_numpy()[idx].sum(axis=1) / g["count"].to_numpy()[idx].sum(axis=1)
    allm = sorted(set(em) | set(m["month"]))
    ge = e.groupby("month")["net"].agg(["sum", "count"]).reindex(allm, fill_value=0)
    gm = m.groupby("month")["net"].agg(["sum", "count"]).reindex(allm, fill_value=0)
    j = rng.integers(0, len(allm), (n_boot, len(allm)))
    ce, cm = ge["count"].to_numpy()[j].sum(axis=1), gm["count"].to_numpy()[j].sum(axis=1)
    ok = (ce > 0) & (cm > 0)
    d = ge["sum"].to_numpy()[j].sum(axis=1)[ok] / ce[ok] - gm["sum"].to_numpy()[j].sum(axis=1)[ok] / cm[ok]
    half = em[len(em) // 2]
    st = {"n": int(len(e)), "months": len(em), "mean": float(e["net"].mean()),
          "lo": float(np.percentile(boot, 2.5)), "hi": float(np.percentile(boot, 97.5)),
          "first": float(e[e["month"] < half]["net"].mean()), "second": float(e[e["month"] >= half]["net"].mean()),
          "half_from": half, "hit_rate": float((e["gross"] > 0).mean()), "mean_gross": float(e["gross"].mean()),
          "mid_n": int(len(m)), "mid_mean": float(m["net"].mean()), "mid_hit_rate": float((m["gross"] > 0).mean()),
          "diff": float(e["net"].mean() - m["net"].mean()),
          "diff_lo": float(np.percentile(d, 2.5)), "diff_hi": float(np.percentile(d, 97.5)),
          "p_diff": (int((d <= 0).sum()) + 1) / (len(d) + 1)}
    st["verdict"] = judge(st)
    return st


def judge(st):
    if not (st["mean"] > 0 and st["lo"] > 0 and st["first"] > 0 and st["second"] > 0):
        return VERDICTS[2]
    return VERDICTS[0] if (st["diff"] > 0 and st["p_diff"] < ALPHA) else VERDICTS[1]


def simple(rows):
    if not rows:
        return {"n": 0, "mean": None}
    x = np.array([r["net"] for r in rows])
    return {"n": len(x), "mean": float(x.mean()), "hit_rate": float((np.array([r["gross"] for r in rows]) > 0).mean())}


def data_problems(rows):
    bad = [r for r in rows if abs(r["raw"]) > MAX_MOVE]
    return [f"{PAIR_NAME[r['pair']]} {r['day']}：8時間で {r['raw'] * 100:+.1f}%（{MAX_MOVE * 100:.0f}% を超える）" for r in bad]


# ---------------------------------------------------------------- データの取り込み：Dukascopy（腕C）
def parse_duka(data, day, pair):
    """Dukascopy の1分足（伸張後のバイト列）→ UTC の添字の DataFrame（open / vol / spread=0）"""
    if not data:
        return pd.DataFrame(columns=["open", "vol", "spread"])
    a = np.frombuffer(data, dtype=np.dtype([("t", ">u4"), ("o", ">u4"), ("c", ">u4"), ("l", ">u4"), ("h", ">u4"), ("v", ">f4")]))
    t0 = pd.Timestamp(day).tz_localize("UTC")
    idx = t0 + pd.to_timedelta(a["t"].astype(np.int64), unit="s")
    return pd.DataFrame({"open": a["o"].astype(float) * point(pair), "vol": a["v"].astype(float), "spread": 0.0}, index=idx)


class Duka:
    """1日ずつ取りに行き、覚えておく。取れなかった日（404 以外の失敗）を数える。
    混雑の断り（429・5xx）は長めに待って取り直す。取りに行く手順の細部で、数える決まりではない"""
    BUSY_WAITS = (5, 15, 30, 60, 90)
    OTHER_WAITS = (2, 4, 8, 16, 32)

    def __init__(self, opener=None, pause=0.2, tries=6, timeout=60, wait=time.sleep, cache_dir=None):
        self.opener = opener or (lambda req: urllib.request.urlopen(req, timeout=timeout))
        self.pause, self.tries, self.wait, self.cache_dir = pause, tries, wait, cache_dir
        self.cache, self.errors, self.fetched, self.times, self.from_disk = {}, [], 0, [], 0

    def _path(self, pair, day):
        return os.path.join(self.cache_dir, f"{SYM[pair]}_{day}.bi5") if self.cache_dir else None

    def _save(self, pair, day, body):
        if self.cache_dir:
            os.makedirs(self.cache_dir, exist_ok=True)
            with open(self._path(pair, day), "wb") as f:
                f.write(body)

    def raw(self, pair, day):
        """伸張後のバイト列（データの無い日は b""・取れなければ None）。cache_dir があれば、取れたものを置いて次は読むだけにする"""
        path = self._path(pair, day)
        if path and os.path.exists(path):
            with open(path, "rb") as f:
                body = f.read()
            self.from_disk += 1
            return lzma.decompress(body) if body else b""
        url = DUKA_URL.format(sym=SYM[pair], y=day.year, m=day.month - 1, d=day.day)
        last = None
        for k in range(self.tries):
            t0 = time.monotonic()
            try:
                with self.opener(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research)"})) as r:
                    body = r.read()
                self.fetched += 1
                self.times.append(time.monotonic() - t0)
                self._save(pair, day, body)
                self.wait(self.pause)
                return lzma.decompress(body) if body else b""
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    self._save(pair, day, b"")
                    return b""
                last = f"HTTP {e.code}"
                waits = self.BUSY_WAITS if (e.code == 429 or e.code >= 500) else self.OTHER_WAITS
            except Exception as e:  # noqa: BLE001  通信の失敗はまとめて数える
                last = f"{type(e).__name__}: {e}"
                waits = self.OTHER_WAITS
            if k < self.tries - 1:
                self.wait(waits[min(k, len(waits) - 1)])
        self.errors.append(f"{SYM[pair]} {day}：{last}")
        return None

    def window(self, pair, day):
        key = (pair, day)
        if key not in self.cache:
            data = self.raw(pair, day)
            self.cache[key] = FAILED if data is None else windows_from_bars(parse_duka(data, day, pair)).get(day)
        return self.cache[key]


def first_candidates(start, end, pairs=tuple(PAIRS)):
    """月ごとに最初に見に行く日（月の最後の平日・15日以上の最初の平日）。休場でとばす日は、あとで1日ずつ取りに行く"""
    end_d = pd.Timestamp(end).date()
    keys = []
    for y, m in months_between(start, end):
        wd = weekdays(y, m)
        if wd[-1] > end_d:
            continue
        mid = [d for d in wd if d.day >= 15]
        for p in pairs:
            keys += [(p, wd[-1])] + ([(p, mid[0])] if mid else [])
    return keys


def fetch_only(pair, span_start, span_end, cache_dir, end=PERIOD["dukascopy"][1], duka=None, budget_min=None, clock=time.monotonic):
    """取得だけ（数えない）：span の月の、月末と真ん中に使う日のファイルを cache_dir に置く。
    取りに行く日は数えるときと同じ pick_day で決める（休場でとばす日も同じ）。→ (取れなかった件数, 取得した件数)
    budget_min を過ぎたら新しい月に入らずに終わる（取れた分は置き場に残る＝数える段が残りを取り直す）"""
    d = duka or Duka(cache_dir=cache_dir)
    end_d = pd.Timestamp(end).date()
    months = [(y, m) for y, m in months_between(span_start, span_end) if weekdays(y, m)[-1] <= end_d]
    t0 = clock()
    for k, (y, m) in enumerate(months):
        if budget_min is not None and clock() - t0 > budget_min * 60:
            print(f"{SYM[pair]}：時間の上限（{budget_min}分）で {y}-{m:02d} から先は取らずに終わる（数える段が取り直す）", flush=True)
            break
        for rule in ("last", "mid"):
            pick_day(d.window, pair, y, m, rule, end_d)
        if (k + 1) % 12 == 0 or k + 1 == len(months):
            med = f"{np.median(d.times):.1f}" if d.times else "—"
            print(f"{SYM[pair]} {y}-{m:02d} まで：取得 {d.fetched}・手元から {d.from_disk}・取れなかった {len(d.errors)}（1回の中央値 {med}秒）", flush=True)
    for e in d.errors:
        print(f"  取れなかった：{e}", flush=True)
    return len(d.errors), d.fetched


# ---------------------------------------------------------------- データの取り込み：MT5 の書き出し（腕B）
def read_mt5_csv(path):
    """ExportBarsEA の5分足（時刻,始値,高値,安値,終値,ティック数,始まりのスプレッド,足の中の最大スプレッド・値は売値）
    → サーバー時刻（時刻のついていない）の DataFrame（time / open / vol / spread_pt）。文字コード・区切り・見出しの有無は自動で見分ける"""
    with open(path, "rb") as f:
        head = f.read(4)
    enc = "utf-16" if head[:2] in (b"\xff\xfe", b"\xfe\xff") else ("utf-8-sig" if head[:3] == b"\xef\xbb\xbf" else "utf-8")
    with open(path, encoding=enc, errors="replace") as f:
        first = f.readline()
    sep = max([",", "\t", ";"], key=first.count)
    has_header = not first.split(sep)[0].strip()[:1].isdigit()
    raw = pd.read_csv(path, sep=sep, encoding=enc, header=None, skiprows=1 if has_header else 0, dtype=str)
    c0 = raw.iloc[:, 0].str.strip()
    rest = raw.iloc[:, 1:]
    if rest.iloc[:, 0].str.strip().str.match(r"^\d{1,2}:\d{2}").all():        # 日付と時刻が別の列
        c0 = c0 + " " + rest.iloc[:, 0].str.strip()
        rest = rest.iloc[:, 1:]
    t = parse_server_time(c0)
    nums = rest.apply(lambda s: pd.to_numeric(s.str.strip(), errors="coerce"))
    return pd.DataFrame({"time": t.to_numpy(), "open": nums.iloc[:, 0].to_numpy(float),
                         "vol": nums.iloc[:, 4].to_numpy(float), "spread_pt": nums.iloc[:, 5].to_numpy(float)})


def parse_server_time(c0):
    """「2022.06.01 00:05」「2022-06-01 00:05:00」・数字（1970年からの秒）のどれでも読む"""
    if c0.str.fullmatch(r"\d+").all():
        return pd.to_datetime(c0.astype(np.int64), unit="s")
    c = c0.str.replace(".", "-", n=2, regex=False)
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return pd.to_datetime(c, format=fmt)
        except (ValueError, TypeError):
            pass
    return pd.to_datetime(c, format="mixed")


def server_to_utc(t):
    """サーバー時刻（ニューヨーク時間＋7時間・時刻のついていない）→ UTC。日曜の朝の夏時間の切り替わりで決まらない時刻は捨てる"""
    ny = (pd.DatetimeIndex(t) - pd.Timedelta(hours=SERVER_SHIFT_H)).tz_localize(NY, ambiguous="NaT", nonexistent="NaT")
    return ny.tz_convert("UTC")


def mt5_bars(df, pair):
    idx = server_to_utc(df["time"])
    b = pd.DataFrame({"open": df["open"].to_numpy(float), "vol": df["vol"].to_numpy(float),
                      "spread": df["spread_pt"].to_numpy(float) * point(pair)}, index=idx)
    return b[b.index.notna()].sort_index()


class Mt5:
    def __init__(self, folder, pairs=tuple(PAIRS), reader=read_mt5_csv):
        self.win, self.info = {}, {}
        for p in pairs:
            path = os.path.join(folder, f"m5tick_{SYM[p]}.csv")
            df = reader(path)
            b = mt5_bars(df, p)
            self.win[p] = windows_from_bars(b)
            self.info[p] = {"path": path, "rows": int(len(df)), "first": str(b.index.min()), "last": str(b.index.max())}

    def window(self, pair, day):
        return self.win[pair].get(day)

    def spread_check(self, start):
        """08時台のスプレッドの中央値（pips）。単位の取り違えを見つけるため（損益は見ない）"""
        out = {}
        s = pd.Timestamp(start).date()
        for p, w in self.win.items():
            v = [x[1] / pip(p) for d, x in w.items() if d >= s]
            out[p] = float(np.median(v)) if v else None
        return out


# ---------------------------------------------------------------- 株（Yahoo の日足）
def load_equity(fetcher=fetch):
    out, failed = {}, []
    for tk in [US] + [v[0] for v in PAIRS.values()]:
        df = fetcher(tk, "1d", start="2013-01-01")
        if df is None:
            failed.append(f"{tk}: 取れない")
            continue
        s = df["Close"].astype(float)
        s, _ = clean(s[s > 0], fx=False)
        ch = s[s.index >= pd.Timestamp("2014-06-01")].pct_change().abs().dropna()
        if len(ch) and ch.max() > EQ_MAX:
            failed.append(f"{tk}: 直したあとも1日 {ch.max() * 100:.1f}%（{ch.idxmax().date()}）が {EQ_MAX * 100:.0f}% を超える")
        out[tk] = s
    return out, failed


# ---------------------------------------------------------------- 出力
def _p(x, nd=3):
    return "—" if x is None else f"{x * 100:+.{nd}f}%"


def armc_status(path=ARM["dukascopy"][2]):
    """腕C の記録があり、データが取れていれば True（＝腕B は読むための数字）"""
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        return bool(d.get("data_ok"))
    except (OSError, ValueError):
        return False


def render_md(out):
    cid = out["id"]
    L = [f"# R4 {out['arm']} 正確なロンドン 08:00→16:00 の窓（月末の値決めの前）", "",
         f"- 生成: {out['generated_jst']}　事前登録の指紋（PILLAR_PREREG.md の sha256）: `{out['prereg_sha256']}`",
         f"- 物差しと判定＝PILLAR_PREREG.md「R4」の腕B と「R4 腕B の補足と腕C」（計算より先にコミット）。期間 {out['period'][0]}〜{out['period'][1]}・1回だけ数えた結果",
         f"- 役目：**{out['role']}**", f"- 決まり：{TITLE[cid]}",
         f"- 費用：{out['cost_note']}", ""]
    if out["failed"]:
        errs = [f"- 取れなかった日：{x}" for x in out.get("fetch_errors", [])[:10]]
        return "\n".join(L + ["## ⚠️ データの取得の失敗", ""] + [f"- {x}" for x in out["failed"][:30]] + errs +
                         ["", "何も数えていない（判定なし）。直し方を登録してから、やり直す。", ""]) + "\n"
    r = out["result"]
    L += ["## 判定", "", "| 判定 | 回数 | 費用後の平均 | 95%の幅 | 前半 | 後半 | 真ん中の日 | 月末−真ん中 | 差の幅 | 差の片側 p |",
          "|---|---|---|---|---|---|---|---|---|---|",
          f"| {r['verdict']} | {r['n']}（{r['months']}か月） | {_p(r['mean'])} | {_p(r['lo'])}〜{_p(r['hi'])} | {_p(r['first'])} | "
          f"{_p(r['second'])} | {_p(r['mid_mean'])}（{r['mid_n']}回） | {_p(r['diff'])} | {_p(r['diff_lo'])}〜{_p(r['diff_hi'])} | {r['p_diff']:.4f} |", "",
          "## 読むための数字（判定には使わない）", "",
          f"- 上がった向きに当たった割合：月末 {r['hit_rate'] * 100:.0f}%／真ん中 {r['mid_hit_rate'] * 100:.0f}%。費用前の月末の平均 {_p(r['mean_gross'])}",
          "", "| ペア | 月末 | 真ん中 |", "|---|---|---|"]
    for p, v in out["reading"]["by_pair"].items():
        L.append(f"| {PAIR_NAME[p]} | {_p(v['end']['mean'])}（{v['end']['n']}回） | {_p(v['mid']['mean'])}（{v['mid']['n']}回） |")
    if out["reading"].get("since_2022_06"):
        v = out["reading"]["since_2022_06"]
        L += ["", f"- 2022-06 以降だけ（腕B と同じ期間）：月末 {_p(v['end']['mean'])}（{v['end']['n']}回）／真ん中 {_p(v['mid']['mean'])}（{v['mid']['n']}回）"]
    if out["reading"].get("spread_pips"):
        L += ["", "- 08時台のスプレッドの中央値（pips）：" + "・".join(f"{PAIR_NAME[p]} {v:.2f}" for p, v in out["reading"]["spread_pips"].items() if v)]
    L += ["", "## 読み方の約束と限界", "",
          "- ◎ のときだけ MT5 のデモで前向き（決まりはそのまま・36回ごとに費用後の平均がマイナスなら止める）。それ以外は検証済みリストへ",
          "- 出る値は 16:00 に始まる足の始値＝値決めの窓（15:57:30〜16:02:30）の直前まで。持ち越しはしない",
          "- 過去の成績は将来を約束しない。研究の記録であり投資助言ではない", ""]
    return "\n".join(L) + "\n"


def run(source, window_fn, equities, start, end, rng):
    end_rows, mid_rows, cover = collect(window_fn, equities, start, end, source)
    return end_rows, mid_rows, cover


def build(source, end_rows, mid_rows, cover, failed, role, rng, today, extra=None):
    cid, arm, _, _ = ARM[source]
    out = {"generated_jst": dt.datetime.now(JST).strftime("%Y-%m-%dT%H:%M+09:00"), "prereg_sha256": prereg_sha256(),
           "kind": "backtest" if role == "判定" else "reading", "section": "R4", "id": cid, "arm": arm, "role": role,
           "period": list(PERIOD[source]), "failed": list(failed), "coverage": cover, "data_ok": False,
           "titles": {cid: TITLE[cid]} if role == "判定" else {}, "verdicts": {},
           "cost_note": ("売値の中値で損益・入る足と出る足の実際のスプレッドの半分ずつ" if source == "mt5"
                         else "腕A と同じ控えめな値（円のペア 1.2pips・ほか 1.8pips の往復）")}
    out["fetch_errors"] = list((extra or {}).pop("fetch_errors", []))
    if source == "dukascopy":
        short = [f"{SYM[p]}：月末と真ん中の両方が見つかった月 {c['share'] * 100:.1f}%（{COVER * 100:.0f}% 未満）"
                 for p, c in cover.items() if c["share"] < COVER]
        out["failed"] += short
    if not out["failed"] and end_rows and mid_rows:
        out["failed"] += data_problems(end_rows + mid_rows)
    if not out["failed"] and end_rows and mid_rows:
        out["data_ok"] = True
        st = stats(end_rows, mid_rows, rng)
        out["result"] = st
        out["reading"] = {"by_pair": {p: {"end": simple([r for r in end_rows if r["pair"] == p]),
                                          "mid": simple([r for r in mid_rows if r["pair"] == p])} for p in PAIRS}}
        if source == "dukascopy":
            out["reading"]["since_2022_06"] = {"end": simple([r for r in end_rows if r["day"] >= "2022-06-01"]),
                                               "mid": simple([r for r in mid_rows if r["day"] >= "2022-06-01"])}
        out["reading"].update(extra or {})
        if role == "判定" and st["verdict"] != VERDICTS[0]:
            out["verdicts"][cid] = {"status": "stop", "decided_on": today, "n": st["n"], "mean": st["mean"], "lo": st["lo"],
                                    "hi": st["hi"], "reason": f"過去のデータで1回だけ数えて{st['verdict']}"}
    elif not out["failed"]:
        out["failed"].append("取引が1回も数えられない")
    out["trades_end"] = [{k: r[k] for k in ("day", "pair", "gross", "net")} for r in end_rows] if out["data_ok"] else []
    return out


def write(out, source):
    _, _, oj, om = ARM[source]
    with open(oj, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    md = render_md(out)
    with open(om, "w", encoding="utf-8") as f:
        f.write(md)
    print(md)


def probe(days=(dt.date(2015, 1, 15), dt.date(2019, 6, 14), dt.date(2024, 3, 15))):
    """届くか・1回の取得に何秒かかるかだけ（値動きは数えない）。足の数と、ロンドン 08時台・16時台に取引量のある足の数を表示"""
    d = Duka()
    ok = True
    for p in PAIRS:
        for day in days:
            t0 = time.monotonic()
            data = d.raw(p, day)
            sec = time.monotonic() - t0
            if data is None:
                ok = False
                print(f"❌ {SYM[p]} {day}：{d.errors[-1]}（{sec:.1f}秒）", flush=True)
                continue
            b = parse_duka(data, day, p)
            h = b[b["vol"] > 0].index.tz_convert(LON).hour
            print(f"✅ {SYM[p]} {day}：{len(b)}本（取引量あり {(b['vol'] > 0).sum()}本・ロンドン08時台 {(h == ENTRY_H).sum()}本・"
                  f"16時台 {(h == EXIT_H).sum()}本）・{sec:.1f}秒", flush=True)
    if d.times:
        print(f"1回の取得の秒数（取り直しの待ちを除く）：中央値 {np.median(d.times):.1f}・最大 {max(d.times):.1f}", flush=True)
    print("届く" if ok else "一部届かない", flush=True)
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="R4 腕B・腕C 正確なロンドン 08:00→16:00 の窓")
    ap.add_argument("--source", choices=["dukascopy", "mt5"], default="dukascopy")
    ap.add_argument("--dir", default=r"C:\mt5run", help="腕B：m5tick_*.csv のあるフォルダ")
    ap.add_argument("--probe", action="store_true", help="Dukascopy に届くかだけ（数えない）")
    ap.add_argument("--check", action="store_true", help="腕B：読めた行・時刻・スプレッドだけ（損益は数えない）")
    ap.add_argument("--fetch-only", action="store_true", help="腕C：取得だけ（数えない）。--pair と --span と --cache-dir と一緒に")
    ap.add_argument("--pair", default=None, help="EURUSD など（--fetch-only のとき）")
    ap.add_argument("--span", default=None, help="取得する月の範囲 2015-01-01,2020-12-31（--fetch-only のとき）")
    ap.add_argument("--cache-dir", default=None, help="腕C：取得したファイルの置き場（リポジトリには入れない）")
    ap.add_argument("--budget-min", type=float, default=None, help="--fetch-only の時間の上限（分）")
    a = ap.parse_args(argv)
    if a.probe:
        return probe()
    if a.fetch_only:
        pair = {v: k for k, v in SYM.items()}[a.pair]
        s0, s1 = a.span.split(",")
        n_err, _ = fetch_only(pair, s0, s1, a.cache_dir, budget_min=a.budget_min)
        return 0 if n_err == 0 else 1
    start, end = PERIOD[a.source]
    rng = np.random.default_rng(SEED)
    today = str(dt.datetime.now(JST).date())
    if a.source == "mt5":
        src = Mt5(a.dir)
        sp = src.spread_check(start)
        for p, info in src.info.items():
            print(f"{SYM[p]}：{info['rows']}行・{info['first']}〜{info['last']}（UTC）・"
                  f"08時台のスプレッドの中央値 {sp[p] if sp[p] is None else round(sp[p], 2)} pips")
        failed = [f"{SYM[p]}：08時台のスプレッドの中央値 {v} pips が {SPREAD_PIPS_OK} の外（単位の取り違え？）"
                  for p, v in sp.items() if v is None or not (SPREAD_PIPS_OK[0] <= v <= SPREAD_PIPS_OK[1])]
        if a.check:
            print("点検だけ（損益は数えていない）。" + ("⚠️ " + " / ".join(failed) if failed else "問題なし"))
            return 1 if failed else 0
        role = "読むための数字（腕C が判定）" if armc_status() else "判定"
        extra = {"spread_pips": sp}
        window_fn = src.window
    else:
        src = Duka(cache_dir=a.cache_dir)
        failed, role, extra, window_fn = [], "判定", {}, src.window
    equities, eq_failed = load_equity()
    failed = list(failed) + eq_failed
    end_rows, mid_rows, cover = ([], [], {}) if failed else run(a.source, window_fn, equities, start, end, rng)
    if a.source == "dukascopy":
        extra["fetch_errors"] = src.errors[:20]
        extra["fetched_files"] = src.fetched
        extra["from_cache"] = src.from_disk
        print(f"手元から {src.from_disk}・新しく取得 {src.fetched}・取れなかった {len(src.errors)}件", flush=True)
    out = build(a.source, end_rows, mid_rows, cover, failed, role, rng, today, extra)
    write(out, a.source)
    return 0 if not out["failed"] else 1


if __name__ == "__main__":
    sys.exit(main())
