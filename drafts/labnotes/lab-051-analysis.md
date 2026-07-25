# lab-051-analysis.md — AIシグナル研究日誌 #051

## 基準日: 2026-07-26

## 研究テーマ
上昇トレンド×逆張り買い（reversalL）の前向きN=113でCI下限がゼロ割れした原因を解剖。
仮説：BBが77%を占有しており、BBの低成績が全体CI下限を引き下げている。
RSI単体（23%/26件）は前向き73.1%で依然健在か検証。

## 前向きトラッカー確認 (2026-07-26)
- `trend=上昇×reversalL`: FWD 57/113=50.4% E(R)=+0.177 CI[-0.01~+0.36] → ✅昇格維持
  - CI下限=-0.01でゼロ割れ（降格1回目チェックポイント通過）

## 仮説と事前宣言
- H1: signal=rsi_oversold_bounce × trend=上昇 × reversalL の前向きCI下限 ≥ 43%
- H2: signal=bb_lower_touch × trend=上昇 × reversalL の前向き平均R CI下限 ≤ 0

## 検証スクリプト（Python）

```python
import json, math
from datetime import date, datetime

with open("signals-log.json") as f:
    raw = json.load(f)

closed = [s for s in raw if s.get("outcome") not in [None, "", "open", "pending"]]

def get_trend(d):
    ta = d.get("trend_alignment")
    if isinstance(ta, dict) and ta.get("higher_tf_trend"):
        return ta["higher_tf_trend"]
    return None

rev_long_signals = {"rsi_oversold_bounce", "bb_lower_touch"}
def is_reversal_long(d):
    return "ロング" in (d.get("direction") or "") and d.get("primary_signal") in rev_long_signals

def get_date(s):
    ts = s.get("fired_at") or ""
    try:
        return datetime.fromisoformat(ts).date()
    except:
        return None

def is_win(s): return s.get("outcome") in ["tp1","tp2","TP1","TP2","TP"]
def get_R(s):
    o = s.get("outcome","")
    if o in ["tp1","TP1"]: return 1.33
    if o in ["tp2","TP2","TP"]: return 2.0
    if o in ["sl","SL"]: return -1.0
    return 0

def wilson_ci(k, n, z=1.96):
    if n == 0: return (0, 0)
    p = k/n; d = 1 + z**2/n
    center = (p + z**2/(2*n)) / d
    margin = z * math.sqrt(p*(1-p)/n + z**2/(4*n**2)) / d
    return max(0, center-margin), min(1, center+margin)

def r_ci(rs):
    if len(rs) < 2: return (0,0,0)
    n = len(rs); m = sum(rs)/n
    var = sum((x-m)**2 for x in rs)/(n-1)
    se = math.sqrt(var/n)
    return m, m-1.96*se, m+1.96*se

def norm_ticker(t): return (t or "").replace("=X","")
tickers_by_group = {
    "index": {"NKD=F","ES=F","NQ=F","YM=F","^FTSE"},
    "jpy_fx": {"USDJPY","EURJPY","GBPJPY","AUDJPY"},
    "other_fx": {"EURUSD","GBPUSD","AUDUSD","EURAUD","GBPAUD"},
    "metal": {"GC=F","SI=F"}, "btc": {"BTC-USD"}, "oil": {"CL=F"},
}
def get_group(s):
    t = norm_ticker(s.get("ticker",""))
    for g, tset in tickers_by_group.items():
        if t in tset: return g
    return None

fwd_start = date(2026, 6, 22)
ul_all = [s for s in closed if get_trend(s) == "上昇" and is_reversal_long(s)]
ul_fwd = sorted([s for s in ul_all if get_date(s) and get_date(s) >= fwd_start], key=lambda x: get_date(x))
ul_is = [s for s in ul_all if not get_date(s) or get_date(s) < fwd_start]
mid = len(ul_fwd)//2
fwd1 = ul_fwd[:mid]; fwd2 = ul_fwd[mid:]
```

## 生出力

```
全クローズ: 2624

=== [全体] trend=上昇×reversalL ===
  IS          : 54/101 = 53.5%  CI[43.8,62.9]  E(R)=+0.246 RCI[+0.02~+0.47]
  FWD全体       : 57/113 = 50.4%  CI[41.4,59.5]  E(R)=+0.175 RCI[-0.04~+0.39]
  FWD前半       : 34/56 = 60.7%  CI[47.6,72.4]  E(R)=+0.415 RCI[+0.11~+0.72]
  FWD後半       : 23/57 = 40.4%  CI[28.6,53.3]  E(R)=-0.060 RCI[-0.36~+0.24]
  全期間         : 111/214 = 51.9%  CI[45.2,58.5]  E(R)=+0.209 RCI[+0.05~+0.36]

=== [シグナル別] IS→FWD ===
  IS  rsi_oversold_bounce: 13/25 = 52.0%  CI[33.5,70.0]  E(R)=+0.212
  FWD rsi_oversold_bounce: 19/26 = 73.1%  CI[53.9,86.3]  E(R)=+0.703 RCI[+0.30~+1.11]
  IS  bb_lower_touch     : 41/76 = 53.9%  CI[42.8,64.7]  E(R)=+0.257
  FWD bb_lower_touch     : 38/87 = 43.7%  CI[33.7,54.1]  E(R)=+0.018 RCI[-0.23~+0.26]

=== [グループ別] FWD ===
  index       : 10/30 = 33.3%  CI[19.2,51.2]  E(R)=-0.223
  jpy_fx      : 15/26 = 57.7%  CI[38.9,74.5]  E(R)=+0.344
  other_fx    : 20/38 = 52.6%  CI[37.3,67.5]  E(R)=+0.226
  oil         :  6/7  = 85.7%  CI[48.7,97.4]  E(R)=+0.997 (N=7小)

=== [グループ×シグナル FWD] ===
  index×rsi_oversold_bounce: 3/3 = 100.0% (N=3小)
  index×bb_lower_touch     : 7/27 = 25.9%
  jpy_fx×rsi_oversold_bounce: 2/3 = 66.7%
  jpy_fx×bb_lower_touch    : 13/23 = 56.5%
  other_fx×rsi_oversold_bounce: 6/9 = 66.7%
  other_fx×bb_lower_touch  : 14/29 = 48.3%

=== [RSI/BB FWD時系列] ===
  RSI全FWD  : 19/26 = 73.1%  CI[53.9,86.3]  E(R)=+0.703 RCI[+0.30~+1.11]
  RSIFWD前半: 12/13 = 92.3%  CI[66.7,98.6]  E(R)=+1.151
  RSIFWD後半:  7/13 = 53.8%  CI[29.1,76.8]  E(R)=+0.255 (後半減速)
  BB全FWD   : 38/87 = 43.7%  CI[33.7,54.1]  E(R)=+0.018 RCI[-0.23~+0.26]
  BBFWD前半 : 22/43 = 51.2%  CI[36.8,65.4]  E(R)=+0.192
  BBFWD後半 : 16/44 = 36.4%  CI[23.8,51.1]  E(R)=-0.153 (後半崩落)

=== [グループ別] IS ===
  IS index  : 35/51 = 68.6%  CI[55.0,79.7]
  IS jpy_fx : 15/26 = 57.7%  CI[38.9,74.5]
  IS other_fx: 1/16 =  6.2%  CI[1.1,28.3]

=== [比較対照] FWD ===
  下降×revL FWD: 75/159 = 47.2%  CI[39.6,54.9]  E(R)=+0.105
  中立×revL FWD: 39/89  = 43.8%  CI[34.0,54.2]  E(R)=+0.055

=== 全期間 サブグループ（claims用） ===
  signal=rsi_oversold_bounce×上昇×revL: k=32, n=51 (62.7%)
  signal=bb_lower_touch×上昇×revL    : k=79, n=163 (48.5%)
  group=index×上昇×revL              : k=45, n=81 (55.6%)
  group=jpy_fx×上昇×revL             : k=30, n=52 (57.7%)
  group=other_fx×上昇×revL           : k=21, n=54 (38.9%)

=== 判定サマリ ===
▶ H1 RSI FWD: 19/26 CI下限=53.9% ≥43% ✅
▶ H2 BB FWD E(R)RCI下限=-0.227 ≤0 ✅
▶ 全期間: 111/214 = 51.9% CI[45.2,58.5] E(R)=+0.209 RCI[+0.05~+0.36]
▶ シグナル構成比: RSI=23% (26件), BB=77% (87件)
```

## 交絡点検
1. IS指数68.6% → FWD33.3%の急落: 全クローズ件数の増加に伴う通常のドローダウンか
2. BB FWD後半崩落(36.4%): 指数×BB=7/27=25.9%が引きずっている (#050確認済み)
3. other_fx IS6.2% → FWD52.6%: 金属レジーム転換と同根の性能シフト (#030/#032/#036)
4. RSI FWD後半53.8%(N=13): N小サンプルのためCI幅が広い（29.1~76.8%）

## 注記
- FWD数値は日付（fired_at ≥ 2026-06-22）で区切った前向き期間
- claims.jsonにはverify.py対応フィルタで再現可能な全期間数値のみ記載
- FWD期間数値（73.1%、43.7%）は本文のみに記載（日付フィルタは verify.py 非対応）
