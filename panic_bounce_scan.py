# -*- coding: utf-8 -*-
"""
panic_bounce_scan.py — 「今どの資産が投げ売り＝反発候補か」を日次スキャン（非FX）。
検証(_panic_cross.py)で確定した条件に基づく：本丸=RSI売られすぎ、出来高急増は上乗せ。
  過去2年の歴史検証: RSI≤30で前向き5日+0.92σ/78%、RSI≤30+出来高急増+1.0σ/77%、RSI≤25+パニック+1.66σ/81%。
データ: Yahoo chart API 直叩き（detect_sr_levels と同手法、ローカルで動く）。
使い方: python panic_bounce_scan.py
※ 検出ツール。実トレード採用には前向き再現＋スリッページ確認が要る（bandwalkで更に落ちる罠あり）。
"""
import sys, os, json, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta
import numpy as np
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
JST = timezone(timedelta(hours=9))

ASSETS=[("GC=F","金"),("SI=F","銀"),("CL=F","原油"),("NKD=F","日経225"),
        ("ES=F","S&P500"),("NQ=F","Nasdaq"),("YM=F","ダウ"),("^FTSE","英FTSE"),("BTC-USD","ビットコイン")]

def fetch(tk,rng="9mo"):
    url=("https://query1.finance.yahoo.com/v8/finance/chart/"
         +urllib.parse.quote(tk)+f"?range={rng}&interval=1d")
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0"})
    d=json.load(urllib.request.urlopen(req,timeout=25))
    q=d["chart"]["result"][0]["indicators"]["quote"][0]
    return q.get("high") or [], q.get("low") or [], q["close"], q.get("volume") or []

def atr14(H,L,C,p=14):
    H,L,C=map(lambda x:np.asarray(x,float),(H,L,C))
    if len(C)<p+1: return np.nan
    tr=np.maximum(H[1:]-L[1:], np.maximum(abs(H[1:]-C[:-1]),abs(L[1:]-C[:-1])))
    a=np.nanmean(tr[:p])
    for i in range(p,len(tr)):
        a=(a*(p-1)+tr[i])/p
    return a

def _swings(H,L,k=3):
    sh,sl=[],[]
    for i in range(k,len(H)-k):
        if H[i]==max(H[i-k:i+k+1]): sh.append(H[i])
        if L[i]==min(L[i-k:i+k+1]): sl.append(L[i])
    return sh,sl

def supports_below(H,L,entry,tol=0.006,min_touch=2):
    """現値より下のサポート（スイング高安クラスタ）を近い順に返す [(price,touches),...]"""
    sh,sl=_swings(np.asarray(H,float),np.asarray(L,float))
    pts=sorted(sh+sl)
    if not pts: return []
    zones,cur=[],[pts[0]]
    for p in pts[1:]:
        if abs(p-cur[-1])/cur[-1]<=tol: cur.append(p)
        else: zones.append(cur); cur=[p]
    zones.append(cur)
    out=[(float(np.mean(z)),len(z)) for z in zones if len(z)>=min_touch and np.mean(z)<entry]
    return sorted(out,key=lambda x:-x[0])  # 近い（高い）順

def _dec(x): return 2 if x<1000 else (1 if x<100000 else 0)

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

# 拾いゾーン定数（ATR倍）: _overshoot_depth.py 実測＝RSI≤30後の追加下落 中央0.9/75%1.7/90%3.7、反発中央1.2
ZONE_SHALLOW, ZONE_DEEP, ZONE_MAX, ZONE_TP = 0.9, 1.7, 3.7, 1.2

def build_zone(name):
    H,L,C = series[name]
    entry=float(C[-1]); a=atr14(H,L,C)
    if not (a and a>0): return [f"  ◆{name}: ATR算出不可"]
    d=_dec(entry)
    z1=entry-ZONE_SHALLOW*a; z2=entry-ZONE_DEEP*a; zmax=entry-ZONE_MAX*a
    tp=entry+ZONE_TP*a; sl=entry-(ZONE_MAX+0.6)*a
    sups=supports_below(H,L,entry)
    sup_txt="／".join(f"{p:.{d}f}(★{t})" for p,t in sups[:2]) if sups else "なし(レンジ下限)"
    strong=[p for p,t in sups if t>=3 and p<zmax]
    sl_final=min(sl,(max(strong)-0.3*a)) if strong else sl
    return [
        f"  ◆{name}  現値 {entry:.{d}f} / ATR {a:.{d}f}",
        f"     拾いゾーン: 浅 {z1:.{d}f}（−0.9ATR）／ 深 {z2:.{d}f}（−1.7ATR）  ← 半数〜3/4はこの範囲で底",
        f"     最大想定突っ込み: {zmax:.{d}f}（−3.7ATR）",
        f"     近いサポート: {sup_txt}",
        f"     SL目安: {sl_final:.{d}f}（最大想定/強サポート割れの下）",
        f"     反発目安TP: {tp:.{d}f}（+1.2ATR・中央値）",
    ]

print("="*84)
print("📉 パニック反発スキャン（非FX9資産・日足）— 投げ売り＝反発候補を探す")
print("="*84)
print(f"{'資産':<12}{'RSI':>6}{'%b':>7}{'出来高z':>8}{'3日%':>8}  シグナル")
print("-"*84)
results=[]; series={}
for tk,name in ASSETS:
    try: H,L,C,V=fetch(tk)
    except Exception as e:
        print(f"{name:<12}  取得失敗"); continue
    H=np.array([x if x is not None else np.nan for x in H],float)
    L=np.array([x if x is not None else np.nan for x in L],float)
    C=np.array([x if x is not None else np.nan for x in C],float)
    V=np.array([x if x is not None else np.nan for x in V],float)
    ok=~(np.isnan(C)|np.isnan(H)|np.isnan(L)); H,L,C=H[ok],L[ok],C[ok]
    if len(C)<40: print(f"{name:<12}  データ不足"); continue
    rsi=rsi_wilder(C); pb=pctb(C)
    volz=None
    Vf=np.array([x for x in V if not np.isnan(x)],float)
    if len(Vf)>=21 and Vf[-21:-1].std()>0:
        volz=(Vf[-3:].mean()-Vf[-21:-1].mean())/Vf[-21:-1].std()
    move3=(C[-1]/C[-4]-1)/(np.nanstd(np.diff(C)/C[:-1])*np.sqrt(3)) if len(C)>5 else 0
    label,score=assess(rsi, volz, move3)
    results.append((score,name,rsi,pb,volz,move3,label))
    series[name]=(H,L,C)

for score,name,rsi,pb,volz,move3,label in sorted(results,key=lambda x:(-x[0], x[2] if np.isfinite(x[2]) else 999)):
    vz=f"{volz:+.1f}σ" if volz is not None else "  —"
    pbs=f"{pb:+.2f}" if np.isfinite(pb) else "  —"
    print(f"{name:<12}{rsi:>6.1f}{pbs:>7}{vz:>8}{move3:>+7.1f}σ  {label}")

cand=[r for r in results if r[0]>=2]
cand_line = ("🎯 反発候補(RSI≤30): " + ", ".join(r[1] for r in cand)) if cand else "現在、RSI≤30の反発候補なし（無理に拾わない）"
print("\n" + cand_line)

zone_blocks=[]
if cand:
    print("\n――― 反発候補の拾いゾーン（参考・分割/損切り前提）―――")
    for r in sorted(cand,key=lambda x:-x[0]):
        lines=build_zone(r[1])
        for ln in lines: print(ln)
        zone_blocks.append((r[1],lines))

print("\n※ 検出のみ。RSI≤30＝歴史的に前向き+0.9σ/78%だが、bandwalkで更に落ちる例もある。")
print("  実トレードは反転確認(陽線/RSI反転)・分割・損切り前提で。本採用は前向き再現＋スリッページ確認後。")

# ── panic-scan.md を出力（GitHub Actions が日次でコミット。SYNC禁忌＝ローカルから push しない）──
def _write_md(results, cand, cand_line, zone_blocks):
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
    if zone_blocks:
        L.append("\n## 🎯 反発候補の拾いゾーン（参考・分割/損切り前提）")
        L.append("> RSI≤30後の追加下落は実測で中央0.9ATR・3/4が1.7ATR以内・最大(90%)3.7ATR、反発中央1.2ATR。\n")
        for nm,lines in zone_blocks:
            L.append(f"**{lines[0].strip().lstrip('◆ ')}**")
            for ln in lines[1:]:
                L.append(f"- {ln.strip()}")
            L.append("")
    L.append("\n---\n")
    L.append("⚠️ **検出ツールであり売買推奨ではありません。** RSI≤30は歴史的に反発しやすい一方、強い下落では"
             "バンドウォークでさらに下げることもあります。実トレードは反転確認（陽線/RSI反転）・分割・損切り前提で。\n")
    L.append("※ 歴史内2年・上昇ドリフト期・深条件はサンプル小。前向き(アウトオブサンプル)再現＋スリッページ確認まで実トレード採用しない。"
             "本ファイルは前向き検証データ蓄積のための非公開メモ（GitHub Actions が日次生成）。")
    content = "\n".join(L)+"\n"
    with open("panic-scan.md","w",encoding="utf-8") as f:
        f.write(content)
    return content

def _maybe_email(md_text, cand):
    """候補がある日だけ、Gmail creds が存在する環境（GitHub Actions）でメール送信。
    ローカル実行（creds無し）や候補なしの日は何もしない。失敗してもスキャンは止めない。"""
    if not cand:
        print("（メール: RSI≤30の候補なし→送信しない）"); return
    user = os.environ.get("GMAIL_USER"); pw = os.environ.get("GMAIL_APP_PASSWORD")
    to = os.environ.get("ALERT_RECIPIENT") or user
    if not (user and pw):
        print("（メール: Gmail creds 未設定→スキップ＝ローカル実行）"); return
    try:
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email.utils import formatdate
        names = "・".join(r[1] for r in cand)
        today = datetime.now(JST).strftime("%Y-%m-%d")
        subject = f"📉 パニック反発候補: {names}（{today}）"
        try:
            import markdown
            body_html = markdown.markdown(md_text, extensions=["tables","fenced_code","nl2br","sane_lists"])
            html = ("<html><body style=\"font-family:-apple-system,Segoe UI,sans-serif;font-size:14px;"
                    "line-height:1.6;color:#1f2328;max-width:760px;margin:0 auto;padding:8px\">"
                    "<style>table{border-collapse:collapse;width:100%;margin:8px 0}"
                    "th,td{border:1px solid #d0d7de;padding:5px 8px;font-size:13px;text-align:left}"
                    "th{background:#f6f8fa}h1{font-size:18px}h2{font-size:16px}</style>"
                    f"{body_html}"
                    "<hr><p style=\"font-size:12px;color:#6e7781\">※本メールは個人用の検出メモであり投資助言ではありません。"
                    "RSI≤30は歴史的に反発しやすい一方、強い下落ではさらに下げることもあります（bandwalk）。"
                    "反転確認・分割・損切り前提で。最終判断は自己責任で。</p></body></html>")
            part = MIMEText(html, "html", "utf-8")
        except Exception:
            part = MIMEText(md_text, "plain", "utf-8")
        msg = MIMEMultipart(); msg["From"]=user; msg["To"]=to; msg["Subject"]=subject
        msg["Date"]=formatdate(localtime=True); msg.attach(part)
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
            server.login(user, pw); server.sendmail(user, [to], msg.as_string())
        print(f"✅ パニック反発候補メールを {to} に送信: {subject}")
    except Exception as e:
        print(f"⚠️ メール送信失敗（スキャンは継続）: {type(e).__name__}: {e}")

try:
    md_text = _write_md(results, cand, cand_line, zone_blocks)
    print("\n→ panic-scan.md を出力。")
    _maybe_email(md_text, cand)
except Exception as e:
    print(f"\n⚠️ panic-scan.md 出力/通知失敗: {e}")
