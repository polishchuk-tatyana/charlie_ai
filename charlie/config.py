"""Lesson configuration: words, limits, model settings."""

# there can be many lessons on different topics and I decided to use dict for them and one lesson with words is a list,
# I use only one lesson for this task, but in future it can be extended
WORDS = {
    "animals_lesson": ["cat", "dog", "elephant", "dragonfly"]
}

MAX_ATTEMPTS_PER_WORD = 3
MAX_HISTORY = 10

LLM_MODEL = "llama-3.3-70b-versatile"
LLM_TEMPERATURE = 1
LLM_MAX_TOKENS = 1024

STT_MODEL = "whisper-large-v3-turbo"
STT_LANGUAGE = "en"

TTS_MODEL = "playai-tts"
TTS_VOICE = "Fritz-PlayAI"

PARTIAL_MATCH_THRESHOLD = 0.5
ON_TOPIC_MATCH_THRESHOLD = 0.9
