"""Lesson configuration: words, limits, model settings."""
import os
from dotenv import load_dotenv
from groq import Groq
import sounddevice as sd

load_dotenv()

client = Groq(
    api_key=os.environ.get("GROQ_API_KEY"),
)
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

PARTIAL_MATCH_THRESHOLD = 0.5
ON_TOPIC_MATCH_THRESHOLD = 0.9

# stt config
def get_device_sample_rate():
    device_info = sd.query_devices(kind="input")
    SAMPLE_RATE = int(device_info["default_samplerate"])
    return SAMPLE_RATE
SAMPLE_RATE = get_device_sample_rate()
CHANNELS = 1
STT_MODEL = "whisper-large-v3-turbo"
STT_LANGUAGE = "en"

# tts config
TTS_MODEL = "canopylabs/orpheus-v1-english"
TTS_VOICE = "austin"
TTS_SAMPLE_RATE = 24000 # Orpheus native output rate
TTS_CHANNELS = 1
