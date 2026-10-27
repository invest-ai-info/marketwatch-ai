import json,sys,datetime as dt
sys.path.insert(0,'.')
import signal_lab_verify as v
data=json.load(open('signals-log.json'))
data=data if isinstance(data,list) else data.get('signals',data)
asof=dt.datetime.now(dt.timezone(dt.timedelta(hours=9)))
print('ASOF',asof.isoformat())
data,fails,dr=v.apply_asof(data,asof,asof.strftime('%Y-%m-%d'))
print(fails,dr)
B={"group":"other_fx","direction":"long"}
FW={"fired_from":"2026-06-20"}
IS={"fired_before":"2026-06-20"}
def R(label,f):
    k,n=v.compute(data,f); lo,hi=v.wilson(k,n)
    print(f"{label:34s} {k}/{n} = {100*k/max(n,1):.1f}% CI[{lo:.1f},{hi:.1f}]  {json.dumps(f,ensure_ascii=False)}")
    return {"label":label,"filter":f,"k":k,"n":n}
out=[]
out.append(R("FWD:その他FXの買い",{**B,**FW}))
out.append(R("IS:その他FXの買い",{**B,**IS}))
out.append(R("全期間:その他FXの買い",B))
out.append(R("FWD:買い全体",{"direction":"long",**FW}))
out.append(R("FWD:その他FXの売り",{"group":"other_fx","direction":"short",**FW}))
out.append(R("FWD:円がからむFXの買い",{"group":"jpy_fx","direction":"long",**FW}))
out.append(R("FWD:全シグナル",FW))
for tf in ("1h","4h","1d"): out.append(R(f"FWD:その他FXの買い {tf}",{**B,**FW,"tf":tf}))
for t in ("上昇","下降","中立・もみあい"): out.append(R(f"FWD:その他FXの買い {t}",{**B,**FW,"trend":t}))
for tk in ("EURUSD=X","GBPUSD=X","AUDUSD=X","EURAUD=X","GBPAUD=X"): out.append(R(f"FWD:その他FXの買い {tk}",{**B,**FW,"ticker":tk}))
json.dump(out,open('drafts/labnotes/lab-132-raw.json','w'),ensure_ascii=False)
