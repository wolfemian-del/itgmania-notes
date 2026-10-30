#!/usr/bin/env python3
"""Generate the in-game test pack for notes/itgmania_course_format_reference.txt section 16 (checks M1-M11).

Usage:
  python make_cref_test_pack.py --song1 "Pack/Song One" --song2 "Pack/Song Two" --song3 "Pack/Song Three" --out CrefTests

--songN is "<pack folder>/<song folder>" exactly as on disk (case-insensitive pack). Pick 3 different songs that
each last at least 60 s, dance-single charts that are easy for you. Song 2 should be about 120 BPM (check M3).
Copy the output folder into <your ITGmania data folder>/Courses/ , then Reload Songs/Courses (or restart).
CHECKLIST.txt in the output folder says what to do and what is predicted for each course.
Optional --diff Easy (or Medium, Hard, 1..8 ...) pins which chart is used; the default 1..20 lets the engine pick a random chart per song.
Uses only the standard library. Names containing : ; # are refused (they cannot be written in #SONG).
"""
import argparse, os, sys

def main():
    ap = argparse.ArgumentParser()
    for i in (1, 2, 3):
        ap.add_argument(f"--song{i}", required=True)
    ap.add_argument("--out", default="CrefTests")
    ap.add_argument("--diff", default="1..20",
                    help="chart selector written in every #SONG: a difficulty name (Beginner, Easy, Medium, Hard, Challenge) or a meter range like 1..8. Default 1..20 = ANY chart, picked at random per course load")
    a = ap.parse_args()
    s = [a.song1, a.song2, a.song3]
    for x in s:
        if any(c in x for c in ":;#") or "/" not in x.replace("\\", "/"):
            sys.exit(f"bad song spec {x!r}: need Pack/Song without : ; #")
    s = [x.replace("\\", "/") for x in s]
    r = a.diff
    if any(c in r for c in ":;#"):
        sys.exit(f"bad --diff {r!r}")
    # default "1..20" matches every chart; the engine then picks one AT RANDOM (Course.cpp ~633). Use --diff Easy to pin it.
    def song(i, mods=""):
        return f"#SONG:{s[i]}:{r}:{mods};"
    def head(n, d):
        d = "".join(" " if ch in ":;#" else ch for ch in d)
        return f"#COURSE:Cref {n};\n#SCRIPTER:cref test pack;\n#DESCRIPTION:{d};\n"

    c = {}
    c["M01_timed_equals"] = head("M01", "Song1: reverse from 10s to 20s (= syntax)") + \
        "#MODS:TIME=10:LEN=10:MODS=reverse;\n" + song(0) + "\n" + song(1) + "\n"
    c["M02_timed_docs_colon"] = head("M02", "Control: CourseFormat.txt colon syntax; expect NO reverse") + \
        "#MODS:TIME:10:LEN:10:MODS:reverse;\n" + song(0) + "\n" + song(1) + "\n"
    c["M03_time0_mirror"] = head("M03", "Song2: mirror with TIME=0 LEN=20; how much is mirrored?") + \
        song(0) + "\n#MODS:TIME=0:LEN=20:MODS=mirror;\n" + song(1) + "\n"
    c["M03b_time0_long_big"] = head("M03b", "Song2: big with TIME=0 LEN=9999; expect extra notes on the whole song") + \
        song(0) + "\n#MODS:TIME=0:LEN=9999:MODS=big;\n" + song(1) + "\n"
    c["M03c_time5_big"] = head("M03c", "Song2: big with TIME=5 LEN=20; expect extra notes only from 5s to 25s") + \
        song(0) + "\n#MODS:TIME=5:LEN=20:MODS=big;\n" + song(1) + "\n"
    c["M04_time_base"] = head("M04", "Song2: reverse at 15s to 25s (relative to song 2)") + \
        song(0) + "\n#MODS:TIME=15:LEN=10:MODS=reverse;\n" + song(1) + "\n"
    c["M05_missing_song_carryover"] = head("M05", "Timed reverse meant for a missing song; where does it appear?") + \
        song(0) + "\n#MODS:TIME=5:LEN=10:MODS=reverse;\n#SONG:CrefNoPack/CrefNoSong:" + r + ":;\n" + song(2) + "\n"
    c["M06_songselect_cache"] = head("M06", "Open Cache/Courses file after loading twice; see which keys survive") + \
        "#SONGSELECT:GENRE=CrefGenre:DURATION=0-300:BPMRANGE=0-300:DIFFICULTY=Medium:MODS=showcourse;\n" + song(0) + "\n"
    c["M07_invalid_mod_logging"] = head("M07", "Search log for 'foo': #MODS warns, #SONG mods does not") + \
        "#MODS:TIME=1:LEN=5:MODS=cref_bad_mods_token;\n" + song(0) + "\n" + \
        song(1, "cref_bad_song_token") + "\n"
    c["M08_stage_level_battery"] = head("M08", "Entry mod 'battery': does the life meter change type?") + \
        song(0, "battery") + "\n" + song(1) + "\n"
    c["M09_noteskin"] = head("M09", "Entry noteskin cel on song1, metal on song2: does the skin change?") + \
        song(0, "cel") + "\n" + song(1, "metal") + "\n"
    c["M10a_meter_medium"] = head("M10a", "#METER:Medium:8 (docs form); expected invalid") + \
        "#METER:Medium:8;\n" + song(0) + "\n" + song(1) + "\n"
    c["M10b_meter_regular"] = head("M10b", "#METER:Regular:8; expected to show 8") + \
        "#METER:Regular:8;\n" + song(0) + "\n" + song(1) + "\n"
    c["M11_style_double"] = head("M11", "#STYLE:double (ignored by loader); compare with doubles play") + \
        "#STYLE:DOUBLE;\n" + song(0) + "\n" + song(1) + "\n"

    os.makedirs(a.out, exist_ok=True)
    for name, body in c.items():
        with open(os.path.join(a.out, name + ".crs"), "w", encoding="utf-8", newline="\n") as f:
            f.write(body)

    check = """CREF TEST PACK - CHECKLIST (see notes/itgmania_course_format_reference.txt section 16)
Songs: 1=%s  2=%s  3=%s
Play singles, easy mode is fine. Reload songs/courses after copying. Predictions are from code reading, not runs.
Log: Logs/log.txt (and info.txt). Report PASS/FAIL (matches prediction) or what you saw.

M01 Play song 1 of M01_timed_equals. Prediction: arrows go reverse at ~10 s, back at ~20 s.
M02 Same for M02. Prediction: NOTHING changes; no log line about it. (Control: the engine doc's syntax.)
M03 M03: on song 2, mirror with TIME=0 LEN=20. Original prediction (shorter than 20 s) was wrong per the log;
    kept for reference.
M03 RESULT (user run, mirror): log says the transform was applied from beat 6 to 49 (about the full 20 s, starting ~8 beats
    in), but no mirror was visible. M03b/M03c below use "big" (adds extra notes, easy to see) to check visibility:
M03b M03b song 2: TIME=0 LEN=9999 big. Prediction: extra notes from about beat 6 (a few seconds in) to the end.
M03c M03c song 2: TIME=5 LEN=20 big. Prediction: extra notes only from about 5 s to 25 s of song 2.
M04 M04: on song 2, reverse starts 15 s into SONG 2 (not 15 s after the course began). Prediction: yes.
M05 M05: entry 2 does not exist. Prediction: reverse from 5-15 s appears on song 2 (the third #SONG, the next one that
    resolves), and the course is incomplete. Note the song order shown.
M06 Load M06 (it is fine if the entry matches nothing), exit the game cleanly, open the file in Cache/Courses/ for it
    (name contains the course file name). Prediction: the #SONGSELECT line lacks GENRE=..., DURATION= and BPMRANGE=.
    Paste the #SONGSELECT lines you find.
M07 Search the log for cref_bad_mods_token and cref_bad_song_token. Prediction: first appears (course file warning
    "Error processing"), second does not appear at load.
M08 M08 song 1 with 'battery' entry mod: Prediction: life meter stays a normal bar.
M09 M09: does song 1 use noteskin cel and song 2 metal (visible change from your usual skin)? Prediction unknown.
M10 M10a vs M10b: shown course meter. Prediction: a shows the computed meter (Medium invalid, log line about
    invalid #METER string); b shows 8.
M11 M11: does the course behave differently from a copy without #STYLE (try doubles)? Prediction: no difference
    from the loader (STYLE is never read); other mechanisms unknown.
""" % tuple(s)
    with open(os.path.join(a.out, "CHECKLIST.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(check)
    print(f"wrote {len(c)} courses + CHECKLIST.txt to {a.out}")

main()
