"""
gen_voice.py — $0 narration + word-timestamp generator.

Replaces ElevenLabs with:
  1. edge-tts   -> free neural narration (Microsoft voices, no API key)
  2. faster-whisper (small model) -> free word-level timestamps,
     by transcribing the audio we just generated

USAGE:
    python gen_voice.py

Reads SCRIPT_LINES below (one entry per caption/VO line), and produces:
    output/voice.mp3         -- the full narration, all lines concatenated
    output/word_timings.json -- word-level timing data for captions

SETUP (run once):
    pip install edge-tts faster-whisper --break-system-packages

NOTE: faster-whisper's first run downloads the "small" model (~484MB).
This is a one-time download — it's cached afterward, so every run after
the first is fast and needs no internet for the model itself.
"""

import asyncio
import json
import os
import subprocess

import edge_tts
from faster_whisper import WhisperModel

# ---------------------------------------------------------------------------
# 1. YOUR SCRIPT — edit this list for each new video.
#    Keep each line short (matches the beat grammar: ~2.7 words/sec pacing).
# ---------------------------------------------------------------------------
SCRIPT_LINES = [
    "Have you ever seen a moon this big?",
    "This is the exact same moon.",
    "So why does it look so different?",
    "It's called the Moon Illusion.",
    "Your brain compares the moon to what's around it.",
    "Near the horizon, buildings and trees make it look huge.",
    "High in the sky, with nothing to compare it to, it shrinks.",
    "The moon never changed size at all.",
    "Only your perception did.",
]

VOICE = "en-US-GuyNeural"  # free Edge TTS voice; browse more with `edge-tts --list-voices`
OUTPUT_DIR = "output"
LINE_AUDIO_DIR = os.path.join(OUTPUT_DIR, "lines")
FULL_AUDIO_PATH = os.path.join(OUTPUT_DIR, "voice.mp3")
TIMINGS_PATH = os.path.join(OUTPUT_DIR, "word_timings.json")
WHISPER_MODEL_SIZE = "small"  # better accuracy than tiny; ~484MB one-time download, then cached


# ---------------------------------------------------------------------------
# 2. Generate narration audio per line with Edge TTS
# ---------------------------------------------------------------------------
async def generate_line_audio(text: str, path: str):
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(path)


async def generate_all_audio():
    os.makedirs(LINE_AUDIO_DIR, exist_ok=True)
    paths = []
    for i, line in enumerate(SCRIPT_LINES):
        path = os.path.join(LINE_AUDIO_DIR, f"line_{i:02d}.mp3")
        print(f"Generating voice for line {i}: {line!r}")
        await generate_line_audio(line, path)
        paths.append(path)
    return paths


def concatenate_audio(line_paths, output_path):
    """Stitch all line mp3s into one file using ffmpeg concat."""
    list_file = os.path.join(OUTPUT_DIR, "concat_list.txt")
    with open(list_file, "w") as f:
        for p in line_paths:
            f.write(f"file '{os.path.abspath(p)}'\n")

    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", list_file,
            "-c", "copy",
            output_path,
        ],
        check=True,
    )
    print(f"Full narration saved to {output_path}")


# ---------------------------------------------------------------------------
# 3. Transcribe the generated audio with faster-whisper to get
#    word-level timestamps (this replaces ElevenLabs' timing data)
# ---------------------------------------------------------------------------
def get_word_timings(audio_path: str):
    print(f"Loading faster-whisper ({WHISPER_MODEL_SIZE}) — first run downloads the model...")
    model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")

    segments, _ = model.transcribe(audio_path, word_timestamps=True)

    words = []
    for segment in segments:
        for word in segment.words:
            words.append({
                "word": word.word.strip(),
                "start": round(word.start, 3),
                "end": round(word.end, 3),
            })
    return words


# ---------------------------------------------------------------------------
# 4. Run everything
# ---------------------------------------------------------------------------
def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    line_paths = asyncio.run(generate_all_audio())
    concatenate_audio(line_paths, FULL_AUDIO_PATH)

    words = get_word_timings(FULL_AUDIO_PATH)

    with open(TIMINGS_PATH, "w") as f:
        json.dump(words, f, indent=2)

    print(f"\nDone. {len(words)} words timed.")
    print(f"Audio:    {FULL_AUDIO_PATH}")
    print(f"Timings:  {TIMINGS_PATH}")
    print("\nSample of word_timings.json:")
    print(json.dumps(words[:5], indent=2))


if __name__ == "__main__":
    main()
