import os

from charlie.config import LLM_MODEL, LLM_MAX_TOKENS, LLM_TEMPERATURE
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
client = Groq(
    api_key=os.environ.get("GROQ_API_KEY"),
)


def request_to_groq(prompt: str, history: list, user_msg: str, temperature: float = LLM_TEMPERATURE) -> str:
    messages: list = [{"role": "system", "content": prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_msg})
    chat_completion = client.chat.completions.create(
        messages=messages,
        model=LLM_MODEL,
        temperature=temperature,
        max_completion_tokens=LLM_MAX_TOKENS
    )
    return str(chat_completion.choices[0].message.content)
