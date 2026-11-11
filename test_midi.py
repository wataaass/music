"""out/song.mid の検査。 python3 test_midi.py"""
import mido, make_midi as mm

mid = mido.MidiFile("out/song.mid")
SCALE = {6, 8, 9, 11, 1, 2, 4}  # F#マイナー
tempo = [m.tempo for m in mid.tracks[0] if m.type == "set_tempo"]
assert len(tempo) == 1 and abs(mido.tempo2bpm(tempo[0]) - 110.5) < 0.01, tempo
assert abs(mid.length - 56 * 4 * 60 / 110.5) < 0.05, mid.length
names = [t.name for t in mid.tracks]
assert names == ["Tempo", "Bass", "Chords", "Lead", "Drums"], names
for tr in mid.tracks[1:]:
    now, on, count = 0, {}, 0
    for m in tr:
        now += m.time
        assert m.time >= 0
        if m.type == "note_on" and m.velocity > 0:
            assert m.note not in on, f"{tr.name}: 同じ音が重なっている tick={now} note={m.note}"
            on[m.note] = now; count += 1
            if tr.name != "Drums":
                assert m.note % 12 in SCALE, f"{tr.name}: スケール外 {m.note}"
            if tr.name == "Bass":
                assert 28 <= m.note <= 47, m.note
                assert len(on) == 1, f"Bass が重なっている tick={now}"
        elif m.type in ("note_off", "note_on"):
            assert now - on.pop(m.note) >= 10, f"{tr.name}: 短すぎる音 tick={now}"
    assert not on and count > 0 and now == 56 * mm.BAR, (tr.name, on, now)
    print(f"{tr.name:7s} {count} ノート")
# 切り刻み区間に無音スロットと32分の反復がある
a, b = mm.CHOP[0] * mm.BAR, mm.CHOP[1] * mm.BAR
slots = set()
for _, st, en, _, _ in mm.notes:
    if st < b and en > a:
        slots.update(range((max(st, a) - a) // mm.S32, (min(en, b) - a - 1) // mm.S32 + 1))
n = (b - a) // mm.S32
assert 0 < n - len(slots) < n // 2, (n, len(slots))
print(f"切り刻み区間: {n} スロット中 {n - len(slots)} が無音\nOK")
