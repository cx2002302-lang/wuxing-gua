# Changelog

All notable changes to this project are documented in this file. The format is
a plain keep-a-changelog-style list; the project has one released version so
far.

## Unreleased

### Added

- **Action-semantics declaration for group files** (`semantics` block, optional):
  `{"action": "relabel" | "fixed" | "explicit"}` — `relabel` (actions may be
  renamed along with states; the right reading for switch/milestone systems and
  the historical default), `fixed` (event names pinned; the right reading for
  event-driven state machines), `explicit` (per-action renaming via
  `action_map`). Declared in the group file, resolved by `check`, and reported
  in the output as `semantics` + `semantics_assumed`. Undeclared groups still
  run under `relabel`, but with a loud warning on stderr — the permissive
  default is never silent. `--strict` remains as the fixed override.
  Two-class comparison table and a self-assessment guide:
  [docs/judge-semantics.md](docs/judge-semantics.md).
- Rung 1c in [examples/](examples/): a 4-reachable-state event-labeled close
  fragment (padded to 8) with three candidate groups — the fixed positive
  control (passes), the structurally-identical wait-state swap declaring
  `fixed` (refused, TV 1.0), and the same elements declaring `relabel`
  (passes). One candidate, two opposite verdicts: the two readings, made
  runnable. Generator `make_eventfsm_samples.py --check` re-verifies byte
  identity; both readings recorded in `examples/expected/eventfsm_expected.json`.
- All twelve committed group files now carry an explicit `semantics`
  declaration; the expected records under `examples/expected/` include the
  declaration fields (re-recorded from fresh runs of the same commands — every
  pre-existing reading bit-identical).

### Changed

- `discover` stamps its output with `semantics: {action: relabel, assumed:
  true}` (its search judges under the relabel reading; the stamp travels with
  a saved group file until the model author declares otherwise).
- `discover` refuses models with `n_actions > n_bits` at the entry gate
  (exit 3 with an explanatory message) instead of crashing — its candidate
  search is built on the bit-string action convention; event-class models are
  judged by hand-derived candidates + `check` (see rung 1c).
- `selftest` grows from 13 to 15 branches: the declared-vs-undeclared reading
  invariance (a declaration must not change a switch-class reading), and the
  event-class fixed/relabel divergence with the discover domain guard.

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
