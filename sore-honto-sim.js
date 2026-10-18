/* それ、本当？ 定説シミュレーター（guide-sore-honto.html 用）。
   計算はすべて読者のブラウザの中。価格は sim-data/ の日足。ほかのスクリプトと名前がぶつからないよう全体を包む。 */
(function(){
/*ENGINE-START*/
// ---------- 指標の計算 ----------
function sma(a,n){const r=new Float64Array(a.length).fill(NaN);let s=0,c=0;for(let i=0;i<a.length;i++){const x=a[i];if(isNaN(x)){s=0;c=0;continue;}s+=x;c++;if(c>n){s-=a[i-n];c=n;}if(c===n)r[i]=s/n;}return r;}
function ema(a,n){const r=new Float64Array(a.length).fill(NaN);const k=2/(n+1);let prev=NaN,s=0,c=0;for(let i=0;i<a.length;i++){const x=a[i];if(isNaN(x))continue;if(isNaN(prev)){s+=x;c++;if(c===n){prev=s/n;r[i]=prev;}}else{prev=x*k+prev*(1-k);r[i]=prev;}}return r;}
function sdev(a,n,m){const r=new Float64Array(a.length).fill(NaN);for(let i=n-1;i<a.length;i++){if(isNaN(m[i]))continue;let s=0;for(let j=i-n+1;j<=i;j++){const d=a[j]-m[i];s+=d*d;}r[i]=Math.sqrt(s/n);}return r;}
function rmax(a,n){const r=new Float64Array(a.length).fill(NaN);for(let i=n-1;i<a.length;i++){let m=-Infinity;for(let j=i-n+1;j<=i;j++)if(a[j]>m)m=a[j];r[i]=m;}return r;}
function rmin(a,n){const r=new Float64Array(a.length).fill(NaN);for(let i=n-1;i<a.length;i++){let m=Infinity;for(let j=i-n+1;j<=i;j++)if(a[j]<m)m=a[j];r[i]=m;}return r;}
function rsi(c,n){const r=new Float64Array(c.length).fill(NaN);let g=0,l=0;for(let i=1;i<c.length;i++){const d=c[i]-c[i-1],up=d>0?d:0,dn=d<0?-d:0;if(i<=n){g+=up;l+=dn;if(i===n){g/=n;l/=n;r[i]=l===0?100:100-100/(1+g/l);}}else{g=(g*(n-1)+up)/n;l=(l*(n-1)+dn)/n;r[i]=l===0?100:100-100/(1+g/l);}}return r;}
function rci(c,n){const r=new Float64Array(c.length).fill(NaN);const w=new Array(n);for(let i=n-1;i<c.length;i++){for(let j=0;j<n;j++)w[j]=c[i-j];let s=0;for(let j=0;j<n;j++){let gt=0,eq=0;for(let k=0;k<n;k++){if(w[k]>w[j])gt++;else if(w[k]===w[j])eq++;}const pr=gt+(eq+1)/2;const d=(j+1)-pr;s+=d*d;}r[i]=(1-6*s/(n*(n*n-1)))*100;}return r;}
// 値動きの幅（ATR・ワイルダー式）
function atrW(D,n){const r=new Float64Array(D.n).fill(NaN);let a=NaN,s=0;for(let i=1;i<D.n;i++){const tr=Math.max(D.h[i]-D.l[i],Math.abs(D.h[i]-D.c[i-1]),Math.abs(D.l[i]-D.c[i-1]));if(i<=n){s+=tr;if(i===n){a=s/n;r[i]=a;}}else{a=(a*(n-1)+tr)/n;r[i]=a;}}return r;}
// 状態（true/false/null）が「偽→真」に変わった日を合図にする
function events(n,f,gate){const st=new Int8Array(n).fill(-1);for(let i=0;i<n;i++){const v=f(i);st[i]=v===null?-1:(v?1:0);}const sig=new Uint8Array(n);let warm=n;for(let i=1;i<n;i++){if(st[i]!==-1&&st[i-1]!==-1&&warm===n)warm=i;if(st[i]===1&&st[i-1]===0&&(!gate||gate(i)))sig[i]=1;}return{sig,warm,st};}
const ok=(...xs)=>xs.every(x=>!isNaN(x));

const PRESETS=[
 {id:'gc',g:'trend',dir:1,t:'ゴールデンクロスは買い',d:'短期の移動平均線が長期線を下から上に抜けた日',p:[{k:'s',l:'短期線（日）',v:25,min:2,max:200},{k:'l',l:'長期線（日）',v:75,min:3,max:400}],chk:p=>p.s<p.l?'':'短期は長期より短くしてください',
  b:(D,p)=>{const a=sma(D.c,p.s),b=sma(D.c,p.l);return events(D.n,i=>ok(a[i],b[i])?a[i]>b[i]:null);}},
 {id:'dc',g:'trend',dir:-1,t:'デッドクロスは売り',d:'短期の移動平均線が長期線を上から下に抜けた日',p:[{k:'s',l:'短期線（日）',v:25,min:2,max:200},{k:'l',l:'長期線（日）',v:75,min:3,max:400}],chk:p=>p.s<p.l?'':'短期は長期より短くしてください',
  b:(D,p)=>{const a=sma(D.c,p.s),b=sma(D.c,p.l);return events(D.n,i=>ok(a[i],b[i])?a[i]<b[i]:null);}},
 {id:'maup',g:'trend',dir:1,t:'移動平均線を上に抜けたら買い',d:'終値が移動平均線を下から上に抜けた日',p:[{k:'n',l:'移動平均（日）',v:25,min:2,max:400}],
  b:(D,p)=>{const m=sma(D.c,p.n);return events(D.n,i=>ok(m[i])?D.c[i]>m[i]:null);}},
 {id:'madn',g:'trend',dir:-1,t:'移動平均線を下に抜けたら売り',d:'終値が移動平均線を上から下に抜けた日',p:[{k:'n',l:'移動平均（日）',v:25,min:2,max:400}],
  b:(D,p)=>{const m=sma(D.c,p.n);return events(D.n,i=>ok(m[i])?D.c[i]<m[i]:null);}},
 {id:'macd',g:'trend',dir:1,t:'MACDがシグナルを上に抜けたら買い',d:'MACD線がシグナル線を下から上に抜けた日',p:[{k:'f',l:'短期（日）',v:12,min:2,max:100},{k:'s',l:'長期（日）',v:26,min:3,max:200},{k:'g',l:'シグナル（日）',v:9,min:2,max:50}],chk:p=>p.f<p.s?'':'短期は長期より短くしてください',
  b:(D,p)=>{const a=ema(D.c,p.f),b=ema(D.c,p.s),m=new Float64Array(D.n);for(let i=0;i<D.n;i++)m[i]=a[i]-b[i];const g=ema(m,p.g);return events(D.n,i=>ok(m[i],g[i])?m[i]>g[i]:null);}},
 {id:'cloud',g:'trend',dir:1,t:'雲を上に抜けたら買い（一目均衡表）',d:'終値が雲の上限を下から上に抜けた日',p:[{k:'a',l:'転換線（日）',v:9,min:2,max:60},{k:'b',l:'基準線（日）',v:26,min:3,max:120},{k:'c',l:'先行スパン2（日）',v:52,min:5,max:240}],
  b:(D,p)=>{const hA=rmax(D.h,p.a),lA=rmin(D.l,p.a),hB=rmax(D.h,p.b),lB=rmin(D.l,p.b),hC=rmax(D.h,p.c),lC=rmin(D.l,p.c);const s=p.b-1;return events(D.n,i=>{const j=i-s;if(j<0)return null;const A=((hA[j]+lA[j])/2+(hB[j]+lB[j])/2)/2,B=(hC[j]+lC[j])/2;return ok(A,B)?D.c[i]>Math.max(A,B):null;});}},
 {id:'bbup',g:'trend',dir:1,t:'ボリンジャーバンド+2σを抜けたら買い（順張り）',d:'終値が上のバンドを下から上に抜けた日',p:[{k:'n',l:'期間（日）',v:20,min:5,max:200},{k:'k',l:'何σ',v:2,min:0.5,max:4,step:0.5}],
  b:(D,p)=>{const m=sma(D.c,p.n),s=sdev(D.c,p.n,m);return events(D.n,i=>ok(m[i],s[i])?D.c[i]>m[i]+p.k*s[i]:null);}},
 {id:'high',g:'trend',dir:1,t:'高値を更新したら買い',d:'終値がそれまでのN日間の高値を上回った日（久しぶりの更新）',p:[{k:'n',l:'何日間の高値か',v:250,min:5,max:1000}],
  b:(D,p)=>{const m=rmax(D.h,p.n);return events(D.n,i=>i<1||!ok(m[i-1])?null:D.c[i]>m[i-1]);}},

 {id:'rsilo',g:'osc',dir:1,t:'RSIが30を下回ったら買い',d:'RSIが下限を上から下に割った日（売られすぎ）',p:[{k:'n',l:'RSIの期間（日）',v:14,min:2,max:100},{k:'th',l:'下限',v:30,min:1,max:50}],
  b:(D,p)=>{const r=rsi(D.c,p.n);return events(D.n,i=>ok(r[i])?r[i]<p.th:null);}},
 {id:'rsihi',g:'osc',dir:-1,t:'RSIが70を上回ったら売り',d:'RSIが上限を下から上に超えた日（買われすぎ）',p:[{k:'n',l:'RSIの期間（日）',v:14,min:2,max:100},{k:'th',l:'上限',v:70,min:50,max:99}],
  b:(D,p)=>{const r=rsi(D.c,p.n);return events(D.n,i=>ok(r[i])?r[i]>p.th:null);}},
 {id:'bblo',g:'osc',dir:1,t:'ボリンジャーバンド−2σで買い（逆張り）',d:'終値が下のバンドを上から下に割った日',p:[{k:'n',l:'期間（日）',v:20,min:5,max:200},{k:'k',l:'何σ',v:2,min:0.5,max:4,step:0.5}],
  b:(D,p)=>{const m=sma(D.c,p.n),s=sdev(D.c,p.n,m);return events(D.n,i=>ok(m[i],s[i])?D.c[i]<m[i]-p.k*s[i]:null);}},
 {id:'bbhi',g:'osc',dir:-1,t:'ボリンジャーバンド+2σで売り（逆張り）',d:'終値が上のバンドを下から上に抜けた日',p:[{k:'n',l:'期間（日）',v:20,min:5,max:200},{k:'k',l:'何σ',v:2,min:0.5,max:4,step:0.5}],
  b:(D,p)=>{const m=sma(D.c,p.n),s=sdev(D.c,p.n,m);return events(D.n,i=>ok(m[i],s[i])?D.c[i]>m[i]+p.k*s[i]:null);}},
 {id:'stoch',g:'osc',dir:1,t:'ストキャスティクスの売られすぎ圏ゴールデンクロスは買い',d:'%Dが下限より下で、%Kが%Dを下から上に抜けた日',p:[{k:'n',l:'%Kの期間（日）',v:14,min:3,max:100},{k:'th',l:'下限',v:20,min:1,max:50}],
  b:(D,p)=>{const hh=rmax(D.h,p.n),ll=rmin(D.l,p.n),K=new Float64Array(D.n).fill(NaN);for(let i=0;i<D.n;i++)if(ok(hh[i],ll[i]))K[i]=hh[i]===ll[i]?50:(D.c[i]-ll[i])/(hh[i]-ll[i])*100;const Dd=sma(K,3);return events(D.n,i=>ok(K[i],Dd[i])?K[i]>Dd[i]:null,i=>Dd[i]<p.th);}},
 {id:'rci',g:'osc',dir:1,t:'RCIが−80から上向いたら買い',d:'RCIが下限を下から上に戻した日（底打ち）',p:[{k:'n',l:'RCIの期間（日）',v:9,min:3,max:52},{k:'th',l:'下限',v:-80,min:-99,max:0}],
  b:(D,p)=>{const r=rci(D.c,p.n);return events(D.n,i=>ok(r[i])?r[i]>p.th:null);}},
 {id:'dev',g:'osc',dir:1,t:'移動平均線から大きく下に離れたら買い',d:'終値が移動平均線よりX%以上下に離れた日（乖離率）',p:[{k:'n',l:'移動平均（日）',v:25,min:2,max:400},{k:'x',l:'何%下',v:10,min:1,max:50}],
  b:(D,p)=>{const m=sma(D.c,p.n);return events(D.n,i=>ok(m[i])?(D.c[i]/m[i]-1)*100<=-p.x:null);}},
 {id:'psy',g:'osc',dir:1,t:'サイコロジカルラインが25%以下なら買い',d:'直近N日のうち上がった日の割合が下限以下になった日',p:[{k:'n',l:'期間（日）',v:12,min:4,max:60},{k:'th',l:'下限（%）',v:25,min:0,max:50}],
  b:(D,p)=>{const up=new Uint8Array(D.n);for(let i=1;i<D.n;i++)up[i]=D.c[i]>D.c[i-1]?1:0;return events(D.n,i=>{if(i<p.n)return null;let s=0;for(let j=i-p.n+1;j<=i;j++)s+=up[j];return s/p.n*100<=p.th;});}},

 {id:'streak',g:'other',dir:1,t:'何日も続けて下がったら買い（逆張り）',d:'終値が前日より下がる日がN日続いた日',p:[{k:'n',l:'何日続けて',v:5,min:2,max:15}],
  b:(D,p)=>{let s=0;const st=new Int16Array(D.n);for(let i=1;i<D.n;i++){s=D.c[i]<D.c[i-1]?s+1:0;st[i]=s;}return events(D.n,i=>i<1?null:st[i]>=p.n);}},
 {id:'streakup',g:'other',dir:-1,t:'何日も続けて上がったら売り（逆張り）',d:'終値が前日より上がる日がN日続いた日',p:[{k:'n',l:'何日続けて',v:5,min:2,max:15}],
  b:(D,p)=>{let s=0;const st=new Int16Array(D.n);for(let i=1;i<D.n;i++){s=D.c[i]>D.c[i-1]?s+1:0;st[i]=s;}return events(D.n,i=>i<1?null:st[i]>=p.n);}},
 {id:'gapup',g:'other',dir:-1,t:'大きく窓を開けて上がった日は売り（窓埋め）',d:'始値が前日の高値よりX%以上高く始まった日',p:[{k:'x',l:'何%上で始まったか',v:2,min:0.5,max:20,step:0.5}],
  b:(D,p)=>events(D.n,i=>i<1?null:(D.o[i]/D.h[i-1]-1)*100>=p.x)},
 {id:'vol',g:'other',dir:1,t:'出来高が急に増えて上がった日は買い',d:'出来高が直前20日の平均のX倍以上で、終値が前日より上がった日',vol:true,p:[{k:'x',l:'平均の何倍',v:2,min:1.2,max:20,step:0.1}],
  b:(D,p)=>{const av=sma(D.v,20);return events(D.n,i=>i<21||!ok(av[i-1])||av[i-1]<=0?null:(D.v[i]>=p.x*av[i-1]&&D.c[i]>D.c[i-1]));}},
];
// 画面に出すことば（t: 定説の名前、d: 説明、l: 数字の欄の名前）
const TEXT={
 gc:{t:'ゴールデンクロスで買い',d:'短期線が長期線を上抜けた日',l:{s:'短期（日）',l:'長期（日）'}},
 dc:{t:'デッドクロスで売り',d:'短期線が長期線を下抜けた日',l:{s:'短期（日）',l:'長期（日）'}},
 maup:{t:'移動平均線の上抜けで買い',d:'終値が移動平均線を上抜けた日',l:{n:'期間（日）'}},
 madn:{t:'移動平均線の下抜けで売り',d:'終値が移動平均線を下抜けた日',l:{n:'期間（日）'}},
 macd:{t:'MACDのゴールデンクロスで買い',d:'MACDがシグナルを上抜けた日',l:{f:'短期',s:'長期',g:'シグナル'}},
 cloud:{t:'一目均衡表の雲抜けで買い',d:'終値が雲の上限を上抜けた日',l:{a:'転換線',b:'基準線',c:'先行スパン2'}},
 bbup:{t:'ボリンジャーバンド+2σ超えで買い（順張り）',d:'終値が+2σを上抜けた日',l:{n:'期間（日）',k:'幅（σ）'}},
 high:{t:'高値更新で買い',d:'終値が過去N日の高値を超えた日',l:{n:'期間（日）'}},
 rsilo:{t:'RSI 30割れで買い',d:'RSIが下限を下回った日（売られすぎ）',l:{n:'期間（日）',th:'下限'}},
 rsihi:{t:'RSI 70超えで売り',d:'RSIが上限を上回った日（買われすぎ）',l:{n:'期間（日）',th:'上限'}},
 bblo:{t:'ボリンジャーバンド−2σで買い（逆張り）',d:'終値が−2σを下回った日',l:{n:'期間（日）',k:'幅（σ）'}},
 bbhi:{t:'ボリンジャーバンド+2σで売り（逆張り）',d:'終値が+2σを上回った日',l:{n:'期間（日）',k:'幅（σ）'}},
 stoch:{t:'ストキャスティクスの売られすぎ圏ゴールデンクロスで買い',d:'%Dが下限より下で、%Kが%Dを上抜けた日',l:{n:'期間（日）',th:'下限'}},
 rci:{t:'RCIの−80からの反転で買い',d:'RCIが下限を下から上抜けた日',l:{n:'期間（日）',th:'下限'}},
 dev:{t:'移動平均乖離率のマイナス拡大で買い',d:'終値が移動平均線からX%以上下に離れた日',l:{n:'期間（日）',x:'乖離（%）'}},
 psy:{t:'サイコロジカルライン25%以下で買い',d:'直近N日の上昇日の割合が下限以下の日',l:{n:'期間（日）',th:'下限（%）'}},
 streak:{t:'連続下落で買い（逆張り）',d:'N日続けて下落した日',l:{n:'連続日数'}},
 streakup:{t:'連続上昇で売り（逆張り）',d:'N日続けて上昇した日',l:{n:'連続日数'}},
 gapup:{t:'上窓で売り（窓埋め）',d:'始値が前日高値よりX%以上高い日',l:{x:'窓（%）'}},
 vol:{t:'出来高急増の上昇で買い',d:'出来高が20日平均のX倍以上で上昇した日',l:{x:'平均の何倍'}},
};
PRESETS.forEach(P=>{const x=TEXT[P.id];if(!x)return;P.t=x.t;P.d=x.d;P.p.forEach(q=>{if(x.l&&x.l[q.k])q.l=x.l[q.k];});});
// 条件として使うときの名前（nm）、状態の説明（sd）、初期値（fd）
const META={
 gc:{nm:'ゴールデンクロス状態',sd:p=>`${p.s}日線が${p.l}日線より上`},
 dc:{nm:'デッドクロス状態',sd:p=>`${p.s}日線が${p.l}日線より下`},
 maup:{nm:'移動平均線より上',sd:p=>`終値が${p.n}日線より上`,fd:{n:200}},
 madn:{nm:'移動平均線より下',sd:p=>`終値が${p.n}日線より下`,fd:{n:200}},
 macd:{nm:'MACD',sd:()=>'MACDがシグナルより上'},
 cloud:{nm:'一目均衡表の雲',sd:()=>'終値が雲より上'},
 bbup:{nm:'ボリンジャー+σより上',sd:p=>`終値が+${p.k}σより上`},
 high:{nm:'高値更新',sd:p=>`終値が過去${p.n}日の高値より上`},
 rsilo:{nm:'RSI 売られすぎ',sd:p=>`RSI(${p.n})が${p.th}未満`},
 rsihi:{nm:'RSI 買われすぎ',sd:p=>`RSI(${p.n})が${p.th}超`},
 bblo:{nm:'ボリンジャー−σより下',sd:p=>`終値が−${p.k}σより下`},
 bbhi:{nm:'ボリンジャー+σより上',sd:p=>`終値が+${p.k}σより上`},
 stoch:{nm:'ストキャスティクス',sd:()=>'%Kが%Dより上'},
 rci:{nm:'RCI',sd:p=>`RCI(${p.n})が${p.th}より上`},
 dev:{nm:'移動平均乖離率',sd:p=>`${p.n}日線から${p.x}%以上下`},
 psy:{nm:'サイコロジカルライン',sd:p=>`サイコロジカル(${p.n})が${p.th}%以下`},
 streak:{nm:'連続下落',sd:p=>`${p.n}日以上連続で下落中`},
 streakup:{nm:'連続上昇',sd:p=>`${p.n}日以上連続で上昇中`},
 gapup:{nm:'上窓',sd:p=>`前日高値より${p.x}%以上高く始まった`},
 vol:{nm:'出来高急増',sd:p=>`出来高が平均の${p.x}倍以上で上昇`},
};
PRESETS.forEach(P=>Object.assign(P,META[P.id]));
// 条件の日を表す印（state: その日にその状態 / recent: 直近w日以内にその合図）
function condMask(D,c){const r=c.P.b(D,c.params),m=new Uint8Array(D.n);if(c.mode==='recent'){let last=-1e9;for(let i=0;i<D.n;i++){if(r.sig[i])last=i;m[i]=i-last<c.w?1:0;}}else{for(let i=0;i<D.n;i++)m[i]=r.st[i]===1?1:0;}return{m,warm:r.warm};}

function mulberry32(a){return function(){a|=0;a=a+0x6D2B79F5|0;let t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296;};}
function hashStr(s){let h=2166136261;for(let i=0;i<s.length;i++){h^=s.charCodeAt(i);h=Math.imul(h,16777619);}return h>>>0;}

// 偽薬（1銘柄）：同じ範囲のでたらめな日に、同じ回数だけ入る
function placeboRand(groups,trials,rng){const K=groups.reduce((s,g)=>s+g.pos.length,0),pm=new Float64Array(trials);for(let t=0;t<trials;t++){let s=0;for(const g of groups){const N=g.L.length,k=g.pos.length;for(let j=0;j<k;j++)s+=g.L[(rng()*N)|0];}pm[t]=s/K;}return pm;}
// 偽薬（まとめて）：合図の日付の並びを保ったまま、全銘柄そろって別の時期にずらす
function placeboShift(groups,trials,rng,minShift){const K=groups.reduce((s,g)=>s+g.pos.length,0),Lmax=Math.max(...groups.map(g=>g.L.length)),lo=Math.min(minShift,Math.floor(Lmax/4)),span=Math.max(1,Lmax-2*lo),pm=new Float64Array(trials);for(let t=0;t<trials;t++){const sh=lo+((rng()*span)|0);let s=0;for(const g of groups){const n=g.L.length;for(const j of g.pos)s+=g.L[(j+sh)%n];}pm[t]=s/K;}return pm;}
const mean=a=>a.length?a.reduce((x,y)=>x+y,0)/a.length:NaN;
function median(a){if(!a.length)return NaN;const s=[...a].sort((x,y)=>x-y),m=s.length>>1;return s.length%2?s[m]:(s[m-1]+s[m])/2;}
function pTail(pm,x){let ge=0,le=0;for(const v of pm){if(v>=x-1e-12)ge++;if(v<=x+1e-12)le++;}return{ge,le,pBetter:(ge+1)/(pm.length+1),pWorse:(le+1)/(pm.length+1)};}

// 1銘柄ぶんの下ごしらえ：損益・出口・合図の日・条件の日
// 出口：損切り・利確・追いかける損切りのうち先に届いたもの。届かなければ最長の日の終値。
// 同じ日に損切りと利確の両方に届いたら損切りが先（不利なほうに寄せる）。窓で飛び越えたらその日の始値。
function prepare(D,P,params,opt,conds){
  conds=conds||[];
  const n=D.n,base=P.b(D,params),mask=new Uint8Array(n).fill(1);let warm=base.warm;
  for(const c of conds){const r=condMask(D,c);if(r.warm>warm)warm=r.warm;for(let i=0;i<n;i++)mask[i]&=r.m[i];}
  let i0=0;while(i0<n&&D.d[i0]<opt.from)i0++;
  let i1=n-1;while(i1>=0&&D.d[i1]>opt.to)i1--;
  const H=opt.H,cost=opt.cost/100,dir=P.dir,ex=opt.exit||{on:false},elig=[],last=Math.min(i1,n-1-H);
  const R=new Float64Array(n).fill(NaN),X=new Int32Array(n).fill(-1),XP=new Float64Array(n).fill(NaN),WHY=new Int8Array(n),RISK=new Float64Array(n).fill(NaN);
  const atr=ex.on&&(ex.stop==='atr'||ex.tp==='atr'||ex.trail)?atrW(D,14):null;if(atr&&warm<15)warm=15;
  for(let t=Math.max(i0,warm);t<=last;t++){
    const e=D.o[t+1];let xp=NaN,why=0,xj=t+H,sd=NaN;
    if(ex.on){
      if(ex.stop==='pct')sd=ex.sv/100;else if(ex.stop==='atr')sd=ex.sv*atr[t]/e;
      let td=NaN;if(ex.tp==='pct')td=ex.tv/100;else if(ex.tp==='atr')td=ex.tv*atr[t]/e;else if(ex.tp==='r')td=ex.tv*sd;
      const trD=ex.trail?ex.tk*atr[t]:NaN,stopPx=isNaN(sd)?NaN:e*(1-dir*sd),tgtPx=isNaN(td)?NaN:e*(1+dir*td);
      let best=e,trailPx=NaN;
      for(let j=t+1;j<=t+H;j++){
        const o=D.o[j],h=D.h[j],l=D.l[j];let sp=stopPx,sw=2;
        if(!isNaN(trailPx)&&(isNaN(sp)||(dir>0?trailPx>sp:trailPx<sp))){sp=trailPx;sw=3;}
        if(j>t+1){
          if(!isNaN(sp)&&(dir>0?o<=sp:o>=sp)){xp=o;why=sw;xj=j;break;}
          if(!isNaN(tgtPx)&&(dir>0?o>=tgtPx:o<=tgtPx)){xp=o;why=1;xj=j;break;}
        }
        if(!isNaN(sp)&&(dir>0?l<=sp:h>=sp)){xp=sp;why=sw;xj=j;break;}
        if(!isNaN(tgtPx)&&(dir>0?h>=tgtPx:l<=tgtPx)){xp=tgtPx;why=1;xj=j;break;}
        if(!isNaN(trD)){best=dir>0?Math.max(best,h):Math.min(best,l);trailPx=best-dir*trD;}
      }
    }
    if(isNaN(xp)){xp=D.c[t+H];why=0;xj=t+H;}
    X[t]=xj;XP[t]=xp;WHY[t]=why;RISK[t]=sd;R[t]=dir*(xp/e-1)-cost;elig.push(t);
  }
  const pick=ok=>{const out=[];let busy=-1;for(const t of elig){if(!ok(t))continue;if(opt.ovl&&t<busy)continue;out.push(t);busy=X[t];}return out;};
  return{D,elig,R,X,XP,WHY,RISK,mask,i0,i1,H,dir,trades:pick(t=>base.sig[t]&&mask[t]),t0:conds.length?pick(t=>base.sig[t]):null};
}

// 評価：1銘柄でも、まとめてでも同じ流れ
function evaluate(parts,opt){
  const T=2000,pooled=parts.length>1,minS=Math.max(60,opt.H*3);
  const PL=(groups,trials,key)=>{const rng=mulberry32(hashStr(key));return pooled?placeboShift(groups,trials,rng,minS):placeboRand(groups,trials,rng);};
  let K=0,N=0;const sr=[];
  for(const p of parts){p.rv=p.elig.map(t=>p.R[t]);p.sr=p.trades.map(t=>p.R[t]);p.K=p.trades.length;p.sigMean=mean(p.sr);p.baseMean=mean(p.rv);p.baseWin=p.rv.length?p.rv.filter(r=>r>0).length/p.rv.length:NaN;p.pos=new Int32Array(p.D.n).fill(-1);p.elig.forEach((t,j)=>p.pos[t]=j);K+=p.K;N+=p.elig.length;for(const r of p.sr)sr.push(r);}
  const wmean=(f,w)=>{let s=0,ws=0;for(const p of parts){const x=f(p),k=w(p);if(k&&!isNaN(x)){s+=x*k;ws+=k;}}return ws?s/ws:NaN;};
  const res={parts,K,N,H:opt.H,dir:parts.length?parts[0].dir:1,pooled};
  if(!pooled&&parts.length)Object.assign(res,{trades:parts[0].trades,R:parts[0].R,X:parts[0].X,XP:parts[0].XP,WHY:parts[0].WHY,i0:parts[0].i0,i1:parts[0].i1});
  const yrs=p=>{if(!p.elig.length)return 0;const t=x=>Date.UTC((x/10000)|0,((x/100)|0)%100-1,x%100);return(t(p.D.d[p.elig[p.elig.length-1]])-t(p.D.d[p.elig[0]]))/864e5/365.25;};
  res.years=!pooled&&parts.length?yrs(parts[0]):0;
  res.baseMean=K?wmean(p=>p.baseMean,p=>p.K):wmean(p=>p.baseMean,p=>p.elig.length);
  res.baseWin=K?wmean(p=>p.baseWin,p=>p.K):wmean(p=>p.baseWin,p=>p.elig.length);
  if(pooled){const big=parts.filter(p=>p.K>=5);res.consist={m:big.length,g:big.filter(p=>p.sigMean>p.baseMean).length};}
  if(parts.some(p=>p.t0)){
    const c={K0:0},s0=[];
    for(const p of parts){c.K0+=p.t0.length;for(const t of p.t0)s0.push(p.R[t]);p.rvC=[];p.posC=new Int32Array(p.D.n).fill(-1);for(const t of p.elig)if(p.mask[t]){p.posC[t]=p.rvC.length;p.rvC.push(p.R[t]);}}
    c.mean0=mean(s0);c.nC=parts.reduce((s,p)=>s+p.rvC.length,0);
    c.baseC=K?wmean(p=>mean(p.rvC),p=>p.K):wmean(p=>mean(p.rvC),p=>p.rvC.length);
    if(c.K0)c.p0=pTail(PL(parts.filter(p=>p.t0.length).map(p=>({L:p.rv,pos:p.t0.map(t=>p.pos[t])})),T,opt.key+'t'),c.mean0).pBetter;
    res.combo=c;
  }
  if(!K)return res;
  res.sigMean=mean(sr);res.sigMed=median(sr);res.sigWin=sr.filter(r=>r>0).length/K;
  if(opt.exit&&opt.exit.on){const cnt=[0,0,0,0];let hold=0,rs=0,rn=0;for(const p of parts)for(const t of p.trades){cnt[p.WHY[t]]++;hold+=p.X[t]-t;if(p.RISK[t]>0){rs+=p.R[t]/p.RISK[t];rn++;}}res.exitStats={cnt,hold:hold/K,avgR:rn?rs/rn:NaN};}
  const pm=PL(parts.filter(p=>p.K).map(p=>({L:p.rv,pos:p.trades.map(t=>p.pos[t])})),T,opt.key);
  Object.assign(res,pTail(pm,res.sigMean));res.pm=pm;res.T=T;
  // 前半と後半：全体の日付の真ん中で分ける
  const ds=[];for(const p of parts)for(const t of p.elig)ds.push(p.D.d[t]);ds.sort((a,b)=>a-b);const mid=ds[Math.floor(ds.length/2)];
  res.halves=[0,1].map(h=>{
    const inH=d=>h?d>=mid:d<mid,groups=[],srH=[],allRv=[];let from=Infinity,to=-Infinity,wb=0,wk=0;
    for(const p of parts){const L=[],pos=[],at=new Map();
      for(const t of p.elig){const d=p.D.d[t];if(!inH(d))continue;at.set(t,L.length);L.push(p.R[t]);allRv.push(p.R[t]);if(d<from)from=d;if(d>to)to=d;}
      for(const t of p.trades)if(at.has(t)){pos.push(at.get(t));srH.push(p.R[t]);}
      if(pos.length){groups.push({L,pos});wb+=mean(L)*pos.length;wk+=pos.length;}}
    const o={from,to,K:srH.length,sig:mean(srH),base:wk?wb/wk:mean(allRv)};o.diff=o.sig-o.base;
    if(o.K)o.p=pTail(PL(groups,1000,opt.key+'h'+h),o.sig).pBetter;
    return o;});
  // 条件が成り立つ日だけから取った偽薬と比べる
  if(res.combo&&res.combo.nC)res.combo.pC=pTail(PL(parts.filter(p=>p.K).map(p=>({L:p.rvC,pos:p.trades.map(t=>p.posC[t])})),T,opt.key+'c'),res.sigMean).pBetter;
  return res;
}
function backtest(D,P,params,opt,conds){return evaluate([prepare(D,P,params,opt,conds)],opt);}

function judge(res,tests){
  const v=judgeCore(res,tests),c=res.combo;
  if(c&&res.K>=20&&c.nC&&(v.cls==='good'||(v.cls==='watch'&&res.pBetter<0.05)))
    v.body+=c.pC<0.05?`条件の日だけの偽薬と比べても合図が上でした（${fmtP(c.pC)}）。`:`ただし条件の日だけの偽薬と比べると差は偶然の範囲（${fmtP(c.pC)}）。良さは条件によるものです。`;
  if(res.consist&&res.K>=20&&res.consist.m)v.body+=`${res.consist.m}銘柄中${res.consist.g}銘柄で偽薬より上。`;
  return v;
}
function judgeCore(res,tests){
  const alpha=0.05/tests;
  if(!res.K||res.K<20)return{cls:'none',chip:'回数不足',head:`合図が${res.K||0}回しかなく、判定できません`,body:'20回以上が目安。期間を延ばす・条件をゆるめる・「まとめて確かめる」を試してください。'};
  const [a,b]=res.halves,hOK=a.K>=5&&b.K>=5;
  const bothGood=hOK&&a.diff>0&&b.diff>0,bothBad=hOK&&a.diff<0&&b.diff<0;
  if(res.pBetter<alpha&&bothGood)return{cls:'good',chip:'偽薬より良い',head:'でたらめに入るより、はっきり良い成績',body:`偽薬2,000回中、合図以上は${res.ge}回（${fmtP(res.pBetter)}）だけ。前半・後半とも合図が上。※過去データでの結果です。`};
  if(res.pWorse<alpha&&bothBad)return{cls:'bad',chip:'偽薬より悪い',head:'でたらめに入るより、はっきり悪い成績',body:`偽薬2,000回中、合図以下は${res.le}回（${fmtP(res.pWorse)}）だけ。前半・後半とも合図が下。定説と逆の結果です。`};
  if(res.pBetter<0.05||res.pWorse<0.05){
    const good=res.pBetter<0.05,p=good?res.pBetter:res.pWorse,why=[];
    if(p>=alpha)why.push(`${tests}通り試したので合格ラインは${fmtP(alpha)}。今回は${fmtP(p)}で届きません。`);
    if(good?!bothGood:!bothBad)why.push(hOK?'前半と後半で向きがそろいません。':'前半か後半の合図が5回未満です。');
    return{cls:'watch',chip:'偶然の範囲',head:good?'良さそうだが、偶然でも出る程度の差':'悪そうだが、偶然でも出る程度の差',body:why.join('')};
  }
  return{cls:'none',chip:'差なし',head:'でたらめに入るのと変わらない',body:`偽薬2,000回中${res.ge}回（${(res.ge/res.T*100).toFixed(0)}%）が合図以上の成績でした。`};
}
// 割合を「%」で見せる
function fmtP(p){const x=p*100;return x<0.1?'0.1%未満':x<1?x.toFixed(2).replace(/0+$/,'').replace(/\.$/,'')+'%':x.toFixed(1).replace(/\.0$/,'')+'%';}
/*ENGINE-END*/

// ---------- 画面 ----------
const ROOT=document.getElementById('mw-sim');if(!ROOT)return;
const $=id=>document.getElementById('sim-'+id);
const S={frame:'trad',g:'trend',preset:'gc',params:{},conds:[],ds:null,dsId:'N225',index:[],cache:{},tests:new Set(),last:null};
try{const t=JSON.parse(sessionStorage.getItem('kenshou-tests')||'[]');t.forEach(k=>S.tests.add(k));}catch(e){}
const pct=(x,d=2)=>isNaN(x)?'—':(x>=0?'+':'−')+Math.abs(x*100).toFixed(d)+'%';
const fmtDate=d=>{const s=String(d);return `${s.slice(0,4)}/${s.slice(4,6)}/${s.slice(6,8)}`;};
const fmtPrice=x=>x>=1000?x.toLocaleString('ja-JP',{maximumFractionDigits:1}):x.toLocaleString('ja-JP',{minimumFractionDigits:x<10?4:1,maximumFractionDigits:x<10?4:2});
const WHYL=['期限','利確','損切り','トレーリング'];
function el(tag,attrs,text){const e=document.createElement(tag);if(attrs)for(const k in attrs)e.setAttribute(k,attrs[k]);if(text!=null)e.textContent=text;return e;}

function renderPresets(){
  const box=$('presets');box.textContent='';
  ROOT.querySelectorAll('.tab').forEach(b=>b.setAttribute('aria-selected',b.dataset.g===S.g?'true':'false'));
  for(const P of PRESETS.filter(p=>p.g===S.g)){
    const off=P.vol&&S.ds&&!S.ds.hasVol;
    const lab=el('label',{class:'preset'+(P.id===S.preset?' is-on':'')+(off?' is-off':''),for:'sim-p-'+P.id});
    const inp=el('input',{type:'radio',name:'simpreset',id:'sim-p-'+P.id,value:P.id});if(P.id===S.preset)inp.checked=true;if(off)inp.disabled=true;
    const tx=el('span');const t=el('span',{class:'t'},P.t);t.appendChild(el('span',{class:'dirtag '+(P.dir>0?'dir-buy':'dir-sell')},P.dir>0?'買い':'売り'));
    tx.appendChild(t);tx.appendChild(el('span',{class:'d'},off?'このデータには出来高がないため使えません':P.d));
    lab.appendChild(inp);lab.appendChild(tx);box.appendChild(lab);
    inp.addEventListener('change',()=>{S.preset=P.id;S.params={};renderPresets();renderParams();run();});
  }
}
function curPreset(){return PRESETS.find(p=>p.id===S.preset);}
function renderParams(){
  const P=curPreset(),box=$('params');box.textContent='';
  for(const q of P.p){
    if(S.params[q.k]==null)S.params[q.k]=q.v;
    const lab=el('label',{class:'field',for:'sim-q-'+q.k},q.l);
    const inp=el('input',{type:'number',id:'sim-q-'+q.k,min:q.min,max:q.max,step:q.step||1,value:S.params[q.k],inputmode:'decimal'});
    inp.addEventListener('change',()=>{let v=parseFloat(inp.value);if(isNaN(v))v=q.v;v=Math.min(q.max,Math.max(q.min,v));inp.value=v;S.params[q.k]=v;run();});
    lab.appendChild(inp);box.appendChild(lab);
  }
}
// ---------- 組み合わせ ----------
const COMBOS=[
 {t:'上昇トレンドの押し目買い',trig:'rsilo',tp:{n:14,th:30},conds:[{id:'maup',mode:'state',w:5,params:{n:200}}]},
 {t:'雲の上で−2σ',trig:'bblo',tp:{n:20,k:2},conds:[{id:'cloud',mode:'state',w:5,params:{a:9,b:26,c:52}}]},
 {t:'出来高を伴うゴールデンクロス',trig:'gc',tp:{s:25,l:75},conds:[{id:'vol',mode:'recent',w:5,params:{x:2}}]},
 {t:'RSI売られすぎ後のMACD',trig:'macd',tp:{f:12,s:26,g:9},conds:[{id:'rsilo',mode:'recent',w:10,params:{n:14,th:30}}]},
 {t:'下降トレンドの戻り売り',trig:'rsihi',tp:{n:14,th:70},conds:[{id:'madn',mode:'state',w:5,params:{n:200}}]},
];
const byId=id=>PRESETS.find(p=>p.id===id);
function defParams(P,asCond){const o={};P.p.forEach(q=>o[q.k]=asCond&&P.fd&&P.fd[q.k]!=null?P.fd[q.k]:q.v);return o;}
function condText(c){const P=byId(c.id);return c.mode==='recent'?`${c.w}日以内に「${P.t}」の合図`:`${P.sd(c.params)}`;}
function renderCombos(){
  const box=$('combos');box.textContent='';
  for(const cb of COMBOS){
    const off=cb.conds.some(c=>byId(c.id).vol)&&S.ds&&!S.ds.hasVol;
    const b=el('button',{type:'button',class:'combo',title:`${byId(cb.trig).t}＋${cb.conds.map(condText).join('＋')}`},cb.t);if(off)b.disabled=true;
    b.addEventListener('click',()=>{const P=byId(cb.trig);S.g=P.g;S.preset=P.id;S.params={...cb.tp};S.conds=cb.conds.map(c=>({...c,params:{...c.params}}));renderPresets();renderParams();renderConds();run();});
    box.appendChild(b);
  }
}
function numField(id,label,val,min,max,step,set){
  const lab=el('label',{class:'field',for:id},label);const inp=el('input',{type:'number',id,min,max,step,value:val,inputmode:'decimal'});
  inp.addEventListener('change',()=>{let v=parseFloat(inp.value);if(isNaN(v))v=val;v=Math.min(max,Math.max(min,v));inp.value=v;set(v);ROOT.querySelectorAll('.cond-desc').forEach((p,i)=>{if(S.conds[i])p.textContent=condText(S.conds[i]);});run();});
  lab.appendChild(inp);return lab;
}
function renderConds(){
  const box=$('conds');box.textContent='';
  S.conds.forEach((c,idx)=>{
    const P=byId(c.id),card=el('div',{class:'cond'}),top=el('div',{class:'cond-top'});
    top.appendChild(el('b',null,'条件'+(idx+1)));
    const rm=el('button',{type:'button',class:'linkbtn'},'外す');rm.addEventListener('click',()=>{S.conds.splice(idx,1);renderConds();run();});top.appendChild(rm);card.appendChild(top);
    const f1=el('label',{class:'field',for:`sim-c${idx}-id`},'指標');const s1=el('select',{id:`sim-c${idx}-id`});
    for(const [g,gl] of [['trend','トレンド系'],['osc','オシレーター系'],['other','値動き・出来高']]){const og=el('optgroup',{label:gl});for(const q of PRESETS.filter(p=>p.g===g)){const o=el('option',{value:q.id},q.nm);if(q.id===c.id)o.selected=true;if(q.vol&&S.ds&&!S.ds.hasVol)o.disabled=true;og.appendChild(o);}s1.appendChild(og);}
    s1.addEventListener('change',()=>{c.id=s1.value;c.params=defParams(byId(c.id),true);renderConds();run();});f1.appendChild(s1);card.appendChild(f1);
    const f2=el('label',{class:'field',for:`sim-c${idx}-mode`},'使い方');const s2=el('select',{id:`sim-c${idx}-mode`});
    [['state','その日にこの状態なら'],['recent','直近N日以内に合図が出ていたら']].forEach(([v,t])=>{const o=el('option',{value:v},t);if(c.mode===v)o.selected=true;s2.appendChild(o);});
    s2.addEventListener('change',()=>{c.mode=s2.value;renderConds();run();});f2.appendChild(s2);card.appendChild(f2);
    const grid=el('div',{class:'params'});
    if(c.mode==='recent')grid.appendChild(numField(`sim-c${idx}-w`,'何日以内',c.w,1,60,1,v=>{c.w=v;}));
    for(const q of P.p)grid.appendChild(numField(`sim-c${idx}-${q.k}`,q.l,c.params[q.k],q.min,q.max,q.step||1,v=>{c.params[q.k]=v;}));
    card.appendChild(grid);card.appendChild(el('p',{class:'cond-desc'},condText(c)));box.appendChild(card);
  });
  const add=$('addCond');add.disabled=S.conds.length>=2;add.textContent=S.conds.length>=2?'条件は2つまでです':'＋ 条件を足す';
}

const frameOf=e=>e.frame||(e.kind==='読み込んだCSV'?'any':'trad');
const HOLDS={trad:[[1,'翌日だけ'],[5,'約1週間'],[20,'約1か月'],[60,'約3か月']]};
function renderHold(){
  const box=$('holdSeg'),cur=[...box.querySelectorAll('input')].findIndex(r=>r.checked),pos=cur<0?2:cur;box.textContent='';
  HOLDS[S.frame].forEach(([v,sub],i)=>{const lab=el('label'),inp=el('input',{type:'radio',name:'simhold',id:'sim-h'+i,value:v});if(i===pos)inp.checked=true;inp.addEventListener('change',run);const sp=el('span',null,v+'日');sp.appendChild(el('small',null,sub));lab.appendChild(inp);lab.appendChild(sp);box.appendChild(lab);});
  $('holdHint').textContent='翌日の始値で入り、この日数（営業日）後の終値で決済。';
}
function renderSymbols(){
  const sel=$('sym');sel.textContent='';const groups={};
  for(const e of S.index){const f=frameOf(e);if(f!==S.frame&&f!=='any')continue;(groups[e.kind]=groups[e.kind]||[]).push(e);}
  const order=['まとめて確かめる','指数','株','為替','商品','読み込んだCSV'];
  const KL={'まとめて確かめる':'まとめて確かめる','指数':'指数','株':'日本株','為替':'FX（通貨ペア）','商品':'金・銀','読み込んだCSV':'読み込んだCSV'};
  for(const g of order){if(!groups[g])continue;const og=el('optgroup',{label:KL[g]||g});for(const e of groups[g]){const o=el('option',{value:e.id},e.name);if(e.id===S.dsId)o.selected=true;og.appendChild(o);}sel.appendChild(og);}
}
function renderYears(){
  const D=S.ds,y0=Math.floor((D.pool?D.first:D.d[0])/10000),y1=Math.floor((D.pool?D.last:D.d[D.n-1])/10000);
  for(const id of ['y0','y1']){const s=$(id);s.textContent='';for(let y=y0;y<=y1;y++){s.appendChild(el('option',{value:y},y+'年'));}}
  $('y0').value=y0;$('y1').value=y1;
}
function prep(raw,meta){
  const n=raw.d.length,D={d:Int32Array.from(raw.d),o:Float64Array.from(raw.o),h:Float64Array.from(raw.h),l:Float64Array.from(raw.l),c:Float64Array.from(raw.c),v:Float64Array.from(raw.v||new Array(n).fill(0)),n,name:meta.name,kind:meta.kind};
  let z=0;for(let i=0;i<n;i++)if(!(D.v[i]>0))z++;D.hasVol=z/n<0.01;return D;
}
async function fetchDs(id){
  if(!S.cache[id]){const meta=S.index.find(e=>e.id===id);const r=await fetch('sim-data/'+id+'.json');if(!r.ok)throw new Error('価格データを読み込めませんでした');S.cache[id]=prep(await r.json(),meta);}
  return S.cache[id];
}
async function loadDs(id){
  const meta=S.index.find(e=>e.id===id);
  if(meta.pool){
    if(meta.pool.some(x=>!S.cache[x]))showVerdict({cls:'none',chip:'読み込み中',head:`${meta.pool.length}銘柄の値動きを読み込んでいます…`,body:''});
    const members=await Promise.all(meta.pool.map(fetchDs));
    S.ds={pool:true,members,name:meta.name,hasVol:members.some(m=>m.hasVol),first:Math.min(...members.map(m=>m.d[0])),last:Math.max(...members.map(m=>m.d[m.n-1]))};
  }else S.ds=await fetchDs(id);
  S.dsId=id;
  if(curPreset().vol&&!S.ds.hasVol){S.preset=PRESETS.find(p=>p.g===S.g&&!p.vol).id;S.params={};}
  renderYears();renderPresets();renderParams();renderConds();renderCombos();
}

function key(){const o={from:+$('y0').value*10000+101,to:+$('y1').value*10000+1231};return [S.dsId,S.preset,JSON.stringify(S.params),JSON.stringify(S.conds),JSON.stringify(exitOpt()),hold(),$('cost').value,o.from,o.to,$('ovl').checked?1:0].join('|');}
const hold=()=>+ROOT.querySelector('input[name="simhold"]:checked').value;
function exitOpt(){const e={stop:$('stopMode').value,sv:+$('stopVal').value,tp:$('tpMode').value,tv:+$('tpVal').value,trail:$('trail').checked,tk:+$('trailVal').value};e.on=e.stop!=='none'||e.tp!=='none'||e.trail;return e;}
function exitText(o){const e=o.exit;if(!e||!e.on)return `${o.H}日保有`;const a=[];if(e.stop==='pct')a.push(`損切り${e.sv}%`);if(e.stop==='atr')a.push(`損切り 平均値幅×${e.sv}`);if(e.tp==='pct')a.push(`利確${e.tv}%`);if(e.tp==='atr')a.push(`利確 平均値幅×${e.tv}`);if(e.tp==='r')a.push(`利確 損切り幅×${e.tv}`);if(e.trail)a.push(`トレーリング 平均値幅×${e.tk}`);a.push(`最長${o.H}日`);return a.join('・');}
const XDEF={stop:{pct:5,atr:2},tp:{pct:10,atr:3,r:2}};
function syncExit(ev){
  const sm=$('stopMode').value,tm=$('tpMode').value,id=ev&&ev.target&&ev.target.id;
  if(id==='stopMode'&&sm!=='none')$('stopVal').value=XDEF.stop[sm];
  if(id==='tpMode'&&tm!=='none')$('tpVal').value=XDEF.tp[tm];
  $('stopVal').disabled=sm==='none';$('tpVal').disabled=tm==='none';$('trailVal').disabled=!$('trail').checked;
  $('stopUnit').textContent=sm==='pct'?'%':sm==='atr'?'倍':'幅';
  $('tpUnit').textContent=tm==='pct'?'%':tm==='none'?'幅':'倍';
}

function run(){
  if(!S.ds)return;
  const P=curPreset();
  let y0=+$('y0').value,y1=+$('y1').value;if(y0>y1){[y0,y1]=[y1,y0];$('y0').value=y0;$('y1').value=y1;}
  let msg=P.chk?P.chk(S.params):'';
  for(const [i,c] of S.conds.entries()){const CP=byId(c.id);if(msg)break;if(CP.chk&&CP.chk(c.params))msg=`条件${i+1}：${CP.chk(c.params)}`;else if(CP.vol&&!S.ds.hasVol)msg=`条件${i+1}：このデータには出来高がないため、出来高の条件は使えません`;}
  if(!msg){const e=exitOpt();if(e.tp==='r'&&e.stop==='none')msg='「損切り幅の何倍」を使うときは、損切りも設定してください';else if((e.stop!=='none'&&!(e.sv>0))||(e.tp!=='none'&&!(e.tv>0))||(e.trail&&!(e.tk>0)))msg='損切り・利確の幅は0より大きくしてください';}
  if(msg){showVerdict({cls:'none',chip:'条件を直してください',head:msg,body:''});return;}
  const k=key();
  const opt={from:y0*10000+101,to:y1*10000+1231,H:hold(),cost:+$('cost').value,ovl:$('ovl').checked,key:k,exit:exitOpt()};
  $('results').classList.add('busy');
  requestAnimationFrame(()=>setTimeout(()=>{
    const conds=S.conds.map(c=>({P:byId(c.id),params:c.params,mode:c.mode,w:c.w}));
    let res;
    if(S.ds.pool){const usesVol=P.vol||S.conds.some(c=>byId(c.id).vol);const mem=usesVol?S.ds.members.filter(m=>m.hasVol):S.ds.members;res=evaluate(mem.map(D=>prepare(D,P,S.params,opt,conds)),opt);res.excluded=usesVol?S.ds.members.filter(m=>!m.hasVol).map(m=>m.name):[];}
    else res=backtest(S.ds,P,S.params,opt,conds);
    if(res.K>0){S.tests.add(k);try{sessionStorage.setItem('kenshou-tests',JSON.stringify([...S.tests]));}catch(e){}}
    S.last={res,P,opt,y0,y1,ds:S.ds};
    draw();$('results').classList.remove('busy');
  },0));
}
function paramText(P){return P.p.map(q=>`${q.l.replace(/（.*?）/,'')}：${S.params[q.k]}`).join('、');}
function showVerdict(v){
  const box=$('verdict');box.className='verdict v-'+v.cls;$('vChip').textContent=v.chip;$('vHead').textContent=v.head;$('vBody').textContent=v.body;
}
function draw(){
  const {res,P,opt,y0,y1,ds}=S.last,tests=Math.max(1,S.tests.size);
  $('vWhat').textContent=`${P.t}${S.conds.map(c=>'＋'+condText(c)).join('')}｜${ds.name} ${y0}〜${y1}年｜${paramText(P)}｜${exitText(opt)}｜コスト${opt.cost}%`;
  const v=judge(res,tests);showVerdict(v);
  $('tN').textContent=res.K+'回';$('tNs').textContent=[res.combo?`合図だけなら${res.combo.K0}回`:'',res.pooled?`${res.parts.filter(p=>p.K).length}銘柄の合計`:res.years&&!res.combo?`年${(res.K/res.years).toFixed(1)}回`:''].filter(Boolean).join('／');
  const xl=$('exitLine');xl.hidden=!(res.exitStats&&res.K);
  if(res.exitStats&&res.K){const s=res.exitStats,c=s.cnt,f=x=>(x/res.K*100).toFixed(0)+'%';xl.textContent=`決済理由：${opt.exit.tp!=='none'?`利確${f(c[1])}・`:''}${opt.exit.stop!=='none'?`損切り${f(c[2])}・`:''}${opt.exit.trail?`トレーリング${f(c[3])}・`:''}期限${f(c[0])}｜平均${s.hold.toFixed(1)}日保有${isNaN(s.avgR)?'':`｜1回平均 ${s.avgR>=0?'+':'−'}${Math.abs(s.avgR).toFixed(2)}（損切り幅＝1）`}`;}
  const cc=$('comboCard');cc.hidden=!res.combo;
  if(res.combo){const c=res.combo,cb=$('comboBody');cb.textContent='';
    $('comboSub').textContent=`条件で合図が${c.K0}回→${res.K}回に。3行目は条件の日だけの偽薬と比較（差がなければ、良さは条件によるもの）。`;
    [['合図だけ',c.K0,c.mean0,'全日',res.baseMean,c.K0?c.p0:NaN],['組み合わせ',res.K,res.sigMean,'全日',res.baseMean,res.K?res.pBetter:NaN],['組み合わせ（条件の日と比較）',res.K,res.sigMean,'条件の日',c.baseC,res.K&&c.nC?c.pC:NaN]].forEach(([a,k,m,w,b,p])=>{
      const tr=el('tr'),d=m-b;[a,k+'回',pct(m),w,pct(b),pct(d),isNaN(p)?'—':fmtP(p)].forEach((x,j)=>{const td=el('td',{class:'num'},x);if(j===5&&!isNaN(d))td.className='num '+(d>0?'pos':'neg');tr.appendChild(td);});cb.appendChild(tr);});}
  $('tS').textContent=pct(res.sigMean);$('tP').textContent=pct(res.baseMean);
  $('tW').textContent=res.K?`${(res.sigWin*100).toFixed(0)}% / ${(res.baseWin*100).toFixed(0)}%`:'—';
  $('histSub').textContent=res.K?`${res.pooled?'日付の並びを保ったまま時期をずらした偽薬（同じ日に合図が集中する分を数えすぎないため）。':`でたらめな日に同じ${res.K}回入る偽薬。`}合図以上は${res.ge}回（${(res.ge/res.T*100).toFixed(1)}%）。少ないほど偶然ではありません。${P.dir<0?'売りの合図は、下がれば利益で計算。':''}`:'合図が出ていません。';
  const hb=$('halvesBody');hb.textContent='';
  if(res.halves){for(const [i,h] of res.halves.entries()){const tr=el('tr');
    [`${i?'後半':'前半'}（${String(h.from).slice(0,4)}〜${String(h.to).slice(0,4)}年）`,h.K+'回',pct(h.sig),pct(h.base),pct(h.diff),h.K?fmtP(h.p):'—'].forEach((t,j)=>{const td=el('td',{class:'num'},t);if(j===4&&h.K)td.className='num '+(h.diff>0?'pos':'neg');tr.appendChild(td);});hb.appendChild(tr);}}
  else{const tr=el('tr');tr.appendChild(el('td',{colspan:6},'合図が出ていません'));hb.appendChild(tr);}
  $('priceTitle').textContent=res.pooled?`銘柄ごとの内訳`:`合図が出た場所`;
  $('priceWrap').hidden=!!res.pooled;$('breakWrap').hidden=!res.pooled;
  $('priceNote').textContent=P.dir<0?'売りの合図は下がれば勝ち':'';
  const tb=$('tradeBody'),th=$('tradeHead');tb.textContent='';th.textContent='';
  (res.pooled?['銘柄','合図の日','エントリー','決済日','決済値','理由','損益']:['合図の日','エントリー','決済日','決済値','理由','損益']).forEach(x=>th.appendChild(el('th',null,x)));
  const all=[];for(const p of res.parts)for(const t of p.trades)all.push([p,t]);all.sort((x,y)=>y[0].D.d[y[1]]-x[0].D.d[x[1]]);
  for(const [p,t] of all.slice(0,400)){const D=p.D,tr=el('tr'),r=p.R[t];
    const cells=[fmtDate(D.d[t]),fmtPrice(D.o[t+1]),fmtDate(D.d[p.X[t]]),fmtPrice(p.XP[t]),WHYL[p.WHY[t]],pct(r)];if(res.pooled)cells.unshift(D.name);
    cells.forEach((x,j)=>tr.appendChild(el('td',{class:'num'+(j===cells.length-1?(r>0?' pos':' neg'):'')},x)));tb.appendChild(tr);}
  if(all.length>400){const tr=el('tr');tr.appendChild(el('td',{colspan:7},`新しい順に400回まで（全${all.length}回）`));tb.appendChild(tr);}
  const alpha=0.05/tests;
  $('counterText').textContent=`試した組み合わせ：${tests}通り → 合格ライン ${fmtP(alpha)}（5% ÷ ${tests}）。試すほど偶然の当たりが増えるため、だんだん厳しくなります。`;
  drawHist(res);if(res.pooled)drawBreak(res);else drawPrice(res);
}

// ---------- グラフ ----------
const NS='http://www.w3.org/2000/svg';
function sv(tag,a){const e=document.createElementNS(NS,tag);for(const k in a)e.setAttribute(k,a[k]);return e;}
function niceStep(range,count){const raw=range/count,p=Math.pow(10,Math.floor(Math.log10(raw))),f=raw/p;return(f<1.5?1:f<3?2:f<7?5:10)*p;}
function tip(box,html,x,y){let t=box.querySelector('.tip');if(!t){t=el('div',{class:'tip'});box.appendChild(t);}t.textContent='';html.forEach(([cls,txt])=>{const s=el(cls==='b'?'b':'div',cls==='m'?{class:'m'}:null,txt);t.appendChild(s);});t.hidden=false;const W=box.clientWidth,tw=t.offsetWidth;t.style.left=Math.max(0,Math.min(W-tw,x+12))+'px';t.style.top=Math.max(0,y-10)+'px';}
function hideTip(box){const t=box.querySelector('.tip');if(t)t.hidden=true;}

function drawHist(res){
  const box=$('hist');box.textContent='';if(!res.K){box.appendChild(el('p',{class:'sub'},'—'));return;}
  const W=Math.max(300,box.clientWidth),Hh=210,m={l:12,r:12,t:28,b:30};
  const pm=res.pm;let lo=Infinity,hi=-Infinity;for(const x of pm){if(x<lo)lo=x;if(x>hi)hi=x;}lo=Math.min(lo,res.sigMean);hi=Math.max(hi,res.sigMean);const pad=(hi-lo)*0.06||0.001;lo-=pad;hi+=pad;
  const B=Math.max(20,Math.min(48,Math.floor((W-m.l-m.r)/9))),bw=(hi-lo)/B,cnt=new Array(B).fill(0);for(const x of pm){cnt[Math.min(B-1,Math.floor((x-lo)/bw))]++;}
  const maxC=Math.max(...cnt),X=x=>m.l+(x-lo)/(hi-lo)*(W-m.l-m.r),Y=c=>Hh-m.b-c/maxC*(Hh-m.t-m.b);
  const svg=sv('svg',{viewBox:`0 0 ${W} ${Hh}`,width:'100%',role:'img','aria-label':`偽薬2,000回の平均の分布と、合図の平均${pct(res.sigMean)}の位置`});
  const step=niceStep((hi-lo)*100,Math.max(3,Math.floor(W/110)))/100;
  for(let v=Math.ceil(lo/step)*step;v<=hi;v+=step){const x=X(v);svg.appendChild(sv('line',{x1:x,x2:x,y1:m.t,y2:Hh-m.b,stroke:'var(--grid)','stroke-width':1}));const tx=sv('text',{x,y:Hh-m.b+18,'text-anchor':'middle','font-size':11,fill:'var(--muted)'});tx.textContent=(Math.abs(v)<1e-9?'0':pct(v,Math.abs(step*100)<0.1?2:Math.abs(step*100)<1?1:0));svg.appendChild(tx);}
  for(let i=0;i<B;i++){if(!cnt[i])continue;const x0=X(lo+i*bw),x1=X(lo+(i+1)*bw),hiBar=lo+(i+0.5)*bw>=res.sigMean;const h=Hh-m.b-Y(cnt[i]);const w=Math.max(1,x1-x0-2),r=Math.min(3,w/2,h);
    const d=`M${x0+1},${Hh-m.b} V${Y(cnt[i])+r} Q${x0+1},${Y(cnt[i])} ${x0+1+r},${Y(cnt[i])} H${x0+1+w-r} Q${x0+1+w},${Y(cnt[i])} ${x0+1+w},${Y(cnt[i])+r} V${Hh-m.b} Z`;
    const p=sv('path',{d,fill:hiBar?'var(--plot-bar-hi)':'var(--plot-bar)'});svg.appendChild(p);
    const hit=sv('rect',{x:x0,y:m.t,width:x1-x0,height:Hh-m.t-m.b,fill:'transparent',tabindex:-1});
    const a=lo+i*bw,b=a+bw;hit.addEventListener('pointermove',ev=>{const r0=box.getBoundingClientRect();p.setAttribute('opacity','.75');tip(box,[['b',cnt[i]+'回'],['m',`偽薬の平均 ${pct(a)}〜${pct(b)}`]],ev.clientX-r0.left,ev.clientY-r0.top);});
    hit.addEventListener('pointerleave',()=>{p.removeAttribute('opacity');hideTip(box);});svg.appendChild(hit);}
  svg.appendChild(sv('line',{x1:m.l,x2:W-m.r,y1:Hh-m.b,y2:Hh-m.b,stroke:'var(--axis)','stroke-width':1}));
  const sx=X(res.sigMean);svg.appendChild(sv('line',{x1:sx,x2:sx,y1:m.t-6,y2:Hh-m.b,stroke:'var(--accent)','stroke-width':2.5}));
  const lt=sv('text',{x:sx,y:m.t-12,'text-anchor':sx>W*0.8?'end':sx<W*0.2?'start':'middle','font-size':12.5,'font-weight':700,fill:'var(--ink)'});lt.textContent=`合図 ${pct(res.sigMean)}`;svg.appendChild(lt);
  box.appendChild(svg);
}

function drawPrice(res){
  const box=$('price');box.textContent='';const D=S.last.ds;
  const a=res.i0,b=res.i1;if(b-a<2)return;
  const W=Math.max(300,box.clientWidth),Hh=W<520?230:280,m={l:54,r:12,t:12,b:28};
  let lo=Infinity,hi=-Infinity;for(let i=a;i<=b;i++){if(D.c[i]<lo)lo=D.c[i];if(D.c[i]>hi)hi=D.c[i];}
  const logS=hi/lo>4,f=logS?Math.log:(x=>x),L=f(lo)-(f(hi)-f(lo))*0.04,U=f(hi)+(f(hi)-f(lo))*0.04;
  const X=i=>m.l+(i-a)/(b-a)*(W-m.l-m.r),Y=v=>m.t+(U-f(v))/(U-L)*(Hh-m.t-m.b);
  const svg=sv('svg',{viewBox:`0 0 ${W} ${Hh}`,width:'100%',role:'img','aria-label':`${D.name}の終値と、合図で入った${res.K}回の位置`});
  // 縦の目盛り
  let ticks=[];if(logS){for(let e=Math.floor(Math.log10(lo))-1;e<=Math.ceil(Math.log10(hi));e++)for(const k of [1,2,5]){const v=k*Math.pow(10,e);if(v>=Math.exp(L)&&v<=Math.exp(U))ticks.push(v);}if(ticks.length>7)ticks=ticks.filter(v=>/^1/.test(String(v/Math.pow(10,Math.floor(Math.log10(v)))))||ticks.length<10&&/^5/.test(String(v/Math.pow(10,Math.floor(Math.log10(v))))));}
  else{const st=niceStep(hi-lo,5);for(let v=Math.ceil(lo/st)*st;v<=hi;v+=st)ticks.push(v);}
  for(const v of ticks){const y=Y(v);svg.appendChild(sv('line',{x1:m.l,x2:W-m.r,y1:y,y2:y,stroke:'var(--grid)','stroke-width':1}));const tx=sv('text',{x:m.l-6,y:y+4,'text-anchor':'end','font-size':11,fill:'var(--muted)'});tx.textContent=v>=10000?(v/10000)+'万':v.toLocaleString('ja-JP');svg.appendChild(tx);}
  // 横の目盛り（年）
  const yrs=[];for(let i=a+1;i<=b;i++)if(Math.floor(D.d[i]/10000)!==Math.floor(D.d[i-1]/10000))yrs.push(i);
  const every=Math.max(1,Math.ceil(yrs.length/Math.max(2,Math.floor(W/70))));
  yrs.forEach((i,k)=>{if(k%every)return;const x=X(i);svg.appendChild(sv('line',{x1:x,x2:x,y1:Hh-m.b,y2:Hh-m.b+4,stroke:'var(--axis)'}));const tx=sv('text',{x,y:Hh-m.b+17,'text-anchor':'middle','font-size':11,fill:'var(--muted)'});tx.textContent=Math.floor(D.d[i]/10000);svg.appendChild(tx);});
  svg.appendChild(sv('line',{x1:m.l,x2:W-m.r,y1:Hh-m.b,y2:Hh-m.b,stroke:'var(--axis)','stroke-width':1}));
  // 終値の線（画面の幅に合わせて間引く）
  const stepI=Math.max(1,Math.floor((b-a)/(W*1.5)));let d='';for(let i=a;i<=b;i+=stepI)d+=(d?'L':'M')+X(i).toFixed(1)+','+Y(D.c[i]).toFixed(1);d+='L'+X(b).toFixed(1)+','+Y(D.c[b]).toFixed(1);
  svg.appendChild(sv('path',{d,fill:'none',stroke:'var(--plot-line)','stroke-width':1.5,'stroke-linejoin':'round','stroke-linecap':'round'}));
  // 合図で入った場所
  for(const t of res.trades){const i=t+1;if(i>b)continue;const win=res.R[t]>0,x=X(i),y=Y(D.o[i]);
    svg.appendChild(win?sv('circle',{cx:x,cy:y,r:4.5,fill:'var(--mark-good)',stroke:'var(--plot-surface)','stroke-width':1.5}):sv('circle',{cx:x,cy:y,r:3.8,fill:'var(--plot-surface)',stroke:'var(--mark-bad)','stroke-width':2}));}
  const cross=sv('line',{x1:0,x2:0,y1:m.t,y2:Hh-m.b,stroke:'var(--axis)','stroke-width':1,visibility:'hidden'});svg.appendChild(cross);
  const hit=sv('rect',{x:m.l,y:m.t,width:W-m.l-m.r,height:Hh-m.t-m.b,fill:'transparent'});svg.appendChild(hit);
  const tset=new Map();for(const t of res.trades)tset.set(t+1,t);
  hit.addEventListener('pointermove',ev=>{const r0=box.getBoundingClientRect(),sc=W/r0.width,px=(ev.clientX-r0.left)*sc;let i=Math.round(a+(px-m.l)/(W-m.l-m.r)*(b-a));i=Math.max(a,Math.min(b,i));
    const near=Math.max(1,Math.round((b-a)/(W-m.l-m.r)*5));let tr=null;for(let k=0;k<=near&&tr===null;k++){if(tset.has(i+k))tr=tset.get(i+k);else if(tset.has(i-k))tr=tset.get(i-k);}
    const xi=tr!==null?tr+1:i;cross.setAttribute('x1',X(xi));cross.setAttribute('x2',X(xi));cross.setAttribute('visibility','visible');
    const lines=[['b',fmtPrice(D.c[xi])],['m',fmtDate(D.d[xi])+' の終値']];
    if(tr!==null){const r=res.R[tr];lines.push(['',`合図 ${fmtDate(D.d[tr])}｜${fmtPrice(D.o[tr+1])}で入り ${fmtDate(D.d[res.X[tr]])} ${fmtPrice(res.XP[tr])}で決済（${WHYL[res.WHY[tr]]}）`]);lines.push(['b',`${pct(r)}（${r>0?'勝ち':'負け'}）`]);}
    tip(box,lines,(ev.clientX-r0.left),(ev.clientY-r0.top));});
  hit.addEventListener('pointerleave',()=>{cross.setAttribute('visibility','hidden');hideTip(box);});
  box.appendChild(svg);
}

function drawBreak(res){
  const rows=res.parts.filter(p=>p.elig.length).map(p=>({name:p.D.name,K:p.K,sig:p.sigMean,base:p.baseMean,diff:p.sigMean-p.baseMean}));
  rows.sort((a,b)=>((b.K>=5)-(a.K>=5))||((b.K>=5&&a.K>=5)?b.diff-a.diff:b.K-a.K));
  const mx=Math.max(1e-9,...rows.filter(r=>r.K>=5).map(r=>Math.abs(r.diff)));
  const tb=$('breakBody');tb.textContent='';
  for(const r of rows){const tr=el('tr',r.K<5?{class:'dim'}:null);
    [r.name,r.K+'回',pct(r.sig),pct(r.base),pct(r.diff)].forEach((x,j)=>tr.appendChild(el('td',{class:'num'+(j===4&&r.K>=5?(r.diff>0?' pos':' neg'):'')},x)));
    const td=el('td');
    if(r.K>=5){const W=120,c=W/2,w=Math.abs(r.diff)/mx*(c-2),s=sv('svg',{width:W,height:14,viewBox:`0 0 ${W} 14`,'aria-hidden':'true'});s.appendChild(sv('line',{x1:c,x2:c,y1:0,y2:14,stroke:'var(--axis)','stroke-width':1}));s.appendChild(sv('rect',{x:r.diff>0?c:c-w,y:3,width:Math.max(1,w),height:8,rx:2,fill:r.diff>0?'var(--good)':'var(--bad)'}));td.appendChild(s);}
    else td.textContent='回数不足';
    tr.appendChild(td);tb.appendChild(tr);}
  const cs=res.consist||{m:0,g:0};
  $('breakSub').textContent=`合図5回以上の${cs.m}銘柄中、偽薬より上は${cs.g}銘柄。${res.excluded&&res.excluded.length?`出来高のない${res.excluded.join('・')}は除外。`:''}`;
}

// ---------- CSV ----------
function splitCSV(line,sep){const out=[];let cur='',q=false;for(let i=0;i<line.length;i++){const ch=line[i];if(q){if(ch==='"'){if(line[i+1]==='"'){cur+='"';i++;}else q=false;}else cur+=ch;}else if(ch==='"')q=true;else if(ch===sep){out.push(cur);cur='';}else cur+=ch;}out.push(cur);return out.map(s=>s.trim());}
function parseDate(s){const m=String(s).match(/(\d{4})\D?(\d{1,2})\D?(\d{1,2})/);if(!m)return NaN;return(+m[1])*10000+(+m[2])*100+(+m[3]);}
function parseCSV(text){
  const lines=text.replace(/^﻿/,'').split(/\r?\n/).filter(l=>l.trim());if(lines.length<30)throw new Error('行が少なすぎます（300行以上を目安にしてください）');
  const sep=(lines[0].match(/\t/g)||[]).length>(lines[0].match(/,/g)||[]).length?'\t':',';
  const head=splitCSV(lines[0],sep),find=re=>head.findIndex(h=>re.test(h));
  let ci={d:find(/日付|年月日|date/i),o:find(/始値|open/i),h:find(/高値|high/i),l:find(/安値|low/i),c:find(/^(?!.*調整).*(終値|close)/i),v:find(/出来高|volume/i)};
  let start=1;if(ci.d<0||ci.o<0||ci.h<0||ci.l<0||ci.c<0){if(isNaN(parseDate(head[0])))throw new Error('日付・始値・高値・安値・終値の列が見つかりません');ci={d:0,o:1,h:2,l:3,c:4,v:head.length>5?5:-1};start=0;}
  const num=s=>parseFloat(String(s).replace(/[,円\s]/g,''));const rows=new Map();
  for(let i=start;i<lines.length;i++){const f=splitCSV(lines[i],sep);const d=parseDate(f[ci.d]),o=num(f[ci.o]),h=num(f[ci.h]),l=num(f[ci.l]),c=num(f[ci.c]),v=ci.v>=0?num(f[ci.v]):0;if(isNaN(d)||!(o>0&&h>0&&l>0&&c>0))continue;rows.set(d,[o,Math.max(h,o,c),Math.min(l,o,c),c,isNaN(v)?0:v]);}
  const ds=[...rows.keys()].sort((a,b)=>a-b);if(ds.length<300)throw new Error(`使える行が${ds.length}行しかありません。300行（約1年）以上が必要です`);
  const raw={d:ds,o:[],h:[],l:[],c:[],v:[]};for(const d of ds){const r=rows.get(d);raw.o.push(r[0]);raw.h.push(r[1]);raw.l.push(r[2]);raw.c.push(r[3]);raw.v.push(r[4]);}return raw;
}
async function readFileText(file){const buf=await file.arrayBuffer();try{return new TextDecoder('utf-8',{fatal:true}).decode(buf);}catch(e){return new TextDecoder('shift_jis').decode(buf);}}

// ---------- つなぎこみ ----------
ROOT.querySelectorAll('.tab').forEach(b=>b.addEventListener('click',()=>{S.g=b.dataset.g;const first=PRESETS.find(p=>p.g===S.g&&!(p.vol&&!S.ds.hasVol));S.preset=first.id;S.params={};renderPresets();renderParams();run();}));
$('sym').addEventListener('change',async e=>{try{await loadDs(e.target.value);run();}catch(err){showVerdict({cls:'bad',chip:'読み込めません',head:err.message,body:''});}});
['y0','y1','cost','ovl'].forEach(id=>$(id).addEventListener('change',run));
['stopMode','stopVal','tpMode','tpVal','trail','trailVal'].forEach(id=>$(id).addEventListener('change',ev=>{syncExit(ev);run();}));
renderHold();
$('csv').addEventListener('change',async e=>{const f=e.target.files[0];if(!f)return;const errBox=$('csvErr');errBox.hidden=true;
  try{const raw=parseCSV(await readFileText(f));const id='csv-'+Date.now();const name=f.name.replace(/\.[^.]+$/,'');S.index.push({id,name,kind:'読み込んだCSV'});S.cache[id]=prep(raw,{name,kind:'読み込んだCSV'});S.dsId=id;renderSymbols();await loadDs(id);run();}
  catch(err){errBox.textContent=err.message;errBox.hidden=false;}e.target.value='';});
$('addCond').addEventListener('click',()=>{if(S.conds.length>=2)return;S.conds.push({id:'maup',mode:'state',w:5,params:defParams(byId('maup'),true)});renderConds();run();});
$('resetBtn').addEventListener('click',()=>{S.tests.clear();try{sessionStorage.removeItem('kenshou-tests');}catch(e){}run();});
function copyText(txt,okId){const done=()=>{$(okId).hidden=false;setTimeout(()=>$(okId).hidden=true,2000);};
  const fb=()=>{const ta=$('copyFallback');if(okId==='addrOk'){const r=document.createRange();r.selectNodeContents($('addr'));const s=getSelection();s.removeAllRanges();s.addRange(r);return;}ta.value=txt;ta.hidden=false;ta.select();};
  try{navigator.clipboard.writeText(txt).then(done,fb);}catch(e){fb();}}
$('copyBtn').addEventListener('click',()=>{if(!S.last)return;const {res,P,opt,y0,y1,ds}=S.last,v=judge(res,Math.max(1,S.tests.size));
  const txt=[`【それ、本当？検証室の結果】`,`定説：${P.t}（${paramText(P)}）`,...(S.conds.length?[`条件：${S.conds.map(condText).join('／')}`]:[]),...(res.combo?[`合図だけなら：${res.combo.K0}回・平均${pct(res.combo.mean0)}／条件の日の偽薬：平均${pct(res.combo.baseC)}・偽薬が勝った割合 ${res.K&&res.combo.nC?fmtP(res.combo.pC):'—'}`]:[]),`銘柄・期間：${ds.name}／${y0}〜${y1}年`,`確かめ方：翌日の始値で入り、${exitText(opt)}（コスト${opt.cost}%）`,`合図の回数：${res.K}回`,`合図の平均：${pct(res.sigMean)}／偽薬の平均：${pct(res.baseMean)}`,`勝率：合図 ${res.K?(res.sigWin*100).toFixed(0):'—'}%／偽薬 ${(res.baseWin*100).toFixed(0)}%`,`偽薬が勝った割合：${res.K?fmtP(res.pBetter):'—'}（試した組み合わせ ${Math.max(1,S.tests.size)}通り）`,`判定：${v.chip}`,...(res.exitStats&&res.K?[$('exitLine').textContent]:[]),...(res.consist&&res.K?[`銘柄ごと：${res.consist.m}銘柄中${res.consist.g}銘柄で偽薬より上`]:[])].join('\n');
  copyText(txt,'copyOk');});
let rz;new ResizeObserver(()=>{clearTimeout(rz);rz=setTimeout(()=>{if(S.last)draw();},120);}).observe($('results'));

(async()=>{
  try{const r=await fetch('sim-data/index.json');if(!r.ok)throw new Error();S.index=await r.json();const ids=k=>S.index.filter(e=>e.kind===k).map(e=>e.id),jp=ids('株'),fx=ids('為替');const trad=S.index.filter(e=>frameOf(e)==='trad').map(e=>e.id);S.index.unshift({id:'ALL_JP',name:`日本株${jp.length}銘柄まとめて`,kind:'まとめて確かめる',frame:'trad',pool:jp},{id:'ALL_FX',name:`FX ${fx.length}通貨ペアまとめて`,kind:'まとめて確かめる',frame:'trad',pool:fx},{id:'ALL',name:`全${trad.length}銘柄まとめて`,kind:'まとめて確かめる',frame:'trad',pool:trad});renderSymbols();await loadDs('N225');run();}
  catch(e){showVerdict({cls:'bad',chip:'読み込めません',head:'価格データを読み込めませんでした',body:'ページを開き直すか、CSVを読み込んでください。'});S.index=[];renderPresets();renderParams();}
})();
})();
