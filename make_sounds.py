"""Generates Block Catch's sound effects and music into sounds/*.ogg.

Everything is synthesized here (chiptune style: square, triangle and noise waves), so there is nothing to license.
Edit a sound below, run this again, and the game picks up the new files.

    .venv\\Scripts\\pip install numpy soundfile     (once)
    .venv\\Scripts\\python make_sounds.py
"""
from pathlib import Path

import numpy as np
import soundfile as sf

RATE = 22050
OUT = Path(__file__).resolve().parent / "sounds"
rng = np.random.default_rng(7)  # fixed seed, so the noise sounds come out the same every run


# ---------- building blocks ----------
def samples(dur):
    return int(dur * RATE)


def osc(freq, dur, wave="square", duty=0.5):
    """A tone. freq is a number, or an array of per-sample frequencies for slides."""
    n = samples(dur)
    f = np.full(n, float(freq)) if np.ndim(freq) == 0 else np.resize(freq, n)
    phase = np.cumsum(f) / RATE % 1.0
    if wave == "square":
        return np.where(phase < duty, 1.0, -1.0)
    if wave == "triangle":
        return 4 * np.abs(phase - 0.5) - 1
    if wave == "saw":
        return 2 * phase - 1
    return np.sin(2 * np.pi * phase)


def slide(f0, f1, dur):
    """Frequencies gliding from f0 to f1 (evenly in pitch)."""
    return f0 * (f1 / f0) ** np.linspace(0, 1, samples(dur))


def noise(dur, hold=1):
    """8-bit style noise; a bigger hold gives a lower, rougher rumble."""
    n = samples(dur)
    return np.repeat(rng.choice([-1.0, 1.0], n // hold + 1), hold)[:n]


def fade(sound, attack=0.004, speed=8.0):
    """Quick attack, then an exponential die-away (higher speed = shorter)."""
    t = np.arange(len(sound)) / RATE
    env = np.exp(-t * speed)
    a = min(len(sound), samples(attack))
    env[:a] *= np.linspace(0, 1, a)
    env[-samples(0.004):] *= np.linspace(1, 0, samples(0.004))  # no click at the end
    return sound * env


def held(sound, release=0.03):
    """Even volume with a short fade in and out, for notes in a melody."""
    env = np.ones(len(sound))
    a, r = min(len(sound) // 2, samples(0.004)), min(len(sound) // 2, samples(release))
    env[:a] = np.linspace(0, 1, a)
    env[len(sound) - r:] = np.linspace(1, 0, r)
    return sound * env


def seq(*parts):
    return np.concatenate(parts)


def mix(*parts):
    out = np.zeros(max(len(p) for p in parts))
    for p in parts:
        out[:len(p)] += p
    return out


def note(name):
    """'A4', 'C#5' ... -> frequency in Hz."""
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    pitch, octave = name[:-1], int(name[-1])
    return 440 * 2 ** ((names.index(pitch) + 12 * (octave + 1) - 69) / 12)


def tones(names, each, wave="square", duty=0.25, last=None):
    """A quick run of notes (arpeggio); the last one can ring longer."""
    out = []
    for i, n in enumerate(names):
        d = last if (last and i == len(names) - 1) else each
        out.append(held(osc(note(n), d, wave, duty), 0.01))
    return seq(*out)


def save(name, sound, volume):
    OUT.mkdir(exist_ok=True)
    sound = (sound / max(1e-9, np.abs(sound).max()) * volume).astype(np.float32)
    # written in small blocks: libsndfile's Vorbis encoder overflows its stack on big ones (Windows)
    with sf.SoundFile(OUT / f"{name}.ogg", "w", RATE, 1, format="OGG", subtype="VORBIS") as f:
        for i in range(0, len(sound), 2048):
            f.write(sound[i:i + 2048])


# ---------- sound effects ----------
def make_effects():
    # block hit: a coin-like two-step blip, a little higher at each combo level (x1..x4)
    for level in range(1, 5):
        base = note("C5") * 2 ** ((level - 1) * 3 / 12)
        save(f"hit{level}", fade(seq(osc(base, 0.035, duty=0.25), osc(base * 1.5, 0.09, duty=0.25)), speed=14), 0.32)
    save("air", fade(tones(["G5", "B5", "D6", "G6"], 0.032), speed=10), 0.32)
    save("gold", seq(tones(["C6", "E6", "G6", "C7"], 0.04),
                     fade(mix(osc(note("E7"), 0.3, duty=0.5) * 0.5, osc(note("C7"), 0.3, duty=0.25)), speed=9)), 0.4)
    save("crash", fade(mix(osc(slide(170, 45, 0.3), 0.3, "sine"), noise(0.3, 6) * 0.5), speed=9), 0.55)
    save("boom", mix(fade(noise(0.7, 10), speed=5), fade(osc(slide(130, 35, 0.5), 0.5, "sine"), speed=6) * 0.8), 0.75)
    save("fizzle", fade(noise(0.25, 2), speed=14), 0.18)
    save("jump", fade(osc(slide(260, 620, 0.12), 0.12, duty=0.5), speed=12), 0.22)
    save("walljump", mix(fade(osc(slide(360, 880, 0.11), 0.11, duty=0.25), speed=12),
                         fade(noise(0.03, 1), speed=60) * 0.5), 0.25)
    save("blockjump", mix(fade(osc(slide(330, 990, 0.14), 0.14, duty=0.25), speed=10),
                          fade(osc(slide(660, 1320, 0.1), 0.1, duty=0.5), speed=14) * 0.4), 0.26)
    swell = np.sin(np.linspace(0, np.pi, samples(0.16)))
    save("dash", mix(noise(0.16, 1) * swell * 0.6, osc(slide(500, 1100, 0.16), 0.16, duty=0.125) * swell * 0.4), 0.22)
    # pause and resume: a sleepy snore, countdown ticks, and a bright wake-up
    save("snore", mix(fade(osc(slide(140, 90, 0.5), 0.5, "sine"), attack=0.15, speed=4),
                      fade(noise(0.5, 6), attack=0.15, speed=4) * 0.3), 0.3)
    save("tick", fade(osc(note("A5"), 0.08, duty=0.5), speed=18), 0.22)
    save("wake", tones(["G5", "C6", "E6", "G6"], 0.035, "square", 0.5, last=0.14), 0.3)
    save("heart", tones(["C5", "E5", "G5", "C6"], 0.06, "square", 0.5, last=0.18), 0.32)
    jitter = slide(70, 40, 0.45) * (1 + 0.4 * rng.standard_normal(samples(0.45)))
    save("zap", fade(mix(osc(jitter, 0.45, "saw"), noise(0.45, 3) * 0.7), speed=6), 0.42)
    t = np.arange(samples(0.4)) / RATE
    save("magnet", held(osc(320 + 90 * np.sin(2 * np.pi * 22 * t), 0.4, duty=0.25), 0.1), 0.24)
    tremolo = 0.6 + 0.4 * np.sign(np.sin(2 * np.pi * 18 * np.arange(samples(0.32)) / RATE))
    save("speed", held(osc(slide(300, 1500, 0.32), 0.32, duty=0.25) * tremolo, 0.06), 0.24)
    save("combo", tones(["G5", "C6", "E6", "G6"], 0.05, last=0.16), 0.3)
    save("hat", mix(tones(["C5", "E5", "G5", "C6"], 0.08, "square", 0.5, last=0.35),
                    tones(["E4", "G4", "C5", "E5"], 0.08, "triangle", last=0.35) * 0.7), 0.38)
    save("gameover", mix(tones(["G4", "E4", "C4", "G3"], 0.16, "square", 0.5, last=0.5),
                         tones(["C4", "G3", "E3", "C3"], 0.16, "triangle", last=0.5)), 0.4)
    save("click", fade(osc(1200, 0.03, duty=0.5), speed=40), 0.15)
    beep = held(osc(note("C6"), 0.06, duty=0.5), 0.01)
    save("warn", seq(beep, np.zeros(samples(0.05)), beep), 0.2)


# ---------- music ----------
BPM = 140
STEP = 60 / BPM / 4  # one 16th note
CHORDS = {"Am": ["A", "C", "E"], "F": ["F", "A", "C"], "C": ["C", "E", "G"], "G": ["G", "B", "D"], "E": ["E", "G#", "B"]}
BASS = {"Am": "A2", "F": "F2", "C": "C3", "G": "G2", "E": "E2"}
# 16 bars: chord, then the melody in 8th notes ("-" holds the note before, "." is a rest)
SONG = [
    ("Am", "E5 . E5 D5 C5 . A4 ."), ("F", "C5 . D5 . E5 - - ."), ("C", "G5 . E5 . D5 C5 D5 ."), ("G", "B4 - - . G4 . B4 D5"),
    ("Am", "E5 . E5 D5 C5 . A4 ."), ("F", "C5 . D5 . F5 - E5 ."), ("C", "E5 D5 C5 . G4 . C5 ."), ("G", "D5 - - - - . . ."),
    ("F", "A5 . G5 . F5 . E5 ."), ("G", "D5 . E5 . G5 - - ."), ("Am", "E5 . D5 . C5 . D5 ."), ("Am", "E5 - - . . . E5 G5"),
    ("F", "A5 . G5 . F5 . A5 ."), ("G", "B5 . A5 . G5 - D5 ."), ("C", "E5 . G5 . C6 - - ."), ("E", "B5 - G#5 - E5 - - ."),
]


def make_music():
    bar = 16 * STEP
    length = samples(bar * len(SONG))
    track = np.zeros(length + samples(1.0))  # extra room for notes ringing past the end

    def put(sound, at, volume):
        i = samples(at)
        track[i:i + len(sound)] += sound * volume

    kick = fade(osc(slide(150, 45, 0.12), 0.12, "sine"), speed=18)
    snare = fade(noise(0.12, 3), speed=22)
    hihat = fade(noise(0.03, 1), speed=90)
    for b, (chord, melody) in enumerate(SONG):
        start = b * bar
        busy = b >= 8  # the second half drives a bit harder
        # bass: root, octave up, on 8th notes
        root = note(BASS[chord])
        for k in range(8):
            f = root * (2 if k % 2 else 1)
            put(held(osc(f, STEP * 2 * 0.9, "triangle"), 0.02), start + k * 2 * STEP, 0.32)
        # arpeggio: chord tones on 16ths, quiet in the background
        tones_ = [note(n + "4") for n in CHORDS[chord]] + [note(CHORDS[chord][0] + "5")]
        for k in range(16):
            put(held(osc(tones_[k % 4], STEP * 0.8, duty=0.125), 0.01), start + k * STEP, 0.05)
        # drums
        for k in range(16):
            at = start + k * STEP
            if k in (0, 8) or (busy and k in (6, 10)):
                put(kick, at, 0.5)
            if k in (4, 12):
                put(snare, at, 0.2)
            if k % 2 == 1 or busy:
                put(hihat, at, 0.06)
        # melody, with a touch of vibrato on long notes
        slots = melody.split()
        k = 0
        while k < 8:
            if slots[k] in (".", "-"):
                k += 1
                continue
            n = 1
            while k + n < 8 and slots[k + n] == "-":
                n += 1
            dur = n * 2 * STEP * 0.92
            t = np.arange(samples(dur)) / RATE
            vibrato = 1 + 0.006 * np.sin(2 * np.pi * 6 * t) * np.clip(t / 0.15 - 0.5, 0, 1)
            put(held(osc(note(slots[k]) * vibrato, dur, duty=0.25), 0.04), start + k * 2 * STEP, 0.15)
            k += n
    # wrap the ringing tail around to the start, so the loop is seamless
    tail = track[length:]
    track = track[:length]
    track[:len(tail)] += tail
    save("music", track, 0.8)


if __name__ == "__main__":
    make_effects()
    make_music()
    for f in sorted(OUT.glob("*.ogg")):
        print(f"{f.name:14} {f.stat().st_size // 1024:4} KB")
