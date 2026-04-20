from difflib import SequenceMatcher

from charlie.llm import request_to_groq
from charlie.prompts import InputCategory, CLASSIFIER_PROMPT
from log_handler import logger as log

def classify_input_text(text, expected_word) -> InputCategory:
    if not text.strip():
        return InputCategory.EMPTY
    ratio = SequenceMatcher(None, text.lower().strip(), expected_word.lower()).ratio()

    log.info(f"Result lib: {ratio}. <0.3 - OFF_TOPIC, >0.9 - ON_TOPIC")
    if ratio < 0.3 and "?" in text:
        return InputCategory.OFF_TOPIC
    if ratio > 0.9:
        return InputCategory.ON_TOPIC

    # let the LLM decide what the category is if 0.3 > ratio > 0.9

    result_llm = classify_by_llm(text, expected_word)
    log.info(f"Result llm: {result_llm}")
    return result_llm


def classify_by_llm(text: str, expected_word: str) -> InputCategory:
    prompt = CLASSIFIER_PROMPT.format(word=expected_word, text=text)
    # log.info(f"Classify Prompt: {prompt}")
    raw = request_to_groq(prompt=prompt, history=[], user_msg="Classify.", temperature=0)
    cleaned = raw.strip().upper().rstrip(".")
    try:
        return InputCategory(cleaned.lower())
    except ValueError:
        return InputCategory.UNCLEAR
