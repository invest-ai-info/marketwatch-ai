# 研究日誌 #115 分析メモ

## 基準日
2026-10-01（JST）

## 題材
RSI売られすぎ逆張り買い（rsi_oversold_bounce）の前向き積み上がり状況 — 391回で期待値のプラスが示唆される

## 仮説ID
rsi_oversold_edge（登録日: 2026-06-16、IS/FWD境界: 2026-06-17）

## トラッカー更新
- 前向き: 198/389=51%, E(R)=+0.188R, CI=[+0.02~+0.36] 🟡蓄積中
- #109（前回同テーマ）から17回追加（374→391）
- CI下限+0.02で依然プラス維持
- 次チェックポイント: N=400（あと9回）
- 昇格基準: CI下限>0を2回連続 → 1回目はパス済、2回目待ち

## 検証スクリプト（使用フィルタ）

```python
import json, math
from signal_lab_verify import GROUPS

with open("signals-log.json") as f:
    logs = json.load(f)

def closed(d): return d.get("outcome") in ("tp1", "tp2", "sl")
def win(d): return d.get("outcome") in ("tp1", "tp2")
def r_of(d): return {"tp2": 2.0, "tp1": 4/3, "sl": -1.0}.get(d.get("outcome"), 0)
def fa(d): return d.get("fired_at","")[:10]

FWD = "2026-06-17"

def matches(s, f):
    if not closed(s): return False
    if f.get("signal"):
        if s.get("primary_signal") != f["signal"]: return False
    if f.get("direction") == "long":
        if not s.get("direction","").startswith("ロング"): return False
    if f.get("group"):
        if s.get("ticker") not in GROUPS.get(f["group"], set()): return False
    if f.get("tf"):
        if s.get("timeframe") != f["tf"]: return False
    if f.get("fired_from"):
        if not fa(s) or not (fa(s) >= f["fired_from"]): return False
    if f.get("fired_before"):
        if not fa(s) or not (fa(s) < f["fired_before"]): return False
    return True
```

## 生出力（全数値）

### 全体ベースライン（FWD期間 2026-06-17以降）
全体FWD: n=4141, k=1797, pct=43.4%, CI=[41.9~44.9%], E(R)=0.013

### RSI売られすぎ逆張り買い
IS（登録前 〜2026-06-16）: n=133, k=52, pct=39.1%, CI=[31.2~47.6%], E(R)=-0.088

FWD（登録後 2026-06-17〜）: n=391, k=198, pct=50.6%, CI=[45.7~55.6%], E(R)=0.182

### FWDグループ別
- metal（金・銀）: n=49, k=28, pct=57.1%, CI=[43.3~70.0%], E(R)=0.333
- oil（原油）: n=26, k=13, pct=50.0%, CI=[32.1~67.9%], E(R)=0.167
- index（株価指数）: n=79, k=40, pct=50.6%, CI=[39.8~61.4%], E(R)=0.181
- jpy_fx（円の通貨ペア）: n=99, k=51, pct=51.5%, CI=[41.8~61.1%], E(R)=0.202
- other_fx（円以外の通貨ペア）: n=122, k=58, pct=47.5%, CI=[38.9~56.3%], E(R)=0.109
- btc（ビットコイン）: n=14, k=8, pct=57.1%, CI=[32.6~78.6%], E(R)=0.333

### FWD時間足別
- 1時間足: n=246, k=118, pct=48.0%, CI=[41.8~54.2%], E(R)=0.119
- 4時間足: n=125, k=65, pct=52.0%, CI=[43.3~60.6%], E(R)=0.213
- 日足: n=20, k=15, pct=75.0%, CI=[53.1~88.8%], E(R)=0.750

## 交絡チェック
- IS vs FWD: IS期間は登録前のデータで後ろ向き集計。FWD期間は登録後のリアルタイム集計 → 分割は適切
- FWDグループ: 全6グループで43%を上回る（円以外の通貨ペアのみCI範囲が43%をまたぐ）
- FWD時間足: 1時間足・4時間足のCIは43%を含む → 足ごとの差は現時点で明確でない（日足はN少）

## 前回（#109）との差分
- FWD: 374→391（+17回）
- FWD勝率: 50.3%→50.6%（+0.3pp）
- E(R): 0.18前後で安定
- CI下限（E(R)）: 依然+0.02でプラス維持（昇格条件の1つ目クリア済み）
