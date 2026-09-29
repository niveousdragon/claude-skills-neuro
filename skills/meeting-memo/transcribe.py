"""Transcribe a meeting recording (webm/mp4/m4a/wav...) with faster-whisper.

Writes <out>.txt with [hh:mm:ss] timestamps, one segment per line, and <out>.srt.
Lines are flushed as they come, so a partial file is usable if the run is stopped.
Console output is ASCII only (Windows cp1251 consoles crash on arbitrary Unicode).

usage: python transcribe.py RECORDING OUT_STEM [--model large-v3-turbo] [--lang ru]
"""
import argparse
import os
import sys
import time

# Anaconda ships its own libiomp5md.dll and ctranslate2 loads another; without this
# the process aborts with "OMP: Error #15" before transcribing anything.
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

from faster_whisper import WhisperModel


def ts(sec, srt=False):
    h, rem = divmod(int(sec), 3600)
    m, s = divmod(rem, 60)
    if srt:
        return f"{h:02d}:{m:02d}:{s:02d},{int((sec % 1) * 1000):03d}"
    return f"{h:02d}:{m:02d}:{s:02d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("recording")
    ap.add_argument("out_stem")
    ap.add_argument("--model", default="large-v3-turbo")
    ap.add_argument("--lang", default="ru")
    ap.add_argument("--prompt", default=None,
                    help="initial prompt: names, terms, acronyms expected in the talk")
    a = ap.parse_args()

    # int8 on CPU keeps large-v3-turbo usable without a GPU; CUDA is used when present.
    try:
        import ctranslate2
        cuda = ctranslate2.get_cuda_device_count() > 0
    except Exception:
        cuda = False
    model = WhisperModel(a.model, device="cuda" if cuda else "cpu",
                         compute_type="float16" if cuda else "int8")

    segments, info = model.transcribe(
        a.recording, language=a.lang, vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
        initial_prompt=a.prompt,
        # Without this, one misheard phrase is fed forward and whisper can loop on it.
        condition_on_previous_text=False,
    )
    total = info.duration
    print(f"[OK] audio {total / 60:.1f} min, device={'cuda' if cuda else 'cpu'}", flush=True)

    t0 = time.time()
    last_report = 0.0
    with open(a.out_stem + ".txt", "w", encoding="utf-8") as txt, \
         open(a.out_stem + ".srt", "w", encoding="utf-8") as srt:
        for i, seg in enumerate(segments, 1):
            text = seg.text.strip()
            txt.write(f"[{ts(seg.start)}] {text}\n")
            srt.write(f"{i}\n{ts(seg.start, True)} --> {ts(seg.end, True)}\n{text}\n\n")
            txt.flush()
            srt.flush()
            if seg.end - last_report > 300:
                last_report = seg.end
                print(f"[..] {seg.end / 60:.0f}/{total / 60:.0f} min, "
                      f"elapsed {(time.time() - t0) / 60:.1f} min", flush=True)
    print(f"[OK] done in {(time.time() - t0) / 60:.1f} min", flush=True)


if __name__ == "__main__":
    sys.exit(main())
