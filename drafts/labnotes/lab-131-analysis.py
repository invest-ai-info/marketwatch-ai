import json,sys,datetime as dt
sys.path.insert(0,'.')
import signal_lab_verify as v
data=json.load(open('signals-log.json'))
data=data if isinstance(data,list) else data.get('signals',data)
asof=dt.datetime.now(dt.timezone(dt.timedelta(hours=9)))
print('ASOF',asof.isoformat())
data,fails,dr=v.apply_asof(data,asof,asof.strftime('%Y-%m-%d'))
print(fails,dr)
B={"group":"index","direction":"short"}
FW={"fired_from":"2026-07-01"}
IS={"fired_before":"2026-07-01"}
def R(label,f):
    k,n=v.compute(data,f); lo,hi=v.wilson(k,n)
    print(f"{label:34s} {k}/{n} = {100*k/max(n,1):.1f}% CI[{lo:.1f},{hi:.1f}]  {json.dumps(f,ensure_ascii=False)}")
    return {"label":label,"filter":f,"k":k,"n":n}
out=[]
out.append(R("FWD:指数の売り",{**B,**FW}))
out.append(R("IS:指数の売り",{**B,**IS}))
out.append(R("全期間:指数の売り",B))
out.append(R("FWD:売り全体",{"direction":"short",**FW}))
out.append(R("FWD:指数の買い",{"group":"index","direction":"long",**FW}))
out.append(R("FWD:全シグナル",FW))
for tf in ("1h","4h","1d"): out.append(R(f"FWD:指数の売り {tf}",{**B,**FW,"tf":tf}))
for t in ("上昇","下降","中立・もみあい"): out.append(R(f"FWD:指数の売り {t}",{**B,**FW,"trend":t}))
for tk in ("NKD=F","ES=F","NQ=F","YM=F","^FTSE"): out.append(R(f"FWD:指数の売り {tk}",{**B,**FW,"ticker":tk}))
json.dump(out,open('drafts/labnotes/lab-131-raw.json','w'),ensure_ascii=False)
