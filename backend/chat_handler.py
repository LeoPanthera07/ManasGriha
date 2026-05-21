import asyncio
import random
import re
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from personas import PERSONAS


def _build_llm(api_key: str) -> ChatGroq:
    """Create a Groq LLM instance with the user-provided API key."""
    return ChatGroq(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        temperature=0.85,
        api_key=api_key,
    )


def _clean_response(text: str, persona_name: str) -> str:
    """Strip LLM artifacts that leak prompt structure into the visible message."""

    # Remove "[PersonaName]:" or "[PersonaName] :" prefix (the LLM echoing its own name)
    for p in PERSONAS.values():
        text = re.sub(
            rf'^\s*\[?\s*{re.escape(p["name"])}\s*\]?\s*:\s*',
            '', text, count=1, flags=re.IGNORECASE
        )

    # Remove "Responding to X:" / "Replying to X:" / "In response to X:" prefixes
    text = re.sub(
        r'^(Responding|Replying|In response)\s+to\s+[\w\s]+?:\s*',
        '', text, count=1, flags=re.IGNORECASE
    )

    # Remove meta-commentary the LLM sometimes adds
    noise_patterns = [
        r'No more responses? needed\.?',
        r'I\'ll keep it brief\.?',
        r'Here\'s my (?:brief )?(?:take|response|thought)[:.]?\s*',
        r'Let me (?:briefly )?respond[:.]?\s*',
    ]
    for pat in noise_patterns:
        text = re.sub(pat, '', text, flags=re.IGNORECASE)

    return text.strip()


def _detect_reply_target(reply_text: str, own_key: str) -> str | None:
    """Scan the reply text to find which persona is being referenced.
    Returns the persona key most likely being replied to, or None."""
    mentioned = []
    lower = reply_text.lower()
    for key, persona in PERSONAS.items():
        if key == own_key:
            continue
        # Check for name mention (case-insensitive)
        if persona["name"].lower() in lower:
            mentioned.append(key)
        # Also check first name only (e.g. "Marcus" for "Marcus Aurelius")
        first_name = persona["name"].split()[0].lower()
        if len(first_name) > 3 and first_name in lower and key not in mentioned:
            mentioned.append(key)

    return mentioned[0] if mentioned else None


def _build_group_context(conversation_history: list) -> str:
    """Build a readable summary of recent group chat messages for persona context."""
    if not conversation_history:
        return ""

    lines = []
    for msg in conversation_history[-30:]:  # last 30 messages for context
        if msg["role"] == "user":
            lines.append(f"[User]: {msg['content']}")
        else:
            name = msg.get("persona_name", msg.get("persona_key", "Unknown"))
            lines.append(f"[{name}]: {msg['content']}")

    return "\n".join(lines)


def get_ai_response(persona_key: str, conversation_history: list, user_message: str, api_key: str) -> str:
    """Get a single persona response (individual chat endpoint)."""
    persona = PERSONAS.get(persona_key)
    if not persona:
        return "I don't recognize that persona."

    llm = _build_llm(api_key)
    messages = [SystemMessage(content=persona["system_prompt"])]

    for msg in conversation_history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))

    messages.append(HumanMessage(content=user_message))
    response = llm.invoke(messages)
    return _clean_response(response.content, persona["name"])


async def get_group_responses(
    conversation_history: list,
    user_message: str,
    api_key: str,
    reply_to_content: str = None,
    reply_to_persona: str = None,
):
    """
    Async generator that yields persona responses one-by-one.
    Each yield is a dict: {persona_key, persona_name, avatar, color, reply}
    """
    llm = _build_llm(api_key)
    context = _build_group_context(conversation_history)

    # Build the user's message with reply context if applicable
    effective_user_message = user_message
    if reply_to_content and reply_to_persona:
        effective_user_message = f"[Replying to {reply_to_persona}'s message: \"{reply_to_content}\"]\n{user_message}"

    # Shuffle persona order so it's not always the same person first
    persona_keys = list(PERSONAS.keys())
    random.shuffle(persona_keys)

    # ── Round 1: All personas respond to the user ────────────────────────
    initial_responses = {}

    for key in persona_keys:
        persona = PERSONAS[key]

        system_content = persona["system_prompt"]
        if context:
            system_content += f"\n\nHere is the recent group chat conversation:\n{context}"

        messages = [
            SystemMessage(content=system_content),
            HumanMessage(content=effective_user_message),
        ]

        try:
            response = await asyncio.to_thread(llm.invoke, messages)
            reply = _clean_response(response.content, persona["name"])
        except Exception as e:
            reply = f"[Could not respond: {str(e)[:100]}]"

        initial_responses[key] = reply

        yield {
            "type": "persona_reply",
            "persona_key": key,
            "persona_name": persona["name"],
            "avatar": persona["avatar"],
            "color": persona["color"],
            "reply": reply,
        }

        # Update context with this persona's response for the next personas
        context += f"\n[{persona['name']}]: {reply}"

        # Small delay to feel natural (not all messages at once)
        await asyncio.sleep(0.3)

    # ── Round 2: Debate — 2-3 personas react to what others said ─────────
    debate_personas = random.sample(persona_keys, min(3, len(persona_keys)))

    for key in debate_personas:
        persona = PERSONAS[key]

        # Build what others said (excluding this persona)
        others = [
            f"- {PERSONAS[k]['name']}: \"{resp}\""
            for k, resp in initial_responses.items()
            if k != key
        ]
        others_said = "\n".join(others)

        debate_prompt = f"""This is a group chat. Everyone just shared their views on: "{effective_user_message}"

What others said:
{others_said}

You already spoke. Now jump back in with a QUICK reaction (1-2 sentences). 
Pick one thing someone else said that you agree with, disagree with, or want to push further. 
Write ONLY your reaction — nothing else. No introductions, no labels, no meta-commentary."""

        system_content = persona["system_prompt"]
        if context:
            system_content += f"\n\nRecent group chat:\n{context}"

        messages = [
            SystemMessage(content=system_content),
            HumanMessage(content=debate_prompt),
        ]

        try:
            response = await asyncio.to_thread(llm.invoke, messages)
            reply = _clean_response(response.content, persona["name"])
        except Exception as e:
            reply = f"[Could not respond: {str(e)[:100]}]"

        # Detect which persona is being replied to from actual content
        reply_to_key = _detect_reply_target(reply, key)
        if not reply_to_key:
            # Fallback: pick a random other persona
            reply_to_key = random.choice([k for k in persona_keys if k != key])

        yield {
            "type": "debate_reply",
            "persona_key": key,
            "persona_name": persona["name"],
            "avatar": persona["avatar"],
            "color": persona["color"],
            "reply": reply,
            "reply_to_key": reply_to_key,
            "reply_to_name": PERSONAS[reply_to_key]["name"],
            "reply_to_content": initial_responses.get(reply_to_key, ""),
        }

        context += f"\n[{persona['name']}]: {reply}"
        await asyncio.sleep(0.3)