import os
import re

server_file = 'server.py'
with open(server_file, 'r') as f:
    content = f.read()

# 1. Monkey patch anthropic at the top
monkey_patch = """import anthropic
import httpx

class MockAnthropicMessage:
    def __init__(self, text):
        self.text = text

class MockAnthropicContent:
    def __init__(self, text):
        self.content = [MockAnthropicMessage(text)]

class MockAnthropicMessages:
    async def create(self, model, max_tokens, system=None, messages=None, **kwargs):
        prompt = ""
        if system:
            prompt += f"{system}\\n\\n"
        for m in messages:
            prompt += f"{m['role']}: {m['content']}\\n"
        async with httpx.AsyncClient(timeout=120.0) as http:
            try:
                resp = await http.post("http://localhost:11434/api/generate", json={
                    "model": "llama3.2:3b",
                    "prompt": prompt,
                    "stream": False
                })
                data = resp.json()
                return MockAnthropicContent(data.get("response", ""))
            except Exception as e:
                import logging
                logging.error(f"Ollama error: {e}")
                return MockAnthropicContent("Sorry sir, my local language model is offline.")

class MockAsyncAnthropic:
    def __init__(self, *args, **kwargs):
        self.messages = MockAnthropicMessages()

anthropic.AsyncAnthropic = MockAsyncAnthropic
"""

if 'MockAsyncAnthropic' not in content:
    content = content.replace('import anthropic', monkey_patch, 1)

# 2. Replace synthesize_speech
new_tts = """async def synthesize_speech(text: str) -> Optional[bytes]:
    import tempfile, os, asyncio
    try:
        with tempfile.NamedTemporaryFile(suffix=".m4a", delete=False) as f:
            temp_path = f.name
        process = await asyncio.create_subprocess_exec(
            "say", "-v", "Daniel", "-o", temp_path, text,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()
        with open(temp_path, "rb") as f:
            data = f.read()
        os.unlink(temp_path)
        
        # Increment usage to avoid breaking tracking
        if "tts_calls" in _session_tokens:
            _session_tokens["tts_calls"] += 1
            _append_usage_entry(0, 0, "tts")
        return data
    except Exception as e:
        import logging
        logging.error(f"TTS error: {e}")
        return None
"""

# Find the old function and replace it
import ast
# We will use simple regex or string replacement since we know exact lines
old_tts_start = content.find('async def synthesize_speech(text: str) -> Optional[bytes]:')
old_tts_end = content.find('# LLM Response', old_tts_start)

if old_tts_start != -1 and old_tts_end != -1:
    # go back a bit from LLM response
    old_tts_end = content.rfind('# -----', old_tts_start, old_tts_end)
    if old_tts_end != -1:
        old_tts = content[old_tts_start:old_tts_end]
        content = content.replace(old_tts, new_tts + '\n\n')

with open(server_file, 'w') as f:
    f.write(content)

print("Offline mode patch applied successfully.")
