import json,sys
sys.path.insert(0,'.')
import signal_lab_verify as v
data=json.load(open('signals-log.json',encoding='utf-8-sig'))
ASOF="2026-11-02T06:13:00+09:00"
data,af,dropped=v.apply_asof(data,v.parse_asof(ASOF),"2026-11-02")
print("asof issues",af)
B="2026-09-27"
Q=[
("FWD:順張り・トレンド強",{"family":"tf","adx_band":"strong","fired_from":B}),
("FWD:順張り・トレンド弱(対照)",{"family":"tf","adx_band":"weak","fired_from":B}),
("FWD:順張り全体",{"family":"tf","fired_from":B}),
("FWD:全シグナル",{"fired_from":B}),
("IS:順張り・トレンド強",{"family":"tf","adx_band":"strong","fired_before":B}),
("IS:順張り・トレンド弱",{"family":"tf","adx_band":"weak","fired_before":B}),
("FWD強 4h",{"family":"tf","adx_band":"strong","tf":"4h","fired_from":B}),
("FWD強 1h",{"family":"tf","adx_band":"strong","tf":"1h","fired_from":B}),
("FWD強 買い",{"family":"tf","adx_band":"strong","direction":"long","fired_from":B}),
("FWD強 売り",{"family":"tf","adx_band":"strong","direction":"short","fired_from":B}),
("FWD強 指数",{"family":"tf","adx_band":"strong","group":"index","fired_from":B}),
("FWD強 円FX",{"family":"tf","adx_band":"strong","group":"jpy_fx","fired_from":B}),
("FWD強 他FX",{"family":"tf","adx_band":"strong","group":"other_fx","fired_from":B}),
("FWD強 金銀",{"family":"tf","adx_band":"strong","group":"metal","fired_from":B}),
("FWD強 btc",{"family":"tf","adx_band":"strong","group":"btc","fired_from":B}),
("FWD強 oil",{"family":"tf","adx_band":"strong","group":"oil","fired_from":B}),
]
for l,f in Q:
    k,n=v.compute(data,f); lo,hi=v.wilson(k,n) if n else (0,0)
    print(f"{l}\t{k}/{n}\t{100*k/max(n,1):.1f}%\t[{lo*100 if lo<1 else lo:.1f},{hi*100 if hi<1 else hi:.1f}]\t{f}")
