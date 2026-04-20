import os
from charlie.config import LLM_MODEL, LLM_MAX_TOKENS, LLM_TEMPERATURE, STT_MODEL, STT_LANGUAGE, client
from log_handler import logger as log

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

# for sst
def transcribe(wav_path: str) -> str:
    # read binary data (`rb`) from .wav file and convert into text
    with open(wav_path, "rb") as f:
        transcription = client.audio.transcriptions.create(
            file=(os.path.basename(wav_path), f.read()),
            model=STT_MODEL,
            language=STT_LANGUAGE,
            temperature=0,
            response_format="text",
        )
    text = str(transcription).strip()
    log.info(f"Transcribed: {text!r}")
    return text
