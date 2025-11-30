# app.py — cleaned & fixed (buttons under input, no duplicates)
from dotenv import load_dotenv
load_dotenv()

import streamlit as st
from datetime import datetime
import json
from typing import List, Dict, Any
import os

import agent_logic
from planner import generate_chat_reply, generate_with_gemini_json

st.set_page_config(page_title="SmartGrocer", page_icon="🛒", layout="centered")

# Developer-provided uploaded file path (kept for environments that want to serve it)
DEMO_IMG = "/mnt/data/9871b25d-bd9b-4f30-b7d8-d6f40a313650.png"

# --------------------------
# Styling (dark theme friendly)
# --------------------------
st.markdown(
    """
    <style>
    .stApp { background-color: #0b1220; color: #e6eef8; }

    .user-msg {
        background-color: #16a34a;
        color: white;
        padding: 12px 16px;
        border-radius: 16px;
        margin: 8px 0;
        max-width: 78%;
        float: right;
        clear: both;
        font-size: 15px;
        line-height: 1.4;
    }
    .bot-msg {
        background-color: #1f2937;
        color: #e6eef8;
        padding: 12px 16px;
        border-radius: 16px;
        margin: 8px 0;
        max-width: 78%;
        float: left;
        clear: both;
        font-size: 15px;
        line-height: 1.4;
        border: 1px solid rgba(255,255,255,0.03);
    }
    .timestamp {
        font-size: 11px;
        color: #94a3b8;
        margin: 6px 0 14px 0;
        clear: both;
    }
    .chat-container { max-width: 920px; margin: 18px auto; padding-top: 8px; }
    .header-title { font-size: 26px; font-weight: 700; color: #fff; margin-bottom: 6px; }
    .header-sub { color: #9aa7bf; margin-bottom: 12px; }

    .plan-card { background:#071827; border:1px solid #112233; padding:12px; border-radius:10px; margin:10px 0; color: #e6eef8; }
    .plan-day { color:#93c5fd; font-weight:700; margin-bottom:6px; }
    .plan-uses { color:#c7f9d2; font-size:14px; margin-bottom:6px; }
    .plan-step { color:#d1d5db; font-size:14px; margin:3px 0; }

    .format-info { background: #082233; border-left: 4px solid #2563eb; padding: 10px 12px; border-radius: 8px; color: #cfe3ff; margin-bottom: 12px; }

    /* Sticky inventory preview at top (small) */
    .sticky-inv {
        position: -webkit-sticky;
        position: sticky;
        top: 0;
        z-index: 999;
        background-color: #071827;
        padding: 6px 10px;
        border-bottom: 1px solid rgba(255,255,255,0.04);
        margin-bottom: 10px;
    }

    /* button styling tweaks */
    .stButton>button {
        padding: 10px 14px;
        border-radius: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------
# Session state defaults
# --------------------------
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "text": (
                "Hi — I'm SmartGrocer. I can track your inventory, remind about expiring items, and plan meals.\n\n"
                "To add an item to inventory use the format: `item, quantity, unit, expiry-date` (see examples below)."
            ),
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    ]

if "latest_plan" not in st.session_state:
    st.session_state.latest_plan = None

# --------------------------
# Helper: show plan and missing (defined BEFORE use)
# --------------------------
def _show_plan_and_missing(parsed_plan: List[Dict[str, Any]]):
    """
    Renders the parsed_plan as cards (appends assistant messages) and computes missing items.
    """
    # Render each day as a plan-card assistant message (HTML string)
    for day in parsed_plan:
        day_header = f"<div class='plan-card'><div class='plan-day'>Day {day.get('day')}: {day.get('dish')}</div>"
        uses = day.get('uses', []) or []
        extra = day.get('extra', []) or []
        uses_html = "<div class='plan-uses'><strong>Uses:</strong> " + ", ".join([u.title() for u in uses]) + "</div>"
        extra_html = "<div class='plan-uses'><strong>Extras:</strong> " + (", ".join([e.title() for e in extra]) if extra else "—") + "</div>"
        steps_html = "<div>"
        for idx, s in enumerate(day.get('steps', []), start=1):
            steps_html += f"<div class='plan-step'>{idx}. {s}</div>"
        steps_html += "</div></div>"
        st.session_state.messages.append({
            "role": "assistant",
            "text": day_header + uses_html + extra_html + steps_html,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

    # Compute missing items
    inv_snapshot = agent_logic.get_inventory_snapshot()
    missing = agent_logic.compute_missing_items_from_plan(parsed_plan, inv_snapshot)
    if not missing:
        st.session_state.messages.append({
            "role": "assistant",
            "text": "You have everything required for this plan (based on estimated quantities).",
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    else:
        lines = []
        for m in missing:
            lines.append(f"- {m['item'].title()}: need {m['required']} {m['unit']}, have {m['have']} → buy {m['to_buy']} {m['unit']}")
        st.session_state.messages.append({
            "role": "assistant",
            "text": "You're missing the following items to make the meals:\n" + "\n".join(lines),
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

# --------------------------
# UI header + input format help
# --------------------------
st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
st.markdown("<div class='header-title'>🛒 SmartGrocer — Your Household Assistant</div>", unsafe_allow_html=True)
st.markdown("<div class='header-sub'>Track inventory • Reduce waste • Plan meals — India-friendly</div>", unsafe_allow_html=True)

st.markdown(
    """
    <div class="format-info">
    <strong>How to add items to inventory</strong><br>
    Use this exact CSV format (comma-separated):<br>
    <code>item, quantity, unit, expiry-date</code><br><br>
    Examples:<br>
    • <code>milk, 1, L, 2025-11-25</code><br>
    • <code>egg, 6, count, 2025-11-23</code><br>
    • <code>atta, 2, kg, none</code>  (use <code>none</code> if no expiry)
    </div>
    """,
    unsafe_allow_html=True,
)

# --------------------------
# Sticky inventory preview (top) - kept, but buttons removed from top
# --------------------------
inv_text = agent_logic.print_inventory()
st.markdown(f"<div class='sticky-inv'><strong>Inventory preview:</strong><br><pre style='color:#cfe3ff'>{inv_text or 'Inventory empty.'}</pre></div>", unsafe_allow_html=True)

# show demo image (optional)
try:
    if os.path.exists(DEMO_IMG):
        st.image(DEMO_IMG, use_container_width=False, width=120)
except Exception:
    pass

# --------------------------
# Helper functions for messages
# --------------------------
def add_message(role: str, text: str):
    st.session_state.messages.append({"role": role, "text": text, "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})

def render_messages():
    for m in st.session_state.messages:
        cls = "user-msg" if m["role"] == "user" else "bot-msg"
        st.markdown(f"<div class='{cls}'>{m['text'].replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='timestamp'>{m['time']}</div>", unsafe_allow_html=True)

# --------------------------
# Render chat area
# --------------------------
render_messages()

# --------------------------
# Input + horizontal quick-action buttons (below input)
# --------------------------

# Input form
with st.container():
    with st.form("input_form", clear_on_submit=True):
        user_input = st.text_input(
            "Type your message or add item (item, qty, unit, expiry YYYY-MM-DD)",
            placeholder="e.g. milk, 1, L, 2025-11-25",
            key="user_input_field"
        )
        submitted = st.form_submit_button("Send", key="btn_send_input")
        if submitted and user_input:
            add_message("user", user_input)

            # Inventory add detection (CSV)
            if "," in user_input and len(user_input.split(",")) >= 2:
                parts = [p.strip() for p in user_input.split(",")]
                name = parts[0]
                qty = parts[1] if len(parts) > 1 else "1"
                unit = parts[2] if len(parts) > 2 else None
                expiry = parts[3] if len(parts) > 3 else None
                try:
                    added = agent_logic.add_manual_purchase(name, qty, unit, expiry)
                    add_message("assistant", f"Added: {name.title()}, {added.get('qty')} {added.get('unit')}, expires {added.get('expiry_date')}. What else?")
                except Exception as e:
                    add_message("assistant", f"Failed to add item: {e}")
            else:
                lower = user_input.lower()
                if "forget" in lower:
                    suggestions = agent_logic.am_i_forgetting([])
                    if not suggestions:
                        add_message("assistant", "You're not forgetting anything important.")
                    else:
                        text = "\n".join([f"- {s['message']}" for s in suggestions])
                        add_message("assistant", "Here are some reminders:\n" + text)
                elif "inventory" in lower or "show inventory" in lower:
                    add_message("assistant", agent_logic.print_inventory())
                elif "meal" in lower or "plan" in lower:
                    add_message("assistant", "Generating a meal plan — you can also use the buttons below.")
                    expiring = [s["item"] for s in agent_logic.am_i_forgetting([])]
                    out = generate_with_gemini_json(expiring, days=3, temperature=0.0)
                    if out.get("error"):
                        fallback = agent_logic.mock_llm_plan(expiring, days=3) if hasattr(agent_logic, "mock_llm_plan") else []
                        st.session_state.latest_plan = fallback
                        add_message("assistant", "Couldn't fetch structured Gemini plan — using fallback plan.")
                        _show_plan_and_missing(fallback)
                    else:
                        parsed = out.get("parsed", [])
                        st.session_state.latest_plan = parsed
                        add_message("assistant", "Here's a 3-day meal plan I generated:")
                        _show_plan_and_missing(parsed)
                else:
                    reply = generate_chat_reply(user_input)
                    add_message("assistant", reply)

    # horizontal buttons row — unique keys
    btn_cols = st.columns([1,1,1], gap="medium")
    with btn_cols[0]:
        if st.button("🔔 Am I forgetting something?", key="btn_forgetting_input"):
            add_message("user", "Am I forgetting something?")
            suggestions = agent_logic.am_i_forgetting([])
            if not suggestions:
                add_message("assistant", "You're not missing anything urgent 👍")
            else:
                text = "\n".join([f"- {s['message']}" for s in suggestions])
                add_message("assistant", "Here are some reminders:\n" + text)

    with btn_cols[1]:
        if st.button("📋 Show Inventory", key="btn_show_inventory_input"):
            inv_text = agent_logic.print_inventory()
            add_message("assistant", f"**Your Inventory:**\n{inv_text}")

    with btn_cols[2]:
        if st.button("🍽️ Generate 3-Day Meal Plan", key="btn_generate_plan_input"):
            add_message("user", "Generate 3-day meal plan")
            with st.spinner("Generating meal plan..."):
                expiring = [s["item"] for s in agent_logic.am_i_forgetting([])]
                out = generate_with_gemini_json(expiring, days=3, temperature=0.0)
                if out.get("error"):
                    fallback = agent_logic.mock_llm_plan(expiring, days=3) if hasattr(agent_logic, "mock_llm_plan") else []
                    st.session_state.latest_plan = fallback
                    add_message("assistant", "Couldn't fetch structured Gemini plan — using fallback plan.")
                    _show_plan_and_missing(fallback)
                else:
                    parsed = out.get("parsed", [])
                    st.session_state.latest_plan = parsed
                    add_message("assistant", "Here's a 3-day meal plan I generated:")
                    _show_plan_and_missing(parsed)

# If plan exists show "What am I missing?" button (unique key)
if st.session_state.latest_plan:
    if st.button("🧾 What items am I missing for this plan?", key="btn_missing_for_plan"):
        inv_snapshot = agent_logic.get_inventory_snapshot()
        missing = agent_logic.compute_missing_items_from_plan(st.session_state.latest_plan, inv_snapshot)
        if not missing:
            add_message("assistant", "You have everything required for this plan (based on estimated quantities).")
        else:
            lines = []
            for m in missing:
                lines.append(f"- {m['item'].title()}: need {m['required']} {m['unit']}, have {m['have']} → buy {m['to_buy']} {m['unit']}")
            add_message("assistant", "You're missing the following items to make the meals:\n" + "\n".join(lines))

# Persist memory safely
try:
    agent_logic.save_memory()
except Exception:
    pass

st.markdown("</div>", unsafe_allow_html=True)
