# grenre-grooves

Nine four-bar grooves over Am | C | Em | G at 120 BPM. `genre_grooves_Am-C-Em-G.zip` is the original
archive, unpacked in `genre_grooves_Am-C-Em-G/` (MIDI, MP3 and the generator).

## Demo bits

`demo/<song>/<track>/01.mp3` … `64.mp3` holds each song's four tracks (`drums`, `bass`,
`accompaniment`, `melody`), each cut into its 64 sixteenth notes of 125 ms.

- The 64 bits of a track, played in series, are the complete track.
- The four tracks, played in parallel, are the complete song.

Bits where a track is silent are exported too, so every track has all 64. The bits come straight
from the MIDI files, at 48 kHz because a sixteenth is then exactly 6000 samples. They have one gain
per song and no compression, so the tracks still add up to the song. The original MP3s' mastering
and the dub echo on `05_rockers_riddim_dub` are not in the MIDI files, so the bits don't have them,
and the reverb tail after the fourth bar is cut off.

For gapless playback, use a player that honours the MP3's LAME delay and padding (ffmpeg and
browsers' `decodeAudioData` do), and schedule each bit on the 125 ms grid.

Regenerate them with ffmpeg, libfluidsynth and `pip install mido numpy pyfluidsynth`:

```sh
python3 tools/make_demo_bits.py
```
