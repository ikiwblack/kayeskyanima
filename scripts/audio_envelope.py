import wave
import numpy as np

def load_audio_envelope(wav_path, fps):
    with wave.open(wav_path, "rb") as wf:
        frames = wf.readframes(wf.getnframes())
        audio = np.frombuffer(frames, dtype=np.int16)

    audio = audio / np.max(np.abs(audio))
    samples_per_frame = int(len(audio) / (wf.getnframes() / wf.getframerate() * fps))

    envelope = []
    for i in range(0, len(audio), samples_per_frame):
        chunk = audio[i:i+samples_per_frame]
        envelope.append(float(np.mean(np.abs(chunk))))

    return envelope
