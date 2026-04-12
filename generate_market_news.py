"""
æ¯æãã¼ã±ãããã¥ã¼ã¹èªåçæã¹ã¯ãªããï¼æ­´å²çã¤ãã³ãå¹´è¡¨ä»ãï¼
yfinance ã§ä¾¡æ ¼ãã¼ã¿åå¾ãChart.js ã§ãã£ã¼ãè¡¨ç¤º
"""

import yfinance as yf
import json
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))

# âââââââââââââââââââââââââââââââââââââââââ
# æ­´å²çã¤ãã³ããã¼ã¿ï¼1971ãï¼
# âââââââââââââââââââââââââââââââââââââââââ
HISTORICAL_EVENTS = [
    {"date": "1971-08", "label": "ãã¯ã½ã³ã·ã§ãã¯",       "desc": "ç±³ãã«ã¨éã®åæåæ­¢ãå¤åç¸å ´å¶ã¸ç§»è¡ããã«åãæ¥è½ã360åå°ãã100åå°ã¸ã®é·æåé«ãå§ã¾ã£ãã",           "assets": ["usdjpy", "gold"]},
    {"date": "1973-11", "label": "ç¬¬ä¸æ¬¡ãªã¤ã«ã·ã§ãã¯",   "desc": "OAPECåæ²¹ç¦è¼¸ãåæ²¹ä¾¡æ ¼ãç´4åã«æ¥é¨°ãä¸ççã¤ã³ãã¬ã¨æ ªå®ãå¼ãèµ·ãããã",                            "assets": ["nikkei", "sp500", "gold"]},
    {"date": "1979-02", "label": "ç¬¬äºæ¬¡ãªã¤ã«ã·ã§ãã¯",   "desc": "ã¤ã©ã³é©å½ã§åæ²¹ä¾çµ¦ãæ¿æ¸ãåæ²¹ä¾¡æ ¼ãåã³æ¥é¨°ãä¸ççµæ¸ãç´æããã",                                   "assets": ["nikkei", "sp500", "gold"]},
    {"date": "1985-09", "label": "ãã©ã¶åæ",             "desc": "G5ããã«é«æ¯æ­£ã§åæããã«åã240åå°ãã120åå°ã¸ã¨æ¥è½ããå¤§è¦æ¨¡ãªåé«ãé²è¡ããã",                    "assets": ["usdjpy", "nikkei"]},
    {"date": "1987-10", "label": "ãã©ãã¯ãã³ãã¼",       "desc": "ãã¥ã¼ã¨ã¼ã¯æ ªå¼å¸å ´ã§1æ¥ã«22.6%ã®æ´è½ãä¸çåææ ªå®ã¨ãªãæ¥çµå¹³åãç¿æ¥ç´15%ä¸è½ããã",               "assets": ["nikkei", "sp500"]},
    {"date": "1990-01", "label": "æ¥æ¬ããã«å´©å£",         "desc": "æ¥çµå¹³åã38,915åã®ãã¼ã¯ããæ¥è½éå§ãå¤±ããã30å¹´ã®å§ã¾ãã¨ãªã£ãæ­´å²çãªå¤§æ´è½ã",                    "assets": ["nikkei"]},
    {"date": "1995-01", "label": "éªç¥å¤§éç½ã»åé«",       "desc": "éªç¥æ·¡è·¯å¤§éç½å¾ã«åãæ¥é¨°ã1ãã«=79åå°ã®å²ä¸æé«å¤ãè¨é²ãæ¥çµå¹³åãæ¥è½ããã",                        "assets": ["nikkei", "usdjpy"]},
    {"date": "1997-07", "label": "ã¢ã¸ã¢éè²¨å±æ©",         "desc": "ã¿ã¤ãã¼ãæ´è½ããå§ã¾ã£ãã¢ã¸ã¢éè²¨å±æ©ãæ¥æ¬ã®éèæ©é¢ã«ãæ³¢åãå±±ä¸è¨¼å¸ãªã©ç¸æ¬¡ãã§ç ´ç¶»ããã",          "assets": ["nikkei", "usdjpy"]},
    {"date": "1998-08", "label": "ã­ã·ã¢è²¡æ¿å±æ©/LTCM",   "desc": "ã­ã·ã¢ãããã©ã«ãå®£è¨ãããã¸ãã¡ã³ãLTCMç ´ç¶»ãä¸ççãªä¿¡ç¨åç¸®ã¨ãã«å®ã»åé«ãå éããã",              "assets": ["nikkei", "sp500", "usdjpy"]},
    {"date": "2000-03", "label": "ITããã«å´©å£",           "desc": "NASDAQã5,048ã®æé«å¤ããæ¥è½ãITããã«ãå´©å£ã2002å¹´ã¾ã§ä¸ççãªæ ªå®ãç¶ããã",                       "assets": ["nikkei", "sp500"]},
    {"date": "2001-09", "label": "9.11ãã­",               "desc": "ç±³åæå¤çºãã­ããã¥ã¼ã¨ã¼ã¯å¸å ´ã1é±éééãåéå¾ã«æ ªä¾¡ãæ¥è½ãéãå®å¨è³ç£ã¨ãã¦è²·ãããã",            "assets": ["nikkei", "sp500", "gold"]},
    {"date": "2003-03", "label": "ã¤ã©ã¯æ¦äº",             "desc": "ç±³è±è»ãã¤ã©ã¯ä¾µæ»ãéå§ãå°æ¿å­¦ãªã¹ã¯ãé«ã¾ãåæ²¹ã»éä¾¡æ ¼ãä¹±é«ä¸ããã",                               "assets": ["gold", "nikkei"]},
    {"date": "2008-09", "label": "ãªã¼ãã³ã·ã§ãã¯",       "desc": "ãªã¼ãã³ã»ãã©ã¶ã¼ãºçµå¶ç ´ç¶»ã§ä¸çéèå±æ©ãåçºãæ¥çµå¹³åã¯ãã¼ã¯ããç´60%ãS&P500ã¯ç´57%ä¸è½ããã",   "assets": ["nikkei", "sp500", "usdjpy", "gold"]},
    {"date": "2010-05", "label": "æ¬§å·åµåå±æ©",           "desc": "ã®ãªã·ã£è²¡æ¿å±æ©ãæ¬§å·å¨ä½ã«æ³¢åãã¦ã¼ã­ãæ¥è½ãä¸ççãªãªã¹ã¯ãªãã®åããå¼·ã¾ã£ãã",                    "assets": ["nikkei", "sp500", "gold"]},
    {"date": "2011-03", "label": "æ±æ¥æ¬å¤§éç½",           "desc": "æ±æ¥æ¬å¤§éç½ã»ç¦å³¶åçºäºæãæ¥çµå¹³åãç´20%æ¥è½ãåãæ¥é¨°ãä¸æ1ãã«=76åå°ã®è¶åé«ãè¨é²ããã",        "assets": ["nikkei", "usdjpy"]},
    {"date": "2013-04", "label": "ã¢ãããã¯ã¹/ç°æ¬¡åç·©å","desc": "æ¥éãç°æ¬¡åéèç·©åãçºè¡¨ãåå®ã»æ ªé«ãä¸æ°ã«å éãæ¥çµå¹³åã¯ç´2å¹´ã§åå¢ããã",                        "assets": ["nikkei", "usdjpy"]},
    {"date": "2015-08", "label": "ãã£ã¤ãã·ã§ãã¯",       "desc": "ä¸­å½æ ªå¼å¸å ´ã®æ¥è½ãä¸çã«æ³¢åãVIXææ°ãæ¥é¨°ãæ¥çµå¹³åã¯1é±éã§ç´11%ä¸è½ããã",                        "assets": ["nikkei", "sp500"]},
    {"date": "2016-06", "label": "Brexitå½æ°æç¥¨",         "desc": "è±å½ãEUé¢è±ãæ±ºå®ããã³ããæ¥è½ãä¸çæ ªå®ã»åé«ãé²è¡ãå¸å ´ã®æ³å®å¤ã®çµæã«è¡æãèµ°ã£ãã",             "assets": ["nikkei", "sp500", "gold"]},
    {"date": "2016-11", "label": "ãã©ã³ãå¤§çµ±é å½é¸",     "desc": "ãã©ã³ãå½é¸å¾ã«ããã©ã³ãã©ãªã¼ããçºçãç±³æ ªã»ãã«é«ã»æ¥æ¬æ ªãå¤§ããä¸æããã",                        "assets": ["nikkei", "sp500", "usdjpy"]},
    {"date": "2018-12", "label": "ç±³ä¸­è²¿ææ¦äº",           "desc": "ç±³ä¸­è²¿ææ©æ¦ãæ¿åãS&P500ãå¹´æ«ã«ããã¦ç´20%æ¥è½ãä¸çã®æ ªå¼å¸å ´ãåæºããã",                          "assets": ["nikkei", "sp500"]},
    {"date": "2020-02", "label": "ã³ã­ãã·ã§ãã¯",         "desc": "æ°åã³ã­ããã³ãããã¯å®£è¨ãä¸çã®æ ªå¼å¸å ´ãç´1ã¶æã§30ã40%æ¥è½ãå²ä¸æéã®å¼±æ°ç¸å ´å¥ãã¨ãªã£ãã",      "assets": ["nikkei", "sp500", "usdjpy", "gold"]},
    {"date": "2022-02", "label": "ã­ã·ã¢ã»ã¦ã¯ã©ã¤ãä¾µæ»", "desc": "ã­ã·ã¢ãã¦ã¯ã©ã¤ãã«è»äºä¾µæ»ãåæ²¹ã»å¤©ç¶ã¬ã¹ã»éä¾¡æ ¼ãæ¥é¨°ãä¸ççãªã¤ã³ãã¬å éã®å¼ãéã¨ãªã£ãã",       "assets": ["nikkei", "sp500", "gold"]},
    {"date": "2022-03", "label": "FRBæ¥éå©ä¸ãéå§",     "desc": "FRBãã¼ã­éå©æ¿ç­ãçµäºãæ¥éãªå©ä¸ããéå§ãåµå¸ã»æ ªå¼ãåæä¸è½ãåã¯å¯¾ãã«ã§30å¹´ã¶ãã®åå®ã«ã",      "assets": ["nikkei", "sp500", "usdjpy", "gold"]},
    {"date": "2023-03", "label": "SVBç ´ç¶»",               "desc": "ã·ãªã³ã³ãã¬ã¼ãã³ã¯ç ´ç¶»ãç±³å°éã¸ã®ä¿¡ç¨ä¸å®ãæ¡å¤§ãéãå®å¨è³ç£ã¨ãã¦æ¥é¨°ããã",                        "assets": ["nikkei", "sp500", "gold"]},
    {"date": "2024-08", "label": "æ¥çµå¹³åæ­´å²çæ´è½",     "desc": "æ¥çµå¹³åã1æ¥ã§-4,451åï¼-12.4%ï¼ã®æ­´å²çæ´è½ãåã­ã£ãªã¼ãã¬ã¼ãå·»ãæ»ãã§åãæ¥é¨°ããã",              "assets": ["nikkei", "usdjpy"]},
]

# âââââââââââââââââââââââââââââââââââââââââ
# ãã¼ã¿åå¾é¢æ°
# âââââââââââââââââââââââââââââââââââââââââ
def get_price(ticker_symbol):
    try:
        t = yf.Ticker(ticker_symbol)
        hist = t.history(period="2d")
        if len(hist) < 2:
            return None, None, None
        prev = hist["Close"].iloc[-2]
        last = hist["Close"].iloc[-1]
        return last, prev, (last - prev) / prev * 100
    except Exception:
        return None, None, None

def get_historical_monthly(ticker, start="1975-01-01"):
    try:
        t = yf.Ticker(ticker)
        hist = t.history(start=start)
        if hist.empty:
            return [], []
        yearly = hist["Close"].resample("YE").last().dropna()
        dates  = [d.strftime("%Y") for d in yearly.index]
        prices = [round(float(v), 2) for v in yearly.values]
        return dates, prices
    except Exception:
        return [], []

def fmt_price(val, decimals=2, prefix="", suffix=""):
    if val is None:
        return "N/A"
    return f"{prefix}{val:,.{decimals}f}{suffix}"

def fmt_change(pct):
    if pct is None:
        return ""
    sign = "â²" if pct >= 0 else "â¼"
    cls  = "up" if pct >= 0 else "down"
    return f'<span class="{cls} price-change">{sign}{abs(pct):.2f}%</span>'

def sentiment(changes):
    ups   = sum(1 for c in changes if c and c > 0)
    downs = sum(1 for c in changes if c and c < 0)
    if ups > downs:
        return "ããå¼·æ°", "#238636", "ð"
    elif downs > ups:
        return "ããå¼±æ°", "#da3633", "ð"
    return "ä¸­ç«", "#9e6a03", "â¡ï¸"

def build_annotations(asset_key, dates):
    """æå®ã¢ã»ããã«é¢ããã¤ãã³ãã®Chart.jsã¢ããã¼ã·ã§ã³ãçæ"""
    anns = {}
    date_set = set(dates)
    for i, ev in enumerate(HISTORICAL_EVENTS):
        if asset_key not in ev["assets"]:
            continue
        # ææ¬¡ãã¼ã¿ã«å«ã¾ããæè¿ã®æãæ¢ã
        ev_date = ev["date"]
        # å¯¾å¿ããæãããä»¥éã®æåã®æãæ¢ã
        target = next((d for d in dates if d >= ev_date), None)
        if target is None:
            continue
        key = f"ev{i}"
        anns[key] = {
            "type": "line",
            "xMin": target,
            "xMax": target,
            "borderColor": "rgba(255, 193, 7, 0.7)",
            "borderWidth": 1.5,
            "borderDash": [4, 3],
            "label": {
                "content": ev["label"],
                "display": False,
                "backgroundColor": "rgba(30,30,40,0.95)",
                "color": "#ffd700",
                "font": {"size": 11},
                "padding": 6,
                "position": "start",
            },
            "enter": {"label": {"display": True}},
            "leave": {"label": {"display": False}},
        }
    return anns

# âââââââââââââââââââââââââââââââââââââââââ
# HTMLçæ
# âââââââââââââââââââââââââââââââââââââââââ
def build_html(data, hist, now_jst):
    date_str = now_jst.strftime("%Yå¹´%-mæ%-dæ¥")
    time_str = now_jst.strftime("%Yå¹´%-mæ%-dæ¥ %H:%M JST")

    nk,  _, nk_chg  = data["nikkei"]
    sp,  _, sp_chg  = data["sp500"]
    fx,  _, fx_chg  = data["usdjpy"]
    efx, _, efx_chg = data["eurjpy"]
    oil, _, oil_chg = data["oil"]
    gld, _, gld_chg = data["gold"]
    btc, _, btc_chg = data["btc"]
    eth, _, eth_chg = data["eth"]

    label, badge_color, emoji = sentiment([nk_chg, sp_chg, btc_chg, gld_chg])

    # æ­´å²ãã£ã¼ããã¼ã¿ãJSONå
    nk_dates,  nk_prices  = hist["nikkei"]
    sp_dates,  sp_prices  = hist["sp500"]
    fx_dates,  fx_prices  = hist["usdjpy"]
    gld_dates, gld_prices = hist["gold"]

    # ã¢ããã¼ã·ã§ã³
    nk_ann  = json.dumps(build_annotations("nikkei", nk_dates),  ensure_ascii=False)
    sp_ann  = json.dumps(build_annotations("sp500",  sp_dates),  ensure_ascii=False)
    fx_ann  = json.dumps(build_annotations("usdjpy", fx_dates),  ensure_ascii=False)
    gld_ann = json.dumps(build_annotations("gold",   gld_dates), ensure_ascii=False)

    # ã¤ãã³ãä¸è¦§ãã¼ãã«è¡ãçæ
    event_rows = ""
    for ev in sorted(HISTORICAL_EVENTS, key=lambda x: x["date"], reverse=True):
        asset_badges = ""
        map_ = {"nikkei": "æ¥çµ", "sp500": "S&P", "usdjpy": "ãã«å", "gold": "é"}
        for a in ev["assets"]:
            asset_badges += f'<span class="badge">{map_.get(a, a)}</span>'
        event_rows += f"""
        <tr>
          <td class="ev-date">{ev["date"]}</td>
          <td class="ev-label">{ev["label"]}</td>
          <td>{asset_badges}</td>
          <td class="ev-desc">{ev["desc"]}</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ãã¼ã±ãããã¥ã¼ã¹ - {date_str}</title>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/chartjs-plugin-annotation/3.0.1/chartjs-plugin-annotation.min.js"></script>
  <style>
    *{{margin:0;padding:0;box-sizing:border-box}}
    body{{font-family:'Segoe UI','Hiragino Sans','Yu Gothic',sans-serif;background:#0d1117;color:#e6edf3;min-height:100vh}}
    header{{background:linear-gradient(135deg,#161b22,#1c2128);border-bottom:1px solid #30363d;padding:24px 32px}}
    .header-inner{{max-width:1200px;margin:0 auto;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px}}
    .header-title{{font-size:1.6rem;font-weight:700;background:linear-gradient(90deg,#58a6ff,#79c0ff);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}
    .header-meta{{font-size:.85rem;color:#8b949e}}
    .header-meta span{{color:#58a6ff;font-weight:600}}
    main{{max-width:1200px;margin:0 auto;padding:32px 24px}}
    .sentiment-banner{{background:linear-gradient(135deg,#1c2f1c,#162416);border:1px solid #2ea043;border-radius:12px;padding:20px 28px;margin-bottom:32px;display:flex;align-items:center;gap:16px;flex-wrap:wrap}}
    .sentiment-badge{{color:#fff;font-weight:700;font-size:.9rem;padding:6px 16px;border-radius:20px;white-space:nowrap;background:{badge_color}}}
    .sentiment-text{{color:#7ee787;font-size:.95rem;line-height:1.6}}
    .section-title{{font-size:1.1rem;font-weight:600;color:#8b949e;text-transform:uppercase;letter-spacing:.08em;margin-bottom:16px}}
    .cards-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:20px;margin-bottom:40px}}
    .card{{background:#161b22;border:1px solid #30363d;border-radius:12px;padding:20px;transition:border-color .2s}}
    .card:hover{{border-color:#58a6ff}}
    .card-header{{display:flex;align-items:center;gap:10px;margin-bottom:14px}}
    .card-icon{{width:36px;height:36px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:1.1rem}}
    .icon-stocks{{background:#1a3a5c}}.icon-fx{{background:#3a2a1a}}.icon-cmd{{background:#2a1a3a}}.icon-crypto{{background:#1a3a2a}}
    .card-title{{font-weight:700;font-size:1rem;color:#e6edf3}}
    .card-subtitle{{font-size:.75rem;color:#8b949e}}
    .price-row{{display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid #21262d}}
    .price-row:last-of-type{{border-bottom:none}}
    .price-label{{font-size:.85rem;color:#8b949e}}
    .price-value{{font-size:.95rem;font-weight:600;color:#e6edf3}}
    .price-change{{font-size:.8rem;margin-left:4px}}
    .up{{color:#3fb950}}.down{{color:#f85149}}
    .card-summary{{margin-top:14px;padding-top:14px;border-top:1px solid #21262d;font-size:.82rem;color:#8b949e;line-height:1.65}}
    /* ãã£ã¼ãã»ã¯ã·ã§ã³ */
    .chart-section{{background:#161b22;border:1px solid #30363d;border-radius:12px;padding:24px;margin-bottom:24px}}
    .chart-title{{font-size:1rem;font-weight:700;color:#e6edf3;margin-bottom:4px}}
    .chart-subtitle{{font-size:.78rem;color:#8b949e;margin-bottom:16px}}
    .chart-hint{{font-size:.75rem;color:#ffd700;margin-bottom:12px}}
    .chart-wrap{{position:relative;height:280px}}
    /* ã¤ãã³ããã¼ãã« */
    .event-section{{background:#161b22;border:1px solid #30363d;border-radius:12px;padding:24px;margin-bottom:32px;overflow-x:auto}}
    table{{width:100%;border-collapse:collapse;font-size:.83rem}}
    th{{text-align:left;padding:10px 12px;border-bottom:2px solid #30363d;color:#8b949e;font-weight:600;white-space:nowrap}}
    td{{padding:10px 12px;border-bottom:1px solid #21262d;vertical-align:top;line-height:1.5}}
    tr:hover td{{background:#1c2128}}
    .ev-date{{color:#58a6ff;white-space:nowrap;font-weight:600}}
    .ev-label{{font-weight:700;color:#e6edf3;white-space:nowrap}}
    .ev-desc{{color:#8b949e;font-size:.8rem}}
    .badge{{display:inline-block;background:#21262d;color:#79c0ff;border:1px solid #30363d;border-radius:4px;padding:2px 6px;font-size:.72rem;margin:2px 2px 2px 0;white-space:nowrap}}
    footer{{background:#161b22;border-top:1px solid #30363d;padding:20px 32px;text-align:center;font-size:.78rem;color:#6e7681}}
    footer a{{color:#58a6ff;text-decoration:none}}
    @media(max-width:600px){{.header-inner{{flex-direction:column}}.sentiment-banner{{flex-direction:column}}}}
  </style>
</head>
<body>
<header>
  <div class="header-inner">
    <div>
      <div class="header-title">ð ãã¼ã±ãããã¥ã¼ã¹</div>
      <div class="header-meta">æçµæ´æ°: <span>{time_str}</span></div>
    </div>
    <div class="header-meta">GitHub Actions èªåæ´æ°</div>
  </div>
</header>
<main>

  <!-- ã»ã³ãã¡ã³ã -->
  <div class="sentiment-banner">
    <div class="sentiment-badge">{emoji} {label}</div>
    <div class="sentiment-text">
      æ¥çµå¹³å {fmt_price(nk, 0, suffix='å')} / S&amp;P500 {fmt_price(sp, 2)} /
      USD/JPY {fmt_price(fx, 2, suffix='å')} / BTC {fmt_price(btc, 0, prefix='$')} /
      é {fmt_price(gld, 2, prefix='$', suffix='/oz')}
    </div>
  </div>

  <!-- ä»æ¥ã®ã«ã¼ã -->
  <p class="section-title">æ¬æ¥ã®ãã¼ã±ãã</p>
  <div class="cards-grid">
    <div class="card">
      <div class="card-header">
        <div class="card-icon icon-stocks">ð¾</div>
        <div><div class="card-title">æ ªå¼å¸å ´</div><div class="card-subtitle">æ¥æ¬æ ªã»ç±³å½æ ª</div></div>
      </div>
      <div class="price-row"><span class="price-label">æ¥çµå¹³å</span><span class="price-value">{fmt_price(nk, 0, suffix='å')} {fmt_change(nk_chg)}</span></div>
      <div class="price-row"><span class="price-label">S&amp;P500</span><span class="price-value">{fmt_price(sp, 2)} {fmt_change(sp_chg)}</span></div>
    </div>
    <div class="card">
      <div class="card-header">
        <div class="card-icon icon-fx">ð±</div>
        <div><div class="card-title">çºæ¿ï¼FXï¼</div><div class="card-subtitle">ãã«åã»ã¦ã¼ã­å</div></div>
      </div>
      <div class="price-row"><span class="price-label">USD/JPY</span><span class="price-value">{fmt_price(fx, 2, suffix='å')} {fmt_change(fx_chg)}</span></div>
      <div class="price-row"><span class="price-label">EUR/JPY</span><span class="price-value">{fmt_price(efx, 2, suffix='å')} {fmt_change(efx_chg)}</span></div>
    </div>
    <div class="card">
      <div class="card-header">
        <div class="card-icon icon-cmd">ð¢ï¸</div>
        <div><div class="card-title">ã³ã¢ãã£ãã£</div><div class="card-subtitle">åæ²¹ã»é</div></div>
      </div>
      <div class="price-row"><span class="price-label">WTIåæ²¹</span><span class="price-value">{fmt_price(oil, 2, prefix='$', suffix='/bbl')} {fmt_change(oil_chg)}</span></div>
      <div class="price-row"><span class="price-label">éï¼ã¹ãããï¼</span><span class="price-value">{fmt_price(gld, 2, prefix='$', suffix='/oz')} {fmt_change(gld_chg)}</span></div>
    </div>
    <div class="card">
      <div class="card-header">
        <div class="card-icon icon-crypto">â¿</div>
        <div><div class="card-title">æå·è³ç£</div><div class="card-subtitle">BTCã»ETH</div></div>
      </div>
      <div class="price-row"><span class="price-label">Bitcoin (BTC)</span><span class="price-value">{fmt_price(btc, 0, prefix='$')} {fmt_change(btc_chg)}</span></div>
      <div class="price-row"><span class="price-label">Ethereum (ETH)</span><span class="price-value">{fmt_price(eth, 2, prefix='$')} {fmt_change(eth_chg)}</span></div>
    </div>
  </div>

  <!-- æ­´å²ãã£ã¼ã -->
  <p class="section-title">ð 50å¹´ä¾¡æ ¼ãã£ã¼ãï¼æ­´å²çã¤ãã³ãä»ãï¼</p>

  <div class="chart-section">
    <div class="chart-title">æ ªå¼å¸å ´ â æ¥çµå¹³å / S&amp;P500</div>
    <div class="chart-subtitle">ææ¬¡çµå¤ï¼å·¦è»¸: æ¥çµå¹³ååãå³è»¸: S&amp;P500ãã¤ã³ãï¼</div>
    <div class="chart-hint">ð¡ ç¹ç·ãã¼ã«ã¼ã«ã«ã¼ã½ã«ãå½ã¦ãã¨ã¤ãã³ãåãè¡¨ç¤ºããã¾ã</div>
    <div class="chart-wrap"><canvas id="chartStocks"></canvas></div>
  </div>

  <div class="chart-section">
    <div class="chart-title">çºæ¿ â USD/JPYï¼ãã«åï¼</div>
    <div class="chart-subtitle">ææ¬¡çµå¤ï¼å/ãã«ï¼</div>
    <div class="chart-hint">ð¡ ç¹ç·ãã¼ã«ã¼ã«ã«ã¼ã½ã«ãå½ã¦ãã¨ã¤ãã³ãåãè¡¨ç¤ºããã¾ã</div>
    <div class="chart-wrap"><canvas id="chartFX"></canvas></div>
  </div>

  <div class="chart-section">
    <div class="chart-title">ã´ã¼ã«ã â éä¾¡æ ¼ï¼ã¹ããã/åç©ï¼</div>
    <div class="chart-subtitle">ææ¬¡çµå¤ï¼USD/ozï¼</div>
    <div class="chart-hint">ð¡ ç¹ç·ãã¼ã«ã¼ã«ã«ã¼ã½ã«ãå½ã¦ãã¨ã¤ãã³ãåãè¡¨ç¤ºããã¾ã</div>
    <div class="chart-wrap"><canvas id="chartGold"></canvas></div>
  </div>

  <!-- ã¤ãã³ãä¸è¦§ -->
  <p class="section-title">ð æ­´å²çã¤ãã³ãä¸è¦§</p>
  <div class="event-section">
    <table>
      <thead><tr><th>å¹´æ</th><th>ã¤ãã³ã</th><th>é¢é£è³ç£</th><th>æ¦è¦</th></tr></thead>
      <tbody>{event_rows}</tbody>
    </table>
  </div>

</main>
<footer>
  <p>ãã¼ã¿ã½ã¼ã¹: Yahoo Finance (yfinance) &nbsp;|&nbsp;
  <a href="https://invest-ai-info.github.io/marketwatch-ai/">GitHub Pages</a> &nbsp;|&nbsp;
  æ¬ãã¼ã¿ã¯èªååå¾ã»è¡¨ç¤ºã§ãããæè³å©è¨ã§ã¯ããã¾ããã</p>
</footer>

<script>
const NK_DATES  = {json.dumps(nk_dates)};
const NK_PRICES = {json.dumps(nk_prices)};
const SP_DATES  = {json.dumps(sp_dates)};
const SP_PRICES = {json.dumps(sp_prices)};
const FX_DATES  = {json.dumps(fx_dates)};
const FX_PRICES = {json.dumps(fx_prices)};
const GLD_DATES  = {json.dumps(gld_dates)};
const GLD_PRICES = {json.dumps(gld_prices)};

const NK_ANN  = {nk_ann};
const SP_ANN  = {sp_ann};
const FX_ANN  = {fx_ann};
const GLD_ANN = {gld_ann};

const gridColor  = 'rgba(48,54,61,0.8)';
const labelColor = '#8b949e';

function makeChart(id, datasets, annotations, yLabels) {{
  const ctx = document.getElementById(id).getContext('2d');
  const scales = {{}};
  datasets.forEach((ds, i) => {{
    const axId = 'y' + i;
    ds.yAxisID = axId;
    scales[axId] = {{
      position: i === 0 ? 'left' : 'right',
      grid: {{ color: i === 0 ? gridColor : 'transparent', drawBorder: false }},
      ticks: {{ color: labelColor, font: {{ size: 10 }}, maxTicksLimit: 6,
        callback: v => yLabels[i] ? yLabels[i](v) : v }},
      title: {{ display: false }},
    }};
  }});
  scales['x'] = {{
    ticks: {{ color: labelColor, font: {{ size: 10 }}, maxTicksLimit: 12,
      callback: function(val, idx) {{
        const lbl = this.getLabelForValue(val);
        return lbl && lbl.endsWith('-01') ? lbl.substring(0,4) : '';
      }}
    }},
    grid: {{ color: gridColor, drawBorder: false }},
  }};
  return new Chart(ctx, {{
    type: 'line',
    data: {{ labels: datasets[0].dates, datasets }},
    options: {{
      responsive: true, maintainAspectRatio: false,
      interaction: {{ mode: 'index', intersect: false }},
      plugins: {{
        legend: {{ labels: {{ color: '#e6edf3', font: {{ size: 12 }} }} }},
        tooltip: {{ backgroundColor: 'rgba(22,27,34,0.95)', titleColor: '#58a6ff',
                    bodyColor: '#e6edf3', borderColor: '#30363d', borderWidth: 1 }},
        annotation: {{ annotations }},
      }},
      scales,
      elements: {{ point: {{ radius: 0, hoverRadius: 4 }}, line: {{ tension: 0.2 }} }},
    }}
  }});
}}

// æ ªå¼ãã£ã¼ãï¼æ¥çµ + S&P500ï¼
const mergedDates = [...new Set([...NK_DATES, ...SP_DATES])].sort();
const nkMap = Object.fromEntries(NK_DATES.map((d,i) => [d, NK_PRICES[i]]));
const spMap = Object.fromEntries(SP_DATES.map((d,i) => [d, SP_PRICES[i]]));
makeChart('chartStocks', [
  {{ label: 'æ¥çµå¹³åï¼åï¼', dates: NK_DATES, data: NK_PRICES,
     borderColor: '#58a6ff', backgroundColor: 'rgba(88,166,255,0.08)',
     borderWidth: 1.5, fill: true }},
  {{ label: 'S&P500', dates: SP_DATES, data: SP_PRICES,
     borderColor: '#3fb950', backgroundColor: 'rgba(63,185,80,0.06)',
     borderWidth: 1.5, fill: true }},
], Object.assign({{}}, NK_ANN, SP_ANN),
[v => v.toLocaleString()+'å', v => v.toLocaleString()]);

// çºæ¿ãã£ã¼ã
makeChart('chartFX', [
  {{ label: 'USD/JPYï¼åï¼', dates: FX_DATES, data: FX_PRICES,
     borderColor: '#f0883e', backgroundColor: 'rgba(240,136,62,0.08)',
     borderWidth: 1.5, fill: true }},
], FX_ANN, [v => v.toFixed(1)+'å']);

// éãã£ã¼ã
makeChart('chartGold', [
  {{ label: 'éä¾¡æ ¼ï¼USD/ozï¼', dates: GLD_DATES, data: GLD_PRICES,
     borderColor: '#ffd700', backgroundColor: 'rgba(255,215,0,0.08)',
     borderWidth: 1.5, fill: true }},
], GLD_ANN, [v => '$'+v.toLocaleString()]);
</script>
</body>
</html>"""


# âââââââââââââââââââââââââââââââââââââââââ
# ã¡ã¤ã³
# âââââââââââââââââââââââââââââââââââââââââ
def main():
    now_jst = datetime.now(JST)
    print("ð¡ ç¾å¨ä¾¡æ ¼ãåå¾ä¸­...")
    data = {
        "nikkei": get_price("^N225"),
        "sp500":  get_price("^GSPC"),
        "usdjpy": get_price("JPY=X"),
        "eurjpy": get_price("EURJPY=X"),
        "oil":    get_price("CL=F"),
        "gold":   get_price("GC=F"),
        "btc":    get_price("BTC-USD"),
        "eth":    get_price("ETH-USD"),
    }
    print("ð æ­´å²çä¾¡æ ¼ãã¼ã¿ãåå¾ä¸­ï¼50å¹´åï¼...")
    hist = {
        "nikkei": get_historical_monthly("^N225",  "1975-01-01"),
        "sp500":  get_historical_monthly("^GSPC",  "1975-01-01"),
        "usdjpy": get_historical_monthly("JPY=X",  "1975-01-01"),
        "gold":   get_historical_monthly("GC=F",   "1975-01-01"),
    }
    print("ðï¸  HTMLçæä¸­...")
    content = build_html(data, hist, now_jst)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(content)
    print(f"â index.html çæå®äº ({now_jst.strftime('%Y-%m-%d %H:%M JST')})")

if __name__ == "__main__":
    main()
