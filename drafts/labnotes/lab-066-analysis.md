# lab-066-analysis.md
**仮説**: trend=下降 gate — FWD N=519 で期待値CI下限がプラス到達
**日付**: 2026-08-10
**分類**: ②前向き大変動（CI下限 +0.023 > 0 に到達、最大変動トラッカー）

---

## 検証スクリプト

```python
import json, math

def wilson(k, n, z=1.96):
    if n == 0: return (0.0, 0.0)
    p = k/n
    denom = 1 + z*z/n
    center = (p + z*z/(2*n)) / denom
    margin = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / denom
    lo = max(0.0, center - margin)
    hi = min(1.0, center + margin)
    return (round(lo*100,1), round(hi*100,1))

def er(k,n):
    if n==0: return 0
    wr = k/n
    return round(2.0*wr - 1.5*(1-wr), 3)

def rci(k,n):
    lo,hi = wilson(k,n)
    er_lo = round(2.0*(lo/100) - 1.5*(1-(lo/100)),3)
    er_hi = round(2.0*(hi/100) - 1.5*(1-(hi/100)),3)
    return f"[{er_lo:+.3f},{er_hi:+.3f}]"

GROUPS = {
    "metal":    {"GC=F", "SI=F"},
    "index":    {"NKD=F", "ES=F", "NQ=F", "YM=F", "^FTSE"},
    "jpy_fx":   {"USDJPY=X", "EURJPY=X", "GBPJPY=X", "AUDJPY=X"},
    "other_fx": {"EURUSD=X", "GBPUSD=X", "AUDUSD=X", "EURAUD=X", "GBPAUD=X"},
    "btc":      {"BTC-USD"},
    "oil":      {"CL=F"},
}
def get_group(ticker):
    for g, tickers in GROUPS.items():
        if ticker in tickers:
            return g
    return None
def get_trend(d):
    ta = d.get("trend_alignment")
    if isinstance(ta, dict) and ta.get("higher_tf_trend"):
        return ta["higher_tf_trend"]
    return "unknown"
def match(d, f):
    if "group" in f and get_group(d.get("ticker","")) != f["group"]: return False
    if "direction" in f:
        fdir = f["direction"]; ddir = d.get("direction","")
        if fdir=="long" and "ロング" not in ddir: return False
        if fdir=="short" and "ショート" not in ddir: return False
    if "trend" in f and get_trend(d) != f["trend"]: return False
    if "signal" in f and d.get("primary_signal","") != f["signal"]: return False
    if "reversal_long" in f:
        ps = d.get("primary_signal",""); ddir = d.get("direction","")
        is_rl = ("ロング" in ddir) and (ps in {"rsi_oversold_bounce","bb_lower_touch"})
        if f["reversal_long"] != is_rl: return False
    return True
def closed(d): return d.get("outcome") in ("tp1","tp2","sl")
def win(d): return d.get("outcome") in ("tp1","tp2")
def compute(data, f):
    k = sum(1 for d in data if closed(d) and win(d) and match(d, f))
    n = sum(1 for d in data if closed(d) and match(d, f))
    return k, n

with open('signals-log.json') as f:
    data = json.load(f)
FWD_START = "2026-06-25"
is_data = [d for d in data if d.get("fired_at","") < FWD_START]
fwd_data = [d for d in data if d.get("fired_at","") >= FWD_START]
F = {"trend": "下降"}

# メイン結果
for label, subset in [("IS", is_data), ("FWD", fwd_data), ("ALL", data)]:
    k,n = compute(subset, F)
    lo,hi = wilson(k,n); e = er(k,n); rc = rci(k,n)
    print(f"{label}: {k}/{n}={k/n*100:.1f}% CI[{lo}~{hi}] E(R)={e:+.3f} RCI={rc}")
```

---

## 生出力（signal_lab_verify.py互換関数で検証）

```
IS全体        : 135/377=35.8%  CI[31.1~40.8]  E(R)=-0.247  RCI=[-0.412,-0.072]
FWD全体       : 248/519=47.8%  CI[43.5~52.1]  E(R)=+0.172  RCI=[+0.023,+0.324]
全期間全体     : 383/896=42.7%  CI[39.5~46.0]  E(R)=-0.004  RCI=[-0.117,+0.110]

--- グループ別 IS/FWD ---
metal IS      : 31/136=22.8%  CI[16.5~30.5]  E(R)=-0.702  RCI=[-0.922,-0.432]
metal FWD     : 55/103=53.4%  CI[43.8~62.7]  E(R)=+0.369  RCI=[+0.033,+0.695]
metal 全期間  : 86/239=36.0%  CI[30.2~42.2]  E(R)=-0.241  RCI=[-0.443,-0.023]
index FWD     : 49/95=51.6%   CI[41.7~61.4]  E(R)=+0.305  RCI=[-0.040,+0.649]
index 全期間  : 63/120=52.5%  CI[43.6~61.2]  E(R)=+0.338  RCI=[+0.026,+0.642]
oil 全期間    : 36/65=55.4%   CI[43.4~66.7]
other_fx FWD  : 73/156=46.8%  CI[39.1~54.6]  E(R)=+0.138

--- シグナル別（FWD期間） ---
rsi_oversold IS : 29/87=33.3%  E(R)=-0.333
rsi_oversold FWD: 28/47=59.6%  CI[45.3~72.4]  E(R)=+0.585  RCI=[+0.085,+1.034]
bb_lower IS   : 26/83=31.3%   E(R)=-0.404
bb_lower FWD  : 62/109=56.9%  CI[47.5~65.8]  E(R)=+0.491  RCI=[+0.162,+0.803]
bb_lower 全期間: 88/192=45.8%  CI[38.9~52.9]  E(R)=+0.104
high_break IS : 5/14=35.7%    E(R)=-0.250
high_break FWD: 12/41=29.3%   CI[17.6~44.5]  E(R)=-0.476
high_break 全期間: 17/55=30.9% CI[20.3~44.0]  E(R)=-0.418  RCI=[-0.789,+0.040]

--- 方向別（FWD期間） ---
dir=long FWD  : 194/401=48.4% CI[43.5~53.3]  E(R)=+0.193  RCI=[+0.023,+0.365]
dir=short FWD : 54/118=45.8%  CI[37.0~54.7]  E(R)=+0.102

--- reversal_long別 ---
reversal_long IS : 55/170=32.4%  E(R)=-0.368
reversal_long FWD: 90/156=57.7%  CI[49.8~65.2]  E(R)=+0.519  RCI=[+0.243,+0.782]
reversal_long 全期間: 145/326=44.5%  CI[39.2~49.9]  E(R)=+0.057
```

---

## 採択仮説と主要知見

### H1（採択）: FWD N=519 で E(R) RCI 下限が +0.023 > 0 に到達
- verify.py（非cluster調整）で確認済み
- トラッカー（cluster調整）では RCI[+0.01~+0.23] で条件成就に至らず継続監視中

### H2（採択）: IS期間の悪化主因は金属グループのレジーム差
- metal IS 22.8% (-0.702R) → FWD 53.4% (+0.369R)
- IS期間の金（GC=F）・銀（SI=F）は下降トレンド中のシグナルが全滅に近い成績
- FWD期間は金属の強気相場転換でシグナル方向と合致し始めた

### H3（採択）: 改善は reversal_long 単独でなく全方位的
- 逆張り(reversal_long): IS 32.4% → FWD 57.7% (+25.3pp)
- 非逆張り: IS期間不詳、FWD非reversal = 158/363 ≈ 43.5%（過去⛔反証と差なし）
- ただし high_break はFWD期間でも 29.3%（-0.476R）と悪化継続

### トラッカー状態（2026-08-10 sweep後）
- 🟡蓄積中（⛔反証圏内だが cluster-adjusted でまだ到達せず）
- 連続ヒット0本（⛔反証には連続2本required）
- 次のチェックポイント: N=540付近（次の検証でCI_lower>0継続なら⛔反証候補）

---

## N不一致メモ
- signal_lab_verify.py（全銘柄対象）: FWD N=519
- signal-lab-tracker.json（1d拡張銘柄8種除外）: FWD N=517
- 記事・claims.json はverify.py の N=519 を使用（オラクル値が正式）
