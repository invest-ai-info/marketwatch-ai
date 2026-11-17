# -*- coding: utf-8 -*-
"""
method_lab.py — 毎日の新しい方法（2026-11-17 オーナー決定）

オーナーの言葉:「新しい方法を毎日探して新しい方法だけをシグナル研究で発表してください。かといって増え続けるのも問題なので、
研究中の方法の中で最も成績の悪いものから削除していきましょう。1日1回新しい方法を見つけ出して研究として発表して
成績の悪いものは一つ消すという形に」「しっかりと研究して改善を繰り返し進化していきましょう」。
事前登録＝PILLAR_PREREG.md「毎日の新しい方法と入れ替え（2026-11-17）」。この冒頭とその節の決まりは、結果を見る前にコミットした。

■ 何をするか（GitHub Actions の method-lab.yml が毎晩・routine の push のあとに動かす。LLM は使わない）
  ※ 2026-11-17 夜に第2版へ（PILLAR_PREREG.md「毎日の新しい方法と入れ替え・第2版」＝結果を見る前にコミット）。
  1) サイトの監視18銘柄の日足（Yahoo・2000年ごろ〜）と、比べ用の「別の市場」22銘柄の日足を取る。
  2) その日の候補を K=200 通り作る（決まった種＝日付から作るので、何度動かしても同じ候補になる）。
       ・用意した考え方の一覧（method_ideas.json＝よく知られた方法・理由つき）から 2つ
       ・研究中の方法と、過去で惜しかった方法の「1か所だけ変えた形」（進化）から 40
       ・部品の組み合わせ（でたらめに選ぶ）から残り
     すでに試した形（同じ ID）は二度と試さない。
  3) 過去の確かめ8つ（全部満たして合格。偶然の合格を減らすため）:
       ① 探す期間（〜2017）: 100回以上・平均プラス・偽薬との差プラス・その日の200通りまとめての多重検定（BH q=0.05）
       ② 時代（〜2007／2008〜2012／2013〜2017）: 20回以上の時代で、偽薬との差がプラスでないのは1つまで
       ③ 銘柄の広がり: 3銘柄以上の組で、10回以上の銘柄の半分以上が偽薬との差プラス
       ④ 隣の値: 数の部品を1つずつ隣の値に変えた形（50回以上）の3分の2以上が偽薬との差プラス
       ⑤ 別の市場: 18銘柄に入っていない似た市場でも、30回以上あれば偽薬との差プラス
       ⑥ 確かめる期間（2018〜前日）: 50回以上・平均プラス・偽薬との差プラス・片側 p<0.05・2018〜2021／2022〜 の両方で差プラス
       ⑦ 費用2倍でも確かめる期間の平均がプラス
       ⑧ 確かめる期間の回数が1年あたり40以上
     合格したものは、売買の7割以上がすでにある方法（研究中・その日に先に通ったもの）と重ならなければ**全部**登録の候補にする。
     記事の主役＝その中で探す期間の z がいちばん大きいもの（無ければ「惜しかった方法」）。
  4) 研究中の方法（method-lab-registry.json）の前向きの成績を数える＝登録した日より後に出たシグナルだけ。

■ 登録・判定・入れ替えは routine が research_rotation.py で行う（この表は読むだけ）。

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
RULES_VERSION = 2          # 第2版（2026-11-17 夜）。版が変わったら試した形の一覧を空から始める
K_DEFAULT = 200
K_IDEAS, K_MUT = 2, 40
FDR_Q = 0.05
ERAS = [("1900-01-01", "2007-12-31"), ("2008-01-01", "2012-12-31"), ("2013-01-01", "2017-12-31")]
ERA_MIN_N = 20
HALVES = [("2018-01-01", "2021-12-31"), ("2022-01-01", "9999-12-31")]
HALF_MIN_N = 20
INSTR_MIN_N = 10
NEIGHBOR_MIN_N = 50
NEIGHBOR_SHARE = 2 / 3
OTHER_MIN_N = 30
OVERLAP_MAX = 0.70
ROWS_KEEP = 40            # 記録に残す候補の行（z の上位＋探す期間を通ったもの全部）
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
EXIT_JA = {   # 記事にそのまま出る＝やさしい日本語（check_plain_japanese：「×」「R」を使わない）
    "atr_tp": "損切りはATRの1.5倍・利確はATRの2倍（サイトのシグナルと同じ・最長20日）",
    "atr_tp3": "損切りはATRの1.5倍・利確はATRの3倍（最長30日）",
    "hold_1": "次の日の終値で手じまい（損切りはATRの1.5倍）",
    "hold_3": "3日目の終値で手じまい（損切りはATRの1.5倍）",
    "hold_5": "5日目の終値で手じまい（損切りはATRの1.5倍）",
    "hold_10": "10日目の終値で手じまい（損切りはATRの1.5倍）",
}
DOW_JA = ["月", "火", "水", "木", "金"]
# 別の市場（18銘柄に入っていない似た市場＝⑤の確かめ用。登録・前向きには使わない）
OTHER = {
    "index": ["^GDAXI", "^FCHI", "^STOXX50E", "^HSI", "^AXJO", "^GSPTSE", "RTY=F", "^KS11"],
    "commodity": ["HG=F", "PL=F", "NG=F", "HO=F", "ZS=F"],
    "jpy_fx": ["CADJPY=X", "CHFJPY=X", "NZDJPY=X"],
    "nonjpy_fx": ["USDCAD=X", "USDCHF=X", "NZDUSD=X", "EURGBP=X", "EURCHF=X"],
    "btc": ["ETH-USD"],
}
OTHER_OF = {
    "index": OTHER["index"], "commodity": OTHER["commodity"], "jpy_fx": OTHER["jpy_fx"],
    "nonjpy_fx": OTHER["nonjpy_fx"], "fx": OTHER["jpy_fx"] + OTHER["nonjpy_fx"],
    "risk": OTHER["index"] + OTHER["btc"], "all": [s for v in OTHER.values() for s in v],
}
OTHER_SYMS = [s for v in OTHER.values() for s in v]
OTHER_SPREAD_PCT = {s: 0.0003 for s in OTHER["index"]} | {s: 0.0008 for s in OTHER["commodity"]} | {"ETH-USD": 0.0006}


def _spread(sym, price):
    """往復の費用（値段の単位）。signal_lab_sweep の表と同じ考え（為替は pips・ほかは値段の割合）。"""
    try:
        from signal_lab_sweep import SPREAD_PCT
    except Exception:  # pragma: no cover
        SPREAD_PCT = {}
    if sym in SPREAD_PCT:
        return price * SPREAD_PCT[sym]
    if sym in OTHER_SPREAD_PCT:
        return price * OTHER_SPREAD_PCT[sym]
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
        """(R, 持った日数)。R は費用を引いたあと。"""
        key = (dirn, exit_name)
        if key not in self._out:
            self._out[key] = _outcome(self, dirn, exit_name)
        return self._out[key][:2]

    def cost_r(self, dirn, exit_name):
        """各日に入った場合の費用（R の単位）。費用2倍の確かめ用。"""
        self.outcome(dirn, exit_name)
        return self._out[(dirn, exit_name)][2]

    def pool_mean(self, dirn, exit_name, lo, hi):
        """でたらめに入った場合の平均（lo〜hi のシグナルの日すべての R の平均＝偽薬の平均を正確に出したもの）と日数。"""
        key = ("pool", dirn, exit_name, lo, hi)
        if key not in self._cache:
            R, _h = self.outcome(dirn, exit_name)
            idx = np.arange(self.n)
            d = np.array(self.dates)
            ok = np.isfinite(R) & (idx >= WARMUP) & (d >= lo) & (d <= hi)
            self._cache[key] = (float(R[ok].mean()) if ok.any() else None, int(ok.sum()))
        return self._cache[key]


def _outcome(b, dirn, exit_name):
    """各日 t にシグナルが出たとして、t+1 の始値で入ったときの (R, 持った日数)。データの終わりで決まらないものは NaN。"""
    tpm, maxb = EXITS[exit_name]
    n = b.n
    R = np.full(n, np.nan)
    held = np.zeros(n, dtype=int)
    costR = np.full(n, np.nan)
    if n < 3:
        return R, held, costR
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
    with np.errstate(invalid="ignore", divide="ignore"):
        costR[:-1] = np.where(ok, cost / risk, np.nan)
    return R, held, costR


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
def trades_of(spec, bars, since=None, syms=None, until=None):
    """[(シグナルの日, 銘柄, t, R)]。持っている間は次に入らない。since 以降・until 以前のシグナルだけ。決まっていないものは除く。
    syms を渡すと、その銘柄で数える（別の市場の確かめ用）。"""
    dirn = 1 if spec["direction"] == "long" else -1
    out = []
    for sym in (syms if syms is not None else UNIVERSES[spec["universe"]]):
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
            if until and b.dates[t] > until:
                break
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
    z = (actual - float(means.mean())) / sd if sd > 0 else None
    return {"mean": round(float(means.mean()), 4), "sd": round(sd, 4), "p": round(p, 4),
            "excess": round(actual - float(means.mean()), 4), "z": None if z is None else round(z, 3),
            "p_norm": None if z is None else float(0.5 * math.erfc(z / math.sqrt(2)))}


def _years(lo, hi):
    return max((dt.date.fromisoformat(hi) - dt.date.fromisoformat(lo)).days / 365.25, 1e-9)


def excess_exact(spec, bars, trs, lo, hi):
    """平均 − でたらめに入った場合の平均（銘柄ごとの全部の日の平均を、回数で重みづけ＝偽薬の平均を正確に）。"""
    if not trs:
        return None
    dirn = 1 if spec["direction"] == "long" else -1
    per = {}
    for _d, sym, _t, _r in trs:
        per[sym] = per.get(sym, 0) + 1
    base, m = 0.0, 0
    for sym, k in per.items():
        pm, _n = bars[sym].pool_mean(dirn, spec["exit"], lo, hi)
        if pm is None:
            continue
        base += pm * k
        m += k
    if not m:
        return None
    return float(np.mean([r for *_x, r in trs])) - base / m


def _within(trs, lo, hi):
    return [x for x in trs if lo <= x[0] <= hi]


def explore_eval(spec, bars, for_date):
    """① 探す期間の数字（200通りすべてに数える）。"""
    trs = trades_of(spec, bars)
    ex = [x for x in trs if x[0] <= EXPLORE_END]
    seed = int(hashlib.sha1((spec_id(spec) + for_date).encode()).hexdigest()[:8], 16)
    first = min((bars[s].dates[WARMUP] for s in UNIVERSES[spec["universe"]] if s in bars and bars[s].n > WARMUP),
                default="2000-01-01")
    st = stats_of(ex)
    st["placebo"] = placebo(spec, bars, ex, first, EXPLORE_END, seed)
    st["from"] = first
    return trs, st


def neighbors(spec):
    """数の部品を1つずつ隣の値に変えた形（④）。"""
    out = []
    base = canon(spec)
    for i, c in enumerate(base["conds"]):
        params = COND[c[0]][0]
        for j, choices in enumerate(params):
            if c[j + 1] not in choices:
                continue
            pos = choices.index(c[j + 1])
            for q in (pos - 1, pos + 1):
                if 0 <= q < len(choices):
                    nb = json.loads(json.dumps(base))
                    nb["conds"][i][j + 1] = choices[q]
                    out.append(nb)
    return out


def full_eval(spec, bars, others, for_date, trs, ex):
    """②〜⑧（探す期間の多重検定を通ったものだけに数える）。"""
    confirm_end = (dt.date.fromisoformat(for_date) - dt.timedelta(days=1)).isoformat()
    dirn = 1 if spec["direction"] == "long" else -1
    seed = int(hashlib.sha1((spec_id(spec) + for_date).encode()).hexdigest()[:8], 16)
    res = {}
    # ② 時代
    eras = []
    for lo, hi in ERAS:
        t = _within(trs, lo, min(hi, EXPLORE_END))
        exs = excess_exact(spec, bars, t, lo, hi)
        eras.append({"from": lo, "to": hi, "n": len(t), "mean": None if not t else round(float(np.mean([x[3] for x in t])), 4),
                     "excess": None if exs is None else round(exs, 4)})
    counted = [e for e in eras if e["n"] >= ERA_MIN_N]
    bad = [e for e in counted if (e["excess"] or 0) <= 0]
    res["eras"] = eras
    g_eras = len(counted) >= 2 and len(bad) <= 1
    # ③ 銘柄の広がり
    allt = _within(trs, "1900-01-01", confirm_end)
    syms = UNIVERSES[spec["universe"]]
    inst = []
    for sym in syms:
        t = [x for x in allt if x[1] == sym]
        if len(t) >= INSTR_MIN_N:
            exs = excess_exact(spec, bars, t, "1900-01-01", confirm_end)
            inst.append({"sym": sym, "n": len(t), "excess": None if exs is None else round(exs, 4)})
    pos = sum(1 for x in inst if (x["excess"] or 0) > 0)
    res["instruments"] = {"counted": len(inst), "positive": pos, "detail": inst}
    g_inst = len(syms) < 3 or (len(inst) > 0 and pos >= 0.5 * len(inst))
    # ④ 隣の値
    nbs = []
    for nb in neighbors(spec):
        t = [x for x in trades_of(nb, bars) if x[0] <= EXPLORE_END]
        if len(t) >= NEIGHBOR_MIN_N:
            exs = excess_exact(nb, bars, t, "1900-01-01", EXPLORE_END)
            nbs.append({"id": spec_id(nb), "n": len(t), "excess": None if exs is None else round(exs, 4)})
    npos = sum(1 for x in nbs if (x["excess"] or 0) > 0)
    res["neighbors"] = {"counted": len(nbs), "positive": npos}
    g_nb = not nbs or npos >= NEIGHBOR_SHARE * len(nbs) - 1e-9
    # ⑤ 別の市場
    osyms = [x for x in OTHER_OF.get(spec["universe"], []) if x in others]
    ot = trades_of(spec, others, syms=osyms, until=confirm_end) if osyms else []
    oexs = excess_exact(spec, others, ot, "1900-01-01", confirm_end) if ot else None
    res["others"] = {"n": len(ot), "mean": None if not ot else round(float(np.mean([x[3] for x in ot])), 4),
                     "excess": None if oexs is None else round(oexs, 4), "markets": len(osyms)}
    g_other = len(ot) < OTHER_MIN_N or (oexs or 0) > 0
    # ⑥ 確かめる期間
    co = _within(trs, CONFIRM_START, confirm_end)
    cst = stats_of(co)
    cst["placebo"] = placebo(spec, bars, co, CONFIRM_START, confirm_end, seed + 1)
    cst["per_year"] = round(len(co) / _years(CONFIRM_START, confirm_end), 1)
    cst["to"] = confirm_end
    halves = []
    for lo, hi in HALVES:
        t = _within(co, lo, min(hi, confirm_end))
        exs = excess_exact(spec, bars, t, lo, min(hi, confirm_end))
        halves.append({"from": lo, "to": min(hi, confirm_end), "n": len(t),
                       "mean": None if not t else round(float(np.mean([x[3] for x in t])), 4),
                       "excess": None if exs is None else round(exs, 4)})
    cst["halves"] = halves
    hc = [h for h in halves if h["n"] >= HALF_MIN_N]
    pl = cst["placebo"] or {}
    g_conf = (cst["n"] >= MIN_N_CONFIRM and (cst["mean"] or 0) > 0 and (pl.get("excess") or 0) > 0
              and (pl.get("p_norm") if pl.get("p_norm") is not None else 1) < P_MAX
              and len(hc) >= 1 and all((h["excess"] or 0) > 0 for h in hc))
    # ⑦ 費用2倍
    if co:
        extra = [bars[x[1]].cost_r(dirn, spec["exit"])[x[2]] for x in co]
        cost2 = float(np.mean([x[3] for x in co]) - np.nanmean(extra))
    else:
        cost2 = None
    cst["cost2_mean"] = None if cost2 is None else round(cost2, 4)
    g_cost = cost2 is not None and cost2 > 0
    # ⑧ 回数
    g_freq = cst["per_year"] >= MIN_PER_YEAR
    res["confirm"] = cst
    res["gates"] = {"eras": g_eras, "instruments": g_inst, "neighbors": g_nb, "markets": g_other,
                    "confirm": g_conf, "cost": g_cost, "frequency": g_freq}
    by = {}
    for d, _s, _t, r in trs:
        if d <= confirm_end:
            by.setdefault(d[:4], []).append(r)
    res["by_year"] = {y: [len(v), round(float(np.mean(v)), 3)] for y, v in sorted(by.items())}
    return res


GATE_ORDER = ["explore", "eras", "instruments", "neighbors", "markets", "confirm", "cost", "frequency"]
GATE_JA = {"explore": "探す期間（多重検定）", "eras": "時代", "instruments": "銘柄の広がり", "neighbors": "隣の値",
           "markets": "別の市場", "confirm": "確かめる期間", "cost": "費用2倍", "frequency": "回数"}


def bh_pass(pvals, q=FDR_Q):
    """ベンジャミニ・ホッホベルグ法で通る添え字の集合（p が None のものは通さない）。"""
    items = sorted((p, i) for i, p in enumerate(pvals) if p is not None)
    m = len(pvals)
    k = 0
    for rank, (p, _i) in enumerate(items, start=1):
        if p <= q * rank / m:
            k = rank
    return {i for _p, i in items[:k]}


def overlap(a, b):
    """a の売買（銘柄・シグナルの日）のうち b と重なる割合。"""
    if not a:
        return 0.0
    sb = {(x[1], x[0]) for x in b}
    return sum(1 for x in a if (x[1], x[0]) in sb) / len(a)


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
        p = parents[tries % len(parents)]          # 親を順番に（1つの系統に偏らせない）
        tries += 1
        add("mutation", mutate(p["spec"], rng), p["id"])
    tries = 0
    while len(out) < k and tries < 2000:
        tries += 1
        add("random", random_spec(rng))
    return out


PURE_FILTERS = {"above_ma", "below_ma", "roc_gt", "roc_lt", "vol_high", "not_dow", "squeeze", "month_start"}
PARENT_FAMILIES = 8


def family_of(spec):
    """系統＝向き＋絞り込み以外の部品の名前（銘柄の組・数・手じまいは問わない）。例：買い×RSI の売られすぎ。"""
    names = sorted({c[0] for c in spec["conds"]} - PURE_FILTERS) or sorted({c[0] for c in spec["conds"]})
    return spec["direction"] + ":" + "+".join(names)


def pick_parents(registry, lab):
    """進化の親：研究中の新しい方法（全部）＋過去で惜しかった方法（探す期間の z の順・系統ごとに1つまで・最大8系統）。
    2026-11-17 夜：試しの3日分で「1か所変えた形」が1つの系統（株価指数の2日 RSI の押し目買い）に偏ったので、系統ごとに1つまでにした
    （合格の物差しは変えていない＝PILLAR_PREREG 第2版の追記）。"""
    out, fams = [], set()
    for m in (registry or {}).get("methods", []):
        if m.get("status") in ("tracking", "promoted"):
            out.append({"id": m["id"], "spec": m["spec"]})
    for t in sorted((lab or {}).get("near", []), key=lambda x: -(x.get("z") or 0)):
        f = family_of(t["spec"])
        if f in fams or len(fams) >= PARENT_FAMILIES:
            continue
        fams.add(f)
        out.append({"id": t["id"], "spec": t["spec"]})
    return out


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


def load_all_bars(refresh=False, syms=None):
    bars, missing = {}, []
    for s in (syms or SYMS):
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


def run_batch(for_date, lab, registry, bars, others, k=K_DEFAULT):
    tested = list(lab.get("tested_ids", [])) + [m["id"] for m in registry.get("methods", [])]
    parents = pick_parents(registry, lab)
    batch = make_batch(for_date, tested, parents, k)
    rows = []
    for src, spec, why in batch:
        trs, ex = explore_eval(spec, bars, for_date)
        pl = ex.get("placebo") or {}
        basic = ex["n"] >= MIN_N_EXPLORE and (ex["mean"] or 0) > 0 and (pl.get("excess") or 0) > 0
        rows.append({"id": spec_id(spec), "source": src, "why": why if src == "idea" else None,
                     "parent": why if src == "mutation" else None, "name": spec_name(spec), "spec": spec,
                     "explore": ex, "z": pl.get("z"), "_trs": trs, "_p": pl.get("p_norm") if basic else None})
    fdr = bh_pass([r["_p"] for r in rows])
    funnel = {g: 0 for g in GATE_ORDER}
    for i, r in enumerate(rows):
        r["gates"] = {"explore": i in fdr}
        if i in fdr:
            r.update(full_eval(r["spec"], bars, others, for_date, r["_trs"], r["explore"]))
            r["gates"] = {"explore": True, **r["gates"]}
        ok = True
        for g in GATE_ORDER:
            ok = ok and bool(r["gates"].get(g))
            if ok:
                funnel[g] += 1
        r["passed"] = ok
    # ほぼ同じ方法は1つに（研究中の方法・その日に先に通ったものと売買が7割以上重なるものは登録しない）
    live = [trades_of(m["spec"], bars) for m in registry.get("methods", []) if m.get("status") in ("tracking", "promoted")]
    accepted, dups = [], []
    for r in sorted([r for r in rows if r["passed"]], key=lambda r: -(r["z"] or 0)):
        hit = max([overlap(r["_trs"], t) for t in live + [a["_trs"] for a in accepted]] or [0.0])
        r["overlap"] = round(hit, 3)
        (dups if hit >= OVERLAP_MAX else accepted).append(r)
    for r in dups:
        r["duplicate"] = True

    def full_record(r, status):
        out = dict(r)
        out.update(describe(r["spec"]))
        out["status"] = status
        for key in ("_trs", "_p"):
            out.pop(key, None)
        return out

    registered = [full_record(r, "passed") for r in accepted]
    if registered:
        chosen = registered[0]
    else:
        pool = [r for r in rows if r["gates"].get("explore")] or [r for r in rows if r["explore"]["n"] >= MIN_N_EXPLORE] or rows
        best = max(pool, key=lambda r: (r["z"] if r["z"] is not None else -9e9)) if pool else None
        if best is not None and "confirm" not in best:
            best.update(full_eval(best["spec"], bars, others, for_date, best["_trs"], best["explore"]))
            best["gates"] = {"explore": best["gates"].get("explore", False), **best["gates"]}
        chosen = full_record(best, "near_miss") if best else None
    counts = {"tried": len(rows), "pass_explore": funnel["explore"], "pass_eras": funnel["eras"],
              "pass_instruments": funnel["instruments"], "pass_neighbors": funnel["neighbors"],
              "pass_markets": funnel["markets"], "pass_confirm": funnel["confirm"], "pass_cost": funnel["cost"],
              "pass_frequency": funnel["frequency"], "pass_all": sum(1 for r in rows if r["passed"]),
              "duplicates": len(dups), "registered": len(registered),
              "by_source": {s2: sum(1 for r in rows if r["source"] == s2) for s2 in ("idea", "mutation", "random")}}
    keep = {r["id"] for r in sorted(rows, key=lambda r: -(r["z"] or -9e9))[:ROWS_KEEP]} | {r["id"] for r in rows if r["gates"].get("explore")}
    slim = []
    for r in rows:
        if r["id"] not in keep:
            continue
        c = r.get("confirm") or {}
        slim.append({"id": r["id"], "source": r["source"], "name": r["name"], "passed": r["passed"],
                     "gates": r["gates"], "z": r["z"], "explore_n": r["explore"]["n"], "explore_mean": r["explore"]["mean"],
                     "confirm_n": c.get("n"), "confirm_mean": c.get("mean"),
                     "confirm_excess": (c.get("placebo") or {}).get("excess"), "duplicate": r.get("duplicate", False)})
    near = [{"id": r["id"], "spec": r["spec"], "z": r["z"], "date": for_date}
            for r in rows if r["gates"].get("explore") and not r["passed"]]
    return {"for_date": for_date, "rules_version": RULES_VERSION, "counts": counts, "chosen": chosen,
            "registered": registered, "rows": slim}, [r["id"] for r in rows], near


def write_md(lab):
    fm = lambda v: "—" if v is None else f"{v:+.3f}"
    L = ["# 🧪 毎日の新しい方法（method-lab）", "",
         f"- 更新: {lab.get('asof')}（値段は {lab.get('data_through')} まで）・決まりの版 {lab.get('rules_version')}",
         "- 事前登録: PILLAR_PREREG.md「毎日の新しい方法と入れ替え・第2版（2026-11-17 夜）」",
         f"- これまでに試した形: {len(lab.get('tested_ids', []))}通り", ""]
    for d in sorted(lab.get("batches", {}), reverse=True)[:3]:
        b = lab["batches"][d]
        c = b["counts"]
        L.append(f"## {d} の候補（{c['tried']}通り → 合格 {c['pass_all']}・ほぼ同じ {c.get('duplicates', 0)}・登録 {c.get('registered', 0)}）")
        L.append("")
        L.append("確かめごとに残った数（前から順に全部を満たした数）: " + " → ".join(
            f"{GATE_JA[g]} {c.get('pass_' + g, 0)}" for g in GATE_ORDER))
        L.append("")
        for ch in (b.get("registered") or ([b["chosen"]] if b.get("chosen") else [])):
            tag = "✅ 登録（前向きへ）" if ch["status"] == "passed" else "△ 惜しかった方法（登録しない）"
            e, co = ch["explore"], ch.get("confirm") or {}
            L.append(f"- {tag}: **{ch['name']}**（{ch['exit_ja']}）`{ch['id']}`")
            L.append(f"  - 探す期間: {e['n']}回・平均 {fm(e['mean'])}R・偽薬との差 {fm((e.get('placebo') or {}).get('excess'))}・z {(e.get('placebo') or {}).get('z')}")
            if co.get("n"):
                L.append(f"  - 確かめる期間: {co['n']}回・平均 {fm(co['mean'])}R・偽薬との差 {fm((co.get('placebo') or {}).get('excess'))}"
                         f"・p {round((co.get('placebo') or {}).get('p_norm') or 1, 4)}・1年 {co.get('per_year')}回・費用2倍 {fm(co.get('cost2_mean'))}R")
            if ch.get("gates"):
                L.append("  - 確かめ: " + "・".join(f"{GATE_JA[g]}{'○' if ch['gates'].get(g) else '×'}" for g in GATE_ORDER if g in ch["gates"]))
        L.append("")
        L.append("| 出どころ | 方法 | z | 探す n | 探す 平均R | 確かめ n | 確かめ 平均R | 合格 |")
        L.append("|---|---|---|---|---|---|---|---|")
        for r in sorted(b["rows"], key=lambda r: -(r["z"] or -9e9))[:30]:
            L.append(f"| {r['source']} | {r['name']} | {r['z']} | {r['explore_n']} | {fm(r['explore_mean'])} | {r['confirm_n'] or '—'} | "
                     f"{fm(r['confirm_mean'])} | {'✅' if r['passed'] and not r.get('duplicate') else '≒' if r.get('duplicate') else '·'} |")
        L.append("")
    if lab.get("forward"):
        L.append("## 研究中の方法の前向き")
        L.append("| ID | 登録 | n | 平均R | 95%の幅 | 偽薬との差 |")
        L.append("|---|---|---|---|---|---|")
        for mid, f in sorted(lab["forward"].items()):
            L.append(f"| {mid} | {f.get('since')} | {f['n']} | {fm(f['mean'])} | {fm(f['lo'])}〜{fm(f['hi'])} | {fm(f.get('excess'))} |")
    open(OUT_MD, "w", encoding="utf-8").write("\n".join(L) + "\n")


def save_lab(lab):
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(lab, fh, ensure_ascii=False, separators=(",", ":"))


def cmd_daily(args):
    now = dt.datetime.now(JST)
    for_date = args.for_date or next_routine_date(now)
    lab = load_json(OUT_JSON, {})
    if lab.get("rules_version") != RULES_VERSION:
        print(f"決まりの版が {lab.get('rules_version')} → {RULES_VERSION}：試した形の一覧と候補を空から始める（PILLAR_PREREG 第2版）")
        lab = {"rules_version": RULES_VERSION, "previous_versions": [{"version": lab.get("rules_version") or 1,
                                                                      "batches": sorted((lab.get("batches") or {}).keys())}]
               if lab else []}
    registry = load_json(REGISTRY, {"methods": []})
    bars, missing = load_all_bars(refresh=args.refresh)
    if len(bars) < len(SYMS) // 2:
        print("❌ 値段が半分も取れない＝やめる（前の版を残す）")
        sys.exit(1)
    lab.setdefault("batches", {})
    lab.setdefault("tested_ids", [])
    if for_date in lab["batches"] and not args.force:
        print(f"{for_date} の候補はもうある（同じ日には作り直さない）＝前向きだけ数え直す")
    else:
        others, omiss = load_all_bars(refresh=args.refresh, syms=OTHER_SYMS)
        missing += omiss
        b, ids, near = run_batch(for_date, lab, registry, bars, others, args.k)
        lab["batches"][for_date] = b
        known = set(lab["tested_ids"])
        lab["tested_ids"] += [i for i in ids if i not in known]
        lab["near"] = sorted(near + lab.get("near", []), key=lambda x: -(x.get("z") or 0))[:30]
        c = b["counts"]
        print(f"{for_date}: {c['tried']}通り → " + " → ".join(f"{GATE_JA[g]} {c['pass_' + g]}" for g in GATE_ORDER)
              + f"（ほぼ同じ {c['duplicates']}・登録 {c['registered']}）")
        for ch in (b.get("registered") or ([b["chosen"]] if b.get("chosen") else [])):
            print(f"  {'登録' if ch['status'] == 'passed' else '惜しかった方法'}: {ch['name']}（{ch['spec']['exit']}）{ch['id']}")
    for d in sorted(lab["batches"])[:-KEEP_BATCHES]:
        del lab["batches"][d]
    cmd_forward(lab, registry, bars, now.strftime("%Y-%m-%d %H:%M JST"))
    lab["asof"] = now.strftime("%Y-%m-%d %H:%M JST")
    lab["data_through"] = max(b.dates[-1] for b in bars.values() if b.n)
    lab["missing"] = missing
    lab["rules_version"] = RULES_VERSION
    lab["rules"] = {"explore_end": EXPLORE_END, "confirm_start": CONFIRM_START, "min_n_explore": MIN_N_EXPLORE,
                    "min_n_confirm": MIN_N_CONFIRM, "p_max": P_MAX, "fdr_q": FDR_Q, "min_per_year": MIN_PER_YEAR,
                    "placebo_draws": PLACEBO_DRAWS, "sl_mult": SL_MULT, "k": args.k, "overlap_max": OVERLAP_MAX}
    save_lab(lab)
    write_md(lab)
    print(f"→ {os.path.basename(OUT_JSON)} / {os.path.basename(OUT_MD)}")


def cmd_forward_only(args):
    now = dt.datetime.now(JST)
    lab = load_json(OUT_JSON, {})
    registry = load_json(REGISTRY, {"methods": []})
    bars, _missing = load_all_bars(refresh=args.refresh)
    cmd_forward(lab, registry, bars, now.strftime("%Y-%m-%d %H:%M JST"))
    save_lab(lab)
    write_md(lab)


def cmd_test(args):
    spec = json.loads(args.spec)
    if not spec_valid(spec):
        print("形が正しくない（部品の名前・引数・向き・銘柄の組・手じまいを確かめる）")
        sys.exit(2)
    bars, _m = load_all_bars(refresh=args.refresh)
    others, _o = load_all_bars(refresh=args.refresh, syms=OTHER_SYMS)
    for_date = args.for_date or next_routine_date()
    trs, ex = explore_eval(spec, bars, for_date)
    res = full_eval(spec, bars, others, for_date, trs, ex)
    print(json.dumps({"id": spec_id(spec), "name": spec_name(spec), "explore": ex, **res}, ensure_ascii=False, indent=1))


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
