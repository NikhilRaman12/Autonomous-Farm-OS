"""AgriNexus OS — closed-loop autonomous farm agent for Kaggriculture.

Architecture:
  OBSERVE -> SPECIALIST PLANS -> ECONOMIC ARBITRATION -> ROUTE/EXECUTE
  -> RECONCILE from the next observation.

The specialists are deliberately lightweight and deterministic:
  - Crop planner: crop lifecycle, yield timing and fertilizer ROI
  - Livestock planner: feed/care/production/fertilizer lifecycle
  - Market planner: liquidity, price-aware selling and procurement
  - Workforce planner: marginal throughput versus daily hire cost
  - Expansion planner: only unlock capacity that can be monetised before season end
  - Safety/terminal planner: protects survival and liquidates before the final state

This is a competition-safe single-file agent: no network, files, model downloads,
persistent state, or non-standard dependencies.
"""

import math

CROPS = {
    "WHEAT": {"seed": 10, "base": 25, "first": 2, "maxday": 4, "max": 6, "ongoing": False},
    "CARROT": {"seed": 20, "base": 35, "first": 2, "maxday": 3, "max": 4, "ongoing": False},
    "TOMATO": {"seed": 50, "base": 60, "first": 8, "maxday": 8, "max": 4, "ongoing": True},
    "STRAWBERRY": {"seed": 100, "base": 120, "first": 10, "maxday": 10, "max": 4, "ongoing": True},
    "MELON": {"seed": 80, "base": 250, "first": 10, "maxday": 12, "max": 6, "ongoing": False},
}
ANIMALS = {
    "COW": {"cost": 400, "structure": "PASTURE", "build": "BUILD_PASTURE",
            "product": "MILK", "interval": 2, "max": 6},
    "SHEEP": {"cost": 500, "structure": "PASTURE", "build": "BUILD_PASTURE",
              "product": "WOOL", "interval": 3, "max": 6},
    "GOOSE": {"cost": 300, "structure": "COOP", "build": "BUILD_COOP",
              "product": "EGG", "interval": 1, "max": 4},
}
BASE = {k: v["base"] for k, v in CROPS.items()}
BASE.update({"EGG": 50, "MILK": 160, "WOOL": 200, "FERTILIZER": 100})

# Conservative production envelope. It is intentionally dynamic: these are
# ceilings, not promises to buy all assets.
ANIMAL_CAP = {"COW": 5, "SHEEP": 7, "GOOSE": 4}
CROP_PLAN = {"WHEAT": 14, "MELON": 8, "STRAWBERRY": 4, "CARROT": 3}
MAX_HANDS = 8
MAX_ORDERS = 10
SEASON_END = 29
WHEAT_FLOOR = 18
SELL_FLOOR = {"WHEAT": 18, "CARROT": 24, "TOMATO": 42,
              "STRAWBERRY": 88, "MELON": 190, "EGG": 38,
              "MILK": 115, "WOOL": 135, "FERTILIZER": 70}
SELL_BATCH = {"WHEAT": 30, "CARROT": 12, "TOMATO": 8, "STRAWBERRY": 5,
              "MELON": 4, "EGG": 12, "MILK": 10, "WOOL": 8, "FERTILIZER": 8}

# Lower number = more urgent.
PRIO = {
    "FEED": 0, "HARVEST": 1, "WATER": 2, "CARE": 3, "FERT": 4,
    "FERTILIZE": 5, "PLACE": 6, "DIG": 7, "BUILD": 8, "PLANT": 9
}


def tile(tiles, p):
    return tiles[p[1]][p[0]]


def dist(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def move(pos, target):
    x, y = pos
    tx, ty = target
    if x < tx:
        return ["EAST"]
    if x > tx:
        return ["WEST"]
    if y < ty:
        return ["SOUTH"]
    if y > ty:
        return ["NORTH"]
    return None


def shed_cells(n):
    h = n // 2
    return [(h - 1, h - 1), (h, h - 1), (h - 1, h), (h, h)]


def nearest_shed(pos, n):
    return min(shed_cells(n), key=lambda q: dist(pos, q))


def unlocked(tiles):
    for y, row in enumerate(tiles):
        for x, value in enumerate(row):
            if value != "LOCKED":
                yield (x, y)


def survey(tiles):
    s = {
        "empty": [], "weeds": [], "free_coop": [], "free_pasture": [],
        "crop": {}, "animals": {"COW": 0, "SHEEP": 0, "GOOSE": 0}
    }
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
                if a:
                    s["animals"][a] += 1
                elif k == "COOP":
                    s["free_coop"].append(p)
                else:
                    s["free_pasture"].append(p)
    return s


def stock(private):
    out = {a: private.get("shed", {}).get(a, 0) for a in ANIMALS}
    for inv in private.get("inventories", []) or []:
        for a in out:
            out[a] += inv.get(a, 0)
    return out


def animal_total(s, private):
    q = stock(private)
    return {a: s["animals"][a] + q[a] for a in ANIMALS}


def live_count(s, private):
    q = animal_total(s, private)
    return sum(q.values())


def work_size(me):
    n = 0
    for p in unlocked(me["tiles"]):
        t = tile(me["tiles"], p)
        if not isinstance(t, dict):
            continue
        if t.get("kind") == "PLANT":
            n += 1
        elif t.get("kind") in ("PASTURE", "COOP") and t.get("animal"):
            n += 2
        elif t.get("kind") == "WEED":
            n += 1
    return n


def ready(t, day):
    if not isinstance(t, dict) or t.get("kind") != "PLANT":
        return False
    c = t.get("crop")
    info = CROPS.get(c)
    return bool(info and t.get("yield_units", 0) > 0 and
                day - t.get("planted_day", day) >= info["first"])


def days_left(day):
    return max(0, SEASON_END - day)


def crop_value(crop, price):
    info = CROPS[crop]
    return price / max(1, info["seed"])


def choose_crop(day, prices, survey_state, seeds, money):
    """Crop specialist: choose a crop by remaining horizon + market ROI.

    Melon receives a strong economic prior because it converts a single planting
    into a high-value harvest. Wheat remains mandatory when livestock exists.
    """
    if day + 2 >= SEASON_END:
        return "WHEAT" if seeds.get("WHEAT", 0) else None

    candidates = []
    for crop, info in CROPS.items():
        have = survey_state["crop"].get(crop, 0) + seeds.get(crop, 0)
        need = CROP_PLAN.get(crop, 0) - have
        if need <= 0:
            continue
        if day + info["first"] > SEASON_END:
            continue
        p = prices.get(crop, info["base"])
        score = crop_value(crop, p)

        # High-value one-shot crop: favour it while enough season remains.
        if crop == "MELON":
            score += 2.4 if day <= 17 else 0.5
        elif crop == "STRAWBERRY":
            score += 1.4 if 5 <= day <= 17 else 0.2
        elif crop == "WHEAT":
            score += 1.2 if live_count(survey_state, {}) else 0.0
        elif crop == "CARROT":
            score += 0.3

        # Avoid buying seed that cannot be turned into cash before season end.
        if day + info["maxday"] > SEASON_END:
            score -= 1.5

        # Market-relative signal: don't blindly flood an already depressed crop.
        ratio = p / max(1, info["base"])
        score += max(-1.5, min(1.5, ratio - 1.0))
        candidates.append((score, crop))

    if not candidates:
        return None
    return max(candidates)[1]


def crop_tasks(obs, me, private, s):
    day = obs["day"]
    prices = obs.get("market", {}).get("prices", {})
    seeds = private.get("seeds", {}) or {}
    chosen = choose_crop(day, prices, s, seeds, me.get("money", 0))
    jobs = []

    # First-class crop lifecycle: water every day, harvest on maturity,
    # fertilize only where the yield uplift can still be monetised.
    for p in unlocked(me["tiles"]):
        t = tile(me["tiles"], p)
        if not isinstance(t, dict):
            continue
        if t.get("kind") == "WEED":
            jobs.append((PRIO["DIG"], p, ["DIG"], "DIG"))
            continue
        if t.get("kind") != "PLANT":
            continue
        c = t.get("crop")
        if ready(t, day):
            jobs.append((PRIO["HARVEST"], p, ["HARVEST"], "HARVEST"))
        if not t.get("watered_today", False):
            jobs.append((PRIO["WATER"], p, ["WATER"], "WATER"))
        if private.get("shed", {}).get("FERTILIZER", 0) > 0:
            age = day - t.get("planted_day", day)
            # Fertilize only while the crop can still convert it into harvest.
            if c == "MELON" and 5 <= age <= 7:
                jobs.append((PRIO["FERTILIZE"], p, ["FERTILIZE"], "FERTILIZE"))
            elif c == "STRAWBERRY" and 8 <= age <= 11:
                jobs.append((PRIO["FERTILIZE"], p, ["FERTILIZE"], "FERTILIZE"))
            elif c in ("WHEAT", "CARROT") and 1 <= age <= 2:
                jobs.append((PRIO["FERTILIZE"], p, ["FERTILIZE"], "FERTILIZE"))

    # Plant only when a seed is actually available; never create phantom work.
    if chosen and seeds.get(chosen, 0) > 0 and s["empty"]:
        near = sorted(
            s["empty"],
            key=lambda q: min(dist(q, z) for z in shed_cells(len(me["tiles"])))
        )
        # Batch planting is bounded by active units, preventing an overbuilt field.
        n = min(seeds[chosen], len(near), len(me.get("hands", [])) + 1, 4)
        for p in near[:n]:
            jobs.append((PRIO["PLANT"], p, ["PLANT", chosen], "PLANT"))
    return jobs


def livestock_tasks(obs, me, private, s):
    day = obs["day"]
    jobs = []
    for p in unlocked(me["tiles"]):
        t = tile(me["tiles"], p)
        if not (isinstance(t, dict) and t.get("kind") in ("PASTURE", "COOP")
                and t.get("animal")):
            continue
        if not t.get("fed_today", False):
            jobs.append((PRIO["FEED"], p, ["FEED"], "FEED"))
        elif not t.get("cared_today", False):
            jobs.append((PRIO["CARE"], p, ["CARE"], "CARE"))
        if t.get("yield_units", 0) >= max(2, ANIMALS[t["animal"]]["max"] - 1):
            jobs.append((PRIO["HARVEST"], p, ["HARVEST"], "HARVEST"))
        if t.get("fertilizer_available", False):
            jobs.append((PRIO["FERT"], p, ["COLLECT_FERTILIZER"], "FERT"))

    # Only buy animals early enough to amortise their production cycle.
    totals = animal_total(s, private)
    prices = obs.get("market", {}).get("prices", {})
    wheat_price = prices.get("WHEAT", 25)
    cash = float(me.get("money", 0))
    free_pasture = list(s["free_pasture"])
    free_coop = list(s["free_coop"])
    shed = private.get("shed", {})
    wheat = shed.get("WHEAT", 0)

    for animal in ("SHEEP", "COW", "GOOSE"):
        cap = ANIMAL_CAP[animal]
        if totals[animal] >= cap:
            continue
        if day > 16:
            continue
        info = ANIMALS[animal]
        product_price = prices.get(info["product"], BASE[info["product"]])
        # Production must clear a conservative feed + capital hurdle.
        interval_feed = max(1, info["interval"]) * wheat_price
        if product_price < interval_feed * 0.85:
            continue
        free = free_pasture if info["structure"] == "PASTURE" else free_coop
        if not free:
            continue
        # Don't spend the farm's operating buffer on an asset purchase.
        if cash < info["cost"] + 700:
            continue
        p = free.pop(0)
        jobs.append((PRIO["BUILD"], p, [info["build"]], "BUILD"))
        jobs.append((PRIO["PLACE"], p, ["PLACE", animal], "PLACE"))
        cash -= info["cost"]
        totals[animal] += 1

    # Place purchased animals already in the shed when structures exist.
    st = stock(private)
    for animal in ("SHEEP", "COW", "GOOSE"):
        free = s["free_pasture"] if ANIMALS[animal]["structure"] == "PASTURE" else s["free_coop"]
        for p in list(free):
            if st[animal] <= 0:
                break
            jobs.append((PRIO["PLACE"], p, ["PLACE", animal], "PLACE"))
            st[animal] -= 1
    return jobs


def assign(units, jobs):
    """Spatial scheduler: preserve worker locality instead of global thrashing."""
    out = [None] * len(units)
    remaining = list(range(len(jobs)))

    # If a unit is already standing on a required tile, execute there first.
    for i, pos in enumerate(units):
        hits = [j for j in remaining if jobs[j][1] == pos]
        if hits:
            j = min(hits, key=lambda z: (jobs[z][0], z))
            out[i] = jobs[j]
            remaining.remove(j)

    # Then allocate highest-priority nearby work.
    for i, pos in enumerate(units):
        if out[i] is not None or not remaining:
            continue
        j = min(
            remaining,
            key=lambda z: (jobs[z][0], dist(pos, jobs[z][1]), z)
        )
        out[i] = jobs[j]
        remaining.remove(j)
    return out


def dispatch(pos, job, inv, private, n):
    if job is None:
        return ["PASS"]
    _, target, action, kind = job

    if kind == "FEED" and inv.get("WHEAT", 0) <= 0:
        sh = nearest_shed(pos, n)
        if pos != sh:
            return move(pos, sh)
        q = min(4, private.get("shed", {}).get("WHEAT", 0))
        return ["PICKUP", "WHEAT", q] if q else ["PASS"]

    if kind == "PLACE" and inv.get(action[1], 0) <= 0:
        sh = nearest_shed(pos, n)
        if pos != sh:
            return move(pos, sh)
        return (["PICKUP", action[1], 1]
                if private.get("shed", {}).get(action[1], 0) > 0
                else ["PASS"])

    if kind == "FERTILIZE" and inv.get("FERTILIZER", 0) <= 0:
        sh = nearest_shed(pos, n)
        if pos != sh:
            return move(pos, sh)
        return (["PICKUP", "FERTILIZER", 1]
                if private.get("shed", {}).get("FERTILIZER", 0) > 0
                else ["PASS"])

    return move(pos, target) or action


def sell_orders(day, prices, shed, live):
    orders = []
    # Liquidate products only when price is economically acceptable; late-season
    # mode becomes more aggressive because inventory has zero terminal value.
    late = day >= 26
    for item, qty in shed.items():
        if qty <= 0 or item in ("COW", "SHEEP", "GOOSE"):
            continue
        if len(orders) >= MAX_ORDERS:
            break
        price = prices.get(item, BASE.get(item, 1))
        floor = SELL_FLOOR.get(item, 1)
        if late or price >= floor:
            reserve = live * 3 if item == "WHEAT" else 0
            n = min(max(0, qty - reserve), SELL_BATCH.get(item, 8))
            if n > 0:
                orders.append(["SELL", item, n])
    return orders


def market_orders(obs, me, private, s):
    """Market specialist: sell first, preserve feed, then invest only in ROI-positive assets."""
    day = obs["day"]
    prices = obs.get("market", {}).get("prices", {})
    shed = private.get("shed", {}) or {}
    seeds = private.get("seeds", {}) or {}
    money = float(me.get("money", 0))
    orders = []
    live = live_count(s, private)

    # SELL is prioritized because shed capacity is finite and unsold terminal
    # inventory is worthless.
    orders.extend(sell_orders(day, prices, shed, live))
    orders = orders[:MAX_ORDERS]

    wheat_price = prices.get("WHEAT", 25)
    wheat_stock = shed.get("WHEAT", 0) + sum(
        x.get("WHEAT", 0) for x in private.get("inventories", []) or []
    )
    feed_reserve = live * 3

    # Wheat is the livestock operating constraint. Buy only when it is cheap
    # enough and maintain a modest runway rather than hoarding inventory.
    if len(orders) < MAX_ORDERS and live and wheat_stock < feed_reserve:
        if wheat_price <= 45:
            need = min(50, feed_reserve + live * 2 - wheat_stock)
            affordable = int(max(0, money - 800) // max(1, wheat_price))
            n = min(need, affordable)
            if n > 0:
                orders.append(["BUY_PRODUCT", "WHEAT", n])
                money -= n * wheat_price

    # Seed procurement: market-relative ROI, not blind fixed quantities.
    if len(orders) < MAX_ORDERS and day <= 18:
        ranked = sorted(
            CROPS,
            key=lambda c: (prices.get(c, CROPS[c]["base"]) / CROPS[c]["base"]),
            reverse=True,
        )
        for crop in ranked:
            if len(orders) >= MAX_ORDERS:
                break
            info = CROPS[crop]
            have = s["crop"].get(crop, 0) + seeds.get(crop, 0)
            need = CROP_PLAN.get(crop, 0) - have
            if need <= 0 or day + info["first"] > SEASON_END:
                continue
            # Melon is a strategic cash crop; wheat is feed insurance.
            cap = 4 if crop == "MELON" else 3
            reserve = 1000 + live * max(10, wheat_price) * 2
            affordable = int(max(0, money - reserve) // info["seed"])
            n = min(need, cap, affordable)
            if n > 0:
                orders.append(["BUY_SEED", crop, n])
                money -= n * info["seed"]

    # Animal purchases are capped and cash-buffered. Sheep/Cow are useful both
    # for products and fertilizer; geese are short-cycle but not forced.
    if len(orders) < MAX_ORDERS and day <= 16:
        totals = animal_total(s, private)
        for animal in ("SHEEP", "COW", "GOOSE"):
            if len(orders) >= MAX_ORDERS:
                break
            if totals[animal] >= ANIMAL_CAP[animal]:
                continue
            info = ANIMALS[animal]
            product = info["product"]
            pp = prices.get(product, BASE[product])
            feed_cost = wheat_price * info["interval"]
            if pp < feed_cost * 0.85:
                continue
            if money < info["cost"] + 700:
                continue
            free = s["free_pasture"] if info["structure"] == "PASTURE" else s["free_coop"]
            # Structure can be built by the execution layer if an empty tile exists.
            if not free and not s["empty"]:
                continue
            orders.append(["BUY_ANIMAL", animal, 1])
            money -= info["cost"]
            totals[animal] += 1

    # Workforce specialist: hires are daily, so only add a hand when visible
    # workload justifies the marginal throughput. Cheap early hands are useful.
    workload = work_size(me)
    current = len(me.get("hands", []))
    desired = min(MAX_HANDS, max(1, math.ceil(workload / 5)))
    if day <= 4:
        desired = min(MAX_HANDS, max(desired, 2))
    if day >= 25:
        desired = min(desired, 4)

    # Hiring cost rises for each additional hand on that day.
    # We stop before the next cost would consume the operating buffer.
    while current < desired and len(orders) < MAX_ORDERS:
        # Environment uses increasing same-day hire cost; Fibonacci is a safe
        # conservative approximation of the visible early cost schedule.
        fib = (1, 1, 2, 3, 5, 8, 13, 21)
        cost = fib[min(current, len(fib) - 1)]
        if money < cost + 100:
            break
        orders.append(["HIRE"])
        money -= cost
        current += 1

    # Expansion specialist: only buy a quadrant if there is enough season left
    # to operate it and cash remains healthy after the purchase.
    q = len(me.get("unlocked_quadrants", []))
    if len(orders) < MAX_ORDERS and q < 3 and day in (10, 18):
        land_cost = 1000 if q == 1 else 2000
        if day <= 18 and money >= land_cost + 1500:
            orders.append(["BUY_LAND"])

    # Final-day liquidity: no growth purchases; sell every valuable product.
    if day >= 28:
        # Replace speculative orders with terminal liquidation if slots permit.
        orders = [o for o in orders if o[0] == "SELL"]
        if not orders:
            orders = sell_orders(day, prices, shed, live)
    return orders[:MAX_ORDERS]


def arbitrate(*sets):
    """Economic authorization layer: preserve one non-conflicting job per tile."""
    best = {}
    for jobs in sets:
        for job in jobs:
            priority, target, action, kind = job
            key = (tuple(target), kind)
            if key not in best or priority < best[key][0]:
                best[key] = job
    return sorted(best.values(), key=lambda x: (x[0], x[1][1], x[1][0]))


def observe_and_plan(obs):
    """Multi-agent council. Each specialist sees the same real observation."""
    player = obs["player"]
    me = obs["farms"][player]
    private = obs.get("private", {}) or {}
    s = survey(me["tiles"])

    crop = crop_tasks(obs, me, private, s)
    livestock = livestock_tasks(obs, me, private, s)

    # Fertility specialist is represented by crop/animal jobs, but collection
    # remains explicit so fertilizer never silently disappears.
    fertility = [
        j for j in livestock + crop
        if j[3] in ("FERT", "FERTILIZE")
    ]
    crop_only = [j for j in crop if j[3] not in ("FERT", "FERTILIZE")]
    animal_only = [j for j in livestock if j[3] not in ("FERT", "FERTILIZE")]

    jobs = arbitrate(crop_only, animal_only, fertility)
    return me, private, s, jobs


def _impl(obs):
    me, private, s, jobs = observe_and_plan(obs)

    # Execution layer: assign the same job graph to all available units while
    # minimizing movement. This is intentionally recomputed from observation,
    # making the policy closed-loop rather than relying on hidden state.
    units = [tuple(me["farmer"])] + [tuple(x) for x in me.get("hands", [])]
    assigned = assign(units, jobs)
    inventories = private.get("inventories", []) or []

    actions = []
    for i, pos in enumerate(units):
        inv = inventories[i] if i < len(inventories) else {}
        actions.append(dispatch(pos, assigned[i], inv, private, len(me["tiles"])))

    return {
        "farmer": actions[0] if actions else ["PASS"],
        "hands": actions[1:],
        "market": market_orders(obs, me, private, s),
    }


def agent(obs):
    """Competition entrypoint. Never allow an unexpected state to crash a game."""
    try:
        return _impl(obs)
    except Exception:
        try:
            player = obs.get("player", 0)
            farms = obs.get("farms", [])
            hands = farms[player].get("hands", []) if farms else []
            return {
                "farmer": ["PASS"],
                "hands": [["PASS"] for _ in hands],
                "market": [],
            }
        except Exception:
            return {"farmer": ["PASS"], "hands": [], "market": []}
