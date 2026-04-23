# Charlie AI — English Lesson Core

A Python implementation of the core lesson logic for **Charlie AI**, a voice-based English teacher for children aged 4–8. Charlie is a playful 8-year-old fox from London who guides a child through a short vocabulary lesson.

This repo implements the service accepts what the child typed, drives the lesson flow, and generates Charlie's response through an LLM.
Voice I/O (STT/TTS) can be plugged in later.

## Quick start

### 1. Requirements
- Python 3.11+
- A free Groq API key — get one at https://console.groq.com

### 2. Install
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure
```bash
cp .env.example .env
# open .env and paste your GROQ_API_KEY
```

### 4. Run

**Text mode (default):**
```bash
python -m main
```
Talk to Charlie by typing. Example:
```
> hi
Hi there! I'm Charlie, a little fox from London! Want to learn fun words with me?
> ok
Look — a cat! Can you say "cat"?
> cat
Yay! Great job! Now — a dog! Say "dog"!
...
```

**Voice mode:**
```bash
python -m main --voice
```
Charlie's replies are synthesized through Groq TTS and played through your speakers; your answers are captured from the microphone. Each turn:
1. The prompt `🎤 Speak now... (press Enter to stop)` appears.
2. Say your answer (e.g. "cat"), then press Enter to end the recording.
3. Charlie's spoken reply plays back; wait for it to finish before the next turn.

On macOS you may be prompted to grant microphone permission to Terminal / your IDE on the first run — accept it, otherwise the recording will be silent.

The session ends automatically after the farewell phase in either mode.

## Project layout

```
charlie_ai/
├── main.py                 # CLI entry point: input loop
├── requirements.txt
├── .env.example
├── log_handler.py          # shared logger
└── charlie/
    ├── config.py           # lesson words, model IDs, thresholds
    ├── lesson.py           # LessonManager — state machine driving the flow
    ├── prompts.py          # persona + phase-specific instructions
    ├── handlers.py         # child-input classification (difflib + LLM)
    └── llm.py              # thin Groq client wrapper
```

## How it works

### The lesson is a state machine owned by code, not the LLM

`LessonManager` explicitly tracks:
- `phase` — `GREETING → WORD_INTRO → WORD_PRACTICE → ... → FAREWELL`
- `word_index` / `attempts` — which word we're on and how many tries the child has had
- `history` — recent dialogue turns fed back to the LLM as context

On each user turn, `process_conversation(user_msg)`:
1. appends the message to history
2. classifies the input (only during `WORD_PRACTICE`)
3. builds a **dynamically assembled system prompt** from `BASE_PERSONA` + a task instruction for the current phase/category
4. calls the LLM
5. stores the reply and advances the phase

The LLM is responsible only for **how** Charlie speaks. **What** happens next — which word comes up, when to congratulate, when to say goodbye — is decided by code. This makes the flow deterministic, testable, and easy to extend.

### Input classification handles the real world

Children don't give clean answers. They stay silent, mispronounce, say random things, or ask questions. `handlers.classify_input_text` sorts input into one of:

- `EMPTY` — silent or whitespace
- `ON_TOPIC` — said the target word (allowing small mistakes)
- `PARTIAL` — tried but missed (e.g. "ket" → "cat")
- `OFF_TOPIC` — unrelated ("I like pizza", "how do you spell it?")
- `UNCLEAR` — could not tell

The classifier is a **hybrid**:
- Cheap `difflib.SequenceMatcher` handles the obvious cases (empty / near-exact match / clearly unrelated questions).
- The marginal grey zone (ratio between the thresholds) gets escalated to a small LLM call with a dedicated classifier prompt, temperature `0`, and a few-shot examples.

This keeps latency and cost low on the common path while keeping accuracy on ambiguous inputs.

### Prompt structure

Every LLM call for Charlie gets a system prompt built fresh at runtime:

```
BASE_PERSONA (constant — character, tone, rules)
+ CURRENT TASK (dynamic — depends on phase and, for practice, input category)
```

Phase-specific instructions live in `PHASE_INSTRUCTIONS` / `PRACTICE_INSTRUCTIONS` and are `.format(word=..., actual=...)`-ed just before the call. Charlie always receives a narrow "do exactly this right now" task rather than a vague "run a whole lesson" mandate.

## Design decisions

### Two LLM calls in `WORD_PRACTICE` (classifier + responder)

During the practice phase the system can make up to two LLM calls: one to classify the child's input, then one to generate Charlie's reply. This looks heavier than necessary, but I chose it deliberately because the two calls have **different requirements**:

| | Classifier | Responder |
|---|---|---|
| Temperature | `0` (deterministic, we want the same label for the same input) | `~0.7` (playful, varied) |
| Role | judgement | character performance |
| Failure mode tolerance | must be correct — drives state transitions | soft — rephrasing is fine |

With two calls I can set each knob independently. The classifier is strict and repeatable; the responder is warm and alive.

### Alternative: single-call with JSON output (not used, but valid)

The two calls can be collapsed into **one** by asking the LLM to return a structured JSON like:

```json
{"category": "ON_TOPIC", "reply": "Yay! You did it!"}
```

…using Groq's JSON mode (`response_format={"type": "json_object"}`). This halves the number of requests and reduces latency — a meaningful optimization in a real-time voice product where every ~200 ms counts.

**Why I didn't do it here:** a single call forces a single temperature. The classifier wants `0`, the responder wants something higher for variety; any compromise (e.g. `0.3`) weakens both sides — the classifier becomes slightly less stable on edge cases, and Charlie becomes slightly more monotonic. For a correctness-sensitive path (category drives phase transitions), I preferred the cleaner separation.

**When I would switch:** in production, once latency/cost matters more than marginal classifier accuracy, or if evaluation shows JSON-mode classification holds up well enough. The single-call approach is a fully valid production path — I just didn't pick it for this task.

### Why state in code, not in the prompt

A prompt like *"greet the child, teach them cat/dog/bird, then say goodbye"* sounds tempting but makes the LLM responsible for pacing, transitions, and memory across turns — all of which LLMs do poorly and inconsistently. Explicit code-owned state gives us:
- deterministic lesson length
- trivial unit-testability of transitions
- easy ability to change flow (add a new phase, skip a word after N failed attempts, etc.) without touching prompts

### Why `.env` holds only the API key

Everything else — words, model IDs, thresholds, max tokens — lives in `charlie/config.py`. It's application logic, versioned with the code. `.env` is reserved for secrets and per-environment differences, which is only the Groq key in this setup.

## Extending the lesson

- **More words / other topics:** `WORDS` in `config.py` is a dict keyed by lesson name. Add a new entry (e.g. `"colors_lesson": ["red", "blue", ...]`) and pass the key to `LessonManager(lesson_name=...)`.
- **More phases:** add a value to the `Phase` enum, add an entry to `PHASE_INSTRUCTIONS`, and add the transition in `LessonManager.__switch_phase`.
- **Different reaction styles:** adjust `PRACTICE_INSTRUCTIONS[category]` — no code changes needed.

## Voice I/O

The lesson core is text-only by design, but the project ships with both sides of a full voice cycle — STT on the way in and streaming TTS on the way out. They are not yet wired into `main.py` (the CLI still uses `input()` / `print()`), but both adapters are standalone and ready to plug in.

### Speech-to-text (`charlie/stt.py`)

Records audio from the microphone with `sounddevice` using a push-to-talk style: the call starts an input stream, the user speaks, pressing Enter stops the recording. The captured samples are saved as a WAV under `records/` (timestamped filename, so each session keeps a replayable trail for debugging) and transcribed through Groq `whisper-large-v3-turbo`. `record_and_transcribe()` returns a clean string ready to be passed into `LessonManager.process_conversation`.

Key choices:
- **Enter-to-stop** over fixed duration — children don't fit a timer, and silence detection is fragile on young voices.
- **Native sample rate** (`sd.query_devices(...)['default_samplerate']`) — avoids the classic macOS glitch where requesting 16 kHz on a 48 kHz-only mic yields garbled audio.
- **Language pinned to English** — Whisper would otherwise burn latency auto-detecting, and on short clips like `"cat"` it often picks wrong.

### Text-to-speech (`charlie/tts.py`)

Streams Charlie's reply from Groq `canopylabs/orpheus-v1-english` (voice `austin`) and plays it live through `sounddevice.OutputStream`. Nothing is written to disk — audio is consumed as it comes over the wire.

The implementation uses three cooperating threads:
- **Producer** — downloads the HTTP response in 4 KB chunks, skips the WAV header by searching for the `"data"` sub-chunk (the header length is not fixed), and pushes raw PCM bytes into a `queue.Queue`.
- **Audio callback** — `sounddevice` calls it from its own audio thread every ~20 ms; it pulls bytes from the queue, carries any leftover from the previous callback so samples aren't lost, converts them to `int16`, and writes into the output buffer. On the end-of-stream sentinel it pads with silence and raises `sd.CallbackStop` to stop cleanly.
- **Main thread** — blocks on a `threading.Event` that the callback sets once playback finishes.

`speak(text)` is a single function call; the threading, synchronization and header skipping are internal.

Key choices:
- **Streaming over save-to-file** — playback starts after the first few KB instead of waiting for the whole clip; noticeable on slow networks and on longer Charlie replies.
- **WAV + runtime header skip** — Groq's Orpheus endpoint does not currently accept `response_format="pcm"`, so the producer finds the `"data"` marker itself instead of relying on a fixed 44-byte offset (the real header includes a variable-length `LIST/INFO` chunk).
- **Playback sample rate slightly above native** — bumping `sd.OutputStream` to ~28800 Hz while Orpheus renders at 24000 Hz makes Charlie sound a bit faster and brighter, which fits a small playful fox better than the default rate.

### Putting it together

`main.py` exposes a `--voice` flag that swaps `input()` for `record_and_transcribe()` and `print()` for `speak()`. The lesson core is unchanged — it still takes a string in and returns a string out; voice is purely an I/O-layer swap on top of the same `LessonManager`.
