import json
import os
from datetime import date, datetime, timedelta
from typing import Optional, Dict, Any, List
import math

# ---------- Persistence / defaults ----------
MEMORY_PATH = "memory.json"

# Default config
REMINDER_THRESHOLD_DAYS = 3
ITEMS_WITH_EXPIRY = {
    "milk", "paneer", "curd", "yogurt", "bread", "packaged_oil",
    "butter", "cheese", "ready_meal", "fresh_juice", "biscuits", "juice"
}
DEFAULT_UNIT = {
    "milk": "L", "paneer": "kg", "salt": "kg", "atta": "kg",
    "rice": "kg", "dal": "kg", "onion": "kg", "tomato": "kg", "egg": "count"
}
DEFAULT_CONSUMPTION_PER_DAY = {
    "milk": 1.5, "salt": 0.01, "atta": 0.5, "rice": 0.4, "dal": 0.1
}
DEFAULT_STAPLES = ["salt", "milk", "atta", "rice", "dal", "onion", "tomato"]

# In-memory memory object (persisted to disk)
memory: Dict[str, Any] = {
    "inventory": {},  # item -> {qty, unit, expiry_date (ISO), last_updated}
    "consumption_history": {},  # item -> [ {date_iso, qty} ]
    "preferences": {"reminder_threshold_days": REMINDER_THRESHOLD_DAYS}
}


# ---------- Persistence helpers ----------
def load_memory(path: str = MEMORY_PATH):
    global memory
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            # merge safely (loaded keys override defaults where provided)
            for k, v in loaded.items():
                if isinstance(v, dict) and isinstance(memory.get(k), dict):
                    memory[k].update(v)
                else:
                    memory[k] = v
        except Exception:
            # ignore corrupt file
            pass


def save_memory(path: str = MEMORY_PATH):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(memory, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print("Error saving memory:", e)
        return False


# ---------- Date helpers ----------
def parse_date_iso(s: Optional[str]):
    if s is None:
        return None
    s = str(s).strip()
    if s == "":
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            continue
    return None


def iso_date(d: Optional[date]):
    return d.isoformat() if d is not None else None


def today():
    return date.today()


def safe_float(x):
    try:
        return float(x)
    except Exception:
        return 0.0


# ---------- Core inventory / consumption logic ----------
def add_manual_purchase(name: str, qty, unit: Optional[str] = None, expiry: Optional[str] = None):
    """
    Add a purchase to inventory.
    - If expiry is None, empty, or 'none' -> assign default expiry = today + default_expiry_days (if > 0)
    - default_expiry_days controlled by memory['preferences']['default_expiry_days']
    - Purchases are logged to purchase_history (not consumption_history).
    """
    key = name.lower()
    # normalize qty
    try:
        qty_val = float(qty)
    except Exception:
        qty_val = qty  # allow non-numeric like "1 pack"

    # unit fallback
    unit = (unit or DEFAULT_UNIT.get(key, "unit")).lower()

    # determine expiry: respect explicit valid date strings; treat empty/'none' specially
    expiry_iso = None
    if expiry is not None:
        s = str(expiry).strip().lower()
        if s != "" and s != "none":
            # try parsing user-provided date
            parsed = parse_date_iso(s)
            if parsed:
                expiry_iso = iso_date(parsed)
            else:
                # if parsing failed, leave as None and fall through to default logic
                expiry_iso = None

    # default expiry behavior: use memory preference if expiry not provided
    default_days = int(memory.get("preferences", {}).get("default_expiry_days", 7))
    if (expiry_iso is None) and default_days and default_days > 0:
        expiry_date = today() + timedelta(days=default_days)
        expiry_iso = iso_date(expiry_date)

    # update inventory
    inv = memory.setdefault("inventory", {})
    prev_qty = safe_float(inv.get(key, {}).get("qty", 0.0))
    try:
        new_qty = prev_qty + float(qty_val)
    except Exception:
        new_qty = qty_val

    inv[key] = {
        "qty": new_qty,
        "unit": unit,
        "expiry_date": expiry_iso,
        "last_updated": iso_date(today())
    }

    # Save to purchase_history (do not record purchases as consumption)
    ph = memory.setdefault("purchase_history", {})
    ph.setdefault(key, []).append({"date": iso_date(today()), "qty": float(qty_val) if isinstance(qty_val, (int, float)) else qty_val})

    save_memory()
    return inv[key]


def estimate_consumption_rate_per_day(name: str) -> float:
    """
    Estimate consumption rate per day from consumption_history.
    If no history exists, return DEFAULT_CONSUMPTION_PER_DAY value (or 0.0).
    """
    key = name.lower()
    # allow explicit override in memory (optional)
    overrides = memory.get("consumption_overrides", {}) or {}
    if key in overrides:
        try:
            return float(overrides[key])
        except Exception:
            pass

    hist = memory.get("consumption_history", {}).get(key, [])
    if not hist:
        return DEFAULT_CONSUMPTION_PER_DAY.get(key, 0.0)
    total_qty = 0.0
    earliest = today()
    latest = today()
    for rec in hist:
        qty = safe_float(rec.get("qty", 0.0))
        d = parse_date_iso(rec.get("date"))
        total_qty += qty
        if d:
            if d < earliest:
                earliest = d
            if d > latest:
                latest = d
    window = (latest - earliest).days
    if window <= 0:
        window = 1
    try:
        return total_qty / float(window)
    except Exception:
        return 0.0


def days_left_for_item(name: str) -> Optional[float]:
    """
    Returns:
      - float days left if computable
      - None if unknown / should not be used for reminders
    Logic:
      1) If expiry_date exists -> compute days from expiry.
      2) Else if consumption rate > 0 -> return qty / rate.
      3) Else -> return None (do NOT remind)
    """
    key = name.lower()
    inv = memory.get("inventory", {}).get(key)
    if not inv:
        return None

    expiry_iso = inv.get("expiry_date")
    if expiry_iso:
        expd = parse_date_iso(expiry_iso)
        if expd is None:
            return None
        return compute_days_left_from_expiry(expd)

    # no expiry: try to estimate from consumption history or defaults
    qty = safe_float(inv.get("qty", 0.0))
    rate = estimate_consumption_rate_per_day(key)

    # NEW: if we don't know the rate (zero) then treat as unknown -> don't remind
    if not rate or rate <= 0:
        return None

    try:
        return qty / rate
    except Exception:
        return None



def compute_days_left_from_expiry(expiry_date: date) -> float:
    """
    Return fractional days left from expiry_date to today().
    """
    td = expiry_date - today()
    return td.total_seconds() / (24.0 * 3600.0)


def days_left_for_item(name: str) -> Optional[float]:
    key = name.lower()
    inv = memory.get("inventory", {}).get(key)
    if not inv:
        return None
    expiry_iso = inv.get("expiry_date")
    if expiry_iso:
        expd = parse_date_iso(expiry_iso)
        if expd is None:
            return None
        return compute_days_left_from_expiry(expd)
    qty = safe_float(inv.get("qty", 0.0))
    rate = estimate_consumption_rate_per_day(key)
    if rate <= 0:
        return float("inf")
    return qty / rate


def am_i_forgetting(current_cart: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    if current_cart is None:
        current_cart = []
    th = memory.get("preferences", {}).get("reminder_threshold_days", REMINDER_THRESHOLD_DAYS)
    suggestions = []
    to_check = set(list(memory.get("inventory", {}).keys()) + list(DEFAULT_CONSUMPTION_PER_DAY.keys()) + DEFAULT_STAPLES)
    for item in to_check:
        item = item.lower()
        days_left = days_left_for_item(item)
        if days_left is None:
            continue
        if item in [c.lower() for c in current_cart]:
            continue
        if days_left <= th:
            if days_left <= 0:
                msg = f"{item.title()} seems finished. Add to cart?"
            elif days_left < 1:
                msg = f"{item.title()} likely less than a day left. Add to cart?"
            else:
                days_rounded = int(math.floor(days_left)) if days_left >= 1 else 0
                msg = f"{item.title()} about {days_rounded} day(s) left. Add to cart?"
            suggestions.append({"item": item, "days_left": days_left, "message": msg})
    suggestions.sort(key=lambda x: x["days_left"])
    return suggestions


# ---------- Pretty helpers for UI ----------
def print_inventory():
    inv = memory.get("inventory", {})
    if not inv:
        return "Inventory empty."
    lines = []
    for item, v in inv.items():
        qty = v.get("qty", 0)
        unit = v.get("unit", "")
        expiry = v.get("expiry_date", None)
        last_updated = v.get("last_updated", None)
        lines.append(f"{item.title():<12} | {qty} {unit:<5} | expiry: {expiry} | updated: {last_updated}")
    return "\n".join(lines)


# initialize by loading disk memory if present
load_memory()


# ---------- New: Recipe requirement estimation & missing-items logic ----------
# sensible default per-recipe consumption (units)
# units should match your inventory units whenever possible
RECIPE_ING_QUANTITIES: Dict[str, tuple] = {
    "milk": (0.25, "L"),        # 250 ml per recipe portion
    "paneer": (0.15, "kg"),
    "egg": (2, "count"),
    "potato": (2, "count"),
    "onion": (1, "count"),
    "tomato": (1, "count"),
    "rice": (0.25, "kg"),       # 250 g
    "dal": (0.1, "kg"),
    "poha": (0.15, "kg"),
    "sugar": (0.05, "kg"),
    "cauliflower": (0.5, "kg"),
    "mustard oil": (0.03, "L"),
    "cardamom powder": (0.005, "kg"),
    "cashews": (0.02, "kg"),
    "almonds": (0.02, "kg"),
    "raisins": (0.02, "kg"),
    "saffron": (0.0005, "g"),
    "ginger": (0.02, "kg"),
    "garlic": (0.01, "kg"),
    "green chilli": (2, "count"),
    "turmeric powder": (0.005, "kg"),
    "red chilli powder": (0.005, "kg"),
    "coriander powder": (0.01, "kg"),
    "cumin powder": (0.005, "kg"),
    "garam masala": (0.003, "kg"),
    "salt": (0.01, "kg"),
    "cilantro": (0.01, "kg"),
    "asafoetida (hing, optional)": (0.001, "kg"),
    # fallback for unknown items will be 1 unit count
}


def _normalize_item_name(name: str) -> str:
    if not isinstance(name, str):
        return str(name).strip().lower()
    return name.strip().lower()


def _normalize_unit(u: Optional[str]) -> str:
    if not u:
        return "unit"
    return str(u).strip().lower()


def _convert_qty(value: float, from_unit: str, to_unit: str) -> Optional[float]:
    """
    Basic unit conversions:
    - kg <-> g
    - L <-> ml
    - if both are 'count' or same unit -> pass through
    Returns converted value in to_unit, or None if conversion not supported.
    """
    fu = _normalize_unit(from_unit)
    tu = _normalize_unit(to_unit)
    if fu == tu:
        return value
    # kg <-> g
    if fu == "kg" and tu in ("g", "gm", "gram", "grams"):
        return value * 1000.0
    if fu in ("g", "gm", "gram", "grams") and tu == "kg":
        return value / 1000.0
    # L <-> ml
    if fu == "l" and tu in ("ml", "milliliter", "millilitre"):
        return value * 1000.0
    if fu in ("ml", "milliliter", "millilitre") and tu == "l":
        return value / 1000.0
    # simple plural handling for 'count'
    if fu in ("count", "unit") and tu in ("count", "unit"):
        return value
    # no conversion available
    return None


def aggregate_plan_requirements(parsed_plan: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    """
    Convert a parsed plan (list of day dicts) to aggregated required quantities.
    Returns { item: {"qty": total_qty, "unit": unit} } using RECIPE_ING_QUANTITIES defaults.
    Unknown items default to 1 'count' per appearance.
    """
    reqs: Dict[str, Dict[str, float]] = {}
    for day in parsed_plan:
        # combine uses + extra
        items: List[str] = []
        if isinstance(day.get("uses"), list):
            items += day.get("uses", [])
        if isinstance(day.get("extra"), list):
            items += day.get("extra", [])
        # count each item once per recipe
        for it in items:
            item = _normalize_item_name(it)
            default = RECIPE_ING_QUANTITIES.get(item)
            if default:
                qty, unit = default
            else:
                qty, unit = (1.0, "count")
            if item not in reqs:
                reqs[item] = {"qty": 0.0, "unit": unit}
            reqs[item]["qty"] += qty
    # round quantities for neatness
    for k in reqs:
        reqs[k]["qty"] = float(round(reqs[k]["qty"], 4))
    return reqs


def compute_missing_items_from_plan(parsed_plan: List[Dict[str, Any]], inventory_snapshot: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Compare aggregated required items with inventory_snapshot (defaults to memory inventory).
    inventory_snapshot expected shape: { item: {"qty": float, "unit": str, "expiry_date": "YYYY-MM-DD" or None} }
    Returns list of missing items: [{ "item":..., "required":..., "have":..., "unit":..., "to_buy":... }, ...]
    """
    if inventory_snapshot is None:
        inventory_snapshot = memory.get("inventory", {})

    reqs = aggregate_plan_requirements(parsed_plan)
    missing: List[Dict[str, Any]] = []

    for item, need in reqs.items():
        need_qty = float(need["qty"])
        need_unit = _normalize_unit(need["unit"])
        inv = inventory_snapshot.get(item, {})
        have_qty = safe_float(inv.get("qty", 0.0))
        have_unit = _normalize_unit(inv.get("unit", need_unit))

        # Try to convert have_qty to need_unit if units differ
        if have_qty > 0 and have_unit != need_unit:
            converted = _convert_qty(have_qty, have_unit, need_unit)
            if converted is not None:
                have_qty_converted = converted
            else:
                # if cannot convert, treat have_qty as 0 for comparison (safer)
                have_qty_converted = 0.0
        else:
            have_qty_converted = have_qty

        if have_qty_converted >= need_qty:
            continue  # enough
        else:
            to_buy = max(0.0, need_qty - have_qty_converted)
            # Round to friendly amounts (e.g., 2 decimals)
            to_buy = float(math.ceil(to_buy * 100) / 100.0) if to_buy >= 0.01 else to_buy
            missing.append({
                "item": item,
                "required": need_qty,
                "have": have_qty_converted,
                "have_unit": have_unit,
                "unit": need_unit,
                "to_buy": to_buy
            })

    # Sort missing by descending to_buy for prioritization
    missing.sort(key=lambda x: x["to_buy"], reverse=True)
    return missing


def get_inventory_snapshot() -> Dict[str, Any]:
    """Return a shallow copy of current inventory."""
    return dict(memory.get("inventory", {}))


# Developer-specified uploaded file path (from conversation history).
# Use this path as a file URL in environments that transform local paths to served URLs.
FILE_URL = "/mnt/data/5cc44563-f985-4171-8ebc-624fe5578e46.png"

def get_uploaded_file_url() -> str:
    """
    Return the known uploaded-file path. In hosted environments (Kaggle/Colab),
    this path may be transformed to an HTTP-accessible URL by the platform.
    """
    return FILE_URL
