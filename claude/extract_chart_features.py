#!/usr/bin/env python3
"""Extract per-chart features from ITGmania song cache files into a CSV.
 
Reads Cache/Songs/* (written by ITGmania v1.3.0; format notes in
itgmania_cache_format_spec.txt). Standard library only. Read-only: it never
modifies the cache.
 
Usage:
    python extract_chart_features.py PATH_TO_CACHE OUTPUT.csv
        [--packs-file packs.txt] [--exclude-packs-file skip.txt]
    python extract_chart_features.py PATH_TO_CACHE --list-packs packs.txt
 
PATH_TO_CACHE is the ITGmania "Cache" folder or its "Songs" subfolder.
 
Choosing packs: you do NOT need to remove packs from your library. First run
with --list-packs packs.txt, which prints every pack found (with chart counts)
and writes the names to packs.txt, one per line. Delete the lines for packs you
do not want, save, and pass the file back with --packs-file. (Or use
--exclude-packs-file with a file listing only the packs to leave out.) Names
are matched without regard to upper/lower case; lines starting with # are
ignored. Duplicate detection runs after the selection, so it only compares
the packs you kept.
 
Run on a real ITGmania v1.3.0 cache by the user (2026-10-10): 5,557 files read,
0 failures. Written from the engine source; see itgmania_cache_format_spec.txt.
"""
import argparse
import csv
import re
import sys
from pathlib import Path
 
RADAR_NAMES = [
    "Stream", "Voltage", "Air", "Freeze", "Chaos", "Notes", "TapsAndHolds",
    "Jumps", "Holds", "Mines", "Hands", "Rolls", "Lifts", "Fakes",
]
TECH_NAMES = [
    "Crossovers", "HalfCrossovers", "FullCrossovers", "Footswitches",
    "UpFootswitches", "DownFootswitches", "Sideswitches", "Jacks",
    "Brackets", "Doublesteps",
]
NUM_PLAYERS = 2
WINDOWS = (8, 16, 32)  # measures, for sustained-NPS features
 
 
def parse_tags(text):
    """Return a list of (name, value) in file order.
 
    Comment lines ("//...") are dropped first. A tag is '#NAME:value;'; a ';'
    preceded by a backslash does not end the value. Backslash escapes are
    removed from the returned value.
    """
    lines = [ln for ln in text.splitlines() if not ln.lstrip().startswith("//")]
    text = "\n".join(lines)
    tags = []
    i, n = 0, len(text)
    while i < n:
        if text[i] != "#":
            i += 1
            continue
        j = i + 1
        buf = []
        while j < n:
            c = text[j]
            if c == "\\" and j + 1 < n:
                buf.append(text[j + 1])
                j += 2
                continue
            if c == ";":
                break
            buf.append(c)
            j += 1
        raw = "".join(buf)
        name, sep, value = raw.partition(":")
        if sep:
            tags.append((name.strip().upper(), value))
        i = j + 1
    return tags
 
 
def floats(s):
    out = []
    for p in s.split(","):
        p = p.strip()
        if p == "":
            continue
        try:
            out.append(float(p))
        except ValueError:
            out.append(float("nan"))
    return out
 
 
def per_player_first(values, count):
    """Cache lists hold every player's values back to back; the loader splits
    them evenly. Return player 1's slice (None if the length is unusable)."""
    if not values:
        return None
    per = len(values) // NUM_PLAYERS
    if per < count:
        return None
    return values[:count]
 
 
def first_section(s):
    """NPS-style tags separate players with '|'; take the first."""
    return s.split("|")[0] if s else ""
 
 
def sustained(nps, w):
    """Max mean NPS over any window of w consecutive measures (0 if shorter)."""
    if len(nps) < w:
        return 0.0
    cur = sum(nps[:w])
    best = cur
    for k in range(w, len(nps)):
        cur += nps[k] - nps[k - w]
        best = max(best, cur)
    return best / w
 
 
def measure_features(nps, notes):
    nz = [x for x in nps if x > 0]
    f = {
        "measure_count": len(nps),
        "active_measures": len(nz),
        "total_rows": sum(notes) if notes else 0,
        "peak_nps_calc": max(nps) if nps else 0.0,
        "mean_nps_active": (sum(nz) / len(nz)) if nz else 0.0,
    }
    srt = sorted(nz)
    f["p90_nps_active"] = srt[int(0.9 * (len(srt) - 1))] if srt else 0.0
    for w in WINDOWS:
        f["sust_nps_%d" % w] = sustained(nps, w)
    return f
 
 
def split_charts(tags):
    """Split the tag list into (song_tags, [chart_tags, ...])."""
    song, charts, cur = [], [], None
    for name, value in tags:
        if name == "NOTEDATA":
            cur = []
            charts.append(cur)
        elif cur is None:
            song.append((name, value))
        else:
            cur.append((name, value))
    return song, charts
 
 
def tag_dict(tags):
    d = {}
    for name, value in tags:
        d[name] = value  # last one wins, as in the engine's INI reader
    return d
 
 
def pack_from_songfile(path):
    parts = [p for p in re.split(r"[\\/]+", path) if p]
    return parts[1] if len(parts) >= 3 else ""
 
 
def process_file(path):
    text = path.read_text(encoding="utf-8", errors="replace")
    song_tags, chart_tag_lists = split_charts(parse_tags(text))
    sd = tag_dict(song_tags)
    songfile = sd.get("SONGFILENAME", "")
    rows, problems = [], []
    for ct in chart_tag_lists:
        cd = tag_dict(ct)
        row = {
            "pack": pack_from_songfile(songfile),
            "song_file": songfile,
            "cache_file": path.name,
            "title": sd.get("TITLE", ""),
            "artist": sd.get("ARTIST", ""),
            "music_length": sd.get("MUSICLENGTH", ""),
            "steps_type": cd.get("STEPSTYPE", ""),
            "difficulty": cd.get("DIFFICULTY", ""),
            "meter": cd.get("METER", ""),
            "description": cd.get("DESCRIPTION", ""),
            "chart_name": cd.get("CHARTNAME", ""),
            "credit": cd.get("CREDIT", ""),
        }
        missing = [t for t in ("RADARVALUES", "TECHCOUNTS", "NPSPERMEASURE",
                               "NOTESPERMEASURE", "PEAKNPS", "METER")
                   if t not in cd]
        radar = per_player_first(floats(cd.get("RADARVALUES", "")), len(RADAR_NAMES))
        tech = per_player_first(floats(cd.get("TECHCOUNTS", "")), len(TECH_NAMES))
        for i, nm in enumerate(RADAR_NAMES):
            row["radar_" + nm] = radar[i] if radar else ""
        for i, nm in enumerate(TECH_NAMES):
            row["tech_" + nm] = tech[i] if tech else ""
        nps = floats(first_section(cd.get("NPSPERMEASURE", "")))
        notes = [int(x) for x in floats(first_section(cd.get("NOTESPERMEASURE", "")))
                 if x == x]
        pk = floats(first_section(cd.get("PEAKNPS", "")))
        row["peak_nps"] = pk[0] if pk else ""
        row.update(measure_features(nps, notes))
        # per-100-rows tech rates (rows = counted note rows; jumps count once)
        total = row["total_rows"]
        for nm in TECH_NAMES:
            v = row["tech_" + nm]
            row["tech_per100_" + nm] = (v / total * 100.0) if (total and v != "") else ""
        # GrooveStats hash: identifies identical note data + BPM changes.
        # hash_status is separate from "flags" on purpose: a missing hash must
        # not get a chart dropped from fitting.
        h = cd.get("GROOVESTATSHASH", "").strip()
        row["groovestats_hash"] = h
        row["groovestats_hash_version"] = cd.get("GROOVESTATSHASHVERSION", "").strip()
        if not h:
            row["hash_status"] = "missing"
        elif not re.fullmatch(r"[0-9a-fA-F]{16}", h):
            row["hash_status"] = "malformed"
        elif not row["total_rows"]:
            row["hash_status"] = "empty_chart"  # hash would only cover BPMs
        elif not row["groovestats_hash_version"]:
            row["hash_status"] = "no_version"
        else:
            row["hash_status"] = "ok"
        flags = []
        if missing:
            flags.append("missing:" + "+".join(missing))
        if radar is None:
            flags.append("radar_unusable")
        elif any(x == -1 for x in radar):
            flags.append("radar_unknown")
        if tech is None:
            flags.append("tech_unusable")
        elif any(x == -1 for x in tech):
            flags.append("tech_unknown")
        row["flags"] = ";".join(flags)
        if flags:
            problems.append((path.name, row["difficulty"], row["flags"]))
        rows.append(row)
    return rows, problems
 
 
def assign_duplicates(rows):
    """Group charts that share a GrooveStats hash (same notes and BPM changes).
 
    Adds dup_group (id, blank if unique), dup_group_size, dup_packs (distinct
    packs in the group), dup_meter_conflict (1 if members carry different
    meters) and dup_feature_mismatch (1 if members differ in peak NPS, notes
    or tech counts, which the hash can miss: it ignores stops, warps, delays
    and the song offset). Only hash_status == "ok" rows are grouped, within the
    same steps type and hash version. Returns a summary dict.
    """
    feat_cols = ["peak_nps", "radar_Notes"] + ["tech_" + t for t in TECH_NAMES]
    groups = {}
    for r in rows:
        r["dup_group"] = ""
        r["dup_group_size"] = 1
        r["dup_packs"] = 1
        r["dup_meter_conflict"] = 0
        r["dup_feature_mismatch"] = 0
        if r["hash_status"] != "ok":
            continue
        key = (r["steps_type"], r["groovestats_hash"].lower(),
               r["groovestats_hash_version"])
        groups.setdefault(key, []).append(r)
    summ = {"groups": 0, "charts": 0, "cross_pack": 0,
            "meter_conflicts": [], "feature_mismatches": []}
    gid = 0
    for members in groups.values():
        if len(members) < 2:
            continue
        gid += 1
        packs = sorted({m["pack"] for m in members})
        meters = sorted({str(m["meter"]) for m in members})
        feats = {tuple(str(m[c]) for c in feat_cols) for m in members}
        for m in members:
            m["dup_group"] = gid
            m["dup_group_size"] = len(members)
            m["dup_packs"] = len(packs)
            m["dup_meter_conflict"] = 1 if len(meters) > 1 else 0
            m["dup_feature_mismatch"] = 1 if len(feats) > 1 else 0
        summ["groups"] += 1
        summ["charts"] += len(members)
        if len(packs) > 1:
            summ["cross_pack"] += 1
        label = "%s (%s)" % (members[0]["title"], members[0]["difficulty"])
        if len(meters) > 1:
            summ["meter_conflicts"].append((label, meters, packs))
        if len(feats) > 1:
            summ["feature_mismatches"].append((label, packs))
    return summ
 
 
def read_pack_list(path):
    """One pack name per line; blank lines and lines starting with # ignored.
    utf-8-sig so a Notepad byte-order mark does not stick to the first name."""
    names = []
    for line in Path(path).read_text(encoding="utf-8-sig").splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            names.append(s)
    return names
 
 
def select_packs(rows, include_file, exclude_file):
    present = {r["pack"].lower() for r in rows}
    if include_file:
        inc = read_pack_list(include_file)
        if not inc:
            sys.exit("%s lists no packs." % include_file)
        want = {p.lower() for p in inc}
        missing = [p for p in inc if p.lower() not in present]
        before = len(rows)
        rows = [r for r in rows if r["pack"].lower() in want]
        print("Pack selection (include list): kept %d of %d charts"
              % (len(rows), before))
        if missing:
            print("  WARNING: not found in the cache (check spelling): %s"
                  % "; ".join(missing))
    if exclude_file:
        exc = {p.lower() for p in read_pack_list(exclude_file)}
        before = len(rows)
        rows = [r for r in rows if r["pack"].lower() not in exc]
        print("Pack selection (exclude list): kept %d of %d charts"
              % (len(rows), before))
        missing = sorted(exc - present)
        if missing:
            print("  WARNING: excluded names not found in the cache: %s"
                  % "; ".join(missing))
    return rows
 
 
def find_song_cache(arg):
    p = Path(arg)
    if (p / "Songs").is_dir():
        p = p / "Songs"
    if not p.is_dir():
        sys.exit("Not a folder: %s" % arg)
    return p
 
 
def main():
    ap = argparse.ArgumentParser(
        description="Extract per-chart features from ITGmania cache files.")
    ap.add_argument("cache", help='the ITGmania "Cache" folder')
    ap.add_argument("out", nargs="?",
                    help="output CSV (not needed with --list-packs)")
    ap.add_argument("--list-packs", metavar="FILE",
                    help="print the packs found, write their names to FILE, "
                         "and stop")
    ap.add_argument("--packs-file", metavar="FILE",
                    help="only use the packs named in FILE")
    ap.add_argument("--exclude-packs-file", metavar="FILE",
                    help="leave out the packs named in FILE")
    a = ap.parse_args()
    if not a.list_packs and not a.out:
        ap.error("an output CSV is required unless --list-packs is used")
    cache_dir = find_song_cache(a.cache)
    out_path = Path(a.out) if a.out else None
    all_rows, all_problems, nfiles, nfail, nempty = [], [], 0, 0, 0
    for f in sorted(cache_dir.iterdir()):
        if not f.is_file():
            continue
        nfiles += 1
        try:
            rows, problems = process_file(f)
        except Exception as e:  # keep going; report at the end
            nfail += 1
            print("FAILED %s: %s" % (f.name, e), file=sys.stderr)
            continue
        if not rows:
            nempty += 1
            print("NO CHARTS in %s" % f.name, file=sys.stderr)
        all_rows.extend(rows)
        all_problems.extend(problems)
    if not all_rows:
        sys.exit("No charts found in %s" % cache_dir)
    if a.list_packs:
        counts = {}
        for r in all_rows:
            c = counts.setdefault(r["pack"], [0, set()])
            c[0] += 1
            c[1].add(r["song_file"])
        names = sorted(counts, key=lambda s: s.lower())
        print("%-48s %7s %6s" % ("pack", "charts", "songs"))
        for n in names:
            print("%-48s %7d %6d" % ((n or "(unknown pack)")[:48],
                                     counts[n][0], len(counts[n][1])))
        Path(a.list_packs).write_text(
            "\n".join(n for n in names if n) + "\n", encoding="utf-8")
        print("\n%d packs. Names written to %s: delete the lines for packs you "
              "do not want, then use --packs-file %s"
              % (len([n for n in names if n]), a.list_packs, a.list_packs))
        if "" in counts:
            print("NOTE: %d charts have no pack name (no #SONGFILENAME); they "
                  "are dropped when --packs-file is used." % counts[""][0])
        return
    if a.packs_file or a.exclude_packs_file:
        all_rows = select_packs(all_rows, a.packs_file, a.exclude_packs_file)
        if not all_rows:
            sys.exit("No charts left after pack selection.")
        all_problems = [(r["cache_file"], r["difficulty"], r["flags"])
                        for r in all_rows if r["flags"]]
    dup = assign_duplicates(all_rows)
    cols = []
    for r in all_rows:
        for k in r:
            if k not in cols:
                cols.append(k)
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(all_rows)
    print("Files read: %d (failed: %d, no charts: %d)" % (nfiles, nfail, nempty))
    print("Charts written: %d -> %s" % (len(all_rows), out_path))
    print("Charts with flags: %d" % len(all_problems))
    for name, diff, flag in all_problems[:20]:
        print("  %s [%s]: %s" % (name, diff, flag))
    if len(all_problems) > 20:
        print("  ... %d more (see the flags column)" % (len(all_problems) - 20))
    status = {}
    for r in all_rows:
        status[r["hash_status"]] = status.get(r["hash_status"], 0) + 1
    print("Hash status: " + ", ".join("%s=%d" % kv for kv in sorted(status.items())))
    print("Duplicate groups (same notes + BPMs): %d, covering %d charts; "
          "%d span more than one pack" % (dup["groups"], dup["charts"],
                                          dup["cross_pack"]))
    print("  groups with conflicting meters: %d" % len(dup["meter_conflicts"]))
    for label, meters, packs in dup["meter_conflicts"][:10]:
        print("    %s: meters %s in packs %s" % (label, "/".join(meters),
                                                 ", ".join(packs)[:80]))
    print("  groups with differing features (hash misses stops/warps/offset): %d"
          % len(dup["feature_mismatches"]))
    for label, packs in dup["feature_mismatches"][:10]:
        print("    %s in packs %s" % (label, ", ".join(packs)[:80]))
 
 
if __name__ == "__main__":
    main()