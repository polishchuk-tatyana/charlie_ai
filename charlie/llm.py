import os
from charlie.config import (
    LLM_MODEL, LLM_MAX_TOKENS, LLM_TEMPERATURE,
    STT_MODEL, STT_LANGUAGE,
    TTS_MODEL, TTS_VOICE,
    client,
)
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

# for tts
def tts_stream(text: str):
    """Open a streaming Groq TTS response. Returns a context manager that yields
    raw PCM16 chunks at TTS_SAMPLE_RATE; the caller reads them via iter_bytes().
    """
    return client.audio.speech.with_streaming_response.create(
        model=TTS_MODEL,
        voice=TTS_VOICE,
        response_format="wav",
        input=text,
    )