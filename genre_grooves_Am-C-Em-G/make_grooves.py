import os, random, subprocess, wave
import numpy as np
import mido
import fluidsynth

PPQ, BPM = 480, 120
SPB = 60.0 / BPM
SF2 = '/usr/share/sounds/sf2/TimGM6mb.sf2'
OUT = '/home/claude/out'
os.makedirs(OUT, exist_ok=True)

NAMES = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5, 'F#': 6, 'G': 7,
         'G#': 8, 'A': 9, 'A#': 10, 'B': 11}
def N(s):
    return 12 * (int(s[-1]) + 1) + NAMES[s[:-1]]
def NN(*names):
    return [N(x) for x in names]

# Am | C | Em | G
ROOT = NN('A2', 'C3', 'E2', 'G2')
TRIAD = [NN('A3', 'C4', 'E4'), NN('G3', 'C4', 'E4'), NN('G3', 'B3', 'E4'), NN('G3', 'B3', 'D4')]
HIGH = [NN('A4', 'C5', 'E5'), NN('G4', 'C5', 'E5'), NN('G4', 'B4', 'E5'), NN('G4', 'B4', 'D5')]
SEV = [NN('G3', 'A3', 'C4', 'E4'), NN('G3', 'B3', 'C4', 'E4'),
       NN('G3', 'B3', 'D4', 'E4'), NN('G3', 'B3', 'D4', 'A4')]

# GM drum keys
KICK, RIM, SNARE, CLAP, ESNARE = 36, 37, 38, 39, 40
LTOM, CHH, LMTOM, PHH, MTOM, OHH, HMTOM, CRASH, HTOM, RIDE = 41, 42, 43, 44, 45, 46, 47, 49, 50, 51
TAMB, COWBELL, HBONGO, LBONGO, MCONGA, HCONGA, LCONGA = 54, 56, 60, 61, 62, 63, 64
CABASA, MARACAS, CLAVES, SHAKER = 69, 70, 75, 82


class Track:
    def __init__(self, name, ch, prog, vol=100, pan=64, rev=40, cho=0, bank=0):
        self.name, self.ch, self.prog, self.bank = name, ch, prog, bank
        self.vol, self.pan, self.rev, self.cho = vol, pan, rev, cho
        self.notes = []   # (start_beat, dur_beat, pitch, vel)
        self.bends = []   # (beat, value -8192..8191)

    def n(self, start, dur, pitch, vel=90):
        self.notes.append((start, dur, pitch, vel))

    def hit(self, start, pitch, vel=100, dur=0.12):
        self.n(start, dur, pitch, vel)

    def chord(self, start, dur, pitches, vel=80):
        for p in pitches:
            self.n(start, dur, p, vel)


def song():
    return (Track('Drums', 9, 0, vol=110, rev=25, bank=128),
            Track('Bass', 0, 38, vol=105, rev=10),
            Track('Accompaniment', 1, 0, vol=80, pan=50, rev=55, cho=30),
            Track('Melody', 2, 80, vol=92, pan=78, rev=50, cho=20))


def bars():
    for b in range(4):
        yield b, b * 4.0


def melody_from(tr, rhythm, pitch_bars, vel=95):
    for b, o in bars():
        for (s, d), p in zip(rhythm, pitch_bars[b]):
            if p:
                tr.n(o + s, d, N(p), vel)


# ---------------------------------------------------------------- genres
def trance():
    D, B, A, M = song()
    D.prog = 24  # Electronic kit
    B.prog, A.prog, M.prog = 38, 81, 81
    A.vol, M.vol = 70, 90
    for b, o in bars():
        for i in range(4):
            D.hit(o + i, KICK, 120)
            D.hit(o + i + 0.5, OHH, 85)
            for k in (0, 1, 2, 3):
                D.hit(o + i + k * 0.25, CHH, 55 if k % 2 == 0 else 40)
        D.hit(o + 1, CLAP, 105); D.hit(o + 3, CLAP, 105)
        # rolling offbeat bass
        for i in range(4):
            for k in (1, 2, 3):
                B.n(o + i + k * 0.25, 0.22, ROOT[b], 105 if k == 2 else 90)
        # trance gate on the chord
        gate = [1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 1, 1, 0]
        for k, g in enumerate(gate):
            if g:
                A.chord(o + k * 0.25, 0.2, [p + 12 for p in TRIAD[b]], 70 + (15 if k % 4 == 0 else 0))
    D.hit(0, CRASH, 110)
    for k in range(8):  # snare build into the loop
        D.hit(14 + k * 0.25, SNARE, 50 + k * 8)
    lead = [['E5', 'E5', 'A5', 'E5', 'C5', 'E5', 'B4', 'C5'],
            ['E5', 'E5', 'G5', 'E5', 'C5', 'E5', 'D5', 'C5'],
            ['G5', 'G5', 'B5', 'G5', 'E5', 'G5', 'D5', 'E5'],
            ['D5', 'D5', 'G5', 'D5', 'B4', 'D5', 'A4', 'B4']]
    melody_from(M, [(k * 0.5, 0.45) for k in range(8)], lead, 92)
    return (D, B, A, M), {}


def house():
    D, B, A, M = song()
    D.prog = 25  # 808/909-ish
    B.prog, A.prog, M.prog = 38, 1, 54
    for b, o in bars():
        for i in range(4):
            D.hit(o + i, KICK, 118)
            D.hit(o + i + 0.5, OHH, 80)
            for k in range(4):
                D.hit(o + i + k * 0.25, SHAKER, 60 if k == 2 else 42)
            D.hit(o + i + 0.25, CHH, 45); D.hit(o + i + 0.75, CHH, 50)
        D.hit(o + 1, CLAP, 100); D.hit(o + 3, CLAP, 100)
        r = ROOT[b]
        for s, d, iv, v in [(0.5, 0.4, 0, 105), (1.5, 0.4, 0, 100), (2.5, 0.3, 12, 95),
                            (3.25, 0.2, 7, 85), (3.5, 0.4, 0, 100)]:
            B.n(o + s, d, r + iv, v)
        for s, d in [(0, 0.3), (0.75, 0.3), (1.5, 0.6), (2.5, 0.3), (3.25, 0.3)]:
            A.chord(o + s, d, [p + 12 for p in SEV[b]], 82)
    D.hit(0, CRASH, 100)
    for s, d, p in [(0.5, .5, 'E5'), (1, .5, 'D5'), (1.5, 1, 'C5'), (3, .5, 'A4'), (3.5, .5, 'C5'),
                    (4.5, .5, 'E5'), (5, .5, 'G5'), (5.5, 1, 'E5'), (7, .5, 'D5'), (7.5, .5, 'C5'),
                    (8.5, .5, 'B4'), (9, .5, 'D5'), (9.5, 1, 'E5'), (11, .5, 'G5'), (11.5, .5, 'E5'),
                    (12.5, .5, 'D5'), (13, .5, 'B4'), (13.5, 1.5, 'D5'), (15, .5, 'B4'), (15.5, .5, 'C5')]:
        M.n(s, d, N(p), 90)
    return (D, B, A, M), {'swing16': 0.04}


def dancehall():
    D, B, A, M = song()
    B.prog, A.prog, M.prog = 38, 17, 80
    for b, o in bars():
        for s in (0, 1.5, 3):
            D.hit(o + s, KICK, 120)
        D.hit(o + 1, SNARE, 105); D.hit(o + 3, SNARE, 105)
        D.hit(o + 1, CLAP, 80); D.hit(o + 3, CLAP, 80)
        for k in range(8):
            D.hit(o + k * 0.5, CHH, 70 if k % 2 else 55)
        D.hit(o + 3.75, CHH, 50); D.hit(o + 1.75, CHH, 45)
        for s in (0, 0.75, 1.5, 2.5, 3.25):
            D.hit(o + s, CLAVES, 70)
        r = ROOT[b] - 12
        for s, d, iv in [(0, 0.7, 0), (1.5, 0.7, 0), (3, 0.4, 0), (3.5, 0.3, 7)]:
            B.n(o + s, d, r, 110) if iv == 0 else B.n(o + s, d, r + iv, 95)
        for i in range(4):
            A.chord(o + i + 0.5, 0.18, TRIAD[b], 78)
    rhythm = [(0, .25), (.75, .25), (1.5, .25), (2, .5), (2.75, .25), (3.5, .5)]
    pb = [['A4', 'A4', 'C5', 'E5', 'D5', 'C5'], ['C5', 'C5', 'E5', 'G5', 'E5', 'D5'],
          ['B4', 'B4', 'D5', 'E5', 'D5', 'B4'], ['D5', 'D5', 'B4', 'G4', 'A4', 'B4']]
    melody_from(M, rhythm, pb, 95)
    return (D, B, A, M), {}


def reggaeton():
    D, B, A, M = song()
    D.prog = 25
    B.prog, A.prog, M.prog = 38, 24, 81
    A.vol, M.vol = 95, 82
    for b, o in bars():
        for i in range(4):
            D.hit(o + i, KICK, 118)
            D.hit(o + i + 0.5, CHH, 60); D.hit(o + i, CHH, 45)
        for s in (0.75, 1.5, 2.75, 3.5):
            D.hit(o + s, ESNARE, 100)
        for k in range(16):
            D.hit(o + k * 0.25, CABASA, 45 if k % 2 else 30)
        r = ROOT[b] - 12
        for s in (0, 0.75, 1.5, 2, 2.75, 3.5):
            B.n(o + s, 0.6 if s % 1 != 0.5 else 0.45, r, 108)
        t = TRIAD[b]
        arp = [t[0] - 12, t[2] - 12 if t[2] - 12 > t[0] - 12 else t[1], t[0], t[1], t[2], t[1], t[0], t[2]]
        arp = [ROOT[b] + 12, t[0], t[1], t[2], t[1] + 12, t[2], t[1], t[0]]
        for k, p in enumerate(arp):
            A.n(o + k * 0.5, 0.45, p, 80 if k % 2 == 0 else 68)
    D.hit(0, CRASH, 95)
    rhythm = [(0.5, .25), (0.75, .25), (1, .5), (1.75, .75), (2.5, .5), (3, .5), (3.5, .5)]
    pb = [['C5', 'D5', 'E5', 'E5', 'D5', 'C5', 'A4'], ['C5', 'D5', 'E5', 'G5', 'E5', 'D5', 'C5'],
          ['B4', 'C5', 'B4', 'G4', 'B4', 'D5', 'E5'], ['D5', 'E5', 'D5', 'B4', 'G4', 'A4', None]]
    melody_from(M, rhythm, pb, 88)
    return (D, B, A, M), {}


def rockers_dub():
    D, B, A, M = song()
    B.prog, A.prog, M.prog = 33, 27, 22
    B.vol, A.vol = 120, 78
    for b, o in bars():
        D.hit(o + 0, KICK, 115); D.hit(o + 2, KICK, 118)
        D.hit(o + 2, SNARE, 100)
        D.hit(o + 1, RIM, 70); D.hit(o + 3, RIM, 75)
        for k in range(8):
            D.hit(o + k * 0.5, CHH, 62 if k % 2 == 0 else 48)
        D.hit(o + 3.5, OHH, 60)
        for i in (1, 3):
            A.chord(o + i, 0.15, HIGH[b], 85)          # skank on 2 & 4
            A.chord(o + i + 0.5, 0.1, HIGH[b], 50)     # ghost chop
    for s, p in [(15, HTOM), (15.25, HMTOM), (15.5, MTOM), (15.75, LTOM)]:
        D.hit(s, p, 95)
    bass = [[(0, .5, 33), (.75, .25, 33), (1.5, .5, 36), (2, 1, 40), (3, .5, 38), (3.5, .5, 36)],
            [(0, .5, 36), (.75, .25, 36), (1.5, .5, 40), (2, 1, 43), (3, .5, 41), (3.5, .5, 40)],
            [(0, .5, 28), (.75, .25, 28), (1.5, .5, 31), (2, 1, 35), (3, .5, 33), (3.5, .5, 31)],
            [(0, .5, 31), (.75, .25, 31), (1.5, .5, 35), (2, 1, 38), (3, .5, 36), (3.5, .5, 35)]]
    for b, o in bars():
        for s, d, p in bass[b]:
            B.n(o + s, d * 0.95, p, 112)
    for s, d, p in [(0, 1.5, 'E5'), (1.5, .5, 'D5'), (2, 1, 'C5'), (3, 1, 'A4'),
                    (4.5, .5, 'C5'), (5, .5, 'D5'), (5.5, 1.5, 'E5'), (7, 1, 'G5'),
                    (8, 1.5, 'G5'), (9.5, .5, 'E5'), (10, 2, 'B4'),
                    (12.5, .5, 'D5'), (13, .5, 'B4'), (13.5, .5, 'A4'), (14, 2, 'G4')]:
        M.n(s, d, N(p), 88)
    return (D, B, A, M), {'swing8': 0.08, 'jitter': 0.01, 'echo': True}


def dnb():
    D, B, A, M = song()
    D.prog = 16  # Power kit
    B.prog, A.prog, M.prog = 39, 89, 4
    A.vol, M.vol = 75, 96
    for b, o in bars():
        D.hit(o + 0, KICK, 120); D.hit(o + 2.5, KICK, 115)
        if b % 2 == 1:
            D.hit(o + 0.5, KICK, 90)
        D.hit(o + 1, SNARE, 118); D.hit(o + 3, SNARE, 118)
        for s in (1.75, 2.25, 3.75):
            D.hit(o + s, SNARE, 38)
        for k in range(16):
            D.hit(o + k * 0.25, CHH, 65 if k % 2 == 0 else 40)
        D.hit(o + 0.5, RIDE, 50); D.hit(o + 2, RIDE, 50)
        r = ROOT[b] - 12
        B.n(o, 2.4, r, 112); B.n(o + 2.5, 1.0, r, 105); B.n(o + 3.5, 0.45, r + 12, 95)
        A.chord(o, 3.95, [p + 12 for p in SEV[b]], 70)
    D.hit(0, CRASH, 110)
    for k in range(4):
        D.hit(15 + k * 0.25, SNARE, 70 + k * 12)
    rhythm = [(0, .75), (0.75, .75), (1.5, 1), (2.5, .5), (3, 1)]
    pb = [['E5', 'C5', 'A4', 'B4', 'C5'], ['E5', 'G5', 'E5', 'D5', 'C5'],
          ['B4', 'D5', 'E5', 'D5', 'B4'], ['D5', 'B4', 'G4', 'A4', 'B4']]
    melody_from(M, rhythm, pb, 92)
    return (D, B, A, M), {}


def afro_gqom():
    D, B, A, M = song()
    B.prog, A.prog, M.prog = 38, 52, 108
    A.vol, M.vol = 82, 100
    for b, o in bars():
        for s in (0, 0.75, 1.5, 2.5, 3.25):  # broken gqom kick
            D.hit(o + s, KICK, 120 if s in (0, 1.5) else 105)
        D.hit(o + 1, CLAP, 95); D.hit(o + 3, CLAP, 100)
        for s, p in [(0.5, MTOM), (1.25, LTOM), (2, HTOM), (2.75, MTOM), (3.5, LTOM), (3.75, LMTOM)]:
            D.hit(o + s, p, 90)
        for k in range(16):
            D.hit(o + k * 0.25, MARACAS, 70 if k % 4 == 2 else 45)
        for s, p in [(0.25, HCONGA), (1.0, LCONGA), (2.25, HCONGA), (3.0, MCONGA)]:
            D.hit(o + s, p, 70)
        r = ROOT[b] - 12
        for s, d in [(0, 0.7), (1.5, 0.5), (2.5, 1.2)]:
            B.n(o + s, d, r, 112)
        A.chord(o, 1.4, SEV[b], 78); A.chord(o + 2.5, 1.4, SEV[b], 70)
        h = HIGH[b]
        pat = [0, 2, 1, 2, 0, 1, 2, 1, 0, 2]
        pos = [0, .5, .75, 1.25, 1.5, 2, 2.5, 2.75, 3.25, 3.5]
        for s, i in zip(pos, pat):
            M.n(o + s, 0.3, h[i], 100 if s % 1 == 0 else 85)
    for k in range(8):
        D.hit(14 + k * 0.25, [HTOM, HMTOM, MTOM, LTOM][k % 4], 80 + k * 4)
    return (D, B, A, M), {'swing16': 0.025}


def dubstep():
    D, B, A, M = song()
    D.prog = 16
    B.prog, A.prog, M.prog = 81, 89, 80
    B.vol, B.rev = 100, 15
    A.vol, M.vol = 72, 80
    for b, o in bars():
        D.hit(o, KICK, 125); D.hit(o + 2, SNARE, 125); D.hit(o + 2, CLAP, 90)
        if b % 2 == 1:
            D.hit(o + 3.25, KICK, 100)
        D.hit(o + 1.5, KICK, 80)
        for k in range(8):
            D.hit(o + k * 0.5, CHH, 60)
        D.hit(o + 3.5, OHH, 70)
        r = ROOT[b] - 12
        # "wobble": retriggered saw bass, rate changes per half bar
        rate = [1 / 3, 1 / 4][b % 2]
        t = 0.0
        while t < 2.0 - 1e-6:
            B.n(o + t, rate * 0.8, r, 115 if abs(t % 1) < 1e-6 else 95)
            B.n(o + t, rate * 0.8, r + 12, 70)
            t += rate
        for s, d in [(2.5, 0.5), (3.0, 0.25), (3.25, 0.25), (3.5, 0.5)]:
            B.n(o + s, d * 0.9, r + (7 if s == 3.25 else 0), 110)
            B.n(o + s, d * 0.9, r + 12, 70)
        A.chord(o, 3.9, [p + 12 for p in TRIAD[b]], 60)
    D.hit(0, CRASH, 110)
    for s, d, p in [(0, 1, 'E5'), (1, .5, 'C5'), (1.5, 1.5, 'A4'),
                    (4, 1, 'E5'), (5, .5, 'G5'), (5.5, 1.5, 'E5'),
                    (8, 1, 'B4'), (9, .5, 'D5'), (9.5, 1.5, 'E5'),
                    (12, 1, 'D5'), (13, .5, 'B4'), (13.5, 2, 'G4')]:
        M.n(s, d, N(p), 85)
    return (D, B, A, M), {}


def trap():
    D, B, A, M = song()
    D.prog = 25  # TR-808
    B.prog, A.prog, M.prog = 38, 48, 9
    B.vol, A.vol, M.vol = 125, 70, 96
    for b, o in bars():
        kicks = [0, 0.75, 2.5] if b % 2 == 0 else [0, 1.5, 1.75, 3.25]
        for s in kicks:
            D.hit(o + s, KICK, 120)
        D.hit(o + 2, CLAP, 115); D.hit(o + 2, SNARE, 80)
        # hats: 8ths with 16th, triplet and 32nd rolls
        hats = [k * 0.5 for k in range(8)]
        if b == 0: hats += [1.25, 3.25]
        if b == 1: hats += [3 + i / 6 for i in range(1, 6)]
        if b == 2: hats += [1 + i * 0.125 for i in range(1, 4)] + [3.25, 3.75]
        if b == 3: hats += [2 + i * 0.125 for i in range(1, 8)] + [3 + i / 6 for i in range(6)]
        for s in sorted(set(round(h, 4) for h in hats)):
            D.hit(o + s, CHH, 75 if s % 0.5 == 0 else 52)
        D.hit(o + 3.5, OHH, 55)
        # 808 bass with glide into next bar
        r = ROOT[b] - 12
        B.n(o, 0.7, r, 120)
        B.n(o + 0.75, 1.2, r, 105)
        B.n(o + 2.5, 1.45, r, 110)
        A.chord(o, 3.95, TRIAD[b], 62)
    # 808 glide on the last bar back up toward the A
    B.bends += [(15.0, 0), (15.25, 1200), (15.5, 2600), (15.75, 4096), (15.98, 0)]
    rhythm = [(0, .25), (0.25, .25), (0.5, .5), (1.5, .25), (1.75, .25), (2, .5), (3, .5), (3.5, .5)]
    pb = [['A5', 'E5', 'C5', 'A5', 'E5', 'C5', 'B4', 'C5'],
          ['G5', 'E5', 'C5', 'G5', 'E5', 'C5', 'D5', 'E5'],
          ['G5', 'E5', 'B4', 'G5', 'E5', 'B4', 'D5', 'E5'],
          ['G5', 'D5', 'B4', 'G5', 'D5', 'B4', 'A4', 'B4']]
    melody_from(M, rhythm, pb, 90)
    return (D, B, A, M), {}


GENRES = [('01_trance', 'Trance', trance), ('02_dancehall', 'Dancehall', dancehall),
          ('03_reggaeton', 'Reggaeton', reggaeton), ('04_house', 'House', house),
          ('05_rockers_riddim_dub', 'Rockers Riddim Dub', rockers_dub),
          ('06_drum_and_bass', 'Drum and Bass', dnb), ('07_afrohouse_gqom', 'Afro House / Gqom', afro_gqom),
          ('08_dubstep', 'Dubstep', dubstep), ('09_trap', 'Trap', trap)]


# ---------------------------------------------------------------- feel
def apply_feel(tracks, opts, seed):
    rnd = random.Random(seed)
    for tr in tracks:
        new = []
        for s, d, p, v in tr.notes:
            q = round(s * 4)
            if opts.get('swing16') and abs(s * 4 - q) < 1e-6 and q % 2 == 1:
                s += opts['swing16']
            q8 = round(s * 2)
            if opts.get('swing8') and abs(s * 2 - q8) < 1e-6 and q8 % 2 == 1:
                s += opts['swing8']
            if opts.get('jitter') and s > 0:
                s += rnd.uniform(-opts['jitter'], opts['jitter'])
            v = max(1, min(127, v + rnd.randint(-5, 5)))
            new.append((max(0.0, s), min(d, 16 - s), p, v))
        tr.notes = new


# ---------------------------------------------------------------- midi
def write_midi(path, title, tracks):
    mf = mido.MidiFile(type=1, ticks_per_beat=PPQ)
    meta = mido.MidiTrack(); mf.tracks.append(meta)
    meta += [mido.MetaMessage('track_name', name=title, time=0),
             mido.MetaMessage('time_signature', numerator=4, denominator=4, time=0),
             mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(BPM), time=0),
             mido.MetaMessage('end_of_track', time=PPQ * 16)]
    for tr in tracks:
        mt = mido.MidiTrack(); mf.tracks.append(mt)
        ev = []
        for s, d, p, v in tr.notes:
            ev.append((round(s * PPQ), 1, mido.Message('note_on', channel=tr.ch, note=p, velocity=v)))
            ev.append((round((s + d) * PPQ), 0, mido.Message('note_off', channel=tr.ch, note=p, velocity=0)))
        for s, val in tr.bends:
            ev.append((round(s * PPQ), 2, mido.Message('pitchwheel', channel=tr.ch, pitch=val)))
        ev.sort(key=lambda e: (e[0], e[1]))
        head = [mido.MetaMessage('track_name', name=tr.name, time=0)]
        if tr.ch != 9:
            head += [mido.Message('control_change', channel=tr.ch, control=0, value=0, time=0)]
        head += [mido.Message('program_change', channel=tr.ch, program=tr.prog, time=0),
                 mido.Message('control_change', channel=tr.ch, control=7, value=tr.vol, time=0),
                 mido.Message('control_change', channel=tr.ch, control=10, value=tr.pan, time=0),
                 mido.Message('control_change', channel=tr.ch, control=91, value=tr.rev, time=0),
                 mido.Message('control_change', channel=tr.ch, control=93, value=tr.cho, time=0)]
        mt += head
        last = 0
        for t, _, m in ev:
            m.time = t - last; last = t
            mt.append(m)
        mt.append(mido.MetaMessage('end_of_track', time=max(0, PPQ * 16 - last)))
    mf.save(path)


# ---------------------------------------------------------------- render
SR = 44100
def render(path_wav, tracks, tail=2.5, loops=1):
    fs = fluidsynth.Synth(samplerate=float(SR), gain=0.5)
    sfid = fs.sfload(SF2)
    fs.set_reverb(0.6, 0.4, 0.8, 0.5)
    ev = []
    for L in range(loops):
        off = L * 16.0
        for tr in tracks:
            for s, d, p, v in tr.notes:
                ev.append(((off + s) * SPB, 1, tr.ch, p, v))
                ev.append(((off + s + d) * SPB, 0, tr.ch, p, 0))
            for s, val in tr.bends:
                ev.append(((off + s) * SPB, 2, tr.ch, val, 0))
    ev.sort(key=lambda e: (e[0], e[1]))
    for tr in tracks:
        fs.program_select(tr.ch, sfid, tr.bank, tr.prog)
        for c, val in ((7, tr.vol), (10, tr.pan), (91, tr.rev), (93, tr.cho)):
            fs.cc(tr.ch, c, val)
    chunks, now = [], 0
    for t, kind, ch, p, v in ev:
        smp = int(round(t * SR))
        if smp > now:
            chunks.append(fs.get_samples(smp - now)); now = smp
        if kind == 1: fs.noteon(ch, p, v)
        elif kind == 0: fs.noteoff(ch, p)
        else: fs.pitch_bend(ch, p)
    total = int((loops * 16 * SPB + tail) * SR)
    chunks.append(fs.get_samples(total - now))
    fs.delete()
    audio = np.concatenate(chunks).astype(np.int16)
    with wave.open(path_wav, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(audio.tobytes())


def to_mp3(wav, mp3, echo=False):
    af = []
    if echo:  # dub tape-echo flavour: dotted-8th delay
        af.append('aecho=0.85:0.6:375|750:0.35|0.18')
    af += ['acompressor=threshold=-18dB:ratio=3:attack=10:release=120:makeup=2',
           'loudnorm=I=-14:TP=-1.0:LRA=9', 'afade=t=out:st=9.2:d=1.2']
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', wav, '-af', ','.join(af),
                    '-ar', '44100', '-codec:a', 'libmp3lame', '-b:a', '256k', mp3], check=True)


if __name__ == '__main__':
    for i, (slug, title, fn) in enumerate(GENRES):
        tracks, opts = fn()
        apply_feel(tracks, opts, seed=i)
        write_midi(f'{OUT}/{slug}.mid', title, tracks)
        wav = f'/home/claude/{slug}.wav'
        render(wav, tracks)
        to_mp3(wav, f'{OUT}/{slug}.mp3', echo=opts.get('echo', False))
        print('done', slug)
