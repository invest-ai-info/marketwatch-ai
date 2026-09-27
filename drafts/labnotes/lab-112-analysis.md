# lab-112 分析ノート — 逆張り買い・足別比較

**記事番号**: 112  
**作成日**: 2026-09-28  
**種別**: 定点観測のみ（昇格/反証なし、FDR候補なし）

## 調査スクリプト

```python
import json, sys
sys.path.insert(0, '.')
from signal_lab_verify import compute, wilson

with open('signals-log.json', encoding='utf-8') as f:
    data = json.load(f)

# 全体ベースライン
k_all, n_all = compute(data, {})
lo, hi = wilson(k_all, n_all)
print(f"全体: {k_all}/{n_all} = {k_all/n_all*100:.1f}%, CI=[{lo:.1f}%〜{hi:.1f}%]")

# 逆張り買い 足別
for tf in ['1h', '4h', '1d']:
    k, n = compute(data, {'reversal_long': True, 'tf': tf})
    lo, hi = wilson(k, n)
    print(f"reversal_long + tf={tf}: {k}/{n} = {k/n*100:.1f}%, CI=[{lo:.1f}%〜{hi:.1f}%]")

# 日足 勝ちの内訳
from signal_lab_verify import closed, win
rev_1d = [d for d in data if closed(d) and d.get('direction','').startswith('ロング') and d.get('primary_signal') in ('rsi_oversold_bounce','bb_lower_touch') and d.get('tf','') == '1d']
tp1 = sum(1 for d in rev_1d if d.get('outcome') == 'tp1')
tp2 = sum(1 for d in rev_1d if d.get('outcome') == 'tp2')
sl  = sum(1 for d in rev_1d if d.get('outcome') == 'sl')
avg_r = (tp1 * 1.33 + tp2 * 2.0 - sl * 1.0) / len(rev_1d) if rev_1d else 0
print(f"日足内訳: TP1={tp1}, TP2={tp2}, SL={sl}, avg_R={avg_r:.2f}")
```

## 生出力

```
全体: 2059/4786 = 43.0%, CI=[41.6%〜44.4%]
reversal_long + tf=1h: 397/897 = 44.3%, CI=[41.0%〜47.5%]
reversal_long + tf=4h: 215/491 = 43.8%, CI=[39.5%〜48.2%]
reversal_long + tf=1d: 33/57 = 57.9%, CI=[45.0%〜69.8%]
日足内訳: TP1=33, TP2=0, SL=24, avg_R=+0.35
```

## 考察

- 1時間足・4時間足は全体ベースラインとほぼ同じ（約44%）。偶然のぶれの幅がベースラインをまたいでおり、差があるとは言えない。
- 日足は57.9%と高いが、57回と少ない。CIが45%〜70%と非常に広く、「足が長いほど勝ちやすい」の結論を出すには回数不足。
- 前向きトラッカーで「逆張り買い全般（日足のみ）」が2025-09-10から追跡中。24回/14勝(58%)、まだ蓄積中（基準80回）。

## 今日の選択理由

- 昇格/反証: なし
- FDR新候補: sweep 0件
- 読者質問: なし
- 出口の相性の回: 月曜かつ直近6日に #111（出口-1d-bb_lower_touch-long）があるためスキップ
- → 定点観測のみ → 「足別の逆張り比較」を選択
