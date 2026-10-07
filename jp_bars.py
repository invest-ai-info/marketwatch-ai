# -*- coding: utf-8 -*-
"""東証の全上場の値段の置き場（研究ラボ共通）。2026-10-06 夜 オーナー「研究ペースをもっと加速させてください」。

これまでは研究ラボ1本ごとに約3,700銘柄×3種類の足を Yahoo から取り直し、1回45〜60分（点検と本番で2回）かかっていた。
ここで **1回だけ8台で並列に取って1つのファイルにまとめ、actions/cache に置く**。各ラボはそこから読む＝数秒。

- 取るもの：日足 取れる全期間（1990-01-01〜を period1 で頼む。ラボが 10年・5年を頼めばそこで切って返す。取れた足が日ごとでなければ10年に戻す）／
  1時間足 729日（だめなら1年）／5分足 60日（だめなら1か月）
- 置き方：足の種類ごとに「銘柄の番号・時刻（秒）・始高安終出来高（float32）」の配列。Yahoo の値はもともと float32 の精度
- 読み方：`fetch(code, interval, rng)` は yori_lab.fetch_chart と同じ形（[(JST の時刻, 始, 高, 安, 終, 出来高)]）を返す。
  置き場に無い足の種類・銘柄は Yahoo から取る（遅いが同じ答え）。範囲（rng＝5y・729d・60d など）は置き場を作った日から数えて切る
- ⚠️ 置き場は**作った日のデータ**。ラボの出力には置き場を作った日時と一覧の日付を書く（`info()`）
- ⚠️ リポジトリには入れない（大きい・銘柄ごとの値段＝Pages で配信されてしまう）。actions/cache と artifact だけ

使い方（Actions の jp-bars-cache.yml から）:
  python jp_bars.py fetch --shard 0 --of 8 --out part-0.npz
  python jp_bars.py merge --out jp-bars/jp-bars.npz part-*.npz
ラボ側:  import jp_bars;  fetch = jp_bars.fetcher();  stocks, list_date = jp_bars.load_universe()
"""
import argparse
import datetime as dt
import glob
import json
import os
import re
import sys
import time

import numpy as np

import build_jp_highs as H
import highs_trap_lab as T
import pillar_lab as P
import yori_lab as Y

DEFAULT_PATH = os.environ.get("JP_BARS", "jp-bars/jp-bars.npz")
FULL_DAILY = "from:1990"     # 日足の全期間＝1990-01-01〜今日を period1 で頼む（range=max は月ごとの足が返った・2026-10-07）
SPECS = (("1d", (FULL_DAILY, "10y")), ("60m", T.H1_RANGES), ("5m", T.M5_RANGES))   # 日足は取れる全期間（2026-10-07 J18・2016年より前で確かめるため）
DAILY_MAX_SPACING = 5         # 日足の間隔の中央値（暦日）がこれを超えたら日足ではない＝次の範囲（10年）で取り直す
RANGE_DAYS = {"d": 1, "mo": 30.44, "y": 365.25}
IV_KEY = {"1d": "d", "60m": "h", "5m": "m"}


# ════════════════════ 取る（1台分） ════════════════════

def shard_codes(codes, shard, of):
    """並べた銘柄を of 台に順番に配る（0, of, 2·of … が shard 0）"""
    return [c for i, c in enumerate(sorted(codes)) if i % of == shard]


def _pack(rows_by_code, codes):
    """{code: [(datetime, o, h, l, c, v)]} → (銘柄番号 int32, 時刻 int64, 値 float32[n,5])"""
    idx, ts, vals = [], [], []
    for i, code in enumerate(codes):
        rows = rows_by_code.get(code) or []
        if not rows:
            continue
        idx.append(np.full(len(rows), i, np.int32))
        ts.append(np.fromiter((int(r[0].timestamp()) for r in rows), np.int64, len(rows)))
        vals.append(np.array([r[1:6] for r in rows], np.float32))
    if not idx:
        return np.zeros(0, np.int32), np.zeros(0, np.int64), np.zeros((0, 5), np.float32)
    return np.concatenate(idx), np.concatenate(ts), np.vstack(vals)


def daily_ok(rows):
    """日足として使えるか（足の間隔の中央値が DAILY_MAX_SPACING 日以下）。range=max で月ごとの足が返ったときに弾く"""
    if len(rows) < 3:
        return True
    gaps = sorted((rows[i + 1][0] - rows[i][0]).days for i in range(len(rows) - 1))
    return gaps[len(gaps) // 2] <= DAILY_MAX_SPACING


def fetch_spec(fetch, code, iv, ranges):
    """→ (足, 使った範囲)。範囲を順に試し、日足は daily_ok を満たすものだけ使う"""
    for rg in ranges:
        x = fetch(code, iv, rg)
        if x and (iv != "1d" or daily_ok(x)):
            return x, rg
    return None, None


def fetch_shard(codes, fetch=Y.fetch_chart, pause=0.03):
    """→ {"codes", "d_*", "h_*", "m_*", "missing", "fallback"}（1台分）。fallback＝最初の範囲で取れず次の範囲を使った銘柄"""
    got = {iv: {} for iv, _ in SPECS}
    missing = {iv: [] for iv, _ in SPECS}
    fallback = {iv: [] for iv, _ in SPECS}
    for n, code in enumerate(codes):
        for iv, ranges in SPECS:
            rows, used = fetch_spec(fetch, code, iv, ranges)
            if rows:
                got[iv][code] = rows
                if used != ranges[0]:
                    fallback[iv].append(code)
            else:
                missing[iv].append(code)
        if (n + 1) % 100 == 0:
            print(f"  ...{n + 1}/{len(codes)}", flush=True)
        time.sleep(pause)
    out = {"codes": np.array(codes), "missing": json.dumps(missing), "fallback": json.dumps(fallback)}
    for iv, _ in SPECS:
        k = IV_KEY[iv]
        out[f"{k}_code"], out[f"{k}_t"], out[f"{k}_v"] = _pack(got[iv], codes)
    return out


# ════════════════════ まとめる ════════════════════

def merge(parts, meta):
    """1台分のファイル（dict）をまとめて1つに。銘柄番号は全体の並びに振り直す"""
    codes = sorted({str(c) for p in parts for c in p["codes"]})
    pos = {c: i for i, c in enumerate(codes)}
    out = {"codes": np.array(codes), "meta": json.dumps(meta, ensure_ascii=False)}
    missing = {iv: [] for iv, _ in SPECS}
    fallback = {iv: [] for iv, _ in SPECS}
    for p in parts:
        for iv, lst in json.loads(str(p["missing"])).items():
            missing[iv] += lst
        for iv, lst in json.loads(str(p["fallback"]) if "fallback" in p else "{}").items():
            fallback[iv] += lst
    out["missing"] = json.dumps(missing)
    out["fallback"] = json.dumps(fallback)
    for iv, _ in SPECS:
        k = IV_KEY[iv]
        ci, ts, vs = [], [], []
        for p in parts:
            local = np.array([pos[str(c)] for c in p["codes"]], np.int32)
            if len(p[f"{k}_code"]):
                ci.append(local[p[f"{k}_code"]])
                ts.append(p[f"{k}_t"])
                vs.append(p[f"{k}_v"])
        ci = np.concatenate(ci) if ci else np.zeros(0, np.int32)
        ts = np.concatenate(ts) if ts else np.zeros(0, np.int64)
        vs = np.vstack(vs) if vs else np.zeros((0, 5), np.float32)
        order = np.lexsort((ts, ci))
        out[f"{k}_code"], out[f"{k}_t"], out[f"{k}_v"] = ci[order], ts[order], vs[order]
    return out


# ════════════════════ 読む ════════════════════

class Bars:
    """置き場のファイル1つ。fetch(code, interval, rng) で yori_lab.fetch_chart と同じ形を返す"""

    def __init__(self, path=DEFAULT_PATH):
        z = np.load(path, allow_pickle=False)
        self.codes = [str(c) for c in z["codes"]]
        self.pos = {c: i for i, c in enumerate(self.codes)}
        self.meta = json.loads(str(z["meta"]))
        self.missing = json.loads(str(z["missing"]))
        self.fallback = json.loads(str(z["fallback"])) if "fallback" in z.files else {}
        self.arr = {}
        for iv, k in IV_KEY.items():
            ci = z[f"{k}_code"]
            starts = np.searchsorted(ci, np.arange(len(self.codes) + 1))
            self.arr[iv] = (starts, z[f"{k}_t"], z[f"{k}_v"])
        self.live = 0

    def rows(self, code, interval):
        if code not in self.pos or interval not in self.arr:
            return None
        starts, ts, vs = self.arr[interval]
        i = self.pos[code]
        a, b = starts[i], starts[i + 1]
        if a == b:
            return None
        return [(dt.datetime.fromtimestamp(int(t), P.JST), float(v[0]), float(v[1]), float(v[2]), float(v[3]), float(v[4]))
                for t, v in zip(ts[a:b], vs[a:b])]

    def cutoff(self, rng):
        """範囲（5y・729d・60d・1mo など）→ 置き場を作った日時から数えた始まりの時刻（読めなければ None＝全部）"""
        m = re.fullmatch(r"(\d+)(d|mo|y)", str(rng))
        built = self.meta.get("built_at")
        if not m or not built:
            return None
        try:
            start = dt.datetime.fromisoformat(built)
        except ValueError:
            return None
        return start - dt.timedelta(days=int(m.group(1)) * RANGE_DAYS[m.group(2)])

    def fetch(self, code, interval, rng, live=Y.fetch_chart):
        """置き場にあればそれを（頼まれた範囲に切って）、無ければ Yahoo から（取れなかった記録がある銘柄は置き場と同じく None）"""
        r = self.rows(code, interval)
        if r is not None:
            c = self.cutoff(rng)
            return [x for x in r if x[0] >= c] if c else r
        if code in self.pos and code in self.missing.get(interval, []):
            return None
        self.live += 1
        return live(code, interval, rng)


_BARS = None


def bars(path=None):
    """置き場があれば読む（1回だけ）。無ければ None"""
    global _BARS
    path = path or DEFAULT_PATH
    if _BARS is None and os.path.exists(path):
        _BARS = Bars(path)
        print(f"📦 値段の置き場を使う：{path}（作成 {_BARS.meta.get('built_at')}・{len(_BARS.codes)}銘柄・一覧 {_BARS.meta.get('list_date')}）", flush=True)
    return _BARS


def fetcher(path=None):
    """ラボの fetch に渡す関数。置き場が無ければ Yahoo から取る（これまでどおり）"""
    b = bars(path)
    return b.fetch if b else Y.fetch_chart


def load_universe(path=None):
    """置き場の一覧（作った日と同じ銘柄）。無ければ JPX から取る（build_jp_highs.load_universe）"""
    b = bars(path)
    if b and b.meta.get("stocks"):
        return b.meta["stocks"], b.meta.get("list_date")
    return H.load_universe()


def info(path=None):
    """ラボの出力に書く、置き場の情報（使っていなければ None）"""
    b = bars(path)
    if not b:
        return None
    return {"built_at": b.meta.get("built_at"), "list_date": b.meta.get("list_date"), "n_codes": len(b.codes),
            "missing": {k: len(v) for k, v in b.missing.items()}, "fallback": {k: len(v) for k, v in b.fallback.items()},
            "daily_range": (b.meta.get("specs") or {}).get("1d", ["10y"])[0], "live_fetches": b.live}


# ════════════════════ コマンド ════════════════════

def main(argv):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch")
    f.add_argument("--shard", type=int, required=True)
    f.add_argument("--of", type=int, required=True)
    f.add_argument("--out", required=True)
    m = sub.add_parser("merge")
    m.add_argument("--out", required=True)
    m.add_argument("parts", nargs="+")
    args = ap.parse_args(argv)
    if args.cmd == "fetch":
        stocks, _ = H.load_universe()
        codes = shard_codes(stocks, args.shard, args.of)
        print(f"台 {args.shard}/{args.of}：{len(codes)}銘柄")
        out = fetch_shard(codes)
        np.savez_compressed(args.out, **out)
        miss = json.loads(out["missing"])
        fb = json.loads(out["fallback"])
        print(f"保存 {args.out}：取れなかった 日足 {len(miss['1d'])}・1時間足 {len(miss['60m'])}・5分足 {len(miss['5m'])}"
              f"・日足を10年で取り直した {len(fb['1d'])}")
        return 0
    stocks, list_date = H.load_universe()
    paths = sorted(p for pat in args.parts for p in glob.glob(pat))
    parts = [dict(np.load(p, allow_pickle=False)) for p in paths]
    meta = {"built_at": dt.datetime.now(P.JST).isoformat(timespec="minutes"), "list_date": list_date,
            "stocks": stocks, "specs": {iv: list(r) for iv, r in SPECS}, "n_parts": len(parts)}
    out = merge(parts, meta)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    np.savez_compressed(args.out, **out)
    miss = json.loads(out["missing"])
    size = os.path.getsize(args.out) / 1e6
    print(f"まとめ {args.out}：{len(out['codes'])}銘柄・{size:.0f}MB・日足 {len(out['d_t']):,}本・1時間足 {len(out['h_t']):,}本・"
          f"5分足 {len(out['m_t']):,}本・取れなかった 日足 {len(miss['1d'])}・1時間足 {len(miss['60m'])}・5分足 {len(miss['5m'])}"
          f"・日足を10年で取り直した {len(json.loads(out['fallback'])['1d'])}"
          f"・日足の最初 {dt.datetime.fromtimestamp(int(out['d_t'].min()), P.JST).date() if len(out['d_t']) else '—'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
