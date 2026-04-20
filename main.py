from charlie.lesson import LessonManager

def main():
    lesson = LessonManager("animals_lesson")
    while True:
        text = input("> ")
        reply = lesson.process_conversation(str(text))
        print(reply)
        if lesson.is_finished():
            break


if __name__ == '__main__':
    main()

