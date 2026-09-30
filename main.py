# AgriNexus OS — Kaggriculture high-throughput livestock/meta policy
import math

CROPS={"WHEAT":{"seed":10,"base":25,"first":2,"maxday":4,"max":6,"ongoing":False},
"CARROT":{"seed":20,"base":35,"first":2,"maxday":3,"max":4,"ongoing":False},
"TOMATO":{"seed":50,"base":60,"first":8,"maxday":8,"max":4,"ongoing":True},
"STRAWBERRY":{"seed":100,"base":120,"first":10,"maxday":10,"max":4,"ongoing":True},
"MELON":{"seed":80,"base":250,"first":10,"maxday":12,"max":6,"ongoing":False}}
ANIMALS={"COW":{"cost":400,"structure":"PASTURE","build":"BUILD_PASTURE","product":"MILK","first":8,"interval":2,"max":6},
"SHEEP":{"cost":500,"structure":"PASTURE","build":"BUILD_PASTURE","product":"WOOL","first":6,"interval":3,"max":6},
"GOOSE":{"cost":300,"structure":"COOP","build":"BUILD_COOP","product":"EGG","first":4,"interval":1,"max":4}}
BASE={k:v["base"] for k,v in CROPS.items()}; BASE.update({"EGG":50,"MILK":160,"WOOL":200,"FERTILIZER":100})

TARGET={"COW":10,"SHEEP":6,"GOOSE":0}
CROP_TARGET={"WHEAT":18,"STRAWBERRY":6,"CARROT":3}
MAX_HANDS=8
FEED_DAYS=16
WHEAT_BUY_CEILING=55
SELL_FLOOR={"MILK":120,"WOOL":140,"STRAWBERRY":90,"CARROT":25,"TOMATO":45,"WHEAT":18}
SELL_BATCH={"MILK":10,"WOOL":8,"STRAWBERRY":8,"CARROT":20,"TOMATO":12,"WHEAT":30}
P={"FEED":0,"HARVEST":1,"WATER":2,"CARE":3,"FERT":4,"FERTILIZE":5,"PLACE":6,"BUILD":7,"DIG":8,"PLANT":9}

def tile(ts,p): return ts[p[1]][p[0]]
def dist(a,b): return abs(a[0]-b[0])+abs(a[1]-b[1])
def move(pos,t):
    x,y=pos; tx,ty=t
    if x<tx:return ["EAST"]
    if x>tx:return ["WEST"]
    if y<ty:return ["SOUTH"]
    if y>ty:return ["NORTH"]
    return None
def shed_cells(n):
    h=n//2; return [(h-1,h-1),(h,h-1),(h-1,h),(h,h)]
def nearest_shed(pos,n): return min(shed_cells(n),key=lambda q:dist(pos,q))
def unlocked(ts):
    for y,row in enumerate(ts):
        for x,t in enumerate(row):
            if t!="LOCKED": yield (x,y)
def survey(ts):
    s={"empty":[],"weeds":[],"free_coop":[],"free_pasture":[],"crop":{},
       "animals":{"COW":0,"SHEEP":0,"GOOSE":0}}
    for p in unlocked(ts):
        t=tile(ts,p)
        if t is None:s["empty"].append(p)
        elif isinstance(t,dict):
            k=t.get("kind")
            if k=="WEED":s["weeds"].append(p)
            elif k=="PLANT":
                c=t.get("crop");s["crop"][c]=s["crop"].get(c,0)+1
            elif k in ("COOP","PASTURE"):
                a=t.get("animal")
                if a:s["animals"][a]+=1
                elif k=="COOP":s["free_coop"].append(p)
                else:s["free_pasture"].append(p)
    return s
def stock(priv):
    out={a:priv.get("shed",{}).get(a,0) for a in ANIMALS}
    for inv in priv.get("inventories",[]) or []:
        for a in out:out[a]+=inv.get(a,0)
    return out
def totals(s,priv):
    st=stock(priv);return {a:s["animals"][a]+st[a] for a in ANIMALS}
def herd(s,priv):
    q=totals(s,priv);return q["COW"]+q["SHEEP"]+q["GOOSE"]
def work_size(me):
    n=0
    for p in unlocked(me["tiles"]):
        t=tile(me["tiles"],p)
        if isinstance(t,dict):
            if t.get("kind")=="PLANT":n+=1
            elif t.get("kind") in ("PASTURE","COOP") and t.get("animal"):n+=2
            elif t.get("kind")=="WEED":n+=1
    return n
def ready(t,day):
    c=t.get("crop") if isinstance(t,dict) else None
    return isinstance(t,dict) and t.get("kind")=="PLANT" and t.get("yield_units",0)>0 and day-t.get("planted_day",day)>=CROPS.get(c,{}).get("first",99)

def choose_crop(day,s,seeds):
    order=("WHEAT","CARROT","STRAWBERRY") if day<10 else ("WHEAT","STRAWBERRY","CARROT")
    cand=[]
    for c in order:
        have=s["crop"].get(c,0)+seeds.get(c,0); need=CROP_TARGET.get(c,0)-have
        if need<=0 or day+CROPS[c]["first"]>29:continue
        score=need/max(1,CROP_TARGET[c])+CROPS[c]["base"]/100
        if c=="WHEAT":score+=0.8
        if c=="STRAWBERRY" and day>=10:score+=0.8
        cand.append((score,c))
    return max(cand)[1] if cand else None

def tasks(obs,me,priv,s):
    day=obs["day"];ts=me["tiles"];shed=priv.get("shed",{});r=[]
    for p in unlocked(ts):
        t=tile(ts,p)
        if not isinstance(t,dict):continue
        k=t.get("kind")
        if k=="WEED":r.append((P["DIG"],p,["DIG"],"DIG"));continue
        if k=="PLANT":
            c=t.get("crop")
            if ready(t,day):r.append((P["HARVEST"],p,["HARVEST"],"HARVEST"))
            if not t.get("watered_today",False):r.append((P["WATER"],p,["WATER"],"WATER"))
            if shed.get("FERTILIZER",0)>0:
                age=day-t.get("planted_day",day)
                if c in ("WHEAT","CARROT","MELON"):
                    w=(CROPS[c]["maxday"]+1)//2
                    if w<=age<=w+1 and t.get("fertilized_until_day",-1)<day:
                        r.append((P["FERTILIZE"],p,["FERTILIZE"],"FERTILIZE"))
                elif c=="STRAWBERRY" and 10<=age<=14 and t.get("fertilized_until_day",-1)<day:
                    r.append((P["FERTILIZE"],p,["FERTILIZE"],"FERTILIZE"))
        elif k in ("PASTURE","COOP") and t.get("animal"):
            if not t.get("fed_today",False):r.append((P["FEED"],p,["FEED"],"FEED"))
            elif not t.get("cared_today",False):r.append((P["CARE"],p,["CARE"],"CARE"))
            if t.get("yield_units",0)>=max(2,ANIMALS[t["animal"]]["max"]-1):
                r.append((P["HARVEST"],p,["HARVEST"],"HARVEST"))
            if t.get("fertilizer_available",False):r.append((P["FERT"],p,["COLLECT_FERTILIZER"],"FERT"))
    q=totals(s,priv); current=q["COW"]+q["SHEEP"]
    need=max(0,TARGET["COW"]+TARGET["SHEEP"]-current-len(s["free_pasture"]))
    for _ in range(need):
        if not s["empty"]:break
        p=min(s["empty"],key=lambda z:min(dist(z,h) for h in shed_cells(len(ts))))
        r.append((P["BUILD"],p,["BUILD_PASTURE"],"BUILD"));s["empty"].remove(p);s["free_pasture"].append(p)
    st=stock(priv)
    for a in ("COW","SHEEP"):
        free=s["free_pasture"]
        while st[a]>0 and free:
            p=free.pop(0);r.append((P["PLACE"],p,["PLACE",a],"PLACE"));st[a]-=1
    return r

def assign(units,jobs):
    out=[None]*len(units);left=list(range(len(jobs)))
    for i,pos in enumerate(units):
        hit=[j for j in left if jobs[j][1]==pos]
        if hit:
            j=min(hit,key=lambda z:(jobs[z][0],z));out[i]=jobs[j];left.remove(j)
    for i,pos in enumerate(units):
        if out[i] is not None or not left:continue
        j=min(left,key=lambda z:(jobs[z][0],dist(pos,jobs[z][1]),z));out[i]=jobs[j];left.remove(j)
    return out

def dispatch(pos,job,inv,priv,n):
    if job is None:return ["PASS"]
    _,target,action,kind=job
    if kind=="FEED" and inv.get("WHEAT",0)<=0:
        sh=nearest_shed(pos,n)
        if pos!=sh:return move(pos,sh)
        q=min(4,priv.get("shed",{}).get("WHEAT",0))
        return ["PICKUP","WHEAT",q] if q else ["PASS"]
    if kind=="PLACE" and inv.get(action[1],0)<=0:
        sh=nearest_shed(pos,n)
        if pos!=sh:return move(pos,sh)
        return ["PICKUP",action[1],1] if priv.get("shed",{}).get(action[1],0)>0 else ["PASS"]
    if kind=="FERTILIZE" and inv.get("FERTILIZER",0)<=0:
        sh=nearest_shed(pos,n)
        if pos!=sh:return move(pos,sh)
        return ["PICKUP","FERTILIZER",1] if priv.get("shed",{}).get("FERTILIZER",0)>0 else ["PASS"]
    return move(pos,target) or action

def market(obs,me,priv,s):
    day=obs["day"];money=float(me.get("money",0));prices=obs.get("market",{}).get("prices",{})
    shed=priv.get("shed",{});seeds=priv.get("seeds",{});orders=[]
    for item in ("MILK","WOOL","STRAWBERRY","CARROT","TOMATO","EGG","FERTILIZER"):
        qty=shed.get(item,0)
        if qty<=0 or len(orders)>=10:continue
        floor=SELL_FLOOR.get(item,1);price=prices.get(item,BASE.get(item,1))
        if day>=28 or price>=floor:
            n=min(qty,SELL_BATCH.get(item,8))
            if n:orders.append(["SELL",item,n])
    h=herd(s,priv); wheat=shed.get("WHEAT",0); reserve=h*FEED_DAYS
    excess=max(0,wheat-reserve)
    if excess and len(orders)<10 and prices.get("WHEAT",25)>=18:
        orders.append(["SELL","WHEAT",min(excess,SELL_BATCH["WHEAT"])])
    inv_w=sum(x.get("WHEAT",0) for x in priv.get("inventories",[]) or [])
    wp=prices.get("WHEAT",25);current=wheat+inv_w;desired=max(reserve,h*8)
    if h and wp<=WHEAT_BUY_CEILING and current<desired and len(orders)<10:
        need=desired-current;aff=int(max(0,money-1000)//max(1,wp));n=min(need,aff,50)
        if n>0:orders.append(["BUY_PRODUCT","WHEAT",n]);money-=n*wp
    for c in ("WHEAT","STRAWBERRY","CARROT"):
        if len(orders)>=10:break
        have=s["crop"].get(c,0)+seeds.get(c,0);need=CROP_TARGET.get(c,0)-have
        if need<=0 or day+CROPS[c]["first"]>29:continue
        reserve_cash=1200+h*FEED_DAYS*max(10,wp)//2
        aff=int(max(0,money-reserve_cash)//CROPS[c]["seed"]);n=min(need,aff,8)
        if n>0:orders.append(["BUY_SEED",c,n]);money-=n*CROPS[c]["seed"]
    q=totals(s,priv);h=q["COW"]+q["SHEEP"]+q["GOOSE"]
    actual_feed=wheat+sum(x.get("WHEAT",0) for x in priv.get("inventories",[]) or [])
    for a in ("SHEEP","COW"):
        if len(orders)>=10 or q[a]>=TARGET[a]:continue
        if day < (4 if a=="SHEEP" else 6):continue
        cost=ANIMALS[a]["cost"];newh=h+1;runway=newh*FEED_DAYS*wp
        product=ANIMALS[a]["product"];prodprice=prices.get(product,BASE[product])
        opening_feed=max(actual_feed,newh*4);feed_purchase=max(0,opening_feed-actual_feed);feed_cash=feed_purchase*wp
        if money>=cost+runway+feed_cash+500 and prodprice>=0.8*wp*ANIMALS[a]["interval"]:
            orders.append(["BUY_ANIMAL",a,1]);money-=cost;q[a]+=1;h=newh
            if feed_purchase and len(orders)<10:
                orders.append(["BUY_PRODUCT","WHEAT",min(feed_purchase,50)]);money-=feed_cash;actual_feed+=feed_purchase
    current=len(me.get("hands",[]));desired=min(MAX_HANDS,max(4,math.ceil(max(1,work_size(me))/6)))
    fib=(1,1,2,3,5,8,13,21)
    while current<desired and len(orders)<10:
        cost=fib[min(current,7)]
        if money<cost:break
        orders.append(["HIRE"]);money-=cost;current+=1
    nq=len(me.get("unlocked_quadrants",[]))
    if nq<3 and len(orders)<10:
        land=1000 if nq==1 else 2000
        if money>=land+max(0,h*FEED_DAYS*wp//3):orders.append(["BUY_LAND"])
    return orders[:10]

def _impl(obs):
    p=obs["player"];me=obs["farms"][p];priv=obs.get("private",{}) or {};s=survey(me["tiles"])
    jobs=tasks(obs,me,priv,s)
    crop=choose_crop(obs["day"],s,priv.get("seeds",{}))
    if crop and priv.get("seeds",{}).get(crop,0)>0 and s["empty"]:
        n=min(priv["seeds"][crop],len(s["empty"]),len(me.get("hands",[]))+1)
        for pos in sorted(s["empty"],key=lambda z:min(dist(z,h) for h in shed_cells(len(me["tiles"]))))[:n]:
            jobs.append((P["PLANT"],pos,["PLANT",crop],"PLANT"))
    jobs.sort(key=lambda x:(x[0],x[1][1],x[1][0]))
    units=[tuple(me["farmer"])]+[tuple(x) for x in me.get("hands",[])]
    assigned=assign(units,jobs);invs=priv.get("inventories",[]) or [];actions=[]
    for i,pos in enumerate(units):
        inv=invs[i] if i<len(invs) else {}
        actions.append(dispatch(pos,assigned[i],inv,priv,len(me["tiles"])))
    return {"farmer":actions[0] if actions else ["PASS"],"hands":actions[1:],"market":market(obs,me,priv,s)}

def agent(obs):
    try:return _impl(obs)
    except Exception:
        try:
            p=obs.get("player",0);hs=obs.get("farms",[{}])[p].get("hands",[])
            return {"farmer":["PASS"],"hands":[["PASS"] for _ in hs],"market":[]}
        except Exception:return {"farmer":["PASS"],"hands":[],"market":[]}
