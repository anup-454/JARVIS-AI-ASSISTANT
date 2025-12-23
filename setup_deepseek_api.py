#!/usr/bin/env python3
"""
Setup script to configure Deepseek API key for Jarvis
"""

import os
from pathlib import Path

def setup_deepseek():
    script_path = Path(__file__).parent / "python jarvis_assistant.py"
    
    print("=" * 60)
    print("Deepseek API Setup for Jarvis")
    print("=" * 60)
    print()
    print("To get your Deepseek API key:")
    print("1. Go to https://platform.deepseek.com/")
    print("2. Sign up/Login")
    print("3. Go to API Keys: https://platform.deepseek.com/api-keys")
    print("4. Click 'Create API Key'")
    print("5. Copy the key (starts with 'sk-')")
    print()
    print("-" * 60)
    
    api_key = input("Enter your Deepseek API key: ").strip()
    
    if not api_key.startswith("sk-"):
        print("❌ Invalid! API key should start with 'sk-'")
        return
    
    if len(api_key) < 20:
        print("❌ Invalid! API key too short")
        return
    
    # Read the script
    with open(script_path, 'r') as f:
        content = f.read()
    
    # Replace the placeholder
    old_line = 'DEEPSEEK_API_KEY = "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"'
    new_line = f'DEEPSEEK_API_KEY = "{api_key}"'
    
    if old_line in content:
        content = content.replace(old_line, new_line)
        with open(script_path, 'w') as f:
            f.write(content)
        print(f"✅ API key saved successfully!")
        print(f"Key (last 10 chars): ...{api_key[-10:]}")
        print()
        print("Now you can run:")
        print(f'  python -u "{script_path}"')
    else:
        print("❌ Could not find the API key line in the script")

if __name__ == "__main__":
    setup_deepseek()
