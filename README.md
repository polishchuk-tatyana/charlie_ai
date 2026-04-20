# Charlie AI — English Lesson Core

A Python implementation of the core lesson logic for **Charlie AI**, a voice-based English teacher for children aged 4–8. Charlie is a playful 8-year-old fox from London who guides a child through a short vocabulary lesson.

This repo implements the **text-only core** (per the task brief): the service accepts what the child typed, drives the lesson flow, and generates Charlie's response through an LLM.
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
The session ends automatically after the farewell phase.

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

The lesson core is text-only by design, but the project includes scaffolding for a full voice cycle.

**Speech-to-text** (`charlie/stt.py`) — records audio from the microphone with `sounddevice` using a push-to-talk style (start on call, stop on Enter), saves the stream to a temporary WAV, and transcribes it through Groq `whisper-large-v3-turbo`. `record_and_transcribe()` returns a clean string ready to be passed into `LessonManager.process_conversation`. STT is not wired into `main.py` yet — the CLI still reads from `input()`.

**Text-to-speech** (`charlie/tts.py`) — will feed Charlie's reply to Groq `playai-tts` and play the resulting audio back to the child. Since `process_conversation` already returns a plain string, TTS is a thin adapter on the output side — symmetrical to STT on the input side. Once both are done, `main.py` will gain a `--voice` flag that swaps `input()` for the microphone and `print()` for playback, keeping the text mode as the default.
