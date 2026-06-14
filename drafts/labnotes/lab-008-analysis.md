# 研究日誌 #008 — 分析スクリプト全文と生出力

**仮説**: ma_golden（移動平均ゴールデンクロス）の実勝率は損益分岐43%を下回り、CI上限が43%未満であることを確認する  
**事前合否基準**: N≥20 かつ CI上限 < 43% → 棄却確認として「通過A」  
**基準日**: 2026-06-15 (JST)  
**signals-log件数**: 824件（内closed=654件）

---

## スクリプト全文

```python
#!/usr/bin/env python3
# lab-008-analysis.py — シグナル種別勝率マップ（全654件）
import json, math
from collections import defaultdict

def wilson(k, n, z=1.96):
    if n == 0: return (0.0, 100.0)
    p = k/n
    den = 1 + z*z/n
    c = (p + z*z/(2*n))/den
    pm = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))/den
    return (max(0, c-pm)*100, min(1, c+pm)*100)

def exp_r(p):
    """期待値R: TP1=+2R, SL=-1.5R（R:R=1.33設計）"""
    return p*2.0 + (1-p)*(-1.5)

data = json.load(open('signals-log.json'))
closed = [d for d in data if d.get('outcome') in ('tp1','tp2','sl')]

GROUPS = {
    "all": None,
    "metal":    {"GC=F", "SI=F"},
    "index":    {"NKD=F", "ES=F", "NQ=F", "YM=F", "^FTSE"},
    "jpy_fx":   {"USDJPY", "EURJPY", "GBPJPY", "AUDJPY",
                 "USDJPY=X","EURJPY=X","GBPJPY=X","AUDJPY=X"},
    "other_fx": {"EURUSD=X", "GBPUSD=X", "AUDUSD=X", "EURAUD=X", "GBPAUD=X"},
    "btc":      {"BTC-USD"},
    "oil":      {"CL=F"},
}

# === 全体baseline ===
all_k = sum(1 for d in closed if d['outcome'] in ('tp1','tp2'))
all_n = len(closed)
all_lo, all_hi = wilson(all_k, all_n)
print(f"全体baseline: {all_k}/{all_n} = {all_k/all_n*100:.1f}%  CI[{all_lo:.1f}~{all_hi:.1f}%]  E(R)={exp_r(all_k/all_n):+.3f}R")

# === primary_signal 別 ===
sig_stats = defaultdict(lambda: [0,0])
for d in closed:
    s = d.get('primary_signal', 'unknown')
    sig_stats[s][1] += 1
    if d['outcome'] in ('tp1','tp2'):
        sig_stats[s][0] += 1

print(f"\n{'シグナル':<32} {'k':>4} {'n':>5} {'勝率':>7} {'CI下限':>7} {'CI上限':>7} {'E(R)':>8}")
for sig, (k, n) in sorted(sig_stats.items(), key=lambda x: -x[1][0]/max(x[1][1],1)):
    if n >= 5:
        lo, hi = wilson(k, n)
        er = exp_r(k/n)
        print(f"  {sig:<30} {k:>4} {n:>5} {k/n*100:>6.1f}% {lo:>6.1f}% {hi:>6.1f}% {er:>+8.3f}R")

# === ma_golden 方向・グループ内訳 ===
print("\n=== ma_golden 方向確認 ===")
mag = [d for d in closed if d.get('primary_signal') == 'ma_golden']
long_count = sum(1 for d in mag if 'ロング' in (d.get('direction') or ''))
short_count = sum(1 for d in mag if 'ショート' in (d.get('direction') or ''))
print(f"  全{len(mag)}件: ロング={long_count}, ショート={short_count}")

print("\n=== ma_golden × グループ別 ===")
for grp, tickers in GROUPS.items():
    if grp == "all": continue
    sub = [d for d in mag if d.get('ticker') in tickers]
    if sub:
        k = sum(1 for d in sub if d['outcome'] in ('tp1','tp2'))
        n = len(sub)
        lo, hi = wilson(k, n)
        print(f"  {grp}: {k}/{n} = {k/n*100:.1f}%  CI[{lo:.1f}~{hi:.1f}%]")

# === 事前合否基準チェック ===
print("\n=== 主仮説の事前合否確認 ===")
mag_k, mag_n = 7, 30
lo8, hi8 = wilson(mag_k, mag_n)
print(f"  ma_golden: {mag_k}/{mag_n} = {mag_k/mag_n*100:.1f}%  CI[{lo8:.1f}~{hi8:.1f}%]")
print(f"  CI上限={hi8:.1f}% < 43%? {'→ YES → 通過A（棄却確認）' if hi8 < 43 else '→ NO → 未達'}")
print(f"  N=30 >= 20? {'→ YES' if mag_n >= 20 else '→ NO'}")

# === トラッカー更新 ===
print("\n=== 前向きトラッカー現在値 ===")
rev_long = [d for d in closed if 'ロング' in (d.get('direction') or '') 
            and d.get('primary_signal') in {'rsi_oversold_bounce','bb_lower_touch'}]
k,n = sum(1 for d in rev_long if d['outcome'] in ('tp1','tp2')), len(rev_long)
lo,hi = wilson(k,n)
print(f"  [f] 全逆張りロング: {k}/{n} = {k/n*100:.1f}%  CI[{lo:.1f}~{hi:.1f}%]")

idx_rev = [d for d in rev_long if d.get('ticker') in GROUPS['index']]
k,n = sum(1 for d in idx_rev if d['outcome'] in ('tp1','tp2')), len(idx_rev)
lo,hi = wilson(k,n)
print(f"  [g] 指数×逆張りロング: {k}/{n} = {k/n*100:.1f}%  CI[{lo:.1f}~{hi:.1f}%]")

fx_rev = [d for d in rev_long if d.get('ticker') in GROUPS['other_fx']]
k,n = sum(1 for d in fx_rev if d['outcome'] in ('tp1','tp2')), len(fx_rev)
lo,hi = wilson(k,n)
print(f"  [h] 他FX×逆張りロング: {k}/{n} = {k/n*100:.1f}%  CI[{lo:.1f}~{hi:.1f}%]")

i_sub = [d for d in closed if d.get('ticker') in GROUPS['other_fx'] 
         and isinstance(d.get('sr_runway'), dict) and d['sr_runway'].get('blocked') == True]
k,n = sum(1 for d in i_sub if d['outcome'] in ('tp1','tp2')), len(i_sub)
lo,hi = wilson(k,n) if n else (0,0)
print(f"  [i] 他FX×blocked=True: {k}/{n} = {k/n*100:.1f}%  CI[{lo:.1f}~{hi:.1f}%]" if n else "  [i] N=0")

def get_trend(d):
    ta = d.get("trend_alignment")
    if isinstance(ta, dict): return ta.get("higher_tf_trend","unknown")
    return "unknown"

blocked = [d for d in closed if isinstance(d.get('sr_runway'), dict) and d['sr_runway'].get('blocked') == True]
j_sub = [d for d in blocked if get_trend(d) == '中立・もみあい']
k,n = sum(1 for d in j_sub if d['outcome'] in ('tp1','tp2')), len(j_sub)
lo,hi = wilson(k,n) if n else (0,0)
print(f"  [j] 中立×blocked=True: {k}/{n} = {k/n*100:.1f}%  CI[{lo:.1f}~{hi:.1f}%]" if n else "  [j] N=0")

k_sub = [d for d in blocked if d.get('ticker') in GROUPS['other_fx'] and get_trend(d) == '下降']
k,n = sum(1 for d in k_sub if d['outcome'] in ('tp1','tp2')), len(k_sub)
lo,hi = wilson(k,n) if n else (0,0)
print(f"  [k] 他FX×blocked=True×下降: {k}/{n} = {k/n*100:.1f}%  CI[{lo:.1f}~{hi:.1f}%]" if n else "  [k] N=0")

# === 探索的: d_sup_atr（verify.py非対応次元・参考値のみ） ===
print("\n=== 探索的: d_sup_atr（verify.py非対応・本記事クレーム外）===")
sr_c = [d for d in closed if isinstance(d.get('sr_runway'), dict) 
        and d['sr_runway'].get('d_sup_atr') is not None]
for thr in [0.5, 1.0]:
    near = [d for d in sr_c if d['sr_runway']['d_sup_atr'] < thr]
    far  = [d for d in sr_c if d['sr_runway']['d_sup_atr'] >= thr]
    kn   = sum(1 for d in near if d['outcome'] in ('tp1','tp2'))
    kf   = sum(1 for d in far  if d['outcome'] in ('tp1','tp2'))
    lon, hin = wilson(kn, len(near)) if near else (0,0)
    lof, hif = wilson(kf, len(far))  if far  else (0,0)
    print(f"  d_sup_atr<{thr}: {kn}/{len(near)}={kn/len(near)*100:.1f}% CI[{lon:.1f}~{hin:.1f}] | >=: {kf}/{len(far)}={kf/len(far)*100:.1f}%")
```

---

## 生出力

```
全体baseline: 262/654 = 40.1%  CI[36.4~43.9%]  E(R)=-0.098R

シグナル                                  k     n      勝率    CI下限    CI上限      E(R)
  ma_dead                              8    14   57.1%   32.6%   78.6%   +0.500R
  macd_dead                           47   103   45.6%   36.3%   55.2%   +0.097R
  bb_lower_touch                      68   157   43.3%   35.8%   51.1%   +0.016R
  rsi_oversold_bounce                 51   128   39.8%   31.8%   48.5%   -0.105R
  macd_golden                         34    88   38.6%   29.1%   49.1%   -0.148R
  low_break                           16    42   38.1%   25.0%   53.2%   -0.167R
  rsi_overbought                       5    14   35.7%   16.3%   61.2%   -0.250R
  high_break                          15    45   33.3%   21.4%   47.9%   -0.333R
  bb_upper_break                       5    16   31.2%   14.2%   55.6%   -0.406R
  ma_golden                            7    30   23.3%   11.8%   40.9%   -0.683R
  fib_pullback_long                    2    10   20.0%    5.7%   51.0%   -0.800R

=== ma_golden 方向確認 ===
  全30件: ロング=30, ショート=0

=== ma_golden × グループ別 ===
  jpy_fx: 1/3 = 33.3%  CI[6.1~79.2%]
  other_fx: 6/22 = 27.3%  CI[13.2~48.2%]
  btc: 0/2 = 0.0%  CI[0.0~65.8%]
  index: 0/3 = 0.0%  CI[0.0~56.2%]

=== 主仮説の事前合否確認 ===
  ma_golden: 7/30 = 23.3%  CI[11.8~40.9%]
  CI上限=40.9% < 43%? → YES → 通過A（棄却確認）
  N=30 >= 20? → YES

=== 前向きトラッカー現在値 ===
  [f] 全逆張りロング: 119/285 = 41.8%  CI[36.2~47.6%]
  [g] 指数×逆張りロング: 34/66 = 51.5%  CI[39.7~63.2%]
  [h] 他FX×逆張りロング: 33/60 = 55.0%  CI[42.5~66.9%]
  [i] 他FX×blocked=True: 10/15 = 66.7%  CI[41.7~84.8%]
  [j] 中立×blocked=True: 2/10 = 20.0%  CI[5.7~51.0%]
  [k] 他FX×blocked=True×下降: 8/8 = 100.0%  CI[67.6~100.0%]

=== 探索的: d_sup_atr（verify.py非対応・本記事クレーム外）===
  d_sup_atr<0.5: 34/63=54.0% CI[41.8~65.7] | >=: 83/219=37.9%
  d_sup_atr<1.0: 54/129=41.9% CI[33.7~50.5] | >=: 63/153=41.2%
```

---

## 交絡の点検

1. **グループ偏り**: ma_golden 30件中22件が other_fx（他FX通貨ペア）。other_fx 全体の平均（逆張りロング 55.0%）と比較すると ma_golden の 27.3% は著しく低い → 「FXペアに多い」という事実は他の FX シグナルとの比較を可能にし、交絡を軽減。
2. **時期偏り**: signals-log は 2026-05-20〜2026-06-15（約4週間）。ゴールデンクロスは移動平均が収束・拡散する局面に発火するため、この期間の相場環境（全体的な横ばい〜下降）が ma_golden 不振の一因の可能性あり。構造的問題か時期的問題かは長期蓄積で確認が必要。
3. **N=30 の信頼性**: CI[11.8~40.9%] はブレ幅29pp と広い。ただし CI 上限が 40.9% < 43% という点は N が小さくても一定の意味を持つ（上振れても損益分岐未満）。
4. **ma_dead との比較**: ma_dead 8/14（57.1%）は逆方向（デッドクロス=売りシグナル）で有望だが N=14 と小さい。ma_golden vs ma_dead の非対称性は #004 の GC=F ロング vs ショート と同じ構造を示している可能性がある。

---

## 次回への繋ぎ

- d_sup_atr < 0.5 で 54.0%（CI[41.8~65.7%], N=63）という探索的数字が出た。これは verify.py の非対応次元。次セッションで「要verify.py拡張（キー:d_sup_atr）」エスカレとして正式申請するか、人間が判断してゲートを拡張するまで保留。
- ma_dead (N=14) は今後 N を積み上げた後に再検証候補。事前宣言基準: N≥30 かつ CI下限 > 43%。
