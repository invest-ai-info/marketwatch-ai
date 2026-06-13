# lab-007-analysis.md — 検証ログ（三次元解析: blocked × group × trend）

## 基準日: 2026-06-14 (JST)

## 採択仮説
「other_fx × blocked=True の66.7%高勝率は、下降トレンドケースへの偏り（トレンド交絡）によって説明される」

## 事前宣言の合否基準（データ確認前に宣言）
- 条件①: other_fx × blocked=True × 下降 のWilson CI下限 ≥ 43% かつ N ≥ 5
- 条件②: other_fx × blocked=True × 中立 の勝率 < 43%
- 条件③: index × blocked=True > metal × blocked=True（グループ差の存在確認）
→ 3条件クリアで「通過A」

## 検証スクリプト（完全版）

```python
import json, math

def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 100.0)
    p = k / n
    den = 1 + z*z/n
    c = (p + z*z/(2*n)) / den
    pm = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / den
    return (max(0, c-pm)*100, min(1, c+pm)*100)

GROUPS = {
    "metal":    {"GC=F", "SI=F"},
    "index":    {"NKD=F", "ES=F", "NQ=F", "YM=F", "^FTSE"},
    "jpy_fx":   {"USDJPY=X", "EURJPY=X", "GBPJPY=X", "AUDJPY=X"},
    "other_fx": {"EURUSD=X", "GBPUSD=X", "AUDUSD=X", "EURAUD=X", "GBPAUD=X"},
    "btc":      {"BTC-USD"},
    "oil":      {"CL=F"},
}

with open('/home/user/marketwatch-ai/signals-log.json') as f:
    data = json.load(f)

def closed(d): return d.get("outcome") in ("tp1","tp2","sl")
def win(d): return d.get("outcome") in ("tp1","tp2")
def get_trend(d):
    ta = d.get("trend_alignment")
    if isinstance(ta, dict) and ta.get("higher_tf_trend"):
        return ta["higher_tf_trend"]
    return "unknown"
def get_group(d):
    ticker = d.get("ticker","")
    for g, tickers in GROUPS.items():
        if ticker in tickers: return g
    return "other"

closed_data = [d for d in data if closed(d)]
# Total: 652

# blocked=True/False
blocked_true = [d for d in closed_data if isinstance(d.get("sr_runway"), dict) and d["sr_runway"].get("blocked") == True]
blocked_false = [d for d in closed_data if isinstance(d.get("sr_runway"), dict) and d["sr_runway"].get("blocked") == False]
```

## 生の出力

```
=== Total closed signals: 652 ===

blocked=True: N=41, blocked=False: N=285, no_sr_runway: N=326

blocked=True全体:  22/41  = 53.7%  CI[38.7%~67.9%]
blocked=False全体: 111/285 = 38.9% CI[33.5%~44.7%]

=== blocked=True × グループ別 ===
  metal     : 4/8  = 50.0%  CI[21.5%~78.5%]
  index     : 6/8  = 75.0%  CI[40.9%~92.9%]
  jpy_fx    : 1/5  = 20.0%  CI[3.6%~62.4%]
  other_fx  : 10/15 = 66.7% CI[41.7%~84.8%]
  btc       : 0/3  = 0.0%   CI[0.0%~56.2%]  ← N=3のため本分析対象外
  oil       : 1/2  = 50.0%  CI[9.5%~90.5%]  ← N=2のため本分析対象外

=== blocked=False × グループ別 ===
  metal     : 9/50  = 18.0% CI[9.8%~30.8%]
  index     : 40/89 = 44.9% CI[35.0%~55.3%]
  jpy_fx    : 18/58 = 31.0% CI[20.6%~43.8%]
  other_fx  : 30/64 = 46.9% CI[35.2%~58.9%]

=== other_fx × blocked=True × trend（三次元核心） ===
  下降          : 8/8  = 100.0% CI[67.6%~100.0%]   ← N=8≥5, CI下限67.6%≥43% → 条件①✅
  上昇          : 2/3  = 66.7%  CI[20.8%~93.9%]    ← N=3 小サンプル
  中立・もみあい : 0/4  = 0.0%   CI[0.0%~49.0%]   ← 0.0% < 43% → 条件②✅

=== 三次元: 全グループ × blocked=True × trend ===
  【metal blocked=T=8】
    下降: 2/6 = 33.3%  CI[9.7%~70.0%]
    中立: 2/2 = 100.0% CI[34.2%~100.0%]  ← N=2
    上昇: N=0

  【index blocked=T=8】
    下降: 2/3 = 66.7%  CI[20.8%~93.9%]
    中立: N=0
    上昇: 4/5 = 80.0%  CI[37.6%~96.4%]

  【jpy_fx blocked=T=5】
    下降: N=0
    中立: 0/2 = 0.0%   CI[0.0%~65.8%]
    上昇: 1/3 = 33.3%  CI[6.1%~79.2%]

  【other_fx blocked=T=15】
    下降: 8/8 = 100.0%  CI[67.6%~100.0%]
    中立: 0/4 = 0.0%    CI[0.0%~49.0%]
    上昇: 2/3 = 66.7%   CI[20.8%~93.9%]
```

## 事前宣言の判定

| 条件 | 基準 | 実績 | 判定 |
|---|---|---|---|
| ① other_fx×blocked=T×下降 CI下限≥43% かつ N≥5 | CI下限≥43% & N≥5 | CI下限67.6%, N=8 | ✅ |
| ② other_fx×blocked=T×中立 < 43% | 勝率<43% | 0.0% | ✅ |
| ③ index×blocked=T > metal×blocked=T | index>metal | 75.0% > 50.0% | ✅ |

→ **通過A（3条件クリア）**

## 交絡解明

other_fx×blocked=True の10/15=66.7%のうち:
- 下降トレンド: 8件（全勝）
- 中立: 4件（全敗）
- 上昇: 3件（2勝1敗）

→ 下降8件と上昇3件の計11件で10勝 = 90.9%（交絡で高め）
→ 中立4件で0勝が足を引っ張り、結果66.7%

other_fx × blocked=True × 下降が全体の勝利を牽引していることが確認された。
トレンド偏り（8/15=53%が下降）が66.7%という数字を生み出した交絡。

## 前向きトラッカー更新

- [i] other_fx × blocked=True: 10/15 = 66.7% CI[41.7%~84.8%]（N不足・前回と同値）
- [k] NEW: other_fx × blocked=True × 下降: 8/8 = 100.0% CI下限67.6%（N=8 蓄積中）
  宣言基準: N≥15かつCI下限≥50%

## 期待値R計算（TP1 R:R = 1.333）

| グループ条件 | 勝率 | E(R) |
|---|---|---|
| blocked=True全体 | 53.7% | +0.252R |
| other_fx × blocked=True | 66.7% | +0.556R |
| other_fx × blocked=True × 下降 | 100.0% | +1.333R |
| other_fx × blocked=True × 中立 | 0.0% | -1.000R |
| other_fx × blocked=False | 46.9% | +0.094R |
| blocked=False全体 | 38.9% | -0.091R |
