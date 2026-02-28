from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import uuid

from database import engine, get_db, Base
from models import Conversation, Message
from chat_handler import get_ai_response
from personas import PERSONAS

# Create all DB tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(title="ManasGriha API", version="1.0.0")

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

# ── Routes ───────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "ManasGriha is alive 🏛️"}


@app.get("/personas")
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


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    if request.persona_key not in PERSONAS:
        raise HTTPException(status_code=404, detail="Persona not found")

    # Get or create conversation session
    session_id = request.session_id or str(uuid.uuid4())
    conversation = db.query(Conversation).filter_by(session_id=session_id).first()

    if not conversation:
        conversation = Conversation(
            session_id=session_id,
            persona_key=request.persona_key
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    # Build history for LLM context
    history = [
        {"role": msg.role, "content": msg.content}
        for msg in conversation.messages
    ]

    # Get AI reply
    reply = get_ai_response(request.persona_key, history, request.message)

    # Save user message + AI reply to DB
    db.add(Message(conversation_id=conversation.id, role="user", content=request.message))
    db.add(Message(conversation_id=conversation.id, role="assistant", content=reply))
    db.commit()

    return ChatResponse(
        session_id=session_id,
        persona_key=request.persona_key,
        persona_name=PERSONAS[request.persona_key]["name"],
        reply=reply
    )


@app.get("/history/{session_id}")
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


@app.delete("/history/{session_id}")
def clear_history(session_id: str, db: Session = Depends(get_db)):
    conversation = db.query(Conversation).filter_by(session_id=session_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete(conversation)
    db.commit()
    return {"message": "Conversation cleared"}
