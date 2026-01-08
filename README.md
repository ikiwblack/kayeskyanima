# Simple Text to Animation

CPU-only pipeline to convert narration text into simple 2D animation video.

## Features
- No GPU
- No stock media
- Simple child-like animation
- Deterministic & cheap
- Suitable for personal use

## Flow
Text → LLM → timeline.json → frames → video → audio → final video

## Requirements
- Python 3.9+
- FFmpeg

## Install
pip install -r requirements.txt

## Run
python main.py
