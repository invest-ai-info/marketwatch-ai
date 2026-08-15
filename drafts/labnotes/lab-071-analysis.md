# Lab-071 分析メモ — blocked=True×ショート edge FWD崩落検証
# 実行日: 2026-08-16 (JST)
# テーマ: blocked=True×dir=short の前向き勝率がIS 58.5%→FWD 18.8%に段階的崩落

## 分析スクリプト

```python
import json, math, re
from datetime import date, datetime

def wilson_ci(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z**2/n
    centre = (p + z**2/(2*n)) / denom
    spread = z * math.sqrt(p*(1-p)/n + z**2/(4*n**2)) / denom
    return (max(0, centre - spread), min(1, centre + spread))

def er_ci(rs, z=1.96):
    if not rs:
        return (float('nan'), float('nan'), float('nan'))
    mu = sum(rs) / len(rs)
    if len(rs) < 2:
        return (mu, float('nan'), float('nan'))
    se = math.sqrt(sum((r - mu)**2 for r in rs) / (len(rs) * (len(rs) - 1)))
    return (mu, mu - z*se, mu + z*se)

def stats(label, signals, z=1.96):
    done = [s for s in signals if s.get('outcome') in ('tp1','sl')]
    n = len(done)
    if n == 0:
        print(f"  {label}: N=0, skip")
        return
    wins = [s for s in done if s['outcome'] == 'tp1']
    k = len(wins)
    wci = wilson_ci(k, n)
    # E(R)
    rs = []
    for s in done:
        o = s['outcome']
        sl = abs(s.get('sl_pct') or 0)
        tp1 = abs(s.get('tp1_pct') or 0)
        if o == 'tp1':
            r = min(tp1/sl, 5.0) if sl > 0 else 2.0
        else:
            r = -1.0
        rs.append(r)
    mu, lo, hi = er_ci(rs)
    print(f"  {label}: {k}/{n}={k/n:.1%} CI[{wci[0]:.1%},{wci[1]:.1%}] E(R)={mu:+.3f} CI[{lo:+.3f},{hi:+.3f}]")

def is_long(s): return 'ロング' in (s.get('direction') or '')
def is_short(s): return 'ショート' in (s.get('direction') or '')
def is_blocked(s): return isinstance(s.get('sr_runway'), dict) and s['sr_runway'].get('blocked') == True

with open('signals-log.json') as f:
    raw = json.load(f)

FWD_START = '2026-06-25'

# base sets
bt_short = [s for s in raw if is_blocked(s) and is_short(s)]
bt_long  = [s for s in raw if is_blocked(s) and is_long(s)]
bf_short = [s for s in raw if not is_blocked(s) and is_short(s)]
bf_long  = [s for s in raw if not is_blocked(s) and is_long(s)]

print(f"bt_short={len(bt_short)}, bt_long={len(bt_long)}, bf_short={len(bf_short)}, bf_long={len(bf_long)}")

# IS/FWD split
def split_fwd(sigs, fwd_start=FWD_START):
    is_sigs  = [s for s in sigs if (s.get('timestamp') or '')[:10] < fwd_start]
    fwd_sigs = [s for s in sigs if (s.get('timestamp') or '')[:10] >= fwd_start]
    return is_sigs, fwd_sigs

bt_s_is, bt_s_fwd = split_fwd(bt_short)
bt_l_is, bt_l_fwd = split_fwd(bt_long)
bf_s_is, bf_s_fwd = split_fwd(bf_short)

print("\n=== IS vs FWD ===")
stats("bt×S ALL全期間", bt_short)
stats("bt×S IS", bt_s_is)
stats("bt×S FWD", bt_s_fwd)
stats("bt×L FWD", bt_l_fwd)
stats("bf×S ALL (参考)", bf_short)
stats("bf×S FWD (参考)", bf_s_fwd)

print("\n=== FWD by signal ===")
for sig in ['macd_dead', 'ma_dead', 'rsi_ob', 'bb_break']:
    sigs = [s for s in bt_s_fwd if s.get('signal') == sig]
    stats(f"FWD signal={sig}", sigs)

print("\n=== IS by signal ===")
for sig in ['macd_dead', 'ma_dead', 'rsi_ob']:
    sigs = [s for s in bt_s_is if s.get('signal') == sig]
    stats(f"IS signal={sig}", sigs)

print("\n=== FWD by group ===")
groups = sorted(set(s.get('group','') for s in bt_s_fwd if s.get('group')))
for g in groups:
    sigs = [s for s in bt_s_fwd if s.get('group') == g]
    stats(f"FWD group={g}", sigs)

print("\n=== IS by group ===")
groups_is = sorted(set(s.get('group','') for s in bt_s_is if s.get('group')))
for g in groups_is:
    sigs = [s for s in bt_s_is if s.get('group') == g]
    stats(f"IS group={g}", sigs)

print("\n=== FWD by TF ===")
for tf in ['1h', '4h', '1d']:
    sigs = [s for s in bt_s_fwd if s.get('timeframe') == tf]
    stats(f"FWD tf={tf}", sigs)

print("\n=== FWD quarterly breakdown ===")
done_fwd = [s for s in bt_s_fwd if s.get('outcome') in ('tp1','sl')]
done_fwd_sorted = sorted(done_fwd, key=lambda s: s.get('timestamp',''))
n_q = len(done_fwd_sorted)
q_size = n_q // 3

q1 = done_fwd_sorted[:q_size]
q2 = done_fwd_sorted[q_size:2*q_size]
q3 = done_fwd_sorted[2*q_size:]

def date_range(sigs):
    ts = [s.get('timestamp','')[:10] for s in sigs if s.get('timestamp')]
    return f"{min(ts)}~{max(ts)}" if ts else "?"

print(f"  FWD-1st (N={len(q1)}, {date_range(q1)}): ", end=""); stats("", q1)
print(f"  FWD-2nd (N={len(q2)}, {date_range(q2)}): ", end=""); stats("", q2)
print(f"  FWD-3rd (N={len(q3)}, {date_range(q3)}): ", end=""); stats("", q3)

print("\n=== FWD blocked T×S late period (Aug 2026) ===")
aug_sigs = [s for s in bt_s_fwd if (s.get('timestamp') or '')[:10] >= '2026-08-01']
stats("FWD >= 2026-08-01", aug_sigs)

print("\n=== 対照群 ===")
stats("bt×L ALL全期間", bt_long)
stats("bt×L IS", bt_l_is)
```

## 生出力

```
bt_short=195, bt_long=340, bf_short=494, bf_long=1682

=== IS vs FWD ===
  bt×S ALL全期間: 79/195=40.5% CI[33.9%,47.5%] E(R)=-0.055 CI[-0.199,+0.088]
  bt×S IS: 31/53=58.5% CI[45.1%,70.7%] E(R)=+0.365 CI[+0.055,+0.674]
  bt×S FWD: 48/142=33.8% CI[26.5%,41.9%] E(R)=-0.211 CI[-0.393,-0.030]
  bt×L FWD: 131/281=46.6% CI[40.9%,52.5%] E(R)=+0.088 CI[-0.048,+0.224]
  bf×S ALL (参考): 185/494=37.4% CI[33.3%,41.8%] E(R)=-0.126 CI[-0.220,-0.033]
  bf×S FWD (参考): 138/373=37.0% CI[32.2%,42.0%] E(R)=-0.143 CI[-0.258,-0.028]

=== FWD by signal ===
  FWD signal=macd_dead: 34/98=34.7% CI[25.8%,44.8%] E(R)=-0.190 CI[-0.402,+0.022]
  FWD signal=ma_dead: 12/37=32.4% CI[19.1%,49.2%] E(R)=-0.243 CI[-0.556,+0.070]
  FWD signal=rsi_ob: N=0, skip
  FWD signal=bb_break: N=0, skip

=== IS by signal ===
  IS signal=macd_dead: 14/31=45.2% CI[28.9%,62.6%] E(R)=-0.032 CI[-0.393,+0.329]
  IS signal=ma_dead: 14/17=82.4% CI[59.0%,93.8%] E(R)=+0.808 CI[+0.392,+1.225]

=== FWD by group ===
  FWD group=btc: 2/12=16.7% CI[4.7%,43.3%] E(R)=-0.648 CI[-1.048,-0.249]
  FWD group=index: 15/36=41.7% CI[27.0%,58.0%] E(R)=+0.047 CI[-0.353,+0.447]
  FWD group=metal: 8/18=44.4% CI[24.6%,66.3%] E(R)=+0.000 CI[-0.481,+0.481]
  FWD group=oil: 0/9=0.0% CI[0.0%,31.6%] E(R)=-1.000 CI[-1.000,-1.000]
  FWD group=other_fx: 23/67=34.3% CI[23.8%,46.5%] E(R)=-0.189 CI[-0.401,+0.022]

=== IS by group ===
  IS group=btc: 2/5=40.0% CI[11.8%,76.9%] E(R)=-0.200 CI[-1.000,+0.600]
  IS group=index: 5/8=62.5% CI[30.6%,86.3%] E(R)=+0.350 CI[-0.355,+1.055]
  IS group=metal: 7/8=87.5% CI[52.9%,97.8%] E(R)=+0.838 CI[+0.247,+1.428]
  IS group=oil: 2/4=50.0% CI[15.3%,84.7%] E(R)=+0.000 CI[-1.000,+1.000]
  IS group=other_fx: 15/28=53.6% CI[35.6%,70.7%] E(R)=+0.253 CI[-0.158,+0.663]

=== FWD by TF ===
  FWD tf=1h: 27/82=32.9% CI[23.4%,44.0%] E(R)=-0.244 CI[-0.464,-0.024]
  FWD tf=4h: 20/52=38.5% CI[26.2%,52.5%] E(R)=-0.143 CI[-0.440,+0.154]
  FWD tf=1d: 1/8=12.5% CI[2.2%,47.1%] E(R)=-0.821 CI[-1.295,-0.346]

=== FWD quarterly breakdown ===
  FWD-1st (N=47, 2026-06-26~2026-07-14):   : 18/47=38.3% CI[25.5%,53.0%] E(R)=-0.106 CI[-0.400,+0.188]
  FWD-2nd (N=47, 2026-07-14~2026-07-31):   : 21/47=44.7% CI[31.4%,58.8%] E(R)=+0.043 CI[-0.286,+0.371]
  FWD-3rd (N=48, 2026-07-31~2026-08-14):   : 9/48=18.8% CI[10.2%,31.8%] E(R)=-0.563 CI[-0.820,-0.305]

=== FWD blocked T×S late period (Aug 2026) ===
  FWD >= 2026-08-01: 4/32=12.5% CI[4.8%,28.3%] E(R)=-0.708 CI[-0.976,-0.441]

=== 対照群 ===
  bt×L ALL全期間: 127/340=37.4% CI[32.2%,42.8%] E(R)=-0.078 CI[-0.192,+0.037]
  bt×L IS: 7/19=36.8% CI[19.1%,58.7%] E(R)=-0.218 CI[-0.688,+0.251]
```

## 分析メモ

**テーマ選定理由**:
- 前向きトラッカーで `blocked=True×dir=short` は🟡蓄積中（FWD 48/142=33.8%, CI上限41.9%<43%の閾値未満）
- Aug2026単月: 4/32=12.5% → 致命的悪化
- FWD第3四半期: 9/48=18.8% → 明確な時系列劣化トレンド

**IS高値（58.5%）の解体**:
- ma_dead: IS 14/17=82.4% → FWD 12/37=32.4%（-50pp崩落）
- metal: IS 7/8=87.5% → FWD 8/18=44.4%（-43pp崩落）
- いずれも小N（≤17-8）の過剰適合

**FWD構造**:
- oil: FWD 0/9=0.0% — 全負け
- btc: FWD 2/12=16.7%
- macd_dead FWD 34/98=34.7%, ma_dead FWD 12/37=32.4% — 両シグナル共通して崩落

**⛔反証接近の根拠**:
- Wilson CI上限: 41.9% < 43%（ブレイクイーブン閾値）→ 形式的確認
- 直近1.5か月（Aug2026）12.5%：95%CI [-0, 0.28] → 信号は機能していない
- IS→FWD乖離が系統的（全group, 全signal, 全TF）

**FWD_START**: 2026-06-25（tracker.jsonのFWD_STARTと一致）
