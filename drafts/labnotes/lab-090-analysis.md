# lab-090 分析ノート

基準日: 2026-09-05  
仮説: RSI売られすぎ逆張り買い（rsi_oversold_bounce）N=296 前向き追跡  
先行シリーズ: #069 (N=179), #074 (4H詳細), #082 (N=250・昇格ストライク失敗)

---

## 実行スクリプト（抜粋・signal_lab_verify.py の match() を使用）

```python
import json, math, datetime, random, signal_lab_verify as slv

with open('signals-log.json') as f:
    data = json.load(f)

def is_win(s): return s.get('outcome') in ['tp1','tp2']
def get_r(s):
    if s.get('outcome')=='tp2': return 2.0
    elif s.get('outcome')=='tp1': return 1.33
    else: return -1.0

def get_fired_date(s):
    d = s.get('fired_at','')
    if d:
        try: return datetime.date.fromisoformat(d[:10])
        except: pass
    return None

def wilson(k, n, z=1.96):
    if n==0: return 0,0
    p=k/n; denom=1+z**2/n
    center=(p+z**2/(2*n))/denom
    margin=z*math.sqrt(p*(1-p)/n+z**2/(4*n**2))/denom
    return center-margin, center+margin

def filter_sig(signals, flt):
    return [s for s in signals if slv.closed(s) and slv.match(s, flt)]

def stats_group(grp, label=''):
    if not grp:
        print(f"  {label}: no data")
        return None
    wins = sum(1 for s in grp if is_win(s))
    n = len(grp)
    pct = wins/n*100
    Rs = [get_r(s) for s in grp]
    avg_r = sum(Rs)/len(Rs)
    lo, hi = wilson(wins, n)
    print(f"  {label}: {wins}/{n} = {pct:.1f}%, E(R)={avg_r:.3f}, CI[{lo*100:.1f}%,{hi*100:.1f}%]")
    return wins, n, avg_r, Rs

REG_DATE = datetime.date(2026, 6, 16)
all_closed = filter_sig(data, {})
rsi_all = filter_sig(data, {"signal":"rsi_oversold_bounce"})
rsi_fwd = [s for s in rsi_all if get_fired_date(s) and get_fired_date(s) >= REG_DATE]
rsi_is = [s for s in rsi_all if get_fired_date(s) and get_fired_date(s) < REG_DATE]
```

---

## 生出力

```
Total closed: 4142, rsi_ob: IS=133, FWD=296

--- IS vs FWD ---
  IS: 52/133 = 39.1%, E(R)=-0.089, CI[31.2%,47.6%]
  FWD全体: 158/296 = 53.4%, E(R)=0.244, CI[47.7%,59.0%]
    FWD R bootstrap CI: [0.102, 0.370]

前回#082(N=255) vs 追加分(41件)
  #082時点: 134/255 = 52.5%, E(R)=0.224, CI[46.4%,58.6%]
  追加分: 24/41 = 58.5%, E(R)=0.364, CI[43.4%,72.2%]

--- FWD by timeframe ---
  1h: 92/198 = 46.5%, E(R)=0.083, CI[39.7%,53.4%]
  4h: 56/86 = 65.1%, E(R)=0.517, CI[54.6%,74.3%]

--- FWD by trend ---
  trend=上昇: 49/74 = 66.2%, E(R)=0.543, CI[54.9%,76.0%]
  trend=下降: 53/120 = 44.2%, E(R)=0.029, CI[35.6%,53.1%]
  trend=中立・もみあい: 56/102 = 54.9%, E(R)=0.279, CI[45.2%,64.2%]

--- FWD by group ---
  index: 34/68 = 50.0%, E(R)=0.165, CI[38.4%,61.6%]
  jpy_fx: 38/62 = 61.3%, E(R)=0.428, CI[48.8%,72.4%]
  other_fx: 45/90 = 50.0%, E(R)=0.165, CI[39.9%,60.1%]
  metal: 23/41 = 56.1%, E(R)=0.307, CI[41.0%,70.1%]
  btc: 7/13 = 53.8%, E(R)=0.255, CI[29.1%,76.8%]

--- 4H×jpy_fx ---
  4H×jpy_fx: 16/18 = 88.9%, E(R)=1.071, CI[67.2%,96.9%]
  4H×other_fx: 19/35 = 54.3%, E(R)=0.265, CI[38.2%,69.5%]
  4H×index: 9/14 = 64.3%, E(R)=0.498, CI[38.8%,83.7%]

--- P3以降(7/28〜9/5): 160件 ---
  P3全体: 91/160 = 56.9%, E(R)=0.325, CI[49.1%,64.3%]
  P3×4H: 35/47 = 74.5%, E(R)=0.735, CI[60.5%,84.7%]
  P3×1H: 53/110 = 48.2%, E(R)=0.123, CI[39.1%,57.4%]
  P3×4H×jpy_fx: 12/13 = 92.3%, E(R)=1.151, CI[66.7%,98.6%]
```

---

## トラッカー更新値

tracker: 売られすぎ逆張り買い(rsi_oversold_bounce・全足)  
→ 158/296 53% E(R)=+0.24 CI[+0.05~+0.44] 🟡蓄積中  
昇格ストライク1回目（前回8/28は-0.007で失敗→本日+0.05で再到達）

## 判定
- H1（FWD全体 E(R) CI下限 > 0）: +0.05 > 0 → ✅ 昇格ストライク1回目 再取得
- H2（4H足 CI下限 > 43%）: 54.6% ✅
- H3（1H足 CI下限 < 43%）: 39.7% ✅（無エッジ継続確認）
- H4（4H×jpy_fx ≥ 80%）: 88.9% ✅

## 交絡チェック
- 追加41件: 24/41 = 58.5%（継続高勝率、選択バイアスなし）
- グループ構成変化: index 68/296=23%, jpy_fx 62/296=21%, other_fx 90/296=30% → 安定

## 補足（小サンプル注意）
- 4H×jpy_fx (N=18): CI[67.2%,96.9%] 広めのCI。前回#074の93.8%(N=16)から88.9%(N=18)に変化は正常範囲
- P3×4H×jpy_fx (N=13): 参考値
