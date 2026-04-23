import argparse

from charlie.lesson import LessonManager
from charlie.stt import record_and_transcribe
from charlie.tts import speak


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--voice", action="store_true", help="Use mic + speaker instead of keyboard")
    args = parser.parse_args()
    lesson = LessonManager("animals_lesson")
    while True:
        if args.voice:
            text = record_and_transcribe()
        else:
            text = input("> ")
        reply = lesson.process_conversation(str(text))
        print(reply)
        if args.voice:
            speak(reply)
        if lesson.is_finished():
            break


if __name__ == '__main__':
    main()
