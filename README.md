# itgmania-notes

Source-code analysis notes, patches and helper scripts for my ITGmania fork and related projects
(engine v1.3.0 plus selected beta heads; Simply Love fork). Written by reading the ITGmania source.
The author cannot run the game for every item, so claims carry confidence tags.

**Start with [INDEX.md](INDEX.md).** It has the topic table, section map, file status table and open to-dos.

## Confidence tags
- `[CODE]` read in the source (file and function given)
- `[INFERRED]` reasoned from the code, not tested
- `[UNVERIFIED]` not determined
- `[TESTED]` / `[OBSERVED]` run or observed in game by the user

Each note names the version it applies to. Behavior may differ in newer releases.

## Layout
| Path | Contents |
|---|---|
| `INDEX.md` | Entry point: topics, status of every file, open work |
| `notes/` | Findings files (engine map, series, editor, input, courses, sorting, offsets, scoring, CodeQL, difficulty writeup and cache spec, etc.) |
| `patches/` | Patches (`git apply`); see INDEX for status of each |
| `tools/difficulty/`, `tools/course/` | Course builder (script and GUI), difficulty-model scripts, model JSON, `DifficultyModel.lua`; `.crs` parser tests |

Scripts import each other by name; keep `extract_chart_features.py` and `difficulty_model_notech.json` beside the course scripts when running them.

## Status
Mostly read-only analysis. Several patches are built and field-tested, others are only apply-checked; INDEX.md says which.
Nothing here is endorsed by the ITGmania project.

## License
See [NOTICE](NOTICE).
