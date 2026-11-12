import json,sys
sys.path.insert(0,'.')
import signal_lab_verify as v
data=json.load(open('signals-log.json',encoding='utf-8-sig'))
ASOF="2026-11-13T06:12:00+09:00"
data,af,dropped=v.apply_asof(data,v.parse_asof(ASOF),"2026-11-13")
print("asof issues",af)
B="2026-07-21"; MID="2026-09-16"
S={"signal":"macd_golden","ma_pos":"below_both"}
Q=[
("FWD MACDG×両MA下",{**S,"fired_from":B}),
("FWD 全シグナル",{"fired_from":B}),
("FWD 買い全体",{"direction":"long","fired_from":B}),
("FWD 売り全体",{"direction":"short","fired_from":B}),
("FWD 両MA下の買い全体",{"ma_pos":"below_both","direction":"long","fired_from":B}),
("FWD MACDゴールデン全体",{"signal":"macd_golden","fired_from":B}),
("FWD 両MA下全体",{"ma_pos":"below_both","fired_from":B}),
("IS MACDG×両MA下",{**S,"fired_before":B}),
("IS 買い全体",{"direction":"long","fired_before":B}),
("IS 全",{"fired_before":B}),
("FWD 買い",{**S,"direction":"long","fired_from":B}),
("FWD 売り",{**S,"direction":"short","fired_from":B}),
("FWD 1h",{**S,"tf":"1h","fired_from":B}),
("FWD 4h",{**S,"tf":"4h","fired_from":B}),
("FWD 1d",{**S,"tf":"1d","fired_from":B}),
("FWD 指数",{**S,"group":"index","fired_from":B}),
("FWD 円FX",{**S,"group":"jpy_fx","fired_from":B}),
("FWD 他FX",{**S,"group":"other_fx","fired_from":B}),
("FWD 金銀",{**S,"group":"metal","fired_from":B}),
("FWD btc",{**S,"group":"btc","fired_from":B}),
("FWD oil",{**S,"group":"oil","fired_from":B}),
("FWD 前半",{**S,"fired_from":B,"fired_before":MID}),
("FWD 後半",{**S,"fired_from":MID}),
]
for l,f in Q:
    k,n=v.compute(data,f); lo,hi=v.wilson(k,n) if n else (0,0)
    if hi<=1: lo,hi=lo*100,hi*100
    print(f"{l}\t{k}/{n}\t{100*k/max(n,1):.1f}%\t[{lo:.1f},{hi:.1f}]")
