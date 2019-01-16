from __future__ import division

import re
import sys

from google.cloud import translate


from google.cloud import speech
from google.cloud.speech import enums
from google.cloud.speech import types
from pydub import AudioSegment
from pydub.playback import play
from gtts import gTTS
import pyaudio
from six.moves import queue


#### Instantiate a client
translate_client = translate.Client()

# Audio recording parameters
RATE = 16000
CHUNK = int(RATE / 10)  # 100ms

#SPEAKER CODES
    # hi-IN Hindi
    # ur-IN	Urdu (India)
    # te-IN	Telugu (India)
    # ta-IN	Tamil (India)
    # mr-IN	Marathi (India)
    # ml-IN	Malayalam (India)
    # kn-IN	Kannada (India)
    # gu-IN	Gujarati (India)
    # en-US English (USA)
speaker = 'hi-IN'


# en or hi
target = 'en'


class MicrophoneStream(object):
    """Opens a recording stream as a generator yielding the audio chunks."""
    def __init__(self, rate, chunk):
        self._rate = rate
        self._chunk = chunk

        #### Create a thread-safe buffer of audio data
        self._buff = queue.Queue()
        self.closed = True

    def __enter__(self):
        self._audio_interface = pyaudio.PyAudio()
        self._audio_stream = self._audio_interface.open(
            format=pyaudio.paInt16,
            # 1-channel (mono) audio
            
            channels=1, rate=self._rate,
            input=True, frames_per_buffer=self._chunk,
            # Run the audio stream asynchronously to fill the buffer object.
            stream_callback=self._fill_buffer,
        )

        self.closed = False

        return self

    def __exit__(self, type, value, traceback):
        self._audio_stream.stop_stream()
        self._audio_stream.close()
        self.closed = True
        # Signal the generator to terminate so that the client's
        # streaming_recognize method will not block the process termination.
        self._buff.put(None)
        self._audio_interface.terminate()

    def _fill_buffer(self, in_data, frame_count, time_info, status_flags):
        """Continuously collect data from the audio stream, into the buffer."""
        self._buff.put(in_data)
        return None, pyaudio.paContinue

    def generator(self):
        while not self.closed:
            # Use a blocking get() to ensure there's at least one chunk of
            # data, and stop iteration if the chunk is None, indicating the
            # end of the audio stream.
            chunk = self._buff.get()
            if chunk is None:
                return
            data = [chunk]

            # Now consume whatever other data's still buffered.
            while True:
                try:
                    chunk = self._buff.get(block=False)
                    if chunk is None:
                        return
                    data.append(chunk)
                except queue.Empty:
                    break

            yield b''.join(data)


def listen_print_loop(responses):

    num_chars_printed = 0
    for response in responses:
        
        if not response.results:
            continue

        # The `results` list is consecutive. For streaming, we only care about
        # the first result being considered, since once it's `is_final`, it
        # moves on to considering the next utterance.
        result = response.results[0]
        if not result.alternatives:
            continue

        # Display the transcription of the top alternative.
        transcript = result.alternatives[0].transcript

        # Display interim results, but with a carriage return at the end of the
        # line, so subsequent lines will overwrite them.
        #
        # If the previous result was longer than this one, we need to print
        # some extra spaces to overwrite the previous result
        overwrite_chars = ' ' * (num_chars_printed - len(transcript))

        if not result.is_final:
            sys.stdout.write(transcript + overwrite_chars + '\r')
            sys.stdout.flush()

            num_chars_printed = len(transcript)

        else:
            #### CREATE TRANSLATION
            translation = translate_client.translate(transcript,target_language=target)
  
            #### EXIT PHRASE
            if re.search(r'\b(exit conversation|quit)\b', transcript, re.I):
                print('Exiting Conversation..')
                ttsgoodbye = gTTS('it was great chatting with you, goodbye')
                ttsgoodbye.save('goodbye.mp3')
                goodbyesound = AudioSegment.from_file("goodbye.mp3", format="mp3")
                play(goodbyesound)
                break
                
            else:
                #### PRINT DATA
                print(u'Speaker In {}: '.format(translation['detectedSourceLanguage']), transcript + overwrite_chars)
                print(u'Translation: {}'.format(translation['translatedText']))
                print('\r')
                
                #### CREATE TRANSLATED MP3 & PLAY
                tts = gTTS(translation['translatedText'],lang=target)
                tts.save('translation.mp3')
                sound = AudioSegment.from_file("translation.mp3", format="mp3")
                play(sound)
                

            num_chars_printed = 0


def main():

    language_code = speaker  # a BCP-47 language tag

    client = speech.SpeechClient()
    config = types.RecognitionConfig(
        encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=RATE,
        language_code=language_code)
    streaming_config = types.StreamingRecognitionConfig(
        config=config,
        interim_results=True)

    with MicrophoneStream(RATE, CHUNK) as stream:
        audio_generator = stream.generator()
        requests = (types.StreamingRecognizeRequest(audio_content=content)
                    for content in audio_generator)

        responses = client.streaming_recognize(streaming_config, requests)

        # Put the transcription responses to use.
        listen_print_loop(responses)


if __name__ == '__main__':
    main()