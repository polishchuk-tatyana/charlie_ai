import json

from charlie.config import MAX_ATTEMPTS_PER_WORD, MAX_HISTORY, WORDS
from charlie.handlers import classify_input_text
from charlie.llm import request_to_groq
from charlie.prompts import Phase, build_system_prompt, InputCategory
from log_handler import logger as log


class LessonManager:
    def __init__(self, lesson_name: str):
        self.words: list[str] = WORDS[lesson_name]
        self.__word_index: int = 0
        self.__attempts: int = 0
        self.__phase: Phase = Phase.GREETING
        self.history: list[dict] = []
        self.__finished: bool = False

    @property
    def current_word(self) -> str | None:
        if self.__word_index < len(self.words):
            return self.words[self.__word_index]
        return None

    def process_conversation(self, user_msg: str) -> str:
        self.history.append({"role": "user", "content": user_msg})

        category: InputCategory | None = None
        if self.__phase == Phase.WORD_PRACTICE:
            category = classify_input_text(user_msg, self.current_word)

        prompt = build_system_prompt(
            phase=self.__phase,
            category=category,
            word=self.current_word,
            actual=user_msg,
        )
        log.info(f"Phase: {self.__phase}, Word: {self.current_word}, Category: {category}")

        reply = request_to_groq(prompt=prompt, history=self.history[-MAX_HISTORY:], user_msg=user_msg)

        self.history.append({"role": "assistant", "content": reply})
        log.info(f"\n{json.dumps(self.history, indent=2, ensure_ascii=False)}")
        self.__switch_phase(category)
        return reply

    def __switch_phase(self, category: InputCategory | None) -> None:
        if self.__phase == Phase.GREETING:
            self.__phase = Phase.WORD_INTRO
            return

        if self.__phase == Phase.WORD_INTRO:
            # Charlie just introduced the word; the next user input will be the attempt
            self.__phase = Phase.WORD_PRACTICE
            return

        if self.__phase == Phase.WORD_PRACTICE:
            self.__attempts += 1
            succeeded = category == InputCategory.ON_TOPIC
            give_up = self.__attempts >= MAX_ATTEMPTS_PER_WORD
            if succeeded or give_up:
                self.__word_index += 1
                self.__attempts = 0
                if self.__word_index >= len(self.words):
                    self.__phase = Phase.FAREWELL
                else:
                    self.__phase = Phase.WORD_INTRO
            # else: stay in WORD_PRACTICE for another attempt
            return

        if self.__phase == Phase.FAREWELL:
            self.__finished = True

    def is_finished(self) -> bool:
        return self.__finished
