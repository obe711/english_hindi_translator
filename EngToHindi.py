#!/usr/bin/env python3

##Translate English from Microphone to Hindi

## - Need to figure out how to run on 2nd PI over network. Maybe websocket?


import speech_recognition as sr
from googletrans import Translator
from pydub import AudioSegment
from pydub.playback import play
from gtts import gTTS

translator = Translator()

# obtain audio from the microphone
r = sr.Recognizer()
with sr.Microphone() as source:
    print("Say something!")
    audio = r.listen(source)

try:
    print("TRANSLATING")
    audio_input = r.recognize_sphinx(audio)
    ###translation = translator.translate(audio_input, dest='hi').text
    pronounced = translator.translate(audio_input, dest='hi').extra_data['translation'][1][2]
    print("You Said: ", audio_input)
    ###print("Translation: ", translation)
    ###print("Pronounced: ", pronounced)
    tts = gTTS(pronounced,lang='hi')
    tts.save('translation.mp3')
    sound = AudioSegment.from_file("translation.mp3", format="mp3")
    play(sound)
except sr.UnknownValueError:
    print("Could not understand audio")
except sr.RequestError as e:
    print("Error; {0}".format(e))

