#!/usr/bin/env python3
"""Simple TTS test"""
import pyttsx3

engine = pyttsx3.init()
engine.setProperty('rate', 160)
engine.setProperty('volume', 1.0)

print("Testing pyttsx3 TTS...")
engine.say("Hello, this is a test")
engine.runAndWait()
print("Done!")
