"""
Jarvis-like Windows Assistant (single-file)

Features:
- Wake-word detection (simple keyword detection on recognized speech: "jarvis")
- Voice input (speech_recognition with Google Web Speech by default)
- Text-to-speech (pyttsx3 - offline)
- Open apps (edit the `APPS` dictionary with full paths)
- Open websites
- Shutdown / restart PC (Windows commands)
- Get current time & date
- Weather (OpenWeatherMap API; add your API key)
- Greeting on activation
- Basic error handling and logging

Notes / Requirements:
- This is a single-file, best-effort assistant suitable for Windows.
- You will need to install dependencies:
    pip install SpeechRecognition pyttsx3 requests psutil
  For microphone support on Windows you usually also need PyAudio:
    pip install pipwin
    pipwin install pyaudio
  or
    pip install pyaudio
  If installing PyAudio fails, follow the PyAudio Windows wheel instructions.

- By default the script uses the Google Web Speech API via the speech_recognition package.
  That requires an internet connection. If you need an offline recognizer, consider using
  VOSK and adapting this script.

- If you want a more robust/wakeword-first approach, integrate Picovoice Porcupine or Snowboy
  (Porcupine is commercial but offers a free tier for development). This script implements
  a pragmatic approach: continuous background recognition and activates when the recognized
  phrase contains the wake word "jarvis".

- Edit the APPS mapping to point to the executables on your PC.
- Add your OpenWeatherMap API key below in WEATHER_API_KEY.

Usage:
    python jarvis_assistant.py

"""

import os
import sys
import time
import json
import threading
import subprocess
import webbrowser
from datetime import datetime
from pathlib import Path

import customtkinter as ctk
from tkinter import scrolledtext
import tkinter as tk

import requests
import psutil

# For typing into applications
try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False

import speech_recognition as sr

try:
    from openai import OpenAI
    USE_DEEPSEEK = True
except ImportError:
    USE_DEEPSEEK = False

try:
    import sounddevice as sd
except ImportError:
    sd = None

# Try to use Windows SAPI for TTS (more reliable than pyttsx3)
try:
    import pyttsx3
    USE_PYTTSX3 = True
except ImportError:
    USE_PYTTSX3 = False

try:
    import win32com.client as winclient
    USE_WIN32COM = True
except ImportError:
    USE_WIN32COM = False

# ----------------------------- Configuration -----------------------------
WAKE_WORD = "jarvis"            # Word to trigger the assistant (lowercase)
LANG = "en-US"                  # Language for recognition
WEATHER_API_KEY = "bc832dc2b5b2995be35bae2ae2bd6f44"  # <-- Put your API key here
WEATHER_UNITS = "metric"        # metric or imperial

# Deepseek API Key - Get from https://platform.deepseek.com/
# Get your API key: https://platform.deepseek.com/api-keys
DEEPSEEK_API_KEY = ""  # Replace with your actual key starting with 'sk-'
USE_DEEPSEEK_CHAT = USE_DEEPSEEK and DEEPSEEK_API_KEY and DEEPSEEK_API_KEY.startswith("sk-")

# Initialize Deepseek client if API key is provided
deepseek_client = None
if USE_DEEPSEEK_CHAT:
    try:
        deepseek_client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
        print("[Init] Deepseek API integration enabled")
    except Exception as e:
        print(f"[Init] Deepseek initialization failed: {e}")
        USE_DEEPSEEK_CHAT = False
else:
    if not USE_DEEPSEEK:
        print("[Init] OpenAI library not installed. Install with: pip install openai")
    elif DEEPSEEK_API_KEY == "YOUR_DEEPSEEK_API_KEY_HERE":
        print("[Init] Deepseek API key not configured. Questions will not be answered.")
    try:
        deepseek_client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
        print("[Init] Deepseek ChatGPT integration enabled")
    except Exception as e:
        print(f"[Init] Deepseek initialization failed: {e}")
        USE_DEEPSEEK_CHAT = False

# Memory/Config file
MEMORY_FILE = Path(__file__).parent / "jarvis_memory.json"
USER_NAME = None  # Will be loaded from memory file

# Map friendly names to executable paths (edit to your installed apps)
APPS = {
    "notepad": r"C:\Windows\system32\notepad.exe",
    "calculator": r"C:\Windows\System32\calc.exe",
    "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "edge": r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "firefox": r"C:\Program Files\Mozilla Firefox\firefox.exe",
    "camera": r"C:\Windows\System32\WindowsCamera\WindowsCamera.exe",
    "spotify": r"C:\Users\anup0\AppData\Roaming\Spotify\spotify.exe",
    "discord": r"C:\Users\anup0\AppData\Local\Discord\app-1.0.9010\Discord.exe",
    "vlc": r"C:\Program Files\VideoLAN\VLC\vlc.exe",
    "steam": r"C:\Program Files (x86)\Steam\steam.exe",
    "settings": r"C:\Windows\System32\settings.exe",
    "task manager": r"C:\Windows\System32\taskmgr.exe",
    "word": r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.exe",
    "excel": r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.exe",
    "powerpoint": r"C:\Program Files\Microsoft Office\root\Office16\POWERPNT.exe",
    "paint": r"C:\Windows\System32\mspaint.exe",
    "file explorer": r"C:\Windows\explorer.exe",
}

# Websites that can be opened by friendly name
WEBSITES = {
    "google": "https://www.google.com",
    "youtube": "https://www.youtube.com",
    "github": "https://github.com",
    "facebook": "https://www.facebook.com",
    "twitter": "https://www.twitter.com",
    "instagram": "https://www.instagram.com",
    "reddit": "https://www.reddit.com",
}

# TTS engine setup
# We'll create fresh pyttsx3 engines in threads as needed
tts_engine = True if USE_PYTTSX3 else False
if USE_PYTTSX3:
    print("[Init] Using pyttsx3 for TTS (thread-safe mode)")
elif USE_WIN32COM:
    tts_engine = winclient.Dispatch("SAPI.SpVoice")
    print("[Init] Using Windows SAPI for TTS")
else:
    tts_engine = None
    print("[Init] No TTS engine available")

# Recognizer
recognizer = sr.Recognizer()

# Sounddevice config for audio capture
SAMPLE_RATE = 16000
CHUNK_DURATION = 2  # seconds per chunk
microphone_available = sd is not None

# Internal state
assistant_active = False
background_listener = None
should_stop = False  # Flag to stop mid-command
dictation_mode = False  # Flag to enable dictation/typing mode

# TTS lock to prevent concurrent calls
tts_lock = threading.Lock()

def tts_worker_thread_func(text):
    """Run TTS in a separate thread with proper locking"""
    global should_stop
    with tts_lock:
        try:
            print(f"[TTS] Speaking: {text}")
            if USE_PYTTSX3:
                # Create a fresh engine for this thread to avoid event loop issues
                print(f"[TTS] Creating fresh pyttsx3 engine...")
                engine = pyttsx3.init()
                engine.setProperty('rate', 160)
                engine.setProperty('volume', 1.0)
                print(f"[TTS] Engine created, calling say()...")
                engine.say(text)
                print(f"[TTS] Calling runAndWait()...")
                engine.runAndWait()
                # Check if we should stop - poll every 0.1 seconds during speech
                while engine.isBusy():
                    if should_stop:
                        print(f"[TTS] Stop requested during speech, stopping engine")
                        engine.stop()
                        break
                    time.sleep(0.1)
                print(f"[TTS] Finished speaking: {text}")
                del engine  # Clean up
            else:
                print("[TTS] Engine not available")
        except Exception as e:
            print(f"[TTS] Error: {type(e).__name__}: {e}")
        finally:
            should_stop = False  # Reset flag after speaking

# ----------------------------- Utilities ---------------------------------

def speak(text, block=True):
    """Speak the given text using TTS in a separate thread"""
    if not tts_engine:
        print(f"[TTS] No engine available")
        return
    
    # Don't speak error messages to user
    if "error" in text.lower() or "failed" in text.lower() or "could not" in text.lower():
        print(f"[TTS] Skipping error message (not speaking to user): {text}")
        return
    
    print(f"[TTS] speak() called with block={block}")
    thread = threading.Thread(target=tts_worker_thread_func, args=(text,), daemon=False)
    thread.start()
    
    if block:
        print(f"[TTS] Waiting for speech to finish...")
        thread.join()  # Wait for speech to finish
        print(f"[TTS] Speech finished.")
    
    # Add small delay after speaking to avoid picking up own voice
    time.sleep(0.5)


def get_time_str():
    now = datetime.now()
    return now.strftime("%I:%M %p")


def get_date_str():
    now = datetime.now()
    return now.strftime("%A, %B %d, %Y")


# ----------------------------- Memory Functions --------------------------

def load_memory():
    """Load saved memory (user name, preferences) from file."""
    global USER_NAME
    try: 
        if MEMORY_FILE.exists():
            with open(MEMORY_FILE, 'r') as f:
                memory = json.load(f)
                USER_NAME = memory.get('user_name')
                print(f"[Memory] Loaded user name: {USER_NAME}")
    except Exception as e:
        print(f"[Memory] Error loading memory: {e}")


def save_memory():
    """Save memory (user name, preferences) to file."""
    try:
        memory = {'user_name': USER_NAME}
        with open(MEMORY_FILE, 'w') as f:
            json.dump(memory, f)
        print(f"[Memory] Saved user name: {USER_NAME}")
    except Exception as e:
        print(f"[Memory] Error saving memory: {e}")


def ask_deepseek(question):
    """Ask Deepseek AI a question and get response (optimized for speed)."""
    if not USE_DEEPSEEK_CHAT or not deepseek_client:
        return "Deepseek API not configured. Please add your API key."
    
    try:
        print(f"[Deepseek] Asking: {question}")
        response = deepseek_client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are Jarvis, a helpful AI assistant. Keep responses very brief (1-2 sentences max) for voice output."},
                {"role": "user", "content": question}
            ],
            temperature=0.5,
            max_tokens=150,
            timeout=10
        )
        answer = response.choices[0].message.content
        print(f"[Deepseek] Response: {answer}")
        return answer
    except Exception as e:
        print(f"[Deepseek] Error: {e}")
        return f"Sorry, I encountered an error: {str(e)}"


def get_health_tips():
    """Get random health tips from a built-in collection or API."""
    health_tips = [
        "Drink at least 8 glasses of water daily to stay hydrated and maintain good health.",
        "Exercise for at least 30 minutes a day to improve cardiovascular health and mood.",
        "Get 7 to 9 hours of quality sleep each night for better cognitive function and immune health.",
        "Eat a balanced diet with plenty of fruits, vegetables, and whole grains.",
        "Practice meditation or deep breathing exercises to reduce stress and anxiety.",
        "Limit your intake of sugar and processed foods to maintain a healthy weight.",
        "Take regular breaks from screens to reduce eye strain and improve posture.",
        "Wash your hands frequently to prevent the spread of infections.",
        "Maintain a healthy BMI by combining diet and regular exercise.",
        "Spend time outdoors in natural sunlight for vitamin D and improved mental health.",
        "Keep your social connections strong, as they contribute to overall well-being.",
        "Limit alcohol consumption and avoid smoking for better health.",
        "Stay active throughout the day, even with light activities like walking.",
        "Include probiotics in your diet to support digestive health.",
        "Practice gratitude daily to improve mental health and happiness.",
        "Stretch regularly to improve flexibility and reduce muscle tension.",
        "Limit caffeine intake, especially in the evening, for better sleep.",
        "Eat foods rich in omega-3 fatty acids for brain and heart health.",
    ]
    
    import random
    tip = random.choice(health_tips)
    return tip


def get_news():
    """Fetch recent news headlines from NewsAPI."""
    try:
        # Using a free news API that doesn't require authentication for basic usage
        # Alternative: You can use newsapi.org with a free API key
        
        # Try using Google News RSS feed via a public API
        url = "https://newsapi.org/v2/top-headlines?country=us&sortBy=publishedAt&pageSize=5"
        # Using a demo key - replace with your own from https://newsapi.org/
        news_api_key = "demo"
        
        # If newsapi doesn't work, try alternative: BBC News or similar
        try:
            response = requests.get(f"{url}&apiKey={news_api_key}", timeout=8)
            if response.status_code == 200:
                data = response.json()
                if data.get('articles'):
                    headlines = []
                    for article in data['articles'][:3]:  # Get top 3 headlines
                        headline = article.get('title', 'No title')
                        headlines.append(headline)
                    
                    news_text = "Here are the latest news headlines: "
                    for i, headline in enumerate(headlines, 1):
                        news_text += f"Number {i}: {headline}. "
                    return news_text
        except Exception as e:
            print(f"NewsAPI error: {e}")
        
        # Fallback: provide some generic news
        fallback_news = "I couldn't fetch live news at this moment. Here are some tips: Stay informed by checking major news websites like BBC, CNN, or Reuters. Make sure to check reliable sources for accurate information."
        return fallback_news
        
    except Exception as e:
        print(f"News fetch error: {e}")
        return "I'm unable to fetch news at the moment. Please check a news website directly."


def get_weather(location="auto"):
    """Return a short weather summary for given location.
    location can be: city name ("London,UK"), lat,lon tuple string, or 'auto' to use IP geolocation.
    """
    if WEATHER_API_KEY == "YOUR_OPENWEATHERMAP_API_KEY_HERE":
        return "Weather API key not set. Please add your OpenWeatherMap API key in the script." 

    try:
        if location == "auto":
            # simple IP-based lookup (may not be precise)
            ipinfo = requests.get("https://ipinfo.io/json", timeout=5).json()
            city = ipinfo.get("city")
            if city:
                q = city
            else:
                q = "New York"
        else:
            q = location

        url = f"https://api.openweathermap.org/data/2.5/weather?q={q}&appid={WEATHER_API_KEY}&units={WEATHER_UNITS}"
        resp = requests.get(url, timeout=8)
        if resp.status_code != 200:
            return f"Could not fetch weather (HTTP {resp.status_code})."
        data = resp.json()
        desc = data['weather'][0]['description']
        temp = data['main']['temp']
        feels = data['main'].get('feels_like')
        unit = '°C' if WEATHER_UNITS == 'metric' else '°F'
        return f"{desc.capitalize()}, {temp}{unit} (feels like {feels}{unit}) in {data.get('name', q)}."
    except Exception as e:
        return f"Weather fetch error: {e}"


def open_app(name):
    global dictation_mode
    path = APPS.get(name.lower())
    if not path:
        return False, f"No app found for '{name}'. Edit the APPS mapping in the script."
    try:
        # Disable dictation for non-Notepad apps
        if name.lower() != "notepad":
            dictation_mode = False
            print("[DICTATION] Dictation mode disabled - opening app")
        
        subprocess.Popen(path)
        
        # Enable dictation mode ONLY for Notepad
        if name.lower() == "notepad":
            dictation_mode = True
            print("[DICTATION] Dictation mode enabled - speak to type in Notepad")
            time.sleep(2)  # Give Notepad time to open and focus
        
        return True, f"Opening {name}."
    except Exception as e:
        return False, f"Failed to open {name}: {e}"


def open_website(name_or_url):
    global dictation_mode
    
    # Disable dictation when opening websites
    dictation_mode = False
    print("[DICTATION] Dictation mode disabled - opening website")
    
    key = name_or_url.lower().strip()
    
    # Check if it's in WEBSITES dictionary
    if key in WEBSITES:
        url = WEBSITES[key]
        friendly_name = key
    else:
        # It's a direct URL or domain name
        if not (key.startswith('http://') or key.startswith('https://')):
            url = 'https://' + key
        else:
            url = key
        # Extract friendly name from URL for speech
        friendly_name = key.replace('https://', '').replace('http://', '').replace('www.', '').split('/')[0].replace('.com', '').replace('.org', '')
    
    try:
        webbrowser.open(url)
        return True, f"Opening {friendly_name}."
    except Exception as e:
        return False, f"Failed to open {friendly_name}: {e}"


def search_youtube(query):
    """Search for a video on YouTube and open it."""
    try:
        # URL-encode the search query
        from urllib.parse import quote
        encoded_query = quote(query)
        search_url = f"https://www.youtube.com/results?search_query={encoded_query}"
        print(f"[YouTube] Searching for: {query}")
        webbrowser.open(search_url)
        return True, f"Searching YouTube for {query}."
    except Exception as e:
        return False, f"Failed to search YouTube: {e}"


def search_spotify(query):
    """Search for a song/artist/playlist on Spotify and open it."""
    try:
        # First, try to open Spotify app
        spotify_path = APPS.get("spotify")
        if spotify_path:
            try:
                subprocess.Popen(spotify_path)
                print(f"[Spotify] Opening Spotify app...")
            except Exception as e:
                print(f"[Spotify] Could not open Spotify app: {e}")
        
        # URL-encode the search query
        from urllib.parse import quote
        encoded_query = quote(query)
        # Open Spotify search in web player
        search_url = f"https://open.spotify.com/search/{encoded_query}"
        print(f"[Spotify] Searching for: {query}")
        webbrowser.open(search_url)
        return True, f"Searching Spotify for {query}."
    except Exception as e:
        return False, f"Failed to search Spotify: {e}"


def shutdown_pc():
    """Shutdown the machine (Windows)."""
    try:
        # /s = shutdown, /t 5 = wait 5 seconds, /f = force close apps
        subprocess.Popen(["shutdown", "/s", "/t", "5", "/f"], shell=False)
        return True, "Shutting down the PC in 5 seconds."
    except Exception as e:
        return False, f"Shutdown failed: {e}"


def restart_pc():
    try:
        # /r = restart, /t 5 = wait 5 seconds, /f = force close apps
        subprocess.Popen(["shutdown", "/r", "/t", "5", "/f"], shell=False)
        return True, "Restarting the PC in 5 seconds."
    except Exception as e:
        return False, f"Restart failed: {e}"


# ----------------------------- Command Handling --------------------------

def handle_command(command_text):
    text = command_text.lower()
    print(f"Command received: '{text}'")
    print(f"Debug - 'time' in text: {'time' in text}, 'date' in text: {'date' in text}")

    # Self-introduction commands
    if any(w in text for w in ["who are you", "what is your name", "tell me about yourself", "introduce yourself"]):
        msg = "I am Jarvis, your personal AI assistant. I can help you with time, date, opening apps, websites, and answering questions."
        print(f"Speaking: {msg}")
        speak(msg)
        return

    # How are you
    if "how are" in text:
        if USER_NAME:
            msg = f"I am doing great, {USER_NAME}! How can I assist you?"
        else:
            msg = "I am doing great! How can I assist you?"
        print(f"Speaking: {msg}")
        speak(msg)
        return

    # Time and date commands
    if "time" in text and "date" in text:
        msg = f"Today is {get_date_str()} and the time is {get_time_str()}."
        print(f"Speaking: {msg}")
        speak(msg)
        return

    if "time" in text:
        msg = f"The time is {get_time_str()}."
        print(f"Speaking: {msg}")
        speak(msg)
        return

    if "date" in text:
        msg = f"Today is {get_date_str()}."
        print(f"Speaking: {msg}")
        speak(msg)
        return

    # Remember my name commands
    if "remember my name" in text or "my name is" in text:
        # Extract name after "my name is"
        if "my name is" in text:
            name = text.split("my name is", 1)[1].strip().rstrip('.')
            if name:
                globals()['USER_NAME'] = name
                save_memory()
                msg = f"Nice to meet you, {name}. I will remember your name."
                speak(msg)
                return
        speak("I didn't catch your name. Please tell me again.")
        return

    # Greet with user's name
    if any(w in text for w in ["hello", "hi", "hey"]):
        if USER_NAME:
            msg = f"Hello, {USER_NAME}!"
        else:
            msg = "Hello! What's your name?"
        speak(msg)
        return

    # Health tips command
    if any(w in text for w in ["health tip", "health advice", "health tips", "give me a health tip", "tell me a health tip"]):
        tip = get_health_tips()
        print(f"Speaking: {tip}")
        speak(tip)
        return

    # News command
    if any(w in text for w in ["news", "latest news", "tell me the news", "what's in the news", "recent news", "today's news"]):
        news = get_news()
        print(f"Speaking: {news}")
        speak(news)
        return

    # shutdown command
    if "shutdown" in text:
        ok, msg = shutdown_pc()
        speak(msg)
        return

    # restart command (check before "start" keyword since "restart" contains "start")
    if "restart" in text or "reboot" in text:
        ok, msg = restart_pc()
        speak(msg)
        return

    # Spotify search command
    if "spotify" in text and any(w in text for w in ["search", "play", "find", "look for", "listen"]):
        # Extract the search query
        search_query = None
        
        # Pattern 1: "search spotify for X"
        if "search spotify for" in text:
            search_query = text.split("search spotify for", 1)[1].strip()
        # Pattern 2: "search for X on spotify"
        elif "search for" in text and "spotify" in text:
            search_query = text.split("search for", 1)[1].split("on spotify")[0].split("spotify")[0].strip()
        # Pattern 3: "play X on spotify" or "play X spotify"
        elif "play" in text and "spotify" in text:
            search_query = text.split("play", 1)[1].split("on spotify")[0].split("spotify")[0].strip()
        # Pattern 4: "find X on spotify"
        elif "find" in text and "spotify" in text:
            search_query = text.split("find", 1)[1].split("on spotify")[0].split("spotify")[0].strip()
        # Pattern 5: "listen to X on spotify"
        elif "listen to" in text and "spotify" in text:
            search_query = text.split("listen to", 1)[1].split("on spotify")[0].split("spotify")[0].strip()
        # Pattern 6: "spotify X"
        elif "spotify" in text:
            parts = text.split("spotify")
            if len(parts) > 1 and parts[1].strip():
                search_query = parts[1].strip()
        
        if search_query:
            ok, msg = search_spotify(search_query)
            speak(msg)
            return
        else:
            speak("What would you like me to search for on Spotify?")
            return

    # YouTube search command
    if "youtube" in text and any(w in text for w in ["search", "play", "find", "look for"]):
        # Extract the search query
        search_query = None
        
        # Pattern 1: "search youtube for X"
        if "search youtube for" in text:
            search_query = text.split("search youtube for", 1)[1].strip()
        # Pattern 2: "search for X on youtube"
        elif "search for" in text and "youtube" in text:
            search_query = text.split("search for", 1)[1].split("on youtube")[0].split("youtube")[0].strip()
        # Pattern 3: "play X on youtube" or "play X youtube"
        elif "play" in text and "youtube" in text:
            search_query = text.split("play", 1)[1].split("on youtube")[0].split("youtube")[0].strip()
        # Pattern 4: "find X on youtube"
        elif "find" in text and "youtube" in text:
            search_query = text.split("find", 1)[1].split("on youtube")[0].split("youtube")[0].strip()
        # Pattern 5: "youtube X"
        elif "youtube" in text:
            parts = text.split("youtube")
            if len(parts) > 1 and parts[1].strip():
                search_query = parts[1].strip()
        
        if search_query:
            ok, msg = search_youtube(search_query)
            speak(msg)
            return
        else:
            speak("What would you like me to search for on YouTube?")
            return

    if any(w in text for w in ["open", "launch", "start"]):
        # Try to open an app or website - extract the target after the verb
        words = text.split()
        target = None
        for kw in ["open", "launch", "start"]:
            if kw in words:
                idx = words.index(kw)
                if idx + 1 < len(words):
                    target = ' '.join(words[idx+1:]).strip()
                break

        if not target:
            speak("What should I open?")
            return

        # Normalize the target
        tgt = target.replace('the ', '').replace('app ', '').strip()
        
        # Check if it's a website (has dots or known website keywords)
        if '.' in tgt or any(w in tgt for w in ['google', 'youtube', 'facebook', 'twitter', 'github', 'instagram']):
            print(f"Opening website: {tgt}")
            ok, msg = open_website(tgt)
        else:
            # Try to open as app
            print(f"Opening app: {tgt}")
            ok, msg = open_app(tgt)
        
        speak(msg)
        return

    # Dictation mode control
    if "stop dictation" in text or "stop typing" in text or "exit dictation" in text:
        global dictation_mode
        dictation_mode = False
        print("[DICTATION] Dictation mode disabled")
        speak("Dictation mode stopped.")
        return

    # exit commands
    if any(w in text for w in ["stop", "exit", "quit", "goodbye", "bye"]):
        speak("Goodbye.")
        sys.exit(0)
    
    # Use Deepseek for any unknown commands/questions
    if USE_DEEPSEEK_CHAT:
        print("Using Deepseek to answer question...")
        answer = ask_deepseek(text)
        speak(answer)
        return
    
    # Unknown command - do nothing
    print("Command not recognized.")


# ----------------------------- Audio Processing --------------------------

def enhance_low_frequency_audio(audio_data):
    """Enhance low-frequency content in audio for better bass/low-pitch detection."""
    import numpy as np
    
    try:
        # Convert to float for processing
        audio_float = audio_data.astype(float)
        
        # Normalize to prevent clipping
        max_val = np.max(np.abs(audio_float))
        if max_val > 0:
            audio_float = audio_float / max_val
        
        # Apply low-frequency emphasis filter
        enhanced = audio_float.copy()
        for i in range(1, len(enhanced)):
            enhanced[i] = 0.7 * enhanced[i] + 0.3 * enhanced[i-1]
        
        # Scale back to int16 range
        enhanced = (enhanced * 32767).astype('int16')
        return enhanced
    except Exception as e:
        print(f"[Audio] Low-frequency enhancement failed: {e}")
        return audio_data


def detect_low_frequency_amplitude(audio_data):
    """Detect amplitude in low-frequency range (bass detection)."""
    import numpy as np
    
    try:
        audio_float = audio_data.astype(float)
        rms = np.sqrt(np.mean(audio_float ** 2))
        return int(rms)
    except:
        return int(abs(audio_data).max())


# ----------------------------- Main ------------------------------------
def listen_for_wakeword_and_command():
    """Listen for commands with enhanced sensitivity for low-pitch sounds."""
    global should_stop
    if not microphone_available:
        return
    
    try:
        # Record for 3 seconds to capture complete phrases
        duration = 3
        print("Listening for command...")
        audio_data = sd.rec(int(SAMPLE_RATE * duration), samplerate=SAMPLE_RATE, channels=1, dtype='int16')
        sd.wait()
        
        # Detect amplitude using RMS (better for low frequencies)
        rms_amplitude = detect_low_frequency_amplitude(audio_data)
        max_amplitude = abs(audio_data).max()
        
        # Skip only if completely silent - very lenient for low-pitch detection
        if max_amplitude < 150 and rms_amplitude < 100:
            return
        
        # Enhance low-frequency content
        audio_data = enhance_low_frequency_audio(audio_data)
        
        # Amplify quiet audio for better recognition
        if max_amplitude < 8000:
            # Stronger amplification for quiet audio
            audio_data = (audio_data.astype(float) * (10000.0 / max(max_amplitude, 1))).astype('int16')
            print(f"[Audio] Amplified audio (max: {max_amplitude}, RMS: {rms_amplitude})")
        
        audio = sr.AudioData(audio_data.tobytes(), SAMPLE_RATE, 2)
    except Exception as e:
        print(f"Recording error: {e}")
        return
    
    try:
        text = recognize_with_fallback(audio)
        if not text:
            return
        print(f"Heard: {text}")
        
        # Check if user wants to stop current speech
        if any(w in text.lower() for w in ["stop", "stop talking", "stop speaking", "be quiet", "shush"]):
            should_stop = True  # Signal TTS to stop
            print("Stop signal received")
            return  # Don't process as command, just stop current speech
        
        # Check if user wants to exit
        if any(w in text.lower() for w in ["exit", "quit", "goodbye", "bye"]):
            speak("Goodbye.", block=False)
            return
        
        # Process command directly - no wake word needed
        handle_command(text)
        
    except sr.UnknownValueError:
        print("Could not understand audio.")
        return  # Continue listening
    except sr.RequestError as e:
        print(f"Recognition error: {e}")
        return  # Continue listening
    except Exception as e:
        print(f"Error: {e}")
        return  # Continue listening


def main():
    # Load saved memory first
    load_memory()
    
    if USER_NAME:
        greeting = f"Welcome back, {USER_NAME}. Jarvis ready to help. Just speak your command."
    else:
        greeting = "Jarvis ready to help. Just speak your command."
    
    speak(greeting, block=False)
    try:
        if not microphone_available:
            print("Sounddevice not available. Falling back to typed commands.")
            while True:
                cmd = input("Type command (or 'exit'): ").strip()
                if not cmd:
                    continue
                if cmd.lower() in ("exit", "quit"):
                    print("Exiting.")
                    break
                handle_command(cmd)
        else:
            while True:
                listen_for_wakeword_and_command()
                time.sleep(0.01)  # Minimal delay for max speed
    except KeyboardInterrupt:
        print("Exiting.")
        sys.exit(0)
import tkinter as tk
from tkinter import scrolledtext
import threading
import time



class JarvisGUI:
    def __init__(self):
        self.listening_active = False
        self.wave_cycle = 0
        self.wave_chars = ['▁', '▂', '▃', '▄', '▅', '▆', '▇', '█', '▇', '▆', '▅', '▄', '▃', '▂']
        self.listening_mode = "wake"  # "wake" or "command"
        self.create_window()
        # Show startup greeting
        self.show_startup_greeting()
        # Auto-start listening after greeting
        self.root.after(2000, self.auto_start_listening)
        
    def create_window(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.root = ctk.CTk()
        self.root.title("Jarvis AI Assistant")
        self.root.geometry("1000x800")
        self.root.resizable(True, True)
        
        # Main container with gradient-like background
        main_frame = ctk.CTkFrame(self.root, fg_color="#0a0e27")
        main_frame.pack(fill="both", expand=True, padx=0, pady=0)
        
        # Header with logo/title
        header_frame = ctk.CTkFrame(main_frame, fg_color="#0f1419")
        header_frame.pack(fill="x", padx=0, pady=0)
        
        title = ctk.CTkLabel(
            header_frame,
            text="🤖 JARVIS",
            font=("Helvetica", 32, "bold"),
            text_color="#ffffff"
        )
        title.pack(pady=20)
        
        # Chat Display - Modern card style
        chat_frame = ctk.CTkFrame(main_frame, fg_color="#1a1f3a", corner_radius=20)
        chat_frame.pack(padx=30, pady=20, fill="both", expand=True)
        
        self.chat_display = scrolledtext.ScrolledText(
            chat_frame,
            wrap=tk.WORD,
            width=100,
            height=25,
            font=("Segoe UI", 10),
            bg="#0d1117",
            fg="#e0e6ed",
            insertbackground="#4f92ff",
            relief=tk.FLAT,
            borderwidth=0
        )
        self.chat_display.pack(fill="both", expand=True, padx=15, pady=15)
        self.chat_display.config(state=tk.DISABLED)
        
        # Input Section with gradient background
        input_section = ctk.CTkFrame(main_frame, fg_color="#1a1f3a", corner_radius=20)
        input_section.pack(padx=30, pady=20, fill="x")
        
        # Text input
        input_label = ctk.CTkLabel(
            input_section,
            text="💬 Type or speak",
            font=("Segoe UI", 11, "bold"),
            text_color="#ffffff"
        )
        input_label.pack(anchor="w", padx=15, pady=(15, 5))
        
        input_sub_frame = ctk.CTkFrame(input_section, fg_color="transparent")
        input_sub_frame.pack(padx=15, pady=5, fill="x")
        
        self.input_box = ctk.CTkEntry(
            input_sub_frame,
            placeholder_text="Type your command here...",
            font=("Segoe UI", 11),
            text_color="#ffffff",
            fg_color="#0a0e27",
            border_color="#404854",
            border_width=2,
            corner_radius=8,
            height=40
        )
        self.input_box.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.send_btn = ctk.CTkButton(
            input_sub_frame,
            text="📤",
            command=self.send_text_command,
            width=45,
            height=40,
            font=("Segoe UI", 16),
            fg_color="#4f92ff",
            hover_color="#6ba3ff",
            corner_radius=8
        )
        self.send_btn.pack(side="left")
        
        # Bind Enter key to send command
        self.input_box.bind("<Return>", lambda e: self.send_text_command())
        
        # Control Buttons Frame - Modern button design
        button_section = ctk.CTkFrame(input_section, fg_color="transparent")
        button_section.pack(padx=0, pady=(10, 15), fill="x")
        
        # Start Button
        self.start_btn = ctk.CTkButton(
            button_section,
            text="🎙 Start Listening",
            command=self.start_listening,
            width=150,
            height=38,
            font=("Segoe UI", 11, "bold"),
            fg_color="#22863a",
            hover_color="#2ea043",
            corner_radius=8
        )
        self.start_btn.pack(side="left", padx=5)
        
        # Stop Button
        self.stop_btn = ctk.CTkButton(
            button_section,
            text="⏹ Stop",
            command=self.stop_listening,
            width=100,
            height=38,
            font=("Segoe UI", 11, "bold"),
            fg_color="#da3633",
            hover_color="#f85149",
            state="disabled",
            corner_radius=8
        )
        self.stop_btn.pack(side="left", padx=5)
        
        # Clear Button
        self.clear_btn = ctk.CTkButton(
            button_section,
            text="🗑 Clear",
            command=self.clear_chat,
            width=100,
            height=38,
            font=("Segoe UI", 11, "bold"),
            fg_color="#404854",
            hover_color="#565f69",
            corner_radius=8
        )
        self.clear_btn.pack(side="left", padx=5)
        
        # Exit Button
        self.exit_btn = ctk.CTkButton(
            button_section,
            text="❌ Exit",
            command=self.root.quit,
            width=100,
            height=38,
            font=("Segoe UI", 11, "bold"),
            fg_color="#444c56",
            hover_color="#565f69",
            corner_radius=8
        )
        self.exit_btn.pack(side="right", padx=5)
        
        # Status Label with Wave Animation - Bottom bar
        status_frame = ctk.CTkFrame(main_frame, fg_color="#0f1419", corner_radius=0)
        status_frame.pack(fill="x", padx=0, pady=0)
        
        self.status_label = ctk.CTkLabel(
            status_frame,
            text="Status: Ready",
            font=("Segoe UI", 10),
            text_color="#8b949e"
        )
        self.status_label.pack(side="left", padx=20, pady=12)
        
        self.wave_label = ctk.CTkLabel(
            status_frame,
            text="",
            font=("Segoe UI", 12),
            text_color="#4f92ff"
        )
        self.wave_label.pack(side="right", padx=20, pady=12)
    
    def send_text_command(self):
        """Send text command from input box"""
        text = self.input_box.get().strip()
        if text:
            self.add_message("You", text)
            self.input_box.delete(0, "end")
            handle_command_gui(text, self)
    
    def update_wave_animation(self):
        """Update the wave animation"""
        if self.listening_active:
            wave = " ".join([self.wave_chars[self.wave_cycle]] * 8)
            self.wave_label.configure(text=wave)
            self.wave_cycle = (self.wave_cycle + 1) % len(self.wave_chars)
            self.root.after(100, self.update_wave_animation)
        else:
            self.wave_label.configure(text="")
    
    def show_startup_greeting(self):
        """Show greeting on startup"""
        if USER_NAME:
            greeting = f"Welcome back {USER_NAME}. Ready to help!"
        else:
            greeting = "Welcome. I'm Jarvis. Ready to help!"
        
        self.add_message("Jarvis", greeting)
        # Speak greeting in a non-blocking way
        threading.Thread(target=lambda: speak(greeting, block=False), daemon=True).start()
    
    def auto_start_listening(self):
        """Automatically start listening after startup greeting"""
        if not self.listening_active:
            self.start_listening()
    
    def add_message(self, sender, message):
        """Add message to chat display with Gemini-like styling"""
        self.chat_display.config(state=tk.NORMAL)
        timestamp = datetime.now().strftime("%H:%M")
        
        # Format message based on sender
        if sender == "You":
            formatted = f"You ({timestamp}): {message}\n\n"
            self.chat_display.insert(tk.END, formatted)
            # Color user messages blue
            start_idx = self.chat_display.index(f"end-{len(formatted)+1}c")
            self.chat_display.tag_add("user", start_idx, "end-1c")
        elif sender == "Jarvis":
            formatted = f"Jarvis ({timestamp}): {message}\n\n"
            self.chat_display.insert(tk.END, formatted)
            # Color Jarvis messages green
            start_idx = self.chat_display.index(f"end-{len(formatted)+1}c")
            self.chat_display.tag_add("jarvis", start_idx, "end-1c")
        else:
            formatted = f"[{sender}] {message}\n\n"
            self.chat_display.insert(tk.END, formatted)
            # Color system messages gray
            start_idx = self.chat_display.index(f"end-{len(formatted)+1}c")
            self.chat_display.tag_add("system", start_idx, "end-1c")
        
        # Configure tags
        self.chat_display.tag_config("user", foreground="#4f92ff")
        self.chat_display.tag_config("jarvis", foreground="#22863a")
        self.chat_display.tag_config("system", foreground="#8b949e")
        
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.yview(tk.END)
    
    def clear_chat(self):
        """Clear chat display"""
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.delete(1.0, tk.END)
        self.chat_display.config(state=tk.DISABLED)
    
    def update_status(self, status):
        """Update status label"""
        # Determine what to show based on listening mode
        if self.listening_active:
            display_text = f"Status: Listening for command..."
        else:
            display_text = f"Status: {status}"
        
        self.status_label.configure(text=display_text)
        self.root.update()
    
    def start_listening(self):
        """Start listening for commands"""
        global should_stop
        if not self.listening_active:
            should_stop = False  # Reset stop flag
            self.listening_active = True
            self.wave_cycle = 0
            self.start_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")
            self.update_status("Listening...")
            self.add_message("System", "Started listening for commands")
            
            # Start wave animation
            self.update_wave_animation()
            
            threading.Thread(target=self.listen_loop, daemon=True).start()
    
    def stop_listening(self):
        """Stop listening"""
        self.listening_active = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.update_status("Stopped")
        self.add_message("System", "Stopped listening")
    
    def listen_loop(self):
        """Main listening loop"""
        try:
            while self.listening_active:
                listen_for_wakeword_and_command_gui(self)
        except Exception as e:
            self.add_message("Error", str(e))
            self.stop_listening()
    
    def run(self):
        """Start GUI"""
        self.root.mainloop()


def handle_command_gui(command_text, gui):
    """Handle command with GUI feedback"""
    text = command_text.lower()
    response = None
    
    # Self-introduction commands
    if any(w in text for w in ["who are you", "what is your name", "tell me about yourself", "introduce yourself"]):
        response = "I am Jarvis, your personal AI assistant. I can help you with time, date, opening apps, websites, and answering questions."
    
    # How are you
    elif "how are" in text:
        if USER_NAME:
            response = f"I am doing great, {USER_NAME}! How can I assist you?"
        else:
            response = "I am doing great! How can I assist you?"
    
    # Time and date commands
    elif "time" in text and "date" in text:
        response = f"Today is {get_date_str()} and the time is {get_time_str()}."
    elif "time" in text:
        response = f"The time is {get_time_str()}."
    elif "date" in text:
        response = f"Today is {get_date_str()}."
    
    # Remember my name
    elif "remember my name" in text or "my name is" in text:
        if "my name is" in text:
            name = text.split("my name is", 1)[1].strip().rstrip('.')
            if name:
                globals()['USER_NAME'] = name
                save_memory()
                response = f"Nice to meet you, {name}. I will remember your name."
        else:
            response = "I didn't catch your name. Please tell me again."
    
    # Greet
    elif any(w in text for w in ["hello", "hi", "hey"]):
        if USER_NAME:
            response = f"Hello, {USER_NAME}!"
        else:
            response = "Hello! What's your name?"
    
    # Health tips command
    elif any(w in text for w in ["health tip", "health advice", "health tips", "give me a health tip", "tell me a health tip"]):
        response = get_health_tips()
    
    # News command
    elif any(w in text for w in ["news", "latest news", "tell me the news", "what's in the news", "recent news", "today's news"]):
        response = get_news()
    
    # Spotify search command
    elif "spotify" in text and any(w in text for w in ["search", "play", "find", "look for", "listen"]):
        search_query = None
        if "search spotify for" in text:
            search_query = text.split("search spotify for", 1)[1].strip()
        elif "search for" in text and "spotify" in text:
            search_query = text.split("search for", 1)[1].split("on spotify")[0].split("spotify")[0].strip()
        elif "play" in text and "spotify" in text:
            search_query = text.split("play", 1)[1].split("on spotify")[0].split("spotify")[0].strip()
        elif "find" in text and "spotify" in text:
            search_query = text.split("find", 1)[1].split("on spotify")[0].split("spotify")[0].strip()
        elif "listen to" in text and "spotify" in text:
            search_query = text.split("listen to", 1)[1].split("on spotify")[0].split("spotify")[0].strip()
        elif "spotify" in text:
            parts = text.split("spotify")
            if len(parts) > 1 and parts[1].strip():
                search_query = parts[1].strip()
        
        if search_query:
            ok, response = search_spotify(search_query)
        else:
            response = "What would you like me to search for on Spotify?"
    
    # YouTube search command
    elif "youtube" in text and any(w in text for w in ["search", "play", "find", "look for"]):
        search_query = None
        if "search youtube for" in text:
            search_query = text.split("search youtube for", 1)[1].strip()
        elif "search for" in text and "youtube" in text:
            search_query = text.split("search for", 1)[1].split("on youtube")[0].split("youtube")[0].strip()
        elif "play" in text and "youtube" in text:
            search_query = text.split("play", 1)[1].split("on youtube")[0].split("youtube")[0].strip()
        elif "find" in text and "youtube" in text:
            search_query = text.split("find", 1)[1].split("on youtube")[0].split("youtube")[0].strip()
        elif "youtube" in text:
            parts = text.split("youtube")
            if len(parts) > 1 and parts[1].strip():
                search_query = parts[1].strip()
        
        if search_query:
            ok, response = search_youtube(search_query)
        else:
            response = "What would you like me to search for on YouTube?"
    
    # Shutdown
    elif "shutdown" in text:
        ok, response = shutdown_pc()
    
    # Restart
    elif "restart" in text or "reboot" in text:
        ok, response = restart_pc()
    
    # Open apps/websites
    elif any(w in text for w in ["open", "launch", "start"]):
        words = text.split()
        target = None
        for kw in ["open", "launch", "start"]:
            if kw in words:
                idx = words.index(kw)
                if idx + 1 < len(words):
                    target = ' '.join(words[idx+1:]).strip()
                break
        
        if not target:
            response = "What should I open?"
        else:
            tgt = target.replace('the ', '').replace('app ', '').strip()
            if '.' in tgt or any(w in tgt for w in ['google', 'youtube', 'facebook', 'twitter', 'github', 'instagram', 'reddit']):
                ok, response = open_website(tgt)
            else:
                ok, response = open_app(tgt)
    
    # Exit
    elif any(w in text for w in ["stop", "exit", "quit", "goodbye", "bye"]):
        global should_stop
        should_stop = True
        response = "Stopped."
        gui.add_message("Jarvis", response)
        speak(response, block=False)
        return
    
    # Use Deepseek for unknown questions
    elif USE_DEEPSEEK_CHAT:
        response = ask_deepseek(text)
    
    else:
        response = "I didn't understand that. Can you repeat?"
    
    # Display and speak response
    if response:
        gui.add_message("Jarvis", response)
        speak(response, block=False)


def listen_for_wakeword_and_command_gui(gui):
    """Listen for commands directly - no wake word needed (GUI version, simplified)"""
    global should_stop
    if not microphone_available:
        return
    
    try:
        gui.update_status("Listening for command...")
        
        # Ultra-fast listening - 2 seconds (ultra-sensitive for quiet voice)
        duration = 2
        audio_data = sd.rec(int(SAMPLE_RATE * duration), samplerate=SAMPLE_RATE, channels=1, dtype='int16')
        sd.wait()
        
        # Skip if silent (very low threshold to catch quiet speech)
        if audio_data.max() < 300:
            return
        
        # Skip if very loud (likely feedback from own voice/speaker)
        if audio_data.max() > 30000:
            print(f"[LISTEN] Skipping loud audio (likely speaker feedback): {audio_data.max()}")
            return
        
        audio = sr.AudioData(audio_data.tobytes(), SAMPLE_RATE, 2)
        
        text = recognizer.recognize_google(audio, language=LANG)
        print(f"[LISTEN] Heard: '{text}'")
        
        # If in dictation mode, type the text instead of processing as command
        if dictation_mode:
            print(f"[DICTATION] Typing: {text}")
            if PYAUTOGUI_AVAILABLE:
                try:
                    # Use clipboard method for better Unicode support (works for Hindi, etc.)
                    import subprocess
                    # Copy text to clipboard
                    process = subprocess.Popen(['powershell', '-Command', f'Set-Clipboard -Value "{text} "'], 
                                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    process.communicate()
                    
                    # Small delay to ensure clipboard is set
                    time.sleep(0.2)
                    
                    # Paste from clipboard
                    pyautogui.hotkey('ctrl', 'v')
                    print(f"[DICTATION] Pasted to Notepad")
                except Exception as e:
                    print(f"[DICTATION] Error typing: {e}")
                    # Fallback: try direct typing
                    try:
                        pyautogui.write(text + " ", interval=0.02)
                    except:
                        print("[DICTATION] Could not type text")
            else:
                print("[DICTATION] pyautogui not available. Install with: pip install pyautogui")
            return
        
        # Display what was heard
        gui.add_message("You", text)
        
        # Check if user wants to stop current speech
        if any(w in text.lower() for w in ["stop", "stop talking", "stop speaking", "be quiet", "shush"]):
            should_stop = True  # Signal TTS to stop
            print("Stop signal received")
            return  # Don't process as command, just stop current speech
        
        # Check if user wants to exit
        if any(w in text.lower() for w in ["exit", "quit", "goodbye", "bye"]):
            gui.add_message("Jarvis", "Goodbye.")
            speak("Goodbye.", block=False)
        else:
            # Process command directly - no wake word needed
            handle_command_gui(text, gui)
        
        gui.update_status("Listening for command...")
    except sr.UnknownValueError:
        print("Could not understand audio")
        return  # Continue listening
    except sr.RequestError as e:
        print(f"Recognition error: {e}")
        return  # Continue listening, don't show error in chat
    except Exception as e:
        print(f"Error: {e}")
        return  # Continue listening, don't show error in chat


if __name__ == '__main__':
    gui = JarvisGUI()
    gui.run()    