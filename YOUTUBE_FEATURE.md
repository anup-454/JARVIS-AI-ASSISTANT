# YouTube Search Feature

## Overview
JARVIS now supports searching and opening specific YouTube videos using voice commands.

## Command Patterns

You can use any of these voice command patterns to search YouTube:

### Pattern 1: "Search YouTube for [video name]"
```
"Search YouTube for cat videos"
"Search YouTube for music production"
"Search YouTube for Python tutorial"
```

### Pattern 2: "Search for [video name] on YouTube"
```
"Search for gaming highlights on YouTube"
"Search for cooking recipes on YouTube"
"Search for motivational speeches on YouTube"
```

### Pattern 3: "Play [video name] on YouTube"
```
"Play music on YouTube"
"Play workout videos on YouTube"
"Play funny compilations on YouTube"
```

### Pattern 4: "Play [video name] YouTube"
```
"Play gaming videos YouTube"
"Play tutorials YouTube"
"Play vlogs YouTube"
```

### Pattern 5: "Find [video name] on YouTube"
```
"Find guitar lessons on YouTube"
"Find coding tutorials on YouTube"
"Find movie trailers on YouTube"
```

### Pattern 6: "YouTube [video name]"
```
"YouTube songs"
"YouTube movie reviews"
"YouTube tech news"
```

### Pattern 7: Just open YouTube
```
"Open YouTube"
"Launch YouTube"
"Open the YouTube"
```

## Examples

### Example 1: Search for a specific song
**You say:** "Play Bohemian Rhapsody on YouTube"
**JARVIS responds:** "Searching YouTube for Bohemian Rhapsody"
**Result:** YouTube search results page opens with the video

### Example 2: Search for a tutorial
**You say:** "Search YouTube for web development tutorial"
**JARVIS responds:** "Searching YouTube for web development tutorial"
**Result:** YouTube search results page opens with tutorials

### Example 3: Search for a channel
**You say:** "Search for MrBeast on YouTube"
**JARVIS responds:** "Searching YouTube for MrBeast"
**Result:** YouTube search results page opens

## How It Works

1. JARVIS listens for voice commands
2. When it detects "YouTube" + search words ("search", "play", "find", "look for")
3. It extracts the video name from your command
4. Opens YouTube search results page with your query
5. Your default browser opens with search results

## Notes

- The search results page opens automatically in your default browser
- You can then browse and click on the video you want
- Full video names work best for accurate searches
- Common video/channel names are usually found in the first few results

## Integration

This feature is integrated into:
- ✅ Main listening function
- ✅ GUI command handler
- ✅ Both Assistant.py and python jarvis_gui_porcu.py.py
- ✅ Console and GUI versions

