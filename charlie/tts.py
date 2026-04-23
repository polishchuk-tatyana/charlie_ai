"""Stream Charlie's voice from Groq TTS and play it live via sounddevice."""
import queue
import threading

import numpy as np
import sounddevice as sd

from charlie.config import TTS_CHANNELS, TTS_SAMPLE_RATE
from charlie.llm import tts_stream
from log_handler import logger as log

BYTES_PER_SAMPLE = 2       # PCM16 = 2 bytes per sample
CHUNK_BYTES = 4096         # HTTP read size
END_OF_STREAM = None       # sentinel put in the queue when download finishes


def speak(text: str) -> None:
    audio_queue: queue.Queue = queue.Queue()
    finished = threading.Event()

    def producer():
        header_buf = bytearray()
        header_done = False
        try:
            with tts_stream(text) as response:
                for chunk in response.iter_bytes(chunk_size=CHUNK_BYTES):
                    if header_done:
                        audio_queue.put(chunk)
                        continue
                    header_buf.extend(chunk)
                    # Find the "data" subchunk — PCM bytes start 8 bytes after it
                    # (4 bytes for "data" tag + 4 bytes for chunk size).
                    data_idx = header_buf.find(b"data")
                    if data_idx != -1 and len(header_buf) >= data_idx + 8:
                        pcm_start = data_idx + 8
                        leftover = bytes(header_buf[pcm_start:])
                        if leftover:
                            audio_queue.put(leftover)
                        header_done = True
        except Exception as e:
            log.error(f"TTS stream failed: {e}")
        finally:
            audio_queue.put(END_OF_STREAM)

    leftover = bytearray()   # bytes pulled from queue but not yet played

    def callback(outdata, frames, time_info, status):
        needed = frames * TTS_CHANNELS * BYTES_PER_SAMPLE
        buf = bytearray(leftover)
        leftover.clear()

        while len(buf) < needed:
            try:
                chunk = audio_queue.get_nowait()
            except queue.Empty:
                break
            if chunk is END_OF_STREAM:
                buf.extend(b"\x00" * (needed - len(buf)))
                outdata[:] = np.frombuffer(bytes(buf[:needed]), dtype=np.int16).reshape(-1, TTS_CHANNELS)
                finished.set()
                raise sd.CallbackStop
            buf.extend(chunk)

        if len(buf) < needed:
            buf.extend(b"\x00" * (needed - len(buf)))
        outdata[:] = np.frombuffer(bytes(buf[:needed]), dtype=np.int16).reshape(-1, TTS_CHANNELS)
        leftover.extend(buf[needed:])   # carry remainder to next callback

    threading.Thread(target=producer, daemon=True).start()

    with sd.OutputStream(
        samplerate=TTS_SAMPLE_RATE,
        channels=TTS_CHANNELS,
        dtype="int16",
        callback=callback,
    ):
        finished.wait()
