<p align="center">
  <img src="https://em-content.zobj.net/source/apple/391/classical-building_1f3db-fe0f.png" width="80" />
</p>

<h1 align="center">ManasGriha</h1>
<p align="center"><i>मनस्गृह — The House of the Mind</i></p>

<p align="center">
  <b>An AI-powered council of legendary thinkers, debating your life's questions in real time.</b>
</p>

<p align="center">
  <a href="#-quick-start"><img src="https://img.shields.io/badge/⚡_Quick_Start-3_Commands-7c5cfc?style=for-the-badge" /></a>
  <a href="#-the-council"><img src="https://img.shields.io/badge/🏛️_Council-8_Personas-D4A574?style=for-the-badge" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-34d399?style=for-the-badge" /></a>
</p>

---

## 💡 What is ManasGriha?

ManasGriha is a **WhatsApp-style group chat** where 8 legendary minds — from Marcus Aurelius to Elon Musk — discuss your questions, challenge each other's views, and help you think more clearly.

**Not a chatbot. A council.**

Send a message and watch Stoic emperors debate tech moguls. Ask for career advice and see military strategists argue with philosophers. Every conversation is a collision of worldviews, designed to give you *clarity through contrast*.

You can also pull any persona aside for a **private 1-on-1 conversation** when you need their undivided attention.

### ✨ Key Features

| Feature | Description |
|---------|-------------|
| 🏛️ **Group Debate** | All 8 personas respond to your message, then debate each other in rounds |
| 💬 **1-on-1 Chats** | Private conversations with any individual persona |
| ↩️ **Reply-to** | Reply to specific messages — personas see the thread context |
| ⚡ **Real-time Streaming** | Responses stream in one by one via SSE (Server-Sent Events) |
| 🔑 **BYOK** | Bring Your Own Key — users provide their own Groq API key |
| 🌙 **Dark Glassmorphic UI** | Premium dark theme with blur, gradients, and macOS aesthetics |
| 📱 **Responsive** | Works on desktop and mobile with collapsible sidebar |
| 🚀 **Single Deploy** | One FastAPI service serves both API and frontend — deploy anywhere |

---

## 🏛️ The Council

| Persona | Domain | Style |
|---------|--------|-------|
| 👑 **Marcus Aurelius** | Stoic Philosophy | Calm, measured, journal-like reflections |
| 🦉 **Socrates** | Dialectic Inquiry | Questions everything, draws out your own answers |
| ♟️ **Chanakya** | Strategy & Statecraft | Ruthlessly pragmatic, power dynamics |
| 🎭 **Robert Greene** | Power & Human Nature | Pattern recognition, historical parallels |
| ⚡ **Nikola Tesla** | Innovation & Science | First-principles thinking, systems design |
| 💪 **David Goggins** | Mental Toughness | No-excuse discipline, raw honesty |
| ⚔️ **Napoleon Bonaparte** | Strategic Leadership | Decisive action, operational planning |
| 🚀 **Elon Musk** | Risk & Innovation | Data-driven bets, contrarian thinking |

---

## ⚡ Quick Start

### Prerequisites

- **Python 3.11+**
- **Groq API Key** — free at [console.groq.com/keys](https://console.groq.com/keys)

### 3-Command Setup

```bash
# 1. Clone and enter the project
git clone https://github.com/LeoPanthera07/ManasGriha.git
cd ManasGriha

# 2. Install dependencies
cd backend
python3 -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Run
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Open **[http://localhost:8000](http://localhost:8000)** → enter your Groq API key → start chatting.

> **No Node.js, no build step, no `.env` file needed.** The frontend is pure HTML/CSS/JS served by FastAPI.

---

## 🗂️ Project Structure

```
ManasGriha/
├── backend/
│   ├── main.py              # FastAPI app — routes, SSE streaming, static files
│   ├── chat_handler.py      # Group response generator, debate logic
│   ├── personas.py          # All 8 persona definitions & system prompts
│   ├── models.py            # SQLAlchemy models (conversations, messages)
│   ├── database.py          # Database engine & session factory
│   └── requirements.txt     # Python dependencies
│
├── frontend/
│   ├── index.html           # Single-page app entry
│   └── assets/
│       ├── styles/
│       │   └── index.css    # Full design system — glassmorphism, tokens
│       └── js/
│           └── app.js       # Chat logic, SSE client, mode switching
│
├── LICENSE                  # MIT
└── README.md
```

---

## 🔧 How It Works

### Chat Flow

```
User sends message
       │
       ▼
  ┌─────────────────────┐
  │  Chat Mode?         │
  └────┬────────────┬───┘
       │            │
    Group       Individual
       │            │
       ▼            ▼
  SSE Stream    POST /api/chat
  8 personas    1 persona
  respond       responds
       │
       ▼
  Debate Round
  2–3 personas
  react to each
  other
```

### Group Chat Mechanics

1. **Initial Round** — All 8 personas respond in a shuffled order
2. **Debate Round** — 2–3 personas are selected to respond to what others said
3. **User can reply** — Hit the reply button on any message to add context
4. **Personas see everything** — Full conversation history is passed to each LLM call

### API Key Security

Your Groq API key **never touches the server's filesystem**. It's:
- Stored in your browser's `localStorage`
- Sent per-request via the `X-API-Key` header
- Used only for that single request, then discarded
