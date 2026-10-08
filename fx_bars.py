# -*- coding: utf-8 -*-
"""為替の値段の置き場（FX の研究ラボ共通）。2026-10-07 オーナー「FX短期トレードの期待値向上の研究を加速させてください」。

これまでの為替のラボ（S1〜S3・L1〜L4・C1 など）は Yahoo の1時間足＝**過去730日（約2年）しか取れず**、
1つの問いに使える回数が少なく（判定の力が弱い）、選ぶ期間と確かめる期間にも分けられなかった。
ここで **Dukascopy の1時間足（売値 BID と買値 ASK）を12ペア×2012年から**、1回だけ並列に取って actions/cache に置く。
各ラボはそこから読む＝数秒。売値と買値の両方があるので、**その時間の実際の売り買いの差（スプレッド）**も分かる。

- 取るもの：`https://datafeed.dukascopy.com/datafeed/<ペア>/<年>/<月-1>/<BID|ASK>_candles_hour_1.bi5`
  （月ごとのファイル・LZMA で縮めた 24バイトの並び＝月の初めからの秒・始・終・安・高・取引量。値は整数で、円のペアは 1/1000・ほかは 1/100000）
- 置き方：受け取ったファイルをそのまま `fx-bars/raw/<ペア>/<BID|ASK>/<YYYY-MM>.bi5` に置く（無いと言われた月は空のファイル＝取り直さない）。
  取れなかった月（混雑・通信の失敗）は置かない＝次の実行で取り直す
- 読み方：`load(pair)` → UTC の時刻ごとの売値と買値の始高安終・取引量（取引量のある時間だけ）
- ⚠️ 置き場は**作った日までのデータ**。ラボの出力には `info()`（作った日時・そろっている月の数）を書く
- ⚠️ リポジトリには入れない（`fx-bars/` は SYNC 禁忌・.gitignore）。actions/cache と artifact だけ

使い方（Actions の fx-bars-cache.yml から）:
  python fx_bars.py probe                                   # 届くか・1回の秒数・中身の点検だけ（何も置かない）
  python fx_bars.py fetch --shard 0 --of 16 --budget-min 300   # 置き場に無い月だけ取り、新しく取ったものを fx-new/ に置く
  python fx_bars.py merge --new fx-new                      # fx-new/ を fx-bars/ に重ね、INFO.json（そろっている月）を書く
ラボ側:  import fx_bars;  df = fx_bars.load("USDJPY")
"""
import argparse
import datetime as dt
import json
import lzma
import os
import shutil
import sys
import time
import urllib.error
import urllib.request

import numpy as np
import pandas as pd

JST = dt.timezone(dt.timedelta(hours=9))
PAIRS = ("EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCHF", "USDCAD", "NZDUSD",
         "EURJPY", "GBPJPY", "AUDJPY", "EURAUD", "GBPAUD")          # サイトの為替9ペア＋ドルのペア3つ
SIDES = ("BID", "ASK")
START = (2012, 1)
EARLY = ((2004, 1), (2011, 12))       # 🆕 2026-10-08 確かめ用の昔の期間（X の結果を見たあとに足した・XC だけが使う）
ROOT = os.environ.get("FX_BARS", "fx-bars")
NEW = "fx-new"
URL = "https://datafeed.dukascopy.com/datafeed/{pair}/{y}/{m0:02d}/{side}_candles_hour_1.bi5"
REC = np.dtype([("t", ">u4"), ("o", ">u4"), ("c", ">u4"), ("l", ">u4"), ("h", ">u4"), ("v", ">f4")])
# 点検用の値の範囲（2004年以降。外れたら単位の取り違え＝置かない）
SANE = {"EURUSD": (0.8, 1.7), "GBPUSD": (0.9, 2.2), "USDJPY": (60, 220), "AUDUSD": (0.4, 1.2), "USDCHF": (0.6, 1.4),
        "USDCAD": (0.85, 1.7), "NZDUSD": (0.4, 1.0), "EURJPY": (80, 230), "GBPJPY": (100, 260), "AUDJPY": (50, 140),
        "EURAUD": (1.0, 2.2), "GBPAUD": (1.4, 2.6)}


def point(pair):
    return 0.001 if pair.endswith("JPY") else 0.00001


def pip(pair):
    return 0.01 if pair.endswith("JPY") else 0.0001


def last_full_month(today=None):
    """今日の前の月（月ごとのファイルは、その月が終わってから取る）"""
    t = today or dt.datetime.now(dt.timezone.utc).date()
    first = t.replace(day=1)
    p = first - dt.timedelta(days=1)
    return p.year, p.month


def months(start=START, end=None):
    end = end or last_full_month()
    y, m = start
    out = []
    while (y, m) <= tuple(end):
        out.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def raw_path(root, pair, side, y, m):
    return os.path.join(root, "raw", pair, side, f"{y}-{m:02d}.bi5")


def tasks(pairs=PAIRS, start=START, end=None):
    """（ペア, 売値/買値, 年, 月）の一覧。並びは固定＝台への割り振りが毎回同じ"""
    return [(p, s, y, m) for p in pairs for s in SIDES for (y, m) in months(start, end)]


def shard(items, k, n):
    return [x for i, x in enumerate(items) if i % n == k]


# ════════════════════ 読み取り ════════════════════

def parse(data, y, m, pair):
    """伸張後のバイト列 → UTC の時刻の DataFrame（o h l c v）。時刻は月の初め（UTC）からの秒"""
    if not data:
        return pd.DataFrame(columns=["o", "h", "l", "c", "v"], dtype=float)
    if len(data) % REC.itemsize:
        raise ValueError(f"{pair} {y}-{m:02d}：長さ {len(data)} が {REC.itemsize} の倍数でない")
    a = np.frombuffer(data, dtype=REC)
    t0 = pd.Timestamp(year=y, month=m, day=1, tz="UTC")
    idx = t0 + pd.to_timedelta(a["t"].astype(np.int64), unit="s")
    k = point(pair)
    return pd.DataFrame({"o": a["o"] * k, "h": a["h"] * k, "l": a["l"] * k, "c": a["c"] * k,
                         "v": a["v"].astype(float)}, index=idx)


def check_month(df, y, m, pair):
    """中身の点検（置く前）。問題があれば文、なければ None"""
    if df.empty:
        return None
    lo, hi = SANE[pair]
    t0 = pd.Timestamp(year=y, month=m, day=1, tz="UTC")
    t1 = t0 + pd.offsets.MonthBegin(1)
    if df.index.min() < t0 or df.index.max() >= t1:
        return f"時刻が月の外（{df.index.min()}〜{df.index.max()}）"
    live = df[df["v"] > 0]
    if len(live) and not (lo <= live["c"].median() <= hi):
        return f"値の中央値 {live['c'].median():.5g} が {lo}〜{hi} の外（単位の取り違え）"
    if (live["h"] < live["l"]).any():
        return "高値が安値より下の足がある"
    return None


def _read(path, y, m, pair):
    with open(path, "rb") as f:
        body = f.read()
    return parse(lzma.decompress(body) if body else b"", y, m, pair)


def load(pair, root=None, start=None, end=None):
    """1ペアの1時間足（UTC）。列＝bo bh bl bc（売値）・ao ah al ac（買値）・v（売値側の取引量）。
    取引量のある時間で、売値と買値の両方がそろう時間だけ。置き場に無い月は飛ばす（そろい具合は coverage() で見る）"""
    root = root or ROOT
    parts = []
    for (y, m) in months(start or START, end):
        sides = {}
        for s in SIDES:
            p = raw_path(root, pair, s, y, m)
            if not os.path.exists(p):
                break
            sides[s] = _read(p, y, m, pair)
        if len(sides) < 2 or sides["BID"].empty or sides["ASK"].empty:
            continue
        b = sides["BID"].add_prefix("b")
        a = sides["ASK"][["o", "h", "l", "c"]].add_prefix("a")
        j = b.join(a, how="inner")
        parts.append(j[j["bv"] > 0])
    if not parts:
        return pd.DataFrame(columns=["bo", "bh", "bl", "bc", "bv", "ao", "ah", "al", "ac"])
    df = pd.concat(parts).sort_index()
    df = df[~df.index.duplicated(keep="first")]
    return df.rename(columns={"bv": "v"})


def coverage(root=None, pairs=PAIRS, start=START, end=None):
    """ペア×売値/買値ごとに、置き場にある月の数・足りない月"""
    root = root or ROOT
    ms = months(start, end)
    out = {}
    for p in pairs:
        for s in SIDES:
            miss = [f"{y}-{m:02d}" for (y, m) in ms if not os.path.exists(raw_path(root, p, s, y, m))]
            out[f"{p}/{s}"] = {"have": len(ms) - len(miss), "want": len(ms), "missing": miss}
    return out


def info(root=None):
    """ラボの出力に書く、置き場の情報（無ければ None）"""
    path = os.path.join(root or ROOT, "INFO.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        meta = json.load(f)
    cov = meta.get("coverage", {})
    return {"built_at": meta.get("built_at"), "months": meta.get("months"),
            "complete": sum(1 for v in cov.values() if v["have"] == v["want"]), "series": len(cov)}


# ════════════════════ 取得 ════════════════════

class Fetcher:
    """1か月ずつ取りに行く。無いと言われた月（404）は空のファイルを置く（取り直さない）。
    混雑の断り（429・5xx）は長めに待って取り直す。取りに行く手順の細部で、数える決まりではない"""
    BUSY_WAITS = (5, 15, 30, 60, 90)
    OTHER_WAITS = (2, 4, 8, 16, 32)

    def __init__(self, opener=None, pause=0.2, tries=6, timeout=90, wait=time.sleep):
        self.opener = opener or (lambda req: urllib.request.urlopen(req, timeout=timeout))
        self.pause, self.tries, self.wait = pause, tries, wait
        self.errors, self.fetched, self.empty, self.times = [], 0, 0, []

    def get(self, pair, side, y, m):
        """縮めたままのバイト列（無い月は b""）・取れなければ None"""
        url = URL.format(pair=pair, y=y, m0=m - 1, side=side)
        last = None
        for k in range(self.tries):
            t0 = time.monotonic()
            try:
                with self.opener(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research)"})) as r:
                    body = r.read()
                self.times.append(time.monotonic() - t0)
                self.wait(self.pause)
                return body
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    return b""
                last = f"HTTP {e.code}"
                waits = self.BUSY_WAITS if (e.code == 429 or e.code >= 500) else self.OTHER_WAITS
            except Exception as e:  # noqa: BLE001  通信の失敗はまとめて数える
                last = f"{type(e).__name__}: {e}"
                waits = self.OTHER_WAITS
            if k < self.tries - 1:
                self.wait(waits[min(k, len(waits) - 1)])
        self.errors.append(f"{pair} {side} {y}-{m:02d}：{last}")
        return None


def save(root, pair, side, y, m, body):
    p = raw_path(root, pair, side, y, m)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as f:
        f.write(body)


def fetch(items, have_root=None, new_root=NEW, fetcher=None, budget_min=None, clock=time.monotonic, log=print):
    """置き場（have_root）に無い月だけ取り、点検に通ったものを new_root に置く。budget_min を過ぎたら新しい月に入らない。
    → 数（取得・空・点検で落とした・取れなかった・時間切れで残した）"""
    have_root = have_root or ROOT
    f = fetcher or Fetcher()
    todo = [x for x in items if not os.path.exists(raw_path(have_root, *x))]
    t0 = clock()
    bad, left = [], 0
    for i, (p, s, y, m) in enumerate(todo):
        if budget_min is not None and clock() - t0 > budget_min * 60:
            left = len(todo) - i
            log(f"時間の上限（{budget_min}分）で残り {left} 件は取らずに終わる（次の実行で取る）")
            break
        body = f.get(p, s, y, m)
        if body is None:
            continue
        if body:
            try:
                prob = check_month(parse(lzma.decompress(body), y, m, p), y, m, p)
            except Exception as e:  # noqa: BLE001
                prob = f"{type(e).__name__}: {e}"
            if prob:
                bad.append(f"{p} {s} {y}-{m:02d}：{prob}")
                continue
            f.fetched += 1
        else:
            f.empty += 1
        save(new_root, p, s, y, m, body)
        if (i + 1) % 50 == 0:
            med = f"{np.median(f.times):.1f}" if f.times else "—"
            log(f"{i + 1}/{len(todo)}：取得 {f.fetched}・空 {f.empty}・点検で落とした {len(bad)}・取れなかった {len(f.errors)}（1回の中央値 {med}秒）")
    for e in f.errors + bad:
        log(f"  ⚠️ {e}")
    return {"todo": len(todo), "fetched": f.fetched, "empty": f.empty, "bad": len(bad), "failed": len(f.errors), "left": left}


def merge(new_root=NEW, root=None, today=None):
    """new_root の月を置き場に重ね（同じ月は新しいほうで上書き）、INFO.json を書く → coverage"""
    root = root or ROOT
    src = os.path.join(new_root, "raw")
    n = 0
    if os.path.isdir(src):
        for d, _, files in os.walk(src):
            for fn in files:
                rel = os.path.relpath(os.path.join(d, fn), src)
                dst = os.path.join(root, "raw", rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copyfile(os.path.join(d, fn), dst)
                n += 1
    end = last_full_month(today)
    cov = coverage(root, end=end)
    early = coverage(root, start=EARLY[0], end=EARLY[1])
    meta = {"built_at": dt.datetime.now(JST).isoformat(timespec="minutes"), "months": [f"{START[0]}-{START[1]:02d}", f"{end[0]}-{end[1]:02d}"],
            "added": n, "coverage": cov}
    if any(v["have"] for v in early.values()):           # 昔の期間を取ったときだけ書く
        meta["early_months"] = [f"{EARLY[0][0]}-{EARLY[0][1]:02d}", f"{EARLY[1][0]}-{EARLY[1][1]:02d}"]
        meta["coverage_early"] = early
    os.makedirs(root, exist_ok=True)
    with open(os.path.join(root, "INFO.json"), "w", encoding="utf-8") as fo:
        json.dump(meta, fo, ensure_ascii=False, indent=1)
    return n, cov


# ════════════════════ 点検 ════════════════════

def probe(pairs=("EURUSD", "USDJPY"), when=((2012, 3), (2019, 6), (2026, 8)), fetcher=None):
    """届くか・1回の取得の秒数・中身（時刻・値の範囲・売り買いの差）だけ。何も置かない・値動きは数えない"""
    f = fetcher or Fetcher()
    ok = True
    for p in pairs:
        for (y, m) in when:
            got = {}
            for s in SIDES:
                t0 = time.monotonic()
                body = f.get(p, s, y, m)
                sec = time.monotonic() - t0
                if body is None:
                    ok = False
                    print(f"❌ {p} {s} {y}-{m:02d}：{f.errors[-1]}（{sec:.1f}秒）", flush=True)
                    continue
                df = parse(lzma.decompress(body) if body else b"", y, m, p)
                prob = check_month(df, y, m, p)
                live = df[df["v"] > 0]
                ok = ok and prob is None and len(live) > 0
                print(f"{'✅' if prob is None and len(live) else '❌'} {p} {s} {y}-{m:02d}：{len(df)}本（取引量あり {len(live)}本）"
                      f"・{df.index.min() if len(df) else '—'}〜{df.index.max() if len(df) else '—'}"
                      f"・終値の中央値 {live['c'].median() if len(live) else float('nan'):.5g}・{sec:.1f}秒"
                      + (f"・{prob}" if prob else ""), flush=True)
                got[s] = live
            if len(got) == 2 and len(got["BID"]) and len(got["ASK"]):
                j = got["BID"].join(got["ASK"], lsuffix="_b", rsuffix="_a", how="inner")
                spr = (j["c_a"] - j["c_b"]) / pip(p)
                print(f"   売り買いの差（終値・pips）：中央値 {spr.median():.2f}・10%点 {spr.quantile(.1):.2f}・90%点 {spr.quantile(.9):.2f}"
                      f"・マイナス {int((spr < 0).sum())}本", flush=True)
                ok = ok and 0 < spr.median() < 10
    if f.times:
        print(f"1回の取得の秒数（取り直しの待ちを除く）：中央値 {np.median(f.times):.1f}・最大 {max(f.times):.1f}", flush=True)
    print("届く・中身も正しい" if ok else "一部届かない／中身がおかしい", flush=True)
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("probe")
    f = sub.add_parser("fetch")
    f.add_argument("--shard", type=int, required=True)
    f.add_argument("--of", type=int, required=True)
    f.add_argument("--budget-min", type=float, default=None)
    f.add_argument("--period", choices=("main", "early"), default="main")
    mg = sub.add_parser("merge")
    mg.add_argument("--new", default=NEW)
    sub.add_parser("coverage")
    a = ap.parse_args(argv)
    if a.cmd == "probe":
        return probe()
    if a.cmd == "fetch":
        items = shard(tasks() if a.period == "main" else tasks(start=EARLY[0], end=EARLY[1]), a.shard, a.of)
        print(f"台 {a.shard}/{a.of}：{len(items)}件（置き場にある月は取らない）", flush=True)
        st = fetch(items, budget_min=a.budget_min, log=lambda s: print(s, flush=True))
        print(f"結果：{st}", flush=True)
        return 0
    if a.cmd == "merge":
        n, cov = merge(a.new)
        full = sum(1 for v in cov.values() if v["have"] == v["want"])
        print(f"重ねた月 {n}・そろった系列 {full}/{len(cov)}")
        print("| ペア/側 | ある月 | 欲しい月 | 足りない月（先頭5つ） |\n|---|---|---|---|")
        for k, v in cov.items():
            print(f"| {k} | {v['have']} | {v['want']} | {', '.join(v['missing'][:5])} |")
        early = coverage(start=EARLY[0], end=EARLY[1])
        if any(v["have"] for v in early.values()):
            print(f"\n昔の期間（{EARLY[0][0]}〜{EARLY[1][0]}）\n| ペア/側 | ある月 | 欲しい月 | 足りない月（先頭5つ） |\n|---|---|---|---|")
            for k, v in early.items():
                print(f"| {k} | {v['have']} | {v['want']} | {', '.join(v['missing'][:5])} |")
        return 0
    cov = coverage()
    for k, v in cov.items():
        print(k, v["have"], "/", v["want"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
