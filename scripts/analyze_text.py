import os
import json
import re
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

WAJIB FORMAT:
{
  "fps": 12,
  "characters": [
    { "id": "a", "x": 250, "color": "&H00FFCC&" },
    { "id": "b", "x": 650, "color": "&HFF99FF&" }
  ],
  "scenes": [
    {
      "speaker": "a",
      "text": "...",
      "emotion": "happy",
      "bg": "neutral",
      "duration": 4
    }
  ]
}

NASKAH:
<<<TEXT>>>
"""

def extract_json(text: str) -> dict:
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("GPT tidak mengembalikan JSON")
    return json.loads(match.group())

def analyze(text: str) -> dict:
    cached = load_cached_timeline(text)
    if cached:
        return cached

    resp = client.responses.create(
        model="gpt-4o-mini",
        input=PROMPT.replace("<<<TEXT>>>", text),
        temperature=0.3
    )

    raw = resp.output_text
    timeline = extract_json(raw)

    save_cached_timeline(text, timeline)
    return timeline
