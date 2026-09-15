# CSE Course Choice &amp; Teacher Assignment System
**Dept. of Computer Science &amp; Engineering, Varendra University**

An end-to-end pipeline that takes teacher course preferences and the department's
curricula, and produces a semester's course-distribution / teacher-assignment
sheet automatically — replacing a manual, spreadsheet-based process.

## How it fits together

```
                         ┌─────────────────────┐
                         │  course_choice_form  │   teachers rank their
                         │  .html (web form)    │   preferred courses (1–6)
                         └──────────┬───────────┘
                                    │ CSV export
                                    ▼
┌──────────────────┐      ┌─────────────────────┐      ┌───────────────────┐
│  Batch_Registry   │      │ Curriculum_Courses   │      │  Teacher_Config    │
│  .xlsx            │─────▶│ .xlsx                │      │  .xlsx             │
│  (active batches, │      │ (course list per     │      │  (credit limits,   │
│  current semester)│      │  curriculum/semester)│      │  theory targets)   │
└──────────┬─────────┘      └──────────┬───────────┘      └─────────┬─────────┘
           │                           │                            │
           └──────────────┬────────────┘                            │
                           ▼                                        │
                 generate_requirements.py                           │
                           │                                        │
                           ▼                                        │
              course_requirements.csv ◀─────── Pre_Locked_Assignments.xlsx
              (this term's full demand)         (External faculty, Math/Chem
                           │                      service courses, special cases —
                           ▼                      removed from the pool up front)
                  assign_engine.py  ◀─────────────────────┘
                           │
                           ▼
              Final course distribution / teacher assignment sheet
```

## Repository structure

```
engine/
  assign_engine.py          — the ranked-choice, credit-capped assignment engine
  generate_requirements.py  — builds this term's course list from Batch Registry + Curriculum Courses
templates/
  Teacher_Config_TEMPLATE.xlsx          — teacher credit limits & theory-course quotas
  Pre_Locked_Assignments_TEMPLATE.xlsx  — External Faculty / Math-Chemistry Service / Fully External courses
  Batch_Registry_TEMPLATE.xlsx          — active batches, curriculum, current semester-position
  Curriculum_Courses.xlsx               — course list for all 3 curricula, all 8 semesters
web/
  course_choice_form.html   — teacher-facing form, Claude-artifact version (shared storage,
                               works instantly inside claude.ai, no setup — but the link only
                               works when opened through Claude)
docs/
  index.html                — the SAME form, adapted to run standalone on GitHub Pages,
                               backed by a free Firebase database instead of Claude's
                               artifact storage. This is the folder GitHub Pages serves from.
  .nojekyll                 — tells GitHub Pages to serve the file as-is, no Jekyll processing
firestore.rules             — security rules to paste into the Firebase console
SETUP_FIREBASE.md           — step-by-step: create the Firebase project, connect it,
                               turn on GitHub Pages
curriculum-reference/
  curriculum_a.md, curriculum_b.md, curriculum_c.md  — transcribed source syllabi (reference)
sample_data/
  Real Summer 2026 data, used to build and validate the assignment engine's rules
  (credit-splitting model, theory/lab pairing, priority order). Contains real
  teacher names — keep this repo private.
```

## Hosting the web form

Two versions of the same form exist, for two different situations:

| | `web/course_choice_form.html` | `docs/index.html` |
|---|---|---|
| Runs inside | a Claude artifact link | any web browser, standalone |
| Backend | Claude's built-in artifact storage | Firebase Firestore (free) |
| Setup needed | none | ~10 minutes, see `SETUP_FIREBASE.md` |
| Link stays valid | as long as the Claude conversation/artifact exists | permanently, at your own GitHub Pages URL |

If you want a permanent, department-owned link (e.g.
`https://<username>.github.io/<repo>/`) instead of a Claude artifact link,
follow **`SETUP_FIREBASE.md`** — it walks through creating the free Firebase
project and turning on GitHub Pages.

## Current status

**Built and tested:**
- Assignment engine (`assign_engine.py`) — validated against real Summer 2026 data.
  Confirmed rules: theory section = 1 teacher, full credit; lab section = 2
  teachers, credit split evenly; a teacher's theory-course count is capped by
  designation (overridable per teacher); whichever teacher takes a theory
  section is mandatorily paired onto that section's lab.
- Course requirements generator (`generate_requirements.py`) — tested against
  3 example batches (one per curriculum), correctly expands each batch's
  current-semester course list into per-section rows and separates out
  Project/Thesis/Industrial-Attachment/Report-Writing as special-load, not
  normal sections.
- Teacher choice web form (`web/course_choice_form.html`) — ranked preferences,
  duplicate-choice prevention, admin submissions view + CSV export, and a
  deadline lock.
- All 3 curricula transcribed and validated (semester-by-semester credit totals
  match the source syllabi exactly).

**Not yet wired together (next steps):**
- `assign_engine.py` currently reads plain CSVs (produced from one-time parsing
  of the old Summer 2026 distribution file). It does not yet read
  `Teacher_Config.xlsx` or `Pre_Locked_Assignments.xlsx` directly — that
  integration is pending until those templates are filled in with real,
  current data (see the red-flagged rows in `Teacher_Config_TEMPLATE.xlsx`).
- Elective resolution (`Curriculum_Courses.xlsx` → "Elective Selection" tab) is
  built but untested against a real semester, since no electives have been
  selected yet.
- No single "run everything" script yet — each stage is run individually.

## Setup

```bash
pip install -r requirements.txt
```

## Running the pipeline (current, manual)

```bash
# 1. Fill in templates/Batch_Registry_TEMPLATE.xlsx (Batches tab) and
#    templates/Curriculum_Courses.xlsx (Elective Selection tab) for the term.
#    Open/save once in Excel or LibreOffice so formulas recalculate.

# 2. Generate this term's course requirements
cd engine
python3 generate_requirements.py ../templates/Batch_Registry_TEMPLATE.xlsx ../templates/Curriculum_Courses.xlsx
# → generated_course_requirements.csv, generated_special_load.csv

# 3. Run the assignment engine (see engine/assign_engine.py docstring —
#    currently expects course_requirements.csv / teacher_choices.csv /
#    teacher_master.csv in the shapes found in sample_data/)
```

## Known limitations

- `web/course_choice_form.html` (the Claude-artifact version) depends on
  Claude's artifact storage API — it only works when opened through a Claude
  artifact link, not as a standalone site. `docs/index.html` is the version
  to use for standalone/GitHub Pages hosting (see "Hosting the web form" above).
- `docs/index.html`'s Firestore security rules (see `firestore.rules`) allow
  open read/write with no login, matching the original artifact version's
  security level. Fine for a low-stakes internal tool; tighten later if needed.
- `sample_data/` contains real teacher names from Summer 2026 — keep this
  repository **private**, or scrub it before making it public.
- Section counts for a given course default to "all of the batch's sections";
  exceptions go in the Batch Registry's "Section Overrides" tab.

## License / usage

Internal tool for the CSE Department, Varendra University. Not licensed for
external redistribution.
