# 🤖 Jarvis AI Assistant (Python)

Jarvis is a **Windows-based AI Voice Assistant** built using Python.
It can listen to voice commands, respond using text-to-speech, open applications and websites, provide weather updates, fetch news, and even interact through a modern GUI.

This project is inspired by the concept of a personal desktop assistant like *Iron Man’s Jarvis*.

---

## ✨ Features

* 🎙 Voice command recognition
* 🔊 Text-to-speech (offline support)
* 🖥 Open desktop applications (Notepad, Chrome, Spotify, etc.)
* 🌐 Open websites (Google, YouTube, GitHub, etc.)
* 🕒 Tell current **time & date**
* 🌦 Live **weather updates** (OpenWeatherMap API)
* 📰 Latest **news headlines**
* ❤️ Health tips
* 💬 Chat-based **GUI interface**
* 🧠 Memory support (remembers user name)
* 🤖 AI responses using **DeepSeek API** (optional)
* 🛑 Shutdown / Restart system (Windows)
* ⌨ Dictation mode for typing via voice

---

## 🛠 Tech Stack

* **Language:** Python
* **GUI:** CustomTkinter, Tkinter
* **Speech Recognition:** SpeechRecognition, SoundDevice
* **Text-to-Speech:** pyttsx3 / Windows SAPI
* **APIs:**

  * OpenWeatherMap
  * DeepSeek (optional)

---

## 📂 Project Structure

```
├── Assistant.py
├── jarvis_memory.json
├── README.md
```

---

## 🔧 Installation

### 1️⃣ Clone the repository

```bash
git clone https://github.com/your-username/jarvis-ai-assistant.git
cd jarvis-ai-assistant
```

### 2️⃣ Install dependencies

```bash
pip install SpeechRecognition pyttsx3 requests psutil customtkinter sounddevice openai pyautogui
```

### 3️⃣ Install PyAudio (Important)

For Windows:

```bash
pip install pipwin
pipwin install pyaudio
```

---

## 🔑 API Configuration

### 🌦 Weather API

Get your API key from **OpenWeatherMap**
👉 [https://openweathermap.org/api](https://openweathermap.org/api)

Update in `Assistant.py`:

```python
WEATHER_API_KEY = "your_api_key_here"
```

### 🤖 DeepSeek AI (Optional)

Get API key from
👉 [https://platform.deepseek.com/api-keys](https://platform.deepseek.com/api-keys)

```python
DEEPSEEK_API_KEY = "sk-xxxxxxxx"
```

---

## ▶ How to Run

```bash
python Assistant.py
```

* GUI will open automatically
* Jarvis will start listening after launch
* You can **speak or type commands**

---

## 🗣 Example Commands

* “What is the time?”
* “Open Chrome”
* “Search YouTube for Python tutorials”
* “Play music on Spotify”
* “What’s the weather?”
* “Tell me a health tip”
* “Shutdown the system”
* “My name is Anup”

---

## ⚠ Requirements

* Windows OS
* Working microphone
* Internet connection (for APIs & speech recognition)

---

## 🚀 Future Enhancements

* Offline speech recognition (VOSK)
* Wake-word detection using Porcupine
* Cross-platform support
* More AI-powered conversations
* Mobile / Web version

---

## 👨‍💻 Author

**Anup**
ISE Student | Python & AI Enthusiast

If you like this project ⭐ star the repo!

---

## 📜 License

This project is licensed under the **MIT License**.
Feel free to use, modify, and distribute.

