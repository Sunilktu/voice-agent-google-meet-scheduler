# voice_io.py
import os
import asyncio
import speech_recognition as sr
from gtts import gTTS
from pydub import AudioSegment # Changed: Using pydub for audio segment manipulation
from pydub.playback import play # Changed: Using pydub for audio playback

# Recognizer instance for STT
r = sr.Recognizer()

async def get_voice_input() -> str:
    """Captures voice input from the microphone and converts it to text."""
    with sr.Microphone() as source:
        print("\nSay something!")
        r.adjust_for_ambient_noise(source) # Adjust for ambient noise
        try:
            audio = await asyncio.to_thread(r.listen, source, timeout=10, phrase_time_limit=10) # Listen for up to 5 seconds
            print("Recognizing...")
            text = await asyncio.to_thread(r.recognize_google, audio) # Use Google Web Speech API
            print(f"You said: {text}")
            return text
        except sr.WaitTimeoutError:
            print("No speech detected. Please try again.")
            return ""
        except sr.UnknownValueError:
            print("Could not understand audio. Please try again.")
            return ""
        except sr.RequestError as e:
            print(f"Could not request results from Google Speech Recognition service; {e}")
            return ""
        except Exception as e:
            print(f"An unexpected error occurred during voice input: {e}")
            return ""

async def speak_text(text: str):
    """Converts text to speech and plays it using gTTS and pydub."""
    if not text:
        return
    print(f"Bot speaking: {text}")
    try:
        tts = gTTS(text=text, lang='en')
        audio_file = "bot_response.mp3"
        
        # Save the gTTS output to a temporary MP3 file
        await asyncio.to_thread(tts.save, audio_file)
        
        # Load the MP3 file using pydub
        audio = AudioSegment.from_file(audio_file, format="mp3")
        
        # Play the AudioSegment using pydub's playback.play
        # This will use ffplay (from FFmpeg) for MP3 playback.
        await asyncio.to_thread(play, audio)
        
        os.remove(audio_file) # Clean up the temporary file
    except Exception as e:
        print(f"Error during text-to-speech or playback: {e}")
        print("Please ensure FFmpeg is installed and accessible in your system's PATH for MP3 playback with pydub.")

