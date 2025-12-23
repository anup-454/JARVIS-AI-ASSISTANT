# Spotify Integration Guide

## Overview
JARVIS now has full Spotify integration! You can search for songs, artists, playlists, and podcasts on Spotify using voice commands.

## Features

✅ **Open Spotify** - Simply say "open Spotify"  
✅ **Search for Music** - Multiple command patterns  
✅ **Auto-Launch App** - Desktop app opens while search loads  
✅ **Web Player** - Falls back to web search if desktop app unavailable  

## Command Patterns

### Pattern 1: "Search Spotify for [song/artist]"
```
"Search Spotify for Bohemian Rhapsody"
"Search Spotify for The Beatles"
"Search Spotify for workout music"
```

### Pattern 2: "Search for [song/artist] on Spotify"
```
"Search for Taylor Swift on Spotify"
"Search for meditation music on Spotify"
"Search for lo-fi beats on Spotify"
```

### Pattern 3: "Play [song/artist] on Spotify"
```
"Play Blinding Lights on Spotify"
"Play Ed Sheeran on Spotify"
"Play Jazz on Spotify"
```

### Pattern 4: "Play [song/artist] Spotify"
```
"Play Uptown Funk Spotify"
"Play Dua Lipa Spotify"
"Play hip-hop Spotify"
```

### Pattern 5: "Find [song/artist] on Spotify"
```
"Find My Favorite Song on Spotify"
"Find The Weeknd on Spotify"
"Find acoustic covers on Spotify"
```

### Pattern 6: "Listen to [song/artist] on Spotify"
```
"Listen to Levitating on Spotify"
"Listen to Bruno Mars on Spotify"
"Listen to chill vibes on Spotify"
```

### Pattern 7: "Spotify [song/artist]"
```
"Spotify Drake"
"Spotify pop hits"
"Spotify sleep music"
```

### Pattern 8: Just open Spotify
```
"Open Spotify"
"Launch Spotify"
"Open the Spotify"
```

## Examples

### Example 1: Search for a specific song
**You say:** "Play Blinding Lights on Spotify"  
**JARVIS responds:** "Searching Spotify for Blinding Lights"  
**Result:** Spotify app opens + web search results load

### Example 2: Search for an artist
**You say:** "Search Spotify for The Weeknd"  
**JARVIS responds:** "Searching Spotify for The Weeknd"  
**Result:** Artist profile and songs appear

### Example 3: Search for a playlist/genre
**You say:** "Search Spotify for workout music"  
**JARVIS responds:** "Searching Spotify for workout music"  
**Result:** Workout playlists appear

## How It Works

1. JARVIS listens for "spotify" + action words ("search", "play", "find", "listen", "look for")
2. Extracts the song/artist/playlist name from your voice command
3. Opens the Spotify desktop app (if installed)
4. Opens Spotify web search results in your browser
5. You can then browse and click to play music

## Spotify Path

The Spotify executable path is configured at:
```
"spotify": r"C:\Users\anup0\AppData\Roaming\Spotify\spotify.exe"
```

If Spotify is installed in a different location, update this path in the APPS dictionary.

## Integration

This feature is integrated into:
- ✅ Main listening function
- ✅ GUI command handler
- ✅ Both Assistant.py and python jarvis_gui_porcu.py.py
- ✅ Console and GUI versions

## Notes

- Spotify requires a Spotify account (free or premium)
- Desktop app opening is optional; web search works without it
- You can customize the search query as needed
- Works with songs, artists, playlists, albums, podcasts, and genres

## Tips

- Use specific song/artist names for faster results
- You can say "Spotify [anything]" - it will search for it
- If you want just the app, say "Open Spotify"
- If you're searching for a genre or mood, add descriptive words like "upbeat", "chill", "workout", etc.

