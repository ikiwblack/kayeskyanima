import wave
import numpy as np

def load_audio_envelope(wav_path, fps):
    with wave.open(wav_path, "rb") as wf:
        sr = wf.getframerate()
        frames = wf.readframes(wf.getnframes())
        audio = np.frombuffer(frames, dtype=np.int16)

    max_val = np.max(np.abs(audio))
    if max_val > 0:
        audio = audio / max_val
    else:
        audio = audio.astype(np.float32)

    samples_per_frame = int(sr / fps)

    envelope = []
    for i in range(0, len(audio), samples_per_frame):
        chunk = audio[i:i + samples_per_frame]
        if len(chunk) == 0:
            envelope.append(0.0)
        else:
            envelope.append(float(np.mean(np.abs(chunk))))

    return envelope
