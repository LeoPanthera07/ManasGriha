import json
import uuid
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from sse_starlette.sse import EventSourceResponse

from database import engine, get_db, Base
from models import Conversation, Message, GroupConversation, GroupMessage
from chat_handler import get_ai_response, get_group_responses
from personas import PERSONAS

# Create all DB tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(title="ManasGriha API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Schemas ──────────────────────────────────────────────
class ChatRequest(BaseModel):
    persona_key: str
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    session_id: str
    persona_key: str
    persona_name: str
    reply: str

class GroupChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    reply_to_id: Optional[int] = None


# ── Helper: extract API key from request ─────────────────
def get_api_key(request: Request) -> str:
    key = request.headers.get("x-api-key", "").strip()
    if not key:
        raise HTTPException(status_code=401, detail="GROQ API key required. Pass it in the X-API-Key header.")
    return key


# ── Routes ───────────────────────────────────────────────

@app.get("/api")
def root():
    return {"status": "ManasGriha is alive 🏛️", "version": "2.0.0"}


@app.get("/api/personas")
def get_personas():
    return [
        {
            "key": key,
            "name": p["name"],
            "tagline": p["tagline"],
            "avatar": p["avatar"],
            "color": p["color"]
        }
        for key, p in PERSONAS.items()
    ]


# ── Legacy individual chat ───────────────────────────────
@app.post("/api/chat", response_model=ChatResponse)
def chat(request_body: ChatRequest, request: Request, db: Session = Depends(get_db)):
    api_key = get_api_key(request)

    if request_body.persona_key not in PERSONAS:
        raise HTTPException(status_code=404, detail="Persona not found")

    session_id = request_body.session_id or str(uuid.uuid4())
    conversation = db.query(Conversation).filter_by(session_id=session_id).first()

    if not conversation:
        conversation = Conversation(
            session_id=session_id,
            persona_key=request_body.persona_key
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    history = [
        {"role": msg.role, "content": msg.content}
        for msg in conversation.messages
    ]

    reply = get_ai_response(request_body.persona_key, history, request_body.message, api_key)

    db.add(Message(conversation_id=conversation.id, role="user", content=request_body.message))
    db.add(Message(conversation_id=conversation.id, role="assistant", content=reply))
    db.commit()

    return ChatResponse(
        session_id=session_id,
        persona_key=request_body.persona_key,
        persona_name=PERSONAS[request_body.persona_key]["name"],
        reply=reply
    )


# ── Group chat (SSE streaming) ──────────────────────────
@app.post("/api/group-chat")
async def group_chat(request_body: GroupChatRequest, request: Request, db: Session = Depends(get_db)):
    api_key = get_api_key(request)

    session_id = request_body.session_id or str(uuid.uuid4())
    conversation = db.query(GroupConversation).filter_by(session_id=session_id).first()

    if not conversation:
        conversation = GroupConversation(session_id=session_id)
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    # Extract the conversation ID as a plain int (avoids DetachedInstanceError later)
    conversation_id = int(conversation.id)

    # Build conversation history (extract all data now, before session closes)
    history = []
    for msg in conversation.messages:
        entry = {"role": msg.role, "content": msg.content}
        if msg.persona_key:
            entry["persona_key"] = msg.persona_key
            entry["persona_name"] = PERSONAS.get(msg.persona_key, {}).get("name", msg.persona_key)
        history.append(entry)

    # Resolve reply-to context
    reply_to_content = None
    reply_to_persona = None
    if request_body.reply_to_id:
        reply_to_msg = db.query(GroupMessage).filter_by(id=request_body.reply_to_id).first()
        if reply_to_msg:
            reply_to_content = reply_to_msg.content
            if reply_to_msg.persona_key:
                reply_to_persona = PERSONAS.get(reply_to_msg.persona_key, {}).get("name", reply_to_msg.persona_key)
            else:
                reply_to_persona = "User"

    # Save user message
    user_msg = GroupMessage(
        conversation_id=conversation_id,
        role="user",
        content=request_body.message,
        reply_to_id=request_body.reply_to_id,
    )
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)
    user_msg_id = int(user_msg.id)

    # Capture all needed values before the generator runs
    user_message_text = request_body.message

    async def event_generator():
        # Send session info first
        yield {
            "event": "session",
            "data": json.dumps({"session_id": session_id, "user_message_id": user_msg_id}),
        }

        # Create a fresh DB session for the generator (the request session is closed by now)
        from database import SessionLocal
        gen_db = SessionLocal()

        try:
            async for response in get_group_responses(
                conversation_history=history,
                user_message=user_message_text,
                api_key=api_key,
                reply_to_content=reply_to_content,
                reply_to_persona=reply_to_persona,
            ):
                # Save persona message to DB using the generator's own session
                persona_msg = GroupMessage(
                    conversation_id=conversation_id,
                    role="assistant",
                    persona_key=response["persona_key"],
                    content=response["reply"],
                    reply_to_id=user_msg_id if response["type"] == "persona_reply" else None,
                )
                gen_db.add(persona_msg)
                gen_db.commit()
                gen_db.refresh(persona_msg)

                response["message_id"] = persona_msg.id

                yield {
                    "event": response["type"],
                    "data": json.dumps(response),
                }
        finally:
            gen_db.close()

        yield {"event": "done", "data": json.dumps({"status": "complete"})}

    return EventSourceResponse(event_generator())


# ── Group history ────────────────────────────────────────
@app.get("/api/group-history/{session_id}")
def get_group_history(session_id: str, db: Session = Depends(get_db)):
    conversation = db.query(GroupConversation).filter_by(session_id=session_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = []
    for m in conversation.messages:
        msg_data = {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "timestamp": m.timestamp.isoformat() if m.timestamp else None,
            "reply_to_id": m.reply_to_id,
        }
        if m.persona_key:
            persona = PERSONAS.get(m.persona_key, {})
            msg_data["persona_key"] = m.persona_key
            msg_data["persona_name"] = persona.get("name", m.persona_key)
            msg_data["avatar"] = persona.get("avatar", "🤖")
            msg_data["color"] = persona.get("color", "#888")
        messages.append(msg_data)

    return {"session_id": session_id, "messages": messages}


@app.delete("/api/group-history/{session_id}")
def clear_group_history(session_id: str, db: Session = Depends(get_db)):
    conversation = db.query(GroupConversation).filter_by(session_id=session_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete(conversation)
    db.commit()
    return {"message": "Group conversation cleared"}


# ── Legacy endpoints ─────────────────────────────────────
@app.get("/api/history/{session_id}")
def get_history(session_id: str, db: Session = Depends(get_db)):
    conversation = db.query(Conversation).filter_by(session_id=session_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session_id": session_id,
        "persona_key": conversation.persona_key,
        "messages": [
            {"role": m.role, "content": m.content, "timestamp": m.timestamp}
            for m in conversation.messages
        ]
    }


@app.delete("/api/history/{session_id}")
def clear_history(session_id: str, db: Session = Depends(get_db)):
    conversation = db.query(Conversation).filter_by(session_id=session_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete(conversation)
    db.commit()
    return {"message": "Conversation cleared"}


# ── Serve frontend static files ──────────────────────────
# This MUST be last so API routes take precedence
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="static-assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """Serve the SPA — all non-API routes return index.html."""
        file_path = FRONTEND_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIR / "index.html")
