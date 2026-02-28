from langchain_groq import ChatGroq
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from personas import PERSONAS
from dotenv import load_dotenv
import os

load_dotenv()

llm = ChatGroq(
    model="llama3-70b-8192",
    temperature=0.85,
    max_tokens=1024,
    groq_api_key=os.getenv("GROQ_API_KEY")
)

def get_ai_response(persona_key: str, history: list, user_message: str) -> str:
    if persona_key not in PERSONAS:
        raise ValueError(f"Unknown persona: {persona_key}")

    persona = PERSONAS[persona_key]
    messages = [SystemMessage(content=persona["system_prompt"])]

    for msg in history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))

    messages.append(HumanMessage(content=user_message))

    response = llm.invoke(messages)
    return response.content