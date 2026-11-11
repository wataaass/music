"""110.5 BPM / F#マイナーの曲を MIDI に書き出す。

    python3 make_midi.py        ->  out/song.mid

音色の作り方は SETTINGS.md を参照。
"""
import os
import random

import mido

BPM = 110.5
PPQ = 480
S16 = PPQ // 4          # 16分音符
S32 = PPQ // 8          # 32分音符
BAR = PPQ * 4
BARS = 56

# セクション（小節は0始まり、end は含まない）
INTRO = (0, 2)
MAIN = (2, 18)
TRANS = (18, 20)
CHOP = (20, 28)
RETURN = (28, 36)
BREAK = (36, 40)
FINAL = (40, 56)

BASS, CHORD, LEAD, DRUM = "Bass", "Chords", "Lead", "Drums"
CHANNEL = {BASS: 0, CHORD: 1, LEAD: 2, DRUM: 9}

# コード: (ベースの根音, ボイシング)
CH = {
    "F#m9": (30, [54, 57, 61, 64, 68]),
    "Dmaj9": (38, [50, 54, 57, 61, 64]),
    "Aadd9": (33, [52, 57, 61, 64, 71]),
    "Eadd9": (40, [52, 56, 59, 64, 66]),
    "Bm9": (35, [59, 62, 66, 69, 73]),
    "C#m7": (37, [56, 61, 64, 68, 71]),
    "F#m": (30, [54, 57, 61, 66, 69]),
}
PROG_MAIN = ["F#m9", "Dmaj9", "Aadd9", "Eadd9"]
PROG_BREAK = ["Bm9", "C#m7", "Dmaj9", "Eadd9"]
PROG_END = ["Dmaj9", "Eadd9", "C#m7", "F#m"]

# メロディ: コードごとの (開始16分, 長さ16分, ノート)
MEL = {
    "F#m9": [(0, 3, 73), (3, 3, 76), (6, 2, 78), (8, 2, 76), (10, 2, 73), (12, 4, 69)],
    "Dmaj9": [(0, 3, 69), (3, 3, 73), (6, 2, 74), (8, 4, 78), (12, 2, 76), (14, 2, 73)],
    "Aadd9": [(0, 3, 76), (3, 3, 73), (6, 2, 69), (8, 2, 71), (10, 2, 73), (12, 4, 76)],
    "Eadd9": [(0, 3, 71), (3, 3, 76), (6, 4, 80), (10, 2, 78), (12, 2, 76), (14, 2, 68)],
    "Bm9": [(0, 6, 74), (6, 2, 73), (8, 8, 78)],
    "C#m7": [(0, 6, 76), (6, 2, 73), (8, 8, 80)],
    "C#m7end": [(0, 3, 80), (3, 3, 76), (6, 2, 73), (8, 4, 71), (12, 4, 68)],
    "F#m": [(0, 3, 73), (3, 3, 76), (6, 10, 78)],
}
MEL_B = {  # 2周目の変化形
    "F#m9": [(0, 2, 78), (2, 2, 76), (4, 2, 73), (6, 2, 76), (8, 3, 78), (11, 3, 81), (14, 2, 80)],
    "Dmaj9": [(0, 3, 78), (3, 3, 76), (6, 2, 74), (8, 2, 73), (10, 2, 69), (12, 4, 73)],
    "Aadd9": [(0, 2, 76), (2, 2, 73), (4, 2, 76), (6, 2, 81), (8, 4, 80), (12, 4, 76)],
    "Eadd9": [(0, 3, 80), (3, 3, 78), (6, 2, 76), (8, 2, 71), (10, 2, 76), (12, 4, 80)],
}

# ベースの打点（16分の位置）
BASS_A = [0, 2, 4, 6, 7, 8, 10, 12, 14, 15]
BASS_B = [0, 2, 3, 4, 6, 8, 10, 11, 12, 13, 14, 15]
BASS_FULL = list(range(16))

notes = []   # (track, start, end, pitch, velocity)
ccs = []     # (track, tick, controller, value)


def add(track, start, length, pitch, vel):
    notes.append((track, int(start), int(start + length), pitch, vel))


def bass_bar(bar, chord, hits, fill32=False):
    root = CH[chord][0]
    t0 = bar * BAR
    for i, st in enumerate(hits):
        nxt = hits[i + 1] if i + 1 < len(hits) else 16
        pitch = root
        if st in (7, 15):
            pitch = root + 7 if root + 7 <= 42 else root - 5
        if fill32 and st >= 12:
            for k in range(2):  # 最後の1拍は32分連打
                add(BASS, t0 + st * S16 + k * S32, S32 * 0.85, pitch, 112 if k == 0 else 96)
            continue
        add(BASS, t0 + st * S16, (nxt - st) * S16 * 0.9, pitch, 118 if st % 4 == 0 else 104)


def chord_bar(bar, chord, stab=False):
    t0 = bar * BAR
    voicing = CH[chord][1]
    if not stab:
        for p in voicing:
            add(CHORD, t0, BAR - S32, p, 92)
        return
    for st, ln in [(0, 3), (3, 3), (6, 2), (8, 3), (11, 3), (14, 2)]:
        for p in voicing:
            add(CHORD, t0 + st * S16, ln * S16 * 0.85, p, 100 if st in (0, 8) else 88)


def lead_bar(bar, key, table=MEL):
    t0 = bar * BAR
    for st, ln, p in table[key]:
        add(LEAD, t0 + st * S16, ln * S16 * 0.92, p, 104)


def drum_bar(bar, roll=False, kick=(0, 7, 10), snare=(4, 12)):
    t0 = bar * BAR
    for st in kick:
        add(DRUM, t0 + st * S16, S16 // 2, 36, 118)
    for st in snare:
        add(DRUM, t0 + st * S16, S16 // 2, 38, 110)
        add(DRUM, t0 + st * S16, S16 // 2, 39, 96)
    for st in range(16):
        if roll and st >= 12:
            for k in range(2):
                add(DRUM, t0 + st * S16 + k * S32, S32 // 2, 42, 70 + 6 * (st - 12) + 4 * k)
        else:
            add(DRUM, t0 + st * S16, S16 // 2, 42, 96 if st % 4 == 0 else (80 if st % 2 == 0 else 62))
    add(DRUM, t0 + 14 * S16, S16, 46, 78)


def band_section(start, end, prog, bass_hits, lead_table, stab=False, fill_every=4):
    for bar in range(start, end):
        i = bar - start
        chord = prog[i % len(prog)]
        last = (i % fill_every) == fill_every - 1
        bass_bar(bar, chord, bass_hits, fill32=last)
        chord_bar(bar, chord, stab=stab)
        lead_bar(bar, chord, lead_table)
        drum_bar(bar, roll=last)


# --- イントロ: 下降フレーズと低音 ---
for p in CH["F#m9"][1]:
    add(CHORD, 0, BAR * 2 - S16, p, 70)
for i, p in enumerate([85, 83, 81, 80, 78, 76, 74, 73, 71, 69, 68, 66, 64, 62, 61, 57]):
    add(LEAD, i * S16, S16 * 0.9, p, 100 - 2 * i)
add(BASS, BAR, PPQ * 2 * 0.95, 37, 110)
for st in range(8, 16):
    add(BASS, BAR + st * S16, S16 * 0.9, 37 if st < 12 else 30, 90 + 3 * (st - 8))
    for k in range(2 if st >= 12 else 1):
        add(DRUM, BAR + st * S16 + k * S32, S32 // 2, 38, 60 + 6 * (st - 8))

# --- 本編 ---
band_section(MAIN[0], MAIN[0] + 8, PROG_MAIN, BASS_A, MEL)
band_section(MAIN[0] + 8, MAIN[1], PROG_MAIN, BASS_A, MEL_B)

# --- つなぎ: 帯域フィルター + 1オクターブ下のベース ---
for bar in range(*TRANS):
    for p in CH["Eadd9"][1]:
        add(CHORD, bar * BAR, BAR - S32, p, 84)
    add(BASS, bar * BAR, BAR * 0.97, 28, 110)
t0, span = TRANS[0] * BAR, (TRANS[1] - TRANS[0]) * BAR
for i in range(33):  # CC74: 閉じてから開く
    x = i / 32
    val = int(110 - 85 * (1 - abs(2 * x - 1) ** 2))
    ccs.append((CHORD, t0 + int(span * x), 74, val))
ccs.append((CHORD, t0 + span, 74, 127))
for st in range(8, 16):
    for k in range(2 if st >= 12 else 1):
        add(DRUM, (TRANS[1] - 1) * BAR + st * S16 + k * S32, S32 // 2, 38, 64 + 6 * (st - 8))

# --- 切り刻み区間の素材（あとで並べ替える） ---
band_section(CHOP[0], CHOP[1], PROG_MAIN, BASS_B, MEL, stab=True)

# --- 復帰 ---
band_section(RETURN[0], RETURN[1], PROG_MAIN, BASS_B, MEL_B)

# --- ブレイク: ベースを伸ばす ---
for bar in range(*BREAK):
    chord = PROG_BREAK[bar - BREAK[0]]
    add(BASS, bar * BAR, BAR * 0.98, CH[chord][0], 112)
    chord_bar(bar, chord)
    lead_bar(bar, chord)
for st in range(8, 16):
    for k in range(2):
        add(DRUM, (BREAK[1] - 1) * BAR + st * S16 + k * S32, S32 // 2, 38, 58 + 7 * (st - 8))

# --- 終盤: 16分で埋める ---
band_section(FINAL[0], FINAL[0] + 8, PROG_MAIN, BASS_FULL, MEL_B, stab=True, fill_every=2)
band_section(FINAL[0] + 8, FINAL[0] + 12, PROG_MAIN, BASS_FULL, MEL, stab=True, fill_every=2)
for i, chord in enumerate(PROG_END):
    bar = FINAL[0] + 12 + i
    last = i == 3
    bass_bar(bar, chord, BASS_FULL if not last else [0], fill32=not last)
    chord_bar(bar, chord, stab=not last)
    lead_bar(bar, "C#m7end" if chord == "C#m7" else chord)
    if not last:
        drum_bar(bar, roll=True)
    else:
        add(DRUM, bar * BAR, S16, 36, 120)
        add(DRUM, bar * BAR, PPQ * 2, 49, 110)


# --- 切り刻み: 32分単位で全トラックを同じ並べ替えにかける ---
def chop(all_notes, start_bar, end_bar, seed=7):
    rng = random.Random(seed)
    a, b = start_bar * BAR, end_bar * BAR
    n = (b - a) // S32
    src = []  # 各スロットが参照する元スロット（None は無音）
    while len(src) < n:
        r = rng.random()
        j = len(src)
        if r < 0.50:
            src += list(range(j, j + rng.choice([2, 4, 4, 6, 8])))
        elif r < 0.85:
            size = rng.choice([1, 1, 2])
            src += list(range(j, j + size)) * rng.choice([2, 3, 4])
        else:
            src += [None] * rng.choice([1, 2])
    src = src[:n]
    src[0] = 0  # 区間の頭は必ず鳴らす

    keep = [x for x in all_notes if x[2] <= a or x[1] >= b]
    inside = [x for x in all_notes if not (x[2] <= a or x[1] >= b)]
    pieces = {}  # (track, pitch) -> [[start, end, vel]]
    for j, s in enumerate(src):
        if s is None:
            continue
        s0, s1 = a + s * S32, a + (s + 1) * S32
        shift = (j - s) * S32
        contiguous = j > 0 and src[j - 1] is not None and src[j - 1] == s - 1
        for tr, st, en, p, v in inside:
            lo, hi = max(st, s0), min(en, s1)
            if hi - lo < 10:
                continue
            lst = pieces.setdefault((tr, p), [])
            if contiguous and st < s0 and lst and lst[-1][1] == lo + shift:
                lst[-1][1] = hi + shift  # 元の音が続いているのでつなぐ
            else:
                lst.append([lo + shift, hi + shift, v])
    for (tr, p), lst in pieces.items():
        for st, en, v in lst:
            if en - st >= S32:  # 切れ目を作るため少し短くする
                en -= 8
            keep.append((tr, st, en, p, v))
    return keep


notes = chop(notes, *CHOP)


def write(path):
    mid = mido.MidiFile(type=1, ticks_per_beat=PPQ)
    meta = mido.MidiTrack()
    meta.append(mido.MetaMessage("track_name", name="Tempo", time=0))
    meta.append(mido.MetaMessage("set_tempo", tempo=round(60_000_000 / BPM), time=0))
    meta.append(mido.MetaMessage("time_signature", numerator=4, denominator=4, time=0))
    meta.append(mido.MetaMessage("key_signature", key="F#m", time=0))
    meta.append(mido.MetaMessage("end_of_track", time=BARS * BAR))
    mid.tracks.append(meta)
    for name in (BASS, CHORD, LEAD, DRUM):
        ch = CHANNEL[name]
        ev = []
        for tr, st, en, p, v in notes:
            if tr == name:
                ev.append((st, 1, mido.Message("note_on", channel=ch, note=p, velocity=v)))
                ev.append((en, 0, mido.Message("note_off", channel=ch, note=p, velocity=0)))
        for tr, tick, cc, val in ccs:
            if tr == name:
                ev.append((tick, 2, mido.Message("control_change", channel=ch, control=cc, value=val)))
        ev.sort(key=lambda e: (e[0], e[1]))
        track = mido.MidiTrack()
        track.append(mido.MetaMessage("track_name", name=name, time=0))
        now = 0
        for tick, _, msg in ev:
            track.append(msg.copy(time=tick - now))
            now = tick
        track.append(mido.MetaMessage("end_of_track", time=max(0, BARS * BAR - now)))
        mid.tracks.append(track)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    mid.save(path)
    return mid


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "song.mid")
    m = write(out)
    print(f"{out}: {m.length:.1f} 秒, {len(notes)} ノート")
