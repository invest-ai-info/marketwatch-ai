# -*- coding: utf-8 -*-
"""
method_lab.py — 毎日の新しい方法（2026-11-17 オーナー決定）

オーナーの言葉:「新しい方法を毎日探して新しい方法だけをシグナル研究で発表してください。かといって増え続けるのも問題なので、
研究中の方法の中で最も成績の悪いものから削除していきましょう。1日1回新しい方法を見つけ出して研究として発表して
成績の悪いものは一つ消すという形に」「しっかりと研究して改善を繰り返し進化していきましょう」。
事前登録＝PILLAR_PREREG.md「毎日の新しい方法と入れ替え（2026-11-17）」。この冒頭とその節の決まりは、結果を見る前にコミットした。

■ 何をするか（GitHub Actions の method-lab.yml が毎晩・routine の push のあとに動かす。LLM は使わない）
  1) サイトの監視18銘柄の日足（Yahoo・2000年ごろ〜）を取る。
  2) その日の候補を K=48 通り作る（決まった種＝日付から作るので、何度動かしても同じ候補になる）。
       ・用意した考え方の一覧（method_ideas.json＝よく知られた方法・理由つき）から 2つ
       ・研究中の方法と、過去で惜しかった方法の「1か所だけ変えた形」（進化）から 10
       ・部品の組み合わせ（でたらめに選ぶ）から 36（足りないぶんもここで埋める）
     すでに試した形（同じ ID）は二度と試さない。
  3) それぞれを過去で数える（損益は R＝損切りまでの幅〔ATR×1.5〕を1とした単位・費用を引いたあと）。
       探す期間  ＝ 〜2017-12-31（シグナルの日）
       確かめる期間＝ 2018-01-01 〜 発表の日の前の日
       偽薬＝同じ銘柄・同じ期間・同じ向き・同じ手じまいで、入る日だけでたらめにした 2,000 回
  4) 合格（すべて満たす）:
       ① 探す期間: 回数 100 以上・平均 R がプラス・偽薬より良い割合 p < 0.05（片側）
       ② 確かめる期間: 回数 50 以上・平均 R がプラス・偽薬との差がプラス
       ③ 確かめる期間の回数が 1年あたり 40 以上（前向きの最初の判定＝80回 に2年以内で届く）
     合格の中で、探す期間の「偽薬からの離れ具合（z）」がいちばん大きい1つをその日の「新しい方法」にする。
     合格が無ければ、探す期間の z がいちばん大きいものを「惜しかった方法」として出す（前向きには進めない）。
  5) 研究中の方法（method-lab-registry.json）の前向きの成績を数える＝登録した日より後に出たシグナルだけ。

■ 登録・判定・入れ替えは routine が research_cull.py で行う（この表は読むだけ）。

■ 入る・出るの決まり（どの方法も同じ・過去も前向きも同じ）
  ・シグナルはその日の終値で決まる → 次の日の始値で入る（先読みしない）
  ・損切り＝入った値 ∓ ATR(14)×1.5（ATR はシグナルの日の値）。これを 1R とする
  ・手じまいの形 6つ: atr_tp＝利確 ATR×2（サイトのシグナルと同じ）・最長20日／atr_tp3＝利確 ATR×3・最長30日／
                     hold_1・hold_3・hold_5・hold_10＝その日数の終値（損切りつき）
  ・同じ日に損切りと利確の両方に届いたら損切りが先（悪いほうに数える）。始値が損切りを越えて始まったら始値で手じまう
  ・同じ方法・同じ銘柄で持っている間は次のシグナルで入らない
  ・費用＝signal_lab_sweep.SPREAD_PCT（為替は円のペア 0.8銭・ほか 1.2pips）×1.5 を R に直して毎回引く

使い方:
  python method_lab.py daily [--for-date YYYY-MM-DD] [--k 24]   # 候補を作って数え、研究中の前向きも数え直す（Actions）
  python method_lab.py forward                                  # 前向きだけ数え直す
  python method_lab.py test '<spec json>' [--for-date D]          # 1つの形を数えるだけ（記録しない・調べもの用）
出力: method-lab.json（機械用）・method-lab.md（人が読む）＝ GitHub 側で作る（SYNC禁忌・手元から push しない）
"""
import argparse
import datetime as dt
import hashlib
import json
import math
import os
import random
import sys

import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT_JSON = os.path.join(ROOT, "method-lab.json")
OUT_MD = os.path.join(ROOT, "method-lab.md")
REGISTRY = os.path.join(ROOT, "method-lab-registry.json")
IDEAS = os.path.join(ROOT, "method_ideas.json")
BARS_DIR = os.path.join(ROOT, "method-bars")          # 作業用の置き場（.gitignore）
JST = dt.timezone(dt.timedelta(hours=9))

# ── 事前登録の物差し（PILLAR_PREREG.md と同じ数字・変えるときは新しい節を足す） ──
EXPLORE_END = "2017-12-31"
CONFIRM_START = "2018-01-01"
MIN_N_EXPLORE = 100
MIN_N_CONFIRM = 50
P_MAX = 0.05
MIN_PER_YEAR = 40
PLACEBO_DRAWS = 2000
K_DEFAULT = 48
K_IDEAS, K_MUT = 2, 10
SL_MULT = 1.5
WARMUP = 252
KEEP_BATCHES = 10

INSTRUMENTS = [
    ("GC=F", "金", "commodity"), ("SI=F", "銀", "commodity"), ("CL=F", "原油", "commodity"),
    ("NKD=F", "日経225先物", "index"), ("ES=F", "S&P500先物", "index"), ("NQ=F", "ナスダック100先物", "index"),
    ("YM=F", "ダウ先物", "index"), ("^FTSE", "FTSE100", "index"), ("BTC-USD", "ビットコイン", "btc"),
    ("USDJPY=X", "ドル円", "jpy_fx"), ("EURJPY=X", "ユーロ円", "jpy_fx"), ("GBPJPY=X", "ポンド円", "jpy_fx"),
    ("AUDJPY=X", "豪ドル円", "jpy_fx"), ("EURUSD=X", "ユーロドル", "nonjpy_fx"), ("GBPUSD=X", "ポンドドル", "nonjpy_fx"),
    ("AUDUSD=X", "豪ドル米ドル", "nonjpy_fx"), ("EURAUD=X", "ユーロ豪ドル", "nonjpy_fx"), ("GBPAUD=X", "ポンド豪ドル", "nonjpy_fx"),
]
SYMS = [s for s, _n, _g in INSTRUMENTS]
NAME_JA = {s: n for s, n, _g in INSTRUMENTS}
_KIND = {s: g for s, _n, g in INSTRUMENTS}
UNIVERSES = {
    "all": SYMS,
    "index": [s for s in SYMS if _KIND[s] == "index"],
    "commodity": [s for s in SYMS if _KIND[s] == "commodity"],
    "fx": [s for s in SYMS if _KIND[s] in ("jpy_fx", "nonjpy_fx")],
    "jpy_fx": [s for s in SYMS if _KIND[s] == "jpy_fx"],
    "nonjpy_fx": [s for s in SYMS if _KIND[s] == "nonjpy_fx"],
    "risk": [s for s in SYMS if _KIND[s] in ("index", "btc")],
}
UNIVERSE_JA = {
    "all": "監視している18銘柄", "index": "株価指数の5つ", "commodity": "金・銀・原油",
    "fx": "為替の9ペア", "jpy_fx": "円のペアの4つ", "nonjpy_fx": "円以外の為替の5ペア", "risk": "株価指数とビットコイン",
}
EXITS = {  # name: (利確の ATR 倍率 or None, 最長の日数)
    "atr_tp": (2.0, 20), "atr_tp3": (3.0, 30),
    "hold_1": (None, 1), "hold_3": (None, 3), "hold_5": (None, 5), "hold_10": (None, 10),
}
EXIT_JA = {
    "atr_tp": "損切りATR×1.5・利確ATR×2（サイトのシグナルと同じ・最長20日）",
    "atr_tp3": "損切りATR×1.5・利確ATR×3（最長30日）",
    "hold_1": "次の日の終値で手じまい（損切りATR×1.5つき）",
    "hold_3": "3日目の終値で手じまい（損切りATR×1.5つき）",
    "hold_5": "5日目の終値で手じまい（損切りATR×1.5つき）",
    "hold_10": "10日目の終値で手じまい（損切りATR×1.5つき）",
}
DOW_JA = ["月", "火", "水", "木", "金"]


def _spread(sym, price):
    """往復の費用（値段の単位）。signal_lab_sweep の表と同じ考え（為替は pips・ほかは値段の割合）。"""
    try:
        from signal_lab_sweep import SPREAD_PCT
    except Exception:  # pragma: no cover
        SPREAD_PCT = {}
    if sym in SPREAD_PCT:
        return price * SPREAD_PCT[sym]
    if sym.endswith("=X"):
        return np.full_like(price, 0.008 if "JPY" in sym else 0.00012)
    return np.zeros_like(price)


# ─────────────────────────────── 値段 ───────────────────────────────
class Bars:
    """1銘柄の日足と、その上で計算する指標（必要になったときだけ計算して覚えておく）。"""

    def __init__(self, sym, dates, o, h, l, c):
        self.sym = sym
        self.dates = list(dates)                     # 'YYYY-MM-DD'
        self.o, self.h, self.l, self.c = (np.asarray(x, dtype=float) for x in (o, h, l, c))
        self.n = len(self.c)
        self._cache = {}
        self._out = {}

    # 指標
    def get(self, key, fn):
        if key not in self._cache:
            with np.errstate(invalid="ignore", divide="ignore"):
                self._cache[key] = fn()
        return self._cache[key]

    def prev_c(self):
        return self.get("pc", lambda: np.concatenate([[np.nan], self.c[:-1]]))

    def tr(self):
        def f():
            pc = self.prev_c()
            return np.nanmax(np.vstack([self.h - self.l, np.abs(self.h - pc), np.abs(self.l - pc)]), axis=0)
        return self.get("tr", f)

    def atr(self, n=14):
        def f():
            tr = self.tr()
            out = np.full(self.n, np.nan)
            if self.n > n:
                out[n] = np.nanmean(tr[1:n + 1])
                a = 1.0 / n
                for i in range(n + 1, self.n):
                    out[i] = out[i - 1] + a * (tr[i] - out[i - 1])
            return out
        return self.get(("atr", n), f)

    def sma(self, x, n):
        if len(x) < n:
            return np.full(len(x), np.nan)
        cs = np.cumsum(np.insert(np.nan_to_num(x), 0, 0.0))
        out = np.full(len(x), np.nan)
        out[n - 1:] = (cs[n:] - cs[:-n]) / n
        return out

    def ma(self, n):
        return self.get(("ma", n), lambda: self.sma(self.c, n))

    def avg_range(self, n):
        return self.get(("ar", n), lambda: self.sma(self.tr(), n))

    def sd(self, n):
        def f():
            m = self.ma(n)
            m2 = self.sma(self.c ** 2, n)
            return np.sqrt(np.maximum(m2 - m ** 2, 0))
        return self.get(("sd", n), f)

    def rsi(self, n):
        def f():
            d = np.diff(self.c, prepend=np.nan)
            up, dn = np.where(d > 0, d, 0.0), np.where(d < 0, -d, 0.0)
            out = np.full(self.n, np.nan)
            if self.n <= n:
                return out
            au, ad = np.mean(up[1:n + 1]), np.mean(dn[1:n + 1])
            for i in range(n, self.n):
                if i > n:
                    au = (au * (n - 1) + up[i]) / n
                    ad = (ad * (n - 1) + dn[i]) / n
                out[i] = 100.0 if ad == 0 else 100 - 100 / (1 + au / ad)
            return out
        return self.get(("rsi", n), f)

    def streak(self, up):
        def f():
            out = np.zeros(self.n)
            pc = self.prev_c()
            for i in range(1, self.n):
                moved = self.c[i] > pc[i] if up else self.c[i] < pc[i]
                out[i] = out[i - 1] + 1 if moved else 0
            return out
        return self.get(("streak", up), f)

    def roll(self, x, n, how):
        out = np.full(len(x), np.nan)
        if len(x) >= n:
            from numpy.lib.stride_tricks import sliding_window_view
            w = sliding_window_view(x, n)
            out[n - 1:] = w.max(axis=1) if how == "max" else w.min(axis=1)
        return out

    def ibs(self):
        return self.get("ibs", lambda: np.where(self.h > self.l, (self.c - self.l) / (self.h - self.l), np.nan))

    def roc(self, n):
        def f():
            out = np.full(self.n, np.nan)
            out[n:] = self.c[n:] / self.c[:-n] - 1
            return out
        return self.get(("roc", n), f)

    def month_pos(self):
        """その月の何営業日目か（1から）。"""
        def f():
            out = np.zeros(self.n)
            for i, d in enumerate(self.dates):
                out[i] = 1 if i == 0 or d[:7] != self.dates[i - 1][:7] else out[i - 1] + 1
            return out
        return self.get("mpos", f)

    def weekday(self):
        return self.get("wd", lambda: np.array([dt.date.fromisoformat(d).weekday() for d in self.dates], dtype=float))

    def day(self):
        return self.get("day", lambda: np.array([int(d[8:10]) for d in self.dates], dtype=float))

    # 結果の表（入った場合の R を、すべての日について先に計算しておく）
    def outcome(self, dirn, exit_name):
        key = (dirn, exit_name)
        if key not in self._out:
            self._out[key] = _outcome(self, dirn, exit_name)
        return self._out[key]


def _outcome(b, dirn, exit_name):
    """各日 t にシグナルが出たとして、t+1 の始値で入ったときの (R, 持った日数)。データの終わりで決まらないものは NaN。"""
    tpm, maxb = EXITS[exit_name]
    n = b.n
    R = np.full(n, np.nan)
    held = np.zeros(n, dtype=int)
    if n < 3:
        return R, held
    t = np.arange(n - 1)
    entry = b.o[t + 1]
    atr = b.atr(14)[t]
    risk = SL_MULT * atr
    ok = np.isfinite(entry) & np.isfinite(risk) & (risk > 0) & (entry > 0)
    sl = entry - dirn * risk
    tp = entry + dirn * tpm * atr if tpm else None
    exitp = np.full(len(t), np.nan)
    done = ~ok
    for k in range(1, maxb + 1):
        idx = t + k
        valid = (~done) & (idx < n)
        if not valid.any():
            break
        ii = np.clip(idx, 0, n - 1)
        O, H, L, C = b.o[ii], b.h[ii], b.l[ii], b.c[ii]
        if k >= 2:  # 始値が損切り（または利確）を越えて始まった
            gap_sl = valid & ((O <= sl) if dirn > 0 else (O >= sl))
            exitp[gap_sl] = O[gap_sl]
            held[t[gap_sl]] = k
            done |= gap_sl
            valid &= ~gap_sl
            if tp is not None:
                gap_tp = valid & ((O >= tp) if dirn > 0 else (O <= tp))
                exitp[gap_tp] = O[gap_tp]
                held[t[gap_tp]] = k
                done |= gap_tp
                valid &= ~gap_tp
        hit_sl = valid & ((L <= sl) if dirn > 0 else (H >= sl))
        exitp[hit_sl] = sl[hit_sl]
        held[t[hit_sl]] = k
        done |= hit_sl
        valid &= ~hit_sl
        if tp is not None:
            hit_tp = valid & ((H >= tp) if dirn > 0 else (L <= tp))
            exitp[hit_tp] = tp[hit_tp]
            held[t[hit_tp]] = k
            done |= hit_tp
            valid &= ~hit_tp
        if k == maxb:
            exitp[valid] = C[valid]
            held[t[valid]] = k
            done |= valid
    cost = _spread(b.sym, entry) * 1.5
    with np.errstate(invalid="ignore", divide="ignore"):
        r = dirn * (exitp - entry) / risk - cost / risk
    R[:-1] = np.where(np.isfinite(exitp) & ok, r, np.nan)
    return R, held


def clean_rows(rows):
    """(date, o, h, l, c) の並びを整える：欠け・0以下・日付の重複を落とし、高値・安値を始値・終値の外側にそろえる。"""
    out, seen = [], set()
    for d, o, h, l, c in rows:
        if d in seen or not all(isinstance(x, (int, float)) and math.isfinite(x) and x > 0 for x in (o, h, l, c)):
            continue
        seen.add(d)
        out.append((d, o, max(h, o, c), min(l, o, c), c))
    out.sort()
    return out


def load_bars(sym, refresh=False, today=None):
    """Yahoo の日足（1995年〜）。今日（UTC）の足は途中なので使わない。作業用に method-bars/ に置く。"""
    os.makedirs(BARS_DIR, exist_ok=True)
    path = os.path.join(BARS_DIR, sym.replace("^", "_").replace("=", "_") + ".json")
    today = today or dt.datetime.now(dt.timezone.utc).date().isoformat()
    rows = None
    if not refresh and os.path.exists(path):
        cached = json.load(open(path, encoding="utf-8"))
        if cached.get("fetched") == today:
            rows = cached["rows"]
    if rows is None:
        import yfinance as yf
        last = None
        for _ in range(3):
            try:
                df = yf.download(sym, start="1995-01-01", interval="1d", progress=False, auto_adjust=False)
                if df is not None and len(df):
                    break
            except Exception as e:  # pragma: no cover
                last = e
        else:
            raise RuntimeError(f"{sym}: Yahoo から取れない（{last}）")
        if hasattr(df.columns, "levels"):
            df.columns = [c[0] for c in df.columns]
        rows = [(str(ix)[:10], float(r["Open"]), float(r["High"]), float(r["Low"]), float(r["Close"]))
                for ix, r in df.iterrows()]
        rows = [r for r in rows if r[0] < today]
        json.dump({"fetched": today, "rows": rows}, open(path, "w", encoding="utf-8"))
    rows = clean_rows([tuple(r) for r in rows])
    d, o, h, l, c = zip(*rows) if rows else ([], [], [], [], [])
    return Bars(sym, d, o, h, l, c)


# ─────────────────────────────── 部品（条件） ───────────────────────────────
# 名前: (引数の候補のリスト, 合う向き, 計算, 言葉)
def _f(x):
    return np.nan_to_num(x, nan=np.nan)


COND = {
    "rsi_lt": ([[2, 3, 5, 14], [5, 10, 15, 20, 25, 30]], ["long"],
               lambda b, n, x: b.rsi(n) < x, lambda n, x: f"RSI（{n}日）が{x}より下"),
    "rsi_gt": ([[2, 3, 5, 14], [70, 75, 80, 85, 90, 95]], ["short", "long"],
               lambda b, n, x: b.rsi(n) > x, lambda n, x: f"RSI（{n}日）が{x}より上"),
    "bb_lt": ([[1.5, 2, 2.5]], ["long"],
              lambda b, k: b.c < b.ma(20) - k * b.sd(20), lambda k: f"終値がボリンジャーバンド（20日）の−{k}σより下"),
    "bb_gt": ([[1.5, 2, 2.5]], ["short", "long"],
              lambda b, k: b.c > b.ma(20) + k * b.sd(20), lambda k: f"終値がボリンジャーバンド（20日）の＋{k}σより上"),
    "down_streak": ([[2, 3, 4, 5]], ["long", "short"],
                    lambda b, k: b.streak(False) >= k, lambda k: f"{k}日続けて終値が下がった"),
    "up_streak": ([[2, 3, 4, 5]], ["short", "long"],
                  lambda b, k: b.streak(True) >= k, lambda k: f"{k}日続けて終値が上がった"),
    "new_low": ([[5, 10, 20, 55]], ["long", "short"],
                lambda b, n: b.c <= b.roll(b.c, n, "min"), lambda n: f"終値が{n}日でいちばん安い"),
    "new_high": ([[5, 10, 20, 55]], ["long", "short"],
                 lambda b, n: b.c >= b.roll(b.c, n, "max"), lambda n: f"終値が{n}日でいちばん高い"),
    "ibs_lt": ([[0.1, 0.15, 0.2, 0.25]], ["long"],
               lambda b, x: b.ibs() < x, lambda x: f"終値がその日の値幅の下から{round(x * 100)}%以内"),
    "ibs_gt": ([[0.75, 0.8, 0.85, 0.9]], ["short", "long"],
               lambda b, x: b.ibs() > x, lambda x: f"終値がその日の値幅の上から{round((1 - x) * 100)}%以内"),
    "ma_cross_up": ([[[5, 20], [10, 50], [20, 100], [50, 200]]], ["long"],
                    lambda b, p: _cross(b.ma(p[0]), b.ma(p[1]), True),
                    lambda p: f"{p[0]}日移動平均が{p[1]}日移動平均を上に抜けた"),
    "ma_cross_dn": ([[[5, 20], [10, 50], [20, 100], [50, 200]]], ["short", "long"],
                    lambda b, p: _cross(b.ma(p[0]), b.ma(p[1]), False),
                    lambda p: f"{p[0]}日移動平均が{p[1]}日移動平均を下に抜けた"),
    "dist_ma_lt": ([[20, 50, 200], [1, 1.5, 2, 3]], ["long"],
                   lambda b, n, x: b.c < b.ma(n) - x * b.atr(14), lambda n, x: f"終値が{n}日移動平均よりATRの{x}倍以上下"),
    "dist_ma_gt": ([[20, 50, 200], [1, 1.5, 2, 3]], ["short", "long"],
                   lambda b, n, x: b.c > b.ma(n) + x * b.atr(14), lambda n, x: f"終値が{n}日移動平均よりATRの{x}倍以上上"),
    "gap_dn": ([[0.3, 0.5, 1.0]], ["long", "short"],
               lambda b, x: b.o < b.prev_c() - x * _prev(b.atr(14)),
               lambda x: f"始値が前の日の終値よりATRの{x}倍以上下で始まった"),
    "gap_up": ([[0.3, 0.5, 1.0]], ["short", "long"],
               lambda b, x: b.o > b.prev_c() + x * _prev(b.atr(14)),
               lambda x: f"始値が前の日の終値よりATRの{x}倍以上上で始まった"),
    "big_dn": ([[1, 1.5, 2]], ["long", "short"],
               lambda b, x: (b.o - b.c) >= x * b.atr(14), lambda x: f"その日の陰線の長さがATRの{x}倍以上"),
    "big_up": ([[1, 1.5, 2]], ["short", "long"],
               lambda b, x: (b.c - b.o) >= x * b.atr(14), lambda x: f"その日の陽線の長さがATRの{x}倍以上"),
    "nr": ([[4, 7]], ["long", "short"],
           lambda b, n: (b.h - b.l) <= b.roll(b.h - b.l, n, "min"), lambda n: f"その日の値幅が{n}日でいちばん狭い"),
    "inside": ([], ["long", "short"],
               lambda b: (b.h < _prev(b.h)) & (b.l > _prev(b.l)), lambda: "高値と安値が前の日の中におさまった（はらみ足）"),
    "roc_gt": ([[20, 60, 120, 250]], ["long"],
               lambda b, n: b.roc(n) > 0, lambda n: f"終値が{n}日前より高い"),
    "roc_lt": ([[20, 60, 120, 250]], ["short", "long"],
               lambda b, n: b.roc(n) < 0, lambda n: f"終値が{n}日前より安い"),
    "month_start": ([[1, 2, 3]], ["long"],
                    lambda b, k: b.month_pos() <= k, lambda k: f"月の最初の{k}営業日"),
    "late_month": ([], ["long"], lambda b: b.day() >= 25, lambda: "月の25日以降"),
    "dow": ([[0, 1, 2, 3, 4]], ["long", "short"],
            lambda b, d: b.weekday() == d, lambda d: f"{DOW_JA[d]}曜日"),
    "brk_prev_high": ([], ["long", "short"], lambda b: b.c > _prev(b.h), lambda: "終値が前の日の高値より上"),
    "brk_prev_low": ([], ["long", "short"], lambda b: b.c < _prev(b.l), lambda: "終値が前の日の安値より下"),
    "squeeze": ([[0.6, 0.7, 0.8]], ["long", "short"],
                lambda b, x: b.avg_range(5) < x * b.avg_range(50),
                lambda x: f"最近5日の値幅の平均が50日の平均の{x}倍より小さい"),
    # 絞り込みに使う部品
    "above_ma": ([[50, 100, 200]], ["long", "short"], lambda b, n: b.c > b.ma(n), lambda n: f"終値が{n}日移動平均より上"),
    "below_ma": ([[50, 100, 200]], ["long", "short"], lambda b, n: b.c < b.ma(n), lambda n: f"終値が{n}日移動平均より下"),
    "vol_high": ([[1.3, 1.5]], ["long", "short"],
                 lambda b, x: b.avg_range(5) > x * b.avg_range(50),
                 lambda x: f"最近5日の値幅の平均が50日の平均の{x}倍より大きい"),
    "not_dow": ([[0, 4]], ["long", "short"], lambda b, d: b.weekday() != d, lambda d: f"{DOW_JA[d]}曜日でない"),
}
SETUPS = [k for k in COND if k not in ("above_ma", "below_ma", "vol_high", "not_dow")]
FILTERS = ["above_ma", "below_ma", "roc_gt", "roc_lt", "vol_high", "squeeze", "not_dow", "month_start", "ibs_lt", "ibs_gt"]


def _prev(x):
    return np.concatenate([[np.nan], x[:-1]])


def _cross(fast, slow, up):
    pf, ps = _prev(fast), _prev(slow)
    return (fast > slow) & (pf <= ps) if up else (fast < slow) & (pf >= ps)


def cond_mask(b, cond):
    name, args = cond[0], cond[1:]
    with np.errstate(invalid="ignore"):
        m = COND[name][2](b, *args)
    m = np.asarray(m, dtype=bool) & np.isfinite(b.c)
    m[:WARMUP] = False
    return m


def cond_ja(cond):
    return COND[cond[0]][3](*cond[1:])


# ─────────────────────────────── 方法（spec） ───────────────────────────────
def canon(spec):
    conds = sorted([list(c) for c in spec["conds"]], key=lambda c: json.dumps(c))
    return {"direction": spec["direction"], "universe": spec["universe"], "conds": conds, "exit": spec["exit"]}


def spec_id(spec):
    s = json.dumps(canon(spec), sort_keys=True, ensure_ascii=False)
    return "ml-" + hashlib.sha1(s.encode("utf-8")).hexdigest()[:8]


def spec_name(spec):
    side = "買う" if spec["direction"] == "long" else "売る"
    conds = "かつ".join(f"「{cond_ja(c)}」" for c in spec["conds"])
    return f"{UNIVERSE_JA[spec['universe']]}で、{conds}のときに{side}"


def spec_valid(spec):
    try:
        if spec["direction"] not in ("long", "short") or spec["universe"] not in UNIVERSES or spec["exit"] not in EXITS:
            return False
        if not 1 <= len(spec["conds"]) <= 3:
            return False
        names = [c[0] for c in spec["conds"]]
        if len(set(names)) != len(names):
            return False
        for c in spec["conds"]:
            params, _dirs, _fn, _ja = COND[c[0]]
            if len(c) - 1 != len(params):
                return False
            for v, choices in zip(c[1:], params):
                if v not in choices:
                    return False
        return True
    except Exception:
        return False


def describe(spec):
    return {"id": spec_id(spec), "name": spec_name(spec), "exit_ja": EXIT_JA[spec["exit"]],
            "universe_ja": UNIVERSE_JA[spec["universe"]], "conds_ja": [cond_ja(c) for c in spec["conds"]],
            "direction": spec["direction"], "spec": canon(spec)}


# ─────────────────────────────── 数える ───────────────────────────────
def trades_of(spec, bars, since=None):
    """[(シグナルの日, 銘柄, t, R)]。持っている間は次に入らない。since 以降のシグナルだけ（前向き）。決まっていないものは除く。"""
    dirn = 1 if spec["direction"] == "long" else -1
    out = []
    for sym in UNIVERSES[spec["universe"]]:
        b = bars.get(sym)
        if b is None or b.n < WARMUP + 5:
            continue
        m = np.ones(b.n, dtype=bool)
        for c in spec["conds"]:
            m &= cond_mask(b, c)
        R, held = b.outcome(dirn, spec["exit"])
        nxt = 0
        for t in np.flatnonzero(m):
            if since and b.dates[t] < since:
                continue
            if t < nxt:
                continue
            if not np.isfinite(R[t]):
                if held[t] == 0:  # まだ決まっていない（持っている途中）
                    break
                continue
            out.append((b.dates[t], sym, int(t), float(R[t])))
            nxt = t + max(int(held[t]), 1)
    out.sort()
    return out


def stats_of(trs):
    """回数・平均R・95%の幅（同じ日のシグナルはまとめて数える）・勝ち（R>0）の割合。"""
    n = len(trs)
    if not n:
        return {"n": 0, "mean": None, "lo": None, "hi": None, "win": None}
    Rs = np.array([r for *_x, r in trs])
    mean = float(Rs.mean())
    groups = {}
    for d, _s, _t, r in trs:
        groups.setdefault(d, []).append(r)
    G = len(groups)
    if G >= 2:
        se = math.sqrt(sum((sum(g) - len(g) * mean) ** 2 for g in groups.values()) * G / (G - 1)) / n
    else:
        se = float("nan")
    return {"n": n, "mean": round(mean, 4), "lo": round(mean - 1.96 * se, 4) if G >= 2 else None,
            "hi": round(mean + 1.96 * se, 4) if G >= 2 else None, "win": round(float((Rs > 0).mean()), 4)}


def placebo(spec, bars, trs, lo_date, hi_date, seed):
    """入る日だけでたらめにした平均R（PLACEBO_DRAWS 回）→ (平均, ばらつき, 本物以上の割合 p)。"""
    if not trs:
        return None
    dirn = 1 if spec["direction"] == "long" else -1
    rng = np.random.default_rng(seed)
    per = {}
    for _d, sym, _t, _r in trs:
        per[sym] = per.get(sym, 0) + 1
    total = np.zeros(PLACEBO_DRAWS)
    m_all = 0
    for sym, m in per.items():
        b = bars[sym]
        R, _h = b.outcome(dirn, spec["exit"])
        idx = np.arange(b.n)
        dates = np.array(b.dates)
        ok = np.isfinite(R) & (idx >= WARMUP) & (dates >= lo_date) & (dates <= hi_date)
        pool = R[ok]
        if not len(pool):
            continue
        total += pool[rng.integers(0, len(pool), size=(PLACEBO_DRAWS, m))].sum(axis=1)
        m_all += m
    if not m_all:
        return None
    means = total / m_all
    actual = float(np.mean([r for *_x, r in trs]))
    p = (1 + int((means >= actual).sum())) / (PLACEBO_DRAWS + 1)
    sd = float(means.std())
    return {"mean": round(float(means.mean()), 4), "sd": round(sd, 4), "p": round(p, 4),
            "excess": round(actual - float(means.mean()), 4),
            "z": round((actual - float(means.mean())) / sd, 3) if sd > 0 else None}


def _years(lo, hi):
    return max((dt.date.fromisoformat(hi) - dt.date.fromisoformat(lo)).days / 365.25, 1e-9)


def evaluate(spec, bars, for_date, with_years=False):
    """探す期間・確かめる期間の数字と、合否。"""
    trs = trades_of(spec, bars)
    confirm_end = (dt.date.fromisoformat(for_date) - dt.timedelta(days=1)).isoformat()
    ex = [x for x in trs if x[0] <= EXPLORE_END]
    co = [x for x in trs if CONFIRM_START <= x[0] <= confirm_end]
    seed = int(hashlib.sha1((spec_id(spec) + for_date).encode()).hexdigest()[:8], 16)
    first = min((bars[s].dates[WARMUP] for s in UNIVERSES[spec["universe"]] if s in bars and bars[s].n > WARMUP),
                default="2000-01-01")
    res = {"explore": stats_of(ex), "confirm": stats_of(co)}
    res["explore"]["placebo"] = placebo(spec, bars, ex, first, EXPLORE_END, seed)
    res["confirm"]["placebo"] = placebo(spec, bars, co, CONFIRM_START, confirm_end, seed + 1)
    res["confirm"]["per_year"] = round(len(co) / _years(CONFIRM_START, confirm_end), 1)
    res["explore"]["from"] = first
    res["confirm"]["to"] = confirm_end
    gates = screen(res)
    res["gates"] = gates
    res["passed"] = all(gates.values())
    if with_years:
        by = {}
        for d, _s, _t, r in trs:
            if d <= confirm_end:
                by.setdefault(d[:4], []).append(r)
        res["by_year"] = {y: [len(v), round(float(np.mean(v)), 3)] for y, v in sorted(by.items())}
    return res


def screen(res):
    e, c = res["explore"], res["confirm"]
    ep, cp = e.get("placebo") or {}, c.get("placebo") or {}
    return {
        "explore": bool(e["n"] >= MIN_N_EXPLORE and (e["mean"] or 0) > 0 and ep.get("p", 1) < P_MAX),
        "confirm": bool(c["n"] >= MIN_N_CONFIRM and (c["mean"] or 0) > 0 and (cp.get("excess") or 0) > 0),
        "frequency": bool((c.get("per_year") or 0) >= MIN_PER_YEAR),
    }


# ─────────────────────────────── 候補を作る ───────────────────────────────
def _rand_cond(rng, name):
    params = COND[name][0]
    return [name] + [rng.choice(p) for p in params]


def random_spec(rng):
    setup = rng.choice(SETUPS)
    direction = rng.choice(COND[setup][1])
    conds = [_rand_cond(rng, setup)]
    if rng.random() < 0.7:
        f = rng.choice([x for x in FILTERS if x != setup])
        conds.append(_rand_cond(rng, f))
    return {"direction": direction, "universe": rng.choice(list(UNIVERSES)), "conds": conds,
            "exit": rng.choice(list(EXITS))}


def mutate(spec, rng):
    s = json.loads(json.dumps(canon(spec)))
    op = rng.choice(["param", "param", "exit", "universe", "add", "drop"])
    if op == "param":
        cands = [i for i, c in enumerate(s["conds"]) if COND[c[0]][0]]
        if cands:
            i = rng.choice(cands)
            c = s["conds"][i]
            j = rng.randrange(len(COND[c[0]][0]))
            choices = COND[c[0]][0][j]
            pos = choices.index(c[j + 1]) if c[j + 1] in choices else 0
            step = rng.choice([-1, 1])
            c[j + 1] = choices[min(max(pos + step, 0), len(choices) - 1)]
            if c[j + 1] == spec_lookup(spec, i, j):
                c[j + 1] = choices[min(max(pos - step, 0), len(choices) - 1)]
        else:
            op = "exit"
    if op == "exit":
        s["exit"] = rng.choice([e for e in EXITS if e != s["exit"]])
    elif op == "universe":
        s["universe"] = rng.choice([u for u in UNIVERSES if u != s["universe"]])
    elif op == "add" and len(s["conds"]) < 3:
        have = {c[0] for c in s["conds"]}
        f = rng.choice([x for x in FILTERS if x not in have])
        s["conds"].append(_rand_cond(rng, f))
    elif op == "drop" and len(s["conds"]) > 1:
        s["conds"].pop(rng.randrange(1, len(s["conds"])))
    return s


def spec_lookup(spec, i, j):
    try:
        return canon(spec)["conds"][i][j + 1]
    except Exception:
        return None


def load_ideas():
    if not os.path.exists(IDEAS):
        return []
    return json.load(open(IDEAS, encoding="utf-8")).get("ideas", [])


def make_batch(for_date, tested, parents, k=K_DEFAULT):
    """その日の候補（決まった種で作る＝何度動かしても同じ）。[(出どころ, spec, 理由 or 親の ID)]"""
    rng = random.Random(int(hashlib.sha1(("method-lab:" + for_date).encode()).hexdigest()[:12], 16))
    seen = set(tested)
    out = []

    def add(src, spec, why=None):
        if spec_valid(spec) and spec_id(spec) not in seen and len(out) < k:
            seen.add(spec_id(spec))
            out.append((src, canon(spec), why))
            return True
        return False

    n_idea = 0
    for idea in load_ideas():
        if n_idea >= K_IDEAS:
            break
        if add("idea", idea["spec"], idea.get("why")):
            n_idea += 1
    tries = 0
    target = len(out) + K_MUT
    while parents and len(out) < target and tries < 400:
        tries += 1
        p = parents[min(int(rng.random() ** 2 * len(parents)), len(parents) - 1)]  # 上位ほど選ばれやすい
        add("mutation", mutate(p["spec"], rng), p["id"])
    tries = 0
    while len(out) < k and tries < 2000:
        tries += 1
        add("random", random_spec(rng))
    return out


def pick_parents(registry, lab):
    """進化の親：研究中の方法（前向き30回以上なら前向きの平均、それより少なければ探す期間の z の順）＋過去で惜しかった方法。"""
    rows = []
    for m in (registry or {}).get("methods", []):
        if m.get("status") not in ("tracking", "promoted"):
            continue
        fw = ((lab or {}).get("forward") or {}).get(m["id"]) or {}
        if (fw.get("n") or 0) >= 30:
            key = 10 + (fw.get("mean") or 0)
        else:
            key = (m.get("past", {}).get("explore", {}).get("placebo") or {}).get("z") or 0
        rows.append((key, {"id": m["id"], "spec": m["spec"]}))
    for t in (lab or {}).get("near", [])[:6]:
        rows.append(((t.get("z") or 0) / 10, {"id": t["id"], "spec": t["spec"]}))
    rows.sort(key=lambda x: -x[0])
    return [r for _k, r in rows]


# ─────────────────────────────── 前向き ───────────────────────────────
def forward_stats(spec, bars, since, asof_seed):
    trs = trades_of(spec, bars, since=since)
    st = stats_of(trs)
    last_bar = max((bars[s].dates[-1] for s in UNIVERSES[spec["universe"]] if s in bars and bars[s].n), default=since)
    pl = placebo(spec, bars, trs, since, last_bar, asof_seed) if trs else None
    st["placebo"] = pl
    st["excess"] = pl["excess"] if pl else None
    st["since"] = since
    st["through"] = last_bar
    st["last_signal"] = trs[-1][0] if trs else None
    return st


# ─────────────────────────────── 実行 ───────────────────────────────
def next_routine_date(now=None):
    """次に routine（毎朝 06:10 JST）が記事を書く日。06:00 より前なら今日、あとなら明日。"""
    now = now or dt.datetime.now(JST)
    d = now.date()
    if now.hour >= 6:
        d += dt.timedelta(days=1)
    return d.isoformat()


def load_json(path, default):
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return default


def load_all_bars(refresh=False):
    bars, missing = {}, []
    for s in SYMS:
        try:
            bars[s] = load_bars(s, refresh=refresh)
        except Exception as e:
            print(f"⚠️ {s}: {e}")
            missing.append(s)
    return bars, missing


def cmd_forward(lab, registry, bars, now_jst):
    fw = {}
    for m in registry.get("methods", []):
        if m.get("status") not in ("tracking", "promoted"):
            continue
        seed = int(hashlib.sha1((m["id"] + "fwd").encode()).hexdigest()[:8], 16)
        fw[m["id"]] = forward_stats(m["spec"], bars, m["registered_at"], seed)
    lab["forward"] = fw
    lab["forward_asof"] = now_jst
    return lab


def run_batch(for_date, lab, registry, bars, k=K_DEFAULT):
    tested = [t["id"] for t in lab.get("tested", [])] + [m["id"] for m in registry.get("methods", [])]
    parents = pick_parents(registry, lab)
    batch = make_batch(for_date, tested, parents, k)
    rows = []
    for src, spec, why in batch:
        res = evaluate(spec, bars, for_date)
        e = res["explore"]
        rows.append({"id": spec_id(spec), "source": src, "why": why if src == "idea" else None,
                     "parent": why if src == "mutation" else None, "name": spec_name(spec), "spec": spec,
                     "explore": e, "confirm": res["confirm"], "gates": res["gates"], "passed": res["passed"],
                     "z": (e.get("placebo") or {}).get("z")})
    passed = [r for r in rows if r["passed"]]
    pool = passed or [r for r in rows if r["explore"]["n"] >= MIN_N_EXPLORE] or rows
    best = max(pool, key=lambda r: (r["z"] if r["z"] is not None else -9e9)) if pool else None
    chosen = None
    if best:
        detail = evaluate(best["spec"], bars, for_date, with_years=True)
        chosen = dict(best)
        chosen.update(describe(best["spec"]))
        chosen["by_year"] = detail.get("by_year", {})
        chosen["status"] = "passed" if best["passed"] else "near_miss"
    counts = {"tried": len(rows),
              "pass_explore": sum(r["gates"]["explore"] for r in rows),
              "pass_confirm": sum(r["gates"]["confirm"] for r in rows),
              "pass_frequency": sum(r["gates"]["frequency"] for r in rows),
              "pass_all": len(passed),
              "by_source": {s: sum(1 for r in rows if r["source"] == s) for s in ("idea", "mutation", "random")}}
    return {"for_date": for_date, "counts": counts, "chosen": chosen,
            "rows": [{k2: r[k2] for k2 in ("id", "source", "name", "passed", "gates", "z")} |
                     {"explore_n": r["explore"]["n"], "explore_mean": r["explore"]["mean"],
                      "confirm_n": r["confirm"]["n"], "confirm_mean": r["confirm"]["mean"],
                      "confirm_excess": (r["confirm"].get("placebo") or {}).get("excess"),
                      "per_year": r["confirm"].get("per_year")} for r in rows],
            "_full": rows}


def write_md(lab):
    L = ["# 🧪 毎日の新しい方法（method-lab）", "",
         f"- 更新: {lab.get('asof')}（値段は {lab.get('data_through')} まで）",
         "- 事前登録: PILLAR_PREREG.md「毎日の新しい方法と入れ替え（2026-11-17）」", ""]
    for d in sorted(lab.get("batches", {}), reverse=True)[:3]:
        b = lab["batches"][d]
        c = b["counts"]
        L.append(f"## {d} の候補（{c['tried']}通り・合格 {c['pass_all']}）")
        ch = b.get("chosen")
        if ch:
            tag = "✅ 新しい方法（前向きへ）" if ch["status"] == "passed" else "△ 惜しかった方法（前向きには進めない）"
            e, co = ch["explore"], ch["confirm"]
            L.append(f"- {tag}: **{ch['name']}**（{ch['exit_ja']}）`{ch['id']}`")
            L.append(f"  - 探す期間: {e['n']}回・平均 {e['mean']:+.3f}R・偽薬との差 {(e.get('placebo') or {}).get('excess')}・p {(e.get('placebo') or {}).get('p')}")
            if co["n"]:
                L.append(f"  - 確かめる期間: {co['n']}回・平均 {co['mean']:+.3f}R・偽薬との差 {(co.get('placebo') or {}).get('excess')}・1年 {co.get('per_year')}回")
        L.append("")
        L.append("| 出どころ | 方法 | 探す n | 探す 平均R | 確かめ n | 確かめ 平均R | 合格 |")
        L.append("|---|---|---|---|---|---|---|")
        for r in b["rows"]:
            fm = lambda v: "—" if v is None else f"{v:+.3f}"
            L.append(f"| {r['source']} | {r['name']} | {r['explore_n']} | {fm(r['explore_mean'])} | {r['confirm_n']} | "
                     f"{fm(r['confirm_mean'])} | {'✅' if r['passed'] else '·'} |")
        L.append("")
    if lab.get("forward"):
        L.append("## 研究中の方法の前向き")
        L.append("| ID | 登録 | n | 平均R | 95%の幅 | 偽薬との差 |")
        L.append("|---|---|---|---|---|---|")
        for mid, f in sorted(lab["forward"].items()):
            fm = lambda v: "—" if v is None else f"{v:+.3f}"
            L.append(f"| {mid} | {f.get('since')} | {f['n']} | {fm(f['mean'])} | {fm(f['lo'])}〜{fm(f['hi'])} | {fm(f.get('excess'))} |")
    open(OUT_MD, "w", encoding="utf-8").write("\n".join(L) + "\n")


def cmd_daily(args):
    now = dt.datetime.now(JST)
    for_date = args.for_date or next_routine_date(now)
    lab = load_json(OUT_JSON, {})
    registry = load_json(REGISTRY, {"methods": []})
    bars, missing = load_all_bars(refresh=args.refresh)
    if len(bars) < len(SYMS) // 2:
        print("❌ 値段が半分も取れない＝やめる（前の版を残す）")
        sys.exit(1)
    lab.setdefault("batches", {})
    lab.setdefault("tested", [])
    if for_date in lab["batches"] and not args.force:
        print(f"{for_date} の候補はもうある（同じ日には作り直さない）＝前向きだけ数え直す")
    else:
        b = run_batch(for_date, lab, registry, bars, args.k)
        full = b.pop("_full")
        lab["batches"][for_date] = b
        known = {t["id"] for t in lab["tested"]}
        for r in full:
            if r["id"] not in known:
                lab["tested"].append({"id": r["id"], "date": for_date, "passed": r["passed"]})
        near = [r for r in full if r["gates"]["explore"] and not r["passed"]]
        lab["near"] = sorted(([{"id": r["id"], "spec": r["spec"], "z": r["z"], "date": for_date} for r in near]
                              + lab.get("near", [])), key=lambda x: -(x.get("z") or 0))[:20]
        c = b["counts"]
        ch = b.get("chosen") or {}
        print(f"{for_date}: {c['tried']}通り → 合格 {c['pass_all']}（探す {c['pass_explore']}・確かめ {c['pass_confirm']}・回数 {c['pass_frequency']}）")
        if ch:
            print(f"  {'新しい方法' if ch['status'] == 'passed' else '惜しかった方法'}: {ch['name']}（{ch['spec']['exit']}）{ch['id']}")
    for d in sorted(lab["batches"])[:-KEEP_BATCHES]:
        del lab["batches"][d]
    cmd_forward(lab, registry, bars, now.strftime("%Y-%m-%d %H:%M JST"))
    lab["asof"] = now.strftime("%Y-%m-%d %H:%M JST")
    lab["data_through"] = max(b.dates[-1] for b in bars.values() if b.n)
    lab["missing"] = missing
    lab["rules"] = {"explore_end": EXPLORE_END, "confirm_start": CONFIRM_START, "min_n_explore": MIN_N_EXPLORE,
                    "min_n_confirm": MIN_N_CONFIRM, "p_max": P_MAX, "min_per_year": MIN_PER_YEAR,
                    "placebo_draws": PLACEBO_DRAWS, "sl_mult": SL_MULT}
    json.dump(lab, open(OUT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    write_md(lab)
    print(f"→ {os.path.basename(OUT_JSON)} / {os.path.basename(OUT_MD)}")


def cmd_forward_only(args):
    now = dt.datetime.now(JST)
    lab = load_json(OUT_JSON, {})
    registry = load_json(REGISTRY, {"methods": []})
    bars, _missing = load_all_bars(refresh=args.refresh)
    cmd_forward(lab, registry, bars, now.strftime("%Y-%m-%d %H:%M JST"))
    json.dump(lab, open(OUT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    write_md(lab)


def cmd_test(args):
    spec = json.loads(args.spec)
    if not spec_valid(spec):
        print("形が正しくない（部品の名前・引数・向き・銘柄の組・手じまいを確かめる）")
        sys.exit(2)
    bars, _m = load_all_bars(refresh=args.refresh)
    for_date = args.for_date or next_routine_date()
    res = evaluate(spec, bars, for_date, with_years=True)
    print(json.dumps({"id": spec_id(spec), "name": spec_name(spec), **res}, ensure_ascii=False, indent=1))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("daily")
    a.add_argument("--for-date")
    a.add_argument("--k", type=int, default=K_DEFAULT)
    a.add_argument("--force", action="store_true")
    a.add_argument("--refresh", action="store_true")
    f = sub.add_parser("forward")
    f.add_argument("--refresh", action="store_true")
    t = sub.add_parser("test")
    t.add_argument("spec")
    t.add_argument("--for-date")
    t.add_argument("--refresh", action="store_true")
    args = ap.parse_args()
    {"daily": cmd_daily, "forward": cmd_forward_only, "test": cmd_test}[args.cmd](args)


if __name__ == "__main__":
    main()
