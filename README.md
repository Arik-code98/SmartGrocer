# 🛒 SmartGrocer – AI-Powered Grocery & Meal Planning Assistant

SmartGrocer is an intelligent household assistant that helps you **track your inventory**, **get reminders for expiring items**, and **generate AI-powered meal plans** using Google Gemini.  
The project includes a **Streamlit UI** that feels like a chat app, making grocery management effortless.

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
| `README.md` | Project documentation (this file) |

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
After sending the message if the chat bubble doesn't appear click the send button again.