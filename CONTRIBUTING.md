# Contributing

Welcome. This project judges symmetry groups of finite state machines, and its
credibility rests on two disciplines that we ask every contributor — internal
or external — to follow. They are short, and they are the whole contract.

## The two disciplines

**1. Preregister before you measure.** If your change produces a number (a
benchmark reading, a new case study, a performance comparison), write down —
before running anything — what you expect, what threshold separates "hit" from
"miss", and what would make you stop. Keep that note in a write-once file and
reference it from your result records. Surprises are welcome; retroactive
predictions are not. Crashes, timeouts and negative results are first-class
outcomes: record them as they happened, and never re-run until it looks right.

**2. Reconcile every number.** Any figure that appears in documentation must be
traceable to a machine-readable record — see `docs/evidence.md` for the index
format (one anchor per line: claim, source file, field). Documentation states
magnitudes; the records hold exact values. If a number cannot be anchored, it
does not go in. Timing claims in prose stay at magnitude level (single-run
wall-clock numbers drift); exact durations live in the records.

## Practical rules

- **Zero dependencies.** The package is standard-library-only, Python >= 3.10.
  Run everything as `python -X utf8 ...`, and read/write files with explicit
  `encoding='utf-8'`.
- **Freeze the criteria.** Never modify judging code to make a result pass.
  Fixes to search or diagnostics go together with a selftest regression run
  (`python -X utf8 -m wuxing_gua selftest`, 13 branches) and, where behavior
  changes, an entry in `CHANGELOG.md`.
- **Refusal is a feature.** Exit codes 1 (reject), 2 (insufficient samples) and
  3 (error) are load-bearing. Do not add paths that turn uncertainty into a
  pass.
- **Compression ratios are readings, not promises.** Describe structure;
  don't advertise savings.
- **Keep documentation in English**, and keep claims positioned against what
  the tool *combines* (group finding, zero-tolerance verification,
  abstention-aware sampling, calibrated self-diagnostics) rather than against
  unnamed other work.

## Pull request checklist

- [ ] `python -X utf8 -m wuxing_gua selftest` passes (13 branches).
- [ ] Every new number in docs is anchored in `docs/evidence.md`.
- [ ] New behavior has a selftest branch or a documented reason not to.
- [ ] `CHANGELOG.md` updated under an "Unreleased" heading if user-visible.
- [ ] No timing-precision claims added to prose (magnitudes only).

## Reporting problems

Open an issue with: the exact command, the exit code, the input files (or a
minimal reproducer), and — if it is a wrong-result report — what you expected
and why. Wrong-pass results (exit 0 where you believe the group is illegal) are
the most valuable bug reports in this project and will be treated as such.
