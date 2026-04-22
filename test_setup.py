#!/usr/bin/env python3
"""Test script for Gemini API connection."""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load config
import config
from dotenv import load_dotenv

# Load .env
env_path = project_root / ".env"
load_dotenv(env_path)

print("=" * 60)
print("🔍 GEMINI BOT TEST SCRIPT")
print("=" * 60)

# Check configuration
print("\n📋 Configuration Check:")
print(f"  ✓ Telegram Bot Token: {'✅' if config.BOT_TOKEN else '❌'}")
print(f"  ✓ Telegram Chat ID: {config.ADMIN_CHAT_ID if config.ADMIN_CHAT_ID else '❌'}")
print(f"  ✓ Gemini API Key: {'✅' if config.GEMINI_API_KEY else '❌'}")
print(f"  ✓ Gemini Model: {config.GEMINI_MODEL} (Gemma 3)")
print(f"  ✓ Groq API Key: {'✅' if config.GROQ_API_KEY else '❌'}")

# Test Gemini API connection
print("\n🤖 Testing Gemini API Connection...")

try:
    import google.genai
    
    # Create client with API key
    client = google.genai.Client(api_key=config.GEMINI_API_KEY)
    print(f"  ✓ Configured with model: {config.GEMINI_MODEL}")
    
    # Send test request
    print("\n  Sending test prompt: 'Hello, introduce yourself briefly'")
    response = client.models.generate_content(
        model=config.GEMINI_MODEL,
        contents="Hello, introduce yourself briefly",
        config={"max_output_tokens": 200}
    )
    
    if response.text:
        print(f"\n  ✅ GEMINI API WORKS!")
        print(f"\n  Response preview:\n  {response.text[:200]}...")
        
    else:
        print(f"  ⚠️ API responded but no text returned")
        
except ImportError:
    print("  ❌ google.genai not installed. Run: pip install -q -U google-genai")
    sys.exit(1)
    
except Exception as e:
    print(f"  ❌ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Check database setup
print("\n💾 Database Check:")
try:
    from db import init_db
    init_db()
    print(f"  ✓ Database initialized at: {config.DB_PATH}")
    print(f"  ✓ Work directory: {config.WORK_DIR}")
except Exception as e:
    print(f"  ❌ Database error: {e}")
    sys.exit(1)

# Check modules
print("\n📦 Module Import Check:")
try:
    from gemini_runner import run_gemini, is_busy, queue_length
    print(f"  ✓ gemini_runner imported")
    from formatting import md_to_telegram_html, split_message
    print(f"  ✓ formatting imported")
    from voice import transcribe_voice
    print(f"  ✓ voice imported")
    from scheduler import run_scheduler
    print(f"  ✓ scheduler imported")
except ImportError as e:
    print(f"  ❌ Import error: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("✅ ALL TESTS PASSED!")
print("=" * 60)
print("\nBot is ready to use. Start with: python main.py")
print(f"Send messages to Telegram chat ID: {config.ADMIN_CHAT_ID}")
