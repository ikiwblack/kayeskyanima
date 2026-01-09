import os
import json
import re
import google.generativeai as genai
from scripts.cache import load_cached_timeline, save_cached_timeline

genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-pro')

PROMPT = """
Ubah naskah menjadi timeline animasi.

ATURAN:
- Output HARUS JSON valid.
- Dimensi video adalah <<<WIDTH>>>x<<<HEIGHT>>>. Sesuaikan posisi horizontal karakter (`x`) agar sesuai dengan lebar ini.
- Maksimal 10 scene.
- Emotion hanya: neutral, sad, happy, thinking, angry, surprised.
- Gesture (opsional) hanya: raise_hand, walk.
- Durasi 3–6 detik.
- Untuk setiap karakter, pilih warna dari daftar di bawah ini.

WARNA:
- &H00FFFF& (Cyan)
- &HFF00FF& (Magenta)
- &HFFFF00& (Yellow)
- &H00FF00& (Green)
- &HFF0000& (Red)
- &H0000FF& (Blue)

WAJIB FORMAT:
{
  "width": <<<WIDTH>>>,
  "height": <<<HEIGHT>>>,
  "fps": 12,
  "characters": [
    { "id": "a", "x": 400, "color": "&H00FFFF&" },
    { "id": "b", "x": 1400, "color": "&HFF00FF&" }
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
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.endswith("```"):
        text = text[:-3]

    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("Gemini tidak mengembalikan JSON yang valid")
    return json.loads(match.group())

def analyze(text: str, orientation: str = "9:16") -> dict:
    """Menganalisis naskah dan mengembalikan timeline dictionary berdasarkan orientasi."""
    cache_key = f"orientation={orientation}::{text}"
    cached = load_cached_timeline(cache_key)
    if cached:
        return cached

    if orientation == "16:9":
        width, height = 1920, 1080
    else:  # Default ke 9:16
        width, height = 1080, 1920

    prompt = PROMPT.replace("<<<TEXT>>>", text)
    prompt = prompt.replace("<<<WIDTH>>>", str(width))
    prompt = prompt.replace("<<<HEIGHT>>>", str(height))

    response = model.generate_content(prompt)

    try:
        raw_text = response.text
        timeline = extract_json(raw_text)

        if "characters" in timeline:
            colors = ["&H00FFFF&", "&HFF00FF&", "&HFFFF00&", "&H00FF00&", "&HFF0000&", "&H0000FF&"]
            for i, char in enumerate(timeline["characters"]):
                if "color" not in char or not char["color"]:
                    char["color"] = colors[i % len(colors)]
        
        # Fallback untuk memastikan dimensi ada di output
        timeline.setdefault("width", width)
        timeline.setdefault("height", height)

        save_cached_timeline(cache_key, timeline)
        return timeline
    except (ValueError, AttributeError) as e:
        raise ValueError(f"Gagal memproses response dari Gemini: {e}") from e
