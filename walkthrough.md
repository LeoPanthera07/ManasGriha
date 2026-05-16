# ManasGriha Overhaul — Walkthrough

## What Changed

ManasGriha was transformed from a Flutter mobile app with individual persona chats into a **web-based dual-mode chat application** served directly by FastAPI.

### Two Chat Modes

| Mode | What it does |
|------|-------------|
| **The Council** (Group) | All 8 personas respond to your message, then debate each other |
| **Individual** (1-on-1) | Private conversation with a single persona |

The sidebar lets you switch between modes — "The Council" for group, or click any persona for 1-on-1.

---

## Screenshots

### Sidebar Layout — Group & Individual sections
![Sidebar showing GROUP and INDIVIDUAL sections with all personas](/Users/mihir/.gemini/antigravity/brain/61beda78-340c-491e-ad4c-9bb5b9831296/artifacts/sidebar_layout.png)

### Individual Chat — David Goggins
![1-on-1 chat with David Goggins, showing his response to a workout consistency question](/Users/mihir/.gemini/antigravity/brain/61beda78-340c-491e-ad4c-9bb5b9831296/artifacts/individual_chat.png)

### Group Chat — Welcome Screen
![The Council welcome screen with all 8 persona tags](/Users/mihir/.gemini/antigravity/brain/61beda78-340c-491e-ad4c-9bb5b9831296/artifacts/group_welcome.png)

---

## Files Changed

### Backend

| File | Change |
|------|--------|
| [personas.py](file:///Users/mihir/Programming/Projects_Local/ManasGriha/backend/personas.py) | Unified persona definitions, added group chat rules |
| [models.py](file:///Users/mihir/Programming/Projects_Local/ManasGriha/backend/models.py) | Added `GroupConversation` + `GroupMessage` with `reply_to_id` |
| [chat_handler.py](file:///Users/mihir/Programming/Projects_Local/ManasGriha/backend/chat_handler.py) | Async group response generator, debate rounds, BYOK |
| [main.py](file:///Users/mihir/Programming/Projects_Local/ManasGriha/backend/main.py) | SSE endpoint, BYOK via `X-API-Key` header, static file serving |
| [database.py](file:///Users/mihir/Programming/Projects_Local/ManasGriha/backend/database.py) | Fixed DB path to absolute (works from any CWD) |
| [requirements.txt](file:///Users/mihir/Programming/Projects_Local/ManasGriha/backend/requirements.txt) | Added `sse-starlette` |

### Frontend (New — replaced Flutter)

| File | Purpose |
|------|---------|
| [index.html](file:///Users/mihir/Programming/Projects_Local/ManasGriha/frontend/index.html) | SPA entry with sidebar, chat, modal, toast |
| [index.css](file:///Users/mihir/Programming/Projects_Local/ManasGriha/frontend/assets/styles/index.css) | Full design system — glassmorphism, gradients, macOS aesthetic |
| [app.js](file:///Users/mihir/Programming/Projects_Local/ManasGriha/frontend/assets/js/app.js) | Dual-mode chat, SSE streaming, BYOK, reply-to, mode switching |

---

## How to Run

```bash
cd backend
source .venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Open http://localhost:8000, enter your Groq API key, and start chatting.

## Verification

- ✅ Group chat: All 8 personas respond via SSE + 3 debate replies
- ✅ Individual chat: 1-on-1 with Goggins confirmed working
- ✅ Mode switching: Sidebar toggles between group and individual
- ✅ BYOK: API key stored in localStorage, passed via `X-API-Key` header
- ✅ Reply-to: Messages can reference other messages in group chat
- ✅ Design: Dark glassmorphism, gradient accents, macOS rounded corners, Inter font
