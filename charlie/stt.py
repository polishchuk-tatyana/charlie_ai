import os
import queue
import tempfile

from charlie.config import SAMPLE_RATE, CHANNELS
from charlie.llm import transcribe
from log_handler import logger as log
import numpy as np
import sounddevice as sd
import soundfile as sf

def record_and_transcribe() -> str:
    audio = _record_until_enter()
    if len(audio) == 0:
        return ""
    wav_path = _save_wav(audio)
    # try:
    log.info(wav_path)
    return transcribe(wav_path)

    # finally:
    #     os.remove(wav_path)


def _record_until_enter() -> np.ndarray:
    chunks: queue.Queue = queue.Queue()

    def callback(sound_sample, frames, time_info, status):
        chunks.put(sound_sample)

    print("🎤 Speak now... (press Enter to stop)")
    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype='int16',
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

def _save_wav(audio: np.ndarray) -> str:
    # created file .wav in tmp folder
    fd, path = tempfile.mkstemp(suffix=".wav")
    # disconnect file on os
    os.close(fd)
    # wrote audio (samples from np.ndarray) into file .wav
    sf.write(path, audio, SAMPLE_RATE)
    # record stopped, can return path only
    return path

record_and_transcribe()