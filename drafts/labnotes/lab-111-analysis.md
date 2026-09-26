# #111 分析メモ — 日足 −2σタッチ買い × 出口の相性（探索期間）

## 基本情報
- 基準日: 2026-09-27（JST）
- 入口: bb_lower_touch（ボリンジャーバンドの下の線（−2σ）タッチ）
- 方向: long（買い）
- 足: 1d（日足）
- 探索期間: 〜2026-09-25（exit-lab.json asof: 2026-09-26, is_until: 2026-09-25）
- 前向き: 2026-09-25〜（まだ蓄積中）

## exit-lab.json から読み取った主要数値

### 全18銘柄（group=all）
| 損切り | 利確 | 1回あたり平均R | いまの方式との差 | 件数 | 旗 |
|---|---|---|---|---|---|
| ATR1.5倍（いまの方式） | ATRの2倍（いまの方式） | -0.06 | — | 4095 | — |
| ATR1.5倍 | 利確なし | +0.21 | +0.28 | 4071 | — |
| ATR1.5倍 | RSI70超え | +0.08 | +0.15 | 4080 | — |
| 節目安値 | 利確なし | +0.20 | +0.26 | 4082 | — |
| シャンデリア | 損切り幅の2倍 | -0.43 | -0.24 | 1041 | 🚩 |
| シャンデリア | 損切り幅の3倍 | -0.46 | -0.27 | 1041 | 🚩 |
| タートル型 | 損切り幅の2倍 | -0.25 | -0.13 | 2996 | 🚩 |

### FX9銘柄（group=fx）
| 損切り | 利確 | 1回あたり平均R | いまの方式との差 | 件数 | 旗 |
|---|---|---|---|---|---|
| ATR1.5倍（いまの方式） | ATRの2倍（いまの方式） | -0.16 | — | 2320 | — |
| シャンデリア | ATRの2倍 | -0.58 | -0.36 | 754 | 🚩 |
| シャンデリア | 損切り幅の2倍 | -0.55 | -0.34 | 754 | 🚩 |
| シャンデリア | 損切り幅の3倍 | -0.59 | -0.37 | 754 | 🚩 |
| シャンデリア | 節目高値 | -0.58 | -0.36 | 754 | 🚩 |
| シャンデリア | 半分1Rで建値へ | -0.57 | -0.35 | 754 | 🚩 |

### 株価指数（group=index）
| 損切り | 利確 | 1回あたり平均R | 件数 |
|---|---|---|---|
| ATR1.5倍（いまの方式） | ATRの2倍（いまの方式） | +0.11 | 1099 |
| ATR1.5倍 | 利確なし | +0.46 | 1088 |
| シャンデリア | 損切り幅の2倍 | -0.03 | 222 |

### コモディティ（group=commodity: 金・銀・原油）
| 損切り | 利確 | 1回あたり平均R | 件数 |
|---|---|---|---|
| ATR1.5倍（いまの方式） | ATRの2倍（いまの方式） | -0.02 | 519 |
| ATR1.5倍 | 利確なし | +0.56 | 516 |

## シャンデリア早期・後期の一貫性（chandelier/rr2, all）
- 早期: vs_base=-0.29R（n=430）→ マイナス
- 後期: vs_base=-0.20R（n=609）→ マイナス
- 両期間で同じ方向に出た → 「目立つ」の旗が立つ条件を満たす

## 「目立つ」の物差しの解釈
- 物差し: 癖のない値動き（作り物）5回で平均0.2マス偶然が出る（旧方式1.2マスから改善）
- 今回の旗: 全18銘柄3マス + FX5マス = 計8マス
- 8マスは偶然の平均0.2マスよりずっと多い → 偶然だけでは説明しにくい
- ただし、FX5マスはすべてシャンデリアという「同じパターン」なので独立ではない
- 前向き（2026-09-25〜）でまだ確認できていない

## 前向き（flagged_forward）
7件が前向きで追跡中（all×chandelier/rr2, all×chandelier/rr3, fx×chandelier各種）
まだデータが入っていない（fwd={}）

## スクリプト

```python
import json

d = json.load(open('exit-lab.json'))
cells = d.get('cells', [])

def get_cell(entry, side, tf, group, sl, tp, period='is'):
    for c in cells:
        if (c.get('entry') == entry and c.get('side') == side and 
            c.get('tf') == tf and c.get('group') == group and
            c.get('sl') == sl and c.get('tp') == tp and c.get('period') == period):
            return c
    return None

entry, side, tf = 'bb_lower_touch', 'long', '1d'

# 主要セル抽出
base = get_cell(entry, side, tf, 'all', 'atr', 'atr2')
print(f"BASE: n={base['n']}, avg={base['avg']:.3f}, win={base['win']:.3f}")

for (sl, tp, grp) in [
    ('atr', 'none', 'all'), ('swing', 'none', 'all'), ('atr', 'rsi70', 'all'),
    ('chandelier', 'rr2', 'all'), ('chandelier', 'rr3', 'all'), ('turtle', 'rr2', 'all'),
    ('chandelier', 'atr2', 'fx'), ('chandelier', 'rr2', 'fx'),
    ('atr', 'atr2', 'index'), ('atr', 'none', 'index'),
    ('atr', 'atr2', 'commodity'), ('atr', 'none', 'commodity'),
]:
    c = get_cell(entry, side, tf, grp, sl, tp)
    if c and c.get('n', 0) > 0:
        vs = c.get('vs_base', {})
        early = c.get('vs_base_early', {})
        late = c.get('vs_base_late', {})
        print(f"{grp} {sl}/{tp}: avg={c['avg']:.3f}, n={c['n']}, vs={vs.get('avg','N/A'):.3f}, bonf={c.get('bonf')}")
        if early.get('n'):
            print(f"  early={early.get('avg','N/A'):.3f}(n={early.get('n')}), late={late.get('avg','N/A'):.3f}(n={late.get('n')})")
```

## 生出力（主要セル）
BASE: n=4095, avg=-0.064, win=0.411
all atr/none: avg=0.210, n=4071, vs=0.283, bonf=False
all swing/none: avg=0.195, n=4082, vs=0.264, bonf=False
all atr/rsi70: avg=0.080, n=4080, vs=0.149, bonf=False
all chandelier/rr2: avg=-0.431, n=1041, vs=-0.237, bonf=True
  early=-0.287(n=430), late=-0.202(n=609)
all chandelier/rr3: avg=-0.464, n=1041, vs=-0.270, bonf=True
  early=-0.393(n=430), late=-0.183(n=609)
all turtle/rr2: avg=-0.248, n=2996, vs=-0.127, bonf=True
fx chandelier/atr2: avg=-0.575, n=754, vs=-0.361, bonf=True
fx chandelier/rr2: avg=-0.551, n=754, vs=-0.337, bonf=True
index atr/atr2: avg=0.113, n=1099
index atr/none: avg=0.460, n=1088, vs=0.359, bonf=False
commodity atr/atr2: avg=-0.023, n=519
commodity atr/none: avg=0.563, n=516, vs=0.593, bonf=False
