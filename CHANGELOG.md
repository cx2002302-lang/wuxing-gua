# Changelog

All notable changes to this project are documented in this file. The format is
a plain keep-a-changelog-style list; the project has one released version so
far.

## 0.1.0 — first public release

The initial public release of `wuxing_gua`, a zero-dependency command-line tool
that decides whether a symmetry group of a finite state machine can be used —
judged on black-box transition data, before any compression, with explicit
refusal when it cannot.

### Added

**Commands** (all JSON on stdout, progress/diagnostics on stderr):

- `discover` — automatic symmetry-group search on a transition model: three-way
  candidate generation, zero-tolerance equivariance judging, closure, sentinel
  re-check, plus a completeness block that can *prove* a search underreturned.
- `check` — full-transition-table verification of a candidate group: two
  zero-tolerance layers (transition equivariance, reward-profile equality).
- `check-sample` — sample-based verification from `(state, action,
  next-state, reward)` trajectories with three verdicts: pass / reject /
  abstain (insufficient samples never converts into a pass).
- `selftest` — end-to-end self-check, 13 branches covering every command,
  flag and exit path.
- `demo` — regenerates the deterministic demo fixtures (byte-identical on
  re-run) used by this list, the README and the selftest.

**Discovery flags** (freely composable; the judging criteria are identical on
every path):

- `--canonize` — canonical renumbering before search, removing
  state-numbering artifacts from discovery results.
- `--multi-label K` — union of generator sets found under K random
  renumberings (fixed seed stream, default 20261025).
- `--extra-candidates` — adds the environment's own action-permutation maps to
  the candidate pool when bijective.
- `--pad-aware` — quotient-graph search arm for unreachable padding states,
  with candidates back-filled and judged identically.
- `--report-confidence` — read-only confidence block (proved-incomplete /
  statistical-suspicion / no-evidence verdicts) with an explicit
  out-of-distribution caveat.
- `--preset robust` — one-flag form of `--canonize --extra-candidates
  --multi-label 8`, the recommended entry point.

**Contract:**

- Exit codes: 0 pass/group found, 1 reject, 2 insufficient samples, 3 input or
  internal error (usage errors also map to 3 so they cannot collide with
  "insufficient samples").
- Input formats: transition model JSON, group JSON (generator lists accepted —
  closed automatically and reported), JSONL trajectory samples.

**Distribution and quality control:**

- Zero third-party dependencies; Python >= 3.10, standard library only.
- Verified install paths: `pip install . --target <dir> --no-build-isolation`
  and a self-contained source bundle (104 files), both selftest-verified
  (`docs/evidence.md`, anchors E39, E40).
- Continuous integration runs the full selftest on every push and pull request
  (`.github/workflows/ci.yml`).

**Documentation:**

- `docs/quickstart.md`, `docs/boundaries.md` (scale envelope and 12 numbered
  limitations), `docs/negative-results.md` (ten transferable negative
  findings), `docs/evidence.md` (traceability index: one anchor per line from
  every claim in this repository to its machine-readable source record).
- `examples/` — three case-study models (32, 512 and 16,384 states) transcribed
  from existing codebases, each with a copy-paste command and its expected
  output.

### Known limitations

Summarized in `docs/boundaries.md`; the short version: bit-string convention
required; discovery (not verification) has a practical scale ceiling between
512 and 16,384 states for padded models; the confidence statistics are
calibrated on research environments and flagged as such; no third-party
reproduction yet.
