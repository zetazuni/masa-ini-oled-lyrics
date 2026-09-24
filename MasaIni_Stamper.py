#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║  ♫  LYRIC TIMESTAMP STAMPER                                ║
║  "Masa Ini, Masa Nanti dan Masa Indah Lainnya" — Nuca       ║
║  Output → MasaIni_LyricsVideo.ino  (Heltec WiFi-LoRa 32 V4)║
╠══════════════════════════════════════════════════════════════╣
║  Install  :  pip install pynput                             ║
╚══════════════════════════════════════════════════════════════╝

  HOW TO USE
  ──────────
  1.  Run this script:  python MasaIni_Stamper.py
  2.  Press  T      at the exact moment the song starts (timer = 0).
  3.  Press  SPACE  the exact moment each lyric line begins.
  4.  Press  B      to undo the last stamp and redo it.
  5.  Press  Q      when done — saves  lyrics_timestamps.h next to this
      script. MasaIni_LyricsVideo.ino #includes it: just re-flash.
"""

import os
import sys
import time
import threading
from pynput import keyboard as pkb

# ──────────────────────────────────────────────────────────────
#  LYRICS
#  - Each entry = one timestamp event (one SPACE press)
#  - Empty string "" = instrumental gap → shows "~ ~ ~" on OLED
#  - Lines > 18 chars are auto-split into two OLED rows on export
# ──────────────────────────────────────────────────────────────
LYRICS = [
    # ── Verse 1 ─────────────────────────────────────
    "Semua kata yang terucap",
    "Semua tertuju padamu, oh",
    "Semua arah yang ku tempuh",
    "Semua tertuju padamu,",
    "ho-oh-oh",

    # ── Verse 2 ─────────────────────────────────────
    "Kau adalah semua jawaban",
    "Dari doa yang kupanjatkan",
    "Dengan hadirmu di hidupku",
    "Sudah ku merasa cukup",

    # ── Chorus ──────────────────────────────────────
    "Hati ini telah menetapkan",
    "Engkau sosok yang 'kan menemaniku",
    "Di masa ini,",
    "Di masa nanti,",
    "dan masa indah lainnya",

    # ── Chorus (repeat) ─────────────────────────────
    "Di masa ini,",
    "masa nanti",
    "Dan masa indah lainnya",
]

# OLED character limits per font
OLED_LARGE_MAX  = 18   # u8g2_font_7x13B_tf  — large single-line
OLED_MEDIUM_MAX = 21   # u8g2_font_6x10_tf   — medium two-line

# ──────────────────────────────────────────────────────────────
#  SHARED STATE  (all access inside _lock)
# ──────────────────────────────────────────────────────────────
_lock    = threading.Lock()
_idx     = 0          # index of the CURRENT (unstemped) lyric
_stamps  = []         # list of int milliseconds, one per lyric
_t0      = None       # monotonic() when T was pressed (song start)
_running = True       # main loop flag
_done    = False      # all lines stamped

# ──────────────────────────────────────────────────────────────
#  HELPERS
# ──────────────────────────────────────────────────────────────
def _elapsed() -> int:
    """Milliseconds since the T press (or 0)."""
    with _lock:
        t0 = _t0
    return 0 if t0 is None else int((time.monotonic() - t0) * 1000)


def _fmt(ms) -> str:
    """Format milliseconds as MM:SS.mmm"""
    if ms is None:
        return "--:--.---"
    m, rem = divmod(ms / 1000.0, 60.0)
    return f"{int(m):02d}:{rem:06.3f}"


def _clr():
    os.system("cls" if os.name == "nt" else "clear")


# ──────────────────────────────────────────────────────────────
#  TERMINAL UI
# ──────────────────────────────────────────────────────────────
W = 60  # box width

def _box_line(text: str, width: int = W - 4) -> str:
    return f"│ {str(text)[:width]:<{width}} │"


def _hr(c: str = "─") -> str:
    return c * W


def draw():
    """Render the current state to the terminal."""
    with _lock:
        idx    = _idx
        stamps = list(_stamps)
        done   = _done
        t0     = _t0

    el  = _elapsed()
    n   = len(LYRICS)
    bar = "▓" * min(idx, n)
    gap = "░" * max(n - idx, 0)

    _clr()

    # ── header ──────────────────────────────────────────────
    print(f"╔{_hr('═')}╗")
    print(_box_line("♫  LYRIC TIMESTAMP STAMPER"))
    print(_box_line("   'Masa Ini...' by Nuca   ×   Heltec OLED"))
    print(f"╠{_hr('═')}╣")
    print(_box_line(
        f"Timer    : {_fmt(el) if t0 else 'waiting — press T when the song starts'}"
    ))
    print(_box_line(f"Progress : {min(idx,n):>2}/{n}  [{bar}{gap}]"))
    print(f"╚{_hr('═')}╝")
    print()

    # ── previous (already stamped) line ─────────────────────
    print(f"  {_hr()}")
    if idx > 0 and stamps:
        prev_txt = LYRICS[idx - 1]
        s_ms     = stamps[idx - 1]
        e_ms     = stamps[idx] if idx < len(stamps) else el
        label    = f'"{prev_txt}"' if prev_txt else "(instrumental gap)"
        print(f"  ✓  [{_fmt(s_ms)} → {_fmt(e_ms)}]")
        print(f"     {label}")
    else:
        print(f"  (beginning of song)")

    print()

    # ── current line ─────────────────────────────────────────
    if not done and idx < n:
        cur_txt = LYRICS[idx]
        label   = f'"{cur_txt}"' if cur_txt else "(instrumental gap)"
        is_long = cur_txt and len(cur_txt) > OLED_LARGE_MAX
        warn    = "   ⚠ long → auto-split on export" if is_long else ""
        print(f"  ►  {label}{warn}")
    elif done:
        print(f"  ✓  All {n} lines stamped!")
    print()

    # ── next line ────────────────────────────────────────────
    if not done and idx + 1 < n:
        nxt     = LYRICS[idx + 1]
        nxt_lbl = f'"{nxt}"' if nxt else "(instrumental gap)"
        print(f"  next ›  {nxt_lbl}")
    elif not done and idx + 1 == n:
        print(f"  next ›  (last line)")

    print()
    print(f"  {_hr()}")

    # ── stamped log (last 4) ─────────────────────────────────
    if stamps:
        print()
        print("  Recent stamps:")
        show_from = max(0, len(stamps) - 4)
        for i in range(show_from, len(stamps)):
            txt    = LYRICS[i] if i < n else "?"
            label  = f'"{txt}"' if txt else "(gap)"
            s_ms   = stamps[i]
            e_ms   = stamps[i+1] if i+1 < len(stamps) else (el if not done else stamps[-1]+4000)
            short  = label[:30] + ("…" if len(label) > 30 else "")
            print(f"    [{i+1:>2}] {_fmt(s_ms)} → {_fmt(e_ms)}   {short}")

    print()
    print(f"  {_hr()}")
    if not done:
        print("  [T] start timer   [SPACE] stamp line   [B] undo   [Q] quit & export")
    else:
        print("  [Q] export & quit")
    print()


# ──────────────────────────────────────────────────────────────
#  KEYBOARD HANDLER  (runs in pynput's background thread)
# ──────────────────────────────────────────────────────────────
def on_press(key):
    global _idx, _stamps, _t0, _running, _done

    el = _elapsed()   # read before acquiring lock

    with _lock:
        # ── T — start the song timer (t = 0) ──────────────
        if hasattr(key, "char") and key.char and key.char.lower() == "t":
            if _t0 is None:
                _t0 = time.monotonic()

        # ── SPACE — stamp current line (timer must be running) ──
        elif key == pkb.Key.space:
            if _t0 is not None and not _done:
                _stamps.append(el)
                _idx += 1
                if _idx >= len(LYRICS):
                    _done = True

        # ── B — back / undo last stamp ────────────────────
        elif hasattr(key, "char") and key.char and key.char.lower() == "b":
            if _idx > 0:
                _idx   -= 1
                _done   = False
                if _stamps:
                    _stamps.pop()

        # ── Q — quit ─────────────────────────────────────
        elif hasattr(key, "char") and key.char and key.char.lower() == "q":
            _running = False
            return False   # stops the pynput listener


# ──────────────────────────────────────────────────────────────
#  AUTO-SPLIT  (for lines that are too wide for the OLED)
# ──────────────────────────────────────────────────────────────
def auto_split(text: str, max_len: int = OLED_LARGE_MAX):
    """
    Split a long lyric into (line1, line2) for 2-line OLED mode.
    Picks the word boundary that minimises the longer half, so the two
    rows are as balanced as possible.
    """
    if not text or len(text) <= max_len:
        return text, ""
    best, best_w = None, None
    for i, ch in enumerate(text):
        if ch != " ":
            continue
        worst = max(len(text[:i].strip()), len(text[i:].strip()))
        if best_w is None or worst < best_w:
            best, best_w = i, worst
    if best is None:
        return text, ""
    return text[:best].strip(), text[best:].strip()


# ──────────────────────────────────────────────────────────────
#  EXPORT → Arduino .h file
# ──────────────────────────────────────────────────────────────
def export():
    with _lock:
        stamps = list(_stamps)

    n   = len(stamps)
    nL  = len(LYRICS)

    rows = []
    for i in range(nL):
        text      = LYRICS[i]
        start_ms  = stamps[i]  if i < n     else 0
        end_ms    = stamps[i+1] if i+1 < n  else (stamps[-1] + 4000 if stamps else 4000)
        missing   = i >= n

        l1, l2 = auto_split(text)
        l1_esc  = l1.replace('"', '\\"')
        l2_esc  = l2.replace('"', '\\"')

        note = "  // ← TIMESTAMP MISSING — fill manually" if missing else ""
        rows.append(
            f'  {{"{l1_esc}", "{l2_esc}", {start_ms}UL, {end_ms}UL}},{note}'
        )

    duration = (stamps[-1] + 6000) if stamps else 0

    content = (
        "// ╔══════════════════════════════════════════════════════╗\n"
        "// ║  Generated by MasaIni_Stamper.py                   ║\n"
        "// ║  #included by MasaIni_LyricsVideo.ino              ║\n"
        "// ╚══════════════════════════════════════════════════════╝\n"
        "\n"
        "#pragma once\n"
        "\n"
        "struct Lyric {\n"
        "  const char* line1;        // first display row\n"
        "  const char* line2;        // second row, empty for single-line\n"
        "  unsigned long startMs;    // ms from song start\n"
        "  unsigned long endMs;\n"
        "};\n"
        "\n"
        f"#define SONG_DURATION_MS  ({duration}UL)\n"
        "\n"
        "const Lyric lyrics[] = {\n"
        + "\n".join(rows)
        + "\n};\n"
        "const int NUM_LYRICS = sizeof(lyrics) / sizeof(Lyric);\n"
    )

    # ── session summary ─────────────────────────────────────
    print()
    print("═" * W)
    print("  SESSION SUMMARY")
    print("═" * W)
    print(f"  Lines stamped   : {n} / {nL}")
    if stamps:
        print(f"  First stamp     : {_fmt(stamps[0])}")
        print(f"  Last stamp      : {_fmt(stamps[-1])}")
        print(f"  Song duration   : {_fmt(duration)}")
    print()

    # ── arduino output ──────────────────────────────────────
    print("═" * W)
    print("  ARDUINO OUTPUT  (lyrics_timestamps.h)")
    print("═" * W)
    print()
    print(content)

    # ── save file ───────────────────────────────────────────
    fname = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "lyrics_timestamps.h")
    with open(fname, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"  ✓  Saved to:  {fname}")
    print(f"     MasaIni_LyricsVideo.ino #includes it — just re-flash.")
    print()


# ──────────────────────────────────────────────────────────────
#  MAIN
# ──────────────────────────────────────────────────────────────
def main():
    print(__doc__)

    # Quick preflight
    try:
        import pynput  # noqa: F401
    except ImportError:
        print("  ERROR: pynput not found.")
        print("  Run:   pip install pynput")
        sys.exit(1)

    print(f"  Lyrics loaded: {len(LYRICS)} entries ({sum(1 for l in LYRICS if l)} lines + {sum(1 for l in LYRICS if not l)} gaps)")
    print()
    input("  Press Enter to open the stamping UI, then start your music player...")

    # Start keyboard listener (runs in its own daemon thread)
    listener = pkb.Listener(on_press=on_press)
    listener.start()

    # ── render loop ──────────────────────────────────────────
    # - Fast (50 ms) when the timer is running — keeps elapsed time live
    # - Slower (200 ms) while waiting for first SPACE
    while True:
        with _lock:
            running = _running
            t0      = _t0
        if not running:
            break
        draw()
        time.sleep(0.05 if t0 else 0.2)

    # final frame
    draw()

    print()
    print("  Generating Arduino output...")
    time.sleep(0.3)
    export()

    listener.join()
    print("  Done. Selamat tinggal!")


if __name__ == "__main__":
    main()
