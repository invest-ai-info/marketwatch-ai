# lab-128 分析メモ — rsi_oversold_edge 定点観測（前向き422回）

日付: 2026-10-20 (JST)
仮説ID: rsi_oversold_edge
テーマ: RSIが30を下回ったとき逆張りで買うと勝ちやすいか（前向き422回の現在地）

## 仮説

RSI（相対力指数）が30未満で primary_signal=rsi_oversold_bounce（売られすぎ反発買い）が発火したとき、
ATRベースのTP1（損切り幅の1.33倍）に到達する割合は、全ロングシグナルのベースライン（約43%）を上回る。

登録日: 2026-06-16（rsi_oversold_edge）
IS/FWD 区切り: 2026-06-17（registered_at の翌日）

## スクリプト

```python
import json, math, sys, datetime
sys.path.insert(0, '.')
import signal_lab_verify as v

with open('signals-log.json') as f:
    data = json.load(f)
signals = data.get('signals', data) if isinstance(data, dict) else data

asof_dt = datetime.datetime.fromisoformat('2026-10-20T06:10:00+09:00')
filtered, fails, dropped = v.apply_asof(signals, asof_dt, '2026-10-20')

FWD_FROM = '2026-06-17'

k_is, n_is = v.compute(filtered, {'signal': 'rsi_oversold_bounce', 'fired_before': FWD_FROM})
k_fwd, n_fwd = v.compute(filtered, {'signal': 'rsi_oversold_bounce', 'fired_from': FWD_FROM})
k_base, n_base = v.compute(filtered, {'direction': 'long', 'fired_from': FWD_FROM})

def avg_r_ci(rows):
    rs = []
    for s in rows:
        out = s.get('outcome','')
        if out == 'tp1': rs.append(1.33)
        elif out == 'tp2': rs.append(2.0)
        elif out == 'sl': rs.append(-1.0)
    if len(rs) < 2: return 0, 0, 0
    avg = sum(rs)/len(rs)
    var = sum((x-avg)**2 for x in rs)/(len(rs)-1)
    se = math.sqrt(var/len(rs))
    return round(avg,3), round(avg-1.96*se,3), round(avg+1.96*se,3)

fwd_rows = [d for d in filtered if v.closed(d) and v.match(d, {'signal': 'rsi_oversold_bounce', 'fired_from': FWD_FROM})]
is_rows  = [d for d in filtered if v.closed(d) and v.match(d, {'signal': 'rsi_oversold_bounce', 'fired_before': FWD_FROM})]

avg_f, rci_lo_f, rci_hi_f = avg_r_ci(fwd_rows)
avg_i, _, _ = avg_r_ci(is_rows)

lo_f, hi_f = v.wilson(k_fwd, n_fwd)
lo_i, hi_i = v.wilson(k_is, n_is)
lo_b, hi_b = v.wilson(k_base, n_base)

print(f'IS : k={k_is} n={n_is} win={100*k_is/n_is:.1f}% CI=[{lo_i:.1f}%~{hi_i:.1f}%] avgR={avg_i:+.3f}')
print(f'FWD: k={k_fwd} n={n_fwd} win={100*k_fwd/n_fwd:.1f}% CI=[{lo_f:.1f}%~{hi_f:.1f}%] avgR={avg_f:+.3f} R-CI=[{rci_lo_f:+.3f}~{rci_hi_f:+.3f}]')
print(f'Base(FWD long): k={k_base} n={n_base} win={100*k_base/n_base:.1f}% CI=[{lo_b:.1f}%~{hi_b:.1f}%]')
```

## 生出力

```
After asof: 6640 signals (dropped 0)
IS : k=52 n=133 win=39.1% CI=[31.2%~47.6%] avgR=-0.089
FWD: k=209 n=422 win=49.5% CI=[44.8%~54.3%] avgR=+0.154 R-CI=[+0.043~+0.265]
Base(FWD long): k=1446 n=3362 win=43.0% CI=[41.3%~44.7%]
```

## 解釈

- IS（事前登録前）: 39.1% → ベースライン43.0%を下回る（後付けに利用しなかった根拠）
- FWD（前向き）: 49.5% → ベースラインを6.5ポイント上回る
- Wilson 95%CI 下限 44.8% > 43.0%（ベースライン超え確認）
- R-CI: [+0.043~+0.265] → **両端がプラス** = 新しいマイルストーン（平均Rの95%CI下限がゼロ超え）
- status: tracking（promote_strikes=1：昇格条件を一度は満たしたが継続判定なし）

## トラッカー履歴の補足

tracker.jsonのhistoryより(R-CI下限の推移):
- 2026-10-01: rci_lo=+0.018 (プラス)
- 2026-10-09: rci_lo=-0.003 (一時マイナス)
- 2026-10-20: rci_lo=+0.043 (my固定R計算) / tracker上=0.0 (ATRスケール)
  → 両手法でゼロ付近をうろうろ → 昇格判定の境界線上

## 本日の判定

✅ 定点観測（前向き422回・R-CI下限プラス到達） → 題材採用
