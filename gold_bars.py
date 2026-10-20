# -*- coding: utf-8 -*-
"""金（XAUUSD）の1分足（売値 BID・買値 ASK）を Dukascopy から1日ずつ取って置く（KJG・2026-10-20）。
取るだけ＝値動きは見ない。手元でも Actions（gold-bars-fetch.yml・16台に分ける）でも同じものを使う。

- 取るもの：`https://datafeed.dukascopy.com/datafeed/XAUUSD/<年>/<月-1>/<日>/<BID|ASK>_candles_min_1.bi5`（時刻は UTC）
- 置き方：`<root>/<BID|ASK>/YYYY-MM-DD.bi5`（無いと言われた日＝空のファイル・取り直さない）。土曜は取らない
- 取れなかった日（混雑・時間切れ）は置かない＝もう一度回せば無いファイルだけ取る
- Dukascopy は1件に10〜30秒かかる。手元から同時10件で1分に約16件（同時30件は時間切れが増えて遅い）＝台を分けると速い
- ⚠️ リポジトリには置かない（手元の置き場は C:\\mt5run\\duka_xau・Actions は artifact だけ）

  python gold_bars.py fetch --first 2021-09-01 --last 2026-09-30 [--root DIR] [--shard 0 --of 16] [--workers 10] [--newest-first]
"""
import argparse
import concurrent.futures as cf
import datetime as dt
import os
import sys
import time
import urllib.error
import urllib.request

try:
    import truststore   # 手元（ノートンの証明書で SSL が落ちるため Windows の証明書の置き場を使う）。Actions には無くてよい
    truststore.inject_into_ssl()
except ImportError:
    pass

URL = "https://datafeed.dukascopy.com/datafeed/XAUUSD/{y}/{m0:02d}/{d:02d}/{side}_candles_min_1.bi5"
SIDES = ("BID", "ASK")
BUSY_WAITS = (5, 15, 30, 60, 90)
OTHER_WAITS = (2, 4, 8, 16, 32)
LOCAL_ROOT = r"C:\mt5run\duka_xau"


def path_of(root, side, day):
    return os.path.join(root, side, f"{day.isoformat()}.bi5")


def days(first, last):
    d = first
    while d <= last:
        if d.weekday() != 5:          # 土曜は市場が閉じている
            yield d
        d += dt.timedelta(days=1)


def items(first, last, shard=0, of=1, newest_first=False):
    """(向き, 日) の一覧。台に分けるときは i 番目ごと（日の順に並べてから）"""
    xs = [(s, d) for d in days(first, last) for s in SIDES]
    xs = xs[shard::of]
    return xs[::-1] if newest_first else xs


def get(side, day, tries=6, pause=0.3, timeout=90):
    """→ バイト列（無い日は b""）か、取れなかった理由の文字列"""
    url = URL.format(y=day.year, m0=day.month - 1, d=day.day, side=side)
    last = "失敗"
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research)"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read()
            time.sleep(pause)
            return body
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return b""
            last = f"HTTP {e.code}"
            waits = BUSY_WAITS if (e.code == 429 or e.code >= 500) else OTHER_WAITS
        except Exception as e:  # noqa: BLE001  通信の失敗はまとめて数える
            last = type(e).__name__
            waits = OTHER_WAITS
        if k < tries - 1:
            time.sleep(waits[min(k, len(waits) - 1)])
    return last


def save(root, side, day, body):
    p = path_of(root, side, day)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".part"
    with open(tmp, "wb") as f:
        f.write(body)
    os.replace(tmp, p)


def fetch(root, todo, workers, budget_min=None, log=print):
    errs, done, t0 = [], 0, time.monotonic()

    def job(item):
        if budget_min is not None and (time.monotonic() - t0) / 60 > budget_min:
            return item, "時間切れ（予算）"
        side, day = item
        body = get(side, day)
        if isinstance(body, str):
            return item, body
        save(root, side, day, body)
        return item, None

    with cf.ThreadPoolExecutor(workers) as ex:
        for item, err in ex.map(job, todo):
            done += 1
            if err:
                errs.append(f"{item[0]} {item[1]}: {err}")
            if done % 200 == 0:
                log(f"  {done}/{len(todo)} failed {len(errs)} {(time.monotonic() - t0) / 60:.1f}min")
    return errs


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["fetch"])
    ap.add_argument("--first", default="2021-09-01")
    ap.add_argument("--last", default="2026-09-30")
    ap.add_argument("--root", default=LOCAL_ROOT)
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--of", type=int, default=1)
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--budget-min", type=float, default=None)
    ap.add_argument("--newest-first", action="store_true")
    a = ap.parse_args(argv)
    first, last = dt.date.fromisoformat(a.first), dt.date.fromisoformat(a.last)
    todo = [x for x in items(first, last, a.shard, a.of, a.newest_first) if not os.path.exists(path_of(a.root, *x))]
    print(f"to fetch {len(todo)} (shard {a.shard}/{a.of}, existing files skipped)", flush=True)
    errs = fetch(a.root, todo, a.workers, a.budget_min, log=lambda s: print(s, flush=True))
    os.makedirs(a.root, exist_ok=True)
    with open(os.path.join(a.root, f"fetch-errors-{a.shard}.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(errs))
    print(f"done: {len(todo)} items, failed {len(errs)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
