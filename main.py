"""AgriNexus OS — Multi-agent autonomous farm intelligence.

Kaggriculture competition entry point. Specialist agents cooperate through a
single deterministic arbitration layer: Crop, Livestock, Fertility, Market,
Expansion, and Workforce. No network calls, model downloads, external state,
or persistent runtime dependencies are required.
"""

import math

CROPS = {
    "WHEAT": {"seed": 10, "base": 25, "first": 2, "maxday": 4, "ongoing": False},
    "CARROT": {"seed": 20, "base": 35, "first": 2, "maxday": 3, "ongoing": False},
    "TOMATO": {"seed": 50, "base": 60, "first": 8, "maxday": 8, "ongoing": True},
    "STRAWBERRY": {"seed": 100, "base": 120, "first": 10, "maxday": 10, "ongoing": True},
    "MELON": {"seed": 80, "base": 250, "first": 10, "maxday": 12, "ongoing": False},
}
ANIMALS = {
    "COW": {"cost": 400, "structure": "PASTURE", "build": "BUILD_PASTURE", "product": "MILK", "first": 8, "interval": 2, "max": 6},
    "SHEEP": {"cost": 500, "structure": "PASTURE", "build": "BUILD_PASTURE", "product": "WOOL", "first": 6, "interval": 3, "max": 6},
    "GOOSE": {"cost": 300, "structure": "COOP", "build": "BUILD_COOP", "product": "EGG", "first": 4, "interval": 1, "max": 4},
}
BASE = {k: v["base"] for k, v in CROPS.items()}
BASE.update({"EGG": 50, "MILK": 160, "WOOL": 200, "FERTILIZER": 100})

# Tuned operating envelope. These are deliberately conservative because the
# ladder rewards wins, not raw margin, and the market is shared.
COW_MAX, SHEEP_MAX, GOOSE_MAX = 6, 5, 4
CROP_TARGETS = {"WHEAT": 8, "CARROT": 4, "TOMATO": 4, "STRAWBERRY": 6, "MELON": 2}
MAX_HANDS, MAX_QUADRANTS = 11, 2
LAST_ANIMAL_DAY = 16
HIRE_COSTS = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89]
SELL_CAP = {"STRAWBERRY": 6, "MILK": 8, "WOOL": 8, "EGG": 10,
            "TOMATO": 5, "CARROT": 8, "MELON": 2, "FERTILIZER": 4}
P = {"RESCUE": 0, "FEED": 1, "HARVEST": 2, "CARE": 3, "WATER": 4,
     "PLACE": 5, "FERTILIZE": 6, "FERT": 7, "BUILD": 8, "PLANT": 9, "DIG": 10}


def tile(tiles, p):
    return tiles[p[1]][p[0]]


def dist(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def move(pos, target):
    x, y = pos
    tx, ty = target
    if x < tx: return ["EAST"]
    if x > tx: return ["WEST"]
    if y < ty: return ["SOUTH"]
    if y > ty: return ["NORTH"]
    return None


def shed_cells(n):
    h = n // 2
    return [(h-1, h-1), (h, h-1), (h-1, h), (h, h)]


def nearest_shed(pos, n):
    return min(shed_cells(n), key=lambda p: dist(pos, p))


def unlocked(tiles):
    for y, row in enumerate(tiles):
        for x, t in enumerate(row):
            if t != "LOCKED":
                yield (x, y)


def survey(tiles):
    s = {"empty": [], "weeds": [], "free_coop": [], "free_pasture": [],
         "crop": {}, "animals": {"COW": 0, "SHEEP": 0, "GOOSE": 0}}
    for p in unlocked(tiles):
        t = tile(tiles, p)
        if t is None:
            s["empty"].append(p)
        elif isinstance(t, dict):
            k = t.get("kind")
            if k == "WEED":
                s["weeds"].append(p)
            elif k == "PLANT":
                c = t.get("crop")
                s["crop"][c] = s["crop"].get(c, 0) + 1
            elif k in ("COOP", "PASTURE"):
                a = t.get("animal")
                if a: s["animals"][a] += 1
                elif k == "COOP": s["free_coop"].append(p)
                else: s["free_pasture"].append(p)
    return s


def stock(private):
    out = {a: private.get("shed", {}).get(a, 0) for a in ANIMALS}
    for inv in private.get("inventories", []) or []:
        for a in out:
            out[a] += inv.get(a, 0)
    return out


def live_count(s):
    return sum(s["animals"].values())


def target_animals(a):
    return {"COW": COW_MAX, "SHEEP": SHEEP_MAX, "GOOSE": GOOSE_MAX}[a]


def ready(tile_, day):
    if not isinstance(tile_, dict) or tile_.get("kind") != "PLANT":
        return False
    c = tile_.get("crop")
    if c not in CROPS:
        return False
    return tile_.get("yield_units", 0) > 0 and day - tile_.get("planted_day", day) >= CROPS[c]["first"]


def animal_buy_ok(a, day, cash, wheat_price, product_price):
    if day > LAST_ANIMAL_DAY:
        return False
    info = ANIMALS[a]
    net = product_price / info["interval"] - wheat_price
    return net > 0 and cash >= info["cost"] + 250


def desired_crop(day, prices, s, seeds=None):
    """Crop portfolio agent: diversify while protecting feed and season time."""
    seeds = seeds or {}
    candidates = []
    for crop, info in CROPS.items():
        have = s["crop"].get(crop, 0) + seeds.get(crop, 0)
        deficit = max(0, CROP_TARGETS.get(crop, 0) - have)
        if deficit <= 0 or day + info["first"] > 30:
            continue
        market_ratio = prices.get(crop, info["base"]) / max(1, info["base"])
        feed_bonus = 1.35 if crop == "WHEAT" and live_count(s) else 0.0
        deficit_bonus = deficit / max(1, CROP_TARGETS.get(crop, 1))
        time_bonus = min(1.0, (30 - day) / max(1, info["maxday"])) * 0.35
        score = info["weight"] * market_ratio + deficit_bonus + feed_bonus + time_bonus
        candidates.append((score, crop))
    return max(candidates)[1] if candidates else None


def tasks(obs, me, private, s):
    day, tiles = obs["day"], me["tiles"]
    result = []
    shed = private.get("shed", {})

    for p in unlocked(tiles):
        t = tile(tiles, p)
        if not isinstance(t, dict):
            continue
        k = t.get("kind")
        if k == "WEED":
            result.append((P["DIG"], p, ["DIG"], "DIG"))
        elif k == "PLANT":
            age = day - t.get("planted_day", day)
            if ready(t, day):
                result.append((P["HARVEST"], p, ["HARVEST"], "HARVEST"))
            if not t.get("watered_today", False):
                urgent = "RESCUE" if t.get("consecutive_unwatered", 0) >= 1 else "WATER"
                result.append((P[urgent], p, ["WATER"], "WATER"))
            if (t.get("crop") in ("CARROT", "TOMATO", "STRAWBERRY", "MELON")
                    and shed.get("FERTILIZER", 0) > 0
                    and t.get("fertilized_until_day", -1) < day
                    and age >= max(2, CROPS[t.get("crop")]["first"] - 2)):
                result.append((P["FERTILIZE"], p, ["FERTILIZE"], "FERTILIZE"))
        elif k in ("COOP", "PASTURE") and t.get("animal"):
            if not t.get("fed_today", False):
                urgent = "RESCUE" if t.get("consecutive_unfed", 0) >= 1 else "FEED"
                result.append((P[urgent], p, ["FEED"], "FEED"))
            elif not t.get("cared_today", False):
                result.append((P["CARE"], p, ["CARE"], "CARE"))
            if t.get("yield_units", 0) >= max(1, ANIMALS[t["animal"]]["max"] - 2):
                result.append((P["HARVEST"], p, ["HARVEST"], "HARVEST"))
            if t.get("fertilizer_available", False):
                result.append((P["FERT"], p, ["COLLECT_FERTILIZER"], "FERT"))

    # Build only as the herd becomes affordable. Structures are placed near the
    # shed because FEED/CARE/HARVEST recur for the entire season.
    st = stock(private)
    prices = obs.get("market", {}).get("prices", {})
    for a in ("COW", "SHEEP"):
        if s["animals"][a] + st[a] >= target_animals(a):
            continue
        if not animal_buy_ok(a, day, me["money"], prices.get("WHEAT", 25),
                             prices.get(ANIMALS[a]["product"], BASE[ANIMALS[a]["product"]])):
            continue
        free = s["free_pasture"]
        if not free and s["empty"]:
            p = min(s["empty"], key=lambda q: min(dist(q, z) for z in shed_cells(len(tiles))))
            result.append((P["BUILD"], p, [ANIMALS[a]["build"]], "BUILD"))
            s["empty"].remove(p)
            free.append(p)

    # Place animals already purchased.
    for a in ("COW", "SHEEP", "GOOSE"):
        if st[a] <= 0:
            continue
        free = s["free_pasture"] if ANIMALS[a]["structure"] == "PASTURE" else s["free_coop"]
        if free:
            result.append((P["PLACE"], free.pop(0), ["PLACE", a], "PLACE"))
            st[a] -= 1

    crop = desired_crop(day, prices, s)
    seeds = private.get("seeds", {})
    if crop and seeds.get(crop, 0) > 0:
        for p in sorted(s["empty"], key=lambda q: min(dist(q, z) for z in shed_cells(len(tiles)))):
            result.append((P["PLANT"], p, ["PLANT", crop], "PLANT"))
            seeds[crop] -= 1
            if seeds[crop] <= 0:
                break
    return result


def assign(units, work):
    a = [None] * len(units)
    left = list(range(len(work)))
    # Standing-on-work pass: this small scheduling rule materially reduces
    # movement and prevents the priority queue from stealing a ready worker.
    for i, pos in enumerate(units):
        hits = [j for j in left if work[j][1] == pos]
        if hits:
            j = min(hits, key=lambda z: (work[z][0], z))
            a[i], left = work[j], [z for z in left if z != j]
    for i in [j for j, x in enumerate(a) if x is None]:
        if not left: break
        j = min(left, key=lambda z: (work[z][0], dist(units[i], work[z][1]), z))
        a[i], left = work[j], [z for z in left if z != j]
    return a


def dispatch(pos, task, inv, private, n):
    if task is None:
        return ["PASS"]
    _, target, action, kind = task
    if kind == "FEED" and inv.get("WHEAT", 0) <= 0:
        shed = nearest_shed(pos, n)
        if pos != shed: return move(pos, shed)
        q = min(3, private.get("shed", {}).get("WHEAT", 0))
        return ["PICKUP", "WHEAT", q] if q else ["PASS"]
    if kind == "PLACE":
        a = action[1]
        if inv.get(a, 0) <= 0:
            shed = nearest_shed(pos, n)
            if pos != shed: return move(pos, shed)
            return ["PICKUP", a, 1] if private.get("shed", {}).get(a, 0) else ["PASS"]
    if kind == "FERTILIZE" and inv.get("FERTILIZER", 0) <= 0:
        shed = nearest_shed(pos, n)
        if pos != shed: return move(pos, shed)
        return ["PICKUP", "FERTILIZER", 1] if private.get("shed", {}).get("FERTILIZER", 0) else ["PASS"]
    return move(pos, target) or action


def market(obs, me, private, s):
    day = obs["day"]
    prices = obs.get("market", {}).get("prices", {})
    shed = private.get("shed", {})
    seeds = private.get("seeds", {})
    orders, cash = [], float(me.get("money", 0))
    live = live_count(s)

    # Liquidate continuously, but keep feed stock. High-glut products are drip-sold.
    reserve_wheat = max(2, live * 2)
    q = max(0, shed.get("WHEAT", 0) - reserve_wheat)
    if q: orders.append(["SELL", "WHEAT", min(q, 10)])
    for item, qty in shed.items():
        if item == "WHEAT" or qty <= 0 or len(orders) >= 6:
            continue
        ratio = prices.get(item, BASE.get(item, 1)) / max(1, BASE.get(item, 1))
        n = min(qty, 10 if day >= 28 else SELL_CAP.get(item, 5))
        if ratio <= 0.30: n = 0
        if n: orders.append(["SELL", item, n])

    # Seed portfolio: buy only what is still missing, ranked by current market signal.
    for crop in sorted(CROPS, key=lambda c: prices.get(c, CROPS[c]["base"]) / CROPS[c]["base"], reverse=True):
        if len(orders) >= 8 or day > 29 - CROPS[crop]["first"]:
            continue
        have = s["crop"].get(crop, 0) + seeds.get(crop, 0)
        need = CROP_TARGETS.get(crop, 0) - have
        reserve = 500 + live * max(10, prices.get("WHEAT", 25))
        affordable = int(max(0, cash - reserve) // CROPS[crop]["seed"])
        n = min(5 if crop != "WHEAT" else 8, max(0, need), affordable)
        if n:
            orders.append(["BUY_SEED", crop, n])
            cash -= n * CROPS[crop]["seed"]

    # Livestock portfolio: cows, sheep and geese provide milk, wool and eggs.
    st = stock(private)
    wheat_stock = shed.get("WHEAT", 0)
    for a in ("COW", "SHEEP", "GOOSE"):
        if len(orders) >= 9 or day > LAST_ANIMAL_DAY:
            break
        current = s["animals"][a] + st[a]
        if current >= target_animals(a) or wheat_stock < max(3, live * 2):
            continue
        product = ANIMALS[a]["product"]
        if animal_buy_ok(a, day, cash, prices.get("WHEAT", 25), prices.get(product, BASE[product])):
            orders.append(["BUY_ANIMAL", a, 1])
            cash -= ANIMALS[a]["cost"]
            wheat_stock -= 1
            live += 1

    # Fibonacci labor: scale only with visible work; first hires are cheap.
    work = 0
    for p in unlocked(me["tiles"]):
        t = tile(me["tiles"], p)
        if isinstance(t, dict):
            if t.get("kind") == "PLANT": work += 1
            elif t.get("kind") in ("COOP", "PASTURE") and t.get("animal"): work += 2
            elif t.get("kind") == "WEED": work += 1
    current = len(me.get("hands", []))
    desired = min(MAX_HANDS, max(3, 1 + math.ceil(work / 4)))
    if live >= 6: desired = max(desired, min(MAX_HANDS, 5 + live // 3))
    while current < desired and current < len(HIRE_COSTS) and len(orders) < 10:
        cost = HIRE_COSTS[current]
        if cash < cost + 150: break
        orders.append(["HIRE"]); cash -= cost; current += 1

    # Q2 only after the first quadrant is productive and labor is already present.
    if (len(me.get("unlocked_quadrants", [])) < MAX_QUADRANTS and day >= 12
            and len(me.get("hands", [])) >= 7 and cash >= 1800 and len(orders) < 10):
        owned = sum(1 for row in me["tiles"] for t in row if t != "LOCKED")
        used = sum(1 for row in me["tiles"] for t in row if t not in (None, "LOCKED"))
        if owned and used / owned >= 0.70:
            orders.append(["BUY_LAND"])
    return orders[:10]


def _impl(obs):
    """Observe → specialist proposals → arbitration → execution."""
    player = obs["player"]
    me = obs["farms"][player]
    private = obs.get("private", {}) or {}
    s = survey(me["tiles"])

    # Specialist agents. Each produces proposals; none directly controls a unit.
    crop_proposals = tasks(obs, me, private, s)  # Crop lifecycle + portfolio.
    livestock_proposals = [
        x for x in tasks(obs, me, private, s)
        if x[3] in ("FEED", "CARE", "HARVEST", "BUILD", "PLACE", "FERT")
    ]
    fertility_proposals = [
        x for x in tasks(obs, me, private, s)
        if x[3] in ("FERT", "FERTILIZE")
    ]

    # Explicit crop portfolio proposal: variety is selected from deficits + market.
    chosen = desired_crop(
        obs["day"], obs.get("market", {}).get("prices", {}),
        s, private.get("seeds", {})
    )
    if chosen and private.get("seeds", {}).get(chosen, 0) > 0:
        for p in sorted(
            s["empty"],
            key=lambda q: min(dist(q, z) for z in shed_cells(len(me["tiles"])))
        )[:2]:
            crop_proposals.append((P["PLANT"], p, ["PLANT", chosen], "PLANT"))

    # One arbitration layer removes conflicting specialist proposals.
    proposals = {}
    for proposal in crop_proposals + livestock_proposals + fertility_proposals:
        priority, target, action, kind = proposal
        key = (tuple(target), kind)
        if key not in proposals or priority < proposals[key][0]:
            proposals[key] = proposal
    work = sorted(proposals.values(), key=lambda x: (x[0], x[1][1], x[1][0]))

    positions = [tuple(me["farmer"])] + [tuple(x) for x in me.get("hands", [])]
    assigned = assign(positions, work)
    inventories = private.get("inventories", []) or []
    actions = []
    for i, pos in enumerate(positions):
        inv = inventories[i] if i < len(inventories) else {}
        actions.append(dispatch(pos, assigned[i], inv, private, len(me["tiles"])))

    # Market/Expansion/Workforce agents share the same final economic envelope.
    return {
        "farmer": actions[0] if actions else ["PASS"],
        "hands": actions[1:],
        "market": market(obs, me, private, s),
    }


def agent(obs):
    try:
        return _impl(obs)
    except Exception:
        player = obs.get("player", 0)
        hands = obs.get("farms", [{}])[player].get("hands", [])
        return {"farmer": ["PASS"], "hands": [["PASS"] for _ in hands], "market": []}
