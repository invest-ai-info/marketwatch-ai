# -*- coding: utf-8 -*-
"""candle_lab.py — C1 シグナルの直前の足の形（ピンバー・包み足）。2026-09-27 夜登録・オーナー「進めてください」。

事前登録＝PILLAR_PREREG.md「C1 シグナルの直前の足の形」（計算より先にコミット）。下の定数と判定はそこと同じ値で固定し、
結果を見てから動かさない。出力には事前登録の文書の指紋（sha256）を書き込む。

━━ 事前に決めたこと ━━
対象   : signals-log.json の決着したシグナル（signal_env_profile.load と同じ＝tp1/tp2 が効いた・sl が効かなかった）。
判定足 : B＝終わりの時刻（始まり＋時間足の長さ）が発火時刻以前の、いちばん新しい足。P＝その1本前。
         エンジンは作りかけの足でも合図を出す（fetch_data の最後の足）ので、発火した足そのものは使わない。
         1時間足・4時間足＝Yahoo の1時間足。4時間足はエンジンと同じく取引所の現地時刻のまま resample("4h")。
           エンジンは period="30d" で取るので、区切りの起点＝発火日の30日前の現地0時（resample の origin）に合わせる。
         日足＝Yahoo の日足。足の終わり＝その日付の現地0時＋24時間（まだ分からない足を使わない側）。
形     : 買いのピンバー＝下ヒゲ≧足の長さの60% かつ 実体≦30%。売りは上ヒゲで同じ。
         買いの包み足＝B陽線・P陰線・B始値≦P終値・B終値≧P始値。売りは陰陽を逆に。足の長さ0は形なし。
区分   : same＝同じ向きの形あり／opposite＝逆向きだけあり／none＝形なし。
物差し : signal_env_profile の超過勝率（xw）。補助に超過R（xr）。幅は銘柄×日の二方向・安全側（mean_se_safe）。
判定   : 主な問いは same だけ。件数100未満＝件数不足。95%の幅が0より上・平均5ポイント以上・前半後半ともプラス＝兆し。
         同じ条件で下向き＝逆。それ以外＝差なし。前半・後半＝数えたシグナルの日付の真ん中で分ける。

使い方:  python candle_lab.py        → candle-lab.json / candle-lab.md を書く（GitHub Actions の candle-lab.yml が実行）
"""
import collections
import datetime as dt
import json
import sys
import time

import pandas as pd

import signal_env_profile as E
from pillar_lab import prereg_sha256

PIN_WICK = 0.60
PIN_BODY = 0.30
MIN_N = 100
MIN_EFF = 0.05
ALPHA = 0.05
ENGINE_DAYS = 30          # generate_technical_alerts.fetch_data(days=30) と同じ
OUT_JSON = "candle-lab.json"
OUT_MD = "candle-lab.md"
BUCKETS = ("same", "opposite", "none")
LABEL = {"same": "同じ向きの形あり", "opposite": "逆向きの形あり", "none": "形なし"}


# ════════════════════ 形の決め方（純関数・テスト対象） ════════════════════

def pin_dirs(o, h, l, c):
    """ピンバーの向きの集合: {"long"}（下ヒゲ）/ {"short"}（上ヒゲ）/ 空。"""
    rng = h - l
    if not rng or rng <= 0:
        return set()
    body = abs(c - o)
    out = set()
    if body <= PIN_BODY * rng:
        if (min(o, c) - l) >= PIN_WICK * rng:
            out.add("long")
        if (h - max(o, c)) >= PIN_WICK * rng:
            out.add("short")
    return out


def engulf_dirs(p, b):
    """包み足の向きの集合。p, b は (始値, 高値, 安値, 終値)。"""
    po, _, _, pc = p
    bo, bh, bl, bc = b
    if bh - bl <= 0:
        return set()
    out = set()
    if bc > bo and pc < po and bo <= pc and bc >= po:
        out.add("long")
    if bc < bo and pc > po and bo >= pc and bc <= po:
        out.add("short")
    return out


def classify(p, b, side):
    """区分と内訳。side は "long" / "short"。"""
    pins, engs = pin_dirs(*b), engulf_dirs(p, b)
    other = "short" if side == "long" else "long"
    same_pin, same_eng = side in pins, side in engs
    if same_pin or same_eng:
        bucket = "same"
    elif other in pins or other in engs:
        bucket = "opposite"
    else:
        bucket = "none"
    return {"bucket": bucket, "pin": same_pin, "engulf": same_eng}


def last_closed(bars, fired, length):
    """終わり（始まり＋length）が fired 以前の最後の足とその1本前 → (P, B) の (始,高,安,終) か None。"""
    if bars is None or len(bars) < 2:
        return None
    ends = bars.index + length
    ok = bars[ends <= fired]
    if len(ok) < 2:
        return None
    row = lambda r: (float(r["Open"]), float(r["High"]), float(r["Low"]), float(r["Close"]))  # noqa: E731
    return row(ok.iloc[-2]), row(ok.iloc[-1])


def resample_4h(h1, origin):
    """エンジンと同じ 4時間足（取引所の現地時刻のまま・起点 origin）。"""
    agg = {"Open": "first", "High": "max", "Low": "min", "Close": "last"}
    return h1.resample("4h", origin=origin).agg(agg).dropna(subset=["Close"])


def engine_origin(fired, tz):
    """エンジンの period="30d" の取り始め＝発火日の30日前の現地0時（resample の起点）。"""
    d = (fired.tz_convert(tz) - pd.Timedelta(days=ENGINE_DAYS)).date()
    return pd.Timestamp(d).tz_localize(tz, ambiguous=False, nonexistent="shift_forward")


def verdict(n, m, lo, hi, h1, h2):
    if n < MIN_N:
        return "件数不足"
    if lo > 0 and m >= MIN_EFF and h1 is not None and h2 is not None and h1 > 0 and h2 > 0:
        return "兆し（形があると勝ちやすい）"
    if hi < 0 and m <= -MIN_EFF and h1 is not None and h2 is not None and h1 < 0 and h2 < 0:
        return "逆（形があると負けやすい）"
    return "差なし"


# ════════════════════ 値段の取得 ════════════════════

def fetch(ticker, interval, tries=3):
    """Yahoo の足を取引所の現地時刻のまま返す（1時間足＝過去730日・日足＝2026-03-01から）。"""
    import yfinance as yf
    for k in range(tries):
        try:
            if interval == "1h":
                df = yf.download(ticker, period="730d", interval="1h", progress=False, auto_adjust=True)
            else:
                df = yf.download(ticker, start="2026-03-01", interval="1d", progress=False, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df = df.dropna(subset=["Open", "High", "Low", "Close"])
            if len(df) > 20:
                return df.sort_index()
        except Exception as e:  # noqa: BLE001
            print(f"  ⚠️ {ticker} {interval} 取得失敗 {k + 1}/{tries}: {type(e).__name__}: {str(e)[:80]}", file=sys.stderr)
        time.sleep(2 * (k + 1))
    return None


class Prices:
    def __init__(self, fetcher=fetch):
        self.fetcher = fetcher
        self.h1, self.d1, self.r4 = {}, {}, {}

    def _h1(self, t):
        if t not in self.h1:
            df = self.fetcher(t, "1h")
            if df is not None and df.index.tz is None:
                df.index = df.index.tz_localize("UTC")
            self.h1[t] = df
        return self.h1[t]

    def _d1(self, t):
        if t not in self.d1:
            df = self.fetcher(t, "1d")
            if df is not None and df.index.tz is None:
                h1 = self._h1(t)
                tz = h1.index.tz if h1 is not None else "UTC"
                df.index = pd.DatetimeIndex([pd.Timestamp(x.date()) for x in df.index]).tz_localize(
                    tz, ambiguous=False, nonexistent="shift_forward")
            self.d1[t] = df
        return self.d1[t]

    def pair(self, ticker, tf, fired):
        """(P, B) か、取れない理由の文字列。"""
        if tf == "1h":
            h1 = self._h1(ticker)
            if h1 is None:
                return "値段が取れない"
            got = last_closed(h1, fired, pd.Timedelta(hours=1))
        elif tf == "4h":
            h1 = self._h1(ticker)
            if h1 is None:
                return "値段が取れない"
            origin = engine_origin(fired, h1.index.tz)
            key = (ticker, origin)
            if key not in self.r4:
                self.r4[key] = resample_4h(h1, origin)
            got = last_closed(self.r4[key], fired, pd.Timedelta(hours=4))
        elif tf == "1d":
            d1 = self._d1(ticker)
            if d1 is None:
                return "値段が取れない"
            got = last_closed(d1, fired, pd.Timedelta(days=1))
        else:
            return "時間足が不明"
        return got if got is not None else "足が足りない"


# ════════════════════ 数える ════════════════════

def stats(xs, mid):
    n = len(xs)
    if n < 2:
        return {"n": n}
    m, se, df = E.mean_se_safe([x["xw"] for x in xs], [(x["ticker"], x["date"]) for x in xs])
    mr, ser, _ = E.mean_se_safe([x["xr"] for x in xs], [(x["ticker"], x["date"]) for x in xs])
    t95 = E.t_crit(ALPHA, df)
    h1 = [x["xw"] for x in xs if x["date"] < mid]
    h2 = [x["xw"] for x in xs if x["date"] >= mid]
    a1 = sum(h1) / len(h1) if h1 else None
    a2 = sum(h2) / len(h2) if h2 else None
    lo, hi = m - t95 * se, m + t95 * se
    return {"n": n, "win": sum(x["win"] for x in xs) / n, "excess": m, "lo": lo, "hi": hi,
            "half1": a1, "half2": a2, "n1": len(h1), "n2": len(h2),
            "excess_r": mr, "r_lo": mr - t95 * ser, "r_hi": mr + t95 * ser,
            "verdict": verdict(n, m, lo, hi, a1, a2)}


def run(rows, prices):
    skipped = collections.Counter()
    used = []
    for x in rows:
        d = x["d"]
        side = x["stratum"][2]
        if side not in ("long", "short"):
            skipped["向きが無い"] += 1
            continue
        try:
            fired = pd.Timestamp(d.get("fired_at"))
            if fired.tz is None:
                fired = fired.tz_localize("Asia/Tokyo")
        except (TypeError, ValueError):
            skipped["発火時刻が読めない"] += 1
            continue
        got = prices.pair(x["ticker"], d.get("timeframe"), fired)
        if isinstance(got, str):
            skipped[got] += 1
            continue
        c = classify(got[0], got[1], side)
        used.append({**x, **c, "tf": d.get("timeframe"), "asset": x["stratum"][3]})
    dates = sorted({x["date"] for x in used})
    mid = dates[len(dates) // 2] if dates else ""
    main = {b: stats([x for x in used if x["bucket"] == b], mid) for b in BUCKETS}
    read = {
        "ピンバーだけ（同じ向き）": stats([x for x in used if x["pin"] and not x["engulf"]], mid),
        "包み足だけ（同じ向き）": stats([x for x in used if x["engulf"] and not x["pin"]], mid),
        "ピンバーと包み足の両方（同じ向き）": stats([x for x in used if x["pin"] and x["engulf"]], mid),
    }
    by = {}
    for key, fn in (("時間足", lambda x: x["tf"]), ("資産クラス", lambda x: x["asset"]),
                    ("順張り・逆張り", lambda x: {"tf": "順張り", "mr": "逆張り"}.get(x["fam"], "その他"))):
        by[key] = {}
        for v in sorted({fn(x) for x in used}, key=str):
            sub = [x for x in used if fn(x) == v]
            by[key][str(v)] = {b: stats([x for x in sub if x["bucket"] == b], mid) for b in BUCKETS}
    share = collections.Counter(x["bucket"] for x in used)
    return {"n_rows": len(rows), "n_used": len(used), "skipped": dict(skipped), "split_date": mid,
            "first": dates[0] if dates else "", "last": dates[-1] if dates else "",
            "share": {b: share[b] for b in BUCKETS}, "main": main, "read": read, "by": by}


# ════════════════════ 書き出し ════════════════════

def pct(v, sign=True):
    return "—" if v is None else (f"{v * 100:+.1f}" if sign else f"{v * 100:.1f}")


def row_md(name, s):
    if s.get("n", 0) < 2 or "excess" not in s:
        return f"| {name} | {s.get('n', 0)} | — | — | — | — | — |"
    return (f"| {name} | {s['n']} | {pct(s['win'], False)}% | {pct(s['excess'])}（{pct(s['lo'])}〜{pct(s['hi'])}） | "
            f"{pct(s['half1'])}／{pct(s['half2'])} | {s['excess_r']:+.3f}R | {s['verdict']} |")


HEAD = "| 区分 | 件数 | 勝率 | 超過勝率（95%の幅・ポイント） | 前半／後半 | 超過R | 判定 |\n|---|---:|---:|---|---|---:|---|"


def render(res):
    m = res["main"]["same"]
    L = ["# C1 シグナルの直前の足の形（ピンバー・包み足）", "",
         f"作成: {res['generated_at']}（GitHub Actions で計算）。事前登録＝`PILLAR_PREREG.md`「C1 シグナルの直前の足の形」"
         f"（指紋 sha256 `{(res.get('prereg_sha256') or '')[:16]}…`）。**売買の決まりではない**。", "",
         f"- 対象：決着したシグナル {res['n_rows']:,}件のうち、直前の足を作れた {res['n_used']:,}件（{res['first']}〜{res['last']}）。"
         f"前半・後半の境目 {res['split_date']}",
         "- 数えなかったもの：" + ("、".join(f"{k} {v}件" for k, v in res["skipped"].items()) or "なし"),
         "- 割合：" + "／".join(f"{LABEL[b]} {res['share'][b]:,}件" for b in BUCKETS), "",
         f"## 判定（主な問い＝同じ向きの形あり）：**{m.get('verdict', '件数不足')}**", "",
         "基準＝超過勝率の95%の幅がまるごと0より上・平均5ポイント以上・前半後半ともプラス（逆向きも同じ条件）。件数100未満は件数不足。", "",
         HEAD] + [row_md(LABEL[b], res["main"][b]) for b in BUCKETS] + ["",
         "## 読むための表（判定しない）", "", "### 形の内訳", "", HEAD] + [row_md(k, v) for k, v in res["read"].items()]
    for key, groups in res["by"].items():
        L += ["", f"### {key}別", "", HEAD]
        for v, bs in groups.items():
            L += [row_md(f"{v}・{LABEL[b]}", bs[b]) for b in BUCKETS]
    L += ["", "---", "", "※ 研究の記録です。投資助言ではありません。将来の成績を約束するものではありません。"]
    return "\n".join(L)


def main():
    rows = E.load("signals-log.json")
    res = run(rows, Prices())
    res["generated_at"] = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).strftime("%Y-%m-%dT%H:%M+09:00")
    res["prereg_file"] = "PILLAR_PREREG.md"
    res["prereg_sha256"] = prereg_sha256()
    res["constants"] = {"PIN_WICK": PIN_WICK, "PIN_BODY": PIN_BODY, "MIN_N": MIN_N, "MIN_EFF": MIN_EFF,
                        "ALPHA": ALPHA, "ENGINE_DAYS": ENGINE_DAYS}
    json.dump(res, open(OUT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    open(OUT_MD, "w", encoding="utf-8").write(render(res))
    print(f"C1: {res['n_used']}/{res['n_rows']} 件・判定 {res['main']['same'].get('verdict')}")


if __name__ == "__main__":
    main()
