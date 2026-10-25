import json,sys,datetime as dt
sys.path.insert(0,'.')
import signal_lab_verify as v
data=json.load(open('signals-log.json'))
data=data if isinstance(data,list) else data.get('signals',data)
asof=dt.datetime.now(dt.timezone(dt.timedelta(hours=9)))
print('ASOF',asof.isoformat())
data,fails,dr=v.apply_asof(data,asof,asof.strftime('%Y-%m-%d'))
print(fails,dr)
B={"signal":"rsi_oversold_bounce"}
FW={"fired_from":"2026-06-17"}
def R(label,f):
    k,n=v.compute(data,f); lo,hi=v.wilson(k,n)
    print(f"{label:34s} {k}/{n} = {100*k/max(n,1):.1f}% CI[{lo:.1f},{hi:.1f}]  {json.dumps(f,ensure_ascii=False)}")
    return {"label":label,"filter":f,"k":k,"n":n}
out=[]
out.append(R("FWD:売られすぎ反発",{**B,**FW}))
out.append(R("IS:売られすぎ反発",{**B,"fired_before":"2026-06-17"}))
out.append(R("全期間:売られすぎ反発",B))
out.append(R("FWD:ロング全体",{"direction":"long",**FW}))
out.append(R("FWD:全シグナル",FW))
for tf in ("1h","4h","1d"): out.append(R(f"FWD:反発 {tf}",{**B,**FW,"tf":tf}))
for g in ("index","metal","jpy_fx","other_fx","btc","oil"): out.append(R(f"FWD:反発 {g}",{**B,**FW,"group":g}))
for t in ("上昇","下降","中立・もみあい"): out.append(R(f"FWD:反発 {t}",{**B,**FW,"trend":t}))
json.dump(out,open('/tmp/claude-0/-home-user-marketwatch-ai/b85988a2-99c6-5b61-82ce-a95159d9fb1f/scratchpad/c130.json','w'),ensure_ascii=False)
