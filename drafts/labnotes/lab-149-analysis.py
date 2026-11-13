import json,sys
sys.path.insert(0,'.')
import signal_lab_verify as v
data=json.load(open('signals-log.json',encoding='utf-8-sig'))
ASOF="2026-11-14T06:11:00+09:00"
data,af,dropped=v.apply_asof(data,v.parse_asof(ASOF),"2026-11-14")
print("asof issues",af)
B="2026-07-01"; MID="2026-09-01"
S={"group":"index","direction":"short"}
Q=[("FWD 指数の売り",{**S,"fired_from":B}),("FWD 売り全体",{"direction":"short","fired_from":B}),
("FWD 指数の買い",{"group":"index","direction":"long","fired_from":B}),("FWD 指数全体",{"group":"index","fired_from":B}),
("FWD 全シグナル",{"fired_from":B}),("IS 指数の売り",{**S,"fired_before":B}),("IS 売り全体",{"direction":"short","fired_before":B}),
("FWD 1h",{**S,"tf":"1h","fired_from":B}),("FWD 4h",{**S,"tf":"4h","fired_from":B}),("FWD 1d",{**S,"tf":"1d","fired_from":B}),
("FWD 日経先物",{**S,"ticker":"NKD=F","fired_from":B}),("FWD S&P",{**S,"ticker":"ES=F","fired_from":B}),
("FWD ナスダック",{**S,"ticker":"NQ=F","fired_from":B}),("FWD ダウ",{**S,"ticker":"YM=F","fired_from":B}),("FWD FTSE",{**S,"ticker":"^FTSE","fired_from":B}),
("FWD 前半",{**S,"fired_from":B,"fired_before":MID}),("FWD 後半",{**S,"fired_from":MID}),
("FWD 上昇",{**S,"trend":"上昇","fired_from":B}),("FWD 下降",{**S,"trend":"下降","fired_from":B}),("FWD 中立",{**S,"trend":"中立・もみあい","fired_from":B})]
for l,f in Q:
    k,n=v.compute(data,f); lo,hi=v.wilson(k,n) if n else (0,0)
    if hi<=1: lo,hi=lo*100,hi*100
    print(f"{l}\t{k}/{n}\t{100*k/max(n,1):.1f}%\t[{lo:.1f},{hi:.1f}]")
