#!/usr/bin/env python3
"""Build an ITGmania course (.crs) from charts picked by MODELED difficulty.

Reads the ITGmania song cache (Cache/Songs/*), rates every dance-single
non-Edit chart with the deployed difficulty model (difficulty_model_notech.json,
the same formula DifficultyModel.lua uses in-game), and writes a .crs with fixed
#SONG entries for charts at the rating(s) you ask for.

Standard library only. Read-only on the cache. Needs extract_chart_features.py
in the same folder (it supplies the cache parser, so parsing is identical to
the extractor the model was fitted with).

Examples
    # 10 random charts, all modeled 11
    python make_course_by_rating.py CACHE --rating 11 --count 10 \
        --model difficulty_model_notech.json --out "Courses/Modeled/Eleven.crs"

    # a ladder: one chart at each listed rating, in that order
    python make_course_by_rating.py CACHE --ratings 9,10,11,12,13 --out Ladder.crs

    # any chart rated 10..12, 8 entries, sorted easiest to hardest
    python make_course_by_rating.py CACHE --range 10-12 --count 8 --sort asc ...

    # see what you have: charts per modeled rating (no course written)
    python make_course_by_rating.py CACHE --histogram

Useful options: --seed N (repeatable pick), --include-packs-file /
--exclude-packs-file (one pack name per line, as in the extractor),
--root FOLDER[;FOLDER...] (folder(s) containing Songs/; drops cache entries
whose song folder is not found in any of them),
--min-seconds/--max-seconds (song length filter), --lives N, --no-pin.

Rating rule (must match DifficultyModel.lua / apply_model.py):
    raw = intercept + sum(coef * feature); cal = interp(raw, knots) (flat
    outside); rating = clamp(floor(cal + 0.5), 1, 19)   (half-up rounding).
"""
import argparse
import bisect
import json
import math
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import extract_chart_features as ecf
except ImportError:
    sys.exit("extract_chart_features.py must be in the same folder as this "
             "script.")

SLOTS = ("Beginner", "Easy", "Medium", "Hard", "Challenge")
BAD_CHARS = re.compile(r"[:;#]")  # cannot be escaped in #SONG (see notes)


# ------------------------------------------------------------------ model ---

def load_model(path):
    m = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if m.get("steps_type", "dance-single") != "dance-single":
        sys.exit("model is for %s, not dance-single" % m.get("steps_type"))
    if m.get("tech_features"):
        sys.exit("this script supports the no-tech model only "
                 "(difficulty_model_notech.json)")
    cal = m.get("calibration_knots")
    if cal:
        if len(cal["x"]) != len(cal["y"]) or len(cal["x"]) < 2:
            sys.exit("bad calibration knots in model file")
    return m


def derived_features(r):
    """Features the model needs that are not already columns in the row.
    Same definitions as fit_difficulty_model.build_features."""
    rows = max(r["total_rows"], 1)
    f = {
        "log_rows": math.log(rows),
        "active_frac": r["active_measures"] / max(r["measure_count"], 1),
        "hands_per_row": r["radar_Hands"] / rows,
        "mines_per_row": r["radar_Mines"] / rows,
        "holds_per_row": (r["radar_Holds"] + r["radar_Rolls"]) / rows,
        "jumps_per_row": r["radar_Jumps"] / rows,
    }
    return f


def interp(x, xs, ys):
    """numpy.interp semantics: linear between knots, flat outside."""
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    i = bisect.bisect_right(xs, x)
    x0, x1, y0, y1 = xs[i - 1], xs[i], ys[i - 1], ys[i]
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0)


def model_value(row, model):
    """Return (raw, calibrated, rating) for a feature row, or None."""
    d = derived_features(row)
    raw = model["intercept"]
    for name, coef in model["coefficients"].items():
        if name in d:
            v = d[name]
        elif name in row:
            v = row[name]
        else:
            sys.exit("model feature %s is not available" % name)
        if v == "" or v != v:
            return None
        raw += coef * float(v)
    cal = model.get("calibration_knots")
    val = interp(raw, cal["x"], cal["y"]) if cal else raw
    rating = int(min(max(math.floor(val + 0.5), 1), 19))
    return raw, val, rating


# ---------------------------------------------------------------- library ---

def song_dir_from_songfile(songfile):
    parts = [p for p in re.split(r"[\\/]+", songfile) if p]
    # Songs/<pack>/<song>/<file>
    if len(parts) >= 4:
        return parts[1], parts[2], "/".join(parts[:3])
    return None


def scan_library(cache_dir, model, progress=None, should_stop=None):
    """Parse the whole cache once and rate every eligible chart.

    Applies only the filters that do not depend on user choices (steps type,
    Edit, unusable data, odd song paths, ':;#' in names). Returns
    (rows, stats). `progress(done, total)` is called now and then;
    `should_stop()` returning True abandons the scan (returns None)."""
    stats = {"files": 0, "charts": 0, "not_single": 0, "edit": 0,
             "flagged": 0, "no_song_dir": 0, "bad_name": 0}
    files = [f for f in sorted(cache_dir.iterdir()) if f.is_file()]
    out = []
    for n, f in enumerate(files):
        if should_stop and should_stop():
            return None
        if progress and n % 100 == 0:
            progress(n, len(files))
        stats["files"] += 1
        try:
            rows, _ = ecf.process_file(f)
        except Exception as e:
            print("FAILED %s: %s" % (f.name, e), file=sys.stderr)
            continue
        for r in rows:
            stats["charts"] += 1
            if r["steps_type"] != "dance-single":
                stats["not_single"] += 1
                continue
            if r["difficulty"] not in SLOTS:
                stats["edit"] += 1  # Edit slot (and anything unknown)
                continue
            if r["flags"]:
                stats["flagged"] += 1
                continue
            sd = song_dir_from_songfile(r["song_file"])
            if sd is None:
                stats["no_song_dir"] += 1
                continue
            pack, sdir, rel = sd
            if BAD_CHARS.search(pack) or BAD_CHARS.search(sdir):
                stats["bad_name"] += 1
                continue
            mv = model_value(r, model)
            if mv is None:
                stats["flagged"] += 1
                continue
            try:
                ml = float(r["music_length"])
            except (TypeError, ValueError):
                ml = None
            hk = None
            if r["hash_status"] == "ok":
                hk = (r["groovestats_hash"].lower(),
                      r["groovestats_hash_version"])
            out.append({
                "pack": pack, "dir": sdir, "rel": rel, "slot": r["difficulty"],
                "title": r["title"], "artist": r["artist"],
                "meter": r["meter"], "raw": mv[0], "cal": mv[1],
                "rating": mv[2], "key": (pack.lower(), sdir.lower()),
                "length": ml, "hash": hk,
            })
    if progress:
        progress(len(files), len(files))
    return out, stats


def parse_roots(root):
    """One folder, several folders separated by ';', or a list -> list of
    Paths. A chart's song folder counts as present if it exists under ANY."""
    if not root:
        return []
    if isinstance(root, str):
        root = root.split(";")
    return [Path(r.strip()) for r in root if str(r).strip()]


def song_dir_present(rel, roots):
    return any((r / rel).is_dir() for r in roots)


def filter_library(rows, include=None, exclude=None, root=None,
                   min_seconds=0, max_seconds=0, keep_duplicates=False):
    """Apply the user's choices to scanned rows. include/exclude are sets of
    lower-case pack names (None = no filter). root: folder(s) that contain
    Songs/ (see parse_roots). Returns (rows, counts)."""
    cnt = {"excluded_pack": 0, "gone": 0, "length": 0, "dup": 0}
    roots = parse_roots(root)
    dir_ok = {}
    seen, out = set(), []
    for c in rows:
        p = c["pack"].lower()
        if (include is not None and p not in include) or \
                (exclude is not None and p in exclude):
            cnt["excluded_pack"] += 1
            continue
        if roots:
            ok = dir_ok.get(c["rel"])
            if ok is None:
                ok = dir_ok[c["rel"]] = song_dir_present(c["rel"], roots)
            if not ok:
                cnt["gone"] += 1
                continue
        ml = c["length"]
        if ml is not None and ((min_seconds and ml < min_seconds) or
                               (max_seconds and ml > max_seconds)):
            cnt["length"] += 1
            continue
        if not keep_duplicates and c["hash"] is not None:
            if c["hash"] in seen:
                cnt["dup"] += 1
                continue
            seen.add(c["hash"])
        out.append(c)
    return out, cnt


def load_library(cache_dir, model, a):
    """CLI helper: scan, then filter with the command-line options."""
    inc = exc = None
    if a.include_packs_file:
        inc = {p.lower() for p in ecf.read_pack_list(a.include_packs_file)}
    if a.exclude_packs_file:
        exc = {p.lower() for p in ecf.read_pack_list(a.exclude_packs_file)}
    rows, stats = scan_library(cache_dir, model)
    rows, cnt = filter_library(rows, inc, exc, a.root, a.min_seconds,
                               a.max_seconds, a.keep_duplicates)
    stats.update(cnt)
    return rows, stats


# ----------------------------------------------------------------- course ---

def pick(cands, wanted, a, rng):
    """cands: rated charts. wanted: list of (lo, hi) per course entry."""
    chosen, used_songs, used_packs = [], set(), {}
    for lo, hi in wanted:
        pool = [c for c in cands if lo <= c["rating"] <= hi
                and (a.allow_same_song or c["key"] not in used_songs)
                and (not a.max_per_pack
                     or used_packs.get(c["pack"].lower(), 0) < a.max_per_pack)]
        if not pool:
            return chosen, (lo, hi)
        # one candidate per song first, so songs with several charts at this
        # rating are not favoured
        bysong = {}
        for c in pool:
            bysong.setdefault(c["key"], []).append(c)
        song = rng.choice(sorted(bysong))
        c = rng.choice(bysong[song])
        chosen.append(c)
        used_songs.add(c["key"])
        used_packs[c["pack"].lower()] = used_packs.get(c["pack"].lower(), 0) + 1
    return chosen, None


def write_crs(path, chosen, a, label):
    for s, nm in ((a.title, "title"), (a.scripter, "scripter")):
        if s and BAD_CHARS.search(s):
            sys.exit("--%s may not contain : ; # (the course file cannot "
                     "escape them)" % nm)
    mods = "nodifficult" if not a.no_pin else ""
    L = ["#COURSE:%s;" % a.title]
    if a.scripter:
        L.append("#SCRIPTER:%s;" % a.scripter)
    L.append("#DESCRIPTION:%s;" % label)
    if a.lives:
        L.append("#LIVES:%d;" % a.lives)
    if a.style:
        L.append("#STYLE:%s;" % a.style)
    for c in chosen:
        L.append("#SONG:%s/%s:%s:%s;" % (c["pack"], c["dir"], c["slot"], mods))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")


def parse_range(s):
    m = re.fullmatch(r"\s*(\d+)\s*(?:-\s*(\d+))?\s*", s)
    if not m:
        sys.exit("bad rating range %r (use 11 or 10-12)" % s)
    lo = int(m.group(1))
    hi = int(m.group(2) or lo)
    if lo > hi or lo < 1 or hi > 19:
        sys.exit("rating range must be within 1-19 and low <= high")
    return lo, hi


def main():
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(
        description="Build an ITGmania .crs from modeled chart difficulty.")
    ap.add_argument("cache", help='the ITGmania "Cache" folder (or Cache/Songs)')
    ap.add_argument("--model", default=str(Path(__file__).resolve().parent
                                           / "difficulty_model_notech.json"))
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--rating", help="target modeled rating for every entry, "
                   "e.g. 11")
    g.add_argument("--range", dest="rrange", help="allowed modeled rating "
                   "range for every entry, e.g. 10-12")
    g.add_argument("--ratings", help="comma list, one entry per item, in "
                   "order; each item is N or LO-HI, e.g. 9,10,11-12")
    ap.add_argument("--count", type=int, default=10,
                    help="number of entries with --rating/--range (default 10)")
    ap.add_argument("--out", help="course file to write, e.g. "
                    "Courses/Modeled/Eleven.crs")
    ap.add_argument("--title", help="course title (default: from --out name)")
    ap.add_argument("--scripter", default="")
    ap.add_argument("--lives", type=int, default=0)
    ap.add_argument("--style", default="", help='optional #STYLE value, e.g. '
                    '"single". Off by default; the v1.3.0 course loader '
                    'skips #STYLE (see the course findings note, 3), so it '
                    'has no effect there')
    ap.add_argument("--sort", choices=["random", "asc", "desc"],
                    default="random",
                    help="order of entries with --rating/--range "
                    "(asc/desc use the unrounded modeled value)")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--include-packs-file")
    ap.add_argument("--exclude-packs-file")
    ap.add_argument("--root", help="folder containing Songs/ (several: separate with ';'); cache entries whose song folder is not found in any of them are ignored. On Windows the songs are usually in %%APPDATA%%\\ITGmania or the install folder")
    ap.add_argument("--min-seconds", type=float, default=0)
    ap.add_argument("--max-seconds", type=float, default=0)
    ap.add_argument("--max-per-pack", type=int, default=0)
    ap.add_argument("--allow-same-song", action="store_true")
    ap.add_argument("--keep-duplicates", action="store_true",
                    help="do not collapse charts that share a GrooveStats hash")
    ap.add_argument("--no-pin", action="store_true",
                    help="omit 'nodifficult' so Hard/Challenge course "
                    "difficulties shift each entry to a neighbouring slot")
    ap.add_argument("--histogram", action="store_true",
                    help="print charts per modeled rating and stop")
    a = ap.parse_args()

    model = load_model(a.model)
    cache_dir = ecf.find_song_cache(a.cache)
    lib, st = load_library(cache_dir, model, a)
    print("cache files: %d, charts: %d" % (st["files"], st["charts"]))
    print("skipped: not dance-single %d, Edit %d, flagged/unrated %d, "
          "no song folder in path %d, ':;#' in name %d, pack filter %d, "
          "folder missing %d, length filter %d, duplicate hash %d"
          % (st["not_single"], st["edit"], st["flagged"], st["no_song_dir"],
             st["bad_name"], st["excluded_pack"], st["gone"], st["length"],
             st["dup"]))
    print("usable rated charts: %d" % len(lib))
    if not lib:
        sys.exit("nothing to choose from")

    if a.histogram or not (a.rating or a.rrange or a.ratings):
        hist = {}
        for c in lib:
            h = hist.setdefault(c["rating"], [0, set()])
            h[0] += 1
            h[1].add(c["key"])
        print("\nmodeled  charts  songs")
        for k in sorted(hist):
            print("%7d  %6d  %5d" % (k, hist[k][0], len(hist[k][1])))
        if not a.histogram:
            print("\nGive --rating, --range or --ratings (and --out) to build "
                  "a course.")
        return

    if not a.out:
        sys.exit("--out is required to write a course")
    out = Path(a.out)
    if not a.title:
        a.title = out.stem
    if a.ratings:
        wanted = [parse_range(s) for s in a.ratings.split(",")]
        label = "Modeled difficulty ladder: " + a.ratings
        a.sort = "random"  # order is the one given
    else:
        lo, hi = parse_range(a.rating or a.rrange)
        wanted = [(lo, hi)] * a.count
        label = ("Modeled difficulty %s" % (a.rating or a.rrange)
                 ) + ", %d songs" % a.count
    if a.count < 1 and not a.ratings:
        sys.exit("--count must be at least 1")

    rng = random.Random(a.seed)
    chosen, fail = pick(lib, wanted, a, rng)
    if fail:
        lo, hi = fail
        sys.exit("only found %d of %d entries: ran out of charts rated %s "
                 "(after one-song / per-pack limits). Try a wider --range, "
                 "--allow-same-song, or fewer entries."
                 % (len(chosen), len(wanted),
                    str(lo) if lo == hi else "%d-%d" % (lo, hi)))
    if a.sort != "random" and not a.ratings:
        chosen.sort(key=lambda c: c["cal"], reverse=(a.sort == "desc"))
    write_crs(out, chosen, a, label)
    print("\nwrote %s (%d entries)" % (out, len(chosen)))
    for i, c in enumerate(chosen, 1):
        print("%2d. [%2d  %5.2f] %-8s %-30s %s / %s  (label %s)"
              % (i, c["rating"], c["cal"], c["slot"], c["title"][:30],
                 c["pack"][:24], c["dir"][:24], c["meter"]))


if __name__ == "__main__":
    main()
