"""
create_sample.py
Generates a short, clean 5-second sample song (.wav) with bass, chords, and drums
using Python standard library (wave, math, struct) so no dependencies are required.
"""

import math
import struct
import wave
from pathlib import Path

OUTPUT_FILE = Path(__file__).resolve().parent / "samples" / "short_groove.wav"
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

SAMPLE_RATE = 44100
DURATION = 6.0  # 6 seconds
NUM_SAMPLES = int(SAMPLE_RATE * DURATION)

# Chord progression frequencies (Frequencies in Hz):
# C major: C4 (261.63), E4 (329.63), G4 (392.00)
# A minor: A3 (220.00), C4 (261.63), E4 (329.63)
# F major: F3 (174.61), A3 (220.00), C4 (261.63)
# G major: G3 (196.00), B3 (246.94), D4 (293.66)
CHORDS = [
    [261.63, 329.63, 392.00, 523.25],  # C
    [220.00, 261.63, 329.63, 440.00],  # Am
    [174.61, 220.00, 261.63, 349.23],  # F
    [196.00, 246.94, 293.66, 392.00],  # G
]
BASS_NOTES = [130.81, 110.00, 87.31, 98.00]

print(f"Generating sample song: {OUTPUT_FILE} ({DURATION}s)...")

with wave.open(str(OUTPUT_FILE), "w") as wav_out:
    wav_out.setnchannels(2)  # Stereo
    wav_out.setsampwidth(2)  # 16-bit
    wav_out.setframerate(SAMPLE_RATE)

    for i in range(NUM_SAMPLES):
        t = i / SAMPLE_RATE

        # Bar timing: 1.5s per chord
        chord_idx = int(t / 1.5) % len(CHORDS)
        chord = CHORDS[chord_idx]
        bass_freq = BASS_NOTES[chord_idx]

        # Piano / Guitar chord arpeggio simulation
        arpeggio_note = chord[int(t * 4) % len(chord)]
        arpeggio_env = math.exp(-((t * 4) % 1.0) * 4)
        melody = 0.3 * math.sin(2 * math.pi * arpeggio_note * t) * arpeggio_env

        # Bassline
        bass_env = 0.8 + 0.2 * math.sin(2 * math.pi * 2 * t)
        bass = 0.35 * math.sin(2 * math.pi * bass_freq * t) * bass_env

        # Drum beat simulation (kick & snare)
        beat_t = (t * 2) % 1.0  # 120 bpm = 2 beats per sec
        is_snare = int(t * 2) % 2 == 1
        drum = 0.0

        if not is_snare:
            # Kick drum: fast pitch drop sine
            kick_freq = 120.0 * math.exp(-beat_t * 20) + 45.0
            drum = 0.4 * math.sin(2 * math.pi * kick_freq * beat_t) * math.exp(-beat_t * 8)
        else:
            # Snare drum: noise burst + low tone
            noise = ((math.sin(i * 12345.67) % 1.0) - 0.5) * 2.0
            drum = (0.25 * noise + 0.15 * math.sin(2 * math.pi * 180 * beat_t)) * math.exp(-beat_t * 12)

        # Vocals / Lead flute simulation (continuous gentle vibrato melody)
        lead_freq = chord[2] * 2  # Higher octave
        vibrato = 5.0 * math.sin(2 * math.pi * 5.0 * t)
        lead = 0.15 * math.sin(2 * math.pi * (lead_freq + vibrato) * t)

        # Mix channels
        left_val = melody * 0.7 + bass * 0.5 + drum * 0.6 + lead * 0.5
        right_val = melody * 0.5 + bass * 0.5 + drum * 0.6 + lead * 0.7

        # Soft clip to prevent distortion
        left_val = max(-0.95, min(0.95, left_val))
        right_val = max(-0.95, min(0.95, right_val))

        # Convert to 16-bit integer
        left_int = int(left_val * 32767)
        right_int = int(right_val * 32767)

        wav_out.writeframes(struct.pack("<hh", left_int, right_int))

print("Sample song generated successfully.")

