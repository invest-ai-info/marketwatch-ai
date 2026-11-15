import json,sys
sys.path.insert(0,'.')
import signal_lab_verify as v
data=json.load(open('signals-log.json',encoding='utf-8-sig'))
ASOF="2026-11-16T06:11:00+09:00"
data,af,dropped=v.apply_asof(data,v.parse_asof(ASOF),"2026-11-16")
print("asof issues",af)
B="2026-06-26"; MID="2026-09-01"
S={"signal":"ma_dead"}
Q=[("FWD ma_dead",{**S,"fired_from":B}),("FWD 売り全体",{"direction":"short","fired_from":B}),("FWD 全シグナル",{"fired_from":B}),
("IS ma_dead",{**S,"fired_before":B}),("IS 全シグナル",{"fired_before":B}),
("FWD ma_dead 売り",{**S,"direction":"short","fired_from":B}),("FWD ma_dead 買い",{**S,"direction":"long","fired_from":B}),
("FWD 1h",{**S,"tf":"1h","fired_from":B}),("FWD 4h",{**S,"tf":"4h","fired_from":B}),("FWD 1d",{**S,"tf":"1d","fired_from":B}),
("FWD index",{**S,"group":"index","fired_from":B}),("FWD jpy_fx",{**S,"group":"jpy_fx","fired_from":B}),("FWD other_fx",{**S,"group":"other_fx","fired_from":B}),
("FWD metal",{**S,"group":"metal","fired_from":B}),("FWD btc",{**S,"group":"btc","fired_from":B}),("FWD oil",{**S,"group":"oil","fired_from":B}),
("FWD 前半",{**S,"fired_from":B,"fired_before":MID}),("FWD 後半",{**S,"fired_from":MID}),
("FWD 上昇",{**S,"trend":"上昇","fired_from":B}),("FWD 下降",{**S,"trend":"下降","fired_from":B}),("FWD 中立",{**S,"trend":"中立・もみあい","fired_from":B}),
("FWD ma_golden",{"signal":"ma_golden","fired_from":B})]
for l,f in Q:
    k,n=v.compute(data,f); lo,hi=v.wilson(k,n) if n else (0,0)
    if hi<=1: lo,hi=lo*100,hi*100
    print(f"{l}\t{k}/{n}\t{100*k/max(n,1):.1f}%\t[{lo:.1f},{hi:.1f}]")
