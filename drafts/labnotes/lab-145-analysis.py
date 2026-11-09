import json,sys
sys.path.insert(0,'.')
import signal_lab_verify as v
data=json.load(open('signals-log.json',encoding='utf-8-sig'))
ASOF="2026-11-10T06:12:00+09:00"
data,af,dropped=v.apply_asof(data,v.parse_asof(ASOF),"2026-11-10")
print("asof issues",af)
B="2026-09-28"
S={"signal":"rsi_oversold_bounce","tf":"4h"}
Q=[
("FWD 売られすぎ4h",{**S,"fired_from":B}),
("FWD 4h買い全体(対照)",{"tf":"4h","direction":"long","fired_from":B}),
("FWD 4h全シグナル",{"tf":"4h","fired_from":B}),
("FWD 全シグナル",{"fired_from":B}),
("IS 売られすぎ4h",{**S,"fired_before":B}),
("IS 4h買い全体",{"tf":"4h","direction":"long","fired_before":B}),
("FWD 売られすぎ全足",{"signal":"rsi_oversold_bounce","fired_from":B}),
("FWD 4h 指数",{**S,"group":"index","fired_from":B}),
("FWD 4h 円FX",{**S,"group":"jpy_fx","fired_from":B}),
("FWD 4h 他FX",{**S,"group":"other_fx","fired_from":B}),
("FWD 4h 金銀",{**S,"group":"metal","fired_from":B}),
("FWD 4h btc",{**S,"group":"btc","fired_from":B}),
("FWD 4h oil",{**S,"group":"oil","fired_from":B}),
("FWD 前半(〜10/19)",{**S,"fired_from":B,"fired_before":"2026-10-20"}),
("FWD 後半(10/20〜)",{**S,"fired_from":"2026-10-20"}),
]
for l,f in Q:
    k,n=v.compute(data,f); lo,hi=v.wilson(k,n) if n else (0,0)
    print(f"{l}\t{k}/{n}\t{100*k/max(n,1):.1f}%\t[{lo*100 if lo<1 else lo:.1f},{hi*100 if hi<1 else hi:.1f}]")
