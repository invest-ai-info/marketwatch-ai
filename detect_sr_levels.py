# -*- coding: utf-8 -*-
"""
実価格データから 水平サポート/レジスタンス と 簡易トレンドライン を自動検出する。
手法: スイングピボット(局所高安) → 近接レベルをクラスタリング(タッチ回数=強さ) → 現値からの距離。
データ: Yahoo Finance chart API を直接取得（yfinanceライブラリは現在Yahooにブロックされるため不使用）。
使い方:
  python detect_sr_levels.py GC=F USDJPY=X        # ティッカー直接（ライブ取得）
  python detect_sr_levels.py _sr_USDJPY.csv        # ローカルCSV(Date,Open,High,Low,Close)
  python detect_sr_levels.py                       # 既定の主要銘柄
※ これは検出ツール。実トレード採用には別途バックテストが必要（popular だから効くとは限らない）。
"""
import sys, os, csv, json, urllib.request, urllib.parse
import numpy as np

try:  # Windows の cp932 コンソールでも絵文字/矢印で落ちないよう UTF-8 を強制
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

K = 3            # スイング判定の左右本数（局所高安）
TOL = 0.006      # クラスタ許容幅（0.6%）
MIN_TOUCH = 2    # S/Rとみなす最小タッチ回数
DEFAULT = ["USDJPY=X", "GBPJPY=X", "NKD=F", "GC=F", "BTC-USD"]

def fetch_yahoo(ticker, rng="9mo"):
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/"
           + urllib.parse.quote(ticker) + f"?range={rng}&interval=1d")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    d = json.load(urllib.request.urlopen(req, timeout=25))
    r = d["chart"]["result"][0]
    q = r["indicators"]["quote"][0]
    H, L, C = [], [], []
    for h, l, c in zip(q["high"], q["low"], q["close"]):
        if h is not None and l is not None and c is not None:
            H.append(float(h)); L.append(float(l)); C.append(float(c))
    return np.array(H[-180:]), np.array(L[-180:]), np.array(C[-180:])

def load_csv(path):
    H, L, C = [], [], []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                H.append(float(row["High"])); L.append(float(row["Low"])); C.append(float(row["Close"]))
            except (ValueError, KeyError):
                continue
    return np.array(H[-180:]), np.array(L[-180:]), np.array(C[-180:])

def swings(highs, lows, k=K):
    sh, sl = [], []
    for i in range(k, len(highs)-k):
        if highs[i] == max(highs[i-k:i+k+1]): sh.append((i, highs[i]))
        if lows[i]  == min(lows[i-k:i+k+1]):  sl.append((i, lows[i]))
    return sh, sl

def cluster(levels, tol=TOL):
    if not levels: return []
    pts = sorted(levels, key=lambda x: x[1])
    zones, cur = [], [pts[0]]
    for idx, p in pts[1:]:
        if abs(p - cur[-1][1]) / cur[-1][1] <= tol:
            cur.append((idx, p))
        else:
            zones.append(cur); cur = [(idx, p)]
    zones.append(cur)
    out = []
    for z in zones:
        prices = [p for _, p in z]
        out.append({"price": float(np.mean(prices)), "touches": len(z),
                    "last_idx": max(i for i, _ in z)})
    return out

def trendline(sw, n=4):
    if len(sw) < 2: return None
    pts = sw[-n:]
    xs = np.array([i for i, _ in pts], float)
    ys = np.array([p for _, p in pts], float)
    a, b = np.polyfit(xs, ys, 1)
    return {"value_now": float(a*xs[-1] + b), "rising": a > 0, "n": len(pts)}

def analyze(src):
    label = os.path.splitext(os.path.basename(src))[0] if src.endswith(".csv") else src
    print(f"\n===== {label} =====")
    try:
        highs, lows, C = load_csv(src) if src.endswith(".csv") else fetch_yahoo(src)
    except Exception as e:
        print("  取得失敗:", e); return
    if len(C) < 40:
        print("  データ不足"); return
    close = float(C[-1]); n = len(C)
    sh, sl = swings(highs, lows)
    zones = [z for z in cluster([(i, p) for i, p in sh] + [(i, p) for i, p in sl]) if z["touches"] >= MIN_TOUCH]
    zones.sort(key=lambda z: (z["touches"], z["last_idx"]), reverse=True)
    dec = 2 if close < 1000 else (1 if close < 100000 else 0)
    print(f"  現値: {close:.{dec}f}  （日足{n}本・スイング高{len(sh)}/安{len(sl)}）")
    res = sorted([z for z in zones if z["price"] > close], key=lambda z: z["price"])
    sup = sorted([z for z in zones if z["price"] < close], key=lambda z: z["price"], reverse=True)
    print("  ▼ 主要レジスタンス（上）  ※★=タッチ回数=強さ")
    for z in res[:3][::-1]:
        print(f"      {z['price']:.{dec}f}  {'★'*min(z['touches'],6)} ({z['touches']}タッチ, +{(z['price']-close)/close*100:.1f}%)")
    print(f"  ── 現値 {close:.{dec}f} ──")
    print("  ▲ 主要サポート（下）")
    for z in sup[:3]:
        print(f"      {z['price']:.{dec}f}  {'★'*min(z['touches'],6)} ({z['touches']}タッチ, -{(close-z['price'])/close*100:.1f}%)")
    up, dn = trendline(sl), trendline(sh)
    print("  ◇ 簡易トレンドライン（近似・直近スイング直線フィット。あくまで補助）")
    if up: print(f"      安値ライン: 現在値 {up['value_now']:.{dec}f} / {'上向き↗' if up['rising'] else '下向き↘'}")
    if dn: print(f"      高値ライン: 現在値 {dn['value_now']:.{dec}f} / {'上向き↗' if dn['rising'] else '下向き↘'}")

if __name__ == "__main__":
    args = sys.argv[1:] or DEFAULT
    for a in args:
        analyze(a)
    print("\n※ 検出ツール。実トレード採用には backtest が必要（popular だから効くとは限らない）。")
