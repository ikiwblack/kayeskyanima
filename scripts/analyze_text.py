import os
import json
from openai import OpenAI

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

PROMPT = """Kamu adalah sistem yang mengubah naskah menjadi timeline animasi.

ATURAN:
- Output HARUS JSON valid
- Jangan beri penjelasan
- Maksimal 10 scene
- Emotion hanya boleh: neutral, sad, happy, thinking, angry
- Durasi 3–6 detik per scene

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

def analyze(text):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": PROMPT.replace("<<<TEXT>>>", text)
            }
        ],
        temperature=0.3
    )

    content = response.choices[0].message.content
    timeline = json.loads(content)

    with open("timeline.json", "w", encoding="utf-8") as f:
        json.dump(timeline, f, indent=2, ensure_ascii=False)

    return timeline
