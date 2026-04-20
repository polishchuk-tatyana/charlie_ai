import os
import queue
import tempfile
from datetime import datetime
from pathlib import Path

from charlie.config import SAMPLE_RATE, CHANNELS
from charlie.llm import transcribe
from log_handler import logger as log
import numpy as np
import sounddevice as sd
import soundfile as sf

RECORDS_DIR = Path(__file__).resolve().parent.parent / "records"

def record_and_transcribe() -> str:
    audio = _record_until_enter()
    if len(audio) == 0:
        return ""
    wav_path = _save_wav_to_records(audio)
    log.info(f"Saved recording: {wav_path}")
    try:
        return transcribe(wav_path)
    except Exception as e:
        log.error(e)
        return ""


def _record_until_enter() -> np.ndarray:
    chunks: queue.Queue = queue.Queue()

    def callback(sound_sample, frames, time_info, status):
        chunks.put(sound_sample.copy())

    print("🎤 Speak now... (press Enter to stop)")
    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype='int16',
        blocksize=0,
        callback=callback
    ):
        input()
    print("✓ Recording stopped.")

    frames = []
    while not chunks.empty():
        frames.append(chunks.get())
    if not frames:
        return np.array([], dtype=np.int16)
    return np.concatenate(frames, axis=0)

def _save_wav_to_records(audio: np.ndarray) -> str:
    RECORDS_DIR.mkdir(parents=True, exist_ok=True)
    filename = datetime.now().strftime("%Y%m%d_%H%M%S_%f") + ".wav"
    path = RECORDS_DIR / filename
    sf.write(str(path), audio, SAMPLE_RATE, subtype="PCM_16")
    return str(path)


def _save_wav_to_tmp(audio: np.ndarray) -> str:
    # created file .wav in tmp folder
    fd, path = tempfile.mkstemp(suffix=".wav")
    # disconnect file on os
    os.close(fd)
    # wrote audio (samples from np.ndarray) into file .wav
    sf.write(path, audio, SAMPLE_RATE, subtype="PCM_16")
    # record stopped, can return path only
    return path

record_and_transcribe()