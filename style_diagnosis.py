# -*- coding: utf-8 -*-
"""投資スタイル診断（自分の MT4 の取引履歴から「どの長さの取引が自分に合っているか」を数える）。2026-09-27 オーナー依頼。

質問に答えるだけの診断は、当たったかどうかを確かめられない。ここでは自分の実際の取引を保有時間の長さ（スタイル）ごとに分け、
費用を引いたあとで数える。「いろんな環境で取引している」（オーナー）ので、**値動きの大きさ・流れの向き・時期が変わっても
同じ結果になるか**まで確かめてから「合っている」と判定する。

⚠️ 取引履歴は個人の記録＝手元専用。入力も出力も research/ の下に置く（research/ は GitHub へ送られない）。
   このファイル（計算の道具）は公開リポジトリにあるが、個人のデータは1つも入れない。
⚠️ 判定の決まりは下の定数と judge() に固定（結果を見てから動かさない）。
⚠️ 投資助言ではない。過去の自分の記録の集計で、これからの成績を約束しない。

使い方（手元）:
  python style_diagnosis.py research/Statement.htm
  python style_diagnosis.py research/Statement.htm --profile research/style-diagnosis/profile.json
  python style_diagnosis.py --init-profile         → 自己申告の質問ファイルを research/style-diagnosis/ に作る
  オプション:
    --server-tz ny+7   MT4 のサーバー時刻（既定＝ニューヨーク+7時間＝夏は UTC+3・冬は UTC+2 の会社）。utc+2 / utc+3 / jst も可
    --no-market        値段を取りに行かない（環境の確認は「未確認」になり、「合っている」は出ない）
    --out DIR          出力先（既定 research/style-diagnosis）
"""
import argparse
import datetime as dt
import html
import json
import math
import os
import re
import sys
from zoneinfo import ZoneInfo

import numpy as np

JST, NY, UTC = ZoneInfo("Asia/Tokyo"), ZoneInfo("America/New_York"), dt.timezone.utc
OUT_DIR = os.path.join("research", "style-diagnosis")

# ── 判定の決まり（結果を見てから動かさない） ──
STYLES = [("スキャルピング", 0, 60), ("デイトレ", 60, 480), ("スイング", 480, 7200), ("長め", 7200, math.inf)]  # 保有時間（分）
MIN_N = 30            # これ未満は「記録が足りない」
MIN_N_CELL = 10       # 環境・時期の区分は、この件数以上の区分だけ見る
TOP_DROP = 5          # 大きい勝ちをこの回数だけ除いてもプラスか
N_BOOT = 2000
SEED = 20260927
ATR_N, SMA_N, VOL_WIN = 14, 200, 250
ATR_COVERAGE = 0.8    # 値段が取れた取引がこの割合以上なら「値動きの大きさ」で割った物差しを使う

SLOTS = ["平日6-9時", "平日9-18時", "平日18-24時", "平日0-6時", "週末"]
CLASSES = ["円のペア", "その他の為替", "金・銀", "株価指数", "原油", "暗号資産", "その他"]
CCY = {"usd", "jpy", "eur", "gbp", "aud", "nzd", "cad", "chf", "try", "zar", "mxn", "cnh", "hkd", "sgd", "nok", "sek", "pln"}
YAHOO = [(r"gold|xau", "GC=F"), (r"silver|xag", "SI=F"), (r"oil|wti|brent", "CL=F"), (r"n225|jp225|nikkei|jpn225", "NKD=F"),
         (r"nasdaq|us100|nas100|ustec", "NQ=F"), (r"sp500|us500|spx", "ES=F"), (r"dow|us30|dj30", "YM=F"),
         (r"uk100|ftse", "^FTSE"), (r"btc", "BTC-USD"), (r"eth", "ETH-USD")]


# ════════════════════ 読み込み ════════════════════

def server_to_jst(s, server_tz="ny+7"):
    """MT4 のサーバー時刻の文字列 → 日本時間"""
    t = dt.datetime.strptime(s.strip(), "%Y.%m.%d %H:%M:%S" if s.count(":") == 2 else "%Y.%m.%d %H:%M")
    z = server_tz.lower().replace(" ", "")
    if z == "jst":
        return t.replace(tzinfo=JST)
    m = re.fullmatch(r"ny([+-]\d+)", z)
    if m:
        return (t - dt.timedelta(hours=int(m.group(1)))).replace(tzinfo=NY).astimezone(JST)
    m = re.fullmatch(r"utc([+-]\d+)", z)
    if m:
        return (t - dt.timedelta(hours=int(m.group(1)))).replace(tzinfo=UTC).astimezone(JST)
    raise ValueError(f"--server-tz が読めません: {server_tz}")


def _num(s):
    s = (s or "").replace(" ", "").replace(",", "").replace(" ", "")
    return float(s) if s not in ("", "-") else 0.0


def _rows(text):
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", text, re.S | re.I):
        yield [html.unescape(re.sub(r"<[^>]+>", "", c)).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S | re.I)]


def read_text(path):
    """MT4 の保存形式の違い（UTF-8／UTF-16／Shift_JIS）を吸収して読む"""
    b = open(path, "rb").read()
    if b[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return b.decode("utf-16")
    for enc in ("utf-8", "cp932"):
        try:
            return b.decode(enc)
        except UnicodeDecodeError:
            pass
    return b.decode("utf-8", errors="replace")


def parse_statement(text, server_tz="ny+7"):
    """MT4 の口座履歴（Statement.htm / DetailedStatement.htm）→ (決済済みの取引, 口座の決済損益 or None)"""
    trades, closed_pl = [], None
    for r in _rows(text):
        if len(r) >= 2 and re.match(r"(Closed (Trade )?P/L|決済損益)[:：]?$", r[0] or ""):
            closed_pl = _num(r[1])
        if len(r) != 14 or r[2].lower() not in ("buy", "sell"):
            continue
        o, c = server_to_jst(r[1], server_tz), server_to_jst(r[8], server_tz)
        side = 1 if r[2].lower() == "buy" else -1
        po, pc = float(r[5]), float(r[9])
        profit, comm, tax, swap = _num(r[13]), _num(r[10]), _num(r[11]), _num(r[12])
        trades.append({"sym": r[4].lower(), "side": side, "lot": float(r[3]), "open": o, "close": c, "po": po, "pc": pc,
                       "sl": float(r[6] or 0), "profit": profit, "cost": comm + tax + swap, "comm": comm, "swap": swap,
                       "net": profit + comm + tax + swap, "hold_min": (c - o).total_seconds() / 60})
    trades.sort(key=lambda x: x["open"])
    return trades, closed_pl


# ════════════════════ 分ける ════════════════════

def style_of(x):
    return next(n for n, a, b in STYLES if a <= x["hold_min"] < b)


def slot_of(x):
    o = x["open"].astimezone(JST)
    if o.weekday() >= 5:
        return "週末"
    h = o.hour
    return "平日9-18時" if 9 <= h < 18 else "平日18-24時" if h >= 18 else "平日0-6時" if h < 6 else "平日6-9時"


def fx_pair(sym):
    s = re.sub(r"[^a-z]", "", sym.lower())[:6]
    return s if len(s) == 6 and s[:3] in CCY and s[3:] in CCY else None


def class_of(sym):
    p = fx_pair(sym)
    if p:
        return "円のペア" if p.endswith("jpy") else "その他の為替"
    s = sym.lower()
    for pat, name in ((r"gold|xau|silver|xag", "金・銀"), (r"oil|wti|brent", "原油"), (r"btc|eth|crypto", "暗号資産"),
                      (r"n225|jp225|nikkei|nasdaq|us100|nas100|sp500|us500|dow|us30|uk100|ftse|dax|ger", "株価指数")):
        if re.search(pat, s):
            return name
    return "その他"


def yahoo_of(sym):
    p = fx_pair(sym)
    if p:
        return p.upper() + "=X"
    for pat, tk in YAHOO:
        if re.search(pat, sym.lower()):
            return tk
    return None


# ════════════════════ 環境（その取引に入る前の日足で決める＝後から見た情報を使わない） ════════════════════

def daily_features(df):
    """日足 → 日付ごとの ATR14（ワイルダー）・値動きの大きさの順位（過去250日の中で）・200日線より上か"""
    h, l, c = (np.asarray(df[k].values, float) for k in ("High", "Low", "Close"))
    pc = np.concatenate([[c[0]], c[:-1]])
    tr = np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))
    atr = np.full(len(c), np.nan)
    if len(c) >= ATR_N:
        atr[ATR_N - 1] = tr[:ATR_N].mean()
        for i in range(ATR_N, len(c)):
            atr[i] = (atr[i - 1] * (ATR_N - 1) + tr[i]) / ATR_N
    rel = atr / c
    rank = np.full(len(c), np.nan)
    for i in range(len(c)):
        w = rel[max(0, i - VOL_WIN + 1): i + 1]
        w = w[~np.isnan(w)]
        if len(w) >= 60 and not np.isnan(rel[i]):
            rank[i] = (w < rel[i]).mean()
    sma = np.convolve(c, np.ones(SMA_N) / SMA_N, mode="full")[:len(c)]
    sma[:SMA_N - 1] = np.nan
    dates = [d.date() if hasattr(d, "date") else d for d in df.index]
    return {"dates": dates, "atr": atr, "rank": rank, "up": np.where(np.isnan(sma), np.nan, (c > sma).astype(float))}


def fetch_daily(ticker, start):
    import yfinance as yf
    import pandas as pd
    df = yf.download(ticker, start=start, interval="1d", progress=False, auto_adjust=True)
    if df is None or len(df) == 0:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df.dropna(subset=["High", "Low", "Close"])


def attach_market(trades, fetch=fetch_daily):
    """取引ごとに、入る前日までの日足で ATR・値動きの大きさ・流れの向きを付ける。取れなかった銘柄の一覧を返す"""
    if not trades:
        return []
    start = (min(x["open"] for x in trades) - dt.timedelta(days=500)).date().isoformat()
    feats, missing = {}, []
    for tk in sorted({yahoo_of(x["sym"]) for x in trades} - {None}):
        try:
            df = fetch(tk, start)
        except Exception as e:  # noqa: BLE001
            print(f"  ⚠️ {tk} の値段を取れず: {type(e).__name__}", file=sys.stderr)
            df = None
        if df is None or len(df) < 60:
            missing.append(tk)
            continue
        feats[tk] = daily_features(df)
    for x in trades:
        f = feats.get(yahoo_of(x["sym"]))
        x.update(atr=None, vol=None, trend=None)
        if not f:
            continue
        d = x["open"].astimezone(UTC).date()
        i = int(np.searchsorted(np.array(f["dates"]), d)) - 1        # 入った日より前の最後の日足
        if i < 0 or np.isnan(f["atr"][i]):
            continue
        x["atr"] = float(f["atr"][i])
        r = f["rank"][i]
        if not np.isnan(r):
            x["vol"] = "小さい" if r < 1 / 3 else "ふつう" if r < 2 / 3 else "大きい"
        u = f["up"][i]
        if not np.isnan(u):
            x["trend"] = "流れに沿う" if (u > 0) == (x["side"] > 0) else "流れに逆らう"
    return missing


def net_units(x, kind):
    """1回の損益を、ロットや銘柄に左右されない物差しにする。
    atr＝費用込みの値幅 ÷ 入る前の1日のふつうの値動き（ATR）／bp＝費用込みの値幅 ÷ 入った値段（1万分の1）"""
    move = x["side"] * (x["pc"] - x["po"])
    if x["profit"]:
        move *= x["net"] / x["profit"]          # 手数料・スワップを同じ割合で値幅に直す
    if kind == "atr":
        return move / x["atr"] if x.get("atr") else None
    return move / x["po"] * 1e4


# ════════════════════ 数える ════════════════════

def _week(x):
    y, w, _ = x["open"].astimezone(JST).isocalendar()
    return f"{y}-{w:02d}"


def boot_ci(vals, keys, n=N_BOOT, seed=SEED):
    """週ごとにまとめて引き直す（同じ週の取引は似た相場なので1かたまりとして扱う）"""
    vals, keys = np.asarray(vals, float), np.asarray(keys)
    if len(vals) < 2:
        return None, None
    rng = np.random.default_rng(seed)
    uk = np.unique(keys)
    idx = [np.flatnonzero(keys == k) for k in uk]
    sums = np.array([vals[i].sum() for i in idx])
    cnts = np.array([len(i) for i in idx])
    ms = np.empty(n)
    for j in range(n):
        p = rng.integers(0, len(uk), len(uk))
        ms[j] = sums[p].sum() / cnts[p].sum()
    return float(np.percentile(ms, 2.5)), float(np.percentile(ms, 97.5))


def group_stats(xs, kind):
    us = [(x, net_units(x, kind)) for x in xs]
    us = [(x, u) for x, u in us if u is not None]
    vals = [u for _, u in us]
    out = {"n": len(xs), "n_unit": len(vals), "net_yen": sum(x["net"] for x in xs),
           "cost_yen": sum(x["cost"] for x in xs), "win": float(np.mean([x["net"] > 0 for x in xs])) if xs else None}
    if vals:
        out["mean"] = float(np.mean(vals))
        out["lo"], out["hi"] = boot_ci(vals, [_week(x) for x, _ in us])
        s = sorted(vals)
        out["mean_wo_top"] = float(np.mean(s[:-TOP_DROP])) if len(s) > TOP_DROP else None
    return out


def judge(st, halves, cells, env_checked):
    """スタイルの判定（固定）。halves／cells＝[(区分名, 件数, 平均)]"""
    if st.get("n_unit", 0) < MIN_N or st.get("mean") is None:
        return "？ 記録が足りない", [f"{MIN_N}回未満"]
    if st["hi"] is not None and st["hi"] < 0:
        return "✕ 合っていない", ["95%の幅がまるごと0より下"]
    if st["mean"] <= 0:
        return "▽ マイナス寄り（確かではない）", ["平均がマイナス・幅は0をまたぐ"]
    why = []
    if st["lo"] is None or st["lo"] <= 0:
        why.append("95%の幅が0をまたぐ")
    if st.get("mean_wo_top") is None or st["mean_wo_top"] <= 0:
        why.append(f"大きい勝ち{TOP_DROP}回を除くとマイナス")
    bad_h = [n for n, k, m in halves if k >= MIN_N_CELL and m is not None and m <= 0]
    if bad_h:
        why.append("時期によってマイナス（" + "・".join(bad_h) + "）")
    if not env_checked:
        why.append("環境の確認ができていない")
    bad_c = [n for n, k, m in cells if k >= MIN_N_CELL and m is not None and m <= 0]
    if bad_c:
        why.append("環境によってマイナス（" + "・".join(bad_c) + "）")
    return ("◯ 合っている", []) if not why else ("△ プラスだが確かではない", why)


def diagnose(trades, kind, env_checked):
    by_style = {n: [x for x in trades if style_of(x) == n] for n, _, _ in STYLES}
    cut = trades[len(trades) // 2]["open"] if trades else None
    res = {}
    for name, xs in by_style.items():
        st = group_stats(xs, kind)
        halves = []
        for hn, ys in (("前半", [x for x in xs if x["open"] < cut]), ("後半", [x for x in xs if x["open"] >= cut])):
            vs = [v for v in (net_units(y, kind) for y in ys) if v is not None]
            halves.append((hn, len(vs), float(np.mean(vs)) if vs else None))
        cells = []
        for key, labels in (("vol", ("小さい", "ふつう", "大きい")), ("trend", ("流れに沿う", "流れに逆らう"))):
            for lab in labels:
                vs = [v for v in (net_units(y, kind) for y in xs if y.get(key) == lab) if v is not None]
                cells.append((("値動き" + lab) if key == "vol" else lab, len(vs), float(np.mean(vs)) if vs else None))
        verdict, why = judge(st, halves, cells, env_checked)
        res[name] = dict(st, halves=halves, cells=cells, verdict=verdict, why=why)
    return res


def cross(trades, keyf, labels, kind):
    """区分 × スタイル の 件数・円・平均"""
    out = {}
    for lab in labels:
        for s, _, _ in STYLES:
            xs = [x for x in trades if keyf(x) == lab and style_of(x) == s]
            vs = [v for v in (net_units(x, kind) for x in xs) if v is not None]
            out[(lab, s)] = (len(xs), sum(x["net"] for x in xs), float(np.mean(vs)) if vs else None)
    return out


def habits(trades):
    """参考（判定には使わない）：負けて閉じてから30分以内に入った取引・1日4回以上の日の取引"""
    closes = sorted((x["close"], x["net"]) for x in trades)
    after = [x for x in trades if any(n < 0 and 0 <= (x["open"] - c).total_seconds() <= 1800 for c, n in closes if c <= x["open"])]
    per = {}
    for x in trades:
        d = x["open"].astimezone(JST).date()
        per[d] = per.get(d, 0) + 1
    busy = [x for x in trades if per[x["open"].astimezone(JST).date()] >= 4]
    return {"after_loss": (len(after), sum(x["net"] for x in after)), "busy_days": (len(busy), sum(x["net"] for x in busy))}


# ════════════════════ 自己申告（参考） ════════════════════

PROFILE_TEMPLATE = {
    "説明": "answers の null を choices のどれかに書き換えてください。判定には使わず、記録との食い違いを見せるだけです。",
    "choices": {
        "weekday_daytime": ["見られない", "スマホで時々", "画面を見続けられる"],
        "weekday_evening": ["見られない", "スマホで時々", "画面を見続けられる"],
        "preferred_style": [n for n, _, _ in STYLES],
        "revenge_urge": ["負けた後すぐ取り返したくなる", "ならない"],
    },
    "answers": {"weekday_daytime": None, "weekday_evening": None, "preferred_style": None, "revenge_urge": None},
}


def compare_profile(ans, res, trades, hab):
    lines = []
    if not ans:
        return lines
    pref = ans.get("preferred_style")
    if pref in res:
        lines.append(f"- 自分で合うと思うスタイル＝{pref} → 記録の判定は「{res[pref]['verdict']}」")
    day = [x for x in trades if slot_of(x) == "平日9-18時"]
    if ans.get("weekday_daytime") in ("見られない", "スマホで時々") and day:
        lines.append(f"- 平日の日中は「{ans['weekday_daytime']}」→ それでも平日9〜18時に入った取引が {len(day)}回"
                     f"（{sum(x['net'] for x in day):+,.0f}円）")
    n, y = hab["after_loss"]
    if ans.get("revenge_urge") == "ならない" and n:
        lines.append(f"- 負けた後すぐ取り返したく「ならない」→ 記録では負けて30分以内に入った取引が {n}回（{y:+,.0f}円）")
    return lines


# ════════════════════ 出力 ════════════════════

def _f(v, d=2):
    return "—" if v is None else f"{v:+.{d}f}"


def _span(m):
    return f"{int(m // 1440)}日" if m >= 1440 and m % 1440 == 0 else f"{int(m // 60)}時間" if m >= 60 else f"{int(m)}分"


def render(meta, res, slots, classes, hab, prof_lines):
    kind = meta["kind"]
    unit = "1日のふつうの値動き（ATR）の何倍か" if kind == "atr" else "入った値段の1万分のいくつか（bp）"
    L = ["# 投資スタイル診断（自分の取引記録から）", "",
         f"作成: {meta['generated_at']}／記録: {meta['first']}〜{meta['last']}（{meta['n']}回）／"
         f"純損益 {meta['net_yen']:+,.0f}円（手数料・スワップ {meta['cost_yen']:+,.0f}円を含む）",
         f"- 口座の決済損益との照合: {meta['check']}",
         f"- 物差し＝1回の損益を「{unit}」で表したもの（費用込み・ロットの大きさに左右されない）",
         f"- 環境の確認: {meta['env']}", "",
         "## スタイルの判定", "",
         "| スタイル（保有時間） | 回数 | 勝率 | 純損益 | 平均 | 95%の幅 | 大勝ち除く | 判定 | 理由 |",
         "|---|---:|---:|---:|---:|---|---:|---|---|"]
    for n, a, b in STYLES:
        r = res[n]
        span = _span(a) + "〜" + ("" if b == math.inf else _span(b))
        win = "—" if r["win"] is None else f"{r['win']:.0%}"
        L.append(f"| {n}（{span}） | {r['n']} | {win} | "
                 f"{r['net_yen']:+,.0f}円 | {_f(r.get('mean'))} | {_f(r.get('lo'))}〜{_f(r.get('hi'))} | {_f(r.get('mean_wo_top'))} | "
                 f"{r['verdict']} | {'・'.join(r['why'])} |")
    L += ["", "判定の決まり（固定）：", f"- ◯ 合っている＝{MIN_N}回以上・平均がプラス・95%の幅がまるごと0より上・大きい勝ち{TOP_DROP}回を除いてもプラス・"
          f"記録の前半と後半のどちらもプラス・値動きの大きさ（小さい／ふつう／大きい）と流れの向き（沿う／逆らう）のどの区分でもプラス（{MIN_N_CELL}回以上の区分だけ見る）",
          "- △＝平均はプラスだが上のどれかを満たさない（理由の欄）／▽＝平均がマイナス／✕＝95%の幅がまるごと0より下／？＝回数が足りない", "",
          "## 環境が変わっても同じか（平均。かっこ内は回数）", "",
          "| スタイル | 前半 | 後半 | 値動き小さい | ふつう | 大きい | 流れに沿う | 流れに逆らう |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for n, _, _ in STYLES:
        r = res[n]
        cells = [f"{_f(m)}（{k}）" for _, k, m in r["halves"] + r["cells"]]
        L.append(f"| {n} | " + " | ".join(cells) + " |")
    for title, tab, labels in (("入った時間帯（日本時間）", slots, SLOTS), ("銘柄の種類", classes, CLASSES)):
        L += ["", f"## {title} × スタイル（回数・純損益）", "", "| | " + " | ".join(n for n, _, _ in STYLES) + " |",
              "|---|" + "---:|" * len(STYLES)]
        for lab in labels:
            if not any(tab[(lab, s)][0] for s, _, _ in STYLES):
                continue
            L.append(f"| {lab} | " + " | ".join(f"{tab[(lab, s)][0]}回 {tab[(lab, s)][1]:+,.0f}円" for s, _, _ in STYLES) + " |")
    L += ["", "## 参考（判定には使わない）", "",
          f"- 負けて閉じてから30分以内に入った取引：{hab['after_loss'][0]}回・{hab['after_loss'][1]:+,.0f}円",
          f"- 1日に4回以上入った日の取引：{hab['busy_days'][0]}回・{hab['busy_days'][1]:+,.0f}円"]
    if prof_lines:
        L += ["", "## 自己申告と記録の食い違い", ""] + prof_lines
    L += ["", "---", "", "※ 自分の過去の取引記録の集計です。投資助言ではありません。これからの成績を約束するものではありません。"]
    return "\n".join(L) + "\n"


def run(path, server_tz="ny+7", market=True, profile=None, out_dir=OUT_DIR, fetch=fetch_daily, now=None):
    trades, closed_pl = parse_statement(read_text(path), server_tz)
    if not trades:
        raise SystemExit("決済済みの取引が見つかりません（MT4 の口座履歴の「レポートの保存」で出したファイルか確かめてください）")
    missing = attach_market(trades, fetch) if market else []
    cover = np.mean([x.get("atr") is not None for x in trades]) if market else 0.0
    kind = "atr" if cover >= ATR_COVERAGE else "bp"
    env_checked = bool(market and cover >= ATR_COVERAGE)
    res = diagnose(trades, kind, env_checked)
    net = sum(x["net"] for x in trades)
    meta = {"generated_at": (now or dt.datetime.now(JST)).isoformat(timespec="minutes"), "n": len(trades),
            "first": trades[0]["open"].date().isoformat(), "last": trades[-1]["open"].date().isoformat(),
            "net_yen": net, "cost_yen": sum(x["cost"] for x in trades), "kind": kind,
            "check": "口座の数字が見つからない" if closed_pl is None else
            ("一致" if abs(closed_pl - net) < 1 else f"不一致（口座 {closed_pl:+,.0f}円／集計 {net:+,.0f}円）"),
            "env": ("未確認（--no-market）" if not market else
                    f"値段を取れた取引 {cover:.0%}" + (f"・取れなかった銘柄 {', '.join(missing)}" if missing else "") +
                    ("" if env_checked else f"（{ATR_COVERAGE:.0%}未満のため未確認扱い）"))}
    hab = habits(trades)
    ans = None
    if profile and os.path.exists(profile):
        with open(profile, encoding="utf-8") as fh:
            ans = (json.load(fh) or {}).get("answers")
    md = render(meta, res, cross(trades, slot_of, SLOTS, kind), cross(trades, lambda x: class_of(x["sym"]), CLASSES, kind),
                hab, compare_profile(ans, res, trades, hab))
    os.makedirs(out_dir, exist_ok=True)
    stamp = (now or dt.datetime.now(JST)).strftime("%Y%m%d")
    with open(os.path.join(out_dir, f"report-{stamp}.md"), "w", encoding="utf-8") as fh:
        fh.write(md)
    with open(os.path.join(out_dir, f"result-{stamp}.json"), "w", encoding="utf-8") as fh:
        json.dump({"meta": meta, "styles": res, "habits": hab}, fh, ensure_ascii=False, indent=1, default=str)
    return md, res, meta


def main(argv=None):
    ap = argparse.ArgumentParser(description="投資スタイル診断（MT4 の口座履歴から）")
    ap.add_argument("statement", nargs="?")
    ap.add_argument("--server-tz", default="ny+7")
    ap.add_argument("--no-market", action="store_true")
    ap.add_argument("--profile", default=os.path.join(OUT_DIR, "profile.json"))
    ap.add_argument("--out", default=OUT_DIR)
    ap.add_argument("--init-profile", action="store_true")
    a = ap.parse_args(argv)
    if a.init_profile:
        os.makedirs(os.path.dirname(a.profile) or ".", exist_ok=True)
        if os.path.exists(a.profile):
            print(f"すでにあります（上書きしない）: {a.profile}")
            return 0
        with open(a.profile, "w", encoding="utf-8") as fh:
            json.dump(PROFILE_TEMPLATE, fh, ensure_ascii=False, indent=1)
        print(f"作りました: {a.profile}（answers を書き換えてから、もう一度診断を実行してください）")
        return 0
    if not a.statement:
        ap.error("MT4 の口座履歴のファイルを指定してください（例: research/Statement.htm）")
    md, _, _ = run(a.statement, a.server_tz, not a.no_market, a.profile, a.out)
    print(md)
    print(f"保存先: {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
