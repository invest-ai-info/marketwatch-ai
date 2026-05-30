# -*- coding: utf-8 -*-
"""週次ゾーン分析用：監視18銘柄のテクニカル水準を weekly-levels.json に出力。
ゾーン推定（支持/抵抗）の素材＝現値・MA・ATR・高安・月次レンジ。価格データは yfinance。
週次 routine（weekly-zone-plan）から呼ばれる。ローカル/CCR どちらでも動くよう cert 回避を内蔵。"""
import os, json, sys, warnings
try:
    import certifi
    os.environ.setdefault("CURL_CA_BUNDLE", certifi.where())
    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
    os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())
except Exception:
    pass
warnings.filterwarnings("ignore")
import pandas as pd
import yfinance as yf

# (表示名, yfinanceティッカー, 小数桁)
INSTRUMENTS = [
    ("金", "GC=F", 1), ("銀", "SI=F", 2), ("原油WTI", "CL=F", 2),
    ("日経225", "NKD=F", 0), ("S&P500", "ES=F", 1), ("ナスダック", "NQ=F", 1),
    ("ダウ", "YM=F", 0), ("英FTSE", "^FTSE", 1), ("ビットコイン", "BTC-USD", 0),
    ("ドル円", "USDJPY=X", 2), ("ユーロ円", "EURJPY=X", 2), ("ポンド円", "GBPJPY=X", 2),
    ("豪ドル円", "AUDJPY=X", 2), ("ユーロドル", "EURUSD=X", 4), ("ポンドドル", "GBPUSD=X", 4),
    ("豪ドルドル", "AUDUSD=X", 4), ("ユーロ豪ドル", "EURAUD=X", 4), ("ポンド豪ドル", "GBPAUD=X", 4),
]


def flat(d):
    if d is None or len(d) == 0:
        return pd.DataFrame()
    if isinstance(d.columns, pd.MultiIndex):
        d.columns = d.columns.get_level_values(0)
    return d


def fetch(tk):
    try:
        d = flat(yf.download(tk, period="2y", interval="1d", progress=False, auto_adjust=True))
        if "Close" in d and len(d) > 60:
            return d.dropna(subset=["Close"])
    except Exception:
        pass
    try:
        from curl_cffi import requests as creq
        s = creq.Session(impersonate="chrome", verify=False)
        d = flat(yf.Ticker(tk, session=s).history(period="2y", interval="1d", auto_adjust=True))
        if "Close" in d and len(d) > 60:
            return d.dropna(subset=["Close"])
    except Exception:
        pass
    return pd.DataFrame()


def levels(d, dec):
    c, h, l = d["Close"], d["High"], d["Low"]
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    r = lambda x: round(float(x), dec)
    out = {
        "price": r(c.iloc[-1]),
        "ma20": r(c.rolling(20).mean().iloc[-1]),
        "ma50": r(c.rolling(50).mean().iloc[-1]),
        "ma200": r(c.rolling(200).mean().iloc[-1]) if len(c) >= 200 else None,
        "atr14": r(tr.ewm(alpha=1/14, adjust=False).mean().iloc[-1]),
        "hi120": r(h.tail(120).max()), "lo120": r(l.tail(120).min()),
        "hi250": r(h.tail(250).max()), "lo250": r(l.tail(250).min()),
        "monthly": [],
    }
    m = d.resample("ME").agg({"Low": "min", "High": "max", "Close": "last"}).tail(12)
    for idx, row in m.iterrows():
        out["monthly"].append({"m": idx.strftime("%Y-%m"), "lo": r(row["Low"]), "hi": r(row["High"]), "cl": r(row["Close"])})
    return out


def main():
    result = {"instruments": []}
    ok = 0
    for name, tk, dec in INSTRUMENTS:
        d = fetch(tk)
        if len(d) == 0:
            result["instruments"].append({"name": name, "ticker": tk, "error": "no_data"})
            print(f"  ⚠️ {name} ({tk}) データ取得失敗", file=sys.stderr)
            continue
        result["instruments"].append({"name": name, "ticker": tk, **levels(d, dec)})
        ok += 1
        print(f"  ✅ {name} ({tk}) price={result['instruments'][-1]['price']}", file=sys.stderr)
    with open("weekly-levels.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"weekly-levels.json 出力: {ok}/{len(INSTRUMENTS)} 銘柄成功", file=sys.stderr)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
