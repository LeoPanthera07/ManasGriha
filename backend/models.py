from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database import Base


# ── Legacy models (kept for backward compat) ──────────────────────────────────

class Conversation(Base):
    __tablename__ = "conversations"

    id           = Column(Integer, primary_key=True, index=True)
    session_id   = Column(String, unique=True, index=True, nullable=False)
    persona_key  = Column(String, nullable=False)
    created_at   = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.timestamp"
    )


class Message(Base):
    __tablename__ = "messages"

    id              = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role            = Column(String, nullable=False)   # "user" | "assistant"
    content         = Column(Text, nullable=False)
    timestamp       = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    conversation = relationship("Conversation", back_populates="messages")


# ── Group chat models ─────────────────────────────────────────────────────────

class GroupConversation(Base):
    __tablename__ = "group_conversations"

    id         = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    messages = relationship(
        "GroupMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="GroupMessage.timestamp"
    )


class GroupMessage(Base):
    __tablename__ = "group_messages"

    id              = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("group_conversations.id"), nullable=False)
    role            = Column(String, nullable=False)       # "user" | "assistant"
    persona_key     = Column(String, nullable=True)        # null for user messages
    content         = Column(Text, nullable=False)
    reply_to_id     = Column(Integer, ForeignKey("group_messages.id"), nullable=True)
    timestamp       = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    conversation = relationship("GroupConversation", back_populates="messages")
    reply_to     = relationship("GroupMessage", remote_side=[id], uselist=False)
