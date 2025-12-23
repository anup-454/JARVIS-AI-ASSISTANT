"""Test microphone audio levels and speech recognition"""

import sounddevice as sd
import numpy as np
import speech_recognition as sr

SAMPLE_RATE = 16000

print("=" * 60)
print("🎤 MICROPHONE TEST")
print("=" * 60)

# Test 1: Record and display audio levels
print("\n[TEST 1] Recording 3 seconds of audio...")
print("Please speak clearly into your microphone!\n")

audio_data = sd.rec(int(SAMPLE_RATE * 3), samplerate=SAMPLE_RATE, channels=1, dtype='int16')
sd.wait()

audio_level = audio_data.max()
print(f"Audio Level: {audio_level}")
print(f"Status: ", end="")

if audio_level < 200:
    print("❌ TOO QUIET - Speak louder or move microphone closer")
elif audio_level < 300:
    print("⚠️  VERY QUIET - Try speaking louder")
elif audio_level < 1000:
    print("⚠️  QUIET - Could be better")
elif audio_level < 25000:
    print("✅ GOOD - Audio level is good!")
else:
    print("⚠️  TOO LOUD - Reduce microphone sensitivity")

# Test 2: Speech Recognition
print("\n[TEST 2] Testing speech recognition...")
print("Trying to understand what you said...\n")

try:
    recognizer = sr.Recognizer()
    audio = sr.AudioData(audio_data.tobytes(), SAMPLE_RATE, 2)
    
    text = recognizer.recognize_google(audio, language="en-US")
    print(f"✅ SUCCESS! Recognized: '{text}'")
except sr.UnknownValueError:
    print("❌ Could not understand audio")
    print("   Try speaking more clearly or louder")
except sr.RequestError as e:
    print(f"❌ Recognition error: {e}")
    print("   Check your internet connection")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 60)
print("TROUBLESHOOTING:")
print("- If audio level is too low: Speak louder, move mic closer")
print("- If recognition fails: Check internet, speak clearly")
print("- If too loud: Reduce microphone input volume in Windows")
print("=" * 60)
