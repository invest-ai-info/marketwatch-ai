# AIシグナル研究日誌 #027 — 分析スクリプト & 生出力
基準日: 2026-07-02 (JST)

## 仮説
「逆張り買い（reversal_long=True）グループ別成績マップ ── 指数57%・メタル25%・BTC25%の三峰構造と上昇トレンド交絡」

事前宣言合否基準:
- H1: revL × index で in-sample CI下限 ≥ 43% かつ N ≥ 20
- H2: revL × metal で in-sample CI上限 ≤ 43% かつ N ≥ 20
- H3: revL × btc で in-sample CI上限 ≤ 43% かつ N ≥ 20

## 前処理
signals-log.json total: 1610件
closed (outcome in tp1/tp2/sl): 1273件

reversal_long=True 判定ロジック (signal_lab_verify.py準拠):
- direction に "ロング" を含む
- primary_signal が rsi_oversold_bounce または bb_lower_touch

## スクリプト
```python
import json, math

with open("signals-log.json") as f:
    signals = json.load(f)

GROUPS = {
    "metal":    {"GC=F", "SI=F"},
    "index":    {"NKD=F", "ES=F", "NQ=F", "YM=F", "^FTSE"},
    "jpy_fx":   {"USDJPY=X", "EURJPY=X", "GBPJPY=X", "AUDJPY=X"},
    "other_fx": {"EURUSD=X", "GBPUSD=X", "AUDUSD=X", "EURAUD=X", "GBPAUD=X"},
    "btc":      {"BTC-USD"},
    "oil":      {"CL=F"},
}
REV = {"rsi_oversold_bounce", "bb_lower_touch"}

def closed(d): return d.get("outcome") in ("tp1","tp2","sl")
def win(d): return d.get("outcome") in ("tp1","tp2")
def get_trend(d):
    ta = d.get("trend_alignment")
    if isinstance(ta, dict) and ta.get("higher_tf_trend"):
        return ta["higher_tf_trend"]
    return "unknown"
def get_group(d):
    t = d.get("ticker","")
    for g, tickers in GROUPS.items():
        if t in tickers: return g
    return "other"
def is_revL(d):
    is_long = "ロング" in (d.get("direction") or "")
    return is_long and d.get("primary_signal") in REV
def wilson_ci(k, n, z=1.96):
    if n == 0: return (0, 0)
    p = k / n
    denom = 1 + z*z/n
    center = (p + z*z/(2*n)) / denom
    margin = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / denom
    return (max(0, center-margin)*100, min(1, center+margin)*100)
```

## 生出力

クローズ済み: 1273 件

=== 全体 ===
全体: 520/1273=40.8% CI[38.2~43.6%]

=== reversal_long=True ===
全逆張り買い                   : 204/499=40.9% CI[36.7~45.2%] 
revL × index                : 59/103=57.3% CI[47.6~66.4%]
revL × jpy_fx               : 40/89=44.9% CI[35.0~55.3%]
revL × other_fx             : 56/139=40.3% CI[32.5~48.6%]
revL × metal                : 23/93=24.7% CI[17.1~34.4%]
revL × btc                  : 12/48=25.0% CI[14.9~38.8%]
revL × oil                  : 14/27=51.9% CI[34.0~69.3%]

revL × trend=上昇             : 65/118=55.1% CI[46.1~63.8%]
revL × trend=下降             : 72/203=35.5% CI[29.2~42.3%]
revL × trend=中立・もみあい       : 66/174=37.9% CI[31.1~45.3%]

revL × tf=1h                : 122/296=41.2% CI[35.8~46.9%]
revL × tf=4h                : 76/192=39.6% CI[32.9~46.6%]

revL × signal=rsi_oversold_bounce : 79/203=38.9% CI[32.5~45.8%]
revL × signal=bb_lower_touch      : 125/296=42.2% CI[36.7~47.9%]

=== 交差分析 ===
revL × index × 上昇           : 37/57=64.9% CI[51.9~76.0%]
revL × index × 中立・もみあい    : 17/39=43.6% CI[29.3~59.0%]
revL × jpy_fx × 上昇          : 19/30=63.3% CI[45.5~78.1%]
revL × jpy_fx × 下降          : 5/14=35.7% CI[16.3~61.2%]
revL × jpy_fx × 中立          : 16/45=35.6% CI[23.2~50.2%]
revL × other_fx × 上昇        : 6/23=26.1% CI[12.5~46.5%]
revL × other_fx × 下降        : 23/53=43.4% CI[31.0~56.7%]
revL × other_fx × 中立        : 27/63=42.9% CI[31.4~55.1%]

## 合否判定
H1: revL × index CI下限47.6%≥43% かつ N=103≥20 → ✅ 通過A
H2: revL × metal CI上限34.4%≤43% かつ N=93≥20 → ✅ 通過A
H3: revL × btc CI上限38.8%≤43% かつ N=48≥20 → ✅ 通過A

探索的発見:
- other_fx × 上昇 × revL = 26.1%(6/23) - 上昇トレンドでも逆張り買いが損益分岐割れ（N小・CI[12.5~46.5%]）
- 指数 × 上昇 × revL = 64.9%(37/57) - CI下限51.9%で最強組合せ
- 円クロス × 上昇 × revL = 63.3%(19/30) - CI下限45.5%で2位
- 全体revL = 40.9% < 43%だが CI[36.7~45.2%]で確定打なし（上方も含む）

## 交絡点検
1. グループ構成偏り: index(103/499=20.6%) vs metal(93/499=18.6%) vs other_fx(139/499=27.9%)
   → other_fxが最多で全体40.9%を引き下げる構造
2. トレンド分布: 上昇118/499=23.6%、下降203/499=40.7%、中立174/499=34.9%
   → 下降が最多でrevL全体を引き下げる

## 前向きトラッカー参照値（verify.py対象外・参考）
reversalL（逆張り買い）gate: forward 31/53=58%, E(R)=+0.36 CI[+0.05~+0.68]
trend=中立・もみあい×reversalL gate: forward 18/28=64%, E(R)=+0.50 CI[+0.08~+0.92]
group=index×reversalL edge: forward 8/16=50%
trend=上昇×reversalL edge: forward 11/17=65%
