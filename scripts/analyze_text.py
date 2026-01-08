import os
import json
import re
import google.generativeai as genai
from scripts.cache import load_cached_timeline, save_cached_timeline

genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

PROMPT = """
Ubah naskah menjadi timeline animasi.

ATURAN:
- Output HARUS JSON valid
- Maksimal 10 scene
- Emotion hanya: neutral, sad, happy, thinking, angry, surprised
- Gesture (opsional) hanya: raise_hand, walk
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
      "duration": 4,
      "gesture": "walk"
    }
  ]
}

NASKAH:
<<<TEXT>>>
"""

def extract_json(text: str) -> dict:
    # Gemini may return JSON inside ```json ... ``` markdown.
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.endswith("```"):
        text = text[:-3]

    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("Gemini tidak mengembalikan JSON yang valid")
    return json.loads(match.group())

def analyze(text: str) -> dict:
    """Analyzes the script text and returns a timeline dictionary."""
    cached = load_cached_timeline(text)
    if cached:
        return cached

    prompt_with_text = PROMPT.replace("<<<TEXT>>>", text)

    # Call the Gemini API
    response = model.generate_content(prompt_with_text)

    try:
        raw_text = response.text
        timeline = extract_json(raw_text)

        save_cached_timeline(text, timeline)
        return timeline
    except (ValueError, AttributeError) as e:
        raise ValueError(f"Gagal memproses response dari Gemini: {e}") from e
