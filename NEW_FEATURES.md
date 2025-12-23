# New Features Added to JARVIS

## Health Tips Feature
Your JARVIS assistant can now provide daily health tips to keep you healthy and informed.

### How to use:
Simply say any of these commands:
- "Health tip"
- "Health advice"
- "Give me a health tip"
- "Tell me a health tip"

The assistant will respond with a random health tip from a curated collection of 18 health tips covering:
- Hydration
- Exercise
- Sleep
- Nutrition
- Stress management
- Mental health
- And more...

### Example:
User: "Give me a health tip"
Jarvis: "Drink at least 8 glasses of water daily to stay hydrated and maintain good health."

---

## News Feature
Your JARVIS assistant can now fetch and share the latest news headlines.

### How to use:
Simply say any of these commands:
- "News"
- "Latest news"
- "Tell me the news"
- "What's in the news"
- "Recent news"
- "Today's news"

The assistant will fetch the top 3 latest news headlines and read them to you.

### Example:
User: "Tell me the news"
Jarvis: "Here are the latest news headlines: Number 1: [headline]. Number 2: [headline]. Number 3: [headline]."

---

## Implementation Details

### Files Modified:
1. **Assistant.py** - Main assistant file with both CLI and GUI versions
2. **python jarvis_gui_porcu.py.py** - GUI-focused version

### Functions Added:
- `get_health_tips()` - Returns a random health tip from the collection
- `get_news()` - Fetches latest news headlines from NewsAPI

### Features Integrated In:
- Main command handler
- GUI command handler
- Both voice and text input modes

---

## Requirements:
The news feature requires an internet connection to fetch live headlines. If the API is unavailable, a fallback message will be provided.

Health tips are stored locally and don't require internet access.

---

## Customization:
You can easily add more health tips by editing the `health_tips` list in the `get_health_tips()` function.

To use your own NewsAPI key instead of the demo key, replace `news_api_key = "demo"` with your actual key from https://newsapi.org/

