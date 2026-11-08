import json,sys
sys.path.insert(0,'.')
import signal_lab_verify as v
data=json.load(open('signals-log.json',encoding='utf-8-sig'))
ASOF="2026-11-09T06:12:00+09:00"
data,af,dropped=v.apply_asof(data,v.parse_asof(ASOF),"2026-11-09")
print("asof issues",af)
B="2026-06-23"
S={"signal":"low_break"}
Q=[
("FWD 安値ブレイク",{**S,"fired_from":B}),
("FWD 売り全体",{"direction":"short","fired_from":B}),
("FWD 全シグナル",{"fired_from":B}),
("IS 安値ブレイク",{**S,"fired_before":B}),
("IS 売り全体",{"direction":"short","fired_before":B}),
("FWD 1h",{**S,"tf":"1h","fired_from":B}),
("FWD 4h",{**S,"tf":"4h","fired_from":B}),
("FWD 1d",{**S,"tf":"1d","fired_from":B}),
("FWD 指数",{**S,"asset_class":"index","fired_from":B}),
("FWD FX",{**S,"asset_class":"fx","fired_from":B}),
("FWD コモ",{**S,"asset_class":"commodity","fired_from":B}),
("FWD btc",{**S,"asset_class":"crypto","fired_from":B}),
("FWD 前半(〜9/15)",{**S,"fired_from":B,"fired_before":"2026-09-16"}),
("FWD 後半(9/16〜)",{**S,"fired_from":"2026-09-16"}),
("FWD 下降",{**S,"trend":"下降","fired_from":B}),
]
for l,f in Q:
    k,n=v.compute(data,f); lo,hi=v.wilson(k,n) if n else (0,0)
    print(f"{l}\t{k}/{n}\t{100*k/max(n,1):.1f}%\t[{lo*100 if lo<1 else lo:.1f},{hi*100 if hi<1 else hi:.1f}]")
