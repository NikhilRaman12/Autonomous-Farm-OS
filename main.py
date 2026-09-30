"""AgriNexus OS - multi-agent autonomous farm for Kaggriculture.

Loop every turn (stateless, closed loop - everything is re-derived from obs):

  OBSERVE -> SPECIALIST PROPOSALS -> ECONOMIC ARBITRATION -> SCHEDULE/EXECUTE
  -> (next observation reconciles the result)

Specialists (each one prices its own domain from the live market curves):
  Livestock  - animal purchase ROI (products + fertilizer - feed - capital)
  Crop       - crop purchase ROI per tile-day, pool/glut aware
  Fertility  - fertilizer is a sale commodity (collect every animal every day)
  Market     - reservation-price selling, feed procurement, terminal liquidation
  Expansion  - land ROI vs. best marginal tile use
  Workforce  - hire count from workload; spatial job scheduler
  Safety     - mandatory water/feed, shed-overflow guard, final-day drop/sell

Pure standard library. No files, network, randomness or persistent state.
"""

import math

TPD = 24
LAST_DAY = 29
END_STEP = 718          # last step whose actions are processed by the engine
I0 = 10000

CROPS = {
    "WHEAT": {"seed": 10, "first": 2, "maxd": 4, "cap": 6, "ongoing": False, "interval": 0},
    "CARROT": {"seed": 20, "first": 2, "maxd": 3, "cap": 4, "ongoing": False, "interval": 0},
    "TOMATO": {"seed": 50, "first": 8, "maxd": 8, "cap": 4, "ongoing": True, "interval": 1},
    "STRAWBERRY": {"seed": 100, "first": 10, "maxd": 10, "cap": 4, "ongoing": True, "interval": 2},
    "MELON": {"seed": 80, "first": 10, "maxd": 12, "cap": 6, "ongoing": False, "interval": 0},
}
# harvest age that captures the full (watered) yield, and that yield
CROP_H = {"WHEAT": (4, 4), "CARROT": (3, 3), "TOMATO": (11, 4),
          "STRAWBERRY": (16, 4), "MELON": (10, 6)}
ANIMALS = {
    "GOOSE": {"cost": 300, "struct": "COOP", "build": "BUILD_COOP", "first": 4,
              "interval": 1, "held": 4, "product": "EGG"},
    "COW": {"cost": 400, "struct": "PASTURE", "build": "BUILD_PASTURE", "first": 8,
            "interval": 2, "held": 6, "product": "MILK"},
    "SHEEP": {"cost": 500, "struct": "PASTURE", "build": "BUILD_PASTURE", "first": 6,
              "interval": 3, "held": 6, "product": "WOOL"},
}
PRODUCTS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK",
            "WOOL", "FERTILIZER"]
INPUTS = ("WHEAT", "GOOSE", "COW", "SHEEP")
LAND_PRICES = (1000, 2000, 4000)

MARKET = {
    "WHEAT": {"base": 25, "T": 400, "below_func": "sqrt", "below_target": 0.80, "above_func": "log", "above_target": 0.20},
    "CARROT": {"base": 35, "T": 450, "below_func": "hinge", "below_target": 1.00, "above_func": "sqrt", "above_target": 0.70},
    "TOMATO": {"base": 60, "T": 200, "below_func": "hinge", "below_target": 0.40, "above_func": "sqrt", "above_target": 0.60},
    "STRAWBERRY": {"base": 120, "T": 100, "below_func": "sqrt", "below_target": 0.70, "above_func": "linear", "above_target": 1.60},
    "MELON": {"base": 250, "T": 300, "below_func": "log", "below_target": 0.20, "above_func": "sq", "above_target": 3.60},
    "EGG": {"base": 50, "T": 332, "below_func": "hinge", "below_target": 0.40, "above_func": "log", "above_target": 0.20},
    "MILK": {"base": 160, "T": 122, "below_func": "sqrt", "below_target": 0.60, "above_func": "linear", "above_target": 1.60},
    "WOOL": {"base": 200, "T": 105, "below_func": "log", "below_target": 0.20, "above_func": "sq", "above_target": 3.20},
    "FERTILIZER": {"base": 100, "T": 200, "below_func": "linear", "below_target": 0.40, "above_func": "linear", "above_target": 0.40},
}

# reservation price as a fraction of base (selling below it = hold)
HOLD = {"MELON": 0.30, "STRAWBERRY": 0.35, "MILK": 0.35, "WOOL": 0.35, "TOMATO": 0.40,
        "CARROT": 0.40, "EGG": 0.45, "FERTILIZER": 0.12, "WHEAT": 0.60}

LOCAL_TESTING = False    # Set to False for competition
_ERR = []               # diagnostics only (tests assert it stays empty)


# --------------------------------------------------------------------------
# market model (mirror of the engine price curve)
# --------------------------------------------------------------------------
def _shape(func, x, T):
    x = max(0.0, x)
    if func == "linear":
        return x
    if func == "sq":
        return x * x
    if func == "sqrt":
        return math.sqrt(x)
    if func == "log":
        return math.log(1.0 + x)
    if func == "log10":
        return math.log10(1.0 + x)
    if func == "hinge":
        u = x / T if T else x
        return u + 8.0 * max(0.0, u - 1.0) ** 2
    return x


def price(P, item, inv):
    p = P.get(item) or MARKET[item]
    base = p["base"]
    T = p["T"]
    i0 = p.get("I0", I0)
    if inv < i0:
        f = p["below_func"]
        amp = p["below_target"] * base / max(1e-9, _shape(f, T, T))
        v = base + amp * _shape(f, i0 - inv, T)
    else:
        f = p["above_func"]
        amp = p["above_target"] * base / max(1e-9, _shape(f, T, T))
        v = base - amp * _shape(f, inv - i0, T)
    return max(1, int(round(v)))


def rev(P, item, inv, n):
    """Revenue of selling n units one by one starting at market inventory inv."""
    total = 0
    x = inv
    for _ in range(int(n)):
        p = price(P, item, x)
        total += p
        if p > 1:
            x += 1
    return total


def fib(n):
    a, b = 1, 1
    for _ in range(n):
        a, b = b, a + b
    return a


def dist(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def step_toward(pos, tgt):
    dx, dy = tgt[0] - pos[0], tgt[1] - pos[1]
    if dx == 0 and dy == 0:
        return None
    if abs(dx) >= abs(dy):
        return "EAST" if dx > 0 else "WEST"
    return "SOUTH" if dy > 0 else "NORTH"


# --------------------------------------------------------------------------
# observation -> normalised state
# --------------------------------------------------------------------------
class S:
    pass


def observe(obs):
    s = S()
    s.day = int(obs.get("day", 0))
    s.hour = int(obs.get("hour", 0))
    s.step = int(obs.get("step", s.day * TPD + s.hour))
    s.player = int(obs.get("player", 0))
    me = obs["farms"][s.player]
    s.money = float(me.get("money", 0))
    s.tiles = me["tiles"]
    s.N = len(s.tiles)
    s.units = [tuple(me["farmer"])] + [tuple(h) for h in (me.get("hands") or [])]
    s.quadrants = list(me.get("unlocked_quadrants") or ["NW"])
    s.hires_today = int(me.get("hires_today", 0))
    priv = obs.get("private") or {}
    s.shed = dict(priv.get("shed") or {})
    s.seeds = dict(priv.get("seeds") or {})
    invs = list(priv.get("inventories") or [])
    s.invs = [dict(invs[i]) if i < len(invs) and invs[i] else {} for i in range(len(s.units))]
    mk = obs.get("market") or {}
    s.prices = dict(mk.get("prices") or {})
    s.minv = dict(mk.get("inventory") or {})
    s.P = MARKET
    params = mk.get("params")
    if isinstance(params, dict) and params:
        s.P = {k: dict(MARKET.get(k, {}), **(params.get(k) or {})) for k in MARKET}
    half = s.N // 2
    s.sheds = [(half - 1, half - 1), (half, half - 1), (half - 1, half), (half, half)]
    s.left = END_STEP - s.step            # turns still processed, incl. this one
    s.final = s.day >= LAST_DAY

    s.animals, s.plants, s.weeds, s.empties, s.structs = [], [], [], [], []
    for y, row in enumerate(s.tiles):
        for x, t in enumerate(row):
            p = (x, y)
            if t is None:
                s.empties.append(p)
            elif isinstance(t, dict):
                k = t.get("kind")
                if k == "PLANT":
                    s.plants.append((p, t))
                elif k == "WEED":
                    s.weeds.append(p)
                elif k in ("COOP", "PASTURE"):
                    if t.get("animal"):
                        s.animals.append((p, t))
                    else:
                        s.structs.append((p, k))
    s.pipe = {a: s.shed.get(a, 0) + sum(i.get(a, 0) for i in s.invs) for a in ANIMALS}
    s.wheat = s.shed.get("WHEAT", 0) + sum(i.get("WHEAT", 0) for i in s.invs)
    s.n_animals = len(s.animals) + sum(s.pipe.values())
    s.shed_total = sum(v for v in s.shed.values() if v > 0)
    return s


def p_now(s, item):
    v = s.prices.get(item)
    return float(v) if v is not None else float(MARKET[item]["base"])


def nearest_shed(s, pos):
    return min(s.sheds, key=lambda q: (dist(pos, q), q))


def sdist(s, p):
    return min(dist(p, q) for q in s.sheds)


# --------------------------------------------------------------------------
# economics
# --------------------------------------------------------------------------
def animal_units(atype, d):
    """Expected (product units, fertilizer units) of an animal placed on day d."""
    info = ANIMALS[atype]
    t0 = d + info["first"] - 1           # end-of-day index of first production
    if t0 > 28:
        prod = 0.0
    else:
        ticks = (28 - t0) // info["interval"] + 1
        prod = ticks * (1 + info["interval"]) * 0.88
    fert = max(0, LAST_DAY - d) * 0.95
    return prod, fert


def expected_other_units(s, extra=None):
    """Units my current herd will still push into each market (last-in pricing)."""
    out = {"EGG": 0.0, "MILK": 0.0, "WOOL": 0.0, "FERTILIZER": 0.0}
    herd = [(t["animal"], t.get("placed_day", s.day)) for _, t in s.animals]
    for a, n in s.pipe.items():
        herd += [(a, s.day)] * n
    for a, n in (extra or {}).items():
        herd += [(a, s.day)] * n
    for a, pd in herd:
        prod, _ = animal_units(a, max(pd, s.day - 0))
        info = ANIMALS[a]
        rem_days = max(0, 28 - s.day)
        if pd + info["first"] - 1 <= s.day:
            ticks = rem_days // info["interval"] + 1
            prod = ticks * (1 + info["interval"]) * 0.88
        out[info["product"]] += prod
        out["FERTILIZER"] += max(0, LAST_DAY - s.day) * 0.95
    return out


def animal_margin(s, atype, extra=None):
    """(net season value, capital) of one more animal of this type, bought now."""
    info = ANIMALS[atype]
    d = s.day + (1 if s.hour >= 14 else 0)
    prod_u, fert_u = animal_units(atype, d)
    oth = expected_other_units(s, extra)
    prod = info["product"]
    x_prod = s.minv.get(prod, I0) + oth[prod]
    x_fert = s.minv.get("FERTILIZER", I0) + oth["FERTILIZER"]
    v = rev(s.P, prod, x_prod, int(prod_u)) + rev(s.P, "FERTILIZER", x_fert, int(fert_u))
    wheat_cost = max(0, 29 - d) * p_now(s, "WHEAT") * 1.25
    
    # Worker action cost (Phase 3 Economics):
    # 1 action to build/place + 1 FEED and 1 CARE per day + 1 HARVEST per product + 1 COLLECT per day
    days_alive = max(0, 29 - d)
    actions = 1 + (2 * days_alive) + prod_u + days_alive
    worker_action_cost = actions * 3.5  # Approx 3.5 money per worker action
    
    return v - info["cost"] - wheat_cost - worker_action_cost, info["cost"]


def crop_margin(s, crop, extra_units=0):
    """(net profit, tile-days, units) of one more plant of this crop, bought now."""
    cd = CROPS[crop]
    h, units = CROP_H[crop]
    if s.day + h > LAST_DAY:
        return -1e9, h, units
    standing = 0
    for _, t in s.plants:
        if t.get("crop") == crop:
            standing += CROP_H[crop][1]
    standing += s.seeds.get(crop, 0) * units + extra_units
    x0 = s.minv.get(crop, I0) + standing
    val = rev(s.P, crop, x0, units)
    if crop == "WHEAT" and s.n_animals > 0:
        feed_value = 0.85 * p_now(s, "WHEAT") * units
        stock_need = s.n_animals * 3
        if s.wheat + standing < stock_need:
            val = max(val, feed_value)
            
    # Worker action cost (Phase 3 Economics):
    # 1 PLANT + (h/2) WATER + 1 HARVEST
    actions = 1 + (h / 2.0) + 1
    worker_action_cost = actions * 3.5
    
    return val - cd["seed"] - worker_action_cost, h, units


# --------------------------------------------------------------------------
# specialists -> market proposals
# --------------------------------------------------------------------------
def market_agent_sells(s):
    """Dynamic Marginal Revenue selling and Terminal Liquidation."""
    orders, proceeds = [], 0.0
    crowded = s.shed_total > 88
    
    # Terminal mode check
    is_terminal = (s.day >= 28)
    
    for item in PRODUCTS:
        stock = s.shed.get(item, 0)
        if stock <= 0:
            continue
            
        keep = 0
        if item == "WHEAT":
            if not is_terminal:
                keep = s.n_animals + 3
            else:
                # On day 28/29, only keep exactly enough for remaining feeds
                unfed = sum(1 for _, t in s.animals if not t.get("fed_today"))
                keep = unfed + (1 if s.day == 28 else 0)
                
        stock -= keep
        if stock <= 0:
            continue
            
        base = s.P[item]["base"]
        
        # Calculate dynamic floor
        if is_terminal:
            floor_p = 1.0 # Liquidate everything for whatever we can get
        else:
            base_frac = HOLD.get(item, 0.3)
            # Adjust based on inventory pressure and time left
            if crowded:
                base_frac *= 0.5
            
            # As the season progresses past day 20, we gradually lower standards
            if s.day > 20:
                base_frac *= max(0.4, (28 - s.day) / 8.0)
                
            floor_p = max(1.0, base * base_frac)
            
        x = s.minv.get(item, I0)
        k, got = 0, 0
        
        # Marginal Revenue evaluation
        while k < stock:
            p = price(s.P, item, x)
            if p < floor_p:
                break # Stop selling, marginal revenue is too poor
            got += p
            k += 1
            if p > 1:
                x += 1
                
        if k > 0:
            orders.append(("SELL", item, k, got))
            proceeds += got
            
    orders.sort(key=lambda o: -o[3])
    return orders, proceeds


def feed_need(s):
    unfed = sum(1 for _, t in s.animals if not t.get("fed_today"))
    waiting = sum(s.pipe.values())
    if s.day >= LAST_DAY:
        return 0
    return unfed + waiting


def slots_free(s):
    committed = sum(s.pipe.values()) + sum(max(0, v) for v in s.seeds.values())
    return len(s.empties) + len(s.structs) - committed


def livestock_proposals(s, slots, cash):
    out = []
    if s.day > 24 or slots <= 0 or cash < 290:
        return out
    extra = {}
    for _ in range(min(slots, 30)):
        best = None
        for a in ANIMALS:
            net, cost = animal_margin(s, a, extra)
            if net < 0.9 * cost:
                continue
            roi = net / cost
            if best is None or roi > best[0]:
                best = (roi, a, net, cost)
        if best is None:
            break
        out.append(best)
        extra[best[1]] = extra.get(best[1], 0) + 1
        cash -= best[3]
        if cash < 290:
            break
    return out


def crop_proposals(s, slots, cash):
    out = []
    if slots <= 0 or s.day > 19:
        return out
    extra = {}
    for _ in range(min(slots, 40)):
        best = None
        for c in ("MELON", "CARROT", "WHEAT"):
            net, h, units = crop_margin(s, c, extra.get(c, 0))
            per_day = net / float(h)
            if per_day < 28 or net < 0.8 * CROPS[c]["seed"]:
                continue
            roi = net / CROPS[c]["seed"]
            if best is None or per_day > best[0]:
                best = (per_day, c, net, roi)
        if best is None:
            break
        cost = CROPS[best[1]]["seed"]
        out.append((best[3], best[1], best[2], cost))
        extra[best[1]] = extra.get(best[1], 0) + CROP_H[best[1]][1]
        cash -= cost
        if cash < 80:
            break
    return out


def land_proposal(s, slots, cash):
    n_extra = len(s.quadrants) - 1
    if n_extra >= 3 or s.day > 17:
        return None
    cost = LAND_PRICES[n_extra]
    if slots > 3 or cash < cost + 500:
        return None
    # value: best marginal tile use over the time left, for the tiles we can fill
    best = 0.0
    for a in ANIMALS:
        net, c = animal_margin(s, a)
        best = max(best, net)
    cm = max((crop_margin(s, c)[0] for c in ("MELON",)), default=0)
    best = max(best, cm)
    fill = min(18, int((cash - cost) // 300))
    if fill < 4:
        return None
    if best * fill > 1.8 * cost:
        return ("BUY_LAND", cost)
    return None


def workforce_target(s, n_new_animals, n_new_plants):
    work = 0.0
    work += 5.5 * len(s.animals)
    work += 7.0 * (sum(s.pipe.values()) + n_new_animals)
    for _, t in s.plants:
        work += 2.2
    work += 3.5 * (sum(max(0, v) for v in s.seeds.values()) + n_new_plants)
    work += 1.5 * len(s.weeds)
    target = int(math.ceil(work * 1.1 / 19.0)) - 1
    if s.day >= LAST_DAY:
        target = max(target, min(6, 1 + len(s.animals) // 6))
    return max(0, min(11, target))


def market_council(s):
    """Specialists propose, arbitrator funds by ROI under the cash budget."""
    sells, est = market_agent_sells(s)
    orders = [["SELL", it, k] for (_, it, k, _) in sells]
    budget = s.money + 0.93 * est
    spent = 0.0

    # Safety/feed: wheat for today's feeding is non-negotiable.
    need = feed_need(s)
    if need > 0 and s.wheat < need and not s.final:
        qty = need - s.wheat + (2 if s.hour <= 1 else 0)
        unit_p = price(s.P, "WHEAT", s.minv.get("WHEAT", I0) - qty // 2)
        qty = int(min(qty, max(0, (budget - spent) // max(1, unit_p))))
        room = 100 - s.shed_total
        qty = min(qty, max(0, room))
        if qty > 0:
            orders.append(["BUY_PRODUCT", "WHEAT", qty])
            spent += qty * unit_p

    slots = slots_free(s)
    reserve = 60 + 6 * s.n_animals
    avail = budget - spent - reserve
    is_terminal = (s.day >= 28)

    props = []
    # STOP speculative investment in terminal mode
    if not is_terminal and not s.final and s.left > 30:
        for roi, a, net, cost in livestock_proposals(s, slots, avail):
            props.append((roi, "animal", a, cost))
        for roi, c, net, cost in crop_proposals(s, slots, avail):
            props.append((roi, "seed", c, cost))
    props.sort(key=lambda p: (-p[0] if p[1] != "animal" else -p[0] - 0.75, p[2]))
    # animals get a small priority edge: they start paying (fertilizer) next day

    bought_a, bought_p = {}, {}
    for roi, kind, item, cost in props:
        if slots <= 0 or avail < cost:
            continue
        if len(orders) >= 9:
            break
        if kind == "animal":
            bought_a[item] = bought_a.get(item, 0) + 1
        else:
            bought_p[item] = bought_p.get(item, 0) + 1
        avail -= cost
        slots -= 1
    shed_room = 100 - s.shed_total
    for a, n in bought_a.items():
        n = min(n, max(0, shed_room))
        shed_room -= n
        if n > 0:
            orders.append(["BUY_ANIMAL", a, n])
    for c, n in bought_p.items():
        orders.append(["BUY_SEED", c, n])

    # Expansion
    if not is_terminal and not s.final and len(orders) < 9 and s.hour <= 3:
        lp = land_proposal(s, slots, avail)
        if lp:
            orders.append(["BUY_LAND"])
            avail -= lp[1]

    # Workforce
    if s.hour <= 2 and not s.final or (s.final and s.hour <= 1):
        target = workforce_target(s, sum(bought_a.values()), sum(bought_p.values()))
        have = s.hires_today
        k = have
        cash_h = max(0.0, avail + reserve * 0.5)
        while k < target and len(orders) < 10:
            cst = fib(k)
            if cst > 70 or cst > cash_h:
                break
            orders.append(["HIRE"])
            cash_h -= cst
            k += 1
    return orders[:10]


# --------------------------------------------------------------------------
# job generation (Crop / Livestock / Fertility agents -> tile actions)
# --------------------------------------------------------------------------
def tile_plan(s):
    """Decide which empty tile gets which asset (animals near, crops far)."""
    wait = {a: n for a, n in s.pipe.items() if n > 0}
    free_structs = sorted(s.structs, key=lambda q: (sdist(s, q[0]), q[0]))
    near = sorted(s.empties, key=lambda p: (sdist(s, p), p[1], p[0]))
    used = set()
    place = []        # (tile, atype, is_empty_tile)
    for atype in sorted(wait, key=lambda a: list(ANIMALS).index(a)):
        kind = ANIMALS[atype]["struct"]
        for _ in range(wait[atype]):
            pick = None
            for q in free_structs:
                if q[1] == kind and q[0] not in used:
                    pick = (q[0], False)
                    break
            if pick is None:
                for p in near:
                    if p not in used:
                        pick = (p, True)
                        break
            if pick is None:
                break
            used.add(pick[0])
            place.append((pick[0], atype, pick[1]))
    far = [p for p in sorted(s.empties, key=lambda p: (-sdist(s, p), p[1], p[0])) if p not in used]
    plant = []
    for crop in ("MELON", "CARROT", "WHEAT", "TOMATO", "STRAWBERRY"):
        n = s.seeds.get(crop, 0)
        if n <= 0:
            continue
        h = CROP_H[crop][0]
        if s.day + h > LAST_DAY:
            continue
        for _ in range(n):
            if not far:
                break
            p = far.pop(0)
            plant.append((p, crop))
    return place, plant


def gen_groups(s):
    G = {}

    def add(tile, val, act, need=None):
        G.setdefault(tile, []).append((val, act, need))

    day = s.day
    # --- Livestock + Fertility
    for p, t in s.animals:
        a = t["animal"]
        info = ANIMALS[a]
        pp = p_now(s, info["product"])
        fed = t.get("fed_today", False)
        if not fed and day < LAST_DAY:
            add(p, 500 if t.get("consecutive_unfed", 0) >= 1 else 150, ("FEED",), "WHEAT")
        if not t.get("cared_today", False) and day <= 27:
            add(p, max(40.0, pp * 0.9), ("CARE",))
        yu = t.get("yield_units", 0)
        if yu > 0 and (yu >= 2 or day >= 27 or yu >= info["held"] - 1):
            add(p, yu * pp + 10, ("HARVEST",))
        if t.get("fertilizer_available", False):
            add(p, p_now(s, "FERTILIZER") + 5, ("COLLECT_FERTILIZER",))
    # --- Crops
    for p, t in s.plants:
        c = t.get("crop")
        cd = CROPS.get(c)
        if not cd:
            add(p, 5, ("DIG",))
            continue
        age = day - t.get("planted_day", day)
        watered = t.get("watered_today", False)
        cu = t.get("consecutive_unwatered", 0)
        yu = t.get("yield_units", 0)
        h, cap = CROP_H[c]
        pp = p_now(s, c)
        potential = cap * pp
        hopeless = (age + (LAST_DAY - day) < cd["first"]) and not cd["ongoing"]
        ws = (cd["maxd"] + 1) // 2
        inwin = (not cd["ongoing"]) and ws <= age <= cd["maxd"]
        if not watered and not hopeless:
            if cu >= 1:
                add(p, max(60.0, potential * 0.8), ("WATER",))
            elif inwin and yu < cd["cap"]:
                add(p, pp * 1.0 + 5, ("WATER",))
        ripe = False
        if age >= cd["first"] and yu > 0:
            if cd["ongoing"]:
                ripe = True
            else:
                ripe = yu >= cd["cap"] or age >= cd["maxd"] or s.final or (
                    age >= cd["first"] and s.left < 30)
        if ripe:
            val = yu * pp
            if inwin and not watered and yu < cd["cap"] and not s.final:
                val = 0.5
            add(p, val + 10, ("HARVEST",))
    for p in s.weeds:
        add(p, 12, ("DIG",))
    # --- placements and plantings
    place, plant = tile_plan(s)
    for tile, atype, is_empty in place:
        info = ANIMALS[atype]
        if is_empty:
            add(tile, 260, (info["build"],), atype)
        else:
            add(tile, 300, ("PLACE", atype), atype)
    for tile, crop in plant:
        add(tile, 120 + p_now(s, crop) * 0.5, ("PLANT", crop))
    # structure built but not yet occupied, and we are carrying that animal
    for tile, kind in s.structs:
        for atype, info in ANIMALS.items():
            if info["struct"] == kind:
                add(tile, 300, ("PLACE", atype), atype)
    return G


# --------------------------------------------------------------------------
# arbitration + spatial scheduler
# --------------------------------------------------------------------------
def schedule(s, G):
    n = len(s.units)
    acts = [["PASS"] for _ in range(n)]
    assigned = [False] * n
    claimed = set()
    done = set()
    seeds_left = dict(s.seeds)
    shed_left = dict(s.shed)

    def doable(i, act, need):
        if need and s.invs[i].get(need, 0) <= 0:
            return False
        if act[0] == "PLANT" and seeds_left.get(act[1], 0) <= 0:
            return False
        return True

    # Safety: shed overflow guard and final-day drops
    carried = sum(sum(v for k, v in inv.items()) for inv in s.invs)
    overflow = (s.shed_total + carried) > 94
    for i, pos in enumerate(s.units):
        inv = s.invs[i]
        prod = sum(v for k, v in inv.items() if k not in INPUTS)
        if prod <= 0:
            continue
        force = (overflow and prod >= 3) or (s.final and (s.hour >= 13 or prod >= 12)) \
            or (s.left <= 8 and prod > 0)
        if not force:
            continue
        sh = nearest_shed(s, pos)
        if pos == sh:
            acts[i] = ["DROP"]
        else:
            acts[i] = [step_toward(pos, sh)]
        assigned[i] = True

    # 1) standing on work: do it (highest value first)
    for i, pos in enumerate(s.units):
        if assigned[i] or pos in claimed:
            continue
        g = G.get(pos)
        if not g:
            continue
        for val, act, need in sorted(g, key=lambda z: -z[0]):
            if (pos, act) in done or not doable(i, act, need):
                continue
            acts[i] = list(act)
            assigned[i] = True
            claimed.add(pos)
            done.add((pos, act))
            if act[0] == "PLANT":
                seeds_left[act[1]] -= 1
            break

    # 2) global greedy matching of idle units to tiles
    unfed = sum(1 for _, t in s.animals if not t.get("fed_today"))
    cands = []
    for i, pos in enumerate(s.units):
        if assigned[i]:
            continue
        inv = s.invs[i]
        for tile, g in G.items():
            if tile in claimed:
                continue
            val, nact, fetch = 0.0, 0, None
            for v, act, need in g:
                if (tile, act) in done:
                    continue
                if act[0] == "PLANT" and seeds_left.get(act[1], 0) <= 0:
                    continue
                if need and inv.get(need, 0) <= 0:
                    if shed_left.get(need, 0) <= 0:
                        continue
                    if fetch is None:
                        fetch = need
                    elif fetch != need:
                        continue
                val += v
                nact += 1
            if nact == 0:
                continue
            if fetch:
                sh = nearest_shed(s, pos)
                cost = dist(pos, sh) + dist(sh, tile) + 1
            else:
                sh = None
                cost = dist(pos, tile)
            score = val / (cost + 0.7 * nact + 1.0)
            cands.append((-score, i, tile, fetch, sh))
    cands.sort(key=lambda c: (c[0], c[1], c[2]))
    fetchers = []
    for negsc, i, tile, fetch, sh in cands:
        if assigned[i] or tile in claimed:
            continue
        pos = s.units[i]
        assigned[i] = True
        claimed.add(tile)
        if fetch:
            fetchers.append((i, fetch, sh))
        else:
            m = step_toward(pos, tile)
            acts[i] = [m] if m else ["PASS"]
    # fetch orders
    by_item = {}
    for i, fetch, sh in fetchers:
        by_item.setdefault(fetch, []).append(i)
    for item, ids in by_item.items():
        if item == "WHEAT":
            want = unfed
        else:
            want = sum(1 for _, a, _e in tile_plan(s)[0] if a == item)
        per = max(1, int(math.ceil(want / float(len(ids)))))
        for i in ids:
            pos = s.units[i]
            sh = nearest_shed(s, pos)
            if pos == sh:
                q = int(min(shed_left.get(item, 0), per + (1 if item == "WHEAT" else 0)))
                if item == "WHEAT":
                    q = min(q, 14)
                if q > 0:
                    acts[i] = ["PICKUP", item, q]
                    shed_left[item] = shed_left.get(item, 0) - q
                else:
                    acts[i] = ["PASS"]
            else:
                m = step_toward(pos, sh)
                acts[i] = [m] if m else ["PASS"]
    return acts


# --------------------------------------------------------------------------
# entry point
# --------------------------------------------------------------------------
def _safe(fn, default, *a):
    try:
        return fn(*a)
    except Exception as e:          # isolate one specialist, never the whole farm
        if LOCAL_TESTING:
            raise
        _ERR.append((fn.__name__, repr(e)))
        return default


def plan(obs):
    s = observe(obs)
    market = _safe(market_council, [], s)
    G = _safe(gen_groups, {}, s)
    acts = _safe(schedule, None, s, G) if G else [["PASS"] for _ in s.units]
    if acts is None:
        acts = [["PASS"] for _ in s.units]
    return {"farmer": acts[0] if acts else ["PASS"], "hands": acts[1:], "market": market}


def agent(obs):
    try:
        return plan(obs)
    except Exception as e:
        if LOCAL_TESTING:
            raise
        _ERR.append(("plan", repr(e)))
        try:
            me = obs["farms"][obs.get("player", 0)]
            return {"farmer": ["PASS"], "hands": [["PASS"] for _ in (me.get("hands") or [])],
                    "market": []}
        except Exception:
            return {"farmer": ["PASS"], "hands": [], "market": []}
