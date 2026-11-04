import json,sys
sys.path.insert(0,'.')
import signal_lab_verify as v
data=json.load(open('signals-log.json',encoding='utf-8-sig'))
ASOF="2026-11-05T06:12:00+09:00"
data,af,dropped=v.apply_asof(data,v.parse_asof(ASOF),"2026-11-05")
print("asof issues",af)
B="2026-09-28"
S={"trend":"下降","reversal_long":True}
Q=[
("FWD:下降中の逆張り買い",{**S,"fired_from":B}),
("IS:下降中の逆張り買い(登録前)",{**S,"fired_before":B}),
("FWD:買い全体(対照)",{"direction":"long","fired_from":B}),
("FWD:全シグナル",{"fired_from":B}),
("FWD:逆張り買い全体(トレンド問わず)",{"reversal_long":True,"fired_from":B}),
("FWD:下降トレンド中の買い全体",{"trend":"下降","direction":"long","fired_from":B}),
("FWD 1h",{**S,"tf":"1h","fired_from":B}),
("FWD 4h",{**S,"tf":"4h","fired_from":B}),
("FWD 1d",{**S,"tf":"1d","fired_from":B}),
("FWD 指数",{**S,"group":"index","fired_from":B}),
("FWD 円FX",{**S,"group":"jpy_fx","fired_from":B}),
("FWD 他FX",{**S,"group":"other_fx","fired_from":B}),
("FWD 金銀",{**S,"group":"metal","fired_from":B}),
("FWD btc",{**S,"group":"btc","fired_from":B}),
("FWD oil",{**S,"group":"oil","fired_from":B}),
("FWD 前半(〜10/16)",{**S,"fired_from":B,"fired_before":"2026-10-17"}),
("FWD 後半(10/17〜)",{**S,"fired_from":"2026-10-17"}),
]
for l,f in Q:
    k,n=v.compute(data,f); lo,hi=v.wilson(k,n) if n else (0,0)
    print(f"{l}\t{k}/{n}\t{100*k/max(n,1):.1f}%\t[{lo*100 if lo<1 else lo:.1f},{hi*100 if hi<1 else hi:.1f}]\t{f}")
