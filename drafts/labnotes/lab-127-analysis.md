# lab-127 分析メモ — cs_aligned 反証確定

日付: 2026-10-18 (JST)
仮説ID: cs_aligned
テーマ: 通貨の強さと同じ向きに入ると勝ちにくい？

## 仮説
「通貨の強弱マトリクスでシグナルの向きと一致する」場面でシグナルが出たとき、
勝率はベースラインより低い。

登録日: 2026-09-28
IS/FWD 区切り: fired_before/fired_from = "2026-09-29"

## スクリプト

```python
import json, math, statistics
with open('signals-log.json') as f:
    data = json.load(f)

fwd_start = '2026-09-29'

def cs_align_of(d):
    fa = d.get('fx_alignment')
    if isinstance(fa, dict):
        a = fa.get('aligned')
        if a is None: return None
        return 'aligned' if a else 'against'
    return None

def get_fired_date(s): return s.get('fired_at','')[:10]
def is_win(s): return s.get('outcome') in ['tp1']
def is_closed(s): return s.get('outcome') in ['tp1','sl','expired']
def get_r(s):
    o = s.get('outcome','')
    if o == 'tp1': return 1.33
    if o == 'sl': return -1.0
    if o == 'expired': return 0.0
    return 0.0

def wilson_ci(k,n,z=1.96):
    if n==0: return (0,0)
    p=k/n; d=1+z**2/n; c=(p+z**2/(2*n))/d
    m=z*math.sqrt(p*(1-p)/n+z**2/(4*n**2))/d
    return (max(0,c-m),min(1,c+m))

def r_ci(rs):
    if len(rs)<2: return (0,0)
    m=statistics.mean(rs); s=statistics.stdev(rs); se=s/math.sqrt(len(rs))
    return (m-1.96*se, m+1.96*se)
```

## 生出力

IS cs_aligned (fired_before=2026-09-29):
  k=318 n=809 win=39.3% CI=[36.0%~42.7%] avgR=-0.058

IS baseline:
  k=2086 n=4949 win=42.1%

FWD cs_aligned (fired_from=2026-09-29):
  k=18 n=80 win=22.5% CI=[14.7%~32.8%] avgR=-0.463 R-CI=[-0.678,-0.249]

FWD cs_against (fired_from=2026-09-29):
  k=33 n=78 win=42.3% CI=[32.0%~53.4%] avgR=+0.011 R-CI=[-0.243,+0.266]

FWD baseline (all, fired_from=2026-09-29):
  k=151 n=416 win=36.3% CI=[31.8%~41.0%] avgR=-0.142

FWD cs_None: 258件（fx_alignment が記録されていないシグナル）

## 判定

- FWD cs_aligned のR-CI=[-0.678,-0.249] → 両端が負 → ⛔反証確定（trackerが「rejected」に変更）
- IS 39.3%はベースライン42.1%より低いが差は3pp程度、事前登録前は「怪しい」程度だった
- FWD で一気に22.5%まで落ち、ベースライン36.3%との差が13.8pp（反証確定）
- cs_against（逆向き）は42.3%でベースライン36.3%より高いが、R-CIが0を含む → 「逆向きが有利」とは言えない
  （→ 「同じ向きが不利」というのが今回の発見）
- trackerが「逆向きで再登録（cs_aligned の却下を受けて）」を自動登録。2026-10-19以降を前向き計測開始

## 交絡点検

- FX専用: cs_align は fx_alignment を参照 → FXシグナルのみ対象（全銘柄の一部）
- FWD cs_aligned=80件、cs_against=78件、cs_None=258件
- FWD期間の全体成績が36.3%（ベースライン）で、この期間は全体的に難しい相場だったが、
  cs_alignedはさらに低い22.5%

## 注記

trackerの出力ではN=84とあったが、Pythonの直接集計ではN=80（tp1=18, sl=61, expired=1）。
差はtrackerの計算方式の違い（no_plan の扱い等）によるもの。記事はPython直接集計のN=80を使用。
