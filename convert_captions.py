"""
convert_captions.py — turns gen_voice.py's flat word_timings.json into the
VoLine[] shape that remotion/src/lib/shorts.tsx's <Captions> component expects:

    [
      { "text": "...", "start": 0.0, "end": 1.2, "words": [
          { "w": "Have", "start": 0.0, "end": 0.3 },
          { "w": "you",  "start": 0.3, "end": 0.5 },
          ...
      ]},
      ...
    ]

It groups the flat Whisper word list back into lines using SCRIPT_LINES
from gen_voice.py (same source of truth, so line text always matches).

USAGE:
    python convert_captions.py

Reads:  output/word_timings.json   (from gen_voice.py)
Writes: output/captions.json       (ready for <Captions lines={...} />)
"""

import json
import os

from gen_voice import SCRIPT_LINES  # reuse the same script lines, single source of truth

WORD_TIMINGS_PATH = os.path.join("output", "word_timings.json")
CAPTIONS_OUT_PATH = os.path.join("output", "captions.json")


def main():
    with open(WORD_TIMINGS_PATH) as f:
        flat_words = json.load(f)

    expected_word_count = sum(len(line.split()) for line in SCRIPT_LINES)
    actual_word_count = len(flat_words)

    if expected_word_count != actual_word_count:
        print(
            f"WARNING: expected {expected_word_count} words from SCRIPT_LINES, "
            f"but Whisper produced {actual_word_count}. Whisper sometimes splits "
            f"contractions differently (e.g. \"It's\" -> \"It\" + \"'s\"). "
            f"Grouping below is best-effort — check output/captions.json before "
            f"trusting it fully."
        )

    vo_lines = []
    cursor = 0

    for line_text in SCRIPT_LINES:
        n_words = len(line_text.split())
        line_words = flat_words[cursor : cursor + n_words]
        cursor += n_words

        if not line_words:
            # Ran out of words (mismatch case) — skip gracefully rather than crash.
            continue

        vo_lines.append({
            "text": line_text,
            "start": line_words[0]["start"],
            "end": line_words[-1]["end"],
            "words": [
                {"w": w["word"], "start": w["start"], "end": w["end"]}
                for w in line_words
            ],
        })

    with open(CAPTIONS_OUT_PATH, "w") as f:
        json.dump(vo_lines, f, indent=2)

    print(f"Wrote {len(vo_lines)} caption lines to {CAPTIONS_OUT_PATH}")
    print("\nSample (first line):")
    print(json.dumps(vo_lines[0] if vo_lines else {}, indent=2))


if __name__ == "__main__":
    main()
