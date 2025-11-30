
from dotenv import load_dotenv
load_dotenv()

import os
import json
import re
import traceback
from typing import List, Dict, Any, Optional, Tuple

# HTTP requests only used for optional diagnostic / REST fallback removal option;
# for your current working SDK we do not use REST fallback.
import requests  # kept for completeness / diagnostics if needed

# Attempt to import Google Generative AI SDK (gemini)
try:
    import google.generativeai as genai  # type: ignore
except Exception:
    genai = None  # type: ignore

# Path to the uploaded demo GIF/screenshot (from your session history).
# Environment or UI code can transform this local path into a served URL.
SAMPLE_HERO_PATH = "/mnt/data/5cc44563-f985-4171-8ebc-624fe5578e46.png"


# ------------------------------
# Low-level helpers
# ------------------------------
def _ensure_genai_configured() -> bool:
    """
    Ensure genai is configured with GOOGLE_API_KEY if available.
    Returns True if configuration likely succeeded.
    """
    if genai is None:
        return False
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return False
    try:
        # safe to call multiple times
        genai.configure(api_key=api_key)
        return True
    except Exception:
        return False


def _extract_json_block(text: str) -> Optional[Any]:
    """
    Find and repair a JSON array/object in noisy model text.
    Returns parsed Python object on success or None.
    """
    if not isinstance(text, str):
        return None

    # find first {...} or [...] block (greedy)
    m = re.search(r"(\{(?:.|\n)*\}|\[(?:.|\n)*\])", text, flags=re.DOTALL)
    if not m:
        return None
    blk = m.group(1)

    # try direct parse
    try:
        return json.loads(blk)
    except Exception:
        pass

    fixed = blk

    # replace single quotes with double quotes if appears JSON-like
    if "'" in fixed and '"' not in fixed:
        fixed = fixed.replace("'", '"')

    # remove trailing commas
    fixed = re.sub(r",\s*}", "}", fixed)
    fixed = re.sub(r",\s*]", "]", fixed)

    # remove JS-style comments
    fixed = re.sub(r"//.*?$", "", fixed, flags=re.MULTILINE)
    fixed = re.sub(r"/\*.*?\*/", "", fixed, flags=re.DOTALL)

    # naive brace balancing
    opens = fixed.count("{") + fixed.count("[")
    closes = fixed.count("}") + fixed.count("]")
    if opens > closes:
        fixed = fixed + ("]" * (opens - closes))

    try:
        return json.loads(fixed)
    except Exception:
        return None


def parse_plan_text_to_json(plan_text: str, expected_days: int = 3) -> List[Dict[str, Any]]:
    """
    Best-effort parser: transform human-readable plan text into structured data.
    Returns list of day dicts:
      [{ "day": 1, "dish": "...", "uses": [...], "extra": [...], "steps": [...] }, ...]
    """
    if not plan_text or not isinstance(plan_text, str):
        return []

    text = plan_text.strip()

    # Split on "Day N" markers
    parts = re.split(r"(?i)\bDay\s*\d+\b[:\s]*", text)
    markers = re.findall(r"(?i)\bDay\s*\d+\b", text)

    blocks = []
    if len(markers) >= 1 and len(parts) >= 2:
        for i, blk in enumerate(parts[1:], start=1):
            blocks.append((i, blk.strip()))
    else:
        chunks = [c.strip() for c in re.split(r"\n\s*\n", text) if c.strip()]
        for i, c in enumerate(chunks[:expected_days], start=1):
            blocks.append((i, c))

    parsed = []
    for day_index, block in blocks[:expected_days]:
        dish = ""
        uses = []
        extra = []
        steps = []

        m_dish = re.search(r"(?i)\bDish\s*[:\-]\s*(.+)", block)
        if m_dish:
            dish = m_dish.group(1).strip()
        else:
            first_line = block.splitlines()[0].strip() if block.splitlines() else ""
            if first_line and len(first_line.split()) <= 8:
                dish = first_line

        m_uses = re.search(r"(?i)\bUses\s*(?:expiring)?\s*[:\-]\s*(.+)", block)
        if m_uses:
            uses = [u.strip().rstrip(".") for u in re.split(r"[,\n;\/]+", m_uses.group(1)) if u.strip()]

        m_extra = re.search(r"(?i)\bExtra ingredients\s*[:\-]\s*(.+)", block)
        if m_extra:
            extra = [u.strip().rstrip(".") for u in re.split(r"[,\n;\/]+", m_extra.group(1)) if u.strip()]

        steps_found = re.findall(r"\d+\.\s*(.+)", block)
        if steps_found:
            steps = [s.strip().rstrip(".") for s in steps_found][:3]
        else:
            m_steps = re.search(r"(?i)\bSteps\s*[:\-]\s*(.+)", block, flags=re.DOTALL)
            if m_steps:
                candidate = m_steps.group(1).strip()
                pieces = re.split(r"\n|(?<=\.)\s+", candidate)
                steps = [p.strip().rstrip(".") for p in pieces if p.strip()][:3]

        parsed.append({
            "day": day_index,
            "dish": dish,
            "uses": uses,
            "extra": extra,
            "steps": steps
        })

    return parsed


# ------------------------------
# SDK call helper (tailored to your installed SDK v0.8.5)
# ------------------------------
def _call_genai_model(prompt: str, model_name: str = "gemini-2.5-flash",
                      temperature: float = 0.2, max_output_tokens: int = 900) -> Tuple[bool, str]:
    """
    SDK-only: instantiate genai.GenerativeModel(model_name) and call generate_content(prompt).
    Returns (True, generated_text) or (False, error_message).
    """
    if genai is None:
        return False, "Gemini SDK not installed."

    # Ensure configured if possible (doesn't hurt to call)
    _ensure_genai_configured()

    try:
        model = genai.GenerativeModel(model_name=model_name)
    except Exception as e:
        return False, f"Could not instantiate GenerativeModel: {e}"

    try:
        # IMPORTANT: call generate_content(prompt) WITHOUT unsupported kwargs like `temperature`
        resp = model.generate_content(prompt)
        text = getattr(resp, "text", None) or str(resp)
        return True, text
    except Exception as e:
        return False, f"generate_content failed: {e}"


# ------------------------------
# Public API: generate meal plan (JSON) + chat reply
# ------------------------------
def generate_with_gemini_json(expiring_items: List[str], days: int = 3,
                              model_name: str = "gemini-2.5-flash",
                              temperature: float = 0.2) -> Dict[str, Any]:
    """
    Request Gemini to return strict JSON for a meal plan.
    Returns {'raw': <text>, 'parsed': <list>} on success or {'error': msg, 'raw': <text?>} on failure.
    """
    prompt = f"""You are an expert Indian household meal planner.
Create a {days}-day meal plan that MUST use the expiring items first when available.

Expiring items: {', '.join(expiring_items) if expiring_items else 'none'}

Return ONLY valid JSON: an array of day objects with this schema:
[
  {{
    "day": 1,
    "dish": "Aloo Gobi",
    "uses": ["paneer","milk"],
    "extra": ["potato","onion"],
    "steps": ["step 1","step 2","step 3"]
  }},
  ...
]

Do not include explanations, markdown, or any text outside the JSON array.
Use lowercase for ingredient names where possible.
"""

    ok, text_or_err = _call_genai_model(prompt, model_name=model_name, temperature=temperature, max_output_tokens=900)
    if not ok:
        # return error (caller can fallback)
        return {"error": text_or_err}

    text = text_or_err

    # Try direct JSON
    try:
        parsed = json.loads(text)
        return {"raw": text, "parsed": parsed}
    except Exception:
        pass

    # Try extract JSON block
    extracted = _extract_json_block(text)
    if extracted is not None:
        return {"raw": text, "parsed": extracted}

    # Last resort: parse human text into structured plan
    structured = parse_plan_text_to_json(text, expected_days=days)
    if structured:
        return {"raw": text, "parsed": structured}

    return {"error": "Model did not return valid JSON or parseable plan.", "raw": text}


def generate_chat_reply(user_text: str, model_name: str = "gemini-2.5-flash", temperature: float = 0.3) -> str:
    """
    Simple chat wrapper around Gemini. Returns model text or an error string.
    """
    system_instruction = (
        "You are SmartGrocer, a helpful Indian household assistant. Be concise and practical. "
        "If the user asks about inventory, ask them to use the format: 'item, qty, unit, expiry'. "
        "If asked for recipes, prefer simple Indian dishes for a household of 2-4. "
    )
    prompt = f"{system_instruction}\nUser: {user_text}\nAssistant:"

    ok, text_or_err = _call_genai_model(prompt, model_name=model_name, temperature=temperature, max_output_tokens=400)
    if not ok:
        return f"Error generating chat reply: {text_or_err}"
    return text_or_err


# ------------------------------
# Local deterministic fallback planner (for demos)
# ------------------------------
INDIAN_RECIPES = {
    "paneer_bhurji": {"uses": ["paneer", "onion", "tomato"], "steps": ["Crumble paneer", "Saute onions & tomatoes", "Mix & serve"]},
    "milk_poha": {"uses": ["milk", "poha", "sugar"], "steps": ["Soak poha", "Warm milk", "Mix & serve"]},
    "aloo_sabzi": {"uses": ["potato", "onion", "tomato"], "steps": ["Boil potatoes", "Saute masala", "Mix & serve"]},
    "dal_tadka": {"uses": ["dal", "onion", "tomato"], "steps": ["Wash dal", "Cook dal", "Tadka & serve"]}
}


def mock_llm_plan(expiring_items: List[str], days: int = 3) -> List[Dict[str, Any]]:
    """
    Deterministic local planner that prefers recipes using expiring items.
    """
    plan = []
    used_ings = set()

    for d in range(days):
        chosen_name = None
        chosen_meta = None
        # pick a recipe using an expiring ingredient not yet used
        for rname, meta in INDIAN_RECIPES.items():
            for ing in meta["uses"]:
                if ing in expiring_items and ing not in used_ings:
                    chosen_name = rname
                    chosen_meta = meta
                    break
            if chosen_name:
                break

        if not chosen_name:
            # choose first recipe not already used in plan for determinism
            for rname in INDIAN_RECIPES.keys():
                if rname not in [p.get("dish") for p in plan]:
                    chosen_name = rname
                    chosen_meta = INDIAN_RECIPES[rname]
                    break
            if not chosen_name:
                chosen_name = list(INDIAN_RECIPES.keys())[0]
                chosen_meta = INDIAN_RECIPES[chosen_name]

        uses = [ing for ing in chosen_meta["uses"] if ing in expiring_items]
        if not uses:
            uses = chosen_meta["uses"][:2]

        plan.append({
            "day": d + 1,
            "dish": chosen_name.replace("_", " ").title(),
            "uses": uses,
            "extra": [i for i in chosen_meta["uses"] if i not in uses],
            "steps": chosen_meta["steps"][:3]
        })
        used_ings.update(uses)

    return plan


# ------------------------------
# CLI convenience
# ------------------------------
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="planner.py CLI - generate a meal plan (Gemini or fallback)")
    parser.add_argument("--days", type=int, default=3, help="Number of days in plan")
    parser.add_argument("--items", type=str, default="", help="Comma-separated expiring items (e.g. milk,paneer)")
    args = parser.parse_args()

    items = [i.strip().lower() for i in args.items.split(",") if i.strip()] if args.items else []
    out = generate_with_gemini_json(items, days=args.days)
    if out.get("error"):
        fallback = mock_llm_plan(items, days=args.days)
        print(json.dumps(fallback, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(out.get("parsed", []), ensure_ascii=False, indent=2))
