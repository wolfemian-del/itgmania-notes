ITGMANIA CODE ANALYSIS - PROJECT INDEX
REVISION: 2026-10-31-e (flat notes, patches and the former claude/ files sorted into notes/, patches/, tools/difficulty/; stale known gaps removed) | file: INDEX.md | READ THIS FIRST in every chat
Purpose: find the right file and section without reading everything. Not a findings file.
Tags used in all files: [CODE] [INFERRED] [UNVERIFIED] [TESTED]/[OBSERVED] (user-run).
Version basis: v1.3.0 (8a3bf8884a) unless a row says beta. Beta head last seen 26d81c1a6f (2026-10-29, course/mod files compared for cref; earlier: eac008e0ac 2026-10-24 modeled-sort enum only; engine beta 05a6439 2026-10-15 offrec only).

FILE STATUS LABELS (use exactly these words at the start of a status cell; add OPEN-CHECKS if in-game items remain)
 REFERENCE            spec or map; prefer it over older overlapping notes
 ACTIVE               work in progress; claims may still move
 PATCH-BUILT-TESTED   built and exercised in game (or CI plus user confirmation)
 PATCH-APPLY-CHECKED  applies cleanly / syntax-checked; NOT claimed as run
 ARCHIVE              superseded or chronological log; history only
 A label is not proof: nothing is production-proven unless the note carries [TESTED]/[OBSERVED].

PREFIX GLOSSARY (citation prefix -> primary file -> what it covers)
 engine    notes/itgmania_engine_notes_v3.txt              core: workspace setup, architecture map, to-do, KNOWN-WRONG CLAIMS
 loadmem   notes/itgmania_load_memory_findings.txt         song loading, memory, caches, timing tables
 toggle    notes/itgmania_toggle_findings.txt              pack/song toggle (DisabledGroups), wheel timing, SL operator menu
 beta      notes/itgmania_beta_findings.txt                read-only findings on the beta branch
 series    notes/itgmania_series_notes.txt                 Pack.ini Series / SORT_SERIES
 sketch    notes/itgmania_pack_toggle_sketch.txt           pack toggle design, build log, open test list (Part I3)
 diffnotes notes/itgmania_difficulty_rating_notes.txt      chronological log of the difficulty-rating work (archive)
 writeup   notes/itgmania_difficulty_rating_writeup.txt    derived difficulty rating: the organized account
 display   notes/itgmania_display_meter_findings.txt       show the modeled rating instead of the official meter
 reload    notes/itgmania_reload_profile_fix_evaluation.txt  Reload Songs clears the saved P1 profile
 offrec    notes/itgmania_offset_recommend_findings.txt    Global Offset recommendation from session tap data
 codescan  notes/itgmania_codescan_findings.txt            CodeQL alert triage on the fork
 msort     notes/itgmania_modeled_sort_findings.txt        sorting the wheel by the modeled rating
 course    notes/itgmania_course_builder_findings.txt      building .crs files from modeled difficulty (script, GUI)
 cref      notes/itgmania_course_format_reference.txt      .crs format, #MODS, #SONGSELECT, engine parse rules
 score     notes/itgmania_score_matching_findings.txt      how a stepfile is matched to a score in a profile
 Other notes (input, padsensor, editor, editor_clipboard_mouse, misc, cache_format_spec) have no prefix; use the topic table.

REPO WORKFLOW (2026-10-30): the GitHub repo wolfemian-del/itgmania-notes IS the canonical store. There is no
 second copy: the old Project docs are deprecated and must not be edited. All paths in this file are repo paths.
 Edit files in place and commit; git history replaces whole-file re-typing, and files may be moved with git mv.
 Licensing: see NOTICE.

HOW TO START A CHAT
 1. Read this file. Pick the topic row(s) below; read only those files/sections.
 2. For source work read notes/itgmania_engine_notes_v3.txt sections 0-2, 5, 6 and 8 (task,
    workspace setup, architecture map, to-do list, KNOWN-WRONG CLAIMS).
 3. Check the repo against the FILE STATUS TABLE (git ls-files); report any file that is missing from the
    table or listed but absent before other work. Do not ask the user to re-upload a file that is in the repo.
 4. Cite sections with the file prefix: engine (core v3), loadmem, toggle, beta, series,
    sketch, diffnotes, display, reload, offrec, codescan, msort, course, cref, score, e.g. "loadmem:7q", "series:12h", "sketch:I3", "diffnotes:11",
    "display:4", "offrec:7", "codescan:5", "msort:3", "course:5", "cref:7". Bare "section 7" is ambiguous. Older files still say
    "engine notes 7x": use the SECTION MAP below to find where 7x lives now.
 5. When a file changes: bump its REVISION, update its row in the status table and the
    topic table, tell the user.
 6. WHEN A FILE CHANGES: commit it in place (bump its REVISION line and its row here in the same commit),
    use a plain-language commit message, and tell the user which paths changed. Moving files into the target
    folders is allowed with git mv, in a commit that also updates the paths in this file. Files edited for
    new findings also get a FILE STATUS header if they lack one.

SECTION MAP (former itgmania_engine_notes.txt, split 2026-10-12; section IDs unchanged)
 engine (notes/itgmania_engine_notes_v3.txt): 00, 0, 1, 2, 3, 3a, 5, 5b, 6, 8 (4 = pointer)
 loadmem (notes/itgmania_load_memory_findings.txt): 4, 4a-4g, 7p, 7q, 7s
 toggle (notes/itgmania_toggle_findings.txt):   7f, 7g, 7h, 7k, 7l, 7m, 7n, 7v, 7w
 beta (notes/itgmania_beta_findings.txt):       7b, 7c, 7d, 7e, 7i, 7j, 7o, 7r, 7t, 7u
 display (notes/itgmania_display_meter_findings.txt): 1-8 (sites, data uses, Lua capabilities, patch contents, tests, risks, next, in-game checks)
 reload (notes/itgmania_reload_profile_fix_evaluation.txt): 1-8 (answer, bug recap, why both calls skipped, persistent branch, callers, risk, in-game checks, status)
 offrec (notes/itgmania_offset_recommend_findings.txt): 1-14 (idea, answer, per-tap data, sign, F6 autosync, Lua pref/file access, pack SyncOffset effect, design, open checks, next, Simply Love findings, SL session reset, engine per-song autosync reset, beta/upstream comparison)
 codescan (notes/itgmania_codescan_findings.txt): 1-8 (answer, how read, #464 ffmpeg, #461 shuffle seed, #427 malloc/delete + fix, #4/#5 alloca, excluding extern/ + alert handling, open)
 msort (notes/itgmania_modeled_sort_findings.txt): 1-8 (answer, how the Meter sort works, Steps data access/Compress safety/parity, enum/IsSongSort/persistence/unknown names, Simply Love sort menu, options A-D and decisions D1-D4, beta comparison, in-game checks and next steps)
 course (notes/itgmania_course_builder_findings.txt): 1-12 (answer and usage, .crs syntax, rating and picking, caveats, tests, in-game checks C1-C7, 9 GUI, 10 full .crs parameter reference, 11 Songs location, 12 failoff / fail-type reset and its patch; the note's own contents are the detail)
 cref (notes/itgmania_course_format_reference.txt): 1-18 (answer F1-F7, method, MSD syntax, header tags, #SONG, #SONGSELECT, timed #MODS 7, mod vocabulary 8, pipeline 9, lives/award 10, loading/cache 11, Lua API 12, doc-vs-code D1-D13 13, community claims 14, beta 15, in-game checks M1-M11 16, observations, open)

TOPIC TABLE (topic | read | status)
 Series feature (Pack.ini Series/SeriesBanner, SORT_SERIES) | notes/itgmania_series_notes.txt (1-11 = v1.3.0; 12 = beta) ; engine:3, 3a ; beta:7r | complete
 Pack/song toggle (DisabledGroups, UI, SL operator menu) | notes/itgmania_pack_toggle_sketch.txt (Parts A-I) ; toggle:7f, 7g, 7h, 7n, 7v ; patches/itgmania_pack_toggle*.patch, patches/sl_toggle_songs.patch | built + field-tested; open tests sketch:I3 items 12-36
 Wheel timing log (LogWheelTimings) | patches/wheel-timing-log.patch ; toggle:7n, 7w ; sketch:I4 | done
 SL song-search shortcut (F key) | patches/sl_song_search_shortcut.patch ; toggle:7m | F works; checks 27-36 open (sketch:I3)
 Reload Songs clears saved P1 profile | reload (notes/itgmania_reload_profile_fix_evaluation.txt) ; patches/reload_keep_default_profile.patch ; toggle:7v item 4 | PATCH-APPLY-CHECKED; OPEN-CHECKS reload:7 (pushed to fork 2026-10-14, not built or run)
 GitHub code scanning (CodeQL) alerts on the fork: triage, fix, extern/ filter | codescan (notes/itgmania_codescan_findings.txt) ; patches/palettize_free_colormap.patch ; patches/codeql_filter_extern.patch | REFERENCE: COMPLETE 2026-10-16, 0 open alerts [OBSERVED]; optional upstream reports codescan:8
 Multi-song Global Offset recommendation (tap offsets vs F6 autosync; NULL/ITG pack offsets) | offrec (notes/itgmania_offset_recommend_findings.txt) ; engine:3 | ACTIVE, read-only: feasible in theme Lua, nothing built; checks offrec:9 G1-G8, open S2/S6
 Sort the wheel by the modeled difficulty rating (new SORT_MODELED_METER) | msort (notes/itgmania_modeled_sort_findings.txt) ; display:2 ; beta:7r ; toggle:7w | ACTIVE, read-only design: feasible, no code; decisions msort:6 D1-D4, checks msort:8 open
 Build Course (.crs) files from modeled difficulty, script and GUI | course (notes/itgmania_course_builder_findings.txt) ; tools/difficulty/make_course_by_rating.py, make_course_gui.py ; patches/itgmania_course_reset_song_level_v1.3.0.patch | ACTIVE; OPEN-CHECKS course:7 (GUI seen on real cache; C7 failoff results course:12)
 Course (.crs) format reference: supported/unsupported tags, #MODS, #SONGSELECT, mod vocabulary | cref (notes/itgmania_course_format_reference.txt) ; tools/course/ (parser test, test-pack generator) ; course:10, 12 | ACTIVE; OPEN-CHECKS cref:16 (M3b, M3c, M4, M11 pending); key result F1: colon-form #MODS does nothing
 Song loading, memory, caches, timing tables | loadmem:4, 4a-4g, 7p, 7q, 7s | read-only findings
 Input codes ("|", close-folder fallback) | notes/itgmania_input_notes.txt ; beta:7b | done (beta)
 Pad sensors / SnekConfig / PumpHID | notes/itgmania_padsensor_notes.txt ; beta:7c | done (beta)
 Editor: waveform, Adjust Sync, TempoDetector | notes/itgmania_editor_notes.txt ; beta:7o | done (beta)
 Editor: clipboard, undo/redo, mouse | notes/itgmania_editor_clipboard_mouse_notes.txt ; beta:7d | done (beta)
 WASAPI default, BrokeIO lights, show-one-in-row, websocket deflate | notes/itgmania_misc_notes.txt ; beta:7e, 7i, 7j | done (beta)
 Other beta commits (build cleanup, profile sort, video refactor) | beta:7t, 7u | read, not run
 Derived difficulty rating (1-19, DDR X scale) | notes/itgmania_difficulty_rating_writeup.txt first; diffnotes for code hook points; cache spec; tools | Lua port verified in game; open items writeup:10
 Show modeled rating instead of the official meter (pref DifficultyDisplay, Pack.ini DifficultyMode) | display (notes/itgmania_display_meter_findings.txt) ; patches/sl_display_meter.patch | PATCH-APPLY-CHECKED; OPEN-CHECKS display:8 (mock-tested Lua only, not run in game)
 Second-stage user docs | engine:6 item 8 ; cref is the first course-specific source for it | OPEN

FILE STATUS TABLE (file | status | version basis | revision | in-file header)
 Header column: FS = has a "FILE STATUS" block (status, basis, topic key, read-when, see-also);
 REV = has only a title + REVISION block; none = no header (code/patch/data).
 Notes (notes/)
  notes/itgmania_engine_notes_v3.txt | ACTIVE core: architecture, series state, to-do, errata | v1.3.0 8a3bf8884a; beta seen up to 7b34bfe2ac | 2026-10-12-a | FS
  notes/itgmania_load_memory_findings.txt | ACTIVE, read-only findings | v1.3.0; 7q, 7s also checked on beta | 2026-10-12-a | FS
  notes/itgmania_toggle_findings.txt | ACTIVE; open tests sketch:I3; 7v item 4 says PARKED (now see reload) | v1.3.0 + Simply Love dd06138; patches apply to beta c8e69b9ca8 | 2026-10-12-a | FS
  notes/itgmania_beta_findings.txt | ACTIVE, read-only findings on beta | beta 28e58a78c7 -> c8e69b9ca8 -> e4b4bf0755 | 2026-10-12-a | FS
  notes/itgmania_display_meter_findings.txt | ACTIVE; patch built, in-game checks open (section 8) | v1.3.0 + Simply Love dd06138; beta not diffed | 2026-10-30-b | FS
  notes/itgmania_reload_profile_fix_evaluation.txt | ACTIVE; fix drafted, checks open (section 7); its section 8 still says "not committed" (now pushed, see topic row) | v1.3.0 8a3bf8884a; beta 3f5f27725a (identical Reload) | 2026-10-31-a | FS
  notes/itgmania_offset_recommend_findings.txt | NEW 2026-10-14: ACTIVE read-only findings; nothing built or run; open checks section 9 | engine v1.3.0 8a3bf88 + beta 05a6439; Simply Love fork itgmania-release 2c58dab + upstream itgmania-release dd06138 / itgmania-beta 649706f | 2026-10-15-c | FS
  notes/itgmania_codescan_findings.txt | NEW 2026-10-15: COMPLETE 2026-10-16 (0 open alerts); #427 fixed, extern/ filter works; only optional upstream reports left (section 8) | fork release 51bf20206 -> d5f0548 -> 16614f1 -> cbeaa30, beta 7b83223dd -> bd26dd6 -> fb259b3 -> 29275af; FFmpeg pin 9bc0bcce7a03 | 2026-10-16-c | FS
  notes/itgmania_modeled_sort_findings.txt | NEW 2026-10-24: ACTIVE read-only findings and design evaluation; nothing built or run; decisions msort:6 D1-D4 and in-game checks msort:8 open | engine v1.3.0 8a3bf8884a; beta eac008e0ac (enum, IsSongSort and Meter-sort call sites only); Simply Love dd06138 | 2026-10-30-a | FS
  notes/itgmania_course_builder_findings.txt | NEW 2026-10-24: ACTIVE; .crs syntax and course loading read from source; script and GUI mock-tested only; in-game checks section 7 open; 5.3 and 10.1 are extended by cref | engine v1.3.0 8a3bf8884a; model difficulty_model_notech.json | 2026-10-31-a | FS
  notes/itgmania_course_format_reference.txt | NEW 2026-10-30: ACTIVE; read-only analysis plus one synthetic parser test; nothing run in game; checks cref:16 open; Reddit thread analysed (cref:14) | engine v1.3.0 8a3bf8884a; beta 26d81c1a6f (course/mod files) | 2026-10-31-a | FS
  notes/itgmania_score_matching_findings.txt | NEW 2026-10-25: ACTIVE read-only findings; nothing built or run; how a stepfile is matched to a score in a profile (renaming/moving songs, Stats.xml, edit charts); cite as score:N | engine v1.3.0 8a3bf8884a; beta NOT checked | 2026-10-25-b | FS
  notes/itgmania_series_notes.txt | ACTIVE, complete | v1.3.0; section 12 = beta e4b4bf0755 | 2026-10-31-a | FS
  notes/itgmania_pack_toggle_sketch.txt | ACTIVE; open test list Part I3 | v1.3.0; patches apply to beta c8e69b9ca8 (git apply --check, not compiled) | 2026-10-31-a | FS
  notes/itgmania_editor_notes.txt | ACTIVE, complete (in-game checks only) | beta 28e58a78c7 (some items c8e69b9ca8) | 2026-10-11-a | FS
  notes/itgmania_editor_clipboard_mouse_notes.txt | ACTIVE, complete (in-game checks only) | beta 28e58a78c7 | 2026-10-11-a | FS
  notes/itgmania_input_notes.txt | ACTIVE, complete | beta 28e58a78c7 | 2026-10-11-a | FS
  notes/itgmania_padsensor_notes.txt | ACTIVE, complete (hardware checks only) | beta 28e58a78c7 (some items c8e69b9ca8) | 2026-10-11-a | FS
  notes/itgmania_misc_notes.txt | ACTIVE, four items done (hardware/in-game checks only) | beta 28e58a78c7; WASAPI driver itself is in v1.3.0 | 2026-10-11-a | FS
  notes/itgmania_difficulty_rating_notes.txt | ARCHIVE (chronological log; the writeup is the organized account) | v1.3.0; beta not diffed | 2026-10-31-a | FS
 Writeup (notes/)
  notes/itgmania_difficulty_rating_writeup.txt | ACTIVE; open items section 10 | v1.3.0 + Simply Love; beta not diffed | 2026-10-31-a | FS
 Patches (patches/; apply order: toggle, toggle_ui, wheel-timing, clang fix; SL patches go to the theme)
  patches/itgmania_pack_toggle_v1.3.0.patch | built and field-tested by the user | v1.3.0 (also applies to beta c8e69b9ca8) | none | none
  patches/itgmania_pack_toggle_ui_v1.3.0.patch | apply after the first; field-tested | v1.3.0 (also applies to beta c8e69b9ca8) | none | none
  patches/wheel-timing-log.patch | field-tested (pref LogWheelTimings) | v1.3.0 fork build | none | none
  patches/itgmania_clang_format_fix.patch | apply LAST; fork build passed with it | v1.3.0 fork build | none | none
  patches/reload_keep_default_profile.patch | NEW 2026-10-14: SongManager::Reload skips the default-profile pref write and the profile load for guests (3 lines). git apply --check clean on v1.3.0 and beta 3f5f27725a; g++ -fsyntax-only OK; pushed to the fork's release and beta branches; NOT built or run in game; independent of the toggle patches | v1.3.0; beta 3f5f27725a | none | none
  patches/itgmania_course_reset_song_level_v1.3.0.patch | NEW 2026-10-28: ScreenGameplay::SetupSong resets Current options to the Song level instead of the Stage level, so per-entry failoff survives the course song change (1 statement). git apply --check clean on v1.3.0; g++ -fsyntax-only OK on release and beta; pushed 2026-10-28 to fork release (772575e) and beta (ceaa23b); NOT built or run in game | v1.3.0; fork beta 29275af | none | none
  patches/palettize_free_colormap.patch | NEW 2026-10-15: RageSurfaceUtils_Palettize.cpp line 293 "delete acolormap" -> "free(acolormap)" (1 line; CodeQL #427, closed by it). git format-patch of the release commit d5f0548; reverse-applies clean on release; the beta commit bd26dd6 is the same change; pushed to both branches; fork CI/Release workflow runs on later commits show success; NOT run in game; independent of the other engine patches | v1.3.0 fork release; beta 7b83223dd | none | none
  patches/codeql_filter_extern.patch | NEW 2026-10-15: .github/workflows/codeql.yml (+21 lines): analyze with upload: never, jq drops extern/ results from the SARIF, upload-sarif with the same category. git format-patch of release 16614f1; beta fb259b3 is the same change. WORKS [OBSERVED 2026-10-16]. NOTE: this patch alone does not change the push trigger; the follow-up commits cbeaa30 (release) / 29275af (beta) add workflow_dispatch and the workflow/config paths to the trigger and are NOT in this patch file | fork release / beta workflow as of 2026-10-15 | none | none
  patches/sl_toggle_songs.patch | field-tested (operator-menu entry works) | Simply Love dd06138 | none | none
  patches/sl_toggle_songs_manual_edits.txt | hand-edit form of the patch above (en.ini strings now match the patch: "🤍  " prefix) | Simply Love dd06138 | 2026-10-13-a | FS
  patches/sl_song_search_shortcut.patch | F key works; checks 27-36 open | Simply Love dd06138 (engine v1.3.0/beta unchanged for it) | none | none
  patches/sl_display_meter.patch | rebuilt 2026-10-13 (replaces the 2026-10-12 version, which had a Chart-row "%i" error in Both mode); git apply --check clean on dd06138; Lua parses on 5.1 and 5.4; logic mock-tested (32 cases); NOT run in game. Needs tools/difficulty/DifficultyModel.lua already in the theme Scripts folder | Simply Love dd06138 | none | none
 Difficulty tools and data (tools/difficulty/; the former claude/ folder, emptied 2026-10-31)
  tools/difficulty/extract_chart_features.py, fit_difficulty_model.py (v2), make_lua_rating.py, apply_model.py,
   predict_meter_check.py | user-run on the real library | v1.3.0 cache format | uploaded 2026-10-11 | none
  tools/difficulty/DifficultyModelCheck.lua, DifficultyModel.lua | Lua port verified in game (Simply Love, dance-single) | v1.3.0 | uploaded 2026-10-11 | none
  tools/difficulty/difficulty_model_notech.json | deployed model; DifficultyModel.lua is generated from it | v1.3.0 | uploaded 2026-10-11 | none (JSON: no comments)
  notes/itgmania_cache_format_spec.txt | REFERENCE; written from the writer source, no real cache file inspected | v1.3.0 | 2026-10-31-a | FS
 Tools (tools/difficulty/)
  tools/difficulty/make_course_gui.py | NEW 2026-10-25: tkinter front end for the course builder; imports make_course_by_rating (same folder, plus extract_chart_features.py and the model JSON); standard library only; tested headless on Linux (Xvfb) with a synthetic cache, NOT on Windows, NOT on the real cache | course:9 | 2026-10-25 | docstring
  tools/difficulty/make_course_by_rating.py | NEW 2026-10-24, revised 2026-10-25 (load_library split into scan_library + filter_library for the GUI; CLI output unchanged): course builder; imports extract_chart_features.py and reads difficulty_model_notech.json (both now in the same folder); standard library only; mock-tested, NOT run on the real cache; the test used a stub of the extractor functions, not the full project file | v1.3.0 cache format + engine .crs syntax | 2026-10-24 | docstring
 Tools (tools/course/)
  tools/course/crs_mods_parser_test.sh | NEW 2026-10-30: bash + g++; cuts the REAL MsdFile::ReadBuf, split/Trim and ParseCourseMods text out of a v1.3.0 checkout by line range, builds with stubs, runs 18 #MODS scenarios (cref:7.1). Usage: bash crs_mods_parser_test.sh <itgmania checkout at v1.3.0>. Line ranges are valid for v1.3.0 only | v1.3.0 8a3bf8884a | 2026-10-30 | comment header
  tools/course/make_cref_test_pack.py | NEW 2026-10-30 (--diff option added -g): stdlib Python; writes 14 .crs files for checks cref:16 M1-M11 (M10a/b) plus CHECKLIST.txt with predictions. Usage: python make_cref_test_pack.py --song1 "Pack/Song" --song2 ... --song3 ... --out CrefTests; copy output into Courses/. Test-generated with dummy names only | v1.3.0 | 2026-10-30 | docstring
  tools/course/extract_mod_tokens.py | NEW 2026-10-30: pulls the mod literals/numbered families/find() gates out of PlayerOptions.cpp lines 768-1521 into JSON (usage: python3 -I extract_mod_tokens.py out.json; path to the checkout is hard-coded to /home/claude/itgmania) | v1.3.0 | 2026-10-30 | none
 Root: INDEX.md (this file)
 NOTE: older notes write patch names with dots (..._v1.3.0.patch) or underscores
   (..._v1_3_0.patch); the repo uses the names above. Same files.

GITHUB FORKS (user's; Claude may commit and push there directly, user's rule 2026-10-13)
 Engine: github.com/wolfemian-del/itgmania (upstream itgmania/itgmania; default branch release)
  release  v1.3.0 + the four engine patches (Ian's commits) + Simply Love fork submodule pin; stable build
           tip 772575e (2026-10-28: + course reset Song-level patch; 2026-10-16: CodeQL trigger fix; 2026-10-15: + Palettize free() fix d5f0548 and CodeQL
           extern/ filter 16614f1, on 51bf20206; 2026-10-14: + Reload guest-profile fix, on dab9b1a87)
  beta     upstream beta (merged to acf1637870 on 2026-10-13) + the same patches in one commit + theme pin
           tip ceaa23b (2026-10-28: + course reset Song-level patch; 2026-10-16: CodeQL trigger fix; 2026-10-15: + Palettize free() fix bd26dd6 and CodeQL
           extern/ filter fb259b3, on 7b83223dd; 2026-10-14: + Reload guest-profile fix, on 0239eac16)
  itg-patches  REDUNDANT (duplicate of release, made by Claude 2026-10-13); delete on GitHub (the push proxy
           refused the delete with HTTP 403, so the user must do it)
  Pushing needs the repo attached to the session (add_repo with push access); without it the git proxy
           returns 403 "not in this session's authorized repository set". Read-only add_repo (2026-10-29) gives git
           clone/fetch only: gh api and WebFetch on github.com PR pages are refused (cref:14).
 Simply Love: github.com/wolfemian-del/Simply-Love-SM5 (upstream Simply-Love/Simply-Love-SM5; default itgmania-release)
  itgmania-release  dd06138 + Toggle Songs entry + F song search + DifficultyDisplay + Scripts/DifficultyModel.lua
           (tip 2c58dab1, 2026-10-13); this is the branch the engine pins
  itg-patches  REDUNDANT (same commit as itgmania-release); delete on GitHub (same 403)
  No itgmania-beta branch yet: upstream's is 15 commits past dd06138 and a trial merge conflicts in
           Scripts/SL-PlayerOptions.lua and metrics.ini; upstream engine beta still pins dd06138. Create it
           when the engine beta bumps its pin. (Upstream itgmania-beta is 649706f as of 2026-10-15.)
 Build workflow (.github/workflows/release.yml, triggers on push to beta and release): trimmed on BOTH engine
  branches (release: user's eefc12b91d; beta: 0239eac16e, 2026-10-13) to one job, windows-2022 with
  WITH_CLUB_FANTASTIC=Off, so no song packs are bundled and the installer name ends -no-songs. [CODE]
  release still uses WITH_FULL_RELEASE=On (adds Texture Font Generator.exe); beta uses the nightly config.
  The workflow only uploads/attests an artifact (no GitHub Release). x64 is [INFERRED] (setup-env asks
  msbuild for x64; no platform override). Run conclusions CAN be read with gh run list (worked 2026-10-16;
  the 2026-10-14 note that Actions results were unreadable no longer holds); release.yml runs on the
  2026-10-15/16 commits show success.
 Both engine branches pin the SL fork by commit (submodule URL = the fork, no branch key). When
 itgmania-release moves, bump the gitlink on release and beta. Keep the pin on the branch tip so a shallow
 submodule fetch can find it.
 Local clones used by Claude are lost with the session; git remotes: origin = the fork, upstream = mainline.
 Code scanning: workflow .github/workflows/codeql.yml ("CodeQL Advanced", Ubuntu, build-mode manual) with
  .github/codeql/codeql-config.yml; since 2026-10-15 it filters extern/ results before upload and runs on
  changes to the workflow/config or manual dispatch (see codescan:7). The session credential cannot read
  alerts (API 403 2026-10-15); the user pastes alert text. State 2026-10-16: 0 open alerts.

FOLDER LAYOUT (repo paths)
 Applied (2026-10-30): notes/ (all notes, the difficulty writeup and the cache format spec), patches/ (all .patch files and the
   hand-edit text), tools/difficulty/ (course builder, difficulty-model scripts, model JSON and Lua), tools/course/,
   INDEX.md/README.md/NOTICE at the root. claude/ was emptied 2026-10-31 and is gone; nothing is loose at the root.
 New files: always give an explicit folder path; never create new files at the root except INDEX/README/NOTICE/AGENTS.
 Filenames use underscores; scripts import each other by exact name (extract_chart_features.py,
   difficulty_model_notech.json). Keep them beside the course scripts when running them.

KNOWN GAPS IN THE FILES (as of this revision; entries written before 2026-10-30 refer to the Project era: "re-typed" = rewritten whole through the Project tools, "Project copies" = the now-deprecated Project docs)
 - Older files (sketch, series notes, input/misc/padsensor/editor notes, patches, difficulty
   notes) still say "engine notes 7x" or "section 00 manifest"; use the SECTION MAP above. The
   manifest and ls procedure no longer exist (replaced by this index).
 - diffnotes section 11 repeats the deployed-model and in-game entries; use the writeup.
 - The difficulty writeup (notes/itgmania_difficulty_rating_writeup.txt) does not yet mention the
   display-meter work, the modeled-sort evaluation or the course builder; its open items (section 10) are unchanged. See display notes
   section 7, msort:6 and course:1.
 - toggle:7v item 4, engine:6 item 13 and reload:8 still say "PARKED" / "not committed" (not re-typed, to
   avoid undiffed rewrites of large files); the topic row above supersedes them. The reload topic row's
   "results unread" for the Actions builds can now be checked with gh run list (not done).
 - offrec: the beta/upstream comparison (offrec:14) diffed whole files but checked only the lines the
   findings depend on in the larger changed files (Player, GameState, ScreenDebugOverlay,
   ScreenGameplay, Song, TimingData, ProfileManager); other upstream Simply Love branches were not
   compared. offrec was rewritten whole four times (2026-10-14-a/b, 2026-10-15-a/b/c); sections
   were re-typed, not diffed.
 - codescan: only alerts #464, #461, #427, #4, #5 were assessed; the other 470-odd extern/ alerts were not seen
   (closed by the filter, not reviewed). The rule IDs for #461 and #4/#5 in the note come from the alert titles
   the user pasted, not from the API. The patch file codeql_filter_extern.patch lacks the follow-up trigger fix.
 - msort: beta was compared only for the SortOrder enum, IsSongSort and the Meter-sort call sites; the Meter
   section loop, SelectSong and ScreenSelectMusic.cpp:1915 were not diffed on beta (msort:7). The checked-out
   commits were confirmed with git rev-parse (engine 8a3bf8884a, Simply Love dd06138b).
 - course: .crs loading was read on v1.3.0 (beta diffed for the course/mod files in cref:15). The course script was tested on a synthetic
   cache with a stub of the extractor functions it imports, not the full tools/difficulty/extract_chart_features.py, and
   not on the real cache. The model JSON beside it was re-typed from the project copy for the test (47 knots
   checked by count; one digit slip was found and fixed by comparing with the project text); the script reads
   whatever JSON the user puts beside it, so use the project's own difficulty_model_notech.json.
   course:5.3 (":;#" names unusable) is true for #SONG only; #SONGSELECT supports escapes (cref:6.3).
 - cref: the Reddit thread and PR #173 page were supplied by the user 2026-10-30 (cref:14); Simply Love's course handling was not read;
   the parser test re-types the driver loop that mimics LoadFromMsd; nothing was run in game.
