# tutorail-bundles

A catalogue repository. Each subfolder is one self-contained tutorAIl bundle; see
`README.md` for what a bundle is and how to add one.

## Where work is tracked

**GitHub issues in `skomp/tutorail-bundles`.** Not a `TODO.md`. Every issue Claude creates
carries the `created-by-claude` label, and issue bodies are written in ASD-STE100
Simplified Technical English.

## Where course-quality audits go

The findings go in an issue here, one issue per bundle. **The full report goes in
`skomp/tutorail-authoring` under `docs/audits/`**, because that is where the rubric and the
`course-quality` skill live and the report has to be readable beside them.

- `docs/audits/2026-09-12-course-quality-first-run.md` — the first run, three courses. Its
  totals are superseded; the correction note at the top says why.
- `docs/audits/2026-09-13-course-quality-all-bundles.md` — all five bundles, with the
  per-course reports in `docs/audits/2026-09-13/`.

Audits propose and never change a bundle. Applying a proposal is the `tutorail-authoring`
skill's job, after the author agrees.

## A total is not a grade

A course's score is comparable **against its own lessons only**. The figure tracks how
finely a lesson's `## Suggested progression` enumerates clauses, so two bundles with
different house styles are not measured with the same ruler. Never rank the bundles by
total.

## Lesson numbers are ambiguous in `webgl-typescript-scene`

Its chapters 1 to 14 map to the files `00` to `13`, and its chapters 15 to 18 map to the
files `15` to `18`, because the old lesson 14 became the optional `minimal-gltf-loader`.
Name a lesson by its id, never by a bare number.
