# SmartGrocer 🛒
**An AI-powered grocery tracking and meal planning assistant for Indian households**

---

## The Problem

Households frequently buy groceries they already have, forget what's running low, or let perishables expire — because tracking it all manually is tedious and error-prone. The mental load compounds when you also need to answer:

- *What should I buy today?*
- *What's about to go bad?*
- *What can I cook with what I already have?*

SmartGrocer solves exactly this: a conversational assistant that reduces waste, saves money, and simplifies everyday cooking decisions.

---

## Features

- **Inventory tracking** — Add items with quantities and expiry dates using plain language
- **Expiry detection** — Automatically flags items close to spoiling
- **Smart reminders** — Ask "Am I forgetting something?" and get a contextual answer
- **AI meal planning** — Generates structured 3-day Indian meal plans using your available ingredients
- **Missing ingredient detection** — Identifies what you need to complete a recipe
- **Chat-style interface** — Natural conversation powered by Gemini 2.5 Flash

---

## Why an Agent?

Traditional grocery apps rely on rigid forms and manual entry. Grocery management is *dynamic* — quantities change, plans shift, and context matters. An LLM-powered agent handles this naturally:

- Understands free-form input like *"add 1L milk expiring tomorrow"*
- Reasons across inventory, expiry dates, and consumption history
- Asks clarifying questions when information is incomplete
- Adapts responses based on what you actually have

The result is a real assistant, not just another dashboard.

---

## Architecture

SmartGrocer uses a **multi-agent design** with four specialized components:

| Agent | Responsibility |
|---|---|
| **Inventory Agent** | Tracks items, quantities, and expiry |
| **Reminder Agent** | Detects low stock and approaching expiry |
| **Meal Planner Agent** | Generates 3-day meal plans from available ingredients |
| **Chat Agent** | Handles general queries and natural conversation |

**Stack:** Python · Streamlit · Google Gemini 2.5 Flash · JSON-structured generation · Local `memory.json` persistence

---

## Repository Structure

```
smartgrocer/
├── app.py            # Streamlit chat UI with quick-action buttons
├── planner.py        # Gemini chat integration and meal plan generation
├── agent_logic.py    # Inventory logic, expiry handling, reminders, and memory
├── memory.json       # Persistent inventory storage
├── requirements.txt  # Dependencies
└── README.md
```

---

## Getting Started

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/smartgrocer.git
cd smartgrocer
```

### 2. Create and activate a virtual environment
```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Add your Gemini API key
Create a `.env` file in the project root:
```
GOOGLE_API_KEY=your_key_here
```
Get your key at [Google AI Studio](https://aistudio.google.com/).

### 5. Run the app
```bash
streamlit run app.py
```

> **Tip:** If the chat bubble doesn't appear after sending a message, click Send once more — this is a known Streamlit quirk.

---

## Live Demo

Try it without installing anything: [smartgrocer.streamlit.app](https://sctml01-mtp9lq3onlfd8wkmjsgttw.streamlit.app/)