# 🛒 SmartGrocer – AI-Powered Grocery & Meal Planning Assistant

SmartGrocer is an intelligent household assistant that helps you **track your inventory**, **get reminders for expiring items**, and **generate AI-powered meal plans** using Google Gemini.  
The project includes a **Streamlit UI** that feels like a chat app, making grocery management effortless.

⚠️**Problem Statement**

Households frequently buy groceries they already have, forget items they need, or allow perishables to expire because keeping track manually is tedious and error-prone. This leads to wasted money, wasted food, and unnecessary stress—especially in busy Indian households where ingredients vary, quantities change often, and meal planning is part of everyday life.

The problem becomes even more complex when trying to decide:

- What should I buy today?

- What items are running low?

- What can I cook with what I already have?

SmartGrocer aims to solve exactly this: a personal grocery-tracking and meal-planning assistant that reduces waste, saves money, and simplifies everyday cooking decisions.

✅**Why Agents?**

Traditional apps rely on manual data entry and rigid workflows. But grocery management is dynamic, conversational, and full of exceptions. Agents—especially LLM-powered ones—are perfect because they can:

- Interpret free-form human language ("add 1L milk expiring tomorrow")

- Reason about inventory, expiry, and consumption

- Generate meal plans based on ingredients

- Ask for missing information automatically

- Learn from user behavior and adapt

- Agents transform the experience into a natural conversation, not a form-filling task.

This is why SmartGrocer works exceptionally well as an agent-based system: it becomes a real helper, not just a dashboard.

⚙️**What I Created — Architecture Overview**

SmartGrocer is a multi-agent AI assistant built with:

- Inventory Agent – Tracks items, quantities, consumption, and expiry.

- Reminder Agent – Detects items close to expiry or running out and notifies the user.

- Meal Planner Agent – Generates structured 3-day meal plans based on available items.

- Chat Agent – Handles general queries, small talk, and natural conversation.

`System Structure`

1. User Interface: A fully custom Streamlit chat UI with clean design, buttons, and natural chat flow.

2. Backend Agents: Python agents that store memory, compute expiry, identify missing items, and generate plans.

3. LLM Integration: *Gemini 2.5 Flash* + *JSON*-structured generation for meal plans.

4. Local Memory: A persistent memory.json that stores inventory and usage history.

Together, these components allow the agent to understand, reason, plan, and respond intelligently.

---

## 🔍 Project Overview

- **Core Functions**:
  - Add and track grocery inventory  
  - Automatic expiry detection  
  - Smart reminders ("Am I forgetting something?")  
  - AI-generated **3-day Indian meal plans**  
  - Missing-ingredient detection  
  - Chat-style interface powered by Gemini  

- **Tech Used**:
  - Python  
  - Streamlit  
  - Google Gemini 2.5 Flash  
  - dotenv for API key security  

---

## 📁 Repository Structure

| File | Description |
|------|-------------|
| `app.py` | Streamlit UI with chat interface and quick-action buttons |
| `planner.py` | Handles Gemini chat + structured meal planning |
| `agent_logic.py` | Inventory logic, expiry handling, reminders, and memory storage |
| `memory.json` | Persistent storage of inventory |
| `requirements.txt` | Required packages |
| `README.md` | Project documentation |

---

## 📦 Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/smartgrocer.git
   cd smartgrocer

---

2. **Create & activate virtual environment**
    ```bash
    python -m venv .venv
    .venv\Scripts\activate 

---

3. **Install dependencies**
    ```bash
    pip install -r requirements.txt

---

4. **Add your Gemini API key**
    Create a .env file:
    ```bash
    GOOGLE_API_KEY=your_key_here

---

5. **Run the app**
    ```bash
    streamlit run app.py

---

## 💡 Small Tip
If the chat bubble doesn't appear after sending a message, click Send again.