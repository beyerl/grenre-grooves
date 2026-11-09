#!/usr/bin/env python3
"""Cut every track of every groove into 64 sixteenth-note MP3 bits.

Each MIDI track is rendered on its own, so a note that rings across a sixteenth
boundary carries on into the next bit. Played in series, the 64 bits of a track
are the whole track. Played in parallel, the four tracks are the whole song. One
gain per song keeps the balance between the tracks.

Needs ffmpeg, libfluidsynth and: pip install mido numpy pyfluidsynth

    python3 tools/make_demo_bits.py [SOURCE_DIR] [OUT_DIR]
"""
import pathlib
import subprocess
import sys

import fluidsynth
import mido
import numpy as np

SF2 = "/usr/share/sounds/sf2/TimGM6mb.sf2"
SR = 48000  # the only common rate where a sixteenth at 120 BPM is a whole number of samples
BITS = 64
GAIN = 0.5
FADE_S = 0.005  # the render stops at the last sixteenth; avoids a click there
BITRATE = "192k"


def read_tracks(path):
    """Return (samples_per_bit, [(name, channel, program, ccs, events)])."""
    mf = mido.MidiFile(path)
    tempo = next(m.tempo for t in mf.tracks for m in t if m.type == "set_tempo")
    if any(m.tempo != tempo for t in mf.tracks for m in t if m.type == "set_tempo"):
        raise ValueError(f"{path}: tempo changes are not supported")
    per_bit = tempo / 1e6 / 4 * SR
    if per_bit != int(per_bit):
        raise ValueError(f"{path}: a sixteenth is not a whole number of samples")
    ticks_to_samples = tempo / 1e6 / mf.ticks_per_beat * SR

    tracks = []
    for track in mf.tracks[1:]:
        name, channel, program, ccs, events, tick = None, None, 0, [], [], 0
        for m in track:
            tick += m.time
            if m.type == "track_name":
                name = m.name
            elif m.type == "program_change":
                channel, program = m.channel, m.program
            elif m.type == "control_change":
                ccs.append((m.control, m.value))
            elif m.type in ("note_on", "note_off", "pitchwheel"):
                events.append((round(tick * ticks_to_samples), m))
        tracks.append((name, channel, program, ccs, events))
    if len(tracks) != 4:
        raise ValueError(f"{path}: expected 4 tracks, found {len(tracks)}")
    return int(per_bit), tracks


def render(track, total):
    """Render one track alone as float stereo samples of exactly `total` frames."""
    _, channel, program, ccs, events = track
    fs = fluidsynth.Synth(samplerate=float(SR), gain=GAIN)
    sfid = fs.sfload(SF2)
    fs.set_reverb(0.6, 0.4, 0.8, 0.5)
    fs.program_select(channel, sfid, 128 if channel == 9 else 0, program)
    for control, value in ccs:
        fs.cc(channel, control, value)
    chunks, now = [], 0
    for at, m in events:
        at = min(at, total)
        if at > now:
            chunks.append(fs.get_samples(at - now))
            now = at
        if m.type == "note_on" and m.velocity:
            fs.noteon(channel, m.note, m.velocity)
        elif m.type in ("note_on", "note_off"):
            fs.noteoff(channel, m.note)
        else:
            fs.pitch_bend(channel, m.pitch)
    if now < total:
        chunks.append(fs.get_samples(total - now))
    fs.delete()
    return np.concatenate(chunks).astype(np.float64).reshape(-1, 2)


def encode(pcm, path):
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "s16le", "-ar", str(SR), "-ac", "2", "-i", "-",
         "-codec:a", "libmp3lame", "-b:a", BITRATE, "-id3v2_version", "0", str(path)],
        input=pcm.tobytes(), check=True)


def decode(path):
    raw = subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-i", str(path), "-f", "s16le", "-ar", str(SR), "-ac", "2", "-"],
        capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.int16).astype(np.float64).reshape(-1, 2)


def snr_db(reference, other):
    noise = np.sum((reference - other) ** 2)
    return float("inf") if noise == 0 else 10 * np.log10(np.sum(reference ** 2) / noise)


def process(mid, out):
    per_bit, tracks = read_tracks(mid)
    total = per_bit * BITS
    stems = [render(t, total) for t in tracks]

    fade = np.ones(total)
    n = int(FADE_S * SR)
    fade[-n:] = np.linspace(1, 0, n)
    fade = fade[:, None]
    mix = sum(stems)
    peak = np.abs(mix).max()
    gain = min(32767 * 10 ** (-1 / 20) / peak, 32767 / max(np.abs(s).max() for s in stems))
    stems = [np.rint(s * fade * gain).astype(np.int16) for s in stems]

    decoded = []
    for (name, *_), stem in zip(tracks, stems):
        folder = out / mid.stem / name.lower()
        folder.mkdir(parents=True, exist_ok=True)
        bits = []
        for i in range(BITS):
            path = folder / f"{i + 1:02d}.mp3"
            encode(stem[i * per_bit:(i + 1) * per_bit], path)
            bit = decode(path)
            if len(bit) != per_bit:
                raise ValueError(f"{path}: decodes to {len(bit)} samples, expected {per_bit}")
            bits.append(bit)
        decoded.append(np.concatenate(bits))

    track_snr = [snr_db(s.astype(np.float64), d) for s, d in zip(stems, decoded)]
    song = sum(s.astype(np.float64) for s in stems)
    print(f"{mid.stem:24s} track SNR {min(track_snr):5.1f} dB min, "
          f"song SNR {snr_db(song, sum(decoded)):5.1f} dB, peak {np.abs(sum(decoded)).max():.0f}")


def main():
    source = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "genre_grooves_Am-C-Em-G")
    out = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else "demo")
    mids = sorted(source.glob("*.mid"))
    if not mids:
        sys.exit(f"no MIDI files in {source}")
    for mid in mids:
        process(mid, out)


if __name__ == "__main__":
    main()
