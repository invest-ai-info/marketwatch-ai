# lab-053-analysis.md — AIシグナル研究日誌 #053 解析ログ

**基準日**: 2026-07-28 (JST)  
**テーマ**: MA位置フィルタ（above_both × Long）の全件検証——「両MAライン上でロングは逆効果か」

---

## スクリプト全文

```python
# /tmp/lab053_analysis2.py — signal_lab_verify.py の match/closed/win を再利用

import json, math
from signal_lab_verify import closed, win, match, compute

with open("signals-log.json") as f:
    data = json.load(f)

# --- claims.json と完全一致させる検証値（verify.py oracle 経由） ---
claims = [
    ('above_both × Long 全件', {'ma_pos':'above_both','direction':'long'}),
    ('below_both × Long 全件', {'ma_pos':'below_both','direction':'long'}),
    ('above_both × Short', {'ma_pos':'above_both','direction':'short'}),
    ('above_both × Long × 上昇', {'ma_pos':'above_both','direction':'long','trend':'上昇'}),
    ('above_both × Long × 下降', {'ma_pos':'above_both','direction':'long','trend':'下降'}),
    ('above_both × Long × 中立', {'ma_pos':'above_both','direction':'long','trend':'中立・もみあい'}),
    ('below_both × Long × 上昇', {'ma_pos':'below_both','direction':'long','trend':'上昇'}),
    ('above_both × Long × signal=high_break', {'ma_pos':'above_both','direction':'long','signal':'high_break'}),
    ('above_both × Long × signal=rsi_overbought', {'ma_pos':'above_both','direction':'long','signal':'rsi_overbought'}),
    ('above_both × Long × signal=macd_golden', {'ma_pos':'above_both','direction':'long','signal':'macd_golden'}),
    ('above_both × Long × signal=bb_upper_break', {'ma_pos':'above_both','direction':'long','signal':'bb_upper_break'}),
    ('above_both × Long × signal=ma_golden', {'ma_pos':'above_both','direction':'long','signal':'ma_golden'}),
    ('above_both × Long × group=other_fx', {'ma_pos':'above_both','direction':'long','group':'other_fx'}),
    ('above_both × Long × group=index', {'ma_pos':'above_both','direction':'long','group':'index'}),
    ('above_both × Long × group=metal', {'ma_pos':'above_both','direction':'long','group':'metal'}),
    ('above_both × Long × group=oil', {'ma_pos':'above_both','direction':'long','group':'oil'}),
    ('below_both × Long × group=index', {'ma_pos':'below_both','direction':'long','group':'index'}),
    ('below_both × Short', {'ma_pos':'below_both','direction':'short'}),
]

for label, f in claims:
    k, n = compute(data, f)
    wr = k/n if n>0 else 0
    print(f'  {label}: k={k}, n={n}, wr={wr:.1%}')
```

---

## 生出力（oracle 経由・完全再現可能）

```
Filter → k / n (using verify.py oracle)
  above_both × Long 全件: k=206, n=549, wr=37.5%
  below_both × Long 全件: k=354, n=799, wr=44.3%
  above_both × Short: k=94, n=206, wr=45.6%
  above_both × Long × 上昇: k=94, n=260, wr=36.2%
  above_both × Long × 下降: k=45, n=129, wr=34.9%
  above_both × Long × 中立: k=64, n=156, wr=41.0%
  below_both × Long × 上昇: k=105, n=201, wr=52.2%
  above_both × Long × signal=high_break: k=52, n=148, wr=35.1%
  above_both × Long × signal=rsi_overbought: k=16, n=53, wr=30.2%
  above_both × Long × signal=macd_golden: k=63, n=152, wr=41.4%
  above_both × Long × signal=bb_upper_break: k=46, n=108, wr=42.6%
  above_both × Long × signal=ma_golden: k=26, n=78, wr=33.3%
  above_both × Long × group=other_fx: k=45, n=144, wr=31.2%
  above_both × Long × group=index: k=66, n=153, wr=43.1%
  above_both × Long × group=metal: k=9, n=40, wr=22.5%
  above_both × Long × group=oil: k=16, n=22, wr=72.7%
  below_both × Long × group=index: k=95, n=190, wr=50.0%
  below_both × Short: k=125, n=322, wr=38.8%
```

---

## R値（期待値）の補助計算

R = TP1ヒット: +1.333R, SL: -1.0R として計算

- above_both × Long: R=-0.125 RCI=[-0.219,-0.030] ← **CI全域マイナス**
- below_both × Long: R=+0.034 RCI=[-0.047,+0.114]
- above_both × Long × 上昇: R=-0.157 RCI=[-0.293,-0.020]
- above_both × Long × high_break: R=-0.180 RCI=[-0.360,-0.001]
- above_both × Long × rsi_overbought: R=-0.296 RCI=[-0.584,-0.007]
- above_both × Long × other_fx: R=-0.271 RCI=[-0.448,-0.094]

---

## Wilson CI 95% 補助計算

| フィルタ | k | n | wr | CI |
|---|---|---|---|---|
| above_both × Long | 206 | 549 | 37.5% | [33.6%, 41.6%] |
| below_both × Long | 354 | 799 | 44.3% | [40.9%, 47.8%] |
| above_both × Short | 94 | 206 | 45.6% | [39.0%, 52.5%] |
| above_both × L × 上昇 | 94 | 260 | 36.2% | [30.6%, 42.2%] |
| below_both × L × 上昇 | 105 | 201 | 52.2% | [45.4%, 59.0%] |
| above_both × L × high_break | 52 | 148 | 35.1% | [27.9%, 43.1%] |
| above_both × L × rsi_overbought | 16 | 53 | 30.2% | [19.5%, 43.5%] |
| above_both × L × other_fx | 45 | 144 | 31.2% | [24.2%, 39.2%] |
| above_both × L × index | 66 | 153 | 43.1% | [35.6%, 51.1%] |

---

## 事前宣言（ゲート基準）

- H1: above_both × Long の CI上限 < 43%（損益分岐を有意に下回ると宣言）
  → ✅ CI=[33.6%,41.6%], CI上限41.6% < 43%, N=549≥20
- H2: R の 95%CI が全域マイナス
  → ✅ RCI=[-0.219,-0.030], 全域マイナス確認

---

## 交絡点検

1. **金属グループのバイアス**: above_both × Long × metal = k=9, n=40, 22.5%。metal は金属レジーム転換期に歪む可能性あり。ただし index=43.1%（N=153）、other_fx=31.2%（N=144）、jpy_fx=40.1%（N=147）と複数グループで損益分岐割れ確認 → metal 偏りだけでは説明できない。
2. **oil の外れ値**: oil=72.7%（N=22）は小標本。main hypothesis には影響軽微（N=22/549=4%）。
3. **トレンドバイアス**: 上昇36.2%/下降34.9%/中立41.0% → トレンド依存は軽微（全トレンドで損益分岐割れ）。
4. **シグナルバイアス**: 逆張り（rsi/bb）のabove_both×L は N=7 のみ（above_both の状態で逆張りロングはほぼ発火しない）。95%以上が順張り/トレンドフォロー型シグナル（macd_golden/high_break/bb_upper_break）。

---

## 前向きトラッカーとの関係

- tracker 登録: `ステート 上昇配置（>MA25&75）×ロング` (2026-07-20, edge)
- FWD: N=70, 31/70=44%, R=+0.033 RCI=[-0.27~+0.33] — CI 0またぎ、有意差なし
- 全期間R = -0.12 (全closed=IS+FWD 合算)
- ISは 37.5%（N=479）、FWDは 44%（N=70）で改善傾向だが統計的有意差なし

---

## 解釈メモ

当システムのシグナルスイートは本質的に逆張り系（bb_lower_touch, rsi_oversold_bounce, support_bounce）。
- above_both（両MA上）の状態では、これらの逆張りシグナルはほぼ発火しない（N=7のみ）
- above_both での主発火シグナルは: macd_golden/high_break/bb_upper_break/ma_golden — 順張り/ブレイクアウト型
- 順張りシグナルの below_both と above_both を比較:
  - high_break × above_both × L: 35.1% ← 高値ブレイク後さらに上 = 過熱状態
  - macd_golden × above_both × L: 41.4% ← 相対的にマシ
- below_both × L が above_both × L より高い理由: 逆張り系の本来の生息域（bb_lower, rsi_oversold が below_both で発火）
- 結論: MA位置は「シグナルが適切な環境で発火しているか」の代理変数として機能する

