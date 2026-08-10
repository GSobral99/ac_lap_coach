import pyttsx3

import time

def speak(messages):
    engine = pyttsx3.init()
    for message in messages:
        engine.say(message)
        engine.runAndWait()
        time.sleep(0.3)
