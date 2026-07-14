# AIシグナル研究日誌 #040 — ラボノート

**研究日**: 2026-07-15 (JST)  
**仮説**: tier=good gate は IS 低パフォーマンス（金属不毛期の遺物）を前向きデータが覆し、前向き E(R) CI 全域プラスで ⛔反証確定

---

## 検証スクリプト

```python
import json, math

with open('signals-log.json') as f:
    data = json.load(f)

def closed(d): return d.get('outcome') in ('tp1','tp2','sl')
def win(d): return d.get('outcome') in ('tp1','tp2')
signals = [s for s in data if closed(s)]

GROUPS = {
    "metal":    {"GC=F", "SI=F"},
    "index":    {"NKD=F", "ES=F", "NQ=F", "YM=F", "^FTSE"},
    "jpy_fx":   {"USDJPY=X", "EURJPY=X", "GBPJPY=X", "AUDJPY=X"},
    "other_fx": {"EURUSD=X", "GBPUSD=X", "AUDUSD=X", "EURAUD=X", "GBPAUD=X"},
    "btc":      {"BTC-USD"},
    "oil":      {"CL=F"},
}
def get_group(s):
    t = s.get('ticker','')
    for g, tickers in GROUPS.items():
        if t in tickers: return g
    return 'other'

def wilson(k, n, z=1.96):
    if n == 0: return (0.0, 0.0)
    p = k/n
    den = 1 + z*z/n
    c = (p + z*z/(2*n))/den
    pm = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))/den
    return (round(max(0, c-pm)*100,1), round(min(1, c+pm)*100,1))

def rcalc(lst):
    n = len(lst)
    if n == 0: return 0.0, (0.0, 0.0)
    er = sum(lst)/n
    std = math.sqrt(sum((r-er)**2 for r in lst)/(n-1)) if n>1 else 0
    m = 1.96*std/math.sqrt(n)
    return round(er,3), (round(er-m,3), round(er+m,3))

def stats(lst):
    n = len(lst)
    if n == 0: return "N=0"
    k = sum(1 for s in lst if win(s))
    r_list = [1.33 if win(s) else -1.0 for s in lst]
    er, rci = rcalc(r_list)
    ci = wilson(k, n)
    return f"k={k}/N={n}={100*k/n:.1f}% E(R)={er:+.3f} CI[{ci[0]}%,{ci[1]}%] RCI[{rci[0]:+.3f},{rci[1]:+.3f}]"

def tier_eq(s, t):
    sel = s.get('selection')
    return isinstance(sel, dict) and sel.get('tier') == t

good       = [s for s in signals if tier_eq(s,'good')]
neutral    = [s for s in signals if tier_eq(s,'neutral')]
elite      = [s for s in signals if tier_eq(s,'elite')]
avoid      = [s for s in signals if tier_eq(s,'avoid')]
good_l     = [s for s in good if 'ロング' in (s.get('direction') or '')]
good_s     = [s for s in good if 'ショート' in (s.get('direction') or '')]
good_metal = [s for s in good if get_group(s)=='metal']
good_idx   = [s for s in good if get_group(s)=='index']
good_ofx   = [s for s in good if get_group(s)=='other_fx']
good_jpy   = [s for s in good if get_group(s)=='jpy_fx']
good_btc   = [s for s in good if get_group(s)=='btc']
good_oil   = [s for s in good if get_group(s)=='oil']
```

---

## 生出力

```
総クローズ: 1699

=== tier=good 全体 ===
k=129/N=285=45.3% E(R)=+0.055 CI[39.6%,51.1%] RCI[-0.080,+0.190]

=== tier=good × dir=long (全) ===
k=119/N=272=43.8% E(R)=+0.019 CI[38.0%,49.7%] RCI[-0.118,+0.157]

=== tier=good × dir=short (全) ===
k=10/N=13=76.9% E(R)=+0.792 CI[49.7%,91.8%] RCI[+0.237,+1.348]

=== tier=neutral 全体 ===
k=160/N=432=37.0% E(R)=-0.137 CI[32.6%,41.7%] RCI[-0.243,-0.031]

=== tier=elite 全体 ===
k=90/N=185=48.6% E(R)=+0.134 CI[41.5%,55.8%] RCI[-0.035,+0.302]

=== tier=avoid 全体 ===
k=197/N=471=41.8% E(R)=-0.025 CI[37.5%,46.3%] RCI[-0.129,+0.078]

=== tier=good × group別 (全) ===
metal  : k=15/N=47=31.9% E(R)=-0.256 CI[20.4%,46.2%] RCI[-0.570,+0.057]
index  : k=43/N=87=49.4% E(R)=+0.152 CI[39.2%,59.7%] RCI[-0.095,+0.398]
other_fx: k=34/N=75=45.3% E(R)=+0.108 CI[34.6%,56.6%] RCI[-0.176,+0.393]
jpy_fx : k=20/N=44=45.5% E(R)=+0.059 CI[31.7%,59.9%] RCI[-0.323,+0.441]
btc    : k=10/N=15=66.7% E(R)=+0.631 CI[41.7%,84.8%] RCI[+0.021,+1.241]
oil    : k=7/N=17=41.2% E(R)=-0.095 CI[21.6%,64.0%] RCI[-0.620,+0.430]
```

---

## 前向きトラッカー計測値（signal_lab_tracker.py, 登録日2026-06-25）

```
tier=good         gate  ⛔反証  前向き61/89=68% E(R)=+0.60 CI[+0.31~+0.89] N=89≥80
tier=good×dir=long gate  ⛔反証  前向き56/83=68% E(R)=+0.57 CI[+0.26~+0.89] N=83≥80
```

反証成立条件:
- N≥80 ✅ (89/83 両方)
- CI上限<0 を満たすべきだったが、実際は CI下限+0.31/+0.26 >> 0 → 完全逆転

---

## 解釈・交絡点検

1. **IS低パフォーマンスの原因（#038判明済）**
   - tier=good × metal = 15/47=31.9% (E(R)=-0.256) が IS 期間に集中
   - 金属レジーム転換（#030: IS E(R)=-0.964 → FWD +0.672）が主因
   - tier=good の油も IS 41.2% (N=17) と低位

2. **FWD好成績の構造（#035判明済）**
   - IS→FWD 全グループで性能シフト
   - 構成シフト（asset mix の変化）寄与 ≒ 0pp（純粋な性能転換）

3. **tier=neutral との対比（重要）**
   - tier=neutral: 37.0% E(R)=-0.137 RCI[-0.243,-0.031] → 全域マイナス継続
   - tier=good は転換したが tier=neutral は転換していない → ティアの識別力は実在

4. **dir=long 単独でも ⛔反証（56/83=68%）**
   - dir=short は N=13 と小サンプルで判断不能
   - ロング主体でも強い → 方向ではなく tier がドライバー

5. **Wilson CI 内包確認（multi-comparison 懸念）**
   - tier=good × group=btc = 66.7% (N=15) は CI 幅大 → 過信禁止
   - 主張は tier=good 全体（N=285）に限定し、グループ別は補足

---

## 交絡点検チェックリスト

- [x] 金属レジーム転換が IS 低パフォーマンスの主因（#038で解明済み）
- [x] 構成シフト寄与≒0（純粋な性能シフト）
- [x] N=89/83 ≥ 80 （昇格基準クリア）
- [x] tier=neutral は対照として依然弱い（tier識別力の傍証）
- [x] 小サンプル注意 (btc N=15, oil N=17) → 補足にのみ記載
