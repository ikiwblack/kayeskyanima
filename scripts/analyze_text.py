import os
import json
from openai import OpenAI
from scripts.cache import load_cached_timeline, save_cached_timeline

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

PROMPT = """
Ubah naskah menjadi timeline animasi.

ATURAN:
- Output HARUS JSON valid
- Maksimal 10 scene
- Emotion hanya: neutral, sad, happy, thinking, angry
- Durasi 3–6 detik

FORMAT:
{
  "fps": 24,
  "scenes": [
    { "text": "...", "emotion": "...", "duration": 4 }
  ]
}

NASKAH:
<<<TEXT>>>
"""

def analyze(text: str) -> dict:
    cached = load_cached_timeline(text)
    if cached:
        return cached

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{
            "role": "user",
            "content": PROMPT.replace("<<<TEXT>>>", text)
        }],
        temperature=0.3
    )

    content = resp.choices[0].message.content
    timeline = json.loads(content)

    save_cached_timeline(text, timeline)
    return timeline
