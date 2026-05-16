import asyncio
import random
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
    """Get a single persona response (legacy endpoint)."""
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
    return response.content


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
            reply = response.content
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
        others_said = "\n".join(
            f"[{PERSONAS[k]['name']}]: {resp}"
            for k, resp in initial_responses.items()
            if k != key
        )

        debate_prompt = f"""The group just discussed this. Here's what everyone said:

{others_said}

The user's original message was: "{effective_user_message}"

Now react BRIEFLY (1-2 sentences max) to what the other personas said. 
Agree, disagree, challenge, or build on someone's point. Be specific — name who you're responding to.
Don't repeat what you already said. Add something NEW to the discussion.
If you genuinely have nothing to add, just say something short and move on."""

        system_content = persona["system_prompt"]
        if context:
            system_content += f"\n\nRecent group chat:\n{context}"

        messages = [
            SystemMessage(content=system_content),
            HumanMessage(content=debate_prompt),
        ]

        try:
            response = await asyncio.to_thread(llm.invoke, messages)
            reply = response.content
        except Exception as e:
            reply = f"[Could not respond: {str(e)[:100]}]"

        # Find a persona to "reply to" — pick one this persona is most likely reacting to
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
        }

        context += f"\n[{persona['name']}]: {reply}"
        await asyncio.sleep(0.3)