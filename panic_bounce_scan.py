# -*- coding: utf-8 -*-
"""
panic_bounce_scan.py — 「今どの資産が投げ売り＝反発候補か」を日次スキャン（非FX）。
検証(_panic_cross.py)で確定した条件に基づく：本丸=RSI売られすぎ、出来高急増は上乗せ。
  過去2年の歴史検証: RSI≤30で前向き5日+0.92σ/78%、RSI≤30+出来高急増+1.0σ/77%、RSI≤25+パニック+1.66σ/81%。
データ: Yahoo chart API 直叩き（detect_sr_levels と同手法、ローカルで動く）。
使い方: python panic_bounce_scan.py
※ 検出ツール。実トレード採用には前向き再現＋スリッページ確認が要る（bandwalkで更に落ちる罠あり）。
"""
import sys, json, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta
import numpy as np
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
JST = timezone(timedelta(hours=9))

ASSETS=[("GC=F","金"),("SI=F","銀"),("CL=F","原油"),("NKD=F","日経225"),
        ("ES=F","S&P500"),("NQ=F","Nasdaq"),("YM=F","ダウ"),("^FTSE","英FTSE"),("BTC-USD","ビットコイン")]

def fetch(tk,rng="6mo"):
    url=("https://query1.finance.yahoo.com/v8/finance/chart/"
         +urllib.parse.quote(tk)+f"?range={rng}&interval=1d")
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0"})
    d=json.load(urllib.request.urlopen(req,timeout=25))
    q=d["chart"]["result"][0]["indicators"]["quote"][0]
    return q["close"], q.get("volume") or []

def rsi_wilder(C,p=14):
    C=np.asarray(C,float)
    if len(C)<=p: return np.nan
    d=np.diff(C); g=np.clip(d,0,None); l=np.clip(-d,0,None)
    ag=g[:p].mean(); al=l[:p].mean()
    for i in range(p,len(C)):
        if i>p: ag=(ag*(p-1)+g[i-1])/p; al=(al*(p-1)+l[i-1])/p
    return 100.0 if al==0 else 100-100/(1+ag/al)

def pctb(C,n=20,k=2.0):
    C=np.asarray(C,float)
    if len(C)<n: return np.nan
    w=C[-n:]; m=w.mean(); s=w.std()
    return (C[-1]-(m-k*s))/(2*k*s) if s>0 else np.nan

def assess(rsi, volz, move3):
    """確定条件でラベル付け。本丸=RSI、出来高は上乗せ。"""
    if not np.isfinite(rsi): return "—", 0
    panic_vol = (volz is not None and volz>0.5)
    if rsi<=25 and panic_vol and move3<-0.5:
        return "🔴強パニック反発候補(RSI≤25+投げ)", 4
    if rsi<=25:
        return "🔴深い売られすぎ(RSI≤25)", 3
    if rsi<=30 and panic_vol:
        return "🟠パニック反発候補(RSI≤30+出来高急増)", 3
    if rsi<=30:
        return "🟠売られすぎ(RSI≤30)", 2
    if rsi<=37:
        return "🟡やや売られすぎ(監視)", 1
    return "・中立〜", 0

print("="*84)
print("📉 パニック反発スキャン（非FX9資産・日足）— 投げ売り＝反発候補を探す")
print("="*84)
print(f"{'資産':<12}{'RSI':>6}{'%b':>7}{'出来高z':>8}{'3日%':>8}  シグナル")
print("-"*84)
results=[]
for tk,name in ASSETS:
    try: C,V=fetch(tk)
    except Exception as e:
        print(f"{name:<12}  取得失敗"); continue
    C=np.array([x if x is not None else np.nan for x in C],float)
    V=np.array([x if x is not None else np.nan for x in V],float)
    ok=~np.isnan(C); C=C[ok]; V=V[ok]
    if len(C)<40: print(f"{name:<12}  データ不足"); continue
    rsi=rsi_wilder(C); pb=pctb(C)
    volz=None
    if len(V)>=21 and np.isfinite(V[-21:-1]).all() and V[-21:-1].std()>0:
        volz=(V[-3:].mean()-V[-21:-1].mean())/V[-21:-1].std()
    move3=(C[-1]/C[-4]-1)/(np.nanstd(np.diff(C)/C[:-1])*np.sqrt(3)) if len(C)>5 else 0
    label,score=assess(rsi, volz, move3)
    results.append((score,name,rsi,pb,volz,move3,label))

for score,name,rsi,pb,volz,move3,label in sorted(results,key=lambda x:(-x[0], x[2] if np.isfinite(x[2]) else 999)):
    vz=f"{volz:+.1f}σ" if volz is not None else "  —"
    pbs=f"{pb:+.2f}" if np.isfinite(pb) else "  —"
    print(f"{name:<12}{rsi:>6.1f}{pbs:>7}{vz:>8}{move3:>+7.1f}σ  {label}")

cand=[r for r in results if r[0]>=2]
cand_line = ("🎯 反発候補(RSI≤30): " + ", ".join(r[1] for r in cand)) if cand else "現在、RSI≤30の反発候補なし（無理に拾わない）"
print("\n" + cand_line)
print("\n※ 検出のみ。RSI≤30＝歴史的に前向き+0.9σ/78%だが、bandwalkで更に落ちる例もある。")
print("  実トレードは反転確認(陽線/RSI反転)・分割・損切り前提で。本採用は前向き再現＋スリッページ確認後。")

# ── panic-scan.md を出力（GitHub Actions が日次でコミット。SYNC禁忌＝ローカルから push しない）──
def _write_md(results, cand, cand_line):
    now = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    L = []
    L.append(f"# 📉 パニック反発スキャン（非FX 9資産）\n")
    L.append(f"データ取得: **{now}**（日足ベース・1日1回）\n")
    L.append(f"> 投げ売り＝反発候補（**本丸=RSI売られすぎ**、出来高急増は上乗せ）。"
             f"歴史検証(非FX2年): RSI≤30→前向き5日**+0.92σ/78%**、RSI≤25**+1.66σ/81%**、RSI≤30+出来高急増+1.02σ。\n")
    L.append(f"**{cand_line}**\n")
    L.append("| 資産 | RSI | %b | 出来高z | 3日(σ) | シグナル |")
    L.append("|---|---:|---:|---:|---:|---|")
    for score,name,rsi,pb,volz,move3,label in sorted(results,key=lambda x:(-x[0], x[2] if np.isfinite(x[2]) else 999)):
        vz=f"{volz:+.1f}σ" if volz is not None else "—"
        pbs=f"{pb:+.2f}" if np.isfinite(pb) else "—"
        L.append(f"| {name} | {rsi:.1f} | {pbs} | {vz} | {move3:+.1f} | {label} |")
    L.append("\n---\n")
    L.append("⚠️ **検出ツールであり売買推奨ではありません。** RSI≤30は歴史的に反発しやすい一方、強い下落では"
             "バンドウォークでさらに下げることもあります。実トレードは反転確認（陽線/RSI反転）・分割・損切り前提で。\n")
    L.append("※ 歴史内2年・上昇ドリフト期・深条件はサンプル小。前向き(アウトオブサンプル)再現＋スリッページ確認まで実トレード採用しない。"
             "本ファイルは前向き検証データ蓄積のための非公開メモ（GitHub Actions が日次生成）。")
    with open("panic-scan.md","w",encoding="utf-8") as f:
        f.write("\n".join(L)+"\n")

try:
    _write_md(results, cand, cand_line)
    print("\n→ panic-scan.md を出力。")
except Exception as e:
    print(f"\n⚠️ panic-scan.md 出力失敗: {e}")
