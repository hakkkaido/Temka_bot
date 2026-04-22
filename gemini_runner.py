"""Gemini runner — API calls with in-memory message queue and conversation history."""

import asyncio
import logging
from typing import Optional, Callable

from config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_TIMEOUT
from db import get_history, save_message

logger = logging.getLogger("gemini_runner")

# In-memory state
_is_busy = False
_message_queue: list[dict] = []  # [{"text": str, "callback": Callable}]


def is_busy() -> bool:
    return _is_busy


def queue_length() -> int:
    return len(_message_queue)


async def run_gemini(
    prompt: str,
    session_id: Optional[str] = None,
    on_result: Optional[Callable] = None,
    max_turns: Optional[int] = None,
    queue_max: int = 5,
) -> dict:
    """Run Gemini API. If busy, queue the message.

    Returns:
        {"status": "started"} — task launched
        {"status": "queued", "position": N} — added to queue
        {"status": "queue_full"} — rejected
    """
    global _is_busy

    if _is_busy:
        if len(_message_queue) >= queue_max:
            return {"status": "queue_full"}
        _message_queue.append({"text": prompt, "session_id": session_id, "callback": on_result})
        return {"status": "queued", "position": len(_message_queue)}

    _is_busy = True

    # Launch in background task so we don't block the handler
    asyncio.create_task(_process_prompt(prompt, session_id, on_result, max_turns))
    return {"status": "started"}


async def _process_prompt(
    prompt: str,
    session_id: Optional[str],
    on_result: Optional[Callable],
    max_turns: Optional[int],
):
    """Execute Gemini API and then drain the queue."""
    global _is_busy

    try:
        result = await _execute_gemini(prompt, session_id, max_turns)

        new_session_id = result.get("session_id", session_id) if result else session_id
        result_text = result.get("result", "") if result else ""

        if on_result:
            await on_result(result_text, new_session_id)

        # Drain queued messages
        while _message_queue:
            queued = _message_queue.pop(0)
            sid = new_session_id or queued.get("session_id")
            combined_prompt = queued["text"]

            qr = await _execute_gemini(combined_prompt, sid, max_turns)
            q_text = qr.get("result", "") if qr else ""
            q_sid = qr.get("session_id", sid) if qr else sid
            new_session_id = q_sid

            cb = queued.get("callback")
            if cb:
                await cb(q_text, q_sid)

    except Exception as e:
        logger.error(f"Error in _process_prompt: {e}", exc_info=True)
        if on_result:
            await on_result(f"Ошибка: {e}", session_id)
    finally:
        _is_busy = False


async def _execute_gemini(
    prompt: str,
    session_id: Optional[str] = None,
    max_turns: Optional[int] = None,
) -> Optional[dict]:
    """Run Gemini API with conversation history, return parsed result."""
    
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY not set")
        return None

    try:
        import google.genai
        
        # Create client with API key
        client = google.genai.Client(api_key=GEMINI_API_KEY)
        
        # Get conversation history if session exists
        history = []
        if session_id:
            db_history = get_history(session_id, limit=max_turns * 2 if max_turns else 30)
            for msg in db_history:
                # Convert our history format to Google GenAI format
                role = "user" if msg["role"] == "user" else "model"
                history.append({
                    "role": role,
                    "parts": [{"text": msg["text"]}]
                })
        
        # Build messages for Gemini
        messages = history + [
            {"role": "user", "parts": [{"text": prompt}]}
        ]

        # Call Gemini API
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=messages,
                config={
                    "temperature": 0.7,
                    "max_output_tokens": 2048,
                }
            )
            
            result_text = response.text if response.text else "Нет ответа от Gemini"
            
        except Exception as api_error:
            logger.error(f"Gemini API call error: {api_error}")
            result_text = f"Ошибка Gemini API: {api_error}"

        # Save messages
        save_message("user", prompt, session_id)
        save_message("assistant", result_text, session_id)

        return {"result": result_text, "session_id": session_id}

    except ImportError:
        logger.error("google.genai not installed. Run: pip install -q -U google-genai")
        return None
    except Exception as e:
        logger.error(f"Gemini execution error: {e}", exc_info=True)
        return None

